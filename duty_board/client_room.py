"""Client Rooms: one room per customer, two faces, a membrane between.

Staff endpoints require a System User session. Client endpoints require a
Website User session and resolve the caller's room from their membership as
the FIRST act — nothing is ever queried by a client-supplied identifier.
Internal ("whisper") messages never cross the membrane.
"""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

MSG_MAX = 2000
CLIENT_STATUS = {"To Do": "Queued", "In Progress": "In Progress", "Completed": "Done"}


# ---------------- membrane guards ----------------


def _staff_only():
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)


def _client_room():
	"""Resolve the calling Website User's room. The only door clients have."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if frappe.db.get_value("User", user, "user_type") != "Website User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	member = frappe.get_all(
		"Client Room Member",
		filters={"user": user, "active": 1},
		fields=["room"],
		limit=1,
	)
	if not member:
		frappe.throw(_("No room is linked to your account — contact Xlevel support."))
	room = frappe.get_doc("Client Room", member[0].room)
	if room.status != "Active":
		frappe.throw(_("This room is not currently active."))
	return room


def _room_payload(room, include_internal, before=None, limit=40):
	filters = {"room": room.name}
	if not include_internal:
		filters["internal"] = 0
	if before:
		filters["creation"] = ["<", before]
	rows = frappe.get_all(
		"Client Room Message",
		filters=filters,
		fields=["name", "message", "internal", "owner", "creation"],
		order_by="creation desc",
		limit=min(cint(limit) or 40, 100),
	)
	has_more = len(rows) >= min(cint(limit) or 40, 100)
	rows.reverse()
	names = {}
	for r in rows:
		r.creation = str(r.creation)
		r.who = names.setdefault(
			r.owner, frappe.utils.get_fullname(r.owner) or r.owner
		)
		r.is_staff = frappe.db.get_value("User", r.owner, "user_type") == "System User"
	return rows, has_more


def _visible_tasks(room):
	if not room.project:
		return []
	rows = frappe.get_all(
		"Duty Project Task",
		filters={"project": room.project, "client_visible": 1},
		fields=["name", "title", "column", "assignee", "modified"],
		order_by="modified desc",
		limit=100,
	)
	out = []
	for t in rows:
		status = CLIENT_STATUS.get(t.column)
		if not status:
			continue  # Suspended stays behind the membrane
		out.append(
			{
				"title": t.title,
				"status": status,
				"assignee_first": (
					frappe.utils.get_fullname(t.assignee).split(" ")[0]
					if t.assignee
					else None
				),
			}
		)
	return out


def _ensure_project(room):
	if room.project and frappe.db.exists("Duty Project", room.project):
		return room.project
	customer_name = room.customer
	proj = frappe.get_doc(
		{
			"doctype": "Duty Project",
			"project_name": f"{customer_name} — Requests",
			"customer": customer_name,
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	room.db_set("project", proj.name, update_modified=False)
	room.project = proj.name
	return proj.name


def _post(room, text, internal=0):
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Message is empty."))
	if len(text) > MSG_MAX:
		frappe.throw(_("Message is too long."))
	doc = frappe.get_doc(
		{
			"doctype": "Client Room Message",
			"room": room.name,
			"message": text,
			"internal": cint(internal),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.publish_realtime("duty_client_room", {"room": room.name})
	return doc


# ---------------- staff face ----------------


@frappe.whitelist()
def get_rooms():
	_staff_only()
	rooms = frappe.get_all(
		"Client Room",
		filters={"status": ["!=", "Archived"]},
		fields=["name", "customer", "status", "project"],
		order_by="modified desc",
	)
	for r in rooms:
		last = frappe.get_all(
			"Client Room Message",
			filters={"room": r.name},
			fields=["message", "creation", "owner"],
			order_by="creation desc",
			limit=1,
		)
		r.last = last[0].message[:60] if last else ""
		r.last_when = str(last[0].creation) if last else None
		r.members = frappe.db.count("Client Room Member", {"room": r.name, "active": 1})
	return rooms


@frappe.whitelist()
def create_room(customer):
	_staff_only()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Unknown customer."))
	existing = frappe.db.get_value("Client Room", {"customer": customer})
	if existing:
		return existing
	doc = frappe.get_doc(
		{"doctype": "Client Room", "customer": customer, "status": "Active"}
	).insert(ignore_permissions=True)
	_ensure_project(doc)
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def get_room(name, before=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	messages, has_more = _room_payload(room, include_internal=True, before=before)
	members = frappe.get_all(
		"Client Room Member",
		filters={"room": name, "active": 1},
		fields=["name", "user"],
	)
	for m in members:
		m.full_name = frappe.utils.get_fullname(m.user)
	return {
		"name": room.name,
		"customer": room.customer,
		"status": room.status,
		"project": room.project,
		"messages": messages,
		"has_more": has_more,
		"members": members,
		"tasks": _visible_tasks(room),
	}


@frappe.whitelist()
def post_message(name, message, internal=0):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	if room.status != "Active" and not cint(internal):
		frappe.throw(_("Room is frozen — only internal notes allowed."))
	_post(room, message, internal)
	return get_room(name)


@frappe.whitelist()
def add_member(name, email, full_name=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	email = (email or "").strip().lower()
	if not email or "@" not in email:
		frappe.throw(_("Give a valid email."))
	if frappe.db.exists("User", email):
		utype = frappe.db.get_value("User", email, "user_type")
		if utype != "Website User":
			frappe.throw(_("{0} is a staff account — clients must be portal users.").format(email))
	else:
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": (full_name or email.split("@")[0]).strip(),
				"user_type": "Website User",
				"send_welcome_email": 1,
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Client Room Member", {"room": name, "user": email}):
		frappe.get_doc(
			{"doctype": "Client Room Member", "room": name, "user": email, "active": 1}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def remove_member(member_name):
	_staff_only()
	frappe.db.set_value("Client Room Member", member_name, "active", 0, update_modified=False)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def set_room_status(name, status):
	_staff_only()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only System Managers can freeze or archive rooms."))
	if status not in ("Active", "Frozen", "Archived"):
		frappe.throw(_("Bad status."))
	frappe.db.set_value("Client Room", name, "status", status, update_modified=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def make_task_from_message(name, title):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the task a title."))
	project = _ensure_project(room)
	from duty_board.projects import create_task

	create_task(project, title)
	card = frappe.get_all(
		"Duty Project Task",
		filters={"project": project, "title": title},
		order_by="creation desc",
		limit=1,
	)[0].name
	frappe.db.set_value(
		"Duty Project Task", card, "client_visible", 1, update_modified=False
	)
	_post(room, _("📋 Logged: “{0}” → Queued").format(title))
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def set_card_visibility(card, visible):
	_staff_only()
	frappe.db.set_value(
		"Duty Project Task", card, "client_visible", cint(visible), update_modified=False
	)
	frappe.db.commit()
	return {"ok": True}


# ---------------- client face (portal) ----------------


@frappe.whitelist()
def client_get_room(before=None):
	room = _client_room()
	messages, has_more = _room_payload(room, include_internal=False, before=before)
	return {
		"customer": room.customer,
		"messages": messages,
		"has_more": has_more,
		"tasks": _visible_tasks(room),
	}


@frappe.whitelist()
def client_post_message(message):
	room = _client_room()
	_post(room, message, internal=0)
	# staff hear about client words
	try:
		from duty_board.api import _notify_user

		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		for u in frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			fields=["name"],
		):
			if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
				_notify_user(
					u.name,
					_("🤝 {0} · {1}").format(first, room.customer),
					(message or "")[:120],
				)
	except Exception:
		pass
	return client_get_room()


@frappe.whitelist()
def client_request_task(title):
	room = _client_room()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Describe what you need."))
	if len(title) > 200:
		frappe.throw(_("Keep the request under 200 characters."))
	project = _ensure_project(room)
	frappe.get_doc(
		{
			"doctype": "Duty Project Task",
			"project": project,
			"title": title,
			"column": "To Do",
			"urgency": "Medium",
			"client_visible": 1,
			"client_requested": 1,
		}
	).insert(ignore_permissions=True)
	_post(room, _("🙋 Requested: “{0}” → Queued").format(title))
	frappe.db.commit()
	return client_get_room()
