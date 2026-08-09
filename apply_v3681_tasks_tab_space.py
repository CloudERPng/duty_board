#!/usr/bin/env python3
"""Duty Board v3.68.1 — review item 1: client Tasks tab uses the space.

The Tasks tab capped its container at 860px (narrower even than the
Accounting tab's 1180px) and set the table at 14px with 11px headers and
tight 8px cells — a lot of viewport left empty and small type doing the
work. Desktop only changes:

- Container: 860px -> 1280px (Accounting keeps its own width).
- Table: 14px -> 15.5px body; headers 11px -> 12px; cell padding
  8px -> 12px 10px so rows breathe; title column bolder at 16px.
- Status pills scale up a notch inside the tasks table so they don't
  look shrunken beside the larger type.

Mobile (<=899px) keeps its stacked card layout untouched — it already
uses the space well.

portal only. bench build --app duty_board && bench restart,
clear-website-cache. Anchored, idempotent. Requires v3.68.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

WIDTH_OLD = '\tbody[data-tab="tasks"] .wrap { max-width: 860px; }'
WIDTH_NEW = '\tbody[data-tab="tasks"] .wrap { max-width: 1280px; }'

FONT_OLD = '''\ttable.tt { width: 100%; border-collapse: collapse; font-size: 14px; }
\ttable.tt th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;'''
FONT_NEW = '''\ttable.tt { width: 100%; border-collapse: collapse; font-size: 14px; }
\tbody[data-tab="tasks"] table.tt { font-size: 15.5px; }
\tbody[data-tab="tasks"] table.tt td { padding: 12px 10px; }
\tbody[data-tab="tasks"] td.tt-title { font-size: 16px; font-weight: 700; }
\tbody[data-tab="tasks"] table.tt .pill { font-size: 12.5px; padding: 4px 12px; }
\ttable.tt th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;'''

HDR_OLD = '\ttable.tt td { padding: 8px; border-bottom: 1px dashed #eee; vertical-align: top; }'
HDR_NEW = '''\ttable.tt td { padding: 8px; border-bottom: 1px dashed #eee; vertical-align: top; }
\tbody[data-tab="tasks"] table.tt th { font-size: 12px; padding-bottom: 8px; }'''

EDITS = [
    ("tasks wrap width", WIDTH_OLD, WIDTH_NEW),
    ("tasks table type scale", FONT_OLD, FONT_NEW),
    ("tasks table headers", HDR_OLD, HDR_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PORTAL), encoding="utf-8") as f:
        html = f.read()

    if 'body[data-tab="tasks"] table.tt { font-size: 15.5px; }' in html:
        print("Already applied. Nothing to do.")
        return
    if '"3.68.0"' not in init:
        sys.exit("ABORT: not at v3.68.0.")

    problems = [f"  [{html.count(o)}] {label}" for label, o, _ in EDITS if html.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for label, old, new in EDITS:
        html = html.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, PORTAL), "w", encoding="utf-8") as f:
        f.write(html)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.68.0"', '"3.68.1"'))
    print("wrote __init__.py -> 3.68.1")


if __name__ == "__main__":
    main()
