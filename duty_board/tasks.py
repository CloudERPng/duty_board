from datetime import datetime, time as dtime, timedelta

import frappe
from frappe.utils import add_to_date, getdate, time_diff_in_seconds, today

from duty_board.api import (
	AUTO_PREFIX,
	END_OF_DAY,
	_system_tz,
	_user_tz,
	user_today,
)

AUTO_REASON = "Auto clock-out (forgot to clock out)"


def _local_date_of(user, naive_system_dt):
	stz = _system_tz()
	return stz.localize(naive_system_dt).astimezone(_user_tz(user)).date()


def _local_end_of_day(user, local_date):
	"""23:59 of the user's local day, as naive system-timezone datetime."""
	utz = _user_tz(user)
	stz = _system_tz()
	end = utz.localize(datetime.combine(local_date, dtime(23, 59)))
	return end.astimezone(stz).replace(tzinfo=None)


def auto_clock_out():
	"""Runs hourly. Anyone whose last Duty Log is a Clock In from a previous
	*local* day gets clocked out at 23:59 of that local day; work sessions
	still running from a previous local day are closed the same way."""

	users = frappe.get_all("Duty Log", distinct=True, pluck="user")
	for user in users:
		last = frappe.get_all(
			"Duty Log",
			filters={"user": user},
			fields=["log_type", "log_time"],
			order_by="log_time desc",
			limit=1,
		)
		if not last or last[0].log_type != "Clock In":
			continue

		log_local_day = _local_date_of(user, last[0].log_time)
		if log_local_day >= user_today(user):
			continue  # still their today — leave them alone

		end_time = _local_end_of_day(user, log_local_day)
		if end_time <= last[0].log_time:
			end_time = add_to_date(last[0].log_time, seconds=30)

		frappe.get_doc(
			{
				"doctype": "Duty Log",
				"user": user,
				"log_type": "Clock Out",
				"log_time": end_time,
				"reason": AUTO_REASON,
			}
		).insert(ignore_permissions=True)

	stale = frappe.get_all(
		"Work Session",
		filters={"end_time": ["is", "not set"]},
		fields=["name", "user", "start_time"],
	)
	for s in stale:
		start_local_day = _local_date_of(s.user, s.start_time)
		if start_local_day >= user_today(s.user):
			continue
		doc = frappe.get_doc("Work Session", s.name)
		end_time = _local_end_of_day(s.user, start_local_day)
		if end_time <= doc.start_time:
			end_time = add_to_date(doc.start_time, seconds=30)
		doc.end_time = end_time
		doc.save(ignore_permissions=True)

	frappe.db.commit()


def weekly_digest():
	"""Monday morning email to System Managers: last week's duty hours,
	utilization, plan completion, top customers, and day summaries."""

	end = getdate(today()) - timedelta(days=getdate(today()).weekday() + 1)  # last Sunday
	start = end - timedelta(days=6)  # last Monday

	logs = frappe.get_all(
		"Duty Log",
		filters={"log_time": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]},
		fields=["user", "full_name", "log_type", "reason", "log_time", "day_summary"],
		order_by="log_time asc",
	)
	sessions = frappe.get_all(
		"Work Session",
		filters={"start_time": ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]},
		fields=["user", "customer", "start_time", "end_time", "duration"],
	)
	todos = frappe.get_all(
		"Daily Todo",
		filters={"date": ["between", [start, end]]},
		fields=["user", "status"],
	)

	staff = {}

	def s_for(user, full_name=None):
		return staff.setdefault(
			user,
			{
				"name": full_name or user,
				"duty": 0.0,
				"task": 0.0,
				"breaks": 0,
				"done": 0,
				"total": 0,
				"summaries": [],
			},
		)

	open_in = {}
	for log in logs:
		rec = s_for(log.user, log.full_name)
		if log.log_type == "Clock In":
			open_in[log.user] = log.log_time
		else:
			if open_in.get(log.user):
				rec["duty"] += time_diff_in_seconds(log.log_time, open_in[log.user]) / 3600.0
				open_in[log.user] = None
			reason = log.reason or ""
			if reason != END_OF_DAY and not reason.startswith(AUTO_PREFIX):
				rec["breaks"] += 1
			if log.day_summary:
				rec["summaries"].append(
					f"{getdate(log.log_time).strftime('%a %d %b')}: {log.day_summary}"
				)

	customers = {}
	for s in sessions:
		if not s.end_time:
			continue
		hrs = (s.duration or 0) / 3600.0
		s_for(s.user)["task"] += hrs
		if s.customer:
			customers[s.customer] = customers.get(s.customer, 0.0) + hrs

	for t in todos:
		rec = s_for(t.user)
		rec["total"] += 1
		if t.status == "Done":
			rec["done"] += 1

	if not staff:
		return  # nothing to report

	rows = ""
	for user, r in sorted(staff.items(), key=lambda x: -x[1]["duty"]):
		util = round(r["task"] / r["duty"] * 100) if r["duty"] else 0
		rows += (
			f"<tr><td>{frappe.utils.escape_html(r['name'])}</td>"
			f"<td align='right'>{r['duty']:.1f}</td>"
			f"<td align='right'>{r['task']:.1f}</td>"
			f"<td align='right'>{util}%</td>"
			f"<td align='right'>{r['done']}/{r['total']}</td>"
			f"<td align='right'>{r['breaks']}</td></tr>"
		)

	cust_rows = "".join(
		f"<tr><td>{frappe.utils.escape_html(c)}</td><td align='right'>{h:.1f}</td></tr>"
		for c, h in sorted(customers.items(), key=lambda x: -x[1])[:10]
	)

	summaries_html = ""
	for user, r in sorted(staff.items(), key=lambda x: x[1]["name"]):
		if r["summaries"]:
			items = "".join(
				f"<li>{frappe.utils.escape_html(s)}</li>" for s in r["summaries"]
			)
			summaries_html += f"<p><b>{frappe.utils.escape_html(r['name'])}</b></p><ul>{items}</ul>"

	overdue_html = ""
	if frappe.db.exists("DocType", "Duty Issue"):
		overdue = frappe.get_all(
			"Duty Issue",
			filters={
				"status": ["in", ["Open", "In Progress"]],
				"due_date": ["<", today()],
			},
			fields=["name", "title", "customer", "severity", "due_date"],
			order_by="due_date asc",
			limit=20,
		)
		if overdue:
			issue_rows = "".join(
				f"<tr><td>{i.name}</td>"
				f"<td>{frappe.utils.escape_html(i.title)}</td>"
				f"<td>{frappe.utils.escape_html(i.customer or '')}</td>"
				f"<td>{i.severity}</td>"
				f"<td>{i.due_date}</td></tr>"
				for i in overdue
			)
			overdue_html = f"""
	<h3 style="color:#B91C1C">&#9888; Overdue issues</h3>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
		<tr style="background:#B91C1C;color:#fff">
			<th>Ref</th><th>Title</th><th>Customer</th><th>Severity</th><th>Due</th>
		</tr>
		{issue_rows}
	</table>
	"""

	html = f"""
	<h2 style="color:#0F5C55">Duty Board — Week of {start.strftime('%d %b')} to {end.strftime('%d %b %Y')}</h2>
	<h3 style="color:#0E7490">Team summary</h3>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
		<tr style="background:#0F5C55;color:#fff">
			<th>Staff</th><th>Duty hrs</th><th>Task hrs</th><th>Utilization</th><th>Plan done</th><th>Breaks</th>
		</tr>
		{rows}
	</table>
	<h3 style="color:#0E7490">Top customers by support time</h3>
	<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
		<tr style="background:#0F5C55;color:#fff"><th>Customer</th><th>Hours</th></tr>
		{cust_rows or "<tr><td colspan='2'>No customer-tagged sessions</td></tr>"}
	</table>
	{overdue_html}
	<h3 style="color:#0E7490">End-of-day summaries</h3>
	{summaries_html or "<p>No summaries recorded.</p>"}
	<p style="color:#6B7280;font-size:12px">Automated weekly digest from Duty Board.</p>
	"""

	recipients = [
		u.name
		for u in frappe.get_all(
			"Has Role",
			filters={"role": "System Manager", "parenttype": "User"},
			fields=["parent as name"],
		)
		if frappe.db.get_value("User", u.name, "enabled")
		and u.name not in ("Administrator", "Guest")
	]
	recipients = sorted(set(recipients))
	if recipients:
		frappe.sendmail(
			recipients=recipients,
			subject=f"Duty Board weekly digest — {start.strftime('%d %b')} to {end.strftime('%d %b')}",
			message=html,
		)
