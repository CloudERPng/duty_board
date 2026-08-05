"""Duty Board projects: the kanban face.

One fact, two views: a card's assignee gets a linked Daily Todo on their
plan; completing either side completes the other. Sync from the todo side
runs through doc_events (see hooks.py), from the card side inline here.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

COLUMNS = ["To Do", "In Progress", "Completed", "Suspended"]
URGENCIES = ["Low", "Medium", "High", "Critical"]


def _notify(user, title, body):
	try:
		from duty_board.api import _notify_user

		_notify_user(user, title, body)
	except Exception:
		pass


@frappe.whitelist()
def get_projects():
	projects = frappe.get_all(
		"Duty Project",
		filters={"status": "Active"},
		fields=["name", "project_name", "customer", "target_date"],
		order_by="creation asc",
	)
	if not projects:
		return []
	tasks = frappe.get_all(
		"Duty Project Task",
		filters={"project": ["in", [p.name for p in projects]]},
		fields=["project", "column", "due_date"],
	)
	tday = getdate(today())
	stats = {p.name: {"total": 0, "done": 0, "overdue": 0, "suspended": 0} for p in projects}
	for t in tasks:
		s = stats[t.project]
		s["total"] += 1
		if t.column == "Completed":
			s["done"] += 1
		elif t.column == "Suspended":
			s["suspended"] += 1
		elif t.due_date and getdate(t.due_date) < tday:
			s["overdue"] += 1
	for p in projects:
		p.update(stats[p.name])
		p.pct = int(p["done"] * 100 / p["total"]) if p["total"] else 0
		p.target_date = str(p.target_date) if p.target_date else None
		p.days_left = (getdate(p.target_date) - tday).days if p.target_date else None
	return projects


@frappe.whitelist()
def create_project(project_name, customer=None, target_date=None):
	project_name = (project_name or "").strip()
	if not project_name:
		frappe.throw(_("Give the project a name."))
	if not customer:
		frappe.throw(_("Every project belongs to a customer — pick one."))
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Unknown customer."))
	doc = frappe.get_doc(
		{
			"doctype": "Duty Project",
			"project_name": project_name,
			"customer": customer,
			"target_date": target_date or None,
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def archive_project(name):
	frappe.db.set_value("Duty Project", name, "status", "Archived", update_modified=False)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def get_project_board(project):
	rows = frappe.get_all(
		"Duty Project Task",
		filters={"project": project},
		fields=[
			"name", "title", "column", "assignee", "due_date",
			"urgency", "linked_todo", "modified",
		],
		order_by="sort_order asc, creation asc",
	)
	names = [r.name for r in rows]
	note_counts, working = {}, {}
	if names:
		for n in frappe.get_all(
			"Duty Project Note",
			filters={"card": ["in", names]},
			fields=["card", "count(name) as cnt"],
			group_by="card",
		):
			note_counts[n.card] = n.cnt
		for w in frappe.get_all(
			"Work Session",
			filters={"project_task": ["in", names], "end_time": ["is", "not set"]},
			fields=["project_task", "user"],
		):
			working.setdefault(w.project_task, []).append(w.user)
	tday = getdate(today())
	now = frappe.utils.now_datetime()
	tasks = {c: [] for c in COLUMNS}
	for t in rows:
		t.due_date = str(t.due_date) if t.due_date else None
		t.overdue = bool(
			t.due_date and getdate(t.due_date) < tday and t.column in ("To Do", "In Progress")
		)
		t.stale_days = (now - t.modified).days if t.modified else 0
		del t["modified"]
		t.notes = note_counts.get(t.name, 0)
		t.working = working.get(t.name, [])
		tasks.setdefault(t.column, []).append(t)
	return {"columns": COLUMNS, "tasks": tasks}


@frappe.whitelist()
def create_task(project, title, column="To Do", assignee=None, due_date=None, urgency="Medium"):
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the task a title."))
	if column not in COLUMNS:
		column = "To Do"
	if urgency not in URGENCIES:
		urgency = "Medium"
	doc = frappe.get_doc(
		{
			"doctype": "Duty Project Task",
			"project": project,
			"title": title,
			"column": column,
			"assignee": assignee or None,
			"due_date": due_date or None,
			"urgency": urgency,
		}
	).insert(ignore_permissions=True)
	if doc.assignee:
		_ensure_todo(doc)
	frappe.db.commit()
	return get_project_board(project)


@frappe.whitelist()
def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None):
	doc = frappe.get_doc("Duty Project Task", name)
	old_assignee = doc.assignee
	if title and title.strip():
		doc.title = title.strip()
	doc.due_date = due_date or None
	if urgency in URGENCIES:
		doc.urgency = urgency
	doc.description = description
	if client_visible is not None:
		doc.client_visible = cint(client_visible)
	doc.assignee = assignee or None
	doc.save(ignore_permissions=True)

	if old_assignee != doc.assignee:
		if old_assignee and doc.linked_todo and frappe.db.exists("Daily Todo", doc.linked_todo):
			if frappe.db.get_value("Daily Todo", doc.linked_todo, "status") == "Open":
				frappe.delete_doc(
					"Daily Todo", doc.linked_todo, ignore_permissions=True, force=True
				)
		doc.db_set("linked_todo", None, update_modified=False)
		if doc.assignee:
			_ensure_todo(doc)
	elif doc.linked_todo and frappe.db.exists("Daily Todo", doc.linked_todo):
		frappe.db.set_value(
			"Daily Todo", doc.linked_todo, "description", doc.title, update_modified=False
		)

	if column and column in COLUMNS and column != doc.column:
		doc.db_set("column", column, update_modified=False)
		_sync_todo_from_card(doc, column)
		if column == "Completed":
			_stop_my_session_on(doc.name)

	frappe.db.commit()
	return get_project_board(doc.project)


@frappe.whitelist()
def move_task(name, column):
	if column not in COLUMNS:
		frappe.throw(_("Unknown column."))
	doc = frappe.get_doc("Duty Project Task", name)
	doc.db_set("column", column, update_modified=False)
	_sync_todo_from_card(doc, column)
	if column == "Completed":
		_stop_my_session_on(doc.name)
	frappe.db.commit()
	return get_project_board(doc.project)


@frappe.whitelist()
def delete_task(name):
	doc = frappe.get_doc("Duty Project Task", name)
	project = doc.project
	if doc.linked_todo and frappe.db.exists("Daily Todo", doc.linked_todo):
		if frappe.db.get_value("Daily Todo", doc.linked_todo, "status") == "Open":
			frappe.delete_doc("Daily Todo", doc.linked_todo, ignore_permissions=True, force=True)
	frappe.delete_doc("Duty Project Task", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	return get_project_board(project)


def _ensure_todo(card):
	from duty_board.api import user_today

	proj = frappe.db.get_value(
		"Duty Project", card.project, ["project_name", "customer"], as_dict=True
	) or frappe._dict()
	project_name = proj.project_name or card.project
	target_today = user_today(card.assignee)
	date = getdate(card.due_date) if card.due_date else target_today
	if date < target_today:
		date = target_today
	todo = frappe.get_doc(
		{
			"doctype": "Daily Todo",
			"user": card.assignee,
			"date": date,
			"description": card.title,
			"status": "Done" if card.column == "Completed" else "Open",
			"assigned_by": frappe.session.user if frappe.session.user != card.assignee else None,
			"customer": proj.customer,
			"project_task": card.name,
			"project": project_name,
		}
	).insert(ignore_permissions=True)
	card.db_set("linked_todo", todo.name, update_modified=False)
	if card.assignee != frappe.session.user:
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		_notify(
			card.assignee,
			_("Project task from {0}").format(first),
			f"{project_name}: {card.title}",
		)


def _sync_todo_from_card(card, column):
	if not card.linked_todo or not frappe.db.exists("Daily Todo", card.linked_todo):
		return
	if column == "Completed":
		frappe.db.set_value("Daily Todo", card.linked_todo, "status", "Done", update_modified=False)
	elif column in ("To Do", "In Progress"):
		frappe.db.set_value("Daily Todo", card.linked_todo, "status", "Open", update_modified=False)
	# Suspended: the plan item is left untouched


def _stop_my_session_on(card_name):
	from duty_board.api import _get_running_session

	running = _get_running_session(frappe.session.user)
	if running and running.get("project_task") == card_name:
		s = frappe.get_doc("Work Session", running.name)
		s.end_time = frappe.utils.now_datetime()
		s.save(ignore_permissions=True)


@frappe.whitelist()
def get_card(name):
	doc = frappe.get_doc("Duty Project Task", name)
	proj = frappe.db.get_value(
		"Duty Project", doc.project, ["project_name", "customer"], as_dict=True
	) or frappe._dict()
	notes = frappe.get_all(
		"Duty Project Note",
		filters={"card": name},
		fields=["note", "owner", "creation"],
		order_by="creation asc",
	)
	for n in notes:
		n.who = frappe.utils.get_fullname(n.owner)
		n.when = str(n.creation)
	working = [
		w.user
		for w in frappe.get_all(
			"Work Session",
			filters={"project_task": name, "end_time": ["is", "not set"]},
			fields=["user"],
		)
	]
	return {
		"name": doc.name,
		"project": doc.project,
		"project_name": proj.project_name,
		"customer": proj.customer,
		"title": doc.title,
		"column": doc.column,
		"assignee": doc.assignee,
		"due_date": str(doc.due_date) if doc.due_date else None,
		"urgency": doc.urgency,
		"description": doc.description,
		"client_visible": cint(doc.client_visible),
		"notes": notes,
		"working": working,
	}


@frappe.whitelist()
def add_card_note(name, note):
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Empty note."))
	frappe.get_doc({"doctype": "Duty Project Note", "card": name, "note": note}).insert(
		ignore_permissions=True
	)
	frappe.db.commit()
	try:
		from duty_board.api import parse_mentions

		doc = frappe.get_doc("Duty Project Task", name)
		title = doc.title or name
		me = frappe.session.user
		first = frappe.utils.get_fullname(me).split(" ")[0]
		mentioned = [m for m in parse_mentions(note) if m != me]

		participants = set()
		if doc.assignee:
			participants.add(doc.assignee)
		for a in frappe.get_all(
			"Duty Project Note", filters={"card": name}, fields=["owner"]
		):
			participants.add(a.owner)
		participants.discard(me)
		participants -= set(mentioned)

		for m in mentioned:
			_notify(m, _("💬 {0} mentioned you").format(first), f"📁 {title}: {note[:120]}")
		for p in participants:
			_notify(p, _("💬 {0} · 📁 {1}").format(first, title[:40]), note[:120])
	except Exception:
		pass
	frappe.publish_realtime("duty_board_note", {"kind": "card", "id": name})
	return get_card(name)


@frappe.whitelist()
def start_card_work(name):
	from duty_board.api import _is_clocked_in, _stop_running_session
	from frappe.utils import now_datetime

	user = frappe.session.user
	doc = frappe.get_doc("Duty Project Task", name)
	if doc.column in ("Completed",):
		frappe.throw(_("This card is completed."))
	if not _is_clocked_in(user):
		frappe.throw(_("Clock in first before starting work."))
	customer = frappe.db.get_value("Duty Project", doc.project, "customer")

	# picking up an unassigned card assigns you (and creates your plan copy)
	if not doc.assignee:
		doc.assignee = user
		doc.save(ignore_permissions=True)
		_ensure_todo(doc)

	_stop_running_session(user)
	frappe.get_doc(
		{
			"doctype": "Work Session",
			"user": user,
			"activity": doc.title,
			"customer": customer,
			"project_task": doc.name,
			"start_time": now_datetime(),
		}
	).insert()
	if doc.column == "To Do":
		doc.db_set("column", "In Progress", update_modified=False)
		_sync_todo_from_card(doc, "In Progress")
	frappe.db.commit()
	return get_card(name)


@frappe.whitelist()
def stop_card_work(name):
	_stop_my_session_on(name)
	frappe.db.commit()
	return get_card(name)


# ---- doc_events (wired in hooks.py) ----


def on_todo_update(doc, method=None):
	if not doc.get("project_task"):
		return
	if not doc.has_value_changed("status"):
		return
	card = frappe.db.get_value(
		"Duty Project Task", doc.project_task, ["name", "column"], as_dict=True
	)
	if not card:
		return
	if doc.status == "Done" and card.column != "Completed":
		frappe.db.set_value(
			"Duty Project Task", card.name, "column", "Completed", update_modified=False
		)
	elif doc.status == "Open" and card.column == "Completed":
		frappe.db.set_value(
			"Duty Project Task", card.name, "column", "In Progress", update_modified=False
		)


def on_todo_trash(doc, method=None):
	if not doc.get("project_task"):
		return
	if frappe.db.exists("Duty Project Task", doc.project_task):
		frappe.db.set_value(
			"Duty Project Task", doc.project_task, "linked_todo", None, update_modified=False
		)
