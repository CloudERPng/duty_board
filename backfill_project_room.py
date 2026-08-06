"""Backfill Duty Project.room — assign each project to its customer's main room.

Projects are moving from customer-scoped to room-scoped (a project belongs
to exactly one room). Existing projects have no room. This assigns each to
its customer's MAIN room so nothing is orphaned:

  main room = the Financial Room if one is flagged, else the oldest active
  (non-archived) room for that customer.

After deploy, staff reassign individual projects to the correct room by
hand (e.g. moving "Still testing implement" to a second room). Until then
every project has a home and the customer's main room shows them all —
exactly today's behaviour for that room.

Idempotent: only touches projects whose room is null/empty.
"""

import frappe


def execute():
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
