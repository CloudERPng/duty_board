#!/usr/bin/env python3
"""Duty Board v3.81.0 — sales cadence (discussed & locked).

The pipeline had memory but no discipline: nothing dated the next touch,
meetings lived outside the system, follow-up load was invisible.

NEXT STEP — one dated action per open lead:
- Duty Lead +next_step, +next_step_due, +next_step_user,
  +next_step_reminder.
- lead_set_step: writes the step, auto-creates a Duty Reminder at the
  due moment for the assignee (v3.75 cron does the nudging — nothing
  new fires), auto-notes the timeline, notifies the assignee.
- lead_complete_step(outcome): auto-notes "✅ … — outcome", cancels the
  reminder, clears — and the UI immediately prompts the next step. The
  cadence loop.
- Pipeline cards: ❗ "no next step" (amber shame badge, decision 1) on
  open leads without one; else 📞 due (red when overdue). Header counts
  the gaps. Lead drawer gets a Next Step block above Tasks.

MEETINGS — reusing the whole existing machinery:
- Duty Meeting +lead link. Scheduling creates a roomless Confirmed
  Duty Meeting (attendees = you + lead owner): the existing calendar
  queries, morning/hour reminder crons, and invite emails all just
  work.
- Slot picking reuses the client-slot grid (decision 2) — weekends,
  leave, and public holidays respected automatically.
- Past meetings without an outcome show "📝 log outcome" in the drawer;
  outcomes write to the timeline.

TEAM LOAD (decision 3): 👥 grid gains a 📞 Follow-ups column — open
next-steps per person.

Schema -> bench migrate && bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.80.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
SALES = "duty_board/sales.py"
PROJ = "duty_board/projects.py"
LDDT = "duty_board/duty_board/doctype/duty_lead/duty_lead.json"
DMDT = "duty_board/duty_board/doctype/duty_meeting/duty_meeting.json"
CHECK_ONLY = "--check" in sys.argv

# ============ sales.py ============
S1_OLD = '''\t\t\t"erp_lead", "erp_quotation", "erp_customer", "erp_sales_order",
\t\t],'''
S1_NEW = '''\t\t\t"erp_lead", "erp_quotation", "erp_customer", "erp_sales_order",
\t\t\t"next_step", "next_step_due", "next_step_user",
\t\t],'''

S2_OLD = '''\t\t\tnote_counts[n.lead] = n.cnt
'''
S2_NEW = '''\t\t\tnote_counts[n.lead] = n.cnt
\t\tmeet_next = {}
\t\tfor m in frappe.get_all(
\t\t\t"Duty Meeting",
\t\t\tfilters={"lead": ["in", names], "status": "Confirmed"},
\t\t\tfields=["lead", "meeting_date", "start_time"],
\t\t\torder_by="meeting_date asc, start_time asc",
\t\t):
\t\t\tif m.lead not in meet_next and m.meeting_date and getdate(m.meeting_date) >= tday:
\t\t\t\tmeet_next[m.lead] = f"{m.meeting_date} {str(m.start_time)[:5] if m.start_time else ''}".strip()
'''

S3_OLD = '''\t\tl.notes = note_counts.get(l.name, 0)'''
S3_NEW = '''\t\tl.notes = note_counts.get(l.name, 0)
\t\tl.next_step_due = str(l.next_step_due) if l.next_step_due else None
\t\tl.no_step = 0 if l.next_step else 1
\t\tl.step_overdue = bool(
\t\t\tl.next_step and l.next_step_due and frappe.utils.get_datetime(l.next_step_due) < now
\t\t)
\t\tl.meeting_next = meet_next.get(l.name) if names else None'''

S4_OLD = '''\ttotal = {
\t\t"count": len(leads),
\t\t"value": sum(s["value"] for s in stages.values()) if sv else None,
\t}'''
S4_NEW = '''\ttotal = {
\t\t"count": len(leads),
\t\t"value": sum(s["value"] for s in stages.values()) if sv else None,
\t\t"no_step": sum(1 for l in leads if l.no_step),
\t}'''

S5_OLD = '''\t\t"tasks": tasks,
\t\t"notes": notes,
\t}'''
S5_NEW = '''\t\t"next_step": doc.get("next_step"),
\t\t"next_step_due": str(doc.next_step_due) if doc.get("next_step_due") else None,
\t\t"next_step_user": doc.get("next_step_user"),
\t\t"step_overdue": bool(
\t\t\tdoc.get("next_step")
\t\t\tand doc.get("next_step_due")
\t\t\tand frappe.utils.get_datetime(doc.next_step_due) < frappe.utils.now_datetime()
\t\t),
\t\t"meetings": _lead_meetings(name),
\t\t"tasks": tasks,
\t\t"notes": notes,
\t}'''

S6_APPEND = '''

def _lead_meetings(lead):
	now = frappe.utils.now_datetime()
	rows = frappe.get_all(
		"Duty Meeting",
		filters={"lead": lead},
		fields=["name", "topic", "meeting_date", "start_time", "status", "outcome", "outcome_note"],
		order_by="meeting_date desc, start_time desc",
		limit=8,
	)
	for m in rows:
		start = frappe.utils.get_datetime(f"{m.meeting_date} {m.start_time or '00:00:00'}")
		m.meeting_date = str(m.meeting_date)
		m.start_time = str(m.start_time)[:5] if m.start_time else ""
		m.past = 1 if start < now else 0
	return rows


def _cancel_step_reminder(doc):
	if doc.get("next_step_reminder") and frappe.db.exists("Duty Reminder", doc.next_step_reminder):
		frappe.db.set_value(
			"Duty Reminder", doc.next_step_reminder, "status", "Cancelled", update_modified=False
		)


@frappe.whitelist()
def lead_set_step(name, step, due, user=None):
	"""Set (or replace) the lead's single next step. Auto-creates the
	reminder at the due moment — the nudge is generated, never manual."""
	require_staff()
	step = (step or "").strip()
	if not step:
		frappe.throw(_("Describe the next step."))
	when = frappe.utils.get_datetime(due)
	if when <= frappe.utils.now_datetime():
		frappe.throw(_("Pick a future time."))
	doc = frappe.get_doc("Duty Lead", name)
	who = user or doc.lead_owner or frappe.session.user
	_cancel_step_reminder(doc)
	rem = frappe.get_doc({
		"doctype": "Duty Reminder",
		"user": who,
		"text": f"📞 {doc.company}: {step}"[:200],
		"remind_at": when,
		"repeat": "None",
		"status": "Active",
	}).insert(ignore_permissions=True)
	doc.db_set(
		{
			"next_step": step[:140],
			"next_step_due": when,
			"next_step_user": who,
			"next_step_reminder": rem.name,
		},
		update_modified=False,
	)
	frappe.db.commit()
	_auto_note(name, f"📞 Next step: {step} — due {str(when)[:16]} ({frappe.utils.get_fullname(who)})")
	if who != frappe.session.user:
		first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
		_notify(who, _("Next step from {0}").format(first), f"{doc.company}: {step}")
	return get_lead(name)


@frappe.whitelist()
def lead_complete_step(name, outcome=None):
	"""Complete the current step with an outcome; timeline remembers,
	reminder dies, and the UI immediately asks for the next one."""
	require_staff()
	doc = frappe.get_doc("Duty Lead", name)
	if not doc.get("next_step"):
		frappe.throw(_("No next step is set."))
	_cancel_step_reminder(doc)
	note = f"✅ Done: {doc.next_step}"
	if (outcome or "").strip():
		note += f" — {outcome.strip()}"
	_auto_note(name, note)
	doc.db_set(
		{"next_step": None, "next_step_due": None, "next_step_user": None, "next_step_reminder": None},
		update_modified=False,
	)
	frappe.db.commit()
	return get_lead(name)


@frappe.whitelist()
def lead_meeting_slots(name, date):
	"""Availability for a lead meeting — the same slot grid clients see:
	weekdays, working hours, leave and public holidays respected."""
	require_staff()
	from duty_board.client_room import _meeting_slots

	doc = frappe.get_doc("Duty Lead", name)
	staff = list({frappe.session.user, doc.lead_owner or frappe.session.user})
	slots = _meeting_slots(staff, getdate(date)) or []
	out = []
	for s in slots:
		if isinstance(s, dict):
			out.append(str(s.get("start") or s.get("time") or ""))
		else:
			out.append(str(s))
	return {"slots": [s for s in out if s]}


@frappe.whitelist()
def lead_schedule_meeting(name, meeting_date, start_time, topic=None):
	"""A roomless Duty Meeting linked to the lead — existing calendar,
	reminder crons, and invites all apply unchanged."""
	require_staff()
	doc = frappe.get_doc("Duty Lead", name)
	topic = (topic or "").strip() or f"{doc.company} — sales meeting"
	users = list({frappe.session.user, doc.lead_owner or frappe.session.user})
	meet = frappe.get_doc({
		"doctype": "Duty Meeting",
		"topic": topic[:140],
		"lead": name,
		"meeting_date": getdate(meeting_date),
		"start_time": start_time if len(str(start_time)) > 5 else f"{start_time}:00",
		"duration_mins": 30,
		"status": "Confirmed",
		"requested_by": frappe.session.user,
		"confirmed_by": frappe.session.user,
		"attendees": [{"user": u} for u in users],
	})
	meet.insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		from duty_board.client_room import _send_meeting_invite

		_send_meeting_invite(meet, "REQUEST")
	except Exception:
		pass
	_auto_note(name, f"📅 Meeting scheduled: {topic} — {meeting_date} {str(start_time)[:5]}")
	return get_lead(name)


@frappe.whitelist()
def lead_meeting_outcome(meeting, note):
	require_staff()
	doc = frappe.get_doc("Duty Meeting", meeting)
	if not doc.get("lead"):
		frappe.throw(_("Not a lead meeting."))
	doc.db_set({"outcome": "Held", "outcome_note": (note or "").strip()[:500]}, update_modified=False)
	frappe.db.commit()
	_auto_note(doc.lead, f"📝 Meeting outcome: {(note or '').strip()}")
	return get_lead(doc.lead)
'''

# ============ projects.py: team-load follow-ups ============
P1_OLD = '''\tfrom duty_board.leave import users_on_leave'''
P1_NEW = '''\t_fu = {}
\tfor f in frappe.get_all(
\t\t"Duty Lead",
\t\tfilters={"status": "Open", "next_step_user": ["is", "set"]},
\t\tfields=["next_step_user", "count(name) as cnt"],
\t\tgroup_by="next_step_user",
\t):
\t\t_fu[f.next_step_user] = f.cnt
\tfrom duty_board.leave import users_on_leave'''

P2_OLD = '''\t\t\t"full_name": _("Unassigned") if user == "__unassigned__" else frappe.utils.get_fullname(user),'''
P2_NEW = '''\t\t\t"full_name": _("Unassigned") if user == "__unassigned__" else frappe.utils.get_fullname(user),
\t\t\t"followups": _fu.get(user, 0),'''

# ============ JS ============
J1_OLD = '''\t\t\t\t\t\t${l.notes ? `<span>💬 ${l.notes}</span>` : ""}'''
J1_NEW = '''\t\t\t\t\t\t${l.notes ? `<span>💬 ${l.notes}</span>` : ""}
\t\t\t\t\t\t${l.no_step ? `<span class="duty-step-none" title="${__("No next step — every open lead needs one")}">❗ ${__("no next step")}</span>` : l.next_step ? `<span class="duty-step ${l.step_overdue ? "duty-lead-over" : ""}" title="${frappe.utils.escape_html(l.next_step)}">📞 ${l.next_step_due ? frappe.datetime.str_to_user(l.next_step_due).slice(0, 17) : ""}</span>` : ""}
\t\t\t\t\t\t${l.meeting_next ? `<span title="${__("Next meeting")}">📅 ${l.meeting_next.slice(5, 16)}</span>` : ""}'''

J2_OLD = '''`💼 <b>${__("Pipeline")}</b> · ${data.total.count} ${__("leads")}` +'''
J2_NEW = '''`💼 <b>${__("Pipeline")}</b> · ${data.total.count} ${__("leads")}` +
\t\t\t\t\t(data.total.no_step ? ` · <b class="duty-step-none">❗ ${data.total.no_step} ${__("without next step")}</b>` : "") +'''

J3_OLD = '''\t\tconst $x = $(d.fields_dict.extras.wrapper).html(`
\t\t\t${contact_bits.length ?'''
J3_NEW = '''\t\tthis._lead_ctx = x;
\t\tconst $x = $(d.fields_dict.extras.wrapper).html(`
\t\t\t${contact_bits.length ?'''

J4_OLD = '''\t\t\t<div class="duty-lead-section">📋 ${__("Tasks")}</div>'''
J4_NEW = '''\t\t\t<div class="duty-lead-section">📞 ${__("Next step")}</div>
\t\t\t<div class="duty-ld-step">
\t\t\t\t${x.next_step ? `<div class="duty-ld-step-cur ${x.step_overdue ? "over" : ""}"><b>${esc(x.next_step)}</b><span class="text-muted"> · ${x.next_step_due ? frappe.datetime.str_to_user(x.next_step_due) : ""} · ${esc((this.name_map || {})[x.next_step_user] || x.next_step_user || "")}</span> <button class="btn btn-xs btn-primary duty-step-done">✓ ${__("Done")}</button> <a class="duty-step-edit" title="${__("Replace")}">✎</a></div>` : `<span class="duty-step-none">❗ ${__("No next step — every open lead needs one.")}</span> <button class="btn btn-xs btn-primary duty-step-set">＋ ${__("Set next step")}</button>`}
\t\t\t</div>
\t\t\t<div class="duty-lead-section">📅 ${__("Meetings")}</div>
\t\t\t<div class="duty-ld-meets">
\t\t\t\t${(x.meetings || []).map((m) => `<div class="duty-ld-meet"><b>${frappe.datetime.str_to_user(m.meeting_date)} ${m.start_time || ""}</b> · ${esc(m.topic)} ${m.outcome ? `<span class="text-muted">— ${esc(m.outcome_note || m.outcome)}</span>` : m.past ? `<a class="duty-meet-log" data-m="${m.name}">📝 ${__("log outcome")}</a>` : ""}</div>`).join("") || `<div class="text-muted" style="font-size:12px">${__("None yet.")}</div>`}
\t\t\t\t<button class="btn btn-xs btn-default duty-meet-new">📅 ${__("Schedule meeting")}</button>
\t\t\t</div>
\t\t\t<div class="duty-lead-section">📋 ${__("Tasks")}</div>'''

J5_OLD = '''\t\t\t\tthis._$ldrawer.find(".duty-ld-details").toggle(t === "det");
\t\t\t});
\t\t}'''
J5_NEW = '''\t\t\t\tthis._$ldrawer.find(".duty-ld-details").toggle(t === "det");
\t\t\t});
\t\t\tthis._$ldrawer.on("click", ".duty-step-set, .duty-step-edit", () => this.lead_step_prompt(this._lead_ctx));
\t\t\tthis._$ldrawer.on("click", ".duty-step-done", () => {
\t\t\t\tconst lx = this._lead_ctx;
\t\t\t\tfrappe.prompt(
\t\t\t\t\t{ fieldname: "outcome", fieldtype: "Data", label: __("Outcome (what happened?)") },
\t\t\t\t\t(v) => frappe.call({
\t\t\t\t\t\tmethod: "duty_board.sales.lead_complete_step",
\t\t\t\t\t\targs: { name: lx.name, outcome: v.outcome || "" },
\t\t\t\t\t\tcallback: (r) => {
\t\t\t\t\t\t\tif (!r.message) return;
\t\t\t\t\t\t\tthis.render_lead_dialog(r.message);
\t\t\t\t\t\t\tthis.refresh_sales(true);
\t\t\t\t\t\t\tthis.lead_step_prompt(r.message);
\t\t\t\t\t\t},
\t\t\t\t\t}),
\t\t\t\t\t__("Step done — {0}", [this._lead_ctx.company]), __("Done")
\t\t\t\t);
\t\t\t});
\t\t\tthis._$ldrawer.on("click", ".duty-meet-new", () => this.lead_meet_dialog(this._lead_ctx));
\t\t\tthis._$ldrawer.on("click", ".duty-meet-log", (e) => {
\t\t\t\tconst mid = $(e.currentTarget).data("m");
\t\t\t\tfrappe.prompt(
\t\t\t\t\t{ fieldname: "note", fieldtype: "Small Text", label: __("How did it go?"), reqd: 1 },
\t\t\t\t\t(v) => frappe.call({
\t\t\t\t\t\tmethod: "duty_board.sales.lead_meeting_outcome",
\t\t\t\t\t\targs: { meeting: mid, note: v.note },
\t\t\t\t\t\tcallback: (r) => r.message && this.render_lead_dialog(r.message),
\t\t\t\t\t}),
\t\t\t\t\t__("Meeting outcome"), __("Log")
\t\t\t\t);
\t\t\t});
\t\t}'''

J6_OLD = '''\trender_lead_dialog(x) {'''
J6_NEW = '''\tlead_step_prompt(x) {
\t\tfrappe.prompt(
\t\t\t[
\t\t\t\t{ fieldname: "step", fieldtype: "Data", label: __("Next step (e.g. Call Mrs Ade re: quotation)"), reqd: 1, default: x.next_step || "" },
\t\t\t\t{ fieldname: "due", fieldtype: "Datetime", label: __("When"), reqd: 1, default: x.next_step_due || "" },
\t\t\t],
\t\t\t(v) => frappe.call({
\t\t\t\tmethod: "duty_board.sales.lead_set_step",
\t\t\t\targs: { name: x.name, step: v.step, due: v.due },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tif (!r.message) return;
\t\t\t\t\tfrappe.show_alert({ message: __("📞 Next step set — reminder will fire."), indicator: "green" });
\t\t\t\t\tthis.render_lead_dialog(r.message);
\t\t\t\t\tthis.refresh_sales(true);
\t\t\t\t},
\t\t\t}),
\t\t\t__("Next step — {0}", [x.company]), __("Set")
\t\t);
\t}

\tlead_meet_dialog(x) {
\t\tconst d = new frappe.ui.Dialog({
\t\t\ttitle: `📅 ${__("Meeting — {0}", [x.company])}`,
\t\t\tfields: [
\t\t\t\t{ fieldname: "topic", fieldtype: "Data", label: __("Topic"), default: `${x.company} — sales meeting` },
\t\t\t\t{ fieldname: "date", fieldtype: "Date", label: __("Day"), reqd: 1 },
\t\t\t\t{ fieldname: "slot_html", fieldtype: "HTML" },
\t\t\t],
\t\t});
\t\tconst $slots = () => $(d.fields_dict.slot_html.wrapper);
\t\tconst load = () => {
\t\t\tconst day = d.get_value("date");
\t\t\tif (!day) return;
\t\t\t$slots().html(`<span class="text-muted">${__("Checking availability…")}</span>`);
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.sales.lead_meeting_slots",
\t\t\t\targs: { name: x.name, date: day },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst slots = (r.message && r.message.slots) || [];
\t\t\t\t\t$slots().html(slots.length
\t\t\t\t\t\t? `<div class="duty-slot-grid">${slots.map((s) => `<button class="btn btn-xs btn-default" data-s="${s}">${s}</button>`).join("")}</div>`
\t\t\t\t\t\t: `<span class="text-muted">${__("No slots that day — weekends, leave and holidays are blocked.")}</span>`);
\t\t\t\t\t$slots().find("button").on("click", (e) => {
\t\t\t\t\t\tconst s = $(e.currentTarget).data("s");
\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\tmethod: "duty_board.sales.lead_schedule_meeting",
\t\t\t\t\t\t\targs: { name: x.name, meeting_date: day, start_time: s, topic: d.get_value("topic") },
\t\t\t\t\t\t\tcallback: (rr) => {
\t\t\t\t\t\t\t\tif (!rr.message) return;
\t\t\t\t\t\t\t\td.hide();
\t\t\t\t\t\t\t\tfrappe.show_alert({ message: __("📅 Meeting scheduled — it's on the calendar with reminders."), indicator: "green" });
\t\t\t\t\t\t\t\tthis.render_lead_dialog(rr.message);
\t\t\t\t\t\t\t\tthis.refresh_sales(true);
\t\t\t\t\t\t\t},
\t\t\t\t\t\t});
\t\t\t\t\t});
\t\t\t\t},
\t\t\t});
\t\t};
\t\td.fields_dict.date.$input.on("change", load);
\t\td.show();
\t}

\trender_lead_dialog(x) {'''

J7_OLD = '''<th>${__("Projects")}</th></tr></thead>'''
J7_NEW = '''<th>${__("Projects")}</th><th>📞 ${__("Follow-ups")}</th></tr></thead>'''

J8_OLD = '''\t\t\t\t\t\t<td class="duty-tl-projects">${p.projects.map((n) => `<span class="duty-tl-chip">${esc(n)}</span>`).join(" ")}</td>'''
J8_NEW = '''\t\t\t\t\t\t<td class="duty-tl-projects">${p.projects.map((n) => `<span class="duty-tl-chip">${esc(n)}</span>`).join(" ")}</td>
\t\t\t\t\t\t<td>${p.followups ? `📞 ${p.followups}` : `<span class="text-muted">0</span>`}</td>'''

CSS_OLD = '''\t\t\t\tbody:not(.duty-mobile) .duty-pj-main { max-width: 1220px; }
\t\t\t}'''
CSS_NEW = '''\t\t\t\tbody:not(.duty-mobile) .duty-pj-main { max-width: 1220px; }
\t\t\t}
\t\t\t.duty-step-none { color: #B45309; font-weight: 700; font-size: 11px; }
\t\t\t.duty-step { font-size: 11px; font-weight: 700; color: #0F5C55; }
\t\t\t.duty-ld-step, .duty-ld-meets { margin-bottom: 12px; font-size: 13px; }
\t\t\t.duty-ld-step-cur { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
\t\t\t.duty-ld-step-cur.over b { color: #C2410C; }
\t\t\t.duty-ld-meet { padding: 3px 0; }
\t\t\t.duty-meet-log { color: #B45309; font-weight: 700; cursor: pointer; }
\t\t\t.duty-ld-meets .duty-meet-new { margin-top: 6px; }
\t\t\t.duty-slot-grid { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
\t\t\t.duty-slot-grid button { min-width: 64px; }'''


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = json.load(f)
    changed = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        changed = True
    if changed:
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, SALES, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def lead_set_step(" in files[SALES]:
        print("Already applied. Nothing to do.")
        return
    if '"3.80.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.80.0.")

    checks = [
        (SALES, S1_OLD, "pipeline fields", 1), (SALES, S2_OLD, "meet-next batch", 1),
        (SALES, S3_OLD, "enrich loop", 1), (SALES, S4_OLD, "total gaps", 1),
        (SALES, S5_OLD, "get_lead payload", 1),
        (PROJ, P1_OLD, "team-load fu batch", 1), (PROJ, P2_OLD, "team-load row", 1),
        (JS, J1_OLD, "card badges", 1), (JS, J2_OLD, "header gaps", 1),
        (JS, J3_OLD, "lead ctx", 1), (JS, J4_OLD, "drawer blocks", 1),
        (JS, J5_OLD, "delegated handlers", 1), (JS, J6_OLD, "helper methods", 1),
        (JS, J7_OLD, "tl header", 1), (JS, J8_OLD, "tl row", 1),
        (JS, CSS_OLD, "css", 1),
    ]
    problems = [f"  [{files[f].count(o)} != {n}] {label}" for f, o, label, n in checks if files[f].count(o) != n]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(checks)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, LDDT), [
        {"fieldname": "next_step", "fieldtype": "Data", "label": "Next Step"},
        {"fieldname": "next_step_due", "fieldtype": "Datetime", "label": "Next Step Due"},
        {"fieldname": "next_step_user", "fieldtype": "Link", "label": "Next Step User", "options": "User"},
        {"fieldname": "next_step_reminder", "fieldtype": "Data", "label": "Next Step Reminder"},
    ])
    add_fields(os.path.join(root, DMDT), [
        {"fieldname": "lead", "fieldtype": "Link", "label": "Lead", "options": "Duty Lead"},
    ])
    print("  Duty Lead +step fields · Duty Meeting +lead")

    s = files[SALES]
    for o, n in [(S1_OLD, S1_NEW), (S2_OLD, S2_NEW), (S3_OLD, S3_NEW), (S4_OLD, S4_NEW), (S5_OLD, S5_NEW)]:
        s = s.replace(o, n, 1)
    s += S6_APPEND
    with io.open(os.path.join(root, SALES), "w", encoding="utf-8") as f:
        f.write(s)
    print("  sales.py: pipeline enrichment + 5 cadence endpoints")

    pj = files[PROJ].replace(P1_OLD, P1_NEW, 1).replace(P2_OLD, P2_NEW, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: team-load follow-up counts")

    js = files[JS]
    for o, n in [(J1_OLD, J1_NEW), (J2_OLD, J2_NEW), (J3_OLD, J3_NEW), (J4_OLD, J4_NEW), (J5_OLD, J5_NEW), (J6_OLD, J6_NEW), (J7_OLD, J7_NEW), (J8_OLD, J8_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: badges, header gaps, drawer blocks, prompts, slot dialog, team-load column")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.80.0"', '"3.81.0"'))
    print("wrote __init__.py -> 3.81.0")


if __name__ == "__main__":
    main()
