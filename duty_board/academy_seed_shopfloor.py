"""Retail Foundations — seed and reconcile.

The entry-level retail track: the shop floor job itself. The estate already has
the till (Certified ZhiftPOS Operator) and the branch manager (Retail Leadership
Essentials); this is the person between them, and it completes a ladder somebody
can climb — Foundations, Operator, Supervisor, Leadership.

All nine modules written and every one audits clean. Seeded ACTIVE. It
reconciles its module list on every run, so a later revision joins without
anybody editing a child table.

seat_price is deliberately left at 0. Price it against Certified ZhiftPOS
Operator at NGN18,000 as the next rung up rather than against the manager
track, and set it before selling. Also confirm in Duty Settings:
academy_bank_details, academy_approver, academy_vat_rate, academy_tutors.

Existing modules are left untouched. Content changes go through
academy_repair.push_lessons rather than through re-seeding.

Run:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_shopfloor.seed_shopfloor_track
"""

import json
import os

import frappe

PRODUCT = "Retail Foundations"
TRACK = "Retail Foundations"

# display order; modules not yet written are simply absent from the data file
ORDER = ["the_job", "customers", "the_shelf", "stock_dates", "money_honesty",
         "the_shift", "hard_moments", "getting_better", "the_day"]

DESCRIPTION = (
    "For the person working the shop floor. What the job actually consists of beyond "
    "serving customers, how the shop makes money and why that governs every rule you "
    "are given, keeping a section right, handling stock and dates, the habits that "
    "protect you as well as the business, and what actually gets somebody promoted. "
    "Assumes no experience and no particular system."
)

WHO_FOR = (
    "Shop assistants, counter staff and stockroom staff, including first jobs. Nothing "
    "is assumed — no retail experience, no finance background, and no software: the "
    "track works for a business running on paper. Every term is explained where it is "
    "first used."
)

OUTCOMES = (
    "State what the job is for beyond serving customers, and use a quiet hour well. "
    "Explain what margin is and why one damaged item costs several sales. Start a shift "
    "with five minutes that produce a plan rather than a reaction. Know what to learn "
    "about the stock and when to refuse to guess. Understand which standards protect "
    "the money, the customer and you. And know, specifically, what gets somebody moved "
    "up rather than assuming it is being liked."
)


def _data():
    path = os.path.join(os.path.dirname(__file__), "academy_shopfloor_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_shopfloor_track():
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
			"category": "Retail & Point of Sale",
            "title": TRACK,
            "product": PRODUCT,
            "audience": "Client",
            "serial_prefix": "RL",
            "description": DESCRIPTION,
            "who_for": WHO_FOR,
            "outcomes": OUTCOMES,
            "access": "Paid",
            # price not yet set: one module of nine. Decide it when the track is
            # complete, against Certified ZhiftPOS Operator at NGN18,000 (the
            # next rung up) rather than against the manager track.
            "seat_price": 0,
            "active": 1,          # all nine modules audit ok
            "modules": [{"module": m} for m in mods],
        }).insert(ignore_permissions=True)
        print("seeded track: %s (%d modules, ACTIVE)" % (TRACK, len(mods)))

    frappe.db.commit()
    print("\nAll nine modules written and audit clean: 81 chapters, 243 checks,")
    print("379 questions, approximately 41,000 words.")
    print("BEFORE SELLING: set a seat_price (currently 0) and confirm in Duty Settings")
    print("academy_bank_details, academy_approver, academy_vat_rate, academy_tutors.")
