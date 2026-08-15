#!/usr/bin/env python3
"""Build 'Master Data and Configuration' into academy_control_data.json.

Module 3 of System-Based Internal Control in a Retail Environment.

Deliberately does not repeat module 4's supplier master-data work. That chapter
covered suppliers, bank accounts and the change-then-pay test; this module
covers everything else that is set once and then determines how thousands of
transactions behave — items and prices, customers and credit, warehouses and
accounts, workflow configuration, and the settings nobody reviews.

Verified from source: Item Price carries price_list, price_list_rate,
valid_from and valid_upto and tracks changes; Customer carries credit_limits,
payment_terms, default_price_list and tracks changes; Workflow ships with
Workflow Document State, Workflow Transition and Workflow Action.

Run from the app package directory:  python3 build_control_m3.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "master_data"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The quietest control in the building", 12, """<p>Transactions get audited. Configuration does not, and configuration determines how every transaction behaves.</p>

<p><b>Consider the leverage.</b> Somebody changes a price on an item. No transaction is created, no approval is sought in most configurations, and no report highlights it. Yet every sale of that item from that moment carries the new price, and if the item sells two hundred times a day across twenty branches, one field change has altered four thousand transactions a day without appearing in any of them.</p>

<p>That asymmetry — enormous effect, minimal visibility — is why master data is the highest-leverage area in this track and the least examined.</p>

<p><b>What counts as master data here.</b> Items and their prices. Customers, their credit limits and terms. Warehouses and their accounting. Cost centres. Tax templates. Payment terms. Approval configuration. Roles and permissions, which get their own module. And the settings that sit behind all of it — rounding, naming, tolerances, whether negative stock is permitted.</p>

<p><b>Why it goes unaudited, and the reasons are worth naming because they are not laziness.</b> It is not a transaction, so it does not appear in any transaction listing. It is often changed by people considered technical rather than commercial, so it falls between the operational and IT audit scopes. It rarely has an approval workflow, because approvals slow down a business that needs a price changed today. And it is genuinely tedious to examine without the right query.</p>

<p><b>What makes it testable at all.</b> Module 2 established that version history records the old value, the new value, who changed it and when — and that Item, Customer, Item Price and the rest ship with tracking enabled. So master data changes are queryable exactly like transactions, and the same profiling methods apply: by person, by frequency, by timing, against a distribution.</p>

<p><b>The test that protects every other test.</b> Before anything else in this module, confirm that change tracking is still enabled on the doctypes you rely on. If somebody switched it off, every version query returns empty — cleanly, silently, and reassuringly. That is the single configuration change that would make an auditor blind, and it deserves to be checked first and periodically thereafter.</p>

<blockquote>WATCH-OUT: Master data changes concentrate around events. Prices move before a promotion, credit limits move before a large order, tax settings move at a rate change. Testing a quiet month tells you little; testing the fortnight around a known event tells you a great deal more.</blockquote>

<p><b>One reason this work is welcomed more than transaction testing.</b> Master data findings rarely accuse anybody. Nobody stole anything; a setting was permissive, a limit was never applied, an approval step was never configured. That makes the conversation about design rather than conduct, and design conversations are ones operations managers will engage with willingly. It is a good place for a new audit function to start building credibility before it has to raise anything harder.</p>"""
, [
 C("A price is changed on an item selling 200 times daily across 20 branches. The change:",
   ["Creates an audit trail transaction", "Alters four thousand transactions a day without appearing in any of them",
    "Requires approval by default", "Shows on the price variance report"], 1,
   "Enormous effect, minimal visibility — which is why master data is the highest-leverage area."),
 C("Which single configuration change would make an auditor blind without any error appearing?",
   ["Disabling a workflow", "Switching off change tracking on a doctype",
    "Changing a naming series", "Removing a report role"], 1,
   "Every version query then returns empty, cleanly and reassuringly."),
 C("Testing master data changes in a quiet month rather than around a known event:",
   ["Gives a cleaner baseline", "Tells you little — changes concentrate around promotions, large orders and rate changes",
    "Is the correct approach", "Avoids seasonal distortion"], 1,
   "Test the fortnight around a promotion, a large order or a rate change; a quiet month shows you almost nothing.")]),

("The four questions of any doctype", 12, """<p>Faced with any master record you have never examined — a price list, a tax template, a payment term — four questions establish what control exists. They take about ten minutes and they work on anything.</p>

<p><b>1. Who can change it?</b> Not who does, who can. The permission model answers this, and the answer is frequently wider than anybody believes. A role granted for one purpose carries rights nobody enumerated, and role assignments accumulate as people change jobs.</p>

<p><b>2. Is there a workflow attached?</b> A Workflow defines states and transitions and records a Workflow Action naming who was asked and who acted. If one exists, changes are approved and traceable. If not, a change is immediate and unilateral — and knowing which is true is the difference between testing compliance and testing existence.</p>

<p><b>3. Is change tracking enabled?</b> If yes, you can reconstruct every change with old and new values. If no, you can see only the current state and must rely on somebody's word for what it was before.</p>

<p><b>4. Does anything else depend on it?</b> A price list feeds every sale. A tax template feeds every invoice. A warehouse's accounting feeds the general ledger. The blast radius determines how much the first three questions matter, and it is what turns a technical finding into a business one.</p>

<p><b>Why this framework matters more than any individual test.</b> This track cannot enumerate every doctype in an ERP. What it can do is give you a method that works on the ones it never mentions — a new module, a custom doctype, something a consultant added last year. Four questions, ten minutes, and you know whether a control exists.</p>

<p><b>Where the answers live.</b> Permissions on the Role Permission Manager and on the doctype itself. Workflow as a record naming the document type it governs. Tracking as a property of the doctype. Dependencies from knowing the business, and from following the links out of the record.</p>

<p><b>The finding you will most often produce.</b> Not that somebody did something wrong, but that <b>nothing prevents them</b>. "Any user with the Item Manager role can change any price on any item at any time, with no approval and no notification" is a finding with no wrongdoing in it, and it is usually more valuable than a list of changes — because it describes the exposure rather than one instance of it being exercised.</p>

<blockquote>IMPLEMENTATION TIP: Run the four questions on the ten doctypes that matter most in your business and write the answers on one page. That page is your master data control map, it takes an afternoon, and no such document exists in most retailers.</blockquote>

<p><b>A caution about relying on the documentation.</b> Implementation documents describe what was configured at go-live, and businesses change. A document stating that price changes require approval is evidence of an intention several years ago, not of a control today. Test the live configuration and treat the documentation as a statement of what somebody once wanted — which is useful context and is not the same thing as a control.</p>"""
, [
 C("A consultant added a custom doctype you have never seen. To establish what control exists:",
   ["Read the implementation documentation", "Ask the four questions: who can change it, is there a workflow, is tracking on, what depends on it",
    "Test recent transactions", "Request a demonstration"], 1,
   "The method works on doctypes this track never mentions."),
 C("Which question determines how much the other three matter?",
   ["Who can change it", "Whether tracking is enabled",
    "Whether a workflow exists", "What else depends on it"], 3,
   "Blast radius is what turns a technical finding into a business one."),
 C("The most common master data finding is:",
   ["An unauthorised change", "That nothing prevents the change",
    "A missing approval", "An incorrect value"], 1,
   "It describes the exposure rather than one instance of it being exercised.")]),

("Items, price lists and the rate that moved", 12, """<p>Price is where master data meets money most directly, and in a multi-price-list retailer it is more complicated than it first appears.</p>

<p><b>How pricing is held.</b> An <b>Item Price</b> record ties an item to a <code>price_list</code> at a <code>price_list_rate</code>, with <code>valid_from</code> and <code>valid_upto</code> bounding when it applies. A business typically runs several price lists — standard retail, trade, a promotional list, sometimes one per channel — and the applicable price depends on which list the customer or transaction resolves to.</p>

<p><b>That resolution is itself worth testing.</b> If a customer's <code>default_price_list</code> can be changed by whoever raises their order, the price list is not a control. Establish who sets it and whether the change is tracked.</p>

<p><b>The validity fields are a gift to an auditor.</b> Because a price carries <code>valid_from</code>, a price can be created today and made effective from a past date. That is legitimate for a genuine backdated agreement and it is also exactly how a transaction already recorded can be made to look correctly priced afterwards. <b>Compare the creation timestamp against valid_from</b> and flag material backdating. It is one comparison and almost nobody makes it.</p>

<p><b>The standing tests.</b></p>

<p><b>Price changes by user and frequency</b>, from the version history. Rank against the estate: a user changing prices ten times more often than their peers is doing something worth understanding, even if each change is correct.</p>

<p><b>Changes outside the review cycle.</b> If prices are meant to be reviewed monthly by a named committee, changes at other times are exceptions by definition.</p>

<p><b>Large percentage movements.</b> Not because large is wrong, but because large should be deliberate. A rate moving 40% overnight either reflects something real or reflects a mistake, and both warrant a note.</p>

<p><b>Prices below cost.</b> Where the price list rate falls below the valuation rate, every sale loses money. Usually an error — a decimal, a unit of measure, a promotional price left in place after the promotion ended. Occasionally deliberate. Always worth finding, because it is money leaving with nobody's knowledge.</p>

<p><b>Items themselves.</b> Duplicate items split stock and defeat analysis. Items created and immediately transacted, particularly by the same person, are worth a look. And an item's unit of measure and conversion factor, as module 5 noted, produce differences that look exactly like theft when set wrongly.</p>

<blockquote>IMPLEMENTATION TIP: Compare Item Price creation dates against valid_from across a year, and look at anything backdated by more than a few days. Legitimate backdating is rare and explicable; the test costs one query and it catches a specific and otherwise invisible manipulation.</blockquote>

<p><b>Promotional prices that never ended.</b> A promotional rate is created with a validity window, and where the end date is left open the price simply persists. Nobody notices because the item continues selling normally — at the promotional rate, indefinitely. Query Item Price for records with no valid_upto on a promotional price list, and compare against the promotion calendar. It is a recurring and entirely mechanical loss, and it is usually larger than anyone expects.</p>"""
, [
 C("An Item Price record created today with valid_from set three weeks ago:",
   ["Is a routine correction", "May make already-recorded transactions look correctly priced afterwards",
    "Is prevented by the system", "Affects only future sales"], 1,
   "Compare creation timestamp against valid_from; legitimate backdating is rare and explicable."),
 C("A price list rate sitting below the item's valuation rate means:",
   ["A competitive position", "Every sale of it loses money, usually through a decimal or unit error",
    "A stock valuation problem", "A promotional strategy"], 1,
   "Money leaving with nobody's knowledge, and it is trivially testable."),
 C("If whoever raises an order can change the customer's default price list:",
   ["Pricing is flexible", "The price list is not a control",
    "Approval compensates", "Version history is sufficient"], 1,
   "Establish who sets it and whether the change is tracked.")]),

("Customers, credit limits and terms", 12, """<p>On the sales side, master data decides who may owe you money and how much. It is the mirror of the supplier work in module 4 and it is examined even less.</p>

<p><b>What matters on a customer record.</b> The credit limit, held in the <code>credit_limits</code> table. Payment terms. The default price list. The customer group, which frequently drives pricing and terms by default. And whether the record is enabled at all.</p>

<p><b>The credit limit test that matters.</b> Not whether limits exist — whether they are enforced and whether they move. Query the version history for credit limit changes: who raised them, by how much, and what happened next. <b>A limit raised shortly before a large order to that customer is the pattern to look for</b>, and it is the sales-side equivalent of the bank-change test.</p>

<p>The innocent version is entirely common: a good customer growing, a limit reviewed properly and raised. What distinguishes them is whether the increase went through whatever review exists, and whether the customer subsequently paid.</p>

<p><b>Limits that are exceeded rather than raised.</b> Depending on configuration, exceeding a credit limit may block the order, warn, or do nothing. Establish which. If exceeding a limit merely produces a warning that anybody can dismiss, the limit is advisory — and the finding is the configuration rather than any individual order.</p>

<p><b>Terms as a discount, which module 5 of the finance track established.</b> A customer moved from thirty days to sixty has received a concession worth real money, and it appears nowhere as a discount. Test terms changes the same way as credit limits: who changed them, when, and whether anything was obtained in exchange. Businesses with rigorous discount approval and no terms approval have an uncontrolled discount channel.</p>

<p><b>Customer creation.</b> Who can create a customer, and can the person who raises orders also create the account they raise them for? The same segregation question as suppliers, and the same answer: if one person can do both, a sale can be made to an entity nobody vetted, on terms nobody approved.</p>

<p><b>Dormant and duplicate customers.</b> Duplicates fragment the receivables view so that a customer's total exposure is understated across two records. Dormant accounts reactivating are worth a look, particularly where the record was edited first.</p>

<blockquote>WATCH-OUT: Test credit limit changes against subsequent orders and subsequent payment. A limit raised, a large order shipped, and the customer then failing is a sequence worth understanding regardless of intent — because the same sequence with no intent behind it is a credit control failure, and that is a finding too.</blockquote>

<p><b>Who owns the customer master matters as much as who edits it.</b> In many retailers customer records are created by whoever takes the order and never reviewed by anybody in finance, which means credit terms are effectively set by sales. That is not necessarily wrong — it is fast, and speed matters — but it should be a decision rather than a consequence of how permissions happened to be assigned. Ask who reviews new trade accounts, and how soon after creation.</p>"""
, [
 C("A customer's credit limit is raised shortly before a large order. This is:",
   ["Normal account growth", "The sales-side equivalent of the bank-change test, and worth examining",
    "A pricing matter", "Only relevant if they default"], 1,
   "The innocent version is common; what distinguishes them is review and subsequent payment."),
 C("Exceeding a credit limit produces a warning anybody can dismiss. The finding is:",
   ["The orders that exceeded it", "The configuration — the limit is advisory",
    "The credit controller's performance", "The customer's behaviour"], 1,
   "Establish whether exceeding blocks, warns, or does nothing."),
 C("A business with rigorous discount approval and no terms approval has:",
   ["Balanced controls", "An uncontrolled discount channel",
    "A credit risk only", "A reporting gap"], 1,
   "Extended terms are a concession worth real money and appear nowhere as a discount.")]),

("Warehouses, accounts and cost centres", 12, """<p>The structural master data decides where transactions land in the accounts, and errors here are invisible operationally while being material financially.</p>

<p><b>Warehouses.</b> Each carries accounting configuration determining which account stock value posts to. A warehouse created with the wrong account sends stock value to the wrong place, and nothing in the warehouse operation looks wrong at all — goods arrive, goods leave, counts reconcile. The problem appears only when somebody compares the stock ledger to the general ledger, which is what module 2's <i>Stock And Account Value Comparison</i> does and why it belongs in the quarterly programme.</p>

<p><b>Test the warehouse list itself.</b> How many exist, how many are transacting, and how many were created in the last year by whom. Warehouses proliferate — a temporary one for a project, one per van, one created to solve a problem in 2022 — and each is a location stock can sit in unwatched. <b>A warehouse holding value with no movement for months is worth asking about</b>, because dormant locations are where stock is parked.</p>

<p><b>Cost centres.</b> They determine which part of the business carries a cost, and therefore what every branch profitability figure says. A cost posted to the wrong cost centre makes one branch look worse and another better, with no effect on group profit. That is not fraud, it is usually error — and it distorts precisely the reports management uses to make decisions about branches.</p>

<p>Test cost centre usage by transaction volume and value, and look for defaults doing work they should not: where a cost centre is set as a default and rarely overridden, most costs land there whether they belong or not.</p>

<p><b>Accounts.</b> The chart of accounts is master data too. Accounts created recently, accounts with unusual names, accounts receiving postings that do not fit their description. Suspense and clearing accounts deserve particular attention: they exist to hold items temporarily, and a suspense account with a growing balance and ageing items is where unresolved problems accumulate quietly.</p>

<p><b>The test that surfaces most of this at once.</b> List accounts, cost centres and warehouses by transaction count and value for the period, sorted ascending. The bottom of that list — the ones barely used — is where errors and deliberate misplacement both live, because a rarely-used destination is a rarely-examined one.</p>

<blockquote>IMPLEMENTATION TIP: Ask for the balance and age of every suspense and clearing account quarterly. These accounts should clear. One that has held the same balance for eight months contains something nobody could resolve, and somebody decided to stop trying.</blockquote>

<p><b>Inter-branch and inter-company accounts deserve the same treatment.</b> Where branches transact with each other, the balances between them should net to nil across the group. Where they do not, something has been posted on one side and not the other, and the difference sits unexamined because it belongs to two people and therefore to neither. Ask for the inter-branch position quarterly; a growing unreconciled balance is a reliable indicator of a process that has quietly stopped working.</p>"""
, [
 C("A warehouse configured with the wrong accounting account will:",
   ["Fail on the first transaction", "Operate normally while sending stock value to the wrong place",
    "Block stock movement", "Show as a count difference"], 1,
   "It surfaces only when the stock ledger is compared to the general ledger."),
 C("Branch 4 looks unprofitable. You find rent for Branch 9 posted to its cost centre all year. Group profit is:",
   ["Reduces group profit", "Leaves group profit unchanged while making one branch look worse and another better",
    "Creates a stock difference", "Fails validation"], 1,
   "Usually error rather than fraud, and it lands squarely in the reports used to judge branch managers."),
 C("Listing accounts, cost centres and warehouses by usage ascending surfaces problems because:",
   ["Low usage means low value", "A rarely-used destination is a rarely-examined one",
    "New records cluster there", "It shows configuration errors"], 1,
   "Errors and deliberate misplacement both live at the bottom of that list.")]),

("Workflow, and what approval actually means", 12, """<p>Approval is the control most businesses believe they have and least often verify. In Frappe it is a concrete, inspectable object rather than a policy, which means you can establish exactly what exists in an hour.</p>

<p><b>What a Workflow is.</b> A record attached to a document type, defining <b>states</b> a document can be in, <b>transitions</b> between them, and which role may perform each transition. When somebody acts, a <b>Workflow Action</b> records who was asked and who acted. It is a genuine audit trail of approval, not an inference from a status field.</p>

<p><b>The three things to establish for any document type that matters.</b> Whether a workflow exists at all. What its states and transitions are. And which roles hold each transition, then which users hold those roles — because a beautifully designed workflow where six people hold the approver role is a different control from one where two do.</p>

<p><b>The alternative mechanism.</b> An <b>Authorization Rule</b> enforces a value threshold by role, user, designation or employee, naming an approving role or user. It is simpler than a workflow and it does one thing: above this value, that person must agree. Many businesses use it for purchase orders and nothing else, and never notice that everything else has no threshold at all.</p>

<p><b>The finding that outranks the others.</b> Where neither mechanism exists on a document type that moves money, report the absence. It is not a pattern, it is not an instance, and it does not require anybody to have done anything wrong — and it is more important than either. "No approval is required for any stock write-off at any value" is a complete finding on its own.</p>

<p><b>Testing a workflow that does exist.</b> Compare documents that reached an approved state against the Workflow Actions that should accompany them. Look for approvals by the document's own creator. Look for a single user performing an implausible volume of approvals, which usually means approving is a formality rather than a review. And check whether amendment after approval re-triggers the workflow, because if it does not, approval attaches to a version that no longer exists.</p>

<p><b>The configuration change nobody watches.</b> Workflows can be edited. A transition's permitted role can be widened, a state removed, the whole workflow disabled. Those changes are themselves tracked, and reviewing them periodically is worth more than testing compliance — because a control that was quietly relaxed will show perfect compliance thereafter.</p>

<blockquote>WATCH-OUT: A single user performing hundreds of approvals a month is not evidence of diligence. It is evidence that approving has become a keystroke, and the control is documented rather than performed. Volume per approver is the fastest way to see it.</blockquote>

<p><b>And check who holds the approver role rather than who uses it.</b> A workflow requiring a manager's approval is only as strong as the list of people holding that role, and role membership grows quietly — somebody covers a colleague's leave, a role is granted for a project, a leaver's permissions are never removed. Six approvers where the design assumed two is not a workflow failure; it is a permissions failure wearing a workflow's clothes, and module 7 examines it properly.</p>"""
, [
 C("Which record proves who was asked to approve and who acted?",
   ["The document's status field", "Workflow Action", "The version history", "The Authorization Rule"], 1,
   "A genuine audit trail of approval rather than an inference from a status."),
 C("No approval mechanism exists on stock write-offs at any value. This is:",
   ["Not a finding without an instance of abuse", "A complete finding on its own",
    "A configuration preference", "A matter for IT"], 1,
   "It does not require anybody to have done anything wrong, and it outranks any pattern."),
 C("One user performs hundreds of approvals a month. This indicates:",
   ["Strong engagement", "Approving has become a keystroke rather than a review",
    "An efficient workflow", "Appropriate delegation"], 1,
   "Volume per approver is the fastest way to see a documented rather than performed control.")]),

("The settings nobody reviews", 12, """<p>Beneath the master records sit configuration settings that were chosen once, usually at implementation, often by somebody no longer at the business, and never revisited. Several of them determine whether controls in this track function at all.</p>

<p><b>The ones worth checking, and why each matters.</b></p>

<p><b>Change tracking</b>, per doctype. Already covered and repeated because it protects everything else.</p>

<p><b>Negative stock</b>, permitted or not. Module 5 covered the consequences. What matters here is that it is a choice somebody made, and it should be revisited rather than inherited.</p>

<p><b>Match tolerances</b> on purchase invoices. Module 4 showed that a 5% tolerance on ₦2bn is ₦100m of unchallenged variance. The number should be deliberate.</p>

<p><b>Rounding and precision.</b> How many decimal places, and how rounding differences are posted. Small, systematic, and material over volume — and a rounding account that accumulates a growing balance is telling you something.</p>

<p><b>Naming series.</b> Documents numbered sequentially make gaps detectable; documents numbered by hash do not. If your invoices are sequential, testing for gaps is a completeness test you get free. If they are not, you have lost a check that most auditors assume they have.</p>

<p><b>Tax templates.</b> Which rate applies to what, and whether an item or customer can override it. A wrong template is a compliance exposure rather than a fraud one, and it compounds silently across every affected transaction until somebody reconciles the return.</p>

<p><b>Backdating.</b> Whether documents can be posted to a closed period, and who can. This is the setting that determines whether last month's numbers are final. If any user can post into a closed month, no reported figure is ever settled, and the reports you built findings on can change after you reported them.</p>

<p><b>Permission defaults</b> on new users and roles, which module 7 examines properly.</p>

<p><b>How to test a setting.</b> Read it, record it, and note when it was last changed and by whom. Then ask the question that matters: <i>what would be different if this were set the other way?</i> If the answer is nothing, it does not matter. If the answer is that a control would exist, you have found something.</p>

<blockquote>IMPLEMENTATION TIP: Check whether posting into closed periods is permitted before you rely on any month-end figure. If it is open to ordinary users, every comparative you produce is provisional, and you should say so in your reports rather than discover it when a number moves.</blockquote>

<p><b>Settings that were right and stopped being right.</b> A tolerance set when the business turned over ₦200m may be indefensible at ₦2bn, because the same percentage now permits ten times the absolute variance. The same applies to approval thresholds, which quietly weaken every year that inflation runs and nobody revisits them. A limit of ₦500,000 set four years ago is a materially different control today, and reviewing thresholds against current values is a straightforward annual recommendation almost nobody makes.</p>"""
, [
 C("Documents numbered by hash rather than sequentially mean:",
   ["Better security", "You have lost the gap test most auditors assume they have",
    "Faster processing", "No effect on testing"], 1,
   "Sequential numbering gives you a completeness test free."),
 C("If any user can post into a closed period:",
   ["Corrections are easier", "No reported figure is ever settled, including the ones your findings rest on",
    "Only the current month matters", "Reconciliation compensates"], 1,
   "Check it before relying on any month-end figure, and say so in reports if it is open."),
 C("You have recorded a setting whose significance you do not know. To decide whether it matters, ask:",
   ["When it was last changed", "What would be different if it were set the other way",
    "Who owns it", "Whether it is documented"], 1,
   "If the answer is that a control would exist, you have found something.")]),

("Establishing a configuration baseline", 12, """<p>Testing configuration once tells you the position today. It says nothing about what changed to get here, or what changes next. A baseline solves both, and almost no internal audit function maintains one.</p>

<p><b>What a baseline is.</b> A recorded snapshot of the configuration that matters: the settings from the previous chapter, the workflows and their transitions, the approval rules and thresholds, the roles and their holders, the price lists and their owners, the count of active warehouses, cost centres and accounts. Taken once, dated, and stored where the audit function controls it.</p>

<p><b>What it gives you.</b> Every subsequent review becomes a comparison rather than an examination. "What changed since March?" is a far better question than "what is the configuration?", and it takes minutes rather than a day. It also converts a vague sense that things have drifted into a specific list.</p>

<p><b>Where the evidence is.</b> Version history covers records — workflows, price lists, customers, items. Some settings are singles and change silently unless tracked. So build the baseline from what you can query and record the rest by hand, dated, with a note of who confirmed it. An imperfect baseline is worth a great deal more than none, and the temptation to wait until you can automate it is how it never gets made.</p>

<p><b>Frequency.</b> Quarterly for most businesses. Immediately after any upgrade, migration or major configuration project, because those are when settings move without anybody deciding — defaults reassert, custom changes are lost, new options arrive already switched on.</p>

<p><b>The upgrade point deserves emphasis.</b> A system upgrade can reset a setting to its default. If negative stock was disallowed and the upgrade re-enabled it, nobody would notice for months. Comparing the baseline before and after an upgrade is a specific, cheap, high-value piece of work that almost nobody performs, and it is the single strongest argument for keeping a baseline at all.</p>

<p><b>What to do with the differences.</b> Most will be legitimate and explicable. The point is not to challenge every change but to establish that each was intended — that somebody decided rather than something drifted. A change nobody can account for is a finding regardless of whether it caused harm, because it means changes can happen without a decision.</p>

<blockquote>IMPLEMENTATION TIP: Take the baseline before the next upgrade, whatever else is on your plan. Comparing before and after is half a day of work that will find something, and after the upgrade the opportunity is gone permanently.</blockquote>

<p><b>What to do when you inherit a system nobody documented.</b> This is the common case rather than the exception. Start with the settings that determine whether your own testing works — tracking, backdating, negative stock — then the approval configuration on money-moving doctypes, then the structural lists. That order gets you to a defensible position in about a week, and it means everything you subsequently test rests on a foundation you have actually examined rather than assumed.</p>"""
, [
 C("A configuration baseline turns each subsequent review into:",
   ["A full examination", "A comparison — 'what changed since March?'",
    "A compliance test", "A control assessment"], 1,
   "Minutes rather than a day, and a specific list rather than a sense of drift."),
 C("The strongest argument for keeping a baseline is:",
   ["Regulatory expectation", "A system upgrade can reset a setting to default and nobody would notice for months",
    "It supports the annual plan", "It documents the system"], 1,
   "Comparing before and after an upgrade is half a day that will find something."),
 C("Comparing baselines you find eleven differences; ten are explained and one is not. That one is:",
   ["Only a finding if it caused harm", "A finding regardless, because changes can happen without a decision",
    "An IT matter", "Acceptable if reversible"], 1,
   "The point is establishing that each change was intended.")]),

("The master data tests", 12, """<p>The working programme for this module, with the innocent explanation each test needs before deployment.</p>

<p><b>Configuration tests.</b> Run these first and periodically; they are nil-expected and they protect everything else.</p>

<p><b>Change tracking disabled on a monitored doctype.</b> <i>Innocent:</i> a doctype that never needed tracking, which should be a deliberate and short list.<br>
<b>Backdating into closed periods permitted for ordinary users.</b> <i>Innocent:</i> none really — it is a decision to be made consciously.<br>
<b>Approval mechanism absent on a money-moving doctype.</b> <i>Innocent:</i> a genuinely low-risk document, argued rather than assumed.<br>
<b>Match tolerance above a deliberate figure.</b> <i>Innocent:</i> a considered decision somebody can state.</p>

<p><b>Change tests.</b> From version history, run monthly.</p>

<p><b>Price changes by user, frequency and size.</b> <i>Innocent:</i> a pricing analyst whose job it is, which is why you rank rather than count.<br>
<b>Item Price backdated materially.</b> <i>Innocent:</i> a genuine retrospective agreement, documented.<br>
<b>Credit limit raised then large order.</b> <i>Innocent:</i> a reviewed increase for a growing customer that subsequently paid.<br>
<b>Terms extended.</b> <i>Innocent:</i> a negotiated concession with something obtained in exchange.<br>
<b>Workflow or authorisation configuration changed.</b> <i>Innocent:</i> a deliberate process improvement.</p>

<p><b>Structural tests.</b> Quarterly.</p>

<p><b>Warehouses, cost centres and accounts by usage, ascending.</b> <i>Innocent:</i> seasonal or project locations.<br>
<b>Suspense and clearing account balances and ageing.</b> <i>Innocent:</i> genuinely unresolved items being worked.<br>
<b>Price below cost.</b> <i>Innocent:</i> a deliberate loss-leader, which should be a named list.<br>
<b>Duplicate items and customers.</b> <i>Innocent:</i> genuinely distinct entities with similar names.</p>

<p><b>How master data findings differ in the reporting.</b> They usually have no victim and no incident. Nothing was lost, nobody did anything wrong, and the finding is that something could happen. That makes them easy to defer — there is no urgency, and a recommendation to add an approval step costs somebody time forever.</p>

<p><b>So quantify the exposure rather than describing the gap.</b> Not "no approval is required for price changes" but "any of the fourteen users holding this role can change any price, affecting an average of ₦4.2m of daily sales, with no approval and no notification to anybody." The second version gets acted on. The first gets noted.</p>

<blockquote>WATCH-OUT: Master data recommendations are the ones most often agreed and never implemented, because implementing them slows somebody down permanently and the risk is theoretical until it is not. Track these to closure harder than any other category, and report repeats — a recommendation agreed twice and implemented never is itself the finding.</blockquote>

<p><b>A final word on where this module sits.</b> Master data is the least visible work in the track and, in most retailers, the highest-leverage. It produces no dramatic findings and it quietly determines whether every control in the other modules functions. An audit function that tests transactions rigorously and configuration never is testing whether people followed rules while leaving unexamined the question of whether the rules exist — and the second question is the one that determines the answer to the first.</p>"""
, [
 C("Master data findings are easy to defer because:",
   ["They are technical", "There is no incident and no victim — the finding is that something could happen",
    "They belong to IT", "They are low value"], 1,
   "Which is why the exposure must be quantified rather than the gap described."),
 C("Which framing gets acted on?",
   ["'No approval is required for price changes'", "'Fourteen users can change any price affecting ₦4.2m of daily sales, with no approval or notification'",
    "'Price control is weak'", "'Approval workflow is recommended'"], 1,
   "The first gets noted; the second gets acted on."),
 C("You raised the same price-approval recommendation twice. Both were agreed, neither built. Report:",
   ["A follow-up administrative matter", "Itself the finding",
    "Evidence of low risk", "A resourcing issue"], 1,
   "Track master data recommendations to closure harder than any other category.")]),
]


QUESTIONS = [
 Q("Master data is the least audited area mainly because:", ["It is technical", "It is not a transaction and appears in no transaction listing", "It rarely changes", "It is low value"], 1,
   "Enormous effect, minimal visibility.", "Ch1 §4", "Why master data matters"),
 Q("Which change would make an auditor blind with no error appearing anywhere?", ["Disabling a workflow", "Switching off change tracking", "Removing a report role", "Changing a naming series"], 1,
   "Every version query returns empty, cleanly and reassuringly.", "Ch1 §6", "Why master data matters"),
 Q("Master data changes concentrate:", ["Evenly through the year", "Around events — promotions, large orders, rate changes", "At month end", "During audits"], 1,
   "Test the fortnight around a known event rather than a quiet month.", "Ch1 §7", "Why master data matters"),
 Q("The four questions of any doctype are who can change it, is there a workflow, is tracking on, and:", ["When was it created", "What else depends on it", "Who owns it", "Is it documented"], 1,
   "Blast radius determines how much the other three matter.", "Ch2 §5", "The four questions"),
 Q("Which record names who was asked to approve and who acted?", ["The status field", "Workflow Action", "Version", "Authorization Rule"], 1,
   "A genuine audit trail rather than an inference.", "Ch2 §7", "The four questions"),
 Q("The most common master data finding is that:", ["Somebody changed something wrongly", "Nothing prevents the change", "Approval was skipped", "Values are incorrect"], 1,
   "It describes the exposure rather than one instance of it.", "Ch2 §8", "The four questions"),
 Q("The four-question method is valuable mainly because it works on:", ["Standard doctypes", "Doctypes this track never mentions, including custom ones", "Financial documents", "Master records only"], 1,
   "A new module, a custom doctype, something a consultant added last year.", "Ch2 §6", "The four questions"),
 Q("Item Price validity is bounded by:", ["created and modified", "valid_from and valid_upto", "start_date and end_date", "posting_date"], 1,
   "Which is what makes backdated validity directly testable.", "Ch3 §2", "Items and prices"),
 Q("An Item Price created today with valid_from three weeks ago can:", ["Only affect future sales", "Make already-recorded transactions look correctly priced", "Not be saved", "Be applied automatically"], 1,
   "Compare creation timestamp against valid_from.", "Ch3 §5", "Items and prices"),
 Q("A price list rate below the item's valuation rate means:", ["A competitive price", "Every sale loses money", "A stock error", "A promotional strategy"], 1,
   "Usually a decimal or unit of measure error, and trivially testable.", "Ch3 §9", "Items and prices"),
 Q("If order-raisers can change a customer's default price list:", ["Pricing is responsive", "The price list is not a control", "Approval compensates", "Tracking is sufficient"], 1,
   "Establish who sets it and whether the change is tracked.", "Ch3 §4", "Items and prices"),
 Q("A credit limit raised shortly before a large order is:", ["Normal growth", "The sales-side equivalent of the bank-change test", "A pricing issue", "Only relevant on default"], 1,
   "The innocent version is common; review and subsequent payment distinguish them.", "Ch4 §3", "Customers and credit"),
 Q("If exceeding a credit limit produces a dismissible warning, the finding is:", ["The orders that exceeded it", "The configuration — the limit is advisory", "The credit controller", "Customer behaviour"], 1,
   "Establish whether exceeding blocks, warns, or does nothing.", "Ch4 §5", "Customers and credit"),
 Q("Extended payment terms granted without approval constitute:", ["A service decision", "An uncontrolled discount channel", "A credit risk only", "A terms matter"], 1,
   "A concession worth real money that appears nowhere as a discount.", "Ch4 §6", "Customers and credit"),
 Q("Duplicate customer records are dangerous because they:", ["Slow reporting", "Fragment the receivables view so total exposure is understated", "Break pricing", "Duplicate invoices"], 1,
   "The customer's total exposure is split across two records.", "Ch4 §8", "Customers and credit"),
 Q("A warehouse with the wrong accounting configuration will:", ["Block transactions", "Operate normally while stock value posts to the wrong place", "Fail reconciliation immediately", "Show count differences"], 1,
   "It surfaces only in the stock-to-general-ledger comparison.", "Ch5 §2", "Structural master data"),
 Q("A cost posted to the wrong cost centre:", ["Reduces group profit", "Distorts branch reports used for decisions", "Creates a stock issue", "Fails validation"], 1,
   "Usually error, and it affects exactly the reports that matter.", "Ch5 §5", "Structural master data"),
 Q("Sorting warehouses, accounts and cost centres by usage ascending surfaces problems because:", ["New records cluster there", "A rarely-used destination is a rarely-examined one", "Low usage means low value", "Errors are random"], 1,
   "Errors and deliberate misplacement both live at the bottom of the list.", "Ch5 §8", "Structural master data"),
 Q("A suspense account holding the same balance for eight months contains:", ["A timing difference", "Something nobody could resolve, and somebody stopped trying", "A rounding accumulation", "A migration artefact"], 1,
   "These accounts should clear.", "Ch5 §7", "Structural master data"),
 Q("A Workflow defines states, transitions and:", ["Value thresholds", "Which role may perform each transition", "Naming series", "Field permissions"], 1,
   "With Workflow Action recording who was asked and who acted.", "Ch6 §2", "Workflow and approval"),
 Q("An Authorization Rule enforces:", ["State transitions", "A value threshold with a named approving role or user", "Field-level access", "Document naming"], 1,
   "Simpler than a workflow, and it does one thing.", "Ch6 §4", "Workflow and approval"),
 Q("Where no approval mechanism exists on a money-moving doctype you should:", ["Test the largest transactions", "Report the absence as a complete finding", "Recommend monitoring", "Sample recent changes"], 1,
   "It requires nobody to have done anything wrong and outranks any pattern.", "Ch6 §5", "Workflow and approval"),
 Q("If amendment after approval does not re-trigger the workflow:", ["Amendments need monitoring", "Approval attaches to a version that no longer exists", "The workflow needs a state", "Approval should move later"], 1,
   "Which makes every limit advisory.", "Ch6 §6", "Workflow and approval"),
 Q("A control that was quietly relaxed will subsequently show:", ["Increased exceptions", "Perfect compliance", "No change", "More approvals"], 1,
   "Which is why reviewing configuration changes beats testing compliance.", "Ch6 §7", "Workflow and approval"),
 Q("Sequential document numbering gives you:", ["Better performance", "A completeness test for free", "Stronger security", "Simpler reporting"], 1,
   "Hash-based numbering loses the gap test most auditors assume they have.", "Ch7 §5", "Settings"),
 Q("If ordinary users can post into closed periods:", ["Corrections are simpler", "No reported figure is ever settled", "Only the current month is affected", "Reconciliation compensates"], 1,
   "Including the figures your findings rest on.", "Ch7 §8", "Settings"),
 Q("The question that determines whether a setting matters is:", ["When it changed", "What would differ if it were set the other way", "Who owns it", "Whether it is documented"], 1,
   "If the answer is that a control would exist, you have found something.", "Ch7 §9", "Settings"),
 Q("A rounding account with a growing balance is:", ["Expected", "Telling you something", "A migration artefact", "Immaterial by definition"], 1,
   "Small and systematic becomes material over volume.", "Ch7 §4", "Settings"),
 Q("A configuration baseline converts each review into:", ["A control assessment", "A comparison", "A compliance test", "A full examination"], 1,
   "'What changed since March?' takes minutes rather than a day.", "Ch8 §3", "Configuration baseline"),
 Q("The strongest argument for a baseline is that an upgrade can:", ["Introduce bugs", "Reset a setting to default with nobody noticing for months", "Change the interface", "Require retraining"], 1,
   "Comparing before and after is half a day that will find something.", "Ch8 §6", "Configuration baseline"),
 Q("An imperfect baseline recorded by hand is:", ["Not worth keeping", "Worth a great deal more than none", "Only useful if automated", "A compliance risk"], 1,
   "Waiting until it can be automated is how it never gets made.", "Ch8 §4", "Configuration baseline"),
 Q("A configuration change nobody can account for is:", ["Only a finding if harmful", "A finding regardless", "An IT matter", "Acceptable if reversible"], 1,
   "It means changes can happen without a decision.", "Ch8 §7", "Configuration baseline"),
 Q("Baselines should be taken quarterly and also:", ["At year end", "Immediately after any upgrade or migration", "Before each audit", "When staff change"], 1,
   "Those are when settings move without anybody deciding.", "Ch8 §5", "Configuration baseline"),
 Q("Which is a nil-expected configuration test?", ["Price changes by user", "Change tracking disabled on a monitored doctype", "Credit limit changes", "Warehouse usage"], 1,
   "Run first and periodically; it protects everything else.", "Ch9 §2", "Master data tests"),
 Q("The innocent explanation for frequent price changes by one user is:", ["A system fault", "A pricing analyst whose job it is", "A promotion", "Duplicate items"], 1,
   "Which is why you rank against peers rather than count.", "Ch9 §4", "Master data tests"),
 Q("Master data recommendations are most often:", ["Rejected", "Agreed and never implemented", "Implemented immediately", "Escalated"], 1,
   "Implementing them slows somebody down permanently and the risk is theoretical until it is not.", "Ch9 §8", "Master data tests"),
 Q("A recommendation agreed twice and implemented never is:", ["A follow-up matter", "Itself the finding", "Evidence of low risk", "A resourcing problem"], 1,
   "Report repeats explicitly.", "Ch9 §8", "Master data tests"),
 Q("Quantifying a master data exposure means stating:", ["The control gap", "Who can do what, affecting how much, with what oversight", "The policy breached", "The remediation cost"], 1,
   "The first gets noted; the second gets acted on.", "Ch9 §7", "Master data tests"),
 Q("Which structural test runs quarterly rather than monthly?", ["Price changes by user", "Suspense account balances and ageing", "Credit limit changes", "Terms extensions"], 1,
   "Structural tests move slowly and monthly adds nothing.", "Ch9 §6", "Master data tests"),
 Q("The innocent explanation for a price below cost is:", ["A rounding error", "A deliberate loss-leader, which should be a named list", "A stock revaluation", "A currency movement"], 1,
   "If no such list exists, every instance is an error.", "Ch9 §6", "Master data tests"),
 Q("Warehouses proliferate because:", ["The system creates them", "Temporary and project locations are created and never retired", "Migration duplicates them", "Each branch needs several"], 1,
   "Each is a location stock can sit in unwatched.", "Ch5 §3", "Structural master data"),
 Q("A dormant warehouse holding value with no movement for months is:", ["Normal for seasonal stock", "Worth asking about — dormant locations are where stock is parked", "A reporting artefact", "A closing candidate only"], 1,
   "Test the warehouse list itself, not just the transactions.", "Ch5 §4", "Structural master data"),
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
    rebalance(QUESTIONS, "control:master_data:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:master_data:checks")

    mod = {
        "title": "Master Data and Configuration",
        "desc": ("Set once, and it governs thousands of transactions. The four questions "
                 "that establish what control exists on any doctype, backdated price "
                 "validity, credit limits raised before large orders, warehouses and cost "
                 "centres, what approval actually means in a workflow, the settings nobody "
                 "reviews, and keeping a configuration baseline."),
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
