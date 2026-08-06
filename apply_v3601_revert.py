#!/usr/bin/env python3
"""Duty Board v3.60.1 — revert the v3.60.0 presentation (selector replaces it).

Per decision, the chips-and-filter approach is being replaced by a
single project selector at the top of the client's project view. This
patch removes the v3.60.0 PRESENTATION and KEEPS the v3.60.0 BACKEND
(project/project_name in the task, milestone and CR payloads, and the CR
project link) — the selector in v3.60.2 consumes exactly those fields.

Reverted:
- staff room task column: project chip on rows + the filter bar + its
  click binding
- client portal: per-project stacked phase strips (back to the single
  strip), the task-table project chip, the _multiproj flag
- the project-chip / filter-bar / strip CSS on both surfaces

Kept (backend, feeds the selector):
- _project_names(), project/project_name in _work_rows / _visible_tasks
  / _milestone_rows / _chreq_rows
- Duty Change Request.project + chreq_add/chreq_update project args

JS only apart from leaving the doctype field in place: bench build --app
duty_board && bench restart. (No migrate — the CR field stays.)

Anchored, all-or-nothing, idempotent. Requires v3.60.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# Each pair is (current v3.60.0 text) -> (original v3.59.7 text). These are the
# exact inverses of the v3.60.0 JS/portal presentation edits.

# staff task row chip -> plain title
J2_NOW = '\t\t\t\t\t\t<span class="duty-crt-title">${t.kind === "issue" ? "⚠ " : "📁 "}${t.client_requested ? "🙋 " : ""}${frappe.utils.escape_html(t.title)}${t.project_name && this._cr_multiproj ? `<span class="duty-projchip">${frappe.utils.escape_html(t.project_name)}</span>` : ""}</span>'
J2_ORIG = '\t\t\t\t\t\t<span class="duty-crt-title">${t.kind === "issue" ? "⚠ " : "📁 "}${t.client_requested ? "🙋 " : ""}${frappe.utils.escape_html(t.title)}</span>'

# staff filter-bar block -> plain tasks open
J3_NOW = '''\t\t\t<div class="duty-cr-tasks">
\t\t\t\t${(() => {
\t\t\t\t\tconst names = [...new Set((x.tasks || []).map((t) => t.project_name).filter(Boolean))];
\t\t\t\t\tthis._cr_multiproj = names.length > 1;
\t\t\t\t\tif (!this._cr_multiproj) return "";
\t\t\t\t\tconst pf = this._cr_pfilter || "";
\t\t\t\t\treturn `<div class="duty-projbar"><a data-pf="" class="${!pf ? "on" : ""}">${__("All")}</a>${names
\t\t\t\t\t\t.map((n) => `<a data-pf="${frappe.utils.escape_html(n)}" class="${pf === n ? "on" : ""}">${frappe.utils.escape_html(n)}</a>`)
\t\t\t\t\t\t.join("")}<a data-pf="__none__" class="${pf === "__none__" ? "on" : ""}">${__("General")}</a></div>`;
\t\t\t\t})()}
\t\t\t\t${(x.tasks || [])
\t\t\t\t\t.filter((t) => !this._cr_pfilter || (this._cr_pfilter === "__none__" ? !t.project_name : t.project_name === this._cr_pfilter))
\t\t\t\t\t.filter((t) => !this._cr_tfilter || t.status === this._cr_tfilter)'''
J3_ORIG = '''\t\t\t<div class="duty-cr-tasks">
\t\t\t\t${(x.tasks || [])
\t\t\t\t\t.filter((t) => !this._cr_tfilter || t.status === this._cr_tfilter)'''

# staff filter-bar click binding -> gone
J4_NOW = '''\t\t$room.find(".duty-projbar a").on("click", (e) => {
\t\t\tthis._cr_pfilter = $(e.currentTarget).attr("data-pf") || "";
\t\t\tthis.render_client_room(x);
\t\t});
\t\t$room.find(".duty-cr-task").on("click", (e) => {
\t\t\tconst $t = $(e.currentTarget);
\t\t\tif ($t.data("kind") === "issue") {'''
J4_ORIG = '''\t\t$room.find(".duty-cr-task").on("click", (e) => {
\t\t\tconst $t = $(e.currentTarget);
\t\t\tif ($t.data("kind") === "issue") {'''

# staff CSS -> gone
J1_NOW = '''\t\t\t.duty-ch-munit { background: var(--bg-light-gray, #eef2f1); color: #0f766e; border: 1px solid #d5e5e2; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 16px; white-space: nowrap; }
\t\t\t.duty-projchip { display: inline-block; background: #EEF4F3; color: #0F5C55; border: 1px solid #D2E4E0; border-radius: 7px; padding: 0 6px; font-size: 10px; font-weight: 700; margin-left: 6px; vertical-align: middle; }
\t\t\t.duty-projbar { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 8px; }
\t\t\t.duty-projbar a { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 8px; border: 1px solid var(--border-color, #e0e0e0); color: var(--text-muted, #666); cursor: pointer; text-decoration: none; }
\t\t\t.duty-projbar a.on { background: #0F5C55; border-color: #0F5C55; color: #fff; }'''
J1_ORIG = '\t\t\t.duty-ch-munit { background: var(--bg-light-gray, #eef2f1); color: #0f766e; border: 1px solid #d5e5e2; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 16px; white-space: nowrap; }'

# portal task chip -> plain
P1_NOW = '<td class="tt-title">${x.seen ? "<span class=\'dotc\' style=\'background:#087A67\'></span> " : ""}${esc(x.title)}${x.project_name && window._multiproj ? `<span class="pchip">${esc(x.project_name)}</span>` : ""}</td>'
P1_ORIG = '<td class="tt-title">${x.seen ? "<span class=\'dotc\' style=\'background:#087A67\'></span> " : ""}${esc(x.title)}</td>'

# portal _multiproj flag -> gone
P2_NOW = '''\twindow._multiproj = [...new Set((d.tasks || []).map((x) => x.project_name).filter(Boolean))].length > 1;
\tconst rows = (d.tasks || []).filter((x) => !filt || x.status === filt);'''
P2_ORIG = '\tconst rows = (d.tasks || []).filter((x) => !filt || x.status === filt);'

# portal per-project strips -> single strip
P3_NOW = '''\tconst _projs = [...new Set(rows.map((m) => m.project_name).filter(Boolean))];
\tif (rows.length && _projs.length > 1) {
\t\t// Multiple projects: one phase strip per project, stacked.
\t\twrap.style.display = "block";
\t\twrap.innerHTML = _projs.map((pn) => {
\t\t\tconst pr = rows.filter((m) => m.project_name === pn);
\t\t\tconst pdone = pr.filter((m) => m.status === "Approved").length;
\t\t\tconst pcur = pr.findIndex((m) => m.status !== "Approved");
\t\t\treturn `<div class="pjstrip"><div class="pjstriphd">${esc(pn)}</div><div class="msstep">${pr.map((m, i) => {
\t\t\t\tconst st = m.status === "Approved" ? "d" : i === pcur ? "a" : "u";
\t\t\t\treturn `<div class="mss ${st}"><span class="mssd">${st === "d" ? "✓" : i + 1}</span><span class="mssl">${esc(m.title)}</span>${st === "a" ? `<span class="msshere">You are here${m.target_date ? ` · 🎯 ${esc(m.target_date)}` : ""}</span>` : ""}</div>`;
\t\t\t}).join('<span class="mssline"></span>')}</div><div class="pjbar"><i style="width:${Math.round((pdone / pr.length) * 100)}%"></i></div><div class="muted" style="font-size:12px">${pcur >= 0 ? `${esc(pr[pcur].title)} in progress · ${pdone} of ${pr.length} phases` : `All ${pr.length} phases signed off 🎉`}</div></div>`;
\t\t}).join("");
\t\tconst sumEl0 = document.getElementById("pjsum"); if (sumEl0) sumEl0.remove();
\t} else if (rows.length) {
\t\twrap.style.display = "block";
\t\tconst cur = rows.findIndex((m) => m.status !== "Approved");
\t\twrap.innerHTML = `<div id="msstep">${rows.map((m, i) => {'''
P3_ORIG = '''\tif (rows.length) {
\t\twrap.style.display = "block";
\t\tconst cur = rows.findIndex((m) => m.status !== "Approved");
\t\twrap.innerHTML = `<div id="msstep">${rows.map((m, i) => {'''

# portal CSS -> original single #msstep rule
PC_NOW = '''\t#msstep, .msstep { display: flex; align-items: flex-start; overflow-x: auto; padding: 4px 0 10px; -webkit-overflow-scrolling: touch; }
\t.pchip { display: inline-block; background: #EEF4F3; color: #0F5C55; border: 1px solid #D2E4E0; border-radius: 7px; padding: 0 6px; font-size: 10px; font-weight: 700; margin-left: 7px; vertical-align: middle; }
\t.pjstrip { padding: 8px 0 4px; border-top: 1px solid #EEF2F0; }
\t.pjstrip:first-child { border-top: 0; }
\t.pjstriphd { font-size: 12px; font-weight: 800; color: #0F5C55; margin: 0 0 2px; }
\t.pjbar { height: 5px; background: #E7EDEA; border-radius: 99px; overflow: hidden; margin: 2px 0 4px; }
\t.pjbar i { display: block; height: 100%; background: #0E8A63; border-radius: 99px; }'''
PC_ORIG = '\t#msstep { display: flex; align-items: flex-start; overflow-x: auto; padding: 4px 0 10px; -webkit-overflow-scrolling: touch; }'

JS_EDITS = [
    ("staff CSS removed", J1_NOW, J1_ORIG),
    ("staff task chip removed", J2_NOW, J2_ORIG),
    ("staff filter bar removed", J3_NOW, J3_ORIG),
    ("staff filter binding removed", J4_NOW, J4_ORIG),
]
PORTAL_EDITS = [
    ("portal _multiproj removed", P2_NOW, P2_ORIG),
    ("portal task chip removed", P1_NOW, P1_ORIG),
    ("portal per-project strips reverted", P3_NOW, P3_ORIG),
    ("portal CSS reverted", PC_NOW, PC_ORIG),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, PORTAL, JS):
        fp = os.path.join(root, p)
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "duty-projbar" not in files[JS]:
        print("Already reverted (or v3.60.0 presentation not present). Nothing to do.")
        return
    if '"3.60.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.60.0.")

    problems = []
    for label, now, _o in JS_EDITS:
        if files[JS].count(now) != 1:
            problems.append(f"  [{files[JS].count(now)}] JS: {label}")
    for label, now, _o in PORTAL_EDITS:
        if files[PORTAL].count(now) != 1:
            problems.append(f"  [{files[PORTAL].count(now)}] portal: {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(JS_EDITS)+len(PORTAL_EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = dict(files)
    for label, now, orig in JS_EDITS:
        out[JS] = out[JS].replace(now, orig, 1)
    for label, now, orig in PORTAL_EDITS:
        out[PORTAL] = out[PORTAL].replace(now, orig, 1)
    out[INIT] = out[INIT].replace('"3.60.0"', '"3.60.1"')

    for p in (JS, PORTAL, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(out[p])
        print(f"  reverted {p}")
    print("wrote __init__.py -> 3.60.1")


if __name__ == "__main__":
    main()
