#!/usr/bin/env python3
"""Duty Board v3.59.2 — the task stack: juggle without losing anything.

DESIGN (per decision): fast SWITCHING, never parallel clocks. One Work
Session runs at a time so every number stays truthful — task time can
never exceed on-duty time, _day_numbers stays honest, the team board
stays unambiguous. What changes is that switching no longer DISCARDS:

- start_task now PAUSES the running task into the stack (unless you
  ticked "completed", which keeps its existing meaning).
- The stack holds up to 5 paused tasks per user (newest kept; overflow
  drops the oldest). Beyond five it's not a stack, it's a graveyard.
- The board strip becomes a tray listing every paused task with its
  age; ▶ resumes that one (pausing whatever you're on), ✕ dismisses it.
- Starting a task whose activity matches a paused entry consumes that
  entry — typing the same task by hand counts as resuming it.
- Clock-out still captures the running task (additively now).

Doctype change: Duty Paused Task drops one-per-user (autoname hash,
unique removed) — bench migrate applies it whether or not v3.59.1 was
ever migrated on this bench.

Deploy: bench migrate && bench build --app duty_board && bench restart

Anchored, all-or-nothing, idempotent. Requires v3.59.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
API = "duty_board/api.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
DT = "duty_board/duty_board/doctype/duty_paused_task/duty_paused_task.json"
CHECK_ONLY = "--check" in sys.argv

STACK_CAP = 5

# --- 1. _capture_paused_task: additive, deduped, capped ----------------------

A1_OLD = '\tfrappe.db.delete("Duty Paused Task", {"user": user})\n\tfrappe.get_doc('
A1_NEW = '''\t# Additive: this joins the stack rather than replacing it. Dedupe on
\t# activity so pausing the same task twice keeps one entry (the fresh one).
\tfrappe.db.delete(
\t\t"Duty Paused Task", {"user": user, "activity": (running.activity or "").strip()}
\t)
\tfrappe.get_doc('''

A2_OLD = '\t).insert(ignore_permissions=True)\n\tfrappe.db.commit()\n\n\ndef _my_paused(user):'
A2_NEW = '''\t).insert(ignore_permissions=True)
\t# Cap the stack: keep the newest {cap}, drop the oldest overflow.
\textras = frappe.get_all(
\t\t"Duty Paused Task",
\t\tfilters={{"user": user}},
\t\torder_by="paused_at desc",
\t\tpluck="name",
\t)[{cap}:]
\tfor name in extras:
\t\tfrappe.delete_doc("Duty Paused Task", name, ignore_permissions=True, force=True)
\tfrappe.db.commit()


def _my_paused(user):'''.format(cap=STACK_CAP)

# --- 2. _my_paused returns the whole stack -----------------------------------

A3_OLD = '''def _my_paused(user):
\trow = frappe.db.get_value(
\t\t"Duty Paused Task",
\t\t{"user": user},
\t\t["name", "activity", "customer", "daily_todo", "paused_at"],
\t\tas_dict=True,
\t)
\tif not row:
\t\treturn None
\trow.paused_at = str(row.paused_at) if row.paused_at else None
\treturn row'''

A3_NEW = '''def _my_paused(user):
\trows = frappe.get_all(
\t\t"Duty Paused Task",
\t\tfilters={"user": user},
\t\tfields=["name", "activity", "customer", "daily_todo", "paused_at"],
\t\torder_by="paused_at desc",
\t\tlimit=%d,
\t)
\tfor r in rows:
\t\tr.paused_at = str(r.paused_at) if r.paused_at else None
\treturn rows''' % STACK_CAP

# --- 3. resume a SPECIFIC entry, pausing the current one first ---------------

A4_OLD = '''@frappe.whitelist()
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
\treturn get_board()'''

A4_NEW = '''@frappe.whitelist()
def resume_paused_task(name=None):
\t"""Reopen ONE paused task as a fresh Work Session, pausing whatever is
\trunning now. No name = the most recently paused."""
\trequire_staff()
\tuser = frappe.session.user
\tif not _is_clocked_in(user):
\t\tfrappe.throw(_("Clock in first before resuming."))
\tfilters = {"user": user}
\tif name:
\t\tfilters["name"] = name
\trows = frappe.get_all(
\t\t"Duty Paused Task",
\t\tfilters=filters,
\t\tfields=["name", "activity", "customer", "daily_todo", "duty_issue", "project_task"],
\t\torder_by="paused_at desc",
\t\tlimit=1,
\t)
\tif not rows:
\t\tfrappe.throw(_("Nothing paused to resume."))
\trow = rows[0]
\t# The task you are leaving joins the stack; the one you resume leaves it.
\t_capture_paused_task(user)
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
\tfrappe.delete_doc("Duty Paused Task", row.name, ignore_permissions=True, force=True)
\tfrappe.db.commit()
\treturn get_board()'''

# --- 4. dismiss a SPECIFIC entry (no name = clear all, old behaviour) --------

A5_OLD = '''@frappe.whitelist()
def dismiss_paused_task():
\t"""Clear the paused task without resuming."""
\trequire_staff()
\tfrappe.db.delete("Duty Paused Task", {"user": frappe.session.user})
\tfrappe.db.commit()
\treturn get_board()'''

A5_NEW = '''@frappe.whitelist()
def dismiss_paused_task(name=None):
\t"""Drop one paused task (or all of them, with no name) without resuming."""
\trequire_staff()
\tfilters = {"user": frappe.session.user}
\tif name:
\t\tfilters["name"] = name
\tfrappe.db.delete("Duty Paused Task", filters)
\tfrappe.db.commit()
\treturn get_board()'''

# --- 5. start_task: pause, don't discard -------------------------------------

A6_OLD = '''\tprevious = _stop_running_session(user)
\tif cint(complete_previous) and previous and previous.daily_todo:
\t\t_complete_todo(previous.daily_todo)
\t# Starting anything fresh supersedes a paused task.
\tfrappe.db.delete("Duty Paused Task", {"user": user})'''

A6_NEW = '''\t# Switching pauses the running task instead of discarding it — unless
\t# you marked it completed, in which case it is done, not paused.
\tif not cint(complete_previous):
\t\t_capture_paused_task(user)
\tprevious = _stop_running_session(user)
\tif cint(complete_previous) and previous and previous.daily_todo:
\t\t_complete_todo(previous.daily_todo)
\t# Typing a task that matches a paused entry IS resuming it by hand.
\tfrappe.db.delete("Duty Paused Task", {"user": user, "activity": activity.strip()})'''

# --- 6. JS: the tray ---------------------------------------------------------

JS_METHOD_OLD = '''\trender_paused_strip(data) {
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
\t}'''

JS_METHOD_NEW = '''\trender_paused_strip(data) {
\t\tconst host = this.body.find(".duty-me");
\t\thost.find(".duty-paused-strip").remove();
\t\tconst stack = (data && data.my_paused) || [];
\t\tif (!stack.length) return;
\t\tconst clocked = data.me && data.me.status === "On Duty";
\t\tconst esc = frappe.utils.escape_html;
\t\tconst $s = $(`
\t\t\t<div class="duty-paused-strip">
\t\t\t\t<div class="duty-paused-head">
\t\t\t\t\t<span class="duty-paused-ic">⏸</span>
\t\t\t\t\t<b>${__("Paused")} (${stack.length})</b>
\t\t\t\t\t${clocked ? "" : `<span class="duty-paused-hint">${__("Clock in to resume")}</span>`}
\t\t\t\t</div>
\t\t\t\t${stack
\t\t\t\t\t.map(
\t\t\t\t\t\t(p) => `
\t\t\t\t<div class="duty-paused-row" data-name="${esc(p.name)}">
\t\t\t\t\t<span class="duty-paused-txt">
\t\t\t\t\t\t<b>${esc(p.activity || __("a task"))}</b>${p.customer ? ` · ${esc(p.customer)}` : ""}
\t\t\t\t\t\t<span class="duty-paused-age">${p.paused_at ? frappe.datetime.comment_when(p.paused_at) : ""}</span>
\t\t\t\t\t</span>
\t\t\t\t\t${clocked ? `<a class="duty-paused-resume">▶ ${__("Resume")}</a>` : ""}
\t\t\t\t\t<a class="duty-paused-dismiss" title="${__("Dismiss")}">✕</a>
\t\t\t\t</div>`
\t\t\t\t\t)
\t\t\t\t\t.join("")}
\t\t\t</div>`);
\t\thost.prepend($s);
\t\t$s.find(".duty-paused-resume").on("click", (e) => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.api.resume_paused_task",
\t\t\t\targs: { name: $(e.currentTarget).closest(".duty-paused-row").attr("data-name") },
\t\t\t\tfreeze: true,
\t\t\t\tcallback: (r) => { if (r.message) this.render(r.message); },
\t\t\t});
\t\t});
\t\t$s.find(".duty-paused-dismiss").on("click", (e) => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.api.dismiss_paused_task",
\t\t\t\targs: { name: $(e.currentTarget).closest(".duty-paused-row").attr("data-name") },
\t\t\t\tcallback: (r) => { if (r.message) this.render(r.message); },
\t\t\t});
\t\t});
\t}'''

# --- 7. styles ---------------------------------------------------------------

JS_STYLE_OLD = '\t\t\t.duty-paused-dismiss:hover { opacity: 1; }'
JS_STYLE_NEW = JS_STYLE_OLD + '''
\t\t\t.duty-paused-strip { display: block; }
\t\t\t.duty-paused-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 13px; }
\t\t\t.duty-paused-row { display: flex; align-items: center; gap: 10px; padding: 5px 0 5px 26px; border-top: 1px dashed #F0DFB6; }
\t\t\t.duty-paused-row:first-of-type { border-top: 0; }
\t\t\t.duty-paused-age { font-size: 11px; color: var(--text-muted, #999); margin-left: 6px; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, API, JS):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()
    if not os.path.exists(os.path.join(root, DT)):
        sys.exit("ABORT: Duty Paused Task doctype missing — apply v3.59.1 first.")

    if "def resume_paused_task(name=None):" in files[API]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.1 — apply earlier patches first.")

    edits = [
        (API, A1_OLD, A1_NEW),
        (API, A2_OLD, A2_NEW),
        (API, A3_OLD, A3_NEW),
        (API, A4_OLD, A4_NEW),
        (API, A5_OLD, A5_NEW),
        (API, A6_OLD, A6_NEW),
        (JS, JS_METHOD_OLD, JS_METHOD_NEW),
        (JS, JS_STYLE_OLD, JS_STYLE_NEW),
    ]
    problems = [f"  [{files[f].count(o)}] {f}: {o[:44]!r}" for f, o, _ in edits if files[f].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(edits)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # doctype: many-per-user
    with io.open(os.path.join(root, DT), encoding="utf-8") as f:
        dt = json.load(f)
    dt["autoname"] = "hash"
    dt["naming_rule"] = "Random"
    for fld in dt["fields"]:
        if fld["fieldname"] == "user":
            fld.pop("unique", None)
    with io.open(os.path.join(root, DT), "w", encoding="utf-8") as f:
        json.dump(dt, f, indent=1)
        f.write("\n")
    print("  doctype: Duty Paused Task -> many per user (hash-named)")

    out = dict(files)
    for f, old, new in edits:
        out[f] = out[f].replace(old, new, 1)
    for f in (API, JS, INIT):
        content = out[f]
        if f == INIT:
            content = content.replace('"3.59.1"', '"3.59.2"')
        with io.open(os.path.join(root, f), "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"  wrote {f}")
    print("wrote __init__.py -> 3.59.2")


if __name__ == "__main__":
    main()
