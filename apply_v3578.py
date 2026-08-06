#!/usr/bin/env python3
"""Duty Board v3.57.8 — My Day and My Dashboard become one workspace.

DESKTOP STAFF: a single "My Day" rail entry with two horizontal tabs at
the top — \U0001f4c6 My Day (the board: current task, plan, sessions, team
today) and \U0001f4ca Dashboard (tiles, charts, calendar, rooms, training).
The separate "My Dashboard" rail button goes away. Any code that calls
show_face("me") — dashboard deep-links, notifications — transparently
lands on the Dashboard tab, so nothing else needed rewiring.

DELIBERATELY UNCHANGED:
- Consultants: their Dashboard stays a standalone face; the board face
  carries team-wide information they must not see, so no merge.
- Mobile: the \U0001f464 chip and mtab routing keep today's behaviour; the
  merge is desktop-only (the `merged` flag gates every change).

This is a tab-switcher over the two EXISTING faces — both render
pipelines untouched — not a DOM merge.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.7.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. constructor: the tab bar --------------------------------------------

A1_OLD = '\t\tthis.face = "board";'
A1_NEW = '''\t\tthis.face = "board";
\t\tthis._day_tab = "today";
\t\tthis.$daytabs = $(`
\t\t\t<div class="duty-daytabs" style="display:none">
\t\t\t\t<a data-dt="today" class="on">\\ud83d\\udcc6 ${__("My Day")}</a>
\t\t\t\t<a data-dt="dash">\\ud83d\\udcca ${__("Dashboard")}</a>
\t\t\t</div>`).insertBefore(this.body);
\t\tthis.$daytabs.find("a").on("click", (e) => {
\t\t\tthis._day_tab = $(e.currentTarget).attr("data-dt") === "dash" ? "dash" : "today";
\t\t\tthis.show_face("board");
\t\t});'''

# --- 2. staff desktop: My Dashboard leaves the rail --------------------------

A2_OLD = '\tboard._is_consultant = localStorage.getItem("duty_cons") === "1";'
A2_NEW = A2_OLD + '''
\t// Desktop staff reach the dashboard as a tab inside My Day now.
\t// Consultants keep the standalone face; mobile keeps its \\ud83d\\udc64 chip.
\tif (!board._is_consultant && !board.is_mobile()) {
\t\tboard.rail = board.rail.filter((r) => r.id !== "me");
\t}'''

# --- 3. show_face: remap + merged-aware toggles ------------------------------

A3_OLD = '\tshow_face(face) {\n\t\tif (this._idshim) this._idshim.hide();'
A3_NEW = '''\tshow_face(face) {
\t\tconst merged = !this._is_consultant && !this.is_mobile();
\t\tif (face === "me" && merged) {
\t\t\t// Every existing show_face("me") caller lands on the Dashboard tab.
\t\t\tface = "board";
\t\t\tthis._day_tab = "dash";
\t\t}
\t\tif (this._idshim) this._idshim.hide();'''

A4_OLD = '\t\tthis.body.toggle(face === "board");\n\t\t$(".duty-pulse").toggle(face === "board");'
A4_NEW = '''\t\tconst dtab = merged ? (this._day_tab || "today") : "today";
\t\tthis.body.toggle(face === "board" && dtab === "today");
\t\t$(".duty-pulse").toggle(face === "board" && dtab === "today");
\t\tif (this.$daytabs) {
\t\t\tthis.$daytabs.toggle(merged && face === "board");
\t\t\tthis.$daytabs.find("a").removeClass("on").filter(`[data-dt="${dtab}"]`).addClass("on");
\t\t}'''

A5_OLD = '\t\tthis.$me.toggle(face === "me");'
A5_NEW = '\t\tthis.$me.toggle(merged ? face === "board" && dtab === "dash" : face === "me");'

A6_OLD = '\t\tif (face === "me") this.refresh_me();'
A6_NEW = '\t\tif (face === "me" || (face === "board" && merged && dtab === "dash")) this.refresh_me();'

# --- 4. styles ---------------------------------------------------------------

A7_OLD = '\t\t\t.duty-fluid.container { max-width: 100%; }'
A7_NEW = A7_OLD + '''
\t\t\t.duty-daytabs { display: flex; gap: 8px; margin: 0 0 12px; }
\t\t\t.duty-daytabs a { padding: 7px 18px; border-radius: 10px; font-weight: 600; cursor: pointer; border: 1px solid var(--border-color, #e0e0e0); background: var(--card-bg, #fff); color: var(--text-muted, #666); text-decoration: none; }
\t\t\t.duty-daytabs a:hover { color: var(--text-color, #333); text-decoration: none; }
\t\t\t.duty-daytabs a.on { background: #0F5C55; border-color: #0F5C55; color: #fff; }'''

EDITS = [
    ("constructor: day tab bar", A1_OLD, A1_NEW),
    ("rail: My Dashboard off desktop staff rail", A2_OLD, A2_NEW),
    ("show_face: me -> board+dash remap (merged only)", A3_OLD, A3_NEW),
    ("show_face: merged-aware board toggle + tab sync", A4_OLD, A4_NEW),
    ("show_face: merged-aware $me toggle", A5_OLD, A5_NEW),
    ("show_face: dashboard refresh on tab", A6_OLD, A6_NEW),
    ("styles: day tabs", A7_OLD, A7_NEW),
]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if "duty-daytabs" in src:
        print("Already applied — duty-daytabs present. Nothing to do.")
        return
    if '["issues", "chat", "projects", "me", "news"]' not in src:
        sys.exit("ABORT: v3.57.7 not applied — run apply_v3577.py first.")

    problems = [f"  [{src.count(o)} matches] {label}" for label, o, _ in EDITS if src.count(o) != 1]
    if problems:
        print("ABORT — anchors did not match exactly once:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = src
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(js_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"\nwrote {JS}")

    init_path = os.path.join(os.getcwd(), INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.7"', '"3.57.8"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.8")
    else:
        print("NOTE: version was not 3.57.7 — left untouched.")


if __name__ == "__main__":
    main()
