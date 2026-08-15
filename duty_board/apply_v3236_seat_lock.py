#!/usr/bin/env python3
"""Duty Board v3.236.0 — SEAT GATE CONCURRENCY.

seat_gate reads the entitlement and the seats used, decides, and returns; the
caller then writes the training records. Nothing serialises the two, so two
administrators assigning the last seat at the same moment both read "1 left",
both pass, and both write. The client receives two seats for one paid, no error
is raised, and nothing in the system ever notices — the count is derived from
the records, so it simply reads 2 of 1 afterwards.

The same shape covers a learner self-starting a paid track while an
administrator assigns, which is the likelier real-world version.

The fix is a row lock rather than a rewrite. Before reading anything, take
SELECT ... FOR UPDATE on that room and track's entitlement rows. A second
transaction attempting the same room and track blocks until the first commits,
then re-reads the true count and fails honestly if the seat has gone.

Three properties that make this safe here:

  - gate and write already share one transaction. The commit in
    client_assign_track sits after the inserts, so the lock is still held when
    the records are created. Verified before writing this patch.
  - the lock is per room and track, so assignments to different clients or
    different tracks never block each other.
  - it is taken only for Paid tracks with new learners, which is the only path
    where a seat can be consumed. Free and Included tracks return before the
    lock is reached and are unaffected.

Where no entitlement row exists there is nothing to lock, and nothing to race:
the gate throws "not purchased" regardless of ordering.

Deploy: apply -> clear-cache -> restart. No schema change. Requires v3.235.0.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
ACADEMY = "duty_board/academy.py"
CHECK_ONLY = "--check" in sys.argv

OLD = '''	ent = entitlement_for(room, track)
	if not ent["seats"]:'''

NEW = '''	_lock_seats(room, track)
	ent = entitlement_for(room, track)
	if not ent["seats"]:'''

HELPER_ANCHOR = '''def seat_gate(room, track, new_learners):'''

HELPER = '''def _lock_seats(room, track):
	"""Serialise seat checking for one room and track.

	seat_gate reads the entitlement and the seats used, decides, and returns —
	the caller then writes the training records. Without a lock, two
	administrators assigning the last seat at the same moment both read one
	left, both pass, and both write: two seats consumed against one paid, with
	no error anywhere. The count is derived from the records, so afterwards it
	simply reads 2 of 1.

	Locking the entitlement rows makes the second transaction wait for the
	first to commit, after which it re-reads the true count and fails honestly.

	Scope is deliberately narrow. Only this room and this track are locked, so
	unrelated assignments never block, and it is reached only for Paid tracks
	with new learners. Where no entitlement row exists there is nothing to lock
	and nothing to race: the gate throws "not purchased" whatever the ordering.
	"""
	frappe.db.sql(
		"""select name from `tabDuty Academy Entitlement`
		   where room = %s and track = %s for update""",
		(room, track),
	)


def seat_gate(room, track, new_learners):'''


def main():
    root = os.getcwd()
    read = lambda p: io.open(os.path.join(root, p), encoding="utf-8").read()

    init = read(INIT)
    academy = read(ACADEMY)

    if "_lock_seats" in academy:
        print("Already applied. Nothing to do.")
        return
    if '"3.235.0"' not in init:
        sys.exit("ABORT: not at v3.235.0.")

    problems = []
    for label, anchor in (("gate read", OLD), ("helper insertion point", HELPER_ANCHOR)):
        n = academy.count(anchor)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))

    # the guarantee this patch rests on: no commit between gate and write
    room_py = read("duty_board/client_room.py")
    seg = room_py.split("seat_gate(room.name, track, len(fresh))", 1)
    if len(seg) == 2:
        after = seg[1].split("frappe.db.commit()", 1)[0]
        if "insert(" not in after:
            problems.append("  client_assign_track appears to commit before writing —"
                            " the lock would be released too early")
    if problems:
        print("ABORT:")
        print("\n".join(problems))
        sys.exit(1)

    print("Anchors clean.")
    print("Verified: client_assign_track writes its records before committing,")
    print("so the lock is still held when the seats are consumed.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    academy = academy.replace(HELPER_ANCHOR, HELPER, 1)
    academy = academy.replace(OLD, NEW, 1)
    with io.open(os.path.join(root, ACADEMY), "w", encoding="utf-8") as f:
        f.write(academy)
    print("  academy.py: _lock_seats added and called before the read")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.235.0"', '"3.236.0"'))
    print("wrote __init__.py -> 3.236.0")


if __name__ == "__main__":
    main()
