from datetime import datetime, time as dtime

import pytz

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	getdate,
	now_datetime,
	time_diff_in_seconds,
	today,
)

END_OF_DAY = "End of day"
AUTO_PREFIX = "Auto clock-out"
ALLOWED_EMOJIS = ["👍", "❤️", "😂", "🎉", "✅", "👀"]


# ---------------- Timezone helpers ----------------


def _system_tz():
	try:
		from frappe.utils import get_system_timezone

		return pytz.timezone(get_system_timezone())
	except Exception:
		return pytz.timezone(
			frappe.db.get_single_value("System Settings", "time_zone") or "UTC"
		)


def _user_tz(user):
	cache = getattr(frappe.local, "duty_tz_cache", None)
	if cache is None:
		cache = {}
		frappe.local.duty_tz_cache = cache
	if user not in cache:
		tz_name = frappe.db.get_value("User", user, "time_zone")
		try:
			cache[user] = pytz.timezone(tz_name) if tz_name else _system_tz()
		except Exception:
			cache[user] = _system_tz()
	return cache[user]


def user_now(user):
	"""Current time in the user's own timezone (aware)."""
	return _system_tz().localize(now_datetime()).astimezone(_user_tz(user))


def user_today(user):
	"""The user's local calendar date right now."""
	return user_now(user).date()


def user_day_window(user, day=None):
	"""The user's local day expressed as naive system-timezone datetimes,
	for querying log_time / start_time columns."""
	day = day or user_today(user)
	utz = _user_tz(user)
	stz = _system_tz()
	start = utz.localize(datetime.combine(day, dtime.min)).astimezone(stz)
	end = utz.localize(datetime.combine(day, dtime.max)).astimezone(stz)
	return start.replace(tzinfo=None), end.replace(tzinfo=None)


def _is_break(reason):
	reason = reason or ""
	return reason != END_OF_DAY and not reason.startswith(AUTO_PREFIX)


# ---------------- Clock in / out ----------------


@frappe.whitelist()
def clock_in():
	_make_log("Clock In")
	return get_board()


@frappe.whitelist()
def clock_out(reason=None, summary=None):
	if not reason:
		frappe.throw(_("Please give a reason for clocking out."))
	_stop_running_session(frappe.session.user)
	_make_log("Clock Out", reason, summary)
	return get_board()


# ---------------- Team chat ----------------


@frappe.whitelist()
def send_message(
	message=None,
	mentions=None,
	reply_to=None,
	reply_snippet=None,
	attachment=None,
	attachment_name=None,
	attachment_type=None,
):
	mention_list = []
	if mentions:
		try:
			parsed = frappe.parse_json(mentions)
			if isinstance(parsed, list):
				mention_list = [m for m in parsed if isinstance(m, str)][:50]
		except Exception:
			mention_list = []

	doc = frappe.get_doc(
		{
			"doctype": "Team Message",
			"user": frappe.session.user,
			"message": message,
			"mentions": frappe.as_json(mention_list) if mention_list else None,
			"reply_to": reply_to or None,
			"reply_snippet": (reply_snippet or "")[:140] or None,
			"attachment": attachment or None,
			"attachment_name": attachment_name or None,
			"attachment_type": attachment_type or None,
		}
	)
	doc.insert()

	if attachment:
		file_name = frappe.db.get_value(
			"File",
			{
				"file_url": attachment,
				"owner": frappe.session.user,
				"attached_to_name": ["is", "not set"],
			},
		)
		if file_name:
			frappe.db.set_value(
				"File",
				file_name,
				{"attached_to_doctype": "Team Message", "attached_to_name": doc.name},
				update_modified=False,
			)

	frappe.db.commit()
	payload = _message_payload(doc.as_dict(), {})
	frappe.publish_realtime("duty_board_message", payload)
	return payload


@frappe.whitelist()
def get_messages(limit=50):
	rows = frappe.get_all(
		"Team Message",
		fields=[
			"name",
			"user",
			"full_name",
			"message",
			"mentions",
			"reply_to",
			"reply_snippet",
			"attachment",
			"attachment_name",
			"attachment_type",
			"creation",
		],
		order_by="creation desc",
		limit=min(cint(limit) or 50, 200),
	)
	rows.reverse()
	reactions = _reactions_for([r.name for r in rows])
	seen = {
		s.user: str(s.last_seen)
		for s in frappe.get_all("Chat Seen", fields=["user", "last_seen"])
	}
	return {
		"messages": [_message_payload(r, reactions) for r in rows],
		"seen": seen,
	}


@frappe.whitelist()
def search_messages(query):
	query = (query or "").strip()
	if len(query) < 2:
		frappe.throw(_("Type at least 2 characters to search."))
	rows = frappe.get_all(
		"Team Message",
		filters=[
			["Team Message", "message", "like", f"%{query}%"],
		],
		fields=[
			"name",
			"user",
			"full_name",
			"message",
			"mentions",
			"reply_to",
			"reply_snippet",
			"attachment",
			"attachment_name",
			"attachment_type",
			"creation",
		],
		order_by="creation desc",
		limit=30,
	)
	return [_message_payload(r, {}) for r in rows]


@frappe.whitelist()
def set_chat_seen():
	user = frappe.session.user
	now = now_datetime()
	name = frappe.db.exists("Chat Seen", {"user": user})
	if name:
		frappe.db.set_value("Chat Seen", name, "last_seen", now, update_modified=False)
	else:
		frappe.get_doc(
			{"doctype": "Chat Seen", "user": user, "last_seen": now}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.publish_realtime(
		"duty_board_seen", {"user": user, "last_seen": str(now)}
	)
	return {"user": user, "last_seen": str(now)}


@frappe.whitelist()
def toggle_reaction(message, emoji):
	if emoji not in ALLOWED_EMOJIS:
		frappe.throw(_("That reaction is not available."))
	if not frappe.db.exists("Team Message", message):
		frappe.throw(_("Message not found."))
	user = frappe.session.user
	existing = frappe.db.exists(
		"Message Reaction", {"message": message, "user": user, "emoji": emoji}
	)
	if existing:
		frappe.delete_doc("Message Reaction", existing, ignore_permissions=True)
	else:
		frappe.get_doc(
			{
				"doctype": "Message Reaction",
				"message": message,
				"user": user,
				"emoji": emoji,
			}
		).insert()
	frappe.db.commit()
	reactions = _reactions_for([message]).get(message, {})
	frappe.publish_realtime(
		"duty_board_reaction", {"message": message, "reactions": reactions}
	)
	return reactions


def _reactions_for(names):
	if not names:
		return {}
	rows = frappe.get_all(
		"Message Reaction",
		filters={"message": ["in", names]},
		fields=["message", "user", "emoji"],
	)
	out = {}
	for r in rows:
		out.setdefault(r.message, {}).setdefault(r.emoji, []).append(r.user)
	return out


def _message_payload(r, reactions):
	mentions = []
	if r.get("mentions"):
		try:
			parsed = frappe.parse_json(r.get("mentions"))
			if isinstance(parsed, list):
				mentions = parsed
		except Exception:
			mentions = []
	return {
		"name": r.get("name"),
		"user": r.get("user"),
		"full_name": r.get("full_name") or r.get("user"),
		"message": r.get("message"),
		"mentions": mentions,
		"reply_to": r.get("reply_to"),
		"reply_snippet": r.get("reply_snippet"),
		"attachment": r.get("attachment"),
		"attachment_name": r.get("attachment_name"),
		"attachment_type": r.get("attachment_type"),
		"creation": str(r.get("creation")),
		"reactions": reactions.get(r.get("name"), {}),
	}


# ---------------- To-do list ----------------


@frappe.whitelist()
def add_todo(description, customer=None, for_user=None, date=None, due_time=None):
	session = frappe.session.user
	if not (description or "").strip():
		frappe.throw(_("Please type the to-do first."))

	target = for_user or session
	if target != session:
		exists = frappe.db.get_value(
			"User", target, ["enabled", "user_type"], as_dict=True
		)
		if not exists or not exists.enabled or exists.user_type != "System User":
			frappe.throw(_("Cannot assign to that user."))

	# "today" is the assignee's local today
	target_today = user_today(target)
	todo_date = getdate(date) if date else target_today
	if todo_date < target_today:
		todo_date = target_today

	frappe.get_doc(
		{
			"doctype": "Daily Todo",
			"user": target,
			"date": todo_date,
			"due_time": due_time or None,
			"description": description.strip(),
			"customer": customer or None,
			"status": "Open",
			"assigned_by": session if target != session else None,
		}
	).insert()
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def toggle_todo(name, done):
	doc = frappe.get_doc("Daily Todo", name)
	_check_todo_owner(doc)
	doc.status = "Done" if cint(done) else "Open"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def remove_todo(name):
	doc = frappe.get_doc("Daily Todo", name)
	_check_todo_owner(doc)
	frappe.delete_doc("Daily Todo", name, ignore_permissions=True)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def carry_todo(name):
	doc = frappe.get_doc("Daily Todo", name)
	_check_todo_owner(doc)
	if doc.status == "Done":
		frappe.throw(_("This to-do is already done."))
	doc.date = add_days(getdate(doc.date), 1)
	doc.carry_count = cint(doc.carry_count) + 1
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def carry_all():
	user = frappe.session.user
	names = frappe.get_all(
		"Daily Todo",
		filters={"user": user, "date": user_today(user), "status": "Open"},
		pluck="name",
	)
	tomorrow = add_days(user_today(user), 1)
	for name in names:
		doc = frappe.get_doc("Daily Todo", name)
		doc.date = tomorrow
		doc.carry_count = cint(doc.carry_count) + 1
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def bring_old_todos():
	user = frappe.session.user
	names = frappe.get_all(
		"Daily Todo",
		filters={"user": user, "date": ["<", user_today(user)], "status": "Open"},
		pluck="name",
	)
	for name in names:
		doc = frappe.get_doc("Daily Todo", name)
		doc.date = user_today(user)
		doc.carry_count = cint(doc.carry_count) + 1
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_board()


def _check_todo_owner(doc):
	if doc.user != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("You can only manage your own to-do list."))


def _complete_todo(name):
	if not name or not frappe.db.exists("Daily Todo", name):
		return
	doc = frappe.get_doc("Daily Todo", name)
	if doc.status != "Done":
		doc.status = "Done"
		doc.save(ignore_permissions=True)


def _sorted_todos(rows):
	return sorted(rows, key=lambda x: (str(x.due_time or "99:99:99"), str(x.name)))


# ---------------- Tasks ----------------


@frappe.whitelist()
def start_task(activity, customer=None, todo=None, complete_previous=0):
	user = frappe.session.user
	if not (activity or "").strip():
		frappe.throw(_("Please describe what you are working on."))
	if not _is_clocked_in(user):
		frappe.throw(_("Clock in first before starting a task."))

	previous = _stop_running_session(user)
	if cint(complete_previous) and previous and previous.daily_todo:
		_complete_todo(previous.daily_todo)

	frappe.get_doc(
		{
			"doctype": "Work Session",
			"user": user,
			"activity": activity.strip(),
			"customer": customer or None,
			"daily_todo": todo or None,
			"start_time": now_datetime(),
		}
	).insert()
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def stop_task(completed=0):
	user = frappe.session.user
	stopped = _stop_running_session(user)
	if cint(completed) and stopped and stopped.daily_todo:
		_complete_todo(stopped.daily_todo)
	frappe.db.commit()
	return get_board()


def _make_log(log_type, reason=None, summary=None):
	frappe.get_doc(
		{
			"doctype": "Duty Log",
			"user": frappe.session.user,
			"log_type": log_type,
			"log_time": now_datetime(),
			"reason": reason,
			"day_summary": summary,
		}
	).insert()
	frappe.db.commit()


def _is_clocked_in(user):
	start, end = user_day_window(user)
	last = frappe.get_all(
		"Duty Log",
		filters={"user": user, "log_time": ["between", [start, end]]},
		fields=["log_type"],
		order_by="log_time desc",
		limit=1,
	)
	return bool(last) and last[0].log_type == "Clock In"


def _get_running_session(user):
	rows = frappe.get_all(
		"Work Session",
		filters={"user": user, "end_time": ["is", "not set"]},
		fields=["name", "activity", "customer", "daily_todo", "start_time"],
		order_by="start_time desc",
		limit=1,
	)
	return rows[0] if rows else None


def _stop_running_session(user):
	running = _get_running_session(user)
	if running:
		doc = frappe.get_doc("Work Session", running.name)
		doc.end_time = now_datetime()
		doc.save()
	return running


# ---------------- Leave awareness ----------------


def _users_on_leave(user_ids):
	"""Users with an approved Leave Application covering their local today."""
	if not frappe.db.exists("DocType", "Leave Application"):
		return set()
	emp_map = {
		e.name: e.user_id
		for e in frappe.get_all(
			"Employee",
			filters={"user_id": ["in", user_ids]},
			fields=["name", "user_id"],
		)
	}
	if not emp_map:
		return set()
	on_leave = set()
	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": ["in", list(emp_map.keys())],
			"docstatus": 1,
			"status": "Approved",
			"from_date": ["<=", add_days(getdate(today()), 1)],
			"to_date": [">=", add_days(getdate(today()), -1)],
		},
		fields=["employee", "from_date", "to_date"],
	)
	for lv in leaves:
		uid = emp_map.get(lv.employee)
		if not uid:
			continue
		local_today = user_today(uid)
		if getdate(lv.from_date) <= local_today <= getdate(lv.to_date):
			on_leave.add(uid)
	return on_leave


# ---------------- The board ----------------


@frappe.whitelist()
def get_board():
	"""Current status of every enabled System User, each in their own local day."""
	now = now_datetime()
	session = frappe.session.user

	users = frappe.get_all(
		"User",
		filters={
			"enabled": 1,
			"user_type": "System User",
			"name": ["not in", ["Guest", "Administrator"]],
		},
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
	)
	user_ids = [u.name for u in users]

	windows = {u.name: user_day_window(u.name) for u in users}
	global_start = min(w[0] for w in windows.values()) if windows else now
	global_end = max(w[1] for w in windows.values()) if windows else now

	logs = frappe.get_all(
		"Duty Log",
		filters={"log_time": ["between", [global_start, global_end]]},
		fields=["user", "log_type", "reason", "log_time", "day_summary"],
		order_by="log_time asc",
	)
	logs_by_user = {}
	for log in logs:
		win = windows.get(log.user)
		if win and win[0] <= log.log_time <= win[1]:
			logs_by_user.setdefault(log.user, []).append(log)

	running = frappe.get_all(
		"Work Session",
		filters={"end_time": ["is", "not set"]},
		fields=["user", "activity", "customer", "daily_todo", "start_time"],
		order_by="start_time desc",
	)
	running_by_user = {}
	for s in running:
		running_by_user.setdefault(s.user, s)

	all_sessions = frappe.get_all(
		"Work Session",
		filters={"start_time": ["between", [global_start, global_end]]},
		fields=["user", "activity", "customer", "start_time", "end_time", "duration"],
		order_by="start_time asc",
	)
	sessions_by_user = {}
	for s in all_sessions:
		win = windows.get(s.user)
		if not (win and win[0] <= s.start_time <= win[1]):
			continue
		if not s.end_time:
			s.duration = int(time_diff_in_seconds(now, s.start_time))
		sessions_by_user.setdefault(s.user, []).append(s)

	todo_fields = [
		"name",
		"user",
		"date",
		"description",
		"customer",
		"status",
		"due_time",
		"assigned_by",
		"carry_count",
	]
	local_dates = {u.name: user_today(u.name) for u in users}
	todos = frappe.get_all(
		"Daily Todo",
		filters={"date": ["in", list(set(local_dates.values()))]},
		fields=todo_fields,
		order_by="creation asc",
	)
	todos_by_user = {}
	for t in todos:
		if getdate(t.date) != local_dates.get(t.user):
			continue
		t.due_time = str(t.due_time)[:5] if t.due_time else None
		todos_by_user.setdefault(t.user, []).append(t)
	for key in todos_by_user:
		todos_by_user[key] = _sorted_todos(todos_by_user[key])

	on_leave = _users_on_leave(user_ids)

	board = []
	for u in users:
		ulogs = logs_by_user.get(u.name, [])
		status, reason, since, summary = "Off Duty", None, None, None
		on_duty_seconds, open_in, breaks = 0, None, 0

		for log in ulogs:
			if log.log_type == "Clock In":
				open_in = log.log_time
			elif open_in:
				on_duty_seconds += time_diff_in_seconds(log.log_time, open_in)
				open_in = None
				if _is_break(log.reason):
					breaks += 1

		if ulogs:
			last = ulogs[-1]
			since = last.log_time
			if last.log_type == "Clock In":
				status = "On Duty"
				if open_in:
					on_duty_seconds += time_diff_in_seconds(now, open_in)
			elif (last.reason or "") == END_OF_DAY:
				status = "Done for the Day"
				reason = last.reason
				summary = last.day_summary
			else:
				status = "Away"
				reason = last.reason

		if status == "Off Duty" and u.name in on_leave:
			status = "On Leave"

		task = None
		sess = running_by_user.get(u.name)
		if sess and status == "On Duty":
			task = {
				"activity": sess.activity,
				"customer": sess.customer,
				"todo": sess.daily_todo,
				"start_time": str(sess.start_time),
				"seconds": int(time_diff_in_seconds(now, sess.start_time)),
			}

		utodos = todos_by_user.get(u.name, [])
		todos_done = sum(1 for t in utodos if t.status == "Done")

		board.append(
			{
				"user": u.name,
				"full_name": u.full_name or u.name,
				"user_image": u.user_image,
				"status": status,
				"reason": reason,
				"since": since,
				"on_duty_seconds": int(on_duty_seconds),
				"breaks": breaks,
				"task": task,
				"summary": summary,
				"todos_done": todos_done,
				"todos_total": len(utodos),
				"todos": utodos,
				"sessions": sessions_by_user.get(u.name, []),
			}
		)

	order = {
		"On Duty": 0,
		"Away": 1,
		"Done for the Day": 2,
		"On Leave": 3,
		"Off Duty": 4,
	}
	board.sort(key=lambda r: (order.get(r["status"], 9), r["full_name"].lower()))

	me = next((r for r in board if r["user"] == session), None)

	my_start, my_end = user_day_window(session)
	my_sessions = frappe.get_all(
		"Work Session",
		filters={"user": session, "start_time": ["between", [my_start, my_end]]},
		fields=["activity", "customer", "start_time", "end_time", "duration"],
		order_by="start_time desc",
		limit=10,
	)
	for s in my_sessions:
		if not s.end_time:
			s.duration = int(time_diff_in_seconds(now, s.start_time))

	my_today = user_today(session)
	my_upcoming = frappe.get_all(
		"Daily Todo",
		filters={"user": session, "date": [">", my_today], "status": "Open"},
		fields=todo_fields,
		order_by="date asc, creation asc",
		limit=30,
	)
	for t in my_upcoming:
		t.due_time = str(t.due_time)[:5] if t.due_time else None
		t.date = str(t.date)

	overdue_count = frappe.db.count(
		"Daily Todo",
		{"user": session, "date": ["<", my_today], "status": "Open"},
	)

	return {
		"me": me,
		"board": board,
		"my_sessions": my_sessions,
		"my_todos": todos_by_user.get(session, []),
		"my_upcoming": my_upcoming,
		"overdue_count": overdue_count,
		"server_time": str(now),
	}
