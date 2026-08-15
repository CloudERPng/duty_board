#!/usr/bin/env python3
"""Build 'Reading Your Branch's Numbers' into academy_retail_data.json.

Module 2 of Retail Leadership Essentials.

STANDS ALONE. An earlier draft assumed the finance track as a prerequisite and
referred to it four times, which was wrong: a branch manager buying a leadership
course has almost certainly not bought Accounting & Finance for Non-Finance
Managers, and a course that depends on another course the reader does not own is
a course with a hole in it.

Every finance concept this module uses is now explained where it is used —
briefly, at branch level, in the terms a manager meets on their own reports.
Margin and markup, contribution, allocated cost. The finance track goes further
on all of them and is a good next step; it is not a precondition.

The organising claim is that most branch managers are given a report they have
never been taught to distrust — and the most damaging figure on it is usually
the one they are measured on.

Run from the app package directory:  python3 build_retail_m2.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_numbers"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The reports you get, and the ones you need", 11, """<p>Most branch managers receive a sales report daily, a P&L monthly, and a stock report when somebody asks for one. That is what the business happens to produce, and it is not the same thing as what the job requires.</p>

<p><b>What you are usually given.</b> Sales against target, by day and month. Sometimes footfall or transaction count. A monthly branch P&L with costs allocated down from the centre. A stock valuation figure.</p>

<p><b>What that set is missing, and each gap matters.</b></p>

<p><b>Margin, not just sales.</b> A branch can grow sales and lose money, and the sales report will never say so. The Ikeja manager from module 1 is the standard case.</p>

<p><b>Availability.</b> Sales tell you what you sold. Nothing on a standard report tells you what a customer came for and did not find, which is the largest recoverable loss in most branches.</p>

<p><b>Shrinkage, at branch and category level.</b> Frequently buried inside cost of sales as a residual and never isolated, so nobody can say what it actually is.</p>

<p><b>Which costs are yours.</b> A branch P&L usually mixes costs you control with costs allocated from the centre, and presents them as one number you are held to.</p>

<p><b>The two questions to ask about any report before you read it.</b> Who produced it, and from what? A figure assembled from the system is different evidence from one somebody typed into a spreadsheet, and a manager who does not know which they are holding will defend a number they cannot support.</p>

<p><b>Asking for what you need.</b> Most managers assume the reporting is fixed. Usually it is not — the data exists and nobody asked for it in that shape. A specific request, made once, with a reason attached, succeeds far more often than managers expect: not "can I have better reports" but "can I have margin by category monthly, because I cannot tell whether promotions are helping or hurting."</p>

<p><b>And the honest position if the answer is no.</b> Build the two or three numbers yourself, roughly, from what you can see. A rough margin figure you produced beats an accurate one you do not have — and a manager who has been tracking something by hand for three months has a much stronger case for it being reported properly.</p>

<blockquote>IMPLEMENTATION TIP: List the numbers you receive and the ones you would need to answer the three questions from module 1. The gap is usually two or three figures, and asking for them specifically, once, with a reason, is a ten-minute job most managers never do.</blockquote>

<p><b>One more thing to establish about any report: when it arrives.</b> A monthly pack landing on the twenty-fifth describes a period that ended nearly two months earlier, by which time every decision it might have informed has been taken. If yours is late, ask for it a week earlier and accept it will be slightly less accurate. Almost every business can do this, almost none has been asked, and the week of relevance is worth more than the accuracy given up.</p>"""
, [
 C("Sales grew nine per cent at your branch and you are told it was a good month. Before agreeing you need:",
   ["Footfall", "Margin, because a branch can grow sales and lose money",
    "The stock figure", "The target"], 1,
   "The sales report will never tell you that, which is the Ikeja case from module 1."),
 C("The largest recoverable loss in most branches appears on:",
   ["The P&L", "No standard report at all — what a customer came for and did not find",
    "The stock valuation", "The shrinkage line"], 1,
   "Sales tell you what you sold, not what you failed to sell."),
 C("Asking for a report you do not get succeeds far more often when phrased as:",
   ["A request for better reporting", "A specific figure with the reason you need it",
    "An escalation", "A group-wide proposal"], 1,
   "The data usually exists and nobody asked for it in that shape.")]),

("Sales: the number everybody watches", 11, """<p>Sales is the figure your branch is judged on, discussed in every meeting, and the one that tells you least about whether the month was any good.</p>

<p><b>Break it into its parts, because only the parts are actionable.</b> Sales equals transactions multiplied by average basket. Transactions come from footfall multiplied by conversion. So four numbers sit under the one, and a change in sales is always a change in at least one of them.</p>

<p><b>Why this matters more than it sounds.</b> "Sales are down eight per cent" gives you nothing to do. "Footfall is down twelve, conversion is up two points and basket is flat" tells you the market shrank and your team held its share — which is a completely different conversation and a completely different action.</p>

<p><b>What each part tells you.</b></p>

<p><b>Footfall</b> is mostly not yours. Weather, the market, a competitor opening, roadworks, the estate that feeds you. Worth knowing precisely so you can say what happened without sounding defensive.</p>

<p><b>Conversion</b> is yours. Service, availability, queue speed, layout. A conversion drop with footfall steady is a branch problem, and it is the single most useful signal on this list.</p>

<p><b>Basket</b> is partly yours. Range and pricing are not, but prompting, adjacency, availability of the second item and staff knowledge are.</p>

<p><b>If you do not measure footfall</b>, and many branches do not, transactions are the usable substitute. Transaction count against last year, at the same point in the week, tells you most of what footfall would.</p>

<p><b>The comparison that misleads and the one that does not.</b> Comparing to last month compares different weather, different promotions and a different number of paydays. Compare like periods — this week against the same week last year, this Saturday against Saturdays. Month-on-month movement in a seasonal business tells you about the calendar rather than about your branch.</p>

<p><b>And treat the target as what it is.</b> A target is somebody's expectation set before the year began. Missing it can mean the branch underperformed, or that the expectation was wrong. Both happen, and a manager who can distinguish them with the four numbers is worth listening to; one who only knows they missed is not.</p>

<p><b>A note on daily sales figures.</b> They are the most-watched and least informative numbers in retail. A single day contains weather, one large basket, a delivery that did not arrive, and a public holiday nobody remembered — none of which says anything about the branch. Read them for exceptions rather than for trend, and hold judgement until the week is complete. Managers who react daily teach their teams that the number moves for reasons nobody can influence, which is precisely the wrong lesson.</p>

<blockquote>IMPLEMENTATION TIP: Every week, write down four numbers rather than one: transactions, basket, and the two compared with the same week last year. It takes five minutes and it converts every sales conversation you will have that month from an argument into a diagnosis.</blockquote>"""
, [
 C("Sales are down eight per cent. Footfall is down twelve, conversion up two points, basket flat. This means:",
   ["The branch underperformed", "The market shrank and your team held its share",
    "Pricing is wrong", "Service has slipped"], 1,
   "The same fall, read four ways instead of one, produces a different conversation entirely."),
 C("Which part of the sales equation is most usefully treated as a branch problem?",
   ["Footfall", "Conversion", "Price", "Range"], 1,
   "A conversion drop with footfall steady is the single most useful signal available."),
 C("Comparing this month to last month in a seasonal business tells you about:",
   ["Branch performance", "The calendar",
    "Conversion", "Staff productivity"], 1,
   "Compare like periods — this week against the same week last year, Saturdays against Saturdays.")]),

("Margin, and why yours moved", 11, """<p><b>Gross margin is what is left of each naira of sales after the goods themselves are paid for.</b> Sell ₦100 of goods that cost you ₦70 and your gross margin is ₦30, or 30%. It is not the same as markup, which is the uplift on cost — the same transaction is a 30% margin and a 43% markup, and confusing the two is how a branch prices for 40% and achieves 29%.</p><p>Four things move it, and this chapter is about which of the four you can see at branch level, which you caused, and what to do in the week you notice.</p>

<p><b>The four movers, in the order a branch manager can act on them.</b></p>

<p><b>Mix</b> — what sold, not what it sold for. The commonest cause and the one most often missed, because every individual product margin looks correct. A month heavy in low-margin categories drops blended margin with nothing wrong anywhere.</p>

<p><b>Discount and markdown</b> — what you gave away, deliberately or otherwise. Yours, visible, and reportable by reason if the counter is configured as the ZhiftPOS track describes.</p>

<p><b>Loss</b> — shrinkage arriving as a lower margin with no label attached, which the next chapter covers.</p>

<p><b>Buying price</b> — rarely yours, and worth checking rather than assuming, because a supplier increase can pass through without anybody telling the branches.</p>

<p><b>The order to check them in.</b> Mix first, because it is the most likely and the easiest to see. Then markdown, which is reportable. Then loss. Buying price last, because you can rarely do anything about it and it is the one most managers reach for first.</p>

<p><b>What a two-point move is worth.</b> On a branch turning over ₦18,000,000 a month, two points of margin is ₦360,000 monthly — roughly ₦4.3m a year. That is usually larger than every cost saving a branch manager is asked to find, and it moves without anybody deciding anything.</p>

<p><b>Which is why margin deserves the attention sales gets.</b> A manager who reads only sales can lose ₦4.3m a year without a single bad day appearing in any report they read. That is not a hypothetical: it is precisely the Ikeja situation from module 1, and it lasted three quarters.</p>

<p><b>What to do in the week you notice.</b> Do not announce a margin problem. Decompose it first — pull the category split and compare with the prior period, look at markdown by reason, check whether any large line's cost moved. You will usually find one or two categories carrying the whole movement, and a specific finding gets acted on where a general concern gets nodded at.</p>

<p><b>Where a branch manager most often causes a margin fall without noticing.</b> Not through discounting, which is visible, but through what gets promoted, displayed and pushed. Front-of-store space given to a low-margin category, staff prompting the cheaper alternative because it is easier to sell, a display built where a supplier funded it — each shifts mix without any decision that looks like a pricing decision. Which makes mix worth more attention than it usually gets: it is the only margin lever that improves without asking a single customer to pay more.</p>

<blockquote>WATCH-OUT: A margin fall with sales up is the pattern to fear most, because everything on the surface looks like success and the branch will be congratulated while it earns less. Check margin whenever sales rise sharply, not only when they fall.</blockquote>"""
, [
 C("Margin fell and sales rose. This pattern is dangerous because:",
   ["It is rare", "Everything on the surface looks like success while the branch earns less",
    "It cannot be diagnosed", "It is head office's concern"], 1,
   "Check margin whenever sales rise sharply, not only when they fall."),
 C("The first of the four movers to check is:",
   ["Buying price", "Mix", "Loss", "Markdown"], 1,
   "It is the most likely cause and the easiest to see, and every individual product margin still looks correct."),
 C("Two points of margin on a branch turning over ₦18m a month is worth about:",
   ["₦36,000 a month", "₦360,000 a month",
    "₦3.6m a month", "₦18,000 a month"], 1,
   "Roughly ₦4.3m a year, usually larger than every cost saving a branch manager is asked to find.")]),

("Availability, as a number", 11, """<p>The largest recoverable loss in most branches is invisible on every report, because a sale that did not happen leaves no record. Turning availability into a number is the single highest-value measurement a branch manager can introduce.</p>

<p><b>Why it matters more than it appears.</b> A customer who cannot find one item frequently leaves without the other four they came for, and some of them do not come back for a month. The loss is not the one line — it is the basket and a portion of the relationship.</p>

<p><b>Rank by contribution rather than by sales, and the distinction matters.</b> Contribution is what a line leaves you after the cost of the goods themselves — its selling price less what you paid for it. A line selling ₦900,000 a month at 8% leaves you ₦72,000; one selling ₦300,000 at 35% leaves ₦105,000. The second is smaller on every sales report and worth more to your branch, and an availability check built on sales value will watch the wrong forty lines.</p><p><b>How to measure it without a system that does it for you.</b> Take your top forty lines by contribution, walk them at the same time twice a week, and count how many are unavailable. That is your availability rate on the lines that matter, it takes fifteen minutes, and almost no branch has the figure.</p>

<p><b>Where the system helps.</b> Where stock is tracked, a report of lines at zero on hand tells you what is out now. What it will not tell you is how long it was out or how often, which is why the manual count twice a week is worth keeping — a line out for six hours on a Tuesday is not the same problem as one out every weekend.</p>

<p><b>Converting it to money, which is what makes anybody act.</b> A line selling four a day at ₦1,200 with 30% margin, out for nine days in the month, cost roughly ₦13,000 of margin at that branch. Multiply across the lines that are habitually out and the number is usually startling — and it is the number that gets a replenishment problem taken seriously where a complaint about gaps does not.</p>

<p><b>The four causes, and they need different fixes.</b> Not ordered — an ordering discipline problem. Ordered and not delivered — a supplier or central problem, which is reportable rather than yours. Delivered and not on the shelf — a replenishment problem, and the most common of the four. Or on the shelf and unfindable, which is a layout problem and is invisible to every count you will do.</p>

<p><b>That third cause deserves emphasis</b> because it is both the most frequent and the most fixable. Stock sitting in the back while the shelf is empty is a branch losing sales on goods it already paid for, and no system report will identify it — only somebody walking the floor with the stock figure in their hand.</p>

<blockquote>IMPLEMENTATION TIP: Count your top forty lines twice a week for a month and price the gaps. That single exercise produces the most persuasive number a branch manager can put in front of head office, because it is a loss the business is already suffering and had never quantified.</blockquote>

<p><b>What to do with the count once you have it.</b> Do not send it upward immediately. Fix the third cause first — stock in the back that is not on the shelf — because it is yours, it is usually the largest, and it takes a replenishment routine rather than a request to anybody. Then report what remains, which will be the ordering and supply causes, with the money attached. A manager who has already fixed their own half is heard very differently from one reporting the whole problem outward.</p>"""
, [
 C("A customer cannot find one item on their list. The realistic loss is:",
   ["That one line", "The basket, and a portion of the relationship",
    "Nothing if they buy the rest", "One transaction"], 1,
   "Some of them do not come back for a month."),
 C("Which cause of unavailability is most frequent and most fixable?",
   ["Not ordered", "Delivered but not on the shelf",
    "Ordered but not delivered", "On the shelf but unfindable"], 1,
   "Stock in the back while the shelf is empty is a branch losing sales on goods it already paid for."),
 C("Availability should be measured on your top lines by:",
   ["Sales value", "Contribution", "Order frequency", "Shelf space"], 1,
   "Following the finance track's argument — the biggest sellers are not always where the money is.")]),

("Shrinkage, read honestly", 11, """<p>The internal control track teaches an auditor to test for loss. This chapter is the manager's side of the same problem: what your shrinkage number means, what it is made of, and what you can actually do about it before anybody audits anything.</p>

<p><b>What it is made of, and the order surprises people.</b> Administrative error is usually the largest component — miscounts, mis-scans, wrong units, cut-off mistakes. Then supplier shortfall: invoiced and not delivered, or delivered short and signed for. Then internal theft. Then customer theft, which most managers assume dominates and rarely does. Then damage and expiry.</p>

<p><b>Why the order matters to you specifically.</b> A manager who treats all shrinkage as theft spends their attention on the smallest component and on the part of it involving their own staff, which is corrosive and usually wrong. The first two components are process problems, they are yours, and they are fixable without accusing anybody.</p>

<p><b>Getting a number at all.</b> Many businesses never isolate shrinkage — it emerges as a residual inside cost of sales, blended with mix and pricing, and nobody can say what it was. If that is your situation, producing a defensible shrinkage figure by category is itself a substantial piece of work and probably the most valuable thing you will do this year.</p>

<p><b>Read it as a percentage and by category.</b> Naira ranks by branch size and tells you nothing. As a percentage of sales, compared within category, you can see whether your loss is concentrated or spread. Concentrated points at a specific process, location or person; spread points at counting, receiving or systemic error.</p>

<p><b>The receiving bay is where a manager has most leverage.</b> It is the point where the business's money becomes its goods, it is usually staffed by the most junior person available, under time pressure with a driver waiting — and a receipt that always exactly matches the order is not a good sign. Real deliveries are occasionally short. A receiver whose figures never differ is copying rather than counting.</p>

<p><b>And the count nobody trusts.</b> If your counts are done by whoever is responsible for the stock, you do not have a count — you have a confirmation. Rotating who counts what, at no cost, changes the quality of the number more than any amount of exhortation about accuracy.</p>

<p><b>And what a manager can do that an auditor cannot.</b> An auditor tests and reports; you are there every day. The things that actually reduce shrinkage are unglamorous and local — a receiving bay where somebody counts, a back door that is not propped open, a rota that does not leave one person alone with the stockroom, waste recorded when it happens rather than reconstructed at month end. None of that appears in an audit finding, and all of it moves the number.</p>

<blockquote>WATCH-OUT: Be suspicious of your own good news. A branch whose count differences are always small and always favourable is more often a branch where the count is being adjusted to agree with the system than one where nothing is going missing.</blockquote>"""
, [
 C("Your shrinkage figure is unchanged and small every month. This is:",
   ["Reassuring", "More often a count adjusted to agree with the system than a branch losing nothing",
    "Evidence of good control", "Expected in a well-run store"], 1,
   "Genuine counting produces differences in both directions and of varying size."),
 C("A manager treating all shrinkage as theft will:",
   ["Deter losses effectively", "Spend attention on the smallest component, and on their own staff",
    "Find the cause faster", "Reduce it fastest"], 1,
   "Administrative error and supplier shortfall are larger, are process problems, and are fixable without accusing anybody."),
 C("A receiver whose quantities always exactly match the order is:",
   ["Highly accurate", "Copying rather than counting",
    "Working with a reliable supplier", "Following procedure"], 1,
   "Real deliveries are occasionally short, damaged or over.")]),

("Costs: yours, and the other kind", 11, """<p>A branch P&L usually mixes costs you decide with costs allocated to you from the centre, presents them as one figure, and holds you to the total. Separating the two is the difference between a cost conversation that goes somewhere and one that goes in circles.</p>

<p><b>Costs that are genuinely yours.</b> The rota and overtime, which is usually the largest controllable cost in a branch. Utilities, to the extent behaviour affects them. Consumables. Waste and damage. Local repairs and small discretionary spend. Cash losses.</p>

<p><b>Costs allocated to you.</b> A share of head office, group insurance, systems, marketing, sometimes distribution. These arrive by a rule somebody chose, often years ago, and they change when the rule changes rather than when anything happens at your branch.</p>

<p><b>The point branch managers most need to be able to make.</b> An allocated cost does not disappear if the activity does. A branch showing a loss after allocation may be contributing substantially toward group overhead, and closing it would make the group worse off — the overhead simply redistributes onto the branches that remain.</p>

<p><b>So the number to know about your own branch is its contribution</b>: sales, less cost of sales, less the costs that would genuinely stop if the branch stopped. That is the figure that says whether your branch earns its keep, and it is frequently a great deal healthier than the bottom line you are shown.</p>

<p><b>Where the rota deserves its own attention.</b> It is the one large cost a manager adjusts weekly, and most rotas are built from availability and habit rather than from trade. Compare your staffing profile to your hourly sales profile for one week: most branches find they are overstaffed in the morning and short at the times that actually convert. Fixing that costs nothing and improves both the cost line and the conversion line at once.</p>

<p><b>And a caution about cutting.</b> Cost reduction at branch level is real and it is small. Two points of margin, or a fixed availability problem, is usually worth more than every controllable cost saving available — which is why the previous chapters come first in this module rather than last.</p>

<p><b>The cost conversation worth having upward.</b> When head office asks for a percentage off branch costs, the useful reply is not a refusal or a promise. It is what that percentage represents at your branch, what it would come out of, and what it would cost elsewhere — hours removed from the trading hours that convert, for instance. Costs are real and so are the consequences of cutting the wrong ones, and a manager who can show both is taken more seriously than one who simply complies or simply objects.</p>

<blockquote>IMPLEMENTATION TIP: Ask for your branch's P&L split into controllable and allocated. Many businesses have never presented it that way and can produce it easily. It changes what you are accountable for from a number you cannot influence to one you can.</blockquote>"""
, [
 C("Your branch shows a loss after head office allocation. Before accepting that it is failing you should establish:",
   ["The allocation basis", "Its contribution — sales less cost of sales less costs that would genuinely stop",
    "The rent", "Group profitability"], 1,
   "An allocated cost does not disappear if the branch does; it redistributes onto the ones that remain."),
 C("You are asked to find savings at your branch. The line worth looking at first is:",
   ["Utilities", "The rota and overtime", "Waste", "Consumables"], 1,
   "It is also the one a manager adjusts weekly, usually from availability and habit rather than from trade."),
 C("Comparing your staffing profile to your hourly sales profile usually reveals:",
   ["Correct coverage", "Overstaffing in the morning and shortage when trade converts",
    "Excess overtime", "A training gap"], 1,
   "Fixing it costs nothing and improves the cost line and the conversion line at once.")]),

("The numbers that lie", 11, """<p>Every branch report contains figures that look precise and are not. Knowing which is not cynicism — it is what stops you defending a number you cannot support, or acting on one that was never real.</p>

<p><b>Stock valuation.</b> True only as at the last count, and drifting from that moment. If your last count was in March, the September figure is an estimate with a March anchor. Ask when the count was before treating it as fact.</p>

<p><b>Anything with an allocation in it.</b> Branch profit after head office costs is arithmetic performed on a rule. Change the rule and your branch's profitability changes without a single thing happening in the store.</p>

<p><b>Like-for-like comparisons across a change.</b> A refit, a range change, a new competitor, a road closure — the comparison is between two different situations. Say so at the time rather than being asked later.</p>

<p><b>Averages that hide their shape.</b> An average basket of ₦4,200 might be a tight cluster or two entirely different customer groups. Averages across branches are worse — the estate average describes no branch that exists.</p>

<p><b>Percentages on small numbers.</b> Complaints up 200% means two became six. In a branch of your size most weekly percentages are noise, and reacting to them is how a team gets whiplashed by numbers that meant nothing.</p>

<p><b>Anything typed rather than derived.</b> The finance and control tracks both make this point and it applies to your own reports: a figure somebody entered into a spreadsheet has been through a human, and humans round, transpose and remember. Ask where a surprising number came from before you act on it.</p>

<p><b>And the one closest to home: figures you produced yourself.</b> A count you rushed, an availability check done from memory, a footfall estimate. You will trust these more than they deserve precisely because you produced them. Note how each was arrived at, and be as sceptical of your own numbers as of anybody else's.</p>

<p><b>What to do with all of this.</b> Not distrust everything — use each figure for what it can carry. Stock valuation for direction rather than precision. Contribution rather than allocated profit for whether the branch works. Like-for-like only across comparable periods. And any surprising number checked once before it becomes a decision.</p>

<blockquote>WATCH-OUT: The most dangerous figure on any report is the one you are measured on, because you have the strongest reason to accept it when it is good and to argue with it when it is not. Apply the same scepticism in both directions or you are not being sceptical at all.</blockquote>

<p><b>How to disagree with a number properly.</b> Not by disputing it in a meeting from memory. Establish what it was built from, find the specific step you think is wrong, and put that in writing with the alternative figure and how you arrived at it. A manager who says a number feels wrong is dismissed; one who says the valuation is anchored on a March count and here is what a current count shows is not. The difference is entirely in the preparation.</p>"""
, [
 C("Your stock valuation shows September and the last count was in March. The figure is:",
   ["Accurate as reported", "An estimate anchored on March and drifting since",
    "Only wrong if shrinkage is high", "Verified by the system"], 1,
   "Ask when the count was before treating a valuation as fact."),
 C("Complaints at your branch are up 200% this week. This most likely means:",
   ["A service failure", "Two became six, and it is noise",
    "A trend worth acting on", "A staffing problem"], 1,
   "Reacting to weekly percentages on small numbers is how a team gets whiplashed by figures that meant nothing."),
 C("The most dangerous figure on any report is:",
   ["The oldest", "The one you are measured on",
    "The allocated one", "The estimated one"], 1,
   "You have the strongest reason to accept it when good and argue when bad — scepticism must run both ways.")]),

("Okelewo: what the Ikeja two points cost", 11, """<p>Module 1 left the Ikeja manager with sales up nine per cent and margin down two points, unaware because he read the sales report and not the margin one. This is what it cost and how it was found.</p>

<p><b>The arithmetic.</b> Ikeja turns over about ₦21,000,000 a month. Two points of margin is ₦420,000 monthly. Over the three quarters it ran, roughly ₦3.8m — against a nine per cent sales increase that added, at the branch's actual margin, about ₦1.4m of gross profit over the same period.</p>

<p><b>So the branch worked harder, sold more, and earned ₦2.4m less.</b> Every daily report during those three quarters was green.</p>

<p><b>What caused it, in the order it was found.</b> Decomposition first, not accusation. The category split showed the whole movement sitting in two categories, both of which had been promoted repeatedly. The markdown report — available because the counters record a reason on the line, as the ZhiftPOS track describes — showed the promotional discount running at nearly double its budgeted percentage. And a third of the promotional volume was on lines the branch would have sold anyway.</p>

<p><b>The manager had not done anything forbidden.</b> He ran promotions he was permitted to run, to hit a sales target he was measured on, and the system recorded every one of them correctly. Nobody was reading the record.</p>

<p><b>How it surfaced.</b> Not from a report. The finance lead was preparing a group margin analysis, noticed one branch moving against the estate, and asked. That is luck rather than control — and the uncomfortable question afterwards was how long it would have run had she been looking at something else that week.</p>

<p><b>What changed.</b> The monthly branch call added margin, shrinkage, availability and staff turnover to what had been a sales conversation. Within two quarters Ikeja's manager was reading his margin report, because it had become something he was asked about — the attention lever from module 1, applied downward.</p>

<p><b>And the point for you.</b> He was not a poor manager. He was a manager reading the report he was given, measured on the number he was shown, doing exactly what that arrangement rewarded. The defence is knowing which numbers you are not being shown, which is the whole of this module.</p>

<blockquote>IMPLEMENTATION TIP: If your monthly conversation with your manager covers only sales, you are in the Ikeja position whether or not anything is currently wrong. Bring margin to it yourself, before anybody asks, and the conversation changes permanently.</blockquote>

<p><b>The wider lesson from Ikeja, which applies well beyond promotions.</b> A person measured on one number will optimise that number, and will do it honestly and energetically. That is not a character flaw and it cannot be trained away — it is what measurement does. So the useful question about any target you are given is what it would cost the business if you hit it by the easiest available route, and whether anybody is watching that cost. If the answer is nobody, say so before you start rather than after three quarters.</p>"""
, [
 C("Ikeja's nine per cent sales rise added ₦1.4m of gross profit while two margin points cost ₦3.8m. The branch:",
   ["Broke even", "Worked harder, sold more, and earned ₦2.4m less",
    "Gained on volume", "Lost only on promotions"], 1,
   "Every daily report during those three quarters was green."),
 C("The margin problem was found because:",
   ["A report flagged it", "The finance lead happened to notice one branch moving against the estate",
    "The manager investigated", "An audit tested it"], 1,
   "That is luck rather than control, and the uncomfortable question is how long it would otherwise have run."),
 C("If your monthly conversation with your manager covers only sales, you are:",
   ["Appropriately focused", "In the Ikeja position, whether or not anything is currently wrong",
    "Following the process", "Protected by the reporting"], 1,
   "Bring margin to it yourself, before anybody asks.")]),

("The manager's weekly numbers", 11, """<p>This is the chapter to keep. Six figures, weekly, in about fifteen minutes — and the discipline is that they are the same six every week, because a number is only useful once you know what normal looks like.</p>

<p><b>1. Transactions and basket, against the same week last year.</b> Two numbers, and between them they explain almost any sales movement. Not against last week — against the comparable week.</p>

<p><b>2. Margin percentage, against the prior month.</b> The number your sales report will not tell you and the one that quietly costs the most. If you can only add one figure to what you currently see, add this.</p>

<p><b>3. Availability on your top forty by contribution.</b> Counted, not estimated. Fifteen minutes twice a week, and it is the largest recoverable loss you have.</p>

<p><b>4. Markdown value and its top reason.</b> Not just how much was given away but why, which the counter records if it is configured as it should be.</p>

<p><b>5. Hours against trade.</b> Whether the rota matched the shape of the week, which is both the largest controllable cost and a conversion lever.</p>

<p><b>6. One thing from the floor.</b> Not a number. Something you saw — a queue that did not move, a category customers kept asking about, a member of staff who has gone quiet. The figures tell you what happened; this tells you what is about to.</p>

<p><b>Why the same six.</b> A number in isolation means nothing. Twelve weeks of the same six means you know your branch's normal, and you notice a departure in the week it starts rather than in the quarter it shows up. That is the entire value, and it comes from consistency rather than sophistication.</p>

<p><b>Write them down and keep them.</b> Most managers look and move on. A retained series turns a snapshot into a trend, and a trend is the difference between noticing that something is unusual and noticing that something has changed — only the second is worth acting on.</p>

<p><b>And what to do with the six.</b> One of them will be moving in a direction you do not like. That one becomes the cause you spend module 1's protected hour on. Not all six, and not whichever is loudest — the one that is both moving and worth money.</p>

<blockquote>IMPLEMENTATION TIP: Put the six on one sheet, same day each week, and keep twelve weeks of them where you can see the series at once. Fifteen minutes weekly is three hours a quarter, and it is the difference between managing your branch and being informed about it afterwards.</blockquote>

<p><b>What to do when the six all look fine.</b> Most weeks they will, and that is the point — a routine whose value only appears when something is wrong still has to be run on the weeks nothing is. Record the quiet week and move on. The value is not in what any single week tells you; it is that the twelfth week tells you something the first eleven made visible, and there is no way to get the twelfth without the eleven.</p>"""
, [
 C("If you could add only one figure to a standard sales report, it should be:",
   ["Footfall", "Margin percentage", "Stock valuation", "Complaints"], 1,
   "It is the number the sales report will not tell you and the one that quietly costs the most."),
 C("The sixth weekly item is one thing from the floor rather than a number because:",
   ["Numbers are unreliable", "The figures tell you what happened; the floor tells you what is about to",
    "It is easier to collect", "It engages the team"], 1,
   "A queue that did not move, a category customers kept asking about, a member of staff gone quiet."),
 C("The value of tracking the same six figures weekly comes from:",
   ["Their sophistication", "Consistency — twelve weeks tells you what normal looks like",
    "Their accuracy", "Head office expectation"], 1,
   "You notice a departure in the week it starts rather than the quarter it shows up.")]),
]


QUESTIONS = [
 Q("A standard branch reporting pack is missing margin, availability, isolated shrinkage and:", ["Footfall", "Which costs are controllable", "Transaction count", "The target"], 1,
   "It usually mixes costs you decide with costs allocated from the centre.", "Ch1 §4", "The reports"),
 Q("Before reading any report you should ask who produced it and:", ["When", "From what", "For whom", "How often"], 1,
   "A figure from the system is different evidence from one typed into a spreadsheet.", "Ch1 §6", "The reports"),
 Q("A request for a figure you do not currently receive works best when it:", ["Goes through your manager", "Names the figure and the reason you need it", "Is raised at a meeting", "Covers all branches"], 1,
   "The data usually exists and nobody asked for it in that shape.", "Ch1 §7", "The reports"),
 Q("If the answer to a reporting request is no, the useful response is to:", ["Escalate", "Build the two or three numbers roughly yourself", "Drop it", "Wait for a review"], 1,
   "Three months of hand-tracking is a much stronger case for it being reported properly.", "Ch1 §8", "The reports"),
 Q("Sales equals transactions multiplied by:", ["Footfall", "Average basket", "Conversion", "Margin"], 1,
   "And transactions are footfall multiplied by conversion — four numbers under the one.", "Ch2 §2", "Sales"),
 Q("Which part of the sales equation is least within a branch manager's control?", ["Conversion", "Footfall", "Basket", "Transactions"], 1,
   "Worth knowing precisely so you can say what happened without sounding defensive.", "Ch2 §5", "Sales"),
 Q("A conversion drop with footfall steady is:", ["A market signal", "A branch problem", "A pricing issue", "Seasonal"], 1,
   "The single most useful signal on the list.", "Ch2 §6", "Sales"),
 Q("Where footfall is not measured, the usable substitute is:", ["Basket", "Transaction count", "Margin", "Stock movement"], 1,
   "Against last year at the same point in the week.", "Ch2 §8", "Sales"),
 Q("A missed target can mean the branch underperformed or:", ["The market moved", "The expectation was wrong", "Costs rose", "Stock was short"], 1,
   "A manager who can distinguish the two with four numbers is worth listening to.", "Ch2 §10", "Sales"),
 Q("The four movers of margin, in the order a branch manager should check them:", ["Buying price, mix, markdown, loss", "Mix, markdown, loss, buying price", "Loss, mix, markdown, buying price", "Markdown, buying price, mix, loss"], 1,
   "Buying price last, because you can rarely act on it and it is what most managers reach for first.", "Ch3 §7", "Margin"),
 Q("Mix is missed most often because:", ["It is not reported", "Every individual product margin still looks correct", "It changes slowly", "It is head office's decision"], 1,
   "A month heavy in low-margin categories drops blended margin with nothing wrong anywhere.", "Ch3 §3", "Margin"),
 Q("Two points of margin on ₦18m monthly turnover is worth annually about:", ["₦360,000", "₦4.3m", "₦720,000", "₦43m"], 1,
   "Usually larger than every cost saving a branch manager is asked to find.", "Ch3 §8", "Margin"),
 Q("On noticing a margin fall you should first:", ["Report it", "Decompose it by category, markdown reason and cost", "Reduce discounts", "Review pricing"], 1,
   "A specific finding gets acted on where a general concern gets nodded at.", "Ch3 §10", "Margin"),
 Q("Availability should be measured on your top lines ranked by:", ["Sales value", "Contribution", "Units sold", "Shelf space"], 1,
   "The biggest sellers are not always where the money is.", "Ch4 §4", "Availability"),
 Q("A system report of lines at zero will not tell you:", ["What is out now", "How long it was out or how often", "Which category", "The value"], 1,
   "Which is why a manual count twice a week is worth keeping.", "Ch4 §5", "Availability"),
 Q("A line selling four a day at ₦1,200 with 30% margin, out for nine days, costs roughly:", ["₦4,300", "₦13,000", "₦43,000", "₦1,300"], 1,
   "Converting availability to money is what gets a replenishment problem taken seriously.", "Ch4 §6", "Availability"),
 Q("Which cause of unavailability is invisible to every count you will do?", ["Not ordered", "On the shelf but unfindable", "Delivered not shelved", "Ordered not delivered"], 1,
   "It is a layout problem rather than a stock one.", "Ch4 §7", "Availability"),
 Q("The most frequent cause of a gap is:", ["Not ordered", "Delivered but not on the shelf", "Supplier failure", "Theft"], 1,
   "A branch losing sales on goods it has already paid for.", "Ch4 §8", "Availability"),
 Q("The largest component of shrinkage is usually:", ["Customer theft", "Administrative error", "Internal theft", "Damage"], 1,
   "Miscounts, mis-scans, wrong units and cut-off mistakes.", "Ch5 §2", "Shrinkage"),
 Q("Treating all shrinkage as theft causes a manager to:", ["Find it faster", "Spend attention on the smallest component", "Deter losses", "Improve counts"], 1,
   "And on the part involving their own staff, which is corrosive and usually wrong.", "Ch5 §3", "Shrinkage"),
 Q("Shrinkage should be compared:", ["In naira across branches", "As a percentage, within category", "Against budget only", "Monthly against last month"], 1,
   "Naira ranks by branch size and tells you nothing.", "Ch5 §5", "Shrinkage"),
 Q("A receiver whose quantities always match the order exactly is:", ["Accurate", "Copying rather than counting", "Well trained", "Working with a good supplier"], 1,
   "Real deliveries are occasionally short, damaged or over.", "Ch5 §6", "Shrinkage"),
 Q("A count performed by whoever is responsible for the stock is:", ["A control", "A confirmation", "Adequate if supervised", "Standard practice"], 1,
   "Rotating who counts what costs nothing and changes the quality of the number.", "Ch5 §7", "Shrinkage"),
 Q("The largest controllable cost in most branches is:", ["Utilities", "The rota and overtime", "Waste", "Repairs"], 1,
   "And the one a manager adjusts weekly.", "Ch6 §2", "Costs"),
 Q("A branch showing a loss after allocation may still be:", ["Failing", "Contributing substantially toward group overhead", "Overstaffed", "Mispriced"], 1,
   "Closing it would redistribute the overhead onto the branches that remain.", "Ch6 §5", "Costs"),
 Q("The figure that says whether your branch earns its keep is:", ["Net profit after allocation", "Contribution", "Gross margin", "Sales against target"], 1,
   "Sales less cost of sales less the costs that would genuinely stop.", "Ch6 §6", "Costs"),
 Q("Comparing staffing profile to hourly sales profile typically shows:", ["Correct coverage", "Overstaffing in the morning and shortage when trade converts", "Excess overtime", "Understaffing throughout"], 1,
   "Fixing it costs nothing and improves cost and conversion together.", "Ch6 §7", "Costs"),
 Q("Cost reduction at branch level is:", ["The largest lever available", "Real and small, usually smaller than margin or availability", "Head office's responsibility", "The first thing to attempt"], 1,
   "Which is why the earlier chapters come first in this module.", "Ch6 §8", "Costs"),
 Q("A stock valuation is true only:", ["At month end", "As at the last count", "When the system syncs", "After reconciliation"], 1,
   "Ask when the count was before treating it as fact.", "Ch7 §2", "Numbers that lie"),
 Q("Branch profit after head office costs is:", ["An objective measure", "Arithmetic performed on a rule somebody chose", "Audited", "Comparable across branches"], 1,
   "Change the rule and your branch's profitability changes with nothing happening in the store.", "Ch7 §3", "Numbers that lie"),
 Q("An estate average describes:", ["Typical performance", "No branch that exists", "The median branch", "The target"], 1,
   "Averages across branches hide their shape entirely.", "Ch7 §5", "Numbers that lie"),
 Q("Complaints up 200% in a branch of your size is usually:", ["A service failure", "Noise", "A trend", "A staffing signal"], 1,
   "Two became six.", "Ch7 §6", "Numbers that lie"),
 Q("Figures you produced yourself deserve:", ["More trust", "The same scepticism as anybody else's", "No documentation", "Automatic acceptance"], 1,
   "You will trust them more than they deserve precisely because you produced them.", "Ch7 §8", "Numbers that lie"),
 Q("Ikeja turned over ₦21m monthly. Two points of margin cost:", ["₦42,000 a month", "₦420,000 a month", "₦4.2m a month", "₦210,000 a month"], 1,
   "Roughly ₦3.8m across the three quarters it ran.", "Ch8 §2", "Okelewo Ikeja"),
 Q("The nine per cent sales rise added ₦1.4m of gross profit, so the branch was:", ["Ahead overall", "About ₦2.4m worse off", "Break-even", "Ahead on volume"], 1,
   "Every daily report during those three quarters was green.", "Ch8 §3", "Okelewo Ikeja"),
 Q("The Ikeja problem was found by:", ["The margin report", "The finance lead noticing one branch moving against the estate", "An audit", "The manager"], 1,
   "Luck rather than control.", "Ch8 §6", "Okelewo Ikeja"),
 Q("The Ikeja manager had:", ["Broken the discount policy", "Done exactly what the arrangement rewarded", "Concealed the promotions", "Bypassed approval"], 1,
   "He ran permitted promotions to hit the number he was measured on, and the system recorded every one.", "Ch8 §5", "Okelewo Ikeja"),
 Q("What changed afterwards was that the monthly branch call added margin, shrinkage, availability and:", ["Footfall", "Staff turnover", "Complaints", "Stock days"], 1,
   "The attention lever from module 1, applied downward.", "Ch8 §7", "Okelewo Ikeja"),
 Q("How many figures are in the weekly routine?", ["Four", "Six", "Eight", "Ten"], 1,
   "About fifteen minutes, the same six every week.", "Ch9 §1", "The weekly six"),
 Q("Transactions and basket should be compared against:", ["Last week", "The same week last year", "The monthly average", "Target"], 1,
   "Not against last week — against the comparable week.", "Ch9 §2", "The weekly six"),
 Q("The sixth weekly item is:", ["Stock valuation", "One thing from the floor, not a number", "Complaints", "Cash variance"], 1,
   "The figures tell you what happened; this tells you what is about to.", "Ch9 §7", "The weekly six"),
 Q("The value of the weekly six comes from:", ["Their precision", "Consistency, so you learn what normal looks like", "Their number", "Head office reporting"], 1,
   "Twelve weeks of the same six means you notice a departure in the week it starts.", "Ch9 §8", "The weekly six"),
 Q("Which of the six should become your protected hour's work?", ["The loudest", "The one both moving and worth money", "The newest", "All six in rotation"], 1,
   "Not all six, and not whichever is loudest.", "Ch9 §10", "The weekly six"),
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
    rebalance(QUESTIONS, "retail:the_numbers:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:the_numbers:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 2 — Reading Your Branch's Numbers",
        "desc": ("Which figures on a branch report are true, which are artefacts of how the "
                 "group allocates, and what to look at each week. Sales broken into its four "
                 "parts, margin and why yours moved, availability as a number, shrinkage read "
                 "honestly, controllable against allocated cost, the numbers that lie, and a "
                 "weekly routine of six figures."),
        "lessons": [
            {"title": t, "est": e, "html": h,
             "checks": [dict(c, sort=i) for i, c in enumerate(ch)]}
            for t, e, h, ch in LESSONS
        ],
        "questions": QUESTIONS,
    }

    data = {}
    if os.path.exists(DATA):
        with io.open(DATA, encoding="utf-8") as f:
            data = json.load(f)
    data[KEY] = mod
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("chapters: %d | mean %d | min %d" % (len(lens), sum(lens) / len(lens), min(lens)))
    sp = collections.Counter(q["ans"] for q in QUESTIONS)
    print("questions: %d | spread %s | guessable %d%%"
          % (len(QUESTIONS), dict(sorted(sp.items())),
             round(max(sp.values()) * 100 / len(QUESTIONS))))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
