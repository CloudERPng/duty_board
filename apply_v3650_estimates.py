#!/usr/bin/env python3
"""Duty Board v3.65.0 — effort estimates (review gap #5).

Work Sessions capture actual hours; nothing captured EXPECTED hours, so
"estimated 40h, burned 55h" — the early warning that a phase is going
sideways — was unanswerable. This adds the estimate half:

- Schema: Duty Project Task +estimate_hours (Float).
- Card: an "Est. hours" input (data-f flows through the generic save;
  BOTH call sites forward it).
- get_card returns estimate_hours AND actual_hours (sum of the task's
  Work Session durations) so the card shows est vs actual.
- get_project_board carries estimate_hours + actual_hours per task, and
  the Phases view rolls them up per phase: "est 24h · logged 31h" with
  over-budget emphasis when actual > estimate.

Schema change -> bench migrate && bench build && bench restart.
Anchored, idempotent. Requires v3.64.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
CR = "duty_board/client_room.py"
TASKDT = "duty_board/duty_board/doctype/duty_project_task/duty_project_task.json"
CHECK_ONLY = "--check" in sys.argv

# --- 1. board fetch + per-task actuals --------------------------------------
FETCH_OLD = '''\t\t\t"urgency", "linked_todo", "modified", "awaiting_client", "milestone",
\t\t\t"blocked_by",
\t\t],'''
FETCH_NEW = '''\t\t\t"urgency", "linked_todo", "modified", "awaiting_client", "milestone",
\t\t\t"blocked_by", "estimate_hours",
\t\t],'''

# actuals map — piggyback on the existing batched queries block
ACT_OLD = '''\tnames = [r.name for r in rows]
\tby_name = {r.name: r for r in rows}
\tnote_counts, working, sub_counts = {}, {}, {}'''
ACT_NEW = '''\tnames = [r.name for r in rows]
\tby_name = {r.name: r for r in rows}
\tnote_counts, working, sub_counts, actual_secs = {}, {}, {}, {}'''

ACT2_OLD = '''\t\tfor s in frappe.get_all(
\t\t\t"Duty Project Subtask",
\t\t\tfilters={"parent": ["in", names]},
\t\t\tfields=["parent", "count(name) as total", "sum(case when status='Done' then 1 else 0 end) as done"],
\t\t\tgroup_by="parent",
\t\t):
\t\t\tsub_counts[s.parent] = (cint(s.done), cint(s.total))'''
ACT2_NEW = '''\t\tfor s in frappe.get_all(
\t\t\t"Duty Project Subtask",
\t\t\tfilters={"parent": ["in", names]},
\t\t\tfields=["parent", "count(name) as total", "sum(case when status='Done' then 1 else 0 end) as done"],
\t\t\tgroup_by="parent",
\t\t):
\t\t\tsub_counts[s.parent] = (cint(s.done), cint(s.total))
\t\tfor a in frappe.get_all(
\t\t\t"Work Session",
\t\t\tfilters={"project_task": ["in", names]},
\t\t\tfields=["project_task", "sum(duration) as secs"],
\t\t\tgroup_by="project_task",
\t\t):
\t\t\tactual_secs[a.project_task] = a.secs or 0'''

ACT3_OLD = '''\t\tt.blocked = 0
\t\tt.blocked_title = None'''
ACT3_NEW = '''\t\tt.actual_hours = round((actual_secs.get(t.name, 0) or 0) / 3600.0, 1)
\t\tt.blocked = 0
\t\tt.blocked_title = None'''

# --- 2. get_card returns estimate + actual ----------------------------------
CARD_OLD = '''\t\t"blocked_by": doc.blocked_by,'''
CARD_NEW = '''\t\t"blocked_by": doc.blocked_by,
\t\t"estimate_hours": doc.estimate_hours,
\t\t"actual_hours": round(
\t\t\t(frappe.db.sql(
\t\t\t\t"select coalesce(sum(duration),0) from `tabWork Session` where project_task=%s",
\t\t\t\tname,
\t\t\t)[0][0] or 0) / 3600.0, 1),'''

# --- 3. update_task accepts estimate_hours ----------------------------------
SIG_OLD = 'def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None, blocked_by=None):'
SIG_NEW = 'def update_task(name, title=None, assignee=None, due_date=None, urgency=None, column=None, description=None, client_visible=None, awaiting_client=None, hours=None, milestone=None, blocked_by=None, estimate_hours=None):'

SET_OLD = '''\t\tdoc.blocked_by = new_blk
\tdoc.save(ignore_permissions=True)'''
SET_NEW = '''\t\tdoc.blocked_by = new_blk
\tif estimate_hours is not None:
\t\tfrom frappe.utils import flt
\t\tdoc.estimate_hours = flt(estimate_hours) or None
\tdoc.save(ignore_permissions=True)'''

# --- 4. card form: Est. hours input + est/actual line -----------------------
FORM_OLD = '''\t\t\t\t<label class="duty-ld-f"><span>🔒 ${__("Blocked by")}</span><select data-f="blocked_by"><option value="">${__("— nothing —")}</option>${(t.task_options || []).map((o) => `<option value="${o.name}" ${t.blocked_by === o.name ? "selected" : ""}>${esc(o.title)}</option>`).join("")}</select></label>'''
FORM_NEW = '''\t\t\t\t<label class="duty-ld-f"><span>🔒 ${__("Blocked by")}</span><select data-f="blocked_by"><option value="">${__("— nothing —")}</option>${(t.task_options || []).map((o) => `<option value="${o.name}" ${t.blocked_by === o.name ? "selected" : ""}>${esc(o.title)}</option>`).join("")}</select></label>
\t\t\t\t<label class="duty-ld-f"><span>⏱ ${__("Est. hours")}</span><input type="number" step="0.5" min="0" data-f="estimate_hours" value="${t.estimate_hours || ""}" placeholder="${__("e.g. 4")}">${t.actual_hours ? `<small class="duty-est-act ${t.estimate_hours && t.actual_hours > t.estimate_hours ? "over" : ""}">${__("logged")} ${t.actual_hours}h${t.estimate_hours ? ` / ${t.estimate_hours}h` : ""}</small>` : ""}</label>'''

# --- 5. both save sites ------------------------------------------------------
SAVE1_OLD = '\t\t\t\t\tblocked_by: v.blocked_by || null,\n\t\t\t\t},'
SAVE1_NEW = '\t\t\t\t\tblocked_by: v.blocked_by || null,\n\t\t\t\t\testimate_hours: v.estimate_hours || null,\n\t\t\t\t},'
SAVE2_OLD = '\t\t\t\t\tblocked_by: v2.blocked_by || null,\n\t\t\t\t},'
SAVE2_NEW = '\t\t\t\t\tblocked_by: v2.blocked_by || null,\n\t\t\t\t\testimate_hours: v2.estimate_hours || null,\n\t\t\t\t},'

# --- 6. phase rollup: est vs actual per phase on Phases view ----------------
# _milestone_decorate task subfetch gains the two fields...
DEC_OLD = '''\t\t\tfields=[
\t\t\t\t"name", "title", "column", "assignee", "due_date",
\t\t\t\t"urgency", "description", "awaiting_client",
\t\t\t],'''
DEC_NEW = '''\t\t\tfields=[
\t\t\t\t"name", "title", "column", "assignee", "due_date",
\t\t\t\t"urgency", "description", "awaiting_client", "estimate_hours",
\t\t\t],'''

DEC2_OLD = '''\t\tr.cards_total = len(tasks)
\t\tr.cards_done = sum(1 for t in tasks if t.column == "Completed")
\t\tr.awaiting = sum(1 for t in tasks if cint(t.awaiting_client) and t.column != "Completed")'''
DEC2_NEW = '''\t\tr.cards_total = len(tasks)
\t\tr.cards_done = sum(1 for t in tasks if t.column == "Completed")
\t\tr.awaiting = sum(1 for t in tasks if cint(t.awaiting_client) and t.column != "Completed")
\t\tr.est_hours = round(sum(t.estimate_hours or 0 for t in tasks), 1)
\t\ttask_names = [t.name for t in tasks]
\t\tr.act_hours = 0
\t\tif task_names:
\t\t\tsecs = frappe.db.sql(
\t\t\t\t"select coalesce(sum(duration),0) from `tabWork Session` where project_task in %(n)s",
\t\t\t\t{"n": task_names},
\t\t\t)[0][0] or 0
\t\t\tr.act_hours = round(secs / 3600.0, 1)'''

# ...and the Phases view meta line shows it
META_OLD = ' · ${m.cards_done || 0}/${m.cards_total || 0} ${__("tasks")}${m.baselined'
META_NEW = ' · ${m.cards_done || 0}/${m.cards_total || 0} ${__("tasks")}${m.est_hours ? ` · ⏱ <span class="${m.act_hours > m.est_hours ? "duty-est-over" : ""}">${m.act_hours || 0}h/${m.est_hours}h</span>` : m.act_hours ? ` · ⏱ ${m.act_hours}h` : ""}${m.baselined'

# --- 7. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-kb-blk { font-size: 10.5px; color: #B45309; margin-top: 2px; font-weight: 700; }'
CSS_NEW = '''\t\t\t.duty-kb-blk { font-size: 10.5px; color: #B45309; margin-top: 2px; font-weight: 700; }
\t\t\t.duty-est-act { display: block; font-size: 11px; color: #65736F; margin-top: 2px; }
\t\t\t.duty-est-act.over, .duty-est-over { color: #C2410C; font-weight: 700; }'''


def add_field(dt_path):
    with io.open(dt_path, encoding="utf-8") as f:
        dt = json.load(f)
    if any(fl["fieldname"] == "estimate_hours" for fl in dt["fields"]):
        return False
    dt["fields"].append({
        "fieldname": "estimate_hours", "fieldtype": "Float",
        "label": "Estimate (hours)", "precision": "1",
    })
    if "field_order" in dt:
        dt["field_order"].append("estimate_hours")
    with io.open(dt_path, "w", encoding="utf-8") as f:
        json.dump(dt, f, indent=1)
        f.write("\n")
    return True


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, PROJ, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "estimate_hours=None):" in files[PROJ]:
        print("Already applied. Nothing to do.")
        return
    if '"3.64.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.64.0.")

    checks = [
        (PROJ, FETCH_OLD, "fetch"), (PROJ, ACT_OLD, "maps"), (PROJ, ACT2_OLD, "actuals query"),
        (PROJ, ACT3_OLD, "task actuals"), (PROJ, CARD_OLD, "get_card"), (PROJ, SIG_OLD, "sig"),
        (PROJ, SET_OLD, "setter"), (JS, FORM_OLD, "form"), (JS, SAVE1_OLD, "save1"),
        (JS, SAVE2_OLD, "save2"), (JS, META_OLD, "phase meta"), (JS, CSS_OLD, "css"),
        (CR, DEC_OLD, "decorate fields"), (CR, DEC2_OLD, "decorate rollup"),
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
    print("  doctype: Duty Project Task +estimate_hours")

    pj = files[PROJ]
    for o, n in [(FETCH_OLD, FETCH_NEW), (ACT_OLD, ACT_NEW), (ACT2_OLD, ACT2_NEW), (ACT3_OLD, ACT3_NEW), (CARD_OLD, CARD_NEW), (SIG_OLD, SIG_NEW), (SET_OLD, SET_NEW)]:
        pj = pj.replace(o, n, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: fetch/actuals/get_card/signature/setter")

    cr = files[CR]
    for o, n in [(DEC_OLD, DEC_NEW), (DEC2_OLD, DEC2_NEW)]:
        cr = cr.replace(o, n, 1)
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(cr)
    print("  client_room.py: phase est/actual rollup")

    js = files[JS]
    for o, n in [(FORM_OLD, FORM_NEW), (SAVE1_OLD, SAVE1_NEW), (SAVE2_OLD, SAVE2_NEW), (META_OLD, META_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: est input/both saves/phase meta/css")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.64.0"', '"3.65.0"'))
    print("wrote __init__.py -> 3.65.0")


if __name__ == "__main__":
    main()
