#!/usr/bin/env python3
"""Duty Board v3.208.0 — THE COHORT SPINE.

The academy could assign a course to one person at a time and nothing more.
The paid model is a group: Client X's staff run Course Y between these dates
with this facilitator, attend a live session, read the manual, then sit the
exam inside a window. Nothing in the software represented that group, so the
schedule, the attendance, the exam window, the group result and the invoice
all lived in someone's head.

This patch adds the object everything else hangs from.

New doctypes
  Duty Training Cohort (COH-YYYY-#####): room, title, track or single module,
    facilitator, session_on, exam window opens_on/closes_on, status
    (Draft -> Enrolled -> In Progress -> Closed), members child table.
  Duty Training Cohort Member: trainee, attended, enrolled.
  Duty Training Record: +cohort (Data) — the back-link that makes a group
    result computable later.

New module duty_board/cohort.py (house rule: new domains get new modules)
  cohort_list / cohort_get / cohort_create / cohort_set / cohort_add_member /
  cohort_remove_member / cohort_enrol / cohort_attendance / cohort_close.
  Enrolment is idempotent: it reuses any Duty Training Record the trainee
  already has for that module and stamps the cohort on it rather than
  creating a duplicate, so a cohort can be re-run after adding a late joiner.

Exam window
  _exam_gate gains the record and refuses a start outside the cohort's window.
  Records with no cohort, or a cohort with no dates, behave exactly as before.
  The window is enforced on the CLIENT path only, as with attempt policy —
  staff testing stays ungated.

Staff UI
  A 👥 Cohorts primary action on the room's 🎓 Training Academy dialog: list
  with status and enrolment counts, and a detail view for scheduling, member
  management, attendance marking, enrolment and closing.

Deploy: apply -> bench migrate (new doctypes) -> bench build --app duty_board
-> clear-cache + clear-website-cache -> restart. Anchored, idempotent.
Requires v3.207.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
COHORT = "duty_board/cohort.py"
TRDT = "duty_board/duty_board/doctype/duty_training_record/duty_training_record.json"
DT_DIR = "duty_board/duty_board/doctype"
CHECK_ONLY = "--check" in sys.argv


COHORT_JSON = {
    "actions": [],
    "autoname": "format:COH-{YYYY}-{#####}",
    "creation": "2026-08-13 10:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": [
        "room", "title", "status", "track", "module", "facilitator",
        "session_on", "opens_on", "closes_on", "note", "members",
    ],
    "fields": [
        {"fieldname": "room", "fieldtype": "Link", "label": "Client Room",
         "options": "Client Room", "reqd": 1, "in_list_view": 1},
        {"fieldname": "title", "fieldtype": "Data", "label": "Title",
         "reqd": 1, "in_list_view": 1},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status",
         "options": "Draft\nEnrolled\nIn Progress\nClosed", "default": "Draft",
         "in_list_view": 1},
        {"fieldname": "track", "fieldtype": "Link", "label": "Certification Track",
         "options": "Duty Certification Track"},
        {"fieldname": "module", "fieldtype": "Link", "label": "Single Course",
         "options": "Duty Training Module"},
        {"fieldname": "facilitator", "fieldtype": "Link", "label": "Facilitator",
         "options": "User"},
        {"fieldname": "session_on", "fieldtype": "Datetime", "label": "Live Session"},
        {"fieldname": "opens_on", "fieldtype": "Datetime", "label": "Exam Window Opens"},
        {"fieldname": "closes_on", "fieldtype": "Datetime", "label": "Exam Window Closes"},
        {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
        {"fieldname": "members", "fieldtype": "Table", "label": "Members",
         "options": "Duty Training Cohort Member"},
    ],
    "index_web_pages_for_search": 1,
    "links": [],
    "modified": "2026-08-13 10:00:00.000000",
    "modified_by": "Administrator",
    "module": "Duty Board",
    "name": "Duty Training Cohort",
    "owner": "Administrator",
    "permissions": [{
        "create": 1, "delete": 1, "email": 1, "export": 1, "print": 1,
        "read": 1, "report": 1, "role": "System Manager", "share": 1, "write": 1,
    }],
    "sort_field": "modified",
    "sort_order": "DESC",
    "states": [],
    "title_field": "title",
}

MEMBER_JSON = {
    "actions": [],
    "autoname": "hash",
    "creation": "2026-08-13 10:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": ["trainee", "trainee_name", "attended", "enrolled"],
    "fields": [
        {"fieldname": "trainee", "fieldtype": "Link", "label": "Trainee",
         "options": "User", "reqd": 1, "in_list_view": 1},
        {"fieldname": "trainee_name", "fieldtype": "Data", "label": "Name",
         "in_list_view": 1},
        {"fieldname": "attended", "fieldtype": "Check", "label": "Attended Session",
         "in_list_view": 1},
        {"fieldname": "enrolled", "fieldtype": "Check", "label": "Enrolled",
         "in_list_view": 1},
    ],
    "index_web_pages_for_search": 1,
    "links": [],
    "modified": "2026-08-13 10:00:00.000000",
    "modified_by": "Administrator",
    "module": "Duty Board",
    "name": "Duty Training Cohort Member",
    "owner": "Administrator",
    "permissions": [],
    "sort_field": "modified",
    "sort_order": "DESC",
    "states": [],
    "istable": 1,
}

CTRL = '''# Copyright (c) 2026, Xlevel Retail Systems Ltd
import frappe
from frappe.model.document import Document


class {cls}(Document):
\tpass
'''


COHORT_PY = '''"""Training cohorts: the group as a first-class object.

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
\t"title", "track", "module", "facilitator", "session_on",
\t"opens_on", "closes_on", "note",
}


def _staff_only():
\tfrom duty_board.permissions import require_staff

\trequire_staff()


def _cohort(name):
\t_staff_only()
\treturn frappe.get_doc("Duty Training Cohort", name)


def _modules(coh):
\t"""The courses this cohort covers: every module of the track, in order,
\tor the single course when one is named."""
\tif coh.track:
\t\treturn frappe.get_all(
\t\t\t"Duty Certification Track Module",
\t\t\tfilters={"parent": coh.track},
\t\t\tpluck="module",
\t\t\torder_by="idx asc",
\t\t)
\treturn [coh.module] if coh.module else []


def window_state(cohort):
\t"""Open / not yet / closed / none, for a cohort name. Used by the exam
\tgate and by the staff UI so both read the same clock."""
\tif not cohort:
\t\treturn {"state": "none"}
\trow = frappe.db.get_value(
\t\t"Duty Training Cohort", cohort, ["opens_on", "closes_on", "status"], as_dict=True
\t)
\tif not row or (not row.opens_on and not row.closes_on):
\t\treturn {"state": "none"}
\tnow = now_datetime()
\tif row.opens_on and now < get_datetime(row.opens_on):
\t\treturn {"state": "early", "opens_on": str(row.opens_on)}
\tif row.closes_on and now > get_datetime(row.closes_on):
\t\treturn {"state": "closed", "closes_on": str(row.closes_on)}
\treturn {"state": "open", "closes_on": str(row.closes_on) if row.closes_on else None}


# ---------------- reads ----------------


@frappe.whitelist()
def cohort_list(room=None):
\t_staff_only()
\tfilters = {"room": room} if room else {}
\trows = frappe.get_all(
\t\t"Duty Training Cohort",
\t\tfilters=filters,
\t\tfields=[
\t\t\t"name", "room", "title", "status", "track", "module",
\t\t\t"facilitator", "session_on", "opens_on", "closes_on",
\t\t],
\t\torder_by="creation desc",
\t\tlimit_page_length=60,
\t)
\tfor r in rows:
\t\tr["member_count"] = frappe.db.count(
\t\t\t"Duty Training Cohort Member", {"parent": r.name}
\t\t)
\t\tr["enrolled_count"] = frappe.db.count(
\t\t\t"Duty Training Cohort Member", {"parent": r.name, "enrolled": 1}
\t\t)
\t\tr["window"] = window_state(r.name)
\treturn rows


@frappe.whitelist()
def cohort_get(name):
\tcoh = _cohort(name)
\tmods = _modules(coh)
\ttitles = {
\t\tm.name: m.title
\t\tfor m in frappe.get_all(
\t\t\t"Duty Training Module", filters={"name": ["in", mods or [""]]},
\t\t\tfields=["name", "title"],
\t\t)
\t}
\tpeople = []
\tfor m in coh.members:
\t\trecs = frappe.get_all(
\t\t\t"Duty Training Record",
\t\t\tfilters={"room": coh.room, "trainee": m.trainee, "module": ["in", mods or [""]]},
\t\t\tfields=["module", "status"],
\t\t)
\t\tdone = sum(1 for r in recs if r.status == "Completed")
\t\tpeople.append({
\t\t\t"trainee": m.trainee,
\t\t\t"trainee_name": m.trainee_name or frappe.utils.get_fullname(m.trainee),
\t\t\t"attended": cint(m.attended),
\t\t\t"enrolled": cint(m.enrolled),
\t\t\t"done": done,
\t\t\t"total": len(mods),
\t\t})
\treturn {
\t\t"name": coh.name,
\t\t"room": coh.room,
\t\t"title": coh.title,
\t\t"status": coh.status,
\t\t"track": coh.track,
\t\t"module": coh.module,
\t\t"facilitator": coh.facilitator,
\t\t"session_on": str(coh.session_on) if coh.session_on else None,
\t\t"opens_on": str(coh.opens_on) if coh.opens_on else None,
\t\t"closes_on": str(coh.closes_on) if coh.closes_on else None,
\t\t"note": coh.note,
\t\t"courses": [{"name": m, "title": titles.get(m, m)} for m in mods],
\t\t"people": people,
\t\t"window": window_state(coh.name),
\t}


@frappe.whitelist()
def cohort_candidates(room):
\t"""Active members of the room who are not already in this room's rooms —
\tthe pool a cohort draws from."""
\t_staff_only()
\trows = frappe.get_all(
\t\t"Client Room Member",
\t\tfilters={"room": room, "active": 1},
\t\tfields=["user"],
\t)
\treturn [
\t\t{"user": r.user, "full_name": frappe.utils.get_fullname(r.user)}
\t\tfor r in rows
\t\tif r.user
\t]


# ---------------- writes ----------------


@frappe.whitelist()
def cohort_create(room, title, track=None, module=None):
\t_staff_only()
\tif not frappe.db.exists("Client Room", room):
\t\tfrappe.throw(_("Not found."))
\tif not (track or module):
\t\tfrappe.throw(_("A cohort needs either a certification track or a single course."))
\tcoh = frappe.get_doc({
\t\t"doctype": "Duty Training Cohort",
\t\t"room": room,
\t\t"title": title,
\t\t"track": track,
\t\t"module": module,
\t\t"status": "Draft",
\t}).insert(ignore_permissions=True)
\tfrappe.db.commit()
\treturn cohort_get(coh.name)


@frappe.whitelist()
def cohort_set(name, field, value=None):
\tcoh = _cohort(name)
\tif field not in SETTABLE:
\t\tfrappe.throw(_("That field is not editable here."))
\tcoh.db_set(field, value or None)
\tfrappe.db.commit()
\treturn cohort_get(name)


@frappe.whitelist()
def cohort_add_member(name, user):
\tcoh = _cohort(name)
\tif not frappe.db.exists("Client Room Member", {"room": coh.room, "user": user, "active": 1}):
\t\tfrappe.throw(_("That person is not an active member of this room."))
\tif any(m.trainee == user for m in coh.members):
\t\tfrappe.throw(_("Already in this cohort."))
\tcoh.append("members", {
\t\t"trainee": user,
\t\t"trainee_name": frappe.utils.get_fullname(user),
\t})
\tcoh.save(ignore_permissions=True)
\tfrappe.db.commit()
\treturn cohort_get(name)


@frappe.whitelist()
def cohort_remove_member(name, user):
\tcoh = _cohort(name)
\trow = [m for m in coh.members if m.trainee == user]
\tif not row:
\t\tfrappe.throw(_("Not in this cohort."))
\tif cint(row[0].enrolled):
\t\tfrappe.throw(
\t\t\t_("{0} is already enrolled — their training records stand. Remove them from the course instead.").format(
\t\t\t\trow[0].trainee_name or user
\t\t\t)
\t\t)
\tcoh.members = [m for m in coh.members if m.trainee != user]
\tcoh.save(ignore_permissions=True)
\tfrappe.db.commit()
\treturn cohort_get(name)


@frappe.whitelist()
def cohort_attendance(name, user, attended=1):
\tcoh = _cohort(name)
\thit = False
\tfor m in coh.members:
\t\tif m.trainee == user:
\t\t\tm.attended = 1 if cint(attended) else 0
\t\t\thit = True
\tif not hit:
\t\tfrappe.throw(_("Not in this cohort."))
\tcoh.save(ignore_permissions=True)
\tfrappe.db.commit()
\treturn cohort_get(name)


@frappe.whitelist()
def cohort_enrol(name):
\t"""Create (or adopt) a Duty Training Record per member per course and
\tstamp the cohort on it. Idempotent — safe to re-run after a late joiner."""
\tcoh = _cohort(name)
\tif coh.status == "Closed":
\t\tfrappe.throw(_("This cohort is closed."))
\tmods = _modules(coh)
\tif not mods:
\t\tfrappe.throw(_("This cohort has no courses — set a track or a single course first."))
\tif not coh.members:
\t\tfrappe.throw(_("This cohort has no members yet."))
\tcreated, adopted = 0, 0
\tfor m in coh.members:
\t\tfor mod in mods:
\t\t\texisting = frappe.db.get_value(
\t\t\t\t"Duty Training Record",
\t\t\t\t{"room": coh.room, "module": mod, "trainee": m.trainee},
\t\t\t\t"name",
\t\t\t)
\t\t\tif existing:
\t\t\t\tif not frappe.db.get_value("Duty Training Record", existing, "cohort"):
\t\t\t\t\tfrappe.db.set_value(
\t\t\t\t\t\t"Duty Training Record", existing, "cohort", coh.name,
\t\t\t\t\t\tupdate_modified=False,
\t\t\t\t\t)
\t\t\t\tadopted += 1
\t\t\t\tcontinue
\t\t\tfrappe.get_doc({
\t\t\t\t"doctype": "Duty Training Record",
\t\t\t\t"room": coh.room,
\t\t\t\t"module": mod,
\t\t\t\t"trainee": m.trainee,
\t\t\t\t"trainee_name": m.trainee_name or frappe.utils.get_fullname(m.trainee),
\t\t\t\t"status": "Assigned",
\t\t\t\t"cohort": coh.name,
\t\t\t}).insert(ignore_permissions=True)
\t\t\tcreated += 1
\t\tm.enrolled = 1
\tif coh.status == "Draft":
\t\tcoh.status = "Enrolled"
\tcoh.save(ignore_permissions=True)
\tfrappe.db.commit()
\t_announce(coh, created)
\treturn {"created": created, "adopted": adopted, "cohort": cohort_get(name)}


def _announce(coh, created):
\t"""One room narration and one notification per trainee — the same
\tetiquette the single-assignment path already keeps."""
\tif not created:
\t\treturn
\ttry:
\t\tfrom duty_board.client_room import _post

\t\troom = frappe.get_doc("Client Room", coh.room)
\t\t_post(
\t\t\troom,
\t\t\t_("🎓 Training cohort “{0}” enrolled — {1} course place(s) across {2} people").format(
\t\t\t\tcoh.title, created, len(coh.members)
\t\t\t),
\t\t)
\texcept Exception:
\t\tfrappe.log_error(frappe.get_traceback(), "duty_board cohort narration")
\tfor m in coh.members:
\t\ttry:
\t\t\tfrom duty_board.api import _notify_user

\t\t\t_notify_user(
\t\t\t\tm.trainee,
\t\t\t\t_("🎓 New training · Xlevel"),
\t\t\t\tcoh.title,
\t\t\t)
\t\texcept Exception:
\t\t\tpass


@frappe.whitelist()
def cohort_close(name):
\tcoh = _cohort(name)
\tcoh.db_set("status", "Closed")
\tfrappe.db.commit()
\treturn cohort_get(name)
'''


# --- client_room.py: exam window on the gate -------------------------------
GATE_OLD = '''def _exam_gate(module, user):
\t"""Enforce the attempt cap and cooling-off window. Called on the CLIENT
\tpath only — internal staff testing keeps its old ungated behaviour."""
\tst = _quiz_state(module, user)
\tif st["passed"]:
\t\treturn st'''

GATE_NEW = '''def _exam_gate(module, user, record=None):
\t"""Enforce the cohort exam window, the attempt cap and the cooling-off
\twindow. Called on the CLIENT path only — internal staff testing keeps its
\told ungated behaviour."""
\tst = _quiz_state(module, user)
\tif st["passed"]:
\t\treturn st
\tif record:
\t\t_cohort_window_gate(record)'''

WIN_OLD = '''def _topic_breakdown(pairs):'''

WIN_NEW = '''def _cohort_window_gate(record):
\t"""A record enrolled through a cohort may only sit its exam inside that
\tcohort's window. Records with no cohort, or a cohort with no dates, are
\tuntouched — this is opt-in per cohort, like every other policy here."""
\tcohort = frappe.db.get_value("Duty Training Record", record, "cohort")
\tif not cohort:
\t\treturn
\tfrom duty_board.cohort import window_state

\tw = window_state(cohort)
\tif w["state"] == "early":
\t\tfrappe.throw(
\t\t\t_("This assessment opens on {0}.").format(
\t\t\t\tfrappe.utils.format_datetime(w["opens_on"], "d MMM yyyy, HH:mm")
\t\t\t)
\t\t)
\tif w["state"] == "closed":
\t\tfrappe.throw(
\t\t\t_("The assessment window for this cohort closed on {0}. Speak to your training coordinator.").format(
\t\t\t\tfrappe.utils.format_datetime(w["closes_on"], "d MMM yyyy, HH:mm")
\t\t\t)
\t\t)


def _topic_breakdown(pairs):'''

CQS_OLD = '''\t_exam_gate(rec.module, frappe.session.user)
\treturn _exam_start(rec.name, rec.module)'''

CQS_NEW = '''\t_exam_gate(rec.module, frappe.session.user, rec.name)
\treturn _exam_start(rec.name, rec.module)'''


# --- staff SPA: 👥 Cohorts on the room academy dialog ----------------------
JS_OLD = '''\tacademy_dialog(x) {
\t\tconst d = new frappe.ui.Dialog({ title: `🎓 ${x.customer} — ${__("Training Academy")}`, size: "large" });'''

JS_NEW = '''\tacademy_dialog(x) {
\t\tconst d = new frappe.ui.Dialog({ title: `🎓 ${x.customer} — ${__("Training Academy")}`, size: "large" });
\t\td.set_primary_action(`\\u{1F465} ${__("Cohorts")}`, () => { d.hide(); this.cohorts_dialog(x); });'''

JS_DLG_OLD = '''\tteam_training_dialog() {'''

JS_DLG_NEW = '''\tcohorts_dialog(x) {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst d = new frappe.ui.Dialog({ title: `\\u{1F465} ${x.customer} \\u2014 ${__("Training cohorts")}`, size: "extra-large" });
\t\tconst call = (m, args, cb) =>
\t\t\tfrappe.call({ method: `duty_board.cohort.${m}`, args: args || {}, callback: (r) => cb && cb(r.message) });
\t\tconst wtext = (w) => {
\t\t\tif (!w || w.state === "none") return __("no exam window");
\t\t\tif (w.state === "early") return `\\u{1F512} ${__("opens")} ${frappe.datetime.str_to_user(w.opens_on)}`;
\t\t\tif (w.state === "closed") return `\\u{1F512} ${__("closed")} ${frappe.datetime.str_to_user(w.closes_on)}`;
\t\t\treturn `\\u{1F7E2} ${__("window open")}${w.closes_on ? ` \\u00b7 ${__("until")} ${frappe.datetime.str_to_user(w.closes_on)}` : ""}`;
\t\t};
\t\tconst list = () =>
\t\t\tcall("cohort_list", { room: x.name }, (rows) => {
\t\t\t\trows = rows || [];
\t\t\t\t$(d.body).html(`
\t\t\t\t\t<div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-primary duty-coh-new">\\uFF0B ${__("New cohort")}</button>
\t\t\t\t\t\t<span class="text-muted" style="font-size:12px">${__("A cohort is one group of this client's staff running a track together, with a session date and an exam window.")}</span>
\t\t\t\t\t</div>
\t\t\t\t\t${rows.length
\t\t\t\t\t\t? rows.map((c) => `
\t\t\t\t\t\t<div class="duty-cr-msrow" style="cursor:pointer" data-coh="${esc(c.name)}">
\t\t\t\t\t\t\t<b>${esc(c.title)}</b>
\t\t\t\t\t\t\t<span class="text-muted" style="font-size:12px;margin-left:8px">${esc(c.status)} \\u00b7 ${c.enrolled_count}/${c.member_count} ${__("enrolled")}</span>
\t\t\t\t\t\t\t<span class="text-muted" style="font-size:12px;margin-left:auto">${wtext(c.window)}</span>
\t\t\t\t\t\t</div>`).join("")
\t\t\t\t\t\t: `<div class="text-muted">${__("No cohorts yet for this client.")}</div>`}
\t\t\t\t`);
\t\t\t\t$(d.body).find("[data-coh]").on("click", (e) => detail($(e.currentTarget).data("coh")));
\t\t\t\t$(d.body).find(".duty-coh-new").on("click", () => newCohort());
\t\t\t});
\t\tconst newCohort = () => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.client_room.room_tracks_for_assign",
\t\t\t\targs: { name: x.name },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst tracks = r.message || [];
\t\t\t\t\tif (!tracks.length) {
\t\t\t\t\t\tfrappe.msgprint(__("This room's products carry no client certification tracks yet."));
\t\t\t\t\t\treturn;
\t\t\t\t\t}
\t\t\t\t\tconst nd = new frappe.ui.Dialog({
\t\t\t\t\t\ttitle: __("New cohort"),
\t\t\t\t\t\tfields: [
\t\t\t\t\t\t\t{ fieldname: "title", fieldtype: "Data", label: __("Title"), reqd: 1,
\t\t\t\t\t\t\t  description: __("How this group will be referred to, e.g. “Finance team \\u2014 October intake”") },
\t\t\t\t\t\t\t{ fieldname: "track", fieldtype: "Select", label: __("Certification track"), reqd: 1,
\t\t\t\t\t\t\t  options: tracks.map((t) => `${t.name}|${t.title} (${t.module_count})`).join("\\n") },
\t\t\t\t\t\t],
\t\t\t\t\t\tprimary_action_label: __("Create"),
\t\t\t\t\t\tprimary_action: (v) => {
\t\t\t\t\t\t\tnd.hide();
\t\t\t\t\t\t\tcall("cohort_create", { room: x.name, title: v.title, track: String(v.track).split("|")[0] },
\t\t\t\t\t\t\t\t(c) => detail(c.name));
\t\t\t\t\t\t},
\t\t\t\t\t});
\t\t\t\t\t// show titles, submit ids
\t\t\t\t\tnd.fields_dict.track.df.options = tracks.map((t) => ({ value: t.name, label: `${t.title} \\u00b7 ${t.module_count} ${__("courses")}` }));
\t\t\t\t\tnd.fields_dict.track.refresh();
\t\t\t\t\tnd.show();
\t\t\t\t},
\t\t\t});
\t\t};
\t\tconst dateField = (c, key, label) =>
\t\t\t`<div style="display:flex;gap:8px;align-items:center;margin:5px 0">
\t\t\t\t<span style="min-width:150px;font-size:12.5px">${label}</span>
\t\t\t\t<input type="datetime-local" class="form-control input-sm duty-coh-dt" data-key="${key}" value="${c[key] ? String(c[key]).replace(" ", "T").slice(0, 16) : ""}" style="max-width:230px">
\t\t\t</div>`;
\t\tconst detail = (name) =>
\t\t\tcall("cohort_get", { name: name }, (c) => {
\t\t\t\t$(d.body).html(`
\t\t\t\t\t<a class="duty-coh-back" style="cursor:pointer;font-size:12.5px">\\u2190 ${__("All cohorts")}</a>
\t\t\t\t\t<h4 style="margin:8px 0 2px">${esc(c.title)}</h4>
\t\t\t\t\t<div class="text-muted" style="font-size:12px;margin-bottom:10px">${esc(c.name)} \\u00b7 ${esc(c.status)} \\u00b7 ${c.courses.length} ${__("courses")} \\u00b7 ${wtext(c.window)}</div>
\t\t\t\t\t${dateField(c, "session_on", __("Live session"))}
\t\t\t\t\t${dateField(c, "opens_on", __("Exam window opens"))}
\t\t\t\t\t${dateField(c, "closes_on", __("Exam window closes"))}
\t\t\t\t\t<div class="duty-lead-section" style="margin-top:14px">\\u{1F465} ${__("Members")}</div>
\t\t\t\t\t${c.people.length
\t\t\t\t\t\t? c.people.map((p) => `
\t\t\t\t\t\t<div class="duty-cr-msrow">
\t\t\t\t\t\t\t<label style="margin:0;font-weight:400;font-size:12.5px"><input type="checkbox" class="duty-coh-att" data-u="${esc(p.trainee)}" ${p.attended ? "checked" : ""}> ${__("attended")}</label>
\t\t\t\t\t\t\t<b style="margin-left:10px">${esc(p.trainee_name)}</b>
\t\t\t\t\t\t\t<span class="text-muted" style="font-size:12px;margin-left:auto">${p.enrolled ? `${p.done}/${p.total} ${__("complete")}` : __("not enrolled")}</span>
\t\t\t\t\t\t\t${p.enrolled ? "" : `<a class="duty-coh-rm" data-u="${esc(p.trainee)}" style="cursor:pointer;margin-left:10px" title="${__("Remove")}">\\u2715</a>`}
\t\t\t\t\t\t</div>`).join("")
\t\t\t\t\t\t: `<div class="text-muted">${__("No members yet.")}</div>`}
\t\t\t\t\t<div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">
\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-default duty-coh-add">\\uFF0B ${__("Add member")}</button>
\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-primary duty-coh-enrol">\\u{1F393} ${__("Enrol everyone")}</button>
\t\t\t\t\t\t${c.status === "Closed" ? "" : `<button type="button" class="btn btn-sm btn-default duty-coh-close">${__("Close cohort")}</button>`}
\t\t\t\t\t</div>
\t\t\t\t\t<p class="text-muted" style="font-size:11.5px;margin-top:10px">${__("Enrolling is safe to repeat — existing course records are adopted, never duplicated.")}</p>
\t\t\t\t`);
\t\t\t\t$(d.body).find(".duty-coh-back").on("click", list);
\t\t\t\t$(d.body).find(".duty-coh-dt").on("change", (e) => {
\t\t\t\t\tconst $i = $(e.currentTarget);
\t\t\t\t\tcall("cohort_set", { name: name, field: $i.data("key"), value: ($i.val() || "").replace("T", " ") }, () => detail(name));
\t\t\t\t});
\t\t\t\t$(d.body).find(".duty-coh-att").on("change", (e) => {
\t\t\t\t\tconst $i = $(e.currentTarget);
\t\t\t\t\tcall("cohort_attendance", { name: name, user: $i.data("u"), attended: $i.is(":checked") ? 1 : 0 });
\t\t\t\t});
\t\t\t\t$(d.body).find(".duty-coh-rm").on("click", (e) =>
\t\t\t\t\tcall("cohort_remove_member", { name: name, user: $(e.currentTarget).data("u") }, () => detail(name)));
\t\t\t\t$(d.body).find(".duty-coh-close").on("click", () =>
\t\t\t\t\tfrappe.confirm(__("Close this cohort? Its exam window still governs."), () =>
\t\t\t\t\t\tcall("cohort_close", { name: name }, () => detail(name))));
\t\t\t\t$(d.body).find(".duty-coh-enrol").on("click", () =>
\t\t\t\t\tcall("cohort_enrol", { name: name }, (res) => {
\t\t\t\t\t\tfrappe.show_alert({
\t\t\t\t\t\t\tmessage: __("{0} created, {1} adopted", [res.created, res.adopted]),
\t\t\t\t\t\t\tindicator: "green",
\t\t\t\t\t\t});
\t\t\t\t\t\tdetail(name);
\t\t\t\t\t}));
\t\t\t\t$(d.body).find(".duty-coh-add").on("click", () =>
\t\t\t\t\tcall("cohort_candidates", { room: x.name }, (pool) => {
\t\t\t\t\t\tconst taken = new Set(c.people.map((p) => p.trainee));
\t\t\t\t\t\tconst free = (pool || []).filter((p) => !taken.has(p.user));
\t\t\t\t\t\tif (!free.length) return frappe.msgprint(__("Every active room member is already in this cohort."));
\t\t\t\t\t\tconst ad = new frappe.ui.Dialog({
\t\t\t\t\t\t\ttitle: __("Add member"),
\t\t\t\t\t\t\tfields: [{ fieldname: "user", fieldtype: "Select", label: __("Person"), reqd: 1,
\t\t\t\t\t\t\t\toptions: free.map((p) => ({ value: p.user, label: p.full_name })) }],
\t\t\t\t\t\t\tprimary_action_label: __("Add"),
\t\t\t\t\t\t\tprimary_action: (v) => { ad.hide(); call("cohort_add_member", { name: name, user: v.user }, () => detail(name)); },
\t\t\t\t\t\t});
\t\t\t\t\t\tad.show();
\t\t\t\t\t}));
\t\t\t});
\t\tlist();
\t\td.show();
\t}

\tteam_training_dialog() {'''


# --- permissions suite: a new module needs its own negative test --------
TEST = "duty_board/tests/test_permissions.py"
T1_OLD = '\t"duty_board.library": set(),'
T1_NEW = '\t"duty_board.library": set(),\n\t"duty_board.cohort": set(),'
T2_OLD = '\tdef test_library_denies_clients(self):\n\t\tself._assert_denied("duty_board.library")'
T2_NEW = (
    '\tdef test_library_denies_clients(self):\n\t\tself._assert_denied("duty_board.library")\n\n'
    '\tdef test_cohort_denies_clients(self):\n\t\tself._assert_denied("duty_board.cohort")'
)


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = json.load(f)
    added = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        added = True
    if added:
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def write_doctype(root, folder, spec, cls):
    d = os.path.join(root, DT_DIR, folder)
    if not os.path.isdir(d):
        os.makedirs(d)
    for fname, body in (
        ("__init__.py", ""),
        (folder + ".json", json.dumps(spec, indent=1) + "\n"),
        (folder + ".py", CTRL.format(cls=cls)),
    ):
        p = os.path.join(d, fname)
        if os.path.exists(p):
            continue
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(body)


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, JS, TEST):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if os.path.exists(os.path.join(root, COHORT)):
        print("Already applied. Nothing to do.")
        return
    if '"3.207.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.207.0.")

    edits = [
        (CR, GATE_OLD, GATE_NEW, "_exam_gate takes the record"),
        (CR, WIN_OLD, WIN_NEW, "_cohort_window_gate"),
        (CR, CQS_OLD, CQS_NEW, "client_quiz_start passes the record"),
        (JS, JS_OLD, JS_NEW, "academy dialog Cohorts action"),
        (JS, JS_DLG_OLD, JS_DLG_NEW, "cohorts_dialog"),
        (TEST, T1_OLD, T1_NEW, "NON_STAFF map entry"),
        (TEST, T2_OLD, T2_NEW, "cohort negative test"),
    ]

    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    write_doctype(root, "duty_training_cohort", COHORT_JSON, "DutyTrainingCohort")
    write_doctype(root, "duty_training_cohort_member", MEMBER_JSON, "DutyTrainingCohortMember")
    print("  doctypes: Duty Training Cohort + Member")

    add_fields(os.path.join(root, TRDT), [
        {"fieldname": "cohort", "fieldtype": "Data", "label": "Cohort", "read_only": 1},
    ])
    print("  Duty Training Record: +cohort")

    with io.open(os.path.join(root, COHORT), "w", encoding="utf-8") as f:
        f.write(COHORT_PY)
    print("  cohort.py written")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, JS, TEST):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: exam window on the gate")
    print("  duty_board.js: cohorts dialog")
    print("  test_permissions.py: duty_board.cohort registered")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.207.0"', '"3.208.0"'))
    print("wrote __init__.py -> 3.208.0")


if __name__ == "__main__":
    main()
