#!/usr/bin/env python3
"""Duty Board v3.80.0 — contracted layouts (video-reported UI fix).

On wide screens the working faces stretched edge-to-edge: My Day put
labels far-left and buttons far-right, Chat right-aligned your own
messages at the screen edge, Projects pinned Team/Consultants/Archive
far from the columns — constant left-right eye travel across empty
middle space.

Fix (desktop >=992px only, additive CSS, same recipe as the client
portal's Tasks-tab fix): each face's content column is capped and kept
together —
- My Day (board face): 1120px, centered.
- Issues: 1160px, centered.
- Sales: 1140px, centered.
- Chat: thread pane capped at 1000px beside the rail (reading stays
  anchored; no more far-edge bubbles).
- Projects: main pane capped at 1220px so the view toggles and
  Team/Consultants/Archive sit beside the columns, not a screen away;
  the kanban keeps its own internal horizontal scroll for many columns.

Mobile untouched. JS(CSS) only. bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.79.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

CSS_OLD = '\t\t\t.duty-kb-files { font-size: 10.5px; color: #65736F; font-weight: 700; }'
CSS_NEW = '''\t\t\t.duty-kb-files { font-size: 10.5px; color: #65736F; font-weight: 700; }
\t\t\t/* --- contracted layouts: keep content together on wide screens --- */
\t\t\t@media (min-width: 992px) {
\t\t\t\tbody:not(.duty-mobile) .duty-board { max-width: 1120px; margin-left: auto; margin-right: auto; }
\t\t\t\tbody:not(.duty-mobile) .duty-issues { max-width: 1160px; margin-left: auto; margin-right: auto; }
\t\t\t\tbody:not(.duty-mobile) .duty-sales { max-width: 1140px; margin-left: auto; margin-right: auto; }
\t\t\t\tbody:not(.duty-mobile) .duty-chat { max-width: 1000px; margin-right: auto; }
\t\t\t\tbody:not(.duty-mobile) .duty-projects { max-width: 1500px; margin-left: auto; margin-right: auto; }
\t\t\t\tbody:not(.duty-mobile) .duty-pj-main { max-width: 1220px; }
\t\t\t}'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "contracted layouts: keep content together" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.79.1"' not in init:
        sys.exit("ABORT: not at v3.79.1.")
    if js.count(CSS_OLD) != 1:
        sys.exit(f"ABORT: css anchor [{js.count(CSS_OLD)}].")

    print("Anchor matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    js = js.replace(CSS_OLD, CSS_NEW, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.79.1"', '"3.80.0"'))
    print("  duty_board.js: face width caps (board/issues/sales/chat/projects)")
    print("wrote __init__.py -> 3.80.0")


if __name__ == "__main__":
    main()
