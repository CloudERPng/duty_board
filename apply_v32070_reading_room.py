#!/usr/bin/env python3
"""Duty Board v3.207.0 — THE READING ROOM: focus mode for the client academy.

loadTraining() builds #mycerts and #mytracks as sibling divs inserted BEFORE
#acad, then every drill-down — course, lesson, exam — rewrites only #acad. The
gallery above is never cleared, so a learner reads a lesson appended underneath
the whole index, and (as of v3.206.0) sits a proctored, timed assessment with
their certificate cards above the countdown.

This patch introduces a focus state on <body> and a proper reading shell.

  body[data-acad="read"] — course view, lesson, result: certificates, tracks
      and the card's own "Training" header are hidden. Nothing but the thing
      you opened.
  body[data-acad="exam"] — the proctored runner: the above, plus the bottom
      tab bar. A sat exam should not offer four ways out of the room.
  body without data-acad — the index, exactly as before.

The reading view itself is rebuilt: a slim bar carrying the TRACK you are on,
then course and lesson position, a hairline progress rule, the lesson title as
a real heading, the body centred at a readable measure instead of ragged
against a wide card, and the actions on a quiet footer.

Backend: _track_for_module resolves which certification track a course sits in
for this reader — preferring one they are actually pursuing, since a module can
belong to several — and client_course returns it for the breadcrumb.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema, no migrate. Anchored, idempotent.
Requires v3.206.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


# --- 1. backend: which track is this course part of, for this reader -------
TRK_OLD = '''@frappe.whitelist()
def client_course(record):'''

TRK_NEW = '''def _track_for_module(room, user, module):
\t"""The track to name in the reader's breadcrumb. A module can sit in
\tseveral tracks; prefer one the reader is actually pursuing, then fall
\tback to the first client track that contains it. None when it stands
\talone — the breadcrumb then shows the product."""
\tparents = frappe.get_all(
\t\t"Duty Certification Track Module",
\t\tfilters={"module": module},
\t\tfields=["parent"],
\t)
\tif not parents:
\t\treturn None
\tnames = list({p.parent for p in parents})
\ttracks = frappe.get_all(
\t\t"Duty Certification Track",
\t\tfilters={"name": ["in", names], "active": 1, "audience": "Client"},
\t\tfields=["name", "title", "product"],
\t\torder_by="title asc",
\t)
\tif not tracks:
\t\treturn None
\tbest = None
\tfor t in tracks:
\t\tmods = frappe.get_all(
\t\t\t"Duty Certification Track Module",
\t\t\tfilters={"parent": t.name},
\t\t\tfields=["module"],
\t\t\torder_by="idx asc",
\t\t)
\t\tmod_names = [m.module for m in mods]
\t\tif module not in mod_names:
\t\t\tcontinue
\t\tdone = frappe.db.count(
\t\t\t"Duty Training Record",
\t\t\t{
\t\t\t\t"room": room.name, "trainee": user,
\t\t\t\t"module": ["in", mod_names], "status": "Completed",
\t\t\t},
\t\t)
\t\thas = frappe.db.count(
\t\t\t"Duty Training Record",
\t\t\t{"room": room.name, "trainee": user, "module": ["in", mod_names]},
\t\t)
\t\trow = {
\t\t\t"title": t.title,
\t\t\t"product": t.product,
\t\t\t"position": mod_names.index(module) + 1,
\t\t\t"total": len(mod_names),
\t\t\t"done": done,
\t\t\t"pursuing": has >= len(mod_names),
\t\t}
\t\tif row["pursuing"]:
\t\t\treturn row
\t\tif best is None:
\t\t\tbest = row
\treturn best


@frappe.whitelist()
def client_course(record):'''

CRET_OLD = '''	if not rec or rec.room != room.name or rec.trainee != frappe.session.user:
		frappe.throw(_("Not found."), frappe.PermissionError)
	mod = frappe.db.get_value(
		"Duty Training Module", rec.module, ["title", "product", "description"], as_dict=True
	)
	lessons = frappe.get_all(
		"Duty Lesson",
		filters={"module": rec.module},
		fields=["name", "title", "est_minutes"],
		order_by="sort_order asc, creation asc",
	)
	done = {
		p.lesson
		for p in frappe.get_all(
			"Duty Lesson Progress",
			filters={"user": frappe.session.user, "module": rec.module, "completed_at": ["is", "set"]},
			fields=["lesson"],
		)
	}
	return {
		"record": record,
		"title": mod.title,
		"product": mod.product,
		"description": mod.description,
'''

# my_course is byte-identical from "mod = frappe.db.get_value" onward, so the
# anchor must start at client_course's own room guard to stay unique.
CRET_NEW = CRET_OLD + '''		"track": _track_for_module(room, frappe.session.user, rec.module),
'''


# --- 2. portal: the focus switch -------------------------------------------
FOCUS_OLD = '''function loadTraining() {
\tstopBeat();'''

FOCUS_NEW = '''function acadFocus(mode) {
\t/* "" = index, "read" = course/lesson/result, "exam" = proctored runner.
\t   The index blocks (#mycerts, #mytracks) are siblings of #acad, so they
\t   survive an innerHTML rewrite — hiding them is the only way to be alone
\t   with the material. */
\tif (mode) document.body.setAttribute("data-acad", mode);
\telse document.body.removeAttribute("data-acad");
}
function loadTraining() {
\tstopBeat();
\tacadFocus("");'''

OC_OLD = '''function openCourse(record) {
\tstopBeat();'''
OC_NEW = '''function openCourse(record) {
\tstopBeat();
\tacadFocus("read");'''

OL_OLD = '''function openLesson(lesson, record) {
\tstopBeat();'''
OL_NEW = '''function openLesson(lesson, record) {
\tstopBeat();
\tacadFocus("read");'''

SQ_OLD = '''function startQuiz(record) {
\tstopBeat();'''
SQ_NEW = '''function startQuiz(record) {
\tstopBeat();
\tacadFocus("read");'''

ER_OLD = '''function examRunner(t, record) {
\tconst acad = () => document.getElementById("acad");'''
ER_NEW = '''function examRunner(t, record) {
\tacadFocus("exam");
\tconst acad = () => document.getElementById("acad");'''

XR_OLD = '''function examResult(res, record) {
\tconst canRetake'''
XR_NEW = '''function examResult(res, record) {
\tacadFocus("read");
\tconst canRetake'''


# Exam focus hides the tab bar. Every exit from the runner - finish, network
# error, forfeit - must hand the tab bar back, or a failed call strands the
# candidate in a room with no door. cleanup() sits on all of those paths.
ERC_OLD = "\tconst cleanup = () => { clearInterval(timer); timer = null; window.removeEventListener(\"blur\", onBlur); };"
ERC_NEW = "\tconst cleanup = () => { clearInterval(timer); timer = null; window.removeEventListener(\"blur\", onBlur); acadFocus(\"read\"); };"


# --- 3. portal: the reading shell ------------------------------------------
RD_OLD = '''\t\tdocument.getElementById("acad").innerHTML = `
\t\t\t<div style="background:linear-gradient(120deg,#0A473F,#087A67 60%,#146B62);color:#fff;border-radius:12px;padding:14px 18px;margin-bottom:16px">
\t\t\t\t<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;opacity:.75">${esc(c.product || "")} \u00b7 Lesson ${idx + 1} of ${c.lessons.length}</div>
\t\t\t\t<div style="font-size:20px;font-weight:800;margin-top:3px">${esc(l.title)}</div>
\t\t\t\t<div style="font-size:12px;opacity:.85;margin-top:5px">\u23F1 ~${l.est_minutes} min read</div>
\t\t\t</div>
\t\t\t<div id="lessonbody"></div>
\t\t\t<div style="display:flex;gap:10px;align-items:center;margin-top:18px;border-top:1px solid #EEF2F0;padding-top:12px;flex-wrap:wrap">
\t\t\t\t<span style="display:flex;gap:5px;margin-right:auto">${c.lessons.map((x, k) => `<i style="width:9px;height:9px;border-radius:50%;background:${x.done ? "#087A67" : "#D9E4E0"};${k === idx ? "outline:2px solid #087A67;outline-offset:2px" : ""}"></i>`).join("")}</span>
\t\t\t\t${l.done
\t\t\t\t\t? `<span class="acaddone">\u2713 Read</span>${next ? `<button onclick="openLesson('${esc(next.name)}','${esc(record)}')">Next lesson \u2192</button>` : ""}`
\t\t\t\t\t: `<button id="lread" onclick="markRead('${esc(lesson)}','${esc(record)}')">\u2713 Mark as read${next ? " \u00b7 next \u2192" : ""}</button>`}
\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="openCourse('${esc(record)}')">\u2190 Lessons</button>
\t\t\t</div>`;'''

RD_NEW = '''\t\tconst trk = c.track || null;
\t\tconst spine = trk ? trk.title : (c.product || "");
\t\tconst place = (trk ? `Course ${trk.position} of ${trk.total} \u00b7 ` : "") + esc(c.title || "");
\t\tconst pct = c.lessons.length ? Math.round(((idx + 1) / c.lessons.length) * 100) : 0;
\t\tdocument.getElementById("acad").innerHTML = `
\t\t\t<div class="rdbar">
\t\t\t\t<button class="rdback" onclick="openCourse('${esc(record)}')" title="Back to the course">\u2190</button>
\t\t\t\t<div class="rdcrumb">
\t\t\t\t\t<b>${esc(spine)}</b>
\t\t\t\t\t<span>${place} \u00b7 Lesson ${idx + 1} of ${c.lessons.length}</span>
\t\t\t\t</div>
\t\t\t\t<span class="rdmin">~${l.est_minutes} min</span>
\t\t\t</div>
\t\t\t<div class="rdprog"><i style="width:${pct}%"></i></div>
\t\t\t<div class="rdwrap">
\t\t\t\t<h1 class="rdtitle">${esc(l.title)}</h1>
\t\t\t\t<div id="lessonbody"></div>
\t\t\t\t<div class="rdfoot">
\t\t\t\t\t<span class="rddots">${c.lessons.map((x, k) => `<i class="${x.done ? "on" : ""}${k === idx ? " cur" : ""}"></i>`).join("")}</span>
\t\t\t\t\t${l.done
\t\t\t\t\t\t? `<span class="acaddone">\u2713 Read</span>${next ? `<button onclick="openLesson('${esc(next.name)}','${esc(record)}')">Next lesson \u2192</button>` : ""}`
\t\t\t\t\t\t: `<button id="lread" onclick="markRead('${esc(lesson)}','${esc(record)}')">\u2713 Mark as read${next ? " \u00b7 next \u2192" : ""}</button>`}
\t\t\t\t\t<button class="rdghost" onclick="openCourse('${esc(record)}')">\u2190 All lessons</button>
\t\t\t\t</div>
\t\t\t</div>`;'''


# --- 4. portal: css --------------------------------------------------------
CSS_OLD = '''\t/* ---- proctored assessment ---- */'''

CSS_NEW = '''\t/* ---- the reading room ---- */
\tbody[data-acad] #mycerts, body[data-acad] #mytracks { display: none !important; }
\tbody[data-acad] .card.acad > h3.foldh { display: none !important; }
\tbody[data-acad="exam"] .tabbar { display: none !important; }

\t.rdbar { display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 6;
\t\tbackground: #fff; padding: 4px 0 10px; }
\t.rdback { flex: 0 0 auto; width: 32px; height: 32px; padding: 0; border-radius: 50%;
\t\tbackground: #EEF3F1 !important; color: #17403A !important; font-size: 16px; line-height: 1; }
\t.rdcrumb { flex: 1; min-width: 0; }
\t.rdcrumb b { display: block; font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase;
\t\tcolor: var(--brand-700); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
\t.rdcrumb span { display: block; font-size: 12.5px; color: #6B7C77; margin-top: 2px;
\t\twhite-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
\t.rdmin { flex: 0 0 auto; font-size: 12px; color: #6B7C77; }
\t.rdprog { height: 3px; border-radius: 99px; background: #E9EFEC; overflow: hidden; margin-bottom: 26px; }
\t.rdprog i { display: block; height: 100%; background: var(--brand); transition: width .3s ease; }
\t.rdwrap { max-width: 660px; margin: 0 auto; }
\t.rdtitle { font-family: Fraunces, Georgia, serif; font-size: 30px; line-height: 1.2; font-weight: 600;
\t\tmargin: 0 0 22px; color: #16211F; letter-spacing: -.2px; }
\t.rdfoot { display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
\t\tmargin-top: 34px; border-top: 1px solid #EEF2F0; padding-top: 16px; }
\t.rddots { display: flex; gap: 5px; margin-right: auto; }
\t.rddots i { width: 9px; height: 9px; border-radius: 50%; background: #D9E4E0; }
\t.rddots i.on { background: #087A67; }
\t.rddots i.cur { outline: 2px solid #087A67; outline-offset: 2px; }
\t.rdghost { background: #E2E8E5 !important; color: #2A3833 !important; }
\t@media (max-width: 700px) {
\t\t.rdtitle { font-size: 25px; margin-bottom: 18px; }
\t\t.rdprog { margin-bottom: 20px; }
\t\t.rdmin { display: none; }
\t}

\t/* ---- proctored assessment ---- */'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _track_for_module(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.206.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.206.0.")

    edits = [
        (CR, TRK_OLD, TRK_NEW, "_track_for_module"),
        (CR, CRET_OLD, CRET_NEW, "client_course returns track"),
        (PORTAL, FOCUS_OLD, FOCUS_NEW, "acadFocus + index exit"),
        (PORTAL, OC_OLD, OC_NEW, "openCourse focus"),
        (PORTAL, OL_OLD, OL_NEW, "openLesson focus"),
        (PORTAL, SQ_OLD, SQ_NEW, "startQuiz focus"),
        (PORTAL, ER_OLD, ER_NEW, "examRunner focus"),
        (PORTAL, ERC_OLD, ERC_NEW, "exam cleanup restores the tab bar"),
        (PORTAL, XR_OLD, XR_NEW, "examResult focus"),
        (PORTAL, RD_OLD, RD_NEW, "reading shell"),
        (PORTAL, CSS_OLD, CSS_NEW, "reading room css"),
    ]

    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)

    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: _track_for_module + course breadcrumb")
    print("  portal.html: focus mode, reading shell, css")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.206.0"', '"3.207.0"'))
    print("wrote __init__.py -> 3.207.0")


if __name__ == "__main__":
    main()
