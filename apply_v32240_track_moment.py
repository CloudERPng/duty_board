#!/usr/bin/env python3
"""Duty Board v3.224.0 - A QUALIFICATION, NOT A PILE OF COURSES.

The last two from the review, both on the learner's side.

L4  Course cards were a flat grid. Eight loose cards read as a pile; the same
    eight grouped under their track, with a progress bar and "3 of 8
    complete", read as a qualification in progress - which is what the client
    actually bought. Ungrouped courses keep their own heading beneath.

L6  Finishing a course issued a certificate. Finishing a whole TRACK produced
    nothing distinct - no summary of what was achieved, and no suggestion of
    what to do next. That was the omission with the clearest commercial cost:
    it is the only moment where a second sale suggests itself to the person
    who has just proved the first one worked.

    Passing the last course of a track now opens an achievement view: what
    they covered with dates and per-course certificates, total study time, the
    verifiable serial, and one recommended next track - preferring one the
    client can already assign, falling back to one worth asking about.

    It also appears as "View achievement" on any completed track heading, so
    it is not a moment that has to be caught the first time.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.223.0.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


DUE_OLD = '\tdue = {\n\t\td.name: d.due_on'

DUE_NEW = '\ttrack_of = _tracks_by_module(room, user, my_modules)\n\tdue = {\n\t\td.name: d.due_on'

PAY_OLD = '\t\t\t"next_lesson": next_lesson.get(r.module) if r.trainee == user else None,'

PAY_NEW = '\t\t\t"next_lesson": next_lesson.get(r.module) if r.trainee == user else None,\n\t\t\t"track": track_of.get(r.module) if r.trainee == user else None,'

HELP_OLD = '@frappe.whitelist()\ndef client_pursue_track(track):'

HELP_NEW = 'def _tracks_by_module(room, user, modules):\n\t"""module -> the track it belongs to for this learner, resolved once.\n\n\tThe course cards group under it, so eight loose courses read as a\n\tqualification in progress rather than a pile."""\n\tif not modules:\n\t\treturn {}\n\tout = {}\n\tfor m in modules:\n\t\tt = _track_for_module(room, user, m)\n\t\tif t:\n\t\t\tout[m] = {"title": t["title"], "position": t["position"], "total": t["total"]}\n\treturn out\n\n\ndef _track_just_completed(room, user, module):\n\t"""Did finishing this course finish a whole track?\n\n\tModule completion is its own event and already issues a certificate. A\n\ttrack finishing is the larger moment and had none — no summary of what was\n\tachieved and, more to the point commercially, no suggestion of what to do\n\tnext. This is the only place a second sale suggests itself to the person who\n\thas just proved the first one worked."""\n\tfor p in frappe.get_all(\n\t\t"Duty Certification Track Module", filters={"module": module}, fields=["parent"]\n\t):\n\t\ttrack = frappe.db.get_value(\n\t\t\t"Duty Certification Track", p.parent,\n\t\t\t["name", "title", "active", "audience"], as_dict=True,\n\t\t)\n\t\tif not track or not cint(track.active) or track.audience != "Client":\n\t\t\tcontinue\n\t\tmods = frappe.get_all(\n\t\t\t"Duty Certification Track Module", filters={"parent": p.parent}, pluck="module"\n\t\t)\n\t\tif not mods:\n\t\t\tcontinue\n\t\tdone = frappe.db.count(\n\t\t\t"Duty Training Record",\n\t\t\t{"room": room.name, "trainee": user, "module": ["in", mods], "status": "Completed"},\n\t\t)\n\t\tif done >= len(mods):\n\t\t\treturn {"track": track.name, "title": track.title}\n\treturn None\n\n\n@frappe.whitelist()\ndef client_track_summary(track):\n\t"""What they achieved, and what is next."""\n\troom = _learning_room()\n\tuser = frappe.session.user\n\tt = frappe.db.get_value(\n\t\t"Duty Certification Track", track, ["title", "product", "description"], as_dict=True\n\t)\n\tif not t:\n\t\tfrappe.throw(_("Not found."))\n\tmods = frappe.get_all(\n\t\t"Duty Certification Track Module", filters={"parent": track},\n\t\tpluck="module", order_by="idx asc",\n\t)\n\tcourses, minutes = [], 0\n\tfor m in mods:\n\t\trec = frappe.db.get_value(\n\t\t\t"Duty Training Record",\n\t\t\t{"room": room.name, "trainee": user, "module": m},\n\t\t\t["status", "completed_on", "certificate_shelf"], as_dict=True,\n\t\t) or frappe._dict()\n\t\tmins = sum(\n\t\t\tcint(l.est_minutes) or 5\n\t\t\tfor l in frappe.get_all("Duty Lesson", filters={"module": m}, fields=["est_minutes"])\n\t\t)\n\t\tminutes += mins\n\t\tcourses.append({\n\t\t\t"title": frappe.db.get_value("Duty Training Module", m, "title") or m,\n\t\t\t"done": rec.get("status") == "Completed",\n\t\t\t"completed_on": str(rec.get("completed_on"))[:10] if rec.get("completed_on") else None,\n\t\t\t"cert": rec.get("certificate_shelf"),\n\t\t\t"minutes": mins,\n\t\t})\n\tcert = frappe.db.get_value(\n\t\t"Duty Certificate",\n\t\t{"user": user, "track": track, "status": ["!=", "Revoked"]},\n\t\t["serial", "issued_on"], as_dict=True,\n\t)\n\t# what to do next: another track they can reach and have not begun\n\tnxt = None\n\ttry:\n\t\tfrom duty_board.academy import track_catalogue\n\n\t\tfor row in track_catalogue(room):\n\t\t\tif row["track"] == track:\n\t\t\t\tcontinue\n\t\t\tif not _on_track(room, user, row["track"]):\n\t\t\t\tnxt = {\n\t\t\t\t\t"track": row["track"], "title": row["title"],\n\t\t\t\t\t"courses": row["courses"], "assignable": row["assignable"],\n\t\t\t\t\t"description": row["description"],\n\t\t\t\t}\n\t\t\t\tif row["assignable"]:\n\t\t\t\t\tbreak\n\texcept Exception:\n\t\tnxt = None\n\treturn {\n\t\t"track": track,\n\t\t"title": t.title,\n\t\t"product": t.product,\n\t\t"description": t.description,\n\t\t"courses": courses,\n\t\t"complete": sum(1 for c in courses if c["done"]),\n\t\t"total": len(courses),\n\t\t"minutes": minutes,\n\t\t"serial": cert.serial if cert else None,\n\t\t"issued_on": str(cert.issued_on)[:10] if cert and cert.issued_on else None,\n\t\t"next": nxt,\n\t}\n\n\n@frappe.whitelist()\ndef client_pursue_track(track):'

SUB_OLD = '\t\t"newly_certified": newly_certified,\n\t}\n\n\n@frappe.whitelist()\ndef my_quiz_start(record):'

SUB_NEW = '\t\t"newly_certified": newly_certified,\n\t\t"track_done": _track_just_completed(\n\t\t\tfrappe.get_doc("Client Room", rec.room), frappe.session.user, rec.module\n\t\t) if newly_certified else None,\n\t}\n\n\n@frappe.whitelist()\ndef my_quiz_start(record):'

TF_OLD = '\t\t"newly_certified": newly_certified,\n\t}\n\n\n@frappe.whitelist()\ndef proctored_next(attempt):'

TF_NEW = '\t\t"newly_certified": newly_certified,\n\t\t"track_done": _track_just_completed(\n\t\t\tfrappe.get_doc("Client Room", rec.room), frappe.session.user, rec.module\n\t\t) if newly_certified else None,\n\t}\n\n\n@frappe.whitelist()\ndef proctored_next(attempt):'

CARDS_OLD = '(mine.length ? `<div class="lmsh">Your courses</div><div class="lmsgrid">${mine.map(courseCard).join("")}</div>` : "") +'

CARDS_NEW = '(mine.length ? groupedCourses(mine, courseCard) : "") +'

GRP_OLD = 'function pursueTrack(track) {'

GRP_NEW = 'function groupedCourses(mine, courseCard) {\n\t/* Eight loose cards read as a pile; the same eight under their track read\n\t   as a qualification in progress, which is what they are. */\n\tconst groups = new Map();\n\tmine.forEach((r) => {\n\t\tconst key = r.track ? r.track.title : "";\n\t\tif (!groups.has(key)) groups.set(key, []);\n\t\tgroups.get(key).push(r);\n\t});\n\tconst keyed = [...groups.entries()].sort((a, b) => (a[0] ? -1 : 1));\n\treturn keyed.map(([title, rows]) => {\n\t\trows.sort((a, b) => ((a.track ? a.track.position : 0) - (b.track ? b.track.position : 0)));\n\t\tif (!title) {\n\t\t\treturn `<div class="lmsh">Your courses</div><div class="lmsgrid">${rows.map(courseCard).join("")}</div>`;\n\t\t}\n\t\tconst total = rows[0].track.total || rows.length;\n\t\tconst done = rows.filter((r) => r.status === "Completed").length;\n\t\tconst pct = total ? Math.round((done / total) * 100) : 0;\n\t\treturn `\n\t\t\t<div class="trkh">\n\t\t\t\t<div><b>${esc(title)}</b><span class="muted"> \\u00b7 ${done} of ${total} complete</span></div>\n\t\t\t\t<span class="trkbar"><i style="width:${pct}%"></i></span>\n\t\t\t\t${done >= total ? `<a class="trkview" onclick="openAchievement(\'${esc(rows[0].track.name || "")}\')">View achievement \\u2192</a>` : ""}\n\t\t\t</div>\n\t\t\t<div class="lmsgrid">${rows.map(courseCard).join("")}</div>`;\n\t}).join("");\n}\nfunction openAchievement(track) {\n\tif (!track) return;\n\tacadFocus("read");\n\tapi("client_track_summary", { track: track })\n\t\t.then((s) => {\n\t\t\tconst hrs = (m) => (!m ? "" : m < 60 ? m + " min" : Math.round((m / 60) * 10) / 10 + " hours");\n\t\t\tdocument.getElementById("acad").innerHTML = `\n\t\t\t\t<div class="achv">\n\t\t\t\t\t<div class="achvtop">\\u{1F393}</div>\n\t\t\t\t\t<h1>${esc(s.title)}</h1>\n\t\t\t\t\t<div class="muted">${esc(s.product || "")}${s.issued_on ? ` \\u00b7 completed ${esc(s.issued_on)}` : ""}</div>\n\t\t\t\t\t${s.serial ? `<div class="achvser">${esc(s.serial)}</div>` : ""}\n\t\t\t\t\t<div class="achvstats">\n\t\t\t\t\t\t<span><b>${s.complete}</b> of ${s.total} courses</span>\n\t\t\t\t\t\t<span><b>${hrs(s.minutes)}</b> of study</span>\n\t\t\t\t\t</div>\n\t\t\t\t\t<div class="achvsec"><b>What you covered</b>\n\t\t\t\t\t\t<ol>${(s.courses || []).map((c) => `<li>${esc(c.title)}${c.completed_on ? ` <span class="muted">\\u00b7 ${esc(c.completed_on)}</span>` : ""}${c.cert ? ` <a href="/api/method/duty_board.client_room.client_shelf_file?id=${esc(c.cert)}" target="_blank">certificate</a>` : ""}</li>`).join("")}</ol>\n\t\t\t\t\t</div>\n\t\t\t\t\t${s.next ? `<div class="achvnext"><b>What next</b>\n\t\t\t\t\t\t<div class="achvnexttitle">${esc(s.next.title)}</div>\n\t\t\t\t\t\t${s.next.description ? `<p>${esc(s.next.description)}</p>` : ""}\n\t\t\t\t\t\t<span class="muted">${s.next.courses} course${s.next.courses === 1 ? "" : "s"}${s.next.assignable ? "" : " \\u00b7 ask your administrator about adding it"}</span></div>` : ""}\n\t\t\t\t\t<div style="margin-top:22px"><button class="rdghost" onclick="loadTraining()">\\u2190 Back to training</button></div>\n\t\t\t\t</div>`;\n\t\t})\n\t\t.catch(fail);\n}\nfunction pursueTrack(track) {'

CEL_OLD = '\tif (res.newly_certified) celebrate();'

CEL_NEW = '\tif (res.newly_certified) celebrate();\n\tif (res.track_done && res.track_done.track) {\n\t\tsetTimeout(() => openAchievement(res.track_done.track), 1400);\n\t}'

CSS_OLD = '\t.rdask { margin-top: 26px;'

CSS_NEW = '\t.trkh { display: flex; align-items: center; gap: 12px; flex-wrap: wrap;\n\t\tmargin: 22px 0 10px; font-size: 14.5px; }\n\t.trkh > div { flex: 1; min-width: 170px; }\n\t.trkbar { flex: 0 0 90px; height: 6px; border-radius: 99px; background: #E9EFEC; overflow: hidden; }\n\t.trkbar i { display: block; height: 100%; background: var(--brand); }\n\t.trkview { font-size: 12.5px; font-weight: 700; color: var(--brand-700); cursor: pointer; white-space: nowrap; }\n\t.achv { max-width: 620px; margin: 0 auto; text-align: center; padding: 10px 0 20px; }\n\t.achvtop { font-size: 46px; line-height: 1; }\n\t.achv h1 { font-family: Fraunces, Georgia, serif; font-size: 30px; line-height: 1.2;\n\t\tfont-weight: 600; margin: 12px 0 4px; }\n\t.achvser { display: inline-block; margin-top: 10px; font-size: 12px; letter-spacing: 1px;\n\t\tbackground: #FBF6E9; color: #7A5312; border-radius: 99px; padding: 5px 14px; }\n\t.achvstats { display: flex; justify-content: center; gap: 26px; margin: 22px 0 4px; font-size: 13px; color: #6B7C77; }\n\t.achvstats b { display: block; font-size: 22px; color: var(--brand-700); }\n\t.achvsec { text-align: left; margin-top: 26px; }\n\t.achvsec b, .achvnext b { display: block; font-size: 11.5px; letter-spacing: 1.5px;\n\t\ttext-transform: uppercase; color: var(--brand-700); margin-bottom: 8px; }\n\t.achvsec ol { margin: 0; padding-left: 22px; font-size: 14.5px; line-height: 1.9; }\n\t.achvnext { text-align: left; margin-top: 26px; background: var(--brand-50);\n\t\tborder: 1px solid #CBE7DE; border-radius: 12px; padding: 16px 18px; }\n\t.achvnexttitle { font-size: 17px; font-weight: 700; }\n\t.achvnext p { font-size: 14px; line-height: 1.6; color: #33423E; margin: 6px 0; }\n\n\t.rdask { margin-top: 26px;'



EDITS = [
    (CR, HELP_OLD, HELP_NEW, "track helpers + summary"),
    (CR, DUE_OLD, DUE_NEW, "resolve tracks once"),
    (CR, PAY_OLD, PAY_NEW, "track on each record"),
    (CR, SUB_OLD, SUB_NEW, "classic result carries track_done"),
    (CR, TF_OLD, TF_NEW, "timed result carries track_done"),
    (PORTAL, CARDS_OLD, CARDS_NEW, "grouped rendering"),
    (PORTAL, GRP_OLD, GRP_NEW, "groupedCourses + openAchievement"),
    (PORTAL, CEL_OLD, CEL_NEW, "open on track completion"),
    (PORTAL, CSS_OLD, CSS_NEW, "css"),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_track_summary(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.223.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.223.0.")

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

    for f, old, new, _label in EDITS:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: track grouping, completion detection, summary")
    print("  portal.html: grouped cards, achievement view")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.223.0"', '"3.224.0"'))
    print("wrote __init__.py -> 3.224.0")


if __name__ == "__main__":
    main()
