#!/usr/bin/env python3
"""Duty Board v3.59.3 — the stack you can actually find.

Two fixes surfaced by the owner failing to find "start task B" — which
is the test that matters:

1. LABEL. The card button "Switch Task" reads as REPLACE, because
   until v3.59.2 that is what it did. It becomes "＋ Another Task" with
   a tooltip saying the current one pauses into the tray. Same dialog,
   same wiring — the words now describe the new semantics.

2. THE TRAP. The switch dialog's "I completed: {task}" checkbox
   defaulted to TICKED. Under stack semantics a blind click-through
   would mark Task A completed instead of pausing it — the exact
   opposite of what the feature promises. Default flips to unticked,
   and the dialog now opens with a line stating plainly where the
   current task is going: "⏸ '{task}' will pause into your tray…".

Anchored, all-or-nothing, idempotent. Requires v3.59.2.
Run from ~/frappe-bench/apps/duty_board. JS only:
bench build --app duty_board && bench restart.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '\t\t\t\t\t\t<button class="btn btn-default duty-switch-btn">${__("Switch Task")}</button>'
A1_NEW = '\t\t\t\t\t\t<button class="btn btn-default duty-switch-btn" title="${__("Start another task — this one pauses into your tray")}">＋ ${__("Another Task")}</button>'

A2_OLD = '\t\tconst current = this.current_task;\n\t\tif (switching && current && current.todo) {'
A2_NEW = '''\t\tconst current = this.current_task;
\t\tif (switching && current) {
\t\t\tconst note = current.todo
\t\t\t\t? __("⏸ “{0}” will pause into your tray unless you mark it completed below.", [frappe.utils.escape_html(current.activity)])
\t\t\t\t: __("⏸ “{0}” will pause into your tray — resume it anytime.", [frappe.utils.escape_html(current.activity)]);
\t\t\tfields.unshift({
\t\t\t\tfieldname: "pause_note",
\t\t\t\tfieldtype: "HTML",
\t\t\t\toptions: `<div class="duty-pause-note">${note}</div>`,
\t\t\t});
\t\t}
\t\tif (switching && current && current.todo) {'''

A3_OLD = '\t\t\t\tlabel: __("I completed: {0}", [frappe.utils.escape_html(current.activity)]),\n\t\t\t\tdefault: 1,'
A3_NEW = '\t\t\t\tlabel: __("I completed: {0}", [frappe.utils.escape_html(current.activity)]),\n\t\t\t\t// Unticked by default: switching PAUSES. Completing is the deliberate act.\n\t\t\t\tdefault: 0,'

A4_OLD = '\t\t\t.duty-paused-age { font-size: 11px; color: var(--text-muted, #999); margin-left: 6px; }'
A4_NEW = A4_OLD + '''
\t\t\t.duty-pause-note { background: #FFF7E6; border: 1px solid #F5D08A; border-radius: 8px; padding: 8px 12px; margin-bottom: 10px; font-size: 12.5px; }'''

EDITS = [
    ("card button: ＋ Another Task", A1_OLD, A1_NEW),
    ("dialog: pause-destination note", A2_OLD, A2_NEW),
    ("checkbox: default unticked", A3_OLD, A3_NEW),
    ("styles: pause note", A4_OLD, A4_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "duty-pause-note" in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.2"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.2 — apply apply_v3592_stack.py first.")

    problems = [f"  [{files[JS].count(o)}] {label}" for label, o, _ in EDITS if files[JS].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = files[JS]
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(out)

    init = files[INIT].replace('"3.59.2"', '"3.59.3"')
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init)
    print("wrote __init__.py -> 3.59.3")


if __name__ == "__main__":
    main()
