#!/usr/bin/env python3
"""Duty Board v3.203.0 — CONSOLIDATED CROSS-TRACK EDITORIAL CORRECTIVE.

Clears the residual banned-phrase debt from the six pro tracks written
before the textbook-register hardening: POS, Accounts, Sysadmin,
Payroll, HR, Inventory. Selling and Procurement are already clean and
are only swept, not edited. The older staff-training tracks (bkpr,
consultant, closer, client_reports) are deliberately out of scope.

Method: ordered, case-preserving phrase replacements applied to every
string in the six data files (longest/most-specific first; the
"point of no return" idiom special-cased ahead of the generic rule),
then a FULL-APP sweep across all eight pro tracks that must come back
zero, plus depth and question-integrity re-validation on every touched
module.

Deploy: apply -> commit -> then on the server, per track:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_pos_pro.refresh_lessons
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_pos_pro.refresh_questions
  (repeat for accounts, sysadmin, payroll, hr, inventory)

Anchored by expected-count assertions, idempotent (guarded by version).
Requires v3.202.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import re
import sys

INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

TARGET_FILES = [
    "duty_board/academy_pos_pro_data.json",
    "duty_board/academy_accounts_pro_data.json",
    "duty_board/academy_sysadmin_pro_data.json",
    "duty_board/academy_payroll_pro_data.json",
    "duty_board/academy_hr_pro_data.json",
    "duty_board/academy_inventory_pro_data.json",
]
SWEEP_ONLY_FILES = [
    "duty_board/academy_sales_pro_data.json",
    "duty_board/academy_procure_pro_data.json",
]

# Ordered: most specific first. Each replacement is register-neutral and
# introduces no banned substring and no 'law'.
MAPPINGS = [
    ("is the point of no return", "is the irreversible step"),   # idiom guard
    ("which is the point", "which is the purpose"),
    (" is the point", " is the purpose"),
    ("the point is", "the purpose is"),
    ("which is why", "and for this reason"),
    ("an archaeology", "a reconstruction"),
    ("archaeology", "reconstruction"),
    ("workhorse layer", "primary working layer"),
    ("workhorse", "primary instrument"),
    ("one heroic annual count", "one all-at-once annual count"),
    ("heroic", "exceptional"),
    ("money on shelves", "working capital on shelves"),
    ("used in anger", "in live use"),
    ("cheap moment", "low-cost moment"),
    ("cheapest", "lowest-cost"),
    ("doing its job", "operating as designed"),
    ("doing their job", "operating as designed"),
    ("paying off", "yielding returns"),
    ("pays for itself", "recovers its cost"),
    ("earning its keep", "demonstrating its value"),
    ("worst moment", "least convenient moment"),
    ("boring", "routine"),
]

# The full validation list (frozen editorial ban + legacy voice list).
BANNED = ["network breathes", "not a conversation", "wrong by construction",
          "tight cycle", "workhorse", "dissolving", "boundaries are tested",
          "teaches padding", "paying off", "buys nothing", "honest use",
          "informal lanes", "honesty rule", "dying quietly",
          "which is the point", "the one idea", "here is the trap",
          "keeps it honest", "earning its keep", " is the point",
          "the point is", "which is why", "with sighs", "worst moment",
          "dispute generator", "side door", "at zero cost", "cheap moment",
          "cheapest", "spends the business", "login attached",
          "proves its worth", "the defence", "state wrongly",
          "conducted from memory", "priceless", "archaeology", "boring",
          "heroic", "money on shelves", "used in anger", "pays for itself",
          "doing its job", "doing their job", "montaigne",
          "certified professional", "the consultant", "consultants",
          "the academy", "this academy", "engagement", "constitution",
          "costume", "scar tissue", "witness", "testimony"]


def _preserve_case(repl):
    def inner(m):
        src = m.group(0)
        if src[:1].isupper() or (src[:1] == " " and src[1:2].isupper()):
            if repl[:1] == " ":
                return " " + repl[1:2].upper() + repl[2:]
            return repl[:1].upper() + repl[1:]
        return repl
    return inner


def apply_mappings(text, counter):
    for old, new in MAPPINGS:
        pat = re.compile(re.escape(old), re.IGNORECASE)
        text, n = pat.subn(_preserve_case(new), text)
        if n:
            counter[old] = counter.get(old, 0) + n
    return text


def walk(obj, counter):
    if isinstance(obj, str):
        return apply_mappings(obj, counter)
    if isinstance(obj, list):
        return [walk(x, counter) for x in obj]
    if isinstance(obj, dict):
        return {k: walk(v, counter) for k, v in obj.items()}
    return obj


def sweep(path, enforce_law):
    """Return (findings, law_count) for one data file."""
    with io.open(path, encoding="utf-8") as f:
        d = json.load(f)
    findings = []
    law_count = 0
    for mod, m in d.items():
        blob = json.dumps(m, ensure_ascii=False)
        low = blob.lower()
        for w in BANNED + ["erpnext"]:
            if w in low:
                findings.append(f"{os.path.basename(path)}/{mod}: '{w}'")
        n = len(re.findall(r"\b[Ll]aws?\b", blob))
        law_count += n
        if n and enforce_law:
            findings.append(f"{os.path.basename(path)}/{mod}: 'law' x{n}")
    return findings, law_count


def integrity(path):
    """Depth + question integrity for one data file."""
    with io.open(path, encoding="utf-8") as f:
        d = json.load(f)
    probs = []
    for mod, m in d.items():
        for l in m.get("lessons", []):
            if len(l["html"]) < 2500:
                probs.append(f"{os.path.basename(path)}/{mod}: depth {l['title'][:40]} ({len(l['html'])})")
        qs = m.get("questions", [])
        if len(qs) != 35:
            probs.append(f"{os.path.basename(path)}/{mod}: {len(qs)} questions")
        for q in qs:
            if len(q["opts"]) != 4 or len(set(q["opts"])) != 4 or not (0 <= q["ans"] <= 3):
                probs.append(f"{os.path.basename(path)}/{mod}: malformed '{q['q'][:40]}'")
    return probs


def main():
    root = os.getcwd()
    init_path = os.path.join(root, INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()

    if '"3.203.0"' in init:
        print("Already applied. Nothing to do.")
        return
    if '"3.202.0"' not in init:
        sys.exit("ABORT: not at v3.202.0.")

    total = 0
    per_file = {}
    staged = {}
    for rel in TARGET_FILES:
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            sys.exit(f"ABORT: missing {rel}")
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
        counter = {}
        new_data = walk(data, counter)
        n = sum(counter.values())
        per_file[rel] = counter
        total += n
        staged[path] = new_data

    print(f"REPLACEMENTS PLANNED: {total} across {len(TARGET_FILES)} files")
    for rel, counter in per_file.items():
        if counter:
            det = ", ".join(f"'{k}' x{v}" for k, v in sorted(counter.items()))
            print(f"  {os.path.basename(rel)}: {sum(counter.values())}  [{det}]")
        else:
            print(f"  {os.path.basename(rel)}: 0")

    if total < 60 or total > 130:
        sys.exit(f"ABORT: replacement count {total} outside expected band 60-130 — re-scan before applying.")

    # Validate staged content BEFORE writing anything.
    stage_probs = []
    for path, new_data in staged.items():
        for mod, m in new_data.items():
            blob = json.dumps(m, ensure_ascii=False)
            low = blob.lower()
            for w in BANNED + ["erpnext"]:
                if w in low:
                    stage_probs.append(f"{os.path.basename(path)}/{mod}: residual '{w}'")
            for l in m.get("lessons", []):
                if len(l["html"]) < 2500:
                    stage_probs.append(f"{os.path.basename(path)}/{mod}: depth {l['title'][:40]} ({len(l['html'])})")
            qs = m.get("questions", [])
            if len(qs) != 35:
                stage_probs.append(f"{os.path.basename(path)}/{mod}: {len(qs)} questions")
            for q in qs:
                if len(q["opts"]) != 4 or len(set(q["opts"])) != 4 or not (0 <= q["ans"] <= 3):
                    stage_probs.append(f"{os.path.basename(path)}/{mod}: malformed '{q['q'][:40]}'")
    if stage_probs:
        print("ABORT — staged content not clean:")
        print("\n".join("  " + p for p in stage_probs))
        sys.exit(1)
    print("STAGED VALIDATION: clean (bans zero, depth held, banks intact)")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for path, new_data in staged.items():
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print(f"  wrote {os.path.basename(path)}")

    with io.open(init_path, "w", encoding="utf-8") as f:
        f.write(init.replace('"3.202.0"', '"3.203.0"'))
    print("wrote __version__ -> 3.203.0")

    # FULL-APP SWEEP: all eight pro tracks must come back zero.
    print("\nFULL-APP SWEEP (eight pro tracks):")
    all_findings = []
    for rel in TARGET_FILES + SWEEP_ONLY_FILES:
        path = os.path.join(root, rel)
        enforce_law = rel in SWEEP_ONLY_FILES
        f1, law_n = sweep(path, enforce_law)
        f2 = integrity(path)
        all_findings += f1 + f2
        law_note = "" if enforce_law else f"  ('law' x{law_n} — out of scope, reported only)"
        print(f"  {os.path.basename(rel)}: {'CLEAN' if not (f1 or f2) else 'ISSUES ' + str(f1 + f2)}{law_note}")
    if all_findings:
        sys.exit("SWEEP FAILED — see findings above.")
    print("SWEEP: ALL EIGHT PRO TRACKS CLEAN on the banned-phrase register.")
    print("NOTE: the \\blaw\\b register rule remains enforced on Selling/Procurement only;")
    print("      older tracks' counts reported above for a possible follow-up pass.")


if __name__ == "__main__":
    main()
