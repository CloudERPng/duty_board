# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""UAT: acceptance testing for implementation projects.

Model (decisions, 29 Jul 2026): template bank per product, maintained by
managers (desk grid on Duty UAT Template); engagements seed from the bank
then diverge freely. Clients test on the portal; a Fail spawns a Duty Issue
and blocks the case until resolution re-queues it. Sign-off may carry
explicit exceptions. A signed UAT gates Go-Live milestones — hard.
"""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from duty_board.permissions import require_staff

TERMINAL = ("Passed", "Waived")


def _is_manager():
	if "System Manager" in frappe.get_roles():
		return True
	try:
		from duty_board.accounting import _books_manager

		return _books_manager()
	except Exception:
		return False


def _post_room(room_name, text):
	from duty_board.client_room import _post

	_post(frappe.get_doc("Client Room", room_name), text)


def _push_clients(room_name, title, body):
	try:
		from duty_board.client_room import _push_room_clients

		_push_room_clients(frappe.get_doc("Client Room", room_name), title, body)
	except Exception:
		pass


def _rows(room):
	rows = frappe.get_all(
		"Duty UAT Case",
		filters={"room": room},
		fields=["name", "section", "title", "steps", "expected", "status", "issue", "waive_reason", "sort_order"],
		order_by="sort_order asc, creation asc",
		limit_page_length=0,
	)
	for r in rows:
		r["attempts"] = frappe.get_all(
			"Duty UAT Result",
			filters={"parent": r.name},
			fields=["attempt", "result", "observed", "evidence_url", "evidence_name", "by_user", "on", "on_behalf"],
			order_by="attempt asc",
		)
		for a in r["attempts"]:
			a["by_first"] = frappe.utils.get_fullname(a.by_user).split(" ")[0] if a.by_user else ""
			a["on"] = str(a["on"])[:16] if a["on"] else ""
	return rows


def _signoff(room):
	s = frappe.get_all(
		"Duty UAT Signoff",
		filters={"room": room},
		fields=["signed_full", "signed_at", "note", "exceptions", "passed", "waived", "total"],
		order_by="creation desc",
		limit_page_length=1,
	)
	if not s:
		return None
	s = s[0]
	s["signed_at"] = str(s["signed_at"])[:16]
	return s


def _progress(rows):
	c = {"total": len(rows), "passed": 0, "failed": 0, "blocked": 0, "waived": 0, "awaiting": 0}
	for r in rows:
		if r["status"] == "Passed":
			c["passed"] += 1
		elif r["status"] == "Waived":
			c["waived"] += 1
		elif r["status"] in ("Blocked", "Blocked by Issue"):
			c["blocked"] += 1
		elif r["status"] == "Failed":
			c["failed"] += 1
		else:
			c["awaiting"] += 1
	return c


def uat_gate_check(room, milestone_title):
	"""Hard gate: a Go-Live milestone cannot complete/approve while this
	room's UAT exists and is unsigned."""
	t = (milestone_title or "").lower()
	if "go-live" not in t and "go live" not in t and "golive" not in t:
		return
	if not frappe.db.count("Duty UAT Case", {"room": room}):
		return
	if not _signoff(room):
		frappe.throw(
			_("Go-Live is gated by UAT: the acceptance tests for this room have not been signed off by the client yet.")
		)


# ---------------- staff ----------------


@frappe.whitelist()
def uat_state(room):
	require_staff()
	rows = _rows(room)
	return {
		"rows": rows,
		"progress": _progress(rows),
		"signoff": _signoff(room),
		"manager": 1 if _is_manager() else 0,
		"templates": frappe.get_all(
			"Duty UAT Template", filters={"active": 1}, pluck="product", order_by="product asc"
		),
		"room_products": frappe.db.get_value("Client Room", room, "products") or "",
	}


@frappe.whitelist()
def uat_seed(room):
	"""Copy matching template cases into this engagement. Matches template
	products against the room's products (csv, case-insensitive); with no
	match it seeds every active template so nothing silently seeds empty."""
	require_staff()
	if frappe.db.count("Duty UAT Case", {"room": room}):
		frappe.throw(_("This room already has UAT cases — add more individually instead of reseeding."))
	products = [p.strip().lower() for p in (frappe.db.get_value("Client Room", room, "products") or "").split(",") if p.strip()]
	templates = frappe.get_all("Duty UAT Template", filters={"active": 1}, pluck="name")
	chosen = [t for t in templates if t.lower() in products] or templates
	if not chosen:
		frappe.throw(_("No active UAT templates exist yet — a manager can create them under Duty UAT Template."))
	order = 0
	made = 0
	for tpl in chosen:
		doc = frappe.get_doc("Duty UAT Template", tpl)
		for c in doc.cases:
			order += 10
			frappe.get_doc(
				{
					"doctype": "Duty UAT Case",
					"room": room,
					"section": c.section or doc.product,
					"title": c.title,
					"steps": c.steps,
					"expected": c.expected,
					"status": "Awaiting Client",
					"sort_order": order,
				}
			).insert(ignore_permissions=True)
			made += 1
	frappe.db.commit()
	_post_room(room, _("🧪 Acceptance testing is ready: {0} scenario(s) await your testing — see Projects on your portal.").format(made))
	_push_clients(room, _("🧪 Your acceptance tests are ready · Xlevel"), _("{0} scenarios to test").format(made))
	return uat_state(room)


@frappe.whitelist()
def uat_case_add(room, title, section=None, steps=None, expected=None):
	require_staff()
	last = frappe.get_all("Duty UAT Case", filters={"room": room}, fields=["max(sort_order) as m"])
	frappe.get_doc(
		{
			"doctype": "Duty UAT Case",
			"room": room,
			"section": (section or "").strip() or "General",
			"title": (title or "").strip()[:140],
			"steps": (steps or "").strip() or None,
			"expected": (expected or "").strip() or None,
			"status": "Awaiting Client",
			"sort_order": cint(last[0].m if last else 0) + 10,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return uat_state(room)


@frappe.whitelist()
def uat_case_update(name, title=None, section=None, steps=None, expected=None):
	require_staff()
	doc = frappe.get_doc("Duty UAT Case", name)
	if title and title.strip():
		doc.title = title.strip()[:140]
	if section is not None:
		doc.section = (section or "").strip() or "General"
	if steps is not None:
		doc.steps = (steps or "").strip() or None
	if expected is not None:
		doc.expected = (expected or "").strip() or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return uat_state(doc.room)


@frappe.whitelist()
def uat_case_delete(name):
	require_staff()
	doc = frappe.get_doc("Duty UAT Case", name)
	room = doc.room
	frappe.delete_doc("Duty UAT Case", name, ignore_permissions=True, force=True)
	frappe.db.commit()
	return uat_state(room)


@frappe.whitelist()
def uat_waive(name, reason):
	require_staff()
	if not _is_manager():
		frappe.throw(_("Only managers can waive an acceptance case."), frappe.PermissionError)
	doc = frappe.get_doc("Duty UAT Case", name)
	doc.status = "Waived"
	doc.waive_reason = (reason or "").strip()[:140] or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return uat_state(doc.room)


@frappe.whitelist()
def uat_record(name, result, observed=None):
	"""Staff record a result on the client's behalf (walkthrough sessions)."""
	require_staff()
	return record_result(name, result, observed, None, None, on_behalf=1)


def record_result(name, result, observed=None, evidence_url=None, evidence_name=None, on_behalf=0):
	if result not in ("Pass", "Fail", "Blocked"):
		frappe.throw(_("Result must be Pass, Fail or Blocked."))
	if result != "Pass" and not (observed or "").strip():
		frappe.throw(_("Tell us what happened — it becomes the defect record."))
	doc = frappe.get_doc("Duty UAT Case", name)
	if doc.status == "Waived":
		frappe.throw(_("This case was waived."))
	doc.append(
		"results",
		{
			"attempt": len(doc.results) + 1,
			"result": result,
			"observed": (observed or "").strip()[:500] or None,
			"evidence_url": evidence_url or None,
			"evidence_name": evidence_name or None,
			"by_user": frappe.session.user,
			"on": now_datetime(),
			"on_behalf": cint(on_behalf),
		},
	)
	if result == "Pass":
		doc.status = "Passed"
	elif result == "Blocked":
		doc.status = "Blocked"
	else:
		doc.status = "Failed"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	if result == "Fail":
		_spawn_defect(doc)
	return doc.room


def _spawn_defect(case):
	from duty_board.client_room import _new_client_issue

	room = frappe.get_doc("Client Room", case.room)
	last = case.results[-1] if case.results else None
	detail = _("UAT defect · {0}\nScenario: {1}\nExpected: {2}\nObserved: {3}").format(
		case.name, case.title, case.expected or "—", (last.observed if last else "") or "—"
	)
	issue = _new_client_issue(
		room,
		_("UAT: {0}").format(case.title)[:200],
		requested=0,
		raised_by=frappe.session.user,
		detail=detail,
		issue_type="Bug",
	)
	if last and last.evidence_url:
		f = frappe.db.get_value("File", {"file_url": last.evidence_url}, "name")
		if f:
			frappe.db.set_value(
				"File", f,
				{"attached_to_doctype": "Duty Issue", "attached_to_name": issue.name},
				update_modified=False,
			)
	case.db_set("issue", issue.name, update_modified=False)
	case.db_set("status", "Blocked by Issue", update_modified=False)
	frappe.db.commit()
	_post_room(case.room, _("🧪 Test failed: “{0}” — logged for fixing; it returns for retest once resolved.").format(case.title))


def on_issue_resolved(issue_name):
	"""Called from update_issue_status: re-queue the case for retest."""
	case = frappe.db.get_value(
		"Duty UAT Case", {"issue": issue_name, "status": "Blocked by Issue"}, "name"
	)
	if not case:
		return
	doc = frappe.get_doc("Duty UAT Case", case)
	doc.db_set("status", "Awaiting Client", update_modified=False)
	frappe.db.commit()
	_post_room(doc.room, _("🧪 Fixed and ready for retest: “{0}” — see Projects on your portal.").format(doc.title))
	_push_clients(doc.room, _("🧪 Ready for retest · Xlevel"), doc.title[:120])


# ---------------- client (non-whitelisted; called via client_room wrappers) ----------------


def client_state(room_name):
	rows = _rows(room_name)
	out_rows = [
		{
			"name": r["name"], "section": r["section"], "title": r["title"], "steps": r["steps"],
			"expected": r["expected"], "status": r["status"], "waive_reason": r["waive_reason"],
			"attempts": len(r["attempts"]),
			"last_observed": (r["attempts"][-1]["observed"] if r["attempts"] else None),
		}
		for r in rows
	]
	prog = _progress(rows)
	testable = [r for r in rows if r["status"] not in TERMINAL]
	signable = bool(rows) and not any(r["status"] == "Awaiting Client" for r in rows)
	return {"rows": out_rows, "progress": prog, "signoff": _signoff(room_name), "signable": 1 if signable else 0}


def client_result(room_name, name, result, observed=None, evidence_url=None, evidence_name=None):
	doc = frappe.db.get_value("Duty UAT Case", name, ["room", "status"], as_dict=True)
	if not doc or doc.room != room_name:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	record_result(name, result, observed, evidence_url, evidence_name, on_behalf=0)
	if result == "Pass":
		rows = _rows(room_name)
		if rows and all(r["status"] in TERMINAL for r in rows):
			_post_room(room_name, _("🧪 All acceptance scenarios settled — the sign-off awaits your administrator on the portal."))
	return client_state(room_name)


def client_sign(room_name, user, note=None):
	rows = _rows(room_name)
	if not rows:
		frappe.throw(_("No acceptance cases to sign."))
	if any(r["status"] == "Awaiting Client" for r in rows):
		frappe.throw(_("Some scenarios haven't been tested yet — every case needs a result (or a waiver) before sign-off."))
	if _signoff(room_name):
		frappe.throw(_("UAT is already signed off for this room."))
	exceptions = [r["title"] for r in rows if r["status"] not in TERMINAL]
	prog = _progress(rows)
	full = frappe.utils.get_fullname(user)
	frappe.get_doc(
		{
			"doctype": "Duty UAT Signoff",
			"room": room_name,
			"signed_by": user,
			"signed_full": full,
			"signed_at": now_datetime(),
			"note": (note or "").strip()[:300] or None,
			"exceptions": "; ".join(exceptions)[:500] or None,
			"passed": prog["passed"],
			"waived": prog["waived"],
			"total": prog["total"],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	_post_room(
		room_name,
		_("🧪✍ UAT SIGNED OFF by {0} — {1}/{2} passed{3}{4}").format(
			full, prog["passed"], prog["total"],
			_(", {0} waived").format(prog["waived"]) if prog["waived"] else "",
			_(" · with exceptions: {0}").format("; ".join(exceptions)) if exceptions else "",
		),
	)
	return client_state(room_name)
