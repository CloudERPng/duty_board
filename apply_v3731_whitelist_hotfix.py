#!/usr/bin/env python3
"""Duty Board v3.73.1 — HOTFIX for v3.73.0.

The receipts patch inserted _touch_delivered anchored below
get_messages' @frappe.whitelist() decorator — so the decorator attached
to the helper instead: get_messages lost its whitelist (Method Not
Allowed on the chat face) and the internal helper was wrongly exposed.

Fix: decorator off the helper, back onto get_messages.

api.py only. bench restart (no build, no migrate).
Anchored, idempotent. Requires v3.73.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
API = "duty_board/api.py"
CHECK_ONLY = "--check" in sys.argv

A_OLD = '''@frappe.whitelist()
def _touch_delivered(user):'''
A_NEW = '''def _touch_delivered(user):'''

B_OLD = '''\t\tpass  # receipts must never break a poll


def get_messages(limit=50, before=None, after=None):'''
B_NEW = '''\t\tpass  # receipts must never break a poll


@frappe.whitelist()
def get_messages(limit=50, before=None, after=None):'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, API), encoding="utf-8") as f:
        api = f.read()

    if "@frappe.whitelist()\ndef get_messages(" in api:
        print("Already applied. Nothing to do.")
        return
    if '"3.73.0"' not in init:
        sys.exit("ABORT: not at v3.73.0.")
    if api.count(A_OLD) != 1 or api.count(B_OLD) != 1:
        sys.exit(f"ABORT: anchors [{api.count(A_OLD)}], [{api.count(B_OLD)}].")

    print("Anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    api = api.replace(A_OLD, A_NEW, 1).replace(B_OLD, B_NEW, 1)
    with io.open(os.path.join(root, API), "w", encoding="utf-8") as f:
        f.write(api)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.73.0"', '"3.73.1"'))
    print("  api.py: whitelist restored to get_messages, stripped from helper")
    print("wrote __init__.py -> 3.73.1")


if __name__ == "__main__":
    main()
