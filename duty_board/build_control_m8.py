#!/usr/bin/env python3
"""Build 'Building the Tests' into academy_control_data.json.

Module 8 of System-Based Internal Control in a Retail Environment, and where
the price is justified: the domain modules gave the auditor tests to run, this
one gives them the ability to design their own.

Deliberately does not repeat the branch-distribution material from modules 5
and 6, which covered shrinkage and revenue respectively. Chapter 5 here is
composite scoring across domains — combining measures from different modules
into one ranking — which none of them covered.

Run from the app package directory:  python3 build_control_m8.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "test_design"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("From a question to a test", 12, """<p>Every module so far handed you tests. This one is about designing your own, because the library will never cover the thing you actually need to know next week.</p>

<p><b>The sequence, and skipping any step produces a test that runs and tells you nothing.</b></p>

<p><b>1. State the risk in a sentence.</b> Not "procurement risk" — "a buyer could order goods from a supplier they control, at a price nobody compared, and nobody would know." A risk you cannot state in a sentence is not yet understood well enough to test.</p>

<p><b>2. State the control that should prevent it.</b> Competitive quotes above a value, a declared-interests register, approval by somebody outside procurement. If you cannot name a control, you have found something before writing any query — the risk is unmitigated, and that is the finding.</p>

<p><b>3. State what would be observable if the control failed.</b> This is the step people skip and it is the one that determines whether a test is possible. Orders above the quote threshold with no quotation record. A supplier whose contact details match an employee's. A supplier reaching material volume within weeks of creation.</p>

<p><b>4. Only now, write the query.</b> Which doctype, which fields, which filters, which joins.</p>

<p><b>5. Decide what a hit means before you run it.</b> Including what an innocent hit looks like. If you cannot describe one, you do not understand the population well enough to interpret the output.</p>

<p><b>Why step three does most of the work.</b> Many real risks leave no trace in the system at all. A buyer accepting a personal payment to favour a supplier produces no anomalous record — the orders are ordinary, the prices may be defensible, the goods arrive. No query finds it, and pretending otherwise wastes a fortnight.</p>

<p>Recognising that early is a skill rather than a failure. It redirects you toward what <i>is</i> observable — concentration, price drift, supplier creation patterns — or toward recommending a control that would create evidence, such as a declared-interests process. <b>A risk with no observable signature needs a control that generates one</b>, and saying so is a better outcome than a test that finds nothing and is reported as assurance.</p>

<p><b>The trap of testing what is easy.</b> Some things are convenient to query and matter little. An audit programme accumulates these because they produce output and output feels like work. Judge every test by the risk it addresses, not by the rows it returns, and be willing to retire a productive test that addresses nothing.</p>

<blockquote>IMPLEMENTATION TIP: Write the five steps out for the next test you design, in that order, before opening a query editor. Most badly designed tests are ones where the query came first and the risk was reverse-engineered from what the data happened to contain.</blockquote>

<p><b>Where test ideas actually come from.</b> Not from a textbook list. From the last investigation you conducted, from something a branch manager mentioned in passing, from a loss the business absorbed and explained away, and from the exploratory views in module 2. Keep a running note of candidate tests as they occur to you — most will never be built, and the two or three that are will be far better targeted than anything designed in the abstract at the start of a planning cycle.</p>"""
, [
 C("You cannot name a control that should prevent the risk you have described. This means:",
   ["The test cannot be designed", "You have found something before writing any query — the risk is unmitigated",
    "The risk is immaterial", "You should test compensating controls"], 1,
   "That absence is the finding, and it outranks any pattern you would have found."),
 C("A buyer accepting a personal payment to favour a supplier leaves:",
   ["A price variance", "No anomalous record at all — orders are ordinary and goods arrive",
    "A concentration signature", "An approval gap"], 1,
   "Recognising a risk with no observable signature is a skill, and it redirects you toward controls that would create one."),
 C("A test that returns plenty of rows but addresses no material risk should be:",
   ["Kept, since it produces output", "Retired",
    "Run less often", "Reassigned to another owner"], 1,
   "Programmes accumulate easy tests because output feels like work.")]),

("Defining the population", 12, """<p>Most wrong answers in this work come not from a faulty query but from testing the wrong set of records. The population definition is where accuracy is won or lost, and it takes minutes to get right.</p>

<p><b>Five decisions, every time.</b></p>

<p><b>Which doctype, and parent or child?</b> Module 2 established this. Document-level questions come from the parent; line-level questions must come from the child, and asking a line question of a parent returns a confident and wrong answer.</p>

<p><b>Which docstatus?</b> Draft, submitted, cancelled. Almost always submitted only — but cancelled documents are the entire population for a void test, and drafts are transactions that never happened. State it explicitly rather than inheriting whatever the default filter gives you.</p>

<p><b>Which date field?</b> Posting date, transaction date, creation, modification, due date. These differ, sometimes by weeks. A period defined on the wrong one is wrong in a way that looks entirely reasonable, and you will not remember which you used.</p>

<p><b>Which scope?</b> Company, branch, warehouse, cost centre. A group operating several companies will double-count or under-count depending on how the filter is set.</p>

<p><b>What is deliberately excluded, and why?</b> Intercompany transactions, a branch that closed, a migration period where data is known to be unreliable. Exclusions are legitimate; undocumented exclusions are how a finding collapses when somebody asks what happened to the missing month.</p>

<p><b>The completeness check that costs thirty seconds.</b> Before analysing anything, count the population and compare it against something you already know — total sales for the period, the number of branches, the count of active suppliers. If your population is 40% of what you expected, a filter is doing something you did not intend, and finding that now is a great deal cheaper than finding it in a meeting.</p>

<p><b>Sampling, and when it is still right.</b> Population testing is preferred throughout this track, but sampling remains correct where the evidence is not in the system — where you must inspect a physical document, visit a location, or interview somebody. You cannot examine four hundred delivery notes physically. Sample there, deliberately and with a stated basis, and say so.</p>

<p><b>And a note on data outside the system.</b> Where a control depends on something not recorded — a verbal authorisation, an emailed quote, a signed delivery note in a folder — no query will test it. Say so plainly rather than testing the recorded part and implying the whole control was examined.</p>

<blockquote>WATCH-OUT: Count your population and reconcile it to something known before you analyse it. A test on 40% of the data returns clean results 40% of the time, and nothing about the output will tell you the population was wrong.</blockquote>

<p><b>Time periods deserve their own thought.</b> A test run over one month may miss a pattern that only shows across six; a test run over three years may be dominated by a business that no longer exists. Match the window to what you are looking for: point-in-time impossibilities need only the current period, behavioural patterns need enough periods for a trend, and anything spanning a system change should stop at that boundary and say why.</p>"""
, [
 C("Your population comes back at roughly 40% of expected. You should:",
   ["Proceed — the sample is adequate", "Stop: a filter is doing something unintended, and clean results would be meaningless",
    "Widen the date range", "Add the missing branches"], 1,
   "Nothing in the output will tell you the population was wrong."),
 C("Sampling rather than population testing remains correct when:",
   ["The population is large", "The evidence is not in the system — physical documents, visits, interviews",
    "Time is short", "The risk is low"], 1,
   "You cannot examine four hundred delivery notes physically; sample deliberately and say so."),
 C("A control depending on an emailed quote held outside the system should be:",
   ["Tested on the recorded portion", "Stated plainly as not testable by query",
    "Assumed to operate", "Excluded from the programme"], 1,
   "Testing the recorded part and implying the whole control was examined is worse than not testing it.")]),

("Nil-expected and analytical tests", 12, """<p>Two kinds of test, and they behave so differently that treating one like the other is the most common design error in an exception programme.</p>

<p><b>A nil-expected test</b> looks for something that should never occur. Refunds against no original. Payments with no invoice. Negative stock. Enabled accounts for people who left. In a healthy month it returns nothing, and <b>any row is a finding</b>.</p>

<p>These are the strongest tests you can build. The threshold question does not arise, interpretation is straightforward, and a nil result is genuine assurance rather than an absence of evidence. Build as many as the risks allow.</p>

<p><b>An analytical test</b> examines a distribution. Void rate by cashier. Adjustment frequency by storekeeper. Price variance by supplier. It always returns rows, and the question is the shape rather than the existence of output.</p>

<p>These are weaker individually and necessary, because most real risks do not produce impossible records — they produce ordinary records in unusual quantities.</p>

<p><b>What goes wrong when the two are confused.</b> Treat an analytical test as nil-expected and every month produces a report full of findings that are simply normal business, which exhausts whoever must investigate and discredits the programme. Treat a nil-expected test as analytical and you will rank the impossible records and investigate only the worst, which means accepting some genuinely impossible ones because they were not the largest.</p>

<p><b>How to tell which you have built.</b> Ask what the test returns in a perfectly controlled month. If the answer is nothing, it is nil-expected. If the answer is a distribution, it is analytical. The question takes a second and it determines how the output must be read, reported and resourced.</p>

<p><b>Converting analytical to nil-expected where you can.</b> This is worth effort. "High void rate" is analytical and arguable. "Voided with no amendment" is nil-expected and specific. Often a sharper definition of the underlying risk turns a distribution into an impossibility — and the nil-expected version will be acted on where the analytical one is debated.</p>

<p><b>The reporting difference.</b> A nil-expected test with no hits is reportable as assurance: no instance occurred in the period. An analytical test with nothing unusual is reportable only as an absence of outliers, which is a weaker statement and should be presented as one rather than dressed up.</p>

<blockquote>IMPLEMENTATION TIP: Every time you design an analytical test, spend five minutes asking whether a sharper definition would make it nil-expected. The conversion is not always possible and when it is, the test becomes several times more useful.</blockquote>

<p><b>A third category worth naming: the reconciliation test.</b> Neither impossible nor distributional, it asks whether two records that must agree do agree — stock ledger against general ledger, despatched against received, till reading against banked. These behave like nil-expected tests in that any difference is a finding, and like analytical ones in that small differences may be tolerable. Treat them as nil-expected with a stated tolerance, and be explicit about what that tolerance accepts.</p>"""
, [
 C("How do you tell which kind of test you have built?",
   ["By the number of rows", "By asking what it returns in a perfectly controlled month",
    "By the doctype", "By the threshold required"], 1,
   "Nothing means nil-expected; a distribution means analytical."),
 C("Treating an analytical test as nil-expected produces:",
   ["Better coverage", "A monthly report full of findings that are normal business",
    "Fewer false positives", "Stronger assurance"], 1,
   "It exhausts whoever must investigate and discredits the programme."),
 C("'High void rate' can often be sharpened into a nil-expected test by redefining it as:",
   ["Voids above the branch mean", "Voided with no amendment following",
    "Voids in the final hour", "Voids above a value"], 1,
   "The nil-expected version gets acted on where the analytical one gets debated.")]),

("The false positive problem", 12, """<p>Every exception programme dies the same way. Tests are added, hits accumulate, nobody investigates them, and the whole apparatus becomes a report that is produced and not read. The mechanism is always false positives.</p>

<p><b>Why it is fatal rather than merely annoying.</b> Investigation capacity is small and fixed — one person, part-time, with other duties. A test producing forty hits a month does not produce forty investigations; it produces none, because forty is beyond what anybody will start. And once a report has been ignored for two months, it is ignored permanently, including the month it contained something real.</p>

<p><b>The number to design toward.</b> Ask how many exceptions the business will genuinely investigate in a month. In most retailers the honest answer is between five and fifteen across the whole programme. That is your budget, and every test must be tuned to fit within it collectively.</p>

<p>This is a harder discipline than it sounds, because each individual test seems worth having.</p>

<p><b>Four ways to reduce false positives without losing sensitivity.</b></p>

<p><b>Sharpen the definition.</b> The previous chapter's conversion — from a distribution to an impossibility — is the most powerful and the least used.</p>

<p><b>Require corroboration.</b> Two conditions rather than one. Not high voids, but high voids <i>and</i> shrinkage in the same category at the same branch. Each alone produces many hits; together they produce few, and the few are worth looking at.</p>

<p><b>Suppress known-innocent cases, with expiry.</b> A documented exception note removes a recurring hit somebody has already explained. Without expiry it becomes a permanently deleted test.</p>

<p><b>Raise the threshold deliberately, and say what you have accepted.</b> Moving a threshold to reduce noise means accepting that smaller instances go unexamined. That is a legitimate decision and it should be recorded as one rather than made quietly by whoever tuned the query.</p>

<p><b>Run new tests in silence first.</b> A month, results to you alone. You will find out what the test actually returns under normal conditions, which is almost always more than you expected. Tune, write the innocent explanation from what you observed rather than what you imagined, then release. A test released untuned generates a wave, exhausts goodwill, and quietly kills the credibility of every test that follows it.</p>

<blockquote>WATCH-OUT: The temptation when building a programme is comprehensiveness. Comprehensiveness is precisely what causes the output to be ignored. Six well-tuned tests that are genuinely investigated beat thirty that are not, and the difference is not effort but restraint.</blockquote>

<p><b>The other direction, which is rarer and worth watching for.</b> A test tuned so tightly that it never fires is providing no assurance while appearing on the control list. If a test has never produced a hit and you have never verified it against a known case, you cannot distinguish a well-controlled process from a threshold set beyond anything that will ever occur. Both look identical in the report, and only one is good news.</p>"""
, [
 C("How many exceptions should a programme be designed to produce monthly?",
   ["As many as the tests find", "The number the business will genuinely investigate, usually five to fifteen",
    "One per test", "One per branch"], 1,
   "That is your budget, and every test must fit within it collectively."),
 C("A report ignored for two months is:",
   ["Recoverable with better formatting", "Ignored permanently, including the month it contains something real",
    "Due for review", "Evidence of low risk"], 1,
   "Which is why forty hits produce no investigations rather than forty."),
 C("Requiring two conditions rather than one reduces false positives because:",
   ["The query is stricter", "Each alone produces many hits; together they produce few, and the few are worth looking at",
    "It halves the population", "It excludes analytical tests"], 1,
   "High voids and shrinkage in the same category at the same branch, rather than either alone.")]),

("Composite scoring across domains", 12, """<p>Modules 5 and 6 each ranked branches on their own measures. This chapter combines them, and the combination answers a question no single domain can: <b>where should fieldwork go?</b></p>

<p><b>Why the combination is stronger than any component.</b> Each individual measure has innocent explanations. A branch may have high shrinkage because of its category mix, high voids because of a faulty scanner, slow banking because of its location. Each is explicable alone. A branch that is an outlier on all three has a much shorter list of innocent explanations, and the probability that three independent innocent causes coincide at one location is low.</p>

<p><b>Building it, and the method is simple enough to do in a spreadsheet.</b></p>

<p>Choose your measures across domains — shrinkage rate, void rate, adjustment frequency, count-to-adjustment interval, days to bank, transfer anomalies, segregation conflicts held by branch staff. Normalise each, since raw counts rank by branch size. Rank branches on each measure. Then count how many measures place each branch in the worst quartile.</p>

<p>Branches appearing in the worst quartile on three or more are your list. It is one query per measure and a sort, and it is the most useful single page an internal audit function can produce.</p>

<p><b>Weighting, and why to resist it initially.</b> The temptation is to weight measures by importance. Resist it for the first year: weights are guesses, they invite argument about the weighting rather than the finding, and the simple count of quartile appearances is robust and explicable. Add weighting only when you have enough history to justify a particular weight, and be able to say why.</p>

<p><b>What the composite is and is not.</b> It is a fieldwork priority list. It is not a ranking of dishonesty, it does not accuse anybody, and it must not be presented as identifying problem branches — because branches that appear may be doing something legitimate that your measures penalise, and a manager told their branch is "top of the risk list" will hear an accusation whatever words you use.</p>

<p><b>Trend over level, again.</b> A branch entering the worst quartile on a measure it was previously average on has changed, and change is what you are looking for. A branch that has always been there is probably characteristic — a format, a location, a category mix — and has likely been discussed before without resolution.</p>

<p><b>The most valuable output is the recurrence.</b> Run the composite monthly and keep it. Three or four branches will appear repeatedly across quarters, and that persistent list, not the rota, should determine where you spend your time. Most audit functions visit branches in an order decided before any of this was known.</p>

<p><b>One caution about small estates.</b> With five or six branches, quartiles are meaningless and a distribution is barely a distribution. The method still works but the arithmetic should be simpler: rank, look at the top one or two, and rely more on trend than on position. Applying standard-deviation language to six data points produces false precision and invites an argument about statistics that you will lose and should not have started.</p>

<blockquote>IMPLEMENTATION TIP: Build the composite from measures you already produce. It requires no new tests — only that the outputs of modules 4 to 7 are retained and comparable, which is the argument for keeping monthly results rather than discussing and discarding them.</blockquote>"""
, [
 C("A branch is an outlier on shrinkage, voids and days-to-bank. This matters because:",
   ["Three findings are better than one", "Three independent innocent causes rarely coincide at one location",
    "The measures are correlated", "It confirms the shrinkage figure"], 1,
   "Each measure alone has an innocent explanation; all three together have a much shorter list."),
 C("Weighting the measures in a composite score should be:",
   ["Done from the outset for accuracy", "Resisted initially — weights are guesses and invite argument about the weighting rather than the finding",
    "Set by management", "Based on financial value only"], 1,
   "The simple count of quartile appearances is robust and explicable."),
 C("The composite ranking should be presented as:",
   ["A list of problem branches", "A fieldwork priority list",
    "A performance measure", "A risk score per manager"], 1,
   "A manager told their branch tops the risk list hears an accusation whatever words you use.")]),

("Building a test in the app", 12, """<p>A test in your head is worth little. A test stored, parameterised, scheduled and versioned is an asset of the function, and that is what the Audit & Exceptions app exists to hold.</p>

<p><b>What you record when creating a test.</b> A code, stable across renames, so findings can reference it years later. The risk in a sentence. The control it evidences. The query or filter. The threshold, exposed as a parameter rather than buried. A severity. A frequency. And the note describing what an innocent hit looks like.</p>

<p><b>Why the threshold must be a parameter.</b> A limit written into the query goes stale the moment the business changes it, silently, and nobody notices because the test still runs and still returns rows. As a parameter it is visible, adjustable, and recorded on each run — so a result from March remains interpretable in September even though the threshold has since moved.</p>

<p><b>Why the run snapshot matters.</b> A run stores what the test returned at the time. Findings raised months earlier rest on data that may since have been amended, corrected or cancelled; re-running the query then produces a different answer. Without the snapshot you cannot show what you saw, and a finding you cannot evidence is a finding you will lose.</p>

<p><b>Ownership.</b> Each test names who investigates a hit. Without it, exceptions arrive in a report belonging to nobody, and the default owner — the audit function — becomes a queue of work it was never resourced for. Where a hit genuinely belongs to operations to explain, say so in the test itself.</p>

<p><b>Severity, set at design time rather than argued at reporting time.</b> A test's default grade should reflect the risk it addresses, so a hit arrives pre-graded and the conversation is about the instance rather than about how seriously to take the category.</p>

<p><b>Versioning your own tests.</b> When you change a threshold or a query, that change is itself worth recording. A result that shifted because the business changed and one that shifted because you changed the test are different facts, and six months later nobody remembers which happened.</p>

<p><b>And the same standard you apply to everyone else.</b> The app's own doctypes track changes, and your suppressions are as visible as anybody else's actions. That is correct: an audit tool without an audit trail is a poor advertisement for the discipline, and your own use of it should withstand the scrutiny you apply elsewhere.</p>

<blockquote>IMPLEMENTATION TIP: Write the innocent-hit note before the query rather than after. If you cannot describe what a legitimate hit looks like, you do not yet understand the population well enough to interpret an illegitimate one — and the note written afterwards is usually a rationalisation of the first argument you lost.</blockquote>

<p><b>Naming conventions, which matter more than they sound.</b> A test code that encodes domain and sequence — P2P-004, INV-002, REV-007 — lets a finding reference a test permanently, lets a programme be assembled by prefix, and survives the test being renamed as your understanding improves. Findings raised two years ago against a code still resolve; findings raised against 'the supplier bank test' resolve to whatever somebody now assumes that meant.</p>"""
, [
 C("A result from March is reviewed in September; the threshold has since changed. It remains interpretable because:",
   ["The query is versioned", "The parameters as they stood were recorded on the run",
    "Severity was fixed", "The finding was graded"], 1,
   "A threshold buried in the query would leave the old result meaningless."),
 C("Your monthly pack contains eleven exceptions and no name against any of them. What happens is:",
   ["Faster escalation", "Exceptions belonging to nobody, defaulting to a queue the audit function was never resourced for",
    "Shared responsibility", "Management ownership"], 1,
   "Where a hit belongs to operations to explain, the test should say so."),
 C("The innocent-hit note should be written:",
   ["After the first month's results", "Before the query",
    "When the first dispute arises", "By the audited department"], 1,
   "Written afterwards it is usually a rationalisation of the first argument you lost.")]),

("Scheduling and continuous monitoring", 12, """<p>An annual audit examines a year after it has finished. Continuous monitoring examines the month while there is still something to do about it, and the difference is mostly a matter of scheduling.</p>

<p><b>Frequency follows consequence, not convenience.</b> The question for each test is how much damage accrues between occurrence and detection.</p>

<p><b>Weekly</b> for anything where the interval determines recoverability. The bank-change-then-payment test is the clearest case: a week may be the difference between stopping a payment and writing off a loss.</p>

<p><b>Monthly</b> for behavioural analytics — voids, adjustments, discounts, price changes. These are patterns rather than events, and a month is the shortest period over which a pattern is meaningful.</p>

<p><b>Quarterly</b> for structural work — access reviews, configuration baselines, integrity reports, dormant records. These move slowly and running them monthly adds noise rather than assurance.</p>

<p><b>What continuous monitoring actually changes.</b> Not the tests, which are the same. It changes what the annual plan is for. Instead of visiting branches on a rota and testing whatever is there, the standing programme runs continuously and the plan directs fieldwork at what the programme surfaced. <b>The rota becomes a fallback rather than the method.</b></p>

<p>It also changes the conversation with management, from an annual report on a year that has ended to a monthly one about the current position, which is a different kind of usefulness and is received differently.</p>

<p><b>The resourcing point, stated honestly.</b> Continuous monitoring is cheaper to run than an annual cycle once the tests exist, and considerably more expensive to establish. The first quarter is mostly building. If the function cannot protect that time, the realistic path is to build three tests properly rather than twenty badly, and add as capacity allows.</p>

<p><b>What to do with a clean run.</b> Record it. A nil-expected test returning nothing for six consecutive months is assurance, and it belongs in the report as such. Functions that report only exceptions give the impression that they find nothing when things are working, which undersells the work and makes the exception months look worse than they are.</p>

<p><b>And the failure mode to watch.</b> Scheduled tests that run and are never opened. A test producing output nobody reads is worse than no test, because it appears on a list of controls and provides none. Review the review: which tests were actually looked at last quarter, and by whom.</p>

<blockquote>IMPLEMENTATION TIP: Put a calendar entry against each frequency band rather than each test. Twenty minutes weekly, an hour monthly, half a day quarterly. Scheduling the review rather than the test is what makes the output get read, and unread output is the only real failure mode here.</blockquote>

<p><b>What to do when you fall behind.</b> You will. A busy quarter, a large investigation, leave. The failure is not missing a month; it is quietly abandoning the schedule and pretending otherwise. Run the tests late, note that they were late, and look hardest at the weekly ones — those are the tests whose value depends on timeliness, and a month-late run of a payment watch is a review rather than a control.</p>"""
, [
 C("Which test's frequency is determined by recoverability rather than pattern length?",
   ["Void rate by cashier", "Bank account changed then paid",
    "Access review", "Adjustment frequency"], 1,
   "A week may be the difference between stopping a payment and writing off a loss."),
 C("Under continuous monitoring, the branch visit rota becomes:",
   ["The primary method", "A fallback, with fieldwork directed by what the programme surfaced",
    "Quarterly rather than annual", "Unnecessary"], 1,
   "Instead of testing whatever is at the branch you happen to be visiting."),
 C("A nil-expected test returning nothing for six months should be:",
   ["Retired as unproductive", "Recorded and reported as assurance",
    "Run less often", "Widened"], 1,
   "Functions reporting only exceptions appear to find nothing when things are working.")]),

("Designing the programme", 12, """<p>Individual tests are craft. A programme is design, and it answers a different question: does the set of tests, taken together, address the risks that matter?</p>

<p><b>Start from a risk map rather than from the tests you can build.</b> List the significant risks by process — procurement, inventory, revenue, cash, master data, access. For each, note the control that should address it and whether a test evidences that control. The gaps are what the programme is missing, and they are invisible if you build upward from queries.</p>

<p><b>Expect the gaps to cluster where testing is hard.</b> Every programme is strongest where data is convenient and weakest where the risk leaves no trace. That is not a criticism, it is a fact to state — and stating it prevents a programme being read as coverage when it is coverage of the observable.</p>

<p><b>Balance, which is worth checking deliberately.</b> Count your tests by domain. Most self-assembled programmes are heavily weighted toward revenue and inventory, because those are where the data is richest and the findings most frequent. If procurement has two tests and revenue has twelve, that is a statement about convenience rather than about where the money is — and module 4 argued that procurement losses are larger and rarer.</p>

<p><b>Size, and the honest number.</b> Twenty to thirty tests is a mature programme for a mid-sized retailer. Fewer than ten is thin. More than forty, for a function of one or two people, is a library that cannot be maintained or investigated, and it will decay into a set of scheduled jobs nobody opens.</p>

<p><b>Group into programmes with a cadence.</b> A monthly branch programme, a quarterly master data and access review, a weekly payment watch. Grouping makes the work schedulable and gives each block an owner and a slot, which is what turns intent into routine.</p>

<p><b>Who investigates.</b> Not everything belongs to audit. A price variance belongs to procurement to explain; an access conflict belongs to the department head to confirm. Design the routing at programme level, so exceptions arrive with the person who can resolve them rather than with the person who found them — and audit's role becomes reviewing whether the explanation is adequate, which is a far better use of a small function.</p>

<p><b>Review the programme annually.</b> Which tests found something, which never do, which risks emerged that nothing covers. A programme that has not changed in three years is describing a business that has.</p>

<blockquote>WATCH-OUT: Judge a programme by risk coverage rather than by activity. Thirty tests producing five hundred hits a year can be worse coverage than twelve producing sixty, if the thirty cluster in one domain and the twelve span all of them.</blockquote>

<p><b>Show the map, not just the tests.</b> When presenting a programme to an audit committee, present the risk map with the tests against it — including the risks with no test and the reason. That document does two things a test list cannot: it shows that coverage was designed rather than assembled, and it puts the untested risks in front of the people who can decide whether to accept them. Those gaps are then a business decision rather than an audit omission.</p>"""
, [
 C("Your programme has twelve revenue tests and two procurement tests. This most likely reflects:",
   ["Where the risk is", "Where the data is convenient",
    "Management priorities", "Regulatory focus"], 1,
   "Procurement losses are larger and rarer, which is precisely why they are harder to test."),
 C("Building a programme upward from the queries you can write means:",
   ["Efficient use of data", "Gaps are invisible, because you never listed the risks nothing covers",
    "Better coverage", "Faster deployment"], 1,
   "Start from a risk map and note where no test evidences the control."),
 C("A price variance surfaces. The person best placed to explain it is:",
   ["The audit function, which found it", "Procurement, with audit reviewing whether the explanation holds",
    "The branch manager", "Finance"], 1,
   "Routing exceptions to whoever can resolve them is a far better use of a small function than investigating everything itself.")]),

("Maintaining the library", 12, """<p>A test written once and never revisited decays. The business changes, thresholds go stale, false positives creep up, and a test that was sharp in January is noise by December. Maintenance is unglamorous and it is what distinguishes a programme from a folder of queries.</p>

<p><b>What decays, and how you notice.</b></p>

<p><b>Thresholds</b> lose meaning as values change. A ₦500,000 threshold set three years ago is a materially different control today, and inflation alone will have widened or narrowed the population without anybody deciding.</p>

<p><b>Configuration</b> moves beneath the test. A workflow is added, a field is renamed, a doctype is customised, an upgrade changes a default. A test can silently return nothing because the field it filters on no longer holds what it did.</p>

<p><b>The population shifts.</b> New branches, new categories, a change in how something is recorded. A test built when transfers were instantaneous behaves differently once in-transit warehousing is enabled.</p>

<p><b>The most dangerous failure: the test that returns nothing because it is broken.</b> A nil result reads as assurance. If the query silently matches nothing — a renamed field, a changed value, a filter that no longer applies — you will report assurance you do not have, and nothing will tell you.</p>

<p><b>The defence is a canary.</b> Periodically, verify each nil-expected test against a case you know should trigger it. Construct one in a test environment, or find a historical record that ought to match, and confirm the test finds it. A scanner whose silence has never been tested is not evidence of anything — the same principle that governs any control, applied to your own tools.</p>

<p><b>When to retire a test.</b> When the risk no longer exists, when the control has been replaced by a preventive one that makes detection redundant, or when it has produced nothing but false positives for a year and cannot be sharpened. Retire deliberately, record why, and keep the definition — a retired test with its reasoning is useful history, while a deleted one leaves a gap nobody can explain.</p>

<p><b>Reviewing the library annually.</b> For each test: has it ever found anything, what proportion of hits were genuine, is the threshold still right, does the risk still exist, and is the innocent-hit note still accurate. An hour per ten tests, once a year, and it is the difference between a programme that improves and one that ossifies.</p>

<p><b>The measure worth tracking about your own work.</b> Not the number of exceptions raised, which rewards noisy tests. The proportion of hits that turned out to be genuine, and the proportion of findings that were implemented. Those two say whether the programme is precise and whether it changes anything, which is the whole question.</p>

<blockquote>WATCH-OUT: A test that has returned nothing for a year is either excellent assurance or quietly broken, and the output looks identical either way. Verify it against a known case before reporting another clean year.</blockquote>

<p><b>And the handover point, which is where libraries usually die.</b> A programme held in one person's head does not survive their departure, however well the tests are stored. Each test needs its risk, its reasoning and its innocent-hit note written down well enough that a successor can decide whether to keep it. Write for the person who arrives after you and knows none of the history — which is the same standard module 2 set for working papers, applied to the programme itself.</p>"""
, [
 C("A nil-expected test has returned nothing for a year. This is:",
   ["Assurance", "Either assurance or a broken query, and the output looks identical",
    "Grounds for retirement", "Evidence the control works"], 1,
   "Verify against a known case before reporting another clean year."),
 C("A test should be retired when:",
   ["It produces few hits", "The risk no longer exists, a preventive control replaced it, or it cannot be sharpened after a year of false positives",
    "The threshold changes", "Staff change"], 1,
   "Retire deliberately and keep the definition — a deleted test leaves a gap nobody can explain."),
 C("Which measure of your own programme is most worth tracking?",
   ["Number of exceptions raised", "Proportion of hits that were genuine, and of findings implemented",
    "Number of tests", "Coverage by domain"], 1,
   "Counting exceptions rewards noisy tests.")]),
]


QUESTIONS = [
 Q("The first step in designing a test is to:", ["Choose the doctype", "State the risk in a sentence", "Set a threshold", "Identify the data"], 1,
   "A risk you cannot state in a sentence is not understood well enough to test.", "Ch1 §2", "From question to test"),
 Q("If you cannot name a control that should prevent the risk:", ["The test is impossible", "You have found something before writing any query", "Use a proxy control", "Escalate to management"], 1,
   "The risk is unmitigated, and that is the finding.", "Ch1 §3", "From question to test"),
 Q("Which step determines whether a test is possible at all?", ["Writing the query", "Stating what would be observable if the control failed", "Setting the threshold", "Choosing the frequency"], 1,
   "Many real risks leave no trace in the system.", "Ch1 §4", "From question to test"),
 Q("A risk with no observable signature calls for:", ["A broader query", "A control that would generate one", "Sampling", "Interviews only"], 1,
   "Better than a test that finds nothing and is reported as assurance.", "Ch1 §8", "From question to test"),
 Q("Programmes accumulate easy tests because:", ["They are cheap", "Output feels like work", "They are requested", "Data is available"], 1,
   "Judge a test by the risk it addresses, not the rows it returns.", "Ch1 §9", "From question to test"),
 Q("Line-level questions must be answered from:", ["The parent doctype", "The child table", "The ledger", "The report view"], 1,
   "Asking a line question of a parent returns a confident wrong answer.", "Ch2 §3", "Defining the population"),
 Q("Which docstatus is the entire population for a void test?", ["0 draft", "1 submitted", "2 cancelled", "All three"], 2,
   "Almost every other test wants submitted only.", "Ch2 §4", "Defining the population"),
 Q("Before analysing, you should reconcile the population count against:", ["The prior period", "Something you already know, such as total sales or branch count", "The budget", "The report total"], 1,
   "A test on 40% of the data returns clean results 40% of the time.", "Ch2 §8", "Defining the population"),
 Q("Sampling remains correct when:", ["The population is large", "The evidence is not in the system", "Time is short", "Risk is low"], 1,
   "Physical documents, visits and interviews cannot be population-tested.", "Ch2 §9", "Defining the population"),
 Q("Undocumented exclusions from a population are dangerous because:", ["They bias the result", "A finding collapses when somebody asks what happened to the missing month", "They break the query", "They affect materiality"], 1,
   "Exclusions are legitimate; undocumented ones are not.", "Ch2 §7", "Defining the population"),
 Q("A nil-expected test returns what in a healthy month?", ["A small distribution", "Nothing", "One row per branch", "A ranked list"], 1,
   "Any row is a finding rather than a data point.", "Ch3 §2", "Test types"),
 Q("Analytical tests are necessary because most real risks produce:", ["Impossible records", "Ordinary records in unusual quantities", "No records", "Configuration changes"], 1,
   "Weaker individually, and unavoidable.", "Ch3 §4", "Test types"),
 Q("Treating a nil-expected test as analytical means:", ["Fewer false positives", "Ranking the impossible and investigating only the worst", "Better coverage", "Stronger assurance"], 1,
   "You accept some genuinely impossible records because they were not the largest.", "Ch3 §6", "Test types"),
 Q("A nil-expected test with no hits is reportable as:", ["An absence of outliers", "Assurance that no instance occurred", "Inconclusive", "A control gap"], 1,
   "An analytical test with nothing unusual is a weaker statement.", "Ch3 §9", "Test types"),
 Q("Converting an analytical test to nil-expected usually requires:", ["A higher threshold", "A sharper definition of the underlying risk", "More data", "Corroboration"], 1,
   "'High void rate' becomes 'voided with no amendment'.", "Ch3 §8", "Test types"),
 Q("A programme should be tuned to produce monthly:", ["One hit per test", "The number the business will genuinely investigate", "As many as possible", "Ten per branch"], 1,
   "Usually between five and fifteen across the whole programme.", "Ch4 §4", "False positives"),
 Q("Forty hits a month produce:", ["Forty investigations", "None", "A useful trend", "Better tuning data"], 1,
   "Forty is beyond what anybody will start.", "Ch4 §3", "False positives"),
 Q("The most powerful and least used way to cut false positives is:", ["Raising the threshold", "Sharpening the definition", "Suppression", "Corroboration"], 1,
   "Converting a distribution into an impossibility.", "Ch4 §6", "False positives"),
 Q("Raising a threshold to reduce noise should be:", ["Done quietly by whoever tunes it", "Recorded as a decision about what is now unexamined", "Avoided entirely", "Set by management"], 1,
   "It is legitimate, and it accepts that smaller instances go unexamined.", "Ch4 §9", "False positives"),
 Q("A new test should first be run:", ["Across all branches", "In silence for a month, results to you alone", "On historical data only", "At one branch"], 1,
   "You will find out what it returns under normal conditions, which is more than expected.", "Ch4 §10", "False positives"),
 Q("A composite score is stronger than its components because:", ["It uses more data", "Three independent innocent causes rarely coincide at one location", "It is normalised", "It is ranked"], 1,
   "Each measure alone has an innocent explanation.", "Ch5 §2", "Composite scoring"),
 Q("Weighting composite measures should initially be:", ["Set by value", "Resisted", "Agreed with management", "Based on history"], 1,
   "Weights are guesses and invite argument about the weighting rather than the finding.", "Ch5 §5", "Composite scoring"),
 Q("The composite ranking is:", ["A list of problem branches", "A fieldwork priority list", "A performance measure", "A risk score per manager"], 1,
   "A manager told their branch tops the risk list hears an accusation.", "Ch5 §6", "Composite scoring"),
 Q("The most valuable composite output is:", ["The current month's ranking", "The branches that recur across quarters", "The worst single measure", "The estate average"], 1,
   "That persistent list, not the rota, should determine where time goes.", "Ch5 §8", "Composite scoring"),
 Q("Building a composite requires:", ["New tests", "Only that existing monthly outputs are retained and comparable", "A statistical package", "Management weighting"], 1,
   "Which is the argument for keeping monthly results rather than discarding them.", "Ch5 §9", "Composite scoring"),
 Q("A threshold should be stored as:", ["A constant in the query", "An exposed parameter recorded on each run", "A note in the description", "A programme setting"], 1,
   "So a March result stays interpretable in September.", "Ch6 §3", "Building a test"),
 Q("The run snapshot exists because:", ["Queries are slow", "Underlying documents may be amended before a finding is challenged", "Storage is cheap", "Scheduling requires it"], 1,
   "A finding you cannot evidence is a finding you will lose.", "Ch6 §4", "Building a test"),
 Q("A test with no named investigator results in:", ["Shared ownership", "A queue the audit function was never resourced for", "Faster escalation", "Management review"], 1,
   "Say in the test itself where a hit belongs to operations.", "Ch6 §5", "Building a test"),
 Q("Severity should be set:", ["When a hit is reported", "At design time", "By the investigator", "By value"], 1,
   "So the conversation is about the instance rather than the category.", "Ch6 §6", "Building a test"),
 Q("Changes to your own test definitions should be:", ["Undocumented", "Recorded, so a shifted result can be attributed to the business or the test", "Approved by management", "Avoided"], 1,
   "Six months later nobody remembers which changed.", "Ch6 §7", "Building a test"),
 Q("Weekly frequency is justified where:", ["Volumes are high", "The interval between occurrence and detection determines recoverability", "The test is quick", "Management asks"], 1,
   "The bank-change-then-payment test is the clearest case.", "Ch7 §3", "Scheduling"),
 Q("Structural tests such as access reviews belong at:", ["Weekly", "Monthly", "Quarterly", "Annual"], 2,
   "Running them monthly adds noise rather than assurance.", "Ch7 §5", "Scheduling"),
 Q("Continuous monitoring changes the annual plan by making the visit rota:", ["More frequent", "A fallback rather than the method", "Unnecessary", "Risk-weighted"], 1,
   "Fieldwork is directed at what the programme surfaced.", "Ch7 §6", "Scheduling"),
 Q("Establishing continuous monitoring is:", ["Cheaper than an annual cycle from the start", "Expensive to establish and cheaper to run", "Equivalent in cost", "Only viable for large functions"], 1,
   "If the build time cannot be protected, build three tests properly rather than twenty badly.", "Ch7 §8", "Scheduling"),
 Q("Scheduled tests that run and are never opened are:", ["Harmless", "Worse than no test — they appear on a list of controls and provide none", "Useful history", "Adequate coverage"], 1,
   "Review which tests were actually looked at last quarter, and by whom.", "Ch7 §10", "Scheduling"),
 Q("A programme should be built starting from:", ["The queries you can write", "A risk map by process", "Available reports", "Last year's findings"], 1,
   "Gaps are invisible if you build upward from queries.", "Ch8 §2", "Programme design"),
 Q("Twelve revenue tests and two procurement tests reflects:", ["Where the risk is", "Where the data is convenient", "Management priority", "Regulatory focus"], 1,
   "Procurement losses are larger and rarer, which is why they are harder to test.", "Ch8 §5", "Programme design"),
 Q("A mature programme for a mid-sized retailer is about:", ["Five tests", "Twenty to thirty", "Fifty", "One hundred"], 1,
   "More than forty for a function of one or two people cannot be maintained.", "Ch8 §6", "Programme design"),
 Q("Exceptions should be routed to:", ["Audit in every case", "The person who can resolve them, with audit reviewing adequacy", "The branch manager", "The data owner"], 1,
   "A better use of a small function than investigating everything itself.", "Ch8 §8", "Programme design"),
 Q("A programme unchanged in three years is:", ["Stable and mature", "Describing a business that has changed", "Well designed", "Adequately maintained"], 1,
   "Review annually: what found something, what never does, what risks emerged.", "Ch8 §9", "Programme design"),
 Q("The most dangerous test failure is one that:", ["Produces too many hits", "Returns nothing because it is broken", "Runs slowly", "Has a stale threshold"], 1,
   "A nil result reads as assurance and nothing will tell you otherwise.", "Ch9 §5", "Maintaining the library"),
 Q("The defence against a silently broken test is:", ["Peer review", "Verifying it against a case known to trigger it", "More frequent running", "A second query"], 1,
   "A scanner whose silence has never been tested is not evidence of anything.", "Ch9 §6", "Maintaining the library"),
 Q("Which measure of the programme is most worth tracking?", ["Exceptions raised", "Proportion of hits that were genuine, and of findings implemented", "Tests built", "Domains covered"], 1,
   "Counting exceptions rewards noisy tests.", "Ch9 §9", "Maintaining the library"),
 Q("A retired test's definition should be:", ["Deleted", "Kept with its reasoning", "Archived without context", "Transferred"], 1,
   "A deleted test leaves a gap nobody can explain.", "Ch9 §7", "Maintaining the library"),
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
    rebalance(QUESTIONS, "control:test_design:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "control:test_design:checks")

    mod = {
        "title": "Building the Tests",
        "desc": ("Designing your own, because no library covers what you need next week. "
                 "From risk to observable signature to query, defining a population "
                 "properly, nil-expected against analytical tests, the false positive "
                 "problem that kills every exception programme, composite scoring across "
                 "domains, scheduling by consequence, and keeping a library that does not "
                 "quietly break."),
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
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("questions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("topics:", dict(collections.Counter(q["topic"] for q in QUESTIONS)))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
