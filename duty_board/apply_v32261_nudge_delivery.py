#!/usr/bin/env python3
"""Duty Board v3.226.1 — AUDIT CHUNK F: a reminder recorded but never sent.

training_nudges wraps the email in try/except and the in-app notification in
another, which is right — one bad address must not abort a batch. It then
stamps last_nudge_on and increments nudge_count regardless of whether either
succeeded.

So a learner whose address bounces is marked as reminded, drops out of the
seven-day repeat window, and is never chased again — and nothing anywhere says
so. It is the same silent-failure shape as the certificate download and the
"never signed in" flag: no error, no log line, just a person quietly stopping
being served.

Now the stamp only happens if at least one channel got through, and a total
failure is logged with the learner's address so it appears in the error log
rather than nowhere. An undelivered reminder is retried the next day, which is
the correct behaviour: the point of the cadence is that somebody hears it.

The rest of Chunk F came back clean — all 20 scheduled and hooked method paths
resolve, no sendmail sits unprotected inside a loop, all four synchronous sends
are wrapped, and there are no bare excepts in the app.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart.
No schema. Anchored, idempotent. Requires v3.226.0.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
ACAD = "duty_board/academy.py"
CHECK_ONLY = "--check" in sys.argv


OLD = '''\t\ttry:
\t\t\tfrappe.sendmail(
\t\t\t\trecipients=[user],
\t\t\t\tsubject=_("Your training — {0} course(s) need attention").format(len(rows)),
\t\t\t\tmessage="""<p>A quiet reminder about your training:</p>
<ul>{lines}</ul>
<p>Open the portal, go to Training, and pick up where you left off.</p>
<p>&mdash; CloudERP.One Academy</p>""".format(lines=lines),
\t\t\t)
\t\texcept Exception:
\t\t\tfrappe.log_error(frappe.get_traceback(), "duty_board training nudge email")
\t\ttry:
\t\t\tfrom duty_board.api import _notify_user

\t\t\t_notify_user(
\t\t\t\tuser, _("🎓 Training reminder"),
\t\t\t\t_("{0} course(s) need your attention").format(len(rows)),
\t\t\t)
\t\texcept Exception:
\t\t\tpass
\t\tfor r, _reason in rows:
\t\t\tfrappe.db.set_value(
\t\t\t\t"Duty Training Record", r.name,
\t\t\t\t{"last_nudge_on": today_d, "nudge_count": cint(r.nudge_count) + 1},
\t\t\t\tupdate_modified=False,
\t\t\t)
\t\tsent += 1'''

NEW = '''\t\tdelivered = False
\t\ttry:
\t\t\tfrappe.sendmail(
\t\t\t\trecipients=[user],
\t\t\t\tsubject=_("Your training — {0} course(s) need attention").format(len(rows)),
\t\t\t\tmessage="""<p>A quiet reminder about your training:</p>
<ul>{lines}</ul>
<p>Open the portal, go to Training, and pick up where you left off.</p>
<p>&mdash; CloudERP.One Academy</p>""".format(lines=lines),
\t\t\t)
\t\t\tdelivered = True
\t\texcept Exception:
\t\t\tfrappe.log_error(frappe.get_traceback(), "duty_board training nudge email")
\t\ttry:
\t\t\tfrom duty_board.api import _notify_user

\t\t\t_notify_user(
\t\t\t\tuser, _("🎓 Training reminder"),
\t\t\t\t_("{0} course(s) need your attention").format(len(rows)),
\t\t\t)
\t\t\tdelivered = True
\t\texcept Exception:
\t\t\tpass
\t\tif not delivered:
\t\t\t# Stamping now would drop this learner out of the seven-day repeat
\t\t\t# window for a reminder nobody received. Leave the record untouched
\t\t\t# so tomorrow's run tries again, and say so somewhere visible.
\t\t\tfrappe.log_error(
\t\t\t\t"No channel reached %s — reminder not recorded, will retry" % user,
\t\t\t\t"duty_board training nudge undelivered",
\t\t\t)
\t\t\tcontinue
\t\tfor r, _reason in rows:
\t\t\tfrappe.db.set_value(
\t\t\t\t"Duty Training Record", r.name,
\t\t\t\t{"last_nudge_on": today_d, "nudge_count": cint(r.nudge_count) + 1},
\t\t\t\tupdate_modified=False,
\t\t\t)
\t\tsent += 1'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, ACAD):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "delivered = False" in files[ACAD]:
        print("Already applied. Nothing to do.")
        return
    if '"3.226.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.226.0.")

    n = files[ACAD].count(OLD)
    if n != 1:
        sys.exit("ABORT - anchor matched %d times, expected 1." % n)
    print("All 1 anchors matched exactly once.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    files[ACAD] = files[ACAD].replace(OLD, NEW, 1)
    with io.open(os.path.join(root, ACAD), "w", encoding="utf-8") as f:
        f.write(files[ACAD])
    print("  academy.py: a reminder is only recorded once a channel got through")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.226.0"', '"3.226.1"'))
    print("wrote __init__.py -> 3.226.1")


if __name__ == "__main__":
    main()
