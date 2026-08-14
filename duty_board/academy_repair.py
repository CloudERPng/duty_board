"""Academy repair: push corrected question banks to the live database.

The seeds are insert-only — seed_closer_tracks and its siblings skip any module
that already exists — so correcting academy_*_data.json does nothing to a site
that has already been seeded. This closes that gap.

rebalance_banks() reads the (already corrected) data files and updates the
matching Duty Quiz Question records in place: the four options and the correct
letter, nothing else. Question text, rationale and source are the match keys and
are never written, so a question edited in the desk is found rather than
clobbered, and anything it cannot match is reported rather than guessed at.

Idempotent: a record already holding the target arrangement is left untouched,
so running it twice is the same as running it once.

  bench --site xlevel.clouderp.one execute duty_board.academy_repair.rebalance_banks
  bench --site xlevel.clouderp.one execute duty_board.academy_repair.rebalance_banks --kwargs "{'dry_run': 1}"
  bench --site xlevel.clouderp.one execute duty_board.academy_repair.verify_spread
"""

import collections
import json
import os

import frappe

FAMILIES = ("closer", "bkpr", "consultant", "client_reports")
ALL_FAMILIES = ("accounts_pro", "bkpr", "client_reports", "closer", "consultant",
                "hr_pro", "inventory_pro", "payroll_pro", "pos_pro",
                "procure_pro", "sales_pro", "sysadmin_pro")
LETTERS = "ABCD"


def _data_files(families=FAMILIES):
    here = os.path.dirname(os.path.abspath(__file__))
    for fam in families:
        path = os.path.join(here, "academy_%s_data.json" % fam)
        if os.path.exists(path):
            yield fam, path


def _norm(s):
    return " ".join((s or "").split()).strip().lower()


def rebalance_banks(dry_run=0):
    """Align live question banks with the corrected data files."""
    dry_run = int(dry_run or 0)
    updated = matched = missing_mod = missing_q = already = 0
    report = []

    for fam, path in _data_files():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, mod in data.items():
            if not isinstance(mod, dict) or "questions" not in mod:
                continue
            mod_name = frappe.db.get_value("Duty Training Module", {"title": mod["title"]}, "name")
            if not mod_name:
                missing_mod += 1
                report.append("  module not on this site: %s (%s)" % (mod["title"], fam))
                continue

            live = frappe.get_all(
                "Duty Quiz Question",
                filters={"module": mod_name},
                fields=["name", "question", "opt_a", "opt_b", "opt_c", "opt_d", "correct"],
            )
            index = {}
            for row in live:
                index.setdefault(_norm(row.question), []).append(row)

            hit = miss = fixed = 0
            for q in mod["questions"]:
                rows = index.get(_norm(q["q"]))
                if not rows:
                    miss += 1
                    continue
                row = rows.pop(0)
                hit += 1
                want = {
                    "opt_a": q["opts"][0], "opt_b": q["opts"][1],
                    "opt_c": q["opts"][2], "opt_d": q["opts"][3],
                    "correct": LETTERS[q["ans"]],
                }
                if all((row.get(k) or "") == (v or "") for k, v in want.items()):
                    already += 1
                    continue
                fixed += 1
                if not dry_run:
                    frappe.db.set_value("Duty Quiz Question", row.name, want, update_modified=False)

            matched += hit
            missing_q += miss
            updated += fixed
            report.append("  %-22s %-16s matched %3d, updated %3d%s"
                          % (key, fam, hit, fixed, (", UNMATCHED %d" % miss) if miss else ""))

    if not dry_run:
        frappe.db.commit()

    print("\n".join(report))
    print("\n%s: %d question(s) updated, %d already correct, %d matched in total."
          % ("DRY RUN" if dry_run else "APPLIED", updated, already, matched))
    if missing_q:
        print("%d question(s) in the data files had no match on this site — "
              "they were probably edited in the desk. Fix those by hand." % missing_q)
    if missing_mod:
        print("%d module(s) in the data files are not seeded on this site." % missing_mod)
    return {"updated": updated, "already": already, "matched": matched,
            "unmatched": missing_q, "missing_modules": missing_mod}


def verify_spread(threshold=40):
    """Report every module whose bank can be passed by guessing one option.

    This reads the DATABASE, not the data files — it is the check that answers
    'what can a candidate actually do today', and it is worth running after any
    bulk edit to the banks.
    """
    threshold = int(threshold or 40)
    rows = frappe.get_all(
        "Duty Training Module", filters={"active": 1}, fields=["name", "title", "pass_mark"]
    )
    bad = []
    for m in rows:
        qs = frappe.get_all(
            "Duty Quiz Question", filters={"module": m.name, "active": 1}, fields=["correct"]
        )
        if not qs:
            continue
        spread = collections.Counter(q.correct for q in qs)
        top = max(spread.values())
        guess = round(top * 100.0 / len(qs))
        line = "%-52s %3d questions  %s  guess %d%%" % (
            m.title[:52], len(qs),
            " ".join("%s:%d" % (l, spread.get(l, 0)) for l in LETTERS), guess,
        )
        if guess > threshold:
            bad.append((guess, line, m.pass_mark or 70))
        print(("  " if guess <= threshold else "!!") + line)

    print("\n%d module(s) checked." % len(rows))
    if bad:
        print("\n%d module(s) are guessable above %d%%:" % (len(bad), threshold))
        for guess, line, pm in sorted(bad, reverse=True):
            print("   %s   (pass mark %d%%)" % (line, pm))
    else:
        print("Every bank is within the guessing floor. Nothing to fix.")
    return {"checked": len(rows), "guessable": len(bad)}


def certificates_at_risk():
    """Which certificates were issued against banks that were guessable?

    Run this BEFORE rebalancing, so you know what was already handed out."""
    rows = frappe.db.sql(
        """select track_title, product, count(*) as n, min(issued_on) as first, max(issued_on) as last
           from `tabDuty Certificate` where status = 'Valid'
           group by track_title, product order by n desc""",
        as_dict=True,
    )
    for r in rows:
        print("  %-46s %-14s %4d issued  %s to %s"
              % ((r.track_title or "")[:46], (r.product or "")[:14], r.n, r.first, r.last))
    print("\n%d track(s) with live certificates." % len(rows))
    return rows


def push_topics(dry_run=0):
    """Write derived question topics into the live banks.

    Topics are what the sponsor scorecard reports on, so without them its
    weakest-areas section stays blank however many exams are sat. Matches on
    question text and writes ONLY the topic field, so nothing authored in the
    desk is disturbed. Idempotent.
    """
    dry_run = int(dry_run or 0)
    updated = already = matched = missing_q = missing_mod = 0
    report = []

    for fam, path in _data_files(ALL_FAMILIES):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, mod in data.items():
            if not isinstance(mod, dict) or "questions" not in mod:
                continue
            mod_name = frappe.db.get_value("Duty Training Module", {"title": mod["title"]}, "name")
            if not mod_name:
                missing_mod += 1
                continue
            live = frappe.get_all(
                "Duty Quiz Question", filters={"module": mod_name},
                fields=["name", "question", "topic"],
            )
            index = {}
            for row in live:
                index.setdefault(_norm(row.question), []).append(row)

            hit = fixed = 0
            for q in mod["questions"]:
                topic = (q.get("topic") or "").strip()
                if not topic:
                    continue
                rows = index.get(_norm(q["q"]))
                if not rows:
                    missing_q += 1
                    continue
                row = rows.pop(0)
                hit += 1
                if (row.get("topic") or "") == topic:
                    already += 1
                    continue
                fixed += 1
                if not dry_run:
                    frappe.db.set_value("Duty Quiz Question", row.name,
                                        "topic", topic, update_modified=False)
            matched += hit
            updated += fixed
            report.append("  %-22s %-16s matched %3d, tagged %3d" % (key, fam, hit, fixed))

    if not dry_run:
        frappe.db.commit()
    print("\n".join(report))
    print("\n%s: %d question(s) tagged, %d already correct, %d matched."
          % ("DRY RUN" if dry_run else "APPLIED", updated, already, matched))
    if missing_q:
        print("%d question(s) had no match on this site." % missing_q)
    if missing_mod:
        print("%d module(s) in the data files are not seeded here." % missing_mod)
    return {"tagged": updated, "already": already, "matched": matched}


def topic_coverage():
    """How much of the live estate can the scorecard actually report on?"""
    mods = frappe.get_all("Duty Training Module", filters={"active": 1},
                          fields=["name", "title"])
    bare = []
    tot = tagged = 0
    for m in mods:
        qs = frappe.get_all("Duty Quiz Question", filters={"module": m.name, "active": 1},
                            fields=["topic"])
        if not qs:
            continue
        n = len(qs)
        t = sum(1 for q in qs if (q.topic or "").strip())
        tot += n
        tagged += t
        if t < n:
            bare.append((m.title, n - t, n))
    print("%d of %d live questions carry a topic (%d%%)."
          % (tagged, tot, round(tagged * 100.0 / tot) if tot else 0))
    for title, miss, n in sorted(bare, key=lambda x: -x[1])[:20]:
        print("   %-52s %d of %d untagged" % (title[:52], miss, n))
    return {"tagged": tagged, "total": tot, "modules_incomplete": len(bare)}
