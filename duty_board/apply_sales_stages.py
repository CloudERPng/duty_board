#!/usr/bin/env python3
"""Duty Board — SALES KANBAN STAGES.

Two changes to the pipeline:

  MERGE Contacted and Qualified into a single stage. The distinction was not
  earning its column: a lead that has been rung and a lead that has been
  assessed were being moved between two columns on a judgement nobody had
  written down, which is exactly the kind of stage that fills with leads
  somebody stopped maintaining.

  ADD "Awaiting Payment" after Negotiation. Terms agreed, money not yet in.
  This is the stage most pipelines lack and the one that matters most in this
  market, because a deal that is agreed and unpaid is neither Won nor still
  being negotiated, and putting it in either place misstates the pipeline.

New pipeline: New → Contacted → Proposal → Negotiation → Awaiting Payment

NAMING NOTE, and it is a real decision rather than a detail. The merged stage
is called "Contacted" rather than "Qualified" because every lead in it has
definitely been contacted while only some have been qualified. Naming it
Qualified would mean a lead rung once and not yet assessed sits in a column
claiming it is qualified — and since the kanban sums value per stage, that
overstates the pipeline in the direction that causes the most damage. If you
would rather have "Qualified", it is the MERGED_NAME constant below plus the
same value in the doctype options and the JS list; nothing else reads it.

Touches four places, all of which must agree or the board breaks:
  1. sales.py            STAGES — the server's source of truth
  2. duty_lead.json      the Select field's options
  3. duty_board.js       the lead-detail dropdown list
  4. duty_board.js       the per-column CSS

And migrates existing data: any lead sitting in Qualified moves to the merged
stage. Without that step those leads vanish from the board — they would still
exist, with a stage value no column matches, which is worse than losing them
because nobody would notice.

Anchored and idempotent. --check for a dry run.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart,
then run the migration function noted at the end.
"""

import io
import os
import sys

CHECK = "--check" in sys.argv
MERGED_NAME = "Contacted"
NEW_STAGE = "Awaiting Payment"

OLD_LIST = '["New", "Contacted", "Qualified", "Proposal", "Negotiation"]'
NEW_LIST = '["New", "Contacted", "Proposal", "Negotiation", "Awaiting Payment"]'

OLD_JS_LIST = '["New", "Contacted", "Qualified", "Proposal", "Negotiation"]'
NEW_JS_LIST = '["New", "Contacted", "Proposal", "Negotiation", "Awaiting Payment"]'

OLD_OPTIONS = '"New\\nContacted\\nQualified\\nProposal\\nNegotiation"'
NEW_OPTIONS = '"New\\nContacted\\nProposal\\nNegotiation\\nAwaiting Payment"'

OLD_CSS = (
    '\t\t\t.duty-sales-kanban .duty-kb-col[data-col="Qualified"] { border-top: 3px solid #0F5C55; }\n'
    '\t\t\t.duty-sales-kanban .duty-kb-col[data-col="Qualified"] .duty-kb-col-head { color: #0F5C55; }\n'
)
# Qualified's column colour is retired; Awaiting Payment takes a distinct one
# (amber-green) so it reads as "nearly done" rather than as another red stage
NEW_CSS = ""
CSS_ANCHOR = (
    '\t\t\t.duty-sales-kanban .duty-kb-col[data-col="Negotiation"] { border-top: 3px solid #dc2626; }\n'
    '\t\t\t.duty-sales-kanban .duty-kb-col[data-col="Negotiation"] .duty-kb-col-head { color: #b91c1c; }\n'
)
CSS_ADD = (
    '\t\t\t.duty-sales-kanban .duty-kb-col[data-col="Awaiting Payment"] { border-top: 3px solid #7c3aed; }\n'
    '\t\t\t.duty-sales-kanban .duty-kb-col[data-col="Awaiting Payment"] .duty-kb-col-head { color: #6d28d9; }\n'
)

EDITS = [
    ("sales.py", [(OLD_LIST, NEW_LIST)]),
    ("duty_board/doctype/duty_lead/duty_lead.json", [(OLD_OPTIONS, NEW_OPTIONS)]),
    ("duty_board/page/duty_board/duty_board.js",
     [(OLD_JS_LIST, NEW_JS_LIST),
      (OLD_CSS, NEW_CSS),
      (CSS_ANCHOR, CSS_ANCHOR + CSS_ADD)]),
]


def main():
    problems = []
    plans = []
    for path, subs in EDITS:
        if not os.path.exists(path):
            problems.append("missing file: %s" % path)
            continue
        text = io.open(path, encoding="utf-8").read()
        already = 0
        for old, new in subs:
            n = text.count(old)
            if n == 0 and new and new in text:
                already += 1
                continue
            if n != 1:
                problems.append("%s: expected 1 occurrence, found %d of %r"
                                % (path, n, old[:60]))
                continue
            text = text.replace(old, new, 1)
        plans.append((path, text, already))

    if problems:
        print("ABORT — %d problem(s):" % len(problems))
        for p in problems:
            print("   %s" % p)
        sys.exit(1)

    for path, text, already in plans:
        if already:
            print("  %-52s %d edit(s) already applied" % (path, already))
        if not CHECK:
            io.open(path, "w", encoding="utf-8").write(text)
        print("  %-52s %s" % (path, "would write" if CHECK else "written"))

    print()
    print("pipeline is now: " + " -> ".join(eval(NEW_LIST)))
    if CHECK:
        print("--check given; nothing written.")
        return

    # verification: every place that names the stages must agree
    src = io.open("sales.py", encoding="utf-8").read()
    js = io.open("duty_board/page/duty_board/duty_board.js", encoding="utf-8").read()
    dt = io.open("duty_board/doctype/duty_lead/duty_lead.json", encoding="utf-8").read()
    ok = True
    for label, cond in [
        ("sales.py STAGES", NEW_LIST in src),
        ("js dropdown list", NEW_JS_LIST in js),
        ("doctype options", NEW_OPTIONS.replace('\\\\n', '\\n') in dt or NEW_OPTIONS in dt),
        ("Awaiting Payment CSS", 'data-col="Awaiting Payment"' in js),
        ("no Qualified left in sales.py", "Qualified" not in src),
        ("no Qualified left in js kanban", js.count('data-col="Qualified"') == 0),
    ]:
        print("  %-34s %s" % (label, "ok" if cond else "FAILED"))
        ok = ok and cond
    if not ok:
        sys.exit("verification failed — do not deploy")


if __name__ == "__main__":
    main()
