#!/usr/bin/env python3
"""Duty Board v3.223.0 - WHERE SOMEBODY STOPPED, AND PROOF THEY FINISHED.

Three from the review, all on the administrator's side.

A3  The dashboard said how many, never where. Counts of assigned, complete and
    overdue tell an administrator to chase everybody. Expanding a person now
    shows each course: chapters read against total, attempts and best score,
    due date, and whether they are blocked. That turns "chase everyone" into
    "chase these three, about this".

A5  The employer could not see the certificates they paid for. The learner
    could download their own; the person who bought the seat could not. The
    file was already reachable - client_shelf_file is room-scoped, so any
    member including the administrator could fetch it - it simply was never
    linked. Now it is, beside each completed course.

A4  No export. An HR head asks for the certified list early, for personnel
    files or to show a client of their own, and its absence looks unserious.
    Export CSV returns the full roster - name, email, course, status, chapters
    read, attempts, best score, due date, overdue, blocked, completed, last
    signed in - saved straight from the browser with a BOM so Excel opens the
    naira and the names correctly.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.222.0.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


ROWS_OLD = '\t\tr["blocked"] = False\n\t\tif r.status != "Completed":\n\t\t\tst = _quiz_state(r.module, r.trainee, r.name)\n\t\t\tr["blocked"] = bool(not st["passed"] and st["attempts_left"] == 0)\n\treturn users, recs'

ROWS_NEW = '\t\tr["blocked"] = False\n\t\tif r.status != "Completed":\n\t\t\tst = _quiz_state(r.module, r.trainee, r.name)\n\t\t\tr["blocked"] = bool(not st["passed"] and st["attempts_left"] == 0)\n\t# per-course detail, so an administrator can see WHERE somebody stopped\n\t# rather than only that they have not finished\n\tmods = list({r.module for r in recs})\n\ttotals = {}\n\tfor l in frappe.get_all(\n\t\t"Duty Lesson", filters={"module": ["in", mods or [""]]}, fields=["module"]\n\t):\n\t\ttotals[l.module] = totals.get(l.module, 0) + 1\n\tdone = {}\n\tfor p in frappe.get_all(\n\t\t"Duty Lesson Progress",\n\t\tfilters={"module": ["in", mods or [""]], "completed_at": ["is", "set"]},\n\t\tfields=["module", "user"],\n\t):\n\t\tdone[(p.user, p.module)] = done.get((p.user, p.module), 0) + 1\n\tatt = {}\n\tfor a in frappe.get_all(\n\t\t"Duty Quiz Attempt",\n\t\tfilters={"record": ["in", [r.name for r in recs] or [""]], "finished_at": ["is", "set"]},\n\t\tfields=["record", "score"],\n\t):\n\t\tcur = att.setdefault(a.record, {"n": 0, "best": 0})\n\t\tcur["n"] += 1\n\t\tcur["best"] = max(cur["best"], cint(a.score))\n\tfor r in recs:\n\t\tr["lessons_total"] = totals.get(r.module, 0)\n\t\tr["lessons_done"] = done.get((r.trainee, r.module), 0)\n\t\tr["attempts"] = att.get(r.name, {}).get("n", 0)\n\t\tr["best"] = att.get(r.name, {}).get("best", 0)\n\treturn users, recs'

COURSES_OLD = '\t\t\t"courses": [\n\t\t\t\t{\n\t\t\t\t\t"record": r.name, "title": r["title"], "status": r.status,\n\t\t\t\t\t"due_on": str(r.due_on) if r.due_on else None,\n\t\t\t\t\t"overdue": r["overdue"],\n\t\t\t\t\t"blocked": r["blocked"],\n\t\t\t\t}'

COURSES_NEW = '\t\t\t"courses": [\n\t\t\t\t{\n\t\t\t\t\t"record": r.name, "title": r["title"], "status": r.status,\n\t\t\t\t\t"due_on": str(r.due_on) if r.due_on else None,\n\t\t\t\t\t"overdue": r["overdue"],\n\t\t\t\t\t"blocked": r["blocked"],\n\t\t\t\t\t"lessons_total": r["lessons_total"],\n\t\t\t\t\t"lessons_done": r["lessons_done"],\n\t\t\t\t\t"attempts": r["attempts"],\n\t\t\t\t\t"best": r["best"],\n\t\t\t\t\t"cert": frappe.db.get_value(\n\t\t\t\t\t\t"Duty Training Record", r.name, "certificate_shelf"\n\t\t\t\t\t) if r.status == "Completed" else None,\n\t\t\t\t}'

EXP_OLD = '@frappe.whitelist()\ndef client_admin_grant_attempt(record):'

EXP_NEW = '@frappe.whitelist()\ndef client_admin_export():\n\t"""The roster as a spreadsheet.\n\n\tAn HR head asks for this early — for personnel files, or to show a client\n\tof their own who is certified — and its absence looks unserious. Returned as\n\tCSV text rather than a file so the browser can save it without a round trip\n\tthrough the shelf."""\n\troom = _require_room_admin()\n\t_users, recs = _admin_rows(room)\n\tseen = _last_signed_in([r.trainee for r in recs])\n\tout = [\n\t\t"Name,Email,Course,Status,Lessons read,Lessons total,Attempts,Best score,"\n\t\t"Due on,Overdue,Blocked,Completed on,Last signed in"\n\t]\n\n\tdef q(v):\n\t\ts = "" if v is None else str(v)\n\t\treturn \'"%s"\' % s.replace(\'"\', \'""\') if ("," in s or \'"\' in s) else s\n\n\tfor r in sorted(recs, key=lambda x: ((x.trainee_name or ""), x["title"])):\n\t\tout.append(\n\t\t\t",".join(\n\t\t\t\tq(v)\n\t\t\t\tfor v in (\n\t\t\t\t\tr.trainee_name or frappe.utils.get_fullname(r.trainee),\n\t\t\t\t\tr.trainee, r["title"], r.status,\n\t\t\t\t\tr["lessons_done"], r["lessons_total"], r["attempts"],\n\t\t\t\t\tr["best"] or "", r.due_on or "",\n\t\t\t\t\t"yes" if r["overdue"] else "", "yes" if r["blocked"] else "",\n\t\t\t\t\tr.completed_on or "", seen.get(r.trainee) or "never",\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\treturn {\n\t\t"filename": "training_%s_%s.csv" % (\n\t\t\t"".join(c for c in (room.customer or room.name) if c.isalnum())[:32], today()\n\t\t),\n\t\t"csv": "\\n".join(out),\n\t}\n\n\n@frappe.whitelist()\ndef client_admin_grant_attempt(record):'

ADMROW_OLD = '\t\t\t\t\t\t<div class="admrow">\n\t\t\t\t\t\t\t<div class="admwho">\n\t\t\t\t\t\t\t\t<b>${esc(p.full_name)}</b>\n\t\t\t\t\t\t\t\t<span class="muted">${p.assigned ? `${p.complete} of ${p.assigned} complete` : "nothing assigned"}${p.overdue ? ` · <span class="admlate">${p.overdue} overdue</span>` : ""}${p.never ? ` · <span class="pplnever">never signed in</span>` : ""}${(p.blocked || []).length ? ` · <span class="admlate">blocked</span>` : ""}</span>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<div class="admbar"><i style="width:${p.assigned ? Math.round((p.complete / p.assigned) * 100) : 0}%"></i></div>\n\t\t\t\t\t\t\t${(p.blocked || []).length ? `<a class="admgrant" data-r="${esc(p.blocked[0].record)}" title="${esc(p.blocked[0].title)}">Grant attempt</a>` : ""}\n\t\t\t\t\t\t\t${p.assigned > p.complete ? `<a class="admnudge" data-u="${esc(p.user)}">Remind</a>` : ""}\n\t\t\t\t\t\t</div>`).join("")'

ADMROW_NEW = '\t\t\t\t\t\t<div class="admrow" data-u="${esc(p.user)}">\n\t\t\t\t\t\t\t<div class="admwho">\n\t\t\t\t\t\t\t\t<b>${esc(p.full_name)}</b>\n\t\t\t\t\t\t\t\t<span class="muted">${p.assigned ? `${p.complete} of ${p.assigned} complete` : "nothing assigned"}${p.overdue ? ` · <span class="admlate">${p.overdue} overdue</span>` : ""}${p.never ? ` · <span class="pplnever">never signed in</span>` : ""}${(p.blocked || []).length ? ` · <span class="admlate">blocked</span>` : ""}</span>\n\t\t\t\t\t\t\t</div>\n\t\t\t\t\t\t\t<div class="admbar"><i style="width:${p.assigned ? Math.round((p.complete / p.assigned) * 100) : 0}%"></i></div>\n\t\t\t\t\t\t\t${(p.blocked || []).length ? `<a class="admgrant" data-r="${esc(p.blocked[0].record)}" title="${esc(p.blocked[0].title)}">Grant attempt</a>` : ""}\n\t\t\t\t\t\t\t${p.assigned > p.complete ? `<a class="admnudge" data-u="${esc(p.user)}">Remind</a>` : ""}\n\t\t\t\t\t\t\t${p.assigned ? `<a class="admexp" data-u="${esc(p.user)}">Detail</a>` : ""}\n\t\t\t\t\t\t\t<div class="admdetail" id="det-${esc(p.user)}"></div>\n\t\t\t\t\t\t</div>`).join("")'

HDL_OLD = '\t\t\thost.querySelectorAll(".admgrant").forEach((a) =>'

HDL_NEW = '\t\t\thost.querySelectorAll(".admexp").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => {\n\t\t\t\t\tconst u = a.getAttribute("data-u");\n\t\t\t\t\tconst box = document.getElementById("det-" + u);\n\t\t\t\t\tif (!box) return;\n\t\t\t\t\tif (box.innerHTML) { box.innerHTML = ""; a.textContent = "Detail"; return; }\n\t\t\t\t\ta.textContent = "Hide";\n\t\t\t\t\tconst p = (window._adm.people || []).find((x) => x.user === u) || {};\n\t\t\t\t\tbox.innerHTML = (p.courses || []).map((c) => {\n\t\t\t\t\t\tconst pct = c.lessons_total ? Math.round((c.lessons_done / c.lessons_total) * 100) : 0;\n\t\t\t\t\t\tconst state = c.status === "Completed"\n\t\t\t\t\t\t\t? `<span class="detok">Certified${c.best ? ` \\u00b7 ${c.best}%` : ""}</span>`\n\t\t\t\t\t\t\t: c.blocked ? `<span class="detbad">Out of attempts</span>`\n\t\t\t\t\t\t\t: c.attempts ? `<span class="detwarn">${c.attempts} attempt${c.attempts === 1 ? "" : "s"}${c.best ? `, best ${c.best}%` : ""}</span>`\n\t\t\t\t\t\t\t: c.lessons_done ? `<span class="muted">reading</span>`\n\t\t\t\t\t\t\t: `<span class="muted">not started</span>`;\n\t\t\t\t\t\treturn `<div class="detrow">\n\t\t\t\t\t\t\t<span class="dettitle">${esc(c.title)}</span>\n\t\t\t\t\t\t\t<span class="detbar"><i style="width:${pct}%"></i></span>\n\t\t\t\t\t\t\t<span class="detmeta">${c.lessons_total ? `${c.lessons_done}/${c.lessons_total}` : ""}</span>\n\t\t\t\t\t\t\t${state}\n\t\t\t\t\t\t\t${c.due_on ? `<span class="detmeta${c.overdue ? " late" : ""}">${c.overdue ? "overdue " : "due "}${esc(String(c.due_on).slice(0, 10))}</span>` : ""}\n\t\t\t\t\t\t\t${c.cert ? `<a href="/api/method/duty_board.client_room.client_shelf_file?id=${esc(c.cert)}" target="_blank">Certificate</a>` : ""}\n\t\t\t\t\t\t</div>`;\n\t\t\t\t\t}).join("") || `<span class="muted">Nothing assigned.</span>`;\n\t\t\t\t}));\n\t\t\thost.querySelectorAll(".admgrant").forEach((a) =>'

EXPBTN_OLD = '\t\t\t\t\t\t<button id="admassign">＋ Assign training</button>'

EXPBTN_NEW = '\t\t\t\t\t\t<button id="admcsv" style="background:#E2E8E5;color:#2A3833">Export CSV</button>\n\t\t\t\t\t\t<button id="admassign">＋ Assign training</button>'

EXPHDL_OLD = '\t\t\tconst rall = document.getElementById("admrall");'

EXPHDL_NEW = '\t\t\tconst csv = document.getElementById("admcsv");\n\t\t\tif (csv) csv.onclick = () => {\n\t\t\t\tcsv.disabled = true;\n\t\t\t\tapi("client_admin_export")\n\t\t\t\t\t.then((r) => {\n\t\t\t\t\t\tconst blob = new Blob(["\\uFEFF" + r.csv], { type: "text/csv;charset=utf-8;" });\n\t\t\t\t\t\tconst a = document.createElement("a");\n\t\t\t\t\t\ta.href = URL.createObjectURL(blob);\n\t\t\t\t\t\ta.download = r.filename || "training.csv";\n\t\t\t\t\t\tdocument.body.appendChild(a); a.click(); a.remove();\n\t\t\t\t\t\tcsv.disabled = false;\n\t\t\t\t\t})\n\t\t\t\t\t.catch((e) => { csv.disabled = false; fail(e); });\n\t\t\t};\n\t\t\tconst rall = document.getElementById("admrall");'

CSS_OLD = '\t.admgrant { font-size: 12px; font-weight: 700; color: #B27409; cursor: pointer; white-space: nowrap; }'

CSS_NEW = '\t.admgrant { font-size: 12px; font-weight: 700; color: #B27409; cursor: pointer; white-space: nowrap; }\n\t.admexp { font-size: 12px; font-weight: 700; color: var(--brand-700); cursor: pointer; white-space: nowrap; }\n\t.admdetail { width: 100%; }\n\t.admdetail:empty { display: none; }\n\t.detrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap;\n\t\tpadding: 6px 0 6px 14px; border-left: 2px solid #E9EFEC; margin: 2px 0 2px 4px; font-size: 12.5px; }\n\t.dettitle { flex: 0 0 40%; min-width: 150px; }\n\t.detbar { flex: 0 0 70px; height: 5px; border-radius: 99px; background: #E9EFEC; overflow: hidden; }\n\t.detbar i { display: block; height: 100%; background: var(--brand); }\n\t.detmeta { color: #6B7C77; }\n\t.detmeta.late { color: #B27409; font-weight: 700; }\n\t.detok { color: #0C6B4F; font-weight: 700; }\n\t.detwarn { color: #8A5A0B; font-weight: 700; }\n\t.detbad { color: #B27409; font-weight: 700; }'



EDITS = [
    (CR, ROWS_OLD, ROWS_NEW, "per-course detail"),
    (CR, COURSES_OLD, COURSES_NEW, "course payload + certificate"),
    (CR, EXP_OLD, EXP_NEW, "csv export"),
    (PORTAL, ADMROW_OLD, ADMROW_NEW, "roster row + detail slot"),
    (PORTAL, HDL_OLD, HDL_NEW, "expand handler"),
    (PORTAL, EXPBTN_OLD, EXPBTN_NEW, "export button"),
    (PORTAL, EXPHDL_OLD, EXPHDL_NEW, "export handler"),
    (PORTAL, CSS_OLD, CSS_NEW, "detail css"),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_admin_export(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.222.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.222.0.")

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
    print("  client_room.py: per-course detail, certificate link, CSV export")
    print("  portal.html: expandable roster, export button")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.222.0"', '"3.223.0"'))
    print("wrote __init__.py -> 3.223.0")


if __name__ == "__main__":
    main()
