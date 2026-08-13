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
from frappe.utils import cint, get_datetime, now_datetime, today

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


# ---------------- the sponsor scorecard ----------------


def _attempt_pairs(att):
	"""[(question, correct?)] for a finished attempt, whichever exam style it
	was. Timed attempts already carry per-question outcomes; classic papers
	are recomputed from the served order and the answer sheet, using exactly
	the arithmetic that scored them."""
	import json

	if att.get("results"):
		try:
			return [(r["q"], bool(r.get("ok"))) for r in json.loads(att["results"])]
		except Exception:
			return []
	try:
		served = json.loads(att.get("served") or "[]")
		answers = json.loads(att.get("answers") or "{}")
	except Exception:
		return []
	if not served:
		return []
	correct = {
		q.name: "ABCD".index(q.correct)
		for q in frappe.get_all(
			"Duty Quiz Question",
			filters={"name": ["in", [s["q"] for s in served]]},
			fields=["name", "correct"],
		)
		if q.correct
	}
	out = []
	for s in served:
		chosen = answers.get(s["q"])
		chosen = cint(chosen) if chosen is not None else -1
		real = s["order"][chosen] if 0 <= chosen < 4 else -1
		out.append((s["q"], real == correct.get(s["q"])))
	return out


def _bucket(score):
	if score >= 85:
		return "85–100"
	if score >= 70:
		return "70–84"
	if score >= 50:
		return "50–69"
	return "Below 50"


@frappe.whitelist()
def cohort_scorecard(name):
	"""The group's result. Reached entirely through the cohort back-link."""
	coh = _cohort(name)
	mods = _modules(coh)
	titles = {
		m.name: m.title
		for m in frappe.get_all(
			"Duty Training Module", filters={"name": ["in", mods or [""]]},
			fields=["name", "title"],
		)
	}
	recs = frappe.get_all(
		"Duty Training Record",
		filters={"cohort": coh.name},
		fields=["name", "module", "trainee", "trainee_name", "status"],
	)
	attended = {m.trainee for m in coh.members if cint(m.attended)}
	by_rec = {r.name: r for r in recs}
	attempts = []
	if recs:
		attempts = frappe.get_all(
			"Duty Quiz Attempt",
			filters={"record": ["in", list(by_rec)], "finished_at": ["is", "set"]},
			fields=[
				"name", "record", "module", "user", "score", "passed",
				"finished_at", "served", "answers", "results", "blurs", "mode",
			],
			order_by="finished_at asc",
		)

	# ---- per person, per course
	first_of, best_of, tries_of = {}, {}, {}
	for a in attempts:
		key = (a.user, a.module)
		first_of.setdefault(key, a)
		tries_of[key] = tries_of.get(key, 0) + 1
		if a.score > best_of.get(key, {}).get("score", -1):
			best_of[key] = a

	people = []
	for m in coh.members:
		rows = []
		for mod in mods:
			rec = next(
				(r for r in recs if r.trainee == m.trainee and r.module == mod), None
			)
			key = (m.trainee, mod)
			best = best_of.get(key)
			first = first_of.get(key)
			rows.append({
				"module": mod,
				"title": titles.get(mod, mod),
				"enrolled": bool(rec),
				"complete": bool(rec and rec.status == "Completed"),
				"attempts": tries_of.get(key, 0),
				"first": cint(first.score) if first else None,
				"best": cint(best.score) if best else None,
				"passed": bool(best and cint(best.passed)),
			})
		sat = [r for r in rows if r["attempts"]]
		people.append({
			"trainee": m.trainee,
			"trainee_name": m.trainee_name or frappe.utils.get_fullname(m.trainee),
			"attended": m.trainee in attended,
			"courses": rows,
			"complete": sum(1 for r in rows if r["complete"]),
			"total": len(mods),
			"average": round(sum(r["best"] for r in sat) / len(sat)) if sat else None,
		})
	people.sort(key=lambda p: (-(p["average"] if p["average"] is not None else -1), p["trainee_name"]))

	# ---- per course
	courses = []
	for mod in mods:
		bests = [
			r["best"] for p in people for r in p["courses"]
			if r["module"] == mod and r["best"] is not None
		]
		passed = sum(
			1 for p in people for r in p["courses"] if r["module"] == mod and r["passed"]
		)
		courses.append({
			"module": mod,
			"title": titles.get(mod, mod),
			"sat": len(bests),
			"passed": passed,
			"pass_rate": round(passed * 100 / len(bests)) if bests else None,
			"average": round(sum(bests) / len(bests)) if bests else None,
		})

	# ---- distribution over every best score in the cohort
	buckets = {"85–100": 0, "70–84": 0, "50–69": 0, "Below 50": 0}
	all_best = [
		r["best"] for p in people for r in p["courses"] if r["best"] is not None
	]
	for s in all_best:
		buckets[_bucket(s)] += 1

	# ---- weakest areas, from FIRST attempts only
	agg = {}
	firsts = list(first_of.values())
	qids = set()
	pairs_by_attempt = {}
	for a in firsts:
		pairs = _attempt_pairs(a)
		pairs_by_attempt[a.name] = pairs
		qids.update(q for q, _ok in pairs)
	topics = {
		q.name: (q.topic or "").strip()
		for q in frappe.get_all(
			"Duty Quiz Question", filters={"name": ["in", list(qids) or [""]]},
			fields=["name", "topic"],
		)
	}
	has_topics = any(topics.values())
	for pairs in pairs_by_attempt.values():
		for q, ok in pairs:
			t = topics.get(q) or ""
			if not t:
				continue
			row = agg.setdefault(t, {"topic": t, "right": 0, "total": 0})
			row["total"] += 1
			if ok:
				row["right"] += 1
	areas = sorted(
		({**r, "pct": round(r["right"] * 100 / r["total"])} for r in agg.values()),
		key=lambda r: (r["pct"], r["topic"]),
	)

	# ---- integrity summary (staff view only; never printed for the sponsor)
	timed = [a for a in attempts if (a.mode or "") == "Timed"]
	timeouts = 0
	for a in timed:
		try:
			import json as _j

			timeouts += sum(1 for r in _j.loads(a.results or "[]") if r.get("timed_out"))
		except Exception:
			pass
	blurs = sum(cint(a.blurs) for a in timed)

	sat_people = sum(1 for p in people if p["average"] is not None)
	return {
		"cohort": coh.name,
		"title": coh.title,
		"room": coh.room,
		"customer": frappe.db.get_value("Client Room", coh.room, "customer") or coh.room,
		"status": coh.status,
		"facilitator": frappe.utils.get_fullname(coh.facilitator) if coh.facilitator else None,
		"session_on": str(coh.session_on) if coh.session_on else None,
		"opens_on": str(coh.opens_on) if coh.opens_on else None,
		"closes_on": str(coh.closes_on) if coh.closes_on else None,
		"members": len(coh.members),
		"attended": len(attended),
		"sat": sat_people,
		"courses": courses,
		"people": people,
		"buckets": [{"band": b, "n": buckets[b]} for b in ("85–100", "70–84", "50–69", "Below 50")],
		"average": round(sum(all_best) / len(all_best)) if all_best else None,
		"pass_rate": (
			round(sum(c["passed"] for c in courses) * 100 / sum(c["sat"] for c in courses))
			if sum(c["sat"] for c in courses) else None
		),
		"areas": areas,
		"has_topics": has_topics,
		"integrity": {"timed": len(timed), "timeouts": timeouts, "blurs": blurs},
	}


def _pct_bar(pct, colour):
	return (
		'<div style="height:8px;background:#E9EFEC;border-radius:99px;overflow:hidden;min-width:90px">'
		'<div style="height:8px;width:%s%%;background:%s"></div></div>' % (pct, colour)
	)


def _scorecard_html(sc):
	esc = frappe.utils.escape_html
	def band(p):
		return "#0E8A63" if p >= 70 else ("#C99A2E" if p >= 50 else "#C2410C")
	course_rows = "".join(
		"<tr><td>%s</td><td style='text-align:center'>%s</td><td style='text-align:center'>%s</td>"
		"<td style='text-align:center'>%s</td><td style='text-align:center'>%s</td></tr>"
		% (
			esc(c["title"]), c["sat"], c["passed"],
			("%s%%" % c["pass_rate"]) if c["pass_rate"] is not None else "—",
			("%s%%" % c["average"]) if c["average"] is not None else "—",
		)
		for c in sc["courses"]
	)
	area_rows = "".join(
		"<tr><td>%s</td><td style='width:46%%'>%s</td><td style='text-align:right'>%s%% (%s/%s)</td></tr>"
		% (esc(a["topic"]), _pct_bar(a["pct"], band(a["pct"])), a["pct"], a["right"], a["total"])
		for a in sc["areas"][:8]
	)
	people_rows = "".join(
		"<tr><td>%s</td><td style='text-align:center'>%s</td><td style='text-align:center'>%s of %s</td>"
		"<td style='text-align:center'>%s</td></tr>"
		% (
			esc(p["trainee_name"]),
			"Yes" if p["attended"] else "—",
			p["complete"], p["total"],
			("%s%%" % p["average"]) if p["average"] is not None else "did not sit",
		)
		for p in sc["people"]
	)
	dist = "".join(
		"<tr><td>%s</td><td style='text-align:right'>%s</td></tr>" % (b["band"], b["n"])
		for b in sc["buckets"]
	)
	areas_block = (
		"<h2>Where the group is weakest</h2>"
		"<p class=note>Measured on first attempts only. A retake is taken by someone "
		"who has already seen the paper, so it flatters the score without proving the "
		"understanding.</p>"
		"<table>%s</table>" % area_rows
	) if sc["areas"] else ""
	return """<html><head><meta charset="utf-8"><style>
@page {{ size: A4 portrait; margin: 18mm 16mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #16211F; font-size: 11.5px; }}
h1 {{ font-size: 21px; margin: 0 0 2px; color: #0A473F; }}
h2 {{ font-size: 13px; margin: 22px 0 7px; color: #0A473F;
	border-bottom: 1px solid #DCE4E1; padding-bottom: 4px; }}
.sub {{ color: #6B7C77; font-size: 11px; margin-bottom: 16px; }}
.tiles {{ width: 100%; border-collapse: separate; border-spacing: 8px 0; }}
.tiles td {{ background: #F4F7F6; border-radius: 8px; padding: 10px 12px; width: 25%; }}
.tiles b {{ display: block; font-size: 22px; color: #0A473F; }}
.tiles span {{ font-size: 10px; color: #6B7C77; text-transform: uppercase; letter-spacing: 1px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .8px;
	color: #6B7C77; border-bottom: 1px solid #DCE4E1; padding: 5px 4px; }}
td {{ padding: 6px 4px; border-bottom: 1px solid #F0F4F2; vertical-align: middle; }}
.note {{ color: #6B7C77; font-size: 10.5px; margin: 4px 0 8px; }}
.foot {{ margin-top: 26px; color: #6B7C77; font-size: 10px;
	border-top: 1px solid #DCE4E1; padding-top: 8px; }}
</style></head><body>
<h1>{title}</h1>
<div class="sub">{customer} &middot; training scorecard &middot; issued {issued}{fac}</div>
<table class="tiles"><tr>
	<td><b>{attended}/{members}</b><span>attended</span></td>
	<td><b>{sat}</b><span>sat the assessment</span></td>
	<td><b>{pass_rate}</b><span>pass rate</span></td>
	<td><b>{average}</b><span>average score</span></td>
</tr></table>
<h2>By course</h2>
<table><tr><th>Course</th><th style="text-align:center">Sat</th><th style="text-align:center">Passed</th>
<th style="text-align:center">Pass rate</th><th style="text-align:center">Average</th></tr>{course_rows}</table>
{areas_block}
<h2>Score distribution</h2>
<table><tr><th>Band</th><th style="text-align:right">Results</th></tr>{dist}</table>
<h2>Roster</h2>
<table><tr><th>Name</th><th style="text-align:center">Session</th>
<th style="text-align:center">Courses complete</th><th style="text-align:center">Average</th></tr>{people_rows}</table>
<div class="foot">Assessments are proctored: questions are drawn at random from a larger bank,
served one at a time under a per-question time limit, and every result is recorded against a
verifiable certificate serial. Prepared by Xlevel Retail Systems Ltd &middot; CloudERP.One Academy.</div>
</body></html>""".format(
		title=esc(sc["title"]),
		customer=esc(sc["customer"]),
		issued=frappe.utils.format_date(today(), "d MMMM yyyy"),
		fac=(" &middot; facilitated by %s" % esc(sc["facilitator"])) if sc["facilitator"] else "",
		attended=sc["attended"], members=sc["members"], sat=sc["sat"],
		pass_rate=("%s%%" % sc["pass_rate"]) if sc["pass_rate"] is not None else "—",
		average=("%s%%" % sc["average"]) if sc["average"] is not None else "—",
		course_rows=course_rows, areas_block=areas_block, dist=dist, people_rows=people_rows,
	)


@frappe.whitelist()
def cohort_scorecard_publish(name):
	"""Render the sponsor PDF, file it on the client's shelf, narrate it."""
	from frappe.utils.pdf import get_pdf

	sc = cohort_scorecard(name)
	if not sc["sat"]:
		frappe.throw(_("Nobody has sat the assessment yet — there is no result to publish."))
	pdf = get_pdf(_scorecard_html(sc))
	safe = "".join(ch if ch.isalnum() else "_" for ch in sc["title"])[:48]
	fname = "Training_Scorecard_%s_%s.pdf" % (safe, sc["cohort"])
	f = frappe.get_doc(
		{"doctype": "File", "file_name": fname, "content": pdf, "is_private": 1}
	).insert(ignore_permissions=True)
	shelf = frappe.get_doc({
		"doctype": "Client Shelf Doc",
		"room": sc["room"],
		"title": _("Training scorecard — {0}").format(sc["title"]),
		"category": _("Training"),
		"file_url": f.file_url,
		"file_name": fname,
		"active": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		from duty_board.client_room import _post

		_post(
			frappe.get_doc("Client Room", sc["room"]),
			_("📊 Training scorecard published: “{0}” — {1} of {2} sat, {3} pass rate. It is on your Documents shelf.").format(
				sc["title"], sc["sat"], sc["members"],
				("%s%%" % sc["pass_rate"]) if sc["pass_rate"] is not None else "—",
			),
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "duty_board scorecard narration")
	return {"shelf": shelf.name, "file_url": f.file_url, "file_name": fname}


@frappe.whitelist()
def cohort_close(name):
	coh = _cohort(name)
	coh.db_set("status", "Closed")
	frappe.db.commit()
	return cohort_get(name)
