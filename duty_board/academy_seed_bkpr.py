"""CloudERP.One Certified Bookkeeper track seed — approved content (27-07-2026).

Content lives in academy_bkpr_data.json (4 modules: M1 The Service & The
System, M2a Daily Posting Craft, M2b Month-End & the Close, M4 The
Professional Bookkeeper — 28 lessons, 106 questions). M3 The Nigerian
Statutory Month is deliberately absent pending the authoritative Taxation
manual; add it to the track via desk when seeded.

Audience: Consultant (internal only — never appears in client catalogues).
Product: Accounting Services. Track: XLV-BKPR, pass mark 70.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_bkpr.seed_bookkeeper_track
Idempotent per module and per track.
"""

import json
import os

import frappe

ORDER = ["m1", "m2a", "m2b", "m4"]

TRACK = {
	"title": "CloudERP.One Certified Bookkeeper",
	"serial_prefix": "XLV-BKPR",
	"description": "The accounting unit's certification: the service and its board, daily posting craft, month-end and the close, and professional conduct. The Nigerian Statutory Month module joins the track when seeded.",
}


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_bkpr_data.json")
	with open(path) as f:
		return json.load(f)


def seed_bookkeeper_track():
	data = _data()
	if not frappe.db.exists("Duty Product", "Accounting Services"):
		print("Duty Product 'Accounting Services' missing — run accounting.sync_accounting_clients (or create it) first.")
		return

	module_names = {}
	for i, key in enumerate(ORDER):
		m = data[key]
		existing = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
		if existing:
			module_names[key] = existing
			print(f"module exists: {m['title']}")
			continue
		mod = frappe.get_doc(
			{
				"doctype": "Duty Training Module",
				"title": m["title"],
				"product": "Accounting Services",
				"description": m["desc"],
				"active": 1,
				"audience": "Consultant",
				"sort_order": 20 + i,
				"pass_mark": 70,
			}
		).insert(ignore_permissions=True)
		module_names[key] = mod.name
		for j, l in enumerate(m["lessons"]):
			frappe.get_doc(
				{
					"doctype": "Duty Lesson",
					"module": mod.name,
					"title": l["title"],
					"sort_order": j,
					"est_minutes": l["est"],
					"content": l["html"],
				}
			).insert(ignore_permissions=True)
		for q in m["questions"]:
			frappe.get_doc(
				{
					"doctype": "Duty Quiz Question",
					"module": mod.name,
					"question": q["q"],
					"opt_a": q["opts"][0],
					"opt_b": q["opts"][1],
					"opt_c": q["opts"][2],
					"opt_d": q["opts"][3],
					"correct": "ABCD"[q["ans"]],
					"rationale": q["why"],
					"source": q["src"],
					"active": 1,
				}
			).insert(ignore_permissions=True)
		print(f"seeded module: {m['title']} ({len(m['lessons'])} lessons, {len(m['questions'])} questions)")

	if frappe.db.exists("Duty Certification Track", {"title": TRACK["title"]}):
		print(f"track exists: {TRACK['title']}")
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Certification Track",
				"title": TRACK["title"],
				"product": "Accounting Services",
				"audience": "Consultant",
				"serial_prefix": TRACK["serial_prefix"],
				"description": TRACK["description"],
				"active": 1,
				"modules": [{"module": module_names[k]} for k in ORDER],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules — M3 joins via desk when seeded)")

	frappe.db.commit()
	print("Certified Bookkeeper track ready.")
