# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Commercial layer: client dependencies, change-request pricing gate,
cost-to-serve, and room scope. New domain per the modularisation rule —
this does not live in the monoliths.

Model: subscriptions are the revenue and include unlimited in-scope support;
change requests are the only billable object, priced exclusively by the CR
pricer (Duty Settings), and invisible to clients until released.
"""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, get_fullname, now_datetime, today

from duty_board.permissions import require_staff


def _post_room(room_name, text):
	from duty_board.client_room import _post

	_post(frappe.get_doc("Client Room", room_name), text)


def _notify(user, title, body):
	try:
		from duty_board.api import _notify_user

		_notify_user(user, title, body)
	except Exception:
		pass


# ---------------- client dependency register ----------------


@frappe.whitelist()
def deps_list(room=None):
	require_staff()
	filters = {}
	if room:
		filters["room"] = room
	rows = frappe.get_all(
		"Duty Client Dependency",
		filters=filters,
		fields=[
			"name", "room", "title", "category", "status", "detail", "client_owner",
			"due_date", "requested_by", "provided_on", "provided_note", "received_on",
			"reminded_on", "remind_count", "blocks", "creation",
		],
		order_by="status asc, due_date asc, creation asc",
		limit_page_length=0,
	)
	tdy = today()
	customers = {}
	for r in rows:
		if r.room not in customers:
			customers[r.room] = frappe.db.get_value("Client Room", r.room, "customer")
		r["customer"] = customers[r.room]
		r["age_days"] = date_diff(tdy, str(r.creation)[:10])
		r["overdue"] = 1 if (r.due_date and r.status in ("Awaiting", "Provided") and str(r.due_date) < tdy) else 0
		r["days_late"] = date_diff(tdy, str(r.due_date)) if r["overdue"] else 0
	return rows


@frappe.whitelist()
def dep_add(room, title, category=None, detail=None, due_date=None, client_owner=None, blocks=None):
	require_staff()
	doc = frappe.get_doc(
		{
			"doctype": "Duty Client Dependency",
			"room": room,
			"title": (title or "").strip()[:140],
			"category": category or "Other",
			"detail": (detail or "").strip() or None,
			"due_date": due_date or None,
			"client_owner": (client_owner or "").strip() or None,
			"blocks": (blocks or "").strip() or None,
			"requested_by": frappe.session.user,
			"status": "Awaiting",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	_post_room(room, _("📋 We need something from you: “{0}”{1} — see Awaiting from you on your portal home.").format(
		doc.title, _(" by {0}").format(doc.due_date) if doc.due_date else ""))
	return deps_list(room)


@frappe.whitelist()
def dep_receive(name):
	"""Staff confirm the item actually arrived and is usable."""
	require_staff()
	doc = frappe.get_doc("Duty Client Dependency", name)
	doc.status = "Received"
	doc.received_on = now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_post_room(doc.room, _("✅ Received with thanks: “{0}”").format(doc.title))
	return deps_list(doc.room)


@frappe.whitelist()
def dep_reopen(name, note=None):
	"""What the client provided wasn't usable — back to Awaiting."""
	require_staff()
	doc = frappe.get_doc("Duty Client Dependency", name)
	doc.status = "Awaiting"
	doc.provided_on = None
	doc.provided_note = (note or "").strip() or doc.provided_note
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_post_room(doc.room, _("↩ Still needed: “{0}”{1}").format(doc.title, f" — {note}" if note else ""))
	return deps_list(doc.room)


@frappe.whitelist()
def dep_waive(name, reason=None):
	require_staff()
	doc = frappe.get_doc("Duty Client Dependency", name)
	doc.status = "Waived"
	doc.waived_reason = (reason or "").strip()[:140] or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return deps_list(doc.room)


@frappe.whitelist()
def dep_remind(name):
	require_staff()
	doc = frappe.get_doc("Duty Client Dependency", name)
	if doc.status not in ("Awaiting", "Provided"):
		frappe.throw(_("Nothing to remind about."))
	doc.reminded_on = today()
	doc.remind_count = cint(doc.remind_count) + 1
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_post_room(doc.room, _("🔔 A kind reminder — still awaiting from you: “{0}”{1}").format(
		doc.title, _(" (due {0})").format(doc.due_date) if doc.due_date else ""))
	return deps_list(doc.room)


def client_deps(room_name):
	"""Portal payload: open + recently closed dependencies for the room."""
	rows = frappe.get_all(
		"Duty Client Dependency",
		filters={"room": room_name, "status": ["in", ["Awaiting", "Provided", "Received"]]},
		fields=["name", "title", "category", "status", "detail", "due_date", "provided_note", "creation"],
		order_by="status asc, due_date asc",
		limit_page_length=0,
	)
	tdy = today()
	out = []
	for r in rows:
		if r.status == "Received" and date_diff(tdy, str(r.creation)[:10]) > 30:
			continue
		r["overdue"] = 1 if (r.due_date and r.status == "Awaiting" and str(r.due_date) < tdy) else 0
		out.append(r)
	return out


def client_provide(room_name, name, note=None):
	doc = frappe.get_doc("Duty Client Dependency", name)
	if doc.room != room_name:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if doc.status not in ("Awaiting", "Provided"):
		frappe.throw(_("This item is already settled."))
	doc.status = "Provided"
	doc.provided_on = now_datetime()
	doc.provided_note = (note or "").strip()[:300] or doc.provided_note
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_post_room(room_name, _("📨 {0} marked “{1}” as provided{2}").format(
		get_fullname(frappe.session.user), doc.title, f" — {note.strip()}" if note and note.strip() else ""))
	if doc.requested_by:
		_notify(doc.requested_by, _("📋 Dependency provided"), doc.title)
	return client_deps(room_name)


def delay_split(room_name):
	"""Vendor vs client delay evidence: days each open/received dependency sat
	past due, plus totals. The argument-ending number."""
	rows = frappe.get_all(
		"Duty Client Dependency",
		filters={"room": room_name},
		fields=["title", "status", "due_date", "received_on", "provided_on", "creation"],
		limit_page_length=0,
	)
	client_days = 0
	for r in rows:
		if not r.due_date:
			continue
		end = str(r.received_on or r.provided_on or "")[:10] or today()
		late = date_diff(end, str(r.due_date))
		if late > 0:
			client_days += late
	return {"client_delay_days": client_days, "items": len(rows)}


# ---------------- change-request pricing gate ----------------


def _pricer_users():
	s = frappe.get_single("Duty Settings")
	out = [(s.get("cr_pricer") or "").strip().lower()]
	if (s.get("cr_pricer_deputy") or "").strip():
		out.append(s.get("cr_pricer_deputy").strip().lower())
	return [u for u in out if u]


def _require_pricer():
	require_staff()
	if frappe.session.user.lower() not in _pricer_users():
		frappe.throw(_("Only the CR pricer can do this."), frappe.PermissionError)


@frappe.whitelist()
def pricing_queue():
	"""The pricer's desk: everything awaiting pricing, oldest first, with age."""
	require_staff()
	if frappe.session.user.lower() not in _pricer_users():
		return {"pricer": 0}
	rows = frappe.get_all(
		"Duty Change Request",
		filters={"pricing_status": "Awaiting Pricing", "status": ["!=", "Declined"]},
		fields=["name", "room", "title", "original_request", "reason", "creation", "source_type"],
		order_by="creation asc",
		limit_page_length=0,
	)
	tdy = today()
	for r in rows:
		r["customer"] = frappe.db.get_value("Client Room", r.room, "customer")
		r["age_days"] = date_diff(tdy, str(r.creation)[:10])
	return {"pricer": 1, "queue": rows}


@frappe.whitelist()
def chreq_price(name, decision, price=None, estimate_hours=None, note=None):
	"""The single commercial gate. Decisions:
	  Priced                → quotation set, released to client for approval
	  Covered by Subscription / Goodwill → released, work may proceed, no charge
	  Rejected / Deferred   → stays internal; client never sees a half-thought
	"""
	_require_pricer()
	valid = ["Priced", "Covered by Subscription", "Goodwill", "Rejected", "Deferred"]
	if decision not in valid:
		frappe.throw(_("Decision must be one of: {0}").format(", ".join(valid)))
	doc = frappe.get_doc("Duty Change Request", name)
	doc.pricing_status = decision
	doc.priced_by = frappe.session.user
	doc.priced_on = now_datetime()
	if estimate_hours:
		doc.estimate_hours = flt(estimate_hours)
	if decision == "Priced":
		if not flt(price):
			frappe.throw(_("A priced CR needs a price."))
		doc.quotation = flt(price)
		doc.released = 1
		doc.invoice_status = "To Invoice"
		# releasing IS the submission: put it in front of the client formally
		if doc.status in ("Draft",):
			doc.status = "Awaiting Approval"
			doc.submitted_on = now_datetime()
	elif decision in ("Covered by Subscription", "Goodwill"):
		doc.released = 1
		doc.quotation = 0
		doc.invoice_status = ""
	else:
		doc.released = 0
	if note:
		doc.approval_note = (note or "").strip()[:300]
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	if decision == "Priced":
		_post_room(doc.room, _("💼 Change request “{0}” has been quoted — please review and approve on your portal.").format(doc.title))
		try:
			from duty_board.client_room import _push_room_clients

			_push_room_clients(
				frappe.get_doc("Client Room", doc.room),
				_("💼 Change request awaits your approval · Xlevel"),
				doc.title[:120],
			)
		except Exception:
			pass
	elif decision in ("Covered by Subscription", "Goodwill"):
		_post_room(doc.room, _("💼 Change request “{0}”: {1} — no charge; work can proceed.").format(
			doc.title, _("covered by your subscription") if decision == "Covered by Subscription" else _("approved as goodwill")))
	return pricing_queue()


@frappe.whitelist()
def chreq_set_invoice(name, invoice_status):
	_require_pricer()
	if invoice_status not in ("To Invoice", "Invoiced", "Paid", ""):
		frappe.throw(_("Bad status."))
	frappe.db.set_value("Duty Change Request", name, "invoice_status", invoice_status or None, update_modified=False)
	frappe.db.commit()
	return {"ok": 1}


def work_may_proceed(doc):
	"""The gate condition: covered/goodwill, or priced AND client-approved."""
	ps = doc.get("pricing_status") or "Awaiting Pricing"
	if ps in ("Covered by Subscription", "Goodwill"):
		return True
	if ps == "Priced" and doc.get("approved_at"):
		return True
	return False


def notify_pricer_new_cr(doc):
	customer = frappe.db.get_value("Client Room", doc.room, "customer")
	for u in _pricer_users():
		_notify(u, _("💼 CR awaiting pricing"), f"{customer}: {doc.title}")


# ---------------- cost-to-serve ----------------


@frappe.whitelist()
def cost_to_serve(months=1):
	"""Per customer: attention consumed (work-session hours split by kind) vs
	known fees. Unlimited support makes this THE pricing instrument: it shows
	which subscriptions are underpriced for the load they generate."""
	require_staff()
	from duty_board.client_room import _staff_only  # manager check parity with Books money views
	from duty_board.accounting import _books_manager

	if not _books_manager():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	months = max(1, min(cint(months) or 1, 12))
	since = frappe.utils.add_months(today(), -months)
	rows = frappe.db.sql(
		"""
		select customer,
			sum(duration) as total_secs,
			sum(case when coalesce(duty_issue, '') != '' then duration else 0 end) as support_secs,
			sum(case when coalesce(project_task, '') != '' then duration else 0 end) as delivery_secs,
			count(distinct user) as staff_count
		from `tabWork Session`
		where coalesce(customer, '') != '' and start_time >= %s and coalesce(duration, 0) > 0
		group by customer
		order by total_secs desc
		""",
		(since,),
		as_dict=True,
	)
	rate = flt(frappe.db.get_single_value("Duty Settings", "staff_cost_rate"))
	fees_ok = True
	out = []
	for r in rows:
		hours = round(flt(r.total_secs) / 3600.0, 1)
		fee = None
		try:
			fee = flt(frappe.db.get_value("Customer", r.customer, "accounting_fees")) or None
		except Exception:
			fees_ok = False
		cost = round(hours * rate) if rate else None
		out.append(
			{
				"customer": r.customer,
				"hours": hours,
				"support_hours": round(flt(r.support_secs) / 3600.0, 1),
				"delivery_hours": round(flt(r.delivery_secs) / 3600.0, 1),
				"other_hours": round((flt(r.total_secs) - flt(r.support_secs) - flt(r.delivery_secs)) / 3600.0, 1),
				"staff_count": r.staff_count,
				"monthly_fee": fee,
				"cost": cost,
				"fee_covers": (round(flt(fee) * months) >= cost) if (fee and cost) else None,
			}
		)
	return {"rows": out, "months": months, "rate": rate, "since": since}


# ---------------- room scope ----------------


@frappe.whitelist()
def set_room_scope(name, scope_note=None, support_plan=None):
	require_staff()
	vals = {}
	if scope_note is not None:
		vals["scope_note"] = (scope_note or "").strip()[:600] or None
	if support_plan is not None:
		vals["support_plan"] = (support_plan or "").strip()[:140] or None
	if vals:
		frappe.db.set_value("Client Room", name, vals, update_modified=False)
		frappe.db.commit()
	return {"ok": 1}
