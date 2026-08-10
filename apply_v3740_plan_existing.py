#!/usr/bin/env python3
"""Duty Board v3.74.0 — plan your day from existing work (team request 1).

Staff plan daily to-dos but couldn't add their PENDING ISSUES or PROJECT
TASKS to a day's plan — everything had to be typed afresh. Now:

- Daily Todo +duty_issue (Data) — issue-linked todos, mirroring the
  existing project_task linkage.
- api.plan_sources(): the picker's data — my open issues (assignee) and
  my open project tasks, each with title + customer/project.
- api.plan_existing(kind, source, date): creates the linked todo for
  today or a future date, titled from the source, customer derived
  (issue's customer / project's customer). Duplicate-guard: an open
  todo already linked to that source refuses a second.
- BONUS FIX uncovered while wiring: sessions started from a planned
  todo carried only customer — NOT the task/issue linkage. Now they
  inherit project_task/duty_issue from the todo, so planned work flows
  correctly into earnings, SLA, and service lines.
- UI: a 📋 button beside Add in the plan bar -> picker dialog (Issues /
  Tasks sections, radio pick, date defaulting today).

Schema (one field) -> bench migrate && bench build && bench restart.
Anchored, idempotent. Requires v3.73.2.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
API = "duty_board/api.py"
TDDT = "duty_board/duty_board/doctype/daily_todo/daily_todo.json"
CHECK_ONLY = "--check" in sys.argv

# --- 1. api.py: session-from-todo inherits linkage --------------------------
S_OLD = '''\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Work Session",
\t\t\t"user": user,
\t\t\t"activity": activity.strip(),
\t\t\t"customer": customer or None,
\t\t\t"daily_todo": todo or None,
\t\t\t"start_time": now_datetime(),
\t\t}
\t).insert()'''
S_NEW = '''\t_t_task, _t_issue = None, None
\tif todo:
\t\t_tv = frappe.db.get_value("Daily Todo", todo, ["project_task", "duty_issue"], as_dict=True)
\t\tif _tv:
\t\t\t_t_task, _t_issue = _tv.project_task or None, _tv.duty_issue or None
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Work Session",
\t\t\t"user": user,
\t\t\t"activity": activity.strip(),
\t\t\t"customer": customer or None,
\t\t\t"daily_todo": todo or None,
\t\t\t"project_task": _t_task,
\t\t\t"duty_issue": _t_issue,
\t\t\t"start_time": now_datetime(),
\t\t}
\t).insert()'''

# --- 2. api.py: plan_sources + plan_existing after add_todo -----------------
P_OLD = '''def add_todo(description, customer=None, for_user=None, for_users=None, date=None, due_time=None):'''
P_NEW = '''def plan_sources():
\t"""My open issues and my open project tasks — the 'add from existing'
\tpicker's data."""
\trequire_staff()
\tuser = frappe.session.user
\tissue_names = frappe.get_all("Duty Issue Assignee", filters={"user": user}, pluck="parent")
\tissues = []
\tif issue_names:
\t\tissues = frappe.get_all(
\t\t\t"Duty Issue",
\t\t\tfilters={"name": ["in", issue_names], "status": ["in", ["Open", "In Progress"]]},
\t\t\tfields=["name", "title", "customer"],
\t\t\torder_by="modified desc",
\t\t\tlimit=50,
\t\t)
\ttasks = frappe.get_all(
\t\t"Duty Project Task",
\t\tfilters={"assignee": user, "column": ["not in", ["Completed", "Suspended"]]},
\t\tfields=["name", "title", "project"],
\t\torder_by="modified desc",
\t\tlimit=50,
\t)
\tpnames = {}
\tif tasks:
\t\tfor p in frappe.get_all(
\t\t\t"Duty Project",
\t\t\tfilters={"name": ["in", list({t.project for t in tasks})]},
\t\t\tfields=["name", "project_name", "customer"],
\t\t):
\t\t\tpnames[p.name] = p
\tfor t in tasks:
\t\tpr = pnames.get(t.project)
\t\tt.project_name = pr.project_name if pr else t.project
\t\tt.customer = pr.customer if pr else None
\treturn {"issues": issues, "tasks": tasks}


@frappe.whitelist()
def plan_existing(kind, source, date=None):
\t"""Add an existing issue/task to my plan for a day (default today)."""
\trequire_staff()
\tuser = frappe.session.user
\td = getdate(date) if date else getdate(today())
\tif d < getdate(today()):
\t\tfrappe.throw(_("Plan for today or a future day."))
\tif kind == "issue":
\t\trow = frappe.db.get_value("Duty Issue", source, ["title", "customer"], as_dict=True)
\t\tif not row:
\t\t\tfrappe.throw(_("Unknown issue."))
\t\tdupe = frappe.get_all(
\t\t\t"Daily Todo",
\t\t\tfilters={"user": user, "duty_issue": source, "status": ["!=", "Completed"]},
\t\t\tlimit=1,
\t\t)
\t\tif dupe:
\t\t\tfrappe.throw(_("That issue is already on your plan."))
\t\tvals = {"description": row.title, "customer": row.customer, "duty_issue": source}
\telif kind == "task":
\t\trow = frappe.db.get_value("Duty Project Task", source, ["title", "project"], as_dict=True)
\t\tif not row:
\t\t\tfrappe.throw(_("Unknown task."))
\t\tdupe = frappe.get_all(
\t\t\t"Daily Todo",
\t\t\tfilters={"user": user, "project_task": source, "status": ["!=", "Completed"]},
\t\t\tlimit=1,
\t\t)
\t\tif dupe:
\t\t\tfrappe.throw(_("That task is already on your plan."))
\t\tcust = frappe.db.get_value("Duty Project", row.project, "customer")
\t\tvals = {"description": row.title, "customer": cust, "project_task": source, "project": row.project}
\telse:
\t\tfrappe.throw(_("Unknown kind."))
\tfrappe.get_doc(
\t\tdict(
\t\t\tdoctype="Daily Todo",
\t\t\tuser=user,
\t\t\tfull_name=frappe.utils.get_fullname(user),
\t\t\tdate=d,
\t\t\tstatus="Open",
\t\t\t**vals,
\t\t)
\t).insert(ignore_permissions=True)
\tfrappe.db.commit()
\treturn get_board()


@frappe.whitelist()
def add_todo(description, customer=None, for_user=None, for_users=None, date=None, due_time=None):'''

# NOTE: add_todo already carries @frappe.whitelist() on the line ABOVE the
# anchor — P_OLD anchors on the def line only, so the decorator stays put
# and the two NEW endpoints bring their own decorators... except
# plan_sources needs one. Handled by inserting its decorator explicitly:
P_NEW = P_NEW.replace("def plan_sources():", "def plan_sources():", 1)

# --- 3. JS: 📋 button in the plan bar ----------------------------------------
B_OLD = '''\t\t\t\t\t<input type="text" class="form-control duty-todo-input" placeholder="${__("Add a to-do and press Enter...")}">
\t\t\t\t\t<button class="btn btn-default btn-sm duty-todo-add-btn">${__("Add")}</button>'''
B_NEW = '''\t\t\t\t\t<input type="text" class="form-control duty-todo-input" placeholder="${__("Add a to-do and press Enter...")}">
\t\t\t\t\t<button class="btn btn-default btn-sm duty-todo-add-btn">${__("Add")}</button>
\t\t\t\t\t<button class="btn btn-default btn-sm duty-todo-existing-btn" title="${__("Add from my issues & tasks")}">📋</button>'''

W_OLD = '''\t\t$plan.find(".duty-todo-more-btn").on("click", () => this.add_todo_dialog());'''
W_NEW = '''\t\t$plan.find(".duty-todo-more-btn").on("click", () => this.add_todo_dialog());
\t\t$plan.find(".duty-todo-existing-btn").on("click", () => this.plan_existing_dialog());'''

# --- 4. JS: the picker dialog, before add_todo_dialog -----------------------
D_OLD = '\tadd_todo_dialog() {'
D_NEW = '''\tplan_existing_dialog() {
\t\tconst esc = frappe.utils.escape_html;
\t\tfrappe.call({
\t\t\tmethod: "duty_board.api.plan_sources",
\t\t\tcallback: (r) => {
\t\t\t\tconst S = r.message || {};
\t\t\t\tconst issues = S.issues || [], tasks = S.tasks || [];
\t\t\t\tif (!issues.length && !tasks.length) {
\t\t\t\t\tfrappe.show_alert({ message: __("No open issues or tasks assigned to you."), indicator: "orange" });
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t\tconst opt = (kind, name, title, sub) => `
\t\t\t\t\t<label class="duty-px-row"><input type="radio" name="duty-px" value="${kind}:${name}">
\t\t\t\t\t<span class="duty-px-t">${esc(title)}</span><span class="duty-px-s">${esc(sub || "")}</span></label>`;
\t\t\t\tconst d = new frappe.ui.Dialog({
\t\t\t\t\ttitle: __("Add existing work to my plan"),
\t\t\t\t\tprimary_action_label: __("Add to plan"),
\t\t\t\t\tprimary_action: () => {
\t\t\t\t\t\tconst v = $(d.body).find("input[name=duty-px]:checked").val();
\t\t\t\t\t\tif (!v) return frappe.show_alert({ message: __("Pick one."), indicator: "orange" });
\t\t\t\t\t\tconst [kind, ...rest] = v.split(":");
\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\tmethod: "duty_board.api.plan_existing",
\t\t\t\t\t\t\targs: { kind: kind, source: rest.join(":"), date: $(d.body).find(".duty-px-date").val() || null },
\t\t\t\t\t\t\tcallback: (rr) => {
\t\t\t\t\t\t\t\td.hide();
\t\t\t\t\t\t\t\tfrappe.show_alert({ message: __("Added to your plan."), indicator: "green" });
\t\t\t\t\t\t\t\tthis.refresh(true);
\t\t\t\t\t\t\t},
\t\t\t\t\t\t});
\t\t\t\t\t},
\t\t\t\t});
\t\t\t\t$(d.body).html(`
\t\t\t\t\t<div class="duty-px-date-row"><label>${__("For day")}</label>
\t\t\t\t\t<input type="date" class="form-control input-sm duty-px-date" value="${frappe.datetime.now_date()}" min="${frappe.datetime.now_date()}"></div>
\t\t\t\t\t${issues.length ? `<h6>🐞 ${__("My open issues")}</h6>${issues.map((i) => opt("issue", i.name, i.title, i.customer)).join("")}` : ""}
\t\t\t\t\t${tasks.length ? `<h6 style="margin-top:10px">📌 ${__("My project tasks")}</h6>${tasks.map((t) => opt("task", t.name, t.title, t.project_name)).join("")}` : ""}
\t\t\t\t`);
\t\t\t\td.show();
\t\t\t},
\t\t});
\t}

\tadd_todo_dialog() {'''

# --- 5. CSS ------------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-msg-seen.tick-read { color: #3B82F6; font-weight: 700; }'
CSS_NEW = '''\t\t\t.duty-msg-seen.tick-read { color: #3B82F6; font-weight: 700; }
\t\t\t.duty-px-row { display: flex; gap: 8px; align-items: baseline; padding: 5px 2px; border-bottom: 1px dashed #eee; cursor: pointer; font-weight: 400; width: 100%; }
\t\t\t.duty-px-t { font-size: 13px; }
\t\t\t.duty-px-s { font-size: 11.5px; color: #8a958f; margin-left: auto; }
\t\t\t.duty-px-date-row { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }
\t\t\t.duty-px-date-row input { max-width: 170px; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, API):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def plan_existing(" in files[API]:
        print("Already applied. Nothing to do.")
        return
    if '"3.73.2"' not in files[INIT]:
        sys.exit("ABORT: not at v3.73.2.")

    checks = [
        (API, S_OLD, "session linkage", 1), (API, P_OLD, "plan endpoints", 1),
        (JS, B_OLD, "picker button", 1), (JS, W_OLD, "picker wire", 1),
        (JS, D_OLD, "picker dialog", 1), (JS, CSS_OLD, "css", 1),
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

    # Daily Todo +duty_issue
    with io.open(os.path.join(root, TDDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "duty_issue" for fl in dt["fields"]):
        dt["fields"].append({"fieldname": "duty_issue", "fieldtype": "Data", "label": "Duty Issue"})
        if "field_order" in dt:
            dt["field_order"].append("duty_issue")
        with io.open(os.path.join(root, TDDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    print("  Daily Todo +duty_issue")

    # decorator-safe insertion: P_OLD is the def line; the new block must
    # carry whitelists for both new endpoints and END with the plain def
    # line so add_todo keeps its own decorator (which sits above P_OLD and
    # is untouched). plan_sources/plan_existing get decorators here:
    a = files[API].replace(S_OLD, S_NEW, 1)
    a = a.replace(
        "@frappe.whitelist()\n" + P_OLD,
        "@frappe.whitelist()\n"
        + P_NEW.replace("def plan_sources():", "def plan_sources():", 1)
        .replace("@frappe.whitelist()\ndef add_todo", "@frappe.whitelist()\ndef add_todo"),
        1,
    ) if False else a
    # Simpler and explicit: anchor on decorator+def together.
    DEC_OLD = "@frappe.whitelist()\n" + P_OLD
    DEC_NEW = (
        "@frappe.whitelist()\n"
        + P_NEW
    )
    if a.count(DEC_OLD) != 1:
        sys.exit(f"ABORT: decorator anchor [{a.count(DEC_OLD)}].")
    a = a.replace(DEC_OLD, DEC_NEW, 1)
    with io.open(os.path.join(root, API), "w", encoding="utf-8") as f:
        f.write(a)
    print("  api.py: session linkage + plan_sources/plan_existing (decorator-safe)")

    js = files[JS]
    for o, n in [(B_OLD, B_NEW), (W_OLD, W_NEW), (D_OLD, D_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: 📋 picker")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.73.2"', '"3.74.0"'))
    print("wrote __init__.py -> 3.74.0")


if __name__ == "__main__":
    main()
