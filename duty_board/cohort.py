"""Training cohorts: the group as a first-class object.

A cohort is one client's staff running one track (or one course) together —
a live session on a date, a manual to read, and an exam window to sit inside.
Every endpoint here is staff-only; clients never address a cohort directly,
they only feel it as the training that appeared on their portal and the window
their assessment opens in.

Enrolment is idempotent by design. It adopts any Duty Training Record the
trainee already holds for a module rather than creating a second one, so a
cohort can be re-enrolled after a late joiner is added without doubling
anybody's course list.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

STATUSES = ("Draft", "Enrolled", "In Progress", "Closed")
SETTABLE = {
	"title", "track", "module", "facilitator", "session_on",
	"opens_on", "closes_on", "note",
}


def _staff_only():
	from duty_board.permissions import require_staff

	require_staff()


def _cohort(name):
	_staff_only()
	return frappe.get_doc("Duty Training Cohort", name)


def _modules(coh):
	"""The courses this cohort covers: every module of the track, in order,
	or the single course when one is named."""
	if coh.track:
		return frappe.get_all(
			"Duty Certification Track Module",
			filters={"parent": coh.track},
			pluck="module",
			order_by="idx asc",
		)
	return [coh.module] if coh.module else []


def window_state(cohort):
	"""Open / not yet / closed / none, for a cohort name. Used by the exam
	gate and by the staff UI so both read the same clock."""
	if not cohort:
		return {"state": "none"}
	row = frappe.db.get_value(
		"Duty Training Cohort", cohort, ["opens_on", "closes_on", "status"], as_dict=True
	)
	if not row or (not row.opens_on and not row.closes_on):
		return {"state": "none"}
	now = now_datetime()
	if row.opens_on and now < get_datetime(row.opens_on):
		return {"state": "early", "opens_on": str(row.opens_on)}
	if row.closes_on and now > get_datetime(row.closes_on):
		return {"state": "closed", "closes_on": str(row.closes_on)}
	return {"state": "open", "closes_on": str(row.closes_on) if row.closes_on else None}


# ---------------- reads ----------------


@frappe.whitelist()
def cohort_list(room=None):
	_staff_only()
	filters = {"room": room} if room else {}
	rows = frappe.get_all(
		"Duty Training Cohort",
		filters=filters,
		fields=[
			"name", "room", "title", "status", "track", "module",
			"facilitator", "session_on", "opens_on", "closes_on",
		],
		order_by="creation desc",
		limit_page_length=60,
	)
	for r in rows:
		r["member_count"] = frappe.db.count(
			"Duty Training Cohort Member", {"parent": r.name}
		)
		r["enrolled_count"] = frappe.db.count(
			"Duty Training Cohort Member", {"parent": r.name, "enrolled": 1}
		)
		r["window"] = window_state(r.name)
	return rows


@frappe.whitelist()
def cohort_get(name):
	coh = _cohort(name)
	mods = _modules(coh)
	titles = {
		m.name: m.title
		for m in frappe.get_all(
			"Duty Training Module", filters={"name": ["in", mods or [""]]},
			fields=["name", "title"],
		)
	}
	people = []
	for m in coh.members:
		recs = frappe.get_all(
			"Duty Training Record",
			filters={"room": coh.room, "trainee": m.trainee, "module": ["in", mods or [""]]},
			fields=["module", "status"],
		)
		done = sum(1 for r in recs if r.status == "Completed")
		people.append({
			"trainee": m.trainee,
			"trainee_name": m.trainee_name or frappe.utils.get_fullname(m.trainee),
			"attended": cint(m.attended),
			"enrolled": cint(m.enrolled),
			"done": done,
			"total": len(mods),
		})
	return {
		"name": coh.name,
		"room": coh.room,
		"title": coh.title,
		"status": coh.status,
		"track": coh.track,
		"module": coh.module,
		"facilitator": coh.facilitator,
		"session_on": str(coh.session_on) if coh.session_on else None,
		"opens_on": str(coh.opens_on) if coh.opens_on else None,
		"closes_on": str(coh.closes_on) if coh.closes_on else None,
		"note": coh.note,
		"courses": [{"name": m, "title": titles.get(m, m)} for m in mods],
		"people": people,
		"window": window_state(coh.name),
	}


@frappe.whitelist()
def cohort_candidates(room):
	"""Active members of the room who are not already in this room's rooms —
	the pool a cohort draws from."""
	_staff_only()
	rows = frappe.get_all(
		"Client Room Member",
		filters={"room": room, "active": 1},
		fields=["user"],
	)
	return [
		{"user": r.user, "full_name": frappe.utils.get_fullname(r.user)}
		for r in rows
		if r.user
	]


# ---------------- writes ----------------


@frappe.whitelist()
def cohort_create(room, title, track=None, module=None):
	_staff_only()
	if not frappe.db.exists("Client Room", room):
		frappe.throw(_("Not found."))
	if not (track or module):
		frappe.throw(_("A cohort needs either a certification track or a single course."))
	coh = frappe.get_doc({
		"doctype": "Duty Training Cohort",
		"room": room,
		"title": title,
		"track": track,
		"module": module,
		"status": "Draft",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return cohort_get(coh.name)


@frappe.whitelist()
def cohort_set(name, field, value=None):
	coh = _cohort(name)
	if field not in SETTABLE:
		frappe.throw(_("That field is not editable here."))
	coh.db_set(field, value or None)
	frappe.db.commit()
	return cohort_get(name)


@frappe.whitelist()
def cohort_add_member(name, user):
	coh = _cohort(name)
	if not frappe.db.exists("Client Room Member", {"room": coh.room, "user": user, "active": 1}):
		frappe.throw(_("That person is not an active member of this room."))
	if any(m.trainee == user for m in coh.members):
		frappe.throw(_("Already in this cohort."))
	coh.append("members", {
		"trainee": user,
		"trainee_name": frappe.utils.get_fullname(user),
	})
	coh.save(ignore_permissions=True)
	frappe.db.commit()
	return cohort_get(name)


@frappe.whitelist()
def cohort_remove_member(name, user):
	coh = _cohort(name)
	row = [m for m in coh.members if m.trainee == user]
	if not row:
		frappe.throw(_("Not in this cohort."))
	if cint(row[0].enrolled):
		frappe.throw(
			_("{0} is already enrolled — their training records stand. Remove them from the course instead.").format(
				row[0].trainee_name or user
			)
		)
	coh.members = [m for m in coh.members if m.trainee != user]
	coh.save(ignore_permissions=True)
	frappe.db.commit()
	return cohort_get(name)


@frappe.whitelist()
def cohort_attendance(name, user, attended=1):
	coh = _cohort(name)
	hit = False
	for m in coh.members:
		if m.trainee == user:
			m.attended = 1 if cint(attended) else 0
			hit = True
	if not hit:
		frappe.throw(_("Not in this cohort."))
	coh.save(ignore_permissions=True)
	frappe.db.commit()
	return cohort_get(name)


@frappe.whitelist()
def cohort_enrol(name):
	"""Create (or adopt) a Duty Training Record per member per course and
	stamp the cohort on it. Idempotent — safe to re-run after a late joiner."""
	coh = _cohort(name)
	if coh.status == "Closed":
		frappe.throw(_("This cohort is closed."))
	mods = _modules(coh)
	if not mods:
		frappe.throw(_("This cohort has no courses — set a track or a single course first."))
	if not coh.members:
		frappe.throw(_("This cohort has no members yet."))
	created, adopted = 0, 0
	for m in coh.members:
		for mod in mods:
			existing = frappe.db.get_value(
				"Duty Training Record",
				{"room": coh.room, "module": mod, "trainee": m.trainee},
				"name",
			)
			if existing:
				if not frappe.db.get_value("Duty Training Record", existing, "cohort"):
					frappe.db.set_value(
						"Duty Training Record", existing, "cohort", coh.name,
						update_modified=False,
					)
				adopted += 1
				continue
			frappe.get_doc({
				"doctype": "Duty Training Record",
				"room": coh.room,
				"module": mod,
				"trainee": m.trainee,
				"trainee_name": m.trainee_name or frappe.utils.get_fullname(m.trainee),
				"status": "Assigned",
				"cohort": coh.name,
			}).insert(ignore_permissions=True)
			created += 1
		m.enrolled = 1
	if coh.status == "Draft":
		coh.status = "Enrolled"
	coh.save(ignore_permissions=True)
	frappe.db.commit()
	_announce(coh, created)
	return {"created": created, "adopted": adopted, "cohort": cohort_get(name)}


def _announce(coh, created):
	"""One room narration and one notification per trainee — the same
	etiquette the single-assignment path already keeps."""
	if not created:
		return
	try:
		from duty_board.client_room import _post

		room = frappe.get_doc("Client Room", coh.room)
		_post(
			room,
			_("🎓 Training cohort “{0}” enrolled — {1} course place(s) across {2} people").format(
				coh.title, created, len(coh.members)
			),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board cohort narration")
	for m in coh.members:
		try:
			from duty_board.api import _notify_user

			_notify_user(
				m.trainee,
				_("🎓 New training · Xlevel"),
				coh.title,
			)
		except Exception:
			pass


@frappe.whitelist()
def cohort_close(name):
	coh = _cohort(name)
	coh.db_set("status", "Closed")
	frappe.db.commit()
	return cohort_get(name)
