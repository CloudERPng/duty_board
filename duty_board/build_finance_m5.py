#!/usr/bin/env python3
"""Build the Understanding Cost module into academy_finance_data.json.

Track module 4, and the hinge of the course: modules 1 to 3 taught reading,
this one turns to deciding.

Builds on module 1's cost-behaviour chapter rather than repeating it. That
chapter introduced fixed, variable and step costs to explain the expense block
of a P&L. This module treats behaviour as a decision tool — relevant range,
splitting a mixed cost, contribution, and the costs that must be ignored.

The through-line: the same naira is several different numbers depending on the
question being asked, and using the wrong one is how competent managers reach
confident wrong answers.

Merges into the data file. Rebalance folded into the build.

Run from the app package directory:  python3 build_finance_m5.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "cost"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The same naira is several different numbers", 10, """<p>Ask a finance team what a crate of soft drinks costs you and a careful one will ask what you intend to do with the answer. That is not evasion. It is the single most important idea in costing, and the reason managers who are otherwise numerate reach confident wrong conclusions.</p>

<p><b>One crate, four legitimate costs.</b></p>

<p><b>₦4,800</b> — what you paid the supplier. The purchase cost, and the only figure everybody agrees on.</p>

<p><b>₦5,150</b> — with inbound freight and handling added. The landed cost, and what belongs in cost of sales.</p>

<p><b>₦6,400</b> — with a share of rent, salaries, power and vehicles loaded on. The fully absorbed cost, and what a costing report will usually show you.</p>

<p><b>₦5,150</b> again — what genuinely changes if you sell one more crate tonight, because the rent and the salaries are already being paid whatever you do. The marginal cost.</p>

<p>All four are correct. Each answers a different question, and the fully absorbed ₦6,400 is the one most likely to be quoted and the one most likely to be wrong for the decision in front of you.</p>

<p><b>Here is where it costs money.</b> A customer offers to take 400 crates at ₦6,000 each. The costing report says the crate costs ₦6,400, so the order shows a loss of ₦400 a crate and gets declined.</p>

<p>But nothing in that ₦6,400 changes because of this order. The rent is paid, the salaries are paid, the warehouse is already lit. What actually changes is ₦5,150 a crate. At ₦6,000 the order contributes ₦850 a crate — <b>₦340,000 of real money the business has just refused</b> because it used a number built for a different purpose.</p>

<p><b>The reverse error is equally expensive and less obvious.</b> A product priced off marginal cost alone looks profitable on every sale and never covers the overhead it depends on. Sell enough of it and the business is busier, larger and poorer.</p>

<p><b>So the discipline is not to find the true cost.</b> There is no such thing. The discipline is to ask what decision you are making, and then choose the cost that answers it:</p>

<p><b>What should our standing price be?</b> Absorbed cost — the price must cover everything over time.<br>
<b>Should we accept this one-off order?</b> Marginal cost — only what changes.<br>
<b>Is this product worth stocking at all?</b> Contribution against the shelf space it occupies.<br>
<b>Should we close this branch?</b> Only the costs that would actually stop.</p>

<p>Each of those has a chapter ahead of it. What they share is the habit of asking the question before reaching for the number, which is the opposite of how most costing conversations begin.</p>

<blockquote>WATCH-OUT: When somebody quotes "the cost" of anything in a meeting, the useful question is what is inside it. In most businesses the answer is a fully absorbed figure — appropriate for pricing, misleading for almost every other decision, and quoted for all of them.</blockquote>

<p><b>Why businesses default to the absorbed number.</b> It is the one the accounting system produces, because stock has to be valued for the balance sheet and that valuation must include a share of overhead. So the figure exists for a statutory reason, it is calculated monthly whether anyone asks or not, and it is therefore the number lying nearest to hand when a decision comes up. Convenience, not suitability, is why it gets used — and knowing that is half the defence against it.</p>""",
 [C("A crate costs ₦5,150 landed and ₦6,400 fully absorbed. A one-off order at ₦6,000 a crate:",
    ["Loses ₦400 a crate and should be declined", "Contributes ₦850 a crate and is worth taking",
     "Breaks even", "Cannot be assessed without the margin"], 1,
    "The absorbed overhead is being paid whatever you do. Only the ₦5,150 changes because of this order."),
  C("Which cost should set your standing list price?",
    ["Marginal cost", "Purchase cost", "Fully absorbed cost", "Landed cost"], 2,
    "Over time the price must cover everything, or the overhead is never recovered."),
  C("The right first question when somebody quotes 'the cost' is:",
    ["Is it accurate", "What is inside it, and what decision is it for",
     "Does it include VAT", "Who calculated it"], 1,
    "There is no single true cost. Each version answers a different question.")]),

("Cost behaviour as a decision tool", 10, """<p>Module 1 introduced fixed, variable and step costs to make sense of the expense block on a P&L. That was description. This chapter uses the same classification to predict — which is a harder and more useful thing.</p>

<p><b>The prediction question is always the same: if activity changes by X, what happens to cost?</b> Answer that and you can evaluate almost any operational decision without waiting for finance.</p>

<p><b>The qualification textbooks skip and practitioners live with: the relevant range.</b> Rent is fixed — within the range of activity your current premises can handle. Push volume past that and you need a second warehouse, and the fixed cost steps. Every fixed cost is fixed only across some band of activity, and knowing where your bands end is worth more than the classification itself.</p>

<p>A manager who knows their branch can handle 40% more volume before anything structural changes holds a genuinely valuable piece of information. Growth inside that band is enormously profitable; growth just past it is not, and the difference is invisible on any report.</p>

<p><b>Most real costs are mixed, and pretending otherwise is the commonest costing error.</b> A generator has a standing cost — servicing, maintenance, the capital tied up — plus diesel that moves with hours run. A delivery operation has drivers on salary plus fuel that varies with distance. Treating either as purely fixed or purely variable will give you a wrong answer, and the direction of the error depends on which way volume moves.</p>

<p><b>Splitting a mixed cost, with arithmetic you can do yourself.</b> Take the highest and lowest activity months of the last year.</p>

<p>Busiest month: 2,400 deliveries, transport cost ₦3,800,000.<br>
Quietest month: 1,200 deliveries, transport cost ₦2,600,000.</p>

<p>The difference is ₦1,200,000 across 1,200 deliveries, so the variable element is <b>₦1,000 per delivery</b>. At 1,200 deliveries the variable part is ₦1,200,000, so the fixed element is ₦2,600,000 − ₦1,200,000 = <b>₦1,400,000 a month</b>.</p>

<p>Now you can predict. Three thousand deliveries next month should cost about ₦1,400,000 + ₦3,000,000 = ₦4,400,000. If it comes in at ₦5,200,000, you have a specific question to ask rather than a vague sense that transport is expensive.</p>

<p><b>The method's honest limitation.</b> Two data points, both of them extremes, and either might be atypical — a month with a fuel crisis or a vehicle off the road distorts it completely. Use several years' points and look at the pattern if you can. But even the crude version, done on your own numbers, beats the alternative of having no idea which part of a cost you can influence.</p>

<blockquote>IMPLEMENTATION TIP: Split your three largest controllable costs into fixed and variable elements once, using twelve months of data. You only have to do it properly once a year, and it converts every subsequent volume conversation from opinion into arithmetic.</blockquote>

<p><b>A caution about cost per unit.</b> Dividing total cost by volume produces a figure that changes every month purely because volume changed, and people read the movement as a cost problem. If fixed cost is ₦1.4m and you make 1,400 deliveries, that is ₦1,000 a delivery of fixed cost; at 2,800 deliveries it is ₦500. Nothing got cheaper. Cost per unit is a useful summary and a terrible trend line, and comparing it month to month in a seasonal business tells you about seasonality rather than efficiency.</p>""",
 [C("Busiest month 2,400 deliveries at ₦3.8m; quietest 1,200 at ₦2.6m. The variable cost per delivery is:",
    ["₦1,583", "₦1,000", "₦2,167", "₦583"], 1,
    "₦1.2m of extra cost across 1,200 extra deliveries. The fixed element is then ₦1.4m a month."),
  C("A fixed cost is fixed:",
    ["Permanently", "Only within a relevant range of activity",
     "Until inflation changes it", "Unless volume falls"], 1,
    "Push past the band your current premises or team can handle and the fixed cost steps."),
  C("Treating a generator cost as purely variable would:",
    ["Be accurate enough", "Understate cost at low activity and overstate it at high activity",
     "Overstate cost at low activity", "Have no effect on decisions"], 1,
    "It has a standing element regardless of hours run, so a purely variable model misses it at low volumes.")]),

("Direct and indirect: the second axis", 10, """<p>Fixed and variable answers <i>how does this cost move</i>. Direct and indirect answers a different question: <i>can we trace this cost to the thing we are measuring</i>. The two axes are independent, and confusing them is why costing conversations go in circles.</p>

<p><b>Direct costs</b> can be traced to a specific product, branch or job without arbitrary judgement. The goods themselves, the packaging on that product, the delivery run made for that customer, the wages of staff working only in that branch.</p>

<p><b>Indirect costs</b> — overheads — are incurred for the business generally and have to be shared out by some rule. The MD's salary, group insurance, head office rent, the finance team, the ERP subscription.</p>

<p><b>Now the point that catches people.</b> A cost can be direct and fixed at the same time: a branch manager's salary is fixed in amount and directly traceable to that branch. A cost can be indirect and variable: head office power rises with activity across the group but belongs to no single branch. Four combinations, all common, and neither axis tells you the other.</p>

<p><b>What is direct depends entirely on what you are measuring.</b> This is the sentence to keep.</p>

<p>Branch rent is <i>direct</i> to the branch — trace it exactly. That same rent is <i>indirect</i> to any single product sold inside the branch, because no product caused it. Change the unit of measurement and the classification changes with it, without a single naira moving.</p>

<p>So "is this a direct cost?" is an incomplete question. "Direct to what?" is the whole of it.</p>

<p><b>Why this matters practically.</b> The proportion of your cost base that is indirect determines how much of any product or branch profitability figure is judgement rather than fact. A business where 80% of costs are direct produces product margins you can broadly trust. A business where 45% of costs are indirect produces product margins that are largely an artefact of the sharing rule — and people will still argue about them to two decimal places.</p>

<p><b>The practical response is not more precise allocation.</b> It is knowing which figures are solid. Direct costs are evidence. Allocated costs are a convention that somebody chose, usually years ago, often for a business that no longer exists in that shape. Treat the first as fact and the second as an assumption you are entitled to question.</p>

<blockquote>IMPLEMENTATION TIP: Ask what percentage of your total cost base is allocated rather than traced. If it is small, product and branch comparisons are meaningful. If it is large, the ranking of your products by profitability is substantially a ranking of the allocation rule, and it deserves far less confidence than it usually receives.</blockquote>

<p><b>One structural consequence worth noticing.</b> The share of costs that are indirect has risen almost everywhere over the last few decades — systems, compliance, management, marketing, all of which serve everything and belong to nothing. So costing has become progressively less certain at exactly the time reports have become more precise-looking. A modern costing report carries more decimal places and less evidence than one from thirty years ago, and the confidence it invites is not warranted by the arithmetic behind it.</p>""",
 [C("A branch manager's salary is:",
    ["Direct and variable", "Indirect and fixed", "Direct and fixed", "Indirect and variable"], 2,
    "Fixed in amount and traceable to that branch. The two axes are independent."),
  C("Branch rent, when measuring the profitability of one product sold there, is:",
    ["Direct", "Indirect", "Variable", "Marginal"], 1,
    "No product caused it. What counts as direct depends entirely on what you are measuring."),
  C("If 45% of the cost base is allocated rather than traced, product profitability rankings are:",
    ["Reliable to two decimal places", "Substantially a ranking of the allocation rule",
     "Understated", "Independent of overhead"], 1,
    "Direct costs are evidence; allocated costs are a convention somebody chose.")]),

("Absorption: how overhead lands on a product", 10, """<p>Somebody has to decide how the MD's salary reaches a crate of soft drinks. Absorption costing is the machinery that does it, and the machinery is entirely a set of choices.</p>

<p><b>The mechanism, in three steps.</b> Total the overhead for a period. Choose a basis of absorption — units, labour hours, machine hours, floor space, revenue. Divide one by the other to get a rate, then apply that rate to each unit.</p>

<p>Overhead of ₦12,000,000 across 30,000 units gives ₦400 a unit. Simple, defensible, and quietly full of assumptions.</p>

<p><b>Watch what the choice of basis does.</b> A business makes two products. Product A is bulky, slow-moving, occupies half the warehouse and sells 5,000 units. Product B is compact, fast, occupies a tenth of the space and sells 25,000 units.</p>

<p>Absorb the ₦12,000,000 <b>by unit</b>: every unit carries ₦400, so A absorbs ₦2,000,000 and B absorbs ₦10,000,000.<br>
Absorb it <b>by floor space</b>: A carries half the warehouse, so A absorbs ₦6,000,000 and B far less.</p>

<p>Product A's apparent cost has tripled and nothing physical has changed. If A's price was set from its absorbed cost, the business has just decided A is unprofitable — or profitable — purely on the strength of a rule chosen in a meeting.</p>

<p><b>Which basis is right?</b> The one that best reflects what actually causes the overhead. If most of your overhead is warehouse-driven, space is a better basis than units. If it is driven by handling and picking, transactions are better. If it is genuinely general and unrelated to any of these, then any basis is arbitrary, and the honest response is to admit that rather than dress it up.</p>

<p><b>Under- and over-absorption, briefly.</b> The rate is set in advance using expected volume. If actual volume comes in lower, less overhead is absorbed than was actually incurred, and the shortfall lands in the P&L as a variance. This is why a quiet month can carry an unexplained-looking cost with no operational cause: the overhead was always there, and fewer units carried it.</p>

<p><b>What a manager should take from this.</b> Absorbed product costs are useful for pricing and for stock valuation, which is what they exist for. They are poor at answering whether to accept an order, drop a line, or keep a branch — because every one of those decisions turns on what would <i>change</i>, and absorbed overhead mostly would not.</p>

<blockquote>WATCH-OUT: Beware any decision to discontinue a product on the strength of its absorbed cost. Drop it and the overhead does not leave with it — it redistributes onto everything that remains, making the next product look unprofitable. Businesses have shrunk themselves out of existence one rational-looking discontinuation at a time.</blockquote>

<p><b>The death-spiral, since it has a name and a shape.</b> Drop the product carrying the least; the overhead redistributes; the next-weakest product now looks unprofitable; drop that one too. Each step is defensible on its own numbers, and the sequence ends with a business carrying its whole overhead on a handful of lines that cannot possibly support it. The error is not in any single decision — it is in using a number that assumes the overhead will follow the product out of the door, when it never does.</p>""",
 [C("Overhead ₦12m absorbed across 30,000 units gives a rate of:",
    ["₦4,000", "₦400", "₦40", "₦1,200"], 1,
    "12,000,000 ÷ 30,000 = ₦400 a unit, before asking whether units are the right basis."),
  C("Switching the absorption basis from units to floor space changes a product's cost because:",
    ["The overhead total changed", "The rule for sharing changed, though nothing physical did",
     "Volumes changed", "The product became more expensive to make"], 1,
    "A bulky slow line absorbs far more on space than on units, and no naira has moved."),
  C("Discontinuing a product because its absorbed cost exceeds its price risks:",
    ["Nothing — it was loss-making", "The overhead redistributing onto everything that remains",
     "A stock write-down", "Higher direct costs"], 1,
    "Businesses have shrunk out of existence one rational-looking discontinuation at a time.")]),

("Contribution: the number for one-off decisions", 10, """<p>Contribution is selling price less variable cost. That is the whole definition, and it is the most useful number in operational decision-making because it answers exactly one question cleanly: <b>how much does this sale contribute toward the costs I am paying anyway?</b></p>

<p>A crate sells at ₦7,200 with variable cost ₦5,150. Contribution is ₦2,050, or 28% of the selling price. That ₦2,050 goes toward the rent, the salaries and the power — and once those are covered, toward profit.</p>

<p><b>Why this beats profit per unit for short-run decisions.</b> Profit per unit includes absorbed overhead, which does not change with the decision. Contribution includes only what changes. So when the question is "should we do this <i>as well as</i> what we already do", contribution is the right instrument and profit per unit is actively misleading.</p>

<p><b>The bulk order, worked properly.</b> Four hundred crates at ₦6,000 against variable cost ₦5,150 gives contribution of ₦850 a crate — ₦340,000 in total. Provided it does not displace full-price sales, does not need extra fixed resource, and does not damage what you charge everybody else, it is worth taking, and the absorbed-cost view that called it a ₦160,000 loss was answering a question nobody asked.</p>

<p><b>Three conditions, and they are where judgement actually lives.</b></p>

<p><b>Does it displace better business?</b> If the 400 crates would otherwise have sold at ₦7,200, you have not gained ₦340,000 — you have lost ₦480,000. Contribution analysis assumes spare capacity, and the assumption is often wrong.</p>

<p><b>Does it need new fixed cost?</b> If serving it requires a vehicle or a shift, that cost is not fixed for this decision — it is caused by it, and it belongs in the arithmetic.</p>

<p><b>What does it do to your price everywhere else?</b> This is the one that does the real damage. A discount that becomes known becomes the price. The ₦340,000 is a single transaction; a repriced customer base is permanent.</p>

<p><b>Contribution per unit of the scarce thing.</b> When something is genuinely limited — shelf space, cold storage, delivery slots, working capital — the product with the highest contribution per unit is not necessarily the one to push. What matters is contribution per unit of whatever is scarce. A line contributing ₦2,050 per crate but occupying four times the space of one contributing ₦900 is the worse use of a full warehouse, and the ranking by contribution alone would tell you the opposite.</p>

<blockquote>IMPLEMENTATION TIP: Know the contribution percentage of your top ten lines. It takes an afternoon, it changes what you promote, and it is the number that tells you what an extra naira of sales is actually worth — which is never the same as the margin printed on the price list.</blockquote>

<p><b>Contribution also reframes what a discount actually costs.</b> A 10% discount on a ₦7,200 crate is ₦720 off the price — but it comes entirely out of the ₦2,050 contribution, which is a 35% cut in what the sale is worth to you. To stand still you would need to sell roughly 54% more crates. That arithmetic is worth doing before any promotion is approved, because discount conversations are almost always conducted in percentage-of-price terms while the damage lands in percentage-of-contribution.</p>""",
 [C("Selling price ₦7,200, variable cost ₦5,150. Contribution is:",
    ["₦7,200", "₦2,050", "₦5,150", "₦850"], 1,
    "Price less variable cost. It goes toward fixed costs first, then profit."),
  C("The bulk order at ₦6,000 would otherwise have sold at ₦7,200. Accepting it:",
    ["Gains ₦340,000", "Loses ₦480,000 of contribution you already had",
     "Is neutral", "Gains ₦340,000 less overhead"], 1,
    "Contribution analysis assumes spare capacity. Displacing full-price sales inverts the answer."),
  C("With warehouse space scarce, products should be ranked by:",
    ["Contribution per unit", "Contribution per unit of space occupied",
     "Absorbed profit per unit", "Selling price"], 1,
    "Rank by contribution per unit of whatever is genuinely limited, not per unit sold.")]),

("Break-even and the margin of safety", 10, """<p>Break-even is the volume at which contribution exactly covers fixed cost — the point where the business stops losing and has not yet started earning. Module 1 mentioned it in passing; here it becomes a working tool.</p>

<p><b>The arithmetic.</b> Fixed costs divided by contribution per unit gives break-even in units. Fixed costs divided by contribution percentage gives it in revenue.</p>

<p>A branch carries ₦5,200,000 of monthly fixed cost and earns 28% contribution. Break-even revenue is ₦5,200,000 ÷ 0.28 = <b>₦18,570,000 a month</b>. Below that the branch loses money however busy it looks; above it, 28 kobo in every extra naira falls to profit.</p>

<p><b>The margin of safety is the number worth reporting.</b> If that branch is currently doing ₦24,000,000, it is ₦5,430,000 above break-even — a margin of safety of about 23%. Sales could fall 23% before the branch loses money.</p>

<p>That single percentage tells a manager more about their exposure than the profit figure does. Two branches both making ₦1,500,000 a month, one with a 40% margin of safety and one with 8%, are in entirely different positions, and only the second should keep you awake.</p>

<p><b>Where the model quietly lies, and it is worth knowing before you rely on it.</b></p>

<p>It assumes fixed costs stay fixed — but they step, so break-even is not one point but a staircase. It assumes contribution percentage is constant, when in practice mix and discounting move it monthly. And it assumes you can sell whatever volume the arithmetic requires, which is the assumption most likely to be untrue.</p>

<p>None of that makes it useless. It makes it a planning tool rather than a prediction: it tells you the shape of the risk, not the date of the outcome.</p>

<p><b>Where it earns its keep.</b> Deciding whether a new branch is viable — what volume must it reach, and is that plausible in that location? Judging whether a fixed-cost increase is affordable — a ₦600,000 rent rise at 28% contribution needs ₦2,140,000 of extra monthly revenue to stand still, which is a far more concrete question than "can we afford it?" And knowing, in a downturn, how much room you have before decisions become urgent.</p>

<blockquote>IMPLEMENTATION TIP: Any proposed increase in fixed cost should be converted into the extra revenue required to cover it before anyone approves it. Divide the increase by your contribution percentage. It reframes "it's only ₦600,000 a month" into "we need ₦2.1m more revenue every month, forever", which is the question actually being asked.</blockquote>

<p><b>Break-even for a whole business versus a branch.</b> A branch's break-even should be calculated on the fixed costs the branch actually causes, not including allocated head office — otherwise you are measuring the branch against a burden it cannot influence. Calculate it both ways if you like: the first tells you whether the branch works as an operation, the second tells you what it needs to reach to carry its share. They are different questions and both are legitimate, provided nobody confuses one for the other.</p>""",
 [C("Fixed cost ₦5.2m a month, contribution 28%. Break-even revenue is about:",
    ["₦5.2m", "₦14.6m", "₦18.6m", "₦26.0m"], 2,
    "5.2m ÷ 0.28 ≈ ₦18.6m. Below it the branch loses money however busy it looks."),
  C("A branch at ₦24m revenue with break-even at ₦18.6m has a margin of safety of about:",
    ["5%", "23%", "44%", "77%"], 1,
    "Sales could fall about 23% before it loses money. It says more about exposure than the profit figure does."),
  C("A ₦600,000 monthly rent rise at 28% contribution requires extra monthly revenue of:",
    ["₦600,000", "₦2.1m", "₦168,000", "₦840,000"], 1,
    "600,000 ÷ 0.28 ≈ ₦2.14m, forever — which is the question actually being asked.")]),

("Relevant cost: what actually changes", 10, """<p>Every decision has exactly one costing question behind it: <b>what will be different if I say yes?</b> Costs that differ between the options are relevant. Costs that do not are noise, however large and however carefully calculated.</p>

<p><b>Three tests, and a cost must pass all three.</b> It must be in the <i>future</i> — money already spent cannot be changed by today's decision. It must be a <i>cash</i> flow — depreciation and allocated overhead are accounting entries, not money moving. And it must <i>differ</i> between the options.</p>

<p><b>Worked: should we deliver with our own fleet or use a third party?</b></p>

<p>The internal costing says own-fleet delivery costs ₦2,400 a drop, made up of ₦900 fuel and driver time, ₦600 vehicle depreciation, ₦400 allocated transport-office overhead, and ₦500 allocated head office. A third party quotes ₦1,800 a drop, and the switch looks like an obvious ₦600 saving.</p>

<p>Now apply the tests. The ₦900 is real, in the future, and would stop — relevant. The ₦600 depreciation is not cash and the vehicles are already bought — not relevant unless they can be sold, in which case the sale proceeds are relevant instead. The ₦400 transport office partly disappears if you close it — relevant to the extent it actually stops. The ₦500 head office allocation does not change at all — irrelevant.</p>

<p>So the honest comparison is ₦900 plus whatever part of the ₦400 genuinely stops, against ₦1,800. Outsourcing probably costs <i>more</i>, not less. The ₦600 saving was an artefact of comparing a fully absorbed internal number against a market price — and this specific mistake is made in boardrooms constantly.</p>

<p><b>The general shape of it.</b> Comparing an absorbed internal cost to an external quote is not a like-for-like comparison, because the external quote contains the supplier's overhead and profit while your internal figure contains overhead that will still be there after you outsource. Outsourcing decisions made this way are systematically biased toward outsourcing.</p>

<p><b>The question that cuts through it.</b> For every line in the internal cost, ask: <i>if we outsource tomorrow, does this payment stop?</i> If yes, it belongs in the comparison. If no, it does not, however genuinely the business incurs it.</p>

<blockquote>WATCH-OUT: Allocated head office cost is the most common irrelevant cost in real decisions, and the hardest to exclude politically — because a branch or department is being charged for it and feels it. Feeling a cost and being able to remove it are different things, and only the second matters to the decision.</blockquote>

<p><b>One relevant cost that is regularly forgotten.</b> The cost of the change itself. Redundancy, contract exit penalties, retraining, the dip in service while a new supplier learns your business, management time consumed for six months. These are future, cash, and entirely caused by the decision — which makes them as relevant as anything in the comparison, and they are routinely left out because they are one-off and awkward to estimate. A switch that saves ₦200,000 a month and costs ₦4m to execute takes twenty months to break even, and that fact belongs in the paper.</p>""",
 [C("A cost is relevant to a decision only if it is:",
    ["Large", "Future, cash, and different between the options",
     "Directly traceable", "In the budget"], 1,
    "All three tests must pass. Failing any one makes the cost noise, however carefully calculated."),
  C("Vehicle depreciation on vehicles you already own, when comparing to outsourcing, is:",
    ["Relevant — it is a real cost", "Not relevant unless the vehicles can be sold",
     "Relevant only if fully depreciated", "Relevant at half value"], 1,
    "It is not cash and the money is already spent. If they can be sold, the proceeds are what matters."),
  C("Comparing a fully absorbed internal cost to an external quote is biased because:",
    ["External quotes are always higher", "Your overhead remains after outsourcing while the quote contains theirs",
     "Internal costs exclude VAT", "It ignores depreciation"], 1,
    "It makes outsourcing look cheaper than it is, systematically.")]),

("Sunk cost, opportunity cost, and how decisions go wrong", 10, """<p>Two ideas account for a large share of the bad decisions made by intelligent people, and both are about costs that feel real and are not what they seem.</p>

<p><b>Sunk cost: money already spent, unrecoverable, and irrelevant to every decision from now on.</b></p>

<p>You have spent ₦8,000,000 developing a product line. Completing it needs ₦3,000,000 more, and the honest revenue forecast is now ₦2,500,000. The instinct is that abandoning it wastes ₦8,000,000. It does not. The ₦8,000,000 is gone in both scenarios — the only live question is whether spending ₦3,000,000 to earn ₦2,500,000 is sensible, and it plainly is not.</p>

<p>The ₦8,000,000 belongs in a review of how the decision was made. It has no place in deciding what to do next.</p>

<p><b>Why it is so hard.</b> Abandoning feels like admitting the ₦8,000,000 was wasted, and continuing postpones that admission. So the money is protected by spending more of it, and organisations do this at every scale — stock nobody will buy held rather than marked down, a branch kept open because of the fit-out cost, a system persisted with because of what was paid for it.</p>

<p><b>The test that helps:</b> if you were arriving today, with the ₦8,000,000 already gone and no history, what would you do? That is the right answer, and the only thing making it feel wrong is authorship.</p>

<p><b>Opportunity cost: the value of what you give up by choosing this instead of the best alternative.</b> It never appears in any accounting system, and it is frequently the largest cost in the decision.</p>

<p>Using a warehouse bay for slow-moving stock has no invoice attached. But if that bay could hold fast-moving lines contributing ₦450,000 a month, the slow stock costs ₦450,000 a month to keep — a cost no report will ever show you. The same applies to a manager's time, to working capital tied up, and to the credit you extend to a slow customer instead of a prompt one.</p>

<p><b>The two together explain most stubborn commercial mistakes.</b> Dead stock is held because of what was paid for it — sunk cost — while it occupies space that could earn — opportunity cost. Both forces point the same way, and neither appears on the P&L. Which is why marking down and clearing dead stock feels like accepting a loss when it is actually stopping one.</p>

<blockquote>IMPLEMENTATION TIP: When arguing about whether to persist with something, ban the original spend from the conversation for ten minutes and decide on the future alone. If the answer changes when the history is excluded, the history was doing the deciding.</blockquote>

<p><b>Where sunk cost thinking is legitimate, and it is narrow.</b> The original spend matters for accountability — reviewing how a decision was made, and learning from it — and it matters for accounting, because the write-off has to be recognised. Neither of those is the same as letting it influence what you do next. Keep the two conversations separate and hold them on different days if necessary: what should we do now, and separately, what does this teach us. Merging them guarantees that the second corrupts the first.</p>""",
 [C("₦8m spent, ₦3m needed to finish, revised forecast ₦2.5m. You should:",
    ["Finish it — ₦8m is already invested", "Stop: the live question is ₦3m spent to earn ₦2.5m",
     "Finish it to recover part of the ₦8m", "Spend ₦3m and reassess"], 1,
    "The ₦8m is gone in both scenarios and belongs in a review of the decision, not in the decision."),
  C("Slow stock occupying a bay that could hold lines contributing ₦450,000 a month costs:",
    ["Nothing — the space is already paid for", "₦450,000 a month in opportunity cost",
     "Only its storage share", "Its purchase price annually"], 1,
    "It never appears in any accounting system and is frequently the largest cost in the decision."),
  C("The test for a suspected sunk-cost decision is:",
    ["How much has been spent so far", "Whether the original decision was reasonable",
     "What you would do arriving today with no history", "Whether the spend can be capitalised"], 2,
    "If the answer changes when history is excluded, the history was doing the deciding.")]),

("Costing questions for the decisions you face", 10, """<p>This is the chapter to keep. Five decisions every operating manager meets, and the costing question that answers each — because using the wrong one is not a technicality, it is how a reasonable manager reaches a confident wrong answer.</p>

<p><b>1. Should we accept this one-off order below list price?</b></p>

<p>Ask for contribution: price less variable cost. Then the three conditions — does it displace full-price business, does it need new fixed resource, and what does it do to your pricing everywhere else? If it passes all three and contributes anything, it is worth taking. <i>Do not</i> use absorbed cost.</p>

<p><b>2. Should we discontinue this product or branch?</b></p>

<p>Ask what costs would actually stop. Compare that against the contribution lost. A branch showing an absorbed loss of ₦900,000 a month while contributing ₦1,400,000 toward group overhead makes the group ₦1,400,000 worse off by closing — the overhead does not close with it. This is the single most expensive misuse of absorbed cost there is.</p>

<p><b>3. Should we make it ourselves or buy it in?</b></p>

<p>Ask which payments genuinely stop, and compare only those against the quote. Add the opportunity cost of whatever the internal capacity would otherwise do. Exclude sunk investment and unavoidable overhead.</p>

<p><b>4. Can we afford this increase in fixed cost?</b></p>

<p>Divide it by your contribution percentage to get the extra revenue needed to stand still. Then ask, plainly, whether that volume is achievable in your market. Approving fixed cost without doing this division is how a break-even creeps upward until a normal month becomes a losing one.</p>

<p><b>5. Which products should we push, given limited space, capital or delivery slots?</b></p>

<p>Rank by contribution per unit of the constraint, not per unit sold, and not by margin percentage. The right answer frequently contradicts both.</p>

<p><b>The habit underneath all five.</b> Before reaching for any number, say out loud what would be different if the answer were yes. That sentence — not the report — determines which cost is the right one. It takes fifteen seconds and it is the difference between costing that informs decisions and costing that decorates them.</p>

<p><b>And the caution to end on.</b> Contribution answers short-run questions. Over time, every cost is variable and everything must be covered: a business pricing permanently on contribution will be busy, growing and unprofitable. Use contribution for the decision at the margin, absorbed cost for the standing price, and know which question you are answering.</p>

<blockquote>IMPLEMENTATION TIP: Keep the five questions where you take decisions. The commonest costing error in business is not arithmetic — it is a correct calculation answering the wrong question, presented confidently, and acted on.</blockquote>

<p><b>What this module has actually given you.</b> Not a costing system — you have one of those and finance runs it. What you now have is the ability to interrogate the number in front of you: to ask what is inside it, whether it would change if the decision changed, and whether it answers the question being asked. That is a small skill and it is the one that separates a manager who is guided by their costing reports from one who is governed by them.</p>""",
 [C("A branch shows an absorbed loss of ₦900,000 but contributes ₦1.4m toward group overhead. Closing it:",
    ["Saves ₦900,000 a month", "Makes the group ₦1.4m a month worse off",
     "Is neutral", "Saves ₦500,000 a month"], 1,
    "The overhead does not close with the branch. This is the most expensive misuse of absorbed cost there is."),
  C("Pricing permanently on contribution rather than absorbed cost produces a business that is:",
    ["Highly profitable", "Busy, growing and unprofitable",
     "Under-priced but stable", "Over-priced"], 1,
    "In the long run every cost is variable and everything must be covered."),
  C("Before choosing a cost figure, the fifteen seconds best spent are on:",
    ["Verifying the arithmetic", "Naming what would actually be different if you said yes",
     "Checking who prepared the report", "Confirming the absorption basis"], 1,
    "That sentence decides which number is the right one, and it is the step almost always skipped.")]),
]


QUESTIONS = [
 Q("Purchase ₦4,800, landed ₦5,150, absorbed ₦6,400. Which belongs in cost of sales?", ["₦4,800", "₦5,150", "₦6,400", "The average"], 1,
   "Landed cost includes freight and duty needed to get goods sellable.", "Ch1 §3", "What a cost is"),
 Q("Which cost answers 'should we take this one-off order?'", ["Absorbed", "Marginal", "Purchase", "Standard"], 1,
   "Only what actually changes because of the order is relevant.", "Ch1 §7", "What a cost is"),
 Q("An order at ₦6,000 against landed ₦5,150 and absorbed ₦6,400 contributes:", ["A ₦400 loss", "₦850 a crate", "₦1,200 a crate", "Nothing"], 1,
   "The absorbed overhead is paid whatever you do.", "Ch1 §6", "What a cost is"),
 Q("Pricing permanently off marginal cost produces a business that is:", ["Highly profitable", "Busier, larger and poorer", "Under-stocked", "Over-priced"], 1,
   "It never covers the overhead it depends on.", "Ch1 §8", "What a cost is"),
 Q("The correct first question about any quoted cost is:", ["Is it accurate", "What is inside it and what decision is it for", "Who prepared it", "Does it include VAT"], 1,
   "There is no single true cost; each version answers a different question.", "Ch1 §10", "What a cost is"),
 Q("2,400 deliveries cost ₦3.8m; 1,200 cost ₦2.6m. Fixed element per month is:", ["₦2.6m", "₦1.4m", "₦1.2m", "₦3.8m"], 1,
   "Variable is ₦1,000 a delivery; at 1,200 that is ₦1.2m, leaving ₦1.4m fixed.", "Ch2 §7", "Cost behaviour"),
 Q("On that model, 3,000 deliveries should cost about:", ["₦3.0m", "₦4.4m", "₦4.75m", "₦5.2m"], 1,
   "₦1.4m fixed plus 3,000 × ₦1,000.", "Ch2 §8", "Cost behaviour"),
 Q("The relevant range is:", ["The range of prices customers accept", "The band of activity over which a fixed cost stays fixed", "The margin range", "The forecast period"], 1,
   "Knowing where your bands end is worth more than the classification itself.", "Ch2 §4", "Cost behaviour"),
 Q("The high-low method's main weakness is:", ["It needs a year of data", "It uses two points, both extremes, either of which may be atypical", "It ignores fixed costs", "It requires machine hours"], 1,
   "A fuel crisis or a vehicle off the road distorts it completely.", "Ch2 §9", "Cost behaviour"),
 Q("Growth within the relevant range is:", ["Equally profitable as growth beyond it", "Far more profitable, because nothing structural changes", "Less profitable", "Impossible to measure"], 1,
   "The difference is invisible on any report, which is why knowing the band matters.", "Ch2 §5", "Cost behaviour"),
 Q("Head office power, rising with group activity, is:", ["Direct and variable", "Indirect and variable", "Direct and fixed", "Indirect and fixed"], 1,
   "It moves with activity but belongs to no single branch.", "Ch3 §4", "Direct and indirect"),
 Q("'Is this a direct cost?' is incomplete because:", ["Costs change over time", "Direct depends entirely on what is being measured", "VAT must be excluded", "It ignores behaviour"], 1,
   "Branch rent is direct to the branch and indirect to any product sold in it.", "Ch3 §6", "Direct and indirect"),
 Q("A business with 80% direct costs produces product margins that are:", ["Largely artefacts of allocation", "Broadly trustworthy", "Impossible to compare", "Always overstated"], 1,
   "Direct costs are evidence; allocated costs are a convention.", "Ch3 §8", "Direct and indirect"),
 Q("The practical response to a heavily allocated cost base is:", ["More precise allocation rules", "Knowing which figures are solid and treating the rest as assumptions", "Ignoring overhead", "Allocating by revenue"], 1,
   "Precision in an arbitrary rule does not make it less arbitrary.", "Ch3 §9", "Direct and indirect"),
 Q("Overhead ₦12m over 30,000 units gives an absorption rate of:", ["₦40", "₦400", "₦4,000", "₦1,200"], 1,
   "Before asking whether units are the right basis at all.", "Ch4 §3", "Absorption and allocation"),
 Q("A bulky slow-moving line absorbs far more overhead when the basis changes from units to:", ["Revenue", "Floor space", "Labour hours", "Transactions"], 1,
   "Its apparent cost can triple with nothing physical changing.", "Ch4 §5", "Absorption and allocation"),
 Q("The best basis of absorption is the one that:", ["Is simplest to calculate", "Best reflects what actually causes the overhead", "Produces the highest margins", "Matches the budget"], 1,
   "If the overhead is genuinely general, any basis is arbitrary and it is better to say so.", "Ch4 §7", "Absorption and allocation"),
 Q("Under-absorption in a quiet month happens because:", ["Overhead rose", "Fewer units carried an overhead that was always there", "Prices fell", "Variable costs rose"], 1,
   "The rate was set on expected volume, and actual volume came in lower.", "Ch4 §8", "Absorption and allocation"),
 Q("Absorbed product cost is genuinely useful for:", ["Accepting one-off orders", "Pricing and stock valuation", "Branch closure decisions", "Make-or-buy decisions"], 1,
   "It is poor at every decision that turns on what would change.", "Ch4 §9", "Absorption and allocation"),
 Q("Contribution is:", ["Revenue less all costs", "Selling price less variable cost", "Gross profit less overhead", "Price less absorbed cost"], 1,
   "It measures what a sale contributes toward costs you are paying anyway.", "Ch5 §1", "Contribution"),
 Q("Contribution beats profit per unit for short-run decisions because:", ["It is larger", "It includes only what changes with the decision", "It includes overhead", "It is easier to calculate"], 1,
   "Absorbed overhead does not change with the decision, so including it misleads.", "Ch5 §3", "Contribution"),
 Q("The most damaging of the three conditions on a discounted bulk order is usually:", ["It might displace full-price sales", "It might need new fixed cost", "What it does to your price everywhere else", "The delivery cost"], 2,
   "A single transaction against a permanently repriced customer base.", "Ch5 §8", "Contribution"),
 Q("With cold storage scarce, rank products by:", ["Contribution per unit", "Contribution per unit of cold storage used", "Margin percentage", "Revenue"], 1,
   "Rank by contribution per unit of whatever is genuinely limited.", "Ch5 §9", "Contribution"),
 Q("Contribution analysis assumes:", ["Full capacity", "Spare capacity", "Fixed prices", "Constant mix"], 1,
   "Where capacity is full, the extra order displaces something and the answer inverts.", "Ch5 §6", "Contribution"),
 Q("Fixed cost ₦4.2m, contribution 30%. Break-even revenue is:", ["₦4.2m", "₦12.6m", "₦14.0m", "₦1.26m"], 2,
   "4.2m ÷ 0.30 = ₦14m.", "Ch6 §3", "Break-even"),
 Q("Margin of safety measures:", ["Profit above budget", "How far sales can fall before break-even", "Contribution percentage", "The fixed cost buffer"], 1,
   "It tells a manager more about exposure than the profit figure does.", "Ch6 §5", "Break-even"),
 Q("Two branches earn identical profit; one has a 40% margin of safety and one 8%. This means:", ["They are equally exposed", "Only the second should worry you", "The first is less efficient", "Nothing useful"], 1,
   "Identical profit, entirely different positions.", "Ch6 §6", "Break-even"),
 Q("Break-even is a staircase rather than a point because:", ["Prices change", "Fixed costs step as activity grows", "Contribution varies", "Volume is uncertain"], 1,
   "Every fixed cost is fixed only within a relevant range.", "Ch6 §7", "Break-even"),
 Q("A ₦900,000 monthly cost increase at 30% contribution needs extra monthly revenue of:", ["₦900,000", "₦270,000", "₦3.0m", "₦1.17m"], 2,
   "900,000 ÷ 0.30 = ₦3m, forever.", "Ch6 §10", "Break-even"),
 Q("A relevant cost must be future, cash, and:", ["Large", "Traceable", "Different between the options", "In the budget"], 2,
   "Failing any of the three makes it noise, however carefully calculated.", "Ch7 §2", "Relevant cost"),
 Q("Allocated head office cost in an outsourcing decision is:", ["Relevant, because the branch is charged it", "Irrelevant, because it does not change", "Relevant at half value", "Relevant only if it exceeds the quote"], 1,
   "Feeling a cost and being able to remove it are different things.", "Ch7 §8", "Relevant cost"),
 Q("The question that identifies a relevant cost is:", ["Is it in the costing report", "If we do this tomorrow, does this payment stop", "Is it direct", "Is it variable"], 1,
   "If yes it belongs in the comparison; if no it does not.", "Ch7 §7", "Relevant cost"),
 Q("Comparing internal absorbed cost to an external quote biases the decision toward:", ["Keeping it in house", "Outsourcing", "Neither", "Delay"], 1,
   "Your overhead remains after outsourcing while the quote already contains theirs.", "Ch7 §6", "Relevant cost"),
 Q("Owned vehicles' depreciation becomes relevant to an outsourcing decision only if:", ["It is fully charged", "The vehicles can be sold, in which case the proceeds matter", "It exceeds the quote", "It is directly traceable"], 1,
   "Depreciation itself is not cash and the money is already spent.", "Ch7 §5", "Relevant cost"),
 Q("₦8m spent, ₦3m to complete, ₦2.5m expected revenue. The correct decision is:", ["Complete it", "Stop", "Complete and reassess", "Seek more funding"], 1,
   "The ₦8m is gone either way; spending ₦3m to earn ₦2.5m is not sensible.", "Ch8 §3", "Sunk and opportunity cost"),
 Q("Sunk cost is hard to ignore mainly because:", ["It is usually large", "Abandoning feels like admitting the money was wasted", "It appears in the accounts", "Auditors require it"], 1,
   "So the money is protected by spending more of it.", "Ch8 §5", "Sunk and opportunity cost"),
 Q("Opportunity cost appears in:", ["The P&L", "The balance sheet", "No accounting system at all", "The cash flow statement"], 2,
   "And it is frequently the largest cost in the decision.", "Ch8 §7", "Sunk and opportunity cost"),
 Q("Dead stock is held because of sunk cost while incurring:", ["Depreciation", "Opportunity cost on the space it occupies", "Interest", "Absorption variance"], 1,
   "Both forces point the same way and neither appears on the P&L.", "Ch8 §9", "Sunk and opportunity cost"),
 Q("A branch with an absorbed loss of ₦900k contributing ₦1.4m to group overhead should be:", ["Closed, saving ₦900k", "Kept — closing costs the group ₦1.4m a month", "Closed and reopened smaller", "Sold"], 1,
   "The overhead does not close with the branch.", "Ch9 §4", "Costing decisions"),
 Q("For a make-or-buy decision you compare the quote against:", ["Total internal absorbed cost", "Only the payments that genuinely stop, plus opportunity cost", "Direct costs only", "Variable costs only"], 1,
   "And exclude sunk investment and unavoidable overhead.", "Ch9 §6", "Costing decisions"),
 Q("The habit that determines which cost to use is:", ["Consulting the costing report", "Stating what would be different if the answer were yes", "Using absorbed cost consistently", "Asking the auditor"], 1,
   "It takes fifteen seconds and decides whether costing informs or decorates.", "Ch9 §9", "Costing decisions"),
 Q("The commonest costing error in business is:", ["Arithmetic mistakes", "A correct calculation answering the wrong question", "Out-of-date rates", "Ignoring VAT"], 1,
   "Presented confidently, and acted on.", "Ch9 §11", "Costing decisions"),
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
    rebalance(QUESTIONS, "finance:cost:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:cost:checks")

    mod = {
        "title": "Understanding Cost",
        "desc": ("The same naira is several different numbers depending on the question. "
                 "Cost behaviour as a prediction tool, absorption and why the rule is a "
                 "choice, contribution, break-even and margin of safety, relevant cost, "
                 "sunk and opportunity cost, and the five decisions an operating manager "
                 "actually faces."),
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
