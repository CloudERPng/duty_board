#!/usr/bin/env python3
"""Duty Board v3.61.2 — project-first milestones, Stage 1 (backend only).

Milestones belong to PROJECTS, managed independently of rooms — so a
room-less project (Desma, TrustCare) can have phases too. This stage
adds the project-scoped backend without touching UI; everything is
API-testable. The room-based staff UI keeps working via the existing
endpoints until Stage 2 moves phase management onto the Projects face.

Changes (client_room.py):
1. _milestone_build_rows(milestone_names, project_name_map): the shared
   row builder, extracted from _milestone_rows so a project-scoped fetch
   can reuse it.
2. _milestone_rows(room): unchanged behaviour (room-scoped), now built
   on the shared helper.
3. _project_milestone_rows(project): the project-scoped fetch.
4. project_seed_milestones(project, plan_type): seed the Xlevel method
   onto a PROJECT; guard per-project (kills the "room already has
   milestones" wall); derive room from the project (nullable).
5. project_milestone_add(project, ...): add one phase to a project,
   sort-order per project.

Changes (projects.py):
6. get_project_board(project) also returns "milestones" so the Projects
   face can show phases (Stage 2 renders them).

No schema change, no migrate. bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.61.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1+2. refactor _milestone_rows onto a shared builder --------------------
MR_OLD = '''def _milestone_rows(room):
\trows = frappe.get_all(
\t\t"Duty Milestone",
\t\tfilters={"room": room.name},
\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\tfor r in rows:'''
MR_NEW = '''def _milestone_rows(room):
\t"""Room-scoped milestone rows (legacy path: every phase in the room)."""
\trows = frappe.get_all(
\t\t"Duty Milestone",
\t\tfilters={"room": room.name},
\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\treturn _milestone_decorate(rows, _project_names(room))


def _project_milestone_rows(project):
\t"""Project-scoped milestone rows — the project-first path. Works whether
\tor not the project is attached to a room."""
\trows = frappe.get_all(
\t\t"Duty Milestone",
\t\tfilters={"project": project},
\t\tfields=[
\t\t\t"name", "title", "description", "sort_order", "status", "target_date",
\t\t\t"approved_full", "approved_at", "approval_note", "submitted_on", "project",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)
\tpname = frappe.db.get_value("Duty Project", project, "project_name") or project
\treturn _milestone_decorate(rows, {project: pname})


def _milestone_decorate(rows, pnames):
\t"""Shared row builder: attach tasks, progress counts, project label."""
\tfor r in rows:'''

# the tail of the old function — replace the room-based pnames + return
MR_TAIL_OLD = '''\tpnames = _project_names(room)
\tfor r in rows:
\t\tr.project_name = pnames.get(r.project)
\treturn rows'''
MR_TAIL_NEW = '''\tfor r in rows:
\t\tr.project_name = pnames.get(r.project)
\treturn rows'''

# --- 4. project_seed_milestones (project-first seed) ------------------------
# insert before the existing milestones_seed
SEED_OLD = '''def milestones_seed(name, plan_type=None):
\t_staff_only()'''
SEED_NEW = '''@frappe.whitelist()
def project_seed_milestones(project, plan_type=None):
\t"""Seed the Xlevel method onto a PROJECT (room-independent). Guards per
\tproject, so each project in a room gets its own phase journey."""
\t_staff_only()
\tif not frappe.db.exists("Duty Project", project):
\t\tfrappe.throw(_("Unknown project."))
\tif frappe.db.count("Duty Milestone", {"project": project}):
\t\tfrappe.throw(_("This project already has phases."))
\troom_name = frappe.db.get_value("Duty Project", project, "room")

\tplan = None
\tif plan_type:
\t\tfrom duty_board.plan_templates import PLAN_TYPES

\t\tif plan_type not in PLAN_TYPES:
\t\t\tfrappe.throw(_("Unknown plan type."))
\t\tplan = PLAN_TYPES[plan_type][1]

\tfrom frappe.utils import add_days

\tfor i, (title, desc) in enumerate(XLEVEL_METHOD):
\t\tphase_tasks = (plan or {}).get(title, [])
\t\tms = frappe.get_doc(
\t\t\t{
\t\t\t\t"doctype": "Duty Milestone",
\t\t\t\t"room": room_name or None,
\t\t\t\t"project": project,
\t\t\t\t"title": title,
\t\t\t\t"description": desc,
\t\t\t\t"sort_order": i,
\t\t\t\t"status": "Upcoming",
\t\t\t\t"target_date": add_days(today(), max(t[3] for t in phase_tasks))
\t\t\t\tif phase_tasks
\t\t\t\telse None,
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tfor t_title, t_desc, t_urg, t_off in phase_tasks:
\t\t\tfrappe.get_doc(
\t\t\t\t{
\t\t\t\t\t"doctype": "Duty Project Task",
\t\t\t\t\t"project": project,
\t\t\t\t\t"title": t_title,
\t\t\t\t\t"column": "To Do",
\t\t\t\t\t"urgency": t_urg if t_urg in ("Low", "Medium", "High", "Critical") else "Medium",
\t\t\t\t\t"description": t_desc or None,
\t\t\t\t\t"due_date": add_days(today(), t_off) if t_off else None,
\t\t\t\t\t"milestone": ms.name,
\t\t\t\t}
\t\t\t).insert(ignore_permissions=True)
\tfrappe.db.commit()
\treturn {"ok": 1, "project": project}


@frappe.whitelist()
def project_milestone_add(project, title, description=None, target_date=None):
\t"""Add one phase to a project; sort-order sequenced per project."""
\t_staff_only()
\tif not frappe.db.exists("Duty Project", project):
\t\tfrappe.throw(_("Unknown project."))
\ttitle = (title or "").strip()
\tif not title:
\t\tfrappe.throw(_("Give the phase a title."))
\troom_name = frappe.db.get_value("Duty Project", project, "room")
\tlast = frappe.db.sql(
\t\t"select coalesce(max(sort_order), -1) from `tabDuty Milestone` where project = %s",
\t\tproject,
\t)[0][0]
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Duty Milestone",
\t\t\t"room": room_name or None,
\t\t\t"project": project,
\t\t\t"title": title[:120],
\t\t\t"description": (description or "").strip()[:500] or None,
\t\t\t"target_date": target_date or None,
\t\t\t"sort_order": last + 1,
\t\t\t"status": "Upcoming",
\t\t}
\t).insert(ignore_permissions=True)
\tfrappe.db.commit()
\treturn {"ok": 1, "project": project}


def milestones_seed(name, plan_type=None):
\t_staff_only()'''

# --- 6. get_project_board returns milestones --------------------------------
GPB_OLD = '''\treturn {
\t\t"columns": COLUMNS,
\t\t"tasks": tasks,
\t\t"consultants": [
\t\t\tr.user
\t\t\tfor r in frappe.get_all(
\t\t\t\t"Duty Project Consultant", filters={"parent": project}, fields=["user"]
\t\t\t)
\t\t],
\t}'''
GPB_NEW = '''\tfrom duty_board.client_room import _project_milestone_rows

\treturn {
\t\t"columns": COLUMNS,
\t\t"tasks": tasks,
\t\t"milestones": _project_milestone_rows(project),
\t\t"consultants": [
\t\t\tr.user
\t\t\tfor r in frappe.get_all(
\t\t\t\t"Duty Project Consultant", filters={"parent": project}, fields=["user"]
\t\t\t)
\t\t],
\t}'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _project_milestone_rows(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.61.1.")

    checks = [
        (CR, MR_OLD), (CR, MR_TAIL_OLD), (CR, SEED_OLD),
        (PROJ, GPB_OLD),
    ]
    problems = [f"  [{files[f].count(s)}] {s[:44]!r}" for f, s in checks if files[f].count(s) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All 4 anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    cr = files[CR].replace(MR_OLD, MR_NEW, 1).replace(MR_TAIL_OLD, MR_TAIL_NEW, 1).replace(SEED_OLD, SEED_NEW, 1)
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(cr)
    print("  client_room.py: shared builder + project fetch + project seed/add")

    pr = files[PROJ].replace(GPB_OLD, GPB_NEW, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pr)
    print("  projects.py: get_project_board returns milestones")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.61.1"', '"3.61.2"'))
    print("wrote __init__.py -> 3.61.2")


if __name__ == "__main__":
    main()
