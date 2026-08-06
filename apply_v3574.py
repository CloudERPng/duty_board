#!/usr/bin/env python3
"""Duty Board v3.57.4 — one view on a 15" laptop.

Root cause (measured, not guessed): Frappe's desk page container sizes
itself to a fixed breakpoint width and does not subtract the expanded
workspace sidebar. On a 1315px CSS viewport the .layout-main-section
wrapper computed 1183px wide starting 237px in — 106px past the right
edge. Every face on this page overflowed; Chat was just the first one
dense enough at both edges to make the horizontal panning obvious.

The fix:
1. FLUID CONTAINERS, this page only: both page containers (head and
   body) get max-width 100%, so content sizes to the space that is
   actually there. This removes the overflow AND returns the margin
   Frappe was reserving — more room, not less. Other desk pages are
   untouched.
2. SMALL-LAPTOP TUNING (≤1440px viewports): conversation rail 360→320
   and the room task column 360→320 inside the Chat face, so rail +
   thread + tasks share a 15" screen with a readable chat column even
   with the workspace sidebar expanded. Larger monitors keep v3.57.2
   sizing untouched.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.3.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. fluid containers, scoped to this page's wrapper ----------------------

A1_OLD = '\tconst board = new DutyBoard(page);'
A1_NEW = '''\t// Frappe's fixed-width .container ignores the expanded workspace
\t// sidebar and overflows small viewports (measured: 106px at 1315px).
\t// Fluid containers on THIS page only — head and body stay aligned.
\t$(wrapper).find(".container").addClass("duty-fluid");
''' + A1_OLD

# --- 2. styles ---------------------------------------------------------------

A2_OLD = '\t\t\t.duty-chatface .duty-dm-list .duty-msg { margin-bottom: 14px; line-height: 1.55; }'

A2_NEW = A2_OLD + '''
\t\t\t/* .duty-fluid.container out-specifies Bootstrap's .container breakpoints. */
\t\t\t.duty-fluid.container { max-width: 100%; }
\t\t\t@media (max-width: 1440px) {
\t\t\t\t/* 15" laptops: rail + thread + tasks in one view, sidebar expanded or not. */
\t\t\t\t.duty-ch-rail { width: 320px; min-width: 320px; }
\t\t\t\t.duty-chatface .duty-cr-side { width: 320px; }
\t\t\t}'''

EDITS = [
    ("page load: fluid containers", A1_OLD, A1_NEW),
    ("styles: fluid rule + <=1440px tuning", A2_OLD, A2_NEW),
]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if "duty-ch-new" not in src:
        sys.exit("ABORT: v3.57.3 not applied — run apply_v3573.py first.")
    if "duty-fluid" in src:
        print("Already applied — duty-fluid present. Nothing to do.")
        return

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
    new_init = init.replace('"3.57.3"', '"3.57.4"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.4")
    else:
        print("NOTE: __init__.py not at 3.57.3 — version left untouched.")


if __name__ == "__main__":
    main()
