#!/usr/bin/env python3
"""Academy content auditor.

Checks every academy_*_data.json in the app against the standards the eight
professional tracks were rewritten to, and reports what falls short.

The check that matters most is answer spread. A bank whose correct answers
cluster on one option can be passed by someone who picks that option every
time and has read nothing — which makes the certificate false rather than
merely thin. It is invisible in the app, because the exam shuffles the display
order per serve, so only an audit of the bank itself will find it.

Usage
  python3 audit_academy.py                 # audit everything, summary table
  python3 audit_academy.py --detail KEY    # one module, question by question
  python3 audit_academy.py --file NAME     # one data file
  python3 audit_academy.py --json          # machine-readable, for CI

Run from the app package directory (the one holding academy_*_data.json):
  cd ~/frappe-bench/apps/duty_board/duty_board && python3 audit_academy.py

Note: this audits the SEED files, which is where content is authored. If a
lesson has been edited in the desk since seeding, the database is the truth
and this will not see it.
"""

import collections
import glob
import json
import os
import re
import sys

# ---- the standards, in one place so they can be argued with -----------------
STD = {
    "chapters_min": 9,          # chapters per module
    "chars_min": 2500,          # per chapter, hard floor
    "chars_target": 2700,       # per chapter, mean target
    "bank_min": 35,             # questions per module
    "spread_max": 10,           # most-frequent correct option, out of 35
    "guess_max": 40,            # % scored by always picking the commonest option
    "checks_per_chapter": 3,    # formative end-of-lesson checks
}

# From the v3.203.0 consolidated editorial corrective.
BANNED = [
    "delve", "tapestry", "testament to", "in today's", "it's worth noting",
    "at the end of the day", "game-changer", "game changer", "seamless",
    "cutting-edge", "best-in-class", "synergy", "paradigm", "holistic",
    "unlock", "empower", "ever-evolving", "furthermore", "moreover",
    "in conclusion", "dive into", "deep dive", "navigate the", "the world of",
    "landscape of", "realm of", "when it comes to", "needless to say",
]

LETTERS = "ABCD"


def strip_html(s):
    return re.sub(r"<[^>]+>", " ", s or "")


def correct_index(q):
    """Banks have used two conventions: 'ans' as a 0-based index, and
    'correct' as a letter. Normalise both to an index."""
    if "ans" in q and q["ans"] is not None:
        try:
            return int(q["ans"])
        except (TypeError, ValueError):
            pass
    c = (q.get("correct") or "").strip().upper()
    return LETTERS.index(c) if c in LETTERS else -1


def audit_module(key, mod):
    lessons = mod.get("lessons") or []
    qs = mod.get("questions") or []
    bodies = [strip_html(l.get("html") or l.get("content") or "") for l in lessons]
    lens = [len(b) for b in bodies]

    spread = collections.Counter()
    no_key = 0
    for q in qs:
        i = correct_index(q)
        if i < 0:
            no_key += 1
        else:
            spread[i] += 1
    top_n = max(spread.values()) if spread else 0
    guess = round(top_n * 100.0 / len(qs)) if qs else 0

    topics = sum(1 for q in qs if (q.get("topic") or "").strip())
    checks = sum(len(l.get("checks") or []) for l in lessons)

    banned = collections.Counter()
    for b in bodies:
        t = b.lower()
        for w in BANNED:
            n = t.count(w)
            if n:
                banned[w] += n

    fails = []
    if len(lessons) < STD["chapters_min"]:
        fails.append("chapters %d<%d" % (len(lessons), STD["chapters_min"]))
    if lens and min(lens) < STD["chars_min"]:
        fails.append("thin chapter %d" % min(lens))
    if lens and (sum(lens) / len(lens)) < STD["chars_target"]:
        fails.append("mean %d" % (sum(lens) / len(lens)))
    if len(qs) < STD["bank_min"]:
        fails.append("bank %d<%d" % (len(qs), STD["bank_min"]))
    if guess > STD["guess_max"]:
        fails.append("GUESSABLE %d%%" % guess)
    if no_key:
        fails.append("%d unkeyed" % no_key)
    if topics < len(qs):
        fails.append("topics %d/%d" % (topics, len(qs)))
    if checks < len(lessons) * STD["checks_per_chapter"]:
        fails.append("checks %d/%d" % (checks, len(lessons) * STD["checks_per_chapter"]))
    if banned:
        fails.append("banned %d" % sum(banned.values()))

    return {
        "key": key,
        "title": mod.get("title", key),
        "chapters": len(lessons),
        "chars_mean": int(sum(lens) / len(lens)) if lens else 0,
        "chars_min": min(lens) if lens else 0,
        "bank": len(qs),
        "spread": {LETTERS[i] if i < 4 else str(i): n for i, n in sorted(spread.items())},
        "guess": guess,
        "unkeyed": no_key,
        "topics": topics,
        "checks": checks,
        "banned": dict(banned),
        "fails": fails,
    }


def load_all(only_file=None):
    out = []
    for path in sorted(glob.glob("academy_*_data.json")):
        if only_file and only_file not in path:
            continue
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print("  !! %s unreadable: %s" % (path, e))
            continue
        for key, mod in data.items():
            if isinstance(mod, dict) and "lessons" in mod:
                r = audit_module(key, mod)
                r["file"] = os.path.basename(path)
                out.append(r)
    return out


def detail(key):
    for path in sorted(glob.glob("academy_*_data.json")):
        data = json.load(open(path, encoding="utf-8"))
        if key not in data:
            continue
        mod = data[key]
        print("== %s — %s (%s)\n" % (key, mod.get("title", ""), os.path.basename(path)))
        for i, l in enumerate(mod.get("lessons") or [], 1):
            body = strip_html(l.get("html") or l.get("content") or "")
            flag = "  <-- thin" if len(body) < STD["chars_min"] else ""
            print("  ch%-2d %-52s %6d chars%s" % (i, (l.get("title") or "")[:52], len(body), flag))
        print()
        for i, q in enumerate(mod.get("questions") or [], 1):
            ci = correct_index(q)
            print("  q%-3d [%s] %s" % (i, LETTERS[ci] if 0 <= ci < 4 else "?", (q.get("q") or "")[:72]))
        return
    print("No module with key %r." % key)


def main():
    args = sys.argv[1:]
    if "--detail" in args:
        return detail(args[args.index("--detail") + 1])
    only = args[args.index("--file") + 1] if "--file" in args else None
    rows = load_all(only)
    if not rows:
        print("No academy_*_data.json found. Run from the app package directory.")
        return
    if "--json" in args:
        print(json.dumps(rows, indent=1))
        return

    print("%-22s %-26s %3s %6s %5s %5s %-16s %s" % (
        "MODULE", "FILE", "CH", "MEAN", "BANK", "GUESS", "SPREAD", "VERDICT"))
    print("-" * 132)
    bad = []
    for r in sorted(rows, key=lambda x: (-x["guess"], x["file"], x["key"])):
        verdict = "ok" if not r["fails"] else ", ".join(r["fails"][:3])
        if r["fails"]:
            bad.append(r)
        print("%-22s %-26s %3d %6d %5d %4d%% %-16s %s" % (
            r["key"][:22], r["file"].replace("academy_", "").replace("_data.json", "")[:26],
            r["chapters"], r["chars_mean"], r["bank"], r["guess"],
            " ".join("%s:%d" % (k, v) for k, v in r["spread"].items())[:16],
            verdict))

    print("\n%d module(s) audited, %d with findings.\n" % (len(rows), len(bad)))

    danger = [r for r in rows if r["guess"] > STD["guess_max"]]
    if danger:
        print("GUESSABLE BANKS — a candidate who always picks the commonest option scores:")
        for r in sorted(danger, key=lambda x: -x["guess"]):
            print("   %-22s %3d%%   (pass mark is 70%%)" % (r["key"], r["guess"]))
        print("   These certificates do not certify anything. Fix before anything else.\n")

    unkeyed = [r for r in rows if r["unkeyed"]]
    if unkeyed:
        print("UNKEYED QUESTIONS (no usable correct answer):")
        for r in unkeyed:
            print("   %-22s %d" % (r["key"], r["unkeyed"]))
        print()

    allbanned = collections.Counter()
    for r in rows:
        allbanned.update(r["banned"])
    if allbanned:
        print("BANNED PHRASES across the estate:")
        for w, n in allbanned.most_common(12):
            print("   %-24s %d" % (w, n))


if __name__ == "__main__":
    main()
