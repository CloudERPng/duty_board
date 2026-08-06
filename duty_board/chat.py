"""Duty Board — the Chat face.

One flat, latest-first conversation list covering all three message
surfaces: the team room (Team Message), every client room the session
user may see (Client Room Message), and every DM thread they are a
party to (Duty DM).

Cost discipline: this endpoint is polled by a face people leave open all
day, so it must not fan out per conversation the way get_rooms() does.
Everything below is grouped SQL — a fixed number of queries regardless
of how many rooms or threads exist.

Rendering, sending, receipts and attachments all stay where they already
live (api.py, client_room.py, dm.py). This module only answers the
question "what conversations are there, and which ones are shouting?"
"""

import frappe
from frappe import _
from frappe.utils import cint

# Preview text shown under each rail row.
PREVIEW = 70


def _preview(text, prefix=""):
	t = (text or "").strip().replace("\n", " ")
	if len(t) > PREVIEW:
		t = t[: PREVIEW - 1].rstrip() + "…"
	return (prefix + t) if t else prefix.strip()


def _visible_rooms(me):
	"""Same visibility rules as client_room.get_rooms, evaluated once."""
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names
	from duty_board.client_room import _staff_sees_room

	is_consultant = require_staff_or_consultant()
	rooms = frappe.get_all(
		"Client Room",
		filters={"status": ["!=", "Archived"]},
		fields=["name", "customer", "unit", "status", "staff_users", "owner_user"],
	)
	if is_consultant:
		allowed = set(consultant_room_names())
		return [r for r in rooms if r.name in allowed]
	if "System Manager" not in frappe.get_roles():
		return [r for r in rooms if _staff_sees_room(r, me)]
	return rooms


def _room_last(room_names):
	"""Last message per room — one grouped query, not one per room."""
	if not room_names:
		return {}
	rows = frappe.db.sql(
		"""
		select m.room, m.message, m.creation, m.owner
		from `tabClient Room Message` m
		join (
			select room, max(creation) as mx
			from `tabClient Room Message`
			where room in %(rooms)s
			group by room
		) last on last.room = m.room and last.mx = m.creation
		""",
		{"rooms": tuple(room_names)},
		as_dict=True,
	)
	# A tie on creation (same room, same second) would yield two rows; the
	# last one wins, which is arbitrary but stable enough for a preview.
	return {r.room: r for r in rows}


def _room_unread(room_names, me):
	"""Unread per room, split client-authored vs everything else.

	Mirrors client_room._room_unread's semantics (own messages never count,
	Client Room Seen is the watermark) but resolves every room at once and
	classifies the author by joining tabUser instead of calling _utype per
	message.
	"""
	if not room_names:
		return {}
	rows = frappe.db.sql(
		"""
		select
			m.room,
			sum(case when u.user_type = 'Website User' then 1 else 0 end) as client,
			count(m.name) as total
		from `tabClient Room Message` m
		left join `tabUser` u on u.name = m.owner
		left join `tabClient Room Seen` s on s.room = m.room and s.user = %(me)s
		where m.room in %(rooms)s
		  and m.owner != %(me)s
		  and (s.last_seen is null or m.creation > s.last_seen)
		group by m.room
		""",
		{"rooms": tuple(room_names), "me": me},
		as_dict=True,
	)
	return {
		r.room: {
			"client": cint(r.client),
			"other": cint(r.total) - cint(r.client),
			"total": cint(r.total),
		}
		for r in rows
	}


def _team_entry(me):
	"""The Duty Room. Always present, always pinned — a team chat with no
	messages yet is still the room you talk to your colleagues in."""
	last = frappe.get_all(
		"Team Message",
		fields=["message", "creation", "full_name", "user"],
		order_by="creation desc",
		limit=1,
	)
	seen = frappe.db.get_value("Chat Seen", {"user": me}, "last_seen")
	filters = {"user": ["!=", me]}
	if seen:
		filters["creation"] = [">", seen]
	unread = frappe.db.count("Team Message", filters)

	entry = {
		"kind": "team",
		"id": "__team__",
		"title": _("Duty Room"),
		"subtitle": _("The whole team"),
		"icon": "💬",
		"pinned": 1,
		"unread": cint(unread),
		"unread_client": 0,
		"last": "",
		"last_when": None,
	}
	if last:
		who = (last[0].full_name or last[0].user or "").split(" ")[0]
		entry["last"] = _preview(last[0].message, f"{who}: " if who else "")
		entry["last_when"] = str(last[0].creation)
	return entry


def _dm_entries(me):
	"""One row per counterparty, with the text of the newest message.

	Two grouped queries: the per-thread high-water mark, then the messages
	sitting on those marks. Unread comes from dm.get_unread_map, which is
	already a single group-by.
	"""
	from duty_board.dm import get_unread_map

	pairs = frappe.db.sql(
		"""
		select
			case when sender = %(me)s then recipient else sender end as other,
			max(creation) as mx
		from `tabDuty DM`
		where sender = %(me)s or recipient = %(me)s
		group by other
		""",
		{"me": me},
		as_dict=True,
	)
	if not pairs:
		return []

	marks = [p.mx for p in pairs]
	msgs = frappe.db.sql(
		"""
		select sender, recipient, message, creation
		from `tabDuty DM`
		where (sender = %(me)s or recipient = %(me)s)
		  and creation in %(marks)s
		""",
		{"me": me, "marks": tuple(marks)},
		as_dict=True,
	)
	by_other = {}
	for m in msgs:
		other = m.recipient if m.sender == me else m.sender
		by_other[other] = m

	unread = get_unread_map(me)
	others = [p.other for p in pairs if p.other]
	names = {}
	if others:
		for u in frappe.get_all(
			"User",
			filters={"name": ["in", others]},
			fields=["name", "full_name", "enabled", "user_image"],
		):
			names[u.name] = u

	out = []
	for p in pairs:
		other = p.other
		if not other:
			continue
		u = names.get(other)
		if not u or not u.enabled:
			# Disabled colleagues drop out of the rail rather than sitting
			# there as an unclickable ghost.
			continue
		m = by_other.get(other)
		mine = m and m.sender == me
		out.append(
			{
				"kind": "dm",
				"id": other,
				"title": u.full_name or other,
				"subtitle": _("Direct message"),
				"icon": "✉",
				"image": u.user_image or None,
				"pinned": 0,
				"unread": cint(unread.get(other) or 0),
				"unread_client": 0,
				"last": _preview(m.message if m else "", _("You: ") if mine else ""),
				"last_when": str(p.mx) if p.mx else None,
			}
		)
	return out


@frappe.whitelist()
def get_rail():
	"""Every conversation the session user has, newest first.

	The team room is pinned to the top regardless of when it last spoke;
	everything else sorts purely by last_when, with never-used rooms
	falling to the bottom in customer order.
	"""
	from duty_board.permissions import require_staff_or_consultant

	is_consultant = require_staff_or_consultant()
	me = frappe.session.user

	rooms = _visible_rooms(me)
	room_names = [r.name for r in rooms]
	last_map = _room_last(room_names)
	unread_map = _room_unread(room_names, me)

	joins = {}
	if room_names:
		for j in frappe.db.sql(
			"""
			select room, count(name) as cnt
			from `tabClient Join Request`
			where room in %(rooms)s and status = 'Pending'
			group by room
			""",
			{"rooms": tuple(room_names)},
			as_dict=True,
		):
			joins[j.room] = cint(j.cnt)

	# Consultants never see the internal team room or DMs — stripped from
	# the data, not hidden by the client. dm.py and get_messages are
	# require_staff besides; this keeps the rail honest about it.
	entries = [] if is_consultant else [_team_entry(me)]

	for r in rooms:
		last = last_map.get(r.name)
		u = unread_map.get(r.name) or {"client": 0, "other": 0, "total": 0}
		entries.append(
			{
				"kind": "room",
				"id": r.name,
				"title": r.customer,
				"subtitle": r.unit or "General",
				"icon": "🤝",
				"pinned": 0,
				"status": r.status,
				"unread": cint(u["total"]),
				"unread_client": cint(u["client"]),
				"unread_other": cint(u["other"]),
				"join_requests": joins.get(r.name, 0),
				"last": _preview(last.message if last else ""),
				"last_when": str(last.creation) if last else None,
			}
		)

	if not is_consultant:
		entries.extend(_dm_entries(me))

	# Stable sort, least significant key first: alphabetical tie-break, then
	# newest-first, then silent conversations to the bottom, then pin the
	# team room. Three cheap passes beat one clever key.
	entries.sort(key=lambda e: (e.get("title") or "").lower())
	entries.sort(key=lambda e: e.get("last_when") or "", reverse=True)
	entries.sort(key=lambda e: (0 if e.get("pinned") else 1, 0 if e.get("last_when") else 1))
	return entries
