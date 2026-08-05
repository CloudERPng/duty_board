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


def _code_prefix(template):
	base = (template or "").replace("Zhift", "").replace("zhift", "").strip()
	base = "".join(ch for ch in base if ch.isalnum()).upper()
	return (base or "UAT")[:4]


def _next_code(room, prefix):
	existing = frappe.get_all(
		"Duty UAT Case", filters={"room": room, "code": ["like", prefix + "-%"]}, pluck="code"
	)
	n = 0
	for c in existing:
		try:
			n = max(n, int(str(c).split("-")[-1]))
		except Exception:
			pass
	return f"{prefix}-{n + 1:02d}"


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
		fields=["name", "section", "title", "steps", "expected", "status", "issue", "waive_reason", "sort_order", "template", "code"],
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
		"uat_due": str(frappe.db.get_value("Client Room", room, "uat_due") or "") or None,
	}


@frappe.whitelist()
def uat_seed(room, templates=None, due=None):
	"""Copy chosen template banks into this engagement. `templates` is a csv
	of Duty UAT Template names — the staff picker supplies it. Templates
	already seeded into this room are skipped, so a second product's bank
	can be added later without duplicating the first."""
	require_staff()
	import json as _json

	if isinstance(templates, str) and templates.strip().startswith("["):
		chosen = [t for t in _json.loads(templates) if t]
	else:
		chosen = [t.strip() for t in (templates or "").split(",") if t.strip()]
	if not chosen:
		frappe.throw(_("Pick at least one template to seed."))
	already = set(
		frappe.get_all(
			"Duty UAT Case", filters={"room": room, "template": ["is", "set"]}, pluck="template", distinct=True
		)
	)
	order = cint(
		frappe.get_all("Duty UAT Case", filters={"room": room}, fields=["max(sort_order) as m"])[0].m or 0
	)
	made, skipped = 0, []
	for tpl in chosen:
		if not frappe.db.exists("Duty UAT Template", tpl):
			frappe.throw(_("Unknown template: {0}").format(tpl))
		if tpl in already:
			skipped.append(tpl)
			continue
		doc = frappe.get_doc("Duty UAT Template", tpl)
		prefix = _code_prefix(tpl)
		seq = 0
		for c in doc.cases:
			order += 10
			seq += 1
			frappe.get_doc(
				{
					"doctype": "Duty UAT Case",
					"room": room,
					"code": f"{prefix}-{seq:02d}",
					"template": tpl,
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
	if due:
		frappe.db.set_value("Client Room", room, "uat_due", due, update_modified=False)
	if made:
		_d = due or frappe.db.get_value("Client Room", room, "uat_due")
		_post_room(room, _("🧪 Acceptance testing is ready: {0} scenario(s) await your testing{1} — see Projects on your portal.").format(
			made, _(" · target: {0}").format(_d) if _d else ""))
		_push_clients(room, _("🧪 Your acceptance tests are ready · Xlevel"), _("{0} scenarios to test").format(made))
	if skipped:
		frappe.msgprint(_("Already seeded, skipped: {0}").format(", ".join(skipped)))
	return uat_state(room)


@frappe.whitelist()
def uat_unseed(room, template):
	"""Manager undo: remove a template's UNTESTED cases from a room (cases
	with recorded attempts are kept — history is never deleted)."""
	require_staff()
	if not _is_manager():
		frappe.throw(_("Only managers can unseed."), frappe.PermissionError)
	victims = frappe.get_all(
		"Duty UAT Case", filters={"room": room, "template": template}, fields=["name"]
	)
	removed, kept = 0, 0
	for v in victims:
		if frappe.db.count("Duty UAT Result", {"parent": v.name}):
			kept += 1
			continue
		frappe.delete_doc("Duty UAT Case", v.name, ignore_permissions=True, force=True)
		removed += 1
	frappe.db.commit()
	if kept:
		frappe.msgprint(_("{0} tested case(s) kept — attempt history is never deleted.").format(kept))
	return uat_state(room)


@frappe.whitelist()
def uat_case_add(room, title, section=None, steps=None, expected=None):
	require_staff()
	last = frappe.get_all("Duty UAT Case", filters={"room": room}, fields=["max(sort_order) as m"])
	frappe.get_doc(
		{
			"doctype": "Duty UAT Case",
			"room": room,
			"code": _next_code(room, "ADD"),
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
		_("UAT {0}: {1}").format(case.code or case.name, case.title)[:200],
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
	frappe.db.set_value("Duty Issue", issue.name, "severity", "High", update_modified=False)
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
			"name": r["name"], "code": r["code"], "section": r["section"], "title": r["title"], "steps": r["steps"],
			"expected": r["expected"], "status": r["status"], "waive_reason": r["waive_reason"],
			"attempts": len(r["attempts"]),
			"last_observed": (r["attempts"][-1]["observed"] if r["attempts"] else None),
		}
		for r in rows
	]
	prog = _progress(rows)
	testable = [r for r in rows if r["status"] not in TERMINAL]
	signable = bool(rows) and not any(r["status"] == "Awaiting Client" for r in rows)
	return {
		"rows": out_rows,
		"progress": prog,
		"signoff": _signoff(room_name),
		"signable": 1 if signable else 0,
		"uat_due": str(frappe.db.get_value("Client Room", room_name, "uat_due") or "") or None,
	}


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
	try:
		_issue_certificate(room_name, user, full, note, exceptions, prog, rows)
	except Exception:
		frappe.log_error(frappe.get_traceback()[:3000], "uat certificate")
	_post_room(
		room_name,
		_("🧪✍ UAT SIGNED OFF by {0} — {1}/{2} passed{3}{4}").format(
			full, prog["passed"], prog["total"],
			_(", {0} waived").format(prog["waived"]) if prog["waived"] else "",
			_(" · with exceptions: {0}").format("; ".join(exceptions)) if exceptions else "",
		),
	)
	return client_state(room_name)


def heartbeat():
	"""Hourly-called, daily-acting: nudge rooms whose UAT has stalled —
	open cases, no result recorded for 3+ days, not nudged in 3+ days."""
	from frappe.utils import add_days, getdate, today

	tdy = getdate(today())
	rooms = frappe.get_all(
		"Duty UAT Case", filters={"status": "Awaiting Client"}, pluck="room", distinct=True
	)
	for room in rooms:
		nudged = frappe.db.get_value("Client Room", room, "uat_nudged_on")
		if nudged and (tdy - getdate(nudged)).days < 3:
			continue
		last = frappe.db.sql(
			"""select max(r.`on`) from `tabDuty UAT Result` r
			join `tabDuty UAT Case` c on c.name = r.parent where c.room = %s""",
			(room,),
		)[0][0]
		anchor = getdate(str(last)[:10]) if last else None
		if anchor is None:
			first = frappe.db.get_value(
				"Duty UAT Case", {"room": room}, "min(creation)"
			)
			anchor = getdate(str(first)[:10]) if first else tdy
		if (tdy - anchor).days < 3:
			continue
		n = frappe.db.count("Duty UAT Case", {"room": room, "status": "Awaiting Client"})
		due = frappe.db.get_value("Client Room", room, "uat_due")
		left = (getdate(due) - tdy).days if due else None
		_post_room(
			room,
			_("🧪 A gentle reminder — {0} test scenario(s) still await you{1}. Stuck on any? Request a walkthrough from the testing card.").format(
				n, _(" · {0} day(s) to your target of {1}").format(left, due) if due and left is not None and left >= 0 else (_(" · your target date {0} has passed").format(due) if due else "")
			),
		)
		_push_clients(room, _("🧪 Your tests are waiting · Xlevel"), _("{0} scenarios still to go").format(n))
		frappe.db.set_value("Client Room", room, "uat_nudged_on", tdy, update_modified=False)
	frappe.db.commit()


def _issue_certificate(room_name, user, full, note, exceptions, prog, rows):
	from frappe.utils.pdf import get_pdf

	room = frappe.get_doc("Client Room", room_name)
	when = now_datetime().strftime("%d %B %Y, %H:%M")
	defects = frappe.get_all(
		"Duty UAT Case",
		filters={"room": room_name, "issue": ["is", "set"]},
		fields=["code", "title", "issue", "status"],
	)
	def row(r):
		res = {"Passed": "PASS", "Waived": "WAIVED", "Failed": "FAIL", "Blocked": "BLOCKED", "Blocked by Issue": "DEFECT OPEN"}.get(r["status"], r["status"])
		col = {"Passed": "#2E7D5B", "Waived": "#6b7280"}.get(r["status"], "#B0443C")
		return (
			f"<tr><td style='color:#96A09B'>{frappe.utils.escape_html(r.get('code') or '')}</td>"
			f"<td>{frappe.utils.escape_html(r['title'])}</td>"
			f"<td style='color:#96A09B'>{len(r['attempts'])}×</td>"
			f"<td style='font-weight:700;color:{col}'>{res}</td></tr>"
		)
	sections = {}
	for r in rows:
		sections.setdefault(r["section"] or "General", []).append(r)
	body_rows = ""
	for s, rs in sections.items():
		body_rows += f"<tr><td colspan='4' style='padding-top:12px;font-size:9px;letter-spacing:2px;color:#0E5A4A;font-weight:700'>{frappe.utils.escape_html(s.upper())}</td></tr>"
		body_rows += "".join(row(r) for r in rs)
	html = f"""<html><head><style>
		body {{ font-family: Georgia, 'Times New Roman', serif; color: #182420; margin: 40px 46px; }}
		.top {{ border-bottom: 3px solid #0E5A4A; padding-bottom: 14px; }}
		.brand {{ font-size: 20px; font-weight: bold; color: #0E5A4A; }}
		h1 {{ font-size: 26px; margin: 26px 0 4px; font-weight: normal; }}
		.mut {{ color: #6B7772; font-size: 12px; }}
		table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
		td {{ padding: 5px 6px; border-bottom: 1px solid #E8E5DD; vertical-align: top; }}
		.box {{ border: 1px solid #E8E5DD; padding: 12px 14px; margin-top: 16px; font-size: 12.5px; }}
		.sig {{ margin-top: 30px; border-top: 1px solid #182420; display: inline-block; padding-top: 6px; font-size: 13px; }}
	</style></head><body>
	<div class="top"><span class="brand">Xlevel Retail Systems</span>
	<span style="float:right" class="mut">CloudERP.One · xlevel.clouderp.one</span></div>
	<h1>Certificate of User Acceptance</h1>
	<div class="mut">{frappe.utils.escape_html(room.customer)} · {frappe.utils.escape_html(room.unit or "General")} · issued {when} (WAT)</div>
	<div class="box"><b>{prog["passed"]} of {prog["total"]}</b> scenarios passed{f" · {prog['waived']} waived by agreement" if prog["waived"] else ""}{f" · {len(defects)} defect(s) were raised and worked during testing" if defects else ""}.</div>
	<table><tr style="font-size:9px;letter-spacing:1px;color:#6B7772"><td>CODE</td><td>SCENARIO</td><td>TESTED</td><td>RESULT</td></tr>{body_rows}</table>
	{f'<div class="box" style="border-color:#A96F1A"><b>Accepted with exceptions:</b> {frappe.utils.escape_html("; ".join(exceptions))}</div>' if exceptions else ""}
	{f'<div class="box"><b>Client note:</b> {frappe.utils.escape_html(note)}</div>' if (note or "").strip() else ""}
	<p style="font-size:13px;margin-top:22px">The undersigned confirms, on behalf of {frappe.utils.escape_html(room.customer)},
	that the system behaves as agreed for the scenarios above and formally accepts the implementation
	{"subject to the exceptions listed" if exceptions else "without exception"}.</p>
	<div class="sig"><b>{frappe.utils.escape_html(full)}</b><br><span class="mut">{when} · recorded electronically on the Xlevel Client Portal</span></div>
	</body></html>"""
	pdf = get_pdf(html)
	fname = f"UAT-Acceptance-{room.customer.replace(' ', '-')[:40]}-{now_datetime().strftime('%Y%m%d-%H%M')}.pdf"
	fdoc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"is_private": 1,
			"content": pdf,
			"attached_to_doctype": "Client Room",
			"attached_to_name": room.name,
		}
	).insert(ignore_permissions=True)
	frappe.get_doc(
		{
			"doctype": "Client Shelf Doc",
			"room": room.name,
			"title": _("Certificate of User Acceptance"),
			"category": "Certificates",
			"file_url": fdoc.file_url,
			"file_name": fname,
			"active": 1,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	admins = [
		m.user
		for m in frappe.get_all(
			"Client Room Member", filters={"room": room.name, "active": 1, "is_admin": 1}, fields=["user"]
		)
		if m.user
	]
	if admins:
		try:
			frappe.sendmail(
				recipients=admins,
				subject=_("Certificate of User Acceptance — {0}").format(room.customer),
				message=_(
					"<p>Dear {0},</p><p>Thank you — your acceptance testing is formally signed off. "
					"Your Certificate of User Acceptance is attached, and a copy lives permanently in "
					"the <b>Documents</b> tab of your portal.</p><p>Warm regards,<br>Xlevel Retail Systems</p>"
				).format(frappe.utils.get_fullname(admins[0]).split(" ")[0]),
				attachments=[{"fname": fname, "fcontent": pdf}],
			)
		except Exception:
			frappe.log_error(frappe.get_traceback()[:2000], "uat certificate mail")
