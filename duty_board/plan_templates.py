"""Standard project plan templates — data only, no logic.

Edited from the client-approved Standard Project Task Library document.
Each entry: phase title -> list of (task title, client-facing description,
urgency, due offset in days from seed date). Offsets are absolute from
project start, per the document's definition.
"""

STANDARD_PLAN = {
	"Discovery": [
		("Kickoff meeting & project charter", "Introduce teams, confirm objectives, sponsors, escalation paths and communication cadence.", "High", 2),
		("Current process walkthrough", "Document as-is processes: sales, purchasing, inventory, accounting, approvals.", "High", 5),
		("Branch & warehouse structure mapping", "Capture all locations, warehouses, transit (GIT) flows and inter-branch movements.", "High", 6),
		("Chart of accounts review", "Review existing CoA, agree target structure, cost centers and dimensions.", "Medium", 7),
		("Item & pricing catalogue review", "Item groups, UOMs, barcodes, price lists, discounting rules and tax templates.", "High", 8),
		("Roles & permission matrix", "Who does what: role list, approval limits, segregation of duties.", "Medium", 9),
		("Integrations & devices inventory", "POS hardware, scales, printers, payment terminals, e-invoicing (NGE), banks.", "Medium", 9),
		("Scope & success criteria sign-off", "Written scope statement with success criteria — the yardstick for UAT.", "Critical", 10),
	],
	"Configuration": [
		("Company, branches & warehouses setup", "Companies, cost centers, branches and the full warehouse tree created.", "High", 14),
		("Chart of accounts & taxes configured", "CoA loaded, VAT/WHT templates, modes of payment mapped to accounts.", "High", 15),
		("Item masters & price lists configured", "Item groups, items, UOM conversions, barcodes, selling and buying price lists.", "High", 18),
		("Customers, suppliers & terms", "Customer/supplier groups, credit limits, payment terms and territories.", "Medium", 18),
		("Buying & selling workflows", "Purchase and sales cycles configured with approval workflows per the matrix.", "High", 20),
		("POS profiles & hardware setup", "ZhiftPOS profiles per branch, payment modes, receipt formats, offline mode.", "High", 21),
		("Stock rules & reorder levels", "Valuation method, negative-stock policy, transit warehouses, reorder rules.", "Medium", 21),
		("Print formats & document branding", "Invoices, receipts, delivery notes and vouchers in your brand.", "Low", 22),
		("User accounts & permissions applied", "All users created, roles assigned, permission matrix enforced and spot-tested.", "High", 23),
		("Configuration review walkthrough", "Joint walkthrough of the configured system against the agreed scope.", "Critical", 24),
	],
	"Data Migration": [
		("Migration templates issued", "Excel templates for items, customers, suppliers, balances handed over with guidance.", "High", 25),
		("Master data cleaned & validated", "Client-returned data validated: duplicates, missing UOMs, orphan groups resolved.", "High", 29),
		("Item & partner masters imported", "Items, customers and suppliers loaded and sample-checked on the live site.", "High", 30),
		("Opening stock counted & imported", "Physical count per warehouse, stock reconciliation entries posted and verified.", "Critical", 33),
		("Opening financial balances imported", "Trial balance, receivables and payables loaded and tied to the count date.", "Critical", 34),
		("Migration reconciliation sign-off", "Stock value and TB agreed to source records; variances documented and accepted.", "Critical", 35),
	],
	"Training": [
		("Training plan & environment ready", "Training site prepared with migrated data; schedule agreed per department.", "Medium", 36),
		("Sales & POS operator training", "Cashiers and floor staff: billing, returns, shift close, offline recovery.", "High", 38),
		("Purchasing & stores training", "Purchase orders, receipts, transfers, counts and reorder handling.", "High", 39),
		("Accounts team training", "Payments, reconciliation, taxes, period close and financial reports.", "High", 40),
		("Supervisor & manager training", "Approvals, dashboards, exception reports and day-end controls.", "Medium", 41),
		("Training assessment & gap session", "Short competency checks; repeat sessions booked for weak areas.", "Medium", 42),
	],
	"User Acceptance Testing": [
		("UAT scenario pack issued", "End-to-end scripts covering your real daily, weekly and month-end operations.", "High", 43),
		("Sales-to-cash cycle tested", "Quotation to invoice to payment, including POS shifts, returns and discounts.", "Critical", 45),
		("Procure-to-pay cycle tested", "PO to receipt to purchase invoice to payment, including landed costs.", "Critical", 45),
		("Inventory movements tested", "Transfers, GIT, counts, adjustments and valuation checked across branches.", "Critical", 46),
		("Period-end & reports validated", "P&L, balance sheet, stock ledger and management reports validated by your team.", "High", 47),
		("Issues resolved & retested", "All UAT findings fixed, retested and closed in the tracker.", "High", 48),
		("UAT sign-off", "Formal client acceptance that the system is ready for live operation.", "Critical", 49),
	],
	"Go-Live": [
		("Cutover plan agreed", "Sequenced cutover checklist: freeze, final counts, balance top-up, switch time.", "Critical", 50),
		("Final data top-up", "Delta transactions and final balances brought over at the freeze point.", "Critical", 52),
		("Go-live day floor support", "Consultants on-site/online at first transactions; issues resolved on the spot.", "Critical", 53),
		("Legacy system set to read-only", "Old system frozen for reference; all new entries in CloudERP.One only.", "High", 53),
		("Day-one close verified", "First day's shifts, postings and cash-up verified end-to-end.", "Critical", 54),
	],
	"Hypercare": [
		("Daily health check & issue triage", "Daily review of postings, error queues and user-reported issues.", "High", 56),
		("First week-end close supported", "Week-one close done together; recurring errors root-caused.", "High", 60),
		("First month-end close supported", "Month-end run jointly: stock valuation, reconciliations, management pack.", "Critical", 83),
		("Performance & adoption review", "Usage review per branch; retraining or config tweaks where adoption lags.", "Medium", 84),
		("Handover to support & stability sign-off", "Open items closed or scheduled; formal transition to the support SLA.", "Critical", 85),
	],
}

CRM_PLAN = {
	"Discovery": [
		("Kickoff meeting & project charter / planning", "Introduce teams, confirm objectives and communication cadence; agree lead sources, funnel stages, KPIs, current data landscape and the written scope that anchors UAT.", "High", 2),
	],
	"Configuration": [
		("Install CloudERP.One instance", "Your dedicated CloudERP.One site provisioned, secured and branded.", "High", 3),
		("Install CRM and allied modules", "CRM and supporting modules — orders, inventory, HR, accounting — installed and activated.", "High", 5),
		("Client registers with payment gateway", "Your payment gateway account opened, verified and connected for online payments and settlement.", "High", 5),
		("Email templates & WhatsApp notifications", "Standard outreach and stage-change emails/SMS/WhatsApp in your brand and voice.", "Low", 7),
		("Dashboards, reports & number cards", "Pipeline, conversion and activity dashboards for reps and leadership.", "Medium", 10),
		("User accounts & permissions applied", "Reps, team leads and managers created with correct visibility rules.", "High", 10),
		("Configuration review walkthrough", "Joint walkthrough of the configured CRM against the agreed scope.", "Critical", 12),
	],
	"Data Migration": [
		("Migration templates issued", "Templates for products, contacts, delivery agents and employees handed over with guidance.", "High", 2),
		("Delivery agents created and invited to the CRM", "All delivery agents set up with logins and invited onto the platform.", "High", 5),
		("Staff created and invited to the CRM", "Closers, media buyers and back-office staff set up with logins and invited onto the platform.", "High", 5),
		("Delivery agents onboarded", "Agents walked through order assignment, delivery status updates and remittance on the platform.", "Critical", 10),
		("Migration reconciliation sign-off", "Record counts agreed to source; acceptance recorded.", "Critical", 12),
	],
	"Training": [
		("Training plan & environment ready", "Training site with migrated data; sessions scheduled per role.", "Medium", 5),
		("Closer training", "Leads, activities, quotations, CRM Orders and mobile usage day-to-day.", "High", 8),
		("Closer manager training", "Pipeline reviews, reassignment, targets, dashboards and coaching views.", "High", 9),
		("Media buyer training", "Campaigns, segmentation and lead-source performance tracking.", "Medium", 10),
		("Finance training", "Payments, remittances, gateway settlement reconciliation and financial reports.", "High", 11),
		("Inventory training", "Stock receipt, transfers, agent stock and returns handling.", "Medium", 12),
		("HR training", "Employee records, attendance and payroll basics on the platform.", "Medium", 14),
		("Management training", "Dashboards, KPIs, approvals and oversight across all modules.", "Medium", 16),
		("Training assessment & gap session", "Competency checks; repeat sessions booked for weak areas.", "Medium", 16),
	],
	"User Acceptance Testing": [
		("UAT scenario pack issued", "Scripts from lead capture through quotation, order and handoff.", "High", 14),
		("Order to payment tested", "Order capture, confirmation, delivery assignment and payment tested end-to-end.", "Critical", 18),
		("Dashboards & reports validated", "Leadership confirms the numbers match reality and read correctly.", "High", 18),
		("Issues resolved & retested", "All UAT findings fixed, retested and closed in the tracker.", "High", 19),
		("UAT sign-off", "Formal client acceptance that the CRM is ready for live operation.", "Critical", 20),
	],
	"Go-Live": [
		("Cutover plan agreed", "Switch date, final pipeline sync and channel cut-across sequenced.", "Critical", 14),
		("Order forms switched to CRM", "All order forms and inbound channels now create orders and leads in CloudERP.One only.", "Critical", 21),
		("Go-live week floor support", "Consultants beside the sales team through the first live days.", "High", 27),
		("First pipeline review on live data", "First weekly pipeline meeting run entirely from the new CRM.", "High", 28),
	],
	"Hypercare": [
		("Daily usage & data quality checks", "Adoption per rep, duplicate leads, stalled deals reviewed daily.", "High", 32),
		("Follow-up discipline coaching", "Overdue activities and rotting deals worked with team leads.", "Medium", 32),
		("First month pipeline & KPI review", "Month-one numbers reviewed with leadership; config tuned.", "Critical", 32),
		("Handover to support & stability sign-off", "Open items closed or scheduled; formal transition to the support SLA.", "Critical", 32),
	],
}

PLAN_TYPES = {
	"standard": ("Standard CloudERP.One Implementation", STANDARD_PLAN),
	"crm": ("CRM on CloudERP.One Implementation", CRM_PLAN),
}
