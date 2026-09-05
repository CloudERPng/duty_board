#!/usr/bin/env python3
"""Bring 'Understanding Your Monthly Reports' up to the estate standard.

The weakest thing in the estate and the only one a paying client opens without
a consultant beside them: 5 chapters at a 1,472 mean against a 2,500 floor, no
checks at all, and 15 exam questions where every other module carries 35 or
more.

The existing content is good — that is worth saying, because the temptation
with a thin module is to rewrite it. Nothing here is discarded. Every original
chapter keeps its argument and its voice and is brought to depth, and three
chapters are added for material the module gestured at and never covered:

  Why profit is not cash. Currently one clause at the end of the P&L chapter.
  It is the single thing most likely to hurt a business owner who reads their
  statements and still runs out of money, and it earns a chapter.

  The questions worth asking. The module repeatedly tells the reader to ask
  their team and never says what to ask or what a good answer sounds like.

  What good looks like over a year. Everything else is a single month. The
  reader needs to know what a trend means and when a number is worth worrying
  about rather than noting.

VOICE. Second person, addressed to a business owner rather than a bookkeeper —
they are the customer, not the operator. Terms defined at first use, no jargon
left standing, and nothing that assumes they know an accounting convention.
This is the one module in the estate where the reader is paying for the service
being described.

Run from the app package directory:  python3 build_client_reports.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "reports"
DATA = "academy_client_reports_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}

BANNED = ["at the end of the day"]

# text appended to the existing chapters, keyed by chapter index
EXTEND = {
0: """<p><b>Why the 5th working day and not the 1st.</b> The month has to be closed before it can be reported, and closing means every bank account reconciled to its statement, every supplier invoice captured, and the checklist completed and signed. A pack produced faster than that is a pack produced from incomplete records — which reads the same and is worth considerably less. The few days are the difference between a number and a number you can rely on.</p>

<p><b>What to do if the pack is late.</b> Ask, and ask early rather than waiting. Nine times in ten the answer is a document that has not reached us — a bank statement, a query unanswered — and the delay is recoverable the day it is raised. The tenth is something we should be telling you about anyway.</p>

<p><b>What the cover note is doing.</b> Five lines, written by a person rather than generated. It exists because a pack of statements answers questions you did not ask and stays silent on the one thing that actually mattered this month — so somebody who looked at your numbers writes down what they would tell you if you were in the room. Where it says nothing notable happened, that is itself information worth having.</p>

<p><b>Keep them.</b> Your packs accumulate into the record of your business, and they are what a bank, an investor or a buyer will ask for. They live permanently in your portal under Documents, so there is nothing for you to file — but knowing they are there, and that the set is complete, is worth more than most owners realise until the month somebody asks for three years of statements at a week's notice.</p>""",

1: """<p><b>The comparison column, used properly.</b> Look at it before you look at the numbers themselves. A figure means very little on its own — ₦4.2m of expenses is neither good nor bad — but ₦4.2m against ₦3.1m last month is a question, and the question is the useful part. Read the movements first, then go to the lines that moved.</p>

<p><b>Two movements that are almost always worth a question.</b> Gross margin falling while revenue holds, which means your costs moved or something is leaking between buying and selling. And any single expense line that has jumped without an obvious reason — the cover note usually explains it, and where it does not, that is precisely the thing to ask about.</p>

<p><b>One month is weather.</b> A single bad month can be a delayed invoice, a large one-off purchase, or a customer who paid late. Three months in the same direction is a trend, and trends are what you act on. Resist reorganising the business on the strength of one P&amp;L — and equally, do not dismiss the third consecutive month of the same movement as noise.</p>

<p><b>And the line most owners skip.</b> Cost of sales. It is less interesting than revenue and it is where margin is actually won or lost, because a small percentage movement there outweighs almost anything happening further down the page.</p>""",

2: """<p><b>Receivables, in one practical rule.</b> The schedule shows who owes you and for how long. Anything past your agreed terms is money you have already earned and not yet been paid for — you have effectively lent it to that customer, without deciding to. The older it gets the less likely it is to arrive, which is why the aging column matters more than the total.</p>

<p><b>Stock, if you carry it.</b> It sits on the Balance Sheet as an asset at what it cost you, not what you hope to sell it for. Stock that is not moving is money on a shelf, and it is one of the commonest places for a profitable-looking business to have no cash — the profit is real and it is sitting in the storeroom.</p>

<p><b>The tax lines deserve their own habit.</b> Once a month, look at your cash and bank figure, then subtract the VAT, PAYE and pension balances. What is left is roughly what is actually yours to use. Owners who do this are rarely surprised by a remittance; owners who do not are surprised most quarters, and the surprise is always in the same direction.</p>

<p><b>What equity tells you over time.</b> If it is growing month after month, the business is accumulating value. If it is flat while you are profitable, the profits are being drawn out as fast as they are made — which may be exactly what you intend, and is worth knowing rather than discovering.</p>""",

3: """<p><b>Where the five checks usually find something.</b> In practice it is receivables and the tax lines. Margin and the biggest mover are usually explained in the cover note before you get to them. Receivables and the tax lines are the two that quietly accumulate without anybody raising them, because nothing about them looks wrong in a single month — they only look wrong across three.</p>

<p><b>Do it at the same moment each month.</b> The five minutes only survives if it has a slot; attached to the arrival of the pack, or the first Monday, or whatever fits. Owners who intend to review their statements when they have time review them roughly twice a year, and the review is worth almost nothing done twice a year.</p>

<p><b>Why five and not fifteen.</b> A longer review does not happen. The five were chosen because each one can be done from the pack without a calculator, each has caught something real in a live business, and together they take the time of a phone call. A review you actually perform every month beats a thorough one you perform twice a year, by a margin that is not close.</p>

<p><b>If you only ever do one.</b> Subtract the tax balances from your cash. It takes fifteen seconds, it is the check most likely to prevent an unpleasant surprise, and it is the one owners most often wish they had been doing.</p>

<p><b>What to do with what you find.</b> Write down the one thing that struck you, and look for it again next month. That single habit turns a monthly read into a trend, which is the only form in which any of this is genuinely useful — and it takes about as long as the sentence you write.</p>""",

4: """<p><b>What makes a good question, from our side.</b> Specific beats general. <i>Why is cost of sales up?</i> can be answered properly; <i>are these numbers right?</i> cannot, and usually means something more particular is bothering you that is worth naming. Nobody expects you to use the right accounting word — describing what looks odd in your own terms is entirely sufficient, and it is what we would rather have.</p>

<p><b>Nothing is too small to ask.</b> The questions owners apologise for asking are frequently the ones that surface something real, and an unasked question about a figure has a way of becoming a decision made on a misunderstanding. There is no charge for asking and no such thing as an obvious question.</p>

<p><b>Where to ask it.</b> In your room, rather than by text message or in a call. Not out of formality — because the answer then sits permanently beside the figure it explains, so that in eleven months when the same question occurs to you, the answer is already there with the pack.</p>

<p><b>Adding your people.</b> Your portal can carry more than one person from your side, which is worth doing for whoever handles your paperwork day to day. Requests for documents and questions about transactions reach them directly instead of routing through you, which is usually the single biggest thing an owner can do to make their statements arrive on time.</p>""",
}

NEW_CHAPTERS = [
("Why profit is not cash", 5, """<p>The most common conversation we have with owners begins with a version of this: the P&amp;L says the business made money and there is nothing in the bank. Both things are true at once, and understanding why is probably the single most useful thing in this module.</p>

<p><b>The reason, in one sentence.</b> Profit records what you earned and what it cost you. Cash records what actually moved in and out of your account. They are different questions, and they answer at different times.</p>

<p><b>Where the money goes between the two.</b></p>

<p><b>Into customers who have not paid yet.</b> You invoice in March, the P&amp;L counts it as March's revenue, and the money arrives in May. Profitable in March, no cash in March.</p>

<p><b>Into stock.</b> Buying goods converts cash into an asset. Nothing on the P&amp;L changes until they sell, and the cash has already gone.</p>

<p><b>Into paying suppliers.</b> The mirror image — a bill you have not paid is a cost already in your P&amp;L and cash still in your account, which flatters your bank balance rather than your profit.</p>

<p><b>Into things that are not costs at all.</b> Repaying a loan, buying equipment, or the owner drawing money out. Every one of them reduces your bank balance and appears nowhere on the P&amp;L.</p>

<p><b>Which produces the practical version.</b> A growing business is frequently short of cash precisely because it is growing — more sales means more stock bought and more customers owing you, and both consume cash before the profit arrives. That is normal, it is survivable, and it is dangerous only when nobody saw it coming.</p>

<p><b>The two questions to hold apart.</b> <i>Are we profitable?</i> and <i>can we pay next month's bills?</i> are different questions with different answers, and a business can be a confident yes on one and a nervous no on the other for months at a time. Most owner anxiety about money comes from asking the first and hearing an answer to it while worrying about the second.</p>

<p><b>The version that catches people out.</b> A very good month, followed by a cash squeeze six weeks later. You sold more than usual, which meant buying more stock and invoicing more customers, and both of those consumed cash immediately while the profit arrives on your customers' payment terms. Nothing went wrong. The business simply funded its own growth out of your bank account, and nobody mentioned that it would.</p>

<p><b>What to do about it, and it is simple.</b> Read your bank balance and your profit as two separate facts, every month, and never assume one predicts the other. When they diverge, the Balance Sheet says where the difference went — receivables up, stock up, or money drawn out. That is the whole diagnosis.</p>"""),

("The questions worth asking", 5, """<p>This module keeps telling you to ask your team. It is worth being specific about what, because owners consistently ask fewer questions than they should and then act on assumptions instead.</p>

<p><b>The four that are always worth asking.</b></p>

<p><b>Is there anything in this pack you would want me to notice?</b> The most valuable question available to you, and almost nobody asks it. Your accounting team sees your numbers every day and forms views they may not volunteer unprompted, partly because they do not want to seem alarmist.</p>

<p><b>What is the biggest thing that moved, and why?</b> Even where the cover note explains it, asking again gets you the reasoning rather than the summary.</p>

<p><b>What is my cash going to look like next month?</b> Your team can see your receivables, your payables and your commitments. They cannot forecast your sales, and between those they can usually tell you more than you would expect.</p>

<p><b>Is anything about to become a problem?</b> Aging receivables, a tax balance building faster than usual, a supplier account stretching. All visible in the records before they are visible to you.</p>

<p><b>What a good answer sounds like.</b> A number, a cause, and what happens next. <i>Cost of sales rose 4 points because the November purchase came in at the new price — it will hold at this level unless the supplier moves again.</i> If an answer leaves you unsure what to do with it, say so; that is not a difficult conversation and it usually means the answer was incomplete rather than that you missed something.</p>

<p><b>What not to worry about asking.</b> Whether you are using the right word. Owners regularly preface a question with an apology for not being an accountant, and it is genuinely unnecessary — describing what looks odd in ordinary language is not a lesser version of the question, it is the question. Your team translates for a living.</p>

<p><b>When to ask.</b> When the pack arrives, not three months later. Your team has the month fresh, the working papers open and the reasoning still in their head — the same question in July about March gets a slower and thinner answer, through no fault of anybody's.</p>

<p><b>Who to ask, if your business has grown.</b> The person who prepares your books and the person who advises you may not be the same, and questions about what a number means go to the first while questions about what to do about it go to the second. Where you are unsure, ask anyway — being routed to the right person costs you nothing and telling us which questions you have is itself useful.</p>

<p><b>And the question to ask once a year.</b> What would you do differently if this were your business? It is an unusual thing to ask an accountant and the answers tend to be worth the awkwardness.</p>"""),

("What good looks like over a year", 5, """<p>Every other chapter is about one month. This one is about the shape across twelve, which is where the statements stop being a report and start being useful.</p>

<p><b>The three lines worth tracking across the year.</b> Gross margin as a percentage, because it should be broadly stable and a slow drift is the commonest way a business gets quietly less profitable. Receivables as a share of your monthly sales, because a steady climb means you are collecting more slowly than you are selling. And your tax balances against your cash, because that gap is what a remittance date will eventually test.</p>

<p><b>What is normal.</b> Monthly figures bounce. Seasonal trades bounce enormously — a December that looks like a different business is not a signal. What matters is the same month against the same month last year, which strips the season out and is the comparison worth making once you have a year of packs.</p>

<p><b>When to be concerned rather than curious.</b> Three consecutive months moving the same way on any of the three lines above. A gap between profit and cash that widens rather than fluctuates. And any figure your team cannot explain when asked — rare, and worth taking seriously when it happens, because unexplained is different from complicated.</p>

<p><b>What the year-end brings.</b> Your annual accounts and tax filings are built from these same monthly packs, which is why the monthly discipline matters more than it appears to. A business that has closed and reviewed twelve clean months arrives at its year end with the work already done. One that has not spends the first quarter of the following year reconstructing the previous one, at a cost, under a deadline.</p>

<p><b>What a year of packs is actually worth to you.</b> Beyond the reading: it is the evidence that your business is what you say it is. Owners tend to think of monthly statements as a compliance chore and discover their value at the one moment it cannot be manufactured — a loan application, a partner's due diligence, a sale. None of those can be prepared for in a fortnight.</p>

<p><b>What a bank or a buyer looks at.</b> Not one month. They want twelve, consistent, with the same figures appearing in the same places and no unexplained gaps — which is exactly what a year of monthly closes produces and exactly what a business reconstructing its year in March cannot show. The monthly pack is quietly building an asset, and its value only appears at the moment somebody asks for it.</p>

<p><b>And the thing worth doing once a year.</b> Read twelve cover notes in a row. It takes twenty minutes, it is the closest thing to a narrative history of your business that exists, and owners are frequently surprised by what they had forgotten was a concern in March.</p>"""),
("The whole thing, in one page", 4, """<p>Eight chapters, and it reduces to less than it looks.</p>

<p><b>What arrives, and when.</b> By the 5th working day, in your portal. Cover note first, always — it is written to answer the question you were about to ask.</p>

<p><b>The P&amp;L says whether you made money.</b> Read the comparison column before the figures. Gross margin is the number to watch. One month is weather; three months in the same direction is a trend.</p>

<p><b>The Balance Sheet says what you own and owe.</b> Receivables aging matters more than the receivables total. The tax lines were never your money.</p>

<p><b>Profit is not cash.</b> The difference went into customers who have not paid, stock, supplier payments, or out of the business — and the Balance Sheet says which.</p>

<p><b>Five checks, five minutes, same moment every month.</b> Cover note, gross margin, biggest mover, receivables aging, tax lines. If you only ever do one, subtract the tax balances from your cash.</p>

<p><b>Ask.</b> Specifically, in your room, when the pack arrives. The most valuable question is whether there is anything in it your team would want you to notice.</p>

<p><b>And across a year</b>, watch three lines: gross margin, receivables against monthly sales, and tax balances against cash. Compare the same month to the same month last year rather than to last month.</p>

<p><b>What this module deliberately did not do.</b> Teach you accounting. Nothing here requires you to prepare a statement, know a debit from a credit, or check anybody's arithmetic — that is the service you are paying for, and duplicating it would be a poor use of your time. What it teaches is how to read the output and what to ask, which is the part that cannot be delegated because only you know what you were expecting.</p>

<p><b>The one habit worth building.</b> Open the pack the day it arrives, read the cover note, run the five checks, and write down the one thing that struck you. Under ten minutes, once a month — and it is the difference between receiving statements and actually knowing how your business is doing.</p>

<p><b>If you take one sentence from the whole module.</b> Your statements are not a report card and they are not a compliance obligation — they are the only regular, honest description you get of a business you are otherwise experiencing from the inside. Ten minutes a month is a small price for the outside view, and almost every owner who starts doing it says the same thing: the surprise was how much was already visible.</p>

<blockquote>If any of this raised a question, ask it in your room. There is no charge for asking, no such thing as an obvious question, and the answer will sit permanently beside the figure it explains.</blockquote>"""),
]

CHECKS = {
0: [
 C("The pack arrives on the 5th working day rather than the 1st because:",
   ["Of processing queues", "The month must be closed first — banks reconciled, invoices captured, checklist signed",
    "It is a contractual term", "Statements are batched"], 1,
   "A pack produced faster is produced from incomplete records, which reads the same and is worth much less."),
 C("The first thing to read when the pack arrives is:",
   ["The Profit & Loss", "The cover note",
    "The Balance Sheet", "The schedules"], 1,
   "It is written to answer the question you were about to ask, and lists anything awaiting you."),
 C("If the pack is late, the usual cause is:",
   ["Volume at the accounting team", "A document that has not reached them",
    "A system delay", "A public holiday"], 1,
   "Nine times in ten, and recoverable the day it is raised.")],
1: [
 C("The single most watchable number on the P&L is:",
   ["Revenue", "Gross margin as a percentage",
    "Total expenses", "The bottom line"], 1,
   "If prices are unchanged and margin falls, costs rose or something is leaking."),
 C("A single month's figure is described as weather. Climate is:",
   ["The annual accounts", "The trend across months",
    "The budget", "The prior year"], 1,
   "One month can be a delayed invoice or a late-paying customer; the trend across months is what you steer by."),
 C("The line most owners skip, where margin is actually won or lost, is:",
   ["Operating expenses", "Cost of sales",
    "Revenue", "Depreciation"], 1,
   "A small percentage movement there outweighs almost anything further down the page.")],
2: [
 C("Money owed to you past your agreed terms means you have:",
   ["A collection problem to escalate", "Effectively lent it to that customer without deciding to",
    "Written it off", "A cash timing difference only"], 1,
   "The older it gets the less likely it is to arrive, which is why the aging matters more than the total."),
 C("VAT, PAYE and pension balances on your Balance Sheet are:",
   ["Yours until remitted", "Money that was never yours",
    "An expense already taken", "Provisions"], 1,
   "It sits in your bank looking like cash and belongs to FIRS, the state and your staff's pension accounts."),
 C("The monthly habit suggested for the tax lines is to take your cash figure and:",
   ["Compare it to last month", "Subtract the VAT, PAYE and pension balances",
    "Divide by monthly costs", "Add expected receipts"], 1,
   "What is left is roughly what is actually yours to use.")],
3: [
 C("In practice, the five checks most often find something in:",
   ["Margin and the biggest mover", "Receivables and the tax lines",
    "Revenue", "Operating expenses"], 1,
   "The other two are usually explained in the cover note before you reach them."),
 C("Owners who intend to review their statements when they have time review them:",
   ["Monthly", "About twice a year",
    "Quarterly", "Weekly"], 1,
   "Which is why the five minutes needs a fixed slot rather than an intention."),
 C("After the review, the habit that turns it into something useful is:",
   ["Filing the pack", "Writing down the one thing that struck you and looking for it next month",
    "Calling your accountant", "Comparing to budget"], 1,
   "That is what turns a monthly read into a trend.")],
4: [
 C("A good question to your accounting team is:",
   ["General, so they can range widely", "Specific",
    "Written formally", "Asked at the year end"], 1,
   "'Why is cost of sales up' can be answered properly; 'are these numbers right' cannot."),
 C("Questions should be asked in your room rather than by call or text because:",
   ["It is the formal channel", "The answer then sits permanently beside the figure it explains",
    "It is faster", "Calls are not recorded"], 1,
   "So that in eleven months, when the same question occurs to you, the answer is already there."),
 C("The biggest single thing an owner can do to make statements arrive on time is:",
   ["Chase the accounting team", "Add the person who handles their paperwork to the portal",
    "Send documents monthly", "Confirm receipt promptly"], 1,
   "Requests and queries then reach them directly instead of routing through you.")],
5: [
 C("A profitable month with no cash in the bank usually means the money went into:",
   ["Expenses not yet recorded", "Receivables, stock, supplier payments, or out of the business",
    "Tax", "An accounting error"], 1,
   "Profit records what you earned; cash records what actually moved."),
 C("Repaying a loan, buying equipment and drawing money out have in common that they:",
   ["Reduce profit", "Reduce your bank balance and appear nowhere on the P&L",
    "Are tax deductible", "Increase equity"], 1,
   "Which is one of the four places the difference between profit and cash goes."),
 C("A growing business is frequently short of cash because:",
   ["Growth is unprofitable", "More sales means more stock and more customers owing you, both before the profit arrives",
    "Costs rise faster", "Margins fall with volume"], 1,
   "Normal and survivable, and dangerous only when nobody saw it coming.")],
6: [
 C("The most valuable question available to an owner, and almost never asked, is:",
   ["What is my profit?", "Is there anything in this pack you would want me to notice?",
    "Are the numbers right?", "How do we reduce tax?"], 1,
   "Your team forms views they may not volunteer, partly from not wanting to seem alarmist."),
 C("A good answer contains a number, a cause and:",
   ["A comparison", "What happens next",
    "A recommendation", "The source document"], 1,
   "If an answer leaves you unsure what to do with it, that usually means it was incomplete."),
 C("Your accounting team can forecast your cash better than you expect because they can see:",
   ["Your sales pipeline", "Your receivables, payables and commitments",
    "Your market", "Your bank's position"], 1,
   "What they cannot see is your future sales.")],
7: [
 C("The comparison that strips out seasonality is:",
   ["This month against last month", "The same month against the same month last year",
    "The rolling quarter", "Year to date against budget"], 1,
   "Which becomes available once you have a year of packs."),
 C("Concern rather than curiosity is warranted when a line moves the same way for:",
   ["One month", "Three consecutive months",
    "Two quarters", "A full year"], 1,
   "Along with a profit-to-cash gap that widens rather than fluctuates."),
 C("A business that has closed and reviewed twelve clean months arrives at year end:",
   ["With more to do", "With the work already done",
    "Needing an audit", "At the same position"], 1,
   "One that has not spends the first quarter reconstructing the previous year, at a cost and under a deadline.")],
8: [
 C("The one habit the module recommends building takes:",
   ["An hour a month", "Under ten minutes, once a month",
    "A weekly review", "A quarterly meeting"], 1,
   "Open the pack, read the cover note, run the five checks, write down the one thing that struck you."),
 C("If you do only one of the five checks, it should be:",
   ["Gross margin", "Subtracting the tax balances from your cash",
    "The biggest mover", "Receivables aging"], 1,
   "Fifteen seconds, and the check most likely to prevent an unpleasant surprise."),
 C("The difference the habit makes is between receiving statements and:",
   ["Filing them properly", "Actually knowing how your business is doing",
    "Satisfying your bank", "Reducing your accounting fee"], 1,
   "Which is the whole argument of the module in one line.")],
}

EXTRA_QUESTIONS = [
 Q("A pack produced faster than the close allows is:", ["More useful", "Produced from incomplete records", "Standard practice", "A premium service"], 1,
   "It reads the same and is worth considerably less.", "L1", "What arrives every month, and when"),
 Q("Your monthly packs live permanently in:", ["Your email", "Your portal Documents", "A shared drive", "The accountant's files"], 1,
   "Which matters the month somebody asks for three years of statements at a week's notice.", "L1", "What arrives every month, and when"),
 Q("Read the comparison column:", ["After the figures", "Before the figures", "Only at year end", "When something looks wrong"], 1,
   "A figure alone means little; a movement is a question, and the question is the useful part.", "L2", "Reading your Profit & Loss"),
 Q("Gross margin falling while revenue holds means:", ["Sales are weakening", "Costs moved or something is leaking between buying and selling", "Prices rose", "Nothing material"], 1,
   "One of the two movements almost always worth a question.", "L2", "Reading your Profit & Loss"),
 Q("Three months moving in the same direction is:", ["Noise", "A trend", "Seasonal", "A reporting artefact"], 1,
   "One month is weather; resist reorganising on a single P&L and do not dismiss the third.", "L2", "Reading your Profit & Loss"),
 Q("Stock sits on the Balance Sheet at:", ["What you expect to sell it for", "What it cost you", "Market value", "Net of margin"], 1,
   "Stock that is not moving is money on a shelf.", "L3", "Reading your Balance Sheet"),
 Q("Equity flat while the business is profitable means:", ["A reporting error", "Profits are being drawn out as fast as they are made", "Losses elsewhere", "Tax is too high"], 1,
   "Which may be exactly what you intend, and is worth knowing rather than discovering.", "L3", "Reading your Balance Sheet"),
 Q("The five-minute review works best:", ["Whenever there is time", "At the same moment each month", "Quarterly", "Before a bank meeting"], 1,
   "Owners who wait for time review roughly twice a year.", "L4", "The five-minute monthly review"),
 Q("Steady sales with climbing receivables means you are:", ["Growing well", "Selling well and collecting badly", "Over-invoicing", "Under-pricing"], 1,
   "Caught early it is a phone call rather than a crisis.", "L4", "The five-minute monthly review"),
 Q("Questions owners apologise for asking are frequently:", ["Unnecessary", "The ones that surface something real", "Already answered", "Best sent by email"], 1,
   "An unasked question has a way of becoming a decision made on a misunderstanding.", "L5", "Working with your accounting team"),
 Q("Answering a transaction query the same day means:", ["Faster statements only", "Your books are truer all month", "A discount", "Fewer reminders only"], 1,
   "The transaction gets posted correctly rather than waiting.", "L5", "Working with your accounting team"),
 Q("Profit records what you earned; cash records:", ["What you kept", "What actually moved in and out", "What you invoiced", "What is owed"], 1,
   "Different questions, answered at different times.", "L6", "Why profit is not cash"),
 Q("Invoicing in March and being paid in May makes March:", ["Cash positive", "Profitable without the cash", "Loss making", "Unrecorded"], 1,
   "One of the four places the difference goes.", "L6", "Why profit is not cash"),
 Q("When profit and cash diverge, the statement that says where the difference went is:", ["The P&L", "The Balance Sheet", "The cover note", "The schedules"], 1,
   "Receivables up, stock up, or money drawn out — that is the whole diagnosis.", "L6", "Why profit is not cash"),
 Q("Asking what your cash will look like next month works because your team can see:", ["Your sales forecast", "Your receivables, payables and commitments", "Your market", "Your bank limits"], 1,
   "They cannot forecast your sales, and between those they usually know more than you expect.", "L7", "The questions worth asking"),
 Q("The question suggested once a year is:", ["What is our tax position?", "What would you do differently if this were your business?", "Are we compliant?", "How do we cut costs?"], 1,
   "An unusual thing to ask an accountant, and the answers tend to be worth the awkwardness.", "L7", "The questions worth asking"),
 Q("If an answer leaves you unsure what to do with it, you should:", ["Accept it", "Say so", "Ask somebody else", "Wait for next month"], 1,
   "It usually means the answer was incomplete rather than that you missed something.", "L7", "The questions worth asking"),
 Q("The three lines worth tracking across a year are gross margin, tax balances against cash, and:", ["Total expenses", "Receivables as a share of monthly sales", "Headcount", "Revenue growth"], 1,
   "A steady climb means you are collecting more slowly than you are selling.", "L8", "What good looks like over a year"),
 Q("A December that looks like a different business is:", ["A warning", "Not a signal, in a seasonal trade", "An error", "Always investigated"], 1,
   "Which is why the same month against the same month last year is the comparison worth making.", "L8", "What good looks like over a year"),
 Q("A figure your team cannot explain when asked is:", ["Common", "Rare, and worth taking seriously", "Expected in complex months", "A timing difference"], 1,
   "Unexplained is different from complicated.", "L8", "What good looks like over a year"),
 Q("Reading twelve cover notes in a row is described as:", ["A compliance exercise", "The closest thing to a narrative history of your business", "Unnecessary", "An audit preparation"], 1,
   "Twenty minutes, and owners are frequently surprised by what they had forgotten.", "L8", "What good looks like over a year"),
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
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data[KEY]

    if len(mod["lessons"]) == 5:
        for i, extra in sorted(EXTEND.items()):
            mod["lessons"][i]["html"] = mod["lessons"][i]["html"].rstrip() + "\n" + extra
            mod["lessons"][i]["est"] = 7
        for title, est, html in NEW_CHAPTERS:
            mod["lessons"].append({"title": title, "est": est, "html": html})
        bank_now = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in mod["questions"]}
        for q in EXTRA_QUESTIONS:
            if re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() not in bank_now:
                mod["questions"].append(q)
    else:
        print("already extended (%d chapters) — refreshing checks only" % len(mod["lessons"]))

    if len(mod["lessons"]) != 9:
        raise SystemExit("ABORT: %d chapters, expected 9" % len(mod["lessons"]))

    rebalance(mod["questions"], "clientreports:exam")
    flat = [c for _i, ch in sorted(CHECKS.items()) for c in ch]
    rebalance(flat, "clientreports:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in mod["questions"]}
    problems, seen = [], set()
    for idx, checks in sorted(CHECKS.items()):
        if idx >= len(mod["lessons"]):
            problems.append("no chapter %d" % (idx + 1))
            continue
        if len(checks) != 3:
            problems.append("ch%d has %d checks" % (idx + 1, len(checks)))
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
        mod["lessons"][idx]["checks"] = [dict(c, sort=i) for i, c in enumerate(checks)]
    missing = [i + 1 for i in range(len(mod["lessons"])) if not mod["lessons"][i].get("checks")]
    if missing:
        problems.append("chapters without checks: %s" % missing)
    for l in mod["lessons"]:
        flat_t = re.sub(r"<[^>]+>", " ", l["html"]).lower()
        for b in BANNED:
            if b in flat_t:
                problems.append("banned phrase in %s" % l["title"][:40])
    if problems:
        raise SystemExit("ABORT — %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    print("checks: %d | questions: %d" % (
        sum(len(l["checks"]) for l in mod["lessons"]), len(mod["questions"])))
    sp = collections.Counter(q["ans"] for q in mod["questions"])
    print("answer spread: %s | guessable %d%%" % (
        dict(sorted(sp.items())), round(max(sp.values()) * 100 / len(mod["questions"]))))
    thin = [i + 1 for i, n in enumerate(lens) if n < 2500]
    print("thin chapters:", thin or "NONE")


if __name__ == "__main__":
    main()
