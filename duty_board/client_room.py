"""Client Rooms: one room per customer, two faces, a membrane between.

Staff endpoints require a System User session. Client endpoints require a
Website User session and resolve the caller's room from their membership as
the FIRST act — nothing is ever queried by a client-supplied identifier.
Internal ("whisper") messages never cross the membrane.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, today

MSG_MAX = 2000
CLIENT_STATUS = {"To Do": "Queued", "In Progress": "In Progress", "Completed": "Done"}


# ---------------- membrane guards ----------------


def _staff_only():
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if frappe.db.get_value("User", frappe.session.user, "user_type") != "System User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)


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
			"name", "message", "internal", "owner", "creation",
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
		r.who = names.setdefault(
			r.owner, frappe.utils.get_fullname(r.owner) or r.owner
		)
		r.is_staff = frappe.db.get_value("User", r.owner, "user_type") == "System User"
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
			}
		)
	projs = frappe.get_all(
		"Duty Project",
		filters={"customer": room.customer, "status": "Active"},
		pluck="name",
	)
	if projs:
		for t in frappe.get_all(
			"Duty Project Task",
			filters={"project": ["in", projs], "client_visible": 1},
			fields=["name", "title", "column", "assignee", "client_requested", "modified", "creation"],
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


# ---------------- staff face ----------------


@frappe.whitelist()
def get_rooms():
	_staff_only()
	rooms = frappe.get_all(
		"Client Room",
		filters={"status": ["!=", "Archived"]},
		fields=["name", "customer", "unit", "status", "project"],
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
		r.unread = _room_unread(r.name, frappe.session.user)
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
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	messages, has_more = _room_payload(room, include_internal=True, before=before)
	members = frappe.get_all(
		"Client Room Member",
		filters={"room": name, "active": 1},
		fields=["name", "user", "last_seen", "is_admin"],
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
	return {
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


@frappe.whitelist()
def post_message(name, message, internal=0, attachment_url=None, attachment_name=None, ref=None):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
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
	return client_get_room()


def _serve_file(fdoc, filename):
	import mimetypes

	mimetype = (
		mimetypes.guess_type(filename or fdoc.file_name or "")[0]
		or "application/octet-stream"
	)
	frappe.local.response.filename = filename or fdoc.file_name
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
		return {
			"kind": "card",
			"title": t.title,
			"status": status,
			"client_requested": cint(t.client_requested),
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
	_serve_file(fdoc, fdoc.file_name)


def _shelf_rows(room):
	rows = frappe.get_all(
		"Client Shelf Doc",
		filters={"room": room.name, "active": 1},
		fields=["name", "title", "category", "file_name", "creation"],
		order_by="creation desc",
		limit=200,
	)
	for r in rows:
		r.creation = str(r.creation)[:10]
	return rows


@frappe.whitelist()
def shelf_add(name, title, attachment_url, attachment_name=None, category=None):
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
	frappe.get_doc(
		{
			"doctype": "Client Shelf Doc",
			"room": room.name,
			"title": title[:140],
			"category": (category or "").strip()[:60] or None,
			"file_url": attachment_url,
			"file_name": attachment_name or owned,
			"active": 1,
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


@frappe.whitelist()
def client_get_documents():
	room = _client_room()
	return _shelf_rows(room)


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
	_serve_file(frappe.get_doc("File", fname), d.file_name)


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
	_serve_file(frappe.get_doc("File", fname), d.file_name)


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


def _room_unread(room_name, user):
	seen = frappe.db.get_value(
		"Client Room Seen", {"room": room_name, "user": user}, "last_seen"
	)
	filters = {"room": room_name, "owner": ["!=", user]}
	if seen:
		filters["creation"] = [">", seen]
	return frappe.db.count("Client Room Message", filters)


@frappe.whitelist()
def mark_room_seen(name):
	_staff_only()
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
	_staff_only()
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
	rows = frappe.get_all(
		"Duty Milestone",
		filters={"room": room.name},
		fields=[
			"name", "title", "description", "sort_order", "status", "target_date",
			"approved_full", "approved_at", "approval_note", "submitted_on", "project",
		],
		order_by="sort_order asc, creation asc",
	)
	for r in rows:
		r.target_date = str(r.target_date) if r.target_date else None
		r.approved_at = str(r.approved_at)[:16] if r.approved_at else None
		tasks = frappe.get_all(
			"Duty Project Task",
			filters={"milestone": r.name},
			fields=[
				"name", "title", "column", "assignee", "due_date",
				"urgency", "description", "awaiting_client",
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
	return rows


@frappe.whitelist()
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
	return rows


@frappe.whitelist()
def client_approve_milestone(id, note=None):
	room = _client_room()
	if not _client_can_approve(room):
		frappe.throw(_("Only your team's administrator can approve on behalf of your company."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Milestone", id)
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
		],
		order_by="creation desc",
	)
	for r in rows:
		r.submitted_on = str(r.submitted_on)[:16] if r.submitted_on else None
		r.approved_at = str(r.approved_at)[:16] if r.approved_at else None
		r.declined_at = str(r.declined_at)[:16] if r.declined_at else None
		r.delivered_at = str(r.delivered_at)[:16] if r.delivered_at else None
		r.cost_fmt = _chreq_fmt(r.cost_impact)
		r.approved_fmt = _chreq_fmt(r.approved_amount)
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
def chreq_add(name, title, original_request=None):
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
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return get_room(name)


@frappe.whitelist()
def chreq_from_message(name, msg, title):
	_staff_only()
	room = frappe.get_doc("Client Room", name)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Give the change request a title."))
	m = frappe.db.get_value(
		"Client Room Message", msg, ["room", "message"], as_dict=True
	)
	if not m or m.room != room.name:
		frappe.throw(_("Message not found in this room."))
	frappe.get_doc(
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
	return get_room(name)


@frappe.whitelist()
def chreq_from_issue(issue):
	_staff_only()
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
	frappe.get_doc(
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
	return get_room(room.name)


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
	quotation=None,
):
	_staff_only()
	doc = frappe.get_doc("Duty Change Request", id)
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
	rows = [
		r for r in _chreq_rows(room)
		if r.status in ("Awaiting Approval", "Approved", "Declined", "In Delivery", "Delivered")
	]
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
	pdf = frappe.utils.pdf.get_pdf(_report_html(room, label, s))
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
			"Duty Training Module", fields=["name", "title", "product"]
		)
	}
	for r in rows:
		m = mods.get(r.module)
		r.module_title = m.title if m else r.module
		r.product = m.product if m else None
		r.completed_on = str(r.completed_on) if r.completed_on else None
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
		pdf = frappe.utils.pdf.get_pdf(
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
		for m in frappe.get_all("Duty Training Module", fields=["name", "title", "product"])
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
	pdf = frappe.utils.pdf.get_pdf(_track_certificate_html(cert))
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
	_serve_file(frappe.get_doc("File", fname), f"{serial}.pdf")


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
	"""The pickable product names — exactly what track inheritance matches on."""
	_staff_only()
	out = set()
	for p in frappe.get_all(
		"Duty Certification Track", filters={"active": 1}, fields=["product"], pluck="product"
	):
		if p and p.strip():
			out.add(p.strip())
	for p in frappe.get_all(
		"Duty Training Module", filters={"active": 1}, fields=["product"], pluck="product"
	):
		if p and p.strip():
			out.add(p.strip())
	return sorted(out)


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
	pdf = frappe.utils.pdf.get_pdf(_rca_html(doc, rca, timeline))
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
	day_n = frappe.db.count(
		"Duty Meeting", {"room": ["in", rooms], "creation": [">=", str(today_d)]}
	)
	if day_n >= 1:
		frappe.throw(
			_("You've already requested a meeting today — one request per day keeps our calendar fair for everyone.")
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
				"description": f"📅 {doc.customer}: {doc.topic}",
				"status": "Open",
				"due_time": doc.start_time,
				"assigned_by": me if me != u else None,
			}
		).insert(ignore_permissions=True)
		todos.append(t.name)
	doc.db_set("created_todos", json.dumps(todos), update_modified=False)
	doc.db_set("status", "Confirmed", update_modified=False)
	doc.db_set("confirmed_by", me, update_modified=False)
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
	_email_meeting_invite(doc, room)
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


def meeting_reminders():
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


def _meeting_ics(doc):
	start = f"{str(doc.meeting_date).replace('-', '')}T{str(doc.start_time).replace(':', '')[:6]}"
	end_hour = int(str(doc.start_time)[:2]) + 1
	end = f"{str(doc.meeting_date).replace('-', '')}T{end_hour:02d}{str(doc.start_time)[3:5]}00"
	firsts = ", ".join(
		frappe.utils.get_fullname(a.user).split(" ")[0] for a in (doc.attendees or [])
	)
	return "\r\n".join(
		[
			"BEGIN:VCALENDAR",
			"VERSION:2.0",
			"PRODID:-//Xlevel Retail Systems//Duty Board//EN",
			"METHOD:PUBLISH",
			"BEGIN:VEVENT",
			f"UID:{doc.name}@xlevel.clouderp.one",
			f"DTSTART;TZID=Africa/Lagos:{start}",
			f"DTEND;TZID=Africa/Lagos:{end}",
			f"SUMMARY:Xlevel meeting: {doc.topic}",
			f"DESCRIPTION:With {firsts}. Manage this meeting on your portal.",
			"END:VEVENT",
			"END:VCALENDAR",
		]
	)


def _email_meeting_invite(doc, room):
	try:
		emails = [
			mm.user
			for mm in frappe.get_all(
				"Client Room Member",
				filters={"room": room.name, "active": 1},
				fields=["user"],
			)
			if "@" in (mm.user or "")
		]
		if not emails:
			return
		slot = str(doc.start_time)[:5]
		frappe.sendmail(
			recipients=emails,
			subject=_("📅 Confirmed: {0} — {1} {2}").format(
				doc.topic, frappe.utils.formatdate(doc.meeting_date, "d MMM"), slot
			),
			message=_(
				"Your meeting is confirmed.<br><b>{0}</b><br>{1} at {2} (WAT)<br><br>"
				"The attached invite adds it to your calendar."
			).format(
				frappe.utils.escape_html(doc.topic),
				frappe.utils.formatdate(doc.meeting_date, "EEEE, d MMMM"),
				slot,
			),
			attachments=[{"fname": "xlevel-meeting.ics", "fcontent": _meeting_ics(doc)}],
			delayed=True,
		)
	except Exception:
		pass


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
	if utype == "System User":
		pass
	elif utype == "Website User":
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
	_serve_file(fdoc, m.attachment_name or fdoc.file_name)


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
	room = _client_room()
	out = []
	for u in frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["full_name"],
	):
		if u.full_name and u.full_name != "Administrator":
			out.append({"first": u.full_name.split(" ")[0], "full": u.full_name, "kind": "staff"})
	me = frappe.session.user
	for m in frappe.get_all(
		"Client Room Member", filters={"room": room.name, "active": 1}, fields=["user"]
	):
		if m.user == me:
			continue
		full = frappe.utils.get_fullname(m.user) or m.user
		out.append({"first": full.split(" ")[0], "full": full, "kind": "colleague"})
	return out


@frappe.whitelist(allow_guest=True)
def submit_join_request(token, full_name, email, phone=None, password=None):
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
		password = (password or "").strip()
		if password and len(password) < 8:
			frappe.throw(_("Password must be at least 8 characters."))
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name,
				"user_type": "Website User",
				"enabled": 0,
				"send_welcome_email": 0 if password else 1,
			}
		)
		if password:
			u.new_password = password
		u.insert(ignore_permissions=True)
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


@frappe.whitelist()
def approve_join(request_name):
	_staff_only()
	req = frappe.get_doc("Client Join Request", request_name)
	if req.status != "Pending":
		frappe.throw(_("Already handled."))
	add_member(req.room, req.email, req.full_name)
	if frappe.db.get_value("User", req.email, "user_type") == "Website User":
		frappe.db.set_value("User", req.email, "enabled", 1, update_modified=False)
	req.db_set("status", "Approved", update_modified=False)
	frappe.db.commit()
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
	return client_get_room()
