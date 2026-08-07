#!/usr/bin/env python3
"""Duty Board v3.62.3 — phase task management + milestone on task cards.

Three fixes, all the same root cause as the edit-button gap: retiring the
legacy room-card dialog (v3.61.9) took the task-management UI with it, and
the new Projects-face Phases view never got it. Backends survive.

1. TASK LIST under each phase: the Phases view showed only a count
   ("0 of 8 tasks"). Now each phase expands to show its actual tasks
   (title · status · owner), using m.tasks already in the payload.
2. ADD/REMOVE tasks to a phase: a 📋 action per phase opens a picker of
   THIS project's tasks with checkboxes, wired to the existing
   milestone_set_tasks. A new project-scoped options endpoint
   (project_milestone_task_options) replaces the room/customer-wide
   legacy one so the list is scoped to the project.
3. MILESTONE ON THE CARD: get_project_board omitted the task's milestone,
   so Kanban cards didn't show their phase. Adds milestone to the fetch
   and a phase-name map + chip on each card.

JS + projects.py + one new client_room endpoint. No schema.
bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.62.2.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CR = "duty_board/client_room.py"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. projects.py: board fetch includes milestone -------------------------
BOARD_OLD = '''\t\tfields=[
\t\t\t"name", "title", "column", "assignee", "due_date",
\t\t\t"urgency", "linked_todo", "modified", "awaiting_client",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)'''
BOARD_NEW = '''\t\tfields=[
\t\t\t"name", "title", "column", "assignee", "due_date",
\t\t\t"urgency", "linked_todo", "modified", "awaiting_client", "milestone",
\t\t],
\t\torder_by="sort_order asc, creation asc",
\t)'''

# carry milestone into the per-task dict the board returns
BOARD_T_OLD = '''\t\tt.subs_done, t.subs_total = sub_counts.get(t.name, (0, 0))
\t\ttasks.setdefault(t.column, []).append(t)'''
BOARD_T_NEW = '''\t\tt.subs_done, t.subs_total = sub_counts.get(t.name, (0, 0))
\t\t# t.milestone already present from the fetch
\t\ttasks.setdefault(t.column, []).append(t)'''

# --- 2. client_room.py: project-scoped task-options endpoint ----------------
EP_ANCHOR = '''@frappe.whitelist()
def milestone_set_tasks(id, tasks):'''
EP_NEW = '''@frappe.whitelist()
def project_milestone_task_options(id):
\t"""Tasks of THIS milestone's project, flagged for the picker. Project-
\tscoped (unlike the legacy customer-wide milestone_task_options)."""
\t_staff_only()
\tms = frappe.get_doc("Duty Milestone", id)
\tproject = frappe.db.get_value("Duty Milestone", id, "project")
\tout = []
\tif not project:
\t\treturn out
\tfor t in frappe.get_all(
\t\t"Duty Project Task",
\t\tfilters={"project": project},
\t\tfields=["name", "title", "column", "milestone"],
\t\torder_by="creation asc",
\t):
\t\tout.append({
\t\t\t"name": t.name,
\t\t\t"title": t.title,
\t\t\t"column": t.column,
\t\t\t"checked": t.milestone == id,
\t\t\t"elsewhere": bool(t.milestone and t.milestone != id),
\t\t})
\treturn out


@frappe.whitelist()
def milestone_set_tasks(id, tasks):'''

# --- 3. JS: add 📋 action + expandable task sublist (single clean anchor) ----
ACTS_OLD = '''\t\t\t\t\t<div class="duty-phase-acts">
\t\t\t\t\t\t<a data-a="up" title="${__("Move up")}">▲</a>
\t\t\t\t\t\t<a data-a="down" title="${__("Move down")}">▼</a>
\t\t\t\t\t\t${!locked ? `<a data-a="edit" title="${__("Edit phase")}">✎</a>` : ""}
\t\t\t\t\t\t${st === "active" && m.status !== "In Progress" ? `<a data-a="start" title="${__("Mark in progress")}">▶</a>` : ""}
\t\t\t\t\t\t${!locked && m.status !== "Awaiting Approval" ? `<a data-a="ask" title="${__("Request client sign-off")}">✅</a>` : ""}
\t\t\t\t\t\t${!locked ? `<a data-a="del" title="${__("Delete phase")}">🗑</a>` : ""}
\t\t\t\t\t</div>
\t\t\t\t</div>`;
\t\t\t}).join("");'''
ACTS_NEW = '''\t\t\t\t\t<div class="duty-phase-acts">
\t\t\t\t\t\t<a data-a="up" title="${__("Move up")}">▲</a>
\t\t\t\t\t\t<a data-a="down" title="${__("Move down")}">▼</a>
\t\t\t\t\t\t<a data-a="tasks" title="${__("Add or remove tasks")}">📋</a>
\t\t\t\t\t\t${!locked ? `<a data-a="edit" title="${__("Edit phase")}">✎</a>` : ""}
\t\t\t\t\t\t${st === "active" && m.status !== "In Progress" ? `<a data-a="start" title="${__("Mark in progress")}">▶</a>` : ""}
\t\t\t\t\t\t${!locked && m.status !== "Awaiting Approval" ? `<a data-a="ask" title="${__("Request client sign-off")}">✅</a>` : ""}
\t\t\t\t\t\t${!locked ? `<a data-a="del" title="${__("Delete phase")}">🗑</a>` : ""}
\t\t\t\t\t</div>
\t\t\t\t\t${(m.tasks || []).length ? `<div class="duty-phase-tasks">${m.tasks.map((tk) => `<div class="duty-phase-task"><span class="duty-pt-dot ${tk.status === "Done" ? "done" : ""}"></span><span class="duty-pt-title">${esc(tk.title)}</span><span class="duty-pt-st">${esc(tk.status || "")}</span>${tk.assignee ? `<span class="duty-pt-who">${esc(tk.assignee)}</span>` : ""}</div>`).join("")}</div>` : `<div class="duty-phase-tasks empty">${__("No tasks in this phase yet — 📋 to add.")}</div>`}
\t\t\t\t</div>`;
\t\t\t}).join("");'''

# --- 4. JS: the 📋 tasks handler (picker) -----------------------------------
HANDLER_OLD = '''\t\t\t\tif (a === "del") return frappe.confirm(__("Delete this phase? Its tasks are kept but unlinked."), () => frappe.call({ method: "duty_board.client_room.milestone_delete", args: { id: id }, callback: done }));'''
HANDLER_NEW = '''\t\t\t\tif (a === "del") return frappe.confirm(__("Delete this phase? Its tasks are kept but unlinked."), () => frappe.call({ method: "duty_board.client_room.milestone_delete", args: { id: id }, callback: done }));
\t\t\t\tif (a === "tasks") {
\t\t\t\t\tconst m = (ms || []).find((z) => z.name === id) || {};
\t\t\t\t\tfrappe.call({ method: "duty_board.client_room.project_milestone_task_options", args: { id: id }, callback: (r) => {
\t\t\t\t\t\tconst opts = r.message || [];
\t\t\t\t\t\tconst pd = new frappe.ui.Dialog({ title: `📋 ${frappe.utils.escape_html(m.title || "")} — ${__("tasks in this phase")}` });
\t\t\t\t\t\t$(pd.body).html(opts.length
\t\t\t\t\t\t\t? opts.map((o) => `<label style="display:flex;gap:8px;align-items:baseline;padding:5px 2px;border-bottom:1px dashed var(--border-color);font-size:var(--text-sm)"><input type="checkbox" value="${o.name}" ${o.checked ? "checked" : ""}><b>${frappe.utils.escape_html(o.title)}</b><span class="text-muted">${frappe.utils.escape_html(o.column)}</span>${o.elsewhere ? `<span class="duty-lead-chip">${__("in another phase")}</span>` : ""}</label>`).join("")
\t\t\t\t\t\t\t\t+ `<p class="text-muted duty-attach-hint">${__("Ticked tasks belong to this phase; on the client's plan their title and status become visible under it.")}</p><button type="button" class="btn btn-sm btn-primary duty-pt-save">${__("Save")}</button>`
\t\t\t\t\t\t\t: `<div class="text-muted">${__("This project has no tasks yet. Add tasks on the Board, then attach them here.")}</div>`);
\t\t\t\t\t\t$(pd.body).find(".duty-pt-save").on("click", () => {
\t\t\t\t\t\t\tconst picked = $(pd.body).find("input:checked").map((i, el) => el.value).get();
\t\t\t\t\t\t\tfrappe.call({ method: "duty_board.client_room.milestone_set_tasks", args: { id: id, tasks: JSON.stringify(picked) }, callback: () => { pd.hide(); frappe.show_alert({ message: __("Phase tasks updated."), indicator: "green" }); done(); } });
\t\t\t\t\t\t});
\t\t\t\t\t\tpd.show();
\t\t\t\t\t}});
\t\t\t\t\treturn;
\t\t\t\t}'''

# --- 5. JS: milestone name map on the board + chip on the card --------------
MAP_OLD = '''\trender_kanban(project, data) {
\t\tif (project !== this.current_project) return;'''
MAP_NEW = '''\trender_kanban(project, data) {
\t\tif (project !== this.current_project) return;
\t\tthis._ms_names = {};
\t\t(data.milestones || []).forEach((m) => { this._ms_names[m.name] = m.title; });'''

CHIP_OLD = '\t\t\t\t<div class="duty-kb-title">${frappe.utils.escape_html(t.title)}</div>'
CHIP_NEW = '''\t\t\t\t<div class="duty-kb-title">${frappe.utils.escape_html(t.title)}</div>
\t\t\t\t${t.milestone && this._ms_names && this._ms_names[t.milestone] ? `<div class="duty-kb-ms">🚩 ${frappe.utils.escape_html(this._ms_names[t.milestone])}</div>` : ""}'''

# --- 6. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-phase-add { margin-top: 10px; }'
CSS_NEW = '''\t\t\t.duty-phase-add { margin-top: 10px; }
\t\t\t.duty-phase-tasks { margin: 4px 0 2px 38px; display: flex; flex-direction: column; gap: 3px; }
\t\t\t.duty-phase-tasks.empty { color: var(--text-muted, #9aa4a0); font-size: 12px; font-style: italic; }
\t\t\t.duty-phase-task { display: flex; align-items: center; gap: 8px; font-size: 12.5px; }
\t\t\t.duty-pt-dot { width: 7px; height: 7px; border-radius: 50%; background: #C4CFC9; flex: none; }
\t\t\t.duty-pt-dot.done { background: #0E8A63; }
\t\t\t.duty-pt-title { flex: 1; min-width: 0; }
\t\t\t.duty-pt-st { color: var(--text-muted, #888); font-size: 11px; }
\t\t\t.duty-pt-who { color: #5f6d68; font-size: 11px; }
\t\t\t.duty-kb-ms { font-size: 10.5px; color: #0F5C55; margin-top: 2px; font-weight: 600; }'''

EDITS_PROJ = [
    ("board fetch +milestone", BOARD_OLD, BOARD_NEW),
    ("board task +milestone note", BOARD_T_OLD, BOARD_T_NEW),
]
EDITS_CR = [
    ("project task-options endpoint", EP_ANCHOR, EP_NEW),
]
EDITS_JS = [
    ("phase tasks action + sublist", ACTS_OLD, ACTS_NEW),
    ("tasks picker handler", HANDLER_OLD, HANDLER_NEW),
    ("board milestone map", MAP_OLD, MAP_NEW),
    ("card milestone chip", CHIP_OLD, CHIP_NEW),
    ("phase/card CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, CR, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def project_milestone_task_options(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.62.2"' not in files[INIT]:
        sys.exit("ABORT: not at v3.62.2.")

    problems = []
    for label, o, _ in EDITS_PROJ:
        if files[PROJ].count(o) != 1: problems.append(f"  [{files[PROJ].count(o)}] proj: {label}")
    for label, o, _ in EDITS_CR:
        if files[CR].count(o) != 1: problems.append(f"  [{files[CR].count(o)}] cr: {label}")
    for label, o, _ in EDITS_JS:
        if files[JS].count(o) != 1: problems.append(f"  [{files[JS].count(o)}] js: {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS_PROJ)+len(EDITS_CR)+len(EDITS_JS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = dict(files)
    for _l, o, n in EDITS_PROJ: out[PROJ] = out[PROJ].replace(o, n, 1)
    for _l, o, n in EDITS_CR: out[CR] = out[CR].replace(o, n, 1)
    for _l, o, n in EDITS_JS: out[JS] = out[JS].replace(o, n, 1)
    out[INIT] = out[INIT].replace('"3.62.2"', '"3.62.3"')

    for p in (PROJ, CR, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(out[p])
        print(f"  wrote {p}")
    print("wrote __init__.py -> 3.62.3")


if __name__ == "__main__":
    main()
