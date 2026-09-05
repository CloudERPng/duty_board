"""Standard project plan templates — data only, no logic.

REBUILT as composable packs rather than monolithic plans.

WHY. The old file held two fixed plans with absolute day offsets. Three
problems: a client who bought six modules got a plan describing all of them,
nothing recorded who owned a task so client-side waiting was invisible, and
every date was absolute so the plan kept its dates when reality slipped.

HOW IT WORKS NOW.

  A plan type = a spine of seven phases + the PACKS that client actually bought.
  Tasks carry a PHASE-RELATIVE day, and each plan type defines its own phase
  windows — that is what lets one pack serve both a 21-day ecommerce build and
  an 85-day retail rollout without writing it twice.

  Every task names an OWNER: Xlevel, Client or Joint. Most implementation
  slippage is waiting on the client, and it cannot be managed while invisible.

TASK SHAPE: (title, description, urgency, phase_day, owner)

DECISIONS TAKEN, so nobody has to rediscover them:

  Big-bang cutover for retail, not phased by branch. The retail pack therefore
  carries a branch readiness checklist and an all-branch simultaneous count,
  because a big bang across many branches stands or falls on those two.

  Certification is NOT a go-live gate. Training tasks are delivery tasks.

  Ecommerce go-live REQUIRES the payment gateway. Seerbit is handled inside a
  week, so it sits on the critical path with an explicit gate in Configuration
  rather than being discovered late — if that gate is open, go-live moves, and
  the plan says so where somebody can see it.

  The first month-end close is a task. Most implementations celebrate at go-live
  and meet the real problems three weeks later, so hypercare exits on criteria —
  one clean close completed — rather than on a date.

Phase names match XLEVEL_METHOD in client_room.py and are client-facing. Do not
rename them here without changing them there.
"""

PHASES = [
	"Discovery",
	"Configuration",
	"Data Migration",
	"Training",
	"User Acceptance Testing",
	"Go-Live",
	"Hypercare",
]

OWNERS = ("Xlevel", "Client", "Joint")

# phase -> (first day, last day) from project start. Phases overlap deliberately
# in the compressed plan; that is what three weeks requires, and it only holds if
# client data lands during Configuration.
WINDOWS_21 = {
	"Discovery": (0, 3),
	"Configuration": (2, 9),
	"Data Migration": (6, 12),
	"Training": (10, 15),
	"User Acceptance Testing": (14, 18),
	"Go-Live": (18, 21),
	"Hypercare": (21, 35),
}

WINDOWS_85 = {
	"Discovery": (0, 10),
	"Configuration": (8, 26),
	"Data Migration": (20, 38),
	"Training": (34, 46),
	"User Acceptance Testing": (44, 52),
	"Go-Live": (52, 58),
	"Hypercare": (58, 90),
}


# ------------------------------------------------------------------ packs

CORE = {
	"Discovery": [
		("Kickoff meeting & project charter", "Introduce teams, confirm objectives, sponsors, escalation paths and communication cadence.", "High", 0, "Joint"),
		("Department process walkthrough", "Sit with each department and document how the business actually runs today, including the exceptions.", "High", 1, "Joint"),
		("Project team & decision-makers named", "Named client lead per workstream, and who signs off what. Nothing moves without this.", "High", 1, "Client"),
		("Scope & success criteria sign-off", "Written scope statement with success criteria \u2014 the yardstick UAT is measured against.", "Critical", 3, "Joint"),
	],
	"Configuration": [
		("Environment provisioned", "CloudERP.One site created, applications installed, access issued to the project team.", "High", 0, "Xlevel"),
		("Configuration walkthrough & sign-off", "Joint walkthrough of the configured system against the agreed scope, before data lands.", "Critical", 7, "Joint"),
	],
	"Data Migration": [
		("Migration templates issued", "Templates for every master and balance handed over with worked examples and a return date.", "High", 0, "Xlevel"),
		("Client data returned", "Completed templates returned. The commonest cause of delay on any implementation.", "Critical", 3, "Client"),
		("Data validated & queries resolved", "Duplicates, missing units, orphan categories and unmapped accounts raised and cleared.", "High", 5, "Joint"),
		("Migration reconciliation sign-off", "Stock value and trial balance agreed to source records; every variance documented and accepted in writing.", "Critical", 8, "Joint"),
	],
	"Training": [
		("Training plan & environment ready", "Training site loaded with the client's own migrated data; schedule agreed per department.", "Medium", 0, "Xlevel"),
		("Training attendance confirmed", "Named attendees released by the business for each session. The second commonest cause of delay.", "High", 1, "Client"),
		("Training completion review", "Which sessions ran, who attended, and where a repeat is needed before UAT.", "Medium", 5, "Joint"),
	],
	"User Acceptance Testing": [
		("UAT scenario pack issued", "End-to-end scripts covering the client's real daily, weekly and month-end operations.", "High", 0, "Xlevel"),
		("UAT executed by client team", "The client's own staff run the scripts on their own data. Not a demonstration by us.", "Critical", 2, "Client"),
		("Issues resolved & retested", "Every finding fixed, retested and closed in the tracker with the tester's confirmation.", "High", 4, "Xlevel"),
		("UAT sign-off", "Formal client acceptance that the system is ready for live operation.", "Critical", 5, "Client"),
	],
	"Go-Live": [
		("Cutover plan agreed", "Sequenced checklist: freeze point, final counts, balance top-up, switch time, fallback position.", "Critical", 0, "Joint"),
		("Cutover rehearsal", "Dry run of the cutover sequence against a copy. Finds the forgotten step while it is still cheap.", "High", 1, "Xlevel"),
		("Backup & restore drill", "A backup taken and restored to a test site, proving the copy is real before it is needed.", "Critical", 1, "Xlevel"),
		("Freeze & final data top-up", "Legacy system frozen, delta transactions and closing balances brought over at the freeze point.", "Critical", 2, "Joint"),
		("Go-live day support", "Consultants present at the first live transactions; issues resolved on the spot.", "Critical", 3, "Xlevel"),
		("Go-live confirmed by client", "Client confirms the system is their system of record from this date.", "Critical", 3, "Client"),
	],
	"Hypercare": [
		("Daily check-in \u2014 week one", "Short daily call covering what broke, what is unclear and what needs a fix today.", "High", 1, "Joint"),
		("Issue log reviewed weekly", "Open issues by severity and age, with owners and dates, reviewed with the client lead.", "High", 5, "Joint"),
		("First month-end close supported", "The client's own team closes the month with us present. The real test of an implementation, not go-live day.", "Critical", 20, "Joint"),
		("Hypercare exit review", "Exit on criteria rather than a date: one clean close completed, open issues below the agreed level, handover pack accepted.", "Critical", 30, "Joint"),
	],
}

ACCOUNTING = {
	"Discovery": [
		("Chart of accounts review", "Review the existing chart, agree the target structure, cost centres and any dimensions.", "High", 2, "Joint"),
		("Fiscal year & accounting policy confirmed", "Statutory year end, valuation method, and the policy decisions the accountant owns.", "High", 2, "Client"),
		("Tax treatment ruling", "VAT status, WHT categories, exempt and standard-rated item classes \u2014 confirmed by the accountant, not assumed.", "High", 2, "Client"),
	],
	"Configuration": [
		("Company, cost centres & fiscal years", "Company record, cost centre tree, and the fiscal year created ahead of need rather than on the day it fails.", "High", 1, "Xlevel"),
		("Chart of accounts loaded", "Target chart built, account types set at creation, and the posting map verified on one live document of each kind.", "High", 2, "Xlevel"),
		("Tax templates & modes of payment", "VAT and WHT templates, item tax categories, and every payment mode mapped to its account.", "High", 3, "Xlevel"),
		("Accounts Settings walk", "Each field read as the policy question it is, with the answer and its reason recorded.", "Medium", 4, "Joint"),
		("Print formats & letterhead", "Invoices, receipts and vouchers carrying the legally required content, confirmed by the accountant.", "Medium", 5, "Xlevel"),
	],
	"Data Migration": [
		("Opening trial balance loaded", "Trial balance loaded and tied to the agreed cut-off date.", "Critical", 5, "Xlevel"),
		("Open receivables & payables loaded", "Per party, per open invoice, with real dates and due dates. Never as one balance per party.", "Critical", 5, "Xlevel"),
		("Bank balances & reconciliation position", "Opening bank balances with any uncleared items identified at the cut-off.", "High", 6, "Joint"),
	],
	"Training": [
		("Accounts team training", "Invoicing, payments and allocation, bank reconciliation, the tax registers and period close.", "High", 2, "Xlevel"),
		("Cash & control monitoring training", "The daily and weekly reads: unallocated payments, aged receivables, cash position, exception reports.", "High", 3, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Sales-to-cash cycle tested", "Order to invoice to receipt to allocation, including credit notes and returns.", "Critical", 2, "Client"),
		("Procure-to-pay cycle tested", "Requisition to order to receipt to invoice to payment, including a three-way match exception.", "Critical", 2, "Client"),
		("Period-end reports validated", "P&L, balance sheet, trial balance and tax registers validated by the client's accountant.", "High", 3, "Client"),
	],
	"Go-Live": [
		("Opening balances final top-up", "Movements between the migration cut-off and the freeze point brought over and re-tied.", "Critical", 2, "Xlevel"),
	],
	"Hypercare": [
		("First VAT return prepared from the system", "The return built from the system's own registers rather than from a spreadsheet beside it.", "High", 22, "Joint"),
	],
}

INVENTORY = {
	"Discovery": [
		("Branch & warehouse structure mapping", "Every location, warehouse, transit flow and inter-branch movement captured on paper before anything is created.", "High", 2, "Joint"),
		("Item catalogue & UOM review", "Item groups, brands, categories, units and conversions, barcodes and identity requirements.", "High", 3, "Joint"),
		("Valuation & stock policy decisions", "Valuation method, negative stock posture, batch and serial requirements per item class.", "High", 3, "Client"),
	],
	"Configuration": [
		("Warehouse tree built", "Warehouse tree created to the agreed design, with transit warehouses and warehouse types.", "High", 2, "Xlevel"),
		("Item groups, brands & categories", "The reporting trees created before items are loaded, so nothing lands ungrouped.", "High", 2, "Xlevel"),
		("Stock settings & identity flags", "Stock settings walked and recorded; batch and serial flags applied per the control register rather than per item.", "High", 3, "Xlevel"),
		("Reorder levels & auto-replenishment", "Levels set from data where it exists, and automation enabled only where the levels were computed rather than guessed.", "Medium", 6, "Joint"),
	],
	"Data Migration": [
		("Item data cleanup & categorisation", "Duplicates merged, units resolved, every item assigned to its group, brand and category. Client-side and usually the long pole.", "Critical", 2, "Client"),
		("Item masters imported & sampled", "Items loaded and a sample checked line by line on the live site against source.", "High", 4, "Xlevel"),
		("Opening stock counted", "Physical count per warehouse at the agreed cut-off, counted blind and signed.", "Critical", 6, "Client"),
		("Opening stock imported & valued", "Counts posted with opening valuations checked against recent purchase documents before submission.", "Critical", 7, "Xlevel"),
	],
	"Training": [
		("Inventory team training", "Receiving, transfers, counts, adjustments, dates and rotation, and the reports that expose drift.", "High", 2, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Stock movements tested", "Receipts, issues, transfers and transit movements tested across branches with identity captured.", "Critical", 2, "Client"),
		("Counts & adjustments tested", "A count performed and reconciled end to end, including the variance investigation path.", "High", 3, "Client"),
	],
	"Go-Live": [
		("Final stock count & top-up", "Movements since the migration count captured and posted at the freeze point.", "Critical", 2, "Joint"),
	],
	"Hypercare": [
		("First cycle count reviewed", "First post-go-live count run by the client's team, with variances worked rather than adjusted away.", "High", 18, "Joint"),
	],
}

PROCUREMENT = {
	"Discovery": [
		("Supplier list & terms review", "Suppliers, groups, currencies, payment terms and any standing arrangements.", "Medium", 3, "Joint"),
		("Approval limits & buying authority", "Who may raise, approve and release, and at what values.", "High", 3, "Client"),
	],
	"Configuration": [
		("Supplier groups & buying price lists", "Supplier tree, buying price lists per currency, and default terms per group.", "Medium", 4, "Xlevel"),
		("Purchase workflow & approval limits", "Requisition, order and invoice workflow configured to the agreed authority matrix.", "High", 5, "Xlevel"),
		("Three-way match settings", "Order, receipt and invoice matching enforced, with the exception route defined for what fails.", "High", 5, "Xlevel"),
	],
	"Data Migration": [
		("Supplier masters imported", "Suppliers loaded with terms, currency and bank details verified through a known channel.", "High", 4, "Xlevel"),
		("Open purchase orders loaded", "Outstanding orders brought over with their remaining quantities and dates.", "Medium", 6, "Xlevel"),
	],
	"Training": [
		("Procurement team training", "Requests, quotation cycles, orders, receiving discipline and the matching exceptions.", "High", 3, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Procure-to-pay tested with exceptions", "Full cycle including a short delivery and an over-billed invoice, not only the clean path.", "Critical", 3, "Client"),
	],
	"Hypercare": [
		("First supplier payment run reviewed", "First run prepared by the client, reviewed for allocation, terms and the separation of prepare and release.", "High", 12, "Joint"),
	],
}

RETAIL_POS = {
	"Discovery": [
		("Branch list & hardware inventory", "Every branch, its terminals, printers, scanners, drawers and network position recorded.", "High", 4, "Joint"),
		("Payment methods & terminal mapping", "Every tender type the branches accept, and how each maps to an account.", "High", 4, "Joint"),
	],
	"Configuration": [
		("POS profiles per branch", "A ZhiftPOS profile per branch with its warehouse, cost centre, payment modes and price list.", "High", 6, "Xlevel"),
		("ZhiftPOS installed at all branches", "Installed, connected and smoke-tested at every branch, not only the pilot.", "Critical", 8, "Xlevel"),
		("Receipt formats & offline behaviour", "Receipt layout per brand requirements, and offline mode tested by disconnecting a terminal deliberately.", "High", 9, "Xlevel"),
		("Cashier users & till permissions", "Individual logins for every cashier \u2014 no shared accounts \u2014 with permissions scoped to their branch.", "High", 9, "Xlevel"),
	],
	"Training": [
		("Train the trainers", "Branch supervisors trained to standard so they can train and correct their own cashiers.", "High", 1, "Xlevel"),
		("Cashier training per branch", "Billing, returns, voids, shift open and close, and what to do when the connection drops.", "High", 4, "Xlevel"),
		("Supervisor & branch manager training", "Approvals, shift review, exception reports, cash-up and day-end controls.", "High", 6, "Xlevel"),
	],
	"User Acceptance Testing": [
		("POS shift cycle tested", "Open, sell, refund, void, cash-up and close, with the variance path exercised.", "Critical", 3, "Client"),
		("Offline recovery tested", "A terminal disconnected mid-shift and recovered, with transactions reconciled afterwards.", "Critical", 4, "Client"),
	],
	"Go-Live": [
		("Branch readiness checklist signed", "Per branch: hardware working, users created, stock counted, staff trained, tenders tested. Big bang stands or falls here.", "Critical", 1, "Joint"),
		("All-branch simultaneous count", "Every branch counted on the same night at the freeze point. The largest logistical task in a big-bang retail cutover.", "Critical", 2, "Client"),
		("All branches live", "Every branch trading on ZhiftPOS from opening, with support allocated per branch for day one.", "Critical", 3, "Xlevel"),
	],
	"Hypercare": [
		("Per-branch first-week shift review", "Every branch's first week of shift closes reviewed for variances, voids and discount patterns.", "High", 8, "Joint"),
	],
}

CRM_SALES = {
	"Discovery": [
		("Sales process & pipeline review", "How opportunities arrive, who owns them, and the stages the business actually uses.", "Medium", 2, "Joint"),
		("Customer segmentation & pricing rules", "Customer groups, territories, price lists and the discount authority ladder.", "High", 3, "Joint"),
	],
	"Configuration": [
		("Customer groups, territories & price lists", "The two trees built independently, and selling price lists per group.", "High", 3, "Xlevel"),
		("Pricing rules & discount governance", "Quantity breaks and class discounts configured, with the deviation ladder recorded.", "Medium", 4, "Xlevel"),
		("Sales workflow & CRM dashboards", "Quotation to order to delivery to invoice, with the pipeline views the sales lead will actually read.", "Medium", 5, "Xlevel"),
	],
	"Data Migration": [
		("Customer masters imported", "Customers loaded with groups, terms, credit limits and tax identifiers.", "High", 4, "Xlevel"),
		("Open orders & quotations loaded", "Outstanding commitments brought over with their schedules.", "Medium", 6, "Xlevel"),
	],
	"Training": [
		("Sales team training", "Quotations, orders, the pipeline, and the reads that show what is actually happening.", "High", 3, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Quote-to-invoice cycle tested", "Quotation through order, delivery and invoice, including a partial delivery and a return.", "Critical", 2, "Client"),
	],
}

ECOM_CRM = {
	"Discovery": [
		("Business model & funnel walkthrough", "How this operation differs from the others: channels, offers, closer model, agent network, remittance flow.", "High", 1, "Joint"),
		("Delivery agent network review", "Coverage, agent types, remittance arrangements and the cash flow from agent back to business.", "High", 2, "Joint"),
	],
	"Configuration": [
		("ZhiftCRM installed & configured", "Installed and configured to the agreed funnel, statuses and closer workflow.", "Critical", 1, "Xlevel"),
		("Order form templates built", "Order forms built per offer, ready for installation on the client's WordPress properties.", "High", 3, "Xlevel"),
		("Emailing system configured", "Sending domain, records and deliverability verified \u2014 not a personal mailbox.", "Medium", 4, "Xlevel"),
		("Meta Business Platform onboarding", "Client onboarded onto our Meta business platform for WhatsApp messaging, with numbers verified.", "High", 4, "Joint"),
		("Agent app & web access configured", "Agent application configured, test accounts created and a delivery cycle walked end to end.", "High", 5, "Xlevel"),
		("Back-office workspaces & reporting", "Core ERPNext workspaces and reports curated per job family, so each team sees its own work.", "Medium", 6, "Xlevel"),
	],
	"Data Migration": [
		("Staff details supplied & uploaded", "All staff including media buyers, with roles matching how they actually operate.", "High", 2, "Client"),
		("Product details supplied & uploaded", "Products with brand and category set up first, so nothing lands ungrouped.", "Critical", 3, "Client"),
		("Delivery agent details supplied & uploaded", "Agent records with coverage areas, contact details and remittance arrangements.", "High", 4, "Client"),
		("User profiles aligned to operations", "Every profile checked against how that person actually works, not against a generic role list.", "High", 6, "Xlevel"),
	],
	"Training": [
		("Closer & closer manager training", "The frontend end to end: lead handling, order creation, follow-up and the closer dashboards.", "Critical", 1, "Xlevel"),
		("Media buyer training \u2014 frontend", "How buying activity appears in the system and what the numbers mean.", "High", 2, "Xlevel"),
		("Media buyer training \u2014 order forms", "Order form creation and installation on WordPress, done by them rather than for them.", "High", 3, "Xlevel"),
		("Agent WhatsApp group & onboarding", "Group created, agents onboarded and their first credentials issued.", "High", 3, "Joint"),
		("Delivery agent training", "The agent app and web application: accepting, delivering, remitting and reporting exceptions.", "Critical", 4, "Xlevel"),
		("Logistics team training", "Dispatch, assignment, tracking and the exception paths when a delivery fails.", "High", 4, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Order-to-delivery-to-cash tested", "Lead through closer, order, dispatch, agent delivery, remittance and posting \u2014 the whole chain on real data.", "Critical", 2, "Client"),
		("Agent remittance & reconciliation tested", "Agent collections reconciled to orders and to cash received, including a failed delivery.", "Critical", 3, "Client"),
	],
	"Go-Live": [
		("Agent network onboarded & live", "All agents onboarded, credentialled and confirmed working before the first live order is dispatched.", "Critical", 2, "Joint"),
	],
	"Hypercare": [
		("Closer performance review \u2014 week one", "First week of closer activity reviewed: conversion, follow-up discipline and where coaching is needed.", "High", 8, "Joint"),
		("Agent remittance review \u2014 week one", "First week of remittances reconciled, with any gap chased while it is still small.", "Critical", 8, "Joint"),
	],
}

HR = {
	"Discovery": [
		("Organisation structure & roles", "Departments, designations, branches and the reporting structure as it actually operates.", "Medium", 3, "Joint"),
		("Leave & HR policy review", "Leave types, entitlements, carry-forward rules and approval routing, confirmed in writing.", "High", 3, "Client"),
	],
	"Configuration": [
		("Departments, designations & branches", "The organisational masters built, with leave approvers set per department.", "Medium", 5, "Xlevel"),
		("Holiday lists & shift types", "Holiday lists per working pattern for the current year, and shift types where attendance is tracked.", "Medium", 5, "Xlevel"),
		("Leave types, policy & allocations", "Leave types built from the written policy rather than from practice, then the policy and its assignments.", "High", 6, "Xlevel"),
		("HR Settings walk", "Each setting decided and recorded with its reason, including retirement age and naming.", "Low", 6, "Joint"),
	],
	"Data Migration": [
		("Employee data supplied", "Full records including joining dates from contracts, states of residence and bank details.", "Critical", 3, "Client"),
		("Employee masters imported & verified", "Records loaded and the fields payroll depends on verified before the first run.", "High", 5, "Xlevel"),
		("Opening leave balances loaded", "Balances as at the cut-off, agreed with each employee where the business wants that.", "Medium", 6, "Joint"),
	],
	"Training": [
		("HR team training", "The employee lifecycle, leave, attendance and the register hygiene reads.", "High", 3, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Joiner, leave & exit tested", "A full lifecycle exercised end to end including an approved leave application and a leaver.", "High", 3, "Client"),
	],
}

PAYROLL = {
	"Discovery": [
		("Salary structure review", "Package shape, components, and which are earnings, deductions and employer costs.", "High", 3, "Joint"),
		("Statutory applicability ruling", "PAYE states of residence, pension and PFAs, NHF and any levies \u2014 confirmed by the accountant with rates from their current table.", "Critical", 3, "Client"),
	],
	"Configuration": [
		("Salary components configured", "Components built with stable abbreviations, correct types and their ledger accounts.", "High", 6, "Xlevel"),
		("Income tax slab & statutory components", "Slab entered from the accountant's current computation sheet and read back line by line before use.", "Critical", 7, "Xlevel"),
		("Salary structures & assignments", "Structures per package rather than per person, with assignments carrying each employee's base.", "High", 7, "Xlevel"),
		("Statutory payable accounts wired", "Every custody payable created and typed, and the posting map verified on a preview slip.", "High", 8, "Xlevel"),
	],
	"Data Migration": [
		("Assignments loaded & previewed", "Every employee's structure and base loaded, with a preview slip read against their offer letter.", "Critical", 6, "Xlevel"),
		("Year-to-date figures loaded", "Where go-live is mid-year, YTD taxable income and PAYE withheld brought over.", "High", 7, "Joint"),
	],
	"Training": [
		("Payroll & accounts payroll training", "The run procedure, the reconciliations inside it, the registers and the remittance workflow.", "Critical", 4, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Parallel payroll run", "A full run computed in the system and compared line by line against the last manually prepared month. Every difference explained.", "Critical", 2, "Joint"),
	],
	"Go-Live": [
		("First live payroll run", "First run executed by the client's team with us present, including the headcount reconciliation.", "Critical", 3, "Joint"),
	],
	"Hypercare": [
		("First remittance cycle supported", "Schedules produced from the register, tied to the custody accounts, and filed on time.", "Critical", 15, "Joint"),
	],
}

NGE = {
	"Discovery": [
		("FIRS e-invoicing obligation assessed", "Turnover band, applicable deadline and what the business must transmit, confirmed with the accountant.", "High", 2, "Joint"),
	],
	"Configuration": [
		("NGE Portal provisioned", "Middleware provisioned and connected to the site.", "High", 5, "Xlevel"),
		("TIN, credentials & field mapping", "Taxpayer identifiers registered and every required invoice field mapped and populated.", "High", 6, "Joint"),
		("Transmission test completed", "Test invoices transmitted and acknowledged before any live document depends on it.", "Critical", 8, "Xlevel"),
	],
	"User Acceptance Testing": [
		("Live transmission validated", "Invoices raised in UAT transmit and acknowledge end to end, with the failure path exercised.", "Critical", 3, "Client"),
	],
	"Hypercare": [
		("First month transmission reconciled", "Transmitted invoices reconciled to the sales register, so any gap is found by the business rather than by the authority.", "Critical", 22, "Joint"),
	],
}

PAYMENTS = {
	"Discovery": [
		("Seerbit registration initiated", "Started at contract signature rather than at kickoff. Ecommerce go-live depends on this and its clock is not ours.", "Critical", 0, "Client"),
		("KYC documents submitted", "Full KYC pack submitted. Incomplete documents are the usual reason this stalls.", "Critical", 1, "Client"),
	],
	"Configuration": [
		("KYC approved", "Approval received. If this is not clear by the gate below, go-live moves \u2014 flag it the day it slips, not later.", "Critical", 3, "Client"),
		("Transaction limit increased above default", "Limit raised from the NGN500,000 default to the agreed ceiling.", "Critical", 4, "Client"),
		("Gateway configured for all operating countries", "Setup completed for every country the business trades in, not only the primary one.", "High", 5, "Xlevel"),
		("Test transaction settled end to end", "A real transaction taken, settled and reconciled into the ledger.", "Critical", 6, "Xlevel"),
		("PAYMENT GATEWAY READY \u2014 GO-LIVE GATE", "Gateway confirmed live and settling. Ecommerce go-live cannot proceed without this; if it is open, the go-live date moves.", "Critical", 7, "Joint"),
	],
	"User Acceptance Testing": [
		("Payment flow tested with reconciliation", "Customer payment through settlement to ledger, including a failed and a refunded transaction.", "Critical", 3, "Client"),
	],
	"Hypercare": [
		("First settlement cycle reconciled", "Gateway settlements reconciled to orders and to the bank, with any difference chased in week one.", "High", 8, "Joint"),
	],
}

SYSADMIN = {
	"Discovery": [
		("User list & permission matrix", "Every user, their job family, and who may do what \u2014 including approval limits and segregation of duties.", "High", 4, "Joint"),
	],
	"Configuration": [
		("Users created & roles applied", "Individual accounts for every person, roles by job family, and permissions spot-tested rather than assumed.", "High", 6, "Xlevel"),
		("Privileged access restricted", "System Manager held by two named people, and two-factor on the privileged and money-handling accounts.", "High", 7, "Xlevel"),
		("Backup arrangement confirmed in writing", "Schedule, retention, off-site copy, and the two numbers: how much work a restore would lose and how long it would take.", "High", 7, "Joint"),
	],
	"Training": [
		("Client system administrator handover", "The client's named administrator trained on users, permissions, backups, the change procedure and the health reads.", "High", 5, "Xlevel"),
	],
	"Hypercare": [
		("Administration handover pack issued", "Control register, customisation register, calendar of routine checks, and the escalation path on paper.", "High", 25, "Xlevel"),
	],
}

PACKS = {
	"core": ("Project spine and gates", CORE),
	"accounting": ("Accounting & Finance", ACCOUNTING),
	"inventory": ("Inventory & Warehousing", INVENTORY),
	"procurement": ("Procurement", PROCUREMENT),
	"retail_pos": ("Retail & ZhiftPOS", RETAIL_POS),
	"crm_sales": ("Selling & CRM", CRM_SALES),
	"ecom_crm": ("Ecommerce CRM — closers, media buyers, agents", ECOM_CRM),
	"hr": ("HR", HR),
	"payroll": ("Payroll", PAYROLL),
	"nge": ("FIRS e-invoicing (NGE Portal)", NGE),
	"payments": ("Payment gateway (Seerbit)", PAYMENTS),
	"sysadmin": ("System administration & handover", SYSADMIN),
}

PLAN_TYPES = {
	"ecommerce": (
		"Ecommerce CRM Implementation",
		["core", "ecom_crm", "payments", "accounting", "inventory", "crm_sales",
		 "hr", "payroll", "sysadmin"],
		WINDOWS_21,
	),
	"retail": (
		"Multi-Branch Retail Implementation",
		["core", "accounting", "inventory", "procurement", "retail_pos",
		 "crm_sales", "hr", "payroll", "nge", "sysadmin"],
		WINDOWS_85,
	),
	"standard": (
		"Standard CloudERP.One Implementation",
		["core", "accounting", "inventory", "procurement", "crm_sales",
		 "hr", "payroll", "sysadmin"],
		WINDOWS_85,
	),
}


def build_plan(plan_type):
	"""Compose a plan type's packs into {phase: [(title, desc, urgency, offset, owner)]}.

	Phase-relative days are mapped into that plan type's window and clamped to it,
	so a pack written once serves both timelines. Sorted by day within each phase.
	"""
	if plan_type not in PLAN_TYPES:
		return {}
	_label, pack_keys, windows = PLAN_TYPES[plan_type]
	out = {phase: [] for phase in PHASES}
	for key in pack_keys:
		pack = PACKS[key][1]
		for phase, tasks in pack.items():
			if phase not in out:
				continue
			start, end = windows[phase]
			for title, desc, urgency, rel_day, owner in tasks:
				out[phase].append((title, desc, urgency, min(start + rel_day, end), owner))
	for phase in out:
		out[phase].sort(key=lambda t: t[3])
	return out


def plan_labels():
	"""(key, label) for every plan type, for pickers."""
	return [(k, v[0]) for k, v in PLAN_TYPES.items()]


def plan_packs(plan_type):
	"""(key, label) of the packs a plan type includes — these are the scope lines."""
	if plan_type not in PLAN_TYPES:
		return []
	return [(k, PACKS[k][0]) for k in PLAN_TYPES[plan_type][1]]
