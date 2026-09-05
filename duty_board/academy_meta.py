#!/usr/bin/env python3
"""Fill the catalogue metadata that the shop window and portal now display.

The writing has been done — a thousand chapters of it — and a buyer arriving at
a track's page saw sections missing and no sample to judge it by. This fills
who_for and outcomes on the twelve tracks lacking them, and marks one chapter
per track as the sample.

WHO_FOR AND OUTCOMES ARE DIFFERENT PROMISES and are written as such. who_for
names the reader and, where it matters, says plainly who it is NOT for — a
sentence that saves a client buying the wrong seat. outcomes states what the
person will be able to DO, in the verbs of the job rather than of the syllabus:
"reconcile a bank account nobody has touched for three months", not "understand
bank reconciliation".

THE SAMPLE IS CHOSEN, NOT TAKEN AT RANDOM. It is the chapter that best shows the
writing carries judgement rather than instructions — usually one with a DRILL and
a real decision in it. A sample that reads like a manual sells a manual.

Run:  bench --site <site> execute duty_board.academy_meta.fill --kwargs "{'dry_run': 0}"
"""

import frappe
from frappe.utils import cint

# ─────────────────────────────────────────────────────── who_for / outcomes
META = {
	"ZhiftCRM Certified Closer": {
		"who_for": (
			"Closers working leads and orders in ZhiftCRM — the people who ring the "
			"customer, confirm the sale and own it until it is delivered. No prior "
			"system knowledge is assumed. It does not cover configuring the CRM or "
			"managing a team; those are the Consultant and Closer Manager tracks."
		),
		"outcomes": (
			"Work a day's orders without losing one. Read the status wall and know which "
			"bucket is theirs and which belongs to dispatch. Create an order cleanly, "
			"handle a duplicate warning correctly, and edit items without leaving an "
			"agent to argue at the door. Work the follow-up pool by claiming rather than "
			"colliding, and recover an abandoned cart while it is still worth "
			"recovering. Read their own summary honestly, including the difference "
			"between a confirmation problem and a delivery one."
		),
	},
	"ZhiftCRM Certified Closer Manager": {
		"who_for": (
			"Team leads and closer managers who answer for other people's numbers. "
			"Assumes the Closer track's ground, or equivalent time on the floor. It is "
			"not a configuration course — a manager who also administers the system "
			"should take the Consultant track as well."
		),
		"outcomes": (
			"Read Orders Status and Team Closer Summary for what they actually say: a "
			"rate with its denominator, a confirmation failure told apart from a "
			"delivery one, and 'Unassigned' recognised as a coverage finding rather "
			"than a person. Compare closers fairly by holding brand, branch and period "
			"still. Spot a process fault in a status column that no individual row "
			"reveals. Run a coaching conversation from evidence instead of a league "
			"table."
		),
	},
	"ZhiftCRM Certified Consultant": {
		"who_for": (
			"Implementation consultants and administrators who configure ZhiftCRM for "
			"clients and support it afterwards. Written for the person a client rings "
			"when something is wrong. It assumes you will be asked to justify a setting, "
			"not merely to change it."
		),
		"outcomes": (
			"Stand up a client's CRM end to end: closers and their remits, shift "
			"management and its coverage grid, the duplicate and consolidation settings "
			"and what each costs when wrong. Build and publish a campaign form, embed it "
			"by iframe or WordPress plugin, and diagnose a silent submission failure "
			"down to CORS. Explain every report to the person who owns it, compute a "
			"client's own ROAS profitability threshold from their margin, and say why "
			"attribution and ROAS will never reconcile."
		),
	},
	"ZhiftERP Accounts Professional": {
		"who_for": (
			"Accountants and accounts staff who post in ZhiftERP daily. Assumes "
			"bookkeeping knowledge; teaches the system, the controls around it, and the "
			"month-end that follows. Not for business owners who only read the output — "
			"that is Understanding Your Monthly Reports."
		),
		"outcomes": (
			"Own a chart of accounts that still makes sense in three years. Post any "
			"transaction to the right document rather than the convenient one. "
			"Reconcile a bank account nobody has touched for three months. Run "
			"receivables and payables so the aging tells the truth, close a period "
			"properly, and produce statements somebody can sign."
		),
	},
	"ZhiftERP HR Professional": {
		"who_for": (
			"HR officers and managers running the employee lifecycle in ZhiftERP. "
			"Assumes no system knowledge. Payroll is a separate track — this one stops "
			"where the salary structure begins."
		),
		"outcomes": (
			"Maintain an employee master and an organisation structure that reporting "
			"can rely on. Run recruitment and onboarding to a repeatable standard. "
			"Operate attendance, shifts and leave without the arguments those normally "
			"produce. Handle appraisals, transfers and exits so the record survives the "
			"person."
		),
	},
	"ZhiftERP Inventory Management Professional": {
		"who_for": (
			"Storekeepers, inventory controllers and anyone who answers for a count. "
			"Assumes no system knowledge. It covers what moves and how it is proved, "
			"not what is bought — procurement is its own track."
		),
		"outcomes": (
			"Set up warehouses and an item master that reconciles. Move stock with the "
			"right entry every time and know why the wrong one balances but lies. "
			"Operate serial and batch control where it matters. Run a stock "
			"reconciliation and a physical count that stands up, and explain a variance "
			"rather than absorbing it."
		),
	},
	"ZhiftERP Payroll Professional": {
		"who_for": (
			"Payroll officers and the accountants who check them, working in Nigeria. "
			"Covers PAYE, pension and the statutory calendar as they actually apply. "
			"Assumes the HR track's ground or equivalent familiarity with the employee "
			"master."
		),
		"outcomes": (
			"Build salary structures that survive a raise and a promotion. Compute PAYE "
			"and statutory deductions correctly and know where each figure comes from. "
			"Run a payroll cycle end to end, produce payslips people can read, and "
			"answer a query without recomputing the month. File and remit on the "
			"statutory calendar rather than after it."
		),
	},
	"ZhiftERP Procurement Professional": {
		"who_for": (
			"Buyers, procurement officers and store managers who raise and receive "
			"orders. Assumes no system knowledge. It ends at receipt; what happens to "
			"the stock afterwards is the Inventory track."
		),
		"outcomes": (
			"Run a supplier master worth having. Take a material request through RFQ, "
			"quotation and purchase order without losing the audit trail. Receive "
			"accurately, handle a short or damaged delivery properly, and match a "
			"three-way discrepancy. Read landed cost so a cheap price stops looking "
			"like a saving."
		),
	},
	"ZhiftERP Sales Professional": {
		"who_for": (
			"Sales administrators, order processors and the people who own the quote-"
			"to-cash chain in ZhiftERP. Assumes no system knowledge. It is a system and "
			"process track rather than a selling-skills course."
		),
		"outcomes": (
			"Maintain customers, items and price lists that hold their meaning. Take a "
			"quotation through to a sales order and an invoice without rekeying or "
			"drift. Handle partial deliveries, returns and credit notes so the ledger "
			"stays true. Read the sales reports for what they are measuring."
		),
	},
	"ZhiftERP Sysadmin Professional": {
		"who_for": (
			"System administrators responsible for a live ZhiftERP: users, permissions, "
			"master data and the day something breaks. Assumes comfort with the system "
			"as a user. It is written for the person who is called at eight in the "
			"evening."
		),
		"outcomes": (
			"Design roles and permissions that are defensible rather than convenient. "
			"Govern master data so duplicates never start. Run backups you have actually "
			"restored from. Diagnose a failure by evidence in a defined order, and know "
			"which changes need a change record and which do not."
		),
	},
	"CloudERP.One Certified Bookkeeper": {
		"who_for": (
			"Bookkeepers on the firm's own accounting service, working client books on "
			"CloudERP.One. Assumes accounting fundamentals. It teaches the craft, the "
			"cadence and the professional judgement — including what to do when a "
			"client asks for something you should refuse."
		),
		"outcomes": (
			"Post a client's day with narrations a stranger could follow. Take a month "
			"to a close that a reviewer will pass. Reconcile a bank that disagrees and "
			"find why rather than plugging it. Hold the review gate, raise a suspicious "
			"item the same day, cover a colleague's clients without dropping the "
			"cadence, and know the limits of your own competence in front of a client."
		),
	},
	"Understanding Your Monthly Reports": {
		"who_for": (
			"Business owners and directors who receive monthly accounts and want to read "
			"them properly. No accounting background assumed and none taught — this is "
			"about using the pack, not preparing it."
		),
		"outcomes": (
			"Read a profit and loss and a balance sheet without pretending. Understand "
			"why profit is not cash and where the difference went. Run the five checks "
			"worth doing every month, ask your accountant the questions that get real "
			"answers, and know what good looks like across a year rather than in one "
			"month."
		),
	},
	"ZhiftPOS Professional": {
		"outcomes": (
			"Command a ZhiftPOS estate end to end: the Point of Sale Profile at depth, "
			"commissioning and the terminal estate, shift operations and sales "
			"processing, concessions, returns and overrides, the extended counters and "
			"the voucher programme. Run daily verification and offline operation, clear "
			"the queue, reconcile a counter and supervise the people on it."
		),
	},
}

# The chapter that best shows the writing has judgement in it. Matched on a
# distinctive fragment of the title so a renumbering does not break this.
SAMPLE_HINTS = {
	"ZhiftERP HR Professional": ["leave", "attendance", "employee master"],
	"ZhiftERP Inventory Management Professional": ["reconciliation", "count", "stock entr"],
	"ZhiftERP Payroll Professional": ["statutory", "payroll run", "payslip"],
	"ZhiftERP Procurement Professional": ["landed", "receipt", "supplier"],
	"ZhiftERP Sales Professional": ["price list", "sales order", "quotation"],
	"ZhiftERP Sysadmin Professional": ["permission", "backup", "recovery"],
	"CloudERP.One Certified Bookkeeper": ["suspense", "reconcil", "review"],
	"Understanding Your Monthly Reports": ["profit is not cash", "questions worth", "five checks"],
	"Certified ZhiftPOS Operator": ["close", "shift", "sale"],
	"Certified ZhiftPOS Supervisor": ["close", "verif", "queue"],
	"ZhiftPOS Implementation Consultant": ["profile", "commission", "terminal"],
	"ZhiftPOS Professional": ["profile", "shift", "verif"],
}


def _pick_sample(track, hints):
	"""The best chapter to show a buyer, preferring one that carries a DRILL."""
	mods = frappe.get_all("Duty Certification Track Module",
						  filters={"parent": track}, pluck="module", order_by="idx asc")
	if not mods:
		return None
	rows = frappe.get_all("Duty Lesson", filters={"module": ["in", mods]},
						  fields=["name", "title", "content", "module"],
						  order_by="module asc, idx asc", limit_page_length=0)
	if not rows:
		return None
	drilled = [r for r in rows if "DRILL" in (r.content or "")]
	pool = drilled or rows
	for h in (hints or []):
		for r in pool:
			if h.lower() in (r.title or "").lower():
				return r
	# no hint matched: the second chapter of the first module reads better as a
	# sample than the first, which is usually scene-setting
	return pool[1] if len(pool) > 1 else pool[0]


@frappe.whitelist()
def fill(dry_run=1):
	dry = cint(dry_run)
	changed, samples = [], []

	for title, vals in META.items():
		name = frappe.db.get_value("Duty Certification Track", {"title": title}, "name")
		if not name:
			print("  ?? no track titled %r" % title)
			continue
		upd = {}
		for k, v in vals.items():
			if not (frappe.db.get_value("Duty Certification Track", name, k) or "").strip():
				upd[k] = v
		if upd:
			changed.append("%s <- %s" % (title, ", ".join(sorted(upd))))
			if not dry:
				frappe.db.set_value("Duty Certification Track", name, upd)

	for title, hints in SAMPLE_HINTS.items():
		name = frappe.db.get_value("Duty Certification Track", {"title": title}, "name")
		if not name:
			continue
		mods = frappe.get_all("Duty Certification Track Module",
							  filters={"parent": name}, pluck="module")
		if mods and frappe.db.exists("Duty Lesson", {"is_sample": 1, "module": ["in", mods]}):
			continue
		les = _pick_sample(name, hints)
		if not les:
			continue
		samples.append("%s <- %s" % (title, les.title))
		if not dry:
			frappe.db.set_value("Duty Lesson", les.name, "is_sample", 1)

	if not dry:
		frappe.db.commit()

	head = "DRY RUN" if dry else "DONE"
	print("%s — %d track(s) gain who_for/outcomes:" % (head, len(changed)))
	for c in changed:
		print("   %s" % c)
	print("%s — %d sample chapter(s) marked:" % (head, len(samples)))
	for c in samples:
		print("   %s" % c)
	if dry:
		print('\nRe-run with --kwargs "{\'dry_run\': 0}" to apply.')
	return {"meta": len(changed), "samples": len(samples)}
