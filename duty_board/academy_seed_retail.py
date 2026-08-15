"""Retail Leadership Essentials — seed and reconcile.

Nine modules planned; eight written. The track is seeded INACTIVE so it can be
read and reviewed in the app without appearing in any client catalogue, and it
reconciles its module list on every run — so module 9 joins automatically
as they are written, with nobody editing a child table.

Set active=1 when the track is complete and the four Duty Settings values are
confirmed.

Run:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_retail.seed_retail_track
"""

import json
import os

import frappe

PRODUCT = "Retail Leadership"
TRACK = "Retail Leadership Essentials"

# display order; modules not yet written are simply absent from the data file
ORDER = ["the_job", "the_numbers", "availability", "people", "loss", "customers", "upward", "without_you"]

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

    names, missing = {}, []
    for key in ORDER:
        if key not in data:
            missing.append(key)
            continue
        title = data[key]["title"]
        n = frappe.db.get_value("Duty Training Module", {"title": title}, "name")
        if n:
            names[key] = n
        else:
            missing.append(title)

    if missing:
        print("not seeded on this site (%d): %s" % (len(missing), ", ".join(missing)))
        print("run the content seeder first; this script wires the track.\n")

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
            "active": 0,          # eight of nine modules written
            "modules": [{"module": m} for m in mods],
        }).insert(ignore_permissions=True)
        print("seeded track: %s (%d modules, inactive)" % (TRACK, len(mods)))

    frappe.db.commit()
    print("\nSeeded inactive: eight of nine modules are written, so the track is readable")
    print("in the app for review and appears in no client catalogue. Re-run after each")
    print("new module — the list reconciles. Set active=1 when the track is complete.")
