#!/usr/bin/env python3
"""Build the What the Numbers Are For module into academy_finance_data.json.

Track module 8, and the last written — deliberately. Framing is easier once you
know what you are framing, so this module can point at the seven that precede it
rather than promise them.

It is the only module in the track that is not primarily technique. It covers
who accounts are for, what accounting genuinely cannot tell you, the three
statements as one picture, what good financial information looks like, the
governance questions, working with a finance team, the pressure to make a
number, and what to do on Monday.

Checks scenario-first, exam questions computational or definitional.

Run from the app package directory:  python3 build_finance_m9.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "purpose"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Who the accounts are for", 10, """<p>Financial statements look like neutral descriptions of a business. They are not. They are documents prepared for particular readers under particular rules, and knowing which reader a set of accounts was written for explains most of what is confusing about it.</p>

<p><b>The readers, and what each wants.</b></p>

<p><b>Owners</b> want to know what they made and what their stake is worth. <b>Lenders</b> want to know whether the debt can be serviced and what they could recover if it cannot — which is why they read cash and security before profit. <b>The tax authority</b> wants taxable profit computed under tax rules, which differ from accounting rules on purpose. <b>Suppliers</b> extending credit want to know whether they will be paid. <b>Managers</b> want to know what to do next week.</p>

<p>Those wants conflict. A number that satisfies one reader will disappoint another, and no single set of statements serves them all equally.</p>

<p><b>Which is why most businesses have two sets of numbers, entirely legitimately.</b> <i>Statutory accounts</i> are prepared once a year to a prescribed format, audited or reviewed, filed, and designed for outsiders. <i>Management accounts</i> are prepared monthly, in whatever format is useful, unaudited, and designed for you.</p>

<p>They will not agree exactly, and that is correct rather than suspicious. Statutory accounts follow rules on revenue recognition, provisioning and disclosure that a monthly management pack does not need. If somebody asks why the audited profit differs from the sum of your twelve management reports, the answer is usually year-end adjustments — provisions revisited, accruals trued up, judgements finalised — and it deserves a plain explanation rather than defensiveness.</p>

<p><b>Tax accounts are a third thing again.</b> Taxable profit is computed under the tax law: some accounting costs are not deductible, capital allowances replace depreciation on a different schedule, and timing differs. A business paying tax on a figure that does not match its accounting profit is not being cheated; it is being taxed under rules written for a different purpose.</p>

<p><b>Why this matters to a manager.</b> Because it tells you which document to reach for and how much weight to give it. Judging monthly performance from statutory accounts means working with information up to fifteen months old by the time it is filed. Assessing a customer's creditworthiness from statutory accounts means reading a document prepared to satisfy a filing requirement, at a date they chose, possibly a year ago — useful, and not the same as knowing how they are trading today.</p>

<p><b>And the practical question worth asking of any set of numbers you are handed.</b> Who prepared this, for whom, and under what rules? A management pack from your own finance team, a customer's audited accounts, and a supplier's credit application are three different kinds of evidence, and treating them as equally reliable descriptions of reality is the commonest mistake made by people who have just learned to read them.</p>

<blockquote>IMPLEMENTATION TIP: When you receive any financial statement from outside your business, look first at the date it covers and the date it was signed. The gap between those two, plus the gap to today, tells you how much of what you are reading is history rather than news.</blockquote>

<p><b>And one caution about the audited label.</b> An audit is an opinion that the statements are free from material misstatement under a set of standards. It is not a certificate of health, it does not mean the business is solvent today, and it does not mean the auditor examined every transaction. Clean audit opinions have preceded failures often enough that treating one as reassurance about the future is a misreading of what was actually said.</p>""",
 [C("Your audited profit differs from the sum of twelve monthly management reports. This is:",
    ["Evidence of an error", "Normally correct — year-end adjustments true up provisions and judgements",
     "A sign of manipulation", "Impossible if the ledger is accurate"], 1,
    "The two documents are prepared for different readers under different rules."),
  C("A customer sends you audited accounts to support a credit request. The main limitation is:",
    ["They may be unaudited in substance", "They describe a date they chose, possibly a year ago",
     "They exclude cash", "They use tax rules"], 1,
    "Useful evidence, and not the same as knowing how they are trading today."),
  C("Tax paid differs from the tax charge in the accounts because:",
    ["Somebody made an error", "Taxable profit is computed under rules written for a different purpose",
     "Payments are made in arrears", "Depreciation was miscalculated"], 1,
    "Some costs are not deductible and capital allowances replace depreciation on a different schedule.")]),

("What accounting cannot tell you", 10, """<p>Seven modules have argued that financial statements repay careful reading. This chapter argues the boundary: there are things a manager needs to know that no set of accounts will ever contain, and mistaking silence for absence is how businesses walk into trouble with clean numbers.</p>

<p><b>Accounting records what can be measured in money and owned.</b> That excludes a great deal that determines whether a business survives.</p>

<p><b>Your people.</b> A trained, experienced, loyal team appears in the accounts only as a cost. The business that has spent three years building capability and the one that has churned through staff show identical salary lines. Losing your best three people is a catastrophic event that no statement records.</p>

<p><b>Your customer relationships.</b> Unless bought, they are worth nothing on the balance sheet. A business with two hundred loyal customers and one wholly dependent on a single account that could leave show the same equity.</p>

<p><b>Your reputation, your systems, your processes, your brand.</b> All built at cost, none carried as assets. So a business can consume all four to make a good year — cutting training, deferring maintenance, delaying supplier payments, pushing staff harder — and report an excellent result while becoming materially weaker. <b>The accounts will applaud it.</b></p>

<p><b>Accounting is also historical.</b> It tells you what happened, with a delay. A monthly pack arriving on the fifteenth describes a period that ended two weeks ago and began six. By the time you act, the cause is old. This is why the forward-looking instruments in this track — the thirteen-week cash forecast, the reforecast, the pipeline — matter as much as the backward-looking ones.</p>

<p><b>And it is denominated in a currency that moves.</b> Comparing this year's revenue to last year's, in an economy with meaningful inflation, compares two different naira. Growth of 18% when prices rose 22% is a contraction reported as an expansion, and nothing in the statements says so.</p>

<p><b>What to do about all of this.</b> Not to distrust the accounts — they remain the most reliable systematic information you have. Rather to hold, alongside them, a short list of the things that matter and are not measured: your key people, your customer concentration, the age and condition of your assets, your service levels, your standing with suppliers. Review that list with the same seriousness as the numbers, because it is where the next problem is forming while the numbers look fine.</p>

<blockquote>WATCH-OUT: The most dangerous period in a business is often the one where results are good and the unmeasured things are deteriorating — deferred maintenance, stretched suppliers, exhausted staff, an ageing customer base. Every one of those improves this year's numbers and none of them appears anywhere.</blockquote>

<p><b>A related blind spot: what the business decided not to do.</b> The opportunity cost from module 4 applies at the level of the whole business. An order declined because capacity was short, a market entered a year later than a competitor, a hire deferred — none of these appears anywhere, and collectively they can matter more than anything that does. The accounts record what happened. They are entirely silent on what was available and forgone.</p>""",
 [C("A manager cuts training, defers maintenance and stretches suppliers to deliver a strong year. The accounts will:",
    ["Show the deterioration", "Applaud it — none of what was consumed is measured",
     "Show it in the notes", "Reduce the asset values"], 1,
    "All four were built at cost and none is carried as an asset."),
  C("Revenue grew 18% while prices rose 22%. The statements report:",
    ["A contraction", "An expansion, though the business shrank in real terms",
     "No change", "An inflation adjustment"], 1,
    "The accounts are denominated in a currency that moves, and nothing in them says so."),
  C("Two businesses have identical salary lines; one has a trained loyal team and one has churned staff for three years. The accounts show:",
    ["The difference in a note", "Nothing distinguishing them",
     "Lower profit for the churning business", "A provision for turnover"], 1,
    "Losing your best three people is a catastrophic event that no statement records.")]),

("The three statements as one picture", 10, """<p>Modules 1 to 3 taught the statements separately, which is how they must be learned and not how they should be read. Each answers a different question, and each is misleading alone.</p>

<p><b>The three questions.</b> The profit and loss asks <i>how did the period go?</i> The balance sheet asks <i>what are we standing on?</i> The cash flow statement asks <i>where did the money actually move?</i></p>

<p><b>How they connect, in three links worth knowing by heart.</b></p>

<p>Profit from the P&L lands in the balance sheet as an increase in equity, less anything distributed. The cash movement in the cash flow statement equals the change in the balance sheet's cash line. And the working capital movements in the cash flow statement are the changes between two balance sheets. <b>They are three views of one set of events, not three reports.</b></p>

<p><b>Why reading one alone misleads, with the specific failure in each case.</b></p>

<p><i>P&L alone:</i> a profitable business quietly running out of money. Module 3's distributor reported ₦11,600,000 of profit while trading consumed ₦6,400,000 of cash, and the P&L said nothing.</p>

<p><i>Balance sheet alone:</i> a position with no explanation of how it arose. Stock is up ₦14,000,000 — because sales grew, or because buying went wrong, or because a line stopped selling? The statement cannot say.</p>

<p><i>Cash flow alone:</i> a business that looks healthy because it stopped investing, or sold assets, or drew a loan. Cash rose and the business weakened.</p>

<p><b>The combinations that mean something.</b> Profit rising with cash falling and the cash cycle lengthening is growth absorbing money — normal, and it requires funding somebody must arrange. Profit rising with equity falling means owners are extracting more than the business earns. Cash rising with operating cash negative means something outside trading is holding it up. Steady profit with ageing receivables and growing stock is the signature of a managed result rather than an earned one.</p>

<p>None of those four is visible in any single statement. All four are obvious across three.</p>

<p><b>The reading order that works.</b> Start with the P&L for the story of the period. Move to the balance sheet and ask what changed and where the money went. Then use the cash flow statement, or the reconciliation from module 3, to confirm it. Fifteen minutes, monthly, in that order — and you will know more about your business than most of the people managing it.</p>

<blockquote>IMPLEMENTATION TIP: Whenever somebody shows you a single statement and draws a conclusion from it, ask what the other two say. It is the cheapest analytical question available and it is right often enough to be worth asking every time.</blockquote>

<p><b>Where the three statements are usually kept apart, and why that is a design failure.</b> Most management packs lead with the P&L, put the balance sheet at the back if at all, and produce a cash flow statement only annually. So the statement that shows performance is prominent, the one that shows exposure is buried, and the one that shows survival is absent for eleven months of the year. If you change one thing about your own pack after this module, put a short cash summary and the key balance sheet movements on the same page as the profit.</p>""",
 [C("A manager presents a strong P&L as evidence the business is healthy. The right response is:",
    ["Accept it", "Ask what the balance sheet and cash flow say",
     "Ask for the audited version", "Check the tax charge"], 1,
    "A profitable business quietly running out of money looks exactly like this on one statement."),
  C("Cash rose this month while operating cash was negative. This means:",
    ["Trading improved", "Something outside trading held it up — borrowing, or asset sales",
     "Receivables were collected", "Stock was reduced"], 1,
    "Cash rising and the business weakening are entirely compatible."),
  C("Profit is rising while equity falls. The likeliest explanation is:",
    ["Depreciation is too high", "Owners are extracting more than the business earns",
     "Stock was written down", "Revenue was overstated"], 1,
    "Drawings never touch the P&L, so this is invisible on the statement most owners read.")]),

("What good financial information looks like", 10, """<p>Most managers receive a monthly pack and never ask whether it is any good. It is worth having a standard, because the difference between a useful pack and a useless one is not effort — it is design, and the useless version usually costs more to produce.</p>

<p><b>Timely beats precise.</b> A pack that is 95% right on the fifth of the month is worth more than one that is 100% right on the twenty-fifth. By the twenty-fifth the period is nearly two months gone and every decision it might have informed has been taken. Businesses routinely trade a week of relevance for a decimal place of accuracy, and the trade is almost always wrong.</p>

<p><b>Comparable, or it says nothing.</b> A number alone is not information. Against last year, against plan, against the same month last year in a seasonal business — a figure needs a reference point before it means anything, and adjacent months are usually the wrong reference.</p>

<p><b>Decomposed, not aggregated.</b> "Costs were ₦31,400,000" invites no action. Split by behaviour, by department, by controllability, it becomes a set of questions with owners. Aggregation is what makes a report safe to present and useless to act on.</p>

<p><b>Consistent.</b> If the format changes every quarter, nobody builds the habit of reading it and no trend is visible. A mediocre report used consistently beats an excellent one that keeps being redesigned.</p>

<p><b>Short.</b> A forty-page pack is read by nobody, including the person who prepared it. One page of the numbers that matter, with detail available behind it for anyone who asks, is read by everybody. The instinct to include everything is an instinct to avoid being asked for something — and it costs the readership entirely.</p>

<p><b>Carrying the non-financial.</b> The best packs put a handful of operational measures beside the money — service level, stockouts, staff turnover, complaint volume, days to bank. These are usually the leading indicators of the financial numbers, and separating them into a different report read by different people guarantees nobody connects the two.</p>

<p><b>And accompanied by commentary that says something.</b> "Revenue was below budget" is a restatement of the number. "Revenue was ₦4,200,000 below budget, of which ₦3,100,000 is the delayed opening of the second branch and the remainder is softer footfall in the last week; the branch opens on the 12th and we expect to recover half in September" is information. If the commentary in your pack could have been written without reading the numbers, it is decoration.</p>

<blockquote>IMPLEMENTATION TIP: Ask for your pack a week earlier and accept that it will be slightly less accurate. Almost every business can do this, almost none has been asked, and the extra week of relevance is worth more than the accuracy given up.</blockquote>

<p><b>One further test of a pack: does anything in it ever change what somebody does?</b> A report that is produced faithfully, circulated, filed, and never acted upon is a cost with no return — and there are more of those in business than anybody admits. If you cannot name a decision your monthly pack has influenced in the last quarter, either the pack is wrong or the reading of it is, and both are worth fixing before adding anything to it.</p>""",
 [C("Your monthly pack is complete and accurate but arrives on the 25th. The best change is:",
    ["Add more detail", "Ask for it a week earlier and accept slightly less accuracy",
     "Have it audited", "Extend the commentary"], 1,
    "By the 25th the period is nearly two months gone and the decisions have been taken."),
  C("The commentary in a pack reads 'costs were higher than budget'. This is:",
    ["Adequate reporting", "A restatement of the number rather than information",
     "Appropriately concise", "A variance explanation"], 1,
    "If it could have been written without reading the numbers, it is decoration."),
  C("A forty-page monthly pack is most likely:",
    ["Thorough", "Read by nobody, including its preparer",
     "Required for governance", "Better than one page"], 1,
    "One page with detail available behind it is read by everybody.")]),

("The questions a director must ask", 10, """<p>Whether you sit on a board, run a subsidiary, or simply carry responsibility for a unit, there is a small set of questions that constitute financial oversight. They are not technical, and asking them consistently matters more than answering any of them cleverly.</p>

<p><b>1. Can we pay what falls due in the next ninety days?</b> Not "are we profitable". The thirteen-week cash forecast answers this, and it is the first question because it is the only one whose wrong answer stops the business.</p>

<p><b>2. Is our reported performance being earned or managed?</b> Module 1's judgement lines. Are estimates stable? Do provisions move with the underlying, or with the result? Is the balance sheet deteriorating while profit holds?</p>

<p><b>3. What is our largest single exposure?</b> One customer, one supplier, one product, one facility, one person. Concentration is the risk that arrives without warning, and it is almost never on a standard report.</p>

<p><b>4. Are the controls real?</b> Not documented — real. Is somebody independent reconciling the cash? Is anybody enforcing credit limits? Are variances investigated or filed? A control that exists on paper and not in practice is worse than none, because it produces confidence without protection.</p>

<p><b>5. Are we consuming what we are not measuring?</b> Deferred maintenance, exhausted staff, stretched suppliers, an ageing asset base. Chapter two's list, reviewed with the same seriousness as the numbers.</p>

<p><b>6. What would have to go wrong for this to fail?</b> Asked while things are going well, when it is a cheap question. Asked when things are going badly, it is no longer a question but a description.</p>

<p><b>On the value of asking the same questions repeatedly.</b> The point is not novelty. Asking the same six every quarter creates an expectation that they will be asked, and an organisation that expects a question prepares an answer — which means somebody has looked. Half the value of oversight is produced before the meeting happens.</p>

<p><b>And the harder discipline: acting on an answer you do not like.</b> Governance fails far more often through comfortable acceptance than through failure to ask. The question that matters is the second one — "you said the same thing last quarter; what changed?" — and it is the one people avoid because it makes the meeting uncomfortable and the alternative merely expensive.</p>

<blockquote>WATCH-OUT: Be most careful when everything is reported as fine for several periods running. Real businesses generate problems continuously. A report that never contains bad news is not describing a business without problems; it is describing a reporting process that has stopped carrying them upward.</blockquote>

<p><b>What to do when you cannot get an answer.</b> Occasionally a question is met with complexity rather than an answer — a long technical explanation that leaves you no wiser. That is worth noticing rather than accepting. A person who understands their numbers can explain them simply to somebody who does not, and the inability to do so usually means either the explainer does not understand it either, or does not wish to. Both are findings. Ask again, in writing, and ask for the answer in plain terms.</p>""",
 [C("A unit reports everything as fine for four consecutive quarters. This should prompt:",
    ["Confidence in management", "A concern that the reporting process has stopped carrying problems upward",
     "A reduction in oversight", "An increase in targets"], 1,
    "Real businesses generate problems continuously."),
  C("A control is fully documented but nobody independent performs the reconciliation. This is:",
    ["Adequate for audit", "Worse than no control, because it produces confidence without protection",
     "A minor deficiency", "Acceptable if the person is trusted"], 1,
    "The question is whether controls are real, not whether they are written down."),
  C("The most valuable follow-up when a manager repeats last quarter's answer is:",
    ["Accept it and move on", "'You said the same thing last quarter — what changed?'",
     "Request more detail", "Escalate to the board"], 1,
    "Governance fails through comfortable acceptance far more often than through failure to ask.")]),

("Working with your finance team", 10, """<p>Most operating managers have a difficult relationship with finance, and most of the difficulty is structural rather than personal. It is worth understanding, because a good working relationship with your finance team is the highest-return professional relationship available to an operating manager.</p>

<p><b>Why the friction exists.</b> Finance is accountable for accuracy and for control; operations is accountable for delivery and speed. Those pull against each other honestly. Finance says no because saying yes without evidence is precisely what they are there to prevent. Operations pushes because the customer is waiting. Neither is the obstacle the other believes them to be.</p>

<p><b>What finance actually needs from you, and rarely gets.</b> Advance notice rather than emergencies. Accurate coding at source, because a miscoded invoice becomes a variance somebody spends an hour explaining. Realistic forecasts rather than optimistic ones — a manager whose forecasts are consistently achievable becomes trusted, and trust converts directly into faster answers. And a decision when they ask for one, rather than silence that leaves an item unresolved at month end.</p>

<p><b>What you should ask for, and are entitled to.</b> Your numbers in a format you can use rather than the format the system produces. The assumptions behind anything you are held to. Explanation rather than defence when something surprises you. And the answer to "what would I have to show you to get a yes?" — which converts a refusal into a specification, and is the single most useful sentence in this chapter.</p>

<p><b>The translation problem, and who should solve it.</b> Finance speaks in accruals, absorption and variances; operations speaks in deliveries, stockouts and shifts. Most miscommunication is vocabulary rather than disagreement. Having read seven modules of this track, you are now the person better placed to bridge it — which is an advantage, and slightly a responsibility.</p>

<p><b>Where to be genuinely firm.</b> When a number does not match what you know happened, say so and keep saying so. Finance is working from what was recorded, and if what was recorded is wrong, they cannot know unless somebody who was there tells them. Managers who accept numbers they believe are wrong, because arguing is tiring, allow errors to become the history of the business.</p>

<p><b>And the thing worth doing once.</b> Spend a day with whoever prepares your numbers, watching how they are built. You will find out where the estimates are, which figures are solid and which are approximations, and which of your own behaviours make their job harder. It costs a day and it changes every subsequent conversation.</p>

<p><b>And what to offer in return.</b> Finance teams are rarely told what happened operationally, so they explain variances they do not understand and are then blamed for the explanation. Ten minutes at the start of each month telling whoever prepares your numbers what actually happened — the machine that failed, the customer who left, the promotion that ran late — improves the commentary in your own pack more than any amount of chasing. It is the cheapest quality improvement available and almost nobody does it.</p>

<blockquote>IMPLEMENTATION TIP: The most useful question you can ask finance is "what would I have to show you to get a yes?" It converts a refusal into a specification, and in most cases the specification is something you can produce in an afternoon.</blockquote>""",
 [C("Finance refuses a request. The most productive response is:",
    ["Escalate above them", "Ask what you would have to show them to get a yes",
     "Proceed and inform them", "Request a written justification"], 1,
    "It converts a refusal into a specification, usually one you can meet in an afternoon."),
  C("A figure in your pack does not match what you know happened on the ground. You should:",
    ["Accept it — the ledger is authoritative", "Say so and keep saying so until it is resolved",
     "Adjust for it in your own records", "Raise it at year end"], 1,
    "Finance works from what was recorded, and cannot know it is wrong unless somebody who was there says so."),
  C("A manager whose forecasts are consistently achievable rather than optimistic gains:",
    ["A lower target", "Trust, which converts into faster answers",
     "Less scrutiny of costs", "A larger budget"], 1,
    "Predictability is worth more to finance than ambition.")]),

("Judgement, and the pressure to make a number", 10, """<p>Every module in this track has touched a line that requires judgement: a provision, a useful life, an accrual, a cut-off, a write-off. This chapter is about the moment when judgement meets pressure, because that moment arrives in every business and rarely announces itself.</p>

<p><b>What it looks like in practice.</b> Nobody is asked to falsify anything. The month is short of target, and a set of individually defensible choices is available. The provision could be a little lower — the evidence is genuinely ambiguous. The write-off could wait a month — the customer might still pay. The invoice could be raised on the 30th rather than the 2nd — the goods are nearly ready. An asset's useful life could reasonably be six years rather than four.</p>

<p>Each is arguable. Each is within the range a reasonable person might choose. And taken together they close the gap.</p>

<p><b>The two tests that help, and they are practical rather than philosophical.</b></p>

<p><b>The direction test.</b> Are the judgements landing consistently on the side that improves the result? Any single estimate can go either way legitimately. When every ambiguity resolves favourably, month after month, that pattern is not the result of independent judgements — it is the result of a bias, and the bias is what somebody outside would see immediately.</p>

<p><b>The explanation test.</b> Could you explain this choice to somebody outside the business, calmly, and have them agree it was reasonable? Not "could you defend it" — defence is available for almost anything. Would a disinterested person, told the full circumstances, nod?</p>

<p><b>Why it matters commercially, quite apart from ethics.</b> A number improved by judgement is borrowed from a later period, and it must be repaid. The provision not taken this month is taken next month with interest, alongside next month's own problems. Businesses that manage results this way do not avoid the reckoning; they accumulate it, and it arrives all at once in a period that had done nothing to deserve it.</p>

<p><b>What to do if you are the one being leaned on.</b> Put the position in writing, factually and without accusation: this is the estimate, here is the basis, here is the range, here is what I recommend. A written record changes the conversation, and it protects everybody including the person applying the pressure — who is usually under pressure themselves and has not thought past this month.</p>

<p><b>And the thing worth saying plainly.</b> The pressure to make a number is normal and it is not, in itself, wrongdoing. What matters is whether the business can distinguish between a difficult judgement made honestly and a comfortable one made to order — and whether anybody is willing to say which is which. Most accounting failures did not begin with dishonesty. They began with a small, defensible choice that nobody wrote down and everybody repeated.</p>

<p><b>The structural protection, which matters more than individual character.</b> Judgements are safest where they are made by somebody without a stake in the answer, documented with their basis, and reviewed by a second person. That is not a comment on anybody's integrity — it is the recognition that a person whose bonus depends on a result should not be the sole author of the estimate that determines it. Businesses that arrange this rarely have the problem; businesses that rely on individuals being strong under pressure eventually find one who is not, and it is usually not the person they expected.</p>

<blockquote>WATCH-OUT: The clearest early sign is a business where estimates are discussed only when the result is short. Provisions and useful lives that are revisited in a bad month and never in a good one are not being estimated — they are being used.</blockquote>""",
 [C("A month is short of target and several estimates could reasonably be adjusted favourably. The concern is:",
    ["Any single adjustment", "That the judgements all land on the side that improves the result",
     "That estimates exist at all", "The size of the gap"], 1,
    "Any one estimate can go either way legitimately; a consistent direction is a bias, not judgement."),
  C("Provisions and useful lives are revisited whenever the month is short, and never when it is strong. This means they are:",
    ["Being estimated carefully", "Being used rather than estimated",
     "Correctly conservative", "Under-reviewed"], 1,
    "It is the clearest early sign that judgement has become an instrument."),
  C("You are asked to adopt an estimate you think is too favourable. The most useful step is:",
    ["Refuse verbally and move on", "Put the estimate, basis, range and your recommendation in writing",
     "Escalate immediately to the board", "Adopt it and note it later"], 1,
    "A written record changes the conversation and protects everybody, including the person applying the pressure.")]),

("Being wrong well", 10, """<p>Everything in this track produces estimates, and estimates are wrong. The question that separates businesses is not accuracy but what happens next — whether being wrong produces learning, blame, or nothing at all.</p>

<p><b>Most organisations produce nothing at all.</b> The budget is missed, the miss is explained, the explanation is accepted, and no record is kept of what was predicted or why it was wrong. Next year the same forecasting method produces the same class of error, and nobody notices because nobody compared.</p>

<p><b>What a business that learns actually does.</b> It keeps the original prediction and compares. Not to allocate blame — to find out which of its beliefs are unreliable. There is a large difference between "we missed by ₦8,000,000" and "we assumed the second branch would open in March and it opened in July, which is ₦6,000,000 of it; we have now made that assumption three times and been late every time."</p>

<p>The second version is worth something. It changes how the next plan is built.</p>

<p><b>The three questions after any material miss.</b> Which assumption was wrong? Was it unknowable at the time, or did somebody know and not say? And what will we do differently — not "try harder", but a change to the method.</p>

<p>That middle question is the uncomfortable one and the most valuable. Information that existed in the business and did not reach the decision is a communication failure, and it is fixable. Information nobody could have had is bad luck, and it is not.</p>

<p><b>Keep your own record.</b> Module 6 suggested this and it belongs here as the closing discipline. Write down what you expect — the number, the date, the assumption — before the outcome is known. Over two years it will tell you whether you are systematically optimistic, systematically cautious, or well calibrated, which almost nobody knows about themselves.</p>

<p>That is not a finance exercise. It is the only reliable way to improve judgement, and it is available to anybody willing to be specific in advance and honest afterwards.</p>

<p><b>And the cultural point, which sits above all of it.</b> Businesses that punish honest misses get optimistic forecasts and late bad news — because the rational response to punishment is concealment, and concealment is far more expensive than the miss ever was. Businesses that reward early honest reporting get information while it is still useful. Whichever of those you run, you are running one of them, and the incentives will decide which regardless of what anybody says about wanting candour.</p>

<blockquote>IMPLEMENTATION TIP: After the next material variance in your area, write three sentences: which assumption was wrong, whether it was knowable, and what changes in the method. Keep them. Ten of those over two years is a genuine education, and no training course produces the equivalent.</blockquote>

<p><b>A note on how to hold the record.</b> Keep it private and keep it honest. The moment a personal calibration log becomes something the business reads, it stops being a learning instrument and becomes a performance document, and the predictions in it will start to be written for the reader rather than for the truth. Its whole value depends on nobody needing to be impressed by it.</p>""",
 [C("A business explains and accepts every budget miss, keeping no record of what was assumed. The consequence is:",
    ["Efficient reporting", "The same class of error recurs and nobody notices, because nobody compared",
     "Improved forecasting", "Reduced blame"], 1,
    "The learning depends entirely on keeping the original prediction and comparing."),
  C("Which question after a miss is most uncomfortable and most valuable?",
    ["Which assumption was wrong", "Was it knowable at the time, or did somebody know and not say",
     "How large was the variance", "Who was responsible"], 1,
    "Information that existed and did not reach the decision is a fixable communication failure."),
  C("A business that punishes honest misses will predictably get:",
    ["More accurate forecasts", "Optimistic forecasts and late bad news",
     "Better cost control", "Earlier escalation"], 1,
    "Concealment is the rational response to punishment, and it costs far more than the miss.")]),

("What to do on Monday", 10, """<p>Eight modules, and the risk with all of it is that it stays interesting and never becomes habitual. This chapter is the shortest useful conversion of the track into practice.</p>

<p><b>This week.</b></p>

<p>Work out what one day of receivables is worth in your business — annual revenue divided by 365. Every collection conversation from then on has a price attached.</p>

<p>Find out your real cost of money, including fees and required balances. Without it you cannot price terms, size a discount, or judge a bulk buy.</p>

<p>Ask for your management pack a week earlier, accepting slightly less accuracy.</p>

<p><b>This month.</b></p>

<p>Build a thirteen-week cash forecast for your own unit, weekly, on customers' actual payment behaviour rather than their terms. Update it weekly and compare against what happened.</p>

<p>Work the reconciliation from profit to operating cash once, by hand, on your own numbers. It takes twenty minutes and it converts "I don't know why we're short" into three balance sheet lines with owners.</p>

<p>Write down your four working capital policy numbers, even roughly, and find out where buying, sales and finance disagree.</p>

<p><b>This quarter.</b></p>

<p>Know the contribution percentage of your top ten lines and check where your shelf space, promotions and sales emphasis actually go.</p>

<p>Split your three largest controllable costs into fixed and variable elements, so every future volume conversation is arithmetic rather than opinion.</p>

<p>Read the P&L, balance sheet and cash flow together, in that order, and write one sentence on where the money went.</p>

<p><b>Permanently.</b></p>

<p>The six weekly cash questions. The six questions about any P&L. And the habit underneath the whole track: before reaching for a number, say what decision it is for — because almost every expensive mistake in these eight modules was a correct calculation answering the wrong question.</p>

<p><b>What you should now be able to do.</b> Open your own management accounts and say what happened, why, and what you intend to do about it, without waiting for anybody to interpret them for you. That was the promise at the start. If you can do it in fifteen minutes a month, the track has done its work.</p>

<p><b>And a closing thought about what the numbers are for.</b> They are not a scorecard, and they are not a compliance exercise. They are the only systematic memory a business has — the accumulated record of what it did and what happened as a result. A manager who can read that record makes better decisions than one who cannot, not because the numbers are wise, but because they are the only honest account of whether the last decision worked.</p>

<blockquote>IMPLEMENTATION TIP: Pick two items from this chapter, not ten. Do them until they are habits, then come back for two more. A manager who genuinely does the weekly cash questions and knows their contribution percentages is ahead of most of the people they will ever negotiate with.</blockquote>

<p><b>One last word on what this track deliberately did not teach.</b> You cannot prepare accounts, you cannot audit them, and you do not know the standards. That was the design: read before prepare, because you will be handed accounts and never asked to draft them. If any part of this makes you want to go further — into a professional qualification, or into the standards themselves — that is a good instinct and a different course. What you have is enough to be a competent, sceptical, useful reader of your own business, which is what the job actually requires.</p>""",
 [C("Of everything in the track, the two habits worth starting with are:",
    ["Reading the annual accounts and the tax computation", "The weekly cash questions and knowing your contribution percentages",
     "Variance analysis and absorption costing", "Break-even and capital appraisal"], 1,
    "Pick two, make them habits, then come back for two more."),
  C("Almost every expensive mistake in this track came from:",
    ["Arithmetic errors", "A correct calculation answering the wrong question",
     "Out-of-date data", "Poor reporting formats"], 1,
    "Which is why the habit is to name the decision before reaching for the number."),
  C("The track's stated promise is that you can:",
    ["Prepare a set of statutory accounts", "Open your own management accounts and say what happened, why, and what you intend to do",
     "Replace your finance team", "Pass a professional examination"], 1,
    "Fifteen minutes a month, without waiting for anybody to interpret them for you.")]),
]


QUESTIONS = [
 Q("Statutory accounts are prepared primarily for:", ["Operational decisions", "Outsiders, to a prescribed format", "Tax computation", "Weekly management"], 1,
   "Management accounts are the monthly instrument, in whatever format is useful.", "Ch1 §4", "Who accounts are for"),
 Q("Lenders read which part of a set of accounts first?", ["Revenue growth", "Cash and security", "Gross margin", "Equity"], 1,
   "They want to know whether debt can be serviced and what is recoverable if it cannot.", "Ch1 §2", "Who accounts are for"),
 Q("Audited profit differing from the sum of monthly management reports is:", ["Evidence of error", "Normal, from year-end adjustments to provisions and judgements", "A control weakness", "A tax matter"], 1,
   "The two are prepared for different readers under different rules.", "Ch1 §5", "Who accounts are for"),
 Q("Taxable profit differs from accounting profit because:", ["Errors in the ledger", "Tax law disallows some costs and replaces depreciation with capital allowances", "Timing of payments", "Auditor adjustments"], 1,
   "It is computed under rules written for a different purpose.", "Ch1 §6", "Who accounts are for"),
 Q("The first thing to check on any external financial statement is:", ["The auditor's name", "The date it covers and the date it was signed", "The profit figure", "The disclosure notes"], 1,
   "The gaps tell you how much is history rather than news.", "Ch1 §9", "Who accounts are for"),
 Q("A trained loyal team appears in the accounts as:", ["An intangible asset", "A cost only", "Goodwill", "A provision"], 1,
   "Two businesses with very different capability show identical salary lines.", "Ch2 §3", "Limits of accounting"),
 Q("Cutting training, deferring maintenance and stretching suppliers to make a year will:", ["Show as asset impairment", "Improve the reported result while the business weakens", "Trigger a provision", "Reduce reported profit"], 1,
   "None of what was consumed is measured anywhere.", "Ch2 §5", "Limits of accounting"),
 Q("Revenue growth of 18% with inflation at 22% is:", ["Real growth", "A contraction reported as an expansion", "Neutral", "An accounting error"], 1,
   "The accounts are denominated in a currency that moves.", "Ch2 §8", "Limits of accounting"),
 Q("A monthly pack arriving on the fifteenth describes a period that:", ["Is current", "Ended two weeks ago and began six", "Is forecast", "Covers the quarter"], 1,
   "Which is why the forward-looking instruments matter as much as the backward-looking ones.", "Ch2 §7", "Limits of accounting"),
 Q("The most dangerous period in a business is often when:", ["Losses are reported", "Results are good and the unmeasured things are deteriorating", "Cash is tight", "Growth is rapid"], 1,
   "Every one of those improves this year's numbers and none appears anywhere.", "Ch2 §10", "Limits of accounting"),
 Q("Profit from the P&L arrives on the balance sheet as:", ["An increase in cash", "An increase in equity, less distributions", "A reduction in liabilities", "An increase in assets generally"], 1,
   "One of the three links worth knowing by heart.", "Ch3 §3", "The three statements together"),
 Q("Working capital movements in the cash flow statement are:", ["Estimates", "The changes between two balance sheets", "P&L items", "Non-cash adjustments"], 1,
   "Three views of one set of events, not three reports.", "Ch3 §3", "The three statements together"),
 Q("Reading the balance sheet alone tells you the position but not:", ["What is owned", "How it arose", "What is owed", "The equity"], 1,
   "Stock up ₦14m — because sales grew, buying went wrong, or a line stopped selling?", "Ch3 §5", "The three statements together"),
 Q("Steady profit with ageing receivables and growing stock is the signature of:", ["Rapid growth", "A managed result rather than an earned one", "Seasonal trading", "Good cost control"], 1,
   "Invisible in any single statement and obvious across three.", "Ch3 §7", "The three statements together"),
 Q("The recommended reading order is:", ["Balance sheet, cash flow, P&L", "P&L, balance sheet, cash flow", "Cash flow, P&L, balance sheet", "Any order"], 1,
   "Story of the period, then what changed, then confirm where the money went.", "Ch3 §8", "The three statements together"),
 Q("A pack that is 95% right on the fifth versus 100% right on the twenty-fifth:", ["The later one is better", "The earlier one is worth more", "They are equivalent", "Depends on the audit"], 1,
   "By the twenty-fifth every decision it might have informed has been taken.", "Ch4 §2", "Good financial information"),
 Q("A number with no comparison is:", ["Sufficient", "Not information", "Best practice", "Adequate for trends"], 1,
   "Against last year, against plan, or against the same month in a seasonal business.", "Ch4 §3", "Good financial information"),
 Q("Aggregation in reporting makes a report:", ["Clearer", "Safe to present and useless to act on", "More accurate", "Shorter and better"], 1,
   "Decomposed by behaviour, department and controllability, it becomes questions with owners.", "Ch4 §4", "Good financial information"),
 Q("A mediocre report used consistently beats an excellent one that:", ["Is too long", "Keeps being redesigned", "Is late", "Excludes commentary"], 1,
   "If the format changes quarterly, nobody builds the habit and no trend is visible.", "Ch4 §5", "Good financial information"),
 Q("Operational measures beside the financial ones matter because they are usually:", ["Easier to collect", "Leading indicators of the financial numbers", "Required by governance", "More accurate"], 1,
   "Separating them into a different report guarantees nobody connects the two.", "Ch4 §7", "Good financial information"),
 Q("Commentary that could have been written without reading the numbers is:", ["Concise", "Decoration", "Standard practice", "Sufficient for the board"], 1,
   "Cause, amount, recurrence and action make it information.", "Ch4 §8", "Good financial information"),
 Q("The first governance question is:", ["Are we profitable", "Can we pay what falls due in ninety days", "Is the margin holding", "Is the audit clean"], 1,
   "It is the only one whose wrong answer stops the business.", "Ch5 §2", "Governance"),
 Q("Concentration risk is dangerous mainly because it:", ["Is expensive to reduce", "Arrives without warning and is rarely on a standard report", "Affects margin", "Requires disclosure"], 1,
   "One customer, one supplier, one product, one facility, one person.", "Ch5 §4", "Governance"),
 Q("A control that exists on paper but not in practice is:", ["Better than nothing", "Worse than none, because it produces confidence without protection", "Adequate for audit", "A minor issue"], 1,
   "The question is whether controls are real, not whether they are documented.", "Ch5 §5", "Governance"),
 Q("Asking the same six questions every quarter is valuable because:", ["It ensures consistency", "An organisation that expects a question prepares an answer, so somebody has looked", "It satisfies the auditor", "It saves time"], 1,
   "Half the value of oversight is produced before the meeting happens.", "Ch5 §8", "Governance"),
 Q("Governance most often fails through:", ["Failure to ask questions", "Comfortable acceptance of answers", "Insufficient technical skill", "Inadequate reporting"], 1,
   "The follow-up question is the one people avoid because it makes the meeting uncomfortable.", "Ch5 §9", "Governance"),
 Q("The friction between finance and operations is mainly:", ["Personal", "Structural — accuracy and control against delivery and speed", "A skills gap", "A reporting problem"], 1,
   "Neither is the obstacle the other believes them to be.", "Ch6 §2", "Working with finance"),
 Q("The most useful question to ask finance after a refusal is:", ["Who decided this", "What would I have to show you to get a yes", "Can we escalate", "What is the policy"], 1,
   "It converts a refusal into a specification.", "Ch6 §9", "Working with finance"),
 Q("A manager whose forecasts are consistently achievable gains:", ["A softer target", "Trust, and therefore faster answers", "Reduced scrutiny", "A larger allocation"], 1,
   "Predictability is worth more to finance than ambition.", "Ch6 §3", "Working with finance"),
 Q("Accepting a number you believe is wrong because arguing is tiring allows:", ["Efficient closing", "Errors to become the history of the business", "Finance to correct it later", "The audit to catch it"], 1,
   "Finance cannot know it is wrong unless somebody who was there says so.", "Ch6 §6", "Working with finance"),
 Q("Spending a day watching how your numbers are built tells you:", ["The software in use", "Where the estimates are and which figures are approximations", "The audit trail", "The chart of accounts"], 1,
   "And which of your own behaviours make their job harder.", "Ch6 §7", "Working with finance"),
 Q("Most accounting failures began with:", ["Deliberate falsification", "A small defensible choice nobody wrote down and everybody repeated", "System errors", "Auditor negligence"], 1,
   "Which is why the direction test matters more than any single judgement.", "Ch7 §9", "Judgement and ethics"),
 Q("The direction test asks whether:", ["Estimates are conservative", "Judgements consistently land on the side that improves the result", "Provisions are adequate", "Cut-off is correct"], 1,
   "Any single estimate can go either way; a consistent direction is a bias.", "Ch7 §4", "Judgement and ethics"),
 Q("The explanation test asks whether:", ["You could defend the choice", "A disinterested person told the full circumstances would agree it was reasonable", "The auditor would accept it", "It complies with the standard"], 1,
   "Defence is available for almost anything.", "Ch7 §5", "Judgement and ethics"),
 Q("A number improved by judgement is:", ["A permanent gain", "Borrowed from a later period and repaid with that period's own problems", "Neutral over time", "Recovered by growth"], 1,
   "Businesses accumulate the reckoning rather than avoiding it.", "Ch7 §6", "Judgement and ethics"),
 Q("Estimates discussed only when the result is short indicates they are:", ["Carefully reviewed", "Being used rather than estimated", "Conservative", "Immaterial"], 1,
   "The clearest early sign that judgement has become an instrument.", "Ch7 §10", "Judgement and ethics"),
 Q("Most organisations respond to a budget miss by:", ["Recording the assumption that failed", "Explaining it, accepting it, and keeping no record", "Changing the method", "Reforecasting"], 1,
   "So the same class of error recurs and nobody notices.", "Ch8 §2", "Learning from numbers"),
 Q("The most valuable question after a material miss is:", ["How large was it", "Was the information knowable at the time, or did somebody know and not say", "Who is responsible", "Can it be recovered"], 1,
   "Information that existed and did not reach the decision is fixable.", "Ch8 §5", "Learning from numbers"),
 Q("Recording your own predictions before outcomes are known tells you:", ["Whether the business is well run", "Whether you are systematically optimistic, cautious, or well calibrated", "Whether budgets are fair", "Whether forecasts are accurate"], 1,
   "Almost nobody knows this about themselves.", "Ch8 §6", "Learning from numbers"),
 Q("Businesses that punish honest misses reliably get:", ["Accuracy", "Optimistic forecasts and late bad news", "Tighter control", "Better margins"], 1,
   "Concealment is the rational response, and it costs more than the miss.", "Ch8 §8", "Learning from numbers"),
 Q("One day of receivables is calculated as:", ["Receivables divided by 365", "Annual revenue divided by 365", "Debtor days divided by revenue", "Receivables divided by debtor days"], 1,
   "Once you know it, every collection conversation has a price attached.", "Ch9 §2", "What to do next"),
 Q("The habit underneath the whole track is:", ["Checking the arithmetic", "Naming the decision before reaching for the number", "Reading the pack monthly", "Reconciling to the bank"], 1,
   "Almost every expensive mistake was a correct calculation answering the wrong question.", "Ch9 §8", "What to do next"),
 Q("The numbers are best understood as:", ["A scorecard", "The only systematic memory a business has", "A compliance requirement", "A control mechanism"], 1,
   "The only honest account of whether the last decision worked.", "Ch9 §10", "What to do next"),
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
    rebalance(QUESTIONS, "finance:purpose:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "finance:purpose:checks")

    mod = {
        "title": "What the Numbers Are For",
        "desc": ("The capstone. Who accounts are prepared for and why that shapes them, "
                 "what accounting cannot tell you, the three statements as one picture, "
                 "what good financial information looks like, the questions a director "
                 "must ask, working with your finance team, judgement under pressure, "
                 "learning from being wrong, and what to do on Monday."),
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
