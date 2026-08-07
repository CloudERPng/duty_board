#!/usr/bin/env python3
"""Duty Board v3.62.4 — set a task's phase from the task card.

The task<->phase link was one-directional: you could attach tasks from a
phase's 📋 picker, but the task card itself had no phase field — you
couldn't see or set which phase a task belongs to from the task side.
And get_card didn't return milestone, update_task didn't accept it.

Adds:
- get_card returns "milestone" (so the card shows the current phase).
- update_task accepts milestone=... and assigns it (the setter).
- A "Phase" dropdown in the card detail form (data-f="milestone"), which
  the existing generic [data-f] save loop packs and sends automatically —
  no save-handler change needed. Options come from this._ms_names (the
  project's phase map render_kanban already builds).

This also gives you the tool to bulk-link the orphaned Desma tasks (all
milestone=NULL after the earlier wipe): open each, pick its phase. Or use
the phase 📋 picker for bulk — either side now works.

JS + projects.py. No schema (milestone field already exists on the task).
bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.62.3.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. get_card returns milestone ------------------------------------------
GETCARD_OLD = '''\t\t"urgency": doc.urgency,
\t\t"description": doc.description,'''
GETCARD_NEW = '''\t\t"urgency": doc.urgency,
\t\t"milestone": doc.milestone,
\t\t"description": doc.description,'''

# --- 2. update_task accepts + assigns milestone -----------------------------
SIG_OLD = 'def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None):'
SIG_NEW = 'def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None):'

SET_OLD = '''\tdoc.assignee = assignee or None
\tdoc.save(ignore_permissions=True)'''
SET_NEW = '''\tdoc.assignee = assignee or None
\tif milestone is not None:
\t\tdoc.milestone = milestone or None
\tdoc.save(ignore_permissions=True)'''

# --- 3. the Phase dropdown in the card form ---------------------------------
FORM_OLD = '\t\t\t\t<label class="duty-ld-f"><span>${__("Column")}</span><select data-f="column">${["To Do", "In Progress", "Completed", "Suspended"].map((s) => `<option ${t.column === s ? "selected" : ""}>${s}</option>`).join("")}</select></label>'
FORM_NEW = '''\t\t\t\t<label class="duty-ld-f"><span>${__("Column")}</span><select data-f="column">${["To Do", "In Progress", "Completed", "Suspended"].map((s) => `<option ${t.column === s ? "selected" : ""}>${s}</option>`).join("")}</select></label>
\t\t\t\t<label class="duty-ld-f"><span>🚩 ${__("Phase")}</span><select data-f="milestone"><option value="">${__("— none —")}</option>${Object.entries(this._ms_names || {}).map(([id, nm]) => `<option value="${id}" ${t.milestone === id ? "selected" : ""}>${esc(nm)}</option>`).join("")}</select></label>'''

EDITS_PROJ = [
    ("get_card milestone", GETCARD_OLD, GETCARD_NEW),
    ("update_task signature", SIG_OLD, SIG_NEW),
    ("update_task set milestone", SET_OLD, SET_NEW),
]
EDITS_JS = [
    ("card form phase dropdown", FORM_OLD, FORM_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PROJ), encoding="utf-8") as f:
        proj = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if 'data-f="milestone"' in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.62.3"' not in init:
        sys.exit("ABORT: not at v3.62.3.")

    problems = []
    for label, o, _ in EDITS_PROJ:
        if proj.count(o) != 1: problems.append(f"  [{proj.count(o)}] proj: {label}")
    for label, o, _ in EDITS_JS:
        if js.count(o) != 1: problems.append(f"  [{js.count(o)}] js: {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS_PROJ)+len(EDITS_JS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for _l, o, n in EDITS_PROJ: proj = proj.replace(o, n, 1)
    for _l, o, n in EDITS_JS: js = js.replace(o, n, 1)

    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(proj)
    print("  projects.py: get_card +milestone, update_task +milestone")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: phase dropdown in card form")
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.62.3"', '"3.62.4"'))
    print("wrote __init__.py -> 3.62.4")


if __name__ == "__main__":
    main()
