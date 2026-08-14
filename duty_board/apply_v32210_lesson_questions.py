#!/usr/bin/env python3
"""Duty Board v3.221.0 - LESSON QUESTIONS, KEPT WITH THE LESSON.

v3.220.0 posted a learner's question into the client room. That was the wrong
home and the correction came from Olamide within the hour: the room carries
invoices, tickets and project traffic, so a training question is buried within
a day, the learner cannot see it beside the material that confused them, and
the answer never reaches the next person with the same confusion.

A question now belongs to the chapter that caused it.

  Duty Lesson Question (new): lesson, module, room, asker, question, status,
    answer, answerer, and a published flag.

  Learner  - "Questions on this lesson" sits under every chapter. Their own
             threads always show, with the answer underneath once it arrives.
  Staff    - a Lesson questions queue on the rail, oldest first, answered
             inline. Designated tutors are notified when one arrives; set them
             in Duty Settings > Academy Tutors, falling back to the academy
             approver so a fresh install has somebody rather than nobody.
  Learner  - in-app notification AND an email carrying their question, the
             answer and who wrote it.

  Published answers are the addition to the brief, and the reason to bother:
  a published thread appears for everyone reading that chapter, so the second
  person does not have to ask, and over a cohort the chapter accumulates the
  FAQ its readers actually needed. Publish is ticked by default and can be
  cleared for anything specific to one learner.

  Duty Settings: +academy_tutors.

Deploy: apply -> bench migrate -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. Anchored, idempotent. Requires v3.220.0.
"""

import io
import json as _json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
ACAD = "duty_board/academy.py"
PORTAL = "duty_board/www/portal.html"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
DSDT = "duty_board/duty_board/doctype/duty_settings/duty_settings.json"
DT_DIR = "duty_board/duty_board/doctype"
CHECK_ONLY = "--check" in sys.argv

CTRL = """# Copyright (c) 2026, Xlevel Retail Systems Ltd
import frappe
from frappe.model.document import Document


class DutyLessonQuestion(Document):
\tpass
"""

QDT = {'actions': [], 'autoname': 'hash', 'creation': '2026-08-14 09:00:00.000000', 'doctype': 'DocType', 'engine': 'InnoDB', 'field_order': ['lesson', 'lesson_title', 'module', 'module_title', 'room', 'asked_by', 'asked_on', 'question', 'status', 'answer', 'answered_by', 'answered_on', 'published'], 'fields': [{'fieldname': 'lesson', 'fieldtype': 'Link', 'label': 'Lesson', 'options': 'Duty Lesson', 'reqd': 1}, {'fieldname': 'lesson_title', 'fieldtype': 'Data', 'label': 'Lesson Title', 'in_list_view': 1}, {'fieldname': 'module', 'fieldtype': 'Link', 'label': 'Module', 'options': 'Duty Training Module'}, {'fieldname': 'module_title', 'fieldtype': 'Data', 'label': 'Module Title'}, {'fieldname': 'room', 'fieldtype': 'Link', 'label': 'Client Room', 'options': 'Client Room', 'in_list_view': 1}, {'fieldname': 'asked_by', 'fieldtype': 'Data', 'label': 'Asked By', 'in_list_view': 1}, {'fieldname': 'asked_on', 'fieldtype': 'Datetime', 'label': 'Asked On'}, {'fieldname': 'question', 'fieldtype': 'Text', 'label': 'Question', 'reqd': 1}, {'fieldname': 'status', 'fieldtype': 'Select', 'label': 'Status', 'options': 'Open\nAnswered', 'default': 'Open', 'in_list_view': 1}, {'fieldname': 'answer', 'fieldtype': 'Text', 'label': 'Answer'}, {'fieldname': 'answered_by', 'fieldtype': 'Data', 'label': 'Answered By'}, {'fieldname': 'answered_on', 'fieldtype': 'Datetime', 'label': 'Answered On'}, {'fieldname': 'published', 'fieldtype': 'Check', 'label': 'Published On Lesson'}], 'index_web_pages_for_search': 1, 'links': [], 'modified': '2026-08-14 09:00:00.000000', 'modified_by': 'Administrator', 'module': 'Duty Board', 'name': 'Duty Lesson Question', 'owner': 'Administrator', 'permissions': [{'create': 1, 'delete': 1, 'email': 1, 'export': 1, 'print': 1, 'read': 1, 'report': 1, 'role': 'System Manager', 'share': 1, 'write': 1}], 'sort_field': 'modified', 'sort_order': 'DESC', 'states': [], 'title_field': 'lesson_title'}

ASK_OLD = '@frappe.whitelist()\ndef client_lesson_ask(lesson, question):\n\t"""A learner\'s question about a chapter, posted into their room.\n\n\tSelf-serve removed the facilitator, and with it the person a confused\n\tlearner would have asked. Without somewhere to put the question they stall\n\tand quietly stop — which shows up much later as a cohort that never\n\tfinished, with no record of why.\n\n\tRouted through client_post_message so it reaches staff by the same path as\n\tany other client message. The counter on the lesson is the editorial\n\tby-product: a chapter that keeps generating questions is usually a chapter\n\tthat is badly written rather than a subject that is hard."""\n\troom, l, rec = _lesson_access(lesson)\n\tquestion = (question or "").strip()\n\tif len(question) < 5:\n\t\tfrappe.throw(_("Tell us a little more so we can answer properly."))\n\tmod_title = frappe.db.get_value("Duty Training Module", l.module, "title") or ""\n\ttext = _("\\u2753 **Question about {0} \\u2014 {1}**\\n\\n{2}").format(\n\t\tmod_title, l.title, question[:2000]\n\t)\n\ttry:\n\t\tfrappe.db.set_value(\n\t\t\t"Duty Lesson", lesson, "question_count",\n\t\t\tcint(frappe.db.get_value("Duty Lesson", lesson, "question_count")) + 1,\n\t\t\tupdate_modified=False,\n\t\t)\n\texcept Exception:\n\t\tpass\n\tclient_post_message(text)\n\treturn {"ok": 1}\n\n\n'

ASK_NEW = '@frappe.whitelist()\ndef client_lesson_ask(lesson, question):\n\t"""A learner\'s question, kept with the chapter it is about.\n\n\tv3.220.0 posted these into the room. That was wrong: the room carries\n\tinvoices, tickets and project traffic, so a training question is buried\n\twithin a day and the answer never reaches the next person with the same\n\tconfusion. A question belongs to the chapter that caused it."""\n\troom, l, rec = _lesson_access(lesson)\n\tquestion = (question or "").strip()\n\tif len(question) < 5:\n\t\tfrappe.throw(_("Tell us a little more so we can answer properly."))\n\tmod_title = frappe.db.get_value("Duty Training Module", l.module, "title") or ""\n\tdoc = frappe.get_doc({\n\t\t"doctype": "Duty Lesson Question",\n\t\t"lesson": lesson, "lesson_title": l.title,\n\t\t"module": l.module, "module_title": mod_title,\n\t\t"room": room.name, "asked_by": frappe.session.user,\n\t\t"asked_on": now_datetime(), "question": question[:4000],\n\t\t"status": "Open",\n\t}).insert(ignore_permissions=True)\n\ttry:\n\t\tfrappe.db.set_value(\n\t\t\t"Duty Lesson", lesson, "question_count",\n\t\t\tcint(frappe.db.get_value("Duty Lesson", lesson, "question_count")) + 1,\n\t\t\tupdate_modified=False,\n\t\t)\n\texcept Exception:\n\t\tpass\n\tfrappe.db.commit()\n\t_notify_tutors(doc, room)\n\treturn client_lesson_questions(lesson)\n\n\ndef _tutors():\n\t"""Who answers. Falls back to the academy approver so a fresh install has\n\tsomebody rather than nobody."""\n\ts = frappe.get_cached_doc("Duty Settings")\n\traw = (s.get("academy_tutors") or "").strip()\n\tif not raw:\n\t\traw = (s.get("academy_approver") or s.get("cr_pricer") or "").strip()\n\treturn [e.strip() for e in re.split(r"[,;\\s]+", raw) if e.strip()]\n\n\ndef _notify_tutors(doc, room):\n\ttry:\n\t\tfrom duty_board.api import _notify_user\n\n\t\twho = frappe.utils.get_fullname(doc.asked_by)\n\t\tfor t in _tutors():\n\t\t\t_notify_user(\n\t\t\t\tt,\n\t\t\t\t_("\\u2753 Lesson question \\u00b7 {0}").format(room.customer or room.name),\n\t\t\t\t_("{0} asked about {1}").format(who, doc.lesson_title),\n\t\t\t)\n\texcept Exception:\n\t\tfrappe.log_error(frappe.get_traceback(), "duty_board lesson question notify")\n\n\n@frappe.whitelist()\ndef client_lesson_questions(lesson):\n\t"""This learner\'s own threads, plus anything published to the chapter.\n\n\tPublished answers are the point: the second person with the same confusion\n\tfinds it already answered, and over a cohort the chapter accumulates the\n\tFAQ its readers actually needed."""\n\troom, _l, _rec = _lesson_access(lesson)\n\tme = frappe.session.user\n\trows = frappe.get_all(\n\t\t"Duty Lesson Question",\n\t\tfilters={"lesson": lesson},\n\t\tfields=["name", "asked_by", "asked_on", "question", "status", "answer",\n\t\t\t\t"answered_by", "answered_on", "published", "room"],\n\t\torder_by="asked_on asc",\n\t)\n\tout = []\n\tfor r in rows:\n\t\tmine = r.asked_by == me\n\t\tif not mine and not (cint(r.published) and r.answer):\n\t\t\tcontinue\n\t\tout.append({\n\t\t\t"name": r.name,\n\t\t\t"mine": mine,\n\t\t\t"who": frappe.utils.get_fullname(r.asked_by) if not mine else _("You"),\n\t\t\t"asked_on": str(r.asked_on)[:16] if r.asked_on else None,\n\t\t\t"question": r.question,\n\t\t\t"status": r.status,\n\t\t\t"answer": r.answer,\n\t\t\t"answered_by": frappe.utils.get_fullname(r.answered_by) if r.answered_by else None,\n\t\t\t"answered_on": str(r.answered_on)[:16] if r.answered_on else None,\n\t\t\t"published": cint(r.published),\n\t\t})\n\treturn out\n\n'

JS_OLD = 'function askLesson(lesson) {\n\t/* With no facilitator, a learner who does not understand something has\n\t   nowhere to put the question, so they stall and quietly stop. This gives\n\t   it somewhere to go — and tells us which chapters keep generating it. */\n\tconst box = document.getElementById("rdaskbox");\n\tif (!box) return;\n\tif (box.innerHTML) { box.innerHTML = ""; return; }\n\tbox.innerHTML = `\n\t\t<div class="askwrap">\n\t\t\t<label>What would you like to ask?</label>\n\t\t\t<textarea id="askq" rows="3" placeholder="Describe what is unclear \\u2014 quoting the part that confused you helps us answer properly."></textarea>\n\t\t\t<div class="askacts">\n\t\t\t\t<button id="asksend">Send question</button>\n\t\t\t\t<button class="rdghost" onclick="askLesson()">Cancel</button>\n\t\t\t</div>\n\t\t\t<p class="askfoot">Your question is posted in your organisation\'s room, so your colleagues and our team can both see it and the answer.</p>\n\t\t</div>`;\n\tdocument.getElementById("askq").focus();\n\tdocument.getElementById("asksend").onclick = () => {\n\t\tconst q = document.getElementById("askq").value.trim();\n\t\tif (q.length < 5) return alert("Tell us a little more so we can answer properly.");\n\t\tdocument.getElementById("asksend").disabled = true;\n\t\tapi("client_lesson_ask", { lesson: lesson, question: q })\n\t\t\t.then(() => {\n\t\t\t\tbox.innerHTML = `<div class="askwrap ok">\\u2713 Sent. Our team will reply in your room \\u2014 carry on reading in the meantime.</div>`;\n\t\t\t})\n\t\t\t.catch((e) => { document.getElementById("asksend").disabled = false; fail(e); });\n\t};\n}\n'

JS_NEW = 'function renderAsk(lesson) {\n\tconst host = document.getElementById("rdaskbox");\n\tif (!host) return;\n\tapi("client_lesson_questions", { lesson: lesson })\n\t\t.then((rows) => paintAsk(lesson, rows || []))\n\t\t.catch(() => paintAsk(lesson, []));\n}\nfunction paintAsk(lesson, rows) {\n\tconst host = document.getElementById("rdaskbox");\n\tif (!host) return;\n\twindow._askrows = rows;\n\tconst thread = (q) => `\n\t\t<div class="qacard${q.mine ? " mine" : ""}">\n\t\t\t<div class="qahead">${esc(q.who)}${q.asked_on ? ` <span class="qadt">${esc(q.asked_on)}</span>` : ""}${!q.mine && q.published ? `<span class="qatag">Answered for everyone</span>` : ""}</div>\n\t\t\t<div class="qaq">${esc(q.question)}</div>\n\t\t\t${q.answer\n\t\t\t\t? `<div class="qaa"><b>${esc(q.answered_by || "Our team")}</b>${q.answered_on ? ` <span class="qadt">${esc(q.answered_on)}</span>` : ""}<p>${esc(q.answer)}</p></div>`\n\t\t\t\t: q.mine ? `<div class="qawait">Waiting for an answer \\u2014 we will email you when it arrives.</div>` : ""}\n\t\t</div>`;\n\thost.innerHTML = `\n\t\t${rows.length ? `<div class="qawrap">${rows.map(thread).join("")}</div>` : ""}\n\t\t<div id="qaform"></div>`;\n}\nfunction askLesson(lesson) {\n\t/* With no facilitator, a learner who does not understand something has\n\t   nowhere to put the question, so they stall and quietly stop. The thread\n\t   lives with the chapter, where the confusion happened. */\n\tconst box = document.getElementById("qaform");\n\tif (!box) return;\n\tif (box.innerHTML) { box.innerHTML = ""; return; }\n\tbox.innerHTML = `\n\t\t<div class="askwrap">\n\t\t\t<label>What would you like to ask?</label>\n\t\t\t<textarea id="askq" rows="3" placeholder="Describe what is unclear \\u2014 quoting the part that confused you helps us answer properly."></textarea>\n\t\t\t<div class="askacts">\n\t\t\t\t<button id="asksend">Send question</button>\n\t\t\t\t<button class="rdghost" onclick="askLesson(\'${esc(lesson)}\')">Cancel</button>\n\t\t\t</div>\n\t\t\t<p class="askfoot">Your question stays with this lesson. We will answer here and email you when we do.</p>\n\t\t</div>`;\n\tdocument.getElementById("askq").focus();\n\tdocument.getElementById("asksend").onclick = () => {\n\t\tconst q = document.getElementById("askq").value.trim();\n\t\tif (q.length < 5) return alert("Tell us a little more so we can answer properly.");\n\t\tdocument.getElementById("asksend").disabled = true;\n\t\tapi("client_lesson_ask", { lesson: lesson, question: q })\n\t\t\t.then((rows) => paintAsk(lesson, rows || []))\n\t\t\t.catch((e) => { document.getElementById("asksend").disabled = false; fail(e); });\n\t};\n}\n'

RD_OLD = '\t\t\t\t<div class="rdask"><a class="rdasklink" onclick="askLesson(\'${esc(lesson)}\')">Something unclear? Ask our team about this lesson</a></div>\n\t\t\t\t<div id="rdaskbox"></div>'

RD_NEW = '\t\t\t\t<div class="rdask"><b>Questions on this lesson</b><a class="rdasklink" onclick="askLesson(\'${esc(lesson)}\')">Ask a question</a></div>\n\t\t\t\t<div id="rdaskbox"></div>'

CALL_OLD = '\t\trenderChecks(l, lesson, record);'

CALL_NEW = '\t\trenderChecks(l, lesson, record);\n\t\trenderAsk(lesson);'

CSS_OLD = '\t.rdask { margin-top: 14px; }'

CSS_NEW = '\t.rdask { margin-top: 26px; padding-top: 16px; border-top: 1px solid #EEF2F0;\n\t\tdisplay: flex; align-items: baseline; gap: 14px; }\n\t.rdask b { font-size: 15px; }\n\t.qawrap { margin-top: 12px; }\n\t.qacard { border: 1px solid #E4EAE8; border-radius: 12px; padding: 13px 15px; margin-bottom: 10px; background: #fff; }\n\t.qacard.mine { border-color: #CBE7DE; background: #FAFDFC; }\n\t.qahead { font-size: 12.5px; font-weight: 700; color: #33423E; margin-bottom: 5px; }\n\t.qadt { font-weight: 400; color: #6B7C77; }\n\t.qatag { float: right; font-size: 10.5px; font-weight: 700; text-transform: uppercase;\n\t\tletter-spacing: .8px; color: var(--brand-700); background: var(--brand-50);\n\t\tborder-radius: 99px; padding: 2px 9px; }\n\t.qaq { font-size: 14.5px; line-height: 1.55; }\n\t.qaa { margin-top: 10px; padding-top: 10px; border-top: 1px solid #F0F4F2; font-size: 12.5px; color: #33423E; }\n\t.qaa p { margin: 5px 0 0; font-size: 14.5px; line-height: 1.6; }\n\t.qawait { margin-top: 8px; font-size: 12.5px; color: #8A5A0B; }'

STAFF_OLD = '# ---------------- academy health: the cross-room view ----------------'

STAFF_NEW = '# ---------------- lesson questions: the tutor queue ----------------\n\n\n@frappe.whitelist()\ndef questions(status="Open"):\n\t"""The queue of learner questions, oldest first — because the person who\n\thas waited longest is the one most likely to have given up."""\n\t_staff_only()\n\tfilters = {} if status == "All" else {"status": status or "Open"}\n\trows = frappe.get_all(\n\t\t"Duty Lesson Question", filters=filters,\n\t\tfields=["name", "room", "module_title", "lesson_title", "lesson", "asked_by",\n\t\t\t\t"asked_on", "question", "status", "answer", "answered_by", "published"],\n\t\torder_by="asked_on asc", limit_page_length=100,\n\t)\n\tfor r in rows:\n\t\tr["customer"] = frappe.db.get_value("Client Room", r.room, "customer") or r.room\n\t\tr["who"] = frappe.utils.get_fullname(r.asked_by)\n\t\tr["waiting_days"] = (\n\t\t\t(getdate(today()) - getdate(r.asked_on)).days if r.asked_on else 0\n\t\t)\n\treturn rows\n\n\n@frappe.whitelist()\ndef question_counts():\n\t_staff_only()\n\treturn {"open": frappe.db.count("Duty Lesson Question", {"status": "Open"})}\n\n\n@frappe.whitelist()\ndef answer_question(name, answer, publish=0):\n\t"""Answer, notify in-app, email the learner, and optionally publish the\n\tthread to the chapter so nobody else has to ask it."""\n\t_staff_only()\n\tanswer = (answer or "").strip()\n\tif len(answer) < 5:\n\t\tfrappe.throw(_("Write an answer first."))\n\tq = frappe.get_doc("Duty Lesson Question", name)\n\tq.db_set({\n\t\t"answer": answer[:4000], "status": "Answered",\n\t\t"answered_by": frappe.session.user, "answered_on": now_datetime(),\n\t\t"published": 1 if cint(publish) else 0,\n\t}, update_modified=False)\n\tfrappe.db.commit()\n\ttry:\n\t\tfrom duty_board.api import _notify_user\n\n\t\t_notify_user(\n\t\t\tq.asked_by, _("\\u2705 Your question has been answered"),\n\t\t\t_("{0} \\u00b7 {1}").format(q.module_title or "", q.lesson_title or ""),\n\t\t)\n\texcept Exception:\n\t\tpass\n\ttry:\n\t\tfrappe.sendmail(\n\t\t\trecipients=[q.asked_by],\n\t\t\tsubject=_("Answered: your question on {0}").format(q.lesson_title or ""),\n\t\t\tmessage="""<p>Hello,</p>\n<p>You asked about <b>{lesson}</b> in {module}:</p>\n<blockquote style="border-left:3px solid #DCE4E1;margin:0 0 14px;padding:2px 0 2px 14px;color:#4A5A55">{question}</blockquote>\n<p><b>{who} replied:</b></p>\n<div style="background:#F4F7F6;border-radius:10px;padding:14px 16px;line-height:1.6">{answer}</div>\n<p style="margin-top:16px">The answer is also on the lesson itself, under\n<i>Questions on this lesson</i>, so you can read it alongside the material.</p>\n<p>&mdash; CloudERP.One Academy</p>""".format(\n\t\t\t\tlesson=frappe.utils.escape_html(q.lesson_title or ""),\n\t\t\t\tmodule=frappe.utils.escape_html(q.module_title or ""),\n\t\t\t\tquestion=frappe.utils.escape_html((q.question or "")[:600]),\n\t\t\t\twho=frappe.utils.escape_html(frappe.utils.get_fullname(frappe.session.user)),\n\t\t\t\tanswer=frappe.utils.escape_html(answer).replace("\\n", "<br>"),\n\t\t\t),\n\t\t)\n\texcept Exception:\n\t\tfrappe.log_error(frappe.get_traceback(), "duty_board answer email")\n\treturn {"ok": 1}\n\n\n# ---------------- academy health: the cross-room view ----------------'

JSD_OLD = '\tacademy_health_css() {'

JSD_NEW = '\tlesson_questions_dialog() {\n\t\tconst esc = frappe.utils.escape_html;\n\t\tconst d = new frappe.ui.Dialog({ title: `\\u2753 ${__("Lesson questions")}`, size: "extra-large" });\n\t\tlet status = "Open";\n\t\tconst load = () =>\n\t\t\tfrappe.call({\n\t\t\t\tmethod: "duty_board.academy.questions", args: { status: status },\n\t\t\t\tcallback: (r) => {\n\t\t\t\t\tconst rows = r.message || [];\n\t\t\t\t\t$(d.body).html(`\n\t\t\t\t\t\t<div style="margin-bottom:10px">\n\t\t\t\t\t\t\t<button class="btn btn-xs ${status === "Open" ? "btn-primary" : "btn-default"} duty-q-f" data-s="Open">${__("Open")}</button>\n\t\t\t\t\t\t\t<button class="btn btn-xs ${status === "Answered" ? "btn-primary" : "btn-default"} duty-q-f" data-s="Answered">${__("Answered")}</button>\n\t\t\t\t\t\t\t<button class="btn btn-xs ${status === "All" ? "btn-primary" : "btn-default"} duty-q-f" data-s="All">${__("All")}</button>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t\t${rows.length ? rows.map((q) => `\n\t\t\t\t\t\t<div class="duty-q-card" data-n="${esc(q.name)}">\n\t\t\t\t\t\t\t<div class="duty-q-meta"><b>${esc(q.who)}</b> \\u00b7 ${esc(q.customer)} \\u00b7 ${esc(q.module_title || "")} \\u2014 ${esc(q.lesson_title || "")}\n\t\t\t\t\t\t\t\t${q.status === "Open" && q.waiting_days > 1 ? `<span class="duty-q-old">${q.waiting_days} ${__("days waiting")}</span>` : ""}</div>\n\t\t\t\t\t\t\t<div class="duty-q-q">${esc(q.question)}</div>\n\t\t\t\t\t\t\t${q.answer ? `<div class="duty-q-a"><b>${esc(q.answered_by || "")}</b>${q.published ? ` <span class="duty-q-pub">${__("published")}</span>` : ""}<div>${esc(q.answer)}</div></div>` : ""}\n\t\t\t\t\t\t\t${q.status === "Open" ? `\n\t\t\t\t\t\t\t\t<textarea class="form-control duty-q-in" rows="3" placeholder="${__("Write the answer the learner will read")}"></textarea>\n\t\t\t\t\t\t\t\t<label class="duty-q-pubchk"><input type="checkbox" class="duty-q-pubbox" checked> ${__("Publish on the lesson so others do not have to ask")}</label>\n\t\t\t\t\t\t\t\t<button class="btn btn-sm btn-primary duty-q-send">${__("Send answer")}</button>` : ""}\n\t\t\t\t\t\t</div>`).join("")\n\t\t\t\t\t\t\t: `<div class="text-muted">${__("Nothing here.")}</div>`}`);\n\t\t\t\t\t$(d.body).find(".duty-q-f").on("click", (e) => { status = $(e.currentTarget).data("s"); load(); });\n\t\t\t\t\t$(d.body).find(".duty-q-send").on("click", (e) => {\n\t\t\t\t\t\tconst $c = $(e.currentTarget).closest(".duty-q-card");\n\t\t\t\t\t\tconst txt = $c.find(".duty-q-in").val();\n\t\t\t\t\t\tif (!txt || txt.trim().length < 5) { frappe.msgprint(__("Write an answer first.")); return; }\n\t\t\t\t\t\t$(e.currentTarget).prop("disabled", true);\n\t\t\t\t\t\tfrappe.call({\n\t\t\t\t\t\t\tmethod: "duty_board.academy.answer_question",\n\t\t\t\t\t\t\targs: { name: $c.data("n"), answer: txt, publish: $c.find(".duty-q-pubbox").is(":checked") ? 1 : 0 },\n\t\t\t\t\t\t\tcallback: () => { frappe.show_alert({ message: __("Answer sent"), indicator: "green" }); load(); },\n\t\t\t\t\t\t});\n\t\t\t\t\t});\n\t\t\t\t},\n\t\t\t});\n\t\tload();\n\t\td.show();\n\t}\n\n\tacademy_health_css() {'

RAIL_OLD = '\t\t\tboard.rail.push({ id: "academyhealth", ic: board._rsvg.pulse, label: __("Academy health"), go: () => board.academy_health_dialog() });'

RAIL_NEW = '\t\t\tboard.rail.push({ id: "academyhealth", ic: board._rsvg.pulse, label: __("Academy health"), go: () => board.academy_health_dialog() });\n\t\t\tboard.rail.push({ id: "lessonq", ic: board._rsvg.ask, label: __("Lesson questions"), go: () => board.lesson_questions_dialog() });'

ICON_OLD = '\t\tpulse: \'<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>\','

ICON_NEW = '\t\tpulse: \'<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>\',\n\t\task: \'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>\','

QCSS_OLD = '\t\t\t.duty-ah-go { cursor: pointer; font-weight: 600; }`;'

QCSS_NEW = '\t\t\t.duty-ah-go { cursor: pointer; font-weight: 600; }\n\t\t\t.duty-q-card { border: 1px solid #E4EAE8; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }\n\t\t\t.duty-q-meta { font-size: 12px; color: #6B7C77; margin-bottom: 6px; }\n\t\t\t.duty-q-old { background: #FFF7E6; color: #B27409; border-radius: 99px; padding: 2px 9px; font-weight: 700; margin-left: 6px; }\n\t\t\t.duty-q-q { font-size: 14px; line-height: 1.55; margin-bottom: 8px; }\n\t\t\t.duty-q-a { background: #F4F7F6; border-radius: 8px; padding: 10px 12px; font-size: 13px; line-height: 1.55; }\n\t\t\t.duty-q-pub { color: #0C6B4F; font-size: 11px; text-transform: uppercase; letter-spacing: .8px; }\n\t\t\t.duty-q-pubchk { display: block; font-weight: 400; font-size: 12.5px; margin: 8px 0; }`;'



EDITS = [
    (CR, ASK_OLD, ASK_NEW, "question doctype + learner reads"),
    (ACAD, STAFF_OLD, STAFF_NEW, "tutor queue"),
    (PORTAL, RD_OLD, RD_NEW, "reader heading"),
    (PORTAL, CALL_OLD, CALL_NEW, "render threads"),
    (PORTAL, JS_OLD, JS_NEW, "ask + thread js"),
    (PORTAL, CSS_OLD, CSS_NEW, "thread css"),
    (JS, ICON_OLD, ICON_NEW, "ask icon"),
    (JS, RAIL_OLD, RAIL_NEW, "rail item"),
    (JS, JSD_OLD, JSD_NEW, "questions dialog"),
    (JS, QCSS_OLD, QCSS_NEW, "dialog css"),
]


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
    for p in (INIT, CR, ACAD, PORTAL, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_lesson_questions(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.220.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.220.0.")

    problems = []
    for f, old, _new, label in EDITS:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(EDITS))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    d = os.path.join(root, DT_DIR, "duty_lesson_question")
    if not os.path.isdir(d):
        os.makedirs(d)
    for fname, body in (("__init__.py", ""),
                        ("duty_lesson_question.json", _json.dumps(QDT, indent=1) + "\n"),
                        ("duty_lesson_question.py", CTRL)):
        p = os.path.join(d, fname)
        if not os.path.exists(p):
            with io.open(p, "w", encoding="utf-8") as f:
                f.write(body)
    print("  doctype: Duty Lesson Question")

    add_fields(os.path.join(root, DSDT), [
        {"fieldname": "academy_tutors", "fieldtype": "Small Text",
         "label": "Academy Tutors", "description": "Who answers lesson questions. Comma separated."},
    ])
    print("  Duty Settings: +academy_tutors")

    for f, old, new, _label in EDITS:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, ACAD, PORTAL, JS):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: ask + read threads")
    print("  academy.py: tutor queue, answer, email")
    print("  portal.html / duty_board.js: learner threads, staff queue")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.220.0"', '"3.221.0"'))
    print("wrote __init__.py -> 3.221.0")


if __name__ == "__main__":
    main()
