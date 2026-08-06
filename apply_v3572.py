#!/usr/bin/env python3
"""Duty Board v3.57.2 — rail width + badge visibility.

- Conversation rail 320px -> 360px; the thread column gives back the
  40px (it's flex). Row padding up a notch.
- Unread pills go WhatsApp-green and slightly larger so they read as
  "new messages" at a glance. Red stays reserved for client-authored
  unread — that distinction is operational, not cosmetic.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.1.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '\t\t\t.duty-ch-rail { width: 320px; min-width: 320px; display: flex; flex-direction: column; border-right: 1px solid var(--border-color, #e0e0e0); background: var(--fg-color, #fafafa); }'
A1_NEW = '\t\t\t.duty-ch-rail { width: 360px; min-width: 360px; display: flex; flex-direction: column; border-right: 1px solid var(--border-color, #e0e0e0); background: var(--fg-color, #fafafa); }'

A2_OLD = '\t\t\t.duty-ch-badge { background: #6b7280; color: #fff; border-radius: 10px; padding: 0 7px; font-size: 11px; font-weight: 700; line-height: 18px; }'
A2_NEW = '\t\t\t.duty-ch-badge { background: #22c55e; color: #fff; border-radius: 11px; padding: 0 8px; font-size: 12px; font-weight: 700; line-height: 20px; min-width: 20px; text-align: center; }'

A3_OLD = '\t\t\t.duty-ch-row { display: flex; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--border-color, #ececec); cursor: pointer; text-decoration: none; color: inherit; }'
A3_NEW = '\t\t\t.duty-ch-row { display: flex; gap: 11px; padding: 12px 14px; border-bottom: 1px solid var(--border-color, #ececec); cursor: pointer; text-decoration: none; color: inherit; }'

EDITS = [
    ("rail: 320 -> 360", A1_OLD, A1_NEW),
    ("badge: green, larger", A2_OLD, A2_NEW),
    ("rows: breathing room", A3_OLD, A3_NEW),
]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if "duty-ch-unit" not in src:
        sys.exit("ABORT: v3.57.1 not applied — run apply_v3571.py first.")
    if "width: 360px; min-width: 360px" in src:
        print("Already applied — 360px rail present. Nothing to do.")
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
    new_init = init.replace('"3.57.1"', '"3.57.2"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.2")
    else:
        print("NOTE: __init__.py not at 3.57.1 — version left untouched.")


if __name__ == "__main__":
    main()
