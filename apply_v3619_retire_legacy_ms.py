#!/usr/bin/env python3
"""Duty Board v3.61.9 — retire the legacy room-card milestone UI (Option C).

Phases now live on the Projects face (v3.61.2–.5). The room card kept a
SECOND path — a milestone strip with a "Manage" link opening a dialog
that called the room-scoped milestones_seed/milestone_add, the exact
functions that re-create the room-blended mixing we eliminated. Option C:

- SINGLE-project room: keep the glance strip (it's accurate there), but
  the "Manage" link now jumps to the Projects face instead of opening
  the legacy dialog.
- MULTI-project room: the strip's blended read is meaningless, so hide
  it and show a one-line pointer to the Projects face.
- The legacy milestones_dialog method is deleted outright — no path
  reaches it anymore.

The room-scoped milestones_seed / milestone_add endpoints are LEFT in
place (harmless, unreferenced by UI now) to avoid touching backend in a
UI-retirement patch; a later cleanup can remove them.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.61.8.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. rebuild the strip: single-project glance + redirect / multi hide -----
STRIP_OLD = '''\t\tconst $ms = $room.find(".duty-cr-mstones");
\t\tif ($ms.length) {
\t\t\tconst mst = x.milestones || [];
\t\t\tconst done = mst.filter((m) => m.status === "Approved").length;
\t\t\tconst waiting = mst.filter((m) => m.status === "Awaiting Approval").length;
\t\t\tconst current = mst.find((m) => m.status === "In Progress");
\t\t\t$ms.html(`
\t\t\t\t<div class="duty-lead-section">🏁 ${__("Milestones")} <a class="duty-cr-msmanage">${__("Manage")}</a></div>
\t\t\t\t${mst.length
\t\t\t\t\t? `<div class="duty-cr-msline">
\t\t\t\t\t\t\t<div class="duty-cr-msbar"><i style="width:${Math.round((done / mst.length) * 100)}%"></i></div>
\t\t\t\t\t\t\t<span>${done}/${mst.length} ${__("approved")}${waiting ? ` · <b class="duty-cr-mswait">⏳ ${waiting} ${__("awaiting client")}</b>` : ""}${current ? ` · 🔵 ${frappe.utils.escape_html(current.title)}` : ""}</span>
\t\t\t\t\t\t</div>`
\t\t\t\t\t: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No milestones yet — Manage to seed the Xlevel method.")}</div>`}
\t\t\t`);
\t\t\t$ms.find(".duty-cr-msmanage").on("click", () => this.milestones_dialog(x));
\t\t}'''
STRIP_NEW = '''\t\tconst $ms = $room.find(".duty-cr-mstones");
\t\tif ($ms.length) {
\t\t\tconst mst = x.milestones || [];
\t\t\tconst projCount = new Set(mst.map((m) => m.project).filter(Boolean)).size;
\t\t\tif (projCount > 1) {
\t\t\t\t// Multi-project room: the blended strip is meaningless — point to the
\t\t\t\t// Projects face where each project's phases are managed on their own.
\t\t\t\t$ms.html(`
\t\t\t\t\t<div class="duty-lead-section">🏁 ${__("Phases")}</div>
\t\t\t\t\t<div class="text-muted" style="font-size:var(--text-sm)">${__("This client has multiple projects. Manage each project's phases on the")} <a class="duty-cr-msgoproj" style="cursor:pointer;font-weight:600">${__("Projects face")}</a>.</div>
\t\t\t\t`);
\t\t\t} else {
\t\t\t\tconst done = mst.filter((m) => m.status === "Approved").length;
\t\t\t\tconst waiting = mst.filter((m) => m.status === "Awaiting Approval").length;
\t\t\t\tconst current = mst.find((m) => m.status === "In Progress");
\t\t\t\t$ms.html(`
\t\t\t\t\t<div class="duty-lead-section">🏁 ${__("Phases")} <a class="duty-cr-msgoproj" style="cursor:pointer">${__("Manage ›")}</a></div>
\t\t\t\t\t${mst.length
\t\t\t\t\t\t? `<div class="duty-cr-msline">
\t\t\t\t\t\t\t\t<div class="duty-cr-msbar"><i style="width:${Math.round((done / mst.length) * 100)}%"></i></div>
\t\t\t\t\t\t\t\t<span>${done}/${mst.length} ${__("approved")}${waiting ? ` · <b class="duty-cr-mswait">⏳ ${waiting} ${__("awaiting client")}</b>` : ""}${current ? ` · 🔵 ${frappe.utils.escape_html(current.title)}` : ""}</span>
\t\t\t\t\t\t\t</div>`
\t\t\t\t\t\t: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No phases yet — manage on the Projects face.")}</div>`}
\t\t\t\t`);
\t\t\t}
\t\t\t$ms.find(".duty-cr-msgoproj").on("click", () => this.show_face("projects"));
\t\t}'''

# --- 2. delete the legacy milestones_dialog method entirely -----------------
# Anchor from the method opening to its close, replaced with a tombstone
# comment. The method spans milestones_dialog(x) { ... render(x); } .
DIALOG_HEAD = '\tmilestones_dialog(x) {'
DIALOG_TAIL = '''\t\trender(x);
\t\td.show();
\t}

\tchreqs_dialog(x) {'''
DIALOG_REPLACE_TAIL = '''\tchreqs_dialog(x) {'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "duty-cr-msgoproj" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.8"' not in init:
        sys.exit("ABORT: not at v3.61.8.")

    if js.count(STRIP_OLD) != 1:
        sys.exit(f"ABORT: strip anchor found {js.count(STRIP_OLD)} times.")
    if js.count(DIALOG_HEAD) != 1:
        sys.exit(f"ABORT: milestones_dialog head found {js.count(DIALOG_HEAD)} times.")
    if js.count(DIALOG_TAIL) != 1:
        sys.exit(f"ABORT: milestones_dialog tail found {js.count(DIALOG_TAIL)} times.")

    # verify head..tail is a contiguous block (head index < tail index, and the
    # slice between them contains no other method definition at 1-tab indent
    # that would indicate a mismatched span)
    hi = js.index(DIALOG_HEAD)
    ti = js.index(DIALOG_TAIL)
    if not (hi < ti):
        sys.exit("ABORT: dialog head/tail ordering wrong.")

    print("All anchors matched (strip + dialog head + dialog tail).")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # 1. strip
    js = js.replace(STRIP_OLD, STRIP_NEW, 1)

    # 2. delete the method: from head to just before chreqs_dialog
    hi = js.index(DIALOG_HEAD)
    ti = js.index(DIALOG_REPLACE_TAIL, hi)
    js = js[:hi] + js[ti:]
    print("  removed legacy milestones_dialog method")

    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  rebuilt room-card milestone strip (single-project glance / multi hide / redirect)")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.61.8"', '"3.61.9"'))
    print("wrote __init__.py -> 3.61.9")


if __name__ == "__main__":
    main()
