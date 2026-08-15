#!/usr/bin/env python3
"""Deepen the ZhiftERP Accounts track.

Fourteen chapters sit below the 2,500 floor and every one of the eight modules
is under the 2,800 depth target. This is a whole-track pass rather than
fourteen patches.

The rule I have held throughout: nothing here asserts product behaviour the
chapter does not already state. Each addition is a consequence, a practical
habit, or reasoning built on facts the chapter establishes — the kind of thing
the author would have added with more room, not new claims about the software.

Most chapters end with a Summary paragraph, so additions are anchored to insert
BEFORE it. A block appended after the summary reads as an afterthought.

Anchored and idempotent: each addition is keyed to an exact string, and a
chapter already carrying the marker is skipped.

Run from the app package directory:  python3 deepen_accounts.py
"""

import io
import json
import re
import sys

DATA = "academy_accounts_pro_data.json"
MARKER = "<!--deepened-->"
FLOOR = 2500
CHECK_ONLY = "--check" in sys.argv

P = lambda t: MARKER + "<p>" + t + "</p>"

# module -> chapter index -> paragraph(s) appended at the end of the chapter
ADDITIONS = {
"chart_gl": {
 1: P("<b>Where the table earns its keep fastest.</b> Not in posting — the documents do that — "
      "but in reading somebody else's work. An unfamiliar balance, a query from the auditor, a "
      "figure a manager disputes: each becomes tractable the moment you can say which account, "
      "which side, and what grew it. Accountants who have worked only in manual books often know "
      "the rules and have never had to read a ledger they did not write, and that is the skill "
      "this chapter is actually building."),
 5: P("<b>A habit worth forming early.</b> When a report figure surprises you, drill it before "
      "you explain it. The temptation is to reason about what the number probably is; the drill "
      "takes thirty seconds and produces the vouchers. Reasoning that turns out to be wrong is "
      "expensive in front of an owner, and the drill-down exists precisely so that nobody in a "
      "finance conversation has to rely on recollection."),
 2: P("<b>What to do with the chart you inherit.</b> Most implementations arrive at a business "
      "that already has one — from a previous system, a spreadsheet, or an accountant's "
      "preference. Do not rebuild it on principle. Run the reading test against it, keep every "
      "account that answers a question somebody asks, and change only what fails. A chart the "
      "accountant recognises is one they will use; a technically superior chart they did not "
      "ask for is one they will work around."),
 3: P("<b>Retyping an account that already has history.</b> It is possible and it is not a "
      "casual change: the existing entries were posted under the old behaviour, and the "
      "machinery the new type switches on will not retrospectively apply to them. Treat it as a "
      "governed event — check what the account holds, decide whether the history needs moving to "
      "a correctly typed account by documented entries, and record the decision. Typing at "
      "creation avoids the whole question, which is why it is a rule rather than a preference."),
 4: P("<b>Why this map is worth verifying rather than trusting.</b> Configuration differs between "
      "businesses — a different default, an item's own account, a template somebody edited — and "
      "the posting map is only true for the configuration in front of you. Verifying one live "
      "document of each kind at go-live takes an hour and finds the one setting that is wrong "
      "before it has produced a year of postings. It is also the fastest way for a new "
      "accountant to trust the system, because they have watched it post."),
 6: P("<b>The tie check as a monthly habit rather than an investigation.</b> Two minutes, first "
      "thing at close, before anything else is examined: control against party report, to the "
      "kobo. When it agrees, that is the whole exercise. When it does not, the difference is "
      "one month old rather than three years old, which is the difference between a lookup and a "
      "reconstruction — and the reconstruction is what makes businesses give up on the tie "
      "entirely."),
 7: P("<b>What made this afternoon work.</b> The reading list came before the tree. Most chart "
      "setups run the other way — the default chart is installed, accounts are added as "
      "transactions demand them, and the reporting question is asked a year later when nobody "
      "can answer it without surgery. Fifteen questions written down first is an hour that saves "
      "the consolidation sitting described in chapter 9."),
 8: P("<b>The pattern behind all four.</b> Each is a small convenience taken at setup that "
      "becomes expensive at scale: an account created rather than a cost centre, a parking "
      "account rather than a classification, a name rather than a type. None was a mistake "
      "anybody would defend, and none was visible on the day it was made. That is the argument "
      "for the setup disciplines in this module — they cost an afternoon and they are the only "
      "point at which any of this is cheap."),
},
"journal_entries": {
 6: P("<b>What the count actually tells you.</b> Track it monthly and it becomes the clearest "
      "single measure of whether the documents are being used. A business migrating off manual "
      "books starts high and falls; a business whose count is climbing is telling you that "
      "somebody is finding the documents harder than the journal, and that is worth "
      "investigating as a usability problem rather than a discipline one. The number is more "
      "useful as a trend than as a threshold."),
 0: P("<b>How to explain this to an accountant who has always journalised.</b> Not as a "
      "restriction. The trading documents do the journal's work and several other jobs besides — "
      "the party ledger, the stock ledger, the tax register, the allocation. Framing it as what "
      "the document adds rather than what the journal is not allowed to do is the difference "
      "between a competent person adopting the system and a competent person working around it."),
 1: P("<b>The User Remark is not optional in practice.</b> A journal without a story is an entry "
      "nobody can review, and it will be read by somebody in a year with no memory of the "
      "circumstances — an auditor, a successor, or you. Write what happened and why, in a "
      "sentence a stranger could follow. It is the cheapest thing on this form and the one most "
      "often left blank."),
 2: P("<b>What to do with a request that is not on the list.</b> Not refuse it outright — ask "
      "what the underlying event is. A large share of off-list requests turn out to be a "
      "document that should have been raised, a correction that has a proper procedure, or a "
      "process gap upstream. The journal is occasionally the right answer; it is almost never "
      "the right first answer, and the question surfaces the real one."),
 3: P("<b>Where accrual discipline is most often abandoned.</b> Not at the big items, which "
      "everybody remembers, but at the medium recurring ones — the quarterly service contract, "
      "the annual licence, the insurance premium. These are individually small enough to feel "
      "not worth the entry and collectively large enough to move a month. Put them on the "
      "template list once and the judgement stops being made every month."),
 4: P("<b>Correcting a correction.</b> It happens, and the rule does not change: reverse and "
      "restate again, cross-referenced to both prior entries. The chain gets longer and stays "
      "readable, which is the point. What must not happen is somebody deciding the trail has "
      "become embarrassing and tidying it — the tidied version is the one an auditor will ask "
      "about, and the honest chain has never yet been a finding."),
 5: P("<b>Why the fenced ones are fenced and the rest are policy.</b> The system blocks what it "
      "can detect unambiguously — a Stock account is a Stock account. It cannot detect that a "
      "journal to Debtors and Sales is a substitute for an invoice, because that is a legitimate "
      "posting in other circumstances. Where the system cannot tell, the control has to be the "
      "named list and the monthly review, which is why chapter 7 exists at all."),
 7: P("<b>The detail worth noticing in this case.</b> The accountant built two more templates "
      "unprompted, and that is the measure of a procedure landing. A control that is complied "
      "with is installed; a control somebody extends on their own is understood. The difference "
      "came from watching the estimate-reverse-actual cycle work across two real months rather "
      "than being told it would."),
 8: P("<b>The recovery is measured rather than declared.</b> Each of these patterns has a number "
      "attached — the monthly journal count, the suspense balance, the tie difference. Fix the "
      "cause and the number moves; declare the fix and it does not. Pick the number before "
      "starting so that in three months there is something to point at other than an impression "
      "that things are better."),
},
"banking": {
 6: P("<b>The control that costs nothing and is skipped most often.</b> Purging bank mandates "
      "and online users the week somebody leaves. It is nobody's specific job, it is invisible "
      "until it matters, and a leaver with live release rights is the single largest bank "
      "exposure a small business carries. Put it on the leaver checklist beside the system "
      "account and the keys, and check the whole list annually against who actually works here."),
 0: P("<b>A note on what reconciliation proves and does not.</b> It proves that the ledger and "
      "the statement describe the same movements. It does not prove that a movement was "
      "authorised, or that the payee was the right one — a fraudulent payment made through the "
      "proper channel reconciles perfectly. That is why chapter 7's governance sits alongside "
      "this routine rather than being replaced by it."),
 1: P("<b>Closing a bank account properly.</b> When a real account is closed, the ledger leaf is "
      "disabled rather than deleted, the Bank Account record is deactivated, any Mode of Payment "
      "pointing at it is repointed or retired, and the final reconciliation is completed and "
      "filed. Accounts abandoned rather than closed leave a zero balance nobody has proved and a "
      "payment mode that will eventually be selected by accident."),
 2: P("<b>What to do about the month the statement will not import.</b> A changed export format, "
      "a corrupted file, a bank portal that has been redesigned. Do not skip the month — the "
      "gap compounds and the next reconciliation inherits it. Enter the lines as Bank "
      "Transactions manually for that month, note why in the reconciliation file, and fix the "
      "mapping before the next one. A month reconciled awkwardly is worth far more than a month "
      "left."),
 3: P("<b>The category the chapter treats most sternly, and why.</b> Items on the bank side that "
      "the ledger has never seen — a charge nobody booked, a debit nobody recognises, a credit "
      "from an unknown source. These are not timing and they are not errors of yours; each is "
      "either a fee to be booked, a mistake by the bank, or something worse. Age them like the "
      "others and escalate rather than absorbing them, because an unrecognised debit accepted "
      "quietly is the pattern that repeats."),
 4: P("<b>Counting a float that is short.</b> The count is recorded as counted, the difference "
      "is recorded as a difference, and the custodian is spoken to the same day. What must not "
      "happen is the count being adjusted to the expected figure, or the shortfall being made up "
      "personally before the count — both destroy the only evidence the arrangement produces, "
      "and the second is usually done by an honest person trying to avoid trouble."),
 5: P("<b>Where the chain most often breaks.</b> Between the cash-up and the banking — the "
      "counted bag that sits in a drawer overnight, the deposit slip nobody matched to the "
      "session. Each link needs its own custodian and its own number, and the handover between "
      "two links is where a loss becomes unattributable. Time-stamp the handovers where you "
      "can; the sequence is what makes the chain evidence rather than four separate counts."),
 7: P("<b>What made the first dig tolerable.</b> It was faced once, deliberately, as a piece of "
      "work with an end — not attempted alongside the monthly routine and abandoned twice. "
      "Businesses in this position usually know the backlog exists and have started it before; "
      "the difference is scheduling it as a project with the history imported in one pass rather "
      "than trying to catch up a month at a time while new months arrive."),
 8: P("<b>The measure to watch after the repair.</b> Not whether the account reconciles — it "
      "will, for a while — but the age of the oldest unreconciled item, tracked monthly. A "
      "reconciliation that is completed but leaves items ageing indefinitely has become a "
      "different kind of formality, and the age is what shows it while the completion rate looks "
      "perfect."),
},
"ar_ap_chair": {
 0: P("<b>Why this chair is different from collections.</b> A collections conversation is about "
      "one customer and one balance. The accounts chair is about whether the total is true — "
      "which is a different question, answered by the tie, the allocation state, the aging basis "
      "and the provisioning, none of which any individual customer conversation touches. Both "
      "jobs are necessary and confusing them produces a business that chases hard and reports "
      "figures nobody can rely on."),
 1: P("<b>The customer call that clears most of a backlog.</b> The standard question — your "
      "payment of the 14th, against which invoices — is answerable by the customer's own "
      "accounts staff in about a minute, and it is not a chase. Most floating payments clear "
      "this way rather than through investigation, and the call has the useful side effect of "
      "establishing a working contact in their finance team before you need one."),
 2: P("<b>Supplier advances need the same discipline in reverse.</b> A payment made ahead of the "
      "bill is an asset, not a negative payable, and it needs matching to the invoice when it "
      "arrives. These are forgotten more often than customer advances because nobody chases you "
      "for your own money — which is exactly why the advance aging in the month-end routine runs "
      "in both directions."),
 3: P("<b>What the provision is not.</b> Not a way of tidying the aging, and not a decision the "
      "system role makes. The matrix percentages are the accountant's professional judgement, "
      "and the entry follows the matrix rather than the balance somebody would prefer to show. "
      "A provision adjusted to produce a desired receivables figure is an earnings decision "
      "wearing a bookkeeping costume."),
 4: P("<b>Sending statements to a customer who disputes them.</b> Keep sending them. A disputed "
      "statement that arrives monthly is a standing invitation to resolve; a statement withheld "
      "because the relationship is difficult removes the only routine document that states your "
      "position. Where the dispute concerns specific items, send the statement and the item list "
      "separately rather than editing the statement."),
 5: P("<b>The migration decision that cannot be undone cheaply.</b> Loading balances rather than "
      "invoices is quick, and every subsequent month pays for it: the aging is wrong, allocation "
      "is impossible, and the tie was never born. Repairing it later means going back to the old "
      "records and reconstructing the open items anyway — the same work, done under worse "
      "conditions, with a year of transactions layered on top."),
 6: P("<b>Where the ninety minutes actually goes.</b> Almost all of it into the unallocated "
      "sweep in the first months, and almost none of it after the backlog clears. That shape is "
      "worth expecting: a business installing this routine should not judge it by the first "
      "sitting, which is a clean-up, but by the third, which is the routine itself. Sittings "
      "that stay long after three months mean something upstream is generating ambiguity faster "
      "than the sweep clears it."),
 7: P("<b>The escalation that resolved in week three is the instructive part.</b> It was "
      "escalated by name and with a date rather than left on a list, which is why it resolved at "
      "all. Unexplainable items do not become explainable by ageing; they either get a named "
      "owner and a deadline or they sit for years and eventually get written off by somebody who "
      "never knew what they were."),
 8: P("<b>What these three have in common.</b> Each is a broken relationship between a total and "
      "its detail — control against parties, receivable against advance, balance against "
      "documents. The AR and AP layer is entirely a set of totals that must decompose, and every "
      "failure in it is a decomposition that stopped working. That is the frame that makes the "
      "month-end routine's order sensible: the tie first, because it tests the relationship "
      "everything else assumes."),
},
"tax_compliance": {
 0: P("<b>How to teach the custody idea so it holds.</b> Not as a rule about accounts. Say what "
      "the money is: this is the state's money, or the supplier's, or the employee's, and it is "
      "in our bank because we collected it on their behalf. Owners who understand it in those "
      "terms stop asking whether the VAT balance can bridge a gap. Owners taught it as an "
      "accounting classification keep asking, because a classification sounds negotiable and a "
      "custody does not."),
 6: P("<b>Where the reserve discipline usually fails first.</b> Not at the transfer — at the "
      "month somebody decides to skip one transfer because the week is tight. The reserve then "
      "runs a month behind and is never caught up, because the catch-up requires two transfers "
      "in one month, which is harder than the one that was skipped. Treat a missed transfer as "
      "an incident with a written reason, exactly like a missed remittance."),
 1: P("<b>Registration and the practical consequence of getting it wrong.</b> A business trading "
      "above a registration threshold without being registered accumulates an obligation it is "
      "not collecting for, and that liability does not expire quietly. The accountant confirms "
      "the position, and the system role's job is to make sure that once the answer is known, "
      "the configuration matches it — templates, item categories, and the registers that "
      "evidence it — rather than being adjusted informally afterwards."),
 2: P("<b>Why the item audit is worth doing before the first return.</b> Exempt, zero-rated and "
      "standard-rated items behave differently and the difference is carried on the item master, "
      "not on the invoice. A mixed-supply business that has never audited its item tax "
      "categories will produce registers that cannot separate the streams, and every month's "
      "apportionment is then a manual reconstruction. One afternoon on the item masters removes "
      "that permanently."),
 3: P("<b>Chasing certificates is a money job, not an administrative one.</b> An unclaimed "
      "withholding credit is cash the business has already paid and can recover, and it expires "
      "by neglect rather than by rule. Attach the chase to the payment routine — the credit is "
      "requested when the deduction happens, not months later when nobody at the customer "
      "remembers the transaction — and keep the receivable aged like any other."),
 4: P("<b>The payroll register is the evidence, not the payslips.</b> Authorities and auditors "
      "ask for the register: gross, deductions by type, net, split by state and by fund. If the "
      "payroll module produces it, file it monthly with the remittance evidence. If it does not, "
      "produce it before the first remittance rather than at the first query, because "
      "reconstructing eleven months of splits from payslips is a week's work nobody has."),
 5: P("<b>Filing a return you know is wrong.</b> It happens — a figure discovered late, a "
      "register that will not tie before the deadline. File on time with the best number, "
      "document what is known to be wrong and why, and amend by the proper route. Late filing "
      "and wrong filing are different failures with different consequences, and the instinct to "
      "delay until it is perfect converts a correctable error into a penalty."),
 7: P("<b>Who speaks to the authority.</b> One named person, with the accountant, and never an "
      "unprepared conversation on the day an officer arrives. The system role's contribution is "
      "extraction — producing the registers, the ledger movements and the documents requested — "
      "not interpretation of the position, which belongs to the accountant or the tax adviser. "
      "Mixing those two roles in a meeting is how businesses concede points nobody asked them to "
      "concede."),
 8: P("<b>What the note in the file actually recorded.</b> That the return and the ledger had "
      "become the same document — which is the entire objective of this module stated in one "
      "sentence by the person who had been doing it the other way for years. It is worth quoting "
      "to any accountant who regards the bridges as bureaucracy: the bridges are what make that "
      "sentence true."),
 9: P("<b>The penalty line as the module's single measure.</b> If penalties and interest are on "
      "the P&L at all, something in this module is not installed, and the amount tells you how "
      "much. It is a better measure than filing punctuality because it captures the whole "
      "chain — reserve, register, bridge, calendar — in one number that the owner already "
      "understands and did not enjoy paying."),
},
"dimensions": {
 0: P("<b>Why folklore survives so long.</b> Because it is never tested. Nobody in a "
      "multi-branch business sets out to run on assertion; the branch numbers simply were never "
      "produced, so the plausible story filled the gap and hardened. The first honest branch P&L "
      "is frequently uncomfortable for exactly that reason — it contradicts something everybody "
      "has believed for years, including the person who believed it hardest."),
 1: P("<b>The mistake to avoid at design time.</b> Creating a leaf for every place rather than "
      "every accountability. A stockroom, a delivery van and a back office are places; they are "
      "not units whose performance anybody manages. Each unnecessary leaf costs a decision on "
      "every posting for the life of the system, and produces reports nobody reads. Ask who is "
      "answerable for this line's result — if the answer is nobody in particular, it is not a "
      "leaf."),
 3: P("<b>Presenting both views to an owner.</b> Show contribution first and let it be "
      "understood, then show the loaded view as a second page with the allocation basis stated "
      "on it. Owners shown only the loaded view argue about the allocation; owners shown "
      "contribution first argue about the branch, which is the conversation worth having. The "
      "order of presentation does more work here than the arithmetic."),
 2: P("<b>What the validation actually prevents.</b> Not carelessness — the ordinary posting "
      "gets its address from a default and nobody thinks about it. It prevents the unusual "
      "posting from going unaddressed: the one-off journal, the imported batch, the document "
      "somebody created outside the normal flow. Those are precisely the postings that land in "
      "the default cost centre and grow the unaddressed lump, and they are the ones the "
      "validation catches."),
 4: P("<b>Review the basis annually and change it rarely.</b> An allocation basis that changes "
      "every year makes branch results incomparable across time, which destroys the only thing "
      "the loaded view is good for. Pick a defensible basis, write down why, and leave it — and "
      "when it genuinely must change, restate the prior year on the new basis so the comparison "
      "survives."),
 5: P("<b>A budget nobody looks at monthly is a document, not a control.</b> The Budget doctype's "
      "value is the variance read arriving beside the actuals every month, with somebody "
      "answering for the difference. Set the actions on exceeding deliberately — a warning that "
      "everybody clicks through teaches the team that the budget is decorative, and a hard stop "
      "on the wrong account will block legitimate trade at the worst moment."),
 6: P("<b>The discipline about adding a second dimension.</b> Each one adds a field to every "
      "accounting document, which means a decision on every posting forever. Add one when there "
      "is a question the business asks monthly and cannot answer, not because the capability "
      "exists. Two dimensions used properly are worth more than four that people select at "
      "random to get past the validation."),
 7: P("<b>The re-verification is the step most implementations skip.</b> Wiring the defaults is "
      "quick and confirming they actually carry through to the postings is slower, which is why "
      "it gets assumed. One live document of each kind, opened and read, finds the item default "
      "nobody set and the POS profile pointing at the wrong centre — before a quarter of "
      "postings have inherited them."),
 8: P("<b>Both patterns produce the same end state by different routes.</b> A chart full of "
      "per-branch copies and a default cost centre swallowing the P&L are the same failure: the "
      "address was not carried at posting, so it was either invented in the account name or lost "
      "entirely. That is why the wiring chapter comes before the reading chapter — a report "
      "cannot recover an address that was never captured."),
},
"close_statements": {
 5: P("<b>The read that changes an owner's behaviour.</b> Showing a profitable month beside a "
      "falling bank balance, with the balance-sheet movements between them named — this much "
      "went into stock, this much is sitting in unpaid invoices. Owners who have only ever seen "
      "a P&L frequently experience this as the first explanation of something they had "
      "attributed to bad luck or to somebody's dishonesty."),
 4: P("<b>Reading it as at a sealed date matters.</b> A balance sheet drawn on an unlocked "
      "period is a snapshot that can change after it is circulated, and it will — a late "
      "document, a correction, an accrual posted the following week. Draw it after the freeze, "
      "and when somebody asks for a figure before close, say plainly that it is provisional "
      "rather than issuing it as though it were not."),
 0: P("<b>The day-five target and why it is worth having.</b> Not because five is significant, "
      "but because a close with no target date drifts to whenever the last item happens to "
      "arrive, which is usually after the month's decisions have already been taken. A statement "
      "that lands on the twenty-fifth describes a period nobody can act on. Pick a day, publish "
      "it, and treat missing it as information about which line failed."),
 1: P("<b>Owners by name, not by role.</b> A checklist line owned by finance is owned by nobody "
      "when two people are on leave. Each line names a person and, ideally, a backup — and the "
      "person who owns a line is the person who says it is done, rather than the person who "
      "notices it was not. That distinction is what turns a checklist from a record of the close "
      "into the mechanism of it."),
 2: P("<b>Carrying a known cut-off gap knowingly.</b> Sometimes an invoice genuinely cannot be "
      "raised before close. The rule is not to force it — it is to accrue it and note it, so "
      "that the statement is right and the reader knows what is in it. What breaks a period is "
      "not the item that arrived late; it is the item that arrived late and was neither accrued "
      "nor mentioned."),
 3: P("<b>Read the trend before the month.</b> A single month's P&L invites explanation of every "
      "line; six columns invite explanation of the lines that moved, which is a much shorter and "
      "more useful conversation. Set the periodicity to monthly by default and resist the "
      "single-period view — it is the shape in which most people first learn to read a P&L and "
      "the shape that teaches least."),
 6: P("<b>The register that is never verified physically.</b> Depreciation posts monthly whether "
      "or not the asset still exists. A vehicle sold, a generator that failed, a fit-out removed "
      "in a refit — each keeps depreciating quietly until somebody walks the register against "
      "the actual assets. Once a year, with a person who knows what the items are, and the "
      "disposals processed properly rather than written off in a lump."),
 7: P("<b>What the audit costs depends almost entirely on this module.</b> A business whose "
      "months were closed, reconciled and frozen hands over a year that has already been "
      "examined twelve times. A business closing annually hands over twelve months of unexamined "
      "posting and pays for the auditor to find what its own routine would have found for free. "
      "The fee difference is real and it is the argument that persuades owners who find the "
      "close tedious."),
 8: P("<b>The first close is the expensive one.</b> It carries the backlog, it uncovers "
      "everything the previous arrangement left, and it takes far longer than any subsequent "
      "one. Businesses that abandon the close usually abandon it here, having concluded from the "
      "first attempt that it is unaffordable monthly. Say in advance that the first is atypical, "
      "and schedule it as a project rather than as a month-end."),
},
"advanced_accounts": {
 2: P("<b>Separating four authorities in a small business.</b> With three finance people it "
      "cannot be done perfectly, and the answer is not to pretend otherwise. Separate what "
      "matters most — release from record, and configure from everything — accept the remaining "
      "overlaps explicitly, write down which they are, and compensate with detective controls "
      "over exactly those gaps. A documented, compensated overlap is a control position; an "
      "undocumented one is the audit finding."),
 4: P("<b>Run the test before you need it.</b> Nominate somebody, give them the documentation "
      "only, and have them run one month while the incumbent stays silent. Every question they "
      "have to ask is a gap, written down and closed. It costs a month of mild inefficiency and "
      "it is the only honest version of the test — a handover pack that has never been used by "
      "anybody but its author is a document, not a handover."),
 6: P("<b>Where the boundary is hardest to hold.</b> The client asks a policy question in "
      "passing, casually, expecting an answer — what rate should we depreciate this at, should "
      "we provide against this debt. The answer that keeps the boundary is to say what the "
      "system can do and route the choice to the accountant, in the same sentence, without "
      "making it sound like a refusal. Managed well it takes ten seconds; avoided, it becomes a "
      "position you are answerable for."),
 0: P("<b>Recording the answers is the point of the walk.</b> A setting configured without a "
      "recorded reason gets changed by the next person who finds it inconvenient, and nobody can "
      "say whether the original value was a decision or a default. One line per field — what it "
      "is set to and why — turns the settings page into a policy document and makes the annual "
      "re-walk a review rather than a rediscovery."),
 1: P("<b>Several companies on one site, and the mistake to avoid.</b> Each legal entity keeps "
      "its own chart, cost centres, defaults and fiscal years, and intercompany balances must "
      "agree at both ends. The mistake is treating a second company as a reporting convenience — "
      "a branch that is not a legal entity belongs in the cost centre tree, not in its own "
      "company, and unpicking that afterwards is a migration rather than a change."),
 3: P("<b>The daily lines are the ones that keep the rest cheap.</b> References captured at "
      "entry, cost centres cascading, exceptions cleared the same day — none of it feels like "
      "finance work, and all of it is what makes the monthly routine take ninety minutes instead "
      "of three days. When a close starts overrunning, the cause is nearly always upstream in "
      "the daily habits rather than in the close itself."),
 5: P("<b>Where a control map is most useful.</b> Not as documentation — as the answer when "
      "somebody proposes removing a control because it is inconvenient. Showing that a "
      "preventive control has a detective partner, and what would be uncovered if the "
      "preventive one went, turns a request into an informed trade. Occasionally the trade is "
      "worth making, and the map is how you can tell."),
 7: P("<b>Four quarters is the honest pace.</b> The structural layer cannot be installed in a "
      "week because most of it requires decisions from people who are busy — the settings walk "
      "with the accountant, the authorities with the owner, the calendar with everybody. "
      "Implementations that try to do it at go-live either skip it or make the decisions on the "
      "client's behalf, and both produce a structure nobody in the business owns."),
 8: P("<b>The eight laws are worth reading together once.</b> Each was stated in the module that "
      "earned it, and the set is short enough to hold in mind: the chart reads, the journal is "
      "specialised, the bank is proved, the totals decompose, the custody is not ours, every "
      "naira has an address, the month is sealed, and the authorities are separate. A finance "
      "function that holds those eight is well ahead of most, whatever else it has not yet "
      "installed."),
},
}


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    touched = 0
    report = []
    for mod_key, chapters in ADDITIONS.items():
        if mod_key not in data:
            sys.exit("ABORT: module %r not present" % mod_key)
        lessons = data[mod_key]["lessons"]
        for idx, para in sorted(chapters.items()):
            if idx >= len(lessons):
                sys.exit("ABORT: %s has no chapter %d" % (mod_key, idx + 1))
            l = lessons[idx]
            if MARKER in l["html"]:
                report.append("  %-18s ch%-2d already deepened" % (mod_key, idx + 1))
                continue
            before = len(re.sub(r"<[^>]+>", " ", l["html"]))
            after = before + len(re.sub(r"<[^>]+>", " ", para))
            flag = "" if after >= FLOOR else "  STILL THIN"
            report.append("  %-18s ch%-2d %5d -> %5d%s" % (mod_key, idx + 1, before, after, flag))
            if not CHECK_ONLY:
                # insert before the closing Summary paragraph where one exists,
                # so the addition reads as part of the chapter rather than after it
                m = re.search(r"<p><b>Summary\.", l["html"])
                if m:
                    l["html"] = l["html"][:m.start()] + para + l["html"][m.start():]
                else:
                    l["html"] = l["html"].rstrip() + "\n" + para
            touched += 1

    print("\n".join(report))
    print("\nchapters extended: %d" % touched)
    if CHECK_ONLY:
        print("--check given; nothing written.")
        return

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    thin = [(k, i + 1, n) for k, m in data.items()
            for i, l in enumerate(m["lessons"])
            for n in [len(re.sub(r"<[^>]+>", " ", l["html"]))] if n < FLOOR]
    print("still below the %d floor: %s" % (FLOOR, thin or "NONE"))
    for k, m in data.items():
        lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in m["lessons"]]
        print("   %-18s mean %d" % (k, sum(lens) / len(lens)))


if __name__ == "__main__":
    main()
