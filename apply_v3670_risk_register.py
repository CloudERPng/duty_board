#!/usr/bin/env python3
"""Duty Board v3.67.0 — project risk register (review gap #6).

Risk lived only on Change Requests — reactive, scope-tied. Every major
project needs the proactive log: what could derail this, how likely, how
bad, what's our mitigation, who owns it. This adds it:

- New doctype: Duty Project Risk — project (Link), title, likelihood
  (Low/Medium/High), impact (Low/Medium/High), mitigation (Small Text),
  owner (Link User), status (Open/Mitigating/Closed). Severity is
  derived (likelihood x impact) for sorting, not stored.
- Endpoints: project_risks(project) list; risk_save(...) create/update;
  risk_delete(id). Staff-only.
- UI: a ⚠ Risks view on the project detail bar (Board · Calendar ·
  Phases · Risks) — the register: severity-sorted rows with inline
  add/edit/close/delete.
- Portfolio: get_projects counts open risks per project; the grid's
  Status cell shows "· N risks" when any are open.

Schema (new doctype) -> bench migrate && bench build && bench restart.
Anchored, idempotent. Requires v3.66.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
DTDIR = "duty_board/duty_board/doctype/duty_project_risk"
CHECK_ONLY = "--check" in sys.argv

RISK_DT = {
    "actions": [],
    "autoname": "hash",
    "creation": "2026-08-08 09:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": [
        "project", "title", "likelihood", "impact",
        "mitigation", "owner_user", "status",
    ],
    "fields": [
        {"fieldname": "project", "fieldtype": "Link", "label": "Project", "options": "Duty Project", "reqd": 1},
        {"fieldname": "title", "fieldtype": "Data", "label": "Risk", "reqd": 1},
        {"fieldname": "likelihood", "fieldtype": "Select", "label": "Likelihood", "options": "Low\nMedium\nHigh", "default": "Medium"},
        {"fieldname": "impact", "fieldtype": "Select", "label": "Impact", "options": "Low\nMedium\nHigh", "default": "Medium"},
        {"fieldname": "mitigation", "fieldtype": "Small Text", "label": "Mitigation"},
        {"fieldname": "owner_user", "fieldtype": "Link", "label": "Owner", "options": "User"},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Open\nMitigating\nClosed", "default": "Open"},
    ],
    "links": [],
    "modified": "2026-08-08 09:00:00.000000",
    "modified_by": "Administrator",
    "module": "Duty Board",
    "name": "Duty Project Risk",
    "naming_rule": "Random",
    "owner": "Administrator",
    "permissions": [
        {"create": 1, "delete": 1, "read": 1, "report": 1, "role": "System Manager", "write": 1}
    ],
    "sort_field": "modified",
    "sort_order": "DESC",
    "states": [],
}

# --- 1. endpoints appended after get_team_load ------------------------------
EP_ANCHOR = '''\tout.sort(key=lambda x: (-x["est_hours"], -x["open"]))
\treturn out'''
EP_NEW = '''\tout.sort(key=lambda x: (-x["est_hours"], -x["open"]))
\treturn out


_RISK_SCORE = {"Low": 1, "Medium": 2, "High": 3}


@frappe.whitelist()
def project_risks(project):
\t"""The project's risk register, severity-sorted (open first)."""
\trequire_staff()
\trows = frappe.get_all(
\t\t"Duty Project Risk",
\t\tfilters={"project": project},
\t\tfields=["name", "title", "likelihood", "impact", "mitigation", "owner_user", "status"],
\t)
\tfor r in rows:
\t\tr.severity = _RISK_SCORE.get(r.likelihood, 2) * _RISK_SCORE.get(r.impact, 2)
\t\tr.owner_name = frappe.utils.get_fullname(r.owner_user) if r.owner_user else None
\trows.sort(key=lambda r: (r.status == "Closed", -r.severity))
\treturn rows


@frappe.whitelist()
def risk_save(project, title, likelihood="Medium", impact="Medium", mitigation=None, owner_user=None, status="Open", name=None):
\t"""Create (no name) or update (name given) a risk."""
\trequire_staff()
\ttitle = (title or "").strip()
\tif not title:
\t\tfrappe.throw(_("Describe the risk."))
\tvals = {
\t\t"title": title[:200],
\t\t"likelihood": likelihood if likelihood in ("Low", "Medium", "High") else "Medium",
\t\t"impact": impact if impact in ("Low", "Medium", "High") else "Medium",
\t\t"mitigation": (mitigation or "").strip()[:1000] or None,
\t\t"owner_user": owner_user or None,
\t\t"status": status if status in ("Open", "Mitigating", "Closed") else "Open",
\t}
\tif name:
\t\tfrappe.db.set_value("Duty Project Risk", name, vals, update_modified=True)
\telse:
\t\tif not frappe.db.exists("Duty Project", project):
\t\t\tfrappe.throw(_("Unknown project."))
\t\tdoc = frappe.get_doc(dict(doctype="Duty Project Risk", project=project, **vals))
\t\tdoc.insert(ignore_permissions=True)
\tfrappe.db.commit()
\treturn project_risks(project)


@frappe.whitelist()
def risk_delete(name):
\trequire_staff()
\tproject = frappe.db.get_value("Duty Project Risk", name, "project")
\tfrappe.delete_doc("Duty Project Risk", name, ignore_permissions=True, force=True)
\tfrappe.db.commit()
\treturn project_risks(project)'''

# --- 2. portfolio: open-risk counts in get_projects -------------------------
PF_OLD = '''\t\tp.at_risk = 1 if (p.get("overdue", 0) or (g["worst_slip"] or 0) > 0) else 0
\treturn projects'''
PF_NEW = '''\t\tp.at_risk = 1 if (p.get("overdue", 0) or (g["worst_slip"] or 0) > 0) else 0
\trisk_counts = {}
\tfor rc in frappe.get_all(
\t\t"Duty Project Risk",
\t\tfilters={"project": ["in", [p.name for p in projects]], "status": ["!=", "Closed"]},
\t\tfields=["project", "count(name) as cnt"],
\t\tgroup_by="project",
\t):
\t\trisk_counts[rc.project] = rc.cnt
\tfor p in projects:
\t\tp.open_risks = risk_counts.get(p.name, 0)
\treturn projects'''

# --- 3. UI: Risks toggle on the project bar ---------------------------------
TOGGLE_OLD = '''\t\t\t\t\t<a class="duty-pj-v ${this._pj_view === "phases" ? "on" : ""}" data-v="phases">🚩 ${__("Phases")}${(data.milestones || []).length ? ` <b>${data.milestones.length}</b>` : ""}</a>'''
TOGGLE_NEW = '''\t\t\t\t\t<a class="duty-pj-v ${this._pj_view === "phases" ? "on" : ""}" data-v="phases">🚩 ${__("Phases")}${(data.milestones || []).length ? ` <b>${data.milestones.length}</b>` : ""}</a>
\t\t\t\t\t<a class="duty-pj-v ${this._pj_view === "risks" ? "on" : ""}" data-v="risks">⚠ ${__("Risks")}</a>'''

BRANCH_OLD = '''\t\tif (this._pj_view === "phases") {
\t\t\tthis.render_phases(project, data, $wrap);
\t\t\treturn;
\t\t}'''
BRANCH_NEW = '''\t\tif (this._pj_view === "phases") {
\t\t\tthis.render_phases(project, data, $wrap);
\t\t\treturn;
\t\t}
\t\tif (this._pj_view === "risks") {
\t\t\tthis.render_risks(project, $wrap);
\t\t\treturn;
\t\t}'''

# --- 4. render_risks method, before render_phases ---------------------------
METHOD_OLD = '\trender_phases(project, data, $wrap) {'
METHOD_NEW = '''\trender_risks(project, $wrap) {
\t\tconst esc = frappe.utils.escape_html;
\t\t$wrap.html(`<div class="text-muted duty-plan-empty">${__("Loading risks…")}</div>`);
\t\tconst SEVC = (s) => s >= 6 ? "#C2410C" : s >= 3 ? "#B45309" : "#65736F";
\t\tconst reload = () => frappe.call({ method: "duty_board.projects.project_risks", args: { project: project }, callback: (r) => draw(r.message || []) });
\t\tconst draw = (rows) => {
\t\t\tconst open = rows.filter((x) => x.status !== "Closed").length;
\t\t\tconst body = rows.map((x) => `
\t\t\t\t<tr class="${x.status === "Closed" ? "duty-risk-closed" : ""}" data-name="${x.name}">
\t\t\t\t\t<td><b style="color:${SEVC(x.severity)}">${x.severity}</b></td>
\t\t\t\t\t<td><b>${esc(x.title)}</b>${x.mitigation ? `<div class="duty-risk-mit">${esc(x.mitigation)}</div>` : ""}</td>
\t\t\t\t\t<td>${esc(x.likelihood)}</td>
\t\t\t\t\t<td>${esc(x.impact)}</td>
\t\t\t\t\t<td>${x.owner_name ? esc(x.owner_name) : `<span class="text-muted">—</span>`}</td>
\t\t\t\t\t<td>${esc(x.status)}</td>
\t\t\t\t\t<td class="duty-risk-acts"><a data-a="edit">✎</a> ${x.status !== "Closed" ? `<a data-a="close">✅</a>` : ""} <a data-a="del">🗑</a></td>
\t\t\t\t</tr>`).join("");
\t\t\t$wrap.html(`
\t\t\t\t<div class="duty-pf">
\t\t\t\t\t<div class="duty-pf-head"><b>⚠ ${__("Risk register")}</b><span class="text-muted">${open} ${__("open")}</span><button class="btn btn-xs btn-primary duty-risk-add" style="margin-left:auto">＋ ${__("Log a risk")}</button></div>
\t\t\t\t\t${rows.length ? `<table class="duty-pf-table"><thead><tr><th>${__("Sev")}</th><th>${__("Risk & mitigation")}</th><th>${__("Likelihood")}</th><th>${__("Impact")}</th><th>${__("Owner")}</th><th>${__("Status")}</th><th></th></tr></thead><tbody>${body}</tbody></table>` : `<div class="text-muted duty-plan-empty">${__("No risks logged. A major project with an empty register usually means nobody looked.")}</div>`}
\t\t\t\t</div>`);
\t\t\tconst dlg = (x) => frappe.prompt(
\t\t\t\t[
\t\t\t\t\t{ fieldname: "title", fieldtype: "Data", label: __("Risk"), reqd: 1, default: x ? x.title : "" },
\t\t\t\t\t{ fieldname: "likelihood", fieldtype: "Select", label: __("Likelihood"), options: ["Low", "Medium", "High"], default: x ? x.likelihood : "Medium" },
\t\t\t\t\t{ fieldname: "impact", fieldtype: "Select", label: __("Impact"), options: ["Low", "Medium", "High"], default: x ? x.impact : "Medium" },
\t\t\t\t\t{ fieldname: "mitigation", fieldtype: "Small Text", label: __("Mitigation"), default: x ? x.mitigation || "" : "" },
\t\t\t\t\t{ fieldname: "owner_user", fieldtype: "Link", options: "User", label: __("Owner"), default: x ? x.owner_user || "" : "" },
\t\t\t\t\t{ fieldname: "status", fieldtype: "Select", label: __("Status"), options: ["Open", "Mitigating", "Closed"], default: x ? x.status : "Open" },
\t\t\t\t],
\t\t\t\t(v) => frappe.call({
\t\t\t\t\tmethod: "duty_board.projects.risk_save",
\t\t\t\t\targs: { project: project, name: x ? x.name : null, ...v },
\t\t\t\t\tcallback: (r) => draw(r.message || []),
\t\t\t\t}),
\t\t\t\tx ? __("Edit risk") : __("Log a risk"), __("Save")
\t\t\t);
\t\t\t$wrap.find(".duty-risk-add").on("click", () => dlg(null));
\t\t\t$wrap.find(".duty-risk-acts a").on("click", (e) => {
\t\t\t\tconst a = $(e.currentTarget).data("a");
\t\t\t\tconst nm = $(e.currentTarget).closest("tr").data("name");
\t\t\t\tconst x = rows.find((z) => z.name === nm);
\t\t\t\tif (a === "edit") return dlg(x);
\t\t\t\tif (a === "close") return frappe.call({ method: "duty_board.projects.risk_save", args: { project: project, name: nm, title: x.title, likelihood: x.likelihood, impact: x.impact, mitigation: x.mitigation, owner_user: x.owner_user, status: "Closed" }, callback: (r) => draw(r.message || []) });
\t\t\t\tif (a === "del") return frappe.confirm(__("Delete this risk entry?"), () => frappe.call({ method: "duty_board.projects.risk_delete", args: { name: nm }, callback: (r) => draw(r.message || []) }));
\t\t\t});
\t\t};
\t\treload();
\t}

\trender_phases(project, data, $wrap) {'''

# --- 5. portfolio grid shows open risk count --------------------------------
PFUI_OLD = '''\t\t\t\t\t<td>${p.at_risk ? `<span class="duty-pf-badge risk">At risk</span>` : `<span class="duty-pf-badge ok">On track</span>`}</td>'''
PFUI_NEW = '''\t\t\t\t\t<td>${p.at_risk ? `<span class="duty-pf-badge risk">At risk</span>` : `<span class="duty-pf-badge ok">On track</span>`}${p.open_risks ? `<div class="duty-pf-risks">⚠ ${p.open_risks} ${__("risks")}</div>` : ""}</td>'''

# --- 6. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-tl-projects { max-width: 320px; }'
CSS_NEW = '''\t\t\t.duty-tl-projects { max-width: 320px; }
\t\t\t.duty-risk-mit { font-size: 11.5px; color: #65736F; margin-top: 2px; }
\t\t\t.duty-risk-closed { opacity: .55; }
\t\t\t.duty-risk-acts a { cursor: pointer; opacity: .65; margin-right: 4px; text-decoration: none; }
\t\t\t.duty-risk-acts a:hover { opacity: 1; }
\t\t\t.duty-pf-risks { font-size: 11px; color: #B45309; font-weight: 700; margin-top: 3px; }'''

EDITS_PROJ = [
    ("risk endpoints", EP_ANCHOR, EP_NEW),
    ("portfolio risk counts", PF_OLD, PF_NEW),
]
EDITS_JS = [
    ("risks toggle", TOGGLE_OLD, TOGGLE_NEW),
    ("risks branch", BRANCH_OLD, BRANCH_NEW),
    ("render_risks", METHOD_OLD, METHOD_NEW),
    ("portfolio risk cell", PFUI_OLD, PFUI_NEW),
    ("risk CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def project_risks(" in files[PROJ]:
        print("Already applied. Nothing to do.")
        return
    if '"3.66.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.66.0.")

    problems = []
    for label, o, _ in EDITS_PROJ:
        if files[PROJ].count(o) != 1: problems.append(f"  [{files[PROJ].count(o)}] proj: {label}")
    for label, o, _ in EDITS_JS:
        if files[JS].count(o) != 1: problems.append(f"  [{files[JS].count(o)}] js: {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS_PROJ)+len(EDITS_JS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    dtdir = os.path.join(root, DTDIR)
    os.makedirs(dtdir, exist_ok=True)
    with io.open(os.path.join(dtdir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(dtdir, "duty_project_risk.json"), "w", encoding="utf-8") as f:
        json.dump(RISK_DT, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(dtdir, "duty_project_risk.py"), "w", encoding="utf-8") as f:
        f.write(
            "import frappe\nfrom frappe.model.document import Document\n\n\nclass DutyProjectRisk(Document):\n\tpass\n"
        )
    print("  doctype: Duty Project Risk created")

    pj = files[PROJ]
    for _l, o, n in EDITS_PROJ: pj = pj.replace(o, n, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: project_risks/risk_save/risk_delete + portfolio counts")

    js = files[JS]
    for _l, o, n in EDITS_JS: js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: Risks view + portfolio cell")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.66.0"', '"3.67.0"'))
    print("wrote __init__.py -> 3.67.0")


if __name__ == "__main__":
    main()
