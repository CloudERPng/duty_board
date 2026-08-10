#!/usr/bin/env python3
"""Duty Board v3.79.1 — HOTFIX for v3.79.0 (video-reported dead button).

The task view is a docked drawer whose `d` is a shim (show/hide only) —
`d.body` doesn't exist, so the file handlers bound to $(d.body) attached
to nothing: the 📎 section rendered but Add files / preview / delete
were dead. Bind on $dw (the drawer element, in scope) instead.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.79.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

PAIRS = [
    ('\t\t$(d.body).find(".duty-tf-chip").on("click", (e) => {',
     '\t\t$dw.find(".duty-tf-chip").off("click").on("click", (e) => {'),
    ('\t\t$(d.body).find(".duty-tf-del").on("click", (e) => {',
     '\t\t$dw.find(".duty-tf-del").off("click").on("click", (e) => {'),
    ('\t\t$(d.body).find(".duty-tf-add input").on("change", async (e) => {',
     '\t\t$dw.find(".duty-tf-add input").off("change").on("change", async (e) => {'),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if '$dw.find(".duty-tf-chip")' in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.79.0"' not in init:
        sys.exit("ABORT: not at v3.79.0.")

    problems = [f"  [{js.count(o)}] handler {i+1}" for i, (o, _n) in enumerate(PAIRS) if js.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All 3 anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for o, n in PAIRS:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.79.0"', '"3.79.1"'))
    print("  duty_board.js: handlers bound on $dw (drawer)")
    print("wrote __init__.py -> 3.79.1")


if __name__ == "__main__":
    main()
