#!/usr/bin/env python3
"""Build the Profit Is Not Cash module into academy_finance_data.json.

Track module 3. Completes the three-statement foundation: module 1 said how the
period went, module 2 said what the business is standing on, this one traces
where the money actually moved.

Deliberately does NOT re-teach stock days, debtor days and creditor days —
module 2 built them. This module uses them, which is the point of writing the
reading spine in order.

Merges into the data file. Rebalance is folded into the build.

Run from the app package directory:  python3 build_finance_m4.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "profit_cash"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The profitable business that ran out of money", 10, """<p>More businesses fail while profitable than fail while making losses. That sentence sounds wrong the first time anyone hears it, and understanding why it is true is the most valuable thing in this module.</p>

<p><b>Walk through a year that looks like success.</b></p>

<p>A distributor turns over ₦180,000,000 and earns 22% gross margin. Overheads are ₦28,000,000. Operating profit is ₦11,600,000 — a genuinely decent year, and every monthly P&L said so.</p>

<p>Now follow the money instead of the profit.</p>

<p>Demand grew, so stock was built from ₦24,000,000 to ₦38,000,000: <b>₦14,000,000 of cash converted into goods</b>. The new customers won during the year buy on credit, so receivables rose from ₦20,000,000 to ₦33,000,000: <b>another ₦13,000,000 delivered and not yet collected</b>. Two delivery vehicles were bought outright for ₦9,000,000. And the owner drew ₦6,000,000, which never appears on the P&L at all.</p>

<p>Against ₦11,600,000 of profit, the business absorbed roughly ₦42,000,000. It ended the year more profitable, larger, better positioned — and about ₦30,000,000 short of cash. Every one of those decisions was reasonable. Together they are how a good year becomes an emergency.</p>

<p><b>The four ways profit and cash separate.</b></p>

<p><b>Timing.</b> Revenue is recognised on delivery, cost when goods are sold. Cash moves when people pay, which is neither of those moments.</p>

<p><b>Working capital.</b> Growth absorbs cash into stock and receivables before it returns any. The faster you grow, the more it absorbs.</p>

<p><b>Capital spending.</b> Buying a vehicle costs the cash today and hits the P&L over five years as depreciation. The bank feels it immediately; the profit figure barely notices.</p>

<p><b>Things that never touch the P&L at all.</b> Loan principal repayments, owner drawings, tax payments on a different timetable to the charge. Every one drains cash while leaving profit untouched.</p>

<p><b>Why this catches capable people.</b> Because the P&L is the statement that gets read, discussed in meetings, and used to judge managers. It is genuinely the right instrument for asking whether the trading works. It simply cannot answer the question that determines survival, which is whether the money is there when it is needed — and nothing about a healthy P&L warns you that it is not.</p>

<p><b>The uncomfortable corollary.</b> A business can trade its way into failure by succeeding. Winning a large customer on ninety-day terms is a commercial triumph and a cash event, and the two arrive at different times. The order comes first. The cash comes last. What happens in between has to be funded by somebody, and if nobody planned for it, that somebody is the business's own bank balance.</p>

<blockquote>WATCH-OUT: The phrase to be most suspicious of in your own reporting is "we had a great month". Ask immediately what it did to stock and receivables. A great month that consumed three months of cash is a fact worth knowing on the day, not in the quarter.</blockquote>

<p><b>One clarification, because it is where people over-correct.</b> None of this means growth is dangerous or that credit customers should be refused. It means growth has a price, that price is paid in cash before it is earned back, and somebody has to decide deliberately how much of it the business can fund. A company that grows 30% with a plan for the working capital is in a completely different position from one that grows 30% and discovers the consequence in month eight.</p>""",
 [C("Which is most often the cause when a profitable business fails?",
    ["Poor margins", "Cash absorbed by growth, capital spending and drawings",
     "Excessive depreciation", "High tax charges"], 1,
    "Every one of those is reasonable on its own. Together they consume more than the profit earned."),
  C("Buying a ₦9m vehicle outright affects this year's P&L by roughly:",
    ["₦9m", "Nothing", "One year's depreciation", "₦9m less the resale value"], 2,
    "The bank feels the whole ₦9m immediately; profit sees only the annual charge."),
  C("An owner drawing ₦6m from the business appears on the P&L as:",
    ["An expense", "A drawing in operating costs", "Nothing at all", "A financing cost"], 2,
    "Drawings reduce equity and drain cash without ever touching profit, which is why they surprise owners.")]),

("What the cash flow statement shows", 10, """<p>The third statement exists because the first two, read together, still only let you infer the movement of money. The cash flow statement traces it directly: opening balance, everything that came in, everything that went out, closing balance.</p>

<p><b>It is the least opinion-laden statement you will read.</b> The P&L depends on estimates — depreciation lives, provisions, accruals, cut-off. The balance sheet carries those same judgements in its totals. Cash either moved or it did not. There is a bank statement, and it agrees or somebody has a serious problem.</p>

<p>That is why analysts and lenders reach for it first. A business can flatter profit in half a dozen legitimate ways without breaking a single rule. Flattering cash requires the money to actually be there.</p>

<p><b>What it answers that nothing else does.</b> Not "did we do well" — that is the P&L. Not "what are we standing on" — that is the balance sheet. It answers <b>where did the money come from and where did it go</b>, which is the question every manager asks in the week the bank balance surprises them.</p>

<p><b>The shape of it.</b> Three sections, each answering a different question, then a total that ties to the movement in the bank:</p>

<p><b>Operating</b> — did trading generate cash, or consume it?<br>
<b>Investing</b> — what was spent on, or received from, long-term assets?<br>
<b>Financing</b> — what came from or went to lenders and owners?</p>

<p>Add the three and you get the change in cash for the period. That number can be checked against the bank in about ten seconds, which is precisely why the statement is trusted.</p>

<p><b>The one thing people misread.</b> A negative total is not automatically bad and a positive total is not automatically good, and the section matters more than the sign. Cash falling because the business bought a warehouse is a decision. Cash falling because trading consumed it is a condition. Cash rising because a loan was drawn is borrowed comfort. Cash rising because customers paid is the real thing.</p>

<p><b>How to read it in ninety seconds.</b> Look at operating cash first, and only then at the total. If operating cash is strongly positive and the total is negative, the business is generating money and choosing to spend it — usually fine. If operating cash is negative and the total is positive, something outside trading is holding the business up, and that source will eventually stop.</p>

<blockquote>IMPLEMENTATION TIP: If your business does not produce a cash flow statement monthly, you can build the important half from two balance sheets and a P&L in about twenty minutes. The next chapters show how — and doing it yourself once teaches more than reading a hundred prepared ones.</blockquote>

<p><b>A word on what "cash" means here.</b> It is money genuinely available: bank balances and equivalents. It is not the value of stock you could sell, not receivables you expect to collect, and not an unused overdraft facility — a facility is somebody else's money, available at their discretion, and treating it as cash is how businesses discover the meaning of "repayable on demand" at the worst possible moment.</p>""",
 [C("Why is the cash flow statement harder to flatter than the P&L?",
    ["It is audited more often", "It relies on fewer estimates — cash either moved or it did not",
     "It is prepared last", "It excludes tax"], 1,
    "Depreciation lives, provisions and cut-off are all judgement. A bank statement is not."),
  C("Operating cash is strongly negative while total cash rose. This means:",
    ["Trading is generating money", "Something outside trading is holding the business up",
     "The business is highly profitable", "Suppliers are being paid early"], 1,
    "Borrowing or asset sales can mask a trading problem, and that source eventually stops."),
  C("Cash fell this month because a warehouse was purchased. This is:",
    ["A condition to worry about", "A decision, visible in the investing section",
     "An operating failure", "A financing problem"], 1,
    "The section matters more than the sign. Where the money went tells you whether to be concerned.")]),

("Operating, investing, financing", 10, """<p>The three sections are not filing categories. Each answers a distinct question, and reading them separately is what turns the statement from a number into a diagnosis.</p>

<p><b>Operating activities: does the trading itself generate cash?</b></p>

<p>Cash from customers, less cash to suppliers, staff, landlords, and the tax authority. This is the engine. A business whose operating cash is consistently negative is being funded by somebody else — a lender, an investor, or its own assets being sold — and no amount of profit growth changes that until the operating line turns.</p>

<p>Over a full year, operating cash should broadly resemble operating profit. When it does not, the gap is the interesting part, and the next chapter is entirely about reading it.</p>

<p><b>Investing activities: what did we spend on the future?</b></p>

<p>Buying vehicles, equipment, premises, software; and on the other side, proceeds when assets are sold. Normally negative in a growing business, which is healthy — it means capacity is being built.</p>

<p>The reading that matters is <b>investing against depreciation</b>. If depreciation is ₦6,000,000 a year and capital spending is ₦1,000,000, the asset base is being consumed faster than it is replaced. Profit looks fine for years while the fleet ages, and the reckoning arrives all at once. Consistent investing below depreciation is a business quietly eating itself.</p>

<p><b>Financing activities: who is funding us, and are we paying them back?</b></p>

<p>Loans drawn and repaid, owner injections, drawings and dividends. Note that <b>only the principal repayment sits here</b> — interest is an operating cost. That split confuses people constantly: a ₦2,000,000 monthly loan payment made up of ₦1,600,000 principal and ₦400,000 interest appears in two different sections.</p>

<p><b>The combination is the diagnosis.</b> Positive operating, negative investing, negative financing is the healthiest common shape: trading generates cash, some is reinvested, some repays debt. Negative operating, positive financing is the shape of a business surviving on borrowing. Positive operating and heavily positive financing might be funding an expansion — or might be borrowing that nobody has asked hard questions about.</p>

<p><b>One pattern worth naming.</b> Strongly positive operating cash alongside near-zero investing, sustained over years, often means an owner extracting everything the business generates. It looks superb on the operating line. It is a business being harvested rather than built, and the sign appears in the financing section as drawings, not anywhere on the P&L.</p>

<blockquote>IMPLEMENTATION TIP: Compare capital spending to depreciation once a year. It is one division, and it answers whether the business is building capacity, holding it, or living off it — a question almost nobody asks and everybody eventually cares about.</blockquote>

<p><b>Where the sections mislead if read alone.</b> A business selling assets to fund operations shows healthy total cash: the investing section is positive and the total looks fine. Only the split reveals that the business is consuming its own capacity to pay this month's bills. That is why the three sections are presented separately rather than netted — the net figure would hide precisely the thing you most need to see.</p>""",
 [C("Interest paid on a loan belongs in which section?",
    ["Financing, with the principal", "Operating", "Investing", "It is excluded from cash flow"], 1,
    "Only the principal repayment is financing. A single monthly instalment therefore splits across two sections."),
  C("Depreciation ₦6m a year with capital spending of ₦1m suggests:",
    ["Efficient asset management", "The asset base is being consumed faster than replaced",
     "Assets are overvalued", "Strong reinvestment"], 1,
    "Profit looks fine for years while the fleet ages, and the replacement bill arrives at once."),
  C("Negative operating cash with strongly positive financing cash describes:",
    ["A business reinvesting profits", "A business surviving on borrowing",
     "A business repaying debt", "A seasonal peak"], 1,
    "Trading is consuming cash and lenders are covering it. That source has a limit.")]),

("From profit to operating cash", 10, """<p>Operating cash is not calculated from scratch. It starts at operating profit and adjusts, which is exactly why the reconciliation is so useful: each adjustment names a reason profit and cash differed, and the list is short enough to hold in your head.</p>

<p><b>Start with operating profit. Then three groups of adjustment.</b></p>

<p><b>1. Add back non-cash charges.</b> Depreciation and amortisation reduced profit and moved no money, so they come straight back. This is the single largest adjustment in most asset-heavy businesses and the reason a company with modest profit can generate solid cash.</p>

<p><b>2. Adjust for working capital movements.</b> Here the balance sheet earns its keep:</p>

<p>Stock rose ₦14,000,000 → subtract ₦14,000,000. Cash went into goods.<br>
Receivables rose ₦13,000,000 → subtract ₦13,000,000. You delivered and were not paid.<br>
Payables rose ₦5,000,000 → add ₦5,000,000. Suppliers funded you.</p>

<p>The rule in one line: <b>an asset going up uses cash, a liability going up provides it.</b> Reversed, both hold — stock falling releases cash, payables falling consumes it.</p>

<p><b>3. Deduct tax actually paid</b>, which is rarely the tax charged in the accounts.</p>

<p><b>The worked example from chapter one, finished properly.</b></p>

<p>Operating profit ₦11,600,000. Add depreciation ₦4,000,000 → ₦15,600,000. Less stock increase ₦14,000,000 → ₦1,600,000. Less receivables increase ₦13,000,000 → negative ₦11,400,000. Add payables increase ₦5,000,000 → negative ₦6,400,000.</p>

<p>So a business reporting ₦11,600,000 of operating profit consumed ₦6,400,000 of cash from trading — before it bought a single vehicle or paid the owner anything. The ₦18,000,000 gap is not an error or a mystery. It is three balance sheet lines, and it is entirely explainable in four minutes to anyone who asks.</p>

<p><b>Why doing this yourself matters.</b> You need two balance sheets and one P&L, all of which you already receive. Working the reconciliation once, by hand, on your own numbers, converts "I don't understand why we're short" into "we are short because stock and debtors absorbed ₦27,000,000, and here is which one I intend to attack first.”</p>

<p><b>Two adjustments people commonly get backwards.</b> A <i>reduction</i> in stock is a source of cash and gets added — you sold goods you had already paid for. A <i>reduction</i> in payables is a use of cash and gets subtracted — you settled what you owed. The instinct is that falling numbers must be bad and rising numbers good, and for working capital the opposite is usually true on the cash line.</p>

<p><b>And one caution about using the reconciliation as a defence.</b> It explains the gap; it does not excuse it. “Cash fell because stock and receivables rose” is an explanation, and if the same explanation appears for four consecutive quarters it has stopped being an explanation and become the business's operating pattern — one that needs permanent funding rather than a temporary facility.</p>

<blockquote>IMPLEMENTATION TIP: Asset up, cash down. Liability up, cash up. Those two lines will get you through ninety per cent of cash flow reading, and they are worth memorising even if nothing else in this module sticks.</blockquote>""",
 [C("Depreciation is added back to profit when calculating operating cash because:",
    ["It is tax deductible", "It reduced profit but moved no money",
     "It will be spent later", "It is an estimate"], 1,
    "It is the largest adjustment in most asset-heavy businesses."),
  C("Receivables rose ₦13m during the year. In the reconciliation you:",
    ["Add ₦13m", "Subtract ₦13m", "Ignore it", "Add ₦13m less the provision"], 1,
    "An asset going up uses cash: you delivered the goods and have not been paid."),
  C("Profit ₦11.6m, depreciation ₦4m, stock +₦14m, receivables +₦13m, payables +₦5m. Operating cash is:",
    ["+₦15.6m", "−₦6.4m", "+₦11.6m", "−₦18m"], 1,
    "11.6 + 4 − 14 − 13 + 5 = −6.4m. The trading consumed cash despite reporting a profit.")]),

("Where the money actually went", 10, """<p>Module 2 built the three day-counts and the cash cycle. This chapter uses them, because the reconciliation tells you <i>how much</i> working capital absorbed and the day-counts tell you <i>why</i> — and only the second is actionable.</p>

<p><b>Absorption without explanation is not a finding.</b> "Stock absorbed ₦14,000,000" prompts the obvious response of buying less, which is often wrong. Stock rising in proportion to sales is the cost of growth. Stock rising while sales are flat is a different problem entirely, and the day-count is what distinguishes them.</p>

<p><b>Run it on the distributor.</b> Revenue rose from ₦140,000,000 to ₦180,000,000 — up 29%. Stock rose from ₦24,000,000 to ₦38,000,000 — up 58%. Stock days moved from 60 to 74.</p>

<p>Had stock merely kept pace with sales it would have reached about ₦31,000,000. The other ₦7,000,000 is the business becoming <b>less efficient</b> at holding stock, and that half is recoverable without selling less. The first half is the price of growth and is only recoverable by growing more slowly.</p>

<p>Same arithmetic on receivables. Debtor days from 52 to 67 means customers are paying fifteen days slower. On ₦180,000,000 of revenue, each day is roughly ₦493,000 — so fifteen days is about ₦7,400,000 sitting in other people's businesses that used to sit in yours.</p>

<p><b>That conversion is the most useful trick in this module: turn days into naira.</b> "Debtor days rose from 52 to 67" is a statistic that gets nodded at in a meeting. "Our customers are holding ₦7,400,000 more of our money than a year ago" is a decision. Same fact, entirely different reception.</p>

<p><b>The three levers, and their honest costs.</b></p>

<p><b>Collect faster.</b> The most immediate, and it costs relationship capital with customers you may want to keep. Best aimed at the ageing tail rather than everybody.</p>

<p><b>Hold less stock.</b> Real money, and it risks stockouts — which cost margin and customers in ways that never appear as a line on the P&L. Aim at the slow and dead lines first, never across the board.</p>

<p><b>Pay suppliers later.</b> Free until it is not: supply slows, priority moves elsewhere, prices harden.</p>

<p><b>The one that is not a lever.</b> Cutting overheads improves profit and does very little for the cash cycle. It is the response most managers reach for first and the one least connected to the problem, because the money is not in the overheads — it is on the shelves and in other people's bank accounts.</p>

<blockquote>IMPLEMENTATION TIP: Work out what one day of receivables is worth in your business — annual revenue divided by 365. Once you know that number, every conversation about collection has a price attached, and collection stops being an administrative chore.</blockquote>

<p><b>A sequencing point.</b> Of the three levers, receivables moves fastest and stock moves largest. Collection responds to attention within weeks. Stock takes a buying cycle or more, because you cannot un-buy what is already on the shelves — you can only stop adding and sell through what is there. When cash is tight, chase collections for immediate relief and adjust buying for the structural fix, and expect the two to arrive on different timescales.</p>""",
 [C("Revenue up 29% while stock rose 58% means:",
    ["Growth alone explains the stock", "Roughly half the increase is lost efficiency, and is recoverable",
     "Stock was written down", "Suppliers raised prices"], 1,
    "Growth explains the first part; the rest is holding stock less efficiently, which can be recovered without selling less."),
  C("Revenue ₦180m. One day of receivables is worth roughly:",
    ["₦180,000", "₦493,000", "₦1.5m", "₦15m"], 1,
    "180m ÷ 365 ≈ ₦493,000. Turning days into naira is what makes collection a decision rather than a chore."),
  C("Which response does least to improve the cash cycle?",
    ["Collecting receivables faster", "Reducing slow-moving stock",
     "Cutting overheads", "Taking full supplier terms"], 2,
    "It improves profit but the money is on the shelves and in customers' accounts, not in the overheads.")]),

("Forecasting cash for an operating unit", 10, """<p>Everything so far looked backwards. A cash forecast looks forward, and it is the one piece of finance an operating manager should build themselves rather than receive.</p>

<p><b>Thirteen weeks, one line per week.</b> Not months — months hide the problem, because a business can be comfortable on the first and desperate on the twenty-eighth and the monthly view shows neither. Thirteen weeks is long enough to see trouble coming and short enough to forecast honestly.</p>

<p><b>Four blocks, and no more.</b></p>

<p><b>Opening balance.</b> What is actually in the bank. Not the ledger, the bank.</p>

<p><b>Receipts.</b> Collections from existing receivables, week by week according to when each customer really pays rather than when their terms say they should. Then cash sales, which you can estimate from history with reasonable confidence.</p>

<p><b>Payments.</b> Suppliers by due date, payroll on its date, rent, power, loan instalments, tax on its due date. These are mostly knowable, which is what makes the exercise worth doing.</p>

<p><b>Closing balance</b>, which becomes next week's opening.</p>

<p><b>The discipline is in the receipts, and that is where honesty is hardest.</b> The temptation is to assume everyone pays on terms. They do not, and you already know which ones. A customer who has taken sixty days for the last six invoices will take sixty days for the next one, and a forecast that assumes thirty is not a forecast — it is a wish that will make next month a surprise.</p>

<p><b>What the forecast is for.</b> Not accuracy — it will be wrong. Its purpose is <b>lead time</b>. A trough spotted in week nine can be managed: chase a specific large debtor, delay a discretionary purchase, ask a supplier for two extra weeks while the relationship is calm, arrange facility headroom before you need it. The same trough discovered in week nine <i>of</i> week nine can only be survived, and every option available is worse and more expensive.</p>

<p><b>Update it weekly, and compare to what actually happened.</b> The comparison is where the value compounds. Within a couple of months you learn which customers pay as promised, which suppliers can wait, and how far your own estimates drift — and the forecast stops being a spreadsheet and becomes a genuine instrument.</p>

<blockquote>WATCH-OUT: Two payments are habitually forgotten in first attempts and both are large: tax on its statutory due date, and the annual or quarterly items — insurance renewals, licence fees, bonuses. They arrive on schedule and are entirely predictable, and they still wreck forecasts because nobody wrote them down.</blockquote>

<p><b>Build it for the unit you actually run.</b> A branch manager forecasting the whole group's cash is doing somebody else's job badly. Forecast what you control: your takings, your local payments, your stock commitments. Where head office sweeps your bank daily, the forecast is still worth building — it becomes the evidence for what you need and when, which is a far stronger position than asking for money in the week you need it.</p>""",
 [C("Why thirteen weeks rather than three months?",
    ["It is easier to calculate", "Monthly views hide a business comfortable on the 1st and desperate on the 28th",
     "It matches the tax quarter", "Banks require it"], 1,
    "Weekly granularity is what makes a mid-month trough visible at all."),
  C("A customer has taken 60 days on their last six invoices. Your forecast should assume:",
    ["30 days, per their terms", "60 days, per their behaviour",
     "45 days as a compromise", "They will not pay"], 1,
    "A forecast built on terms rather than behaviour is a wish, and it makes next month a surprise."),
  C("A trough is visible in week nine of your forecast. The value of knowing now is:",
    ["The forecast will prove accurate", "Options are still cheap — a supplier or the bank can be asked calmly",
     "It can be excluded from reporting", "It confirms the budget"], 1,
    "The same trough met on the day can only be survived, and every remaining option is worse and more expensive.")]),

("Cash-heavy trading: discipline as financial control", 10, """<p>Much of Nigerian retail and distribution still moves substantial physical cash, and cash has a property no other asset has: <b>it is the only thing on the balance sheet that can leave without a transaction</b>. Stock can be stolen, but it leaves a hole somebody eventually counts. Cash simply is not there.</p>

<p>That makes cash handling a financial control rather than an operational chore, and it belongs in a finance module rather than being left to operations.</p>

<p><b>The chain of custody is the whole idea.</b> At every moment, exactly one named person is responsible for a given sum, and every handover is recorded and witnessed by both sides. Customer to cashier, cashier to supervisor at close, supervisor to safe, safe to banking. Break the chain anywhere and a loss becomes untraceable — not unprovable, untraceable, which is worse, because it means nobody can be cleared either.</p>

<p><b>Why banking speed is a control and not just convenience.</b> Cash sitting on a premises overnight is exposed to theft, to fire, and to borrowing that intends to be repaid. Same-day or next-day banking is not about efficiency; it removes the exposure entirely. A business with several days of takings on site is carrying a risk it has not priced.</p>

<p><b>The variance rule that most operations get wrong.</b> Overs matter as much as shorts. An instinct says a till that is over is a good problem. It is not — it means the process is not working, and a process that produces random overs will produce shorts too. Worse, a consistent small over can be somebody building a float to cover a later short. <b>Investigate both directions.</b></p>

<p><b>Delayed banking, and why it is the pattern to watch.</b> The classic loss in a cash business is not a dramatic theft. It is lapping: takings banked late, with today's receipts covering yesterday's shortfall, rolling forward indefinitely. Every individual day reconciles. The books balance. The only visible sign is a persistent gap between the date cash is taken and the date it reaches the bank — which is why <b>days-to-bank</b> is worth measuring as seriously as any financial ratio.</p>

<p><b>Reconciliation is the point where the control either exists or does not.</b> Till reading, physical count, banking slip, bank statement — four numbers that must agree, checked by somebody who did not handle the money. Self-reconciliation is not a control at all, however honest the individual, because it cannot clear them of suspicion any more than it can catch them.</p>

<blockquote>WATCH-OUT: The most reliable early indicator of a cash problem is not the size of variances but their pattern — the same till, the same shift, the same person, small amounts, consistently. Large one-off differences are usually errors. Small persistent ones are usually something else.</blockquote>

<p><b>Why this belongs to a manager rather than a cashier.</b> Every control here depends on somebody independent looking, and independence is a management arrangement rather than a procedure. A rota that puts the same supervisor with the same cashier every shift defeats a well-designed control on paper. So does the manager who signs the reconciliation without checking it — which is worse than not signing, because it converts a real control into documented assurance that nobody performed.</p>""",
 [C("Why does cash require different controls from stock?",
    ["It is worth more", "It can leave without any transaction and without leaving a countable hole",
     "It is harder to count", "It is not on the balance sheet"], 1,
    "A stock loss eventually shows up in a count. Cash simply is not there."),
  C("A till that is consistently slightly OVER is:",
    ["A good problem", "Evidence the process is not working, and possibly a float being built",
     "Not worth investigating", "Proof of careful cashiering"], 1,
    "A process producing random overs will produce shorts too, and a consistent over can be cover for a later short."),
  C("Which measure best exposes lapping — takings banked late and covered by later receipts?",
    ["Daily till variance", "Days between cash being taken and reaching the bank",
     "Gross margin", "Stock days"], 1,
    "Every individual day reconciles under lapping. The gap between taking and banking is the visible sign.")]),

("Seasonality and the trough after the peak", 10, """<p>Almost every trading business in Nigeria has a rhythm: the festive build, the January flatness, term-time and holiday patterns, salary week against month-end. Managing cash without accounting for that rhythm is managing an average that never actually occurs.</p>

<p><b>The peak is a cash event before it is a revenue event, and the order matters.</b></p>

<p>Consider a festive build. In October you buy heavily — cash goes out. In November stock sits at its highest and the bank at its lowest, and nothing has been earned yet. December sells it, and if trading is cash, money returns quickly; if it is credit, the money arrives in January or February. Meanwhile January's rent, salaries and tax fall due on schedule against the flattest trading month of the year.</p>

<p>So the sequence is: <b>spend, wait, sell, wait again, and meet fixed costs in the gap</b>. The most dangerous point is not the quiet season — it is the weeks immediately before the peak, when the money is committed and none of it has returned.</p>

<p><b>The trap that catches people twice.</b> The first is buying to the optimistic forecast. Stock bought for a peak that underperforms does not vanish; it sits, ties up cash, and is sold later at a markdown. The peak is over and the cash is still on the shelves.</p>

<p>The second is treating a good December as spare money. Cash that arrives after a peak has to carry the business through the trough that follows it. Distributing it, or committing it to something new, converts a normal seasonal pattern into a crisis by February.</p>

<p><b>What to do about it, concretely.</b> Build the thirteen-week forecast <i>through</i> the peak and out the other side, not up to it. The forecast that stops at the end of December is the one that misses the problem entirely, because December looks magnificent and January is where the difficulty lives.</p>

<p><b>Compare like seasons, never adjacent months.</b> December against November tells you nothing. December against last December tells you whether the peak was better, and by how much — and it is the only comparison worth putting in front of anyone.</p>

<p><b>The other rhythm, inside the month.</b> Salary week lifts consumer trading and drains business cash on the same date. In a business selling to consumers and paying staff on the 25th, the last week of the month is simultaneously the strongest for takings and the heaviest for outgoings. A monthly view averages these into invisibility; a weekly forecast shows them plainly.</p>

<blockquote>IMPLEMENTATION TIP: Keep last year's actual weekly cash pattern beside this year's forecast. Seasonality repeats far more reliably than most managers expect, and last year's shape is usually a better starting point than this year's optimism.</blockquote>

<p><b>The supplier conversation to have early.</b> If your peak requires buying two months ahead of selling, that funding gap is a structural feature rather than a one-off. Negotiate extended terms for the season specifically, in the quiet part of the year, with volume to offer in exchange. A supplier asked in August about December is having a commercial discussion; the same supplier asked in November is receiving a credit request, and answers it differently.</p>""",
 [C("In a festive build, the most dangerous point for cash is:",
    ["The quiet season after", "The weeks before the peak, when money is committed and none has returned",
     "The peak itself", "The start of the buying period"], 1,
    "Spend, wait, sell, wait again — and the fixed costs fall due in the gap."),
  C("Cash arriving after a strong December should be treated as:",
    ["Spare money for new commitments", "The funding that carries the business through January and February",
     "A distribution to owners", "Evidence the peak was over-stocked"], 1,
    "Committing it converts an ordinary seasonal pattern into a February crisis."),
  C("The only worthwhile comparison for a December is:",
    ["November", "The monthly average", "Last December", "The annual budget"], 2,
    "Adjacent months in a seasonal business compare different things and tell you nothing.")]),

("The weekly cash conversation", 10, """<p>This is the chapter to keep. Everything else explained how cash behaves; this is the routine that keeps a manager ahead of it, and it is deliberately short enough to survive a busy week.</p>

<p><b>Six questions, once a week, in this order.</b></p>

<p><b>1. What is actually in the bank, and what was it last week?</b> The real balance, not the ledger. Start from fact.</p>

<p><b>2. What is due out in the next fortnight that I cannot move?</b> Payroll, tax, loan instalments, rent. Knowing the immovable total is what makes everything else a choice rather than a scramble.</p>

<p><b>3. What is due in, and from whom specifically?</b> Not a total — names. "₦12,000,000 expected" is a hope; "₦7,000,000 from three customers, and I have spoken to two of them" is a position.</p>

<p><b>4. What is over ninety days, and what happened to it this week?</b> If the answer is nothing, that debt is ageing on your watch, and every week makes the conversation harder.</p>

<p><b>5. What did stock do?</b> Rising stock is cash leaving. It is the slowest-moving of the questions and the easiest to ignore for a quarter, which is exactly why it belongs on a weekly list.</p>

<p><b>6. Where is the low point in the next thirteen weeks, and what am I doing about it now?</b> The single most valuable question here, because it is the only one that is entirely about lead time.</p>

<p><b>Why weekly rather than monthly.</b> Because every remedy available to you gets worse with delay. A supplier asked for extra time three weeks ahead, while the relationship is calm, usually says yes. The same supplier asked on the due date says yes with conditions, or no. A bank approached with a forecast is a different conversation from a bank approached with an overdrawn account. Cash management is almost entirely about buying yourself time, and time is only available early.</p>

<p><b>The habit that separates managers who never have cash crises</b> is not superior forecasting. It is that they look weekly and act on small signals — one customer slipping, one stock line building, one week looking thin in six weeks' time — while the signals are still small enough to be handled by a phone call.</p>

<p><b>And the sentence worth carrying out of this module.</b> Profit is an opinion, cash is a fact. Both statements matter, and only one of them will be waiting when the salaries fall due.</p>

<blockquote>IMPLEMENTATION TIP: Put the six questions in a standing fifteen-minute slot with whoever handles your banking, same time every week. It is the highest-return quarter of an hour in a manager's calendar, and its value comes almost entirely from being unmissable rather than from being clever.</blockquote>

<p><b>What to escalate, and when.</b> Not every difficulty is yours to solve. A single slow customer is yours. A structural gap — the business cannot fund its own trading cycle at current volumes — belongs above you, and it belongs there early, with the thirteen-week forecast attached. Managers are rarely criticised for raising a funding requirement three months ahead with evidence. They are frequently criticised for raising it in the week it bites, and the numbers were available both times.</p>""",
 [C("Why does 'who owes it' beat 'how much is expected'?",
    ["It is easier to calculate", "A total is a hope; named debtors you have spoken to are a position",
     "It satisfies the auditor", "It affects the P&L"], 1,
    "Specific names can be chased. A total cannot."),
  C("Why is a weekly rhythm better than monthly for cash?",
    ["It is more accurate", "Every remedy gets worse with delay, and time is only available early",
     "Banks require it", "It reduces the forecast error"], 1,
    "A supplier asked three weeks ahead usually says yes; asked on the due date, yes with conditions or no."),
  C("The most valuable of the six weekly questions is:",
    ["What is in the bank", "What is due out", "Where the low point is in the next thirteen weeks and what is being done now",
     "What stock did"], 2,
    "It is the only one entirely about lead time, which is what every other remedy depends on.")]),
]


QUESTIONS = [
 Q("More businesses fail while:", ["Making losses", "Profitable", "Growing slowly", "Paying tax"], 1,
   "Growth, capital spending and drawings can consume more than the profit earned.", "Ch1 §1", "Profit versus cash"),
 Q("Which never appears on the P&L but drains cash?", ["Depreciation", "Loan principal repayments", "Cost of sales", "Rent"], 1,
   "Only the interest portion is a cost; the principal is a financing outflow.", "Ch1 §7", "Profit versus cash"),
 Q("A ₦9m vehicle bought outright hits this year's profit by about:", ["₦9m", "One year's depreciation", "Nothing ever", "₦9m less scrap value"], 1,
   "The bank feels it at once; the P&L spreads it over the asset's life.", "Ch1 §6", "Profit versus cash"),
 Q("Winning a large customer on 90-day terms is:", ["Purely good news", "A commercial win and a cash event arriving at different times", "A financing decision", "Neutral for cash"], 1,
   "The order comes first, the cash last, and the gap must be funded by somebody.", "Ch1 §9", "Profit versus cash"),
 Q("The right response to 'we had a great month' is to ask:", ["What the margin was", "What it did to stock and receivables", "What the tax charge was", "Whether costs were controlled"], 1,
   "A great month that consumed three months of cash is worth knowing on the day.", "Ch1 §10", "Profit versus cash"),
 Q("The cash flow statement is trusted because:", ["It is audited separately", "It depends on far fewer estimates than the other two", "It is prepared first", "It excludes working capital"], 1,
   "Cash either moved or it did not, and a bank statement settles it.", "Ch2 §2", "The cash flow statement"),
 Q("It answers which question?", ["Did we trade well", "What are we standing on", "Where did the money come from and go", "What will we earn next year"], 2,
   "The other two questions belong to the P&L and the balance sheet.", "Ch2 §4", "The cash flow statement"),
 Q("A negative total cash movement is:", ["Always bad", "Not necessarily bad — the section matters more than the sign", "Evidence of losses", "A financing failure"], 1,
   "Cash falling to buy a warehouse is a decision; cash falling from trading is a condition.", "Ch2 §7", "The cash flow statement"),
 Q("Read the cash flow statement by looking first at:", ["The total", "Operating cash", "Financing cash", "The closing balance"], 1,
   "The total without the operating line can hide a trading problem funded by borrowing.", "Ch2 §8", "The cash flow statement"),
 Q("Cash rising because a loan was drawn is:", ["The same as cash from customers", "Borrowed comfort", "Operating cash", "An investing inflow"], 1,
   "It raises the balance without the business having generated anything.", "Ch2 §7", "The cash flow statement"),
 Q("Which belongs in investing activities?", ["Interest paid", "Purchase of delivery vehicles", "Owner drawings", "Payments to suppliers"], 1,
   "Investing covers long-term assets bought and sold.", "Ch3 §5", "Operating investing financing"),
 Q("A ₦2m loan instalment of ₦1.6m principal and ₦400k interest appears:", ["Entirely in financing", "Entirely in operating", "Split across financing and operating", "Entirely in investing"], 2,
   "Principal is financing, interest is operating. The split confuses people constantly.", "Ch3 §8", "Operating investing financing"),
 Q("Capital spending consistently below depreciation indicates:", ["Strong cost control", "A business quietly consuming its asset base", "Overstated depreciation", "Healthy reinvestment"], 1,
   "Profit looks fine for years and the reckoning arrives all at once.", "Ch3 §6", "Operating investing financing"),
 Q("Positive operating, negative investing, negative financing describes:", ["A business surviving on borrowing", "Trading generating cash, some reinvested and some repaying debt", "A business being harvested", "A failing business"], 1,
   "It is the healthiest common shape.", "Ch3 §9", "Operating investing financing"),
 Q("Strong operating cash with near-zero investing over several years often means:", ["Excellent efficiency", "A business being harvested rather than built", "Assets are fully depreciated", "Suppliers are funding growth"], 1,
   "The sign appears in financing as drawings, and nowhere on the P&L.", "Ch3 §10", "Operating investing financing"),
 Q("In the reconciliation, depreciation is:", ["Subtracted", "Added back", "Ignored", "Split across sections"], 1,
   "It reduced profit and moved no money.", "Ch4 §3", "Reconciling profit to cash"),
 Q("Stock rose ₦14m. In the reconciliation you:", ["Add ₦14m", "Subtract ₦14m", "Ignore it", "Add it to investing"], 1,
   "An asset going up uses cash.", "Ch4 §5", "Reconciling profit to cash"),
 Q("Payables rose ₦5m. In the reconciliation you:", ["Subtract ₦5m", "Add ₦5m", "Ignore it", "Treat it as financing"], 1,
   "A liability going up provides cash — suppliers funded you.", "Ch4 §5", "Reconciling profit to cash"),
 Q("Profit ₦11.6m, depreciation ₦4m, stock +₦14m, debtors +₦13m, creditors +₦5m gives operating cash of:", ["+₦15.6m", "−₦6.4m", "−₦18m", "+₦2.6m"], 1,
   "11.6 + 4 − 14 − 13 + 5 = −6.4m.", "Ch4 §7", "Reconciling profit to cash"),
 Q("The two rules that carry most cash flow reading are:", ["Revenue up cash up; costs up cash down", "Asset up cash down; liability up cash up", "Profit up cash up; loss down cash down", "Stock up margin down; debtors up revenue up"], 1,
   "They will get you through ninety per cent of it.", "Ch4 §9", "Reconciling profit to cash"),
 Q("Tax in the reconciliation should be:", ["The charge in the P&L", "The amount actually paid", "Ignored", "Added back like depreciation"], 1,
   "The charge and the payment run on different bases and timing.", "Ch4 §6", "Reconciling profit to cash"),
 Q("Revenue up 29% and stock up 58% means the excess is:", ["Entirely the cost of growth", "Partly lost efficiency, and recoverable without selling less", "A stock write-down", "A supplier price rise"], 1,
   "Growth explains part; the rest is holding stock less efficiently.", "Ch5 §3", "Working capital movements"),
 Q("Debtor days rose from 52 to 67 on ₦180m revenue. Roughly how much extra is tied up?", ["₦2.5m", "₦7.4m", "₦15m", "₦493,000"], 1,
   "15 days at about ₦493,000 a day ≈ ₦7.4m sitting in customers' businesses.", "Ch5 §5", "Working capital movements"),
 Q("Turning days into naira matters because:", ["It is more accurate", "A statistic gets nodded at; a naira figure gets a decision", "Auditors require it", "It changes the ratio"], 1,
   "Same fact, entirely different reception in a meeting.", "Ch5 §6", "Working capital movements"),
 Q("Reducing stock across the board rather than targeting slow lines risks:", ["Higher supplier prices", "Stockouts that cost margin and customers invisibly", "A write-down", "Longer debtor days"], 1,
   "Aim at slow and dead lines, never uniformly.", "Ch5 §8", "Working capital movements"),
 Q("Which lever is least connected to the cash cycle?", ["Collecting faster", "Reducing slow stock", "Taking full supplier terms", "Cutting overheads"], 3,
   "The money is on the shelves and in customers' accounts, not in the overheads.", "Ch5 §9", "Working capital movements"),
 Q("A cash forecast should be built:", ["Monthly for twelve months", "Weekly for thirteen weeks", "Daily for a year", "Quarterly"], 1,
   "Monthly hides a business comfortable on the 1st and desperate on the 28th.", "Ch6 §2", "Cash forecasting"),
 Q("Receipts should be forecast on:", ["Agreed terms", "Actual customer payment behaviour", "The average of both", "The sales budget"], 1,
   "A forecast built on terms rather than behaviour is a wish.", "Ch6 §6", "Cash forecasting"),
 Q("The main purpose of a cash forecast is:", ["Accuracy", "Lead time", "Bank compliance", "Budget setting"], 1,
   "A trough seen early can be managed; discovered late it can only be survived.", "Ch6 §7", "Cash forecasting"),
 Q("Which payments are most often forgotten in a first forecast?", ["Payroll and rent", "Tax due dates and annual items like insurance renewals", "Supplier invoices", "Utilities"], 1,
   "Entirely predictable, on schedule, and still routinely omitted.", "Ch6 §9", "Cash forecasting"),
 Q("Comparing forecast to actual each week mainly teaches you:", ["Whether the bank is accurate", "Which customers pay as promised and how far your estimates drift", "The tax position", "Gross margin"], 1,
   "That is where the value compounds and the forecast becomes an instrument.", "Ch6 §8", "Cash forecasting"),
 Q("Cash needs different controls from stock because:", ["It is more valuable", "It can leave without a transaction and without a countable hole", "It is harder to store", "It is taxed differently"], 1,
   "A stock loss eventually surfaces in a count.", "Ch7 §1", "Cash handling discipline"),
 Q("A till consistently slightly over should be:", ["Welcomed", "Investigated like a shortage", "Ignored below a threshold", "Banked separately"], 1,
   "A process producing overs produces shorts, and a steady over can be a float for a later short.", "Ch7 §5", "Cash handling discipline"),
 Q("Lapping is best exposed by measuring:", ["Daily variance", "Days between takings and banking", "Gross margin", "Staff numbers"], 1,
   "Every individual day reconciles under lapping; the delay is the visible sign.", "Ch7 §6", "Cash handling discipline"),
 Q("Reconciliation is a control only when performed by:", ["The cashier who handled it", "Somebody who did not handle the money", "The bank", "The auditor annually"], 1,
   "Self-reconciliation cannot clear the individual any more than it can catch them.", "Ch7 §7", "Cash handling discipline"),
 Q("The most reliable early indicator of a cash problem is:", ["Large one-off differences", "Small persistent differences on the same till or shift", "Total variance value", "Banking frequency"], 1,
   "Large one-offs are usually errors; small persistent ones usually are not.", "Ch7 §8", "Cash handling discipline"),
 Q("In a festive build, cash is most exposed:", ["In January", "In the weeks before the peak", "During the peak", "After collections arrive"], 1,
   "The money is committed to stock and none of it has returned.", "Ch8 §3", "Seasonality"),
 Q("Cash arriving after a strong December should:", ["Be distributed", "Fund the trough that follows", "Be reinvested immediately", "Repay all debt"], 1,
   "Committing it turns a normal season into a February crisis.", "Ch8 §6", "Seasonality"),
 Q("A thirteen-week forecast built in November should run:", ["To the end of December", "Through the peak and out the other side", "To the year end", "Only to the peak"], 1,
   "December looks magnificent; January is where the difficulty lives.", "Ch8 §7", "Seasonality"),
 Q("Profit is an opinion and cash is:", ["A forecast", "A fact", "An estimate", "A ratio"], 1,
   "Both statements matter, and only one will be waiting when salaries fall due.", "Ch9 §10", "The weekly routine"),
]


QUESTIONS += [
 Q("Which of the six weekly questions is entirely about lead time?",
   ["What is in the bank", "What is due out", "What is due in",
    "Where the low point falls in the next thirteen weeks"], 3,
   "Every other remedy depends on having time, and time is only available early.", "Ch9 \u00a78", "The weekly routine"),
 Q("Why is a list of named debtors better than a total expected?",
   ["It is more conservative", "It is a position that can be chased rather than a hope",
    "It matches the ledger", "It is required by the bank"], 1,
   "Specific names can be actioned; a total cannot.", "Ch9 \u00a74", "The weekly routine"),
 Q("A debt over ninety days with nothing done this week means:",
   ["It is under control", "It should be written off",
    "It is ageing on your watch and the conversation only gets harder", "It belongs to finance"], 2,
   "Every week of delay reduces both the chance of collection and the customer's willingness.", "Ch9 \u00a76", "The weekly routine"),
 Q("Managers who avoid cash crises mainly differ by:",
   ["Better forecasting models", "Larger overdraft facilities",
    "Tighter cost control", "Acting weekly on small signals while a phone call still fixes them"], 3,
   "One customer slipping, one stock line building, one thin week ahead \u2014 handled while small.", "Ch9 \u00a79", "The weekly routine"),
 Q("Extended seasonal supplier terms are best negotiated:",
   ["In the week the stock is needed", "In the quiet part of the year, with volume to offer",
    "After the peak has passed", "Through the bank"], 1,
   "Asked in August about December it is a commercial discussion; asked in November it is a credit request.",
   "Ch8 \u00a710", "Seasonality"),
 Q("A branch manager's cash forecast should cover:",
   ["The whole group", "Nothing \u2014 it is head office work",
    "The unit they control, as evidence of what they need and when", "Only the annual budget"], 2,
   "Far stronger than asking for money in the week you need it.", "Ch6 \u00a710", "Cash forecasting"),
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
    rebalance(QUESTIONS, "finance:profit_cash:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:profit_cash:checks")

    mod = {
        "title": "Profit Is Not Cash",
        "desc": ("Why more businesses fail while profitable than while making losses. The "
                 "cash flow statement, the reconciliation from profit to operating cash, "
                 "what growth actually costs, a thirteen-week forecast you build yourself, "
                 "cash handling as a financial control, and the weekly conversation that "
                 "keeps a manager ahead of it."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    path = "academy_finance_data.json"
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
