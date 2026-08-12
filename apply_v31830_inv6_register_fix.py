#!/usr/bin/env python3
"""Duty Board v3.183.0 — INVENTORY 6 REGISTER CORRECTION (formal manual
tone; flattens the editorial phrasing that slipped into v3.182.0).

Anchored counted replaces on branch_network lessons, questions, and
description. No structural change: 9 chapters, 35 questions unchanged
in count and coverage.

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_inventory_pro.refresh_lessons --kwargs "{'only': 'branch_network'}"
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_inventory_pro.refresh_questions --kwargs "{'only': 'branch_network'}"

Idempotent. Requires v3.182.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_inventory_pro_data.json"
CHECK_ONLY = "--check" in sys.argv

# (old, new, expected_count) across the module's lesson html
LESSON_FIXES = [
 ("The network breathes on a cycle. This chapter is the weekly procedure, step by step, as the stock manager runs it.",
  "The replenishment cycle runs weekly. This chapter is the procedure, step by step, as the stock manager runs it.", 1),
 ("the reads (Chapter 7) are how the center answers for stock it cannot see from a desk. The division is the programme's standing shape:",
  "the reads (Chapter 7) are how the center maintains oversight of stock at remote sites. The division is the programme's standing shape:", 1),
 ("The center answers for stock it cannot see. These reads are how. Each is stated with",
  "These reads give the center its oversight of stock at remote sites. Each is stated with", 1),
 ("adjusted quantities carry one-line reasons back to the branch, because a silent cut teaches padding and a reasoned one teaches the arithmetic",
  "adjusted quantities carry one-line reasons back to the branch, so the branch can correct its next request from the same data", 1),
 ("documented, and communicated \u2014 never by who asked loudest or last.",
  "documented, and communicated.", 1),
 ("the answer is a calculation, not a conversation.",
  "the answer is the recorded calculation.", 1),
 ("<b>opening estimates are always wrong \u2014 so the first cycle reads tight.</b>",
  "<b>opening estimates differ from actual demand \u2014 so the first ninety days run on a weekly review cycle.</b>", 1),
 ("The honesty rule is stated in the plan itself: these figures are estimates, they will be wrong item by item, and the correction mechanism is the tight first cycle (step 4), not debate over the estimates.",
  "The plan states the standing assumption: these figures are estimates, they will differ from actual demand item by item, and the correction mechanism is the first-cycle review (step 4), not revision of the estimates.", 1),
 ("The reconciliation instrument at a branch opening has exactly one honest use: nothing (the go-live Opening Stock purpose belongs to the company's original implementation, not to branch expansion).",
  "The reconciliation instrument is not used at branch openings; the Opening Stock purpose belongs to the company's original implementation, not to branch expansion.", 1),
 ("<b>4. The first ninety days \u2014 the tight cycle.</b> Because the opening estimates are wrong by construction:",
  "<b>4. The first ninety days \u2014 the weekly review cycle.</b> Because the opening estimates will differ from actual demand:", 1),
 ("A lateral is not an informal favour between branch managers; it is a transfer with every discipline attached.",
  "A lateral is a standard transfer with every control applied.", 1),
 ("a branch appearing repeatedly is a replenishment failure to fix at the run (the levels, the cadence, the transit time), not a boundary to keep waiving \u2014 the exception that becomes a habit is the boundary dissolving in slow motion.",
  "a branch appearing repeatedly is a replenishment failure to fix at the run (the levels, the cadence, the transit time); recurring exceptions indicate the boundary is no longer being enforced.", 1),
 ("Every flow in this chapter is the standard machinery with a reason attached \u2014 the network has no informal lanes.",
  "Every flow in this chapter uses the standard documents with a recorded reason.", 1),
 ("This read is the module's workhorse \u2014 it feeds",
  "This read is the module's most frequently used figure \u2014 it feeds", 1),
 ("(the Stock Balance at the site's node \u2014 module 1's tree paying off)",
  "(the Stock Balance at the site's group node, using module 1's tree structure)", 1),
 ("<b>The tight cycle:</b> weekly line-by-line sell-through review for <b>ninety days</b>. Week three already shows the pattern the plan predicted it could not predict: four lines selling at twice the estimate, a tail of slow openers flagged early.",
  "<b>The weekly review cycle:</b> line-by-line sell-through review for <b>ninety days</b>. Week three shows the first differences from the estimates: four lines selling at twice the estimate, and a tail of slow openers flagged early.", 1),
 ("the exception-purchase list empty \u2014 the boundary holding through a scarce month, which is when boundaries are actually tested.",
  "the exception-purchase list empty \u2014 the boundary held through the scarce month.", 1),
 ("Correction: the tight cycle started late \u2014 weekly reads, levels from actuals. Prevention: the honesty rule written into the opening plan: estimates are wrong by construction, and the first ninety days read weekly.",
  "Correction: the weekly review cycle started late \u2014 weekly reads, levels from actuals. Prevention: the standing assumption written into the opening plan: estimates differ from actual demand, and the first ninety days are reviewed weekly.", 1),
 ("Prevention: Chapter 4's arithmetic \u2014 pro-rata on sell-through ignores the ask's size, so padding buys nothing and shows in the review.",
  "Prevention: Chapter 4's arithmetic \u2014 pro-rata on sell-through ignores the size of the ask, so padding does not change the allocation and is visible in the review.", 1),
 ("Prevention: the monthly exception list to the owner, read as a replenishment health report rather than a permissions log.",
  "Prevention: the monthly exception list to the owner, reviewed for replenishment failures at their source.", 1),
 ("open a branch by transfer with the ninety-day tight cycle and day-sixty levels",
  "open a branch by transfer with the ninety-day weekly review cycle and day-sixty levels", 1),
 ("branches opened by transfer and read tight for ninety days",
  "branches opened by transfer and reviewed weekly for ninety days", 1),
 ("with the plan stating the honesty rule: these are estimates and the first cycle will correct them.",
  "with the plan stating the standing assumption: these are estimates and the first-cycle review will correct them.", 1),
 ("recurring monthly; the boundary dissolving in slow motion. Correction:",
  "recurring monthly; the boundary no longer enforced. Correction:", 1),
 ("executed as standard transfers with reasons \u2014 no informal lanes.",
  "executed as standard transfers with recorded reasons.", 1),
]

# (old, new, expected_count) across the module's questions JSON
QUESTION_FIXES = [
 ("\"Informal\"", "\"Decentralised buying\"", 1),
 ("A silent cut teaches padding; a reasoned one teaches arithmetic.",
  "Adjustments carry one-line reasons back to the branch.", 1),
 ("\"Who asked loudest\"", "\"Request order\"", 1),
 ("Documented and communicated, never argued.", "Documented and communicated.", 1),
 ("Why the other site got more \u2014 as a calculation, not a conversation",
  "Why one site received more than another \u2014 from the recorded calculation", 1),
 ("Padding cannot move it.", "The arithmetic ignores the size of the ask.", 1),
 ("Type quantities and rates into existence with no documents \u2014 module 5's opening hazards recreated voluntarily",
  "Enter quantities and rates with no documents behind them \u2014 module 5's opening hazards repeated", 1),
 ("Wrong by construction \u2014 corrected by the tight first cycle, not defended",
  "Estimates that will differ from actual demand \u2014 corrected by the first-cycle reviews", 1),
 ("\"Secrets\"", "\"Final figures\"", 1),
 ("The honesty rule in the plan itself.", "Stated in the opening plan.", 1),
 ("Weekly line-by-line sell-through reads, replenishment on data, levels written at day sixty, first count inside month one",
  "Weekly line-by-line sell-through reviews, replenishment on data, levels written at day sixty, first count inside month one", 1),
 ("The tight cycle.", "The first ninety days' procedure.", 1),
 ("\"Good teamwork\"", "\"Normal operations\"", 1),
 ("\"More trucks needed\"", "\"A transport issue\"", 1),
 ("\"Resourceful\"", "\"Operating normally\"", 1),
 ("\"Lucky\"", "\"Efficient\"", 1),
 ("\"Fined\"", "\"Ignored\"", 1),
 ("A replenishment failure to fix at the run \u2014 not a boundary to keep waiving",
  "A replenishment failure to fix at the run \u2014 the levels, the cadence, or the transit assumption", 1),
 ("The habit is the boundary dissolving.", "Recurring exceptions indicate a replenishment failure.", 1),
 ("per item per branch \u2014 the module's workhorse figure", "per item per branch \u2014 the module's most frequently used figure", 1),
 ("\"A theft signal\"", "\"A count error\"", 1),
 ("The exception-purchase list staying empty \u2014 boundaries are tested exactly when supply is short",
  "The exception-purchase list staying empty through the shortage", 1),
 ("\"Hidden\"", "\"Retained\"", 1),
 ("The tight cycle catching slow openers young.", "The weekly review flagging slow openers early.", 1),
 ("The tight cycle's first proof.", "The first cycle count verifying the bins.", 1),
 ("The first cycle count inside month one, the opening file complete",
  "Bins verified by the first cycle count inside month one, the opening file complete", 0),
 ("branches opened by transfer and read tight, every flow through the standard machinery with a reason",
  "branches opened by transfer and reviewed weekly, every flow through the standard documents with a recorded reason", 1),
]

DESC_FIXES = [
 ("opening a new branch by transfer with the ninety-day tight cycle and day-sixty reorder levels",
  "opening a new branch by transfer with the ninety-day weekly review cycle and day-sixty reorder levels", 1),
 ("the weekly replenishment run \u2014 inputs, the reasoned review pass, the despatch pass through transit, and the closing note",
  "the weekly replenishment run \u2014 inputs, the review pass with reasoned adjustments, the despatch pass through transit, and the closing note", 1),
]


def _apply(blob, fixes, where):
    for old, new, exp in fixes:
        n = blob.count(old)
        if exp == 0:
            if n:
                blob = blob.replace(old, new)
                print(f"  optional fix applied ({n}x): {old[:50]}")
            continue
        if n != exp:
            sys.exit(f"ABORT: anchor found {n}x (expected {exp}) in {where}: {old[:70]}")
        blob = blob.replace(old, new)
    return blob


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    if '"3.183.0"' in init:
        print("Already applied. Nothing to do.")
        return
    if '"3.182.0"' not in init:
        sys.exit("ABORT: not at v3.182.0.")

    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)
    mod = data["branch_network"]

    lessons_blob = json.dumps(mod["lessons"], ensure_ascii=False)
    lessons_blob = _apply(lessons_blob, LESSON_FIXES, "lessons")
    mod["lessons"] = json.loads(lessons_blob)

    q_blob = json.dumps(mod["questions"], ensure_ascii=False)
    q_blob = _apply(q_blob, QUESTION_FIXES, "questions")
    mod["questions"] = json.loads(q_blob)

    d_blob = json.dumps(mod["desc"], ensure_ascii=False)
    d_blob = _apply(d_blob, DESC_FIXES, "desc")
    mod["desc"] = json.loads(d_blob)

    # validation: structure preserved, register scan
    import re
    problems = []
    if len(mod["lessons"]) != 9:
        problems.append(f"  lessons: {len(mod['lessons'])}")
    if len(mod["questions"]) != 35:
        problems.append(f"  questions: {len(mod['questions'])}")
    short = [f"{l['title'][:40]} ({len(l['html'])})" for l in mod["lessons"] if len(l["html"]) < 2500]
    if short:
        problems.append(f"  below depth: {short}")
    for q in mod["questions"]:
        if len(q["opts"]) != 4 or len(set(q["opts"])) != 4:
            problems.append(f"  malformed opts: {q['q'][:40]}")
    blob = json.dumps(mod, ensure_ascii=False)
    for phrase in ["network breathes", "not a conversation", "who asked loudest", "wrong by construction",
                   "tight cycle", "read tight", "workhorse", "dissolving", "boundaries are tested",
                   "predicted it could not predict", "teaches padding", "paying off", "buys nothing",
                   "honest use", "informal lanes", "honesty rule"]:
        if phrase in blob.lower():
            problems.append(f"  residual editorial phrase: '{phrase}'")
    if re.search(r"\b[Ll]aws?\b", blob):
        problems.append("  law leakage")
    if "ERPNext" in blob:
        problems.append("  ERPNext leakage")
    if problems:
        print("ABORT — validation failed:")
        print("\n".join(problems))
        sys.exit(1)
    dist = {c: sum(1 for q in mod["questions"] if q["ans"] == i) for i, c in enumerate("ABCD")}
    print(f"INV 6 corrected: 9 chapters ({sum(len(l['html']) for l in mod['lessons']):,} chars, min {min(len(l['html']) for l in mod['lessons']):,}), bank 35, spread {dist}")
    print("register scan: CLEAN (all editorial phrases removed)")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.182.0"', '"3.183.0"'))
    print("  data: INVENTORY 6 register corrected (formal manual tone)")
    print("wrote __version__ -> 3.183.0")


if __name__ == "__main__":
    main()
