# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Day plan — a person's working day, allotted each morning around what is
already booked.

Rules:
- A Duty Day Plan holds the window (work start/end, the break), the working
  days, the standup, and a table of budgets. A budget is Daily (hours a day),
  Weekly (hours a week, optionally rotating through a list — "one product a
  week"), Fixed (a daily block at a set time — reading at 19:00) or Slack
  (hours a day kept free, never placed).
- Each morning (08:00, or the Re-plan button) today's blocks are laid into
  the free time: meetings first, since they are booked and everything else is
  not; then Fixed blocks; then the Daily budgets; then this week's Weekly
  budgets, spread over the days left. Blocks are Daily Todos with a start
  time and a duration, so they tick off like any to-do and show on the board.
- Done is the only signal. A Weekly budget owes what has not been ticked;
  an undone block from an earlier day is dropped and its hours placed again.
  A block you Move is pinned: the planner leaves it alone until you unpin it.
- What does not fit is listed as unplaced rather than squeezed in — a plan
  that lies about the day is worse than one that says "no room today".
- The standup goes on everyone's calendar except external consultants, as a
  roomless Duty Meeting (roomless meetings get no reminder mails).
- The booking tools (portal and Schedule-this) read the plan too: no slot
  in the break or outside the window for a person with an active plan.
"""

import datetime as dt
import json
import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MIN_CHUNK = 30  # a block is never split finer than this
DEFAULT_MEETING_MINS = 60


# ─────────────────────────── plan access ───────────────────────────

def _plan_for(user):
	name = frappe.db.get_value("Duty Day Plan", {"user": user, "active": 1}, "name")
	return frappe.get_doc("Duty Day Plan", name) if name else None


def _mins(t):
	"""Minutes since midnight from a Time field (timedelta, time or 'HH:MM[:SS]')."""
	if t is None or t == "":
		return None
	if isinstance(t, dt.timedelta):
		return int(t.total_seconds() // 60)
	if isinstance(t, dt.time):
		return t.hour * 60 + t.minute
	s = str(t)
	h, m = s.split(":")[0], s.split(":")[1]
	return int(h) * 60 + int(m)


def _hhmm(m):
	return "%02d:%02d" % (m // 60, m % 60)


def _working_day(plan, d):
	names = [x.strip()[:3].title() for x in str(plan.working_days or "Mon,Tue,Wed,Thu,Fri").split(",") if x.strip()]
	if DAY_NAMES[d.weekday()] not in names:
		return False
	try:
		from duty_board.leave import holidays, is_on_leave

		if d in holidays() or is_on_leave(plan.user, d):
			return False
	except Exception:
		pass
	return True


def _week_of(d):
	start = d - dt.timedelta(days=d.weekday())
	return start, start + dt.timedelta(days=6)


def _rotation_item(row, d):
	items = [x.strip() for x in str(row.rotation or "").splitlines() if x.strip()]
	if not items:
		return None
	return items[(d.isocalendar()[1] - 1) % len(items)]


def _budget_title(row, d):
	item = _rotation_item(row, d)
	return f"{row.title} · {item}" if item else row.title


# ─────────────────────────── what is already on the day ───────────────────────────

def _meetings_on(user, d):
	"""Pending/Confirmed meetings the person attends or asked for, as
	(start_min, end_min, dict)."""
	parents = frappe.get_all("Duty Meeting Attendee", filters={"user": user}, pluck="parent", limit_page_length=0)
	rows = frappe.get_all(
		"Duty Meeting",
		filters={"meeting_date": d, "status": ["in", ["Pending", "Confirmed"]]},
		fields=["name", "topic", "start_time", "duration_mins", "room", "customer", "status", "requested_by"],
		limit_page_length=0,
	)
	out = []
	for m in rows:
		if m.name not in parents and m.requested_by != user:
			continue
		s = _mins(m.start_time)
		if s is None:
			continue
		e = s + (cint(m.duration_mins) or DEFAULT_MEETING_MINS)
		out.append((s, e, {"name": m.name, "topic": m.topic, "customer": m.customer, "room": m.room, "status": m.status}))
	return sorted(out)


def _todos_on(user, d):
	return frappe.get_all(
		"Daily Todo",
		filters={"user": user, "date": d},
		fields=["name", "description", "status", "due_time", "duration_mins", "plan_key", "planned", "pinned", "project", "customer"],
		order_by="due_time asc",
		limit_page_length=0,
	)


def _subtract(gaps, s, e):
	"""Remove [s, e) from a list of [start, end] gaps."""
	out = []
	for g0, g1 in gaps:
		if e <= g0 or s >= g1:
			out.append([g0, g1])
			continue
		if s > g0:
			out.append([g0, s])
		if e < g1:
			out.append([e, g1])
	return [g for g in out if g[1] - g[0] >= MIN_CHUNK]


def _place(gaps, minutes):
	"""First gap that fits the whole block; else chunks of at least MIN_CHUNK
	across gaps. Returns (chunks, remaining_minutes) and consumes the gaps."""
	minutes = int(minutes)
	for i, (g0, g1) in enumerate(gaps):
		if g1 - g0 >= minutes:
			chunk = (g0, minutes)
			gaps[i] = [g0 + minutes, g1]
			if gaps[i][1] - gaps[i][0] < MIN_CHUNK:
				gaps.pop(i)
			return [chunk], 0
	chunks = []
	left = minutes
	i = 0
	while i < len(gaps) and left >= MIN_CHUNK:
		g0, g1 = gaps[i]
		take = min(left, g1 - g0)
		take -= take % MIN_CHUNK
		if take < MIN_CHUNK:
			i += 1
			continue
		chunks.append((g0, take))
		left -= take
		gaps[i] = [g0 + take, g1]
		if gaps[i][1] - gaps[i][0] < MIN_CHUNK:
			gaps.pop(i)
		else:
			i += 1
	return chunks, left


# ─────────────────────────── week bookkeeping ───────────────────────────

def _week_done(user, d):
	"""Minutes ticked off per plan_key in the week containing d."""
	ws, we = _week_of(d)
	done = {}
	for t in frappe.get_all(
		"Daily Todo",
		filters={"user": user, "status": "Done", "planned": 1, "date": ["between", [str(ws), str(we)]]},
		fields=["plan_key", "duration_mins"],
		limit_page_length=0,
	):
		done[t.plan_key] = done.get(t.plan_key, 0) + (cint(t.duration_mins) or 0)
	return done


def _drop_stale_blocks(user, d):
	"""Undone planned blocks from earlier days this week: their hours are owed
	again, so the records go — a to-do dated Monday that nobody will ever tick
	is noise, not a plan."""
	ws, _we = _week_of(d)
	stale = frappe.get_all(
		"Daily Todo",
		filters={"user": user, "planned": 1, "status": "Open", "date": ["between", [str(ws), str(add_days(d, -1))]]},
		pluck="name",
		limit_page_length=0,
	)
	for n in stale:
		frappe.delete_doc("Daily Todo", n, ignore_permissions=True, force=True)
	return len(stale)


def _days_left(plan, d):
	"""Working days from d to the end of its week, d included."""
	_ws, we = _week_of(d)
	n = 0
	x = d
	while x <= we:
		if _working_day(plan, x):
			n += 1
		x += dt.timedelta(days=1)
	return max(n, 1)


# ─────────────────────────── which project ───────────────────────────

def _pick_project(user, d):
	"""The project the two hours go to today: the active one with the nearest
	open dated task — the deadline decides, not the alphabet. A project whose
	RAG is owned by the client is waiting on them (Montaigne, paused) and is
	skipped. Ties go to the project that has had fewer of these blocks this
	week, so two live projects share the week rather than one taking it all."""
	ws, we = _week_of(d)
	given = {}
	for t in frappe.get_all(
		"Daily Todo",
		filters={"user": user, "planned": 1, "plan_key": "project", "date": ["between", [str(ws), str(we)]]},
		fields=["project"],
		limit_page_length=0,
	):
		if t.project:
			given[t.project] = given.get(t.project, 0) + 1
	cands = []
	for p in frappe.get_all(
		"Duty Project",
		filters={"status": "Active", "rag": ["!=", "Completed"]},
		fields=["name", "project_name", "customer", "target_date", "rag", "rag_owner"],
		limit_page_length=0,
	):
		if p.rag_owner and frappe.db.get_value("User", p.rag_owner, "user_type") == "Website User":
			continue  # waiting on the client
		nearest = frappe.db.get_value(
			"Duty Project Task",
			{"project": p.name, "column": ["in", ["To Do", "In Progress"]], "due_date": ["is", "set"]},
			"min(due_date)",
		)
		cands.append((str(nearest or p.target_date or "9999-12-31"), given.get(p.name, 0), p))
	if not cands:
		return None
	cands.sort(key=lambda c: (c[0], c[1], c[2].project_name or ""))
	# a deadline within a week of the front-runner's is the same urgency: share the week
	front = cands[0]
	near = [c for c in cands if c[0] != "9999-12-31" and abs((getdate(c[0]) - getdate(front[0])).days) <= 7]
	pick = min(near, key=lambda c: (c[1], c[0]))[2] if near else front[2]
	label = f"{pick.customer} — {pick.project_name}" if pick.customer and pick.project_name and pick.customer not in pick.project_name else (pick.project_name or pick.name)
	return {"name": pick.name, "customer": pick.customer, "label": label}


# ─────────────────────────── the allotment ───────────────────────────

def plan_day(user=None, date=None, force=0):
	"""Lay today's blocks into the free time. Keeps Done and pinned blocks,
	replaces the rest. Returns what was placed and what did not fit."""
	user = user or frappe.session.user
	d = getdate(date or nowdate())
	plan = _plan_for(user)
	if not plan:
		return {"planned": 0, "reason": "no plan"}
	if not _working_day(plan, d) and not cint(force):
		return {"planned": 0, "reason": "not a working day"}

	_drop_stale_blocks(user, d)
	# today's replaceable blocks go; Done and pinned stay
	for t in _todos_on(user, d):
		if cint(t.planned) and t.status == "Open" and not cint(t.pinned):
			frappe.delete_doc("Daily Todo", t.name, ignore_permissions=True, force=True)

	work_s, work_e = _mins(plan.work_start), _mins(plan.work_end)
	br_s, br_e = _mins(plan.break_start), _mins(plan.break_end)
	gaps = [[work_s, work_e]]
	if br_s is not None and br_e is not None and br_e > br_s:
		gaps = _subtract(gaps, br_s, br_e)
	for s, e, _m in _meetings_on(user, d):
		gaps = _subtract(gaps, s, e)
	kept = _todos_on(user, d)  # Done + pinned + hand-made todos with a time
	for t in kept:
		s = _mins(t.due_time)
		if s is not None:
			gaps = _subtract(gaps, s, s + (cint(t.duration_mins) or MIN_CHUNK))
	kept_mins = {}
	for t in kept:
		if t.plan_key:
			kept_mins[t.plan_key] = kept_mins.get(t.plan_key, 0) + (cint(t.duration_mins) or 0)

	slack = sum(flt(r.hours) for r in plan.budgets if r.kind == "Slack") * 60
	placed, unplaced = [], []

	project_pick = None

	def make(row, start, mins, title, project=None):
		# a to-do tied to a project cannot be private (the team sees where the
		# hours go); everything else on the plan is the owner's alone
		doc = frappe.get_doc({
			"doctype": "Daily Todo",
			"user": user,
			"full_name": frappe.utils.get_fullname(user),
			"date": d,
			"description": title[:140],
			"status": "Open",
			"private": 0 if project else 1,
			"due_time": _hhmm(start) + ":00",
			"duration_mins": int(mins),
			"plan_key": row.key,
			"planned": 1,
			"pinned": 0,
			"project": project["name"] if project else None,
			"customer": project["customer"] if project else None,
		}).insert(ignore_permissions=True)
		placed.append({"name": doc.name, "title": title, "start": _hhmm(start), "mins": int(mins), "key": row.key,
					   "project": project["name"] if project else None})

	# Fixed blocks: at their time, or not at all today (a meeting booked over
	# reading means no reading, not reading at some other hour). Outside the
	# window — reading at 22:00 — the only thing that stops them is a clash
	# with something booked.
	busy = [(bs, be) for bs, be, _m in _meetings_on(user, d)]
	for t in kept:
		ts = _mins(t.due_time)
		if ts is not None:
			busy.append((ts, ts + (cint(t.duration_mins) or MIN_CHUNK)))
	for row in plan.budgets:
		if row.kind != "Fixed" or _mins(row.start_time) is None or kept_mins.get(row.key):
			continue
		s = _mins(row.start_time)
		mins = int(flt(row.hours) * 60)
		inside = work_s <= s and s + mins <= work_e
		if inside:
			ok = any(g0 <= s and s + mins <= g1 for g0, g1 in gaps)
			if ok:
				gaps = _subtract(gaps, s, s + mins)
		else:
			ok = not any(bs < s + mins and be > s for bs, be in busy)
		if ok:
			make(row, s, mins, row.title, project=None)
		else:
			unplaced.append({"title": row.title, "mins": mins, "key": row.key})

	# capacity after slack: the planner leaves that much of the day untouched
	free = sum(g1 - g0 for g0, g1 in gaps)
	budget_room = max(0, free - slack)

	def lay(row, want_full, title, project=None):
		"""Place up to the room left; report the shortfall as unplaced."""
		nonlocal budget_room
		want = min(want_full, budget_room)
		got = 0
		if want >= MIN_CHUNK:
			chunks, _left = _place(gaps, want)
			for s, m in chunks:
				make(row, s, m, title, project=project)
				got += m
			budget_room -= got
		short = want_full - got
		if short >= MIN_CHUNK:
			unplaced.append({"title": title, "mins": short, "key": row.key})
		return got

	# Daily budgets — the project budget names the project it is for
	for row in plan.budgets:
		if row.kind != "Daily":
			continue
		want_full = int(flt(row.hours) * 60) - kept_mins.get(row.key, 0)
		if want_full < MIN_CHUNK:
			continue
		if row.key == "project":
			project_pick = _pick_project(user, d)
			title = f"{row.title} · {project_pick['label']}" if project_pick else row.title
			lay(row, want_full, title, project=project_pick)
		else:
			lay(row, want_full, row.title)

	# Weekly budgets: what the week still owes, spread over the days left
	done = _week_done(user, d)
	days_left = _days_left(plan, d)
	for row in plan.budgets:
		if row.kind != "Weekly":
			continue
		owed = int(flt(row.hours) * 60) - done.get(row.key, 0) - kept_mins.get(row.key, 0)
		if owed < MIN_CHUNK:
			continue
		share = min(owed, max(60, int(math.ceil(owed / days_left / MIN_CHUNK)) * MIN_CHUNK))
		lay(row, share, _budget_title(row, d))

	frappe.db.commit()
	return {"planned": len(placed), "placed": placed, "unplaced": unplaced, "date": str(d)}


# ─────────────────────────── the standup ───────────────────────────

def _standup_attendees(plan):
	from duty_board.permissions import is_consultant

	out = []
	for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name", limit_page_length=0):
		if u in ("Administrator", "Guest"):
			continue
		try:
			if is_consultant(u):
				continue
		except Exception:
			pass
		out.append(u)
	return out


def ensure_standup(plan, d):
	"""One roomless Duty Meeting a working day, everyone but consultants on
	it. Idempotent on (topic, date)."""
	if not cint(plan.standup) or not _working_day(plan, d):
		return None
	topic = (plan.standup_topic or "Daily standup").strip()
	existing = frappe.db.get_value("Duty Meeting", {"topic": topic, "meeting_date": d, "status": ["!=", "Cancelled"]}, "name")
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Duty Meeting",
		"topic": topic,
		"meeting_date": d,
		"start_time": _hhmm(_mins(plan.standup_start) or 510) + ":00",
		"duration_mins": cint(plan.standup_mins) or 30,
		"status": "Confirmed",
		"requested_by": plan.user,
		"confirmed_by": plan.user,
		"reminded_morning": 1,
		"reminded_hour": 1,
		"attendees": [{"user": u} for u in _standup_attendees(plan)],
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return doc.name


# ─────────────────────────── the day, as the face and the brief see it ───────────────────────────

def _day_payload(plan, d):
	user = plan.user
	items = []
	if cint(plan.standup) and _working_day(plan, d):
		s = _mins(plan.standup_start) or 510
		items.append({"kind": "standup", "start": _hhmm(s), "end": _hhmm(s + (cint(plan.standup_mins) or 30)),
					  "title": plan.standup_topic or "Daily standup"})
	for s, e, m in _meetings_on(user, d):
		if (m.get("topic") or "") == (plan.standup_topic or "Daily standup") and not m.get("room"):
			continue
		items.append({"kind": "meeting", "start": _hhmm(s), "end": _hhmm(e), "title": m["topic"] or _("Meeting"),
					  "customer": m.get("customer"), "room": m.get("room"), "name": m["name"], "status": m.get("status")})
	br_s, br_e = _mins(plan.break_start), _mins(plan.break_end)
	if br_s is not None and br_e:
		items.append({"kind": "break", "start": _hhmm(br_s), "end": _hhmm(br_e), "title": _("Break — nothing goes here")})
	pnames = {}
	for t in _todos_on(user, d):
		s = _mins(t.due_time)
		ptitle = None
		if t.project:
			if t.project not in pnames:
				pnames[t.project] = frappe.db.get_value("Duty Project", t.project, "project_name") or t.project
			ptitle = pnames[t.project]
		items.append({"kind": "block" if cint(t.planned) else "todo", "name": t.name, "title": t.description,
					  "start": _hhmm(s) if s is not None else None,
					  "end": _hhmm(s + (cint(t.duration_mins) or MIN_CHUNK)) if s is not None else None,
					  "mins": cint(t.duration_mins), "done": t.status == "Done", "pinned": cint(t.pinned), "key": t.plan_key,
					  "project": t.project, "project_title": ptitle, "customer": t.customer})
	items.sort(key=lambda i: (i.get("start") or "99:99", i["kind"]))

	done = _week_done(user, d)
	ws, we = _week_of(d)
	planned = {}
	for t in frappe.get_all(
		"Daily Todo",
		filters={"user": user, "planned": 1, "date": ["between", [str(ws), str(we)]]},
		fields=["plan_key", "duration_mins", "status"],
		limit_page_length=0,
	):
		planned[t.plan_key] = planned.get(t.plan_key, 0) + (cint(t.duration_mins) or 0)
	week = []
	for row in plan.budgets:
		if row.kind == "Slack":
			continue
		per_week = flt(row.hours) * (5 if row.kind in ("Daily", "Fixed") else 1)
		week.append({"key": row.key, "title": _budget_title(row, d), "kind": row.kind, "budget_h": per_week,
					 "done_h": done.get(row.key, 0) / 60.0, "planned_h": planned.get(row.key, 0) / 60.0,
					 "rotation": _rotation_item(row, d)})
	return {
		"date": str(d), "working": _working_day(plan, d), "items": items, "week": week,
		"week_start": str(ws), "window": {"start": _hhmm(_mins(plan.work_start)), "end": _hhmm(_mins(plan.work_end))},
		"budgets": [{"key": r.key, "title": r.title, "kind": r.kind, "hours": flt(r.hours)} for r in plan.budgets if r.kind != "Slack"],
	}


@frappe.whitelist()
def my_plan():
	from duty_board.permissions import is_consultant

	plan = _plan_for(frappe.session.user)
	return {"exists": bool(plan), "name": plan.name if plan else None,
			"can_setup": "System Manager" in frappe.get_roles() and not is_consultant(frappe.session.user)}


@frappe.whitelist()
def day_view(date=None):
	plan = _plan_for(frappe.session.user)
	if not plan:
		return {"exists": False}
	out = _day_payload(plan, getdate(date or nowdate()))
	out["exists"] = True
	return out


@frappe.whitelist()
def replan(date=None):
	"""The button. Same as the morning run for that day."""
	plan = _plan_for(frappe.session.user)
	if not plan:
		frappe.throw(_("No day plan for you yet."))
	d = getdate(date or nowdate())
	ensure_standup(plan, d)
	r = plan_day(frappe.session.user, d, force=1)
	r["view"] = _day_payload(plan, d)
	return r


@frappe.whitelist()
def move_block(name, start, duration_mins=None, pin=1):
	"""Manual allotment: put a block where you want it. Moving pins it."""
	t = frappe.get_doc("Daily Todo", name)
	if t.user != frappe.session.user:
		frappe.throw(_("Not your block."))
	t.due_time = str(start)[:5] + ":00"
	if duration_mins is not None:
		t.duration_mins = max(MIN_CHUNK, cint(duration_mins))
	t.pinned = cint(pin)
	t.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def pin_block(name, pinned=1):
	t = frappe.get_doc("Daily Todo", name)
	if t.user != frappe.session.user:
		frappe.throw(_("Not your block."))
	t.db_set("pinned", cint(pinned))
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def add_block(date, start, duration_mins, key=None, title=None):
	"""Manual allotment, from nothing: a pinned block for a budget (its title
	and rotation) or a free-text one."""
	plan = _plan_for(frappe.session.user)
	if not plan:
		frappe.throw(_("No day plan for you yet."))
	d = getdate(date)
	row = next((r for r in plan.budgets if r.key == key), None)
	title = (title or "").strip() or (_budget_title(row, d) if row else "")
	if not title:
		frappe.throw(_("Give the block a title or pick a budget."))
	doc = frappe.get_doc({
		"doctype": "Daily Todo", "user": frappe.session.user, "full_name": frappe.utils.get_fullname(frappe.session.user),
		"date": d, "description": title[:140], "status": "Open", "private": 1,
		"due_time": str(start)[:5] + ":00", "duration_mins": max(MIN_CHUNK, cint(duration_mins)),
		"plan_key": row.key if row else None, "planned": 1, "pinned": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def remove_block(name):
	t = frappe.get_doc("Daily Todo", name)
	if t.user != frappe.session.user or not cint(t.planned):
		frappe.throw(_("Only your own planned blocks can be removed here."))
	frappe.delete_doc("Daily Todo", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": 1}


DEFAULT_BUDGETS = [
	{"title": "Project work", "key": "project", "kind": "Daily", "hours": 2, "colour": "#0F5C55"},
	{"title": "CRM agent issues", "key": "crm", "kind": "Daily", "hours": 1, "colour": "#5B3E86"},
	{"title": "Slack", "key": "slack", "kind": "Slack", "hours": 1.5},
	{"title": "Reading", "key": "reading", "kind": "Fixed", "hours": 1, "start_time": "22:00:00", "colour": "#8A5A0B"},
	{"title": "Business review", "key": "business", "kind": "Weekly", "hours": 3, "rotation": "Zhift Platforms\nXlevelBackOffice\nXlevelRetail", "colour": "#1F5FA8"},
	{"title": "Product review", "key": "product", "kind": "Weekly", "hours": 3, "rotation": "ZhiftPOS\nZhiftHMS\nZhiftHR\nNew Modules\nZhiftCRM", "colour": "#B5541C"},
	{"title": "New business ideas", "key": "ideas", "kind": "Weekly", "hours": 3, "colour": "#087A67"},
]


@frappe.whitelist()
def setup_default_plan():
	"""The plan as agreed: 09:00–20:00, break 15:00–17:00, Mon–Fri, standup
	08:30, the budgets above. Edit it afterwards at /app/duty-day-plan."""
	from duty_board.permissions import require_sysadmin

	require_sysadmin()
	user = frappe.session.user
	if frappe.db.exists("Duty Day Plan", {"user": user}):
		return {"ok": 1, "existing": 1}
	doc = frappe.get_doc({
		"doctype": "Duty Day Plan", "user": user, "active": 1, "working_days": "Mon,Tue,Wed,Thu,Fri",
		"work_start": "09:00:00", "work_end": "20:00:00", "break_start": "15:00:00", "break_end": "17:00:00",
		"standup": 1, "standup_topic": "Daily standup", "standup_start": "08:30:00", "standup_mins": 30,
		"notify_email": 1, "notify_push": 1, "budgets": DEFAULT_BUDGETS,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


# ─────────────────────────── the morning ───────────────────────────

def _brief_html(plan, view, result):
	E = frappe.utils.escape_html
	lines = []
	for i in view["items"]:
		when = f"{i['start']}–{i['end']}" if i.get("start") else _("anytime")
		who = ""
		if i["kind"] == "meeting" and i.get("customer"):
			who = f" · {E(i['customer'])}"
		elif i.get("project_title") and i["kind"] == "todo":
			who = f" · {E(i['customer'] or '')} {E(i['project_title'])}".rstrip()
		tag = {"meeting": "🤝", "standup": "👥", "break": "☕", "block": "▪", "todo": "•"}.get(i["kind"], "•")
		done = " ✓" if i.get("done") else ""
		lines.append(f'<tr><td style="padding:3px 8px;white-space:nowrap;color:#6B7772">{when}</td>'
					 f'<td style="padding:3px 8px">{tag} {E(i["title"])}{who}{done}</td></tr>')
	wk = "".join(
		f'<tr><td style="padding:2px 8px">{E(w["title"])}</td>'
		f'<td style="padding:2px 8px;white-space:nowrap">{w["done_h"]:g} / {w["budget_h"]:g} h</td></tr>'
		for w in view["week"] if w["kind"] == "Weekly"
	)
	un = "".join(f"<li>{E(u['title'])} — {u['mins']} min</li>" for u in result.get("unplaced", []))
	return (
		f'<table style="border-collapse:collapse">{"".join(lines)}</table>'
		+ (f'<p style="margin:12px 0 4px;font-weight:700">{_("No room today for")}</p><ul>{un}</ul>' if un else "")
		+ f'<p style="margin:12px 0 4px;font-weight:700">{_("This week")}</p><table style="border-collapse:collapse">{wk}</table>'
	)


def morning_plan():
	"""cron: 0 8 * * * — for every active plan on a working day: the standup
	on the calendar, the day allotted, and the day sent (email + push)."""
	from duty_board.api import _notify_user
	from duty_board.notify import _send, _shell

	d = getdate(nowdate())
	out = []
	for name in frappe.get_all("Duty Day Plan", filters={"active": 1}, pluck="name"):
		plan = frappe.get_doc("Duty Day Plan", name)
		if not _working_day(plan, d):
			continue
		try:
			ensure_standup(plan, d)
			result = plan_day(plan.user, d)
			view = _day_payload(plan, d)
			first_block = next((i for i in view["items"] if i["kind"] in ("block", "meeting")), None)
			body = "; ".join(f"{i['start']} {i['title']}" for i in view["items"] if i["kind"] in ("meeting", "block"))[:160]
			if cint(plan.notify_email):
				_send(plan.user, _("[Day] {0}").format(frappe.utils.formatdate(d, "EEE d MMM")), _shell(_("Your day"), _brief_html(plan, view, result)))
			if cint(plan.notify_push):
				_notify_user(plan.user, _("📅 Your day: {0} blocks").format(result.get("planned", 0)), body or _("Nothing planned"))
			out.append({"user": plan.user, "planned": result.get("planned", 0), "unplaced": len(result.get("unplaced", []))})
		except Exception:
			frappe.log_error(frappe.get_traceback()[-1500:], "day plan morning")
	return out


def plan_blocked_hours(user, d):
	"""Hours (as 'HH' strings) a person with an active plan cannot take a
	meeting: the break, and anything outside the window. For the booking
	tools."""
	plan = _plan_for(user)
	if not plan:
		return set()
	d = getdate(d)
	if not _working_day(plan, d):
		return {"%02d" % h for h in range(24)}
	work_s, work_e = _mins(plan.work_start), _mins(plan.work_end)
	br_s, br_e = _mins(plan.break_start), _mins(plan.break_end)
	blocked = set()
	for h in range(24):
		s, e = h * 60, h * 60 + 60
		if s < work_s or e > work_e:
			blocked.add("%02d" % h)
		elif br_s is not None and br_e and s < br_e and e > br_s:
			blocked.add("%02d" % h)
	return blocked
