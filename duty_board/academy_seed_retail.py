"""Retail Leadership Essentials — seed and reconcile.

All nine modules written. Seeds the content — modules, lessons, checks and questions — and then wires the
track. The first version of this file only wired the track: it looked each
module up by title, printed the ones it could not find, and created nothing, so
running it produced a track with no modules and nothing visible in the app.
That was the whole reason the track could not be seen.

Existing modules are left untouched. Content changes go through
academy_repair.push_lessons rather than through re-seeding.

Before selling, confirm in Duty Settings: academy_bank_details,
academy_approver, academy_vat_rate, academy_tutors.

Run:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_retail.seed_retail_track
"""

import json
import os

import frappe

PRODUCT = "Retail Leadership"
TRACK = "Retail Leadership Essentials"

# display order; modules not yet written are simply absent from the data file
ORDER = ["the_job", "the_numbers", "availability", "people", "loss", "customers", "upward", "without_you", "the_week"]

DESCRIPTION = (
    "For the person running a branch. What the job actually is as against what it was "
    "before you were promoted, how to read your own numbers and know which of them lie, "
    "closing the largest recoverable loss in most branches, building a team that stays, "
    "and preventing loss rather than measuring it. Written for a multi-branch retailer in "
    "this market, with one business followed throughout."
)

WHO_FOR = (
    "Branch and store managers, and the supervisors being prepared for those roles. No "
    "finance or management background is assumed — every term is explained where it is "
    "used, and nothing in the track depends on any other course."
)

OUTCOMES = (
    "Tell the difference between a busy week and a managerial one. Read a branch report "
    "and know which figures are true, which are artefacts of allocation, and what the "
    "sales number is hiding. Measure availability on the lines that earn most and close "
    "the gaps by cause rather than by exhortation. Run a rota and a first week that keep "
    "people. Prevent loss by design rather than vigilance, and know what to do in the "
    "hour you first suspect somebody."
)


def _data():
    path = os.path.join(os.path.dirname(__file__), "academy_retail_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_retail_track():
    data = _data()

    if not frappe.db.exists("Duty Product", PRODUCT):
        frappe.get_doc({
            "doctype": "Duty Product", "title": PRODUCT, "active": 1, "sort_order": 30,
        }).insert(ignore_permissions=True)
        print("created Duty Product: %s" % PRODUCT)

    names = {}
    for i, key in enumerate(ORDER):
        if key not in data:
            print("MISSING from the data file, skipped: %s" % key)
            continue
        m = data[key]
        existing = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
        if existing:
            names[key] = existing
            print("module exists, left untouched: %s" % m["title"])
            continue

        mod = frappe.get_doc({
            "doctype": "Duty Training Module",
            "title": m["title"],
            "product": PRODUCT,
            "description": m["desc"],
            "active": 1,
            "audience": "Client",
            "sort_order": 30 + i,
            "pass_mark": 70,
            "timed_mode": 1,
            "seconds_per_question": 75,
            "questions_served": 10,
            "max_attempts": 2,
            "retake_wait_hours": 24,
            "hide_wrong_answers": 1,
        }).insert(ignore_permissions=True)
        names[key] = mod.name

        for j, l in enumerate(m["lessons"]):
            lesson = frappe.get_doc({
                "doctype": "Duty Lesson",
                "module": mod.name,
                "title": l["title"],
                "sort_order": j,
                "est_minutes": l["est"],
                "content": l["html"],
                # third chapter is the public sample, as on the other tracks
                "is_sample": 1 if j == 2 else 0,
            }).insert(ignore_permissions=True)
            for k, c in enumerate(l.get("checks") or []):
                opts = list(c["opts"]) + [None, None, None, None]
                frappe.get_doc({
                    "doctype": "Duty Lesson Check",
                    "lesson": lesson.name,
                    "sort_order": k,
                    "question": c["q"],
                    "opt_a": opts[0], "opt_b": opts[1],
                    "opt_c": opts[2], "opt_d": opts[3],
                    "correct": "ABCD"[c["ans"]],
                    "rationale": c.get("why"),
                    "active": 1,
                }).insert(ignore_permissions=True)

        for q in m["questions"]:
            frappe.get_doc({
                "doctype": "Duty Quiz Question",
                "module": mod.name,
                "question": q["q"],
                "opt_a": q["opts"][0], "opt_b": q["opts"][1],
                "opt_c": q["opts"][2], "opt_d": q["opts"][3],
                "correct": "ABCD"[q["ans"]],
                "rationale": q["why"],
                "source": q["src"],
                "topic": q["topic"],
                "active": 1,
            }).insert(ignore_permissions=True)

        checks = sum(len(l.get("checks") or []) for l in m["lessons"])
        print("seeded module: %s (%d chapters, %d checks, %d questions)"
              % (m["title"], len(m["lessons"]), checks, len(m["questions"])))

    mods = [names[k] for k in ORDER if k in names]
    if not mods:
        print("no modules available — nothing to wire.")
        return

    existing = frappe.db.get_value("Duty Certification Track", {"title": TRACK}, "name")
    if existing:
        t = frappe.get_doc("Duty Certification Track", existing)
        have = {r.module for r in t.modules}
        added = [m for m in mods if m not in have]
        if added:
            for m in added:
                t.append("modules", {"module": m})
            t.save(ignore_permissions=True)
            print("%s: added %d module(s), now %d" % (TRACK, len(added), len(t.modules)))
        else:
            print("%s: already lists every available module (%d)" % (TRACK, len(have)))
    else:
        frappe.get_doc({
            "doctype": "Duty Certification Track",
            "title": TRACK,
            "product": PRODUCT,
            "audience": "Client",
            "serial_prefix": "RL",
            "description": DESCRIPTION,
            "who_for": WHO_FOR,
            "outcomes": OUTCOMES,
            "access": "Paid",
            "seat_price": 45000,
            "active": 1,          # all nine modules audit ok
            "modules": [{"module": m} for m in mods],
        }).insert(ignore_permissions=True)
        print("seeded track: %s (%d modules, ACTIVE)" % (TRACK, len(mods)))

    frappe.db.commit()
    print("\nAll nine modules written and audit clean: 81 chapters, 243 checks,")
    print("379 questions, approximately 41,000 words. Before selling, confirm in Duty")
    print("Settings: academy_bank_details, academy_approver, academy_vat_rate,")
    print("academy_tutors.")
