"""Accounting Services unit — the cadence engine and close matrix.

Clients are customers with accounting_services = "On Board". Rooms are
created/tagged by sync; deliverable instances spawn per period from a global
template set (plus per-room optionals); the matrix reads clients × period.

Manual runs:
  bench --site <site> execute duty_board.accounting.sync_accounting_clients
  bench --site <site> execute duty_board.accounting.scheduled_open_period

hooks.py (server-maintained — add manually):
  scheduler_events = {
      "daily": [..., "duty_board.accounting.scheduled_open_period"],
  }
(daily is safe: opening is idempotent and self-limits to the current period.)
"""

import calendar
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from duty_board.client_room import _post, _staff_only

SERVICE_PRODUCT = "Accounting Services"

SEED_TYPES = [
	# (title, frequency, due_basis, due_day, optional, sort)
	("Bank journals posted & current", "Monthly", "Last working day of period", 0, 0, 1),
	("Bank reconciliation", "Monthly", "Nth working day of next month", 3, 0, 2),
	("Financial statements", "Monthly", "Nth working day of next month", 5, 0, 3),
	("Stock take", "Quarterly", "Last working day of period", 0, 1, 4),
]


def _workday_set():
	day_idx = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
	days = {0, 1, 2, 3, 4}
	try:
		raw = (frappe.get_cached_doc("Duty Settings").get("workdays") or "").strip()
		if raw:
			parsed = {day_idx[t.strip()[:3].lower()] for t in raw.split(",") if t.strip()[:3].lower() in day_idx}
			if parsed:
				days = parsed
	except Exception:
		pass
	return days


def nth_working_day(year, month, n):
	days = _workday_set()
	d = date(year, month, 1)
	count = 0
	while True:
		if d.weekday() in days:
			count += 1
			if count >= n:
				return d
		d += timedelta(days=1)
		if d.month != month:
			return d - timedelta(days=1)


def last_working_day(year, month):
	days = _workday_set()
	d = date(year, month, calendar.monthrange(year, month)[1])
	while d.weekday() not in days and d.day > 1:
		d -= timedelta(days=1)
	return d


def _due_date(t, year, month):
	if t.due_basis == "Nth working day of next month":
		ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
		return nth_working_day(ny, nm, max(1, cint(t.due_day)))
	if t.due_basis == "Nth working day of period":
		return nth_working_day(year, month, max(1, cint(t.due_day)))
	return last_working_day(year, month)


def _onboard_customers():
	return frappe.get_all(
		"Customer",
		filters={"accounting_services": "On Board"},
		fields=["name", "accounting_fees"],
	)


def _accounting_rooms():
	custs = {c.name: c for c in _onboard_customers()}
	if not custs:
		return [], {}
	rooms = frappe.get_all(
		"Client Room",
		filters={"customer": ["in", list(custs)], "status": ["!=", "Archived"]},
		fields=["name", "customer", "bookkeeper", "books_optionals", "products"],
	)
	return rooms, custs


@frappe.whitelist()
def seed_deliverable_types():
	_staff_only()
	created = 0
	for title, freq, basis, day, opt, so in SEED_TYPES:
		if frappe.db.exists("Duty Service Deliverable Type", {"title": title}):
			continue
		frappe.get_doc(
			{
				"doctype": "Duty Service Deliverable Type",
				"title": title,
				"frequency": freq,
				"due_basis": basis,
				"due_day": day,
				"optional": opt,
				"active": 1,
				"sort_order": so,
			}
		).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	return {"created": created}


@frappe.whitelist()
def sync_accounting_clients():
	_staff_only()
	return _sync_accounting_clients()


def _sync_accounting_clients():
	"""Customer.accounting_services = 'On Board' → room exists, tagged with the
	service product. One-directional; no off-boarding."""
	if not frappe.db.exists("Duty Product", SERVICE_PRODUCT):
		frappe.get_doc(
			{"doctype": "Duty Product", "title": SERVICE_PRODUCT, "active": 1, "sort_order": 50}
		).insert(ignore_permissions=True)
	created, tagged = 0, 0
	for c in _onboard_customers():
		room_name = frappe.db.get_value(
			"Client Room", {"customer": c.name, "status": ["!=", "Archived"]}, "name"
		)
		if not room_name:
			from duty_board.client_room import _ensure_token

			doc = frappe.get_doc(
				{"doctype": "Client Room", "customer": c.name, "unit": "Accounting", "status": "Active"}
			).insert(ignore_permissions=True)
			_ensure_token(doc)
			room_name = doc.name
			created += 1
		prods = [p.strip() for p in (frappe.db.get_value("Client Room", room_name, "products") or "").split(",") if p.strip()]
		if SERVICE_PRODUCT not in prods:
			prods.append(SERVICE_PRODUCT)
			frappe.db.set_value("Client Room", room_name, "products", ", ".join(prods), update_modified=False)
			tagged += 1
	frappe.db.commit()
	return {"customers": len(_onboard_customers()), "rooms_created": created, "rooms_tagged": tagged}


def _quarter_end_month(month):
	return month in (3, 6, 9, 12)


def _open_period(period):
	"""Spawn missing deliverable instances for every accounting room. Idempotent."""
	year, month = int(period[:4]), int(period[5:7])
	rooms, _custs = _accounting_rooms()
	types = frappe.get_all(
		"Duty Service Deliverable Type",
		filters={"active": 1},
		fields=["name", "title", "frequency", "due_basis", "due_day", "optional"],
		order_by="sort_order asc",
	)
	spawned = 0
	for room in rooms:
		optionals = {t.strip() for t in (room.books_optionals or "").split(",") if t.strip()}
		for t in types:
			if t.frequency == "Quarterly" and not _quarter_end_month(month):
				continue
			if cint(t.optional) and t.name not in optionals and t.title not in optionals:
				continue
			if frappe.db.exists(
				"Duty Service Deliverable",
				{"room": room.name, "deliverable_type": t.name, "period": period},
			):
				continue
			frappe.get_doc(
				{
					"doctype": "Duty Service Deliverable",
					"room": room.name,
					"deliverable_type": t.name,
					"period": period,
					"due_date": _due_date(t, year, month),
					"status": "Pending",
					"assigned_to": room.bookkeeper or None,
				}
			).insert(ignore_permissions=True)
			spawned += 1
	frappe.db.commit()
	return spawned


@frappe.whitelist()
def books_open_period(period):
	_staff_only()
	n = _open_period(period)
	return {"spawned": n, "period": period}


def scheduled_open_period():
	"""Daily-safe: syncs new on-board customers and opens the current period."""
	frappe.set_user("Administrator")
	try:
		_sync_accounting_clients()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "accounting sync")
	_open_period(today()[:7])


@frappe.whitelist()
def books_matrix(period=None):
	_staff_only()
	period = (period or today()[:7]).strip()[:7]
	rooms, custs = _accounting_rooms()
	types = frappe.get_all(
		"Duty Service Deliverable Type",
		filters={"active": 1},
		fields=["name", "title", "optional"],
		order_by="sort_order asc",
	)
	insts = frappe.get_all(
		"Duty Service Deliverable",
		filters={"period": period, "room": ["in", [r.name for r in rooms]] if rooms else ["is", "set"]},
		fields=[
			"name", "room", "deliverable_type", "status", "due_date",
			"assigned_to", "reviewer", "delivered_on", "notes",
		],
	)
	by_room = {}
	tdy = getdate(today())
	for i in insts:
		i.due_date = str(i.due_date) if i.due_date else None
		i.late = bool(i.due_date and getdate(i.due_date) < tdy and i.status not in ("Delivered", "Acknowledged"))
		by_room.setdefault(i.room, {})[i.deliverable_type] = i
	out_rooms = []
	for r in sorted(rooms, key=lambda x: x.customer or ""):
		out_rooms.append(
			{
				"room": r.name,
				"customer": r.customer,
				"bookkeeper": r.bookkeeper,
				"bookkeeper_name": frappe.utils.get_fullname(r.bookkeeper) if r.bookkeeper else None,
				"optionals": r.books_optionals or "",
				"fee": custs.get(r.customer, frappe._dict()).get("accounting_fees"),
				"cells": by_room.get(r.name, {}),
			}
		)
	return {"period": period, "types": types, "rooms": out_rooms}


@frappe.whitelist()
def books_set(name, status=None, assigned_to=None, reviewer=None, notes=None):
	_staff_only()
	doc = frappe.get_doc("Duty Service Deliverable", name)
	vals = {}
	if status and status != doc.status:
		if status not in ("Pending", "In Progress", "In Review", "Delivered", "Acknowledged"):
			frappe.throw(_("Unknown status."))
		if status == "Acknowledged":
			frappe.throw(_("Acknowledged is stamped by the client, not set by staff."))
		if (
			status == "Delivered"
			and doc.reviewer
			and frappe.session.user != doc.reviewer
			and "System Manager" not in frappe.get_roles()
		):
			frappe.throw(
				_("This deliverable has a reviewer — only {0} can mark it Delivered.").format(
					frappe.utils.get_fullname(doc.reviewer)
				)
			)
		vals["status"] = status
		if status == "In Review" and doc.reviewer:
			try:
				from duty_board.api import _notify_user

				t_title = frappe.db.get_value("Duty Service Deliverable Type", doc.deliverable_type, "title")
				cust = frappe.db.get_value("Client Room", doc.room, "customer")
				_notify_user(doc.reviewer, _("👁 Review requested"), f"{cust} · {t_title} · {doc.period}")
			except Exception:
				pass
		if status == "Delivered":
			vals["delivered_on"] = today()
			t = frappe.db.get_value("Duty Service Deliverable Type", doc.deliverable_type, "title")
			room = frappe.get_doc("Client Room", doc.room)
			_post(room, _("📒 {0} — {1} is ready for {2}.").format(t, doc.period, room.customer))
	if assigned_to is not None:
		vals["assigned_to"] = assigned_to or None
	if reviewer is not None:
		vals["reviewer"] = reviewer or None
	if notes is not None:
		vals["notes"] = (notes or "").strip()[:500] or None
	if vals:
		doc.db_set(vals, update_modified=False)
		frappe.db.commit()
	return books_matrix(doc.period)


@frappe.whitelist()
def books_set_room(name, bookkeeper=None, optionals=None):
	_staff_only()
	vals = {}
	if bookkeeper is not None:
		vals["bookkeeper"] = bookkeeper or None
	if optionals is not None:
		vals["books_optionals"] = (optionals or "").strip()[:300] or None
	if vals:
		frappe.db.set_value("Client Room", name, vals, update_modified=False)
		frappe.db.commit()
	return {"ok": True}


# ---------------- client face: the deliverable ceremony ----------------


def _client_deliverable_rows(room):
	periods = sorted(
		{d.period for d in frappe.get_all("Duty Service Deliverable", filters={"room": room.name}, fields=["period"])},
		reverse=True,
	)[:3]
	if not periods:
		return []
	rows = frappe.get_all(
		"Duty Service Deliverable",
		filters={"room": room.name, "period": ["in", periods]},
		fields=["name", "deliverable_type", "period", "due_date", "status", "delivered_on", "acknowledged_on", "acknowledged_by"],
		order_by="period desc",
	)
	titles = {
		t.name: t.title
		for t in frappe.get_all("Duty Service Deliverable Type", fields=["name", "title"])
	}
	out = []
	for r in rows:
		out.append(
			{
				"name": r.name,
				"title": titles.get(r.deliverable_type, r.deliverable_type),
				"period": r.period,
				"due_date": str(r.due_date) if r.due_date else None,
				"delivered_on": str(r.delivered_on) if r.delivered_on else None,
				"acknowledged_on": str(r.acknowledged_on)[:16] if r.acknowledged_on else None,
				"acknowledged_by": r.acknowledged_by,
				"status": "Acknowledged"
				if r.status == "Acknowledged"
				else ("Delivered" if r.status == "Delivered" else "In preparation"),
			}
		)
	return out


@frappe.whitelist()
def client_get_deliverables():
	from duty_board.client_room import _client_room

	room = _client_room()
	return _client_deliverable_rows(room)


@frappe.whitelist()
def client_ack_deliverable(name):
	from duty_board.client_room import _client_room, _post

	room = _client_room()
	doc = frappe.db.get_value(
		"Duty Service Deliverable", name, ["room", "status", "deliverable_type", "period", "assigned_to"], as_dict=True
	)
	if not doc or doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status != "Delivered":
		frappe.throw(_("Only delivered items can be acknowledged."))
	who = frappe.utils.get_fullname(frappe.session.user)
	frappe.db.set_value(
		"Duty Service Deliverable",
		name,
		{"status": "Acknowledged", "acknowledged_on": frappe.utils.now_datetime(), "acknowledged_by": who},
		update_modified=False,
	)
	frappe.db.commit()
	t_title = frappe.db.get_value("Duty Service Deliverable Type", doc.deliverable_type, "title")
	_post(room, _("✅ {0} acknowledged receipt of {1} — {2}.").format(who, t_title, doc.period))
	if doc.assigned_to:
		try:
			from duty_board.api import _notify_user

			_notify_user(doc.assigned_to, _("✅ Acknowledged"), f"{room.customer} · {t_title} · {doc.period}")
		except Exception:
			pass
	return _client_deliverable_rows(room)
