"""Backfill Duty Project.room — assign each project to its customer's main room."""

import frappe


def execute():
	if "duty_board" not in frappe.get_installed_apps():
		return
	if not frappe.db.has_column("Duty Project", "room"):
		return

	projects = frappe.get_all(
		"Duty Project",
		filters={"room": ["in", [None, ""]]},
		fields=["name", "customer"],
	)
	main_room_cache = {}
	for p in projects:
		if not p.customer:
			continue
		room = main_room_cache.get(p.customer)
		if room is None:
			room = _main_room(p.customer)
			main_room_cache[p.customer] = room or ""
		if room:
			frappe.db.set_value("Duty Project", p.name, "room", room, update_modified=False)

	frappe.db.commit()


def _main_room(customer):
	rooms = frappe.get_all(
		"Client Room",
		filters={"customer": customer, "status": ["!=", "Archived"]},
		fields=["name", "is_financial_room", "creation"],
		order_by="creation asc",
	)
	if not rooms:
		return None
	for r in rooms:
		if r.get("is_financial_room"):
			return r.name
	return rooms[0].name
