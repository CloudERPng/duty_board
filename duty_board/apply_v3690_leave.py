#!/usr/bin/env python3
"""Duty Board v3.69.0 — leave management, replacing ERPNext leave.

Decisions locked (question bank A): weekdays only, no carry-over, full
days only, Annual type only (type field future-proofed), System Managers
approve, on-leave staff excluded from meeting slots + flagged in team
load + status shows On Leave, staff self-cancel future leave.

- Schema: Duty User Rate +annual_leave_days (Int). New doctype
  Duty Leave Request (user, leave_type, start/end, work_days, status,
  note, decided_by/on/note).
- New module duty_board/leave.py: my_leave, request_leave, cancel_leave,
  decide_leave, weekday math, balance validation, overlap guard.
- api.py _users_on_leave: SOURCE SWAP — was reading ERPNext Leave
  Application; now reads approved Duty Leave Requests. The board's
  existing "On Leave" status wiring downstream is untouched and now
  feeds from Duty Board itself. ERPNext leave is thereby abandoned.
- _meeting_slots: a requested staff member on approved leave that date
  -> no slots offered (same contract as the fully-booked rule).
- get_team_load: +on_leave flag; 🌴 shown beside the name.
- Me face: 🌴 Leave card — remaining/taken, request form (start, end,
  note), own requests with cancel, and for System Managers an
  approvals block (approve/decline with optional note).

Schema -> bench migrate && bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.68.3.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
API = "duty_board/api.py"
CR = "duty_board/client_room.py"
PROJ = "duty_board/projects.py"
URDT = "duty_board/duty_board/doctype/duty_user_rate/duty_user_rate.json"
LDIR = "duty_board/duty_board/doctype/duty_leave_request"
LEAVE = "duty_board/leave.py"
CHECK_ONLY = "--check" in sys.argv

LEAVE_DT = {
    "actions": [],
    "autoname": "hash",
    "creation": "2026-08-09 09:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": [
        "user", "leave_type", "start_date", "end_date", "work_days",
        "status", "note", "decided_by", "decided_on", "decision_note",
    ],
    "fields": [
        {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1},
        {"fieldname": "leave_type", "fieldtype": "Select", "label": "Type", "options": "Annual", "default": "Annual"},
        {"fieldname": "start_date", "fieldtype": "Date", "label": "Start", "reqd": 1},
        {"fieldname": "end_date", "fieldtype": "Date", "label": "End", "reqd": 1},
        {"fieldname": "work_days", "fieldtype": "Int", "label": "Work Days"},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Pending\nApproved\nDeclined\nCancelled", "default": "Pending"},
        {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
        {"fieldname": "decided_by", "fieldtype": "Link", "label": "Decided By", "options": "User"},
        {"fieldname": "decided_on", "fieldtype": "Datetime", "label": "Decided On"},
        {"fieldname": "decision_note", "fieldtype": "Small Text", "label": "Decision Note"},
    ],
    "links": [],
    "modified": "2026-08-09 09:00:00.000000",
    "modified_by": "Administrator",
    "module": "Duty Board",
    "name": "Duty Leave Request",
    "naming_rule": "Random",
    "owner": "Administrator",
    "permissions": [
        {"create": 1, "delete": 1, "read": 1, "report": 1, "role": "System Manager", "write": 1}
    ],
    "sort_field": "modified",
    "sort_order": "DESC",
    "states": [],
}

LEAVE_PY = '''"""Leave management — Duty Board native, replacing ERPNext leave.

Rules (locked at design time): entitlement per user in Duty Settings'
user-rate table (annual_leave_days, WORK days); weekdays only; no
carry-over (balance is per calendar YEAR of the leave's start date);
full days only; System Managers approve; staff cancel their own future
leave, admins cancel anything.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from duty_board.permissions import require_staff


def _is_admin(user=None):
	return "System Manager" in frappe.get_roles(user or frappe.session.user)


def _workdays(start, end):
	"""Weekdays (Mon-Fri) inclusive between two dates."""
	s, e = getdate(start), getdate(end)
	if e < s:
		return 0
	n, d = 0, s
	while d <= e:
		if d.weekday() < 5:
			n += 1
		d += timedelta(days=1)
	return n


def _entitlement(user):
	row = frappe.get_all(
		"Duty User Rate",
		filters={"user": user, "parenttype": "Duty Settings"},
		fields=["annual_leave_days"],
		limit=1,
	)
	return cint(row[0].annual_leave_days) if row else 0


def _taken(user, year):
	rows = frappe.get_all(
		"Duty Leave Request",
		filters={"user": user, "status": "Approved"},
		fields=["work_days", "start_date"],
	)
	return sum(cint(r.work_days) for r in rows if getdate(r.start_date).year == year)


def _overlaps(user, start, end, exclude=None):
	filters = {
		"user": user,
		"status": ["in", ["Pending", "Approved"]],
		"start_date": ["<=", end],
		"end_date": [">=", start],
	}
	if exclude:
		filters["name"] = ["!=", exclude]
	return bool(frappe.get_all("Duty Leave Request", filters=filters, limit=1))


def is_on_leave(user, date=None):
	d = getdate(date or today())
	return bool(
		frappe.get_all(
			"Duty Leave Request",
			filters={
				"user": user,
				"status": "Approved",
				"start_date": ["<=", d],
				"end_date": [">=", d],
			},
			limit=1,
		)
	)


def users_on_leave(user_ids, date=None):
	d = getdate(date or today())
	rows = frappe.get_all(
		"Duty Leave Request",
		filters={
			"user": ["in", list(user_ids)],
			"status": "Approved",
			"start_date": ["<=", d],
			"end_date": [">=", d],
		},
		fields=["user"],
	)
	return {r.user for r in rows}


def _my_requests(user, year):
	rows = frappe.get_all(
		"Duty Leave Request",
		filters={"user": user},
		fields=["name", "start_date", "end_date", "work_days", "status", "note"],
		order_by="start_date desc",
		limit=30,
	)
	out = []
	tday = getdate(today())
	for r in rows:
		sd = getdate(r.start_date)
		if sd.year < year and r.status in ("Declined", "Cancelled"):
			continue  # keep history light: old rejections drop off
		r.start_date = str(r.start_date)
		r.end_date = str(r.end_date)
		r.cancellable = 1 if (r.status in ("Pending", "Approved") and sd > tday) else 0
		out.append(r)
	return out


@frappe.whitelist()
def my_leave():
	require_staff()
	user = frappe.session.user
	year = getdate(today()).year
	ent = _entitlement(user)
	taken = _taken(user, year)
	data = {
		"entitlement": ent,
		"taken": taken,
		"remaining": max(ent - taken, 0),
		"year": year,
		"requests": _my_requests(user, year),
		"is_admin": 1 if _is_admin() else 0,
	}
	if data["is_admin"]:
		pend = frappe.get_all(
			"Duty Leave Request",
			filters={"status": "Pending"},
			fields=["name", "user", "start_date", "end_date", "work_days", "note"],
			order_by="start_date asc",
		)
		for p in pend:
			p.full_name = frappe.utils.get_fullname(p.user)
			p.start_date = str(p.start_date)
			p.end_date = str(p.end_date)
			p.remaining = max(_entitlement(p.user) - _taken(p.user, getdate(p.start_date).year), 0)
		data["pending"] = pend
	return data


@frappe.whitelist()
def request_leave(start_date, end_date, note=None):
	require_staff()
	user = frappe.session.user
	s, e = getdate(start_date), getdate(end_date)
	if e < s:
		frappe.throw(_("End date is before start date."))
	if s < getdate(today()):
		frappe.throw(_("Leave cannot start in the past."))
	days = _workdays(s, e)
	if not days:
		frappe.throw(_("That range covers no work days."))
	if _overlaps(user, s, e):
		frappe.throw(_("You already have leave requested or approved in that period."))
	remaining = _entitlement(user) - _taken(user, s.year)
	if days > remaining:
		frappe.throw(_("Not enough leave left: {0} day(s) requested, {1} remaining.").format(days, max(remaining, 0)))
	frappe.get_doc(
		{
			"doctype": "Duty Leave Request",
			"user": user,
			"leave_type": "Annual",
			"start_date": s,
			"end_date": e,
			"work_days": days,
			"status": "Pending",
			"note": (note or "").strip()[:500] or None,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return my_leave()


@frappe.whitelist()
def cancel_leave(name):
	require_staff()
	doc = frappe.get_doc("Duty Leave Request", name)
	own = doc.user == frappe.session.user
	if not own and not _is_admin():
		frappe.throw(_("Not yours to cancel."))
	if doc.status not in ("Pending", "Approved"):
		frappe.throw(_("Already {0}.").format(doc.status.lower()))
	if own and not _is_admin() and getdate(doc.start_date) <= getdate(today()):
		frappe.throw(_("Leave that has started can only be cancelled by an administrator."))
	doc.db_set("status", "Cancelled", update_modified=True)
	frappe.db.commit()
	return my_leave()


@frappe.whitelist()
def decide_leave(name, approve, note=None):
	require_staff()
	if not _is_admin():
		frappe.throw(_("Only administrators approve leave."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Leave Request", name)
	if doc.status != "Pending":
		frappe.throw(_("Already decided."))
	if cint(approve):
		remaining = _entitlement(doc.user) - _taken(doc.user, getdate(doc.start_date).year)
		if cint(doc.work_days) > remaining:
			frappe.throw(_("Balance no longer sufficient: {0} requested, {1} left.").format(doc.work_days, max(remaining, 0)))
		doc.db_set("status", "Approved", update_modified=True)
	else:
		doc.db_set("status", "Declined", update_modified=True)
	doc.db_set("decided_by", frappe.session.user, update_modified=False)
	doc.db_set("decided_on", frappe.utils.now(), update_modified=False)
	if note:
		doc.db_set("decision_note", (note or "").strip()[:500], update_modified=False)
	frappe.db.commit()
	return my_leave()
'''

# --- api.py: source swap -----------------------------------------------------
SWAP_OLD = '''def _users_on_leave(user_ids):
\t"""Users with an approved Leave Application covering their local today."""
\tif not frappe.db.exists("DocType", "Leave Application"):
\t\treturn set()
\temp_map = {
\t\te.name: e.user_id
\t\tfor e in frappe.get_all(
\t\t\t"Employee",
\t\t\tfilters={"user_id": ["in", user_ids]},
\t\t\tfields=["name", "user_id"],
\t\t)
\t}
\tif not emp_map:
\t\treturn set()
\ton_leave = set()
\tleaves = frappe.get_all(
\t\t"Leave Application",
\t\tfilters={
\t\t\t"employee": ["in", list(emp_map.keys())],
\t\t\t"docstatus": 1,
\t\t\t"status": "Approved",
\t\t\t"from_date": ["<=", add_days(getdate(today()), 1)],
\t\t\t"to_date": [">=", add_days(getdate(today()), -1)],
\t\t},
\t\tfields=["employee", "from_date", "to_date"],
\t)
\tfor lv in leaves:
\t\tuid = emp_map.get(lv.employee)
\t\tif not uid:
\t\t\tcontinue
\t\tlocal_today = user_today(uid)
\t\tif getdate(lv.from_date) <= local_today <= getdate(lv.to_date):
\t\t\ton_leave.add(uid)
\treturn on_leave'''
SWAP_NEW = '''def _users_on_leave(user_ids):
\t"""Users on approved Duty Board leave covering their local today.
\t(Source-swapped from ERPNext Leave Application — leave now lives here.)"""
\trows = frappe.get_all(
\t\t"Duty Leave Request",
\t\tfilters={
\t\t\t"user": ["in", list(user_ids)],
\t\t\t"status": "Approved",
\t\t\t"start_date": ["<=", add_days(getdate(today()), 1)],
\t\t\t"end_date": [">=", add_days(getdate(today()), -1)],
\t\t},
\t\tfields=["user", "start_date", "end_date"],
\t)
\ton_leave = set()
\tfor lv in rows:
\t\tlocal_today = user_today(lv.user)
\t\tif getdate(lv.start_date) <= local_today <= getdate(lv.end_date):
\t\t\ton_leave.add(lv.user)
\treturn on_leave'''

# --- client_room.py: meeting slots exclude on-leave staff -------------------
SLOTS_OLD = '''\tif d.weekday() >= 5:  # Sat/Sun — the banner's promise holds
\t\treturn []
\tblocked = set()'''
SLOTS_NEW = '''\tif d.weekday() >= 5:  # Sat/Sun — the banner's promise holds
\t\treturn []
\tfrom duty_board.leave import is_on_leave
\tfor u in staff_list:
\t\tif is_on_leave(u, d):
\t\t\treturn []  # a requested attendee is on leave that day
\tblocked = set()'''

# --- projects.py: team load on_leave flag -----------------------------------
TL_OLD = '''\tout = []
\tfor user, g in load.items():
\t\tout.append({
\t\t\t"user": None if user == "__unassigned__" else user,'''
TL_NEW = '''\tfrom duty_board.leave import users_on_leave
\t_leave_set = users_on_leave([u for u in load if u != "__unassigned__"]) if load else set()
\tout = []
\tfor user, g in load.items():
\t\tout.append({
\t\t\t"user": None if user == "__unassigned__" else user,
\t\t\t"on_leave": 1 if user in _leave_set else 0,'''

# --- JS: team load 🌴 chip ---------------------------------------------------
TLJS_OLD = '<td><b style="color:${p.user ? this.user_color(p.user) : "#8a958f"}">${esc(p.full_name)}</b></td>'
TLJS_NEW = '<td><b style="color:${p.user ? this.user_color(p.user) : "#8a958f"}">${esc(p.full_name)}</b>${p.on_leave ? " 🌴" : ""}</td>'

# --- JS: leave card placeholder on the Me face ------------------------------
PLACE_OLD = '''\t\t\t</div>` : ""}
\t\t\t<div class="duty-me-cal">'''
PLACE_NEW = '''\t\t\t</div>` : ""}
\t\t\t<div class="duty-me-leave"></div>
\t\t\t<div class="duty-me-cal">'''

# --- JS: loader call at bind time -------------------------------------------
LOAD_OLD = '\t\tthis.$me.find(".duty-req-sg").on("click", (e) =>'
LOAD_NEW = '''\t\tthis._load_leave_card();
\t\tthis.$me.find(".duty-req-sg").on("click", (e) =>'''

# --- JS: the leave card methods, before refresh_me --------------------------
METH_OLD = '\trefresh_me(month) {'
METH_NEW = '''\t_load_leave_card() {
\t\tconst $host = this.$me.find(".duty-me-leave");
\t\tif (!$host.length) return;
\t\tfrappe.call({
\t\t\tmethod: "duty_board.leave.my_leave",
\t\t\tcallback: (r) => r.message && this._render_leave_card(r.message),
\t\t});
\t}

\t_render_leave_card(L) {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst $host = this.$me.find(".duty-me-leave");
\t\tif (!$host.length) return;
\t\tconst PILL = { Pending: "⏳", Approved: "✅", Declined: "✖", Cancelled: "◌" };
\t\tconst reqs = (L.requests || []).map((q) => `
\t\t\t<div class="duty-lv-row">
\t\t\t\t<span class="duty-lv-st duty-lv-${q.status.toLowerCase()}">${PILL[q.status] || ""} ${__(q.status)}</span>
\t\t\t\t<b>${esc(q.start_date)} → ${esc(q.end_date)}</b>
\t\t\t\t<span class="text-muted">${q.work_days} ${__("day(s)")}${q.note ? " · " + esc(q.note) : ""}</span>
\t\t\t\t${q.cancellable ? `<a class="duty-lv-cancel" data-id="${q.name}" title="${__("Cancel")}">✕</a>` : ""}
\t\t\t</div>`).join("");
\t\tconst pend = (L.pending || []).map((p) => `
\t\t\t<div class="duty-lv-row">
\t\t\t\t<b>${esc(p.full_name)}</b>
\t\t\t\t<span>${esc(p.start_date)} → ${esc(p.end_date)} · ${p.work_days} ${__("day(s)")}</span>
\t\t\t\t<span class="text-muted">${p.remaining} ${__("left")}${p.note ? " · " + esc(p.note) : ""}</span>
\t\t\t\t<span class="duty-req-btns">
\t\t\t\t\t<button class="btn btn-xs btn-primary duty-lv-ok" data-id="${p.name}">✓ ${__("Approve")}</button>
\t\t\t\t\t<button class="btn btn-xs btn-default duty-lv-no" data-id="${p.name}">✗ ${__("Decline")}</button>
\t\t\t\t</span>
\t\t\t</div>`).join("");
\t\t$host.html(`
\t\t\t<div class="duty-me-reqs duty-lv-card">
\t\t\t\t<h4>🌴 ${__("Leave")} <span class="duty-lv-bal">${L.remaining} ${__("of")} ${L.entitlement} ${__("days left")} · ${L.taken} ${__("taken in")} ${L.year}</span></h4>
\t\t\t\t${reqs || `<div class="text-muted" style="font-size:12.5px">${__("No leave requested this year.")}</div>`}
\t\t\t\t<div class="duty-lv-ask">
\t\t\t\t\t<input type="date" class="form-control input-sm duty-lv-s">
\t\t\t\t\t<span>→</span>
\t\t\t\t\t<input type="date" class="form-control input-sm duty-lv-e">
\t\t\t\t\t<input type="text" class="form-control input-sm duty-lv-note" placeholder="${__("Note (optional)")}">
\t\t\t\t\t<button class="btn btn-xs btn-primary duty-lv-go">🌴 ${__("Request leave")}</button>
\t\t\t\t</div>
\t\t\t\t${L.is_admin && (L.pending || []).length ? `<h4 style="margin-top:14px">🗂 ${__("Awaiting your approval")}</h4>${pend}` : ""}
\t\t\t</div>`);
\t\tconst redo = (r) => r.message && this._render_leave_card(r.message);
\t\t$host.find(".duty-lv-go").on("click", () => {
\t\t\tconst s = $host.find(".duty-lv-s").val();
\t\t\tconst e = $host.find(".duty-lv-e").val();
\t\t\tif (!s || !e) return frappe.show_alert({ message: __("Pick both dates."), indicator: "orange" });
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.leave.request_leave",
\t\t\t\targs: { start_date: s, end_date: e, note: $host.find(".duty-lv-note").val() || null },
\t\t\t\tcallback: (r) => { frappe.show_alert({ message: __("Leave requested."), indicator: "green" }); redo(r); },
\t\t\t});
\t\t});
\t\t$host.find(".duty-lv-cancel").on("click", (e) =>
\t\t\tfrappe.confirm(__("Cancel this leave?"), () =>
\t\t\t\tfrappe.call({ method: "duty_board.leave.cancel_leave", args: { name: $(e.currentTarget).data("id") }, callback: redo }))
\t\t);
\t\t$host.find(".duty-lv-ok").on("click", (e) =>
\t\t\tfrappe.call({ method: "duty_board.leave.decide_leave", args: { name: $(e.currentTarget).data("id"), approve: 1 }, callback: (r) => { frappe.show_alert({ message: __("Approved."), indicator: "green" }); redo(r); } })
\t\t);
\t\t$host.find(".duty-lv-no").on("click", (e) => {
\t\t\tconst id = $(e.currentTarget).data("id");
\t\t\tfrappe.prompt(
\t\t\t\t[{ fieldname: "note", fieldtype: "Small Text", label: __("Reason (optional)") }],
\t\t\t\t(v) => frappe.call({ method: "duty_board.leave.decide_leave", args: { name: id, approve: 0, note: v.note || null }, callback: redo }),
\t\t\t\t__("Decline leave"), __("Decline")
\t\t\t);
\t\t});
\t}

\trefresh_me(month) {'''

# --- JS: CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-pf-risks { font-size: 11px; color: #B45309; font-weight: 700; margin-top: 3px; }'
CSS_NEW = '''\t\t\t.duty-pf-risks { font-size: 11px; color: #B45309; font-weight: 700; margin-top: 3px; }
\t\t\t.duty-lv-card h4 { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
\t\t\t.duty-lv-bal { font-size: 12.5px; font-weight: 600; color: #0E8A63; }
\t\t\t.duty-lv-row { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; padding: 6px 0; border-bottom: 1px dashed var(--border-color, #eee); font-size: 13px; }
\t\t\t.duty-lv-row:last-child { border-bottom: none; }
\t\t\t.duty-lv-st { font-weight: 700; font-size: 12px; }
\t\t\t.duty-lv-approved { color: #0E8A63; }
\t\t\t.duty-lv-pending { color: #B45309; }
\t\t\t.duty-lv-declined, .duty-lv-cancelled { color: #9aa4a0; }
\t\t\t.duty-lv-cancel { cursor: pointer; opacity: .6; margin-left: auto; }
\t\t\t.duty-lv-cancel:hover { opacity: 1; }
\t\t\t.duty-lv-ask { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 10px; }
\t\t\t.duty-lv-ask input[type="date"] { max-width: 150px; }
\t\t\t.duty-lv-ask .duty-lv-note { max-width: 220px; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, API, CR, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if os.path.exists(os.path.join(root, LEAVE)):
        print("Already applied. Nothing to do.")
        return
    if '"3.68.3"' not in files[INIT]:
        sys.exit("ABORT: not at v3.68.3.")

    checks = [
        (API, SWAP_OLD, "leave source swap"), (CR, SLOTS_OLD, "meeting slots"),
        (PROJ, TL_OLD, "team load flag"), (JS, TLJS_OLD, "team load chip"),
        (JS, PLACE_OLD, "me-face placeholder"), (JS, LOAD_OLD, "loader call"),
        (JS, METH_OLD, "leave card methods"), (JS, CSS_OLD, "css"),
    ]
    problems = [f"  [{files[f].count(o)}] {label}" for f, o, label in checks if files[f].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(checks)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # user-rate column
    with io.open(os.path.join(root, URDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "annual_leave_days" for fl in dt["fields"]):
        dt["fields"].append({"fieldname": "annual_leave_days", "fieldtype": "Int", "label": "Annual Leave (work days)", "in_list_view": 1})
        if "field_order" in dt:
            dt["field_order"].append("annual_leave_days")
        with io.open(os.path.join(root, URDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    print("  Duty User Rate +annual_leave_days")

    # leave request doctype
    ldir = os.path.join(root, LDIR)
    os.makedirs(ldir, exist_ok=True)
    with io.open(os.path.join(ldir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(ldir, "duty_leave_request.json"), "w", encoding="utf-8") as f:
        json.dump(LEAVE_DT, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(ldir, "duty_leave_request.py"), "w", encoding="utf-8") as f:
        f.write("import frappe\nfrom frappe.model.document import Document\n\n\nclass DutyLeaveRequest(Document):\n\tpass\n")
    print("  doctype: Duty Leave Request created")

    with io.open(os.path.join(root, LEAVE), "w", encoding="utf-8") as f:
        f.write(LEAVE_PY)
    print("  duty_board/leave.py created")

    files[API] = files[API].replace(SWAP_OLD, SWAP_NEW, 1)
    files[CR] = files[CR].replace(SLOTS_OLD, SLOTS_NEW, 1)
    files[PROJ] = files[PROJ].replace(TL_OLD, TL_NEW, 1)
    js = files[JS]
    for o, n in [(TLJS_OLD, TLJS_NEW), (PLACE_OLD, PLACE_NEW), (LOAD_OLD, LOAD_NEW), (METH_OLD, METH_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    files[JS] = js
    files[INIT] = files[INIT].replace('"3.68.3"', '"3.69.0"')

    for p in (API, CR, PROJ, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  api.py source-swapped, meeting slots + team load integrated, Me-face card wired")
    print("wrote __init__.py -> 3.69.0")


if __name__ == "__main__":
    main()
