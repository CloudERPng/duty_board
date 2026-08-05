# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Gamification for the staff portal — tiers 1 and 2.

Design law: reward quality, consistency and teamwork; NEVER raw volume
alone. Streaks are personal (no comparison). Badges are permanent
milestones over signals the board already captures. Kudos are
peer-to-peer. The team pulse is one collective goal — cooperation,
not ranking.
"""

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	flt,
	get_datetime,
	get_fullname,
	getdate,
	now_datetime,
	today,
)

from duty_board.permissions import require_staff


def _my_resolved_names(me):
	mine = frappe.get_all("Duty Issue Assignee", filters={"user": me}, pluck="parent")
	if not mine:
		return []
	return frappe.get_all(
		"Duty Issue",
		filters={"name": ["in", mine], "status": ["in", ["Resolved", "Closed"]]},
		pluck="name",
	)


@frappe.whitelist()
def my_gamify():
	"""Streak, badges and the week card — the caller's alone."""
	require_staff()
	me = frappe.session.user
	horizon = 60

	# ---- raw day signals over the horizon ----
	since = add_days(today(), -horizon)
	clock_days = {
		str(r.log_time)[:10]
		for r in frappe.get_all(
			"Duty Log",
			filters={"user": me, "log_type": "Clock In", "log_time": [">=", since]},
			fields=["log_time"],
		)
	}
	plan_days = {
		str(r.date)[:10]
		for r in frappe.get_all(
			"Daily Todo", filters={"user": me, "date": [">=", since]}, fields=["date"]
		)
	}
	update_days = {
		str(r.creation)[:10]
		for r in frappe.get_all(
			"Duty Issue Update",
			filters={"owner": me, "creation": [">=", since]},
			fields=["creation"],
		)
	}

	def day_active(ds):
		return ds in clock_days and ds in plan_days and ds in update_days

	# ---- streak walk: today backwards, weekends never break it ----
	today_s = today()
	cur = 0
	for i in range(horizon):
		ds = str(add_days(today_s, -i))
		if getdate(ds).weekday() >= 5:
			continue
		if day_active(ds):
			cur += 1
		elif i == 0:
			continue  # today isn't over — an idle today doesn't break it
		else:
			break
	best = 0
	# best over the horizon (independent walk)
	run = 0
	for i in range(horizon, -1, -1):
		ds = str(add_days(today_s, -i))
		if getdate(ds).weekday() >= 5:
			continue
		if day_active(ds):
			run += 1
			best = max(best, run)
		else:
			run = 0
	best = max(best, cur)

	# ---- badges ----
	resolved_names = _my_resolved_names(me)
	n_res = len(resolved_names)
	d30 = add_days(today(), -30)
	mine_all = frappe.get_all("Duty Issue Assignee", filters={"user": me}, pluck="parent")

	# last five rated resolutions, all five stars
	five_run = False
	if mine_all:
		rated = frappe.get_all(
			"Duty Issue",
			filters={"name": ["in", mine_all], "client_rating": [">", 0]},
			fields=["client_rating"],
			order_by="modified desc",
			limit=5,
		)
		five_run = len(rated) == 5 and all(cint(r.client_rating) == 5 for r in rated)

	# clean month: no SLA breach on my issues in 30d
	clean = True
	if mine_all:
		clean = (
			frappe.db.count(
				"Duty Issue",
				filters=[
					["name", "in", mine_all],
					["modified", ">", d30],
					["sla_res_met", "=", 0],
					["sla_res_due", "<", now_datetime()],
				],
			)
			== 0
		)

	# checklist discipline: resolved issues that carried a fully-done checklist
	gated = 0
	if resolved_names:
		rows = frappe.get_all(
			"Duty Issue Checklist Item",
			filters={"parent": ["in", resolved_names]},
			fields=["parent", "done"],
		)
		by = {}
		for r in rows:
			t, k = by.get(r.parent, (0, 0))
			by[r.parent] = (t + 1, k + cint(r.done))
		gated = sum(1 for t, k in by.values() if t and t == k)

	cr_spotted = frappe.db.count(
		"Duty Change Request",
		{
			"owner": me,
			"pricing_status": ["in", ["Priced", "Covered by Subscription", "Goodwill"]],
		},
	)
	finished_books = 0
	for pr in frappe.get_all(
		"Duty Book Progress",
		filters={"user": me},
		fields=["book", "chapters_done"],
	):
		total = frappe.db.count("Duty Book Chapter", {"book": pr.book})
		done_n = len([c for c in (pr.chapters_done or "").split(",") if c])
		if total and done_n >= total:
			finished_books += 1
	n_highlights = frappe.db.count("Duty Book Highlight", {"user": me})
	certs = frappe.get_all(
		"Duty Certificate",
		filters={"user": me, "status": ["!=", "Revoked"]},
		fields=["track_title"],
	)

	badges = [
		{"id": "first_res", "icon": "🥇", "label": _("First Resolution"), "earned": n_res >= 1, "desc": _("Resolve your first ticket.")},
		{"id": "res_50", "icon": "🛠", "label": _("50 Club"), "earned": n_res >= 50, "desc": _("Fifty tickets resolved.")},
		{"id": "res_100", "icon": "⚙️", "label": _("Century"), "earned": n_res >= 100, "desc": _("One hundred tickets resolved.")},
		{"id": "res_500", "icon": "🏆", "label": _("The 500"), "earned": n_res >= 500, "desc": _("Five hundred tickets resolved.")},
		{"id": "five_run", "icon": "⭐", "label": _("Five Stars, Five Times"), "earned": five_run, "desc": _("Your last five rated tickets — all five stars.")},
		{"id": "clean_month", "icon": "🛡", "label": _("Clean Month"), "earned": bool(mine_all) and clean, "desc": _("Thirty days without an SLA breach.")},
		{"id": "checklist_20", "icon": "✅", "label": _("Checklist Discipline"), "earned": gated >= 20, "desc": _("Twenty resolutions through a completed checklist.")},
		{"id": "cr_spotter", "icon": "💱", "label": _("CR Spotter"), "earned": cr_spotted >= 1, "desc": _("Draft a change request that gets priced.")},
		{"id": "bookworm", "icon": "📖", "label": _("Bookworm"), "earned": finished_books >= 1, "desc": _("Finish a book in the Library.")},
		{"id": "marginalia", "icon": "🖍", "label": _("Marginalia"), "earned": n_highlights >= 10, "desc": _("Leave ten highlights across the shelves.")},
		{"id": "streak_7", "icon": "🔥", "label": _("One-Week Flame"), "earned": best >= 5, "desc": _("A full working week of clock-in, plan and updates.")},
		{"id": "streak_30", "icon": "🌋", "label": _("The Month"), "earned": best >= 22, "desc": _("A full working month on streak.")},
	]
	for c in certs[:6]:
		badges.append({"id": "cert", "icon": "🎓", "label": c.track_title or _("Certified"), "earned": True, "desc": _("Academy certification.")})

	# ---- week card (Monday to now) ----
	wd = getdate(today()).weekday()
	week_start = add_days(today(), -wd)
	week_res = 0
	if mine_all:
		week_res = frappe.db.count(
			"Duty Issue",
			{"name": ["in", mine_all], "status": ["in", ["Resolved", "Closed"]], "modified": [">=", week_start]},
		)
	secs = 0
	for s in frappe.get_all(
		"Work Session",
		filters={"user": me, "start_time": [">=", week_start]},
		fields=["duration"],
	):
		secs += cint(s.duration)
	ratings = []
	if mine_all:
		ratings = frappe.get_all(
			"Duty Issue",
			filters={"name": ["in", mine_all], "client_rating": [">", 0], "modified": [">=", week_start]},
			pluck="client_rating",
		)
	kudos_wk = frappe.db.count("Duty Kudos", {"to_user": me, "creation": [">=", week_start]})

	memory = frappe.db.sql(
		"""
		select h.text, h.note, bk.title as book_title
		from `tabDuty Book Highlight` h
		join `tabDuty Book` bk on bk.name = h.book
		where h.user = %s and h.creation < %s
		order by rand() limit 1
		""",
		(me, add_days(today(), -14)),
		as_dict=True,
	)
	return {
		"memory": memory[0] if memory else None,
		"streak": {
			"current": cur,
			"best": best,
			"today": {
				"clock": today_s in clock_days,
				"plan": today_s in plan_days,
				"update": today_s in update_days,
			},
		},
		"badges": badges,
		"week": {
			"resolved": week_res,
			"hours": round(secs / 3600.0, 1),
			"avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
			"kudos": kudos_wk,
		},
	}


@frappe.whitelist()
def kudos_give(row):
	"""👏 one issue update. Peer-to-peer: no self-kudos, once per update."""
	require_staff()
	me = frappe.session.user
	upd = frappe.db.get_value(
		"Duty Issue Update", row, ["name", "owner", "issue"], as_dict=True
	)
	if not upd:
		frappe.throw(_("Update not found."))
	if upd.owner == me:
		frappe.throw(_("Applauding yourself is a workout, not kudos."))
	if frappe.db.exists("Duty Kudos", {"from_user": me, "ref_name": row}):
		frappe.throw(_("Already applauded."))
	frappe.get_doc({
		"doctype": "Duty Kudos",
		"from_user": me,
		"to_user": upd.owner,
		"ref_type": "Duty Issue Update",
		"ref_name": row,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		from duty_board.api import _notify_user

		_notify_user(upd.owner, _("👏 Kudos from {0}").format(get_fullname(me).split(" ")[0]), _("On your update in {0}").format(upd.issue))
	except Exception:
		pass
	return {"ok": 1}


@frappe.whitelist()
def team_pulse():
	"""The one collective goal: this week's resolutions vs target, breach
	watch, and this month's most-appreciated — cooperation, not ranking."""
	require_staff()
	wd = getdate(today()).weekday()
	week_start = add_days(today(), -wd)
	resolved = frappe.db.count(
		"Duty Issue",
		{"status": ["in", ["Resolved", "Closed"]], "modified": [">=", week_start]},
	)
	target = cint(frappe.db.get_single_value("Duty Settings", "pulse_target")) or 40
	breaches = frappe.db.count(
		"Duty Issue",
		{
			"sla_res_met": 0,
			"sla_res_due": ["between", [str(week_start), str(now_datetime())]],
		},
	)
	month_start = today()[:8] + "01"
	rows = frappe.db.sql(
		"""
		select to_user, count(*) n from `tabDuty Kudos`
		where creation >= %s group by to_user order by n desc limit 3
		""",
		(month_start,),
		as_dict=True,
	)
	return {
		"resolved": resolved,
		"target": target,
		"breaches": breaches,
		"applauded": [
			{"user": r.to_user, "name": get_fullname(r.to_user).split(" ")[0], "n": r.n}
			for r in rows
		],
	}
