#!/usr/bin/env python3
"""Duty Board v3.221.1 — HOTFIX: a published question named who asked it.

client_lesson_questions returned the asker's full name on every thread, so a
published answer showed the rest of the client's staff exactly who had not
understood the chapter. Olamide caught it before anyone shipped a question.

That is the failure that quietly kills the whole feature. A learner who thinks
their confusion will be displayed to colleagues under their own name does not
ask — they stall silently, which is the precise behaviour the questions were
built to prevent. And publishing was ticked by default, so it would have been
the normal case rather than the exception.

Now:
  - a learner's own thread reads "You", as before
  - a published thread from anyone else reads "A colleague asked", with no name
  - the timestamp is dropped on other people's threads too, because on a team
    of eight a date and time identifies somebody just as well as a name does

Staff still see the asker in the tutor queue, which is correct: they have to
answer the person, and the queue is not a place learners can reach.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.221.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


PY_OLD = '''\t\t\t"who": frappe.utils.get_fullname(r.asked_by) if not mine else _("You"),
\t\t\t"asked_on": str(r.asked_on)[:16] if r.asked_on else None,'''

PY_NEW = '''\t\t\t# never name a colleague to a colleague: someone who believes their
\t\t\t# confusion will be published under their own name does not ask
\t\t\t"who": _("You") if mine else _("A colleague asked"),
\t\t\t"asked_on": (str(r.asked_on)[:16] if r.asked_on else None) if mine else None,'''

JS_OLD = '''\t\t\t<div class="qahead">${esc(q.who)}${q.asked_on ? ` <span class="qadt">${esc(q.asked_on)}</span>` : ""}${!q.mine && q.published ? `<span class="qatag">Answered for everyone</span>` : ""}</div>'''
JS_NEW = '''\t\t\t<div class="qahead">${esc(q.who)}${q.mine && q.asked_on ? ` <span class="qadt">${esc(q.asked_on)}</span>` : ""}${!q.mine ? `<span class="qatag">Answered for everyone</span>` : ""}</div>'''

FOOT_OLD = '''\t\t\t<p class="askfoot">Your question stays with this lesson. We will answer here and email you when we do.</p>'''
FOOT_NEW = '''\t\t\t<p class="askfoot">Your question stays with this lesson. We will answer here and email you when we do. If the answer would help others we may show it on this lesson \u2014 without your name.</p>'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if '_("A colleague asked")' in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.221.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.221.0.")

    edits = [
        (CR, PY_OLD, PY_NEW, "anonymise other learners"),
        (PORTAL, JS_OLD, JS_NEW, "thread header"),
        (PORTAL, FOOT_OLD, FOOT_NEW, "say so when asking"),
    ]
    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
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

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: published threads carry no asker identity")
    print("  portal.html: header and the promise made when asking")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.221.0"', '"3.221.1"'))
    print("wrote __init__.py -> 3.221.1")


if __name__ == "__main__":
    main()
