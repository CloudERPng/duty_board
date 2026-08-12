#!/usr/bin/env python3
"""Duty Board v3.190.0 — SELLING 1-4 REGISTER TIGHTENING (textbook
manual tone).

Flattens the consultative constructions that remained after the
editorial-phrase ban: rhetorical framings (is the point / which is why /
side door / cheap moment), vivid-consequence phrasing (worst moment /
dispute generator / with sighs), and colour (priceless / at zero cost /
login attached). Anchored counted replaces on four modules; no
structural change.

Deploy: apply -> commit -> then refresh lessons+questions for
customers, items_prices, quotations, sales_orders.

Idempotent. Requires v3.189.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_sales_pro_data.json"
CHECK_ONLY = "--check" in sys.argv

FIXES = {
"customers": {
 "lessons": [
  ("because a missing TIN discovered at invoicing blocks the document at the worst moment.",
   "because a missing TIN prevents the invoice from being submitted when invoicing is due.", 1),
  ("Every field Chapter 2 walked is cheap to complete at creation and expensive to fix in flight: the wrong group prices",
   "Every field Chapter 2 walked is quick to complete at creation and costly to correct after documents exist: the wrong group prices", 1),
  ("The read is cheap while the register is young and priceless once collections depend on whole balances.",
   "The read requires little effort while the register is small, and becomes essential once collections depend on complete balances.", 1),
 ],
 "questions": [
  ("a missing TIN blocks invoicing at the worst moment",
   "a missing TIN prevents invoice submission when invoicing is due", 1),
 ],
},
"items_prices": {
 "lessons": [
  ("an unauthorised change is a margin leak with a login attached.",
   "an unauthorised change is a margin loss attributable to a specific user account.", 1),
 ],
 "questions": [],
},
"quotations": {
 "lessons": [
  ("The pre-fill is the point \u2014 verify it rather than retype it.",
   "The pre-fill is the intended behaviour \u2014 verify it rather than retype it.", 1),
  ("\u2014 the inheritance is the point: the agreement the customer accepted is what the order states, without re-keying and without re-keying's errors.",
   "\u2014 this inheritance ensures the order states exactly what the customer accepted, without re-keying and without re-keying errors.", 1),
  ("inherits what the quotation states, which is why the offer is built from the registers (modules 1-2) rather than composed freehand:",
   "inherits what the quotation states. The offer is therefore built from the registers (modules 1-2) rather than composed freehand:", 1),
  ("quoting exclusive and invoicing inclusive is a dispute generator, and the template discipline prevents it.",
   "quoting tax-exclusive and invoicing tax-inclusive causes disputes; the template discipline prevents it.", 1),
  ("prices and credit are the two places a sales document spends the business's money, and both move only with named approval.",
   "prices and credit are the two areas where a sales document commits the business's money, and both move only with named approval.", 1),
  ("the file's version thread is the defence.",
   "the file's version thread is the control against this.", 1),
  ("becomes a dispute conducted from memory.",
   "becomes a dispute with no reference document.", 1),
 ],
 "questions": [
  ("The inheritance is the point.", "The inheritance prevents re-keying errors.", 1),
  ("A dispute generator \u2014 the template discipline keeps",
   "A cause of disputes \u2014 the template discipline keeps", 1),
 ],
},
"sales_orders": {
 "lessons": [
  ("\u2014 which is why the check runs here and not only at invoicing.",
   ". For this reason the check runs at submission and not only at invoicing.", 1),
  ("The read's output is a short list with owners, not a long list with sighs.",
   "The read's output is a short list of rows, each with a named owner and action.", 1),
  ("An order amendment is not a side door around the offer's approvals; the concession",
   "An order amendment does not bypass the offer's approvals; the concession", 1),
  ("Error 3 \u2014 the amendment side door.",
   "Error 3 \u2014 the amendment bypass.", 1),
  ("The confirmation pass proves its worth at zero cost: Montaigne AH's operations team confirms",
   "The confirmation step performs its function: Montaigne AH's operations team confirms", 1),
  ("The confirmation is the last cheap moment to catch a disagreement: the customer reading their own commitment back finds the wrong quantity or date now, against a document, rather than at the delivery dock against a truck.",
   "The confirmation is the final opportunity to catch a disagreement before execution: the customer reads their own commitment back and finds any wrong quantity or date now, against a document, rather than at delivery.", 1),
  ("this module's disciplines exist because commitments are expensive to state wrongly.",
   "this module's disciplines exist because an incorrectly stated commitment is costly to correct.", 1),
  ("service-level conversations conducted from memory.",
   "service-level reviews with no documentary record.", 1),
 ],
 "questions": [
  ("Re-enter the deviation ladder \u2014 an amendment is not a side door around the offer's approvals",
   "Re-enter the deviation ladder \u2014 an amendment does not bypass the offer's approvals", 1),
  ("Nothing \u2014 Montaigne AH confirmed the branch sequence against their own plan before anything shipped, at zero cost",
   "Nothing \u2014 Montaigne AH confirmed the branch sequence against their own plan before anything shipped", 1),
  ("The cheap moment used.", "The confirmation step performing its function.", 1),
  ("The last cheap moment to catch a disagreement \u2014 the customer reads their commitment back against a document",
   "The final pre-execution check \u2014 the customer reads their commitment back against a document", 1),
 ],
},
}

RESIDUAL_SCAN = [" is the point", "the point is", "which is why", "with sighs", "worst moment",
                 "dispute generator", "side door", "at zero cost", "cheap moment",
                 "spends the business", "login attached", "proves its worth", "the defence",
                 "state wrongly", "conducted from memory", "priceless", "expensive to fix in flight"]


def _apply(blob, fixes, where):
    for old, new, exp in fixes:
        n = blob.count(old)
        if n != exp:
            sys.exit(f"ABORT: anchor found {n}x (expected {exp}) in {where}: {old[:70]}")
        blob = blob.replace(old, new)
    return blob


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    if '"3.190.0"' in init:
        print("Already applied. Nothing to do.")
        return
    if '"3.189.0"' not in init:
        sys.exit("ABORT: not at v3.189.0.")

    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)

    n_l = n_q = 0
    for key, sets in FIXES.items():
        mod = data[key]
        lb = json.dumps(mod["lessons"], ensure_ascii=False)
        lb = _apply(lb, sets["lessons"], f"{key} lessons")
        mod["lessons"] = json.loads(lb)
        n_l += len(sets["lessons"])
        if sets["questions"]:
            qb = json.dumps(mod["questions"], ensure_ascii=False)
            qb = _apply(qb, sets["questions"], f"{key} questions")
            mod["questions"] = json.loads(qb)
        n_q += len(sets["questions"])

    # validation: structure + residual scan on the four modules
    problems = []
    for key in FIXES:
        mod = data[key]
        if len(mod["questions"]) != 35:
            problems.append(f"  {key}: {len(mod['questions'])} questions")
        short = [l["title"][:40] for l in mod["lessons"] if len(l["html"]) < 2500]
        if short:
            problems.append(f"  {key} below depth: {short}")
        low = json.dumps(mod, ensure_ascii=False).lower()
        for p in RESIDUAL_SCAN:
            if p in low:
                problems.append(f"  {key}: residual '{p}'")
    if problems:
        print("ABORT — validation failed:")
        print("\n".join(problems))
        sys.exit(1)
    print(f"SELL 1-4 tightened: {n_l} lesson fixes + {n_q} question fixes; residual scan CLEAN; structure preserved")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.189.0"', '"3.190.0"'))
    print("  data: SELLING 1-4 register tightened (textbook manual tone)")
    print("wrote __version__ -> 3.190.0")


if __name__ == "__main__":
    main()
