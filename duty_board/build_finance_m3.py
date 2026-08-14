#!/usr/bin/env python3
"""Build the Reading the Balance Sheet module into academy_finance_data.json.

Module 3 of Accounting & Finance for Non-Finance Managers. Completes the
reading spine begun in module 2: the P&L says how the period went, the balance
sheet says what the business is standing on.

MERGES into the existing data file rather than replacing it, so building one
module never destroys another. build_finance_m2.py was corrected to do the same
after this file was written — a builder that clobbers its siblings is a trap
waiting for whoever rebuilds in six months.

Run from the app package directory:  python3 build_finance_m3.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "read_bs"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("What you own, what you owe, and what is left", 9, """<p>The profit and loss account covers a period: what happened between the first of the month and the last. The balance sheet is different in kind. It is a photograph taken at one instant — the close of business on the last day — showing what the business owns, what it owes, and the difference between the two.</p>

<p>That difference is what belongs to the owners, and it is the only number on the page that nobody chooses directly. It falls out of the other two.</p>

<p><b>Three blocks, and that is the whole structure.</b></p>

<p><b>Assets</b> are things of value the business controls: cash in the bank, stock on the shelves, money customers owe you, vehicles, fittings, the building if you own it.</p>

<p><b>Liabilities</b> are obligations to other people: suppliers awaiting payment, a bank loan, tax owed, staff salaries accrued but not yet paid, a customer's deposit for goods you have not delivered.</p>

<p><b>Equity</b> is what remains: assets less liabilities. It is the owners' stake — what would be left in theory if everything were sold at book value and every debt settled.</p>

<p><b>Why a manager should care about a statement they will never prepare.</b> Because the P&L can only tell you half the story, and the more comfortable half. A business can report a profit every month for two years while its stock swells, its customers stop paying and its supplier terms quietly stretch. Every one of those developments is invisible on the P&L and unmistakable on the balance sheet.</p>

<p>The two statements are also linked, tightly. The profit you earned this month arrives on the balance sheet as an increase in equity. If a business made ₦8,000,000 profit and took nothing out, equity rose ₦8,000,000. Where it went — into stock, into receivables, into the bank, into repaying a loan — is what the balance sheet tells you and the P&L cannot.</p>

<p><b>The instant matters more than people expect.</b> Because it is a photograph, a balance sheet can be dressed for the picture. Paying suppliers on the 2nd rather than the 30th, or pushing a delivery over month-end, changes what the statement shows without changing anything real about the business. This is not usually sinister; it is just worth knowing that a single balance sheet is a moment, and a trend of them is evidence.</p>

<p><b>What good reading looks like.</b> Nobody sensible reads a balance sheet top to bottom. You read it for change: what is bigger than last quarter, what is smaller, and what that movement says about where the money went. A manager who can do that in ten minutes is doing something most people in the building cannot.</p>

<blockquote>IMPLEMENTATION TIP: Always read a balance sheet next to the previous one. A single column tells you the position; two columns tell you the direction, and direction is what you can act on.</blockquote>

<p><b>One warning about the word "worth".</b> Equity is not what the business would sell for. It is assets at book value less liabilities, and book value is history — what was paid, less what has been charged since. A business with a well-known name, a trained team and a loyal customer base carries none of that on the page, while a business with obsolete stock carries it at cost until somebody writes it down. Equity is a useful number and a poor valuation.</p>""",
 [C("A balance sheet describes:",
    ["A period of trading", "A single moment — the close of the last day", "The next twelve months", "The tax year"], 1,
    "The P&L covers a period; the balance sheet is a photograph at one instant, which is why a single one is a moment and a series is evidence."),
  C("A business made ₦8m profit and distributed nothing. On the balance sheet:",
    ["Cash rises ₦8m", "Equity rises ₦8m", "Liabilities fall ₦8m", "Nothing changes"], 1,
    "Profit arrives as an increase in equity. Where the money actually went — stock, receivables, bank, debt repayment — is the interesting part."),
  C("Paying suppliers on the 2nd instead of the 30th changes:",
    ["The business's real position", "What the month-end photograph shows",
     "Reported profit", "Nothing at all"], 1,
    "It is a moment, and moments can be dressed. Usually not sinister, but a reason to read the trend rather than one column.")]),

("The accounting equation as an idea, not a formula", 9, """<p>Assets equal liabilities plus equity. It is stated as a formula, which makes it look like arithmetic to be memorised. It is better understood as a sentence about the world: <b>everything the business has, somebody has a claim on.</b></p>

<p>Either an outsider has the claim — a supplier, a lender, the tax authority — or the owners do. There is no third possibility, which is why the two sides can never disagree.</p>

<p><b>Follow one transaction and it stops being abstract.</b></p>

<p>You buy ₦5,000,000 of stock on credit. Assets rise ₦5,000,000, because you now hold the stock. Liabilities rise ₦5,000,000, because the supplier is owed. Equity does not move — you are no better or worse off, you are simply larger on both sides. This is why buying stock does not make you richer, however much fuller the warehouse looks.</p>

<p>Now you sell that stock for ₦7,000,000 cash. Cash rises ₦7,000,000, stock falls ₦5,000,000, so assets rise ₦2,000,000 net. Liabilities are unchanged. Equity therefore rises ₦2,000,000 — and that ₦2,000,000 is exactly the gross profit the P&L reported. The two statements agreed without anybody making them agree.</p>

<p><b>Now the transaction that catches people out.</b> You pay the supplier the ₦5,000,000. Cash falls, so assets fall ₦5,000,000. Liabilities fall ₦5,000,000. Equity does not move at all — and neither does profit. Paying a bill is not a cost. The cost happened when the goods were sold; paying is settlement.</p>

<p>That single point resolves most of the confusion managers have about why the bank balance and the profit figure refuse to agree.</p>

<p><b>The one place equity moves without profit.</b> When owners put money in, or take money out. An owner injecting ₦10,000,000 raises cash and raises equity, and no profit was earned. An owner drawing ₦3,000,000 reduces both, and no loss was made. Drawings are not an expense, and a business that treats them as one will understate its own performance.</p>

<p><b>Why this is worth twenty minutes of your life.</b> Because once you can trace a transaction through both sides, you stop needing to be told what a balance sheet movement means — you can work it out. Stock up and payables up is buying on credit. Stock up and cash down is buying with your own money. The same increase in stock, two completely different stories, and the balance sheet distinguishes them where the P&L shows neither.</p>

<blockquote>IMPLEMENTATION TIP: When any balance sheet number moves and you want to know what happened, ask which other number moved with it. Assets and liabilities together means an outsider funded it. Assets and equity together means you earned it or the owners put it in.</blockquote>

<p><b>A note on why this never fails to balance.</b> Every transaction touches at least two places, and always in a way that preserves the equation. That is the whole of double-entry, and it is why a balance sheet that does not balance is not a business problem but a bookkeeping one. What it does not guarantee is that the numbers are right — a balance sheet balances perfectly well with the wrong stock figure in it, because the error simply appears on both sides.</p>""",
 [C("You buy ₦5m of stock on credit. Equity:",
    ["Rises ₦5m", "Falls ₦5m", "Does not move", "Rises by the expected margin"], 2,
    "Assets and liabilities both rise. You are larger on both sides and no better off — which is why a full warehouse is not wealth."),
  C("You pay a supplier ₦5m you already owed. Profit:",
    ["Falls ₦5m", "Is unaffected — the cost occurred when the goods were sold", "Rises ₦5m", "Falls by the margin"], 1,
    "Paying a bill is settlement, not cost. This one point resolves most confusion about why cash and profit disagree."),
  C("Stock rose and payables rose by the same amount. This tells you:",
    ["The business earned it", "An owner injected funds",
     "The stock was bought on supplier credit", "Stock was written down"], 2,
    "Assets and liabilities moving together means an outsider funded the increase.")]),

("Current and non-current, and why the split matters", 9, """<p>Both assets and liabilities are split in two, and the dividing line is time: <b>within twelve months, or beyond</b>.</p>

<p><b>Current assets</b> are cash or things expected to become cash within a year: bank balances, stock, money owed by customers, prepayments.</p>

<p><b>Non-current assets</b> are held to be used rather than sold: vehicles, equipment, fittings, buildings, software.</p>

<p><b>Current liabilities</b> fall due within a year: suppliers, tax, accrued salaries, the next twelve months of a loan.</p>

<p><b>Non-current liabilities</b> fall due later: the rest of that loan, long leases.</p>

<p><b>The split exists to answer one question: can this business pay what is about to fall due?</b> Nothing else on the balance sheet answers it, and it is the question that determines whether a business survives the next quarter regardless of how profitable it is.</p>

<p><b>Working capital</b> is current assets less current liabilities. Current assets of ₦46,000,000 against current liabilities of ₦31,000,000 gives ₦15,000,000 of working capital, and a current ratio of 1.5. A ratio below 1 means the things falling due within the year exceed the things becoming cash within the year — which does not guarantee failure, but does mean the business is relying on something not yet on the page.</p>

<p><b>Where the crude reading goes wrong, and it matters.</b> Not all current assets are equally current. Cash is cash. Receivables become cash when customers pay, which for a distributor with slow debtors may be ninety days. Stock becomes cash only after it is sold <i>and then</i> collected — and slow-moving stock may never become cash at all.</p>

<p>So a business with a comfortable current ratio built almost entirely from stock is not comfortable. The <b>quick ratio</b> — current assets excluding stock, over current liabilities — asks the harder question: if nothing else sold from today, could we meet what falls due? For a stock-heavy retailer the two ratios can differ enormously, and the second is the honest one.</p>

<p><b>The trap on the liability side.</b> The current portion of a long-term loan sits in current liabilities, and people reading quickly treat the loan as long-term because that is how they think of it. The twelve months of instalments ahead are due within twelve months, and the business must find them from somewhere.</p>

<blockquote>WATCH-OUT: A rising current ratio is not automatically good news. If it is rising because stock is piling up and customers are paying more slowly, the ratio is improving while the business gets weaker. Always ask which component moved.</blockquote>

<p><b>Where the twelve-month rule gets interesting.</b> Stock that will not sell within a year is still shown as current, because that is the convention for the category rather than a judgement about the item. So a business sitting on dead stock reports it among the assets expected to become cash within twelve months, and the ratio inherits the optimism. This is another reason the ageing profile matters more than the classification.</p>""",
 [C("The line dividing current from non-current is:",
    ["Value", "Whether it is physical", "Twelve months", "Whether it was bought on credit"], 2,
    "Current means expected to become cash, or to fall due, within a year."),
  C("Current assets ₦46m, current liabilities ₦31m. The current ratio is:",
    ["1.5", "0.67", "15", "2.0"], 0,
    "46 ÷ 31 ≈ 1.5. Working capital is the ₦15m difference; the ratio is the relationship."),
  C("A comfortable current ratio made up almost entirely of stock is:",
    ["Reassuring", "Weaker than it looks — stock becomes cash only after it sells and is collected",
     "Impossible", "Evidence of good buying"], 1,
    "The quick ratio strips stock out and asks the harder question, which for a stock-heavy retailer is the honest one.")]),

("Inventory: the number that moves your margin", 9, """<p>For a retail or distribution business, stock is usually the largest current asset and the one most capable of misleading. It is also the point where the balance sheet and the P&L are joined at the hip — which is why an error here damages both statements at once.</p>

<p><b>Stock is carried at cost, not at what you hope to sell it for.</b> ₦30,000,000 of stock means ₦30,000,000 was spent acquiring and preparing it. The profit is recognised when it sells, not when it arrives.</p>

<p>The exception matters: if stock is worth <i>less</i> than it cost — damaged, expired, obsolete, superseded — it must be written down to what it will actually fetch. Accounts may never carry stock above its recoverable value. That rule is what turns a slow-moving line into a P&L event, eventually.</p>

<p><b>The joint that makes this chapter important.</b> As module 2 showed, cost of sales is opening stock plus purchases less closing stock. Closing stock is a balance sheet number. So <b>every naira of error in the stock figure is a naira of error in profit</b>, in the opposite direction.</p>

<p>Count ₦2,000,000 too much and cost of sales is ₦2,000,000 too low, profit ₦2,000,000 too high, and the balance sheet ₦2,000,000 too strong. One mistake, two wrong statements, and nothing anywhere flags it.</p>

<p>This is why the stock count is not an inventory chore. It is the single largest determinant of whether your accounts are true.</p>

<p><b>What to look at, beyond the number.</b> Stock rising faster than sales is the classic warning: money converting into goods faster than goods convert into money. Measure it as <b>stock days</b> — stock divided by cost of sales, times 365. Stock of ₦30,000,000 on cost of sales of ₦180,000,000 is 61 days. If that was 45 days a year ago, roughly ₦8,000,000 of cash has quietly moved onto the shelves.</p>

<p><b>Ageing beats totals.</b> A stable total can hide a rotting composition: fast lines thinning while dead stock accumulates underneath. Ask for stock by age, and treat anything older than a defined threshold as a decision waiting to be made rather than an asset.</p>

<p><b>And the quiet one.</b> A business that never writes anything off is not a business with no obsolete stock — it is a business not looking. Zero write-offs year after year is a finding, not a clean bill of health.</p>

<blockquote>IMPLEMENTATION TIP: Two numbers, monthly, on one line: stock days and the value of stock older than your threshold. Almost everything that goes wrong with inventory shows up in one of them long before it shows up in profit.</blockquote>

<p><b>One thing that flatters stock quietly.</b> Goods held on consignment, or bought under an arrangement where they can be returned, may sit on your shelves without being yours. Conversely, stock you own may sit in a customer's warehouse. The physical location and the accounting ownership are different questions, and businesses that count what they can see rather than what they own get both the stock figure and the cost of sales wrong.</p>""",
 [C("Stock is carried on the balance sheet at:",
    ["Expected selling price", "Cost, unless it is worth less than cost",
     "Cost plus the standard margin", "The insured value"], 1,
    "Profit is recognised when it sells. Stock worth less than cost must be written down."),
  C("Stock ₦30m, cost of sales ₦180m. Stock days are roughly:",
    ["6", "61", "167", "365"], 1,
    "30 ÷ 180 × 365 ≈ 61 days. Rising stock days means cash converting into goods faster than goods convert into cash."),
  C("A business reporting zero stock write-offs for three years is most likely:",
    ["Exceptionally well run", "Not looking", "Understating its stock", "Buying only fast lines"], 1,
    "Every stockholding business has obsolescence. Zero write-offs is a finding rather than a clean bill of health.")]),

("Receivables: revenue you have not been paid for", 9, """<p>Receivables — debtors — are sales you have made and not yet collected. As module 2 established, the sale became revenue on delivery. The balance sheet is where the unpaid consequence sits, and it grows quietly while the P&L looks healthy.</p>

<p><b>The measure that matters is time, not size.</b> Debtor days: receivables divided by revenue, times 365. Receivables of ₦24,000,000 on revenue of ₦146,000,000 is about 60 days. Whether that is good depends entirely on your terms — 60 days against 30-day terms means half your customers are late, and the business is financing them.</p>

<p><b>That phrase is worth sitting with. You are financing your customers.</b> Every naira in receivables is a naira you have spent on goods and not recovered. A distributor with ₦24,000,000 out has, in effect, lent that to its customers interest-free — and may itself be paying interest on an overdraft to do it.</p>

<p><b>Ageing is where the truth is.</b> A total tells you almost nothing; the split tells you everything. ₦24,000,000 made up of ₦20,000,000 under thirty days and ₦4,000,000 over ninety is a healthy book with a small problem. The same ₦24,000,000 made up of ₦9,000,000 current and ₦15,000,000 over ninety is a serious one dressed as an ordinary one.</p>

<p>Debt over ninety days rarely improves with age. The probability of collection falls steeply, and every month of delay makes the conversation harder and the customer less willing.</p>

<p><b>The provision, and what it admits.</b> Because some receivables will not be collected, accounts carry a provision for doubtful debts, which reduces the asset and reduces profit. It is an estimate, and as module 2's chapter on judgement noted, it is a favourite place to flatter a result. A provision that stays flat while the ageing deteriorates is not prudence; it is postponement.</p>

<p><b>Concentration is the risk nobody measures.</b> Ask what share of receivables sits with the largest customer. If one name is 40% of the book, that customer's difficulty is your difficulty, and it will arrive without warning. A well-spread book of the same size is a materially different exposure.</p>

<p><b>What a manager should actually do.</b> Read the ageing monthly, not the total. Chase at the point the invoice becomes overdue rather than when it becomes alarming. And treat a customer who is slow but growing as a decision rather than a success — more sales to somebody who does not pay makes the position worse, not better.</p>

<p><b>A distinction worth keeping clear.</b> A customer who disputes an invoice is not the same as a customer who cannot pay, and both sit in the same ageing bucket. Disputes are usually a service or paperwork failure on your side — a wrong price, a short delivery, a missing document — and they are fixable in days by somebody with authority. Grouping them with genuine credit problems means the fixable ones age alongside the unfixable, and nobody separates them until the total is alarming.</p>

<blockquote>WATCH-OUT: Revenue growth and receivables growth arriving together, with receivables growing faster, is one of the most reliable early warnings in business. It usually means terms are being stretched to win the sales — and the sales are real while the cash is not.</blockquote>""",
 [C("Receivables ₦24m on revenue ₦146m gives debtor days of roughly:",
    ["16", "60", "120", "6"], 1,
    "24 ÷ 146 × 365 ≈ 60 days. Against 30-day terms that means the business is financing its customers."),
  C("₦24m of receivables: which composition is the serious problem?",
    ["₦20m current, ₦4m over 90 days", "₦9m current, ₦15m over 90 days",
     "₦24m spread evenly", "Both are equally healthy"], 1,
    "Age, not size, carries the meaning. Debt over ninety days rarely improves with age."),
  C("Revenue growing while receivables grow faster usually means:",
    ["Excellent commercial performance", "Terms are being stretched to win the sales",
     "Customers are paying early", "A pricing improvement"], 1,
    "The sales are real; the cash is not. It is one of the most reliable early warnings there is.")]),

("Payables: the money you are holding", 9, """<p>Payables — creditors — are what you owe suppliers for goods and services already received. It is the mirror of receivables, and the only large balance sheet line where <i>bigger</i> can be better.</p>

<p><b>Supplier credit is free funding, and it is the cheapest a business will ever get.</b> If a supplier lets you pay in thirty days, they have financed your stock for thirty days at no interest. Every day of supplier credit is a day you do not need an overdraft.</p>

<p><b>Creditor days</b> measure it: payables divided by cost of sales, times 365. Payables of ₦27,000,000 on cost of sales of ₦180,000,000 is about 55 days.</p>

<p><b>Put the three together and you have the cash cycle.</b> Stock days plus debtor days less creditor days. On our numbers: 61 + 60 − 55 = 66 days. That is how long the business funds its own trading before the money comes back — and it is the number that determines how much cash growth will consume.</p>

<p>Because that is the counter-intuitive part: <b>growth eats cash</b>. If every ₦1,000,000 of extra monthly sales requires 66 days of funding, doubling sales does not double comfort. It doubles the hole to be funded, and profitable businesses fail this way far more often than unprofitable ones fail from losses.</p>

<p><b>But payables have a limit, and it is not the terms.</b> It is the relationship. Stretching suppliers works until it does not: supply gets slower, priority goes elsewhere, prices harden, and eventually deliveries stop at the moment you most need them. Rising creditor days can mean sharp treasury management or a business quietly running out of money, and the balance sheet cannot tell you which. The supplier can.</p>

<p><b>Watch for the tell.</b> Creditor days rising while cash falls and receivables lengthen is not treasury policy. It is a business paying late because it cannot pay on time, and the three moving together is the signature.</p>

<p><b>One number that hides here.</b> Payables often include accrued expenses and tax not yet remitted. Tax collected and not yet paid over is not working capital, however much it looks like it — it is somebody else's money sitting in your account with a due date attached. Businesses that fund operations from it discover the cost when the due date arrives.</p>

<blockquote>IMPLEMENTATION TIP: Track the cash cycle as one monthly number. A business improving margin while its cash cycle lengthens is not necessarily improving, and the two facts sit in different statements — so nobody notices unless somebody puts them side by side.</blockquote>

<p><b>The other direction is worth naming too.</b> Paying suppliers faster than you need to is not virtue; it is lending them your money. If a supplier offers thirty days and you pay in ten, you have funded twenty days of their business out of your own working capital for nothing in return. Unless there is a settlement discount that beats your cost of money, take the terms you were given — that is what they are for.</p>""",
 [C("Payables ₦27m on cost of sales ₦180m gives creditor days of roughly:",
    ["15", "55", "150", "6.7"], 1,
    "27 ÷ 180 × 365 ≈ 55 days. Every day of supplier credit is a day you do not need an overdraft."),
  C("Stock days 61, debtor days 60, creditor days 55. The cash cycle is:",
    ["176 days", "66 days", "56 days", "5 days"], 1,
    "61 + 60 − 55 = 66 days of self-funded trading. It is what determines how much cash growth will consume."),
  C("Creditor days rising, cash falling, receivables lengthening together indicates:",
    ["Sharp treasury management", "A business paying late because it cannot pay on time",
     "Improved supplier terms", "Seasonal buying"], 1,
    "Either reading is possible for creditor days alone. All three moving together is the signature of trouble.")]),

("Fixed assets, and the balance sheet that ages", 9, """<p>Non-current assets — property, vehicles, equipment, fittings, software — are held to be used rather than sold, and they are the part of the balance sheet most likely to be quietly wrong.</p>

<p><b>Two numbers, and the gap between them is the point.</b> Cost is what you paid. Accumulated depreciation is how much has been charged against profit since. The difference, net book value, is what appears on the balance sheet.</p>

<p>Vehicles at ₦24,000,000 cost with ₦19,200,000 accumulated depreciation show ₦4,800,000 net. That does not mean they are worth ₦4,800,000. It means ₦4,800,000 of the original cost has yet to be charged to profit. Net book value is an unexpired cost, not a valuation, and treating it as one is the commonest error in reading this section.</p>

<p><b>Read the ratio, not the number.</b> Net book value against cost tells you how used-up the asset base is. ₦4,800,000 against ₦24,000,000 means the fleet is 80% depreciated — old, near replacement, and about to demand cash that nothing in the accounts has set aside. A business with heavily depreciated assets and a healthy profit is often a business with an unfunded replacement bill approaching.</p>

<p><b>Additions and disposals tell the story of intent.</b> Rising fixed assets means the business is investing. Falling means it is not replacing, which may be prudence in a downturn or may be a business slowly consuming its own capacity. The balance sheet shows which is happening; only management can say which was intended.</p>

<p><b>Revaluation, where property is involved.</b> Some businesses revalue land and buildings upward, which raises assets and raises equity through a reserve rather than through profit. Nothing was earned and no cash arrived. It can materially change how strong a balance sheet looks, so when equity jumps, check whether the business earned it or revalued it.</p>

<p><b>The asset that is not there.</b> Leased premises, leased vehicles, rented equipment — depending on treatment these may not appear as assets at all, while the obligation to pay for them is entirely real. Two businesses operating identically, one owning and one leasing, present very different balance sheets. Comparing them on asset totals compares financing choices rather than operations.</p>

<blockquote>WATCH-OUT: A large "assets under construction" or "capital work in progress" balance that does not move for several periods is worth asking about. It is where stalled projects sit, unfinished and undepreciated, and it can hold real money doing nothing while looking like an asset.</blockquote>

<p><b>And one practical check.</b> Ask whether the fixed asset register has been walked recently — whether somebody has physically confirmed the assets still exist and are still in use. Registers accumulate items that were scrapped, stolen or replaced years ago, and every one of those is carrying a book value and a depreciation charge for something that is not there. It is unglamorous work and it is the only way the number becomes trustworthy.</p>""",
 [C("Vehicles: cost ₦24m, accumulated depreciation ₦19.2m. Net book value means:",
    ["They are worth ₦4.8m", "₦4.8m of the original cost has yet to be charged to profit",
     "₦4.8m is available to spend", "They can be sold for ₦4.8m"], 1,
    "Net book value is an unexpired cost, not a valuation. Treating it as market value is the commonest error here."),
  C("A fleet 80% depreciated with healthy profit most likely indicates:",
    ["Efficient asset use", "An unfunded replacement bill approaching",
     "Assets are overvalued", "Depreciation is too high"], 1,
    "Depreciation records use; it sets nothing aside. The replacement has to be funded separately."),
  C("Equity rose sharply with no corresponding profit. A likely explanation is:",
    ["A stock write-off", "A property revaluation or owner injection",
     "Higher depreciation", "Longer supplier terms"], 1,
    "Revaluation raises assets and equity through a reserve. Nothing was earned and no cash arrived.")]),

("Equity: what the owners actually have", 9, """<p>Equity is the residual — assets less liabilities — and it is usually shown in parts, each of which answers a different question about where the owners' stake came from.</p>

<p><b>Share capital, or capital introduced</b>, is what the owners put in. It rises only when they put in more.</p>

<p><b>Retained earnings</b> are every naira of profit the business has ever made and not distributed, accumulated since it began. This is the line that connects the two statements permanently: each period's profit lands here, each dividend or drawing leaves from here.</p>

<p><b>Reserves</b> cover amounts set aside for particular reasons — a revaluation reserve being the common one.</p>

<p><b>The most useful thing this section tells you</b> is how the business was built. Equity of ₦120,000,000 made up of ₦100,000,000 introduced and ₦20,000,000 retained is a business funded largely by its owners. The same ₦120,000,000 made up of ₦10,000,000 introduced and ₦110,000,000 retained is a business that funded itself out of its own trading. Both look identical on the total; they are entirely different animals.</p>

<p><b>Negative retained earnings</b> — accumulated losses — mean the business has lost more since inception than it has made. It can still be trading perfectly well today; the line is history, not a verdict on the present. But it does mean any current profit is repairing past damage before it builds anything.</p>

<p><b>Drawings and dividends are the line to watch closely in an owner-managed business.</b> They are not costs and never appear on the P&L, so a business can report healthy profit every year while the owners extract more than it earns, and equity falls steadily. The P&L will look fine throughout. Only the balance sheet shows the business getting weaker — which is precisely why an owner reading only the P&L can be surprised by their own bank.</p>

<p><b>Gearing, in one sentence.</b> Compare debt to equity. A business with ₦80,000,000 of borrowings against ₦40,000,000 of equity is carrying twice as much of other people's money as its own, which magnifies both good years and bad ones. There is no correct level, but there is a level at which a poor quarter stops being uncomfortable and starts being existential.</p>

<blockquote>IMPLEMENTATION TIP: Equity movement over a year is one of the fastest health checks available. Rising equity with no owner injection means the business earned it. Falling equity with profit reported means it is being taken out faster than it is being made.</blockquote>

<p><b>Why gearing is a temperament question as much as a financial one.</b> Debt magnifies. A geared business in a good year returns more to its owners than an ungeared one, because the lenders take a fixed amount and the owners keep the rest. In a bad year the lenders still take their fixed amount, and the owners absorb the whole shortfall. The right level therefore depends on how volatile your trading is and how much of a bad year you could absorb without the question becoming existential — not on what a ratio table says is normal.</p>""",
 [C("Retained earnings represent:",
    ["This year's profit", "Cash held in reserve",
     "All profit ever made and not distributed", "Money owed to the owners"], 2,
    "It accumulates since inception. Each period's profit lands here; each drawing leaves from here."),
  C("Equity ₦120m: ₦10m introduced and ₦110m retained describes:",
    ["A business funded by its owners", "A business that funded itself from trading",
     "A heavily borrowed business", "A business with a revaluation"], 1,
    "The total is identical to the reverse case and the two are entirely different animals."),
  C("Profit is reported every year yet equity is falling. The likeliest cause is:",
    ["Depreciation", "Owners extracting more than the business earns",
     "Rising payables", "A stock write-down"], 1,
    "Drawings are not a cost and never touch the P&L, so this is invisible on the statement most owners read.")]),

("Reading a balance sheet as an exposure map", 9, """<p>This is the chapter to keep. The balance sheet is not a scorecard — it does not tell you how well you did. It tells you what you are standing on and where you are exposed, which is a more useful thing to know and a harder one to get from anywhere else.</p>

<p><b>Six questions, in order.</b></p>

<p><b>1. Where did the money go?</b> Compare against the prior period. Equity up ₦8,000,000 from profit, but cash down ₦2,000,000 — so ₦10,000,000 went somewhere. Stock and receivables are almost always the answer, and finding which one is the whole exercise.</p>

<p><b>2. Can we pay what is about to fall due?</b> Current assets against current liabilities, and then the same excluding stock. If the second answer is uncomfortable, the first was flattering you.</p>

<p><b>3. How long is the cash cycle, and is it lengthening?</b> Stock days plus debtor days less creditor days. A lengthening cycle means growth will consume more cash than it did last year, which is the thing that catches profitable businesses out.</p>

<p><b>4. What is the shape of the receivables book?</b> Not the total — the ageing, and the concentration. One customer at 40% is a different business from a well-spread book of the same size.</p>

<p><b>5. How used-up are the assets?</b> Net book value against cost. Heavy depreciation with no additions is a replacement bill forming quietly, and nothing has been set aside for it.</p>

<p><b>6. Who owns this business's future — the owners or the lenders?</b> Debt against equity, and whether the trend is toward one or the other.</p>

<p><b>Read the two statements together or you will be misled by both.</b> The P&L alone shows a profitable business that may be running out of money. The balance sheet alone shows a position without explaining how it arose. Profit rising while the cash cycle lengthens and receivables age is the single most common pattern in a business that is about to have a difficult year, and neither statement shows it on its own.</p>

<p><b>The discipline worth building.</b> Ten minutes, quarterly, against the previous quarter, in the order above. Write down which number moved most and why. You will be right about the why perhaps half the time at first — but you will be asking the finance team a specific question rather than a vague one, and that alone changes the answer you get.</p>

<blockquote>IMPLEMENTATION TIP: If you take one habit from this module, make it question one. "Equity rose, cash fell, so where did the money go?" is the question that finds stock problems, collection problems and overtrading before any of them reach the P&L.</blockquote>

<p><b>What this module does not tell you, and where it goes next.</b> The balance sheet shows the position and the P&L shows the period, but neither actually traces the movement of cash — they only let you infer it. The statement that does that directly is the cash flow statement, and it is the subject of the next module. Between the three, the questions "did we do well", "what are we standing on" and "where did the money actually go" each have a proper home.</p>""",
 [C("The balance sheet is best understood as:",
    ["A scorecard of performance", "A map of what you are standing on and where you are exposed",
     "A forecast", "A tax return"], 1,
    "Performance is the P&L's job. Exposure is what only this statement shows."),
  C("Equity rose ₦8m from profit while cash fell ₦2m. This means:",
    ["An accounting error", "₦10m went somewhere — usually stock or receivables",
     "The owners withdrew ₦10m", "Depreciation was ₦10m"], 1,
    "Finding which of the two absorbed it is the whole exercise, and it is question one for a reason."),
  C("Which pattern most reliably precedes a difficult year?",
    ["Profit falling with cash rising", "Profit rising while the cash cycle lengthens and receivables age",
     "Equity rising with no borrowings", "Stock days falling"], 1,
    "It is invisible on either statement alone, which is why the two must be read together.")]),
]


QUESTIONS = [
 Q("A balance sheet shows the position at:", ["The start of the year", "A single date", "An average over the period", "The tax year end"], 1,
   "It is a photograph at one instant, which is why a series matters more than one column.", "Ch1 §1", "What a balance sheet is"),
 Q("Which is a liability rather than an asset?", ["Prepaid insurance", "A customer's deposit for undelivered goods", "Stock on the shelf", "Money owed by a customer"], 1,
   "You owe them goods or a refund, so it is an obligation.", "Ch1 §3", "What a balance sheet is"),
 Q("Profit of ₦8m with no distributions appears on the balance sheet as:", ["A rise in cash", "A rise in equity", "A fall in liabilities", "A rise in fixed assets"], 1,
   "Where the money physically went is a separate question the balance sheet answers.", "Ch1 §6", "What a balance sheet is"),
 Q("Reading one balance sheet without the prior period gives you:", ["Direction", "Position but not direction", "Profitability", "The cash cycle"], 1,
   "Direction is what you can act on, and it needs two columns.", "Ch1 §8", "What a balance sheet is"),
 Q("Assets equal liabilities plus equity because:", ["It is a bookkeeping convention", "Everything the business has, somebody has a claim on", "Assets are valued to make it balance", "Tax rules require it"], 1,
   "Either an outsider has the claim or the owners do. There is no third possibility.", "Ch2 §1", "The accounting equation"),
 Q("Buying ₦5m of stock on credit changes equity by:", ["+₦5m", "−₦5m", "Nothing", "+ the expected margin"], 2,
   "Assets and liabilities rise together; you are larger on both sides and no better off.", "Ch2 §3", "The accounting equation"),
 Q("Selling ₦5m of stock for ₦7m cash raises equity by:", ["₦7m", "₦2m", "₦5m", "Nothing until collected"], 1,
   "Assets rise ₦2m net and liabilities are unchanged, which is exactly the gross profit reported.", "Ch2 §4", "The accounting equation"),
 Q("Paying a ₦5m supplier bill affects profit by:", ["−₦5m", "Nothing", "−the margin", "+₦5m"], 1,
   "The cost occurred when the goods were sold. Paying is settlement.", "Ch2 §5", "The accounting equation"),
 Q("An owner drawing ₦3m from the business is recorded as:", ["An expense in the P&L", "A reduction in equity", "A liability", "A cost of sale"], 1,
   "Drawings never touch the P&L, which is why they are invisible to anyone reading only that statement.", "Ch2 §6", "The accounting equation"),
 Q("Stock rose while cash fell by the same amount. This means:", ["It was bought on supplier credit", "It was bought with the business's own money", "It was written down", "An owner injected funds"], 1,
   "Two assets moved; no outsider funded it.", "Ch2 §7", "The accounting equation"),
 Q("The current portion of a long-term loan belongs in:", ["Non-current liabilities", "Current liabilities", "Equity", "Non-current assets"], 1,
   "Twelve months of instalments fall due within twelve months, however long-term the loan feels.", "Ch3 §8", "Current and non-current"),
 Q("The quick ratio differs from the current ratio by excluding:", ["Receivables", "Cash", "Stock", "Prepayments"], 2,
   "Stock becomes cash only after it sells and is then collected.", "Ch3 §7", "Current and non-current"),
 Q("A current ratio rising because stock is piling up and debtors are slowing is:", ["Good news", "Improvement while the business weakens", "Impossible", "Evidence of strong buying"], 1,
   "Always ask which component moved rather than reading the ratio alone.", "Ch3 §9", "Current and non-current"),
 Q("Current assets ₦60m, current liabilities ₦40m. Working capital is:", ["₦100m", "₦20m", "1.5", "₦40m"], 1,
   "Working capital is the difference; the ratio is the relationship.", "Ch3 §6", "Current and non-current"),
 Q("Non-current assets are held:", ["For resale", "To be used rather than sold", "As security for loans", "Only if owned outright"], 1,
   "That purpose, not the value, is what places them beyond the twelve-month line.", "Ch3 §3", "Current and non-current"),
 Q("Closing stock overstated by ₦2m makes reported profit:", ["₦2m too low", "₦2m too high", "Unaffected", "Too high by the margin on ₦2m"], 1,
   "One error, two wrong statements, and nothing flags it.", "Ch4 §4", "Inventory"),
 Q("Stock ₦45m on cost of sales ₦270m gives stock days of about:", ["61", "45", "6", "167"], 0,
   "45 ÷ 270 × 365 ≈ 61 days.", "Ch4 §6", "Inventory"),
 Q("Stock damaged and unsellable at full price must be:", ["Left at cost until sold", "Written down to what it will fetch", "Moved to non-current assets", "Charged to equity"], 1,
   "Accounts may never carry stock above its recoverable value.", "Ch4 §3", "Inventory"),
 Q("A stable stock total can still hide:", ["A pricing error", "Fast lines thinning while dead stock accumulates", "A supplier price rise", "A revaluation"], 1,
   "Ageing beats totals, which is why the age profile is worth more than the number.", "Ch4 §7", "Inventory"),
 Q("Receivables ₦36m on revenue ₦219m gives debtor days of about:", ["30", "60", "90", "16"], 1,
   "36 ÷ 219 × 365 ≈ 60 days.", "Ch5 §2", "Receivables"),
 Q("Every naira sitting in receivables is:", ["Profit already banked", "Money lent to customers interest-free", "A liability", "Deferred revenue"], 1,
   "You have spent on the goods and not recovered it, sometimes while paying overdraft interest to do so.", "Ch5 §3", "Receivables"),
 Q("A provision for doubtful debts that stays flat while ageing deteriorates is:", ["Prudent", "Postponement", "Required by the standards", "Evidence of good collection"], 1,
   "It flatters this period at the expense of a later one.", "Ch5 §6", "Receivables"),
 Q("One customer representing 40% of receivables is primarily:", ["A commercial success", "A concentration risk that arrives without warning", "A pricing opportunity", "Irrelevant if they pay on time"], 1,
   "Their difficulty becomes your difficulty, and a well-spread book of the same size is a different exposure.", "Ch5 §7", "Receivables"),
 Q("Payables ₦45m on cost of sales ₦300m gives creditor days of about:", ["55", "15", "150", "6.7"], 0,
   "45 ÷ 300 × 365 ≈ 55 days.", "Ch6 §3", "Payables"),
 Q("Stock days 70, debtor days 55, creditor days 40. The cash cycle is:", ["165 days", "85 days", "25 days", "40 days"], 1,
   "70 + 55 − 40 = 85 days of self-funded trading.", "Ch6 §4", "Payables"),
 Q("Why does growth consume cash?", ["Margins fall as volume rises", "Each extra sale must be funded for the length of the cash cycle", "Fixed costs rise", "Suppliers shorten terms"], 1,
   "Profitable businesses fail this way far more often than unprofitable ones fail from losses.", "Ch6 §5", "Payables"),
 Q("Tax collected but not yet remitted, sitting in payables, is:", ["Working capital to use", "Somebody else's money with a due date", "Revenue", "Equity"], 1,
   "Businesses that fund operations from it discover the cost when the date arrives.", "Ch6 §8", "Payables"),
 Q("Net book value of a fixed asset represents:", ["Its market value", "Unexpired cost not yet charged to profit", "Its replacement cost", "Its insured value"], 1,
   "Treating it as a valuation is the commonest error in reading this section.", "Ch7 §3", "Fixed assets"),
 Q("Cost ₦40m with accumulated depreciation ₦34m indicates an asset base that is:", ["Newly invested", "Around 85% depreciated, with replacement approaching", "Overvalued", "Fully funded for replacement"], 1,
   "And nothing in the accounts has set money aside for it.", "Ch7 §4", "Fixed assets"),
 Q("Comparing a business that owns its premises with one that leases, on asset totals, compares:", ["Operational efficiency", "Financing choices rather than operations", "Profitability", "Market share"], 1,
   "Depending on treatment, the leased premises may not appear as an asset at all.", "Ch7 §7", "Fixed assets"),
 Q("A capital work in progress balance unchanged for several periods is:", ["Normal and expected", "Worth asking about — stalled projects sit there undepreciated", "A depreciation error", "Part of current assets"], 1,
   "It can hold real money doing nothing while looking like an asset.", "Ch7 §8", "Fixed assets"),
 Q("Retained earnings of ₦110m against ₦10m introduced describes a business that:", ["Was funded by its owners", "Funded itself out of its own trading", "Is heavily borrowed", "Has revalued its property"], 1,
   "The same total composed the other way round is an entirely different animal.", "Ch8 §5", "Equity and reserves"),
 Q("Negative retained earnings mean:", ["The business is insolvent", "Accumulated losses exceed accumulated profits since inception", "This year was a loss", "Owners withdrew capital"], 1,
   "It is history rather than a verdict on the present, but current profit repairs before it builds.", "Ch8 §6", "Equity and reserves"),
 Q("Borrowings ₦80m against equity ₦40m means the business:", ["Is under-borrowed", "Carries twice as much of other people's money as its own", "Has negative equity", "Cannot borrow further"], 1,
   "Gearing magnifies both good years and bad ones.", "Ch8 §8", "Equity and reserves"),
 Q("Equity rising with no owner injection means:", ["The business earned it", "Assets were revalued", "Debt increased", "Drawings were taken"], 0,
   "It is one of the fastest health checks available over a year.", "Ch8 §9", "Equity and reserves"),
 Q("The first question to ask of any balance sheet is:", ["What is the profit", "Where did the money go", "What is the tax charge", "How much is owed to the bank"], 1,
   "Equity up and cash down means something absorbed the difference, usually stock or receivables.", "Ch9 §2", "Reading exposure"),
 Q("The P&L read alone can hide:", ["Gross margin", "A profitable business running out of money", "Revenue growth", "Operating costs"], 1,
   "Only the balance sheet shows what the profit turned into.", "Ch9 §9", "Reading exposure"),
 Q("A lengthening cash cycle means:", ["Growth will consume more cash than before", "Margins are improving", "Suppliers are being paid faster", "Stock is moving faster"], 0,
   "It is the thing that catches profitable businesses out.", "Ch9 §5", "Reading exposure"),
 Q("Which combination most warrants concern?", ["Profit rising, cash cycle shortening", "Profit rising, cash cycle lengthening, receivables ageing", "Profit flat, equity rising", "Stock days falling, margin flat"], 1,
   "It is invisible on either statement alone, which is why they are read together.", "Ch9 §9", "Reading exposure"),
 Q("Reading the balance sheet quarterly against the prior quarter mainly gives you:", ["A tax position", "Movement, and therefore a specific question to ask", "A profit figure", "A budget variance"], 1,
   "A specific question to finance gets a different answer from a vague one.", "Ch9 §10", "Reading exposure"),
]


def rebalance(items, seed):
    """Spread correct answers evenly across A-D by rotating each option list.

    The first draft of module 2 came out 72% guessable with 29 of 40 answers in
    position B — the same defect that made four legacy tracks passable by a
    candidate who had read nothing. It is evidently what an author produces by
    default, so the correction belongs in the build rather than in a later pass.
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
    rebalance(QUESTIONS, "finance:read_bs:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:read_bs:checks")

    mod = {
        "title": "Reading the Balance Sheet",
        "desc": ("What the business is standing on, and where it is exposed. Working "
                 "capital, stock days, debtor and creditor days, the cash cycle, what "
                 "net book value really means, and the six questions that turn a "
                 "position into a decision. Worked in naira on trading numbers."),
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
    data[KEY] = mod                      # merge, never clobber a sibling module
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
