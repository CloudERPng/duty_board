"""ZhiftCRM Certified Consultant track seed — distilled from the six product manuals (28-07-2026).

Content lives in academy_consultant_data.json (5 modules: C1 Platform &
Dashboard Command, C2 Orders Customers & Fulfilment, C3 The Campaign
Engine, C4 Reports & the Numbers, C5 Administration: Closers & Shifts —
31 lessons, 134 questions). Rerunning keeps existing modules, adds new
ones, renumbers sort_order, and syncs the ZCRM-CONSULT track's module
rows to ORDER — replacing the interim composition of reused client
modules; staff progress on those modules is untouched (they remain in
the client tracks).

Audience: Consultant (internal only — never appears in client catalogues).
Product: ZhiftCRM. Track: ZCRM-CONSULT, pass mark 70.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_consultant.seed_consultant_track
Idempotent per module and per track.
"""

import json
import os

import frappe

ORDER = ["c1", "c2", "c3", "c4", "c5"]

TRACK = {
	"title": "ZhiftCRM Certified Consultant",
	"serial_prefix": "ZCRM-CONSULT",
	"description": "The implementer's certification, distilled from the full product manuals: platform and dashboard command, the order engine, the campaign engine, the report library, and the administration layer — closers and shift management.",
}


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_consultant_data.json")
	with open(path) as f:
		return json.load(f)


def seed_consultant_track():
	data = _data()
	if not frappe.db.exists("Duty Product", "ZhiftCRM"):
		print("Duty Product 'ZhiftCRM' missing — create it first.")
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
				"product": "ZhiftCRM",
				"description": m["desc"],
				"active": 1,
				"audience": "Consultant",
				"sort_order": 30,
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

	# sort_order follows ORDER regardless of seeding history
	for i, key in enumerate(ORDER):
		frappe.db.set_value("Duty Training Module", module_names[key], "sort_order", 30 + i, update_modified=False)

	track_name = frappe.db.get_value("Duty Certification Track", {"title": TRACK["title"]}, "name")
	if track_name:
		tr = frappe.get_doc("Duty Certification Track", track_name)
		desired = [module_names[k] for k in ORDER]
		current = [row.module for row in tr.modules]
		if current != desired:
			tr.modules = []
			for mn in desired:
				tr.append("modules", {"module": mn})
			tr.save(ignore_permissions=True)
			print(f"track updated: {TRACK['title']} → {len(desired)} modules in order")
		else:
			print(f"track exists: {TRACK['title']} (module rows already in order)")
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Certification Track",
				"title": TRACK["title"],
				"product": "ZhiftCRM",
				"audience": "Consultant",
				"serial_prefix": TRACK["serial_prefix"],
				"description": TRACK["description"],
				"active": 1,
				"modules": [{"module": module_names[k]} for k in ORDER],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

	frappe.db.commit()
	print("Certified Consultant track ready — composition replaced with the five manual-distilled modules.")
