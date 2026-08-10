#!/usr/bin/env python3
"""Duty Board v3.76.0 — project visibility by assignment (team request 3).

Staff assigned to a project (Duty Project Consultant rows — the same
table the 👤 Consultants button manages and phase bonuses split over)
see it; unassigned staff don't, by default. Rules:

- System Managers see everything (oversight unchanged).
- Other staff: get_projects returns only projects where they are a
  consultant OR the project's owner (creator) — so the list, the 📊
  portfolio, and every dependent surface filter automatically.
- get_project_board: same guard server-side, so a direct load of an
  unassigned project's board is refused, not just hidden.
- create_project: the creator is auto-added to the consultants table —
  you always see what you just made, and new projects are never
  invisible orphans.
- Consultant (client-side) filtering untouched — it already existed and
  this mirrors its pattern for staff.

NOTE for rollout: projects with an EMPTY consultants table are visible
only to System Managers and their creator until people are assigned —
assign your teams via 👤 Consultants right after deploying.

No schema. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.75.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. get_projects: staff assignment filter -------------------------------
G_OLD = '''\tprojects = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"status": "Active"},
\t\tfields=["name", "project_name", "customer", "target_date"],
\t\torder_by="creation asc",
\t)
\tif _is_c:
\t\tprojects = [p for p in projects if p.name in _memb]'''
G_NEW = '''\tprojects = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"status": "Active"},
\t\tfields=["name", "project_name", "customer", "target_date", "owner"],
\t\torder_by="creation asc",
\t)
\tif _is_c:
\t\tprojects = [p for p in projects if p.name in _memb]
\telif "System Manager" not in frappe.get_roles():
\t\t_mine = set(
\t\t\tfrappe.get_all(
\t\t\t\t"Duty Project Consultant",
\t\t\t\tfilters={"user": frappe.session.user},
\t\t\t\tpluck="parent",
\t\t\t)
\t\t)
\t\tprojects = [p for p in projects if p.name in _mine or p.owner == frappe.session.user]'''

# --- 2. get_project_board: staff guard --------------------------------------
B_OLD = '''def get_project_board(project):
\tfrom duty_board.permissions import require_staff_or_consultant, consultant_project_names
\tif require_staff_or_consultant() and project not in consultant_project_names():
\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)'''
B_NEW = '''def get_project_board(project):
\tfrom duty_board.permissions import require_staff_or_consultant, consultant_project_names
\tif require_staff_or_consultant() and project not in consultant_project_names():
\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)
\tif not require_staff_or_consultant() and "System Manager" not in frappe.get_roles():
\t\t_ok = frappe.get_all(
\t\t\t"Duty Project Consultant",
\t\t\tfilters={"parent": project, "user": frappe.session.user},
\t\t\tlimit=1,
\t\t) or frappe.db.get_value("Duty Project", project, "owner") == frappe.session.user
\t\tif not _ok:
\t\t\tfrappe.throw(_("You're not assigned to this project."), frappe.PermissionError)'''

# --- 3. create_project: creator auto-assigned -------------------------------
C_OLD = '''def create_project(project_name, customer=None, target_date=None, room=None):'''
C_ANCHOR2 = '"doctype": "Duty Project",'


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PROJ), encoding="utf-8") as f:
        proj = f.read()

    if "You're not assigned to this project." in proj:
        print("Already applied. Nothing to do.")
        return
    if '"3.75.0"' not in init:
        sys.exit("ABORT: not at v3.75.0.")

    problems = []
    if proj.count(G_OLD) != 1:
        problems.append(f"  [{proj.count(G_OLD)}] projects filter")
    if proj.count(B_OLD) != 1:
        problems.append(f"  [{proj.count(B_OLD)}] board guard")
    # creator auto-assign: find the insert inside create_project and append
    # consultant row after; anchored on the doc dict + following insert.
    import re
    m = re.search(
        r'(def create_project\(project_name, customer=None, target_date=None, room=None\):.*?\n\t\)\.insert\(ignore_permissions=True\)\n)',
        proj, re.S,
    )
    m2 = re.search(
        r'(def create_project\(project_name, customer=None, target_date=None, room=None\):.*?insert\(ignore_permissions=True\))',
        proj, re.S,
    )
    if not m2:
        problems.append("  create_project insert not found")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    proj = proj.replace(G_OLD, G_NEW, 1).replace(B_OLD, B_NEW, 1)

    # creator auto-assign: the create_project body assigns the doc; find the
    # first "doc = frappe.get_doc(" ... ").insert(" within create_project and
    # add a consultant append before insert by transforming the segment.
    seg = m2.group(1)
    if "append(" in seg and "consultants" in seg:
        pass  # already appends consultants somehow
    else:
        # transform: `frappe.get_doc(\n\t\t{...}` returns doc then .insert —
        # handle both `frappe.get_doc({...}).insert(...)` and
        # `doc = frappe.get_doc({...})\n\tdoc.insert(...)` shapes by splitting
        # at the final `.insert(ignore_permissions=True)`.
        new_seg = seg.replace(
            '"doctype": "Duty Project",',
            '"doctype": "Duty Project",\n\t\t\t"consultants": [{"user": frappe.session.user}],',
            1,
        )
        if new_seg == seg:
            sys.exit("ABORT: could not add creator consultant row.")
        proj = proj.replace(seg, new_seg, 1)

    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(proj)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.75.0"', '"3.76.0"'))
    print("  projects.py: staff filter, board guard, creator auto-assigned")
    print("wrote __init__.py -> 3.76.0")


if __name__ == "__main__":
    main()
