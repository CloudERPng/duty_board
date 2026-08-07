#!/usr/bin/env python3
"""Duty Board v3.61.4 — Stage 2: manage phases on the Projects face.

Stage 1 gave get_project_board a "milestones" array and project-first
seed/add endpoints. This adds the UI: a third view on the project detail
bar — ▦ Board · 📅 Calendar · 🚩 Phases — that renders and manages the
open project's phase journey, room-independent, per project.

The Phases view:
- empty project -> a "Seed the Xlevel method" control (plan picker),
  calling project_seed_milestones(project, plan_type).
- with phases -> an ordered list; each phase shows status, target date,
  task roll-up (n of m), and actions: ▲▼ reorder, ▶ start, ✅ request
  client sign-off, 🗑 delete. Plus an "add a phase" input.
- reorder/status/approve/delete reuse the existing id-based milestone
  endpoints (milestone_move / _set_status / _request_approval /
  _delete); add uses project_milestone_add.

This is the surface that RETIRES room-wide phase mixing for staff: each
project's phases are managed on that project, never blended by room.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.61.3.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. add the Phases toggle button ----------------------------------------
TOGGLE_OLD = '\t\t\t\t\t<a class="duty-pj-v ${this._pj_view === "cal" ? "on" : ""}" data-v="cal">📅 ${__("Calendar")}</a>'
TOGGLE_NEW = '''\t\t\t\t\t<a class="duty-pj-v ${this._pj_view === "cal" ? "on" : ""}" data-v="cal">📅 ${__("Calendar")}</a>
\t\t\t\t\t<a class="duty-pj-v ${this._pj_view === "phases" ? "on" : ""}" data-v="phases">🚩 ${__("Phases")}${(data.milestones || []).length ? ` <b>${data.milestones.length}</b>` : ""}</a>'''

# --- 2. the phases view-branch, right after the cal early-return -------------
BRANCH_OLD = '''\t\tif ((this._pj_view || "board") === "cal") {
\t\t\tthis.render_calendar(project, data, $wrap);
\t\t\treturn;
\t\t}'''
BRANCH_NEW = '''\t\tif ((this._pj_view || "board") === "cal") {
\t\t\tthis.render_calendar(project, data, $wrap);
\t\t\treturn;
\t\t}
\t\tif (this._pj_view === "phases") {
\t\t\tthis.render_phases(project, data, $wrap);
\t\t\treturn;
\t\t}'''

# --- 3. render_phases method, added before kb_card --------------------------
METHOD_OLD = '\tkb_card(t) {'
METHOD_NEW = '''\trender_phases(project, data, $wrap) {
\t\tconst ms = data.milestones || [];
\t\tconst esc = frappe.utils.escape_html;
\t\tconst $p = $(`<div class="duty-phases"></div>`).appendTo($wrap);

\t\tif (!ms.length) {
\t\t\t$p.html(`
\t\t\t\t<div class="duty-phases-empty">
\t\t\t\t\t<p class="text-muted">${__("No phases yet. Seed the Xlevel delivery method, or add phases one at a time below.")}</p>
\t\t\t\t\t<div class="duty-phase-seed">
\t\t\t\t\t\t<select class="form-control duty-seed-plan" style="max-width:280px;display:inline-block">
\t\t\t\t\t\t\t<option value="standard">${__("Standard plan (phases + starter tasks)")}</option>
\t\t\t\t\t\t\t<option value="">${__("Phases only (no tasks)")}</option>
\t\t\t\t\t\t</select>
\t\t\t\t\t\t<button class="btn btn-primary btn-sm duty-seed-go">🚩 ${__("Seed the Xlevel method")}</button>
\t\t\t\t\t</div>
\t\t\t\t</div>`);
\t\t\t$p.find(".duty-seed-go").on("click", () => {
\t\t\t\tconst plan = $p.find(".duty-seed-plan").val();
\t\t\t\tfrappe.call({
\t\t\t\t\tmethod: "duty_board.client_room.project_seed_milestones",
\t\t\t\t\targs: { project: project, plan_type: plan || null },
\t\t\t\t\tfreeze: true,
\t\t\t\t\tcallback: () => { frappe.show_alert({ message: __("Phases seeded."), indicator: "green" }); this.load_kanban(project); },
\t\t\t\t});
\t\t\t});
\t\t} else {
\t\t\tconst curIdx = ms.findIndex((m) => m.status !== "Approved");
\t\t\tconst rows = ms.map((m, i) => {
\t\t\t\tconst st = m.status === "Approved" ? "done" : i === curIdx ? "active" : "up";
\t\t\t\tconst locked = m.status === "Approved";
\t\t\t\treturn `
\t\t\t\t<div class="duty-phase-row duty-phase-${st}" data-id="${esc(m.name)}">
\t\t\t\t\t<span class="duty-phase-ix">${st === "done" ? "✓" : i + 1}</span>
\t\t\t\t\t<div class="duty-phase-main">
\t\t\t\t\t\t<div class="duty-phase-title">${esc(m.title)}${m.status === "Awaiting Approval" ? ` <span class="duty-phase-wait">⏳ ${__("awaiting client")}</span>` : ""}</div>
\t\t\t\t\t\t<div class="duty-phase-meta">${esc(m.status)}${m.target_date ? ` · 🎯 ${esc(m.target_date)}` : ""} · ${m.cards_done || 0}/${m.cards_total || 0} ${__("tasks")}</div>
\t\t\t\t\t</div>
\t\t\t\t\t<div class="duty-phase-acts">
\t\t\t\t\t\t<a data-a="up" title="${__("Move up")}">▲</a>
\t\t\t\t\t\t<a data-a="down" title="${__("Move down")}">▼</a>
\t\t\t\t\t\t${st === "active" && m.status !== "In Progress" ? `<a data-a="start" title="${__("Mark in progress")}">▶</a>` : ""}
\t\t\t\t\t\t${!locked && m.status !== "Awaiting Approval" ? `<a data-a="ask" title="${__("Request client sign-off")}">✅</a>` : ""}
\t\t\t\t\t\t${!locked ? `<a data-a="del" title="${__("Delete phase")}">🗑</a>` : ""}
\t\t\t\t\t</div>
\t\t\t\t</div>`;
\t\t\t}).join("");
\t\t\t$p.html(`
\t\t\t\t<div class="duty-phase-list">${rows}</div>
\t\t\t\t<div class="duty-phase-add">
\t\t\t\t\t<input type="text" class="form-control input-sm duty-newphase" placeholder="${__("Add a phase title and press Enter…")}" style="max-width:340px;display:inline-block">
\t\t\t\t</div>`);
\t\t\t$p.find(".duty-phase-acts a").on("click", (e) => {
\t\t\t\tconst a = $(e.currentTarget).data("a");
\t\t\t\tconst id = $(e.currentTarget).closest(".duty-phase-row").data("id");
\t\t\t\tconst done = () => this.load_kanban(project);
\t\t\t\tif (a === "up" || a === "down") return frappe.call({ method: "duty_board.client_room.milestone_move", args: { id: id, direction: a }, callback: done });
\t\t\t\tif (a === "start") return frappe.call({ method: "duty_board.client_room.milestone_set_status", args: { id: id, status: "In Progress" }, callback: done });
\t\t\t\tif (a === "ask") return frappe.confirm(__("Tell the client this phase is complete and request their formal sign-off?"), () => frappe.call({ method: "duty_board.client_room.milestone_request_approval", args: { id: id }, callback: done }));
\t\t\t\tif (a === "del") return frappe.confirm(__("Delete this phase? Its tasks are kept but unlinked."), () => frappe.call({ method: "duty_board.client_room.milestone_delete", args: { id: id }, callback: done }));
\t\t\t});
\t\t\t$p.find(".duty-newphase").on("keydown", (e) => {
\t\t\t\tif (e.key !== "Enter") return;
\t\t\t\tconst t = e.target.value.trim();
\t\t\t\tif (!t) return;
\t\t\t\te.target.value = "";
\t\t\t\tfrappe.call({
\t\t\t\t\tmethod: "duty_board.client_room.project_milestone_add",
\t\t\t\t\targs: { project: project, title: t },
\t\t\t\t\tcallback: () => this.load_kanban(project),
\t\t\t\t});
\t\t\t});
\t\t}
\t}

\tkb_card(t) {'''

# --- 4. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-paused-dismiss:hover { opacity: 1; }'
CSS_NEW = '''\t\t\t.duty-paused-dismiss:hover { opacity: 1; }
\t\t\t.duty-phases { padding: 12px 4px; max-width: 720px; }
\t\t\t.duty-phases-empty { text-align: center; padding: 24px; }
\t\t\t.duty-phase-seed { display: flex; gap: 10px; justify-content: center; align-items: center; flex-wrap: wrap; }
\t\t\t.duty-phase-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid var(--border-color, #e6e6e6); border-radius: 10px; margin-bottom: 8px; background: #fff; }
\t\t\t.duty-phase-active { border-color: #0F5C55; box-shadow: 0 0 0 1px #0F5C55 inset; }
\t\t\t.duty-phase-done { opacity: .7; }
\t\t\t.duty-phase-ix { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; background: #EEF4F3; color: #0F5C55; flex: none; }
\t\t\t.duty-phase-done .duty-phase-ix { background: #0E8A63; color: #fff; }
\t\t\t.duty-phase-main { flex: 1; min-width: 0; }
\t\t\t.duty-phase-title { font-weight: 700; }
\t\t\t.duty-phase-meta { font-size: 12px; color: var(--text-muted, #888); }
\t\t\t.duty-phase-wait { color: #B45309; font-size: 11px; font-weight: 700; }
\t\t\t.duty-phase-acts { display: flex; gap: 8px; }
\t\t\t.duty-phase-acts a { cursor: pointer; opacity: .65; text-decoration: none; }
\t\t\t.duty-phase-acts a:hover { opacity: 1; }
\t\t\t.duty-phase-add { margin-top: 10px; }'''

EDITS = [
    ("phases toggle button", TOGGLE_OLD, TOGGLE_NEW),
    ("phases view-branch", BRANCH_OLD, BRANCH_NEW),
    ("render_phases method", METHOD_OLD, METHOD_NEW),
    ("phases CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "render_phases(project, data, $wrap)" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.3"' not in init:
        sys.exit("ABORT: not at v3.61.3.")

    problems = [f"  [{js.count(o)}] {label}" for label, o, _ in EDITS if js.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for label, old, new in EDITS:
        js = js.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.61.3"', '"3.61.4"'))
    print("wrote __init__.py -> 3.61.4")


if __name__ == "__main__":
    main()
