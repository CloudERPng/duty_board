#!/usr/bin/env python3
"""Duty Board v3.61.7 — client task rows as a responsive column grid.

The task rows under each phase were free-flowing: priority and status
floated to wherever the title text ended, so nothing aligned between
rows and the eye couldn't scan a column. This rebuilds taskRow as an
aligned CSS grid — Task · Assignee · Due · Priority · Status — so
Critical/High reads as a vertical band, due dates line up, and status
sits in one place. Overdue dates get red emphasis; an "⏳ Awaiting you"
row stays for tasks needing client input (with the Respond button).

Responsive: the 5-column grid holds on desktop; at ≤640px it collapses
to a stacked card (label-less, each field on its own line) so phones
stay readable. Client/internal boundary respected — no hours, staleness,
or comment counts (those stay on the staff Kanban).

portal only. bench build --app duty_board && bench restart,
clear-website-cache. Anchored, idempotent. Requires v3.61.6.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

# --- the taskRow rebuild ----------------------------------------------------
ROW_OLD = '''\tconst taskRow = (t) => {
\t\tconst [ubg, ufg] = URG[t.urgency] || URG.Medium;
\t\treturn `
\t\t<div class="mst" style="flex-direction:column;align-items:stretch;gap:2px;border:1px solid ${t.awaiting_client && t.status !== "Done" ? "#f59e0b" : "#f3f4f6"};border-radius:8px;padding:7px 9px;margin:2px 0;background:${t.awaiting_client && t.status !== "Done" ? "#fffbeb" : "#fff"}">
\t\t\t<div style="display:flex;gap:8px;align-items:baseline">
\t\t\t\t<span class="dotc" style="background:${t.status === "Done" ? "#0E8A63" : t.status === "In Progress" ? "#2563EB" : "#C4CFC9"}"></span>
\t\t\t\t<b style="font-size:13px">${esc(t.title)}</b>
\t\t\t\t<span class="pill" style="background:${ubg};color:${ufg};margin-left:auto">${esc(t.urgency || "Medium")}</span>
\t\t\t\t<span class="pill ${PILL[t.status]}">${esc(t.status)}</span>
\t\t\t</div>
\t\t\t<div class="muted" style="font-size:12px;display:flex;gap:12px;flex-wrap:wrap">
\t\t\t\t${t.assignee ? `<span>👤 ${esc(t.assignee)}</span>` : `<span>👤 Unassigned</span>`}
\t\t\t\t${t.due_date ? `<span style="${t.overdue ? "color:#dc2626;font-weight:700" : ""}">📅 ${t.overdue ? "⚠ " : ""}${esc(t.due_date)}</span>` : ""}
\t\t\t</div>
\t\t\t${t.description ? `<div class="muted" style="font-size:12px;line-height:1.45">${esc(t.description)}</div>` : ""}
\t\t\t${t.awaiting_client && t.status !== "Done" ? `<div style="display:flex;gap:8px;align-items:center;margin-top:2px"><span class="pill pcta">⏳ Your input needed</span><button style="font-size:12px;padding:4px 12px" onclick="respondTask('${esc(t.title).replace(/'/g, "&#39;")}')">💬 Respond</button></div>` : ""}
\t\t</div>`;
\t};'''

ROW_NEW = '''\tconst taskRow = (t) => {
\t\tconst [ubg, ufg] = URG[t.urgency] || URG.Medium;
\t\tconst awaiting = t.awaiting_client && t.status !== "Done";
\t\tconst dotcol = t.status === "Done" ? "#0E8A63" : t.status === "In Progress" ? "#2563EB" : "#C4CFC9";
\t\treturn `
\t\t<div class="ctask${awaiting ? " ctask-await" : ""}">
\t\t\t<div class="ctask-main">
\t\t\t\t<span class="dotc" style="background:${dotcol}"></span>
\t\t\t\t<div class="ctask-tw">
\t\t\t\t\t<b>${esc(t.title)}</b>
\t\t\t\t\t${t.description ? `<div class="ctask-desc">${esc(t.description)}</div>` : ""}
\t\t\t\t</div>
\t\t\t</div>
\t\t\t<div class="ctask-who"><span class="ctask-lbl">Owner</span>${t.assignee ? esc(t.assignee) : "Unassigned"}</div>
\t\t\t<div class="ctask-due"><span class="ctask-lbl">Due</span>${t.due_date ? `<span class="${t.overdue ? "ctask-over" : ""}">${t.overdue ? "⚠ " : ""}${esc(t.due_date)}</span>` : "—"}</div>
\t\t\t<div class="ctask-pri"><span class="pill" style="background:${ubg};color:${ufg}">${esc(t.urgency || "Medium")}</span></div>
\t\t\t<div class="ctask-st"><span class="pill ${PILL[t.status]}">${esc(t.status)}</span></div>
\t\t\t${awaiting ? `<div class="ctask-cta"><span class="pill pcta">⏳ Your input needed</span><button onclick="respondTask('${esc(t.title).replace(/'/g, "&#39;")}')">💬 Respond</button></div>` : ""}
\t\t</div>`;
\t};'''

# --- CSS for the responsive grid --------------------------------------------
CSS_OLD = '.msfocus { font-size: 12px; font-weight: 800; color: #0F5C55; margin: 0 0 6px; }'
CSS_NEW = '''.msfocus { font-size: 12px; font-weight: 800; color: #0F5C55; margin: 0 0 6px; }
\t/* Client task rows — aligned column grid (desktop) -> stacked card (mobile) */
\t.ctask { display: grid; grid-template-columns: minmax(0,1fr) 130px 116px 92px 104px; column-gap: 12px; row-gap: 2px; align-items: start; border: 1px solid #f0f2f1; border-radius: 8px; padding: 9px 11px; margin: 3px 0; background: #fff; }
\t.ctask-await { border-color: #f59e0b; background: #fffbeb; }
\t.ctask-main { display: flex; gap: 8px; align-items: baseline; min-width: 0; }
\t.ctask-tw { min-width: 0; }
\t.ctask-tw b { font-size: 13px; }
\t.ctask-desc { font-size: 11.5px; line-height: 1.4; color: #7A8783; margin-top: 2px; }
\t.ctask-who, .ctask-due { font-size: 12px; color: #5f6d68; align-self: center; }
\t.ctask-pri, .ctask-st { align-self: center; }
\t.ctask-over { color: #dc2626; font-weight: 700; }
\t.ctask-lbl { display: none; }
\t.ctask-cta { grid-column: 1 / -1; display: flex; gap: 8px; align-items: center; margin-top: 4px; }
\t.ctask-cta button { font-size: 12px; padding: 4px 12px; }
\t@media (max-width: 640px) {
\t\t.ctask { grid-template-columns: 1fr; row-gap: 4px; }
\t\t.ctask-who, .ctask-due { display: flex; gap: 6px; }
\t\t.ctask-lbl { display: inline; font-weight: 700; color: #9aa4a0; min-width: 46px; }
\t\t.ctask-pri, .ctask-st { justify-self: start; }
\t}'''

EDITS = [
    ("taskRow -> column grid", ROW_OLD, ROW_NEW),
    ("task grid CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PORTAL), encoding="utf-8") as f:
        html = f.read()

    if 'class="ctask' in html:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.6"' not in init:
        sys.exit("ABORT: not at v3.61.6.")

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
        f.write(init.replace('"3.61.6"', '"3.61.7"'))
    print("wrote __init__.py -> 3.61.7")


if __name__ == "__main__":
    main()
