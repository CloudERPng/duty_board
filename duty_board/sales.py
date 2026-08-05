"""Duty Board sales pipeline: the third face.

A lead's tasks ARE Daily Todos carrying a lead link — one record, visible
both on the pipeline and on the assignee's daily plan. Won/Lost archive
leads off the board without deleting anything.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today
from duty_board.permissions import require_staff

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
	require_staff()
	leads = frappe.get_all(
		"Duty Lead",
		filters={"status": "Open"},
		fields=[
			"name", "company", "lead_owner", "stage", "value",
			"contact_name", "email", "phone", "expected_close", "source", "modified",
			"erp_lead", "erp_quotation", "erp_customer", "erp_sales_order",
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
	return {"stages": STAGES, "pipeline": stages, "total": total, "show_values": sv, "radar": _radar_rows()}


@frappe.whitelist()
def create_lead(company, lead_owner, value=None, contact_name=None, email=None, phone=None, description=None, expected_close=None, source=None):
	require_staff()
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
	require_staff()
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
	require_staff()
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
	require_staff()
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
	require_staff()
	frappe.db.set_value(
		"Duty Lead", name, {"status": "Open", "closed_on": None}, update_modified=True
	)
	_auto_note(name, _("Reopened"))
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def get_closed_leads(outcome):
	require_staff()
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
	require_staff()
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
		"erp_lead": doc.get("erp_lead"),
		"erp_quotation": doc.get("erp_quotation"),
		"erp_sales_order": doc.get("erp_sales_order"),
		"files": frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Duty Lead", "attached_to_name": name},
			fields=["file_name", "file_url", "creation"],
			order_by="creation desc",
		),
		"expected_close": str(doc.expected_close) if doc.expected_close else None,
		"source": doc.source,
		"tasks": tasks,
		"notes": notes,
	}


@frappe.whitelist()
def add_lead_task(lead, description, date=None, time=None, assignee=None):
	require_staff()
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
	require_staff()
	doc = frappe.get_doc("Daily Todo", name)
	if not doc.get("lead"):
		frappe.throw(_("Not a lead task."))
	doc.status = "Done" if cint(done) else "Open"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_lead(doc.lead)


@frappe.whitelist()
def add_lead_note(lead, note):
	require_staff()
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Empty note."))
	frappe.get_doc({"doctype": "Duty Lead Note", "lead": lead, "note": note}).insert(
		ignore_permissions=True
	)
	frappe.db.commit()
	try:
		from duty_board.api import parse_mentions

		doc = frappe.get_doc("Duty Lead", lead)
		company = doc.company or lead
		me = frappe.session.user
		first = frappe.utils.get_fullname(me).split(" ")[0]
		mentioned = [m for m in parse_mentions(note) if m != me]

		participants = set()
		if doc.lead_owner:
			participants.add(doc.lead_owner)
		for a in frappe.get_all("Duty Lead Note", filters={"lead": lead}, fields=["owner"]):
			participants.add(a.owner)
		participants.discard(me)
		participants -= set(mentioned)

		for m in mentioned:
			_notify(m, _("💬 {0} mentioned you").format(first), f"💼 {company}: {note[:120]}")
		for p in participants:
			_notify(p, _("💬 {0} · 💼 {1}").format(first, company[:40]), note[:120])
	except Exception:
		pass
	frappe.publish_realtime("duty_board_note", {"kind": "lead", "id": lead})
	return get_lead(lead)


# ─────────────────── the Radar: pre-pipeline watching ───────────────────
# Zero-contact companies live HERE, never in the pipeline — a lead
# implies a conversation; the radar implies attention. Promotion is the
# one-way door between the two.

HEAT_ORDER = {"Hot": 0, "Warm": 1, "Cool": 2}


def _radar_rows():
	rows = frappe.get_all(
		"Duty Prospect",
		filters={"status": "Watching"},
		fields=["name", "company", "sector", "heat", "trigger", "est_worth", "link", "angle", "notes", "modified"],
	)
	rows.sort(key=lambda r: (HEAT_ORDER.get(r.heat, 1), (r.company or "").lower()))
	return rows


@frappe.whitelist()
def radar_add(company, sector=None, angle=None, heat="Warm", trigger=None, est_worth=None, link=None):
	require_staff()
	frappe.get_doc({
		"doctype": "Duty Prospect",
		"company": company.strip(),
		"sector": (sector or "").strip() or None,
		"angle": angle,
		"heat": heat if heat in HEAT_ORDER else "Warm",
		"trigger": trigger,
		"est_worth": flt(est_worth) if est_worth else None,
		"link": link,
		"status": "Watching",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return _radar_rows()


@frappe.whitelist()
def radar_update(name, company=None, sector=None, angle=None, heat=None, trigger=None, est_worth=None, link=None):
	require_staff()
	doc = frappe.get_doc("Duty Prospect", name)
	if company:
		doc.company = company.strip()
	if sector is not None:
		doc.sector = sector.strip() or None
	if angle is not None:
		doc.angle = angle
	if heat in HEAT_ORDER:
		doc.heat = heat
	if trigger is not None:
		doc.trigger = trigger
	if est_worth is not None:
		doc.est_worth = flt(est_worth) or None
	if link is not None:
		doc.link = link or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _radar_rows()


@frappe.whitelist()
def radar_note(name, note):
	"""Append a dated signal to the log."""
	require_staff()
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Write the signal first."))
	doc = frappe.get_doc("Duty Prospect", name)
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	stamp = frappe.utils.now_datetime().strftime("%d %b")
	doc.notes = ((doc.notes or "") + f"\n[{stamp} · {first}] {note}").strip()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return doc.notes


@frappe.whitelist()
def radar_drop(name, reason=None):
	require_staff()
	doc = frappe.get_doc("Duty Prospect", name)
	doc.status = "Dropped"
	doc.drop_reason = (reason or "").strip() or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _radar_rows()


@frappe.whitelist()
def radar_promote(name):
	"""Contact has begun: the watch ends, the pipeline takes over. Carries
	company, worth, and the whole signals log into a fresh Duty Lead."""
	require_staff()
	doc = frappe.get_doc("Duty Prospect", name)
	if doc.status != "Watching":
		frappe.throw(_("Already {0}.").format(doc.status.lower()))
	desc_bits = []
	if doc.angle:
		desc_bits.append(_("Angle: {0}").format(doc.angle))
	if doc.trigger:
		desc_bits.append(_("Trigger that opened the door: {0}").format(doc.trigger))
	if doc.notes:
		desc_bits.append(_("Signals log:") + "\n" + doc.notes)
	lead = frappe.get_doc({
		"doctype": "Duty Lead",
		"company": doc.company,
		"lead_owner": frappe.session.user,
		"stage": "New",
		"status": "Open",
		"value": doc.est_worth or None,
		"description": "\n\n".join(desc_bits) or None,
		"source": "Radar",
	}).insert(ignore_permissions=True)
	doc.status = "Promoted"
	doc.promoted_lead = lead.name
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"lead": lead.name, "radar": _radar_rows()}


@frappe.whitelist()
def radar_today():
	"""One prospect a day, rotating by ordinal date — the marketing-senses
	stimulant on My Dashboard."""
	require_staff()
	rows = _radar_rows()
	if not rows:
		return None
	import datetime as _dt

	return rows[_dt.date.today().toordinal() % len(rows)]


# ─────────────── the ERPNext bridge: lead → quotation → customer → SO ───────────────

SERVICE_ITEM = "XLV-SERVICE"


def _ensure_service_item():
	if not frappe.db.exists("Item", SERVICE_ITEM):
		frappe.get_doc({
			"doctype": "Item", "item_code": SERVICE_ITEM, "item_name": "Professional Services",
			"item_group": frappe.db.get_value("Item Group", {"is_group": 0}) or "All Item Groups",
			"is_stock_item": 0, "stock_uom": "Nos",
		}).insert(ignore_permissions=True)
	return SERVICE_ITEM


@frappe.whitelist()
def erp_lead_push(name):
	"""Materialise the Duty Lead as a real ERPNext Lead, once."""
	require_staff()
	doc = frappe.get_doc("Duty Lead", name)
	if doc.get("erp_lead") and frappe.db.exists("Lead", doc.erp_lead):
		return {"erp_lead": doc.erp_lead}
	lead = frappe.get_doc({
		"doctype": "Lead",
		"lead_name": doc.contact_name or doc.company,
		"company_name": doc.company,
		"email_id": doc.email or None,
		"mobile_no": doc.phone or None,
		"source": "Existing Customer" if doc.source == "Referral" else None,
	})
	lead.insert(ignore_permissions=True)
	doc.db_set("erp_lead", lead.name, update_modified=False)
	frappe.db.commit()
	return {"erp_lead": lead.name}


@frappe.whitelist()
def quote_create(name, items):
	"""Lines in, submitted Quotation out, default-format PDF attached to
	the Duty Lead. Lines ride a generic service Item so free-text
	descriptions price cleanly."""
	require_staff()
	doc = frappe.get_doc("Duty Lead", name)
	if not doc.get("erp_lead"):
		frappe.throw(_("Create the ERPNext lead first (ERP ⇢ Lead)."))
	rows = frappe.parse_json(items) if isinstance(items, str) else items
	rows = [r for r in (rows or []) if flt(r.get("qty")) > 0 and flt(r.get("rate")) >= 0 and (r.get("description") or "").strip()]
	if not rows:
		frappe.throw(_("Add at least one line: description, qty and rate."))
	code = _ensure_service_item()
	q = frappe.get_doc({
		"doctype": "Quotation",
		"quotation_to": "Lead",
		"party_name": doc.erp_lead,
		"items": [{
			"item_code": code,
			"item_name": (r["description"].strip())[:140],
			"description": r["description"].strip(),
			"qty": flt(r["qty"]),
			"rate": flt(r["rate"]),
		} for r in rows],
	})
	q.insert(ignore_permissions=True)
	q.submit()
	doc.db_set("erp_quotation", q.name, update_modified=False)
	try:
		pdf = frappe.get_print("Quotation", q.name, as_pdf=True)
		from frappe.utils.file_manager import save_file

		save_file(f"{q.name}.pdf", pdf, "Duty Lead", name, is_private=1)
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "quote pdf")
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	frappe.get_doc({"doctype": "Duty Lead Note", "lead": name,
		"note": _("🧾 {0} created quotation {1} ({2} line(s)) — PDF attached.").format(first, q.name, len(rows))}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"erp_quotation": q.name}


@frappe.whitelist()
def attach_proposal(name, file_url, label=None):
	"""Pin a sent proposal onto the lead's document trail."""
	require_staff()
	frappe.db.sql(
		"""update `tabFile` set attached_to_doctype='Duty Lead', attached_to_name=%s
		where file_url=%s and (attached_to_doctype is null or attached_to_doctype='')""",
		(name, file_url),
	)
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	frappe.get_doc({"doctype": "Duty Lead Note", "lead": name,
		"note": _("📎 {0} attached proposal: {1}").format(first, (label or file_url.split("/")[-1])[:120])}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def lead_won_convert(name):
	"""The finish line: Customer created, Quotation becomes a submitted
	Sales Order, Duty Lead marked Won. Ends the sales process."""
	require_staff()
	doc = frappe.get_doc("Duty Lead", name)
	if not doc.get("erp_quotation"):
		frappe.throw(_("No quotation to convert — create one first."))
	q = frappe.get_doc("Quotation", doc.erp_quotation)
	cust = doc.get("erp_customer")
	if not cust or not frappe.db.exists("Customer", cust):
		cust_doc = frappe.get_doc({
			"doctype": "Customer", "customer_name": doc.company,
			"customer_type": "Company",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}) or "All Customer Groups",
			"territory": "All Territories",
			"lead_name": doc.get("erp_lead") or None,
		})
		cust_doc.insert(ignore_permissions=True)
		cust = cust_doc.name
		doc.db_set("erp_customer", cust, update_modified=False)
	so = frappe.get_doc({
		"doctype": "Sales Order",
		"customer": cust,
		"delivery_date": frappe.utils.add_days(today(), 14),
		"items": [{
			"item_code": it.item_code, "item_name": it.item_name,
			"description": it.description, "qty": it.qty, "rate": it.rate,
			"delivery_date": frappe.utils.add_days(today(), 14),
			"prevdoc_docname": q.name,
		} for it in q.items],
	})
	so.insert(ignore_permissions=True)
	so.submit()
	doc.db_set("erp_sales_order", so.name, update_modified=False)
	doc.db_set("status", "Won", update_modified=True)
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	frappe.get_doc({"doctype": "Duty Lead Note", "lead": name,
		"note": _("🏆 {0} closed WON — customer {1}, sales order {2}. Sales process complete.").format(first, cust, so.name)}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"erp_customer": cust, "erp_sales_order": so.name}
