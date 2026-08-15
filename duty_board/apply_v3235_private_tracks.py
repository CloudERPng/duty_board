#!/usr/bin/env python3
"""Duty Board v3.235.0 — PRIVATE TRACKS.

Corporate Policy Certification needs a client's own SOPs turned into courses
that only that client can see. Today every track with active=1 and
audience=Client appears in every client's catalogue, so Slot's inventory
transfer procedure would be listed to Pricewise.

Adds `private_to_room` (Link Client Room) to Duty Certification Track. Empty
means the track is general and behaves exactly as now; set, it means the track
exists only for that room.

The reason this patch is larger than it sounds: SEVEN places list tracks, not
one. Filtering the obvious catalogue and stopping would have leaked the track
through the assignment picker, the staff list and the public /academy page. They
need two different rules:

  Room-scoped — show general tracks plus this room's own:
    academy.track_catalogue           the client catalogue
    client_room.room_tracks_for_assign  the admin's assignment picker
    client_room._track_for_module       module-to-track resolution
    client_room._tracks_for_room        the learner's track list

  Not room-scoped — show general tracks only:
    client_room.staff_tracks            staff-facing list
    client_room._evaluate_certifications certificate awarding
    www/academy.py                      the PUBLIC catalogue

The public page matters most: a leak there is visible to anyone on the internet,
not merely to another client.

Deploy: apply -> bench migrate (schema) -> clear-cache + clear-website-cache ->
restart. Anchored, idempotent, --check for a dry run. Requires v3.234.0.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
TRACK_JSON = "duty_board/duty_board/doctype/duty_certification_track/duty_certification_track.json"
CLIENT_ROOM = "duty_board/client_room.py"
ACADEMY = "duty_board/academy.py"
PUBLIC = "duty_board/www/academy.py"
CHECK_ONLY = "--check" in sys.argv

FIELD = {
    "fieldname": "private_to_room",
    "fieldtype": "Link",
    "label": "Private to Client Room",
    "options": "Client Room",
    "description": (
        "Leave empty for a general track. Set it and the track exists only for that "
        "room — it will not appear in any other client's catalogue, in the public "
        "catalogue, or in staff lists."
    ),
}

# (file, old, new, label) — each anchor must appear exactly once
EDITS = [
    # --- room-scoped: general tracks plus this room's own -------------------
    (ACADEMY,
     '''	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},''',
     '''	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client",
				 "private_to_room": ["in", [None, "", room]]},''',
     "track_catalogue — client catalogue"),

    (CLIENT_ROOM,
     '''	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},
		fields=["name", "title", "product"],''',
     '''	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client",
				 "private_to_room": ["in", [None, "", room.name]]},
		fields=["name", "title", "product"],''',
     "room_tracks_for_assign — assignment picker"),

    (CLIENT_ROOM,
     '''	tracks = frappe.get_all(
		"Duty Certification Track",
		filters={"name": ["in", names], "active": 1, "audience": "Client"},''',
     '''	tracks = frappe.get_all(
		"Duty Certification Track",
		filters={"name": ["in", names], "active": 1, "audience": "Client",
				 "private_to_room": ["in", [None, "", room.name]]},''',
     "_track_for_module — module-to-track resolution"),

    (CLIENT_ROOM,
     '''	tracks = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},
		fields=["name", "title", "product", "description", "access"],''',
     '''	tracks = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client",
				 "private_to_room": ["in", [None, "", room.name]]},
		fields=["name", "title", "product", "description", "access"],''',
     "_tracks_for_room — learner track list"),

    # --- not room-scoped: general tracks only ------------------------------
    (CLIENT_ROOM,
     '''	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1},''',
     '''	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "private_to_room": ["in", [None, ""]]},''',
     "staff_tracks — staff list"),

    (CLIENT_ROOM,
     '''	for track in frappe.get_all(
		"Duty Certification Track", filters={"active": 1}, fields=["name"]
	):''',
     '''	for track in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "private_to_room": ["in", [None, ""]]},
		fields=["name"],
	):''',
     "_evaluate_certifications — certificate awarding"),

    (PUBLIC,
     '''	rows = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},''',
     '''	rows = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client",
				 "private_to_room": ["in", [None, ""]]},''',
     "www/academy.py — PUBLIC catalogue"),
]


def main():
    root = os.getcwd()
    read = lambda p: io.open(os.path.join(root, p), encoding="utf-8").read()

    init = read(INIT)
    if '"3.234.0"' not in init:
        sys.exit("ABORT: not at v3.234.0.")

    track = json.loads(read(TRACK_JSON))
    have_field = any(f.get("fieldname") == "private_to_room"
                     for f in track.get("fields", []))
    files = {p: read(p) for p in {ACADEMY, CLIENT_ROOM, PUBLIC}}

    if have_field and all(e[1] not in files[e[0]] for e in EDITS):
        print("Already applied. Nothing to do.")
        return

    problems = []
    for path, old, _new, label in EDITS:
        n = files[path].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(EDITS))
    print("Field present already: %s" % have_field)

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # schema: place the field beside `active`, so it reads as a visibility control
    if not have_field:
        fields = track["fields"]
        idx = next((i for i, f in enumerate(fields)
                    if f.get("fieldname") == "active"), len(fields) - 1)
        fields.insert(idx + 1, FIELD)
        with io.open(os.path.join(root, TRACK_JSON), "w", encoding="utf-8") as f:
            json.dump(track, f, indent=1, sort_keys=True)
            f.write("\n")
        print("  doctype: private_to_room added after `active`")

    for path in files:
        s = files[path]
        for p, old, new, _label in EDITS:
            if p == path:
                s = s.replace(old, new, 1)
        with io.open(os.path.join(root, path), "w", encoding="utf-8") as f:
            f.write(s)
        print("  %s: filtered" % path)

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.234.0"', '"3.235.0"'))
    print("wrote __init__.py -> 3.235.0")
    print("\nSchema change: run bench migrate.")


if __name__ == "__main__":
    main()
