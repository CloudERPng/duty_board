#!/usr/bin/env python3
"""Duty Board v3.78.0 — proctored (timed) exams.

The exam served the whole paper at once, untimed — ideal for AI-assisted
cheating. Decisions locked: 60s/question default with per-module
override, per-module Timed toggle, timeout = wrong but flagged, focus
losses recorded + announced, manager forensics, disconnect forfeits the
current question and resumes at the next. (Random subset + option
shuffle already existed and are reused untouched.)

- Duty Training Module: +timed_mode (Check), +seconds_per_question
  (Int, default 60), +questions_served (Int; 0 = existing default of
  QUIZ_SIZE).
- Duty Quiz Attempt: +mode, +current_idx, +current_served_at, +results
  (JSON: per-question given/correct/elapsed/timed_out), +blurs.
- Backend (client_room.py): my_quiz_start on a timed module returns a
  timed handle (no questions leak); proctored_next serves ONE question
  stamped server-side; proctored_answer validates within the limit
  +5s network grace (late/timeout = wrong, flagged), records elapsed,
  advances — no going back — and on the last question scores, writes
  the attempt, and awards certification through the same completion
  path as the classic flow. Reconnect calls proctored_next: the stale
  question forfeits, the next serves. quiz_forensics (SM-only) lists
  timed attempts with per-question timing patterns + blur counts.
- UI: timed runner dialog — rules screen (announcing that timing and
  tab-switches are recorded), one question at a time with a live
  countdown bar, auto-submit on zero, blur counter; SM-only ⏱ Exam
  forensics button in the 🎓 Team training dialog.

Client-portal quizzes keep the classic flow regardless of the toggle
(staff modules aren't in the portal; client academies have different
politics — revisit deliberately if ever needed).

Schema -> bench migrate && bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.77.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CR = "duty_board/client_room.py"
TMDT = "duty_board/duty_board/doctype/duty_training_module/duty_training_module.json"
QADT = "duty_board/duty_board/doctype/duty_quiz_attempt/duty_quiz_attempt.json"
CHECK_ONLY = "--check" in sys.argv

# --- 1. my_quiz_start branches to timed mode --------------------------------
MS_OLD = '''@frappe.whitelist()
def my_quiz_start(record):
\t_staff_only()
\trec = frappe.db.get_value(
\t\t"Duty Training Record", record, ["name", "module", "trainee", "room"], as_dict=True
\t)
\tif not rec or rec.trainee != frappe.session.user or rec.room:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\treturn _quiz_start(rec.name, rec.module)'''
MS_NEW = '''@frappe.whitelist()
def my_quiz_start(record):
\t_staff_only()
\trec = frappe.db.get_value(
\t\t"Duty Training Record", record, ["name", "module", "trainee", "room"], as_dict=True
\t)
\tif not rec or rec.trainee != frappe.session.user or rec.room:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\tmod = frappe.db.get_value(
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
\treturn {"timed": 1, "attempt": base["attempt"], "size": size, "seconds": seconds}


def _timed_attempt(attempt):
\tatt = frappe.get_doc("Duty Quiz Attempt", attempt)
\tif att.user != frappe.session.user:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\tif att.finished_at:
\t\tfrappe.throw(_("This attempt is already finished."))
\tif (att.mode or "") != "Timed":
\t\tfrappe.throw(_("Not a timed attempt."))
\treturn att


def _timed_seconds(att):
\treturn cint(
\t\tfrappe.db.get_value("Duty Training Module", att.module, "seconds_per_question")
\t) or 60


def _timed_finish(att):
\t"""Score from results, write the attempt, run the shared completion."""
\tresults = json.loads(att.results or "[]")
\tscore_n = sum(1 for r in results if r.get("ok"))
\ttotal = len(json.loads(att.served or "[]")) or 1
\tscore = round(score_n * 100 / total)
\trec = frappe.get_doc("Duty Training Record", att.record)
\tpass_mark = cint(frappe.db.get_value("Duty Training Module", rec.module, "pass_mark")) or 70
\tpassed = score >= pass_mark
\tatt.db_set(
\t\t{"finished_at": now_datetime(), "score": score, "passed": 1 if passed else 0},
\t\tupdate_modified=False,
\t)
\tfrappe.db.commit()
\tnewly_certified = False
\tif passed and rec.status != "Completed":
\t\t_award_module_completion(rec)
\t\tnewly_certified = True
\twrong = [
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
\t}


@frappe.whitelist()
def proctored_next(attempt):
\t"""Serve the current question, stamped server-side. Calling this after
\ta disconnect forfeits the stale question (rule: no going back)."""
\t_staff_only()
\tatt = _timed_attempt(attempt)
\tserved = json.loads(att.served or "[]")
\tidx = cint(att.current_idx)
\tresults = json.loads(att.results or "[]")
\t# a question was served but never answered (reload/disconnect): forfeit it
\tif att.current_served_at and len(results) <= idx and idx < len(served):
\t\tresults.append({"q": served[idx]["q"], "given": None, "ok": False, "timed_out": True, "elapsed": None})
\t\tidx += 1
\t\tatt.db_set(
\t\t\t{"results": json.dumps(results), "current_idx": idx, "current_served_at": None},
\t\t\tupdate_modified=False,
\t\t)
\tif idx >= len(served):
\t\treturn _timed_finish(att)
\ts = served[idx]
\tq = frappe.db.get_value(
\t\t"Duty Quiz Question", s["q"],
\t\t["question", "opt_a", "opt_b", "opt_c", "opt_d"], as_dict=True,
\t)
\topts = [q.opt_a, q.opt_b, q.opt_c, q.opt_d]
\tatt.db_set("current_served_at", now_datetime(), update_modified=False)
\tfrappe.db.commit()
\treturn {
\t\t"idx": idx,
\t\t"size": len(served),
\t\t"question": q.question,
\t\t"options": [opts[i] for i in s["order"]],
\t\t"seconds": _timed_seconds(att),
\t}


@frappe.whitelist()
def proctored_answer(attempt, choice=None, blurs=0):
\t"""Record the answer for the CURRENT question. Server-enforced timing:
\tanswers after limit+5s grace count as timed out. Advances; no return."""
\t_staff_only()
\tatt = _timed_attempt(attempt)
\tserved = json.loads(att.served or "[]")
\tidx = cint(att.current_idx)
\tif idx >= len(served) or not att.current_served_at:
\t\treturn proctored_next(attempt)
\ts = served[idx]
\telapsed = (now_datetime() - get_datetime(att.current_served_at)).total_seconds()
\tlimit = _timed_seconds(att) + 5  # network grace
\tresults = json.loads(att.results or "[]")
\tif len(results) > idx:
\t\treturn proctored_next(attempt)  # double-submit: ignore, serve next
\ttimed_out = elapsed > limit or choice is None or choice == ""
\tok = False
\tif not timed_out:
\t\tchosen = cint(choice)
\t\treal = s["order"][chosen] if 0 <= chosen < 4 else -1
\t\tcorrect = "ABCD".index(frappe.db.get_value("Duty Quiz Question", s["q"], "correct"))
\t\tok = real == correct
\tresults.append({
\t\t"q": s["q"],
\t\t"given": None if timed_out else cint(choice),
\t\t"ok": bool(ok),
\t\t"timed_out": bool(timed_out),
\t\t"elapsed": round(elapsed, 1),
\t})
\tatt.db_set(
\t\t{
\t\t\t"results": json.dumps(results),
\t\t\t"current_idx": idx + 1,
\t\t\t"current_served_at": None,
\t\t\t"blurs": cint(att.blurs) + cint(blurs),
\t\t},
\t\tupdate_modified=False,
\t)
\tfrappe.db.commit()
\treturn proctored_next(attempt)


@frappe.whitelist()
def quiz_forensics(limit=30):
\t"""SM-only: recent timed attempts with the timing pattern — the AI
\tsignature detector (uniform elapsed + blur count tell the story)."""
\t_staff_only()
\tif "System Manager" not in frappe.get_roles():
\t\tfrappe.throw(_("Managers only."), frappe.PermissionError)
\trows = frappe.get_all(
\t\t"Duty Quiz Attempt",
\t\tfilters={"mode": "Timed", "finished_at": ["is", "set"]},
\t\tfields=["name", "user", "module", "score", "passed", "blurs", "results", "finished_at"],
\t\torder_by="finished_at desc",
\t\tlimit=cint(limit) or 30,
\t)
\tout = []
\tfor a in rows:
\t\tres = json.loads(a.results or "[]")
\t\ttimes = [r["elapsed"] for r in res if r.get("elapsed") is not None]
\t\tavg = round(sum(times) / len(times), 1) if times else 0
\t\tspread = round(max(times) - min(times), 1) if times else 0
\t\tout.append({
\t\t\t"user": frappe.utils.get_fullname(a.user),
\t\t\t"module": frappe.db.get_value("Duty Training Module", a.module, "title") or a.module,
\t\t\t"when": str(a.finished_at)[:16],
\t\t\t"score": a.score,
\t\t\t"passed": a.passed,
\t\t\t"blurs": cint(a.blurs),
\t\t\t"avg_s": avg,
\t\t\t"spread_s": spread,
\t\t\t"timeouts": sum(1 for r in res if r.get("timed_out")),
\t\t\t"times": times,
\t\t\t"flag": 1 if (times and spread < 8 and avg > 10) or cint(a.blurs) >= len(res) else 0,
\t\t})
\treturn out'''

# --- 2. JS: timed branch in my_quiz_dialog ----------------------------------
JQ_OLD = '''\t\t\tcallback: (r) => {
\t\t\t\tconst t = r.message;
\t\t\t\tif (!t) return;
\t\t\t\tconst d = new frappe.ui.Dialog({ title: `📝 ${__("Assessment")} — 10 ${__("questions")}`, size: "large" });'''
JQ_NEW = '''\t\t\tcallback: (r) => {
\t\t\t\tconst t = r.message;
\t\t\t\tif (!t) return;
\t\t\t\tif (t.timed) return this.proctored_runner(t);
\t\t\t\tconst d = new frappe.ui.Dialog({ title: `📝 ${__("Assessment")} — 10 ${__("questions")}`, size: "large" });'''

# --- 3. JS: the proctored runner, before my_quiz_dialog ---------------------
JR_OLD = '\tmy_quiz_dialog(record) {'
JR_NEW = '''\tproctored_runner(t) {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst d = new frappe.ui.Dialog({ title: `⏱ ${__("Timed assessment")} — ${t.size} ${__("questions")}`, size: "large", static: true });
\t\tlet blurs = 0, timer = null, deadline = 0;
\t\tconst onBlur = () => { blurs += 1; };
\t\t$(window).on("blur.duty_exam", onBlur);
\t\tconst cleanup = () => { clearInterval(timer); $(window).off("blur.duty_exam"); };
\t\td.$wrapper.on("hidden.bs.modal", cleanup);
\t\tconst finish = (R) => {
\t\t\tcleanup();
\t\t\t$(d.body).html(`
\t\t\t\t<div style="text-align:center;padding:14px 6px">
\t\t\t\t\t<div style="font-size:40px">${R.passed ? "🎉" : "😞"}</div>
\t\t\t\t\t<h4>${R.passed ? __("Passed") : __("Not this time")} — ${R.score}% <span class="text-muted" style="font-size:13px">(${__("pass mark")} ${R.pass_mark}%)</span></h4>
\t\t\t\t\t${R.timeouts ? `<p style="color:#B45309;font-weight:700">⏱ ${R.timeouts} ${__("question(s) timed out")}</p>` : ""}
\t\t\t\t\t${(R.wrong || []).length ? `<div style="text-align:left;margin-top:10px"><b>${__("Review these topics")}:</b><ul>${R.wrong.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>` : ""}
\t\t\t\t\t${R.newly_certified ? `<p style="color:#0E8A63;font-weight:700">🎓 ${__("Certified!")}</p>` : ""}
\t\t\t\t</div>`);
\t\t\td.set_primary_action(__("Close"), () => d.hide());
\t\t};
\t\tconst show = (Q) => {
\t\t\tif (Q.done) return finish(Q);
\t\t\tdeadline = Date.now() + Q.seconds * 1000;
\t\t\t$(d.body).html(`
\t\t\t\t<div class="duty-ex-top"><b>${__("Question")} ${Q.idx + 1} / ${Q.size}</b><span class="duty-ex-clock">${Q.seconds}s</span></div>
\t\t\t\t<div class="duty-ex-bar"><span style="width:100%"></span></div>
\t\t\t\t<div class="duty-ex-q">${esc(Q.question)}</div>
\t\t\t\t${Q.options.map((o, j) => `<label class="duty-ex-opt"><input type="radio" name="duty-ex" value="${j}"><span>${esc(o)}</span></label>`).join("")}
\t\t\t\t<p class="text-muted" style="font-size:11.5px;margin-top:8px">${__("One question at a time. No going back. Unanswered when the clock hits zero counts as wrong.")}</p>
\t\t\t`);
\t\t\tclearInterval(timer);
\t\t\ttimer = setInterval(() => {
\t\t\t\tconst left = Math.max(0, deadline - Date.now());
\t\t\t\tconst pct = (left / (Q.seconds * 1000)) * 100;
\t\t\t\t$(d.body).find(".duty-ex-clock").text(`${Math.ceil(left / 1000)}s`);
\t\t\t\t$(d.body).find(".duty-ex-bar span").css("width", pct + "%").toggleClass("low", pct < 25);
\t\t\t\tif (left <= 0) submit(null);
\t\t\t}, 250);
\t\t\td.set_primary_action(__("Submit answer"), () => {
\t\t\t\tconst v = $(d.body).find("input[name=duty-ex]:checked").val();
\t\t\t\tsubmit(v === undefined ? null : v);
\t\t\t});
\t\t};
\t\tconst submit = (choice) => {
\t\t\tclearInterval(timer);
\t\t\tconst b = blurs; blurs = 0;
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.client_room.proctored_answer",
\t\t\t\targs: { attempt: t.attempt, choice: choice, blurs: b },
\t\t\t\tcallback: (r) => r.message && show(r.message),
\t\t\t});
\t\t};
\t\t// rules screen first — the announcement is part of the deterrent
\t\t$(d.body).html(`
\t\t\t<div style="padding:6px 2px">
\t\t\t\t<h4>⏱ ${__("This is a timed assessment")}</h4>
\t\t\t\t<ul style="font-size:13.5px;line-height:1.7">
\t\t\t\t\t<li>${__("Questions appear one at a time — {0} seconds each.", [t.seconds])}</li>
\t\t\t\t\t<li>${__("Once you answer (or time runs out) you move on. There is no going back.")}</li>
\t\t\t\t\t<li>${__("Your time per question and any switching away from this tab are recorded.")}</li>
\t\t\t\t</ul>
\t\t\t</div>`);
\t\td.set_primary_action(`▶ ${__("Start")}`, () => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.client_room.proctored_next",
\t\t\t\targs: { attempt: t.attempt },
\t\t\t\tcallback: (r) => r.message && show(r.message),
\t\t\t});
\t\t});
\t\td.show();
\t}

\tmy_quiz_dialog(record) {'''

# --- 4. JS: SM forensics button in Team training dialog ---------------------
JF_OLD = '''\t\t\t\tconst d = new frappe.ui.Dialog({ title: __("🎓 Team training & certification"), size: "extra-large" });'''
JF_NEW = '''\t\t\t\tconst d = new frappe.ui.Dialog({ title: __("🎓 Team training & certification"), size: "extra-large" });
\t\t\t\tif (frappe.user.has_role("System Manager")) {
\t\t\t\t\td.set_secondary_action_label(`⏱ ${__("Exam forensics")}`);
\t\t\t\t\td.set_secondary_action(() => {
\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\tmethod: "duty_board.client_room.quiz_forensics",
\t\t\t\t\t\t\tcallback: (fr) => {
\t\t\t\t\t\t\t\tconst rows = fr.message || [];
\t\t\t\t\t\t\t\tconst fd = new frappe.ui.Dialog({ title: `⏱ ${__("Timed-exam forensics")}`, size: "extra-large" });
\t\t\t\t\t\t\t\t$(fd.body).html(rows.length ? `
\t\t\t\t\t\t\t\t\t<table class="table table-sm" style="font-size:12px">
\t\t\t\t\t\t\t\t\t<tr><th>${__("Person")}</th><th>${__("Module")}</th><th>${__("When")}</th><th>${__("Score")}</th><th>${__("Avg s/q")}</th><th>${__("Spread")}</th><th>${__("Timeouts")}</th><th>${__("Tab-outs")}</th><th></th></tr>
\t\t\t\t\t\t\t\t\t${rows.map((x) => `<tr class="${x.flag ? "duty-fx-flag" : ""}">
\t\t\t\t\t\t\t\t\t\t<td><b>${frappe.utils.escape_html(x.user)}</b></td><td>${frappe.utils.escape_html(x.module)}</td><td>${x.when}</td>
\t\t\t\t\t\t\t\t\t\t<td>${x.score}%${x.passed ? " ✅" : ""}</td><td>${x.avg_s}s</td><td title="${(x.times || []).join(", ")}s">${x.spread_s}s</td>
\t\t\t\t\t\t\t\t\t\t<td>${x.timeouts || 0}</td><td>${x.blurs || 0}</td><td>${x.flag ? `<b style="color:#C2410C">⚠ ${__("review")}</b>` : ""}</td>
\t\t\t\t\t\t\t\t\t</tr>`).join("")}
\t\t\t\t\t\t\t\t\t</table>
\t\t\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("⚠ = uniform answer times (low spread at unhurried pace) or tab-outs on nearly every question — the lookup/AI signature. Hover Spread for per-question times. A flag is a conversation, not a verdict.")}</p>`
\t\t\t\t\t\t\t\t\t: `<p class="text-muted">${__("No timed attempts yet.")}</p>`);
\t\t\t\t\t\t\t\tfd.show();
\t\t\t\t\t\t\t},
\t\t\t\t\t\t});
\t\t\t\t\t});
\t\t\t\t}'''

# --- 5. CSS ------------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-lv-ask .duty-rm-rep-sel { max-width: 110px; }'
CSS_NEW = '''\t\t\t.duty-lv-ask .duty-rm-rep-sel { max-width: 110px; }
\t\t\t.duty-ex-top { display: flex; align-items: baseline; margin-bottom: 4px; }
\t\t\t.duty-ex-clock { margin-left: auto; font-weight: 800; font-size: 18px; color: #0F5C55; }
\t\t\t.duty-ex-bar { height: 6px; border-radius: 4px; background: #EEF2F1; overflow: hidden; margin-bottom: 12px; }
\t\t\t.duty-ex-bar span { display: block; height: 100%; background: #0E8A63; transition: width .25s linear; }
\t\t\t.duty-ex-bar span.low { background: #C2410C; }
\t\t\t.duty-ex-q { font-weight: 700; font-size: 15px; margin-bottom: 10px; }
\t\t\t.duty-ex-opt { display: flex; gap: 10px; align-items: baseline; padding: 8px 10px; border: 1px solid #E4EAE8; border-radius: 10px; margin-bottom: 6px; cursor: pointer; font-weight: 400; }
\t\t\t.duty-ex-opt:hover { background: #F4F7F6; }
\t\t\t.duty-fx-flag td { background: #FEF6F0; }'''


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
    for p in (INIT, JS, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def proctored_next(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.77.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.77.0.")

    checks = [
        (CR, MS_OLD, "quiz start branch", 1), (JS, JQ_OLD, "timed branch", 1),
        (JS, JR_OLD, "runner", 1), (JF_OLD in files[JS] and 1 or 0, JF_OLD, "forensics", 1),
        (JS, CSS_OLD, "css", 1),
    ]
    problems = []
    for f, o, label, n in [(CR, MS_OLD, "quiz start branch", 1), (JS, JQ_OLD, "timed branch", 1), (JS, JR_OLD, "runner", 1), (JS, JF_OLD, "forensics hook", 1), (JS, CSS_OLD, "css", 1)]:
        if files[f].count(o) != n:
            problems.append(f"  [{files[f].count(o)} != {n}] {label}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All 5 anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, TMDT), [
        {"fieldname": "timed_mode", "fieldtype": "Check", "label": "Timed (proctored) exam"},
        {"fieldname": "seconds_per_question", "fieldtype": "Int", "label": "Seconds per Question", "default": "60"},
        {"fieldname": "questions_served", "fieldtype": "Int", "label": "Questions Served (0 = default)"},
    ])
    add_fields(os.path.join(root, QADT), [
        {"fieldname": "mode", "fieldtype": "Data", "label": "Mode"},
        {"fieldname": "current_idx", "fieldtype": "Int", "label": "Current Index"},
        {"fieldname": "current_served_at", "fieldtype": "Datetime", "label": "Current Served At"},
        {"fieldname": "results", "fieldtype": "Long Text", "label": "Results JSON"},
        {"fieldname": "blurs", "fieldtype": "Int", "label": "Focus Losses"},
    ])
    print("  module + attempt fields added")

    cr = files[CR].replace(MS_OLD, MS_NEW, 1)
    if "get_datetime" not in cr.split("\n\n")[0] and "from frappe.utils import" in cr:
        cr = cr.replace(
            "from frappe.utils import", "from frappe.utils import get_datetime,", 1
        ) if "get_datetime" not in cr[:2000] else cr
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(cr)
    print("  client_room.py: timed branch + proctored endpoints + forensics")

    js = files[JS]
    for o, n in [(JQ_OLD, JQ_NEW), (JR_OLD, JR_NEW), (JF_OLD, JF_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: timed runner + forensics dialog")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.77.0"', '"3.78.0"'))
    print("wrote __init__.py -> 3.78.0")


if __name__ == "__main__":
    main()
