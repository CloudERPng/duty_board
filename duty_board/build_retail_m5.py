#!/usr/bin/env python3
"""Build 'Loss' into academy_retail_data.json.

Module 5 of Retail Leadership Essentials.

Deliberately does not repeat what is already in this track. Module 2 covered
what shrinkage is made of and how to read the number; module 3 covered receiving
as a cause of gaps. This module is about prevention and process design at branch
level — the physical branch, the count, waste and expiry, cash, the process gaps
where loss hides, and what a manager does in the hour they first suspect
somebody.

That last chapter is the one that matters most and is covered almost nowhere.
Managers destroy their own cases and damage innocent people in the first hour,
and they do it from urgency and a sense of responsibility rather than malice.

STANDS ALONE. No other module or track assumed.

Run from the app package directory:  python3 build_retail_m5.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "loss"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Designing a branch where loss is hard", 11, """<p>Most loss prevention is discussed as vigilance. Vigilance is exhausting, inconsistent, and fails on a busy Saturday. Design works whether or not anybody is paying attention, and it is largely free.</p>

<p><b>The principle: make the honest thing easy and the dishonest thing awkward.</b> Not impossible — a determined person will find a way. Awkward is enough, because most loss is opportunistic rather than planned, and opportunity is something a branch manager can remove.</p>

<p><b>The back door.</b> It is the largest single physical risk in most branches and it is usually propped open for ventilation, for a smoker, or because somebody is carrying boxes. A back door that is closed by default, opened deliberately, and visible from somewhere staff work removes a whole category of loss without a single conversation about trust.</p>

<p><b>Bins and packaging.</b> Goods leave in rubbish more often than managers expect. Flattening cartons, keeping bins away from stock, and emptying them at a time somebody is present costs nothing.</p>

<p><b>The stockroom that nobody can be alone in for an hour.</b> Not surveillance — arrangement. A stockroom that is visible, walked through, and where two people are usually present is a different environment from one at the end of a corridor that nobody enters between deliveries.</p>

<p><b>Keys and access.</b> Who can open, who can access the safe, who has the stockroom key, and whether that list is current. In most branches somebody who left months ago still appears on it, and nobody has looked.</p>

<p><b>High-value lines near the till or in a locked case</b>, not at the far end of the shop by the fire exit. Obvious, frequently overlooked, and worth reviewing whenever the range changes.</p>

<p><b>Where the manager is at the times that matter.</b> Opening, closing, delivery, cash-up. Not because staff need watching, but because those are the moments where a gap in the process becomes visible — and being present occasionally, unpredictably, at those times tells you more than any camera.</p>

<p><b>And the point that governs the whole module.</b> Every control here protects your honest staff as much as it constrains anybody else. A branch where nobody can be alone with the stock is a branch where nobody can be suspected of having been. That is worth saying out loud to your team, because otherwise controls read as accusations.</p>

<blockquote>IMPLEMENTATION TIP: Walk your branch once asking only one question: where could something leave without anybody seeing? The back door, the bins, the staff room, the delivery bay, the fire exit. Fixing the two worst answers usually costs nothing and takes an afternoon.</blockquote>

<p><b>And review it after any change to the branch.</b> A refit, a new range, a fire door relocated, a delivery bay reorganised — each can quietly reopen something you closed. The high-value line that sat by the till last year may now be beside the exit because a planogram changed centrally, and nobody who made that decision was thinking about loss. A walk after any physical change costs ten minutes and is the cheapest moment to catch it.</p>"""
, [
 C("The aim of physical design in loss prevention is to make the dishonest thing:",
   ["Impossible", "Awkward",
    "Detectable afterwards", "Punishable"], 1,
   "Most loss is opportunistic rather than planned, and opportunity is what a manager can remove."),
 C("Walking your branch for places something could leave unseen, the first thing to look at is:",
   ["The till area", "The back door",
    "The stockroom", "The fire exit"], 1,
   "Usually propped open for ventilation, a smoker, or somebody carrying boxes."),
 C("Controls should be explained to the team as protecting them, because otherwise they:",
   ["Are ignored", "Read as accusations",
    "Slow the work", "Require enforcement"], 1,
   "A branch where nobody can be alone with the stock is one where nobody can be suspected of having been.")]),

("A count that means something", 11, """<p>Most branches count stock and learn nothing, because the count is done by the people responsible for the stock, in a hurry, against a list showing what the system expects. That is not a count. It is a confirmation.</p>

<p><b>What makes a count worth doing.</b></p>

<p><b>Somebody other than the person responsible.</b> Rotating who counts what costs nothing and changes the quality of the number more than any instruction about accuracy. It also protects the person responsible, who can no longer be the only explanation for a difference.</p>

<p><b>Count blind where you can.</b> A sheet showing the expected quantity invites the counter to agree with it, especially when they are tired and the number is close. Counting without the expectation and comparing afterwards takes the same time and produces a genuinely independent number.</p>

<p><b>Count the things that matter more often than everything.</b> A full count twice a year tells you about the year. A weekly count of your forty highest-value or highest-risk lines tells you about this week, while you can still do something. Small and frequent beats large and rare for everything except the annual valuation.</p>

<p><b>Investigate the differences you find, at least sometimes.</b> A branch that counts, records a difference, adjusts and moves on has converted a signal into a bookkeeping entry. The adjustment is not the end of the process — it is the beginning of a question about why.</p>

<p><b>What a difference is telling you.</b> Concentrated in one category or one location points at a specific cause — a process, a shelf, a person, a supplier. Spread thinly everywhere points at counting, receiving or system error. The pattern is more informative than the total, and most branches only ever look at the total.</p>

<p><b>And the count that should worry you.</b> Differences that are always small and always in your favour. Genuine counting produces differences in both directions, of varying size, because real error is random. A tidy result sustained over months is more often a count being adjusted to agree with the system than a branch losing nothing.</p>

<blockquote>WATCH-OUT: A count sheet pre-printed with expected quantities is the commonest way a branch counts itself into a comfortable answer. It takes no longer to count blind, and the number you get is worth something.</blockquote>

<p><b>What to do about a difference you cannot explain.</b> Record it as unexplained rather than assigning it a plausible cause. A branch that attributes every difference to damage or to miscounting has removed its own ability to see a pattern, because everything now has a reason and nothing is outstanding. Unexplained is a legitimate category, it should not be empty, and the size of it over a quarter tells you how well your other records are working.</p>"""
, [
 C("A count sheet pre-printed with the expected quantity invites the counter to:",
   ["Work faster", "Agree with it, particularly when tired and the number is close",
    "Check twice", "Record variances"], 1,
   "Counting blind takes the same time and produces a genuinely independent number."),
 C("Differences that are always small and always favourable suggest:",
   ["Tight control", "A count being adjusted to agree with the system",
    "Low shrinkage", "Accurate receiving"], 1,
   "Real error is random and produces differences in both directions, of varying size."),
 C("Rotating who counts protects the person responsible because they:",
   ["Have less work", "Can no longer be the only explanation for a difference",
    "Learn other areas", "Are supervised"], 1,
   "The control that constrains also clears.")]),

("Waste, damage and expiry", 11, """<p>Waste is the loss branches accept as inevitable, and a substantial part of it is not. It differs from theft in one important way: it is entirely visible, entirely local, and nobody has to be accused of anything.</p>

<p><b>Where it comes from.</b> Stock ordered in quantities the branch cannot sell before it expires. Poor rotation, so new stock is put in front of old. Damage in handling — cases dropped, goods stacked badly, items handled repeatedly because the stockroom is disorganised. And chilled or frozen lines lost to a power interruption or a door left open.</p>

<p><b>Rotation is the cheapest fix in retail and the most consistently neglected.</b> Filling from the front takes ten seconds longer and prevents most expiry loss. It is neglected because it takes ten seconds longer, every time, on a busy afternoon — which means it is a habit problem rather than a knowledge problem, and habits are built by explaining the cost rather than by repeating the instruction.</p>

<p><b>Mark down before it expires, not after.</b> A line three days from expiry sold at half price recovers half. The same line two days later recovers nothing and costs you the disposal. Most branches discover expiry at the point of writing it off, which is the one moment nothing can be done — a weekly walk of short-dated stock turns a write-off into a markdown.</p>

<p><b>Record waste when it happens, by reason.</b> Not reconstructed at month end from memory. Expiry, damage in handling, damage on delivery, customer damage, power failure. Five categories, recorded at the time, and within a quarter you can see which one is actually costing you — and they need entirely different fixes.</p>

<p><b>Power deserves specific mention in this market.</b> Chilled and frozen loss to an outage is a real and recurring cost, and it is partly predictable. Knowing what an hour without power costs you in stock terms is what turns a generator or a fuel budget from an expense into an arithmetic question — and it is the kind of number nobody has ever produced for the person who approves the spend.</p>

<p><b>And the waste that hides.</b> Goods damaged in handling are sometimes quietly disposed of rather than recorded, because recording feels like reporting yourself. A branch where recording damage is treated as normal learns what its handling actually costs; a branch where it is treated as a failure learns nothing and keeps paying.</p>

<blockquote>IMPLEMENTATION TIP: Walk your short-dated stock once a week and mark down anything within a few days of expiry. It takes twenty minutes, it converts write-offs into partial recovery, and most branches have never done it deliberately because expiry is discovered rather than looked for.</blockquote>

<p><b>The ordering connection nobody makes.</b> Persistent expiry loss on a line usually means the order quantity is wrong for how fast that line actually sells, not that staff are careless. Marking down repeatedly treats the symptom; changing the order size treats the cause. Where the same line is marked down every month, the fix belongs in the ordering routine rather than in the rotation habit, and it is worth checking which of the two you are actually dealing with before instructing anybody.</p>"""
, [
 C("A line three days from expiry, marked down, recovers half. Two days later it:",
   ["Recovers a third", "Recovers nothing and costs you the disposal",
    "Can be returned", "Recovers the same"], 1,
   "Most branches discover expiry at the point of writing it off, which is the one moment nothing can be done."),
 C("Your team knows to rotate stock and does not do it consistently. The reason is that it:",
   ["Is poorly understood", "Takes ten seconds longer, every time, on a busy afternoon",
    "Needs more training", "Belongs to somebody else"], 1,
   "A habit problem rather than a knowledge problem, so explaining the cost works better than repeating the instruction."),
 C("Where recording damage is treated as reporting yourself, a branch:",
   ["Records less and loses less", "Learns nothing and keeps paying",
    "Improves handling", "Reduces write-offs"], 1,
   "Recording waste at the time, by reason, is what shows which of five causes is actually costing you.")]),

("Cash", 11, """<p>Cash is the one thing in a branch that is worth exactly its face value to anybody who takes it, cannot be traced once gone, and passes through the hands of your most junior staff all day.</p>

<p><b>The principle that governs all of it: cash should always be somebody's responsibility, and only one person's at a time.</b> Every point where that breaks — a drawer two people use, a float handed over without counting, a bag left in the office — is a point where a loss cannot be attributed and therefore cannot be resolved.</p>

<p><b>Counting at handover, both ways.</b> The person taking a drawer counts what they receive; the person handing it back counts what they hand over. Both counts recorded. Without them a shortage belongs to two shifts and can be assigned to neither, which protects nobody and resolves nothing.</p>

<p><b>Keep the drawer low.</b> Excess cash lifted to the safe during the day, at unpredictable times, by a named person. It reduces what is exposed and it removes the situation where a till holds more than anybody has counted since morning.</p>

<p><b>Banking.</b> Regular, but not so regular that it is a schedule anybody outside can learn. Two people where the amounts justify it. And the trip itself is the point of highest risk in the whole cash process — worth thinking about properly rather than treating as an errand.</p>

<p><b>Reconcile daily and investigate small differences.</b> A branch that only investigates large variances is teaching anybody who is inclined exactly what the threshold is. Small and persistent matters more than one large and explained.</p>

<p><b>Differences in both directions.</b> An overage is a process failure just as a shortage is — it means somebody was charged wrongly, or change was given short, and a customer paid for it. A branch that celebrates overages and investigates shortages is only looking at half its errors.</p>

<p><b>The manager's own habits set the standard.</b> Petty cash taken without a note, the safe left open during the count, a float borrowed and replaced later. Staff observe this precisely and conclude, reasonably, that the rules describe what is written rather than what is done — and once that conclusion is drawn it applies to every rule in the branch, not only the cash ones.</p>

<blockquote>WATCH-OUT: The most damaging thing a manager can do with cash is create a situation nobody can be cleared of. A drawer shared between two people, a float handed over uncounted, a safe several people can open — each of these means that when something does go missing, every one of those people is under suspicion and none can be exonerated.</blockquote>

<p><b>The cash conversation to have before anything goes wrong.</b> Tell your team plainly how cash is handled and why: that counts at handover exist so a difference belongs to one shift, that lifting to the safe reduces what anybody is carrying responsibility for, and that a shortage will be looked at as a process question first. A team that knows the rules and the reasoning reports a difference immediately. A team that fears the response finds a way to make the drawer balance, which is the outcome that costs most and is hardest to detect.</p>"""
, [
 C("Two cashiers share one drawer and it comes up short. The consequence is:",
   ["A shared responsibility", "Both are under suspicion and neither can be cleared",
    "A training matter", "An acceptable variance"], 1,
   "Cash should be somebody's responsibility, and only one person's at a time."),
 C("A branch that investigates only large variances is teaching anybody inclined:",
   ["That control is tight", "Exactly what the threshold is",
    "That accuracy matters", "To report differences"], 1,
   "Small and persistent matters more than one large and explained."),
 C("A till overage should be treated as:",
   ["Good news", "A process failure — somebody was charged wrongly or given short change",
    "An offsetting entry", "A rounding effect"], 1,
   "A branch celebrating overages and investigating shortages is looking at half its errors.")]),

("Where loss hides in the process", 11, """<p>The physical routes matter, and the larger losses in a well-run branch usually go out through legitimate processes used wrongly. Each of these is a normal, necessary function that leaves a specific trace when misused.</p>

<p><b>Refunds and returns.</b> A refund with no original sale is money leaving against nothing. The control is simple and absolute — no receipt or record, no refund — and where a system requires the original transaction to be found, that route closes entirely. What a manager watches is the pattern: refunds concentrated on one person, one time of day, or one payment method.</p>

<p><b>Voids and cancelled sales.</b> A sale rung up, cash taken, and the transaction cancelled leaves the customer with goods, the branch with no record, and the money unaccounted. A void rate that is far above the branch's normal, concentrated on one person, is the pattern worth looking at — not any individual void, which is nearly always innocent.</p>

<p><b>Discounts.</b> Given to friends, given to nobody and pocketed as the difference, or given habitually to avoid an argument. The reason recorded against each is what turns a large discount total into an answerable question.</p>

<p><b>Staff purchases.</b> Legitimate and worth having, and the point at which staff handle their own transactions. The rule that solves it is that nobody rings up their own purchase, and it costs nothing.</p>

<p><b>Damages and write-offs.</b> A category where goods leave with a reason attached, and therefore a category worth a second signature above a value. Write-offs that cluster around one person or one line deserve a look.</p>

<p><b>The pattern rule that applies to all of them.</b> No single instance means anything. Every one of these is a normal transaction that happens dozens of times a week for good reasons. What is informative is concentration — the same person, the same hour, the same line, repeatedly, against what the rest of the branch does. A manager who reacts to one void will be wrong nearly every time and will have taught their team that ordinary work attracts suspicion.</p>

<p><b>And the arithmetic worth knowing.</b> These processes handle small amounts frequently, which is why they are attractive and why they are missed. A ₦3,000 loss twice a week is ₦312,000 a year, and it never once looks like a large number.</p>

<blockquote>IMPLEMENTATION TIP: Ask for refunds, voids, discounts and write-offs broken down by person and by hour, once a month. Look for concentration rather than volume. It takes ten minutes and it is the only way these processes become visible without watching anybody.</blockquote>

<p><b>Why looking at these monthly is itself a control.</b> A process that is known to be reviewed behaves differently from one that is not, whether or not anything is ever found. That is not a cynical point about deterrence — it is that people are more careful with a discount reason or a write-off note when they know somebody reads them, and the accuracy of the record improves for entirely honest reasons. The review improves the data even in the branches where nothing is wrong.</p>"""
, [
 C("A single void, taken on its own, is:",
   ["Suspicious", "Almost always innocent — concentration is what is informative",
    "A control failure", "Worth investigating"], 1,
   "A manager who reacts to one void will be wrong nearly every time and teaches the team that ordinary work attracts suspicion."),
 C("A ₦3,000 loss occurring twice a week amounts annually to:",
   ["₦31,000", "₦312,000", "₦72,000", "₦6,000"], 1,
   "These processes handle small amounts frequently, which is why they are attractive and why they are missed."),
 C("The rule that solves the staff purchase risk at no cost is:",
   ["A monthly limit", "Nobody rings up their own purchase",
    "Manager approval", "A separate account"], 1,
   "It is a legitimate and worthwhile arrangement; the control is simply who processes it.")]),

("When you suspect somebody", 11, """<p>This chapter is the one that matters most and is taught almost nowhere. What a manager does in the first hour after suspecting a member of their team determines whether anything can be established at all — and whether an innocent person is damaged.</p>

<p><b>Start from what makes this hard for you specifically.</b> You know this person. You hired them, or you work beside them daily. The instinct is either to dismiss the possibility or to confront it immediately, and both are wrong for the same reason: you are the least well placed person in the business to be objective about it.</p>

<p><b>Four rules, and each is broken routinely by decent managers acting from urgency.</b></p>

<p><b>Do not confront.</b> Not a hint, not a pointed question, not a change in how you speak to them. A conversation before the facts are established converts a possibility into a denial and a warning, and you get one first conversation.</p>

<p><b>Do not investigate alone.</b> Your judgement about somebody you work with is not reliable and will not look reliable afterwards. This is a moment to involve the person your business says to involve.</p>

<p><b>Do not discuss it with the team.</b> Not with your deputy, not with the person's colleague, not to ask whether anybody has noticed anything. It spreads within a day, it reaches the person concerned, and if you are wrong you have damaged somebody who did nothing.</p>

<p><b>Do preserve what you have.</b> Write down what you saw and when, keep the reports rather than assuming they will still be there, and note the date. Records change, and memory is not evidence.</p>

<p><b>Then tell one person — the one your business has said to tell.</b> Usually your own manager or whoever handles this centrally. Specifically not somebody who reports to you and not the person's colleague. If your business has never told you who that is, find out this week rather than at the moment you need it.</p>

<p><b>What you must not conclude.</b> The figures can show that stock left without a sale, that voids concentrate on one shift, that a person had access and opportunity. <b>They cannot show intent</b>, and a manager who states or implies it has gone beyond what they know and has usually made the situation unrecoverable.</p>

<p><b>And the outcome most likely to be right.</b> Most suspicions turn out to be process failures — a step nobody was doing, a control that had lapsed, a genuine error repeated. Approaching it as a process question first is not naivety; it is both more often correct and the only approach that leaves you able to work with the person afterwards.</p>

<blockquote>WATCH-OUT: The most common way a manager destroys their own case, and an innocent person's standing, is a well-intentioned conversation on the day they first suspect something. If you are unsure whether you have crossed from wondering into suspecting, assume you have and apply these rules — applying them unnecessarily costs nothing at all.</blockquote>

<p><b>What to do about your own certainty.</b> The strongest feeling you will have in that first hour is that you already know. That feeling is not evidence, it is frequently wrong, and it is exactly what makes managers act too quickly. The discipline is to write down specifically what you observed — dates, amounts, what you actually saw rather than what you concluded — and to notice how much thinner it looks written down than it felt. That is not a reason to drop it; it is the difference between a case and an impression.</p>"""
, [
 C("You are unsure whether you have crossed from wondering into suspecting. You should:",
   ["Wait for more evidence", "Assume you have — applying the rules unnecessarily costs nothing",
    "Ask a colleague's view", "Raise it informally"], 1,
   "The commonest way a case and an innocent person's standing are destroyed is a well-intentioned conversation on day one."),
 C("Asking a trusted colleague whether they have noticed anything about the person:",
   ["Gathers useful evidence", "Spreads within a day and damages somebody who may have done nothing",
    "Is a reasonable first step", "Protects the team"], 1,
   "Do not discuss it with the team, including your deputy."),
 C("The figures can show access, opportunity and that stock left without a sale. They cannot show:",
   ["Timing", "Intent", "Value", "Frequency"], 1,
   "A manager who states or implies it has gone beyond what they know and usually made the situation unrecoverable.")]),

("Loss that arrives with the delivery", 11, """<p>Not all loss leaves through the front of the branch. A meaningful share never arrives at all, and it is the part a manager is best placed to catch and least often measured on.</p>

<p><b>Three ways it happens, none requiring anybody at your branch to be dishonest.</b> Invoiced and not delivered. Delivered short and signed for. Delivered damaged and accepted because rejecting it was difficult at the time.</p>

<p><b>Why it is systematically under-detected.</b> The receiving happens at the busiest moment, by whoever is available, with a driver who wants to leave, against a document that says what should be there. The path of least resistance is to sign, and the loss surfaces weeks later as an unexplained stock difference attributed to something else entirely.</p>

<p><b>The conditions that make checking possible</b>, which are a manager's responsibility rather than the receiver's. Time to count. Somewhere to put things down. A person whose job it is at that moment. And the authority to record a shortage without needing to find you first — because if raising a problem requires an escalation, problems will not be raised.</p>

<p><b>What to do about the returns you are owed.</b> Damaged goods, short deliveries and recalled lines represent money the supplier owes you, and in many branches the paperwork is started and never followed. Credits outstanding is a number worth having: most managers have never asked for it, and it is frequently larger than they expect.</p>

<p><b>Watch the pattern by supplier.</b> One short delivery is an error. The same supplier short on the same line repeatedly is something else, and it is only visible if shortages are recorded. That record is what lets somebody centrally have a conversation you cannot have from a branch.</p>

<p><b>And be careful about the relationship.</b> A driver who has come to your branch for three years is a familiar face, and familiarity is exactly what makes checking feel rude. Counting is not an accusation, it is the job — and a supplier who objects to being counted is telling you something worth knowing.</p>

<blockquote>IMPLEMENTATION TIP: Ask what credits your branch is owed and has not received. It is a number almost nobody at branch level has, it costs one email, and it is usually a real amount of money sitting in paperwork somebody started and nobody finished.</blockquote>

<p><b>The returns you owe in the other direction.</b> Goods sent back to suppliers, recalled lines, and stock transferred to another branch are all ways inventory leaves without a sale, and each is a legitimate movement that needs the same discipline as a delivery arriving. A transfer sent and never received at the other end sits as a difference in two sets of books and is usually only found at a full count months later. Confirm the other end received what you sent, at the time.</p>"""
, [
 C("A short delivery signed for surfaces weeks later as:",
   ["A supplier dispute", "An unexplained stock difference attributed to something else",
    "A credit note", "A pricing error"], 1,
   "The receiving happened at the busiest moment against a document saying what should be there."),
 C("A supplier who objects to their delivery being counted is:",
   ["Being efficient", "Telling you something worth knowing",
    "Following their policy", "Under time pressure"], 1,
   "Counting is not an accusation, it is the job."),
 C("Credits owed to the branch and never received are:",
   ["Head office's concern", "Usually a real amount sitting in paperwork somebody started and nobody finished",
    "Written off automatically", "Rarely material"], 1,
   "It is a number almost nobody at branch level has, and it costs one email to ask for.")]),

("Okelewo: the year the number moved", 11, """<p>Okelewo's stock losses ran at about 2.1% of sales across eleven branches — roughly ₦48m a year on group turnover. The founder's assumption, shared by most of his managers, was that it was theft. This is what a year of working on it actually found.</p>

<p><b>What the first proper analysis showed.</b> Losses were not spread evenly. Three branches carried a disproportionate share, and within those, two categories carried most of it. That alone changed the question from a general one about honesty to a specific one about four situations.</p>

<p><b>What the four turned out to be.</b></p>

<p><b>Receiving at the flagship</b>, where deliveries were signed for by whoever was nearest, usually while serving. Eight months of received quantities matching ordered quantities exactly. Nobody was counting, and short deliveries had been arriving unrecorded for as long as anybody could establish.</p>

<p><b>Expiry in chilled at two branches</b>, where filling was done from the back of the shelf because it was faster, and short-dated stock was discovered at write-off rather than looked for. Entirely a rotation habit.</p>

<p><b>A stockroom at the Lagos branch</b> that one person could be alone in for two hours at a time, at the end of a corridor, with a back door that was propped open through the afternoon. Nothing was ever proved and nothing needed to be — the arrangement was changed and the category's losses fell by more than half.</p>

<p><b>Counting everywhere</b>, done by the people responsible for the stock, against pre-printed expected quantities. The counts had been agreeing with the system for years and telling nobody anything.</p>

<p><b>What the year produced.</b> Losses from 2.1% to 1.3% of sales, worth about ₦18m annually. One dismissal, at a branch not among the three, arising from something unrelated found in passing.</p>

<p><b>The uncomfortable part of the result.</b> Roughly nine-tenths of the recovery came from process — counting, rotating, receiving, and an arrangement in a stockroom. The assumption that had been costing the business ₦48m a year was not just wrong; it had actively prevented the work, because a problem understood as dishonesty invites surveillance rather than examination.</p>

<blockquote>IMPLEMENTATION TIP: Before assuming anything about your own loss number, split it by branch, by category and by time. The concentration usually points at a process, and a general suspicion about people is the least actionable and least often correct explanation available.</blockquote>

<p><b>What the founder said afterwards.</b> That the year had cost him less than the assumption had — and that the part he found hardest was accepting that eleven managers, himself included, had been confidently wrong about the same thing for three years without anybody testing it. The assumption was never examined because it did not look like an assumption. It looked like knowing your business.</p>"""
, [
 C("Okelewo's losses fell from 2.1% to 1.3% of sales. The recovery came roughly nine-tenths from:",
   ["Dismissals and deterrence", "Process — counting, rotating, receiving and a stockroom arrangement",
    "Better surveillance", "Range changes"], 1,
   "Worth about ₦18m annually, with one dismissal, at a branch not among the three worst."),
 C("The assumption that the loss was theft had:",
   ["Focused attention usefully", "Actively prevented the work",
    "Deterred some of it", "Made no difference"], 1,
   "A problem understood as dishonesty invites surveillance rather than examination."),
 C("The Lagos stockroom losses fell by more than half after the arrangement changed, and:",
   ["A dismissal followed", "Nothing was ever proved and nothing needed to be",
    "The culprit was identified", "Cameras were installed"], 1,
   "Removing the opportunity resolved it without anybody being accused.")]),

("The loss routine", 11, """<p>This is the chapter to keep. None of it is difficult and all of it is the kind of thing that gets postponed until a number appears that somebody wants explained.</p>

<p><b>Daily.</b> Cash counted at every handover, both directions, recorded. Differences investigated the same day regardless of size or direction. Back door closed. Excess cash lifted to the safe at times that are not a pattern.</p>

<p><b>Weekly.</b> Count your forty highest-value or highest-risk lines, blind, by somebody other than the person responsible. Walk your short-dated stock and mark down what is close. Check that waste has been recorded by reason rather than reconstructed later.</p>

<p><b>Monthly.</b> Refunds, voids, discounts and write-offs by person and by hour — looking for concentration rather than volume. Received against ordered by receiver. Credits owed and not received. And the keys and access list, checked against who actually still works here.</p>

<p><b>Quarterly.</b> Walk the branch asking where something could leave unseen. Review where high-value lines sit. Look at the loss number split by category and location rather than as a total.</p>

<p><b>And the thing to say to your team, more than once.</b> That these routines exist so that when something does go wrong it can be traced to a cause rather than to a group of people. Staff who understand that controls protect them cooperate with them; staff who experience controls as suspicion comply grudgingly and tell you nothing.</p>

<p><b>What it is worth.</b> On a branch turning over ₦18m a month, moving losses from 2% to 1.3% is about ₦126,000 a month. It is not a dramatic number in any single week, which is exactly why it survives for years — and it is roughly what your entire controllable cost budget amounts to.</p>

<p><b>The one to start with.</b> Blind counting of your top lines, weekly, by somebody who does not look after them. It is free, it takes twenty minutes, and it is the only item on this list that tells you whether any of the others are working.</p>

<blockquote>WATCH-OUT: Every routine here is a control on your own branch, which means it is also a control on you. A manager who exempts themselves — the float borrowed, the write-off unrecorded, the safe left open during the count — has cancelled the whole arrangement, whatever anybody has been told.</blockquote>

<p><b>A last word on proportion.</b> Nothing in this module is about running a suspicious branch. The great majority of people who work in retail are honest, most loss is process rather than dishonesty, and a manager who treats their team as a risk will get a worse result on every measure in this track, not only this one. The routines exist so that the honest majority are never under a suspicion that cannot be resolved — which is a better reason to run them than any amount of loss prevention.</p>"""
, [
 C("The loss routine item worth starting with is:",
   ["The monthly void report", "Blind weekly counting of top lines by somebody who does not look after them",
    "The quarterly walk", "The access list"], 1,
   "It is the only item that tells you whether any of the others are working."),
 C("Your branch turns over ₦18m a month and you cut losses from 2% to 1.3%. Annually that is worth about:",
   ["₦150,000", "₦1.5m",
    "₦15m", "₦450,000"], 1,
   "About ₦126,000 a month, which is never dramatic in a single week and is roughly an entire controllable cost budget over a year."),
 C("A manager who borrows the float or leaves the safe open during a count has:",
   ["Made a minor exception", "Cancelled the whole arrangement, whatever anybody has been told",
    "Saved time reasonably", "Acted within their authority"], 1,
   "Every routine here is a control on the branch, which means it is also a control on the manager.")]),
]


QUESTIONS = [
 Q("Design beats vigilance in loss prevention because vigilance:", ["Costs money", "Is exhausting, inconsistent, and fails on a busy Saturday", "Requires training", "Needs supervision"], 1,
   "Design works whether or not anybody is paying attention, and it is largely free.", "Ch1 §1", "Physical design"),
 Q("Making the dishonest thing awkward rather than impossible is enough because most loss is:", ["Small", "Opportunistic rather than planned", "External", "Undetected"], 1,
   "Opportunity is what a branch manager can remove.", "Ch1 §2", "Physical design"),
 Q("The largest single physical risk in most branches is:", ["The till", "The back door", "The fire exit", "The staff room"], 1,
   "Usually propped open for ventilation, a smoker, or somebody carrying boxes.", "Ch1 §3", "Physical design"),
 Q("The keys and access list in most branches:", ["Is reviewed monthly", "Still includes somebody who left months ago", "Is held centrally", "Is up to date"], 1,
   "And nobody has looked.", "Ch1 §6", "Physical design"),
 Q("Controls should be explained as protecting honest staff because otherwise they:", ["Are resisted", "Read as accusations", "Slow the branch", "Get bypassed"], 1,
   "A branch where nobody can be alone with the stock is one where nobody can be suspected of having been.", "Ch1 §9", "Physical design"),
 Q("A count done by the person responsible for the stock is:", ["A control", "A confirmation", "Adequate if supervised", "Standard practice"], 1,
   "Rotating who counts costs nothing and changes the quality of the number.", "Ch2 §1", "Counting"),
 Q("Counting blind means counting:", ["Twice", "Without the expected quantity, comparing afterwards", "In pairs", "Without a list"], 1,
   "It takes the same time and produces a genuinely independent number.", "Ch2 §4", "Counting"),
 Q("For everything except the annual valuation, counts should be:", ["Large and rare", "Small and frequent", "Announced", "Full-range"], 1,
   "A weekly count of forty high-value lines tells you about this week, while you can still act.", "Ch2 §5", "Counting"),
 Q("A difference concentrated in one category or location points at:", ["Counting error", "A specific cause — a process, shelf, person or supplier", "System error", "Receiving"], 1,
   "Spread thinly everywhere points at counting, receiving or system error instead.", "Ch2 §7", "Counting"),
 Q("Adjusting a difference and moving on converts a signal into:", ["A control", "A bookkeeping entry", "A trend", "A report"], 1,
   "The adjustment is the beginning of a question about why, not the end of the process.", "Ch2 §6", "Counting"),
 Q("Waste differs from theft in that it is:", ["Larger", "Entirely visible and local, with nobody to accuse", "Unavoidable", "Seasonal"], 1,
   "A substantial part of what branches accept as inevitable is not.", "Ch3 §1", "Waste"),
 Q("Rotation is neglected because it:", ["Is not understood", "Takes ten seconds longer every time", "Requires equipment", "Is unassigned"], 1,
   "A habit problem rather than a knowledge problem.", "Ch3 §3", "Waste"),
 Q("A line marked down three days before expiry recovers half; two days later it:", ["Recovers a quarter", "Recovers nothing and costs the disposal", "Can be returned", "Recovers the same"], 1,
   "A weekly walk of short-dated stock turns a write-off into a markdown.", "Ch3 §4", "Waste"),
 Q("Waste should be recorded:", ["At month end", "When it happens, by reason", "Weekly in total", "Only above a value"], 1,
   "Five categories recorded at the time show which one is actually costing you.", "Ch3 §5", "Waste"),
 Q("Knowing what an hour without power costs in stock turns a generator into:", ["An overhead", "An arithmetic question", "A capital request", "A safety measure"], 1,
   "The kind of number nobody has produced for the person who approves the spend.", "Ch3 §6", "Waste"),
 Q("Cash should be the responsibility of:", ["The shift", "One person at a time", "The supervisor", "Whoever is on the till"], 1,
   "Every point where that breaks is a point where a loss cannot be attributed.", "Ch4 §2", "Cash"),
 Q("At handover the drawer should be counted:", ["By the person receiving it", "By both, in both directions, recorded", "By the manager", "At the end of the day"], 1,
   "Without both counts a shortage belongs to two shifts and can be assigned to neither.", "Ch4 §3", "Cash"),
 Q("A branch that investigates only large cash variances teaches:", ["That control is tight", "Anybody inclined exactly what the threshold is", "Accuracy", "Reporting discipline"], 1,
   "Small and persistent matters more than one large and explained.", "Ch4 §6", "Cash"),
 Q("A till overage indicates:", ["Good fortune", "A process failure — somebody was charged wrongly or short-changed", "Rounding", "An offset"], 1,
   "A branch celebrating overages and investigating shortages sees half its errors.", "Ch4 §7", "Cash"),
 Q("When a manager borrows the float or leaves the safe open, staff conclude:", ["It is a one-off", "The rules describe what is written rather than what is done", "Trust is high", "The manager is busy"], 1,
   "And the conclusion applies to every rule in the branch, not only the cash ones.", "Ch4 §8", "Cash"),
 Q("The control on refunds that closes the largest route is:", ["Manager approval", "No receipt or record, no refund", "A value limit", "A returns register"], 1,
   "A refund with no original sale is money leaving against nothing.", "Ch5 §2", "Process gaps"),
 Q("What is informative about voids is:", ["Any single void", "Concentration on one person, hour or line", "The total value", "The time taken"], 1,
   "Individual voids are nearly always innocent.", "Ch5 §3", "Process gaps"),
 Q("The staff purchase control that costs nothing is:", ["A spending limit", "Nobody rings up their own purchase", "Manager sign-off", "A separate till"], 1,
   "It is a legitimate arrangement; the control is who processes it.", "Ch5 §5", "Process gaps"),
 Q("A ₦3,000 loss twice a week is worth annually:", ["₦31,000", "₦312,000", "₦72,000", "₦156,000"], 1,
   "Small amounts frequently, which is why they are attractive and why they are missed.", "Ch5 §8", "Process gaps"),
 Q("A manager who reacts to a single void will:", ["Deter future ones", "Be wrong nearly every time", "Establish a standard", "Find the pattern"], 1,
   "And will have taught the team that ordinary work attracts suspicion.", "Ch5 §7", "Process gaps"),
 Q("On first suspecting a member of your team you should NOT:", ["Write down what you saw", "Confront them", "Preserve the records", "Tell the person your business names"], 1,
   "A conversation before the facts are established converts a possibility into a denial and a warning.", "Ch6 §4", "Suspicion"),
 Q("Discussing a suspicion with your deputy:", ["Gathers evidence", "Spreads within a day and may damage somebody who did nothing", "Is a reasonable check", "Shares the burden"], 1,
   "Do not discuss it with the team at all.", "Ch6 §6", "Suspicion"),
 Q("A manager is poorly placed to investigate their own team member because they:", ["Lack training", "Cannot be objective, and will not look objective afterwards", "Have no authority", "Are too busy"], 1,
   "This is a moment to involve the person your business says to involve.", "Ch6 §5", "Suspicion"),
 Q("The figures cannot show:", ["Access", "Intent", "Opportunity", "Sequence"], 1,
   "A manager who states or implies it has gone beyond what they know.", "Ch6 §9", "Suspicion"),
 Q("Most suspicions turn out to be:", ["Confirmed", "Process failures", "Unresolvable", "Customer theft"], 1,
   "Approaching it as a process question first is both more often correct and the only approach that leaves you able to work with the person afterwards.", "Ch6 §10", "Suspicion"),
 Q("Loss arriving with the delivery includes invoiced-not-delivered, delivered-damaged-and-accepted, and:", ["Wrong pricing", "Delivered short and signed for", "Late delivery", "Substituted lines"], 1,
   "None requires anybody at your branch to be dishonest.", "Ch7 §2", "Supplier-side loss"),
 Q("Delivery loss is systematically under-detected because receiving happens:", ["At month end", "At the busiest moment, by whoever is available, with a driver waiting", "Without paperwork", "In the stockroom"], 1,
   "The path of least resistance is to sign.", "Ch7 §3", "Supplier-side loss"),
 Q("If recording a shortage requires finding the manager, then shortages will:", ["Be recorded properly", "Not be raised", "Be estimated", "Be reported weekly"], 1,
   "The conditions that make checking possible are a manager's responsibility rather than the receiver's.", "Ch7 §4", "Supplier-side loss"),
 Q("Credits owed and not received are:", ["Immaterial", "Usually a real amount sitting in unfinished paperwork", "Written off automatically", "Head office's records"], 1,
   "Almost nobody at branch level has the number, and it costs one email.", "Ch7 §5", "Supplier-side loss"),
 Q("A supplier who objects to being counted is:", ["Under time pressure", "Telling you something worth knowing", "Following policy", "Being efficient"], 1,
   "Counting is not an accusation, it is the job.", "Ch7 §7", "Supplier-side loss"),
 Q("Okelewo's losses ran at 2.1% of sales, worth about:", ["₦4.8m a year", "₦48m a year", "₦18m a year", "₦480m a year"], 1,
   "Across eleven branches, and assumed by nearly everybody to be theft.", "Ch8 §1", "Okelewo"),
 Q("The first proper analysis changed the question by showing losses were:", ["Larger than thought", "Concentrated in three branches and two categories", "Evenly spread", "Seasonal"], 1,
   "From a general question about honesty to a specific one about four situations.", "Ch8 §2", "Okelewo"),
 Q("Roughly what share of Okelewo's recovery came from process rather than dismissal?", ["A half", "Nine-tenths", "A third", "All of it"], 1,
   "Counting, rotating, receiving, and an arrangement in a stockroom.", "Ch8 §8", "Okelewo"),
 Q("The Lagos stockroom losses halved after the arrangement changed, and:", ["A dismissal followed", "Nothing was proved and nothing needed to be", "Cameras were fitted", "The category was moved"], 1,
   "Removing the opportunity resolved it without anybody being accused.", "Ch8 §6", "Okelewo"),
 Q("The theft assumption had cost the business because a problem understood as dishonesty invites:", ["Investigation", "Surveillance rather than examination", "Dismissals", "Policy changes"], 1,
   "It actively prevented the work that eventually recovered ₦18m a year.", "Ch8 §9", "Okelewo"),
 Q("Moving losses from 2% to 1.3% on ₦18m monthly turnover is worth about:", ["₦12,600", "₦126,000 a month", "₦1.26m a month", "₦36,000"], 1,
   "Roughly an entire controllable cost budget, and never dramatic in any single week.", "Ch9 §6", "The routine"),
 Q("Which loss routine item tells you whether the others are working?", ["The monthly void report", "Blind weekly counting by somebody not responsible for the stock", "The quarterly walk", "Cash reconciliation"], 1,
   "Free, twenty minutes, and the only one that verifies the rest.", "Ch9 §7", "The routine"),
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
    rebalance(QUESTIONS, "retail:loss:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:loss:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 5 — Loss",
        "desc": ("Preventing it rather than measuring it. Designing a branch where loss is "
                 "hard, a count that means something, waste and expiry, cash and the "
                 "situations nobody can be cleared of, where loss hides inside legitimate "
                 "processes, what to do in the hour you first suspect somebody, and the "
                 "loss that never arrives at all."),
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
