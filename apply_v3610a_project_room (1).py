#!/usr/bin/env python3
"""Duty Board v3.61.0a — projects become room-scoped: schema + backfill only.

This is the SAFE half. It adds the Duty Project.room link and backfills
every existing project to its customer's main room, but LEAVES the
queries filtering by customer — so nothing user-facing changes yet. You
deploy this, confirm every project got a room and both rooms behave
exactly as today, and only then does v3.61.0b flip the queries to filter
by room.

Splitting it this way means that if the query cutover misbehaves, the
schema underneath is already proven — you know which half to blame.

1. Duty Project gains a `room` Link field (to Client Room).
2. Backfill patch assigns each existing project to its customer's main
   room (Financial Room if flagged, else oldest active room).
3. staff create_project accepts an optional room and stamps it.

Deploy: bench migrate && bench build --app duty_board && bench restart
Anchored, idempotent. Requires v3.60.3.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
PROJDT = "duty_board/duty_board/doctype/duty_project/duty_project.json"
PROJPY = "duty_board/projects.py"
PATCHES = "duty_board/patches.txt"
CHECK_ONLY = "--check" in sys.argv

# create_project: accept + stamp room (optional; safe no-op if not passed)
CP_OLD = '''def create_project(project_name, customer=None, target_date=None):'''
CP_NEW = '''def create_project(project_name, customer=None, target_date=None, room=None):'''

CP_DOC_OLD = '''\t\t\t"customer": customer,'''
CP_DOC_NEW = '''\t\t\t"customer": customer,
\t\t\t"room": room or None,'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PROJPY), encoding="utf-8") as f:
        proj = f.read()

    if "def create_project(project_name, customer=None, target_date=None, room=None)" in proj:
        print("Already applied. Nothing to do.")
        return
    if '"3.60.3"' not in init:
        sys.exit("ABORT: not at v3.60.3.")

    problems = []
    if proj.count(CP_OLD) != 1:
        problems.append(f"  [{proj.count(CP_OLD)}] create_project signature")
    if proj.count(CP_DOC_OLD) < 1:
        problems.append(f"  [{proj.count(CP_DOC_OLD)}] create_project customer field")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("Anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # doctype: +room
    with io.open(os.path.join(root, PROJDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "room" for fl in dt["fields"]):
        # insert room right after customer for a sensible form order
        idx = next((i for i, fl in enumerate(dt["fields"]) if fl["fieldname"] == "customer"), len(dt["fields"]) - 1)
        dt["fields"].insert(idx + 1, {
            "fieldname": "room", "fieldtype": "Link", "label": "Room",
            "options": "Client Room",
        })
        if "field_order" in dt and "room" not in dt["field_order"]:
            if "customer" in dt["field_order"]:
                dt["field_order"].insert(dt["field_order"].index("customer") + 1, "room")
            else:
                dt["field_order"].append("room")
        with io.open(os.path.join(root, PROJDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
        print("  doctype: Duty Project +room")

    # projects.py
    proj = proj.replace(CP_OLD, CP_NEW, 1).replace(CP_DOC_OLD, CP_DOC_NEW, 1)
    with io.open(os.path.join(root, PROJPY), "w", encoding="utf-8") as f:
        f.write(proj)
    print("  projects.py: create_project +room")

    # register backfill
    with io.open(os.path.join(root, PATCHES), encoding="utf-8") as f:
        pt = f.read()
    line = "duty_board.patches.backfill_project_room"
    if line not in pt:
        pt = pt.rstrip() + "\n" + line + "\n"
        with io.open(os.path.join(root, PATCHES), "w", encoding="utf-8") as f:
            f.write(pt)
        print("  patches.txt: backfill_project_room registered")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.60.3"', '"3.61.0"'))
    print("wrote __init__.py -> 3.61.0")


if __name__ == "__main__":
    main()
