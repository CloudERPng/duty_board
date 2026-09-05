#!/usr/bin/env python3
"""Build 'The Working Day' into academy_shopfloor_data.json.

Module 9 of Retail Foundations, and the last.

The capstone problem is the same one the Retail Leadership track faced: a final
module that restates the previous eight is worthless. This one earns its place
by changing the axis. Modules 1 to 8 are organised by subject; a shift is not.
It arrives as a sequence, and the same person who can answer every question in
this track can still be overwhelmed at eleven o'clock on a Saturday because
nobody ever told them what order to do things in.

So this module is organised by time — open, morning, the busy hour, the quiet
hour, the close — and its content is the one thing no earlier module could
give: what to do when several right things compete for the same pair of hands.

Three positions:

  PRIORITISATION IS THE SKILL. Named as such, given an explicit order, and
  practised. Everything else in the track is a thing to do; this is how to
  choose between them, and it is what actually separates two people working
  the same shift.

  IT IS HONEST ABOUT BAD DAYS. Short-staffed, behind, everything at once. The
  advice is to decide what is NOT being done rather than to attempt everything
  badly, which is the same rule module 6's supervisor used and the one most
  people never learn.

  THE TRACK'S CLOSE IS DELIBERATELY MODEST. No grand claim about transforming
  a career. The honest summary is that almost nothing here is clever, all of it
  is available to anybody, and it is worth learning because very few people do
  it deliberately.

Run from the app package directory:  python3 build_shopfloor_m9.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_day"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The skill nobody names", 10, """<p>Everything in this track so far is a thing to do. This module is about choosing between them, which is the actual difficulty of the job and the thing almost nobody is taught.</p>

<p><b>What a shift really feels like.</b> Not a list worked through in order. A queue of small competing demands arriving faster than one person can meet them: a customer approaching, a delivery half away, a gap on a shelf, a colleague asking for change, a phone ringing, something spilt. Every one is legitimate. Nobody hands you the order.</p>

<p><b>Which is why two people on the same shift produce different results.</b> Not effort — most people work hard. The difference is that one of them is choosing deliberately and the other is doing whatever is nearest and loudest, and by the end of the day the second person has been busy continuously and left the important things undone.</p>

<p><b>The order, and it holds almost everywhere.</b></p>

<p><b>Anything unsafe comes first.</b> A spill, a blocked exit, something about to fall, somebody hurt. Not because it is urgent but because the cost of being wrong is different in kind from everything else on the list.</p>

<p><b>Then a customer who is waiting.</b> They are the only item that cannot be rescheduled, and they are watching.</p>

<p><b>Then anything with a clock on it.</b> Chilled goods out of the chiller, a delivery vehicle waiting, something that closes at a time.</p>

<p><b>Then filling gaps.</b> The largest recoverable value in the shop and the thing that gets skipped when the day gets busy.</p>

<p><b>Then everything else</b> — facing, tidying, cleaning, the jobs that look like work and can wait an hour without costing anything.</p>

<p><b>The one thing to notice about that order.</b> The most visible tasks are at the bottom. A shop where somebody is always tidying and the shelves have holes in them is a shop where somebody is working hard in the wrong order, and it is a very common way to spend a career without ever being promoted.</p>

<p><b>Where the order does not settle it.</b> Occasionally two things at the same level compete — two customers waiting, two perishable jobs. Then the tiebreak is which one gets worse fastest. A customer who has just arrived can wait thirty seconds; one who has been standing for two minutes cannot. Chilled stock out in the sun degrades faster than chilled stock in the shade. That single question resolves most of the remainder.</p>

<blockquote>WORTH KNOWING: If you learn one thing from this module, learn that list. It resolves perhaps eight decisions out of ten without any thought at all, which leaves your attention for the two that genuinely need it.</blockquote>"""
, [
 C("The difference between two people on the same shift is mostly:",
   ["Effort", "Whether they are choosing deliberately or doing what is nearest and loudest",
    "Experience", "Which section they work"], 1,
   "One of them ends the day busy continuously with the important things undone."),
 C("Anything unsafe comes first because:",
   ["It is most urgent", "The cost of being wrong is different in kind from everything else",
    "Policy requires it", "Customers notice"], 1,
   "A spill, a blocked exit, something about to fall."),
 C("The most visible tasks sit:",
   ["At the top of the order", "At the bottom",
    "In the middle", "Outside the order"], 1,
   "A shop where somebody is always tidying and the shelves have holes is somebody working hard in the wrong order.")]),

("Before the doors open", 10, """<p>The first fifteen minutes decide the shape of the whole shift, and they are the minutes most often spent putting a bag down and starting whatever is in front of you.</p>

<p><b>The handover, first.</b> Ask whoever is going off, or read whatever was left. What happened, what is outstanding, what is coming today. Thirty seconds, and it prevents you discovering all of it the hard way at eleven.</p>

<p><b>The safety walk, which takes ninety seconds and almost nobody does.</b> Exits clear. Nothing spilt. Nothing stacked where it will fall. It sounds excessive on an ordinary morning and it is the only moment in the day when you will look at those things deliberately.</p>

<p><b>Then the floor, as a customer would walk it.</b> What is empty, what is untidy, what is obviously wrong. You are building a list, not fixing anything yet — the fixing comes after you know the whole picture, because otherwise you spend twenty minutes on the first problem you met rather than the biggest.</p>

<p><b>Then the temperature check, if your branch has chillers.</b> Doors closed, nothing above the load line, nothing that sounds wrong. Ten seconds, and it is the one check where finding a problem early rather than late is worth thousands.</p>

<p><b>Then decide the order.</b> Given what you found and what is coming, what has to happen before the shop gets busy and what can wait for the quiet hour? Fill before facing. Chilled before ambient. The lines that sell fastest before the ones that do not.</p>

<p><b>And the thing to check that nobody mentions.</b> Whether anybody is off. It changes the entire shape of a day — who covers breaks, whether the delivery gets away, whether you will be alone at the busy hour. Knowing at nine is a plan; discovering at two is a scramble.</p>

<p><b>If you arrive to no handover at all.</b> Common on openings, and on any shift following somebody who left in a hurry. Do the other three parts and add one: look for anything mid-flight. A half-emptied cage, a trolley in an aisle, a section half-filled. Those are the previous shift's unfinished sentences, and finding them at eight is much cheaper than meeting them at eleven.</p>

<p><b>Why the walk comes before the work rather than after it.</b> Because once you start a task you stop being able to see the shop — attention narrows to the thing in your hands, and it stays narrow for as long as you are busy. The five minutes at the start is the only part of the day when you look at the whole floor with nothing else competing, which is why it produces a better list than an hour of noticing things while doing something else.</p>

<blockquote>IMPLEMENTATION TIP: Do the four — handover, safety, floor, temperature — in that order for one week. It takes under five minutes in total and you will find you already know about most of the day's problems before anybody tells you, which is most of what a good reputation is made of.</blockquote>"""
, [
 C("The floor walk at the start of a shift is for:",
   ["Fixing what you find", "Building a list",
    "Counting stock", "Checking prices"], 1,
   "Fixing the first problem you meet means spending twenty minutes on it rather than on the biggest one."),
 C("The check that changes the entire shape of a day is:",
   ["The delivery time", "Whether anybody is off",
    "The weather", "The promotion schedule"], 1,
   "Knowing at nine is a plan; discovering at two is a scramble."),
 C("The safety walk takes about:",
   ["Ten minutes", "Ninety seconds",
    "Half an hour", "As long as needed"], 1,
   "And it is the only moment in the day when those things get looked at deliberately.")]),

("The morning", 10, """<p>The most productive hours of most retail days, and the ones most often spent on the wrong things.</p>

<p><b>What the morning is for.</b> Getting the shop ready to sell before the people who buy arrive. Everything that is easier without customers in the way — filling, deliveries, the heavy work — belongs here, and everything that can be done with customers present belongs later.</p>

<p><b>The delivery, if there is one.</b> It comes first because it has a vehicle attached and because the goods are worth nothing in a cage. Count before signing. Cold goods away before anything else. Then get it out rather than putting it away — a delivery neatly stacked in the stockroom is the biggest cause of empty shelves in the shop.</p>

<p><b>Then the fill, in the right order.</b> Chilled and fresh first, because they are perishable and because they sell early. Then the fast lines, then everything else. Rotate as you go — it costs nothing at that moment and a write-off later. Check dates while the stock is in your hand.</p>

<p><b>The trap of the morning.</b> Working on something absorbing and not looking up. The shop is quiet, the task is satisfying, and forty minutes pass without you noticing that two customers came in and left. Glance up every few minutes; it is the whole of the customer part of the morning.</p>

<p><b>What not to do now.</b> Deep cleaning, reorganising, anything that makes a section unusable for a while. Those belong in the quiet hour, and doing them in the morning means the shop is worse exactly when it starts trading.</p>

<p><b>And the morning's real test.</b> Whether the shop is ready when the first real customers arrive. Not perfect — ready. Full shelves, nothing unsafe, somebody visible. A shop that is still being set up at midday has lost the morning twice: once by not being ready, and once because the work now has to be done around people.</p>

<p><b>The morning judgement worth getting right.</b> How much to put out. Too little and you are refilling all day; too much and you have a back room on the shelf and stock that will not sell before its date. The rough answer is enough to last until the next natural gap in the day, which for most lines is until the quiet hour — and the way to learn it for your own section is to notice, for a fortnight, which lines you keep going back to.</p>

<p><b>What to do when the delivery is late.</b> It happens constantly and it wrecks the morning plan, because everything was sequenced around it. The useful response is to work the rest of the plan rather than waiting — fill from what is already in the building, do the date check, do the stockroom — so that when the vehicle arrives the only thing left is the delivery itself. Standing ready for a delivery that has not come is the most expensive way to spend a morning.</p>

<blockquote>IMPLEMENTATION TIP: Get the delivery out before you make it neat. Stock on the shelf sells; stock stacked beautifully in the back does not, and the neatness can happen this afternoon.</blockquote>"""
, [
 C("A delivery neatly stacked in the stockroom is:",
   ["Correctly handled", "The biggest cause of empty shelves in the shop",
    "Ready for the fill", "Safe until needed"], 1,
   "Stock on the shelf sells and stock stacked beautifully in the back does not — get it out before you make it neat."),
 C("The trap of the morning is:",
   ["Starting too slowly", "Working on something absorbing and not looking up",
    "Filling in the wrong order", "Taking a break too early"], 1,
   "Forty minutes pass without noticing that two customers came in and left."),
 C("Deep cleaning and reorganising belong:",
   ["In the morning", "In the quiet hour",
    "Before opening", "At close"], 1,
   "Doing them in the morning makes the shop worse exactly when it starts trading.")]),

("The busy hour", 10, """<p>The part of the day everything else exists to support, and the part where planning stops and judgement starts.</p>

<p><b>What changes.</b> You stop doing tasks and start responding. That is correct rather than a failure — the busy hour is when the shop makes its money, and a person filling shelves while a queue builds is doing the second-most-valuable thing available.</p>

<p><b>The order collapses to three things.</b> Customers who are waiting. The queue moving. Anything unsafe. Everything else can wait an hour, and the hour is short.</p>

<p><b>Watch rather than serve, where you can.</b> If somebody else has the till and you are free, the most valuable position is where you can see the whole thing — the queue, the aisles, who needs help, what is emptying. Somebody has to be able to see it, and during the busy hour the person on the till cannot.</p>

<p><b>Fill the fast lines only.</b> Not a general fill. The three or four things emptying quickest, done in gaps, because a hole on a fast line during the busiest hour costs more than the entire rest of the day's replenishment.</p>

<p><b>Do not start anything you cannot stop.</b> The rule that saves the most trouble. Anything that leaves a section unusable, a trolley in the way or a job half-open is wrong in this hour, however tempting the gap looks.</p>

<p><b>Say things out loud.</b> To customers waiting — that somebody is coming. To colleagues — that the queue is building, that you are taking the chilled gap, that you are going for change. In a busy hour, three people working silently do less than three people saying what they are doing, because everybody duplicates and nobody covers.</p>

<p><b>And afterwards, the ten minutes that matter.</b> When it drops, do the reset before you rest: put back what was abandoned, fill what emptied, clear what was dropped. Ten minutes then is worth an hour later, and it is the difference between a shop that recovers from a rush and one that carries it for the rest of the day.</p>

<p><b>When the busy hour is longer than an hour.</b> Some days it is four, and the advice above assumes a rush that ends. If it does not, the reset has to happen in pieces — two minutes whenever it eases rather than ten minutes at the end — and something has to give, which is chapter 7's territory. What must not happen is running the whole afternoon on busy-hour rules and arriving at close with nothing filled and everything abandoned.</p>

<blockquote>WATCH-OUT: The commonest mistake in a busy hour is starting a task at the wrong moment — a fill, a count, a stockroom job. It feels productive and it removes you from the floor exactly when the floor needs somebody on it.</blockquote>"""
, [
 C("In the busy hour, the priority order collapses to customers waiting, anything unsafe and:",
   ["The delivery", "The queue moving",
    "Filling gaps", "The till count"], 1,
   "Everything else can wait an hour, and the hour is short."),
 C("Three people working silently in a busy hour do less than three people saying what they are doing because:",
   ["It is quicker to shout", "Everybody duplicates and nobody covers",
    "Customers hear it", "The supervisor can direct them"], 1,
   "Saying what you are taking is what prevents two people doing the same thing."),
 C("The ten minutes immediately after a rush should be spent:",
   ["Resting", "Resetting — putting back, filling, clearing",
    "Counting", "On the stockroom"], 1,
   "Ten minutes then is worth an hour later.")]),

("The quiet hour", 10, """<p>The most misunderstood part of the day. If the job were serving customers, a quiet hour would be nothing to do. It is in fact when almost everything that improves a shop happens.</p>

<p><b>What belongs here, roughly in order of value.</b></p>

<p><b>The gaps that were not filled during the rush.</b> First, always, because they are still costing money.</p>

<p><b>The date check.</b> A section at a time, front and back, on a rotation so the whole shop gets covered across a fortnight.</p>

<p><b>The stockroom.</b> The single highest-return use of a quiet hour, and the least visible. Anything that makes the next fill faster pays every day afterwards.</p>

<p><b>Dead facings and things in the wrong place.</b> The items customers cannot find, which are lost sales sitting in plain view.</p>

<p><b>Then the visible work.</b> Facing, cleaning, tidying. Genuinely worth doing and last, because they can be done at any time and everything above cannot.</p>

<p><b>The habit that separates people.</b> Having a list before the quiet hour arrives. Somebody with a list uses twenty quiet minutes; somebody without spends them looking for something to do and then tidying, because tidying is what presents itself. The list comes from the morning walk and from what you noticed during the rush.</p>

<p><b>What to do when there genuinely is nothing.</b> Learn something. Read shelf labels in a section you do not know. Ask a colleague what a line is for. Walk somebody else's aisle and find their gaps. Twenty minutes of that, twice a week, is what makes somebody useful across the whole shop rather than only in their own corner.</p>

<p><b>And the thing not to do.</b> Disappear. A quiet shop still needs somebody visible, and the quiet hour is exactly when the customer who needs help is least able to find anybody.</p>

<p><b>And the quiet hour that is not quiet.</b> Some branches do not get one, particularly small ones with steady trade. Then the quiet-hour work happens in five-minute pieces all day, which is harder and entirely possible: one gap filled between customers, one shelf date-checked while passing, three minutes in the stockroom when the delivery is away. The list matters more in that branch than in one with a genuine lull, because without it nothing on it ever gets started.</p>

<p><b>The trap at the other end.</b> A long quiet period, particularly in the afternoon, and the temptation to start something large — a full reorganisation, a deep clean, a whole-section reset. Check the clock first. Anything that leaves the shop worse for an hour is only safe if there is more than an hour, and the commonest version of this mistake is a section pulled apart at four o'clock and still apart when the after-work trade arrives.</p>

<blockquote>IMPLEMENTATION TIP: Keep a running list on your phone or in a pocket during the shift — the gap you could not fill, the label that was wrong, the thing you noticed. The quiet hour then answers itself, and it is the difference between twenty useful minutes and twenty spent straightening.</blockquote>"""
, [
 C("The highest-return use of a quiet hour is:",
   ["Facing", "The stockroom",
    "Cleaning", "The date check"], 1,
   "It is also the least visible, and anything that makes the next fill faster pays every day afterwards."),
 C("Somebody without a list spends a quiet hour:",
   ["Resting", "Looking for something to do, and then tidying",
    "Helping colleagues", "Learning the range"], 1,
   "Tidying is what presents itself when nothing has been planned."),
 C("Disappearing during a quiet hour is a problem because:",
   ["Supervisors notice", "It is when a customer needing help is least able to find anybody",
    "Work goes undone", "It looks bad"], 1,
   "A quiet shop still needs somebody visible.")]),

("The close", 10, """<p>The last twenty minutes are the part colleagues judge you on, because they are the part they inherit.</p>

<p><b>What closing is actually for.</b> Not finishing your work — leaving the shop in a state the next shift can start from. Those are different, and the difference shows up in what gets prioritised when there is not time for everything.</p>

<p><b>The order, when you are short of time.</b> Anything unsafe or perishable first — the spill, the chilled stock left out, the thing that cannot wait overnight. Then anything that would block tomorrow morning: the delivery cage in the way, the stockroom you cannot get through. Then the fill for the morning, if your branch fills at close. Then the visible tidying, which is genuinely last.</p>

<p><b>The handover, which takes thirty seconds and is the highest-value part.</b> What happened, what is outstanding, what is coming, anything not obvious. Written where you can, so it reaches the opener who was not there rather than only the person in front of you. Including on the days nothing happened — <i>nothing outstanding, delivery came, all away</i> is useful and it builds the habit for the days when it matters.</p>

<p><b>Never leave a job half-done and silent.</b> Half-done is often unavoidable; silent is the part that causes the trouble. One sentence converts an abandoned task into a handed-over one.</p>

<p><b>The money and the keys.</b> Count in front of somebody, report any difference in either direction, and never make one up from your own pocket. Lock what should be locked. Log out. These take two minutes and they are the ones that protect you rather than the shop.</p>

<p><b>And the last look.</b> Walk the floor once as a customer would see it in the morning. You are not fixing anything — you are noticing, so that what you write down is true and so that tomorrow's opener meets what you said they would.</p>

<p><b>The close that is rushed, which is most of them.</b> If you have ten minutes and twenty minutes of work, the handover is the thing that survives — not because it is the biggest job but because it is the only one that makes tomorrow easier rather than today tidier. A shop that opens knowing what happened yesterday recovers from an untidy close in twenty minutes. A shop that opens blind spends the morning finding out.</p>

<p><b>And the one thing worth doing even when there is no time at all.</b> Say it rather than write it. Thirty seconds to whoever is there — the two things they most need to know — beats a note nobody wrote because the shift overran. The written version is better and the spoken version is enormously better than nothing, which is what most rushed closes actually produce.</p>

<blockquote>WORTH KNOWING: Nobody sees the four hours you worked well and everybody meets the trolley you left. That is unfair as an assessment and entirely accurate as a prediction of what following you is like.</blockquote>"""
, [
 C("Closing is for:",
   ["Finishing your work", "Leaving the shop in a state the next shift can start from",
    "Completing the checklist", "Securing the building"], 1,
   "The difference shows in what gets prioritised when there is not time for everything."),
 C("The handover should be given:",
   ["When something happened", "Including on the days nothing happened",
    "Weekly", "Only to the supervisor"], 1,
   "It is useful information and it builds the habit for the days when it matters."),
 C("Counting the drawer in front of somebody and reporting differences either way:",
   ["Protects the shop", "Protects you",
    "Is a formality", "Is the supervisor's job"], 1,
   "Along with locking what should be locked and logging out.")]),

("The day that goes wrong", 10, """<p>Short-staffed, behind, three things at once, and no prospect of doing it all. This happens regularly and almost nobody is taught what to do about it.</p>

<p><b>The instinct, and why it fails.</b> Work faster and try to do everything. It produces a day where every job is done badly, nothing is finished, mistakes are made, and the person is exhausted and has nothing to show. Speed is not the variable that gives; scope is.</p>

<p><b>What to do instead.</b> Decide what is not being done, deliberately and early. Not everything can be done, so the only question is whether the things dropped are chosen or accidental. Chosen means the right things survive; accidental means whatever was furthest from you at the time is what got missed.</p>

<p><b>What survives, in every version of a bad day.</b> Safety. Customers waiting. Anything perishable. The money handled properly — because a bad day is exactly when mistakes with cash happen and exactly when nobody has time to sort them out afterwards.</p>

<p><b>What goes.</b> Facing. Cleaning beyond the necessary. Deep work of any kind. The stockroom. And any improvement project, however keen you were about it this morning.</p>

<p><b>Say it out loud.</b> To your supervisor if there is one — <i>I am not going to get the stockroom done, is that alright?</i> — and to colleagues. That single sentence converts something that will look like a failure into a decision somebody agreed with, and it takes four seconds. People almost never say it, and then apologise at the end of the shift for something nobody would have minded.</p>

<p><b>And do not carry it home.</b> A bad day is a bad day. It is not evidence about you, particularly when it was caused by two people being off. The person who works well on the good days and steadily on the bad ones is doing the job properly; nobody is judged on a Saturday when the shop was short by two.</p>

<p><b>What a bad day is genuinely worth, afterwards.</b> Notice what broke first. The thing that fell over soonest when there was not enough time is usually the thing with no slack in it on ordinary days either — a routine only one person knows, a job that always runs to the last minute, a section that is only ever just about kept. Bad days are the cheapest diagnostic a branch gets, and almost nobody reads them that way.</p>

<p><b>The version of a bad day that is nobody's fault and still costs.</b> Two people off, a late delivery and a broken chiller in the same shift. Nothing was mismanaged, and the shop still needs somebody to decide the order. That is the whole argument of this module in one sentence: the days that go well can be worked through, and the days that go badly have to be chosen through — and the second is a skill rather than an attitude.</p>

<blockquote>IMPLEMENTATION TIP: The sentence to practise is 'I am not going to get X done today.' Said at eleven it is a plan. Said at five it is an excuse, and it is exactly the same information.</blockquote>"""
, [
 C("On a bad day, the variable that gives is:",
   ["Speed", "Scope",
    "Quality", "Hours"], 1,
   "Trying to do everything faster produces a day where every job is done badly and nothing is finished."),
 C("Things dropped on a bad day should be:",
   ["Whatever is furthest away", "Chosen",
    "Decided by the supervisor", "Caught up afterwards"], 1,
   "Accidental dropping means whatever was furthest from you is what got missed."),
 C("'I am not going to get X done today' said at eleven rather than at five is:",
   ["The same either way", "A plan rather than an excuse",
    "Less honest", "Better in writing"], 1,
   "It is exactly the same information, and the timing is what changes how it lands.")]),

("Okelewo Stores: an ordinary Thursday", 10, """<p>A full shift at the Ibadan branch, sixteen months in, with Ada now the senior assistant. Nothing remarkable happens, which is the point.</p>

<p><b>07:50.</b> Arrives ten minutes early, as always. Handover from the closer: delivery expected, one chiller was making a noise last night, the promotion end was left half-built. Safety walk — exits clear, nothing spilt. Floor walk with a list forming. Chillers: the noisy one sounds fine now, noted to mention it anyway. One person off sick, so breaks will be tight.</p>

<p><b>08:30.</b> Delivery. Counted against the note before the driver leaves — two cases short on a line, written on the paperwork, signed. Cold goods into the cold first. Then out onto the floor rather than into the stockroom, chilled and fresh before anything else, rotating and checking dates as she goes.</p>

<p><b>10:00.</b> The promotion end rebuilt, because it is the fastest-selling space in the shop and it was left half-done. Fifteen minutes.</p>

<p><b>11:30 to 13:00, the busy hour.</b> No tasks. Watching, filling the three fast lines in gaps, taking the queue twice when it built past four. One customer complaint about a price — checked, the customer was right, apologised, fixed the label afterwards so it would not happen again. Nothing started that could not be stopped.</p>

<p><b>13:10.</b> The reset. Ten minutes putting back, filling, clearing. Then a break.</p>

<p><b>14:00, the quiet hour.</b> The list from the morning: two gaps that did not get filled, a date check on the household aisle, twenty minutes in the stockroom moving the fast lines nearer the door. Not the facing, which could wait.</p>

<p><b>16:00.</b> Realises the stockroom job will not be finished and the afternoon fill has not started. Says so to the supervisor: the fill matters more, the stockroom can wait until Monday. Agreed in four seconds.</p>

<p><b>17:40, the close.</b> Perishables away, the cage moved out of the morning's path, the fill done. Drawer counted with the supervisor watching, ₦200 over, reported. Four lines of handover: the short delivery, the chiller noise, the price label fixed, the stockroom half-moved.</p>

<p><b>What the day contained.</b> No crisis, no heroics, and about eleven separate decisions about what to do next — almost all of them resolved by the order in chapter 1 without any thought at all.</p>

<blockquote>IMPLEMENTATION TIP: Read that timeline against your own last shift. Not to feel bad about the comparison — to notice which of the moments were decisions you made and which just happened to you. That ratio is the whole of this module.</blockquote>"""
, [
 C("At the delivery, the two-case shortage was:",
   ["Reported afterwards", "Written on the paperwork before signing, with the driver present",
    "Noted for the count", "Accepted and adjusted"], 1,
   "The last point at which a shortage is a conversation rather than an unresolvable loss."),
 C("At 16:00, realising the stockroom would not be finished, Ada:",
   ["Stayed late", "Said so and agreed which job mattered more",
    "Worked faster", "Left it half-done silently"], 1,
   "Agreed in four seconds, because said at four it is a plan rather than an excuse."),
 C("The drawer was ₦200 over, which was:",
   ["Left as it was", "Reported",
    "Adjusted", "Noted at the next count"], 1,
   "Over is as much a problem as short, and every difference is reported in either direction.")]),

("The whole track, and what to do on Monday", 10, """<p>Nine modules, and they come down to less than it looks.</p>

<p><b>The job is six things, not one</b> (module 1). Stock where customers can buy it, a shelf that tells the truth, service that brings people back, money handled so nothing goes missing, what you notice getting said, and the shift running whether or not anybody is watching. The quiet hour is the job rather than a break from it.</p>

<p><b>Service is four things</b> (module 2). Findable, knowing the answer, the queue moving, doing what you said. Warmth improves all four and replaces none, which is why a quiet person can be excellent at this.</p>

<p><b>The shelf is the biggest number you can influence</b> (module 3). Four causes of a gap, two of them yours, and the largest is stock that is in the building and not out. Fill before you face.</p>

<p><b>Rotation is the habit that pays most</b> (module 4). New behind, old forward, every time. Dates are a safety matter first. Damage is recorded, not hidden.</p>

<p><b>The controls protect you</b> (module 5). Your own login, one person to a drawer, count at handovers, report every difference, and the line is at zero. Never put yourself between a person and the door.</p>

<p><b>A shift owes the next one a clean start</b> (module 6). Lateness lands on a named person. The handover is thirty seconds. Bullying, harassment and unsafe work are not part of learning the job.</p>

<p><b>When it goes wrong, people come before stock and cash</b> (module 7). The first thirty seconds, who to call, where your responsibility ends. Comply in a robbery.</p>

<p><b>Reliability first, then a section right unwatched, then taking something on</b> (module 8). Ask the three questions. Almost nobody does.</p>

<p><b>And choose deliberately</b> (module 9). Unsafe, waiting customer, clock, gaps, everything else.</p>

<p><b>What to actually do on Monday.</b> Three things, and no more. Arrive ten minutes early. Do the four-part start — handover, safety, floor, temperature. And leave one sentence of handover at the end. Those three take under ten minutes across a whole shift, they need nobody's permission, and they will change how the day goes within a fortnight.</p>

<p><b>The honest summary of this track.</b> Almost nothing in it is clever. A shelf filled before it is faced, a date checked while the stock is in your hand, a difference reported, a sentence at the end of a shift. All of it is available to anybody who decides to do it, and the reason it is worth learning is that very few people do it deliberately — which is also why doing it gets noticed faster than most people expect.</p>

<blockquote>WORTH KNOWING: If you keep three habits from nine modules, keep the ten minutes early, the four-part start, and the handover sentence. Everything else in this track is easier once those three are automatic, and none of them requires you to be good at anything yet.</blockquote>"""
, [
 C("The three things to do on Monday are ten minutes early, the four-part start and:",
   ["A date check", "One sentence of handover at the end",
    "Filling before facing", "Asking for feedback"], 1,
   "Under ten minutes across a whole shift, and none of them needs anybody's permission."),
 C("The honest summary of the track is that almost nothing in it is:",
   ["Difficult", "Clever",
    "Practical", "New"], 1,
   "It is available to anybody, and worth learning because very few people do it deliberately."),
 C("The three habits are recommended because everything else in the track:",
   ["Depends on them", "Is easier once they are automatic",
    "Requires supervision", "Comes later"], 1,
   "And none of them requires you to be good at anything yet.")]),
]


QUESTIONS = [
 Q("A shift arrives as:", ["A list worked through in order", "A queue of competing demands arriving faster than one person can meet them", "A rota of tasks", "A sequence of customers"], 1,
   "Every one is legitimate and nobody hands you the order.", "Ch1 §2", "Choosing"),
 Q("The priority order begins with:", ["A waiting customer", "Anything unsafe", "Anything with a clock", "Filling gaps"], 1,
   "Not because it is most urgent but because the cost of being wrong differs in kind.", "Ch1 §4", "Choosing"),
 Q("A waiting customer comes second because they are:", ["Most visible", "The only item that cannot be rescheduled", "Most valuable", "Most likely to complain"], 1,
   "And they are watching.", "Ch1 §5", "Choosing"),
 Q("Facing, tidying and cleaning sit:", ["Second", "Last", "Above filling", "Outside the order"], 1,
   "They can wait an hour without costing anything.", "Ch1 §8", "Choosing"),
 Q("A shop where somebody is always tidying and the shelves have holes shows:", ["Understaffing", "Somebody working hard in the wrong order", "Poor ordering", "A layout problem"], 1,
   "A very common way to spend a career without ever being promoted.", "Ch1 §9", "Choosing"),
 Q("The priority list resolves roughly how many decisions without thought?", ["Half", "Eight out of ten", "All of them", "A few"], 1,
   "Which leaves your attention for the two that genuinely need it.", "Ch1 §10", "Choosing"),
 Q("The four-part start is handover, safety walk, floor walk and:", ["The till", "Temperature", "The rota", "The delivery"], 1,
   "Under five minutes in total.", "Ch2 §5", "Before opening"),
 Q("The safety walk covers exits clear, nothing spilt and:", ["Prices correct", "Nothing stacked where it will fall", "Doors locked", "Alarms set"], 1,
   "The only moment in the day those get looked at deliberately.", "Ch2 §3", "Before opening"),
 Q("The temperature check is worth doing because finding a problem early rather than late is worth:", ["A few naira", "Thousands", "A written report", "A supervisor's time"], 1,
   "Doors closed, nothing above the load line, nothing sounding wrong.", "Ch2 §5", "Before opening"),
 Q("Knowing whether anybody is off changes:", ["The mood", "The entire shape of the day", "The rota only", "Break times"], 1,
   "Who covers breaks, whether the delivery gets away, whether you are alone at the busy hour.", "Ch2 §7", "Before opening"),
 Q("The morning is for:", ["Cleaning", "Getting the shop ready to sell before the buyers arrive", "Paperwork", "Training"], 1,
   "Everything easier without customers in the way belongs there.", "Ch3 §2", "The morning"),
 Q("At a delivery, the order is count, cold goods away and then:", ["Stack it neatly", "Get it out onto the floor", "Check the paperwork", "Update the system"], 1,
   "The neatness can happen this afternoon.", "Ch3 §3", "The morning"),
 Q("The fill order in the morning is chilled and fresh, then:", ["Everything else", "The fast lines", "Promotions", "Heavy items"], 1,
   "Rotating as you go and checking dates while the stock is in your hand.", "Ch3 §4", "The morning"),
 Q("Deep cleaning and reorganising in the morning means:", ["An early finish", "The shop is worse exactly when it starts trading", "Better standards", "Less disruption"], 1,
   "Those belong in the quiet hour.", "Ch3 §6", "The morning"),
 Q("A shop still being set up at midday has lost the morning:", ["Once", "Twice", "Partly", "Not at all"], 1,
   "Once by not being ready, and once because the work now happens around people.", "Ch3 §7", "The morning"),
 Q("During the busy hour you stop doing tasks and start responding, which is:", ["A failure of planning", "Correct", "A sign of understaffing", "Temporary"], 1,
   "The busy hour is when the shop makes its money.", "Ch4 §2", "The busy hour"),
 Q("Somebody filling shelves while a queue builds is doing:", ["The right thing", "The second-most-valuable thing available", "Nothing useful", "What they were told"], 1,
   "The order collapses to three things in that hour.", "Ch4 §2", "The busy hour"),
 Q("If somebody else has the till and you are free, the most valuable position is:", ["Beside them", "Where you can see the whole thing", "In the stockroom", "On the door"], 1,
   "The person on the till cannot see it during the busy hour.", "Ch4 §4", "The busy hour"),
 Q("During the busy hour you fill:", ["Nothing", "The three or four fastest lines, in gaps", "Whatever is empty", "The promotional ends only"], 1,
   "A hole on a fast line then costs more than the rest of the day's replenishment.", "Ch4 §5", "The busy hour"),
 Q("The rule that saves the most trouble in a busy hour is:", ["Serve first", "Do not start anything you cannot stop", "Ask for help", "Keep the queue short"], 1,
   "Anything leaving a section unusable or a job half-open is wrong in that hour.", "Ch4 §6", "The busy hour"),
 Q("The commonest mistake in a busy hour is:", ["Serving too slowly", "Starting a task at the wrong moment", "Leaving the till", "Not asking for help"], 1,
   "It feels productive and removes you from the floor when the floor needs somebody.", "Ch4 §8", "The busy hour"),
 Q("The quiet hour is when:", ["Little happens", "Almost everything that improves a shop happens", "Staff rest", "Cleaning is done"], 1,
   "If the job were serving customers, it would be nothing to do.", "Ch5 §1", "The quiet hour"),
 Q("The first thing in a quiet hour is:", ["The stockroom", "The gaps that were not filled during the rush", "The date check", "Facing"], 1,
   "They are still costing money.", "Ch5 §3", "The quiet hour"),
 Q("The date check should run:", ["All at once", "A section at a time, on a rotation across a fortnight", "Weekly on everything", "Only on fast lines"], 1,
   "Front and back, so the whole shop gets covered.", "Ch5 §4", "The quiet hour"),
 Q("The habit that separates people at the quiet hour is:", ["Working faster", "Having a list before it arrives", "Asking the supervisor", "Starting immediately"], 1,
   "Somebody without one spends it looking for something to do and then tidying.", "Ch5 §8", "The quiet hour"),
 Q("When there is genuinely nothing to do, the recommendation is to:", ["Rest", "Learn something", "Help elsewhere", "Ask for tasks"], 1,
   "Twenty minutes twice a week is what makes somebody useful across the whole shop.", "Ch5 §9", "The quiet hour"),
 Q("Closing is for leaving the shop in a state:", ["That looks finished", "The next shift can start from", "The manager expects", "That passes inspection"], 1,
   "Different from finishing your own work, and the difference shows in what gets prioritised.", "Ch6 §2", "The close"),
 Q("At close, the first priority when short of time is:", ["The fill", "Anything unsafe or perishable", "The tidying", "The handover"], 1,
   "Then anything that would block tomorrow morning.", "Ch6 §3", "The close"),
 Q("A handover should be written where possible so that it reaches:", ["The supervisor", "The opener who was not there", "The record", "Everybody equally"], 1,
   "A spoken one only reaches the person in front of you.", "Ch6 §4", "The close"),
 Q("Half-done is often unavoidable; what causes the trouble is:", ["The amount left", "Silent", "The timing", "Who inherits it"], 1,
   "One sentence converts an abandoned task into a handed-over one.", "Ch6 §5", "The close"),
 Q("The last look around the floor is for:", ["Fixing things", "Noticing, so what you write down is true", "Security", "Cleaning"], 1,
   "So tomorrow's opener meets what you said they would.", "Ch6 §7", "The close"),
 Q("On a bad day, trying to do everything faster produces:", ["A long day", "Every job done badly and nothing finished", "Acceptable results", "Overtime"], 1,
   "Speed is not the variable that gives; scope is.", "Ch7 §2", "The bad day"),
 Q("The only real question on a short-staffed day is whether the things dropped are:", ["Recoverable", "Chosen or accidental", "Reported", "Few"], 1,
   "Accidental means whatever was furthest from you got missed.", "Ch7 §3", "The bad day"),
 Q("What survives every version of a bad day includes safety, waiting customers, perishables and:", ["The stockroom", "The money handled properly", "Facing", "The fill"], 1,
   "A bad day is exactly when cash mistakes happen and when nobody has time to sort them out.", "Ch7 §4", "The bad day"),
 Q("Saying 'I am not going to get X done' takes about:", ["A minute", "Four seconds", "A conversation", "A written note"], 1,
   "And it converts something that looks like a failure into a decision somebody agreed with.", "Ch7 §6", "The bad day"),
 Q("A bad day caused by two people being off is:", ["Evidence about you", "Not evidence about you", "A performance matter", "Worth explaining"], 1,
   "Nobody is judged on a Saturday when the shop was short by two.", "Ch7 §7", "The bad day"),
 Q("Ada's handover from the closer included the delivery, the half-built promotion end and:", ["A price error", "A chiller making a noise", "A staff absence", "A complaint"], 1,
   "Which she noted to mention even though it sounded fine in the morning.", "Ch8 §2", "Ordinary Thursday"),
 Q("The promotion end was rebuilt at 10:00 because:", ["It looked untidy", "It is the fastest-selling space in the shop", "The supervisor asked", "Stock had arrived"], 1,
   "Fifteen minutes, before the busy period.", "Ch8 §4", "Ordinary Thursday"),
 Q("During the busy hour Ada started:", ["The afternoon fill", "Nothing that could not be stopped", "The stockroom", "A date check"], 1,
   "Watching, filling three fast lines in gaps, and taking the queue twice.", "Ch8 §5", "Ordinary Thursday"),
 Q("After the price complaint, Ada fixed the label because:", ["Policy required it", "It would otherwise happen again", "The customer asked", "The supervisor noticed"], 1,
   "The customer was right, and the cause was in plain view.", "Ch8 §5", "Ordinary Thursday"),
 Q("The quiet hour was spent on the morning's list and:", ["Facing", "Twenty minutes moving fast lines nearer the stockroom door", "Cleaning", "Paperwork"], 1,
   "The facing could wait.", "Ch8 §7", "Ordinary Thursday"),
 Q("The day contained about how many decisions on what to do next?", ["Two or three", "About eleven", "Dozens", "None worth noting"], 1,
   "Almost all resolved by the priority order without any thought at all.", "Ch8 §10", "Ordinary Thursday"),
 Q("The three things to start on Monday are ten minutes early, the four-part start and:", ["A date check", "One sentence of handover", "A stockroom hour", "Asking for feedback"], 1,
   "Under ten minutes across a whole shift, needing nobody's permission.", "Ch9 §11", "The whole track"),
]


BANNED = ["at the end of the day"]


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
    if len(LESSONS) != 9:
        raise SystemExit("ABORT: %d chapters, expected 9" % len(LESSONS))

    rebalance(QUESTIONS, "shopfloor:the_day:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:the_day:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    problems = []
    seen = set()
    for _t, _e, html, ch in LESSONS:
        flat = re.sub(r"<[^>]+>", " ", html).lower()
        for b in BANNED:
            if b in flat:
                problems.append("banned phrase %r" % b)
        if len(ch) != 3:
            problems.append("chapter has %d checks" % len(ch))
        for c in ch:
            norm = re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip()
            if norm in bank:
                problems.append("duplicates exam question: %s" % c["q"][:58])
            if norm in seen:
                problems.append("duplicate check: %s" % c["q"][:58])
            seen.add(norm)
            if len(c.get("why") or "") < 40:
                problems.append("weak rationale: %s" % c["q"][:50])
            if len(c["opts"]) != 4:
                problems.append("not 4 options: %s" % c["q"][:50])
    if problems:
        raise SystemExit("ABORT — %d problem(s):\n  %s" % (len(problems), "\n  ".join(problems)))

    mod = {
        "title": "RF 9 — The Working Day",
        "desc": ("Everything in the track, in the order a shift actually meets it. The priority "
                 "order that resolves most decisions without thought, the four-part start, the "
                 "morning, the busy hour, the quiet hour, the close, what to do on a day that "
                 "goes wrong, and the three habits worth keeping from all nine modules."),
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
    thin = [i + 1 for i, n in enumerate(lens) if n < 2500]
    print("thin chapters:", thin or "NONE")


if __name__ == "__main__":
    main()
