#!/usr/bin/env python3
"""Duty Board v3.57.7 — consultants lose the Client Rooms face.

The Chat face now carries every room a consultant is assigned to, so
the old Client Rooms face is a redundant second door for him. Removing
the rail button alone would strand two deep-links on a face he can no
longer navigate away from, so both are rerouted for consultants:

- Dashboard "my rooms" chips  -> Chat face, room opened there
- view_origin (notification jump-to-message) -> Chat face, then jump

Staff keep the Client Rooms face untouched — the directory view and
join-request approvals live there.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.6.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '\t\tthis.rail = (this.rail || []).filter((r) => ["issues", "chat", "clients", "projects", "me", "news"].includes(r.id));'
A1_NEW = '\t\tthis.rail = (this.rail || []).filter((r) => ["issues", "chat", "projects", "me", "news"].includes(r.id));'

A2_OLD = '''\t\t\t\t\tconst room = $(e.currentTarget).data("room");
\t\t\t\t\tthis.show_face("clients");
\t\t\t\t\tsetTimeout(() => this.open_client_room(room), 400);'''

A2_NEW = '''\t\t\t\t\tconst room = $(e.currentTarget).data("room");
\t\t\t\t\tif (this._is_consultant) {
\t\t\t\t\t\tthis.show_face("chat");
\t\t\t\t\t\tsetTimeout(() => this.open_convo("room", String(room)), 400);
\t\t\t\t\t} else {
\t\t\t\t\t\tthis.show_face("clients");
\t\t\t\t\t\tsetTimeout(() => this.open_client_room(room), 400);
\t\t\t\t\t}'''

A3_OLD = '''\t\tthis.show_face("clients");
\t\tthis.open_client_room(room_name);
\t\tsetTimeout(() => this.jump_to_msg(msg_id), 1300);'''

A3_NEW = '''\t\tif (this._is_consultant) {
\t\t\tthis.show_face("chat");
\t\t\tthis.open_convo("room", String(room_name));
\t\t} else {
\t\t\tthis.show_face("clients");
\t\t\tthis.open_client_room(room_name);
\t\t}
\t\tsetTimeout(() => this.jump_to_msg(msg_id), 1300);'''

EDITS = [
    ("consultant_shell: drop clients from the allowlist", A1_OLD, A1_NEW),
    ("dashboard room chips: consultants route to Chat", A2_OLD, A2_NEW),
    ("view_origin: consultants route to Chat", A3_OLD, A3_NEW),
]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if '["issues", "chat", "projects", "me", "news"]' in src:
        print("Already applied. Nothing to do.")
        return
    if '["issues", "chat", "clients", "projects", "me", "news"]' not in src:
        sys.exit("ABORT: v3.57.6 not applied — run apply_v3576.py first.")

    problems = [f"  [{src.count(o)} matches] {label}" for label, o, _ in EDITS if src.count(o) != 1]
    if problems:
        print("ABORT — anchors did not match exactly once:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = src
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(js_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"\nwrote {JS}")

    init_path = os.path.join(os.getcwd(), INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.6"', '"3.57.7"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.7")
    else:
        print("NOTE: version was not 3.57.6 — left untouched.")


if __name__ == "__main__":
    main()
