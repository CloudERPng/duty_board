#!/usr/bin/env python3
"""Duty Board v3.75.0 — reminders (team request 2).

"Remind me of X on day Y at time Z" — one-off or repeating.

- New doctype Duty Reminder: user, text, remind_at (Datetime), repeat
  (None/Daily/Weekly/Monthly), status (Active/Done/Cancelled),
  last_fired.
- duty_board/reminders.py: my_reminders / add_reminder (future-time
  guard) / cancel_reminder / fire_due — the scheduler hook: every
  minute, Active reminders whose time has come fire through
  _notify_user (in-app realtime + web push, same channel as leave
  nudges). One-off -> Done; repeating -> advanced to the next
  occurrence (daily +1d, weekly +7d, monthly +1 month), catch-up safe
  (a missed occurrence fires once, then schedules forward from now).
- hooks.py: "* * * * *" cron entry added.
- Me face: ⏰ Reminders card — list with next-fire time + repeat tag +
  cancel, add form (text, date+time, repeat).

Schema (doctype) + hooks -> bench migrate && bench build && bench
restart. Anchored, idempotent. Requires v3.74.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
HOOKS = "duty_board/hooks.py"
RDIR = "duty_board/duty_board/doctype/duty_reminder"
REM = "duty_board/reminders.py"
CHECK_ONLY = "--check" in sys.argv

REM_DT = {
    "actions": [], "autoname": "hash",
    "creation": "2026-08-09 14:00:00.000000", "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": ["user", "text", "remind_at", "repeat", "status", "last_fired"],
    "fields": [
        {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1},
        {"fieldname": "text", "fieldtype": "Data", "label": "Reminder", "reqd": 1},
        {"fieldname": "remind_at", "fieldtype": "Datetime", "label": "Remind At", "reqd": 1},
        {"fieldname": "repeat", "fieldtype": "Select", "label": "Repeat", "options": "None\nDaily\nWeekly\nMonthly", "default": "None"},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Active\nDone\nCancelled", "default": "Active"},
        {"fieldname": "last_fired", "fieldtype": "Datetime", "label": "Last Fired"},
    ],
    "links": [], "modified": "2026-08-09 14:00:00.000000",
    "modified_by": "Administrator", "module": "Duty Board",
    "name": "Duty Reminder", "naming_rule": "Random", "owner": "Administrator",
    "permissions": [{"create": 1, "delete": 1, "read": 1, "report": 1, "role": "System Manager", "write": 1}],
    "sort_field": "modified", "sort_order": "DESC", "states": [],
}

REM_PY = '''"""Reminders — one-off or repeating, fired by the minute-cron and
delivered through _notify_user (in-app + web push)."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_months, get_datetime, now_datetime

from duty_board.permissions import require_staff


@frappe.whitelist()
def my_reminders():
	require_staff()
	rows = frappe.get_all(
		"Duty Reminder",
		filters={"user": frappe.session.user, "status": "Active"},
		fields=["name", "text", "remind_at", "repeat"],
		order_by="remind_at asc",
		limit=50,
	)
	for r in rows:
		r.remind_at = str(r.remind_at)
	return rows


@frappe.whitelist()
def add_reminder(text, remind_at, repeat="None"):
	require_staff()
	text = (text or "").strip()
	if not text:
		frappe.throw(_("What should I remind you about?"))
	when = get_datetime(remind_at)
	if when <= now_datetime():
		frappe.throw(_("Pick a future time."))
	if repeat not in ("None", "Daily", "Weekly", "Monthly"):
		repeat = "None"
	frappe.get_doc({
		"doctype": "Duty Reminder",
		"user": frappe.session.user,
		"text": text[:200],
		"remind_at": when,
		"repeat": repeat,
		"status": "Active",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return my_reminders()


@frappe.whitelist()
def cancel_reminder(name):
	require_staff()
	doc = frappe.get_doc("Duty Reminder", name)
	if doc.user != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not yours."))
	doc.db_set("status", "Cancelled", update_modified=True)
	frappe.db.commit()
	return my_reminders()


def _advance(when, repeat, now):
	"""Next occurrence strictly in the future (catch-up safe)."""
	step = {"Daily": timedelta(days=1), "Weekly": timedelta(days=7)}.get(repeat)
	nxt = when
	for _i in range(400):
		nxt = add_months(nxt, 1) if repeat == "Monthly" else nxt + step
		if get_datetime(nxt) > now:
			return nxt
	return None


def fire_due():
	"""Cron, every minute: fire Active reminders whose time has come."""
	from duty_board.api import _notify_user

	now = now_datetime()
	due = frappe.get_all(
		"Duty Reminder",
		filters={"status": "Active", "remind_at": ["<=", now]},
		fields=["name", "user", "text", "remind_at", "repeat"],
		limit=200,
	)
	for r in due:
		try:
			_notify_user(r.user, _("⏰ Reminder"), r.text)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "reminder notify")
		if r.repeat and r.repeat != "None":
			nxt = _advance(get_datetime(r.remind_at), r.repeat, now)
			if nxt:
				frappe.db.set_value("Duty Reminder", r.name, {"remind_at": nxt, "last_fired": now}, update_modified=False)
			else:
				frappe.db.set_value("Duty Reminder", r.name, {"status": "Done", "last_fired": now}, update_modified=False)
		else:
			frappe.db.set_value("Duty Reminder", r.name, {"status": "Done", "last_fired": now}, update_modified=False)
	if due:
		frappe.db.commit()
'''

# --- hooks: minute cron ------------------------------------------------------
HK_OLD = '''        "15 * * * *": ["duty_board.tasks.auto_clock_out"],'''
HK_NEW = '''        "15 * * * *": ["duty_board.tasks.auto_clock_out"],
        "* * * * *": ["duty_board.reminders.fire_due"],'''

# --- JS: card placeholder + loader + methods --------------------------------
PL_OLD = '''\t\t\t<div class="duty-me-earn"></div>
\t\t\t<div class="duty-me-cal">'''
PL_NEW = '''\t\t\t<div class="duty-me-earn"></div>
\t\t\t<div class="duty-me-remind"></div>
\t\t\t<div class="duty-me-cal">'''

LD_OLD = '''\t\tthis._load_leave_card();
\t\tthis._load_earnings_card();'''
LD_NEW = '''\t\tthis._load_leave_card();
\t\tthis._load_earnings_card();
\t\tthis._load_reminders_card();'''

MT_OLD = '\t_load_earnings_card() {'
MT_NEW = '''\t_load_reminders_card() {
\t\tconst $host = this.$me.find(".duty-me-remind");
\t\tif (!$host.length) return;
\t\tfrappe.call({
\t\t\tmethod: "duty_board.reminders.my_reminders",
\t\t\tcallback: (r) => this._render_reminders_card(r.message || []),
\t\t});
\t}

\t_render_reminders_card(rows) {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst $host = this.$me.find(".duty-me-remind");
\t\tif (!$host.length) return;
\t\tconst list = rows.map((x) => `
\t\t\t<div class="duty-lv-row">
\t\t\t\t<b>${esc(x.text)}</b>
\t\t\t\t<span class="text-muted">${frappe.datetime.str_to_user(x.remind_at)}</span>
\t\t\t\t${x.repeat && x.repeat !== "None" ? `<span class="duty-rm-rep">↻ ${__(x.repeat)}</span>` : ""}
\t\t\t\t<a class="duty-lv-cancel duty-rm-cancel" data-id="${x.name}" title="${__("Cancel")}">✕</a>
\t\t\t</div>`).join("");
\t\t$host.html(`
\t\t\t<div class="duty-me-reqs">
\t\t\t\t<h4>⏰ ${__("Reminders")}</h4>
\t\t\t\t${list || `<div class="text-muted" style="font-size:12.5px">${__("No reminders set.")}</div>`}
\t\t\t\t<div class="duty-lv-ask">
\t\t\t\t\t<input type="text" class="form-control input-sm duty-rm-text" placeholder="${__("Remind me to…")}" maxlength="200">
\t\t\t\t\t<input type="date" class="form-control input-sm duty-rm-date" min="${frappe.datetime.now_date()}">
\t\t\t\t\t<input type="time" class="form-control input-sm duty-rm-time">
\t\t\t\t\t<select class="form-control input-sm duty-rm-rep-sel"><option value="None">${__("Once")}</option><option value="Daily">${__("Daily")}</option><option value="Weekly">${__("Weekly")}</option><option value="Monthly">${__("Monthly")}</option></select>
\t\t\t\t\t<button class="btn btn-xs btn-primary duty-rm-go">⏰ ${__("Set")}</button>
\t\t\t\t</div>
\t\t\t</div>`);
\t\tconst redo = (r) => this._render_reminders_card(r.message || []);
\t\t$host.find(".duty-rm-go").on("click", () => {
\t\t\tconst t = $host.find(".duty-rm-text").val();
\t\t\tconst dd = $host.find(".duty-rm-date").val();
\t\t\tconst tt = $host.find(".duty-rm-time").val();
\t\t\tif (!t || !dd || !tt) return frappe.show_alert({ message: __("Text, date and time, please."), indicator: "orange" });
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.reminders.add_reminder",
\t\t\t\targs: { text: t, remind_at: `${dd} ${tt}:00`, repeat: $host.find(".duty-rm-rep-sel").val() },
\t\t\t\tcallback: (r) => { frappe.show_alert({ message: __("Reminder set."), indicator: "green" }); redo(r); },
\t\t\t});
\t\t});
\t\t$host.find(".duty-rm-cancel").on("click", (e) =>
\t\t\tfrappe.call({ method: "duty_board.reminders.cancel_reminder", args: { name: $(e.currentTarget).data("id") }, callback: redo })
\t\t);
\t}

\t_load_earnings_card() {'''

CSS_OLD = '\t\t\t.duty-px-date-row input { max-width: 170px; }'
CSS_NEW = '''\t\t\t.duty-px-date-row input { max-width: 170px; }
\t\t\t.duty-rm-rep { font-size: 11px; font-weight: 700; color: #0F5C55; background: #E7F5EF; border-radius: 20px; padding: 2px 8px; }
\t\t\t.duty-lv-ask .duty-rm-text { max-width: 240px; }
\t\t\t.duty-lv-ask .duty-rm-date, .duty-lv-ask .duty-rm-time { max-width: 140px; }
\t\t\t.duty-lv-ask .duty-rm-rep-sel { max-width: 110px; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, HOOKS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if os.path.exists(os.path.join(root, REM)):
        print("Already applied. Nothing to do.")
        return
    if '"3.74.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.74.0.")

    checks = [
        (HOOKS, HK_OLD, "cron", 1), (JS, PL_OLD, "placeholder", 1),
        (JS, LD_OLD, "loader", 1), (JS, MT_OLD, "methods", 1), (JS, CSS_OLD, "css", 1),
    ]
    problems = [f"  [{files[f].count(o)} != {n}] {label}" for f, o, label, n in checks if files[f].count(o) != n]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    rdir = os.path.join(root, RDIR)
    os.makedirs(rdir, exist_ok=True)
    with io.open(os.path.join(rdir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(rdir, "duty_reminder.json"), "w", encoding="utf-8") as f:
        json.dump(REM_DT, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(rdir, "duty_reminder.py"), "w", encoding="utf-8") as f:
        f.write("import frappe\nfrom frappe.model.document import Document\n\n\nclass DutyReminder(Document):\n\tpass\n")
    with io.open(os.path.join(root, REM), "w", encoding="utf-8") as f:
        f.write(REM_PY)
    print("  doctype + reminders.py created")

    files[HOOKS] = files[HOOKS].replace(HK_OLD, HK_NEW, 1)
    js = files[JS]
    for o, n in [(PL_OLD, PL_NEW), (LD_OLD, LD_NEW), (MT_OLD, MT_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    files[JS] = js
    files[INIT] = files[INIT].replace('"3.74.0"', '"3.75.0"')

    for p in (HOOKS, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  hooks cron + ⏰ Me-face card wired")
    print("wrote __init__.py -> 3.75.0")


if __name__ == "__main__":
    main()
