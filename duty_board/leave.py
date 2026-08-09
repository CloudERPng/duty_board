"""Leave management — Duty Board native, replacing ERPNext leave.

Rules (locked at design time): entitlement per user in Duty Settings'
user-rate table (annual_leave_days, WORK days); weekdays only; no
carry-over (balance is per calendar YEAR of the leave's start date);
full days only; System Managers approve; staff cancel their own future
leave, admins cancel anything.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from duty_board.permissions import require_staff


def _is_admin(user=None):
	return "System Manager" in frappe.get_roles(user or frappe.session.user)


def holidays():
	"""Public-holiday dates from Duty Settings (Duty Holiday child rows)."""
	try:
		s = frappe.get_cached_doc("Duty Settings")
		return {getdate(h.holiday_date) for h in (s.get("public_holidays") or []) if h.holiday_date}
	except Exception:
		return set()


def _workdays(start, end):
	"""Weekdays (Mon-Fri) inclusive between two dates, public holidays
	excluded — a holiday inside a leave range costs no leave day."""
	s, e = getdate(start), getdate(end)
	if e < s:
		return 0
	hols = holidays()
	n, d = 0, s
	while d <= e:
		if d.weekday() < 5 and d not in hols:
			n += 1
		d += timedelta(days=1)
	return n


def _entitlement(user):
	row = frappe.get_all(
		"Duty User Rate",
		filters={"user": user, "parenttype": "Duty Settings"},
		fields=["annual_leave_days"],
		limit=1,
	)
	return cint(row[0].annual_leave_days) if row else 0


def _taken(user, year):
	rows = frappe.get_all(
		"Duty Leave Request",
		filters={"user": user, "status": "Approved"},
		fields=["work_days", "start_date"],
	)
	return sum(cint(r.work_days) for r in rows if getdate(r.start_date).year == year)


def _overlaps(user, start, end, exclude=None):
	filters = {
		"user": user,
		"status": ["in", ["Pending", "Approved"]],
		"start_date": ["<=", end],
		"end_date": [">=", start],
	}
	if exclude:
		filters["name"] = ["!=", exclude]
	return bool(frappe.get_all("Duty Leave Request", filters=filters, limit=1))


def is_on_leave(user, date=None):
	d = getdate(date or today())
	return bool(
		frappe.get_all(
			"Duty Leave Request",
			filters={
				"user": user,
				"status": "Approved",
				"start_date": ["<=", d],
				"end_date": [">=", d],
			},
			limit=1,
		)
	)


def users_on_leave(user_ids, date=None):
	d = getdate(date or today())
	rows = frappe.get_all(
		"Duty Leave Request",
		filters={
			"user": ["in", list(user_ids)],
			"status": "Approved",
			"start_date": ["<=", d],
			"end_date": [">=", d],
		},
		fields=["user"],
	)
	return {r.user for r in rows}


def _my_requests(user, year):
	rows = frappe.get_all(
		"Duty Leave Request",
		filters={"user": user},
		fields=["name", "start_date", "end_date", "work_days", "status", "note"],
		order_by="start_date desc",
		limit=30,
	)
	out = []
	tday = getdate(today())
	for r in rows:
		sd = getdate(r.start_date)
		if sd.year < year and r.status in ("Declined", "Cancelled"):
			continue  # keep history light: old rejections drop off
		r.start_date = str(r.start_date)
		r.end_date = str(r.end_date)
		r.cancellable = 1 if (r.status in ("Pending", "Approved") and sd > tday) else 0
		out.append(r)
	return out


@frappe.whitelist()
def my_leave():
	require_staff()
	user = frappe.session.user
	year = getdate(today()).year
	ent = _entitlement(user)
	taken = _taken(user, year)
	data = {
		"entitlement": ent,
		"taken": taken,
		"remaining": max(ent - taken, 0),
		"year": year,
		"requests": _my_requests(user, year),
		"is_admin": 1 if _is_admin() else 0,
	}
	if data["is_admin"]:
		pend = frappe.get_all(
			"Duty Leave Request",
			filters={"status": "Pending"},
			fields=["name", "user", "start_date", "end_date", "work_days", "note"],
			order_by="start_date asc",
		)
		for p in pend:
			p.full_name = frappe.utils.get_fullname(p.user)
			p.start_date = str(p.start_date)
			p.end_date = str(p.end_date)
			p.remaining = max(_entitlement(p.user) - _taken(p.user, getdate(p.start_date).year), 0)
			others = frappe.get_all(
				"Duty Leave Request",
				filters={
					"user": ["!=", p.user],
					"status": ["in", ["Approved", "Pending"]],
					"start_date": ["<=", p.end_date],
					"end_date": [">=", p.start_date],
				},
				fields=["user", "status"],
			)
			seen = {}
			for o in others:
				if o.user not in seen or o.status == "Approved":
					seen[o.user] = o.status
			p.also_away = [
				{"name": frappe.utils.get_fullname(u), "status": st}
				for u, st in seen.items()
			]
		data["pending"] = pend
	return data


@frappe.whitelist()
def request_leave(start_date, end_date, note=None):
	require_staff()
	user = frappe.session.user
	s, e = getdate(start_date), getdate(end_date)
	if e < s:
		frappe.throw(_("End date is before start date."))
	if s < getdate(today()):
		frappe.throw(_("Leave cannot start in the past."))
	days = _workdays(s, e)
	if not days:
		frappe.throw(_("That range covers no work days."))
	if _overlaps(user, s, e):
		frappe.throw(_("You already have leave requested or approved in that period."))
	remaining = _entitlement(user) - _taken(user, s.year)
	if days > remaining:
		frappe.throw(_("Not enough leave left: {0} day(s) requested, {1} remaining.").format(days, max(remaining, 0)))
	frappe.get_doc(
		{
			"doctype": "Duty Leave Request",
			"user": user,
			"leave_type": "Annual",
			"start_date": s,
			"end_date": e,
			"work_days": days,
			"status": "Pending",
			"note": (note or "").strip()[:500] or None,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		from duty_board.api import _notify_user

		full = frappe.utils.get_fullname(user)
		sms = {
			u
			for u in frappe.get_all(
				"Has Role",
				filters={"role": "System Manager", "parenttype": "User"},
				pluck="parent",
			)
			if u not in ("Administrator", user)
			and frappe.db.get_value("User", u, "enabled")
		}
		for sm in sms:
			_notify_user(
				sm,
				_("🌴 Leave request: {0}").format(full),
				_("{0} → {1} · {2} day(s). Approve on your Me screen.").format(str(s), str(e), days),
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "leave request notify")
	return my_leave()


@frappe.whitelist()
def cancel_leave(name):
	require_staff()
	doc = frappe.get_doc("Duty Leave Request", name)
	own = doc.user == frappe.session.user
	if not own and not _is_admin():
		frappe.throw(_("Not yours to cancel."))
	if doc.status not in ("Pending", "Approved"):
		frappe.throw(_("Already {0}.").format(doc.status.lower()))
	if own and not _is_admin() and getdate(doc.start_date) <= getdate(today()):
		frappe.throw(_("Leave that has started can only be cancelled by an administrator."))
	doc.db_set("status", "Cancelled", update_modified=True)
	frappe.db.commit()
	return my_leave()


@frappe.whitelist()
def decide_leave(name, approve, note=None):
	require_staff()
	if not _is_admin():
		frappe.throw(_("Only administrators approve leave."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Leave Request", name)
	if doc.status != "Pending":
		frappe.throw(_("Already decided."))
	if cint(approve):
		remaining = _entitlement(doc.user) - _taken(doc.user, getdate(doc.start_date).year)
		if cint(doc.work_days) > remaining:
			frappe.throw(_("Balance no longer sufficient: {0} requested, {1} left.").format(doc.work_days, max(remaining, 0)))
		doc.db_set("status", "Approved", update_modified=True)
	else:
		doc.db_set("status", "Declined", update_modified=True)
	doc.db_set("decided_by", frappe.session.user, update_modified=False)
	doc.db_set("decided_on", frappe.utils.now(), update_modified=False)
	if note:
		doc.db_set("decision_note", (note or "").strip()[:500], update_modified=False)
	frappe.db.commit()
	return my_leave()
