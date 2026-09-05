#!/usr/bin/env python3
"""Add check questions to the CloudERP.One Certified Bookkeeper track.

Same repair as the ZhiftERP and ZhiftPOS tracks: the content is written and
unusually specific — worked figures, Nigerian statement narrations, real due-
date arithmetic — and it carries no checks at all across 37 chapters.

academy_repair.push_lesson_checks covers bkpr by name and matches by position,
so nothing in the seeder needs changing.

Checks are derived strictly from what each chapter states, and this track
rewards that more than most: the material is full of specific numbers and rules
that can be tested exactly rather than gestured at — the snap-backward rule, the
stop rule on a missing purchase invoice, suspense clearing to zero, the
₦50 EMTL, the two-settlement-day alarm on POS clearing.

The guard refuses the run on any duplicate against the exam bank, any repeated
check, any rationale under 40 characters, any option count other than four, or
any chapter of a touched module left without checks.

Run from the app package directory:  python3 add_bkpr_checks.py
"""

import collections
import io
import json
import random
import re
import sys

DATA = "academy_bkpr_data.json"
CHECK_ONLY = "--check" in sys.argv
FORCE = "--force" in sys.argv

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}


CHECKS = {
"m2b": {
 0: [
  C("Reconciliation proves the posting month worked by showing the bank's closing balance agreed to the ledger, and:",
    ["The difference within tolerance", "Every difference listed and explicable",
     "No unmatched lines", "The tool reporting zero"], 1,
    "Every kobo of the gap is explained rather than accepted as small."),
  C("An unpresented cheque issued on the 29th appears as a reconciling item because it:",
    ["Was posted late", "Will clear in the following month",
     "Was never posted", "Is disputed"], 1,
    "The ledger carries it and the bank has not yet seen it."),
  C("The reconciliation tool works by listing unreconciled ledger entries to:",
    ["Delete", "Match against statement lines, or clear by date",
     "Re-post", "Export"], 1,
    "Selected against the account, the statement date and its closing balance.")],
 1: [
  C("An accrual exists so that the statements tell the truth about:",
    ["The bank", "The period",
     "The supplier", "The cash position"], 1,
    "Cash postings say what happened; accruals say what the period consumed."),
  C("An estimated accrual should be reversed:",
    ["When the actual is paid", "On a date, using the reversal the system supports",
     "At year end", "Never — it is adjusted"], 1,
    "Use the dated reversal rather than remembering to do it."),
  C("Estimating July's electricity from the last three months' pattern is:",
    ["A guess to avoid", "The method, drawn from the playbook",
     "Only for small amounts", "A last resort"], 1,
    "The bill never arrives before the 10th, so the estimate is what makes July's statements true.")],
 2: [
  C("Prepayments are described as accruals' mirror because:",
    ["They are also estimates", "Cash left early and the expense belongs to the future",
     "They reverse monthly", "They sit in liabilities"], 1,
    "Annual rent paid in March posts to a prepaid asset rather than to expense."),
  C("₦2,400,000 of annual rent releases monthly at:",
    ["₦240,000", "₦200,000",
     "₦120,000", "The month's share of days"], 1,
    "One mechanical journal per schedule line, every month-end."),
  C("The schedule itself lives:",
    ["In the ledger", "Filed to the Hub and referenced in the playbook",
     "In the client's records", "In the checklist"], 1,
    "Which is what makes the monthly release verifiable rather than remembered.")],
 3: [
  C("The salaries bank line clears only:",
    ["The gross cost", "Net pay",
     "The employer pension", "PAYE"], 1,
    "The real event is the payroll journal, which books gross cost and splits every deduction to its keeper."),
  C("With gross of ₦1,800,000 and employer pension of ₦180,000, the P&L carries an employment cost of:",
    ["₦1,800,000", "₦1,980,000",
     "₦1,494,000", "₦1,656,000"], 1,
    "The employer contribution is a cost of employment rather than a deduction from the employee."),
  C("The pension control holds:",
    ["The employee share only", "Both shares — employee and employer",
     "The employer share only", "Net of PAYE"], 1,
    "₦144,000 plus ₦180,000, awaiting remittance to the fund.")],
 4: [
  C("A control account's balance must always be:",
    ["Nil at month end", "Derivable from a schedule outside the ledger",
     "Equal to the prior month", "Reconciled annually"], 1,
    "Monthly, the derived figure is proved against the ledger's balance."),
  C("A control higher than the derived figure means something was credited to it that:",
    ["Was posted twice", "Should not have been",
     "Belongs to next month", "Was remitted early"], 1,
    "Direction first is the start of the diagnostic sequence."),
  C("A control that disagrees with its schedule is:",
    ["Adjusted to agree", "Diagnosed before anything else ships",
     "Noted for the reviewer", "Carried forward"], 1,
    "The pack does not go out over an unexplained control.")],
 5: [
  C("Every material month-on-month movement earns:",
    ["A note if asked", "A one-sentence explanation in writing",
     "A supervisor review", "A recalculation"], 1,
    "Written into the checklist notes rather than held in the preparer's head."),
  C("Electricity up 99% is treated differently from the other movements because:",
    ["It is the largest", "99% is not a story — it is a stop and an investigation",
     "It affects margin", "It is seasonal"], 1,
    "The line demonstrates the method's value: some movements are explained, and some are questions."),
  C("The cost of sales sentence flags the margin drop to the MD because:",
    ["Policy requires escalation", "A price increase plus volume moved margin three points",
     "The supplier disputed it", "It exceeded budget"], 1,
    "The explanation names the cause and the consequence rather than only the percentage.")],
 6: [
  C("The pack is described as a harvest because by that point:",
    ["It is automated", "Postings, reconciliations, suspense, adjustments, controls and flux are all already done",
     "The client has approved it", "The reviewer has signed"], 1,
    "Nothing is prepared at pack time that was not already true."),
  C("The pack structure is:",
    ["Tailored per client", "Identical every client — only the numbers differ",
     "Set by the tier", "Chosen by the reviewer"], 1,
    "P&L with comparative, balance sheet, supporting schedules, and the cover note."),
  C("The cover note runs to a maximum of:",
    ["One line", "Five lines",
     "One page", "Whatever the month needs"], 1,
    "The month in one sentence, the two flux stories that matter, and anything awaiting the client.")],
},
"m4": {
 0: [
  C("A request for a benchmark range drawn from another client is refused because:",
    ["It is commercially sensitive", "The range is that client's data wearing a disguise",
     "It may be inaccurate", "It requires consent"], 1,
    "Answer from public knowledge only, then turn to the asking client's own figures."),
  C("The shape of a good refusal is to:",
    ["State the rule and stop", "Give something useful and general, so the no does not feel like a wall",
     "Refer it upward", "Explain the policy"], 1,
    "The refusal still leaves the client with something."),
  C("A client contact asking for their own P&L over WhatsApp is refused because:",
    ["The document is not theirs", "The document is theirs and the channel is the breach",
     "It needs approval", "It is not ready"], 1,
    "It goes to their Documents instead — same document, correct route.")],
 1: [
  C("The client register is warm, plain, unhurried, never defensive, and:",
    ["Formal", "Help-shaped rather than accusation-shaped",
     "Brief", "Technical"], 1,
    "To your clients you are the firm, and every message teaches them what the service is like."),
  C("The good version of the unexplained-transaction message names the specifics and:",
    ["Sets a deadline", "Shows the payoff of answering",
     "Cites the policy", "Copies the manager"], 1,
    "Once we know what it was for, July is fully posted."),
  C("'As usual we still don't have your statement' fails because it is:",
    ["Inaccurate", "Accusation-shaped",
     "Too brief", "Sent to the wrong person"], 1,
    "The rewrite names what is needed and what it unlocks instead.")],
 2: [
  C("The bad-news protocol requires the message to go:",
    ["Once the outcome is certain", "Before the system's own surfaces tell them first",
     "With the pack", "After the deadline passes"], 1,
    "Early, plainly, cause attached, path forward — identical for all three cases."),
  C("The late-statement message states the cause, the chases already made, and:",
    ["An apology", "What would still make the deadline",
     "The contract terms", "The new date only"], 1,
    "If the pages arrive today we may still make Friday."),
  C("Saying everything else is closed and reviewed matters because it:",
    ["Deflects blame", "Locates the delay precisely rather than leaving the whole close in doubt",
     "Is required", "Shortens the message"], 1,
    "One missing item is a different message from a general lateness.")],
 3: [
  C("A preparer who surfaces their own doubts is:",
    ["Seen as uncertain", "Trusted more",
     "Slowing the review", "Doing the reviewer's job"], 1,
    "A reviewer who finds an unflagged known issue trusts everything less, permanently."),
  C("The submission notes name the checklist state, the flux notes, and:",
    ["The time taken", "The two things for the reviewer's eye",
     "The client's approval", "The fee"], 1,
    "Review-ready state plus flagged doubts is the craft."),
  C("An unflagged known issue found by a reviewer damages trust:",
    ["For that close", "Permanently",
     "Until corrected", "Only if material"], 1,
    "Which is why burying a doubt costs more than raising it.")],
 4: [
  C("A degrading on-time rate should first be cross-referenced against:",
    ["Client complaints", "Capacity",
     "The review queue", "Seasonality"], 1,
    "The row went from three clients to five in month four, which is the story rather than declining skill."),
  C("The honest conclusion from the sample read is:",
    ["To work longer hours", "A load conversation with the books manager, armed with the numbers",
     "To reduce quality checks", "To request training"], 1,
    "The board wrote the case; that is what it is for."),
  C("Professionals read their own numbers:",
    ["Defensively", "The way they read a client's — honestly, hunting the story",
     "Only at review time", "Through their manager"], 1,
    "Which is what makes the board useful rather than threatening.")],
},
"face": {
 0: [
  C("You see the Books face only if you are a books manager, a System Manager, or:",
    ["A consultant", "A bookkeeper assigned to at least one accounting client",
     "An accountant", "A room member"], 1,
    "If you believe you should see it and do not, your name is not set as any client's bookkeeper — a one-click fix, not a bug."),
  C("Bookkeepers land on My round; managers land on:",
    ["Register", "Matrix",
     "Follow-ups", "KPIs"], 1,
    "The tab strip is the same, but the last three tabs are manager-gated."),
  C("Not seeing Profitability, Billing and KPIs means:",
    ["Something is broken", "They are gated",
     "The period is closed", "Permissions need refreshing"], 1,
    "They are manager-gated by design, so their absence says nothing about your own setup.")],
 1: [
  C("The monthly fee appears in the client column for:",
    ["Everybody", "Managers only, deliberately",
     "Bookkeepers only", "Nobody"], 1,
    "Bookkeepers do not see the fee, which is a design decision rather than an oversight."),
  C("A grey 'no attestation' posting chip means:",
    ["The books are behind", "The round has never been run for that client",
     "The client is new", "The bookkeeper is on leave"], 1,
    "Distinct from green, amber and red, which all describe a lag that exists."),
  C("A green posting chip means a lag of:",
    ["Zero", "One working day or less",
     "Up to three working days", "Any lag inside the period"], 1,
    "Green is one working day or less, amber runs to three, and red is anything beyond that.")],
 2: [
  C("The posted-through date means every transaction dated up to and including it is:",
    ["Reviewed", "In the client's ledger",
     "Reconciled", "Attested"], 1,
    "The picker physically stops at today, so a future claim cannot be made."),
  C("A filled circle on a round card means:",
    ["Today's entry is saved", "A Work Session tagged to that customer exists today",
     "The client is up to date", "A query is open"], 1,
    "The green tick is what appears once today's entry is saved."),
  C("'No accounting clients assigned to you' means:",
    ["The period is closed", "Client setup has not named you",
     "Your role is wrong", "There is no work today"], 1,
    "Fixed in the Matrix's Client setup dialog rather than by support.")],
 3: [
  C("A half-filled circle on the Register means:",
    ["Attested but not worked", "Worked but not attested",
     "Neither", "Both, on a non-working day"], 1,
    "You did the job and skipped the ritual — today's entry can still be saved today."),
  C("An attested-but-no-session mark is:",
    ["Always wrong", "Occasionally legitimate, and as a pattern invites the obvious question",
     "The normal state", "Impossible"], 1,
    "A claim with no visible presence behind it."),
  C("The neglect rule turns a whole row red after how many consecutive silent working days?",
    ["One", "Two or more",
     "Three or more", "Five"], 1,
    "No session and no attestation, and the streak is shown.")],
 4: [
  C("Saving a new question does two things at once: an amber card on the client's portal home, and:",
    ["A task for the reviewer", "An email from the books mailbox",
     "A ledger entry", "A room message"], 1,
    "The client can answer either way, and a reply to the email is captured with the quoted chain trimmed."),
  C("The reference field on a new question should hold:",
    ["Your summary", "The statement narration",
     "The invoice number", "The client's name"], 1,
    "So the client is looking at the same line you are."),
  C("The client filter on Follow-ups is worth narrowing:",
    ["Never", "When working one client",
     "Only for managers", "At month end"], 1,
    "The tab holds three lists across every client by default.")],
 5: [
  C("The onboarding runbook is spawned when:",
    ["The first fee is invoiced", "The customer is marked On Board and the sync creates their room",
     "The kickoff call happens", "A bookkeeper is assigned"], 1,
    "The steps come from the configured template, or the nine-step default."),
  C("Ticking an onboarding step stamps:",
    ["The date only", "Your name",
     "The client's approval", "The manager's sign-off"], 1,
    "Which is why a step is ticked when it is actually done rather than in advance."),
  C("Bank read-only access obtained is recorded in:",
    ["The playbook only", "The Access Register",
     "The client room", "The onboarding note"], 1,
    "One of the nine default steps, alongside ERP roles and opening balances.")],
 6: [
  C("The effective hourly rate divides the monthly fee by:",
    ["Total hours worked", "Hours of customer-tagged Work Sessions that month",
     "Deliverables completed", "Working days"], 1,
    "Which is why tagging sessions to the customer is what makes the number exist at all."),
  C("A client with a fee but no tagged hours shows a dash, which is:",
    ["An error", "Unmeasurable — which is its own finding",
     "A zero rate", "Excluded"], 1,
    "Sorted worst-first, with rates below the configured floor in red."),
  C("These manager tabs are taught to bookkeepers because:",
    ["They may need to cover", "Every number on them is built from what bookkeepers record",
     "Policy requires it", "The gating may change"], 1,
    "And some will hold the manager view sooner than they think.")],
 7: [
  C("The monthly billing run drafts invoices on the 28th regardless of delivery status because:",
    ["It is a technical limitation", "The fee is for the service month, and delivery timing is a separate conversation",
     "Clients expect it", "Drafts are harmless"], 1,
    "Deliberate policy rather than an oversight."),
  C("The drafts are:",
    ["Sent automatically", "Reviewed and submitted by a human",
     "Submitted on payment", "Approved by the client"], 1,
    "Nothing is ever sent to a client unreviewed."),
  C("A client showing 'no fee set' was:",
    ["Invoiced at zero", "Silently skipped",
     "Flagged to the manager", "Billed at the default"], 1,
    "Which is the first thing to fix on the tab.")],
 8: [
  C("The single number that summarises the practice is:",
    ["On-time rate", "The FS close cycle",
     "Posting lag", "Deliverables done"], 1,
    "How many days after month-end the financial statements actually went out, against a promise of five working days or fewer."),
  C("The on-time rate is green at:",
    ["100%", "90% or above",
     "70% or above", "80% or above"], 1,
    "Green at 90% or above, amber from 70, and red below — measured as delivered on or before due."),
  C("Every KPI on the tab is computed from:",
    ["Manager estimates", "Cells moved and attestations saved",
     "Client feedback", "The billing run"], 1,
    "Which is why the daily rituals are what the unit's memory is made of.")],
},
"m1": {
 0: [
  C("The firm keeps books only for businesses running on CloudERP.One because:",
    ["Other platforms are unsupported", "One platform means the skills built on client one apply exactly to client forty",
     "Licensing requires it", "Clients prefer it"], 1,
    "The firm sells depth rather than adaptability."),
  C("A client exists for the firm the moment:",
    ["The contract is signed", "Customer.accounting_services is set to On Board",
     "The first fee is paid", "The room is created"], 1,
    "From that flag the system builds their room, cadence and onboarding runbook overnight."),
  C("There is no off-boarding state in the system because:",
    ["It was overlooked", "Engagements are built to last",
     "Clients rarely leave", "It is handled manually"], 1,
    "A deliberate design decision rather than a gap.")],
 1: [
  C("Every deliverable's due date is:",
    ["Remembered by the bookkeeper", "Computed against the working calendar",
     "Set at onboarding", "Agreed per client"], 1,
    "Working days come from Duty Settings, Monday to Friday unless changed."),
  C("When a fixed statutory day falls on a Saturday, the due date snaps:",
    ["Forward to Monday", "Backward to Friday",
    "To the next working day", "To the month end"], 1,
    "Statutory deadlines are met early; a weekend is never an excuse for lateness."),
  C("Financial statements are due on the:",
    ["Last working day of the period", "5th working day of the next month",
     "3rd working day of the next month", "10th of the next month"], 1,
    "The bank reconciliation is due on the 3rd working day, two days ahead of it.")],
 2: [
  C("A red cell anywhere on the Matrix means:",
    ["In progress", "Past due",
     "Awaiting review", "Not in tier"], 1,
    "The eye means it is sitting with a reviewer and the double tick means the client has acknowledged receipt."),
  C("A dash in a client's PAYE column means:",
    ["Nothing due this period", "PAYE is not in that client's tier",
     "It is overdue", "It was delivered early"], 1,
    "If that client asks about PAYE, it is the tier conversation from lesson 1."),
  C("An amber posting chip showing a lag of two working days means the books:",
    ["Are past due", "Trail reality by two working days, inside tolerance",
     "Have not been started", "Are awaiting review"], 1,
    "Worth closing today rather than an escalation.")],
 3: [
  C("The daily attestation is a signed claim that:",
    ["The work is finished", "The books are posted through a stated date",
     "No queries remain", "The client is satisfied"], 1,
    "With optional transaction and query counts and a note."),
  C("The order to work the board in is:",
    ["Easiest first, for momentum", "Worst first",
     "By client size", "By fee value"], 1,
    "The board is a triage list rather than a menu."),
  C("The goal state at the end of a covered day is that:",
    ["The digest shows all green", "Nobody thinks about you",
     "Every query is closed", "The manager is informed"], 1,
    "The 18:00 digest showing all clients covered is what produces it.")],
 4: [
  C("A query's question should be shaped as:",
    ["You did not tell us", "Help us understand",
     "A formal request", "An instruction"], 1,
    "The shape of the question is what determines the tone of the whole exchange."),
  C("A client replying to the query email rather than using the portal card:",
    ["Does not count as an answer", "Is answering — the system trims the chain and files the reply, attributed",
     "Creates a duplicate", "Must be re-entered by the bookkeeper"], 1,
    "The reply files itself as the answer, attributed, exactly as the portal card would."),
  C("An unclassifiable transaction is posted to suspense and the query raised:",
    ["Once the answer is known", "The same day",
     "At month end", "When it recurs"], 1,
    "The bank ledger stays current, which is what the attestation claims.")],
 5: [
  C("On a split client, the seventh checklist item — reviewer pass complete — is:",
    ["Ticked by the preparer when confident", "Not the preparer's to tick",
     "Optional", "Ticked by the client"], 1,
    "Six of seven belong to the preparer; the last belongs to the reviewer."),
  C("Flagging your own doubt in the review notes:",
    ["Undermines confidence in the work", "Is what makes reviewers trust everything else",
     "Delays the close", "Should be avoided"], 1,
    "Surfacing the one thing you are unsure of is the point of the notes."),
  C("Before the financial statements cell is opened, suspense must be:",
    ["Explained", "Zero",
     "Under a threshold", "Reviewed"], 1,
    "Along with postings complete and the reconciliation done and filed.")],
 6: [
  C("Ticking a checklist item without verifying it is:",
    ["An acceptable shortcut when pressed", "Signing without reading",
     "Covered by the reviewer", "A minor process breach"], 1,
    "A checklist tick is a small signed statement about what was verified."),
  C("The accruals and prepayments tick asserts that prior accruals were:",
    ["Carried forward", "Reversed against actuals",
     "Left in place", "Written off"], 1,
    "Along with recurring accruals raised and prepayment releases run per schedule — not 'probably'."),
  C("The P&L flux tick asserts that every material movement has:",
    ["Been noticed", "A one-sentence written explanation",
     "Been approved", "Been recalculated"], 1,
    "Written down rather than held in the preparer's head.")],
 7: [
  C("The playbook is described as your duty to:",
    ["The client", "Colleagues",
     "The reviewer", "The auditor"], 1,
    "It is what lets somebody else cover your client without discovering everything the hard way."),
  C("Credentials belong:",
    ["In the playbook", "In the access vault, never in chat",
     "With the reviewer", "In the client room"], 1,
    "The access notes record where access lives and when it renews, not the credentials themselves."),
  C("Where a client contact prefers WhatsApp, the playbook records that and adds:",
    ["Use it for everything", "Decisions go in the room",
     "Avoid WhatsApp entirely", "Copy the manager"], 1,
    "Convenience for routine contact does not extend to decisions, which need a record.")],
},
"m2a": {
 0: [
  C("The first question that decides which document a bank line becomes is:",
    ["Is it a debit or a credit", "Is there a party whose ledger this must touch",
     "How large is it", "Is it recurring"], 1,
    "Party payments become Payment Entries; everything else is a Journal Entry or an internal transfer."),
  C("A movement between the client's own accounts is:",
    ["A Journal Entry", "A Payment Entry — Internal Transfer",
     "Two Payment Entries", "A bank reconciliation adjustment"], 1,
    "Two bank ledgers move and the P&L is untouched."),
  C("An unrecognisable line becomes:",
    ["A best-guess expense", "A Journal Entry to suspense, plus a query today",
     "An on-account payment", "A reconciliation item"], 1,
    "The posting keeps the bank ledger current while the question is answered.")],
 1: [
  C("A NIBSS/POS settlement line represents:",
    ["A customer transfer", "The previous day's card sales, net of commission",
     "A bank charge", "A cash deposit"], 1,
    "It clears the POS clearing account, with the commission going to bank charges."),
  C("Stamp duty on a qualifying credit is:",
    ["₦5", "₦50",
     "₦500", "A percentage"], 1,
    "The EMTL, and it appears many times across a month."),
  C("A cheque line's number goes in:",
    ["The remarks", "Reference No",
     "The party field", "The narration"], 1,
    "Which is what the reconciliation matches on.")],
 2: [
  C("On a Payment Entry (Receive), allocation is complete when:",
    ["Every invoice is touched", "Allocated equals Paid",
     "The oldest invoice clears", "The party balance is nil"], 1,
    "The references table loads the party's outstanding invoices on selection."),
  C("A payment arriving referenced to a specific invoice is allocated:",
    ["Oldest first", "To that invoice exactly",
     "Pro rata", "On account"], 1,
    "Even where an older invoice is outstanding — the customer has said what they are paying."),
  C("The Account Paid To on a receive entry is:",
    ["Any bank account", "The ERP bank account mapped to the real one",
     "A clearing account", "Cash in hand"], 1,
    "The playbook lists the mapping between the real account and the ERP one.")],
 3: [
  C("A supplier payment arrives with no purchase invoice in the system. You should:",
    ["Create the invoice from the payment", "Stop — it is a missing-document problem, not a posting problem",
     "Post it to an expense guess", "Hold the payment unposted"], 1,
    "A missing document and a posting difficulty are different problems, and conflating them is how ledgers start to lie."),
  C("The correct sequence for the missing-invoice case is a document request, then:",
    ["Post to suspense", "Post the payment on-account to the supplier",
     "Wait for the invoice", "Post to the expense"], 1,
    "Then allocate the on-account payment once the invoice arrives and is entered."),
  C("Fabricating a purchase invoice to allocate against creates:",
    ["A tidy ledger", "A ledger that lies",
     "A reconciling item", "An audit note"], 1,
    "As does dumping the payment to an expense guess.")],
 4: [
  C("A statutory payment out, such as VAT to FIRS, is posted:",
    ["To an expense account", "Against its control account",
     "To suspense", "As a payment entry"], 1,
    "Dr VAT Payable, Cr bank — the control clears rather than an expense being recognised."),
  C("If the control did not hold the amount being remitted the moment before payment:",
    ["Plug the difference", "Something upstream is wrong — it is a controls investigation",
     "Post the excess to expense", "Adjust the remittance"], 1,
    "That belongs to the month-end controls work rather than to a plug."),
  C("Bank charges should be posted:",
    ["At month end in one journal", "On sight",
     "When reconciling", "Once they exceed a threshold"], 1,
    "The charges family is posted the moment it is met, never hoarded.")],
 5: [
  C("In the worked month, daily sales reach the ledger:",
    ["At settlement", "When the Z-reports are posted, on the day they happened",
     "At month end", "With the bank statement"], 1,
    "Settlement then clears the POS clearing account the following morning."),
  C("A transfer in from the owner personally is watched in both directions because:",
    ["It is unusual", "The owner pays suppliers personally and reimburses himself",
     "It is untaxed", "It affects equity"], 1,
    "A playbook note about that client's month peculiarities."),
  C("The twelve lines are worked using:",
    ["A single document type", "Everything covered so far",
     "Only journal entries", "The bank import tool"], 1,
    "Payment entries, internal transfers, journals, suspense and the clearing patterns together.")],
 6: [
  C("Suspense without a query is described as:",
    ["A holding position", "Procrastination with an account code",
     "Acceptable briefly", "A reconciliation item"], 1,
    "The pairing of the posting and the query is what makes it honest."),
  C("Chasing a stale query is:",
    ["Your memory's job", "The system's — one gentle room reminder per day",
     "Done weekly", "The client's responsibility"], 1,
    "Persistence is automated rather than remembered."),
  C("Suspense must clear to zero:",
    ["By year end", "Before statements",
     "Within a quarter", "When the query resolves"], 1,
    "One of the three iron rules governing the account.")],
 7: [
  C("A POS clearing balance older than about two settlement days means:",
    ["Normal timing", "A missing Z-report, a failed settlement, or an undocumented fee",
     "A bank error", "A reconciliation difference"], 1,
    "The clearing account is a timing device with a built-in alarm."),
  C("On the sales day, the Z-report posts:",
    ["Dr bank, Cr sales", "Dr POS clearing and cash-in-till, Cr sales and VAT output",
     "Dr POS clearing, Cr bank", "Nothing until settlement"], 1,
    "The day's revenue is recognised on the day it happened."),
  C("The settlement morning entry debits the bank and bank charges, and credits:",
    ["Sales", "POS clearing",
     "Cash in till", "VAT output"], 1,
    "Which zeroes the clearing account for that day.")],
},
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

    for mod_key, chapters in CHECKS.items():
        if mod_key not in data:
            sys.exit("ABORT: module %r not in %s" % (mod_key, DATA))
        flat = [c for _i, ch in sorted(chapters.items()) for c in ch]
        rebalance(flat, "bkpr:%s:checks" % mod_key)

    added = skipped = 0
    problems = []
    for mod_key, chapters in CHECKS.items():
        lessons = data[mod_key]["lessons"]
        missing = [i + 1 for i in range(len(lessons)) if i not in chapters]
        if missing:
            problems.append("%s: no checks for chapter(s) %s" % (mod_key, missing))
        bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip()
                for q in data[mod_key].get("questions") or []}
        seen = set()
        for idx, checks in sorted(chapters.items()):
            if idx >= len(lessons):
                sys.exit("ABORT: %s has no chapter %d" % (mod_key, idx + 1))
            if len(checks) != 3:
                problems.append("%s ch%d has %d checks" % (mod_key, idx + 1, len(checks)))
            for c in checks:
                norm = re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip()
                if norm in bank:
                    problems.append("duplicates exam question: %s" % c["q"][:56])
                if norm in seen:
                    problems.append("duplicate check: %s" % c["q"][:56])
                seen.add(norm)
                if len(c.get("why") or "") < 40:
                    problems.append("weak rationale: %s" % c["q"][:50])
                if len(c["opts"]) != 4:
                    problems.append("not 4 options: %s" % c["q"][:50])
            l = lessons[idx]
            if l.get("checks") and not FORCE:
                skipped += 1
                continue
            if not CHECK_ONLY:
                l["checks"] = [dict(c, sort=i) for i, c in enumerate(checks)]
            added += len(checks)

    if problems:
        print("ABORT — %d problem(s):" % len(problems))
        for p in problems:
            print("   %s" % p)
        sys.exit(1)

    print("checks to add: %d | chapters already done: %d" % (added, skipped))
    if CHECK_ONLY:
        print("--check given; nothing written.")
        return

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    chs = sum(len(m["lessons"]) for m in data.values())
    done = sum(1 for m in data.values() for l in m["lessons"] if l.get("checks"))
    tot = sum(len(l.get("checks") or []) for m in data.values() for l in m["lessons"])
    print("track now: %d of %d chapters have checks, %d checks total" % (done, chs, tot))
    sp = collections.Counter(c["ans"] for m in data.values()
                             for l in m["lessons"] for c in (l.get("checks") or []))
    print("answer spread:", dict(sorted(sp.items())))


if __name__ == "__main__":
    main()
