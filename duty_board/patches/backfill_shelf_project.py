"""Backfill Client Shelf Doc.project for docs that predate the field."""

import frappe


def execute():
	if not frappe.db.has_column("Client Shelf Doc", "project"):
		return

	from duty_board.client_room import _ensure_project

	rooms = {}
	docs = frappe.get_all(
		"Client Shelf Doc",
		filters={"project": ["in", [None, ""]]},
		fields=["name", "room"],
	)
	for d in docs:
		if not d.room:
			continue
		proj = rooms.get(d.room)
		if proj is None:
			try:
				room_doc = frappe.get_doc("Client Room", d.room)
				proj = _ensure_project(room_doc)
			except Exception:
				proj = ""
			rooms[d.room] = proj
		if proj:
			frappe.db.set_value("Client Shelf Doc", d.name, "project", proj, update_modified=False)

	frappe.db.commit()
