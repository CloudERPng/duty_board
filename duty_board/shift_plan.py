# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Shift a project's whole plan forward (or back) in one move.

For a project that did not start when it was planned — paused, a late
kickoff — this slides every dated thing by the same number of days so the
plan holds its shape: the gaps between tasks, milestones and meetings are
kept exactly, only the whole thing moves. What it touches:

  - task start_date and due_date
  - milestone target_date
  - future meetings on the project (meeting_date) — past ones are history
  - the project target_date (go-live)

`shift(project, days=..., rebaseline=1)` moves by an explicit number of
days. `shift(project, start=today, ...)` figures the days out for you: it
finds the plan's current earliest start and moves so that becomes `start`.
Always dry-run first (`dry_run=1`) — it changes nothing and returns exactly
what a live run would move, so you can read the new dates before committing.

Completed tasks are left where they are by default (their `completed_on` is
a fact, not a plan) — `include_done=1` moves their planned dates too if you
want the whole chart to line up. Rebaselining after a shift resets the slip
measure to the new go-live; leave it off to keep measuring against the
original commitment.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from duty_board.permissions import require_staff


def _plan_start(project, include_done=False):
	"""The earliest planned date on the project — the day the plan currently
	begins. Looks at task starts and due dates and milestone targets."""
	dates = []
	task_filter = {"project": project}
	if not include_done:
		task_filter["column"] = ["!=", "Completed"]
	for t in frappe.get_all(
		"Duty Project Task", filters=task_filter, fields=["start_date", "due_date"], limit_page_length=0
	):
		dates += [t.start_date, t.due_date]
	for m in frappe.get_all(
		"Duty Milestone", filters={"project": project}, fields=["target_date"], limit_page_length=0
	):
		dates.append(m.target_date)
	dates = [getdate(d) for d in dates if d]
	return min(dates) if dates else None


@frappe.whitelist()
def shift(project, days=None, start=None, rebaseline=0, include_done=0, move_meetings=1, dry_run=1):
	"""Move a project's whole timeline. Returns what moved (or would move).

	Pass `days` for an explicit slide, or `start` (a date) to have the plan's
	current earliest date land on it. Positive days move later, negative
	earlier. dry_run=1 changes nothing.
	"""
	require_staff()
	if not frappe.db.exists("Duty Project", project):
		frappe.throw(_("No such project."))
	include_done = cint(include_done)
	dry = cint(dry_run)

	if days in (None, "") and start:
		cur = _plan_start(project, include_done)
		if not cur:
			frappe.throw(_("This project has no dated tasks or milestones to move."))
		days = (getdate(start) - cur).days
	if days in (None, ""):
		frappe.throw(_("Give either days= or start=."))
	days = int(days)
	if days == 0:
		return {"project": project, "days": 0, "moved": {}, "note": _("Nothing to move — the plan already starts there."), "dry_run": bool(dry)}

	moved = {"tasks": [], "milestones": [], "meetings": [], "project": None}

	task_filter = {"project": project}
	if not include_done:
		task_filter["column"] = ["!=", "Completed"]
	for t in frappe.get_all(
		"Duty Project Task", filters=task_filter,
		fields=["name", "title", "start_date", "due_date", "column"], limit_page_length=0
	):
		ns = add_days(t.start_date, days) if t.start_date else None
		nd = add_days(t.due_date, days) if t.due_date else None
		if t.start_date is None and t.due_date is None:
			continue
		moved["tasks"].append({"name": t.name, "title": t.title,
							   "start": [str(t.start_date) if t.start_date else None, str(ns) if ns else None],
							   "due": [str(t.due_date) if t.due_date else None, str(nd) if nd else None]})
		if not dry:
			vals = {}
			if t.start_date:
				vals["start_date"] = ns
			if t.due_date:
				vals["due_date"] = nd
			frappe.db.set_value("Duty Project Task", t.name, vals, update_modified=False)

	for m in frappe.get_all(
		"Duty Milestone", filters={"project": project},
		fields=["name", "title", "target_date"], limit_page_length=0
	):
		if not m.target_date:
			continue
		nt = add_days(m.target_date, days)
		moved["milestones"].append({"name": m.name, "title": m.title, "target": [str(m.target_date), str(nt)]})
		if not dry:
			frappe.db.set_value("Duty Milestone", m.name, "target_date", nt, update_modified=False)

	if cint(move_meetings):
		today = getdate(nowdate())
		for mt in frappe.get_all(
			"Duty Meeting",
			filters={"project": project, "status": ["in", ["Pending", "Confirmed"]], "meeting_date": [">=", str(today)]},
			fields=["name", "topic", "meeting_date"], limit_page_length=0
		):
			if not mt.meeting_date:
				continue
			nm = add_days(mt.meeting_date, days)
			moved["meetings"].append({"name": mt.name, "topic": mt.topic, "date": [str(mt.meeting_date), str(nm)]})
			if not dry:
				frappe.db.set_value("Duty Meeting", mt.name, "meeting_date", nm, update_modified=False)

	target = frappe.db.get_value("Duty Project", project, "target_date")
	if target:
		ntarget = add_days(target, days)
		moved["project"] = {"target_date": [str(target), str(ntarget)]}
		if not dry:
			frappe.db.set_value("Duty Project", project, "target_date", ntarget, update_modified=False)

	rebaselined = None
	if not dry and cint(rebaseline) and moved["project"]:
		from duty_board.projects import set_project_baseline

		set_project_baseline(project, baseline_target_date=moved["project"]["target_date"][1], force=1)
		rebaselined = moved["project"]["target_date"][1]

	if not dry:
		frappe.db.commit()

	counts = {k: len(v) for k, v in moved.items() if isinstance(v, list)}
	return {
		"project": project, "days": days, "dry_run": bool(dry),
		"counts": counts, "moved": moved,
		"rebaselined_to": rebaselined,
		"note": (_("Dry run — nothing changed. {0} tasks, {1} milestones, {2} meetings would move {3} days.")
				 if dry else _("Moved {0} tasks, {1} milestones, {2} meetings by {3} days."))
		.format(counts["tasks"], counts["milestones"], counts["meetings"], days),
	}
