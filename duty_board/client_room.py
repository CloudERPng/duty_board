"""Client Rooms: one room per customer, two faces, a membrane between.

Staff endpoints require a System User session. Client endpoints require a
Website User session and resolve the caller's room from their membership as
the FIRST act — nothing is ever queried by a client-supplied identifier.
Internal ("whisper") messages never cross the membrane.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime, today
from frappe.utils.pdf import get_pdf
from frappe.rate_limiter import rate_limit

MSG_MAX = 2000
CLIENT_STATUS = {"To Do": "Queued", "In Progress": "In Progress", "Completed": "Done"}


# ---------------- membrane guards ----------------


def _staff_only():
	from duty_board.permissions import require_staff

	require_staff()


RENEWAL_GRACE_DAYS = 14


def _renewal_info(customer):
	"""days_left (negative = overdue), frozen flag. None if no date set."""
	try:
		d = frappe.db.get_value("Customer", customer, "renewal_date")
	except Exception:
		return None
	if not d:
		return None
	days_left = (getdate(d) - getdate(today())).days
	return {
		"date": str(d),
		"days_left": days_left,
		"frozen": days_left < -RENEWAL_GRACE_DAYS,
	}


def _client_memberships():
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if frappe.db.get_value("User", user, "user_type") != "Website User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	return frappe.get_all(
		"Client Room Member",
		filters={"user": user, "active": 1},
		fields=["room"],
	)


def _client_room(allow_frozen=False):
	"""Resolve the calling Website User's room. The only door clients have.
	With multiple memberships the portal names a room via xl_room — honored
	only if it is in the caller's own membership set. A room whose customer's
	renewal is past grace is frozen: only the notice endpoint may pass."""
	memberships = _client_memberships()
	want = frappe.form_dict.get("xl_room")
	if want:
		if want not in {m.room for m in memberships}:
			frappe.throw(_("Not permitted."), frappe.PermissionError)
		room = frappe.get_doc("Client Room", want)
		if room.status == "Archived":
			frappe.throw(_("This room is closed."), frappe.PermissionError)
		_renewal_gate(room, allow_frozen)
		return room
	member = memberships[:1]
	if not member:
		frappe.throw(_("No room is linked to your account — contact Xlevel support."))
	room = frappe.get_doc("Client Room", member[0].room)
	if room.status != "Active":
		frappe.throw(_("This room is not currently active."))
	_renewal_gate(room, allow_frozen)
	return room


def _renewal_gate(room, allow_frozen):
	if allow_frozen:
		return
	info = _renewal_info(room.customer)
	if info and info["frozen"]:
		frappe.throw(
			_("Your portal is paused — subscription renewal is overdue. Please contact your account manager."),
			frappe.PermissionError,
		)


def _room_payload(room, include_internal, before=None, limit=40):
	filters = {"room": room.name}
	if not include_internal:
		filters["internal"] = 0
	if before:
		filters["creation"] = ["<", before]
	rows = frappe.get_all(
		"Client Room Message",
		filters=filters,
		fields=[
			"name", "message", "internal", "owner", "creation", "edited_on",
			"attachment_url", "attachment_name", "ref",
		],
		order_by="creation desc",
		limit=min(cint(limit) or 40, 100),
	)
	has_more = len(rows) >= min(cint(limit) or 40, 100)
	rows.reverse()
	names = {}
	for r in rows:
		r.creation = str(r.creation)
		r.edited_on = str(r.edited_on) if r.get("edited_on") else None
		r.who = names.setdefault(
			r.owner, frappe.utils.get_fullname(r.owner) or r.owner
		)
		r.is_staff = frappe.db.get_value("User", r.owner, "user_type") == "System User"
		r.mine = 1 if r.owner == frappe.session.user else 0
		ext = (r.attachment_name or "").lower().rsplit(".", 1)[-1]
		r.is_image = ext in ("png", "jpg", "jpeg", "gif", "webp")
		r.is_audio = ext in ("webm", "ogg", "mp3", "m4a", "wav")
	by_name = {r.name: r for r in rows}
	for r in rows:
		if not r.get("ref"):
			continue
		t = by_name.get(r.ref)
		if t is None:
			t = frappe.db.get_value(
				"Client Room Message",
				{"name": r.ref, "room": room.name},
				["owner", "message", "internal"],
				as_dict=True,
			)
		if not t:
			r.ref = None
			continue
		t_internal = cint(t.get("internal"))
		if t_internal and not include_internal:
			r.ref_who = "Xlevel"
			r.ref_text = "🔒 …"
		else:
			r.ref_who = (
				frappe.utils.get_fullname(t.get("owner")) or t.get("owner") or ""
			).split(" ")[0]
			r.ref_text = (t.get("message") or "📎")[:90]
	return rows, has_more


ISSUE_CLIENT_STATUS = {
	"Open": "Queued",
	"In Progress": "In Progress",
	"Resolved": "Done",
	"Closed": "Done",
}


def _project_names(room):
	"""name -> display label for THIS ROOM's active projects. The room's
	auto-created catch-all ("… — Requests") shows as "General Requests"."""
	out = {}
	for p in frappe.get_all(
		"Duty Project",
		filters={"room": room.name, "status": "Active"},
		fields=["name", "project_name"],
	):
		label = p.project_name or p.name
		if label.endswith("— Requests") or label.endswith("- Requests"):
			label = "General Requests"
		out[p.name] = label
	return out


def _work_rows(room):
	"""Everything client-visible for this customer: issues + project milestones."""
	out = []
	issues = frappe.get_all(
		"Duty Issue",
		filters={"customer": room.customer, "client_visible": 1},
		fields=[
			"name", "title", "status", "client_requested", "modified",
			"creation", "work_started_at", "resolved_at", "acknowledged_by", "client_confirmed_at", "client_stars",
			"source_type", "source",
		],
		order_by="creation desc",
		limit=100,
	)
	issues = [i for i in issues if _issue_in_room(i, room)]
	names = [i.name for i in issues]
	first_assignee = {}
	if names:
		for a in frappe.get_all(
			"Duty Issue Assignee",
			filters={"parent": ["in", names]},
			fields=["parent", "user"],
			order_by="idx asc",
		):
			first_assignee.setdefault(a.parent, a.user)
	for i in issues:
		status = ISSUE_CLIENT_STATUS.get(i.status)
		if not status:
			continue
		out.append(
			{
				"name": i.name,
				"kind": "issue",
				"title": i.title,
				"status": status,
				"client_requested": i.client_requested,
				"assignee_first": (
					frappe.utils.get_fullname(first_assignee[i.name]).split(" ")[0]
					if i.name in first_assignee
					else None
				),
				"reported": str(i.creation)[:16],
				"started": str(i.work_started_at)[:16] if i.work_started_at else None,
				"done": str(i.resolved_at)[:16] if i.resolved_at else None,
				"seen": bool(i.acknowledged_by),
				"confirmed": 1 if i.client_confirmed_at else 0,
				"stars": cint(i.client_stars) or 0,
				"modified": i.modified,
				"project": None,
				"project_name": None,
			}
		)
	projs = frappe.get_all(
		"Duty Project",
		filters={"room": room.name, "status": "Active"},
		pluck="name",
	)
	if projs:
		pnames = _project_names(room)
		for t in frappe.get_all(
			"Duty Project Task",
			filters={"project": ["in", projs], "client_visible": 1},
			fields=["name", "title", "column", "assignee", "client_requested", "modified", "creation", "project"],
		):
			status = CLIENT_STATUS.get(t.column)
			if not status:
				continue  # Suspended stays behind the membrane
			out.append(
				{
					"name": t.name,
					"kind": "card",
					"title": t.title,
					"status": status,
					"client_requested": t.client_requested,
					"assignee_first": (
						frappe.utils.get_fullname(t.assignee).split(" ")[0]
						if t.assignee
						else None
					),
					"reported": str(t.creation)[:16],
					"modified": t.modified,
					"project": t.project,
					"project_name": pnames.get(t.project),
				}
			)
	out.sort(key=lambda x: str(x.get("reported") or x.get("modified") or ""), reverse=True)
	for o in out:
		del o["modified"]
	return out[:100]


def _visible_tasks(room):
	"""Client payload: titles and statuses only — no internal identifiers."""
	return [
		{
			"id": o["name"],
			"kind": o["kind"],
			"title": o["title"],
			"status": o["status"],
			"assignee_first": o["assignee_first"],
			"reported": o.get("reported"),
			"started": o.get("started"),
			"done": o.get("done"),
			"seen": o.get("seen"),
			"confirmed": o.get("confirmed"),
			"stars": o.get("stars"),
			"project": o.get("project"),
			"project_name": o.get("project_name"),
		}
		for o in _work_rows(room)
	]


def _staff_tasks(room):
	"""Staff face gets the same rows with names and kinds so they open."""
	return _work_rows(room)


def _ensure_token(room):
	if not room.invite_token:
		token = frappe.generate_hash(length=24)
		room.db_set("invite_token", token, update_modified=False)
		room.invite_token = token
	return room.invite_token


def _ensure_project(room):
	if room.project and frappe.db.exists("Duty Project", room.project):
		return room.project
	customer_name = room.customer
	# Each room gets its own catch-all so requests from one room don't land
	# in another's bucket. Label by unit when present to keep them distinct.
	label_unit = (room.get("unit") or "General")
	proj = frappe.get_doc(
		{
			"doctype": "Duty Project",
			"project_name": f"{customer_name} · {label_unit} — Requests",
			"customer": customer_name,
			"room": room.name,
			"status": "Active",
		}
	).insert(ignore_permissions=True)
	room.db_set("project", proj.name, update_modified=False)
	room.project = proj.name
	return proj.name


def _post(room, text, internal=0, attachment_url=None, attachment_name=None, ref=None):
	text = (text or "").strip()
	if not text and not attachment_url:
		frappe.throw(_("Message is empty."))
	if len(text) > MSG_MAX:
		frappe.throw(_("Message is too long."))
	if attachment_url:
		owned = frappe.db.get_value(
			"File", {"file_url": attachment_url, "owner": frappe.session.user}, "file_name"
		)
		if not owned:
			frappe.throw(_("Upload not found — try attaching again."))
		attachment_name = (attachment_name or owned)[:120]
	if ref and not frappe.db.exists("Client Room Message", {"name": ref, "room": room.name}):
		ref = None
	doc = frappe.get_doc(
		{
			"doctype": "Client Room Message",
			"room": room.name,
			"message": text or "📎",
			"internal": cint(internal),
			"attachment_url": attachment_url,
			"attachment_name": attachment_name,
			"ref": ref,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.publish_realtime("duty_client_room", {"room": room.name})
	return doc


@frappe.whitelist()
def edit_room_message(name, message=None, drop_attachment=0):
	"""Edit own room message within 30 min. Because the room is client-visible,
	the original text is preserved as an internal audit whisper."""
	from duty_board.api import _within_edit_window

	doc = frappe.get_doc("Client Room Message", name)
	if doc.owner != frappe.session.user:
		frappe.throw(_("You can only edit your own messages."))
	if frappe.db.get_value("User", doc.owner, "user_type") != "System User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if not _within_edit_window(doc.creation):
		frappe.throw(_("The 30-minute edit window has passed."))
	room = frappe.get_doc("Client Room", doc.room)
	old_text = doc.message
	text = (message or "").strip()
	if not text and not doc.attachment_url:
		frappe.throw(_("A message cannot be empty."))
	doc.message = text or "📎"
	if cint(drop_attachment):
		doc.attachment_url = None
		doc.attachment_name = None
	doc.edited_on = frappe.utils.now_datetime()
	doc.save(ignore_permissions=True)
	# Governance trail: a whisper only staff see, naming the edit and the
	# text as the client may already have read it.
	who = frappe.utils.get_fullname(frappe.session.user)
	_post(room, _("✏ {0} edited a message (was: {1})").format(who, (old_text or "")[:200]), internal=1)
	frappe.db.commit()
	frappe.publish_realtime("duty_client_room", {"room": room.name})
	return {"ok": 1}


# ---------------- staff face ----------------


@frappe.whitelist()
def get_rooms():
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names
	_is_c = require_staff_or_consultant()
	rooms = frappe.get_all(
		"Client Room",
		filters={"status": ["!=", "Archived"]},
		fields=["name", "customer", "unit", "status", "project", "staff_users", "owner_user"],
		order_by="modified desc",
	)
	if _is_c:
		_memb = consultant_room_names()
		rooms = [r for r in rooms if r.name in _memb]
	elif "System Manager" not in frappe.get_roles():
		_me = frappe.session.user
		rooms = [r for r in rooms if _staff_sees_room(r, _me)]
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
		_u = _room_unread(r.name, frappe.session.user)
		r.unread = _u["total"]
		r.unread_client = _u["client"]
		r.unread_other = _u["other"]
		r.join_requests = frappe.db.count(
			"Client Join Request", {"room": r.name, "status": "Pending"}
		)
		try:
			r.health = _room_health(r.name)
		except Exception:
			r.health = None
		try:
			r.renewal = _renewal_info(r.customer)
		except Exception:
			r.renewal = None
	rooms.sort(key=lambda r: (r.customer, (r.unit or "General") != "General", r.unit or ""))
	return rooms


@frappe.whitelist()
def create_room(customer, unit=None):
	_staff_only()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("Unknown customer."))
	unit = (unit or "General").strip()[:40] or "General"
	existing = frappe.db.get_value("Client Room", {"customer": customer, "unit": unit})
	if existing:
		return existing
	doc = frappe.get_doc(
		{"doctype": "Client Room", "customer": customer, "unit": unit, "status": "Active"}
	).insert(ignore_permissions=True)
	_ensure_token(doc)
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def get_room(name, before=None):
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names
	_is_c = require_staff_or_consultant()
	room = frappe.get_doc("Client Room", name)
	if _is_c:
		if name not in consultant_room_names():
			frappe.throw(_("Not permitted."), frappe.PermissionError)
		# Consultants see internal whispers only when the room allows it.
		_incl = bool(cint(room.get("allow_consultant_internal")))
	elif "System Manager" not in frappe.get_roles() and not _staff_sees_room(room, frappe.session.user):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	else:
		_incl = True
	messages, has_more = _room_payload(room, include_internal=_incl, before=before)
	members = frappe.get_all(
		"Client Room Member",
		filters={"room": name, "active": 1},
		fields=["name", "user", "last_seen", "is_admin", "member_type"],
	)
	for m in members:
		m.full_name = frappe.utils.get_fullname(m.user)
		m.last_seen = str(m.last_seen) if m.last_seen else None
	requests = frappe.get_all(
		"Client Join Request",
		filters={"room": name, "status": "Pending"},
		fields=["name", "full_name", "email", "phone", "creation"],
		order_by="creation asc",
	)
	for q in requests:
		q.creation = str(q.creation)
	ret = {
		"name": room.name,
		"customer": room.customer,
		"unit": room.unit or "General",
		"renewal": _renewal_info(room.customer),
		"owner_user": room.owner_user,
		"status": room.status,
		"project": room.project,
		"products": room.products,
		"messages": messages,
		"has_more": has_more,
		"members": members,
		"requests": requests,
		"join_url": f"{frappe.utils.get_url()}/join?token={_ensure_token(room)}",
		"shelf": _shelf_rows(room),
		"meetings": _meeting_rows(room),
		"milestones": _milestone_rows(room),
		"change_requests": _chreq_rows(room),
		"unsettled": [
			dict(
				u,
				meeting_date=str(u.meeting_date),
				start_time=str(u.start_time)[:5],
			)
			for u in frappe.get_all(
				"Duty Meeting",
				filters={
					"room": room.name,
					"status": "Confirmed",
					"outcome": ["in", ["", None]],
					"meeting_date": ["<", frappe.utils.today()],
				},
				fields=["name", "topic", "meeting_date", "start_time"],
				order_by="meeting_date desc",
				limit=5,
			)
		],
		"meeting_staff": json.loads(room.meeting_staff or "[]") if room.meeting_staff else [],
		"tasks": _staff_tasks(room),
	}
	if _is_c:
		# a consultant gets the conversation, not the commercials
		ret["renewal"] = None
		ret["join_url"] = ""
		for k in (
			"requests", "change_requests", "unsettled", "meetings",
			"meeting_staff", "milestones", "shelf",
		):
			ret[k] = []
	return ret


@frappe.whitelist()
def post_message(name, message, internal=0, attachment_url=None, attachment_name=None, ref=None):
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names
	_is_c = require_staff_or_consultant()
	room = frappe.get_doc("Client Room", name)
	if _is_c:
		if name not in consultant_room_names():
			frappe.throw(_("Not permitted."), frappe.PermissionError)
	elif "System Manager" not in frappe.get_roles() and not _staff_sees_room(room, frappe.session.user):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
		internal = 0  # consultants never write internal notes, even where they may read them
	if room.status != "Active" and not cint(internal):
		frappe.throw(_("Room is frozen — only internal notes allowed."))
	_post(room, message, internal, attachment_url, attachment_name, ref)
	try:
		from duty_board.api import _notify_user, parse_mentions

		me = frappe.session.user
		first = frappe.utils.get_fullname(me).split(" ")[0]
		lock = "🔒 " if cint(internal) else ""
		for m in parse_mentions(message):
			if m != me:
				_notify_user(
					m,
					_("💬 {0} · 🤝 {1}").format(first, room.customer),
					f"{lock}{(message or '')[:120]}",
				)
		if not cint(internal):
			from duty_board.api import _push_safe

			member_mentions = set(_room_member_mentions(room, message))
			for m in member_mentions:
				if frappe.db.exists("Duty Push Subscription", {"user": m}):
					_push_safe(
						m,
						_("💬 {0} mentioned you").format(first),
						(message or "📎")[:120],
					)
				else:
					_email_mention(m, room, first, message)
			for mm in frappe.get_all(
				"Client Room Member", filters={"room": room.name, "active": 1}, fields=["user"]
			):
				if mm.user == me or mm.user in member_mentions:
					continue
				if frappe.db.exists("Duty Push Subscription", {"user": mm.user}):
					_push_safe(
						mm.user,
						_("🤝 Xlevel · {0}").format(first),
						(message or "📎")[:120],
					)
	except Exception:
		pass
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
		frappe.db.set_value("User", email, "enabled", 1, update_modified=False)
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
	existing = frappe.db.get_value("Client Room Member", {"room": name, "user": email}, "name")
	if existing:
		frappe.db.set_value("Client Room Member", existing, "active", 1, update_modified=False)
	else:
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


ISSUE_TYPES = (
	"Support", "Bug", "Feature Request", "Configuration", "Training",
	"Data Correction", "Integration", "Billing", "Implementation",
)


def _new_client_issue(room, title, requested=0, raised_by=None, detail=None, issue_type=None, source_message=None):
	doc = frappe.get_doc(
		{
			"doctype": "Duty Issue",
			"title": title[:140],
			"description": (detail or "").strip()[:2000] or None,
			"issue_type": issue_type if issue_type in ISSUE_TYPES else "Support",
			"customer": room.customer,
			"severity": "Medium",
			"status": "Open",
			"raised_by": raised_by or frappe.session.user,
			"source_type": "Client Room",
			"source": room.name,
			"source_message": source_message or None,
			"client_visible": 1,
			"client_requested": cint(requested),
		}
	).insert(ignore_permissions=True)
	try:
		from duty_board.api import stamp_sla

		stamp_sla(doc.name, doc.severity, doc.creation)
	except Exception:
		pass
	return doc


@frappe.whitelist()
def make_task_from_message(name, title, detail=None, msg=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the issue a title."))
	if msg:
		m_room = frappe.db.get_value("Client Room Message", msg, "room")
		if m_room != room.name:
			msg = None
	_new_client_issue(room, title, detail=detail, source_message=msg)
	_post(room, _("⚠ Logged: “{0}” → Queued").format(title))
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
def client_my_rooms():
	out = []
	for m in _client_memberships():
		r = frappe.db.get_value(
			"Client Room", m.room, ["name", "customer", "unit", "status"], as_dict=True
		)
		if r and r.status != "Archived":
			out.append({"name": r.name, "customer": r.customer, "unit": r.unit or "General"})
	out.sort(key=lambda r: (r["customer"], r["unit"] != "General", r["unit"]))
	return out


@frappe.whitelist()
def client_get_room(before=None):
	room = _client_room(allow_frozen=True)
	member = frappe.db.exists(
		"Client Room Member", {"room": room.name, "user": frappe.session.user}
	)
	if member:
		frappe.db.set_value(
			"Client Room Member", member, "last_seen", now_datetime(), update_modified=False
		)
	messages, has_more = _room_payload(room, include_internal=False, before=before)
	return {
		"customer": room.customer,
		"room": room.name,
		"unit": room.unit or "General",
		"renewal": _renewal_info(room.customer),
		"manager_first": (
			frappe.utils.get_fullname(room.owner_user).split(" ")[0]
			if room.owner_user
			else None
		),
		"me": frappe.utils.get_fullname(frappe.session.user),
		"messages": messages,
		"has_more": has_more,
		"tasks": _visible_tasks(room),
	}


def _after_hours_payload():
	"""Non-None outside working hours (configured days/hours in Duty Settings,
	site time). The emergency contact is the CURRENT on-call person from the
	board's rota, their phone read from their User record — the number
	travels ONLY in this payload."""
	now = now_datetime()
	day_idx = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
	start, end, days = 9, 18, {0, 1, 2, 3, 4}
	try:
		s = frappe.get_cached_doc("Duty Settings")
		start = cint(s.get("work_start_hour")) or 9
		end = cint(s.get("work_end_hour")) or 18
		raw = (s.get("workdays") or "").strip()
		if raw:
			parsed = {day_idx[t.strip()[:3].lower()] for t in raw.split(",") if t.strip()[:3].lower() in day_idx}
			if parsed:
				days = parsed
	except Exception:
		pass
	if now.weekday() in days and start <= now.hour < end:
		return None
	oncall_name, oncall_phone = "", ""
	try:
		from duty_board.api import on_call_info

		info = on_call_info()
		if info:
			u = frappe.db.get_value("User", info["user"], ["full_name", "mobile_no", "phone"], as_dict=True)
			if u:
				oncall_name = u.full_name or info["first"]
				oncall_phone = (u.mobile_no or u.phone or "").strip()
	except Exception:
		pass
	return {
		"start": f"{start:02d}:00",
		"end": f"{end:02d}:00",
		"oncall_name": oncall_name,
		"oncall_phone": oncall_phone,
	}

@frappe.whitelist()
def client_post_message(message, attachment_url=None, attachment_name=None, ref=None):
	room = _client_room()
	_post(
		room,
		message,
		internal=0,
		attachment_url=attachment_url,
		attachment_name=attachment_name,
		ref=ref,
	)
	# staff hear about client words; @mentioned staff hear personally
	try:
		from duty_board.api import _notify_user, parse_mentions

		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		mentioned = set(parse_mentions(message))
		for m in mentioned:
			_notify_user(
				m,
				_("💬 {0} ({1}) mentioned you").format(first, room.customer),
				(message or "")[:120],
			)
		for u in frappe.get_all(
			"User",
			filters={"enabled": 1, "user_type": "System User"},
			fields=["name"],
		):
			if u.name in mentioned:
				continue
			if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
				_notify_user(
					u.name,
					_("🤝 {0} · {1}").format(first, room.customer),
					(message or "")[:120],
				)
		from duty_board.api import _push_safe as _ps

		for m in _room_member_mentions(room, message):
			if m == frappe.session.user:
				continue
			if frappe.db.exists("Duty Push Subscription", {"user": m}):
				_ps(m, _("💬 {0} mentioned you").format(first), (message or "")[:120])
			else:
				_email_mention(m, room, first, message)
	except Exception:
		pass
	ret = client_get_room()
	ret["after_hours"] = _after_hours_payload()
	ret["scope_note"] = frappe.db.get_value("Client Room", ret.get("room"), "scope_note") if ret.get("room") else ""
	ret["support_plan"] = frappe.db.get_value("Client Room", ret.get("room"), "support_plan") if ret.get("room") else ""
	return ret


def _serve_file(fdoc, filename):
	"""Images, PDFs and plain text display INLINE (a real werkzeug
	Response — frappe's binary builder ignores display_content_as);
	everything else downloads as before."""
	import mimetypes

	fname = (filename or fdoc.file_name or "file").replace('"', "")
	mimetype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
	if mimetype.startswith("image/") or mimetype in ("application/pdf", "text/plain"):
		from werkzeug.wrappers import Response

		return Response(
			fdoc.get_content(),
			mimetype=mimetype,
			headers={
				"Content-Disposition": 'inline; filename="{0}"'.format(fname),
				"Cache-Control": "private, max-age=300",
			},
		)
	frappe.local.response.filename = fname
	frappe.local.response.filecontent = fdoc.get_content()
	frappe.local.response.type = "binary"
	frappe.local.response.content_type = mimetype


@frappe.whitelist()
def client_rate_stars(id, stars):
	room = _client_room()
	row = _client_issue_for_room(room, id)
	stars = cint(stars)
	if stars < 1 or stars > 5:
		frappe.throw(_("Rate between 1 and 5 stars."))
	if row.status not in ("Resolved", "Closed"):
		frappe.throw(_("You can rate once the work is resolved."))
	frappe.db.set_value("Duty Issue", row.name, {
		"client_stars": stars,
		"client_rating": "Up" if stars >= 4 else "Down" if stars <= 2 else None,
	}, update_modified=False)
	frappe.db.commit()
	_post(room, ("⭐" * stars) + _(" — rating for “{0}”").format(row.title))
	return {"ok": True, "stars": stars}


@frappe.whitelist()
def client_confirm_resolution(id):
	room = _client_room()
	row = _client_issue_for_room(room, id)
	if row.status not in ("Resolved", "Closed"):
		frappe.throw(_("Nothing to confirm yet."))
	if row.client_confirmed_at:
		return {"ok": True}
	frappe.db.set_value("Duty Issue", row.name, "client_confirmed_at", now_datetime(), update_modified=False)
	frappe.db.commit()
	full = frappe.utils.get_fullname(frappe.session.user)
	_post(room, _("✅ Resolution confirmed by {0} — “{1}”").format(full, row.title))
	try:
		from duty_board.api import _notify_user

		for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"):
			if frappe.db.exists("Duty Push Subscription", {"user": u}):
				_notify_user(u, _("✅ Confirmed · {0}").format(room.customer), row.title[:120])
	except Exception:
		pass
	return {"ok": True}


@frappe.whitelist()
def client_reopen(id, comment):
	room = _client_room()
	row = _client_issue_for_room(room, id)
	comment = (comment or "").strip()
	if not comment:
		frappe.throw(_("Tell us what still isn't right — it goes straight to the team."))
	if row.status not in ("Resolved", "Closed"):
		frappe.throw(_("This task is still open."))
	doc = frappe.get_doc("Duty Issue", row.name)
	doc.status = "In Progress"
	doc.save(ignore_permissions=True)
	frappe.db.set_value("Duty Issue", row.name, "client_confirmed_at", None, update_modified=False)
	# A rejected resolution is not a resolution: clear resolved_at so the
	# earnings auto-pay clock stops, and sla_res_met so a failed fix
	# doesn't keep its SLA credit. Both re-set on genuine re-resolution.
	frappe.db.set_value("Duty Issue", row.name, "resolved_at", None, update_modified=False)
	frappe.db.set_value("Duty Issue", row.name, "sla_res_met", 0, update_modified=False)
	frappe.db.commit()
	full = frappe.utils.get_fullname(frappe.session.user)
	_post(room, _("↩️ Reopened by {0} — “{1}”: {2}").format(full, row.title, comment[:500]))
	try:
		from duty_board.api import _notify_user

		for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"):
			if frappe.db.exists("Duty Push Subscription", {"user": u}):
				_notify_user(u, _("↩️ REOPENED · {0}").format(room.customer), row.title[:120])
	except Exception:
		pass
	return {"ok": True}


def _client_issue_for_room(room, issue_name):
	row = frappe.db.get_value(
		"Duty Issue",
		issue_name,
		[
			"name", "title", "status", "customer", "client_visible",
			"client_requested", "description", "creation",
			"work_started_at", "resolved_at", "acknowledged_by", "acknowledged_at",
			"source_type", "source", "issue_type",
			"resolution", "client_stars", "client_confirmed_at",
		],
		as_dict=True,
	)
	if not row or row.customer != room.customer or not cint(row.client_visible):
		frappe.throw(_("Not found."), frappe.PermissionError)
	if not _issue_in_room(row, room):
		frappe.throw(_("Not found."), frappe.PermissionError)
	try:
		from duty_board.api import SLA_MATRIX, _bh_between, _bh_fmt

		full = frappe.db.get_value(
			"Duty Issue",
			issue_name,
			["severity", "sla_ack_due", "sla_ack_met", "sla_res_met"],
			as_dict=True,
		)
		if full and full.sla_ack_due:
			ack_h, res_h = SLA_MATRIX.get(full.severity or "Medium", SLA_MATRIX["Medium"])
			lines = [
				{
					"label": _("Our promise"),
					"text": _("response within {0} business hours, resolution within {1}").format(
						ack_h, res_h
					),
				}
			]
			if row.get("acknowledged_at") and row.get("creation"):
				mins = _bh_between(row.creation, row.acknowledged_at)
				lines.append(
					{
						"label": _("Responded"),
						"text": _("in {0}").format(_bh_fmt(mins)),
						"ok": cint(full.sla_ack_met),
					}
				)
			if row.get("resolved_at") and row.get("creation"):
				mins = _bh_between(row.creation, row.resolved_at)
				lines.append(
					{
						"label": _("Resolved"),
						"text": _("in {0}").format(_bh_fmt(mins)),
						"ok": cint(full.sla_res_met),
					}
				)
			row.sla_lines = lines
	except Exception:
		pass
	return row


@frappe.whitelist()
def client_task_detail(id, kind):
	room = _client_room()
	if kind == "issue":
		row = _client_issue_for_room(room, id)
		files = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Duty Issue", "attached_to_name": row.name},
			fields=["name", "file_name"],
			order_by="creation asc",
		)
		image_exts = ("png", "jpg", "jpeg", "gif", "webp")
		atts = [
			{
				"id": f.name,
				"file_name": f.file_name,
				"is_image": (f.file_name or "").lower().rsplit(".", 1)[-1] in image_exts,
			}
			for f in files
		]
		assignee = frappe.get_all(
			"Duty Issue Assignee",
			filters={"parent": row.name},
			fields=["user"],
			order_by="idx asc",
			limit=1,
		)
		return {
			"kind": "issue",
			"title": row.title,
			"status": ISSUE_CLIENT_STATUS.get(row.status, row.status),
			"client_requested": cint(row.client_requested),
			"detail": row.description,
			"reported": str(row.creation)[:16],
			"started": str(row.work_started_at)[:16] if row.work_started_at else None,
			"done": str(row.resolved_at)[:16] if row.resolved_at else None,
			"assignee_first": (
				frappe.utils.get_fullname(assignee[0].user).split(" ")[0]
				if assignee
				else None
			),
			"seen_by": (
				frappe.utils.get_fullname(row.acknowledged_by).split(" ")[0]
				if row.acknowledged_by
				else None
			),
			"seen_at": str(row.acknowledged_at)[:16] if row.acknowledged_at else None,
			"issue_type": row.get("issue_type"),
			"sla_lines": row.get("sla_lines"),
			"updates": __import__("duty_board.api", fromlist=["x"])._issue_updates(row.name, 10),
			"resolution": row.get("resolution"),
			"client_stars": cint(row.get("client_stars")) or None,
			"client_confirmed_at": str(row.client_confirmed_at)[:16] if row.get("client_confirmed_at") else None,
			"attachments": atts,
		}
	if kind == "card":
		t = frappe.db.get_value(
			"Duty Project Task",
			id,
			[
				"name", "title", "column", "assignee", "description",
				"creation", "client_visible", "client_requested", "project",
			],
			as_dict=True,
		)
		if not t or not cint(t.client_visible):
			frappe.throw(_("Not found."), frappe.PermissionError)
		cust = frappe.db.get_value("Duty Project", t.project, "customer")
		if cust != room.customer:
			frappe.throw(_("Not found."), frappe.PermissionError)
		status = CLIENT_STATUS.get(t.column)
		if not status:
			frappe.throw(_("Not found."), frappe.PermissionError)
		steps_total = frappe.db.count("Duty Project Subtask", {"parent": t.name})
		steps_done = frappe.db.count("Duty Project Subtask", {"parent": t.name, "status": "Done"}) if steps_total else 0
		return {
			"kind": "card",
			"title": t.title,
			"status": status,
			"client_requested": cint(t.client_requested),
			"steps_done": steps_done,
			"steps_total": steps_total,
			"detail": t.description,
			"reported": str(t.creation)[:16],
			"started": None,
			"done": None,
			"assignee_first": (
				frappe.utils.get_fullname(t.assignee).split(" ")[0] if t.assignee else None
			),
			"attachments": [],
		}
	frappe.throw(_("Not found."), frappe.PermissionError)


@frappe.whitelist()
def client_issue_file(fid):
	room = _client_room()
	fdoc = frappe.get_doc("File", fid)
	if fdoc.attached_to_doctype != "Duty Issue" or not fdoc.attached_to_name:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	_client_issue_for_room(room, fdoc.attached_to_name)
	return _serve_file(fdoc, fdoc.file_name)


def _shelf_rows(room):
	rows = frappe.get_all(
		"Client Shelf Doc",
		filters={"room": room.name, "active": 1},
		fields=["name", "title", "category", "file_name", "creation", "owner", "project"],
		order_by="creation desc",
		limit=200,
	)
	_shpn = _project_names(room)
	for r in rows:
		r.creation = str(r.creation)[:10]
		r.project_name = _shpn.get(r.project) if r.project else None
		try:
			r.by = (frappe.utils.get_fullname(r.owner) or "").split(" ")[0]
		except Exception:
			r.by = ""
		r.pop("owner", None)
	return rows


def _financial_room(customer):
	"""THE room that carries a customer's financial data. Resolution:
	explicit Financial Room flag → room with a bookkeeper → room with
	books scope → the sole active room. None if unresolvable."""
	rooms = frappe.get_all(
		"Client Room",
		filters={"customer": customer, "status": ["!=", "Archived"]},
		fields=["name", "is_financial_room", "bookkeeper", "books_scope"],
	)
	if not rooms:
		return None
	for r in rooms:
		if cint(r.is_financial_room):
			return r.name
	for r in rooms:
		if r.bookkeeper:
			return r.name
	for r in rooms:
		if r.books_scope:
			return r.name
	return rooms[0].name if len(rooms) == 1 else None


def _statement_rows(room):
	"""Financial statements for this room's customer, from the Document Hub.
	Served ONLY in the customer's Financial Room."""
	if not room.customer:
		return []
	if _financial_room(room.customer) != room.name:
		return []
	rows = frappe.get_all(
		"Client Document",
		filters={"client": room.customer, "is_financial_statement": 1},
		fields=[
			"name", "statement_type", "period_month", "period_year",
			"published", "published_on", "publish_seq",
			"review_status", "approved_on", "approved_version",
			"due_date", "delayed_until", "delay_reason", "highlights",
		],
		limit_page_length=100,
	)
	threads = {}
	if rows:
		for t in frappe.get_all(
			"Statement Review Entry",
			filters={"parenttype": "Client Document", "parent": ["in", [r.name for r in rows]]},
			fields=["parent", "entry_type", "user", "when", "at_version", "note"],
			order_by="idx asc",
			limit_page_length=500,
		):
			t.when = str(t.when)[:16]
			threads.setdefault(t.parent, []).append(t)
	month_no = {m: i for i, m in enumerate(
		["January", "February", "March", "April", "May", "June", "July",
		 "August", "September", "October", "November", "December"], 1)}
	for r in rows:
		if r.statement_type == "Annual Report":
			r.label = _("{0} Annual Report").format(r.period_year)
		else:
			r.label = _("{0} {1} Management Account").format(r.period_month or "", r.period_year).strip()
		r.month_no = month_no.get(r.period_month, 0)
		r.published_on = str(r.published_on)[:10] if r.published_on else None
		r.approved_on = str(r.approved_on)[:10] if r.approved_on else None
		r.due_date = str(r.due_date) if r.due_date else None
		r.thread = threads.get(r.name, [])
		r.highlight_lines = [l.strip() for l in (r.highlights or "").splitlines() if l.strip()][:5]
		if not r.published:
			from duty_board.document_hub.doctype.client_document.client_document import statement_state

			st = statement_state(r) or {}
			r.state = st.get("state")
			r.state_label = st.get("label")
			if r.month_no and r.period_year:
				pkey = f"{r.period_year}-{r.month_no:02d}"
				delivs = frappe.get_all(
					"Duty Service Deliverable",
					filters={"room": room.name, "period": pkey},
					fields=["name", "deliverable_type", "status", "due_date"],
					order_by="due_date asc, creation asc",
					limit_page_length=6,
				)
				if delivs:
					titles = {
						t.name: t.title
						for t in frappe.get_all(
							"Duty Service Deliverable Type",
							filters={"name": ["in", [x.deliverable_type for x in delivs]]},
							fields=["name", "title"],
						)
					}
					r.progress = [
						{
							"label": (titles.get(x.deliverable_type) or x.deliverable_type or "")[:22],
							"done": 1 if x.status in ("Delivered", "Acknowledged") else 0,
							"active": 1 if x.status in ("In Progress", "In Review") else 0,
						}
						for x in delivs[:5]
					]
				blockers = frappe.get_all(
					"Duty Books Request",
					filters={"room": room.name, "period": pkey, "status": "Requested"},
					fields=["title"],
					limit_page_length=5,
				)
				r.blocked_count = len(blockers)
				r.blocked_titles = [b.title for b in blockers[:3]]
	rows.sort(key=lambda r: (r.period_year or 0, r.month_no), reverse=True)
	return rows


@frappe.whitelist()
def client_statement_feedback(id, text):
	"""Extensive client feedback on a published statement → thread on the
	Client Document, state → Changes Requested, staff notified."""
	room = _client_room()
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Write the feedback first."))
	doc = frappe.get_doc("Client Document", id)
	if doc.client != room.customer or not cint(doc.is_financial_statement) or not cint(doc.published):
		frappe.throw(_("Not found."), frappe.PermissionError)
	_fr = _financial_room(d.client)
	if _fr and _fr != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	from duty_board.document_hub.doctype.client_document.client_document import (
		_notify_statement_staff,
		_thread_add,
		statement_label,
	)

	_thread_add(doc, "Feedback", text)
	doc.db_set("review_status", "Changes Requested", update_modified=False)
	frappe.db.commit()
	label = statement_label(doc)
	try:
		frappe.get_doc(
			{
				"doctype": "Document Activity",
				"document": doc.name,
				"activity": "Client feedback received",
				"user": frappe.session.user,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		pass
	_notify_statement_staff(doc, _("📊 Feedback on {0}").format(label), text[:140])
	try:
		_post(room, _("📊 Feedback received on {0} — we're on it.").format(label))
	except Exception:
		pass
	return {"ok": 1}


@frappe.whitelist()
def client_statement_approve(id):
	"""Client approves the published statement — terminal until republished."""
	room = _client_room()
	doc = frappe.get_doc("Client Document", id)
	if doc.client != room.customer or not cint(doc.is_financial_statement) or not cint(doc.published):
		frappe.throw(_("Not found."), frappe.PermissionError)
	_fr = _financial_room(d.client)
	if _fr and _fr != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.review_status == "Approved":
		return {"ok": 1, "already": 1}
	from duty_board.document_hub.doctype.client_document.client_document import (
		_notify_statement_staff,
		_thread_add,
		statement_label,
	)

	_thread_add(doc, "Approval", _("Approved"))
	doc.db_set("review_status", "Approved", update_modified=False)
	doc.db_set("approved_by", frappe.session.user, update_modified=False)
	doc.db_set("approved_on", frappe.utils.now_datetime(), update_modified=False)
	doc.db_set("approved_version", cint(doc.publish_seq), update_modified=False)
	frappe.db.commit()
	label = statement_label(doc)
	try:
		frappe.get_doc(
			{
				"doctype": "Document Activity",
				"document": doc.name,
				"activity": "Approved by client (v{0})".format(cint(doc.publish_seq)),
				"user": frappe.session.user,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		pass
	_notify_statement_staff(doc, _("✅ {0} approved by the client").format(label), _("Approved by {0}").format(frappe.session.user))
	try:
		_post(room, _("✅ {0} approved — thank you!").format(label))
	except Exception:
		pass
	return {"ok": 1}


@frappe.whitelist()
def client_statement_file(id):
	"""Clients download ONLY the published snapshot of a hub statement."""
	room = _client_room()
	d = frappe.db.get_value(
		"Client Document", id,
		["client", "is_financial_statement", "published", "published_file_url", "published_file_name",
			"review_status", "approved_on", "approved_version", "publish_seq"],
		as_dict=True,
	)
	if (
		not d
		or d.client != room.customer
		or not cint(d.is_financial_statement)
		or not cint(d.published)
	):
		frappe.throw(_("Not found."), frappe.PermissionError)
	_fr = _financial_room(d.client)
	if _fr and _fr != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	fname = frappe.db.get_value("File", {"file_url": d.published_file_url})
	if not fname:
		frappe.throw(_("File missing."))
	fdoc = frappe.get_doc("File", fname)
	approved = d.review_status == "Approved" and cint(d.approved_version or 0) == cint(d.publish_seq or 1)
	if approved and (d.published_file_name or "").lower().endswith(".pdf"):
		try:
			import io

			from pypdf import PdfReader, PdfWriter
			from pypdf.annotations import FreeText

			reader = PdfReader(io.BytesIO(fdoc.get_content()))
			writer = PdfWriter()
			writer.append(reader)
			box = reader.pages[0].mediabox
			note = FreeText(
				text="APPROVED — {0}".format(str(d.approved_on)[:10]),
				rect=(float(box.width) - 235, float(box.height) - 52, float(box.width) - 25, float(box.height) - 20),
				font="Helvetica-Bold",
				font_size="13pt",
				font_color="0b6b4f",
				border_color="0b6b4f",
				background_color="e4f3ec",
			)
			writer.add_annotation(page_number=0, annotation=note)
			buf = io.BytesIO()
			writer.write(buf)
			frappe.local.response.filename = d.published_file_name
			frappe.local.response.filecontent = buf.getvalue()
			frappe.local.response.type = "download"
			return
		except Exception:
			frappe.log_error(frappe.get_traceback()[-1200:], "stamp statement")
	return _serve_file(fdoc, d.published_file_name)


@frappe.whitelist()
def shelf_add(name, title, attachment_url, attachment_name=None, category=None, project=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the document a title."))
	owned = frappe.db.get_value(
		"File", {"file_url": attachment_url, "owner": frappe.session.user}, "file_name"
	)
	if not owned:
		frappe.throw(_("Upload not found — try attaching again."))
	# "__general__" (or blank) files the doc under the room catch-all project —
	# the relationship bucket for contracts, SLAs and the like.
	proj = None if (not project or project == "__general__") else _validate_milestone_project(room.name, project)
	if not proj:
		proj = _ensure_project(room)
	frappe.get_doc(
		{
			"doctype": "Client Shelf Doc",
			"room": room.name,
			"title": title[:140],
			"category": (category or "").strip()[:60] or None,
			"file_url": attachment_url,
			"file_name": attachment_name or owned,
			"active": 1,
			"project": proj,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def shelf_remove(doc_name):
	_staff_only()
	frappe.db.set_value("Client Shelf Doc", doc_name, "active", 0, update_modified=False)
	frappe.db.commit()
	return {"ok": True}


def _statement_year_strip(rows):
	"""Current-year on-time record for Management Accounts: per-month state
	(ontime/late/pending/none) judged against the ORIGINAL due date, plus
	counts and the current consecutive on-time streak."""
	from frappe.utils import getdate, today

	year = getdate(today()).year
	this_month = getdate(today()).month
	months = []
	by_no = {}
	for r in rows:
		if r.statement_type == "Management Account" and cint(r.period_year) == year and r.month_no:
			by_no[r.month_no] = r
	for n in range(1, 13):
		r = by_no.get(n)
		if not r:
			months.append({"m": n, "state": "none" if n > this_month else "none"})
			continue
		if not r.published:
			months.append({"m": n, "state": "pending"})
			continue
		ontime = (not r.due_date) or (r.published_on and str(r.published_on) <= str(r.due_date))
		months.append({"m": n, "state": "ontime" if ontime else "late"})
	pub = [m for m in months if m["state"] in ("ontime", "late")]
	streak = 0
	for m in reversed(pub):
		if m["state"] == "ontime":
			streak += 1
		else:
			break
	return {
		"year": year,
		"months": months,
		"published": len(pub),
		"ontime": len([m for m in pub if m["state"] == "ontime"]),
		"streak": streak,
	}


@frappe.whitelist()
def client_get_documents():
	room = _client_room()
	stm = _statement_rows(room)
	return {"docs": _shelf_rows(room), "statements": stm, "year_strip": _statement_year_strip(stm)}


@frappe.whitelist()
def client_projects():
	"""Active projects for the client's customer, for the portal selector.
	The room catch-all is presented once as "General"; a stable id lets the
	selector scope tasks/phases/CRs/docs to the relationship bucket."""
	room = _client_room()
	projs = frappe.get_all(
		"Duty Project",
		filters={"room": room.name, "status": "Active"},
		fields=["name", "project_name"],
		order_by="creation asc",
	)
	catchall = None
	out = []
	for p in projs:
		label = p.project_name or p.name
		if label.endswith("— Requests") or label.endswith("- Requests"):
			catchall = p.name
			continue
		out.append({"id": p.name, "label": label})
	# General always last, always present so relationship docs have a home.
	out.append({"id": catchall or "__general__", "label": "General"})
	return out


@frappe.whitelist()
def client_shelf_file(id):
	room = _client_room()
	d = frappe.db.get_value(
		"Client Shelf Doc", id, ["room", "file_url", "file_name", "active"], as_dict=True
	)
	if not d or d.room != room.name or not cint(d.active):
		frappe.throw(_("Not found."), frappe.PermissionError)
	fname = frappe.db.get_value("File", {"file_url": d.file_url})
	if not fname:
		frappe.throw(_("File missing."))
	return _serve_file(frappe.get_doc("File", fname), d.file_name)


@frappe.whitelist()
def staff_shelf_file(id):
	_staff_only()
	d = frappe.db.get_value(
		"Client Shelf Doc", id, ["file_url", "file_name"], as_dict=True
	)
	if not d:
		frappe.throw(_("Not found."))
	fname = frappe.db.get_value("File", {"file_url": d.file_url})
	if not fname:
		frappe.throw(_("File missing."))
	return _serve_file(frappe.get_doc("File", fname), d.file_name)


@frappe.whitelist()
def client_search(q):
	room = _client_room()
	q = (q or "").strip()
	if len(q) < 2:
		return {"messages": [], "issues": []}
	like = f"%{q}%"
	msgs = frappe.get_all(
		"Client Room Message",
		filters={"room": room.name, "internal": 0, "message": ["like", like]},
		fields=["name", "message", "owner", "creation"],
		order_by="creation desc",
		limit=15,
	)
	for m in msgs:
		m.who = (frappe.utils.get_fullname(m.owner) or m.owner).split(" ")[0]
		m.creation = str(m.creation)[:16]
		m.message = m.message[:140]
	issues = frappe.get_all(
		"Duty Issue",
		filters={"customer": room.customer, "client_visible": 1, "title": ["like", like]},
		fields=["name", "title", "status", "source_type", "source"],
		order_by="modified desc",
		limit=20,
	)
	extra = frappe.get_all(
		"Duty Issue",
		filters={
			"customer": room.customer,
			"client_visible": 1,
			"description": ["like", like],
		},
		fields=["name", "title", "status", "source_type", "source"],
		limit=20,
	)
	issues = [i for i in issues if _issue_in_room(i, room)]
	extra = [e for e in extra if _issue_in_room(e, room)]
	seen = {i.name for i in issues}
	issues += [e for e in extra if e.name not in seen]
	out_issues = []
	for i in issues:
		status = ISSUE_CLIENT_STATUS.get(i.status)
		if status:
			out_issues.append({"id": i.name, "title": i.title, "status": status})
	return {"messages": msgs, "issues": out_issues[:12]}


@frappe.whitelist()
def client_rate_task(id, rating):
	room = _client_room()
	if rating not in ("Up", "Down"):
		frappe.throw(_("Bad rating."))
	row = _client_issue_for_room(room, id)
	if ISSUE_CLIENT_STATUS.get(row.status) != "Done":
		frappe.throw(_("You can rate once it's done."))
	frappe.db.set_value("Duty Issue", row.name, "client_rating", rating, update_modified=False)
	frappe.db.commit()
	if rating == "Down":
		try:
			from duty_board.api import _notify_user

			for u in frappe.get_all(
				"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]
			):
				if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
					_notify_user(
						u.name,
						_("👎 Client unhappy · {0}").format(room.customer),
						row.title[:120],
					)
		except Exception:
			pass
	return {"ok": True, "rating": rating}


def weekly_room_pulse():
	"""Scheduled: each active room gets its week in one honest line."""
	week_ago = frappe.utils.add_days(frappe.utils.today(), -7)
	for r in frappe.get_all(
		"Client Room", filters={"status": "Active"}, fields=["name", "customer"]
	):
		if not frappe.db.exists("Client Room Member", {"room": r.name, "active": 1}):
			continue
		room = frappe.get_doc("Client Room", r.name)
		rows = [x for x in _work_rows(room) if x["kind"] == "issue"]
		done = sum(
			1
			for x in rows
			if x["status"] == "Done" and str(x.get("modified") or "") >= str(week_ago)
		)
		prog = sum(1 for x in rows if x["status"] == "In Progress")
		queued = sum(1 for x in rows if x["status"] == "Queued")
		if not (done or prog or queued):
			continue
		_post(
			room,
			f"📊 Your week with Xlevel: ✅ {done} completed · 🔄 {prog} in progress · 📋 {queued} queued.",
		)
	frappe.db.commit()


def _push_room_clients(room, title, body):
	try:
		from duty_board.api import _push_safe

		for mm in frappe.get_all(
			"Client Room Member", filters={"room": room.name, "active": 1}, fields=["user"]
		):
			if frappe.db.exists("Duty Push Subscription", {"user": mm.user}):
				_push_safe(mm.user, title, body)
	except Exception:
		pass


def narrate_issue(issue_name, event):
	"""The room speaks when client-visible work moves. event: seen | started | done"""
	try:
		row = frappe.db.get_value(
			"Duty Issue",
			issue_name,
			["title", "customer", "client_visible", "source_type", "source"],
			as_dict=True,
		)
		if not row or not cint(row.client_visible):
			return
		home = _issue_home_room(row)
		if not home:
			return
		room = frappe.get_doc("Client Room", home.name)
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		lines = {
			"seen": (_("👀 Seen by the team — {0}: “{1}”"), _("👀 Your request has been seen")),
			"started": (_("🔄 “{1}” → In Progress · {0}"), _("🔄 Being worked on now")),
			"done": (_("✅ “{1}” → Done · {0}"), _("✅ Completed")),
		}
		if event not in lines:
			return
		room_line, push_title = lines[event]
		_post(room, room_line.format(first, row.title[:90]))
		_push_room_clients(room, f"{push_title} · Xlevel", row.title[:120])
	except Exception:
		pass


def _pending_joins_safe():
	try:
		return frappe.db.count("Client Join Request", {"status": "Pending"})
	except Exception:
		return 0


def _rooms_unread_safe(user):
	try:
		total = 0
		for r in frappe.get_all(
			"Client Room", filters={"status": ["!=", "Archived"]}, pluck="name"
		):
			seen = frappe.db.get_value(
				"Client Room Seen", {"room": r, "user": user}, "last_seen"
			)
			filters = {"room": r, "owner": ["!=", user]}
			if seen:
				filters["creation"] = [">", seen]
			if frappe.db.count("Client Room Message", filters):
				total += 1
		return total
	except Exception:
		return 0


_UTYPE_CACHE = {}


def _utype(user):
	if user not in _UTYPE_CACHE:
		_UTYPE_CACHE[user] = frappe.db.get_value("User", user, "user_type")
	return _UTYPE_CACHE[user]


def _room_unread(room_name, user):
	"""Unseen messages split: client-authored (a human on the client side
	wrote something) vs everything else (staff colleagues, system
	narrations). Returns {total, client, other}."""
	seen = frappe.db.get_value(
		"Client Room Seen", {"room": room_name, "user": user}, "last_seen"
	)
	filters = {"room": room_name, "owner": ["!=", user]}
	if seen:
		filters["creation"] = [">", seen]
	owners = frappe.get_all(
		"Client Room Message", filters=filters, pluck="owner", limit_page_length=0
	)
	client = sum(1 for o in owners if _utype(o) == "Website User")
	return {"total": len(owners), "client": client, "other": len(owners) - client}


@frappe.whitelist()
def mark_room_seen(name):
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names

	if require_staff_or_consultant() and name not in consultant_room_names():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	user = frappe.session.user
	existing = frappe.db.exists("Client Room Seen", {"room": name, "user": user})
	if existing:
		frappe.db.set_value(
			"Client Room Seen", existing, "last_seen", now_datetime(), update_modified=False
		)
	else:
		frappe.get_doc(
			{
				"doctype": "Client Room Seen",
				"room": name,
				"user": user,
				"last_seen": now_datetime(),
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def rename_room_unit(name, unit):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	unit = (unit or "").strip()[:40]
	if not unit:
		frappe.throw(_("Give the room a name."))
	clash = frappe.db.get_value(
		"Client Room", {"customer": room.customer, "unit": unit, "name": ["!=", name]}
	)
	if clash:
		frappe.throw(_("{0} already has a room called {1}.").format(room.customer, unit))
	frappe.db.set_value("Client Room", name, "unit", unit, update_modified=False)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def delete_room(name):
	"""Full removal — System Manager only. Messages, members, shelf, meetings,
	seen-markers and join requests go with it. Issues born here become loose
	customer issues and surface in the General room."""
	_staff_only()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only a System Manager can delete a room."))
	room = frappe.get_doc("Client Room", name)
	for dt, field in [
		("Client Room Message", "room"),
		("Client Room Member", "room"),
		("Client Room Seen", "room"),
		("Client Join Request", "room"),
		("Client Shelf Doc", "room"),
		("Duty Meeting", "room"),
	]:
		for d in frappe.get_all(dt, filters={field: name}, pluck="name"):
			frappe.delete_doc(dt, d, ignore_permissions=True, force=True)
	frappe.delete_doc("Client Room", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": True, "customer": room.customer}


@frappe.whitelist()
def set_room_owner(name, owner):
	_staff_only()
	if owner and frappe.db.get_value("User", owner, "user_type") != "System User":
		frappe.throw(_("The account manager must be a staff account."))
	frappe.db.set_value("Client Room", name, "owner_user", owner or None, update_modified=False)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def staff_typing(name):
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names

	if require_staff_or_consultant() and name not in consultant_room_names():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	frappe.publish_realtime(
		"duty_client_typing", {"room": name, "who": first, "staff": 1}
	)
	return {"ok": True}


@frappe.whitelist()
def client_typing():
	room = _client_room()
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	frappe.publish_realtime(
		"duty_client_typing", {"room": room.name, "who": first, "client": 1}
	)
	return {"ok": True}


def _issue_in_room(i, room):
	"""Room-born issues stay in their room; the General room sweeps everything
	unclaimed (loose customer issues, orphaned rooms)."""
	roomed = i.get("source_type") == "Client Room" and i.get("source")
	if roomed and i.get("source") == room.name:
		return True
	if (room.unit or "General") != "General":
		return False
	if not roomed:
		return True
	return not frappe.db.exists("Client Room", i.get("source"))


def _issue_home_room(row):
	"""Where an issue's story belongs: its birth room, else the customer's General."""
	if row.get("source_type") == "Client Room" and row.get("source"):
		if frappe.db.exists("Client Room", row.source):
			return frappe.db.get_value(
				"Client Room", row.source, ["name", "status"], as_dict=True
			)
	general = frappe.db.get_value(
		"Client Room",
		{"customer": row.customer, "unit": "General", "status": "Active"},
		["name", "status"],
		as_dict=True,
	)
	if general:
		return general
	any_room = frappe.db.get_value(
		"Client Room",
		{"customer": row.customer, "status": "Active"},
		["name", "status"],
		as_dict=True,
	)
	return any_room


# ---------------- milestones: the governance layer ----------------

XLEVEL_METHOD = [
	("Discovery", "Requirements gathered, current processes documented, scope agreed."),
	("Configuration", "System configured to your business: masters, workflows, permissions."),
	("Data Migration", "Your historical data cleaned, migrated and reconciled."),
	("Training", "Your team trained and confident on their daily operations."),
	("User Acceptance Testing", "You test real scenarios end-to-end and confirm readiness."),
	("Go-Live", "The system becomes your live system of record."),
	("Hypercare", "Intensive post-go-live support until stability is confirmed."),
]


def _milestone_locked(doc):
	if doc.status == "Approved":
		frappe.throw(
			_("“{0}” has been formally approved by the client and can no longer be changed.").format(
				doc.title
			)
		)


def _milestone_rows(room):
	"""Room-scoped milestone rows (legacy path: every phase in the room)."""
	rows = frappe.get_all(
		"Duty Milestone",
		filters={"room": room.name},
		fields=[
			"name", "title", "description", "sort_order", "status", "target_date",
			"approved_full", "approved_at", "approval_note", "submitted_on", "project",
			"baseline_date",
		],
		order_by="sort_order asc, creation asc",
	)
	return _milestone_decorate(rows, _project_names(room))


def _project_milestone_rows(project):
	"""Project-scoped milestone rows — the project-first path. Works whether
	or not the project is attached to a room."""
	rows = frappe.get_all(
		"Duty Milestone",
		filters={"project": project},
		fields=[
			"name", "title", "description", "sort_order", "status", "target_date",
			"approved_full", "approved_at", "approval_note", "submitted_on", "project",
			"baseline_date",
		],
		order_by="sort_order asc, creation asc",
	)
	pname = frappe.db.get_value("Duty Project", project, "project_name") or project
	return _milestone_decorate(rows, {project: pname})


def _milestone_decorate(rows, pnames):
	"""Shared row builder: attach tasks, progress counts, project label,
	and baseline variance (slip vs the frozen plan)."""
	from frappe.utils import date_diff
	for r in rows:
		baseline = r.get("baseline_date")
		r.baseline_date = str(baseline) if baseline else None
		r.baselined = 1 if baseline else 0
		if baseline and r.get("target_date"):
			# +ve = later than plan (slipped), -ve = ahead of plan
			r.slip_days = date_diff(r.target_date, baseline)
		else:
			r.slip_days = None
		r.target_date = str(r.target_date) if r.target_date else None
		r.approved_at = str(r.approved_at)[:16] if r.approved_at else None
		tasks = frappe.get_all(
			"Duty Project Task",
			filters={"milestone": r.name},
			fields=[
				"name", "title", "column", "assignee", "due_date",
				"urgency", "description", "awaiting_client", "estimate_hours",
			],
			order_by="creation asc",
			limit=60,
		)
		fullnames = {}
		for t in tasks:
			if t.assignee and t.assignee not in fullnames:
				fullnames[t.assignee] = frappe.utils.get_fullname(t.assignee)
		r.tasks = [
			{
				"name": t.name,
				"title": t.title,
				"status": CLIENT_STATUS.get(t.column, "Queued"),
				"assignee": fullnames.get(t.assignee),
				"due_date": str(t.due_date) if t.due_date else None,
				"overdue": bool(
					t.due_date and t.column != "Completed" and getdate(t.due_date) < getdate(today())
				),
				"urgency": t.urgency,
				"description": (t.description or "").strip()[:300] or None,
				"awaiting_client": cint(t.awaiting_client),
			}
			for t in tasks
		]
		r.cards_total = len(tasks)
		r.cards_done = sum(1 for t in tasks if t.column == "Completed")
		r.awaiting = sum(1 for t in tasks if cint(t.awaiting_client) and t.column != "Completed")
		r.est_hours = round(sum(t.estimate_hours or 0 for t in tasks), 1)
		task_names = [t.name for t in tasks]
		r.act_hours = 0
		if task_names:
			secs = frappe.db.sql(
				"select coalesce(sum(duration),0) from `tabWork Session` where project_task in %(n)s",
				{"n": task_names},
			)[0][0] or 0
			r.act_hours = round(secs / 3600.0, 1)
	for r in rows:
		r.project_name = pnames.get(r.project)
	return rows


@frappe.whitelist()
@frappe.whitelist()
def project_seed_milestones(project, plan_type=None):
	"""Seed the Xlevel method onto a PROJECT (room-independent). Guards per
	project, so each project in a room gets its own phase journey."""
	_staff_only()
	if not frappe.db.exists("Duty Project", project):
		frappe.throw(_("Unknown project."))
	if frappe.db.count("Duty Milestone", {"project": project}):
		frappe.throw(_("This project already has phases."))
	room_name = frappe.db.get_value("Duty Project", project, "room")
	if not room_name:
		frappe.throw(_("Assign this project to a room before seeding phases."))

	plan = None
	if plan_type:
		from duty_board.plan_templates import PLAN_TYPES

		if plan_type not in PLAN_TYPES:
			frappe.throw(_("Unknown plan type."))
		plan = PLAN_TYPES[plan_type][1]

	from frappe.utils import add_days

	for i, (title, desc) in enumerate(XLEVEL_METHOD):
		phase_tasks = (plan or {}).get(title, [])
		ms = frappe.get_doc(
			{
				"doctype": "Duty Milestone",
				"room": room_name,
				"project": project,
				"title": title,
				"description": desc,
				"sort_order": i,
				"status": "Upcoming",
				"target_date": add_days(today(), max(t[3] for t in phase_tasks))
				if phase_tasks
				else None,
			}
		).insert(ignore_permissions=True)
		for t_title, t_desc, t_urg, t_off in phase_tasks:
			frappe.get_doc(
				{
					"doctype": "Duty Project Task",
					"project": project,
					"title": t_title,
					"column": "To Do",
					"urgency": t_urg if t_urg in ("Low", "Medium", "High", "Critical") else "Medium",
					"description": t_desc or None,
					"due_date": add_days(today(), t_off) if t_off else None,
					"milestone": ms.name,
				}
			).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "project": project}


@frappe.whitelist()
def project_set_baseline(project):
	"""Freeze the current phase target dates as the project's baseline. Call
	once the plan is agreed; variance is measured against this line. Safe to
	re-run (a deliberate re-plan) — it re-freezes to current targets."""
	_staff_only()
	if not frappe.db.exists("Duty Project", project):
		frappe.throw(_("Unknown project."))
	phases = frappe.get_all(
		"Duty Milestone",
		filters={"project": project},
		fields=["name", "target_date"],
	)
	if not phases:
		frappe.throw(_("Seed or add phases before baselining."))
	stamped = 0
	for p in phases:
		if p.target_date:
			frappe.db.set_value("Duty Milestone", p.name, "baseline_date", p.target_date, update_modified=False)
			stamped += 1
	frappe.db.set_value("Duty Project", project, "baselined_on", frappe.utils.now(), update_modified=False)
	frappe.db.commit()
	return {"ok": 1, "project": project, "phases_baselined": stamped}


@frappe.whitelist()
def project_baseline_status(project):
	"""Whether a project is baselined, and when."""
	_staff_only()
	on = frappe.db.get_value("Duty Project", project, "baselined_on")
	return {"baselined": 1 if on else 0, "baselined_on": str(on)[:16] if on else None}


@frappe.whitelist()
def project_milestone_add(project, title, description=None, target_date=None):
	"""Add one phase to a project; sort-order sequenced per project."""
	_staff_only()
	if not frappe.db.exists("Duty Project", project):
		frappe.throw(_("Unknown project."))
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the phase a title."))
	room_name = frappe.db.get_value("Duty Project", project, "room")
	if not room_name:
		frappe.throw(_("Assign this project to a room before adding phases."))
	last = frappe.db.sql(
		"select coalesce(max(sort_order), -1) from `tabDuty Milestone` where project = %s",
		project,
	)[0][0]
	frappe.get_doc(
		{
			"doctype": "Duty Milestone",
			"room": room_name,
			"project": project,
			"title": title[:120],
			"description": (description or "").strip()[:500] or None,
			"target_date": target_date or None,
			"sort_order": last + 1,
			"status": "Upcoming",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "project": project}


def milestones_seed(name, plan_type=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	if frappe.db.count("Duty Milestone", {"room": room.name}):
		frappe.throw(_("This room already has milestones."))

	plan = None
	if plan_type:
		from duty_board.plan_templates import PLAN_TYPES

		if plan_type not in PLAN_TYPES:
			frappe.throw(_("Unknown plan type."))
		plan = PLAN_TYPES[plan_type][1]
		if not room.project:
			from duty_board.projects import create_project

			project_name = create_project(
				f"{PLAN_TYPES[plan_type][0]} — {room.customer}"[:120], room.customer
			)
			room.db_set("project", project_name, update_modified=False)
			room.reload()

	from frappe.utils import add_days

	for i, (title, desc) in enumerate(XLEVEL_METHOD):
		phase_tasks = (plan or {}).get(title, [])
		ms = frappe.get_doc(
			{
				"doctype": "Duty Milestone",
				"room": room.name,
				"title": title,
				"description": desc,
				"sort_order": i,
				"status": "Upcoming",
				"project": room.project or None,
				"target_date": add_days(today(), max(t[3] for t in phase_tasks))
				if phase_tasks
				else None,
			}
		).insert(ignore_permissions=True)
		for t_title, t_desc, t_urg, t_off in phase_tasks:
			frappe.get_doc(
				{
					"doctype": "Duty Project Task",
					"project": room.project,
					"title": t_title,
					"column": "To Do",
					"urgency": t_urg if t_urg in ("Low", "Medium", "High", "Critical") else "Medium",
					"description": t_desc or None,
					"due_date": add_days(today(), t_off) if t_off else None,
					"milestone": ms.name,
				}
			).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def milestone_add(name, title, description=None, target_date=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the milestone a title."))
	last = frappe.db.sql(
		"select coalesce(max(sort_order), -1) from `tabDuty Milestone` where room = %s",
		room.name,
	)[0][0]
	frappe.get_doc(
		{
			"doctype": "Duty Milestone",
			"room": room.name,
			"title": title[:120],
			"description": (description or "").strip()[:500] or None,
			"target_date": target_date or None,
			"sort_order": last + 1,
			"status": "Upcoming",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def milestone_task_options(id):
	_staff_only()
	ms = frappe.get_doc("Duty Milestone", id)
	customer = frappe.db.get_value("Client Room", ms.room, "customer")
	out = []
	for p in frappe.get_all(
		"Duty Project", filters={"customer": customer}, fields=["name", "project_name"]
	):
		for t in frappe.get_all(
			"Duty Project Task",
			filters={"project": p.name},
			fields=["name", "title", "column", "milestone"],
			order_by="creation asc",
		):
			out.append(
				{
					"name": t.name,
					"title": t.title,
					"project_title": p.project_name,
					"column": t.column,
					"checked": t.milestone == id,
					"elsewhere": bool(t.milestone and t.milestone != id),
				}
			)
	return out


@frappe.whitelist()
def project_milestone_task_options(id):
	"""Tasks of THIS milestone's project, flagged for the picker. Project-
	scoped (unlike the legacy customer-wide milestone_task_options)."""
	_staff_only()
	ms = frappe.get_doc("Duty Milestone", id)
	project = frappe.db.get_value("Duty Milestone", id, "project")
	out = []
	if not project:
		return out
	for t in frappe.get_all(
		"Duty Project Task",
		filters={"project": project},
		fields=["name", "title", "column", "milestone"],
		order_by="creation asc",
	):
		out.append({
			"name": t.name,
			"title": t.title,
			"column": t.column,
			"checked": t.milestone == id,
			"elsewhere": bool(t.milestone and t.milestone != id),
		})
	return out


@frappe.whitelist()
def milestone_set_tasks(id, tasks):
	_staff_only()
	ms = frappe.get_doc("Duty Milestone", id)
	customer = frappe.db.get_value("Client Room", ms.room, "customer")
	wanted = set(frappe.parse_json(tasks) or [])
	for t in wanted:
		proj = frappe.db.get_value("Duty Project Task", t, "project")
		if frappe.db.get_value("Duty Project", proj, "customer") != customer:
			frappe.throw(_("A selected task belongs to a different customer."))
	current = set(
		frappe.get_all("Duty Project Task", filters={"milestone": id}, pluck="name")
	)
	for t in current - wanted:
		frappe.db.set_value("Duty Project Task", t, "milestone", None, update_modified=False)
	for t in wanted - current:
		frappe.db.set_value("Duty Project Task", t, "milestone", id, update_modified=False)
	frappe.db.commit()
	return get_room(ms.room)


def _validate_milestone_project(room_name, project):
	if not project:
		return None
	cust = frappe.db.get_value("Duty Project", project, "customer")
	room_cust = frappe.db.get_value("Client Room", room_name, "customer")
	if cust != room_cust:
		frappe.throw(_("That project belongs to a different customer."))
	return project


@frappe.whitelist()
def milestone_update(id, title=None, description=None, target_date=None, project=None):
	_staff_only()
	doc = frappe.get_doc("Duty Milestone", id)
	_milestone_locked(doc)
	vals = {}
	if project is not None:
		vals["project"] = _validate_milestone_project(doc.room, project or None)
	if title is not None:
		title = title.strip()
		if not title:
			frappe.throw(_("Give the milestone a title."))
		vals["title"] = title[:120]
	if description is not None:
		vals["description"] = description.strip()[:500] or None
	if target_date is not None:
		vals["target_date"] = target_date or None
	if vals:
		frappe.db.set_value("Duty Milestone", id, vals, update_modified=False)
		frappe.db.commit()
	return get_room(doc.room)


@frappe.whitelist()
def milestone_move(id, direction):
	_staff_only()
	doc = frappe.get_doc("Duty Milestone", id)
	siblings = frappe.get_all(
		"Duty Milestone",
		filters={"room": doc.room},
		fields=["name", "sort_order"],
		order_by="sort_order asc, creation asc",
	)
	idx = next(i for i, s in enumerate(siblings) if s.name == id)
	swap = idx - 1 if direction == "up" else idx + 1
	if 0 <= swap < len(siblings):
		a, b = siblings[idx], siblings[swap]
		frappe.db.set_value("Duty Milestone", a.name, "sort_order", b.sort_order, update_modified=False)
		frappe.db.set_value("Duty Milestone", b.name, "sort_order", a.sort_order, update_modified=False)
		frappe.db.commit()
	return get_room(doc.room)


@frappe.whitelist()
def milestone_set_status(id, status):
	_staff_only()
	if status == "Completed":
		_m = frappe.db.get_value("Duty Milestone", id, ["room", "title"], as_dict=True)
		if _m:
			from duty_board.uat import uat_gate_check

			uat_gate_check(_m.room, _m.title)
	if status not in ("Upcoming", "In Progress"):
		frappe.throw(_("Use Request approval for that."))
	doc = frappe.get_doc("Duty Milestone", id)
	_milestone_locked(doc)
	frappe.db.set_value("Duty Milestone", id, "status", status, update_modified=False)
	frappe.db.commit()
	if status == "In Progress":
		room = frappe.get_doc("Client Room", doc.room)
		_post(room, _("🏁 Phase started: “{0}”").format(doc.title))
		_push_room_clients(room, _("🏁 Phase started · Xlevel"), doc.title[:120])
	return get_room(doc.room)


@frappe.whitelist()
def milestone_request_approval(id):
	_staff_only()
	doc = frappe.get_doc("Duty Milestone", id)
	_milestone_locked(doc)
	frappe.db.set_value(
		"Duty Milestone",
		id,
		{"status": "Awaiting Approval", "submitted_on": now_datetime()},
		update_modified=False,
	)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	_post(
		room,
		_("🏁 “{0}” is complete and awaits your formal approval — open Milestones on your portal.").format(
			doc.title
		),
	)
	_push_room_clients(
		room, _("🏁 Your approval requested · Xlevel"), doc.title[:120]
	)
	return get_room(doc.room)


@frappe.whitelist()
def milestone_delete(id):
	_staff_only()
	doc = frappe.get_doc("Duty Milestone", id)
	_milestone_locked(doc)
	room = doc.room
	frappe.delete_doc("Duty Milestone", id, ignore_permissions=True, force=True)
	frappe.db.commit()
	return get_room(room)


@frappe.whitelist()
def client_get_milestones():
	room = _client_room()
	rows = _milestone_rows(room)
	gate = 1 if _client_can_approve(room) else 0
	for r in rows:
		r.can_approve = gate
	pm = None
	if room.get("owner_user"):
		pm = frappe.utils.get_fullname(room.owner_user)
	return {"rows": rows, "pm": pm}


@frappe.whitelist()
def client_approve_milestone(id, note=None):
	room = _client_room()
	if not _client_can_approve(room):
		frappe.throw(_("Only your team's administrator can approve on behalf of your company."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Milestone", id)
	from duty_board.uat import uat_gate_check

	uat_gate_check(doc.room, doc.title)
	if doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status != "Awaiting Approval":
		frappe.throw(_("This phase is not awaiting approval."))
	full = frappe.utils.get_fullname(frappe.session.user)
	frappe.db.set_value(
		"Duty Milestone",
		id,
		{
			"status": "Approved",
			"approved_by": frappe.session.user,
			"approved_full": full,
			"approved_at": now_datetime(),
			"approval_note": (note or "").strip()[:300] or None,
		},
		update_modified=False,
	)
	frappe.db.commit()
	stamp = frappe.utils.format_datetime(now_datetime(), "d MMM yyyy HH:mm")
	_post(
		room,
		_("✅ PHASE APPROVED: “{0}” — formally signed off by {1} on {2}{3}").format(
			doc.title, full, stamp, f' — “{note.strip()[:200]}”' if note else ""
		),
	)
	try:
		from duty_board.api import _notify_user

		for u in frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]
		):
			if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
				_notify_user(
					u.name,
					_("✅ {0} approved “{1}”").format(room.customer, doc.title),
					full,
				)
	except Exception:
		pass
	frappe.publish_realtime("duty_client_room", {"room": room.name})
	return _milestone_rows(room)


# ---------------- change requests: paid scope governance ----------------


def _chreq_locked(doc):
	if doc.status in ("Approved", "In Delivery", "Delivered"):
		frappe.throw(
			_("“{0}” has been formally approved by the client and can no longer be edited.").format(
				doc.title
			)
		)


def _chreq_currency():
	return frappe.db.get_default("currency") or "NGN"


def _chreq_fmt(v):
	if not v:
		return None
	return frappe.utils.fmt_money(v, currency=_chreq_currency())


def _chreq_rows(room):
	rows = frappe.get_all(
		"Duty Change Request",
		filters={"room": room.name},
		fields=[
			"name", "title", "status", "original_request", "reason", "scope_impact",
			"timeline_impact", "cost_impact", "resource_impact", "risks", "quotation",
			"approved_amount", "submitted_on", "approved_full", "approved_at",
			"approval_note", "declined_at", "decline_reason", "delivered_at",
			"source_type", "source_message", "source_issue",
			"released", "pricing_status", "estimate_hours", "invoice_status", "project",
		],
		order_by="creation desc",
	)
	_crpn = _project_names(room)
	for r in rows:
		r.submitted_on = str(r.submitted_on)[:16] if r.submitted_on else None
		r.approved_at = str(r.approved_at)[:16] if r.approved_at else None
		r.declined_at = str(r.declined_at)[:16] if r.declined_at else None
		r.delivered_at = str(r.delivered_at)[:16] if r.delivered_at else None
		r.cost_fmt = _chreq_fmt(r.cost_impact)
		r.approved_fmt = _chreq_fmt(r.approved_amount)
		r.project_name = _crpn.get(r.project)
		tasks = frappe.get_all(
			"Duty Project Task",
			filters={"change_request": r.name},
			fields=["title", "column"],
			order_by="creation asc",
			limit=60,
		)
		r.tasks = [
			{"title": t.title, "status": CLIENT_STATUS.get(t.column, "Queued")}
			for t in tasks
		]
		r.cards_total = len(tasks)
		r.cards_done = sum(1 for t in tasks if t.column == "Completed")
	return rows


@frappe.whitelist()
def chreq_add(name, title, original_request=None, project=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the change request a title."))
	frappe.get_doc(
		{
			"doctype": "Duty Change Request",
			"room": room.name,
			"title": title[:140],
			"status": "Draft",
			"original_request": (original_request or "").strip() or None,
			"source_type": "Manual",
			"project": _validate_milestone_project(room.name, project or None),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		from duty_board.commercial import notify_pricer_new_cr

		notify_pricer_new_cr(doc)
	except Exception:
		pass
	return get_room(name)


@frappe.whitelist()
def chreq_from_message(name, msg, title):
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names

	if require_staff_or_consultant() and name not in consultant_room_names():
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the change request a title."))
	m = frappe.db.get_value(
		"Client Room Message", msg, ["room", "message"], as_dict=True
	)
	if not m or m.room != room.name:
		frappe.throw(_("Message not found in this room."))
	_cr = frappe.get_doc(
		{
			"doctype": "Duty Change Request",
			"room": room.name,
			"title": title[:140],
			"status": "Draft",
			"original_request": m.message,
			"source_type": "Chat",
			"source_message": msg,
		}
	).insert(ignore_permissions=True)
	_post(room, _("💱 Change request drafted: “{0}”").format(title[:140]))
	frappe.db.commit()
	ret = get_room(name)
	ret["new_cr"] = _cr.name
	ret["new_cr_title"] = _cr.title
	return ret


@frappe.whitelist()
def chreq_from_issue(issue):
	from duty_board.permissions import require_staff_or_consultant

	if require_staff_or_consultant():
		from duty_board.api import _consultant_issue_check

		_consultant_issue_check(frappe.get_doc("Duty Issue", issue))
	i = frappe.db.get_value(
		"Duty Issue",
		issue,
		["title", "description", "customer", "source_type", "source"],
		as_dict=True,
	)
	if not i:
		frappe.throw(_("Issue not found."))
	room_name = None
	if i.source_type == "Client Room" and i.source and frappe.db.exists("Client Room", i.source):
		room_name = i.source
	else:
		room_name = frappe.db.get_value(
			"Client Room", {"customer": i.customer, "status": ["!=", "Archived"]}, "name"
		)
	if not room_name:
		frappe.throw(_("No client room found for {0}.").format(i.customer))
	room = frappe.get_doc("Client Room", room_name)
	cr = frappe.get_doc(
		{
			"doctype": "Duty Change Request",
			"room": room.name,
			"title": i.title[:140],
			"status": "Draft",
			"original_request": i.description or i.title,
			"source_type": "Ticket",
			"source_issue": issue,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	ret = get_room(room.name)
	ret["new_cr"] = cr.name
	ret["new_cr_title"] = cr.title
	return ret


@frappe.whitelist()
def chreq_update(
	id,
	title=None,
	reason=None,
	scope_impact=None,
	timeline_impact=None,
	cost_impact=None,
	resource_impact=None,
	risks=None,
	quotation=None, project=None):
	from duty_board.permissions import require_staff_or_consultant

	_is_c = require_staff_or_consultant()
	doc = frappe.get_doc("Duty Change Request", id)
	if _is_c:
		from duty_board.permissions import consultant_room_names

		ok = False
		if doc.source_issue:
			from duty_board.api import _consultant_issue_check

			try:
				_consultant_issue_check(frappe.get_doc("Duty Issue", doc.source_issue))
				ok = True
			except frappe.PermissionError:
				ok = False
		if not ok and doc.room in consultant_room_names():
			ok = True
		if not ok or quotation:
			frappe.throw(_("Not permitted."), frappe.PermissionError)
	_chreq_locked(doc)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the change request a title."))
	if quotation and not frappe.db.exists("Quotation", quotation):
		frappe.throw(_("Quotation {0} does not exist.").format(quotation))
	frappe.db.set_value(
		"Duty Change Request",
		id,
		{
			"title": title[:140],
			"reason": (reason or "").strip()[:500] or None,
			"scope_impact": (scope_impact or "").strip() or None,
			"timeline_impact": (timeline_impact or "").strip()[:140] or None,
			"cost_impact": frappe.utils.flt(cost_impact) or 0,
			"resource_impact": (resource_impact or "").strip()[:500] or None,
			"risks": (risks or "").strip()[:500] or None,
			"quotation": quotation or None,
			"project": _validate_milestone_project(doc.room, project or None),
		},
		update_modified=False,
	)
	frappe.db.commit()
	return get_room(doc.room)


@frappe.whitelist()
def chreq_request_approval(id):
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
	_chreq_locked(doc)
	ps = doc.get("pricing_status") or "Awaiting Pricing"
	if ps == "Awaiting Pricing":
		frappe.throw(_("This CR is in the pricing queue — it goes to the client once it has been priced."))
	if ps in ("Covered by Subscription", "Goodwill"):
		frappe.throw(_("No client approval needed — this CR is {0} and work can proceed.").format(ps.lower()))
	if ps in ("Rejected", "Deferred"):
		frappe.throw(_("This CR was {0} at pricing.").format(ps.lower()))
	if not cint(doc.get("released")):
		frappe.db.set_value("Duty Change Request", id, "released", 1, update_modified=False)
	if not (doc.scope_impact or "").strip():
		frappe.throw(_("Describe the scope impact before asking the client to approve."))
	frappe.db.set_value(
		"Duty Change Request",
		id,
		{"status": "Awaiting Approval", "submitted_on": now_datetime()},
		update_modified=False,
	)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	amt = _chreq_fmt(doc.cost_impact)
	_post(
		room,
		_("💱 Change request “{0}”{1} awaits your formal approval — open Projects on your portal.").format(
			doc.title, f" ({amt})" if amt else ""
		),
	)
	_push_room_clients(room, _("💱 Change request awaits your approval · Xlevel"), doc.title[:120])
	return get_room(doc.room)


@frappe.whitelist()
def chreq_set_status(id, status):
	_staff_only()
	if status in ("In Progress", "In Delivery", "Delivered"):
		from duty_board.commercial import work_may_proceed

		_doc = frappe.get_doc("Duty Change Request", id)
		if not work_may_proceed(_doc):
			frappe.throw(
				_("Work can't start on this CR yet — it needs pricing (and client approval if priced). Current: {0}").format(
					_doc.get("pricing_status") or "Awaiting Pricing"
				)
			)
	doc = frappe.get_doc("Duty Change Request", id)
	allowed = {
		"Approved": ["In Delivery"],
		"In Delivery": ["Delivered"],
		"Awaiting Approval": ["Draft"],
	}
	if status not in allowed.get(doc.status, []):
		frappe.throw(_("Cannot move “{0}” from {1} to {2}.").format(doc.title, doc.status, status))
	vals = {"status": status}
	if status == "Delivered":
		vals["delivered_at"] = now_datetime()
	frappe.db.set_value("Duty Change Request", id, vals, update_modified=False)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	if status == "In Delivery":
		_post(room, _("🚀 Change request “{0}” is now in delivery.").format(doc.title))
	elif status == "Delivered":
		_post(room, _("📦 Change request “{0}” has been delivered.").format(doc.title))
	return get_room(doc.room)


@frappe.whitelist()
def chreq_reopen(id):
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
	if doc.status != "Declined":
		frappe.throw(_("Only a declined change request can be reopened for revision."))
	frappe.db.set_value(
		"Duty Change Request",
		id,
		{"status": "Draft", "submitted_on": None},
		update_modified=False,
	)
	frappe.db.commit()
	return get_room(doc.room)


@frappe.whitelist()
def chreq_delete(id):
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
	if doc.status not in ("Draft", "Declined"):
		frappe.throw(_("Only draft or declined change requests can be deleted."))
	room = doc.room
	for t in frappe.get_all("Duty Project Task", filters={"change_request": id}, pluck="name"):
		frappe.db.set_value("Duty Project Task", t, "change_request", None, update_modified=False)
	frappe.delete_doc("Duty Change Request", id, ignore_permissions=True, force=True)
	frappe.db.commit()
	return get_room(room)


@frappe.whitelist()
def room_set_project(name, project=None):
	"""Set the room's DEFAULT board project (where new client requests land).
	Kept for back-compat with the scope dialog's single default field."""
	_staff_only()
	if project and not frappe.db.exists("Duty Project", project):
		frappe.throw(_("Unknown project."))
	frappe.db.set_value("Client Room", name, "project", project or None, update_modified=False)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def room_projects(name):
	"""For the scope dialog: this customer's active projects, each flagged
	with whether it currently belongs to THIS room."""
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	out = []
	for p in frappe.get_all(
		"Duty Project",
		filters={"customer": room.customer, "status": "Active"},
		fields=["name", "project_name", "room"],
		order_by="creation asc",
	):
		out.append({
			"name": p.name,
			"label": p.project_name or p.name,
			"mine": 1 if p.room == name else 0,
			"other_room": p.room if (p.room and p.room != name) else None,
		})
	return out


@frappe.whitelist()
def room_assign_projects(name, project_names):
	"""Assign a set of projects to THIS room. Because a project belongs to
	exactly one room, assigning here MOVES it off whatever room it was on.
	Projects of this customer not in the set, currently on this room, are
	left where they are only if still ticked — unticking moves nothing (a
	project must live somewhere); to move a project elsewhere, assign it
	there. Here we only ADD/!MOVE the ticked ones onto this room."""
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	import json as _json

	try:
		wanted = _json.loads(project_names) if isinstance(project_names, str) else (project_names or [])
	except Exception:
		wanted = []
	for pn in wanted:
		if not frappe.db.exists("Duty Project", pn):
			continue
		pc = frappe.db.get_value("Duty Project", pn, "customer")
		if pc != room.customer:
			continue  # never move a project across customers
		frappe.db.set_value("Duty Project", pn, "room", name, update_modified=False)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def chreq_new_task(id, title, assignee=None, due_date=None):
	"""Spawn a delivery card from a CR: ensures the room has a project
	(lazy-creating the requests project if none), creates the card in
	To Do already linked to this change request."""
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
	room = frappe.get_doc("Client Room", doc.room)
	project = _ensure_project(room)
	title = (title or "").strip()[:140]
	if not title:
		frappe.throw(_("Give the task a title."))
	frappe.get_doc(
		{
			"doctype": "Duty Project Task",
			"project": project,
			"title": title,
			"column": "To Do",
			"assignee": (assignee or "").strip() or None,
			"due_date": due_date or None,
			"urgency": "Medium",
			"change_request": id,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_room(doc.room)


@frappe.whitelist()
def chreq_task_options(id):
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
	room = frappe.get_doc("Client Room", doc.room)
	if not room.project:
		return {"project": None, "tasks": []}
	tasks = frappe.get_all(
		"Duty Project Task",
		filters={"project": room.project},
		fields=["name", "title", "column", "change_request"],
		order_by="creation asc",
	)
	return {
		"project": room.project,
		"tasks": [
			{
				"name": t.name,
				"title": t.title,
				"column": t.column,
				"checked": t.change_request == id,
				"elsewhere": bool(t.change_request and t.change_request != id),
			}
			for t in tasks
		],
	}


@frappe.whitelist()
def chreq_set_tasks(id, tasks):
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
	if isinstance(tasks, str):
		tasks = json.loads(tasks)
	current = set(
		frappe.get_all("Duty Project Task", filters={"change_request": id}, pluck="name")
	)
	wanted = set(tasks or [])
	for t in current - wanted:
		frappe.db.set_value("Duty Project Task", t, "change_request", None, update_modified=False)
	for t in wanted - current:
		frappe.db.set_value("Duty Project Task", t, "change_request", id, update_modified=False)
	frappe.db.commit()
	return get_room(doc.room)


def _chreq_client_rows(room):
	"""Drafts stay behind the membrane — the client sees a CR only once staff submit it."""
	gate = 1 if _client_can_approve(room) else 0
	rows = []
	for r in _chreq_rows(room):
		if not cint(r.get("released")):
			continue
		free = (r.get("pricing_status") or "") in ("Covered by Subscription", "Goodwill")
		if r.status in ("Awaiting Approval", "Approved", "Declined", "In Delivery", "Delivered") or free:
			r.no_charge = (
				(_("Covered by your subscription") if r.get("pricing_status") == "Covered by Subscription" else _("Approved by Xlevel as goodwill"))
				if free
				else None
			)
			rows.append(r)
	for r in rows:
		r.can_approve = gate
	return rows


@frappe.whitelist()
def client_get_chreqs():
	return _chreq_client_rows(_client_room())


def _chreq_notify_staff(room, text, body):
	try:
		from duty_board.api import _notify_user

		for u in frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]
		):
			if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
				_notify_user(u.name, text, body)
	except Exception:
		pass


@frappe.whitelist()
def client_approve_chreq(id, note=None):
	room = _client_room()
	if not _client_can_approve(room):
		frappe.throw(_("Only your team's administrator can approve on behalf of your company."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Change Request", id)
	if doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status != "Awaiting Approval":
		frappe.throw(_("This change request is not awaiting approval."))
	full = frappe.utils.get_fullname(frappe.session.user)
	frappe.db.set_value(
		"Duty Change Request",
		id,
		{
			"status": "Approved",
			"approved_by": frappe.session.user,
			"approved_full": full,
			"approved_at": now_datetime(),
			"approved_amount": doc.cost_impact or 0,
			"approval_note": (note or "").strip()[:300] or None,
		},
		update_modified=False,
	)
	frappe.db.commit()
	stamp = frappe.utils.format_datetime(now_datetime(), "d MMM yyyy HH:mm")
	amt = _chreq_fmt(doc.cost_impact)
	_post(
		room,
		_("✅ CHANGE REQUEST APPROVED: “{0}”{1} — formally signed off by {2} on {3}{4}").format(
			doc.title, f" at {amt}" if amt else "", full, stamp,
			f' — “{note.strip()[:200]}”' if note else "",
		),
	)
	_chreq_notify_staff(
		room, _("✅ {0} approved CR “{1}”").format(room.customer, doc.title), full
	)
	try:
		from duty_board.commercial import _spawn_cr_issue

		_spawn_cr_issue(frappe.get_doc("Duty Change Request", id))
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "cr spawn on approval")
	frappe.publish_realtime("duty_client_room", {"room": room.name})
	return _chreq_client_rows(room)


@frappe.whitelist()
def client_decline_chreq(id, reason):
	room = _client_room()
	if not _client_can_approve(room):
		frappe.throw(_("Only your team's administrator can approve on behalf of your company."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Change Request", id)
	if doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status != "Awaiting Approval":
		frappe.throw(_("This change request is not awaiting approval."))
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Please tell us why you are declining, so we can revise it."))
	full = frappe.utils.get_fullname(frappe.session.user)
	frappe.db.set_value(
		"Duty Change Request",
		id,
		{
			"status": "Declined",
			"declined_at": now_datetime(),
			"decline_reason": reason[:500],
		},
		update_modified=False,
	)
	frappe.db.commit()
	_post(
		room,
		_("↩ Change request “{0}” declined by {1} — “{2}”").format(
			doc.title, full, reason[:200]
		),
	)
	_chreq_notify_staff(
		room, _("↩ {0} declined CR “{1}”").format(room.customer, doc.title), reason[:120]
	)
	frappe.publish_realtime("duty_client_room", {"room": room.name})
	return _chreq_client_rows(room)


CLIENT_UPLOAD_EXTS = {
	"png", "jpg", "jpeg", "gif", "webp", "pdf", "doc", "docx", "xls", "xlsx",
	"csv", "txt", "zip", "webm", "mp4", "m4a", "mp3", "ogg", "wav", "ppt", "pptx",
}


@frappe.whitelist()
def client_upload():
	"""Portal file upload. Core upload_file now rejects unattached uploads from
	Website Users, so the portal uploads here instead: session resolved through
	the membrane first, size-capped, extension-whitelisted, and the File saved
	attached to the caller's own room."""
	room = _client_room()
	f = frappe.request.files.get("file")
	if not f:
		frappe.throw(_("No file received."))
	content = f.stream.read()
	if len(content) > 15 * 1024 * 1024:
		frappe.throw(_("File too large (max 15 MB)."))
	fname = (f.filename or "upload").strip()[:140]
	ext = fname.rsplit(".", 1)[1].lower() if "." in fname else ""
	if ext not in CLIENT_UPLOAD_EXTS:
		frappe.throw(_("File type .{0} is not allowed.").format(ext or "?"))
	doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"attached_to_doctype": "Client Room",
			"attached_to_name": room.name,
			"is_private": 1,
			"content": content,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"file_url": doc.file_url, "name": fname}


# ---------------- client administrators: who speaks for the customer ----------------


def _room_admins(room):
	return frappe.get_all(
		"Client Room Member",
		filters={"room": room.name, "active": 1, "is_admin": 1},
		fields=["user"],
	)


def _client_can_approve(room):
	"""Approvals lock to administrators once a room has any. Admin-less rooms
	keep today's behaviour: any member may approve."""
	admins = _room_admins(room)
	if not admins:
		return True
	return frappe.session.user in {a.user for a in admins}


def _client_admin_only(room):
	if not _room_admins(room):
		frappe.throw(
			_("No administrator is set for your team yet — ask Xlevel to appoint one."),
			frappe.PermissionError,
		)
	if not _client_can_approve(room):
		frappe.throw(_("Only your team's administrator can do this."), frappe.PermissionError)


@frappe.whitelist()
def client_get_team():
	room = _client_room()
	members = frappe.get_all(
		"Client Room Member",
		filters={"room": room.name, "active": 1},
		fields=["name", "user", "is_admin", "last_seen"],
		order_by="is_admin desc, creation asc",
	)
	for m in members:
		m.full_name = frappe.utils.get_fullname(m.user)
		m.is_self = m.user == frappe.session.user
		m.last_seen = str(m.last_seen)[:16] if m.last_seen else None
	me_admin = any(m.is_admin and m.is_self for m in members)
	return {
		"members": members,
		"me_admin": bool(me_admin),
		"restricted": bool(any(m.is_admin for m in members)),
	}


@frappe.whitelist()
def client_add_member(email, full_name=None):
	room = _client_room()
	_client_admin_only(room)
	email = (email or "").strip().lower()
	frappe.utils.validate_email_address(email, throw=True)
	if frappe.db.count("Client Room Member", {"room": room.name, "active": 1}) >= 25:
		frappe.throw(_("Member limit reached for this room — contact Xlevel."))
	if frappe.db.exists("User", email):
		if frappe.db.get_value("User", email, "user_type") != "Website User":
			frappe.throw(_("{0} cannot be added to a client portal.").format(email))
		frappe.db.set_value("User", email, "enabled", 1, update_modified=False)
	else:
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": (full_name or email.split("@")[0]).strip()[:80],
				"user_type": "Website User",
				"send_welcome_email": 1,
			}
		).insert(ignore_permissions=True)
	existing = frappe.db.get_value("Client Room Member", {"room": room.name, "user": email}, "name")
	if existing:
		frappe.db.set_value("Client Room Member", existing, "active", 1, update_modified=False)
	else:
		frappe.get_doc(
			{"doctype": "Client Room Member", "room": room.name, "user": email, "active": 1}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	_post(
		room,
		_("👥 {0} added {1} to this room.").format(
			frappe.utils.get_fullname(frappe.session.user), email
		),
	)
	return client_get_team()


@frappe.whitelist()
def client_remove_member(user):
	room = _client_room()
	_client_admin_only(room)
	row = frappe.db.get_value(
		"Client Room Member", {"room": room.name, "user": user, "active": 1}, ["name", "is_admin"], as_dict=True
	)
	if not row:
		frappe.throw(_("Not a member of your team."))
	if row.is_admin and len(_room_admins(room)) <= 1:
		frappe.throw(_("You cannot remove the only administrator."))
	frappe.db.set_value("Client Room Member", row.name, "active", 0, update_modified=False)
	frappe.db.commit()
	_post(
		room,
		_("👥 {0} removed {1} from this room.").format(
			frappe.utils.get_fullname(frappe.session.user), user
		),
	)
	return client_get_team()


@frappe.whitelist()
def client_set_admin(user, on):
	room = _client_room()
	_client_admin_only(room)
	row = frappe.db.get_value(
		"Client Room Member", {"room": room.name, "user": user, "active": 1}, ["name", "is_admin"], as_dict=True
	)
	if not row:
		frappe.throw(_("Not a member of your team."))
	on = cint(on)
	if not on and row.is_admin and len(_room_admins(room)) <= 1:
		frappe.throw(_("You cannot demote the only administrator."))
	frappe.db.set_value("Client Room Member", row.name, "is_admin", on, update_modified=False)
	frappe.db.commit()
	if on:
		_post(
			room,
			_("★ {0} is now a team administrator, appointed by {1}.").format(
				frappe.utils.get_fullname(user), frappe.utils.get_fullname(frappe.session.user)
			),
		)
	return client_get_team()


@frappe.whitelist()
def member_set_admin(member_name, on):
	_staff_only()
	room_name = frappe.db.get_value("Client Room Member", member_name, "room")
	frappe.db.set_value("Client Room Member", member_name, "is_admin", cint(on), update_modified=False)
	frappe.db.commit()
	return get_room(room_name)


# ---------------- client health: who's drifting ----------------


def _room_health(room_name):
	"""Green/Amber/Red with plain reasons. Cheap enough to run per room list."""
	from datetime import timedelta

	reasons = []
	month_ago = now_datetime() - timedelta(days=30)
	week_ago = now_datetime() - timedelta(days=7)
	room = frappe.db.get_value(
		"Client Room", room_name, ["customer", "unit"], as_dict=True
	)
	downs = frappe.db.count(
		"Duty Issue",
		{
			"customer": room.customer,
			"client_rating": "Down",
			"modified": [">=", month_ago],
		},
	)
	if downs:
		reasons.append(_("{0} 👎 in 30 days").format(downs))
	aging = frappe.db.count(
		"Duty Issue",
		{
			"customer": room.customer,
			"client_visible": 1,
			"status": ["in", ["Open", "In Progress"]],
			"creation": ["<", week_ago],
		},
	)
	if aging:
		reasons.append(_("{0} open >7 days").format(aging))
	sla_missed = frappe.db.count(
		"Duty Issue",
		{
			"customer": room.customer,
			"sla_res_met": 0,
			"resolved_at": [">=", month_ago],
			"sla_res_due": ["is", "set"],
		},
	)
	if sla_missed:
		reasons.append(_("{0} SLA missed in 30 days").format(sla_missed))
	last_msg = frappe.db.get_value(
		"Client Room Message",
		{"room": room_name, "internal": 0},
		"creation",
		order_by="creation desc",
	)
	if last_msg:
		silent_days = (now_datetime() - frappe.utils.get_datetime(last_msg)).days
		if silent_days >= 14:
			reasons.append(_("silent {0} days").format(silent_days))
	score = downs * 2 + aging + sla_missed + (1 if last_msg and silent_days >= 14 else 0)
	state = "red" if score >= 4 or downs >= 2 else "amber" if score >= 1 else "green"
	return {"state": state, "reasons": reasons}


# ---------------- monthly service report: the scorecard ----------------


def _report_stats(room, start, end):
	"""Everything the scorecard says about one room's month."""
	from duty_board.api import _bh_between, _bh_fmt

	issues = frappe.get_all(
		"Duty Issue",
		filters={"customer": room.customer, "client_visible": 1},
		fields=[
			"name", "title", "status", "creation", "resolved_at", "acknowledged_at",
			"sla_ack_met", "sla_res_met", "sla_ack_due", "sla_res_due",
			"client_rating", "severity", "source_type", "source",
		],
		limit=500,
	)
	issues = [i for i in issues if _issue_in_room(i, room)]

	def _in(dt):
		return dt and str(start) <= str(dt) < str(end)

	new = [i for i in issues if _in(i.creation)]
	resolved = [i for i in issues if _in(i.resolved_at)]
	open_now = [i for i in issues if i.status in ("Open", "In Progress")]

	ack_verdicts = [i for i in resolved if i.sla_ack_due and i.acknowledged_at]
	res_verdicts = [i for i in resolved if i.sla_res_due]
	ack_hit = sum(1 for i in ack_verdicts if cint(i.sla_ack_met))
	res_hit = sum(1 for i in res_verdicts if cint(i.sla_res_met))

	ack_times = [
		_bh_between(frappe.utils.get_datetime(i.creation), frappe.utils.get_datetime(i.acknowledged_at))
		for i in resolved
		if i.acknowledged_at
	]
	res_times = [
		_bh_between(frappe.utils.get_datetime(i.creation), frappe.utils.get_datetime(i.resolved_at))
		for i in resolved
		if i.resolved_at
	]

	ups = sum(1 for i in issues if i.client_rating == "Up" and _in(i.resolved_at))
	downs = sum(1 for i in issues if i.client_rating == "Down" and _in(i.resolved_at))

	meetings = frappe.db.count(
		"Duty Meeting",
		{"room": room.name, "outcome": "Held", "meeting_date": ["between", [str(start)[:10], str(end)[:10]]]},
	)
	milestones = frappe.get_all(
		"Duty Milestone",
		filters={"room": room.name, "status": "Approved"},
		fields=["title", "approved_at", "approved_full"],
	)
	milestones = [m for m in milestones if _in(m.approved_at)]

	return {
		"new": len(new),
		"resolved": len(resolved),
		"open_now": len(open_now),
		"ack_pct": round(ack_hit * 100 / len(ack_verdicts)) if ack_verdicts else None,
		"res_pct": round(res_hit * 100 / len(res_verdicts)) if res_verdicts else None,
		"avg_ack": _bh_fmt(sum(ack_times) // len(ack_times)) if ack_times else None,
		"avg_res": _bh_fmt(sum(res_times) // len(res_times)) if res_times else None,
		"ups": ups,
		"downs": downs,
		"meetings": meetings,
		"milestones": milestones,
		"resolved_titles": [i.title for i in resolved][:12],
		"activity": bool(new or resolved or meetings or milestones),
	}


def _report_html(room, label, s):
	unit = room.unit or "General"
	kpi = lambda n, l: f'<div class="k"><b>{n}</b><span>{l}</span></div>'
	sla_bits = ""
	if s["ack_pct"] is not None or s["res_pct"] is not None:
		sla_bits = '<h2>Our promises, kept</h2><div class="kpis">'
		if s["ack_pct"] is not None:
			sla_bits += kpi(f'{s["ack_pct"]}%', "responses within SLA")
		if s["res_pct"] is not None:
			sla_bits += kpi(f'{s["res_pct"]}%', "resolutions within SLA")
		if s["avg_ack"]:
			sla_bits += kpi(s["avg_ack"], "average response time")
		if s["avg_res"]:
			sla_bits += kpi(s["avg_res"], "average resolution time")
		sla_bits += "</div>"
	ms_bits = ""
	if s["milestones"]:
		ms_bits = "<h2>Milestones you approved</h2><ul>" + "".join(
			f"<li>✅ <b>{frappe.utils.escape_html(m.title)}</b> — signed off by {frappe.utils.escape_html(m.approved_full or '')}</li>"
			for m in s["milestones"]
		) + "</ul>"
	work_bits = ""
	if s["resolved_titles"]:
		work_bits = "<h2>Completed this month</h2><ul>" + "".join(
			f"<li>{frappe.utils.escape_html(t)}</li>" for t in s["resolved_titles"]
		) + "</ul>"
	sat = ""
	if s["ups"] or s["downs"]:
		sat = f'<p class="sat">Your ratings this month: 👍 {s["ups"]} &nbsp; 👎 {s["downs"]}</p>'
	return f"""<html><head><meta charset="utf-8"><style>
	body {{ font-family: Helvetica, Arial, sans-serif; color: #1f2937; margin: 34px 40px; }}
	.head {{ border-bottom: 4px solid #0F5C55; padding-bottom: 12px; margin-bottom: 20px; }}
	.head h1 {{ color: #0F5C55; margin: 0 0 4px; font-size: 24px; }}
	.head p {{ margin: 0; color: #6b7280; font-size: 13px; }}
	h2 {{ color: #0E7490; font-size: 15px; margin: 22px 0 8px; }}
	.kpis {{ display: table; width: 100%; border-spacing: 8px 0; }}
	.k {{ display: table-cell; background: #f0fdfa; border-radius: 10px; padding: 12px; text-align: center; }}
	.k b {{ display: block; font-size: 22px; color: #0F5C55; }}
	.k span {{ font-size: 11px; color: #6b7280; }}
	ul {{ margin: 6px 0; padding-left: 20px; font-size: 13px; }}
	li {{ margin: 3px 0; }}
	.sat {{ font-size: 14px; }}
	.foot {{ margin-top: 28px; border-top: 1px solid #e5e7eb; padding-top: 10px; font-size: 11px; color: #6b7280; }}
	</style></head><body>
	<div class="head">
		<h1>Monthly Service Report — {frappe.utils.escape_html(label)}</h1>
		<p>{frappe.utils.escape_html(room.customer)}{" · " + frappe.utils.escape_html(unit) if unit != "General" else ""} · prepared by Xlevel Retail Systems</p>
	</div>
	<h2>The month at a glance</h2>
	<div class="kpis">{kpi(s["new"], "new requests")}{kpi(s["resolved"], "completed")}{kpi(s["open_now"], "in progress now")}{kpi(s["meetings"], "meetings held")}</div>
	{sla_bits}{ms_bits}{work_bits}{sat}
	<div class="foot">Generated automatically by your Xlevel Client Portal · xlevel.clouderp.one/portal · Questions? Just reply in your portal chat.</div>
	</body></html>"""


def _generate_room_report(room, start, end, label):
	s = _report_stats(room, start, end)
	if not s["activity"]:
		return None
	pdf = get_pdf(_report_html(room, label, s))
	fname = f"Xlevel_Service_Report_{label.replace(' ', '_')}.pdf"
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"content": pdf,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Client Shelf Doc",
			"room": room.name,
			"title": _("Service Report — {0}").format(label),
			"category": _("Monthly Report"),
			"file_url": f.file_url,
			"file_name": fname,
			"active": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	_post(room, _("📊 Your service report for {0} is on your shelf.").format(label))
	_push_room_clients(room, _("📊 {0} report · Xlevel").format(label), _("Your monthly service report is ready"))
	return s


@frappe.whitelist()
def generate_service_report(name):
	"""Staff: report for the previous calendar month, on demand."""
	_staff_only()
	import calendar
	from datetime import date

	room = frappe.get_doc("Client Room", name)
	today_d = getdate(today())
	first_this = today_d.replace(day=1)
	last_month_end = first_this
	last_month_start = getdate(frappe.utils.add_days(first_this, -1)).replace(day=1)
	label = calendar.month_name[last_month_start.month] + " " + str(last_month_start.year)
	s = _generate_room_report(room, last_month_start, last_month_end, label)
	if not s:
		frappe.throw(_("No activity in {0} for this room — nothing to report.").format(label))
	return {"ok": True, "label": label}


def monthly_service_reports():
	"""Cron: first of the month, every active room with a story to tell."""
	import calendar

	today_d = getdate(today())
	first_this = today_d.replace(day=1)
	last_month_start = getdate(frappe.utils.add_days(first_this, -1)).replace(day=1)
	label = calendar.month_name[last_month_start.month] + " " + str(last_month_start.year)
	for r in frappe.get_all("Client Room", filters={"status": "Active"}, pluck="name"):
		try:
			room = frappe.get_doc("Client Room", r)
			_generate_room_report(room, last_month_start, first_this, label)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "duty_board.monthly_service_reports")


# ---------------- academy: training + certificates ----------------


def _training_rows(room):
	rows = frappe.get_all(
		"Duty Training Record",
		filters={"room": room.name},
		fields=[
			"name", "module", "trainee", "trainee_name", "status",
			"completed_on", "certificate_shelf",
		],
		order_by="creation asc",
	)
	mods = {
		m.name: m
		for m in frappe.get_all(
			"Duty Training Module", fields=["name", "title", "product", "sort_order"]
		)
	}
	for r in rows:
		m = mods.get(r.module)
		r.module_title = m.title if m else r.module
		r.product = m.product if m else None
		r.completed_on = str(r.completed_on) if r.completed_on else None
	rows.sort(key=lambda r: (mods[r.module].sort_order or 999) if r.module in mods else 999)
	return rows


@frappe.whitelist()
def training_modules():
	_staff_only()
	return frappe.get_all(
		"Duty Training Module",
		filters={"active": 1},
		fields=["name", "title", "product"],
		order_by="product asc, title asc",
	)


@frappe.whitelist()
def training_module_add(title, product=None):
	_staff_only()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the module a title."))
	doc = frappe.get_doc(
		{
			"doctype": "Duty Training Module",
			"title": title[:120],
			"product": (product or "").strip()[:60] or None,
			"active": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def room_training(name):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	return _training_rows(room)


@frappe.whitelist()
def room_tracks_for_assign(name):
	"""Client-audience tracks matching this room's products, for the assign dialog."""
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	prods = _room_products(room)
	out = []
	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},
		fields=["name", "title", "product"],
		order_by="product asc, title asc",
	):
		if (t.product or "").strip().lower() not in prods:
			continue
		n = frappe.db.count("Duty Certification Track Module", {"parent": t.name})
		if n:
			out.append({"name": t.name, "title": t.title, "product": t.product, "module_count": n})
	return out


@frappe.whitelist()
def training_assign_track_room(name, track, user):
	"""Assign every module of a client track to a room member at once.
	Existing assignments kept, not duplicated; one room narration, one notification."""
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	if not frappe.db.exists("Client Room Member", {"room": room.name, "user": user, "active": 1}):
		frappe.throw(_("That person is not a member of this room."))
	t = frappe.db.get_value(
		"Duty Certification Track", track, ["title", "product", "audience", "active"], as_dict=True
	)
	if not t or not cint(t.active) or t.audience != "Client":
		frappe.throw(_("Not found."))
	if (t.product or "").strip().lower() not in _room_products(room):
		frappe.throw(_("This track is not part of this room's products."))
	mods = frappe.get_all(
		"Duty Certification Track Module", filters={"parent": track}, pluck="module", order_by="idx asc"
	)
	created, existing = 0, 0
	for m in mods:
		if frappe.db.exists("Duty Training Record", {"room": room.name, "module": m, "trainee": user}):
			existing += 1
			continue
		frappe.get_doc(
			{
				"doctype": "Duty Training Record",
				"room": room.name,
				"module": m,
				"trainee": user,
				"trainee_name": frappe.utils.get_fullname(user),
				"status": "Assigned",
			}
		).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	if created:
		_post(
			room,
			_("🎓 Track assigned: “{0}” for {1} ({2} course(s))").format(
				t.title, frappe.utils.get_fullname(user), created
			),
		)
		try:
			from duty_board.api import _notify_user

			_notify_user(
				user, _("🎓 New training · Xlevel"), _("{0} — {1} course(s) assigned").format(t.title, created)
			)
		except Exception:
			pass
	return {"created": created, "existing": existing, "rows": _training_rows(room)}


@frappe.whitelist()
def training_assign(name, module, user):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	if not frappe.db.exists(
		"Client Room Member", {"room": room.name, "user": user, "active": 1}
	):
		frappe.throw(_("That person is not a member of this room."))
	if frappe.db.exists(
		"Duty Training Record", {"room": room.name, "module": module, "trainee": user}
	):
		frappe.throw(_("Already assigned."))
	frappe.get_doc(
		{
			"doctype": "Duty Training Record",
			"room": room.name,
			"module": module,
			"trainee": user,
			"trainee_name": frappe.utils.get_fullname(user),
			"status": "Assigned",
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	mod_title = frappe.db.get_value("Duty Training Module", module, "title")
	_post(room, _("🎓 Training assigned: “{0}” for {1}").format(mod_title, frappe.utils.get_fullname(user)))
	try:
		from duty_board.api import _notify_user

		_notify_user(user, _("🎓 New training · Xlevel"), mod_title)
	except Exception:
		pass
	return _training_rows(room)


def _certificate_html(trainee_name, module_title, product, date_str):
	prod = f" · {frappe.utils.escape_html(product)}" if product else ""
	return f"""<html><head><meta charset="utf-8"><style>
	body {{ font-family: Georgia, 'Times New Roman', serif; margin: 0; padding: 0; }}
	.frame {{ margin: 30px; border: 3px double #0F5C55; padding: 46px 40px; text-align: center; }}
	.brand {{ color: #0F5C55; font-size: 13px; letter-spacing: 0.25em; text-transform: uppercase; }}
	h1 {{ color: #0F5C55; font-size: 34px; margin: 18px 0 6px; }}
	.sub {{ color: #6b7280; font-size: 14px; margin-bottom: 30px; }}
	.name {{ font-size: 30px; margin: 22px 0 8px; border-bottom: 1px solid #d1d5db; display: inline-block; padding: 0 34px 8px; }}
	.mod {{ font-size: 19px; color: #0E7490; margin: 16px 0 4px; }}
	.date {{ color: #6b7280; font-size: 13px; margin-top: 26px; }}
	.sig {{ margin-top: 44px; display: inline-block; border-top: 1px solid #9ca3af; padding: 6px 40px 0; font-size: 13px; color: #374151; }}
	</style></head><body><div class="frame">
	<div class="brand">Xlevel Retail Systems · CloudERP.One</div>
	<h1>Certificate of Completion</h1>
	<div class="sub">This certifies that</div>
	<div class="name">{frappe.utils.escape_html(trainee_name)}</div>
	<div class="sub">has successfully completed the training module</div>
	<div class="mod">“{frappe.utils.escape_html(module_title)}”{prod}</div>
	<div class="date">Awarded on {date_str}</div>
	<div class="sig">Olamide Shodunke · Chief Executive Officer</div>
	</div></body></html>"""


def _award_module_completion(rec, trained_by=None):
	"""Mark a training record Completed. Roomed records also get the module
	certificate on the room shelf + narration; room-less (consultant) records
	just complete — track-level certificates come from the certification layer."""
	mod = frappe.db.get_value(
		"Duty Training Module", rec.module, ["title", "product"], as_dict=True
	)
	vals = {"status": "Completed", "completed_on": today()}
	if trained_by:
		vals["trained_by"] = trained_by
	if rec.room:
		room = frappe.get_doc("Client Room", rec.room)
		date_str = frappe.utils.format_date(today(), "d MMMM yyyy")
		pdf = get_pdf(
			_certificate_html(rec.trainee_name, mod.title, mod.product, date_str)
		)
		fname = f"Certificate_{rec.trainee_name.replace(' ', '_')}_{mod.title.replace(' ', '_')[:40]}.pdf"
		f = frappe.get_doc(
			{"doctype": "File", "file_name": fname, "content": pdf, "is_private": 1}
		).insert(ignore_permissions=True)
		shelf = frappe.get_doc(
			{
				"doctype": "Client Shelf Doc",
				"room": room.name,
				"title": _("Certificate — {0} · {1}").format(rec.trainee_name, mod.title),
				"category": _("Certificate"),
				"file_url": f.file_url,
				"file_name": fname,
				"active": 1,
			}
		).insert(ignore_permissions=True)
		vals["certificate_shelf"] = shelf.name
	rec.db_set(vals, update_modified=False)
	frappe.db.commit()
	if rec.room:
		_post(
			room,
			_("🎓 {0} is now certified: “{1}” — the certificate is on your shelf. Congratulations!").format(
				rec.trainee_name, mod.title
			),
		)
		_push_room_clients(room, _("🎓 Certificate awarded · Xlevel"), _("{0} — {1}").format(rec.trainee_name, mod.title))
	try:
		_evaluate_certifications(rec.trainee)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board certification evaluation")


@frappe.whitelist()
def training_complete(record):
	_staff_only()
	rec = frappe.get_doc("Duty Training Record", record)
	if rec.status == "Completed":
		frappe.throw(_("Already completed."))
	if not rec.room:
		frappe.throw(_("Consultant records complete through the assessment."))
	_award_module_completion(rec, trained_by=frappe.session.user)
	return _training_rows(frappe.get_doc("Client Room", rec.room))


def _room_metrics(room):
	"""One room's numbers: last 30 days + the whole engagement."""
	from datetime import timedelta

	now = now_datetime()
	s = _report_stats(room, now - timedelta(days=30), now + timedelta(days=1))
	rated = frappe.get_all(
		"Duty Issue",
		filters={"customer": room.customer, "client_visible": 1, "client_stars": [">", 0]},
		fields=["client_stars", "source_type", "source"],
		limit=200,
	)
	rated = [r for r in rated if _issue_in_room(r, room)]
	avg_stars = round(sum(r.client_stars for r in rated) / len(rated), 1) if rated else None
	ms_total = frappe.db.count("Duty Milestone", {"room": room.name})
	ms_done = frappe.db.count("Duty Milestone", {"room": room.name, "status": "Approved"})
	return {
		"new_30": s["new"],
		"resolved_30": s["resolved"],
		"open_now": s["open_now"],
		"avg_ack": s["avg_ack"],
		"avg_res": s["avg_res"],
		"ack_pct": s["ack_pct"],
		"res_pct": s["res_pct"],
		"avg_stars": avg_stars,
		"rated_n": len(rated),
		"ms_done": ms_done,
		"ms_total": ms_total,
		"ms_pct": round(ms_done * 100 / ms_total) if ms_total else None,
	}


@frappe.whitelist()
def client_get_metrics():
	return _room_metrics(_client_room())


@frappe.whitelist()
def room_metrics(name):
	_staff_only()
	return _room_metrics(frappe.get_doc("Client Room", name))


@frappe.whitelist()
def client_get_training():
	room = _client_room()
	rows = _training_rows(room)
	user = frappe.session.user
	my_modules = [r.module for r in rows if r.trainee == user]
	lesson_counts, done_counts = {}, {}
	if my_modules:
		for l in frappe.get_all(
			"Duty Lesson", filters={"module": ["in", my_modules]}, fields=["name", "module"]
		):
			lesson_counts[l.module] = lesson_counts.get(l.module, 0) + 1
		for p in frappe.get_all(
			"Duty Lesson Progress",
			filters={"user": user, "module": ["in", my_modules], "completed_at": ["is", "set"]},
			fields=["module"],
		):
			done_counts[p.module] = done_counts.get(p.module, 0) + 1
	return [
		{
			"record": r.name,
			"trainee_name": r.trainee_name,
			"module_title": r.module_title,
			"product": r.product,
			"status": r.status,
			"completed_on": r.completed_on,
			"cert": r.certificate_shelf,
			"mine": r.trainee == user,
			"lessons_total": lesson_counts.get(r.module, 0) if r.trainee == user else None,
			"lessons_done": done_counts.get(r.module, 0) if r.trainee == user else None,
		}
		for r in rows
	]


def _my_training_record(room, module):
	rec = frappe.db.get_value(
		"Duty Training Record",
		{"room": room.name, "module": module, "trainee": frappe.session.user},
		["name", "status"],
		as_dict=True,
	)
	if not rec:
		frappe.throw(_("This course is not assigned to you."), frappe.PermissionError)
	return rec


@frappe.whitelist()
def client_course(record):
	room = _client_room()
	rec = frappe.db.get_value(
		"Duty Training Record", record, ["room", "module", "trainee"], as_dict=True
	)
	if not rec or rec.room != room.name or rec.trainee != frappe.session.user:
		frappe.throw(_("Not found."), frappe.PermissionError)
	mod = frappe.db.get_value(
		"Duty Training Module", rec.module, ["title", "product", "description"], as_dict=True
	)
	lessons = frappe.get_all(
		"Duty Lesson",
		filters={"module": rec.module},
		fields=["name", "title", "est_minutes"],
		order_by="sort_order asc, creation asc",
	)
	done = {
		p.lesson
		for p in frappe.get_all(
			"Duty Lesson Progress",
			filters={"user": frappe.session.user, "module": rec.module, "completed_at": ["is", "set"]},
			fields=["lesson"],
		)
	}
	return {
		"record": record,
		"title": mod.title,
		"product": mod.product,
		"description": mod.description,
		"status": frappe.db.get_value("Duty Training Record", record, "status"),
		"quiz": _quiz_state(rec.module, frappe.session.user),
		"lessons": [
			{"name": l.name, "title": l.title, "est_minutes": l.est_minutes or 5, "done": l.name in done}
			for l in lessons
		],
	}


def _lesson_access(lesson):
	room = _client_room()
	l = frappe.db.get_value(
		"Duty Lesson", lesson, ["module", "title", "content", "est_minutes"], as_dict=True
	)
	if not l:
		frappe.throw(_("Not found."), frappe.PermissionError)
	rec = _my_training_record(room, l.module)
	return room, l, rec


@frappe.whitelist()
def client_lesson(lesson):
	room, l, rec = _lesson_access(lesson)
	user = frappe.session.user
	prog = frappe.db.get_value(
		"Duty Lesson Progress", {"user": user, "lesson": lesson},
		["name", "seconds", "completed_at"], as_dict=True,
	)
	if not prog:
		frappe.get_doc(
			{
				"doctype": "Duty Lesson Progress",
				"user": user,
				"lesson": lesson,
				"module": l.module,
				"opened_at": now_datetime(),
				"seconds": 0,
			}
		).insert(ignore_permissions=True)
		prog = frappe._dict(seconds=0, completed_at=None)
	if rec.status == "Assigned":
		frappe.db.set_value("Duty Training Record", rec.name, "status", "Reading", update_modified=False)
	frappe.db.commit()
	return {
		"title": l.title,
		"html": frappe.utils.sanitize_html(l.content or ""),
		"est_minutes": l.est_minutes or 5,
		"seconds": prog.seconds or 0,
		"done": bool(prog.completed_at),
	}


@frappe.whitelist()
def client_lesson_beat(lesson, secs):
	_room, l, _rec = _lesson_access(lesson)
	secs = max(0, min(40, cint(secs)))
	name = frappe.db.get_value(
		"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson}, "name"
	)
	if name and secs:
		frappe.db.sql(
			"update `tabDuty Lesson Progress` set seconds = seconds + %s where name = %s",
			(secs, name),
		)
		frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def client_lesson_done(lesson):
	room, l, rec = _lesson_access(lesson)
	prog = frappe.db.get_value(
		"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson},
		["name", "seconds", "completed_at"], as_dict=True,
	)
	if not prog:
		frappe.throw(_("Open the lesson first."))
	if not prog.completed_at:
		frappe.db.set_value(
			"Duty Lesson Progress", prog.name, "completed_at", now_datetime(), update_modified=False
		)
		frappe.db.commit()
	return client_course(
		frappe.db.get_value(
			"Duty Training Record",
			{"room": room.name, "module": l.module, "trainee": frappe.session.user},
			"name",
		)
	)


# ---------------- academy, staff face: consultant training ----------------


@frappe.whitelist()
def training_modules_for_staff():
	_staff_only()
	return frappe.get_all(
		"Duty Training Module",
		filters={"active": 1, "audience": ["in", ["Consultant", "Both"]]},
		fields=["name", "title", "product"],
		order_by="product asc, title asc",
	)


@frappe.whitelist()
def training_assign_staff(module, user):
	_staff_only()
	if frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("Consultant training is for staff accounts."))
	aud = frappe.db.get_value("Duty Training Module", module, "audience")
	if aud not in ("Consultant", "Both"):
		frappe.throw(_("That course is client-facing — its audience does not include consultants."))
	if frappe.db.exists(
		"Duty Training Record", {"module": module, "trainee": user, "room": ["is", "not set"]}
	):
		frappe.throw(_("Already assigned."))
	frappe.get_doc(
		{
			"doctype": "Duty Training Record",
			"module": module,
			"trainee": user,
			"trainee_name": frappe.utils.get_fullname(user),
			"status": "Assigned",
			"trained_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		from duty_board.api import _notify_user

		_notify_user(
			user, _("🎓 New training · Xlevel"), frappe.db.get_value("Duty Training Module", module, "title")
		)
	except Exception:
		pass
	return my_training()


@frappe.whitelist()
def training_team_overview():
	"""Managers: every staff member's academy position — modules assigned/
	completed, lessons done, quiz results, certificates, last activity."""
	_staff_only()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("The team training overview is for managers."), frappe.PermissionError)

	recs = frappe.get_all(
		"Duty Training Record",
		filters={"room": ["is", "not set"]},
		fields=["trainee", "trainee_name", "module", "status", "completed_on"],
		order_by="trainee asc, creation asc",
		limit_page_length=0,
	)
	if not recs:
		return {"people": []}
	mods = {
		m.name: m
		for m in frappe.get_all("Duty Training Module", fields=["name", "title", "product"])
	}
	lesson_totals = {}
	for l in frappe.get_all("Duty Lesson", fields=["module"], limit_page_length=0):
		lesson_totals[l.module] = lesson_totals.get(l.module, 0) + 1
	users = sorted({r.trainee for r in recs})
	done = {}
	last_active = {}
	for p in frappe.get_all(
		"Duty Lesson Progress",
		filters={"user": ["in", users]},
		fields=["user", "module", "completed_at", "modified"],
		limit_page_length=0,
	):
		if p.completed_at:
			done[(p.user, p.module)] = done.get((p.user, p.module), 0) + 1
		la = last_active.get(p.user)
		if not la or str(p.modified) > str(la):
			last_active[p.user] = p.modified
	quiz = {}
	for q in frappe.get_all(
		"Duty Quiz Attempt",
		filters={"user": ["in", users], "finished_at": ["is", "set"]},
		fields=["user", "module", "score", "passed"],
		order_by="finished_at asc",
		limit_page_length=0,
	):
		k = (q.user, q.module)
		cur = quiz.get(k, {"attempts": 0, "best": 0, "passed": 0, "attempts_to_pass": 0})
		cur["attempts"] += 1
		cur["best"] = max(cur["best"], cint(q.score))
		if cint(q.passed) and not cur["passed"]:
			cur["passed"] = 1
			cur["attempts_to_pass"] = cur["attempts"]
		quiz[k] = cur
	certs = {}
	for c in frappe.get_all(
		"Duty Certificate",
		filters={"user": ["in", users], "status": "Issued"},
		fields=["user", "track_title", "product", "issued_on"],
		order_by="issued_on asc",
		limit_page_length=0,
	):
		certs.setdefault(c.user, []).append(
			{"title": c.track_title, "product": c.product, "on": str(c.issued_on)[:10]}
		)
	people = []
	for u in users:
		mine = [r for r in recs if r.trainee == u]
		rows = []
		completed = 0
		for r in mine:
			m = mods.get(r.module) or frappe._dict()
			q = quiz.get((u, r.module), {})
			if r.status == "Completed":
				completed += 1
			rows.append(
				{
					"module": r.module,
					"title": m.get("title") or r.module,
					"product": m.get("product"),
					"status": r.status,
					"completed_on": str(r.completed_on)[:10] if r.completed_on else None,
					"lessons_done": done.get((u, r.module), 0),
					"lessons_total": lesson_totals.get(r.module, 0),
					"quiz_attempts": q.get("attempts", 0),
					"quiz_best": q.get("best", 0),
					"quiz_passed": q.get("passed", 0),
					"quiz_to_pass": q.get("attempts_to_pass", 0),
				}
			)
		people.append(
			{
				"user": u,
				"name": (mine[0].trainee_name or frappe.utils.get_fullname(u)) if mine else u,
				"assigned": len(mine),
				"completed": completed,
				"certificates": certs.get(u, []),
				"last_active": str(last_active.get(u) or "")[:10] or None,
				"rows": rows,
			}
		)
	people.sort(key=lambda p: (-(p["assigned"] - p["completed"]), p["name"]))
	return {"people": people}


@frappe.whitelist()
def staff_tracks():
	"""Consultant-audience certification tracks, for the assign dialog."""
	_staff_only()
	out = []
	for t in frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1},
		fields=["name", "title", "product", "audience"],
		order_by="product asc, title asc",
	):
		mods = frappe.get_all(
			"Duty Certification Track Module", filters={"parent": t.name}, pluck="module", order_by="idx asc"
		)
		assignable = [
			m for m in mods
			if frappe.db.get_value("Duty Training Module", m, "audience") in ("Consultant", "Both")
		]
		if assignable:
			out.append(
				{
					"name": t.name,
					"title": t.title,
					"product": t.product,
					"audience": t.audience,
					"module_count": len(assignable),
				}
			)
	return out


@frappe.whitelist()
def training_assign_track(track, user):
	"""Assign every module of a consultant track to a staff member at once.
	Existing assignments are kept, not duplicated; one notification total."""
	_staff_only()
	if frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("Consultant training is for staff accounts."))
	t = frappe.db.get_value(
		"Duty Certification Track", track, ["title", "audience", "active"], as_dict=True
	)
	if not t or not cint(t.active):
		frappe.throw(_("Not found."))
	mods = frappe.get_all(
		"Duty Certification Track Module", filters={"parent": track}, pluck="module", order_by="idx asc"
	)
	created, existing = 0, 0
	for m in mods:
		aud = frappe.db.get_value("Duty Training Module", m, "audience")
		if aud not in ("Consultant", "Both"):
			continue
		if frappe.db.exists(
			"Duty Training Record", {"module": m, "trainee": user, "room": ["is", "not set"]}
		):
			existing += 1
			continue
		frappe.get_doc(
			{
				"doctype": "Duty Training Record",
				"module": m,
				"trainee": user,
				"trainee_name": frappe.utils.get_fullname(user),
				"status": "Assigned",
				"trained_by": frappe.session.user,
			}
		).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	if created:
		try:
			from duty_board.api import _notify_user

			_notify_user(
				user,
				_("🎓 New training · Xlevel"),
				_("{0} — {1} course(s) assigned").format(t.title, created),
			)
		except Exception:
			pass
	return {"created": created, "existing": existing, "records": my_training()}


def _my_staff_record(module):
	rec = frappe.db.get_value(
		"Duty Training Record",
		{"module": module, "trainee": frappe.session.user, "room": ["is", "not set"]},
		["name", "status"],
		as_dict=True,
	)
	if not rec:
		frappe.throw(_("This course is not assigned to you."), frappe.PermissionError)
	return rec


@frappe.whitelist()
def my_training():
	_staff_only()
	user = frappe.session.user
	rows = frappe.get_all(
		"Duty Training Record",
		filters={"trainee": user, "room": ["is", "not set"]},
		fields=["name", "module", "status", "completed_on"],
		order_by="creation asc",
	)
	mods = {
		m.name: m
		for m in frappe.get_all("Duty Training Module", fields=["name", "title", "product", "sort_order"])
	}
	modules = [r.module for r in rows]
	lesson_counts, done_counts = {}, {}
	if modules:
		for l in frappe.get_all(
			"Duty Lesson", filters={"module": ["in", modules]}, fields=["module"]
		):
			lesson_counts[l.module] = lesson_counts.get(l.module, 0) + 1
		for p in frappe.get_all(
			"Duty Lesson Progress",
			filters={"user": user, "module": ["in", modules], "completed_at": ["is", "set"]},
			fields=["module"],
		):
			done_counts[p.module] = done_counts.get(p.module, 0) + 1
	for r in rows:
		m = mods.get(r.module)
		r.module_title = m.title if m else r.module
		r.product = m.product if m else None
		r.completed_on = str(r.completed_on) if r.completed_on else None
		r.lessons_total = lesson_counts.get(r.module, 0)
		r.lessons_done = done_counts.get(r.module, 0)
	rows.sort(key=lambda r: (mods[r.module].sort_order or 999) if r.module in mods else 999)
	return rows


@frappe.whitelist()
def my_course(record):
	_staff_only()
	rec = frappe.db.get_value(
		"Duty Training Record", record, ["module", "trainee", "room"], as_dict=True
	)
	if not rec or rec.trainee != frappe.session.user or rec.room:
		frappe.throw(_("Not found."), frappe.PermissionError)
	mod = frappe.db.get_value(
		"Duty Training Module", rec.module, ["title", "product", "description"], as_dict=True
	)
	lessons = frappe.get_all(
		"Duty Lesson",
		filters={"module": rec.module},
		fields=["name", "title", "est_minutes"],
		order_by="sort_order asc, creation asc",
	)
	done = {
		p.lesson
		for p in frappe.get_all(
			"Duty Lesson Progress",
			filters={"user": frappe.session.user, "module": rec.module, "completed_at": ["is", "set"]},
			fields=["lesson"],
		)
	}
	return {
		"record": record,
		"title": mod.title,
		"product": mod.product,
		"description": mod.description,
		"status": frappe.db.get_value("Duty Training Record", record, "status"),
		"quiz": _quiz_state(rec.module, frappe.session.user),
		"lessons": [
			{"name": l.name, "title": l.title, "est_minutes": l.est_minutes or 5, "done": l.name in done}
			for l in lessons
		],
	}


@frappe.whitelist()
def my_lesson(lesson):
	_staff_only()
	l = frappe.db.get_value(
		"Duty Lesson", lesson, ["module", "title", "content", "est_minutes"], as_dict=True
	)
	if not l:
		frappe.throw(_("Not found."), frappe.PermissionError)
	rec = _my_staff_record(l.module)
	user = frappe.session.user
	prog = frappe.db.get_value(
		"Duty Lesson Progress", {"user": user, "lesson": lesson},
		["name", "seconds", "completed_at"], as_dict=True,
	)
	if not prog:
		frappe.get_doc(
			{
				"doctype": "Duty Lesson Progress",
				"user": user,
				"lesson": lesson,
				"module": l.module,
				"opened_at": now_datetime(),
				"seconds": 0,
			}
		).insert(ignore_permissions=True)
		prog = frappe._dict(seconds=0, completed_at=None)
	if rec.status == "Assigned":
		frappe.db.set_value("Duty Training Record", rec.name, "status", "Reading", update_modified=False)
	frappe.db.commit()
	return {
		"title": l.title,
		"html": frappe.utils.sanitize_html(l.content or ""),
		"est_minutes": l.est_minutes or 5,
		"seconds": prog.seconds or 0,
		"done": bool(prog.completed_at),
	}


@frappe.whitelist()
def my_lesson_beat(lesson, secs):
	_staff_only()
	module = frappe.db.get_value("Duty Lesson", lesson, "module")
	if not module:
		frappe.throw(_("Not found."), frappe.PermissionError)
	_my_staff_record(module)
	secs = max(0, min(40, cint(secs)))
	name = frappe.db.get_value(
		"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson}, "name"
	)
	if name and secs:
		frappe.db.sql(
			"update `tabDuty Lesson Progress` set seconds = seconds + %s where name = %s",
			(secs, name),
		)
		frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def my_lesson_done(lesson):
	_staff_only()
	l = frappe.db.get_value("Duty Lesson", lesson, ["module", "est_minutes"], as_dict=True)
	if not l:
		frappe.throw(_("Not found."), frappe.PermissionError)
	rec = _my_staff_record(l.module)
	prog = frappe.db.get_value(
		"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson},
		["name", "seconds", "completed_at"], as_dict=True,
	)
	if not prog:
		frappe.throw(_("Open the lesson first."))
	if not prog.completed_at:
		frappe.db.set_value(
			"Duty Lesson Progress", prog.name, "completed_at", now_datetime(), update_modified=False
		)
		frappe.db.commit()
	return my_course(rec.name)


# ---------------- academy: assessment engine ----------------

QUIZ_SIZE = 10


def _quiz_state(module, user):
	attempts = frappe.get_all(
		"Duty Quiz Attempt",
		filters={"user": user, "module": module, "finished_at": ["is", "set"]},
		fields=["score", "passed"],
	)
	return {
		"attempts": len(attempts),
		"best": max((a.score for a in attempts), default=0),
		"passed": any(a.passed for a in attempts),
		"bank": frappe.db.count("Duty Quiz Question", {"module": module, "active": 1}),
	}


def _all_lessons_read(module, user):
	total = frappe.db.count("Duty Lesson", {"module": module})
	if not total:
		return False, total, 0
	done = frappe.db.count(
		"Duty Lesson Progress",
		{"user": user, "module": module, "completed_at": ["is", "set"]},
	)
	return done >= total, total, done


def _quiz_start(rec_name, module):
	import random

	user = frappe.session.user
	ok, total, done = _all_lessons_read(module, user)
	if not ok:
		frappe.throw(_("Finish reading first — {0} of {1} lessons read.").format(done, total))
	bank = frappe.get_all(
		"Duty Quiz Question",
		filters={"module": module, "active": 1},
		fields=["name", "question", "opt_a", "opt_b", "opt_c", "opt_d"],
	)
	if len(bank) < QUIZ_SIZE:
		frappe.throw(_("The test for this course is still being prepared."))
	picked = random.sample(bank, QUIZ_SIZE)
	served, out = [], []
	for q in picked:
		order = [0, 1, 2, 3]
		random.shuffle(order)
		opts = [q.opt_a, q.opt_b, q.opt_c, q.opt_d]
		served.append({"q": q.name, "order": order})
		out.append({"name": q.name, "question": q.question, "options": [opts[i] for i in order]})
	att = frappe.get_doc(
		{
			"doctype": "Duty Quiz Attempt",
			"user": user,
			"module": module,
			"record": rec_name,
			"started_at": now_datetime(),
			"served": json.dumps(served),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"attempt": att.name, "questions": out, "size": QUIZ_SIZE}


def _quiz_submit(attempt, answers, rec):
	att = frappe.get_doc("Duty Quiz Attempt", attempt)
	if att.user != frappe.session.user or att.module != rec.module:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if att.finished_at:
		frappe.throw(_("This attempt is already submitted."))
	if isinstance(answers, str):
		answers = json.loads(answers)
	served = json.loads(att.served or "[]")
	correct_map = {
		q.name: "ABCD".index(q.correct)
		for q in frappe.get_all(
			"Duty Quiz Question",
			filters={"name": ["in", [s["q"] for s in served]]},
			fields=["name", "correct"],
		)
	}
	score_n, wrong = 0, []
	for s in served:
		chosen = answers.get(s["q"])
		if chosen is None:
			chosen = -1
		chosen = cint(chosen)
		real = s["order"][chosen] if 0 <= chosen < 4 else -1
		if real == correct_map.get(s["q"]):
			score_n += 1
		else:
			wrong.append(frappe.db.get_value("Duty Quiz Question", s["q"], "question"))
	score = round(score_n * 100 / len(served))
	pass_mark = cint(frappe.db.get_value("Duty Training Module", rec.module, "pass_mark")) or 70
	passed = score >= pass_mark
	att.db_set(
		{
			"finished_at": now_datetime(),
			"score": score,
			"passed": 1 if passed else 0,
			"answers": json.dumps(answers),
		},
		update_modified=False,
	)
	frappe.db.commit()
	newly_certified = False
	if passed and rec.status != "Completed":
		_award_module_completion(rec)
		newly_certified = True
	state = _quiz_state(rec.module, frappe.session.user)
	return {
		"score": score,
		"passed": passed,
		"pass_mark": pass_mark,
		"wrong": wrong,
		"attempts": state["attempts"],
		"best": state["best"],
		"newly_certified": newly_certified,
	}


@frappe.whitelist()
def my_quiz_start(record):
	_staff_only()
	rec = frappe.db.get_value(
		"Duty Training Record", record, ["name", "module", "trainee", "room"], as_dict=True
	)
	if not rec or rec.trainee != frappe.session.user or rec.room:
		frappe.throw(_("Not found."), frappe.PermissionError)
	return _quiz_start(rec.name, rec.module)


@frappe.whitelist()
def my_quiz_submit(attempt, answers):
	_staff_only()
	att_rec = frappe.db.get_value("Duty Quiz Attempt", attempt, "record")
	rec = frappe.get_doc("Duty Training Record", att_rec)
	if rec.trainee != frappe.session.user or rec.room:
		frappe.throw(_("Not found."), frappe.PermissionError)
	return _quiz_submit(attempt, answers, rec)


@frappe.whitelist()
def client_quiz_start(record):
	room = _client_room()
	rec = frappe.db.get_value(
		"Duty Training Record", record, ["name", "module", "trainee", "room"], as_dict=True
	)
	if not rec or rec.trainee != frappe.session.user or rec.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	return _quiz_start(rec.name, rec.module)


@frappe.whitelist()
def client_quiz_submit(attempt, answers):
	room = _client_room()
	att_rec = frappe.db.get_value("Duty Quiz Attempt", attempt, "record")
	rec = frappe.get_doc("Duty Training Record", att_rec)
	if rec.trainee != frappe.session.user or rec.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	return _quiz_submit(attempt, answers, rec)


# ---------------- certification: tracks, registry, product-branded certs ----------------


def _track_certificate_html(cert):
	verify = f"{frappe.utils.get_url()}/verify?serial={cert.serial}"
	return f"""
<html><head><style>
	@page {{ size: A4 landscape; margin: 0; }}
	body {{ font-family: Helvetica, Arial, sans-serif; margin: 0; color: #16211F; }}
	.cert {{ padding: 60px 80px; height: 100%; box-sizing: border-box;
		border: 14px solid #0F5C55; position: relative; }}
	.inner {{ border: 2px solid #B7DFD6; padding: 40px 50px; text-align: center; height: 100%; box-sizing: border-box; }}
	.brand {{ font-size: 34px; font-weight: 800; color: #0F5C55; letter-spacing: 2px; }}
	.certword {{ font-size: 15px; letter-spacing: 6px; color: #51605C; margin: 18px 0 6px; text-transform: uppercase; }}
	.track {{ font-size: 30px; font-weight: 800; margin: 4px 0 22px; }}
	.holder {{ font-size: 38px; font-weight: 700; color: #0C4A43; margin: 8px 0;
		border-bottom: 2px solid #0F5C55; display: inline-block; padding: 0 30px 6px; }}
	.line {{ font-size: 14px; color: #51605C; margin-top: 16px; line-height: 1.7; }}
	.foot {{ position: absolute; bottom: 46px; left: 80px; right: 80px;
		display: flex; justify-content: space-between; font-size: 12px; color: #51605C; }}
	.sig {{ text-align: center; }}
	.sig b {{ display: block; border-top: 1px solid #16211F; padding-top: 6px; font-size: 13px; color: #16211F; }}
</style></head><body><div class="cert"><div class="inner">
	<div class="brand">{frappe.utils.escape_html(cert.product)}</div>
	<div class="certword">Certificate of Proficiency</div>
	<div class="track">{frappe.utils.escape_html(cert.track_title)}</div>
	<div class="line">This certifies that</div>
	<div class="holder">{frappe.utils.escape_html(cert.holder_name)}</div>
	<div class="line">has completed all required courses and passed the qualifying assessments<br>
	{frappe.utils.escape_html(cert.scores or "")}</div>
	<div class="foot">
		<div>Serial: <b>{cert.serial}</b><br>Issued: {frappe.utils.format_date(cert.issued_on, "d MMMM yyyy")}<br>Verify: {verify}</div>
		<div class="sig">Xlevel Retail Systems Ltd<b>Authorised — CloudERP.One Academy</b></div>
	</div>
</div></div></body></html>"""


def _next_serial(prefix):
	year = frappe.utils.today()[:4]
	base = f"{prefix}-{year}-"
	n = frappe.db.count("Duty Certificate", {"serial": ["like", f"{base}%"]}) + 1
	return f"{base}{n:04d}"


def _best_score(user, module):
	rows = frappe.get_all(
		"Duty Quiz Attempt",
		filters={"user": user, "module": module, "passed": 1},
		fields=["score"],
	)
	return max((r.score for r in rows), default=None)


def _evaluate_certifications(user):
	"""Called after any module completion: issue every track this user has
	just fully satisfied. A Valid certificate blocks re-issue; a
	Recertification Required one does not (the new pass supersedes it)."""
	completed = {
		r.module
		for r in frappe.get_all(
			"Duty Training Record",
			filters={"trainee": user, "status": "Completed"},
			fields=["module"],
		)
	}
	if not completed:
		return
	for track in frappe.get_all(
		"Duty Certification Track", filters={"active": 1}, fields=["name"]
	):
		t = frappe.get_doc("Duty Certification Track", track.name)
		mods = [m.module for m in t.modules]
		if not mods or not set(mods).issubset(completed):
			continue
		if frappe.db.exists("Duty Certificate", {"user": user, "track": t.name, "status": "Valid"}):
			continue
		_issue_certificate(user, t)


def _issue_certificate(user, track):
	holder = frappe.utils.get_fullname(user)
	scores = []
	for m in track.modules:
		title = frappe.db.get_value("Duty Training Module", m.module, "title")
		s = _best_score(user, m.module)
		scores.append(f"{title}: {s}%" if s is not None else f"{title}: instructor certified")
	cert = frappe.get_doc(
		{
			"doctype": "Duty Certificate",
			"serial": _next_serial(track.serial_prefix),
			"user": user,
			"holder_name": holder,
			"track": track.name,
			"track_title": track.title,
			"product": track.product,
			"issued_on": today(),
			"scores": " · ".join(scores),
			"status": "Valid",
		}
	).insert(ignore_permissions=True)
	pdf = get_pdf(_track_certificate_html(cert))
	fname = f"{cert.serial}_{holder.replace(' ', '_')}.pdf"
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"content": pdf,
			"is_private": 1,
			"attached_to_doctype": "Duty Certificate",
			"attached_to_name": cert.name,
		}
	).insert(ignore_permissions=True)
	cert.db_set("file_url", f.file_url, update_modified=False)
	# supersede any recert-flagged predecessor
	for old in frappe.get_all(
		"Duty Certificate",
		filters={"user": user, "track": track.name, "status": "Recertification Required"},
		pluck="name",
	):
		frappe.db.set_value("Duty Certificate", old, {"status": "Revoked", "status_note": f"Superseded by {cert.serial}"}, update_modified=False)
	frappe.db.commit()
	try:
		frappe.sendmail(
			recipients=[user],
			subject=_("🎓 {0} — {1} awarded").format(track.product, track.title),
			message=f"""<p>Congratulations, {frappe.utils.escape_html(holder)}!</p>
<p>You have earned <b>{frappe.utils.escape_html(track.product)} — {frappe.utils.escape_html(track.title)}</b>,
having completed every required course and passed the qualifying assessments.</p>
<p>Serial: <b>{cert.serial}</b> · Issued {frappe.utils.format_date(cert.issued_on, "d MMMM yyyy")}<br>
Anyone can verify this credential at: {frappe.utils.get_url()}/verify?serial={cert.serial}</p>
<p>Your certificate is attached.</p>
<p>— CloudERP.One Academy · Xlevel Retail Systems Ltd</p>""",
			attachments=[{"fname": fname, "fcontent": pdf}],
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board certificate email")
	try:
		from duty_board.api import _notify_user

		_notify_user(user, _("🎓 Certificate awarded"), f"{track.product} — {track.title}")
	except Exception:
		pass
	return cert


def _certs_for(user):
	rows = frappe.get_all(
		"Duty Certificate",
		filters={"user": user, "status": ["!=", "Revoked"]},
		fields=["name", "serial", "track_title", "product", "issued_on", "status"],
		order_by="issued_on desc",
	)
	for r in rows:
		r.issued_on = str(r.issued_on) if r.issued_on else None
	return rows


@frappe.whitelist()
def my_certificates():
	_staff_only()
	return _certs_for(frappe.session.user)


@frappe.whitelist()
def client_get_certificates():
	_client_room()
	return _certs_for(frappe.session.user)


def _serve_certificate(serial):
	cert = frappe.db.get_value(
		"Duty Certificate", {"serial": serial}, ["user", "file_url"], as_dict=True
	)
	if not cert or cert.user != frappe.session.user or not cert.file_url:
		frappe.throw(_("Not found."), frappe.PermissionError)
	fname = frappe.db.get_value("File", {"file_url": cert.file_url})
	if not fname:
		frappe.throw(_("File missing."))
	return _serve_file(frappe.get_doc("File", fname), f"{serial}.pdf")


@frappe.whitelist()
def my_certificate_file(serial):
	_staff_only()
	_serve_certificate(serial)


@frappe.whitelist()
def client_certificate_file(serial):
	_client_room()
	_serve_certificate(serial)


# ---------------- certification: product inheritance & track pursuit ----------------


def _room_products(room):
	return {p.strip().lower() for p in (room.products or "").replace("\n", ",").split(",") if p.strip()}


@frappe.whitelist()
def product_options():
	"""The pickable product names — the Duty Product master."""
	_staff_only()
	return frappe.get_all(
		"Duty Product", filters={"active": 1}, order_by="sort_order asc, title asc", pluck="name"
	)


@frappe.whitelist()
def room_set_products(name, products):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	room.db_set("products", (products or "").strip()[:300] or None, update_modified=False)
	frappe.db.commit()
	return get_room(name)


def _tracks_for_room(room, user):
	prods = _room_products(room)
	if not prods:
		return []
	tracks = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},
		fields=["name", "title", "product", "description"],
		order_by="product asc, title asc",
	)
	tracks = [t for t in tracks if (t.product or "").strip().lower() in prods]
	out = []
	for t in tracks:
		mods = frappe.get_all(
			"Duty Certification Track Module",
			filters={"parent": t.name},
			fields=["module"],
			order_by="idx asc",
		)
		mod_names = [m.module for m in mods]
		if not mod_names:
			continue
		titles = {
			m.name: m.title
			for m in frappe.get_all(
				"Duty Training Module", filters={"name": ["in", mod_names]}, fields=["name", "title"]
			)
		}
		recs = {
			r.module: r.status
			for r in frappe.get_all(
				"Duty Training Record",
				filters={"room": room.name, "trainee": user, "module": ["in", mod_names]},
				fields=["module", "status"],
			)
		}
		done = sum(1 for m in mod_names if recs.get(m) == "Completed")
		out.append(
			{
				"name": t.name,
				"title": t.title,
				"product": t.product,
				"description": t.description,
				"modules": [titles.get(m, m) for m in mod_names],
				"total": len(mod_names),
				"pursuing": all(m in recs for m in mod_names),
				"done": done,
				"certified": bool(
					frappe.db.exists("Duty Certificate", {"user": user, "track": t.name, "status": "Valid"})
				),
			}
		)
	return out


@frappe.whitelist()
def client_get_tracks():
	room = _client_room()
	return _tracks_for_room(room, frappe.session.user)


@frappe.whitelist()
def client_pursue_track(track):
	room = _client_room()
	user = frappe.session.user
	t = frappe.db.get_value(
		"Duty Certification Track", track, ["title", "product", "audience", "active"], as_dict=True
	)
	if not t or not cint(t.active) or t.audience != "Client":
		frappe.throw(_("Not found."), frappe.PermissionError)
	if (t.product or "").strip().lower() not in _room_products(room):
		frappe.throw(_("This track is not part of your subscription."), frappe.PermissionError)
	mods = frappe.get_all(
		"Duty Certification Track Module", filters={"parent": track}, pluck="module"
	)
	created = 0
	for m in mods:
		if frappe.db.exists("Duty Training Record", {"room": room.name, "trainee": user, "module": m}):
			continue
		frappe.get_doc(
			{
				"doctype": "Duty Training Record",
				"room": room.name,
				"module": m,
				"trainee": user,
				"trainee_name": frappe.utils.get_fullname(user),
				"status": "Assigned",
			}
		).insert(ignore_permissions=True)
		created += 1
	frappe.db.commit()
	if created:
		_post(
			room,
			_("🎓 {0} is now pursuing the {1} — {2} track.").format(
				frappe.utils.get_fullname(user), t.product, t.title
			),
		)
	return _tracks_for_room(room, user)


@frappe.whitelist()
def client_get_deliverables():
	from duty_board.accounting import client_get_deliverables as f

	return f()


@frappe.whitelist()
def client_ack_deliverable(name):
	from duty_board.accounting import client_ack_deliverable as f

	return f(name)


@frappe.whitelist()
def client_get_followups():
	from duty_board.accounting import client_get_followups as f

	return f()


@frappe.whitelist()
def client_answer_query(name, answer):
	from duty_board.accounting import client_answer_query as f

	return f(name, answer)


@frappe.whitelist()
def client_fulfill_request(name, attachment_url=None, attachment_name=None):
	from duty_board.accounting import client_fulfill_request as f

	return f(name, attachment_url, attachment_name)


# ---------------- rca: the post-incident report ----------------


def _rca_html(issue, rca, timeline):
	sec = lambda t, b: (
		f'<h2>{t}</h2><p>{frappe.utils.escape_html(b).replace(chr(10), "<br>")}</p>' if b else ""
	)
	tl = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in timeline if v)
	return f"""<html><head><meta charset="utf-8"><style>
	body {{ font-family: Helvetica, Arial, sans-serif; color: #1f2937; margin: 34px 42px; }}
	.head {{ border-bottom: 4px solid #0F5C55; padding-bottom: 12px; margin-bottom: 18px; }}
	.head h1 {{ color: #0F5C55; margin: 0 0 4px; font-size: 22px; }}
	.head p {{ margin: 0; color: #6b7280; font-size: 12px; }}
	h2 {{ color: #0E7490; font-size: 14px; margin: 20px 0 6px; }}
	p {{ font-size: 13px; line-height: 1.6; margin: 0 0 8px; }}
	table {{ border-collapse: collapse; font-size: 12px; margin-top: 6px; }}
	td {{ border: 1px solid #e5e7eb; padding: 5px 12px; }}
	td:first-child {{ background: #f0fdfa; font-weight: bold; color: #0F5C55; }}
	.foot {{ margin-top: 30px; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 11px; color: #6b7280; }}
	</style></head><body>
	<div class="head">
		<h1>Incident Report &amp; Root Cause Analysis</h1>
		<p>{frappe.utils.escape_html(issue.title)} · {frappe.utils.escape_html(issue.customer)} · Severity: {frappe.utils.escape_html(issue.severity or "")}</p>
	</div>
	<h2>Timeline</h2><table>{tl}</table>
	{sec("What happened", rca.get("what_happened"))}
	{sec("Root cause", rca.get("root_cause"))}
	{sec("How we resolved it", rca.get("resolution_action"))}
	{sec("What we changed so it cannot recur", rca.get("prevention"))}
	<div class="foot">Prepared by Xlevel Retail Systems · This report is part of our commitment to transparency after every serious incident.</div>
	</body></html>"""


@frappe.whitelist()
def rca_get(issue):
	_staff_only()
	existing = frappe.db.get_value(
		"Duty RCA",
		{"issue": issue},
		["name", "what_happened", "root_cause", "resolution_action", "prevention"],
		as_dict=True,
	)
	return existing or {}


@frappe.whitelist()
def rca_publish(issue, what_happened=None, root_cause=None, resolution_action=None, prevention=None):
	_staff_only()
	doc = frappe.get_doc("Duty Issue", issue)
	row = frappe._dict(
		customer=doc.customer, source_type=doc.source_type, source=doc.source
	)
	home = _issue_home_room(row)
	if not home:
		frappe.throw(_("This customer has no active room to publish to."))
	room = frappe.get_doc("Client Room", home.name)
	rca = {
		"what_happened": (what_happened or "").strip(),
		"root_cause": (root_cause or "").strip(),
		"resolution_action": (resolution_action or "").strip(),
		"prevention": (prevention or "").strip(),
	}
	fmt = lambda d: frappe.utils.format_datetime(d, "d MMM yyyy HH:mm") if d else None
	timeline = [
		(_("Reported"), fmt(doc.creation)),
		(_("Work started"), fmt(doc.work_started_at)),
		(_("Resolved"), fmt(doc.resolved_at)),
	]
	pdf = get_pdf(_rca_html(doc, rca, timeline))
	fname = f"RCA_{doc.name}.pdf"
	f = frappe.get_doc(
		{"doctype": "File", "file_name": fname, "content": pdf, "is_private": 1}
	).insert(ignore_permissions=True)
	existing = frappe.db.get_value("Duty RCA", {"issue": issue})
	if existing:
		r = frappe.get_doc("Duty RCA", existing)
		shelf_name = r.shelf_doc
		if shelf_name and frappe.db.exists("Client Shelf Doc", shelf_name):
			frappe.db.set_value(
				"Client Shelf Doc", shelf_name,
				{"file_url": f.file_url, "file_name": fname},
				update_modified=False,
			)
		else:
			shelf_name = None
	else:
		r = frappe.get_doc({"doctype": "Duty RCA", "issue": issue})
		shelf_name = None
	if not shelf_name:
		shelf = frappe.get_doc(
			{
				"doctype": "Client Shelf Doc",
				"room": room.name,
				"title": _("Incident Report — {0}").format(doc.title[:80]),
				"category": _("RCA Report"),
				"file_url": f.file_url,
				"file_name": fname,
				"active": 1,
			}
		).insert(ignore_permissions=True)
		shelf_name = shelf.name
	r.update(rca)
	r.room = room.name
	r.published_on = now_datetime()
	r.shelf_doc = shelf_name
	r.save(ignore_permissions=True)
	frappe.db.commit()
	if not existing:
		_post(room, _("📋 Incident report published: “{0}” — the full root-cause analysis is on your shelf.").format(doc.title))
		_push_room_clients(room, _("📋 Incident report · Xlevel"), doc.title[:120])
	return {"ok": True}


# ---------------- meetings ----------------

MEETING_SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
MEETING_DAY_CAP = 2


def _staff_hour_load(user, date):
	"""(busy_hours set, meeting_count) — pending holds count as busy and toward the cap."""
	busy = set()
	count = 0
	for m in frappe.db.sql(
		"""select dm.start_time from `tabDuty Meeting` dm
		   join `tabDuty Meeting Attendee` a on a.parent = dm.name
		   where a.user = %s and dm.meeting_date = %s
		     and dm.status in ('Pending', 'Confirmed')""",
		(user, date),
		as_dict=True,
	):
		busy.add(str(m.start_time)[:2])
		count += 1
	for t in frappe.get_all(
		"Daily Todo",
		filters={
			"user": user,
			"date": date,
			"status": "Open",
			"due_time": ["is", "set"],
		},
		fields=["due_time"],
	):
		busy.add(str(t.due_time)[:2])
	return busy, count


def _meeting_slots(staff_list, date):
	d = getdate(date)
	if d < getdate(frappe.utils.today()):
		return []
	if d.weekday() >= 5:  # Sat/Sun — the banner's promise holds
		return []
	from duty_board.leave import holidays, is_on_leave
	if d in holidays():
		return []  # public holiday — nobody is bookable
	for u in staff_list:
		if is_on_leave(u, d):
			return []  # a requested attendee is on leave that day
	blocked = set()
	for u in staff_list:
		busy, count = _staff_hour_load(u, date)
		if count >= MEETING_DAY_CAP:
			return []  # someone is fully booked that day
		blocked |= busy
	now = frappe.utils.now_datetime()
	out = []
	for s in MEETING_SLOTS:
		if s[:2] in blocked:
			continue
		if d == getdate(frappe.utils.today()) and int(s[:2]) <= now.hour:
			continue
		out.append(s)
	return out


def _valid_staff_ids(ids):
	out = []
	for u in ids:
		if (
			frappe.db.get_value("User", u, "user_type") == "System User"
			and frappe.db.get_value("User", u, "enabled")
			and u != "Administrator"
		):
			out.append(u)
	return out


def _meeting_rows(room, include_past=False):
	filters = {"room": room.name, "status": ["in", ["Pending", "Confirmed"]]}
	if not include_past:
		filters["meeting_date"] = [">=", frappe.utils.today()]
	rows = frappe.get_all(
		"Duty Meeting",
		filters=filters,
		fields=["name", "topic", "meeting_date", "start_time", "status", "requested_by"],
		order_by="meeting_date asc, start_time asc",
		limit=30,
	)
	for r in rows:
		r.meeting_date = str(r.meeting_date)
		r.start_time = str(r.start_time)[:5]
		r.requested_first = (
			frappe.utils.get_fullname(r.requested_by).split(" ")[0]
			if r.requested_by
			else None
		)
		r.staff = [
			frappe.utils.get_fullname(a.user).split(" ")[0]
			for a in frappe.get_all(
				"Duty Meeting Attendee",
				filters={"parent": r.name},
				fields=["user"],
			)
		]
	return rows


def _bookable_staff(room):
	try:
		chosen = json.loads(room.meeting_staff or "[]")
	except Exception:
		chosen = []
	out = []
	for u in frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
	):
		if u.name == "Administrator" or not u.full_name:
			continue
		if chosen and u.name not in chosen:
			continue
		out.append({"id": u.name, "first": u.full_name.split(" ")[0], "full": u.full_name})
	return out


@frappe.whitelist()
def client_meeting_staff():
	room = _client_room()
	return _bookable_staff(room)


@frappe.whitelist()
def set_meeting_staff(name, users):
	_staff_only()
	ids = _valid_staff_ids(frappe.parse_json(users) or [])
	frappe.db.set_value(
		"Client Room", name, "meeting_staff", json.dumps(ids), update_modified=False
	)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def client_meeting_slots(date, staff):
	_client_room()
	ids = _valid_staff_ids(frappe.parse_json(staff) or [])
	if not ids:
		frappe.throw(_("Pick at least one team member."))
	return {"slots": _meeting_slots(ids, date)}


def _meeting_caps_check(room, ids, date):
	"""Customer: 1 request/day, 3/week. Staff: 2 client meetings/day across all customers."""
	from datetime import timedelta

	today_d = getdate(today())
	rooms = frappe.get_all(
		"Client Room", filters={"customer": room.customer}, pluck="name"
	)
	target_d = getdate(date) if date else today_d
	day_n = frappe.db.count(
		"Duty Meeting",
		{
			"room": ["in", rooms],
			"meeting_date": target_d,
			"status": ["!=", "Cancelled"],
		},
	)
	if day_n >= 1:
		frappe.throw(
			_("There's already a meeting scheduled for {0} — one meeting per day keeps our calendar fair. Pick another day.").format(
				frappe.utils.formatdate(target_d, "d MMM")
			)
		)
	week_start = today_d - timedelta(days=today_d.weekday())
	week_n = frappe.db.count(
		"Duty Meeting", {"room": ["in", rooms], "creation": [">=", str(week_start)]}
	)
	if week_n >= 3:
		frappe.throw(
			_("You've reached this week's limit of three meeting requests — for anything urgent, message us right here.")
		)
	for u in ids:
		busy = frappe.db.sql(
			"""select count(*) from `tabDuty Meeting` m
			join `tabDuty Meeting Attendee` a on a.parent = m.name
			where a.user = %s and m.meeting_date = %s
			and m.status in ('Pending', 'Confirmed')""",
			(u, date),
		)[0][0]
		if busy >= 2:
			first = frappe.utils.get_fullname(u).split(" ")[0]
			frappe.throw(
				_("{0} already has two client meetings on that day — choose another day or a different team member.").format(
					first
				)
			)


@frappe.whitelist()
def client_request_meeting(date, time, staff, topic):
	room = _client_room()
	topic = (topic or "").strip()[:120]
	if not topic:
		frappe.throw(_("What is the meeting about?"))
	ids = _valid_staff_ids(frappe.parse_json(staff) or [])
	allowed = {s["id"] for s in _bookable_staff(room)}
	ids = [u for u in ids if u in allowed]
	if not ids:
		frappe.throw(_("Pick at least one team member."))
	if frappe.db.count(
		"Duty Meeting", {"room": room.name, "status": "Pending"}
	) >= 3:
		frappe.throw(_("You have several meetings awaiting confirmation already."))
	_meeting_caps_check(room, ids, date)
	if time not in _meeting_slots(ids, date):
		frappe.throw(_("That slot just became unavailable — pick another."))
	doc = frappe.get_doc(
		{
			"doctype": "Duty Meeting",
			"room": room.name,
			"customer": room.customer,
			"topic": topic,
			"meeting_date": date,
			"start_time": time + ":00",
			"duration_mins": 60,
			"status": "Pending",
			"requested_by": frappe.session.user,
			"attendees": [{"user": u} for u in ids],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	firsts = ", ".join(frappe.utils.get_fullname(u).split(" ")[0] for u in ids)
	_post(
		room,
		_("📅 Meeting requested: “{0}” — {1} {2} with {3} · awaiting confirmation").format(
			topic, frappe.utils.formatdate(date, "d MMM"), time, firsts
		),
	)
	try:
		from duty_board.api import _notify_user

		who = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		for u in ids:
			_notify_user(
				u,
				_("📅 Meeting request · {0}").format(room.customer),
				f"{topic} — {date} {time} ({who})",
			)
	except Exception:
		pass
	return client_get_meetings()


@frappe.whitelist()
def client_get_meetings():
	room = _client_room()
	return _meeting_rows(room)


@frappe.whitelist()
def client_cancel_meeting(id):
	room = _client_room()
	doc = frappe.get_doc("Duty Meeting", id)
	if doc.room != room.name:
		frappe.throw(_("Not found."), frappe.PermissionError)
	if doc.status not in ("Pending", "Confirmed"):
		frappe.throw(_("Already settled."))
	_settle_meeting(doc, "Cancelled")
	_post(room, _("📅 Meeting cancelled by client: “{0}”").format(doc.topic))
	frappe.db.commit()
	return client_get_meetings()


def _settle_meeting(doc, status):
	doc.db_set("status", status, update_modified=False)
	if doc.created_todos:
		try:
			for t in json.loads(doc.created_todos):
				if frappe.db.exists("Daily Todo", t):
					frappe.delete_doc("Daily Todo", t, ignore_permissions=True, force=True)
		except Exception:
			pass


def _meeting_ics(doc, method="REQUEST"):
	"""RFC 5545 invite for a Duty Meeting. Gmail/Outlook auto-surface it;
	SEQUENCE bumps on every re-send so updates replace, not duplicate."""
	from datetime import timedelta

	from frappe.utils import get_datetime, get_url

	seq = cint(doc.ics_seq or 0)
	start = get_datetime(f"{doc.meeting_date} {doc.start_time}")
	end = start + timedelta(minutes=cint(doc.duration_mins) or 30)
	fmt = "%Y%m%dT%H%M%S"
	organizer = frappe.db.get_single_value("Duty Settings", "meeting_organizer_email") or "no-reply@xlevelretail.com"
	attendees = []
	for a in doc.attendees:
		full = frappe.utils.get_fullname(a.user)
		attendees.append(f"ATTENDEE;CN={full};RSVP=TRUE:mailto:{a.user}")
	desc = _("Meeting on your Xlevel client workspace — {0}").format(get_url("/portal"))
	lines = [
		"BEGIN:VCALENDAR",
		"PRODID:-//Xlevel Retail Systems//Duty Board//EN",
		"VERSION:2.0",
		f"METHOD:{method}",
		"BEGIN:VEVENT",
		f"UID:{doc.name}@xlevel.clouderp.one",
		f"SEQUENCE:{seq}",
		f"DTSTAMP:{frappe.utils.now_datetime().strftime(fmt)}",
		f"DTSTART;TZID=Africa/Lagos:{start.strftime(fmt)}",
		f"DTEND;TZID=Africa/Lagos:{end.strftime(fmt)}",
		f"SUMMARY:{(doc.topic or 'Meeting').replace(chr(10), ' ')[:200]}" + (" (CANCELLED)" if method == "CANCEL" else ""),
		f"DESCRIPTION:{desc}",
		f"ORGANIZER;CN=Xlevel Retail Systems:mailto:{organizer}",
		f"STATUS:{'CANCELLED' if method == 'CANCEL' else 'CONFIRMED'}",
	] + attendees + [
		"BEGIN:VALARM",
		"TRIGGER:-PT30M",
		"ACTION:DISPLAY",
		f"DESCRIPTION:{(doc.topic or 'Meeting')[:100]}",
		"END:VALARM",
		"END:VEVENT",
		"END:VCALENDAR",
	]
	return "\r\n".join(lines)


def _send_meeting_invite(doc, method="REQUEST"):
	"""Email the .ics to every attendee so the meeting lands on their own
	calendar (Google, Outlook, Apple). Never raises — invites are a
	courtesy layer over the booking, not part of it."""
	try:
		recipients = [a.user for a in doc.attendees if a.user and "@" in a.user]
		if doc.room:
			recipients += [
				m.user
				for m in frappe.get_all(
					"Client Room Member", filters={"room": doc.room, "active": 1}, fields=["user"]
				)
				if "@" in (m.user or "")
			]
		recipients = list(dict.fromkeys(recipients))
		if not recipients:
			return
		ics = _meeting_ics(doc, method)
		verb = _("cancelled") if method == "CANCEL" else (_("updated") if cint(doc.ics_seq) else _("confirmed"))
		frappe.sendmail(
			recipients=recipients,
			subject=_("📅 {0} — {1} {2}").format(doc.topic or _("Meeting"), doc.meeting_date, str(doc.start_time)[:5]),
			message=_(
				"<p>Your meeting <b>{0}</b> with {1} has been {2}:</p>"
				"<p><b>{3} at {4}</b> ({5} minutes, WAT)</p>"
				"<p>The attached invite adds it to your calendar automatically.</p>"
			).format(
				frappe.utils.escape_html(doc.topic or _("Meeting")),
				frappe.utils.escape_html(doc.customer or "Xlevel"),
				verb, doc.meeting_date, str(doc.start_time)[:5], cint(doc.duration_mins) or 30,
			),
			attachments=[{"fname": "invite.ics", "fcontent": ics.encode()}],
			delayed=False,
		)
		doc.db_set("ics_seq", cint(doc.ics_seq) + 1, update_modified=False)
	except Exception:
		frappe.log_error(frappe.get_traceback()[:2000], "meeting ics invite")


@frappe.whitelist()
def confirm_meeting(id):
	_staff_only()
	doc = frappe.get_doc("Duty Meeting", id)
	if doc.status != "Pending":
		frappe.throw(_("Already settled."))
	attendee_ids = [a.user for a in doc.attendees]
	me = frappe.session.user
	if me not in attendee_ids and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only a requested attendee can confirm."))
	slot = str(doc.start_time)[:5]
	# recheck against everything EXCEPT this meeting's own pending hold
	doc.db_set("status", "Cancelled", update_modified=False)
	if cint(doc.ics_seq):
		doc.reload()
		_send_meeting_invite(doc, "CANCEL")
	ok = slot in _meeting_slots(attendee_ids, str(doc.meeting_date))
	doc.db_set("status", "Pending", update_modified=False)
	if not ok:
		frappe.throw(_("Conflict has appeared — decline and ask the client to rebook."))
	todos = []
	for u in attendee_ids:
		t = frappe.get_doc(
			{
				"doctype": "Daily Todo",
				"user": u,
				"date": doc.meeting_date,
				"description": f"📅 {doc.customer}: {doc.topic}"[:140],
				"status": "Open",
				"due_time": doc.start_time,
				"assigned_by": me if me != u else None,
			}
		).insert(ignore_permissions=True)
		todos.append(t.name)
	doc.db_set("created_todos", json.dumps(todos), update_modified=False)
	doc.db_set("status", "Confirmed", update_modified=False)
	doc.db_set("confirmed_by", me, update_modified=False)
	doc.reload()
	_send_meeting_invite(doc, "REQUEST")
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	firsts = ", ".join(frappe.utils.get_fullname(u).split(" ")[0] for u in attendee_ids)
	_post(
		room,
		_("📅 Confirmed: “{0}” — {1} {2} with {3}").format(
			doc.topic,
			frappe.utils.formatdate(doc.meeting_date, "d MMM"),
			str(doc.start_time)[:5],
			firsts,
		),
	)
	_push_room_clients(
		room,
		_("📅 Meeting confirmed · Xlevel"),
		f"{doc.topic} — {frappe.utils.formatdate(doc.meeting_date, 'd MMM')} {str(doc.start_time)[:5]}",
	)
	return get_room(doc.room)


@frappe.whitelist()
def decline_meeting(id, reason=None):
	_staff_only()
	doc = frappe.get_doc("Duty Meeting", id)
	if doc.status != "Pending":
		frappe.throw(_("Already settled."))
	_settle_meeting(doc, "Declined")
	if reason:
		doc.db_set("decline_reason", reason.strip()[:200], update_modified=False)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	_post(
		room,
		_("📅 “{0}” can't happen then{1} — please pick another slot.").format(
			doc.topic, f" ({reason.strip()[:120]})" if reason else ""
		),
	)
	_push_room_clients(room, _("📅 Please rebook · Xlevel"), doc.topic[:120])
	return get_room(doc.room)


def _statement_review_nudges():
	"""Published statements awaiting review ≥7 days get a gentle client
	nudge, at most once per 7 days per statement."""
	from frappe.utils import add_days, getdate, today

	cutoff = add_days(today(), -7)
	rows = frappe.get_all(
		"Client Document",
		filters={
			"is_financial_statement": 1,
			"published": 1,
			"review_status": "Awaiting Client Review",
			"published_on": ["<=", cutoff],
		},
		fields=["name", "client", "statement_type", "period_month", "period_year", "stmt_nudged_on"],
		limit_page_length=50,
	)
	for r in rows:
		if r.stmt_nudged_on and str(r.stmt_nudged_on) > str(cutoff):
			continue
		room_name = _financial_room(r.client)
		if not room_name:
			continue
		if r.statement_type == "Annual Report":
			label = _("{0} Annual Report").format(r.period_year)
		else:
			label = _("{0} {1} Management Account").format(r.period_month or "", r.period_year).strip()
		try:
			room = frappe.get_doc("Client Room", room_name)
			_post(room, _("📊 Gentle reminder: {0} is awaiting your review — approve it or send feedback from your portal.").format(label))
			_push_room_clients(room, _("📊 Awaiting your review · Xlevel"), label)
			frappe.db.set_value("Client Document", r.name, "stmt_nudged_on", today(), update_modified=False)
			frappe.db.commit()
		except Exception:
			continue


def meeting_reminders():
	try:
		from duty_board.uat import heartbeat

		heartbeat()
	except Exception:
		frappe.log_error(frappe.get_traceback()[:2000], "uat heartbeat")
	try:
		_statement_review_nudges()
	except Exception:
		frappe.log_error(frappe.get_traceback()[:2000], "statement nudges")
	"""Hourly: morning-of and hour-before pushes to the client. Staff already
	ride the todo alert machinery."""
	now = now_datetime()
	today = frappe.utils.today()
	for m in frappe.get_all(
		"Duty Meeting",
		filters={"status": "Confirmed", "meeting_date": today},
		fields=["name", "room", "topic", "start_time", "reminded_morning", "reminded_hour"],
	):
		try:
			if not m.room:
				continue
			room = frappe.get_doc("Client Room", m.room)
		except Exception:
			continue
		slot = str(m.start_time)[:5]
		if not cint(m.reminded_morning) and now.hour >= 7:
			frappe.db.set_value(
				"Duty Meeting", m.name, "reminded_morning", 1, update_modified=False
			)
			_post(room, _("📅 Reminder: today {0} — “{1}”").format(slot, m.topic))
			_push_room_clients(
				room, _("📅 Today {0} · Xlevel").format(slot), m.topic[:120]
			)
		if not cint(m.reminded_hour) and int(str(m.start_time)[:2]) == now.hour + 1:
			frappe.db.set_value(
				"Duty Meeting", m.name, "reminded_hour", 1, update_modified=False
			)
			_push_room_clients(
				room,
				_("📅 In about an hour · Xlevel"),
				f"{m.topic[:100]} — {slot}",
			)
	frappe.db.commit()


MEETING_MINUTES = 60


@frappe.whitelist()
def settle_meeting_outcome(id, outcome, note=None):
	_staff_only()
	if outcome not in ("Held", "Missed"):
		frappe.throw(_("Held or Missed."))
	doc = frappe.get_doc("Duty Meeting", id)
	if doc.status != "Confirmed":
		frappe.throw(_("Only confirmed meetings get an outcome."))
	frappe.db.set_value(
		"Duty Meeting",
		id,
		{"outcome": outcome, "outcome_note": (note or "").strip()[:300] or None},
		update_modified=False,
	)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	slot = str(doc.start_time)[:5]
	if outcome == "Held":
		_post(
			room,
			_("📅 Held ✓ “{0}”{1}").format(
				doc.topic, f" — {note.strip()[:200]}" if note else ""
			),
		)
	else:
		_post(
			room,
			_("📅 “{0}” didn't happen{1} — pick a new slot whenever suits.").format(
				doc.topic, f" ({note.strip()[:150]})" if note else ""
			),
		)
		_push_room_clients(room, _("📅 Let's rebook · Xlevel"), doc.topic[:120])
	return get_room(doc.room)


def _room_member_mentions(room, text):
	low = (text or "").lower()
	if "@" not in low:
		return []
	out = []
	for m in frappe.get_all(
		"Client Room Member", filters={"room": room.name, "active": 1}, fields=["user"]
	):
		full = frappe.utils.get_fullname(m.user) or m.user
		first = full.split(" ")[0].lower()
		if f"@{first}" in low or f"@{m.user.lower()}" in low:
			out.append(m.user)
	return out


def _email_mention(user, room, sender_first, message):
	try:
		frappe.sendmail(
			recipients=[user],
			subject=_("💬 {0} mentioned you — {1} × Xlevel").format(
				sender_first, room.customer
			),
			message=(
				f"<p><b>{frappe.utils.escape_html(sender_first)}</b> mentioned you in your Xlevel room:</p>"
				f"<blockquote style='border-left:3px solid #0F5C55;padding-left:10px;color:#374151'>"
				f"{frappe.utils.escape_html((message or '')[:300])}</blockquote>"
				f"<p><a href='{frappe.utils.get_url()}/portal'>Open your portal</a></p>"
			),
			delayed=True,
		)
	except Exception:
		pass


@frappe.whitelist()
def room_file(msg):
	"""Serve a room attachment to staff or to members of that room only."""
	m = frappe.get_doc("Client Room Message", msg)
	user = frappe.session.user
	utype = frappe.db.get_value("User", user, "user_type")
	from duty_board.permissions import is_consultant

	if utype == "System User" and not is_consultant(user):
		pass
	elif utype in ("System User", "Website User"):
		# portal client OR external consultant: active membership required;
		# internal-note attachments barred (consultant per-room override is
		# a later, deliberate wiring — never a default)
		if m.internal:
			frappe.throw(_("Not permitted."), frappe.PermissionError)
		if not frappe.db.exists(
			"Client Room Member", {"room": m.room, "user": user, "active": 1}
		):
			frappe.throw(_("Not permitted."), frappe.PermissionError)
	else:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if not m.attachment_url:
		frappe.throw(_("No attachment."))
	fname = frappe.db.get_value("File", {"file_url": m.attachment_url})
	if not fname:
		frappe.throw(_("File missing."))
	fdoc = frappe.get_doc("File", fname)
	return _serve_file(fdoc, m.attachment_name or fdoc.file_name)


@frappe.whitelist()
def client_get_timeline():
	room = _client_room()
	from duty_board.timeline import client_timeline

	return client_timeline(room.name)


@frappe.whitelist()
def client_get_uat():
	room = _client_room()
	from duty_board.uat import client_state

	state = client_state(room.name)
	state["can_sign"] = 1 if _client_can_approve(room) else 0
	return state


@frappe.whitelist()
def client_uat_result(name, result, observed=None, evidence_url=None, evidence_name=None):
	room = _client_room()
	from duty_board.uat import client_result

	return client_result(room.name, name, result, observed, evidence_url, evidence_name)


@frappe.whitelist()
def client_uat_sign(note=None):
	room = _client_room()
	if not _client_can_approve(room):
		frappe.throw(_("Only your team administrator can sign off acceptance testing."), frappe.PermissionError)
	from duty_board.uat import client_sign

	return client_sign(room.name, frappe.session.user, note)


@frappe.whitelist()
def client_get_dependencies():
	room = _client_room()
	from duty_board.commercial import client_deps

	return client_deps(room.name)


@frappe.whitelist()
def client_provide_dependency(name, note=None):
	room = _client_room()
	from duty_board.commercial import client_provide

	return client_provide(room.name, name, note)


@frappe.whitelist()
def client_push_ping():
	_client_room()
	from duty_board.push import push_to_user

	push_to_user(
		frappe.session.user,
		"🔔 " + _("Xlevel notifications are on"),
		_("We'll buzz you right here when we reply."),
	)
	return {"ok": True}


@frappe.whitelist()
def client_get_staff():
	"""Names a client may address: their own service team, not the whole
	company roster — room owner, bookkeeper, configured meeting staff, and
	staff who have actually spoken in this room."""
	room = _client_room()
	staff_users = set()
	for field in ("owner_user", "bookkeeper", "meeting_staff"):
		v = room.get(field)
		if v:
			staff_users.update(s.strip() for s in str(v).split(",") if s.strip())
	for owner in frappe.get_all(
		"Client Room Message",
		filters={"room": room.name, "internal": 0},
		pluck="owner",
		distinct=True,
		limit_page_length=0,
	):
		if frappe.db.get_value("User", owner, "user_type") == "System User":
			staff_users.add(owner)
	out = []
	seen = set()
	for su in staff_users:
		if not su or not frappe.db.get_value("User", su, "enabled"):
			continue
		full = frappe.utils.get_fullname(su)
		if not full or full == "Administrator" or full in seen:
			continue
		seen.add(full)
		out.append({"first": full.split(" ")[0], "full": full, "kind": "staff"})
	me = frappe.session.user
	for m in frappe.get_all(
		"Client Room Member", filters={"room": room.name, "active": 1}, fields=["user"]
	):
		if m.user == me:
			continue
		full = frappe.utils.get_fullname(m.user) or m.user
		if "@" in full:
			full = full.split("@")[0]
		first = full.split(" ")[0]
		out.append({"first": first, "full": full, "kind": "colleague"})
	return out


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def submit_join_request(token, full_name, email, phone=None):
	token = (token or "").strip()
	full_name = (full_name or "").strip()[:100]
	email = (email or "").strip().lower()[:120]
	phone = (phone or "").strip()[:30]
	if not token or not full_name or not email or "@" not in email or "." not in email.split("@")[-1]:
		frappe.throw(_("Please fill your name and a valid email."))
	room_name = frappe.db.get_value("Client Room", {"invite_token": token, "status": "Active"})
	if not room_name:
		frappe.throw(_("This invite link is not valid — ask your Xlevel contact for a fresh one."))
	if frappe.db.exists("Client Room Member", {"room": room_name, "user": email, "active": 1}):
		return {"ok": True, "already": True}
	if frappe.db.exists(
		"Client Join Request", {"room": room_name, "email": email, "status": "Pending"}
	):
		return {"ok": True, "pending": True}
	if frappe.db.count("Client Join Request", {"room": room_name, "status": "Pending"}) >= 20:
		frappe.throw(_("Too many pending requests for this room — contact Xlevel directly."))

	created_user = 0
	if not frappe.db.exists("User", email):
		# No guest-chosen credentials and no pre-approval emails: the account
		# sits disabled and silent until a staff member approves, and the
		# approval email's set-password link is the only way to credentials.
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name,
				"user_type": "Website User",
				"enabled": 0,
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		created_user = 1

	frappe.get_doc(
		{
			"doctype": "Client Join Request",
			"room": room_name,
			"full_name": full_name,
			"email": email,
			"phone": phone,
			"status": "Pending",
			"created_user": created_user,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.publish_realtime("duty_client_room", {"room": room_name})
	try:
		from duty_board.api import _notify_user

		customer = frappe.db.get_value("Client Room", room_name, "customer")
		for u in frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]
		):
			if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
				_notify_user(u.name, _("🙋 Join request · {0}").format(customer), full_name)
	except Exception:
		pass
	return {"ok": True}


def _send_join_approved_email(req):
	"""Welcome the approved member: portal link + a set-password link when
	they have never signed in. Courtesy layer — never raises."""
	try:
		from frappe.utils import get_url

		portal = get_url("/portal")
		customer = frappe.db.get_value("Client Room", req.room, "customer") or "your company"
		needs_password = not frappe.db.get_value("User", req.email, "last_login")
		reset_link = None
		if needs_password:
			try:
				user = frappe.get_doc("User", req.email)
				reset_link = user.reset_password(send_email=False)
			except Exception:
				reset_link = None
		first = (req.full_name or "").split(" ")[0] or _("there")
		body = _(
			"<p>Hello {0},</p>"
			"<p>Your request to join the <b>{1}</b> workspace on the Xlevel Client Portal has been <b>approved</b>. 🎉</p>"
			"<p><b>Sign in here:</b> <a href=\"{2}\">{2}</a></p>"
		).format(frappe.utils.escape_html(first), frappe.utils.escape_html(customer), portal)
		if reset_link:
			body += _(
				"<p><b>First, set your password:</b> <a href=\"{0}\">Choose your password</a> — then sign in with your email <b>{1}</b>.</p>"
			).format(reset_link, frappe.utils.escape_html(req.email))
		else:
			body += _("<p>Sign in with your email <b>{0}</b> and your existing password.</p>").format(
				frappe.utils.escape_html(req.email)
			)
		body += _(
			"<p>Tip: open the link on your phone and use “Add to Home Screen” to install the portal as an app, "
			"then allow notifications so nothing waits for you.</p>"
			"<p>See you inside,<br>The Xlevel Team</p>"
		)
		frappe.sendmail(
			recipients=[req.email],
			subject=_("✅ Your Xlevel Client Portal access is approved"),
			message=body,
			delayed=False,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback()[:2000], "join approval email")


@frappe.whitelist()
def approve_join(request_name):
	_staff_only()
	req = frappe.get_doc("Client Join Request", request_name)
	if req.status != "Pending":
		frappe.throw(_("Already handled."))
	add_member(req.room, req.email, req.full_name)
	if frappe.db.get_value("User", req.email, "user_type") == "Website User":
		if req.created_user and not frappe.db.get_value("User", req.email, "last_login"):
			# Retroactive lock: requests submitted before v3.58.0 could carry a
			# requester-chosen password. Scramble it (and any sessions) before
			# enabling, so the approval email's set-password link is the only
			# door — for planted requests and legitimate ones alike.
			from frappe.utils.password import update_password
			update_password(req.email, frappe.generate_hash(length=32), logout_all_sessions=True)
		frappe.db.set_value("User", req.email, "enabled", 1, update_modified=False)
	req.db_set("status", "Approved", update_modified=False)
	frappe.db.commit()
	_send_join_approved_email(req)
	frappe.publish_realtime("duty_client_room", {"room": req.room})
	return get_room(req.room)


@frappe.whitelist()
def reject_join(request_name):
	_staff_only()
	req = frappe.get_doc("Client Join Request", request_name)
	if (
		req.created_user
		and frappe.db.exists("User", req.email)
		and frappe.db.get_value("User", req.email, ["user_type", "enabled"], as_dict=True)
		== frappe._dict(user_type="Website User", enabled=0)
	):
		frappe.delete_doc("User", req.email, ignore_permissions=True, force=True)
	req.db_set("status", "Rejected", update_modified=False)
	frappe.db.commit()
	frappe.publish_realtime("duty_client_room", {"room": req.room})
	return get_room(req.room)


@frappe.whitelist()
def client_request_task(title, detail=None, attachment_url=None, attachment_name=None, urgent=0, issue_type=None):
	room = _client_room()
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Describe what you need."))
	if len(title) > 200:
		frappe.throw(_("Keep the request under 200 characters."))
	att = None
	if attachment_url:
		att = frappe.db.get_value(
			"File",
			{"file_url": attachment_url, "owner": frappe.session.user},
			["name", "file_name"],
			as_dict=True,
		)
		if not att:
			frappe.throw(_("Upload not found — try attaching again."))
	if cint(urgent):
		today_urgent = frappe.db.count(
			"Duty Issue",
			{
				"customer": room.customer,
				"client_requested": 1,
				"severity": "High",
				"creation": [">=", frappe.utils.today()],
			},
		)
		if today_urgent >= 3:
			frappe.throw(
				_("Urgent limit reached for today — please call your account manager for anything critical.")
			)
	if issue_type not in ISSUE_TYPES:
		frappe.throw(_("Choose the request type."))
	doc = _new_client_issue(
		room, title, requested=1, raised_by=frappe.session.user,
		detail=detail, issue_type=issue_type,
	)
	if cint(urgent):
		frappe.db.set_value("Duty Issue", doc.name, "severity", "High", update_modified=False)
	if att:
		frappe.db.set_value(
			"File",
			att.name,
			{"attached_to_doctype": "Duty Issue", "attached_to_name": doc.name},
			update_modified=False,
		)
	frappe.db.commit()  # release the naming-series lock before any network I/O
	_post(
		room,
		(_("🔴 URGENT — ") if cint(urgent) else "")
		+ _("🙋 Requested: “{0}” → Queued").format(title),
		attachment_url=attachment_url,
		attachment_name=(attachment_name or (att.file_name if att else None)),
	)
	try:
		from duty_board.api import _notify_user

		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		for u in frappe.get_all(
			"User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]
		):
			if frappe.db.exists("Duty Push Subscription", {"user": u.name}):
				is_owner = room.owner_user and u.name == room.owner_user
				_notify_user(
					u.name,
					(
						_("★ 🔴 URGENT — your account · {0}")
						if (cint(urgent) and is_owner)
						else _("🔴 URGENT · {0}")
						if cint(urgent)
						else _("⚠ New client issue · {0}")
					).format(room.customer),
					title[:120],
				)
	except Exception:
		pass
	if cint(urgent):
		try:
			from duty_board.api import notify_on_call

			notify_on_call(_("URGENT · {0}").format(room.customer), title[:120])
		except Exception:
			pass
	frappe.db.commit()
	ret = client_get_room()
	ret["after_hours"] = _after_hours_payload()
	ret["scope_note"] = frappe.db.get_value("Client Room", ret.get("room"), "scope_note") if ret.get("room") else ""
	ret["support_plan"] = frappe.db.get_value("Client Room", ret.get("room"), "support_plan") if ret.get("room") else ""
	return ret


@frappe.whitelist()
def meeting_slots_staff(id, date):
	"""Free slots for this meeting's requested attendees on a given day."""
	_staff_only()
	doc = frappe.get_doc("Duty Meeting", id)
	return _meeting_slots([a.user for a in doc.attendees], str(date))


@frappe.whitelist()
def suggest_meeting_time(id, date, time):
	"""Staff counter-proposal: move a Pending meeting to a verified-free
	slot and tell the client in their room. Confirmation stays a separate,
	deliberate act."""
	_staff_only()
	doc = frappe.get_doc("Duty Meeting", id)
	if doc.status != "Pending":
		frappe.throw(_("Already settled."))
	attendee_ids = [a.user for a in doc.attendees]
	me = frappe.session.user
	if me not in attendee_ids and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only a requested attendee can suggest a new time."))
	slot = str(time)[:5]
	if slot not in _meeting_slots(attendee_ids, str(date)):
		frappe.throw(_("That slot is no longer free for the team — pick another."))
	old = f"{frappe.utils.formatdate(doc.meeting_date)} {str(doc.start_time)[:5]}"
	doc.db_set("meeting_date", date, update_modified=False)
	doc.db_set("start_time", slot + ":00", update_modified=False)
	frappe.db.commit()
	room = frappe.get_doc("Client Room", doc.room)
	_post(
		room,
		_("📅 About “{0}”: {1} doesn't work for the team — could we do {2} at {3} instead? If that suits, no reply is needed and we'll confirm it shortly. If not, tell us a better time right here.").format(
			doc.topic, old, frappe.utils.formatdate(date), slot
		),
	)
	_push_room_clients(room, _("📅 New time suggested · Xlevel"), doc.topic[:120])
	return get_room(doc.room)


@frappe.whitelist()
def client_shelf_preview(id):
	"""Inline-rendering variant of client_shelf_file for the Documents
	workspace preview pane. Returns a raw werkzeug Response with an
	explicit inline disposition, since frappe's binary response path
	does not reliably honour display_content_as."""
	room = _client_room()
	d = frappe.db.get_value(
		"Client Shelf Doc", id, ["room", "file_url", "file_name", "active"], as_dict=True
	)
	if not d or d.room != room.name or not cint(d.active):
		frappe.throw(_("Not found."), frappe.PermissionError)
	fname = frappe.db.get_value("File", {"file_url": d.file_url})
	if not fname:
		frappe.throw(_("File missing."))
	fdoc = frappe.get_doc("File", fname)
	import mimetypes

	mt = (
		mimetypes.guess_type(d.file_name or fdoc.file_name or "")[0]
		or "application/octet-stream"
	)
	from werkzeug.wrappers import Response

	resp = Response(fdoc.get_content(), mimetype=mt)
	safe_name = (d.file_name or "file").replace('"', "")
	resp.headers["Content-Disposition"] = f'inline; filename="{safe_name}"'
	resp.headers["Cache-Control"] = "private, max-age=300"
	return resp


@frappe.whitelist()
def invite_consultant(room, email, full_name=None):
	"""One-stroke consultant onboarding: create (or reuse) the System User
	with the Duty Consultant role, add active room membership, send
	frappe's welcome email on creation, and leave an internal note in the
	room. Staff only. Refuses to touch an existing STAFF user — adding the
	consultant role would demote them (require_staff rejects it)."""
	_staff_only()
	from duty_board.permissions import CONSULTANT_ROLE, is_consultant

	email = (email or "").strip().lower()
	frappe.utils.validate_email_address(email, throw=True)
	r = frappe.get_doc("Client Room", room)
	created = 0
	if frappe.db.exists("User", email):
		u = frappe.get_doc("User", email)
		if u.user_type != "System User":
			frappe.throw(_("That email belongs to a client portal user — use the client member flow instead."))
		if not is_consultant(email):
			frappe.throw(_("That email belongs to a staff member. Adding the consultant role would lock them out of the staff app."))
	else:
		if not frappe.db.exists("Role", CONSULTANT_ROLE):
			frappe.get_doc({"doctype": "Role", "role_name": CONSULTANT_ROLE, "desk_access": 1}).insert(ignore_permissions=True)
		names = (full_name or email.split("@")[0]).strip().split(" ", 1)
		u = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": names[0],
			"last_name": names[1] if len(names) > 1 else "",
			"user_type": "System User",
			"enabled": 1,
			"send_welcome_email": 1,
			"roles": [{"role": CONSULTANT_ROLE}],
		}).insert(ignore_permissions=True)
		created = 1
	existing = frappe.db.get_value(
		"Client Room Member", {"room": room, "user": email}, ["name", "active"], as_dict=True
	)
	# tidy desk: module profile + landing workspace, when the site has them
	try:
		updates = {}
		if frappe.db.exists("Module Profile", "External Consultant") and not u.module_profile:
			updates["module_profile"] = "External Consultant"
		if frappe.db.has_column("User", "default_workspace") and not u.get("default_workspace"):
			updates["default_workspace"] = "Home"
		if updates:
			frappe.db.set_value("User", u.name, updates, update_modified=False)
	except Exception:
		pass  # cosmetic only — never block an invite on desk tidying
	if existing:
		frappe.db.set_value("Client Room Member", existing.name, {
			"active": 1, "member_type": "Consultant"
		}, update_modified=False)
	else:
		frappe.get_doc({
			"doctype": "Client Room Member",
			"room": room,
			"user": email,
			"active": 1,
			"member_type": "Consultant",
		}).insert(ignore_permissions=True)
	first = frappe.utils.get_fullname(email).split(" ")[0]
	_post(r, _("👷 Consultant {0} ({1}) was added to this room.").format(first, email), 1, None, None, None)
	frappe.db.commit()
	return {"ok": 1, "created": created, "user": email}


@frappe.whitelist()
def chreq_get(id):
	"""Fetch a change request for the update dialog. Staff freely;
	consultants only for CRs from their assigned issues or their rooms."""
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names

	_is_c = require_staff_or_consultant()
	doc = frappe.get_doc("Duty Change Request", id)
	if _is_c:
		ok = False
		if doc.source_issue:
			from duty_board.api import _consultant_issue_check

			try:
				_consultant_issue_check(frappe.get_doc("Duty Issue", doc.source_issue))
				ok = True
			except frappe.PermissionError:
				ok = False
		if not ok and doc.room in consultant_room_names():
			ok = True
		if not ok:
			frappe.throw(_("Not permitted."), frappe.PermissionError)
	locked = False
	try:
		_chreq_locked(doc)
	except Exception:
		locked = True
	return {
		"name": doc.name,
		"title": doc.title,
		"status": doc.status,
		"pricing_status": doc.get("pricing_status"),
		"reason": doc.reason,
		"scope_impact": doc.scope_impact,
		"timeline_impact": doc.timeline_impact,
		"cost_impact": doc.cost_impact,
		"resource_impact": doc.resource_impact,
		"risks": doc.risks,
		"locked": int(locked),
	}


def _staff_sees_room(room, user):
	"""Empty staff_users = open to all staff; else listed users + the
	room owner (System Managers bypass at the call sites)."""
	su = (room.get("staff_users") or "").strip()
	if not su:
		return True
	if user == room.get("owner_user"):
		return True
	listed = [x.strip().lower() for x in su.replace("\n", ",").split(",") if x.strip()]
	return user.lower() in listed


@frappe.whitelist()
def my_rooms_summary():
	"""For the dashboard: rooms I own and rooms I'm named into."""
	from duty_board.permissions import require_staff_or_consultant, consultant_room_names

	_is_c = require_staff_or_consultant()
	me = frappe.session.user
	rooms = frappe.get_all(
		"Client Room",
		filters={"status": ["!=", "Archived"]},
		fields=["name", "customer", "unit", "owner_user", "staff_users"],
	)
	if _is_c:
		memb = consultant_room_names()
		return {"owned": [], "member": [{"name": r.name, "customer": r.customer, "unit": r.unit} for r in rooms if r.name in memb]}
	owned = [r for r in rooms if r.owner_user == me]
	member = [
		r for r in rooms
		if r.owner_user != me
		and me.lower() in [x.strip().lower() for x in (r.staff_users or "").replace("\n", ",").split(",") if x.strip()]
	]
	slim = lambda rs: [{"name": r.name, "customer": r.customer, "unit": r.unit} for r in rs]
	return {"owned": slim(owned), "member": slim(member)}


@frappe.whitelist()
def room_staff_access(name):
	"""Read the room's staff shortlist — System Manager or room owner."""
	from duty_board.permissions import require_staff

	require_staff()
	room = frappe.get_doc("Client Room", name)
	me = frappe.session.user
	can_edit = "System Manager" in frappe.get_roles() or room.get("owner_user") == me
	return {
		"users": [x.strip() for x in (room.get("staff_users") or "").replace("\n", ",").split(",") if x.strip()],
		"owner": room.get("owner_user"),
		"can_edit": can_edit,
	}


@frappe.whitelist()
def set_room_staff_access(name, users=None, owner=None):
	"""Write the shortlist and/or owner — System Manager or current owner
	only. Empty shortlist restores everyone-sees-it."""
	from duty_board.permissions import require_staff

	require_staff()
	room = frappe.get_doc("Client Room", name)
	me = frappe.session.user
	if "System Manager" not in frappe.get_roles() and room.get("owner_user") != me:
		frappe.throw(_("Only the room owner or a System Manager curates access."), frappe.PermissionError)
	if isinstance(users, str):
		try:
			users = frappe.parse_json(users)
		except Exception:
			users = [x.strip() for x in users.split(",") if x.strip()]
	room.db_set("staff_users", ", ".join(sorted(set(users or []))) or None, update_modified=False)
	if owner is not None:
		room.db_set("owner_user", owner or None, update_modified=False)
	frappe.db.commit()
	return room_staff_access(name)
