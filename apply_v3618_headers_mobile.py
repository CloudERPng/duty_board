#!/usr/bin/env python3
"""Duty Board v3.61.8 — task column headers + mobile sub-tab fix (correct).

A) HEADERS: a header row (Task/Owner/Due/Priority/Status) above each
   phase's task grid, desktop only (hidden <=640px where rows stack).
B) MOBILE SUB-TABS: the switch rule used `.rightcol > .card` (child
   combinator). On mobile .rightcol is display:contents, removing its
   box so the child combinator fails to match. Switched to a DESCENDANT
   selector (`.rightcol .card`) which matches at every width — one rule,
   both breakpoints.

portal only. Requires v3.61.7.
"""
import io, os, sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

LIST_OLD = '<div class="mstasks${m.awaiting ? " open" : ""}">${m.tasks.map(taskRow).join("")}</div>'
LIST_NEW = '<div class="mstasks${m.awaiting ? " open" : ""}"><div class="ctask ctask-head"><div class="ctask-main">Task</div><div>Owner</div><div>Due</div><div>Priority</div><div>Status</div></div>${m.tasks.map(taskRow).join("")}</div>'

HCSS_OLD = '\t.ctask-lbl { display: none; }'
HCSS_NEW = '''\t.ctask-lbl { display: none; }
\t.ctask-head { background: #F4F7F6; border-color: #E4EAE8; padding-top: 6px; padding-bottom: 6px; font-size: 11px; font-weight: 800; letter-spacing: .03em; text-transform: uppercase; color: #8a958f; }
\t.ctask-head > div { align-self: center; }'''

HCSS_HIDE_OLD = '''\t@media (max-width: 640px) {
\t\t.ctask { grid-template-columns: 1fr; row-gap: 4px; }'''
HCSS_HIDE_NEW = '''\t@media (max-width: 640px) {
\t\t.ctask-head { display: none; }
\t\t.ctask { grid-template-columns: 1fr; row-gap: 4px; }'''

SWITCH_OLD = '''\t\tbody[data-tab="pm"][data-pmsub="phases"] .rightcol > .card:not(.mstones),
\t\tbody[data-tab="pm"][data-pmsub="chreqs"] .rightcol > .card:not(.chreqs),
\t\tbody[data-tab="pm"][data-pmsub="timeline"] .rightcol > .card:not(.tlx),
\t\tbody[data-tab="pm"][data-pmsub="uat"] .rightcol > .card:not(.uatx) { display: none !important; }'''
SWITCH_NEW = '''\t\tbody[data-tab="pm"][data-pmsub="phases"] .rightcol .card:not(.mstones),
\t\tbody[data-tab="pm"][data-pmsub="chreqs"] .rightcol .card:not(.chreqs),
\t\tbody[data-tab="pm"][data-pmsub="timeline"] .rightcol .card:not(.tlx),
\t\tbody[data-tab="pm"][data-pmsub="uat"] .rightcol .card:not(.uatx) { display: none !important; }'''

MOBILE_OLD = '''\t\tbody[data-tab="pm"] .card:not(.mstones):not(.chreqs):not(.uatx):not(.tlx) { display: none; }
\t\tbody[data-tab="training"] .card:not(.acad) { display: none; }
\t\tbody[data-tab="docs"] .card:not(.docs) { display: none; }
\t\tbody[data-tab="home"] .msgs { max-height: calc(100vh - 380px); }'''
MOBILE_NEW = '''\t\tbody[data-tab="pm"] .card:not(.mstones):not(.chreqs):not(.uatx):not(.tlx) { display: none; }
\t\tbody[data-tab="pm"] #pmsubbar { display: flex !important; }
\t\tbody[data-tab="training"] .card:not(.acad) { display: none; }
\t\tbody[data-tab="docs"] .card:not(.docs) { display: none; }
\t\tbody[data-tab="home"] .msgs { max-height: calc(100vh - 380px); }'''

EDITS = [
    ("header row markup", LIST_OLD, LIST_NEW),
    ("header CSS", HCSS_OLD, HCSS_NEW),
    ("header hide on mobile", HCSS_HIDE_OLD, HCSS_HIDE_NEW),
    ("switch: child -> descendant", SWITCH_OLD, SWITCH_NEW),
    ("mobile bar visible", MOBILE_OLD, MOBILE_NEW),
]

def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PORTAL), encoding="utf-8") as f:
        html = f.read()
    if "ctask-head" in html:
        print("Already applied. Nothing to do."); return
    if '"3.61.7"' not in init:
        sys.exit("ABORT: not at v3.61.7.")
    problems = [f"  [{html.count(o)}] {label}" for label, o, _ in EDITS if html.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:"); print("\n".join(problems)); sys.exit(1)
    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written."); return
    for label, old, new in EDITS:
        html = html.replace(old, new, 1); print(f"  applied: {label}")
    with io.open(os.path.join(root, PORTAL), "w", encoding="utf-8") as f:
        f.write(html)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.61.7"', '"3.61.8"'))
    print("wrote __init__.py -> 3.61.8")

if __name__ == "__main__":
    main()
