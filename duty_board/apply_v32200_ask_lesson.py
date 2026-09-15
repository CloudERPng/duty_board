#!/usr/bin/env python3
"""Duty Board v3.220.0 - SOMEWHERE TO PUT THE QUESTION.

Flagged when we moved to self-serve and then left out of the functional
review. With a facilitator, a learner who does not understand something asks.
Without one they stall, and stalling is silent - it surfaces months later as a
cohort that never finished, with nothing on record explaining why.

The reading room now carries "Something unclear? Ask our team about this
lesson". The question is posted into the client's room through
client_post_message, so it reaches staff by exactly the same path as any other
client message and needs no separate inbox to be watched.

It is deliberately posted in the open rather than sent privately. Colleagues
see the question and the answer, which means the second person with the same
confusion finds it already answered - and the panel says so plainly rather than
letting anyone assume it is private.

  Duty Lesson: +question_count. A chapter that keeps generating questions is
  usually a chapter that is badly written rather than a subject that is hard,
  and that is worth knowing when the material is reviewed.

Deploy: apply -> bench migrate (one field) -> bench build --app duty_board ->
clear-cache + clear-website-cache -> restart. Anchored, idempotent.
Requires v3.219.1.
"""

import io
import json as _json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
LSDT = "duty_board/duty_board/doctype/duty_lesson/duty_lesson.json"
CHECK_ONLY = "--check" in sys.argv


RD_OLD = '\t\t\t\t<div class="rdfoot">\n\t\t\t\t\t<span class="rddots">${c.lessons.map((x, k) => `<i class="${x.done ? "on" : ""}${k === idx ? " cur" : ""}"></i>`).join("")}</span>\n\t\t\t\t\t${l.done\n\t\t\t\t\t\t? `<span class="acaddone">✓ Read</span>${next ? `<button onclick="openLesson(\'${esc(next.name)}\',\'${esc(record)}\')">Next lesson →</button>` : ""}`\n\t\t\t\t\t\t: `<button id="lread" onclick="markRead(\'${esc(lesson)}\',\'${esc(record)}\')">✓ Mark as read${next ? " · next →" : ""}</button>`}\n\t\t\t\t\t<button class="rdghost" onclick="openCourse(\'${esc(record)}\')">← All lessons</button>\n\t\t\t\t</div>\n\t\t\t</div>`;'

RD_NEW = '\t\t\t\t<div class="rdfoot">\n\t\t\t\t\t<span class="rddots">${c.lessons.map((x, k) => `<i class="${x.done ? "on" : ""}${k === idx ? " cur" : ""}"></i>`).join("")}</span>\n\t\t\t\t\t${l.done\n\t\t\t\t\t\t? `<span class="acaddone">✓ Read</span>${next ? `<button onclick="openLesson(\'${esc(next.name)}\',\'${esc(record)}\')">Next lesson →</button>` : ""}`\n\t\t\t\t\t\t: `<button id="lread" onclick="markRead(\'${esc(lesson)}\',\'${esc(record)}\')">✓ Mark as read${next ? " · next →" : ""}</button>`}\n\t\t\t\t\t<button class="rdghost" onclick="openCourse(\'${esc(record)}\')">← All lessons</button>\n\t\t\t\t</div>\n\t\t\t\t<div class="rdask"><a class="rdasklink" onclick="askLesson(\'${esc(lesson)}\')">Something unclear? Ask our team about this lesson</a></div>\n\t\t\t\t<div id="rdaskbox"></div>\n\t\t\t</div>`;'

JS_OLD = 'function renderChecks(l, lesson, record) {'

JS_NEW = 'function askLesson(lesson) {\n\t/* With no facilitator, a learner who does not understand something has\n\t   nowhere to put the question, so they stall and quietly stop. This gives\n\t   it somewhere to go — and tells us which chapters keep generating it. */\n\tconst box = document.getElementById("rdaskbox");\n\tif (!box) return;\n\tif (box.innerHTML) { box.innerHTML = ""; return; }\n\tbox.innerHTML = `\n\t\t<div class="askwrap">\n\t\t\t<label>What would you like to ask?</label>\n\t\t\t<textarea id="askq" rows="3" placeholder="Describe what is unclear \\u2014 quoting the part that confused you helps us answer properly."></textarea>\n\t\t\t<div class="askacts">\n\t\t\t\t<button id="asksend">Send question</button>\n\t\t\t\t<button class="rdghost" onclick="askLesson()">Cancel</button>\n\t\t\t</div>\n\t\t\t<p class="askfoot">Your question is posted in your organisation\'s room, so your colleagues and our team can both see it and the answer.</p>\n\t\t</div>`;\n\tdocument.getElementById("askq").focus();\n\tdocument.getElementById("asksend").onclick = () => {\n\t\tconst q = document.getElementById("askq").value.trim();\n\t\tif (q.length < 5) return alert("Tell us a little more so we can answer properly.");\n\t\tdocument.getElementById("asksend").disabled = true;\n\t\tapi("client_lesson_ask", { lesson: lesson, question: q })\n\t\t\t.then(() => {\n\t\t\t\tbox.innerHTML = `<div class="askwrap ok">\\u2713 Sent. Our team will reply in your room \\u2014 carry on reading in the meantime.</div>`;\n\t\t\t})\n\t\t\t.catch((e) => { document.getElementById("asksend").disabled = false; fail(e); });\n\t};\n}\nfunction renderChecks(l, lesson, record) {'

CSS_OLD = '\t/* ---- end-of-lesson checks ---- */'

CSS_NEW = '\t.rdask { margin-top: 14px; }\n\t.rdasklink { font-size: 13px; color: var(--brand-700); font-weight: 600; cursor: pointer; }\n\t.askwrap { margin-top: 12px; border: 1px solid #E4EAE8; border-radius: 12px; padding: 14px 16px; background: #fff; }\n\t.askwrap.ok { background: var(--brand-50); border-color: #CBE7DE; color: #0C4A43; font-size: 13.5px; }\n\t.askwrap label { display: block; font-weight: 700; font-size: 13px; margin-bottom: 6px; }\n\t.askwrap textarea { width: 100%; padding: 10px 12px; border: 1px solid #DCE4E1; border-radius: 9px;\n\t\tfont-size: 14.5px; font-family: inherit; line-height: 1.5; }\n\t.askacts { display: flex; gap: 10px; margin-top: 10px; }\n\t.askfoot { font-size: 11.5px; color: #6B7C77; margin: 9px 0 0; line-height: 1.5; }\n\n\t/* ---- end-of-lesson checks ---- */'

PY_OLD = '@frappe.whitelist()\ndef client_lesson_check(lesson, answers):'

PY_NEW = '@frappe.whitelist()\ndef client_lesson_ask(lesson, question):\n\t"""A learner\'s question about a chapter, posted into their room.\n\n\tSelf-serve removed the facilitator, and with it the person a confused\n\tlearner would have asked. Without somewhere to put the question they stall\n\tand quietly stop — which shows up much later as a cohort that never\n\tfinished, with no record of why.\n\n\tRouted through client_post_message so it reaches staff by the same path as\n\tany other client message. The counter on the lesson is the editorial\n\tby-product: a chapter that keeps generating questions is usually a chapter\n\tthat is badly written rather than a subject that is hard."""\n\troom, l, rec = _lesson_access(lesson)\n\tquestion = (question or "").strip()\n\tif len(question) < 5:\n\t\tfrappe.throw(_("Tell us a little more so we can answer properly."))\n\tmod_title = frappe.db.get_value("Duty Training Module", l.module, "title") or ""\n\ttext = _("\\u2753 **Question about {0} \\u2014 {1}**\\n\\n{2}").format(\n\t\tmod_title, l.title, question[:2000]\n\t)\n\ttry:\n\t\tfrappe.db.set_value(\n\t\t\t"Duty Lesson", lesson, "question_count",\n\t\t\tcint(frappe.db.get_value("Duty Lesson", lesson, "question_count")) + 1,\n\t\t\tupdate_modified=False,\n\t\t)\n\texcept Exception:\n\t\tpass\n\tclient_post_message(text)\n\treturn {"ok": 1}\n\n\n@frappe.whitelist()\ndef client_lesson_check(lesson, answers):'



def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = _json.load(f)
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
            _json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_lesson_ask(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.219.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.219.1.")

    edits = [
        (CR, PY_OLD, PY_NEW, "client_lesson_ask"),
        (PORTAL, RD_OLD, RD_NEW, "ask link in the reader"),
        (PORTAL, JS_OLD, JS_NEW, "askLesson"),
        (PORTAL, CSS_OLD, CSS_NEW, "ask css"),
    ]
    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, LSDT), [
        {"fieldname": "question_count", "fieldtype": "Int",
         "label": "Questions Asked", "read_only": 1},
    ])
    print("  Duty Lesson: +question_count")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: client_lesson_ask")
    print("  portal.html: ask panel in the reading room")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.219.1"', '"3.220.0"'))
    print("wrote __init__.py -> 3.220.0")


if __name__ == "__main__":
    main()
