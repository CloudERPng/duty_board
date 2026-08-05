# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Consultant email accountability — five flows, all consultant-only:

1. Assignment emails (issues and project tasks) with full details.
2. Closure confirmations when THEY resolve/close/complete.
3. Stale-issue reminders at 6/12/18/24 hours without an update from
   them (hourly sweep; the highest crossed unsent stage fires, lower
   stages are back-filled in the log so nothing double-sends).
4. A daily list of their pending (not resolved/closed) issues.
5. A Monday digest of last week's and month-to-date performance.

Scheduling ships as Scheduled Job Type RECORDS (created by
setup_email_jobs via bench execute) — the frappe scheduler picks them
up dynamically; hooks.py stays untouched, honouring the deploy ritual.
Nothing here is whitelisted: jobs run from the scheduler, senders are
called by api/projects/commercial code paths."""

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	flt,
	get_datetime,
	get_fullname,
	get_url,
	now_datetime,
	today,
)

from duty_board.permissions import is_consultant

BOARD_URL = "/app/duty-board"
BRAND = "#123C35"
ACCENT = "#0E8A63"
STAGES = (6, 12, 18, 24)


# ─────────────────────────── plumbing ───────────────────────────

def _send(user, subject, html):
	email = frappe.db.get_value("User", user, "email") or user
	try:
		frappe.sendmail(
			recipients=[email],
			subject=subject,
			message=html,
			delayed=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "duty notify send")


def _logged(user, kind, ref=None, stage=None, on=None):
	f = {"user": user, "kind": kind}
	if ref:
		f["ref_name"] = ref
	if stage is not None:
		f["stage"] = stage
	if on:
		f["sent_on"] = on
	return frappe.db.exists("Duty Notify Log", f)


def _log(user, kind, ref=None, stage=None, on=None):
	frappe.get_doc({
		"doctype": "Duty Notify Log",
		"user": user,
		"kind": kind,
		"ref_name": ref,
		"stage": stage,
		"sent_on": on or today(),
	}).insert(ignore_permissions=True)


def _shell(title, inner):
	return f"""
	<div style="max-width:620px;margin:0 auto;font-family:Segoe UI,Arial,sans-serif;color:#17211F">
		<div style="background:{BRAND};color:#E7F0EC;border-radius:12px 12px 0 0;padding:16px 22px;font-size:17px;font-weight:700">
			Duty Board · {title}
		</div>
		<div style="border:1px solid #E2E8E5;border-top:none;border-radius:0 0 12px 12px;padding:20px 22px;background:#fff">
			{inner}
			<div style="margin-top:22px">
				<a href="{get_url(BOARD_URL)}" style="background:{ACCENT};color:#fff;text-decoration:none;font-weight:700;padding:10px 22px;border-radius:9px;display:inline-block">Open Duty Board →</a>
			</div>
			<div style="margin-top:18px;font-size:11px;color:#8A9994">Xlevel Retail Systems · this mailbox is unmonitored.</div>
		</div>
	</div>"""


def _kv(rows):
	tr = "".join(
		f'<tr><td style="padding:5px 12px 5px 0;color:#65736F;font-size:12px;white-space:nowrap;vertical-align:top">{k}</td>'
		f'<td style="padding:5px 0;font-size:13px;font-weight:600">{frappe.utils.escape_html(str(v))}</td></tr>'
		for k, v in rows if v not in (None, "")
	)
	return f'<table style="border-collapse:collapse">{tr}</table>'


def _issue_rows(doc):
	from duty_board.api import _issue_cr

	cr = _issue_cr(doc)
	return [
		(_("Ticket"), doc.name),
		(_("Title"), doc.title),
		(_("Customer"), doc.customer),
		(_("Severity"), doc.severity),
		(_("Type"), doc.get("issue_type") or "Support"),
		(_("Status"), doc.status),
		(_("Due"), str(doc.due_date) if doc.due_date else None),
		(_("Change request"), cr and f'{cr["title"]} — {cr["chip"]}'),
		(_("Description"), (doc.description or "")[:600]),
	]


def _task_rows(doc):
	return [
		(_("Task"), doc.title),
		(_("Project"), frappe.db.get_value("Duty Project", doc.project, "title") or doc.project),
		(_("Customer"), frappe.db.get_value("Duty Project", doc.project, "customer")),
		(_("Urgency"), doc.urgency),
		(_("Column"), doc.column),
		(_("Due"), str(doc.due_date) if doc.due_date else None),
		(_("Description"), (doc.description or "")[:600]),
	]


# ────────────────────── 1 & 2: event senders ──────────────────────

def assignment_email(doc, users, kind="issue"):
	"""Full-detail assignment email — consultants only, never the actor."""
	for u in set(users or []):
		if not u or not is_consultant(u):
			continue
		rows = _issue_rows(doc) if kind == "issue" else _task_rows(doc)
		title = _("New ticket assigned to you") if kind == "issue" else _("New project task assigned to you")
		_send(
			u,
			f"[Duty Board] {title}: {doc.title[:80]}",
			_shell(title, _kv(rows)),
		)


def closure_email(doc, hours=None, kind="issue"):
	"""Confirmation receipt when a consultant closes their own work."""
	u = frappe.session.user
	if not is_consultant(u):
		return
	rows = _issue_rows(doc) if kind == "issue" else _task_rows(doc)
	if hours:
		rows.append((_("Hours logged"), flt(hours)))
	title = _("Closed: your ticket") if kind == "issue" else _("Completed: your task")
	_send(
		u,
		f"[Duty Board] {title} — {doc.title[:80]}",
		_shell(title, _kv(rows) + f'<p style="margin-top:14px;font-size:13px;color:#0B6B4F;font-weight:700">✔ {_("Recorded")} · {now_datetime().strftime("%d %b %Y %H:%M")}</p>'),
	)


# ────────────── consultant/open-issue helpers for jobs ──────────────

def _consultant_open_map():
	"""{consultant: [issue rows]} for Open/In Progress issues."""
	rows = frappe.db.sql(
		"""
		select i.name, i.title, i.customer, i.severity, i.status, i.due_date,
		       i.creation, a.user, a.creation as assigned_at
		from `tabDuty Issue` i
		join `tabDuty Issue Assignee` a on a.parent = i.name
		where i.status in ('Open', 'In Progress')
		""",
		as_dict=True,
	)
	out = {}
	for r in rows:
		if is_consultant(r.user):
			out.setdefault(r.user, []).append(r)
	return out


def _last_update_at(issue, user):
	return frappe.db.get_value(
		"Duty Issue Update",
		{"issue": issue, "owner": user},
		"max(creation)",
	)


# ──────────────────── 3: hourly stale reminders ────────────────────

def remind_stale_issues():
	now = now_datetime()
	for user, issues in _consultant_open_map().items():
		for r in issues:
			base = _last_update_at(r.name, user) or r.assigned_at or r.creation
			hrs = (now - get_datetime(base)).total_seconds() / 3600.0
			due_stage = 0
			for s in STAGES:
				if hrs >= s:
					due_stage = s
			if not due_stage:
				continue
			if _logged(user, "stale", ref=r.name, stage=due_stage):
				continue
			urgency = {6: "#B27409", 12: "#B27409", 18: "#C94646", 24: "#C94646"}[due_stage]
			inner = (
				f'<p style="font-size:13.5px">{_("This ticket has had <b>no update from you for {0}+ hours</b>. Post a progress update — silence reads as inactivity.").format(due_stage)}</p>'
				+ _kv([
					(_("Ticket"), r.name),
					(_("Title"), r.title),
					(_("Customer"), r.customer),
					(_("Severity"), r.severity),
					(_("Status"), r.status),
					(_("Due"), str(r.due_date) if r.due_date else None),
				])
			)
			_send(
				user,
				f"[Duty Board] ⏰ {due_stage}h without an update — {r.title[:70]}",
				_shell(_("Update needed"), inner).replace(BRAND, urgency, 1),
			)
			for s in STAGES:  # back-fill: lower stages never fire late
				if s <= due_stage and not _logged(user, "stale", ref=r.name, stage=s):
					_log(user, "stale", ref=r.name, stage=s)
	frappe.db.commit()


# ───────────────────── 4: the daily pending list ─────────────────────

def daily_pending():
	for user, issues in _consultant_open_map().items():
		if _logged(user, "daily", on=today()):
			continue
		issues.sort(key=lambda r: (r.due_date or "9999", r.severity != "Critical"))
		trs = ""
		for r in issues:
			overdue = r.due_date and str(r.due_date) < today()
			last = _last_update_at(r.name, user)
			age = "—"
			if last:
				age = f"{int((now_datetime() - get_datetime(last)).total_seconds() // 3600)}h"
			trs += (
				f'<tr>'
				f'<td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px;font-weight:700">{frappe.utils.escape_html(r.title[:60])}<br>'
				f'<span style="color:#8A9994;font-weight:500">{frappe.utils.escape_html(r.customer or "")} · {r.name}</span></td>'
				f'<td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px">{r.severity}</td>'
				f'<td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px;{"color:#C94646;font-weight:800" if overdue else ""}">{("⚠ " if overdue else "") + str(r.due_date) if r.due_date else "—"}</td>'
				f'<td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px">{age}</td>'
				f'</tr>'
			)
		inner = (
			f'<p style="font-size:13.5px">{_("You have <b>{0} pending ticket(s)</b>. Today decides which of them move.").format(len(issues))}</p>'
			f'<table style="border-collapse:collapse;width:100%">'
			f'<tr><th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Ticket")}</th>'
			f'<th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Severity")}</th>'
			f'<th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Due")}</th>'
			f'<th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Last update")}</th></tr>'
			f"{trs}</table>"
		)
		_send(user, f"[Duty Board] ☀️ {_('Your pending tickets today')} ({len(issues)})", _shell(_("Daily briefing"), inner))
		_log(user, "daily", on=today())
	frappe.db.commit()


# ──────────────────── 5: the Monday performance digest ────────────────────

def weekly_digest():
	wd = get_datetime(today()).weekday()
	week_start = add_days(today(), -(wd + 7))  # last Monday..Sunday
	week_end = add_days(week_start, 7)
	month_start = today()[:8] + "01"
	consultants = {u for u in _consultant_open_map().keys()}
	# include consultants with zero open issues but activity: union of session users
	for s in frappe.get_all("Work Session", filters={"start_time": [">=", week_start]}, pluck="user"):
		if is_consultant(s):
			consultants.add(s)
	for user in consultants:
		if _logged(user, "weekly", on=today()):
			continue
		mine = frappe.get_all("Duty Issue Assignee", filters={"user": user}, pluck="parent") or [""]

		def _res(since, until=None):
			f = {"name": ["in", mine], "status": ["in", ["Resolved", "Closed"]], "modified": [">=", since]}
			n = frappe.db.count("Duty Issue", f)
			if until:
				n -= frappe.db.count("Duty Issue", {**f, "modified": [">=", until]})
			return max(n, 0)

		def _hours(since, until=None):
			f = [["user", "=", user], ["start_time", ">=", since]]
			if until:
				f.append(["start_time", "<", until])
			return round(sum(cint(x.duration) for x in frappe.get_all("Work Session", filters=f, fields=["duration"])) / 3600.0, 1)

		wk_res = _res(week_start, week_end)
		wk_hours = _hours(week_start, week_end)
		wk_upd = frappe.db.count("Duty Issue Update", {"owner": user, "creation": ["between", [str(week_start), str(week_end)]]})
		mo_res = _res(month_start)
		mo_hours = _hours(month_start)
		backlog = len(_consultant_open_map().get(user, []))
		tile = lambda n, l: (
			f'<td style="padding:12px 16px;border:1px solid #E2E8E5;border-radius:10px;text-align:center">'
			f'<div style="font-size:22px;font-weight:800">{n}</div>'
			f'<div style="font-size:10.5px;color:#65736F;font-weight:700;text-transform:uppercase">{l}</div></td>'
		)
		inner = (
			f'<p style="font-size:13.5px">{_("Your week with Xlevel, in numbers:")}</p>'
			f'<table style="border-collapse:separate;border-spacing:8px"><tr>'
			f'{tile(wk_res, _("resolved"))}{tile(f"{wk_hours}h", _("logged"))}{tile(wk_upd, _("updates"))}{tile(backlog, _("open now"))}'
			f"</tr></table>"
			f'<p style="font-size:12.5px;color:#51605C;margin-top:10px"><b>{_("Month to date")}:</b> {mo_res} {_("resolved")} · {mo_hours}h {_("logged")}</p>'
			+ (f'<p style="font-size:12.5px;color:#B27409;font-weight:700">{_("{0} ticket(s) still open — your daily briefing has the list.").format(backlog)}</p>' if backlog else f'<p style="font-size:12.5px;color:#0B6B4F;font-weight:700">{_("Clean slate — nothing pending. Well done.")}</p>')
		)
		_send(user, f"[Duty Board] 📊 {_('Your week in review')}", _shell(_("Weekly digest"), inner))
		_log(user, "weekly", on=today())
	frappe.db.commit()


# ─────────────────────── one-time job setup ───────────────────────

def setup_email_jobs():
	"""bench execute duty_board.notify.setup_email_jobs
	Creates/repairs the three Scheduled Job Type records. Times are
	SERVER time; adjust cron in the Scheduled Job Type list at will."""
	jobs = [
		("duty_board.notify.remind_stale_issues", "0 * * * *"),
		("duty_board.notify.daily_pending", "30 6 * * *"),
		("duty_board.notify.weekly_digest", "45 6 * * 1"),
	]
	made = []
	for method, cron in jobs:
		name = frappe.db.get_value("Scheduled Job Type", {"method": method})
		if name:
			frappe.db.set_value("Scheduled Job Type", name, {"frequency": "Cron", "cron_format": cron, "stopped": 0})
			made.append(f"repaired {method}")
		else:
			frappe.get_doc({
				"doctype": "Scheduled Job Type",
				"method": method,
				"frequency": "Cron",
				"cron_format": cron,
				"stopped": 0,
			}).insert(ignore_permissions=True)
			made.append(f"created {method}")
	frappe.db.commit()
	return made
