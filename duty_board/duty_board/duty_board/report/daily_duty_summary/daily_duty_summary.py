import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, time_diff_in_seconds, today

END_OF_DAY = "End of day"
AUTO_PREFIX = "Auto clock-out"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	from_date = filters.get("from_date") or today()
	to_date = filters.get("to_date") or today()

	conditions = {"log_time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]}
	if filters.get("user"):
		conditions["user"] = filters.user

	logs = frappe.get_all(
		"Duty Log",
		filters=conditions,
		fields=["user", "full_name", "log_type", "reason", "log_time", "day_summary"],
		order_by="log_time asc",
	)

	# task time per user per day
	sess_conditions = {
		"start_time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
	}
	if filters.get("user"):
		sess_conditions["user"] = filters.user
	sessions = frappe.get_all(
		"Work Session",
		filters=sess_conditions,
		fields=["user", "start_time", "end_time", "duration"],
	)

	now = now_datetime()
	task_seconds = {}
	for s in sessions:
		secs = s.duration or 0
		if not s.end_time:
			secs = time_diff_in_seconds(now, s.start_time)
		key = (getdate(s.start_time), s.user)
		task_seconds[key] = task_seconds.get(key, 0) + secs

	grouped = {}
	for log in logs:
		key = (getdate(log.log_time), log.user)
		grouped.setdefault(key, {"full_name": log.full_name or log.user, "logs": []})
		grouped[key]["logs"].append(log)

	data = []
	for (date, user), bundle in sorted(grouped.items()):
		ulogs = bundle["logs"]
		first_in = last_out = None
		total_seconds, open_in, breaks = 0, None, 0
		still_in = False
		day_summary = None

		for log in ulogs:
			if log.log_type == "Clock In":
				open_in = log.log_time
				if not first_in:
					first_in = log.log_time
			else:
				last_out = log.log_time
				if open_in:
					total_seconds += time_diff_in_seconds(log.log_time, open_in)
					open_in = None
				reason = log.reason or ""
				if reason != END_OF_DAY and not reason.startswith(AUTO_PREFIX):
					breaks += 1
				if log.day_summary:
					day_summary = log.day_summary

		if open_in:
			still_in = True
			if getdate(open_in) == getdate(now):
				total_seconds += time_diff_in_seconds(now, open_in)

		t_secs = task_seconds.get((date, user), 0)
		utilization = round(t_secs / total_seconds * 100, 1) if total_seconds else 0

		data.append(
			{
				"date": date,
				"user": user,
				"full_name": bundle["full_name"],
				"first_in": first_in.time().strftime("%H:%M") if first_in else None,
				"last_out": last_out.time().strftime("%H:%M") if last_out else None,
				"breaks": breaks,
				"hours": round(total_seconds / 3600.0, 2),
				"task_hours": round(t_secs / 3600.0, 2),
				"utilization": utilization,
				"day_summary": day_summary,
				"status": _("Still Clocked In") if still_in else _("Clocked Out"),
			}
		)

	return get_columns(), data


def get_columns():
	return [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 105},
		{"fieldname": "full_name", "label": _("Staff"), "fieldtype": "Data", "width": 160},
		{"fieldname": "first_in", "label": _("First In"), "fieldtype": "Data", "width": 85},
		{"fieldname": "last_out", "label": _("Last Out"), "fieldtype": "Data", "width": 85},
		{"fieldname": "breaks", "label": _("Breaks"), "fieldtype": "Int", "width": 75},
		{"fieldname": "hours", "label": _("Duty Hours"), "fieldtype": "Float", "width": 100},
		{"fieldname": "task_hours", "label": _("Task Hours"), "fieldtype": "Float", "width": 100},
		{
			"fieldname": "utilization",
			"label": _("Utilization %"),
			"fieldtype": "Percent",
			"width": 105,
		},
		{
			"fieldname": "day_summary",
			"label": _("Day Summary"),
			"fieldtype": "Data",
			"width": 300,
		},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{
			"fieldname": "user",
			"label": _("User"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
	]
