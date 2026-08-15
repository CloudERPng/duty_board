#!/usr/bin/env python3
"""Build 'Availability and the Shelf' into academy_retail_data.json.

Module 3 of Retail Leadership Essentials.

Module 2 measured availability — how to count it, how to price a gap, and the
four causes named briefly. This module takes each cause and says what to do
about it, which is a different job: measuring a loss and closing it are not the
same skill and most branches can do the first without the second.

STANDS ALONE. Every term is explained where it is used. No prior module of this
track and no other track is assumed.

Run from the app package directory:  python3 build_retail_m3.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "availability"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The sale that never happened", 11, """<p>Every other loss in a branch leaves a trace. Damaged stock can be counted, theft shows up in a difference, a discount appears on a receipt. A customer who came for something you did not have leaves nothing at all — they simply go, and no report you will ever read contains them.</p>

<p><b>What it actually costs, which is more than the line.</b> A customer looking for four things who cannot find one of them frequently abandons the trip and buys the whole basket elsewhere. Sometimes they buy the other three and are mildly annoyed. Occasionally they stop coming.</p>

<p>So the loss from one gap is somewhere between one item and a customer, and you cannot tell which from the till.</p>

<p><b>Put a number on one gap.</b> A line selling four a day at ₦1,200, where you keep 30 kobo of every naira, earns you about ₦1,440 a day. Out of stock for nine days in a month, that single line cost roughly ₦13,000 of earnings at your branch — and that is only the line itself, before whatever else those customers did not buy.</p>

<p>Twenty such lines and you are into six figures a month, from goods you would have sold and were entitled to sell.</p>

<p><b>Why this is the best problem a branch manager can work on.</b> It is large, it is almost entirely local, most of it needs no money to fix, and unlike costs there is no ceiling — a branch cannot cut its way past zero, but it can nearly always sell more of what it already stocks.</p>

<p><b>And why it stays unfixed.</b> Because nobody complains in a way that reaches you. The customer who leaves does not fill in a form. Your team sees a gap and, if nothing is in the back, has nothing to do about it and stops seeing it by the second week. The absence becomes furniture.</p>

<p><b>What this module does.</b> Module 2 covered measuring availability and pricing a gap. This one takes the four causes in turn — not ordered, ordered and not delivered, delivered and not on the shelf, on the shelf and unfindable — and works through what a branch manager actually does about each. They need entirely different fixes, and treating them as one problem called "availability" is why most branches never move it.</p>

<blockquote>WATCH-OUT: A gap that has been there for more than a fortnight has usually stopped being visible to everybody who works in the branch, including you. That is not carelessness — it is how attention works. It is also why the count has to be deliberate rather than left to noticing.</blockquote>

<p><b>One thing worth settling before the rest of the module.</b> Availability is not the same as having a lot of stock. A branch can hold three months of cover and still be out of the twenty lines that matter, because the money went into the wrong things. Everything here is about being available on what customers actually come for — which usually means holding less in total, not more, with the difference moved to lines that turn.</p>"""
, [
 C("A customer cannot find one of the four items on their list. The realistic range of loss is:",
   ["Exactly one item", "Somewhere between one item and the customer, and the till cannot tell you which",
    "One basket", "Nothing, if they buy the rest"], 1,
   "Some buy the other three, some abandon the trip, and occasionally somebody stops coming."),
 C("A line selling four a day at ₦1,200 keeping 30 kobo in the naira, out for nine days, costs about:",
   ["₦1,440", "₦13,000", "₦43,000", "₦4,300"], 1,
   "And that is the line alone, before whatever else those customers did not buy."),
 C("A gap that has been present for a fortnight is usually:",
   ["Noticed and tolerated", "No longer visible to anybody in the branch, including you",
    "Reported upward", "Filled from the back"], 1,
   "That is how attention works, and it is why the count must be deliberate rather than left to noticing.")]),

("Four causes, four different fixes", 11, """<p>A gap on a shelf looks the same whatever caused it. What put it there determines entirely what you do, and a manager who treats every gap as an ordering problem will fix perhaps a quarter of them.</p>

<p><b>Cause one: it was never ordered.</b> The order was too small, too late, or missed. Yours, and it is a discipline problem rather than a knowledge problem — the fix is a routine somebody owns and a review of what happened when it slipped.</p>

<p><b>Cause two: ordered and not delivered.</b> The supplier shorted you, missed the drop, or delivered something else. Not yours to fix and entirely yours to record — and recording it is what turns a complaint into a case somebody central can act on.</p>

<p><b>Cause three: delivered and not on the shelf.</b> It is in the back. This is usually the largest of the four and it is the one that most offends a manager who sees it clearly for the first time: goods the business has already paid for, sitting fifteen metres from a customer who wanted them.</p>

<p><b>Cause four: on the shelf and unfindable.</b> In the wrong place, behind something, on the bottom shelf, or in a section the customer did not think to look. The stock report says you have it. The customer says you do not. Both are correct.</p>

<p><b>How to tell them apart, which takes about a minute per line.</b> Check the system quantity. If it says zero, the cause is one or two, and the order history tells you which. If it says you have stock, walk to the back — cause three if it is there, cause four if it is on the floor somewhere you did not expect.</p>

<p><b>Why the distinction earns its keep.</b> Each cause has a different owner and a different remedy. Ordering is a routine. Supply is a report upward with evidence. Replenishment is a rota and a habit. Findability is a layout decision. Announce that "availability is a priority" and a team hears an instruction they cannot act on; name which of the four your branch is failing at and they can start on Monday.</p>

<p><b>And the diagnosis usually surprises.</b> Most managers assume supply. Most branches, on counting properly, find that cause three is the largest single component — which is good news, because it is the one they can fix themselves this week.</p>

<blockquote>IMPLEMENTATION TIP: For your next twenty gaps, write down which of the four caused each. Twenty minutes total, and the distribution tells you where to spend the next three months. Almost no branch has done this, and almost every one is surprised by the answer.</blockquote>

<p><b>A note on the causes shifting over time.</b> The distribution is not fixed. Fix your replenishment and cause three shrinks, which makes ordering and supply a larger share of what remains — not because they got worse, but because they are now what is left. That is progress rather than a new problem, and it is worth expecting, because a manager who sees supply rise from a fifth to a third of their gaps can easily conclude that suppliers have deteriorated when in fact their own half is fixed.</p>"""
, [
 C("The system says you have twelve in stock and the shelf is empty. The cause is:",
   ["Not ordered", "Three or four — walk to the back to find out which",
    "Supplier shortfall", "A system error"], 1,
   "In the back is cause three; on the floor in the wrong place is cause four."),
 C("'Availability is a priority' fails as an instruction because:",
   ["It is too general to argue with", "A team cannot act on it — they need to know which of the four is failing",
    "It sounds like criticism", "It has no target"], 1,
   "Name the cause and they can start on Monday."),
 C("Most managers assume supply is the main cause. Counting properly usually shows:",
   ["Supply confirmed", "Delivered but not shelved is the largest component",
    "Ordering is the largest", "The causes are evenly split"], 1,
   "Which is good news, because it is the one they can fix themselves this week.")]),

("Ordering what you will actually sell", 11, """<p>Ordering is arithmetic that people do by feel, and feel is systematically wrong in both directions: too little of what sells and too much of what does not.</p>

<p><b>The three numbers behind every order.</b> How fast the line sells, how long the supplier takes, and how confident you are in both. Everything else is refinement.</p>

<p><b>Lead time is the one most often ignored.</b> If a supplier takes fourteen days and you sell forty a day, you need 560 units simply to cover the wait — before any buffer for a delivery that slips or a week that runs hot. A branch ordering as though delivery were immediate will run out on its best-selling lines, repeatedly, and blame the supplier.</p>

<p><b>The buffer is for variability, not for comfort.</b> Two suppliers with the same fourteen-day average are not the same supplier if one is reliably fourteen and the other is fourteen sometimes and twenty-eight sometimes. The unreliable one costs you more stock permanently — which is a real cost, worth raising with whoever manages that relationship, and it is the kind of thing nobody has ever quantified for them.</p>

<p><b>Order by contribution, not by habit.</b> Contribution is what a line leaves you after the goods themselves are paid for — its price less what you paid. A line selling ₦900,000 a month where you keep 8 kobo in the naira leaves you ₦72,000; one selling ₦300,000 where you keep 35 kobo leaves ₦105,000. The second is smaller on any sales list and worth more to your branch. Your ordering attention should follow the second number rather than the first.</p>

<p><b>The two failures, and they are not symmetrical.</b> Ordering too little costs you sales you never see. Ordering too much costs you cash, space, and eventually a markdown you do take. The first is invisible and the second is visible, which is precisely why most branches drift toward too little on fast lines and too much on slow ones — the mistake nobody notices always wins.</p>

<p><b>Where the ordering discipline actually breaks.</b> Rarely in the calculation. It breaks when the person who orders is also serving, receiving and covering breaks, and the order is done at the end of a long day from memory. Protecting a fixed slot for ordering, with the figures to hand, fixes more than any amount of training in how to calculate a reorder point.</p>

<blockquote>IMPLEMENTATION TIP: Ask what your three worst-selling suppliers' actual lead times have been over the last three months, rather than what they are supposed to be. Most branches order against the promised number and run out against the real one.</blockquote>

<p><b>Where cash constrains the order, say so precisely.</b> Many branches order less than they should because the money is not there that week, and the conversation upward is usually vague about it. Be specific: this line sells this fast, we run out for this many days, and the cover we cannot fund costs this much in lost earnings each month. A funding constraint stated with the loss attached is a different request from one stated as needing more stock, and it is the version that gets answered.</p>"""
, [
 C("A supplier takes fourteen days and you sell forty a day. Before any buffer you need cover of:",
   ["40 units", "560 units", "140 units", "280 units"], 1,
   "A branch ordering as though delivery were immediate runs out on its best lines and blames the supplier."),
 C("Two suppliers both average fourteen days; one is reliably fourteen, the other varies to twenty-eight. The unreliable one:",
   ["Is equivalent on average", "Costs you more stock permanently, which is worth quantifying for whoever manages them",
    "Should be ordered from sooner", "Requires no buffer"], 1,
   "The buffer is for variability, not for comfort."),
 C("Branches drift toward too little of fast lines and too much of slow ones because:",
   ["Fast lines are harder to forecast", "The mistake nobody notices always wins — a stockout is invisible and a markdown is not",
    "Suppliers push slow lines", "Space is allocated wrongly"], 1,
   "Ordering too little costs sales you never see; ordering too much costs a markdown you do take.")]),

("Receiving: where money becomes goods", 11, """<p>The receiving bay is the point at which the business's money turns into the business's goods. It is usually staffed by the most junior person available, under time pressure, with a driver who wants to leave.</p>

<p><b>What a receipt actually asserts.</b> That these goods, in this quantity, in this condition, arrived here today. Everything downstream rests on it: what you pay, what your stock figure says, what your shelf can be filled from. It is the most consequential document created by the least senior person in the process, and that asymmetry is the whole of the risk.</p>

<p><b>The check that costs nothing and tells you most.</b> Compare what was received against what was ordered, across a month, by receiver. A person whose figures always match the order exactly is not counting — they are copying. Real deliveries are occasionally short, occasionally damaged, occasionally over. Perfect agreement across hundreds of deliveries means somebody is signing rather than checking.</p>

<p><b>Why that matters to availability specifically.</b> If you sign for twenty and eighteen arrived, your system believes you have twenty. Your shelf can only be filled with eighteen. The gap appears days later with no apparent cause, your stock figure disagrees with your shelf, and nobody connects it to a delivery signed for on a busy Tuesday.</p>

<p><b>The conditions that make counting possible.</b> Somebody whose job it is at that moment rather than somebody grabbed from the floor. A place to put goods down. Enough time that the driver waiting is not a reason to sign. And the authority to record a shortage without needing to find a manager — because if recording a problem requires an escalation, it will not be recorded.</p>

<p><b>Recording shortages is where the money is.</b> A shortage recorded is a credit you can claim and a supplier problem somebody can act on. A shortage waved through is a loss the business absorbs silently and a supplier who learns that this branch does not check. That reputation travels, and it is worth understanding that it travels in both directions.</p>

<p><b>What a manager should personally do.</b> Not receive. Watch a delivery being received, unannounced, once a month — not to catch anybody, but because you cannot design the arrangement without seeing the conditions the person is working in. Most receiving problems turn out to be about time, space or authority rather than about care.</p>

<p><b>The delivery window nobody negotiates.</b> If your supplier arrives at eleven on a Saturday, receiving happens at your busiest hour by whoever can be spared, which is nobody. That is often changeable and almost never asked about — a standing request for a different slot costs one conversation and removes the condition that makes careful receiving impossible. Where it genuinely cannot move, staff the bay for that window deliberately rather than hoping.</p>

<blockquote>WATCH-OUT: A receiver whose figures always match the order exactly is a stronger signal than one with frequent discrepancies. Discrepancies mean somebody is counting. Perfect agreement, sustained, means somebody is not.</blockquote>"""
, [
 C("You sign for twenty and eighteen arrived. Days later a gap appears with no apparent cause because:",
   ["The supplier shorted you again", "The system believes twenty and the shelf can only be filled with eighteen",
    "Stock was miscounted", "The order was wrong"], 1,
   "Nobody connects it to a delivery signed for on a busy Tuesday."),
 C("If recording a shortage requires finding a manager first, then shortages will:",
   ["Be recorded accurately", "Not be recorded",
    "Be reported weekly", "Be estimated"], 1,
   "The receiver needs authority to record one without an escalation."),
 C("A manager should attend a delivery unannounced once a month in order to:",
   ["Check the receiver", "See the conditions the person is working in",
    "Meet the driver", "Verify the count"], 1,
   "Most receiving problems turn out to be about time, space or authority rather than care.")]),

("The back room and the shelf", 11, """<p>The largest single cause of gaps in most branches is stock that is in the building and not on the shelf. It is also the one entirely within a manager's control, needs no money, and can be improved within a week.</p>

<p><b>Why it happens, and none of it is laziness.</b> A delivery arrives during trading and gets stacked because there is nowhere else. The person who was going to shelve it is called to the till. The shelf that needs filling is not the one anybody walked past. Nobody owns the gap between the back door and the shelf edge, so it belongs to whoever has a free moment, which on a busy day is nobody.</p>

<p><b>The three questions that fix most of it.</b></p>

<p><b>Who does it, by name?</b> Not "the team". A task belonging to everybody is a task belonging to nobody, and replenishment is the classic case.</p>

<p><b>When, specifically?</b> Before opening, and again at a named quiet point in the day. A branch that only fills before opening runs out through the afternoon on exactly the lines that sell fastest.</p>

<p><b>How do they know what to fill?</b> A walk of the lines that matter, not an inspection of everything. Somebody should arrive at the back with a short list rather than a general intention.</p>

<p><b>The back room's condition is the constraint nobody names.</b> If finding a case takes eight minutes, nobody fills a single gap between customers — they wait until a quiet spell that may not come. A back room organised so that the top lines are reachable in under a minute changes replenishment behaviour more than any instruction about priorities, and it costs an afternoon.</p>

<p><b>What to look at as a manager.</b> Walk the back room and the shelf together, in that order, twice a week. Anything in the back whose shelf is empty is a live loss, and the number of those at any moment is a measure of whether the routine is working. It is also the single most persuasive thing to show somebody who thinks availability is a supply problem.</p>

<p><b>And the afternoon test.</b> Compare the shelf at nine in the morning with the same shelf at four. Most branches look properly stocked at opening and thin by mid-afternoon, on the fastest lines, every day — which is a replenishment pattern rather than an ordering one, and it is invisible to anybody who only walks the floor in the morning.</p>

<blockquote>IMPLEMENTATION TIP: Count how many lines are empty on the shelf while stock sits in the back, at four in the afternoon, three days running. That number is your replenishment problem expressed in a way nobody can argue with, and it usually shocks the person who collects it.</blockquote>

<p><b>What to do with a delivery that arrives mid-trade and cannot be shelved immediately.</b> Not stack it wherever there is room, which is how stock becomes invisible. Keep the top lines separate and reachable, and put the rest away properly — the five minutes spent separating on arrival saves the twenty spent searching later, and it is the difference between a delivery that reaches the shelf that afternoon and one that surfaces in a count three weeks later.</p>"""
, [
 C("Your shelves look well stocked at nine and thin by four on the fastest lines, every day. This is:",
   ["An ordering problem", "A replenishment problem, invisible to anybody walking only in the morning",
    "A supply problem", "A layout problem"], 1,
   "Filling only before opening means running out through the afternoon on exactly the lines that sell fastest."),
 C("Your back room is disorganised and a case takes eight minutes to locate. The effect on gaps is that staff:",
   ["Fill more carefully", "Stop filling between customers and wait for a quiet spell that may not come",
    "Ask for assistance", "Report the difficulty"], 1,
   "A back room where top lines are reachable in a minute changes behaviour more than any instruction about priorities."),
 C("Replenishment as a task assigned to 'the team' is:",
   ["Efficient use of everybody", "A task belonging to nobody",
    "Standard practice", "Appropriate for a small branch"], 1,
   "It needs a name, a specific time, and a short list of what to fill.")]),

("On the shelf and still not found", 11, """<p>The fourth cause is the one no count will ever find. Your stock report says you have it. Your shelf says you have it. The customer could not see it, so as far as the sale is concerned you did not have it.</p>

<p><b>Where things become invisible.</b> Below knee height and above eye line. Behind a larger item. In a section the customer had no reason to visit. Behind a promotional display built over the top of it. In a fixture that was reorganised without anybody telling the staff who answer questions.</p>

<p><b>The test that costs twenty minutes.</b> Pick five items a customer might reasonably want and find them yourself, from the entrance, without using your knowledge of the store. It is a strange exercise and it is the fastest way to discover that two of the five are genuinely hard to locate.</p>

<p>Better still, ask somebody who does not work in your branch to do it. Your own knowledge is the thing standing between you and the customer's experience, and it cannot be switched off by trying.</p>

<p><b>What customers do rather than what they buy.</b> Twenty minutes standing still and watching tells you where people hesitate, what they pick up and put down, where they look up for a sign that is not there, and which aisle they walk past without entering. None of it appears in any report and all of it is available for free, every day, to a manager willing to stand still.</p>

<p><b>Ask your staff the one question they can answer better than anybody.</b> What do customers ask you where the answer is on the shelf? The team fields that question constantly and nobody has ever collected the answers. A list of ten such items usually contains three genuine findability problems and two lines you should be stocking differently.</p>

<p><b>Promotional displays deserve their own warning.</b> A display built in an aisle can hide the shelf behind it entirely, and the line it hides is often a steady seller earning more than the promotion in front of it. Whoever builds a display should walk the aisle from both directions afterwards. Almost nobody does.</p>

<p><b>And the signage point.</b> A customer who cannot find a section will not usually ask — most people would rather leave than admit they are lost in a shop. Signage is not decoration; it is the difference between a customer finding your stock and your stock being invisible to them.</p>

<blockquote>IMPLEMENTATION TIP: Ask your team to write down, for one week, every item a customer asked them to locate. That list is the cheapest findability audit available, it takes them no extra time, and it comes from the only people in the building who hear the question.</blockquote>

<p><b>And the change nobody tells the floor about.</b> A fixture moved, a section reorganised, a range shuffled centrally — the staff answering customer questions frequently learn about it by being wrong in front of somebody. Whoever moves anything should tell the people who will be asked, on the day, and a manager who makes that a rule removes a category of embarrassment that quietly makes staff avoid customers who look lost.</p>"""
, [
 C("Your stock report and your shelf both say you have it; the customer could not see it. As far as the sale is concerned:",
   ["You had it and lost the sale to service", "You did not have it",
    "It is a layout preference", "The report is wrong"], 1,
   "The fourth cause is the one no count will ever find."),
 C("Asking somebody from outside your branch to find five items is better than doing it yourself because:",
   ["They are more objective", "Your own knowledge of the store cannot be switched off by trying",
    "They shop more often", "They will be quicker"], 1,
   "It is the fastest way to discover that two of the five are genuinely hard to locate."),
 C("A promotional display built in an aisle should be followed by:",
   ["A sales check after a week", "Walking the aisle from both directions to see what it hides",
    "A price verification", "A stock count"], 1,
   "The line it hides is often a steady seller earning more than the promotion in front of it.")]),

("Slow lines, dead stock and the space they hold", 11, """<p>Availability is usually discussed as a shortage problem. The other half is what is taking up the space — because a shelf is finite, and every facing given to something that does not sell is a facing not given to something that does.</p>

<p><b>What dead stock actually costs, and it is three things.</b> The money tied up in it, which is money you cannot spend on lines that would sell. The space it occupies, which is the part managers most often miss. And the attention it absorbs — counted, moved, dusted, and worked around every time somebody fills the shelf beside it.</p>

<p><b>The space cost is the real one at branch level.</b> A bay holding stock that turns twice a year, where the neighbouring bay turns weekly, is not merely idle — it is actively costing you whatever the fast line would have earned in that space. That is the number to use when arguing for a range change, because it is a loss the business is suffering rather than an opportunity it is missing, and the two are received very differently.</p>

<p><b>Finding it without a system that flags it.</b> Walk your range with the question: when did I last see one of these leave? Staff know this better than any report — the person who fills that shelf can tell you in a sentence which lines never move. Ask them, write the list down, and price the space.</p>

<p><b>What you can and cannot do about it.</b> You usually cannot delete a line from the range, which is a central decision. You can nearly always reduce its facings, move it from prime space, stop reordering it, and mark down what you hold to clear it. Those four are yours and they recover most of the value.</p>

<p><b>Marking down, honestly.</b> Clearing dead stock at a loss feels like accepting a defeat, and it is the opposite: what you paid for it is already spent and cannot be recovered by holding it longer. The only live question is what it will fetch now against what the space and money could do instead. A branch that clears its dead stock quarterly is in a better position than one holding it at full value and calling that prudence.</p>

<p><b>And the seasonal trap.</b> Stock bought for a peak that underperformed does not become more sellable by waiting. Clear it while it is still current rather than storing it for next year, when it will be a year older, out of style, and occupying space for eleven months to save a markdown you will take anyway.</p>

<blockquote>WATCH-OUT: The instinct to hold rather than mark down is strongest on the items where somebody made the buying decision. Nobody wants to write down their own judgement. That is exactly why a quarterly clearance should be routine rather than a decision — a routine has no author to embarrass.</blockquote>

<p><b>Where the space actually goes afterwards.</b> Clearing dead stock only pays if the space is reassigned deliberately. A cleared bay that stays half-empty, or fills with whatever arrives next, has converted one problem into another. Decide before you clear what is going there — usually more facings of something that already sells out — so the exercise ends with a line that turns rather than a gap you created.</p>"""
, [
 C("Holding dead stock rather than clearing it at a loss is:",
   ["Prudent, since the value may return", "The opposite — what you paid is already spent and cannot be recovered by holding",
    "Correct if the season repeats", "A head office decision"], 1,
   "The only live question is what it will fetch now against what the space and money could do instead."),
 C("You have a bay turning twice a year next to one turning weekly. The cost most managers overlook is:",
   ["The money tied up in it", "The space, which is actively costing you what the fast line would earn there",
    "The time spent counting it", "Its eventual obsolescence"], 1,
   "A bay turning twice a year beside one turning weekly is actively costing you what the fast line would have earned."),
 C("A quarterly clearance should be a routine rather than a decision because:",
   ["It is faster", "A routine has no author to embarrass",
    "It suits the calendar", "Head office requires it"], 1,
   "The instinct to hold is strongest on items where somebody made the buying decision.")]),

("Okelewo: the Lalubu storeroom", 11, """<p>Lalubu is the flagship. Highest sales in the group, a manager customers ask for by name, and the third-worst stock losses of eleven branches. This is what a proper look found, and it is a common shape.</p>

<p><b>What she was doing.</b> Serving at the busiest hour every day, because she is the best cashier the business ever had and the queue moves when she is on it. Fifty-five hours a week. Her floor is excellent. Her storeroom had not been examined in about a year.</p>

<p><b>What the count found, in the order it was found.</b></p>

<p><b>Gaps on fast lines every afternoon.</b> The morning fill was thorough and there was no second one, so from about two o'clock the top twenty lines thinned steadily. Nobody had walked the shelf at four.</p>

<p><b>Stock in the back for a third of the gaps.</b> Goods delivered, stacked where there was room, and never shelved — because replenishment belonged to whoever was free, which during trading was nobody. Cause three, and the largest single component.</p>

<p><b>A receiving bay with no receiver.</b> Deliveries were signed for by whoever was nearest, usually while serving. Received quantities matched ordered quantities almost exactly, every time, for eight months. Nobody was counting.</p>

<p><b>Two bays of stock that had not turned in a year</b>, sitting at eye level near the entrance, because that was where it had been put when it arrived and nobody had revisited it.</p>

<p><b>What none of this was.</b> It was not theft, though the shrinkage number had made everybody assume so. It was not a supply problem, though that was the manager's own explanation. It was four ordinary operational failures in a branch whose manager was working extremely hard in the wrong place.</p>

<p><b>What changed, and the order matters.</b> An afternoon replenishment slot with a name against it. One person receiving, with time and authority to record a short delivery. The two dead bays cleared and the space given to the top-selling category. And, hardest of all, the manager off the till at the busiest hour — which she resisted, because it is the part of the job she is best at and the part her team most visibly needed.</p>

<p><b>The result after a quarter.</b> Sales up four per cent with no change in footfall, price or range — just from selling things the branch already had. Stock losses down by roughly a third. And the manager working forty-eight hours instead of fifty-five.</p>

<blockquote>IMPLEMENTATION TIP: The Lalubu pattern — excellent floor, unexamined back room, manager on the till — is the commonest shape in retail. If you recognise it, start with the afternoon walk. It is the cheapest of the four changes and it produces a number within two weeks that makes the rest easier to argue for.</blockquote>

<p><b>What made the Lalubu changes stick.</b> Not the manager's willingness, which was never in doubt, but that each change had a name and a time attached. The afternoon fill belonged to one person at a fixed hour. The receiving belonged to one person for the delivery window. Changes framed as new priorities faded within a month at that branch, as they do everywhere; the ones framed as somebody's job at a specific time survived.</p>"""
, [
 C("Lalubu's shrinkage had made everybody assume theft. The count found:",
   ["Confirmed internal theft", "Four ordinary operational failures",
    "A supplier problem", "A counting error"], 1,
   "The manager's own explanation had been supply, and that was wrong too."),
 C("The largest single component of Lalubu's gaps was:",
   ["Not ordered", "Stock in the back that was never shelved",
    "Supplier shortfall", "Findability"], 1,
   "Replenishment belonged to whoever was free, which during trading was nobody."),
 C("Received quantities matched ordered quantities almost exactly for eight months. This meant:",
   ["Excellent supplier performance", "Nobody was counting",
    "Orders were accurate", "The system was reconciling"], 1,
   "Deliveries were signed for by whoever was nearest, usually while serving.")]),

("The availability routine", 11, """<p>This is the chapter to keep. Everything above becomes a habit or it becomes nothing, and the habit is small enough to survive a bad week.</p>

<p><b>Daily, by somebody with a name.</b> Fill before opening. Fill again at a fixed afternoon point. Both slots owned by a person rather than by the team.</p>

<p><b>Twice a week, fifteen minutes, by you.</b> Walk your top forty lines — the ones that earn most, not the ones that sell most — and count how many are unavailable. Same time of day each week, so the numbers compare. This is the measurement everything else rests on and almost no branch has it.</p>

<p><b>Weekly.</b> Take your gaps and mark each with its cause: not ordered, not delivered, in the back, or unfindable. Ten minutes. The distribution tells you what to work on and it changes over a quarter as you fix things.</p>

<p><b>Weekly, from your team.</b> What did customers ask for that we did not have or they could not find? The people at the counter hear this all day and are never asked.</p>

<p><b>Monthly.</b> Watch one delivery being received, unannounced. Compare received against ordered by receiver across the month. Walk the range for lines that have not moved.</p>

<p><b>Quarterly.</b> Clear the dead stock. Review what the range is doing to your space. Take the cause distribution to your manager with the money attached.</p>

<p><b>What to do with the number.</b> Availability on the lines that matter is the single most useful figure a branch manager can hold, because it is large, it is local, and nobody above you has it either. A manager who can say "we were 91% available on our top forty in March and 96% in June, and here is what the missing 4% is costing" is having a completely different conversation from one reporting that availability has improved.</p>

<p><b>And the honest expectation.</b> You will not reach 100% and should not try — the last few points cost more in stock than they earn in sales. Somewhere in the mid-nineties on the lines that matter is a good branch. The gap worth closing is between where you are and there, and for most branches that gap is worth six figures a month.</p>

<blockquote>IMPLEMENTATION TIP: Start with the twice-weekly count of forty lines and nothing else. Four weeks of that number, and the cause of each gap, will tell you which of the other habits your branch actually needs — and it is the only one of them you cannot substitute with judgement.</blockquote>

<p><b>A closing word on what this module is really about.</b> Nothing here is sophisticated. Count the lines that matter, know why each gap is there, put a name and a time against filling the shelf, and clear what does not sell. It is unglamorous work and it is where the largest recoverable money in a branch sits — which is exactly why it is available: everybody knows it matters and very few branches do it deliberately.</p>"""
, [
 C("Choosing the forty lines to count twice a week, you should rank them by:",
   ["Units sold", "What they earn you",
    "How often they run out", "Head office's list"], 1,
   "Volume and earnings are not the same list, and the count should follow the second."),
 C("You are at 96% on your top forty and considering pushing for 100%. You should not, because:",
   ["It cannot be reached", "The last few points cost more in stock than they earn in sales",
    "Customers do not expect it", "Suppliers will not support it"], 1,
   "Mid-nineties on the lines that matter is a good branch."),
 C("If you start only one habit from this module, it should be:",
   ["The afternoon fill", "The twice-weekly count of forty lines",
    "The receiving check", "The dead stock review"], 1,
   "It is the only one you cannot substitute with judgement, and four weeks of it tells you which others you need.")]),
]


QUESTIONS = [
 Q("What distinguishes a lost sale from every other loss in a branch is that it:", ["Is larger", "Leaves no trace at all", "Is harder to price", "Recurs"], 1,
   "Damaged stock can be counted and a discount appears on a receipt; the customer who left does not.", "Ch1 §1", "The invisible loss"),
 Q("A line selling four a day at ₦1,200 keeping 30 kobo in the naira, out nine days, costs about:", ["₦1,440", "₦13,000", "₦43,000", "₦130,000"], 1,
   "And that is the line alone, before whatever else those customers did not buy.", "Ch1 §4", "The invisible loss"),
 Q("Availability is described as the best problem to work on partly because:", ["It is easy", "There is no ceiling — a branch cannot cut past zero but can nearly always sell more of what it stocks", "Head office funds it", "It is quick"], 1,
   "Large, local, and most of it needs no money.", "Ch1 §6", "The invisible loss"),
 Q("A gap present for more than a fortnight is usually:", ["Escalated", "No longer visible to anybody in the branch", "Filled", "Recorded"], 1,
   "Which is why the count must be deliberate rather than left to noticing.", "Ch1 §8", "The invisible loss"),
 Q("The four causes of a gap are not ordered, not delivered, not shelved, and:", ["Miscounted", "On the shelf but unfindable", "Damaged", "Stolen"], 1,
   "The stock report says you have it and the customer says you do not; both are correct.", "Ch2 §5", "The four causes"),
 Q("The system shows stock and the shelf is empty. The next step is to:", ["Reorder", "Walk to the back", "Check the supplier", "Recount"], 1,
   "In the back is cause three; on the floor in the wrong place is cause four.", "Ch2 §6", "The four causes"),
 Q("Supplier shortfall is not yours to fix but is entirely yours to:", ["Absorb", "Record", "Escalate weekly", "Reorder around"], 1,
   "Recording it turns a complaint into a case somebody central can act on.", "Ch2 §3", "The four causes"),
 Q("Counting properly usually reveals the largest cause to be:", ["Ordering", "Delivered but not shelved", "Supply", "Findability"], 1,
   "Which is good news, because it is the one a branch can fix itself this week.", "Ch2 §9", "The four causes"),
 Q("The three numbers behind every order are sell rate, confidence and:", ["Shelf capacity", "Supplier lead time", "Margin", "Order minimum"], 1,
   "The one most often ignored.", "Ch3 §2", "Ordering"),
 Q("A supplier taking fourteen days, on a line selling forty a day, needs cover of at least:", ["140", "560", "40", "280"], 1,
   "Before any buffer for a slipped delivery or a hot week.", "Ch3 §3", "Ordering"),
 Q("The buffer on a variable supplier exists for:", ["Comfort", "Variability", "Growth", "Promotions"], 1,
   "Two suppliers averaging fourteen days are not the same supplier if one varies to twenty-eight.", "Ch3 §4", "Ordering"),
 Q("A line selling ₦900,000 at 8 kobo in the naira against one selling ₦300,000 at 35 kobo: the second leaves you:", ["₦72,000", "₦105,000", "₦24,000", "₦300,000"], 1,
   "Smaller on any sales list and worth more to your branch.", "Ch3 §5", "Ordering"),
 Q("Branches drift toward under-ordering fast lines because:", ["Forecasting is harder", "A stockout is invisible and a markdown is not", "Suppliers restrict them", "Cash is short"], 1,
   "The mistake nobody notices always wins.", "Ch3 §6", "Ordering"),
 Q("Ordering discipline usually breaks:", ["In the calculation", "When the person ordering is also serving, receiving and covering breaks", "At month end", "When systems change"], 1,
   "A protected slot with the figures to hand fixes more than training in reorder points.", "Ch3 §7", "Ordering"),
 Q("A receipt asserts that these goods, in this quantity and condition:", ["Were ordered", "Arrived here today", "Were paid for", "Were shelved"], 1,
   "The most consequential document created by the least senior person in the process.", "Ch4 §2", "Receiving"),
 Q("A receiver whose figures always match the order exactly is:", ["Accurate", "Copying rather than counting", "Well supplied", "Efficient"], 1,
   "Real deliveries are occasionally short, damaged or over.", "Ch4 §3", "Receiving"),
 Q("Signing for twenty when eighteen arrived produces:", ["An immediate variance", "A gap days later with no apparent cause", "A supplier credit", "A price difference"], 1,
   "The system believes twenty and the shelf can only be filled with eighteen.", "Ch4 §4", "Receiving"),
 Q("If recording a shortage requires finding a manager, shortages will be:", ["Recorded carefully", "Not recorded", "Estimated", "Reported later"], 1,
   "The receiver needs the authority to record one without escalating.", "Ch4 §5", "Receiving"),
 Q("A shortage waved through teaches the supplier that:", ["The branch is easy to serve", "This branch does not check", "Deliveries are flexible", "Credit is unnecessary"], 1,
   "That reputation travels, in both directions.", "Ch4 §6", "Receiving"),
 Q("The largest single cause of gaps in most branches is:", ["Supply failure", "Stock in the building and not on the shelf", "Under-ordering", "Theft"], 1,
   "Entirely within a manager's control, needing no money.", "Ch5 §1", "Replenishment"),
 Q("Replenishment assigned to 'the team' is:", ["Efficient", "A task belonging to nobody", "Standard", "Flexible"], 1,
   "It needs a name, a specific time, and a short list.", "Ch5 §4", "Replenishment"),
 Q("A branch that fills only before opening will:", ["Stay stocked all day", "Run out through the afternoon on its fastest lines", "Need less stock", "Reduce waste"], 1,
   "Which is a replenishment pattern, invisible to anybody walking only in the morning.", "Ch5 §5", "Replenishment"),
 Q("If finding a case in the back takes eight minutes, staff will:", ["Be more careful", "Wait for a quiet spell rather than filling between customers", "Ask for help", "Report it"], 1,
   "Organising the back room changes behaviour more than instructions about priorities.", "Ch5 §7", "Replenishment"),
 Q("Anything in the back whose shelf is empty is:", ["Buffer stock", "A live loss", "Awaiting rotation", "Correctly held"], 1,
   "And the count of those is a measure of whether the routine works.", "Ch5 §8", "Replenishment"),
 Q("The fourth cause is the one that:", ["Costs least", "No count will ever find", "Suppliers cause", "Recurs seasonally"], 1,
   "The report says you have it and the customer says you do not.", "Ch6 §1", "Findability"),
 Q("Asking somebody from outside the branch to find five items is better because:", ["They are objective", "Your own knowledge of the store cannot be switched off", "They shop more", "They are quicker"], 1,
   "Two of the five usually turn out to be genuinely hard to locate.", "Ch6 §4", "Findability"),
 Q("The question only your counter staff can answer is:", ["What sells fastest", "What customers ask them to locate", "What is out of stock", "What competitors charge"], 1,
   "They field it all day and nobody has ever collected the answers.", "Ch6 §6", "Findability"),
 Q("After building a promotional display in an aisle you should:", ["Check sales after a week", "Walk the aisle from both directions", "Verify pricing", "Recount the stock"], 1,
   "The line it hides is often a steady seller earning more than the promotion.", "Ch6 §7", "Findability"),
 Q("A customer who cannot find a section will usually:", ["Ask a member of staff", "Leave rather than admit they are lost", "Look for a sign", "Return later"], 1,
   "Which is why signage is not decoration.", "Ch6 §8", "Findability"),
 Q("The cost of dead stock that managers most often miss is:", ["The cash tied up", "The space it occupies", "The counting time", "The insurance"], 1,
   "A bay turning twice a year beside one turning weekly is actively costing you.", "Ch7 §2", "Dead stock"),
 Q("The space argument works better than an opportunity argument because it describes:", ["A future gain", "A loss the business is already suffering", "A competitor threat", "A range gap"], 1,
   "The two are received very differently.", "Ch7 §3", "Dead stock"),
 Q("Which can a branch manager usually NOT do about a slow line?", ["Reduce its facings", "Delete it from the range", "Stop reordering it", "Mark it down"], 1,
   "Deleting a line is a central decision; the other three are yours.", "Ch7 §5", "Dead stock"),
 Q("Holding dead stock rather than marking it down is:", ["Prudent", "The opposite — what you paid is already spent", "Correct seasonally", "A cash decision"], 1,
   "The only live question is what it fetches now against what the space could do.", "Ch7 §6", "Dead stock"),
 Q("Seasonal stock that underperformed should be:", ["Stored for next year", "Cleared while it is still current", "Returned to supplier", "Held at full value"], 1,
   "A year older, out of style, and occupying space for eleven months to save a markdown you take anyway.", "Ch7 §7", "Dead stock"),
 Q("Lalubu's shrinkage had led everybody to assume theft. The actual causes were:", ["Internal theft confirmed", "Four ordinary operational failures", "Supplier fraud", "System error"], 1,
   "In a branch whose manager was working extremely hard in the wrong place.", "Ch8 §6", "Okelewo Lalubu"),
 Q("Lalubu's received quantities matched ordered quantities for eight months, meaning:", ["Excellent suppliers", "Nobody was counting", "Accurate ordering", "Good system control"], 1,
   "Deliveries were signed for by whoever was nearest, usually while serving.", "Ch8 §5", "Okelewo Lalubu"),
 Q("The hardest of the four changes at Lalubu was:", ["The afternoon slot", "Getting the manager off the till at the busiest hour", "Clearing the dead bays", "Assigning a receiver"], 1,
   "It is the part of the job she is best at and the part her team most visibly needed.", "Ch8 §7", "Okelewo Lalubu"),
 Q("Lalubu's sales rose four per cent after a quarter with no change in footfall, price or range, because the branch:", ["Promoted harder", "Sold things it already had", "Extended hours", "Reduced prices"], 1,
   "Stock losses fell by roughly a third and the manager worked seven hours less.", "Ch8 §8", "Okelewo Lalubu"),
 Q("The twice-weekly count should cover the forty lines that:", ["Sell most units", "Earn the most", "Are most often out", "Cost the most"], 1,
   "Volume and earnings are not the same list.", "Ch9 §3", "The routine"),
 Q("Marking each gap with its cause takes about:", ["An hour", "Ten minutes", "Half a day", "A week"], 1,
   "And the distribution changes over a quarter as you fix things.", "Ch9 §4", "The routine"),
 Q("Aiming for 100% availability is wrong because:", ["It is impossible", "The last few points cost more in stock than they earn", "Customers do not notice", "Suppliers cannot support it"], 1,
   "Mid-nineties on the lines that matter is a good branch.", "Ch9 §8", "The routine"),
 Q("If you start only one habit, it should be the count because it is:", ["Quickest", "The only one you cannot substitute with judgement", "Most visible", "Head office's expectation"], 1,
   "Four weeks of it tells you which of the other habits your branch needs.", "Ch9 §9", "The routine"),
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
    rebalance(QUESTIONS, "retail:availability:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:availability:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 3 — Availability and the Shelf",
        "desc": ("The largest recoverable loss in most branches, and the one no report "
                 "contains. The four causes of a gap and the different fix each needs, "
                 "ordering against real lead times, receiving as the moment money becomes "
                 "goods, the back room, findability, dead stock and the space it holds, "
                 "and a routine small enough to survive a bad week."),
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
