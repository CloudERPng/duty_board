#!/usr/bin/env python3
"""Build 'Getting Better' into academy_shopfloor_data.json.

Module 8 of Retail Foundations.

The module the reader has the most personal stake in, and therefore the one
where vagueness would be least forgivable. Module 1 named the promotion order
in a paragraph; this is the whole of it, made specific enough to act on.

Four positions:

  IT IS SPECIFIC ABOUT WHAT GETS SOMEBODY PROMOTED, INCLUDING THE PARTS THAT
  ARE NOT ABOUT MERIT. Availability, visibility to the person who decides, and
  whether the branch has anywhere to promote into all matter, and a track that
  pretended otherwise would be setting readers up to conclude they had failed
  when they had simply been in a stable branch.

  IT TREATS ASKING AS A SKILL. Most people never ask what they would need to
  do, never ask for feedback, and never say they are interested. Each of those
  is free, and each changes the answer. This is the highest-return material in
  the module.

  IT IS HONEST THAT RETAIL MAY NOT BE THE READER'S CAREER. Many will do a year
  or two and leave. Written as though everybody is climbing, the module would
  lose them — so it names what transfers, and treats leaving well as its own
  competence rather than a failure of loyalty.

  IT ENDS ON THE SUPERVISOR STEP SPECIFICALLY, because that is the one the
  reader is actually next to, and because it is the step people take without
  understanding that the job changes rather than expands.

Run from the app package directory:  python3 build_shopfloor_m8.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "getting_better"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("What actually gets somebody promoted", 10, """<p>Module 1 gave the order in a paragraph. This is the whole of it, because most people spend years guessing at something that is not a secret.</p>

<p><b>First, reliability.</b> Turning up, on time, every time, and doing what you said you would. It is first because everything else is worthless without it — nobody gives a section, a key or a shift to somebody they have to check on. And it is genuinely rare, which is why it outranks talent.</p>

<p><b>Second, the section that is right unwatched.</b> A person whose area is correct when nobody is looking has already demonstrated the thing a supervisor's job requires, which is caring about a standard in the absence of anybody enforcing it.</p>

<p><b>Third, taking something on.</b> A routine, a new starter, an ordering category, the thing nobody does. Nobody is promoted into responsibility they have never held; they are promoted into responsibility they have already been holding informally.</p>

<p><b>Fourth, being good with customers.</b> It matters and it is fourth, and almost everybody assumes it is first.</p>

<p><b>Fifth, and only fifth, knowing the products and the systems.</b> This is the one people work hardest on, and it is the easiest to teach, which is exactly why it counts least in the decision.</p>

<p><b>What is not on the list at all.</b> Working longer hours than anybody else. Being the busiest. Being liked. Each of those feels like it should count and none of them is what somebody is thinking about when they decide who to trust with more.</p>

<p><b>The reframe worth holding.</b> Promotion is not a reward for effort already spent. It is a prediction about whether somebody can be relied on with more, made by a person who will have to answer for that prediction. Read the five in that light and they stop being arbitrary — every one is evidence about reliability under less supervision.</p>

<p><b>Why the order is worth arguing with rather than accepting.</b> Check it against your own branch. Look at the last two people who were promoted and ask which of the five they had. If the answer does not match this list, then this list is wrong for where you work and the real one is worth knowing instead — there are businesses that promote on length of service, on who is available, or on who asked. Knowing which kind you are in beats following a general rule that does not apply.</p>

<p><b>What all five have in common.</b> Each is evidence about what you do when nobody is watching, which is the only thing anybody is really trying to predict. That is why effort does not appear on the list — effort is visible by definition, and the decision is about the hours nobody sees.</p>

<p><b>And the one people find hardest to accept.</b> Somebody less capable than you may be promoted ahead of you, and it is usually not favouritism — it is that they had the five in a different order, most often reliability and taking things on against your product knowledge and speed. That is genuinely annoying and it is also information: the gap is nearly always in the first three rather than in ability.</p>

<blockquote>WORTH KNOWING: If you want a shortcut to all five, ask yourself what your supervisor would have to check if you were given something new. The shorter that list, the closer you are.</blockquote>"""
, [
 C("Reliability is first because:",
   ["It is easily measured", "Nobody gives responsibility to somebody they have to check on",
    "It is company policy", "It is the hardest to fake"], 1,
   "Everything else is worthless without it, and it is genuinely rare."),
 C("Product and system knowledge counts least because it is:",
   ["Unimportant", "The easiest to teach",
    "Rarely tested", "Learned automatically"], 1,
   "It is also the one people work hardest on."),
 C("Promotion is best understood as:",
   ["A reward for effort already spent", "A prediction about whether somebody can be relied on with more",
    "A reward for loyalty", "A recognition of skill"], 1,
   "Made by a person who will have to answer for that prediction.")]),

("Asking, which almost nobody does", 10, """<p>The highest-return material in this module, and it costs nothing but a small amount of awkwardness.</p>

<p><b>Ask what you would need to do.</b> The exact question: <i>what would I need to be doing to be considered for the senior role?</i> Most people never ask, most supervisors have an answer ready, and the question changes how they see you from that moment — because somebody who asks it has declared themselves interested, and interest is information a supervisor did not previously have.</p>

<p><b>Say you are interested at all.</b> This sounds too obvious to need stating and it is the commonest omission in retail. Supervisors are not mind-readers and many people assume that wanting more will be noticed. It frequently is not — plenty of good staff are passed over because everybody assumed they were content.</p>

<p><b>Ask for feedback specifically.</b> <i>How am I doing?</i> gets <i>fine, yeah, good</i> from almost anybody, because it is a question about everything and therefore about nothing. <i>What is the one thing I should do differently?</i> gets an actual answer, because it asks for one item and gives permission to name it.</p>

<p><b>Then take it without defending.</b> The single most valuable half-minute available: somebody tells you something uncomfortable, and you say thank you and nothing else. Explaining why they are wrong — even where they are — teaches them not to bother next time, and the person who stops receiving feedback stops improving without noticing.</p>

<p><b>Ask again in a month.</b> One conversation is a moment; asking twice is a pattern, and a pattern is what makes somebody think of you when a decision comes up. It also lets you show that you acted on the first answer, which is worth more than the acting itself.</p>

<p><b>And accept the answer you get.</b> Sometimes it is not yet, and sometimes there is a reason you will not like. Take it, ask what would change it, and do not argue — the argument confirms whatever the reservation was.</p>

<p><b>When to ask, which matters more than people expect.</b> Not during a rush, not at the end of a bad shift, and not in front of other people. A quiet moment, one to one, and preferably just after you have done something well rather than just after something went wrong — the same question lands completely differently depending on which it follows. Five seconds of timing changes the answer more than any amount of phrasing.</p>

<p><b>What to do with an answer you were not expecting.</b> Sometimes the one thing to do differently is something you thought you were good at, or something about manner rather than work. That is uncomfortable and it is the most valuable kind, because it is the part you cannot see yourself. Sit with it for a day before deciding whether you agree — the first reaction to accurate feedback is very often that it is unfair.</p>

<blockquote>IMPLEMENTATION TIP: Ask one question this month: what is the one thing I should do differently? Ask it of your supervisor, listen, say thank you, and do that thing. Almost nobody does this, which is precisely why it works.</blockquote>"""
, [
 C("'How am I doing?' produces a useless answer because it asks about:",
   ["Too short a period", "Everything, and therefore nothing",
    "Somebody else's judgement", "Performance rather than behaviour"], 1,
   "'What is the one thing I should do differently?' asks for one item and gives permission to name it."),
 C("Explaining why feedback is wrong, even when it is:",
   ["Clarifies the situation", "Teaches them not to bother next time",
    "Shows engagement", "Is expected"], 1,
   "The person who stops receiving feedback stops improving without noticing."),
 C("Many capable staff are passed over because:",
   ["They lack skills", "Everybody assumed they were content",
    "They are needed where they are", "They did not apply"], 1,
   "Supervisors are not mind-readers, and saying you are interested is the commonest omission.")]),

("Practising, rather than just doing", 10, """<p>Doing a job for a year does not make somebody a year better at it. Some people improve steadily and some are exactly as good in year three as in month three, and the difference is not talent.</p>

<p><b>What separates them.</b> The people who improve are working on one specific thing at a time and know what it is. The people who do not are doing the job well and waiting for experience to accumulate, which it does not, because repetition without attention produces speed rather than skill.</p>

<p><b>How to pick the thing.</b> Something small, specific and yours: reading whether a customer wants help, remembering regulars' names, getting through a fill without the shelf looking touched, handling one difficult conversation without going defensive. Vague ambitions — be better with customers — cannot be practised, because you cannot tell whether you did it today.</p>

<p><b>Work on it for a fortnight, then change.</b> Long enough to become slightly automatic, short enough that you do not lose interest. Six things properly over three months beats a general intention to improve held for a year.</p>

<p><b>Where the actual improvement happens.</b> In the thirty seconds after something goes badly. Somebody handled a complaint clumsily, or fumbled a busy period, and the useful question is one: what would I do differently? Answered honestly and then dropped. That is deliberate practice in a shop, and it is available several times a week to anybody who takes it.</p>

<p><b>Copy people.</b> The fastest way to learn most of this. Find the colleague who is best at the thing you are working on and watch what they actually do rather than asking them how they do it — people are unreliable narrators of their own competence, and the useful detail is usually something they do not know they are doing.</p>

<p><b>And the honest limit.</b> Some things you will not become good at, and that is fine. Nobody is good at all of retail. What matters is being good at enough of it and knowing which parts are your weak ones, because somebody who knows their weaknesses can work around them and somebody who does not is surprised by them regularly.</p>

<p><b>The thing that is hardest to practise and worth the most.</b> Staying steady when it is going badly — the queue building, three things wrong at once, somebody unhappy in front of you. Almost everybody is competent when things are calm, and the difference between people shows up entirely under pressure. It cannot be arranged deliberately; what you can do is notice afterwards how you were, and treat that as the measurement rather than how the shift went.</p>

<p><b>A note on speed, which people over-value.</b> Being fast is worth something and it is worth much less than being consistent. A person who fills four shelves properly is more useful than one who fills six with the dates unchecked and the rotation skipped, and the second person often believes they are the better worker. If you are choosing what to improve, choose reliability of the result over the rate of it — speed arrives on its own once the method is right.</p>

<blockquote>IMPLEMENTATION TIP: Pick one thing this fortnight and write it somewhere you will see it. The writing is not ceremony — an intention held only in your head is indistinguishable, after four days, from not having had one.</blockquote>"""
, [
 C("You have done the same job competently for two years without working on anything in particular. What you have most likely gained is:",
   ["Steady improvement", "Speed rather than skill",
    "Broad confidence", "Consistency"], 1,
   "Which is why some people are exactly as good in year three as in month three."),
 C("'Be better with customers' cannot be practised because:",
   ["It is too difficult", "You cannot tell whether you did it today",
    "It takes years", "It depends on others"], 1,
   "The thing to practise must be small, specific and yours."),
 C("Watching a skilled colleague is better than asking them how they do it because:",
   ["They may not want to explain", "People are unreliable narrators of their own competence",
    "It is faster", "Watching is less intrusive"], 1,
   "The useful detail is usually something they do not know they are doing.")]),

("The parts that are not about merit", 10, """<p>Everything so far assumes that doing the right things leads to progression. Mostly it does, and it is worth being honest about the parts that are not about you at all — because people who do not know this conclude they have failed when they have not.</p>

<p><b>There has to be somewhere to go.</b> A branch where nobody has left in three years has no vacancy, however good you are. A business opening branches needs supervisors constantly. That single difference explains more about who gets promoted and when than any amount of performance, and it is worth knowing which kind of business you are in before drawing conclusions about yourself.</p>

<p><b>The person deciding has to have seen you.</b> A manager who is rarely on your shift knows you through what somebody else tells them. That is not unfair, it is just how it works, and it means being visible occasionally to the person who decides is worth something — a morning shift now and then, a word at a handover, being the one who takes something to them.</p>

<p><b>Availability is a factor, and nobody says so.</b> Somebody who can work weekends and evenings is more promotable than somebody who cannot, because a supervisor covers the hardest shifts. That may not be possible for you, and it is worth knowing rather than being puzzled by — it is a constraint rather than a judgement.</p>

<p><b>Timing is mostly luck.</b> Being ready when a vacancy appears is largely coincidence. What you can control is being ready more of the time, so that more of the coincidences land on you.</p>

<p><b>And sometimes it is genuinely unfair.</b> Somebody's relative gets it, or a decision is made for reasons nobody explains. It happens, it is not imagined, and there are two honest responses: ask directly what would have made the difference, and if the answer is not one you can work with, decide whether the business is worth staying in. What does not work is staying and being bitter, which damages nobody but you.</p>

<p><b>And what to do if the ceiling is real.</b> Three options, all reasonable. Stay and be excellent where you are, which is a genuine choice rather than a consolation prize. Ask whether another branch has an opening — people rarely think of it and businesses are often glad to arrange it. Or start looking elsewhere, with a year of specific examples behind you, which is exactly what the note-keeping in chapter 6 produces.</p>

<blockquote>WORTH KNOWING: If you have done everything in this module for a year and nothing has changed, the most likely explanation is that there is nowhere to be promoted to. That is worth checking before concluding anything about yourself.</blockquote>"""
, [
 C("A branch where nobody has left in three years:",
   ["Promotes internally", "Has no vacancy however good you are",
    "Is a good place to develop", "Rotates staff"], 1,
   "It explains more about who gets promoted and when than any amount of performance."),
 C("Availability for weekends and evenings matters because:",
   ["It shows commitment", "A supervisor covers the hardest shifts",
    "It is company policy", "It demonstrates flexibility"], 1,
   "It is a constraint rather than a judgement, and worth knowing rather than being puzzled by."),
 C("If nothing has changed after a year of doing everything right, the most likely explanation is:",
   ["You are not ready", "There is nowhere to be promoted to",
    "Your supervisor disagrees", "The feedback was wrong"], 1,
   "Worth checking before concluding anything about yourself.")]),

("Being given more before you are paid more", 10, """<p>The step almost everybody misses. Extra responsibility usually arrives before the title and before the money, and how somebody handles that gap decides most of what follows.</p>

<p><b>What it looks like.</b> Being asked to open up, to train somebody, to keep a section, to be the one who deals with a supplier. Nobody announces it as a development opportunity. It arrives as a favour, or as a gap, or as nobody else being available.</p>

<p><b>Why it is worth taking, and the argument is not loyalty.</b> Because nobody is promoted into responsibility they have not already held. Every one of those is an audition that has already begun, and the person who says yes twice has a track record while the person who says no twice has a reputation for not wanting more — which is a reasonable thing for a supervisor to conclude.</p>

<p><b>The reasonable limits.</b> Taking on more is not the same as being taken advantage of. If it is regular, substantial and permanent, it is worth saying so: <i>I am happy doing this — is it something that could become part of the role?</i> That sentence is not a demand and it opens the conversation. Doing it silently for a year and becoming resentful is the failure mode, and it is common.</p>

<p><b>Do it properly or do not take it.</b> Half-doing extra responsibility is worse than declining it, because it produces exactly the evidence you did not want — that giving you more does not work. If you cannot do it well, say so at the start; that is a much better conversation than the one afterwards.</p>

<p><b>And say what you did.</b> Not boasting — reporting. <i>I trained Chidi on the chiller this week, he is fine on it now</i>. Supervisors are busy and do not see most of what happens, and work nobody knows about is work that did not count. That sentence takes four seconds and it is the difference between having done something and being known to have done it.</p>

<p><b>The version of this that goes wrong.</b> Somebody takes on extra work, does it well, says nothing about it for a year, and then raises it all at once when they are passed over. From their side it is a fair accumulation of evidence. From the supervisor's side it is a surprise and reads as a grievance, because none of it was visible at the time. The four-second sentence at the moment is worth more than the same information delivered later in bulk.</p>

<blockquote>WATCH-OUT: Half-doing extra responsibility is worse than declining it. It answers the only question that mattered — whether more can be given to you — in the wrong direction, and it is difficult to reopen.</blockquote>"""
, [
 C("Extra responsibility usually arrives:",
   ["With the title", "Before the title and before the money",
    "After a review", "By application"], 1,
   "As a favour, a gap, or nobody else being available."),
 C("Half-doing extra responsibility is worse than declining it because it:",
   ["Wastes time", "Answers the only question that mattered, in the wrong direction",
    "Annoys colleagues", "Delays the decision"], 1,
   "The question was whether more can be given to you, and a half-done job answers it and is hard to reopen."),
 C("Saying what you did is described as:",
   ["Boasting", "Reporting",
    "Unnecessary", "A review matter"], 1,
   "Work nobody knows about is work that did not count.")]),

("If retail is not your career", 10, """<p>Plenty of people do this for a year or two on the way to something else. That is entirely reasonable, and a track written as though everybody is climbing would be useless to them — so this chapter is for that reader.</p>

<p><b>What genuinely transfers, and it is more than people think.</b> Dealing with people you did not choose. Working to a standard when tired and unsupervised. Handling money and being trusted with it. Staying calm with somebody angry. Turning up reliably. Knowing when to escalate. Every one of those is asked about in interviews for jobs that have nothing to do with shops, and most people leaving retail cannot describe any of them because they never thought of them as skills.</p>

<p><b>Which is worth fixing before you leave.</b> Write down, while you still remember, the specific things you did: the section you kept, the person you trained, the complaint you handled, the incident you were part of. Not a CV line — the actual examples with numbers where you have them. Six months later you will remember almost none of it, and a specific example is worth more in any interview than a general claim about being hardworking.</p>

<p><b>Do the job well anyway, and the reason is practical.</b> Whoever manages you will be asked about you by somebody, possibly for years. Retail is smaller than it looks and the same names recur. The person who coasted for eight months because they were leaving anyway has paid for it in a reference they will never see.</p>

<p><b>Leaving well is its own competence.</b> Give proper notice. Work the notice properly rather than mentally departing on the day you resign. Hand over what you know — the section's quirks, the supplier's habits, where things live. And say thank you to the people who trained you, which costs nothing and is remembered disproportionately.</p>

<p><b>And do not disparage it while you are in it.</b> Not for the shop's sake — for yours. Somebody who spends a year telling people this is not their real job has spent a year being worse at something they were doing anyway, and has not arrived at the real one any faster.</p>

<p><b>And a note for the reader who is not sure yet.</b> Plenty of people arrive intending to stay a year and are still there at five, having discovered they are good at it and that it goes somewhere. Plenty of others are certain it is a career and leave within eighteen months. Neither is a failure of planning — you cannot know from outside a job whether it suits you, and the useful position is to do it properly while you find out rather than deciding in advance and acting on the decision.</p>

<blockquote>IMPLEMENTATION TIP: Keep a note on your phone of specific things you did well, added to whenever something happens. It takes ten seconds each time and it is the single most useful thing you can do for a future application, whatever field it is in.</blockquote>"""
, [
 C("Most people leaving retail cannot describe their transferable skills because:",
   ["They are hard to explain", "They never thought of them as skills",
    "Employers do not ask", "They are too general"], 1,
   "Dealing with people, working unsupervised, handling money and staying calm are all asked about elsewhere."),
 C("Doing the job well even when leaving matters because:",
   ["It is the right thing", "Whoever manages you will be asked about you, possibly for years",
    "Notice periods require it", "It affects final pay"], 1,
   "Retail is smaller than it looks and the same names recur."),
 C("Spending a year telling people this is not your real job means:",
   ["Nothing much", "A year spent being worse at something you were doing anyway",
    "Colleagues understand", "You arrive sooner"], 1,
   "And it does not get anybody to the real one any faster.")]),

("What the next step actually is", 10, """<p>The step above you is usually senior assistant, keyholder or supervisor depending on the business. It is worth knowing what it involves, because people take it expecting more of the same job and it is a different one.</p>

<p><b>What changes.</b> You stop being judged on what you did and start being judged on what happened. If the section is not filled, that is now yours even though somebody else was meant to fill it. That single shift is the whole difficulty of the step, and it catches almost everybody.</p>

<p><b>The uncomfortable part.</b> You will have to ask people to do things, including people who were your equals last month and including people you like. Some will be fine and some will test it, and the way through is being consistent rather than being liked — the person who asks everybody the same thing every time is accepted quickly, and the one who avoids asking the difficult person is finished within a month.</p>

<p><b>What gets easier than people expect.</b> Most staff want to be told clearly what is needed. A large share of supervision is simply saying the thing plainly and early rather than hoping somebody notices, and people who have watched a good supervisor already know how to do this.</p>

<p><b>What to do before you get there.</b> Watch how your supervisor handles the awkward moments — the person who is late again, the disagreement, the customer who wants somebody senior. That is the part of the job nobody can teach you afterwards and you are getting to observe it free.</p>

<p><b>And whether you want it at all.</b> A genuine question, and it is fine for the answer to be no. The step means more responsibility, harder shifts, other people's mistakes, and often not much more money at first. Some very good shop assistants would be unhappy supervisors and are worth more where they are. Deciding deliberately not to go up is a different thing from drifting, and it is respectable — what is not useful is wanting it, not saying so, and being disappointed.</p>

<p><b>The money question, worth asking properly.</b> Before accepting, ask what the pay is, whether it changes after any probation period, and what the hours become. Not in order to refuse — the first step is often worth taking on poor money because of where it leads — but because deciding with the facts is different from discovering them later and feeling misled. A business that answers those three straightforwardly is telling you something useful about itself.</p>

<blockquote>WORTH KNOWING: The single most common reason a promotion fails is that somebody who was excellent at doing the work could not ask other people to do it. If that is the part you dread, it is the part to practise before you get there, not after.</blockquote>"""
, [
 C("The change at the next step is being judged on:",
   ["More tasks", "What happened rather than what you did",
    "Customer feedback", "Sales figures"], 1,
   "If the section is not filled, it is yours even though somebody else was meant to fill it."),
 C("The way through the awkwardness of asking former equals is:",
   ["Being firm early", "Being consistent rather than liked",
    "Explaining the reasons", "Asking the easy people first"], 1,
   "The one who avoids asking the difficult person is finished within a month."),
 C("The commonest reason a promotion fails is somebody who:",
   ["Lacked knowledge", "Was excellent at the work and could not ask others to do it",
    "Worked too many hours", "Was unpopular"], 1,
   "If that is the part you dread, it is the part to practise before you get there.")]),

("Okelewo Stores: Ada is offered the senior role", 10, """<p>Fourteen months in. The senior assistant at the Ibadan branch left, and Ada was offered the role. What is worth reading is the year before it rather than the offer.</p>

<p><b>What the supervisor said when asked why.</b> Not that Ada was the best with customers — she was not, and she knew it; another colleague was noticeably better. What she said was that Ada was the only person she never had to check on, and that when something was wrong Ada told her before she found out some other way.</p>

<p><b>The three things Ada had asked for.</b> At six months, what would I need to do. At nine months, what is the one thing I should do differently — the answer was that she went quiet when she disagreed, which she had not known and which took her about two months to change. At twelve months, she said plainly that she was interested when the role came up.</p>

<p><b>The responsibility that arrived before the title.</b> The household aisle at five months. Training two new starters. The chilled fill for a fortnight after the waste problem, which became permanent because she kept doing it. None of it was paid and all of it was the audition.</p>

<p><b>What she nearly got wrong.</b> When she took the aisle, nobody mentioned it for six weeks and she came close to stopping, on the reasonable grounds that it was extra work nobody had noticed. Her account afterwards was that she carried on mostly out of stubbornness rather than any strategy, which is more honest than most versions of this story.</p>

<p><b>What she asked before accepting.</b> What would be different, what would be hard, and whether there was training. The last question got the answer no, not really, which is the usual answer in a small business — and knowing it in advance was worth more than the training would have been.</p>

<p><b>And what she said yes to.</b> Slightly more money, materially more responsibility, the closing shifts, and being the person who has to tell a friend that they are late again. She took about a week to decide, which the supervisor said afterwards was the right amount of time.</p>

<p><b>What is missing from this account deliberately.</b> Any suggestion that fourteen months is the normal timescale. For some people it is three years, for some it never happens because there is no vacancy, and Ada's branch happened to have somebody leave at the point she was ready. The habits in this module are what made her the obvious choice when the vacancy appeared; they did not create the vacancy, and no amount of doing them would have.</p>

<blockquote>IMPLEMENTATION TIP: The three questions Ada asked are the whole chapter — what would I need to do, what should I do differently, and I am interested. Each is one sentence, none costs anything, and almost nobody asks any of them.</blockquote>"""
, [
 C("The reason given for choosing Ada was that she:",
   ["Was best with customers", "Was the only person the supervisor never had to check on",
    "Had the longest service", "Knew the range best"], 1,
   "And that she told her when something was wrong before she found out another way."),
 C("The feedback at nine months was that Ada:",
   ["Worked too slowly", "Went quiet when she disagreed",
    "Needed more product knowledge", "Avoided difficult customers"], 1,
   "She had not known it, and it took about two months to change."),
 C("Asking whether there was training got the answer no, which was:",
   ["A reason to decline", "The usual answer in a small business, and worth knowing in advance",
    "Unexpected", "A negotiating point"], 1,
   "Knowing it beforehand was worth more than the training would have been.")]),

("Review, and the three questions", 10, """<p>The module in short, and it reduces to less than most.</p>

<p><b>The five things, in order.</b> Reliability. A section right unwatched. Taking something on. Being good with customers. Knowing the products. Most people work hardest on the fifth and assume the fourth is first.</p>

<p><b>Promotion is a prediction, not a reward.</b> Somebody is deciding whether you can be relied on with more, and will have to answer for the decision. The shortcut: what would your supervisor have to check if you were given something new?</p>

<p><b>Ask.</b> What would I need to do to be considered. What is the one thing I should do differently. And say that you are interested, because nobody can read it. Take feedback without defending, ask again in a month, accept the answer.</p>

<p><b>Practise one thing at a time.</b> Small, specific, yours, for a fortnight. The improvement happens in the thirty seconds after something goes badly, answering one honest question and then dropping it.</p>

<p><b>Some of it is not about merit.</b> Whether there is anywhere to go, whether the decider has seen you, availability, timing. If a year of doing everything right changes nothing, check whether there is a vacancy before concluding anything about yourself.</p>

<p><b>Responsibility comes before the title.</b> Take it, do it properly or decline it, say what you did, and say something if it becomes permanent and unrecognised.</p>

<p><b>If you are leaving eventually, leave well and write down what you did</b> while you still remember the specifics.</p>

<p><b>The next step is a different job, not a bigger one.</b> Judged on what happened rather than what you did, and the hard part is asking people — including friends — to do things.</p>

<p><b>The three questions, which are the whole module.</b> What would I need to do to be considered? What is the one thing I should do differently? And: I would be interested, when something comes up. Each is one sentence. Almost nobody asks any of them, which is exactly why they work.</p>

<p><b>One last thing, and it applies whether or not you want promotion at all.</b> Everything in this module makes the job itself better rather than only the prospects. Somebody who practises one thing at a time, asks for feedback and takes on responsibility is more interested at work than somebody waiting for the shift to end — and across a year that difference is worth more day to day than any title. The promotion, if it comes, is a by-product.</p>

<blockquote>WORTH KNOWING: The last module puts all of this into a working day — what a good shift looks like from the first five minutes to the handover, with everything from the whole track in the order it actually happens.</blockquote>"""
, [
 C("The three questions that are the whole module are what you would need to do, what to do differently, and:",
   ["When a vacancy is expected", "Saying that you would be interested",
    "How you are assessed", "Whether training exists"], 1,
   "Each is one sentence, and almost nobody asks any of them."),
 C("The shortcut to all five promotion factors is asking what your supervisor would have to:",
   ["Approve", "Check, if you were given something new",
    "Train you in", "Explain"], 1,
   "The shorter that list, the closer you are."),
 C("Improvement happens specifically:",
   ["Over years of experience", "In the thirty seconds after something goes badly",
    "During training", "When feedback is given"], 1,
   "One honest question, answered and then dropped.")]),
]


QUESTIONS = [
 Q("The first factor in promotion is:", ["Product knowledge", "Reliability", "Customer skill", "Length of service"], 1,
   "Nobody gives a section, a key or a shift to somebody they have to check on.", "Ch1 §2", "What gets you promoted"),
 Q("A section that is right unwatched demonstrates:", ["Tidiness", "Caring about a standard with nobody enforcing it", "Speed", "Product knowledge"], 1,
   "Which is the thing a supervisor's job actually requires.", "Ch1 §3", "What gets you promoted"),
 Q("People are promoted into responsibility they:", ["Are trained for", "Have already been holding informally", "Apply for", "Are assessed on"], 1,
   "A routine, a new starter, an ordering category, the thing nobody does.", "Ch1 §4", "What gets you promoted"),
 Q("Being good with customers ranks:", ["First", "Fourth", "Second", "Fifth"], 1,
   "And almost everybody assumes it is first.", "Ch1 §5", "What gets you promoted"),
 Q("What is not on the promotion list at all includes:", ["Reliability", "Working longer hours than anybody else", "Taking things on", "Being trusted"], 1,
   "Along with being the busiest and being liked.", "Ch1 §7", "What gets you promoted"),
 Q("The exact question worth asking is what you would need to be doing to be:", ["Given a pay rise", "Considered for the senior role", "Trained further", "Moved sections"], 1,
   "Most supervisors have an answer ready and most people never ask.", "Ch2 §2", "Asking"),
 Q("The commonest omission in retail careers is:", ["Not working hard enough", "Never saying you are interested", "Poor timekeeping", "Not asking for training"], 1,
   "Plenty of good staff are passed over because everybody assumed they were content.", "Ch2 §3", "Asking"),
 Q("The question that gets a real answer is:", ["How am I doing?", "What is the one thing I should do differently?", "Am I doing well?", "What are my strengths?"], 1,
   "It asks for one item and gives permission to name it.", "Ch2 §4", "Asking"),
 Q("Defending yourself against feedback teaches the other person:", ["Your reasoning", "Not to bother next time", "That you disagree", "To be more specific"], 1,
   "And the person who stops receiving feedback stops improving without noticing.", "Ch2 §5", "Asking"),
 Q("Asking a second time a month later matters because:", ["It shows persistence", "One conversation is a moment and asking twice is a pattern", "The answer may change", "It is expected"], 1,
   "It also lets you show you acted on the first answer.", "Ch2 §6", "Asking"),
 Q("Arguing with a 'not yet' answer:", ["Clarifies the position", "Confirms whatever the reservation was", "Is expected", "Speeds things up"], 1,
   "Ask what would change it instead.", "Ch2 §7", "Asking"),
 Q("Doing a job for a year:", ["Makes you a year better at it", "Does not necessarily make you better at it", "Guarantees promotion", "Builds all the required skills"], 1,
   "Some people are exactly as good in year three as in month three.", "Ch3 §1", "Practising"),
 Q("Repetition without attention produces:", ["Skill", "Speed", "Confidence", "Consistency"], 1,
   "Which is why experience does not accumulate on its own.", "Ch3 §2", "Practising"),
 Q("The thing to practise should be worked on for about:", ["A day", "A fortnight", "Three months", "A year"], 1,
   "Long enough to become slightly automatic, short enough not to lose interest.", "Ch3 §4", "Practising"),
 Q("Deliberate practice in a shop happens:", ["During training", "In the thirty seconds after something goes badly", "At reviews", "When shadowing"], 1,
   "One question, answered honestly and then dropped.", "Ch3 §5", "Practising"),
 Q("Knowing your weaknesses matters because somebody who does not:", ["Cannot improve", "Is surprised by them regularly", "Is overconfident", "Avoids feedback"], 1,
   "Nobody is good at all of retail.", "Ch3 §7", "Practising"),
 Q("A branch where nobody has left in three years offers:", ["Steady development", "No vacancy however good you are", "Better training", "Faster promotion"], 1,
   "A business opening branches needs supervisors constantly.", "Ch4 §2", "Not about merit"),
 Q("A manager rarely on your shift knows you through:", ["Your record", "What somebody else tells them", "Reports", "Observation"], 1,
   "Which is why occasional visibility to the decider is worth something.", "Ch4 §3", "Not about merit"),
 Q("Weekend and evening availability affects promotion because:", ["It shows commitment", "A supervisor covers the hardest shifts", "Policy requires it", "It suits the rota"], 1,
   "A constraint rather than a judgement.", "Ch4 §4", "Not about merit"),
 Q("What you can control about timing is:", ["When vacancies arise", "Being ready more of the time", "Who decides", "The interview"], 1,
   "So that more of the coincidences land on you.", "Ch4 §5", "Not about merit"),
 Q("Where a decision was genuinely unfair, what does not work is:", ["Asking what would have made the difference", "Staying and being bitter", "Deciding whether to leave", "Raising it once"], 1,
   "It damages nobody but you.", "Ch4 §6", "Not about merit"),
 Q("Extra responsibility usually arrives as:", ["A formal offer", "A favour, a gap, or nobody else being available", "Part of a review", "A training plan"], 1,
   "Nobody announces it as a development opportunity.", "Ch5 §2", "Before the title"),
 Q("Saying no to extra responsibility twice produces:", ["No consequence", "A reputation for not wanting more", "A formal note", "A different offer"], 1,
   "Which is a reasonable thing for a supervisor to conclude.", "Ch5 §3", "Before the title"),
 Q("Where extra responsibility becomes permanent, the sentence offered is whether it:", ["Should be paid", "Could become part of the role", "Can be shared", "Was agreed"], 1,
   "Not a demand, and it opens the conversation.", "Ch5 §4", "Before the title"),
 Q("If you cannot do extra responsibility well, you should:", ["Do your best quietly", "Say so at the start", "Take it and ask for help later", "Decline without explaining"], 1,
   "A much better conversation than the one afterwards.", "Ch5 §5", "Before the title"),
 Q("Work nobody knows about is:", ["Its own reward", "Work that did not count", "Noticed eventually", "Recorded anyway"], 1,
   "Supervisors are busy and do not see most of what happens.", "Ch5 §6", "Before the title"),
 Q("Skills that transfer out of retail include handling money, staying calm and:", ["Merchandising", "Working to a standard when tired and unsupervised", "Stock systems", "Product knowledge"], 1,
   "All asked about in interviews for jobs with nothing to do with shops.", "Ch6 §2", "If retail is not your career"),
 Q("Specific examples should be written down:", ["At the exit interview", "While you still remember them", "In a CV", "When applying"], 1,
   "Six months later you will remember almost none of it.", "Ch6 §3", "If retail is not your career"),
 Q("Coasting because you are leaving anyway is paid for in:", ["Final wages", "A reference you will never see", "A shorter notice period", "Colleagues' opinions"], 1,
   "Retail is smaller than it looks and the same names recur.", "Ch6 §4", "If retail is not your career"),
 Q("Leaving well includes proper notice, working it properly, handing over what you know and:", ["Requesting a reference", "Thanking the people who trained you", "An exit interview", "Returning equipment"], 1,
   "It costs nothing and is remembered disproportionately.", "Ch6 §5", "If retail is not your career"),
 Q("At the next step you are judged on:", ["Your own work", "What happened", "Hours worked", "Customer feedback"], 1,
   "The section unfilled is yours even though somebody else was meant to fill it.", "Ch7 §2", "The next step"),
 Q("The supervisor who avoids asking the difficult person is:", ["Being tactful", "Finished within a month", "Building goodwill", "Delaying wisely"], 1,
   "Consistency is what gets accepted quickly.", "Ch7 §3", "The next step"),
 Q("A large share of supervision turns out to be:", ["Monitoring", "Saying the thing plainly and early", "Scheduling", "Reporting upward"], 1,
   "Most staff want to be told clearly what is needed.", "Ch7 §4", "The next step"),
 Q("What to observe before being promoted is how your supervisor handles:", ["Busy periods", "The awkward moments", "Paperwork", "Deliveries"], 1,
   "It is the part nobody can teach you afterwards.", "Ch7 §5", "The next step"),
 Q("Deciding deliberately not to seek promotion is:", ["A failure of ambition", "Respectable, and different from drifting", "Rare", "Discouraged"], 1,
   "What is not useful is wanting it, not saying so, and being disappointed.", "Ch7 §6", "The next step"),
 Q("Ada was chosen despite another colleague being:", ["More experienced", "Noticeably better with customers", "Longer serving", "Better qualified"], 1,
   "She was the only person the supervisor never had to check on.", "Ch8 §2", "Ada's offer"),
 Q("The three things Ada asked came at:", ["Three, six and nine months", "Six, nine and twelve months", "Twelve months only", "Every quarter"], 1,
   "What would I need to do, what should I do differently, and stating her interest.", "Ch8 §3", "Ada's offer"),
 Q("The responsibility Ada held before any title included the aisle, training two starters and:", ["The stockroom", "The chilled fill", "The tills", "Deliveries"], 1,
   "None of it was paid and all of it was the audition.", "Ch8 §4", "Ada's offer"),
 Q("Ada nearly stopped keeping the aisle because:", ["It was too much work", "Nobody mentioned it for six weeks", "She was moved sections", "The supervisor objected"], 1,
   "She carried on mostly out of stubbornness rather than any strategy.", "Ch8 §5", "Ada's offer"),
 Q("Before accepting, Ada asked what would be different, what would be hard and:", ["What it paid", "Whether there was training", "Who else applied", "When it started"], 1,
   "The answer was no, not really, which is usual in a small business.", "Ch8 §6", "Ada's offer"),
 Q("Ada took about a week to decide, which the supervisor said was:", ["Too long", "The right amount of time", "Unnecessary", "A concern"], 1,
   "The role meant closing shifts and telling a friend they are late again.", "Ch8 §7", "Ada's offer"),
 Q("The three questions are described as working precisely because:", ["They are difficult", "Almost nobody asks any of them", "Supervisors expect them", "They are formal"], 1,
   "Each is one sentence and none costs anything.", "Ch9 §10", "Review"),
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

    rebalance(QUESTIONS, "shopfloor:getting_better:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:getting_better:checks")

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
        "title": "RF 8 — Getting Better",
        "desc": ("What actually gets somebody promoted, in order, including the parts that are "
                 "not about merit. The three questions almost nobody asks, how to practise "
                 "rather than merely repeat, taking responsibility before the title, what "
                 "transfers if retail is not your career, and what the next step actually "
                 "involves."),
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
