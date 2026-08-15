#!/usr/bin/env python3
"""Build 'What a Branch Manager Is Actually For' into academy_retail_data.json.

Module 1 of Retail Leadership Essentials.

The design risk in this track is that leadership content is a commodity — every
training firm sells it, and a generic version competes with people who have been
doing it for twenty years. Three things keep this specific:

  - it is written for a branch manager in a multi-branch Nigerian retailer, not
    for managers in general
  - it connects to numbers and controls the business already has, from the
    finance, internal control and ZhiftPOS tracks, without repeating them
  - it MANAGES rather than audits or operates. The control track teaches an
    auditor to test a branch; the POS track teaches a cashier to run a till;
    this teaches the person between them to decide, prioritise and lead.

Running example is Okelewo Stores three years on — the retailer from the POS
track, now eleven branches — so the estate holds together and a manager reads
about a business rather than an abstraction. That is continuity, not a
dependency: nothing here requires the reader to have taken the POS track.

STANDS ALONE. Every term the module uses is explained where it is used. That is
not decoration: the Ikeja story is this module's climax and it turns on "margin
is down two points" being a loss, which is unreadable to somebody who has not
been told what margin is and what a point of it means. A reader without an
accounting background would have reached the punchline and missed it.

Run from the app package directory:  python3 build_retail_m1.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_job"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The job nobody defines", 11, """<p>Most branch managers are promoted from the floor, handed keys and a target, and left to work out the rest. It is the commonest career path in retail and it produces a predictable result: a person doing their old job harder, with more hours and more worry attached.</p>

<p><b>The distinction that changes everything, and it is not obvious from inside.</b> A supervisor makes sure today goes well. A manager makes sure next quarter goes well, using today as evidence. Both matter, and only one of them is the job you were promoted into.</p>

<p>The trap is that the supervisory work is visible, urgent and satisfying. A queue you cleared, a delivery you sorted, a customer you calmed — you can see the result within the hour. Managerial work is slow, invisible and easy to postpone: the staff conversation you did not have, the stock line you did not analyse, the process you meant to fix. Nobody notices its absence for months, and then everybody notices at once.</p>

<p><b>What you were actually given.</b> Not a bigger version of your old role. A small business to run — with its own profit and loss account (the P&L: what the branch sold, what that cost, and what was left), a stock position, a team, a customer base and a cash position. You did not choose the location, the range, the prices or most of the people — and you are still accountable for what the branch produces from them.</p>

<p><b>That gap between control and accountability is permanent</b>, and it is worth accepting early rather than resenting for two years. Every branch manager in every chain has it. The skill is being precise about which side of the line a problem sits on, and this module is largely about learning to be precise about that.</p>

<p><b>The three questions that define the job.</b></p>

<p><b>What is this branch producing?</b> Sales, margin, cash, stock health, customer return. Numbers you should know without asking.</p><p><i>Margin</i> is the one worth pausing on, because it recurs throughout this track. It is what is left of each naira of sales once the goods themselves are paid for: sell ₦100 of goods that cost you ₦70 and your margin is ₦30, or 30%. Sales tell you how much went through the till. Margin tells you how much of it the business kept, and the two move independently — which is the subject of chapter eight and of the module that follows this one.</p>

<p><b>What is it capable of producing?</b> Given its location, size, range and team — because a branch performing well against its own potential is a different situation from one performing well against the estate.</p>

<p><b>What is stopping it?</b> The honest answer, which is usually two or three specific things rather than a general shortage of effort.</p>

<p><b>Why the last one is where managers fail.</b> Asked what is holding a branch back, most managers answer with something they cannot change — footfall, competition, head office pricing, the rent. Those may all be true and none of them is a plan. The useful answer is the biggest thing you could actually move, and finding it is the work.</p>

<blockquote>IMPLEMENTATION TIP: Write down the three questions and answer them for your branch this week, in writing, without looking anything up. Then check your answers against the actual figures. The gap between what you believed and what is true is the most useful thing you will learn this month.</blockquote>

<p><b>One reassurance, because this chapter can read as criticism.</b> Nearly every branch manager in this market was promoted the same way and told the same nothing. If you recognise yourself in the supervisor description, that is not a failing on your part — it is the predictable result of a business that promoted its best floor person and assumed the rest would follow. The gap is in the preparation, not in you, and it closes quickly once somebody names it.</p>"""
, [
 C("A supervisor makes sure today goes well. A manager makes sure:",
   ["Today goes well too", "Next quarter goes well, using today as evidence",
    "The team is happy", "Head office is satisfied"], 1,
   "Both matter, and only one of them is the job you were promoted into."),
 C("Managerial work is easy to postpone because it is:",
   ["Difficult", "Slow, invisible, and unnoticed for months",
    "Unpopular with staff", "Not measured"], 1,
   "Then everybody notices its absence at once."),
 C("Asked what is holding the branch back, most managers name:",
   ["A specific process", "Something they cannot change — footfall, competition, pricing",
    "Their own team", "Stock availability"], 1,
   "Those may be true and none is a plan; the useful answer is the biggest thing you could actually move.")]),

("The five things only you can do", 11, """<p>A branch manager's day fills itself. What separates managers who move a branch from managers who survive one is knowing which work genuinely requires them, and protecting time for it.</p>

<p><b>Five things nobody else in the branch can do.</b></p>

<p><b>1. Decide what matters this month.</b> Everything cannot be a priority, and a team told everything matters will choose for themselves — usually whatever is most visible. Naming two or three things, out loud and repeatedly, is a manager's most under-used power.</p>

<p><b>2. Have the conversation nobody wants to have.</b> The consistently late cashier. The storekeeper whose counts never balance. The supervisor who has stopped caring. These are yours alone, and every week you delay makes the conversation harder and the standard lower for everybody watching.</p>

<p><b>3. Look at the numbers and decide what they mean.</b> Somebody else produces them. Only you can connect them to what you saw on the floor and conclude something.</p>

<p><b>4. Protect the standard.</b> What you walk past, you accept. A shelf gap you do not mention, a till left unlocked, a rude exchange you did not address — each becomes the new normal within a fortnight, because the team is reading you constantly.</p>

<p><b>5. Represent the branch upward, honestly.</b> Nobody at head office knows what your branch needs unless you say so, clearly, with evidence, at the time it can be acted on.</p>

<p><b>Everything else can, in principle, be done by somebody else.</b> Serving, counting, receiving, cleaning, ordering — a manager doing these is either training somebody, covering an absence, or avoiding the five.</p>

<p><b>The avoidance is real and it is understandable.</b> Serving customers is pleasant and you are good at it. The difficult conversation is unpleasant and you may not be. So the day fills with the pleasant work and the difficult item moves to tomorrow, week after week, and it is genuinely hard to see this happening from inside because you are working extremely hard throughout.</p>

<p><b>The test that catches it.</b> At the end of a week, ask which of the five you did. If the honest answer is that you served, covered and firefighted, you had a busy week and not a managerial one. One such week is nothing. A quarter of them is why a branch drifts while its manager exhausts themselves.</p>

<blockquote>WATCH-OUT: Being needed on the floor feels like being a good manager and is often the opposite. A branch that cannot run for two hours without you is not a compliment to your work — it is a description of something you have not yet built.</blockquote>

<p><b>How to protect the time, practically.</b> Not by working later. Block one hour, at the same point each week, when you are not on the floor and not available — and tell your team it exists and why, so that being unavailable is a known arrangement rather than you hiding in the office. Managers who try to find the time never find it; managers who take it out of the week in advance keep it about half the time, which is enough.</p>"""
, [
 C("Your week was spent serving, covering and firefighting. That week was:",
   ["Well managed", "Busy but not managerial",
    "Appropriately hands-on", "A necessary exception"], 1,
   "One such week is nothing; a quarter of them is why a branch drifts while its manager exhausts themselves."),
 C("A branch that cannot run for two hours without you indicates:",
   ["Your value to the team", "Something you have not yet built",
    "Correct delegation", "A staffing shortage"], 1,
   "Being needed on the floor feels like good management and is often the opposite."),
 C("A team told that everything is a priority will:",
   ["Work harder across the board", "Choose for themselves, usually whatever is most visible",
    "Ask for guidance", "Escalate the conflict"], 1,
   "Naming two or three things repeatedly is a manager's most under-used power.")]),

("What you are measured on, and what you actually control", 11, """<p>Most branch managers are measured on sales. Most branch managers control very little of what drives sales. Understanding that mismatch precisely is what lets you argue your case without sounding like you are making excuses.</p>

<p><b>Four levers you genuinely control.</b></p>

<p><b>Availability.</b> Whether the thing a customer came for is on the shelf. Ordering discipline, receiving accuracy, replenishment from the back, and shrinkage — all branch-level, all yours.</p>

<p><b>Conversion and basket.</b> How many people who walk in buy, and how much they buy. Service, layout, queue speed, staff knowledge, prompting.</p>

<p><b>Cost and loss.</b> Rota against trade, overtime, utilities, waste, shrinkage. Small individually, material together, and almost entirely local.</p>

<p><b>The team.</b> Who you hire, how they are trained, whether they stay. The slowest lever and the one that determines the other three.</p>

<p><b>Four things you do not control</b>, and it is worth being unembarrassed about them: footfall, pricing, the range, and the location. Naming them accurately is not excuse-making — it is the precondition for a useful conversation with the people who do control them.</p>

<p><b>The distinction that makes you credible upward.</b> "Sales are down because the market is difficult" is an excuse, whether or not it is true, because it invites no response. "Footfall is down 12% year on year, our conversion is up two points and basket is flat, so we are holding our share of a smaller market — and the two lines that lost us the most sales were out of stock for nine days each" is a report. Same situation, entirely different reception.</p>

<p>The second version requires you to know your numbers, which is module 2.</p>

<p><b>Where managers lose the argument.</b> By claiming control they do not have — promising a sales recovery they cannot deliver — or by disclaiming control they do have, treating shrinkage or availability as somebody else's problem. Both damage credibility, and the second is the more common.</p>

<p><b>The habit worth building now.</b> For any problem, say out loud which side of the line it sits on. Then act on the ones that are yours and report the ones that are not, with evidence, to somebody who can act. That is the whole of managing upward, and module 8 does the detail.</p>

<p><b>A caution about the four levers.</b> They are not equally available to every branch. A small store with three staff cannot flex a rota the way a large one can; a branch with one supplier route has less to say about availability. Work out which of the four is most open to you at your branch specifically, because a manager pushing hard on the lever their situation has closed will exhaust themselves for very little.</p>

<blockquote>IMPLEMENTATION TIP: List your branch's five biggest problems and mark each as yours or not yours. Most managers find the split is roughly even — and that they have been spending their energy on the half they cannot move.</blockquote>"""
, [
 C("'Sales are down because the market is difficult' fails as a report because it:",
   ["Is untrue", "Invites no response",
    "Blames head office", "Lacks a timeframe"], 1,
   "The same situation stated with footfall, conversion, basket and stockout days is a report rather than an excuse."),
 C("Which lever is slowest and determines the other three?",
   ["Availability", "The team", "Conversion", "Cost and loss"], 1,
   "Who you hire, how they are trained, and whether they stay."),
 C("The more common way managers lose credibility upward is by:",
   ["Claiming control they lack", "Disclaiming control they have, such as shrinkage or availability",
    "Reporting too often", "Asking for resources"], 1,
   "Both damage credibility; treating a local problem as somebody else's is the frequent one.")]),

("Authority, and where it stops", 11, """<p>A branch manager has real authority over a small area and none at all over most of what affects them. Being clear about the boundary saves an extraordinary amount of wasted effort.</p>

<p><b>What you can usually decide alone.</b> The rota. Who does what. How the floor is laid out within the standards you were given. Which local problems get attention first. How you spend your own time. Small discretionary spend. And every judgement about your own team's day-to-day performance.</p>

<p><b>What you can influence but not decide.</b> Range and pricing. Headcount. Refurbishment. Systems and policy. Promotions. These need a case made to somebody else, which means evidence, timing and persistence rather than a request.</p>

<p><b>What is simply not yours.</b> Group strategy, other branches, the terms of trade with suppliers, what the business chooses to invest in. Energy spent here is energy not spent on the first list.</p>

<p><b>The authority most managers under-use.</b> Not budget or headcount — <b>attention</b>. What you look at, ask about and follow up on determines what your team treats as important, and you can redirect it entirely without permission from anybody.</p>

<p>A manager who asks about shrinkage every week gets a team that thinks about shrinkage. One who asks only about sales gets a team that thinks only about sales, whatever the wall poster says. That is a genuine lever, it costs nothing, and most managers never think of it as authority at all.</p>

<p><b>The authority most managers over-use.</b> Deciding things their team could decide. Every decision you take that somebody else could have taken trains them to bring you the next one, and within a year you are the bottleneck for a branch of thirty people and cannot understand why you have no time.</p>

<p><b>Where the boundary is genuinely unclear</b>, ask once and in writing. Many branch managers operate for years unsure whether they may authorise something, and resolve it by either never doing it or quietly doing it and hoping. Both are worse than a two-line email that settles it permanently.</p>

<p><b>And the authority you inherit without being told.</b> Whatever your predecessor did, your team assumes you will do — the exceptions they were allowed, the standards that had slipped, the things nobody checked. You are not bound by any of it, but you will have to actively change what you want changed, and the first month is when that is cheapest. Change it later and it reads as a new rule; change it early and it is simply how you run the branch.</p>

<blockquote>WATCH-OUT: A manager who says yes to every decision brought to them is not being helpful. They are teaching a team not to think, and the cost arrives later as a branch that cannot function in their absence — including on the day they are promoted.</blockquote>"""
, [
 C("You want your team to take shrinkage seriously but have no budget and no new headcount. The lever available is:",
   ["A poster campaign", "Asking about it every week, because what you ask about is what they think about",
    "A stricter policy", "Escalation to head office"], 1,
   "It costs nothing, needs nobody's permission, and most managers never treat it as authority at all."),
 C("Taking a decision your team could have taken trains them to:",
   ["Trust your judgement", "Bring you the next one",
    "Work independently", "Escalate less"], 1,
   "Within a year you are the bottleneck for a branch of thirty and cannot understand why you have no time."),
 C("Where your authority over something is genuinely unclear, you should:",
   ["Avoid it entirely", "Ask once, in writing, and settle it permanently",
    "Do it and see", "Wait for a policy"], 1,
   "Never doing it and quietly doing it are both worse than a two-line email.")]),

("Reading a branch from the floor", 11, """<p>Before the numbers arrive, a branch tells you how it is doing. Learning to read it is a genuine skill and it is faster than any report — a manager who walks their floor properly knows most of what next week's figures will say.</p>

<p><b>What to look at, in the order it matters.</b></p>

<p><b>Gaps.</b> Empty facings on lines that should be there. A gap is a sale you did not make and a customer who may not come back for it. Count them on the lines that matter rather than everywhere.</p>

<p><b>The queue.</b> Not just its length — whether it is moving, whether anybody is doing anything about it, and whether people are leaving it. A customer who abandons a queue is invisible in every report you will ever read.</p>

<p><b>Where your staff's eyes are.</b> On customers, on each other, or on their phones. This tells you more about your team's condition than any conversation, and it is visible in ten seconds.</p>

<p><b>Cleanliness and order in the parts customers do not see.</b> The stockroom, the back office, the yard. Front-of-house standards are performed for visitors; the back is what standards actually are.</p>

<p><b>What customers do rather than what they buy.</b> Where they pause, what they pick up and put down, what they ask for and do not find, where they look lost. Twenty minutes standing still and watching is worth more than an hour of walking about.</p>

<p><b>The two walks worth doing deliberately.</b> One at your busiest hour, because that is when everything strains and the weaknesses show. One at your quietest, because that is when standards slip and habits form. Managers who only walk mid-morning see a branch that exists at no other time of day.</p>

<p><b>And the walk you have stopped doing.</b> After a year in a branch you stop seeing it. The gap has been there so long it is furniture; the sign has been crooked since you arrived. The fix is to walk it with somebody else — a manager from another branch, a new starter in their first week — and ask what they notice. New eyes find in ten minutes what familiar ones have stopped registering.</p>

<blockquote>IMPLEMENTATION TIP: Once a month, walk your branch with a colleague from another store and swap. Ask only one question of each other: what would you change first? It costs two hours, it is free, and it is the single most effective way to see your own branch again.</blockquote>

<p><b>What to do with what the walk tells you.</b> Write it down at the time, on the floor, rather than trusting that you will remember at your desk. Three or four specific things beats a general impression, and the specific ones can be assigned to somebody with a date attached. A walk that produces a feeling that the branch is a bit untidy changes nothing; one that produces four named items changes four things.</p>"""
, [
 C("Six people leave your queue on a Saturday afternoon. Next week's figures will show:",
   ["Six lost sales", "Nothing at all — an abandoned queue is invisible in every report",
    "A conversion dip you can trace", "A void pattern"], 1,
   "Which is why whether the queue is moving matters more than how long it is."),
 C("Your shop floor is immaculate and the stockroom is chaotic. What this tells you is:",
   ["The priorities are correct", "Front-of-house is being performed, and the back is your real standard",
    "The stockroom needs more space", "Staff are stretched"], 1,
   "The parts customers never see are the honest measure of what a branch actually keeps to."),
 C("After a year in a branch you stop seeing it. The remedy is to:",
   ["Walk it more often", "Walk it with somebody else and ask what they notice",
    "Use a checklist", "Review photographs"], 1,
   "New eyes find in ten minutes what familiar ones have stopped registering.")]),

("The trap of doing the work", 11, """<p>The most common failure in a first management role is not laziness or incompetence. It is a capable person doing too much themselves, for entirely good reasons, until the branch depends on it.</p>

<p><b>Why it happens, and none of the reasons is stupid.</b> You are faster. The standard matters and you are not sure they will meet it. Explaining takes longer than doing. The customer is waiting now. And, underneath, doing the work is comfortable and managing is not.</p>

<p><b>What it costs, in the order the costs arrive.</b></p>

<p><b>Your time first</b>, which was the resource that made you useful.</p>

<p><b>Then their development</b>, because somebody who is never allowed to do a thing badly never learns to do it well.</p>

<p><b>Then their motivation</b>, since being trusted with nothing is not a pleasant way to work, and the good ones leave first.</p>

<p><b>Then the branch's resilience</b>, because a store that works only when you are in it fails the week you are ill — and every week you are not there, which is more weeks than you think.</p>

<p><b>The delegation that actually works.</b> Not handing over tasks — handing over <i>outcomes</i>, with the standard stated and the method left alone. "Make sure the chilled section is full and rotated by nine every morning, and tell me if you cannot" is an outcome. "Fill the chilled section" is a task you will be checking forever.</p>

<p><b>And accepting the first attempts will be worse.</b> This is the part people cannot get past. The first three times somebody else does it, it will be slower and rougher than your version, and you will be tempted to take it back. Taking it back teaches them they were right to doubt themselves and teaches you that delegation does not work. The fourth attempt is usually fine.</p>

<p><b>What to keep.</b> Not everything delegates. Discipline, pay conversations, anything involving a person's standing, and the final call on money — these are yours and handing them down is not delegation but abdication. The rule is simple enough: <b>delegate the work, never the accountability.</b></p>

<blockquote>WATCH-OUT: The phrase to be suspicious of in your own head is "it is quicker if I just do it." It is quicker today, every time, and that is precisely why it is a trap — the cost is never visible on the day you pay it.</blockquote>

<p><b>Where to start, if this is your pattern.</b> Not with the most important thing you do. Pick something routine, visible and low-risk — the opening checks, the weekly order for one category, the rota draft — hand it over properly with the standard stated, and leave it alone for a month. The point of starting small is not caution about the task; it is that you need to prove to yourself that the branch survives, and one successful handover makes the next three far easier.</p>"""
, [
 C("You catch yourself thinking 'it is quicker if I just do it'. The reason that thought is dangerous is:",
   ["It is usually wrong", "It is correct today, every time, and the cost never shows on the day you pay it",
    "It demotivates the team", "It breaches the job description"], 1,
   "The costs arrive later, in order: your time, their development, their motivation, the branch's resilience."),
 C("Delegation that works hands over:",
   ["Tasks with instructions", "Outcomes, with the standard stated and the method left alone",
    "Authority to decide pay", "Responsibility for results"], 1,
   "'Full and rotated by nine, tell me if you cannot' is an outcome; 'fill the section' is a task you check forever."),
 C("Your best supervisor offers to handle a lateness conversation for you. You should:",
   ["Accept — it develops them", "Decline: anything affecting a person's standing stays with you",
    "Accept with a written brief", "Do it jointly"], 1,
   "Delegate the work, never the accountability.")]),

("Deciding what to do first", 11, """<p>A branch produces more problems than any manager can address. Most managers respond by working longer. The alternative is choosing deliberately, and choosing well is most of what separates branches that improve from branches that merely cope.</p>

<p><b>The two questions that rank almost anything.</b> <i>How much is this costing?</i> and <i>can I actually move it?</i> High cost and movable goes first. Low cost or immovable can wait however loudly it is complaining.</p>

<p>That sounds obvious and it is routinely violated, because attention follows noise rather than value. The loudest problem in a branch is rarely the most expensive one.</p>

<p><b>Put a number on it, even a rough one.</b> A line out of stock nine days a month, selling four a day at ₦1,200 with 30% margin, is costing about ₦13,000 of margin monthly at that branch. The customer complaint that took an hour of your week last month cost considerably less. Both feel urgent; only one is worth your quarter.</p>

<p>The arithmetic does not need to be precise. It needs to exist, because a rough number beats a strong feeling every time.</p>

<p><b>The three-thing rule.</b> Name three priorities for the month, write them where your team can see them, and repeat them until people are tired of hearing them. Not ten. Three is roughly what a team can hold, and a manager with ten priorities has none — the team simply picks whichever they prefer.</p>

<p><b>Distinguish fixing from firefighting.</b> Firefighting is dealing with the instance: the gap filled, the complaint settled, the shift covered. Fixing is dealing with the cause: why the gap keeps appearing, why that complaint recurs, why the rota keeps failing. Firefighting is unavoidable and it is not progress, and a manager who only firefights will do the same fire every month for a year.</p>

<p><b>The hour that pays for itself.</b> One hour a week, protected, spent on a cause rather than an instance. Not more — one hour, genuinely uninterrupted, on the biggest thing on your list. Over a quarter that is thirteen hours on causes, which is more than most branch managers spend in a year, and it is where the difference actually comes from.</p>

<blockquote>IMPLEMENTATION TIP: Write your three priorities on paper and keep them visible on your desk. When something new arrives, ask whether it is bigger than one of the three. If it is not, it waits — and if it is, something comes off the list rather than being added to it.</blockquote>

<p><b>Tell your manager what the three are.</b> Two things follow from doing it. Head office stops assuming you are working on whatever they last mentioned, and you gain a reason to decline the fourth thing that arrives — not a refusal, but a question about which of the three should come off. A manager with visible priorities is much harder to load arbitrarily than one whose list nobody has seen.</p>"""
, [
 C("A line out of stock nine days a month costs ₦13,000 of margin; a complaint cost an hour last month. You should work on:",
   ["The complaint — customers come first", "The stockout, because a rough number beats a strong feeling",
    "Both equally", "Whichever head office asks about"], 1,
   "Attention follows noise rather than value, and the loudest problem is rarely the most expensive."),
 C("A manager with ten priorities has:",
   ["Thorough coverage", "None — the team picks whichever they prefer",
    "A realistic workload", "Too little delegation"], 1,
   "Three is roughly what a team can hold, and a longer list simply hands the choice back to them."),
 C("Firefighting deals with the instance; fixing deals with the cause. A manager who only firefights will:",
   ["Keep the branch stable", "Do the same fire every month for a year",
    "Build resilience", "Develop the team"], 1,
   "One protected hour a week on a cause is thirteen hours a quarter, and it is where the difference comes from.")]),

("Okelewo Stores, three years on", 11, """<p>The retailer from the counter track has grown. Three branches became eleven across Ogun and Lagos, staff went from thirty to a hundred and forty, and the founder no longer knows every person by name. What worked at three branches has stopped working, and the reason is worth understanding because it is the standard path.</p>

<p><b>What changed, and it is not what people expect.</b> The systems held. Prices are central, counters are governed by profiles, shifts are counted, and the figures are trustworthy. The thing that broke was <b>management</b>: eleven branches need eleven people making local decisions well, and the business had promoted eleven good supervisors and given them keys.</p>

<p><b>Three managers, and the pattern in each is common enough to be worth naming.</b></p>

<p><b>Lalubu, the flagship.</b> The manager is the best cashier the business ever had and still serves at the busiest hour every day. Customers love her. Her branch has the highest sales in the group and the third-worst shrinkage, because the storeroom runs itself and nobody has looked at it in a year. She works fifty-five hours and cannot say why she is tired.</p>

<p><b>Sango, the second Abeokuta shop.</b> The manager delegates well and reads his figures. His branch is unremarkable on every measure and has the lowest staff turnover in the group. Head office regards him as steady rather than strong — and he is quietly the most valuable manager in the business, because his branch runs without him and he develops people other branches later take.</p>

<p><b>Ikeja.</b> The manager is ambitious, chases the sales target, and has run three promotions this quarter without asking what they cost. Sales are up nine per cent and margin is down two points — from 30% to 28%, meaning the branch keeps two kobo less of every naira it takes. On that branch's volume the extra sales earn less than the lost margin costs, so it is a loss. He does not know this, because he reads the sales report and not the margin one.</p>

<p><b>What the founder eventually noticed.</b> Not that any of the three was bad. That all three were doing what they had been rewarded for — serving, steadying and selling — and that nobody had ever told them the job was something else. The eleven managers had eleven private definitions of the role, and the business had never written one down.</p>

<p><b>The uncomfortable conclusion for a growing retailer.</b> Promoting your best floor staff is the right instinct and an incomplete plan. The skills that make somebody excellent on the floor — speed, presence, willingness to do it themselves — are precisely the ones that make a mediocre manager if nothing is added to them.</p>

<p><b>What Okelewo did about it.</b> Not a restructure. They wrote down what a branch manager is for — roughly the five things in chapter two — and they changed what they asked about in the monthly call, which had been sales and became sales, margin, shrinkage, availability and staff turnover. Within two quarters the Ikeja manager was reading his margin report, because it had become something he was asked about. That is the attention lever from chapter four, applied from above.</p>

<blockquote>IMPLEMENTATION TIP: Ask yourself which of the three you most resemble. Most managers recognise themselves in one within a sentence or two, and the recognition is more useful than any amount of general advice about leadership.</blockquote>"""
, [
 C("The Lalubu manager has the highest sales and third-worst shrinkage. The cause is:",
   ["Poor staff", "She serves at the busiest hour and nobody has looked at the storeroom in a year",
    "A bad location", "Weak systems"], 1,
   "She is doing what she was rewarded for, at fifty-five hours a week."),
 C("The Ikeja manager's sales are up nine per cent and margin down two points. He does not know because:",
   ["The report is late", "He reads the sales report and not the margin one",
    "Margin is head office's concern", "Promotions are centrally run"], 1,
   "On that branch's volume it is a loss, and it is invisible from the report he reads."),
 C("What broke as Okelewo grew from three branches to eleven was:",
   ["The systems", "Management — eleven people now make local decisions",
    "The pricing", "Stock control"], 1,
   "The systems held; the business had promoted eleven good supervisors and given them keys.")]),

("Review, and what this track covers", 11, """<p>Check yourself against each section before the assessment, then read what follows.</p>

<p><b>The job (Chapter 1).</b> A supervisor makes today go well; a manager makes next quarter go well using today as evidence. Three questions: what is this branch producing, what is it capable of, what is stopping it — and the third is answered with something you can move.</p>

<p><b>The five (Chapter 2).</b> Decide what matters, have the hard conversation, read the numbers and conclude something, protect the standard, represent the branch upward. Everything else can be done by somebody else. A busy week is not automatically a managerial one.</p>

<p><b>Control and accountability (Chapter 3).</b> You control availability, conversion and basket, cost and loss, and the team. You do not control footfall, pricing, range or location. Name which side a problem sits on, act on yours, report the rest with evidence.</p>

<p><b>Authority (Chapter 4).</b> Under-used: attention. Over-used: deciding what your team could decide. Where the boundary is unclear, ask once in writing.</p>

<p><b>The floor (Chapter 5).</b> Gaps, the queue moving, where your staff's eyes are, the parts customers do not see, and what customers do rather than buy. Walk at your busiest and quietest hours, and once a month with somebody else's eyes.</p>

<p><b>Delegation (Chapter 6).</b> Hand over outcomes with the standard stated. Accept the first three attempts will be worse. Delegate the work, never the accountability.</p>

<p><b>Priorities (Chapter 7).</b> How much is it costing, and can I move it. Three priorities, visible and repeated. One protected hour a week on a cause rather than an instance.</p>

<p><b>Okelewo (Chapter 8).</b> The systems held and management did not. Three managers, each doing what they were rewarded for, none told the job was something else.</p>

<p><b>What comes next.</b> Reading your branch's numbers and knowing which ones lie. Availability and the shelf. People — hiring, training, the difficult conversation, and why they leave. Loss, and what a manager does about it that an auditor cannot. Customers and your local market. Managing upward. And the manager's operating week, which pulls all of it into a rhythm you can actually keep.</p>

<blockquote>IMPLEMENTATION TIP: Before moving on, do the chapter one exercise if you have not: answer the three questions in writing, then check against the figures. Everything in the modules that follow assumes you know your own branch's numbers, and most managers discover they knew them less well than they thought.</blockquote>

<p><b>How to use this track if you are already in the job.</b> Do not wait until the end to change anything. Each module has one practice worth starting the week you read it — the three questions here, the numbers in module 2, the availability check in module 3. A manager who finishes the track having changed nothing has read a book; one who starts a single habit per module arrives at the end running a different branch.</p>"""
, [
 C("Which is NOT one of the five things only a branch manager can do?",
   ["Decide what matters this month", "Cover the till at the busiest hour",
    "Protect the standard", "Represent the branch upward"], 1,
   "Serving, counting, receiving and ordering can all in principle be done by somebody else."),
 C("The chapter one exercise asks you to answer the three questions and then:",
   ["Discuss them with your team", "Check your answers against the actual figures",
    "Send them to head office", "Set targets from them"], 1,
   "The gap between what you believed and what is true is the most useful thing you will learn this month."),
 C("What broke at Okelewo as it grew was management rather than systems, which suggests that promoting your best floor staff is:",
   ["A mistake", "The right instinct and an incomplete plan",
    "Better than hiring externally", "Only workable below ten branches"], 1,
   "The skills that make somebody excellent on the floor make a mediocre manager if nothing is added to them.")]),
]


QUESTIONS = [
 Q("The difference between a supervisor and a manager is that a manager:", ["Works longer hours", "Makes next quarter go well, using today as evidence", "Has more staff", "Reports to head office"], 1,
   "Both roles matter; only one is what a promotion into management asks for.", "Ch1 §2", "The job"),
 Q("Managerial work is postponed easily because it is:", ["Difficult", "Slow and invisible, unnoticed for months", "Unpopular", "Unmeasured"], 1,
   "Then everybody notices its absence at once.", "Ch1 §3", "The job"),
 Q("A branch manager was given:", ["A bigger version of their old role", "A small business to run", "A supervisory span", "A sales target"], 1,
   "With a P&L, a stock position, a team, a customer base and a cash position.", "Ch1 §4", "The job"),
 Q("The gap between what a branch manager controls and what they are accountable for is:", ["A sign of poor structure", "Permanent, and true of every branch manager in every chain", "Temporary", "Negotiable"], 1,
   "The skill is being precise about which side of the line a problem sits on.", "Ch1 §5", "The job"),
 Q("The third defining question — what is stopping this branch — should be answered with:", ["The honest constraint, whatever it is", "The biggest thing you could actually move", "Head office's view", "The team's view"], 1,
   "Naming something you cannot change may be true and is not a plan.", "Ch1 §8", "The job"),
 Q("Which is NOT one of the five things only a manager can do?", ["Have the hard conversation", "Receive a delivery", "Protect the standard", "Decide what matters"], 1,
   "Serving, counting, receiving and ordering can be done by somebody else.", "Ch2 §3", "The five things"),
 Q("A team told everything is a priority will:", ["Work harder", "Choose for themselves, usually the most visible thing", "Ask for ranking", "Slow down"], 1,
   "Naming two or three repeatedly is a manager's most under-used power.", "Ch2 §3", "The five things"),
 Q("'What you walk past, you accept' means an unaddressed lapse becomes:", ["A disciplinary matter", "The new normal within a fortnight", "A training need", "A one-off"], 1,
   "The team is reading you constantly.", "Ch2 §6", "The five things"),
 Q("A week spent serving, covering and firefighting was:", ["Well managed", "Busy but not managerial", "Necessary", "Efficient"], 1,
   "One is nothing; a quarter of them is why a branch drifts.", "Ch2 §9", "The five things"),
 Q("A branch that cannot run two hours without you is:", ["Well led", "Describing something you have not built", "Understaffed", "Highly dependent on service"], 1,
   "Being needed on the floor feels like good management and is often the opposite.", "Ch2 §10", "The five things"),
 Q("Which of these does a branch manager genuinely control?", ["Footfall", "Availability", "Pricing", "The range"], 1,
   "Ordering, receiving, replenishment and shrinkage are all local.", "Ch3 §2", "Control and accountability"),
 Q("The slowest lever, which determines the other three, is:", ["Cost and loss", "The team", "Conversion", "Availability"], 1,
   "Who you hire, how they are trained, whether they stay.", "Ch3 §5", "Control and accountability"),
 Q("'The market is difficult' fails as a report because it:", ["Is untrue", "Invites no response", "Sounds negative", "Lacks detail"], 1,
   "Footfall, conversion, basket and stockout days turn the same situation into a report.", "Ch3 §7", "Control and accountability"),
 Q("The more common credibility failure is:", ["Claiming control you lack", "Disclaiming control you have", "Over-reporting", "Asking for resources"], 1,
   "Treating shrinkage or availability as somebody else's problem.", "Ch3 §9", "Control and accountability"),
 Q("For any problem, the habit worth building is to:", ["Escalate promptly", "Say which side of the control line it sits on", "Log it", "Discuss it with the team"], 1,
   "Act on yours; report the rest with evidence to somebody who can act.", "Ch3 §10", "Control and accountability"),
 Q("The authority most branch managers under-use is:", ["Discretionary spend", "Attention", "The rota", "Hiring"], 1,
   "What you ask about weekly is what your team thinks about.", "Ch4 §5", "Authority"),
 Q("A manager who asks only about sales gets a team that:", ["Sells more", "Thinks only about sales, whatever the poster says", "Ignores targets", "Reports better"], 1,
   "It costs nothing to redirect and most managers never treat it as authority.", "Ch4 §6", "Authority"),
 Q("Taking a decision your team could take teaches them to:", ["Trust you", "Bring you the next one", "Decide faster", "Escalate less"], 1,
   "Within a year you are the bottleneck for a branch of thirty.", "Ch4 §7", "Authority"),
 Q("Where your authority is unclear you should:", ["Avoid the area", "Ask once, in writing", "Proceed carefully", "Await policy"], 1,
   "Never doing it and quietly doing it are both worse.", "Ch4 §8", "Authority"),
 Q("Which is NOT something a branch manager can usually decide alone?", ["The rota", "Headcount", "Floor layout within standards", "Which local problem comes first"], 1,
   "Headcount is influenced by making a case, not decided.", "Ch4 §3", "Authority"),
 Q("A customer who abandons your queue appears:", ["As a lost sale", "Nowhere in any report", "In conversion", "As a void"], 1,
   "Which is why whether the queue moves matters more than its length.", "Ch5 §4", "Reading the floor"),
 Q("Standards in the stockroom matter because front-of-house standards are:", ["More important", "Performed for visitors", "Easier to keep", "Head office's concern"], 1,
   "The parts customers never see are the honest measure.", "Ch5 §6", "Reading the floor"),
 Q("The two deliberate walks are at your busiest hour and:", ["Opening time", "Your quietest hour", "Closing time", "Mid-morning"], 1,
   "Busy shows the strain; quiet is when standards slip and habits form.", "Ch5 §8", "Reading the floor"),
 Q("After a year you stop seeing your own branch. The remedy is:", ["A checklist", "Walking it with somebody else's eyes", "More frequent walks", "Photographs"], 1,
   "New eyes find in ten minutes what familiar ones no longer register.", "Ch5 §9", "Reading the floor"),
 Q("Twenty minutes standing still and watching customers is worth more than:", ["A staff briefing", "An hour of walking about", "A sales report", "A stock count"], 1,
   "Where they pause, what they put down, what they ask for and do not find.", "Ch5 §7", "Reading the floor"),
 Q("'It is quicker if I just do it' is a trap because:", ["It is untrue", "It is true today every time, and the cost is invisible on the day", "It irritates staff", "It breaches policy"], 1,
   "The costs arrive later and in order.", "Ch6 §9", "Delegation"),
 Q("The costs of doing too much yourself arrive in which order?", ["Motivation, time, resilience, development", "Your time, their development, their motivation, the branch's resilience", "Resilience, time, motivation, development", "Development, resilience, time, motivation"], 1,
   "Your time was the resource that made you useful.", "Ch6 §4", "Delegation"),
 Q("Effective delegation hands over:", ["Tasks with instructions", "Outcomes with the standard stated", "Accountability", "Authority over pay"], 1,
   "'Full and rotated by nine, tell me if you cannot' is an outcome.", "Ch6 §6", "Delegation"),
 Q("The first three attempts by somebody else will be worse. Taking the task back teaches them:", ["The standard", "They were right to doubt themselves", "To try harder", "Nothing"], 1,
   "The fourth attempt is usually fine.", "Ch6 §7", "Delegation"),
 Q("Which must not be delegated?", ["Ordering", "Anything affecting a person's standing", "Replenishment", "Counting"], 1,
   "Delegate the work, never the accountability.", "Ch6 §8", "Delegation"),
 Q("The two questions that rank almost any problem are how much it costs and:", ["How urgent it is", "Whether you can move it", "Who reported it", "How long it takes"], 1,
   "High cost and movable goes first.", "Ch7 §2", "Priorities"),
 Q("Attention in a branch tends to follow:", ["Value", "Noise", "The rota", "Head office"], 1,
   "The loudest problem is rarely the most expensive one.", "Ch7 §3", "Priorities"),
 Q("A rough cost estimate is worth having because:", ["It satisfies head office", "A rough number beats a strong feeling", "It is required for approval", "It sets the budget"], 1,
   "The arithmetic does not need to be precise; it needs to exist.", "Ch7 §5", "Priorities"),
 Q("How many priorities should a manager name for the month?", ["One", "Three", "Five", "Ten"], 1,
   "Three is roughly what a team can hold; ten means none.", "Ch7 §6", "Priorities"),
 Q("A manager who only firefights will:", ["Keep things stable", "Do the same fire every month for a year", "Develop resilience", "Reduce workload"], 1,
   "Firefighting is unavoidable and it is not progress.", "Ch7 §7", "Priorities"),
 Q("One protected hour a week on causes amounts to how much over a quarter?", ["Four hours", "Thirteen hours", "Fifty hours", "One day"], 1,
   "More than most branch managers spend on causes in a year.", "Ch7 §8", "Priorities"),
 Q("At Okelewo, growth from three branches to eleven broke:", ["The systems", "Management", "Pricing", "Stock control"], 1,
   "The systems held; eleven good supervisors had been given keys.", "Ch8 §2", "Okelewo"),
 Q("The Lalubu manager has the highest sales and third-worst shrinkage because she:", ["Hires poorly", "Serves at the busiest hour while nobody looks at the storeroom", "Discounts heavily", "Has a weak team"], 1,
   "Doing what she was rewarded for, at fifty-five hours a week.", "Ch8 §4", "Okelewo"),
 Q("The Sango manager is regarded as steady and is quietly the most valuable because his branch:", ["Has the highest sales", "Runs without him, and he develops people", "Costs least to run", "Has no complaints"], 1,
   "Lowest staff turnover in the group and other branches later take his people.", "Ch8 §5", "Okelewo"),
 Q("The Ikeja manager's margin fell two points and he does not know because:", ["The report is late", "He reads sales and not margin", "Promotions are central", "Head office withholds it"], 1,
   "On that branch's volume, nine per cent more sales at two points less margin is a loss.", "Ch8 §6", "Okelewo"),
 Q("What the founder eventually noticed was that the three managers were:", ["Underperforming", "Doing what they had been rewarded for, never told the job was something else", "Poorly trained", "Wrongly selected"], 1,
   "Eleven managers held eleven private definitions of the role.", "Ch8 §7", "Okelewo"),
 Q("Promoting your best floor staff is:", ["A mistake", "The right instinct and an incomplete plan", "Preferable to external hiring", "Only workable in small chains"], 1,
   "Speed, presence and willingness to do it yourself make a mediocre manager if nothing is added.", "Ch8 §8", "Okelewo"),
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
    rebalance(QUESTIONS, "retail:the_job:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:the_job:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    for _t, _e, _h, ch in LESSONS:
        for c in ch:
            if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank:
                raise SystemExit("ABORT: check duplicates exam question: %s" % c["q"][:60])

    mod = {
        "title": "RL 1 — What a Branch Manager Is Actually For",
        "desc": ("The job nobody defines. The five things only you can do, what you control "
                 "against what you are measured on, the authority you under-use and the one "
                 "you over-use, reading a branch from its floor, why doing the work yourself "
                 "is the commonest first-management failure, and choosing what to fix first."),
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
    print("topics:", dict(collections.Counter(q["topic"] for q in QUESTIONS)))
    print("checks:", sum(len(l["checks"]) for l in mod["lessons"]))


if __name__ == "__main__":
    main()
