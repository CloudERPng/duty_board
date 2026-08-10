#!/usr/bin/env python3
"""Duty Board v3.82.0 — ZhiftERP Sales Professional academy.

Creates the full selling curriculum (quotation -> delivery -> invoicing,
customer management, taxes, pricing) as 6 PROCTORED training modules
(timed 60s/question, 10 served from 12-question banks), 24 lessons, and
the "ZhiftERP Sales Professional" certification track (ZERP-SALESPRO).

Writes two repo files and bumps the version:
- duty_board/academy_sales_pro_data.json  (content)
- duty_board/academy_seed_sales_pro.py    (idempotent seeder)

Deploy: apply -> commit -> then seed the site:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track

No schema, no build needed for the seed itself. Anchored, idempotent.
Requires v3.81.1. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_sales_pro_data.json"
SEED_PATH = "duty_board/academy_seed_sales_pro.py"
CHECK_ONLY = "--check" in sys.argv

L = lambda t, est, html: {"title": t, "est": est, "html": html}
Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

DATA = {
"customers": {
"title": "Selling 1 — Customers & Selling Foundations",
"desc": "The customer master done right: groups, territories, contacts and addresses, credit limits, and the Selling Settings that shape every document after it.",
"lessons": [
L("The Customer master", "5", "<p>Every selling document in ZhiftERP hangs off a <b>Customer</b>. Create one from <b>Selling &gt; Customer</b>: the name, <b>Customer Group</b>, and <b>Territory</b> are the three fields that drive reporting later — group answers <i>what kind</i> of customer (Retail, Pharmacy, Distributor), territory answers <i>where</i> (Lagos Mainland, Abuja, South-West).</p><p>Set the <b>Default Price List</b> and <b>Default Currency</b> on the customer so quotations pick the right rates automatically. A customer created carelessly today is a reporting headache for years — the master record is a contract with your future reports.</p>"),
L("Contacts & addresses", "4", "<p>A Customer is a company; the humans and locations attach separately. <b>Contacts</b> carry names, phones, and emails; <b>Addresses</b> carry billing and shipping locations. One customer can hold many of each — a chain like your larger retail accounts has one customer record and dozens of branch shipping addresses.</p><p>Mark one contact and one address as <b>primary</b>: documents pull them by default. When a quotation shows the wrong address, the fix is almost always the address record, not the quotation.</p>"),
L("Credit limits & the credit controller", "5", "<p>A <b>Credit Limit</b> on the customer caps how much unpaid exposure you allow. When a new Sales Order would push the outstanding balance past the limit, ZhiftERP blocks submission.</p><p>Only a user holding the <b>Credit Controller</b> role can bypass the block — deliberately, per document. This is the difference between a sales team that grows revenue and one that grows bad debt: the limit is policy, the controller is the exception process.</p>"),
L("Selling Settings that matter", "4", "<p><b>Selling Settings</b> (search it in the awesome bar) holds the switches that shape daily work: customer naming, the default price list, whether sales staff must have an <b>Item Price</b> before selling, and whether one item can appear on multiple rows of the same order.</p><p>Two to know cold: <b>Allow Item to be Added Multiple Times</b> (same item at two rates on one order) and <b>Maintain Same Rate Throughout Sales Cycle</b> — which stops the delivery note quietly changing the price agreed on the order.</p>"),
],
"questions": [
Q("Which three Customer fields most directly drive sales reporting in ZhiftERP?", ["Name, email, phone", "Customer Group, Territory, and the customer name", "Credit limit, currency, price list", "Contact, address, tax ID"], 1, "Group and territory are the analysis dimensions every sales report slices by.", "Customers §1"),
Q("A customer's quotations keep defaulting to the wrong currency. Where is the durable fix?", ["Edit each quotation", "The customer's Default Currency field", "Selling Settings", "The exchange rate list"], 1, "Document defaults flow from the customer master — fix the master, not the symptom.", "Customers §1"),
Q("One customer with 30 branches needing deliveries to each branch is modelled as:", ["30 customers", "One customer with 30 shipping addresses", "One customer, addresses typed per order", "30 price lists"], 1, "One company = one customer; locations are address records attached to it.", "Contacts §2"),
Q("Documents pull which contact and address by default?", ["The newest", "The primary contact and primary address", "Alphabetically first", "Whichever was used last"], 1, "The primary flags control defaulting.", "Contacts §2"),
Q("A Sales Order is blocked because the customer would exceed their credit limit. Who can let it through?", ["Any System Manager", "A user with the Credit Controller role", "The sales user who made it", "Nobody — it must be paid first"], 1, "Credit Controller is the deliberate bypass role for credit-limit blocks.", "Credit §3"),
Q("The credit limit measures the customer's:", ["Lifetime purchases", "Unpaid outstanding exposure", "Number of open orders", "Discount ceiling"], 1, "It caps outstanding receivables, not sales volume.", "Credit §3"),
Q("Where do you control whether the same item can appear on two rows of one order?", ["Item master", "Selling Settings — Allow Item to be Added Multiple Times", "Price list", "Sales Order print format"], 1, "It's a Selling Settings switch.", "Settings §4"),
Q("\"Maintain Same Rate Throughout Sales Cycle\" protects against:", ["Currency changes", "The rate silently differing between order and delivery/invoice", "Discounts", "Tax recalculation"], 1, "It enforces the agreed rate downstream through the cycle.", "Settings §4"),
Q("Customer Group answers which question about a customer?", ["Where they are", "What kind of customer they are", "How much they owe", "Who manages them"], 1, "Group is the kind/segment dimension; territory is the where.", "Customers §1"),
Q("The right place to record a buyer's phone number is:", ["The customer name field", "A Contact linked to the customer", "The quotation remarks", "Selling Settings"], 1, "People live on Contact records, linked to the customer.", "Contacts §2"),
Q("Territory on the customer is best set to:", ["The salesperson's name", "The geographic region used in your reporting structure", "The delivery driver", "The warehouse"], 1, "Territory is the geography dimension for analysis and targets.", "Customers §1"),
Q("A new customer record should always be created with:", ["Only a name — details later", "Name, group, territory, currency and default price list set deliberately", "A credit limit of zero", "A copied address from another customer"], 1, "Master data created deliberately keeps every later document and report clean.", "Customers §1"),
]},
"items_prices": {
"title": "Selling 2 — Items & Price Lists",
"desc": "Sellable items, units of measure, selling price lists and Item Prices — where every rate on every quotation actually comes from.",
"lessons": [
L("The sellable item", "4", "<p>An <b>Item</b> must have <b>Is Sales Item</b> ticked to appear on selling documents. The <b>Item Group</b> plays the same reporting role Customer Group plays on the other side. The <b>Default Unit of Measure</b> (UOM) is the unit stock is kept in; a <b>Sales UOM</b> can differ — keep stock in Units, sell in Cartons of 12 — with a conversion factor doing the arithmetic.</p>"),
L("Price lists", "4", "<p>A <b>Price List</b> is a named collection of rates in one currency — Standard Selling, Distributor NGN, Export USD. Selling documents read rates from the price list on the document, which defaults from the customer.</p><p>Price lists separate <i>who pays what</i>: the same item can be ₦1,000 on Retail and ₦850 on Distributor with no discounts involved — cleaner than discounting, because reports then show true agreed rates.</p>"),
L("Item Price records", "4", "<p>The actual number lives in an <b>Item Price</b>: item + price list + rate (+ optional validity dates and minimum quantity). When a quotation row finds no Item Price for its price list, the rate comes up zero — the single most common \"why is my rate 0?\" answer in support.</p><p>Bulk price maintenance is an import job: export Item Prices, update rates in the sheet, re-import. Never retype fifty rates by hand.</p>"),
L("Currency & conversion", "3", "<p>A price list has one currency. Quote a USD price list to a naira customer and ZhiftERP converts using the <b>Currency Exchange</b> rate into the document currency — visible on the document as the conversion rate.</p><p>Rule of thumb: one price list per currency per commercial arrangement, and let the customer default do the choosing.</p>"),
],
"questions": [
Q("An item refuses to appear on a quotation. First thing to check:", ["Its price", "Is Sales Item is ticked on the item", "The customer group", "The warehouse"], 1, "Only sales items appear on selling documents.", "Items §1"),
Q("Stock kept in Units but sold in Cartons of 12 uses:", ["Two item records", "A Sales UOM with a conversion factor", "A pricing rule", "Manual arithmetic on each row"], 1, "Sales UOM + conversion factor handles the unit difference.", "Items §1"),
Q("A quotation row shows rate 0. The most common cause:", ["The item is inactive", "No Item Price exists for the document's price list", "Taxes not set", "The customer has no territory"], 1, "Rates come from Item Price records; missing record = zero.", "Item Price §3"),
Q("Retail pays ₦1,000, distributors pay ₦850 for the same item. Cleanest model:", ["A 15% discount for distributors", "Two price lists with their own Item Prices", "Two item records", "Edit the rate manually each time"], 1, "Separate price lists show true agreed rates without discount noise.", "Price lists §2"),
Q("The rate a quotation uses comes from:", ["The item's standard rate always", "The Item Price for the document's price list", "The last invoice", "Selling Settings"], 1, "The document's price list is looked up in Item Price.", "Item Price §3"),
Q("A price list can contain:", ["Multiple currencies", "Exactly one currency", "Only NGN", "One item"], 1, "One price list, one currency.", "Currency §4"),
Q("Updating 300 selling rates at quarter start is best done by:", ["Editing each Item Price", "Export, update in sheet, re-import Item Prices", "Deleting the price list", "A pricing rule per item"], 1, "Bulk price maintenance is an import job.", "Item Price §3"),
Q("Which field defaults the price list onto a new quotation?", ["Selling Settings only", "The customer's Default Price List", "The item group", "The territory"], 1, "The customer default drives document defaulting.", "Price lists §2"),
Q("Item Group serves the same purpose for items that ______ serves for customers.", ["Territory", "Customer Group", "Credit limit", "Contact"], 1, "Both are the segment/reporting dimension of their master.", "Items §1"),
Q("A USD price list on a naira document results in:", ["An error", "Automatic conversion at the exchange rate into document currency", "The rate showing in USD", "Zero rates"], 1, "Currency Exchange converts into the document currency.", "Currency §4"),
Q("An Item Price can be limited by:", ["Warehouse", "Validity dates and minimum quantity", "Salesperson", "Payment terms"], 1, "Valid-from/upto and min qty scope an Item Price.", "Item Price §3"),
Q("The unit stock is counted in is the item's:", ["Sales UOM", "Default Unit of Measure", "Carton size", "Price list unit"], 1, "Default UOM is the stock-keeping unit; Sales UOM is for selling.", "Items §1"),
]},
"quotations": {
"title": "Selling 3 — Quotations",
"desc": "The offer document: creating quotations, validity, taxes on the offer, the status lifecycle, losing gracefully, and converting to an order.",
"lessons": [
L("Creating the offer", "5", "<p>A <b>Quotation</b> is the formal offer: customer (or lead), items, quantities, rates, taxes, terms. Create it directly from <b>Selling &gt; Quotation</b> or from a CRM opportunity so the trail from first contact to offer stays linked.</p><p>Rates arrive from the price list; you can override per row — overrides are visible and reportable, so discipline stays intact. The <b>Valid Till</b> date says how long the offer stands; after it passes, the quotation shows <b>Expired</b>.</p>"),
L("Taxes on the quotation", "4", "<p>Attach a <b>Sales Taxes and Charges Template</b> — for Nigerian trade, typically VAT at 7.5% — and the quotation shows the customer the true payable total. Quoting without tax and surprising the customer at invoice is how deals sour late.</p><p>The template travels forward: convert the quotation and the same taxes flow onto the Sales Order and beyond.</p>"),
L("The status lifecycle", "4", "<p>Draft → <b>Open</b> on submit. From Open: <b>Ordered</b> when a Sales Order is made from it, <b>Lost</b> when you concede, <b>Expired</b> when Valid Till passes, <b>Cancelled</b> if withdrawn. The Quotation list filtered to Open IS your offers-awaiting-answer pipeline — keep it honest.</p>"),
L("Losing well & converting", "4", "<p>Marking a quotation <b>Lost</b> asks for a <b>Lost Reason</b> (price, competitor, timing). Six months of honest lost reasons is a strategy document nobody had to write.</p><p>Winning: <b>Create &gt; Sales Order</b> from the quotation carries everything across — items, rates, taxes, terms — no retyping, no transcription errors. The quotation flips to Ordered and the chain of custody is unbroken.</p>"),
],
"questions": [
Q("A submitted quotation awaiting the customer's answer shows status:", ["Draft", "Open", "Ordered", "Pending"], 1, "Submit moves Draft to Open — the awaiting-answer state.", "Lifecycle §3"),
Q("After Valid Till passes with no order, the quotation shows:", ["Lost", "Expired", "Cancelled", "Closed"], 1, "Expiry is automatic from the Valid Till date.", "Lifecycle §3"),
Q("Making a Sales Order from a quotation flips the quotation to:", ["Closed", "Ordered", "Won", "Fulfilled"], 1, "Ordered records that the offer converted.", "Converting §4"),
Q("Marking a quotation Lost prompts for:", ["A discount", "A Lost Reason", "Manager approval", "A replacement quote"], 1, "Lost reasons accumulate into competitive intelligence.", "Losing §4"),
Q("Nigerian VAT on a quotation is applied via:", ["Typing 7.5% into the rate", "A Sales Taxes and Charges Template", "The item master", "The customer group"], 1, "The tax template carries VAT onto the document.", "Taxes §2"),
Q("Why quote taxes on the offer rather than adding them at invoice?", ["It's legally required on quotes", "The customer sees the true payable total — no late surprises", "It changes the rate", "Templates only work on quotations"], 1, "Late tax surprises sour closed deals.", "Taxes §2"),
Q("Overriding a price-list rate on one quotation row is:", ["Impossible", "Allowed, visible, and reportable", "Only for System Managers", "Automatic"], 1, "Row overrides are permitted and transparent.", "Creating §1"),
Q("Your live offers-awaiting-answer list is the Quotation list filtered to:", ["Draft", "Open", "Ordered", "All"], 1, "Open = submitted, unanswered, unexpired.", "Lifecycle §3"),
Q("Converting via Create > Sales Order matters because:", ["It's faster to type fresh", "Items, rates, taxes and terms carry over with no transcription errors", "It skips approval", "It hides the quotation"], 1, "Document flow preserves the agreed offer exactly.", "Converting §4"),
Q("A quotation can be made against:", ["Only a customer", "A customer or a lead", "Only an existing order", "A supplier"], 1, "Quotations support leads as well as customers.", "Creating §1"),
Q("The taxes chosen on the quotation:", ["Must be re-entered on the order", "Flow onto the Sales Order made from it", "Apply only to the quote", "Are locked to VAT"], 1, "The template travels forward through the cycle.", "Taxes §2"),
Q("Six months of Lost Reasons is best used as:", ["A blame record", "Competitive and pricing intelligence for strategy", "A deletion queue", "Nothing — it's noise"], 1, "Patterns in why deals die tell you what to fix.", "Losing §4"),
]},
"sales_orders": {
"title": "Selling 4 — Sales Orders",
"desc": "The commitment document: delivery dates, what submission reserves, the status language, amendments, holds and closes, and delivery tolerance.",
"lessons": [
L("The commitment", "4", "<p>A <b>Sales Order</b> is the point where an offer becomes an obligation: the customer has said yes, and you now owe goods by the <b>Delivery Date</b>. Made from the quotation (preferred) or directly, it carries items, rates, taxes, and per-row delivery dates when different lines ship at different times.</p>"),
L("What submission does", "4", "<p>Submitting a Sales Order commits stock intent: ordered quantities appear as <b>reserved</b> against the warehouse, so planners and other salespeople see the truth of what is promised. It also opens the order's fulfilment ledger — every delivery note and invoice made from it counts down the remaining quantities.</p>"),
L("Status language & control", "5", "<p>A submitted order reads <b>To Deliver and Bill</b>, then <b>To Bill</b> (delivered, not invoiced), <b>To Deliver</b> (invoiced first), and <b>Completed</b>. Two manual controls: <b>Hold</b> pauses an order (credit issues, stock trouble) and <b>Close</b> ends it early — the customer took 80 of 100 and won't take more; closing releases the reservation and stops the order haunting your pending lists.</p><p>Amending: cancel and <b>Amend</b> creates the next revision with full history preserved.</p>"),
L("Delivery tolerance", "3", "<p>Real warehouses ship 102 units against an order of 100. The <b>Over Delivery/Receipt Allowance %</b> (on the item or globally) says how much overage a delivery may carry before ZhiftERP blocks it. Zero tolerance means exact quantities only — right for serialized goods, wrong for bulk.</p>"),
],
"questions": [
Q("A freshly submitted, untouched Sales Order shows status:", ["Open", "To Deliver and Bill", "Confirmed", "Pending"], 1, "Both obligations — deliver and bill — are outstanding.", "Status §3"),
Q("Delivered in full but not yet invoiced, the order reads:", ["To Deliver", "To Bill", "Completed", "Closed"], 1, "Delivery done; billing remains.", "Status §3"),
Q("Submitting a Sales Order affects stock by:", ["Deducting it immediately", "Reserving the ordered quantities against the warehouse", "Nothing until invoice", "Transferring it to the customer"], 1, "Reservation shows everyone what's promised.", "Submission §2"),
Q("The customer took 80 of 100 and will take no more. Correct action:", ["Cancel the order", "Close the order", "Delete the remaining rows", "Deliver 20 to scrap"], 1, "Close ends it early, releases reservation, keeps history.", "Status §3"),
Q("An order that must pause for a credit issue should be:", ["Cancelled", "Held", "Closed", "Deleted"], 1, "Hold pauses without destroying the commitment.", "Status §3"),
Q("Changing a submitted order's quantities is done by:", ["Editing it directly", "Cancel then Amend, creating the next revision", "A new order", "Asking a System Manager to edit SQL"], 1, "Amend preserves the revision history.", "Status §3"),
Q("Shipping 102 against an order of 100 is permitted when:", ["Never", "Over Delivery Allowance % covers the 2% overage", "The driver insists", "The invoice matches"], 1, "The allowance defines acceptable overage before blocking.", "Tolerance §4"),
Q("Different lines shipping at different times are handled by:", ["Separate orders always", "Per-row delivery dates on one order", "Remarks", "Holding the order"], 1, "Row-level delivery dates schedule split fulfilment.", "Commitment §1"),
Q("The order's remaining-to-deliver quantities count down as:", ["Payments arrive", "Delivery Notes are made from the order", "Time passes", "Stock is purchased"], 1, "Fulfilment documents made FROM the order drive its ledger.", "Submission §2"),
Q("\"To Deliver\" (without \"and Bill\") means:", ["Nothing delivered", "Invoiced ahead of delivery; goods still owed", "Completed", "On hold"], 1, "Billing done first; delivery outstanding.", "Status §3"),
Q("Zero over-delivery tolerance is right for:", ["Bulk cement", "Serialized electronics where exact units matter", "All items", "No items"], 1, "Serialized goods need exact quantities; bulk needs slack.", "Tolerance §4"),
Q("The preferred origin of a Sales Order is:", ["Direct entry always", "Create from the accepted Quotation", "Copy of an old order", "Import"], 1, "Creating from the quotation preserves the agreed offer.", "Commitment §1"),
]},
"delivery": {
"title": "Selling 5 — Delivery Notes & Returns",
"desc": "Where stock actually moves: delivery notes from orders, partial shipments, statuses, sales returns, packing slips, and serial/batch discipline.",
"lessons": [
L("The document that moves stock", "4", "<p>The <b>Delivery Note</b> is the moment goods leave: submitting it <b>deducts stock</b> from the warehouse and counts down the Sales Order. Always create it <b>from the order</b> (Create &gt; Delivery Note) so quantities, rates and taxes flow and the order's ledger stays true.</p>"),
L("Partial delivery & status", "4", "<p>Deliver 60 of 100 today: make the DN from the order and edit quantities down — the order remembers 40 remain, and the next DN offers exactly the 40 remaining. A DN reads <b>To Bill</b> until invoiced, then <b>Completed</b>; a DN can also be made against the invoice when billing led.</p>"),
L("Sales returns", "5", "<p>Goods come back via a <b>Sales Return</b>: a Delivery Note with <b>Is Return</b> ticked, made against the original DN, with negative quantities. Submitting it puts stock <b>back into</b> the warehouse and the paper trail ties the return to the exact original shipment. The money side is the credit note — a return Sales Invoice — covered in the next module.</p>"),
L("Packing slips, serials & batches", "4", "<p>A <b>Packing Slip</b> against the DN lists cartons and contents for the driver and the gate. Items tracked by <b>Serial No</b> or <b>Batch</b> demand the exact serials/batches on the DN — this is what makes \"which customer got batch B-204?\" answerable during a recall, in seconds instead of days.</p>"),
],
"questions": [
Q("Stock is deducted from the warehouse at which moment?", ["Sales Order submit", "Delivery Note submit", "Invoice payment", "Quotation acceptance"], 1, "The DN is the stock-moving document.", "Moving stock §1"),
Q("A Delivery Note should be created:", ["From scratch each time", "From the Sales Order via Create > Delivery Note", "By copying an old DN", "Only by storekeepers"], 1, "Creating from the order keeps the fulfilment ledger true.", "Moving stock §1"),
Q("60 of 100 delivered today. The next DN from the order will offer:", ["100", "40", "60", "Whatever is typed"], 1, "The order tracks the remaining 40 automatically.", "Partial §2"),
Q("An undelivered-quantity view across all orders lives in:", ["The DN list", "The Sales Order's remaining quantities (and order analysis reports)", "The item master", "Selling Settings"], 1, "Remaining-to-deliver is order-side data.", "Partial §2"),
Q("A sales return is recorded as:", ["Deleting the original DN", "A Delivery Note with Is Return, against the original DN, negative quantities", "A purchase receipt", "A stock adjustment"], 1, "The return DN reverses stock with a trail to the original.", "Returns §3"),
Q("Submitting a sales-return DN moves stock:", ["Out of the warehouse", "Back into the warehouse", "Nowhere", "To a supplier"], 1, "Returns restore stock.", "Returns §3"),
Q("The customer-money side of a return is handled by:", ["The return DN itself", "A credit note (return Sales Invoice)", "Cash from the driver", "Editing the order"], 1, "Stock and money reverse on separate linked documents.", "Returns §3"),
Q("A DN that has shipped but not been invoiced reads:", ["Completed", "To Bill", "Draft", "Open"], 1, "To Bill = goods gone, billing pending.", "Partial §2"),
Q("\"Which customers received batch B-204?\" is answerable because:", ["Drivers keep notebooks", "Batch numbers are recorded on each Delivery Note", "The invoice lists batches", "It isn't answerable"], 1, "Batch/serial capture on the DN powers recall tracing.", "Serials §4"),
Q("The Packing Slip exists to:", ["Replace the DN", "List cartons and contents for the driver and the gate", "Charge packing fees", "Reserve stock"], 1, "It's the physical-handling companion to the DN.", "Serials §4"),
Q("A serial-tracked item on a DN requires:", ["Nothing special", "The exact serial numbers being shipped", "A batch number", "Manager approval"], 1, "Serialized stock demands per-unit identity on the DN.", "Serials §4"),
Q("A Delivery Note can also be created against:", ["A quotation", "A Sales Invoice, when billing preceded delivery", "A lead", "A price list"], 1, "Invoice-first flows make the DN from the invoice.", "Partial §2"),
]},
"taxes_invoicing": {
"title": "Selling 6 — Taxes, Pricing Rules & Invoicing",
"desc": "VAT done right, inclusive vs exclusive, item tax overrides, pricing rules and discounts, the Sales Invoice, payments, credit notes — and the reports that watch it all.",
"lessons": [
L("Sales taxes & VAT", "5", "<p>The <b>Sales Taxes and Charges Template</b> defines tax rows once — Nigerian <b>VAT 7.5%</b> output tax to its ledger account — and every selling document applies it consistently. An <b>Item Tax Template</b> on an item overrides the document rate for that row: how zero-rated or exempt items sit correctly on a VAT-able invoice.</p><p><b>Inclusive</b> tax means the entered rate already contains VAT (₦1,075 inclusive = ₦1,000 + ₦75); <b>exclusive</b> adds it on top. Mixing them up misstates either your price or your VAT return.</p>"),
L("Pricing rules & discounts", "5", "<p>A <b>Pricing Rule</b> applies a discount or special rate automatically when conditions match — item/group/brand, customer/group/territory, quantity brackets, validity dates. \"10% off cartons of 50+ for Distributors in Q4\" becomes a rule, not a memo.</p><p>Manual discounting still exists per document — the <b>Additional Discount</b> on totals or per-row rate cuts — but rules are policy while manual discounts are exceptions; keep the exceptional rare and visible.</p>"),
L("The Sales Invoice & getting paid", "5", "<p>The <b>Sales Invoice</b> is the accounting event: submitting it books revenue and the customer's receivable. Make it from the order or the DN so quantities and taxes flow. Its outstanding amount clears via <b>Payment Entry</b> — full, partial, or one payment across several invoices.</p><p>Status tells the collection story: <b>Unpaid</b>, <b>Partly Paid</b>, <b>Paid</b>, <b>Overdue</b> once the due date passes — the Overdue filter is your collections worklist.</p>"),
L("Credit notes & the watching reports", "5", "<p>A <b>credit note</b> is a Sales Invoice with <b>Is Return</b> — against the original invoice — reversing revenue and receivable for returned goods or corrections, mirroring the return DN on the money side.</p><p>Then the instruments: <b>Sales Analytics</b> (revenue by customer/item/territory over time), <b>Sales Order Analysis</b> (delivery backlog), and <b>Accounts Receivable</b> (who owes what, aged). A sales professional reads these weekly, not at quarter-end panic.</p>"),
],
"questions": [
Q("Nigerian VAT at 7.5% is applied to selling documents through:", ["Typing it per row", "A Sales Taxes and Charges Template", "The customer master", "A pricing rule"], 1, "The template defines VAT once for consistent application.", "VAT §1"),
Q("A VAT-exempt item on an otherwise VAT-able invoice is handled by:", ["Deleting the tax row", "An Item Tax Template on that item overriding the document rate", "A separate invoice", "A discount equal to the VAT"], 1, "Item tax templates override per row.", "VAT §1"),
Q("₦1,075 entered as tax-INCLUSIVE at 7.5% VAT means net revenue of:", ["₦1,075", "₦1,000", "₦994", "₦1,150"], 1, "Inclusive rates contain the tax: 1,075 / 1.075 = 1,000.", "VAT §1"),
Q("\"10% off for Distributors buying 50+ cartons in Q4\" is best implemented as:", ["A memo to staff", "A Pricing Rule with group, quantity and validity conditions", "Manual edits per order", "A second price list per quarter"], 1, "Conditional automatic discounts are what pricing rules are for.", "Pricing §2"),
Q("Revenue and the customer's receivable are booked when:", ["The order is submitted", "The Sales Invoice is submitted", "The DN is submitted", "Payment arrives"], 1, "The invoice is the accounting event.", "Invoice §3"),
Q("An invoice past its due date and unpaid shows:", ["Unpaid", "Overdue", "Late", "Blocked"], 1, "Overdue is the past-due status — and the collections filter.", "Invoice §3"),
Q("One customer payment covering three invoices is recorded as:", ["Three payment entries", "One Payment Entry allocated across the three invoices", "A journal only", "A credit note"], 1, "Payment Entry allocates one payment over multiple invoices.", "Invoice §3"),
Q("A credit note in ZhiftERP is:", ["A special letter", "A Sales Invoice with Is Return against the original invoice", "A cancelled invoice", "A negative payment"], 1, "The return invoice reverses revenue and receivable with a trail.", "Credit notes §4"),
Q("The stock reversal and the money reversal of a return live on:", ["One document", "The return DN and the credit note respectively", "The order", "A journal entry"], 1, "Stock reverses on the return DN; money on the credit note.", "Credit notes §4"),
Q("Who-owes-what, aged by how long, is the report:", ["Sales Analytics", "Accounts Receivable", "Stock Ledger", "Sales Order Analysis"], 1, "AR ageing is the receivables instrument.", "Reports §4"),
Q("Delivery backlog across all open orders is read from:", ["Accounts Receivable", "Sales Order Analysis", "The DN list", "Sales Register alone"], 1, "Order analysis shows ordered vs delivered vs billed.", "Reports §4"),
Q("Manual per-document discounts should be:", ["The normal pricing method", "Rare, visible exceptions — policy lives in pricing rules and price lists", "Hidden in rates", "Banned entirely"], 1, "Rules are policy; manual discounts are exceptions kept visible.", "Pricing §2"),
]},
}

SEED_SRC = '''"""ZhiftERP Sales Professional track seed — the complete selling curriculum.

Content lives in academy_sales_pro_data.json (6 modules, 24 lessons, 72
questions). Modules are PROCTORED: timed 60s/question, 10 served from
each 12-question bank.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track
Idempotent per module and for the track.
"""

import json
import os

import frappe

ORDER = ["customers", "items_prices", "quotations", "sales_orders", "delivery", "taxes_invoicing"]

TRACK = {
	"title": "ZhiftERP Sales Professional",
	"serial_prefix": "ZERP-SALESPRO",
	"description": "The complete selling certification: customer management, items and pricing, quotations, sales orders, delivery and returns, and taxes, pricing rules, invoicing and collections — six proctored examinations from foundations to the reports that run a sales book.",
}


def _data():
	path = os.path.join(os.path.dirname(__file__), "academy_sales_pro_data.json")
	with open(path) as f:
		return json.load(f)


def seed_sales_pro_track():
	data = _data()
	if not frappe.db.exists("Duty Product", "ZhiftERP"):
		frappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP", "active": 1, "sort_order": 0}).insert(
			ignore_permissions=True
		)
		print("created Duty Product: ZhiftERP")

	module_names = {}
	for i, key in enumerate(ORDER):
		m = data[key]
		existing = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
		if existing:
			module_names[key] = existing
			print(f"module exists: {m['title']}")
			continue
		mod = frappe.get_doc(
			{
				"doctype": "Duty Training Module",
				"title": m["title"],
				"product": "ZhiftERP",
				"description": m["desc"],
				"active": 1,
				"audience": "Both",
				"sort_order": 10 + i,
				"pass_mark": 70,
				"timed_mode": 1,
				"seconds_per_question": 60,
				"questions_served": 10,
			}
		).insert(ignore_permissions=True)
		module_names[key] = mod.name
		for j, l in enumerate(m["lessons"]):
			frappe.get_doc(
				{
					"doctype": "Duty Lesson",
					"module": mod.name,
					"title": l["title"],
					"sort_order": j,
					"est_minutes": l["est"],
					"content": l["html"],
				}
			).insert(ignore_permissions=True)
		for q in m["questions"]:
			frappe.get_doc(
				{
					"doctype": "Duty Quiz Question",
					"module": mod.name,
					"question": q["q"],
					"opt_a": q["opts"][0],
					"opt_b": q["opts"][1],
					"opt_c": q["opts"][2],
					"opt_d": q["opts"][3],
					"correct": "ABCD"[q["ans"]],
					"rationale": q["why"],
					"source": q["src"],
					"active": 1,
				}
			).insert(ignore_permissions=True)
		print(f"seeded module: {m['title']} ({len(m['lessons'])} lessons, {len(m['questions'])} questions, proctored)")

	if frappe.db.exists("Duty Certification Track", {"title": TRACK["title"]}):
		print(f"track exists: {TRACK['title']}")
	else:
		frappe.get_doc(
			{
				"doctype": "Duty Certification Track",
				"title": TRACK["title"],
				"product": "ZhiftERP",
				"audience": "Consultant",
				"serial_prefix": TRACK["serial_prefix"],
				"description": TRACK["description"],
				"active": 1,
				"modules": [{"module": module_names[k]} for k in ORDER],
			}
		).insert(ignore_permissions=True)
		print(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

	frappe.db.commit()
	print("ZhiftERP Sales Professional track ready.")
'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()

    if os.path.exists(os.path.join(root, SEED_PATH)):
        print("Already applied. Nothing to do.")
        return
    if '"3.81.1"' not in init:
        sys.exit("ABORT: not at v3.81.1.")

    problems = []
    for key, m in DATA.items():
        if len(m["questions"]) != 12:
            problems.append(f"  {key}: {len(m['questions'])} questions (want 12)")
        for q in m["questions"]:
            if len(q["opts"]) != 4 or not (0 <= q["ans"] <= 3):
                problems.append(f"  {key}: malformed question '{q['q'][:40]}'")
        if len(m["lessons"]) != 4:
            problems.append(f"  {key}: {len(m['lessons'])} lessons (want 4)")
    if problems:
        print("ABORT — content sanity failed:")
        print("\n".join(problems))
        sys.exit(1)
    print(f"Content sane: {len(DATA)} modules, {sum(len(m['lessons']) for m in DATA.values())} lessons, {sum(len(m['questions']) for m in DATA.values())} questions.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(DATA, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, SEED_PATH), "w", encoding="utf-8") as f:
        f.write(SEED_SRC)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.81.1"', '"3.82.0"'))
    print("  wrote academy_sales_pro_data.json + academy_seed_sales_pro.py")
    print("wrote __init__.py -> 3.82.0")


if __name__ == "__main__":
    main()
