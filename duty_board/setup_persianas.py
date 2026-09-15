#!/usr/bin/env python3
"""Create the Persianas Retail Limited implementation from the signed Service
Agreement (Ref ZH-PRS-2026-047, signed 31 August 2026).

Run:
    bench --site xlevel.clouderp.one execute duty_board.setup_persianas.build --kwargs "{'lead': 'olamide@xlevelretail.com'}"
    bench --site xlevel.clouderp.one execute duty_board.setup_persianas.build --kwargs "{'lead': 'olamide@xlevelretail.com', 'dry_run': 0}"

Creates, in order: the Customer if missing, the Client Room, the Duty Project
with baseline, seven phases, tasks, deliverables, risks, decisions, and the
executive kick-off meeting. Idempotent on the project name: if the project
exists nothing is touched.

WHERE THE DATES COME FROM. Agreement §4 gives a sixteen-week programme in
week ranges, keyed to a Kick-Off Date. The executive kick-off is Monday
14 September 2026 at 12:00, which is week 1 day 1, so every week number lands
on a Monday-to-Friday and every phase end is the Friday of the week §4 names.

    Discovery & Business Analysis   weeks 1-2      ends Fri 25 Sep
    System Configuration            weeks 3-6      ends Fri 23 Oct
    Custom Development              weeks 4-10     ends Fri 20 Nov
    Data Migration                  weeks 7-11     ends Fri 27 Nov
    Training & UAT                  weeks 11-14    ends Fri 18 Dec
    Go-Live                         weeks 14-16    Thu 31 Dec  (Fri 1 Jan is a holiday)
    Hypercare                       60 days        to Mon 1 Mar 2027

THREE THINGS THE CONTRACT DOES NOT SAY OUT LOUD, recorded here so they are on
the project from day one rather than discovered in week 14:

1. Week 15 is Christmas and week 16 ends on New Year's Day. §4 puts the phased
   branch rollout in weeks 14-16 — a retail chain's peak trading period. This
   is baselined exactly as the contract says, because the baseline is the
   contract, and logged as the first risk and a Proposed decision for the
   kick-off. §4 allows a written adjustment; the point is to have it in
   writing in week 1, not week 13.
2. §4 defines the Kick-Off Date as the first working day after receipt of the
   Milestone 1 Mobilisation Payment (₦20,340,000). If that has not landed by
   Friday 11 September, Monday 14 September is a meeting, not the Kick-Off
   Date, and this baseline moves. Confirm before running with dry_run=0.
3. The Agreement's own module list (§3.1) is the scope. Shopify multi-store
   integration and HR & Payroll are both inside it and inside the fee — they
   are workstreams here, not change requests.

Custom Development (weeks 4-10) overlaps Configuration and Data Migration by
design; the contract schedules it that way. The Gantt shows the overlap; the
portal's phase strip shows phase ends in order, which they are.
"""

import frappe
from frappe.utils import add_days, cint, getdate

START = "2026-09-14"
KICKOFF_TIME = "12:00:00"
CUSTOMER = "Persianas Retail Limited"
PROJECT_NAME = "ZhiftERP Implementation — Persianas Retail Limited"
CONTRACT = "Service Agreement ZH-PRS-2026-047"

# Phase: (title, end date, description shown to the client)
PHASES = [
	("Discovery & Business Analysis", "2026-09-25",
	 "Executive kick-off, AS-IS process mapping across all departments and the "
	 "16 branches, the TO-BE blueprint, data migration plan and system "
	 "architecture. Ends with architecture sign-off by PRL IT and Finance."),
	("System Configuration", "2026-10-23",
	 "Every module configured on your staging environment and ZhiftPOS "
	 "installed at the pilot branch. Each department head signs off their "
	 "module's configuration."),
	("Custom Development", "2026-11-20",
	 "The Shopify multi-store integration and the Planning & Forecasting Tool "
	 "built and tested, plus Nigerian localisation, print formats and branch "
	 "P&L segmentation. Ends with UAT acceptance of both custom deliverables."),
	("Data Migration", "2026-11-27",
	 "Masters, opening balances, stock, accounts and HR data for all 16 "
	 "branches migrated, reconciled and signed off by the Finance Director."),
	("Training & UAT", "2026-12-18",
	 "Role-based training for all 150 users and UAT cycles per module. "
	 "Department leads sign off each module."),
	("Go-Live", "2026-12-31",
	 "Phased rollout branch by branch with on-site support, ending with "
	 "go-live acceptance by the CEO / COO."),
	("Hypercare", "2027-03-01",
	 "Sixty days of elevated support from the people who built it, ending "
	 "with handover to your own administrators and the project closeout."),
]

MODULES = [
	"Retail Operations (multi-branch)", "ZhiftPOS", "Sales Order Management",
	"CRM & Loyalty", "Accounting & Financial Management", "HR & Payroll",
	"Inventory & Stock Transfer", "Procurement", "Supplier Management",
	"Shopify Integration",
]

# (title, phase index, days before the phase end, estimate hours, client visible)
TASKS = [
	# ---- 1 Discovery & Business Analysis (ends Fri 25 Sep)
	("Confirm Milestone 1 mobilisation payment received — Kick-Off Date per §4", 0, 11, 1, 0),
	("Executive kick-off: vision, scope, schedule, roles", 0, 11, 4, 1),
	("PRL names Project Sponsor, Project Manager and department leads (§5, due 14 Sep)", 0, 11, 1, 1),
	("Governance, communication plan and sign-off gates agreed (5-business-day rule, §5)", 0, 10, 4, 1),
	("POS hardware specification issued to PRL (terminals, printers, scanners)", 0, 10, 4, 1),
	("Branch survey — connectivity, hardware and layout for all 16 branches", 0, 9, 16, 1),
	("Workshop — Retail Operations and ZhiftPOS", 0, 8, 8, 1),
	("Workshop — Sales Orders, CRM and Loyalty Programme", 0, 8, 6, 1),
	("Workshop — Accounting, multi-entity chart of accounts and reporting", 0, 7, 8, 1),
	("Workshop — HR and Payroll (PAYE, pension, NHF, NSITF, leave)", 0, 7, 8, 1),
	("Workshop — Inventory, stock transfer, replenishment and FIFO costing", 0, 7, 8, 1),
	("Workshop — Procurement and supplier management", 0, 7, 6, 1),
	("Workshop — Shopify storefronts: order, stock, customer and loyalty flows", 0, 7, 8, 1),
	("Workshop — Planning & Forecasting Tool requirements", 0, 7, 6, 1),
	("PRL provides Shopify storefront credentials (§5, due 21 Sep)", 0, 4, 1, 1),
	("AS-IS process maps compiled", 0, 3, 16, 1),
	("TO-BE blueprint drafted", 0, 2, 20, 1),
	("Data Migration Plan issued with templates per data set", 0, 1, 8, 1),
	("System architecture document — hosting, integration, security", 0, 1, 8, 1),
	("User Role and Permission Matrix drafted (150 users)", 0, 1, 8, 1),
	("Architecture sign-off by PRL IT and Finance", 0, 0, 2, 1),
	# ---- 2 System Configuration (ends Fri 23 Oct)
	("Provision staging environment on managed cloud", 1, 21, 6, 0),
	("Company, entity, branch and cost-centre structure configured (16 branches)", 1, 18, 12, 1),
	("Multi-entity chart of accounts configured", 1, 16, 16, 1),
	("Configure — Accounting and Financial Management", 1, 14, 32, 1),
	("Configure — Procurement and Purchase Orders", 1, 14, 20, 1),
	("Configure — Inventory, FIFO valuation, multi-location transfer and replenishment", 1, 11, 32, 1),
	("Configure — Supplier and Vendor Management", 1, 10, 8, 1),
	("Configure — Sales Order Management", 1, 9, 16, 1),
	("Configure — CRM and Loyalty Programme", 1, 8, 24, 1),
	("Configure — HR: employee master, departments, leave, attendance", 1, 7, 24, 1),
	("Configure — Payroll: salary structures, PAYE, pension, NHF, NSITF", 1, 7, 32, 1),
	("Configure — Retail Operations and ZhiftPOS profiles", 1, 4, 32, 1),
	("ZhiftPOS installed and tested at the pilot branch", 1, 3, 24, 1),
	("Users and permissions applied from the matrix", 1, 2, 8, 1),
	("Unit test all modules on staging", 1, 1, 16, 0),
	("Module configuration sign-off by each department head", 1, 0, 4, 1),
	# ---- 3 Custom Development (ends Fri 20 Nov)
	("Shopify integration — technical design and API scoping", 2, 35, 12, 1),
	("Shopify integration — orders inbound (all storefronts)", 2, 28, 32, 0),
	("Shopify integration — inventory sync outbound", 2, 22, 24, 0),
	("Shopify integration — customers and loyalty points bidirectional", 2, 17, 24, 0),
	("Shopify integration — multi-store mapping and conflict handling", 2, 14, 16, 0),
	("Forecasting Tool — design: branch and category projections", 2, 30, 12, 1),
	("Forecasting Tool — demand engine and procurement recommendations", 2, 21, 40, 0),
	("Forecasting Tool — budget vs actual variance reporting", 2, 15, 16, 0),
	("Forecasting Tool — P&L projection linked to live data", 2, 11, 24, 0),
	("Nigerian localisation and statutory reports", 2, 14, 16, 1),
	("Custom print formats — invoices and operational documents", 2, 9, 12, 1),
	("Branch-level P&L segmentation", 2, 7, 12, 1),
	("Integration test — Shopify against live storefront (sandbox)", 2, 4, 16, 1),
	("Custom deliverables handed to PRL for UAT", 2, 2, 4, 1),
	("UAT acceptance — Shopify integration and Forecasting Tool", 2, 0, 4, 1),
	# ---- 4 Data Migration (ends Fri 27 Nov)
	("PRL returns completed migration templates", 3, 28, 2, 1),
	("Data cleansing and validation with PRL", 3, 22, 24, 1),
	("Migrate item and product masters with barcodes and price lists", 3, 18, 20, 0),
	("Migrate customer records and loyalty balances", 3, 15, 12, 0),
	("Migrate supplier list", 3, 14, 6, 0),
	("Migrate chart of accounts mappings and cost centres", 3, 14, 8, 0),
	("Migrate employee records, salary history and YTD PAYE/pension", 3, 10, 16, 0),
	("Migrate opening stock — quantities and FIFO valuation per branch", 3, 7, 24, 0),
	("Post and reconcile opening balances per entity", 3, 4, 20, 1),
	("Payroll parallel run — one cycle against current payroll", 3, 3, 16, 1),
	("Data reconciliation report issued — counts and control totals", 3, 1, 8, 1),
	("Data reconciliation sign-off by Finance Director", 3, 0, 2, 1),
	# ---- 5 Training & UAT (ends Fri 18 Dec)
	("Training plan, schedule and role-based manuals issued", 4, 25, 24, 1),
	("UAT scripts issued per module", 4, 24, 16, 1),
	("Train — branch managers and POS users (16 branches)", 4, 21, 40, 1),
	("Train — finance and accounts users", 4, 18, 12, 1),
	("Train — inventory, procurement and warehouse users", 4, 17, 12, 1),
	("Train — HR and payroll users", 4, 16, 12, 1),
	("Train — CRM, sales order and e-commerce users", 4, 15, 8, 1),
	("Train — system administrators", 4, 14, 16, 1),
	("PRL executes UAT scripts per module", 4, 10, 8, 1),
	("Triage and fix S1 and S2 defects", 4, 7, 32, 1),
	("Training completion registers signed", 4, 2, 2, 1),
	("UAT sign-off per module by department leads", 4, 0, 4, 1),
	# ---- 6 Go-Live (ends Thu 31 Dec)
	("Branch rollout sequence and cutover plan agreed, including rollback", 5, 13, 8, 1),
	("POS hardware delivered and staged at all 16 branches", 5, 10, 8, 1),
	("Go-Live readiness review with PRL", 5, 9, 4, 1),
	("Go-Live Readiness Checklist signed", 5, 8, 2, 1),
	("Final data cutover and balance freeze", 5, 7, 16, 1),
	("Rollout wave 1 — pilot and first branches, on-site support", 5, 7, 24, 1),
	("Rollout wave 2 — remaining branches, on-site support", 5, 2, 32, 1),
	("First live payroll run on ZhiftERP", 5, 1, 8, 1),
	("Go-live acceptance by CEO / COO — all 16 branches", 5, 0, 4, 1),
	# ---- 7 Hypercare (ends Mon 1 Mar 2027)
	("Daily hypercare check — first two weeks", 6, 46, 20, 1),
	("Weekly hypercare review with PRL", 6, 31, 16, 1),
	("First month-end close on ZhiftERP supported", 6, 28, 12, 1),
	("S3 and S4 remediation from UAT", 6, 25, 24, 1),
	("Shopify sync monitoring and reconciliation report", 6, 20, 8, 1),
	("Issue log and monitoring report", 6, 10, 8, 1),
	("System administration handover pack", 6, 5, 12, 1),
	("Project closeout report", 6, 3, 8, 1),
	("Hypercare exit acceptance signed — start of annual support under §9", 6, 0, 4, 1),
]

# (title, phase index, days before phase end, acceptance criteria)
DELIVERABLES = [
	("AS-IS process maps and TO-BE blueprint", 0, 2,
	 "Every in-scope process across the ten workstreams and the 16 branches "
	 "mapped as it runs today and as it will run on ZhiftERP, reviewed in "
	 "workshop and confirmed by the process owner for each area."),
	("Data Migration Plan and templates", 0, 1,
	 "A template issued for each data set in scope — items, customers, "
	 "suppliers, chart of accounts, opening stock, employees — with the fields "
	 "required, the format expected and the date it must be returned."),
	("System architecture — signed off by PRL IT and Finance", 0, 0,
	 "Hosting, integration points (Shopify, POS), security and backup design "
	 "documented and signed by PRL IT and Finance. Agreement §4, Phase 1 gate."),
	("Configured staging environment with ZhiftPOS at the pilot branch", 1, 0,
	 "Every module configured per the signed blueprint, ZhiftPOS live at the "
	 "pilot branch, and each department head's configuration sign-off on "
	 "file. Agreement §4, Phase 2 gate."),
	("Shopify Multi-Store Integration — UAT accepted", 2, 0,
	 "Orders, inventory, customers and loyalty points synchronise in both "
	 "directions across every Persianas storefront, demonstrated in UAT and "
	 "accepted in writing. Agreement §3.2 and §4, Phase 3 gate."),
	("Planning & Forecasting Tool — UAT accepted", 2, 0,
	 "Branch- and category-level projections, procurement recommendations, "
	 "budget vs actual variance and P&L projection run against live data and "
	 "accepted in UAT. Agreement §3.2 and §4, Phase 3 gate."),
	("Data reconciliation sign-off by Finance Director", 3, 0,
	 "Record counts and control totals agree to source for every data set, "
	 "opening balances reconcile to PRL's closing trial balance per entity, "
	 "and the payroll parallel run matches current payroll. Agreement §4, "
	 "Phase 4 gate."),
	("UAT sign-off per module and training registers", 4, 0,
	 "UAT scripts executed for every module with no open S1 or S2 defects, "
	 "signed by the department lead for each, and a signed attendance "
	 "register for every user group. Agreement §4, Phase 5 gate. Triggers "
	 "Milestone 3 invoice under §6.2."),
	("Go-Live Readiness Checklist", 5, 8,
	 "UAT signed off, data validated, training delivered, POS hardware staged "
	 "at every branch, and a cutover plan agreed including rollback."),
	("Go-live acceptance by CEO / COO", 5, 0,
	 "All 16 branches transacting on ZhiftERP and ZhiftPOS, signed by the "
	 "CEO or COO. Agreement §4, Phase 6 gate. Triggers Milestone 4 invoice."),
	("Project Closeout Report and handover pack", 6, 0,
	 "Hypercare activity log, issue log and a system administration handover "
	 "pack accepted by PRL's named administrators; support moves to the SLA "
	 "in Agreement §9."),
]

RISKS = [
	("Go-live scheduled into Christmas trading — weeks 14-16 are 14 Dec to 1 Jan", "High", "High",
	 "Raise at the executive kick-off, not later. Options: hold the contract "
	 "dates with wave 1 before 18 Dec and wave 2 in the first week of January; "
	 "or agree a written adjustment under §4. Either way the decision goes in "
	 "the log in week 1 with the sponsor's name on it."),
	("Milestone 1 payment not received before 14 September", "Medium", "High",
	 "§4 makes the Kick-Off Date conditional on receipt. Confirm with Zhift "
	 "finance on Friday 11 Sep. If unpaid, hold the meeting as a pre-kick-off "
	 "and re-baseline from the receipt date in writing."),
	("Shopify credentials or API access late", "Medium", "High",
	 "Due 21 Sep under §5. Chase on day 5 in writing. Custom Development "
	 "cannot start its integration build without them, and it is the longest "
	 "workstream."),
	("Migration data from 16 branches returned late or inconsistent", "High", "High",
	 "Templates issued week 2 with named owners per branch. Weekly chase from "
	 "week 3. §10.3 puts delay on PRL when data is late — flag in writing the "
	 "first week a branch misses, not the third."),
	("POS hardware not procured in time for rollout", "Medium", "High",
	 "Specification issued in week 1; §5 makes procurement PRL's decision. "
	 "Ask for the purchase order by week 6 and delivery by week 13."),
	("Payroll cutover — statutory YTD figures and first live run", "Medium", "High",
	 "Parallel run in Data Migration against the current payroll before "
	 "cutover. A 1 January go-live is the cleanest possible PAYE year start; "
	 "protect that date for payroll even if branches phase."),
	("Key users unavailable during peak season for UAT and training (weeks 11-14)", "High", "Medium",
	 "Training dates agreed at kick-off and in the client's calendar. Branch "
	 "manager training front-loaded to week 11 before December trading peaks."),
	("Forecasting Tool scope grows beyond §3.2", "Medium", "Medium",
	 "The four functions in §3.2 are the scope. Anything beyond them is a "
	 "change request; record every scope call in the decision log."),
]

DECISIONS = [
	("Sixteen-week programme keyed to Monday 14 September 2026", "Agreed",
	 CONTRACT + " §4", "PRL and Zhift Platforms",
	 "§4 sets a sixteen-week programme from the Kick-Off Date. The executive "
	 "kick-off is Monday 14 September at 12:00; this plan is the dated "
	 "baseline of the contract's week ranges.",
	 "A calendar-driven start independent of Milestone 1 receipt.",
	 "This plan is the baseline. Slip is measured against it. Any material "
	 "change needs written agreement from both parties under §4."),
	("Phased branch rollout across weeks 14-16, not big-bang", "Agreed",
	 CONTRACT + " §4, Phase 6", "PRL and Zhift Platforms",
	 "The contract specifies a phased rollout with on-site go-live support. "
	 "Sixteen branches cannot be supported on site on one day.",
	 "Big-bang across all branches on one date.",
	 "Branches run mixed for up to two weeks; the rollout sequence and "
	 "reconciliation approach are agreed in the cutover plan."),
	("Scope is the §3.1 module list plus the two §3.2 custom builds", "Agreed",
	 CONTRACT + " §3", "PRL and Zhift Platforms",
	 "Retail Operations, ZhiftPOS, Sales Orders, CRM & Loyalty, Accounting, "
	 "multi-entity CoA, HR & Payroll, Inventory & Transfers, Procurement, "
	 "Suppliers, Shopify integration and the Forecasting Tool — 16 branches, "
	 "150 users, ceiling 40 branches / 300 users.",
	 "Deferring HR & Payroll or Shopify to a later phase.",
	 "Both are inside the Development Fee and this timeline. Anything beyond "
	 "is a change request."),
	("Go-live date relative to Christmas trading", "Proposed",
	 "Zhift Platforms, at planning", "Pending — executive kick-off",
	 "The contract's week 16 ends on New Year's Day and week 15 is Christmas. "
	 "PRL must choose between the contract dates and a written adjustment.",
	 "(a) Hold contract dates: wave 1 before 18 Dec, wave 2 first week of "
	 "January, payroll live 1 Jan. (b) Written adjustment under §4 moving "
	 "full go-live to mid-January. (c) Full rollout before 18 Dec — not "
	 "recommended; compresses UAT.",
	 "Undecided until kick-off. Whichever is chosen is recorded here and the "
	 "baseline stays as signed unless (b) is agreed in writing."),
]


def _customer(dry):
	if frappe.db.exists("Customer", CUSTOMER):
		print("   customer exists: %s" % CUSTOMER)
		return CUSTOMER
	if dry:
		print("   would create customer %r" % CUSTOMER)
		return CUSTOMER
	doc = frappe.get_doc({
		"doctype": "Customer", "customer_name": CUSTOMER,
		"customer_type": "Company",
		"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}) or "All Customer Groups",
		"territory": "All Territories",
	})
	doc.insert(ignore_permissions=True)
	print("   customer created: %s" % doc.name)
	return doc.name


def _room(dry, customer):
	name = frappe.db.get_value("Client Room", {"customer": customer}, "name")
	if name:
		print("   room exists: %s" % name)
		return name
	if dry:
		print("   would create room for %s" % customer)
		return None
	doc = frappe.get_doc({
		"doctype": "Client Room", "customer": customer,
		"title": "%s · General" % customer, "status": "Active",
	})
	doc.insert(ignore_permissions=True)
	print("   room created: %s" % doc.name)
	return doc.name


def _kickoff_meeting(dry, room, customer, project, lead):
	"""The executive kick-off. `lead` is the staff member who owns the meeting:
	requester, confirmer and first attendee. bench execute runs as
	Administrator, which must not be the name on a client-facing meeting, so
	the caller passes a real user. Attendees is a mandatory table — Duty
	Meeting.on_update sends calendar invitations to everyone on it, so only
	the lead is added here; the rest are added from the meeting itself."""
	topic = "Executive kick-off — ZhiftERP implementation"
	if frappe.db.exists("Duty Meeting", {"room": room, "meeting_date": START, "topic": topic}):
		print("   kick-off meeting exists")
		return
	if dry:
		print("   would create kick-off meeting %s %s, led by %s" % (START, KICKOFF_TIME[:5], lead))
		return
	frappe.get_doc({
		"doctype": "Duty Meeting", "room": room, "customer": customer,
		"project": project, "topic": topic,
		"meeting_date": START, "start_time": KICKOFF_TIME, "duration_mins": 120,
		"status": "Confirmed", "requested_by": lead, "confirmed_by": lead,
		"attendees": [{"user": lead}],
	}).insert(ignore_permissions=True)
	print("   kick-off meeting created: %s %s, 120 min, led by %s" % (START, KICKOFF_TIME[:5], lead))


@frappe.whitelist()
def build(dry_run=1, lead="olamide@xlevelretail.com"):
	"""lead: email of the staff member who leads the engagement — goes on the
	kick-off meeting. Required for a real run; bench execute has no useful
	session user."""
	dry = cint(dry_run)
	if not lead or not frappe.db.exists("User", lead):
		frappe.throw("Pass lead=&lt;staff email&gt; — the person who leads this engagement "
					 "and owns the kick-off meeting. Got %r." % lead)
	print("%s — Persianas Retail Limited implementation, kick-off %s %s"
		  % ("DRY RUN" if dry else "BUILDING", START, KICKOFF_TIME[:5]))
	if frappe.db.exists("Duty Project", {"project_name": PROJECT_NAME}):
		print("   project already exists — nothing done. Delete it first to rebuild.")
		return {"ok": 0}
	customer = _customer(dry)
	room = _room(dry, customer)

	proj = None
	if not dry:
		proj = frappe.get_doc({
			"doctype": "Duty Project", "project_name": PROJECT_NAME,
			"customer": customer, "room": room, "status": "Active",
			"target_date": PHASES[5][1],
			# Baseline set here and never moved: it is the contract's own
			# schedule, and slip only means something against that.
			"baseline_target_date": PHASES[5][1],
			"baselined_on": frappe.utils.now_datetime(),
		})
		proj.insert(ignore_permissions=True)
		print("   project: %s (go-live %s, baselined)" % (proj.name, PHASES[5][1]))
	else:
		print("   would create project %r, go-live %s, baseline the same"
			  % (PROJECT_NAME, PHASES[5][1]))

	ms = []
	for i, (title, end, desc) in enumerate(PHASES):
		if dry:
			print("   phase %d  %-32s ends %s" % (i + 1, title, end))
			ms.append(None)
			continue
		m = frappe.get_doc({
			"doctype": "Duty Milestone", "room": room, "project": proj.name,
			"title": title, "description": desc, "sort_order": i + 1,
			"status": "Upcoming", "target_date": end, "baseline_date": end,
		})
		m.insert(ignore_permissions=True)
		ms.append(m.name)

	made = 0
	for title, pi, back, est, vis in TASKS:
		due = str(add_days(getdate(PHASES[pi][1]), -back))
		if not dry:
			frappe.get_doc({
				"doctype": "Duty Project Task", "project": proj.name,
				"milestone": ms[pi], "title": title, "column": "To Do",
				"due_date": due, "estimate_hours": est,
				"client_visible": vis, "urgency": "Medium",
			}).insert(ignore_permissions=True)
		made += 1

	dl = 0
	for title, pi, back, crit in DELIVERABLES:
		due = str(add_days(getdate(PHASES[pi][1]), -back))
		if not dry:
			frappe.get_doc({
				"doctype": "Duty Project Deliverable", "project": proj.name,
				"milestone": ms[pi], "title": title, "due_date": due,
				"criteria": crit, "status": "Not started", "client_visible": 1,
			}).insert(ignore_permissions=True)
		dl += 1

	rk = 0
	for title, likely, impact, mit in RISKS:
		if not dry:
			frappe.get_doc({
				"doctype": "Duty Project Risk", "project": proj.name,
				"title": title, "likelihood": likely, "impact": impact,
				"mitigation": mit, "status": "Open", "client_visible": 0,
			}).insert(ignore_permissions=True)
		rk += 1

	dc = 0
	for title, status, raised, decided, why, alts, impact in DECISIONS:
		if not dry:
			frappe.get_doc({
				"doctype": "Duty Project Decision", "project": proj.name,
				"title": title, "status": status, "decided_on": START,
				"raised_by": raised, "decided_by": decided, "context": why,
				"options_considered": alts, "impact": impact, "client_visible": 1,
			}).insert(ignore_permissions=True)
		dc += 1

	_kickoff_meeting(dry, room, customer, proj.name if proj else None, lead)

	if not dry:
		frappe.db.commit()
	print("\n   %d phases · %d tasks · %d deliverables · %d risks · %d decisions"
		  % (len(PHASES), made, dl, rk, dc))
	print("   estimated effort: %d hours" % sum(t[3] for t in TASKS))
	if dry:
		print('\n   Re-run with --kwargs "{\'lead\': \'%s\', \'dry_run\': 0}" to create it.' % lead)
	return {"ok": 1, "tasks": made}
