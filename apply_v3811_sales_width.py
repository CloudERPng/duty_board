#!/usr/bin/env python3
"""Duty Board v3.81.1 — Sales face width (screenshot-reported).

v3.80.0 capped Sales at 1140px — right for a list, wrong for what Sales
now is: a six-stage pipeline kanban plus radar. On wide screens that
left a dead gutter on the left while Negotiation fell off the right
edge into a scrollbar. Sales gets the Projects treatment: 1560px cap,
centered — six columns breathe, ultra-wides stay composed, internal
scroll only when stages genuinely exceed the cap. Mobile untouched.

JS(CSS) only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.81.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

OLD = "\t\t\t\tbody:not(.duty-mobile) .duty-sales { max-width: 1140px; margin-left: auto; margin-right: auto; }"
NEW = "\t\t\t\tbody:not(.duty-mobile) .duty-sales { max-width: 1560px; margin-left: auto; margin-right: auto; }"


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if NEW in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.81.0"' not in init:
        sys.exit("ABORT: not at v3.81.0.")
    if js.count(OLD) != 1:
        sys.exit(f"ABORT: anchor [{js.count(OLD)}].")

    print("Anchor matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js.replace(OLD, NEW, 1))
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.81.0"', '"3.81.1"'))
    print("  duty_board.js: .duty-sales cap 1140 -> 1560")
    print("wrote __init__.py -> 3.81.1")


if __name__ == "__main__":
    main()
