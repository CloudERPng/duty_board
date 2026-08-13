#!/usr/bin/env python3
"""Duty Board v3.206.0 — CLIENT EXAMS GROW UP: proctoring, attempt policy,
result discipline.

The client portal ran the classic paper: all ten questions at once, untimed,
unlimited retakes, and a result screen naming the exact questions you got
wrong. Fine for an internal learning aid; indefensible as a paid assessment,
because attempt two is attempt one with the answer key.

v3.78.0 already built proctoring — one question at a time, server-stamped,
countdown, focus-loss counting, disconnect forfeits — and deliberately fenced
it to staff. This patch opens that gate to the portal and adds the policy
layer a sold exam needs.

STAFF BEHAVIOUR IS UNCHANGED. The proctored core and the timed-start builder
are moved verbatim into shared helpers (_proctored_next / _proctored_answer /
_exam_start) with the whitelisted staff endpoints kept as thin _staff_only()
wrappers over the same code. Every new policy field defaults to today's
behaviour, so no existing module changes until someone ticks a box, and the
attempt gate is enforced on the CLIENT path only.

Schema
  Duty Training Module: +max_attempts (Int, 0 = unlimited),
    +retake_wait_hours (Int, 0 = none), +hide_wrong_answers (Check)
  Duty Quiz Question:  +topic (Data) — powers the per-area result breakdown,
    silent until banks carry topics

Backend (client_room.py)
  - _exam_policy / _quiz_state: policy reported to the UI (attempts_left,
    next_attempt_at, timed, pass_mark, size, hide_wrong)
  - _exam_gate: client-only enforcement of attempt cap + cooling-off
  - _exam_start: shared classic-or-timed start (extracted from my_quiz_start)
  - _proctored_next / _proctored_answer: shared cores (extracted)
  - client_quiz_start honours timed_mode and passes the gate
  - client_proctored_next / client_proctored_answer: room-membership guarded
  - _topic_breakdown: [(question, ok)] -> per-area right/total, sorted worst
    first; returns [] when the bank has no topics
  - _quiz_submit / _timed_finish: breakdown added; wrong-answer list withheld
    when the module says so

Portal (portal.html)
  - honest policy line on the course page; locked state when attempts are
    spent or cooling off
  - timed runner: rules screen, one question, countdown bar, blur counter,
    no going back, auto-submit at zero
  - shared result screen with the per-area breakdown

Deploy: apply -> bench migrate (schema) -> bench build --app duty_board ->
clear-cache + clear-website-cache -> restart. Anchored, idempotent.
Requires v3.205.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
TMDT = "duty_board/duty_board/doctype/duty_training_module/duty_training_module.json"
QQDT = "duty_board/duty_board/doctype/duty_quiz_question/duty_quiz_question.json"
CHECK_ONLY = "--check" in sys.argv


# --- 1. imports: add_to_date for the cooling-off window ---------------------
IMP_OLD = "from frappe.utils import cint, get_datetime, getdate, now_datetime, today"
IMP_NEW = "from frappe.utils import add_to_date, cint, get_datetime, getdate, now_datetime, today"


# --- 2. _quiz_state gains the policy; _exam_policy/_exam_gate/_topic_breakdown
QS_OLD = '''def _quiz_state(module, user):
\tattempts = frappe.get_all(
\t\t"Duty Quiz Attempt",
\t\tfilters={"user": user, "module": module, "finished_at": ["is", "set"]},
\t\tfields=["score", "passed"],
\t)
\treturn {
\t\t"attempts": len(attempts),
\t\t"best": max((a.score for a in attempts), default=0),
\t\t"passed": any(a.passed for a in attempts),
\t\t"bank": frappe.db.count("Duty Quiz Question", {"module": module, "active": 1}),
\t}'''

QS_NEW = '''def _exam_policy(module):
\t"""Per-module exam policy. Every field defaults to the pre-v3.206.0
\tbehaviour — unlimited attempts, no cooling-off, wrong answers shown —
\tso no existing module changes until someone sets it deliberately."""
\tp = frappe.db.get_value(
\t\t"Duty Training Module", module,
\t\t[
\t\t\t"max_attempts", "retake_wait_hours", "hide_wrong_answers",
\t\t\t"timed_mode", "questions_served", "pass_mark",
\t\t],
\t\tas_dict=True,
\t) or frappe._dict()
\treturn frappe._dict({
\t\t"max_attempts": cint(p.get("max_attempts")),
\t\t"wait_hours": cint(p.get("retake_wait_hours")),
\t\t"hide_wrong": cint(p.get("hide_wrong_answers")),
\t\t"timed": cint(p.get("timed_mode")),
\t\t"size": cint(p.get("questions_served")) or QUIZ_SIZE,
\t\t"pass_mark": cint(p.get("pass_mark")) or 70,
\t})


def _quiz_state(module, user):
\tattempts = frappe.get_all(
\t\t"Duty Quiz Attempt",
\t\tfilters={"user": user, "module": module, "finished_at": ["is", "set"]},
\t\tfields=["score", "passed", "finished_at"],
\t\torder_by="finished_at desc",
\t)
\tpol = _exam_policy(module)
\tused = len(attempts)
\tpassed = any(a.passed for a in attempts)
\tnext_at = None
\tif pol.wait_hours and attempts and not passed:
\t\tnx = add_to_date(get_datetime(attempts[0].finished_at), hours=pol.wait_hours)
\t\tif nx > now_datetime():
\t\t\tnext_at = str(nx)
\treturn {
\t\t"attempts": used,
\t\t"best": max((a.score for a in attempts), default=0),
\t\t"passed": passed,
\t\t"bank": frappe.db.count("Duty Quiz Question", {"module": module, "active": 1}),
\t\t"max_attempts": pol.max_attempts,
\t\t"attempts_left": max(0, pol.max_attempts - used) if pol.max_attempts else None,
\t\t"next_attempt_at": next_at,
\t\t"timed": pol.timed,
\t\t"hide_wrong": pol.hide_wrong,
\t\t"size": pol.size,
\t\t"pass_mark": pol.pass_mark,
\t}


def _exam_gate(module, user):
\t"""Enforce the attempt cap and cooling-off window. Called on the CLIENT
\tpath only — internal staff testing keeps its old ungated behaviour."""
\tst = _quiz_state(module, user)
\tif st["passed"]:
\t\treturn st
\tif st["max_attempts"] and st["attempts"] >= st["max_attempts"]:
\t\tfrappe.throw(
\t\t\t_("You have used all {0} permitted attempts for this assessment. Speak to your training coordinator.").format(
\t\t\t\tst["max_attempts"]
\t\t\t)
\t\t)
\tif st["next_attempt_at"]:
\t\tfrappe.throw(
\t\t\t_("Your next attempt unlocks on {0}.").format(
\t\t\t\tfrappe.utils.format_datetime(st["next_attempt_at"], "d MMM yyyy, HH:mm")
\t\t\t)
\t\t)
\treturn st


def _topic_breakdown(pairs):
\t"""[(question_name, ok)] -> per-area right/total, worst area first. The
\tsponsor-facing number. Returns [] when the bank carries no topics, so it
\tstays silent rather than inventing an area called None."""
\tif not pairs:
\t\treturn []
\ttopics = {
\t\tq.name: (q.topic or "").strip()
\t\tfor q in frappe.get_all(
\t\t\t"Duty Quiz Question",
\t\t\tfilters={"name": ["in", [p[0] for p in pairs]]},
\t\t\tfields=["name", "topic"],
\t\t)
\t}
\tif not any(topics.values()):
\t\treturn []
\tagg = {}
\tfor qn, ok in pairs:
\t\tt = topics.get(qn) or _("General")
\t\trow = agg.setdefault(t, {"topic": t, "right": 0, "total": 0})
\t\trow["total"] += 1
\t\tif ok:
\t\t\trow["right"] += 1
\treturn sorted(agg.values(), key=lambda r: (r["right"] / r["total"], r["topic"]))'''


# --- 3. _quiz_submit: collect pairs, honour hide_wrong, add breakdown -------
SUB_LOOP_OLD = '''\tscore_n, wrong = 0, []
\tfor s in served:
\t\tchosen = answers.get(s["q"])
\t\tif chosen is None:
\t\t\tchosen = -1
\t\tchosen = cint(chosen)
\t\treal = s["order"][chosen] if 0 <= chosen < 4 else -1
\t\tif real == correct_map.get(s["q"]):
\t\t\tscore_n += 1
\t\telse:
\t\t\twrong.append(frappe.db.get_value("Duty Quiz Question", s["q"], "question"))'''

SUB_LOOP_NEW = '''\tscore_n, wrong, pairs = 0, [], []
\tfor s in served:
\t\tchosen = answers.get(s["q"])
\t\tif chosen is None:
\t\t\tchosen = -1
\t\tchosen = cint(chosen)
\t\treal = s["order"][chosen] if 0 <= chosen < 4 else -1
\t\thit = real == correct_map.get(s["q"])
\t\tpairs.append((s["q"], hit))
\t\tif hit:
\t\t\tscore_n += 1
\t\telse:
\t\t\twrong.append(frappe.db.get_value("Duty Quiz Question", s["q"], "question"))'''

SUB_RET_OLD = '''\tstate = _quiz_state(rec.module, frappe.session.user)
\treturn {
\t\t"score": score,
\t\t"passed": passed,
\t\t"pass_mark": pass_mark,
\t\t"wrong": wrong,
\t\t"attempts": state["attempts"],
\t\t"best": state["best"],
\t\t"newly_certified": newly_certified,
\t}'''

SUB_RET_NEW = '''\tstate = _quiz_state(rec.module, frappe.session.user)
\treturn {
\t\t"score": score,
\t\t"passed": passed,
\t\t"pass_mark": pass_mark,
\t\t"wrong": [] if state["hide_wrong"] else wrong,
\t\t"breakdown": _topic_breakdown(pairs),
\t\t"attempts": state["attempts"],
\t\t"attempts_left": state["attempts_left"],
\t\t"next_attempt_at": state["next_attempt_at"],
\t\t"best": state["best"],
\t\t"newly_certified": newly_certified,
\t}'''


# --- 4. _timed_finish: same discipline -------------------------------------
TF_OLD = '''\twrong = [
\t\tfrappe.db.get_value("Duty Quiz Question", r["q"], "question")
\t\tfor r in results
\t\tif not r.get("ok")
\t]
\tstate = _quiz_state(rec.module, frappe.session.user)
\treturn {
\t\t"done": 1,
\t\t"score": score,
\t\t"passed": passed,
\t\t"pass_mark": pass_mark,
\t\t"wrong": wrong,
\t\t"timeouts": sum(1 for r in results if r.get("timed_out")),
\t\t"attempts": state["attempts"],
\t\t"best": state["best"],
\t\t"newly_certified": newly_certified,
\t}'''

TF_NEW = '''\twrong = [
\t\tfrappe.db.get_value("Duty Quiz Question", r["q"], "question")
\t\tfor r in results
\t\tif not r.get("ok")
\t]
\tstate = _quiz_state(rec.module, frappe.session.user)
\treturn {
\t\t"done": 1,
\t\t"score": score,
\t\t"passed": passed,
\t\t"pass_mark": pass_mark,
\t\t"wrong": [] if state["hide_wrong"] else wrong,
\t\t"breakdown": _topic_breakdown([(r["q"], bool(r.get("ok"))) for r in results]),
\t\t"timeouts": sum(1 for r in results if r.get("timed_out")),
\t\t"attempts": state["attempts"],
\t\t"attempts_left": state["attempts_left"],
\t\t"next_attempt_at": state["next_attempt_at"],
\t\t"best": state["best"],
\t\t"newly_certified": newly_certified,
\t}'''


# --- 5. my_quiz_start -> _exam_start (verbatim move, staff unchanged) ------
MS_OLD = '''\tmod = frappe.db.get_value(
\t\t"Duty Training Module", rec.module,
\t\t["timed_mode", "seconds_per_question", "questions_served"], as_dict=True,
\t) or frappe._dict()
\tif not cint(mod.timed_mode):
\t\treturn _quiz_start(rec.name, rec.module)
\t# Timed mode: build the attempt with the SAME subset+shuffle machinery,
\t# but hand back only a handle — questions are served one at a time.
\tbase = _quiz_start(rec.name, rec.module)
\tsize = base["size"]
\tif cint(mod.questions_served) and cint(mod.questions_served) != size:
\t\t# module overrides the subset size: rebuild served on the attempt
\t\timport random as _rnd
\t\tatt = frappe.get_doc("Duty Quiz Attempt", base["attempt"])
\t\tbank = frappe.get_all(
\t\t\t"Duty Quiz Question",
\t\t\tfilters={"module": rec.module, "active": 1},
\t\t\tfields=["name"],
\t\t)
\t\tn = min(cint(mod.questions_served), len(bank))
\t\tpicked = _rnd.sample([b.name for b in bank], n)
\t\tserved = []
\t\tfor qn in picked:
\t\t\torder = [0, 1, 2, 3]
\t\t\t_rnd.shuffle(order)
\t\t\tserved.append({"q": qn, "order": order})
\t\tatt.db_set("served", json.dumps(served), update_modified=False)
\t\tsize = n
\tseconds = cint(mod.seconds_per_question) or 60
\tfrappe.db.set_value(
\t\t"Duty Quiz Attempt", base["attempt"],
\t\t{"mode": "Timed", "current_idx": 0, "results": "[]", "blurs": 0},
\t\tupdate_modified=False,
\t)
\tfrappe.db.commit()
\treturn {"timed": 1, "attempt": base["attempt"], "size": size, "seconds": seconds}'''

MS_NEW = '''\treturn _exam_start(rec.name, rec.module)


def _exam_start(rec_name, module):
\t"""Classic paper, or a timed handle when the module is proctored.
\tVerbatim the v3.78.0 logic, lifted out of my_quiz_start so the client
\tportal can reach it without a second copy of the exam mechanics."""
\tmod = frappe.db.get_value(
\t\t"Duty Training Module", module,
\t\t["timed_mode", "seconds_per_question", "questions_served"], as_dict=True,
\t) or frappe._dict()
\tif not cint(mod.timed_mode):
\t\treturn _quiz_start(rec_name, module)
\t# Timed mode: build the attempt with the SAME subset+shuffle machinery,
\t# but hand back only a handle — questions are served one at a time.
\tbase = _quiz_start(rec_name, module)
\tsize = base["size"]
\tif cint(mod.questions_served) and cint(mod.questions_served) != size:
\t\t# module overrides the subset size: rebuild served on the attempt
\t\timport random as _rnd
\t\tatt = frappe.get_doc("Duty Quiz Attempt", base["attempt"])
\t\tbank = frappe.get_all(
\t\t\t"Duty Quiz Question",
\t\t\tfilters={"module": module, "active": 1},
\t\t\tfields=["name"],
\t\t)
\t\tn = min(cint(mod.questions_served), len(bank))
\t\tpicked = _rnd.sample([b.name for b in bank], n)
\t\tserved = []
\t\tfor qn in picked:
\t\t\torder = [0, 1, 2, 3]
\t\t\t_rnd.shuffle(order)
\t\t\tserved.append({"q": qn, "order": order})
\t\tatt.db_set("served", json.dumps(served), update_modified=False)
\t\tsize = n
\tseconds = cint(mod.seconds_per_question) or 60
\tfrappe.db.set_value(
\t\t"Duty Quiz Attempt", base["attempt"],
\t\t{"mode": "Timed", "current_idx": 0, "results": "[]", "blurs": 0},
\t\tupdate_modified=False,
\t)
\tfrappe.db.commit()
\treturn {"timed": 1, "attempt": base["attempt"], "size": size, "seconds": seconds}'''


# --- 6. proctored endpoints split into audience wrapper + shared core ------
PN_OLD = '''\t"""Serve the current question, stamped server-side. Calling this after
\ta disconnect forfeits the stale question (rule: no going back)."""
\t_staff_only()
\tatt = _timed_attempt(attempt)'''

PN_NEW = '''\t"""Serve the current question, stamped server-side. Calling this after
\ta disconnect forfeits the stale question (rule: no going back)."""
\t_staff_only()
\treturn _proctored_next(attempt)


def _proctored_next(attempt):
\tatt = _timed_attempt(attempt)'''

PA_OLD = '''\t"""Record the answer for the CURRENT question. Server-enforced timing:
\tanswers after limit+5s grace count as timed out. Advances; no return."""
\t_staff_only()
\tatt = _timed_attempt(attempt)'''

PA_NEW = '''\t"""Record the answer for the CURRENT question. Server-enforced timing:
\tanswers after limit+5s grace count as timed out. Advances; no return."""
\t_staff_only()
\treturn _proctored_answer(attempt, choice, blurs)


def _proctored_answer(attempt, choice=None, blurs=0):
\tatt = _timed_attempt(attempt)'''

# the three internal hops must target the core, not the staff-gated wrapper
HOP1_OLD = '''\tif idx >= len(served) or not att.current_served_at:
\t\treturn proctored_next(attempt)'''
HOP1_NEW = '''\tif idx >= len(served) or not att.current_served_at:
\t\treturn _proctored_next(attempt)'''

HOP2_OLD = '''\tif len(results) > idx:
\t\treturn proctored_next(attempt)  # double-submit: ignore, serve next'''
HOP2_NEW = '''\tif len(results) > idx:
\t\treturn _proctored_next(attempt)  # double-submit: ignore, serve next'''

HOP3_OLD = '''\tfrappe.db.commit()
\treturn proctored_next(attempt)


@frappe.whitelist()
def quiz_forensics(limit=30):'''
HOP3_NEW = '''\tfrappe.db.commit()
\treturn _proctored_next(attempt)


@frappe.whitelist()
def quiz_forensics(limit=30):'''


# --- 7. client_quiz_start: gate + timed branch -----------------------------
CQS_OLD = '''\tif not rec or rec.trainee != frappe.session.user or rec.room != room.name:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\treturn _quiz_start(rec.name, rec.module)'''

CQS_NEW = '''\tif not rec or rec.trainee != frappe.session.user or rec.room != room.name:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\t_exam_gate(rec.module, frappe.session.user)
\treturn _exam_start(rec.name, rec.module)'''


# --- 8. client proctored endpoints -----------------------------------------
CQSUB_OLD = '''def client_quiz_submit(attempt, answers):
\troom = _client_room()
\tatt_rec = frappe.db.get_value("Duty Quiz Attempt", attempt, "record")
\trec = frappe.get_doc("Duty Training Record", att_rec)
\tif rec.trainee != frappe.session.user or rec.room != room.name:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\treturn _quiz_submit(attempt, answers, rec)'''

CQSUB_NEW = '''def client_quiz_submit(attempt, answers):
\troom = _client_room()
\tatt_rec = frappe.db.get_value("Duty Quiz Attempt", attempt, "record")
\trec = frappe.get_doc("Duty Training Record", att_rec)
\tif rec.trainee != frappe.session.user or rec.room != room.name:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\treturn _quiz_submit(attempt, answers, rec)


def _client_attempt(attempt):
\t"""Room-membership guard on a client exam attempt — the client mirror of
\t_staff_only() on the proctored endpoints. Room resolves first, as always;
\t_timed_attempt then re-checks the attempt belongs to this session."""
\troom = _client_room()
\tatt_rec = frappe.db.get_value("Duty Quiz Attempt", attempt, "record")
\trec = frappe.db.get_value(
\t\t"Duty Training Record", att_rec, ["trainee", "room"], as_dict=True
\t)
\tif not rec or rec.trainee != frappe.session.user or rec.room != room.name:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)


@frappe.whitelist()
def client_proctored_next(attempt):
\t_client_attempt(attempt)
\treturn _proctored_next(attempt)


@frappe.whitelist()
def client_proctored_answer(attempt, choice=None, blurs=0):
\t_client_attempt(attempt)
\treturn _proctored_answer(attempt, choice, blurs)'''


# --- 9. portal: course-page policy line ------------------------------------
P1_OLD = '''\t\t\t\t\t? allRead
\t\t\t\t\t\t? `<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap"><button onclick="startQuiz('${esc(c.record)}')">\U0001F4DD Take the test</button><span class="muted" style="font-size:12px">${qz.attempts ? `best so far ${qz.best}% \u00b7 ` : ""}10 questions \u00b7 pass at 70% \u00b7 unlimited retakes</span></div>`
\t\t\t\t\t\t: `<div class="muted" style="font-size:13px;margin-bottom:10px">\U0001F4DD The test unlocks when every lesson is read.</div>`'''

P1_NEW = '''\t\t\t\t\t? allRead
\t\t\t\t\t\t? (examLocked(qz)
\t\t\t\t\t\t\t? `<div class="exlock">\U0001F512 ${examLockReason(qz)}</div>`
\t\t\t\t\t\t\t: `<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px;flex-wrap:wrap"><button onclick="startQuiz('${esc(c.record)}')">${qz.timed ? "\u23F1 Begin timed assessment" : "\U0001F4DD Take the assessment"}</button><span class="muted" style="font-size:12px">${qz.attempts ? `best so far ${qz.best}% \u00b7 ` : ""}${examPolicyLine(qz)}</span></div>`)
\t\t\t\t\t\t: `<div class="muted" style="font-size:13px;margin-bottom:10px">\U0001F4DD The assessment unlocks when every lesson is read.</div>`'''


# --- 10. portal: runner + result -------------------------------------------
P2_OLD = '''function startQuiz(record) {
\tstopBeat();
\tapi("client_quiz_start", { record: record }).then((t) => {
\t\twindow._quiz = { attempt: t.attempt, record: record };
\t\tdocument.getElementById("acad").innerHTML = `
\t\t\t<h3 style="margin:2px 0 10px">\U0001F4DD Assessment \u2014 10 questions</h3>'''

P2_NEW = '''function examPolicyLine(qz) {
\tconst bits = [(qz.size || 10) + " questions", "pass at " + (qz.pass_mark || 70) + "%"];
\tif (qz.timed) bits.push("timed \u00b7 one question at a time");
\tif (qz.max_attempts) bits.push(qz.max_attempts + " attempt" + (qz.max_attempts === 1 ? "" : "s") + " permitted" + (typeof qz.attempts_left === "number" ? " \u00b7 " + qz.attempts_left + " left" : ""));
\telse bits.push("unlimited retakes");
\treturn bits.join(" \u00b7 ");
}
function examLocked(qz) {
\treturn !qz.passed && (qz.attempts_left === 0 || !!qz.next_attempt_at);
}
function examLockReason(qz) {
\tif (qz.attempts_left === 0) return "You have used all " + qz.max_attempts + " permitted attempts. Speak to your training coordinator.";
\treturn "Your next attempt unlocks on " + esc(String(qz.next_attempt_at || "").slice(0, 16).replace("T", " ")) + ".";
}
function examResult(res, record) {
\tconst canRetake = !res.passed && res.attempts_left !== 0 && !res.next_attempt_at;
\tdocument.getElementById("acad").innerHTML = `
\t\t<div style="text-align:center;padding:12px 0 6px">
\t\t\t<div style="font-size:46px;font-weight:800;color:${res.passed ? "#15803d" : "#B27409"}">${res.score}%</div>
\t\t\t<div class="muted">pass mark ${res.pass_mark}% \u00b7 attempt ${res.attempts}${res.attempts > 1 ? ` \u00b7 best ${res.best}%` : ""}${typeof res.attempts_left === "number" ? ` \u00b7 ${res.attempts_left} remaining` : ""}</div>
\t\t\t${res.timeouts ? `<div style="color:#B45309;font-weight:700;font-size:13px;margin-top:6px">\u23F1 ${res.timeouts} question${res.timeouts === 1 ? "" : "s"} ran out of time</div>` : ""}
\t\t\t${res.newly_certified ? `<div style="margin-top:8px;font-weight:700;color:#0C4A43">\U0001F393 Course completed \u2014 your certificate is on its way to your Documents.</div>` : ""}
\t\t</div>
\t\t${(res.breakdown || []).length
\t\t\t? `<div class="exbd"><b style="font-size:14px">How you scored by area</b>${res.breakdown.map((r) => {
\t\t\t\tconst p = Math.round((r.right / r.total) * 100);
\t\t\t\treturn `<div class="exbdrow"><span class="exbdt">${esc(r.topic)}</span><span class="exbdbar"><i style="width:${p}%;background:${p >= 70 ? "#0E8A63" : p >= 50 ? "#C99A2E" : "#C2410C"}"></i></span><span class="muted" style="font-size:12px">${r.right}/${r.total}</span></div>`;
\t\t\t}).join("")}</div>`
\t\t\t: ""}
\t\t${!res.passed && (res.wrong || []).length
\t\t\t? `<div style="margin-top:12px"><b style="font-size:14px">Review these areas, then retake:</b>${res.wrong.map((w) => `<div class="muted" style="font-size:13px;margin:4px 0">\u2022 ${esc(w)}</div>`).join("")}</div>`
\t\t\t: ""}
\t\t${!res.passed && res.next_attempt_at ? `<div class="exlock" style="margin-top:12px">\U0001F512 Your next attempt unlocks on ${esc(String(res.next_attempt_at).slice(0, 16).replace("T", " "))}.</div>` : ""}
\t\t${!res.passed && res.attempts_left === 0 ? `<div class="exlock" style="margin-top:12px">\U0001F512 You have used all permitted attempts. Speak to your training coordinator.</div>` : ""}
\t\t<div style="display:flex;gap:10px;margin-top:14px">
\t\t\t${canRetake ? `<button onclick="startQuiz('${esc(record)}')">\u21BB Retake now</button>` : ""}
\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="openCourse('${esc(record)}');loadTraining()">Back to course</button>
\t\t</div>`;
\tif (res.newly_certified) celebrate();
}
function examRunner(t, record) {
\tconst acad = () => document.getElementById("acad");
\tlet blurs = 0, timer = null, deadline = 0;
\tconst onBlur = () => { blurs += 1; };
\twindow.addEventListener("blur", onBlur);
\tconst cleanup = () => { clearInterval(timer); timer = null; window.removeEventListener("blur", onBlur); };
\tconst send = (choice) => {
\t\tclearInterval(timer);
\t\tconst b = blurs; blurs = 0;
\t\tconst go = document.getElementById("exgo");
\t\tif (go) go.disabled = true;
\t\tapi("client_proctored_answer", { attempt: t.attempt, choice: choice, blurs: b })
\t\t\t.then(show)
\t\t\t.catch((e) => { cleanup(); fail(e); });
\t};
\tconst show = (Q) => {
\t\tif (Q.done) { cleanup(); return examResult(Q, record); }
\t\tdeadline = Date.now() + Q.seconds * 1000;
\t\tacad().innerHTML = `
\t\t\t<div class="exhead"><b>Question ${Q.idx + 1} of ${Q.size}</b><span class="exclock">${Q.seconds}s</span></div>
\t\t\t<div class="exbar"><i style="width:100%"></i></div>
\t\t\t<div class="exq">${esc(Q.question)}</div>
\t\t\t${Q.options.map((o, j) => `<label class="exopt"><input type="radio" name="exq" value="${j}"><span>${esc(o)}</span></label>`).join("")}
\t\t\t<div style="display:flex;gap:10px;margin-top:12px"><button id="exgo">Submit answer</button></div>
\t\t\t<div class="muted" style="font-size:12px;margin-top:8px">One question at a time. There is no going back. A question still open when the clock reaches zero counts as wrong.</div>`;
\t\tacad().querySelectorAll(".exopt").forEach((l) => l.addEventListener("click", () => {
\t\t\tacad().querySelectorAll(".exopt").forEach((x) => x.classList.remove("on"));
\t\t\tl.classList.add("on");
\t\t}));
\t\tdocument.getElementById("exgo").onclick = () => {
\t\t\tconst v = acad().querySelector("input[name=exq]:checked");
\t\t\tsend(v ? v.value : null);
\t\t};
\t\ttimer = setInterval(() => {
\t\t\tconst left = Math.max(0, deadline - Date.now());
\t\t\tconst pct = (left / (Q.seconds * 1000)) * 100;
\t\t\tconst c = acad().querySelector(".exclock"), b = acad().querySelector(".exbar i");
\t\t\tif (!c || !b) { clearInterval(timer); return; }
\t\t\tc.textContent = Math.ceil(left / 1000) + "s";
\t\t\tb.style.width = pct + "%";
\t\t\tif (pct < 25) b.classList.add("low"); else b.classList.remove("low");
\t\t\tif (left <= 0) send(null);
\t\t}, 250);
\t};
\tacad().innerHTML = `
\t\t<h3 style="margin:2px 0 10px">\u23F1 Timed assessment</h3>
\t\t<div class="exrules">
\t\t\t<div>${t.size} questions, ${t.seconds} seconds each.</div>
\t\t\t<div>Questions appear one at a time. Once you answer \u2014 or the clock reaches zero \u2014 you move on. There is no going back.</div>
\t\t\t<div>Your time on each question, and any switch away from this tab, are recorded on your result.</div>
\t\t\t<div>Do not reload or close this page: a question left open is forfeited.</div>
\t\t</div>
\t\t<div style="display:flex;gap:10px;margin-top:14px">
\t\t\t<button id="exstart">\u25B6 Begin</button>
\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="openCourse('${esc(record)}')">Cancel</button>
\t\t</div>`;
\tdocument.getElementById("exstart").onclick = () => {
\t\tdocument.getElementById("exstart").disabled = true;
\t\tapi("client_proctored_next", { attempt: t.attempt })
\t\t\t.then(show)
\t\t\t.catch((e) => { cleanup(); fail(e); });
\t};
\tdocument.querySelector(".card.acad").scrollIntoView({ behavior: "smooth", block: "start" });
}
function startQuiz(record) {
\tstopBeat();
\tapi("client_quiz_start", { record: record }).then((t) => {
\t\twindow._quiz = { attempt: t.attempt, record: record };
\t\tif (t.timed) return examRunner(t, record);
\t\tdocument.getElementById("acad").innerHTML = `
\t\t\t<h3 style="margin:2px 0 10px">\U0001F4DD Assessment \u2014 ${t.questions.length} questions</h3>'''


# --- 11. portal: classic paper footer + submit routes to examResult --------
P3_OLD = '''\t\t\t<div class="muted" style="font-size:12px;margin-bottom:10px">Unanswered questions count as wrong. Unlimited retakes \u2014 your best score stands.</div>'''
P3_NEW = '''\t\t\t<div class="muted" style="font-size:12px;margin-bottom:10px">Unanswered questions count as wrong. Your best score stands.</div>'''

P4_OLD = '''\tapi("client_quiz_submit", { attempt: window._quiz.attempt, answers: JSON.stringify(answers) })
\t\t.then((res) => {
\t\t\tconst record = window._quiz.record;
\t\t\tdocument.getElementById("acad").innerHTML = `
\t\t\t\t<div style="text-align:center;padding:12px 0 6px">
\t\t\t\t\t<div style="font-size:46px;font-weight:800;color:${res.passed ? "#15803d" : "#B27409"}">${res.score}%</div>
\t\t\t\t\t<div class="muted">pass mark ${res.pass_mark}% \u00b7 attempt ${res.attempts}${res.attempts > 1 ? ` \u00b7 best ${res.best}%` : ""}</div>
\t\t\t\t\t${res.newly_certified ? `<div style="margin-top:8px;font-weight:700;color:#0C4A43">\U0001F393 Course completed \u2014 your certificate is on its way to your Documents.</div>` : ""}
\t\t\t\t</div>
\t\t\t\t${!res.passed && (res.wrong || []).length
\t\t\t\t\t? `<div style="margin-top:8px"><b style="font-size:14px">Review these areas, then retake:</b>${res.wrong.map((w) => `<div class="muted" style="font-size:13px;margin:4px 0">\u2022 ${esc(w)}</div>`).join("")}</div>`
\t\t\t\t\t: ""}
\t\t\t\t<div style="display:flex;gap:10px;margin-top:14px">
\t\t\t\t\t${!res.passed ? `<button onclick="startQuiz('${esc(record)}')">\u21BB Retake now</button>` : ""}
\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="openCourse('${esc(record)}');loadTraining()">Back to course</button>
\t\t\t\t</div>`;
\t\t\tif (res.newly_certified) celebrate();
\t\t})'''

P4_NEW = '''\tapi("client_quiz_submit", { attempt: window._quiz.attempt, answers: JSON.stringify(answers) })
\t\t.then((res) => {
\t\t\texamResult(res, window._quiz.record);
\t\t})'''


# --- 12. portal CSS --------------------------------------------------------
CSS_OLD = '''\t#lessonbody blockquote.bq-warn:before { content: "\u26A0\uFE0F"; }'''
CSS_NEW = '''\t#lessonbody blockquote.bq-warn:before { content: "\u26A0\uFE0F"; }

\t/* ---- proctored assessment ---- */
\t.exhead { display: flex; align-items: baseline; justify-content: space-between; font-size: 14px; margin: 2px 0 6px; }
\t.exclock { font-variant-numeric: tabular-nums; font-weight: 800; font-size: 15px; color: var(--brand-700); }
\t.exbar { height: 5px; border-radius: 99px; background: #E4EAE8; overflow: hidden; margin-bottom: 14px; }
\t.exbar i { display: block; height: 100%; background: var(--brand); transition: width .25s linear; }
\t.exbar i.low { background: #C2410C; }
\t.exq { font-size: 15.5px; font-weight: 700; line-height: 1.5; margin-bottom: 12px; }
\t.exopt { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; margin-bottom: 8px;
\t\tborder: 1px solid #DCE4E1; border-radius: 10px; cursor: pointer; font-size: 14.5px; line-height: 1.45; background: #fff; }
\t.exopt.on { border-color: var(--brand); background: var(--brand-50); }
\t.exopt input { margin-top: 3px; }
\t.exrules { font-size: 14px; line-height: 1.65; background: var(--brand-50); border: 1px solid #CBE7DE;
\t\tborder-radius: 12px; padding: 12px 15px; }
\t.exrules div { margin: 6px 0; padding-left: 16px; position: relative; }
\t.exrules div:before { content: "\u2022"; position: absolute; left: 2px; color: var(--brand); }
\t.exlock { font-size: 13.5px; background: #FFF7E6; border: 1px solid #F3E0B5; color: #7A5312;
\t\tborder-radius: 10px; padding: 10px 13px; margin-bottom: 10px; }
\t.exbd { margin-top: 14px; }
\t.exbdrow { display: flex; align-items: center; gap: 10px; margin: 7px 0; }
\t.exbdt { flex: 0 0 40%; font-size: 13px; }
\t.exbdbar { flex: 1; height: 7px; border-radius: 99px; background: #E4EAE8; overflow: hidden; }
\t.exbdbar i { display: block; height: 100%; }'''


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

    if "def client_proctored_next(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.205.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.205.0.")

    edits = [
        (CR, IMP_OLD, IMP_NEW, "imports: add_to_date"),
        (CR, QS_OLD, QS_NEW, "_quiz_state + policy/gate/breakdown"),
        (CR, SUB_LOOP_OLD, SUB_LOOP_NEW, "_quiz_submit scoring loop"),
        (CR, SUB_RET_OLD, SUB_RET_NEW, "_quiz_submit return"),
        (CR, TF_OLD, TF_NEW, "_timed_finish return"),
        (CR, MS_OLD, MS_NEW, "my_quiz_start -> _exam_start"),
        (CR, PN_OLD, PN_NEW, "proctored_next split"),
        (CR, PA_OLD, PA_NEW, "proctored_answer split"),
        (CR, HOP1_OLD, HOP1_NEW, "hop 1 -> core"),
        (CR, HOP2_OLD, HOP2_NEW, "hop 2 -> core"),
        (CR, HOP3_OLD, HOP3_NEW, "hop 3 -> core"),
        (CR, CQS_OLD, CQS_NEW, "client_quiz_start gate + timed"),
        (CR, CQSUB_OLD, CQSUB_NEW, "client proctored endpoints"),
        (PORTAL, P1_OLD, P1_NEW, "portal: course policy line"),
        (PORTAL, P2_OLD, P2_NEW, "portal: runner + result"),
        (PORTAL, P3_OLD, P3_NEW, "portal: classic paper footer"),
        (PORTAL, P4_OLD, P4_NEW, "portal: submit -> examResult"),
        (PORTAL, CSS_OLD, CSS_NEW, "portal: exam css"),
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

    add_fields(os.path.join(root, TMDT), [
        {"fieldname": "max_attempts", "fieldtype": "Int",
         "label": "Max Attempts (0 = unlimited)"},
        {"fieldname": "retake_wait_hours", "fieldtype": "Int",
         "label": "Retake Wait (hours, 0 = none)"},
        {"fieldname": "hide_wrong_answers", "fieldtype": "Check",
         "label": "Withhold Wrong-Answer List"},
    ])
    add_fields(os.path.join(root, QQDT), [
        {"fieldname": "topic", "fieldtype": "Data", "label": "Topic / Area"},
    ])
    print("  module policy fields + question topic added")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)

    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: shared exam cores + client proctoring + policy")
    print("  portal.html: timed runner, policy line, result breakdown")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.205.0"', '"3.206.0"'))
    print("wrote __init__.py -> 3.206.0")


if __name__ == "__main__":
    main()
