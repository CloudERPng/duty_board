"""ZhiftPOS certification tracks — seed and reconcile.

One module library, three tracks. The Closer pattern: a module belongs to as
many tracks as need it, and the shared body of work yields several products.

  Certified ZhiftPOS Operator      counter_basics, shift_sale,
                                   concessions_returns, extended_counters,
                                   voucher_programme
  Certified ZhiftPOS Supervisor    the operator five, plus honest_counter
  ZhiftPOS Implementation          all nine

Only the OPERATOR track is seeded active. The other two contain modules that
still carry audit findings — no checks on four of them, two thin chapters in
honest_counter — and a paid track whose modules do not meet the standard is
exactly the certificate the estate audit exists to prevent.

Reconciles module lists on every run, so a module reaching standard later joins
its tracks without anybody editing a child table. Existing modules and lessons
are never touched; content changes go through academy_repair.push_lessons.

Run:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_pos_certs.seed_pos_tracks
"""

import json
import os

import frappe

PRODUCT = "ZhiftPOS"

OPERATOR = ["counter_basics", "shift_sale", "concessions_returns",
            "extended_counters", "voucher_programme"]
SUPERVISOR = OPERATOR + ["honest_counter"]
CONSULTANT = ["counter_system", "pos_profile", "terminal_estate"] + SUPERVISOR

TRACKS = [
    {
        "key": "operator",
        "title": "Certified ZhiftPOS Operator",
        "serial_prefix": "ZPOS-OP",
        "modules": OPERATOR,
        "active": 1,
        "access": "Paid",
        "seat_price": 18000,
        "description": (
            "Certifies that you can run a ZhiftPOS counter to a standard the business "
            "can rely on: open a shift with a counted float, build and complete a sale, "
            "handle discounts, returns and overrides through the proper route, work the "
            "lay-by, staff purchase, airtime and voucher counters, and close with a count "
            "that means something. Five modules, forty-five chapters, a proctored "
            "assessment on each."
        ),
        "who_for": (
            "Cashiers and counter staff working a ZhiftPOS till. No prior system "
            "knowledge is assumed. It does not cover configuring a counter — that is the "
            "implementation track."
        ),
        "outcomes": (
            "Run a trading day end to end without supervision. Explain to a customer why "
            "an offline receipt is valid and find the sale for a return. Handle a discount "
            "or a return so it leaves a record somebody can follow. Close a shift with a "
            "counted figure and a one-sentence explanation of any variance. And know why "
            "one person one account protects you rather than restricts you."
        ),
    },
    {
        "key": "supervisor",
        "title": "Certified ZhiftPOS Supervisor",
        "serial_prefix": "ZPOS-SV",
        "modules": SUPERVISOR,
        "active": 1,          # all six modules now audit ok
        "access": "Paid",
        "seat_price": 28000,
        "description": (
            "The operator syllabus plus daily verification and offline "
            "operation: the checks a supervisor runs at close, what works and what waits "
            "when the network is down, and reading the counter's figures at the end of "
            "every day."
        ),
        "who_for": "Shift supervisors and store managers responsible for a counter's figures.",
        "outcomes": (
            "Run and verify a trading day end to end. Read the top bar as a set and judge "
            "a queue by direction and age rather than size. Clear conflicts and failed "
            "sales before they reach the books as a difference. Prove the counter's money "
            "daily from End of Day Funds, run the weekly check circuit that clears honest "
            "staff as much as it catches the rare bad case, and pass the handover test — "
            "if the best supervisor left on Friday, Monday still works."
        ),
    },
    {
        "key": "consultant",
        "title": "ZhiftPOS Implementation Consultant",
        "serial_prefix": "ZPOS-IC",
        "modules": CONSULTANT,
        "active": 0,          # three configuration modules not yet at standard
        "access": "Paid",
        "seat_price": 95000,
        "description": (
            "IN PREPARATION. The full syllabus: counter architecture, building a Point of "
            "Sale Profile, commissioning a terminal estate, and everything in the operator "
            "and supervisor tracks."
        ),
        "who_for": "Implementation consultants and partner staff deploying ZhiftPOS.",
        "outcomes": "Configure a counter correctly and certify the people who will run it.",
    },
]


def _data():
    path = os.path.join(os.path.dirname(__file__), "academy_pos_pro_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed_pos_tracks():
    data = _data()

    if not frappe.db.exists("Duty Product", PRODUCT):
        frappe.get_doc({
            "doctype": "Duty Product", "title": PRODUCT, "active": 1, "sort_order": 20,
        }).insert(ignore_permissions=True)
        print("created Duty Product: %s" % PRODUCT)

    # modules must already exist; this script wires tracks, it does not seed content
    names = {}
    missing = []
    for key, mod in data.items():
        n = frappe.db.get_value("Duty Training Module", {"title": mod["title"]}, "name")
        if n:
            names[key] = n
        else:
            missing.append(mod["title"])
    if missing:
        print("NOT SEEDED on this site (%d):" % len(missing))
        for t in missing:
            print("   %s" % t)
        print("Run the POS content seeder first; this script only wires tracks.\n")

    for spec in TRACKS:
        mods = [names[k] for k in spec["modules"] if k in names]
        if not mods:
            print("skipped %s — none of its modules are on this site" % spec["title"])
            continue

        existing = frappe.db.get_value(
            "Duty Certification Track", {"title": spec["title"]}, "name")
        if existing:
            t = frappe.get_doc("Duty Certification Track", existing)
            have = {r.module for r in t.modules}
            added = [m for m in mods if m not in have]
            if added:
                for m in added:
                    t.append("modules", {"module": m})
                t.save(ignore_permissions=True)
                print("%s: added %d module(s)" % (spec["title"], len(added)))
            else:
                print("%s: already lists every available module" % spec["title"])
            continue

        frappe.get_doc({
            "doctype": "Duty Certification Track",
            "title": spec["title"],
            "product": PRODUCT,
            "audience": "Client",
            "serial_prefix": spec["serial_prefix"],
            "description": spec["description"],
            "who_for": spec.get("who_for"),
            "outcomes": spec.get("outcomes"),
            "access": spec["access"],
            "seat_price": spec["seat_price"],
            "active": spec["active"],
            "modules": [{"module": m} for m in mods],
        }).insert(ignore_permissions=True)
        print("seeded track: %s (%d modules, %s)"
              % (spec["title"], len(mods),
                 "ACTIVE" if spec["active"] else "inactive"))

    frappe.db.commit()
    print("\nOperator and Supervisor are active. The Implementation track stays")
    print("inactive: counter_system, pos_profile and terminal_estate still carry no")
    print("check questions, and a paid track whose modules are below standard is the")
    print("certificate the estate audit exists to prevent.")
    print("\nBefore selling, confirm in Duty Settings: academy_bank_details,")
    print("academy_approver, academy_vat_rate, academy_tutors.")
