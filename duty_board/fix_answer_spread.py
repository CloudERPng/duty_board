#!/usr/bin/env python3
"""Rebalance answer positions in the academy question banks.

Four tracks — Closer, Bookkeeper, Consultant, Client Reports — were authored
before the 9/9/9/8 spread discipline, and their correct answers sit almost
entirely in position B. Ten of the fifteen modules are at 100%, so the exam is
passable by a candidate who picks B throughout and has read nothing.

The questions themselves are sound. Only their option ORDER is wrong, so this
repairs rather than rewrites: for each question the option list is rotated
until the correct answer lands on its assigned position, which preserves the
relative order of the distractors and leaves every word of the content alone.

Deterministic. The RNG is seeded per module, so the same input always produces
the same output and a re-run changes nothing — which matters because this has
to be applied to both the seed files and the live database.

Two kinds of question are left alone:
  - options that are numerically ordered (5%, 10%, 15%, 20%), where reordering
    would look like an error to the candidate
  - options anchored by meaning ("all of the above" must stay last)

Usage
  python3 fix_answer_spread.py --check     # report only, write nothing
  python3 fix_answer_spread.py             # rewrite the data files

Run from the app package directory.
"""

import collections
import glob
import json
import os
import random
import re
import sys

FAMILIES = ("closer", "bkpr", "consultant", "client_reports")
CHECK_ONLY = "--check" in sys.argv


def numeric_value(opt):
    m = re.fullmatch(
        r"[^\d]*?(\d[\d,\.]*)\s*(day|days|hour|hours|%|percent|month|months|year|years)?[^\d]*",
        (opt or "").strip(), re.I,
    )
    return float(m.group(1).replace(",", "")) if m else None


def locked(opts):
    """True when option order carries meaning and must not be disturbed."""
    low = [(o or "").strip().lower() for o in opts]
    if any(re.match(r"^(all|none) of (the )?(above|these)", o) for o in low):
        return "anchored"
    if any(re.search(r"\b(both|either|neither)\b.*\b[a-d]\b\s*(and|or)", o) for o in low):
        return "letter-reference"
    nums = [numeric_value(o) for o in opts]
    if all(n is not None for n in nums) and (nums == sorted(nums) or nums == sorted(nums, reverse=True)):
        return "numeric-order"
    return None


def targets_for(n):
    """Positions to spread n correct answers across four options, as evenly as
    the count allows: 35 -> 9,9,9,8; 27 -> 7,7,7,6."""
    base, extra = divmod(n, 4)
    out = []
    for i in range(4):
        out += [i] * (base + (1 if i < extra else 0))
    return out


def rebalance_module(key, mod):
    qs = mod.get("questions") or []
    if not qs:
        return {"key": key, "moved": 0, "skipped": [], "before": {}, "after": {}}

    before = collections.Counter(q["ans"] for q in qs)
    free, skipped = [], []
    for i, q in enumerate(qs):
        why = locked(q["opts"])
        (skipped if why else free).append((i, why))

    rng = random.Random("duty_board:spread:%s" % key)
    slots = targets_for(len(qs))
    # honour the positions already taken by the questions we cannot touch,
    # so the final distribution counts them rather than fighting them
    for i, _why in skipped:
        a = qs[i]["ans"]
        if a in slots:
            slots.remove(a)
    rng.shuffle(slots)

    moved = 0
    for (i, _why), target in zip(free, slots):
        q = qs[i]
        cur = q["ans"]
        if cur == target:
            continue
        shift = (target - cur) % 4
        q["opts"] = q["opts"][-shift:] + q["opts"][:-shift]
        q["ans"] = target
        moved += 1

    after = collections.Counter(q["ans"] for q in qs)
    return {
        "key": key, "moved": moved,
        "skipped": [(i, w) for i, w in skipped],
        "before": dict(sorted(before.items())), "after": dict(sorted(after.items())),
        "n": len(qs),
    }


def main():
    total_moved = total_q = 0
    print("%-20s %-16s %5s %7s   %-18s %-18s %s" % (
        "MODULE", "FILE", "QS", "MOVED", "BEFORE", "AFTER", "GUESS"))
    print("-" * 108)
    for path in sorted(glob.glob("academy_*_data.json")):
        fam = os.path.basename(path).replace("academy_", "").replace("_data.json", "")
        if fam not in FAMILIES:
            continue
        data = json.load(open(path, encoding="utf-8"))
        touched = False
        for key, mod in data.items():
            if not isinstance(mod, dict) or "questions" not in mod:
                continue
            r = rebalance_module(key, mod)
            total_moved += r["moved"]; total_q += r["n"]
            if r["moved"]:
                touched = True
            guess = round(max(r["after"].values()) * 100.0 / r["n"]) if r["n"] else 0
            print("%-20s %-16s %5d %7d   %-18s %-18s %d%%" % (
                key[:20], fam[:16], r["n"], r["moved"],
                " ".join("%s:%d" % ("ABCD"[k], v) for k, v in r["before"].items()),
                " ".join("%s:%d" % ("ABCD"[k], v) for k, v in r["after"].items()),
                guess))
            for i, w in r["skipped"]:
                print("      left alone (q%d, %s): %s" % (i + 1, w, mod["questions"][i]["q"][:58]))
        if touched and not CHECK_ONLY:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
                f.write("\n")

    print("\n%d of %d questions repositioned." % (total_moved, total_q))
    if CHECK_ONLY:
        print("--check given; no files written.")
    else:
        print("Data files rewritten. Now push to the live database:")
        print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.rebalance_banks")


if __name__ == "__main__":
    main()
