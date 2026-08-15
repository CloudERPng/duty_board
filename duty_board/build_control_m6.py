#!/usr/bin/env python3
"""Build 'Revenue and the Point of Sale' into academy_control_data.json.

Module 6 of System-Based Internal Control in a Retail Environment, and the
commercial heart of the track — point-of-sale abuse is where Nigerian retail
actually loses money, and every technique has a signature in the data.

Field names verified from ERPNext v15 source: is_pos, is_return, return_against,
amended_from, is_consolidated, pos_profile on Sales Invoice; POS Opening Entry
and POS Closing Entry with their payment_reconciliation child tables. Not
recalled — read.

Builds on module 2 rather than repeating it: docstatus, version history and the
parent/child split are assumed known and used.

Run from the app package directory:  python3 build_control_m6.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "revenue_pos"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("How till behaviour appears in the ledger", 12, """<p>ZhiftPOS is a point-of-sale interface over the same ERPNext backend. There is no separate POS database, no nightly interface, and therefore no reconciliation between two systems to perform.</p>

<p><b>That absence is worth stating plainly to anyone arriving from another environment.</b> In a retailer running a standalone till system feeding a separate ERP, the POS-to-ledger reconciliation is a week of work and one of the highest-risk areas on the plan — records can disagree, and the gap is where losses hide. Here the till writes the ledger directly. The reconciliation cannot fail because there is nothing to reconcile, and that week is available for better work.</p>

<p><b>What a sale actually becomes.</b> A till transaction is a <b>Sales Invoice</b> with <code>is_pos</code> set, carrying a <code>pos_profile</code> that identifies the till configuration, an <code>owner</code> identifying the cashier, and a posting date and time. Its lines sit in the child table with quantity, rate, and any discount. Payment creates the corresponding entries, and stock moves through the stock ledger.</p>

<p>So every question you might ask about till behaviour is a question about Sales Invoices and their children, answerable with the techniques from module 2.</p>

<p><b>The four events worth naming now</b>, because the rest of the module examines each in turn.</p>

<p><b>A void</b> is a submitted invoice cancelled and, usually, amended — <code>docstatus</code> 2 with a successor carrying <code>amended_from</code>.<br>
<b>A refund</b> is a Sales Invoice with <code>is_return</code> set, pointing at the original through <code>return_against</code>.<br>
<b>A discount</b> is a field on the invoice line.<br>
<b>An override</b> is a permission exercised, recorded against a user.</p>

<p><b>One structural warning that will otherwise distort every count you produce.</b> Where POS invoices are consolidated, individual transactions carry <code>is_consolidated</code> and a merged document is created behind them. Counting without regard to that flag will double-count revenue, once at transaction level and once consolidated. Establish how your business is configured before your first test, because a revenue figure double the truth is the kind of error that ends a conversation early.</p>

<p><b>Where the shift structure lives.</b> POS Opening Entry and POS Closing Entry bracket a cashier's session, carrying the user, the profile, the period, and a payment reconciliation table comparing expected against counted by payment mode. That pair is the spine of cash testing and it is examined in chapter five.</p>

<p><b>The consequence for your programme.</b> Because everything lands in one place, the techniques transfer. The query pattern that profiles voids by cashier profiles credit notes by sales officer, or adjustments by storekeeper, with the doctype changed and nothing else. Learn it once here and it serves every module that follows.</p>

<blockquote>WATCH-OUT: Establish your consolidation setting before running anything. It is a five-minute check and it determines whether every revenue number you produce for the rest of the year is right or double.</blockquote>

<p><b>One more configuration question worth settling on day one.</b> Whether cancelled invoices are permitted at all, and if so by whom. Some retailers disable cancellation for cashiers entirely and require a supervisor; others allow it freely because the queue is long and the customer is waiting. Neither is wrong, but they produce completely different populations — and a void test designed for one configuration is meaningless under the other. Ask before you build.</p>"""
, [
 C("A colleague proposes a POS-to-ERP reconciliation as a priority for the audit plan. The correct response is:",
   ["Agree — it is high risk", "There is no reconciliation to perform; the till writes the ledger directly",
    "Defer it to the external auditor", "Sample it quarterly"], 1,
   "That week of work is available for better things, and the absence of the risk is worth stating in the plan."),
 C("Your revenue figure comes out at roughly twice the expected value. Check first:",
   ["The date field used", "Whether consolidated POS invoices are being counted alongside the individual ones",
    "The branch filter", "Whether returns were excluded"], 1,
   "is_consolidated distinguishes them, and counting both double-counts every sale."),
 C("A refund is distinguished from an ordinary sale in the data by:",
   ["A negative grand total alone", "is_return being set, with return_against naming the original",
    "docstatus 2", "A separate doctype"], 1,
   "And a refund where return_against is empty is one of the strongest signals in this module.")]),

("Voids: what a cancellation leaves behind", 12, """<p>A void is the most abused transaction type in retail, and in a system environment it is also among the most traceable. Understanding exactly what it leaves behind is what separates a useful test from a suspicion.</p>

<p><b>What actually happens.</b> A submitted invoice cannot be edited. To correct it, the cashier cancels it — <code>docstatus</code> becomes 2 — and creates an amendment, a new document carrying <code>amended_from</code> pointing at the cancelled one. The platform compares the two and records the difference in the version history.</p>

<p>So a void leaves four things: the original with its lines and value, the cancellation with its timestamp and user, the replacement, and a field-level record of what changed between them.</p>

<p><b>Why that matters for the classic scheme.</b> The oldest till fraud is simple: complete a sale, take the customer's cash, then void the transaction and keep the money. The stock is gone, the cash is gone, and the record shows no sale.</p>

<p>Except it does not. It shows a cancelled invoice, timed, attributed, with its contents intact — and the absence of a replacement. <b>A cancellation with no amendment is the shape to look for</b>, because a genuine correction produces a replacement and a theft does not.</p>

<p><b>What innocent voids look like</b>, because you must be able to tell them apart before you deploy any test. A customer changes their mind at the counter. A wrong item is scanned and the whole sale restarted. A payment method fails. A price is queried and corrected. All of these are common, all produce cancellations, and most produce a replacement within a short window.</p>

<p><b>So the test is not "who voids" but the shape of the voiding.</b> Four signals, and the combination matters more than any one:</p>

<p><b>Rate</b> — voids as a share of that cashier's transactions, against the estate distribution rather than against a fixed threshold.<br>
<b>Orphan cancellations</b> — cancelled with no amendment following.<br>
<b>Value</b> — whether voids cluster at the high end of that cashier's normal transaction size.<br>
<b>Timing</b> — concentration near shift end, or outside the busy periods that would explain error.</p>

<p><b>The stock consequence, which is the corroborating evidence.</b> A voided sale returns stock to the ledger. If the goods physically left the shop, the system now believes stock exists that does not, and the difference emerges at the next count as shrinkage attributed to nobody. <b>A branch with an elevated void rate and elevated shrinkage is a far stronger finding than either alone</b>, and the two are usually examined by different people who never compare notes.</p>

<blockquote>IMPLEMENTATION TIP: Run the void rate by cashier monthly and keep the series. A cashier who moves from the middle of the distribution to the top over three months is a better signal than one who has always been slightly high, and only a series shows it.</blockquote>

<p><b>A note on what a high void rate usually turns out to be.</b> In most investigations it is a training problem or a hardware one — a scanner that misreads, a new cashier restarting sales rather than correcting lines, a till whose card terminal times out. Those explanations are common, checkable, and worth eliminating first, because eliminating them is quick and because raising a fraud concern that turns out to be a faulty scanner damages your standing for a year. Investigate the equipment before the person.</p>"""
, [
 C("A cancelled invoice with no amendment following it is significant because:",
   ["Cancellations are always suspicious", "A genuine correction produces a replacement; a theft does not",
    "It breaches document numbering", "It indicates a system error"], 1,
   "The shape of the voiding matters more than the fact of it."),
 C("A voided sale where the goods physically left the shop causes:",
   ["An immediate cash variance", "The system to believe stock exists that does not, surfacing later as unattributed shrinkage",
    "A negative stock entry", "A price variance"], 1,
   "Which is why elevated voids and elevated shrinkage together are far stronger than either alone."),
 C("Judging a cashier's void rate against a fixed threshold rather than the estate distribution:",
   ["Is more objective", "Ignores what normal looks like in your business and for that branch type",
    "Reduces false positives", "Is required for consistency"], 1,
   "The distribution tells you what normal is; a fixed number is somebody's guess.")]),

("Refunds and credit notes", 12, """<p>A refund moves cash out of the business on the strength of a claim that goods came back. It is therefore the transaction with the shortest path between a keystroke and money leaving, and it deserves proportionate attention.</p>

<p><b>How it is recorded.</b> A return is a Sales Invoice with <code>is_return</code> set and <code>return_against</code> naming the original invoice. Quantities and values are negative. Stock returns to the ledger, and cash or a credit leaves.</p>

<p><b>The first and best test: refunds against nothing.</b> Where <code>return_against</code> is empty, or names a document that does not exist or does not correspond, there is no original sale being reversed. Some configurations permit this legitimately — a goodwill credit, a customer without a receipt — but each instance should be explicable, and the population is usually small enough to examine in full.</p>

<p>This is a <b>nil-expected test</b> in most retailers, and any row is a finding rather than a data point.</p>

<p><b>The second test: refunds where the goods did not come back.</b> A return posts stock inward. If the stock never physically arrived, the count will eventually disagree — the same corroboration as with voids. Refunds concentrated on a cashier, combined with shrinkage in the categories they refunded, is a pattern worth pursuing carefully.</p>

<p><b>The third: timing relative to the original.</b> A refund minutes after the sale, on the same till, is a different event from one three weeks later at another branch. Very short intervals suggest the sale was never real; very long ones against a stated policy period suggest the policy is not being applied. Both are testable with date arithmetic between the return and its original.</p>

<p><b>Credit notes on the trade side</b> deserve the same treatment and usually receive less. A credit note reduces what a customer owes, which is economically identical to a payment out — and it is typically raised by somebody in sales rather than at a till, with less supervision. Group them by <code>owner</code>, by customer, and by value, and ask what proportion of each salesperson's revenue is subsequently credited. That ratio varies far more between people than most businesses expect.</p>

<p><b>What innocent looks like.</b> Damaged goods, wrong size, a genuine change of mind within policy, a pricing error corrected in the customer's favour. All routine. The signal is not the existence of refunds but their concentration, their relationship to originals, and whether the stock came back.</p>

<blockquote>WATCH-OUT: Refund authority is frequently granted broadly because refusing customers is uncomfortable and supervisors are busy. Check who actually holds it against who is supposed to — the gap between the policy and the permission list is often wide, and it is the control that matters rather than the policy.</blockquote>

<p><b>The refund method matters as much as the refund.</b> A return refunded in cash is a different risk from one credited to the original card or issued as store credit, because only the first puts notes in somebody's hand. Where your system records the mode, test refunds by method: a cashier whose returns are refunded in cash at a rate well above their peers is worth understanding even where the total refund rate looks ordinary. It is a second dimension most refund testing never uses.</p>"""
, [
 C("A refund where return_against is empty should be treated as:",
   ["Normal for walk-in customers", "A nil-expected finding requiring explanation in every instance",
    "A data quality issue", "Immaterial below a value threshold"], 1,
   "Some configurations permit it legitimately, but each instance should be explicable and the population is small."),
 C("A refund posted three minutes after the original sale on the same till suggests:",
   ["An efficient correction", "The sale may never have been real",
    "A payment method failure", "A pricing error"], 1,
   "Very short intervals and very long ones are both testable with date arithmetic against the original."),
 C("Credit notes on the trade side warrant equal attention to till refunds because:",
   ["They are larger", "They are economically identical to a payment out, and usually less supervised",
    "They affect VAT", "They require approval"], 1,
   "Raised by sales rather than at a till, and the credit-to-revenue ratio varies far more between people than expected.")]),

("Discounts and overrides", 12, """<p>A discount is the quietest way to move value out of a business. Nothing is voided, nothing is refunded, the transaction looks entirely ordinary — and the margin is simply lower.</p>

<p><b>Where it lives.</b> On the invoice line: <code>discount_percentage</code> and <code>discount_amount</code>, against <code>price_list_rate</code> and the final <code>rate</code>. Because it is a line-level field, discount testing must query the child table, and a document-level view will miss it entirely.</p>

<p><b>The shipped test worth adopting immediately.</b> ERPNext ships <i>Calculated Discount Mismatch</i>, which finds lines where the discount recorded does not agree with the arithmetic of price list rate against final rate. Hits indicate either a defect or a manipulation, and either way the line does not say what it appears to say. It costs nothing to run and almost nobody runs it.</p>

<p><b>The analytical tests.</b> Discount as a share of revenue, grouped by user, by branch, and by customer. What you are looking for is concentration: one cashier discounting at three times the branch norm, one customer receiving discounts nobody authorised, one branch systematically softer than the estate.</p>

<p><b>The scheme to understand.</b> A cashier applies a discount the customer never asked for and never received, collecting full price and keeping the difference. The transaction reconciles perfectly — the invoice says ₦8,000, the till holds ₦8,000, stock moved for ₦8,000 — and the business has lost the ₦2,000 of margin between the price list and the rate charged. <b>No cash variance is ever produced</b>, which is precisely why it survives the controls most retailers rely on.</p>

<p>It is detectable only by looking at the discount pattern itself, which is why this chapter exists.</p>

<p><b>Overrides are the adjacent problem.</b> Where a price or discount exceeds what a cashier may grant, a supervisor authorises it. Two things to test: whether the authority is exercised by the person it belongs to, and whether it is exercised so routinely that it has stopped being a control. A supervisor override happening two hundred times a month is not an exception process; it is the normal process with an extra step, and it should be reported as a control that has ceased to function rather than as a list of instances.</p>

<p><b>Where the authorisation lives.</b> Depending on configuration, either a Workflow with states and transitions, or an Authorization Rule enforcing a value threshold by role or user. Establish which mechanism your business uses before designing the test — and if the answer is neither, that is itself the finding, and a more important one than any pattern you would have found.</p>

<blockquote>IMPLEMENTATION TIP: Compare each cashier's average discount percentage against their branch, and each branch against the estate. Two comparisons, one query, and it surfaces both the individual outlier and the branch where the norm itself has drifted.</blockquote>

<p><b>Watch the customer side too.</b> Discounts concentrated on particular customer accounts — especially accounts created recently, or with sparse details, or sharing a phone number with a member of staff — are worth a look. The scheme is straightforward: a discount granted to a related party at the counter, repeatedly, in modest amounts. Grouping discount value by customer and sorting is one query, and in most retailers nobody has ever run it.</p>"""
, [
 C("A cashier applies an unrequested discount and pockets the difference. The control that fails to detect it is:",
   ["Stock counting", "Cash reconciliation — no variance is ever produced",
    "Version history", "Supervisor override"], 1,
   "The invoice, the till and the stock movement all agree; only the discount pattern reveals it."),
 C("Discount testing must query the child table because:",
   ["Parent totals are rounded", "Discount is a line-level field and a document view misses it entirely",
    "Consolidation hides it", "Returns distort the parent"], 1,
   "discount_percentage and discount_amount sit on the invoice line against price_list_rate and rate."),
 C("Supervisor overrides occurring two hundred times a month should be reported as:",
   ["A list of instances for investigation", "A control that has ceased to function",
    "Evidence of active supervision", "A training requirement"], 1,
   "It is the normal process with an extra step rather than an exception process.")]),

("Cash, payment modes and the shift", 12, """<p>Cash testing in this environment is not about counting money — that is the branch's job. It is about whether the record of the shift supports the cash that reached the bank, and where the two diverge.</p>

<p><b>The shift structure.</b> A POS Opening Entry records the cashier, the profile, the period and the opening balance by payment mode. A POS Closing Entry closes it, carrying a payment reconciliation table comparing expected against counted for each mode. The pair defines a session, and the reconciliation table is where variance is recorded rather than inferred.</p>

<p><b>Four tests that follow directly.</b></p>

<p><b>Variance by cashier and by shift</b>, from the closing entry. Both directions: an over is as informative as a short, because a process producing random overs produces shorts too, and a persistent small over can be a float built to cover a later shortfall.</p>

<p><b>Sessions closed without a reconciliation</b>, or closed by somebody other than the cashier who opened them. Both are control breakdowns regardless of whether money is missing.</p>

<p><b>Payment mode mix by cashier.</b> Where takings are split between cash, card and transfer, a cashier whose cash share differs materially from their peers on similar trade is worth understanding. Cash is the only mode that can be taken.</p>

<p><b>Days to bank.</b> The interval between the shift date and the corresponding bank receipt. This is the test that exposes lapping — takings banked late, with today's receipts covering yesterday's shortfall, rolling forward. Every individual day reconciles under lapping and the books balance; the delay is the only visible sign.</p>

<p><b>Why days-to-bank deserves particular emphasis.</b> It is a control measure that behaves like an operational metric, so it is rarely owned by anybody. Operations sees a logistics matter, finance sees a treasury matter, and neither treats it as fraud detection. Measure it per branch, monthly, and rank — a branch consistently two days slower than the estate has either a routing problem or something else, and the two are distinguishable by looking.</p>

<p><b>The corroboration to build.</b> Cash variance alone is noisy; every busy till produces small differences. Variance combined with elevated voids, elevated discounts, or slow banking at the same branch and the same shift is a pattern. <b>Single indicators mislead in cash work more than anywhere else in this track</b>, and the discipline of requiring two before acting will save you from most of the wrong conversations.</p>

<p><b>Where the banking data actually comes from.</b> The bank side is a Payment Entry or a bank reconciliation record; the shift side is the closing entry. Joining them produces days-to-bank, and the join is the fiddly part, because the reference between them depends on how your business records lodgements. Establish that mapping once and the query serves permanently — it is the single most valuable half-day of query work in this module.</p>

<blockquote>WATCH-OUT: A branch with no variances at all, month after month, is not necessarily well run. It can equally mean the count is being made to agree with the system rather than the money being counted independently. Perfect reconciliation deserves the same curiosity as a persistent difference.</blockquote>"""
, [
 C("A till shows a persistent small OVER each shift. This is:",
   ["A good problem", "As informative as a short — possibly a float being built to cover a later shortfall",
    "Immaterial", "Evidence of careful cashiering"], 1,
   "A process producing random overs produces shorts too."),
 C("Which measure exposes lapping, where late banking is covered by later receipts?",
   ["Till variance by shift", "Days between the shift date and the bank receipt",
    "Payment mode mix", "Void rate"], 1,
   "Every individual day reconciles under lapping; the delay is the only visible sign."),
 C("A branch reporting no cash variance at all for six months should prompt:",
   ["Recognition of good practice", "The same curiosity as a persistent difference — the count may be made to agree",
    "A reduction in oversight", "A wider tolerance"], 1,
   "Independent counting produces small differences; perfect agreement suggests the count is not independent.")]),

("Profiling a cashier", 12, """<p>Everything so far tests one behaviour at a time. Profiling combines them, and it is where system-based revenue audit produces findings that no amount of observation would reach.</p>

<p><b>The six measures, all from data already discussed.</b> Void rate. Refund rate. Average discount percentage. Cash variance, both directions. Days to bank where the cashier handles it. Transaction value distribution — because a cashier whose transactions cluster unusually low or high is worth understanding.</p>

<p><b>Normalise, always.</b> Raw counts rank by hours worked and till busyness. Every measure must be per transaction, per naira of takings, or per shift. An unnormalised profile identifies your hardest-working cashier as your biggest risk, and somebody will act on it.</p>

<p><b>Compare against the right population.</b> A cashier at a high-traffic branch is not comparable to one at a quiet suburban store; a fuel-forecourt till is not a supermarket checkout. Compare within branch first, then within branch type, then across the estate — and treat a difference that survives all three as worth investigating.</p>

<p><b>What a profile is and is not.</b> It is a ranking that tells you where to look. It is not evidence, it does not accuse anybody, and it should never be described as identifying suspects. The single most damaging thing an internal auditor can do with this technique is present a ranked list to management as though position implied wrongdoing — because somebody will be at the top of any list, and the top of a list of entirely honest people is still somebody.</p>

<p><b>The combination that actually matters.</b> One measure at the top of a distribution is noise. Two or three, at the same branch, over consecutive months, is a pattern. High voids alone means little; high voids with high discounts and slow banking in the same shift is a specific thing to go and look at.</p>

<p><b>Watch movement, not position.</b> A cashier who has always been slightly above average is probably a characteristic of how they work. One who has moved from the middle of the distribution to the top over four months has changed something, and change is what you are actually looking for. This requires keeping the series, which is the single most common thing audit functions fail to do — the profile is run, discussed, and not retained, so next month starts from nothing.</p>

<blockquote>IMPLEMENTATION TIP: Retain the monthly profile. It takes no effort and it converts a snapshot into a trend, which is the difference between noticing somebody is unusual and noticing somebody has become unusual. Only the second is a finding.</blockquote>

<p><b>And a word about how profiling is received.</b> Staff find out, and the way they find out shapes whether the technique survives. A profile discovered through a disciplinary conversation feels like surveillance; the same profile explained openly — that the business monitors patterns, that being at the top of a list is not an accusation, and that the purpose is protecting honest staff from suspicion — is usually accepted. The second framing is also true, which makes it easier to say.</p>"""
, [
 C("A ranked cashier profile is presented to management. The correct framing is:",
   ["These are the suspects", "This is where to look — position implies nothing on its own",
    "These require disciplinary action", "This is evidence of loss"], 1,
   "Somebody is at the top of any list, and the top of a list of honest people is still somebody."),
 C("An unnormalised profile will typically identify as highest risk:",
   ["The newest cashier", "The busiest cashier", "The part-time staff", "The supervisor"], 1,
   "Raw counts rank by hours worked and till busyness, and somebody will act on it."),
 C("Which is the stronger signal?",
   ["A cashier who has always been slightly above average", "A cashier who moved from mid-distribution to the top over four months",
    "The highest single-month void rate", "The largest transaction value"], 1,
   "Change is what you are looking for, and only a retained series shows it.")]),

("Reading a distribution across branches", 12, """<p>A single branch produces a number with nothing to compare it to. Twenty branches produce a distribution, and that is an analytical advantage an external auditor visiting one location does not have. It is the technique to use hardest, and the one most internal audit functions never adopt.</p>

<p><b>What a distribution tells you that a threshold cannot.</b> A void rate of 3% means nothing in isolation. Against an estate where the mean is 1.2% and the standard deviation is 0.4%, it is more than four standard deviations out — and that is a fact about the business rather than a judgement about a number somebody chose.</p>

<p>Thresholds are guesses that age badly. Distributions adjust themselves as the business changes, which means a programme built on them needs less maintenance and produces fewer arguments.</p>

<p><b>How to build one properly.</b> Take the measure, normalise it, compute the estate mean and standard deviation, and rank. Flag beyond a chosen sigma. Two sigma catches roughly one branch in twenty by chance alone, so in a twenty-branch estate expect one false flag every time — which is why three sigma is usually the better working threshold, and why any flag needs a second measure before it becomes a finding.</p>

<p><b>Adjust for what genuinely differs.</b> Branch format, trade mix, customer type, opening hours. A forecourt store and a mall unit have different void rates for entirely innocent reasons. If a factor explains a difference and applies to several branches, group and compare within the group — the outlier that survives grouping is the interesting one.</p>

<p><b>Trend beats level, and this is worth insisting on.</b> A branch at the estate average but deteriorating for four consecutive months is a more useful finding than one that has always been high. The first is a change with a cause you might still identify; the second is probably a characteristic of the location and has likely already been discussed several times without resolution.</p>

<p><b>The rank-across-measures view.</b> Rank every branch on each of your six measures, then look at which branches appear in the worst quartile on three or more. That composite is the most useful single page an internal audit function can produce, and it takes one query per measure plus a sort. It answers the question the audit committee actually asks — where should we be worried — without pretending to answer the one they sometimes ask, which is who is stealing.</p>

<blockquote>IMPLEMENTATION TIP: Build the composite ranking once and run it monthly. Three or four branches will appear in the worst quartile repeatedly. That short list, rather than the annual visit rota, should be driving where your fieldwork goes.</blockquote>

<p><b>The obvious objection, and the answer to it.</b> Somebody will say that ranking branches is unfair because circumstances differ. They are right, and it is why you group by format and compare within type before ranking across the estate. But the objection is often really an argument that no comparison is possible at all, and that is not right — it is an argument for a better comparison. Concede the adjustment and hold the method, because a business that cannot compare its own branches cannot manage them either.</p>"""
, [
 C("A branch shows a 3% void rate. To know whether that matters you need:",
   ["An industry benchmark", "The estate mean and standard deviation",
    "Last year's figure", "The branch manager's explanation"], 1,
   "A threshold is somebody's guess; a distribution is a fact about your business."),
 C("Flagging at two standard deviations in a twenty-branch estate will:",
   ["Catch only genuine outliers", "Produce roughly one false flag every run by chance alone",
    "Miss most outliers", "Require no second measure"], 1,
   "Which is why three sigma is usually the better working threshold."),
 C("A forecourt store and a mall unit show different void rates. You should:",
   ["Treat the difference as a finding", "Group by format and compare within the group",
    "Use a single estate threshold", "Exclude the forecourt"], 1,
   "The outlier that survives grouping is the interesting one.")]),

("The tests, and what innocent looks like", 12, """<p>This chapter is the working programme: the revenue tests worth running, with the interpretation that keeps each one usable. Every test carries an innocent explanation, and a test deployed without one will be ignored within two months.</p>

<p><b>Nil-expected tests.</b> Any row is a finding.</p>

<p><b>Refunds against no original.</b> <code>is_return</code> set with <code>return_against</code> empty or unmatched. <i>Innocent:</i> configured goodwill credits, if your business permits them — which should be a named, small population.</p>

<p><b>Cancellations with no amendment.</b> Voided and never replaced. <i>Innocent:</i> a customer who abandoned the purchase entirely; expect a modest steady rate and investigate concentration rather than instances.</p>

<p><b>Discount mismatch.</b> The shipped report. <i>Innocent:</i> rounding on unusual unit conversions, and legacy documents from before a configuration change.</p>

<p><b>Sales posted outside trading hours.</b> <i>Innocent:</i> genuine late trading, stocktake adjustments posted by a manager, and time zone or clock configuration — check that before anything else.</p>

<p><b>Analytical tests.</b> Rows are always returned; the distribution is the question.</p>

<p><b>Void rate, refund rate, average discount, cash variance, days to bank</b>, each by cashier and by branch, ranked and normalised. <i>Innocent:</i> new staff learning, a branch with a returns-heavy category, a promotion period, a till with a hardware fault causing repeated re-scans.</p>

<p><b>Timing tests.</b> Refunds within minutes of the original; voids concentrated in the final hour of a shift; transactions clustered immediately below an override threshold. <i>Innocent:</i> shift-end tidying of genuine errors, and the last-hour rush at a branch whose trade is genuinely evening-weighted.</p>

<p><b>Designing the threshold.</b> Start deliberately loose, run in silence for a month, and look at what actually comes back. You will find more than you expected, almost always. Tune until the population is small enough that somebody will genuinely examine every row — because a test producing forty hits a month produces zero investigations, and one producing three produces three.</p>

<p><b>The discipline that keeps the programme alive.</b> Write the innocent explanation before deployment, not after the first argument. If you cannot describe what an innocent hit looks like, you do not yet understand the population well enough to interpret the guilty one — and the test will be dismissed the first time somebody produces a reasonable explanation you had not anticipated.</p>

<blockquote>WATCH-OUT: Never deploy a new revenue test straight into the live programme. Run it privately for a month first. Releasing an untuned test generates a wave of hits, exhausts the goodwill of whoever must investigate them, and quietly kills the credibility of every test that follows it.</blockquote>

<p><b>How many tests is enough.</b> Fewer than you think. Six to eight revenue tests, tuned, reviewed monthly and actually investigated, will find more than thirty tests producing output nobody reads. The temptation when building a programme is comprehensiveness, and comprehensiveness is precisely what causes the output to be ignored. Start with the four nil-expected tests and two analytical ones, run them properly for a quarter, and add only when the existing set is genuinely being worked.</p>"""
, [
 C("A new void test returns forty hits in its first month. The right response is:",
   ["Investigate all forty", "Tune the threshold until the population is small enough that every row is genuinely examined",
    "Raise a systemic finding", "Widen it to other branches"], 1,
   "A test producing forty hits a month produces zero investigations."),
 C("Sales appearing outside trading hours should first be checked against:",
   ["The rota", "Clock and time zone configuration",
    "The branch manager's account", "The stock ledger"], 1,
   "Configuration explains this far more often than behaviour does."),
 C("Writing the innocent explanation before deployment matters because:",
   ["It documents the test", "Without it the test is dismissed the first time somebody offers a reasonable explanation you had not anticipated",
    "It sets the severity", "It satisfies the review process"], 1,
   "If you cannot describe an innocent hit, you do not understand the population well enough to interpret a guilty one.")]),

("Investigating a revenue exception", 12, """<p>A test has produced a hit worth pursuing. What happens next determines whether you end with a finding, a dismissal, or a destroyed case — and most of it is decided in the first hour.</p>

<p><b>Establish the facts from the data before speaking to anyone.</b> The document and its version history. The surrounding transactions on that till and shift. The stock consequence. The cash consequence. Whether it is isolated or one of a series by the same person. All of this is available without alerting anybody, and going into a conversation already knowing it changes the conversation entirely.</p>

<p><b>Build the corroboration.</b> A single anomalous transaction is almost always explicable. What makes a finding is the combination: the void, the missing stock at the next count, the cash variance on the same shift, and the pattern repeating across four weeks. Any one of those alone will be explained away, and reasonably so.</p>

<p><b>Quantify it.</b> "Elevated void rate" is a concern. "₦2.4m of voided transactions in eleven months, of which ₦1.9m had no replacement, at a branch whose shrinkage over the same period was ₦2.1m" is a finding. The number is what moves it from a discussion about behaviour to a decision about action.</p>

<p><b>Preserve before you disturb.</b> Export and retain the evidence with its definition, as module 2 required. Once anybody knows they are being examined, documents can be amended, explanations constructed, and behaviour changed. The version history will record amendments — but you want the position as it was, held by you, before that happens.</p>

<p><b>The first hour when the pattern suggests fraud rather than error.</b> Four things, and they are the ones auditors most often get wrong.</p>

<p><b>Do not tip off.</b> Not a casual question at the branch, not a request for an explanation, not an unusual data request routed through operations.<br>
<b>Do not interview early.</b> An interview conducted before the evidence is complete converts a strong case into a denial and a warning.<br>
<b>Preserve the trail immediately</b>, including anything that could be deleted or amended.<br>
<b>Tell the right person, once.</b> Whoever your charter names — typically the audit committee chair or the chief executive, and specifically not the line manager of the person concerned, who may be involved and will certainly be conflicted.</p>

<p><b>And know where your role ends.</b> You establish what the data shows. You do not conduct disciplinary proceedings, you do not accuse, and you do not decide consequences. Auditors who step past that line lose the independence that made their work credible, and they usually do it from a sense of responsibility rather than ambition — which makes it harder to resist and no less damaging.</p>

<p><b>What happens if you are wrong.</b> Sometimes the pattern has an innocent explanation you did not anticipate, and it emerges after you have escalated. Handle it plainly: say so in writing to everyone who received the original concern, and record the explanation so the test can be tuned. An auditor who withdraws a concern cleanly loses very little; one who defends a position after the explanation arrives loses the ability to raise the next one. Being wrong occasionally is the cost of looking at all.</p>

<blockquote>IMPLEMENTATION TIP: Agree the escalation route with your audit committee before you ever need it, and write it down. The worst moment to work out who to tell is the moment you have something to tell, and hesitation at that point is what allows evidence to disappear.</blockquote>"""
, [
 C("You have a strong pattern suggesting till fraud. The first hour should be spent:",
   ["Interviewing the cashier", "Establishing the facts from the data and preserving the evidence",
    "Informing the branch manager", "Reviewing the CCTV"], 1,
   "An interview before the evidence is complete converts a strong case into a denial and a warning."),
 C("Who should NOT be told first when fraud is suspected at a branch?",
   ["The audit committee chair", "The line manager of the person concerned",
    "The chief executive", "Whoever the audit charter names"], 1,
   "They may be involved and will certainly be conflicted."),
 C("'Elevated void rate at Branch 7' becomes a finding when it is:",
   ["Escalated formally", "Quantified, with the stock and cash consequences attached",
    "Confirmed by the manager", "Repeated next month"], 1,
   "The number moves it from a discussion about behaviour to a decision about action.")]),
]


QUESTIONS = [
 Q("A POS transaction in ZhiftERP is recorded as:", ["A separate POS document type", "A Sales Invoice with is_pos set", "A Journal Entry", "A Payment Entry"], 1,
   "Carrying pos_profile, owner, posting date and time, with lines in the child table.", "Ch1 §4", "Till behaviour in the ledger"),
 Q("There is no POS-to-ERP reconciliation to perform because:", ["It is automated nightly", "The till writes directly into the same backend", "It is done by the external auditor", "Consolidation handles it"], 1,
   "An advantage of the architecture, and worth stating in the audit plan.", "Ch1 §2", "Till behaviour in the ledger"),
 Q("Counting POS revenue without regard to is_consolidated will:", ["Understate revenue", "Double-count it", "Exclude returns", "Exclude cancellations"], 1,
   "Once at transaction level and once consolidated.", "Ch1 §7", "Till behaviour in the ledger"),
 Q("A cashier's shift is bracketed by:", ["Two Journal Entries", "POS Opening Entry and POS Closing Entry", "A Timesheet", "A Stock Entry pair"], 1,
   "The closing entry carries a payment reconciliation table by mode.", "Ch1 §8", "Till behaviour in the ledger"),
 Q("A submitted invoice is corrected by:", ["Editing it in place", "Cancelling and amending, with amended_from naming the original", "Deleting and re-entering", "A credit note only"], 1,
   "Which is why a void leaves a full trail rather than a hole.", "Ch2 §2", "Voids and amendments"),
 Q("The shape most indicative of till theft is:", ["Any cancellation", "A cancellation with no amendment following", "An amendment with a lower value", "A cancellation at shift start"], 1,
   "A genuine correction produces a replacement; a theft does not.", "Ch2 §5", "Voids and amendments"),
 Q("A voided sale where goods physically left creates:", ["A cash variance", "System stock that does not exist, surfacing later as shrinkage", "A negative invoice", "A price variance"], 1,
   "Which makes elevated voids plus elevated shrinkage a far stronger finding than either alone.", "Ch2 §9", "Voids and amendments"),
 Q("Which is NOT one of the four void signals?", ["Rate against the distribution", "Orphan cancellations", "Value clustering high", "Item category"], 3,
   "Rate, orphans, value and timing — and the combination matters more than any one.", "Ch2 §7", "Voids and amendments"),
 Q("A return is identified in the data by:", ["A negative grand total", "is_return set, with return_against naming the original", "docstatus 2", "A credit note doctype"], 1,
   "Quantities and values are negative; stock returns and cash leaves.", "Ch3 §2", "Refunds and returns"),
 Q("Refunds with an empty return_against are:", ["Normal for cash customers", "A nil-expected test where any row needs explanation", "Excluded from testing", "A consolidation artefact"], 1,
   "The population is usually small enough to examine in full.", "Ch3 §3", "Refunds and returns"),
 Q("A refund three minutes after the original on the same till suggests:", ["Efficient correction", "The sale may never have been real", "A card failure", "A pricing correction"], 1,
   "Both very short and very long intervals are testable against the original's timestamp.", "Ch3 §6", "Refunds and returns"),
 Q("Trade credit notes deserve equal scrutiny because they are:", ["Larger in value", "Economically identical to a payment out, and usually less supervised", "Subject to VAT", "Raised more often"], 1,
   "The credit-to-revenue ratio varies far more between salespeople than businesses expect.", "Ch3 §7", "Refunds and returns"),
 Q("Discount fields sit on:", ["The Sales Invoice document", "The Sales Invoice Item child table", "The Item master", "The Price List"], 1,
   "So discount testing must query the child table; a document view misses it.", "Ch4 §2", "Discounts and overrides"),
 Q("Which shipped report finds lines where the discount disagrees with the price arithmetic?", ["Sales Analytics", "Calculated Discount Mismatch", "Item-wise Sales History", "Gross Profit"], 1,
   "It costs nothing to run and almost nobody runs it.", "Ch4 §3", "Discounts and overrides"),
 Q("The unrequested-discount scheme evades detection because:", ["Discounts are unmonitored", "It produces no cash variance at all", "It is below materiality", "Stock is unaffected"], 1,
   "Invoice, till and stock movement all agree; only the discount pattern reveals it.", "Ch4 §6", "Discounts and overrides"),
 Q("Frequent supervisor overrides should be reported as:", ["Instances requiring investigation", "A control that has ceased to function", "Good supervisory engagement", "A training need"], 1,
   "It is the normal process with an extra step.", "Ch4 §8", "Discounts and overrides"),
 Q("Authorisation of an over-limit discount is enforced by Workflow or by:", ["Role Profile", "Authorization Rule", "User Permission", "Print Format"], 1,
   "Establish which your business uses; if neither, that is itself the finding.", "Ch4 §9", "Discounts and overrides"),
 Q("Which measure exposes lapping?", ["Till variance", "Days to bank", "Payment mode mix", "Void rate"], 1,
   "Every individual day reconciles under lapping; the delay is the only sign.", "Ch5 §6", "Cash and payment modes"),
 Q("A persistent small till OVER indicates:", ["Careful cashiering", "A process that is not working, and possibly a float for a later short", "Rounding", "Immaterial variance"], 1,
   "Overs matter as much as shorts.", "Ch5 §4", "Cash and payment modes"),
 Q("A shift closed by somebody other than the cashier who opened it is:", ["Normal at handover", "A control breakdown regardless of whether money is missing", "Only relevant with a variance", "A configuration issue"], 1,
   "Along with sessions closed without a reconciliation.", "Ch5 §5", "Cash and payment modes"),
 Q("Cash variance is best interpreted:", ["Against a fixed tolerance", "Alongside voids, discounts and banking speed at the same branch and shift", "Per transaction", "Monthly only"], 1,
   "Single indicators mislead in cash work more than anywhere else in this track.", "Ch5 §8", "Cash and payment modes"),
 Q("A branch with no variance at all for six months warrants:", ["Commendation", "The same curiosity as a persistent difference", "Reduced oversight", "A wider tolerance"], 1,
   "Independent counting produces small differences.", "Ch5 §9", "Cash and payment modes"),
 Q("An unnormalised cashier profile identifies as highest risk:", ["The newest staff", "The busiest cashier", "Supervisors", "Part-time staff"], 1,
   "Raw counts rank by hours worked and till busyness.", "Ch6 §3", "Cashier profiling"),
 Q("A cashier profile should be described to management as:", ["A list of suspects", "Where to look, with position implying nothing on its own", "Evidence of loss", "A disciplinary input"], 1,
   "Somebody is at the top of any list, including a list of honest people.", "Ch6 §5", "Cashier profiling"),
 Q("The stronger signal is a cashier who:", ["Has always been slightly high", "Has moved from mid-distribution to the top over four months", "Had one high month", "Handles the largest transactions"], 1,
   "Change is what you are looking for, and only a retained series shows it.", "Ch6 §7", "Cashier profiling"),
 Q("Comparison should proceed:", ["Straight to the estate", "Within branch, then branch type, then estate", "Against an industry benchmark", "Against last year only"], 1,
   "A difference surviving all three is worth investigating.", "Ch6 §4", "Cashier profiling"),
 Q("A void rate of 3% is interpretable only against:", ["A policy threshold", "The estate mean and standard deviation", "Last year", "The industry average"], 1,
   "Thresholds are guesses that age badly; distributions adjust themselves.", "Ch7 §2", "Branch distributions"),
 Q("Flagging at two sigma across twenty branches produces:", ["Only genuine outliers", "About one false flag per run by chance", "No flags in a healthy estate", "A normal distribution"], 1,
   "Three sigma is usually the better working threshold.", "Ch7 §4", "Branch distributions"),
 Q("Different formats showing different void rates should be handled by:", ["Applying one estate threshold", "Grouping by format and comparing within the group", "Excluding the outlier format", "Raising a finding"], 1,
   "The outlier that survives grouping is the interesting one.", "Ch7 §5", "Branch distributions"),
 Q("Which is the more useful finding?", ["A branch always above average", "A branch at average but deteriorating four months running", "The highest single month", "The largest branch"], 1,
   "The first is probably characteristic; the second is a change with a cause.", "Ch7 §6", "Branch distributions"),
 Q("The composite ranking asks which branches appear:", ["Highest on any one measure", "In the worst quartile on three or more measures", "Above threshold twice", "In the top decile"], 1,
   "It answers where to worry without pretending to answer who is stealing.", "Ch7 §7", "Branch distributions"),
 Q("Cancellations with no amendment are a:", ["Analytical test", "Nil-expected test", "Configuration check", "Trend measure"], 1,
   "Expect a modest steady rate and investigate concentration rather than instances.", "Ch8 §4", "Test design"),
 Q("Sales outside trading hours should first be checked against:", ["The staff rota", "Clock and time zone configuration", "The stock ledger", "Manager accounts"], 1,
   "Configuration explains this more often than behaviour.", "Ch8 §6", "Test design"),
 Q("A test producing forty hits a month produces:", ["Thorough coverage", "Zero investigations", "A useful trend", "Better tuning data"], 1,
   "Tune until every row is genuinely examined.", "Ch8 §8", "Test design"),
 Q("A new revenue test should be:", ["Deployed to the live programme immediately", "Run privately for a month, then tuned and deployed", "Approved by operations first", "Limited to one branch"], 1,
   "An untuned release exhausts goodwill and kills the credibility of every test after it.", "Ch8 §10", "Test design"),
 Q("The innocent explanation for a test must be written:", ["After the first dispute", "Before deployment", "By the audited department", "Only for analytical tests"], 1,
   "If you cannot describe an innocent hit, you cannot interpret a guilty one.", "Ch8 §9", "Test design"),
 Q("On finding a strong fraud pattern, the first hour is spent:", ["Interviewing", "Establishing facts from data and preserving evidence", "Informing the branch", "Reviewing CCTV"], 1,
   "An early interview converts a strong case into a denial and a warning.", "Ch9 §2", "Investigating exceptions"),
 Q("Evidence should be preserved before disturbing anything because:", ["Retention policy requires it", "Once people know, documents can be amended and explanations constructed", "Queries are slow", "The data may be purged"], 1,
   "You want the position as it was, held by you.", "Ch9 §5", "Investigating exceptions"),
 Q("Who should not be told first about suspected branch fraud?", ["The audit committee chair", "The line manager of the person concerned", "The chief executive", "Whoever the charter names"], 1,
   "They may be involved and will certainly be conflicted.", "Ch9 §7", "Investigating exceptions"),
 Q("A concern becomes a finding when it is:", ["Escalated", "Quantified with stock and cash consequences attached", "Confirmed verbally", "Repeated"], 1,
   "The number moves it from behaviour to action.", "Ch9 §4", "Investigating exceptions"),
 Q("The auditor's role ends at:", ["Disciplinary recommendation", "Establishing what the data shows", "Determining consequences", "Conducting the interview"], 1,
   "Stepping past it loses the independence that made the work credible.", "Ch9 §8", "Investigating exceptions"),
 Q("The escalation route should be agreed:", ["When something is found", "Before it is ever needed, in writing", "By the executive at the time", "Case by case"], 1,
   "Hesitation at that moment is what allows evidence to disappear.", "Ch9 §9", "Investigating exceptions"),
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
    rebalance(QUESTIONS, "control:revenue_pos:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:revenue_pos:checks")

    mod = {
        "title": "Revenue and the Point of Sale",
        "desc": ("Where retail actually loses money, and how every technique shows in the "
                 "data. Voids and what a cancellation leaves behind, refunds against no "
                 "original, the discount scheme that produces no cash variance, shift and "
                 "banking tests, cashier profiling, reading a distribution across branches, "
                 "and the first hour of a suspected fraud."),
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
