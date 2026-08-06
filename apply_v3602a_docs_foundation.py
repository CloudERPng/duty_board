#!/usr/bin/env python3
"""Duty Board v3.60.2a — project-scoped documents: the foundation.

Backend groundwork for the client project selector. Independently safe:
new field, new endpoint, a backfill that preserves the status quo, and a
dead-code removal. Nothing client-visible changes until the selector
(v3.60.2b) ships on top.

1. DEDUP: remove the duplicate _project_names left by v3.60.0 (my
   _work_rows anchor matched a call-site before the definition, so the
   helper was prepended twice — byte-identical dead twin).
2. SHELF GETS A PROJECT: Client Shelf Doc gains a project link; a patch
   backfills every existing doc to its room's catch-all project so
   nothing vanishes when the selector filters by project.
3. _shelf_rows carries project + project_name; shelf_add accepts a
   project arg (defaults to the room catch-all, "General/Relationship"
   allowed).
4. client_projects(): lists the customer's active projects for the
   selector, with a stable "General" entry for the catch-all/relationship
   bucket.

Deploy: bench migrate && bench build --app duty_board && bench restart
  (migrate creates the column AND runs the backfill patch.)

Anchored, all-or-nothing, idempotent. Requires v3.60.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
SHELFDT = "duty_board/duty_board/doctype/client_shelf_doc/client_shelf_doc.json"
PATCHES = "duty_board/patches.txt"
CHECK_ONLY = "--check" in sys.argv

# --- 1. dedup _project_names (remove the FIRST of two identical defs) --------
DUP_BLOCK = '''def _project_names(customer):
\t"""name -> display label for a customer's active projects. The room's
\tauto-created catch-all ("{cust} — Requests") shows as "General Requests"."""
\tout = {}
\tfor p in frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"customer": customer, "status": "Active"},
\t\tfields=["name", "project_name"],
\t):
\t\tlabel = p.project_name or p.name
\t\tif label.endswith("— Requests") or label.endswith("- Requests"):
\t\t\tlabel = "General Requests"
\t\tout[p.name] = label
\treturn out


'''

# --- 2. _shelf_rows carries project -----------------------------------------
SHELF_OLD = '''\trows = frappe.get_all(
\t\t"Client Shelf Doc",
\t\tfilters={"room": room.name, "active": 1},
\t\tfields=["name", "title", "category", "file_name", "creation", "owner"],
\t\torder_by="creation desc",
\t\tlimit=200,
\t)
\tfor r in rows:
\t\tr.creation = str(r.creation)[:10]'''
SHELF_NEW = '''\trows = frappe.get_all(
\t\t"Client Shelf Doc",
\t\tfilters={"room": room.name, "active": 1},
\t\tfields=["name", "title", "category", "file_name", "creation", "owner", "project"],
\t\torder_by="creation desc",
\t\tlimit=200,
\t)
\t_shpn = _project_names(room.customer)
\tfor r in rows:
\t\tr.creation = str(r.creation)[:10]
\t\tr.project_name = _shpn.get(r.project) if r.project else None'''

# --- 3. shelf_add accepts project -------------------------------------------
ADD_OLD = '''def shelf_add(name, title, attachment_url, attachment_name=None, category=None):'''
ADD_NEW = '''def shelf_add(name, title, attachment_url, attachment_name=None, category=None, project=None):'''

ADD_DOC_OLD = '''\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Client Shelf Doc",
\t\t\t"room": room.name,
\t\t\t"title": title[:140],
\t\t\t"category": (category or "").strip()[:60] or None,
\t\t\t"file_url": attachment_url,
\t\t\t"file_name": attachment_name or owned,
\t\t\t"active": 1,
\t\t}
\t).insert(ignore_permissions=True)'''
ADD_DOC_NEW = '''\t# "__general__" (or blank) files the doc under the room catch-all project —
\t# the relationship bucket for contracts, SLAs and the like.
\tproj = None if (not project or project == "__general__") else _validate_milestone_project(room.name, project)
\tif not proj:
\t\tproj = _ensure_project(room)
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Client Shelf Doc",
\t\t\t"room": room.name,
\t\t\t"title": title[:140],
\t\t\t"category": (category or "").strip()[:60] or None,
\t\t\t"file_url": attachment_url,
\t\t\t"file_name": attachment_name or owned,
\t\t\t"active": 1,
\t\t\t"project": proj,
\t\t}
\t).insert(ignore_permissions=True)'''

# --- 4. client_projects endpoint, added after client_get_documents ----------
EP_OLD = '''def client_get_documents():
\troom = _client_room()
\tstm = _statement_rows(room)
\treturn {"docs": _shelf_rows(room), "statements": stm, "year_strip": _statement_year_strip(stm)}'''
EP_NEW = '''def client_get_documents():
\troom = _client_room()
\tstm = _statement_rows(room)
\treturn {"docs": _shelf_rows(room), "statements": stm, "year_strip": _statement_year_strip(stm)}


@frappe.whitelist()
def client_projects():
\t"""Active projects for the client's customer, for the portal selector.
\tThe room catch-all is presented once as "General"; a stable id lets the
\tselector scope tasks/phases/CRs/docs to the relationship bucket."""
\troom = _client_room()
\tprojs = frappe.get_all(
\t\t"Duty Project",
\t\tfilters={"customer": room.customer, "status": "Active"},
\t\tfields=["name", "project_name"],
\t\torder_by="creation asc",
\t)
\tcatchall = None
\tout = []
\tfor p in projs:
\t\tlabel = p.project_name or p.name
\t\tif label.endswith("— Requests") or label.endswith("- Requests"):
\t\t\tcatchall = p.name
\t\t\tcontinue
\t\tout.append({"id": p.name, "label": label})
\t# General always last, always present so relationship docs have a home.
\tout.append({"id": catchall or "__general__", "label": "General"})
\treturn out'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_projects():" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.60.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.60.1.")

    # anchor checks
    problems = []
    if files[CR].count(DUP_BLOCK) != 2:
        problems.append(f"  _project_names dedup: expected 2 copies, found {files[CR].count(DUP_BLOCK)}")
    for label, s, n in [
        ("_shelf_rows +project", SHELF_OLD, 1),
        ("shelf_add sig", ADD_OLD, 1),
        ("shelf_add doc", ADD_DOC_OLD, 1),
        ("client_get_documents", EP_OLD, 1),
    ]:
        if files[CR].count(s) != n:
            problems.append(f"  [{files[CR].count(s)}] {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched (dedup=2, others=1).")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # shelf doctype: +project
    dtp = os.path.join(root, SHELFDT)
    with io.open(dtp, encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "project" for fl in dt["fields"]):
        dt["fields"].append({
            "fieldname": "project", "fieldtype": "Link", "label": "Project",
            "options": "Duty Project",
        })
        if "field_order" in dt:
            dt["field_order"].append("project")
        with io.open(dtp, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
        print("  doctype: Client Shelf Doc +project")

    cr = files[CR]
    # dedup: remove the FIRST identical block only
    cr = cr.replace(DUP_BLOCK, "", 1)
    cr = cr.replace(SHELF_OLD, SHELF_NEW, 1)
    cr = cr.replace(ADD_OLD, ADD_NEW, 1)
    cr = cr.replace(ADD_DOC_OLD, ADD_DOC_NEW, 1)
    cr = cr.replace(EP_OLD, EP_NEW, 1)
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(cr)
    print("  client_room.py: dedup + shelf project + client_projects")

    # register backfill patch
    pt_path = os.path.join(root, PATCHES)
    with io.open(pt_path, encoding="utf-8") as f:
        pt = f.read()
    line = "duty_board.patches.backfill_shelf_project"
    if line not in pt:
        pt = (pt.rstrip() + "\n" + line + "\n") if pt.strip() else (line + "\n")
        with io.open(pt_path, "w", encoding="utf-8") as f:
            f.write(pt)
        print("  patches.txt: backfill registered")

    init = files[INIT].replace('"3.60.1"', '"3.60.2"')
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init)
    print("wrote __init__.py -> 3.60.2")


if __name__ == "__main__":
    main()
