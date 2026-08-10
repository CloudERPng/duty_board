"""Reminders — one-off or repeating, fired by the minute-cron and
delivered through _notify_user (in-app + web push)."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_months, get_datetime, now_datetime

from duty_board.permissions import require_staff


@frappe.whitelist()
def my_reminders():
	require_staff()
	rows = frappe.get_all(
		"Duty Reminder",
		filters={"user": frappe.session.user, "status": "Active"},
		fields=["name", "text", "remind_at", "repeat"],
		order_by="remind_at asc",
		limit=50,
	)
	for r in rows:
		r.remind_at = str(r.remind_at)
	return rows


@frappe.whitelist()
def add_reminder(text, remind_at, repeat="None"):
	require_staff()
	text = (text or "").strip()
	if not text:
		frappe.throw(_("What should I remind you about?"))
	when = get_datetime(remind_at)
	if when <= now_datetime():
		frappe.throw(_("Pick a future time."))
	if repeat not in ("None", "Daily", "Weekly", "Monthly"):
		repeat = "None"
	frappe.get_doc({
		"doctype": "Duty Reminder",
		"user": frappe.session.user,
		"text": text[:200],
		"remind_at": when,
		"repeat": repeat,
		"status": "Active",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return my_reminders()


@frappe.whitelist()
def cancel_reminder(name):
	require_staff()
	doc = frappe.get_doc("Duty Reminder", name)
	if doc.user != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not yours."))
	doc.db_set("status", "Cancelled", update_modified=True)
	frappe.db.commit()
	return my_reminders()


def _advance(when, repeat, now):
	"""Next occurrence strictly in the future (catch-up safe)."""
	step = {"Daily": timedelta(days=1), "Weekly": timedelta(days=7)}.get(repeat)
	nxt = when
	for _i in range(400):
		nxt = add_months(nxt, 1) if repeat == "Monthly" else nxt + step
		if get_datetime(nxt) > now:
			return nxt
	return None


def fire_due():
	"""Cron, every minute: fire Active reminders whose time has come."""
	from duty_board.api import _notify_user

	now = now_datetime()
	due = frappe.get_all(
		"Duty Reminder",
		filters={"status": "Active", "remind_at": ["<=", now]},
		fields=["name", "user", "text", "remind_at", "repeat"],
		limit=200,
	)
	for r in due:
		try:
			_notify_user(r.user, _("⏰ Reminder"), r.text)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "reminder notify")
		if r.repeat and r.repeat != "None":
			nxt = _advance(get_datetime(r.remind_at), r.repeat, now)
			if nxt:
				frappe.db.set_value("Duty Reminder", r.name, {"remind_at": nxt, "last_fired": now}, update_modified=False)
			else:
				frappe.db.set_value("Duty Reminder", r.name, {"status": "Done", "last_fired": now}, update_modified=False)
		else:
			frappe.db.set_value("Duty Reminder", r.name, {"status": "Done", "last_fired": now}, update_modified=False)
	if due:
		frappe.db.commit()
