#!/usr/bin/env python3
"""Duty Board v3.209.0 — THE SPONSOR SCORECARD.

Certificates go to the learner. The scorecard goes to whoever signed the
invoice, and it is the thing that earns the next order: pass rate, score
distribution, the areas the group is weakest in, and a named roster. "Your
stock team scored 54% on variance investigation" is the proposal for the
next engagement.

The v3.208.0 cohort back-link makes this computable without guessing: every
result is reached through Duty Training Record.cohort, so nothing from another
room or another intake can contaminate a group's numbers.

cohort.py gains
  _attempt_pairs   — (question, correct?) from any finished attempt, timed or
                     classic, so both exam styles aggregate the same way
  cohort_scorecard — per course: sat / passed / pass rate / average best;
                     per person: attendance, completion, first and best score;
                     distribution buckets; weakest areas from FIRST attempts
                     only, since retakes are contaminated by having already
                     seen the paper; and an integrity summary (timeouts, focus
                     losses, flagged attempts) for staff eyes
  cohort_scorecard_publish — renders the sponsor PDF, files it on the client's
                     shelf and narrates it into the room

The published PDF deliberately carries results and areas, not the integrity
forensics: aggregate suspicion is a conversation to have with the sponsor, not
a paragraph to hand them about named individuals.

Staff UI: 📊 Scorecard on the cohort detail, with the report on screen and a
publish action.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema, no migrate. Anchored, idempotent.
Requires v3.208.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
COHORT = "duty_board/cohort.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv


PY_OLD = '''@frappe.whitelist()
def cohort_close(name):'''

PY_NEW = '''# ---------------- the sponsor scorecard ----------------


def _attempt_pairs(att):
\t"""[(question, correct?)] for a finished attempt, whichever exam style it
\twas. Timed attempts already carry per-question outcomes; classic papers
\tare recomputed from the served order and the answer sheet, using exactly
\tthe arithmetic that scored them."""
\timport json

\tif att.get("results"):
\t\ttry:
\t\t\treturn [(r["q"], bool(r.get("ok"))) for r in json.loads(att["results"])]
\t\texcept Exception:
\t\t\treturn []
\ttry:
\t\tserved = json.loads(att.get("served") or "[]")
\t\tanswers = json.loads(att.get("answers") or "{}")
\texcept Exception:
\t\treturn []
\tif not served:
\t\treturn []
\tcorrect = {
\t\tq.name: "ABCD".index(q.correct)
\t\tfor q in frappe.get_all(
\t\t\t"Duty Quiz Question",
\t\t\tfilters={"name": ["in", [s["q"] for s in served]]},
\t\t\tfields=["name", "correct"],
\t\t)
\t\tif q.correct
\t}
\tout = []
\tfor s in served:
\t\tchosen = answers.get(s["q"])
\t\tchosen = cint(chosen) if chosen is not None else -1
\t\treal = s["order"][chosen] if 0 <= chosen < 4 else -1
\t\tout.append((s["q"], real == correct.get(s["q"])))
\treturn out


def _bucket(score):
\tif score >= 85:
\t\treturn "85–100"
\tif score >= 70:
\t\treturn "70–84"
\tif score >= 50:
\t\treturn "50–69"
\treturn "Below 50"


@frappe.whitelist()
def cohort_scorecard(name):
\t"""The group's result. Reached entirely through the cohort back-link."""
\tcoh = _cohort(name)
\tmods = _modules(coh)
\ttitles = {
\t\tm.name: m.title
\t\tfor m in frappe.get_all(
\t\t\t"Duty Training Module", filters={"name": ["in", mods or [""]]},
\t\t\tfields=["name", "title"],
\t\t)
\t}
\trecs = frappe.get_all(
\t\t"Duty Training Record",
\t\tfilters={"cohort": coh.name},
\t\tfields=["name", "module", "trainee", "trainee_name", "status"],
\t)
\tattended = {m.trainee for m in coh.members if cint(m.attended)}
\tby_rec = {r.name: r for r in recs}
\tattempts = []
\tif recs:
\t\tattempts = frappe.get_all(
\t\t\t"Duty Quiz Attempt",
\t\t\tfilters={"record": ["in", list(by_rec)], "finished_at": ["is", "set"]},
\t\t\tfields=[
\t\t\t\t"name", "record", "module", "user", "score", "passed",
\t\t\t\t"finished_at", "served", "answers", "results", "blurs", "mode",
\t\t\t],
\t\t\torder_by="finished_at asc",
\t\t)

\t# ---- per person, per course
\tfirst_of, best_of, tries_of = {}, {}, {}
\tfor a in attempts:
\t\tkey = (a.user, a.module)
\t\tfirst_of.setdefault(key, a)
\t\ttries_of[key] = tries_of.get(key, 0) + 1
\t\tif a.score > best_of.get(key, {}).get("score", -1):
\t\t\tbest_of[key] = a

\tpeople = []
\tfor m in coh.members:
\t\trows = []
\t\tfor mod in mods:
\t\t\trec = next(
\t\t\t\t(r for r in recs if r.trainee == m.trainee and r.module == mod), None
\t\t\t)
\t\t\tkey = (m.trainee, mod)
\t\t\tbest = best_of.get(key)
\t\t\tfirst = first_of.get(key)
\t\t\trows.append({
\t\t\t\t"module": mod,
\t\t\t\t"title": titles.get(mod, mod),
\t\t\t\t"enrolled": bool(rec),
\t\t\t\t"complete": bool(rec and rec.status == "Completed"),
\t\t\t\t"attempts": tries_of.get(key, 0),
\t\t\t\t"first": cint(first.score) if first else None,
\t\t\t\t"best": cint(best.score) if best else None,
\t\t\t\t"passed": bool(best and cint(best.passed)),
\t\t\t})
\t\tsat = [r for r in rows if r["attempts"]]
\t\tpeople.append({
\t\t\t"trainee": m.trainee,
\t\t\t"trainee_name": m.trainee_name or frappe.utils.get_fullname(m.trainee),
\t\t\t"attended": m.trainee in attended,
\t\t\t"courses": rows,
\t\t\t"complete": sum(1 for r in rows if r["complete"]),
\t\t\t"total": len(mods),
\t\t\t"average": round(sum(r["best"] for r in sat) / len(sat)) if sat else None,
\t\t})
\tpeople.sort(key=lambda p: (-(p["average"] if p["average"] is not None else -1), p["trainee_name"]))

\t# ---- per course
\tcourses = []
\tfor mod in mods:
\t\tbests = [
\t\t\tr["best"] for p in people for r in p["courses"]
\t\t\tif r["module"] == mod and r["best"] is not None
\t\t]
\t\tpassed = sum(
\t\t\t1 for p in people for r in p["courses"] if r["module"] == mod and r["passed"]
\t\t)
\t\tcourses.append({
\t\t\t"module": mod,
\t\t\t"title": titles.get(mod, mod),
\t\t\t"sat": len(bests),
\t\t\t"passed": passed,
\t\t\t"pass_rate": round(passed * 100 / len(bests)) if bests else None,
\t\t\t"average": round(sum(bests) / len(bests)) if bests else None,
\t\t})

\t# ---- distribution over every best score in the cohort
\tbuckets = {"85–100": 0, "70–84": 0, "50–69": 0, "Below 50": 0}
\tall_best = [
\t\tr["best"] for p in people for r in p["courses"] if r["best"] is not None
\t]
\tfor s in all_best:
\t\tbuckets[_bucket(s)] += 1

\t# ---- weakest areas, from FIRST attempts only
\tagg = {}
\tfirsts = list(first_of.values())
\tqids = set()
\tpairs_by_attempt = {}
\tfor a in firsts:
\t\tpairs = _attempt_pairs(a)
\t\tpairs_by_attempt[a.name] = pairs
\t\tqids.update(q for q, _ok in pairs)
\ttopics = {
\t\tq.name: (q.topic or "").strip()
\t\tfor q in frappe.get_all(
\t\t\t"Duty Quiz Question", filters={"name": ["in", list(qids) or [""]]},
\t\t\tfields=["name", "topic"],
\t\t)
\t}
\thas_topics = any(topics.values())
\tfor pairs in pairs_by_attempt.values():
\t\tfor q, ok in pairs:
\t\t\tt = topics.get(q) or ""
\t\t\tif not t:
\t\t\t\tcontinue
\t\t\trow = agg.setdefault(t, {"topic": t, "right": 0, "total": 0})
\t\t\trow["total"] += 1
\t\t\tif ok:
\t\t\t\trow["right"] += 1
\tareas = sorted(
\t\t({**r, "pct": round(r["right"] * 100 / r["total"])} for r in agg.values()),
\t\tkey=lambda r: (r["pct"], r["topic"]),
\t)

\t# ---- integrity summary (staff view only; never printed for the sponsor)
\ttimed = [a for a in attempts if (a.mode or "") == "Timed"]
\ttimeouts = 0
\tfor a in timed:
\t\ttry:
\t\t\timport json as _j

\t\t\ttimeouts += sum(1 for r in _j.loads(a.results or "[]") if r.get("timed_out"))
\t\texcept Exception:
\t\t\tpass
\tblurs = sum(cint(a.blurs) for a in timed)

\tsat_people = sum(1 for p in people if p["average"] is not None)
\treturn {
\t\t"cohort": coh.name,
\t\t"title": coh.title,
\t\t"room": coh.room,
\t\t"customer": frappe.db.get_value("Client Room", coh.room, "customer") or coh.room,
\t\t"status": coh.status,
\t\t"facilitator": frappe.utils.get_fullname(coh.facilitator) if coh.facilitator else None,
\t\t"session_on": str(coh.session_on) if coh.session_on else None,
\t\t"opens_on": str(coh.opens_on) if coh.opens_on else None,
\t\t"closes_on": str(coh.closes_on) if coh.closes_on else None,
\t\t"members": len(coh.members),
\t\t"attended": len(attended),
\t\t"sat": sat_people,
\t\t"courses": courses,
\t\t"people": people,
\t\t"buckets": [{"band": b, "n": buckets[b]} for b in ("85–100", "70–84", "50–69", "Below 50")],
\t\t"average": round(sum(all_best) / len(all_best)) if all_best else None,
\t\t"pass_rate": (
\t\t\tround(sum(c["passed"] for c in courses) * 100 / sum(c["sat"] for c in courses))
\t\t\tif sum(c["sat"] for c in courses) else None
\t\t),
\t\t"areas": areas,
\t\t"has_topics": has_topics,
\t\t"integrity": {"timed": len(timed), "timeouts": timeouts, "blurs": blurs},
\t}


def _pct_bar(pct, colour):
\treturn (
\t\t'<div style="height:8px;background:#E9EFEC;border-radius:99px;overflow:hidden;min-width:90px">'
\t\t'<div style="height:8px;width:%s%%;background:%s"></div></div>' % (pct, colour)
\t)


def _scorecard_html(sc):
\tesc = frappe.utils.escape_html
\tdef band(p):
\t\treturn "#0E8A63" if p >= 70 else ("#C99A2E" if p >= 50 else "#C2410C")
\tcourse_rows = "".join(
\t\t"<tr><td>%s</td><td style='text-align:center'>%s</td><td style='text-align:center'>%s</td>"
\t\t"<td style='text-align:center'>%s</td><td style='text-align:center'>%s</td></tr>"
\t\t% (
\t\t\tesc(c["title"]), c["sat"], c["passed"],
\t\t\t("%s%%" % c["pass_rate"]) if c["pass_rate"] is not None else "—",
\t\t\t("%s%%" % c["average"]) if c["average"] is not None else "—",
\t\t)
\t\tfor c in sc["courses"]
\t)
\tarea_rows = "".join(
\t\t"<tr><td>%s</td><td style='width:46%%'>%s</td><td style='text-align:right'>%s%% (%s/%s)</td></tr>"
\t\t% (esc(a["topic"]), _pct_bar(a["pct"], band(a["pct"])), a["pct"], a["right"], a["total"])
\t\tfor a in sc["areas"][:8]
\t)
\tpeople_rows = "".join(
\t\t"<tr><td>%s</td><td style='text-align:center'>%s</td><td style='text-align:center'>%s of %s</td>"
\t\t"<td style='text-align:center'>%s</td></tr>"
\t\t% (
\t\t\tesc(p["trainee_name"]),
\t\t\t"Yes" if p["attended"] else "—",
\t\t\tp["complete"], p["total"],
\t\t\t("%s%%" % p["average"]) if p["average"] is not None else "did not sit",
\t\t)
\t\tfor p in sc["people"]
\t)
\tdist = "".join(
\t\t"<tr><td>%s</td><td style='text-align:right'>%s</td></tr>" % (b["band"], b["n"])
\t\tfor b in sc["buckets"]
\t)
\tareas_block = (
\t\t"<h2>Where the group is weakest</h2>"
\t\t"<p class=note>Measured on first attempts only. A retake is taken by someone "
\t\t"who has already seen the paper, so it flatters the score without proving the "
\t\t"understanding.</p>"
\t\t"<table>%s</table>" % area_rows
\t) if sc["areas"] else ""
\treturn """<html><head><meta charset="utf-8"><style>
@page {{ size: A4 portrait; margin: 18mm 16mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #16211F; font-size: 11.5px; }}
h1 {{ font-size: 21px; margin: 0 0 2px; color: #0A473F; }}
h2 {{ font-size: 13px; margin: 22px 0 7px; color: #0A473F;
\tborder-bottom: 1px solid #DCE4E1; padding-bottom: 4px; }}
.sub {{ color: #6B7C77; font-size: 11px; margin-bottom: 16px; }}
.tiles {{ width: 100%; border-collapse: separate; border-spacing: 8px 0; }}
.tiles td {{ background: #F4F7F6; border-radius: 8px; padding: 10px 12px; width: 25%; }}
.tiles b {{ display: block; font-size: 22px; color: #0A473F; }}
.tiles span {{ font-size: 10px; color: #6B7C77; text-transform: uppercase; letter-spacing: 1px; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .8px;
\tcolor: #6B7C77; border-bottom: 1px solid #DCE4E1; padding: 5px 4px; }}
td {{ padding: 6px 4px; border-bottom: 1px solid #F0F4F2; vertical-align: middle; }}
.note {{ color: #6B7C77; font-size: 10.5px; margin: 4px 0 8px; }}
.foot {{ margin-top: 26px; color: #6B7C77; font-size: 10px;
\tborder-top: 1px solid #DCE4E1; padding-top: 8px; }}
</style></head><body>
<h1>{title}</h1>
<div class="sub">{customer} &middot; training scorecard &middot; issued {issued}{fac}</div>
<table class="tiles"><tr>
\t<td><b>{attended}/{members}</b><span>attended</span></td>
\t<td><b>{sat}</b><span>sat the assessment</span></td>
\t<td><b>{pass_rate}</b><span>pass rate</span></td>
\t<td><b>{average}</b><span>average score</span></td>
</tr></table>
<h2>By course</h2>
<table><tr><th>Course</th><th style="text-align:center">Sat</th><th style="text-align:center">Passed</th>
<th style="text-align:center">Pass rate</th><th style="text-align:center">Average</th></tr>{course_rows}</table>
{areas_block}
<h2>Score distribution</h2>
<table><tr><th>Band</th><th style="text-align:right">Results</th></tr>{dist}</table>
<h2>Roster</h2>
<table><tr><th>Name</th><th style="text-align:center">Session</th>
<th style="text-align:center">Courses complete</th><th style="text-align:center">Average</th></tr>{people_rows}</table>
<div class="foot">Assessments are proctored: questions are drawn at random from a larger bank,
served one at a time under a per-question time limit, and every result is recorded against a
verifiable certificate serial. Prepared by Xlevel Retail Systems Ltd &middot; CloudERP.One Academy.</div>
</body></html>""".format(
\t\ttitle=esc(sc["title"]),
\t\tcustomer=esc(sc["customer"]),
\t\tissued=frappe.utils.format_date(today(), "d MMMM yyyy"),
\t\tfac=(" &middot; facilitated by %s" % esc(sc["facilitator"])) if sc["facilitator"] else "",
\t\tattended=sc["attended"], members=sc["members"], sat=sc["sat"],
\t\tpass_rate=("%s%%" % sc["pass_rate"]) if sc["pass_rate"] is not None else "—",
\t\taverage=("%s%%" % sc["average"]) if sc["average"] is not None else "—",
\t\tcourse_rows=course_rows, areas_block=areas_block, dist=dist, people_rows=people_rows,
\t)


@frappe.whitelist()
def cohort_scorecard_publish(name):
\t"""Render the sponsor PDF, file it on the client's shelf, narrate it."""
\tfrom frappe.utils.pdf import get_pdf

\tsc = cohort_scorecard(name)
\tif not sc["sat"]:
\t\tfrappe.throw(_("Nobody has sat the assessment yet — there is no result to publish."))
\tpdf = get_pdf(_scorecard_html(sc))
\tsafe = "".join(ch if ch.isalnum() else "_" for ch in sc["title"])[:48]
\tfname = "Training_Scorecard_%s_%s.pdf" % (safe, sc["cohort"])
\tf = frappe.get_doc(
\t\t{"doctype": "File", "file_name": fname, "content": pdf, "is_private": 1}
\t).insert(ignore_permissions=True)
\tshelf = frappe.get_doc({
\t\t"doctype": "Client Shelf Doc",
\t\t"room": sc["room"],
\t\t"title": _("Training scorecard — {0}").format(sc["title"]),
\t\t"category": _("Training"),
\t\t"file_url": f.file_url,
\t\t"file_name": fname,
\t\t"active": 1,
\t}).insert(ignore_permissions=True)
\tfrappe.db.commit()
\ttry:
\t\tfrom duty_board.client_room import _post

\t\t_post(
\t\t\tfrappe.get_doc("Client Room", sc["room"]),
\t\t\t_("📊 Training scorecard published: “{0}” — {1} of {2} sat, {3} pass rate. It is on your Documents shelf.").format(
\t\t\t\tsc["title"], sc["sat"], sc["members"],
\t\t\t\t("%s%%" % sc["pass_rate"]) if sc["pass_rate"] is not None else "—",
\t\t\t),
\t\t)
\texcept Exception:
\t\tfrappe.log_error(frappe.get_traceback(), "duty_board scorecard narration")
\treturn {"shelf": shelf.name, "file_url": f.file_url, "file_name": fname}


@frappe.whitelist()
def cohort_close(name):'''

IMPORT_OLD = '''from frappe.utils import cint, get_datetime, now_datetime'''
IMPORT_NEW = '''from frappe.utils import cint, get_datetime, now_datetime, today'''


JS_OLD = '''\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-primary duty-coh-enrol">\\u{1F393} ${__("Enrol everyone")}</button>'''

JS_NEW = '''\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-primary duty-coh-enrol">\\u{1F393} ${__("Enrol everyone")}</button>
\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-default duty-coh-score">\\u{1F4CA} ${__("Scorecard")}</button>'''

JS_H_OLD = '''\t\t\t\t$(d.body).find(".duty-coh-back").on("click", list);'''

JS_H_NEW = '''\t\t\t\t$(d.body).find(".duty-coh-back").on("click", list);
\t\t\t\t$(d.body).find(".duty-coh-score").on("click", () => scorecard(name));'''

JS_SC_OLD = '''\t\tlist();
\t\td.show();
\t}

\tteam_training_dialog() {'''

JS_SC_NEW = '''\t\tconst pct = (v) => (v === null || v === undefined ? "\\u2014" : `${v}%`);
\t\tconst scorecard = (name) =>
\t\t\tcall("cohort_scorecard", { name: name }, (s) => {
\t\t\t\tconst band = (p) => (p >= 70 ? "#0E8A63" : p >= 50 ? "#C99A2E" : "#C2410C");
\t\t\t\t$(d.body).html(`
\t\t\t\t\t<a class="duty-coh-back2" style="cursor:pointer;font-size:12.5px">\\u2190 ${__("Back to cohort")}</a>
\t\t\t\t\t<h4 style="margin:8px 0 2px">\\u{1F4CA} ${esc(s.title)}</h4>
\t\t\t\t\t<div class="text-muted" style="font-size:12px;margin-bottom:12px">${esc(s.customer)} \\u00b7 ${s.attended}/${s.members} ${__("attended")} \\u00b7 ${s.sat} ${__("sat")} \\u00b7 ${__("pass rate")} ${pct(s.pass_rate)} \\u00b7 ${__("average")} ${pct(s.average)}</div>
\t\t\t\t\t<div class="duty-lead-section">${__("By course")}</div>
\t\t\t\t\t<table class="table table-sm" style="font-size:12px">
\t\t\t\t\t\t<tr><th>${__("Course")}</th><th>${__("Sat")}</th><th>${__("Passed")}</th><th>${__("Pass rate")}</th><th>${__("Average")}</th></tr>
\t\t\t\t\t\t${s.courses.map((c) => `<tr><td>${esc(c.title)}</td><td>${c.sat}</td><td>${c.passed}</td><td>${pct(c.pass_rate)}</td><td>${pct(c.average)}</td></tr>`).join("")}
\t\t\t\t\t</table>
\t\t\t\t\t${s.areas.length
\t\t\t\t\t\t? `<div class="duty-lead-section">${__("Weakest areas")} <span class="text-muted" style="font-weight:400;font-size:11.5px">\\u00b7 ${__("first attempts only")}</span></div>
\t\t\t\t\t\t${s.areas.slice(0, 8).map((a) => `
\t\t\t\t\t\t<div style="display:flex;gap:10px;align-items:center;margin:5px 0;font-size:12px">
\t\t\t\t\t\t\t<span style="flex:0 0 38%">${esc(a.topic)}</span>
\t\t\t\t\t\t\t<span style="flex:1;height:8px;background:#E9EFEC;border-radius:99px;overflow:hidden"><i style="display:block;height:8px;width:${a.pct}%;background:${band(a.pct)}"></i></span>
\t\t\t\t\t\t\t<span class="text-muted" style="flex:0 0 80px;text-align:right">${a.pct}% (${a.right}/${a.total})</span>
\t\t\t\t\t\t</div>`).join("")}`
\t\t\t\t\t\t: `<p class="text-muted" style="font-size:12px;margin-top:10px">${__("No area breakdown yet — the question bank for these courses carries no topics. Add a Topic to each Duty Quiz Question and this fills in.")}</p>`}
\t\t\t\t\t<div class="duty-lead-section">${__("Roster")}</div>
\t\t\t\t\t<table class="table table-sm" style="font-size:12px">
\t\t\t\t\t\t<tr><th>${__("Name")}</th><th>${__("Session")}</th><th>${__("Complete")}</th><th>${__("Average")}</th></tr>
\t\t\t\t\t\t${s.people.map((p) => `<tr><td>${esc(p.trainee_name)}</td><td>${p.attended ? "\\u2713" : "\\u2014"}</td><td>${p.complete}/${p.total}</td><td>${p.average === null ? __("did not sit") : p.average + "%"}</td></tr>`).join("")}
\t\t\t\t\t</table>
\t\t\t\t\t<div class="text-muted" style="font-size:11.5px;margin-top:10px">\\u23F1 ${__("Integrity")}: ${s.integrity.timed} ${__("timed attempts")} \\u00b7 ${s.integrity.timeouts} ${__("timed out")} \\u00b7 ${s.integrity.blurs} ${__("focus losses")}. ${__("Staff view only — never printed for the client.")}</div>
\t\t\t\t\t<div style="display:flex;gap:8px;margin-top:14px">
\t\t\t\t\t\t<button type="button" class="btn btn-sm btn-primary duty-coh-pub">\\u{1F4E4} ${__("Publish to client's Documents")}</button>
\t\t\t\t\t</div>
\t\t\t\t`);
\t\t\t\t$(d.body).find(".duty-coh-back2").on("click", () => detail(name));
\t\t\t\t$(d.body).find(".duty-coh-pub").on("click", () =>
\t\t\t\t\tfrappe.confirm(__("Publish this scorecard to the client's Documents shelf and announce it in the room?"), () =>
\t\t\t\t\t\tcall("cohort_scorecard_publish", { name: name }, (res) => {
\t\t\t\t\t\t\tfrappe.show_alert({ message: __("Scorecard published"), indicator: "green" });
\t\t\t\t\t\t\tif (res && res.file_url) window.open(res.file_url, "_blank");
\t\t\t\t\t\t})));
\t\t\t});
\t\tlist();
\t\td.show();
\t}

\tteam_training_dialog() {'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, COHORT, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def cohort_scorecard(" in files[COHORT]:
        print("Already applied. Nothing to do.")
        return
    if '"3.208.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.208.0.")

    edits = [
        (COHORT, IMPORT_OLD, IMPORT_NEW, "cohort.py import today"),
        (COHORT, PY_OLD, PY_NEW, "scorecard engine + publish"),
        (JS, JS_OLD, JS_NEW, "Scorecard button"),
        (JS, JS_H_OLD, JS_H_NEW, "Scorecard handler"),
        (JS, JS_SC_OLD, JS_SC_NEW, "scorecard view"),
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
    for p in (COHORT, JS):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  cohort.py: scorecard engine, sponsor PDF, shelf publishing")
    print("  duty_board.js: scorecard view on the cohort detail")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.208.0"', '"3.209.0"'))
    print("wrote __init__.py -> 3.209.0")


if __name__ == "__main__":
    main()
