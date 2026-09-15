#!/usr/bin/env python3
"""Duty Board v3.225.0 — AUDIT CHUNK B: reachability, and two of my own loose ends.

The reverse scan — every whitelisted endpoint, is anything calling it — found
nine that nothing references. All nine are properly guarded, so they are dead
surface rather than a risk. Seven predate this work and are left alone: an
endpoint I cannot see a caller for may still be called from a client script, a
workflow, or an integration I have no visibility of, and deleting somebody
else's code on the strength of a grep is how outages happen.

The other two are mine, written this session and never wired. Both were real
gaps rather than surplus:

  academy.question_counts       — written in v3.221.0 for a badge that was
                                  never added. An unanswered learner question
                                  is only useful if somebody knows it is there,
                                  so the open count now rides on the rail label:
                                  "Lesson questions (3)".

  client_training_admin_due     — written in v3.211.0. Administrators could set
                                  a due date when assigning and never change it
                                  afterwards, which is the moment they actually
                                  want to: when somebody is running late. The
                                  due date in the per-person detail is now
                                  editable in place, and can be set on a course
                                  that never had one.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.224.1.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv


RAIL_OLD = '\t\t\tboard.rail.push({ id: "lessonq", ic: board._rsvg.ask, label: __("Lesson questions"), go: () => board.lesson_questions_dialog() });'

RAIL_NEW = '\t\t\tboard.rail.push({ id: "lessonq", ic: board._rsvg.ask, label: __("Lesson questions"), go: () => board.lesson_questions_dialog() });\n\t\t\t/* An unanswered question is only useful if somebody knows it is there.\n\t\t\t   The count rides on the rail label so it is visible without opening. */\n\t\t\tfrappe.call({\n\t\t\t\tmethod: "duty_board.academy.question_counts",\n\t\t\t\terror: () => {},\n\t\t\t\tcallback: (qc) => {\n\t\t\t\t\tconst n = (qc.message || {}).open || 0;\n\t\t\t\t\tif (!n) return;\n\t\t\t\t\tconst item = board.rail.find((x) => x.id === "lessonq");\n\t\t\t\t\tif (item) { item.label = __("Lesson questions ({0})", [n]); board.build_rail(); }\n\t\t\t\t},\n\t\t\t});'

DUE_OLD = '\t\t\t\t\t\t\t${c.due_on ? `<span class="detmeta${c.overdue ? " late" : ""}">${c.overdue ? "overdue " : "due "}${esc(String(c.due_on).slice(0, 10))}</span>` : ""}'

DUE_NEW = '\t\t\t\t\t\t\t<span class="detdue${c.overdue ? " late" : ""}" data-r="${esc(c.record)}" title="Click to change the due date">${c.due_on ? `${c.overdue ? "overdue " : "due "}${esc(String(c.due_on).slice(0, 10))}` : "set a due date"}</span>'

HDL_OLD = '\t\t\t\t\t}).join("") || `<span class="muted">Nothing assigned.</span>`;'

HDL_NEW = '\t\t\t\t\t}).join("") || `<span class="muted">Nothing assigned.</span>`;\n\t\t\t\t\tbox.querySelectorAll(".detdue").forEach((el) =>\n\t\t\t\t\t\tel.addEventListener("click", () => {\n\t\t\t\t\t\t\tif (el.querySelector("input")) return;\n\t\t\t\t\t\t\tconst rec = el.getAttribute("data-r");\n\t\t\t\t\t\t\tconst cur = (el.textContent.match(/\\d{4}-\\d{2}-\\d{2}/) || [""])[0];\n\t\t\t\t\t\t\tel.innerHTML = `<input type="date" value="${cur}">`;\n\t\t\t\t\t\t\tconst inp = el.querySelector("input");\n\t\t\t\t\t\t\tinp.focus();\n\t\t\t\t\t\t\tinp.addEventListener("change", () =>\n\t\t\t\t\t\t\t\tapi("client_training_admin_due", { record: rec, due_on: inp.value || null })\n\t\t\t\t\t\t\t\t\t.then(loadAdminTraining)\n\t\t\t\t\t\t\t\t\t.catch(fail));\n\t\t\t\t\t\t}));'

CSS_OLD = '\t.detmeta.late { color: #B27409; font-weight: 700; }'

CSS_NEW = '\t.detmeta.late { color: #B27409; font-weight: 700; }\n\t.detdue { color: #6B7C77; cursor: pointer; border-bottom: 1px dashed #CBD5D1; }\n\t.detdue.late { color: #B27409; font-weight: 700; }\n\t.detdue input { border: 1px solid #DCE4E1; border-radius: 6px; padding: 2px 6px; font-size: 12px; }'



EDITS = [
    (JS, RAIL_OLD, RAIL_NEW, "question count on the rail"),
    (PORTAL, DUE_OLD, DUE_NEW, "editable due date"),
    (PORTAL, HDL_OLD, HDL_NEW, "due date handler"),
    (PORTAL, CSS_OLD, CSS_NEW, "css"),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, PORTAL, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "question_counts" in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.224.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.224.1.")

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
    for p in (PORTAL, JS):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  duty_board.js: open question count on the rail")
    print("  portal.html: due dates editable in the per-person detail")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.224.1"', '"3.225.0"'))
    print("wrote __init__.py -> 3.225.0")


if __name__ == "__main__":
    main()
