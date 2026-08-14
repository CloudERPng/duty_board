#!/usr/bin/env python3
"""Build academy_finance_data.json — Reading the Profit & Loss.

Module 2 of Accounting & Finance for Non-Finance Managers, written first
because the P&L is the document this audience already sees every month: it is
where the voice gets set and where a draft can be tested fastest on a real
manager.

Design principle for the whole track, and the place it departs from the
standard textbook treatment: READ BEFORE PREPARE. This audience will never
draft a P&L, they will be handed one. Every chapter therefore starts from a
document or a decision in front of the learner and works back to the concept.

Run from the app package directory:  python3 build_finance_m2.py
"""

import io
import json

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Revenue: when a sale becomes a sale", 9, """<p>The top line looks like the simplest number on the page and is the one most often misread. Revenue is not the money that arrived in the bank this month. It is the value of what you <b>delivered</b> this month, whenever the customer happens to pay.</p>

<p>Those two things come apart constantly, and in both directions.</p>

<p><b>A sale with no money.</b> You supply a distributor ₦4,000,000 of stock on thirty days' credit on the 20th. The goods are gone, the invoice is raised, the customer owes you. That ₦4,000,000 is revenue this month even though not one naira has been received, and it will still be revenue if they pay late, pay slowly, or never pay at all.</p>

<p><b>Money with no sale.</b> A customer pays ₦1,500,000 in advance for goods you will deliver next month. Your bank balance rises today. Your revenue does not. You are holding somebody else's money until you deliver — it sits as a liability, not as income.</p>

<p><b>Why the rule exists.</b> If revenue followed cash, a manager could make a bad month look good simply by chasing customers hard in the last week, and a good month look poor by letting collections slip. The performance of the business would become a story about collection timing rather than about trading. Recognising revenue on delivery keeps the top line describing what the business actually did.</p>

<p><b>What this means when you read your own P&L.</b> A rise in revenue tells you that more was delivered. It tells you nothing whatever about whether you were paid, and nothing about whether you will be. Those questions are answered on the balance sheet, under receivables, and in the cash flow statement — which is why a manager who reads only the P&L can watch revenue climb every month while the business quietly runs out of money.</p>

<p><b>Two things that reduce revenue and are easy to miss.</b> Returns come off the top line, so a month with heavy returns shows lower revenue rather than a separate cost. Trade discounts do the same — a 10% discount on ₦2,000,000 of goods is ₦1,800,000 of revenue, not ₦2,000,000 of revenue and a ₦200,000 cost. That matters when you are trying to work out why margin moved, because discounting hides inside the top line rather than announcing itself.</p>

<p><b>And one thing that is not revenue at all: VAT.</b> The VAT you charge a customer was never yours. You collect it on behalf of the tax authority and pass it on. A P&L that shows revenue inclusive of VAT overstates the business by that amount, and every margin calculated from it will be wrong. When somebody quotes a revenue figure, it is always worth knowing whether it is gross or net of VAT — the two differ by 7.5% and people quote them interchangeably.</p>

<blockquote>WATCH-OUT: The month a business changes its delivery pattern — a big order shipped on the 30th instead of the 2nd — revenue jumps or falls for reasons that have nothing to do with demand. Before concluding anything from a single month, ask what was delivered and when.</blockquote>

<p><b>One more thing the top line will not tell you.</b> Revenue says nothing about whether the sale was any good. A month of heavy discounting and a month of full-price trading can produce identical revenue, and only the next line down begins to separate them. Managers who report upward on revenue alone are describing activity rather than performance, which is why the first question any experienced reader asks about a good revenue month is what it cost to get.</p>""",
 [C("You deliver ₦4m of goods on 30-day credit on the 20th. Revenue this month is:",
    ["Nil until they pay", "₦4m", "₦4m less an allowance for late payment", "Half now, half on payment"], 1,
    "Revenue follows delivery, not collection. Whether you get paid is a receivables question, answered on the balance sheet."),
  C("A customer pays ₦1.5m in advance for next month's delivery. This month you record:",
    ["₦1.5m revenue", "₦1.5m revenue less a provision", "No revenue — you are holding their money until you deliver", "Half the revenue"], 2,
    "Cash arrived but nothing was delivered. Until it is, the money is a liability, not income."),
  C("Why does recognising revenue on delivery rather than on payment matter to a manager?",
    ["It makes revenue larger", "It stops the top line becoming a story about collection timing",
     "It is required for VAT", "It smooths seasonal swings"], 1,
    "If revenue followed cash, a hard collection push would flatter a bad month and slow collections would spoil a good one — and neither says anything about trading.")]),

("Cost of sales, and what sits inside it", 9, """<p>Cost of sales is what the goods you sold actually cost you. Not what you bought this month, not what is sitting in the warehouse — what went out of the door in the hands of customers.</p>

<p>That distinction is the single most common misreading in a retail P&L, so it is worth being slow about.</p>

<p><b>Buying is not a cost.</b> When you buy ₦10,000,000 of stock, nothing has happened to your profit. You have swapped one asset, cash, for another asset, inventory. The P&L does not move. Only when you sell those goods does their cost cross into cost of sales.</p>

<p>So a month of heavy buying ahead of a festive peak does not depress profit, though it will certainly depress your bank balance. A manager who confuses the two will report a disaster to a board that is looking at a perfectly healthy P&L, or the reverse.</p>

<p><b>The arithmetic behind the line.</b> Cost of sales is worked out from what you started with, what you added, and what is left:</p>

<p>Opening stock ₦18,000,000, plus purchases ₦42,000,000, less closing stock ₦21,000,000, gives cost of sales of ₦39,000,000. Everything that came in and did not remain is treated as having been sold.</p>

<p><b>Notice what that arithmetic quietly does.</b> It assumes that anything missing was sold. It was not necessarily sold — it may have been stolen, broken, expired or miscounted. Shrinkage does not appear as a line called shrinkage; it disappears silently into cost of sales and shows up as a margin that is worse than it should be, with no explanation attached.</p>

<p>This is why a manager investigating a fall in gross margin must always ask whether the stock count was any good. A closing stock figure that is overstated by ₦2,000,000 understates cost of sales by exactly ₦2,000,000 and overstates profit by the same. The P&L will look better and be wrong.</p>

<p><b>What else belongs in cost of sales.</b> Beyond the purchase price of the goods: inbound freight, clearing and duty on imports, and any direct handling needed to get goods sellable. The test is whether the cost was incurred to <i>get the goods ready to sell</i>. Delivering them to the customer afterwards is a selling cost, not a cost of sale — a distinction worth holding, because moving delivery costs between the two lines changes gross margin without changing profit at all.</p>

<blockquote>IMPLEMENTATION TIP: If gross margin moves more than a point or two without a price or supplier change, look at stock before you look at anything else. Count quality, cut-off errors on goods received near month-end, and unrecorded write-offs explain most unexplained margin movements in retail and distribution.</blockquote>

<p><b>A note on timing at month-end.</b> Goods received on the last day but not entered until the first of the next month, or an invoice posted before the stock physically arrived, both distort the calculation — and both are common precisely because month-end is busy. This is called a cut-off error, and its signature is a margin that looks wrong one month and unusually good the next, as the two errors reverse. If you see that pattern, the trading was probably fine and the paperwork was not.</p>""",
 [C("You buy ₦10m of stock in March and sell none of it. The effect on March profit is:",
    ["₦10m cost", "Nothing — you swapped cash for inventory", "₦10m cost spread over the year", "Depends on the supplier's terms"], 1,
    "Buying moves value between two assets. Cost only reaches the P&L when the goods are sold."),
  C("Opening stock ₦18m, purchases ₦42m, closing stock ₦21m. Cost of sales is:",
    ["₦42m", "₦39m", "₦45m", "₦21m"], 1,
    "18 + 42 − 21 = 39. Whatever came in and did not remain is treated as sold."),
  C("Closing stock is overstated by ₦2m because of a bad count. The P&L will show:",
    ["Profit understated by ₦2m", "No effect — stock is a balance sheet item",
     "Profit overstated by ₦2m", "Revenue overstated by ₦2m"], 2,
    "Overstated closing stock understates cost of sales by the same amount, so profit is flattered by exactly ₦2m.")]),

("Gross margin: the number that describes your trading", 9, """<p>Gross profit is revenue less cost of sales, and gross margin is that expressed as a percentage of revenue. On ₦60,000,000 of revenue and ₦39,000,000 of cost of sales, gross profit is ₦21,000,000 and gross margin is 35%.</p>

<p>Of every number on the P&L, this is the one a manager should watch most closely, because it describes the thing the business fundamentally does: buy or make something, and sell it for more.</p>

<p><b>Margin and markup are not the same number, and confusing them costs real money.</b> Buy at ₦1,000 and sell at ₦1,500. The markup — the uplift on cost — is 50%. The margin — the share of the selling price you keep — is ₦500 ÷ ₦1,500, which is 33%. Anyone who prices for a 40% margin by adding 40% to cost has actually priced a 29% margin and will wonder for months why the numbers never come out.</p>

<p><b>Why percentage matters more than the naira amount.</b> Gross profit in naira grows simply because you sold more; it tells you about size. Margin tells you about health, and it holds still when volume moves. A business whose gross profit rises 20% while margin falls from 35% to 31% is buying its growth — with discounts, or by shifting toward cheaper products — and that trade may or may not be one anybody chose.</p>

<p><b>Four things move margin, and they need different responses.</b></p>

<p><b>Selling price.</b> Discounting, promotions, and the slow drift that happens when staff have authority to negotiate and nobody watches the average.</p>

<p><b>Buying price.</b> Supplier increases, currency movement on imported goods, losing a volume rebate. Currency deserves particular attention: goods bought at ₦1,600 to the dollar and repriced at ₦1,500 lose margin that no amount of selling effort recovers.</p>

<p><b>Mix.</b> Selling proportionally more low-margin lines drags the average down even when no single product's margin changed at all. This is the most commonly missed cause, because every individual product looks fine.</p>

<p><b>Loss.</b> Shrinkage, damage and expiry, which as we saw arrive silently inside cost of sales.</p>

<p><b>Reading it well means asking which of the four moved.</b> A margin fall of two points has a completely different remedy depending on the answer: a pricing conversation, a supplier conversation, a merchandising decision, or a stock control investigation. The P&L will not tell you which — but it tells you to go and look, and roughly how much is at stake.</p>

<blockquote>IMPLEMENTATION TIP: Track gross margin by month as a percentage on one line, for at least twelve months. Almost nothing in a trading business is more informative for the effort, and a drift of half a point a month is invisible in isolation and severe over a year.</blockquote>

<p><b>What good looks like.</b> A manager who knows their margin knows it as a number they could say aloud without looking — this month, last month, and the same month last year. That sounds like a small thing. It is the difference between noticing a two-point fall in the week it happens and discovering it in a quarterly review, by which point the cause is three months cold and the money is gone.</p>""",
 [C("You buy at ₦1,000 and sell at ₦1,500. The gross MARGIN is:",
    ["50%", "33%", "150%", "67%"], 1,
    "Margin is profit as a share of the selling price: 500 ÷ 1,500 = 33%. The 50% figure is markup, on cost."),
  C("Gross profit rose 20% while gross margin fell from 35% to 31%. This means:",
    ["Costs were well controlled", "The business bought its growth, with discount or cheaper mix",
     "Revenue must have fallen", "A stock count error"], 1,
    "Naira profit tells you about size, margin about health. Growing volume at a worse margin is a trade somebody should have chosen deliberately."),
  C("Every product's margin is unchanged, yet overall gross margin fell. The most likely cause is:",
    ["Shrinkage", "Mix — proportionally more low-margin lines sold",
     "A supplier price rise", "A currency movement"], 1,
    "Mix is the commonest missed cause precisely because each product looks fine on its own.")]),

("Operating expenses and the fixed-cost base", 9, """<p>Below gross profit sit the costs of running the business rather than of buying the goods: salaries, rent, power, fuel, security, transport, marketing, professional fees, bank charges, software. Together they are operating expenses, and the useful way to read them is not by category but by <b>behaviour</b>.</p>

<p><b>Fixed costs</b> do not move with sales. Rent is the same in a quiet month. So is the security contract, most salaries, and the ERP subscription.</p>

<p><b>Variable costs</b> move roughly in proportion to activity: sales commission, transaction fees on card payments, delivery fuel, packaging.</p>

<p><b>Step costs</b> hold flat and then jump. One supervisor covers a shop up to a point, then you need a second. A generator covers a certain load until you need a bigger one. These are the costs that surprise people, because they behave like fixed costs right up until they do not.</p>

<p><b>Why the distinction is the most useful thing in this chapter.</b> It tells you what a change in sales does to profit. If a branch carries ₦4,000,000 a month of fixed cost and earns 35% margin, it needs about ₦11,400,000 of revenue simply to cover that base before making a naira. Every additional sale beyond it contributes 35 kobo in the naira almost straight to profit, because the fixed costs are already paid for.</p>

<p>That asymmetry is why a modest fall in sales can wipe out a branch's profit entirely while a modest rise transforms it, and why managers are so often surprised by both.</p>

<p><b>Reading the expense block on your own P&L.</b> Compare each line to revenue as a percentage, not to last month in naira. Salaries at ₦6,000,000 mean nothing on their own; salaries at 10% of revenue against 8% last year is a finding. Fixed costs rising as a share of revenue is the early signal of a business growing its overhead faster than its trading.</p>

<p><b>And watch what hides in "sundry" or "general".</b> A line that grows quietly and is never questioned because nobody owns it is where uncontrolled spending accumulates. If any single expense category is large and vaguely named, that is where to look first.</p>

<blockquote>WATCH-OUT: Cutting fixed costs feels decisive and is often the wrong first move. A branch failing to cover a ₦4m base may have a revenue problem rather than a cost problem, and cutting the staff who generate the revenue is how a slow decline becomes a fast one. Establish which side the gap is on before acting.</blockquote>

<p><b>One line that is neither fixed nor variable in the way people assume: energy.</b> In a Nigerian operation, diesel for the generator moves with hours of grid failure rather than with sales. It looks variable, behaves unpredictably, and is large enough to distort a month. Treat it as its own thing rather than forcing it into either category, and read it against hours run rather than against revenue.</p>""",
 [C("Sales commission and card transaction fees are:",
    ["Fixed costs", "Variable costs", "Step costs", "Cost of sales"], 1,
    "They move roughly in proportion to activity, which is what makes a cost variable."),
  C("A branch carries ₦4m monthly fixed cost at 35% gross margin. Revenue needed to cover it:",
    ["₦4.0m", "₦6.2m", "₦11.4m", "₦14.0m"], 2,
    "₦4m ÷ 0.35 ≈ ₦11.4m. Each naira of sales contributes only 35 kobo toward the fixed base."),
  C("Salaries were ₦6m last year and ₦6m this year. On its own this tells you:",
    ["Costs are well controlled", "Very little — compare them as a share of revenue",
     "Headcount is unchanged", "Nothing has changed in the business"], 1,
    "Flat in naira while revenue grew is a real improvement; flat while revenue fell is a growing problem. The percentage carries the meaning.")]),

("Operating profit, net profit, and why both exist", 9, """<p>Below the expense block the P&L gives you profit more than once, and each version answers a different question. Reading the wrong one is how managers end up arguing past each other.</p>

<p><b>Operating profit</b> is gross profit less operating expenses. It answers: <i>does the trading operation work?</i> It deliberately excludes how the business is financed and what tax it pays, because neither is the operating manager's doing.</p>

<p><b>Net profit</b> is what remains after interest and tax. It answers: <i>what did the owners actually make?</i></p>

<p><b>Why separating them matters, in one example.</b> Two branches each produce ₦8,000,000 of operating profit. One is funded by the owner's own money, the other by a loan costing ₦3,000,000 a year in interest. The second delivers ₦5,000,000 to the owners against the first's ₦8,000,000. As <i>operations</i> they performed identically, and the manager of the second should not be marked down for a financing decision made above them.</p>

<p>The reverse error is equally common: judging a business on operating profit alone while it is being quietly consumed by the cost of its debt.</p>

<p><b>The line to be careful with is interest.</b> It is not an operating cost and does not belong in a branch's performance, but it is entirely real. A business generating good operating profit and negative net profit does not have a trading problem; it has a financing problem, and no amount of selling harder will fix it.</p>

<p><b>Where tax sits.</b> Below net profit before tax, and it is worth knowing that the tax charge in the accounts rarely equals the cash paid to the tax authority in the same period. They are computed on different bases and on different timing. For an operating manager this matters mainly as a caution: do not reconcile your tax line to your bank statement and expect them to agree.</p>

<p><b>Which number should you be held to?</b> Almost always operating profit, and for the reason above — it is the part you control. If you are being measured on net profit, you are being measured partly on decisions somebody else made about borrowing, and that is worth saying out loud before the review rather than during it.</p>

<blockquote>IMPLEMENTATION TIP: When somebody quotes "profit" without qualifying it, ask which one. The gap between operating and net profit in a business carrying debt can be most of the number, and two people using the same word for different lines will reach opposite conclusions and both be certain.</blockquote>

<p><b>A third measure you will meet: EBITDA.</b> Earnings before interest, tax, depreciation and amortisation — operating profit with the non-cash charges added back. It is popular because it approximates cash generated by trading, and it is misused because it flatters any business with heavy assets. It is a useful number for comparing operations; it is not profit, and it is not what the owners keep.</p>""",
 [C("Two branches both make ₦8m operating profit; one carries ₦3m of interest. As operations they:",
    ["Differ by ₦3m", "Performed identically", "Cannot be compared", "Differ by ₦3m after tax"], 1,
    "Interest is a financing cost, not an operating one. Operating profit deliberately excludes it so trading can be judged on its own."),
  C("A business with healthy operating profit and negative net profit has:",
    ["A trading problem", "A financing problem", "A tax problem", "A stock problem"], 1,
    "The operation works; the cost of its debt is consuming the result. Selling harder will not fix it."),
  C("An operating manager should normally be measured on:",
    ["Net profit", "Revenue", "Operating profit", "Gross profit"], 2,
    "It is the part they control. Net profit folds in borrowing decisions made above them.")]),

("Depreciation and amortisation: cost without payment", 9, """<p>Two lines in the expense block are unlike all the others: no money leaves the business when they are charged. They are the most misunderstood items on the P&L and the reason profit and cash differ even in a business that collects promptly.</p>

<p><b>What depreciation is doing.</b> You buy delivery vehicles for ₦24,000,000 expected to last five years. Charging the whole ₦24,000,000 against the month you bought them would be absurd — it would report a catastrophic month followed by four years of flattered ones, and none of those numbers would describe the business. Instead the cost is spread across the years the vehicles are used: ₦4,800,000 a year, ₦400,000 a month.</p>

<p>That monthly ₦400,000 is a real cost. The vehicles are genuinely being used up. But no payment accompanies it — the money left the bank when you bought them.</p>

<p><b>Amortisation</b> is the same idea for things you cannot touch: software licences, development costs, goodwill on an acquisition.</p>

<p><b>The two consequences a manager must hold on to.</b></p>

<p>First, <b>profit is not cash</b>, and depreciation is one of the main reasons. A business showing ₦2,000,000 profit with ₦3,000,000 of depreciation generated roughly ₦5,000,000 of cash from trading. This is why the cash flow statement starts with profit and adds depreciation straight back.</p>

<p>Second, <b>depreciation is an estimate, and estimates can flatter.</b> Whoever decides that vehicles last five years rather than three has changed reported profit without anything happening in the real world. Lengthening useful lives is one of the quietest ways to improve a profit figure, and it is entirely legitimate right up until it is not.</p>

<p><b>What it does not do.</b> Depreciation does not set money aside to replace the asset. Nothing is being saved. When the vehicles need replacing, the business needs cash it may not have — which is why a company can be profitable for five years and then be unable to afford the trucks it depends on.</p>

<p><b>Where this bites in practice.</b> A distribution business with an ageing fleet reports healthy profit for years while its vehicles quietly reach the end of their lives. The replacement bill arrives all at once, has to be funded from cash or borrowing, and the business that looked profitable throughout discovers it never set anything aside — because nothing in the accounts ever asked it to. Depreciation records the using-up. Funding the replacement is a separate decision that somebody has to make deliberately.</p>

<blockquote>WATCH-OUT: When comparing two branches, check they depreciate on the same basis. A branch charged for its building while another operates rent-free from a group property is not being compared like for like, and the difference can be larger than the profits being compared.</blockquote>""",
 [C("₦24m of vehicles over five years. The monthly depreciation charge is:",
    ["₦24m in month one", "₦400,000", "₦4.8m", "Nil until they are sold"], 1,
    "₦24m ÷ 5 years = ₦4.8m a year, ₦400,000 a month. The cost is spread over the period of use."),
  C("Profit is ₦2m and depreciation ₦3m. Cash generated by trading is roughly:",
    ["₦2m", "₦5m", "Negative ₦1m", "₦3m"], 1,
    "No money left the business for depreciation, so it is added back. This is why the cash flow statement begins with profit and adds it."),
  C("Depreciation charged each month means the business is:",
    ["Setting money aside to replace the asset", "Paying the supplier in instalments",
     "Recording the asset being used up, with no money moving", "Reducing its tax bill in cash"], 2,
    "Nothing is saved and nothing is paid. The cash left when the asset was bought.")]),

("The lines that carry judgement", 9, """<p>Most of the P&L is arithmetic. A handful of lines are opinions, and knowing which is which is what separates a manager who reads accounts from one who merely receives them.</p>

<p><b>Accruals.</b> Costs incurred but not yet invoiced. December's electricity, consumed in December, billed in January, belongs in December. Somebody has to estimate it. An accrual set too low flatters this month and punishes next.</p>

<p><b>Prepayments.</b> The mirror image. A year's insurance paid in advance is not a cost of the month it was paid; eleven twelfths of it belongs to future months and sits on the balance sheet until then.</p>

<p><b>Provisions.</b> An estimate of something expected but not certain — that a portion of receivables will not be collected, that a warranty will be claimed, that a dispute will be lost. Provisions are the most judgement-heavy line on the page, and the most useful to ask about.</p>

<p><b>Write-offs.</b> The point at which an estimate becomes an admission: this stock is gone, this customer will not pay. Write-offs land in one month and describe deterioration that usually happened over many.</p>

<p><b>Why a manager should care about someone else's estimates.</b> Because they move your reported result and they are not neutral. Consider a business under pressure to hit a number: raising the useful life of assets, thinning the bad debt provision, or deferring a write-off each improve this month's profit without anything improving in the business. None is fraud. All are judgement, and all are borrowed from next month.</p>

<p><b>The pattern worth watching</b> is a P&L that meets its target every month by a small margin while receivables age and stock grows. That combination — steady reported profit, deteriorating balance sheet — is the signature of a result being managed rather than earned, and it is visible only if you read the two statements together.</p>

<p><b>The question to ask, and it is a fair one.</b> "What changed in the estimates this month?" A finance team with nothing to hide will answer it in a sentence. It is not an accusation; it is the same question they ask each other.</p>

<p><b>The reverse also happens and is worth naming.</b> A business having a strong month sometimes takes the opportunity to be prudent: raising provisions, writing off what it has been carrying, shortening asset lives. This depresses a good result to build cushion for a weaker one. It is not dishonest either, but it means an unusually poor month can follow an unusually good one for reasons that have nothing to do with trading. Estimates smooth results in both directions.</p>

<blockquote>IMPLEMENTATION TIP: A large write-off is rarely news about the month it appears in. When one lands, the useful question is not "why this month" but "how long was this true before anybody wrote it down" — because that is the number that tells you whether your reporting is working.</blockquote>""",
 [C("December's electricity is consumed in December and billed in January. It belongs in:",
    ["January, when billed", "December, as an accrual", "Split between both", "Whenever it is paid"], 1,
    "Costs belong to the period that consumed them. Somebody estimates the amount and accrues it."),
  C("A year's insurance paid in advance in January is:",
    ["A January cost in full", "Spread across the year, with the balance held as a prepayment",
     "Not a cost at all", "A provision"], 1,
    "Only the month's share is a cost; the rest sits on the balance sheet until its month arrives."),
  C("Steady reported profit alongside ageing receivables and growing stock suggests:",
    ["A well-run business", "A result being managed rather than earned",
     "Rapid growth", "A tax planning strategy"], 1,
    "That combination is the classic signature, and it is visible only by reading the P&L and balance sheet together.")]),

("Reading a branch or department P&L", 9, """<p>Everything so far applies to a whole business. Most managers are handed something narrower: a branch, a department, a category. Those carry two complications that a group P&L does not, and both are worth understanding before you defend or attack a number.</p>

<p><b>Allocated overheads.</b> Head office costs — the MD, finance, IT, the group insurance — have to land somewhere, and they are usually spread across units by some rule: share of revenue, of headcount, of floor space. The rule is a choice, and it is not neutral.</p>

<p>A branch allocated overhead on revenue is penalised for growing. A branch allocated on headcount is penalised for being labour-intensive. Neither reflects what head office actually did for that branch, and both change the branch's apparent profit without anything changing in the branch.</p>

<p><b>So the first question about any branch P&L is which costs the branch controls.</b> If a manager cannot influence a line, holding them to it teaches them the numbers are unfair — and a manager who believes that stops reading them, which is a worse outcome than any allocation error.</p>

<p><b>The useful reading is two-stage.</b> Start with <i>controllable</i> profit: branch revenue, cost of sales, and only the costs the branch decides — staff, local marketing, consumables, waste. That is the manager's scorecard. Then take allocated overhead off to reach the branch's contribution to the group. That is the investment scorecard: whether this branch should exist.</p>

<p>Those two questions have different answers surprisingly often. A branch can be well run and still not worth keeping; a branch can be poorly run and worth fixing rather than closing. Collapsing both into one number loses the distinction and usually leads to closing the wrong branch.</p>

<p><b>Transfer prices.</b> Where stock moves between units at an internal price, that price sets each unit's margin — and it was decided by somebody, not by a market. A distribution centre charging branches a high internal price makes itself look profitable and the branches look weak. Nothing about the group changed.</p>

<p><b>What to do with all this.</b> When a branch P&L looks wrong, check the allocation basis and the transfer price before you check the manager. Those two lines explain more surprising branch results than performance does.</p>

<blockquote>IMPLEMENTATION TIP: Ask for your branch P&L with the allocated costs shown separately rather than buried in the expense lines. Any competent finance team can produce it that way, and it turns an argument about fairness into a conversation about performance.</blockquote>

<p><b>Watch for costs that are allocated but avoidable.</b> A branch charged ₦900,000 a month of head office overhead is not saving ₦900,000 if it closes — most of that cost stays and is simply redistributed to the branches that remain. Closing a branch on the strength of an allocated loss frequently makes the group worse off, because the contribution disappears and the overhead does not. Ask what would actually stop being spent.</p>""",
 [C("Head office overhead allocated to branches on share of revenue means:",
    ["Every branch pays the same", "A growing branch is charged more for growing",
     "Allocation is neutral", "Head office costs disappear"], 1,
    "The basis is a choice with consequences. Allocating on revenue penalises exactly the branches doing best."),
  C("Controllable profit for a branch manager should exclude:",
    ["Branch staff costs", "Local marketing", "Allocated head office overhead", "Branch waste"], 2,
    "A manager cannot influence it. Holding them to it teaches them the numbers are unfair, and they stop reading them."),
  C("A distribution centre raises its internal transfer price to branches. Group profit:",
    ["Rises", "Falls", "Is unchanged — it moves between units", "Depends on the margin"], 2,
    "Nothing entered or left the group. Only the apparent performance of each unit moved.")]),

("Six questions to ask about any P&L", 8, """<p>This chapter is the one to keep. Everything else explained how the statement works; these are the questions that turn it into a decision, in the order worth asking them.</p>

<p><b>1. What period is this, and what is it being compared to?</b> A month against the same month last year is a real comparison. A month against last month compares a 28-day February with a 31-day January and a festive December with a flat one. A part-month against a full month is not a comparison at all, though it is presented as one constantly.</p>

<p><b>2. Which way did gross margin move, and why?</b> Not gross profit in naira — the percentage. If it moved, you are looking at price, buying cost, mix, or loss, and the four have entirely different remedies. This single question surfaces more real problems than the rest of the P&L combined.</p>

<p><b>3. Are operating costs growing faster than revenue?</b> Read them as a percentage of revenue rather than in naira. A cost base rising as a share of revenue is a business whose overhead is outgrowing its trading, and it is the slowest and most dangerous drift on the page because no single month looks alarming.</p>

<p><b>4. What is in the lines I cannot see inside?</b> Anything vaguely named and large — sundry, general, other. Uncontrolled spending accumulates where nobody owns the label.</p>

<p><b>5. What changed in the estimates?</b> Accruals, provisions, useful lives, write-offs. Not an accusation, just the question that stops a managed result passing as an earned one.</p>

<p><b>6. Does this profit look like cash?</b> Profit rising while the bank falls is normal in a growing business — stock and receivables absorb the money. It is also what a serious problem looks like in its early months. The P&L cannot tell you which; it can only tell you to go and look at the other two statements, which is where the next chapters of this track go.</p>

<p><b>A discipline that costs nothing.</b> Write your answer to question two before you open any other report. If you cannot answer it, you have not read the P&L — you have looked at it. The difference shows up in the meeting.</p>

<blockquote>IMPLEMENTATION TIP: Six questions, ten minutes, once a month, in the same order. Managers who do this consistently spot problems roughly a quarter before those who read the numbers only when something already looks wrong — because by then the cause is usually three months old.</blockquote>

<p><b>And one question deliberately not on the list: "did we hit budget?"</b> It is the question most often asked first, and it is the least informative, because a budget is a forecast somebody made months ago under different conditions. Missing a bad budget is not failure and beating an easy one is not success. Ask what the numbers say about the business first, and only then ask what was expected of them.</p>""",
 [C("Comparing this month against last month is weak mainly because:",
    ["Last month is always better", "Month lengths and seasonality differ",
     "It excludes tax", "Revenue is recognised differently"], 1,
    "A 28-day February against a 31-day January, or a flat month against a festive one, produces a difference that means nothing."),
  C("The single most informative question about a P&L is:",
    ["How much profit was made", "Which way gross margin moved, and why",
     "What the tax charge was", "Whether revenue grew"], 1,
    "Margin describes the health of the trading itself, and its four causes each need a different response."),
  C("Profit is rising while the bank balance falls. This is:",
    ["Always a serious problem", "Always normal in growth",
     "Either — the P&L cannot tell you which, and you must look further",
     "Evidence of an accounting error"], 2,
    "Stock and receivables absorb cash in a growing business, and the early months of a serious problem look identical. Only the other statements distinguish them.")]),
]


QUESTIONS = [
 # Revenue and recognition (5)
 Q("Goods are delivered on 28 March and paid for on 30 April. Revenue is recognised in:",
   ["April", "March", "Split across both", "Whichever month the customer's order was placed"], 1,
   "Revenue follows delivery, not collection.", "Ch1 §1", "Revenue and recognition"),
 Q("A customer's ₦1.5m advance payment for next month's goods appears this month as:",
   ["Revenue", "A liability", "Gross profit", "A receivable"], 1,
   "You are holding their money until you deliver.", "Ch1 §2", "Revenue and recognition"),
 Q("A 10% trade discount on ₦2m of goods is recorded as:",
   ["₦2m revenue and ₦200,000 expense", "₦1.8m revenue",
    "₦2m revenue and ₦200,000 in cost of sales", "₦1.8m revenue and ₦200,000 provision"], 1,
   "Discounts reduce the top line, which is why discounting hides inside revenue rather than announcing itself.",
   "Ch1 §6", "Revenue and recognition"),
 Q("VAT charged to customers is:",
   ["Part of revenue", "Part of gross profit", "Collected on behalf of the tax authority, not revenue",
    "An operating expense"], 2,
   "It was never yours. Revenue stated inclusive of VAT overstates the business by 7.5%.", "Ch1 §7", "Revenue and recognition"),
 Q("Revenue rose sharply this month with no change in demand. The likeliest explanation is:",
   ["A pricing error", "A large delivery falling either side of month-end",
    "A change in the VAT rate", "Improved collections"], 1,
   "Delivery timing moves the top line without anything changing in trading.", "Ch1 §8", "Revenue and recognition"),

 # Cost of sales (5)
 Q("Purchasing ₦10m of stock that remains unsold affects this month's profit by:",
   ["Reducing it ₦10m", "Nothing", "Reducing it by the margin", "Increasing it ₦10m"], 1,
   "Cash became inventory. Cost reaches the P&L only on sale.", "Ch2 §2", "Cost of sales"),
 Q("Opening ₦12m, purchases ₦30m, closing ₦9m. Cost of sales is:",
   ["₦30m", "₦33m", "₦27m", "₦51m"], 1,
   "12 + 30 − 9 = 33.", "Ch2 §4", "Cost of sales"),
 Q("Stock stolen during the month appears on the P&L as:",
   ["A separate shrinkage expense", "Nothing until it is investigated",
    "Silently inside cost of sales", "A provision"], 2,
   "The arithmetic assumes whatever is missing was sold, so loss arrives as worse margin with no label.",
   "Ch2 §5", "Cost of sales"),
 Q("Which belongs in cost of sales rather than operating expenses?",
   ["Delivering goods to the customer", "Import duty on the goods",
    "The branch manager's salary", "Bank charges"], 1,
   "The test is whether the cost was incurred to get the goods ready to sell.", "Ch2 §7", "Cost of sales"),
 Q("Closing stock is understated by ₦1m. The effect on reported profit is:",
   ["Overstated ₦1m", "Understated ₦1m", "No effect", "Understated by the margin on ₦1m"], 1,
   "Understated closing stock overstates cost of sales by the same amount, depressing profit.",
   "Ch2 §6", "Cost of sales"),

 # Gross margin (6)
 Q("Revenue ₦50m, cost of sales ₦32.5m. Gross margin is:",
   ["₦17.5m", "35%", "65%", "54%"], 1,
   "17.5 ÷ 50 = 35%. The naira figure is gross profit; the percentage is margin.", "Ch3 §1", "Gross margin"),
 Q("Cost ₦800, selling price ₦1,000. The margin is:",
   ["25%", "20%", "80%", "125%"], 1,
   "200 ÷ 1,000 = 20%. The 25% figure is markup on cost.", "Ch3 §3", "Gross margin"),
 Q("Pricing for a 40% margin by adding 40% to cost actually achieves:",
   ["40%", "About 29%", "About 57%", "60%"], 1,
   "Adding 40% to cost gives a 28.6% margin. This confusion is expensive and common.", "Ch3 §3", "Gross margin"),
 Q("Imported goods bought at ₦1,600 to the dollar are repriced at ₦1,500. The effect is:",
   ["Higher margin", "Margin lost that selling effort cannot recover",
    "No effect until the goods are paid for", "A foreign exchange gain"], 1,
   "Buying price is one of the four movers of margin, and currency is the one nobody in the branch controls.",
   "Ch3 §6", "Gross margin"),
 Q("Which of the four movers of margin needs a merchandising response rather than a pricing one?",
   ["Selling price", "Buying price", "Mix", "Shrinkage"], 2,
   "Mix is about what you sell proportionally more of, so the remedy is what you promote and stock.",
   "Ch3 §7", "Gross margin"),
 Q("Gross margin has fallen two points with no price or supplier change. Look first at:",
   ["The tax charge", "Stock: count quality, cut-off and unrecorded write-offs",
    "Salaries", "Interest cost"], 1,
   "Most unexplained margin movement in retail and distribution is a stock problem.", "Ch2 §9", "Gross margin"),

 # Operating costs (5)
 Q("A second supervisor needed once a shop passes a certain size is an example of:",
   ["A fixed cost", "A variable cost", "A step cost", "A cost of sale"], 2,
   "Step costs hold flat then jump, which is why they surprise people.", "Ch4 §4", "Operating costs"),
 Q("Fixed cost ₦3m a month, gross margin 40%. Revenue needed to break even is:",
   ["₦3.0m", "₦4.2m", "₦7.5m", "₦12.0m"], 2,
   "₦3m ÷ 0.40 = ₦7.5m.", "Ch4 §6", "Operating costs"),
 Q("Operating expenses are best compared against:",
   ["Last month in naira", "Revenue, as a percentage", "The budget only", "Headcount"], 1,
   "Naira comparisons ignore whether the business grew. The percentage carries the meaning.",
   "Ch4 §8", "Operating costs"),
 Q("A large and vaguely named expense category matters because:",
   ["It is usually an error", "It is where uncontrolled spending accumulates unowned",
    "It attracts more tax", "It must be reallocated to cost of sales"], 1,
   "A line nobody owns is a line nobody questions.", "Ch4 §9", "Operating costs"),
 Q("A branch failing to cover its fixed base should first establish:",
   ["Which staff to cut", "Whether the gap is a revenue problem or a cost problem",
    "Whether to raise prices", "Whether to close"], 1,
   "Cutting the people who generate revenue turns a slow decline into a fast one.", "Ch4 §10", "Operating costs"),

 # Profit measures (5)
 Q("Operating profit deliberately excludes:",
   ["Salaries", "Interest and tax", "Depreciation", "Cost of sales"], 1,
   "Financing and tax are not the operating manager's doing, so the line answers whether the trading works.",
   "Ch5 §2", "Profit measures"),
 Q("Two units make identical operating profit; one carries heavy interest. This tells you:",
   ["One traded better", "They traded identically and are financed differently",
    "One has higher costs of sale", "One is more efficient"], 1,
   "Interest is a financing decision made above the unit.", "Ch5 §4", "Profit measures"),
 Q("Strong operating profit with negative net profit indicates:",
   ["A trading problem", "A financing problem", "A stock problem", "A pricing problem"], 1,
   "Selling harder will not fix the cost of debt.", "Ch5 §6", "Profit measures"),
 Q("The tax charge in the accounts and the tax paid in cash that period are:",
   ["Always equal", "Rarely equal — different bases and timing",
    "Equal in the final quarter", "Equal net of VAT"], 1,
   "Do not reconcile the tax line to the bank statement and expect agreement.", "Ch5 §7", "Profit measures"),
 Q("Somebody quotes 'profit' in a meeting without qualifying it. You should:",
   ["Assume net profit", "Assume gross profit", "Ask which one", "Assume operating profit"], 2,
   "In a business carrying debt the gap can be most of the number, and two people can be certain and opposed.",
   "Ch5 §9", "Profit measures"),

 # Non-cash costs (5)
 Q("₦30m of equipment over six years produces an annual depreciation charge of:",
   ["₦30m", "₦6m", "₦5m", "₦2.5m"], 2,
   "₦30m ÷ 6 = ₦5m a year.", "Ch6 §2", "Non-cash costs"),
 Q("Profit ₦4m with depreciation ₦2.5m means cash generated by trading is roughly:",
   ["₦1.5m", "₦4m", "₦6.5m", "₦2.5m"], 2,
   "Depreciation is added back because no money moved when it was charged.", "Ch6 §6", "Non-cash costs"),
 Q("Extending the assumed useful life of assets from three years to five:",
   ["Has no effect on profit", "Increases reported profit without anything changing in the business",
    "Reduces reported profit", "Increases cash"], 1,
   "It is judgement, entirely legitimate, and one of the quietest ways to improve a number.",
   "Ch6 §7", "Non-cash costs"),
 Q("Depreciation charged each month means the business:",
   ["Is saving to replace the asset", "Is recording use with no money moving",
    "Owes the supplier", "Has a cash reserve"], 1,
   "Nothing is set aside, which is why a profitable company can be unable to afford replacements.",
   "Ch6 §8", "Non-cash costs"),
 Q("Comparing two branches, one is charged rent for its building and the other occupies a group property free. This:",
   ["Is a fair comparison", "Makes the comparison unlike for like, possibly by more than the profits compared",
    "Affects only the balance sheet", "Affects only tax"], 1,
   "Check the basis before comparing units on profit.", "Ch6 §9", "Non-cash costs"),

 # Judgement lines (4)
 Q("An estimate of receivables not expected to be collected is:",
   ["An accrual", "A prepayment", "A provision", "A write-off"], 2,
   "A provision is expected but not certain, which makes it the most judgement-heavy line on the page.",
   "Ch7 §4", "Judgement lines"),
 Q("Thinning the bad debt provision to help hit a target is:",
   ["Fraud", "Judgement that borrows from next month", "Required by the standards", "A cash saving"], 1,
   "It improves this month's profit without anything improving in the business.", "Ch7 §6", "Judgement lines"),
 Q("A year's rent paid in advance sits on the balance sheet as:",
   ["An accrual", "A prepayment", "A provision", "A liability"], 1,
   "Only the month's share is a cost; the rest belongs to future months.", "Ch7 §3", "Judgement lines"),
 Q("The most useful question when a large write-off appears is:",
   ["Who authorised it", "How long it was true before anybody wrote it down",
    "Whether it is tax deductible", "Whether it can be reversed"], 1,
   "That answer tells you whether your reporting is working, which matters more than the amount.",
   "Ch7 §9", "Judgement lines"),

 # Reading a branch P&L (5)
 Q("Allocating head office cost on share of revenue means:",
   ["All branches pay equally", "The fastest-growing branch is charged most for growing",
    "The allocation is neutral", "Head office cost falls"], 1,
   "Every allocation basis is a choice with consequences.", "Ch8 §3", "Reading a branch P&L"),
 Q("Controllable profit for a branch manager excludes:",
   ["Branch waste", "Local marketing", "Allocated head office overhead", "Branch staff cost"], 2,
   "Holding a manager to a line they cannot influence teaches them the numbers are unfair.",
   "Ch8 §5", "Reading a branch P&L"),
 Q("A branch can be well run and still not worth keeping. This distinction requires:",
   ["One profit figure", "Reading controllable profit and contribution separately",
    "A revenue target", "A cash flow statement"], 1,
   "Collapsing both questions into one number usually leads to closing the wrong branch.",
   "Ch8 §6", "Reading a branch P&L"),
 Q("Raising the internal transfer price charged to branches:",
   ["Increases group profit", "Reduces group profit",
    "Moves apparent performance between units without changing group profit", "Increases group revenue"], 2,
   "Nothing entered or left the group.", "Ch8 §8", "Reading a branch P&L"),
 Q("A branch result looks surprising. Check first:",
   ["The manager's performance", "The allocation basis and transfer price",
    "The tax charge", "Interest cost"], 1,
   "Those two lines explain more surprising branch results than performance does.", "Ch8 §9", "Reading a branch P&L"),
]


def rebalance(items, seed):
    """Spread correct answers evenly across A-D by rotating each option list.

    Written after the first draft of this module came out 72% guessable — 29 of
    40 answers in position B. That is the same defect that made four legacy
    tracks passable by a candidate who had read nothing, and it is apparently
    what an author produces by default. Rotation preserves the option set, the
    correct answer and the distractor order; only the position changes.

    Deterministic, so re-running the builder reproduces the same paper.
    """
    import random
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
    rebalance(QUESTIONS, "finance:read_pl:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:read_pl:checks")
    mod = {
        "title": "Reading the Profit & Loss",
        "desc": ("For managers handed a P&L every month: what each line actually means, "
                 "why gross margin is the number to watch, which lines carry somebody's "
                 "judgement, and six questions that turn a statement into a decision. "
                 "Worked throughout in naira, on retail and distribution numbers."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }
    data = {"read_pl": mod}
    with io.open("academy_finance_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    import re
    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    for l, n in zip(mod["lessons"], lens):
        print("   %-52s %5d  (%d checks)" % (l["title"][:52], n, len(l["checks"])))
    import collections
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    tp = collections.Counter(q["topic"] for q in QUESTIONS)
    print("\nquestions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("topics:", dict(tp))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
