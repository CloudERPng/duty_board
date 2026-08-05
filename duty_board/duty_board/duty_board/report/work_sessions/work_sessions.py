import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date = filters.get("from_date") or today()
	to_date = filters.get("to_date") or today()

	conditions = {"start_time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]}
	if filters.get("user"):
		conditions["user"] = filters.user
	if filters.get("customer"):
		conditions["customer"] = filters.customer

	sessions = frappe.get_all(
		"Work Session",
		filters=conditions,
		fields=[
			"user",
			"full_name",
			"activity",
			"customer",
			"start_time",
			"end_time",
			"duration",
		],
		order_by="start_time desc",
	)

	now = now_datetime()
	data = []
	for s in sessions:
		duration = s.duration
		status = _("Completed")
		if not s.end_time:
			duration = time_diff_in_seconds(now, s.start_time)
			status = _("Running")
		data.append(
			{
				"date": s.start_time.date(),
				"full_name": s.full_name or s.user,
				"user": s.user,
				"activity": s.activity,
				"customer": s.customer,
				"start": s.start_time.time().strftime("%H:%M"),
				"end": s.end_time.time().strftime("%H:%M") if s.end_time else None,
				"hours": round((duration or 0) / 3600.0, 2),
				"status": status,
			}
		)

	return get_columns(), data


def get_columns():
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 105},
		{"fieldname": "full_name", "label": _("Staff"), "fieldtype": "Data", "width": 160},
		{"fieldname": "activity", "label": _("Working On"), "fieldtype": "Data", "width": 260},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 170,
		},
		{"fieldname": "start", "label": _("Start"), "fieldtype": "Data", "width": 80},
		{"fieldname": "end", "label": _("End"), "fieldtype": "Data", "width": 80},
		{"fieldname": "hours", "label": _("Hours"), "fieldtype": "Float", "width": 90},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 160,
		},
	]
