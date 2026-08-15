#!/usr/bin/env python3
"""Build 'Procure to Pay' into academy_control_data.json.

Module 4 of System-Based Internal Control in a Retail Environment.

One correction to the app specification is embedded here. That document said the
bank-account-change test queries Version on Supplier. It does not: ERPNext holds
banking on a separate Bank Account doctype carrying party_type and party, with
iban and bank_account_no, while Supplier holds only default_bank_account as a
link. Both are tracked. The test therefore watches Bank Account and joins to
the supplier through party — a materially different query, and the reason for
checking rather than recalling.

Also verified: Purchase Order, Purchase Receipt and Purchase Invoice as the
three-way match documents, and Authorization Rule carrying value, based_on,
system_role, approving_role and approving_user.

Run from the app package directory:  python3 build_control_m4.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "procure_pay"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Where procurement leaks", 12, """<p>Procurement is the largest outflow most retailers have, and unlike the till it is unattended. A cash loss is bounded by what fits in a drawer; a procurement loss is bounded by what somebody will authorise, and the amounts are of a different order.</p>

<p><b>The five ways value leaves, roughly in order of how much they cost and inversely to how much attention they get.</b></p>

<p><b>Paying for what did not arrive.</b> Goods invoiced and never delivered, or delivered short and signed for anyway. The most common and the least dramatic, because it usually starts as carelessness at the receiving bay and only later becomes an arrangement.</p>

<p><b>Paying more than agreed.</b> A price above the negotiated rate, a rebate never claimed, a discount never applied. Nobody steals anything; the business simply pays more, invoice after invoice, and nothing looks unusual on any single one.</p>

<p><b>Buying from the wrong supplier.</b> A supplier connected to the buyer, or one whose price is uncompetitive but whose relationship is comfortable. Legal in most cases, expensive in all.</p>

<p><b>Paying the wrong account.</b> A genuine invoice from a genuine supplier, paid to a bank account that is not theirs. The highest-value single event available and the fastest.</p>

<p><b>Paying twice.</b> Duplicate invoices, duplicate suppliers, a credit note never applied. Almost always error rather than intent, and recoverable if found.</p>

<p><b>Why procure-to-pay is unusually testable.</b> The process is documentary from end to end — an order, a receipt, an invoice, a payment — and each document references the last. A control failure therefore shows as a broken relationship between documents rather than as a missing piece of paper, and broken relationships are exactly what a query finds.</p>

<p><b>What makes it different from the till.</b> Till schemes are small and repeated; procurement schemes are large and rare. That changes your method entirely. Analytical profiling — the ranked distribution that works so well for cashiers — is much weaker here, because a single ₦40m event does not show up in an average. <b>Procurement work is mostly nil-expected testing on the whole population</b>, looking for the one relationship that should never exist.</p>

<p><b>And it changes who you are examining.</b> Procurement is done by people senior enough to have influence over how audit findings are received. That is a real consideration, and it is why the evidence standard in this module is higher and why module 9's reporting discipline matters more here than anywhere else in the track.</p>

<blockquote>WATCH-OUT: Procurement fraud is usually discovered by accident — a supplier calls about an unpaid invoice, a delivery driver mentions something, somebody goes on leave and their replacement notices. That is not a testing programme; it is luck, and it means the losses you have found are a sample of the ones that occurred.</blockquote>

<p><b>One thing to establish before designing anything.</b> How much of your purchasing actually goes through the system. In many retailers a meaningful share is bought informally — cash purchases at branch level, urgent replenishment from a nearby wholesaler, services engaged by a phone call and invoiced later. Those transactions are outside every test in this module, and quantifying them is itself a finding. A procurement control framework that covers 60% of spend is a framework with a 40% hole, and nobody has usually measured which.</p>"""
, [
 C("Analytical profiling works less well in procurement than at the till because:",
   ["The data is poorer", "Schemes here are large and rare, and a single event does not move an average",
    "Approvals interfere", "Volumes are lower"], 1,
   "Procurement work is mostly nil-expected testing on the whole population."),
 C("A control failure in procure-to-pay typically shows as:",
   ["A missing document", "A broken relationship between documents",
    "An unusual value", "A late posting"], 1,
   "The process is documentary end to end and each document references the last, which is what makes it queryable."),
 C("Most procurement fraud is discovered by:",
   ["Routine testing", "Accident — a supplier call, a remark, somebody covering leave",
    "External audit", "Reconciliation"], 1,
   "Which means the losses found so far are a sample of those that occurred.")]),

("The three-way match", 12, """<p>The three-way match is the central control in procurement, and in a system environment it is enforced by relationships between documents rather than by somebody comparing three pieces of paper.</p>

<p><b>The three documents.</b> A <b>Purchase Order</b> says what was agreed to be bought, from whom, at what price. A <b>Purchase Receipt</b> says what physically arrived. A <b>Purchase Invoice</b> says what the supplier is charging. Where all three agree on quantity and price, payment is safe. Where they do not, something needs explaining.</p>

<p><b>What the system does automatically and what it does not.</b> ERPNext links these documents and will carry quantities forward, so an invoice created from a receipt inherits its figures. That is convenient and it is not a control — because the documents can also be created independently, and an invoice raised without reference to a receipt has nothing to disagree with.</p>

<p><b>So the first question is coverage, not exceptions.</b> What proportion of purchase invoices reference a receipt at all? A business with 30% of invoices unmatched does not have a match exception problem; it has no three-way match, and reporting individual mismatches would miss the point entirely.</p>

<p><b>The standing tests, and two ship with the platform.</b></p>

<p><i>Received Items To Be Billed</i> lists goods received with no invoice. Aged, it finds receipts that will never be billed — sometimes because the supplier forgot, occasionally because the goods were never really received and the receipt was created to close a purchase order.</p>

<p><i>Billed Items To Be Received</i> is the more interesting direction: <b>invoiced and not received</b>. Every row is money owed or paid for goods with no evidence of arrival. In a retailer this should be a small and explicable population, and it is the single most valuable standing report in this module.</p>

<p><b>Quantity and price variances.</b> Where a receipt records less than the order and the invoice charges for the order quantity, the difference is a payment for goods not received. Where the invoiced rate exceeds the ordered rate, the difference is a payment above agreement. Both are computable across the whole population, and both should be nil or explicable.</p>

<p><b>Tolerances, and the question to ask about them.</b> Most configurations permit a small variance without blocking — a percentage or an amount. Establish what yours is, because it defines exactly how much can be taken without any control firing. A 5% tolerance on ₦2bn of purchasing is ₦100m of unchallenged variance, and that figure usually surprises the people who set it.</p>

<blockquote>IMPLEMENTATION TIP: Before testing match exceptions, measure match coverage. The proportion of invoices with no linked receipt tells you whether the control exists at all, and it is a one-line query that reframes everything that follows.</blockquote>

<p><b>Services complicate the match and deserve their own treatment.</b> There is no receipt for consultancy, cleaning or haulage — nothing physically arrives to be counted. The three-way match collapses to two, and the control that replaces the receipt is somebody confirming the service was performed. Test whether that confirmation exists and who gives it: service spend is where the weakest evidence and the least scrutiny usually coincide, and it is frequently a larger share of spend than anybody assumes.</p>"""
, [
 C("30% of purchase invoices reference no receipt. The correct conclusion is:",
   ["There are many match exceptions", "There is no three-way match, and reporting individual mismatches misses the point",
    "The system is misconfigured", "Receipts are posted late"], 1,
   "Coverage is the first question; exceptions are only meaningful once the control exists."),
 C("A 5% match tolerance on ₦2bn of annual purchasing means:",
   ["A reasonable allowance", "₦100m of variance that no control will challenge",
    "Nothing material", "Faster processing"], 1,
   "Establish the tolerance, because it defines exactly how much can pass unchallenged."),
 C("Which shipped report finds goods invoiced but with no evidence of arrival?",
   ["Received Items To Be Billed", "Billed Items To Be Received",
    "Purchase Order Analysis", "Item-wise Purchase History"], 1,
   "Every row is money owed or paid for goods that may never have come.")]),

("Suppliers as master data", 12, """<p>A supplier record is a standing instruction to pay somebody. It deserves the scrutiny of one, and it is usually created by whoever needed the purchase made.</p>

<p><b>Where the banking actually lives, and this matters for your query.</b> Supplier holds <code>default_bank_account</code> as a link. The banking itself sits on a separate <b>Bank Account</b> record carrying <code>party_type</code> and <code>party</code> pointing back to the supplier, with <code>iban</code> and <code>bank_account_no</code>. Both doctypes track changes.</p>

<p>So the bank-change test queries versions of <b>Bank Account</b> and joins to the supplier through <code>party</code> — not versions of Supplier, which will show only that the default link changed. An auditor testing the wrong doctype gets a clean result and concludes wrongly.</p>

<p><b>The highest-value test in this module.</b> Bank account details changed, followed by a payment to that supplier within a short window. The scheme it detects is simple and devastating: change the account on a legitimate supplier, wait for a genuine invoice to be paid, change it back. The invoice is real, the goods arrived, the approval was proper, and the money went elsewhere. <b>Nothing in the three-way match touches it.</b></p>

<p>Without field-level version history this test is impossible, which is why module 2 spent time on it.</p>

<p><b>Duplicate suppliers.</b> The same entity created twice permits the same invoice to be paid twice, and it defeats spend analysis because the total is split. Test by name similarity, by matching bank account numbers, by shared tax identifiers, and by shared addresses or phone numbers. <b>Matching bank details across two supplier records is the strongest signal</b> and takes one query.</p>

<p><b>Suppliers connected to staff.</b> Compare supplier contact details against employee records — phone numbers, addresses, surnames, bank accounts. This is uncomfortable work and it is standard practice in mature audit functions. Findings here are rarely conclusive on their own; a shared surname is a coincidence in a country with common surnames, and a shared bank account is not.</p>

<p><b>Dormant suppliers reactivated.</b> A supplier with no activity for a year, suddenly transacting, is worth a look — particularly if the record was edited shortly before. Dormant records are attractive precisely because nobody is watching them and they carry the legitimacy of history.</p>

<p><b>Who can create a supplier</b> is the control question behind all of this. If the person who raises orders can also create the supplier they order from, the segregation that everything else depends on is absent, and no amount of downstream testing compensates.</p>

<blockquote>WATCH-OUT: Test bank account changes on the Bank Account doctype, not on Supplier. A version query against Supplier shows only that the default link moved, and it will come back reassuringly empty while the actual account details are being changed weekly.</blockquote>

<p><b>Onboarding is the control that prevents most of this.</b> What actually happens before a supplier record is created — documents collected, bank details verified independently, the relationship declared, a second person approving. In many businesses the answer is that a buyer creates the record when they need to raise an order, which means the standing instruction to pay is created by the person who wants the payment made. Test the sequence: how many suppliers were created on the same day as their first purchase order.</p>"""
, [
 C("A query on Version for Supplier returns no bank changes. You should:",
   ["Conclude no changes occurred", "Query Bank Account instead, joining to the supplier through party",
    "Check permissions", "Widen the date range"], 1,
   "Supplier holds only default_bank_account as a link; the details sit on Bank Account."),
 C("Bank details changed, a genuine invoice paid, details changed back. This defeats:",
   ["Supplier approval", "The three-way match entirely — the invoice, goods and approval are all real",
    "Payment authorisation", "Duplicate detection"], 1,
   "Only version history on the banking record exposes it."),
 C("The strongest single indicator of duplicate suppliers is:",
   ["Similar names", "Matching bank account numbers", "The same address", "A shared contact name"], 1,
   "Names are frequently similar for innocent reasons; bank details are not.")]),

("Approval limits and how they are worked around", 12, """<p>An approval limit says that above a value, a second person must agree. It is the most common financial control in existence and among the easiest to defeat, because defeating it requires no system access at all — only arithmetic.</p>

<p><b>How limits are enforced here.</b> Either a Workflow attached to the doctype, with states and transitions and a recorded Workflow Action naming who was asked and who acted; or an <b>Authorization Rule</b> carrying a <code>value</code>, a <code>based_on</code> basis, and the roles or users permitted to approve. A business may use either, both, or neither.</p>

<p><b>Establish which before testing anything.</b> If the answer is neither — if any buyer can raise and submit any order at any value — then you have your finding, and it outranks every pattern in this chapter. Report the absence of the control before analysing behaviour under a control that does not exist.</p>

<p><b>The classic defeat: splitting.</b> An order of ₦1.4m against a ₦500,000 limit becomes three orders of about ₦470,000, raised the same day to the same supplier. Each is individually within authority and none requires a second signature. The business bought the same goods from the same supplier on the same day and nobody approved the purchase.</p>

<p><b>Testing for it.</b> Group purchase orders by supplier and by date, or by a short window such as a week, and total. Flag where the aggregate crosses the limit while each constituent sits below it. This is a population test, and it is the reason for the emphasis in module 1: sampling fifty orders will almost never find splitting, because the individual orders look entirely ordinary.</p>

<p><b>The histogram, which is faster than any test.</b> Plot purchase order values and look immediately below each approval threshold. If there is a cluster, the limit is being worked around, and you know it in thirty seconds without designing anything. People optimise against limits and the distribution shows it plainly.</p>

<p><b>Amendment after approval.</b> Where a document can be approved at one value and then amended upward, the approval attaches to a version that no longer exists. Version history answers this directly: compare the value at the point of approval with the final value. In a well-configured system amendment re-triggers approval; establish whether yours does, because if it does not, every limit in the business is advisory.</p>

<p><b>Self-approval.</b> Whether the approver can be the requester. Sometimes permitted deliberately for small values, frequently permitted by accident through role assignment. Test it as data — orders where the approving user equals the owner — rather than by reading the policy.</p>

<blockquote>IMPLEMENTATION TIP: The value histogram is the highest-return thirty seconds in this module. One chart, all purchase orders, and a marker at each approval limit. A cluster immediately below a threshold is a finding you can see rather than compute.</blockquote>

<p><b>And check what the limit is actually set against.</b> A threshold on order value behaves differently from one on invoice value or line value, and a limit applied per line rather than per document is barely a limit at all — a single order of ten lines at ₦450,000 each passes every check while committing ₦4.5m. Read the configuration rather than the policy document, because the two frequently describe different controls.</p>"""
, [
 C("Three orders of ₦470,000 to one supplier on one day, against a ₦500,000 limit. The finding is:",
   ["Each order was properly authorised", "The purchase was split so that nobody approved it",
    "The limit is set too low", "The supplier should be consolidated"], 1,
   "Sampling fifty orders will almost never find this; each one looks entirely ordinary."),
 C("Purchase orders can be approved and then amended upward without re-approval. This means:",
   ["Amendments need monitoring", "Every limit in the business is advisory",
    "Approval should be at invoice stage", "The workflow needs a new state"], 1,
   "The approval attaches to a version that no longer exists."),
 C("No approval mechanism exists at all — any buyer can raise and submit any value. You should:",
   ["Analyse buyer behaviour for patterns", "Report the absence of the control before analysing behaviour under one that does not exist",
    "Recommend a value threshold and move on", "Test the largest orders"], 1,
   "It outranks every pattern in the chapter.")]),

("Prices paid against prices agreed", 12, """<p>Nothing is stolen and nothing is missing. The business simply pays more than it agreed, invoice after invoice, and no single document looks wrong. It is the quietest procurement loss and among the largest.</p>

<p><b>What the agreed price is, and where it lives.</b> Depending on how the business works: an Item Price against a supplier price list, a rate on a blanket order, a contracted rate held outside the system, or simply the rate on the last order. Establish which is authoritative before testing, because comparing against the wrong reference produces a report full of differences that mean nothing.</p>

<p><b>The core test.</b> Invoiced rate against agreed rate, by item and supplier, across the whole population, beyond a tolerance. Rank by total value of the difference rather than by percentage — a 2% overcharge on your largest line is worth more than a 40% overcharge on something you buy twice a year, and a percentage-ranked report puts the trivial one at the top.</p>

<p><b>The drift test, which finds what a point-in-time comparison misses.</b> Track the rate paid for an item over eighteen months. A supplier raising prices in small steps, none individually notable, can move a rate 30% in a year while every single invoice passes tolerance. Plotting the series exposes it immediately; testing invoice by invoice never will.</p>

<p><b>Rebates and volume discounts.</b> Where a supplier agreement provides a rebate at a volume threshold, test whether the volume was reached and whether the rebate was claimed and received. Unclaimed rebates are pure loss and are common, because claiming them is somebody's job in the sense that it is nobody's.</p>

<p><b>Comparing across suppliers.</b> For items bought from more than one supplier, compare rates. A persistent difference may be quality, terms or delivery — all legitimate — or it may be that nobody has looked in two years. Either way it is a question worth asking, and the answer belongs to procurement rather than to you.</p>

<p><b>Currency, in an importing business.</b> Where purchases are in foreign currency, test the rate applied against the rate that should have been used on that date. Differences here are usually mechanical rather than deliberate, and they are material — a systematic rate error across a year of imports is a large number, and it will be found eventually by somebody less friendly than you.</p>

<p><b>Who to give this to.</b> Price findings are commercially useful rather than accusatory, which makes them the easiest thing in this module to get acted on. A report showing ₦18m of overcharges recoverable from three suppliers will be welcomed by the people a fraud finding would put on the defensive, and it builds the standing you will need later.</p>

<p><b>Where the agreed price does not exist in the system at all.</b> Often the negotiated rate lives in an email or a signed schedule and was never loaded, so there is nothing to compare against and every invoice passes by default. That is a finding in itself and a straightforward recommendation: load the agreed rates and the control becomes automatic rather than dependent on somebody remembering what was agreed eight months ago.</p>

<blockquote>IMPLEMENTATION TIP: Rank price variances by total naira value, never by percentage. The percentage view surfaces small items with volatile prices and buries the systematic overcharge on your highest-volume line, which is where the money actually is.</blockquote>"""
, [
 C("Your variance report is topped by a spice line bought twice a year at 40% over agreed. Meanwhile your largest line runs 2% over. The report is ranked:",
   ["Correctly, by severity", "By percentage, which buries where the money actually is",
    "By supplier importance", "By frequency of occurrence"], 1,
   "Two per cent on your highest-volume purchase is worth far more than forty on something incidental."),
 C("A supplier raises a rate in small steps totalling 30% over a year, each within tolerance. This is found by:",
   ["Invoice-by-invoice testing", "Plotting the rate series over time",
    "The three-way match", "Approval limit testing"], 1,
   "Every individual invoice passes; only the series exposes the drift."),
 C("You can report either ₦18m recoverable from three suppliers, or a suspected related-party purchase. Starting with the first:",
   ["Wastes the stronger finding", "Is welcomed by people the second would put on the defensive, and builds standing",
    "Delays the important work", "Signals weak resolve"], 1,
   "Commercially useful findings buy the credibility that harder ones later depend on.")]),

("Receiving: the highest-risk point", 12, """<p>The receiving bay is where the business's money becomes the business's goods, and it is typically staffed by the most junior people in the building, under time pressure, with a driver waiting.</p>

<p><b>What a Purchase Receipt asserts.</b> That these goods, in this quantity, arrived at this warehouse on this date. Everything downstream — the invoice match, the stock position, the payment — rests on it. It is the single most consequential document created by the most junior person in the process, and that asymmetry is the whole risk.</p>

<p><b>The tests that follow.</b></p>

<p><b>Receipts recording exactly the ordered quantity, always.</b> Real deliveries are occasionally short, damaged or over. A receiver whose figures always match the order to the unit is not counting; they are copying, and the receipt is worthless as evidence. Compare receipt quantity to order quantity across the population and look at the proportion of exact matches by receiver — it varies far more between people than anybody expects.</p>

<p><b>Receipts created after the invoice.</b> The sequence should be order, receipt, invoice. Where the receipt is created after the invoice arrives, it is frequently being created <i>to match it</i> rather than to record an arrival. Compare creation timestamps rather than posting dates, because posting dates can be set.</p>

<p><b>Receipts posted outside working hours, or by somebody not at that branch.</b> Both are testable against the user and the timestamp, and both are usually explicable — a late delivery, a central user assisting. Usually.</p>

<p><b>Receiving and ordering by the same person.</b> The most important segregation in procurement. Whoever chooses the supplier and the quantity should not be the person confirming what arrived, because that combination permits payment for goods that never came and nobody else ever sees the transaction.</p>

<p><b>What the auditor can and cannot establish from data.</b> You can show that a receipt exists, who created it, when, and whether it agrees with the order and the invoice. You cannot show from data that goods physically arrived. That gap is why occasional physical verification matters — attending a delivery unannounced, or tracing a receipt to the stock that should have resulted from it and then to its sale or its presence on the shelf.</p>

<p><b>The corroboration with module 5.</b> Goods invoiced and receipted but never actually delivered create system stock that does not exist, and it surfaces at the next count as shrinkage. <b>A category with persistent shrinkage and a supplier with a high proportion of exact-match receipts is a specific thing to go and look at</b>, and neither number alone would have sent you there.</p>

<p><b>Deliveries direct to branches are the harder case.</b> Where suppliers deliver to twenty locations rather than a central warehouse, receiving is done by twenty untrained people with no supervision, and receipt quality varies accordingly. Test receipt behaviour by branch as well as by person: a branch whose receipts are systematically exact, or systematically late, is a control gap at a location rather than a problem with an individual.</p>

<blockquote>WATCH-OUT: A receiver whose receipts always exactly match the order is a stronger signal than one with frequent discrepancies. Discrepancies mean somebody is counting. Perfect agreement, sustained across hundreds of deliveries, means somebody is not.</blockquote>"""
, [
 C("A receiver's quantities always exactly match the ordered quantity. This suggests:",
   ["Excellent supplier performance", "They are copying rather than counting, making the receipt worthless as evidence",
    "Good receiving discipline", "Accurate ordering"], 1,
   "Real deliveries are occasionally short, damaged or over."),
 C("A purchase receipt created after the invoice arrived is often being created:",
   ["To correct a posting error", "To match the invoice rather than to record an arrival",
    "For cut-off reasons", "By a central user"], 1,
   "Compare creation timestamps rather than posting dates, because posting dates can be set."),
 C("From data alone, an auditor cannot establish:",
   ["Who created the receipt", "That goods physically arrived",
    "Whether it matches the order", "When it was created"], 1,
   "Which is why occasional physical verification and tracing to stock matter.")]),

("Payment, and the account it went to", 12, """<p>Payment is the last control point and the only irreversible one. Everything before it can be corrected; a payment made to the wrong account is usually gone.</p>

<p><b>What to test at the payment stage.</b></p>

<p><b>Payments without an invoice.</b> A Payment Entry not allocated against a purchase invoice is paying somebody for nothing recorded. Advances exist legitimately, and should be a small, named, monitored population that clears.</p>

<p><b>Duplicate payments.</b> The same supplier, the same amount, close together, or the same supplier invoice number appearing twice. Almost always error, frequently recoverable, and finding recoverable money is the fastest way for a new audit function to establish that it pays for itself.</p>

<p><b>Payment to an account changed recently.</b> The test from chapter three, expressed at the payment end: for every payment, was the receiving bank account modified in the preceding period? This is where the two halves join, and it is worth running weekly rather than periodically, because the value at risk in a single instance can exceed a year of every other finding combined.</p>

<p><b>Payments outside the approval route.</b> Where a workflow governs payment, entries that reached submitted status without the expected Workflow Actions. Where an Authorization Rule governs it, payments above the threshold without the approving user recorded.</p>

<p><b>Manual journals affecting supplier balances.</b> A journal entry adjusting what a supplier is owed bypasses the entire purchase-to-pay process. Legitimate uses exist — corrections, settlements, contra entries — and each should be explicable. A supplier balance moved by journal rather than by invoice or payment is worth understanding every time.</p>

<p><b>The segregation that matters most here.</b> Whoever can create or amend a supplier's bank details should not be able to release payments. If one person can do both, the control is a single decision by a single individual, and everything upstream is decoration. Test it as data — the intersection of the two permission sets — rather than by asking.</p>

<p><b>Timing as a signal.</b> Payments prepared or released outside normal hours, immediately before a holiday period, or in the days after a bank detail change all warrant a look. None proves anything; all are cheap to test and each has a straightforward innocent explanation you should confirm rather than assume.</p>

<p><b>Payment runs, and the exception outside them.</b> Most businesses pay on a cycle — batched and reviewed. The payment made outside that cycle is the one worth examining: urgent, individual, and frequently justified by a supplier threatening to stop supply. Some are genuine. All bypass the review the batch receives, which is generally the point of making them outside the run.</p>

<blockquote>IMPLEMENTATION TIP: Run the bank-change-then-payment test weekly, not monthly. It is the one test in this track where the interval between the event and detection determines whether the money is recoverable, and a week is often the difference.</blockquote>"""
, [
 C("Which test should be run weekly rather than periodically?",
   ["Duplicate payments", "Bank account changed then paid",
    "Price variance", "Match coverage"], 1,
   "The interval between event and detection determines whether the money is recoverable."),
 C("A supplier balance adjusted by journal entry rather than by invoice or payment:",
   ["Is a posting convenience", "Bypasses the entire purchase-to-pay process and needs explaining every time",
    "Is a finance matter only", "Indicates a settlement"], 1,
   "Legitimate uses exist, and each should be explicable."),
 C("The most important payment-stage segregation is between:",
   ["Ordering and receiving", "Amending supplier bank details and releasing payments",
    "Invoicing and approving", "Receiving and invoicing"], 1,
   "If one person can do both, everything upstream is decoration.")]),

("Analytics across suppliers and buyers", 12, """<p>The nil-expected tests find specific broken relationships. Analytics finds the things that are not individually wrong but collectively worth explaining, and in procurement they mostly concern concentration.</p>

<p><b>Spend by supplier, ranked.</b> The starting point, and it produces more questions than it looks like. A supplier who has moved from twentieth to third in a year has a reason, and somebody should be able to state it. A long tail of suppliers used once or twice indicates buying outside whatever framework exists.</p>

<p><b>Spend by buyer.</b> Who is committing the business's money, and how much. Then the more interesting cut: <b>concentration within a buyer</b>. A buyer whose spend is spread across many suppliers is behaving differently from one whose spend is 80% with a single supplier — and the second is not wrong, but it is a relationship worth understanding, particularly if it has become more concentrated over time.</p>

<p><b>New suppliers by volume.</b> A supplier created recently and rapidly reaching significant volume is worth a look. Combine with the master-data tests: who created the record, what checks were done, and does anything connect it to staff.</p>

<p><b>Single-quote purchasing.</b> Where policy requires competitive quotes above a value, test whether more than one supplier was ever considered. In ERPNext this is visible where Request for Quotation and Supplier Quotation are used; where they are not used at all, the policy exists only on paper and that is the finding.</p>

<p><b>Order-to-receipt and receipt-to-invoice intervals.</b> Unusual speed is as informative as unusual delay. An order raised, received and invoiced within an hour was not a procurement process, it was paperwork constructed around a decision already taken — which may be an emergency purchase properly documented afterwards, or may be something else.</p>

<p><b>The limits of analytics here, stated plainly.</b> Unlike the till, procurement schemes are rare and large, so a ranked list will usually contain entirely legitimate businesses at the top. Concentration is normal in retail — you buy most of your soft drinks from one bottler. <b>Use analytics to generate questions, and expect most answers to be satisfactory.</b> An auditor who treats a ranking as a suspect list will be wrong repeatedly, in front of senior people, and will not be listened to when it matters.</p>

<blockquote>IMPLEMENTATION TIP: The most productive single analytic is spend concentration by buyer, tracked over time. A buyer whose supplier concentration is increasing year on year is a question worth asking, and the answer is usually about convenience rather than anything worse — but it is occasionally not.</blockquote>

<p><b>Compare buyers against each other on the same categories.</b> Where two people buy similar goods, differences in price achieved, supplier count and order frequency are informative in a way that a single buyer's numbers never are. The buyer paying consistently more for the same items may be less skilled, may be buying at short notice because of poor planning elsewhere, or may have a reason nobody has asked about. All three are worth knowing and only the comparison surfaces any of them.</p>"""
, [
 C("An order raised, received and invoiced within one hour indicates:",
   ["An efficient process", "Paperwork constructed around a decision already taken",
    "A system error", "A standing order"], 1,
   "Which may be a properly documented emergency, or may be something else."),
 C("Where RFQ and Supplier Quotation are never used despite a competitive-quote policy:",
   ["Test the quotes that exist", "The policy exists only on paper, and that is the finding",
    "Recommend more suppliers", "Check the value threshold"], 1,
   "Testing compliance with a control nobody operates produces nothing."),
 C("A ranked supplier concentration list will usually have at the top:",
   ["The riskiest relationships", "Entirely legitimate businesses",
    "Recently created suppliers", "Related parties"], 1,
   "Concentration is normal in retail; use analytics to generate questions and expect satisfactory answers.")]),

("The P2P tests, and investigating", 12, """<p>The working programme, and how a procurement investigation differs from the ones in modules 5 and 6.</p>

<p><b>Nil-expected tests.</b> Any row needs explaining.</p>

<p><b>Bank account changed then paid within the window.</b> <i>Innocent:</i> a genuine supplier bank change, which should be verifiable by calling a number you already hold — never one on the letter requesting the change.<br>
<b>Invoiced and not received, aged.</b> <i>Innocent:</i> services rather than goods, and prepayments.<br>
<b>Duplicate supplier bank details.</b> <i>Innocent:</i> a group of related companies sharing an account, which should be documented.<br>
<b>Payments with no invoice allocation.</b> <i>Innocent:</i> advances, which should clear.<br>
<b>Split orders below a limit.</b> <i>Innocent:</i> genuinely separate requirements arriving the same day, which is less common than people claim.</p>

<p><b>Analytical tests.</b> Price variance ranked by value, rate drift over time, spend concentration by buyer and supplier, exact-match receipt proportion by receiver, order-to-invoice intervals.</p>

<p><b>How a procurement investigation differs, and this is the important part.</b></p>

<p><b>The value is larger, so the standard of evidence is higher.</b> A ₦40m finding will be examined by people with an interest in its being wrong, and every step will be tested. Document as you go rather than assembling afterwards.</p>

<p><b>The people are more senior.</b> They may have influence over the audit function, access to the systems you are examining, and relationships with whoever you would escalate to. This is precisely why module 9's rule about telling the person your charter names — and specifically not the line manager — exists.</p>

<p><b>External parties are involved.</b> A supplier is not your colleague and cannot be approached informally. A call to a supplier to verify an invoice is an audit procedure with consequences: it may alert somebody, it may damage a commercial relationship, and it should be a decision rather than an impulse.</p>

<p><b>The paper trail extends outside the system.</b> Contracts, quotes, correspondence and delivery notes may exist only on paper or in email. The system tells you what was recorded; it does not tell you what was agreed. A finding that rests on the system alone can be answered with a document you never saw, and being answered that way once costs more credibility than the finding was worth.</p>

<p><b>Ask for the file before you conclude.</b> If a contract, quotation or approval exists outside the system, request it early and in writing, from somebody who is not the subject of the work. Two things follow: you either get the document, in which case your finding improves or dissolves before it is public, or you do not, and the absence of a document that should exist is itself part of the finding. Either outcome is better than being shown it in the meeting.</p>

<p><b>Where to start when something looks wrong.</b> Establish the full document chain for the transaction — order, receipt, invoice, payment, and the version history of each. Then the same chain for that supplier over twelve months. Most procurement schemes repeat, and the second instance is what turns an anomaly into a pattern you can quantify.</p>

<blockquote>WATCH-OUT: Do not contact a supplier during an exploratory phase. Suppliers talk to the buyers they deal with daily, and a single verification call has ended more procurement investigations than any other action. If external confirmation is needed, plan it as a deliberate step with somebody senior informed first.</blockquote>"""
, [
 C("A supplier writes requesting a bank account change. Verification should use:",
   ["The number on the letter", "A number you already hold from before the request",
    "Their email domain", "The buyer's contact"], 1,
   "The letter is exactly what would be forged, including its contact details."),
 C("Calling a supplier to verify an invoice during an exploratory phase:",
   ["Confirms the facts quickly", "Has ended more procurement investigations than any other action",
    "Is standard procedure", "Protects the relationship"], 1,
   "Suppliers talk to the buyers they deal with daily."),
 C("A finding resting only on system records can be answered by:",
   ["A different query", "A contract or email you never saw",
    "The approval history", "The version record"], 1,
   "The system tells you what was recorded, not what was agreed.")]),
]


QUESTIONS = [
 Q("Compared with till fraud, procurement schemes are:", ["Small and frequent", "Large and rare", "Equally distributed", "Easier to profile"], 1,
   "Which is why procurement work is mostly nil-expected population testing.", "Ch1 §7", "Where procurement leaks"),
 Q("A control failure in procure-to-pay usually appears as:", ["A missing document", "A broken relationship between documents", "An unusual approval", "A late payment"], 1,
   "Each document references the last, which makes the break queryable.", "Ch1 §6", "Where procurement leaks"),
 Q("The fastest and highest-value single procurement loss event is:", ["Paying twice", "Paying the wrong bank account", "Paying above agreed price", "Paying for goods not received"], 1,
   "A genuine invoice from a genuine supplier, paid to an account that is not theirs.", "Ch1 §5", "Where procurement leaks"),
 Q("Most procurement fraud is discovered:", ["By routine testing", "By accident", "By external audit", "At year end"], 1,
   "Which means found losses are a sample of those that occurred.", "Ch1 §8", "Where procurement leaks"),
 Q("The three documents of the three-way match are the purchase order, the invoice and:", ["The payment entry", "The purchase receipt", "The requisition", "The supplier quotation"], 1,
   "What was agreed, what arrived, what is being charged.", "Ch2 §2", "Three-way match"),
 Q("Before testing match exceptions you should measure:", ["Tolerance settings", "Match coverage — the proportion of invoices linked to a receipt", "Supplier count", "Approval rates"], 1,
   "If 30% reference no receipt, there is no three-way match to have exceptions to.", "Ch2 §5", "Three-way match"),
 Q("A 5% match tolerance on ₦2bn of purchasing represents:", ["An immaterial allowance", "₦100m of unchallenged variance", "A processing efficiency", "Standard practice"], 1,
   "The figure usually surprises the people who set it.", "Ch2 §8", "Three-way match"),
 Q("'Billed Items To Be Received' lists:", ["Goods received with no invoice", "Goods invoiced with no evidence of arrival", "Orders not yet received", "Invoices not yet paid"], 1,
   "The single most valuable standing report in the module.", "Ch2 §7", "Three-way match"),
 Q("Supplier banking details are held on:", ["The Supplier record directly", "A separate Bank Account record linked by party", "The Payment Entry", "The Purchase Invoice"], 1,
   "Supplier holds only default_bank_account as a link.", "Ch3 §2", "Supplier master data"),
 Q("Which fields on Bank Account carry the account itself?", ["account_name and bank", "iban and bank_account_no", "party and party_type", "is_default and company"], 1,
   "And the doctype tracks changes, which is what makes the test possible.", "Ch3 §2", "Supplier master data"),
 Q("Change the account, let a genuine invoice pay, change it back. This defeats:", ["Payment approval", "The three-way match entirely", "Duplicate detection", "Supplier vetting"], 1,
   "The invoice is real, the goods arrived, the approval was proper.", "Ch3 §4", "Supplier master data"),
 Q("The strongest signal of duplicate suppliers is:", ["Similar names", "Matching bank account numbers", "The same address", "Shared contacts"], 1,
   "Names are often similar innocently; bank details are not.", "Ch3 §6", "Supplier master data"),
 Q("A dormant supplier suddenly transacting is notable because dormant records:", ["Have stale prices", "Carry the legitimacy of history while nobody watches them", "Are usually duplicates", "Lack bank details"], 1,
   "Particularly where the record was edited shortly before.", "Ch3 §8", "Supplier master data"),
 Q("Approval limits are enforced by Workflow or by:", ["User Permission", "Authorization Rule", "Role Profile", "Naming Series"], 1,
   "Carrying a value, a basis, and the roles or users permitted to approve.", "Ch4 §2", "Approval limits"),
 Q("If no approval mechanism exists at all, you should:", ["Analyse buyer patterns", "Report the absence before analysing behaviour", "Recommend a threshold quietly", "Test the largest orders"], 1,
   "It outranks every pattern in the chapter.", "Ch4 §4", "Approval limits"),
 Q("Splitting is best detected by:", ["Sampling large orders", "Grouping orders by supplier and window and totalling", "Reviewing approvals", "Checking the histogram only"], 1,
   "A population test — sampling almost never finds it.", "Ch4 §6", "Approval limits"),
 Q("A cluster of values immediately below an approval threshold indicates:", ["Careful budgeting", "The limit is being worked around", "A pricing convention", "Supplier minimums"], 1,
   "The histogram shows it in thirty seconds without designing a test.", "Ch4 §7", "Approval limits"),
 Q("If a document can be approved then amended upward without re-approval:", ["Amendments should be monitored", "Every limit is advisory", "Approval should move to payment", "The workflow needs a state"], 1,
   "The approval attaches to a version that no longer exists.", "Ch4 §8", "Approval limits"),
 Q("Price variances should be ranked by:", ["Percentage", "Total naira value", "Supplier", "Frequency"], 1,
   "Percentage ranking buries the systematic overcharge on your largest line.", "Ch5 §3", "Price and rate testing"),
 Q("A rate rising 30% over a year in small steps is exposed by:", ["Invoice-by-invoice testing", "Plotting the rate series", "The three-way match", "Tolerance settings"], 1,
   "Every individual invoice passes tolerance.", "Ch5 §4", "Price and rate testing"),
 Q("Unclaimed volume rebates are common because claiming them is:", ["Technically difficult", "Nobody's actual job", "Contractually unclear", "Below materiality"], 1,
   "Pure loss, and recoverable once identified.", "Ch5 §5", "Price and rate testing"),
 Q("Price findings are easier to get acted on because they are:", ["Larger", "Commercially useful rather than accusatory", "Simpler to prove", "Owned by finance"], 1,
   "They build the standing you need for harder findings later.", "Ch5 §8", "Price and rate testing"),
 Q("A receiver whose quantities always match the order exactly is:", ["Highly accurate", "Copying rather than counting", "Working with a reliable supplier", "Following procedure"], 1,
   "Real deliveries are occasionally short, damaged or over.", "Ch6 §4", "Receiving"),
 Q("A receipt created after the invoice is often created:", ["To correct cut-off", "To match the invoice rather than record an arrival", "By a central user", "For reporting"], 1,
   "Compare creation timestamps, not posting dates.", "Ch6 §5", "Receiving"),
 Q("From system data alone you cannot establish:", ["Who created a receipt", "That goods physically arrived", "Whether it matched the order", "When it was created"], 1,
   "Which is why occasional physical verification matters.", "Ch6 §8", "Receiving"),
 Q("The most important procurement segregation is between:", ["Invoicing and payment", "Ordering and receiving", "Receiving and counting", "Approval and payment"], 1,
   "That combination permits payment for goods that never came.", "Ch6 §7", "Receiving"),
 Q("Goods invoiced and receipted but never delivered surface later as:", ["A payment variance", "Shrinkage at the next count", "A duplicate invoice", "A price variance"], 1,
   "Which is the corroboration between this module and inventory.", "Ch6 §9", "Receiving"),
 Q("A Payment Entry with no invoice allocation is:", ["A normal advance", "Paying somebody for nothing recorded, and advances should be a small monitored population", "A journal", "A prepayment only"], 1,
   "Legitimate advances exist and should clear.", "Ch7 §2", "Payment controls"),
 Q("Which test's detection interval determines whether money is recoverable?", ["Duplicate payments", "Bank change then payment", "Price variance", "Match coverage"], 1,
   "Run it weekly rather than monthly.", "Ch7 §9", "Payment controls"),
 Q("A supplier balance moved by journal entry:", ["Is a routine correction", "Bypasses the whole purchase-to-pay process", "Requires no approval", "Affects only reporting"], 1,
   "Each instance should be explicable.", "Ch7 §6", "Payment controls"),
 Q("The critical payment-stage segregation separates releasing payments from:", ["Raising orders", "Amending supplier bank details", "Receiving goods", "Approving invoices"], 1,
   "If one person can do both, everything upstream is decoration.", "Ch7 §7", "Payment controls"),
 Q("Finding recoverable duplicate payments is valuable to a new audit function because it:", ["Is easy", "Demonstrates the function pays for itself", "Avoids conflict", "Requires no access"], 1,
   "Almost always error, frequently recoverable.", "Ch7 §4", "Payment controls"),
 Q("The most productive single procurement analytic is:", ["Spend by supplier", "Spend concentration by buyer over time", "Order count by month", "Average order value"], 1,
   "The answer is usually convenience, and occasionally not.", "Ch8 §9", "Supplier and buyer analytics"),
 Q("An order raised, received and invoiced within an hour is:", ["Efficient", "Paperwork built around a decision already taken", "A standing order", "A system artefact"], 1,
   "Which may be a documented emergency, or may not.", "Ch8 §6", "Supplier and buyer analytics"),
 Q("Where RFQ and Supplier Quotation are never used despite policy:", ["Test the exceptions", "The policy exists only on paper, and that is the finding", "Sample the largest", "Recommend training"], 1,
   "Testing compliance with a control nobody operates produces nothing.", "Ch8 §5", "Supplier and buyer analytics"),
 Q("A ranked concentration list in retail will usually be topped by:", ["Related parties", "Entirely legitimate businesses", "New suppliers", "Single-quote purchases"], 1,
   "Use analytics to generate questions and expect satisfactory answers.", "Ch8 §7", "Supplier and buyer analytics"),
 Q("Verification of a bank change request should use:", ["The number on the request letter", "A number held before the request was made", "The supplier's website", "The buyer's contact"], 1,
   "The letter is exactly what would be forged, including its contact details.", "Ch9 §3", "P2P investigation"),
 Q("Contacting a supplier during an exploratory phase:", ["Confirms facts efficiently", "Has ended more procurement investigations than any other action", "Is required for evidence", "Preserves the relationship"], 1,
   "Suppliers talk to the buyers they deal with daily.", "Ch9 §9", "P2P investigation"),
 Q("A finding resting only on system records may be answered by:", ["A better query", "A contract or email you never saw", "The approval log", "Version history"], 1,
   "The system records what was entered, not what was agreed.", "Ch9 §8", "P2P investigation"),
 Q("Procurement findings need a higher evidence standard mainly because:", ["Values are larger and will be examined by people with an interest in their being wrong", "Data is less reliable", "Suppliers are external", "Approvals are complex"], 0,
   "Document as you go rather than assembling afterwards.", "Ch9 §5", "P2P investigation"),
 Q("Having found one suspicious transaction, the next step is:", ["Interview the buyer", "Build the same document chain for that supplier over twelve months", "Contact the supplier", "Raise the finding"], 1,
   "Most procurement schemes repeat, and the second instance makes it a pattern.", "Ch9 §10", "P2P investigation"),
 Q("An innocent explanation for split orders is:", ["Budget management", "Genuinely separate requirements arriving the same day", "Supplier minimums", "System limitations"], 1,
   "Less common than people claim, and it must be stated before the test is deployed.", "Ch9 §4", "P2P investigation"),
 Q("Duplicate supplier bank details may innocently indicate:", ["A data error", "A group of related companies sharing an account", "A dormant record", "A migration artefact"], 1,
   "Which should be documented rather than assumed.", "Ch9 §4", "P2P investigation"),
]


def rebalance(items, seed):
    n = len(items)
    base, extra = divmod(n, 4)
    slots = []
    for i in range(4):
        slots += [i] * (base + (1 if i < extra else 0))
    random.Random(seed).shuffle(slots)
    for it, target in zip(items, slots):
        cur = it["ans"]
        if cur == target:
            continue
        shift = (target - cur) % 4
        it["opts"] = it["opts"][-shift:] + it["opts"][:-shift]
        it["ans"] = target
    return items


def main():
    rebalance(QUESTIONS, "control:procure_pay:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:procure_pay:checks")

    mod = {
        "title": "Procure to Pay",
        "desc": ("The largest outflow, and unattended. Match coverage before match "
                 "exceptions, suppliers as standing instructions to pay, the bank-change "
                 "test that defeats the three-way match, orders split below a limit, "
                 "prices paid against prices agreed, the receiving bay as the highest-risk "
                 "point, and why a single call to a supplier ends more investigations than "
                 "anything else."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    path = "academy_control_data.json"
    data = {}
    if os.path.exists(path):
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
    data[KEY] = mod
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("modules in file: %s" % ", ".join(sorted(data)))
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    for l, n in zip(mod["lessons"], lens):
        print("   %-54s %5d" % (l["title"][:54], n))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("\nquestions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("topics:", dict(collections.Counter(q["topic"] for q in QUESTIONS)))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
