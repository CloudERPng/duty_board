#!/usr/bin/env python3
"""Duty Board v3.64.0 — task dependencies (blocked_by).

Gap #2 from the PM review: tasks floated independently — "Data Migration
can't start until Configuration signs off" lived only in heads. This adds
a single blocked_by link per task:

- Schema: Duty Project Task +blocked_by (Link -> Duty Project Task).
  Chains compose (C->B->A = a mini critical path); one blocker covers the
  dominant case without many-to-many weight.
- Board: a task whose blocker is not yet Completed shows a 🔒 chip with
  the blocker's name. Blocker completes -> lock disappears automatically.
- Card: a "Blocked by" dropdown of this project's other tasks (get_card
  returns task_options + blocked_by; update_task accepts blocked_by).
  BOTH save call sites forward it (the v3.62.5 lesson, applied first).
- Cycle guard: setting a blocker walks the chain (max 50 hops) and
  refuses a loop, including self.

Schema change -> bench migrate && bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.63.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
TASKDT = "duty_board/duty_board/doctype/duty_project_task/duty_project_task.json"
CHECK_ONLY = "--check" in sys.argv

# --- 1. board fetch + blocked computation -----------------------------------
FETCH_OLD = '''\t\t\t"urgency", "linked_todo", "modified", "awaiting_client", "milestone",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)'''
FETCH_NEW = '''\t\t\t"urgency", "linked_todo", "modified", "awaiting_client", "milestone",
\t\t\t"blocked_by",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)'''

# compute blocked flag in the per-task loop (anchor: the subs line)
BLOCKED_OLD = '''\t\tt.subs_done, t.subs_total = sub_counts.get(t.name, (0, 0))
\t\t# t.milestone already present from the fetch
\t\ttasks.setdefault(t.column, []).append(t)'''
BLOCKED_NEW = '''\t\tt.subs_done, t.subs_total = sub_counts.get(t.name, (0, 0))
\t\t# t.milestone already present from the fetch
\t\tt.blocked = 0
\t\tt.blocked_title = None
\t\tif t.blocked_by:
\t\t\tblk = by_name.get(t.blocked_by)
\t\t\tif blk is not None and blk.column != "Completed":
\t\t\t\tt.blocked = 1
\t\t\t\tt.blocked_title = blk.title
\t\ttasks.setdefault(t.column, []).append(t)'''

# need by_name map — anchor on the names list construction
NAMES_OLD = '''\tnames = [r.name for r in rows]
\tnote_counts, working, sub_counts = {}, {}, {}'''
NAMES_NEW = '''\tnames = [r.name for r in rows]
\tby_name = {r.name: r for r in rows}
\tnote_counts, working, sub_counts = {}, {}, {}'''

# --- 2. get_card returns blocked_by + task_options --------------------------
CARD_OLD = '''\t\t"urgency": doc.urgency,
\t\t"milestone": doc.milestone,'''
CARD_NEW = '''\t\t"urgency": doc.urgency,
\t\t"milestone": doc.milestone,
\t\t"blocked_by": doc.blocked_by,
\t\t"task_options": [
\t\t\t{"name": r.name, "title": r.title}
\t\t\tfor r in frappe.get_all(
\t\t\t\t"Duty Project Task",
\t\t\t\tfilters={"project": doc.project, "name": ["!=", doc.name]},
\t\t\t\tfields=["name", "title"],
\t\t\t\torder_by="creation asc",
\t\t\t)
\t\t],'''

# --- 3. update_task accepts blocked_by with cycle guard ---------------------
SIG_OLD = 'def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None):'
SIG_NEW = 'def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None, blocked_by=None):'

SET_OLD = '''\tif milestone is not None:
\t\tdoc.milestone = milestone or None
\tdoc.save(ignore_permissions=True)'''
SET_NEW = '''\tif milestone is not None:
\t\tdoc.milestone = milestone or None
\tif blocked_by is not None:
\t\tnew_blk = blocked_by or None
\t\tif new_blk:
\t\t\tif new_blk == doc.name:
\t\t\t\tfrappe.throw(_("A task cannot be blocked by itself."))
\t\t\t# cycle guard: walk up the chain from the proposed blocker
\t\t\tseen, cur = set(), new_blk
\t\t\tfor _hop in range(50):
\t\t\t\tif cur == doc.name:
\t\t\t\t\tfrappe.throw(_("That would create a dependency loop."))
\t\t\t\tif not cur or cur in seen:
\t\t\t\t\tbreak
\t\t\t\tseen.add(cur)
\t\t\t\tcur = frappe.db.get_value("Duty Project Task", cur, "blocked_by")
\t\tdoc.blocked_by = new_blk
\tdoc.save(ignore_permissions=True)'''

# --- 4. card form: Blocked by dropdown (after the phase dropdown) -----------
FORM_OLD = '''\t\t\t\t<label class="duty-ld-f"><span>🚩 ${__("Phase")}</span><select data-f="milestone"><option value="">${__("— none —")}</option>${Object.entries(this._ms_names || {}).map(([id, nm]) => `<option value="${id}" ${t.milestone === id ? "selected" : ""}>${esc(nm)}</option>`).join("")}</select></label>'''
FORM_NEW = '''\t\t\t\t<label class="duty-ld-f"><span>🚩 ${__("Phase")}</span><select data-f="milestone"><option value="">${__("— none —")}</option>${Object.entries(this._ms_names || {}).map(([id, nm]) => `<option value="${id}" ${t.milestone === id ? "selected" : ""}>${esc(nm)}</option>`).join("")}</select></label>
\t\t\t\t<label class="duty-ld-f"><span>🔒 ${__("Blocked by")}</span><select data-f="blocked_by"><option value="">${__("— nothing —")}</option>${(t.task_options || []).map((o) => `<option value="${o.name}" ${t.blocked_by === o.name ? "selected" : ""}>${esc(o.title)}</option>`).join("")}</select></label>'''

# --- 5. BOTH save call sites forward blocked_by (v3.62.5 lesson) ------------
SAVE1_OLD = '\t\t\t\t\tmilestone: v.milestone || null,\n\t\t\t\t},'
SAVE1_NEW = '\t\t\t\t\tmilestone: v.milestone || null,\n\t\t\t\t\tblocked_by: v.blocked_by || null,\n\t\t\t\t},'

SAVE2_OLD = '\t\t\t\t\tmilestone: v2.milestone || null,\n\t\t\t\t},'
SAVE2_NEW = '\t\t\t\t\tmilestone: v2.milestone || null,\n\t\t\t\t\tblocked_by: v2.blocked_by || null,\n\t\t\t\t},'

# --- 6. board card: 🔒 blocked chip -----------------------------------------
CHIP_OLD = '''\t\t\t\t${t.milestone && this._ms_names && this._ms_names[t.milestone] ? `<div class="duty-kb-ms">🚩 ${frappe.utils.escape_html(this._ms_names[t.milestone])}</div>` : ""}'''
CHIP_NEW = '''\t\t\t\t${t.milestone && this._ms_names && this._ms_names[t.milestone] ? `<div class="duty-kb-ms">🚩 ${frappe.utils.escape_html(this._ms_names[t.milestone])}</div>` : ""}
\t\t\t\t${t.blocked ? `<div class="duty-kb-blk">🔒 ${__("blocked by")} ${frappe.utils.escape_html(t.blocked_title || "")}</div>` : ""}'''

# --- 7. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-kb-ms { font-size: 10.5px; color: #0F5C55; margin-top: 2px; font-weight: 600; }'
CSS_NEW = '''\t\t\t.duty-kb-ms { font-size: 10.5px; color: #0F5C55; margin-top: 2px; font-weight: 600; }
\t\t\t.duty-kb-blk { font-size: 10.5px; color: #B45309; margin-top: 2px; font-weight: 700; }'''


def add_field(dt_path):
    with io.open(dt_path, encoding="utf-8") as f:
        dt = json.load(f)
    if any(fl["fieldname"] == "blocked_by" for fl in dt["fields"]):
        return False
    dt["fields"].append({
        "fieldname": "blocked_by", "fieldtype": "Link",
        "label": "Blocked By", "options": "Duty Project Task",
    })
    if "field_order" in dt:
        dt["field_order"].append("blocked_by")
    with io.open(dt_path, "w", encoding="utf-8") as f:
        json.dump(dt, f, indent=1)
        f.write("\n")
    return True


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "blocked_by=None):" in files[PROJ]:
        print("Already applied. Nothing to do.")
        return
    if '"3.63.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.63.1.")

    checks = [
        (PROJ, FETCH_OLD, "fetch"), (PROJ, BLOCKED_OLD, "blocked calc"),
        (PROJ, NAMES_OLD, "names map"), (PROJ, CARD_OLD, "get_card"),
        (PROJ, SIG_OLD, "signature"), (PROJ, SET_OLD, "setter"),
        (JS, FORM_OLD, "form dropdown"), (JS, SAVE1_OLD, "save site 1"),
        (JS, SAVE2_OLD, "save site 2"), (JS, CHIP_OLD, "board chip"),
        (JS, CSS_OLD, "css"),
    ]
    problems = [f"  [{files[f].count(o)}] {label}" for f, o, label in checks if files[f].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(checks)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_field(os.path.join(root, TASKDT))
    print("  doctype: Duty Project Task +blocked_by")

    pj = files[PROJ]
    for o, n in [(FETCH_OLD, FETCH_NEW), (NAMES_OLD, NAMES_NEW), (BLOCKED_OLD, BLOCKED_NEW), (CARD_OLD, CARD_NEW), (SIG_OLD, SIG_NEW), (SET_OLD, SET_NEW)]:
        pj = pj.replace(o, n, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: fetch/blocked calc/get_card/signature/setter+cycle guard")

    js = files[JS]
    for o, n in [(FORM_OLD, FORM_NEW), (SAVE1_OLD, SAVE1_NEW), (SAVE2_OLD, SAVE2_NEW), (CHIP_OLD, CHIP_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: dropdown/both save sites/board chip/css")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.63.1"', '"3.64.0"'))
    print("wrote __init__.py -> 3.64.0")


if __name__ == "__main__":
    main()
