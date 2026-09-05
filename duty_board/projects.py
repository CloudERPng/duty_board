"""Duty Board projects: the kanban face.

One fact, two views: a card's assignee gets a linked Daily Todo on their
plan; completing either side completes the other. Sync from the todo side
runs through doc_events (see hooks.py), from the card side inline here.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, date_diff, flt, getdate, now_datetime, nowdate, today
from duty_board.permissions import require_staff

COLUMNS = ["To Do", "In Progress", "Completed", "Suspended"]
URGENCIES = ["Low", "Medium", "High", "Critical"]


def _notify(user, title, body):
	try:
		from duty_board.api import _notify_user

		_notify_user(user, title, body)
	except Exception:
		pass



def _notify_assignment(doc, actor=None, changed=None):
	"""Assignment and change notifications for a card.

	Everything routes through notify_events.announce so the task and issue sides
	cannot drift apart again — they already had once, with tasks silent for
	staff while issues notified.
	"""
	from duty_board.notify_events import announce

	actor = actor or frappe.session.user
	if changed:
		announce(
			doc, "task",
			_("Task updated by {0}").format(frappe.utils.get_fullname(actor).split(" ")[0]),
			body=", ".join(changed),
			actor=actor,
		)
		return
	if not doc.assignee or doc.assignee == actor:
		return
	who = frappe.utils.get_fullname(actor).split(" ")[0]
	when = _(" · due {0}").format(frappe.utils.formatdate(doc.due_date)) if doc.due_date else ""
	announce(
		doc, "task",
		_("Task assigned to you by {0}").format(who),
		body="{0}{1}".format(doc.title, when),
		actor=actor,
	)


def _stamp_assigner(doc, actor=None):
	"""Record who handed the card over, so they can be told when it moves."""
	actor = actor or frappe.session.user
	if doc.assignee and doc.assignee != actor:
		doc.assigned_by = actor
	elif doc.assignee == actor and not doc.get("assigned_by"):
		doc.assigned_by = actor


def _notify_status(doc, event, actor=None, note=None):
	"""Work started, completed, reopened — told to assignee and assigner both.

	This is the case that had no coverage at all: somebody delegating a card
	had no way of hearing it was finished.
	"""
	from duty_board.notify_events import announce

	actor = actor or frappe.session.user
	announce(
		doc, "task",
		_("{0} — {1}").format(event, frappe.utils.get_fullname(actor).split(" ")[0]),
		body=doc.title,
		actor=actor,
		note=note,
	)


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
	from duty_board.plan_templates import plan_labels

	return {
		"columns": COLUMNS,
		"tasks": tasks,
		"milestones": _project_milestone_rows(project),
		# plan picker is built from PLAN_TYPES so adding a plan type needs no JS
		# change. The old picker hardcoded "standard" only, which is why the CRM
		# plan existed for months and was unreachable from the interface.
		"plan_types": [{"key": k, "label": lbl} for k, lbl in plan_labels()],
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
def create_task(project, title, column="To Do", assignee=None, due_date=None,
				urgency="Medium", milestone=None):
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
			# set here rather than by a second call: a task created in a phase
			# column belongs to that phase from the moment it exists
			"milestone": milestone or None,
		}
	).insert(ignore_permissions=True)
	if doc.assignee:
		_stamp_assigner(doc)
		doc.db_set("assigned_by", doc.assigned_by, update_modified=False)
		_ensure_todo(doc)
		_notify_assignment(doc)
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
def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None, blocked_by=None, estimate_hours=None, start_date=None):
	from duty_board.permissions import require_staff_or_consultant
	_is_c = require_staff_or_consultant()
	if _is_c:
		_consultant_task_check(name)

	doc = frappe.get_doc("Duty Project Task", name)
	# When it was finished, stamped on the transition. Without it there is only
	# a count of what is done NOW, which cannot say whether the project was
	# ahead or behind at any point in the past — and a plan-versus-actual curve
	# is exactly that question asked at every date.
	if column and column != doc.column:
		if column == "Completed":
			doc.db_set("completed_on", now_datetime(), update_modified=False)
		elif doc.column == "Completed":
			# moved back out: the completion did not happen, so the date goes
			doc.db_set("completed_on", None, update_modified=False)
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
	if start_date is not None:
		doc.start_date = start_date or None
		# a start after the due date is a typo, and letting it through would
		# draw a bar running backwards on the Gantt
		if doc.start_date and doc.due_date and getdate(doc.start_date) > getdate(doc.due_date):
			frappe.throw(_("The start is after the due date."))
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
			_stamp_assigner(doc)
			_ensure_todo(doc)
			_notify_assignment(doc)
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
	prev_col = doc.column
	doc.db_set("column", column, update_modified=False)
	_sync_todo_from_card(doc, column)
	if column == "Completed":
		_stop_my_session_on(doc.name)
	frappe.db.commit()
	if column != prev_col:
		doc.column = column
		_notify_status(doc, _("Moved to {0}").format(column))
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


def _meeting_when(name):
	"""Date and time of a booked meeting, for the task drawer."""
	if not name:
		return None
	m = frappe.db.get_value("Duty Meeting", name,
							["meeting_date", "start_time", "status"], as_dict=True)
	if not m or m.status in ("Cancelled", "Declined"):
		return None
	return "%s %s" % (m.meeting_date, str(m.start_time)[:5])


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
		# without this the drawer opens with the field blank even where a start
		# is set, and saving would silently clear it
		"start_date": str(doc.start_date) if doc.start_date else None,
		"meeting": doc.meeting,
		"meeting_when": _meeting_when(doc.meeting),
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
	# doc above is bound inside a try; fetch our own so a failure there cannot
	# leave this line raising NameError on a path that otherwise succeeded
	_notify_status(frappe.get_doc("Duty Project Task", name), _("Progress update"), note=note)
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
	_notify_status(doc, _("Work started"))
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


@frappe.whitelist()
def set_project_rag(project, rag, reason=None, owner_user=None, due=None):
	"""Record the project's health as a decision somebody made.

	It used to be worked out in the browser from "is any task overdue", which
	gives a colour with nothing behind it: no reason, no owner, no recovery
	date, and nothing to ask about in a review. Amber has to be explained, so
	a reason is required for anything that is not green.
	"""
	require_staff()
	if rag not in ("On track", "At risk", "Off track", "Completed"):
		frappe.throw(_("Unknown status."))
	if rag in ("At risk", "Off track") and not (reason or "").strip():
		frappe.throw(_("Say why it is {0}. A status with no reason behind it is the first thing a reviewer asks about, and nobody will be able to answer.").format(rag.lower()))
	prev = frappe.db.get_value("Duty Project", project, "rag")
	frappe.db.set_value("Duty Project", project, {
		"rag": rag,
		"rag_reason": (reason or "").strip() or None,
		"rag_owner": owner_user or None,
		"rag_due": due or None,
		# only restarted when the colour itself changes, so "amber for 19 days"
		# stays true when the reason is edited
		"rag_set_on": now_datetime() if prev != rag else
					  (frappe.db.get_value("Duty Project", project, "rag_set_on") or now_datetime()),
		"rag_set_by": frappe.session.user,
	})
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def set_project_baseline(project, baseline_target_date=None, force=0):
	"""Fix the go-live date the engagement is measured against.

	Set once, at the point the plan is agreed. It must not move afterwards or
	slip becomes unmeasurable — a baseline that follows the target always
	reports no slip, which is the most common way a plan quietly stops being a
	commitment.
	"""
	require_staff()
	cur = frappe.db.get_value("Duty Project", project, "baseline_target_date")
	if cur and not cint(force):
		frappe.throw(_("The baseline is already {0}. Changing it erases the slip measured against it, so it takes a deliberate override — and a re-baseline should normally be a change request instead.").format(cur))
	d = baseline_target_date or frappe.db.get_value("Duty Project", project, "target_date")
	if not d:
		frappe.throw(_("There is no target date to baseline."))
	frappe.db.set_value("Duty Project", project,
						{"baseline_target_date": d, "baselined_on": now_datetime()})
	frappe.db.commit()
	return {"ok": 1, "baseline": str(d)}


# ───────────────────────── actuals against estimates ─────────────────────────
#
# The estimate has been captured since the beginning and nothing ever recorded
# what a task actually took — so there was no variance, no forecast, and no
# evidence the estimates meant anything. It is the first thing a project
# consultant asks for.
#
# Nothing new is captured. Work Session already carries project_task and
# duration; it was only ever read to show who is working right now. This sums
# it, which is arithmetic on data you already have.


def _actuals_for_tasks(names):
	"""Hours booked against each task, from the sessions already recorded."""
	if not names:
		return {}
	rows = frappe.db.sql(
		"""select project_task as t, coalesce(sum(duration), 0) as secs,
				  count(name) as sessions, count(distinct user) as people
		   from `tabWork Session`
		   where project_task in %(names)s and duration is not null
		   group by project_task""",
		{"names": tuple(names)}, as_dict=True)
	return {r.t: {"hours": round(flt(r.secs) / 3600.0, 2),
				  "sessions": cint(r.sessions), "people": cint(r.people)}
			for r in rows}


@frappe.whitelist()
def project_effort(project):
	"""Estimated against actual, per phase and per task.

	VARIANCE IS REPORTED ONLY WHERE BOTH NUMBERS EXIST. A task with hours booked
	and no estimate is not "over" — nobody said what it should take. Counting
	those as overruns is how an effort report becomes an argument rather than
	evidence, so they are listed apart and named.
	"""
	require_staff()
	tasks = frappe.get_all(
		"Duty Project Task",
		filters={"project": project},
		fields=["name", "title", "milestone", "column", "estimate_hours", "assignee"],
		limit_page_length=0)
	names = [t.name for t in tasks]
	act = _actuals_for_tasks(names)

	ms = {m.name: m for m in frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title", "sort_order", "status", "target_date"],
		order_by="sort_order asc", limit_page_length=0)}

	rows, phases = [], {}
	for t in tasks:
		a = act.get(t.name) or {}
		est = flt(t.estimate_hours) or 0.0
		hrs = flt(a.get("hours") or 0)
		done = (t.column or "").lower() in ("done", "complete", "completed")
		var = (hrs - est) if (est > 0 and hrs > 0) else None
		rows.append({
			"task": t.name, "title": t.title, "milestone": t.milestone,
			"phase": (ms.get(t.milestone) or {}).get("title"),
			"assignee": frappe.utils.get_fullname(t.assignee) if t.assignee else None,
			"estimate": est, "actual": hrs, "done": 1 if done else 0,
			"sessions": a.get("sessions", 0), "people": a.get("people", 0),
			"variance": var,
			"variance_pct": round(var * 100 / est, 1) if (var is not None and est) else None,
			"no_estimate": 1 if (hrs > 0 and est <= 0) else 0,
			"not_started": 1 if (est > 0 and hrs <= 0) else 0,
		})
		key = t.milestone or "_none"
		p = phases.setdefault(key, {
			"milestone": t.milestone,
			"phase": (ms.get(t.milestone) or {}).get("title") or _("Unassigned"),
			"sort": (ms.get(t.milestone) or {}).get("sort_order") or 999,
			"estimate": 0.0, "actual": 0.0, "tasks": 0, "done": 0,
			"est_done": 0.0, "act_done": 0.0, "unestimated_hours": 0.0})
		p["estimate"] += est
		p["actual"] += hrs
		p["tasks"] += 1
		if est <= 0 and hrs > 0:
			p["unestimated_hours"] += hrs
		if done:
			p["done"] += 1
			p["est_done"] += est
			p["act_done"] += hrs

	for p in phases.values():
		# only completed work with an estimate can say anything about accuracy
		p["variance"] = (p["act_done"] - p["est_done"]) if p["est_done"] > 0 else None
		p["variance_pct"] = (round(p["variance"] * 100 / p["est_done"], 1)
							 if p["est_done"] > 0 else None)
		# what the phase is likely to cost, if the rest behaves like the part done
		rate = (p["act_done"] / p["est_done"]) if p["est_done"] > 0 else None
		p["forecast"] = round(p["estimate"] * rate, 1) if rate else None

	est_all = sum(p["estimate"] for p in phases.values())
	act_all = sum(p["actual"] for p in phases.values())
	est_done = sum(p["est_done"] for p in phases.values())
	act_done = sum(p["act_done"] for p in phases.values())
	rate = (act_done / est_done) if est_done > 0 else None

	rows.sort(key=lambda r: -(abs(r["variance"]) if r["variance"] is not None else 0))
	return {
		"project": project,
		"phases": sorted(phases.values(), key=lambda p: p["sort"]),
		"tasks": rows,
		"estimate": est_all, "actual": act_all,
		"estimate_done": est_done, "actual_done": act_done,
		"burn_rate": round(rate, 2) if rate else None,
		"forecast": round(est_all * rate, 1) if rate else None,
		"overrun": round(est_all * rate - est_all, 1) if rate else None,
		"unestimated": len([r for r in rows if r["no_estimate"]]),
		"unestimated_hours": round(sum(r["actual"] for r in rows if r["no_estimate"]), 2),
		"no_actuals": len([r for r in rows if r["not_started"] and r["done"]]),
	}


# ────────────────────────────── decision log ─────────────────────────────────


@frappe.whitelist()
def decisions(project=None, client_only=0):
	"""Every decision taken, newest first."""
	f = {}
	if project:
		f["project"] = project
	if cint(client_only):
		f["client_visible"] = 1
	rows = frappe.get_all(
		"Duty Project Decision", filters=f,
		fields=["name", "project", "title", "decided_on", "status", "raised_by",
				"decided_by", "milestone", "context", "options_considered",
				"impact", "client_visible", "change_request", "supersedes", "note"],
		order_by="decided_on desc, creation desc", limit_page_length=0)
	ms = {m.name: m.title for m in frappe.get_all(
		"Duty Milestone", fields=["name", "title"], limit_page_length=0)}
	# a superseded decision keeps its place; what replaced it is named on it
	replaced_by = {}
	for r in rows:
		if r.supersedes:
			replaced_by[r.supersedes] = {"name": r.name, "title": r.title,
										 "on": str(r.decided_on)}
	for r in rows:
		r.phase = ms.get(r.milestone)
		r.replaced_by = replaced_by.get(r.name)
	return {
		"rows": rows,
		"agreed": len([r for r in rows if r.status == "Agreed"]),
		"open": len([r for r in rows if r.status == "Proposed"]),
		"superseded": len([r for r in rows if r.status in ("Superseded", "Reversed")]),
	}


@frappe.whitelist()
def save_decision(name=None, **kwargs):
	require_staff()
	allowed = ("project", "title", "decided_on", "status", "raised_by", "decided_by",
			   "milestone", "context", "options_considered", "impact",
			   "client_visible", "change_request", "supersedes", "note")
	doc = (frappe.get_doc("Duty Project Decision", name) if name
		   else frappe.new_doc("Duty Project Decision"))
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not (doc.title or "").strip():
		frappe.throw(_("Say what was decided."))
	if not (doc.decided_by or "").strip():
		frappe.throw(_("Record who made the call. A decision with nobody's name against it settles nothing when it is questioned later."))
	if not doc.decided_on:
		doc.decided_on = nowdate()
	doc.save(ignore_permissions=True)

	# superseding marks the old one rather than deleting it: the sequence is the
	# record, and a log that can be edited backwards is not evidence
	if doc.supersedes and frappe.db.exists("Duty Project Decision", doc.supersedes):
		old = frappe.db.get_value("Duty Project Decision", doc.supersedes, "status")
		if old not in ("Superseded", "Reversed"):
			frappe.db.set_value("Duty Project Decision", doc.supersedes,
								"status", "Superseded")
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def delete_decision(name):
	"""Only a decision nobody has acted on. Anything agreed is superseded."""
	require_staff()
	st = frappe.db.get_value("Duty Project Decision", name, "status")
	if st != "Proposed":
		frappe.throw(_("Only a proposed decision can be deleted. One that was agreed stays on the record and is superseded instead — that is the difference between a log and a draft."))
	frappe.delete_doc("Duty Project Decision", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


# ─────────────────────────── weekly status pack ──────────────────────────────
#
# The document a project consultant lives on, assembled from what the system
# already knows rather than typed into a deck once a week. That is the whole
# argument: theirs is written by an analyst on Friday afternoon and is a
# snapshot of what somebody remembered; this one cannot disagree with the
# system because it IS the system.

RISK_SCORE = {"Low": 1, "Medium": 2, "High": 3}


@frappe.whitelist()
def status_pack(project, days=7):
	"""Everything that happened this week, and what it means for the plan."""
	require_staff()
	back = abs(cint(days) or 7)
	since = add_days(nowdate(), -back)
	today = nowdate()

	p = frappe.db.get_value(
		"Duty Project", project,
		["name", "project_name", "customer", "room", "target_date",
		 "baseline_target_date", "rag", "rag_reason", "rag_owner", "rag_due",
		 "rag_set_on"], as_dict=True)
	if not p:
		frappe.throw(_("No such project."))

	# ---- phases, with slip against their own baseline
	phases = []
	for m in frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title", "status", "target_date", "baseline_date", "sort_order"],
		order_by="sort_order asc", limit_page_length=0):
		tasks = frappe.get_all(
			"Duty Project Task", filters={"milestone": m.name},
			fields=["name", "column"], limit_page_length=0)
		done = len([t for t in tasks if (t.column or "").lower() in ("done", "complete", "completed")])
		slip = (date_diff(m.target_date, m.baseline_date)
				if (m.target_date and m.baseline_date) else None)
		late = (date_diff(today, m.target_date)
				if (m.target_date and str(m.target_date) < today and m.status != "Approved") else None)
		phases.append({
			"title": m.title, "status": m.status,
			"target_date": str(m.target_date) if m.target_date else None,
			"baseline_date": str(m.baseline_date) if m.baseline_date else None,
			"slip_days": slip, "days_late": late,
			"done": done, "total": len(tasks),
		})

	# ---- what actually moved this week, rather than what is open
	moved = frappe.db.sql(
		"""select t.name, t.title, t.column, t.assignee, m.title as phase
		   from `tabDuty Project Task` t
		   left join `tabDuty Milestone` m on m.name = t.milestone
		   where t.project = %(p)s and t.modified >= %(since)s
		   order by t.modified desc""",
		{"p": project, "since": since}, as_dict=True)
	completed = [r for r in moved
				 if (r.column or "").lower() in ("done", "complete", "completed")]

	# ---- decisions taken in the window
	decs = frappe.get_all(
		"Duty Project Decision",
		filters={"project": project, "decided_on": [">=", since]},
		fields=["title", "status", "decided_on", "decided_by", "impact"],
		order_by="decided_on desc", limit_page_length=0)

	# ---- risks, scored so the order is defensible rather than a matter of taste
	risks = []
	for r in frappe.get_all(
		"Duty Project Risk", filters={"project": project, "status": ["!=", "Closed"]},
		fields=["title", "likelihood", "impact", "mitigation", "owner_user", "status"],
		limit_page_length=0):
		score = RISK_SCORE.get(r.likelihood, 1) * RISK_SCORE.get(r.impact, 1)
		risks.append(dict(r, score=score,
						  owner=frappe.utils.get_fullname(r.owner_user) if r.owner_user else None))
	risks.sort(key=lambda r: -r["score"])

	# ---- change requests raised or settled in the window
	# `title` is not a field on Duty Change Request — the request itself is in
	# original_request. audit_fields caught this before it reached the page.
	crs = frappe.get_all(
		"Duty Change Request", filters={"project": project, "modified": [">=", since]},
		fields=["name", "original_request", "status", "cost_impact", "timeline_impact"],
		limit_page_length=0)

	# ---- effort, reusing the same calculation the effort screen shows
	try:
		eff = project_effort(project)
	except Exception:
		eff = {}

	# ---- what is due next, which is the only forward-looking part
	nxt = frappe.db.sql(
		"""select t.title, t.due_date, t.assignee, m.title as phase
		   from `tabDuty Project Task` t
		   left join `tabDuty Milestone` m on m.name = t.milestone
		   where t.project = %(p)s and t.due_date is not null
			 and t.due_date <= %(until)s
			 and lower(coalesce(t.column,'')) not in ('done','complete','completed')
		   order by t.due_date asc limit 12""",
		{"p": project, "until": add_days(today, back)}, as_dict=True)
	for r in nxt:
		r["overdue"] = 1 if str(r["due_date"]) < today else 0
		r["assignee"] = frappe.utils.get_fullname(r["assignee"]) if r["assignee"] else None

	# the schedule question belongs in the weekly document, not only on a screen
	try:
		cp = critical_path(project)
	except Exception:
		cp = {}
	try:
		dlv = deliverables(project)
	except Exception:
		dlv = {}

	late_phases = [x for x in phases if x["days_late"]]
	golive, base = p.get("target_date"), p.get("baseline_target_date")
	return {
		"project": p.name, "project_name": p.project_name, "customer": p.customer,
		"from_date": since, "to_date": today, "days": back,
		"rag": p.rag or ("At risk" if late_phases else "On track"),
		"rag_stated": 1 if p.rag_set_on else 0,
		"rag_reason": p.rag_reason,
		"rag_owner": frappe.utils.get_fullname(p.rag_owner) if p.rag_owner else None,
		"rag_due": str(p.rag_due) if p.rag_due else None,
		"golive": str(golive) if golive else None,
		"baseline": str(base) if base else None,
		"slip_days": date_diff(golive, base) if (golive and base) else None,
		"days_to_golive": date_diff(golive, today) if golive else None,
		"phases": phases, "late_phases": late_phases,
		"completed": completed, "touched": len(moved),
		"decisions": decs,
		"risks": risks, "risks_high": [r for r in risks if r["score"] >= 6],
		"change_requests": crs,
		"effort": {"estimate": eff.get("estimate"), "actual": eff.get("actual"),
				   "burn_rate": eff.get("burn_rate"), "forecast": eff.get("forecast"),
				   "overrun": eff.get("overrun")},
		"next": nxt,
		"deliverables": {
			"accepted": dlv.get("accepted"), "total": dlv.get("total"),
			"awaiting": dlv.get("awaiting"), "overdue": dlv.get("overdue"),
			"no_criteria": dlv.get("no_criteria"),
			"recent": [r for r in (dlv.get("rows") or [])
					   if r.get("accepted_at") and str(r["accepted_at"])[:10] >= since][:6],
			"pending": [r for r in (dlv.get("rows") or [])
						if r.get("status") == "Submitted"][:6],
		},
		"critical": {
			"tasks": (cp.get("critical") or [])[-6:],
			"remaining_hours": cp.get("remaining_hours"),
			"holders": (cp.get("holders") or [])[:3],
			"unlinked": cp.get("unlinked"), "total": cp.get("total"),
		},
	}


# ────────────────────────────── critical path ────────────────────────────────
#
# blocked_by has been captured since the beginning and nothing ever computed
# what it implies. The question a reviewer asks when a date slips is "which
# task moved it", and until now nothing here could answer.
#
# blocked_by is a single link, so dependencies form CHAINS rather than a
# network. That is a real limitation and it is stated rather than hidden: this
# finds the longest chain of unfinished work, which on a chain is the critical
# path. A task blocked by two things can only record one of them.


def _chain(name, tasks, seen=None):
	"""Walk back up the blockers. Returns (path, hit_a_cycle)."""
	seen = seen or set()
	if name in seen:
		return [], True
	seen.add(name)
	b = (tasks.get(name) or {}).get("blocked_by")
	if not b or b not in tasks:
		return [name], False
	up, cyc = _chain(b, tasks, seen)
	if cyc:
		return [], True
	return up + [name], False


@frappe.whitelist()
def critical_path(project):
	"""The longest chain of unfinished work, and what it does to the date."""
	require_staff()
	rows = frappe.get_all(
		"Duty Project Task", filters={"project": project},
		fields=["name", "title", "blocked_by", "estimate_hours", "due_date",
				"column", "assignee", "milestone"], limit_page_length=0)
	tasks = {}
	for r in rows:
		tasks[r.name] = {
			"name": r.name, "title": r.title, "blocked_by": r.blocked_by,
			"est": flt(r.estimate_hours) or 0.0,
			"due": str(r.due_date) if r.due_date else None,
			"done": 1 if (r.column or "").lower() in ("done", "complete", "completed") else 0,
			"assignee": frappe.utils.get_fullname(r.assignee) if r.assignee else None,
			"milestone": r.milestone,
		}
	ms = {m.name: m.title for m in frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title"], limit_page_length=0)}

	chains, cycles = [], []
	for n in tasks:
		path, cyc = _chain(n, tasks)
		if cyc:
			cycles.append(n)
			continue
		rem = sum(tasks[x]["est"] for x in path if not tasks[x]["done"])
		chains.append({"tail": n, "path": path, "remaining": rem, "length": len(path)})
	chains.sort(key=lambda c: (-c["remaining"], -c["length"]))

	def decorate(path):
		out = []
		for x in path:
			t = dict(tasks[x])
			t["phase"] = ms.get(t.pop("milestone"))
			out.append(t)
		return out

	longest = chains[0] if chains else None
	blocking = {}
	for c in chains:
		for x in c["path"][:-1]:
			if not tasks[x]["done"]:
				blocking[x] = blocking.get(x, 0) + 1
	# what is holding up the most work — the thing to unblock first
	holders = sorted(
		[{"task": k, "title": tasks[k]["title"], "blocks": v,
		  "assignee": tasks[k]["assignee"], "due": tasks[k]["due"],
		  "overdue": 1 if (tasks[k]["due"] and tasks[k]["due"] < nowdate()) else 0}
		 for k, v in blocking.items()],
		key=lambda h: -h["blocks"])[:8]

	no_deps = len([t for t in tasks.values() if not t["blocked_by"]])
	return {
		"project": project,
		"critical": decorate(longest["path"]) if longest else [],
		"remaining_hours": longest["remaining"] if longest else 0,
		"chains": len(chains),
		"holders": holders,
		"cycles": [tasks[c]["title"] for c in cycles],
		"unlinked": no_deps,
		"total": len(tasks),
		# stated plainly: a chain is not a network, and pretending otherwise
		# would be the kind of claim a reviewer tests and breaks
		"basis": _("Each task records one blocker, so dependencies form chains rather than a network. This is the longest chain of unfinished work."),
	}


@frappe.whitelist()
def progress_curve(project):
	"""Planned against actual, week by week.

	The plan is built from due dates: work counts as planned-complete on the day
	it was due. The actual is built from completed_on. Both are weighted by
	estimated hours where they exist and by task count where they do not, and
	which one is in use is reported rather than assumed.

	COMPLETION DATES ONLY EXIST FROM THE DAY THE FIELD WAS ADDED. Tasks finished
	before that have no date, so they are counted at the start of the window and
	the number of them is returned — a curve that silently omits finished work
	would read as catastrophic underperformance.
	"""
	require_staff()
	rows = frappe.get_all(
		"Duty Project Task", filters={"project": project},
		fields=["name", "title", "due_date", "completed_on", "column", "estimate_hours"],
		limit_page_length=0)
	if not rows:
		return {"points": [], "total": 0}

	use_hours = any(flt(r.estimate_hours) for r in rows)
	weight = (lambda r: flt(r.estimate_hours) or 0.0) if use_hours else (lambda r: 1.0)
	total = sum(weight(r) for r in rows) or 1.0

	done_rows = [r for r in rows
				 if (r.column or "").lower() in ("done", "complete", "completed")]
	undated = [r for r in done_rows if not r.completed_on]

	dates = [str(r.due_date) for r in rows if r.due_date]
	dates += [str(r.completed_on)[:10] for r in done_rows if r.completed_on]
	if not dates:
		return {"points": [], "total": total, "no_dates": 1}
	start, end = min(dates), max(max(dates), nowdate())

	points, d = [], getdate(start)
	stop = getdate(end)
	guard = 0
	while d <= stop and guard < 400:
		guard += 1
		ds = str(d)
		planned = sum(weight(r) for r in rows if r.due_date and str(r.due_date) <= ds)
		actual = sum(weight(r) for r in done_rows
					 if r.completed_on and str(r.completed_on)[:10] <= ds)
		# finished before the field existed: counted from the start rather than
		# left out, or the curve would libel the team
		actual += sum(weight(r) for r in undated)
		points.append({
			"d": ds,
			"planned": round(planned * 100 / total, 1),
			"actual": round(actual * 100 / total, 1),
			"future": 1 if ds > nowdate() else 0,
		})
		d = add_days(d, 7)

	now = [p for p in points if not p["future"]]
	cur = now[-1] if now else None
	return {
		"points": points,
		"total": total,
		"basis": _("weighted by estimated hours") if use_hours else _("by task count - no estimates recorded"),
		"planned_now": cur["planned"] if cur else None,
		"actual_now": cur["actual"] if cur else None,
		"variance": round(cur["actual"] - cur["planned"], 1) if cur else None,
		"undated_done": len(undated),
		"no_due_dates": len([r for r in rows if not r.due_date]),
		"tasks": len(rows),
	}


# ────────────────────── deliverables and their acceptance ────────────────────
#
# A phase sign-off says the phase is done; it says nothing about which document
# was reviewed, by whom, or against what. That is the record a Big 4 audit asks
# for, and criteria agreed BEFORE the work starts are what stop acceptance
# becoming an argument about taste at the end.


@frappe.whitelist()
def deliverables(project, client_only=0):
	f = {"project": project}
	if cint(client_only):
		f["client_visible"] = 1
	rows = frappe.get_all(
		"Duty Project Deliverable", filters=f,
		fields=["name", "title", "milestone", "status", "owner_user", "due_date",
				"submitted_on", "criteria", "reviewer", "accepted_by", "accepted_at",
				"accept_note", "reject_reason", "artefact_url", "client_visible", "note"],
		order_by="due_date asc, creation asc", limit_page_length=0)
	ms = {m.name: m.title for m in frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title"], limit_page_length=0)}
	today = nowdate()
	for r in rows:
		r.phase = ms.get(r.milestone)
		r.owner_name = frappe.utils.get_fullname(r.owner_user) if r.owner_user else None
		r.overdue = 1 if (r.due_date and str(r.due_date) < today
						  and r.status not in ("Accepted",)) else 0
		# a deliverable with no criteria can be rejected for any reason and
		# accepted for none, so it is flagged rather than left to be discovered
		r.no_criteria = 0 if (r.criteria or "").strip() else 1
	return {
		"rows": rows,
		"accepted": len([r for r in rows if r.status == "Accepted"]),
		"awaiting": len([r for r in rows if r.status == "Submitted"]),
		"overdue": len([r for r in rows if r.overdue]),
		"no_criteria": len([r for r in rows if r.no_criteria]),
		"total": len(rows),
	}


@frappe.whitelist()
def save_deliverable(name=None, **kwargs):
	require_staff()
	allowed = ("project", "title", "milestone", "status", "owner_user", "due_date",
			   "criteria", "reviewer", "artefact_url", "client_visible", "note")
	doc = (frappe.get_doc("Duty Project Deliverable", name) if name
		   else frappe.new_doc("Duty Project Deliverable"))
	prev = doc.get("status")
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not (doc.title or "").strip():
		frappe.throw(_("Give the deliverable a name."))
	if doc.status == "Submitted" and not (doc.criteria or "").strip():
		frappe.throw(_("Set the acceptance criteria before submitting this. Without them it can be rejected for any reason and accepted for none, and the argument happens at the end instead of the beginning."))
	if doc.status == "Submitted" and prev != "Submitted":
		doc.submitted_on = now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def accept_deliverable(name, accepted_by, note=None, accept=1):
	"""Record acceptance or rejection with a name and a timestamp.

	A rejection must say which criterion failed. One that cites none is a change
	request wearing a rejection's clothes, and the difference matters
	commercially — the first is our cost, the second is theirs.
	"""
	require_staff()
	doc = frappe.get_doc("Duty Project Deliverable", name)
	if not (accepted_by or "").strip():
		frappe.throw(_("Record who accepted it. An acceptance with nobody's name against it proves nothing."))
	if cint(accept):
		doc.status = "Accepted"
		doc.accepted_by = accepted_by
		doc.accepted_at = now_datetime()
		doc.accept_note = note or None
		doc.reject_reason = None
	else:
		if not (note or "").strip():
			frappe.throw(_("Say which criterion was not met. A rejection that cites none is a change request rather than a rejection, and they are not the same thing commercially."))
		doc.status = "Rejected"
		doc.reject_reason = note
		doc.accepted_by = None
		doc.accepted_at = None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "status": doc.status}


@frappe.whitelist()
def delete_deliverable(name):
	require_staff()
	st = frappe.db.get_value("Duty Project Deliverable", name, "status")
	if st == "Accepted":
		frappe.throw(_("An accepted deliverable stays on the record. Acceptance is the thing this exists to prove."))
	frappe.delete_doc("Duty Project Deliverable", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def get_milestones_for_project(project):
	"""Phases, for pickers."""
	return frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title"], order_by="sort_order asc", limit_page_length=0)


# ─────────────────────────────── gantt ───────────────────────────────────────
#
# A bar needs a start and an end, and tasks carry only a due date. Rather than
# demand start dates before the view works at all, a missing start is derived
# from the due date and the estimate at HOURS_A_DAY, and the bar is marked as
# derived so it is never mistaken for something somebody planned.

HOURS_A_DAY = 6.0


@frappe.whitelist()
def gantt(project):
	"""Phases and tasks as bars, with baselines, dependencies and today."""
	require_staff()
	proj = frappe.db.get_value(
		"Duty Project", project,
		["name", "project_name", "target_date", "baseline_target_date"], as_dict=True)
	if not proj:
		frappe.throw(_("No such project."))

	ms = frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title", "status", "target_date", "baseline_date", "sort_order"],
		order_by="sort_order asc, target_date asc", limit_page_length=0)

	tasks = frappe.get_all(
		"Duty Project Task", filters={"project": project},
		fields=["name", "title", "milestone", "column", "assignee", "start_date",
				"due_date", "estimate_hours", "blocked_by", "urgency", "completed_on"],
		order_by="due_date asc, sort_order asc", limit_page_length=0)

	# a phase runs from the previous phase's date to its own — the only start a
	# phase actually has, since nobody enters one
	bars, prev = [], None
	for m in ms:
		start = prev or (min([str(t.start_date or t.due_date) for t in tasks
							  if (t.start_date or t.due_date)], default=None))
		bars.append({
			"kind": "phase", "id": m.name, "title": m.title, "status": m.status,
			"start": start, "end": str(m.target_date) if m.target_date else None,
			"baseline_end": str(m.baseline_date) if m.baseline_date else None,
			"slip_days": (date_diff(m.target_date, m.baseline_date)
						  if (m.target_date and m.baseline_date) else None),
			"done": len([t for t in tasks if t.milestone == m.name
						 and (t.column or "").lower() in ("done", "complete", "completed")]),
			"total": len([t for t in tasks if t.milestone == m.name]),
		})
		if m.target_date:
			prev = str(m.target_date)

	import math

	for t in tasks:
		end = str(t.due_date) if t.due_date else None
		if t.start_date:
			start, derived = str(t.start_date), 0
		elif end:
			days = max(1, int(math.ceil((flt(t.estimate_hours) or HOURS_A_DAY) / HOURS_A_DAY)))
			start, derived = str(add_days(getdate(end), -(days - 1))), 1
		else:
			start, derived = None, 1
		done = (t.column or "").lower() in ("done", "complete", "completed")
		bars.append({
			"kind": "task", "id": t.name, "title": t.title,
			"milestone": t.milestone, "column": t.column,
			"assignee": frappe.utils.get_fullname(t.assignee) if t.assignee else None,
			"start": start, "end": end, "derived": derived,
			"estimate": flt(t.estimate_hours) or None,
			"blocked_by": t.blocked_by, "urgency": t.urgency,
			"done": 1 if done else 0,
			"overdue": 1 if (end and end < nowdate() and not done) else 0,
		})

	dated = [b for b in bars if b["start"] and b["end"]]
	span_from = min([b["start"] for b in dated], default=nowdate())
	span_to = max([b["end"] for b in dated]
				  + ([str(proj.target_date)] if proj.target_date else []), default=nowdate())
	return {
		"project": proj.name, "project_name": proj.project_name,
		"golive": str(proj.target_date) if proj.target_date else None,
		"baseline": str(proj.baseline_target_date) if proj.baseline_target_date else None,
		"from": span_from, "to": span_to, "today": nowdate(),
		"bars": bars,
		"undated": len([b for b in bars if b["kind"] == "task" and not b["end"]]),
		"derived": len([b for b in bars if b["kind"] == "task" and b.get("derived") and b["end"]]),
		"hours_a_day": HOURS_A_DAY,
	}


# ─────────────────────────── recurring tasks ─────────────────────────────────

RECUR_DAYS = {"Daily": 1, "Weekly": 7, "Fortnightly": 14}
RECUR_MONTHS = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}


def _recur_next(d, frequency):
	d = getdate(d)
	if frequency in RECUR_DAYS:
		return add_days(d, RECUR_DAYS[frequency])
	return add_months(d, RECUR_MONTHS.get(frequency, 1))


@frappe.whitelist()
def recurring(project=None):
	f = {}
	if project:
		f["project"] = project
	rows = frappe.get_all(
		"Duty Recurring Task", filters=f,
		fields=["name", "title", "project", "milestone", "assignee", "frequency",
				"next_date", "ends_on", "lead_days", "urgency", "estimate_hours",
				"client_visible", "active", "skip_if_open", "description",
				"last_created", "created_count"],
		order_by="active desc, next_date asc", limit_page_length=0)
	ms = {m.name: m.title for m in frappe.get_all(
		"Duty Milestone", fields=["name", "title"], limit_page_length=0)}
	today = nowdate()
	for r in rows:
		r.phase = ms.get(r.milestone)
		r.owner_name = frappe.utils.get_fullname(r.assignee) if r.assignee else None
		r.due_in = date_diff(r.next_date, today) if r.next_date else None
		r.finished = 1 if (r.ends_on and str(r.ends_on) < today) else 0
		# whether the previous one is still sitting open, which is what decides
		# if the next is skipped
		r.open_now = frappe.db.count("Duty Project Task", {
			"recurring": r.name,
			"column": ["not in", ["Completed", "Suspended"]]})
	return {"rows": rows,
			"active": len([r for r in rows if r.active and not r.finished]),
			"blocked": len([r for r in rows if r.skip_if_open and r.open_now])}


@frappe.whitelist()
def save_recurring(name=None, **kwargs):
	require_staff()
	allowed = ("title", "project", "milestone", "assignee", "frequency", "next_date",
			   "ends_on", "lead_days", "urgency", "estimate_hours", "client_visible",
			   "active", "skip_if_open", "description")
	doc = (frappe.get_doc("Duty Recurring Task", name) if name
		   else frappe.new_doc("Duty Recurring Task"))
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not (doc.title or "").strip():
		frappe.throw(_("Give the task a name."))
	if not doc.next_date:
		frappe.throw(_("When is the next one due?"))
	if doc.ends_on and getdate(doc.ends_on) < getdate(doc.next_date):
		frappe.throw(_("It stops before the next one is due, so it would never create anything."))
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def delete_recurring(name, keep_tasks=1):
	"""Stop the rule. Tasks it already made are real work and stay by default."""
	require_staff()
	if not cint(keep_tasks):
		for t in frappe.get_all("Duty Project Task", filters={"recurring": name},
								pluck="name"):
			frappe.delete_doc("Duty Project Task", t, ignore_permissions=True)
	else:
		# the link is cleared so the tasks survive the rule going away
		for t in frappe.get_all("Duty Project Task", filters={"recurring": name},
								pluck="name"):
			frappe.db.set_value("Duty Project Task", t, "recurring", None,
								update_modified=False)
	frappe.delete_doc("Duty Recurring Task", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


def _make_one(r, due):
	doc = frappe.get_doc({
		"doctype": "Duty Project Task",
		"project": r.project, "milestone": r.milestone or None,
		"title": r.title, "description": r.description or None,
		"assignee": r.assignee or None, "due_date": due,
		"urgency": r.urgency or "Medium",
		"estimate_hours": flt(r.estimate_hours) or None,
		"client_visible": cint(r.client_visible),
		"column": "To Do", "recurring": r.name,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def run_recurring(dry_run=0):
	"""Create whatever is due, and move each rule on.

	cron: 0 6 * * *

	CATCHES UP RATHER THAN POSTING ONCE. A rule dormant while nobody looked
	should produce the instances it owed, not one and a claim to be current —
	the same reasoning as the standing orders. Capped, so a bad date cannot spin.
	"""
	today = nowdate()
	made, skipped = [], []
	for name in frappe.get_all(
		"Duty Recurring Task", filters={"active": 1}, pluck="name"):
		r = frappe.get_doc("Duty Recurring Task", name)
		for _i in range(24):
			if not r.next_date:
				break
			if r.ends_on and getdate(r.next_date) > getdate(r.ends_on):
				r.db_set("active", 0, update_modified=False)
				break
			# lead_days brings it forward: a monthly review wanted a week early
			# should appear a week early, not on the day
			appear = add_days(getdate(r.next_date), -abs(cint(r.lead_days)))
			if str(appear) > today:
				break
			if cint(r.skip_if_open) and frappe.db.count("Duty Project Task", {
					"recurring": r.name,
					"column": ["not in", ["Completed", "Suspended"]]}):
				# a weekly check nobody is doing must not become fifty open
				# tasks — the rule waits rather than piling up
				skipped.append("%s (previous still open)" % r.title)
				break
			if not cint(dry_run):
				_make_one(r, str(r.next_date))
				r.db_set("last_created", today, update_modified=False)
				r.db_set("created_count", cint(r.created_count) + 1, update_modified=False)
			made.append("%s -> %s" % (r.title, r.next_date))
			nxt = _recur_next(r.next_date, r.frequency)
			if cint(dry_run):
				break
			r.db_set("next_date", nxt, update_modified=False)
			r.reload()
	if not cint(dry_run):
		frappe.db.commit()
	print("%s: %d task(s) created, %d rule(s) waiting"
		  % ("DRY RUN" if cint(dry_run) else "DONE", len(made), len(skipped)))
	for m in made[:15]:
		print("   + %s" % m)
	for m in skipped[:8]:
		print("   . %s" % m)
	return {"created": len(made), "skipped": len(skipped), "detail": made}
