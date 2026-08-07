#!/usr/bin/env python3
"""Duty Board v3.62.2 — edit a phase's date/title on the Phases view.

Gap found: retiring the legacy room-card dialog (v3.61.9) removed the
only place a phase's target date could be edited, and the new Projects-
face Phases view never had an edit action — only reorder/start/sign-off/
delete. So you couldn't adjust seeded dates before baselining. The
milestone_update backend already supports it; this wires an ✎ Edit
action to it.

Adds an ✎ action to each non-locked phase opening a small dialog: title,
description, target date -> milestone_update. Approved (locked) phases
stay uneditable (their sign-off is permanent).

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.62.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. add the ✎ edit link (before delete, non-locked only) ----------------
ACTS_OLD = '''\t\t\t\t\t\t${st === "active" && m.status !== "In Progress" ? `<a data-a="start" title="${__("Mark in progress")}">▶</a>` : ""}
\t\t\t\t\t\t${!locked && m.status !== "Awaiting Approval" ? `<a data-a="ask" title="${__("Request client sign-off")}">✅</a>` : ""}
\t\t\t\t\t\t${!locked ? `<a data-a="del" title="${__("Delete phase")}">🗑</a>` : ""}'''
ACTS_NEW = '''\t\t\t\t\t\t${!locked ? `<a data-a="edit" title="${__("Edit phase")}">✎</a>` : ""}
\t\t\t\t\t\t${st === "active" && m.status !== "In Progress" ? `<a data-a="start" title="${__("Mark in progress")}">▶</a>` : ""}
\t\t\t\t\t\t${!locked && m.status !== "Awaiting Approval" ? `<a data-a="ask" title="${__("Request client sign-off")}">✅</a>` : ""}
\t\t\t\t\t\t${!locked ? `<a data-a="del" title="${__("Delete phase")}">🗑</a>` : ""}'''

# --- 2. add the edit case in the handler ------------------------------------
HANDLER_OLD = '''\t\t\t\tif (a === "del") return frappe.confirm(__("Delete this phase? Its tasks are kept but unlinked."), () => frappe.call({ method: "duty_board.client_room.milestone_delete", args: { id: id }, callback: done }));
\t\t\t});'''
HANDLER_NEW = '''\t\t\t\tif (a === "del") return frappe.confirm(__("Delete this phase? Its tasks are kept but unlinked."), () => frappe.call({ method: "duty_board.client_room.milestone_delete", args: { id: id }, callback: done }));
\t\t\t\tif (a === "edit") {
\t\t\t\t\tconst m = (ms || []).find((z) => z.name === id) || {};
\t\t\t\t\tfrappe.prompt(
\t\t\t\t\t\t[
\t\t\t\t\t\t\t{ fieldname: "title", fieldtype: "Data", label: __("Phase title"), default: m.title || "", reqd: 1 },
\t\t\t\t\t\t\t{ fieldname: "target_date", fieldtype: "Date", label: __("Target date"), default: m.target_date || null },
\t\t\t\t\t\t\t{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: m.description || "" },
\t\t\t\t\t\t],
\t\t\t\t\t\t(v) => frappe.call({
\t\t\t\t\t\t\tmethod: "duty_board.client_room.milestone_update",
\t\t\t\t\t\t\targs: { id: id, title: v.title, target_date: v.target_date || null, description: v.description || "" },
\t\t\t\t\t\t\tcallback: () => { frappe.show_alert({ message: __("Phase updated."), indicator: "green" }); done(); },
\t\t\t\t\t\t}),
\t\t\t\t\t\t__("Edit phase"), __("Save")
\t\t\t\t\t);
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t});'''

EDITS = [
    ("edit action link", ACTS_OLD, ACTS_NEW),
    ("edit handler case", HANDLER_OLD, HANDLER_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if 'data-a="edit" title="${__("Edit phase")}"' in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.62.1"' not in init:
        sys.exit("ABORT: not at v3.62.1.")

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
        f.write(init.replace('"3.62.1"', '"3.62.2"'))
    print("wrote __init__.py -> 3.62.2")


if __name__ == "__main__":
    main()
