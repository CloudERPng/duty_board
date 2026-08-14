#!/usr/bin/env python3
"""Derive a topic for every question in the academy estate.

Nothing in the estate carries a topic, so the sponsor scorecard's
weakest-areas section — the part that tells a client where their people are
actually weak, and the reason they buy the next engagement — renders an
apology instead of an analysis.

Every question already records where it came from. Three conventions are in
use, and all three resolve to a chapter:

    Ch4                 the eight professional tracks (2,240 questions)
    L3  /  L1, L5       bookkeeper, consultant, client reports (343)
    Creating §2         closer, where the section name is already a topic (49)

So this derives rather than invents. The chapter title becomes the topic, with
its "Chapter N — " prefix stripped and its length capped so it reads as a bar
label on the scorecard.

A NOTE ON GRANULARITY, because it is a real trade-off and worth disagreeing
with if you see it differently. Chapter-level topics give roughly nine areas
per module. For one learner sitting a ten-question exam that is thin, but the
scorecard aggregates first attempts across a whole cohort, so a group of ten
produces a comfortable sample per area. The gain is that a weak area names
something a learner can go and re-read tonight.

The loss is that these are chapters, not competencies, so they will not
aggregate across tracks into a single "where is my workforce weak" view. For
NEW tracks, write a curated cross-module taxonomy at authoring time — it costs
nothing then. Retrofitting one onto 79 legacy modules would be weeks of
judgement for a marginal gain, which is why this does not attempt it.

Usage
  python3 tag_topics.py --check     # report coverage, write nothing
  python3 tag_topics.py             # write topics into the data files

Run from the app package directory.
"""

import collections
import glob
import json
import os
import re
import sys

CHECK_ONLY = "--check" in sys.argv
MAX_LEN = 58


# --- Closer overrides -------------------------------------------------------
# The Closer banks cite sections by name, and many of those names are order
# STATUSES ("Qualified", "Not Reachable") rather than subjects. Deriving from
# them gave fourteen topics for twenty-seven questions, most holding one — noise
# on a scorecard. These map each section onto the competency it belongs to.
CLOSER_TOPICS = {
    "orders_pipeline": {
        "Orders list": "The orders workspace",
        "Creating": "Creating an order",
        "Lifecycle": "The order lifecycle",
        "Transitions": "The order lifecycle",
        "Qualified": "The order lifecycle",
        "Confirmed": "The order lifecycle",
        "Delivered": "The order lifecycle",
        "Failed": "Holds, breaks and recoveries",
        "Returned": "Holds, breaks and recoveries",
        "Not Reachable": "Holds, breaks and recoveries",
        "Cancelled / Closer Summary": "Holds, breaks and recoveries",
        "Drawer": "Inside an order",
        "Quick actions": "Customers and quick actions",
        "Abandoned": "Abandoned carts",
    },
    "closer_workflow": {
        "Shifts": "Shifts and assignment",
        "Shifts note": "Shifts and assignment",
        "Follow-up": "The follow-up pool",
        "Follow-up FAQ": "The follow-up pool",
        "Closer Summary": "Attribution and your numbers",
        "Dashboard": "Attribution and your numbers",
    },
    "reports_analytics": {
        "Directory": "Reports, roles and dates",
        "Role visibility": "Reports, roles and dates",
        "Date filter": "Reports, roles and dates",
        "Closer Summary": "Individual performance",
        "Team Performance": "Comparing teams fairly",
        "Product Sales": "Product sales analysis",
        "ROAS": "Marketing ROAS",
        "Cohorts": "Cohorts and reading together",
        "Reading together": "Cohorts and reading together",
    },
    "team_workflow": {
        "Lifecycle / distribution": "Distributing the work",
        "New Lead": "Distributing the work",
        "Orders list": "Distributing the work",
        "Shifts": "Running closer shifts",
        "Follow-up": "Governing the recovery team",
        "Follow-up FAQ": "Governing the recovery team",
        "Abandoned / recovery": "Managing cart recovery",
        "Abandoned": "Managing cart recovery",
        "Guardrails": "The manager's guardrails",
        "Roles matrix": "The manager's guardrails",
    },
}


def clean_title(t):
    """'Chapter 4 — Warehouse types and the transit warehouse' -> the part
    that means something."""
    t = (t or "").strip()
    t = re.sub(r"^chapter\s*\d+\s*[—–\-:]\s*", "", t, flags=re.I)
    t = re.sub(r"^\d+[\.\)]\s*", "", t)
    t = " ".join(t.split())
    if len(t) > MAX_LEN:
        cut = t[:MAX_LEN].rsplit(" ", 1)[0]
        t = cut + "…"
    return t


def topic_for(src, lessons, module_title, key=None):
    s = (src or "").strip()
    if not s:
        return None

    over = CLOSER_TOPICS.get(key or "")
    if over:
        return over.get(s.split("\u00a7")[0].strip(), clean_title(module_title))

    m = re.match(r"^ch\s*(\d+)", s, re.I)
    if m:
        i = int(m.group(1)) - 1
        if 0 <= i < len(lessons):
            return clean_title(lessons[i].get("title"))
        return clean_title(module_title)

    m = re.match(r"^l\s*(\d+)", s, re.I)          # 'L3' or 'L1, L5' — take the first
    if m:
        i = int(m.group(1)) - 1
        if 0 <= i < len(lessons):
            return clean_title(lessons[i].get("title"))
        return clean_title(module_title)

    if "§" in s:                                   # 'Creating §2' — the name is the topic
        return clean_title(s.split("§")[0])

    return clean_title(s)


def main():
    tagged = total = 0
    per_module = []
    topics_seen = collections.Counter()

    for path in sorted(glob.glob("academy_*_data.json")):
        data = json.load(open(path, encoding="utf-8"))
        touched = False
        for key, mod in data.items():
            if not isinstance(mod, dict) or "questions" not in mod:
                continue
            lessons = mod.get("lessons") or []
            qs = mod.get("questions") or []
            got = collections.Counter()
            for q in qs:
                t = topic_for(q.get("src"), lessons, mod.get("title", key), key)
                total += 1
                if not t:
                    continue
                if q.get("topic") != t:
                    q["topic"] = t
                    touched = True
                tagged += 1
                got[t] += 1
                topics_seen[t] += 1
            per_module.append((key, os.path.basename(path), len(qs), len(got),
                               sum(got.values())))
        if touched and not CHECK_ONLY:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
                f.write("\n")

    print("%-22s %-26s %5s %8s %8s" % ("MODULE", "FILE", "QS", "TOPICS", "TAGGED"))
    print("-" * 76)
    for key, fam, n, ntopics, ntagged in per_module:
        flag = "" if ntagged == n else "   <-- %d untagged" % (n - ntagged)
        print("%-22s %-26s %5d %8d %8d%s" % (
            key[:22], fam.replace("academy_", "").replace("_data.json", "")[:26],
            n, ntopics, ntagged, flag))

    print("\n%d of %d questions tagged across %d distinct topics."
          % (tagged, total, len(topics_seen)))
    thin = [t for t, n in topics_seen.items() if n < 3]
    if thin:
        print("%d topic(s) carry fewer than 3 questions estate-wide — they will "
              "read as noise on a scorecard until the banks grow." % len(thin))
    if CHECK_ONLY:
        print("--check given; no files written.")
    else:
        print("\nData files written. Push to the live database with:")
        print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_topics")


if __name__ == "__main__":
    main()
