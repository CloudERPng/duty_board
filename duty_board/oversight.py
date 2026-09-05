"""Oversight — one screen per customer, for the person who owns the relationship.

WHY THIS EXISTS SEPARATELY FROM PROJECTS.

The Projects face is organised by project, which is the right shape for the
person delivering one. It is the wrong shape for the person who owns the
customer, because a customer with three projects and a client room appears in
four places and nowhere as a whole. This face inverts that: customer first,
everything they have underneath.

WHAT IT DELIBERATELY DOES NOT DO.

It does not reimplement task actions. Start, complete, reassign, reschedule and
create all call the same whitelisted functions the Projects face calls, so a
task moved here behaves identically — the same work sessions, the same activity
trail, the same permission checks, the same client-visibility rules. A second
implementation would drift within a month.

It also does not invent a task type. There is one task doctype and it hangs off
a project; a customer with no project has nothing to hold a task, which is why
create asks for a project when the customer has more than one and refuses when
they have none rather than quietly creating a stray.

LISTING RULE: customers with at least one Client Room, per the request. That is
narrower than all customers and wider than all projects, and it is the right
population — a room is the thing that says an engagement exists.
"""

import frappe
from frappe import _

OPEN_COLUMNS = ("To Do", "In Progress", "Suspended")


def _zero():
	"""Issue and project-task counts kept apart.

	They were summed into one 'open' figure, which hid the split the person
	doing oversight actually needs — a customer with 40 project tasks and no
	tickets is a different situation from one with 40 tickets.
	"""
	return {
		"open": 0, "in_progress": 0, "overdue": 0, "unassigned": 0,
		"issues": 0, "issues_overdue": 0, "issues_unassigned": 0, "tasks": 0,
	}


def _require_oversight():
	"""Staff-and-above only. Consultants see their own projects, not a portfolio."""
	from duty_board.permissions import require_staff

	require_staff()


@frappe.whitelist()
def customers():
	"""Every customer with at least one Client Room, with what is outstanding.

	One query per doctype rather than per customer — the counts are assembled in
	Python because a portfolio of a few hundred customers does not justify the
	round trips, and the alternative was a per-customer count query in a loop.
	"""
	_require_oversight()

	rooms = frappe.get_all(
		"Client Room",
		filters={"status": ["!=", "Archived"]},
		fields=["name", "customer", "status", "is_financial_room"],
	)
	by_customer = {}
	for r in rooms:
		if not r.customer:
			continue
		by_customer.setdefault(r.customer, {"rooms": [], "projects": []})["rooms"].append(r.name)

	if not by_customer:
		return []

	names = list(by_customer)
	projects = frappe.get_all(
		"Duty Project",
		filters={"customer": ["in", names], "status": ["!=", "Archived"]},
		fields=["name", "project_name", "customer", "status", "target_date"],
	)
	pj_by_name = {}
	for p in projects:
		by_customer[p.customer]["projects"].append(p)
		pj_by_name[p.name] = p.customer

	counts = {}
	# Issues hang off the customer directly rather than off a project, so a
	# customer with no project can still have work outstanding. Counting them
	# here is why this face shows a number the Projects face cannot.
	today = frappe.utils.nowdate()
	# assignees is a child Table and cannot be selected as a column — the count of
	# unassigned issues comes from one query against the child doctype instead.
	open_issues = frappe.get_all(
		"Duty Issue",
		filters={"customer": ["in", names], "status": ["in", ["Open", "In Progress"]]},
		fields=["name", "customer", "status", "due_date"],
	)
	assigned = set()
	if open_issues:
		assigned = {
			r.parent for r in frappe.get_all(
				"Duty Issue Assignee",
				filters={"parent": ["in", [i.name for i in open_issues]]},
				fields=["parent"],
			)
		}
	for i in open_issues:
		c = counts.setdefault(i.customer, _zero())
		c["open"] += 1
		c["issues"] += 1
		if i.status == "In Progress":
			c["in_progress"] += 1
		if i.due_date and str(i.due_date) < today:
			c["overdue"] += 1
			c["issues_overdue"] += 1
		if i.name not in assigned:
			c["unassigned"] += 1
			c["issues_unassigned"] += 1

	if pj_by_name:
		rows = frappe.get_all(
			"Duty Project Task",
			filters={"project": ["in", list(pj_by_name)], "column": ["in", list(OPEN_COLUMNS)]},
			fields=["name", "project", "column", "due_date", "assignee"],
		)
		for t in rows:
			cust = pj_by_name.get(t.project)
			if not cust:
				continue
			c = counts.setdefault(cust, _zero())
			c["open"] += 1
			c["tasks"] += 1
			if t.column == "In Progress":
				c["in_progress"] += 1
			if t.due_date and str(t.due_date) < today and t.column != "Completed":
				c["overdue"] += 1
			if not t.assignee:
				c["unassigned"] += 1

	out = []
	for cust, d in by_customer.items():
		c = counts.get(cust, {})
		out.append({
			"customer": cust,
			"rooms": len(d["rooms"]),
			"room": d["rooms"][0] if len(d["rooms"]) == 1 else None,
			"projects": len(d["projects"]),
			"project": d["projects"][0].name if len(d["projects"]) == 1 else None,
			"open": c.get("open", 0),
			"in_progress": c.get("in_progress", 0),
			"overdue": c.get("overdue", 0),
			"unassigned": c.get("unassigned", 0),
			"issues": c.get("issues", 0),
			"issues_overdue": c.get("issues_overdue", 0),
			"issues_unassigned": c.get("issues_unassigned", 0),
			"tasks": c.get("tasks", 0),
		})
	# worst first: overdue, then open, then alphabetical — the point of the screen
	# is to show where attention is needed rather than to be a directory
	out.sort(key=lambda r: (-r["overdue"], -r["open"], (r["customer"] or "").lower()))
	return out


@frappe.whitelist()
def customer_tasks(customer, include_done=0):
	"""Every open task across that customer's projects, plus what create needs.

	Returns the projects too, because creating a task requires one and the face
	should not make the user go elsewhere to find out which exist.
	"""
	_require_oversight()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("No such customer."))

	projects = frappe.get_all(
		"Duty Project",
		filters={"customer": customer, "status": ["!=", "Archived"]},
		fields=["name", "project_name", "status", "target_date"],
		order_by="creation asc",
	)
	rooms = frappe.get_all(
		"Client Room",
		filters={"customer": customer, "status": ["!=", "Archived"]},
		fields=["name", "status", "is_financial_room"],
	)

	today = frappe.utils.nowdate()
	tasks = []
	if projects:
		cols = list(OPEN_COLUMNS) + (["Completed"] if int(include_done or 0) else [])
		pj_titles = {p.name: p.project_name for p in projects}
		rows = frappe.get_all(
			"Duty Project Task",
			filters={"project": ["in", list(pj_titles)], "column": ["in", cols]},
			fields=["name", "project", "title", "column", "assignee", "due_date",
					"urgency", "milestone", "awaiting_client", "client_visible",
					"estimate_hours", "blocked_by", "modified"],
			order_by="due_date asc, modified desc",
			limit_page_length=0,
		)
		for t in rows:
			t.project_title = pj_titles.get(t.project)
			t.overdue = bool(t.due_date and str(t.due_date) < today and t.column != "Completed")
			t.assignee_name = frappe.utils.get_fullname(t.assignee) if t.assignee else None
			tasks.append(t)

		# who is on the clock right now, in one query rather than per task
		live = frappe.get_all(
			"Work Session",
			filters={"project_task": ["in", [t.name for t in tasks]],
					 "end_time": ["is", "not set"]},
			fields=["project_task", "user"],
		) if tasks else []
		on_now = {r.project_task: frappe.utils.get_fullname(r.user) for r in live}
		for t in tasks:
			t.working_by = on_now.get(t.name)

	# Issues, which the first version of this face missed entirely. They link to
	# the customer directly rather than through a project, so they are a separate
	# fetch and they are the items a client actually raises — leaving them out
	# made the screen look calm while the customer was waiting.
	issues = []
	i_rows = frappe.get_all(
		"Duty Issue",
		filters={"customer": customer,
				 "status": ["in", ["Open", "In Progress"] + (["Resolved"] if int(include_done or 0) else [])]},
		fields=["name", "title", "status", "severity", "due_date", "raised_by",
				"client_requested", "client_visible", "issue_type", "work_started_at",
				"acknowledged_at", "sla_res_due", "modified"],
		order_by="due_date asc, modified desc",
		limit_page_length=0,
	)
	if i_rows:
		# assignees are a child table; one query rather than one per issue
		amap = {}
		for a in frappe.get_all(
			"Duty Issue Assignee",
			filters={"parent": ["in", [r.name for r in i_rows]]},
			fields=["parent", "user"],
		):
			amap.setdefault(a.parent, []).append(a.user)
		live = {r.duty_issue for r in frappe.get_all(
			"Work Session",
			filters={"duty_issue": ["in", [r.name for r in i_rows]],
					 "end_time": ["is", "not set"]},
			fields=["duty_issue"],
		)}
		for i in i_rows:
			users = amap.get(i.name) or []
			i.assignee = users[0] if users else None
			i.assignee_name = ", ".join(frappe.utils.get_fullname(u) for u in users) or None
			i.overdue = bool(i.due_date and str(i.due_date) < today)
			i.working = i.name in live
			i.raised_by_name = frappe.utils.get_fullname(i.raised_by) if i.raised_by else None
			issues.append(i)

	return {
		"customer": customer,
		"projects": projects,
		"rooms": rooms,
		"tasks": tasks,
		"issues": issues,
		"staff": _staff_options(),
	}


def _staff_options():
	"""Assignable users: staff and consultants together.

	list_consultants() alone would be wrong here — it returns only the consultant
	role, and oversight reassigns to staff at least as often. The two lists are
	merged and deduped so the picker matches who can actually hold a task.
	"""
	seen, out = set(), []
	try:
		from duty_board.projects import list_consultants

		for r in list_consultants() or []:
			if r["user"] not in seen:
				seen.add(r["user"])
				out.append(r)
	except Exception:
		pass
	for u in frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User",
				 "name": ["not in", ["Administrator", "Guest"]]},
		fields=["name as user", "full_name"],
		limit_page_length=0,
	):
		if u["user"] not in seen:
			seen.add(u["user"])
			out.append(u)
	return sorted(out, key=lambda x: (x.get("full_name") or x["user"]).lower())
