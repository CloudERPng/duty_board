#!/usr/bin/env python3
"""Build the Margin & Pricing module into academy_finance_data.json.

Track module 5. Module 4 established contribution, relevant cost and the
discount arithmetic; this module spends them on the decisions where most
commercial damage is actually done.

Written for a market with real inflation and currency movement, because the
standard textbook treatment of pricing assumes a stability that does not exist
here — and the resulting advice, followed literally, loses money quietly.

Merges into the data file. Rebalance folded into the build.

Run from the app package directory:  python3 build_finance_m6.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "pricing"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Price is the only lever that goes straight to profit", 10, """<p>A business has four levers: sell more, charge more, buy cheaper, spend less. They are not equal, and the difference is larger than most managers expect.</p>

<p><b>Take a business with ₦100,000,000 of revenue, 30% gross margin, and ₦22,000,000 of overhead. Operating profit is ₦8,000,000.</b> Now improve each lever by one per cent and see what happens.</p>

<p><b>Volume up 1%.</b> Revenue rises ₦1,000,000, and gross profit rises by 30% of that — ₦300,000. Profit goes from ₦8,000,000 to ₦8,300,000, a 3.75% improvement. And it is not free: more volume needs more stock and more receivables, so it consumes cash.</p>

<p><b>Buying cost down 1%.</b> Cost of sales falls from ₦70,000,000 to ₦69,300,000, adding ₦700,000. Profit rises 8.75%.</p>

<p><b>Overhead down 1%.</b> ₦220,000 saved. Profit rises 2.75%.</p>

<p><b>Price up 1%, volume unchanged.</b> Revenue rises ₦1,000,000 and <i>nothing else moves at all</i>. You sell the same units, buy the same goods, pay the same rent. The entire ₦1,000,000 falls to profit, which rises <b>12.5%</b>.</p>

<p>One per cent on price is worth more than three per cent on volume, and it costs nothing to implement.</p>

<p><b>The catch, stated honestly, because the arithmetic above assumes volume holds.</b> It usually does not, entirely. But it does not have to hold entirely for the price rise to win. At 30% margin, a 1% price increase can afford to lose about 3.2% of volume before you are worse off. Ask yourself whether a 1% price rise would really cost you one customer in thirty — and in most businesses, on most products, the honest answer is no.</p>

<p><b>Why the least powerful lever gets the most attention.</b> Cost-cutting feels controllable and internal: you decide, and it happens. Price feels exposed — it involves customers, who might say no, and salespeople, who will certainly say it is too high. So businesses spend months finding ₦220,000 of overhead savings and minutes deciding a price that is worth ₦1,000,000.</p>

<p><b>The corollary is uncomfortable and worth sitting with.</b> If a 1% price change moves profit 12.5%, then price errors are equally powerful in the other direction. A salesperson with discretion who gives away 3% on a routine deal has handed over a third of the profit on it. Discretion granted without arithmetic is not delegation; it is an unmeasured cost centre.</p>

<blockquote>IMPLEMENTATION TIP: Work out your own version of the four levers before reading further. Take last year's revenue, gross margin and overhead, and calculate what 1% on each does to your profit. The ranking is nearly always the same and the magnitudes will still surprise you — and it is your own numbers that change behaviour, not an example.</blockquote>

<p><b>One qualification about margin level.</b> The leverage of price rises as margin falls. A business at 15% margin gains even more from a 1% price increase in percentage-profit terms, because the base is thinner — and can afford to lose even less volume before it is worse off. So thin-margin businesses, which are exactly the ones most nervous about pricing, are the ones where price matters most and where discounting does the most damage. The instinct and the arithmetic point in opposite directions.</p>""",
 [C("Revenue ₦100m, 30% margin, overhead ₦22m. A 1% price rise with volume held raises profit by:",
    ["3.75%", "8.75%", "12.5%", "2.75%"], 2,
    "The full ₦1m falls through because nothing else moves — no extra units, stock or cost."),
  C("Which lever is weakest in that example?",
    ["Price", "Volume", "Buying cost", "Overhead"], 3,
    "1% off overhead is ₦220,000 against ₦1m from price, and it gets the most management attention."),
  C("At 30% margin, a 1% price increase can afford to lose roughly how much volume before you are worse off?",
    ["0.3%", "1%", "3.2%", "10%"], 2,
    "Ask whether a 1% rise would really cost one customer in thirty. Usually it would not.")]),

("Cost-plus pricing, and where it fails", 10, """<p>Most businesses price by adding a percentage to cost. It is quick, defensible, and universally understood — and it contains three faults that cost real money.</p>

<p><b>Fault one: it uses the wrong cost, and module 4 explained why.</b> Cost-plus almost always runs off absorbed cost, which includes a share of overhead allocated by a rule somebody chose. Change the rule and the price changes with it. A bulky slow-moving line absorbed on floor space carries a higher cost and gets a higher price — precisely the product least able to bear one.</p>

<p><b>Fault two: it prices in a circle.</b> Absorbed cost per unit depends on volume. Volume depends on price. So you set a price from a cost that assumed a volume that depends on the price you just set. When sales disappoint, absorbed cost per unit rises, cost-plus recommends a higher price, and the higher price reduces volume further. The method actively recommends the wrong direction in a downturn.</p>

<p><b>Fault three, and the largest: it contains no information about the customer.</b> Cost is a fact about you. Price is a proposition to somebody else. Cost-plus asks what you need and never asks what it is worth to them — so it systematically underprices things customers value highly and overprices things they do not.</p>

<p><b>A worked case.</b> Two products both cost ₦5,000 landed. One is a commodity available from four suppliers within walking distance. The other is a specialist part your customer's line stops without. Cost-plus at 40% prices both at ₦7,000. The commodity is probably overpriced and losing share; the specialist part is dramatically underpriced, and the customer would have paid ₦12,000 without hesitating — because for them the alternative is a stopped line.</p>

<p>Same cost, same margin, two entirely different errors, and neither is visible in any report you receive.</p>

<p><b>Where cost-plus is genuinely right.</b> It is not useless. Where products are close substitutes and customers are price-comparing, cost-plus with a consistent margin is efficient and defensible. Where volume is stable and overhead is genuinely spread evenly, the absorbed cost is not far wrong. And it has a virtue nothing else has: it is fast, and a business with four thousand SKUs cannot value-price each one.</p>

<p><b>The practical answer is to segment rather than to abandon.</b> Use cost-plus as the default for the long tail, and take your top twenty lines by contribution — which will be a small fraction of the range and most of the money — and price those deliberately. That is a week's work once a year, and it is where the return is.</p>

<blockquote>WATCH-OUT: Cost-plus guarantees a margin only if you sell the volume it assumed. It does not guarantee profit, it does not guarantee competitiveness, and in a falling market it recommends raising prices. Treat it as a starting point rather than an answer.</blockquote>

<p><b>A related habit worth breaking: the standard margin.</b> Many businesses apply one percentage across a whole category because it is administratively simple. That guarantees the same error repeated across every line in the category — undercharging where value is high, overcharging where it is not — and it produces a price list that looks orderly and leaves money in two directions at once. Orderliness is not accuracy.</p>""",
 [C("Cost-plus prices in a circle because:",
    ["Costs rise with inflation", "Absorbed cost per unit depends on volume, which depends on price",
     "Margins are fixed", "Competitors respond"], 1,
    "When sales disappoint, absorbed cost rises and the method recommends raising price — the wrong direction."),
  C("Two products cost ₦5,000: one a commodity, one a part the customer's line stops without. Cost-plus at 40%:",
    ["Prices both correctly", "Overprices the commodity and underprices the specialist part",
     "Underprices both", "Overprices both"], 1,
    "Cost is a fact about you; price is a proposition to somebody else."),
  C("The practical response to cost-plus's faults is:",
    ["Abandon it entirely", "Add a bigger margin", "Keep it for the long tail and price the top lines deliberately",
     "Price everything at market"], 2,
    "A business with four thousand SKUs cannot value-price each one, but the top twenty carry most of the money.")]),

("What it is worth to them", 10, """<p>Value-based pricing sounds like a consultancy phrase. The underlying question is plain: <b>what does the customer get, and what is their alternative?</b> Everything else follows from those two.</p>

<p><b>Start with the alternative, because it sets the ceiling.</b> A customer buying from you always has other options — a competitor, a substitute product, doing without, doing it themselves. Your realistic maximum is roughly what the best alternative costs them, plus or minus whatever you are genuinely better or worse at.</p>

<p>So the question "what should we charge?" is really "what would they otherwise do, and what does that cost them?" A distributor whose alternative supplier is two days further away has a delivery cost, a stock cost and a risk cost attached to switching, and all of that is headroom you may be leaving on the table.</p>

<p><b>Value is often larger than the product.</b> The price of a spare part is not about the part. A customer whose production line is stopped is buying uptime, and the value is measured against what an idle line costs them per hour. Same physical item, entirely different willingness to pay depending on urgency — which is why availability, speed and reliability are pricing attributes rather than service niceties.</p>

<p><b>Different customers, different value, and this is where most money is left.</b> A hospital pharmacy buying regularly on contract, a corner chemist buying weekly, and a walk-in buying one pack are three different propositions. They differ in volume, in cost to serve, in payment reliability, and crucially in what alternatives they have. A single price across all three is simple, and it is simple in the way that leaves money with two of them.</p>

<p><b>Segmenting honestly.</b> The legitimate bases are volume, cost to serve, payment terms, channel and contract commitment — all defensible, all explicable to a customer who asks. Charging one customer more purely because they seem willing is a different thing, and in a market where buyers talk to each other it is a short-lived strategy that damages trust permanently when discovered. The test worth applying: could you explain your price structure to all your customers at once without embarrassment?</p>

<p><b>How to find out what it is worth without a research budget.</b> Ask your salespeople which lines never get haggled over — those are underpriced. Look at which products customers order at short notice regardless of price. Notice where you win deals without discounting, and where you lose them even after conceding. That information already exists inside your business and nobody has ever collected it deliberately.</p>

<blockquote>IMPLEMENTATION TIP: For your top ten lines, write one sentence each: what does the customer do if we are out of stock? A product whose answer is "they wait for us" and one whose answer is "they buy the other brand" should not be priced by the same rule, and most businesses price them identically.</blockquote>

<p><b>The competitor question, handled properly.</b> Knowing competitor prices is useful; matching them is not a strategy. If you match a competitor you have accepted their view of what your product is worth, which is a decision made by somebody with different costs, different customers and possibly a different objective. Use their price as information about the customer's alternative — which is what it is — rather than as an instruction.</p>""",
 [C("The realistic ceiling on your price is set mainly by:",
    ["Your cost plus a target margin", "What the customer's best alternative costs them",
     "Competitor list prices", "Industry convention"], 1,
    "Plus or minus whatever you are genuinely better or worse at."),
  C("A spare part for a stopped production line is priced against:",
    ["The cost of the part", "What an idle line costs the customer per hour",
     "The competitor's part price", "The freight cost"], 1,
    "Which is why availability and speed are pricing attributes, not service niceties."),
  C("Which basis for charging different customers different prices is hardest to defend?",
    ["Volume committed", "Cost to serve", "Payment terms", "Apparent willingness to pay"], 3,
    "In a market where buyers talk, it damages trust permanently when discovered.")]),

("Discounting: the arithmetic before the negotiation", 10, """<p>Module 4 showed that a discount comes out of contribution rather than out of price. This chapter turns that into the numbers you need before a negotiation rather than after it.</p>

<p><b>The break-even volume increase.</b> If you discount, how much more must you sell simply to stand still? The arithmetic is one line: discount divided by (contribution percentage less discount percentage).</p>

<p>At 30% contribution, a <b>5%</b> discount needs <b>20%</b> more volume to break even. A <b>10%</b> discount needs <b>50%</b> more. A <b>15%</b> discount needs <b>100%</b> more — you must double your sales to be no better off than before.</p>

<p>At 20% contribution it is brutal: a 10% discount needs volume to double.</p>

<p><b>Put that table in front of anyone with discount authority</b> and the conversation changes permanently. "Give them 10%" stops sounding like a concession and starts sounding like a commitment to sell half as much again.</p>

<p><b>The three questions to ask before agreeing any discount.</b></p>

<p><b>Is it buying anything?</b> A discount in exchange for volume, a longer commitment, faster payment or exclusivity is a trade. A discount given because the customer asked is a transfer. Most discounts are transfers described as trades.</p>

<p><b>Will it stay contained?</b> The single largest cost of discounting is rarely the deal itself. It is that the price becomes known — through a shared customer, a leaked invoice, a salesperson using it as precedent — and becomes the new reference price for everyone. One deal's ₦340,000 against a permanently repriced book is not a close call.</p>

<p><b>Would we have won it anyway?</b> Salespeople discount to remove risk from their own week, and often the deal was already won. If you never test this you will never know, which is an argument for occasionally holding firm and observing what actually happens.</p>

<p><b>Structure beats size.</b> A discount that arrives automatically at a volume threshold, paid quarterly in arrears as a rebate, is far better than the same money off the invoice. It rewards behaviour you want, it is not visible on any individual invoice to be used as a precedent, and it is contractual rather than personal — so it survives the salesperson leaving.</p>

<p><b>And the discipline that costs nothing.</b> Every discount granted should be recorded against the person who granted it and reviewed monthly in aggregate. Not to punish anybody — to make visible a cost that is otherwise invisible, because it appears nowhere except as a slightly lower average selling price that nobody can trace.</p>

<blockquote>WATCH-OUT: A discount already given is very hard to withdraw. Customers experience the discounted price as the price, and its removal as an increase — which is why a temporary promotional discount, repeated three times, has quietly become your list price with a marketing story attached.</blockquote>

<p><b>Who should hold discount authority, and at what depth.</b> The useful design is a tiered one: a small discretion at the front line for closing routine business, a larger one at supervisor level, and anything material requiring somebody who sees the whole margin picture. What matters is less where the lines fall than that they exist and are known. Unlimited discretion produces inconsistent pricing across customers who talk to each other, and the resulting conversations cost more than the discounts did.</p>""",
 [C("At 30% contribution, a 10% discount needs how much more volume to break even?",
    ["10%", "25%", "50%", "100%"], 2,
    "10 ÷ (30 − 10) = 50%. 'Give them 10%' means committing to sell half as much again."),
  C("At 20% contribution, a 10% discount requires volume to:",
    ["Rise 20%", "Rise 50%", "Double", "Rise 10%"], 2,
    "10 ÷ (20 − 10) = 100%. Lower contribution makes discounting brutal."),
  C("A rebate paid quarterly on volume achieved is better than an invoice discount because:",
    ["It costs less", "It is invisible as a precedent, rewards behaviour, and is contractual not personal",
     "It avoids VAT", "Customers prefer it"], 1,
    "It also survives the salesperson leaving, which an informal invoice discount does not.")]),

("Raising prices without losing the room", 10, """<p>In an economy with real inflation and currency movement, a business that does not raise prices is cutting them. Holding a price for a year while costs rise 20% is a decision to reduce your own margin, taken by not deciding.</p>

<p><b>The arithmetic of standing still.</b> Buying cost rises 15% on a product with 30% margin. Selling at ₦10,000 with cost ₦7,000 gives ₦3,000 of margin. Cost becomes ₦8,050. To hold ₦3,000 of margin the price must be ₦11,050 — a <b>10.5% increase to recover a 15% cost rise</b>. Raising by 15% would over-recover; raising by 5% loses ground while feeling like action.</p>

<p>Businesses that reprice by "adding the cost increase" as a percentage of price get this wrong in both directions routinely, and rarely notice.</p>

<p><b>Currency deserves separate treatment.</b> Goods bought at ₦1,550 to the dollar and repriced when the rate is ₦1,620 are already behind. And the exposure sits in the <i>replacement</i> cost, not the historical one: what matters for pricing is what the next container will cost, not what the last one did. A business pricing off historical cost during a devaluation makes a healthy-looking margin on every sale and cannot afford to restock — which is the mechanism by which importers go out of business while reporting profits.</p>

<p><b>How to raise a price without losing customers, in practice.</b></p>

<p><b>Give notice.</b> Two weeks' warning converts a shock into a plan, and lets loyal customers buy ahead — which costs you a little margin and buys a great deal of goodwill.</p>

<p><b>Give a reason, and let it be the true one.</b> Customers in this market understand currency and fuel. They do not understand vagueness, and an unexplained increase invites the assumption that it was opportunistic.</p>

<p><b>Do not apologise.</b> An apologetic increase invites negotiation. A matter-of-fact one, stated once and held, mostly gets accepted — and how you communicate it does more work than the number itself.</p>

<p><b>Move the range, not every line equally.</b> Customers anchor on a handful of items whose price they genuinely know. Hold those, move the rest further, and the perceived increase is far smaller than the achieved one.</p>

<p><b>Change something.</b> A new pack size, an improved delivery promise, a bundled service — any real change makes the old price a less useful comparison, and gives the customer something to receive alongside the increase.</p>

<p><b>What to expect.</b> Some noise from the loudest customers, who are not usually your best. Very little from the rest. The most common outcome of a well-executed price increase is that nothing much happens, which is exactly why the increase should have come sooner.</p>

<blockquote>IMPLEMENTATION TIP: After any price rise, watch volume weekly for six weeks. If it holds, you moved too late and probably too little. That is genuinely useful information and it is available only to businesses that measure the result rather than simply brace for it.</blockquote>

<p><b>Small and frequent beats large and rare.</b> Three 4% increases across a year are absorbed far more easily than one 12% increase, and they keep you level with costs rather than repeatedly falling behind and catching up. The single annual reprice is an administrative convenience that costs margin every month it is waited for — and it makes the eventual increase large enough to become an event customers respond to.</p>""",
 [C("Cost rises 15% on a product with 30% margin. The price increase needed to hold margin is about:",
    ["15%", "10.5%", "30%", "4.5%"], 1,
    "₦7,000 becomes ₦8,050; adding ₦3,000 of margin gives ₦11,050 against ₦10,000."),
  C("Stock bought at ₦1,550 to the dollar is repriced when the rate is ₦1,620. The margin shown is:",
    ["Accurate", "Flattering — it is measured against a cost you can no longer buy at",
     "Understated", "Unaffected by the rate"], 1,
    "It is the mechanism by which importers report profits and cannot afford to restock."),
  C("Volume holds completely for six weeks after a price rise. This suggests:",
    ["The increase was too aggressive", "You moved too late and probably too little",
     "Customers did not notice", "Competitors matched you"], 1,
    "Useful information, available only to businesses that measure the result rather than brace for it.")]),

("Mix: the margin nobody chose", 10, """<p>Module 1 named mix as one of the four things that move gross margin, and the one most often missed because every individual product looks fine. This chapter is about managing it deliberately, because mix is the only margin lever that improves without asking a single customer to pay more.</p>

<p><b>The arithmetic, so it stops being abstract.</b> A shop sells two categories. Category A does ₦6,000,000 a month at 40% margin. Category B does ₦4,000,000 at 20%. Blended margin is 32%, and gross profit is ₦3,200,000.</p>

<p>Next month total revenue is identical at ₦10,000,000, but the split has moved to ₦4,000,000 and ₦6,000,000. Blended margin falls to 28% and gross profit to ₦2,800,000. <b>₦400,000 of profit disappeared with no change in prices, costs, or total sales</b> — and every product line report would show nothing wrong at all.</p>

<p>Run it the other way and the same shift toward Category A adds ₦400,000 for free.</p>

<p><b>Why mix drifts without anybody deciding.</b> Promotions run on whatever the supplier funded, which is rarely your best-margin line. Salespeople lead with what is easiest to sell, which is usually the cheapest. Shelf space gets allocated by habit and by supplier pressure. Stockouts push customers to alternatives. None of these is a decision about mix, and together they are the decision about mix.</p>

<p><b>What managing it actually looks like.</b> Know the contribution percentage of your main categories — not the margin on the price list, the actual achieved contribution. Then look at where your visible resources go: front-of-store space, the promotion calendar, what the sales team leads with, what gets replenished first when stock is tight.</p>

<p>If your highest-contributing category occupies the worst shelf and never features in a promotion, your mix is being set by whoever funds your marketing rather than by you.</p>

<p><b>The stockout point, which is worth a line of its own.</b> Running out of a high-margin line does not merely lose that sale — it teaches the customer that the substitute is acceptable. A stockout on your best product is a mix decision with a long tail, and it is why availability on high-contribution lines deserves priority over availability generally.</p>

<p><b>And the caution against pushing mix too hard.</b> Customers do not buy categories, they buy baskets. A low-margin line that brings people through the door and anchors a basket is doing work that its own margin does not show. Removing it can take the profitable items with it. Before demoting anything, ask what else the customers who buy it are buying.</p>

<blockquote>IMPLEMENTATION TIP: Report blended margin alongside revenue every month, and when it moves, decompose it: how much came from price, how much from buying cost, how much from mix? Most businesses cannot answer that question, and the answer usually says mix — which is the cheapest of the three to fix.</blockquote>

<p><b>Mix inside a customer, not just inside a range.</b> The same logic applies to which customers grow. A month where your lowest-margin account grows fastest produces exactly the effect described above, at the customer level rather than the product level. It is worth knowing your contribution by customer as well as by line, because sales effort is usually directed at whoever buys most rather than whoever contributes most, and those are frequently different names.</p>""",
 [C("₦6m at 40% and ₦4m at 20% shifts to ₦4m and ₦6m, total unchanged. Gross profit:",
    ["Is unchanged", "Falls ₦400,000", "Rises ₦400,000", "Falls ₦800,000"], 1,
    "Blended margin drops from 32% to 28% with no change in price, cost or total sales."),
  C("Mix usually drifts because:",
    ["Customers change", "Promotions, shelf space and sales emphasis are decided by other pressures",
     "Costs rise", "Competitors discount"], 1,
    "None of those is a decision about mix, and together they are the decision about mix."),
  C("Before demoting a low-margin line you should ask:",
    ["Whether the supplier will fund it", "What else the customers who buy it are also buying",
     "Whether it can be repriced", "How much space it uses"], 1,
    "Customers buy baskets, and removing an anchor can take the profitable items with it.")]),

("Promotions, bundles and the price you did not mean to set", 10, """<p>A promotion is a temporary price cut with a marketing story attached, and it obeys exactly the discount arithmetic of chapter four. What makes promotions distinctive is what they do <i>after</i> they end.</p>

<p><b>The four outcomes, and only one of them is good.</b></p>

<p><b>Incremental sale.</b> Somebody buys who would not otherwise have bought. This is the outcome the promotion was designed for.</p>

<p><b>Brought-forward sale.</b> An existing customer buys next month's supply this month at a discount. Volume looks excellent, then next month looks poor, and the net effect is that you paid to move a sale forward.</p>

<p><b>Subsidised sale.</b> Somebody who would have paid full price pays less. Pure cost, no benefit, and typically the largest of the four in a promotion aimed at existing customers.</p>

<p><b>Substituted sale.</b> A customer switches from your full-price line to your promoted one. You have discounted your own product against yourself.</p>

<p>A promotion that lifts volume 40% has not necessarily done anything useful. The question is what proportion of that 40% was incremental, and the honest answer in most retail promotions is a minority of it.</p>

<p><b>The measurement that tells you the truth.</b> Compare the promoted period <i>and the period after</i> against the same window before. A promotion followed by a trough moved sales rather than creating them. Most promotion post-mortems stop at the end of the promotion, which guarantees a flattering answer.</p>

<p><b>Bundles are more interesting than discounts, and underused.</b> A bundle at a combined price the customer cannot decompose is harder to compare against a competitor, moves slower lines alongside faster ones, and can raise basket value without ever publishing a lower unit price. The condition is that the bundle contains something the customer genuinely wants — a bundle used to shift dead stock is recognised instantly and damages trust in every future offer.</p>

<p><b>The accidental price, which is the real subject of this chapter.</b> Promote the same line at the same discount three times in a year and you have not run three promotions. You have set a new price and trained customers to wait for it. The tell is simple and worth watching: volume in the weeks <i>before</i> a predictable promotion falls, because everybody knows it is coming.</p>

<p><b>How to avoid it.</b> Vary what is promoted, vary the depth, and vary the timing. Unpredictability is what preserves a promotion's power, and predictability is what converts it into a discount you now give permanently while still paying to advertise it.</p>

<blockquote>WATCH-OUT: Supplier-funded promotions feel free and are not. They consume your shelf space, your staff attention and your customer's attention, and they shift mix toward whatever the supplier wants to move — which is rarely your highest-contribution line. Free money that reshapes your mix is not free.</blockquote>

<p><b>One promotion type worth more than most: the one aimed at a behaviour rather than a product.</b> A discount for ordering online rather than by phone, for collecting rather than delivery, or for paying on the day, buys you a permanent operating saving rather than a temporary volume bump. The money spent is the same; what you own afterwards is different, because a behaviour you have shifted tends to stay shifted long after the offer ends.</p>""",
 [C("An existing customer buying next month's supply at a promotional price is:",
    ["An incremental sale", "A brought-forward sale", "A substituted sale", "A subsidised sale"], 1,
    "Volume looks excellent, next month looks poor, and you paid to move a sale forward."),
  C("A promotion should be measured over:",
    ["The promotional period only", "The promotional period and the period after it",
     "The following quarter", "The full year"], 1,
    "Stopping at the end of the promotion guarantees a flattering answer and hides the trough."),
  C("Running the same promotion at the same depth three times a year:",
    ["Builds brand loyalty", "Sets a new price and trains customers to wait for it",
     "Is the most efficient use of promotion", "Has no lasting effect"], 1,
    "The tell is falling volume in the weeks before a predictable promotion.")]),

("Credit is part of your price", 10, """<p>Two suppliers quote the same product at ₦10,000. One wants payment on delivery; the other offers sixty days. These are not the same price, and treating them as though they are is one of the most common commercial errors in a market where credit is scarce and expensive.</p>

<p><b>What the credit costs you.</b> Sixty days on ₦10,000, funded at 30% a year, costs roughly ₦493. So a ₦10,000 sale on sixty-day terms is economically about ₦9,500 — you have granted a 5% discount and called it terms.</p>

<p>The reason this matters is that the discount is invisible. It appears nowhere on the invoice, in the margin report, or in any discussion of pricing discipline. A business with tight discount controls and generous credit terms is running an uncontrolled discount scheme through a different door.</p>

<p><b>The three prices you are actually quoting.</b> Cash on delivery, thirty days, sixty days — and in a market with real interest rates, those should not be the same number. Quoting a single price regardless of terms means your cash customers are subsidising your credit customers, which is precisely backwards: the cash customer is the better customer and is being charged more in real terms.</p>

<p><b>Settlement discounts, and how to size one.</b> Offering 2% for payment within ten days on a sixty-day invoice buys you fifty days of money. Two per cent over fifty days is roughly 14.6% a year — cheap if your alternative is a 30% overdraft, expensive if you have surplus cash. The right answer depends on your own cost of money, which means you must know it before you can price terms sensibly.</p>

<p><b>Credit as a competitive weapon, and its danger.</b> Extending terms wins business, and it is the easiest concession to grant because nothing about it feels like a price cut. It is also the concession that consumes the most cash, arrives with the most risk, and is hardest to withdraw. A customer whose terms you extend from thirty to sixty days will treat any attempt to reverse it as a serious deterioration in the relationship.</p>

<p><b>The rule worth adopting.</b> Never extend terms without extracting something in exchange — volume commitment, price, exclusivity, or a personal guarantee. Terms are currency, and a business that gives them away for nothing has spent its currency without noticing it had any.</p>

<p><b>And the connection back to module 3.</b> Every day of terms you grant lengthens your cash cycle. If you know what one day of receivables costs you, you can price terms rather than concede them — which turns a soft conversation into an arithmetic one, and arithmetic is much easier to hold a line in.</p>

<p><b>The risk side, briefly.</b> Credit is not only a cost of money, it is an exposure to not being paid at all. A customer taking sixty days is consuming your cash; a customer taking sixty days who then fails costs you the entire margin on everything you ever sold them, and then some. So terms should follow creditworthiness rather than negotiating pressure — and the customer who negotiates hardest for terms is not always the one you would have chosen to lend to.</p>

<blockquote>IMPLEMENTATION TIP: Publish a price list with terms attached — one price for payment on delivery, another for thirty days. It makes the cost of credit visible to the customer and to your own team, and it converts an unmanaged concession into a priced product.</blockquote>""",
 [C("Sixty days' credit on ₦10,000, money costing 30% a year, is worth about:",
    ["₦100", "₦493", "₦3,000", "₦1,500"], 1,
    "Roughly 5% of the invoice — a discount granted invisibly and called terms."),
  C("Quoting one price regardless of payment terms means:",
    ["Everyone is treated fairly", "Cash customers subsidise credit customers",
     "Credit customers subsidise cash customers", "Terms are irrelevant to price"], 1,
    "Which is backwards: the cash customer is the better customer and pays more in real terms."),
  C("2% for payment in ten days on a sixty-day invoice is an annualised rate of roughly:",
    ["2%", "12%", "14.6%", "24%"], 2,
    "Cheap against a 30% overdraft, expensive if you are sitting on surplus cash.")]),

("The pricing decisions you actually make", 10, """<p>This is the chapter to keep. Six decisions, the question behind each, and the mistake each one invites.</p>

<p><b>1. What should this new product cost the customer?</b></p>

<p>Start from their alternative, not from your cost. Use cost only to establish the floor you must not go below. <i>The mistake:</i> cost-plus, which prices your specialist lines like commodities and hands away the money you were best placed to earn.</p>

<p><b>2. Should I approve this discount?</b></p>

<p>Ask what it buys, whether it will stay contained, and what volume increase would be needed to stand still. <i>The mistake:</i> treating a transfer as a trade, and discovering later that the discounted price has become the reference price for everybody.</p>

<p><b>3. Costs have risen. What do I do?</b></p>

<p>Calculate the increase needed to hold margin — which is smaller than the cost increase in percentage terms. Move promptly, give notice and a true reason, hold the anchor lines and move the rest. <i>The mistake:</i> delay, which is a decision to fund your supplier's increase out of your own margin.</p>

<p><b>4. Should we run this promotion?</b></p>

<p>Estimate honestly what share will be incremental rather than brought forward, subsidised or substituted. Measure the period after as well as during. <i>The mistake:</i> repetition, which turns a promotion into a permanent price you also pay to advertise.</p>

<p><b>5. Should we extend credit to win this account?</b></p>

<p>Price the terms, extract something in exchange, and check what it does to your cash cycle. <i>The mistake:</i> granting terms as though they were free because no discount appears on the invoice.</p>

<p><b>6. Our margin has fallen. Where do I look?</b></p>

<p>Price, buying cost, mix, loss — module 1's four movers. Establish which one before acting, because the four have entirely different remedies and the instinct is always to reach for price. <i>The mistake:</i> a general instruction to improve margin, which produces uncoordinated discounting discipline, uncoordinated buying pressure, and no diagnosis.</p>

<p><b>The habit worth building above all of these.</b> Price is reviewed too rarely and cut too easily. Most businesses revisit prices annually, in a rush, under cost pressure — and grant discounts weekly, individually, without arithmetic. Reversing that ratio is worth more than any single pricing decision in this chapter.</p>

<p><b>And the number to carry out of this module.</b> One per cent on price was worth 12.5% of profit in our example. Whatever the equivalent figure is in your business, it is larger than you assumed before chapter one, and it is the reason pricing deserves the seat at the table that cost-cutting currently occupies.</p>

<blockquote>IMPLEMENTATION TIP: Put a standing pricing review in the calendar — quarterly, thirty minutes, top twenty lines by contribution. Not a project, a rhythm. Businesses that do this reprice ahead of their costs; businesses that do not reprice after them, permanently one step behind.</blockquote>

<p><b>Who should be in that review.</b> Not finance alone — they know the costs and not the customers. Not sales alone — they know the customers and will always argue for lower. The useful room contains both, plus whoever controls buying, because a price decision made without knowledge of what the next container will cost is being made half-blind. Thirty minutes with three perspectives beats an afternoon with one.</p>""",
 [C("Cost should be used in pricing a new product mainly to:",
    ["Set the price by adding a margin", "Establish the floor you must not go below",
     "Match the competitor", "Justify the price to the customer"], 1,
    "Start from the customer's alternative; use cost to know where you cannot go."),
  C("Delaying a price increase after a cost rise is:",
    ["Prudent while you watch competitors", "A decision to fund your supplier's increase from your own margin",
     "Neutral if brief", "Preferable to losing volume"], 1,
    "Holding a price while costs rise is cutting it, taken by not deciding."),
  C("Most businesses get the pricing rhythm backwards by:",
    ["Reviewing prices too often", "Reviewing prices rarely and granting discounts weekly without arithmetic",
     "Discounting too rarely", "Repricing before costs move"], 1,
    "Reversing that ratio is worth more than any single pricing decision.")]),
]


QUESTIONS = [
 Q("Revenue ₦100m, 30% margin, overhead ₦22m, profit ₦8m. A 1% price rise with volume held gives profit of:", ["₦8.3m", "₦9.0m", "₦8.22m", "₦8.7m"], 1,
   "The whole ₦1m falls through, a 12.5% improvement.", "Ch1 §5", "Price as a lever"),
 Q("Which lever moves profit least in that example?", ["Price", "Volume", "Buying cost", "Overhead"], 3,
   "1% off overhead is ₦220,000, and it usually receives the most management attention.", "Ch1 §4", "Price as a lever"),
 Q("A salesperson gives away 3% on a deal at 30% margin. They have handed over about:", ["3% of profit", "10% of profit", "A third of the profit on it", "Nothing, if volume holds"], 2,
   "Discretion granted without arithmetic is an unmeasured cost centre.", "Ch1 §8", "Price as a lever"),
 Q("Volume growth is a weaker lever than price partly because:", ["Customers resist it", "It consumes cash in stock and receivables", "It raises overhead", "It reduces margin"], 1,
   "Price rises need no extra working capital at all.", "Ch1 §3", "Price as a lever"),
 Q("At 30% margin, a 1% price rise breaks even if volume falls by no more than about:", ["1%", "3.2%", "10%", "0.3%"], 1,
   "Roughly one customer in thirty, which in most businesses it would not.", "Ch1 §6", "Price as a lever"),
 Q("Cost-plus pricing uses which cost?", ["Marginal", "Landed", "Absorbed", "Replacement"], 2,
   "Which means changing the allocation rule changes the price.", "Ch2 §2", "Cost-plus and its limits"),
 Q("In a downturn, cost-plus recommends:", ["Lower prices", "Higher prices, because absorbed cost per unit rises", "Unchanged prices", "Withdrawing the product"], 1,
   "The method actively recommends the wrong direction.", "Ch2 §3", "Cost-plus and its limits"),
 Q("Cost-plus systematically underprices:", ["Commodities", "Products customers value highly", "Slow movers", "Bulky items"], 1,
   "Cost is a fact about you; it contains no information about the customer.", "Ch2 §4", "Cost-plus and its limits"),
 Q("Cost-plus is most defensible where:", ["Products are unique", "Products are close substitutes and customers price-compare", "Volumes are volatile", "Overhead is high"], 1,
   "And it has the virtue of being fast enough for a long tail of SKUs.", "Ch2 §7", "Cost-plus and its limits"),
 Q("The recommended practical approach is:", ["Value-price everything", "Cost-plus everything", "Cost-plus the tail, deliberately price the top lines by contribution", "Match competitors"], 2,
   "A week's work once a year, on the small fraction of lines carrying most of the money.", "Ch2 §8", "Cost-plus and its limits"),
 Q("The ceiling on price is set by:", ["Your target margin", "The customer's best alternative", "Your absorbed cost", "The market leader"], 1,
   "Adjusted for whatever you are genuinely better or worse at.", "Ch3 §2", "Value and willingness to pay"),
 Q("Availability and speed are best understood as:", ["Service standards", "Pricing attributes", "Overhead costs", "Marketing claims"], 1,
   "A customer with a stopped line is buying uptime, not a part.", "Ch3 §4", "Value and willingness to pay"),
 Q("Which is the least defensible basis for differential pricing?", ["Volume", "Cost to serve", "Payment terms", "Apparent willingness to pay"], 3,
   "Test: could you explain your structure to all customers at once without embarrassment?", "Ch3 §6", "Value and willingness to pay"),
 Q("A line that never gets haggled over is probably:", ["Correctly priced", "Underpriced", "Overpriced", "Unprofitable"], 1,
   "That information already exists in your business and is rarely collected.", "Ch3 §7", "Value and willingness to pay"),
 Q("At 30% contribution, a 5% discount requires extra volume of:", ["5%", "20%", "50%", "100%"], 1,
   "5 ÷ (30 − 5) = 20%.", "Ch4 §2", "Discount arithmetic"),
 Q("At 30% contribution, a 15% discount requires volume to:", ["Rise 15%", "Rise 50%", "Double", "Rise 30%"], 2,
   "15 ÷ (30 − 15) = 100%.", "Ch4 §3", "Discount arithmetic"),
 Q("Most discounts are:", ["Trades", "Transfers described as trades", "Contractual rebates", "Volume incentives"], 1,
   "A discount given because the customer asked buys nothing.", "Ch4 §6", "Discount arithmetic"),
 Q("The largest cost of discounting is usually:", ["The deal itself", "The price becoming the new reference for everyone", "Administration", "Delivery"], 1,
   "One deal's contribution against a permanently repriced customer base.", "Ch4 §7", "Discount arithmetic"),
 Q("Recording discounts against the person who granted them exists to:", ["Punish poor negotiators", "Make visible a cost that otherwise appears nowhere", "Satisfy audit", "Calculate commission"], 1,
   "Otherwise it shows only as a slightly lower average selling price nobody can trace.", "Ch4 §10", "Discount arithmetic"),
 Q("Buying cost rises 12% on a product with 25% margin. The price rise needed to hold margin is about:", ["12%", "9%", "25%", "3%"], 1,
   "Cost is 75% of price, so 12% of 75% is 9% of the selling price.", "Ch5 §2", "Price increases"),
 Q("During a devaluation an importer should price off:", ["Historical cost", "Replacement cost", "Average cost", "Competitor price"], 1,
   "Pricing off historical cost is how importers report profits and cannot afford to restock.", "Ch5 §4", "Price increases"),
 Q("Which most helps a price increase land?", ["Apologising for it", "Notice, a true reason, and holding the anchor lines", "Raising every line equally", "Announcing it after it takes effect"], 1,
   "An apologetic increase invites negotiation.", "Ch5 §6", "Price increases"),
 Q("Holding prices while costs rise 20% is:", ["Prudent", "A decision to cut your margin, taken by not deciding", "Customer-focused", "Neutral"], 1,
   "In an inflationary market, not repricing is repricing.", "Ch5 §1", "Price increases"),
 Q("Volume holding completely six weeks after an increase suggests:", ["It was too aggressive", "You moved too late and too little", "Competitors matched", "Customers will leave later"], 1,
   "Available only to businesses that measure the result rather than brace for it.", "Ch5 §9", "Price increases"),
 Q("₦6m at 40% and ₦4m at 20% becomes ₦4m and ₦6m with the same total. Blended margin moves from:", ["32% to 28%", "30% to 25%", "32% to 36%", "28% to 32%"], 0,
   "₦400,000 of profit disappears with no change in price, cost or total sales.", "Ch6 §2", "Mix"),
 Q("Mix is the only margin lever that:", ["Requires a price rise", "Improves without asking any customer to pay more", "Needs supplier agreement", "Reduces volume"], 1,
   "Which is why it is the cheapest of the four movers to fix.", "Ch6 §1", "Mix"),
 Q("A stockout on a high-contribution line is costly mainly because:", ["The sale is lost", "It teaches the customer the substitute is acceptable", "It raises stock days", "It affects the count"], 1,
   "A mix decision with a long tail.", "Ch6 §7", "Mix"),
 Q("Your best-contributing category occupies the worst shelf and never features in promotions. This means:", ["Mix is well managed", "Your mix is set by whoever funds your marketing", "The category is over-stocked", "Customers do not want it"], 1,
   "None of those pressures is a decision about mix, and together they are the decision.", "Ch6 §5", "Mix"),
 Q("An existing customer buying next month's supply on promotion is:", ["Incremental", "Brought forward", "Substituted", "Subsidised"], 1,
   "Volume looks excellent and next month looks poor.", "Ch7 §3", "Promotions and bundles"),
 Q("A customer switching from your full-price line to your promoted one is:", ["Incremental", "Brought forward", "Substituted", "Subsidised"], 2,
   "You have discounted your own product against yourself.", "Ch7 §5", "Promotions and bundles"),
 Q("Honest promotion measurement compares:", ["The promotion against budget", "The promotion and the period after against a comparable window before", "The promotion against last year", "Volume only"], 1,
   "Stopping at the end of the promotion guarantees a flattering answer.", "Ch7 §7", "Promotions and bundles"),
 Q("Bundles work only when:", ["The discount is deep", "They contain something the customer genuinely wants", "They clear dead stock", "They match a competitor"], 1,
   "A bundle used to shift dead stock is recognised instantly and damages future offers.", "Ch7 §8", "Promotions and bundles"),
 Q("Supplier-funded promotions are not free because:", ["They require matching funds", "They consume shelf space and attention and shift mix toward the supplier's priorities", "They attract tax", "They must be repeated"], 1,
   "Free money that reshapes your mix is not free.", "Ch7 §10", "Promotions and bundles"),
 Q("Sixty days on ₦10,000 at a 30% annual cost of money is worth about:", ["₦300", "₦493", "₦1,000", "₦100"], 1,
   "Roughly 5% — a discount granted invisibly and called terms.", "Ch8 §2", "Credit as price"),
 Q("A business with tight discount controls and generous terms is:", ["Well controlled", "Running an uncontrolled discount scheme through another door", "Conservative", "Cash rich"], 1,
   "The concession appears nowhere on the invoice or in the margin report.", "Ch8 §3", "Credit as price"),
 Q("Offering 2% for payment in ten days on a sixty-day invoice annualises to roughly:", ["2%", "14.6%", "24%", "36%"], 1,
   "Cheap against a 30% overdraft; expensive if you hold surplus cash.", "Ch8 §5", "Credit as price"),
 Q("Terms should never be extended without:", ["Board approval", "Something extracted in exchange", "A credit check", "A price increase"], 1,
   "Terms are currency, and most businesses spend theirs without noticing they had any.", "Ch8 §7", "Credit as price"),
 Q("Quoting one price regardless of terms means:", ["Fairness", "Cash customers subsidise credit customers", "Credit customers pay a premium", "Terms are not a cost"], 1,
   "Precisely backwards — the cash customer is the better customer.", "Ch8 §4", "Credit as price"),
 Q("When pricing a new product, cost tells you:", ["The right price", "The floor", "The ceiling", "The competitor's position"], 1,
   "The ceiling comes from the customer's alternative.", "Ch9 §2", "Pricing decisions"),
 Q("A general instruction to 'improve margin' fails because:", ["It is unpopular", "It produces action without a diagnosis of which of the four movers moved", "Margins cannot be improved", "It requires price rises"], 1,
   "Price, buying cost, mix and loss have entirely different remedies.", "Ch9 §7", "Pricing decisions"),
 Q("Most businesses get the rhythm backwards by:", ["Repricing quarterly", "Reviewing price rarely and discounting weekly without arithmetic", "Discounting rarely", "Repricing before costs rise"], 1,
   "Reversing that ratio is worth more than any single pricing decision.", "Ch9 §8", "Pricing decisions"),
 Q("A standing quarterly pricing review should cover:", ["Every SKU", "The top twenty lines by contribution", "Only new products", "Competitor prices"], 1,
   "Thirty minutes, a rhythm rather than a project.", "Ch9 §10", "Pricing decisions"),
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
    rebalance(QUESTIONS, "finance:pricing:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:pricing:checks")

    mod = {
        "title": "Margin, Pricing and the Decisions You Face",
        "desc": ("Price is the only lever that goes straight to profit, and it gets the "
                 "least management attention. Where cost-plus fails, what a customer's "
                 "alternative is worth, the volume a discount must recover, raising prices "
                 "in an inflationary market, mix as the margin nobody chose, promotions "
                 "that quietly become prices, and credit as an invisible discount."),
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
