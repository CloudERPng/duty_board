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
from frappe.utils import cint

FAMILIES = ("closer", "bkpr", "consultant", "client_reports")
ALL_FAMILIES = ("accounts_pro", "bkpr", "client_reports", "closer", "consultant",
                "control", "finance", "hr_pro", "inventory_pro", "payroll_pro", "pos_pro",
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


def push_lessons(family=None, reset_progress=0, dry_run=0):
    """Sync lesson CONTENT for one family, or all of them, to the data files.

    push_closer_lessons reads academy_closer_data.json and nothing else — it was
    written for one repair and its name says so. Content edited anywhere else
    therefore had no way to reach an already-seeded site, which is how a set of
    glossary panels was written, packaged, deployed and never appeared.

    Syncs by position within each module: chapter N in the file becomes chapter
    N on the site, updating title, content and estimate in place, and appending
    any extra chapters. Lessons are never deleted, because Duty Lesson Progress
    rows point at them.

    family=None does every family. reset_progress=1 clears completion for the
    modules touched — use it only when the material changed enough that a
    learner's tick would be a false record.
    """
    dry_run = int(dry_run or 0)
    reset_progress = int(reset_progress or 0)
    fams = (family,) if family else ALL_FAMILIES
    here = os.path.dirname(os.path.abspath(__file__))
    changed = inserted = skipped = 0

    for fam in fams:
        path = os.path.join(here, "academy_%s_data.json" % fam)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, mod in data.items():
            if not isinstance(mod, dict) or "lessons" not in mod:
                continue
            mod_name = frappe.db.get_value(
                "Duty Training Module", {"title": mod["title"]}, "name"
            )
            if not mod_name:
                skipped += 1
                continue
            live = frappe.get_all(
                "Duty Lesson", filters={"module": mod_name},
                fields=["name", "title", "content", "est_minutes"],
                order_by="sort_order asc, creation asc",
            )
            for i, l in enumerate(mod["lessons"]):
                payload = {
                    "title": l["title"], "content": l["html"],
                    "est_minutes": cint(l.get("est")), "sort_order": i,
                }
                if i < len(live):
                    cur = live[i]
                    if (cur.title == l["title"] and cur.content == l["html"]
                            and cint(cur.est_minutes) == cint(l.get("est"))):
                        continue
                    changed += 1
                    if not dry_run:
                        frappe.db.set_value("Duty Lesson", cur.name, payload,
                                            update_modified=False)
                else:
                    inserted += 1
                    if not dry_run:
                        doc = {"doctype": "Duty Lesson", "module": mod_name}
                        doc.update(payload)
                        frappe.get_doc(doc).insert(ignore_permissions=True)
            if reset_progress and not dry_run:
                frappe.db.delete("Duty Lesson Progress", {"module": mod_name})
            print("  %-14s %-44s %d chapter(s)" % (fam, mod["title"][:44], len(mod["lessons"])))

    if not dry_run:
        frappe.db.commit()
    print("\n%s: %d chapter(s) updated, %d inserted, %d module(s) not on this site."
          % ("DRY RUN" if dry_run else "APPLIED", changed, inserted, skipped))
    return {"changed": changed, "inserted": inserted, "skipped": skipped}


def push_closer_lessons(reset_progress=0, dry_run=0):
    """Sync the Closer lesson set to the corrected data file.

    Chapters were REPLACED here, not merely edited — two wrong lifecycle
    chapters became four correct ones — so a title match is not enough. This
    syncs by position: chapter N in the file becomes chapter N on the site,
    updating title, content and estimate in place, and inserting any extra
    chapters at the end of the order.

    Lessons are never deleted, because Duty Lesson Progress rows point at them
    and deleting would orphan a learner's history. A chapter that moved
    position is rewritten in place instead.

    reset_progress=1 clears completion for the module, so anyone who read the
    old, wrong lifecycle has to read the corrected one. Use it: the material
    changed materially, and a learner carrying a tick for a chapter that no
    longer exists is exactly the false record this whole exercise is about.
    """
    dry_run = int(dry_run or 0)
    reset_progress = int(reset_progress or 0)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "academy_closer_data.json"), encoding="utf-8") as f:
        data = json.load(f)

    changed = inserted = 0
    for key, mod in data.items():
        mod_name = frappe.db.get_value("Duty Training Module", {"title": mod["title"]}, "name")
        if not mod_name:
            print("  module not on this site: %s" % mod["title"])
            continue
        live = frappe.get_all(
            "Duty Lesson", filters={"module": mod_name},
            fields=["name", "title", "sort_order", "content", "est_minutes"],
            order_by="sort_order asc, creation asc",
        )
        for i, want in enumerate(mod["lessons"]):
            payload = {"title": want["title"], "content": want["html"],
                       "est_minutes": want.get("est") or 5, "sort_order": i}
            if i < len(live):
                row = live[i]
                same = (row.title == payload["title"]
                        and (row.content or "") == payload["content"]
                        and int(row.est_minutes or 0) == int(payload["est_minutes"]))
                if same:
                    continue
                changed += 1
                if not dry_run:
                    frappe.db.set_value("Duty Lesson", row.name, payload, update_modified=False)
            else:
                inserted += 1
                if not dry_run:
                    doc = {"doctype": "Duty Lesson", "module": mod_name}
                    doc.update(payload)
                    frappe.get_doc(doc).insert(ignore_permissions=True)

        if reset_progress and not dry_run:
            for p in frappe.get_all("Duty Lesson Progress",
                                    filters={"module": mod_name}, pluck="name"):
                frappe.db.set_value("Duty Lesson Progress", p,
                                    {"completed_at": None, "checks_passed": 0},
                                    update_modified=False)

    if not dry_run:
        frappe.db.commit()
    print("%s: %d chapter(s) rewritten, %d inserted.%s"
          % ("DRY RUN" if dry_run else "APPLIED", changed, inserted,
             " Lesson progress reset." if (reset_progress and not dry_run) else ""))
    print("Now re-run the bank sync so the corrected questions land:")
    print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.rebalance_banks")
    return {"changed": changed, "inserted": inserted}


def push_lesson_checks(dry_run=0):
    """Create or update the end-of-lesson check questions from the data files.

    Checks are formative — never scored, never on a transcript — so they are
    matched and rewritten by position within their lesson rather than by text.
    A check whose wording is improved should update, not duplicate.

    Removing a check from the data file deactivates the surplus record rather
    than deleting it, because Duty Lesson Progress carries a checks_passed flag
    that was earned against the set as it stood.
    """
    dry_run = int(dry_run or 0)
    here = os.path.dirname(os.path.abspath(__file__))
    created = updated = retired = 0
    report = []

    for fam in ALL_FAMILIES:
        path = os.path.join(here, "academy_%s_data.json" % fam)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key, mod in data.items():
            if not isinstance(mod, dict) or "lessons" not in mod:
                continue
            mod_name = frappe.db.get_value("Duty Training Module", {"title": mod["title"]}, "name")
            if not mod_name:
                continue
            n_mod = 0
            for lesson in mod["lessons"]:
                checks = lesson.get("checks") or []
                les_name = frappe.db.get_value(
                    "Duty Lesson", {"module": mod_name, "title": lesson["title"]}, "name"
                )
                if not les_name:
                    if checks:
                        report.append("  lesson not found: %s / %s" % (key, lesson["title"]))
                    continue
                live = frappe.get_all(
                    "Duty Lesson Check", filters={"lesson": les_name},
                    fields=["name", "sort_order"], order_by="sort_order asc, creation asc",
                )
                for i, ch in enumerate(checks):
                    opts = list(ch["opts"]) + [None, None, None, None]
                    payload = {
                        "question": ch["q"], "opt_a": opts[0], "opt_b": opts[1],
                        "opt_c": opts[2], "opt_d": opts[3],
                        "correct": "ABCD"[ch["ans"]], "rationale": ch.get("why"),
                        "sort_order": i, "active": 1,
                    }
                    if i < len(live):
                        updated += 1
                        if not dry_run:
                            frappe.db.set_value("Duty Lesson Check", live[i].name,
                                                payload, update_modified=False)
                    else:
                        created += 1
                        if not dry_run:
                            doc = {"doctype": "Duty Lesson Check", "lesson": les_name}
                            doc.update(payload)
                            frappe.get_doc(doc).insert(ignore_permissions=True)
                    n_mod += 1
                for extra in live[len(checks):]:
                    retired += 1
                    if not dry_run:
                        frappe.db.set_value("Duty Lesson Check", extra.name,
                                            "active", 0, update_modified=False)
            if n_mod:
                report.append("  %-22s %-16s %d check(s)" % (key, fam, n_mod))

    if not dry_run:
        frappe.db.commit()
    print("\n".join(report))
    print("\n%s: %d created, %d updated, %d deactivated."
          % ("DRY RUN" if dry_run else "APPLIED", created, updated, retired))
    print("A lesson with checks now requires them to be answered before it can be marked read.")
    return {"created": created, "updated": updated, "retired": retired}


# Matched on PRODUCT rather than on exact title. The first version of this
# matched titles and missed five tracks, because the real titles carry
# qualifiers the map did not — "System-Based Internal Control in a Retail
# Environment" against "System-Based Internal Control". Product is the stable
# key: every ZhiftCRM track is CRM whatever it is called.
CATEGORY_BY_PRODUCT = {
	"ZhiftPOS": "Retail & Point of Sale",
	"Retail Foundations": "Retail & Point of Sale",
	"ZhiftCRM": "CRM & Ecommerce",
	"Retail Leadership": "Leadership & Management",
	"Accounting Services": "Finance, Control & Compliance",
	"Xlevel Academy": "Finance, Control & Compliance",
}

# Product prefixes, checked after the exact map. Catches ZhiftERP Accounts,
# ZhiftERP Payroll and every other role product without listing them.
CATEGORY_BY_PRODUCT_PREFIX = [
	("ZhiftERP", "ERP by Role"),
	("ZhiftPOS", "Retail & Point of Sale"),
	("ZhiftCRM", "CRM & Ecommerce"),
	("CloudERP", "Finance, Control & Compliance"),
]

# Last resort, for tracks whose product does not resolve.
CATEGORY_BY_TITLE_PREFIX = [
	("ZhiftERP ", "ERP by Role"),
	("ZhiftPOS ", "Retail & Point of Sale"),
	("Certified ZhiftPOS ", "Retail & Point of Sale"),
	("ZhiftCRM ", "CRM & Ecommerce"),
	("Retail Foundations", "Retail & Point of Sale"),
	("Retail Leadership", "Leadership & Management"),
]


def _category_for(title, product):
	p = (product or "").strip()
	if p in CATEGORY_BY_PRODUCT:
		return CATEGORY_BY_PRODUCT[p]
	for pref, cat in CATEGORY_BY_PRODUCT_PREFIX:
		if p.startswith(pref):
			return cat
	t = (title or "").strip()
	for pref, cat in CATEGORY_BY_TITLE_PREFIX:
		if t.startswith(pref):
			return cat
	return None


@frappe.whitelist()
def backfill_track_categories(dry_run=1, overwrite=0):
	"""Set category on tracks already seeded, so the academy page can group them.

	Matches on product first, then product prefix, then title prefix. Anything
	unresolved is left blank rather than guessed — it shows under Other on the
	page, which is visible and fixable rather than silently wrong.

	Pass overwrite=1 to recategorise tracks that already have one, which is what
	you want after changing the maps above.

	bench --site <site> execute duty_board.academy_repair.backfill_track_categories
	bench --site <site> execute duty_board.academy_repair.backfill_track_categories --kwargs "{'dry_run': 0}"
	"""
	dry = int(dry_run or 0)
	over = int(overwrite or 0)
	rows = frappe.get_all(
		"Duty Certification Track", fields=["name", "title", "product", "category"]
	)
	plan, kept, skipped = [], [], []
	for r in rows:
		if r.category and not over:
			kept.append(r.title)
			continue
		cat = _category_for(r.title, r.product)
		if not cat:
			skipped.append("%s  (product: %s)" % (r.title, r.product or "none"))
			continue
		if cat == r.category:
			kept.append(r.title)
			continue
		plan.append((r.name, r.title, r.category, cat))
		if not dry:
			frappe.db.set_value(
				"Duty Certification Track", r.name, "category", cat, update_modified=False
			)
	if not dry and plan:
		frappe.db.commit()
	print("%s: %d track(s) to set, %d already correct" % (
		"DRY RUN" if dry else "SET", len(plan), len(kept)))
	for _n, title, old, cat in plan:
		print("   %-48s %s-> %s" % (title[:48], ("[%s] " % old) if old else "", cat))
	if skipped:
		print("\nNOT categorised — these will show under Other:")
		for t in skipped:
			print("   %s" % t)
	if dry and plan:
		print("\nRe-run with --kwargs \"{'dry_run': 0}\" to apply.")
	return {"set": len(plan), "kept": len(kept), "skipped": skipped}


@frappe.whitelist()
def academy_visibility():
	"""Report, per track, whether it appears on the public academy page and why not.

	The page applies four gates and a track failing any one of them simply is not
	there — with nothing to say so. This prints the gates rather than making
	anybody reason about them from the seeders, which is unreliable because site
	data drifts from the seeders over time.

	bench --site <site> execute duty_board.academy_repair.academy_visibility
	"""
	rows = frappe.get_all(
		"Duty Certification Track",
		fields=["name", "title", "product", "category", "audience", "active",
				"private_to_room", "access", "seat_price"],
		order_by="title asc",
	)
	shown, hidden = [], []
	for r in rows:
		mods = frappe.db.count("Duty Certification Track Module", {"parent": r.name})
		why = []
		if not frappe.utils.cint(r.active):
			why.append("inactive")
		if r.audience not in ("Client", "Both"):
			why.append("audience=%s" % (r.audience or "none"))
		if r.private_to_room:
			why.append("private to %s" % r.private_to_room)
		if not mods:
			why.append("no modules attached")
		row = (r.title, r.product, r.category or "-", mods, why)
		(hidden if why else shown).append(row)

	print("ON THE PUBLIC ACADEMY PAGE (%d)" % len(shown))
	for t, p_, c, m, _ in shown:
		print("   %-46s %-22s %-30s %d mod" % (t[:46], (p_ or "")[:22], c[:30], m))
	print()
	print("NOT ON THE PAGE (%d)" % len(hidden))
	for t, p_, c, m, why in hidden:
		print("   %-46s %-22s %s" % (t[:46], (p_ or "")[:22], "; ".join(why)))
	return {"shown": len(shown), "hidden": len(hidden)}


ERP_ROLE_TRACK_PREFIX = "ZhiftERP "


@frappe.whitelist()
def open_tracks_to_clients(titles=None, dry_run=1):
	"""Move consultant-only tracks to audience Both so clients can see and buy them.

	The ZhiftERP role tracks were built as consultant enablement and seeded
	audience=Consultant, which keeps them off the client catalogue and off the
	public page entirely. They have since been priced for client staff, so they
	need to be visible to both — Both rather than Client, so consultants do not
	lose them from their own catalogue.

	Pass titles as a comma-separated list to be selective; default is every
	ZhiftERP role track plus ZhiftPOS Professional.

	bench --site <site> execute duty_board.academy_repair.open_tracks_to_clients
	bench --site <site> execute duty_board.academy_repair.open_tracks_to_clients --kwargs "{'dry_run': 0}"
	"""
	dry = int(dry_run or 0)
	if titles:
		wanted = [t.strip() for t in str(titles).split(",") if t.strip()]
		rows = frappe.get_all(
			"Duty Certification Track", filters={"title": ["in", wanted]},
			fields=["name", "title", "audience"],
		)
	else:
		rows = [
			r for r in frappe.get_all(
				"Duty Certification Track", fields=["name", "title", "audience"])
			if r.title.startswith(ERP_ROLE_TRACK_PREFIX)
			or r.title == "ZhiftPOS Professional"
		]
	plan = [r for r in rows if r.audience != "Both"]
	print("%s: %d track(s) to open to clients" % ("DRY RUN" if dry else "SET", len(plan)))
	for r in plan:
		print("   %-50s %s -> Both" % (r.title[:50], r.audience or "none"))
		if not dry:
			frappe.db.set_value("Duty Certification Track", r.name, "audience", "Both",
								update_modified=False)
	if not dry and plan:
		frappe.db.commit()
	if dry and plan:
		print("\nRe-run with --kwargs \"{'dry_run': 0}\" to apply.")
	return {"changed": len(plan)}
