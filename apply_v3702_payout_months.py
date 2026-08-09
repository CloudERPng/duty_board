#!/usr/bin/env python3
"""Duty Board v3.70.2 — the payout table becomes the payroll sheet.

Manager review ask: "I need last month's breakdown per staff to know
what to pay." earnings_summary already accepts year/month — the dialog
just never exposed it. This adds:

- A [This month | Last month] toggle on the 💵 Payouts table in the
  Cost-to-serve dialog. One click flips the whole table to the prior
  calendar month — the figure payroll is actually run from.
- A TOTALS row: summed paid hours, hours ₦, resolutions, resolution ₦,
  phase ₦, and the grand total — the number that leaves the bank.
- An honest empty state per month instead of a blank space.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.70.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

OLD = '''\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\tmethod: "duty_board.earnings.earnings_summary",
\t\t\t\t\t\t\tcallback: (pr) => {
\t\t\t\t\t\t\t\tconst P = pr.message || {};
\t\t\t\t\t\t\t\tconst rows = (P.rows || []).map((p) => `<tr>
\t\t\t\t\t\t\t\t\t<td><b>${frappe.utils.escape_html(p.full_name)}</b></td>
\t\t\t\t\t\t\t\t\t<td>${p.paid_hours}h${p.capped ? " ⛔" : ""}<div class="text-muted" style="font-size:10.5px">${p.linked_hours}h ${__("linked")} / ${p.unlinked_hours}h ${__("unlinked")}</div></td>
\t\t\t\t\t\t\t\t\t<td>${naira(p.hours_amt)}</td>
\t\t\t\t\t\t\t\t\t<td>${p.res_count}</td>
\t\t\t\t\t\t\t\t\t<td>${naira(p.res_amt)}</td>
\t\t\t\t\t\t\t\t\t<td>${naira(p.phase_amt)}</td>
\t\t\t\t\t\t\t\t\t<td><b>${naira(p.grand)}</b></td>
\t\t\t\t\t\t\t\t</tr>`).join("");
\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay").html(rows
\t\t\t\t\t\t\t\t\t? `<h5 style="margin:14px 0 6px">💵 ${__("Payouts")} — ${frappe.utils.escape_html(P.label || "")}</h5>
\t\t\t\t\t\t\t\t\t\t<table class="table table-sm" style="font-size:12px"><tr><th>${__("Person")}</th><th>${__("Paid hours")}</th><th>${__("Hours ₦")}</th><th>${__("Res.")}</th><th>${__("Res. ₦")}</th><th>${__("Phase ₦")}</th><th>${__("Total")}</th></tr>${rows}</table>
\t\t\t\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("⛔ = monthly cap reached. Watch the unlinked share — a rising unlinked fraction means hours are drifting away from issues and tasks.")}</p>`
\t\t\t\t\t\t\t\t\t: "");
\t\t\t\t\t\t\t},
\t\t\t\t\t\t});'''

NEW = '''\t\t\t\t\t\tconst loadPay = (py, pm) => {
\t\t\t\t\t\t\t$(d.body).find(".duty-pay").html(`<div class="text-muted" style="font-size:12px">${__("Loading payouts…")}</div>`);
\t\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\t\tmethod: "duty_board.earnings.earnings_summary",
\t\t\t\t\t\t\t\targs: py ? { year: py, month: pm } : {},
\t\t\t\t\t\t\t\tcallback: (pr) => {
\t\t\t\t\t\t\t\t\tconst P = pr.message || {};
\t\t\t\t\t\t\t\t\tconst T = { h: 0, ha: 0, rc: 0, ra: 0, pa: 0, g: 0 };
\t\t\t\t\t\t\t\t\tconst rows = (P.rows || []).map((p) => {
\t\t\t\t\t\t\t\t\t\tT.h += p.paid_hours; T.ha += p.hours_amt; T.rc += p.res_count; T.ra += p.res_amt; T.pa += p.phase_amt; T.g += p.grand;
\t\t\t\t\t\t\t\t\t\treturn `<tr>
\t\t\t\t\t\t\t\t\t\t<td><b>${frappe.utils.escape_html(p.full_name)}</b></td>
\t\t\t\t\t\t\t\t\t\t<td>${p.paid_hours}h${p.capped ? " ⛔" : ""}<div class="text-muted" style="font-size:10.5px">${p.linked_hours}h ${__("linked")} / ${p.unlinked_hours}h ${__("unlinked")}</div></td>
\t\t\t\t\t\t\t\t\t\t<td>${naira(p.hours_amt)}</td>
\t\t\t\t\t\t\t\t\t\t<td>${p.res_count}</td>
\t\t\t\t\t\t\t\t\t\t<td>${naira(p.res_amt)}</td>
\t\t\t\t\t\t\t\t\t\t<td>${naira(p.phase_amt)}</td>
\t\t\t\t\t\t\t\t\t\t<td><b>${naira(p.grand)}</b></td>
\t\t\t\t\t\t\t\t\t</tr>`;
\t\t\t\t\t\t\t\t\t}).join("");
\t\t\t\t\t\t\t\t\tconst nd = frappe.datetime.now_date().split("-");
\t\t\t\t\t\t\t\t\tconst cy = parseInt(nd[0]), cm = parseInt(nd[1]);
\t\t\t\t\t\t\t\t\tconst ly = cm === 1 ? cy - 1 : cy, lm = cm === 1 ? 12 : cm - 1;
\t\t\t\t\t\t\t\t\tconst isCur = P.month === cm && P.year === cy;
\t\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay").html(`
\t\t\t\t\t\t\t\t\t\t<h5 style="margin:14px 0 6px">💵 ${__("Payouts")} — ${frappe.utils.escape_html(P.label || "")}
\t\t\t\t\t\t\t\t\t\t\t<span class="duty-pay-tog"><a data-y="${cy}" data-m="${cm}" class="${isCur ? "on" : ""}">${__("This month")}</a><a data-y="${ly}" data-m="${lm}" class="${isCur ? "" : "on"}">${__("Last month")}</a></span></h5>
\t\t\t\t\t\t\t\t\t\t${rows ? `<table class="table table-sm" style="font-size:12px"><tr><th>${__("Person")}</th><th>${__("Paid hours")}</th><th>${__("Hours ₦")}</th><th>${__("Res.")}</th><th>${__("Res. ₦")}</th><th>${__("Phase ₦")}</th><th>${__("Total")}</th></tr>${rows}
\t\t\t\t\t\t\t\t\t\t<tr class="duty-pay-tot"><td><b>${__("Total to pay")}</b></td><td><b>${Math.round(T.h * 10) / 10}h</b></td><td><b>${naira(T.ha)}</b></td><td><b>${T.rc}</b></td><td><b>${naira(T.ra)}</b></td><td><b>${naira(T.pa)}</b></td><td><b>${naira(T.g)}</b></td></tr></table>
\t\t\t\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("⛔ = monthly cap reached. Watch the unlinked share — a rising unlinked fraction means hours are drifting away from issues and tasks.")}</p>` : `<p class="text-muted" style="font-size:12px">${__("No earnings recorded for")} ${frappe.utils.escape_html(P.label || "")}.</p>`}`);
\t\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay-tog a").on("click", (ev) => loadPay($(ev.currentTarget).data("y"), $(ev.currentTarget).data("m")));
\t\t\t\t\t\t\t\t},
\t\t\t\t\t\t\t});
\t\t\t\t\t\t};
\t\t\t\t\t\tloadPay();'''

CSS_OLD = '\t\t\t@media (max-width: 640px) { .duty-earn-r { grid-template-columns: 1fr auto; } .duty-earn-r .duty-earn-calc { grid-column: 1 / -1; } }'
CSS_NEW = '''\t\t\t@media (max-width: 640px) { .duty-earn-r { grid-template-columns: 1fr auto; } .duty-earn-r .duty-earn-calc { grid-column: 1 / -1; } }
\t\t\t.duty-pay-tog { margin-left: 12px; font-size: 12px; font-weight: 400; }
\t\t\t.duty-pay-tog a { cursor: pointer; padding: 3px 10px; border: 1px solid #D8E2DF; border-radius: 20px; margin-right: 4px; color: #4b5a55; text-decoration: none; }
\t\t\t.duty-pay-tog a.on { background: #123C35; color: #fff; border-color: #123C35; font-weight: 700; }
\t\t\t.duty-pay-tot td { border-top: 2px solid #123C35 !important; background: #F4F8F6; }'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "loadPay" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.70.1"' not in init:
        sys.exit("ABORT: not at v3.70.1.")

    problems = []
    if js.count(OLD) != 1:
        problems.append(f"  [{js.count(OLD)}] payout call block")
    if js.count(CSS_OLD) != 1:
        problems.append(f"  [{js.count(CSS_OLD)}] css anchor")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    js = js.replace(OLD, NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.70.1"', '"3.70.2"'))
    print("  duty_board.js: month toggle + totals row")
    print("wrote __init__.py -> 3.70.2")


if __name__ == "__main__":
    main()
