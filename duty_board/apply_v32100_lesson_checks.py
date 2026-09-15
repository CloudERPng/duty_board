#!/usr/bin/env python3
"""Duty Board v3.210.0 — CHECK QUESTIONS: the lesson teaches back.

With a facilitator in the room, a terse manual works because a human reads
confusion off faces. Self-serve, the material carries the whole teaching load,
and one terminal exam nine chapters later is too coarse an instrument: a
learner finds out they misread chapter 2 by failing the paper, with no idea
which part broke.

Two or three questions at the foot of each lesson fix that. They are formative,
not scored — not drawn from the exam bank, never on the transcript. Get one
wrong and you are told why, immediately, and you try again with the reasoning
in front of you.

They also replace the reading-dwell timer I previously recommended and am now
withdrawing. A timer is beaten by leaving a tab open and it punishes fast
readers to catch slow cheats. A check question cannot be passed by waiting, and
it produces the reading evidence as a by-product of actually teaching.

  Duty Lesson Check (new): lesson, question, opt_a..d, correct, rationale,
    sort_order, active. Standalone rather than a child table, mirroring
    Duty Quiz Question, so banks can be seeded in bulk by patch script.
  Duty Lesson Progress: +checks_passed.

  client_lesson now returns the checks with options shuffled per serve and the
    answer key withheld. client_lesson_check grades server-side and returns
    per-question outcome and rationale; passing every check marks the lesson
    read in the same act. client_lesson_done refuses a lesson that has
    unpassed checks — the free click is gone, but only where a bank exists.

Presence is the switch: a lesson with no checks behaves exactly as it does
today, so nothing in the eight existing tracks changes until a bank is written
for it.

Deploy: apply -> bench migrate (new doctype + field) -> bench build --app
duty_board -> clear-cache + clear-website-cache -> restart. Anchored,
idempotent. Requires v3.209.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
LPDT = "duty_board/duty_board/doctype/duty_lesson_progress/duty_lesson_progress.json"
DT_DIR = "duty_board/duty_board/doctype"
CHECK_ONLY = "--check" in sys.argv


CHECK_JSON = {
    "actions": [],
    "autoname": "hash",
    "creation": "2026-08-13 12:00:00.000000",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": [
        "lesson", "sort_order", "question", "opt_a", "opt_b", "opt_c",
        "opt_d", "correct", "rationale", "active",
    ],
    "fields": [
        {"fieldname": "lesson", "fieldtype": "Link", "label": "Lesson",
         "options": "Duty Lesson", "reqd": 1, "in_list_view": 1},
        {"fieldname": "sort_order", "fieldtype": "Int", "label": "Sort Order"},
        {"fieldname": "question", "fieldtype": "Small Text", "label": "Question",
         "reqd": 1, "in_list_view": 1},
        {"fieldname": "opt_a", "fieldtype": "Small Text", "label": "Option A", "reqd": 1},
        {"fieldname": "opt_b", "fieldtype": "Small Text", "label": "Option B", "reqd": 1},
        {"fieldname": "opt_c", "fieldtype": "Small Text", "label": "Option C"},
        {"fieldname": "opt_d", "fieldtype": "Small Text", "label": "Option D"},
        {"fieldname": "correct", "fieldtype": "Select", "label": "Correct",
         "options": "A\nB\nC\nD", "reqd": 1},
        {"fieldname": "rationale", "fieldtype": "Small Text", "label": "Why",
         "description": "Shown the moment they answer. This is the teaching, not a scold."},
        {"fieldname": "active", "fieldtype": "Check", "label": "Active", "default": "1"},
    ],
    "index_web_pages_for_search": 1,
    "links": [],
    "modified": "2026-08-13 12:00:00.000000",
    "modified_by": "Administrator",
    "module": "Duty Board",
    "name": "Duty Lesson Check",
    "owner": "Administrator",
    "permissions": [{
        "create": 1, "delete": 1, "email": 1, "export": 1, "print": 1,
        "read": 1, "report": 1, "role": "System Manager", "share": 1, "write": 1,
    }],
    "sort_field": "modified",
    "sort_order": "DESC",
    "states": [],
}

CTRL = '''# Copyright (c) 2026, Xlevel Retail Systems Ltd
import frappe
from frappe.model.document import Document


class DutyLessonCheck(Document):
\tpass
'''


# --- 1. serve the checks with the key withheld -----------------------------
CL_OLD = '''\troom, l, rec = _lesson_access(lesson)\n\tuser = frappe.session.user\n\tprog = frappe.db.get_value(\n\t\t"Duty Lesson Progress", {"user": user, "lesson": lesson},\n\t\t["name", "seconds", "completed_at"], as_dict=True,\n\t)\n\tif not prog:\n\t\tfrappe.get_doc(\n\t\t\t{\n\t\t\t\t"doctype": "Duty Lesson Progress",\n\t\t\t\t"user": user,\n\t\t\t\t"lesson": lesson,\n\t\t\t\t"module": l.module,\n\t\t\t\t"opened_at": now_datetime(),\n\t\t\t\t"seconds": 0,\n\t\t\t}\n\t\t).insert(ignore_permissions=True)\n\t\tprog = frappe._dict(seconds=0, completed_at=None)\n\tif rec.status == "Assigned":\n\t\tfrappe.db.set_value("Duty Training Record", rec.name, "status", "Reading", update_modified=False)\n\tfrappe.db.commit()\n\treturn {
\t\t"title": l.title,
\t\t"html": frappe.utils.sanitize_html(l.content or ""),
\t\t"est_minutes": l.est_minutes or 5,
\t\t"seconds": prog.seconds or 0,
\t\t"done": bool(prog.completed_at),
\t}'''

CL_NEW = '''\troom, l, rec = _lesson_access(lesson)\n\tuser = frappe.session.user\n\tprog = frappe.db.get_value(\n\t\t"Duty Lesson Progress", {"user": user, "lesson": lesson},\n\t\t["name", "seconds", "completed_at"], as_dict=True,\n\t)\n\tif not prog:\n\t\tfrappe.get_doc(\n\t\t\t{\n\t\t\t\t"doctype": "Duty Lesson Progress",\n\t\t\t\t"user": user,\n\t\t\t\t"lesson": lesson,\n\t\t\t\t"module": l.module,\n\t\t\t\t"opened_at": now_datetime(),\n\t\t\t\t"seconds": 0,\n\t\t\t}\n\t\t).insert(ignore_permissions=True)\n\t\tprog = frappe._dict(seconds=0, completed_at=None)\n\tif rec.status == "Assigned":\n\t\tfrappe.db.set_value("Duty Training Record", rec.name, "status", "Reading", update_modified=False)\n\tfrappe.db.commit()\n\tchecks_passed = bool(
\t\tfrappe.db.get_value(
\t\t\t"Duty Lesson Progress", {"user": user, "lesson": lesson}, "checks_passed"
\t\t)
\t)
\treturn {
\t\t"title": l.title,
\t\t"html": frappe.utils.sanitize_html(l.content or ""),
\t\t"est_minutes": l.est_minutes or 5,
\t\t"seconds": prog.seconds or 0,
\t\t"done": bool(prog.completed_at),
\t\t"checks": _lesson_checks_for_serve(lesson),
\t\t"checks_passed": checks_passed,
\t}


def _lesson_checks(lesson):
\treturn frappe.get_all(
\t\t"Duty Lesson Check",
\t\tfilters={"lesson": lesson, "active": 1},
\t\tfields=["name", "question", "opt_a", "opt_b", "opt_c", "opt_d", "correct", "rationale"],
\t\torder_by="sort_order asc, creation asc",
\t)


def _check_options(c):
\t"""(letter index, text) for each non-blank option. A check may carry two
\toptions rather than four, and dropping a blank must NOT shift the answer
\tkey: if C is empty and D is correct, D is still index 3."""
\treturn [
\t\t(i, o)
\t\tfor i, o in enumerate((c.opt_a, c.opt_b, c.opt_c, c.opt_d))
\t\tif (o or "").strip()
\t]


def _lesson_checks_for_serve(lesson):
\t"""Shuffled per serve, answer key withheld. The shuffle map is rebuilt on
\tgrading from the same seed the client is handed, so nothing about which
\toption is right ever crosses the wire before they answer."""
\timport random

\tout = []
\tfor c in _lesson_checks(lesson):
\t\topts = _check_options(c)
\t\torder = list(range(len(opts)))
\t\trandom.Random(f"{frappe.session.user}:{c.name}").shuffle(order)
\t\tout.append({
\t\t\t"name": c.name,
\t\t\t"question": c.question,
\t\t\t"options": [opts[i][1] for i in order],
\t\t})
\treturn out


def _check_order(name, count):
\timport random

\torder = list(range(count))
\trandom.Random(f"{frappe.session.user}:{name}").shuffle(order)
\treturn order


@frappe.whitelist()
def client_lesson_check(lesson, answers):
\t"""Grade the end-of-lesson checks. Formative: the outcome is never scored,
\tnever stored per question, and never reaches a transcript. Passing every
\tcheck is what marks the lesson read."""
\troom, l, rec = _lesson_access(lesson)
\tif isinstance(answers, str):
\t\tanswers = json.loads(answers)
\tchecks = _lesson_checks(lesson)
\tif not checks:
\t\tfrappe.throw(_("This lesson has no checks."))
\tresults, all_ok = [], True
\tfor c in checks:
\t\topts = _check_options(c)
\t\torder = _check_order(c.name, len(opts))
\t\tchosen = answers.get(c.name)
\t\tchosen = cint(chosen) if chosen is not None else -1
\t\treal = opts[order[chosen]][0] if 0 <= chosen < len(order) else -1
\t\tok = real == "ABCD".index(c.correct)
\t\tif not ok:
\t\t\tall_ok = False
\t\tresults.append({"name": c.name, "ok": ok, "rationale": c.rationale or ""})
\tprog = frappe.db.get_value(
\t\t"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson}, "name"
\t)
\tif all_ok and prog:
\t\tfrappe.db.set_value("Duty Lesson Progress", prog, "checks_passed", 1, update_modified=False)
\t\tfrappe.db.commit()
\treturn {"results": results, "passed": all_ok}'''


# --- 2. mark-as-read refuses while checks are outstanding ------------------
CD_OLD = '''\troom, l, rec = _lesson_access(lesson)\n\tprog = frappe.db.get_value(\n\t\t"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson},\n\t\t["name", "seconds", "completed_at"], as_dict=True,\n\t)\n\tif not prog:
\t\tfrappe.throw(_("Open the lesson first."))
\tif not prog.completed_at:'''

CD_NEW = '''\troom, l, rec = _lesson_access(lesson)\n\tprog = frappe.db.get_value(\n\t\t"Duty Lesson Progress", {"user": frappe.session.user, "lesson": lesson},\n\t\t["name", "seconds", "completed_at"], as_dict=True,\n\t)\n\tif not prog:
\t\tfrappe.throw(_("Open the lesson first."))
\tif _lesson_checks(lesson) and not cint(
\t\tfrappe.db.get_value("Duty Lesson Progress", prog.name, "checks_passed")
\t):
\t\tfrappe.throw(_("Answer the check questions at the end of the lesson first."))
\tif not prog.completed_at:'''


# --- 3. portal: the check block -------------------------------------------
P_OLD = '''\t\tconst bb = document.getElementById("lessonbody");
\t\tbb.innerHTML = l.html;'''

P_NEW = '''\t\tconst bb = document.getElementById("lessonbody");
\t\tbb.innerHTML = l.html;
\t\trenderChecks(l, lesson, record);'''

P2_OLD = '''function examPolicyLine(qz) {'''

P2_NEW = '''function renderChecks(l, lesson, record) {
\t/* Formative checks. Never scored, never on a transcript — they exist so a
\t   misreading surfaces here rather than in the exam nine chapters later. */
\tconst host = document.getElementById("ckhost");
\tif (!host) return;
\tconst checks = l.checks || [];
\tif (!checks.length) return;
\tif (l.checks_passed) {
\t\thost.innerHTML = `<div class="ckdone">\\u2713 You answered the check questions for this lesson.</div>`;
\t\treturn;
\t}
\tconst paint = () => {
\t\thost.innerHTML = `
\t\t\t<div class="ckwrap">
\t\t\t\t<div class="ckhead">Before you move on</div>
\t\t\t\t<div class="ckintro">Two or three questions to check the lesson landed. They are not scored and never appear on your record \\u2014 if one is wrong you will be told why and can try again.</div>
\t\t\t\t${checks.map((c, i) => `
\t\t\t\t<div class="ckq" data-c="${esc(c.name)}">
\t\t\t\t\t<div class="ckqt">${i + 1}. ${esc(c.question)}</div>
\t\t\t\t\t${c.options.map((o, j) => `<label class="ckopt"><input type="radio" name="ck_${i}" value="${j}"><span>${esc(o)}</span></label>`).join("")}
\t\t\t\t\t<div class="ckfb"></div>
\t\t\t\t</div>`).join("")}
\t\t\t\t<button id="ckgo">Check my answers</button>
\t\t\t</div>`;
\t\tdocument.getElementById("ckgo").onclick = () => {
\t\t\tconst answers = {};
\t\t\tlet missing = 0;
\t\t\thost.querySelectorAll(".ckq").forEach((el) => {
\t\t\t\tconst picked = el.querySelector("input:checked");
\t\t\t\tif (picked) answers[el.getAttribute("data-c")] = parseInt(picked.value, 10);
\t\t\t\telse missing += 1;
\t\t\t});
\t\t\tif (missing) return alert("Answer every question first.");
\t\t\tdocument.getElementById("ckgo").disabled = true;
\t\t\tapi("client_lesson_check", { lesson: lesson, answers: JSON.stringify(answers) })
\t\t\t\t.then((res) => {
\t\t\t\t\t(res.results || []).forEach((r) => {
\t\t\t\t\t\tconst el = host.querySelector(`[data-c="${r.name}"]`);
\t\t\t\t\t\tif (!el) return;
\t\t\t\t\t\tel.classList.toggle("bad", !r.ok);
\t\t\t\t\t\tel.classList.toggle("good", r.ok);
\t\t\t\t\t\tel.querySelector(".ckfb").innerHTML = r.ok
\t\t\t\t\t\t\t? `\\u2713 Correct.${r.rationale ? " " + esc(r.rationale) : ""}`
\t\t\t\t\t\t\t: `\\u2717 Not quite.${r.rationale ? " " + esc(r.rationale) : " Re-read the section above and try again."}`;
\t\t\t\t\t});
\t\t\t\t\tif (res.passed) {
\t\t\t\t\t\tconst btn = document.getElementById("ckgo");
\t\t\t\t\t\tbtn.remove();
\t\t\t\t\t\tconst lr = document.getElementById("lread");
\t\t\t\t\t\tif (lr) { lr.disabled = false; lr.title = ""; }
\t\t\t\t\t} else {
\t\t\t\t\t\tconst btn = document.getElementById("ckgo");
\t\t\t\t\t\tbtn.disabled = false;
\t\t\t\t\t\tbtn.textContent = "Try again";
\t\t\t\t\t}
\t\t\t\t})
\t\t\t\t.catch((e) => { document.getElementById("ckgo").disabled = false; fail(e); });
\t\t};
\t\tconst lr = document.getElementById("lread");
\t\tif (lr) { lr.disabled = true; lr.title = "Answer the check questions first"; }
\t};
\tpaint();
}
function examPolicyLine(qz) {'''

P3_OLD = '''\t\t\t\t<div id="lessonbody"></div>'''
P3_NEW = '''\t\t\t\t<div id="lessonbody"></div>
\t\t\t\t<div id="ckhost"></div>'''

CSS_OLD = '''\t/* ---- proctored assessment ---- */'''

CSS_NEW = '''\t/* ---- end-of-lesson checks ---- */
\t.ckwrap { margin-top: 30px; border-top: 2px solid var(--brand-50); padding-top: 20px; }
\t.ckhead { font-family: Fraunces, Georgia, serif; font-size: 19px; font-weight: 600; margin-bottom: 4px; }
\t.ckintro { font-size: 12.5px; color: #6B7C77; line-height: 1.6; margin-bottom: 16px; }
\t.ckq { padding: 13px 15px; border: 1px solid #E4EAE8; border-radius: 12px; margin-bottom: 11px; background: #fff; }
\t.ckq.good { border-color: #B7DFD6; background: #F6FBF9; }
\t.ckq.bad { border-color: #F0C7BC; background: #FEF8F6; }
\t.ckqt { font-size: 14.5px; font-weight: 700; line-height: 1.45; margin-bottom: 9px; }
\t.ckopt { display: flex; gap: 9px; align-items: flex-start; padding: 5px 2px; cursor: pointer;
\t\tfont-size: 14px; line-height: 1.45; margin: 0; font-weight: 400; }
\t.ckopt input { margin-top: 3px; }
\t.ckfb { font-size: 12.5px; line-height: 1.6; margin-top: 8px; }
\t.ckq.good .ckfb { color: #0C4A43; }
\t.ckq.bad .ckfb { color: #9A3412; }
\t.ckq .ckfb:empty { display: none; }
\t.ckdone { margin-top: 26px; font-size: 13px; color: var(--brand-700); background: var(--brand-50);
\t\tborder: 1px solid #CBE7DE; border-radius: 10px; padding: 10px 14px; }

\t/* ---- proctored assessment ---- */'''


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = json.load(f)
    added = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        added = True
    if added:
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_lesson_check(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.209.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.209.0.")

    edits = [
        (CR, CL_OLD, CL_NEW, "client_lesson serves checks"),
        (CR, CD_OLD, CD_NEW, "lesson_done requires checks"),
        (PORTAL, P_OLD, P_NEW, "renderChecks call"),
        (PORTAL, P2_OLD, P2_NEW, "renderChecks"),
        (PORTAL, P3_OLD, P3_NEW, "check host div"),
        (PORTAL, CSS_OLD, CSS_NEW, "check css"),
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

    d = os.path.join(root, DT_DIR, "duty_lesson_check")
    if not os.path.isdir(d):
        os.makedirs(d)
    for fname, body in (
        ("__init__.py", ""),
        ("duty_lesson_check.json", json.dumps(CHECK_JSON, indent=1) + "\n"),
        ("duty_lesson_check.py", CTRL),
    ):
        p = os.path.join(d, fname)
        if not os.path.exists(p):
            with io.open(p, "w", encoding="utf-8") as f:
                f.write(body)
    print("  doctype: Duty Lesson Check")

    add_fields(os.path.join(root, LPDT), [
        {"fieldname": "checks_passed", "fieldtype": "Check", "label": "Checks Passed"},
    ])
    print("  Duty Lesson Progress: +checks_passed")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: check serving + grading + read gate")
    print("  portal.html: check block, feedback, css")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.209.0"', '"3.210.0"'))
    print("wrote __init__.py -> 3.210.0")


if __name__ == "__main__":
    main()
