#!/usr/bin/env python3
"""Build 'Money, Honesty and the Rules That Protect You' into the shopfloor data.

Module 5 of Retail Foundations.

This is the module most easily written badly. Written from the business's side
it becomes a warning delivered to somebody who has done nothing, and a reader
who feels accused stops reading. The whole module is therefore built on one
reframe, which happens to be true rather than merely tactful:

  THE CONTROLS EXIST TO PROTECT THE PERSON HANDLING THE MONEY. A shortage that
  cannot be attributed becomes a suspicion attached to everybody who was near
  it. Every rule in this chapter — own login, one person per drawer, witnessed
  counts, recorded voids — exists so that on the day something is wrong it is
  provably not you. That is not a softening of the truth; it is the strongest
  argument for the rules and the one nobody makes to new staff.

Three further positions:

  MOST SHRINKAGE IS NOT THEFT. It is process error — miskeys, unrecorded
  damage, receiving mistakes, wrong units. Saying so early is both accurate and
  what makes the rest of the module readable, because a learner who believes
  they are suspected of stealing cannot hear anything else.

  THE SMALL THING IS THE WHOLE DANGER. Almost nobody sets out to steal. People
  eat one item, borrow from a drawer intending to repay, or let a friend's
  discount through, and the distance from there to dismissal is much shorter
  than it looks from the inside. The module is explicit about this because it
  is the actual mechanism by which honest people lose their jobs.

  SUSPECTING A COLLEAGUE HAS A PROCEDURE. Do not confront, do not investigate,
  do not discuss it with other staff, tell the named person. This mirrors the
  manager track's rule from the other side, and the reasons given are the
  learner's own safety and the possibility that they are wrong.

Run from the app package directory:  python3 build_shopfloor_m5.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "money_honesty"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Why this module is not about suspecting you", 10, """<p>A chapter about honesty, given to somebody who has been honest their whole life, can read as an accusation. It is worth saying plainly at the start what this module is actually for, because the reason is not the obvious one.</p>

<p><b>The thing shops lose money to, in order.</b> Process error comes first and it is not close — miskeyed items, damage nobody recorded, deliveries counted wrong, the wrong unit rung up, stock written off twice or not at all. Then customer theft. Then, some way behind in most branches, staff dishonesty.</p>

<p><b>Which matters to you for a specific reason.</b> When a count comes up short, the shop rarely knows which of the three it was. A shortage arrives as a number, and a number cannot say whether it was a miskey in March or somebody taking cash in June. That ambiguity is the danger to you, and it has nothing to do with whether you are honest.</p>

<p><b>So here is the actual argument of this module.</b> Every rule in it — working under your own login, one person to a drawer, counting in front of somebody, recording what you take — exists so that when something is wrong, it can be traced to a cause rather than distributed across everybody who was nearby. The rules are not there because the shop suspects you. They are there so that it cannot.</p>

<p><b>The version of this that people learn too late.</b> Staff who share a login, cover each other's drawers and skip the recording are usually doing it out of goodwill and speed. It works perfectly until the month something is missing, at which point none of them can prove anything about any of it, and the investigation lands on all of them equally. The person who was scrupulous is in exactly the same position as the person who was not.</p>

<p><b>Read the rest of this module as self-protection.</b> That is not a trick to make the rules palatable. It is the more accurate description, and it is why experienced staff follow these rules more carefully than new ones rather than less.</p>

<blockquote>WORTH KNOWING: If you ever find yourself thinking a rule is pointless because you know you are honest, that is precisely the rule to follow most carefully. Your honesty is not in question to you. The rule exists for the day it is in question to somebody who was not there.</blockquote>

<p><b>One more thing about the ordering of those causes.</b> It is not an invitation to relax. A branch where staff dishonesty is rare is usually a branch where the controls are kept, and the reason it is third on the list is partly that the first two are so large and partly that the rules work. Shops that stop bothering discover the order changes. The list describes a well-run branch rather than retail in general.</p>"""
, [
 C("The largest cause of loss in most shops is:",
   ["Staff dishonesty", "Process error",
    "Customer theft", "Damage"], 1,
   "Miskeys, unrecorded damage, receiving mistakes and wrong units come first, and it is not close."),
 C("The danger to an honest member of staff is that a shortage:",
   ["Is always investigated", "Arrives as a number that cannot say what caused it",
    "Is deducted from wages", "Points to the last person on shift"], 1,
   "That ambiguity has nothing to do with whether you are honest."),
 C("Staff who share logins and cover each other's drawers out of goodwill find that:",
   ["It saves time overall", "When something goes missing none of them can prove anything",
    "Supervisors object", "The system prevents it"], 1,
   "The scrupulous person ends up in exactly the same position as the one who was not.")]),

("Your login is yours", 10, """<p>Whatever your branch uses to identify who did something — a login, a code, a card, a key — it is the single most important thing in this module.</p>

<p><b>What it actually is.</b> Not a formality and not a security measure against outsiders. It is the mechanism that attaches every action to a person, which means it is simultaneously what makes you accountable for what you did and what makes you not accountable for what you did not.</p>

<p><b>The rules, and there are only three.</b> Never tell anybody your code. Never use somebody else's, even with their permission, even to help them, even when the queue is long. And never leave a terminal open under your identity while you walk away.</p>

<p><b>Why the middle one is the hardest.</b> Because refusing feels unhelpful. A colleague is stuck, their code is not working, the customer is waiting, and the obvious solution is to put it through under yours. Everybody understands why it happens. What has actually happened is that a transaction you did not perform is now recorded as yours, and if there is anything wrong with it — a wrong price, a void, a shortage — the record says you.</p>

<p><b>The right answer in that moment.</b> Serve the customer yourself, or get somebody who can. It takes the same time, it solves the same problem, and it leaves the record true.</p>

<p><b>What to do if somebody asks for your code.</b> Say no, and say it as a rule rather than as a judgement about them: <i>I am not allowed to, sorry</i>. That is easier than it sounds because it is not personal — you are not accusing them of anything, you are declining to do something you should not do. Anybody reasonable accepts it immediately. Anybody who pushes has told you something worth knowing.</p>

<p><b>And the walking-away rule.</b> An unlocked terminal under your name is available to anybody who passes it, including a customer. Locking it takes two seconds. The habit is worth building until it is automatic, because the times you will forget are the busy ones, and the busy ones are exactly when somebody could use it unnoticed.</p>

<blockquote>WATCH-OUT: If a supervisor or manager asks to use your login, the answer is still no — politely, and with the offer to do it yourself or to fetch somebody with the right access. Seniority does not change what the record will say afterwards, and it is your name on it.</blockquote>

<p><b>What to do if a manager insists.</b> It happens occasionally and it is genuinely uncomfortable. Offer the alternative twice — <i>I will do it myself</i>, or <i>shall I get somebody with that access</i> — and if they still insist, do it their way and write down what happened, when, and who asked, that day. You are not in a position to refuse indefinitely and you are in a position to make sure the record does not rest on your memory in six months.</p>"""
, [
 C("Using a colleague's login to help them means:",
   ["Nothing, if the transaction is correct", "A transaction you did not perform is recorded as theirs, and yours likewise",
    "The system flags it", "Both are covered"], 1,
   "If there is anything wrong with it, the record names the login rather than the person."),
 C("If a supervisor asks to use your login, the answer is:",
   ["Yes, given their seniority", "Still no, with an offer to do it yourself",
    "Yes if recorded", "Ask another manager"], 1,
   "Seniority does not change what the record says afterwards, and it is your name on it."),
 C("Refusing to share a code is easier when framed as:",
   ["A judgement about the person asking", "A rule rather than a judgement",
    "A policy quotation", "A supervisor's instruction"], 1,
   "Anybody reasonable accepts it immediately, and anybody who pushes has told you something worth knowing.")]),

("Cash, and why the rules are strict", 10, """<p>Cash is the only thing in a shop that can be lost without leaving a trace. Everything else has to physically move; money can be gone with nothing missing from any shelf. That is why the rules around it are stricter than anything else you will meet.</p>

<p><b>One person to a drawer.</b> The most important rule and the most often broken, usually to be helpful. Two people using one drawer means neither can account for it, and a shortage becomes a conversation about which of two people it was — with no way to answer. If you are asked to serve from somebody else's open drawer, the answer is the same as for logins: do it your own way or get somebody who can.</p>

<p><b>Count when you take it and count when you hand it over.</b> Both times, in front of the other person, with the number written down or entered. A drawer accepted without counting is a drawer you have taken responsibility for on trust — and if it was already short, it is short on your watch.</p>

<p><b>Count in a way somebody can see.</b> Not because anybody doubts you, but because a count nobody witnessed is a count nobody can confirm. The witness protects you rather than checking you.</p>

<p><b>What to do about a difference.</b> Report it. Every time, whichever direction, however small. A drawer that is over is as much a problem as one that is short — it means something went wrong, usually a customer was overcharged, and it is information. The temptation with a small over is to leave it; the temptation with a small short is to make it up from your own pocket. Both are wrong, and the second is worse than it looks: putting your own money in hides an error, and hiding errors is how a small process fault runs for months.</p>

<p><b>Never take from the drawer for anything.</b> Not change for a colleague, not to buy something, not to be repaid this afternoon. This is the single most common route by which an honest person loses a job — not because of the amount, but because the record shows money removed with no transaction, and no explanation given afterwards ever fully undoes that.</p>

<p><b>And your own money.</b> Keep it separate and keep it out of the till area entirely. A drawer that has personal cash near it produces a question nobody can answer cleanly.</p>

<blockquote>WATCH-OUT: Making up a small shortage from your own pocket feels like the honest thing to do. It is the opposite: it conceals a discrepancy the shop needed to know about, and it establishes a habit that becomes impossible to explain if the shortages grow.</blockquote>

<p><b>Change, and the one habit that prevents most disputes.</b> Say the amount out loud when you take it, leave the note visible until the change is given, and count the change into the customer's hand rather than handing it over as a lump. Every one of those is a defence against the commonest dispute at any counter — the customer who is certain they gave you a larger note. Nobody is lying in most of those cases; somebody has genuinely misremembered, and the only way to settle it afterwards is a record neither of you kept.</p>"""
, [
 C("Making up a small shortage from your own money is:",
   ["The honest response", "Concealing a discrepancy the shop needed to know about",
    "Acceptable if reported later", "Standard practice"], 1,
   "It also establishes a habit that becomes impossible to explain if the shortages grow."),
 C("A drawer that is over is:",
   ["Good news", "As much a problem as one that is short",
    "Left for the next count", "Kept as a float"], 1,
   "Something went wrong, usually a customer was overcharged, and it is information."),
 C("Taking money from the drawer to be repaid the same afternoon is:",
   ["Acceptable if repaid", "The most common route by which an honest person loses a job",
    "A supervisor's decision", "Fine if witnessed"], 1,
   "The record shows money removed with no transaction, and no later explanation fully undoes that.")]),

("Discounts, staff purchases and friends", 10, """<p>Almost every discipline case that involves a decent person starts here rather than at the till drawer. It is worth understanding before it arrives.</p>

<p><b>Discounts are not yours to give.</b> Whatever authority exists to reduce a price belongs to specific people, and the reason is not distrust — it is that a discount is money, and money given away needs the same authority as money taken out. A price reduced by somebody without authority looks identical, in the records, to money missing.</p>

<p><b>The awkward version, which will happen.</b> A friend, a relative, a colleague at the counter, and the expectation is visible. The sentence that resolves it: <i>I am not able to do prices, sorry — I would get in trouble.</i> Saying you would get in trouble is not weakness; it moves the refusal from a judgement about them to a fact about your job, and almost everybody accepts it. Somebody who keeps pushing after that is asking you to risk your job for their discount, and it is worth seeing it in those terms.</p>

<p><b>Your own purchases.</b> Buy through the till like anybody else, served by somebody else where your branch requires it, keep the receipt, and never serve yourself. Serving yourself is the thing that looks worst in a review even when everything about it was correct — and it takes one minute to avoid.</p>

<p><b>Staff discount, where it exists.</b> Use it for yourself, within the rules, and never for anybody else. Buying for a friend on your discount is one of the commonest dismissals in retail, and people are consistently surprised because they were not stealing. The shop's view is simpler than the moral one: the discount is part of your pay, using it for others is giving away something that was not yours, and the amount is not the point.</p>

<p><b>Eating, drinking, opening.</b> Nothing is consumed before it is paid for. Not a drink on a hot day intending to pay at the end of the shift, not a damaged item that was going to be written off anyway. The write-off case is genuinely counterintuitive: goods due for disposal are still the shop's property, and taking them is a decision somebody else is entitled to make.</p>

<p><b>And the general test.</b> If you would be uncomfortable doing it while the owner watched, do not do it. That is a cruder rule than any policy and it catches almost everything.</p>

<blockquote>WATCH-OUT: Buying something for a friend on your staff discount does not feel like dishonesty and is treated as one of the most serious things you can do. Know your branch's rule precisely, and if it is not written down, ask before rather than after.</blockquote>"""
, [
 C("Taking a damaged item that was going to be written off anyway is:",
   ["Fine, since it has no value", "Taking property whose disposal is somebody else's decision",
    "Allowed with permission afterwards", "A supervisor's judgement"], 1,
   "Goods due for disposal are still the shop's property until somebody entitled to decide has decided."),
 C("Using your staff discount to buy something for a friend is:",
   ["A minor breach", "One of the commonest dismissals in retail",
    "Acceptable within limits", "Permitted if declared"], 1,
   "The discount is part of your pay, and using it for others gives away something that was not yours."),
 C("The general test offered is whether you would be comfortable doing it:",
   ["Within policy", "While the owner watched",
    "In front of customers", "With a supervisor present"], 1,
   "A cruder rule than any policy, and it catches almost everything.")]),

("The small thing", 10, """<p>Almost nobody takes a job intending to steal from it. Understanding how honest people end up dismissed is more useful than any warning, because the mechanism is genuinely not obvious from the inside.</p>

<p><b>How it actually goes.</b> Something small and defensible. A drink on a long shift, meaning to pay later. Fifty naira from the drawer to make change, replaced within the hour. A friend's item put through at the wrong price once. Each is trivial, each has a reason, and the person doing it would be insulted to be called dishonest — correctly, at that moment.</p>

<p><b>What changes.</b> Nothing bad happens. No alarm, no consequence, and the thing that felt uncomfortable the first time feels ordinary the third. The size drifts upward slowly because the small amount stopped feeling like anything. Nobody notices a threshold being crossed, because there is no threshold — there is a gradient, and it is only visible looking back.</p>

<p><b>Where it ends.</b> A pattern in the records rather than a single event. By the time anyone looks, there is a history that cannot be explained as an accident, and the explanation that is true — that it started with a drink and never felt like theft — is not one anybody can act on. The person is genuinely shocked, and the shop is genuinely unable to keep them.</p>

<p><b>Which produces the only reliable defence.</b> The line is at zero. Not at a naira amount you have decided is reasonable, because that line moves and you will not notice it moving. Nothing consumed unpaid, nothing removed unrecorded, nothing given away without authority — including the first time, including when it is genuinely defensible.</p>

<p><b>Why the first time is the important one.</b> Because there is no difficulty at all in not starting, and a great deal of difficulty in stopping. The habit that protects you is formed in a moment nobody will ever know about, over something too small to matter.</p>

<p><b>And what to do if you have already done something small.</b> Say so, early, to whoever is right. It is a difficult conversation and it is survivable, which the same thing discovered in three months' time is often not. Almost every serious case in retail was recoverable at the point where somebody could still have mentioned it.</p>

<blockquote>WORTH KNOWING: The reason this chapter exists is not that people are weak. It is that the mechanism is invisible from inside it — everybody who has been through it says the same thing, which is that at no point did it feel like the moment to stop.</blockquote>

<p><b>The pressure that comes from other people.</b> Sometimes the small thing is not your idea. A colleague suggests it, or does it in front of you and expects you to say nothing, or a friend asks you for something at the counter. That is harder than the version you decide alone, because refusing has a social cost the other version does not. The useful thing to know in advance is that you are being asked to accept a risk that lands entirely on you — the person suggesting it is not the one whose login is on the transaction.</p>"""
, [
 C("The reliable defence described is that the line sits at:",
   ["A reasonable small amount", "Zero",
    "Whatever policy states", "The supervisor's discretion"], 1,
   "A line set at an amount moves, and you will not notice it moving."),
 C("The first time matters most because:",
   ["It is the most visible", "There is no difficulty in not starting and a great deal in stopping",
    "It is usually noticed", "Records begin then"], 1,
   "The habit that protects you is formed over something too small to matter."),
 C("Somebody who has already done something small should:",
   ["Wait and see", "Say so early, to whoever is right",
    "Repay it quietly", "Stop and say nothing"], 1,
   "It is a survivable conversation, which the same thing discovered in three months often is not.")]),

("When you see something", 10, """<p>At some point you may see or suspect something — a colleague, a customer, an arrangement that looks wrong. What you do next matters for the shop and matters more for you.</p>

<p><b>A customer taking something, and this is the safety rule of the module.</b> Do not confront them. Do not follow them out of the shop. Do not attempt to stop, hold or take anything back. Note what you can — what they look like, what they took, which way they went — and tell whoever your branch says, immediately. Goods are insured and replaceable. You are not, and no shop worth working for would trade the second for the first. If your branch has told you otherwise, that instruction is wrong and worth raising.</p>

<p><b>A colleague, which is much harder.</b> The rule is the same shape and the reasons are different. Do not confront them. Do not investigate — do not check their till, watch them, or collect evidence. Do not discuss it with other staff, at all, including the one you trust most. Tell the named person your branch specifies, once, factually.</p>

<p><b>Why not investigate.</b> Three reasons, and each is enough on its own. You might be wrong, and an innocent person who learns they were watched by a colleague is a relationship and possibly a career damaged. If you are right, an amateur investigation can destroy the evidence and make the case unprovable. And gathering evidence on a colleague puts you in a position that is difficult to explain afterwards, however good your motives were.</p>

<p><b>Why not tell other staff.</b> Because it spreads within a day, it reaches the person concerned, and if you were wrong you have done something to somebody that cannot be undone. Say it once, upward, and then say nothing.</p>

<p><b>What to say.</b> Facts, not conclusions. <i>I saw X happen on Tuesday</i> rather than <i>I think X is stealing</i>. The first is something you can stand behind. The second is a judgement that is not yours to make and that you may not be able to support.</p>

<p><b>If you are asked to do something wrong.</b> By anybody, including somebody senior. Decline, without drama — <i>I am not comfortable doing that</i> — and tell somebody above them or wherever your branch's route goes. Being asked is not your fault and going along with it does not stay their responsibility.</p>

<p><b>What happens to you afterwards, which nobody mentions.</b> Being present at a theft, reporting a colleague, or being asked questions about a shortage are all unpleasant for days afterwards, and people are often surprised by how much. It is normal, it is not a sign you handled it badly, and it is worth telling somebody rather than carrying it alone. A branch that treats these as routine paperwork and ignores their effect on the people present is getting something wrong.</p>

<blockquote>WATCH-OUT: Never put yourself between a person and the door. That applies to a customer taking goods and to anybody behaving aggressively, and it is the single most important safety rule in this whole track.</blockquote>"""
, [
 C("Seeing a customer take something, you should:",
   ["Confront them politely", "Note what you can and tell somebody immediately, without confronting",
    "Follow them outside", "Ask them to return it"], 1,
   "Goods are insured and replaceable, and no shop worth working for would trade your safety for them."),
 C("Suspecting a colleague, you should not investigate because you might be wrong, evidence can be destroyed, and:",
   ["It takes time", "It puts you in a position that is difficult to explain afterwards",
    "It is the manager's job", "The system will catch it"], 1,
   "Each of the three reasons is enough on its own."),
 C("What you report should be:",
   ["Your conclusion", "Facts",
    "A summary of the pattern", "What others have said"], 1,
   "'I saw X happen on Tuesday' is something you can stand behind; 'I think X is stealing' is not yours to judge.")]),

("Where the losses actually come from", 10, """<p>Having covered honesty, it is worth returning to where the money really goes, because a member of staff who understands this can prevent far more than they could ever be tempted to take.</p>

<p><b>The miskey.</b> The wrong item scanned or entered, usually because two products look alike or one would not scan. The customer is charged wrongly and the stock records are now wrong for two products at once. It is the commonest single error in retail and it is entirely fixable by slowing down for one second on the lines that look alike.</p>

<p><b>The unit confusion.</b> Selling by the item what should be sold by weight, or the single price on the multipack. Small each time, constant across a year.</p>

<p><b>Unrecorded damage and waste.</b> Module 4's territory, and it belongs on this list because it does not just lose the item — it corrupts the records, so the shop cannot tell the loss from a theft afterwards.</p>

<p><b>Receiving errors.</b> Signing for what did not arrive. The loss is real and it is invisible until a count, by which point it looks exactly like something taken from the shop.</p>

<p><b>Give-aways at the counter.</b> Not the deliberate kind — the extra bag, the item not scanned because it was already in the customer's hand, the discount applied that had expired. Each defensible individually.</p>

<p><b>What connects all five.</b> None of them is dishonest, all of them are attributable to nobody, and every one produces a shortage that looks like theft afterwards. Which means the person who is careful about scanning, units, damage records and deliveries is not only saving the shop money — they are removing the ambiguity that would otherwise sit around everybody who works there.</p>

<p><b>The thing worth doing with this.</b> When a count comes up short, most people assume theft. Somebody who knows this list can offer a better question: what changed, which lines, and does it match anything in the way we have been working? That question has recovered far more money in retail than any accusation ever has.</p>

<p><b>And why this matters for how a branch feels to work in.</b> A shop that assumes theft investigates people. A shop that knows this list investigates processes first, which is both more effective and considerably less corrosive to work in. If you are ever in a position to influence which of those your branch does — and a well-informed question at the right moment can do it — it is one of the more valuable things anybody at any level can contribute.</p>

<blockquote>IMPLEMENTATION TIP: Learn the three lines in your section that look almost identical and cost different amounts. Those three are where most of your own miskeys will happen, and knowing them is a one-minute investment against a year of small errors.</blockquote>"""
, [
 C("The commonest single error in retail is:",
   ["Short change", "The miskey",
    "Unrecorded damage", "Receiving errors"], 1,
   "The customer is charged wrongly and the stock records go wrong for two products at once."),
 C("What connects the five loss types is that none is dishonest and every one:",
   ["Is easily traced", "Produces a shortage that looks like theft afterwards",
    "Is covered by insurance", "Is the supervisor's responsibility"], 1,
   "Which is why care removes the ambiguity that would otherwise sit around everybody."),
 C("When a count is short, the better question than who took it is:",
   ["Who was on shift", "What changed, which lines, and does it match how we have been working",
    "When was the last count", "Which door was open"], 1,
   "That question has recovered far more money in retail than any accusation.")]),

("Okelewo Stores: the short drawer", 10, """<p>Eight months in. The Ibadan branch had a drawer come up ₦4,000 short on a Thursday, and what happened next is instructive mostly for what did not happen.</p>

<p><b>The situation.</b> Two people had worked the till that afternoon — Ada for the first half, a colleague for the second — because the supervisor had asked her to cover a break and the drawer had simply carried on. Neither had counted at the handover. Both were entirely honest. Neither could prove anything.</p>

<p><b>What that felt like.</b> Ada described it later as the worst two days of her time there. She knew she had not taken it. She could not demonstrate that, and she found that being certain of your own innocence is no help at all when the record cannot distinguish you from somebody else.</p>

<p><b>What it turned out to be.</b> A miskey. A ₦4,000 airtime voucher entered as a ₦400 one earlier in the day, found when somebody thought to check the transaction list rather than the people. It had nothing to do with either of them and it had been sitting in the records the whole time.</p>

<p><b>What changed afterwards.</b> Not a new rule — the rule already existed. What changed was that Ada started counting at every handover, out loud, in front of whoever was taking over, even when it was awkward and even when the shop was busy. Two or three other people copied her within a month, not because anybody instructed them to but because they had watched what the two days did to her.</p>

<p><b>The part worth taking.</b> The supervisor's instruction to cover the break was reasonable and the outcome was nobody's fault. The rules that would have protected both of them were not broken deliberately by anybody — they were skipped in a busy moment for a good reason, which is how they are always skipped.</p>

<p><b>And the other lesson, which was the supervisor's.</b> She checked the transactions before she talked to anybody. That order matters: two honest people spent two days under suspicion for something a ten-minute look at the records would have explained, and it was only ten minutes because somebody eventually thought to look there first.</p>

<p><b>What Ada did not do, and it is the reason this ends well.</b> She did not accuse the colleague, and the colleague did not accuse her. Both were frightened, both had an obvious person to point at, and neither did. Had either started, the branch would have been left with two people who could not work together afterwards regardless of what the transaction list eventually said — and it would have said exactly the same thing either way.</p>

<blockquote>IMPLEMENTATION TIP: Count at every handover, out loud, in front of the other person. It is awkward for about a week. It is also the single thing in this module that would have prevented the situation above entirely, and it takes ninety seconds.</blockquote>"""
, [
 C("The ₦4,000 shortage turned out to be:",
   ["Taken by a customer", "A miskey — a ₦4,000 voucher entered as ₦400",
    "A counting error at close", "Never explained"], 1,
   "It had been sitting in the transaction records the whole time."),
 C("Ada found that being certain of her own innocence:",
   ["Resolved it quickly", "Was no help when the record could not distinguish her from somebody else",
    "Satisfied the supervisor", "Made the count irrelevant"], 1,
   "Which is the argument of the whole module, met in practice."),
 C("The rules that would have protected both of them were:",
   ["Not in place", "Skipped in a busy moment for a good reason",
    "Deliberately broken", "Unclear to staff"], 1,
   "Nobody broke them deliberately — they were skipped in a busy moment for a good reason, which is how it always happens.")]),

("Review, and the four rules", 10, """<p>The module in short, and it is the shortest list in the track because it needs to be memorable rather than complete.</p>

<p><b>The controls protect you.</b> Most loss is process error, a shortage arrives as a number that cannot say what caused it, and the rules exist so that on the day something is wrong it can be traced rather than distributed across everybody nearby.</p>

<p><b>Your login is yours.</b> Never share it, never use somebody else's whoever asks, never leave a terminal open under your name. Seniority does not change what the record says.</p>

<p><b>Cash is stricter than everything else</b> because it can vanish without anything being missing. One person to a drawer, count at every handover in front of somebody, report every difference in either direction, take nothing from the drawer for any reason, and never make up a shortage from your own pocket.</p>

<p><b>Discounts are not yours to give</b>, your own purchases go through somebody else, and staff discount is for you alone. Nothing is consumed before it is paid for, including things about to be written off.</p>

<p><b>The line is at zero</b>, because a line set at an amount moves and you will not notice it moving.</p>

<p><b>If you see something:</b> never confront, never follow, never investigate, never discuss it with colleagues. Note the facts, tell the named person once. Never put yourself between a person and the door.</p>

<p><b>The four rules, in the order they will come up.</b> One: never use anybody else's login, and never lend yours. Two: count at every handover, out loud, in front of the other person. Three: record every difference and every breakage, including the ones that make you look careless. Four: nothing consumed, removed or discounted without authority — the first time and every time.</p>

<p><b>What all four have in common.</b> Each is slightly awkward, each takes under two minutes, and each one is the thing you would want to be able to point to if a month later somebody asks a question you did not expect. That is the whole of it.</p>

<p><b>A closing word on how this module should feel.</b> If it has read as a set of restrictions, read it once more from the other side. Almost everything in it is a way of being able to answer a question you have not been asked yet. That is worth having in any job and worth having most where money moves — and the people who find these rules natural are, without exception, the ones who have seen what happens when they are absent.</p>

<blockquote>WORTH KNOWING: The next module is the shift and the people on it — working with colleagues, handovers, reliability, and what to do when the team is not working. It is the other half of this one: this module was about the record being clear, and the next is about the shift running whether or not anybody is watching.</blockquote>"""
, [
 C("The four rules are stated in the order:",
   ["Of importance", "They will come up",
    "Of difficulty", "The policy lists them"], 1,
   "Logins, handover counts, recording differences, and nothing without authority."),
 C("What the four rules have in common is that each is slightly awkward, quick, and:",
   ["Required by policy", "The thing you would want to point to if asked an unexpected question a month later",
    "Checked by supervisors", "Recorded in the system"], 1,
   "Which is the whole argument of the module in one line."),
 C("Rule three includes recording differences that:",
   ["Are material", "Make you look careless",
    "Exceed a threshold", "Cannot be explained"], 1,
   "Hiding an error is what turns a process fault into something nobody can explain months later.")]),
]


QUESTIONS = [
 Q("In most branches, the order of loss causes is process error, customer theft and:", ["Damage", "Staff dishonesty", "Supplier error", "Pricing"], 1,
   "Staff dishonesty comes some way behind the other two.", "Ch1 §2", "Why the rules exist"),
 Q("A shortage is dangerous to an honest employee because it:", ["Is deducted from wages", "Arrives as a number that cannot say what caused it", "Triggers dismissal", "Is assumed to be theft"], 1,
   "That ambiguity has nothing to do with whether you are honest.", "Ch1 §3", "Why the rules exist"),
 Q("The rules exist so that when something is wrong it can be:", ["Punished", "Traced to a cause rather than distributed across everybody nearby", "Recovered", "Explained to auditors"], 1,
   "They are not there because the shop suspects you; they are there so that it cannot.", "Ch1 §4", "Why the rules exist"),
 Q("Experienced staff follow these rules:", ["Less carefully than new staff", "More carefully than new staff", "Only when supervised", "As a formality"], 1,
   "Because self-protection is the more accurate description of what they are for.", "Ch1 §6", "Why the rules exist"),
 Q("A rule that seems pointless because you know you are honest is:", ["Safe to relax", "Precisely the rule to follow most carefully", "Worth questioning", "Aimed at others"], 1,
   "Your honesty is not in question to you; the rule exists for the day it is in question to somebody who was not there.", "Ch1 §7", "Why the rules exist"),
 Q("A login attaches every action to a person, which makes you accountable for what you did and:", ["Liable for the shift", "Not accountable for what you did not", "Responsible for the drawer", "Answerable to the supervisor"], 1,
   "Both halves matter, and the second is the one nobody explains.", "Ch2 §2", "Logins"),
 Q("The hardest of the three login rules is:", ["Not sharing your code", "Not using somebody else's", "Locking the terminal", "Changing it regularly"], 1,
   "Because refusing feels unhelpful when a colleague is stuck and a customer is waiting.", "Ch2 §4", "Logins"),
 Q("The right response when a colleague's code will not work is to:", ["Use yours for them", "Serve the customer yourself or fetch somebody who can", "Wait for a supervisor", "Note it and continue"], 1,
   "It takes the same time and leaves the record true.", "Ch2 §5", "Logins"),
 Q("Somebody who keeps pushing after you decline to share a code:", ["Has a genuine need", "Has told you something worth knowing", "Should be reported immediately", "Is testing you"], 1,
   "Anybody reasonable accepts the refusal at once.", "Ch2 §6", "Logins"),
 Q("An unlocked terminal under your name is available to:", ["Colleagues only", "Anybody who passes it, including a customer", "Nobody, briefly", "The next user"], 1,
   "And the times you will forget are the busy ones.", "Ch2 §7", "Logins"),
 Q("Cash rules are strictest because cash:", ["Is most valuable", "Can be lost without leaving a trace", "Is counted daily", "Attracts theft"], 1,
   "Everything else has to physically move.", "Ch3 §1", "Cash"),
 Q("Two people using one drawer means:", ["Faster service", "Neither can account for it", "Shared responsibility", "A supervisor must witness"], 1,
   "A shortage becomes a conversation with no way to answer it.", "Ch3 §2", "Cash"),
 Q("A drawer accepted without counting is:", ["Covered by the previous user", "One you have taken responsibility for on trust", "Checked at close", "The supervisor's risk"], 1,
   "If it was already short, it is short on your watch.", "Ch3 §3", "Cash"),
 Q("Counting where somebody can see is described as:", ["A check on you", "Protection for you", "A policy requirement", "Slower but necessary"], 1,
   "A count nobody witnessed is a count nobody can confirm.", "Ch3 §4", "Cash"),
 Q("Differences should be reported:", ["Above a threshold", "Every time, in either direction", "At the weekly count", "If unexplained"], 1,
   "A drawer that is over usually means a customer was overcharged.", "Ch3 §5", "Cash"),
 Q("Personal money should be kept:", ["In the drawer for safety", "Out of the till area entirely", "With the supervisor", "In a separate compartment"], 1,
   "Personal cash near a drawer produces a question nobody can answer cleanly.", "Ch3 §7", "Cash"),
 Q("A discount given without authority looks, in the records, identical to:", ["A promotion", "Money missing", "A price change", "A return"], 1,
   "Which is why the authority to reduce a price sits with specific people.", "Ch4 §2", "Discounts"),
 Q("The sentence offered for a friend expecting a discount is:", ["We do not do that", "I am not able to do prices, sorry — I would get in trouble", "Ask the manager", "Not today"], 1,
   "It moves the refusal from a judgement about them to a fact about your job.", "Ch4 §3", "Discounts"),
 Q("Serving yourself at the till is:", ["Efficient", "The thing that looks worst in a review even when correct", "Permitted with a witness", "Standard for staff purchases"], 1,
   "And it takes one minute to avoid.", "Ch4 §4", "Discounts"),
 Q("The shop's view of staff discount used for a friend is that:", ["Intent matters", "The discount is part of your pay and the amount is not the point", "It depends on the value", "It is a first-warning matter"], 1,
   "People are consistently surprised because they were not stealing.", "Ch4 §5", "Discounts"),
 Q("Goods due for disposal are:", ["Free to take", "Still the shop's property", "The finder's", "Written off already"], 1,
   "Their disposal is a decision somebody else is entitled to make.", "Ch4 §6", "Discounts"),
 Q("Almost nobody who is dismissed for dishonesty:", ["Denies it", "Set out to steal", "Acted alone", "Took large amounts"], 1,
   "Which is why the mechanism is worth understanding rather than just warning against.", "Ch5 §1", "The small thing"),
 Q("What changes after the first small thing is:", ["The amount immediately", "Nothing bad happens, and it stops feeling uncomfortable", "Somebody notices", "The records show it"], 1,
   "There is no threshold, only a gradient, visible only looking back.", "Ch5 §3", "The small thing"),
 Q("By the time anybody looks, what exists is:", ["A single event", "A pattern that cannot be explained as an accident", "An admission", "A shortage"], 1,
   "And the true explanation is not one anybody can act on.", "Ch5 §4", "The small thing"),
 Q("A line set at a reasonable amount rather than at zero:", ["Is practical", "Moves, and you will not notice it moving", "Is what policies say", "Works for most people"], 1,
   "Which is why the only reliable defence is nothing at all.", "Ch5 §5", "The small thing"),
 Q("Almost every serious case in retail was recoverable at the point where:", ["A manager intervened", "Somebody could still have mentioned it", "The amount was small", "The records were checked"], 1,
   "Which is why saying so early is survivable and saying nothing is often not.", "Ch5 §7", "The small thing"),
 Q("Seeing a customer take something, you must not:", ["Note their description", "Confront or follow them", "Tell anybody", "Continue serving"], 1,
   "Goods are insured and replaceable; you are not.", "Ch6 §2", "When you see something"),
 Q("If your branch instructs you to stop a shoplifter, that instruction:", ["Must be followed", "Is wrong and worth raising", "Applies only to supervisors", "Depends on the value"], 1,
   "No shop worth working for trades your safety for stock.", "Ch6 §2", "When you see something"),
 Q("Suspecting a colleague, you should not discuss it with other staff because:", ["It is confidential", "It spreads within a day and cannot be undone if you were wrong", "The supervisor forbids it", "It slows the investigation"], 1,
   "Say it once, upward, then say nothing.", "Ch6 §5", "When you see something"),
 Q("An amateur investigation can:", ["Speed things up", "Destroy evidence and make the case unprovable", "Confirm suspicions", "Protect the shop"], 1,
   "One of three reasons not to investigate, each sufficient alone.", "Ch6 §4", "When you see something"),
 Q("Reports should state facts rather than conclusions because a conclusion:", ["Takes longer", "Is not yours to make and may not be supportable", "Requires evidence", "Must be written"], 1,
   "'I saw X happen on Tuesday' is something you can stand behind.", "Ch6 §6", "When you see something"),
 Q("If somebody senior asks you to do something wrong:", ["Comply and report it", "Decline without drama and tell somebody above them", "Ask for it in writing", "Do it once"], 1,
   "Going along with it does not stay their responsibility.", "Ch6 §7", "When you see something"),
 Q("The single most important safety rule in the track is never to:", ["Work alone", "Put yourself between a person and the door", "Handle large cash", "Challenge a customer"], 1,
   "It applies to somebody taking goods and to anybody behaving aggressively.", "Ch6 §8", "When you see something"),
 Q("A miskey goes wrong for:", ["One product", "Two products at once", "The customer only", "The count only"], 1,
   "The customer is charged wrongly and both products' records are now wrong.", "Ch7 §2", "Where losses come from"),
 Q("Unrecorded damage belongs on the loss list because it:", ["Costs the most", "Corrupts the records so the loss cannot be told from a theft", "Is hardest to prevent", "Happens most often"], 1,
   "Which is the link between module 4 and this one.", "Ch7 §4", "Where losses come from"),
 Q("Signing for what did not arrive produces a loss that:", ["Is recovered from the supplier", "Looks exactly like something taken from the shop", "Shows immediately", "Is the driver's liability"], 1,
   "Invisible until a count.", "Ch7 §5", "Where losses come from"),
 Q("The five loss types share the property that they are attributable to:", ["The last person on shift", "Nobody", "The supervisor", "The system"], 1,
   "Which is exactly what makes them dangerous to everybody who works there.", "Ch7 §7", "Where losses come from"),
 Q("Learning the three near-identical lines in your section guards against:", ["Customer confusion", "Most of your own miskeys", "Pricing errors", "Stock loss"], 1,
   "A one-minute investment against a year of small errors.", "Ch7 §9", "Where losses come from"),
 Q("The ₦4,000 drawer shortage happened because two people had:", ["Shared a login", "Worked one drawer without counting at handover", "Miscounted the float", "Left it unlocked"], 1,
   "The supervisor had asked Ada to cover a break and the drawer carried on.", "Ch8 §2", "The short drawer"),
 Q("The shortage was eventually explained by:", ["A confession", "A voucher entered at the wrong value", "A customer refund", "A counting error"], 1,
   "Found by checking the transaction list rather than the people.", "Ch8 §4", "The short drawer"),
 Q("What changed afterwards was that Ada:", ["Refused to cover breaks", "Started counting at every handover, out loud", "Asked for her own drawer", "Reported the supervisor"], 1,
   "Two or three others copied her within a month without being instructed to.", "Ch8 §5", "The short drawer"),
 Q("The supervisor's lesson was to check the transactions:", ["After interviewing staff", "Before talking to anybody", "At the weekly count", "With the manager present"], 1,
   "Two honest people spent two days under suspicion for something a ten-minute look would have explained.", "Ch8 §7", "The short drawer"),
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

    rebalance(QUESTIONS, "shopfloor:money_honesty:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:money_honesty:checks")

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
        "title": "RF 5 — Money, Honesty and the Rules That Protect You",
        "desc": ("Why the controls exist to protect the person handling the money rather than "
                 "to police them. Logins, cash handling, discounts and staff purchases, how "
                 "honest people end up dismissed over something small, what to do when you "
                 "see something — including the safety rule that matters most — and where a "
                 "branch's losses actually come from."),
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
