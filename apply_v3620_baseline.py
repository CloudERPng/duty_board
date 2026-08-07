#!/usr/bin/env python3
"""Duty Board v3.62.0 — project baselines: measure slip against the plan.

The biggest PM gap for a major project: target dates silently rewrite
themselves, so "are we behind the plan we committed to?" was
unanswerable. This adds a baseline — a frozen snapshot of each phase's
target date, captured once when the plan is agreed — and computes
variance (current target vs baseline) everywhere phases are shown.

Design:
- Baseline lives at the PHASE level (Duty Milestone.baseline_date). Task
  dates churn too much to baseline usefully; phase dates are what you
  commit and what steering meetings track.
- Baselining is EXPLICIT and once: project_set_baseline(project)
  snapshots every phase's current target_date into baseline_date, and
  stamps Duty Project.baselined_on. You seed phases, adjust them to the
  agreed plan, THEN baseline — so the frozen line is the committed plan,
  not the seed-time guess. Re-baselining is allowed but warns (it's a
  deliberate re-plan, e.g. after an approved scope change).
- _milestone_decorate computes slip_days (current target - baseline) and
  a baselined flag; both milestone fetches carry baseline_date.

Schema: Duty Milestone +baseline_date (Date), Duty Project +baselined_on
(Datetime). bench migrate creates the columns (no backfill — null = not
yet baselined, which is correct).

bench migrate && bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.61.9.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
MSDT = "duty_board/duty_board/doctype/duty_milestone/duty_milestone.json"
PROJDT = "duty_board/duty_board/doctype/duty_project/duty_project.json"
CHECK_ONLY = "--check" in sys.argv

# --- 1. _milestone_decorate: compute variance -------------------------------
DEC_OLD = '''def _milestone_decorate(rows, pnames):
\t"""Shared row builder: attach tasks, progress counts, project label."""
\tfor r in rows:
\t\tr.target_date = str(r.target_date) if r.target_date else None'''
DEC_NEW = '''def _milestone_decorate(rows, pnames):
\t"""Shared row builder: attach tasks, progress counts, project label,
\tand baseline variance (slip vs the frozen plan)."""
\tfrom frappe.utils import date_diff
\tfor r in rows:
\t\tbaseline = r.get("baseline_date")
\t\tr.baseline_date = str(baseline) if baseline else None
\t\tr.baselined = 1 if baseline else 0
\t\tif baseline and r.get("target_date"):
\t\t\t# +ve = later than plan (slipped), -ve = ahead of plan
\t\t\tr.slip_days = date_diff(r.target_date, baseline)
\t\telse:
\t\t\tr.slip_days = None
\t\tr.target_date = str(r.target_date) if r.target_date else None'''

# --- 2. both fetches include baseline_date ----------------------------------
F1_OLD = '''\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\treturn _milestone_decorate(rows, _project_names(room))'''
F1_NEW = '''\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t\t"baseline_date",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\treturn _milestone_decorate(rows, _project_names(room))'''

F2_OLD = '''\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\tpname = frappe.db.get_value("Duty Project", project, "project_name") or project'''
F2_NEW = '''\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t\t"baseline_date",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\tpname = frappe.db.get_value("Duty Project", project, "project_name") or project'''

# --- 3. the set-baseline endpoint, added after project_milestone_add --------
EP_ANCHOR = '''\tfrappe.db.commit()
\treturn {"ok": 1, "project": project}


@frappe.whitelist()
def project_milestone_add(project, title, description=None, target_date=None):'''
EP_NEW = '''\tfrappe.db.commit()
\treturn {"ok": 1, "project": project}


@frappe.whitelist()
def project_set_baseline(project):
\t"""Freeze the current phase target dates as the project's baseline. Call
\tonce the plan is agreed; variance is measured against this line. Safe to
\tre-run (a deliberate re-plan) — it re-freezes to current targets."""
\t_staff_only()
\tif not frappe.db.exists("Duty Project", project):
\t\tfrappe.throw(_("Unknown project."))
\tphases = frappe.get_all(
\t\t"Duty Milestone",
\t\tfilters={"project": project},
\t\tfields=["name", "target_date"],
\t)
\tif not phases:
\t\tfrappe.throw(_("Seed or add phases before baselining."))
\tstamped = 0
\tfor p in phases:
\t\tif p.target_date:
\t\t\tfrappe.db.set_value("Duty Milestone", p.name, "baseline_date", p.target_date, update_modified=False)
\t\t\tstamped += 1
\tfrappe.db.set_value("Duty Project", project, "baselined_on", frappe.utils.now(), update_modified=False)
\tfrappe.db.commit()
\treturn {"ok": 1, "project": project, "phases_baselined": stamped}


@frappe.whitelist()
def project_baseline_status(project):
\t"""Whether a project is baselined, and when."""
\t_staff_only()
\ton = frappe.db.get_value("Duty Project", project, "baselined_on")
\treturn {"baselined": 1 if on else 0, "baselined_on": str(on)[:16] if on else None}


@frappe.whitelist()
def project_milestone_add(project, title, description=None, target_date=None):'''


def add_field(dt_path, field):
    with io.open(dt_path, encoding="utf-8") as f:
        dt = json.load(f)
    if any(fl["fieldname"] == field["fieldname"] for fl in dt["fields"]):
        return False
    dt["fields"].append(field)
    if "field_order" in dt:
        dt["field_order"].append(field["fieldname"])
    with io.open(dt_path, "w", encoding="utf-8") as f:
        json.dump(dt, f, indent=1)
        f.write("\n")
    return True


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, CR), encoding="utf-8") as f:
        cr = f.read()

    if "def project_set_baseline(" in cr:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.9"' not in init:
        sys.exit("ABORT: not at v3.61.9.")

    for label, s in [("decorate", DEC_OLD), ("fetch1", F1_OLD), ("fetch2", F2_OLD), ("endpoint anchor", EP_ANCHOR)]:
        if cr.count(s) != 1:
            sys.exit(f"ABORT: {label} anchor found {cr.count(s)} times.")

    print("All 4 anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_field(os.path.join(root, MSDT), {
        "fieldname": "baseline_date", "fieldtype": "Date", "label": "Baseline Date",
    })
    print("  doctype: Duty Milestone +baseline_date")
    add_field(os.path.join(root, PROJDT), {
        "fieldname": "baselined_on", "fieldtype": "Datetime", "label": "Baselined On",
    })
    print("  doctype: Duty Project +baselined_on")

    cr = cr.replace(DEC_OLD, DEC_NEW, 1).replace(F1_OLD, F1_NEW, 1).replace(F2_OLD, F2_NEW, 1).replace(EP_ANCHOR, EP_NEW, 1)
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(cr)
    print("  client_room.py: variance + set-baseline endpoints")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.61.9"', '"3.62.0"'))
    print("wrote __init__.py -> 3.62.0")


if __name__ == "__main__":
    main()
