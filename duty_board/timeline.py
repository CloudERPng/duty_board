# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""The Delivery Accountability Timeline: one chronological, attributed record
of an engagement, assembled read-only from nine live sources. The artefact
that ends "why is this late?" — and, shown to the client throughout,
prevents the question arising.

Attribution buckets per event: client / xlevel / joint / info.
Delay arithmetic (method printed on the view):
  · client days  = dependency lateness past due (delay_split logic) +
                   CR approval waits (submitted → approved/declined/today)
  · xlevel days  = UAT defect open time (raise → resolved/today)
"""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, now_datetime, today

from duty_board.permissions import require_staff


def _ev(when, icon, text, who="info", days=None):
	return {"when": str(when)[:16], "d": str(when)[:10], "icon": icon, "text": text, "who": who, "days": days}


def _full(u):
	return frappe.utils.get_fullname(u) if u else ""


def _collect(room_name, for_client=False):
	room = frappe.get_doc("Client Room", room_name)
	ev = []
	client_days = 0
	xlevel_days = 0

	ev.append(_ev(room.creation, "🏁", _("Engagement room opened"), "info"))

	# --- milestones ---
	for m in frappe.get_all(
		"Duty Milestone",
		filters={"room": room_name},
		fields=["title", "status", "target_date", "submitted_on", "approved_by", "approved_at"],
		order_by="creation asc",
		limit_page_length=0,
	):
		if m.submitted_on:
			ev.append(_ev(m.submitted_on, "🏗", _("Phase completed by Xlevel: “{0}”").format(m.title), "xlevel"))
		if m.approved_at:
			ev.append(_ev(m.approved_at, "✍", _("Phase approved by {0}: “{1}”").format(_full(m.approved_by), m.title), "client"))

	# --- dependencies ---
	for r in frappe.get_all(
		"Duty Client Dependency",
		filters={"room": room_name},
		fields=["title", "status", "due_date", "creation", "provided_on", "received_on", "reminded_on", "remind_count", "waived_reason"],
		order_by="creation asc",
		limit_page_length=0,
	):
		due = f" · {_('needed by')} {r.due_date}" if r.due_date else ""
		ev.append(_ev(r.creation, "📋", _("Requested from client: “{0}”{1}").format(r.title, due), "info"))
		if cint(r.remind_count):
			ev.append(_ev(r.reminded_on or r.creation, "🔔", _("Client chased ×{0} for “{1}”").format(r.remind_count, r.title), "client"))
		end = r.received_on or r.provided_on
		if end:
			late = date_diff(str(end)[:10], str(r.due_date)) if r.due_date else 0
			if late and late > 0:
				client_days += late
				ev.append(_ev(end, "📨", _("Provided by client: “{0}” — {1} day(s) past due").format(r.title, late), "client", late))
			else:
				ev.append(_ev(end, "📨", _("Provided by client: “{0}”").format(r.title), "client"))
		elif r.status == "Waived":
			ev.append(_ev(r.creation, "⚪", _("Waived: “{0}” ({1})").format(r.title, r.waived_reason or "—"), "info"))
		elif r.due_date and getdate(r.due_date) < getdate(today()):
			late = date_diff(today(), str(r.due_date))
			client_days += late
			ev.append(_ev(today(), "⏳", _("Still awaited from client: “{0}” — {1} day(s) past due").format(r.title, late), "client", late))

	# --- change requests ---
	crs = frappe.get_all(
		"Duty Change Request",
		filters={"room": room_name},
		fields=["title", "status", "creation", "pricing_status", "priced_on", "priced_by",
			"submitted_on", "approved_by", "approved_at", "declined_at", "decline_reason", "delivered_at", "released"],
		order_by="creation asc",
		limit_page_length=0,
	)
	for c in crs:
		if for_client and not cint(c.released):
			continue
		ev.append(_ev(c.creation, "🔄", _("Change request drafted: “{0}”").format(c.title), "info"))
		if c.priced_on and c.pricing_status in ("Priced", "Covered by Subscription", "Goodwill"):
			lbl = {"Priced": _("priced"), "Covered by Subscription": _("covered by subscription"), "Goodwill": _("approved as goodwill")}[c.pricing_status]
			ev.append(_ev(c.priced_on, "💼", _("“{0}” {1} by Xlevel").format(c.title, lbl), "xlevel"))
		if c.submitted_on:
			ev.append(_ev(c.submitted_on, "📤", _("Sent to client for approval: “{0}”").format(c.title), "info"))
			end = c.approved_at or c.declined_at
			wait = date_diff(str(end)[:10], str(c.submitted_on)[:10]) if end else date_diff(today(), str(c.submitted_on)[:10])
			if wait and wait > 0 and (end or c.status == "Awaiting Approval"):
				client_days += wait
		if c.approved_at:
			ev.append(_ev(c.approved_at, "✍", _("Approved by {0}: “{1}”").format(_full(c.approved_by), c.title), "client"))
		if c.declined_at:
			ev.append(_ev(c.declined_at, "↩", _("Declined by client: “{0}” ({1})").format(c.title, c.decline_reason or "—"), "client"))
		if c.delivered_at:
			ev.append(_ev(c.delivered_at, "📦", _("Delivered by Xlevel: “{0}”").format(c.title), "xlevel"))

	# --- issues (raised & resolved; UAT defects feed xlevel days) ---
	for i in frappe.get_all(
		"Duty Issue",
		filters={"customer": room.customer},
		fields=["title", "status", "creation", "resolved_at", "client_confirmed_at", "client_requested", "severity"],
		order_by="creation asc",
		limit_page_length=0,
	):
		is_uat = (i.title or "").startswith("UAT ")
		ev.append(_ev(i.creation, "🐞" if is_uat else "🛠", _("{0}: “{1}”").format(_("Defect raised in testing") if is_uat else (_("Raised by client") if cint(i.client_requested) else _("Logged by Xlevel")), i.title), "client" if cint(i.client_requested) and not is_uat else "info"))
		if i.resolved_at:
			d = max(date_diff(str(i.resolved_at)[:10], str(i.creation)[:10]), 0)
			if is_uat:
				xlevel_days += d
			ev.append(_ev(i.resolved_at, "✅", _("Resolved by Xlevel: “{0}”{1}").format(i.title, _(" — {0} day(s)").format(d) if d else ""), "xlevel", d if is_uat else None))
		elif is_uat:
			xlevel_days += max(date_diff(today(), str(i.creation)[:10]), 0)
		if i.client_confirmed_at:
			ev.append(_ev(i.client_confirmed_at, "🤝", _("Resolution confirmed by client: “{0}”").format(i.title), "client"))

	# --- UAT ---
	cases = frappe.get_all(
		"Duty UAT Case",
		filters={"room": room_name},
		fields=["name", "code", "title", "status", "creation"],
		order_by="creation asc",
		limit_page_length=0,
	)
	if cases:
		first = cases[0].creation
		due = frappe.db.get_value("Client Room", room_name, "uat_due")
		ev.append(_ev(first, "🧪", _("Acceptance testing released: {0} scenario(s){1}").format(len(cases), _(" · window until {0}").format(due) if due else ""), "xlevel"))
		for c in cases:
			for a in frappe.get_all(
				"Duty UAT Result",
				filters={"parent": c.name},
				fields=["result", "on", "by_user", "on_behalf"],
				order_by="attempt asc",
			):
				icon = {"Pass": "✓", "Fail": "✗", "Blocked": "⊘"}[a.result]
				ev.append(_ev(a.on, icon, _("{0} {1}: “{2}”{3}").format(c.code or "", _("passed") if a.result == "Pass" else (_("failed") if a.result == "Fail" else _("blocked")), c.title, _(" (recorded by Xlevel on client's behalf)") if cint(a.on_behalf) else ""), "client"))
		nudged = frappe.db.get_value("Client Room", room_name, "uat_nudged_on")
		if nudged:
			ev.append(_ev(nudged, "🔔", _("Client reminded — scenarios idle"), "client"))
	s = frappe.get_all(
		"Duty UAT Signoff",
		filters={"room": room_name},
		fields=["signed_full", "signed_at", "exceptions", "passed", "waived", "total"],
		order_by="creation asc",
	)
	for x in s:
		ev.append(_ev(x.signed_at, "🏅", _("UAT SIGNED OFF by {0} — {1}/{2} passed{3}{4}").format(x.signed_full, x.passed, x.total, _(", {0} waived").format(x.waived) if x.waived else "", _(" · exceptions: {0}").format(x.exceptions) if x.exceptions else ""), "client"))

	# --- deliverable acknowledgements ---
	try:
		for dv in frappe.get_all(
			"Duty Service Deliverable",
			filters={"room": room_name, "acknowledged_on": ["is", "set"]},
			fields=["deliverable_type", "period", "acknowledged_on", "acknowledged_by"],
			order_by="acknowledged_on asc",
			limit_page_length=0,
		):
			ev.append(_ev(dv.acknowledged_on, "🧾", _("Deliverable signed off by {0}: {1} · {2}").format(_full(dv.acknowledged_by), dv.deliverable_type, dv.period), "client"))
	except Exception:
		pass

	ev = [e for e in ev if e["when"] and e["when"] != "None"]
	ev.sort(key=lambda e: e["when"])
	return {
		"customer": room.customer,
		"unit": room.unit,
		"events": ev,
		"summary": {"client_days": client_days, "xlevel_days": xlevel_days},
		"generated": now_datetime().strftime("%d %b %Y, %H:%M"),
	}


@frappe.whitelist()
def timeline(room):
	require_staff()
	return _collect(room, for_client=False)


def client_timeline(room_name):
	return _collect(room_name, for_client=True)


@frappe.whitelist()
def timeline_pdf(room):
	"""Render the timeline as a PDF, file it privately on the room, return the url."""
	require_staff()
	from frappe.utils.pdf import get_pdf

	t = _collect(room, for_client=False)
	chip = {"client": ("CLIENT", "#A96F1A"), "xlevel": ("XLEVEL", "#0E5A4A"), "info": ("", "#96A09B")}
	rows = "".join(
		f"<tr><td style='white-space:nowrap;color:#96A09B'>{e['when']}</td>"
		f"<td>{e['icon']} {frappe.utils.escape_html(e['text'])}</td>"
		f"<td style='font-size:9px;font-weight:700;letter-spacing:1px;color:{chip.get(e['who'], chip['info'])[1]}'>{chip.get(e['who'], chip['info'])[0]}</td></tr>"
		for e in t["events"]
	)
	html = f"""<html><head><style>
	body {{ font-family: Georgia, serif; color: #182420; margin: 40px 46px; }}
	.top {{ border-bottom: 3px solid #0E5A4A; padding-bottom: 12px; }}
	.brand {{ font-size: 20px; font-weight: bold; color: #0E5A4A; }}
	h1 {{ font-size: 24px; margin: 24px 0 4px; font-weight: normal; }}
	.mut {{ color: #6B7772; font-size: 12px; }}
	.sum {{ border: 1px solid #E8E5DD; padding: 10px 14px; margin: 14px 0; font-size: 13px; }}
	table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
	td {{ padding: 4px 6px; border-bottom: 1px solid #EFEDE6; vertical-align: top; }}
	</style></head><body>
	<div class="top"><span class="brand">Xlevel Retail Systems</span>
	<span style="float:right" class="mut">CloudERP.One · Delivery Record</span></div>
	<h1>Delivery Accountability Timeline</h1>
	<div class="mut">{frappe.utils.escape_html(t["customer"])} · {frappe.utils.escape_html(t["unit"] or "General")} · generated {t["generated"]} (WAT)</div>
	<div class="sum"><b>Attributed waiting time</b> — client: <b style="color:#A96F1A">{t["summary"]["client_days"]} day(s)</b> ·
	Xlevel: <b style="color:#0E5A4A">{t["summary"]["xlevel_days"]} day(s)</b><br>
	<span class="mut">Method: client days = dependency lateness past agreed dates + change-request approval waits;
	Xlevel days = acceptance-defect open time. Every line below is a recorded system event.</span></div>
	<table>{rows}</table>
	</body></html>"""
	pdf = get_pdf(html)
	fname = f"Delivery-Timeline-{t['customer'].replace(' ', '-')[:40]}-{now_datetime().strftime('%Y%m%d-%H%M')}.pdf"
	fdoc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"is_private": 1,
			"content": pdf,
			"attached_to_doctype": "Client Room",
			"attached_to_name": room,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"file_url": fdoc.file_url, "file_name": fname}
