#!/usr/bin/env python3
"""Duty Board v3.61.6 — PM tab: single column, sub-tabs.

The PM (Projects) tab was a 2-column grid but only the right column was
ever filled — tasks moved into the milestones card in an earlier
redesign and left the left column empty (the dead white box). This:

1. Collapses the PM grid to a SINGLE column — milestones and their per-
   phase task lists get full width to breathe (the "PM serious" look).
2. Adds SUB-TABS at the top of the PM content: Phases · Change requests ·
   Timeline · Acceptance testing. One panel shows at a time; Phases is
   default. The Timeline and Acceptance tabs appear only when they have
   content (keyed off the same card.style.display their render functions
   already set), so an engagement with no UAT shows no UAT tab.

Mechanism: a #pmsubbar injected before the mstones card; window._pmsub
holds the active panel; pmShow(panel) toggles a body attribute that CSS
uses to show exactly one PM card. Existing fold() handlers are neutered
on PM (a sub-tab panel is always open, not foldable).

portal only. bench build --app duty_board && bench restart,
clear-website-cache. Anchored, idempotent. Requires v3.61.5.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

# --- 1. collapse grid to single column + sub-tab CSS + panel visibility -----
CSS_OLD = '''\t\t@media (min-width: 900px) {
\t\t\tbody[data-tab="pm"] .rightcol {
\t\t\t\tdisplay: grid !important; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
\t\t\t\tgap: 18px; align-items: start; width: auto;
\t\t\t}
\t\t\tbody[data-tab="pm"] .rightcol > .card { margin-bottom: 0; }
\t\t}'''
CSS_NEW = '''\t\t@media (min-width: 900px) {
\t\t\tbody[data-tab="pm"] .rightcol {
\t\t\t\tdisplay: block !important; width: auto; max-width: 1100px; margin: 0 auto;
\t\t\t}
\t\t\tbody[data-tab="pm"] .rightcol > .card { margin-bottom: 16px; }
\t\t}
\t\t/* PM sub-tabs: show exactly one panel at a time. */
\t\t#pmsubbar { display: none; }
\t\tbody[data-tab="pm"] #pmsubbar {
\t\t\tdisplay: flex; gap: 4px; max-width: 1100px; margin: 0 auto 14px; flex-wrap: wrap;
\t\t}
\t\tbody[data-tab="pm"] #pmsubbar a {
\t\t\tfont-size: 13px; font-weight: 700; padding: 8px 16px; border-radius: 10px;
\t\t\tcolor: #65736F; cursor: pointer; text-decoration: none; border: 1px solid transparent;
\t\t}
\t\tbody[data-tab="pm"] #pmsubbar a.on { background: #123C35; color: #fff; }
\t\tbody[data-tab="pm"] #pmsubbar a:not(.on):hover { background: #EAF0EE; }
\t\tbody[data-tab="pm"][data-pmsub="phases"] .rightcol > .card:not(.mstones),
\t\tbody[data-tab="pm"][data-pmsub="chreqs"] .rightcol > .card:not(.chreqs),
\t\tbody[data-tab="pm"][data-pmsub="timeline"] .rightcol > .card:not(.tlx),
\t\tbody[data-tab="pm"][data-pmsub="uat"] .rightcol > .card:not(.uatx) { display: none !important; }'''

# --- 2. the sub-tab bar markup, before the mstones card ---------------------
BAR_OLD = '''\t<div class="card mstones">
\t\t<h3 class="foldh" onclick="fold(this,'mstones')">'''
BAR_NEW = '''\t<div id="pmsubbar">
\t\t<a data-sub="phases" class="on" onclick="pmShow('phases')">🚩 Phases</a>
\t\t<a data-sub="chreqs" onclick="pmShow('chreqs')">🔁 Change requests</a>
\t\t<a data-sub="timeline" data-optional="1" onclick="pmShow('timeline')" style="display:none">📅 Timeline</a>
\t\t<a data-sub="uat" data-optional="1" onclick="pmShow('uat')" style="display:none">🧪 Acceptance testing</a>
\t</div>
\t<div class="card mstones">
\t\t<h3 class="foldh" onclick="fold(this,'mstones')">'''

# --- 3. the switcher JS + optional-tab visibility, after setTab -------------
JS_OLD = '''setTab((() => {
\tconst t = localStorage.getItem("xl_tab");
\tif (t === "plan") return "pm";
\tif (!t || t === "chat" || t === "tasks") return "home";
\treturn t;
})());'''
JS_NEW = '''window._pmsub = "phases";
function pmShow(panel) {
\twindow._pmsub = panel;
\tdocument.body.dataset.pmsub = panel;
\tdocument.querySelectorAll("#pmsubbar a").forEach((a) => a.classList.toggle("on", a.dataset.sub === panel));
}
function pmSyncOptionalTabs() {
\t// A Timeline / UAT tab appears only when its card has content. The render
\t// functions set card.style.display; we mirror that onto the tab button.
\tconst map = { timeline: ".card.tlx", uat: ".card.uatx" };
\tObject.entries(map).forEach(([sub, sel]) => {
\t\tconst card = document.querySelector(sel);
\t\tconst tab = document.querySelector(`#pmsubbar a[data-sub="${sub}"]`);
\t\tif (!tab) return;
\t\tconst has = card && card.style.display !== "none";
\t\ttab.style.display = has ? "" : "none";
\t\tif (!has && window._pmsub === sub) pmShow("phases"); // active tab vanished
\t});
}
document.body.dataset.pmsub = "phases";
setTab((() => {
\tconst t = localStorage.getItem("xl_tab");
\tif (t === "plan") return "pm";
\tif (!t || t === "chat" || t === "tasks") return "home";
\treturn t;
})());'''

# --- 4. call pmSyncOptionalTabs after timeline & uat render -----------------
TL_OLD = '''\tif (!(t.events || []).length) { card.style.display = "none"; return; }
\tcard.style.display = "";'''
TL_NEW = '''\tif (!(t.events || []).length) { card.style.display = "none"; if (window.pmSyncOptionalTabs) pmSyncOptionalTabs(); return; }
\tcard.style.display = "";
\tif (window.pmSyncOptionalTabs) pmSyncOptionalTabs();'''

UAT_OLD = '''\tif (!u.rows.length) { card.style.display = "none"; QS.uatq = []; renderQueue(); return; }
\tcard.style.display = "";'''
UAT_NEW = '''\tif (!u.rows.length) { card.style.display = "none"; QS.uatq = []; renderQueue(); if (window.pmSyncOptionalTabs) pmSyncOptionalTabs(); return; }
\tcard.style.display = "";
\tif (window.pmSyncOptionalTabs) pmSyncOptionalTabs();'''

EDITS = [
    ("collapse grid + sub-tab CSS", CSS_OLD, CSS_NEW),
    ("sub-tab bar markup", BAR_OLD, BAR_NEW),
    ("switcher JS + optional sync", JS_OLD, JS_NEW),
    ("timeline sync hook", TL_OLD, TL_NEW),
    ("uat sync hook", UAT_OLD, UAT_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, PORTAL), encoding="utf-8") as f:
        html = f.read()

    if "function pmShow(" in html:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.5"' not in init:
        sys.exit("ABORT: not at v3.61.5.")

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
        f.write(init.replace('"3.61.5"', '"3.61.6"'))
    print("wrote __init__.py -> 3.61.6")


if __name__ == "__main__":
    main()
