#!/usr/bin/env python3
"""Create the Montaigne AH implementation from the signed SOW.

Run:
    bench --site xlevel.clouderp.one execute duty_board.setup_montaigne.build
    bench --site xlevel.clouderp.one execute duty_board.setup_montaigne.build --kwargs "{'dry_run': 0}"

WHERE THE DATES COME FROM. The SOW's own project schedule, keyed to a kick-off
of Monday 7 September 2026 — which is a Monday, so the week numbers land
cleanly. Nothing here is invented: every phase end is the Friday of the week the
SOW names.

    Analysis                    weeks 1-2      ends Fri 18 Sep
    Design / blueprint sign-off within phase 1  ends Wed 23 Sep
    Configuration & Build       weeks 3-7      ends Fri 23 Oct
    Data Migration & Testing    weeks 8-10     ends Fri 13 Nov
    UAT & Training              weeks 11-12    ends Fri 27 Nov
    Go-Live                     week 12/13     Fri 4 Dec
    Hypercare                   60 days        to Tue 2 Feb 2027

THE SOW AND THE SLA DISAGREE, and the SOW is followed. The SOW schedule has
five numbered phases over 12-13 weeks; SLA §4.1 describes the same work as
three phases over 12 weeks and calls its own plan "indicative", adding that a
detailed dated plan will be baselined at kick-off. That baselined plan is this
one. Where the two conflict on grouping, the SOW's finer breakdown is used
because it names deliverables per phase and the SLA does not.

Design is given until Wednesday 23 September rather than ending with Analysis:
SLA §4.4 gives the client five business days to accept a milestone, and a
blueprint sign-off gate with no time in it for the sign-off is a gate in name
only.
"""

import frappe
from frappe.utils import add_days, cint, getdate

START = "2026-09-07"
CUSTOMER = "Montaigne AH Ltd"

# Phase: (title, end date, description shown to the client)
PHASES = [
	("Analysis", "2026-09-18",
	 "Kick-off, business process workshops across all six modules, and the "
	 "Functional Requirements Document. Ends with requirements agreed."),
	("Design & Blueprint Sign-Off", "2026-09-23",
	 "The Configuration Blueprint, warehouse and location design, chart of "
	 "accounts, workflows and integration design — signed off before any "
	 "configuration begins."),
	("Configuration & Build", "2026-10-23",
	 "All six modules configured on your staging environment, ZhiftPOS deployed "
	 "with offline mode, cross-module integrations built and unit tested."),
	("Data Migration & Integration Testing", "2026-11-13",
	 "Master data migrated and validated, opening balances posted and reconciled, "
	 "and integration testing signed off."),
	("UAT & Training", "2026-11-27",
	 "Your team tests the system against structured scripts and is trained on it. "
	 "Defects found are fixed before go-live."),
	("Go-Live", "2026-12-04",
	 "Readiness review, cutover and big-bang go-live across all branch locations."),
	("Hypercare", "2027-02-02",
	 "Sixty days of elevated support from the people who built it, ending with "
	 "handover to your own administrators."),
]

MODULES = ["Financial Control", "Procurement", "Inventory Management",
		   "Central CRM", "ZhiftPOS", "Fixed Assets"]

# (title, phase index, days before the phase end, estimate hours, client visible)
TASKS = [
	# ---- Analysis
	("Executive kick-off: vision, scope, schedule, roles", 0, 9, 4, 1),
	("Governance and communication plan agreed", 0, 8, 4, 1),
	("Confirm project sponsor, coordinator and key users", 0, 8, 2, 1),
	("Workshop — Financial Control", 0, 6, 8, 1),
	("Workshop — Procurement", 0, 6, 6, 1),
	("Workshop — Inventory Management", 0, 5, 8, 1),
	("Workshop — Central CRM", 0, 4, 6, 1),
	("Workshop — ZhiftPOS and store operations", 0, 3, 8, 1),
	("Workshop — Fixed Assets", 0, 3, 4, 1),
	("Functional Requirements Document drafted", 0, 1, 16, 1),
	("User Role and Permission Matrix drafted", 0, 1, 8, 1),
	("Data Migration Plan issued with templates", 0, 0, 8, 1),
	# ---- Design
	("Configuration Blueprint compiled", 1, 4, 20, 1),
	("Warehouse and location design", 1, 3, 6, 1),
	("Chart of accounts design — multi-brand, multi-cost-centre", 1, 3, 10, 1),
	("Workflow and approval design", 1, 2, 8, 1),
	("Integration design document — NGE Portal and cross-module", 1, 2, 10, 1),
	("Blueprint walkthrough with the client", 1, 1, 4, 1),
	("Blueprint signed off", 1, 0, 2, 1),
	# ---- Configuration & Build
	("Provision staging environment on managed cloud", 2, 32, 6, 0),
	("Company, brand and branch structure configured", 2, 30, 8, 1),
	("Chart of accounts and cost centres configured", 2, 28, 12, 1),
	("Configure — Financial Control", 2, 22, 32, 1),
	("Configure — Procurement", 2, 20, 24, 1),
	("Configure — Inventory Management", 2, 16, 32, 1),
	("Configure — Fixed Assets", 2, 14, 16, 1),
	("Configure — Central CRM", 2, 11, 24, 1),
	("Configure — ZhiftPOS terminals and profiles", 2, 8, 32, 1),
	("ZhiftPOS offline mode built and tested", 2, 6, 24, 0),
	("Cross-module integrations built", 2, 5, 24, 0),
	("FIRS e-invoicing via NGE Portal configured", 2, 4, 16, 1),
	("Custom dashboards and reports configured", 2, 3, 16, 1),
	("Unit test all six modules", 2, 1, 16, 0),
	("Users and permissions applied from the matrix", 2, 0, 8, 1),
	# ---- Data Migration & Testing
	("Client returns completed migration templates", 3, 18, 2, 1),
	("Data cleansing and validation with the client", 3, 15, 16, 1),
	("Migrate customers and suppliers", 3, 12, 12, 0),
	("Migrate item master and price lists", 3, 11, 16, 0),
	("Migrate fixed asset register", 3, 9, 8, 0),
	("Migrate opening stock quantities and valuations", 3, 7, 12, 0),
	("Post and reconcile opening balances", 3, 5, 16, 1),
	("Integration testing across modules", 3, 3, 20, 0),
	("Migration reconciliation report issued", 3, 1, 8, 1),
	("Integration Test Sign-Off", 3, 0, 4, 1),
	# ---- UAT & Training
	("Training plan and manuals issued", 4, 12, 20, 1),
	("UAT scripts issued to the client", 4, 11, 12, 1),
	("Train — finance and accounts users", 4, 9, 12, 1),
	("Train — procurement and inventory users", 4, 8, 12, 1),
	("Train — store and POS users", 4, 7, 16, 1),
	("Train — CRM users", 4, 6, 8, 1),
	("Train — the three ERP system administrators", 4, 5, 16, 1),
	("Client executes UAT scripts", 4, 4, 8, 1),
	("Triage and fix S1 and S2 defects", 4, 2, 24, 1),
	("Training completion registers signed", 4, 1, 2, 1),
	("UAT signed off", 4, 0, 4, 1),
	# ---- Go-Live
	("Cutover plan agreed, including rollback", 5, 5, 8, 1),
	("Go-Live readiness review with the client", 5, 3, 4, 1),
	("Go-Live Readiness Checklist signed", 5, 2, 2, 1),
	("Final data cutover and balance freeze", 5, 1, 12, 1),
	("Big-bang go-live across all branches", 5, 0, 12, 1),
	# ---- Hypercare
	("Daily hypercare check — week one", 6, 53, 10, 1),
	("Weekly hypercare review with the client", 6, 30, 12, 1),
	("S3 and S4 remediation from UAT", 6, 25, 20, 1),
	("Issue log and monitoring report", 6, 10, 8, 1),
	("System administration handover pack", 6, 5, 12, 1),
	("Project closeout report", 6, 1, 8, 1),
	("Hypercare exit acceptance checklist signed", 6, 0, 4, 1),
]

# (title, phase index, days before phase end, acceptance criteria)
DELIVERABLES = [
	("Functional Requirements Document", 0, 0,
	 "Every in-scope process across the six modules documented, reviewed in "
	 "workshop, and confirmed by the process owner for each area."),
	("User Role and Permission Matrix", 0, 0,
	 "Every user group mapped to a role, and every role to the permissions it "
	 "carries, with no user left unassigned."),
	("Data Migration Plan and templates", 0, 0,
	 "A template issued for each data set in scope, with the fields required, "
	 "the format expected and the date it must be returned."),
	("Signed Configuration Blueprint", 1, 0,
	 "The blueprint describes how each of the six modules will be configured for "
	 "Montaigne AH, has been walked through with the client, and is signed by the "
	 "project sponsor."),
	("Configured staging environment", 2, 0,
	 "All six modules configured per the signed blueprint, ZhiftPOS deployed with "
	 "offline mode working, cross-module integrations built and unit tested, and "
	 "the environment reachable by the client's testers."),
	("Migration reconciliation and Integration Test Sign-Off", 3, 0,
	 "Master data migrated with record counts and control totals agreeing to "
	 "source, opening balances reconciled to the client's closing trial balance, "
	 "and integration tests passed across all module pairs in scope."),
	("UAT Sign-Off and training registers", 4, 0,
	 "UAT scripts executed across all in-scope modules with no open S1 or S2 "
	 "defects, and a signed attendance register for every user group trained."),
	("Go-Live Readiness Checklist", 5, 2,
	 "UAT signed off, data and opening balances validated by the client, training "
	 "delivered to the initial user population, and a cutover plan agreed "
	 "including rollback provisions — SLA clause 4.3."),
	("Project Closeout Report and handover pack", 6, 0,
	 "Hypercare activity log, issue log, and a system administration handover "
	 "pack accepted by the client's three named administrators."),
]

RISKS = [
	("Client data returned late or incomplete", "High", "High",
	 "Templates issued in week 2 with named owners and dates. Weekly chase from "
	 "week 3. SLA 4.5 puts timeline shift on client delay — flag in writing the "
	 "first week a template is late, not the third."),
	("Key users unavailable for workshops or UAT", "Medium", "High",
	 "Workshop and UAT dates agreed at kick-off and put in the client's calendar. "
	 "Escalate to the project sponsor after one missed session."),
	("Opening balances not ready at cutover", "Medium", "High",
	 "Trial balance requested by week 8. Dry-run the balance load during "
	 "integration testing rather than at cutover."),
	("Offline mode behaviour at branches with poor connectivity", "Medium", "High",
	 "Test offline mode at the worst-connected branch during configuration, not "
	 "during UAT."),
	("Scope creep through the six modules", "High", "Medium",
	 "Anything outside the signed blueprint goes through the change request "
	 "procedure in SOW section 6. Record every scope call in the decision log."),
	("FIRS e-invoicing behaviour changes before go-live", "Low", "High",
	 "NGE Portal integration tested against live FIRS behaviour during "
	 "configuration and re-checked in the week before go-live."),
]

DECISIONS = [
	("Big-bang cutover across all branches, not phased", "Agreed",
	 "Statement of Work, Exhibit 1", "Montaigne AH and Xlevel",
	 "Agreed in the SOW. A phased rollout would mean running legacy and "
	 "CloudERP.One in parallel across branches, with the reconciliation burden "
	 "that implies.",
	 "Phased rollout by branch; phased by module.",
	 "All branches transact on the new system from the same date. Cutover "
	 "weekend carries more risk and needs the rollback plan agreed in advance."),
	("Six modules in scope, one legal entity", "Agreed",
	 "Statement of Work, Enterprise Scope", "Montaigne AH and Xlevel",
	 "Financial Control, Procurement, Inventory, CRM, ZhiftPOS and Fixed Assets "
	 "for one entity across unlimited branches and users.",
	 "Fewer modules in phase one with the rest later.",
	 "Anything outside these six is a change request under SOW section 6."),
	("Twelve to thirteen week schedule from 7 September 2026", "Agreed",
	 "Statement of Work, Project Schedule", "Montaigne AH and Xlevel",
	 "The SOW schedule keyed to a kick-off of Monday 7 September, baselined at "
	 "kick-off per SLA clause 4.1.",
	 "The SLA's three-phase grouping over the same twelve weeks.",
	 "This plan is the baseline. Material deviation needs written agreement from "
	 "both parties."),
]


def _room(dry):
	name = frappe.db.get_value("Client Room", {"customer": CUSTOMER}, "name")
	if name:
		print("   room exists: %s" % name)
		return name
	if dry:
		print("   would create room for %s" % CUSTOMER)
		return None
	doc = frappe.get_doc({
		"doctype": "Client Room", "customer": CUSTOMER,
		"title": "%s · General" % CUSTOMER, "status": "Active",
	})
	doc.insert(ignore_permissions=True)
	print("   room created: %s" % doc.name)
	return doc.name


@frappe.whitelist()
def build(dry_run=1):
	dry = cint(dry_run)
	if not frappe.db.exists("Customer", CUSTOMER):
		frappe.throw("Customer %r does not exist. Create it first, or tell me the "
					 "exact name on the system." % CUSTOMER)

	print("%s — Montaigne AH implementation, kick-off %s"
		  % ("DRY RUN" if dry else "BUILDING", START))
	room = _room(dry)

	pname = "CloudERP.One Implementation — Montaigne AH Ltd"
	if frappe.db.exists("Duty Project", {"project_name": pname}):
		print("   project already exists — nothing done. Delete it first to rebuild.")
		return {"ok": 0}

	proj = None
	if not dry:
		proj = frappe.get_doc({
			"doctype": "Duty Project", "project_name": pname,
			"customer": CUSTOMER, "room": room, "status": "Active",
			"target_date": PHASES[5][1],
			# The baseline is set here and never moves. Slip is measured against
			# the date agreed at kick-off, which is the only thing that makes
			# the slip figure mean anything.
			"baseline_target_date": PHASES[5][1],
			"baselined_on": frappe.utils.now_datetime(),
		})
		proj.insert(ignore_permissions=True)
		print("   project: %s (go-live %s, baselined)" % (proj.name, PHASES[5][1]))
	else:
		print("   would create project %r, go-live %s, baseline the same"
			  % (pname, PHASES[5][1]))

	ms = []
	for i, (title, end, desc) in enumerate(PHASES):
		if dry:
			print("   phase %d  %-38s ends %s" % (i + 1, title, end))
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
		if dry:
			made += 1
			continue
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
		if dry:
			dl += 1
			continue
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
				"mitigation": mit, "status": "Open",
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

	if not dry:
		frappe.db.commit()
	print("\n   %d phases · %d tasks · %d deliverables · %d risks · %d decisions"
		  % (len(PHASES), made, dl, rk, dc))
	print("   estimated effort: %d hours" % sum(t[3] for t in TASKS))
	if dry:
		print('\n   Re-run with --kwargs "{\'dry_run\': 0}" to create it.')
	return {"ok": 1, "tasks": made}
