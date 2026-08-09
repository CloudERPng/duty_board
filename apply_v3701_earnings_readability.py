#!/usr/bin/env python3
"""Duty Board v3.70.1 — earnings statement readability (review feedback).

Three fixes from the screenshot:
1. MONTH DEMARCATION: each month is now a bordered card with a tinted
   header band (label left, total right) — Aug vs Jul unmistakable.
2. ONE-LINE MATH: every component renders as a single equation row —
   label · calculation · amount — e.g. "⏱ Customer hours · 41.7h × ₦300
   = ₦12,504" (the actual rate, not the word "rate"), "⚡ SLA bonus ·
   2 × ₦150 = ₦300", ending in a TOTAL row showing the sum of the
   components that produced the month figure.
3. ITEM ROWS: each resolution/phase detail is a fixed grid line —
   title (ellipsised) · meta · amount right-aligned — no more wrapping
   into confusion.

Backend: _compute now returns rates {hourly, resolution, sla} and
sla_count so the equations can render real numbers.

earnings.py + JS. No schema. bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.70.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
EARN = "duty_board/earnings.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. earnings.py: expose rates + sla_count -------------------------------
PY_OLD = '''\treturn {
\t\t"year": year,
\t\t"month": month,
\t\t"label": f"{calendar.month_abbr[month]} {year}",
\t\t"hours": hours,'''
PY_NEW = '''\treturn {
\t\t"year": year,
\t\t"month": month,
\t\t"label": f"{calendar.month_abbr[month]} {year}",
\t\t"rates": {"hourly": round(hr_rate), "resolution": round(res_rate), "sla": round(st["sla"])},
\t\t"sla_count": sum(1 for r in resolutions if r["sla_amount"]),
\t\t"hours": hours,'''

# --- 2. JS: replace the block template with the equation layout -------------
BLK_OLD = '''\t\tconst block = (c, open) => `
\t\t\t<details ${open ? "open" : ""} class="duty-earn-m">
\t\t\t\t<summary><b>${esc(c.label)}</b><span class="duty-earn-grand">${naira(c.totals.grand)}</span></summary>
\t\t\t\t<div class="duty-earn-line">⏱ ${__("Customer hours")}: <b>${c.hours.paid_hours}h</b>${c.hours.capped ? ` <span class="duty-earn-cap">(${__("capped from")} ${c.hours.hours}h)</span>` : ""} × ${__("rate")} = <b>${naira(c.totals.hours)}</b> <span class="text-muted">· ${c.hours.linked_hours}h ${__("linked")} / ${c.hours.unlinked_hours}h ${__("unlinked")}</span></div>
\t\t\t\t${c.resolutions.length ? `<div class="duty-earn-line">✅ ${__("Resolutions")} (${c.resolutions.length}): <b>${naira(c.totals.resolutions)}</b>${c.totals.sla ? ` + ${__("SLA")} <b>${naira(c.totals.sla)}</b>` : ""}</div>
\t\t\t\t<div class="duty-earn-items">${c.resolutions.map((x) => `<div>${esc(x.title)} <span class="text-muted">· ${esc(x.customer || "")}${x.mode === "confirmed" ? (x.stars ? ` · ${"★".repeat(x.stars)}` : " · " + __("confirmed")) : " · " + __("auto (7d)")}${x.split > 1 ? ` · ÷${x.split}` : ""}</span><b style="margin-left:auto">${naira(x.amount + x.sla_amount)}</b></div>`).join("")}</div>` : ""}
\t\t\t\t${c.phases.length ? `<div class="duty-earn-line">🚩 ${__("Phase sign-offs on baseline")}: <b>${naira(c.totals.phases)}</b></div>
\t\t\t\t<div class="duty-earn-items">${c.phases.map((p) => `<div>${esc(p.phase)} <span class="text-muted">· ${esc(p.project)} · ${__("approved")} ${esc(p.approved)}${p.split > 1 ? ` · ÷${p.split}` : ""}</span><b style="margin-left:auto">${naira(p.amount)}</b></div>`).join("")}</div>` : ""}
\t\t\t</details>`;'''
BLK_NEW = '''\t\tconst block = (c, open) => {
\t\t\tconst eq = [];
\t\t\tif (c.totals.hours) eq.push(naira(c.totals.hours));
\t\t\tif (c.totals.resolutions) eq.push(naira(c.totals.resolutions));
\t\t\tif (c.totals.sla) eq.push(naira(c.totals.sla));
\t\t\tif (c.totals.phases) eq.push(naira(c.totals.phases));
\t\t\treturn `
\t\t\t<details ${open ? "open" : ""} class="duty-earn-m">
\t\t\t\t<summary><b>${esc(c.label)}</b><span class="duty-earn-grand">${naira(c.totals.grand)}</span></summary>
\t\t\t\t<div class="duty-earn-rows">
\t\t\t\t\t<div class="duty-earn-r"><span class="duty-earn-lbl">⏱ ${__("Customer hours")}</span><span class="duty-earn-calc"><b>${c.hours.paid_hours}h</b> × ${naira(c.rates.hourly)}${c.hours.capped ? ` <i class="duty-earn-cap">(${__("capped from")} ${c.hours.hours}h)</i>` : ""} <span class="text-muted">· ${c.hours.linked_hours}h ${__("linked")} / ${c.hours.unlinked_hours}h ${__("unlinked")}</span></span><b>${naira(c.totals.hours)}</b></div>
\t\t\t\t\t${c.resolutions.length ? `<div class="duty-earn-r"><span class="duty-earn-lbl">✅ ${__("Resolutions")}</span><span class="duty-earn-calc"><b>${c.resolutions.length}</b> × ${naira(c.rates.resolution)} ${__("base")} <span class="text-muted">· ${__("stars & splits applied per item below")}</span></span><b>${naira(c.totals.resolutions)}</b></div>` : ""}
\t\t\t\t\t${c.totals.sla ? `<div class="duty-earn-r"><span class="duty-earn-lbl">⚡ ${__("SLA bonus")}</span><span class="duty-earn-calc"><b>${c.sla_count}</b> × ${naira(c.rates.sla)}</span><b>${naira(c.totals.sla)}</b></div>` : ""}
\t\t\t\t\t${c.phases.length ? `<div class="duty-earn-r"><span class="duty-earn-lbl">🚩 ${__("Phase sign-offs")}</span><span class="duty-earn-calc"><b>${c.phases.length}</b> ${__("on baseline")}</span><b>${naira(c.totals.phases)}</b></div>` : ""}
\t\t\t\t\t<div class="duty-earn-r duty-earn-total"><span class="duty-earn-lbl">${__("Total")}</span><span class="duty-earn-calc">${eq.length > 1 ? eq.join(" + ") : ""}</span><b>${naira(c.totals.grand)}</b></div>
\t\t\t\t</div>
\t\t\t\t${c.resolutions.length ? `<div class="duty-earn-items">${c.resolutions.map((x) => `<div class="duty-earn-it"><span class="duty-earn-t" title="${esc(x.title)}">${esc(x.title)}</span><span class="duty-earn-meta">${esc(x.customer || "")} · ${x.mode === "confirmed" ? (x.stars ? "★".repeat(x.stars) : __("confirmed")) : __("auto (7d)")}${x.split > 1 ? ` · ÷${x.split}` : ""}</span><b>${naira(x.amount + x.sla_amount)}</b></div>`).join("")}</div>` : ""}
\t\t\t\t${c.phases.length ? `<div class="duty-earn-items">${c.phases.map((p) => `<div class="duty-earn-it"><span class="duty-earn-t" title="${esc(p.phase)}">${esc(p.phase)}</span><span class="duty-earn-meta">${esc(p.project)} · ${esc(p.approved)}${p.split > 1 ? ` · ÷${p.split}` : ""}</span><b>${naira(p.amount)}</b></div>`).join("")}</div>` : ""}
\t\t\t</details>`;
\t\t};'''

# --- 3. CSS: month bands + equation grid + item grid ------------------------
CSS_OLD = '''\t\t\t.duty-earn-m { border-bottom: 1px dashed var(--border-color, #eee); padding: 6px 0; }
\t\t\t.duty-earn-m:last-child { border-bottom: none; }
\t\t\t.duty-earn-m summary { cursor: pointer; display: flex; gap: 10px; align-items: baseline; list-style: none; }
\t\t\t.duty-earn-grand { margin-left: auto; font-weight: 800; color: #0E8A63; }
\t\t\t.duty-earn-line { font-size: 13px; margin: 6px 0 2px; }
\t\t\t.duty-earn-cap { color: #B45309; font-weight: 700; font-size: 12px; }
\t\t\t.duty-earn-items { margin: 2px 0 6px 18px; display: flex; flex-direction: column; gap: 2px; }
\t\t\t.duty-earn-items > div { display: flex; gap: 8px; align-items: baseline; font-size: 12.5px; }'''
CSS_NEW = '''\t\t\t.duty-earn-m { border: 1px solid #D8E2DF; border-radius: 12px; margin-bottom: 14px; overflow: hidden; background: #fff; }
\t\t\t.duty-earn-m summary { cursor: pointer; display: flex; gap: 10px; align-items: baseline; list-style: none; background: #EAF3F0; padding: 10px 14px; font-size: 15px; border-bottom: 1px solid #D8E2DF; }
\t\t\t.duty-earn-m summary::-webkit-details-marker { display: none; }
\t\t\t.duty-earn-grand { margin-left: auto; font-weight: 800; font-size: 16px; color: #0B6B4F; }
\t\t\t.duty-earn-rows { padding: 8px 14px 4px; }
\t\t\t.duty-earn-r { display: grid; grid-template-columns: 160px minmax(0,1fr) auto; gap: 12px; align-items: baseline; padding: 5px 0; font-size: 13px; }
\t\t\t.duty-earn-lbl { font-weight: 700; }
\t\t\t.duty-earn-r > b { text-align: right; }
\t\t\t.duty-earn-total { border-top: 2px solid #123C35; margin-top: 4px; padding-top: 8px; font-size: 14px; }
\t\t\t.duty-earn-total > b { color: #0B6B4F; font-size: 15px; }
\t\t\t.duty-earn-cap { color: #B45309; font-weight: 700; font-size: 12px; font-style: normal; }
\t\t\t.duty-earn-items { margin: 2px 14px 10px; padding-left: 8px; border-left: 3px solid #EAF3F0; display: flex; flex-direction: column; gap: 3px; }
\t\t\t.duty-earn-it { display: grid; grid-template-columns: minmax(0,1fr) auto auto; gap: 10px; align-items: baseline; font-size: 12.5px; }
\t\t\t.duty-earn-t { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
\t\t\t.duty-earn-meta { color: #7A8783; font-size: 11.5px; white-space: nowrap; }
\t\t\t.duty-earn-it > b { text-align: right; }
\t\t\t@media (max-width: 640px) { .duty-earn-r { grid-template-columns: 1fr auto; } .duty-earn-r .duty-earn-calc { grid-column: 1 / -1; } }'''

EDITS_PY = [("rates in payload", PY_OLD, PY_NEW)]
EDITS_JS = [("equation block", BLK_OLD, BLK_NEW), ("month band css", CSS_OLD, CSS_NEW)]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, EARN):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "duty-earn-rows" in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.70.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.70.0.")

    problems = []
    for label, o, _ in EDITS_PY:
        if files[EARN].count(o) != 1: problems.append(f"  [{files[EARN].count(o)}] py: {label}")
    for label, o, _ in EDITS_JS:
        if files[JS].count(o) != 1: problems.append(f"  [{files[JS].count(o)}] js: {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for _l, o, n in EDITS_PY: files[EARN] = files[EARN].replace(o, n, 1)
    for _l, o, n in EDITS_JS: files[JS] = files[JS].replace(o, n, 1)
    files[INIT] = files[INIT].replace('"3.70.0"', '"3.70.1"')

    for p in (EARN, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
        print(f"  wrote {p}")
    print("wrote __init__.py -> 3.70.1")


if __name__ == "__main__":
    main()
