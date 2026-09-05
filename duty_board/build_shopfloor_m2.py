#!/usr/bin/env python3
"""Build 'The Customer In Front Of You' into academy_shopfloor_data.json.

Module 2 of Retail Foundations.

The risk in a customer-service module is that it becomes a list of pleasantries
— smile, greet, be helpful — which everybody already agrees with and nobody can
act on. This one is built on the opposite bet: service is a small number of
specific, learnable behaviours, most of which are about attention and timing
rather than personality, and the whole module is written so that a shy person
can do all of it.

Two positions the module takes deliberately:

  SERVICE IS NOT NICENESS. The measurable things — being found when needed,
  knowing the answer, moving the queue, doing what you said — beat warmth on
  every study anybody has run. Warmth without those is a pleasant experience of
  being failed.

  THE CUSTOMER IS NOT ALWAYS RIGHT, AND SAYING SO IS KINDER. Staff told the
  slogan discover on their first hard day that it is false, and are left with
  nothing. The useful version: the customer is always to be taken seriously,
  which is a different claim and one that survives contact.

The complaint material stops short of the genuinely difficult cases — anger,
abuse, threat, suspected theft — which are module 7's territory. This module
covers the ordinary complaint, which is far more common and where most of the
recoverable value sits.

Run from the app package directory:  python3 build_shopfloor_m2.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "customers"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("What service actually is", 10, """<p>Almost everybody agrees that good service matters and almost nobody can say what it consists of. The usual answers — be friendly, be helpful, smile — are true, unmeasurable, and useless to somebody trying to get better.</p>

<p><b>Here is the specific version. Four things, in the order customers care about them.</b></p>

<p><b>Being findable.</b> A customer who needs help and cannot find anybody is having the worst version of the experience, and it is the commonest complaint in retail anywhere. Not being hidden in an aisle with your back turned is worth more than any amount of charm at the moment somebody finally reaches you.</p>

<p><b>Knowing the answer, or getting it fast.</b> Where it is, what it costs, whether there is more. The customer's question is nearly always about resolving something, and the person who resolves it is the good experience.</p>

<p><b>The queue moving.</b> More on this in Chapter 4, because what actually annoys people is not the length of a queue.</p>

<p><b>Doing what you said you would.</b> If you say you will check, check. If you say it comes Thursday, it needs to be Thursday or the customer needs to know it is not. This is the one that builds the thing shops call loyalty, and it is entirely a matter of follow-through rather than personality.</p>

<p><b>Where warmth fits.</b> It makes all four better and it substitutes for none of them. A friendly person who cannot find you, does not know, and never comes back with the answer has given somebody a pleasant experience of being failed. A quiet person who is present, knows, and follows through is who customers actually come back for.</p>

<p><b>Which is the point for anybody who is not naturally outgoing.</b> Every item on that list is available to a shy person. Service is a set of behaviours, not a temperament, and the belief that you have to be a certain kind of person to be good at it stops people trying.</p>

<blockquote>WORTH KNOWING: When a shop asks customers why they stopped shopping somewhere, the answer is rarely rudeness. It is usually that the thing they wanted was never there, or that somebody said they would sort something out and did not.</blockquote>

<p><b>Why the four are worth learning as a list.</b> Because on a bad day you cannot do all of them, and knowing the order tells you what to protect. If the shop is short-staffed and you can only manage one thing, be findable. If you are new and know almost nothing about the range, follow through on what you promise — that one requires no product knowledge at all and it is the one that makes regulars.</p>

<p><b>The measure that tells you how a shop is really doing.</b> Not whether customers are greeted, which is easy to train and easy to fake, but whether somebody who walks in wanting one specific thing walks out with it. That single question captures availability, product knowledge, findability and follow-through at once — and it is the question a customer is silently asking every time they come in.</p>

<p><b>Why this module comes before the shelf rather than after it.</b> Because the habits here are the ones you can use on your first shift, before you know the range, the stockroom, or where anything lives. Being findable, having four sentences ready, and accepting a no cleanly require nothing but a decision. Everything in the next module requires knowing the shop.</p>"""
, [
 C("The commonest complaint in retail anywhere is:",
   ["Rudeness", "Not being able to find anybody to help",
    "High prices", "Long queues"], 1,
   "Being findable is the first of the four things customers actually care about."),
 C("A friendly person who cannot find you, does not know, and never returns with the answer has given:",
   ["Good service in difficult circumstances", "A pleasant experience of being failed",
    "The best available outcome", "Acceptable service"], 1,
   "Warmth makes the four better and substitutes for none of them."),
 C("For somebody who is not naturally outgoing, the useful fact is that service is:",
   ["Mostly personality", "A set of behaviours",
    "Best left to others", "Learned slowly"], 1,
   "Every item on the list is available to a shy person.")]),

("Reading what somebody wants", 10, """<p>Two customers walk in. One wants to be left alone entirely and will be irritated by an approach. The other has been looking for two minutes and is getting annoyed that nobody has offered. Treating both the same fails one of them, and telling them apart is a genuine skill you can practise.</p>

<p><b>The signals, and they are reliable.</b> Somebody who wants help looks up and around rather than at the shelf; slows or stops in the aisle; looks at you as you pass; picks something up and puts it back twice; has already walked the same stretch once. Somebody who does not want help is moving with purpose, has a list, is on the phone, or is scanning steadily along a shelf — which looks like being lost and is not.</p>

<p><b>The safe opening, when you are not sure.</b> Be visible, be near, and let them start. Most shops' scripted greeting — can I help you — gets a reflexive no from people who did want help, because it arrives as a challenge. <i>Let me know if you need anything</i>, said while continuing what you were doing, gets a much higher hit rate for the same effort.</p>

<p><b>The one exception worth making.</b> Somebody who has been standing in one place for more than a minute or two is stuck, and stuck people rarely ask. That is the moment to approach directly, and the useful phrasing names the section rather than the person: <i>are you finding what you need in the cold section?</i> is easier to answer than a general offer.</p>

<p><b>What to do with a no.</b> Accept it, once, cleanly, and stay visible. The failure is not the first refusal; it is following somebody around afterwards, which converts a customer who wanted privacy into one who leaves.</p>

<p><b>And the situations where you always approach.</b> Somebody carrying more than they can hold. Anybody with a child who is struggling. An older customer reaching for something high. Somebody standing at an unstaffed counter. In each case the need is visible and asking permission first is a formality that wastes the moment.</p>

<blockquote>IMPLEMENTATION TIP: For one shift, notice which customers look up as you pass and which do not, and do nothing else with the observation. The pattern becomes obvious within an hour, and after that you will find you are reading it without effort.</blockquote>

<p><b>The thing that makes all of this harder in practice.</b> You are usually doing something else. Reading customers while facing a shelf, carrying stock, or counting is the actual skill, and the failure mode is not misreading people — it is being so absorbed in a task that you never look up at all. Somebody who glances up every minute or so and reads badly will serve more customers than somebody who reads brilliantly and never looks.</p>

<p><b>And where the reading genuinely fails, which is worth naming.</b> Somebody who has been in three times looking at the same thing and has not bought it is usually deciding on price, and an approach at that moment tends to lose the sale rather than make it. Somebody in a hurry with a child does not want a conversation about alternatives. Reading people is a probability rather than a rule, and being wrong occasionally is the cost of trying at all — the alternative is treating everybody identically, which is wrong more often.</p>"""
, [
 C("Somebody scanning steadily along a shelf is:",
   ["Lost and needs help", "Working through it, and does not",
    "Waiting to be served", "About to complain"], 1,
   "Steady scanning looks like being lost and is not — they are working through the shelf deliberately."),
 C("'Can I help you' often gets a reflexive no because it arrives as:",
   ["An interruption", "A challenge",
    "A sales approach", "A formality"], 1,
   "'Let me know if you need anything' gets a much higher hit rate for the same effort."),
 C("The failure with a customer who has declined help is:",
   ["Approaching in the first place", "Following them afterwards",
    "Staying nearby", "Not asking twice"], 1,
   "Accept the refusal once, cleanly, and stay visible.")]),

("The four sentences worth having ready", 10, """<p>Most awkward moments on a shop floor come from not having words prepared for a situation that arrives several times a day. These four cover most of them.</p>

<p><b>When you do not know: <i>I do not want to guess at that — give me a moment and I will find out.</i></b> Customers do not mind you not knowing. They mind being given a confident answer that turns out to be wrong, because they acted on it. Saying you will find out is not weakness; it is the only version of the exchange where the customer ends up with something true.</p>

<p><b>When you are out of stock: <i>We do not have it today. Would this do instead, or shall I find out when it is coming?</i></b> The bad version stops at the first sentence and lets the customer leave. The good version offers the two things that actually help, and one of them frequently saves the sale.</p>

<p><b>When somebody is annoyed: <i>I am sorry — tell me what happened.</i></b> Two things at once: the apology, which costs nothing and defuses most of it, and the invitation, which gets you the facts. Notice that it does not admit fault or promise anything, so it is safe to say before you know whether the shop is in the wrong.</p>

<p><b>When you cannot do what they want: <i>I am not able to do that myself, but let me get somebody who can decide.</i></b> The important word is <i>myself</i>. It is honest about your limits without making the customer feel refused, and it moves the situation toward somebody with the authority instead of leaving it stuck with somebody without it.</p>

<p><b>Why prepared sentences rather than natural conversation.</b> Because under pressure, in front of somebody unhappy, nobody is at their most articulate. Having the words already means the difficult moment is about the problem rather than about finding something to say — and the customer experiences somebody calm.</p>

<p><b>The one to avoid entirely.</b> <i>That is not my department.</i> It is often true and it lands as refusal. <i>Let me find the person who deals with that</i> says the same thing and takes the same ten seconds.</p>

<blockquote>IMPLEMENTATION TIP: Say the four out loud once, in your own words, before your next shift. They only work if they sound like you — a sentence recited from a manual is audible as one, and a customer trusts it less than an awkward version that is clearly yours.</blockquote>

<p><b>A fifth, for when somebody asks for a discount.</b> It happens constantly in this market and new staff find it uncomfortable, because refusing feels rude and agreeing is not theirs to do. <i>I am not able to change prices myself — would you like me to ask?</i> resolves it in one sentence: honest, not a refusal, and it moves the decision to whoever actually holds it. The answer is often no, and that is fine; the customer wanted the question asked more than they expected it granted.</p>

<p><b>The tone that makes all five work.</b> Ordinary. Not deferential, not scripted, not bright — the voice you would use telling a neighbour something factual. New staff frequently overcorrect into a performance because they think that is what service sounds like, and customers hear it immediately. The sentences above work because they are plain, and they stop working the moment they sound like lines.</p>"""
, [
 C("Customers mind less that you do not know than that:",
   ["You took time to find out", "You gave a confident answer that turned out wrong",
    "You referred them elsewhere", "You seemed uncertain"], 1,
   "A wrong answer given confidently is worse than no answer, because the customer acted on it."),
 C("'I am sorry — tell me what happened' is safe to say before knowing the facts because it:",
   ["Commits to a resolution", "Does not admit fault or promise anything",
    "Delays the complaint", "Transfers responsibility"], 1,
   "The apology defuses most of it and the invitation gets you the facts."),
 C("The important word in 'I am not able to do that myself' is:",
   ["Able", "Myself",
    "Not", "That"], 1,
   "It is honest about your limits without making the customer feel refused.")]),

("Queues, and what actually annoys people", 10, """<p>People will wait. What they will not tolerate is waiting while nothing appears to be happening, and the difference between those two explains almost every queue complaint.</p>

<p><b>What customers actually react to, in order.</b></p>

<p><b>A queue that is not moving.</b> Four people served briskly feels shorter than two people while somebody hunts for a price. Movement is the whole perception.</p>

<p><b>Being ignored while they wait.</b> A queue where staff have not acknowledged anybody feels far longer than one where somebody said a word.</p>

<p><b>Somebody else being served first.</b> This produces more genuine anger than a long wait, because it feels like unfairness rather than inconvenience.</p>

<p><b>Visible staff who are not serving.</b> Whatever you are doing, a waiting customer sees somebody available. This one is worth knowing because you will be the person restocking a shelf ten feet from a queue.</p>

<p><b>What you can do without authority.</b> Acknowledge the queue — a look and a nod to the person at the back costs nothing and resets their clock. If you are near and free, open a second point or take the next person. If you cannot serve, say something true: <i>somebody will be with you shortly</i> only if it is so. And if you are the one holding the queue up — a price check, a difficult transaction — say so to the people waiting rather than working in silence.</p>

<p><b>The single highest-value habit.</b> Watch the queue rather than your own task when the shop is busy. The person who notices it is building at three rather than at six is the person who can do something about it, and noticing is genuinely most of it.</p>

<p><b>And when it goes wrong anyway.</b> A customer who has waited too long is owed an acknowledgement, not an excuse. <i>Sorry for the wait</i> ends it. <i>Sorry, we are short-staffed today</i> invites a conversation about the shop's problems, which the customer did not come for and cannot help with.</p>

<p><b>The queue you can see and the one you cannot.</b> People waiting at a counter are visible. People waiting for somebody to appear at a deli, a service desk, or an unstaffed section are not — they wait longer, complain less, and leave more often. If your branch has a counter that is not permanently staffed, walking past it every few minutes is worth more than anything you can do at the till, because nobody else will notice that queue at all.</p>

<p><b>What not to do when a queue is bad.</b> Do not speed up in a way that shows. A visibly rushed transaction makes the person being served feel processed and the people waiting feel guilty, and it produces errors that cost more time than they save. The right response to pressure is steadiness plus acknowledgement, which is counterintuitive and correct: the queue moves at nearly the same speed and everybody's experience of it improves.</p>

<blockquote>WORTH KNOWING: Four served briskly beats two served slowly, every time, for the same total wait. If you can only influence one thing about a queue, influence whether it is visibly moving.</blockquote>"""
, [
 C("What produces more genuine anger than a long wait is:",
   ["A rude assistant", "Somebody else being served first",
    "A price error", "A closed till"], 1,
   "It feels like unfairness rather than inconvenience."),
 C("A customer who has waited too long is owed:",
   ["An explanation", "An acknowledgement",
    "A discount", "A supervisor"], 1,
   "'Sorry, we are short-staffed' invites a conversation about the shop's problems that the customer cannot help with."),
 C("If you can influence only one thing about a queue, influence:",
   ["Its length", "Whether it is visibly moving",
    "How many tills are open", "Who joins it"], 1,
   "Four served briskly feels shorter than two served slowly.")]),

("The complaint, worked properly", 10, """<p>An ordinary complaint — a faulty item, a wrong price, something that was promised and did not happen — is the most recoverable situation in retail, and most of the recovery is in the first thirty seconds.</p>

<p><b>The five steps, in order, and the order matters.</b></p>

<p><b>Listen to the end.</b> Do not begin solving while they are still talking. Most people arrive with more to say than the first sentence, and interrupting to fix it — even helpfully — reads as not being taken seriously, which is what the complaint is actually about by the time it reaches you.</p>

<p><b>Apologise for the experience, immediately.</b> Not for fault you have not established: <i>I am sorry that happened</i> rather than <i>I am sorry we sold you a bad one</i>. The first is true regardless and does most of the defusing work.</p>

<p><b>Get the facts.</b> What, when, do they have the receipt, what would they like to happen. That last question is worth asking early — people frequently want less than you assume, and a customer who wanted an exchange and was handed an argument about a refund is a problem you created.</p>

<p><b>Do what you can, or get somebody who can.</b> Know your own limits before you need them. If it is inside what you can do, do it now. If it is not, fetch somebody rather than negotiating on their behalf.</p>

<p><b>Close it.</b> Say what will happen and when. A complaint that ends without the customer knowing what comes next has not been resolved; it has been paused.</p>

<p><b>The mistake almost everybody makes.</b> Explaining why it happened. The customer does not want the reason, and the explanation sounds like an excuse however it is meant. Fix first. If they ask why afterwards, then answer.</p>

<p><b>What a complaint is actually worth.</b> Somebody complaining is somebody still engaging. Most unhappy customers say nothing and simply do not return, so the person in front of you is the one giving the shop a chance — which is worth remembering when the complaint is delivered badly, because the delivery and the substance are different things.</p>

<p><b>Two practical things about receipts, which is where most complaints stall.</b> Ask for it after you have heard the problem rather than as the opening move — leading with the receipt reads as looking for a reason to refuse, and it sets the tone for everything after. And where there is no receipt, do not decide the outcome yourself: the shop has a rule, you may not know it fully, and guessing generously is as much a problem as guessing meanly.</p>

<p><b>The complaint that is not really about the thing.</b> Some arrive far angrier than the fault warrants, and it is usually because this is the third thing that has gone wrong for that person today, or because they had to make a journey to come back. Neither is your doing and both are worth knowing, because it stops you reading the intensity as an accusation and answering it defensively. Handle the stated problem, let the rest pass, and it very often subsides within a minute.</p>

<blockquote>WATCH-OUT: Never disagree about the facts in the opening minute, even when you are certain. Argue the facts once and the conversation becomes about who is right; establish them gently afterwards and it stays about fixing the problem.</blockquote>"""
, [
 C("Interrupting to solve a problem while the customer is still talking reads as:",
   ["Efficiency", "Not being taken seriously",
    "Good service", "Impatience only"], 1,
   "Which is what the complaint is usually about by the time it reaches you."),
 C("Asking what the customer would like to happen matters because people frequently want:",
   ["More than you can give", "Less than you assume",
    "A refund", "An apology only"], 1,
   "A customer who wanted an exchange and was handed an argument about a refund is a problem you created."),
 C("Explaining why something happened:",
   ["Reassures the customer", "Sounds like an excuse however it is meant",
    "Should come first", "Is required"], 1,
   "Fix first; answer the why only if they ask afterwards.")]),

("The customer is not always right", 10, """<p>Somebody will tell you the customer is always right. It is not true, staff discover it is not true on their first difficult day, and being handed a slogan that collapses under contact leaves people with nothing to work from.</p>

<p><b>The version that survives.</b> The customer is always to be taken seriously. Their complaint gets heard properly and answered honestly, whether or not they turn out to be correct. That is a real standard, it holds in the hard cases, and it does not require anybody to pretend.</p>

<p><b>Where the difference shows.</b> Somebody is mistaken about a price. The slogan says give it to them. The real standard says check, and if they are wrong, say so plainly and without triumph: <i>I have checked and it is ₦1,200 — I am sorry, I think the label you saw was for the smaller size.</i> Most people accept that easily. What they will not accept is being told they are wrong dismissively, or being right and not believed.</p>

<p><b>The judgement worth learning early.</b> There is a difference between somebody mistaken, somebody chancing it, and somebody being unreasonable. All three are handled the same way — check, answer honestly, escalate if needed. What changes is how much of your own goodwill you spend, and that is a judgement you are allowed to make.</p>

<p><b>Where the line actually is.</b> Customers are entitled to be annoyed, insistent, and difficult to please. They are not entitled to abuse you, and no shop worth working in expects you to absorb that. Chapter 7 of this track covers what to do when it goes past the line; what matters here is knowing that the line exists and that it is not a personal failure to reach it.</p>

<p><b>And the thing nobody tells new staff.</b> Some interactions are simply going to go badly. Not everything is recoverable, some people arrive already angry about something that has nothing to do with you, and doing everything right does not guarantee a good outcome. Judge yourself on whether you handled it well, not on whether they left happy — because the second is not always available.</p>

<p><b>What to do with the ones that go badly, afterwards.</b> They stay with you, particularly early on, and the instinct is either to replay it repeatedly or to decide you are bad at this. Neither helps. The useful version is one question — was there a point where a different sentence would have changed it? — answered honestly and then left alone. Sometimes the answer is yes and you have learned something. Often it is no, and that is worth knowing too.</p>

<blockquote>WORTH KNOWING: A customer who is right and not believed is far more damaging than one who is wrong and told so. The second is a transaction; the first is the story they tell about your shop.</blockquote>"""
, [
 C("The version of the slogan that survives contact is that the customer is always:",
   ["Right", "To be taken seriously",
    "Owed an apology", "Given the benefit"], 1,
   "It holds in the hard cases and does not require anybody to pretend."),
 C("Customers are entitled to be annoyed and difficult to please, but not to:",
   ["Complain repeatedly", "Abuse you",
    "Ask for a supervisor", "Dispute a price"], 1,
   "No shop worth working in expects you to absorb that."),
 C("You should judge yourself on whether you handled it well rather than whether they left happy because:",
   ["Outcomes are subjective", "A good outcome is not always available",
    "Managers assess process", "Happiness cannot be measured"], 1,
   "Some people arrive already angry about something that has nothing to do with you.")]),

("The customers you see again", 10, """<p>Most of a shop's takings come from people who shop there repeatedly, and those customers are made rather than found.</p>

<p><b>The arithmetic, roughly.</b> A customer who spends ₦5,000 a week and shops with you for two years is worth around half a million naira. The same person, lost after one bad experience, took that with them. Which is why an argument won over ₦800 can be a genuinely expensive victory, and why staff are told to be generous about small things — it is not softness, it is the sums.</p>

<p><b>What actually makes somebody a regular.</b> Being recognised, more than anything else. Not remembering their name — remembering that you have seen them. A nod, a <i>hello again</i>, knowing they buy the same thing on Fridays. It is the cheapest thing on this list and the one people report most.</p>

<p><b>Then reliability of the things they came for.</b> A regular is somebody whose weekly items you have. Nothing loses a regular faster than the same line being out three visits running, which is why availability sits in the next module and matters more than service does.</p>

<p><b>Then somebody who solved something once.</b> A customer whose problem you fixed properly becomes disproportionately loyal, more so than one who never had a problem at all. This is the recovery paradox, it is well established, and it is the strongest argument for handling complaints as chapter 5 describes.</p>

<p><b>What you can do with none of the authority.</b> Recognise people. Notice what they buy and ask about it. Remember what somebody asked for last week and tell them when it arrives — that one is remarkable in its effect and almost nobody does it. And be the same person every time, because consistency is what makes a shop feel like somewhere rather than anywhere.</p>

<p><b>The one to be careful with.</b> Familiarity is welcome from a distance and intrusive up close. Recognising somebody is warm; commenting on what they buy, who they are with, or how often they come in can land badly. Follow their lead — a customer who wants a conversation will start one.</p>

<blockquote>IMPLEMENTATION TIP: Pick three faces you see weekly and greet them as returning customers rather than as strangers. That is the entire technique, it takes no time, and it is the single most-reported reason people give for preferring one shop to another that sells the same things.</blockquote>

<p><b>And the version of this that is not about customers at all.</b> A shop where the staff recognise the regulars is almost always a shop where the staff have been there a while. Recognition is a by-product of people staying, which is why the branches that feel welcoming are usually the ones with low turnover rather than the ones with better training. If you stay a year, you will be able to do this without trying; if the whole team turns over every six months, nobody can, however hard they try.</p>"""
, [
 C("A customer whose problem was fixed properly becomes:",
   ["As loyal as any other", "More loyal than one who never had a problem",
    "Unlikely to return", "Loyal only if compensated"], 1,
   "The recovery paradox, and the strongest argument for handling complaints properly."),
 C("What makes somebody a regular, more than anything else, is:",
   ["Low prices", "Being recognised",
    "Speed of service", "Product range"], 1,
   "Not remembering their name — remembering that you have seen them."),
 C("Familiarity with a regular customer should follow:",
   ["Shop policy", "Their lead",
    "The manager's example", "The length of acquaintance"], 1,
   "Recognising somebody is warm; commenting on what they buy or who they are with can land badly.")]),

("Okelewo Stores: the Saturday Ada got right", 10, """<p>A Saturday at the Ibadan branch, four months in. Nothing dramatic happened, which is why it is worth reading.</p>

<p><b>Late morning, the queue.</b> Ada was filling the household aisle with a queue building at the single open till — four people, the supervisor serving, a price check holding everything up. She did not have till access yet. What she did was walk to the back of the queue and say that somebody would be with them shortly, then go and find the price the supervisor was hunting for. Total elapsed time about ninety seconds, and the queue was cleared before it reached six.</p>

<p><b>Just after, the woman with the two children.</b> Standing at the chilled section holding more than she could carry, one child pulling at her. Ada did not ask whether she needed help; she fetched a basket and handed it over. The customer said afterwards that it was the reason she now shops there rather than at the market.</p>

<p><b>Early afternoon, the complaint.</b> A man returned a packet of biscuits that were stale, annoyed, and told Ada at some length that the shop did not check its dates. She let him finish. She apologised that it had happened. She asked what he would like — he wanted the same thing, not his money back, which she had not expected. She replaced it, and then she did the part that mattered: she checked the rest of that line on the shelf and found four more packets past date, which she pulled and told the supervisor about.</p>

<p><b>What she did not do.</b> She did not explain that the supplier delivers short-dated stock sometimes. It was true, it was the actual reason, and it would have sounded like an excuse.</p>

<p><b>Mid-afternoon, the price.</b> A customer insisted a bottle was ₦900. Ada checked; it was ₦1,150, and the ₦900 label belonged to the smaller size on the shelf below. She said so plainly and apologised for the confusing shelf. The customer bought it anyway. Ada then straightened the labels, which took a minute and stopped the same conversation happening six more times that day.</p>

<p><b>The thread running through all four.</b> None of it required authority, permission, or a particular personality. Every one was noticing something and acting on it within about a minute — and the fourth is the one most people would have skipped, because the customer had already gone.</p>

<blockquote>IMPLEMENTATION TIP: The label-straightening is the habit to take from this chapter. When something confuses one customer, it will confuse the next ten. Fixing the cause after the customer leaves is the difference between good service and a shop that gets better.</blockquote>"""
, [
 C("After replacing the stale biscuits, the part that mattered was that Ada:",
   ["Apologised again", "Checked the rest of the line and found four more past date",
    "Told the customer the supplier's fault", "Recorded the complaint"], 1,
   "The complaint was information about a shelf, not just about one packet."),
 C("Ada did not explain that the supplier sometimes delivers short-dated stock because:",
   ["It was not true", "It would have sounded like an excuse",
    "It was confidential", "The customer had not asked"], 1,
   "It was the actual reason, which is exactly what makes it tempting to say."),
 C("Straightening the price labels after the customer left mattered because:",
   ["It was policy", "What confused one customer will confuse the next ten",
    "The supervisor asked", "It tidied the shelf"], 1,
   "Fixing the cause is the difference between good service and a shop that gets better.")]),

("Review, and the practice for this fortnight", 10, """<p>The module in short, then the two things to actually do.</p>

<p><b>Service is four things.</b> Being findable, knowing the answer or getting it fast, the queue moving, and doing what you said. Warmth improves all four and replaces none of them — which is why a quiet person can be excellent at this.</p>

<p><b>Read before you approach.</b> Looking up, slowing, doubling back and putting things down twice mean help is wanted. Moving with purpose and scanning a shelf mean it is not. <i>Let me know if you need anything</i> beats <i>can I help you</i>. Accept a no once and stay visible.</p>

<p><b>Four sentences ready.</b> I do not want to guess. We do not have it — would this do, or shall I find out when it is coming? I am sorry, tell me what happened. I cannot do that myself, but let me get somebody who can.</p>

<p><b>Queues are about movement, not length.</b> Acknowledge the back of the queue, say only true things about the wait, and watch it building at three rather than at six.</p>

<p><b>Complaints: listen to the end, apologise for the experience, get the facts including what they want, act or fetch somebody, and close it.</b> Do not explain why. Do not argue the facts in the first minute.</p>

<p><b>The customer is not always right; they are always to be taken seriously.</b> They may be annoyed and difficult; they may not abuse you. Judge yourself on how you handled it, not on how they left.</p>

<p><b>Regulars are made.</b> Being recognised is the cheapest and most-reported thing you can do, and telling somebody the item they asked about has arrived is remarkable in effect and almost nobody does it.</p>

<p><b>The practice, and it is two things.</b> First: greet three regular faces as returning customers rather than as strangers. Second: the next time something confuses a customer — a label, a sign, a gap where they expected something — fix the cause after they leave. Both take under a minute and neither needs anybody's permission.</p>

<p><b>One thing to expect if you start doing this.</b> The first few times you fix a cause rather than a symptom, nobody will notice. Nobody thanks you for the six complaints that did not happen, because they did not happen. That is the nature of the work, and it is worth deciding now that you will do it anyway — within a few months the pattern shows up as a section with fewer problems than the others, and that is the thing people do notice.</p>

<blockquote>IMPLEMENTATION TIP: The next module is the shelf, and it is the one that matters most. Everything in this module improves an experience; availability decides whether there was anything to experience. A customer served beautifully and sent away empty-handed has still been failed.</blockquote>"""
, [
 C("A customer served beautifully and sent away empty-handed has:",
   ["Received good service", "Still been failed",
    "No cause for complaint", "Been handled correctly"], 1,
   "Everything in this module improves an experience; availability decides whether there was one."),
 C("The two practice tasks are fixing the cause after a customer leaves, and:",
   ["Learning the range", "Greeting three regular faces as returning customers",
    "Improving queue speed", "Rehearsing the four sentences"], 1,
   "Both take under a minute and neither needs anybody's permission."),
 C("Telling a customer that the item they asked about has arrived is described as:",
   ["Standard practice", "Remarkable in effect, and almost nobody does it",
    "The supervisor's job", "Only possible with a system"], 1,
   "One of the things that makes somebody a regular.")]),
]


QUESTIONS = [
 Q("The four components of service, in the order customers care about them, begin with:", ["Friendliness", "Being findable", "Product knowledge", "Speed"], 1,
   "A customer who needs help and cannot find anybody is having the worst version of the experience.", "Ch1 §3", "What service is"),
 Q("The fourth component, which builds what shops call loyalty, is:", ["Smiling", "Doing what you said you would", "Knowing the range", "Serving quickly"], 1,
   "Entirely a matter of follow-through rather than personality.", "Ch1 §6", "What service is"),
 Q("Warmth in service:", ["Substitutes for the other four", "Makes all four better and replaces none", "Matters most", "Is unnecessary"], 1,
   "Which is why a quiet person who is present, knows and follows through is who customers come back for.", "Ch1 §7", "What service is"),
 Q("Asked why they stopped shopping somewhere, customers rarely say rudeness. They say:", ["Prices rose", "The thing they wanted was never there, or somebody did not follow through", "Queues were long", "Staff changed"], 1,
   "Which puts availability and follow-through above manner.", "Ch1 §9", "What service is"),
 Q("Someone who picks an item up and puts it back twice is showing:", ["Indecision to leave alone", "A signal that help is wanted", "Suspicious behaviour", "Price sensitivity"], 1,
   "Along with looking up, slowing, and doubling back.", "Ch2 §2", "Reading customers"),
 Q("Somebody scanning steadily along a shelf:", ["Needs help", "Does not", "Is comparing prices", "Should be approached"], 1,
   "It looks like being lost and is not.", "Ch2 §2", "Reading customers"),
 Q("The higher-hit-rate opening is:", ["Can I help you", "Let me know if you need anything", "Are you alright there", "What are you looking for"], 1,
   "Said while continuing what you were doing, so it does not arrive as a challenge.", "Ch2 §3", "Reading customers"),
 Q("Somebody standing in one place for over a minute is:", ["Browsing", "Stuck, and stuck people rarely ask", "Waiting for somebody", "Deciding"], 1,
   "That is the moment to approach directly, naming the section rather than the person.", "Ch2 §4", "Reading customers"),
 Q("You always approach without waiting when somebody is:", ["Alone", "Carrying more than they can hold", "Browsing slowly", "On the phone"], 1,
   "Along with a struggling parent, an older customer reaching high, or somebody at an unstaffed counter.", "Ch2 §6", "Reading customers"),
 Q("When you do not know the answer, the customer minds most:", ["The delay", "A confident answer that turns out wrong", "Being referred", "Your uncertainty"], 1,
   "Because they acted on it.", "Ch3 §2", "The four sentences"),
 Q("The out-of-stock sentence offers an alternative and:", ["An apology", "To find out when it is coming", "A discount", "A rain check"], 1,
   "The bad version stops at 'we do not have it' and lets the customer leave.", "Ch3 §3", "The four sentences"),
 Q("'I am sorry — tell me what happened' is safe before you know the facts because it:", ["Buys time", "Admits no fault and promises nothing", "Transfers the issue", "Records the complaint"], 1,
   "The apology defuses; the invitation gets the facts.", "Ch3 §4", "The four sentences"),
 Q("The phrase to avoid entirely is:", ["I will find out", "That is not my department", "Let me check", "I cannot do that myself"], 1,
   "'Let me find the person who deals with that' says the same thing in the same ten seconds.", "Ch3 §7", "The four sentences"),
 Q("Prepared sentences help because under pressure nobody is:", ["Calm", "At their most articulate", "Attentive", "Polite"], 1,
   "Having the words means the moment is about the problem rather than about finding something to say.", "Ch3 §6", "The four sentences"),
 Q("What customers react to most in a queue is:", ["Its length", "Whether it is moving", "The number of tills", "Who is serving"], 1,
   "Four served briskly feels shorter than two served slowly.", "Ch4 §3", "Queues"),
 Q("Somebody else being served first produces:", ["Mild irritation", "More genuine anger than a long wait", "A complaint to the manager", "No reaction if explained"], 1,
   "It feels like unfairness rather than inconvenience.", "Ch4 §5", "Queues"),
 Q("A waiting customer seeing staff who are not serving:", ["Understands they have other work", "Sees somebody available", "Assumes a break", "Is unaffected"], 1,
   "Worth knowing, because you will be restocking ten feet from a queue.", "Ch4 §6", "Queues"),
 Q("The highest-value queue habit is:", ["Serving faster", "Watching the queue rather than your own task", "Opening tills", "Calling for help"], 1,
   "Noticing it building at three rather than at six is most of it.", "Ch4 §8", "Queues"),
 Q("'Sorry, we are short-staffed today' is worse than 'sorry for the wait' because it:", ["Is untrue", "Invites a conversation the customer cannot help with", "Blames colleagues", "Sounds rehearsed"], 1,
   "An acknowledgement ends it; an excuse extends it.", "Ch4 §9", "Queues"),
 Q("The first step in handling a complaint is to:", ["Apologise", "Listen to the end", "Establish the facts", "Offer a solution"], 1,
   "Most people arrive with more to say than the first sentence.", "Ch5 §3", "Complaints"),
 Q("The apology should be for:", ["The shop's fault", "The experience", "The inconvenience of returning", "Whatever they allege"], 1,
   "'I am sorry that happened' is true regardless and does most of the defusing.", "Ch5 §4", "Complaints"),
 Q("Asking what the customer would like to happen should come:", ["Last", "Early", "After checking policy", "Only if they seem reasonable"], 1,
   "People frequently want less than you assume.", "Ch5 §5", "Complaints"),
 Q("A complaint that ends without the customer knowing what happens next has been:", ["Resolved", "Paused", "Escalated", "Closed informally"], 1,
   "Say what will happen and when.", "Ch5 §7", "Complaints"),
 Q("Most unhappy customers:", ["Complain", "Say nothing and do not return", "Ask for a manager", "Post online"], 1,
   "Which is why the person complaining is the one giving the shop a chance.", "Ch5 §9", "Complaints"),
 Q("Disagreeing about the facts in the opening minute makes the conversation about:", ["The solution", "Who is right", "The policy", "The evidence"], 1,
   "Establish them gently afterwards and it stays about fixing the problem.", "Ch5 §10", "Complaints"),
 Q("The workable version of the slogan is that the customer is always:", ["Right", "To be taken seriously", "Owed something", "Given the benefit of the doubt"], 1,
   "A real standard that holds in the hard cases.", "Ch6 §2", "Not always right"),
 Q("A customer mistaken about a price should be told:", ["Nothing, just give it", "Plainly and without triumph", "By a supervisor only", "After checking with a colleague"], 1,
   "Most people accept it easily; what they will not accept is being told dismissively.", "Ch6 §3", "Not always right"),
 Q("What customers will not accept is being told they are wrong dismissively, or:", ["Being asked for a receipt", "Being right and not believed", "Waiting for a check", "Being referred upward"], 1,
   "The second is the story they tell about your shop.", "Ch6 §3", "Not always right"),
 Q("Reaching the line where a customer's behaviour becomes unacceptable is:", ["A personal failure", "Not a personal failure", "A sign of poor handling", "Rare enough to ignore"], 1,
   "No shop worth working in expects you to absorb abuse.", "Ch6 §5", "Not always right"),
 Q("You should judge yourself on:", ["Whether they left happy", "Whether you handled it well", "The outcome", "The manager's view"], 1,
   "Because a good outcome is not always available.", "Ch6 §6", "Not always right"),
 Q("A customer spending ₦5,000 weekly for two years is worth roughly:", ["₦50,000", "Half a million naira", "₦5m", "The margin on one visit"], 1,
   "Which is why an argument won over ₦800 can be an expensive victory.", "Ch7 §2", "Regulars"),
 Q("The cheapest and most-reported thing that makes somebody a regular is:", ["A discount", "Being recognised", "Fast service", "Product range"], 1,
   "Not remembering their name — remembering that you have seen them.", "Ch7 §3", "Regulars"),
 Q("What loses a regular fastest is:", ["A rude assistant", "The same line being out three visits running", "A price rise", "A long queue"], 1,
   "Which is why availability matters more than service does.", "Ch7 §4", "Regulars"),
 Q("The recovery paradox says a customer whose problem was fixed becomes:", ["Neutral", "More loyal than one who never had a problem", "Less loyal", "Loyal only with compensation"], 1,
   "The strongest argument for handling complaints properly.", "Ch7 §5", "Regulars"),
 Q("Telling somebody the item they asked for last week has arrived is:", ["Standard", "Remarkable in effect and almost never done", "The supervisor's job", "Impractical"], 1,
   "One of the things available without any authority at all.", "Ch7 §6", "Regulars"),
 Q("Familiarity with regulars should be:", ["Maximised", "Led by the customer", "Formal", "Avoided"], 1,
   "Welcome from a distance and intrusive up close.", "Ch7 §7", "Regulars"),
 Q("With a queue of four and no till access, Ada:", ["Waited", "Acknowledged the back of the queue, then found the price that was holding it up", "Called the manager", "Opened a second till"], 1,
   "About ninety seconds, and the queue cleared before it reached six.", "Ch8 §2", "Ada's Saturday"),
 Q("With the woman holding more than she could carry, Ada:", ["Asked if she needed help", "Fetched a basket and handed it over", "Called a colleague", "Offered to carry it"], 1,
   "The need was visible, so asking permission would have wasted the moment.", "Ch8 §3", "Ada's Saturday"),
 Q("The man returning stale biscuits wanted:", ["A refund", "The same thing again", "An apology", "To speak to a manager"], 1,
   "Which Ada had not expected, and is why the question is worth asking.", "Ch8 §4", "Ada's Saturday"),
 Q("After the biscuit complaint Ada found on the shelf:", ["Nothing else wrong", "Four more packets past date", "A pricing error", "A delivery fault"], 1,
   "The complaint was information about a shelf rather than about one packet.", "Ch8 §4", "Ada's Saturday"),
 Q("After the price dispute, Ada straightened the labels, which stopped:", ["A complaint being logged", "The same conversation happening six more times that day", "The supervisor intervening", "A stock error"], 1,
   "What confused one customer will confuse the next ten.", "Ch8 §6", "Ada's Saturday"),
 Q("What all four of Ada's Saturday actions had in common was:", ["Authority", "Noticing something and acting within about a minute", "Product knowledge", "Supervisor approval"], 1,
   "None required permission or a particular personality.", "Ch8 §7", "Ada's Saturday"),
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

    rebalance(QUESTIONS, "shopfloor:customers:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:customers:checks")

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
        "title": "RF 2 — The Customer In Front Of You",
        "desc": ("What service actually consists of, stated specifically enough to practise: "
                 "the four things customers care about, reading whether somebody wants help, "
                 "four sentences worth having ready, why queues annoy people, working a "
                 "complaint properly, where the line is when the customer is not right, and "
                 "how regulars are made."),
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
