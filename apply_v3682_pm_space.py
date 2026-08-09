#!/usr/bin/env python3
"""Duty Board v3.68.2 — review item 2: Projects/Phases screen space + type.

The PM tab's outer wrap was already wide (1560px) but the inner rightcol
capped at 1100px — the real constraint — and the phase list ran at 14px
rows / 12px descriptions / 13px task grid. Desktop-only changes, same
treatment as the Tasks tab (v3.68.1):

- Inner column: 1100px -> 1360px (sub-tab bar matches).
- Phase rows: 14 -> 15.5px, titles 16px, descriptions 12 -> 13.5px,
  target-date/meta 12 -> 13px, tasks-toggle 12 -> 13px, row padding
  9px -> 12px so the list breathes.
- Client task grid inside phases: 13 -> 14px titles, descriptions
  11.5 -> 12.5px, and the grid columns widened to fit the larger type.

Mobile untouched. portal only. bench build + restart +
clear-website-cache. Anchored, idempotent. Requires v3.68.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

# 1. inner column + sub-tab bar widths
COL_OLD = '''\t\t\tbody[data-tab="pm"] .rightcol {
\t\t\t\tdisplay: block !important; width: auto; max-width: 1100px; margin: 0 auto;
\t\t\t}'''
COL_NEW = '''\t\t\tbody[data-tab="pm"] .rightcol {
\t\t\t\tdisplay: block !important; width: auto; max-width: 1360px; margin: 0 auto;
\t\t\t}'''

BAR_OLD = '''\t\tbody[data-tab="pm"] #pmsubbar {
\t\t\tdisplay: flex; gap: 4px; max-width: 1100px; margin: 0 auto 14px; flex-wrap: wrap;
\t\t}'''
BAR_NEW = '''\t\tbody[data-tab="pm"] #pmsubbar {
\t\t\tdisplay: flex; gap: 4px; max-width: 1360px; margin: 0 auto 14px; flex-wrap: wrap;
\t\t}'''

# 2. phase rows scale (desktop, pm tab only)
MS_OLD = '\t.ms { display: flex; gap: 10px; padding: 9px 0; border-bottom: 1px dashed #eee; align-items: baseline; flex-wrap: wrap; font-size: 14px; }'
MS_NEW = '''\t.ms { display: flex; gap: 10px; padding: 9px 0; border-bottom: 1px dashed #eee; align-items: baseline; flex-wrap: wrap; font-size: 14px; }
\t@media (min-width: 900px) {
\t\tbody[data-tab="pm"] .ms { font-size: 15.5px; padding: 12px 0; }
\t\tbody[data-tab="pm"] .ms b { font-size: 16px; }
\t\tbody[data-tab="pm"] .ms .desc { font-size: 13.5px; }
\t\tbody[data-tab="pm"] .ms .muted { font-size: 13px !important; }
\t\tbody[data-tab="pm"] .mstoggle { font-size: 13px; }
\t\tbody[data-tab="pm"] .ctask { grid-template-columns: minmax(0,1fr) 150px 126px 100px 112px; }
\t\tbody[data-tab="pm"] .ctask-tw b { font-size: 14px; }
\t\tbody[data-tab="pm"] .ctask-desc { font-size: 12.5px; }
\t\tbody[data-tab="pm"] .ctask-who, body[data-tab="pm"] .ctask-due { font-size: 13px; }
\t}'''


EDITS = [
    ("pm inner column width", COL_OLD, COL_NEW),
    ("pm sub-tab bar width", BAR_OLD, BAR_NEW),
    ("phase + task type scale", MS_OLD, MS_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PORTAL), encoding="utf-8") as f:
        html = f.read()

    if 'body[data-tab="pm"] .ms { font-size: 15.5px' in html:
        print("Already applied. Nothing to do.")
        return
    if '"3.68.1"' not in init:
        sys.exit("ABORT: not at v3.68.1.")

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
        f.write(init.replace('"3.68.1"', '"3.68.2"'))
    print("wrote __init__.py -> 3.68.2")


if __name__ == "__main__":
    main()
