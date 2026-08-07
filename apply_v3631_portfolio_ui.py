#!/usr/bin/env python3
"""Duty Board v3.63.1 — portfolio rollup UI on the Projects face.

Backend (v3.63.0) enriched get_projects with phase + slip. This adds the
screen: a 📊 Portfolio button in the Projects side rail that renders a
one-row-per-project health grid into the main pane — Project · Phase ·
Progress · Slip · Overdue · Status — sorted so at-risk projects float to
the top. Click a row to open that project.

This is the "open it every morning" screen for running projects in
parallel: which is behind, which needs attention, all at once.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.63.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. add the Portfolio button to the side head ---------------------------
HEAD_OLD = '''\t\t\t\t\t\t<input type="text" class="form-control input-sm duty-pj-filter" placeholder="${__("Filter projects…")}">
\t\t\t\t\t\t<button class="btn btn-sm btn-default duty-proj-new" title="${__("New Project")}">＋</button>'''
HEAD_NEW = '''\t\t\t\t\t\t<input type="text" class="form-control input-sm duty-pj-filter" placeholder="${__("Filter projects…")}">
\t\t\t\t\t\t<button class="btn btn-sm btn-default duty-proj-portfolio" title="${__("Portfolio — all projects at a glance")}">📊</button>
\t\t\t\t\t\t<button class="btn btn-sm btn-default duty-proj-new" title="${__("New Project")}">＋</button>'''

# --- 2. wire the button (next to the new-project handler) -------------------
WIRE_OLD = '\t\tthis.$projects.find(".duty-proj-new").on("click", () => this.new_project_dialog());'
WIRE_NEW = '''\t\tthis.$projects.find(".duty-proj-new").on("click", () => this.new_project_dialog());
\t\tthis.$projects.find(".duty-proj-portfolio").on("click", () => this.render_portfolio());'''

# --- 3. the render_portfolio method (added before refresh_projects) ---------
METHOD_OLD = '\trefresh_projects(silent) {'
METHOD_NEW = '''\trender_portfolio() {
\t\tthis.current_project = null;
\t\tif (this.is_mobile()) this.$projects.addClass("pj-detail");
\t\tconst $wrap = this.$projects.find(".duty-kanban-wrap").empty();
\t\tconst esc = frappe.utils.escape_html;
\t\tconst ps = (this._projects || []).slice().sort((a, b) => (b.at_risk || 0) - (a.at_risk || 0) || (b.overdue || 0) - (a.overdue || 0) || (b.worst_slip || 0) - (a.worst_slip || 0));
\t\tif (!ps.length) { $wrap.html(`<div class="text-muted duty-plan-empty">${__("No active projects.")}</div>`); return; }
\t\tconst atRisk = ps.filter((p) => p.at_risk).length;
\t\tconst rows = ps.map((p) => {
\t\t\tconst pc = this.proj_color(p.name);
\t\t\tconst slip = p.worst_slip != null && p.worst_slip > 0 ? `<span class="duty-pf-slip late">+${p.worst_slip}d</span>` : (p.phases_total ? `<span class="duty-pf-slip ok">on plan</span>` : `<span class="text-muted">—</span>`);
\t\t\tconst phase = p.phase_current ? esc(p.phase_current) : `<span class="text-muted">${__("no phases")}</span>`;
\t\t\tconst due = p.days_left == null ? `<span class="text-muted">—</span>` : p.days_left < 0 ? `<span class="duty-pf-slip late">${Math.abs(p.days_left)}d over</span>` : `${p.days_left}d left`;
\t\t\treturn `
\t\t\t\t<tr class="duty-pf-row" data-name="${p.name}">
\t\t\t\t\t<td><span class="duty-pf-dot" style="background:${pc}"></span><b>${esc(p.project_name)}</b><div class="duty-pf-cust">${esc(p.customer || "")}</div></td>
\t\t\t\t\t<td>🚩 ${phase}${p.phases_total ? ` <span class="text-muted">${p.phases_done}/${p.phases_total}</span>` : ""}</td>
\t\t\t\t\t<td><div class="duty-pf-bar"><span style="width:${p.pct || 0}%;background:${pc}"></span></div><span class="duty-pf-pct">${p.pct || 0}%</span></td>
\t\t\t\t\t<td>${slip}</td>
\t\t\t\t\t<td>${p.overdue ? `<span class="duty-proj-over">⚠ ${p.overdue}</span>` : `<span class="text-muted">0</span>`}</td>
\t\t\t\t\t<td>${due}</td>
\t\t\t\t\t<td>${p.at_risk ? `<span class="duty-pf-badge risk">At risk</span>` : `<span class="duty-pf-badge ok">On track</span>`}</td>
\t\t\t\t</tr>`;
\t\t}).join("");
\t\t$wrap.html(`
\t\t\t<div class="duty-pf">
\t\t\t\t<div class="duty-pf-head"><b>📊 ${__("Portfolio")}</b><span class="text-muted">${ps.length} ${__("active")}${atRisk ? ` · <b class="duty-proj-over">${atRisk} ${__("at risk")}</b>` : ""}</span></div>
\t\t\t\t<table class="duty-pf-table">
\t\t\t\t\t<thead><tr><th>${__("Project")}</th><th>${__("Phase")}</th><th>${__("Progress")}</th><th>${__("Slip")}</th><th>${__("Overdue")}</th><th>${__("Target")}</th><th>${__("Status")}</th></tr></thead>
\t\t\t\t\t<tbody>${rows}</tbody>
\t\t\t\t</table>
\t\t\t</div>`);
\t\t$wrap.find(".duty-pf-row").on("click", (e) => {
\t\t\tconst name = $(e.currentTarget).data("name");
\t\t\tthis.current_project = name;
\t\t\tlocalStorage.setItem("duty_proj", name);
\t\t\tthis.render_project_tabs();
\t\t\tthis.load_kanban(name);
\t\t});
\t}

\trefresh_projects(silent) {'''

# --- 4. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-proj-head { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 12px; }'
CSS_NEW = '''\t\t\t.duty-proj-head { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 12px; }
\t\t\t.duty-pf { max-width: 1100px; }
\t\t\t.duty-pf-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; font-size: 16px; }
\t\t\t.duty-pf-table { width: 100%; border-collapse: collapse; font-size: 13px; }
\t\t\t.duty-pf-table th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .03em; color: #8a958f; padding: 6px 10px; border-bottom: 2px solid #E4EAE8; }
\t\t\t.duty-pf-table td { padding: 10px; border-bottom: 1px solid #EEF2F1; vertical-align: middle; }
\t\t\t.duty-pf-row { cursor: pointer; }
\t\t\t.duty-pf-row:hover { background: #F4F7F6; }
\t\t\t.duty-pf-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 7px; }
\t\t\t.duty-pf-cust { font-size: 11px; color: #8a958f; margin-left: 16px; }
\t\t\t.duty-pf-bar { display: inline-block; width: 90px; height: 7px; border-radius: 4px; background: #EEF2F1; overflow: hidden; vertical-align: middle; }
\t\t\t.duty-pf-bar span { display: block; height: 100%; }
\t\t\t.duty-pf-pct { font-size: 11px; color: #65736F; margin-left: 6px; }
\t\t\t.duty-pf-slip.late { color: #C2410C; font-weight: 700; }
\t\t\t.duty-pf-slip.ok { color: #0E8A63; }
\t\t\t.duty-pf-badge { font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 20px; }
\t\t\t.duty-pf-badge.risk { background: #FEF0E6; color: #C2410C; }
\t\t\t.duty-pf-badge.ok { background: #E7F5EF; color: #0E8A63; }'''

EDITS = [
    ("portfolio button", HEAD_OLD, HEAD_NEW),
    ("portfolio wire", WIRE_OLD, WIRE_NEW),
    ("render_portfolio method", METHOD_OLD, METHOD_NEW),
    ("portfolio CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "render_portfolio()" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.63.0"' not in init:
        sys.exit("ABORT: not at v3.63.0.")

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
        f.write(init.replace('"3.63.0"', '"3.63.1"'))
    print("wrote __init__.py -> 3.63.1")


if __name__ == "__main__":
    main()
