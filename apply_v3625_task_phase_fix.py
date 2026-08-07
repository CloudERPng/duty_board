#!/usr/bin/env python3
"""Duty Board v3.62.5 — fix: task phase not saving from the card.

v3.62.4 added a Phase dropdown (data-f="milestone") assuming the card
save forwarded all [data-f] values. It doesn't — the save enumerates
each argument explicitly in the frappe.call, and milestone was never
added to either call site (the normal save and the consultant-hours
"saveWith" path). So the dropdown value was collected but never sent.

Adds milestone to both update_task calls. update_task already accepts it
(v3.62.4) and get_card already returns it, so this one-line-per-site fix
completes the path.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.62.4.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- call site 1: normal save -----------------------------------------------
C1_OLD = '''\t\t\t\t\tclient_visible: v.client_visible ? 1 : 0,
\t\t\t\t\tawaiting_client: v.awaiting_client ? 1 : 0,
\t\t\t\t\thours: v.hours || null,
\t\t\t\t},'''
C1_NEW = '''\t\t\t\t\tclient_visible: v.client_visible ? 1 : 0,
\t\t\t\t\tawaiting_client: v.awaiting_client ? 1 : 0,
\t\t\t\t\thours: v.hours || null,
\t\t\t\t\tmilestone: v.milestone || null,
\t\t\t\t},'''

# --- call site 2: saveWith (consultant hours path) --------------------------
C2_OLD = '''\t\t\t\t\tawaiting_client: v2.awaiting_client ? 1 : 0, hours: v2.hours,
\t\t\t\t},'''
C2_NEW = '''\t\t\t\t\tawaiting_client: v2.awaiting_client ? 1 : 0, hours: v2.hours,
\t\t\t\t\tmilestone: v2.milestone || null,
\t\t\t\t},'''

EDITS = [
    ("normal save +milestone", C1_OLD, C1_NEW),
    ("saveWith +milestone", C2_OLD, C2_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "milestone: v.milestone || null" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.62.4"' not in init:
        sys.exit("ABORT: not at v3.62.4.")

    problems = [f"  [{js.count(o)}] {label}" for label, o, _ in EDITS if js.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for label, old, new in EDITS:
        js = js.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.62.4"', '"3.62.5"'))
    print("wrote __init__.py -> 3.62.5")


if __name__ == "__main__":
    main()
