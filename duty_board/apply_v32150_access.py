#!/usr/bin/env python3
"""Duty Board v3.215.0 - PERPETUAL ACCESS, AND EXPIRY THAT SAYS SO.

Two things, both answering the same question: what exactly does a client keep?

1. Training survives a renewal freeze. Every client endpoint runs _renewal_gate,
   so a customer past their ERP renewal grace loses the whole portal - including
   training they bought seats for outright. Seats are a purchase, not a
   subscription. Worse, a pure academy client with no ERP subscription at all
   sits in the same gate.

   Reading, checks, assessments and certificates now resolve the room through
   _learning_room(), which passes allow_frozen. Chat, projects, tickets, the
   catalogue, seat orders and new assignment stay frozen - renewal pressure
   belongs where the money is owed, not on a learner mid-course.

2. Seat expiry stops hiding. _visible_tracks dropped a Paid track the moment
   its seats lapsed, so a learner part-way through watched it vanish with no
   explanation. An expired track a learner is already on now stays visible and
   carries a plain note: you keep what you started and any certificate you
   earned; new colleagues cannot be added until seats are renewed. The
   administrator's catalogue reports expired seats too, rather than silently
   offering the track as if it had never been bought.

Nothing here weakens a gate. Access to a course still requires a training
record, a certificate still requires having passed, and seats are still
enforced on every path that creates new learners.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.214.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
ACAD = "duty_board/academy.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


HELPER_OLD = 'def _visible_tracks(room, tracks, prods):'

HELPER_NEW = 'def _learning_room():\n\t"""The room, reachable even while the portal is frozen for renewal.\n\n\tThe principle: anything that CONSUMES what a client has already paid for\n\tstays open; anything that changes commercial state does not. Seats are a\n\tpurchase, not a subscription, so a late ERP invoice must not lock someone\n\tout of a course they bought or a certificate they earned. Chat, projects,\n\ttickets and new orders stay frozen, which is where renewal pressure belongs.\n\t"""\n\treturn _client_room(allow_frozen=True)\n\n\ndef _visible_tracks(room, tracks, prods, user=None):'

VIS_OLD = 'def _visible_tracks(room, tracks, prods):\n\t"""Included tracks come with the room\'s products, as they always have.\n\tPaid tracks appear only where seats have actually been bought."""\n\tfrom duty_board.academy import entitlement_for\n\n\tout = []\n\tfor t in tracks:\n\t\tif (t.get("access") or "Included") == "Paid":\n\t\t\tif entitlement_for(room.name, t.name)["seats"]:\n\t\t\t\tout.append(t)\n\t\t\tcontinue\n\t\tif (t.product or "").strip().lower() in prods:\n\t\t\tout.append(t)\n\treturn out\n'

VIS_NEW = 'def _visible_tracks(room, tracks, prods, user=None):\n\t"""Included tracks come with the room\'s products, as they always have.\n\tPaid tracks appear where seats have been bought — and STAY visible to a\n\tlearner already on them once those seats expire, flagged rather than\n\tvanished. Expiry stops new people joining; it never removes the course\n\tfrom under someone who is part-way through it."""\n\tfrom duty_board.academy import entitlement_for\n\n\tout = []\n\tfor t in tracks:\n\t\tif (t.get("access") or "Included") == "Paid":\n\t\t\tent = entitlement_for(room.name, t.name)\n\t\t\tif ent["seats"]:\n\t\t\t\tout.append(t)\n\t\t\telif ent["expired_seats"] and user and _on_track(room, user, t.name):\n\t\t\t\tt["seats_expired"] = 1\n\t\t\t\tout.append(t)\n\t\t\tcontinue\n\t\tif (t.product or "").strip().lower() in prods:\n\t\t\tout.append(t)\n\treturn out\n\n\ndef _on_track(room, user, track):\n\t"""Has this learner already been put on the track? Their access outlives\n\tthe seats that granted it."""\n\tmods = frappe.get_all(\n\t\t"Duty Certification Track Module", filters={"parent": track}, pluck="module"\n\t)\n\tif not mods:\n\t\treturn False\n\treturn bool(\n\t\tfrappe.db.exists(\n\t\t\t"Duty Training Record",\n\t\t\t{"room": room.name, "module": ["in", mods], "trainee": user},\n\t\t)\n\t)\n'

CALL_OLD = '\ttracks = _visible_tracks(room, tracks, prods)'

CALL_NEW = '\ttracks = _visible_tracks(room, tracks, prods, user)'

OUT_OLD = '\t\tout.append(\n\t\t\t{\n\t\t\t\t"name": t.name,\n\t\t\t\t"title": t.title,\n\t\t\t\t"product": t.product,\n\t\t\t\t"description": t.description,\n\t\t\t\t"modules": [titles.get(m, m) for m in mod_names],\n\t\t\t\t"total": len(mod_names),\n\t\t\t\t"pursuing": all(m in recs for m in mod_names),\n\t\t\t\t"done": done,\n\t\t\t\t"certified": bool(\n'

OUT_NEW = '\t\tout.append(\n\t\t\t{\n\t\t\t\t"name": t.name,\n\t\t\t\t"seats_expired": cint(t.get("seats_expired")),\n\t\t\t\t"title": t.title,\n\t\t\t\t"product": t.product,\n\t\t\t\t"description": t.description,\n\t\t\t\t"modules": [titles.get(m, m) for m in mod_names],\n\t\t\t\t"total": len(mod_names),\n\t\t\t\t"pursuing": all(m in recs for m in mod_names),\n\t\t\t\t"done": done,\n\t\t\t\t"certified": bool(\n'

CARD_OLD = '\t\t\t\t\t\t${t.certified\n\t\t\t\t\t\t\t? `<div class="lmsdone">Certified</div>`\n\t\t\t\t\t\t\t: t.pursuing\n\t\t\t\t\t\t\t\t? `<div class="lmsbar"><i style="width:${t.total ? Math.round((t.done / t.total) * 100) : 0}%"></i></div><div class="lmsmeta"><b>${t.done}</b> of ${t.total} courses complete</div>`\n\t\t\t\t\t\t\t\t: `<button class="lmscta" onclick="pursueTrack(\'${esc(t.name)}\')">Start this track</button>`}'

CARD_NEW = '\t\t\t\t\t\t${t.seats_expired ? `<div class="lmsexp">Your seats for this track have expired. You keep everything you have started, and any certificate you have earned. New colleagues cannot be added until seats are renewed.</div>` : ""}\n\t\t\t\t\t\t${t.certified\n\t\t\t\t\t\t\t? `<div class="lmsdone">Certified</div>`\n\t\t\t\t\t\t\t: t.pursuing\n\t\t\t\t\t\t\t\t? `<div class="lmsbar"><i style="width:${t.total ? Math.round((t.done / t.total) * 100) : 0}%"></i></div><div class="lmsmeta"><b>${t.done}</b> of ${t.total} courses complete</div>`\n\t\t\t\t\t\t\t\t: `<button class="lmscta" onclick="pursueTrack(\'${esc(t.name)}\')">Start this track</button>`}'

CAT_ENT = '\t\t\t"expires_on": ent["expires_on"] if ent else None,\n\t\t\t"pending": pending.name if pending else None,\n\t\t\t"pending_seats": pending.seats if pending else None,'

CAT_ENT_NEW = '\t\t\t"expires_on": ent["expires_on"] if ent else None,\n\t\t\t"pending": pending.name if pending else None,\n\t\t\t"seats_expired": ent["expired_seats"] if ent else 0,\n\t\t\t"pending_seats": pending.seats if pending else None,'

CSS_OLD = '\t.lmscard.cc { cursor: pointer; }'

CSS_NEW = '\t.lmscard.cc { cursor: pointer; }\n\t.lmsexp { font-size: 12px; line-height: 1.55; background: #FFF7E6; border: 1px solid #F3E0B5;\n\t\tcolor: #7A5312; border-radius: 9px; padding: 8px 11px; margin-top: 8px; }'

SWAPS = [('def _lesson_access(lesson):\n\troom = _client_room()', 'def _lesson_access(lesson):\n\troom = _learning_room()', 'lesson access'), ('def client_get_training():\n\troom = _client_room()', 'def client_get_training():\n\troom = _learning_room()', 'training list'), ('def client_course(record):\n\troom = _client_room()', 'def client_course(record):\n\troom = _learning_room()', 'course'), ('def client_quiz_start(record):\n\troom = _client_room()', 'def client_quiz_start(record):\n\troom = _learning_room()', 'quiz start'), ('def client_quiz_submit(attempt, answers):\n\troom = _client_room()', 'def client_quiz_submit(attempt, answers):\n\troom = _learning_room()', 'quiz submit'), ('_timed_attempt then re-checks the attempt belongs to this session."""\n\troom = _client_room()', '_timed_attempt then re-checks the attempt belongs to this session."""\n\troom = _learning_room()', 'proctored attempt'), ('def client_get_certificates():\n\t_client_room()', 'def client_get_certificates():\n\t_learning_room()', 'certificates'), ('def client_certificate_file(serial):\n\t_client_room()', 'def client_certificate_file(serial):\n\t_learning_room()', 'certificate file'), ('def client_get_tracks():\n\troom = _client_room()', 'def client_get_tracks():\n\troom = _learning_room()', 'tracks')]



def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, ACAD, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _learning_room(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.214.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.214.0.")

    edits = [
        (CR, HELPER_OLD, HELPER_NEW, "_learning_room helper"),
        (CR, VIS_OLD, VIS_NEW, "_visible_tracks keeps expired enrolments"),
        (CR, CALL_OLD, CALL_NEW, "pass the user"),
        (CR, OUT_OLD, OUT_NEW, "track payload carries seats_expired"),
        (ACAD, CAT_ENT, CAT_ENT_NEW, "catalogue reports expired seats"),
        (PORTAL, CARD_OLD, CARD_NEW, "expiry note on the track card"),
        (PORTAL, CSS_OLD, CSS_NEW, "expiry note css"),
    ] + [(CR, o, n, "freeze exempt: " + l) for o, n, l in SWAPS]

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
    for p in (CR, ACAD, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: _learning_room + 9 freeze exemptions + expiry visibility")
    print("  academy.py: catalogue reports expired seats")
    print("  portal.html: expiry note on the learner's track card")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.214.0"', '"3.215.0"'))
    print("wrote __init__.py -> 3.215.0")


if __name__ == "__main__":
    main()
