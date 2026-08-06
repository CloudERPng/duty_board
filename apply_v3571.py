#!/usr/bin/env python3
"""Duty Board v3.57.1 — Chat face polish.

1. Rail naming: the room's unit (General / Finance / HR…) becomes a
   non-truncating chip on the TITLE line, so two rooms for the same
   customer are distinguishable at a glance. The third line goes — the
   unit was the only thing it carried for rooms, and "Direct message"
   under every DM said nothing.

2. The team chat leaves the My Day face on DESKTOP. Chat now lives in
   the Chat face. Mobile is untouched: the phone chat tab renders
   through .duty-side, so the hide is scoped to min-width 992px.

Same contract as apply_v3570.py: exact-string anchors, all-or-nothing,
idempotent. Run from ~/frappe-bench/apps/duty_board. Requires v3.57.0
already applied.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. unit chip on the title line -----------------------------------------

A1_OLD = '''\t\t\t\t\t\t\t<span class="duty-ch-l1">
\t\t\t\t\t\t\t\t<b class="duty-ch-title">${esc(c.title || "")}</b>'''

A1_NEW = '''\t\t\t\t\t\t\t<span class="duty-ch-l1">
\t\t\t\t\t\t\t\t<b class="duty-ch-title">${esc(c.title || "")}</b>
\t\t\t\t\t\t\t\t${c.kind === "room" ? `<span class="duty-ch-unit">${esc(c.subtitle || "General")}</span>` : ""}'''

# --- 2. drop the third line --------------------------------------------------

A2_OLD = '\t\t\t\t\t\t\t<span class="duty-ch-sub">${esc(c.subtitle || "")}</span>\n'
A2_NEW = ''

# --- 3. styles: the chip, and chat off the desktop board ---------------------

A3_OLD = '\t\t\t.duty-ch-badge.is-client { background: #ef4444; }'

A3_NEW = A3_OLD + '''
\t\t\t.duty-ch-unit { background: var(--bg-light-gray, #eef2f1); color: #0f766e; border: 1px solid #d5e5e2; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 16px; white-space: nowrap; flex-shrink: 0; }
\t\t\t@media (min-width: 992px) {
\t\t\t\t/* Chat lives in the Chat face now; My Day gets its width back. */
\t\t\t\t.duty-layout > .duty-side { display: none !important; }
\t\t\t}'''

EDITS = [
    ("rail row: unit chip on title line", A1_OLD, A1_NEW),
    ("rail row: drop third line", A2_OLD, A2_NEW),
    ("styles: unit chip + desktop board sans chat", A3_OLD, A3_NEW),
]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if "duty-chatface" not in src:
        sys.exit("ABORT: v3.57.0 not applied — run apply_v3570.py first.")
    if "duty-ch-unit" in src:
        print("Already applied — duty-ch-unit present. Nothing to do.")
        return

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
    new_init = init.replace('"3.57.0"', '"3.57.1"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.1")
    else:
        print("NOTE: __init__.py not at 3.57.0 — version left untouched.")


if __name__ == "__main__":
    main()
