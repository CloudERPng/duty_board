#!/usr/bin/env python3
"""Duty Board v3.61.0b — projects scope by ROOM (the behavioural cutover).

The schema half (v3.61.0a) added Duty Project.room and backfilled it.
This flips the queries to honour it: a room now shows only the projects
whose room is it. VISIBLE CONSEQUENCE — a customer's second room shows
NO projects until one is assigned to it (Audacious: whichever room the
backfill did not pick is now empty until you move a project over).

Changes:
1. _project_names(room): filter Duty Project by room.name (was customer).
   All four call sites already have `room` in scope — they passed
   room.customer; now they pass room.
2. _work_rows: the project pluck filters by room.name too, so blended
   tasks come only from this room's projects.
3. client_projects: lists this room's active projects (+ General).
4. _ensure_project: the auto catch-all is stamped with room, so each
   room gets its OWN "{unit} — Requests" bucket rather than sharing the
   customer's.
5. room_set_project -> assign_project_to_room: assigning a project here
   MOVES it (a project belongs to exactly one room), and the scope
   dialog field explains that.

JS + client_room only. No migrate (schema already there).
bench build --app duty_board && bench restart, clear-website-cache.
Anchored, idempotent. Requires v3.61.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. _project_names takes room, filters by room --------------------------
PN_OLD = '''def _project_names(customer):
\t"""name -> display label for a customer's active projects. The room's
\tauto-created catch-all ("{cust} — Requests") shows as "General Requests"."""
\tout = {}
\tfor p in frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"customer": customer, "status": "Active"},
\t\tfields=["name", "project_name"],
\t):'''
PN_NEW = '''def _project_names(room):
\t"""name -> display label for THIS ROOM's active projects. The room's
\tauto-created catch-all ("… — Requests") shows as "General Requests"."""
\tout = {}
\tfor p in frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"room": room.name, "status": "Active"},
\t\tfields=["name", "project_name"],
\t):'''

# the four callers: room.customer -> room
CALL1_OLD = '\t\tpnames = _project_names(room.customer)\n\t\tfor t in frappe.get_all('
CALL1_NEW = '\t\tpnames = _project_names(room)\n\t\tfor t in frappe.get_all('
CALL2_OLD = '\t_shpn = _project_names(room.customer)'
CALL2_NEW = '\t_shpn = _project_names(room)'
CALL3_OLD = '\tpnames = _project_names(room.customer)\n\tfor r in rows:\n\t\tr.project_name = pnames.get(r.project)'
CALL3_NEW = '\tpnames = _project_names(room)\n\tfor r in rows:\n\t\tr.project_name = pnames.get(r.project)'
CALL4_OLD = '\t_crpn = _project_names(room.customer)'
CALL4_NEW = '\t_crpn = _project_names(room)'

# --- 2. _work_rows project pluck by room ------------------------------------
WR_OLD = '''\tprojs = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"customer": room.customer, "status": "Active"},
\t\tpluck="name",
\t)'''
WR_NEW = '''\tprojs = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"room": room.name, "status": "Active"},
\t\tpluck="name",
\t)'''

# --- 3. client_projects by room ---------------------------------------------
CP_OLD = '''\troom = _client_room()
\tprojs = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"customer": room.customer, "status": "Active"},
\t\tfields=["name", "project_name"],
\t\torder_by="creation asc",
\t)'''
CP_NEW = '''\troom = _client_room()
\tprojs = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"room": room.name, "status": "Active"},
\t\tfields=["name", "project_name"],
\t\torder_by="creation asc",
\t)'''

# --- 4. _ensure_project stamps room -----------------------------------------
EP_OLD = '''\tcustomer_name = room.customer
\tproj = frappe.get_doc(
\t\t{
\t\t\t"doctype": "Duty Project",
\t\t\t"project_name": f"{customer_name} — Requests",
\t\t\t"customer": customer_name,
\t\t\t"status": "Active",
\t\t}
\t).insert(ignore_permissions=True)'''
EP_NEW = '''\tcustomer_name = room.customer
\t# Each room gets its own catch-all so requests from one room don't land
\t# in another's bucket. Label by unit when present to keep them distinct.
\tlabel_unit = (room.get("unit") or "General")
\tproj = frappe.get_doc(
\t\t{
\t\t\t"doctype": "Duty Project",
\t\t\t"project_name": f"{customer_name} · {label_unit} — Requests",
\t\t\t"customer": customer_name,
\t\t\t"room": room.name,
\t\t\t"status": "Active",
\t\t}
\t).insert(ignore_permissions=True)'''

# --- 5. room_set_project -> exclusive assignment (moves the project) --------
RSP_OLD = '''def room_set_project(name, project=None):
\t"""Link a room to an existing Duty Project (or clear the link). The lazy
\t'{Customer} — Requests' auto-project remains the default path; this is
\tfor pointing a room at a real implementation project."""
\t_staff_only()
\tif project and not frappe.db.exists("Duty Project", project):
\t\tfrappe.throw(_("Unknown project."))
\tfrappe.db.set_value("Client Room", name, "project", project or None, update_modified=False)
\tfrappe.db.commit()
\treturn get_room(name)'''
RSP_NEW = '''def room_set_project(name, project=None):
\t"""Set the room's DEFAULT board project (where new client requests land).
\tKept for back-compat with the scope dialog's single default field."""
\t_staff_only()
\tif project and not frappe.db.exists("Duty Project", project):
\t\tfrappe.throw(_("Unknown project."))
\tfrappe.db.set_value("Client Room", name, "project", project or None, update_modified=False)
\tfrappe.db.commit()
\treturn get_room(name)


@frappe.whitelist()
def room_projects(name):
\t"""For the scope dialog: this customer's active projects, each flagged
\twith whether it currently belongs to THIS room."""
\t_staff_only()
\troom = frappe.get_doc("Client Room", name)
\tout = []
\tfor p in frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"customer": room.customer, "status": "Active"},
\t\tfields=["name", "project_name", "room"],
\t\torder_by="creation asc",
\t):
\t\tout.append({
\t\t\t"name": p.name,
\t\t\t"label": p.project_name or p.name,
\t\t\t"mine": 1 if p.room == name else 0,
\t\t\t"other_room": p.room if (p.room and p.room != name) else None,
\t\t})
\treturn out


@frappe.whitelist()
def room_assign_projects(name, project_names):
\t"""Assign a set of projects to THIS room. Because a project belongs to
\texactly one room, assigning here MOVES it off whatever room it was on.
\tProjects of this customer not in the set, currently on this room, are
\tleft where they are only if still ticked — unticking moves nothing (a
\tproject must live somewhere); to move a project elsewhere, assign it
\tthere. Here we only ADD/!MOVE the ticked ones onto this room."""
\t_staff_only()
\troom = frappe.get_doc("Client Room", name)
\timport json as _json

\ttry:
\t\twanted = _json.loads(project_names) if isinstance(project_names, str) else (project_names or [])
\texcept Exception:
\t\twanted = []
\tfor pn in wanted:
\t\tif not frappe.db.exists("Duty Project", pn):
\t\t\tcontinue
\t\tpc = frappe.db.get_value("Duty Project", pn, "customer")
\t\tif pc != room.customer:
\t\t\tcontinue  # never move a project across customers
\t\tfrappe.db.set_value("Duty Project", pn, "room", name, update_modified=False)
\tfrappe.db.commit()
\treturn get_room(name)'''

# --- JS: scope dialog uses a project multi-select ---------------------------
JS_OLD = '''\t\t\tfrappe.call({ method: "frappe.client.get_value", args: { doctype: "Client Room", filters: { name: x.name }, fieldname: ["scope_note", "support_plan", "project", "is_financial_room"] }, callback: (rv) => {
\t\t\t\tconst cur = rv.message || {};
\t\t\t\tfrappe.prompt(
\t\t\t\t\t[
\t\t\t\t\t\t{ fieldname: "support_plan", fieldtype: "Data", label: __("Support plan (shown to client, e.g. 'Unlimited support · changes quoted via CR')"), default: cur.support_plan || "" },
\t\t\t\t\t\t{ fieldname: "scope_note", fieldtype: "Small Text", label: __("Contract scope — supported modules & boundaries"), default: cur.scope_note || "" },
\t\t\t\t\t\t{ fieldname: "project", fieldtype: "Link", options: "Duty Project", label: __("Project board for this room (tasks, milestones, CR delivery)"), default: cur.project || "" },
\t\t\t\t\t\t{ fieldname: "is_financial_room", fieldtype: "Check", label: __("📊 Financial Room — statements, announcements & review actions for this customer live here (one per customer)"), default: cur.is_financial_room || 0 },
\t\t\t\t\t],
\t\t\t\t\t(v) => frappe.call({ method: "duty_board.commercial.set_room_scope", args: { name: x.name, scope_note: v.scope_note || "", support_plan: v.support_plan || "", is_financial_room: v.is_financial_room ? 1 : 0 }, callback: () =>
\t\t\t\t\t\tfrappe.call({ method: "duty_board.client_room.room_set_project", args: { name: x.name, project: v.project || null }, callback: () => frappe.show_alert({ message: __("⚖ Scope & project saved"), indicator: "green" }) })
\t\t\t\t\t}),
\t\t\t\t\t__("Room scope"), __("Save")
\t\t\t\t);
\t\t\t}});'''
JS_NEW = '''\t\t\tfrappe.call({ method: "duty_board.client_room.room_projects", args: { name: x.name }, callback: (pr) => {
\t\t\t  const projs = pr.message || [];
\t\t\t  frappe.call({ method: "frappe.client.get_value", args: { doctype: "Client Room", filters: { name: x.name }, fieldname: ["scope_note", "support_plan", "project", "is_financial_room"] }, callback: (rv) => {
\t\t\t\tconst cur = rv.message || {};
\t\t\t\tconst d = new frappe.ui.Dialog({
\t\t\t\t\ttitle: __("Room scope"),
\t\t\t\t\tfields: [
\t\t\t\t\t\t{ fieldname: "support_plan", fieldtype: "Data", label: __("Support plan (shown to client, e.g. 'Unlimited support · changes quoted via CR')"), default: cur.support_plan || "" },
\t\t\t\t\t\t{ fieldname: "scope_note", fieldtype: "Small Text", label: __("Contract scope — supported modules & boundaries"), default: cur.scope_note || "" },
\t\t\t\t\t\t{ fieldname: "projects_html", fieldtype: "HTML", label: __("Projects in this room") },
\t\t\t\t\t\t{ fieldname: "is_financial_room", fieldtype: "Check", label: __("📊 Financial Room — statements, announcements & review actions for this customer live here (one per customer)"), default: cur.is_financial_room || 0 },
\t\t\t\t\t],
\t\t\t\t\tprimary_action_label: __("Save"),
\t\t\t\t\tprimary_action: (v) => {
\t\t\t\t\t\tconst picked = [];
\t\t\t\t\t\td.$wrapper.find(".duty-projpick:checked").each((i, el) => picked.push($(el).val()));
\t\t\t\t\t\tfrappe.call({ method: "duty_board.commercial.set_room_scope", args: { name: x.name, scope_note: v.scope_note || "", support_plan: v.support_plan || "", is_financial_room: v.is_financial_room ? 1 : 0 } });
\t\t\t\t\t\tfrappe.call({ method: "duty_board.client_room.room_assign_projects", args: { name: x.name, project_names: JSON.stringify(picked) }, callback: () => { d.hide(); frappe.show_alert({ message: __("⚖ Scope & projects saved"), indicator: "green" }); this.render_client_room(x); } });
\t\t\t\t\t},
\t\t\t\t});
\t\t\t\tconst rows = projs.map((p) => `<label style="display:flex;gap:8px;align-items:center;padding:5px 0"><input type="checkbox" class="duty-projpick" value="${frappe.utils.escape_html(p.name)}" ${p.mine ? "checked" : ""}> <span>${frappe.utils.escape_html(p.label)}${p.other_room ? ` <span style="color:#B45309;font-size:11px">(currently in another room — ticking moves it here)</span>` : ""}</span></label>`).join("");
\t\t\t\td.fields_dict.projects_html.$wrapper.html(`<div style="border:1px solid #e6e6e6;border-radius:8px;padding:8px 12px">${rows || `<span class="text-muted">${__("No projects for this customer yet.")}</span>`}<div class="text-muted" style="font-size:11px;margin-top:6px">${__("A project belongs to exactly one room. Ticking it here moves it here.")}</div></div>`);
\t\t\t\td.show();
\t\t\t  }});
\t\t\t}});'''

CR_EDITS = [
    ("_project_names by room", PN_OLD, PN_NEW),
    ("caller: _work_rows tasks", CALL1_OLD, CALL1_NEW),
    ("caller: shelf", CALL2_OLD, CALL2_NEW),
    ("caller: milestones", CALL3_OLD, CALL3_NEW),
    ("caller: chreqs", CALL4_OLD, CALL4_NEW),
    ("_work_rows pluck by room", WR_OLD, WR_NEW),
    ("client_projects by room", CP_OLD, CP_NEW),
    ("_ensure_project stamps room", EP_OLD, EP_NEW),
    ("room_set_project + assign endpoints", RSP_OLD, RSP_NEW),
]
JS_EDITS = [("scope dialog: project multi-select", JS_OLD, JS_NEW)]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def room_assign_projects(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.61.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.61.0.")

    problems = []
    for label, old, _n in CR_EDITS:
        if files[CR].count(old) != 1:
            problems.append(f"  [{files[CR].count(old)}] CR: {label}")
    for label, old, _n in JS_EDITS:
        if files[JS].count(old) != 1:
            problems.append(f"  [{files[JS].count(old)}] JS: {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(CR_EDITS)+len(JS_EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = dict(files)
    for label, old, new in CR_EDITS:
        out[CR] = out[CR].replace(old, new, 1)
    for label, old, new in JS_EDITS:
        out[JS] = out[JS].replace(old, new, 1)
    out[INIT] = out[INIT].replace('"3.61.0"', '"3.61.1"')

    for p in (CR, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(out[p])
        print(f"  wrote {p}")
    print("wrote __init__.py -> 3.61.1")


if __name__ == "__main__":
    main()
