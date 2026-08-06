#!/usr/bin/env python3
"""Duty Board v3.59.1 — pause a task on clock-out, resume it by hand.

When you clock out, whatever Work Session is running already ends and
banks its time (existing behaviour). This adds memory: what you were
working on is captured into a Duty Paused Task so that when you clock
back in, the board offers it back — you click Resume, which opens a
fresh session on the same activity/customer/issue/card. Per decision,
resume is MANUAL: paused tasks are shown, never auto-started.

Time accounting is untouched: each Work Session already banks its own
duration against the todo, so a task worked across a pause simply has
two sessions that sum correctly. "Pause" stores no clock — only what to
reopen.

New doctype: Duty Paused Task (one per user, field-named).
Hooks: clock_out captures; clock_in leaves it (manual resume); a
resume_paused_task endpoint starts the session and clears the record;
a dismiss_paused_task endpoint clears it without resuming; get_board
surfaces my_paused.

Deploy: bench migrate && bench build --app duty_board && bench restart

Anchored, all-or-nothing, idempotent. Requires v3.59.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
API = "duty_board/api.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
DT_DIR = "duty_board/duty_board/doctype/duty_paused_task"
CHECK_ONLY = "--check" in sys.argv

PAUSED_DOCTYPE = {
    "actions": [],
    "autoname": "field:user",
    "creation": "2026-08-07 09:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": ["user", "activity", "customer", "daily_todo", "duty_issue", "project_task", "paused_at"],
    "fields": [
        {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1, "unique": 1},
        {"fieldname": "activity", "fieldtype": "Small Text", "label": "Activity"},
        {"fieldname": "customer", "fieldtype": "Link", "label": "Customer", "options": "Customer"},
        {"fieldname": "daily_todo", "fieldtype": "Link", "label": "Daily Todo", "options": "Daily Todo"},
        {"fieldname": "duty_issue", "fieldtype": "Data", "label": "Duty Issue"},
        {"fieldname": "project_task", "fieldtype": "Data", "label": "Project Task"},
        {"fieldname": "paused_at", "fieldtype": "Datetime", "label": "Paused At"},
    ],
    "links": [],
    "modified": "2026-08-07 09:00:00.000000",
    "modified_by": "Administrator",
    "module": "Duty Board",
    "name": "Duty Paused Task",
    "naming_rule": "By fieldname",
    "owner": "Administrator",
    "permissions": [
        {"create": 1, "delete": 1, "email": 1, "export": 1, "print": 1, "read": 1, "report": 1, "role": "System Manager", "share": 1, "write": 1},
        {"create": 1, "read": 1, "delete": 1, "role": "All"},
    ],
    "sort_field": "modified",
    "sort_order": "DESC",
    "states": [],
}

# --- clock_out: capture the running session before it ends ------------------

API_CLOCKOUT_OLD = '''\trequire_staff()
\tif not reason:
\t\tfrappe.throw(_("Please give a reason for clocking out."))
\t_stop_running_session(frappe.session.user)'''
API_CLOCKOUT_NEW = '''\trequire_staff()
\tif not reason:
\t\tfrappe.throw(_("Please give a reason for clocking out."))
\t_capture_paused_task(frappe.session.user)
\t_stop_running_session(frappe.session.user)'''

# --- helper + endpoints: inserted before start_task -------------------------

API_HELPERS_OLD = '@frappe.whitelist()\ndef start_task(activity, customer=None, todo=None, complete_previous=0):'
API_HELPERS_NEW = '''def _capture_paused_task(user):
\t"""Remember the running session so clock-in can offer it back. One per
\tuser; a new pause overwrites the last (you resume the most recent thing)."""
\trunning = _get_running_session(user)
\tif not running:
\t\treturn
\tfrappe.db.delete("Duty Paused Task", {"user": user})
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Duty Paused Task",
\t\t\t"user": user,
\t\t\t"activity": running.activity,
\t\t\t"customer": running.customer,
\t\t\t"daily_todo": running.daily_todo,
\t\t\t"duty_issue": running.duty_issue,
\t\t\t"project_task": running.project_task,
\t\t\t"paused_at": now_datetime(),
\t\t}
\t).insert(ignore_permissions=True)
\tfrappe.db.commit()


def _my_paused(user):
\trow = frappe.db.get_value(
\t\t"Duty Paused Task",
\t\t{"user": user},
\t\t["name", "activity", "customer", "daily_todo", "paused_at"],
\t\tas_dict=True,
\t)
\tif not row:
\t\treturn None
\trow.paused_at = str(row.paused_at) if row.paused_at else None
\treturn row


@frappe.whitelist()
def resume_paused_task():
\t"""Reopen the paused task as a fresh Work Session, then clear the record."""
\trequire_staff()
\tuser = frappe.session.user
\tif not _is_clocked_in(user):
\t\tfrappe.throw(_("Clock in first before resuming."))
\trow = frappe.db.get_value(
\t\t"Duty Paused Task",
\t\t{"user": user},
\t\t["activity", "customer", "daily_todo", "duty_issue", "project_task"],
\t\tas_dict=True,
\t)
\tif not row:
\t\tfrappe.throw(_("Nothing paused to resume."))
\t_stop_running_session(user)
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Work Session",
\t\t\t"user": user,
\t\t\t"activity": row.activity or _("Resumed task"),
\t\t\t"customer": row.customer or None,
\t\t\t"daily_todo": row.daily_todo or None,
\t\t\t"duty_issue": row.duty_issue or None,
\t\t\t"project_task": row.project_task or None,
\t\t\t"start_time": now_datetime(),
\t\t}
\t).insert()
\tfrappe.db.delete("Duty Paused Task", {"user": user})
\tfrappe.db.commit()
\treturn get_board()


@frappe.whitelist()
def dismiss_paused_task():
\t"""Clear the paused task without resuming."""
\trequire_staff()
\tfrappe.db.delete("Duty Paused Task", {"user": frappe.session.user})
\tfrappe.db.commit()
\treturn get_board()


@frappe.whitelist()
def start_task(activity, customer=None, todo=None, complete_previous=0):'''

# --- start_task clears any stale paused record ------------------------------

API_STARTTASK_OLD = '''\tprevious = _stop_running_session(user)
\tif cint(complete_previous) and previous and previous.daily_todo:
\t\t_complete_todo(previous.daily_todo)'''
API_STARTTASK_NEW = '''\tprevious = _stop_running_session(user)
\tif cint(complete_previous) and previous and previous.daily_todo:
\t\t_complete_todo(previous.daily_todo)
\t# Starting anything fresh supersedes a paused task.
\tfrappe.db.delete("Duty Paused Task", {"user": user})'''

# --- get_board: surface my_paused -------------------------------------------

API_BOARD_OLD = '\tme = next((r for r in board if r["user"] == session), None)'
API_BOARD_NEW = '\tme = next((r for r in board if r["user"] == session), None)\n\tmy_paused = _my_paused(session)'

# find where the board dict returns 'me' to add my_paused alongside
API_RETURN_OLD = '\treturn {\n\t\t"me": me,\n\t\t"board": board,'
API_RETURN_NEW = '\treturn {\n\t\t"me": me,\n\t\t"my_paused": my_paused,\n\t\t"board": board,'

# --- JS: render the resume strip --------------------------------------------
# Hook: right after render_me(data.me) inside render(), where `data` is in scope.

JS_HOOK_OLD = '''\t\tthis.render_me(data.me);
\t\tthis.render_task(data.me);'''
JS_HOOK_NEW = '''\t\tthis.render_me(data.me);
\t\tthis.render_paused_strip(data);
\t\tthis.render_task(data.me);'''

# The method itself, added before render_task's definition.
JS_METHOD_OLD = "\trender_task(me) {"
JS_METHOD_NEW = '''\trender_paused_strip(data) {
\t\tconst host = this.body.find(".duty-me");
\t\thost.find(".duty-paused-strip").remove();
\t\tconst p = data && data.my_paused;
\t\tif (!p) return;
\t\tconst clocked = data.me && data.me.status === "On Duty";
\t\tconst esc = frappe.utils.escape_html;
\t\tconst $s = $(`
\t\t\t<div class="duty-paused-strip">
\t\t\t\t<span class="duty-paused-ic">⏸</span>
\t\t\t\t<span class="duty-paused-txt">
\t\t\t\t\t${__("Paused")}: <b>${esc(p.activity || __("a task"))}</b>${p.customer ? ` · ${esc(p.customer)}` : ""}
\t\t\t\t</span>
\t\t\t\t${clocked
\t\t\t\t\t? `<a class="duty-paused-resume">▶ ${__("Resume")}</a>`
\t\t\t\t\t: `<span class="duty-paused-hint">${__("Clock in to resume")}</span>`}
\t\t\t\t<a class="duty-paused-dismiss" title="${__("Dismiss")}">✕</a>
\t\t\t</div>`);
\t\thost.prepend($s);
\t\t$s.find(".duty-paused-resume").on("click", () => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.api.resume_paused_task",
\t\t\t\tfreeze: true,
\t\t\t\tcallback: (r) => { if (r.message) this.render(r.message); },
\t\t\t});
\t\t});
\t\t$s.find(".duty-paused-dismiss").on("click", () => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.api.dismiss_paused_task",
\t\t\t\tcallback: (r) => { if (r.message) this.render(r.message); },
\t\t\t});
\t\t});
\t}

\trender_task(me) {'''

JS_PAUSED_STYLE_OLD = '\t\t\t.duty-msg-edit:hover, .duty-cr-edit:hover, .duty-dm-edit:hover { opacity: 1; }'
JS_PAUSED_STYLE_NEW = JS_PAUSED_STYLE_OLD + '''
\t\t\t.duty-paused-strip { display: flex; align-items: center; gap: 10px; margin: 0 0 12px; padding: 9px 14px; background: #FFF7E6; border: 1px solid #F5D08A; border-radius: 10px; }
\t\t\t.duty-paused-ic { font-size: 16px; }
\t\t\t.duty-paused-txt { flex: 1; min-width: 0; font-size: 13px; }
\t\t\t.duty-paused-resume { cursor: pointer; font-weight: 700; color: #0F5C55; white-space: nowrap; }
\t\t\t.duty-paused-hint { font-size: 12px; color: var(--text-muted, #999); white-space: nowrap; }
\t\t\t.duty-paused-dismiss { cursor: pointer; opacity: .5; }
\t\t\t.duty-paused-dismiss:hover { opacity: 1; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, API, JS):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "_capture_paused_task" in files[API]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.0 — apply the message-edit patch first.")

    edits = [
        (API, API_CLOCKOUT_OLD, API_CLOCKOUT_NEW),
        (API, API_HELPERS_OLD, API_HELPERS_NEW),
        (API, API_STARTTASK_OLD, API_STARTTASK_NEW),
        (API, API_BOARD_OLD, API_BOARD_NEW),
        (API, API_RETURN_OLD, API_RETURN_NEW),
        (JS, JS_HOOK_OLD, JS_HOOK_NEW),
        (JS, JS_METHOD_OLD, JS_METHOD_NEW),
        (JS, JS_PAUSED_STYLE_OLD, JS_PAUSED_STYLE_NEW),
    ]

    problems = [f"  [{files[f].count(o)}] {f}: {o[:46]!r}" for f, o, _ in edits if files[f].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(edits)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # doctype
    os.makedirs(os.path.join(root, DT_DIR), exist_ok=True)
    with io.open(os.path.join(root, DT_DIR, "duty_paused_task.json"), "w", encoding="utf-8") as f:
        json.dump(PAUSED_DOCTYPE, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(root, DT_DIR, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(root, DT_DIR, "duty_paused_task.py"), "w", encoding="utf-8") as f:
        f.write("import frappe\nfrom frappe.model.document import Document\n\n\nclass DutyPausedTask(Document):\n\tpass\n")
    print("  doctype: Duty Paused Task created")

    out = dict(files)
    for f, old, new in edits:
        out[f] = out[f].replace(old, new, 1)

    for f in (API, JS, INIT):
        content = out[f]
        if f == INIT:
            content = content.replace('"3.59.0"', '"3.59.1"')
        with io.open(os.path.join(root, f), "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"  wrote {f}")
    print("wrote __init__.py -> 3.59.1")


if __name__ == "__main__":
    main()
