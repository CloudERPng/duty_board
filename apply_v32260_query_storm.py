#!/usr/bin/env python3
"""Duty Board v3.226.0 — AUDIT CHUNK D: the query storm I introduced.

_quiz_state costs four queries. v3.218.0 called it once per training record to
work out who is blocked, and v3.219.0's academy.health() then did that for
every active room in one request.

  one room, 500 open records      2,000 queries for a single screen
  health() across 20 such rooms  40,000 queries in one request

That is not a slow page, it is a timeout — and it would have arrived exactly
when the academy started working, because the number scales with learners.

Everything needed was already fetchable in bulk. _blocked_map does it in two
queries and the arithmetic in memory, honouring per-record granted attempts and
treating an unlimited-attempt module as never blocked, which is the same rule
_quiz_state applies. Both callers now use it.

The stalled check in _room_health had the same shape — one exists() per record
asking whether a learner had ever opened a chapter — and is now one query.

  after: two queries per room regardless of size, plus one for stalled.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart.
No schema. Anchored, idempotent. Requires v3.225.1.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
ACAD = "duty_board/academy.py"
CHECK_ONLY = "--check" in sys.argv


ROWS_OLD = '\ttoday_d = getdate(today())\n\tfor r in recs:\n\t\tr["title"] = titles.get(r.module, r.module)\n\t\tr["overdue"] = bool(\n\t\t\tr.due_on and r.status != "Completed" and getdate(r.due_on) < today_d\n\t\t)\n\t\tr["blocked"] = False\n\t\tif r.status != "Completed":\n\t\t\tst = _quiz_state(r.module, r.trainee, r.name)\n\t\t\tr["blocked"] = bool(not st["passed"] and st["attempts_left"] == 0)\n\t# per-course detail, so an administrator can see WHERE somebody stopped\n\t# rather than only that they have not finished\n\tmods = list({r.module for r in recs})'

ROWS_NEW = '\ttoday_d = getdate(today())\n\tblocked = _blocked_map(recs)\n\tfor r in recs:\n\t\tr["title"] = titles.get(r.module, r.module)\n\t\tr["overdue"] = bool(\n\t\t\tr.due_on and r.status != "Completed" and getdate(r.due_on) < today_d\n\t\t)\n\t\tr["blocked"] = blocked.get(r.name, False)\n\t# per-course detail, so an administrator can see WHERE somebody stopped\n\t# rather than only that they have not finished\n\tmods = list({r.module for r in recs})'

HELPER_OLD = 'def _admin_rows(room):'

HELPER_NEW = 'def _blocked_map(recs):\n\t"""Which of these training records have run out of exam attempts.\n\n\tThis used to call _quiz_state once per record, and _quiz_state costs four\n\tqueries. On a five-hundred-record room that is two thousand queries for one\n\tscreen, and academy.health() does it for every active room at once — forty\n\tthousand queries in a single request, which is a timeout rather than a slow\n\tpage. Everything needed is fetchable in two queries and computed in memory."""\n\topen_recs = [r for r in recs if r.get("status") != "Completed"]\n\tif not open_recs:\n\t\treturn {}\n\tpolicies = {\n\t\tm.name: m\n\t\tfor m in frappe.get_all(\n\t\t\t"Duty Training Module",\n\t\t\tfilters={"name": ["in", list({r.module for r in open_recs})]},\n\t\t\tfields=["name", "max_attempts"],\n\t\t)\n\t}\n\tattempts = {}\n\tfor a in frappe.get_all(\n\t\t"Duty Quiz Attempt",\n\t\tfilters={"record": ["in", [r.name for r in open_recs]], "finished_at": ["is", "set"]},\n\t\tfields=["record", "passed"],\n\t):\n\t\tcur = attempts.setdefault(a.record, {"n": 0, "passed": False})\n\t\tcur["n"] += 1\n\t\tif cint(a.passed):\n\t\t\tcur["passed"] = True\n\tout = {}\n\tfor r in open_recs:\n\t\tcap = cint((policies.get(r.module) or {}).get("max_attempts"))\n\t\tif not cap:\n\t\t\tcontinue                      # unlimited attempts: never blocked\n\t\tcap += cint(r.get("extra_attempts"))\n\t\tst = attempts.get(r.name, {"n": 0, "passed": False})\n\t\tout[r.name] = bool(not st["passed"] and st["n"] >= cap)\n\treturn out\n\n\ndef _admin_rows(room):'

FIELDS_OLD = '\t\tfields=["name", "module", "trainee", "trainee_name", "status", "due_on", "completed_on"],\n\t) if users else []'

FIELDS_NEW = '\t\tfields=["name", "module", "trainee", "trainee_name", "status", "due_on",\n\t\t\t\t"completed_on", "extra_attempts"],\n\t) if users else []'

AC_OLD = '\tfor r in open_recs:\n\t\ttry:\n\t\t\tfrom duty_board.client_room import _quiz_state\n\n\t\t\tst = _quiz_state(r.module, r.trainee, r.name)\n\t\t\tif not st["passed"] and st["attempts_left"] == 0:\n\t\t\t\tblocked += 1\n\t\texcept Exception:\n\t\t\tcontinue'

AC_NEW = '\ttry:\n\t\tfrom duty_board.client_room import _blocked_map\n\n\t\tblocked = sum(1 for v in _blocked_map(recs).values() if v)\n\texcept Exception:\n\t\tfrappe.log_error(frappe.get_traceback(), "duty_board health blocked")'

AC_FIELDS_OLD = '\t\tfields=["name", "module", "trainee", "trainee_name", "status", "due_on", "creation"],\n\t)'

AC_FIELDS_NEW = '\t\tfields=["name", "module", "trainee", "trainee_name", "status", "due_on",\n\t\t\t\t"creation", "extra_attempts"],\n\t)'

ST_OLD = '\tfor r in open_recs:\n\t\tif r.due_on and getdate(r.due_on) < today_d:\n\t\t\toverdue += 1\n\t\tif (today_d - getdate(r.creation)).days >= DORMANT_AFTER_DAYS and not frappe.db.exists(\n\t\t\t"Duty Lesson Progress", {"user": r.trainee, "module": r.module}\n\t\t):\n\t\t\tstalled += 1'

ST_NEW = '\topened = {\n\t\t(p.user, p.module)\n\t\tfor p in frappe.get_all(\n\t\t\t"Duty Lesson Progress",\n\t\t\tfilters={"module": ["in", list({r.module for r in open_recs}) or [""]]},\n\t\t\tfields=["user", "module"],\n\t\t)\n\t} if open_recs else set()\n\tfor r in open_recs:\n\t\tif r.due_on and getdate(r.due_on) < today_d:\n\t\t\toverdue += 1\n\t\tif (today_d - getdate(r.creation)).days >= DORMANT_AFTER_DAYS and (\n\t\t\tr.trainee, r.module\n\t\t) not in opened:\n\t\t\tstalled += 1'


DIV_OLD = '\tscore = round(score_n * 100 / len(served))'

DIV_NEW = '\t# A corrupt or emptied served list would divide by zero here, which the\n\t# learner would meet as a 500 straight after sitting the paper, with the\n\t# attempt already consumed. Fail to a zero instead.\n\tscore = round(score_n * 100 / len(served)) if served else 0'



EDITS = [
    (CR, HELPER_OLD, HELPER_NEW, "_blocked_map"),
    (CR, FIELDS_OLD, FIELDS_NEW, "fetch extra_attempts"),
    (CR, ROWS_OLD, ROWS_NEW, "admin rows use the map"),
    (CR, DIV_OLD, DIV_NEW, "guard the score division"),
    (ACAD, AC_FIELDS_OLD, AC_FIELDS_NEW, "health fetches extra_attempts"),
    (ACAD, ST_OLD, ST_NEW, "stalled check batched"),
    (ACAD, AC_OLD, AC_NEW, "health uses the map"),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, ACAD):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _blocked_map(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.225.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.225.1.")

    problems = []
    for f, old, _new, label in EDITS:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(EDITS))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for f, old, new, _label in EDITS:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, ACAD):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: _blocked_map, batched")
    print("  academy.py: health uses it, stalled check batched")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.225.1"', '"3.226.0"'))
    print("wrote __init__.py -> 3.226.0")


if __name__ == "__main__":
    main()
