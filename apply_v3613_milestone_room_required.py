#!/usr/bin/env python3
"""Duty Board v3.61.3 — milestones require a room (the correct invariant).

Stage 1's seed/add passed room=None for room-less projects, but Duty
Milestone.room is mandatory — so seeding a room-less project crashed with
MandatoryError. Decision: keep room mandatory (the whole system assumes
every milestone lives in a room) and require the PROJECT to have a room
before it can hold phases. A room-less project is a broken state anyway —
it's invisible to clients — so this guard names the real precondition
instead of crashing.

Both project_seed_milestones and project_milestone_add now throw a clear
"assign this project to a room first" if the project has no room, and use
that room (never None) for the milestone.

JS-free, no schema. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.61.2.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
CHECK_ONLY = "--check" in sys.argv

# seed: require room
SEED_OLD = '''\tif frappe.db.count("Duty Milestone", {"project": project}):
\t\tfrappe.throw(_("This project already has phases."))
\troom_name = frappe.db.get_value("Duty Project", project, "room")'''
SEED_NEW = '''\tif frappe.db.count("Duty Milestone", {"project": project}):
\t\tfrappe.throw(_("This project already has phases."))
\troom_name = frappe.db.get_value("Duty Project", project, "room")
\tif not room_name:
\t\tfrappe.throw(_("Assign this project to a room before seeding phases."))'''

SEED_USE_OLD = '''\t\t\t\t"doctype": "Duty Milestone",
\t\t\t\t"room": room_name or None,
\t\t\t\t"project": project,
\t\t\t\t"title": title,'''
SEED_USE_NEW = '''\t\t\t\t"doctype": "Duty Milestone",
\t\t\t\t"room": room_name,
\t\t\t\t"project": project,
\t\t\t\t"title": title,'''

# add: require room
ADD_OLD = '''\tif not title:
\t\tfrappe.throw(_("Give the phase a title."))
\troom_name = frappe.db.get_value("Duty Project", project, "room")'''
ADD_NEW = '''\tif not title:
\t\tfrappe.throw(_("Give the phase a title."))
\troom_name = frappe.db.get_value("Duty Project", project, "room")
\tif not room_name:
\t\tfrappe.throw(_("Assign this project to a room before adding phases."))'''

ADD_USE_OLD = '''\t\t\t"doctype": "Duty Milestone",
\t\t\t"room": room_name or None,
\t\t\t"project": project,
\t\t\t"title": title[:120],'''
ADD_USE_NEW = '''\t\t\t"doctype": "Duty Milestone",
\t\t\t"room": room_name,
\t\t\t"project": project,
\t\t\t"title": title[:120],'''

EDITS = [
    ("seed: require room", SEED_OLD, SEED_NEW),
    ("seed: use room", SEED_USE_OLD, SEED_USE_NEW),
    ("add: require room", ADD_OLD, ADD_NEW),
    ("add: use room", ADD_USE_OLD, ADD_USE_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, CR), encoding="utf-8") as f:
        cr = f.read()

    if "Assign this project to a room before seeding phases" in cr:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.2"' not in init:
        sys.exit("ABORT: not at v3.61.2.")

    problems = [f"  [{cr.count(o)}] {label}" for label, o, _ in EDITS if cr.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for label, old, new in EDITS:
        cr = cr.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(cr)

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.61.2"', '"3.61.3"'))
    print("wrote __init__.py -> 3.61.3")


if __name__ == "__main__":
    main()
