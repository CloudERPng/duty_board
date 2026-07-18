"""Duty Board sales pipeline: the third face.

A lead's tasks ARE Daily Todos carrying a lead link — one record, visible
both on the pipeline and on the assignee's daily plan. Won/Lost archive
leads off the board without deleting anything.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

STAGES = ["New", "Contacted", "Qualified", "Proposal", "Negotiation"]


def _sees_value():
	roles = frappe.get_roles()
	return "Sales Manager" in roles or "System Manager" in roles


def _notify(user, title, body):
	try:
		from duty_board.api import _notify_user

		_notify_user(user, title, body)
	except Exception:
		pass


@frappe.whitelist()
def get_pipeline():
	leads = frappe.get_all(
		"Duty Lead",
		filters={"status": "Open"},
		fields=[
			"name", "company", "lead_owner", "stage", "value",
			"contact_name", "email", "phone", "expected_close", "source", "modified",
		],
		order_by="modified desc",
	)
	names = [l.name for l in leads]
	task_stats, note_counts = {}, {}
	if names:
		tday = getdate(today())
		for t in frappe.get_all(
			"Daily Todo",
			filters={"lead": ["in", names]},
			fields=["lead", "status", "date"],
		):
			s = task_stats.setdefault(t.lead, {"open": 0, "overdue": 0})
			if t.status == "Open":
				s["open"] += 1
				if t.date and getdate(t.date) < tday:
					s["overdue"] += 1
		for n in frappe.get_all(
			"Duty Lead Note",
			filters={"lead": ["in", names]},
			fields=["lead", "count(name) as cnt"],
			group_by="lead",
		):
			note_counts[n.lead] = n.cnt

	sv = _sees_value()
	now = frappe.utils.now_datetime()
	tday = getdate(today())
	stages = {s: {"leads": [], "count": 0, "value": 0 if sv else None} for s in STAGES}
	for l in leads:
		l.value = flt(l.value) if sv else None
		l.stale_days = (now - l.modified).days if l.modified else 0
		del l["modified"]
		l.expected_close = str(l.expected_close) if l.expected_close else None
		l.close_overdue = bool(l.expected_close and getdate(l.expected_close) < tday)
		l.tasks_open = task_stats.get(l.name, {}).get("open", 0)
		l.tasks_overdue = task_stats.get(l.name, {}).get("overdue", 0)
		l.notes = note_counts.get(l.name, 0)
		col = stages.get(l.stage) or stages["New"]
		col["leads"].append(l)
		col["count"] += 1
		if sv:
			col["value"] += l.value
	total = {
		"count": len(leads),
		"value": sum(s["value"] for s in stages.values()) if sv else None,
	}
	return {"stages": STAGES, "pipeline": stages, "total": total, "show_values": sv}


@frappe.whitelist()
def create_lead(company, lead_owner, value=None, contact_name=None, email=None, phone=None, description=None, expected_close=None, source=None):
	company = (company or "").strip()
	if not company:
		frappe.throw(_("Give the prospect a name."))
	if not lead_owner:
		frappe.throw(_("Every prospect needs an owner."))
	doc = frappe.get_doc(
		{
			"doctype": "Duty Lead",
			"company": company,
			"lead_owner": lead_owner,
			"stage": "New",
			"status": "Open",
			"value": flt(value),
			"contact_name": contact_name,
			"email": email,
			"phone": phone,
			"description": description,
			"expected_close": expected_close or None,
			"source": source,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	if lead_owner != frappe.session.user:
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		_notify(lead_owner, _("New lead from {0}").format(first), company)
	return doc.name


@frappe.whitelist()
def update_lead(name, company=None, lead_owner=None, value=None, contact_name=None, email=None, phone=None, description=None, expected_close=None, source=None):
	doc = frappe.get_doc("Duty Lead", name)
	old_owner = doc.lead_owner
	if company and company.strip():
		doc.company = company.strip()
	if lead_owner:
		doc.lead_owner = lead_owner
	if _sees_value():
		doc.value = flt(value)
	doc.contact_name = contact_name
	doc.email = email
	doc.phone = phone
	doc.description = description
	doc.expected_close = expected_close or None
	doc.source = source
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	if doc.lead_owner not in (old_owner, frappe.session.user):
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		_notify(doc.lead_owner, _("Lead handed to you by {0}").format(first), doc.company)
	return get_lead(name)


def _auto_note(lead, text):
	try:
		frappe.get_doc({"doctype": "Duty Lead Note", "lead": lead, "note": text}).insert(
			ignore_permissions=True
		)
	except Exception:
		pass


@frappe.whitelist()
def move_lead(name, stage):
	if stage not in STAGES:
		frappe.throw(_("Unknown stage."))
	old_stage = frappe.db.get_value("Duty Lead", name, "stage")
	frappe.db.set_value("Duty Lead", name, "stage", stage, update_modified=True)
	if old_stage != stage:
		_auto_note(name, f"→ {stage}")
	frappe.db.commit()
	return get_pipeline()


@frappe.whitelist()
def close_lead(name, outcome):
	if outcome not in ("Won", "Lost"):
		frappe.throw(_("Outcome must be Won or Lost."))
	doc = frappe.get_doc("Duty Lead", name)
	doc.status = outcome
	doc.closed_on = today()
	doc.save(ignore_permissions=True)
	# retire open tasks on a closed lead
	for t in frappe.get_all("Daily Todo", filters={"lead": name, "status": "Open"}):
		frappe.delete_doc("Daily Todo", t.name, ignore_permissions=True, force=True)
	_auto_note(name, "🏆 Won" if outcome == "Won" else "✖ Lost")
	frappe.db.commit()
	if doc.lead_owner != frappe.session.user:
		_notify(doc.lead_owner, _("Lead {0}: {1}").format(_(outcome), doc.company), "")
	return get_pipeline()


@frappe.whitelist()
def reopen_lead(name):
	frappe.db.set_value(
		"Duty Lead", name, {"status": "Open", "closed_on": None}, update_modified=True
	)
	_auto_note(name, _("Reopened"))
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def get_closed_leads(outcome):
	if outcome not in ("Won", "Lost"):
		frappe.throw(_("Outcome must be Won or Lost."))
	rows = frappe.get_all(
		"Duty Lead",
		filters={"status": outcome},
		fields=["name", "company", "lead_owner", "value", "closed_on"],
		order_by="closed_on desc, modified desc",
		limit=200,
	)
	sv = _sees_value()
	for r in rows:
		r.value = flt(r.value) if sv else None
		r.closed_on = str(r.closed_on) if r.closed_on else None
	return rows


@frappe.whitelist()
def get_lead(name):
	doc = frappe.get_doc("Duty Lead", name)
	tasks = frappe.get_all(
		"Daily Todo",
		filters={"lead": name},
		fields=["name", "description", "date", "due_time", "status", "user"],
		order_by="date asc, due_time asc, creation asc",
	)
	tday = getdate(today())
	for t in tasks:
		t.date = str(t.date) if t.date else None
		t.due_time = str(t.due_time)[:5] if t.due_time else None
		t.overdue = bool(t.date and t.status == "Open" and getdate(t.date) < tday)
	notes = frappe.get_all(
		"Duty Lead Note",
		filters={"lead": name},
		fields=["note", "owner", "creation"],
		order_by="creation asc",
	)
	for n in notes:
		n.who = frappe.utils.get_fullname(n.owner)
		n.when = str(n.creation)
	return {
		"name": doc.name,
		"company": doc.company,
		"lead_owner": doc.lead_owner,
		"stage": doc.stage,
		"status": doc.status,
		"value": flt(doc.value) if _sees_value() else None,
		"can_edit_value": _sees_value(),
		"contact_name": doc.contact_name,
		"email": doc.email,
		"phone": doc.phone,
		"description": doc.description,
		"expected_close": str(doc.expected_close) if doc.expected_close else None,
		"source": doc.source,
		"tasks": tasks,
		"notes": notes,
	}


@frappe.whitelist()
def add_lead_task(lead, description, date=None, time=None, assignee=None):
	description = (description or "").strip()
	if not description:
		frappe.throw(_("Describe the task."))
	doc = frappe.get_doc("Duty Lead", lead)
	assignee = assignee or doc.lead_owner
	from duty_board.api import user_today

	target_today = user_today(assignee)
	d = getdate(date) if date else target_today
	if d < target_today:
		d = target_today
	frappe.get_doc(
		{
			"doctype": "Daily Todo",
			"user": assignee,
			"date": d,
			"description": description,
			"status": "Open",
			"due_time": time or None,
			"assigned_by": frappe.session.user if frappe.session.user != assignee else None,
			"lead": lead,
			"lead_title": doc.company,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	if assignee != frappe.session.user:
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		_notify(assignee, _("Lead task from {0}").format(first), f"{doc.company}: {description}")
	return get_lead(lead)


@frappe.whitelist()
def toggle_lead_task(name, done):
	doc = frappe.get_doc("Daily Todo", name)
	if not doc.get("lead"):
		frappe.throw(_("Not a lead task."))
	doc.status = "Done" if cint(done) else "Open"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_lead(doc.lead)


@frappe.whitelist()
def add_lead_note(lead, note):
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Empty note."))
	frappe.get_doc({"doctype": "Duty Lead Note", "lead": lead, "note": note}).insert(
		ignore_permissions=True
	)
	frappe.db.commit()
	try:
		from duty_board.api import parse_mentions

		company = frappe.db.get_value("Duty Lead", lead, "company") or lead
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		for m in parse_mentions(note):
			if m != frappe.session.user:
				_notify(
					m,
					_("💬 {0} mentioned you").format(first),
					f"💼 {company}: {note[:120]}",
				)
	except Exception:
		pass
	return get_lead(lead)
