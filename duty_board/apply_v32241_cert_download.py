#!/usr/bin/env python3
"""Duty Board v3.224.1 — HOTFIX: certificate downloads returned nothing.

Found by the Chunk A audit rather than by a user, which is the point of doing
it: _serve_file builds and returns a real werkzeug Response, and every caller
in the file returns it — except the two certificate endpoints, which call
_serve_certificate and throw the result away.

    def client_certificate_file(serial):
        _learning_room()
        _serve_certificate(serial)      # <- result discarded

So the permission checks ran, the file was fetched, the Response was
constructed, and then the endpoint returned None. Both the learner's
"Download PDF" on their certificate and the staff equivalent were affected.

This is the failure mode worth noticing: nothing errors. No traceback, no log
line, no failed permission. The button simply does nothing, which a user
reports as "the download doesn't work" months later, if at all — and there are
two other download paths beside it that DO work, so it looks like an
intermittent browser problem rather than a bug.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart.
No schema. Anchored, idempotent. Requires v3.224.0.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
CHECK_ONLY = "--check" in sys.argv


A_OLD = '''def my_certificate_file(serial):
\t_staff_only()
\t_serve_certificate(serial)'''
A_NEW = '''def my_certificate_file(serial):
\t_staff_only()
\treturn _serve_certificate(serial)'''

B_OLD = '''def client_certificate_file(serial):
\t_learning_room()
\t_serve_certificate(serial)'''
B_NEW = '''def client_certificate_file(serial):
\t_learning_room()
\treturn _serve_certificate(serial)'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "return _serve_certificate(serial)" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.224.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.224.0.")

    edits = [(A_OLD, A_NEW, "staff certificate download"),
             (B_OLD, B_NEW, "client certificate download")]
    problems = []
    for old, _new, label in edits:
        n = files[CR].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for old, new, _label in edits:
        files[CR] = files[CR].replace(old, new, 1)
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(files[CR])
    print("  client_room.py: both certificate endpoints return the response")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.224.0"', '"3.224.1"'))
    print("wrote __init__.py -> 3.224.1")


if __name__ == "__main__":
    main()
