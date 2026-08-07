#!/usr/bin/env python3
"""Duty Board v3.62.1 — baseline UI on the Projects-face Phases view.

Backend (v3.62.0) can freeze a baseline and compute slip. This surfaces
it:

- A baseline bar above the phase list: if not yet baselined, a "Set
  baseline" button (freezes the current plan); if baselined, shows when,
  with a "Re-baseline" option for a deliberate re-plan.
- Per phase, a slip indicator in the meta line: ✓ on plan, or ⚠ +Nd
  late / −Nd early against the frozen baseline. Only shown once
  baselined.

This is what makes a steering meeting answerable: "Discovery baselined
Aug 17, now Sep 3 — 17 days late" instead of a date that silently moved.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.62.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. slip indicator in the phase meta line -------------------------------
META_OLD = '\t\t\t\t\t\t<div class="duty-phase-meta">${esc(m.status)}${m.target_date ? ` · 🎯 ${esc(m.target_date)}` : ""} · ${m.cards_done || 0}/${m.cards_total || 0} ${__("tasks")}</div>'
META_NEW = '''\t\t\t\t\t\t<div class="duty-phase-meta">${esc(m.status)}${m.target_date ? ` · 🎯 ${esc(m.target_date)}` : ""} · ${m.cards_done || 0}/${m.cards_total || 0} ${__("tasks")}${m.baselined && m.slip_days !== null && m.slip_days !== undefined ? ` · <span class="duty-phase-slip ${m.slip_days > 0 ? "late" : m.slip_days < 0 ? "early" : "onplan"}">${m.slip_days > 0 ? `⚠ +${m.slip_days}d vs plan` : m.slip_days < 0 ? `${m.slip_days}d vs plan` : "✓ on plan"}</span>` : ""}</div>'''

# --- 2. baseline bar above the phase list -----------------------------------
BAR_OLD = '''\t\t\t$p.html(`
\t\t\t\t<div class="duty-phase-list">${rows}</div>
\t\t\t\t<div class="duty-phase-add">
\t\t\t\t\t<input type="text" class="form-control input-sm duty-newphase" placeholder="${__("Add a phase title and press Enter…")}" style="max-width:340px;display:inline-block">
\t\t\t\t</div>`);'''
BAR_NEW = '''\t\t\tconst anyBaselined = ms.some((m) => m.baselined);
\t\t\tconst maxSlip = ms.reduce((mx, m) => (m.slip_days != null && m.slip_days > mx ? m.slip_days : mx), 0);
\t\t\tconst baselineBar = anyBaselined
\t\t\t\t? `<div class="duty-baseline-bar on"><span>📏 ${__("Baselined")}${maxSlip > 0 ? ` · <b class="duty-phase-slip late">worst slip +${maxSlip}d</b>` : ` · <b class="duty-phase-slip onplan">on plan</b>`}</span><a class="duty-baseline-set muted">${__("Re-baseline")}</a></div>`
\t\t\t\t: `<div class="duty-baseline-bar"><span class="muted">📏 ${__("Not baselined — freeze the agreed plan to track slip against it.")}</span><button class="btn btn-xs btn-primary duty-baseline-set">${__("Set baseline")}</button></div>`;
\t\t\t$p.html(`
\t\t\t\t${baselineBar}
\t\t\t\t<div class="duty-phase-list">${rows}</div>
\t\t\t\t<div class="duty-phase-add">
\t\t\t\t\t<input type="text" class="form-control input-sm duty-newphase" placeholder="${__("Add a phase title and press Enter…")}" style="max-width:340px;display:inline-block">
\t\t\t\t</div>`);
\t\t\t$p.find(".duty-baseline-set").on("click", () => {
\t\t\t\tconst go = () => frappe.call({
\t\t\t\t\tmethod: "duty_board.client_room.project_set_baseline",
\t\t\t\t\targs: { project: project },
\t\t\t\t\tfreeze: true,
\t\t\t\t\tcallback: (r) => { frappe.show_alert({ message: __("Baseline set — {0} phases frozen.", [(r.message || {}).phases_baselined || 0]), indicator: "green" }); this.load_kanban(project); },
\t\t\t\t});
\t\t\t\tif (anyBaselined) frappe.confirm(__("Re-baseline this project? The frozen plan is replaced by the current dates — do this only for a deliberate, agreed re-plan."), go);
\t\t\t\telse go();
\t\t\t});'''

# --- 3. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-phase-add { margin-top: 10px; }'
CSS_NEW = '''\t\t\t.duty-phase-add { margin-top: 10px; }
\t\t\t.duty-baseline-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px; border: 1px solid #E4EAE8; border-radius: 10px; margin-bottom: 12px; background: #F7FAF9; font-size: 13px; }
\t\t\t.duty-baseline-bar.on { background: #F0F6F4; border-color: #D2E4E0; }
\t\t\t.duty-baseline-set { cursor: pointer; }
\t\t\ta.duty-baseline-set { font-size: 12px; text-decoration: underline; }
\t\t\t.duty-phase-slip { font-weight: 700; }
\t\t\t.duty-phase-slip.late { color: #C2410C; }
\t\t\t.duty-phase-slip.early { color: #0E8A63; }
\t\t\t.duty-phase-slip.onplan { color: #0E8A63; }'''

EDITS = [
    ("phase slip indicator", META_OLD, META_NEW),
    ("baseline bar + action", BAR_OLD, BAR_NEW),
    ("baseline CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "duty-baseline-bar" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.62.0"' not in init:
        sys.exit("ABORT: not at v3.62.0.")

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
        f.write(init.replace('"3.62.0"', '"3.62.1"'))
    print("wrote __init__.py -> 3.62.1")


if __name__ == "__main__":
    main()
