#!/usr/bin/env python3
"""Duty Board v3.226.3 — the test suite was red, and the tests were wrong.

62 tests, 5 failing. Every failing area last changed on 5-6 August, so none of
today's twenty releases caused them: the suite had simply drifted behind the
code and nobody had run it.

That is its own finding. A permanently red suite is worse than no suite,
because it teaches everyone to ignore a failure — including the one that
matters.

All five were stale expectations, not defects:

  join password    v3.58.0 removed guest-chosen credentials on purpose; the
                   test still passed password=. The behaviour it actually
                   asserts, an account created disabled, still holds.
  room unread      v3.57.0 made _room_unread return {total, client, other};
                   the test compared the dict to an int.
  staff workload   staff_workload omits Administrator by design and the suite
                   runs as Administrator, so next(... == me) could never match.
                   This test cannot ever have passed as written.
  meeting caps     the rule counts meetings SCHEDULED on the target date; the
                   test seeded one on the 5th and probed the 6th.
  meeting ics      the SUMMARY line is the bare topic; the test expected an
                   "Xlevel meeting: " prefix that no longer exists.

ONE DESIGN QUESTION LEFT OPEN, deliberately not changed here. In
_meeting_caps_check the daily rule counts by meeting_date while the weekly rule
counts by creation. So three meetings booked today for December exhaust the
week, and one booked per week for twelve weeks never does. The error messages
match the daily reading; the docstring says "1 request/day", which matches the
weekly one. Worth settling which you mean before anyone relies on it.

Deploy: apply, then re-run:
  bench --site xlevel.clouderp.one run-tests --app duty_board
Anchored, idempotent. Requires v3.226.2.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
T = "duty_board/tests/test_core.py"
CHECK_ONLY = "--check" in sys.argv


T1_OLD = '\t\tclient_room.submit_join_request(token, "PW Client", email, password="secret123!")'

T1_NEW = '\t\t# v3.58.0 removed guest-chosen credentials deliberately: the account is\n\t\t# created disabled and the approval email carries the only set-password link.\n\t\tclient_room.submit_join_request(token, "PW Client", email)'

T2_OLD = '\t\tcount = client_room._room_unread(room, "someone.else@example.com")\n\t\tself.assertGreaterEqual(count, 1)\n\t\t# the author has effectively seen their own message\n\t\tself.assertEqual(client_room._room_unread(room, frappe.session.user), 0)'

T2_NEW = '\t\t# v3.57.0 made this a breakdown: {"total", "client", "other"}\n\t\tcount = client_room._room_unread(room, "someone.else@example.com")\n\t\tself.assertGreaterEqual(count["total"], 1)\n\t\t# the author has effectively seen their own message\n\t\tself.assertEqual(client_room._room_unread(room, frappe.session.user)["total"], 0)'

T3_OLD = '\t\tme = frappe.session.user\n\t\tbefore = api.skill_add(me, "UnitTestSkillZ")'

T3_NEW = '\t\t# staff_workload deliberately omits Administrator and Guest, and the suite\n\t\t# runs as Administrator — so exercise it against a real staff row.\n\t\troster = api.staff_workload()\n\t\tif not roster:\n\t\t\tself.skipTest("no non-Administrator staff on this site")\n\t\tme = roster[0]["user"]\n\t\tbefore = api.skill_add(me, "UnitTestSkillZ")'

T4_OLD = '\t\t\t"topic": "today probe", "meeting_date": "2026-08-05",'

T4_NEW = '\t\t\t"topic": "today probe", "meeting_date": "2026-08-06",'

T5_OLD = '\t\t\tclient_room._meeting_caps_check(room2, [], "2026-08-06")'

T5_NEW = '\t\t\t# the rule is one meeting per DATE, so probe the date that is taken\n\t\t\tclient_room._meeting_caps_check(room2, [], "2026-08-06")'

T6_OLD = '\t\tself.assertIn("SUMMARY:Xlevel meeting: ics test", ics)'

T6_NEW = '\t\tself.assertIn("SUMMARY:ics test", ics)'



EDITS = [(T1_OLD, T1_NEW, "join password"),
         (T2_OLD, T2_NEW, "room unread shape"),
         (T3_OLD, T3_NEW, "workload roster"),
         (T4_OLD, T4_NEW, "cap probe date"),
         (T5_OLD, T5_NEW, "cap probe comment"),
         (T6_OLD, T6_NEW, "ics summary")]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, T), encoding="utf-8") as f:
        t = f.read()

    if "roster = api.staff_workload()" in t:
        print("Already applied. Nothing to do.")
        return
    if '"3.226.2"' not in init:
        sys.exit("ABORT: not at v3.226.2.")

    problems = []
    for old, _new, label in EDITS:
        n = t.count(old)
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

    for old, new, _label in EDITS:
        t = t.replace(old, new, 1)
    with io.open(os.path.join(root, T), "w", encoding="utf-8") as f:
        f.write(t)
    print("  tests/test_core.py: five stale expectations corrected")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.226.2"', '"3.226.3"'))
    print("wrote __init__.py -> 3.226.3")


if __name__ == "__main__":
    main()
