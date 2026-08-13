#!/usr/bin/env python3
"""Duty Board v3.212.1 — HOTFIX: the portal api() helper could only reach one module.

v3.212.0 put the academy commerce endpoints in the new duty_board.academy
module, but the portal's api() helper hardcodes the method path as
"duty_board.client_room." + method. So api("academy_catalogue") resolved to
duty_board.client_room.academy_catalogue, which does not exist, and touching
Catalogue produced:

  Failed to get method for command duty_board.client_room.academy_catalogue
  with module 'duty_board.client_room' has no attribute 'academy_catalogue'

Two ways out. Re-exporting thin wrappers from client_room.py would have hidden
the real constraint and left the next new module with the same trap. Instead
api() now takes a full dotted path when one is given and keeps the client_room
shorthand otherwise, so every existing call site is untouched and any future
module is reachable.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> hard refresh. No schema. Anchored, idempotent.
Requires v3.212.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


API_OLD = '''const api = (method, args) =>
\tfetch("/api/method/duty_board.client_room." + method, {'''

API_NEW = '''const api = (method, args) =>
\t/* A bare name is a client_room endpoint (the overwhelming majority, and
\t   every call site written before v3.212.1). A dotted name is taken as a
\t   full path, so modules beyond client_room are reachable. */
\tfetch("/api/method/" + (method.indexOf(".") >= 0 ? method : "duty_board.client_room." + method), {'''

CAT_OLD = '''\tapi("academy_catalogue")'''
CAT_NEW = '''\tapi("duty_board.academy.academy_catalogue")'''

REQ_OLD = '''\t\tapi("academy_request", { track: track, seats: n, note: document.getElementById("seatnote").value || null })'''
REQ_NEW = '''\t\tapi("duty_board.academy.academy_request", { track: track, seats: n, note: document.getElementById("seatnote").value || null })'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if 'method.indexOf(".") >= 0' in files[PORTAL]:
        print("Already applied. Nothing to do.")
        return
    if '"3.212.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.212.0.")

    edits = [
        (PORTAL, API_OLD, API_NEW, "api() accepts a full path"),
        (PORTAL, CAT_OLD, CAT_NEW, "catalogue call"),
        (PORTAL, REQ_OLD, REQ_NEW, "seat request call"),
    ]
    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    with io.open(os.path.join(root, PORTAL), "w", encoding="utf-8") as f:
        f.write(files[PORTAL])
    print("  portal.html: api() path resolution + academy call sites")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.212.0"', '"3.212.1"'))
    print("wrote __init__.py -> 3.212.1")


if __name__ == "__main__":
    main()
