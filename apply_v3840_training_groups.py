#!/usr/bin/env python3
"""Duty Board v3.84.0 — structured My-training (screenshot-reported).

With multiple streams assigned, the list interleaved ZhiftCRM, Selling,
and Bookkeeper modules — because it sorted by sort_order ALONE across
products (Selling's 10-17 zips perfectly into ZhiftCRM's 10-14).

Fix:
- Backend: rows sort by (product, sort_order, title) and carry
  sort_order.
- UI: the list renders as STREAM SECTIONS — a header per product with
  its certified count ("ZhiftERP — 0/8 certified"), modules in course
  order beneath, indented; the per-row product suffix goes (the header
  says it now).

Backend + JS. bench build --app duty_board && bench restart (no
migrate). Anchored, idempotent. Requires v3.83.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CR = "duty_board/client_room.py"
CHECK_ONLY = "--check" in sys.argv

B_OLD = '''\t\tr.lessons_done = done_counts.get(r.module, 0)
\trows.sort(key=lambda r: (mods[r.module].sort_order or 999) if r.module in mods else 999)
\treturn rows'''
B_NEW = '''\t\tr.lessons_done = done_counts.get(r.module, 0)
\t\tr.sort_order = (m.sort_order or 999) if m else 999
\trows.sort(key=lambda r: (r.product or "~", r.sort_order, r.module_title))
\treturn rows'''

J_OLD = '''\t\t\t${rows.length
\t\t\t\t? rows
\t\t\t\t\t\t.map(
\t\t\t\t\t\t\t(r) => `
\t\t\t\t<div class="duty-cr-msrow" style="cursor:pointer" data-record="${r.name}">
\t\t\t\t\t<span>${r.status === "Completed" ? "🏅" : "📖"} <b>${frappe.utils.escape_html(r.module_title)}</b>${r.product ? ` <span class="text-muted">· ${frappe.utils.escape_html(r.product)}</span>` : ""}</span>
\t\t\t\t\t<span class="text-muted" style="font-size:var(--text-sm)">
\t\t\t\t\t\t${r.status === "Completed"
\t\t\t\t\t\t\t? `✓ ${__("certified")} ${r.completed_on || ""}`
\t\t\t\t\t\t\t: `📚 ${r.lessons_done}/${r.lessons_total} ${__("lessons")}${r.lessons_total && r.lessons_done === r.lessons_total ? " · ✓ " + __("all read") : ""}`}
\t\t\t\t\t</span>
\t\t\t\t</div>`
\t\t\t\t\t\t)
\t\t\t\t\t\t.join("")
\t\t\t\t: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No training assigned to you yet.")}</div>`}'''
J_NEW = '''\t\t\t${rows.length
\t\t\t\t? (() => {
\t\t\t\t\t\tconst esc = frappe.utils.escape_html;
\t\t\t\t\t\tlet out = "", last = null;
\t\t\t\t\t\trows.forEach((r) => {
\t\t\t\t\t\t\tconst g = r.product || __("General");
\t\t\t\t\t\t\tif (g !== last) {
\t\t\t\t\t\t\t\tconst gr = rows.filter((x) => (x.product || __("General")) === g);
\t\t\t\t\t\t\t\tconst cert = gr.filter((x) => x.status === "Completed").length;
\t\t\t\t\t\t\t\tout += `<div class="duty-tr-group"><b>${esc(g)}</b><span class="${cert === gr.length ? "duty-tr-done" : ""}">${cert}/${gr.length} ${__("certified")}</span></div>`;
\t\t\t\t\t\t\t\tlast = g;
\t\t\t\t\t\t\t}
\t\t\t\t\t\t\tout += `
\t\t\t\t<div class="duty-cr-msrow duty-tr-row" style="cursor:pointer" data-record="${r.name}">
\t\t\t\t\t<span>${r.status === "Completed" ? "🏅" : "📖"} <b>${esc(r.module_title)}</b></span>
\t\t\t\t\t<span class="text-muted" style="font-size:var(--text-sm)">
\t\t\t\t\t\t${r.status === "Completed"
\t\t\t\t\t\t\t? `✓ ${__("certified")} ${r.completed_on || ""}`
\t\t\t\t\t\t\t: `📚 ${r.lessons_done}/${r.lessons_total} ${__("lessons")}${r.lessons_total && r.lessons_done === r.lessons_total ? " · ✓ " + __("all read") : ""}`}
\t\t\t\t\t</span>
\t\t\t\t</div>`;
\t\t\t\t\t\t});
\t\t\t\t\t\treturn out;
\t\t\t\t  })()
\t\t\t\t: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No training assigned to you yet.")}</div>`}'''

CSS_OLD = '\t\t\t.duty-slot-grid button { min-width: 64px; }'
CSS_NEW = '''\t\t\t.duty-slot-grid button { min-width: 64px; }
\t\t\t.duty-tr-group { display: flex; align-items: baseline; gap: 10px; margin: 14px 0 4px; padding-bottom: 4px; border-bottom: 2px solid #E4EAE8; }
\t\t\t.duty-tr-group b { font-size: 13px; text-transform: uppercase; letter-spacing: .04em; color: #0F5C55; }
\t\t\t.duty-tr-group span { font-size: 11.5px; font-weight: 700; color: #8a958f; }
\t\t\t.duty-tr-group span.duty-tr-done { color: #0E8A63; }
\t\t\t.duty-tr-row { padding-left: 10px; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "duty-tr-group" in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.83.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.83.0.")

    checks = [(CR, B_OLD, "backend sort", 1), (JS, J_OLD, "render block", 1), (JS, CSS_OLD, "css", 1)]
    problems = [f"  [{files[f].count(o)} != {n}] {label}" for f, o, label, n in checks if files[f].count(o) != n]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    files[CR] = files[CR].replace(B_OLD, B_NEW, 1)
    files[JS] = files[JS].replace(J_OLD, J_NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    files[INIT] = files[INIT].replace('"3.83.0"', '"3.84.0"')
    for p in (CR, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: (product, sort_order) sort · duty_board.js: stream sections")
    print("wrote __init__.py -> 3.84.0")


if __name__ == "__main__":
    main()
