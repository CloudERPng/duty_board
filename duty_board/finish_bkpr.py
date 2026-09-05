#!/usr/bin/env python3
"""Finish the Bookkeeper track: m1, m2a, m2b, face.

m4 is already complete. This closes the remaining four modules:

  m1   8 chapters -> 9, 7 thin, 27 questions -> 35
  m2a  8 chapters -> 9, 6 thin, 27 questions -> 35
  m2b  7 chapters -> 9, 4 thin, 27 questions -> 35
  face 9 chapters,      4 thin, 34 questions -> 35

The four new chapters are chosen the same way m4's were — by what a bookkeeper
meets that the module does not cover — rather than by what would round the
count up:

  m1 gains COVER. Leave, illness and somebody else's clients. The module builds
  an elaborate personal discipline and never says what happens when the person
  holding it is absent, which is the moment the playbook chapter exists for and
  is never connected to.

  m2a gains THE MONTH THAT WILL NOT BALANCE. Every other chapter posts a line
  correctly. None covers the ordinary situation of a bank ledger that disagrees
  with the statement and the ordered way to find out why, which is the single
  most common way a posting day goes wrong.

  m2b gains DEPRECIATION AND THE ASSET REGISTER, which the close checklist ticks
  and no chapter teaches — a genuine hole rather than a thin patch. And YEAR
  END, because every chapter stops at the month and the client's audit, tax
  filing and annual accounts all draw on exactly this work.

Depth is added as substance rather than padding: each extension is a case, a
worked figure or a failure mode that belongs to the chapter it joins.

Run from the app package directory:  python3 finish_bkpr.py
"""

import collections
import io
import json
import random
import re
import sys

DATA = "academy_bkpr_data.json"
BANNED = ["at the end of the day"]

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


EXTEND = {
"m1": {
 0: """<p><b>What the tier costs when it is not read.</b> A client on the standard tier asks, reasonably, why their PAYE has not been filed. Nobody has done anything wrong — it is not in their tier — and the conversation is now about what they thought they were buying. That is a sales conversation happening in a bookkeeping room, and it happens because somebody promised in passing what the tier did not contain. Read the tier before answering any question that begins with 'do you also'.</p>

<p><b>Why one platform is a commercial decision and not a technical one.</b> Depth compounds: the fortieth client teaches you something usable on the first. A firm working across five accounting systems has staff who are competent everywhere and expert nowhere, and the difference shows up as time per close — which is the only number that decides whether the engagement makes money.</p>""",
 1: """<p><b>Compute one yourself, now.</b> Period September 2026. The 3rd working day of October: the 1st is a Thursday, so 1st, 2nd (Friday), then the 5th (Monday) — the reconciliation is due Monday the 5th, not Saturday the 3rd. The 5th working day is Wednesday the 7th. Doing this by hand once is what makes the computed dates on the board readable rather than mysterious.</p>

<p><b>Why fixed statutory days snap backward and deliverables do not.</b> A deliverable is a promise between us and the client, so it moves to the next working day we can honour it. A statutory date is a promise to an authority that does not care about our calendar — so we arrive early. Two different kinds of date, two different rules, and confusing them is how a filing becomes late while the board still shows green.</p>""",
 2: """<p><b>The reading order that makes the board fast.</b> Red first, wherever it is. Then amber posting chips, because those are today's work rather than tomorrow's. Then anything showing the reviewer eye for more than a day, since a pack sitting in review is a pack not delivered and the delay is invisible to the client until it is not.</p>

<p><b>The cell that is green and wrong.</b> Delivered on time, ticked, acknowledged — and the pack contained an error nobody caught. The board records that the process ran, not that the answer was right, and no board can. That is why the review gate and the checklist exist as separate machinery: colour is evidence of movement, and the ticks are the only evidence of verification.</p>

<p><b>What the board cannot tell you.</b> Whether the work behind a green cell was any good. A cell moves because somebody moved it, and the checklist behind it is the only evidence of what was actually verified — which is why lesson 7 exists and why a unit that watches only the colours slowly stops meaning anything by them.</p>""",
 4: """<p><b>The query that is really a training gap.</b> Some clients generate the same query every month — the same unlabelled transfer, the same missing reference. That is not a query problem, it is a habit problem, and the fix is a conversation about how they narrate their payments rather than twelve identical queries a year. Raise it once as a pattern: 'we ask about these every month — could Tunde add the invoice number to the transfer reference?'</p>

<p><b>The query nobody answers.</b> After the system's reminders, some go stale anyway. Escalate rather than accumulate: tell the books manager, note it in the pack's cover note as awaiting the client, and post the item to suspense with the query referenced. What must not happen is a decision made for the client by a bookkeeper who got tired of waiting.</p>""",
 5: """<p><b>What review is for, and what it is not.</b> It is not a second person redoing the work — nobody has time and it would prove little. It is a different pair of eyes on the shape: does the flux read sensibly, do the controls tie, has anything unusual been flagged, does the pack say what the month was. A reviewer who recomputes has misunderstood the job; one who reads only the totals has too.</p>

<p><b>The close that goes wrong quietly.</b> Everything ticks, the pack ships, and a fortnight later the client asks about a figure nobody can explain. Trace it back and the cause is almost always a checklist item ticked from memory — the accrual reversal that was assumed rather than seen. The gate holds only if the ticks are true, which is the whole of lesson 7.</p>""",
 6: """<p><b>Why the checklist is worded as assertions.</b> Each item is written so that ticking it says something specific and falsifiable. 'Accruals posted' would be a task; 'recurring accruals raised, prior accruals reversed against actuals, prepayment releases per schedule' is a claim somebody could check you on. That distinction is deliberate — a checklist of tasks measures effort, and a checklist of assertions measures whether the books are right.</p>

<p><b>Ticking under time pressure.</b> The honest move when a deadline is close and an item is genuinely not done is to leave it unticked and say so in the notes, which delays the pack by a day. The dishonest move takes ten seconds and is undetectable until the month it is not. Everybody meets this; the professionals treat the checklist as the one place they never economise.</p>""",
 7: """<p><b>How a playbook actually goes out of date.</b> Not all at once. A bank contact changes, a settlement rate moves, the client opens a second account, and each of those is a small thing nobody records because the person who learned it also remembers it. Six months later somebody covers that client and the playbook describes a business that no longer exists. Update it the day you learn something, in the moment, rather than in a review nobody schedules.</p>

<p><b>The access register's real job.</b> Not security theatre — leaver management. When somebody leaves the firm, the register is the list of what must be revoked, and where it is incomplete the revocation is too. That is also why credentials live in the vault rather than the playbook: the playbook is shared to be useful, and the vault is not.</p>""",
},
"m2a": {
 0: """<p><b>Why the party question comes first rather than the amount or the direction.</b> Because it is the only question whose answer changes which ledgers move. A party payment touches the customer or supplier ledger and their aging; a journal entry does not. Get that wrong and the figures may still balance while the receivables schedule quietly stops matching the control — which surfaces at month end as a controls problem that started as a posting shortcut.</p>

<p><b>The tempting fourth option, and why it is not on the tree.</b> Posting a party payment as a journal entry directly to the receivable account. It balances, it is faster, and it leaves the invoice showing as outstanding forever. The aging then lies, the client chases a customer who has paid, and somebody spends an afternoon working out why.</p>""",
 1: """<p><b>Narrations are written for the bank, not for you.</b> They are truncated to a fixed length, so a long payer name loses its ending, and reference fields carry whatever the sender typed — including nothing. Treat the narration as evidence rather than instruction: it tells you what to check, not what to post. Where it is ambiguous, the amount and the date usually resolve it against an open invoice faster than the name does.</p>

<p><b>Build the client's own dialect into the playbook.</b> Every business has recurring narrations peculiar to it — a landlord's transfer, a director's standing order, a supplier who always pays from a personal account. After the second time you look one up, it belongs in the playbook, and the next person saves the same ten minutes you spent.</p>""",
 3: """<p><b>Why the stop rule is a rule rather than a judgement.</b> Because the pressure is always in the same direction: the payment is real, the bank shows it, and posting it somewhere feels like progress. On-account is progress — it puts the money on the right party's ledger and leaves the allocation for when the evidence exists. What looks like the same thing and is not is allocating to an invoice you created to have something to allocate to.</p>

<p><b>The on-account balance is a work list.</b> Unallocated payments sitting on supplier accounts are documents still missing, and they should be read that way monthly rather than accumulating quietly. A supplier with three on-account payments and no invoices is a document request that was never chased, and it will surface at year end when somebody asks what the balance represents.</p>""",
 4: """<p><b>Grossing up, explained once because it catches everybody.</b> The bank credits interest net of withholding tax. Posting only the credit understates income and loses an asset — the WHT is recoverable and only exists in the books if it is recorded. So the journal recognises the full interest and splits the deduction to WHT receivable. The same shape applies anywhere a payer deducts before paying you.</p>

<p><b>Why correcting entries are reversals rather than edits.</b> A wrong journal is reversed and reposted, leaving both entries visible and linked. Editing it leaves a ledger that has quietly changed since somebody last looked at it, which is precisely the thing a reconciliation, a review or an auditor is trying to rely on. The trail costs one extra line.</p>""",
 6: """<p><b>What suspense is not for.</b> A transaction you could classify with ten minutes of work. Suspense holds items whose answer is genuinely outside the books — a question only the client can settle. Using it for anything you simply have not got to yet turns a control account into a to-do list, and the month-end zero becomes a scramble rather than a confirmation.</p>

<p><b>Reading the suspense balance as a signal.</b> A balance that clears every month is healthy. One that never quite reaches zero, or that carries the same item for three months, is telling you something about the client relationship rather than about the bookkeeping — usually that queries are not being answered and nobody has escalated it.</p>""",
 7: """<p><b>The float, which is where cash businesses go wrong.</b> A till float is not income and not an expense; it moves between cash-in-till and the bank and back. Treating a float top-up as a purchase, or a float return as a deposit of sales, misstates both cash and revenue — and because the amounts are small and regular, it is one of the errors most likely to run for a year unnoticed.</p>

<p><b>Reconciling cash-in-till.</b> The ledger balance should agree to what the client says is physically there, and where it does not, the difference is a question rather than an adjustment. Cash differences are ordinary in retail and they are still differences: post them to a named account so the pattern is visible, never absorb them into sales.</p>""",
},
"m2b": {
 1: """<p><b>What makes an estimate defensible.</b> A basis somebody else could reproduce. Three months' pattern, a contract rate, a meter reading — any of these can be written in one line and checked. 'About the usual' cannot, and it is the difference between an accrual and a plug. Write the basis into the journal's remarks at the moment you post it, because in six weeks you will not remember it.</p>

<p><b>The accrual that is never reversed.</b> The commonest accrual failure. The estimate is raised, the actual arrives and is posted normally, and the reversal never happens — so the expense is counted twice and a liability sits on the balance sheet forever. Using the dated reversal at the moment of posting is what removes this from the list of things anybody has to remember.</p>""",
 2: """<p><b>Prepayments that outlive their schedule.</b> A prepaid balance still sitting after its final release means either the schedule stopped being run or a renewal was posted to prepaid without a new schedule line. Both are found the same way: read the prepaid balance against the schedule's remaining total every month-end, and where they disagree, fix the schedule before the ledger.</p>

<p><b>What belongs in prepayments and what does not.</b> Rent, insurance, licences, subscriptions — costs paid for a defined future period. A deposit is not a prepayment; it is a receivable, because it comes back. A stock purchase is not a prepayment either. The test is whether time is what converts it into an expense.</p>""",
 3: """<p><b>Why the net figure is the one that reconciles.</b> The bank shows one salary line; the journal creates five accounts of movement. The link between them is the net salaries control, which the bank line clears exactly — so if the bank line does not equal the control balance, the payroll journal and the payment disagree and one of them is wrong. That check takes ten seconds and catches most payroll posting errors.</p>

<p><b>Statutory controls, filled and emptied.</b> PAYE and pension payables fill on pay day and empty on remittance. A balance that grows month on month means remittances are not being made or not being posted against the control, and either is worth raising immediately — the first is a compliance problem for the client and the second is a bookkeeping one for us.</p>""",
 5: """<p><b>Writing a flux sentence somebody else can use.</b> Cause, magnitude, and whether it recurs. 'Kolawole price increase from PO 118, plus volume; margin down 3 points; expect this to hold' does all three in a line, and it is what lets the cover note be written in five minutes rather than reconstructed. A sentence that only says what moved has done half the job.</p>

<p><b>The movement with no explanation.</b> Sometimes nothing explains it and the investigation finds an error — that is the method working, and the electricity line exists to show it. What must not happen is a plausible sentence written to close the gap. 'Seasonal variation' is the phrase to watch for in your own notes; it is true often enough to be tempting and it explains nothing.</p>""",
},
"face": {
 3: """<p><b>Why the register is monthly rather than a running list.</b> Because the pattern is the point. A single missed day tells nobody anything; a row with three gaps in a fortnight is a conversation about capacity or about a client who has become difficult to work. Reading it monthly means the conversation happens while it is still about workload rather than about performance.</p>

<p><b>What to do with your own row.</b> Read it before your manager does. A row with an obvious explanation — leave, a client on hold, a week of onboarding — is worth a sentence in the digest note rather than a question later. The register is not an accusation, and it becomes one only when it is the manager who notices first.</p>""",
 5: """<p><b>Why onboarding is a runbook rather than a checklist in somebody's head.</b> Because it happens rarely enough that nobody is fluent in it. A bookkeeper does perhaps three a year, each some months apart, and the steps most often skipped are the ones with no immediate consequence — the playbook first draft, the standard monthly requests explained. Those are exactly the ones that cost a year of small friction when missed.</p>

<p><b>The step that is worth doing properly whatever the hurry.</b> Opening balances agreed. Everything after it inherits whatever was accepted, and a balance agreed loosely at onboarding is a difference somebody hunts at the first reconciliation, the first control tie and the first year end. Agreed means agreed in writing with the client, not accepted from a spreadsheet.</p>""",
 6: """<p><b>What the rate does not mean.</b> That a bookkeeper is slow. An engagement can read red because the fee was set before anybody knew the volume, because the client is genuinely difficult, or because onboarding hours landed in one month. The number opens a conversation about the engagement rather than about the person, and reading it any other way makes people log fewer hours — which destroys the only measurement the unit has.</p>

<p><b>Why hours must be tagged to be counted.</b> An untagged session is invisible to this screen. That is not a rule for the manager's benefit: it is the mechanism by which an underpriced engagement becomes provable, and a bookkeeper who does not tag their hours is the one with no evidence when the load conversation comes.</p>""",
 7: """<p><b>Why billing runs on the 28th regardless.</b> The fee is for the service month and delivery timing is a separate conversation — which sounds harsh and protects everybody. A run conditional on delivery would make an invoice into a scorecard, put pressure on the close, and give a client the impression that a late pack is a discount negotiation. Delivery problems are handled as delivery problems.</p>

<p><b>What to check before submitting the drafts.</b> The no-fee list first, because those clients were silently skipped and will be invisible until somebody notices the revenue is short. Then any client whose fee changed mid-month, since the draft carries the customer record's current figure rather than what was agreed for the period.</p>""",
},
}

NEW_CHAPTERS = {
"m1": [("Cover — leave, illness, and somebody else's clients", 5, """<p>Everything so far builds a personal discipline. This chapter is about the days you are not there, which is when the discipline is tested and when the playbook chapter stops being paperwork.</p>

<p><b>Planned absence.</b> Two things before you go, and they take under an hour. Bring every client's playbook current — not tidied, current: what is mid-flight, what is expected while you are away, which query is stale and who is chasing it. Then hand over in person or in writing to whoever is covering, naming the one thing per client that will bite them.</p>

<p><b>What cover actually means.</b> Not doing your job to your standard — nobody can, and expecting it produces cover that quietly does nothing. It means keeping the books current enough that your return is a resumption rather than a recovery: post the bank, attest honestly, raise queries, and leave anything requiring judgement about that client for you unless it is time-critical.</p>

<p><b>Attesting for somebody else's client.</b> The claim is the same claim and it is now yours. Attest what you actually posted through, not what the previous attestation said, and where you did not get to a client, attest nothing rather than repeating yesterday's date — a stale date carried forward is a false statement made by inertia. A red chip that is honest is worth more than a green one that is not.</p>

<p><b>Unplanned absence.</b> Illness does not permit a handover, which is precisely why the playbook is maintained continuously rather than before leave. The test of a playbook is whether somebody could pick up that client tomorrow without speaking to you — and the honest way to check is to read your own and ask what is only in your head.</p>

<p><b>Coming back.</b> Read the register for your clients before you read anything else: which days are marked, which are silent, what the covering bookkeeper attested. Then the follow-ups list, because a query raised while you were away has been waiting longest. Twenty minutes of that beats a day of discovering things.</p>

<p><b>The client who notices you are away.</b> They will, and what they should not notice is a drop in the service. Tell them before you go where the tier makes it relevant — a one-line message naming who is covering and for how long costs nothing and prevents the question arriving as a complaint. Silence is what makes an absence feel like neglect.</p>

<p><b>And the part that is about the unit rather than about you.</b> Cover is reciprocal and it is remembered. The bookkeeper whose clients are easy to cover — playbook current, queries logged, nothing held privately — is the one colleagues cover willingly. The one whose clients require an archaeology dig gets covered once, carefully, and everybody remembers.</p>""")],
"m2a": [("The month that will not balance", 5, """<p>Every chapter so far posts a line correctly. This is the ordinary situation where the postings are done, the bank ledger disagrees with the statement, and you have to find out why — which is the commonest way a posting day goes wrong.</p>

<p><b>Work it in order, because the order is what stops it taking all afternoon.</b></p>

<p><b>First, the difference itself.</b> Write it down and look at it before doing anything. Is it a round number? A duplicated amount you recognise? Divisible by nine, which usually means transposed digits? Equal to a single transaction you can see on the statement? Two of those five questions solve most differences in under a minute.</p>

<p><b>Second, direction.</b> Is the ledger higher or lower than the bank? Ledger higher means something was posted that the bank has not shown — an unpresented cheque, a duplicate posting, or a payment posted to the wrong month. Ledger lower means something on the statement is not yet in the books, which is usually a charge, a direct debit or a credit nobody told you about.</p>

<p><b>Third, count rather than sum.</b> Compare the number of transactions in the period, not just the total. A count difference of one against a value difference tells you it is a single missing item, which is a very different search from a value difference with matching counts — that is a wrong amount, not a missing line.</p>

<p><b>Fourth, the usual suspects, in this order.</b> Charges posted late or not at all. A transfer between the client's own accounts posted once instead of twice. A payment allocated to the wrong bank account where the client has two. A reversal posted without its original, or an original without its reversal.</p>

<p><b>Fifth, and only fifth, line by line.</b> Tick the statement against the ledger in date order. It is slow, it always works, and reaching for it first is what turns a ten-minute difference into an afternoon.</p>

<p><b>The difference that is not an error at all.</b> Timing. A cheque issued and not presented, a transfer initiated late on the last day, a lodgement credited the next morning — all of these are correct in both records and simply not yet in both. They belong on the reconciliation as reconciling items rather than being hunted as mistakes, and recognising them early is what separates a ten-minute reconciliation from an hour of searching for something that was never wrong.</p>

<p><b>The rule about what you must never do.</b> Post a balancing figure to make it agree. A plug is a lie that reconciles, it will be inherited by whoever holds the client next, and it removes the only evidence that something upstream is wrong. If you genuinely cannot find it, say so — an unexplained difference raised to your reviewer today is a normal event; the same difference discovered in six months, buried under a plug, is not.</p>""")],
"m2b": [
("Depreciation and the asset register", 5, """<p>The close checklist ticks 'depreciation posted' and no chapter has taught it. This one does, because an asset register that drifts is one of the few errors that compounds every month without ever announcing itself.</p>

<p><b>What an asset is, for this purpose.</b> Something the business bought that will be useful for more than a year — a generator, a vehicle, shop fittings, a laptop above whatever threshold the client's policy sets. Below the threshold it is an expense on the day it is bought, and the threshold is a policy decision recorded in the playbook rather than a judgement made per purchase.</p>

<p><b>The register is the source, not the ledger.</b> Every asset carries its cost, its purchase date, its useful life, its method, and its accumulated depreciation to date. The monthly charge is computed from that register, and the ledger receives it — never the other way round. A ledger balance that cannot be traced to a register line is a balance nobody can defend.</p>

<p><b>The monthly posting.</b> Dr Depreciation Expense, Cr Accumulated Depreciation, per asset class rather than per asset, from the register's computed total. Where the client's system runs it automatically, the tick asserts that you verified it was sane — that the run happened, covered the period once, and agrees to the register — rather than that it exists.</p>

<p><b>The three events that break a register.</b> An asset bought and expensed by mistake, so it never enters. An asset disposed of or scrapped and never removed, so it depreciates forever. And a purchase posted at the wrong cost — commonly gross of a trade-in, or including a first-year service. Each is found the same way: reconcile the register total to the ledger's cost account every month-end, exactly as a control account.</p>

<p><b>Disposals, in one line.</b> Remove the cost and the accumulated depreciation together, put the proceeds against them, and whatever remains is a gain or a loss to the P&amp;L. The commonest error is booking the proceeds to income and leaving the asset in place, which overstates both income and assets simultaneously.</p>

<p><b>Why the first month is the one to get right.</b> A depreciation policy applied from the wrong start date, or a life set carelessly, does not fail — it just quietly produces a slightly wrong charge every month for years, and correcting it later means restating every period since. Five minutes on the register entry at purchase is worth more than any amount of later diligence.</p>

<p><b>And what to escalate.</b> Whether something is capital or expense, in any case that is not obvious, is a judgement with tax consequences. It goes to whoever holds that in your firm rather than being decided at posting speed.</p>"""),
("The year end, and what it draws on", 5, """<p>Every chapter so far stops at the month. This one is about what those months become, because the client's annual accounts, tax filing and any audit all draw on exactly the work described in this module.</p>

<p><b>What changes at year end, and it is less than people expect.</b> The same closing discipline, applied once more, with three additions: everything is looked at across twelve months rather than one, balances are confirmed rather than reconciled, and somebody outside the process reads it.</p>

<p><b>Confirming rather than reconciling.</b> A monthly reconciliation proves the ledger agrees with a statement. Year end asks a harder question of every balance sheet line: what is this, and can it be evidenced? Receivables against a schedule and the client's confirmation of who genuinely owes; stock against a count; loans against a lender's statement; the asset register against reality. A balance carried for twelve months without that question being asked is where the surprises live.</p>

<p><b>What the twelve-month read finds that a monthly read does not.</b> A control account that never quite cleared. An accrual reversed in one month and re-raised in the next. A prepayment schedule that stopped being run in August. None of these is visible in the month it happens; all are obvious across a year.</p>

<p><b>Preparing the file.</b> Whoever prepares the annual accounts — the client's auditor, a tax adviser, the firm — needs the same things every time: the trial balance, the reconciliations, the schedules behind every material balance, and the explanations. A unit that has done its monthly work properly assembles this in a day. One that has not spends weeks, at a cost somebody pays.</p>

<p><b>What the bookkeeper owns and does not.</b> You own the records being complete, reconciled and evidenced. You do not own the tax computation, the accounting policy judgements or the accounts themselves — those sit with whoever is engaged for them. Knowing that boundary before the year-end conversation starts is what keeps you from being asked, in good faith, to decide something that is not yours.</p>

<p><b>What the client experiences, and why it matters commercially.</b> A year end that arrives as a short list of confirmations is a client who renews without thinking about it. One that arrives as weeks of requests, reconstructions and surprises is a client who starts wondering what they have been paying for — and the difference between those two experiences was decided across twelve unremarkable months, not in the fortnight anybody is looking.</p>

<p><b>And the habit that makes year end unremarkable.</b> Ask the confirming question once a quarter rather than once a year, on the two or three balances that carry the most. Four small conversations across the year replace one long uncomfortable one, and nothing is discovered eleven months after it could have been fixed.</p>""")],
}

CHECKS = {
"m1": {8: [
 C("The two things to do before planned leave are handing over in person or in writing, and:",
   ["Clearing every query", "Bringing every client's playbook current",
    "Attesting through the leave period", "Closing the period"], 1,
   "Current rather than tidied: what is mid-flight, what is expected, which query is stale and who is chasing it."),
 C("Where a covering bookkeeper did not reach a client, they should attest:",
   ["Yesterday's date again", "Nothing",
    "The period start", "An estimate"], 1,
   "A stale date carried forward is a false statement made by inertia; an honest red chip beats a false green one."),
 C("The test of a playbook is whether somebody could pick up that client tomorrow:",
   ["With a short briefing", "Without speaking to you",
    "Within a week", "With the manager's help"], 1,
   "Which is why it is maintained continuously rather than before leave — illness does not permit a handover.")]},
"m2a": {8: [
 C("A difference divisible by nine usually indicates:",
   ["A missing charge", "Transposed digits",
    "A duplicate posting", "A timing difference"], 1,
   "One of five questions to ask of the difference itself before doing anything else."),
 C("A ledger balance higher than the bank suggests something posted that the bank has not shown, such as:",
   ["A bank charge", "An unpresented cheque",
    "A direct debit", "An uncredited receipt"], 1,
   "Ledger lower means something on the statement is not yet in the books."),
 C("Comparing the count of transactions as well as the total tells you:",
   ["Nothing extra", "Whether it is a single missing item or a wrong amount",
    "The direction", "Which account is affected"], 1,
   "A count difference with a value difference is a very different search from matching counts.")]},
"m2b": {7: [
 C("The monthly depreciation charge is computed from:",
   ["The ledger balance", "The asset register",
    "The prior month", "The purchase invoices"], 1,
   "The ledger receives it — never the other way round, since a balance that cannot be traced to a register line cannot be defended."),
 C("An asset disposed of but never removed from the register:",
   ["Stops depreciating", "Depreciates forever",
    "Is written off automatically", "Shows as an error"], 1,
   "One of three events that break a register, all found by reconciling it to the cost account monthly."),
 C("Booking disposal proceeds to income and leaving the asset in place:",
   ["Is acceptable if immaterial", "Overstates both income and assets simultaneously",
    "Understates profit", "Affects only the balance sheet"], 1,
   "Cost and accumulated depreciation come out together, with proceeds against them.")],
8: [
 C("Year end asks of every balance sheet line a harder question than reconciliation, namely:",
   ["Is it material", "What is this, and can it be evidenced",
    "Has it moved", "Is it authorised"], 1,
   "A balance carried twelve months without that question is where the surprises live."),
 C("A prepayment schedule that stopped being run in August is:",
   ["Visible each month", "Obvious across a year and invisible in the month it happens",
    "Caught by the control tie", "Found at reconciliation"], 1,
   "Which is what the twelve-month read finds that a monthly read does not."),
 C("The bookkeeper owns the records being complete, reconciled and evidenced, but not:",
   ["The reconciliations", "The tax computation and the accounting policy judgements",
    "The schedules", "The trial balance"], 1,
   "Knowing that boundary before the year-end conversation is what stops you being asked in good faith to decide something that is not yours.")]},
}

EXTRA_Q = {
"m1": [
 Q("A question beginning 'do you also' should be answered:", ["From experience", "After reading the tier", "By the manager", "Provisionally"], 1,
   "A promise made in passing becomes a sales conversation happening in a bookkeeping room.", "M1 L1", "Tiers"),
 Q("A deliverable due date moves forward to the next working day, while a fixed statutory date:", ["Does the same", "Snaps backward", "Is fixed regardless", "Is negotiated"], 1,
   "A promise to an authority that does not care about our calendar, so we arrive early.", "M1 L2", "Cadence"),
 Q("The board reading order is red first, then amber posting chips, then:", ["The newest cells", "Anything showing the reviewer eye for more than a day", "Unassigned clients", "Delivered cells"], 1,
   "A pack sitting in review is a pack not delivered.", "M1 L3", "The matrix"),
 Q("A client generating the same query every month is:", ["A query problem", "A habit problem", "A tier problem", "Normal"], 1,
   "Raise it once as a pattern rather than twelve identical times a year.", "M1 L5", "Follow-ups"),
 Q("A reviewer who recomputes the work has:", ["Done it thoroughly", "Misunderstood the job", "Found an error", "Exceeded scope"], 1,
   "Review is a different pair of eyes on the shape, not a second person redoing it.", "M1 L6", "The close"),
 Q("The checklist is worded as assertions rather than tasks because a task list measures:", ["Completeness", "Effort", "Time", "Coverage"], 1,
   "A checklist of assertions measures whether the books are right.", "M1 L7", "Checklists"),
 Q("A playbook goes out of date:", ["All at once, annually", "A small thing at a time, unrecorded", "When staff change", "At year end"], 1,
   "Because the person who learned it also remembers it, until they are not there.", "M1 L8", "Playbooks"),
 Q("The access register's real job is:", ["Security theatre", "Leaver management", "Audit evidence", "Client assurance"], 1,
   "It is the list of what must be revoked when somebody leaves the firm.", "M1 L8", "Playbooks"),
 Q("Cover means keeping the books current enough that your return is:", ["Unnecessary", "A resumption rather than a recovery", "Immediate", "Supervised"], 1,
   "Not doing your job to your standard, which nobody can.", "M1 L9", "Cover"),
],
"m2a": [
 Q("Posting a party payment as a journal to the receivable account leaves:", ["A balanced ledger only", "The invoice outstanding forever and the aging lying", "A reconciling item", "A control difference"], 1,
   "The tempting fourth option that is not on the decision tree.", "M2a L1", "The decision tree"),
 Q("A bank narration should be treated as:", ["An instruction", "Evidence", "A reference", "A description"], 1,
   "It tells you what to check, not what to post.", "M2a L2", "Statement anatomy"),
 Q("A recurring narration peculiar to one client belongs, after the second lookup, in:", ["Your notes", "The playbook", "The query log", "The remarks"], 1,
   "The next person saves the ten minutes you spent.", "M2a L2", "Statement anatomy"),
 Q("Unallocated on-account payments on supplier accounts should be read monthly as:", ["A balance", "A work list of missing documents", "A timing difference", "A control item"], 1,
   "Three on-account payments and no invoices is a document request that was never chased.", "M2a L4", "The stop rule"),
 Q("Interest credited net of withholding tax is posted by:", ["Recording the net", "Recognising the full interest and splitting the deduction to WHT receivable", "Ignoring the WHT", "Accruing the difference"], 1,
   "The WHT is recoverable and only exists in the books if it is recorded.", "M2a L5", "Journal craft"),
 Q("Suspense used for anything you have not got to yet turns a control account into:", ["A clearing account", "A to-do list", "A reconciling item", "An expense"], 1,
   "It holds items whose answer is genuinely outside the books.", "M2a L7", "Suspense"),
 Q("A till float top-up posted as a purchase misstates:", ["Cash only", "Both cash and revenue", "Revenue only", "Nothing material"], 1,
   "Small and regular, which is why it can run for a year unnoticed.", "M2a L8", "Clearing accounts"),
 Q("A cash difference in a retail till should be:", ["Absorbed into sales", "Posted to a named account so the pattern is visible", "Adjusted at month end", "Ignored below a threshold"], 1,
   "Ordinary in retail and still a difference.", "M2a L8", "Clearing accounts"),
 Q("Posting a balancing figure to make a reconciliation agree is:", ["A last resort", "A lie that reconciles", "Acceptable if noted", "A rounding entry"], 1,
   "It will be inherited by whoever holds the client next.", "M2a L9", "The month that will not balance"),
],
"m2b": [
 Q("A defensible estimate has:", ["A conservative figure", "A basis somebody else could reproduce", "Manager approval", "A materiality threshold"], 1,
   "Written into the journal's remarks at the moment of posting.", "M2b L2", "Accruals"),
 Q("The commonest accrual failure is:", ["Over-estimating", "The reversal never happening", "Posting to the wrong account", "Missing the period"], 1,
   "The expense is counted twice and a liability sits on the balance sheet forever.", "M2b L2", "Accruals"),
 Q("A deposit is not a prepayment because:", ["It is immaterial", "It comes back", "It is not time-based", "It is an expense"], 1,
   "The test is whether time is what converts it into an expense.", "M2b L3", "Prepayments"),
 Q("If the salary bank line does not equal the net salaries control:", ["Adjust the control", "The payroll journal and the payment disagree", "Accrue the difference", "It is a timing issue"], 1,
   "A ten-second check that catches most payroll posting errors.", "M2b L4", "Payroll"),
 Q("A statutory control balance growing month on month means remittances are not being made, or:", ["The rate changed", "They are not posted against the control", "Payroll is wrong", "The schedule is stale"], 1,
   "The first is a compliance problem for the client and the second a bookkeeping one for us.", "M2b L4", "Payroll"),
 Q("A good flux sentence gives cause, magnitude and:", ["The account", "Whether it recurs", "The comparison", "The approver"], 1,
   "A sentence that only says what moved has done half the job.", "M2b L6", "Flux"),
 Q("The phrase to watch for in your own flux notes is:", ["Price increase", "Seasonal variation", "Volume", "Timing"], 1,
   "True often enough to be tempting, and it explains nothing.", "M2b L6", "Flux"),
 Q("The capital-or-expense judgement in an unobvious case:", ["Is made at posting speed", "Goes to whoever holds it in the firm", "Follows the threshold", "Is the client's"], 1,
   "It is a judgement with tax consequences.", "M2b L8", "Depreciation"),
 Q("Asking the year-end confirming question once a quarter rather than once a year means:", ["More work overall", "Four small conversations replace one long uncomfortable one", "Earlier filing", "Fewer schedules"], 1,
   "And nothing is discovered eleven months after it could have been fixed.", "M2b L9", "Year end"),
],
"face": [
 Q("The register is monthly rather than a running list because:", ["It is easier to read", "The pattern is the point", "Storage limits", "Managers review monthly"], 1,
   "A row with three gaps in a fortnight is a conversation about capacity while it is still about workload.", "Face L4", "The Register"),
],
}


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
    data = json.load(io.open(DATA, encoding="utf-8"))
    TARGET = {"m1": 9, "m2a": 9, "m2b": 9, "face": 9}

    for fam, exts in EXTEND.items():
        mod = data[fam]
        for idx, extra in sorted(exts.items()):
            if "<!--deep-->" in mod["lessons"][idx]["html"]:
                continue
            mod["lessons"][idx]["html"] = (
                mod["lessons"][idx]["html"].rstrip() + "\n<!--deep-->" + extra)

    for fam, chapters in NEW_CHAPTERS.items():
        mod = data[fam]
        have = {l["title"] for l in mod["lessons"]}
        for title, est, html in chapters:
            if title not in have:
                mod["lessons"].append({"title": title, "est": est, "html": html})

    for fam, qs in EXTRA_Q.items():
        mod = data[fam]
        have = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in mod["questions"]}
        for q in qs:
            if re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() not in have:
                mod["questions"].append(q)

    problems = []
    for fam, want in TARGET.items():
        if len(data[fam]["lessons"]) != want:
            problems.append("%s has %d chapters, expected %d" % (fam, len(data[fam]["lessons"]), want))

    for fam, chapters in CHECKS.items():
        mod = data[fam]
        rebalance([c for _i, ch in sorted(chapters.items()) for c in ch], "bkpr:%s:new" % fam)
        bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in mod["questions"]}
        seen = set()
        for l in mod["lessons"]:
            for c in l.get("checks") or []:
                seen.add(re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip())
        for idx, checks in sorted(chapters.items()):
            for c in checks:
                norm = re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip()
                if norm in bank:
                    problems.append("%s duplicates exam q: %s" % (fam, c["q"][:50]))
                if norm in seen:
                    problems.append("%s duplicate check: %s" % (fam, c["q"][:50]))
                seen.add(norm)
                if len(c.get("why") or "") < 40:
                    problems.append("%s weak rationale: %s" % (fam, c["q"][:46]))
                if len(c["opts"]) != 4:
                    problems.append("%s not 4 options: %s" % (fam, c["q"][:46]))
            mod["lessons"][idx]["checks"] = [dict(c, sort=i) for i, c in enumerate(checks)]

    for fam in TARGET:
        mod = data[fam]
        rebalance(mod["questions"], "bkpr:%s:exam2" % fam)
        for i, l in enumerate(mod["lessons"]):
            if len(l.get("checks") or []) != 3:
                problems.append("%s ch%d has %d checks" % (fam, i + 1, len(l.get("checks") or [])))
            flat = re.sub(r"<[^>]+>", " ", l["html"]).lower()
            for b in BANNED:
                if b in flat:
                    problems.append("%s banned phrase ch%d" % (fam, i + 1))

    if problems:
        sys.exit("ABORT — %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("%-6s %5s %6s %6s %7s %6s" % ("mod", "chap", "mean", "min", "checks", "quest"))
    for fam in ["m1", "m2a", "m2b", "m4", "face"]:
        mod = data[fam]
        lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
        print("%-6s %5d %6d %6d %7d %6d" % (
            fam, len(lens), sum(lens) / len(lens), min(lens),
            sum(len(l.get("checks") or []) for l in mod["lessons"]), len(mod["questions"])))
    thin = [(f, i + 1) for f in TARGET for i, l in enumerate(data[f]["lessons"])
            if len(re.sub(r"<[^>]+>", " ", l["html"])) < 2500]
    print("thin:", thin or "NONE")


if __name__ == "__main__":
    main()
