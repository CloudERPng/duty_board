"""Accounting & Finance for Non-Finance Managers — track seed.

Content lives in academy_finance_data.json, built by build_finance_m2.py.

This is the first PAID track in the estate, so it seeds differently from the
product tracks:

  - its own Duty Product, "Xlevel Academy", because the track is not tied to
    any software the client subscribes to. Attaching it to Accounting Services
    would imply they buy that service, and the v3.213.0 catalogue reads paid
    tracks through entitlement rather than product anyway.
  - access "Paid" with a seat price, so it appears in the catalogue with a
    price and requires an approved order before anyone can be assigned to it.
  - who_for and outcomes populated, because the public catalogue renders those
    two sections and they are the ones that sell.

Seeds lessons, their end-of-lesson checks, and the topic-tagged question bank —
the older seeders predate checks and topics and do not carry them.

Run:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_finance.seed_finance_track

Idempotent per module and per track: an existing module is left alone entirely,
so correcting content afterwards goes through academy_repair, not re-seeding.
"""

import json
import os

import frappe

PRODUCT = "Xlevel Academy"
ORDER = ["read_pl"]

TRACK = {
    "title": "Accounting & Finance for Non-Finance Managers",
    "serial_prefix": "XLV-FIN",
    "seat_price": 45000,
    "description": (
        "For managers and directors who run a business but were never taught to read one. "
        "Built on one principle: read before prepare. You will never draft a set of accounts, "
        "you will be handed them — so every chapter starts from a document or a decision in "
        "front of you and works back to the idea behind it. Worked throughout in naira, on "
        "retail, distribution and branch numbers rather than textbook ones."
    ),
    "who_for": (
        "Branch and store managers, heads of department, operations and commercial leads, "
        "founders and C-level operators. No accounting background is assumed. If you receive "
        "management accounts each month and read them with more hope than confidence, this is "
        "written for you."
    ),
    "outcomes": (
        "Open your own management accounts and say what happened, why, and what you intend to "
        "do about it — without waiting for finance to interpret them. Specifically: read a "
        "profit and loss line by line, tell gross margin from markup and know which of the "
        "four things that move margin moved, separate the costs you control from those "
        "allocated to you, spot the lines that carry somebody's judgement, and ask the six "
        "questions that turn a statement into a decision."
    ),
}


def _data():
    path = os.path.join(os.path.dirname(__file__), "academy_finance_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_finance_track():
    data = _data()

    if not frappe.db.exists("Duty Product", PRODUCT):
        frappe.get_doc({
            "doctype": "Duty Product", "product_name": PRODUCT,
            "active": 1, "sort_order": 90,
        }).insert(ignore_permissions=True)
        print("created Duty Product: %s" % PRODUCT)

    module_names = {}
    for i, key in enumerate(ORDER):
        m = data[key]
        existing = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
        if existing:
            module_names[key] = existing
            print("module exists, left untouched: %s" % m["title"])
            continue

        mod = frappe.get_doc({
            "doctype": "Duty Training Module",
            "title": m["title"],
            "product": PRODUCT,
            "description": m["desc"],
            "active": 1,
            "audience": "Client",
            "sort_order": 20 + i,
            "pass_mark": 70,
            # a sold assessment: timed, capped, cooling-off, answer key withheld
            "timed_mode": 1,
            "seconds_per_question": 75,
            "questions_served": 10,
            "max_attempts": 2,
            "retake_wait_hours": 24,
            "hide_wrong_answers": 1,
        }).insert(ignore_permissions=True)
        module_names[key] = mod.name

        for j, l in enumerate(m["lessons"]):
            lesson = frappe.get_doc({
                "doctype": "Duty Lesson",
                "module": mod.name,
                "title": l["title"],
                "sort_order": j,
                "est_minutes": l["est"],
                "content": l["html"],
                # the third chapter is the public sample: it shows judgement
                # rather than mechanics, which is what a buyer is assessing
                "is_sample": 1 if j == 2 else 0,
            }).insert(ignore_permissions=True)
            for k, c in enumerate(l.get("checks") or []):
                opts = list(c["opts"]) + [None, None, None, None]
                frappe.get_doc({
                    "doctype": "Duty Lesson Check",
                    "lesson": lesson.name,
                    "sort_order": k,
                    "question": c["q"],
                    "opt_a": opts[0], "opt_b": opts[1], "opt_c": opts[2], "opt_d": opts[3],
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
        print("seeded module: %s (%d lessons, %d checks, %d questions)"
              % (m["title"], len(m["lessons"]), checks, len(m["questions"])))

    if frappe.db.exists("Duty Certification Track", {"title": TRACK["title"]}):
        print("track exists, left untouched: %s" % TRACK["title"])
    else:
        t = frappe.get_doc({
            "doctype": "Duty Certification Track",
            "title": TRACK["title"],
            "product": PRODUCT,
            "audience": "Client",
            "serial_prefix": TRACK["serial_prefix"],
            "description": TRACK["description"],
            "who_for": TRACK["who_for"],
            "outcomes": TRACK["outcomes"],
            "access": "Paid",
            "seat_price": TRACK["seat_price"],
            "active": 1,
            "modules": [{"module": module_names[k]} for k in ORDER if k in module_names],
        }).insert(ignore_permissions=True)
        print("seeded track: %s (%s, %d module(s), paid)"
              % (t.title, t.name, len(ORDER)))

    frappe.db.commit()
    print("\nThe track is PAID: it will show a price in the catalogue and nobody "
          "can be assigned to it until a seat order is approved.")
    print("Remaining modules of this track are not written yet — the track is "
          "sellable only once they are.")
