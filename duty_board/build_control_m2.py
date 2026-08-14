#!/usr/bin/env python3
"""Build 'Getting the Data' into academy_control_data.json.

Module 2 of System-Based Internal Control in a Retail Environment, written
first because everything else in the track depends on it and because it is the
module most internal auditors in this market are missing entirely.

Product facts here were read from ERPNext and Frappe v15 source rather than
recalled: the four Report types, the Version diff structure, prepared reports,
the roles table on Report, and the field names used in the worked examples. The
Closer track is the reason for that discipline — it shipped four order statuses
the product does not have.

Audience note that governs the whole register: these are qualified accountants.
Nothing explains double entry, a margin or an accrual. What is explained is the
system, and how to interrogate it.

Merges into the data file. Rebalance folded into the build.

Run from the app package directory:  python3 build_control_m2.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "getting_data"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Why extraction is the first competence", 12, """<p>An auditor who cannot get their own data is dependent on the people they examine. That sentence is the whole argument for this module, and it is worth sitting with before anything technical.</p>

<p><b>Consider how it usually goes.</b> You need eighteen months of stock adjustments by branch. You email IT. Someone runs something and sends a spreadsheet. You do not know precisely what was filtered, whether cancelled documents were included, or which date field was used. If a finding is later challenged, you cannot answer any of those questions — and the person who produced the extract reports to the operations director whose branch you are examining.</p>

<p>Nothing in that is dishonest. It is simply not evidence.</p>

<p><b>The second consequence is subtler and more expensive: you ask smaller questions.</b> An auditor who must requisition every extract asks for what they can justify requesting. An auditor who can query directly asks anything, including the speculative question that turns out to matter. Most real findings begin as an idle look at a distribution, and idle looks do not survive a requisition process.</p>

<p><b>What the system environment actually offers.</b> Every document in ZhiftERP is a row in a table, queryable in full. That changes the fundamental method available to you.</p>

<p>Traditional audit samples: pull fifty purchase orders, examine them, extrapolate. It is what you do when the population is paper in a cabinet, and it carries sampling risk — the fifty may be clean while the population is not.</p>

<p>Here you can test the population. Every purchase order raised in eighteen months, every one of them, against the rule. When it comes back clean you can write <i>"no purchase order in the period was split below the approval limit"</i> rather than <i>"the fifty examined were in order."</i> Those are different assurances, and only one of them is worth what an internal audit function costs.</p>

<p><b>The corollary for exceptions.</b> Population testing changes what a hit means. In sampling, one exception in fifty implies a rate and you argue about extrapolation. In population testing, one exception is one exception — you can name it, price it, and put the document number in the report. The conversation moves from statistics to facts, and facts are much harder to negotiate down.</p>

<p><b>What this module builds.</b> Enough command of the platform to answer your own questions: where data lives, how to filter a population, when to move from the list view to a query, how to read a version history, and how to leave a working paper somebody else can reproduce. Nothing here requires a developer. All of it requires you to stop asking.</p>

<blockquote>WATCH-OUT: The most common reason an audit finding is dismissed is not that it was wrong. It is that the auditor could not say exactly how the number was produced, so the discussion became about the extract rather than the exception. Reproducibility is not administrative tidiness; it is what makes a finding survive contact with the person it concerns.</blockquote>

<p><b>One boundary worth setting early, because it will be tested.</b> Reading data is not the same as changing it, and an internal auditor should have the first and never the second. Read-only access to everything, write access to nothing operational — that is the posture that protects your independence and, incidentally, protects you. An auditor who can post a correction can be asked to, and will one day be asked by somebody senior in a situation where refusing is uncomfortable. Not having the ability is a better defence than having it and declining.</p>"""
, [
 C("An extract you requested from IT supports a finding. It is challenged. The weakness is:",
   ["The sample was too small", "You cannot state exactly what was filtered, so the discussion becomes about the extract",
    "IT lacks audit training", "The data was not certified"], 1,
   "And the person who produced it usually reports to the director whose area you are examining."),
 C("Testing the whole population rather than a sample changes a clean result from:",
   ["A stronger sample", "'The fifty examined were in order' to 'no instance occurred in the period'",
    "An opinion to a certification", "A test to a review"], 1,
   "Only one of those two assurances is worth what an internal audit function costs."),
 C("The subtler cost of depending on others for extracts is that you:",
   ["Wait longer", "Ask smaller questions — only those you can justify requesting",
    "Pay more", "Lose independence formally"], 1,
   "Most real findings begin as a speculative look at a distribution, and those do not survive a requisition process.")]),

("Doctypes, tables and the list view", 12, """<p>Every business object in ZhiftERP is a <b>doctype</b>: Sales Invoice, Purchase Order, Stock Entry, Item, Supplier, User. Each is a table in the database, and each document is a row. Understanding that mapping is most of what you need.</p>

<p><b>Where the data physically sits.</b> A doctype named Sales Invoice is stored in a table called <code>tabSales Invoice</code>. Its line items are a separate child table, <code>tabSales Invoice Item</code>, each row carrying a <code>parent</code> field holding the invoice name. That parent-child split is the single most important structural fact in the platform, because it determines which questions need which table.</p>

<p>Questions about <i>documents</i> — how many invoices, by whom, when — are answered from the parent. Questions about <i>lines</i> — which items, at what discount, at what rate — must be answered from the child, because the parent does not contain them.</p>

<p><b>The list view is a query tool, not a menu.</b> Open any doctype list and you have filters, sorting, column selection and export. Most auditors use it as navigation and never notice they are holding a general-purpose extraction instrument.</p>

<p><b>Filters do more than equals.</b> The comparators available include <code>like</code> and <code>not like</code> for partial matches, <code>in</code> and <code>not in</code> for sets, <code>between</code> for ranges and dates, <code>is set</code> and <code>is not set</code> for presence, and the ordinary greater-than and less-than. A great deal of real testing is nothing more than the right combination of these.</p>

<p><b>Report view is where it becomes an audit tool.</b> Switching a list into report view gives you columns of your choosing, totals, and grouping. "Stock Entries of type Material Issue, this quarter, grouped by owner, with total value" is a report-view configuration, not a programming task, and it is a real adjustment-concentration test.</p>

<p><b>Two fields present on every document</b> and quietly essential. <code>owner</code> is who created it — not who it belongs to, which trips people up constantly. <code>modified_by</code> is who last changed it. Together they answer a large share of "who did this" questions before you go anywhere near the version history.</p>

<p><b>And one distinction that will otherwise cost you.</b> <code>docstatus</code> holds 0 for draft, 1 for submitted, 2 for cancelled. A filter that omits it silently includes drafts and cancellations in your population. Almost every wrong number an auditor produces in ZhiftERP comes from forgetting this, and the resulting figure looks entirely plausible.</p>

<blockquote>IMPLEMENTATION TIP: Before running any test, decide what <code>docstatus</code> you mean and set it explicitly. Cancelled documents belong in a void analysis and nowhere else; drafts are not transactions at all. Making this a habit removes the commonest source of a number you cannot defend.</blockquote>

<p><b>The other structural fact worth knowing: naming.</b> Documents carry a system name — the value in <code>name</code> — which is what links records together. For most transaction doctypes it is the human-readable number you see, but not always, and a child row's link to its parent is by that name rather than by anything visible on screen. When a query returns something that looks like a code rather than an invoice number, that is what you are looking at, and it is the value to use when joining anything.</p>"""
, [
 C("You need discounts by line across a quarter. The data lives in:",
   ["tabSales Invoice", "tabSales Invoice Item, the child table",
    "The General Ledger", "The Version table"], 1,
   "Document-level questions come from the parent; line-level questions must come from the child."),
 C("A test returns a plausible but wrong figure. The most likely single cause is:",
   ["A date field mix-up", "docstatus was not set, so drafts and cancellations were included",
    "The wrong warehouse", "Missing permissions"], 1,
   "0 is draft, 1 submitted, 2 cancelled. Omitting it silently widens every population."),
 C("The `owner` field on a document records:",
   ["The customer or supplier", "Who created it", "Who last modified it", "The assigned officer"], 1,
   "It is who created the record, not who it belongs to — a distinction that trips people up constantly.")]),

("Report Builder: population filters", 12, """<p>ZhiftERP has four kinds of report, and knowing which you are using matters because they differ in who can create them and how far they can reach.</p>

<p><b>Report Builder</b> is a saved list view: a doctype, a set of filters, chosen columns, optional grouping and totals. No code. This is where most of your standing tests should live, because a colleague can open, inspect and re-run one without your help.</p>

<p><b>Query Report</b> is stored SQL, covered in the next chapter. <b>Script Report</b> is Python, and belongs to developers. <b>Custom Report</b> is a saved variant of an existing report with different filters and columns — the fastest way to turn a shipped report into your own standing test.</p>

<p><b>What Report Builder handles well.</b> Anything expressible as filters on one doctype and its immediate links. In practice that is a great deal:</p>

<p>Purchase Orders above a value, this year, by supplier. Stock Entries of type Material Issue, grouped by <code>owner</code>. Sales Invoices where <code>docstatus</code> is 2, by user and branch. Items whose <code>modified</code> date falls in the last month. Users with <code>enabled</code> set and <code>last_active</code> older than ninety days.</p>

<p>Each of those is a genuine control test and none needs a line of code.</p>

<p><b>Where it stops.</b> It cannot join two unrelated doctypes, aggregate across a relationship, or compare a document to another document. "Purchase orders whose supplier's bank details changed in the preceding week" spans three tables and a time relationship, and it needs a query. Recognising the boundary quickly is a skill in itself: if you find yourself exporting two reports to compare them in a spreadsheet, you have crossed it.</p>

<p><b>Save it, name it properly, and give it away.</b> A report saved as <code>P2P-002 Purchase orders above approval limit</code> is an asset of the audit function. The same filters applied ad hoc and forgotten are a personal habit that leaves when you do. Naming to the test code from your programme is what makes the library navigable a year later.</p>

<p><b>The `roles` table on a report</b> controls who can run it. Worth setting deliberately: an audit test visible to the department it examines is not a secret, but it does change behaviour — and in some cases you will want it to, while in others you will not.</p>

<blockquote>IMPLEMENTATION TIP: Build every standing test as a saved Report Builder report where the filters allow it, and only drop to a query when they genuinely do not. A test another auditor can read and re-run without you is worth more than a cleverer one that only you can operate.</blockquote>

<p><b>A practical note on columns.</b> Report Builder shows a default column set that is rarely the one you want, and the columns you add determine whether the output is investigable. As a rule include the document name, the date that defines your population, the person, the branch or warehouse, and the value. Five columns, every time, before whatever the test specifically needs. An output missing the person or the branch will send you back to the system for every single row.</p>"""
, [
 C("You find yourself exporting two reports to compare them in a spreadsheet. This means:",
   ["The reports are badly built", "You have passed what Report Builder can do and need a query",
    "The data is inconsistent", "You need a Script Report"], 1,
   "Report Builder cannot join unrelated doctypes or compare one document to another."),
 C("A standing test built as a saved report rather than ad-hoc filters is:",
   ["Slower to run", "An asset of the function rather than a personal habit that leaves with you",
    "Harder to modify", "Restricted to managers"], 1,
   "Naming it to the programme's test code is what makes the library navigable a year later."),
 C("The fastest way to turn a shipped ERPNext report into your own standing test is:",
   ["Copy the SQL into a Query Report", "Save it as a Custom Report with your filters and columns",
    "Request a Script Report", "Export and rebuild it"], 1,
   "Custom Report is a saved variant of an existing report — no code, and it inherits the underlying logic.")]),

("Query Report and the standing programme", 12, """<p>When filters are not enough, a Query Report stores SQL against the database and presents the result as an ordinary report with parameters. It is the instrument behind most serious exception tests, and an auditor does not need to be a developer to use it — but does need to be careful.</p>

<p><b>What a query unlocks.</b> Joins across unrelated doctypes; aggregation with grouping and having-clauses; comparison of a document against another document; date arithmetic between events. Which is to say: nearly every test in the shipped library, because real exceptions are usually about a <i>relationship</i> between records rather than a property of one.</p>

<p><b>The pattern almost all of them share.</b> Take the population, join what it must be compared against, filter to the condition that should never occur, and return enough columns to investigate — document number, date, person, branch, value. The last part matters: a report returning a count is a statistic, and a report returning document numbers is a work list.</p>

<p><b>Three rules that keep queries defensible.</b></p>

<p><b>Set docstatus explicitly.</b> Always. Repeated from the last chapter because it is the error people keep making after they have learned it.</p>

<p><b>Expose the threshold as a parameter, not a constant.</b> A query with <code>500000</code> buried in it becomes stale silently when the approval limit changes. A parameter is visible, adjustable and — importantly — recorded on the run, so a result is interpretable months later.</p>

<p><b>Return the identifiers.</b> Every row should be traceable to a document somebody can open. An exception you cannot navigate to is an accusation without an address.</p>

<p><b>Permissions are real here.</b> Creating Query Reports requires elevated rights, precisely because SQL bypasses the ordinary permission layer. That is a control worth understanding from both sides: it is why you may need your query approved, and it is why <i>your</i> access to create them is itself something an external auditor should examine.</p>

<p><b>Long-running queries</b> can be marked as prepared reports, which run in the background and notify you. A test spanning eighteen months across twenty branches will need this. It is not a workaround; it is the intended mechanism, and using it stops people writing artificially narrow tests to avoid timeouts.</p>

<p><b>What a standing programme looks like.</b> Twenty to thirty saved tests, each named to a code, each with a stated frequency, grouped into programmes — monthly branch, quarterly master data, annual access review. Built once, refined continuously, run on schedule. That is the difference between an audit function with a method and one with a rota of visits.</p>

<blockquote>WATCH-OUT: A query is only as sound as its joins. A join that silently multiplies rows — one invoice matching three version records — will inflate every total and look entirely reasonable. Check the row count against a known population before trusting any aggregate you did not build yourself.</blockquote>

<p><b>On writing SQL when you are not a developer.</b> You do not need to be fluent to be useful here. The queries behind almost every test in the library are structurally similar, and adapting an existing one — changing the doctype, the date field, the threshold — will carry you a long way. What you must do is verify: run the query with a filter so narrow that you can check the answer by hand, confirm it returns what you expect, then widen it. A query you have never sanity-checked against a known answer is a guess with a semicolon at the end.</p>"""
, [
 C("A query has the approval limit written into it as 500000. The risk is:",
   ["It runs slowly", "It goes stale silently when the limit changes, and the run is uninterpretable later",
    "It needs developer rights", "It cannot be scheduled"], 1,
   "A parameter is visible, adjustable and recorded on the run."),
 C("An exception report returning only counts by branch is:",
   ["Sufficient for reporting", "A statistic rather than a work list — it needs document identifiers",
    "The correct summary level", "Better for confidentiality"], 1,
   "An exception you cannot navigate to is an accusation without an address."),
 C("Your aggregate total is far larger than the population you expected. Check first:",
   ["The date range", "Whether a join is multiplying rows",
    "The docstatus filter", "Branch permissions"], 1,
   "One invoice matching three version records inflates every total and looks entirely reasonable.")]),

("Reading the version history", 12, """<p>The version history is the most under-used evidence in the platform and the reason several tests in your programme are possible at all. Most auditors know it exists and have never read one properly.</p>

<p><b>What is actually recorded.</b> For every tracked change, the platform stores the field that changed, its <b>old value and its new value</b>, along with who made the change and when. Child table rows added, removed and modified are captured too. This is not a log saying "this document was edited" — it is a reconstruction of exactly what it said before.</p>

<p>So the test is not "was the price changed" but "changed from what, to what, by whom, and when relative to the transaction that benefited from it."</p>

<p><b>Cancel-and-amend, which matters enormously for retail.</b> A submitted document is not edited in place; it is cancelled and a new amended document created. The platform compares the amendment against the document it amended, so the version record shows precisely what differed between the two. A cashier's void therefore leaves a full trail: original, cancellation, replacement, and the difference between them.</p>

<p>This is why an amendment is investigable rather than merely visible, and it is worth knowing before you accept anybody's assurance that "the system does not keep that."</p>

<p><b>Two limits, and both are tests rather than footnotes.</b></p>

<p><b>Tracking is a per-doctype setting</b> and it can be switched off. It ships enabled on Sales Invoice, Purchase Order, Stock Entry and Item, but a configuration change could disable it — and every test resting on version history would then return nothing, cleanly and silently. <b>Confirming tracking is still enabled belongs first in your programme</b>, before any test that depends on it.</p>

<p><b>Long-text fields are not diffed.</b> Text editor, code and markdown fields are excluded, so narrative fields, terms and internal notes change without a recorded prior value. Rarely material, occasionally exactly where a dispute lives.</p>

<p><b>How to use it in practice.</b> Version records are queryable like anything else, which means "all changes to supplier bank details in the last quarter, by user" is a report rather than a manual trawl. That single query is the foundation of the highest-value test in the whole programme, and it is unavailable to an auditor who thinks of version history as something you click on one document at a time.</p>

<blockquote>IMPLEMENTATION TIP: When investigating any suspicious document, read its version history before speaking to anybody. It tells you what the document said originally, who changed it and when — and going into a conversation already knowing that changes the conversation completely.</blockquote>

<p><b>What the version history does not tell you.</b> It records what changed, not why, and not what was authorised. A price changed from ₦4,800 to ₦4,200 by a named user at a named time is a fact; whether it was approved is a separate question answered by the workflow record or the authorisation rule, if either applies. Treating a version record as evidence of unauthorised action is a leap, and it is the leap most likely to make an auditor look careless in a meeting where the approval is then produced.</p>"""
, [
 C("A price was changed. The version history lets you establish:",
   ["That an edit occurred", "The old value, the new value, who changed it and when",
    "Only the current value", "The approval that permitted it"], 1,
   "It is a reconstruction of what the document said before, not a log that something happened."),
 C("A cashier voids a transaction. The trail available is:",
   ["Only the cancelled document", "Original, cancellation, replacement, and the difference between them",
    "A deletion record", "Nothing, once cancelled"], 1,
   "The platform compares an amendment against the document it amended."),
 C("Which test belongs FIRST in a programme that relies on version history?",
   ["Price changes by user", "Confirming change tracking is still enabled on the monitored doctypes",
    "Supplier bank changes", "Credit limit changes"], 1,
   "If tracking is disabled, every dependent test returns nothing — cleanly, silently and wrongly.")]),

("The self-integrity reports", 12, """<p>ERPNext ships a family of reports almost nobody runs, and they are the most audit-native things in the product. They do not describe the business; they test whether the record is internally consistent with itself.</p>

<p>That is where a system-based audit should begin, because every other test you run assumes the underlying data is sound. If the stock ledger does not reconcile to the general ledger, a shrinkage analysis is arithmetic on a broken foundation.</p>

<p><b>The ones worth knowing by name.</b></p>

<p><b>Stock Ledger Invariant Check</b> — tests that the running quantity and valuation in the stock ledger behave consistently entry by entry. Hits indicate the ledger itself is disordered, usually from backdated entries or interrupted processing.</p>

<p><b>Incorrect Balance Qty After Transaction</b> — finds ledger entries where the balance carried forward does not follow from the movement recorded. Structural, not operational.</p>

<p><b>Stock And Account Value Comparison</b> — compares stock value in the inventory ledger against the corresponding accounts in the general ledger. A difference here means inventory and finance are telling different stories, and every stock-related financial figure is affected.</p>

<p><b>Invalid Ledger Entries</b> and <b>General And Payment Ledger Comparison</b> — the accounting equivalents, testing that ledger entries are well formed and that the payment ledger agrees with the general ledger.</p>

<p><b>Calculated Discount Mismatch</b> — finds invoice lines where the discount recorded does not agree with the arithmetic of price and rate. Directly useful in revenue testing.</p>

<p><b>Stock Qty Vs Batch Qty</b> and <b>Stock Qty Vs Serial No Count</b> — where batches or serial numbers are used, tests that the detail agrees with the total.</p>

<p><b>How to use them.</b> Run the set quarterly and expect nil. These are not analytical tests where a distribution is interesting; a hit is a defect. Nil results are the normal outcome and they are worth recording as such, because a clean run is itself evidence that the data underlying your other work is sound.</p>

<p><b>What a hit actually means.</b> Usually a technical problem rather than a person — an interrupted posting, a backdated entry, a migration artefact. So the response is a support conversation rather than an investigation. But it is urgent, because until it is resolved you cannot rely on any figure derived from that ledger, and any finding you have raised from it is exposed.</p>

<p><b>Why almost nobody runs these.</b> They are absent from every operational dashboard, they return nothing interesting in a healthy system, and their names describe internal mechanics rather than business problems — <i>Stock Ledger Invariant Check</i> sounds like a developer's tool, and in origin it is. That is exactly why they are worth adopting: shipped, free, unused, and testing something no operational report examines. Adding the set to a quarterly programme costs an hour once.</p>

<blockquote>IMPLEMENTATION TIP: Run the integrity set before beginning any substantive review, not after. A shrinkage finding raised against a stock ledger that does not reconcile to the general ledger will be dismissed the moment somebody notices, and they will be right to dismiss it.</blockquote>"""
, [
 C("Stock And Account Value Comparison returns differences. The immediate implication is:",
   ["A shrinkage problem", "Inventory and finance are telling different stories, so stock-derived figures are unreliable",
    "A pricing error", "A counting error at one branch"], 1,
   "Every stock-related financial figure is affected until it is resolved."),
 C("A hit on Stock Ledger Invariant Check most often indicates:",
   ["Theft", "A technical defect such as a backdated entry or interrupted posting",
    "A valuation policy change", "Poor counting"], 1,
   "The response is a support conversation rather than an investigation — but an urgent one."),
 C("The integrity set should be run:",
   ["After completing substantive testing", "Before beginning it",
    "Only when a problem is suspected", "Annually with the external audit"], 1,
   "A finding raised from a ledger that does not reconcile will be dismissed, and rightly.")]),

("Running a test in Audit & Exceptions", 12, """<p>The tests you build by hand are yours until you leave. The Audit & Exceptions app exists to make them the function's — stored, scheduled, versioned, with a result history attached.</p>

<p><b>What an Audit Test holds.</b> The definition: a code, the risk it addresses, the control it evidences, the query or filter, the threshold as a visible parameter, a severity, a frequency, and a note describing what an innocent hit looks like.</p>

<p><b>That last field deserves attention.</b> A test whose hits are usually innocent trains everybody to ignore its output, and an ignored test is worse than no test because it produces false assurance. If you cannot describe an innocent hit before deploying a test, the test is not ready — you do not yet understand the population well enough to interpret it.</p>

<p><b>An Audit Test Run is immutable and snapshots the result.</b> This is the property that makes findings survive time. A finding raised in March rests on the data as it stood in March; by September the documents may have been amended, corrected or cancelled. Re-running the query then produces a different answer, and without a snapshot you cannot show what you saw. The run also records the parameters as they stood, so a result remains interpretable after a threshold changes.</p>

<p><b>Reading a run.</b> Three questions, in order. How many rows, against how many you expected? Are the hits concentrated — one branch, one user, one week — or spread? And are they the same hits as last time, which distinguishes a persistent condition from a new event?</p>

<p><b>Nil-expected tests versus analytical tests</b> behave differently and should be read differently. A nil-expected test — refunds against no original, negative stock — returns nothing in a healthy month, and any row is a finding. An analytical test — void rates, adjustment frequency — always returns rows, and the question is the shape of the distribution rather than the existence of output. Treating the second like the first produces a report full of findings that are simply normal business.</p>

<p><b>Suppression, and why it must expire.</b> Where a hit is genuinely known and accepted, an exception note records it with a reason and an end date. Without the mechanism, known-innocent hits accumulate until the report is unreadable. Without the expiry, a suppression is a deleted test with extra steps — and the condition it covered will change without anybody revisiting the decision.</p>

<blockquote>WATCH-OUT: The failure mode of every exception system is the same. Tests are added, hits accumulate, nobody reads the output, and the whole apparatus becomes a report nobody opens. Fewer tests with lower false-positive rates, reviewed properly, beat a comprehensive library nobody trusts.</blockquote>

<p><b>How to introduce a new test without poisoning the report.</b> Run it in silence first — scheduled, results reviewed by you alone, for a month. You will find out what it actually returns in normal conditions, which is nearly always more than you expected. Tune the threshold, write the false-positive note from what you saw rather than from what you imagined, and only then put it into the live programme. A test released untuned generates a wave of hits, exhausts the goodwill of whoever must investigate them, and is quietly ignored thereafter.</p>"""
, [
 C("A test's hits are usually innocent. The consequence is:",
   ["A minor inefficiency", "Everybody learns to ignore its output, producing false assurance",
    "More investigation work", "A higher severity grade"], 1,
   "If you cannot describe an innocent hit before deploying, you do not understand the population well enough."),
 C("A finding raised in March is challenged in September and the underlying documents have since been amended. You rely on:",
   ["Re-running the query", "The immutable run snapshot taken at the time",
    "The document version history", "The original report definition"], 1,
   "Re-running produces a different answer, and without the snapshot you cannot show what you saw."),
 C("An analytical test such as void rate always returns rows. Reading it like a nil-expected test produces:",
   ["Better coverage", "A report full of findings that are simply normal business",
    "Fewer false positives", "A stronger distribution"], 1,
   "The question for an analytical test is the shape of the distribution, not the existence of output.")]),

("Working papers that reproduce", 12, """<p>A test nobody else can re-run is an opinion. The standard to hold yourself to is that a competent colleague, given your file and no access to you, could reproduce the number exactly. Very little internal audit work in this market meets it.</p>

<p><b>What a reproducible working paper contains.</b></p>

<p><b>The question</b>, stated before the answer. What were you testing, and what would have made you conclude the control was working?</p>

<p><b>The population and how it was defined.</b> Doctype, date range, <code>docstatus</code>, branch scope, and any exclusions with their reason. This is where most files fail — the extract is present and the definition of what it contains is not.</p>

<p><b>The extraction itself.</b> The saved report name and test code, or the query, with parameters as used. Not "extracted from the system", which tells a reviewer nothing.</p>

<p><b>The result</b>, retained as it was, not as it is now.</p>

<p><b>The reasoning</b> from result to conclusion, including hits examined and found innocent. A file recording only the exceptions you pursued hides the judgement you exercised, and the judgement is the professional part.</p>

<p><b>The conclusion</b>, expressed against the question you began with.</p>

<p><b>Why this matters more here than in a manual environment.</b> Paper working papers contained the evidence physically — the invoice was in the file. A system-based paper contains a reference to data that can change after you looked. The extract is your only fixed point, and its definition is what makes it meaningful. An extract without its definition is a spreadsheet of unknown provenance, however tidy.</p>

<p><b>The date-field trap, which is worth naming specifically.</b> Documents carry several dates: creation, modification, posting, transaction, due. A population defined by the wrong one is wrong in a way that looks entirely reasonable — a "March" population built on <code>creation</code> excludes a March-posted document created in February. Always record which date field defined the period, because you will not remember, and neither will your reviewer.</p>

<blockquote>IMPLEMENTATION TIP: Write the question at the top of the paper before extracting anything. It takes a minute, and it prevents the commonest failure in exploratory work — pulling data, noticing something interesting, and writing up a conclusion to a question you never actually asked.</blockquote>

<p><b>Retention, briefly, because it is usually decided by accident.</b> Working papers supporting a finding should survive at least as long as the finding's follow-up cycle, and in practice longer — a recurring issue is only demonstrable if the earlier files still exist. Decide the period deliberately, store extracts with their definitions rather than as loose spreadsheets, and keep them somewhere the audit function controls. A file held only on one auditor's laptop is not a record of the function's work.</p>"""
, [
 C("Your file contains the extract but not the filters used. The problem is:",
   ["It is untidy", "A spreadsheet of unknown provenance — the definition is what makes it meaningful",
    "It cannot be archived", "It breaches retention policy"], 1,
   "In a system environment the extract is your only fixed point, because the underlying data can change."),
 C("A 'March' population built on the `creation` date will:",
   ["Be correct", "Exclude a March-posted document that was created in February",
    "Include cancelled documents", "Double-count amendments"], 1,
   "Always record which date field defined the period; you will not remember, and neither will your reviewer."),
 C("A working paper recording only the exceptions you pursued:",
   ["Is appropriately concise", "Hides the judgement you exercised, which is the professional part",
    "Meets the standard", "Reduces review time usefully"], 1,
   "Hits examined and found innocent belong in the file precisely because somebody decided they were innocent.")]),

("Looking before you know what you are looking for", 12, """<p>Everything so far assumed you knew the test. Some of the best findings begin the other way round — with an auditor looking at a distribution and noticing that something is shaped oddly.</p>

<p><b>The four exploratory views worth building for any area.</b></p>

<p><b>By person.</b> Whatever the transaction is, group it by <code>owner</code> and count. Adjustments, credit notes, voids, price changes, manual journals. Nearly every concentration finding starts here, and it takes about a minute per doctype.</p>

<p><b>By branch, normalised.</b> The same grouped by location — but per transaction or per naira of revenue, never raw. Raw counts rank branches by size and tell you nothing you did not already know.</p>

<p><b>By time.</b> Volume by day of week and hour of day. Transactions clustering at shift end, at month end, or outside trading hours are worth a look precisely because the timing was chosen.</p>

<p><b>By value distribution.</b> How the amounts are spread. Clusters just below a threshold are the clearest signal in this entire chapter: purchase orders bunching under an approval limit, refunds bunching under a supervisor-override level, write-offs just under a review trigger. People optimise against limits, and the histogram shows it plainly.</p>

<p><b>What to do with an oddity.</b> Not raise a finding. Form a hypothesis, then design the test that would confirm or disprove it, then run that test properly with a defined population. Exploration finds candidates; only a designed test produces evidence. Skipping the second step is how an auditor ends up defending a pattern rather than a fact.</p>

<p><b>And the discipline that keeps this honest.</b> Write down what you expected to see before you look. If you did not have an expectation, you cannot be surprised — you can only find patterns, and patterns are available in any dataset if you look long enough. The expectation is what turns noticing into evidence.</p>

<p><b>Where this fits in the year.</b> Exploration deserves scheduled time rather than being what you do when a review finishes early. A day a quarter, on an area chosen deliberately, produces more new tests than any amount of repeating last year's programme — which by definition finds only what somebody already thought to look for.</p>

<blockquote>IMPLEMENTATION TIP: The value distribution is the single highest-yield exploratory view in a retail environment. Plot any approval-limited transaction against value and look immediately below each limit. If people are working around a control, that is where it shows.</blockquote>

<p><b>A caution about exploring in a live system.</b> Broad queries over long periods can be heavy, and running one at month-end while branches are trading is a way to become unpopular quickly and, occasionally, to be blamed for a slowdown you did not cause. Use prepared reports for anything wide, run heavy exploration outside peak hours, and tell whoever manages the system what you are doing before rather than after. Independence does not require being inconsiderate, and the goodwill matters the first time you need something urgently.</p>"""
, [
 C("Purchase order values cluster just below the approval limit. This is:",
   ["Normal purchasing behaviour", "A candidate finding — people optimise against limits and the histogram shows it",
    "A data quality issue", "Evidence of good budgeting"], 1,
   "Clusters just below a threshold are the clearest signal available in exploratory work."),
 C("You notice an odd pattern while exploring. The correct next step is:",
   ["Raise a finding", "Form a hypothesis and design a proper test with a defined population",
    "Interview the staff involved", "Widen the exploration"], 1,
   "Exploration finds candidates; only a designed test produces evidence."),
 C("Writing down what you expected before looking matters because:",
   ["It documents the plan", "Without an expectation you cannot be surprised — only find patterns, which any dataset offers",
    "It satisfies review standards", "It speeds up analysis"], 1,
   "The expectation is what turns noticing into evidence.")]),
]


QUESTIONS = [
 Q("An auditor who cannot extract their own data is:", ["More efficient", "Dependent on the people they examine", "Following segregation of duties", "Correctly using IT"], 1,
   "And the extract's producer usually reports to the director whose area is under review.", "Ch1 §1", "Why extraction matters"),
 Q("Population testing lets a clean result be expressed as:", ["A representative sample was clean", "No instance occurred in the period", "An estimated error rate", "A reasonable assurance opinion"], 1,
   "Sampling carries the risk that the fifty were clean while the population was not.", "Ch1 §5", "Why extraction matters"),
 Q("Under population testing, a single exception is:", ["Extrapolated to a rate", "One exception, with a document number", "Statistically insignificant", "Ignored below materiality"], 1,
   "The conversation moves from statistics to facts, which are harder to negotiate down.", "Ch1 §7", "Why extraction matters"),
 Q("The commonest reason a finding is dismissed is:", ["It was wrong", "The auditor could not state how the number was produced", "It was immaterial", "It was late"], 1,
   "Reproducibility is what makes a finding survive contact with the person it concerns.", "Ch1 §9", "Why extraction matters"),
 Q("Sales Invoice line items are stored in:", ["tabSales Invoice", "tabSales Invoice Item", "tabItem", "The General Ledger"], 1,
   "Child rows carry a parent field holding the invoice name.", "Ch2 §2", "Doctypes and tables"),
 Q("docstatus values are:", ["1 draft, 2 submitted, 3 cancelled", "0 draft, 1 submitted, 2 cancelled", "0 open, 1 closed", "0 active, 1 inactive"], 1,
   "Omitting it silently includes drafts and cancellations in every population.", "Ch2 §7", "Doctypes and tables"),
 Q("Which filter comparator finds documents where a field has any value at all?", ["like", "is set", "between", "in"], 1,
   "With `is not set` for absence — both are more useful in testing than they first appear.", "Ch2 §4", "Doctypes and tables"),
 Q("`modified_by` records:", ["The document owner", "Who last changed it", "The approver", "The assigned user"], 1,
   "With `owner` recording who created it. Together they answer many 'who did this' questions.", "Ch2 §6", "Doctypes and tables"),
 Q("Report view differs from list view mainly by offering:", ["Faster loading", "Chosen columns, totals and grouping", "Write access", "Scheduled delivery"], 1,
   "Grouping Stock Entries by owner with totals is an adjustment-concentration test, not a programming task.", "Ch2 §5", "Doctypes and tables"),
 Q("The four report types in ERPNext are Report Builder, Query Report, Script Report and:", ["Dashboard Report", "Custom Report", "Print Report", "Scheduled Report"], 1,
   "Custom Report is a saved variant of an existing report with different filters and columns.", "Ch3 §2", "Report Builder"),
 Q("Report Builder cannot:", ["Group and total", "Join two unrelated doctypes", "Filter by date range", "Select columns"], 1,
   "Nor aggregate across a relationship or compare one document to another.", "Ch3 §5", "Report Builder"),
 Q("A saved report named to its programme test code is valuable because:", ["It runs faster", "The library stays navigable a year later", "It restricts access", "It schedules automatically"], 1,
   "The same filters applied ad hoc are a personal habit that leaves when you do.", "Ch3 §6", "Report Builder"),
 Q("The `roles` table on a Report controls:", ["Which columns appear", "Who can run it", "The refresh frequency", "Export permissions"], 1,
   "Worth setting deliberately — visibility to the audited department changes behaviour.", "Ch3 §7", "Report Builder"),
 Q("Query Reports are needed mainly because real exceptions are usually about:", ["Large values", "A relationship between records rather than a property of one", "Recent transactions", "Specific branches"], 1,
   "Joins, aggregation and date arithmetic between events.", "Ch4 §2", "Query Report"),
 Q("A threshold hard-coded into a query rather than exposed as a parameter:", ["Runs faster", "Goes stale silently and leaves the run uninterpretable later", "Improves security", "Prevents misuse"], 1,
   "A parameter is recorded on the run, so a result stays interpretable after the limit changes.", "Ch4 §5", "Query Report"),
 Q("Every exception row should return:", ["A count and a percentage", "Identifiers somebody can open", "The branch only", "A severity grade"], 1,
   "An exception you cannot navigate to is an accusation without an address.", "Ch4 §6", "Query Report"),
 Q("Query Report creation requires elevated rights because:", ["Reports are expensive to run", "SQL bypasses the ordinary permission layer", "They are scheduled", "They export data"], 1,
   "Which is why your own ability to create them is something an external auditor should examine.", "Ch4 §7", "Query Report"),
 Q("A test spanning eighteen months across twenty branches should be:", ["Narrowed to avoid timeouts", "Marked as a prepared report and run in the background", "Split into monthly runs", "Run only at night"], 1,
   "It is the intended mechanism, and it stops people writing artificially narrow tests.", "Ch4 §8", "Query Report"),
 Q("An aggregate far larger than the expected population usually indicates:", ["A date error", "A join multiplying rows", "Missing docstatus", "Wrong branch scope"], 1,
   "One invoice matching three version records inflates every total plausibly.", "Ch4 §10", "Query Report"),
 Q("The version history records, for each tracked change:", ["That an edit occurred", "The field, its old value and its new value", "Only the new value", "A summary of the document"], 1,
   "Plus child rows added, removed and modified, with who and when.", "Ch5 §2", "Version history"),
 Q("A submitted document that needs correcting is:", ["Edited in place", "Cancelled and amended, with the amendment compared against the original", "Deleted and re-entered", "Locked permanently"], 1,
   "Which is why a void leaves a full trail rather than a hole.", "Ch5 §4", "Version history"),
 Q("If change tracking were disabled on a doctype, dependent tests would:", ["Raise an error", "Return nothing, cleanly and silently", "Return all records", "Be blocked by permissions"], 1,
   "Which is why confirming it is enabled belongs first in the programme.", "Ch5 §6", "Version history"),
 Q("Which field type is excluded from version diffing?", ["Currency", "Link", "Text Editor", "Date"], 2,
   "Along with Code and Markdown — narrative fields change without a recorded prior value.", "Ch5 §7", "Version history"),
 Q("Version records are:", ["Viewable only per document", "Queryable like any other doctype", "Purged quarterly", "Restricted to System Managers"], 1,
   "Which turns 'all supplier bank changes last quarter' from a manual trawl into a report.", "Ch5 §8", "Version history"),
 Q("Stock And Account Value Comparison tests:", ["Stock movement accuracy", "Whether the stock ledger agrees with the general ledger", "Valuation policy", "Count accuracy"], 1,
   "A difference means inventory and finance are telling different stories.", "Ch6 §5", "Self-integrity reports"),
 Q("Calculated Discount Mismatch finds:", ["Discounts above policy", "Lines where the recorded discount disagrees with the arithmetic of price and rate", "Unapproved discounts", "Discount concentration"], 1,
   "Directly useful in revenue testing.", "Ch6 §8", "Self-integrity reports"),
 Q("The integrity report set should return:", ["A normal distribution", "Nil", "A benchmark figure", "One hit per branch"], 1,
   "These are not analytical tests; a hit is a defect rather than an interesting number.", "Ch6 §10", "Self-integrity reports"),
 Q("The integrity set should be run:", ["After substantive testing", "Before it", "Only on suspicion", "At year end"], 1,
   "A finding raised from a ledger that does not reconcile will be dismissed, and rightly.", "Ch6 §12", "Self-integrity reports"),
 Q("A hit on the integrity reports usually calls for:", ["A fraud investigation", "A support conversation, urgently", "A branch visit", "A management letter"], 1,
   "The causes are typically technical — interrupted postings, backdated entries, migration artefacts.", "Ch6 §11", "Self-integrity reports"),
 Q("An Audit Test's false-positive note exists because:", ["Documentation is required", "A test whose hits are usually innocent trains everybody to ignore its output", "It sets the severity", "Auditors must disclose limitations"], 1,
   "An ignored test is worse than no test, because it produces false assurance.", "Ch7 §3", "Running audit tests"),
 Q("The run snapshot matters because:", ["Queries are slow", "Underlying documents may be amended before a finding is challenged", "It reduces storage", "It enables scheduling"], 1,
   "Re-running months later produces a different answer and cannot show what you saw.", "Ch7 §5", "Running audit tests"),
 Q("A nil-expected test differs from an analytical test in that:", ["It runs faster", "Any row is a finding, rather than the distribution being the question", "It needs no threshold", "It cannot be scheduled"], 1,
   "Treating an analytical test like a nil-expected one produces findings that are normal business.", "Ch7 §8", "Running audit tests"),
 Q("A suppression without an expiry date is:", ["Efficient", "A deleted test with extra steps", "Best practice", "Required for known issues"], 1,
   "The condition it covered will change without anybody revisiting the decision.", "Ch7 §9", "Running audit tests"),
 Q("The characteristic failure of an exception system is:", ["Queries becoming slow", "Hits accumulating until nobody reads the output", "Insufficient coverage", "Excessive permissions"], 1,
   "Fewer tests with lower false-positive rates beat a comprehensive library nobody trusts.", "Ch7 §10", "Running audit tests"),
 Q("A reproducible working paper must define the population by doctype, date range, branch scope and:", ["Materiality", "docstatus", "Severity", "The reviewer"], 1,
   "This is where most files fail — the extract is present and its definition is not.", "Ch8 §4", "Working papers"),
 Q("A population defined on `creation` rather than `posting_date` will:", ["Be equivalent", "Miss a March-posted document created in February", "Include cancellations", "Double-count amendments"], 1,
   "Record which date field defined the period; you will not remember.", "Ch8 §9", "Working papers"),
 Q("Hits examined and found innocent belong in the file because:", ["Retention policy requires it", "They record the judgement you exercised, which is the professional part", "They support the sample size", "Reviewers request them"], 1,
   "A file recording only pursued exceptions hides the reasoning.", "Ch8 §7", "Working papers"),
 Q("In a system environment the working paper's fixed point is:", ["The document itself", "The extract, defined by its filters", "The report name", "The conclusion"], 1,
   "Unlike paper files, the underlying data can change after you looked.", "Ch8 §8", "Working papers"),
 Q("Grouping any transaction by `owner` and counting is the fastest route to:", ["A valuation test", "A concentration finding", "A completeness test", "A cut-off test"], 1,
   "Adjustments, credit notes, voids, price changes — about a minute per doctype.", "Ch9 §3", "Exploratory extraction"),
 Q("Branch comparisons must be normalised because raw counts:", ["Are harder to compute", "Rank branches by size", "Exclude cancellations", "Ignore seasonality"], 1,
   "Per transaction, per naira of revenue, or per head — never raw.", "Ch9 §4", "Exploratory extraction"),
 Q("Values clustering just below an approval limit indicate:", ["Prudent purchasing", "People optimising against the control", "A data entry convention", "Budget discipline"], 1,
   "The clearest signal available in exploratory work.", "Ch9 §6", "Exploratory extraction"),
 Q("An oddity found while exploring should lead to:", ["A finding", "A hypothesis and a designed test with a defined population", "An interview", "An immediate escalation"], 1,
   "Exploration finds candidates; only a designed test produces evidence.", "Ch9 §7", "Exploratory extraction"),
 Q("Recording your expectation before looking matters because:", ["It documents the plan", "Without it you cannot be surprised, only find patterns", "It sets materiality", "It satisfies review"], 1,
   "Any dataset offers patterns if you look long enough.", "Ch9 §8", "Exploratory extraction"),
]


def rebalance(items, seed):
    """Spread correct answers evenly across A-D by rotating each option list."""
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
    rebalance(QUESTIONS, "control:getting_data:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:getting_data:checks")

    mod = {
        "title": "Getting the Data",
        "desc": ("The module everything else depends on. Doctypes as tables, the list view "
                 "as a query tool, Report Builder and Query Report, reading a version "
                 "history properly, the self-integrity reports nobody runs, running a test "
                 "in Audit & Exceptions, working papers that reproduce, and how to look "
                 "before you know what you are looking for."),
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
