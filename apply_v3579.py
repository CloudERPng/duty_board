#!/usr/bin/env python3
"""Duty Board v3.57.9 HOTFIX — the day tabs appear on first load.

v3.57.8's tab bar was created display:none and only shown inside
show_face() — which runs on CLICK, never on initial page load, where
the board face is simply visible by default. So the tabs existed but
never appeared until you visited another face and came back.

Fix: invoke show_face("board") once at load for staff, driving the
same toggle path a click would. Consultants excluded — their landing
behaviour is managed by consultant_shell and stays untouched.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.8.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '''\tif (!board._is_consultant && !board.is_mobile()) {
\t\tboard.rail = board.rail.filter((r) => r.id !== "me");
\t}'''

A1_NEW = A1_OLD + '''
\t// show_face only runs on clicks; fire it once so the day tabs (and
\t// every other face-state toggle) are correct on first paint.
\tif (!board._is_consultant) board.show_face("board");'''

EDITS = [("page load: initial show_face('board') for staff", A1_OLD, A1_NEW)]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if "fire it once so the day tabs" in src:
        print("Already applied. Nothing to do.")
        return
    if "duty-daytabs" not in src:
        sys.exit("ABORT: v3.57.8 not applied — run apply_v3578.py first.")

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
    with io.open(js_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {JS}")

    init_path = os.path.join(os.getcwd(), INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.8"', '"3.57.9"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.9")
    else:
        print("NOTE: version was not 3.57.8 — left untouched.")


if __name__ == "__main__":
    main()
