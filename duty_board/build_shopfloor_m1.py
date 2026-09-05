#!/usr/bin/env python3
"""Build 'What This Job Is Actually For' into academy_shopfloor_data.json.

Module 1 of Retail Foundations — the entry-level track.

The estate has the till (Certified ZhiftPOS Operator) and the branch manager
(Retail Leadership Essentials) and nothing in between for the person who works
the floor. This track is that: what the job is, the customer, the shelf, stock
and dates, honesty, the shift, difficult moments, and getting better at it.

Three decisions that govern the whole track:

  SOFTWARE-AGNOSTIC. Nothing here assumes ZhiftPOS or any system. A business
  running on paper can use this track, and a learner who later takes the POS
  Operator certificate meets the machine there. Where a system is mentioned it
  is generic ("whatever your branch uses").

  WRITTEN FOR A FIRST JOB, WITHOUT CONDESCENSION. Many readers will be young
  and new to work. That means defining things (margin, shrinkage, rotation) and
  never implying the reader is slow for not knowing them. It does not mean
  simplifying the judgement — the hard parts of retail are hard for everybody.

  THE READER IS THE POINT. Retail Leadership is written for somebody managing
  people; this is written for the person being managed, and it says plainly
  what is in it for them: the job is a trade, it has a ladder, and the habits
  that get somebody promoted are learnable and few.

Running example: Okelewo Stores, seen from the floor rather than the office —
Ada, six weeks in at the Ibadan branch.

Run from the app package directory:  python3 build_shopfloor_m1.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_job"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("What you are actually being paid for", 10, """<p>Ask most people what a shop assistant does and they will say serving customers. That is part of it, and it is not the job. The job is that the branch trades well on the days you are working — and serving customers is one of about six things that make that happen.</p>

<p><b>The six, in the order the day meets them.</b></p>

<p><b>The stock is where customers can find it and buy it.</b> Goods in the stockroom earn nothing. A large share of everything a branch fails to sell was in the building at the time.</p>

<p><b>The shelf tells the truth.</b> Right price on the right item, nothing expired, nothing damaged left out for somebody to be sold by mistake.</p>

<p><b>Customers are served in a way that brings them back.</b> Not the same as being pleasant to them today, which is easier and worth less.</p>

<p><b>Money and goods are handled so that nothing goes missing.</b> Including the part that protects you, which Chapter 6 covers properly.</p>

<p><b>What you notice gets said.</b> You see things nobody else in the business sees, and information dies on the floor unless somebody carries it.</p>

<p><b>The shift runs whether or not anybody is watching.</b> Which is the whole of trust, and it is the thing that gets people promoted.</p>

<p><b>Why this framing matters on a slow afternoon.</b> If the job is serving customers, then a quiet hour is nothing to do. If the job is the six above, a quiet hour is the best part of the day: it is when the gaps get filled, the dates get checked, and the section gets put right. The difference between two people on the same shift, at the same pay, is almost entirely what they do when the shop is empty.</p>

<blockquote>WORTH KNOWING: The people who get promoted in retail are rarely the ones who are best with customers. They are the ones whose section is right when somebody walks past it unannounced.</blockquote>

<p><b>The part of the job nobody describes on a first day.</b> Most of a shift is not one task but a queue of small ones competing for the same pair of hands — a delivery half put away, a gap on the shelf, a customer approaching, a colleague asking for change. Nobody hands you the order. Working out what comes first, over and over, all day, is the actual skill, and it is why two people can work equally hard on the same shift and only one branch runs well.</p>

<p><b>And the reason the six are worth memorising.</b> When you are unsure whether something is your job, check it against the list. Filling a gap in somebody else's section is your job. Mentioning that a customer asked twice for something is your job. Standing at a till when there is no queue and the chilled section is empty is not, however busy it feels.</p>"""
, [
 C("A quiet hour on the shop floor is:",
   ["Nothing to do", "The best part of the day for the other five parts of the job",
    "A time to rest", "For paperwork only"], 1,
   "It is when the gaps get filled, the dates get checked and the section gets put right."),
 C("A large share of what a branch fails to sell was:",
   ["Never ordered", "In the building at the time",
    "Priced wrongly", "Out of season"], 1,
   "Goods sitting in the stockroom earn nothing."),
 C("Serving customers well is:",
   ["The whole job", "One of about six things the job consists of",
    "The manager's concern", "Only relevant when busy"], 1,
   "The job is that the branch trades well on the days you are working.")]),

("The trade you are learning", 10, """<p>Retail gets described as unskilled work by people who have never done it. It is worth knowing early that this is wrong, because believing it changes how you spend your first year.</p>

<p><b>What is actually being learned.</b> Judging how much of something to put out. Reading a customer well enough to know whether they want help or want to be left alone. Handling somebody angry without becoming angry. Spotting that a line is moving faster than usual before the shelf is empty. Counting accurately under pressure. Knowing which of forty things to do first when you are alone and it is busy.</p>

<p>Those are not simple, most people are not naturally good at them, and every one of them improves with deliberate practice.</p>

<p><b>The ladder, stated plainly.</b> Retail promotes from within more than almost any other sector, because the skills are hard to assess from a CV and easy to observe on a floor. The usual shape is assistant, then senior or keyholder, then supervisor, then branch manager — and the people at the top of it mostly started at the bottom of it. Your manager probably did.</p>

<p><b>What actually gets somebody moved up, in order.</b></p>

<p><b>Reliability first.</b> Turning up, on time, every time. It sounds too simple to matter and it is the single largest differentiator, because it is rarer than it should be and everything else depends on it.</p>

<p><b>Then the section that is right unwatched.</b> A person whose area is correct without supervision has demonstrated the thing a supervisor's job actually requires.</p>

<p><b>Then taking something on.</b> Owning a routine, training a new starter, running an ordering category. Nobody is promoted into responsibility they have never held; they are promoted into responsibility they have already been holding informally.</p>

<p><b>Being good with customers comes fourth.</b> It matters, and it is the one people assume comes first.</p>

<p><b>And the part nobody says out loud.</b> Some of what you learn here transfers to anything you do afterwards — dealing with people you did not choose, working to a standard when tired, being trusted with money. Even if retail is not your career, this year is not wasted unless you decide it is.</p>

<p><b>What the ladder looks like in money and hours, roughly.</b> Each step up is usually a modest rise in pay and a larger rise in what you are trusted with — keys, the safe, the rota, other people's mistakes. That is worth knowing in advance because the first step in particular can look like more responsibility for not much more money, and people turn it down. The rise matters less than the fact that step two is not available to anybody who never took step one.</p>

<p><b>How long it usually takes.</b> Faster than people expect in a growing business and slower in a stable one, because promotion needs somewhere to promote into. A branch that is opening sites is a branch that will need supervisors; a branch where nobody has left in three years is not. That is not about you, and it is worth knowing which kind you are in before concluding anything about your prospects.</p>

<blockquote>WORTH KNOWING: If you want to know whether you are seen as promotable, ask your manager directly what you would need to do. Most people never ask, most managers have an answer ready, and the question itself changes how they see you.</blockquote>"""
, [
 C("The single largest differentiator between staff is:",
   ["Being good with customers", "Reliability",
    "Product knowledge", "Speed"], 1,
   "It sounds too simple to matter, and everything else depends on it."),
 C("People are promoted into responsibility they:",
   ["Have never held, as a test", "Have already been holding informally",
    "Ask for formally", "Are trained for first"], 1,
   "Owning a routine, training a starter, running a category."),
 C("Retail promotes from within more than most sectors because the skills are:",
   ["Cheap to teach", "Hard to assess from a CV and easy to observe on a floor",
    "Not transferable", "Regulated"], 1,
   "Which is why the people at the top of the ladder mostly started at the bottom of it.")]),

("How the shop actually makes money", 10, """<p>You do not need to run the branch to benefit from knowing this, and knowing it changes what you pay attention to.</p>

<p><b>Margin, defined once.</b> If a tin is bought from the supplier for ₦700 and sold for ₦1,000, the difference is ₦300. That ₦300 is called the margin, and it is the only money the business ever actually has. Everything else — the rent, the power, the wages, whatever the owner is left with — comes out of the margins on the things sold that month.</p>

<p><b>Which is why the ₦1,000 sale is not worth ₦1,000 to the shop.</b> It is worth ₦300. That single fact explains almost every rule you will be given.</p>

<p><b>Three consequences you can act on.</b></p>

<p><b>A lost sale costs more than it looks.</b> When somebody wants something you do not have out, the branch does not lose ₦1,000 of revenue in a way that can be made up elsewhere — it loses ₦300 that will never exist. Ten of those in a day is ₦3,000 of margin gone, from a shop that might make ₦40,000 of margin on a good day.</p>

<p><b>One damaged item wipes out several sales.</b> If a ₦1,000 tin is dropped and written off, the shop loses the ₦700 it paid. Recovering ₦700 of margin at ₦300 a sale takes between two and three more sales. That is why the careful handling everybody nags about is not fussiness — it is arithmetic.</p>

<p><b>The same logic runs through everything else.</b> Expired stock, an item priced wrong, a discount given without authority: each costs margin, and margin is measured in sales you now have to make again.</p>

<p><b>What this is not.</b> Not a reason to be mean with customers or refuse reasonable things. A returned item from a customer who keeps shopping with you is cheap; a customer lost over ₦500 is expensive. The point is to know what things cost, so the judgement is informed rather than guessed.</p>

<p><b>Two things this does not mean, because both are common misreadings.</b> It does not mean the shop is being cheated when a customer returns something — returns are a normal cost of trading and a business that fights them loses more than it saves. And it does not mean prices are unfair: out of that ₦300 comes the rent, the power, the wages including yours, the stock that did not sell, and whatever is left over. The margin is not the owner's pocket money; it is what the whole operation runs on.</p>

<p><b>Where the margin actually goes, which surprises people.</b> On typical retail numbers, the majority of it is consumed by running the shop before anybody sees a profit. That is why a branch can be busy all day and still be marginal, and why the losses this track keeps mentioning — the expired tin, the dropped bottle, the gap on the shelf — land harder than their size suggests. They come out of the small part at the end, not the big part at the front.</p>

<blockquote>IMPLEMENTATION TIP: Ask somebody what the branch's rough margin percentage is — many will know it. If it is around 25%, then every ₦1,000 of stock damaged, expired or stolen needs ₦4,000 of extra sales to replace. That ratio is worth carrying in your head.</blockquote>"""
, [
 C("A ₦1,000 sale on a ₦700 item is worth to the shop:",
   ["₦1,000", "₦300",
    "₦700", "The full price less tax"], 1,
   "The margin is the only money the business ever actually has."),
 C("A ₦1,000 item dropped and written off costs the shop:",
   ["₦1,000 of revenue", "The ₦700 it paid, needing two or three more sales to recover",
    "Nothing, as it was not sold", "The margin only"], 1,
   "Careful handling is arithmetic rather than fussiness."),
 C("A returned item from a customer who keeps shopping is described as:",
   ["An avoidable loss", "Cheap",
    "The same as a write-off", "A supervisor matter"], 1,
   "A customer lost over ₦500 is the expensive outcome.")]),

("The five minutes at the start of your shift", 10, """<p>Most people arrive, put their things down and start doing whatever is in front of them. Five minutes of looking first changes the whole shift, and almost nobody does it.</p>

<p><b>What to find out, in order.</b></p>

<p><b>What happened before you.</b> Ask whoever is going off shift: anything I should know? Deliveries, problems, a customer coming back, something that broke, a section left half-done. Thirty seconds, and it stops you discovering all of it the hard way.</p>

<p><b>What is coming today.</b> A delivery, a promotion starting, somebody off sick, a busy period you can predict. Whatever your branch uses to say so — a board, a book, a briefing — read it rather than waiting to be told.</p>

<p><b>The state of your own area.</b> Walk it before you touch anything. What is empty, what is untidy, what is obviously wrong. You are building a short list, not fixing things yet.</p>

<p><b>Then decide the order.</b> This is the part that separates people. Given what you found, what has to happen before the shop gets busy, and what can wait until it goes quiet again? Filling gaps beats tidying. Anything a customer is waiting for beats both.</p>

<p><b>Why do it before starting rather than as you go.</b> Because once the shop is busy you stop being able to choose — you react to whatever is nearest and loudest, and the important thing that nobody is standing in front of never gets done. The five minutes buys you a plan that survives the rush.</p>

<p><b>And at the end of the shift, the mirror image.</b> Tell whoever is coming on what you told yourself at the start: what happened, what is outstanding, what they will meet. A handover that takes thirty seconds saves the next person an hour, and it will be you on the receiving end tomorrow.</p>

<blockquote>IMPLEMENTATION TIP: Do the five minutes for one week and notice how often you already knew about a problem before your manager mentioned it. Being the person who already knew is most of what a good reputation is made of.</blockquote>

<p><b>When there is nobody to hand over from.</b> Opening shifts, or a branch where the previous person has already gone. Then the five minutes is the same minus the first question: read whatever the branch leaves behind, walk the floor, and check anything that was mid-flight yesterday — a delivery part-away, a section left half-filled. The absence of a handover is itself information: something was left, and finding it now is cheaper than meeting it at eleven o'clock.</p>

<p><b>The one question worth asking even when nothing seems wrong.</b> Is anybody off today? It changes the whole shape of a shift — who covers the breaks, whether the delivery gets away on time, whether you will be alone on the floor at the busy hour. Knowing at nine is a plan; discovering at two is a scramble.</p>"""
, [
 C("Once the shop is busy you:",
   ["Work faster", "Stop being able to choose, and react to whatever is nearest and loudest",
    "Follow the plan naturally", "Need more staff"], 1,
   "The five minutes buys a plan that survives the rush."),
 C("Walking your area at the start of the shift is for:",
   ["Fixing what is wrong", "Building a short list",
    "Counting stock", "Reporting to the supervisor"], 1,
   "Deciding the order comes after the looking, not during it."),
 C("In deciding the order of work, filling gaps beats tidying, and both are beaten by:",
   ["The delivery", "Anything a customer is waiting for",
    "The count", "Cleaning"], 1,
   "A customer standing waiting is the one thing that cannot be scheduled around.")]),

("Knowing what you sell", 10, """<p>The fastest way to be useful in a shop is to know the stock. Not everything about everything — a few specific things about the lines that move.</p>

<p><b>What is worth knowing, per item, and it is less than people expect.</b></p>

<p><b>Where it is.</b> Being able to walk somebody to it rather than pointing vaguely is the single most-used piece of knowledge on any shop floor.</p>

<p><b>What it costs and what sizes it comes in.</b> Enough to answer without checking, on the lines people ask about most.</p>

<p><b>What it is for, in one sentence.</b> Not the label recited — what a customer would want to know. This one is stronger than it is medicine, this one is the cheaper version of the same thing.</p>

<p><b>What sits next to it in a customer's mind.</b> If we are out of the one they wanted, what would they accept instead? That single piece of knowledge turns lost sales into sales more often than anything else on this list.</p>

<p><b>How to learn it without being taught.</b> Nobody is going to run a course. Read the shelf-edge labels while you face up — you are standing there anyway. Ask a colleague what a line is actually for the first time you handle it. When a customer asks you something you cannot answer, find out the answer afterwards rather than only at the moment. Twenty items a week is a thousand a year, which is more than most branches carry.</p>

<p><b>The honest limits, which matter more in some shops than others.</b> There are questions you must not answer from memory or guesswork — anything medical, anything about what is safe to take with what, anything a customer might act on where being wrong could hurt them. The answer is not an approximation; it is the named person: the pharmacist, the supervisor, whoever your branch says. Saying <i>I do not want to guess with that, let me get somebody</i> costs a customer thirty seconds and is the most professional thing on this page.</p>

<blockquote>WATCH-OUT: The temptation to answer is strongest when you nearly know. That is exactly the case where being wrong is most likely and least obvious to the customer, because you will sound confident.</blockquote>

<p><b>The three questions worth having an answer ready for.</b> Every shop has them, and they arrive several times a day: where is it, is there any more out the back, and when is it coming in. The first two you can usually answer yourself. The third is the one people improvise on, and a guessed delivery date that turns out wrong costs a wasted journey and a customer who now believes the shop is unreliable. <i>I do not want to promise a day and be wrong — let me find out</i> is a better answer than a confident Thursday.</p>"""
, [
 C("The single most-used piece of product knowledge on a shop floor is:",
   ["The price", "Where the item is",
    "The size options", "What it is made of"], 1,
   "Being able to walk somebody to it rather than pointing vaguely."),
 C("Knowing what a customer would accept instead of an out-of-stock item:",
   ["Is the buyer's job", "Turns lost sales into sales more often than anything else",
    "Encourages substitution complaints", "Only applies to large ranges"], 1,
   "What sits next to it in a customer's mind."),
 C("The temptation to answer a question you should refer is strongest when you:",
   ["Know nothing about it", "Nearly know",
    "Are busy", "Are alone"], 1,
   "Which is exactly when being wrong is most likely and least obvious, because you will sound confident.")]),

("Standards, and why they exist", 10, """<p>Every shop has rules that seem excessive when you are new: face the products forward, never leave the till area unlocked, do not put your bag behind the counter, log out when you step away. It is worth understanding why they exist, because rules you understand survive a busy day and rules you have merely been told do not.</p>

<p><b>Most standards are one of three things.</b></p>

<p><b>A rule that protects the money.</b> Locking the till, not sharing a login, counting in front of somebody. These exist because money that cannot be attributed to a person becomes a suspicion attached to everybody near it.</p>

<p><b>A rule that protects you.</b> This is the category people miss, and Chapter 6 is entirely about it. Working under your own login means the day something is wrong at somebody else's till, it is provably not you. Bags out of the sales area means nobody can ever suggest anything about what is in yours.</p>

<p><b>A rule that protects the customer.</b> Date checks, allergen information, not selling damaged goods, the age-restricted rules where they apply. These are the ones with the least flexibility, because the cost of getting them wrong falls on somebody who trusted you.</p>

<p><b>The rules that look like fussiness and are not.</b> Facing products forward is not decoration — a shelf that looks tended sells more and gets stolen from less, which is measurable and slightly strange. Rotating stock so older dates come forward is not neatness; it is the difference between selling something and throwing it away. Nearly every standard that seems cosmetic turns out to have money behind it.</p>

<p><b>What to do with a rule that seems wrong.</b> Follow it and ask why. Sometimes the answer is good and you did not have the information. Sometimes the rule is genuinely out of date, and the person who asked is the reason it changed. What does not work is quietly not doing it, because the reason usually surfaces later at somebody's expense.</p>

<blockquote>WATCH-OUT: The rules most often broken are the ones with no visible consequence when broken once — the unlocked drawer, the shared login, the skipped date check. That is precisely why they are rules rather than instincts.</blockquote>

<p><b>Standards and speed, which people believe are opposed.</b> They are, briefly, while a habit is forming, and then they stop being. Locking a drawer takes two seconds once it is automatic and costs nothing thereafter; checking a date while you face a shelf adds no time at all once you are doing it as you go rather than as a separate task. Almost every standard that feels slow is slow because it is new, and the people who find them effortless are not faster — they folded them into something they were already doing.</p>"""
, [
 C("Working under your own login matters because:",
   ["It is faster", "The day something is wrong elsewhere, it is provably not you",
    "It tracks performance", "It is company policy"], 1,
   "A rule that protects you, not just the business."),
 C("Facing products forward is:",
   ["Decoration", "Measurable — a tended shelf sells more and gets stolen from less",
    "For inspections", "A manager's preference"], 1,
   "Nearly every standard that seems cosmetic turns out to have money behind it."),
 C("You are told to do something that seems pointless to you. The right response is to:",
   ["Quietly skip it", "Do it, and ask why",
    "Escalate it formally", "Wait until somebody reviews it"], 1,
   "The person who asks is sometimes the reason a genuinely outdated rule changes.")]),

("Where you fit", 10, """<p>Knowing who does what, and what your manager is dealing with, makes a job considerably easier to do well.</p>

<p><b>The people around you, roughly.</b> A supervisor or keyholder runs the shift you are on and is who you ask first. The branch manager is responsible for everything the branch does and is measured on things you do not see — sales against last year, stock losses, staff turnover. Above them somebody covers several branches. And there are people you rarely meet who decide what the shop sells and what it costs, which is why your manager sometimes cannot change a price or get a line back.</p>

<p><b>What your manager actually spends the day worrying about.</b> Not you, mostly. Whether the branch hits its numbers, whether stock is disappearing, whether people turn up, whether head office is about to ask something difficult. Understanding that explains a lot of otherwise puzzling behaviour — why they get sharp about a gap on a shelf, why they care so much about the rota, why the same reminder comes round monthly.</p>

<p><b>Which means the useful thing you can do is unprompted information.</b> Your manager cannot see the floor all day. When you tell them a line has been out for three days, a customer asked for something twice this week, or a delivery arrived short, you are giving them something they cannot get any other way. Staff who do this become trusted quickly, because it is rare and obviously useful.</p>

<p><b>Asking for help, without the two failure modes.</b> Asking for everything means nobody can rely on you working alone. Asking for nothing means problems get discovered late, when they cost more. The useful middle: try it, then ask — <i>I would do X, is that right?</i> That question takes ten seconds to answer, teaches you faster than being told, and shows you thought before speaking.</p>

<p><b>And a word about the person who trains you.</b> It is often whoever is available rather than whoever is best, and some of what you are shown will be that person's habits rather than the actual standard. If two people show you different things, it is fine to say so and ask which is right. That is not telling on anybody.</p>

<p><b>The colleague who is not doing their share.</b> It happens, it is genuinely irritating, and there are two things worth knowing. Most of it is not laziness — it is somebody who was never told what the standard was, or who is struggling with something you cannot see. And it is not yours to fix, which is a relief rather than a limitation: mention it once to your supervisor as information rather than as a complaint, and let the person whose job it is do the job. What corrodes a team is not the person doing less; it is everybody else discussing it for a month instead of saying it once.</p>

<blockquote>IMPLEMENTATION TIP: Get in the habit of one useful thing told to your supervisor per shift — a gap, a request, a problem. It costs nothing, and it is the cheapest way to be seen as somebody paying attention.</blockquote>"""
, [
 C("The most useful thing a floor staff member gives their manager is:",
   ["Faster work", "Unprompted information they cannot get any other way",
    "Fewer questions", "Longer hours"], 1,
   "Your manager cannot see the floor all day."),
 C("The useful middle between asking for everything and asking for nothing is:",
   ["Asking at the end of the shift", "Try it, then ask — I would do X, is that right?",
    "Asking only when stuck", "Writing questions down"], 1,
   "It takes ten seconds to answer and shows you thought before speaking."),
 C("If two colleagues show you different ways of doing something:",
   ["Pick either", "Say so and ask which is right",
    "Follow the senior one", "Do whichever is faster"], 1,
   "Some of what you are shown will be somebody's habits rather than the actual standard.")]),

("Okelewo Stores: Ada's first six weeks", 10, """<p>Ada joined the Ibadan branch of Okelewo Stores as a shop assistant with no retail experience. Six weeks in, her supervisor described her as the best new starter in two years. What she actually did is unremarkable and worth reading closely.</p>

<p><b>Week one — she wrote things down.</b> A small notebook: where things were, what she was told, questions she could not ask in the moment. She stopped needing it by week three, but in week one it meant she rarely asked the same thing twice, which people notice more than they notice the asking.</p>

<p><b>Week two — she found out what the branch actually sold.</b> Not by being taught. She read shelf labels while facing up, asked one colleague per shift what a line was for, and wrote down the answers. By week four she could answer most customer questions on her own section.</p>

<p><b>Week three — she started the five minutes.</b> Nobody told her to. She had noticed that she spent the first hour of every shift discovering problems, and that the person going off shift knew about most of them already.</p>

<p><b>Week four — she told the supervisor something.</b> A brand of soap had been out for four days, and two customers had asked for it. Small, but it was the first time anybody had brought that upward without being asked, and the supervisor remembered it.</p>

<p><b>Week five — she said she did not know.</b> A customer asked whether a medicine was safe with something they were already taking. Ada said she did not want to guess and fetched the pharmacist. The pharmacist later said it was the right call and that new staff frequently guess.</p>

<p><b>Week six — she asked the question.</b> What would I need to do to be considered for the senior role? Her supervisor gave her three things. None of them was working harder.</p>

<p><b>What none of this required.</b> Being naturally good with people. Working longer than anybody else. Knowing anything about retail before she started. Every single thing on the list is available to anybody who decides to do it, which is the point of the example and of this whole track.</p>

<blockquote>IMPLEMENTATION TIP: Pick one of Ada's six for your next fortnight. The notebook and the five minutes are the two that produce a visible difference fastest, and neither requires anybody's permission.</blockquote>

<p><b>What did not happen in Ada's six weeks, and is worth saying.</b> She was not brilliant. She did not transform the branch. Two of the six weeks she was tired and did the minimum, and the notebook has three days missing from week two. The record is unremarkable on purpose — a description of somebody doing a few sensible things fairly consistently, not a model employee nobody can match. The reason her supervisor noticed is that the bar is lower than people assume, and almost nobody clears it deliberately.</p>"""
, [
 C("Ada's notebook meant that in week one she:",
   ["Learned faster than others", "Rarely asked the same thing twice",
    "Needed less supervision", "Impressed the manager"], 1,
   "Which people notice more than they notice the asking."),
 C("When asked whether a medicine was safe alongside another, Ada:",
   ["Gave her best answer", "Said she did not want to guess and fetched the pharmacist",
    "Read the label aloud", "Suggested an alternative"], 1,
   "The pharmacist later said new staff frequently guess."),
 C("What Ada's six weeks did not require was:",
   ["Attention", "Being naturally good with people, or working longer than anybody else",
    "Curiosity", "Reliability"], 1,
   "Every item on the list is available to anybody who decides to do it.")]),

("Review, and what this track covers", 10, """<p>The short version of this module, then what is coming.</p>

<p><b>The job is six things, not one.</b> Stock where customers can buy it, a shelf that tells the truth, service that brings people back, money and goods handled so nothing goes missing, what you notice getting said, and the shift running whether or not anybody is watching.</p>

<p><b>The quiet hour is the job.</b> The difference between two people on the same shift and the same pay is mostly what they do when the shop is empty.</p>

<p><b>It is a trade with a ladder.</b> Reliability first, then a section that is right unwatched, then taking something on. Being good with customers comes fourth, and everybody assumes it comes first.</p>

<p><b>Margin is the only real money.</b> A ₦1,000 sale on a ₦700 item is worth ₦300, which is why a damaged item costs two or three sales and why every rule about care and dates has arithmetic behind it.</p>

<p><b>Five minutes at the start.</b> What happened before you, what is coming, the state of your area, then the order of work. Handover at the end, because tomorrow you are the one receiving it.</p>

<p><b>Know where things are, what they cost, what they are for, and what people take instead.</b> And refuse to guess on anything a customer might act on.</p>

<p><b>Standards protect the money, the customer, or you.</b> The third category is the one people miss.</p>

<p><b>Tell somebody one useful thing per shift.</b> It is rare, it is obviously useful, and it costs nothing.</p>

<p><b>What the rest of this track covers.</b> The customer in front of you, and what service actually consists of. The shelf — gaps, facing, and why availability is the largest thing you influence. Stock, dates and rotation. Money and honesty, including the part that protects you. Working a shift with other people. Difficult moments — complaints, anger, theft, emergencies. And getting better: what to practise, and how to become the person they promote.</p>

<blockquote>IMPLEMENTATION TIP: Before the next module, do the five minutes at the start of one shift and tell your supervisor one useful thing. Both take under ten minutes in total and you will have already changed how the shift goes.</blockquote>

<p><b>One thing to carry out of this module above the rest.</b> The job is not what happens when somebody is watching. Every other idea here — the quiet hour, the section that is right unwatched, the standards that protect you, the information nobody asked you for — is the same idea approached from a different side. A person who works the same whether or not the supervisor is on the floor is, in practical terms, already doing the supervisor's job, and that is generally noticed within a few months.</p>"""
, [
 C("The difference between two people on the same shift at the same pay is mostly:",
   ["Natural ability", "What they do when the shop is empty",
    "Experience", "Which section they work"], 1,
   "Which is why the quiet hour is the job rather than a break from it."),
 C("In the promotion order, being good with customers comes:",
   ["First", "Fourth",
    "Second", "Last"], 1,
   "After reliability, a section right unwatched, and taking something on."),
 C("The category of standards people most often miss is the one that protects:",
   ["The money", "You",
    "The customer", "The stock"], 1,
   "Working under your own login means the day something is wrong elsewhere, it is provably not you.")]),
]


QUESTIONS = [
 Q("The job is best described as:", ["Serving customers", "The branch trading well on the days you work", "Keeping the shop tidy", "Operating the till"], 1,
   "Serving customers is one of about six things that make it happen.", "Ch1 §1", "What the job is"),
 Q("Goods in the stockroom:", ["Are safer there", "Earn nothing", "Count as stock cover", "Are the manager's concern"], 1,
   "A large share of what a branch fails to sell was in the building at the time.", "Ch1 §3", "What the job is"),
 Q("A shelf that tells the truth means right price, nothing expired and:", ["Full facings", "Nothing damaged left out to be sold by mistake", "Correct order", "Clear labels"], 1,
   "The customer should not be able to buy something they should not have been sold.", "Ch1 §4", "What the job is"),
 Q("Information you notice on the floor:", ["Reaches management automatically", "Dies unless somebody carries it", "Is recorded by the system", "Is the supervisor's job to find"], 1,
   "You see things nobody else in the business sees.", "Ch1 §7", "What the job is"),
 Q("A quiet hour is:", ["Time to rest", "When gaps get filled and the section gets put right", "For customer service only", "Unproductive by nature"], 1,
   "If the job were only serving customers, a quiet hour would be nothing to do.", "Ch1 §9", "What the job is"),
 Q("People promoted in retail are rarely the best with customers; they are the ones whose:", ["Sales are highest", "Section is right when somebody walks past unannounced", "Hours are longest", "Till is fastest"], 1,
   "The shift running unwatched is the whole of trust.", "Ch1 §10", "What the job is"),
 Q("Retail skills are learned by:", ["Natural aptitude", "Deliberate practice", "Length of service", "Formal training only"], 1,
   "Most people are not naturally good at any of them.", "Ch2 §3", "The trade"),
 Q("The usual retail ladder runs assistant, senior or keyholder, supervisor and:", ["Head office", "Branch manager", "Area manager", "Owner"], 1,
   "And the people at the top of it mostly started at the bottom of it.", "Ch2 §4", "The trade"),
 Q("Reliability is described as:", ["A basic expectation", "The single largest differentiator", "Less important than skill", "Assumed of everybody"], 1,
   "It is rarer than it should be and everything else depends on it.", "Ch2 §6", "The trade"),
 Q("Nobody is promoted into responsibility they have never held. They are promoted into responsibility they:", ["Trained for", "Were already holding informally", "Applied for", "Were assessed on"], 1,
   "Owning a routine, training a new starter, running a category.", "Ch2 §8", "The trade"),
 Q("Asking your manager what you would need to do to be promoted:", ["Looks presumptuous", "Changes how they see you", "Should wait for a review", "Rarely gets an answer"], 1,
   "Most people never ask, and most managers have an answer ready.", "Ch2 §11", "The trade"),
 Q("If an item costs ₦700 and sells for ₦1,000, the margin is:", ["₦1,000", "₦300", "₦700", "30% of cost"], 1,
   "The only money the business ever actually has.", "Ch3 §2", "Margin"),
 Q("Rent, power and wages are paid out of:", ["Total sales", "The margins on what was sold", "The owner's capital", "Turnover"], 1,
   "Which is why a sale is not worth its price to the shop.", "Ch3 §2", "Margin"),
 Q("Ten lost sales in a day, at ₦300 margin each, cost:", ["₦10,000 of revenue", "₦3,000 of margin that will never exist", "Nothing recoverable", "The cost price only"], 1,
   "From a shop that might make ₦40,000 of margin on a good day.", "Ch3 §5", "Margin"),
 Q("Recovering the loss on one damaged ₦1,000 item takes roughly:", ["One more sale", "Two to three more sales", "Ten more sales", "No extra sales"], 1,
   "The shop loses the ₦700 it paid, recovered at ₦300 a sale.", "Ch3 §6", "Margin"),
 Q("At a 25% margin, every ₦1,000 of stock lost needs extra sales of:", ["₦1,000", "₦4,000", "₦2,500", "₦250"], 1,
   "A ratio worth carrying in your head.", "Ch3 §9", "Margin"),
 Q("The five minutes at the start of a shift begins with:", ["Checking the till", "Asking whoever is going off shift what you should know", "Walking your area", "Reading the board"], 1,
   "Thirty seconds that stops you discovering it all the hard way.", "Ch4 §3", "Starting the shift"),
 Q("Walking your area at shift start is for building:", ["A cleaning plan", "A short list", "A stock count", "A report"], 1,
   "You are not fixing things yet.", "Ch4 §5", "Starting the shift"),
 Q("In ordering the day's work, what beats both filling gaps and tidying is:", ["The delivery", "Anything a customer is waiting for", "The count", "The rota"], 1,
   "It is the one thing that cannot be scheduled around.", "Ch4 §6", "Starting the shift"),
 Q("The reason to plan before starting rather than as you go is that once busy you:", ["Work faster", "React to whatever is nearest and loudest", "Forget the list", "Need permission"], 1,
   "The important thing nobody is standing in front of never gets done.", "Ch4 §7", "Starting the shift"),
 Q("A thirty-second handover at the end of a shift saves the next person:", ["A few minutes", "About an hour", "Nothing measurable", "A supervisor conversation"], 1,
   "And tomorrow you are the one receiving it.", "Ch4 §8", "Starting the shift"),
 Q("The most-used product knowledge is:", ["The price", "Where the item is", "The brand", "The size"], 1,
   "Walking somebody to it rather than pointing vaguely.", "Ch5 §3", "Product knowledge"),
 Q("Knowing what a customer would accept instead of an out-of-stock line:", ["Risks complaints", "Turns lost sales into sales", "Is the buyer's job", "Applies only to large ranges"], 1,
   "What sits next to it in a customer's mind.", "Ch5 §6", "Product knowledge"),
 Q("Learning twenty items a week amounts to:", ["A hundred a year", "A thousand a year", "Most of a section", "More than needed"], 1,
   "Which is more than most branches carry.", "Ch5 §7", "Product knowledge"),
 Q("Questions you must not answer from memory include anything:", ["About price", "A customer might act on where being wrong could hurt them", "About availability", "About the business"], 1,
   "The answer is the named person, not an approximation.", "Ch5 §8", "Product knowledge"),
 Q("Saying you do not want to guess and fetching somebody costs the customer:", ["A lost sale", "Thirty seconds", "Their confidence in you", "A wait of several minutes"], 1,
   "And is the most professional thing available in that moment.", "Ch5 §8", "Product knowledge"),
 Q("Standards generally protect the money, the customer, or:", ["The stock", "You", "The brand", "The manager"], 1,
   "The third is the category people miss.", "Ch6 §2", "Standards"),
 Q("Money that cannot be attributed to a person becomes:", ["A write-off", "A suspicion attached to everybody near it", "An accounting adjustment", "The supervisor's problem"], 1,
   "Which is why logins are not shared and counts are witnessed.", "Ch6 §3", "Standards"),
 Q("Rotating stock so older dates come forward is:", ["Neatness", "The difference between selling something and throwing it away", "A display standard", "Optional on fast lines"], 1,
   "Nearly every standard that seems cosmetic has money behind it.", "Ch6 §6", "Standards"),
 Q("The rules most often broken are those with:", ["The least logic", "No visible consequence when broken once", "The most inconvenience", "The least supervision"], 1,
   "Which is precisely why they are rules rather than instincts.", "Ch6 §8", "Standards"),
 Q("A rule that seems wrong should be:", ["Ignored", "Followed, and questioned", "Reported", "Applied selectively"], 1,
   "Quietly not doing it fails later at somebody's expense.", "Ch6 §7", "Standards"),
 Q("Your branch manager is mostly worrying about:", ["Your performance", "The numbers, stock losses, attendance and head office", "Customer service scores", "The rota alone"], 1,
   "Understanding that explains a lot of otherwise puzzling behaviour.", "Ch7 §3", "Where you fit"),
 Q("The reason a manager sometimes cannot change a price is that:", ["It needs approval", "Those decisions are made by people you rarely meet", "The system blocks it", "It requires a promotion"], 1,
   "Range and pricing sit above branch level.", "Ch7 §2", "Where you fit"),
 Q("Telling your supervisor one useful thing per shift is:", ["Expected of everybody", "The cheapest way to be seen as paying attention", "A formal requirement", "Best saved for reviews"], 1,
   "A gap, a request, a problem.", "Ch7 §7", "Where you fit"),
 Q("'I would do X, is that right?' is better than asking outright because it:", ["Saves the supervisor time", "Teaches you faster and shows you thought first", "Avoids interrupting", "Demonstrates confidence"], 1,
   "The useful middle between asking for everything and asking for nothing.", "Ch7 §5", "Where you fit"),
 Q("Some of what a trainer shows you may be:", ["Out of date policy", "Their habits rather than the standard", "Deliberately simplified", "Branch-specific rules"], 1,
   "If two people show you different things, it is fine to ask which is right.", "Ch7 §6", "Where you fit"),
 Q("Ada's notebook in week one meant she:", ["Learned the stock", "Rarely asked the same thing twice", "Impressed the supervisor", "Needed no training"], 1,
   "People notice repeated questions more than they notice questions.", "Ch8 §2", "Ada"),
 Q("Ada learned the range by:", ["Formal training", "Reading shelf labels while facing up and asking one colleague per shift", "Studying at home", "Shadowing the supervisor"], 1,
   "By week four she could answer most questions on her section.", "Ch8 §3", "Ada"),
 Q("Ada started the five minutes because she noticed:", ["Her supervisor did it", "She spent the first hour discovering problems others already knew about", "It was in the handbook", "The shift was quiet"], 1,
   "Nobody told her to.", "Ch8 §4", "Ada"),
 Q("What Ada told the supervisor in week four was:", ["A customer complaint", "A soap brand out for four days that two customers had asked for", "A stock error", "A rota problem"], 1,
   "The first time anybody had brought that upward without being asked.", "Ch8 §5", "Ada"),
 Q("When Ada asked what she would need to do for the senior role, the three things given:", ["Included working harder", "Did not include working harder", "Were about sales", "Were about attendance only"], 1,
   "None of them was effort; all were habits.", "Ch8 §7", "Ada"),
 Q("The two of Ada's habits that produce a visible difference fastest are:", ["Product knowledge and service", "The notebook and the five minutes", "Reliability and speed", "Asking and reporting"], 1,
   "And neither requires anybody's permission.", "Ch8 §9", "Ada"),
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

    rebalance(QUESTIONS, "shopfloor:the_job:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:the_job:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))
    weak = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch if len(c.get("why") or "") < 40]
    if weak:
        raise SystemExit("ABORT: weak rationale:\n  %s" % "\n  ".join(weak))

    mod = {
        "title": "RF 1 — What This Job Is Actually For",
        "desc": ("The shop floor job, stated properly: the six things it consists of, why the "
                 "quiet hour is the job rather than a break from it, how the shop makes money "
                 "and what that means for you, the five minutes at the start of a shift, "
                 "knowing what you sell, why the standards exist, and what actually gets "
                 "somebody promoted."),
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
