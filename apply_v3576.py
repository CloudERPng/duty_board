#!/usr/bin/env python3
"""Duty Board v3.57.6 — the Chat face opens to consultants, rooms only.

WHAT A CONSULTANT GETS: the same WhatsApp-shaped face staff have —
flat latest-first rail, thread centre, task column — containing ONLY
the client rooms he is named into (consultant_room_names, enforced
server-side as before).

WHAT HE MUST NOT GET, stripped in the DATA not just the CSS:
- The Duty Room team chat: never in his rail, never auto-opened.
  get_messages would refuse him anyway; now the entry doesn't exist.
- DMs: dm.py is require_staff throughout. No DM rows, no \u270f button,
  and open_convo hard-refuses non-room kinds for consultants.

MECHANICS:
- chat.py get_rail keeps the is-consultant flag it already computes and
  skips _team_entry / _dm_entries for consultants.
- refresh_chat auto-open becomes "first conversation in the rail" —
  for staff that is still Duty Room (pinned first), so staff behaviour
  is unchanged; for consultants it is their most recent room.
- consultant_shell's face allowlist gains "chat".
- body.duty-consultant hides the \u270f new-DM button.

Two files touched; restart + build required.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.5.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PY = "duty_board/chat.py"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# ---------------------------- chat.py ----------------------------------------

P1_OLD = '\trequire_staff_or_consultant()\n\tme = frappe.session.user'
P1_NEW = '\tis_consultant = require_staff_or_consultant()\n\tme = frappe.session.user'

P2_OLD = '\tentries = [_team_entry(me)]'
P2_NEW = '''\t# Consultants never see the internal team room or DMs — stripped from
\t# the data, not hidden by the client. dm.py and get_messages are
\t# require_staff besides; this keeps the rail honest about it.
\tentries = [] if is_consultant else [_team_entry(me)]'''

P3_OLD = '\tentries.extend(_dm_entries(me))'
P3_NEW = '\tif not is_consultant:\n\t\tentries.extend(_dm_entries(me))'

# ---------------------------- duty_board.js ----------------------------------

J1_OLD = '\t\tthis.rail = (this.rail || []).filter((r) => ["issues", "clients", "projects", "me", "news"].includes(r.id));'
J1_NEW = '\t\tthis.rail = (this.rail || []).filter((r) => ["issues", "chat", "clients", "projects", "me", "news"].includes(r.id));'

J2_OLD = '\t\t\t\tif (!this._ch_open) this.open_convo("team", "__team__");'
J2_NEW = '''\t\t\t\tif (!this._ch_open) {
\t\t\t\t\t// First rail entry: Duty Room for staff (pinned), the most
\t\t\t\t\t// recent room for consultants (who have no team entry).
\t\t\t\t\tconst first = (this._convos || [])[0];
\t\t\t\t\tif (first) this.open_convo(first.kind, String(first.id));
\t\t\t\t}'''

J3_OLD = '\t\tif (!kind || !id) return;\n\t\tthis._ch_open = { kind: kind, id: id };'
J3_NEW = '\t\tif (!kind || !id) return;\n\t\tif (this._is_consultant && kind !== "room") return;\n\t\tthis._ch_open = { kind: kind, id: id };'

J4_OLD = '\t\t\tbody.duty-consultant .duty-chat-rail { display: none !important; }'
J4_NEW = J4_OLD + '\n\t\t\tbody.duty-consultant .duty-ch-new { display: none !important; }'

PY_EDITS = [
    ("get_rail: keep the consultant flag", P1_OLD, P1_NEW),
    ("get_rail: no team entry for consultants", P2_OLD, P2_NEW),
    ("get_rail: no DM entries for consultants", P3_OLD, P3_NEW),
]
JS_EDITS = [
    ("consultant_shell: chat joins the allowlist", J1_OLD, J1_NEW),
    ("refresh_chat: auto-open first rail entry", J2_OLD, J2_NEW),
    ("open_convo: consultants are rooms-only", J3_OLD, J3_NEW),
    ("styles: hide \\u270f from consultants", J4_OLD, J4_NEW),
]


def main():
    root = os.getcwd()
    paths = {PY: None, JS: None}
    for p in paths:
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            paths[p] = f.read()

    # Marker must be text only THIS patch introduces — the bare string
    # "is_consultant = require_staff_or_consultant()" already exists in
    # _visible_rooms and falsely tripped the guard.
    if "entries = [] if is_consultant else [_team_entry(me)]" in paths[PY]:
        print("Already applied. Nothing to do.")
        return
    if "duty-fluid" not in paths[JS]:
        sys.exit("ABORT: v3.57.4 chain missing — apply earlier patches first.")

    problems = []
    for label, old, _ in PY_EDITS:
        if paths[PY].count(old) != 1:
            problems.append(f"  [{paths[PY].count(old)} matches] chat.py: {label}")
    for label, old, _ in JS_EDITS:
        if paths[JS].count(old) != 1:
            problems.append(f"  [{paths[JS].count(old)} matches] duty_board.js: {label}")
    if problems:
        print("ABORT — anchors did not match exactly once:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(PY_EDITS) + len(JS_EDITS)} anchors matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out_py = paths[PY]
    for label, old, new in PY_EDITS:
        out_py = out_py.replace(old, new, 1)
        print(f"  applied chat.py: {label}")
    with io.open(os.path.join(root, PY), "w", encoding="utf-8") as f:
        f.write(out_py)

    out_js = paths[JS]
    for label, old, new in JS_EDITS:
        out_js = out_js.replace(old, new, 1)
        print(f"  applied duty_board.js: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(out_js)

    print(f"\nwrote {PY} and {JS}")

    init_path = os.path.join(root, INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.5"', '"3.57.6"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.6")
    else:
        print("NOTE: version was not 3.57.5 — left untouched.")


if __name__ == "__main__":
    main()
