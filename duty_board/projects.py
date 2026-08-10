"""Duty Board projects: the kanban face.

One fact, two views: a card's assignee gets a linked Daily Todo on their
plan; completing either side completes the other. Sync from the todo side
runs through doc_events (see hooks.py), from the card side inline here.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, today
from duty_board.permissions import require_staff

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
	from duty_board.permissions import require_staff_or_consultant, consultant_project_names
	_is_c = require_staff_or_consultant()
	_memb = consultant_project_names() if _is_c else None
	projects = frappe.get_all(
		"Duty Project",
		filters={"status": "Active"},
		fields=["name", "project_name", "customer", "target_date", "owner"],
		order_by="creation asc",
	)
	if _is_c:
		projects = [p for p in projects if p.name in _memb]
	elif "System Manager" not in frappe.get_roles():
		_mine = set(
			frappe.get_all(
				"Duty Project Staff",
				filters={"user": frappe.session.user},
				pluck="parent",
			)
		)
		projects = [p for p in projects if p.name in _mine or p.owner == frappe.session.user]
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

	# --- phase + baseline slip per project (portfolio signals) ---
	from frappe.utils import date_diff
	ms_rows = frappe.get_all(
		"Duty Milestone",
		filters={"project": ["in", [p.name for p in projects]]},
		fields=["project", "title", "status", "target_date", "baseline_date", "sort_order"],
		order_by="sort_order asc",
	)
	ph = {p.name: {"total": 0, "done": 0, "current": None, "worst_slip": None} for p in projects}
	for m in ms_rows:
		g = ph[m.project]
		g["total"] += 1
		if m.status == "Approved":
			g["done"] += 1
		elif g["current"] is None:
			g["current"] = m.title  # first non-approved by sort_order = where we are
		if m.baseline_date and m.target_date:
			slip = date_diff(m.target_date, m.baseline_date)
			if g["worst_slip"] is None or slip > g["worst_slip"]:
				g["worst_slip"] = slip
	for p in projects:
		g = ph[p.name]
		p.phases_total = g["total"]
		p.phases_done = g["done"]
		p.phase_current = g["current"] or ("Complete" if g["total"] and g["done"] == g["total"] else None)
		p.worst_slip = g["worst_slip"]
		p.at_risk = 1 if (p.get("overdue", 0) or (g["worst_slip"] or 0) > 0) else 0
	risk_counts = {}
	for rc in frappe.get_all(
		"Duty Project Risk",
		filters={"project": ["in", [p.name for p in projects]], "status": ["!=", "Closed"]},
		fields=["project", "count(name) as cnt"],
		group_by="project",
	):
		risk_counts[rc.project] = rc.cnt
	for p in projects:
		p.open_risks = risk_counts.get(p.name, 0)
	return projects


@frappe.whitelist()
def get_team_load():
	"""Per-person load across all active projects: open tasks, overdue,
	estimated hours remaining, blocked count, project spread."""
	require_staff()
	projects = frappe.get_all(
		"Duty Project", filters={"status": "Active"}, fields=["name", "project_name"]
	)
	if not projects:
		return []
	pnames = {p.name: p.project_name for p in projects}
	rows = frappe.get_all(
		"Duty Project Task",
		filters={
			"project": ["in", list(pnames)],
			"column": ["not in", ["Completed", "Suspended"]],
		},
		fields=["name", "assignee", "project", "due_date", "estimate_hours", "blocked_by", "column"],
	)
	blockers = {r.blocked_by for r in rows if r.blocked_by}
	blocker_done = {}
	if blockers:
		for b in frappe.get_all(
			"Duty Project Task",
			filters={"name": ["in", list(blockers)]},
			fields=["name", "column"],
		):
			blocker_done[b.name] = b.column == "Completed"
	tday = getdate(today())
	load = {}
	for r in rows:
		key = r.assignee or "__unassigned__"
		g = load.setdefault(key, {"open": 0, "overdue": 0, "est": 0.0, "blocked": 0, "projects": set()})
		g["open"] += 1
		g["est"] += r.estimate_hours or 0
		g["projects"].add(r.project)
		if r.due_date and getdate(r.due_date) < tday:
			g["overdue"] += 1
		if r.blocked_by and not blocker_done.get(r.blocked_by, False):
			g["blocked"] += 1
	_fu = {}
	for f in frappe.get_all(
		"Duty Lead",
		filters={"status": "Open", "next_step_user": ["is", "set"]},
		fields=["next_step_user", "count(name) as cnt"],
		group_by="next_step_user",
	):
		_fu[f.next_step_user] = f.cnt
	from duty_board.leave import users_on_leave
	_leave_set = users_on_leave([u for u in load if u != "__unassigned__"]) if load else set()
	out = []
	for user, g in load.items():
		out.append({
			"user": None if user == "__unassigned__" else user,
			"on_leave": 1 if user in _leave_set else 0,
			"full_name": _("Unassigned") if user == "__unassigned__" else frappe.utils.get_fullname(user),
			"followups": _fu.get(user, 0),
			"open": g["open"],
			"overdue": g["overdue"],
			"est_hours": round(g["est"], 1),
			"blocked": g["blocked"],
			"projects": sorted(pnames.get(p, p) for p in g["projects"]),
		})
	out.sort(key=lambda x: (-x["est_hours"], -x["open"]))
	return out


_RISK_SCORE = {"Low": 1, "Medium": 2, "High": 3}


@frappe.whitelist()
def project_risks(project):
	"""The project's risk register, severity-sorted (open first)."""
	require_staff()
	rows = frappe.get_all(
		"Duty Project Risk",
		filters={"project": project},
		fields=["name", "title", "likelihood", "impact", "mitigation", "owner_user", "status"],
	)
	for r in rows:
		r.severity = _RISK_SCORE.get(r.likelihood, 2) * _RISK_SCORE.get(r.impact, 2)
		r.owner_name = frappe.utils.get_fullname(r.owner_user) if r.owner_user else None
	rows.sort(key=lambda r: (r.status == "Closed", -r.severity))
	return rows


@frappe.whitelist()
def risk_save(project, title, likelihood="Medium", impact="Medium", mitigation=None, owner_user=None, status="Open", name=None):
	"""Create (no name) or update (name given) a risk."""
	require_staff()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Describe the risk."))
	vals = {
		"title": title[:200],
		"likelihood": likelihood if likelihood in ("Low", "Medium", "High") else "Medium",
		"impact": impact if impact in ("Low", "Medium", "High") else "Medium",
		"mitigation": (mitigation or "").strip()[:1000] or None,
		"owner_user": owner_user or None,
		"status": status if status in ("Open", "Mitigating", "Closed") else "Open",
	}
	if name:
		frappe.db.set_value("Duty Project Risk", name, vals, update_modified=True)
	else:
		if not frappe.db.exists("Duty Project", project):
			frappe.throw(_("Unknown project."))
		doc = frappe.get_doc(dict(doctype="Duty Project Risk", project=project, **vals))
		doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return project_risks(project)


@frappe.whitelist()
def risk_delete(name):
	require_staff()
	project = frappe.db.get_value("Duty Project Risk", name, "project")
	frappe.delete_doc("Duty Project Risk", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	return project_risks(project)


@frappe.whitelist()
def create_project(project_name, customer=None, target_date=None, room=None):
	require_staff()
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
			"staff": [{"user": frappe.session.user}],
			"project_name": project_name,
			"customer": customer,
			"room": room or None,
			"target_date": target_date or None,
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def archive_project(name):
	require_staff()
	frappe.db.set_value("Duty Project", name, "status", "Archived", update_modified=False)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def get_project_board(project):
	from duty_board.permissions import require_staff_or_consultant, consultant_project_names
	if require_staff_or_consultant() and project not in consultant_project_names():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if not require_staff_or_consultant() and "System Manager" not in frappe.get_roles():
		_ok = frappe.get_all(
			"Duty Project Staff",
			filters={"parent": project, "user": frappe.session.user},
			limit=1,
		) or frappe.db.get_value("Duty Project", project, "owner") == frappe.session.user
		if not _ok:
			frappe.throw(_("You're not assigned to this project."), frappe.PermissionError)

	rows = frappe.get_all(
		"Duty Project Task",
		filters={"project": project},
		fields=[
			"name", "title", "column", "assignee", "due_date",
			"urgency", "linked_todo", "modified", "awaiting_client", "milestone",
			"blocked_by", "estimate_hours",
		],
		order_by="sort_order asc, creation asc",
	)
	names = [r.name for r in rows]
	by_name = {r.name: r for r in rows}
	note_counts, working, sub_counts, actual_secs, file_counts = {}, {}, {}, {}, {}
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
		for s in frappe.get_all(
			"Duty Project Subtask",
			filters={"parent": ["in", names]},
			fields=["parent", "count(name) as total", "sum(case when status='Done' then 1 else 0 end) as done"],
			group_by="parent",
		):
			sub_counts[s.parent] = (cint(s.done), cint(s.total))
		for a in frappe.get_all(
			"Work Session",
			filters={"project_task": ["in", names]},
			fields=["project_task", "sum(duration) as secs"],
			group_by="project_task",
		):
			actual_secs[a.project_task] = a.secs or 0
		for fc in frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Duty Project Task", "attached_to_name": ["in", names]},
			fields=["attached_to_name", "count(name) as cnt"],
			group_by="attached_to_name",
		):
			file_counts[fc.attached_to_name] = fc.cnt
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
		t.subs_done, t.subs_total = sub_counts.get(t.name, (0, 0))
		# t.milestone already present from the fetch
		t.actual_hours = round((actual_secs.get(t.name, 0) or 0) / 3600.0, 1)
		t.file_count = file_counts.get(t.name, 0)
		t.blocked = 0
		t.blocked_title = None
		if t.blocked_by:
			blk = by_name.get(t.blocked_by)
			if blk is not None and blk.column != "Completed":
				t.blocked = 1
				t.blocked_title = blk.title
		tasks.setdefault(t.column, []).append(t)
	from duty_board.client_room import _project_milestone_rows

	return {
		"columns": COLUMNS,
		"tasks": tasks,
		"milestones": _project_milestone_rows(project),
		"consultants": [
			r.user
			for r in frappe.get_all(
				"Duty Project Consultant", filters={"parent": project}, fields=["user"]
			)
		],
		"staff": [
			{"user": r.user, "full_name": frappe.utils.get_fullname(r.user)}
			for r in frappe.get_all(
				"Duty Project Staff", filters={"parent": project}, fields=["user"]
			)
		],
	}


@frappe.whitelist()
def create_task(project, title, column="To Do", assignee=None, due_date=None, urgency="Medium"):
	from duty_board.permissions import require_staff_or_consultant, consultant_project_names
	if require_staff_or_consultant() and project not in consultant_project_names():
		frappe.throw(_("Not permitted."), frappe.PermissionError)

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


def _apply_due(doc, due_date):
	"""Set a card's due date, clamping later subtasks (rule 1) and syncing
	their open todos; notifies affected subtask assignees."""
	_new_due = due_date or None
	if _new_due and doc.get("subtasks"):
		_nd = getdate(_new_due)
		for _s in doc.subtasks:
			if _s.due_date and getdate(_s.due_date) > _nd:
				_s.due_date = _new_due
				if _s.assignee and _s.status == "Open":
					_notify(
						_s.assignee,
						_("📌 Subtask due date moved"),
						_("“{0}” now due {1} (card date changed).").format(_s.title, _new_due),
					)
				if _s.todo and frappe.db.exists("Daily Todo", _s.todo):
					if frappe.db.get_value("Daily Todo", _s.todo, "status") == "Open":
						from duty_board.api import user_today as _ut

						_t = _ut(_s.assignee or frappe.session.user)
						frappe.db.set_value("Daily Todo", _s.todo, "date", _nd if _nd >= _t else _t, update_modified=False)
	doc.due_date = _new_due


@frappe.whitelist()
def reschedule_task(name, due_date=None):
	"""Calendar drag: change ONLY the due date (update_task would null
	unsent fields). Clamp rules and todo sync apply."""
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

	doc = frappe.get_doc("Duty Project Task", name)
	_apply_due(doc, due_date)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_project_board(doc.project)


@frappe.whitelist()
def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None, blocked_by=None, estimate_hours=None):
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

	doc = frappe.get_doc("Duty Project Task", name)
	if _is_c and column == "Completed" and doc.column != "Completed":
		from frappe.utils import flt
		if not flt(hours) > 0:
			frappe.throw(_("Enter the hours spent before completing this task."))
		from duty_board.api import _retro_session
		_retro_session(
			hours, doc.title,
			frappe.db.get_value("Duty Project", doc.project, "customer"),
			project_task=name,
		)
		try:
			from duty_board.notify import closure_email

			closure_email(doc, hours, kind="task")
		except Exception:
			frappe.log_error(frappe.get_traceback()[-1200:], "task closure email")
	old_assignee = doc.assignee
	was_awaiting = cint(doc.awaiting_client)
	if awaiting_client is not None:
		doc.awaiting_client = cint(awaiting_client)
	if title and title.strip():
		doc.title = title.strip()
	_apply_due(doc, due_date)
	if urgency in URGENCIES:
		doc.urgency = urgency
	doc.description = description
	if client_visible is not None:
		doc.client_visible = cint(client_visible)
	doc.assignee = assignee or None
	if milestone is not None:
		doc.milestone = milestone or None
	if blocked_by is not None:
		new_blk = blocked_by or None
		if new_blk:
			if new_blk == doc.name:
				frappe.throw(_("A task cannot be blocked by itself."))
			# cycle guard: walk up the chain from the proposed blocker
			seen, cur = set(), new_blk
			for _hop in range(50):
				if cur == doc.name:
					frappe.throw(_("That would create a dependency loop."))
				if not cur or cur in seen:
					break
				seen.add(cur)
				cur = frappe.db.get_value("Duty Project Task", cur, "blocked_by")
		doc.blocked_by = new_blk
	if estimate_hours is not None:
		from frappe.utils import flt
		doc.estimate_hours = flt(estimate_hours) or None
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
			try:
				from duty_board.notify import assignment_email

				assignment_email(doc, [doc.assignee], kind="task")
			except Exception:
				frappe.log_error(frappe.get_traceback()[-1200:], "task assign email")
	elif doc.linked_todo and frappe.db.exists("Daily Todo", doc.linked_todo):
		frappe.db.set_value(
			"Daily Todo", doc.linked_todo, "description", doc.title, update_modified=False
		)

	if column and column in COLUMNS and column != doc.column:
		if column == "Completed":
			_block_completion_on_open_subtasks(doc.name)
		doc.db_set("column", column, update_modified=False)
		_sync_todo_from_card(doc, column)
		if column == "Completed":
			_stop_my_session_on(doc.name)

	if awaiting_client is not None and cint(awaiting_client) and not was_awaiting:
		_nudge_client(doc)

	frappe.db.commit()
	return get_project_board(doc.project)


def _nudge_client(doc):
	"""Task flagged as needing the client's input — tell them on their portal."""
	try:
		from duty_board.client_room import _post, _push_room_clients

		room_name = frappe.db.get_value("Client Room", {"project": doc.project}, "name")
		if not room_name:
			return
		room = frappe.get_doc("Client Room", room_name)
		_post(
			room,
			_("⏳ We need your input to continue: “{0}” — see the Projects tab on your portal.").format(
				doc.title
			),
		)
		_push_room_clients(room, _("⏳ Your input is needed · Xlevel"), doc.title[:120])
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board nudge_client")


@frappe.whitelist()
def move_task(name, column, hours=None):
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

	if column not in COLUMNS:
		frappe.throw(_("Unknown column."))
	doc = frappe.get_doc("Duty Project Task", name)
	if column == "Completed":
		_block_completion_on_open_subtasks(name)
	if _is_c and column == "Completed" and doc.column != "Completed":
		from frappe.utils import flt
		if not flt(hours) > 0:
			frappe.throw(_("Enter the hours spent before completing this task."))
		from duty_board.api import _retro_session
		_retro_session(
			hours, doc.title,
			frappe.db.get_value("Duty Project", doc.project, "customer"),
			project_task=name,
		)
		try:
			from duty_board.notify import closure_email

			closure_email(doc, hours, kind="task")
		except Exception:
			frappe.log_error(frappe.get_traceback()[-1200:], "task closure email")
	doc.db_set("column", column, update_modified=False)
	_sync_todo_from_card(doc, column)
	if column == "Completed":
		_stop_my_session_on(doc.name)
	frappe.db.commit()
	return get_project_board(doc.project)


@frappe.whitelist()
def delete_task(name):
	require_staff()
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
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

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
	subtasks = []
	for s in doc.get("subtasks") or []:
		subtasks.append(
			{
				"row": s.name,
				"title": s.title,
				"assignee": s.assignee,
				"assignee_first": frappe.utils.get_fullname(s.assignee).split(" ")[0] if s.assignee else None,
				"due_date": str(s.due_date) if s.due_date else None,
				"status": s.status,
				"note": s.note,
				"done_by_first": frappe.utils.get_fullname(s.done_by).split(" ")[0] if s.done_by else None,
			}
		)
	return {
		"name": doc.name,
		"project": doc.project,
		"project_name": proj.project_name,
		"customer": proj.customer,
		"title": doc.title,
		"column": doc.column,
		"subtasks": subtasks,
		"subs_done": len([s for s in subtasks if s["status"] == "Done"]),
		"subs_total": len(subtasks),
		"assignee": doc.assignee,
		"due_date": str(doc.due_date) if doc.due_date else None,
		"urgency": doc.urgency,
		"milestone": doc.milestone,
		"blocked_by": doc.blocked_by,
		"estimate_hours": doc.estimate_hours,
		"files": [
			{
				"name": f.name,
				"file_name": f.file_name,
				"file_url": f.file_url,
				"kind": (
					"image" if (f.file_name or "").lower().rsplit(".", 1)[-1] in ("png", "jpg", "jpeg", "gif", "webp")
					else "pdf" if (f.file_name or "").lower().endswith(".pdf")
					else "other"
				),
			}
			for f in frappe.get_all(
				"File",
				filters={"attached_to_doctype": "Duty Project Task", "attached_to_name": name},
				fields=["name", "file_name", "file_url"],
				order_by="creation asc",
			)
		],
		"actual_hours": round(
			(frappe.db.sql(
				"select coalesce(sum(duration),0) from `tabWork Session` where project_task=%s",
				name,
			)[0][0] or 0) / 3600.0, 1),
		"task_options": [
			{"name": r.name, "title": r.title}
			for r in frappe.get_all(
				"Duty Project Task",
				filters={"project": doc.project, "name": ["!=", doc.name]},
				fields=["name", "title"],
				order_by="creation asc",
			)
		],
		"description": doc.description,
		"client_visible": cint(doc.client_visible),
		"notes": notes,
		"working": working,
	}


@frappe.whitelist()
def add_card_note(name, note):
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

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
def task_file_delete(name, file):
	"""Remove one attachment from a task."""
	require_staff()
	row = frappe.db.get_value(
		"File", file, ["attached_to_doctype", "attached_to_name"], as_dict=True
	)
	if not row or row.attached_to_doctype != "Duty Project Task" or row.attached_to_name != name:
		frappe.throw(_("Not found."))
	frappe.delete_doc("File", file, ignore_permissions=True, force=True)
	frappe.db.commit()
	return get_card(name)


@frappe.whitelist()
def start_card_work(name):
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

	from duty_board.api import _is_clocked_in, _stop_running_session
	from frappe.utils import now_datetime

	user = frappe.session.user
	doc = frappe.get_doc("Duty Project Task", name)
	if doc.column in ("Completed",):
		frappe.throw(_("This card is completed."))
	if not _is_c and not _is_clocked_in(user):
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
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

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


# ---------------- subtasks: delegation inside a card ----------------


def _open_subtask_titles(task_name):
	return frappe.get_all(
		"Duty Project Subtask",
		filters={"parent": task_name, "status": "Open"},
		pluck="title",
	)


def _block_completion_on_open_subtasks(task_name):
	open_t = _open_subtask_titles(task_name)
	if open_t:
		frappe.throw(
			_("Can't complete this card — {0} open subtask(s): {1}").format(
				len(open_t), ", ".join(open_t[:5]) + ("…" if len(open_t) > 5 else "")
			)
		)


def _subtask_todo(card, row):
	"""Daily Todo for a subtask assignee, clamped to their today like cards."""
	from duty_board.api import user_today

	target_today = user_today(row.assignee)
	date = getdate(row.due_date) if row.due_date else target_today
	if date < target_today:
		date = target_today
	todo = frappe.get_doc(
		{
			"doctype": "Daily Todo",
			"user": row.assignee,
			"date": date,
			"description": f"📌 {row.title} · under “{card.title}”"[:140],
			"status": "Open",
			"assigned_by": frappe.session.user if frappe.session.user != row.assignee else None,
		}
	).insert(ignore_permissions=True)
	return todo.name


def _validate_subtask_due(card, due_date):
	if due_date and card.due_date and getdate(due_date) > getdate(card.due_date):
		frappe.throw(
			_("A subtask can't be due after the card itself ({0}).").format(card.due_date)
		)


@frappe.whitelist()
def subtask_add(task, title, assignee=None, due_date=None, note=None):
	from duty_board.permissions import require_staff_or_consultant
	if require_staff_or_consultant():
		_consultant_task_check(task)

	card = frappe.get_doc("Duty Project Task", task)
	title = (title or "").strip()[:140]
	if not title:
		frappe.throw(_("Give the subtask a title."))
	_validate_subtask_due(card, due_date)
	row = card.append(
		"subtasks",
		{
			"title": title,
			"assignee": (assignee or "").strip() or None,
			"due_date": due_date or None,
			"note": (note or "").strip() or None,
			"status": "Open",
		},
	)
	card.save(ignore_permissions=True)
	if row.assignee:
		todo = _subtask_todo(card, row)
		frappe.db.set_value("Duty Project Subtask", row.name, "todo", todo, update_modified=False)
		if row.assignee != frappe.session.user:
			_notify(row.assignee, _("📌 Subtask for you"), f"{row.title} · {card.title}")
	frappe.db.commit()
	return get_card(task)


@frappe.whitelist()
def subtask_update(task, row, title=None, assignee=None, due_date=None, note=None):
	from duty_board.permissions import require_staff_or_consultant
	if require_staff_or_consultant():
		_consultant_task_check(task)

	card = frappe.get_doc("Duty Project Task", task)
	target = next((s for s in card.subtasks if s.name == row), None)
	if not target:
		frappe.throw(_("Subtask not found."))
	if due_date is not None:
		_validate_subtask_due(card, due_date or None)
		target.due_date = due_date or None
	if title and title.strip():
		target.title = title.strip()[:140]
	old_assignee = target.assignee
	if assignee is not None:
		target.assignee = (assignee or "").strip() or None
	if note is not None:
		target.note = (note or "").strip() or None
	card.save(ignore_permissions=True)
	if assignee is not None and target.assignee and target.assignee != old_assignee and target.status == "Open":
		todo = _subtask_todo(card, target)
		frappe.db.set_value("Duty Project Subtask", target.name, "todo", todo, update_modified=False)
		if target.assignee != frappe.session.user:
			_notify(target.assignee, _("📌 Subtask for you"), f"{target.title} · {card.title}")
	elif target.todo and frappe.db.exists("Daily Todo", target.todo):
		vals = {"description": f"📌 {target.title} · under “{card.title}”"[:140]}
		if due_date is not None and target.due_date and frappe.db.get_value("Daily Todo", target.todo, "status") == "Open":
			from duty_board.api import user_today

			d = getdate(target.due_date)
			t = user_today(target.assignee or frappe.session.user)
			vals["date"] = d if d >= t else t
		frappe.db.set_value("Daily Todo", target.todo, vals, update_modified=False)
	frappe.db.commit()
	return get_card(task)


@frappe.whitelist()
def subtask_toggle(task, row):
	from duty_board.permissions import require_staff_or_consultant
	if require_staff_or_consultant():
		_consultant_task_check(task)

	card = frappe.get_doc("Duty Project Task", task)
	target = next((s for s in card.subtasks if s.name == row), None)
	if not target:
		frappe.throw(_("Subtask not found."))
	if target.status == "Open":
		target.status = "Done"
		target.done_by = frappe.session.user
		target.done_on = now_datetime()
		if target.todo and frappe.db.exists("Daily Todo", target.todo):
			if frappe.db.get_value("Daily Todo", target.todo, "status") == "Open":
				frappe.db.set_value("Daily Todo", target.todo, "status", "Done", update_modified=False)
	else:
		target.status = "Open"
		target.done_by = None
		target.done_on = None
		if target.todo and frappe.db.exists("Daily Todo", target.todo):
			frappe.db.set_value("Daily Todo", target.todo, "status", "Open", update_modified=False)
	card.save(ignore_permissions=True)
	frappe.db.commit()
	if target.status == "Done" and not _open_subtask_titles(task):
		owner = card.assignee
		if owner and owner != frappe.session.user:
			_notify(owner, _("✅ All subtasks done"), _("“{0}” — ready to complete the card.").format(card.title))
	return get_card(task)


@frappe.whitelist()
def subtask_delete(task, row):
	from duty_board.permissions import require_staff_or_consultant
	if require_staff_or_consultant():
		_consultant_task_check(task)

	card = frappe.get_doc("Duty Project Task", task)
	target = next((s for s in card.subtasks if s.name == row), None)
	if not target:
		frappe.throw(_("Subtask not found."))
	if target.todo and frappe.db.exists("Daily Todo", target.todo):
		if frappe.db.get_value("Daily Todo", target.todo, "status") == "Open":
			frappe.delete_doc("Daily Todo", target.todo, ignore_permissions=True, force=True)
	card.remove(target)
	card.save(ignore_permissions=True)
	frappe.db.commit()
	return get_card(task)


def _consultant_task_check(name):
	"""Consultants touch tasks only inside projects they are granted on."""
	from duty_board.permissions import consultant_project_names

	proj = frappe.db.get_value("Duty Project Task", name, "project")
	if not proj or proj not in consultant_project_names():
		frappe.throw(_("Not permitted."), frappe.PermissionError)


@frappe.whitelist()
def set_project_consultants(project, users):
	"""Staff-only: replace the project's consultant grant list. Notifies
	newly granted consultants."""
	require_staff()
	import json as _json

	from duty_board.permissions import CONSULTANT_ROLE, is_consultant

	users = _json.loads(users) if isinstance(users, str) else (users or [])
	doc = frappe.get_doc("Duty Project", project)
	before = {r.user for r in (doc.consultants or [])}
	doc.set("consultants", [])
	for u in users:
		if not is_consultant(u):
			frappe.throw(_("{0} does not carry the {1} role.").format(u, CONSULTANT_ROLE))
		doc.append("consultants", {"user": u})
	doc.save(ignore_permissions=True)
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	for u in set(users) - before:
		_notify(u, _("Project access granted by {0}").format(first), doc.project_name)
	frappe.db.commit()
	return {"ok": 1, "count": len(users)}


@frappe.whitelist()
def list_consultants():
	"""Staff-only: enabled users carrying the consultant role, for pickers."""
	require_staff()
	from duty_board.permissions import CONSULTANT_ROLE

	rows = frappe.get_all(
		"Has Role",
		filters={"role": CONSULTANT_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	out = []
	for u in set(rows):
		if frappe.db.get_value("User", u, "enabled"):
			out.append({"user": u, "full_name": frappe.utils.get_fullname(u)})
	return sorted(out, key=lambda x: x["full_name"])


def _can_edit_team(doc):
	return (
		"System Manager" in frappe.get_roles()
		or doc.owner == frappe.session.user
	)


@frappe.whitelist()
def project_staff_options(project):
	"""The staff roster (Duty Settings user-rates table) with membership
	flags for the 👥 Team dialog."""
	require_staff()
	doc = frappe.get_doc("Duty Project", project)
	members = {r.user for r in (doc.get("staff") or [])}
	roster = sorted(
		set(
			frappe.get_all(
				"Duty User Rate",
				filters={"parenttype": "Duty Settings"},
				pluck="user",
			)
		)
	)
	options = [
		{"user": u, "full_name": frappe.utils.get_fullname(u), "member": 1 if u in members else 0}
		for u in roster
	]
	options.sort(key=lambda x: x["full_name"] or "")
	return {"options": options, "can_edit": 1 if _can_edit_team(doc) else 0}


@frappe.whitelist()
def project_staff_set(project, users):
	"""Replace the project's staff team. System Managers and the
	project's creator only. Newly added staff are notified."""
	require_staff()
	import json as _json

	users = _json.loads(users) if isinstance(users, str) else (users or [])
	doc = frappe.get_doc("Duty Project", project)
	if not _can_edit_team(doc):
		frappe.throw(_("Only managers or the project's creator set the team."), frappe.PermissionError)
	roster = set(
		frappe.get_all(
			"Duty User Rate", filters={"parenttype": "Duty Settings"}, pluck="user"
		)
	)
	before = {r.user for r in (doc.get("staff") or [])}
	doc.set("staff", [])
	for u in users:
		if u in roster:
			doc.append("staff", {"user": u})
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	for u in set(users) - before:
		try:
			_notify(u, _("👥 Added to project team by {0}").format(first), doc.project_name)
		except Exception:
			pass
	return project_staff_options(project)
