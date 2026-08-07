#!/usr/bin/env python3
"""Duty Board v3.66.0 — resource/capacity view (review gap #4).

"Is Khadijah overcommitted this week?" had no answer without manual
tallying. This adds the per-person load view across ALL active projects:

- Backend: get_team_load() — for every assignee on open (non-Completed,
  non-Suspended) tasks of active projects: open task count, overdue
  count, estimated hours remaining (sum of estimate_hours on open
  tasks), blocked count, and the projects they span. Unassigned open
  work is reported as its own row so it isn't invisible.
- UI: a 👥 button beside 📊 in the Projects side rail -> a Team grid,
  one row per person: Person · Open · Overdue · Est. remaining ·
  Blocked · Projects. Sorted heaviest-load first.

No schema. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.65.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. backend endpoint, appended after get_projects -----------------------
EP_ANCHOR = '''\t\tp.at_risk = 1 if (p.get("overdue", 0) or (g["worst_slip"] or 0) > 0) else 0
\treturn projects'''
EP_NEW = '''\t\tp.at_risk = 1 if (p.get("overdue", 0) or (g["worst_slip"] or 0) > 0) else 0
\treturn projects


@frappe.whitelist()
def get_team_load():
\t"""Per-person load across all active projects: open tasks, overdue,
\testimated hours remaining, blocked count, project spread."""
\trequire_staff()
\tprojects = frappe.get_all(
\t\t"Duty Project", filters={"status": "Active"}, fields=["name", "project_name"]
\t)
\tif not projects:
\t\treturn []
\tpnames = {p.name: p.project_name for p in projects}
\trows = frappe.get_all(
\t\t"Duty Project Task",
\t\tfilters={
\t\t\t"project": ["in", list(pnames)],
\t\t\t"column": ["not in", ["Completed", "Suspended"]],
\t\t},
\t\tfields=["name", "assignee", "project", "due_date", "estimate_hours", "blocked_by", "column"],
\t)
\tblockers = {r.blocked_by for r in rows if r.blocked_by}
\tblocker_done = {}
\tif blockers:
\t\tfor b in frappe.get_all(
\t\t\t"Duty Project Task",
\t\t\tfilters={"name": ["in", list(blockers)]},
\t\t\tfields=["name", "column"],
\t\t):
\t\t\tblocker_done[b.name] = b.column == "Completed"
\ttday = getdate(today())
\tload = {}
\tfor r in rows:
\t\tkey = r.assignee or "__unassigned__"
\t\tg = load.setdefault(key, {"open": 0, "overdue": 0, "est": 0.0, "blocked": 0, "projects": set()})
\t\tg["open"] += 1
\t\tg["est"] += r.estimate_hours or 0
\t\tg["projects"].add(r.project)
\t\tif r.due_date and getdate(r.due_date) < tday:
\t\t\tg["overdue"] += 1
\t\tif r.blocked_by and not blocker_done.get(r.blocked_by, False):
\t\t\tg["blocked"] += 1
\tout = []
\tfor user, g in load.items():
\t\tout.append({
\t\t\t"user": None if user == "__unassigned__" else user,
\t\t\t"full_name": _("Unassigned") if user == "__unassigned__" else frappe.utils.get_fullname(user),
\t\t\t"open": g["open"],
\t\t\t"overdue": g["overdue"],
\t\t\t"est_hours": round(g["est"], 1),
\t\t\t"blocked": g["blocked"],
\t\t\t"projects": sorted(pnames.get(p, p) for p in g["projects"]),
\t\t})
\tout.sort(key=lambda x: (-x["est_hours"], -x["open"]))
\treturn out'''

# --- 2. the 👥 button beside 📊 ----------------------------------------------
BTN_OLD = '''\t\t\t\t\t\t<button class="btn btn-sm btn-default duty-proj-portfolio" title="${__("Portfolio — all projects at a glance")}">📊</button>'''
BTN_NEW = '''\t\t\t\t\t\t<button class="btn btn-sm btn-default duty-proj-portfolio" title="${__("Portfolio — all projects at a glance")}">📊</button>
\t\t\t\t\t\t<button class="btn btn-sm btn-default duty-proj-team" title="${__("Team load — who's carrying what")}">👥</button>'''

WIRE_OLD = '''\t\tthis.$projects.find(".duty-proj-portfolio").on("click", () => this.render_portfolio());'''
WIRE_NEW = '''\t\tthis.$projects.find(".duty-proj-portfolio").on("click", () => this.render_portfolio());
\t\tthis.$projects.find(".duty-proj-team").on("click", () => this.render_team_load());'''

# --- 3. render_team_load, before render_portfolio ---------------------------
METHOD_OLD = '\trender_portfolio() {'
METHOD_NEW = '''\trender_team_load() {
\t\tthis.current_project = null;
\t\tif (this.is_mobile()) this.$projects.addClass("pj-detail");
\t\tconst $wrap = this.$projects.find(".duty-kanban-wrap").empty();
\t\tconst esc = frappe.utils.escape_html;
\t\t$wrap.html(`<div class="text-muted duty-plan-empty">${__("Loading team load…")}</div>`);
\t\tfrappe.call({
\t\t\tmethod: "duty_board.projects.get_team_load",
\t\t\tcallback: (r) => {
\t\t\t\tconst rows = r.message || [];
\t\t\t\tif (!rows.length) { $wrap.html(`<div class="text-muted duty-plan-empty">${__("No open work.")}</div>`); return; }
\t\t\t\tconst body = rows.map((p) => `
\t\t\t\t\t<tr>
\t\t\t\t\t\t<td><b style="color:${p.user ? this.user_color(p.user) : "#8a958f"}">${esc(p.full_name)}</b></td>
\t\t\t\t\t\t<td>${p.open}</td>
\t\t\t\t\t\t<td>${p.overdue ? `<span class="duty-proj-over">⚠ ${p.overdue}</span>` : `<span class="text-muted">0</span>`}</td>
\t\t\t\t\t\t<td>${p.est_hours ? `${p.est_hours}h` : `<span class="text-muted">—</span>`}</td>
\t\t\t\t\t\t<td>${p.blocked ? `🔒 ${p.blocked}` : `<span class="text-muted">0</span>`}</td>
\t\t\t\t\t\t<td class="duty-tl-projects">${p.projects.map((n) => `<span class="duty-tl-chip">${esc(n)}</span>`).join(" ")}</td>
\t\t\t\t\t</tr>`).join("");
\t\t\t\t$wrap.html(`
\t\t\t\t\t<div class="duty-pf">
\t\t\t\t\t\t<div class="duty-pf-head"><b>👥 ${__("Team load")}</b><span class="text-muted">${rows.length} ${__("people")} · ${__("heaviest first")}</span></div>
\t\t\t\t\t\t<table class="duty-pf-table">
\t\t\t\t\t\t\t<thead><tr><th>${__("Person")}</th><th>${__("Open")}</th><th>${__("Overdue")}</th><th>${__("Est. remaining")}</th><th>${__("Blocked")}</th><th>${__("Projects")}</th></tr></thead>
\t\t\t\t\t\t\t<tbody>${body}</tbody>
\t\t\t\t\t\t</table>
\t\t\t\t\t\t<p class="text-muted" style="font-size:12px;margin-top:10px">${__("Est. remaining sums estimate hours on open tasks — tasks without estimates count as 0, so fill estimates for a truthful picture.")}</p>
\t\t\t\t\t</div>`);
\t\t\t},
\t\t});
\t}

\trender_portfolio() {'''

# --- 4. CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-pf-badge.ok { background: #E7F5EF; color: #0E8A63; }'
CSS_NEW = '''\t\t\t.duty-pf-badge.ok { background: #E7F5EF; color: #0E8A63; }
\t\t\t.duty-tl-chip { display: inline-block; font-size: 11px; background: #F0F4F3; border-radius: 20px; padding: 2px 9px; margin: 1px 0; color: #4b5a55; }
\t\t\t.duty-tl-projects { max-width: 320px; }'''

EDITS_PROJ = [("team load endpoint", EP_ANCHOR, EP_NEW)]
EDITS_JS = [
    ("team button", BTN_OLD, BTN_NEW),
    ("team wire", WIRE_OLD, WIRE_NEW),
    ("render_team_load", METHOD_OLD, METHOD_NEW),
    ("team CSS", CSS_OLD, CSS_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def get_team_load(" in files[PROJ]:
        print("Already applied. Nothing to do.")
        return
    if '"3.65.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.65.0.")

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

    pj = files[PROJ]
    for _l, o, n in EDITS_PROJ: pj = pj.replace(o, n, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: get_team_load")

    js = files[JS]
    for _l, o, n in EDITS_JS: js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: 👥 button + team grid")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.65.0"', '"3.66.0"'))
    print("wrote __init__.py -> 3.66.0")


if __name__ == "__main__":
    main()
