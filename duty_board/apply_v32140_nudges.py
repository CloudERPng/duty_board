#!/usr/bin/env python3
"""Duty Board v3.214.0 — NUDGES: due dates that do something.

v3.211.0 gave the client administrator due dates and v3.213.0 gave them the
whole catalogue, but nothing in the system ever looked at a due date again.
Self-paced corporate training is famous for poor completion, and with the
facilitator gone there is no forcing event at all — the deadline was decoration.

Two lanes, both daily, both quiet by design.

  The due lane. Three days before, on the day, the day after, and weekly
  thereafter while it stays open. Four moments, not a drip.

  The dormant lane. A course assigned fourteen days ago with no due date and
  not one lesson ever opened gets exactly one nudge, ever. This is the lane
  that catches the real failure mode of self-serve: not lateness, but silence.

Escalation is weekly and aggregated, never per record: on Monday each room's
administrators get one message naming who is overdue and who has not started.
Chasing staff is their job; our job is to make sure they know.

  Duty Training Record: +last_nudge_on, +nudge_count — no record is nudged
    twice in a day whatever the lanes say, and the dormant lane fires only at
    a count of zero.
  Duty Settings: +academy_nudges_off — one switch to stop all of it.

Frozen and non-Active rooms are skipped entirely: a client whose renewal has
lapsed should not be chased about training.

Install the schedule once after deploying:
  bench --site xlevel.clouderp.one execute duty_board.academy.setup_academy_jobs

Deploy: apply -> bench migrate (new fields) -> bench build --app duty_board ->
clear-cache -> restart -> run the installer above. Anchored, idempotent.
Requires v3.213.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
ACAD = "duty_board/academy.py"
TRDT = "duty_board/duty_board/doctype/duty_training_record/duty_training_record.json"
DSDT = "duty_board/duty_board/doctype/duty_settings/duty_settings.json"
CHECK_ONLY = "--check" in sys.argv


NUDGE_OLD = '''@frappe.whitelist()
def order_decline(name, reason=None):'''

NUDGE_NEW = '''# ---------------- nudges: the cadence that replaces a facilitator ----------------

NUDGE_REPEAT_DAYS = 7
DORMANT_AFTER_DAYS = 14


def _nudges_enabled():
\treturn not cint(_settings().get("academy_nudges_off"))


def _active_rooms():
\treturn {
\t\tr.name for r in frappe.get_all(
\t\t\t"Client Room", filters={"status": "Active"}, fields=["name"]
\t\t)
\t}


def _ever_opened(user, module):
\treturn bool(
\t\tfrappe.db.exists("Duty Lesson Progress", {"user": user, "module": module})
\t)


def _due_lane(rec, today_d):
\t"""Which of the four moments this record is standing on, if any.
\tReturns a short reason string or None."""
\tif not rec.due_on:
\t\treturn None
\tdue = getdate(rec.due_on)
\tgap = (due - today_d).days
\tlast = getdate(rec.last_nudge_on) if rec.last_nudge_on else None
\tif gap == 3:
\t\treturn "due in three days"
\tif gap == 0:
\t\treturn "due today"
\tif gap == -1:
\t\treturn "overdue since yesterday"
\tif gap < -1:
\t\t# weekly thereafter, counted from the last nudge rather than the due date
\t\tif not last or (today_d - last).days >= NUDGE_REPEAT_DAYS:
\t\t\treturn "overdue by {0} days".format(abs(gap))
\treturn None


def training_nudges():
\t"""Daily. bench execute duty_board.academy.training_nudges

\tOne message per learner per day at most, however many courses qualify."""
\tif not _nudges_enabled():
\t\treturn {"skipped": "nudges are switched off in Duty Settings"}
\trooms = _active_rooms()
\tif not rooms:
\t\treturn {"sent": 0}
\ttoday_d = getdate(today())
\trecs = frappe.get_all(
\t\t"Duty Training Record",
\t\tfilters={"status": ["!=", "Completed"], "room": ["in", list(rooms)]},
\t\tfields=["name", "room", "module", "trainee", "trainee_name", "due_on",
\t\t\t\t"last_nudge_on", "nudge_count", "creation"],
\t)
\tby_user = {}
\tfor r in recs:
\t\tif r.last_nudge_on and getdate(r.last_nudge_on) == today_d:
\t\t\tcontinue  # never twice in a day, whatever the lanes say
\t\treason = _due_lane(r, today_d)
\t\tif not reason and not r.due_on and not cint(r.nudge_count):
\t\t\tage = (today_d - getdate(r.creation)).days
\t\t\tif age >= DORMANT_AFTER_DAYS and not _ever_opened(r.trainee, r.module):
\t\t\t\treason = "not started"
\t\tif reason:
\t\t\tby_user.setdefault(r.trainee, []).append((r, reason))
\tsent = 0
\tfor user, rows in by_user.items():
\t\ttitles = {
\t\t\tm.name: m.title for m in frappe.get_all(
\t\t\t\t"Duty Training Module",
\t\t\t\tfilters={"name": ["in", [r.module for r, _x in rows]]},
\t\t\t\tfields=["name", "title"],
\t\t\t)
\t\t}
\t\tlines = "".join(
\t\t\t"<li><b>{0}</b> &mdash; {1}</li>".format(
\t\t\t\tfrappe.utils.escape_html(titles.get(r.module, r.module)), reason
\t\t\t)
\t\t\tfor r, reason in rows
\t\t)
\t\ttry:
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
\t\tsent += 1
\tfrappe.db.commit()
\treturn {"sent": sent, "records": sum(len(v) for v in by_user.values())}


def training_admin_digest():
\t"""Weekly. bench execute duty_board.academy.training_admin_digest

\tOne aggregated message per room to its administrators. Never per record —
\ta digest that arrives every day is a digest nobody reads."""
\tif not _nudges_enabled():
\t\treturn {"skipped": "nudges are switched off in Duty Settings"}
\ttoday_d = getdate(today())
\tsent = 0
\tfor room in _active_rooms():
\t\trecs = frappe.get_all(
\t\t\t"Duty Training Record",
\t\t\tfilters={"room": room, "status": ["!=", "Completed"]},
\t\t\tfields=["module", "trainee", "trainee_name", "due_on", "creation"],
\t\t)
\t\tif not recs:
\t\t\tcontinue
\t\tlate, idle = {}, {}
\t\tfor r in recs:
\t\t\twho = r.trainee_name or frappe.utils.get_fullname(r.trainee)
\t\t\tif r.due_on and getdate(r.due_on) < today_d:
\t\t\t\tlate[who] = late.get(who, 0) + 1
\t\t\telif (today_d - getdate(r.creation)).days >= DORMANT_AFTER_DAYS and not _ever_opened(
\t\t\t\tr.trainee, r.module
\t\t\t):
\t\t\t\tidle[who] = idle.get(who, 0) + 1
\t\tif not late and not idle:
\t\t\tcontinue
\t\tadmins = [
\t\t\tm.user for m in frappe.get_all(
\t\t\t\t"Client Room Member",
\t\t\t\tfilters={"room": room, "active": 1, "is_admin": 1},
\t\t\t\tfields=["user"],
\t\t\t) if m.user
\t\t]
\t\tif not admins:
\t\t\tcontinue
\t\tblock = ""
\t\tif late:
\t\t\tblock += "<p><b>Past their due date</b></p><ul>" + "".join(
\t\t\t\t"<li>{0} &mdash; {1} course(s)</li>".format(frappe.utils.escape_html(k), v)
\t\t\t\tfor k, v in sorted(late.items(), key=lambda kv: -kv[1])
\t\t\t) + "</ul>"
\t\tif idle:
\t\t\tblock += "<p><b>Assigned but never started</b></p><ul>" + "".join(
\t\t\t\t"<li>{0} &mdash; {1} course(s)</li>".format(frappe.utils.escape_html(k), v)
\t\t\t\tfor k, v in sorted(idle.items(), key=lambda kv: -kv[1])
\t\t\t) + "</ul>"
\t\ttry:
\t\t\tfrappe.sendmail(
\t\t\t\trecipients=admins,
\t\t\t\tsubject=_("Training status — {0} person(s) need a word").format(
\t\t\t\t\tlen(set(list(late) + list(idle)))
\t\t\t\t),
\t\t\t\tmessage="""<p>Your team's training this week:</p>
{block}
<p>The full picture, and the Remind button, are on the Training tab of your portal.</p>
<p>&mdash; CloudERP.One Academy</p>""".format(block=block),
\t\t\t)
\t\t\tsent += 1
\t\texcept Exception:
\t\t\tfrappe.log_error(frappe.get_traceback(), "duty_board training digest")
\treturn {"rooms": sent}


def setup_academy_jobs():
\t"""bench execute duty_board.academy.setup_academy_jobs
\tCreates or repairs the Scheduled Job Type records. Times are SERVER time;
\tadjust the cron in the Scheduled Job Type list at will."""
\tjobs = [
\t\t("duty_board.academy.training_nudges", "0 7 * * *"),
\t\t("duty_board.academy.training_admin_digest", "0 8 * * 1"),
\t]
\tmade = []
\tfor method, cron in jobs:
\t\tname = frappe.db.get_value("Scheduled Job Type", {"method": method})
\t\tif name:
\t\t\tfrappe.db.set_value(
\t\t\t\t"Scheduled Job Type", name,
\t\t\t\t{"frequency": "Cron", "cron_format": cron, "stopped": 0},
\t\t\t)
\t\t\tmade.append("repaired " + method)
\t\telse:
\t\t\tfrappe.get_doc({
\t\t\t\t"doctype": "Scheduled Job Type",
\t\t\t\t"method": method,
\t\t\t\t"frequency": "Cron",
\t\t\t\t"cron_format": cron,
\t\t\t\t"stopped": 0,
\t\t\t}).insert(ignore_permissions=True)
\t\t\tmade.append("created " + method)
\tfrappe.db.commit()
\treturn made


@frappe.whitelist()
def order_decline(name, reason=None):'''


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = json.load(f)
    added = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        added = True
    if added:
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, ACAD):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def training_nudges(" in files[ACAD]:
        print("Already applied. Nothing to do.")
        return
    if '"3.213.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.213.0.")

    edits = [(ACAD, NUDGE_OLD, NUDGE_NEW, "nudge lanes + digest + job installer")]
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

    add_fields(os.path.join(root, TRDT), [
        {"fieldname": "last_nudge_on", "fieldtype": "Date", "label": "Last Nudge On", "read_only": 1},
        {"fieldname": "nudge_count", "fieldtype": "Int", "label": "Nudge Count", "read_only": 1},
    ])
    add_fields(os.path.join(root, DSDT), [
        {"fieldname": "academy_nudges_off", "fieldtype": "Check", "label": "Stop Academy Nudges"},
    ])
    print("  Duty Training Record +last_nudge_on/+nudge_count; Duty Settings +academy_nudges_off")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    with io.open(os.path.join(root, ACAD), "w", encoding="utf-8") as f:
        f.write(files[ACAD])
    print("  academy.py: due lane, dormant lane, weekly admin digest, job installer")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.213.0"', '"3.214.0"'))
    print("wrote __init__.py -> 3.214.0")


if __name__ == "__main__":
    main()
