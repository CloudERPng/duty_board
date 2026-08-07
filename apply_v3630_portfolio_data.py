#!/usr/bin/env python3
"""Duty Board v3.63.0 (part 1/1 file — backend) — portfolio data.

Enriches get_projects with the PM signals a portfolio view needs: each
project's current phase (first non-approved milestone), phase progress
(approved/total), and worst baseline slip (max days a phase has moved
past its frozen baseline). Combined with the task stats already computed
(done/total/overdue/pct/days_left), this is everything a one-glance
portfolio grid needs — no second round-trip.

Adds per project: phase_current, phases_done, phases_total, worst_slip,
at_risk (overdue tasks or positive slip).

projects.py only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.62.6.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

OLD = '''\t\tp.days_left = (getdate(p.target_date) - tday).days if p.target_date else None
\treturn projects'''
NEW = '''\t\tp.days_left = (getdate(p.target_date) - tday).days if p.target_date else None

\t# --- phase + baseline slip per project (portfolio signals) ---
\tfrom frappe.utils import date_diff
\tms_rows = frappe.get_all(
\t\t"Duty Milestone",
\t\tfilters={"project": ["in", [p.name for p in projects]]},
\t\tfields=["project", "title", "status", "target_date", "baseline_date", "sort_order"],
\t\torder_by="sort_order asc",
\t)
\tph = {p.name: {"total": 0, "done": 0, "current": None, "worst_slip": None} for p in projects}
\tfor m in ms_rows:
\t\tg = ph[m.project]
\t\tg["total"] += 1
\t\tif m.status == "Approved":
\t\t\tg["done"] += 1
\t\telif g["current"] is None:
\t\t\tg["current"] = m.title  # first non-approved by sort_order = where we are
\t\tif m.baseline_date and m.target_date:
\t\t\tslip = date_diff(m.target_date, m.baseline_date)
\t\t\tif g["worst_slip"] is None or slip > g["worst_slip"]:
\t\t\t\tg["worst_slip"] = slip
\tfor p in projects:
\t\tg = ph[p.name]
\t\tp.phases_total = g["total"]
\t\tp.phases_done = g["done"]
\t\tp.phase_current = g["current"] or ("Complete" if g["total"] and g["done"] == g["total"] else None)
\t\tp.worst_slip = g["worst_slip"]
\t\tp.at_risk = 1 if (p.get("overdue", 0) or (g["worst_slip"] or 0) > 0) else 0
\treturn projects'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PROJ), encoding="utf-8") as f:
        proj = f.read()

    if "p.worst_slip = g[" in proj:
        print("Already applied. Nothing to do.")
        return
    if '"3.62.6"' not in init:
        sys.exit("ABORT: not at v3.62.6.")
    if proj.count(OLD) != 1:
        sys.exit(f"ABORT: anchor found {proj.count(OLD)} times.")

    print("Anchor matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    proj = proj.replace(OLD, NEW, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(proj)
    print("  projects.py: get_projects enriched with phase + slip")
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.62.6"', '"3.63.0"'))
    print("wrote __init__.py -> 3.63.0")


if __name__ == "__main__":
    main()
