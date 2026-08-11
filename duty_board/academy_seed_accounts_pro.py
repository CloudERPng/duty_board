"""ZhiftERP Accounts Professional track seed — the finance curriculum.

Content lives in academy_accounts_pro_data.json. Modules are PROCTORED:
timed 60s/question, 10 served from each 35-question bank. Modules are
added pass by pass; re-running the seed appends new modules to the
existing track (idempotent per module and for the track).

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_accounts_pro.seed_accounts_pro_track
"""

import json
import os

import frappe

ORDER = ["chart_gl"]

TRACK = {
	"title": "ZhiftERP Accounts Professional",
	"serial_prefix": "ZERP-ACCPRO",
	"description": "The complete finance certification: the chart of accounts and the general ledger, journal entries and the manual layer, banking and reconciliation, receivables and payables from the accounts chair, tax accounting and Nigerian compliance, cost centers and dimensions, period close and financial statements, and the advanced accounts layer — proctored examinations from the account tree to the statements that run the firm.",
}


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_accounts_pro_data.json")
	with open(path) as f:
		return json.load(f)


def seed_accounts_pro_track():
	data = _data()
	if not frappe.db.exists("Duty Product", "ZhiftERP Accounts"):
		frappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP Accounts", "active": 1, "sort_order": 8}).insert(
			ignore_permissions=True
		)
		print("created Duty Product: ZhiftERP Accounts")

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
				"product": "ZhiftERP Accounts",
				"description": m["desc"],
				"active": 1,
				"audience": "Both",
				"sort_order": 90 + i,
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
				"product": "ZhiftERP Accounts",
				"audience": "Consultant",
				"serial_prefix": TRACK["serial_prefix"],
				"description": TRACK["description"],
				"active": 1,
				"modules": [{"module": module_names[k]} for k in ORDER],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

	frappe.db.commit()
	print("ZhiftERP Accounts Professional track ready.")


def refresh_lessons(only=None):
	"""Replace lesson content on ALREADY-SEEDED modules from the data
	file (matched by title). Clears lesson read-progress for refreshed
	modules. Questions untouched. Pass only=<module_key> for a single
	module."""
	data = _data()
	refreshed = 0
	keys = [only] if only else ORDER
	for key in keys:
		if key not in data:
			print(f"unknown module key: {key}")
			continue
		m = data[key]
		mod = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
		if not mod:
			print(f"module not seeded yet (skipped): {m['title']}")
			continue
		for row in frappe.get_all("Duty Lesson", filters={"module": mod}, pluck="name"):
			frappe.delete_doc("Duty Lesson", row, ignore_permissions=True, force=True)
		for row in frappe.get_all("Duty Lesson Progress", filters={"module": mod}, pluck="name"):
			frappe.delete_doc("Duty Lesson Progress", row, ignore_permissions=True, force=True)
		for j, l in enumerate(m["lessons"]):
			frappe.get_doc(
				{
					"doctype": "Duty Lesson",
					"module": mod,
					"title": l["title"],
					"sort_order": j,
					"est_minutes": l["est"],
					"content": l["html"],
				}
			).insert(ignore_permissions=True)
		refreshed += 1
		print(f"refreshed: {m['title']} ({len(m['lessons'])} lessons)")
	frappe.db.commit()
	print(f"{refreshed} module(s) refreshed. Read-progress reset for refreshed modules.")


def refresh_questions(only=None):
	"""Replace a seeded module's question bank from the data file
	(matched by title). Past attempts keep stored results. Pass
	only=<module_key> for one module, else all in ORDER."""
	data = _data()
	keys = [only] if only else ORDER
	for key in keys:
		if key not in data:
			print(f"unknown module key: {key}")
			continue
		m = data[key]
		mod = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
		if not mod:
			print(f"module not seeded yet (skipped): {m['title']}")
			continue
		for row in frappe.get_all("Duty Quiz Question", filters={"module": mod}, pluck="name"):
			frappe.delete_doc("Duty Quiz Question", row, ignore_permissions=True, force=True)
		for q in m["questions"]:
			frappe.get_doc(
				{
					"doctype": "Duty Quiz Question",
					"module": mod,
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
		print(f"bank refreshed: {m['title']} ({len(m['questions'])} questions)")
	frappe.db.commit()
	print("Question banks refreshed.")
