#!/usr/bin/env python3
"""Add check questions to the ZhiftERP Accounts track.

Same repair as the ZhiftPOS track: the content is written, product-accurate and
carries detail nobody could infer from a manual, and it has no check questions
at all — 0 across 73 chapters, which fails the estate standard in every module.

The seeders for this family create modules, lessons and questions but not
checks, because there were none when they were written. That is fine and needs
no change: academy_repair.push_lesson_checks already covers accounts_pro by
name and matches by position within a lesson, so checks added here reach the
site through the tool that already exists.

Checks are derived strictly from what each chapter states. Where a chapter is
silent, the check tests the reasoning rather than inventing product behaviour.
Written scenario-first so they do not duplicate the 280-question exam bank —
the guard below refuses the whole run if any do.

Idempotent, with --force to refresh a chapter that already has checks.

Run from the app package directory:  python3 add_accounts_checks.py
"""

import collections
import io
import json
import os
import random
import re
import sys

DATA = "academy_accounts_pro_data.json"
CHECK_ONLY = "--check" in sys.argv
FORCE = "--force" in sys.argv

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}


CHECKS = {
"journal_entries": {
 0: [
  C("The Journal Entry writes bare GL rows, which means every naira it posts has skipped:",
    ["The approval workflow", "The party tie, the stock agreement, the tax registers and the payment allocation",
     "The audit trail", "The posting date validation"], 1,
    "That is not a flaw — it is specialised for events the trading documents cannot express."),
  C("The Sales Invoice maintains the party ledger, feeds the tax registers and ages into the AR report. A Journal Entry replacing it carries:",
    ["The same machinery", "None of it",
     "The party ledger only", "The tax register only"], 1,
    "Which is why the totals it produces are no longer decomposable."),
  C("The Journal Entry exists in ZhiftERP because:",
    ["Some businesses prefer manual books", "Real accounting needs it monthly",
     "Migrations require it", "Auditors ask for it"], 1,
    "Accruals, payroll and depreciation are legitimate monthly traffic no trading document expresses.")],
 1: [
  C("Your monthly review filters Journal Entries by type. A bank movement saved under the wrong type will therefore:",
    ["Post incorrectly", "Never appear in the review",
     "Be rejected on submit", "Require a second approval"], 1,
    "Entry Type does machinery work and review work, so choose it correctly every time."),
  C("A March accrual should carry a posting date in:",
    ["The month it is entered", "March",
     "The month it reverses", "The current open period"], 1,
    "Honest dates always — the entry speaks for the month it belongs to."),
  C("Accrual reversals are dated:",
    ["The last day of the same month", "The 1st of the following month",
     "The date the actual arrives", "Period end"], 1,
    "Which is what makes the estimate-reverse-actual rhythm land clean.")],
 2: [
  C("Which is the largest lawful category of Journal Entry traffic?",
    ["Payroll", "Accruals and prepayments",
     "Depreciation", "Corrections"], 1,
    "Monthly by nature: expenses spread to the months that consumed them, income deferred to the months that earned it."),
  C("Where the payroll module posts the salary journal automatically you should still:",
    ["Re-enter it manually", "Read the generated entry against the posting map once",
     "Reverse and repost it", "Route it for approval"], 1,
    "Debit salary expense by cost centre, credit net pay, credit the statutory custody accounts."),
  C("The lawful uses are named as a list rather than settled case by case because:",
    ["Auditors require a policy", "The discipline only holds if they are named rather than negotiated",
     "The system validates against it", "It speeds up approval"], 1,
    "A list decided in advance is a control; a case-by-case judgement under pressure is not.")],
 3: [
  C("The principle behind accruals in one sentence is that the P&L should state what a month:",
    ["Paid", "Consumed",
     "Invoiced", "Committed"], 1,
    "Payment dates are bank facts; expense dates are consumption facts."),
  C("HealthTrade's ₦2.4m annual rent paid in January first posts to:",
    ["Rent Expense in full", "Prepaid Rent, an asset",
     "An accrual account", "Suspense"], 1,
    "Eleven months of future occupancy is a thing the business owns."),
  C("Without accrual discipline, monthly margins:",
    ["Are understated", "Lurch with payment calendars, and every report reads noise",
     "Are overstated", "Remain accurate but late"], 1,
    "Which is why the consumption journal is automated rather than remembered.")],
 4: [
  C("Even where permissions allow cancelling and amending a posted journal, you should prefer:",
    ["The amendment, as it is cleaner", "The visible correction",
     "A suspense posting", "A period-end adjustment"], 1,
    "An edited past is a ledger that lies about its own history."),
  C("The reverse-and-repost procedure leaves the GL reading:",
    ["Only the corrected figure", "Mistake, mirror, truth — three linked entries",
     "A net adjustment", "The original with a note"], 1,
    "Cross-referenced in their User Remarks so the story is followable."),
  C("Reverse Journal Entry creates:",
    ["A blank entry to complete", "The exact mirror, linked to the original",
     "A draft correction", "A credit note"], 1,
    "The fresh correct entry is then created separately.")],
 5: [
  C("A revenue journal replacing a Sales Invoice breaks the VAT register, collections ageing, and:",
    ["The bank reconciliation", "The customer's document trail — a balance with no invoice to allocate or dispute",
     "The stock ledger", "The cost centre split"], 1,
    "The purchase-side twin breaks input VAT, WHT capture and the supplier ledger the same way."),
  C("With perpetual inventory on, a Journal Entry row against a Stock account is:",
    ["Permitted with approval", "Refused by the form, with an error naming the stock documents to use",
     "Posted with a warning", "Allowed at period end"], 1,
    "A journal there moves the GL while the stock ledger stands still."),
  C("The forbidden journals are forbidden because each one breaks machinery that:",
    ["Is expensive to rebuild", "Cannot report its own breakage",
     "Auditors rely on", "The system depends on"], 1,
    "Which is why the list is learned with what breaks rather than as a rule.")],
 6: [
  C("Create and submit rights on Journal Entry should go to:",
    ["The finance department", "The accountant and one named backstop — two people, not two departments",
     "All supervisors", "Whoever holds the month"], 1,
    "A journal can move any naira anywhere; the day everyone holds the pen, every fence becomes a suggestion."),
  C("Which categories are second-approved regardless of value?",
    ["Accruals and prepayments", "Anything touching control accounts, opening and closing entries, and corrections above materiality",
     "Payroll and depreciation", "Entries by the backstop"], 1,
    "The threshold numbers themselves are the business's own written policy."),
  C("A branch manager needing a correction should:",
    ["Be given journal rights", "Route it through documents and requests",
     "Ask the backstop directly", "Post it for approval"], 1,
    "Warehouse operators, sales staff and branch managers do not hold the pen.")],
 7: [
  C("HealthTrade's accrual rhythm was demonstrated live across March and April, and the accountant then:",
    ["Asked for more training", "Built two more accrual templates unprompted",
     "Reverted to manual entries", "Requested wider permissions"], 1,
    "Seeing the linked reversal work is what made the procedure his rather than imposed."),
  C("The recurring journal set was built in:",
    ["A quarter", "An afternoon",
     "The first month", "A week"], 1,
    "A census of the genuine traffic, then rent, payroll, utilities accrual and depreciation as templates."),
  C("The monthly rent consumption entry was created once and then:",
    ["Copied each month", "Put on Auto Repeat with twelve occurrences and the remark pre-written",
     "Rebuilt from the template", "Posted by the backstop"], 1,
    "Automating it is what stops a monthly discipline depending on somebody remembering.")],
 8: [
  C("Hundreds of Journal Entries monthly with the trading documents unused indicates:",
    ["Poor permissions", "Manual-books fluency that never transferred",
     "A migration problem", "Excessive control"], 1,
    "Migrate the biggest categories to their documents first, and watch the monthly count as the recovery's measure."),
  C("The Difference field on a Journal Entry should be treated as meaning:",
    ["Round it to suspense", "The other side always exists — find it or do not post",
     "An acceptable tolerance", "A rounding adjustment"], 1,
    "Parking the balancing side in suspense is the one-sided instinct that grows the account monthly."),
  C("Control accounts disagreeing with their party reports, patched by journals, is:",
    ["An acceptable reconciliation", "A tie-breaker journal — treating the symptom while the cause continues",
     "Standard month-end practice", "A migration artefact"], 1,
    "The disagreement is information; a journal that hides it removes the signal and keeps the fault.")],
},
"banking": {
 0: [
  C("Internal records can share one fault — the same wrong default poisons the invoice and the register together. The bank statement is different because it is:",
    ["More accurate", "A record the business does not write",
     "Externally audited", "Produced monthly"], 1,
    "It states what money actually moved, when, and where."),
  C("Reconciliation means every statement line matched to a ledger entry, every ledger bank entry matched to a statement line, and:",
    ["The balances agreeing", "The unmatched remainder named and worked",
     "A sign-off recorded", "The difference journalised"], 1,
    "The remainder is the point of the exercise rather than an inconvenience at the end of it."),
  C("A tick that examines nothing is described as:",
    ["An acceptable minimum", "Not reconciliation at all",
     "A first-pass control", "Sufficient for small accounts"], 1,
    "The comparison either happens or the balance is one nobody should rely on.")],
 1: [
  C("Two real bank accounts pooled into one ledger leaf produces:",
    ["A simpler chart", "Two statements that cannot reconcile against one ledger",
     "A consolidation benefit", "A faster close"], 1,
    "Never pool two real accounts, and never split one real account across leaves."),
  C("The linkage that makes the Bank Account record work is:",
    ["The bank name", "The Account field pointed at the ledger leaf",
     "The account number", "Is Company Account"], 1,
    "Without it the record exists and the reconciliation has nothing to compare against."),
  C("Naming a bank leaf 'GTB Current - 0123' rather than 'Bank 1' matters because:",
    ["The bank requires it", "Every report reads plainly for years",
     "It sorts correctly", "It is validated on save"], 1,
    "Bank and account identity in the name, chosen once.")],
 2: [
  C("A bank offers no clean export and somebody proposes typing the statement in. The objection is that it:",
    ["Takes too long", "Re-introduces the typing errors the import exists to avoid",
     "Is not permitted", "Breaks the mapping"], 1,
    "Lines can be entered manually, but push for the export."),
  C("On import, each statement line becomes:",
    ["A Journal Entry", "A Bank Transaction with status Unreconciled",
     "A Payment Entry", "A ledger row"], 1,
    "Which is then matched in the Bank Reconciliation Tool."),
  C("The column mapping in Bank Statement Import is done:",
    ["Every month", "The first time, and remembered",
     "By the bank", "Per statement file"], 1,
    "Date, description, deposit, withdrawal and reference.")],
 3: [
  C("A cheque unpresented at six months is stale. The procedure is to contact the payee and, if lost:",
    ["Wait for it to expire", "Reverse the Payment Entry by the correction rules and reissue properly",
     "Journal it to suspense", "Write it back to income"], 1,
    "Timing items need a written age limit per instrument rather than indefinite patience."),
  C("A transfer in transit beyond a week means:",
    ["Normal banking delay", "Missing — trace it with the bank",
     "A cut-off difference", "A mapping error"], 1,
    "Transfers are measured in days, not months."),
  C("Timing items on the book side appear on the Bank Reconciliation Statement as:",
    ["Errors", "Uncleared items",
     "Unmatched transactions", "Adjustments"], 1,
    "They normally clear the following month, which is why the age limit matters.")],
 4: [
  C("Several drawers posting to one shared Cash account means:",
    ["Simpler reporting", "No variance can be attributed to anyone",
     "Faster reconciliation", "A single custodian"], 1,
    "Each real cash custody gets its own Cash-type leaf, a named holder, a counting schedule and a written purpose."),
  C("Physical cash has stricter rules than bank money because it has:",
    ["Higher volume", "No outside record at all",
     "More handlers", "No documents"], 1,
    "There is no statement to compare a cash balance against."),
  C("The design principle for cash in this market is to keep drawers few, floats small and:",
    ["Counts weekly", "Banking fast",
     "Approvals tight", "Custody rotated"], 1,
    "Nigeria's transfer-heavy payments make minimisation practical.")],
 5: [
  C("A drawer shared by several operators during one session is refused because it:",
    ["Slows the cash-up", "Turns every variance into an argument",
     "Breaches the float rules", "Complicates the count"], 1,
    "One till, one operator, one session — so that any variance belongs to a person who counted it."),
  C("'Roughly ₦180k' recorded at cash-up is:",
    ["An acceptable approximation", "Not a count",
     "Fine if the variance is small", "A supervisor's judgement"], 1,
    "Count the drawer by denomination on a count sheet."),
  C("The cash-up chain runs from the till drawer to the bank statement in:",
    ["Two links", "Four links, each with a number and a named custodian",
     "Three links", "As many links as tills"], 1,
    "Each link produces a number and the numbers must agree.")],
 6: [
  C("The person who assembles a payment run should never be the person who:",
    ["Approves the invoices", "Authorises it at the bank",
     "Reconciles the account", "Records the supplier"], 1,
    "Two people at any size — at eleven staff, the founder releases what the accountant prepares."),
  C("Payments go to the bank details stored in the Supplier record, never to details supplied in:",
    ["A signed letter", "An email or chat message",
     "The purchase order", "The invoice"], 1,
    "A change to those details is a governed master-data event, verified through a known channel to a known person."),
  C("A supplier emails asking for payment of an invoice you cannot find in the system. The run should pay:",
    ["The amount requested", "Nothing — the run pays what the ledger supports",
     "It on account", "Half pending verification"], 1,
    "Which is what makes the separation of prepare and release meaningful.")],
 7: [
  C("HealthTrade's first reconciliation faced eighteen months of history and a remainder of:",
    ["Four items", "34 items, worked by category",
     "Over a hundred items", "Nothing material"], 1,
    "Including a nine-month-old stale cheque for ₦210,000 that was reversed and reissued properly."),
  C("The three banks were given written purposes:",
    ["Current, savings and domiciliary", "Operating, tax reserve and payroll",
     "Head office and two branches", "Receipts, payments and float"], 1,
    "Each with its own Bank Account record and its own reconciliation."),
  C("The first-dig reconciliation is described as facing the whole backlog:",
    ["Monthly", "Once",
     "Quarterly", "At year end"], 1,
    "Import the history through Bank Statement Import and work it, then run the monthly routine.")],
 8: [
  C("An account that reconciles perfectly every month via a balancing journal to a differences account is:",
    ["Well controlled", "Reconciliation by plug",
     "Acceptable if small", "Using the correct procedure"], 1,
    "Forcing agreement converts every real difference — error, fraud, drift — into a booked fiction."),
  C("A GL bank balance nobody would rely on, with decisions made on it anyway, comes from:",
    ["Poor bank service", "The comparison never being performed",
     "Import errors", "Timing differences"], 1,
    "The written maximum unreconciled age is what makes relapse an incident rather than a habit."),
  C("The statement being opened only to check whether one payment landed is a symptom of:",
    ["Efficient working", "The never-reconciled account",
     "Good cash discipline", "A timing problem"], 1,
    "The comparison is monthly or the balance means nothing.")],
},
"ar_ap_chair": {
 0: [
  C("Unlike stock, a receivable has no shelf to count. Its entire existence is:",
    ["The customer's word", "The party's ledger, the documents behind it, and the tie to the control account",
     "The sales order", "The aging report"], 1,
    "Which is why the accounts side owns the record rather than the chase."),
  C("The sales desk chases customers and the purchasing desk pays suppliers. The accounts side owns:",
    ["The collections targets", "That the figures are real, correctly aged, honestly valued and complete",
     "The credit limits", "The payment run"], 1,
    "A division of work rather than a division of interest."),
  C("The four questions to ask of a receivables balance begin with whether every naira is:",
    ["Overdue", "Real — attached to a Party and backed by documents",
     "Collectable", "Correctly aged"], 1,
    "Real, collectable, correctly aged and complete.")],
 1: [
  C("A payment received on account with no invoice references leaves the invoices it should have cleared:",
    ["Marked as paid", "Ageing as overdue, while the customer's net balance looks fine",
     "Unaffected", "Written off"], 1,
    "The aging overstates and collections may chase paid debts."),
  C("A credit note issued and never applied shows the customer:",
    ["A reduced balance", "A debt and a floating credit side by side",
     "Nothing until applied", "An overpayment"], 1,
    "The customer pays the net and disputes the rest."),
  C("Every unmatched item in a party's ledger is:",
    ["A timing difference", "Ambiguity",
     "An error", "A collection issue"], 1,
    "A party's readable story is entries matched, not merely entries recorded.")],
 2: [
  C("Cash received from a customer ahead of any invoice is:",
    ["Income", "A liability — the business owes goods, services or the money back",
     "A negative receivable", "An unallocated payment"], 1,
    "Leaving it as a negative receivable distorts the aging."),
  C("Where a Sales Order exists, a customer advance should be received:",
    ["As an unallocated payment", "Against the Sales Order, so it is recorded as an advance on that order",
     "Into a suspense account", "As a credit note"], 1,
    "The system then posts it to the configured liability treatment rather than letting it float."),
  C("Customer advances crushed into the receivables line produce:",
    ["A simpler statement", "Receivables that shrink when advances arrive, and a figure nobody can decompose",
     "Correct netting", "A faster close"], 1,
    "Customers dispute those statements on sight.")],
 3: [
  C("The size of a doubtful-debt provision should be set by:",
    ["The accountant's judgement", "A written aging matrix built from the business's own collection history",
     "The auditor's expectation", "A fixed percentage of sales"], 1,
    "Percentages per aging bucket, decided in advance rather than by mood."),
  C("While a provision is carried, the debt itself:",
    ["Is removed from the customer's ledger", "Stays on the customer's ledger and collections keeps working it",
     "Is written off", "Stops ageing"], 1,
    "The provision charges the estimated loss now; it does not end the pursuit."),
  C("Provision for Doubtful Debts should be created as a leaf under the receivables group so that it:",
    ["Ages correctly", "Reports against gross receivables",
     "Accepts a party", "Can be journalised"], 1,
    "The reader then sees the gross debt and the estimate side by side.")],
 4: [
  C("The most useful part of Process Statement Of Accounts is the ability to:",
    ["Print PDFs in bulk", "Schedule each customer their statement by email, monthly, automatically",
     "Include aging", "Filter by group"], 1,
    "Set it up once at go-live and the collections reminder then goes out every month without anybody remembering."),
  C("Customers auditing their own statements provides:",
    ["A collections risk", "Free error-checking",
     "A dispute channel", "An audit trail"], 1,
    "The missed payment, the unapplied credit and the invoice never received all come back as queries."),
  C("The customer statement is:",
    ["A summary of the account", "The party ledger, printed",
     "An aging report", "A collections notice"], 1,
    "Which is why it doubles as the chase's standing reminder.")],
 5: [
  C("Opening receivables should be loaded:",
    ["As one balance per customer", "Per customer, per open invoice, with real numbers, dates and due dates",
     "As a single Journal Entry to the control", "By aging bucket"], 1,
    "Three things depend on it: true aging from day one, allocatable future payments, and a tie born intact."),
  C("Loading one opening balance per customer means the Accounts Receivable report ages every balance from:",
    ["Its real invoice date", "Go-live",
     "The statement date", "The due date"], 1,
    "Which makes the aging wrong from the first day and unfixable without redoing the migration."),
  C("Every AR and AP ledger is born in a migration, and how it is loaded decides whether:",
    ["Reporting is fast", "The tie check agrees from day one or never has",
     "Statements can be printed", "Provisions are possible"], 1,
    "Detail, never totals — a migration loaded as balances cannot be repaired later without redoing it.")],
 6: [
  C("The month-end AR/AP routine begins with:",
    ["The unallocated sweep", "The tie check",
     "The advance aging", "The provision review"], 1,
    "Trial Balance controls against the AR and AP report totals, to the kobo — two minutes when it agrees."),
  C("A difference on the tie check should be treated as:",
    ["A rounding matter", "An incident",
     "A month-end adjustment", "A migration artefact"], 1,
    "The Journal Entry filter on the control account finds the cause; never carry it forward unexplained."),
  C("The month should be graded by:",
    ["The size of the receivables balance", "The length of the unallocated list",
     "Days sales outstanding", "The provision level"], 1,
    "Floating payments and unapplied credits are the measure of whether the routine is being kept.")],
 7: [
  C("HealthTrade's first unallocated read found ₦840,000 floating across 23 items, and by month three the read was:",
    ["Unchanged", "Near zero",
     "Higher", "About half"], 1,
    "₦45,000 at month two, after three afternoons in Payment Reconciliation and a standard question put to customers."),
  C("The standard question put to customers about a floating payment was:",
    ["Can you confirm the amount?", "Your payment of March 14th, against which invoices?",
     "Do you dispute this balance?", "Shall we refund it?"], 1,
    "One genuine overpayment was refunded by a proper Payment Entry."),
  C("The ₦60,000 payment no record explained turned out to be:",
    ["A duplicate", "A sister-company transfer mis-referenced",
     "A fraud", "A bank error"], 1,
    "Escalated by name in week one and resolved in week three.")],
 8: [
  C("A control account disagreeing with its party report, with nobody knowing since when, is fixed by:",
    ["A balancing journal", "Finding the causes with the Journal Entry filter and dating the divergence backwards",
     "Reloading the migration", "Writing off the difference"], 1,
    "The monthly check then makes the next divergence a one-month problem rather than a three-year one."),
  C("Reports quoting whichever of the two numbers suits is a symptom of:",
    ["Poor reporting design", "The tie never being checked",
     "A migration problem", "Weak permissions"], 1,
    "Journals to controls, total-per-party migrations and deletions are the usual causes."),
  C("The netting error shows up as receivables that:",
    ["Age incorrectly", "Shrink when advances arrive",
     "Exceed the control", "Cannot be provisioned"], 1,
    "And a balance-sheet figure nobody can decompose.")],
},
"chart_gl": {
 0: [
  C("A posting is wrong and must be corrected. In ZhiftERP the GL Entry itself is:",
    ["Edited to the right figure", "Never edited — corrections are new entries posted beside the old",
     "Cancelled and retyped", "Amended by an administrator"], 1,
    "Which is why the voucher on every row matters: the trail shows both the error and its correction."),
  C("Every GL Entry row carries a posting date, account, amount, party where applicable, cost centre and:",
    ["An approver", "The voucher that created it",
     "A narration", "A reconciliation flag"], 1,
    "The document that wrote the row, which is what makes any figure traceable back to its source."),
  C("In ZhiftERP you do not type ledger entries for trading because:",
    ["Journals are restricted", "The trading documents post their own accounting on submit",
     "The GL is read-only", "Entries require approval"], 1,
    "A Sales Invoice posts revenue, VAT and the customer's debt the moment it is submitted.")],
 1: [
  C("A ₦107,500 sales invoice (₦100,000 plus 7.5% VAT) credits VAT Payable ₦7,500. That ₦7,500 is:",
    ["Income of the business", "Money held for FIRS",
     "A reduction of debtors", "An expense"], 1,
    "Which is why the tax accounts are treated as custody money rather than as revenue."),
  C("The DEAD mnemonic says debits increase Expenses, Assets and Drawings, and that everything else:",
    ["Is unaffected", "Grows by credit",
     "Requires a party", "Is a group account"], 1,
    "Liabilities, income and equity all increase on the credit side."),
  C("You will never see an unbalanced posting in ZhiftERP because:",
    ["Entries are reviewed", "The system enforces that total debits equal total credits",
     "Vouchers are validated", "Journals require approval"], 1,
    "Every document's rows balance by construction, so an unbalanced posting cannot be submitted at all.")],
 2: [
  C("You try to post to a bold row in the Chart of Accounts and it is refused. That row is:",
    ["Disabled", "A group account — a folder for reading, not a leaf that takes postings",
     "Closed for the period", "Restricted by permission"], 1,
    "A group cannot take postings and a leaf cannot have children."),
  C("Converting a group account to a posting account, or the reverse, requires that the account has:",
    ["An approver", "No entries",
     "A number", "A parent"], 1,
    "Which is a reason to get Is Group right at creation."),
  C("An account should be named 'Generator Running Costs' rather than 'Misc Exp 2' because the name:",
    ["Is required to be descriptive", "Will read in every report for years",
    "Determines the account type", "Affects the sort order"], 1,
    "Plain language, chosen once, read by everybody afterwards.")],
 3: [
  C("A real bank account is created without the Bank account type. The consequence is that it:",
    ["Cannot take postings", "Is invisible to the Bank Reconciliation tool that proves it",
     "Rejects payments", "Has no party"], 1,
    "Names are for people; the type is what the machinery reads."),
  C("Receivable and Payable account types force every posting to carry:",
    ["A cost centre", "A Party",
     "A voucher number", "A tax template"], 1,
    "That is what creates the per-party ledgers and the AR and AP reports."),
  C("Journal Entries against Stock-type accounts, with perpetual inventory on, are:",
    ["Allowed with approval", "Blocked by the system",
     "Permitted at period end", "Restricted to administrators"], 1,
    "Stock-type accounts are reserved for the perpetual-inventory postings.")],
 4: [
  C("A Delivery Note posts stock out and cost of goods sold, and posts:",
    ["The revenue as well", "No revenue at all",
     "The tax", "The customer's debt"], 1,
    "Delivery moves value and invoicing books revenue, which is why a period needs both before its margin is true."),
  C("A Purchase Receipt debits Stock In Hand at valuation and credits:",
    ["Creditors", "Stock Received But Not Billed",
     "Cost of Goods Sold", "The bank"], 1,
    "The accrual for goods received and not yet invoiced."),
  C("A Sales Invoice with Update Stock ticked also does the work of:",
    ["The Payment Entry", "The Delivery Note",
     "The Purchase Receipt", "A Journal Entry"], 1,
    "It credits Stock In Hand and debits Cost of Goods Sold in the same posting.")],
 5: [
  C("A manager disputes a figure in a meeting. The habit to have taught them is to:",
    ["Export the report", "Drill down — statement line to account to GL rows to the voucher",
     "Request a reconciliation", "Ask for a journal listing"], 1,
    "A business whose managers drill down argues from documents rather than from recollection."),
  C("To read one document's complete footprint in the General Ledger report, filter by:",
    ["Account", "Voucher No",
     "Party", "Cost Center"], 1,
    "It shows the posting map verified live for that document."),
  C("To answer 'how did this balance get here', the General Ledger filter to use is:",
    ["Party", "Account",
     "Voucher No", "Group By"], 1,
    "One account's full story between two dates, with opening and closing balances.")],
 6: [
  C("The Debtors balance in the Trial Balance equals the sum of the customers' balances because they are:",
    ["Reconciled monthly", "The same GL rows read three ways",
     "Calculated from the same report", "Both derived from invoices"], 1,
    "The control account is the total and the parties are the detail."),
  C("A Journal Entry row posted against Debtors without a Party produces:",
    ["A rejected entry", "Naira in the control that belong to no customer",
     "A duplicate ledger", "An ageing error only"], 1,
    "The AR report's total then no longer equals the control account."),
  C("Which report is the collections worklist?",
    ["The General Ledger filtered by party", "Accounts Receivable, ageing open items into buckets",
     "The Trial Balance", "The Payment Reconciliation tool"], 1,
    "Accounts Payable mirrors it for suppliers.")],
 7: [
  C("HealthTrade wrote down the MD's fifteen monthly questions before touching the tree. Those questions became:",
    ["A reporting request", "The chart's specification",
     "The audit plan", "The close checklist"], 1,
    "Design from the reading, not from the listing."),
  C("The three banks were created as Bank-type leaves named 'GTB Current - 0123' style because:",
    ["Numbering is required", "Three reconciliations were coming, and each account must be identifiable",
     "The bank requires it", "Names must be unique"], 1,
    "Bank and account identity in the name, so the reconciliation in module 3 is unambiguous."),
  C("Walking the Company record's defaults during setup found two wrong. Correcting them then rather than later matters because a default:",
    ["Cannot be changed afterwards", "Silently directs postings until somebody notices",
     "Is used only at year end", "Blocks submission if wrong"], 1,
    "Round Off, Stock Received But Not Billed and the receivable and payable defaults all post without being chosen each time.")],
 8: [
  C("A suspense account with a large, ageing, growing balance is caused by:",
    ["A migration error", "The parking account being used as a destination for everything unclassified",
     "An untyped account", "Missing cost centres"], 1,
    "The fix is sweeping it to zero monthly as a close-checklist line and fixing the source gaps."),
  C("Four hundred accounts in an eleven-person business is chart sprawl, and the branch and line distinctions belong in:",
    ["More group accounts", "Cost Centers",
     "Account numbers", "Separate companies"], 1,
    "Consolidate the balances by documented entries, disable what is unused, and narrow creation rights."),
  C("A bank missing from the reconciliation tool, an invoice refusing a party, and receivables that cannot age share one cause:",
    ["Permission restrictions", "Accounts created with names but without the right Account Type",
     "A closed period", "Missing defaults"], 1,
    "Type at creation as a rule; retyping an account that already has history is a different and harder job.")],
},
}


def rebalance(items, seed):
    """Spread correct answers evenly across A-D.

    The first run of the equivalent ZhiftPOS script put 27 of 27 answers in
    position B. Author bias is consistent and invisible without this.
    """
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
        rebalance(flat, "accounts:%s:checks" % mod_key)

    added = skipped = 0
    problems = []
    for mod_key, chapters in CHECKS.items():
        lessons = data[mod_key]["lessons"]
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
                    problems.append("duplicates exam question: %s" % c["q"][:60])
                if norm in seen:
                    problems.append("duplicate check: %s" % c["q"][:60])
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
