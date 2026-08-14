#!/usr/bin/env python3
"""Build the Managing the Money module into academy_finance_data.json.

Track module 7. Module 3 taught how to measure cash — the cycle, the day
counts, the reconciliation, the forecast. This module is about deciding and
acting: credit policy, collections, stock policy, supplier terms, what funding
costs, and the order of moves when cash is tight.

Written for a market where money is genuinely expensive and term funding is
scarce, which changes the answers. Textbook working-capital advice assumes
cheap, available credit; here supplier terms are often the largest source of
funding a business will ever have, and that changes how they should be managed.

Checks scenario-first, exam questions computational — the separation that
stopped the overlap in module 6.

Run from the app package directory:  python3 build_finance_m8.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "money"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Working capital is a policy, not an outcome", 10, """<p>Most businesses treat working capital as something that happens to them. Stock is whatever buying bought, receivables are whatever customers have not paid, payables are whatever suppliers have not chased. The cash cycle is then reported monthly as though it were weather.</p>

<p>It is not weather. Every element of it is the sum of decisions somebody made, usually without knowing they were making a funding decision.</p>

<p><b>What a working capital policy actually contains.</b> Four numbers, agreed deliberately rather than arrived at:</p>

<p><b>Target stock cover</b> — how many days of sales you intend to hold, by category rather than overall, because fast lines and slow lines should not carry the same cover.<br>
<b>Standard credit terms</b> — what you offer by default, and what must be true for anything longer.<br>
<b>Target collection performance</b> — the debtor days you intend to run at, and what happens when an account passes it.<br>
<b>Supplier terms taken</b> — the terms you intend to use in full, rather than paying early out of habit.</p>

<p><b>Why write them down.</b> Because in the absence of a policy, each of the four is set by whoever has the strongest incentive to move it. Buying holds more stock because stockouts are visible and carrying cost is not. Sales grant longer terms because it wins orders and the cash cost lands somewhere else. Accounts pay suppliers early because it is easier than managing a due date. None of these people is wrong within their own frame, and together they set your funding requirement.</p>

<p><b>The number the policy produces.</b> Module 3 built the cash cycle: stock days plus debtor days less creditor days. A policy sets a target for it. At ₦180,000,000 of annual revenue, each day of cycle is roughly ₦493,000 of funding. Deciding to run at 66 days rather than 80 is a decision to need about ₦6,900,000 less money — permanently, without selling anything differently.</p>

<p><b>The trade-offs are real, and a policy names them.</b> Less stock risks stockouts. Tighter credit loses some customers. Taking full supplier terms strains relationships. A policy that pretends otherwise gets abandoned the first time it costs something. A policy that states the trade-off — "we accept a 2% stockout rate on C-lines in exchange for ₦4,000,000 less funding" — survives contact with reality, because the cost was expected.</p>

<p><b>Who owns it.</b> Working capital sits across buying, sales and finance, which means it belongs to none of them and drifts unless somebody senior owns the whole cycle. In most businesses this is the general manager or the owner, and it is rarely on their list until the cash runs short.</p>

<blockquote>IMPLEMENTATION TIP: Write your four numbers down this month, even as rough targets. The exercise itself surfaces the disagreements — buying and sales will not agree about stock cover, and finding that out in a meeting is far cheaper than finding it out from the bank.</blockquote>

<p><b>Review the four numbers when conditions change, not annually.</b> A policy written when money cost 18% is the wrong policy when it costs 30% — higher funding costs justify tighter stock and shorter terms, because the cost of carrying both has risen. Most businesses set working capital targets once and leave them, so the policy drifts out of line with the environment while the numbers themselves stay reassuringly stable.</p>""",
 [C("Buying holds extra stock, sales grants longer terms, accounts pays suppliers early. Each is defensible, and together they:",
    ["Balance out", "Set the business's funding requirement without anyone deciding it",
     "Improve service", "Reduce the cash cycle"], 1,
    "In the absence of a policy, each element is set by whoever has the strongest incentive to move it."),
  C("At ₦180m revenue, moving the cash cycle from 80 days to 66 releases roughly:",
    ["₦493,000", "₦6.9m of funding, permanently", "₦14m", "Nothing until sales grow"], 1,
    "14 days at about ₦493,000 a day, without selling anything differently."),
  C("A stock policy stated as 'hold less stock' rather than naming the accepted stockout rate will:",
    ["Work if enforced", "Be abandoned the first time it costs something",
     "Reduce funding permanently", "Improve service levels"], 1,
    "A policy that names its trade-off survives contact with reality because the cost was expected.")]),

("Deciding who to lend to", 10, """<p>Granting credit is lending. A business that would never make a loan without asking questions routinely extends ₦4,000,000 of goods on sixty-day terms to a customer nobody assessed, because it arrived as a sales decision rather than a financing one.</p>

<p><b>What you are actually deciding.</b> Not whether they will pay eventually — most will. Whether they will pay on time, whether you can afford the gap if they do not, and what it costs you to fund them meanwhile.</p>

<p><b>The assessment that is proportionate.</b> Full credit analysis is not realistic for every account. Three tiers works:</p>

<p><b>Small accounts</b> — cash or short terms, no assessment. The cost of checking exceeds the exposure.<br>
<b>Medium accounts</b> — trade references from two existing suppliers, how long they have traded, and a starting limit deliberately below what they ask for.<br>
<b>Large accounts</b> — the above plus accounts if available, a site visit, and terms that step up only after a payment history exists.</p>

<p><b>The single most useful signal is how they pay other people.</b> Two trade references, taken up properly with a real conversation rather than a form, will tell you more than any set of accounts. Suppliers are candid with each other about slow payers, and the question to ask is not "do they pay?" but "how many days, and do you have to chase?"</p>

<p><b>Start low and let them earn it.</b> A new account on a ₦500,000 limit that pays promptly for four months and asks for ₦2,000,000 has given you evidence. The same account granted ₦2,000,000 immediately has given you exposure. Raising a limit is a pleasant conversation; reducing one is not.</p>

<p><b>The concentration question from module 2 belongs here as a policy.</b> Set a maximum share of your receivables book that any single customer may represent. When a large customer wants more, the answer is not automatically no — it is that the exposure must be recognised, priced and possibly secured, rather than accumulated by default because each individual order seemed reasonable.</p>

<p><b>Security, briefly and practically.</b> Personal guarantees from directors, post-dated cheques, and payment on delivery for the portion above a limit are all common here and all worth asking for. The request itself is informative: a customer who refuses any form of security while asking for extended terms has told you something.</p>

<p><b>And the discipline nobody enjoys.</b> A credit limit that is never enforced is not a limit. If orders ship regardless once the limit is passed, you have a recording system rather than a control, and every person in the business learns which it is within about a month.</p>

<blockquote>WATCH-OUT: The riskiest accounts are frequently the fastest-growing ones. A customer whose orders double in three months may be thriving, or may be buying from you because their previous suppliers have stopped supplying them. Growth in a single account deserves a check, not just a celebration.</blockquote>

<p><b>Review limits on the way down as well as up.</b> Credit assessment is almost always treated as something done at the start of a relationship, after which the limit stands for years. But the customer whose payments have slowed from thirty-five days to seventy over eighteen months is a different credit risk from the one you assessed, and nothing in a normal ledger process will prompt anybody to say so. An annual review of the largest twenty accounts, comparing current behaviour against what was assumed when the limit was set, catches deterioration while it is still recoverable.</p>""",
 [C("A new customer asks for ₦2m on sixty days. The better opening position is:",
    ["Grant it — the order is valuable", "Grant ₦500,000 and let a payment history earn the rest",
     "Refuse until audited accounts are produced", "Grant it with a price increase"], 1,
    "Raising a limit is a pleasant conversation; reducing one is not."),
  C("Two trade references are available. The most useful question to ask each is:",
    ["Do they pay?", "How many days do they actually take, and do you have to chase?",
     "What limit do you give them?", "How long have you supplied them?"], 1,
    "Suppliers are candid with each other, and the days-and-chasing answer is the one that predicts your experience."),
  C("Orders continue to ship after a customer passes their credit limit. You have:",
    ["A flexible policy", "A recording system rather than a control",
     "An informal limit", "A relationship-led approach"], 1,
    "And everyone in the business learns which it is within about a month.")]),

("Collecting without losing the customer", 10, """<p>Collections is treated as an administrative function and is in fact a commercial one. Done well it protects both the cash and the relationship; done badly it damages one or the other, and usually the wrong one.</p>

<p><b>The principle that makes it work: collect early and gently rather than late and hard.</b> A call three days before an invoice falls due is a service — checking the paperwork arrived and everything is in order. A call three weeks after it fell due is a confrontation. The first costs nothing and prevents most of the second.</p>

<p><b>A cadence that works, and it is not complicated.</b></p>

<p><b>Before due date:</b> confirm the invoice was received and is approved for payment. Most late payment is not refusal — it is an invoice sitting unapproved on somebody's desk, and this call finds it while there is still time.</p>

<p><b>On the due date:</b> a short, friendly reminder. No implication of wrongdoing.</p>

<p><b>Seven days over:</b> a call, not an email, asking for a specific payment date rather than a general assurance. "When will it be paid?" is answerable; "please pay as soon as possible" is not.</p>

<p><b>Thirty days over:</b> escalation to a more senior person on your side speaking to a more senior person on theirs, and a hold on further supply if the policy says so.</p>

<p><b>Beyond sixty days:</b> a decision rather than a routine — a payment plan, security, or recovery. Continuing to send the same reminder monthly is not a strategy, it is a habit.</p>

<p><b>Separate the disputes, as module 2 argued.</b> An invoice queried over a short delivery, a wrong price or a missing document is not a payment problem and no amount of chasing will fix it. It needs somebody with authority to resolve it in days. Disputes ageing alongside genuine slow payers is the most common reason a receivables book looks worse than it is — and the most fixable.</p>

<p><b>Who should make the calls.</b> Not usually the salesperson who owns the relationship, because you are asking them to jeopardise their own next order. A separate voice makes it a process rather than a personal conflict, and lets the salesperson stay on the customer's side of the conversation. That separation is worth more than any script.</p>

<p><b>What to do about the customer who always pays late.</b> Price it, as module 5 argued, or shorten their terms, or both. A customer who reliably takes ninety days on thirty-day terms is not a slow payer, they are a ninety-day customer, and the honest response is to price them as one rather than to keep having the same conversation for years.</p>

<blockquote>IMPLEMENTATION TIP: Record a promised payment date on every collection call and check it on the day. A customer who breaks three promised dates has told you something no ageing report will, and it is the earliest reliable signal that an account is deteriorating.</blockquote>

<p><b>What to do when a genuinely good customer is genuinely struggling.</b> Not the same as a slow payer. A long-standing customer with a real temporary difficulty is worth supporting — a payment plan in writing, reduced supply rather than none, and a clear end point. What matters is that it is explicit and time-bound. The damaging version is the informal accommodation nobody documented, which quietly becomes the new normal and is discovered eighteen months later at four times the exposure.</p>""",
 [C("An invoice is three days from falling due. A call now is:",
    ["Premature and pushy", "A service call that finds an unapproved invoice while there is still time",
     "Only worthwhile for large accounts", "Best sent as an email"], 1,
    "Most late payment is an invoice sitting unapproved, not a refusal to pay."),
  C("At seven days overdue, the more effective ask is:",
    ["Please pay as soon as possible", "A specific date on which it will be paid",
     "A formal demand letter", "A supply hold"], 1,
    "A date is answerable and can be checked; a general assurance cannot."),
  C("The salesperson who owns the account is usually the wrong person to chase payment because:",
    ["They lack the training", "You are asking them to jeopardise their own next order",
     "They do not see the ledger", "It is a finance responsibility"], 1,
    "A separate voice makes it a process rather than a personal conflict.")]),

("How much stock is the right amount", 10, """<p>Stock is usually the largest call on a trading business's cash, and the decision about how much to hold is made hundreds of times a month by people optimising for something other than cash.</p>

<p><b>The asymmetry that drives over-stocking.</b> A stockout is visible, embarrassing and immediately attributable — a customer asked and we did not have it. Excess stock is invisible: it sits quietly, costs money nobody calculates, and nobody is ever blamed for it. So the rational individual behaviour, in the absence of a policy, is to hold more.</p>

<p><b>What excess stock actually costs.</b> The funding, at whatever your money costs — 25% a year on ₦10,000,000 of surplus is ₦2,500,000. Plus obsolescence, damage, and the space it occupies which module 4 priced as an opportunity cost. Stock is not free just because it is already bought.</p>

<p><b>Segment before you set cover.</b> A single stock policy across the range is always wrong somewhere. The standard split is by contribution and movement:</p>

<p><b>A-lines</b> — the small number of items that make most of your money and move fast. Hold generously; a stockout here is expensive twice, because module 5 showed it teaches the customer that the substitute is acceptable.<br>
<b>B-lines</b> — moderate movement. Standard cover, reviewed quarterly.<br>
<b>C-lines</b> — the long tail. Minimum cover, order to demand where you can, and accept a stockout rate deliberately.</p>

<p>Most businesses hold roughly equal cover across all three, which means over-investing in the tail and under-investing where the money is.</p>

<p><b>The reorder question in practical terms.</b> You need cover for the lead time plus a buffer for variability. If a supplier takes fourteen days and you sell 40 units a day, you need 560 units to cover the lead time alone, plus a buffer sized by how unreliable the supply and demand actually are. A supplier who is reliably fourteen days needs a smaller buffer than one who is fourteen days on average and twenty-eight sometimes — reliability is worth real money, and it belongs in the supplier conversation.</p>

<p><b>Dead stock, and the decision people avoid.</b> Stock that has not moved in a defined period is not an asset, it is cash that has changed shape and stopped. Module 4's sunk cost point applies exactly: what you paid is irrelevant. The only question is what it will fetch now against what the space and money could do instead. A business that clears dead stock quarterly at whatever it makes is in a better position than one holding it at full value on the books.</p>

<p><b>Who should decide stock cover, and on what evidence.</b> Not buying alone, whose incentives run one way, and not finance alone, who will always prefer less. The workable arrangement is that finance provides the funding cost per day of cover, operations provides the service consequence, and somebody senior chooses between them explicitly. That conversation happens once a quarter and takes half an hour, and it replaces a hundred individual ordering decisions each made on instinct.</p>

<blockquote>WATCH-OUT: Bulk discounts are the most common route to over-stocking, because the saving is calculable and the funding cost is not. A 5% discount for taking three months' cover instead of one is a poor trade if your money costs 25% a year — you have paid roughly 4% in funding to save 5%, before counting obsolescence and space.</blockquote>""",
 [C("Stockouts are chased and excess stock is not, mainly because:",
    ["Stockouts cost more", "Excess stock is invisible and nobody is ever blamed for it",
     "Buying is measured on availability", "Stock is an asset"], 1,
    "So the rational individual behaviour, absent a policy, is to hold more."),
  C("A supplier is fourteen days on average but sometimes twenty-eight. Compared with a reliable fourteen-day supplier you need:",
    ["The same buffer", "A larger buffer, which is a real cost belonging in the supplier conversation",
     "A smaller buffer", "No buffer if lead time is known"], 1,
    "Reliability is worth money, and it should be part of what you negotiate."),
  C("Most businesses hold similar cover across fast and slow lines. The effect is:",
    ["Balanced risk", "Over-investing in the tail and under-investing where the money is",
     "Lower stockouts overall", "Simpler ordering"], 1,
    "A single policy across the range is always wrong somewhere.")]),

("Supplier terms and the relationship behind them", 10, """<p>In a market where bank credit is expensive and often unavailable, supplier credit is frequently the largest source of funding a business has. It deserves to be managed as deliberately as a loan facility, and it almost never is.</p>

<p><b>What you are managing.</b> Not just days. The package is terms, price, reliability, and priority when supply is short — and they trade against each other. A supplier will often give you one at the expense of another, and knowing which you want is the whole of the negotiation.</p>

<p><b>Take the terms you have been given.</b> Module 3 made the point and it bears repeating as a policy: paying a thirty-day supplier in ten days lends them twenty days of your money for nothing. Unless there is a settlement discount that beats your cost of funds, pay on the due date. Not late, on the date.</p>

<p><b>Sizing a settlement discount properly.</b> Module 5 did the arithmetic from the seller's side; here it is from yours. Two per cent for paying in ten days rather than sixty buys them fifty days of your money at an annualised cost of roughly 14.6%. If your alternative use of that cash is an overdraft at 30%, take the discount. If you are already tight, do not — the discount is cheap money only if you have money.</p>

<p><b>Extending terms: what to offer.</b> Suppliers extend terms for volume commitment, forecast visibility, reliable payment history, or a longer contract. The most underused of these is <b>forecast visibility</b> — telling a supplier what you expect to buy over six months is genuinely valuable to them, costs you nothing, and is frequently worth more than the price concession you were going to ask for instead.</p>

<p><b>The limit, stated plainly.</b> Stretching payment beyond agreed terms works until it does not, and the failure mode is bad: supply slows, allocation goes elsewhere when stock is short, prices harden at the next review, and eventually a delivery you needed does not come. That last one usually arrives at your busiest moment, because that is when you were most stretched.</p>

<p><b>Concentration cuts both ways.</b> Module 2 raised customer concentration; supplier concentration is the mirror. If one supplier is 60% of your purchases, their terms decision is your funding decision and their supply problem is your stockout. A second source, even a more expensive one used for a modest share, is insurance with a calculable premium.</p>

<p><b>And the relationship point.</b> The supplier who backs you in a difficult month is the one you have been straight with. Businesses that communicate before missing a payment date get accommodation; businesses that go quiet and miss it get chased and downgraded. The difference costs one phone call.</p>

<p><b>One thing worth checking in your own terms.</b> Many suppliers quote terms from invoice date while delivering well before invoicing, or from statement date rather than invoice date — which can differ by two weeks or more. Businesses regularly believe they have forty-five days and actually have thirty. Read what the terms are measured from: it is free days if you are wrong in your favour, and an unexpected shortfall if you are not.</p>

<blockquote>IMPLEMENTATION TIP: List your five largest suppliers with the terms you have and the terms you actually take. Most businesses find at least one where they are paying faster than required for no reason other than habit, and correcting it is free funding available this month.</blockquote>""",
 [C("You pay a thirty-day supplier in ten days out of habit. You are:",
    ["Building goodwill efficiently", "Lending them twenty days of your money for nothing",
     "Reducing your cost of goods", "Managing risk prudently"], 1,
    "Unless a settlement discount beats your cost of funds, pay on the due date — not early, not late."),
  C("A supplier offers 2% for paying in ten days instead of sixty. Your overdraft costs 30%. You should:",
    ["Decline — discounts are never worth taking", "Take it if you have the cash, since it annualises near 14.6%",
     "Take it regardless of your cash position", "Negotiate for 4%"], 1,
    "It is cheap money only if you have money; if you are tight, the discount is not affordable."),
  C("The most underused thing to offer a supplier in exchange for longer terms is:",
    ["A price increase", "Forecast visibility over six months",
     "A personal guarantee", "Faster payment on other lines"], 1,
    "It is genuinely valuable to them, costs you nothing, and is often worth more than the concession you meant to ask for.")]),

("What money costs and where it comes from", 10, """<p>Every business is funded by somebody. The question is who, at what price, and on what conditions — and most managers have never been told the answer for their own business.</p>

<p><b>The sources, roughly in order of cost.</b></p>

<p><b>Supplier credit.</b> Usually free within terms, and it is the largest source for most trading businesses. Its price is paid in flexibility and relationship rather than interest.</p>

<p><b>Retained profit.</b> Feels free and is not — it is the owners' money, and it has an opportunity cost equal to whatever else they could do with it. Treating retained earnings as costless is how businesses justify investments that would never survive a proper hurdle.</p>

<p><b>Bank overdraft.</b> Flexible, expensive, and repayable on demand — which is the clause people forget until the moment it is used. Suitable for genuine short-term swings, dangerous as permanent funding.</p>

<p><b>Term loans.</b> Cheaper than an overdraft, fixed repayments, and they match the funding to the life of what is being funded. The right instrument for an asset that will earn over five years.</p>

<p><b>Invoice discounting and LPO financing.</b> Expensive in annualised terms, and genuinely useful when the alternative is turning down an order you cannot fund. Judge it against the contribution on the order rather than against a bank rate.</p>

<p><b>Equity.</b> The most expensive of all, because it has no ceiling — you give away a share of everything the business will ever earn. It is also the only funding that cannot demand its money back at a bad moment.</p>

<p><b>The rule that prevents the commonest funding error: match the term to the use.</b> Fund long-term assets with long-term money and short-term working capital swings with short-term money. Businesses that buy vehicles on an overdraft are the classic failure — the asset earns over five years and the funding can be withdrawn in five days.</p>

<p><b>Know your actual cost of money.</b> Not the headline rate. The effective rate includes arrangement fees, insurance requirements, compensating balances you must keep, and the cost of any security. A 24% facility with a 2% arrangement fee and a required 10% deposit is not 24%. Until you know the real figure you cannot price credit terms, size a settlement discount, or evaluate a bulk buy — which is why this number belongs on a manager's list rather than only on the finance director's.</p>

<p><b>The permanent overdraft, which deserves naming.</b> Many businesses run an overdraft that never clears — it moves between ₦12,000,000 and ₦18,000,000 and has not been at zero for three years. That ₦12,000,000 is not short-term funding, it is permanent working capital financed on a demand facility at the highest rate available. Converting the permanent portion to a term loan usually costs less and cannot be withdrawn at a week's notice.</p>

<blockquote>WATCH-OUT: Repayable on demand means what it says. Overdrafts are typically reviewed annually and can be reduced or withdrawn — most often when the bank sees deterioration, which is exactly when you need it. Never let a business depend on a facility that can disappear at the moment of need.</blockquote>""",
 [C("A business funds delivery vehicles on its overdraft. The structural problem is:",
    ["The rate is too high", "An asset earning over five years is funded by money withdrawable in five days",
     "Depreciation exceeds repayment", "Overdrafts cannot fund assets"], 1,
    "Match the term of the funding to the life of what it funds."),
  C("Your overdraft has moved between ₦12m and ₦18m and never reached zero in three years. The ₦12m is:",
    ["Genuine short-term funding", "Permanent working capital on a demand facility at the highest rate available",
     "A reserve", "An accounting artefact"], 1,
    "Converting the permanent portion to a term loan usually costs less and cannot be withdrawn at a week's notice."),
  C("Treating retained profit as free funding leads a business to:",
    ["Reinvest efficiently", "Justify investments that would not survive a proper hurdle rate",
     "Under-invest", "Pay excessive dividends"], 1,
    "It is the owners' money and carries the opportunity cost of whatever else they could do with it.")]),

("The banking relationship", 10, """<p>A bank facility is not only a financial product; it is a relationship with an institution that will make judgements about you under uncertainty. How you manage the relationship changes what is available and when.</p>

<p><b>What a bank is actually assessing.</b> Not your profit, primarily. Whether you can service the debt from cash generated, whether the business is stable enough to keep doing so, what they can recover if it stops, and — more than most managers realise — whether the management is credible. That last one is assessed almost entirely on how you communicate.</p>

<p><b>The behaviour that builds credibility.</b> Provide information before it is requested. Present bad news early with a plan attached rather than late with an explanation. Be accurate about forecasts and then meet them, because a business that hits modest forecasts is treated far better than one that misses ambitious ones. Bankers price uncertainty, and predictability is cheaper than optimism.</p>

<p><b>What to bring to a facility conversation.</b> The thirteen-week cash forecast from module 3, the reason for the request, what it will be used for specifically, how it will be repaid and from what, and what you are offering as security. A request for "an increase in the overdraft" with no forecast attached invites the least favourable answer available, because the bank must assume the worst case it can imagine.</p>

<p><b>Ask before you need it.</b> This is the single most valuable practice in this chapter. A facility negotiated from a position of comfort is cheaper, larger and less conditional than the same facility requested in the week it becomes urgent. Banks read urgency accurately and price it. And a business that has never asked for anything is not a low-risk borrower in the bank's eyes — it is an unknown one.</p>

<p><b>Understand the covenants.</b> Facilities frequently carry conditions — minimum cover ratios, gearing limits, restrictions on further borrowing or on dividends. Breaching one can make the whole facility repayable regardless of whether payments were made. Know which covenants you have and how much headroom exists before a decision breaches one, because the decisions that breach covenants — a large capital purchase, a dividend, a new loan — are exactly the ones taken without consulting the facility letter.</p>

<p><b>More than one relationship.</b> A single banking relationship is a concentration risk of the kind module 2 described. Even a modest second facility elsewhere provides an alternative and improves your position in every negotiation with the first. The cost is administrative; the value appears in the year you need it.</p>

<p><b>And the point managers most often miss.</b> Your account behaviour is data. Bounced payments, consistently running at the overdraft limit, month-end spikes that suggest window dressing — the bank sees all of it, continuously, and forms a view long before any conversation happens. The facility review is not where the assessment is made; it is where a conclusion already reached is communicated.</p>

<blockquote>IMPLEMENTATION TIP: Send your bank something useful once a quarter without being asked — a short trading update, the current forecast, progress against what you last told them. It costs almost nothing and it changes what happens in the year you need something, because you have become predictable rather than opaque.</blockquote>""",
 [C("A business needs a larger overdraft in six weeks. The best time to ask is:",
    ["When the need becomes certain", "Now, from a position of comfort",
     "After the next set of accounts", "When the bank next reviews the facility"], 1,
    "Banks read urgency accurately and price it. Comfort buys cheaper, larger, less conditional terms."),
  C("A facility request is made with no cash forecast attached. The bank will:",
    ["Assess it on the accounts alone", "Assume the worst case it can imagine",
     "Request one and wait", "Approve at standard terms"], 1,
    "Bring the thirteen-week forecast, the purpose, the repayment source and the security."),
  C("A large capital purchase is being considered. Before approving it you should check:",
    ["The depreciation rate", "Whether it breaches a banking covenant",
     "The supplier's terms", "The insurance position"], 1,
    "Breaching one can make the whole facility repayable, and these are exactly the decisions taken without reading the facility letter.")]),

("When cash is tight: the order of moves", 10, """<p>Every business has weeks where the money will not comfortably cover what is due. What separates outcomes is not whether it happens but the order in which you move — because the cheap options expire first, and panic reliably selects the expensive ones.</p>

<p><b>First, know the position precisely.</b> Exactly what is in the bank, exactly what must go out and when, exactly what is due in and from whom. Module 3's six questions, done properly today. Most bad decisions in a cash squeeze are made on an approximate picture, and the approximation is nearly always more pessimistic than the truth — which drives people to expensive money they did not need.</p>

<p><b>Then, in this order.</b></p>

<p><b>1. Collect.</b> The fastest and cheapest cash available is money already owed to you. Named accounts, specific calls, today. A focused week of collection typically produces more than any other single action, and it costs nothing but goodwill you can afford.</p>

<p><b>2. Defer what can be deferred without cost.</b> Discretionary purchases, non-urgent capital, anything with no penalty attached. This buys time rather than money, and time is what you need.</p>

<p><b>3. Talk to suppliers before the date, not after.</b> A supplier asked in advance for two extra weeks usually agrees. The same supplier discovering a missed payment starts a different process. This is the largest single lever most businesses have and it is routinely used last, out of embarrassment.</p>

<p><b>4. Release stock.</b> Slow lines at a discount, in quantity. It hurts margin and it converts a dead asset into live cash, and module 4's sunk cost point applies: what you paid for it is not relevant to what you should accept now.</p>

<p><b>5. Use facilities you already have.</b> Committed lines, arranged before the pressure, at agreed rates.</p>

<p><b>6. Only then, new expensive money.</b> Invoice discounting, LPO finance, short-term lending. Judge each against what it prevents — losing a supplier, missing payroll, forfeiting an order — rather than against a rate table, because at this point you are pricing consequences, not credit.</p>

<p><b>What not to do, and these are the common ones.</b> Do not miss payroll — the operational and reputational damage exceeds almost any financing cost. Do not use tax money collected on somebody else's behalf, because it is not yours and the arrears carry penalties and a due date that will not move. Do not go silent with anybody you owe; silence converts a solvable timing problem into a credit event. And do not fund a structural gap with short-term money repeatedly — if the squeeze recurs every month, the problem is the cash cycle or the cost base, and borrowing monthly is treating a symptom at increasing cost.</p>

<p><b>The tell for structural versus temporary.</b> A temporary squeeze has an identifiable cause and an end date — a seasonal build, a large customer paying late, a capital purchase. A structural one has neither, and recurs. Naming which you have is the difference between managing a week and needing to change the business.</p>

<blockquote>WATCH-OUT: The most expensive decision in a cash squeeze is usually made in the first hour, from an incomplete picture, under pressure. Spend that hour establishing the position instead. It feels like inaction and it is the highest-return work available.</blockquote>""",
 [C("Cash is tight this week. The first move should be:",
    ["Approach the bank", "Establish the position precisely — bank, outgoings, receipts by name",
     "Discount stock", "Delay payroll"], 1,
    "Most bad squeeze decisions are made on an approximate picture that is more pessimistic than the truth."),
  C("Of the levers available, the one most often used last out of embarrassment is:",
    ["Collecting receivables", "Talking to suppliers before the date rather than after",
     "Discounting stock", "Drawing the overdraft"], 1,
    "A supplier asked in advance usually agrees; one discovering a missed payment starts a different process."),
  C("The squeeze recurs every month with no identifiable cause. Borrowing again is:",
    ["The correct response", "Treating a symptom at increasing cost — the cycle or cost base is the problem",
     "Cheaper than collecting", "Necessary until sales grow"], 1,
    "A temporary squeeze has a cause and an end date. A structural one has neither.")]),

("The money conversations you actually have", 10, """<p>This is the chapter to keep. Six conversations, what to bring, and the mistake each invites.</p>

<p><b>1. "This customer wants sixty days instead of thirty."</b></p>

<p>Price it, extract something for it, and check the concentration. Thirty extra days on ₦4,000,000 at 30% money costs about ₦100,000 a year. <i>The mistake:</i> granting it as a relationship gesture because no discount appears on the invoice, then discovering the cost only in the cash cycle where nobody attributes it to this decision.</p>

<p><b>2. "We should take the bulk discount."</b></p>

<p>Compare the discount against the funding cost of the extra cover, plus obsolescence and space. 5% for three months' cover instead of one is roughly a 4% funding cost at 25% money, before anything goes stale. <i>The mistake:</i> counting the saving, which is calculable, and ignoring the cost, which is not printed anywhere.</p>

<p><b>3. "The account is ninety days over."</b></p>

<p>Establish whether it is a dispute or a payment problem — they need different people and different timescales. Get a specific date. Decide, rather than sending the same reminder for a fourth month. <i>The mistake:</i> routine chasing that substitutes activity for a decision.</p>

<p><b>4. "We need to increase the overdraft."</b></p>

<p>Bring the thirteen-week forecast, the purpose, the repayment source, the security. Ask before it is urgent. <i>The mistake:</i> asking in the week of need, when the bank prices your urgency and you have no negotiating position at all.</p>

<p><b>5. "Cash is tight this week."</b></p>

<p>Establish the position precisely, then collect, defer, talk to suppliers, release stock, use committed facilities, and only then buy expensive money. <i>The mistake:</i> reaching for step six in the first hour on an incomplete picture.</p>

<p><b>6. "Why are we short when we're profitable?"</b></p>

<p>Module 3's reconciliation answers this in four minutes: profit, plus depreciation, less the movements in stock and receivables, plus the movement in payables. Then decide which of the three you are going to attack. <i>The mistake:</i> treating it as a mystery, or as a finance problem, when it is three balance sheet lines and each has an owner.</p>

<p><b>What this module has really been about.</b> Every one of those conversations is a funding decision wearing other clothes — a terms decision, a buying decision, a collection decision. Businesses fail not because somebody made a catastrophic financing choice but because dozens of small decisions, each sensible in its own frame, together set a funding requirement nobody chose and nobody owns.</p>

<p><b>The habit worth keeping.</b> Before agreeing anything that moves stock, terms or payment timing, ask what it does to the cash cycle. It takes a few seconds, it is almost never asked, and it is the difference between a business that funds its growth and one that is surprised by it.</p>

<blockquote>IMPLEMENTATION TIP: Put your four working capital policy numbers, your real cost of money, and your current cash cycle on a single card. Six figures. Almost every decision in this module can be made sensibly from that card, and almost none can be made sensibly without it.</blockquote>""",
 [C("A customer asks for thirty extra days on ₦4m, with money costing 30%. The concession is worth roughly:",
    ["₦4,000 a year", "₦100,000 a year", "₦1.2m a year", "Nothing, if they pay"], 1,
    "Price it and extract something for it, rather than granting it because no discount shows on the invoice."),
  C("A 5% bulk discount requires holding three months' cover instead of one, with money at 25%. This is:",
    ["Clearly worth taking", "Roughly a 4% funding cost against a 5% saving, before obsolescence and space",
     "Free money", "Only worthwhile for A-lines"], 1,
    "The saving is calculable and the cost is printed nowhere, which is why the trade looks better than it is."),
  C("Asked why the business is short despite being profitable, the four-minute answer is:",
    ["A finance systems problem", "Profit plus depreciation, less stock and receivables movements, plus payables",
     "Seasonal timing", "An overdraft limit issue"], 1,
    "Three balance sheet lines, each with an owner — not a mystery.")]),
]


QUESTIONS = [
 Q("A working capital policy should set targets for stock cover, credit terms, collection performance and:", ["Gross margin", "Supplier terms taken", "Headcount", "Capital spending"], 1,
   "Four numbers agreed deliberately rather than arrived at.", "Ch1 §3", "Working capital policy"),
 Q("At ₦180m annual revenue, one day of cash cycle is worth roughly:", ["₦180,000", "₦493,000", "₦1.5m", "₦15m"], 1,
   "Which is why a fourteen-day improvement releases about ₦6.9m.", "Ch1 §6", "Working capital policy"),
 Q("Working capital drifts in most businesses because it:", ["Cannot be measured", "Sits across buying, sales and finance and so belongs to none of them", "Depends on the bank", "Changes seasonally"], 1,
   "It needs somebody senior owning the whole cycle.", "Ch1 §8", "Working capital policy"),
 Q("A policy that names its trade-off explicitly is more likely to:", ["Be approved", "Survive the first time it costs something", "Reduce stockouts", "Lower prices"], 1,
   "Because the cost was expected rather than discovered.", "Ch1 §7", "Working capital policy"),
 Q("Granting ₦4m of goods on sixty days without assessment is best described as:", ["A sales decision", "An unassessed loan", "A marketing cost", "Standard practice"], 1,
   "It arrives dressed as a sales decision, which is why nobody assesses it.", "Ch2 §1", "Credit assessment"),
 Q("The most useful credit signal for a medium-sized new account is:", ["Audited accounts", "How they pay their other suppliers", "Their premises", "Their order size"], 1,
   "Two references taken up in conversation beat any document.", "Ch2 §4", "Credit assessment"),
 Q("Starting a new account on a low limit that rises with payment history gives you:", ["Exposure", "Evidence", "A slower sale", "A weaker relationship"], 1,
   "Raising a limit is a pleasant conversation; reducing one is not.", "Ch2 §5", "Credit assessment"),
 Q("A customer whose orders double in three months should prompt:", ["Celebration only", "A check on why their previous suppliers stopped supplying them", "An automatic limit increase", "A price reduction"], 1,
   "The riskiest accounts are frequently the fastest-growing ones.", "Ch2 §8", "Credit assessment"),
 Q("A credit limit that is not enforced is:", ["A guideline", "A recording system rather than a control", "A relationship tool", "A pricing mechanism"], 1,
   "Everyone learns which it is within about a month.", "Ch2 §7", "Credit assessment"),
 Q("The principle behind effective collections is:", ["Firm and formal from the outset", "Early and gentle rather than late and hard", "Escalate immediately", "Leave it to the salesperson"], 1,
   "A call before the due date is a service; the same call three weeks late is a confrontation.", "Ch3 §2", "Collections"),
 Q("Most late payment is caused by:", ["Refusal to pay", "An invoice sitting unapproved on somebody's desk", "Disputes over quality", "Cash shortage"], 1,
   "Which is why the pre-due-date call finds it while there is still time.", "Ch3 §4", "Collections"),
 Q("At thirty days overdue the appropriate step is:", ["A further email", "Escalation on both sides, and a supply hold if policy says so", "A discount offer", "Legal action"], 1,
   "Routine reminders past this point substitute activity for a decision.", "Ch3 §6", "Collections"),
 Q("A disputed invoice ageing in the ledger needs:", ["The same chasing as any other", "Somebody with authority to resolve it in days", "A provision", "Escalation to legal"], 1,
   "It is the most common reason a book looks worse than it is, and the most fixable.", "Ch3 §8", "Collections"),
 Q("A customer who breaks three promised payment dates has given you:", ["An administrative inconvenience", "The earliest reliable signal that the account is deteriorating", "Grounds for legal action", "A pricing opportunity"], 1,
   "No ageing report tells you this.", "Ch3 §11", "Collections"),
 Q("Surplus stock of ₦10m, money costing 25% a year, carries a funding cost of:", ["₦250,000", "₦2.5m", "₦10m", "Nothing — it is already bought"], 1,
   "Before obsolescence, damage and the space it occupies.", "Ch4 §3", "Stock policy"),
 Q("Selling 40 units a day with a fourteen-day supplier lead time requires cover of at least:", ["40", "560", "140", "280"], 1,
   "Plus a buffer sized by how variable supply and demand actually are.", "Ch4 §7", "Stock policy"),
 Q("A-lines should be held:", ["At minimum cover", "Generously, because a stockout is expensive twice", "At the same cover as C-lines", "To order only"], 1,
   "It loses the sale and teaches the customer that the substitute is acceptable.", "Ch4 §5", "Stock policy"),
 Q("A 5% bulk discount requiring three months' cover instead of one, at 25% money, costs roughly:", ["1% in funding", "4% in funding", "15% in funding", "Nothing"], 1,
   "Two extra months of funding at about 2% a month, before obsolescence and space.", "Ch4 §10", "Stock policy"),
 Q("Dead stock should be valued for decision purposes at:", ["What it cost", "What it will fetch now, against what the space and money could do instead", "Its insured value", "Its replacement cost"], 1,
   "Module 4's sunk cost point applies exactly.", "Ch4 §9", "Stock policy"),
 Q("For most trading businesses in a high-rate market, the largest source of funding is:", ["Bank overdraft", "Supplier credit", "Term loans", "Equity"], 1,
   "It deserves to be managed as deliberately as a loan facility.", "Ch5 §1", "Supplier terms"),
 Q("Paying a thirty-day supplier in ten days means:", ["A cost reduction", "Lending them twenty days of your money for nothing", "Improved terms next year", "Lower risk"], 1,
   "Unless a settlement discount beats your cost of funds.", "Ch5 §3", "Supplier terms"),
 Q("2% for payment in ten days rather than sixty annualises to roughly:", ["2%", "14.6%", "30%", "8%"], 1,
   "Worth taking against a 30% overdraft — if you have the cash.", "Ch5 §4", "Supplier terms"),
 Q("One supplier represents 60% of purchases. This means:", ["Good buying leverage", "Their terms decision is your funding decision", "Lower prices", "Simplified logistics"], 1,
   "And their supply problem is your stockout.", "Ch5 §7", "Supplier terms"),
 Q("The supplier most likely to accommodate you in a difficult month is:", ["The largest", "The one you have been straight with", "The newest", "The cheapest"], 1,
   "The difference between accommodation and being chased costs one phone call.", "Ch5 §8", "Supplier terms"),
 Q("Which funding source has no ceiling on its cost?", ["Overdraft", "Equity", "Term loan", "Invoice discounting"], 1,
   "You give away a share of everything the business will ever earn.", "Ch6 §7", "Cost of funding"),
 Q("The rule that prevents the commonest funding error is:", ["Borrow as little as possible", "Match the term of the funding to the life of what it funds", "Always use term loans", "Avoid overdrafts"], 1,
   "Vehicles on an overdraft is the classic failure.", "Ch6 §8", "Cost of funding"),
 Q("An overdraft that has never reached zero in three years is:", ["Well managed", "Permanent working capital on a demand facility", "A reserve", "Short-term funding"], 1,
   "Converting the permanent portion to a term loan usually costs less and cannot be withdrawn at a week's notice.", "Ch6 §10", "Cost of funding"),
 Q("Your effective cost of money includes the headline rate plus:", ["VAT", "Fees, required deposits and the cost of security", "Depreciation", "Inflation only"], 1,
   "Until you know the real figure you cannot price terms or size a discount.", "Ch6 §9", "Cost of funding"),
 Q("Invoice discounting should be judged against:", ["A bank rate table", "The contribution on the order it lets you accept", "The prime rate", "Your gross margin"], 1,
   "Expensive in annualised terms, and useful when the alternative is turning the order down.", "Ch6 §6", "Cost of funding"),
 Q("Beyond the numbers, a bank is assessing:", ["Your gross margin", "Whether management is credible, judged largely on how you communicate", "Your market share", "Your product range"], 1,
   "Bankers price uncertainty, and predictability is cheaper than optimism.", "Ch7 §2", "Banking relationships"),
 Q("A facility request should be accompanied by:", ["Last year's accounts only", "A cash forecast, the purpose, the repayment source and the security", "A business plan", "A profit projection"], 1,
   "Without it the bank must assume the worst case it can imagine.", "Ch7 §4", "Banking relationships"),
 Q("Breaching a banking covenant can:", ["Increase the interest rate only", "Make the whole facility repayable regardless of payment history", "Trigger a review at year end", "Require additional security"], 1,
   "And the decisions that breach them are exactly those taken without reading the facility letter.", "Ch7 §6", "Banking relationships"),
 Q("A business that has never asked its bank for anything is seen as:", ["Low risk", "An unknown", "Well capitalised", "Preferred"], 1,
   "Which is not the same as low risk, and is priced differently.", "Ch7 §5", "Banking relationships"),
 Q("The bank forms its view of you primarily from:", ["The annual review meeting", "Continuous account behaviour", "Your published accounts", "Industry reports"], 1,
   "The review is where a conclusion already reached is communicated.", "Ch7 §8", "Banking relationships"),
 Q("The first action in a cash squeeze is:", ["Draw the overdraft", "Establish the position precisely", "Discount stock", "Call the bank"], 1,
   "Most bad squeeze decisions are made on an approximate and unduly pessimistic picture.", "Ch8 §2", "When cash is tight"),
 Q("The cheapest and fastest cash available is usually:", ["An overdraft", "Money already owed to you", "Stock discounting", "Invoice finance"], 1,
   "A focused week of collection typically beats any other single action.", "Ch8 §4", "When cash is tight"),
 Q("Which must not be used to fund a squeeze?", ["Slow stock", "Tax collected on somebody else's behalf", "Committed facilities", "Deferred capital spending"], 1,
   "It is not yours, and the arrears carry penalties and an immovable due date.", "Ch8 §9", "When cash is tight"),
 Q("A squeeze with no identifiable cause that recurs monthly indicates:", ["Seasonality", "A structural problem in the cash cycle or cost base", "A collections failure", "A banking issue"], 1,
   "Borrowing monthly is treating a symptom at increasing cost.", "Ch8 §10", "When cash is tight"),
 Q("Thirty extra days on ₦4m with money at 30% costs roughly:", ["₦12,000", "₦100,000 a year", "₦1.2m a year", "₦400,000"], 1,
   "Price the concession rather than granting it as a gesture.", "Ch9 §2", "Money conversations"),
 Q("Businesses fail on working capital mainly because:", ["One catastrophic financing decision", "Dozens of small decisions each sensible in its own frame", "Bank withdrawal", "Poor margins"], 1,
   "Together they set a funding requirement nobody chose and nobody owns.", "Ch9 §8", "Money conversations"),
 Q("Before agreeing anything that moves stock, terms or payment timing, ask:", ["What it does to margin", "What it does to the cash cycle", "Whether it is budgeted", "Who approved it"], 1,
   "A few seconds, almost never asked.", "Ch9 §9", "Money conversations"),
 Q("The six figures worth keeping on one card are the four policy targets, the cash cycle and:", ["Gross margin", "Your real cost of money", "Revenue", "Headcount"], 1,
   "Almost no decision in this module can be made sensibly without it.", "Ch9 §10", "Money conversations"),
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
    rebalance(QUESTIONS, "finance:money:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:money:checks")

    mod = {
        "title": "Managing the Money",
        "desc": ("Working capital as a policy rather than an outcome. Deciding who to lend "
                 "to, collecting without losing the customer, how much stock is the right "
                 "amount, supplier terms as your largest source of funding, what money "
                 "actually costs, the banking relationship, and the order of moves when "
                 "cash is tight."),
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
