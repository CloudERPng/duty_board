"""System-Based Internal Control in a Retail Environment — track seed.

Content lives in academy_control_data.json, built by build_control_m*.py.

Seeded deliberately while INCOMPLETE. Six of nine modules are written, and the
track is published so the material can be reviewed as a learner sees it rather
than read as prose in a chat window. Reviewing a chapter in the reading room —
with its checks, its measure, its typography — surfaces problems that reading
the source never will.

Consequences of publishing early, and how each is handled:

  - `active` is 0 until the set is complete, so the track does not appear in
    the client catalogue and cannot be requested or assigned by a client. Staff
    can still open the modules for review.
  - The description says plainly that it is in preparation. If the flag is ever
    flipped early by accident, a client sees an honest label rather than a
    thin course.
  - Reconciles the module list on every run, so modules 8, 1 and 9
    join the track as they are written without anybody editing a child table by
    hand — the fix made in v3.226.4 after exactly that happened.

To review as a learner: set `active` to 1 on the track and grant yourself an
entitlement, or open the modules directly from the desk.

Run:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_control.seed_control_track
"""

import json
import os

import frappe

PRODUCT = "Xlevel Academy"

# written order, not blueprint order — the track displays in this sequence and
# is re-sequenced as the remaining modules arrive
ORDER = ["getting_data", "master_data", "procure_pay", "inventory", "revenue_pos", "access"]

TRACK = {
    "title": "System-Based Internal Control in a Retail Environment",
    "serial_prefix": "XLV-ICR",
    "seat_price": 85000,
    "description": (
        "IN PREPARATION — six of nine modules published for review. "
        "For internal control officers and auditors in multi-branch retail. In a manual "
        "environment you rely on people behaving well; in a system environment you rely "
        "on the record of what they did. This track teaches how to interrogate that "
        "record: extracting your own data, designing tests that examine the whole "
        "population rather than a sample of fifty, reading a version history, comparing "
        "twenty branches as a distribution, and writing findings that get fixed rather "
        "than argued down."
    ),
    "who_for": (
        "Qualified accountants working as internal control officers or internal auditors "
        "across a multi-branch retail estate, covering procurement, stores, revenue and "
        "cash. Nothing here explains double entry or a margin. What is explained is the "
        "system, and how to interrogate it."
    ),
    "outcomes": (
        "Extract your own data without asking anybody, so you stop asking smaller "
        "questions than you need to. Test a whole population and report that no instance "
        "occurred in the period, rather than that the fifty you examined were in order. "
        "Reconstruct what a document said before it was changed, and who changed it. "
        "Profile behaviour across an estate and know which outlier is a finding rather "
        "than noise. And handle the first hour of a suspected fraud without destroying "
        "your own case."
    ),
}


def _data():
    path = os.path.join(os.path.dirname(__file__), "academy_control_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_control_track():
    data = _data()

    if not frappe.db.exists("Duty Product", PRODUCT):
        frappe.get_doc({
            "doctype": "Duty Product", "title": PRODUCT, "active": 1, "sort_order": 90,
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
            "sort_order": 40 + i,
            "pass_mark": 70,
            "timed_mode": 1,
            "seconds_per_question": 90,   # longer than finance: these are analytical
            "questions_served": 12,
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
                # the void chapter is the public sample: it shows the method
                # rather than the software, which is what a buyer is judging
                "is_sample": 1 if (key == "revenue_pos" and j == 1) else 0,
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

    existing_track = frappe.db.get_value(
        "Duty Certification Track", {"title": TRACK["title"]}, "name"
    )
    if existing_track:
        t = frappe.get_doc("Duty Certification Track", existing_track)
        have = {r.module for r in t.modules}
        added = [module_names[k] for k in ORDER
                 if k in module_names and module_names[k] not in have]
        if added:
            for name in added:
                t.append("modules", {"module": name})
            t.save(ignore_permissions=True)
            print("track exists: added %d module(s)" % len(added))
        else:
            print("track exists and already lists every written module")
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
            "active": 0,          # deliberately unpublished until complete
            "modules": [{"module": module_names[k]} for k in ORDER if k in module_names],
        }).insert(ignore_permissions=True)
        print("seeded track: %s (%s, %d module(s), INACTIVE)"
              % (t.title, t.name, len(ORDER)))

    frappe.db.commit()
    print("\nThe track is seeded with active = 0, so it does NOT appear in the client")
    print("catalogue and cannot be requested or assigned. That is deliberate while")
    print("seven of nine modules are unwritten.")
    print("\nTo review the material as a learner sees it, either open the modules from")
    print("the desk, or set active = 1 on the track and grant yourself an entitlement —")
    print("remembering to set it back before any client sees the catalogue.")
