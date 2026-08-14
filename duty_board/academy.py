"""Academy commerce: catalogue, seat orders, entitlements.

Selling training needs an object that a product string cannot express: how many
people were paid for, from when, until when. That is Duty Academy Entitlement,
and it is the only thing that unlocks a Paid track.

This module carries both faces — the client administrator raising an order, and
staff approving it — so like client_room.py it is deliberately absent from the
staff-denial permission suite. Every client endpoint resolves the room from
membership as its first act, and every mutation is administrator-guarded.

Approval is manual and always will be. Money is confirmed by a person.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, today
from frappe.utils.pdf import get_pdf


def _staff_only():
	from duty_board.permissions import require_staff

	require_staff()


def _room():
	from duty_board.client_room import _client_room

	return _client_room()


def _room_admin():
	from duty_board.client_room import _require_room_admin

	return _require_room_admin()


def _settings():
	return frappe.get_cached_doc("Duty Settings")


def _approver():
	s = _settings()
	return (s.get("academy_approver") or s.get("cr_pricer") or "").strip()


def _track_modules(track):
	return frappe.get_all(
		"Duty Certification Track Module", filters={"parent": track},
		pluck="module", order_by="idx asc",
	)


def seats_used(room, track):
	"""One seat is one named learner on one track, however many courses that
	track contains. Counted from live training records, so it cannot drift."""
	mods = _track_modules(track)
	if not mods:
		return 0
	rows = frappe.get_all(
		"Duty Training Record",
		filters={"room": room, "module": ["in", mods]},
		fields=["trainee"],
	)
	return len({r.trainee for r in rows if r.trainee})


def entitlement_for(room, track):
	"""Total live seats for a room/track. Several orders accumulate. An expiry
	in the past stops counting toward NEW assignment."""
	rows = frappe.get_all(
		"Duty Academy Entitlement",
		filters={"room": room, "track": track, "status": "Active"},
		fields=["name", "seats", "expires_on"],
	)
	today_d = getdate(today())
	live = [r for r in rows if not r.expires_on or getdate(r.expires_on) >= today_d]
	expired = [r for r in rows if r.expires_on and getdate(r.expires_on) < today_d]
	return {
		"seats": sum(cint(r.seats) for r in live),
		"expired_seats": sum(cint(r.seats) for r in expired),
		"any": bool(rows),
		"expires_on": min(
			(str(r.expires_on) for r in live if r.expires_on), default=None
		),
	}


def seat_gate(room, track, new_learners):
	"""Raise unless there is room for this many additional named learners.
	Called from every path that can put somebody on a paid track."""
	if not new_learners:
		return
	access = frappe.db.get_value("Duty Certification Track", track, "access") or "Included"
	if access != "Paid":
		return
	ent = entitlement_for(room, track)
	if not ent["seats"]:
		if ent["expired_seats"]:
			frappe.throw(_("Your seats for this track have expired. Request more to continue."))
		frappe.throw(_("This track has not been purchased yet. Request seats from the catalogue."))
	left = ent["seats"] - seats_used(room, track)
	if new_learners > left:
		frappe.throw(
			_("Not enough seats: {0} left of {1}, and you are assigning {2} more people.").format(
				max(left, 0), ent["seats"], new_learners
			)
		)


# ---------------- client face ----------------


def track_catalogue(room, assignable_only=False):
	"""Every PUBLISHED client track and this room's standing against it.

	Three states, and the catalogue shows all three, because a client should see
	what exists rather than only what they already hold:
	  included  - covered by the products on their room; assign freely
	  entitled  - a Paid track with live seats; assign until the seats run out
	  offered   - not bought, or outside their products; visible with a price or
	              a note, never assignable
	"""
	from duty_board.client_room import _room_products

	prods = _room_products(room)
	out = []
	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},
		fields=["name", "title", "product", "description", "access", "seat_price",
				"who_for", "outcomes"],
		order_by="product asc, title asc",
	):
		n = frappe.db.count("Duty Certification Track Module", {"parent": t.name})
		if not n:
			continue
		access = t.access or "Included"
		paid = access == "Paid"
		included = not paid and (t.product or "").strip().lower() in prods
		ent = entitlement_for(room.name, t.name) if paid else None
		used = seats_used(room.name, t.name) if paid else 0
		left = max(ent["seats"] - used, 0) if ent else None
		assignable = included or bool(left)
		if assignable_only and not assignable:
			continue
		pending = frappe.db.get_value(
			"Duty Academy Order",
			{"room": room.name, "track": t.name, "status": "Requested"},
			["name", "seats"], as_dict=True,
		)
		course_list = []
		minutes = 0
		for m in frappe.get_all(
			"Duty Certification Track Module", filters={"parent": t.name},
			fields=["module"], order_by="idx asc",
		):
			title = frappe.db.get_value("Duty Training Module", m.module, "title") or m.module
			mins = sum(
				cint(x.est_minutes) for x in frappe.get_all(
					"Duty Lesson", filters={"module": m.module}, fields=["est_minutes"]
				)
			)
			minutes += mins
			course_list.append({"title": title, "minutes": mins})
		out.append({
			"track": t.name,
			"name": t.name,
			"who_for": t.who_for,
			"outcomes": t.outcomes,
			"course_list": course_list,
			"minutes": minutes,
			"title": t.title,
			"product": t.product,
			"description": t.description,
			"courses": n,
			"modules": n,
			"access": access,
			"included": included,
			"assignable": assignable,
			"seat_price": flt(t.seat_price),
			"seats": ent["seats"] if ent else None,
			"seats_used": used,
			"seats_left": left,
			"expires_on": ent["expires_on"] if ent else None,
			"pending": pending.name if pending else None,
			"seats_expired": ent["expired_seats"] if ent else 0,
			"pending_seats": pending.seats if pending else None,
		})
	out.sort(key=lambda r: (not r["assignable"], r["access"] != "Included", r["title"]))
	return out


@frappe.whitelist()
def academy_catalogue():
	room = _room_admin()
	return track_catalogue(room)


def _proforma_html(order, room):
	esc = frappe.utils.escape_html
	bank = (_settings().get("academy_bank_details") or "").strip()
	fmt = lambda v: frappe.utils.fmt_money(v, currency="NGN")
	return """<html><head><meta charset="utf-8"><style>
@page {{ size: A4 portrait; margin: 18mm 16mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #16211F; font-size: 12px; }}
h1 {{ font-size: 20px; margin: 0 0 2px; color: #0A473F; }}
.sub {{ color: #6B7C77; font-size: 11px; margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .8px;
	color: #6B7C77; border-bottom: 1px solid #DCE4E1; padding: 6px 4px; }}
td {{ padding: 7px 4px; border-bottom: 1px solid #F0F4F2; }}
.tot td {{ font-weight: 700; border-bottom: none; }}
.bank {{ margin-top: 22px; background: #F4F7F6; border-radius: 8px; padding: 12px 14px;
	white-space: pre-wrap; font-size: 11.5px; }}
.foot {{ margin-top: 24px; color: #6B7C77; font-size: 10px; border-top: 1px solid #DCE4E1; padding-top: 8px; }}
</style></head><body>
<h1>Proforma invoice {name}</h1>
<div class="sub">{customer} &middot; issued {issued} &middot; CloudERP.One Academy</div>
<table>
	<tr><th>Description</th><th style="text-align:center">Seats</th>
		<th style="text-align:right">Per seat</th><th style="text-align:right">Amount</th></tr>
	<tr><td>{track} &mdash; certification track ({courses} courses)</td>
		<td style="text-align:center">{seats}</td>
		<td style="text-align:right">{unit}</td>
		<td style="text-align:right">{amount}</td></tr>
	<tr><td colspan="3" style="text-align:right">VAT</td><td style="text-align:right">{vat}</td></tr>
	<tr class="tot"><td colspan="3" style="text-align:right">Total due</td>
		<td style="text-align:right">{total}</td></tr>
</table>
<div class="bank">{bank}</div>
<div class="foot">One seat entitles one named member of your staff to the full track and, on passing
each assessment, a verifiable certificate. Seats are activated once payment is confirmed.
Xlevel Retail Systems Ltd.</div>
</body></html>""".format(
		name=esc(order.name), customer=esc(room.customer or room.name),
		issued=frappe.utils.format_date(today(), "d MMMM yyyy"),
		track=esc(order.track_title), courses=len(_track_modules(order.track)),
		seats=order.seats, unit=fmt(order.unit_price), amount=fmt(order.amount),
		vat=fmt(order.vat), total=fmt(order.total),
		bank=esc(bank) or "Bank details will follow by email.",
	)


@frappe.whitelist()
def academy_request(track, seats, note=None):
	"""Raise a seat order. Files a proforma on the client's shelf, emails it
	with the bank details, and tells the approver. Grants nothing."""
	from duty_board.client_room import _post

	room = _room_admin()
	seats = cint(seats)
	if seats < 1:
		frappe.throw(_("How many seats do you need?"))
	t = frappe.db.get_value(
		"Duty Certification Track", track,
		["title", "access", "seat_price", "active", "audience"], as_dict=True,
	)
	if not t or not cint(t.active) or t.audience != "Client":
		frappe.throw(_("Not found."))
	if (t.access or "Included") != "Paid":
		frappe.throw(_("That track is already included in your subscription."))
	if frappe.db.exists("Duty Academy Order", {"room": room.name, "track": track, "status": "Requested"}):
		frappe.throw(_("You already have a request in progress for this track."))
	unit = flt(t.seat_price)
	amount = unit * seats
	rate = flt(_settings().get("academy_vat_rate") or 7.5)
	vat = round(amount * rate / 100, 2)
	order = frappe.get_doc({
		"doctype": "Duty Academy Order",
		"room": room.name, "track": track, "track_title": t.title, "seats": seats,
		"unit_price": unit, "amount": amount, "vat": vat, "total": amount + vat,
		"status": "Requested", "requested_by": frappe.session.user,
		"requested_on": now_datetime(), "note": note,
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	pdf = get_pdf(_proforma_html(order, room))
	fname = "Proforma_%s.pdf" % order.name
	f = frappe.get_doc({
		"doctype": "File", "file_name": fname, "content": pdf, "is_private": 1
	}).insert(ignore_permissions=True)
	frappe.get_doc({
		"doctype": "Client Shelf Doc", "room": room.name,
		"title": _("Proforma invoice — {0}").format(order.track_title),
		"category": _("Training"), "file_url": f.file_url, "file_name": fname, "active": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	fmt = lambda v: frappe.utils.fmt_money(v, currency="NGN")
	try:
		frappe.sendmail(
			recipients=[frappe.session.user],
			cc=[_approver()] if _approver() else None,
			subject=_("Proforma {0} — {1} ({2} seats)").format(order.name, t.title, seats),
			message="""<p>Thank you for your request.</p>
<p><b>{title}</b> &mdash; {seats} seat(s) at {unit} per seat.<br>
Amount {amount} &middot; VAT {vat} &middot; <b>Total due {total}</b></p>
<p>The proforma is attached and is also on your Documents shelf in the portal.
Payment details are on the proforma. Your seats are activated once we confirm payment.</p>
<p>&mdash; CloudERP.One Academy &middot; Xlevel Retail Systems Ltd</p>""".format(
				title=frappe.utils.escape_html(t.title), seats=seats, unit=fmt(unit),
				amount=fmt(amount), vat=fmt(vat), total=fmt(amount + vat),
			),
			attachments=[{"fname": fname, "fcontent": pdf}],
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board academy proforma email")
	try:
		_post(room, _("🧾 Seat request raised: {0} — {1} seat(s). Proforma {2} is on your Documents shelf.").format(
			t.title, seats, order.name))
	except Exception:
		pass
	try:
		from duty_board.api import _notify_user

		if _approver():
			_notify_user(_approver(), _("🧾 Academy seat request"),
				_("{0} — {1} seats · {2}").format(room.customer or room.name, seats, fmt(amount + vat)))
	except Exception:
		pass
	return {"order": order.name, "total": order.total}


@frappe.whitelist()
def academy_my_orders():
	room = _room_admin()
	return frappe.get_all(
		"Duty Academy Order",
		filters={"room": room.name},
		fields=["name", "track_title", "seats", "total", "status", "requested_on", "decline_reason"],
		order_by="creation desc", limit_page_length=25,
	)


# ---------------- staff face ----------------


@frappe.whitelist()
def orders(status=None):
	_staff_only()
	filters = {"status": status} if status else {}
	rows = frappe.get_all(
		"Duty Academy Order", filters=filters,
		fields=["name", "room", "track", "track_title", "seats", "unit_price",
				"amount", "vat", "total", "status", "requested_by", "requested_on",
				"payment_ref", "entitlement"],
		order_by="creation desc", limit_page_length=80,
	)
	for r in rows:
		r["customer"] = frappe.db.get_value("Client Room", r.room, "customer") or r.room
	return rows


@frappe.whitelist()
def order_approve(name, payment_ref=None, expires_on=None):
	"""Confirm payment and grant the seats. Deliberately manual."""
	_staff_only()
	from duty_board.client_room import _post

	o = frappe.get_doc("Duty Academy Order", name)
	if o.status != "Requested":
		frappe.throw(_("This order is already {0}.").format(o.status))
	if not (payment_ref or "").strip():
		frappe.throw(_("Record the payment reference — approval is the confirmation that money arrived."))
	ent = frappe.get_doc({
		"doctype": "Duty Academy Entitlement",
		"room": o.room, "track": o.track, "seats": o.seats,
		"granted_on": today(), "expires_on": expires_on or None,
		"status": "Active", "source_order": o.name,
	}).insert(ignore_permissions=True)
	o.db_set({
		"status": "Approved", "payment_ref": payment_ref,
		"approved_by": frappe.session.user, "approved_on": now_datetime(),
		"entitlement": ent.name,
	}, update_modified=False)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", o.room)
	try:
		_post(room, _("✅ Seats activated: {0} — {1} seat(s). Your administrator can now assign them.").format(
			o.track_title, o.seats))
	except Exception:
		pass
	try:
		frappe.sendmail(
			recipients=[o.requested_by],
			subject=_("Seats activated — {0}").format(o.track_title),
			message="""<p>Payment received, thank you.</p>
<p><b>{title}</b> &mdash; {seats} seat(s) are now active{exp}.</p>
<p>Open the portal, go to Training, and assign them to your colleagues.</p>
<p>&mdash; CloudERP.One Academy &middot; Xlevel Retail Systems Ltd</p>""".format(
				title=frappe.utils.escape_html(o.track_title), seats=o.seats,
				exp=(" until %s" % frappe.utils.format_date(expires_on, "d MMMM yyyy")) if expires_on else "",
			),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board academy approval email")
	return {"order": o.name, "entitlement": ent.name}


# ---------------- lesson questions: the tutor queue ----------------


@frappe.whitelist()
def questions(status="Open"):
	"""The queue of learner questions, oldest first — because the person who
	has waited longest is the one most likely to have given up."""
	_staff_only()
	filters = {} if status == "All" else {"status": status or "Open"}
	rows = frappe.get_all(
		"Duty Lesson Question", filters=filters,
		fields=["name", "room", "module_title", "lesson_title", "lesson", "asked_by",
				"asked_on", "question", "status", "answer", "answered_by", "published"],
		order_by="asked_on asc", limit_page_length=100,
	)
	for r in rows:
		r["customer"] = frappe.db.get_value("Client Room", r.room, "customer") or r.room
		r["who"] = frappe.utils.get_fullname(r.asked_by)
		r["waiting_days"] = (
			(getdate(today()) - getdate(r.asked_on)).days if r.asked_on else 0
		)
	return rows


@frappe.whitelist()
def question_counts():
	_staff_only()
	return {"open": frappe.db.count("Duty Lesson Question", {"status": "Open"})}


@frappe.whitelist()
def answer_question(name, answer, publish=0):
	"""Answer, notify in-app, email the learner, and optionally publish the
	thread to the chapter so nobody else has to ask it."""
	_staff_only()
	answer = (answer or "").strip()
	if len(answer) < 5:
		frappe.throw(_("Write an answer first."))
	q = frappe.get_doc("Duty Lesson Question", name)
	q.db_set({
		"answer": answer[:4000], "status": "Answered",
		"answered_by": frappe.session.user, "answered_on": now_datetime(),
		"published": 1 if cint(publish) else 0,
	}, update_modified=False)
	frappe.db.commit()
	try:
		from duty_board.api import _notify_user

		_notify_user(
			q.asked_by, _("\u2705 Your question has been answered"),
			_("{0} \u00b7 {1}").format(q.module_title or "", q.lesson_title or ""),
		)
	except Exception:
		pass
	try:
		frappe.sendmail(
			recipients=[q.asked_by],
			subject=_("Answered: your question on {0}").format(q.lesson_title or ""),
			message="""<p>Hello,</p>
<p>You asked about <b>{lesson}</b> in {module}:</p>
<blockquote style="border-left:3px solid #DCE4E1;margin:0 0 14px;padding:2px 0 2px 14px;color:#4A5A55">{question}</blockquote>
<p><b>{who} replied:</b></p>
<div style="background:#F4F7F6;border-radius:10px;padding:14px 16px;line-height:1.6">{answer}</div>
<p style="margin-top:16px">The answer is also on the lesson itself, under
<i>Questions on this lesson</i>, so you can read it alongside the material.</p>
<p>&mdash; CloudERP.One Academy</p>""".format(
				lesson=frappe.utils.escape_html(q.lesson_title or ""),
				module=frappe.utils.escape_html(q.module_title or ""),
				question=frappe.utils.escape_html((q.question or "")[:600]),
				who=frappe.utils.escape_html(frappe.utils.get_fullname(frappe.session.user)),
				answer=frappe.utils.escape_html(answer).replace("\n", "<br>"),
			),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board answer email")
	return {"ok": 1}


# ---------------- academy health: the cross-room view ----------------


def _room_health(room, customer, today_d):
	from duty_board.client_room import _last_signed_in

	members = [
		m.user for m in frappe.get_all(
			"Client Room Member", filters={"room": room, "active": 1}, fields=["user"]
		) if m.user
	]
	if not members:
		return None
	seen = _last_signed_in(members)
	never = [u for u in members if not seen.get(u)]

	recs = frappe.get_all(
		"Duty Training Record",
		filters={"room": room},
		fields=["name", "module", "trainee", "trainee_name", "status", "due_on", "creation"],
	)
	assigned = len(recs)
	complete = sum(1 for r in recs if r.status == "Completed")
	overdue = stalled = blocked = 0
	open_recs = [r for r in recs if r.status != "Completed"]
	for r in open_recs:
		if r.due_on and getdate(r.due_on) < today_d:
			overdue += 1
		if (today_d - getdate(r.creation)).days >= DORMANT_AFTER_DAYS and not frappe.db.exists(
			"Duty Lesson Progress", {"user": r.trainee, "module": r.module}
		):
			stalled += 1
	for r in open_recs:
		try:
			from duty_board.client_room import _quiz_state

			st = _quiz_state(r.module, r.trainee, r.name)
			if not st["passed"] and st["attempts_left"] == 0:
				blocked += 1
		except Exception:
			continue

	# seats bought and not yet put to use
	idle = 0
	for e in frappe.get_all(
		"Duty Academy Entitlement",
		filters={"room": room, "status": "Active"}, fields=["track", "seats", "expires_on"],
	):
		if e.expires_on and getdate(e.expires_on) < today_d:
			continue
		idle += max(cint(e.seats) - seats_used(room, e.track), 0)

	waiting = frappe.get_all(
		"Duty Academy Order", filters={"room": room, "status": "Requested"},
		fields=["name", "total"],
	)

	# worst first: the two states where a client has paid and received nothing
	# weigh heaviest, because that is where goodwill goes fastest
	score = len(never) * 4 + idle * 4 + blocked * 3 + stalled * 2 + overdue
	return {
		"room": room,
		"customer": customer or room,
		"members": len(members),
		"never": len(never),
		"never_names": [frappe.utils.get_fullname(u) for u in never[:6]],
		"assigned": assigned,
		"complete": complete,
		"rate": round(complete * 100.0 / assigned) if assigned else None,
		"overdue": overdue,
		"stalled": stalled,
		"blocked": blocked,
		"idle_seats": idle,
		"waiting_orders": len(waiting),
		"waiting_value": sum(flt(w.total) for w in waiting),
		"score": score,
	}


@frappe.whitelist()
def health():
	"""Every active room's academy standing, worst first."""
	_staff_only()
	today_d = getdate(today())
	out = []
	for r in frappe.get_all(
		"Client Room", filters={"status": "Active"}, fields=["name", "customer"]
	):
		try:
			row = _room_health(r.name, r.customer, today_d)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "duty_board academy health")
			continue
		if row:
			out.append(row)
	out.sort(key=lambda x: (-x["score"], x["customer"]))
	totals = {
		"rooms": len(out),
		"attention": sum(1 for x in out if x["score"]),
		"never": sum(x["never"] for x in out),
		"stalled": sum(x["stalled"] for x in out),
		"blocked": sum(x["blocked"] for x in out),
		"idle_seats": sum(x["idle_seats"] for x in out),
		"waiting_orders": sum(x["waiting_orders"] for x in out),
	}
	return {"rooms": out, "totals": totals}


# ---------------- nudges: the cadence that replaces a facilitator ----------------

NUDGE_REPEAT_DAYS = 7
DORMANT_AFTER_DAYS = 14


def _nudges_enabled():
	return not cint(_settings().get("academy_nudges_off"))


def _active_rooms():
	return {
		r.name for r in frappe.get_all(
			"Client Room", filters={"status": "Active"}, fields=["name"]
		)
	}


def _ever_opened(user, module):
	return bool(
		frappe.db.exists("Duty Lesson Progress", {"user": user, "module": module})
	)


def _due_lane(rec, today_d):
	"""Which of the four moments this record is standing on, if any.
	Returns a short reason string or None."""
	if not rec.due_on:
		return None
	due = getdate(rec.due_on)
	gap = (due - today_d).days
	last = getdate(rec.last_nudge_on) if rec.last_nudge_on else None
	if gap == 3:
		return "due in three days"
	if gap == 0:
		return "due today"
	if gap == -1:
		return "overdue since yesterday"
	if gap < -1:
		# weekly thereafter, counted from the last nudge rather than the due date
		if not last or (today_d - last).days >= NUDGE_REPEAT_DAYS:
			return "overdue by {0} days".format(abs(gap))
	return None


def training_nudges():
	"""Daily. bench execute duty_board.academy.training_nudges

	One message per learner per day at most, however many courses qualify."""
	if not _nudges_enabled():
		return {"skipped": "nudges are switched off in Duty Settings"}
	rooms = _active_rooms()
	if not rooms:
		return {"sent": 0}
	today_d = getdate(today())
	recs = frappe.get_all(
		"Duty Training Record",
		filters={"status": ["!=", "Completed"], "room": ["in", list(rooms)]},
		fields=["name", "room", "module", "trainee", "trainee_name", "due_on",
				"last_nudge_on", "nudge_count", "creation"],
	)
	by_user = {}
	for r in recs:
		if r.last_nudge_on and getdate(r.last_nudge_on) == today_d:
			continue  # never twice in a day, whatever the lanes say
		reason = _due_lane(r, today_d)
		if not reason and not r.due_on and not cint(r.nudge_count):
			age = (today_d - getdate(r.creation)).days
			if age >= DORMANT_AFTER_DAYS and not _ever_opened(r.trainee, r.module):
				reason = "not started"
		if reason:
			by_user.setdefault(r.trainee, []).append((r, reason))
	sent = 0
	for user, rows in by_user.items():
		titles = {
			m.name: m.title for m in frappe.get_all(
				"Duty Training Module",
				filters={"name": ["in", [r.module for r, _x in rows]]},
				fields=["name", "title"],
			)
		}
		lines = "".join(
			"<li><b>{0}</b> &mdash; {1}</li>".format(
				frappe.utils.escape_html(titles.get(r.module, r.module)), reason
			)
			for r, reason in rows
		)
		try:
			frappe.sendmail(
				recipients=[user],
				subject=_("Your training — {0} course(s) need attention").format(len(rows)),
				message="""<p>A quiet reminder about your training:</p>
<ul>{lines}</ul>
<p>Open the portal, go to Training, and pick up where you left off.</p>
<p>&mdash; CloudERP.One Academy</p>""".format(lines=lines),
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "duty_board training nudge email")
		try:
			from duty_board.api import _notify_user

			_notify_user(
				user, _("🎓 Training reminder"),
				_("{0} course(s) need your attention").format(len(rows)),
			)
		except Exception:
			pass
		for r, _reason in rows:
			frappe.db.set_value(
				"Duty Training Record", r.name,
				{"last_nudge_on": today_d, "nudge_count": cint(r.nudge_count) + 1},
				update_modified=False,
			)
		sent += 1
	frappe.db.commit()
	return {"sent": sent, "records": sum(len(v) for v in by_user.values())}


def training_admin_digest():
	"""Weekly. bench execute duty_board.academy.training_admin_digest

	One aggregated message per room to its administrators. Never per record —
	a digest that arrives every day is a digest nobody reads."""
	if not _nudges_enabled():
		return {"skipped": "nudges are switched off in Duty Settings"}
	today_d = getdate(today())
	sent = 0
	for room in _active_rooms():
		recs = frappe.get_all(
			"Duty Training Record",
			filters={"room": room, "status": ["!=", "Completed"]},
			fields=["module", "trainee", "trainee_name", "due_on", "creation"],
		)
		if not recs:
			continue
		late, idle = {}, {}
		for r in recs:
			who = r.trainee_name or frappe.utils.get_fullname(r.trainee)
			if r.due_on and getdate(r.due_on) < today_d:
				late[who] = late.get(who, 0) + 1
			elif (today_d - getdate(r.creation)).days >= DORMANT_AFTER_DAYS and not _ever_opened(
				r.trainee, r.module
			):
				idle[who] = idle.get(who, 0) + 1
		if not late and not idle:
			continue
		admins = [
			m.user for m in frappe.get_all(
				"Client Room Member",
				filters={"room": room, "active": 1, "is_admin": 1},
				fields=["user"],
			) if m.user
		]
		if not admins:
			continue
		block = ""
		if late:
			block += "<p><b>Past their due date</b></p><ul>" + "".join(
				"<li>{0} &mdash; {1} course(s)</li>".format(frappe.utils.escape_html(k), v)
				for k, v in sorted(late.items(), key=lambda kv: -kv[1])
			) + "</ul>"
		if idle:
			block += "<p><b>Assigned but never started</b></p><ul>" + "".join(
				"<li>{0} &mdash; {1} course(s)</li>".format(frappe.utils.escape_html(k), v)
				for k, v in sorted(idle.items(), key=lambda kv: -kv[1])
			) + "</ul>"
		try:
			frappe.sendmail(
				recipients=admins,
				subject=_("Training status — {0} person(s) need a word").format(
					len(set(list(late) + list(idle)))
				),
				message="""<p>Your team's training this week:</p>
{block}
<p>The full picture, and the Remind button, are on the Training tab of your portal.</p>
<p>&mdash; CloudERP.One Academy</p>""".format(block=block),
			)
			sent += 1
		except Exception:
			frappe.log_error(frappe.get_traceback(), "duty_board training digest")
	return {"rooms": sent}


def setup_academy_jobs():
	"""bench execute duty_board.academy.setup_academy_jobs
	Creates or repairs the Scheduled Job Type records. Times are SERVER time;
	adjust the cron in the Scheduled Job Type list at will."""
	jobs = [
		("duty_board.academy.training_nudges", "0 7 * * *"),
		("duty_board.academy.training_admin_digest", "0 8 * * 1"),
	]
	made = []
	for method, cron in jobs:
		name = frappe.db.get_value("Scheduled Job Type", {"method": method})
		if name:
			frappe.db.set_value(
				"Scheduled Job Type", name,
				{"frequency": "Cron", "cron_format": cron, "stopped": 0},
			)
			made.append("repaired " + method)
		else:
			frappe.get_doc({
				"doctype": "Scheduled Job Type",
				"method": method,
				"frequency": "Cron",
				"cron_format": cron,
				"stopped": 0,
			}).insert(ignore_permissions=True)
			made.append("created " + method)
	frappe.db.commit()
	return made


@frappe.whitelist()
def order_decline(name, reason=None):
	_staff_only()
	o = frappe.get_doc("Duty Academy Order", name)
	if o.status != "Requested":
		frappe.throw(_("This order is already {0}.").format(o.status))
	o.db_set({"status": "Declined", "decline_reason": reason,
			  "approved_by": frappe.session.user, "approved_on": now_datetime()},
			 update_modified=False)
	frappe.db.commit()
	return {"order": o.name}
