#!/usr/bin/env python3
"""Duty Board v3.60.0 — a customer can run several projects in one room.

The data model already blends every Active project of a customer into
one room (see _work_rows). What was missing was the presentation for
more than one. Three phases, one build:

PHASE 1 — LEGIBILITY. _work_rows and _milestone_rows now carry
project + project_name. The client portal task table and phase view,
and the staff room task column, show a project chip per row; when a
customer has >1 active project a filter bar appears (All · each project
· General). Single-project customers see no chips and no bar — the
multi-case unfolds only when it exists.

PHASE 2 — PER-PROJECT PHASE STRIPS. The client "You are here" strip
was one interleaved progression across all projects (milestones carry
project, so two journeys merged into a false line). It now renders one
compact strip per active project, each with its own progress and next
action.

PHASE 3 — CRs LEARN THEIR PROJECT. Duty Change Request gains an
optional project link. chreq_add / chreq_update accept it; the client
CR list labels each with its project when the customer has >1.

Chat stays one unlabelled stream — that is the value of same-room; the
structure lives in the work, not the talk. `unit` is untouched — it is
the org axis (Finance vs General), a different dimension from projects.

Deploy: bench migrate && bench build --app duty_board && bench restart
Anchored, all-or-nothing, idempotent. Requires v3.59.7.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CRDT = "duty_board/duty_board/doctype/duty_change_request/duty_change_request.json"
CHECK_ONLY = "--check" in sys.argv

# =========================================================================
# client_room.py
# =========================================================================

# --- 1. project name map helper, before _work_rows -------------------------
CR1_OLD = 'def _work_rows(room):'
CR1_NEW = '''def _project_names(customer):
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


def _work_rows(room):'''

# --- 2. _work_rows: task rows carry project ---------------------------------
CR2_OLD = '''\t\tfor t in frappe.get_all(
\t\t\t"Duty Project Task",
\t\t\tfilters={"project": ["in", projs], "client_visible": 1},
\t\t\tfields=["name", "title", "column", "assignee", "client_requested", "modified", "creation"],
\t\t):'''
CR2_NEW = '''\t\tpnames = _project_names(room.customer)
\t\tfor t in frappe.get_all(
\t\t\t"Duty Project Task",
\t\t\tfilters={"project": ["in", projs], "client_visible": 1},
\t\t\tfields=["name", "title", "column", "assignee", "client_requested", "modified", "creation", "project"],
\t\t):'''

CR3_OLD = '''\t\t\t\t\t"reported": str(t.creation)[:16],
\t\t\t\t\t"modified": t.modified,
\t\t\t\t}
\t\t\t)'''
CR3_NEW = '''\t\t\t\t\t"reported": str(t.creation)[:16],
\t\t\t\t\t"modified": t.modified,
\t\t\t\t\t"project": t.project,
\t\t\t\t\t"project_name": pnames.get(t.project),
\t\t\t\t}
\t\t\t)'''

# issue rows (the other branch of _work_rows) get null project so the
# client filter treats them as "General".
CR4_OLD = '''\t\t\t\t"stars": cint(i.client_stars) or 0,
\t\t\t\t"modified": i.modified,
\t\t\t}
\t\t)'''
CR4_NEW = '''\t\t\t\t"stars": cint(i.client_stars) or 0,
\t\t\t\t"modified": i.modified,
\t\t\t\t"project": None,
\t\t\t\t"project_name": None,
\t\t\t}
\t\t)'''

# --- 3. _visible_tasks + _work rows pass project through --------------------
CR5_OLD = '''\t\t\t"confirmed": o.get("confirmed"),
\t\t\t"stars": o.get("stars"),
\t\t}
\t\tfor o in _work_rows(room)'''
CR5_NEW = '''\t\t\t"confirmed": o.get("confirmed"),
\t\t\t"stars": o.get("stars"),
\t\t\t"project": o.get("project"),
\t\t\t"project_name": o.get("project_name"),
\t\t}
\t\tfor o in _work_rows(room)'''

# strip modified but keep project — the del loop must not drop it (it only
# deletes "modified", so project already survives; no edit needed there).

# --- 4. _milestone_rows: carry project_name --------------------------------
CR6_OLD = '''\t\tr.cards_total = len(tasks)
\t\tr.cards_done = sum(1 for t in tasks if t.column == "Completed")
\t\tr.awaiting = sum(1 for t in tasks if cint(t.awaiting_client) and t.column != "Completed")
\treturn rows'''
CR6_NEW = '''\t\tr.cards_total = len(tasks)
\t\tr.cards_done = sum(1 for t in tasks if t.column == "Completed")
\t\tr.awaiting = sum(1 for t in tasks if cint(t.awaiting_client) and t.column != "Completed")
\tpnames = _project_names(room.customer)
\tfor r in rows:
\t\tr.project_name = pnames.get(r.project)
\treturn rows'''

# --- 5. _chreq_rows: carry project + project_name --------------------------
CR7_OLD = '''\t\t\t"source_type", "source_message", "source_issue",
\t\t\t"released", "pricing_status", "estimate_hours", "invoice_status",
\t\t],
\t\torder_by="creation desc",
\t)'''
CR7_NEW = '''\t\t\t"source_type", "source_message", "source_issue",
\t\t\t"released", "pricing_status", "estimate_hours", "invoice_status", "project",
\t\t],
\t\torder_by="creation desc",
\t)
\t_crpn = _project_names(room.customer)'''

CR8_OLD = '''\t\tr.cost_fmt = _chreq_fmt(r.cost_impact)
\t\tr.approved_fmt = _chreq_fmt(r.approved_amount)'''
CR8_NEW = '''\t\tr.cost_fmt = _chreq_fmt(r.cost_impact)
\t\tr.approved_fmt = _chreq_fmt(r.approved_amount)
\t\tr.project_name = _crpn.get(r.project)'''

# --- 6. chreq_add accepts project ------------------------------------------
CR9_OLD = '''def chreq_add(name, title, original_request=None):
\t_staff_only()
\troom = frappe.get_doc("Client Room", name)
\ttitle = (title or "").strip()
\tif not title:
\t\tfrappe.throw(_("Give the change request a title."))
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Duty Change Request",
\t\t\t"room": room.name,
\t\t\t"title": title[:140],
\t\t\t"status": "Draft",
\t\t\t"original_request": (original_request or "").strip() or None,
\t\t\t"source_type": "Manual",
\t\t}
\t).insert(ignore_permissions=True)'''
CR9_NEW = '''def chreq_add(name, title, original_request=None, project=None):
\t_staff_only()
\troom = frappe.get_doc("Client Room", name)
\ttitle = (title or "").strip()
\tif not title:
\t\tfrappe.throw(_("Give the change request a title."))
\tfrappe.get_doc(
\t\t{
\t\t\t"doctype": "Duty Change Request",
\t\t\t"room": room.name,
\t\t\t"title": title[:140],
\t\t\t"status": "Draft",
\t\t\t"original_request": (original_request or "").strip() or None,
\t\t\t"source_type": "Manual",
\t\t\t"project": _validate_milestone_project(room.name, project or None),
\t\t}
\t).insert(ignore_permissions=True)'''

# --- 7. chreq_update accepts project ---------------------------------------
CR10_OLD = '''\t\t\t"quotation": quotation or None,
\t\t},
\t\tupdate_modified=False,
\t)
\tfrappe.db.commit()
\treturn get_room(doc.room)'''
CR10_NEW = '''\t\t\t"quotation": quotation or None,
\t\t\t"project": _validate_milestone_project(doc.room, project or None),
\t\t},
\t\tupdate_modified=False,
\t)
\tfrappe.db.commit()
\treturn get_room(doc.room)'''


def patch_chreq_update_sig(src):
    """chreq_update's signature varies; add project= before its body opens."""
    i = src.find("def chreq_update(")
    if i < 0:
        return src, False
    # find the closing paren of the signature
    depth = 0
    j = i + len("def chreq_update")
    while j < len(src):
        if src[j] == "(":
            depth += 1
        elif src[j] == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    sig = src[i:j]
    if "project=" in sig:
        return src, True
    body = sig.rstrip()
    # signature may end "...quotation=None,\n" — strip a trailing comma/space
    # so we don't produce ",, project=None".
    body = body.rstrip()
    if body.endswith(","):
        body = body[:-1].rstrip()
    new_sig = body + ", project=None"
    return src[:i] + new_sig + src[j:], True


# =========================================================================
# duty_board.js — staff room task column chips + filter
# =========================================================================

# The staff task list is rendered from d.tasks (=_staff_tasks=_work_rows).
# Find the staff renderer's row template.
JS1_OLD = '\t\t\t.duty-ch-munit { background: var(--bg-light-gray, #eef2f1); color: #0f766e; border: 1px solid #d5e5e2; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 16px; white-space: nowrap; }'
JS1_NEW = JS1_OLD + '''
\t\t\t.duty-projchip { display: inline-block; background: #EEF4F3; color: #0F5C55; border: 1px solid #D2E4E0; border-radius: 7px; padding: 0 6px; font-size: 10px; font-weight: 700; margin-left: 6px; vertical-align: middle; }
\t\t\t.duty-projbar { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 8px; }
\t\t\t.duty-projbar a { font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 8px; border: 1px solid var(--border-color, #e0e0e0); color: var(--text-muted, #666); cursor: pointer; text-decoration: none; }
\t\t\t.duty-projbar a.on { background: #0F5C55; border-color: #0F5C55; color: #fff; }'''

# staff task row: project chip after the title (only when the row has one)
JS2_OLD = '\t\t\t\t\t\t<span class="duty-crt-title">${t.kind === "issue" ? "⚠ " : "📁 "}${t.client_requested ? "🙋 " : ""}${frappe.utils.escape_html(t.title)}</span>'
JS2_NEW = '\t\t\t\t\t\t<span class="duty-crt-title">${t.kind === "issue" ? "⚠ " : "📁 "}${t.client_requested ? "🙋 " : ""}${frappe.utils.escape_html(t.title)}${t.project_name && this._cr_multiproj ? `<span class="duty-projchip">${frappe.utils.escape_html(t.project_name)}</span>` : ""}</span>'

# staff task list: a filter bar above the rows when >1 project is present
JS3_OLD = '''\t\t\t<div class="duty-cr-tasks">
\t\t\t\t${(x.tasks || [])
\t\t\t\t\t.filter((t) => !this._cr_tfilter || t.status === this._cr_tfilter)'''
JS3_NEW = '''\t\t\t<div class="duty-cr-tasks">
\t\t\t\t${(() => {
\t\t\t\t\tconst names = [...new Set((x.tasks || []).map((t) => t.project_name).filter(Boolean))];
\t\t\t\t\tthis._cr_multiproj = names.length > 1;
\t\t\t\t\tif (!this._cr_multiproj) return "";
\t\t\t\t\tconst pf = this._cr_pfilter || "";
\t\t\t\t\treturn `<div class="duty-projbar"><a data-pf="" class="${!pf ? "on" : ""}">${__("All")}</a>${names
\t\t\t\t\t\t.map((n) => `<a data-pf="${frappe.utils.escape_html(n)}" class="${pf === n ? "on" : ""}">${frappe.utils.escape_html(n)}</a>`)
\t\t\t\t\t\t.join("")}<a data-pf="__none__" class="${pf === "__none__" ? "on" : ""}">${__("General")}</a></div>`;
\t\t\t\t})()}
\t\t\t\t${(x.tasks || [])
\t\t\t\t\t.filter((t) => !this._cr_pfilter || (this._cr_pfilter === "__none__" ? !t.project_name : t.project_name === this._cr_pfilter))
\t\t\t\t\t.filter((t) => !this._cr_tfilter || t.status === this._cr_tfilter)'''

# staff filter bar: click handler, bound alongside the status-filter binding
JS4_OLD = '''\t\t$room.find(".duty-cr-task").on("click", (e) => {
\t\t\tconst $t = $(e.currentTarget);
\t\t\tif ($t.data("kind") === "issue") {'''
JS4_NEW = '''\t\t$room.find(".duty-projbar a").on("click", (e) => {
\t\t\tthis._cr_pfilter = $(e.currentTarget).attr("data-pf") || "";
\t\t\tthis.render_client_room(x);
\t\t});
\t\t$room.find(".duty-cr-task").on("click", (e) => {
\t\t\tconst $t = $(e.currentTarget);
\t\t\tif ($t.data("kind") === "issue") {'''

EDITS_CR = [
    ("_project_names helper", CR1_OLD, CR1_NEW),
    ("_project_names helper", CR1_OLD, CR1_NEW),
    ("_work_rows: task fields +project", CR2_OLD, CR2_NEW),
    ("_work_rows: task row +project", CR3_OLD, CR3_NEW),
    ("_work_rows: issue row +project null", CR4_OLD, CR4_NEW),
    ("_visible_tasks: pass project", CR5_OLD, CR5_NEW),
    ("_milestone_rows: +project_name", CR6_OLD, CR6_NEW),
    ("_chreq_rows: fields +project", CR7_OLD, CR7_NEW),
    ("_chreq_rows: +project_name", CR8_OLD, CR8_NEW),
    ("chreq_add: +project arg", CR9_OLD, CR9_NEW),
    ("chreq_update: +project write", CR10_OLD, CR10_NEW),
]
EDITS_JS = [
    ("styles: project chip + filter bar", JS1_OLD, JS1_NEW),
    ("staff task row: project chip", JS2_OLD, JS2_NEW),
    ("staff task list: filter bar", JS3_OLD, JS3_NEW),
    ("staff filter bar: click binding", JS4_OLD, JS4_NEW),
]

# =========================================================================
# www/portal.html — client task chip + per-project phase strips
# =========================================================================

# Client task table: project chip in the title cell (only when >1 project).
PT1_OLD = '<td class="tt-title">${x.seen ? "<span class=\'dotc\' style=\'background:#087A67\'></span> " : ""}${esc(x.title)}</td>'
PT1_NEW = '<td class="tt-title">${x.seen ? "<span class=\'dotc\' style=\'background:#087A67\'></span> " : ""}${esc(x.title)}${x.project_name && window._multiproj ? `<span class="pchip">${esc(x.project_name)}</span>` : ""}</td>'

# Compute _multiproj once, where the task rows are prepared.
PT2_OLD = '\tconst rows = (d.tasks || []).filter((x) => !filt || x.status === filt);'
PT2_NEW = '''\twindow._multiproj = [...new Set((d.tasks || []).map((x) => x.project_name).filter(Boolean))].length > 1;
\tconst rows = (d.tasks || []).filter((x) => !filt || x.status === filt);'''

# Per-project phase strip: renderMilestones groups by project when >1.
# The phase strip (#msstep) is the interleaved offender; we wrap its build
# in a per-project loop. Anchor on the exact strip-builder opening.
PT3_OLD = '''\tif (rows.length) {
\t\twrap.style.display = "block";
\t\tconst cur = rows.findIndex((m) => m.status !== "Approved");
\t\twrap.innerHTML = `<div id="msstep">${rows.map((m, i) => {'''
PT3_NEW = '''\tconst _projs = [...new Set(rows.map((m) => m.project_name).filter(Boolean))];
\tif (rows.length && _projs.length > 1) {
\t\t// Multiple projects: one phase strip per project, stacked.
\t\twrap.style.display = "block";
\t\twrap.innerHTML = _projs.map((pn) => {
\t\t\tconst pr = rows.filter((m) => m.project_name === pn);
\t\t\tconst pdone = pr.filter((m) => m.status === "Approved").length;
\t\t\tconst pcur = pr.findIndex((m) => m.status !== "Approved");
\t\t\treturn `<div class="pjstrip"><div class="pjstriphd">${esc(pn)}</div><div class="msstep">${pr.map((m, i) => {
\t\t\t\tconst st = m.status === "Approved" ? "d" : i === pcur ? "a" : "u";
\t\t\t\treturn `<div class="mss ${st}"><span class="mssd">${st === "d" ? "✓" : i + 1}</span><span class="mssl">${esc(m.title)}</span>${st === "a" ? `<span class="msshere">You are here${m.target_date ? ` · 🎯 ${esc(m.target_date)}` : ""}</span>` : ""}</div>`;
\t\t\t}).join('<span class="mssline"></span>')}</div><div class="pjbar"><i style="width:${Math.round((pdone / pr.length) * 100)}%"></i></div><div class="muted" style="font-size:12px">${pcur >= 0 ? `${esc(pr[pcur].title)} in progress · ${pdone} of ${pr.length} phases` : `All ${pr.length} phases signed off 🎉`}</div></div>`;
\t\t}).join("");
\t\tconst sumEl0 = document.getElementById("pjsum"); if (sumEl0) sumEl0.remove();
\t} else if (rows.length) {
\t\twrap.style.display = "block";
\t\tconst cur = rows.findIndex((m) => m.status !== "Approved");
\t\twrap.innerHTML = `<div id="msstep">${rows.map((m, i) => {'''

# portal CSS: reuse #msstep rules for the per-project .msstep class, add chip + strip
PT_CSS_OLD = '\t#msstep { display: flex; align-items: flex-start; overflow-x: auto; padding: 4px 0 10px; -webkit-overflow-scrolling: touch; }'
PT_CSS_NEW = '''\t#msstep, .msstep { display: flex; align-items: flex-start; overflow-x: auto; padding: 4px 0 10px; -webkit-overflow-scrolling: touch; }
\t.pchip { display: inline-block; background: #EEF4F3; color: #0F5C55; border: 1px solid #D2E4E0; border-radius: 7px; padding: 0 6px; font-size: 10px; font-weight: 700; margin-left: 7px; vertical-align: middle; }
\t.pjstrip { padding: 8px 0 4px; border-top: 1px solid #EEF2F0; }
\t.pjstrip:first-child { border-top: 0; }
\t.pjstriphd { font-size: 12px; font-weight: 800; color: #0F5C55; margin: 0 0 2px; }
\t.pjbar { height: 5px; background: #E7EDEA; border-radius: 99px; overflow: hidden; margin: 2px 0 4px; }
\t.pjbar i { display: block; height: 100%; background: #0E8A63; border-radius: 99px; }'''

EDITS_PORTAL = [
    ("portal: _multiproj flag", PT2_OLD, PT2_NEW),
    ("portal: task title project chip", PT1_OLD, PT1_NEW),
    ("portal: per-project phase strips", PT3_OLD, PT3_NEW),
    ("portal: chip + strip CSS", PT_CSS_OLD, PT_CSS_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL, JS):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "_project_names(customer)" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.7"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.7 — apply apply_v3597_team_mobile.py first.")

    problems = []
    for label, old, _n in EDITS_CR:
        if files[CR].count(old) != 1:
            problems.append(f"  [{files[CR].count(old)}] client_room.py: {label}")
    for label, old, _n in EDITS_JS:
        if files[JS].count(old) != 1:
            problems.append(f"  [{files[JS].count(old)}] duty_board.js: {label}")
    for label, old, _n in EDITS_PORTAL:
        if files[PORTAL].count(old) != 1:
            problems.append(f"  [{files[PORTAL].count(old)}] portal.html: {label}")
    if files[CR].count("def chreq_update(") != 1:
        problems.append("  chreq_update signature anchor")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS_CR)+len(EDITS_JS)+len(EDITS_PORTAL)+1} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # doctype: CR project link
    with io.open(os.path.join(root, CRDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "project" for fl in dt["fields"]):
        dt["fields"].append({
            "fieldname": "project", "fieldtype": "Link", "label": "Project",
            "options": "Duty Project",
        })
        if "field_order" in dt:
            dt["field_order"].append("project")
        with io.open(os.path.join(root, CRDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
        print("  doctype: Duty Change Request +project")

    out = dict(files)
    for label, old, new in EDITS_CR:
        out[CR] = out[CR].replace(old, new, 1)
    out[CR], _ = patch_chreq_update_sig(out[CR])
    for label, old, new in EDITS_JS:
        out[JS] = out[JS].replace(old, new, 1)
    for label, old, new in EDITS_PORTAL:
        out[PORTAL] = out[PORTAL].replace(old, new, 1)
    out[INIT] = out[INIT].replace('"3.59.7"', '"3.60.0"')

    for p in (CR, JS, PORTAL, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(out[p])
        print(f"  wrote {p}")
    print("wrote __init__.py -> 3.60.0")


if __name__ == "__main__":
    main()
