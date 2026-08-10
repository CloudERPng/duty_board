"""ZhiftERP Sales Professional track seed — the complete selling curriculum.

Content lives in academy_sales_pro_data.json (6 modules, 24 lessons, 72
questions). Modules are PROCTORED: timed 60s/question, 10 served from
each 12-question bank.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track
Idempotent per module and for the track.
"""

import json
import os

import frappe

ORDER = ["customers", "items_prices", "quotations", "sales_orders", "delivery", "taxes_invoicing", "sales_invoice", "advanced"]

TRACK = {
	"title": "ZhiftERP Sales Professional",
	"serial_prefix": "ZERP-SALESPRO",
	"description": "The complete selling certification: customer management, items and pricing, quotations, sales orders, delivery and returns, and taxes, pricing rules, invoicing and collections — six proctored examinations from foundations to the reports that run a sales book.",
}


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_sales_pro_data.json")
	with open(path) as f:
		return json.load(f)


def seed_sales_pro_track():
	data = _data()
	if not frappe.db.exists("Duty Product", "ZhiftERP"):
		frappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP", "active": 1, "sort_order": 0}).insert(
			ignore_permissions=True
		)
		print("created Duty Product: ZhiftERP")

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
				"product": "ZhiftERP",
				"description": m["desc"],
				"active": 1,
				"audience": "Both",
				"sort_order": 10 + i,
				"pass_mark": 70,
				"timed_mode": 1,
				"seconds_per_question": 60,
				"questions_served": 10,
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
		print(f"seeded module: {m['title']} ({len(m['lessons'])} lessons, {len(m['questions'])} questions, proctored)")

	existing_track = frappe.db.get_value("Duty Certification Track", {"title": TRACK["title"]}, "name")
	if existing_track:
		tr = frappe.get_doc("Duty Certification Track", existing_track)
		have = {r.module for r in tr.get("modules") or []}
		added = 0
		for k in ORDER:
			if module_names[k] not in have:
				tr.append("modules", {"module": module_names[k]})
				added += 1
		if added:
			tr.save(ignore_permissions=True)
			print(f"track exists: {TRACK['title']} — appended {added} new module(s)")
		else:
			print(f"track exists: {TRACK['title']} — complete")
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Certification Track",
				"title": TRACK["title"],
				"product": "ZhiftERP",
				"audience": "Consultant",
				"serial_prefix": TRACK["serial_prefix"],
				"description": TRACK["description"],
				"active": 1,
				"modules": [{"module": module_names[k]} for k in ORDER],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

	frappe.db.commit()
	print("ZhiftERP Sales Professional track ready.")
