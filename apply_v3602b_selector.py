#!/usr/bin/env python3
"""Duty Board v3.60.2b — the client project selector.

On the foundation from v3.60.2a. A selector at the top of the client's
project view; choosing a project scopes tasks, phases, change requests
and documents to it. "General" holds the catch-all / relationship
bucket (contracts, SLAs). The selector appears only when the customer
has 2+ projects — a single-project client sees exactly today's view.
Chat stays global (unlabelled), by design.

Mechanism: a global window._psel (project id, or "" = all). loadProjects()
fetches client_projects() and paints the bar; setPsel() re-runs the four
renderers. Each renderer filters by _psel against project ids the
foundation already put in every payload (tasks, milestones, chreqs carry
project; shelf docs carry project).

JS/portal only: bench build --app duty_board && bench restart.
Anchored, all-or-nothing, idempotent. Requires v3.60.2 (foundation).
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

# --- 1. selector bar markup, at the top of the milestones (Projects) card ---
A1_OLD = '''\t<div class="card mstones">
\t\t<h3 class="foldh" onclick="fold(this,'mstones')"><span class="fc">▾</span> <svg class="li" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/></svg> <span class="t">Project milestones</span></h3>'''
A1_NEW = '''\t<div id="pselwrap" style="display:none"></div>
\t<div class="card mstones">
\t\t<h3 class="foldh" onclick="fold(this,'mstones')"><span class="fc">▾</span> <svg class="li" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/></svg> <span class="t">Project milestones</span></h3>'''

# --- 2. loadProjects() + setPsel(), and the boot call ------------------------
A2_OLD = '''\tload();
\tloadMeetings();
\tloadMilestones();
\tloadChreqs();
\tloadTraining();'''
A2_NEW = '''\tload();
\tloadMeetings();
\tloadProjects();
\tloadMilestones();
\tloadChreqs();
\tloadTraining();'''

# add the two functions just before loadMilestones's definition
A3_OLD = '''/* ---- milestones ---- */
function loadMilestones() {'''
A3_NEW = '''/* ---- project selector ---- */
window._psel = window._psel || "";
function loadProjects() {
\tapi("client_projects")
\t\t.then((list) => {
\t\t\twindow._projs = list || [];
\t\t\tconst wrap = document.getElementById("pselwrap");
\t\t\tif (!wrap) return;
\t\t\t// Selector only earns its place with 2+ real projects (General always
\t\t\t// present, so ">2 entries" means "more than one actual project").
\t\t\tif (window._projs.length <= 2) { wrap.style.display = "none"; window._psel = ""; return; }
\t\t\twrap.style.display = "block";
\t\t\twrap.className = "pselbar";
\t\t\twrap.innerHTML = `<span class="psellbl">Project</span><select id="pselsel">
\t\t\t\t<option value="">All projects</option>
\t\t\t\t${window._projs.map((p) => `<option value="${esc(p.id)}" ${window._psel === p.id ? "selected" : ""}>${esc(p.label)}</option>`).join("")}
\t\t\t</select>`;
\t\t\tdocument.getElementById("pselsel").addEventListener("change", (e) => setPsel(e.target.value));
\t\t})
\t\t.catch((e) => console.warn("projects:", e.message));
}
function setPsel(v) {
\twindow._psel = v || "";
\t// Re-run every scoped surface with the new filter.
\tif (window.LAST) render(window.LAST);
\tif (window._msrows) renderMilestones(window._msrows);
\tif (window._chreqs) renderChreqs(window._chreqs);
\tif (window._DOCS && window.renderDocList) window.renderDocList();
}
function _pselMatch(projectId) {
\t// "" = all. General entry id may be a real catch-all project or "__general__".
\tif (!window._psel) return true;
\tif (window._psel === "__general__") return !projectId;
\treturn projectId === window._psel;
}

/* ---- milestones ---- */
function loadMilestones() {'''

# --- 3. tasks filter honours _psel ------------------------------------------
A4_OLD = '\tconst rows = (d.tasks || []).filter((x) => !filt || x.status === filt);'
A4_NEW = '\tconst rows = (d.tasks || []).filter((x) => !filt || x.status === filt).filter((x) => _pselMatch(x.project));'

# --- 4. milestones: remember rows + filter by _psel -------------------------
A5_OLD = '''function renderMilestones(rows) {
\trows = rows || [];'''
A5_NEW = '''function renderMilestones(rows) {
\twindow._msrows = rows || [];
\trows = (rows || []).filter((m) => _pselMatch(m.project));'''

# --- 5. chreqs: filter by _psel ---------------------------------------------
A6_OLD = '''function renderChreqs(rows) {
\trows = rows || [];
\twindow._chreqs = rows;'''
A6_NEW = '''function renderChreqs(rows) {
\twindow._chreqs = rows || [];
\trows = (rows || []).filter((c) => _pselMatch(c.project));'''

# --- 6. docs: filter list by _psel, expose renderList for re-run ------------
A7_OLD = '''\t\t\tconst renderList = () => {
\t\t\t\tconst q = (window._docq || "").toLowerCase();
\t\t\t\tconst rows = window._DOCS.filter((d) =>
\t\t\t\t\t(!window._doccat || d.category === window._doccat) &&'''
A7_NEW = '''\t\t\tconst renderList = () => {
\t\t\t\tconst q = (window._docq || "").toLowerCase();
\t\t\t\tconst rows = window._DOCS.filter((d) => _pselMatch(d.project)).filter((d) =>
\t\t\t\t\t(!window._doccat || d.category === window._doccat) &&'''

A8_OLD = '\t\t\trenderList();'
A8_NEW = '\t\t\twindow.renderDocList = renderList;\n\t\t\trenderList();'

# --- 7. CSS ------------------------------------------------------------------
A9_OLD = '\t#msstep { display: flex; align-items: flex-start; overflow-x: auto; padding: 4px 0 10px; -webkit-overflow-scrolling: touch; }'
A9_NEW = '''\t#msstep { display: flex; align-items: flex-start; overflow-x: auto; padding: 4px 0 10px; -webkit-overflow-scrolling: touch; }
\t.pselbar { display: flex; align-items: center; gap: 10px; background: #fff; border: 1px solid #E4EAE8; border-radius: 12px; padding: 10px 14px; margin: 0 0 12px; }
\t.pselbar .psellbl { font-size: 12px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; color: #0F5C55; }
\t.pselbar select { flex: 1; max-width: 340px; border: 1px solid #D4DCD8; border-radius: 8px; padding: 7px 10px; font-size: 14px; font-family: inherit; background: #fff; }'''

EDITS = [
    ("selector wrap markup", A1_OLD, A1_NEW),
    ("boot loadProjects call", A2_OLD, A2_NEW),
    ("loadProjects + setPsel fns", A3_OLD, A3_NEW),
    ("tasks filter _psel", A4_OLD, A4_NEW),
    ("milestones filter _psel", A5_OLD, A5_NEW),
    ("chreqs filter _psel", A6_OLD, A6_NEW),
    ("docs filter _psel", A7_OLD, A7_NEW),
    ("docs expose renderList", A8_OLD, A8_NEW),
    ("selector CSS", A9_OLD, A9_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "function loadProjects()" in files[PORTAL]:
        print("Already applied. Nothing to do.")
        return
    if '"3.60.2"' not in files[INIT]:
        sys.exit("ABORT: not at v3.60.2 — apply the foundation (v3.60.2a) first.")

    problems = [f"  [{files[PORTAL].count(o)}] {label}" for label, o, _ in EDITS if files[PORTAL].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = files[PORTAL]
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, PORTAL), "w", encoding="utf-8") as f:
        f.write(out)

    # version already 3.60.2 from the foundation; bump patch marker in a comment
    # so both halves share the minor. No number change needed.
    print("portal selector applied (version stays 3.60.2 — foundation + selector).")


if __name__ == "__main__":
    main()
