#!/usr/bin/env python3
"""Build 'Inventory and Movements' into academy_control_data.json.

Module 5 of System-Based Internal Control in a Retail Environment. With module 6
it carries the commercial argument: inventory and the till are where retail
actually loses money.

Verified from ERPNext v15 source: Stock Entry purposes (Material Issue,
Material Receipt, Material Transfer and the manufacturing variants),
from_warehouse / to_warehouse / add_to_transit, Stock Reconciliation with its
difference_amount and expense_account, and the Stock Ledger Entry fields used
in the worked tests.

Builds on modules 2 and 6 rather than repeating them: extraction technique,
distributions and corroboration are assumed and used.

Run from the app package directory:  python3 build_control_m5.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "inventory"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Where the money actually goes", 12, """<p>A retailer turning over ₦2 billion at 2% shrinkage is losing ₦40 million a year. That figure is worth holding in mind for the whole module, because it sets the scale of what inventory testing is for and it is usually larger than everything else on the audit plan combined.</p>

<p><b>What shrinkage is made of, roughly and in the order people expect it wrong.</b> Administrative error — miscounts, mis-scans, wrong units of measure, cut-off mistakes — is usually the largest component and the least investigated, because it is nobody's fault and therefore nobody's job. Supplier shortfall comes next: goods invoiced and not delivered, or delivered short and signed for anyway. Then internal theft. Then customer theft, which is what everybody assumes dominates and rarely does. Then damage and expiry.</p>

<p>An audit function that treats all shrinkage as theft will spend its year on the smallest component and produce very little.</p>

<p><b>Why the system makes this tractable.</b> Stock in ZhiftERP is not a periodic count reconciled once a year. Every movement writes a Stock Ledger Entry — receipt, issue, transfer, sale, adjustment — with the item, warehouse, quantity, valuation, date, time and the document that caused it. The perpetual record means a difference is locatable in time rather than merely discovered at year end.</p>

<p>That changes the question from <i>how much is missing</i> to <i>when did it go missing, from where, and what else happened at that moment.</i></p>

<p><b>The corroboration that makes inventory findings strong.</b> Module 6 established that a voided sale where goods left the shop creates system stock that does not exist. That difference emerges here, at the next count, attributed to nobody. The reverse also holds: an unexplained stock loss at a branch with an elevated void rate is not two findings, it is one finding with two pieces of evidence.</p>

<p><b>Inventory work is where internal audit is most likely to be resented</b>, because a count difference feels like an accusation against whoever runs the store. The framing that works is that most differences are process rather than people, and that establishing which is the point of the exercise. Auditors who open with theft find that branches stop reporting differences at all, which makes the number smaller and the problem larger.</p>

<blockquote>WATCH-OUT: Beware the branch whose count differences are always small and always favourable. Genuine counting produces differences in both directions of varying size. A tidy result month after month more often means the count is being adjusted to agree with the system than that nothing is going missing.</blockquote>

<p><b>One number worth establishing before anything else.</b> What does your business currently believe its shrinkage is, and how was that figure arrived at? In many retailers the answer is that nobody computes it directly — it emerges as a residual inside cost of sales, blended with pricing and mix, and nobody has ever isolated it. If that is the case, producing a defensible shrinkage number by branch and category is itself a substantial piece of work and probably the most valuable thing you will do in your first year.</p>"""
, [
 C("An audit function treats all shrinkage as theft. The likely outcome is:",
   ["Faster identification of losses", "A year spent on the smallest component, producing very little",
    "Better deterrence", "Improved count accuracy"], 1,
   "Administrative error is usually the largest component and the least investigated, because it is nobody's job."),
 C("A branch reports small favourable count differences every month. This most likely indicates:",
   ["Excellent stock discipline", "The count is being adjusted to agree with the system",
    "Low-value stock", "Accurate scanning"], 1,
   "Genuine counting produces differences in both directions and of varying size."),
 C("An unexplained stock loss at a branch with an elevated void rate is:",
   ["Two separate findings", "One finding with two pieces of evidence",
    "Coincidence until proven", "A counting problem"], 1,
   "A voided sale where goods left creates system stock that does not exist, and it surfaces at the count.")]),

("The stock ledger and what it records", 12, """<p>Every movement of stock writes a Stock Ledger Entry. Understanding its fields is what turns inventory testing from a discussion about counts into a set of answerable questions.</p>

<p><b>The fields that matter.</b> <code>item_code</code> and <code>warehouse</code> identify what and where. <code>posting_date</code> and <code>posting_time</code> say when — and note that these are the business dates, which are not necessarily when the entry was created. <code>actual_qty</code> is the movement, positive or negative. <code>qty_after_transaction</code> is the running balance. <code>valuation_rate</code> and <code>stock_value</code> carry the money. And <code>voucher_type</code> with <code>voucher_no</code> name the document that caused it.</p>

<p><b>That last pair is the whole of traceability.</b> Every quantity change points at the document responsible — a Sales Invoice, a Purchase Receipt, a Stock Entry, a Delivery Note, a Stock Reconciliation. There is no such thing as stock that simply changed. If a balance moved, a document moved it, and it is named.</p>

<p><b>The distinction that will otherwise mislead you.</b> Posting date is the business date; creation is when somebody entered it. A movement posted for the 3rd and entered on the 27th is a backdated entry, and the gap between the two is itself a test. Backdating is sometimes entirely legitimate — a delivery note found late — and sometimes exactly what you are looking for, because it lets a difference be papered over after a count.</p>

<p><b>Where the documents come from.</b> Purchase Receipt brings stock in. Delivery Note and POS sales take it out. Stock Entry moves it between warehouses or adjusts it, with a purpose of Material Receipt, Material Issue or Material Transfer. Stock Reconciliation sets a balance directly to a counted figure and books the difference to an expense account.</p>

<p><b>Stock Reconciliation deserves particular attention</b> and gets its own chapter later, because it is the only document that can set a quantity to whatever somebody says it should be. Every other document records a movement with a cause. A reconciliation records an assertion.</p>

<p><b>The running balance as a diagnostic.</b> Because <code>qty_after_transaction</code> carries forward entry by entry, the ledger is self-checking: each balance should follow from the previous one plus the movement. Where it does not, the ledger is disordered rather than the stock being wrong — which is what the integrity reports from module 2 test, and why they belong before any substantive inventory work.</p>

<blockquote>IMPLEMENTATION TIP: When investigating a stock difference, work from the ledger for that item and warehouse rather than from the count. Sorted by posting date, it shows every movement and its document, and the anomalous entry is usually visible on the page rather than requiring a query.</blockquote>

<p><b>A word about units of measure.</b> An item bought in cartons and sold in units carries a conversion factor, and a conversion set up wrongly produces differences that look exactly like theft — large, persistent, and concentrated in specific items. Before pursuing any single-item difference, check the conversion. It is a two-minute check that has saved auditors from a great many embarrassing conversations, and it fails most often on items added recently or by somebody unfamiliar with the convention.</p>"""
, [
 C("A stock balance changed with no explanation anybody can give. In ZhiftERP this means:",
   ["Stock can change without a document", "A document caused it and voucher_type and voucher_no name it",
    "The ledger is corrupt", "It was a system adjustment"], 1,
   "There is no such thing as stock that simply changed."),
 C("An entry posted for the 3rd but created on the 27th is:",
   ["An error", "A backdated entry, and the gap is itself a test",
    "Normal month-end practice", "A consolidation artefact"], 1,
   "Sometimes legitimate, sometimes exactly how a difference is papered over after a count."),
 C("Which document sets a quantity to an asserted figure rather than recording a movement?",
   ["Purchase Receipt", "Stock Reconciliation", "Delivery Note", "Material Transfer"], 1,
   "Every other document records a movement with a cause; a reconciliation records an assertion.")]),

("Counts and count quality", 12, """<p>The count is the only independent evidence that the system's stock figure is true. Everything else in this module compares records to records. So the quality of the count determines the quality of every conclusion drawn from it, and count quality is rarely audited.</p>

<p><b>What makes a count trustworthy</b>, and each is separately testable.</p>

<p><b>Independence.</b> The person counting should not be the person responsible for the stock. A storekeeper counting their own store is not a control, whatever the count says — and it is the most common arrangement in a branch network because it is convenient.</p>

<p><b>A cut-off.</b> Movement must stop, or be recorded precisely, while counting. Goods received during a count and not accounted for produce a difference that has nothing to do with the stock position.</p>

<p><b>Blind counting.</b> Counters who can see the expected figure will, under time pressure, tend to confirm it. Where the system permits, count sheets should not carry the system quantity.</p>

<p><b>Recount of differences.</b> A single count producing a variance should be recounted before an adjustment is posted, because most first-count differences are counting errors.</p>

<p><b>What the auditor actually tests.</b> Not the count itself, usually — you cannot be at every branch. You test the <i>evidence</i> that these conditions held: who signed, whether the counter was independent of the store, whether a recount happened before the adjustment, the interval between the count date and the adjustment posting.</p>

<p><b>That last interval is the most informative single measure here.</b> A count on the 2nd adjusted on the 3rd is a controlled process. A count on the 2nd adjusted on the 24th means three weeks in which the difference could be reduced by other means — transfers in, backdated receipts, or a second count — before anything was recorded. Long intervals do not prove anything and they change what the adjustment means.</p>

<p><b>Attendance, when you can manage it.</b> Attending a count occasionally, unannounced, at a branch chosen by data rather than by rota, tests everything above at once. The finding is rarely the count; it is what you observe about how it is conducted. Announced attendance tests only whether a branch can run a count properly when it knows you are coming, which is a different and much weaker question.</p>

<p><b>Cycle counting, where it exists.</b> Some retailers count high-value or fast-moving lines continuously rather than counting everything periodically. It is better control and it changes your testing: instead of one annual event there is a stream of small counts, and the useful questions become coverage — which items have not been counted at all this year — and consistency, whether the same items keep producing differences. A cycle programme that never reaches certain items is a gap somebody chose, deliberately or otherwise.</p>

<blockquote>WATCH-OUT: Check who performed the count against who is responsible for the stock, for every count, not just the ones you attend. It is one join between the count document and the branch's staff list, and it is the control most likely to be quietly absent.</blockquote>"""
, [
 C("A storekeeper counts their own store. This is:",
   ["Acceptable if supervised remotely", "Not a control, whatever the count says",
    "Standard practice", "Acceptable for low-value stock"], 1,
   "It is the most common arrangement in a branch network, because it is convenient."),
 C("A count on the 2nd is adjusted on the 24th. The concern is:",
   ["The adjustment is stale", "Three weeks in which the difference could be reduced by other means before being recorded",
    "The count was inaccurate", "The posting date is wrong"], 1,
   "It proves nothing on its own and it changes what the adjustment means."),
 C("Announced attendance at a stock count tests:",
   ["Whether the process is sound", "Whether a branch can run a count properly when it knows you are coming",
    "Count accuracy", "Cut-off discipline"], 1,
   "A different and much weaker question than unannounced attendance answers.")]),

("Adjustments: who, how often, how much", 12, """<p>An adjustment changes recorded stock without any goods moving. It is therefore the most powerful instrument in the store and the one most worth watching.</p>

<p><b>Two forms.</b> A Stock Entry with purpose Material Issue or Material Receipt moves quantity in or out with a stated reason. A Stock Reconciliation sets the balance directly to a figure, booking the difference to an expense account. Both change stock; only the second asserts a position rather than recording a movement.</p>

<p><b>The analysis, and it is the same shape as module 6's cashier profiling.</b> Group adjustments by <code>owner</code>, by warehouse, and by item category. Count them, value them, and rank against the estate distribution rather than a threshold. Then look at the combination that matters: frequency, value, direction, and timing relative to counts.</p>

<p><b>Direction is more informative than volume.</b> Adjustments should be roughly balanced over time — miscounts and mis-scans go both ways. A person or a branch whose adjustments are overwhelmingly one direction is doing something other than correcting errors. Persistent write-downs may be concealing loss; persistent write-ups may be concealing an earlier over-issue, or creating stock to cover a later one.</p>

<p><b>Timing relative to the count is the second signal.</b> Adjustments clustering immediately before a count reduce the difference the count will find. Adjustments immediately after it absorb a difference the count did find. Both are worth understanding, and both are visible by plotting adjustment dates against count dates for each branch.</p>

<p><b>Reasons, where your configuration captures them.</b> A reason field that is mandatory and free-text will fill with "adjustment", "correction" and "as per count", which tells you nothing. A short mandatory list — damage, expiry, count difference, mis-scan, theft confirmed — produces analysable data, and the distribution of reasons by branch is informative in itself. If reasons are not captured usefully, that is a recommendation worth making before any test in this chapter will bite.</p>

<p><b>Approval, and the finding you may already have.</b> Establish whether adjustments require approval at all, and above what value. Depending on configuration this is a Workflow on Stock Entry or an Authorization Rule with a threshold. If neither exists — if any storekeeper can write off any quantity without a second person — you have found a control weakness that outranks any pattern you would otherwise report.</p>

<blockquote>IMPLEMENTATION TIP: Plot adjustment value by month against count dates for each branch on one chart. The relationship between the two is visible immediately, and it takes one query. Branches where the two are related are worth a visit; branches where adjustments are steady and unrelated to counts usually have a process problem rather than a people problem.</blockquote>

<p><b>Value thresholds and the shape they create.</b> Where approval is required above a value, expect adjustment values to cluster immediately below it — the same behaviour module 6 described for purchase orders and discounts. Plot adjustment value as a histogram and look at the region just under each threshold. A pronounced cluster means the limit is being worked around rather than respected, and that is a stronger finding than any individual adjustment because it describes a practice rather than an instance.</p>"""
, [
 C("A storekeeper's adjustments are overwhelmingly write-downs over six months. This suggests:",
   ["Careful housekeeping", "Something other than correcting errors — miscounts go both ways",
    "High-damage categories", "Good count discipline"], 1,
   "Direction is more informative than volume."),
 C("A branch posts a run of write-downs in the week before its count, and another run in the week after. Together these:",
   ["Show diligent housekeeping", "Reduce what the count finds and then absorb what it did find",
    "Are unrelated to the count", "Indicate a perishable category"], 1,
   "Plotting adjustment dates against count dates for each branch makes the relationship visible immediately."),
 C("Any storekeeper can write off any quantity without a second person. This is:",
   ["A pattern to monitor", "A control weakness outranking any pattern you would otherwise report",
    "Acceptable below a value", "A configuration preference"], 1,
   "Establish whether approval exists at all before analysing behaviour.")]),

("Transfers between branches", 12, """<p>Stock moving between locations is where quantity most easily disappears, because for a period it belongs to neither end and is somebody's responsibility only in principle.</p>

<p><b>How it is recorded.</b> A Stock Entry with purpose Material Transfer, carrying <code>from_warehouse</code> and <code>to_warehouse</code>. Where in-transit handling is configured, <code>add_to_transit</code> routes the goods through an intermediate warehouse, so despatch and receipt are two events rather than one instantaneous move.</p>

<p><b>That configuration matters enormously to your testing.</b> With transit enabled, stock sits visibly in an in-transit warehouse between despatch and receipt, and the test is simple: what has been in transit longer than the journey takes? Without it, a transfer is a single entry that moves stock instantly from one branch to another, and the receiving branch may never confirm anything arrived. <b>Establish which your business uses before designing any transfer test</b>, because the two need completely different queries.</p>

<p><b>The tests, in order of value.</b></p>

<p><b>In transit beyond the expected duration.</b> Where transit is enabled. A transfer despatched three weeks ago and never received is either lost, stolen, or received without being recorded — and all three need attention.</p>

<p><b>Quantity despatched against quantity received</b>, where both are recorded. Differences should be nil and any difference is a finding.</p>

<p><b>Transfer frequency and direction between branch pairs.</b> A route carrying unusual volume, or one branch that is a persistent net exporter of stock without a commercial reason, is worth understanding.</p>

<p><b>Transfers timed near counts.</b> A branch that receives a large transfer immediately before its count and despatches it back afterwards has borrowed stock to cover a shortfall. It is a known technique, it is entirely visible in the ledger, and almost nobody tests for it.</p>

<p><b>The innocent explanations</b>, which you must be able to state. Genuine rebalancing between branches, a promotion concentrating stock, a new branch being filled, seasonal repositioning. All produce elevated transfer volume, and all are explicable by somebody in operations in a sentence.</p>

<p><b>The corroboration to build.</b> A transfer pattern alone is weak. A transfer pattern plus a count difference at the receiving branch, or plus in-transit stock that never arrives, is not. As throughout this track, one measure is a candidate and two are a finding.</p>

<p><b>Who confirms receipt matters as much as whether it was confirmed.</b> Check that the acknowledgement comes from somebody at the receiving end rather than from the despatching branch or a central user with rights at both. A transfer despatched and received by the same person is not a transfer, it is a movement with one witness — and it is usually a configuration accident rather than a deliberate arrangement.</p>

<blockquote>WATCH-OUT: The branch that both receives and returns the same quantity around its count date is the pattern to look for specifically. It leaves the annual stock position unchanged, produces no adjustment, and is invisible to anybody examining a single branch or a single month.</blockquote>"""
, [
 C("Before designing any transfer test you must establish:",
   ["The value threshold", "Whether in-transit warehousing is configured",
    "The approval rule", "The branch hierarchy"], 1,
   "With transit, despatch and receipt are two events; without it, a transfer is instantaneous and needs a different query."),
 C("A branch receives a large transfer just before its count and returns it just after. This is:",
   ["Routine rebalancing", "Borrowed stock covering a shortfall — visible in the ledger and rarely tested",
    "A cut-off error", "A transit timing issue"], 1,
   "It leaves the annual position unchanged and is invisible to anybody examining one branch or one month."),
 C("Stock in transit for three weeks on a two-day route means it is:",
   ["Still moving", "Lost, stolen, or received without being recorded",
    "A posting delay", "Awaiting approval"], 1,
   "All three need attention, and the receiving branch confirming arrival would have distinguished them at the time.")]),

("Negative stock and what it tells you", 12, """<p>Negative stock means the system believes you have issued more of an item than you ever had. It is arithmetically impossible in the physical world, which makes it one of the few completely unambiguous signals available to an auditor.</p>

<p><b>Where it comes from.</b> Almost always a sequencing failure rather than a theft: goods sold before the receipt was entered, a receipt posted later than the sale it supplied, a transfer recorded out of order, or a backdated entry inserted before movements that followed it.</p>

<p><b>So the finding is usually about process, and that is still worth having.</b> A branch regularly going negative is selling stock the system does not know it has, which means its stock figures are unreliable at all times rather than only at the moment of the negative balance. Every valuation, every reorder calculation and every shrinkage number at that branch inherits the unreliability.</p>

<p><b>Whether it is permitted at all is a configuration decision</b> with real consequences. Allowing negative stock keeps the tills running when paperwork lags, which branches value enormously. Preventing it forces the paperwork to be current and stops sales that the system cannot support, which operations will resist. Both positions are defensible; what matters for your report is that somebody chose, rather than the setting having been inherited from installation and never revisited.</p>

<p><b>The test is simple and the interpretation is where the work is.</b> Query the stock ledger for entries where <code>qty_after_transaction</code> is below zero, group by item, warehouse and month, and rank branches by frequency. Then ask, for the worst: is it one item repeatedly, suggesting a specific process failure such as a supplier whose paperwork always lags, or is it spread, suggesting the branch as a whole is running ahead of its records?</p>

<p><b>The valuation consequence, which is the part most auditors miss.</b> When stock goes negative the system has no cost for the goods being issued, so it estimates — and when the receipt eventually arrives at a different rate, the valuation must be corrected retrospectively. That correction is what generates repost activity and unexplained cost-of-sales movements. <b>A branch with frequent negative stock will also show margin that moves for no commercial reason</b>, and an auditor investigating the margin without knowing this will look in entirely the wrong place.</p>

<blockquote>IMPLEMENTATION TIP: Run the negative stock test before any gross margin investigation at branch level. If negatives are frequent, the margin movement probably has a mechanical explanation, and pursuing it as a pricing or shrinkage matter will waste a fortnight.</blockquote>

<p><b>The recommendation that usually follows.</b> If negative stock is frequent at particular branches, the fix is rarely disciplinary — it is receiving discipline, so that goods are entered when they arrive rather than when somebody has time. That is an operational change with a named owner and a measurable outcome, which makes it exactly the kind of recommendation that gets implemented. Findings whose remedy is 'be more careful' do not get implemented, and this one has a better answer available.</p>"""
, [
 C("Negative stock most commonly indicates:",
   ["Theft", "A sequencing failure — goods sold before the receipt was entered",
    "A valuation error", "A counting error"], 1,
   "Which makes it a process finding, and still worth having."),
 C("A branch with frequent negative stock will also tend to show:",
   ["Higher shrinkage only", "Margin that moves for no commercial reason",
    "Lower transfer volume", "More adjustments in one direction"], 1,
   "The system estimates a cost for goods it does not have, and corrects it retrospectively when the receipt arrives."),
 C("Whether negative stock is permitted is:",
   ["A system limitation", "A configuration decision that should have been made deliberately",
    "Fixed by the platform", "Determined by item type"], 1,
   "Both positions are defensible; what matters is that somebody chose rather than inheriting it from installation.")]),

("Valuation integrity", 12, """<p>Everything so far concerned quantity. Value is a separate question and it can be wrong while every quantity is right — which matters because inventory value flows straight into cost of sales, gross margin and the balance sheet.</p>

<p><b>How value is carried.</b> Each stock ledger entry holds a <code>valuation_rate</code> and a resulting <code>stock_value</code>. Under a moving average, receipts at different prices blend the rate; under FIFO, layers are consumed in order. Either way the value of what is issued is determined by the record, not by anybody's judgement at the moment of issue.</p>

<p><b>The tests that matter here are largely the shipped ones from module 2</b>, and this is where they earn their place.</p>

<p><b>Stock Ledger Invariant Check</b> tests whether running quantity and valuation behave consistently entry by entry. <b>Incorrect Balance Qty After Transaction</b> finds balances that do not follow from the movement recorded. <b>Stock And Account Value Comparison</b> tests whether the stock ledger agrees with the general ledger — and a difference there means inventory and finance are describing different businesses.</p>

<p><b>Run them before substantive inventory work, not after.</b> A shrinkage finding raised against a ledger that does not reconcile to the accounts will be dismissed the moment somebody notices, and they will be right to dismiss it.</p>

<p><b>Reposting, and why it produces confusing results.</b> When a backdated entry or a corrected rate changes history, the system must recalculate valuations for everything that followed. That reposting is legitimate and necessary, and while it is pending or partially complete the figures you extract may not be final. An auditor pulling cost of sales in the middle of a large repost gets a number that will change, and will not know why.</p>

<p><b>Two analytical valuation tests worth running.</b> Items whose valuation rate moved sharply without a corresponding purchase — which usually indicates a correction or a manual intervention rather than a market movement. And items where the valuation rate is materially above the current purchase price, which either means old expensive layers are still held, or means a rate was set incorrectly and every issue since has been costed wrongly.</p>

<p><b>The point to carry into the reporting module.</b> A valuation problem is rarely a fraud and frequently material. It affects the accounts rather than the warehouse, it will be found eventually by the external auditor, and finding it first is one of the clearest demonstrations an internal function can give of being worth its cost.</p>

<p><b>And a caution about method changes.</b> If the business has changed valuation method, or migrated between systems, expect a period where historical comparisons are not meaningful. Comparing this year's margin to last year's across a migration boundary compares two different measurement bases, and somebody will present the difference as a performance story. Establish when the boundary falls and say so before the comparison is made rather than after it has been believed.</p>

<blockquote>WATCH-OUT: Do not extract cost of sales or stock value while a repost is running or queued. The figures are mid-recalculation, they will change, and a finding built on them will evaporate. Check the repost queue before pulling any valuation-based number.</blockquote>"""
, [
 C("You are pulling cost of sales for a margin analysis. Before extracting, check:",
   ["The count dates", "Whether a valuation repost is running or queued",
    "The transfer log", "Adjustment approvals"], 1,
   "Mid-recalculation figures will change, and a finding built on them will evaporate."),
 C("Stock And Account Value Comparison returning differences means:",
   ["Stock has been miscounted", "Inventory and finance are describing different businesses",
    "Valuation method has changed", "A repost is pending"], 1,
   "Every stock-derived financial figure is unreliable until it is resolved."),
 C("An item whose valuation rate sits well above current purchase price indicates:",
   ["Market movement", "Old expensive layers still held, or a rate set incorrectly and costing every issue since",
    "A pricing error", "Supplier overcharging"], 1,
   "Either explanation matters, and the second is the more serious.")]),

("Shrinkage across the estate", 12, """<p>Shrinkage at one branch is a number. Shrinkage across twenty branches is a distribution, and the distribution is where the findings are.</p>

<p><b>Normalise before comparing anything.</b> Shrinkage in naira ranks branches by size and tells you what you already know. Shrinkage as a percentage of sales, or of stock held, is comparable. Every table in this chapter is a percentage.</p>

<p><b>Compare within the right group.</b> Categories differ enormously — high-value small items, perishables and loose goods shrink differently from packaged household lines. A branch with an unusual trade mix will look bad or good for reasons of assortment rather than control. Compare by category first, then aggregate, and treat a branch that is an outlier <i>within</i> its categories as the real signal.</p>

<p><b>The three cuts worth building.</b></p>

<p><b>By branch, normalised and ranked</b>, with the estate mean and standard deviation. Outliers beyond three sigma warrant a look; beyond two, in a twenty-branch estate, you should expect roughly one false flag every run.</p>

<p><b>By category within branch.</b> A branch whose shrinkage is concentrated in one category is a different problem from one losing across the range. Concentration points at a specific process, a specific location in the store, or a specific person; spread points at counting, receiving or systemic error.</p>

<p><b>By trend.</b> A branch at the estate average but deteriorating for four consecutive months is a better finding than one that has always been high — the first is a change with a cause you might still find, the second is probably characteristic and has likely been discussed before.</p>

<p><b>Corroborate with what you already have.</b> This is where the modules join. Shrinkage plus elevated voids points at the till. Shrinkage plus adjustment concentration points at the store office. Shrinkage plus transfer anomalies points at the movement. Shrinkage plus negative stock points at process rather than people. <b>The same shrinkage number means four completely different things depending on what accompanies it</b>, and it is the accompaniment that tells you where to send your fieldwork.</p>

<p><b>What to do with the composite.</b> Rank every branch on shrinkage, voids, adjustments, transfer anomalies and count-to-adjustment interval. Branches appearing in the worst quartile on three or more are your fieldwork list. That single page answers the question the audit committee actually asks — where should we be worried — and it takes one query per measure and a sort.</p>

<blockquote>IMPLEMENTATION TIP: Build the composite once and run it monthly, retaining each month. Three or four branches will recur, and that recurring list should drive where you go — not the rota, which by construction visits branches in an order chosen before any of this was known.</blockquote>

<p><b>What to do with a branch that is consistently good.</b> The distribution has two ends, and the branch three sigma <i>below</i> the estate mean on shrinkage is worth understanding too — either it is doing something the others should copy, or its numbers are not describing reality. Both are worth knowing, and visiting a good branch to find out why is far better received than visiting a poor one, which makes it a useful way to build the relationships you will need when you do have to visit a poor one.</p>"""
, [
 C("Shrinkage compared in naira across branches will:",
   ["Reveal the worst performer", "Rank branches by size and tell you what you already know",
    "Adjust for trade mix", "Highlight category issues"], 1,
   "Every comparison must be normalised — as a percentage of sales or of stock held."),
 C("Shrinkage concentrated in one category at a branch points at:",
   ["Counting error", "A specific process, location or person",
    "Systemic error", "Receiving problems"], 1,
   "Spread across the range points instead at counting, receiving or systemic error."),
 C("The same shrinkage figure accompanied by elevated adjustments rather than elevated voids points at:",
   ["The till", "The store office", "The delivery route", "Receiving"], 1,
   "The accompaniment tells you where to send fieldwork; the shrinkage number alone does not.")]),

("The inventory tests, and investigating a difference", 12, """<p>The working programme, and what to do when a test produces something worth pursuing.</p>

<p><b>Nil-expected tests.</b> Any row is a finding.</p>

<p><b>Negative stock events.</b> <i>Innocent:</i> a supplier whose paperwork routinely lags, which is a real and fixable process finding rather than nothing.<br>
<b>Stock in transit beyond the route duration.</b> <i>Innocent:</i> a genuine delay somebody in logistics can name.<br>
<b>Despatch and receipt quantity differences.</b> <i>Innocent:</i> agreed short-shipment, which should be documented.<br>
<b>The integrity report set.</b> <i>Innocent:</i> none — a hit is a defect and needs support attention.</p>

<p><b>Analytical tests.</b> The distribution is the question.</p>

<p><b>Adjustment frequency and value by person and branch.</b> <i>Innocent:</i> a branch handling damaged goods for the region, a new storekeeper, a category with genuine wastage.<br>
<b>Adjustment direction imbalance.</b> <i>Innocent:</i> perishables, which legitimately write down more than up.<br>
<b>Shrinkage by branch and category, normalised.</b> <i>Innocent:</i> trade mix, store layout, customer profile.<br>
<b>Count-to-adjustment interval.</b> <i>Innocent:</i> a branch awaiting an approval that sits with somebody on leave — which is itself worth reporting.</p>

<p><b>Investigating a difference, in order.</b></p>

<p><b>First, is it real?</b> Check the integrity reports, check for a pending repost, check whether the count was cut off properly and whether units of measure are consistent. A surprising difference is more often mechanical than criminal, and establishing that takes an hour rather than a week.</p>

<p><b>Second, locate it in time.</b> The ledger for that item and warehouse shows every movement. Work backwards from the count to the last point at which the balance was known to be right, and the difference is bounded to a period, which usually bounds it to a shift and a small number of people.</p>

<p><b>Third, look at what else happened in that window.</b> Voids, adjustments, transfers, receipts. This is where corroboration is built and where a single anomaly becomes a pattern.</p>

<p><b>Fourth, quantify.</b> "Stock differences at Branch 7" is a concern; "₦3.2m across eleven months, 78% in two categories, coinciding with an adjustment rate four times the estate mean by one storekeeper" is a finding.</p>

<p><b>And know when to stop and escalate.</b> If the pattern suggests deliberate action rather than error, module 9's rules apply and they apply from that moment: preserve, do not tip off, do not interview, tell the person your charter names. The temptation in inventory work is to ask the storekeeper a friendly question because they are standing there and it seems natural. That single question is what most often ends the investigation.</p>

<p><b>What a completed inventory investigation looks like.</b> A quantified loss, bounded in time and location, with the ledger extract retained as it stood, the corroborating measures attached, the innocent explanations tested and eliminated in writing, and a clear statement of what the data does and does not establish. That last part matters: the data can show that stock left without a sale and that one person had access. It cannot show intent, and a report that implies it has overstepped and will be attacked on exactly that point.</p>

<blockquote>WATCH-OUT: The commonest way an inventory investigation fails is being conducted openly at the branch while it is still exploratory. Stock can be moved, counted differently, or transferred out within a day of somebody realising they are being examined. Do the data work first, entirely, before anybody at the branch knows you are looking.</blockquote>"""
, [
 C("A surprising stock difference should first be tested for:",
   ["Theft", "A mechanical cause — integrity, repost, cut-off, units of measure",
    "Supplier shortfall", "Counting error only"], 1,
   "Establishing that takes an hour rather than a week, and it is more often the answer."),
 C("Having bounded a difference to a period using the ledger, the next step is:",
   ["Interview the storekeeper", "Look at what else happened in that window — voids, adjustments, transfers",
    "Recount the item", "Raise the finding"], 1,
   "This is where corroboration is built and a single anomaly becomes a pattern."),
 C("Asking the storekeeper a friendly question while the work is still exploratory:",
   ["Speeds up the investigation", "Is what most often ends it",
    "Is good practice for context", "Establishes their explanation early"], 1,
   "Stock can be moved, counted differently or transferred out within a day of somebody realising.")]),
]


QUESTIONS = [
 Q("A ₦2bn retailer at 2% shrinkage is losing annually about:", ["₦4m", "₦40m", "₦400m", "₦20m"], 1,
   "Usually larger than everything else on the audit plan combined.", "Ch1 §1", "Scale and causes"),
 Q("The largest component of shrinkage is usually:", ["Customer theft", "Administrative error", "Internal theft", "Damage and expiry"], 1,
   "And the least investigated, because it is nobody's fault and therefore nobody's job.", "Ch1 §2", "Scale and causes"),
 Q("An audit function treating all shrinkage as theft will:", ["Deter losses", "Spend the year on the smallest component", "Find more", "Improve counts"], 1,
   "Customer theft is what everybody assumes dominates and rarely does.", "Ch1 §3", "Scale and causes"),
 Q("Consistently small favourable count differences suggest:", ["Excellent discipline", "The count is being adjusted to agree with the system", "Low-value stock", "Good scanning"], 1,
   "Genuine counting produces differences in both directions and of varying size.", "Ch1 §7", "Scale and causes"),
 Q("Which pair on a Stock Ledger Entry provides traceability?", ["item_code and warehouse", "voucher_type and voucher_no", "posting_date and posting_time", "actual_qty and valuation_rate"], 1,
   "There is no such thing as stock that simply changed.", "Ch2 §3", "The stock ledger"),
 Q("qty_after_transaction records:", ["The movement", "The running balance after it", "The counted quantity", "The reserved quantity"], 1,
   "Which makes the ledger self-checking entry by entry.", "Ch2 §2", "The stock ledger"),
 Q("An entry posted for the 3rd and created on the 27th is:", ["Invalid", "Backdated, and the gap is itself a test", "A transit entry", "A reposting artefact"], 1,
   "Sometimes legitimate, sometimes how a difference is papered over after a count.", "Ch2 §5", "The stock ledger"),
 Q("Which document asserts a balance rather than recording a movement?", ["Delivery Note", "Stock Reconciliation", "Purchase Receipt", "Material Transfer"], 1,
   "Booking the difference to an expense account.", "Ch2 §7", "The stock ledger"),
 Q("The only independent evidence that system stock is true is:", ["The valuation report", "The count", "The general ledger", "The supplier invoice"], 1,
   "Everything else compares records to records.", "Ch3 §1", "Counts and count quality"),
 Q("A storekeeper counting their own store is:", ["Acceptable with supervision", "Not a control", "Standard and adequate", "Acceptable for low value"], 1,
   "The most common arrangement in a branch network, because it is convenient.", "Ch3 §3", "Counts and count quality"),
 Q("Counters who can see the expected figure will tend to:", ["Count more accurately", "Confirm it under time pressure", "Take longer", "Recount more often"], 1,
   "Which is why count sheets should not carry the system quantity where possible.", "Ch3 §5", "Counts and count quality"),
 Q("The most informative single measure of count control is:", ["The number of counters", "The interval between count date and adjustment posting", "The count frequency", "The value counted"], 1,
   "A long interval is time in which the difference could be reduced by other means.", "Ch3 §8", "Counts and count quality"),
 Q("Unannounced attendance at a count is superior because announced attendance tests only:", ["Count accuracy", "Whether a branch can run a count properly when it knows you are coming", "Cut-off", "Independence"], 1,
   "A different and much weaker question.", "Ch3 §9", "Counts and count quality"),
 Q("Adjustments overwhelmingly in one direction indicate:", ["Category characteristics", "Something other than correcting errors", "Good discipline", "Seasonal wastage"], 1,
   "Miscounts and mis-scans go both ways over time.", "Ch4 §5", "Adjustments"),
 Q("Adjustments clustering immediately BEFORE a count:", ["Improve accuracy", "Reduce the difference the count will find", "Are required", "Indicate preparation"], 1,
   "Those immediately after absorb a difference the count did find.", "Ch4 §6", "Adjustments"),
 Q("A mandatory free-text reason field on adjustments will fill with:", ["Useful detail", "'Adjustment', 'correction' and 'as per count'", "Nothing", "Category codes"], 1,
   "A short mandatory list produces analysable data.", "Ch4 §7", "Adjustments"),
 Q("If no approval is required for any adjustment, this outranks:", ["Nothing", "Any pattern you would otherwise report", "The count interval", "Direction analysis"], 1,
   "Establish whether approval exists at all before analysing behaviour.", "Ch4 §8", "Adjustments"),
 Q("Which field indicates in-transit handling on a transfer?", ["to_warehouse", "add_to_transit", "purpose", "expense_account"], 1,
   "It routes goods through an intermediate warehouse, making despatch and receipt two events.", "Ch5 §2", "Transfers"),
 Q("Without in-transit configured, a transfer is:", ["Two events", "A single instantaneous move that the receiving branch may never confirm", "Blocked", "Approval-gated"], 1,
   "The two configurations need completely different queries.", "Ch5 §3", "Transfers"),
 Q("A branch receiving a large transfer before its count and returning it after has:", ["Rebalanced stock", "Borrowed stock to cover a shortfall", "A transit delay", "A cut-off error"], 1,
   "It leaves the annual position unchanged and is invisible to single-branch review.", "Ch5 §7", "Transfers"),
 Q("Stock in transit for three weeks on a two-day route is:", ["Still moving", "Lost, stolen, or received without being recorded", "A posting lag", "Normal"], 1,
   "All three explanations need attention.", "Ch5 §5", "Transfers"),
 Q("Negative stock most often results from:", ["Theft", "Sequencing failure — goods sold before the receipt was entered", "Miscounting", "Valuation error"], 1,
   "Which makes it a process finding, and still worth having.", "Ch6 §2", "Negative stock"),
 Q("A branch with frequent negative stock will also show:", ["Higher transfers", "Margin moving for no commercial reason", "Fewer adjustments", "Better counts"], 1,
   "The system estimates a cost it does not have and corrects it retrospectively.", "Ch6 §7", "Negative stock"),
 Q("Before investigating branch gross margin you should run:", ["The transfer test", "The negative stock test", "The count interval test", "The adjustment direction test"], 1,
   "If negatives are frequent, the margin movement probably has a mechanical explanation.", "Ch6 §8", "Negative stock"),
 Q("Permitting negative stock is:", ["A platform limitation", "A configuration decision that should be deliberate", "Always wrong", "Set per item"], 1,
   "Both positions are defensible; what matters is that somebody chose.", "Ch6 §5", "Negative stock"),
 Q("Under a moving average, receipts at different prices:", ["Are held as layers", "Blend the valuation rate", "Are valued at the latest rate", "Require manual revaluation"], 1,
   "Under FIFO, layers are consumed in order instead.", "Ch7 §2", "Valuation integrity"),
 Q("Before pulling any valuation-based figure, check:", ["The count schedule", "Whether a repost is running or queued", "Approval status", "The transfer log"], 1,
   "Mid-recalculation figures will change and a finding built on them will evaporate.", "Ch7 §6", "Valuation integrity"),
 Q("A valuation rate materially above current purchase price means:", ["Supplier overcharging", "Old expensive layers held, or a rate set incorrectly", "Market movement", "A pricing error"], 1,
   "The second explanation means every issue since has been costed wrongly.", "Ch7 §7", "Valuation integrity"),
 Q("The integrity report set should be run:", ["After substantive inventory work", "Before it", "Only on suspicion", "At year end"], 1,
   "A finding raised against a ledger that does not reconcile will be dismissed.", "Ch7 §5", "Valuation integrity"),
 Q("Shrinkage compared across branches must be expressed as:", ["Naira lost", "A percentage of sales or of stock held", "Units lost", "A count variance"], 1,
   "Naira ranks branches by size.", "Ch8 §2", "Shrinkage analytics"),
 Q("Shrinkage concentrated in one category points at:", ["Counting error", "A specific process, location or person", "Receiving", "Systemic error"], 1,
   "Spread across the range points at counting, receiving or systemic error instead.", "Ch8 §6", "Shrinkage analytics"),
 Q("Shrinkage accompanied by adjustment concentration points at:", ["The till", "The store office", "The delivery route", "Receiving"], 1,
   "The accompaniment tells you where to send fieldwork.", "Ch8 §7", "Shrinkage analytics"),
 Q("Flagging at two sigma across twenty branches produces:", ["Only real outliers", "About one false flag per run", "No flags", "A ranked list"], 1,
   "Three sigma is the better working threshold.", "Ch8 §4", "Shrinkage analytics"),
 Q("The composite fieldwork list is built from branches appearing in the worst quartile on:", ["Any one measure", "Three or more measures", "Shrinkage alone", "Two consecutive months"], 1,
   "It answers where to worry, and takes one query per measure plus a sort.", "Ch8 §8", "Shrinkage analytics"),
 Q("Which is a nil-expected inventory test?", ["Adjustment frequency by branch", "Despatch and receipt quantity differences", "Shrinkage by category", "Count-to-adjustment interval"], 1,
   "Any row is a finding rather than a data point.", "Ch9 §3", "Test design and investigation"),
 Q("The innocent explanation for adjustment direction imbalance is usually:", ["New staff", "Perishables, which legitimately write down more than up", "High-value items", "Poor scanning"], 1,
   "Every test needs its innocent explanation written before deployment.", "Ch9 §5", "Test design and investigation"),
 Q("A count-to-adjustment interval caused by an approver on leave is:", ["Not a finding", "Itself worth reporting", "A data error", "Immaterial"], 1,
   "The innocent explanation is sometimes the finding.", "Ch9 §5", "Test design and investigation"),
 Q("The first question about a surprising stock difference is:", ["Who had access", "Is it real — integrity, repost, cut-off, units of measure", "How much is it worth", "When was the last count"], 1,
   "It is more often mechanical than criminal, and checking takes an hour.", "Ch9 §7", "Test design and investigation"),
 Q("Bounding a difference in time using the ledger usually also bounds it to:", ["A category", "A shift and a small number of people", "A supplier", "A quarter"], 1,
   "Work backwards from the count to the last point the balance was known right.", "Ch9 §8", "Test design and investigation"),
 Q("'Stock differences at Branch 7' becomes a finding when:", ["It is escalated", "It is quantified with concentration and corroboration attached", "The manager confirms it", "It recurs"], 1,
   "The number moves it from a concern to a decision.", "Ch9 §10", "Test design and investigation"),
 Q("The commonest way an inventory investigation fails is:", ["Insufficient data", "Being conducted openly at the branch while still exploratory", "Poor counting", "Late escalation"], 1,
   "Stock can be moved or transferred out within a day of somebody realising.", "Ch9 §12", "Test design and investigation"),
 Q("Inventory work is most likely to be resented because:", ["It takes branch time", "A count difference feels like an accusation against whoever runs the store", "It requires attendance", "It delays trading"], 1,
   "Opening with theft makes branches stop reporting differences at all.", "Ch1 §6", "Scale and causes"),
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
    rebalance(QUESTIONS, "control:inventory:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:inventory:checks")

    mod = {
        "title": "Inventory and Movements",
        "desc": ("Where retail loses most of its money. The stock ledger and what it "
                 "records, count quality, adjustments by person and direction, transfers "
                 "and the stock borrowed before a count, negative stock and its valuation "
                 "consequence, valuation integrity, shrinkage as a distribution across the "
                 "estate, and how to investigate a difference without ending the "
                 "investigation."),
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
