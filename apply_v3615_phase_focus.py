#!/usr/bin/env python3
"""Duty Board v3.61.5 — Stage 3: the client phase strip shows ONE project.

The selector already scopes the phase strip when a client picks a
project (v3.60.2b). The gap was the "All projects" default: it blended
every project's phases into one strip — Discovery→Hypercare twice for a
two-project room, with a single meaningless "you are here". A phase
journey only makes sense within one project.

Fix: renderMilestones computes an EFFECTIVE project. If the client has
explicitly picked one, use it. If they're on "All" but the room has 2+
real projects, auto-focus the FIRST real project (not General) for the
strip — and label the strip with that project's name so it's clear which
journey is shown. Tasks and documents keep their "All" behaviour; only
the phase strip forces a single project, because that's the only view
where blending is incoherent.

portal only. bench build --app duty_board && bench restart,
clear-website-cache. Anchored, idempotent. Requires v3.61.4.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

OLD = '''function renderMilestones(rows) {
\twindow._msrows = rows || [];
\trows = (rows || []).filter((m) => _pselMatch(m.project));
\tconst DOTS = { "Upcoming": "⚪", "In Progress": "🔵", "Awaiting Approval": "🟠", "Approved": "✅" };
\tconst done = rows.filter((m) => m.status === "Approved").length;
\tconst wrap = document.getElementById("msbarwrap");'''

NEW = '''function _phaseFocusProject(allRows) {
\t// Which project's journey the strip shows. Explicit pick wins; otherwise,
\t// on "All", focus the first REAL project (a phase strip blending projects
\t// is meaningless). Returns { id, label } or null (single/no project).
\tif (window._psel) {
\t\tconst p = (window._projs || []).find((x) => x.id === window._psel);
\t\treturn { id: window._psel, label: p ? p.label : null };
\t}
\tconst realIds = [...new Set((allRows || []).map((m) => m.project).filter(Boolean))];
\tif (realIds.length <= 1) return null; // single project: no focus needed
\tconst first = (window._projs || []).find((x) => x.id !== "__general__" && realIds.includes(x.id))
\t\t|| { id: realIds[0], label: null };
\treturn { id: first.id, label: first.label };
}
function renderMilestones(rows) {
\twindow._msrows = rows || [];
\tconst _focus = _phaseFocusProject(rows);
\tif (_focus && _focus.id) {
\t\trows = (rows || []).filter((m) => m.project === _focus.id);
\t} else {
\t\trows = (rows || []).filter((m) => _pselMatch(m.project));
\t}
\tconst DOTS = { "Upcoming": "⚪", "In Progress": "🔵", "Awaiting Approval": "🟠", "Approved": "✅" };
\tconst done = rows.filter((m) => m.status === "Approved").length;
\tconst wrap = document.getElementById("msbarwrap");'''

# Add a project label above the strip when focusing (so the client knows which
# journey they're looking at while on "All").
LABEL_OLD = '''\tif (rows.length) {
\t\twrap.style.display = "block";
\t\tconst cur = rows.findIndex((m) => m.status !== "Approved");
\t\twrap.innerHTML = `<div id="msstep">${rows.map((m, i) => {'''
LABEL_NEW = '''\tif (rows.length) {
\t\twrap.style.display = "block";
\t\tconst cur = rows.findIndex((m) => m.status !== "Approved");
\t\tconst _focusLbl = (!window._psel && _focus && _focus.label) ? `<div class="msfocus">📁 ${esc(_focus.label)}</div>` : "";
\t\twrap.innerHTML = _focusLbl + `<div id="msstep">${rows.map((m, i) => {'''

CSS_OLD = '.msshere { display: block; font-size: 10px; font-weight: 800; color: #0B6B4F; margin-top: 2px; }'
CSS_NEW = '''.msshere { display: block; font-size: 10px; font-weight: 800; color: #0B6B4F; margin-top: 2px; }
.msfocus { font-size: 12px; font-weight: 800; color: #0F5C55; margin: 0 0 6px; }'''

EDITS = [
    ("effective-project focus", OLD, NEW),
    ("focus label above strip", LABEL_OLD, LABEL_NEW),
    ("focus label CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PORTAL), encoding="utf-8") as f:
        html = f.read()

    if "_phaseFocusProject" in html:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.4"' not in init:
        sys.exit("ABORT: not at v3.61.4.")

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
        f.write(init.replace('"3.61.4"', '"3.61.5"'))
    print("wrote __init__.py -> 3.61.5")


if __name__ == "__main__":
    main()
