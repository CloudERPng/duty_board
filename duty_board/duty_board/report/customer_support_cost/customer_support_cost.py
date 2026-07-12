import calendar

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, time_diff_in_seconds, today

HOURS_PER_DAY = 8
NO_CUSTOMER = "— No Customer —"


def execute(filters=None):
	if not frappe.db.exists("DocType", "Salary Structure Assignment"):
		frappe.throw(
			_("Salary Structure Assignment doctype not found. Please install the HRMS app.")
		)

	filters = frappe._dict(filters or {})
	from_date = filters.get("from_date") or today()
	to_date = filters.get("to_date") or today()

	conditions = {"start_time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]}
	if filters.get("customer"):
		conditions["customer"] = filters.customer
	if filters.get("user"):
		conditions["user"] = filters.user

	sessions = frappe.get_all(
		"Work Session",
		filters=conditions,
		fields=["user", "full_name", "customer", "start_time", "end_time", "duration"],
	)
	if not sessions:
		return get_columns(), []

	users = list({s.user for s in sessions})
	emp_by_user = {
		e.user_id: e.name
		for e in frappe.get_all(
			"Employee",
			filters={"user_id": ["in", users]},
			fields=["name", "user_id"],
		)
	}

	# all submitted salary structure assignments for these employees
	ssa_by_emp = {}
	if emp_by_user:
		for ssa in frappe.get_all(
			"Salary Structure Assignment",
			filters={
				"employee": ["in", list(emp_by_user.values())],
				"docstatus": 1,
			},
			fields=["employee", "from_date", "base"],
			order_by="from_date asc",
		):
			ssa_by_emp.setdefault(ssa.employee, []).append(ssa)

	now = now_datetime()
	rows = {}  # (customer, user) -> aggregate
	for s in sessions:
		seconds = s.duration or 0
		if not s.end_time:
			seconds = time_diff_in_seconds(now, s.start_time)
		hours = seconds / 3600.0
		if hours <= 0:
			continue

		start = get_datetime(s.start_time)
		base = _base_as_of(ssa_by_emp.get(emp_by_user.get(s.user)), start.date())
		rate = 0.0
		if base:
			workdays = _weekdays_in_month(start.year, start.month)
			rate = base / (workdays * HOURS_PER_DAY) if workdays else 0.0

		key = (s.customer or NO_CUSTOMER, s.user)
		row = rows.setdefault(
			key,
			{
				"customer": s.customer or NO_CUSTOMER,
				"full_name": s.full_name or s.user,
				"user": s.user,
				"hours": 0.0,
				"monthly_base": base or 0.0,
				"hourly_rate": rate,
				"cost": 0.0,
				"no_salary": not base,
			},
		)
		row["hours"] += hours
		row["cost"] += hours * rate

	data = sorted(rows.values(), key=lambda r: (r["customer"], -r["cost"]))
	for r in data:
		r["hours"] = round(r["hours"], 2)
		r["hourly_rate"] = round(r["hourly_rate"], 2)
		r["cost"] = round(r["cost"], 2)
		if r.pop("no_salary"):
			r["remark"] = _("No Salary Structure Assignment found")

	return get_columns(), data


def _base_as_of(ssa_list, date):
	"""Latest submitted assignment whose from_date is on or before the session date."""
	if not ssa_list:
		return 0
	base = 0
	for ssa in ssa_list:  # sorted ascending by from_date
		if ssa.from_date <= date:
			base = ssa.base or 0
		else:
			break
	# if all assignments start after the session date, use the earliest one
	return base or (ssa_list[0].base or 0)


def _weekdays_in_month(year, month):
	cal = calendar.Calendar()
	return sum(
		1
		for d in cal.itermonthdates(year, month)
		if d.month == month and d.weekday() < 5
	)


def get_columns():
	return [
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Data",
			"width": 200,
		},
		{"fieldname": "full_name", "label": _("Staff"), "fieldtype": "Data", "width": 170},
		{"fieldname": "hours", "label": _("Hours"), "fieldtype": "Float", "width": 90},
		{
			"fieldname": "monthly_base",
			"label": _("Monthly Base"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"fieldname": "hourly_rate",
			"label": _("Hourly Rate"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "cost",
			"label": _("Support Cost"),
			"fieldtype": "Currency",
			"width": 130,
		},
		{"fieldname": "remark", "label": _("Remark"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
	]
