# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Seed the default UAT template banks for ZhiftERP, ZhiftPOS and ZhiftCRM.

Idempotent: ensures the Duty Product rows exist, creates each template only
if absent (existing templates are never overwritten — managers own them once
seeded). Run:

    bench --site xlevel.clouderp.one execute duty_board.uat_seed_templates.seed_templates
"""

import frappe

C = lambda s, t, st, e: {"section": s, "title": t, "steps": st, "expected": e}

BANKS = {
	"ZhiftPOS": [
		C("Access & Setup", "Cashier can log in and open the POS",
		  "1. Log in with a cashier account\n2. Open the POS screen for your outlet",
		  "POS opens against the correct outlet and warehouse; only permitted screens are visible to the cashier role."),
		C("Access & Setup", "Opening a shift with a float",
		  "1. Start a new POS shift\n2. Enter the opening cash float counted in the drawer",
		  "Shift opens recording the float, cashier and time; sales cannot be made without an open shift."),
		C("Items & Pricing", "Find an item by barcode scan",
		  "1. Scan any shelf item's barcode at the till",
		  "The correct item appears immediately with the agreed selling price and available quantity."),
		C("Items & Pricing", "Find an item by name search",
		  "1. Type part of an item's name in the search box",
		  "Matching items list quickly; selecting one adds it to the cart at the correct price."),
		C("Items & Pricing", "Price list is respected",
		  "1. Add an item that has a special/outlet price\n2. Compare the cart price to the agreed price list",
		  "The cart uses the outlet's price list, not the standard rate."),
		C("Sales at the Till", "Complete a simple cash sale",
		  "1. Add 2–3 items to the cart\n2. Take cash payment and complete\n3. Print/see the receipt",
		  "Sale completes, receipt shows outlet details and VAT correctly, stock reduces for each item sold."),
		C("Sales at the Till", "Discount within the allowed limit",
		  "1. Apply a discount within the cashier's permitted limit\n2. Attempt a discount above the limit",
		  "The permitted discount applies; the excessive discount is refused or demands supervisor authorisation."),
		C("Payments", "Split payment (cash + transfer/POS terminal)",
		  "1. Ring up a sale\n2. Pay part in cash and the balance by transfer/card",
		  "Both payment lines record against the invoice; totals reconcile to the invoice amount exactly."),
		C("Payments", "Bank transfer sale is traceable",
		  "1. Complete a sale paid fully by transfer with a reference",
		  "The payment records the mode and reference so the back office can match it to the bank statement."),
		C("Returns & Refunds", "Return an item against a receipt",
		  "1. Take a sold item back using its receipt\n2. Process the return/refund",
		  "A credit/return is created against the original invoice, stock increases back, and the refund mode is recorded."),
		C("Shift & Day Close", "Close the shift and reconcile cash",
		  "1. Close the running shift\n2. Enter the counted drawer cash\n3. Review the closing summary",
		  "The closing shows expected vs counted by payment mode, highlights any variance, and locks the shift."),
		C("Shift & Day Close", "Sales cannot post to a closed shift",
		  "1. After closing, attempt another sale without opening a new shift",
		  "The sale is refused until a new shift is opened."),
		C("Stock", "Stock reduces only from the outlet warehouse",
		  "1. Note an item's quantity in the outlet warehouse\n2. Sell one unit\n3. Re-check the quantity",
		  "Quantity reduces by exactly the sold amount in the outlet warehouse and nowhere else."),
		C("Stock", "Receiving stock into the outlet",
		  "1. Receive a transfer/purchase into the outlet as trained\n2. Sell one of the received items",
		  "Received quantities appear at the till immediately and sell normally."),
		C("Reports", "Daily sales report matches the tills",
		  "1. After test sales, open the daily sales report for the outlet",
		  "Totals by cashier and payment mode agree with the shift closings for the day."),
	],
	"ZhiftCRM": [
		C("Access & Roles", "Each role sees only its own workspace",
		  "1. Log in as a closer, then as a dispatch user\n2. Compare the screens and records visible",
		  "Closers see their assigned leads/orders; dispatch sees orders ready for delivery; neither sees the other's admin screens."),
		C("Leads & Capture", "A lead from the ad form lands in the CRM",
		  "1. Submit a test entry on the connected ad/landing form\n2. Check the CRM within a few minutes",
		  "The lead appears with name, phone and product interest, unassigned or routed per the agreed rule."),
		C("Leads & Capture", "Manual lead entry",
		  "1. Create a lead by hand for a phone-in customer",
		  "The lead saves with source recorded and enters the same follow-up flow as form leads."),
		C("Orders", "Convert a lead to an order",
		  "1. Open a lead as a closer\n2. Create the order with product, quantity, price and delivery address",
		  "A CRM Order is created linked to the lead, priced per the product setup, and appears in the confirmation queue."),
		C("Orders", "Duplicate phone number is flagged",
		  "1. Create a second lead/order using a phone number that already exists",
		  "The system flags the duplicate so the team sees the customer's history before proceeding."),
		C("Confirmation & Closers", "Closer confirms an order",
		  "1. As the assigned closer, call-confirm the test order and mark it confirmed",
		  "Order status moves to confirmed with the closer and time recorded; it becomes visible to dispatch."),
		C("Confirmation & Closers", "Reassigning a lead/order",
		  "1. As a manager, reassign the test order to a different closer",
		  "The new closer sees it in their queue; the old closer no longer does; the change is recorded."),
		C("Dispatch & Delivery", "Assign a delivery agent",
		  "1. As dispatch, assign the confirmed order to a delivery agent with a delivery date",
		  "The agent is recorded on the order; it appears on the agent's delivery list for that date."),
		C("Dispatch & Delivery", "Mark an order delivered",
		  "1. Record the test order as delivered with the amount collected",
		  "Status moves to delivered; the collected amount is captured for payment verification."),
		C("Dispatch & Delivery", "Failed delivery / customer unavailable",
		  "1. Record a delivery attempt as failed with a reason",
		  "The order returns to the follow-up flow with the failure reason visible, not lost."),
		C("Payments & Verification", "Verify an agent's remittance",
		  "1. As accounts, review the agent's delivered orders for the day\n2. Match collected amounts to the remittance/transfer received",
		  "Delivered totals per agent are listed for the day and can be marked verified; shortfalls stand out."),
		C("Returns", "Process a customer return",
		  "1. Record a return against a delivered test order",
		  "The return is captured with reason; stock/financial effects follow the agreed policy and reports reflect it."),
		C("Reports", "Closer performance for the day",
		  "1. Open the closer performance view after the test flow",
		  "Assigned, confirmed and delivered counts per closer match what was actually done in the tests."),
		C("Reports", "Order pipeline is truthful",
		  "1. Open the pipeline/status board",
		  "Every test order sits in the correct column for its real status — nothing stuck or double-counted."),
	],
	"ZhiftERP": [
		C("Access & Masters", "Users log in with correct role limits",
		  "1. Log in as a sales user and as an accounts user\n2. Try to open a screen outside each role",
		  "Each user reaches their own workspaces; out-of-role screens are refused."),
		C("Access & Masters", "Customer master is complete",
		  "1. Open 3 migrated customers at random\n2. Check name, contact, address, credit terms",
		  "Migrated customer records are accurate and complete enough to transact without editing."),
		C("Access & Masters", "Item master is complete",
		  "1. Open 3 migrated items at random\n2. Check UOM, price, tax template, warehouse defaults",
		  "Items carry correct units, prices and VAT settings; no test item transacts with a wrong rate."),
		C("Sales Cycle", "Quotation → Sales Order",
		  "1. Create a quotation for a customer\n2. Convert it to a Sales Order",
		  "The order carries the quotation's items and prices without retyping."),
		C("Sales Cycle", "Delivery Note reduces stock",
		  "1. Deliver against the Sales Order\n2. Check the item's stock level",
		  "Stock reduces from the correct warehouse by the delivered quantity."),
		C("Sales Cycle", "Sales Invoice with VAT",
		  "1. Invoice the delivery\n2. Review the tax lines and totals",
		  "VAT calculates at the correct rate on the correct base; invoice print shows the company's required details."),
		C("Sales Cycle", "Customer payment settles the invoice",
		  "1. Record the customer's payment against the invoice",
		  "The invoice shows paid; the customer's outstanding balance reduces accordingly."),
		C("Purchase Cycle", "Purchase Order → Receipt → Purchase Invoice",
		  "1. Raise a PO on a supplier\n2. Receive the goods\n3. Book the purchase invoice",
		  "Stock increases on receipt; the supplier invoice matches the PO and receipt without manual correction."),
		C("Purchase Cycle", "Supplier payment",
		  "1. Pay the supplier invoice (full or part)",
		  "Supplier outstanding reflects the payment; the bank/cash account used is correct."),
		C("Stock", "Stock transfer between warehouses",
		  "1. Transfer quantity of an item from one warehouse to another\n2. Check both warehouses",
		  "Source reduces and destination increases by the same quantity, valued correctly."),
		C("Stock", "Stock reconciliation adjusts to the physical count",
		  "1. Enter a reconciliation for one item with a deliberate difference",
		  "System quantity adjusts to the counted figure and the difference posts to the agreed adjustment account."),
		C("Accounting", "Journal entry posts correctly",
		  "1. Post a simple journal (e.g. expense accrual)\n2. Open the two ledgers touched",
		  "Debits and credits land on the intended accounts and period."),
		C("Accounting", "Bank entries can be matched",
		  "1. Record a bank payment and a receipt\n2. Review the bank ledger against the statement",
		  "Bank ledger lines carry references that make statement matching practical."),
		C("Accounting", "Trial balance balances after the test flow",
		  "1. Run the Trial Balance for the test period",
		  "Debits equal credits; the test transactions appear under the expected heads."),
		C("Reports & Close", "Receivables and payables are truthful",
		  "1. Run Accounts Receivable and Accounts Payable summaries",
		  "Balances agree with the invoices and payments entered during testing — nothing missing, nothing doubled."),
		C("Reports & Close", "Stock balance report matches reality",
		  "1. Run the stock balance for the test items",
		  "Quantities and values reflect every movement made during the tests."),
	],
}


def seed_templates():
	made, skipped = [], []
	for product, cases in BANKS.items():
		if not frappe.db.exists("Duty Product", product):
			frappe.get_doc(
				{"doctype": "Duty Product", "title": product, "active": 1, "sort_order": 0}
			).insert(ignore_permissions=True)
		if frappe.db.exists("Duty UAT Template", product):
			skipped.append(product)
			continue
		doc = frappe.get_doc({"doctype": "Duty UAT Template", "product": product, "active": 1})
		for c in cases:
			doc.append("cases", c)
		doc.insert(ignore_permissions=True)
		made.append(f"{product} ({len(cases)} cases)")
	frappe.db.commit()
	print("Created:", ", ".join(made) or "none")
	if skipped:
		print("Left untouched (already exist):", ", ".join(skipped))
