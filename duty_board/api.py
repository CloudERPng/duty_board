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
EXPECTED_DUTY_HOURS = 8
EXPECTED_BREAK_HOURS = 1
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
	board = get_board()
	if (reason or "").strip() == END_OF_DAY:
		board["day_summary"] = _day_numbers(frappe.session.user)
	return board


def _day_numbers(user):
	"""The user's day in numbers, computed right after end-of-day clock out."""
	start, end = user_day_window(user)
	logs = frappe.get_all(
		"Duty Log",
		filters={"user": user, "log_time": ["between", [start, end]]},
		fields=["log_type", "reason", "log_time"],
		order_by="log_time asc",
	)

	duty = 0
	brk = 0
	open_in = None
	break_out = None
	for log in logs:
		if log.log_type == "Clock In":
			if break_out:
				brk += time_diff_in_seconds(log.log_time, break_out)
				break_out = None
			open_in = log.log_time
		else:
			if open_in:
				duty += time_diff_in_seconds(log.log_time, open_in)
				open_in = None
			if _is_break(log.reason):
				break_out = log.log_time

	sessions = frappe.get_all(
		"Work Session",
		filters={"user": user, "start_time": ["between", [start, end]]},
		fields=["customer", "duration", "end_time", "start_time"],
	)
	now = now_datetime()
	task = 0
	cust = 0
	for s in sessions:
		secs = s.duration or 0
		if not s.end_time:
			secs = time_diff_in_seconds(now, s.start_time)
		task += secs
		if s.customer:
			cust += secs

	expected_duty = EXPECTED_DUTY_HOURS * 3600
	expected_break = EXPECTED_BREAK_HOURS * 3600

	remarks = []
	if duty < expected_duty:
		remarks.append(
			{
				"kind": "warn",
				"text": _("You were on duty {0} less than the expected {1} hours today.").format(
					_fmt_hm(expected_duty - duty), EXPECTED_DUTY_HOURS
				),
			}
		)
	else:
		remarks.append(
			{
				"kind": "good",
				"text": _("You met the expected {0} hours on duty. Well done.").format(
					EXPECTED_DUTY_HOURS
				),
			}
		)
	if brk > expected_break:
		remarks.append(
			{
				"kind": "warn",
				"text": _("You took {0} more break time than the {1} hour allowance.").format(
					_fmt_hm(brk - expected_break), EXPECTED_BREAK_HOURS
				),
			}
		)
	elif brk:
		remarks.append(
			{"kind": "good", "text": _("Break time stayed within the allowance.")}
		)

	return {
		"expected_duty": expected_duty,
		"expected_break": expected_break,
		"duty": int(duty),
		"task": int(task),
		"breaks": int(brk),
		"customer": int(cust),
		"remarks": remarks,
	}


def _fmt_hm(seconds):
	seconds = int(seconds)
	h, m = seconds // 3600, round((seconds % 3600) / 60)
	return f"{h}h {m}m" if h else f"{m}m"


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

	if mention_list:
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		body = (message or attachment_name or "").strip()[:120]
		for m in mention_list:
			if m != frappe.session.user:
				_push_safe(m, _("{0} mentioned you in Duty Room").format(first), body)
	return payload


@frappe.whitelist()
def get_messages(limit=50, before=None, after=None):
	filters = {}
	if before:
		filters["creation"] = ["<", before]
	if after:
		filters["creation"] = [">", after]
	rows = frappe.get_all(
		"Team Message",
		filters=filters,
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
	has_more = len(rows) >= min(cint(limit) or 50, 200)
	rows.reverse()
	reactions = _reactions_for([r.name for r in rows])
	seen = {
		s.user: str(s.last_seen)
		for s in frappe.get_all("Chat Seen", fields=["user", "last_seen"])
	}
	return {
		"messages": [_message_payload(r, reactions) for r in rows],
		"seen": seen,
		"has_more": has_more,
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
def add_todo(description, customer=None, for_user=None, for_users=None, date=None, due_time=None):
	session = frappe.session.user
	if not (description or "").strip():
		frappe.throw(_("Please type the to-do first."))

	targets = _parse_targets(for_users) or ([for_user] if for_user else [session])
	for target in targets:
		_create_todo_for(target, description, customer, date, due_time)
	frappe.db.commit()
	return get_board()


def _parse_targets(for_users):
	if not for_users:
		return None
	try:
		parsed = frappe.parse_json(for_users)
	except Exception:
		return None
	if not isinstance(parsed, list):
		return None
	targets = [t for t in parsed if isinstance(t, str)]
	return list(dict.fromkeys(targets)) or None


def _validate_target(target):
	if target == frappe.session.user:
		return
	exists = frappe.db.get_value("User", target, ["enabled", "user_type"], as_dict=True)
	if not exists or not exists.enabled or exists.user_type != "System User":
		frappe.throw(_("Cannot assign to {0}.").format(target))


def _create_todo_for(target, description, customer=None, date=None, due_time=None, notify=True):
	session = frappe.session.user
	_validate_target(target)
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
	if notify and target != session:
		first = frappe.utils.get_fullname(session).split(" ")[0]
		_notify_user(target, _("New to-do from {0}").format(first), description.strip())


def _notify_user(user, title, body):
	frappe.publish_realtime(
		"duty_board_notify", {"title": title, "body": body or ""}, user=user
	)
	_push_safe(user, title, body)


def parse_mentions(text):
	"""Find @first-name or @email mentions of enabled staff in free text."""
	if not text or "@" not in text:
		return []
	low = text.lower()
	mentioned = []
	for u in frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
	):
		first = (u.full_name or u.name).split(" ")[0].lower()
		if f"@{first}" in low or f"@{u.name.lower()}" in low:
			mentioned.append(u.name)
	return mentioned


def _push_safe(user, title, body):
	try:
		from duty_board.push import push_to_user

		push_to_user(user, title, body or "")
	except Exception:
		pass


@frappe.whitelist()
def share_todo(name, users):
	doc = frappe.get_doc("Daily Todo", name)
	_check_todo_owner(doc)
	targets = _parse_targets(users) or []
	if not targets:
		frappe.throw(_("Pick at least one colleague."))
	for target in targets:
		if target == doc.user:
			continue
		_create_todo_for(target, doc.description, doc.customer, doc.date, doc.due_time)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def update_todo(name, description=None, customer=None, due_time=None):
	doc = frappe.get_doc("Daily Todo", name)
	_check_todo_owner(doc)
	if description is not None and description.strip():
		doc.description = description.strip()
	doc.customer = customer or None
	doc.due_time = due_time or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def invite_to_task(users):
	user = frappe.session.user
	running = _get_running_session(user)
	if not running:
		frappe.throw(_("You have no task running."))
	targets = _parse_targets(users) or []
	if not targets:
		frappe.throw(_("Pick at least one colleague."))
	first = frappe.utils.get_fullname(user).split(" ")[0]
	for target in targets:
		if target == user:
			continue
		_create_todo_for(target, running.activity, running.customer, None, None, notify=False)
		_notify_user(target, _("{0} invited you to a task").format(first), running.activity)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def set_task_customer(customer=None):
	user = frappe.session.user
	running = _get_running_session(user)
	if not running:
		frappe.throw(_("You have no task running."))
	doc = frappe.get_doc("Work Session", running.name)
	doc.customer = customer or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_board()


@frappe.whitelist()
def add_task_note(session, note):
	if not (note or "").strip():
		frappe.throw(_("Note is empty."))
	owner = frappe.db.get_value("Work Session", session, "user")
	if not owner:
		frappe.throw(_("Task not found."))
	if owner != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("You can only add notes to your own tasks."))
	frappe.get_doc(
		{
			"doctype": "Task Note",
			"work_session": session,
			"user": frappe.session.user,
			"note": note.strip(),
		}
	).insert()
	frappe.db.commit()
	return get_task_notes(session)


@frappe.whitelist()
def get_task_history(before=None, limit=60):
	"""The current user's past work sessions (before their local today), newest first."""
	user = frappe.session.user
	start_today, _end = user_day_window(user)
	cutoff = before or str(start_today)
	cap = min(cint(limit) or 60, 200)
	rows = frappe.get_all(
		"Work Session",
		filters={"user": user, "start_time": ["<", cutoff]},
		fields=["name", "activity", "customer", "start_time", "end_time", "duration"],
		order_by="start_time desc",
		limit=cap,
	)
	has_more = len(rows) >= cap
	next_before = str(rows[-1].start_time) if rows else None

	counts = {}
	names = [r.name for r in rows]
	if names:
		for nc in frappe.get_all(
			"Task Note",
			filters={"work_session": ["in", names]},
			fields=["work_session", "count(name) as cnt"],
			group_by="work_session",
		):
			counts[nc.work_session] = nc.cnt

	for r in rows:
		r.notes = counts.get(r.name, 0)
		r.date = str(getdate(r.start_time))
		r.start_time = str(r.start_time)
		r.end_time = str(r.end_time) if r.end_time else None

	return {"sessions": rows, "has_more": has_more, "next_before": next_before}


@frappe.whitelist()
def get_task_notes(session):
	rows = frappe.get_all(
		"Task Note",
		filters={"work_session": session},
		fields=["user", "full_name", "note", "creation"],
		order_by="creation asc",
	)
	for r in rows:
		r.creation = str(r.creation)
	return rows


# ---------------- Issues ----------------

SEVERITIES = ["Low", "Medium", "High", "Critical"]
ISSUE_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]


def _issue_member_check(doc):
	session = frappe.session.user
	if "System Manager" in frappe.get_roles():
		return
	members = {a.user for a in (doc.assignees or [])}
	members.add(doc.raised_by)
	if session not in members:
		frappe.throw(_("Only the raiser or an assignee can update this issue."))


# ---------------- SLA engine: promises in business hours ----------------
# Business hours: Mon-Fri 09:00-18:00 site time. (ack_hours, resolve_hours)
SLA_MATRIX = {
	"Critical": (1, 4),
	"High": (2, 8),
	"Medium": (8, 24),
	"Low": (24, 40),
}
BH_START, BH_END = 9, 18


def _bh_snap(dt):
	from datetime import timedelta

	while True:
		if dt.weekday() >= 5:
			dt = (dt + timedelta(days=1)).replace(hour=BH_START, minute=0, second=0, microsecond=0)
			continue
		if dt.hour < BH_START:
			return dt.replace(hour=BH_START, minute=0, second=0, microsecond=0)
		if dt.hour >= BH_END:
			dt = (dt + timedelta(days=1)).replace(hour=BH_START, minute=0, second=0, microsecond=0)
			continue
		return dt


def _bh_add(start, hours):
	from datetime import timedelta

	minutes = int(hours * 60)
	cur = _bh_snap(start)
	while minutes > 0:
		eod = cur.replace(hour=BH_END, minute=0, second=0, microsecond=0)
		avail = int((eod - cur).total_seconds() // 60)
		chunk = min(minutes, avail)
		cur += timedelta(minutes=chunk)
		minutes -= chunk
		if minutes > 0:
			cur = _bh_snap(cur)
	return cur


def _bh_between(a, b):
	from datetime import timedelta

	if b <= a:
		return 0
	cur = _bh_snap(a)
	total = 0
	while cur < b:
		eod = cur.replace(hour=BH_END, minute=0, second=0, microsecond=0)
		stop = min(eod, b)
		if stop > cur:
			total += int((stop - cur).total_seconds() // 60)
		cur = _bh_snap(eod + timedelta(minutes=1))
	return total


def _bh_fmt(minutes):
	if minutes < 60:
		return f"{minutes}m"
	h, m = minutes // 60, minutes % 60
	return f"{h}h {m}m" if m else f"{h}h"


def sla_dues(severity, start):
	ack_h, res_h = SLA_MATRIX.get(severity or "Medium", SLA_MATRIX["Medium"])
	return _bh_add(start, ack_h), _bh_add(start, res_h)


def stamp_sla(doc_name, severity, start):
	try:
		ack_due, res_due = sla_dues(severity, start)
		frappe.db.set_value(
			"Duty Issue",
			doc_name,
			{"sla_ack_due": ack_due, "sla_res_due": res_due},
			update_modified=False,
		)
	except Exception:
		pass


def _sla_state(due, done_at, met_flag):
	if not due:
		return None, None
	now = now_datetime()
	if done_at:
		return ("met" if cint(met_flag) else "missed"), None
	if now < due:
		return "pending", _bh_fmt(_bh_between(now, due)) + " left"
	return "overdue", _bh_fmt(_bh_between(due, now)) + " over"


def sla_warnings():
	from datetime import timedelta

	now = now_datetime()
	horizon = now + timedelta(hours=2)
	for due_f, warned_f, done_f, label in [
		("sla_ack_due", "sla_ack_warned", "acknowledged_at", "response"),
		("sla_res_due", "sla_res_warned", "resolved_at", "resolution"),
	]:
		rows = frappe.get_all(
			"Duty Issue",
			filters={
				"status": ["in", ["Open", "In Progress"]],
				due_f: ["<=", horizon],
				warned_f: 0,
			},
			fields=["name", "title", "customer", due_f, done_f],
			limit=50,
		)
		for r in rows:
			if r.get(done_f):
				continue
			frappe.db.set_value("Duty Issue", r.name, warned_f, 1, update_modified=False)
			assignees = frappe.get_all(
				"Duty Issue Assignee", filters={"parent": r.name}, pluck="user"
			)
			targets = assignees or [
				u.name
				for u in frappe.get_all(
					"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]
				)
				if frappe.db.exists("Duty Push Subscription", {"user": u.name})
			]
			overdue = now > r.get(due_f)
			for t in targets:
				_notify_user(
					t,
					(_("🔴 SLA {0} BREACHED · {1}") if overdue else _("⏳ SLA {0} due soon · {1}")).format(
						label, r.customer
					),
					r.title[:120],
				)
	frappe.db.commit()


def _issue_payload(doc):
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Duty Issue", "attached_to_name": doc.name},
		fields=["file_url", "file_name"],
		order_by="creation asc",
	)
	image_exts = ("png", "jpg", "jpeg", "gif", "webp")
	attachments = [
		{
			"file_url": f.file_url,
			"file_name": f.file_name,
			"is_image": (f.file_name or "").lower().rsplit(".", 1)[-1] in image_exts,
		}
		for f in files
	]
	working = [
		w.user
		for w in frappe.get_all(
			"Work Session",
			filters={"duty_issue": doc.name, "end_time": ["is", "not set"]},
			fields=["user"],
		)
	]
	return {
		"attachments": attachments,
		"working": working,
		"client_visible": cint(doc.client_visible or 0),
		"client_requested": cint(doc.client_requested or 0),
		"client_rating": doc.get("client_rating") or None,
		"sla": {
			"ack": dict(zip(("state", "detail"), _sla_state(doc.get("sla_ack_due"), doc.get("acknowledged_at"), doc.get("sla_ack_met")))),
			"res": dict(zip(("state", "detail"), _sla_state(doc.get("sla_res_due"), doc.get("resolved_at"), doc.get("sla_res_met")))),
		},
		"acknowledged_first": (
			frappe.utils.get_fullname(doc.acknowledged_by).split(" ")[0]
			if doc.get("acknowledged_by")
			else None
		),
		"name": doc.name,
		"title": doc.title,
		"customer": doc.customer,
		"severity": doc.severity,
		"status": doc.status,
		"due_date": str(doc.due_date) if doc.due_date else None,
		"raised_by": doc.raised_by,
		"description": doc.description,
		"resolution": doc.resolution,
		"resolved_at": str(doc.resolved_at) if doc.resolved_at else None,
		"source_type": doc.source_type,
		"source": doc.source,
		"created": str(doc.creation),
		"assignees": [a.user for a in (doc.assignees or [])],
	}


@frappe.whitelist()
def create_issue(
	title,
	customer,
	severity="Medium",
	due_date=None,
	description=None,
	assignees=None,
	source_type=None,
	source=None,
	attachments=None,
):
	if not (title or "").strip():
		frappe.throw(_("Please give the issue a title."))
	if not customer:
		frappe.throw(_("An issue must be tracked against a customer."))
	if severity not in SEVERITIES:
		severity = "Medium"

	targets = _parse_targets(assignees) or []
	for t in targets:
		_validate_target(t)

	doc = frappe.get_doc(
		{
			"doctype": "Duty Issue",
			"title": title.strip(),
			"customer": customer,
			"severity": severity,
			"status": "Open",
			"due_date": due_date or None,
			"description": (description or "").strip() or None,
			"raised_by": frappe.session.user,
			"source_type": source_type or "Manual",
			"source": source or None,
			"assignees": [{"user": t} for t in targets],
		}
	)
	doc.insert(ignore_permissions=True)
	stamp_sla(doc.name, severity, doc.creation)

	attach_urls = []
	if attachments:
		try:
			parsed = frappe.parse_json(attachments)
			if isinstance(parsed, list):
				attach_urls = [u for u in parsed if isinstance(u, str)][:10]
		except Exception:
			attach_urls = []
	for u in attach_urls:
		_link_upload_to_issue(u, doc.name)

	frappe.db.commit()

	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	for t in targets:
		if t != frappe.session.user:
			_notify_user(
				t,
				_("{0} issue from {1}").format(severity, first),
				f"{doc.name}: {doc.title}",
			)
	return _issue_payload(doc)


@frappe.whitelist()
def get_issue(name):
	doc = frappe.get_doc("Duty Issue", name)
	return _issue_payload(doc)


def _link_upload_to_issue(file_url, issue_name):
	fname = frappe.db.get_value(
		"File",
		{
			"file_url": file_url,
			"owner": frappe.session.user,
			"attached_to_name": ["is", "not set"],
		},
	)
	if fname:
		frappe.db.set_value(
			"File",
			fname,
			{"attached_to_doctype": "Duty Issue", "attached_to_name": issue_name},
			update_modified=False,
		)
	return fname


@frappe.whitelist()
def attach_to_issue(name, file_url):
	doc = frappe.get_doc("Duty Issue", name)
	_issue_member_check(doc)
	if not _link_upload_to_issue(file_url, doc.name):
		frappe.throw(_("Upload not found — try attaching again."))
	frappe.db.commit()
	return _issue_payload(frappe.get_doc("Duty Issue", name))


@frappe.whitelist()
def set_issue_visibility(name, visible):
	doc = frappe.get_doc("Duty Issue", name)
	_issue_member_check(doc)
	frappe.db.set_value("Duty Issue", name, "client_visible", cint(visible), update_modified=False)
	frappe.db.commit()
	return _issue_payload(frappe.get_doc("Duty Issue", name))


@frappe.whitelist()
def acknowledge_issue(name):
	doc = frappe.get_doc("Duty Issue", name)
	_issue_member_check(doc)
	if not doc.acknowledged_by:
		now = now_datetime()
		vals = {"acknowledged_by": frappe.session.user, "acknowledged_at": now}
		if doc.get("sla_ack_due"):
			vals["sla_ack_met"] = 1 if now <= doc.sla_ack_due else 0
		frappe.db.set_value("Duty Issue", name, vals, update_modified=False)
		frappe.db.commit()
		try:
			from duty_board.client_room import narrate_issue

			narrate_issue(name, "seen")
		except Exception:
			pass
	return _issue_payload(frappe.get_doc("Duty Issue", name))


@frappe.whitelist()
def duty_typing():
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	frappe.publish_realtime("duty_board_typing", {"who": first, "user": frappe.session.user})
	return {"ok": True}


@frappe.whitelist()
def start_issue_work(name):
	user = frappe.session.user
	doc = frappe.get_doc("Duty Issue", name)
	if doc.status not in ("Open", "In Progress"):
		frappe.throw(_("This issue is already {0}.").format(_(doc.status)))
	if not _is_clocked_in(user):
		frappe.throw(_("Clock in first before starting work on an issue."))

	# picking up an issue assigns you to it
	if user not in {a.user for a in (doc.assignees or [])}:
		doc.append("assignees", {"user": user})
	doc.status = "In Progress"
	if not doc.get("work_started_at"):
		doc.work_started_at = now_datetime()
	if not doc.get("acknowledged_by"):
		doc.acknowledged_by = user
		doc.acknowledged_at = now_datetime()
		if doc.get("sla_ack_due"):
			doc.sla_ack_met = 1 if doc.acknowledged_at <= doc.sla_ack_due else 0
	doc.save(ignore_permissions=True)
	try:
		from duty_board.client_room import narrate_issue

		narrate_issue(name, "started")
	except Exception:
		pass

	_stop_running_session(user)
	frappe.get_doc(
		{
			"doctype": "Work Session",
			"user": user,
			"activity": doc.title,
			"customer": doc.customer,
			"duty_issue": doc.name,
			"start_time": now_datetime(),
		}
	).insert()
	frappe.db.commit()
	return _issue_payload(frappe.get_doc("Duty Issue", name))


@frappe.whitelist()
def stop_issue_work(name):
	user = frappe.session.user
	doc = frappe.get_doc("Duty Issue", name)

	running = _get_running_session(user)
	if running and running.get("duty_issue") == name:
		s = frappe.get_doc("Work Session", running.name)
		s.end_time = now_datetime()
		s.save(ignore_permissions=True)

	# revert to Open only when nobody is actively working it anymore
	still_working = frappe.db.exists(
		"Work Session", {"duty_issue": name, "end_time": ["is", "not set"]}
	)
	if doc.status == "In Progress" and not still_working:
		doc.status = "Open"
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _issue_payload(frappe.get_doc("Duty Issue", name))


@frappe.whitelist()
def update_issue_status(name, status, resolution=None):
	if status not in ISSUE_STATUSES:
		frappe.throw(_("Unknown status."))
	doc = frappe.get_doc("Duty Issue", name)
	_issue_member_check(doc)
	if status in ("Resolved", "Closed"):
		running = _get_running_session(frappe.session.user)
		if running and running.get("duty_issue") == name:
			s = frappe.get_doc("Work Session", running.name)
			s.end_time = now_datetime()
			s.save(ignore_permissions=True)
	doc.status = status
	if resolution:
		doc.resolution = resolution.strip()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	if status in ("Resolved", "Closed"):
		fresh = frappe.db.get_value(
			"Duty Issue", name, ["resolved_at", "sla_res_due"], as_dict=True
		)
		if fresh and fresh.resolved_at and fresh.sla_res_due:
			frappe.db.set_value(
				"Duty Issue",
				name,
				"sla_res_met",
				1 if fresh.resolved_at <= fresh.sla_res_due else 0,
				update_modified=False,
			)
			frappe.db.commit()
		try:
			from duty_board.client_room import narrate_issue

			narrate_issue(name, "done")
		except Exception:
			pass

	if status in ("Resolved", "Closed"):
		actor = frappe.session.user
		first = frappe.utils.get_fullname(actor).split(" ")[0]
		recipients = {a.user for a in (doc.assignees or [])}
		recipients.add(doc.raised_by)
		recipients.discard(actor)
		for r in recipients:
			_notify_user(
				r,
				_("Issue {0} by {1}").format(status.lower(), first),
				f"{doc.name}: {doc.title}",
			)
	return _issue_payload(doc)


@frappe.whitelist()
def update_issue(name, severity=None, due_date=None, add_assignees=None):
	doc = frappe.get_doc("Duty Issue", name)
	_issue_member_check(doc)
	if severity and severity in SEVERITIES:
		doc.severity = severity
	doc.due_date = due_date or None
	new_targets = _parse_targets(add_assignees) or []
	existing = {a.user for a in (doc.assignees or [])}
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	for t in new_targets:
		if t in existing:
			continue
		_validate_target(t)
		doc.append("assignees", {"user": t})
		if t != frappe.session.user:
			_notify_user(
				t,
				_("Issue assigned by {0}").format(first),
				f"{doc.name}: {doc.title}",
			)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return _issue_payload(doc)


@frappe.whitelist()
def get_issues(scope="open"):
	filters = {}
	if scope == "resolved":
		filters["status"] = "Resolved"
	elif scope == "closed":
		filters["status"] = "Closed"
	elif scope == "all":
		pass
	else:
		filters["status"] = ["in", ["Open", "In Progress"]]

	issues = frappe.get_all(
		"Duty Issue",
		filters=filters,
		fields=[
			"name",
			"title",
			"customer",
			"severity",
			"status",
			"due_date",
			"raised_by",
			"creation",
			"resolved_at",
		],
		order_by="creation desc",
		limit=200,
	)
	if issues:
		rows = frappe.get_all(
			"Duty Issue Assignee",
			filters={"parenttype": "Duty Issue", "parent": ["in", [i.name for i in issues]]},
			fields=["parent", "user"],
		)
		by_issue = {}
		for r in rows:
			by_issue.setdefault(r.parent, []).append(r.user)
		for i in issues:
			i.assignees = by_issue.get(i.name, [])
			i.due_date = str(i.due_date) if i.due_date else None
			i.creation = str(i.creation)
			i.resolved_at = str(i.resolved_at) if i.resolved_at else None
	return issues


def _fetch_issues(statuses, order_by):
	issues = frappe.get_all(
		"Duty Issue",
		filters={"status": ["in", statuses]},
		fields=[
			"name",
			"title",
			"customer",
			"severity",
			"status",
			"due_date",
			"raised_by",
			"creation",
		],
		order_by=order_by,
		limit=200,
	)
	if issues:
		rows = frappe.get_all(
			"Duty Issue Assignee",
			filters={"parenttype": "Duty Issue", "parent": ["in", [i.name for i in issues]]},
			fields=["parent", "user"],
		)
		by_issue = {}
		for r in rows:
			by_issue.setdefault(r.parent, []).append(r.user)
		for i in issues:
			i.assignees = by_issue.get(i.name, [])
			i.due_date = str(i.due_date) if i.due_date else None
			i.creation = str(i.creation)
	return issues


def _open_issues():
	sev_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
	issues = _fetch_issues(["Open", "In Progress"], "creation asc")
	issues.sort(key=lambda i: (sev_order.get(i.severity, 9), i.due_date or "9999-12-31"))
	return issues


@frappe.whitelist()
def get_issues(status="open"):
	status_map = {
		"open": None,
		"resolved": ["Resolved"],
		"closed": ["Closed"],
		"all": ISSUE_STATUSES,
	}
	if status not in status_map:
		status = "open"
	if status == "open":
		return _open_issues()
	return _fetch_issues(status_map[status], "modified desc")


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
		fields=["name", "activity", "customer", "daily_todo", "duty_issue", "project_task", "start_time"],
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
def delete_message(name):
	"""System Managers only: remove a Duty Room message everywhere.
	Cascades attached files and reactions, then tells every open client."""
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only System Managers can delete messages."))
	if not frappe.db.exists("Team Message", name):
		frappe.throw(_("Message not found — perhaps already deleted."))
	frappe.db.delete("Message Reaction", {"message": name})
	frappe.delete_doc("Team Message", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	frappe.publish_realtime("duty_board_message_deleted", {"name": name})
	return {"ok": True}


def _rooms_joins_board_safe():
	try:
		from duty_board.client_room import _pending_joins_safe

		return _pending_joins_safe()
	except Exception:
		return 0


def _rooms_unread_board_safe(user):
	try:
		from duty_board.client_room import _rooms_unread_safe

		return _rooms_unread_safe(user)
	except Exception:
		return 0


def _dm_unread_safe(user):
	try:
		from duty_board.dm import get_unread_map

		return get_unread_map(user)
	except Exception:
		return {}


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
		fields=["name", "user", "activity", "customer", "daily_todo", "duty_issue", "project_task", "start_time"],
		order_by="start_time desc",
	)
	running_by_user = {}
	for s in running:
		running_by_user.setdefault(s.user, s)

	all_sessions = frappe.get_all(
		"Work Session",
		filters={"start_time": ["between", [global_start, global_end]]},
		fields=["name", "user", "activity", "customer", "start_time", "end_time", "duration"],
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

	note_names = list({s.name for s in all_sessions} | {s.name for s in running})
	note_counts = {}
	if note_names:
		for nc in frappe.get_all(
			"Task Note",
			filters={"work_session": ["in", note_names]},
			fields=["work_session", "count(name) as cnt"],
			group_by="work_session",
		):
			note_counts[nc.work_session] = nc.cnt
	for s in all_sessions:
		s.notes = note_counts.get(s.name, 0)

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
		"project_task",
		"project",
		"lead",
		"lead_title",
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
				"name": sess.name,
				"notes": note_counts.get(sess.name, 0),
				"issue": sess.duty_issue,
				"card": sess.project_task,
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
		fields=["name", "activity", "customer", "start_time", "end_time", "duration"],
		order_by="start_time desc",
		limit=10,
	)
	for s in my_sessions:
		if not s.end_time:
			s.duration = int(time_diff_in_seconds(now, s.start_time))
		s.notes = note_counts.get(s.name, 0)

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

	issues = _open_issues()

	return {
		"me": me,
		"board": board,
		"my_sessions": my_sessions,
		"my_todos": todos_by_user.get(session, []),
		"my_upcoming": my_upcoming,
		"overdue_count": overdue_count,
		"issues": issues,
		"dm_unread": _dm_unread_safe(session),
		"rooms_unread": _rooms_unread_board_safe(session),
		"rooms_joins": _rooms_joins_board_safe(),
		"server_time": str(now),
	}
