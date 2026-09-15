#!/usr/bin/env python3
"""Duty Board v3.218.1 — HOTFIX: "never signed in" was reading the wrong field.

v3.218.0 surfaced Client Room Member.last_seen as "last seen", and flagged an
empty value as "never signed in". That field is written in exactly one place —
client_get_room, the chat endpoint — so it does not mean "signed in", it means
"opened the message thread". An administrator who works in the Training tab and
never opens chat is reported as never having signed in, while looking at the
screen that says so.

A flag that is confidently wrong about the person reading it will make an
administrator distrust the whole roster, and the roster is how they decide whom
to chase.

Frappe already records this correctly on the User: last_active, and last_login
behind it. Both are maintained on every authenticated request regardless of
which tab somebody uses, and both are already populated for existing users — so
this is accurate the moment it deploys, with no backfill and no extra writes on
the request path.

Client Room Member.last_seen is left alone. It is still the right field for
"has this person read the room", which is what chat uses it for.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.218.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
CHECK_ONLY = "--check" in sys.argv


HELPER_OLD = '''@frappe.whitelist()
def client_admin_people():'''

HELPER_NEW = '''def _last_signed_in(users):
\t"""When each person was last actually in the portal.

\tRead from the User record rather than Client Room Member.last_seen: that
\tfield is stamped only by the chat endpoint, so it reports "never" for anyone
\twho works in Training and does not open the message thread. Frappe maintains
\tlast_active on every authenticated request, with last_login behind it."""
\tif not users:
\t\treturn {}
\tout = {}
\tfor u in frappe.get_all(
\t\t"User", filters={"name": ["in", list(users)]},
\t\tfields=["name", "last_active", "last_login"],
\t):
\t\tseen = u.last_active or u.last_login
\t\tout[u.name] = str(seen)[:16] if seen else None
\treturn out


@frappe.whitelist()
def client_admin_people():'''

PPL_OLD = '''\t\t\t"last_seen": str(m.last_seen) if m.last_seen else None,
\t\t})
\treturn out'''
PPL_NEW = '''\t\t\t"last_seen": seen.get(m.user),
\t\t})
\treturn out'''

PPL_SEEN_OLD = '''\tout = []
\tfor m in rows:
\t\tif not m.user:
\t\t\tcontinue
\t\tassigned = frappe.db.count(
\t\t\t"Duty Training Record", {"room": room.name, "trainee": m.user}
\t\t)'''
PPL_SEEN_NEW = '''\tseen = _last_signed_in([m.user for m in rows if m.user])
\tout = []
\tfor m in rows:
\t\tif not m.user:
\t\t\tcontinue
\t\tassigned = frappe.db.count(
\t\t\t"Duty Training Record", {"room": room.name, "trainee": m.user}
\t\t)'''

HOME_OLD = '''\tlast_seen = {
\t\tm.user: str(m.last_seen) if m.last_seen else None
\t\tfor m in frappe.get_all(
\t\t\t"Client Room Member", filters={"room": room.name, "active": 1},
\t\t\tfields=["user", "last_seen"],
\t\t)
\t}'''
HOME_NEW = '''\tlast_seen = _last_signed_in(users)'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _last_signed_in(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.218.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.218.0.")

    edits = [
        (HELPER_OLD, HELPER_NEW, "_last_signed_in"),
        (PPL_SEEN_OLD, PPL_SEEN_NEW, "people: resolve once"),
        (PPL_OLD, PPL_NEW, "people: use it"),
        (HOME_OLD, HOME_NEW, "dashboard: use it"),
    ]
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
    print("  client_room.py: last seen now read from the User login record")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.218.0"', '"3.218.1"'))
    print("wrote __init__.py -> 3.218.1")


if __name__ == "__main__":
    main()
