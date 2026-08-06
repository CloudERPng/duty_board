#!/usr/bin/env python3
"""Duty Board v3.57.5 — consultants can open their rooms again.

THE BUG (client_room.get_room): the `_incl` assignment that decides
whether a consultant sees internal whispers was pasted into the WRONG
branch — the staff-not-permitted branch, on the line AFTER its
frappe.throw, where it can never execute. Meanwhile the consultant
branch, whose flag it reads (allow_consultant_internal), never set
`_incl` at all. Result: every authorized consultant opening a room they
are a member of crashed with UnboundLocalError at _room_payload.

THE FIX: move the assignment into the consultant branch where it
belongs. Staff and System Managers keep _incl=True via the else, the
unauthorized paths still throw first. Whisper visibility for
consultants now actually follows the room's allow_consultant_internal
flag — which was the intent the day that line was written.

This patches PYTHON, so after applying: bench restart (no build needed).

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
The anchor exists identically in 3.56.0 and 3.57.x — client_room.py was
not touched by the v3.57 UI chain — so this same script fixes any other
instance still on 3.56.0 (deploy via git pull instead where possible).
"""

import io
import os
import sys

PY = "duty_board/client_room.py"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '''\tif _is_c:
\t\tif name not in consultant_room_names():
\t\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)
\telif "System Manager" not in frappe.get_roles() and not _staff_sees_room(room, frappe.session.user):
\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)
\t\t_incl = bool(cint(room.get("allow_consultant_internal")))
\telse:
\t\t_incl = True'''

A1_NEW = '''\tif _is_c:
\t\tif name not in consultant_room_names():
\t\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)
\t\t# Consultants see internal whispers only when the room allows it.
\t\t_incl = bool(cint(room.get("allow_consultant_internal")))
\telif "System Manager" not in frappe.get_roles() and not _staff_sees_room(room, frappe.session.user):
\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)
\telse:
\t\t_incl = True'''

EDITS = [("get_room: _incl into the consultant branch", A1_OLD, A1_NEW)]


def main():
    py_path = os.path.join(os.getcwd(), PY)
    if not os.path.exists(py_path):
        sys.exit(f"ABORT: {PY} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(py_path, encoding="utf-8") as f:
        src = f.read()

    if "Consultants see internal whispers only when the room allows it." in src:
        print("Already applied. Nothing to do.")
        return

    problems = [f"  [{src.count(o)} matches] {label}" for label, o, _ in EDITS if src.count(o) != 1]
    if problems:
        print("ABORT — anchors did not match exactly once:")
        print("\n".join(problems))
        sys.exit(1)

    print("Anchor matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = src
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(py_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {PY}")

    init_path = os.path.join(os.getcwd(), INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.4"', '"3.57.5"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.5")
    else:
        print("NOTE: version was not 3.57.4 — left untouched (this server is behind; "
              "prefer `git pull` over patching it directly).")


if __name__ == "__main__":
    main()
