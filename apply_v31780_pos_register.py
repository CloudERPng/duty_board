#!/usr/bin/env python3
"""Duty Board v3.178.0 — POS TRACK REGISTER FLATTENING (strict manual
register, style v3).

The POS track's body content is manual-anchored and preserved verbatim.
This patch flattens the register elements only, via anchored replaces:
- 4 module titles and 18 chapter titles flattened
- every "law" framing converted to "module rule N" (lessons + banks)
- "Case study" chapters renamed "Worked example"
- editorial phrases removed (the one idea / which is the point /
  Here is the trap / keeps it honest)
- the seeder gains rename_pos_modules() to rename the DB module titles
  and track description BEFORE refresh (refresh matches by title)

Deploy: apply -> commit -> then on the server, IN THIS ORDER:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_pos_pro.rename_pos_modules
  # then refresh lessons+questions for ALL EIGHT module keys (block in the notes)

Anchored, idempotent. Requires v3.177.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_pos_pro_data.json"
SEEDER = "duty_board/academy_seed_pos_pro.py"
CHECK_ONLY = "--check" in sys.argv

MODULE_TITLE_RENAMES = {
    "POS 1 — The Counter & the System": "POS 1 — The Counter System: Concepts & Architecture",
    "POS 4 — The Shift & the Sale": "POS 4 — Shift Operations & Sales Processing",
    "POS 6 — The Extended Counters": "POS 6 — Extended Counter Operations",
    "POS 8 — The Honest Counter": "POS 8 — Daily Verification & Offline Operations",
}

LESSON_TITLE_RENAMES = [
    ("counter_system", "Chapter 8 — Case study: Okelewo Stores before ZhiftPOS",
     "Chapter 8 — Worked example: Okelewo Stores before ZhiftPOS"),
    ("counter_system", "Chapter 9 — Review & the first law",
     "Chapter 9 — Review & module rule 1"),
    ("pos_profile", "Chapter 9 — Case study: building Okelewo's profiles",
     "Chapter 9 — Worked example: building Okelewo's profiles"),
    ("pos_profile", "Chapter 10 — Review & the second law",
     "Chapter 10 — Review & module rule 2"),
    ("terminal_estate", "Chapter 8 — Case study: Okelewo commissions five terminals",
     "Chapter 8 — Worked example: Okelewo commissions five terminals"),
    ("terminal_estate", "Chapter 9 — Review & the third law",
     "Chapter 9 — Review & module rule 3"),
    ("shift_sale", "Chapter 8 — Closing the shift, and Okelewo's first month",
     "Chapter 8 — Closing the shift; worked example: Okelewo's first month"),
    ("shift_sale", "Chapter 9 — Review & the fourth law",
     "Chapter 9 — Review & module rule 4"),
    ("concessions_returns", "Chapter 8 — Case study: Okelewo's first quarter of exceptions",
     "Chapter 8 — Worked example: Okelewo's first quarter of exceptions"),
    ("concessions_returns", "Chapter 9 — Review & the fifth law",
     "Chapter 9 — Review & module rule 5"),
    ("extended_counters", "Chapter 8 — Case study: Okelewo's extended counters",
     "Chapter 8 — Worked example: Okelewo's extended counters"),
    ("extended_counters", "Chapter 9 — Review & the sixth law",
     "Chapter 9 — Review & module rule 6"),
    ("voucher_programme", "Chapter 2 — Two kinds of card, six states, one gate",
     "Chapter 2 — Card types, card states, and the activation gate"),
    ("voucher_programme", "Chapter 8 — What to watch, and Okelewo's December",
     "Chapter 8 — The monitoring reads; worked example: Okelewo's December"),
    ("voucher_programme", "Chapter 9 — Review & the seventh law",
     "Chapter 9 — Review & module rule 7"),
    ("honest_counter", "Chapter 1 — Proving the counter daily",
     "Chapter 1 — The daily verification routine"),
    ("honest_counter", "Chapter 9 — The handover test, the owner's page, and Okelewo's finish",
     "Chapter 9 — The handover test and the owner's page; worked example: Okelewo"),
    ("honest_counter", "Chapter 10 — Review & the eighth law",
     "Chapter 10 — Review & module rule 8"),
]

# (module, old, new, expected_count) applied across the module's lesson html
HTML_REPLACES = [
    ("counter_system",
     "The one idea behind ZhiftPOS.</b> ZhiftPOS is built on a single design idea, and understanding it early makes everything else in this track easier:",
     "The design principle.</b> ZhiftPOS is built on one design principle:", 1),
    ("counter_system",
     "ends with a law.</b> A law is a one-sentence rule that sums the module up. Module 1's law:",
     "ends with a module rule.</b> A module rule is a one-sentence statement that sums the module up. Module rule 1:", 1),
    ("counter_system", "The first law:", "Module rule 1:", 1),
    ("pos_profile", "closes with the module's law:", "closes with the module rule:", 1),
    ("pos_profile", "The second law:", "Module rule 2:", 1),
    ("pos_profile", "Here is the trap: switching", "Note the behaviour: switching", 1),
    ("terminal_estate", "The module's law:", "The module rule:", 1),
    ("terminal_estate", "The third law:", "Module rule 3:", 1),
    ("shift_sale", "The module's law:", "The module rule:", 1),
    ("shift_sale", "The fourth law:", "Module rule 4:", 1),
    ("concessions_returns", "The module's law:", "The module rule:", 1),
    ("concessions_returns", "The fifth law:", "Module rule 5:", 1),
    ("extended_counters", "The module's law:", "The module rule:", 1),
    ("extended_counters", "The sixth law:", "Module rule 6:", 1),
    ("extended_counters",
     "There are no side books — which is the point.",
     "There are no side books; every arrangement lives in the standard records.", 1),
    ("extended_counters",
     "The quarter stays uneventful, which is the point: limits",
     "The quarter stays uneventful: limits", 1),
    ("voucher_programme", "The module's law:", "The module rule:", 1),
    ("voucher_programme", "The seventh law:", "Module rule 7:", 1),
    ("honest_counter",
     "Seven modules set the counter up; this one keeps it honest.",
     "Seven modules configured the counter; this module covers its ongoing verification.", 1),
    ("honest_counter",
     "It is the track's second ten-chapter module, and its law:",
     "It is the track's second ten-chapter module, and its module rule:", 1),
    ("honest_counter", "The eighth law:", "Module rule 8:", 1),
    ("honest_counter", "And the track's eight laws together:",
     "The track's eight module rules together:", 1),
]

# (module, old, new, expected_count) applied across the module's questions JSON
QUESTION_REPLACES = [
    ("counter_system", "Module 1's law is:", "Module rule 1 is:", 1),
    ("counter_system", "The one idea behind the whole system.", "The design principle behind the whole system.", 1),
    ("pos_profile", "Module 2's law is:", "Module rule 2 is:", 1),
    ("pos_profile", "The law requires it", "Regulations require it", 1),
    ("pos_profile", "Tax law forbids it", "Tax rules forbid it", 1),
    ("terminal_estate", "Module 3's law is:", "Module rule 3 is:", 1),
    ("shift_sale", "Module 4's law is:", "Module rule 4 is:", 1),
    ("concessions_returns", "Module 5's law is:", "Module rule 5 is:", 1),
    ("extended_counters", "Module 6's law is:", "Module rule 6 is:", 1),
    ("voucher_programme", "Module 7's law is:", "Module rule 7 is:", 1),
    ("honest_counter", "Module 8's law is:", "Module rule 8 is:", 1),
    ("honest_counter", "The eight laws together certify:", "The eight module rules together certify:", 1),
]

DESC_REPLACES = [
    ("honest_counter", "Keeping the counter honest:", "Daily verification and offline operation:"),
]

OLD_TRACK_DESC = "The complete counter certification: the system and its roles, the Point of Sale Profile at full depth, commissioning and the terminal estate, the shift and the sale, concessions, returns and overrides, the extended counters, the voucher programme from mint to breakage, and the honest counter \\u2014 offline, the queue, reconciliation and supervision \\u2014 proctored examinations from the first scan to the counter that proves itself daily."
NEW_TRACK_DESC = "The complete counter certification: the system and its roles, the Point of Sale Profile at full depth, commissioning and the terminal estate, shift operations and sales processing, concessions, returns and overrides, the extended counters, the voucher programme, and daily verification \\u2014 offline operation, the queue, reconciliation and supervision \\u2014 with proctored examinations per module."

RENAME_FN = '''

def rename_pos_modules():
	"""One-off (v3.178.0): flatten POS module titles to the strict manual
	register and update the track description. MUST run BEFORE
	refresh_lessons/refresh_questions after v3.178.0, because refresh
	matches modules by title."""
	renames = {
		"POS 1 \\u2014 The Counter & the System": "POS 1 \\u2014 The Counter System: Concepts & Architecture",
		"POS 4 \\u2014 The Shift & the Sale": "POS 4 \\u2014 Shift Operations & Sales Processing",
		"POS 6 \\u2014 The Extended Counters": "POS 6 \\u2014 Extended Counter Operations",
		"POS 8 \\u2014 The Honest Counter": "POS 8 \\u2014 Daily Verification & Offline Operations",
	}
	for old, new in renames.items():
		name = frappe.db.get_value("Duty Training Module", {"title": old}, "name")
		if name:
			frappe.db.set_value("Duty Training Module", name, "title", new)
			print(f"renamed: {old} -> {new}")
		else:
			already = frappe.db.get_value("Duty Training Module", {"title": new}, "name")
			print(f"skipped: {old} ({'already renamed' if already else 'NOT FOUND'})")
	tr = frappe.db.get_value("Duty Certification Track", {"title": TRACK["title"]}, "name")
	if tr:
		frappe.db.set_value("Duty Certification Track", tr, "description", TRACK["description"])
		print("track description updated")
	frappe.db.commit()
'''


def _replace_counted(s, old, new, expected, where):
    n = s.count(old)
    if n != expected:
        sys.exit(f"ABORT: anchor '{old[:60]}' found {n}x (expected {expected}) in {where}")
    return s.replace(old, new)


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    if '"3.178.0"' in init:
        print("Already applied. Nothing to do.")
        return
    if '"3.177.0"' not in init:
        sys.exit("ABORT: not at v3.177.0.")

    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)
    with io.open(os.path.join(root, SEEDER), encoding="utf-8") as f:
        seeder = f.read()

    # --- module titles ---
    applied = 0
    for key, mod in data.items():
        if mod["title"] in MODULE_TITLE_RENAMES:
            mod["title"] = MODULE_TITLE_RENAMES[mod["title"]]
            applied += 1
    if applied != 4:
        sys.exit(f"ABORT: module title renames applied {applied}x (expected 4)")
    print(f"module titles: 4 renamed")

    # --- lesson titles ---
    for key, old, new in LESSON_TITLE_RENAMES:
        hits = [l for l in data[key]["lessons"] if l["title"] == old]
        if len(hits) != 1:
            sys.exit(f"ABORT: lesson title '{old[:60]}' found {len(hits)}x in {key}")
        hits[0]["title"] = new
    print(f"lesson titles: {len(LESSON_TITLE_RENAMES)} renamed")

    # --- lesson html ---
    for key, old, new, exp in HTML_REPLACES:
        found = 0
        for l in data[key]["lessons"]:
            found += l["html"].count(old)
        if found != exp:
            sys.exit(f"ABORT: html anchor '{old[:60]}' found {found}x in {key} (expected {exp})")
        for l in data[key]["lessons"]:
            l["html"] = l["html"].replace(old, new)
    print(f"html replaces: {len(HTML_REPLACES)} applied")

    # --- questions ---
    for key, old, new, exp in QUESTION_REPLACES:
        blob = json.dumps(data[key]["questions"], ensure_ascii=False)
        n = blob.count(old)
        if n != exp:
            sys.exit(f"ABORT: question anchor '{old[:60]}' found {n}x in {key} (expected {exp})")
        data[key]["questions"] = json.loads(blob.replace(old, new))
    print(f"question replaces: {len(QUESTION_REPLACES)} applied")

    # --- module descs ---
    for key, old, new in DESC_REPLACES:
        if old not in data[key].get("desc", ""):
            sys.exit(f"ABORT: desc anchor '{old}' not found in {key}")
        data[key]["desc"] = data[key]["desc"].replace(old, new)
    print("module descs: updated")

    # --- seeder: track description + rename function ---
    old_desc_literal = OLD_TRACK_DESC.replace("\\u2014", "\u2014")
    new_desc_literal = NEW_TRACK_DESC.replace("\\u2014", "\u2014")
    seeder = _replace_counted(seeder, old_desc_literal, new_desc_literal, 1, "seeder TRACK description")
    if "def rename_pos_modules" not in seeder:
        seeder = seeder.rstrip("\n") + "\n" + RENAME_FN.replace("\\u2014", "\u2014")
    print("seeder: track description flattened, rename_pos_modules() appended")

    # --- validation: register scan + structure ---
    import re
    blob = json.dumps(data, ensure_ascii=False)
    problems = []
    for phrase in ["Case study", "the one idea", "The one idea", "which is the point",
                   "keeps it honest", "Here is the trap", "The Honest Counter",
                   "The Shift & the Sale", "The Counter & the System", "The Extended Counters"]:
        if phrase in blob:
            problems.append(f"  residual phrase: '{phrase}'")
    law_hits = re.findall(r"\b[Ll]aws?\b", blob)
    if law_hits:
        problems.append(f"  residual 'law' occurrences: {len(law_hits)}")
    want = {"counter_system": 9, "pos_profile": 10, "terminal_estate": 9, "shift_sale": 9,
            "concessions_returns": 9, "extended_counters": 9, "voucher_programme": 9, "honest_counter": 10}
    for key, ch in want.items():
        c = data[key]
        if len(c["lessons"]) != ch:
            problems.append(f"  {key}: {len(c['lessons'])} lessons (want {ch})")
        if len(c["questions"]) != 35:
            problems.append(f"  {key}: {len(c['questions'])} questions (want 35)")
        short = [l["title"][:40] for l in c["lessons"] if len(l["html"]) < 2500]
        if short:
            problems.append(f"  {key} below depth: {short}")
        txt = json.dumps(c, ensure_ascii=False)
        if "ERPNext" in txt:
            problems.append(f"  {key}: ERPNext leakage")
        for marker in ["certified professional", "the consultant", "consultants", "the academy",
                       "this academy", "engagement", "constitution", "costume", "scar tissue",
                       "witness", "testimony"]:
            if marker in txt.lower():
                problems.append(f"  {key}: banned marker '{marker}'")
    if problems:
        print("ABORT — validation failed:")
        print("\n".join(problems))
        sys.exit(1)
    print("validation: register scan CLEAN, structure preserved (9/10/9/9/9/9/9/10 ch, 35q each)")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, SEEDER), "w", encoding="utf-8") as f:
        f.write(seeder)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.177.0"', '"3.178.0"'))
    print("  data + seeder: POS TRACK REGISTER FLATTENED (strict manual register)")
    print("wrote __version__ -> 3.178.0")


if __name__ == "__main__":
    main()
