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
from frappe.utils import cint, flt, getdate, today

from duty_board.client_room import _post, _staff_only

SERVICE_PRODUCT = "Accounting Services"


def _books_manager():
	"""Fees and profitability are visible to System Managers and the users
	listed in Duty Settings.books_managers — no one else."""
	if "System Manager" in frappe.get_roles():
		return True
	try:
		raw = (frappe.get_cached_doc("Duty Settings").get("books_managers") or "").lower()
		return frappe.session.user.lower() in {e.strip() for e in raw.replace("\n", ",").split(",") if e.strip()}
	except Exception:
		return False

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


def _prev_working_day(d):
	days = _workday_set()
	while d.weekday() not in days:
		d -= timedelta(days=1)
	return d


def _due_date(t, year, month):
	if t.due_basis == "Nth working day of next month":
		ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
		return nth_working_day(ny, nm, max(1, cint(t.due_day)))
	if t.due_basis == "Nth working day of period":
		return nth_working_day(year, month, max(1, cint(t.due_day)))
	if t.due_basis == "Fixed day of next month":
		ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
		day = min(max(1, cint(t.due_day)), calendar.monthrange(ny, nm)[1])
		# statutory-safe: a deadline on a non-workday is met EARLY, never late
		return _prev_working_day(date(ny, nm, day))
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


STATUTORY_TYPES = [
	# (title, due day of next month — Nigerian monthly compliance calendar)
	("PAYE remittance (state IRS)", 10),
	("VAT return (FIRS)", 21),
	("WHT remittance (FIRS)", 21),
]


@frappe.whitelist()
def seed_statutory_types():
	"""Nigeria monthly statutory set — seeded as OPTIONAL (tiered service):
	enabled per client in the room setup, like Stock take."""
	_staff_only()
	created = 0
	for i, (title, day) in enumerate(STATUTORY_TYPES):
		if frappe.db.exists("Duty Service Deliverable Type", {"title": title}):
			continue
		frappe.get_doc(
			{
				"doctype": "Duty Service Deliverable Type",
				"title": title,
				"frequency": "Monthly",
				"due_basis": "Fixed day of next month",
				"due_day": day,
				"optional": 1,
				"active": 1,
				"sort_order": 10 + i,
			}
		).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	return {"created": created}


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
			_spawn_onboarding(room_name, c.name)
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
	r = _spawn_period_requests(period)
	return {"spawned": n, "requests": r, "period": period}


def scheduled_open_period():
	"""Daily-safe: syncs new on-board customers and opens the current period."""
	frappe.set_user("Administrator")
	try:
		_sync_accounting_clients()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "accounting sync")
	_open_period(today()[:7])
	_spawn_period_requests(today()[:7])


@frappe.whitelist()
def books_matrix(period=None):
	_staff_only()
	period = (period or today()[:7]).strip()[:7]
	rooms, custs = _accounting_rooms()
	types = frappe.get_all(
		"Duty Service Deliverable Type",
		filters={"active": 1},
		fields=["name", "title", "optional", "frequency"],
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
	fees_ok = _books_manager()
	latest_pt = {}
	if rooms:
		for l in frappe.get_all(
			"Duty Books Daily Log",
			filters={"room": ["in", [r.name for r in rooms]], "posted_through": ["is", "set"]},
			fields=["room", "posted_through"],
			order_by="posted_through asc",
		):
			latest_pt[l.room] = l.posted_through
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
				"fee": custs.get(r.customer, frappe._dict()).get("accounting_fees") if fees_ok else None,
				"posted_through": str(latest_pt[r.name]) if r.name in latest_pt else None,
				"lag": _working_days_between(getdate(latest_pt[r.name]), tdy) if r.name in latest_pt else None,
				"cells": by_room.get(r.name, {}),
			}
		)
	return {"period": period, "types": types, "rooms": out_rooms, "fees_visible": fees_ok}


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


# ---------------- profitability: hours against the fee ----------------


@frappe.whitelist()
def books_profitability(period=None):
	_staff_only()
	if not _books_manager():
		frappe.throw(_("Fees and profitability are restricted."), frappe.PermissionError)
	period = (period or today()[:7]).strip()[:7]
	year, month = int(period[:4]), int(period[5:7])
	start = f"{period}-01"
	ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
	end = f"{ny:04d}-{nm:02d}-01"
	rooms, custs = _accounting_rooms()
	if not rooms:
		return {"period": period, "rows": []}
	sessions = frappe.db.sql(
		"""select customer, user, coalesce(sum(duration), 0) as secs
		from `tabWork Session`
		where customer in %(custs)s and start_time >= %(s)s and start_time < %(e)s
		group by customer, user""",
		{"custs": tuple(custs.keys()), "s": start, "e": end},
		as_dict=True,
	)
	by_cust = {}
	for s in sessions:
		by_cust.setdefault(s.customer, []).append(s)
	out = []
	for r in rooms:
		fee = flt(custs.get(r.customer, frappe._dict()).get("accounting_fees"))
		rows = by_cust.get(r.customer, [])
		secs = sum(s.secs for s in rows)
		hours = round(secs / 3600.0, 1)
		out.append(
			{
				"customer": r.customer,
				"fee": fee,
				"hours": hours,
				"rate": round(fee / hours, 0) if hours else None,
				"team": sorted(
					[
						{"user": s.user, "first": frappe.utils.get_fullname(s.user).split(" ")[0], "hours": round(s.secs / 3600.0, 1)}
						for s in rows
					],
					key=lambda x: -x["hours"],
				),
			}
		)
	out.sort(key=lambda x: (x["rate"] is None, x["rate"] if x["rate"] is not None else 0))
	return {"period": period, "rows": out}


# ---------------- daily assurance: register, attestation, digest ----------------

NEGLECT_DAYS = 2


def _working_days_between(d1, d2):
	"""Working days strictly after d1, up to and including d2."""
	days = _workday_set()
	if not d1 or d1 >= d2:
		return 0
	n, d = 0, d1
	while d < d2:
		d = d + timedelta(days=1)
		if d.weekday() in days:
			n += 1
	return n


def _sessions_by_room_day(customers, start, end):
	if not customers:
		return {}
	rows = frappe.db.sql(
		"""select customer, user, date(start_time) as d from `tabWork Session`
		where customer in %(c)s and start_time >= %(s)s and start_time < %(e)s""",
		{"c": tuple(customers), "s": start, "e": end},
		as_dict=True,
	)
	out = {}
	for r in rows:
		out.setdefault((r.customer, str(r.d)), set()).add(r.user)
	return out


@frappe.whitelist()
def books_daily_round():
	"""The bookkeeper's two-tap evening ritual: my clients, today's state."""
	_staff_only()
	user = frappe.session.user
	rooms, custs = _accounting_rooms()
	mine = [r for r in rooms if r.bookkeeper == user] or rooms
	tdy = today()
	sessions = _sessions_by_room_day([r.customer for r in mine], tdy, str(getdate(tdy) + timedelta(days=1)))
	logs = {
		l.room: l
		for l in frappe.get_all(
			"Duty Books Daily Log",
			filters={"user": user, "log_date": tdy, "room": ["in", [r.name for r in mine]]},
			fields=["name", "room", "posted_through", "tx_posted", "queries_raised", "note"],
		)
	}
	last_pt = {}
	for l in frappe.get_all(
		"Duty Books Daily Log",
		filters={"room": ["in", [r.name for r in mine]], "posted_through": ["is", "set"]},
		fields=["room", "posted_through"],
		order_by="posted_through asc",
	):
		last_pt[l.room] = l.posted_through
	out = []
	for r in mine:
		lg = logs.get(r.name)
		pt = (lg and lg.posted_through) or last_pt.get(r.name)
		out.append(
			{
				"room": r.name,
				"customer": r.customer,
				"worked_today": (r.customer, tdy) in sessions,
				"logged_today": bool(lg),
				"posted_through": str(pt) if pt else None,
				"lag": _working_days_between(getdate(pt), getdate(tdy)) if pt else None,
				"tx_posted": lg.tx_posted if lg else None,
				"queries_raised": lg.queries_raised if lg else None,
				"note": lg.note if lg else None,
			}
		)
	return {"date": tdy, "rows": out}


@frappe.whitelist()
def books_log_day(room, posted_through=None, tx_posted=None, queries_raised=None, note=None):
	_staff_only()
	user = frappe.session.user
	customer = frappe.db.get_value("Client Room", room, "customer")
	if posted_through and getdate(posted_through) > getdate(today()):
		frappe.throw(_("Books cannot be posted through a future date."))
	existing = frappe.db.get_value(
		"Duty Books Daily Log", {"user": user, "room": room, "log_date": today()}, "name"
	)
	vals = {
		"posted_through": posted_through or None,
		"tx_posted": cint(tx_posted) if tx_posted is not None else 0,
		"queries_raised": cint(queries_raised) if queries_raised is not None else 0,
		"note": (note or "").strip()[:300] or None,
	}
	if existing:
		frappe.db.set_value("Duty Books Daily Log", existing, vals, update_modified=False)
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Books Daily Log",
				"room": room,
				"customer": customer,
				"user": user,
				"log_date": today(),
				**vals,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	return books_daily_round()


def _register_data(period):
	year, month = int(period[:4]), int(period[5:7])
	rooms, custs = _accounting_rooms()
	wds = _workday_set()
	first = date(year, month, 1)
	last = date(year, month, calendar.monthrange(year, month)[1])
	days = []
	d = first
	while d <= last:
		if d.weekday() in wds:
			days.append(str(d))
		d += timedelta(days=1)
	sessions = _sessions_by_room_day([r.customer for r in rooms], str(first), str(last + timedelta(days=1)))
	logs = frappe.get_all(
		"Duty Books Daily Log",
		filters={"room": ["in", [r.name for r in rooms]] if rooms else ["is", "set"], "log_date": ["between", [str(first), str(last)]]},
		fields=["room", "customer", "log_date", "posted_through", "user"],
	)
	log_days = {}
	for l in logs:
		log_days.setdefault((l.room, str(l.log_date)), []).append(l)
	latest_pt = {}
	for l in frappe.get_all(
		"Duty Books Daily Log",
		filters={"room": ["in", [r.name for r in rooms]] if rooms else ["is", "set"], "posted_through": ["is", "set"]},
		fields=["room", "posted_through"],
		order_by="posted_through asc",
	):
		latest_pt[l.room] = l.posted_through
	tdy = getdate(today())
	out_rooms = []
	for r in sorted(rooms, key=lambda x: x.customer or ""):
		cells = {}
		for ds in days:
			if getdate(ds) > tdy:
				cells[ds] = "future"
			else:
				worked = (r.customer, ds) in sessions
				logged = (r.name, ds) in log_days
				cells[ds] = "both" if worked and logged else ("worked" if worked else ("logged" if logged else "none"))
		streak = 0
		for ds in reversed([x for x in days if getdate(x) <= tdy]):
			if cells[ds] == "none":
				streak += 1
			else:
				break
		pt = latest_pt.get(r.name)
		out_rooms.append(
			{
				"room": r.name,
				"customer": r.customer,
				"bookkeeper": r.bookkeeper,
				"cells": cells,
				"streak": streak,
				"neglected": streak >= NEGLECT_DAYS,
				"posted_through": str(pt) if pt else None,
				"lag": _working_days_between(getdate(pt), tdy) if pt else None,
			}
		)
	return {"period": period, "days": days, "rooms": out_rooms, "neglect_days": NEGLECT_DAYS}


@frappe.whitelist()
def books_register(period=None):
	_staff_only()
	return _register_data((period or today()[:7]).strip()[:7])


def _digest_recipients(rooms):
	users = {r.bookkeeper for r in rooms if r.bookkeeper}
	try:
		raw = (frappe.get_cached_doc("Duty Settings").get("books_managers") or "")
		users |= {e.strip() for e in raw.replace("\n", ",").split(",") if e.strip()}
	except Exception:
		pass
	return {u for u in users if u and frappe.db.exists("User", u)}


def books_evening_digest():
	"""Cron (weekday evenings): the unit's day, told to the whole unit."""
	frappe.set_user("Administrator")
	tdy = getdate(today())
	if tdy.weekday() not in _workday_set():
		return
	data = _register_data(today()[:7])
	rooms = data["rooms"]
	if not rooms:
		return
	ds = today()
	covered, partial, untouched, neglected = [], [], [], []
	for r in rooms:
		state = r["cells"].get(ds, "none")
		lagtxt = f" (posted through {r['posted_through']}, lag {r['lag']}wd)" if r["posted_through"] else " (no attestation yet)"
		line = f"{r['customer']}{lagtxt}"
		if r["neglected"]:
			neglected.append(f"{r['customer']} — {r['streak']} working days untouched")
		if state == "both":
			covered.append(line)
		elif state in ("worked", "logged"):
			partial.append(f"{line} — {'worked, not attested' if state == 'worked' else 'attested, no session'}")
		else:
			untouched.append(line)
	parts = [f"📒 Books daily digest — {ds}"]
	if neglected:
		parts.append("⚠ NEGLECT (≥2 working days): " + "; ".join(neglected))
	parts.append(f"✅ Covered today ({len(covered)}): " + ("; ".join(covered) or "none"))
	if partial:
		parts.append(f"🟡 Partial ({len(partial)}): " + "; ".join(partial))
	parts.append(f"🔴 Untouched today ({len(untouched)}): " + ("; ".join(untouched) or "none"))
	open_q = frappe.db.count("Duty Books Query", {"status": "Open", "room": ["in", [r["room"] for r in rooms]]})
	open_r = frappe.db.count("Duty Books Request", {"status": "Requested", "room": ["in", [r["room"] for r in rooms]]})
	if open_q or open_r:
		parts.append(f"📨 Awaiting clients: {open_q} question(s), {open_r} document(s)")
	body = "\n".join(parts)
	recipients = _digest_recipients(
		[frappe._dict(bookkeeper=r["bookkeeper"]) for r in rooms]
	)
	title = f"📒 Books digest {ds}: {len(covered)}✅ {len(partial)}🟡 {len(untouched)}🔴" + (f" · {len(neglected)}⚠" if neglected else "")
	for u in recipients:
		try:
			from duty_board.api import _notify_user

			_notify_user(u, title, body[:180])
		except Exception:
			pass
	try:
		frappe.sendmail(recipients=sorted(recipients), subject=title, message=body.replace("\n", "<br>"), delayed=False)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "books digest mail")


# ---------------- client follow-ups: queries + document requests ----------------

CHASE_EVERY_WD = 2


def _room_client_emails(room_name):
	users = frappe.get_all(
		"Client Room Member", filters={"room": room_name, "active": 1}, pluck="user"
	)
	out = []
	for u in users:
		if u and frappe.db.get_value("User", u, "enabled"):
			out.append(u)
	return out


def _file_to_shelf(room_name, title, file_url, file_name):
	if not file_url:
		return None
	doc = frappe.get_doc(
		{
			"doctype": "Client Shelf Doc",
			"room": room_name,
			"title": title[:140],
			"category": "Accounting — received",
			"file_url": file_url,
			"file_name": (file_name or "")[:140] or None,
			"active": 1,
		}
	).insert(ignore_permissions=True)
	return doc.name


def _mail_client(room, subject, body, ref_doctype=None, ref_name=None):
	"""Email the room's client members via the Communication send path: this
	stamps Reply-To from the default incoming Email Account and stores the
	Message-ID, so replies thread back to the reference document reliably."""
	recipients = _room_client_emails(room.name)
	if not recipients:
		return
	sender = frappe.db.get_value(
		"Email Account", {"default_incoming": 1, "enable_incoming": 1}, "email_id"
	)
	try:
		from frappe.core.doctype.communication.email import make

		kwargs = {}
		if sender:
			kwargs["sender"] = sender
		make(
			doctype=ref_doctype,
			name=ref_name,
			subject=subject,
			content=body,
			recipients=", ".join(recipients),
			communication_medium="Email",
			sent_or_received="Sent",
			send_email=True,
			**kwargs,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "books client mail")
		try:
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=body,
				reference_doctype=ref_doctype,
				reference_name=ref_name,
				reply_to=sender or None,
				delayed=False,
			)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "books client mail fallback")


def _spawn_period_requests(period):
	"""Standard monthly document requests for every accounting room."""
	try:
		raw = (frappe.get_cached_doc("Duty Settings").get("books_monthly_requests") or "").strip()
	except Exception:
		raw = ""
	if not raw:
		return 0
	year, month = int(period[:4]), int(period[5:7])
	items = []
	for line in raw.splitlines():
		if "|" in line:
			title, wd = line.rsplit("|", 1)
			try:
				wd = max(1, int(wd.strip()))
			except ValueError:
				wd = 2
		else:
			title, wd = line, 2
		title = title.strip()
		if title:
			items.append((title, nth_working_day(year, month, wd)))
	if not items:
		return 0
	rooms, _c = _accounting_rooms()
	n = 0
	for room in rooms:
		for title, due in items:
			if frappe.db.exists(
				"Duty Books Request", {"room": room.name, "period": period, "title": title}
			):
				continue
			frappe.get_doc(
				{
					"doctype": "Duty Books Request",
					"room": room.name,
					"customer": room.customer,
					"period": period,
					"title": title,
					"due_date": due,
					"status": "Requested",
				}
			).insert(ignore_permissions=True)
			n += 1
	frappe.db.commit()
	return n


@frappe.whitelist()
def books_followups(room=None):
	_staff_only()
	rooms, _c = _accounting_rooms()
	names = [r.name for r in rooms if not room or r.name == room]
	queries = frappe.get_all(
		"Duty Books Query",
		filters={"room": ["in", names] if names else ["is", "set"], "status": ["!=", "Resolved"]},
		fields=["name", "room", "customer", "ref_date", "amount", "reference", "question", "status", "answer", "answered_by", "answered_on", "creation"],
		order_by="creation asc",
	)
	requests = frappe.get_all(
		"Duty Books Request",
		filters={"room": ["in", names] if names else ["is", "set"], "status": "Requested"},
		fields=["name", "room", "customer", "period", "title", "detail", "due_date", "creation"],
		order_by="due_date asc",
	)
	tdy = getdate(today())
	for q in queries:
		q.ref_date = str(q.ref_date) if q.ref_date else None
		q.answered_on = str(q.answered_on)[:16] if q.answered_on else None
		q.age_wd = _working_days_between(getdate(q.creation), tdy)
	for r in requests:
		r.due_date = str(r.due_date) if r.due_date else None
		r.overdue = bool(r.due_date and getdate(r.due_date) < tdy)
	received = frappe.get_all(
		"Duty Books Request",
		filters={"room": ["in", names] if names else ["is", "set"], "status": "Received"},
		fields=["name", "room", "customer", "title", "attachment_url", "attachment_name", "fulfilled_on", "fulfilled_by"],
		order_by="fulfilled_on desc",
		limit=10,
	)
	for r in received:
		r.fulfilled_on = str(r.fulfilled_on)[:16] if r.fulfilled_on else None
	return {"rooms": [{"room": r.name, "customer": r.customer} for r in sorted(rooms, key=lambda x: x.customer or "")], "queries": queries, "requests": requests, "received": received}


@frappe.whitelist()
def books_add_query(room, question, ref_date=None, amount=None, reference=None):
	_staff_only()
	customer = frappe.db.get_value("Client Room", room, "customer")
	frappe.get_doc(
		{
			"doctype": "Duty Books Query",
			"room": room,
			"customer": customer,
			"ref_date": ref_date or None,
			"amount": flt(amount) if amount else None,
			"reference": (reference or "").strip()[:140] or None,
			"question": (question or "").strip()[:500],
			"status": "Open",
			"asked_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	roomdoc = frappe.get_doc("Client Room", room)
	_post(roomdoc, _("❓ A question from your accounting team is waiting on the portal home."))
	q = frappe.get_all(
		"Duty Books Query",
		filters={"room": room, "status": "Open", "asked_by": frappe.session.user},
		fields=["name", "question", "ref_date", "amount", "reference"],
		order_by="creation desc",
		limit=1,
	)
	if q:
		q = q[0]
		ref_bits = " · ".join([str(x) for x in [q.ref_date, f"₦{q.amount:,.0f}" if q.amount else None, q.reference] if x])
		_mail_client(
			roomdoc,
			f"❓ Question about a transaction — {roomdoc.customer}",
			f"<p>Your accounting team asks:</p><blockquote>{frappe.utils.escape_html(q.question)}</blockquote>"
			+ (f"<p style='color:#666'>{frappe.utils.escape_html(ref_bits)}</p>" if ref_bits else "")
			+ "<p><b>Just reply to this email</b> and your answer will reach the team directly — or answer on your portal home.</p>",
			"Duty Books Query",
			q.name,
		)
	return books_followups(room)


@frappe.whitelist()
def books_add_request(room, title, detail=None, due_date=None):
	_staff_only()
	customer = frappe.db.get_value("Client Room", room, "customer")
	frappe.get_doc(
		{
			"doctype": "Duty Books Request",
			"room": room,
			"customer": customer,
			"period": today()[:7],
			"title": (title or "").strip()[:140],
			"detail": (detail or "").strip()[:300] or None,
			"due_date": due_date or None,
			"status": "Requested",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	roomdoc = frappe.get_doc("Client Room", room)
	_post(roomdoc, _("📎 Your accounting team has requested a document — see the portal home."))
	rq = frappe.get_all(
		"Duty Books Request",
		filters={"room": room, "status": "Requested"},
		fields=["name", "title", "detail", "due_date"],
		order_by="creation desc",
		limit=1,
	)
	if rq:
		rq = rq[0]
		_mail_client(
			roomdoc,
			f"📎 Document needed — {rq.title}",
			f"<p>Your accounting team needs: <b>{frappe.utils.escape_html(rq.title)}</b></p>"
			+ (f"<p>{frappe.utils.escape_html(rq.detail)}</p>" if rq.detail else "")
			+ (f"<p>Due: {rq.due_date}</p>" if rq.due_date else "")
			+ "<p><b>Reply to this email with the file attached</b> and it will be filed automatically — or upload on your portal home.</p>",
			"Duty Books Request",
			rq.name,
		)
	return books_followups(room)


@frappe.whitelist()
def books_resolve_query(name):
	_staff_only()
	doc = frappe.get_doc("Duty Books Query", name)
	doc.db_set({"status": "Resolved"}, update_modified=False)
	frappe.db.commit()
	return books_followups(doc.room)


@frappe.whitelist()
def books_waive_request(name):
	_staff_only()
	doc = frappe.get_doc("Duty Books Request", name)
	doc.db_set({"status": "Waived"}, update_modified=False)
	frappe.db.commit()
	return books_followups(doc.room)


# ---- client side (membrane-wrapped in client_room) ----


def _client_followup_rows(room):
	queries = frappe.get_all(
		"Duty Books Query",
		filters={"room": room.name, "status": "Open"},
		fields=["name", "ref_date", "amount", "reference", "question"],
		order_by="creation asc",
	)
	for q in queries:
		q.ref_date = str(q.ref_date) if q.ref_date else None
	requests = frappe.get_all(
		"Duty Books Request",
		filters={"room": room.name, "status": "Requested"},
		fields=["name", "title", "detail", "due_date"],
		order_by="due_date asc",
	)
	for r in requests:
		r.due_date = str(r.due_date) if r.due_date else None
	return {"queries": queries, "requests": requests}


@frappe.whitelist()
def client_get_followups():
	from duty_board.client_room import _client_room

	return _client_followup_rows(_client_room())


@frappe.whitelist()
def client_answer_query(name, answer):
	from duty_board.client_room import _client_room, _post

	room = _client_room()
	doc = frappe.db.get_value("Duty Books Query", name, ["room", "status", "question"], as_dict=True)
	if not doc or doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status != "Open":
		frappe.throw(_("This question is closed."))
	answer = (answer or "").strip()[:500]
	if not answer:
		frappe.throw(_("Please write an answer."))
	who = frappe.utils.get_fullname(frappe.session.user)
	frappe.db.set_value(
		"Duty Books Query",
		name,
		{"status": "Answered", "answer": answer, "answered_on": frappe.utils.now_datetime(), "answered_by": who},
		update_modified=False,
	)
	frappe.db.commit()
	_post(room, _("💬 {0} answered an accounting question: {1}").format(who, answer[:120]))
	return _client_followup_rows(room)


@frappe.whitelist()
def client_fulfill_request(name, attachment_url=None, attachment_name=None):
	from duty_board.client_room import _client_room, _post

	room = _client_room()
	doc = frappe.db.get_value("Duty Books Request", name, ["room", "status", "title"], as_dict=True)
	if not doc or doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status != "Requested":
		frappe.throw(_("This request is closed."))
	who = frappe.utils.get_fullname(frappe.session.user)
	frappe.db.set_value(
		"Duty Books Request",
		name,
		{
			"status": "Received",
			"attachment_url": attachment_url or None,
			"attachment_name": (attachment_name or "").strip()[:140] or None,
			"fulfilled_on": frappe.utils.now_datetime(),
			"fulfilled_by": who,
		},
		update_modified=False,
	)
	frappe.db.commit()
	shelf = _file_to_shelf(room.name, f"{doc.title} — {today()[:7]}", attachment_url, attachment_name)
	_post(room, _("📎 {0} sent: {1} — filed to your Documents.").format(who, doc.title) if shelf else _("📎 {0} sent: {1}").format(who, doc.title))
	return _client_followup_rows(room)


# ---- the chase ----


def books_client_chase():
	"""Cron (workday mornings): one gentle reminder per room per day while
	anything is outstanding and stale."""
	frappe.set_user("Administrator")
	tdy = getdate(today())
	if tdy.weekday() not in _workday_set():
		return
	rooms, _c = _accounting_rooms()
	for room in rooms:
		qs = frappe.get_all(
			"Duty Books Query",
			filters={"room": room.name, "status": "Open"},
			fields=["name", "creation", "last_reminded"],
		)
		rs = frappe.get_all(
			"Duty Books Request",
			filters={"room": room.name, "status": "Requested"},
			fields=["name", "due_date", "creation", "last_reminded"],
		)
		due_q = [
			q for q in qs
			if _working_days_between(getdate(q.last_reminded or q.creation), tdy) >= CHASE_EVERY_WD
		]
		due_r = [
			r for r in rs
			if (r.due_date and getdate(r.due_date) <= tdy or _working_days_between(getdate(r.creation), tdy) >= CHASE_EVERY_WD)
			and _working_days_between(getdate(r.last_reminded or r.creation), tdy) >= CHASE_EVERY_WD
		]
		if not due_q and not due_r:
			continue
		bits = []
		if due_q:
			bits.append(_("{0} question(s)").format(len(due_q)))
		if due_r:
			bits.append(_("{0} document(s)").format(len(due_r)))
		try:
			roomdoc = frappe.get_doc("Client Room", room.name)
			_post(roomdoc, _("🔔 Gentle reminder: {0} from your accounting team are awaiting your response — see the portal home.").format(" and ".join(bits)))
			for x in due_q:
				frappe.db.set_value("Duty Books Query", x.name, "last_reminded", today(), update_modified=False)
			for x in due_r:
				frappe.db.set_value("Duty Books Request", x.name, "last_reminded", today(), update_modified=False)
			frappe.db.commit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "books chase")



def handle_communication(doc, method=None):
	"""doc_events hook (add manually to hooks.py):
	doc_events = {"Communication": {"after_insert": "duty_board.accounting.handle_communication"}}
	Email replies threaded to a query/request populate it. Requires an incoming
	Email Account on the site."""
	try:
		if doc.communication_type != "Communication" or doc.sent_or_received != "Received":
			return
		if doc.reference_doctype == "Duty Books Query":
			frappe.enqueue(
				"duty_board.accounting._process_query_reply",
				communication=doc.name,
				queue="short",
				enqueue_after_commit=True,
			)
		elif doc.reference_doctype == "Duty Books Request":
			# Attachments are saved AFTER the Communication is inserted, so
			# processing must wait for the transaction to commit.
			frappe.enqueue(
				"duty_board.accounting._process_request_reply",
				communication=doc.name,
				queue="short",
				enqueue_after_commit=True,
			)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "books inbound mail")


def _extract_reply_text(text_content, content):
	txt = (text_content or "").strip() or frappe.utils.strip_html(content or "").strip()
	if not txt:
		return ""
	lines = []
	for line in txt.splitlines():
		s = line.strip()
		if s.startswith(">"):
			break
		if s.startswith("On ") and s.endswith("wrote:"):
			break
		if s.startswith("From:") or s.startswith("-----Original Message"):
			break
		lines.append(line)
	out = "\n".join(lines).strip()
	return (out or txt)[:500]


def _process_query_reply(communication):
	try:
		doc = frappe.db.get_value(
			"Communication",
			communication,
			["name", "reference_doctype", "reference_name", "sender", "sender_full_name", "text_content", "content"],
			as_dict=True,
		)
		if not doc or doc.reference_doctype != "Duty Books Query" or not doc.reference_name:
			return
		q = frappe.db.get_value("Duty Books Query", doc.reference_name, ["room", "status"], as_dict=True)
		if not q or q.status != "Open":
			return
		answer = _extract_reply_text(doc.text_content, doc.content)
		if not answer:
			frappe.log_error(f"Empty reply text for {communication}", "books query reply")
			return
		who = doc.sender_full_name or doc.sender or "Client"
		frappe.db.set_value(
			"Duty Books Query",
			doc.reference_name,
			{"status": "Answered", "answer": answer, "answered_on": frappe.utils.now_datetime(), "answered_by": who},
			update_modified=False,
		)
		room = frappe.get_doc("Client Room", q.room)
		_post(room, "💬 {0} answered an accounting question by email: {1}".format(who, answer[:120]))
		frappe.db.commit()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "books query reply")


def _process_request_reply(communication):
	doc = frappe.db.get_value(
		"Communication",
		communication,
		["name", "reference_doctype", "reference_name", "sender", "sender_full_name"],
		as_dict=True,
	)
	if not doc or doc.reference_doctype != "Duty Books Request" or not doc.reference_name:
		return
	r = frappe.db.get_value(
		"Duty Books Request", doc.reference_name, ["room", "status", "title"], as_dict=True
	)
	if not r or r.status != "Requested":
		return
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": doc.name},
		fields=["file_url", "file_name"],
	)
	if not files:
		return
	who = doc.sender_full_name or doc.sender or "Client"
	f = files[0]
	frappe.db.set_value(
		"Duty Books Request",
		doc.reference_name,
		{
			"status": "Received",
			"attachment_url": f.file_url,
			"attachment_name": f.file_name,
			"fulfilled_on": frappe.utils.now_datetime(),
			"fulfilled_by": who,
		},
		update_modified=False,
	)
	shelf_title = "{0} — {1}".format(r.title, today()[:7])
	_file_to_shelf(r.room, shelf_title, f.file_url, f.file_name)
	for extra in files[1:]:
		_file_to_shelf(r.room, shelf_title, extra.file_url, extra.file_name)
	room = frappe.get_doc("Client Room", r.room)
	_post(room, "📎 {0} sent {1} by email — filed to your Documents.".format(who, r.title))
	frappe.db.commit()


def books_reprocess_inbound(days=30):
	"""Sweep already-received email replies whose records never updated.
	Run: bench --site <site> execute duty_board.accounting.books_reprocess_inbound"""
	frappe.set_user("Administrator")
	since = frappe.utils.add_days(today(), -cint(days))
	comms = frappe.get_all(
		"Communication",
		filters={
			"communication_type": "Communication",
			"sent_or_received": "Received",
			"reference_doctype": ["in", ["Duty Books Query", "Duty Books Request"]],
			"creation": [">=", since],
		},
		fields=["name", "reference_doctype", "reference_name", "sender", "sender_full_name", "text_content", "content"],
		order_by="creation asc",
	)
	q_done = r_done = 0
	for c in comms:
		if c.reference_doctype == "Duty Books Query":
			before = frappe.db.get_value("Duty Books Query", c.reference_name, "status")
			_process_query_reply(c.name)
			if before == "Open" and frappe.db.get_value("Duty Books Query", c.reference_name, "status") == "Answered":
				q_done += 1
		else:
			before = frappe.db.get_value("Duty Books Request", c.reference_name, "status")
			_process_request_reply(c.name)
			if before == "Requested" and frappe.db.get_value("Duty Books Request", c.reference_name, "status") == "Received":
				r_done += 1
	frappe.db.commit()
	print(f"Reprocessed: {q_done} query answer(s), {r_done} request fulfilment(s) from {len(comms)} candidate communication(s).")


# ---------------- the Books face: access + pulse ----------------


@frappe.whitelist()
def books_access():
	"""Who sees the Books face, and where they land."""
	_staff_only()
	if _books_manager():
		return {"allowed": 1, "manager": 1, "tab": "matrix"}
	rooms, _c = _accounting_rooms()
	if any(r.bookkeeper == frappe.session.user for r in rooms):
		return {"allowed": 1, "manager": 0, "tab": "round"}
	return {"allowed": 0}


@frappe.whitelist()
def books_pulse(period=None):
	_staff_only()
	period = (period or today()[:7]).strip()[:7]
	rooms, custs = _accounting_rooms()
	names = [r.name for r in rooms]
	insts = frappe.get_all(
		"Duty Service Deliverable",
		filters={"period": period, "room": ["in", names] if names else ["is", "set"]},
		fields=["status", "due_date"],
	)
	tdy = getdate(today())
	done = sum(1 for i in insts if i.status in ("Delivered", "Acknowledged"))
	late = sum(
		1 for i in insts if i.due_date and getdate(i.due_date) < tdy and i.status not in ("Delivered", "Acknowledged")
	)
	reg = _register_data(period)
	neglect = sum(1 for r in reg["rooms"] if r["neglected"])
	out = {
		"period": period,
		"clients": len(rooms),
		"done": done,
		"total": len(insts),
		"late": late,
		"neglect": neglect,
		"open_q": frappe.db.count("Duty Books Query", {"status": ["!=", "Resolved"], "room": ["in", names]}) if names else 0,
		"open_r": frappe.db.count("Duty Books Request", {"status": "Requested", "room": ["in", names]}) if names else 0,
	}
	if _books_manager():
		out["fee_total"] = sum(flt(custs.get(r.customer, frappe._dict()).get("accounting_fees")) for r in rooms)
	return out


# ---------------- onboarding runbook ----------------

DEFAULT_ONBOARDING = [
	"Access collected — bank read-only confirmed working",
	"Access Register populated (every access held, granted date)",
	"ERP user & Accounts role provisioned on client site",
	"Opening balances verified against last statements",
	"Chart of accounts reviewed & aligned to templates",
	"Prior-period documents collected to the Hub",
	"Portal members invited (client admin named)",
	"Service tier set (optionals ticked in client setup)",
	"First close date agreed & communicated",
]


def _onboarding_steps_template():
	try:
		raw = (frappe.get_cached_doc("Duty Settings").get("books_onboarding_steps") or "").strip()
		if raw:
			return [l.strip() for l in raw.splitlines() if l.strip()]
	except Exception:
		pass
	return DEFAULT_ONBOARDING


def _spawn_onboarding(room_name, customer):
	if frappe.db.exists("Duty Books Onboarding", {"room": room_name}):
		return 0
	for i, step in enumerate(_onboarding_steps_template()):
		frappe.get_doc(
			{
				"doctype": "Duty Books Onboarding",
				"room": room_name,
				"customer": customer,
				"step": step,
				"sort_order": i,
				"status": "Open",
			}
		).insert(ignore_permissions=True)
	return 1


@frappe.whitelist()
def books_start_onboarding(room):
	_staff_only()
	customer = frappe.db.get_value("Client Room", room, "customer")
	n = _spawn_onboarding(room, customer)
	frappe.db.commit()
	return {"started": n}


@frappe.whitelist()
def books_onboarding():
	_staff_only()
	rooms, _c = _accounting_rooms()
	names = [r.name for r in rooms]
	rows = frappe.get_all(
		"Duty Books Onboarding",
		filters={"room": ["in", names] if names else ["is", "set"]},
		fields=["name", "room", "customer", "step", "sort_order", "status", "done_on", "done_by", "note"],
		order_by="customer asc, sort_order asc",
	)
	by_room = {}
	for r in rows:
		r.done_on = str(r.done_on)[:16] if r.done_on else None
		by_room.setdefault(r.room, {"room": r.room, "customer": r.customer, "steps": []})["steps"].append(r)
	active, complete = [], []
	for v in by_room.values():
		total = len(v["steps"])
		done = sum(1 for s in v["steps"] if s.status == "Done")
		v["done"] = done
		v["total"] = total
		(complete if done == total else active).append(v)
	not_started = [
		{"room": r.name, "customer": r.customer}
		for r in sorted(rooms, key=lambda x: x.customer or "")
		if r.name not in by_room
	]
	return {"active": active, "complete": complete, "not_started": not_started}


@frappe.whitelist()
def books_tick_onboarding(name, done=1, note=None):
	_staff_only()
	doc = frappe.get_doc("Duty Books Onboarding", name)
	vals = {
		"status": "Done" if cint(done) else "Open",
		"done_on": frappe.utils.now_datetime() if cint(done) else None,
		"done_by": frappe.utils.get_fullname(frappe.session.user) if cint(done) else None,
	}
	if note is not None:
		vals["note"] = (note or "").strip()[:300] or None
	doc.db_set(vals, update_modified=False)
	frappe.db.commit()
	if cint(done) and not frappe.db.exists("Duty Books Onboarding", {"room": doc.room, "status": "Open"}):
		room = frappe.get_doc("Client Room", doc.room)
		_post(room, _("🚀 {0} is fully onboarded — welcome aboard!").format(room.customer))
	return books_onboarding()
