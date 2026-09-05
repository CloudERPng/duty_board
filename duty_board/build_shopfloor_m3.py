#!/usr/bin/env python3
"""Build 'The Shelf' into academy_shopfloor_data.json.

Module 3 of Retail Foundations.

This is the module that matters most, and the one where an entry-level learner
can affect the branch's results more than at any other point in the track. The
Retail Leadership track states the manager's version of the same claim: the gap
on the shelf is the largest recoverable loss in most branches and it appears in
no report. This module is the floor-level version — the person who can actually
close it.

Two things it deliberately refuses to do:

  It does not teach replenishment as tidying. Facing, filling and rotating are
  presented as three different jobs with three different purposes, because
  learners who think of them as one thing ("doing the shelf") do the visible
  one and skip the two that carry the money.

  It does not pretend the learner controls ordering. They do not. What they
  control is what leaves the stockroom, what gets noticed, and what gets said —
  and the module is honest that the fourth cause of a gap, the one nobody in
  the building can fix, still has to be reported rather than absorbed.

The four causes come from the manager track and are stated here in the terms a
floor assistant meets them: not ordered, ordered and late, in the building and
not on the shelf, on the shelf and not findable. The third is the largest and
the one entirely within the reader's gift, which is the module's central point.

Run from the app package directory:  python3 build_shopfloor_m3.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_shelf"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The gap nobody records", 10, """<p>When a customer wants something and it is not there, almost nothing happens. They put something else in the basket or they leave. No note is made, no alarm sounds, and when the figures are added up they show what was sold rather than what was wanted.</p>

<p><b>Which makes it the strangest loss in retail.</b> Everything else that costs a shop money leaves a trace. A theft shows up as a shortage at the count. A damaged item is written off and recorded. An expired tin is thrown away and somebody logs it. The empty space on a shelf costs more than all three in most branches and produces no record at all.</p>

<p><b>What it is actually worth.</b> Take the ₦300 margin from module 1. A line that sells thirty a day, out for three days, is ninety lost sales — ₦27,000 of margin from one gap on one product. Most branches have several at any moment. That is why this module comes before stock handling and honesty: it is simply the biggest number a person on the floor can influence.</p>

<p><b>And the second loss, which is larger and slower.</b> A customer who fails to find their weekly item three visits running stops assuming you will have it. They start shopping elsewhere for the whole basket rather than for that one line, and they do not announce it. Module 2 said a regular is worth around half a million naira over two years; availability is how they are lost, far more often than service is.</p>

<p><b>The thing to hold onto.</b> Nobody will ever tell you off for a gap you did not cause. The gap is not a personal failure and this module is not about blame — it is about the fact that a shelf with holes in it is a shop turning customers away all day, quietly, and that the person standing nearest to it is usually the only one who can tell.</p>

<blockquote>WORTH KNOWING: Ask your manager what the branch's worst out-of-stock line was last month. Many will not be able to answer, which is not incompetence — it is that the information only exists on the floor, in the heads of people who saw it.</blockquote>

<p><b>Why this is not the same as caring about the shop's profits.</b> You do not need to. The argument works from your own side too: a shelf with holes in it produces a shift full of customers asking you for things you cannot give them, which is the most tiring version of the job. People who work well-stocked sections spend their day helping, and people who work empty ones spend it apologising for something that was not their doing. That difference is worth more to a shift than it is to the accounts.</p>

<p><b>How big the number actually is, stated carefully.</b> Studies of this in retail put lost sales from unavailability at several percent of what a shop could have taken — the exact figure varies by trade and nobody should quote one as gospel. What is not in dispute is the ranking: in a typical branch it is larger than shrinkage, larger than damage, and larger than waste, and unlike all three it is invisible. That combination — biggest and unrecorded — is why it survives for years in shops that measure everything else carefully.</p>"""
, [
 C("Compared with theft, damage and expiry, a gap on the shelf:",
   ["Costs less", "Costs more in most branches and produces no record",
    "Is recorded automatically", "Is the buyer's responsibility"], 1,
   "Every other loss leaves a trace; this one produces nothing at the end of the day."),
 C("A line selling thirty a day, out for three days, loses roughly:",
   ["₦900 of margin", "₦27,000 of margin",
    "₦9,000 of margin", "Only the day's sales"], 1,
   "Ninety lost sales at ₦300 of margin each, from one gap on one product."),
 C("A customer who cannot find their weekly item three visits running:",
   ["Complains", "Stops assuming you will have it, and moves the whole basket",
    "Buys an alternative", "Asks a member of staff"], 1,
   "They do not announce it, which is why availability loses more regulars than service does.")]),

("Four reasons a shelf is empty", 10, """<p>Every gap has one of four causes, and they need four different responses. Treating them as one thing — "we are out of it" — is why the same gaps recur.</p>

<p><b>Cause one: it was never ordered.</b> Somebody's ordering decision, made elsewhere, possibly weeks ago. You cannot fix it and you can report it, which is the only useful thing available.</p>

<p><b>Cause two: it was ordered and has not arrived.</b> A late delivery, a supplier short-shipping, an import held up. Also not yours to fix. Also worth reporting, because the person who orders often does not know a delivery came short unless somebody says so.</p>

<p><b>Cause three: it is in the building and not on the shelf.</b> In the stockroom, on a pallet, in a cage, behind something. This is the big one — in most branches it is the largest of the four — and it is entirely, completely within your control.</p>

<p><b>Cause four: it is on the shelf and the customer cannot find it.</b> Behind a facing of something else, on the wrong shelf, hidden by a promotion, or in a place nobody would look. The stock exists, the sale is still lost, and the fix takes ten seconds once somebody notices.</p>

<p><b>Why the split matters to you specifically.</b> Two of the four are somebody else's decision and two are yours. If you fix causes three and four in your own section — reliably, every shift — you have closed most of the gaps that were closeable, and the ones remaining are genuine supply problems rather than the shop failing to put its own stock out.</p>

<p><b>The diagnosis, which takes under a minute.</b> Customer asks for something and the shelf is empty. Check the stockroom. If it is there, that is cause three: bring it. If it is not, check whether it is somewhere else on the floor — a promotional end, a second site, misplaced. If it is nowhere, it is cause one or two, and the useful action is telling somebody rather than shrugging.</p>

<blockquote>IMPLEMENTATION TIP: For one week, every time you meet a gap, decide which of the four it is before doing anything else. The proportions in your own branch will surprise you, and knowing them changes what you spend your time on.</blockquote>

<p><b>A fifth cause, which is really cause three in disguise.</b> The stock is on the floor, in a cage or on a pallet or on a trolley, waiting to be put out. It is technically available, it is physically in front of customers, and it is unsellable because nobody can serve themselves from a cage. Deliveries that sit half-worked through a trading day are one of the commonest versions of an empty shelf, and the fix is the same: get it out.</p>"""
, [
 C("The largest of the four causes in most branches is:",
   ["Never ordered", "In the building and not on the shelf",
    "Ordered and late", "On the shelf but unfindable"], 1,
   "And it is the one entirely within a floor assistant's control."),
 C("When something is nowhere in the building, the useful action is:",
   ["Apologising to the customer", "Telling somebody",
    "Waiting for the next delivery", "Suggesting an alternative"], 1,
   "The person who orders often does not know a delivery came short unless somebody says so."),
 C("Of the four causes, how many are within a floor assistant's control?",
   ["One", "Two",
    "All four", "None"], 1,
   "Causes three and four; the other two are ordering and supply decisions made elsewhere.")]),

("Three different jobs, not one", 10, """<p>People talk about "doing the shelf" as though it were a single task. It is three, they have different purposes, and the visible one is the least valuable.</p>

<p><b>Filling.</b> Putting stock out so there is something to buy. This is the one that makes money, and it is the one skipped when time is short, because an empty shelf looks like less work than an untidy one.</p>

<p><b>Facing.</b> Pulling the front row forward and turning labels outward, so the shelf looks tended and a customer can read what is there. This is the visible one, the one a manager can see from across the shop, and the one people do first.</p>

<p><b>Rotating.</b> Putting new stock behind old, so the oldest sells first. This is the invisible one, it takes almost no extra time if done while filling, and skipping it is what turns stock into waste. Module 4 covers dates properly; the habit belongs here because it happens at the moment of filling or not at all.</p>

<p><b>The order when you are short of time, which is most days.</b> Fill first, always. A full shelf that is slightly untidy sells; a beautifully faced shelf with holes in it does not. And rotate while you fill, because it costs nothing at that moment and costs a write-off later.</p>

<p><b>Facing is not worthless.</b> A shelf that looks tended sells more and is stolen from less, both measurably, and a shop where facing is neglected starts to feel abandoned to customers in a way they cannot articulate but do respond to. The argument is about order, not about value.</p>

<p><b>The mistake to know about.</b> Facing an empty shelf. Pulling the last four tins forward so the gap is at the back looks better and is worse — it hides the gap from you, from your supervisor, and from anybody who might have filled it. A gap you can see gets closed. A gap dressed to look full does not.</p>

<blockquote>WATCH-OUT: If your first instinct on a shelf is to straighten it, you are doing the third-most-valuable job first. Look for what is missing before you look at what is untidy.</blockquote>

<p><b>How to tell whether a section has been done properly.</b> Look at the back of the shelf rather than the front. Filled properly, the back is full and the front is what has been sold from. Faced without filling, the front row is neat and there is nothing behind it — which is exactly what a customer discovers when they take the last one, and it is what a supervisor checks when they want to know whether the work is real.</p>

<p><b>The one case where facing genuinely comes first.</b> Ten minutes before the shop opens, or before somebody senior walks the floor, when there is not time to do both properly. That is a legitimate judgement and worth naming so it does not feel like a betrayal of the rule. What matters is that it is the exception you can articulate rather than the default you drifted into — and that the filling happens afterwards rather than instead.</p>"""
, [
 C("When time is short, the order is:",
   ["Face, fill, rotate", "Fill first, rotating as you go",
    "Rotate, face, fill", "Whatever the section needs"], 1,
   "A full shelf that is slightly untidy sells; a beautifully faced shelf with holes does not."),
 C("Pulling the last few items forward so the gap sits at the back is:",
   ["Good practice", "Hiding the gap from everybody who could fill it",
    "Required facing", "Acceptable temporarily"], 1,
   "A gap you can see gets closed; a gap dressed to look full does not."),
 C("Rotating belongs at the moment of filling because:",
   ["Policy requires it", "It costs nothing then and a write-off later",
    "It is faster", "Dates are checked then"], 1,
   "It happens while filling or it does not happen at all.")]),

("Reading a shelf in ten seconds", 10, """<p>You walk past a section fifty times a shift. Most people see it as scenery. Learning to read it takes a week and then costs nothing forever.</p>

<p><b>What you are looking for, in order of value.</b></p>

<p><b>Holes.</b> Actual empty facings. Obvious, and still missed by people whose eyes have stopped registering them after a month in the same aisle.</p>

<p><b>Thin spots.</b> A facing down to one or two units. This is the more valuable read, because a hole is a sale already lost while a thin spot is a sale about to be lost that you can still prevent.</p>

<p><b>Things in the wrong place.</b> An item on the wrong shelf is invisible to the customer looking for it and confusing to the one who finds it. Customers move things constantly; so do staff in a hurry.</p>

<p><b>Labels that do not match.</b> A price label with a different product above it is the single commonest cause of a dispute at the till, and it is a ten-second fix that prevents an argument somebody else will have.</p>

<p><b>Anything that should not be there.</b> Damaged packaging, something leaking, a date that has passed. Module 4's territory, spotted here.</p>

<p><b>The habit that makes it automatic.</b> Walk your section once at the start of the shift, deliberately, looking for those five. After a fortnight you will notice them while walking past on other errands, which is the point — the goal is not a daily inspection but eyes that register a gap without being told to look.</p>

<p><b>The trap of familiarity.</b> The longer you work a section the less you see it. People who have been in the same aisle for six months walk past holes daily without registering them, which is not carelessness — it is how attention works. The counter is to look at it as a customer would occasionally: stand back, at the end of the aisle, and look at the whole thing rather than the part in front of you.</p>

<blockquote>IMPLEMENTATION TIP: Once a week, walk somebody else's section and tell them what you found. It is easier to see gaps in an aisle you do not work, they will find yours, and it costs the pair of you four minutes.</blockquote>

<p><b>The time of day the reading matters most.</b> Late afternoon, before the evening trade. The shelf has taken a full day of selling, the morning fill is long gone, and the people coming in after work will meet whatever is left. Most branches fill in the morning because that is when deliveries land, which means the shelf is at its worst precisely when a large share of the day's customers arrive. A ten-minute pass at four o'clock is worth more than an hour at nine.</p>

<p><b>What to do with what you find when you have no time to fix it.</b> Write it down. A list of six gaps handed to whoever has a quieter hour is worth far more than four of them fixed and two forgotten. The reading and the fixing do not have to be done by the same person or in the same hour, and treating them as separable is what makes the ten-second read possible at all during a busy shift.</p>"""
, [
 C("More valuable than spotting a hole is spotting:",
   ["A wrong label", "A thin spot",
    "A misplaced item", "Damage"], 1,
   "A hole is a sale already lost; a thin spot is one you can still prevent."),
 C("A price label with a different product above it is:",
   ["A minor untidiness", "The commonest cause of a dispute at the till",
    "The supervisor's job", "Corrected at the count"], 1,
   "A ten-second fix that prevents an argument somebody else will have."),
 C("People who have worked the same aisle for months walk past holes because:",
   ["They are careless", "That is how attention works",
    "They are too busy", "The holes are small"], 1,
   "The counter is to stand back at the end of the aisle and look as a customer would.")]),

("The stockroom is not a shop", 10, """<p>Stock in the back earns nothing. Everything about how the stockroom is kept should serve one purpose: making it fast to find something and get it onto the floor.</p>

<p><b>Why it degrades, and it always degrades.</b> A delivery arrives during a busy hour, gets put wherever there is space, and the person who did it knows where things are. Two shifts later they are off and nobody else does. Nothing dramatic happened; the stockroom simply stopped being searchable, and from that point every gap takes five minutes to fill instead of one.</p>

<p><b>What good looks like, and it is not tidiness.</b> Things in the same place as last time. Fast lines nearest the door. Nothing stacked in front of anything else. A pallet broken down rather than left as a wall. Nobody needs it beautiful; everybody needs it predictable.</p>

<p><b>The rule that does most of the work.</b> If you cannot get to it in under a minute, it might as well not be there. Which means a case of something buried behind three others is functionally out of stock — and that is cause three from chapter 2, wearing a disguise. A great deal of what looks like a supply problem is actually a stockroom problem.</p>

<p><b>Putting a delivery away when you are busy.</b> This is where it goes wrong, and the honest advice is: put the fast lines away properly and leave the rest in one identified place rather than scattered. One labelled pile somebody can search is much better than eleven items distributed by convenience. What must not happen is chilled or frozen goods left out because there was no time — that is not untidiness, it is a write-off and possibly a safety matter.</p>

<p><b>And the check nobody does.</b> Before saying "we are out of it" to a customer, actually look. Not remember — look. Staff say we are out several times a day about things that are in the building, because they are recalling this morning rather than checking now. The ten seconds costs less than the sale.</p>

<blockquote>WORTH KNOWING: In most branches, a meaningful share of what customers are told is out of stock is physically in the building at the time. That is the single most recoverable thing in this whole module.</blockquote>

<p><b>What to do when the stockroom genuinely is chaos.</b> It happens — after a big delivery, during a refit, when a branch is short-staffed for a fortnight. Do not try to fix all of it, because you will not finish and a half-sorted stockroom is worse than a consistently bad one. Take your own section, put it in one place, and leave the rest. A single searchable area inside a chaotic stockroom is a real improvement; an ambitious reorganisation abandoned on Thursday is not.</p>"""
, [
 C("A case buried behind three others is:",
   ["Available stock", "Functionally out of stock",
    "Reserve stock", "A tidiness problem"], 1,
   "If you cannot get to it in under a minute, it might as well not be there."),
 C("Putting a delivery away when busy, the right compromise is:",
   ["Scatter it wherever there is space", "Fast lines away properly, the rest in one identified place",
    "Leave it all until quiet", "Put it on the shop floor"], 1,
   "One labelled pile somebody can search beats eleven items distributed by convenience."),
 C("Before telling a customer something is out of stock you should:",
   ["Recall the morning's delivery", "Actually look",
    "Ask a colleague", "Check the system"], 1,
   "Staff say we are out several times a day about things that are in the building.")]),

("Promotions, ends and the things that sell themselves", 10, """<p>Some parts of a shop sell several times what the same product sells elsewhere in the building, and knowing which they are changes where you spend your effort.</p>

<p><b>The places that work.</b> The aisle ends, the area by the entrance, anything at eye level, and the space beside the till. A product moved from a middle shelf to an end can sell many times more without anything else changing — same price, same product, same customers.</p>

<p><b>Which produces the rule.</b> Never let a promotional end run empty. It is the most expensive gap in the building because it is the fastest-selling space, and it empties faster than anywhere else for exactly that reason. If you check one thing an hour on a busy Saturday, check the ends.</p>

<p><b>What a promotion needs to actually work.</b> Stock, obviously. The right price displayed, which is where most promotions fail — a promotional price on the shelf and the old price at the till produces a dispute every single time and, worse, teaches customers that your prices cannot be trusted. And a sign that is still true: a promotion sign left up after the promotion ends is not untidiness, it is telling customers a price you are not going to charge.</p>

<p><b>The judgement about the till area.</b> That space sells because people are stationary and slightly bored. It works with small, cheap, familiar items and does not work with anything requiring a decision. That is not your call to make, but noticing what moves there and mentioning it is genuinely useful — the person who chooses it is rarely the person who watches it.</p>

<p><b>And the thing nobody explains to new staff.</b> Where products go is largely decided elsewhere, and there are usually reasons — supplier agreements, category plans, deliberate placement of high-margin lines at eye level. Which means moving things around on your own initiative is not helpful even when your idea is better. Notice, suggest, and leave the layout alone unless it is plainly wrong.</p>

<blockquote>IMPLEMENTATION TIP: On a busy day, walk the ends and the entrance display every hour. It takes ninety seconds and it protects the fastest-selling space in the shop, which is the highest return on ninety seconds available anywhere on the floor.</blockquote>

<p><b>And the pricing point that catches everybody eventually.</b> When a promotion ends, the stock does not disappear — it usually goes back to its normal shelf at its normal price. Somebody has to move it and somebody has to take the sign down, and if the first happens without the second you have a promotion sign over an empty space. Both halves are one job, and the half people forget is the sign.</p>"""
, [
 C("The most expensive gap in the building is:",
   ["The middle of an aisle", "A promotional end running empty",
    "A low shelf", "The stockroom"], 1,
   "It is the fastest-selling space, which is exactly why it empties fastest."),
 C("A promotional price on the shelf and the old price at the till:",
   ["Is corrected at the till", "Produces a dispute every time and teaches customers your prices cannot be trusted",
    "Is a minor error", "Only matters on large items"], 1,
   "Which is where most promotions actually fail."),
 C("Moving products around on your own initiative is:",
   ["Encouraged if it improves sales", "Not helpful even when your idea is better",
    "Fine within your section", "Expected of experienced staff"], 1,
   "Placement is usually decided elsewhere for reasons including supplier agreements and category plans.")]),

("Saying what you see", 10, """<p>You will notice things nobody else in the business can. What you do with that is the difference between a person who fills shelves and a person who gets promoted.</p>

<p><b>What is worth reporting, and it is a short list.</b> A line that has been out more than a day or two. A line customers have asked for twice. A delivery that arrived short. Something selling far faster than usual. A price that looks wrong. Damage or dates found on the shelf rather than in the stockroom.</p>

<p><b>What makes a report useful rather than a complaint.</b> Specifics. <i>We are always out of things</i> is a mood and cannot be acted on. <i>The 500ml has been out since Tuesday and two customers asked for it today</i> is a fact somebody can do something with — it names the line, the duration and the demand, which is exactly what an ordering decision needs.</p>

<p><b>Say it once, properly, and let it go.</b> Report it, and if nothing happens, mention it a second time and then stop. The frustrating truth is that some of it genuinely cannot be fixed — a supplier has stopped making it, a line is being discontinued, the money is not there this month. You will rarely be told which. Reporting is your part; the decision is not, and treating a non-response as a personal slight is the fastest route to becoming somebody who stops reporting at all.</p>

<p><b>Where to put it.</b> Whatever your branch uses — a book, a board, a message, telling the supervisor. If there is nothing, tell somebody verbally at a moment they can actually hear it, which is not during the Saturday rush.</p>

<p><b>The compounding effect.</b> Somebody who reports specifically and consistently for three months becomes the person the supervisor asks. That is how informal responsibility starts, and module 1 said it: people are promoted into responsibility they have already been holding. This is the cheapest way to start holding some.</p>

<blockquote>IMPLEMENTATION TIP: Keep a note in your pocket during the shift — line, what happened, how many asked. At the end, three lines to your supervisor. It takes a minute and it is more useful information than most branches receive in a week.</blockquote>

<p><b>The report that is worth more than all the others.</b> A customer asked for something you do not stock at all. Everything else on the list is about executing the existing range; this one is about what the range should be, and it is the only information in the building that cannot be found any other way. Nobody's system records a request for a product the shop has never carried. Three people asking for the same thing in a month is a genuine finding, and it will reach nobody unless somebody writes it down.</p>

<p><b>Who to tell, when it is not your supervisor.</b> Some things belong elsewhere: a repeated pricing error is worth mentioning to whoever maintains prices, a supplier consistently delivering short concerns whoever receives deliveries, a safety matter goes wherever your branch says immediately. Sending everything to one person because they are the person you know is how useful information gets stuck. Ask once who deals with what, and the answer serves for years.</p>"""
, [
 C("'We are always out of things' is:",
   ["A fair summary", "A mood that cannot be acted on",
    "A useful escalation", "Better said to the manager"], 1,
   "Naming the line, the duration and the demand is what an ordering decision needs."),
 C("If a reported gap is not acted on, you should:",
   ["Escalate repeatedly", "Mention it a second time and then stop",
    "Stop reporting", "Raise it formally"], 1,
   "Some of it genuinely cannot be fixed, and you will rarely be told which."),
 C("Reporting specifically and consistently for three months makes you:",
   ["Seen as difficult", "The person the supervisor asks",
    "Eligible for training", "A section owner"], 1,
   "Which is how informal responsibility starts, and people are promoted into responsibility they already hold.")]),

("Okelewo Stores: Ada takes the aisle", 10, """<p>Five months in, Ada was given the household aisle — not a promotion, no more money, just her section to keep. What she did with it took about fifteen minutes a shift.</p>

<p><b>Week one — she found out what was actually happening.</b> Every gap she met, she diagnosed against the four causes before doing anything. The result surprised her: most were cause three. The stock was in the building. The aisle was not under-ordered; it was under-filled.</p>

<p><b>Week two — she changed her own order of work.</b> She had been facing first because it looked like progress. She started filling first, rotating as she went, and facing only after. The aisle looked slightly worse for about three days and then looked better than it ever had, because a full shelf faced roughly beats a half-empty shelf faced beautifully.</p>

<p><b>Week three — the stockroom.</b> She spent one quiet afternoon putting the household stock in one place, fast lines nearest the door, nothing stacked in front of anything. Nobody asked her to. Filling a gap went from about four minutes to under one, which is the whole reason the gaps started getting filled.</p>

<p><b>Week four — the pocket note.</b> Three lines to the supervisor at the end of each shift. The one that mattered: a particular bleach out for five days, four customers asking. It turned out nobody had ordered it because the branch's order sheet had it on a monthly cycle and it was selling weekly. That was fixed in one conversation and had been costing the branch quietly for months.</p>

<p><b>What the numbers did.</b> Nobody measured the aisle before, so there is no clean figure — which is honest and worth saying rather than inventing one. What the supervisor noticed was that customers stopped asking her about household lines, because they were finding them.</p>

<p><b>The part worth copying.</b> None of the four weeks required authority, budget or permission. The largest single win — the bleach — came from a note in a pocket. And the thing that made everything else possible was the quiet afternoon in the stockroom, which is the least visible work in the entire module and the reason the rest of it functioned.</p>

<p><b>What did not happen, and is worth saying.</b> Nobody gave Ada the aisle as a reward, nobody checked her progress, and for the first six weeks nobody mentioned it at all. The recognition came later and indirectly — through customers not asking, and through the supervisor starting to ask her about household lines rather than telling her. If you take on a section expecting to be noticed quickly you will be disappointed in about a fortnight and stop. The honest version is that it takes a couple of months and then it is obvious.</p>

<blockquote>IMPLEMENTATION TIP: If you take one thing from this chapter, take the stockroom afternoon. It is invisible, nobody will thank you, and it converts every future gap from a four-minute job into a one-minute job for as long as it lasts.</blockquote>"""
, [
 C("Diagnosing every gap against the four causes showed Ada that her aisle was:",
   ["Under-ordered", "Under-filled",
    "Over-stocked", "Badly laid out"], 1,
   "Most gaps were cause three: the stock was in the building."),
 C("After she started filling before facing, the aisle:",
   ["Improved immediately", "Looked slightly worse for about three days, then better than ever",
    "Looked untidy permanently", "Was unchanged"], 1,
   "A full shelf faced roughly beats a half-empty shelf faced beautifully."),
 C("The bleach had been out for five days because:",
   ["The supplier had stopped it", "It was on a monthly order cycle and selling weekly",
    "Nobody had filled it", "It was misplaced"], 1,
   "Found by a note in a pocket, and fixed in one conversation after costing the branch quietly for months.")]),

("Review, and the four habits", 10, """<p>The module in short, then what to actually do with it.</p>

<p><b>The gap is the biggest number you can influence.</b> It costs more than theft, damage and expiry in most branches and it produces no record at all. One line selling thirty a day, out for three days, is ₦27,000 of margin gone.</p>

<p><b>Four causes, two of them yours.</b> Never ordered, ordered and late, in the building and not out, on the shelf and not findable. The third is the largest and it is entirely within your control. Diagnose before acting.</p>

<p><b>Three jobs, not one.</b> Fill, face, rotate. Fill first, rotate while you fill, face afterwards. Never dress a gap to look full.</p>

<p><b>Read the shelf in ten seconds.</b> Holes, thin spots, things in the wrong place, labels that do not match, anything that should not be there. Thin spots are worth more than holes because the sale has not been lost yet.</p>

<p><b>The stockroom exists to be searched, not admired.</b> If you cannot reach it in a minute it is functionally out of stock. And look before saying you are out.</p>

<p><b>Protect the ends.</b> The fastest-selling space empties fastest and is the most expensive gap in the building.</p>

<p><b>Say what you see, specifically.</b> The line, how long, how many asked. Once, properly, then let it go.</p>

<p><b>The four habits, in the order they pay.</b> First: fill before you face, every time. Second: check your ends and entrance hourly on a busy day. Third: look before telling a customer you are out. Fourth: three specific lines to your supervisor at the end of a shift.</p>

<p><b>And the one afternoon.</b> If you get a quiet afternoon, spend it in the stockroom on your own section. Nothing else in this module produces a bigger return, and nobody will ever notice you did it.</p>

<blockquote>WORTH KNOWING: The next module is stock and dates — where things come from, why rotation matters, and what to do with damage and expiry. It is the other half of this one: this module was about the shelf being full, the next is about everything on it being fit to sell.</blockquote>

<p><b>One sentence to carry out of this module.</b> The shop cannot sell what is not on the shelf, and it cannot sell what a customer cannot find — and both of those are decided by somebody standing in the aisle rather than by anybody making decisions elsewhere. That is unusual in a job at this level, and it is the strongest reason to take this module more seriously than its subject matter suggests.</p>

<p><b>What the four habits are not.</b> They are not a checklist to be completed and reported. Nobody is going to inspect them, and three of the four are invisible to anybody but you. They are habits precisely because the alternative — remembering to care about availability when you happen to think of it — does not survive a busy fortnight. A habit runs on the days you are tired, which are the days the shelf most needs it.</p>

<p><b>And how long before any of this shows.</b> The hourly end check pays the same day. Filling before facing pays within a week. The stockroom afternoon pays from the next shift onward and keeps paying. The reporting takes about three months to change anything, because it has to accumulate before a pattern is visible to whoever orders. Knowing which is which stops you abandoning the slow one for producing nothing in its first fortnight.</p>"""
, [
 C("The four habits begin with:",
   ["Checking the ends hourly", "Filling before facing, every time",
    "Reporting three lines", "The stockroom afternoon"], 1,
   "Stated in the order they pay rather than the order they appear."),
 C("The quiet afternoon in the stockroom is described as producing:",
   ["A visible improvement", "The biggest return in the module, unnoticed",
    "A tidiness benefit", "A one-off gain"], 1,
   "It converts every future gap from a four-minute job into a one-minute job."),
 C("Thin spots are worth more attention than holes because:",
   ["They are easier to fix", "The sale has not been lost yet",
    "They look worse", "They indicate demand"], 1,
   "A hole is a sale already lost; a thin spot is one you can still prevent.")]),
]


QUESTIONS = [
 Q("When a customer cannot find something, the shop's figures record:", ["The lost sale", "What was sold, not what was wanted", "A stock-out event", "Nothing until the count"], 1,
   "Which is why the gap is the strangest loss in retail.", "Ch1 §1", "The gap"),
 Q("Unlike theft, damage and expiry, an empty shelf:", ["Is cheaper", "Produces no record at all", "Is reported daily", "Shows in the accounts"], 1,
   "Everything else that costs a shop money leaves a trace.", "Ch1 §3", "The gap"),
 Q("Ninety lost sales at ₦300 margin comes to:", ["₦2,700", "₦27,000", "₦9,000", "₦270,000"], 1,
   "From one gap on one product over three days.", "Ch1 §4", "The gap"),
 Q("A regular is lost more often by availability than by:", ["Price", "Service", "Location", "Range"], 1,
   "They stop assuming you will have it, and move the whole basket without announcing it.", "Ch1 §5", "The gap"),
 Q("The information about which lines are out mostly exists:", ["In the stock system", "On the floor, with the people who saw it", "In the ordering data", "At head office"], 1,
   "Which is why many managers cannot name last month's worst out-of-stock line.", "Ch1 §7", "The gap"),
 Q("The four causes of a gap are: never ordered, ordered and late, on the shelf but unfindable, and:", ["Stolen", "In the building and not on the shelf", "Discontinued", "Over-sold"], 1,
   "The third is the largest in most branches.", "Ch2 §5", "Four causes"),
 Q("Causes one and two are:", ["Yours to fix", "Somebody else's decision, and worth reporting", "Not worth mentioning", "The supervisor's fault"], 1,
   "The person who orders often does not know a delivery came short unless somebody says so.", "Ch2 §3", "Four causes"),
 Q("The diagnosis when a shelf is empty starts with:", ["Telling the customer", "Checking the stockroom", "Reporting it", "Checking the system"], 1,
   "If it is there, it is cause three: bring it.", "Ch2 §8", "Four causes"),
 Q("Fixing causes three and four reliably means the remaining gaps are:", ["Unavoidable", "Genuine supply problems rather than the shop failing to put its own stock out", "The buyer's fault", "Seasonal"], 1,
   "Two of the four are yours.", "Ch2 §7", "Four causes"),
 Q("The three shelf jobs are filling, facing and:", ["Counting", "Rotating", "Pricing", "Cleaning"], 1,
   "Different purposes, and the visible one is the least valuable.", "Ch3 §2", "Three jobs"),
 Q("The job that makes money and gets skipped when time is short is:", ["Facing", "Filling", "Rotating", "Cleaning"], 1,
   "An empty shelf looks like less work than an untidy one.", "Ch3 §3", "Three jobs"),
 Q("Skipping rotation is what turns:", ["Tidy shelves untidy", "Stock into waste", "Sales into returns", "Facings into gaps"], 1,
   "It takes almost no extra time if done while filling.", "Ch3 §5", "Three jobs"),
 Q("A shelf that looks tended is:", ["A cosmetic matter", "Sold from more and stolen from less, measurably", "Only relevant to inspections", "Less important than price"], 1,
   "The argument about order is not an argument about value.", "Ch3 §7", "Three jobs"),
 Q("Facing an empty shelf so the gap sits at the back:", ["Improves appearance acceptably", "Hides the gap from everybody who could fill it", "Is standard practice", "Helps the count"], 1,
   "A gap you can see gets closed.", "Ch3 §8", "Three jobs"),
 Q("The five things to read on a shelf begin with holes and:", ["Prices", "Thin spots", "Dust", "Facings"], 1,
   "A thin spot is a sale about to be lost that you can still prevent.", "Ch4 §4", "Reading the shelf"),
 Q("An item on the wrong shelf is:", ["A tidiness issue", "Invisible to the customer looking for it", "Corrected at the count", "Rarely a problem"], 1,
   "Customers move things constantly; so do staff in a hurry.", "Ch4 §5", "Reading the shelf"),
 Q("The counter to familiarity blindness is to:", ["Work a different section", "Stand back at the end of the aisle and look as a customer would", "Check a list", "Ask a colleague"], 1,
   "The longer you work a section the less you see it.", "Ch4 §8", "Reading the shelf"),
 Q("Walking somebody else's section weekly works because:", ["It shares the workload", "Gaps are easier to see in an aisle you do not work", "It is required", "It builds product knowledge"], 1,
   "They will find yours, and it costs the pair of you four minutes.", "Ch4 §9", "Reading the shelf"),
 Q("A stockroom degrades because:", ["Staff are careless", "A delivery gets put away by somebody who knows where things are, and then is off shift", "It is too small", "Deliveries are too frequent"], 1,
   "Nothing dramatic happens; it simply stops being searchable.", "Ch5 §3", "The stockroom"),
 Q("Good stockroom practice is described as predictable rather than:", ["Efficient", "Beautiful", "Labelled", "Full"], 1,
   "Things in the same place as last time; fast lines nearest the door.", "Ch5 §4", "The stockroom"),
 Q("The one-minute rule means stock you cannot reach quickly is:", ["Reserve stock", "Functionally out of stock", "Fine where space is tight", "The stockroom's problem"], 1,
   "Much of what looks like a supply problem is a stockroom problem.", "Ch5 §5", "The stockroom"),
 Q("What must never be left out when a delivery cannot be put away is:", ["Fast lines", "Chilled or frozen goods", "Promotional stock", "Heavy items"], 1,
   "That is a write-off and possibly a safety matter rather than untidiness.", "Ch5 §7", "The stockroom"),
 Q("Staff say 'we are out' several times a day about things that are:", ["Discontinued", "In the building at the time", "On order", "In another branch"], 1,
   "Because they are recalling this morning rather than checking now.", "Ch5 §8", "The stockroom"),
 Q("A product moved from a middle shelf to an aisle end can sell:", ["Slightly more", "Many times more, with nothing else changed", "The same", "Less"], 1,
   "Same price, same product, same customers.", "Ch6 §2", "Promotions"),
 Q("On a busy Saturday, the one thing to check hourly is:", ["The till area", "The ends", "The stockroom", "The entrance only"], 1,
   "The fastest-selling space empties fastest.", "Ch6 §3", "Promotions"),
 Q("A promotion sign left up after the promotion ends is:", ["Untidiness", "Telling customers a price you will not charge", "Harmless", "The supervisor's job"], 1,
   "A sign that is still true is part of what a promotion needs to work.", "Ch6 §5", "Promotions"),
 Q("The till area sells because customers are:", ["In a buying mood", "Stationary and slightly bored", "Reminded by signage", "Ready to spend"], 1,
   "It works with small, cheap, familiar items and not with anything requiring a decision.", "Ch6 §6", "Promotions"),
 Q("Product placement is decided elsewhere for reasons including:", ["Staff preference", "Supplier agreements and category plans", "Stock levels", "Shelf size"], 1,
   "Which is why moving things on your own initiative is unhelpful even when your idea is better.", "Ch6 §7", "Promotions"),
 Q("A useful report names the line, the demand and:", ["The supplier", "How long it has been out", "The price", "The customer"], 1,
   "Specifics are what an ordering decision needs.", "Ch7 §3", "Reporting"),
 Q("After reporting a gap twice with no result, you should:", ["Escalate to the manager", "Stop", "Report weekly", "Raise it formally"], 1,
   "Some of it genuinely cannot be fixed and you will rarely be told which.", "Ch7 §4", "Reporting"),
 Q("Treating a non-response as a personal slight leads to:", ["Faster escalation", "Becoming somebody who stops reporting", "A useful conversation", "Better information"], 1,
   "Reporting is your part; the decision is not.", "Ch7 §4", "Reporting"),
 Q("A verbal report should be given:", ["Immediately, whatever is happening", "At a moment they can actually hear it", "In writing only", "At the end of the week"], 1,
   "Which is not during the Saturday rush.", "Ch7 §5", "Reporting"),
 Q("Consistent specific reporting is described as the cheapest way to:", ["Get noticed", "Start holding informal responsibility", "Improve the section", "Help the buyer"], 1,
   "People are promoted into responsibility they already hold.", "Ch7 §6", "Reporting"),
 Q("Ada's week one diagnosis showed her aisle was:", ["Under-ordered", "Under-filled", "Over-faced", "Badly sited"], 1,
   "Most gaps were cause three — the stock was in the building.", "Ch8 §2", "Ada's aisle"),
 Q("Switching to filling before facing made the aisle look:", ["Immediately better", "Slightly worse for three days, then better than ever", "Untidy", "Unchanged"], 1,
   "A full shelf faced roughly beats a half-empty shelf faced beautifully.", "Ch8 §3", "Ada's aisle"),
 Q("The stockroom afternoon changed the time to fill a gap from about four minutes to:", ["Two minutes", "Under one", "Three minutes", "Thirty seconds"], 1,
   "Which is the whole reason the gaps started getting filled.", "Ch8 §4", "Ada's aisle"),
 Q("The bleach had been out five days because the order sheet had it on:", ["A supplier hold", "A monthly cycle while it sold weekly", "Back order", "Discontinued status"], 1,
   "Fixed in one conversation after costing the branch quietly for months.", "Ch8 §5", "Ada's aisle"),
 Q("The chapter gives no clean before-and-after figure because:", ["The gain was small", "Nobody measured the aisle before", "It was seasonal", "The data was lost"], 1,
   "Which is honest and worth saying rather than inventing one.", "Ch8 §6", "Ada's aisle"),
 Q("What the supervisor noticed was that customers stopped:", ["Complaining", "Asking her about household lines", "Queueing", "Requesting alternatives"], 1,
   "Because they were finding them.", "Ch8 §6", "Ada's aisle"),
 Q("The largest single win in Ada's four weeks came from:", ["The stockroom", "A note in a pocket", "Better facing", "The supervisor"], 1,
   "Three specific lines at the end of each shift.", "Ch8 §7", "Ada's aisle"),
 Q("The habit that makes all the others work is:", ["Hourly end checks", "The stockroom afternoon", "Filling first", "Reporting"], 1,
   "It is the least visible work in the module and the reason the rest functioned.", "Ch8 §7", "Ada's aisle"),
 Q("The next module covers stock and dates, described as:", ["A separate subject", "The other half of this one", "An advanced topic", "The supervisor's territory"], 1,
   "This module was the shelf being full; the next is everything on it being fit to sell.", "Ch9 §10", "Review"),
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
    if len(LESSONS) != 9:
        raise SystemExit("ABORT: %d chapters, expected 9" % len(LESSONS))

    rebalance(QUESTIONS, "shopfloor:the_shelf:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:the_shelf:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    problems = []
    seen = set()
    for _t, _e, _h, ch in LESSONS:
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
        "title": "RF 3 — The Shelf",
        "desc": ("The largest loss in most branches and the one that appears in no report. "
                 "The four causes of a gap and which two are yours, why filling beats facing, "
                 "reading a shelf in ten seconds, why the stockroom is not a shop, protecting "
                 "the fastest-selling space, and how to report what you see so somebody can "
                 "act on it."),
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
