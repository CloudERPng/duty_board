#!/usr/bin/env python3
"""Duty Board v3.217.0 - THE CATALOGUE BECOMES A CATALOGUE.

Three problems, one of them a bug I introduced and missed.

1. The administrator's views render into #adminhost, which sits BESIDE the
   learner's own certificates, tracks and course list rather than replacing
   them. So the catalogue appeared with the reader's personal index stacked
   underneath it - exactly the structural problem the reading room had, in a
   place I did not check. A new body[data-adm] state hides the learner blocks
   while an administrator view is open, and every admin view now sets and
   clears it.

2. The catalogue was a stack of rows. It is now a three-column card grid -
   name, product, course count, study time, a clipped description, and a badge
   carrying Included, seats remaining, price per seat, or not subscribed.

3. A row could not say what a track was for. Clicking a card now opens a detail
   view: what it covers, who it is for, what staff will be able to do
   afterwards, the ordered list of courses with their study time, how it is
   assessed, and the actions.

  Duty Certification Track: +who_for, +outcomes. Study time is computed from
  lesson estimates rather than typed, so it cannot drift from the content.

Deploy: apply -> bench migrate (two fields) -> bench build --app duty_board ->
clear-cache + clear-website-cache -> restart. Anchored, idempotent.
Requires v3.216.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
ACAD = "duty_board/academy.py"
PORTAL = "duty_board/www/portal.html"
TRKDT = "duty_board/duty_board/doctype/duty_certification_track/duty_certification_track.json"
CHECK_ONLY = "--check" in sys.argv


CAT_OLD = 'function openCatalogue() {\n\tconst host = document.getElementById("adminhost");\n\tconst money = (v) => "₦" + Number(v || 0).toLocaleString();\n\tapi("duty_board.academy.academy_catalogue")\n\t\t.then((rows) => {\n\t\t\thost.innerHTML = `\n\t\t\t\t<div class="admwrap">\n\t\t\t\t\t<div class="admhead"><div><b>Certification catalogue</b><span class="muted"> · what your organisation can train on</span></div>\n\t\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="loadAdminTraining()">Back</button></div>\n\t\t\t\t\t${rows.length ? rows.map((r) => `\n\t\t\t\t\t<div class="catrow">\n\t\t\t\t\t\t<div class="cattop">\n\t\t\t\t\t\t\t<b>${esc(r.title)}</b>\n\t\t\t\t\t\t\t<span class="cattag ${r.included ? "inc" : r.seats_left ? "own" : "paid"}">${\n\t\t\t\t\t\t\t\tr.included ? "Included" : r.seats_left ? r.seats_left + " seat" + (r.seats_left === 1 ? "" : "s") + " left" : r.access === "Paid" ? money(r.seat_price) + " per seat" : "Not in your subscription"}</span>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t\t<div class="muted" style="font-size:12px">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"}</div>\n\t\t\t\t\t\t${r.description ? `<div class="catdesc">${esc(r.description)}</div>` : ""}\n\t\t\t\t\t\t${r.pending\n\t\t\t\t\t\t\t? `<div class="catnote">Request for ${r.pending_seats} seat(s) received — we will confirm once payment is processed.</div>`\n\t\t\t\t\t\t\t: r.seats\n\t\t\t\t\t\t\t\t? `<div class="catnote ok">${r.seats_left} of ${r.seats} seats available${r.expires_on ? " · until " + esc(String(r.expires_on).slice(0, 10)) : ""}</div>`\n\t\t\t\t\t\t\t\t: (!r.included && r.access !== "Paid")\n\t\t\t\t\t\t\t\t\t? `<div class="catnote">This track comes with a product you are not subscribed to. Ask us about adding it.</div>`\n\t\t\t\t\t\t\t\t\t: ""}\n\t\t\t\t\t\t<div class="catacts">\n\t\t\t\t\t\t\t${r.assignable ? `<a class="catasg" data-t="${esc(r.track)}">Assign to staff</a>` : ""}\n\t\t\t\t\t\t\t${r.access === "Paid" && !r.pending ? `<a class="catreq" data-t="${esc(r.track)}" data-n="${esc(r.title)}" data-p="${r.seat_price}">${r.seats ? "Request more seats" : "Request seats"}</a>` : ""}\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>`).join("")\n\t\t\t\t\t\t: `<span class="muted">No certification tracks have been published yet.</span>`}\n\t\t\t\t</div>`;\n\t\t\thost.querySelectorAll(".catreq").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => requestSeats(a.getAttribute("data-t"), a.getAttribute("data-n"), a.getAttribute("data-p"))));\n\t\t\thost.querySelectorAll(".catasg").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => openAssign(a.getAttribute("data-t"))));\n\t\t})\n\t\t.catch(fail);\n}\n'

CAT_NEW = 'function openCatalogue() {\n\tadmFocus(1);\n\tconst host = document.getElementById("adminhost");\n\tconst money = (v) => "₦" + Number(v || 0).toLocaleString();\n\tconst hrs = (mins) => {\n\t\tif (!mins) return "";\n\t\tconst h = Math.round((mins / 60) * 10) / 10;\n\t\treturn h < 1 ? mins + " min" : h + (h === 1 ? " hour" : " hours");\n\t};\n\tconst badge = (r) =>\n\t\tr.included ? `<span class="cattag inc">Included</span>`\n\t\t: r.seats_left ? `<span class="cattag own">${r.seats_left} seat${r.seats_left === 1 ? "" : "s"} left</span>`\n\t\t: r.access === "Paid" ? `<span class="cattag paid">${money(r.seat_price)} / seat</span>`\n\t\t: `<span class="cattag out">Not subscribed</span>`;\n\tapi("duty_board.academy.academy_catalogue")\n\t\t.then((rows) => {\n\t\t\twindow._cat = rows;\n\t\t\thost.innerHTML = `\n\t\t\t\t<div class="admwrap">\n\t\t\t\t\t<div class="admhead"><div><b>Certification catalogue</b><span class="muted"> · what your organisation can train on</span></div>\n\t\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="admFocus(0);loadAdminTraining()">Back</button></div>\n\t\t\t\t\t${rows.length ? `<div class="catgrid">${rows.map((r, i) => `\n\t\t\t\t\t\t<div class="catcard${r.assignable ? "" : " dim"}" data-i="${i}">\n\t\t\t\t\t\t\t<div class="catcardtop">${badge(r)}</div>\n\t\t\t\t\t\t\t<b class="catname">${esc(r.title)}</b>\n\t\t\t\t\t\t\t<div class="catmeta">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"}${r.minutes ? " · " + hrs(r.minutes) : ""}</div>\n\t\t\t\t\t\t\t<div class="catblurb">${esc(r.description || "")}</div>\n\t\t\t\t\t\t\t${r.pending ? `<div class="catpend">Request for ${r.pending_seats} seat(s) received</div>` : ""}\n\t\t\t\t\t\t\t<span class="catmore">Details →</span>\n\t\t\t\t\t\t</div>`).join("")}</div>`\n\t\t\t\t\t\t: `<span class="muted">No certification tracks have been published yet.</span>`}\n\t\t\t\t</div>`;\n\t\t\thost.querySelectorAll(".catcard").forEach((el) =>\n\t\t\t\tel.addEventListener("click", () => openTrack(parseInt(el.getAttribute("data-i"), 10))));\n\t\t})\n\t\t.catch(fail);\n}\nfunction openTrack(i) {\n\tconst r = (window._cat || [])[i];\n\tif (!r) return;\n\tconst host = document.getElementById("adminhost");\n\tconst money = (v) => "₦" + Number(v || 0).toLocaleString();\n\tconst hrs = (m) => (!m ? "—" : (m < 60 ? m + " min" : Math.round((m / 60) * 10) / 10 + " hours"));\n\tconst state =\n\t\tr.included ? `<div class="catnote ok">Included in your subscription — assign it to as many colleagues as you like.</div>`\n\t\t: r.pending ? `<div class="catnote">Request for ${r.pending_seats} seat(s) received. We will confirm once payment is processed.</div>`\n\t\t: r.seats ? `<div class="catnote ok">${r.seats_left} of ${r.seats} seats available${r.expires_on ? " · until " + esc(String(r.expires_on).slice(0, 10)) : ""}</div>`\n\t\t: r.access === "Paid" ? `<div class="catnote">${money(r.seat_price)} per seat. One seat covers one member of staff for the whole track, and the certificate they earn does not expire.</div>`\n\t\t: `<div class="catnote">This track comes with a product you are not subscribed to. Ask us about adding it.</div>`;\n\thost.innerHTML = `\n\t\t<div class="admwrap">\n\t\t\t<div class="admhead"><div><a class="catback" onclick="openCatalogue()">← Catalogue</a></div></div>\n\t\t\t<h3 class="catdtitle">${esc(r.title)}</h3>\n\t\t\t<div class="catmeta" style="margin-bottom:14px">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"} · about ${hrs(r.minutes)} of study</div>\n\t\t\t${state}\n\t\t\t${r.description ? `<div class="catsec"><b>What this track covers</b><p>${esc(r.description)}</p></div>` : ""}\n\t\t\t${r.who_for ? `<div class="catsec"><b>Who it is for</b><p>${esc(r.who_for)}</p></div>` : ""}\n\t\t\t${r.outcomes ? `<div class="catsec"><b>What your staff will be able to do</b><p>${esc(r.outcomes)}</p></div>` : ""}\n\t\t\t${(r.course_list || []).length ? `<div class="catsec"><b>Courses in this track</b><ol class="catlist">${r.course_list.map((x) => `<li>${esc(x.title)}${x.minutes ? ` <span class="muted">· ${hrs(x.minutes)}</span>` : ""}</li>`).join("")}</ol></div>` : ""}\n\t\t\t<div class="catsec"><b>How it is assessed</b><p>Each course ends with a timed, proctored assessment drawn at random from a larger question bank. Passing every course earns a certificate with a serial anyone can verify.</p></div>\n\t\t\t<div class="catacts">\n\t\t\t\t${r.assignable ? `<button onclick="admFocus(0);openAssign(\'${esc(r.track)}\')">Assign to staff</button>` : ""}\n\t\t\t\t${r.access === "Paid" && !r.pending ? `<button style="background:#E2E8E5;color:#2A3833" onclick="requestSeats(\'${esc(r.track)}\',\'${esc(r.title)}\',${r.seat_price})">${r.seats ? "Request more seats" : "Request seats"}</button>` : ""}\n\t\t\t</div>\n\t\t</div>`;\n}\n'

FOCUS_OLD = 'function acadFocus(mode) {'

FOCUS_NEW = 'function admFocus(on) {\n\t/* The administrator\'s own views render into #adminhost, which sits BESIDE\n\t   the learner\'s certificates, tracks and course list rather than replacing\n\t   them. Without this the catalogue appeared with the reader\'s own index\n\t   stacked underneath it — the same structural problem the reading room had. */\n\tif (on) document.body.setAttribute("data-adm", "1");\n\telse document.body.removeAttribute("data-adm");\n}\nfunction acadFocus(mode) {'

CSS_OLD = '\tbody[data-acad] #mycerts, body[data-acad] #mytracks, body[data-acad] #adminhost { display: none !important; }'

CSS_NEW = '\tbody[data-acad] #mycerts, body[data-acad] #mytracks, body[data-acad] #adminhost { display: none !important; }\n\tbody[data-adm] #mycerts, body[data-adm] #mytracks, body[data-adm] #acad { display: none !important; }\n\n\t.catgrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }\n\t.catcard { border: 1px solid #E4EAE8; border-radius: 14px; padding: 15px 16px; background: #fff;\n\t\tcursor: pointer; display: flex; flex-direction: column; transition: border-color .15s, transform .15s; }\n\t.catcard:hover { border-color: var(--brand); transform: translateY(-2px); }\n\t.catcard.dim { background: #FBFCFC; }\n\t.catcardtop { margin-bottom: 9px; }\n\t.catname { font-family: Fraunces, Georgia, serif; font-size: 17px; line-height: 1.25; font-weight: 600; }\n\t.catmeta { font-size: 11.5px; color: #6B7C77; margin-top: 4px; }\n\t.catblurb { font-size: 12.5px; line-height: 1.55; color: #4A5A55; margin-top: 9px;\n\t\tdisplay: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }\n\t.catpend { font-size: 11.5px; background: #FFF7E6; border-radius: 7px; padding: 5px 9px; margin-top: 9px; color: #7A5312; }\n\t.catmore { font-size: 12px; font-weight: 700; color: var(--brand-700); margin-top: auto; padding-top: 11px; }\n\t.cattag.out { background: #F1F4F3; color: #6B7C77; }\n\t.catback { cursor: pointer; font-size: 12.5px; color: var(--brand-700); font-weight: 700; }\n\t.catdtitle { font-family: Fraunces, Georgia, serif; font-size: 24px; font-weight: 600; margin: 2px 0 2px; }\n\t.catsec { margin-top: 16px; font-size: 13.5px; line-height: 1.6; }\n\t.catsec b { display: block; font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase;\n\t\tcolor: var(--brand-700); margin-bottom: 5px; }\n\t.catsec p { margin: 0; color: #33423E; }\n\t.catlist { margin: 4px 0 0; padding-left: 20px; }\n\t.catlist li { margin: 3px 0; }\n\t@media (max-width: 900px) { .catgrid { grid-template-columns: repeat(2, 1fr); } }\n\t@media (max-width: 620px) { .catgrid { grid-template-columns: 1fr; } }'

PY_OLD = '\t\tout.append({\n\t\t\t"track": t.name,\n\t\t\t"name": t.name,'

PY_NEW = '\t\tcourse_list = []\n\t\tminutes = 0\n\t\tfor m in frappe.get_all(\n\t\t\t"Duty Certification Track Module", filters={"parent": t.name},\n\t\t\tfields=["module"], order_by="idx asc",\n\t\t):\n\t\t\ttitle = frappe.db.get_value("Duty Training Module", m.module, "title") or m.module\n\t\t\tmins = sum(\n\t\t\t\tcint(x.est_minutes) for x in frappe.get_all(\n\t\t\t\t\t"Duty Lesson", filters={"module": m.module}, fields=["est_minutes"]\n\t\t\t\t)\n\t\t\t)\n\t\t\tminutes += mins\n\t\t\tcourse_list.append({"title": title, "minutes": mins})\n\t\tout.append({\n\t\t\t"track": t.name,\n\t\t\t"name": t.name,\n\t\t\t"who_for": t.who_for,\n\t\t\t"outcomes": t.outcomes,\n\t\t\t"course_list": course_list,\n\t\t\t"minutes": minutes,'

PY_F_OLD = '\t\tfields=["name", "title", "product", "description", "access", "seat_price"],\n\t\torder_by="product asc, title asc",'

PY_F_NEW = '\t\tfields=["name", "title", "product", "description", "access", "seat_price",\n\t\t\t\t"who_for", "outcomes"],\n\t\torder_by="product asc, title asc",'

SWAPS = [('function openPeople() {\n\tconst host = document.getElementById("adminhost");', 'function openPeople() {\n\tadmFocus(1);\n\tconst host = document.getElementById("adminhost");', 'people focus'), ('function openAssign(preselect) {\n\tconst host = document.getElementById("adminhost");', 'function openAssign(preselect) {\n\tadmFocus(1);\n\tconst host = document.getElementById("adminhost");', 'assign focus'), ('function requestSeats(track, title, price) {\n\tconst host = document.getElementById("adminhost");', 'function requestSeats(track, title, price) {\n\tadmFocus(1);\n\tconst host = document.getElementById("adminhost");', 'request focus'), ('function loadAdminTraining() {\n\t/* Painted only for the room administrator.', 'function loadAdminTraining() {\n\tadmFocus(0);\n\t/* Painted only for the room administrator.', 'index clears focus')]



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
    for p in (INIT, ACAD, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "function admFocus(" in files[PORTAL]:
        print("Already applied. Nothing to do.")
        return
    if '"3.216.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.216.0.")

    edits = [
        (ACAD, PY_F_OLD, PY_F_NEW, "catalogue query fields"),
        (ACAD, PY_OLD, PY_NEW, "course list + study time"),
        (PORTAL, FOCUS_OLD, FOCUS_NEW, "admFocus"),
        (PORTAL, CAT_OLD, CAT_NEW, "card grid + detail view"),
        (PORTAL, CSS_OLD, CSS_NEW, "catalogue css"),
    ] + [(PORTAL, o, n, l) for o, n, l in SWAPS]

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

    add_fields(os.path.join(root, TRKDT), [
        {"fieldname": "who_for", "fieldtype": "Small Text", "label": "Who It Is For"},
        {"fieldname": "outcomes", "fieldtype": "Small Text", "label": "What They Will Be Able To Do"},
    ])
    print("  Duty Certification Track: +who_for, +outcomes")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (ACAD, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  academy.py: course list and computed study time")
    print("  portal.html: admin focus, card grid, track detail")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.216.0"', '"3.217.0"'))
    print("wrote __init__.py -> 3.217.0")


if __name__ == "__main__":
    main()
