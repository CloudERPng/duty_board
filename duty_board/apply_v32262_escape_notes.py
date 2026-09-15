#!/usr/bin/env python3
"""Duty Board v3.226.2 — AUDIT CHUNK E: notes written by consultants, rendered raw.

Task notes and work-session notes were interpolated into the staff SPA without
escaping, at five places. That matters more than it first looks, because
projects.py guards those writes with require_staff_or_consultant — external
consultants hold desk credentials. So the path is consultant to full staff
member: anything one of them types into a task or session note executes in the
browser of whoever opens the board, in a session with System User rights.

Escaped at all five sites, with the display unchanged.

What Chunk E found clean, and it is most of it:
  - client room messages are escaped before linkify, both in the SPA and in
    DMs, so the client-to-staff path was already closed
  - issue titles use esc(); issue descriptions raised by clients ARE escaped
    (escape_html then newline-to-br) — my first scan flagged them by reading a
    fragment of a compound interpolation rather than the whole expression, and
    they were correct all along
  - the client portal itself came back with no unescaped user-typed values
  - both bundles parse

Remaining and deliberately not touched here: about forty interpolations of
staff-typed titles, customer names and emails in the SPA. Same class, but
staff-to-staff and mostly on values that cannot carry markup in practice. They
want one careful pass rather than a scattered edit at the end of a long day.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart.
No schema. Anchored, idempotent. Requires v3.226.1.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv


N1_OLD = '${x.notes ? " " + x.notes : ""}'

N1_NEW = '${x.notes ? " " + frappe.utils.escape_html(x.notes) : ""}'

N2_OLD = '${t.notes ? `<span>💬 ${t.notes}</span>` : ""}'

N2_NEW = '${t.notes ? `<span>💬 ${frappe.utils.escape_html(t.notes)}</span>` : ""}'

N3_OLD = '${l.notes ? `<span>💬 ${l.notes}</span>` : ""}'

N3_NEW = '${l.notes ? `<span>💬 ${frappe.utils.escape_html(l.notes)}</span>` : ""}'



EDITS = [(N1_OLD, N1_NEW, 3, "session notes"),
         (N2_OLD, N2_NEW, 1, "kanban task notes"),
         (N3_OLD, N3_NEW, 1, "list task notes")]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "escape_html(x.notes)" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.226.1"' not in init:
        sys.exit("ABORT: not at v3.226.1.")

    problems = []
    for old, _new, want, label in EDITS:
        n = js.count(old)
        if n != want:
            problems.append("  [%d != %d] %s" % (n, want, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchor groups matched exactly." % len(EDITS))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for old, new, want, _label in EDITS:
        js = js.replace(old, new, want)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: 5 note interpolations escaped")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.226.1"', '"3.226.2"'))
    print("wrote __init__.py -> 3.226.2")


if __name__ == "__main__":
    main()
