#!/usr/bin/env python3
"""Duty Board v3.77.0 — project STAFF assignment (corrects v3.76.0's model).

The gap v3.76.0 missed: "Consultants" on a project is the EXTERNAL
client-side grant table (its setter even validates the Consultant
role) — there was no staff assignment at all. This builds it:

- New child doctype Duty Project Staff; Duty Project +staff table.
- 👥 Team button beside 👷 Consultants on the project bar: checkbox
  roster (from the Duty Settings user-rates table — your payroll
  roster), editable by System Managers and the project's creator;
  read-only view for everyone else. Newly added staff are notified.
- Visibility filter + board guard re-pointed: non-SM staff see projects
  where they're in the STAFF table (or creator). Consultant-side
  filtering untouched.
- create_project: creator lands in the STAFF table — reverting v3.76's
  accidental insertion of staff into the external consultants grant.
- EARNINGS FIX: _phase_items split phase bonuses over Duty Project
  Consultant — external users — meaning staff phase bonuses would
  never pay. Both references now read Duty Project Staff.

Rollout: assign teams via 👥 Team on each project right after deploy —
projects with an empty staff table are visible only to SMs + creator.

Schema (child doctype + field) -> bench migrate && bench build
--app duty_board && bench restart. Anchored, idempotent. Requires v3.76.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
EARN = "duty_board/earnings.py"
PDT = "duty_board/duty_board/doctype/duty_project/duty_project.json"
SDIR = "duty_board/duty_board/doctype/duty_project_staff"
CHECK_ONLY = "--check" in sys.argv

STAFF_DT = {
    "actions": [], "autoname": "hash",
    "creation": "2026-08-10 09:00:00.000000", "doctype": "DocType",
    "engine": "InnoDB", "istable": 1,
    "field_order": ["user"],
    "fields": [
        {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1, "in_list_view": 1},
    ],
    "links": [], "modified": "2026-08-10 09:00:00.000000",
    "modified_by": "Administrator", "module": "Duty Board",
    "name": "Duty Project Staff", "naming_rule": "Random", "owner": "Administrator",
    "permissions": [], "sort_field": "modified", "sort_order": "DESC", "states": [],
}

# --- projects.py -------------------------------------------------------------
A_OLD = '\t\t\t"consultants": [{"user": frappe.session.user}],'
A_NEW = '\t\t\t"staff": [{"user": frappe.session.user}],'

B_OLD = '''\telif "System Manager" not in frappe.get_roles():
\t\t_mine = set(
\t\t\tfrappe.get_all(
\t\t\t\t"Duty Project Consultant",
\t\t\t\tfilters={"user": frappe.session.user},
\t\t\t\tpluck="parent",
\t\t\t)
\t\t)'''
B_NEW = '''\telif "System Manager" not in frappe.get_roles():
\t\t_mine = set(
\t\t\tfrappe.get_all(
\t\t\t\t"Duty Project Staff",
\t\t\t\tfilters={"user": frappe.session.user},
\t\t\t\tpluck="parent",
\t\t\t)
\t\t)'''

C_OLD = '''\tif not require_staff_or_consultant() and "System Manager" not in frappe.get_roles():
\t\t_ok = frappe.get_all(
\t\t\t"Duty Project Consultant",
\t\t\tfilters={"parent": project, "user": frappe.session.user},
\t\t\tlimit=1,
\t\t) or frappe.db.get_value("Duty Project", project, "owner") == frappe.session.user'''
C_NEW = '''\tif not require_staff_or_consultant() and "System Manager" not in frappe.get_roles():
\t\t_ok = frappe.get_all(
\t\t\t"Duty Project Staff",
\t\t\tfilters={"parent": project, "user": frappe.session.user},
\t\t\tlimit=1,
\t\t) or frappe.db.get_value("Duty Project", project, "owner") == frappe.session.user'''

D_OLD = '''\t\t"consultants": [
\t\t\tr.user
\t\t\tfor r in frappe.get_all(
\t\t\t\t"Duty Project Consultant", filters={"parent": project}, fields=["user"]
\t\t\t)
\t\t],
\t}'''
D_NEW = '''\t\t"consultants": [
\t\t\tr.user
\t\t\tfor r in frappe.get_all(
\t\t\t\t"Duty Project Consultant", filters={"parent": project}, fields=["user"]
\t\t\t)
\t\t],
\t\t"staff": [
\t\t\t{"user": r.user, "full_name": frappe.utils.get_fullname(r.user)}
\t\t\tfor r in frappe.get_all(
\t\t\t\t"Duty Project Staff", filters={"parent": project}, fields=["user"]
\t\t\t)
\t\t],
\t}'''

E_APPEND = '''

def _can_edit_team(doc):
	return (
		"System Manager" in frappe.get_roles()
		or doc.owner == frappe.session.user
	)


@frappe.whitelist()
def project_staff_options(project):
	"""The staff roster (Duty Settings user-rates table) with membership
	flags for the 👥 Team dialog."""
	require_staff()
	doc = frappe.get_doc("Duty Project", project)
	members = {r.user for r in (doc.get("staff") or [])}
	roster = sorted(
		set(
			frappe.get_all(
				"Duty User Rate",
				filters={"parenttype": "Duty Settings"},
				pluck="user",
			)
		)
	)
	options = [
		{"user": u, "full_name": frappe.utils.get_fullname(u), "member": 1 if u in members else 0}
		for u in roster
	]
	options.sort(key=lambda x: x["full_name"] or "")
	return {"options": options, "can_edit": 1 if _can_edit_team(doc) else 0}


@frappe.whitelist()
def project_staff_set(project, users):
	"""Replace the project's staff team. System Managers and the
	project's creator only. Newly added staff are notified."""
	require_staff()
	import json as _json

	users = _json.loads(users) if isinstance(users, str) else (users or [])
	doc = frappe.get_doc("Duty Project", project)
	if not _can_edit_team(doc):
		frappe.throw(_("Only managers or the project's creator set the team."), frappe.PermissionError)
	roster = set(
		frappe.get_all(
			"Duty User Rate", filters={"parenttype": "Duty Settings"}, pluck="user"
		)
	)
	before = {r.user for r in (doc.get("staff") or [])}
	doc.set("staff", [])
	for u in users:
		if u in roster:
			doc.append("staff", {"user": u})
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	first = frappe.utils.get_fullname(frappe.session.user).split(" ")[0]
	for u in set(users) - before:
		try:
			_notify(u, _("👥 Added to project team by {0}").format(first), doc.project_name)
		except Exception:
			pass
	return project_staff_options(project)
'''

# --- earnings.py: phase bonus reads the STAFF table -------------------------
F_OLD = '''\tprojects = frappe.get_all(
\t\t"Duty Project Consultant", filters={"user": user}, pluck="parent"
\t)'''
F_NEW = '''\tprojects = frappe.get_all(
\t\t"Duty Project Staff", filters={"user": user}, pluck="parent"
\t)'''

G_OLD = '\t\tn = max(frappe.db.count("Duty Project Consultant", {"parent": m.project}), 1)'
G_NEW = '\t\tn = max(frappe.db.count("Duty Project Staff", {"parent": m.project}), 1)'

# --- JS ----------------------------------------------------------------------
J1_OLD = '''\t\t\t\t<a class="duty-proj-cons">👷 ${__("Consultants")}${(data.consultants || []).length ? ` <b>${data.consultants.length}</b>` : ""}</a>'''
J1_NEW = '''\t\t\t\t<a class="duty-proj-staffb">👥 ${__("Team")}${(data.staff || []).length ? ` <b>${data.staff.length}</b>` : ""}</a>
\t\t\t\t<a class="duty-proj-cons">👷 ${__("Consultants")}${(data.consultants || []).length ? ` <b>${data.consultants.length}</b>` : ""}</a>'''

J2_OLD = '\t\t$bar.find(".duty-proj-cons").on("click", () => {'
J2_NEW = '''\t\t$bar.find(".duty-proj-staffb").on("click", () => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.projects.project_staff_options",
\t\t\t\targs: { project: this.current_project },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst R = r.message || {};
\t\t\t\t\tconst rows = R.options || [];
\t\t\t\t\tconst d = new frappe.ui.Dialog({
\t\t\t\t\t\ttitle: __("Project team"),
\t\t\t\t\t\tprimary_action_label: R.can_edit ? __("Save team") : __("Close"),
\t\t\t\t\t\tprimary_action: () => {
\t\t\t\t\t\t\tif (!R.can_edit) return d.hide();
\t\t\t\t\t\t\tconst users = $(d.body).find("input.duty-tm:checked").map((_i, el) => $(el).val()).get();
\t\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\t\tmethod: "duty_board.projects.project_staff_set",
\t\t\t\t\t\t\t\targs: { project: this.current_project, users: JSON.stringify(users) },
\t\t\t\t\t\t\t\tcallback: () => {
\t\t\t\t\t\t\t\t\td.hide();
\t\t\t\t\t\t\t\t\tfrappe.show_alert({ message: __("Team saved."), indicator: "green" });
\t\t\t\t\t\t\t\t\tthis.load_kanban(this.current_project);
\t\t\t\t\t\t\t\t},
\t\t\t\t\t\t\t});
\t\t\t\t\t\t},
\t\t\t\t\t});
\t\t\t\t\t$(d.body).html(
\t\t\t\t\t\trows.map((u) => `<label class="duty-px-row"><input type="checkbox" class="duty-tm" value="${u.user}" ${u.member ? "checked" : ""} ${R.can_edit ? "" : "disabled"}><span class="duty-px-t">${frappe.utils.escape_html(u.full_name)}</span></label>`).join("")
\t\t\t\t\t\t|| `<div class="text-muted">${__("No staff in the rates roster yet — add them in Duty Settings.")}</div>`
\t\t\t\t\t);
\t\t\t\t\td.show();
\t\t\t\t},
\t\t\t});
\t\t});
\t\t$bar.find(".duty-proj-cons").on("click", () => {'''

J3_OLD = '\t\t\t.duty-proj-cons { font-size: var(--text-xs); font-weight: 700; color: #087A67; cursor: pointer; margin-right: 10px; }'
J3_NEW = '''\t\t\t.duty-proj-cons { font-size: var(--text-xs); font-weight: 700; color: #087A67; cursor: pointer; margin-right: 10px; }
\t\t\t.duty-proj-staffb { font-size: var(--text-xs); font-weight: 700; color: #0F5C55; cursor: pointer; margin-right: 10px; }'''

J4_OLD = '\t\t\tbody.duty-consultant .duty-proj-new, body.duty-consultant .duty-proj-cons,'
J4_NEW = '\t\t\tbody.duty-consultant .duty-proj-new, body.duty-consultant .duty-proj-cons, body.duty-consultant .duty-proj-staffb,'


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, PROJ, EARN):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def project_staff_set(" in files[PROJ]:
        print("Already applied. Nothing to do.")
        return
    if '"3.76.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.76.0.")

    checks = [
        (PROJ, A_OLD, "creator row", 1), (PROJ, B_OLD, "list filter", 1),
        (PROJ, C_OLD, "board guard", 1), (PROJ, D_OLD, "board payload", 1),
        (EARN, F_OLD, "phase projects", 1), (EARN, G_OLD, "phase split", 1),
        (JS, J1_OLD, "team button", 1), (JS, J2_OLD, "team handler", 1),
        (JS, J3_OLD, "css", 1), (JS, J4_OLD, "consultant hide", 1),
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

    sdir = os.path.join(root, SDIR)
    os.makedirs(sdir, exist_ok=True)
    with io.open(os.path.join(sdir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(sdir, "duty_project_staff.json"), "w", encoding="utf-8") as f:
        json.dump(STAFF_DT, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(sdir, "duty_project_staff.py"), "w", encoding="utf-8") as f:
        f.write("import frappe\nfrom frappe.model.document import Document\n\n\nclass DutyProjectStaff(Document):\n\tpass\n")
    print("  doctype: Duty Project Staff (child) created")

    with io.open(os.path.join(root, PDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "staff" for fl in dt["fields"]):
        dt["fields"].append({"fieldname": "staff", "fieldtype": "Table", "label": "Project Staff", "options": "Duty Project Staff"})
        if "field_order" in dt:
            dt["field_order"].append("staff")
        with io.open(os.path.join(root, PDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    print("  Duty Project +staff table")

    pj = files[PROJ]
    for o, n in [(A_OLD, A_NEW), (B_OLD, B_NEW), (C_OLD, C_NEW), (D_OLD, D_NEW)]:
        pj = pj.replace(o, n, 1)
    pj += E_APPEND
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: filter/guard/payload re-pointed, team endpoints added")

    e = files[EARN].replace(F_OLD, F_NEW, 1).replace(G_OLD, G_NEW, 1)
    with io.open(os.path.join(root, EARN), "w", encoding="utf-8") as f:
        f.write(e)
    print("  earnings.py: phase bonuses split over Duty Project Staff")

    js = files[JS]
    for o, n in [(J1_OLD, J1_NEW), (J2_OLD, J2_NEW), (J3_OLD, J3_NEW), (J4_OLD, J4_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: 👥 Team button + roster dialog")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.76.0"', '"3.77.0"'))
    print("wrote __init__.py -> 3.77.0")


if __name__ == "__main__":
    main()
