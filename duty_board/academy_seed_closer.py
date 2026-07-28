"""Closer & Closer Manager track seed — approved red-pen content (26-07-2026).

Content lives in academy_closer_data.json (4 modules, 24 lessons, 103
questions); screenshots ship as app assets under /assets/duty_board/academy/.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_closer.seed_closer_tracks
Idempotent per module and per track.
"""

import json
import os

import frappe

from duty_board.academy_seed import MODULE_TITLE as FOUNDATIONS_TITLE

ORDER = ["orders_pipeline", "closer_workflow", "reports_analytics", "team_workflow"]

CONSULTANT_TRACK = {
	"title": "ZhiftCRM Certified Consultant",
	"serial_prefix": "ZCRM-CONSULT",
	"description": "The implementer's certification: complete command of every ZhiftCRM workflow — foundations, orders & pipeline, closer workflow, reports & analytics, and team & workflow management. Implementation & configuration modules join the track when seeded.",
	"modules": ["__foundations__", "orders_pipeline", "closer_workflow", "reports_analytics", "team_workflow"],
}

TRACKS = [
	{
		"title": "ZhiftCRM Certified Closer",
		"serial_prefix": "ZCRM-CLOSER",
		"description": "The closer's certification: platform foundations, the full order lifecycle, and the closer workflow including shifts and the follow-up pool.",
		"modules": ["__foundations__", "orders_pipeline", "closer_workflow"],
	},
	{
		"title": "ZhiftCRM Certified Closer Manager",
		"serial_prefix": "ZCRM-CLMGR",
		"description": "The closer manager's certification: everything a closer must know, plus reports & analytics and team & workflow management.",
		"modules": ["__foundations__", "orders_pipeline", "closer_workflow", "reports_analytics", "team_workflow"],
	},
]


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_closer_data.json")
	with open(path) as f:
		return json.load(f)


def seed_closer_tracks():
	data = _data()
	foundations = frappe.db.get_value("Duty Training Module", {"title": FOUNDATIONS_TITLE}, "name")
	if not foundations:
		print("Foundations module not found — run seed_crm_foundations first.")
		return
	if not frappe.db.exists("Duty Product", "ZhiftCRM"):
		print("Duty Product 'ZhiftCRM' missing — run seed_products first.")
		return

	module_names = {"__foundations__": foundations}
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
				"audience": "Both",
				"sort_order": 10 + i,
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

	for t in TRACKS:
		if frappe.db.exists("Duty Certification Track", {"title": t["title"]}):
			print(f"track exists: {t['title']}")
			continue
		frappe.get_doc(
			{
				"doctype": "Duty Certification Track",
				"title": t["title"],
				"product": "ZhiftCRM",
				"audience": "Client",
				"serial_prefix": t["serial_prefix"],
				"description": t["description"],
				"active": 1,
				"modules": [{"module": module_names[k]} for k in t["modules"]],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {t['title']} ({t['serial_prefix']}, {len(t['modules'])} modules)")

	frappe.db.commit()
	print("Closer & Closer Manager tracks ready.")


def seed_consultant_track():
	"""ZhiftCRM Certified Consultant (audience Consultant): the five existing
	modules; implementation/config modules join via rerun or desk when authored.
	Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_closer.seed_consultant_track
	Idempotent; rerun syncs the track's module rows to the canonical list."""
	foundations = frappe.db.get_value("Duty Training Module", {"title": FOUNDATIONS_TITLE}, "name")
	if not foundations:
		print("Foundations module not found — run seed_crm_foundations first.")
		return
	data = _data()
	module_names = {"__foundations__": foundations}
	missing = []
	for key in CONSULTANT_TRACK["modules"]:
		if key == "__foundations__":
			continue
		n = frappe.db.get_value("Duty Training Module", {"title": data[key]["title"]}, "name")
		if n:
			module_names[key] = n
		else:
			missing.append(key)
	if missing:
		print(f"missing modules {missing} — run seed_closer_tracks first.")
		return
	desired = [module_names[k] for k in CONSULTANT_TRACK["modules"]]
	track_name = frappe.db.get_value("Duty Certification Track", {"title": CONSULTANT_TRACK["title"]}, "name")
	if track_name:
		tr = frappe.get_doc("Duty Certification Track", track_name)
		if [r.module for r in tr.modules] != desired:
			tr.modules = []
			for mn in desired:
				tr.append("modules", {"module": mn})
			tr.save(ignore_permissions=True)
			print(f"track updated: {CONSULTANT_TRACK['title']} → {len(desired)} modules in order")
		else:
			print(f"track exists: {CONSULTANT_TRACK['title']} (module rows already in order)")
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Certification Track",
				"title": CONSULTANT_TRACK["title"],
				"product": "ZhiftCRM",
				"audience": "Consultant",
				"serial_prefix": CONSULTANT_TRACK["serial_prefix"],
				"description": CONSULTANT_TRACK["description"],
				"active": 1,
				"modules": [{"module": mn} for mn in desired],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {CONSULTANT_TRACK['title']} ({CONSULTANT_TRACK['serial_prefix']}, {len(desired)} modules — implementation modules join when authored)")
	frappe.db.commit()
	print("Certified Consultant track ready.")
