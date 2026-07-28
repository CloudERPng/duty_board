"""Client course seed — Understanding Your Monthly Reports (approved 28-07-2026).

Audience: Client. Product: Accounting Services — every accounting client's
room is already tagged, so the course appears in their 🎯 catalogue on
seeding, dormant until pursued. Light quiz (15 bank / 10 served / pass 70);
no certificate track by design — module completion is the credential.

The client catalogue is track-based, so the module ships inside a
single-module track (XLV-READER) — completing it issues a small certificate.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_client_reports.seed_client_reports_course
Idempotent; safe to rerun after v2.92.0 (module is kept, track is added).
"""

import json
import os

import frappe


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_client_reports_data.json")
	with open(path) as f:
		return json.load(f)


def seed_client_reports_course():
	m = _data()["reports"]
	if not frappe.db.exists("Duty Product", "Accounting Services"):
		print("Duty Product 'Accounting Services' missing — run accounting.sync_accounting_clients first.")
		return
	mod_name = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
	if mod_name:
		print(f"module exists: {m['title']}")
		_ensure_track(mod_name)
		return
	mod = frappe.get_doc(
		{
			"doctype": "Duty Training Module",
			"title": m["title"],
			"product": "Accounting Services",
			"description": m["desc"],
			"active": 1,
			"audience": "Client",
			"sort_order": 30,
			"pass_mark": 70,
		}
	).insert(ignore_permissions=True)
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
	_ensure_track(mod.name)
	frappe.db.commit()
	print(f"seeded: {m['title']} ({len(m['lessons'])} lessons, {len(m['questions'])} questions) — audience Client, product Accounting Services")


def _ensure_track(module_name):
	title = "Understanding Your Monthly Reports"
	if frappe.db.exists("Duty Certification Track", {"title": title}):
		print("track exists: " + title)
		return
	frappe.get_doc(
		{
			"doctype": "Duty Certification Track",
			"title": title,
			"product": "Accounting Services",
			"audience": "Client",
			"serial_prefix": "XLV-READER",
			"description": "For business owners: read the statements your accounting team sends every month — the reports, the five checks worth doing, and how to get the most from the service.",
			"active": 1,
			"modules": [{"module": module_name}],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	print("created track: " + title + " (XLV-READER, 1 module)")
