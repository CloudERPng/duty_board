#!/usr/bin/env python3
"""Build 'The Shift and the People On It' into academy_shopfloor_data.json.

Module 6 of Retail Foundations.

Modules 1 to 5 are about what one person does. This is about doing it alongside
other people, which is where most of the actual difficulty of a retail job
sits — not the tasks, but the rota, the handover, the colleague who does less,
and the supervisor who is having a bad week.

Four positions:

  RELIABILITY IS THE SUBJECT, NOT AN ASIDE. Module 1 said it is the largest
  differentiator; this module says why in terms the reader feels rather than
  agrees with: lateness and absence are not abstractions, they land on named
  colleagues who then cover, and that is the whole of how a team's goodwill is
  spent. Framed that way it stops being a rule and becomes a relationship.

  THE HANDOVER IS THE TEAM'S REAL INFRASTRUCTURE. Almost every complaint about
  colleagues turns out on inspection to be a handover that did not happen.

  CONFLICT ADVICE MUST BE USABLE BY SOMEBODY WITH NO POWER. Most guidance on
  workplace conflict assumes standing the reader does not have. This module
  gives a junior person three things they can actually do and is honest that
  some situations are not theirs to solve.

  AND IT NAMES WHAT IS NOT ACCEPTABLE. Bullying, harassment, discrimination and
  being asked to work unsafely are not difficult colleagues; they are separate,
  they have routes, and a track written for young people entering their first
  job should say so plainly rather than leaving them to work it out.

Run from the app package directory:  python3 build_shopfloor_m6.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_shift"
DATA = "academy_shopfloor_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("What a shift actually is", 10, """<p>A shift is not a block of hours you are present for. It is a stretch of trading that has to be covered continuously, and you are one of the people covering it — which sounds like the same thing and produces completely different behaviour.</p>

<p><b>The difference in practice.</b> Somebody working hours arrives at nine, works, and leaves at five. Somebody covering trading arrives before nine so they can start at nine, finds out what happened before them, and does not leave a section half-filled at five because the person following will meet it.</p>

<p><b>Why the distinction is worth making early.</b> Because almost every friction between colleagues in a shop comes from this. The colleague who leaves the delivery half-worked, the one who never restocks the bags, the one who takes a break at the busiest moment — mostly they are working their hours rather than covering trading, and they usually do not know there is a difference.</p>

<p><b>The three things a shift owes the one after it.</b> A section in a state somebody can pick up. The information they need — what happened, what is outstanding, what is coming. And no accumulated problems that were easier to solve an hour ago than they will be in an hour's time.</p>

<p><b>What you are owed in return.</b> Exactly the same, and this is the argument that makes it work rather than a lecture about being conscientious. A team where everybody does this is a team where nobody starts a shift by discovering a mess, and the difference in how the job feels is substantial.</p>

<p><b>The uncomfortable version.</b> If most people in a branch are doing this and you are not, it is visible immediately and it costs you more than any single mistake would. If most people are not and you are, it is thankless for a while and it is still the right side to be on — partly because somebody notices within a couple of months, and partly because you will be the person who does not spend every morning fixing yesterday.</p>

<p><b>Where this is hardest, and it is worth naming.</b> The last twenty minutes. Everything in you wants to stop, the shop is closing or your replacement has arrived, and the section is nearly right. Those twenty minutes are disproportionately what colleagues judge you on, because they are the part they inherit — nobody sees the four hours you worked well and everybody meets the trolley you left. It is unfair as an assessment and it is entirely accurate as a prediction of what following you is like.</p>

<p><b>And the version of this that applies to a whole branch.</b> Some shops run as a chain of shifts that each clean up after the last, and some run as a chain that each hands over to the next. The work is identical and the experience of doing it is completely different — the first is exhausting and slightly resentful, the second is ordinary. Which one a branch becomes is decided by about six people each choosing, without discussing it, how they spend their last twenty minutes.</p>

<blockquote>WORTH KNOWING: The quickest way to be liked in a shop has nothing to do with being sociable. It is being the person whose shifts other people are glad to follow.</blockquote>"""
, [
 C("Most friction between colleagues in a shop comes from the difference between:",
   ["Experience levels", "Working hours and covering trading",
    "Full-time and part-time", "Sections"], 1,
   "And the person working their hours usually does not know there is a difference."),
 C("The three things a shift owes the next one are a section somebody can pick up, the information they need, and:",
   ["A full till", "No accumulated problems that were easier to solve an hour ago",
    "A completed checklist", "A tidy stockroom"], 1,
   "Problems get more expensive the longer they wait."),
 C("The quickest way to be liked in a shop is:",
   ["Being sociable", "Being somebody whose shifts other people are glad to follow",
    "Working extra hours", "Helping with breaks"], 1,
   "It has nothing to do with being outgoing.")]),

("Turning up", 10, """<p>Module 1 said reliability is the largest differentiator between staff. This is why, stated in a way that is harder to dismiss.</p>

<p><b>What lateness actually is.</b> Not a mark against you in a file. It is a specific colleague standing at a till for twenty extra minutes who cannot go home, or a section not filled before the shop opens, or somebody's break moved. Lateness does not cost the business abstractly — it lands on a named person, every time, and they know.</p>

<p><b>Which is why it accumulates differently from other faults.</b> Being slow at something, or not knowing the range, or getting an order wrong are all things colleagues forgive easily because they cost them nothing. Being late costs them directly. Five minutes twice a week is not a small thing to the person covering it, and it is the commonest reason a team quietly stops helping somebody.</p>

<p><b>The margin, and it is the whole technique.</b> Aim to arrive ten minutes early and you will be on time on the day the bus does not come. Aim to arrive exactly on time and you will be late roughly once a fortnight, because transport in this market is not reliable enough to plan to the minute. The ten minutes is not virtue; it is arithmetic about variance.</p>

<p><b>When you are going to be late anyway.</b> Ring, early, and say when you will actually arrive. The call is worth far more than the minutes — it converts an absence somebody has to react to into a delay they can plan around. And say the real time rather than the hopeful one, because a second call moving it again costs more credibility than the original lateness.</p>

<p><b>Sickness, said properly.</b> Genuinely ill is genuinely ill, and coming in sick to a food or pharmacy business is not conscientious, it is a problem for everybody. Ring as early as you can, because the person building the day's cover at seven can do something and the one finding out at nine cannot. And do not explain at length; the shop needs to know you are not coming and roughly for how long.</p>

<p><b>The one that is worth more than all of it.</b> Do not swap or drop shifts casually once accepted. A rota is a promise several people have planned around, and somebody who changes theirs regularly makes everybody else's less reliable.</p>

<p><b>What lateness does to you rather than to others.</b> A person who arrives at the last possible minute starts every shift behind — no handover, no walk of the section, straight into whatever is loudest. That is module 1's five minutes lost every single day, and it compounds: the shift is more reactive, more tiring and more error-prone before it has begun. The margin is not only courtesy to colleagues; it is what lets you start the day rather than have the day start on you.</p>

<blockquote>IMPLEMENTATION TIP: Set your alarm for a start ten minutes earlier than your shift needs, permanently, and stop thinking about it. Almost everybody who is reliably on time has done exactly this, and almost nobody who is regularly late has.</blockquote>"""
, [
 C("Lateness differs from other faults because it:",
   ["Is recorded formally", "Lands on a named colleague every time",
    "Is easily noticed", "Affects customers"], 1,
   "Colleagues forgive being slow or not knowing things because those cost them nothing."),
 C("Aiming to arrive exactly on time produces lateness roughly:",
   ["Never", "Once a fortnight",
    "Once a month", "Only in bad weather"], 1,
   "The ten-minute margin is arithmetic about variance rather than virtue."),
 C("When ringing to say you will be late, you should give:",
   ["The earliest possible time", "The real time rather than the hopeful one",
    "No time until you know", "A range"], 1,
   "A second call moving it again costs more credibility than the original lateness.")]),

("The handover", 10, """<p>Almost every complaint about a colleague turns out, when examined, to be a handover that did not happen. It takes thirty seconds and almost nobody does it properly.</p>

<p><b>What it consists of.</b> Four things, in about three sentences. What happened that they need to know. What is outstanding and where it got to. What is coming — a delivery, a collection, a customer returning. And anything that is not obvious: a machine playing up, a section left deliberately, a decision somebody made.</p>

<p><b>The test of a good one.</b> The person taking over does not discover anything in their first hour that you already knew. That is the whole standard, and it is easy to check afterwards.</p>

<p><b>Why written beats spoken where it is possible.</b> Not because people forget, though they do, but because a spoken handover only reaches the person standing in front of you. A note in whatever your branch uses reaches the person on tomorrow's early shift who was not there. Where there is no book or board, three lines on paper left where somebody will see it does the same job.</p>

<p><b>The half-finished job, which is where most of the trouble is.</b> Leaving something half-done is often unavoidable — a shift ends mid-task. What makes it a problem is leaving it half-done and silent. <i>The chilled delivery is done except the yoghurts, they are on the trolley in the back</i> converts an abandoned job into a handed-over one, and the difference in how it is received is enormous for a sentence that takes four seconds.</p>

<p><b>Receiving a handover badly.</b> The commonest failure is not listening properly because you are already thinking about starting. If somebody is telling you something, stop and take it — you are being given, free, the information you would otherwise spend an hour discovering.</p>

<p><b>And when there is nobody to hand over to.</b> Closing shifts, or a gap between staff. Write it. The absence of a person is not the absence of a next shift, and a note left on a closing shift is the most useful thing an opener can find.</p>

<p><b>What not to put in a handover.</b> Opinions about people. <i>The delivery is short two cases</i> is a handover; <i>the driver was useless again</i> is a complaint that will be read by several people including, eventually, somebody you did not intend. Keep it factual for the same reason module 5 said to report facts rather than conclusions — anything written down travels further and lasts longer than the moment it was written in.</p>

<p><b>The handover you give a supervisor rather than a colleague.</b> Slightly different: they need the exceptions rather than the routine. What went wrong, what you could not finish, what a customer will ring about tomorrow, and anything you noticed that they will want to know before somebody else tells them. That last one is worth its own emphasis — a supervisor who hears about a problem from you rather than from a complaint is a supervisor who trusts you, and that trust is built almost entirely in thirty-second conversations at the end of shifts.</p>

<blockquote>IMPLEMENTATION TIP: End every shift with one sentence to whoever is next, even when nothing happened — especially then, because 'nothing outstanding, delivery came, all put away' is genuinely useful information and it builds the habit for the days when there is something.</blockquote>"""
, [
 C("The test of a good handover is that the person taking over:",
   ["Asks no questions", "Discovers nothing in their first hour that you already knew",
    "Signs the book", "Starts immediately"], 1,
   "Easy to check afterwards, which is what makes it a real standard."),
 C("Written handover beats spoken mainly because:",
   ["People forget", "It reaches somebody who was not there",
    "It is required", "It is more formal"], 1,
   "A spoken handover only reaches the person standing in front of you."),
 C("Leaving a job half-done becomes a problem when it is left:",
   ["Untidy", "Half-done and silent",
    "For somebody junior", "Near closing"], 1,
   "One sentence converts an abandoned job into a handed-over one.")]),

("Working next to people", 10, """<p>You do not choose your colleagues and you spend more waking hours with them than with most of your friends. A few things make that go better and almost none of them are about being sociable.</p>

<p><b>Do your share of the work nobody wants.</b> Every shop has jobs people avoid — the bins, the cleaning, the section that is always a mess, the late shift. Somebody is doing them. A person who visibly takes their turn is forgiven a great deal; a person who is always elsewhere when those jobs come round is noticed within about a fortnight, and no amount of being pleasant compensates.</p>

<p><b>Help before being asked, in small amounts.</b> Not martyrdom. Taking the queue when somebody is stuck, carrying the other end, finishing the last of a job somebody ran out of time for. Small, frequent, unremarked — that is what builds the thing that means people help you when you need it.</p>

<p><b>Do not keep score out loud.</b> Everybody notices imbalance and mentioning it constantly is what makes it corrosive rather than merely present. If it is genuinely one-sided over months, that is a conversation with a supervisor rather than a running commentary to colleagues.</p>

<p><b>Be careful with the group.</b> Every workplace has grumbling, and a certain amount is normal and harmless. What is not harmless is being drawn into the running criticism of a particular person, because it always gets back, and because the person who joins in is remembered as much as the person who started it. Neither defending nor joining — just not participating — is a workable position and it costs nothing.</p>

<p><b>Two practical things about new people.</b> When somebody joins, tell them the things that are not written down: where things are, who to ask, what the unwritten rules are. It takes ten minutes and it is remembered for a year. And when you are the new person, ask; nobody minds in the first month, and the window closes faster than people expect.</p>

<p><b>The one that matters more in a small branch than anywhere else.</b> Leave the disagreement at the end of the shift. In a team of eight, a grudge held for a fortnight makes everybody's job worse, and there is nowhere to go to avoid each other. Say the thing, or let it go — carrying it is the option that costs the most.</p>

<p><b>The colleague you find difficult personally.</b> There will be one, and liking everybody is not a requirement of the job. What is required is working with them properly — the same handover, the same help, the same information — because the alternative punishes customers and other colleagues for something between the two of you. Civil and useful is an achievable standard with somebody you would not choose, and being able to do it is genuinely valuable.</p>

<blockquote>WORTH KNOWING: The colleague who helps you when you are struggling is almost always the one you helped six weeks ago without thinking about it. That is not a moral claim, it is just how it works.</blockquote>"""
, [
 C("A person who is always elsewhere when the unpopular jobs come round is noticed within about:",
   ["A day", "A fortnight",
    "Six months", "A year"], 1,
   "And no amount of being pleasant compensates for it."),
 C("Being drawn into running criticism of a colleague is harmful partly because:",
   ["It wastes time", "The person who joins in is remembered as much as the one who started it",
    "Supervisors disapprove", "It is against policy"], 1,
   "Not participating is a workable position that costs nothing."),
 C("In a small branch, carrying a disagreement for a fortnight is:",
   ["Sometimes necessary", "The option that costs the most",
    "Better than confrontation", "Normal"], 1,
   "There is nowhere to go to avoid each other, so it makes everybody's job worse.")]),

("When somebody is not pulling their weight", 10, """<p>It will happen and it is genuinely irritating. Most advice on this assumes an authority you do not have, so here is the version that works from where you are standing.</p>

<p><b>First, consider that you might be wrong.</b> Not as politeness — as accuracy. People are frequently doing something you cannot see: a different section, a task somebody assigned quietly, a personal situation. And people who are struggling often look like people who are not trying. Spend a week noticing before concluding.</p>

<p><b>Second, if it is genuinely happening, say something to them once and lightly.</b> Not a confrontation and not a complaint — a request. <i>Could you take the bins tonight, I did them the last two?</i> is a sentence almost anybody accepts, and a surprising share of imbalance is not deliberate at all. People lose track of whose turn it was, and a light ask resets it without anybody losing face.</p>

<p><b>Third, if it continues, tell your supervisor once, factually, and then stop.</b> Facts rather than character: <i>the bins have not been done on the late shift for three weeks</i>, not <i>he never does anything</i>. The first is actionable and the second is a complaint about a person that puts the supervisor in an awkward position and you in a worse one.</p>

<p><b>And then genuinely let it go.</b> This is the hard part. Once you have said it, it is not yours — the supervisor may be dealing with it in ways you will never see, or may have decided not to, or may be handling something about that person that is none of your business. Continuing to raise it makes you the problem in the conversation, however right you were originally.</p>

<p><b>What not to do, in order of how much damage it causes.</b> Do not do their work silently and resentfully for months. Do not discuss it with other colleagues. Do not start matching their effort downward, which is the commonest response and the one that costs you most, because you will be judged on your work rather than on the comparison.</p>

<p><b>And the honest limit.</b> Some situations do not get resolved. A colleague who does less may be tolerated for reasons nobody explains to you. You can work well, say your piece once, and decide whether the job is worth it on balance — but you cannot fix another person's performance from beside them, and trying is the thing that makes people leave jobs they otherwise liked.</p>

<blockquote>WATCH-OUT: Matching somebody's lower effort feels like fairness and reads as poor performance. Nobody assessing you will place your work next to theirs; they will place it next to what the job requires.</blockquote>"""
, [
 C("The first response to a colleague apparently not pulling their weight is to:",
   ["Tell the supervisor", "Consider that you might be wrong",
    "Speak to them directly", "Match their effort"], 1,
   "People who are struggling often look like people who are not trying."),
 C("Reporting it should be done in terms of:",
   ["Their character", "Facts",
    "The team's view", "Your workload"], 1,
   "'The bins have not been done on the late shift for three weeks' is actionable; 'he never does anything' is not."),
 C("Matching a colleague's lower effort:",
   ["Restores fairness", "Reads as poor performance",
    "Prompts a conversation", "Is a reasonable response"], 1,
   "Nobody assessing you will place your work next to theirs; they will place it next to what the job requires.")]),

("Your supervisor", 10, """<p>The person running your shift has more influence on whether you enjoy this job than anybody else, including the manager. A few things make that relationship work.</p>

<p><b>What they are actually dealing with.</b> Covering the rota with people who are off sick, hitting something they are measured on, somebody above them asking for things, and a floor to run at the same time. They are usually a former shop assistant promoted eighteen months ago, frequently with no training in managing anybody, and they are improvising more than they let on.</p>

<p><b>Which makes the useful behaviours obvious.</b> Bring solutions where you have one. Tell them things early rather than at the point of crisis. Do not make them chase you. And be somebody they can rely on without checking — that last one is worth more to a supervisor than any amount of enthusiasm.</p>

<p><b>Asking for things.</b> Time off, a shift change, a different section. Ask early, ask once, accept the answer, and give a reason if you have one. A request made three weeks ahead is a scheduling matter and the same request made on Thursday for Saturday is a problem — the answer often changes purely on that, which is worth knowing before assuming a refusal was about you.</p>

<p><b>When you disagree.</b> Say it once, privately, and then do it. Not in front of customers, not in front of the team, not by doing it your own way quietly. A supervisor who is publicly disagreed with has to defend the decision rather than consider it; the same point made privately is often accepted, sometimes immediately.</p>

<p><b>What to do when a supervisor gives you an instruction that contradicts an earlier one.</b> It happens constantly and it is rarely inconsistency — usually something changed that you were not told about. Ask once, neutrally: <i>do you want me to do X instead of Y, or as well?</i> That single question resolves most of it, avoids the appearance of arguing, and produces the information you actually need rather than a guess about which instruction was more recent.</p>

<p><b>When they are wrong and it matters.</b> Safety, honesty, something that will harm a customer. Say so plainly at the time, and if it is not resolved, take it further — module 5 covered the shape of that. Everything else is a preference and can wait.</p>

<p><b>And when they are having a bad week.</b> Supervisors are sharp under pressure sometimes, and it is very rarely about you. The right response is to be steady rather than to take it personally or to match it. If it becomes a pattern rather than a week, that is different and it belongs with the next chapter.</p>

<blockquote>IMPLEMENTATION TIP: Ask your supervisor once what would make their week easier. Almost nobody asks, most have an immediate answer, and it is usually something small that you are already in a position to do.</blockquote>"""
, [
 C("A request for time off made three weeks ahead versus on Thursday for Saturday:",
   ["Receives the same answer", "Often gets a different answer purely because of the notice",
    "Requires a form either way", "Depends on the reason"], 1,
   "Worth knowing before assuming a refusal was about you."),
 C("Disagreeing with a supervisor should happen:",
   ["In the moment, so it is fresh", "Once, privately, followed by doing it",
    "In front of the team for fairness", "Through the manager"], 1,
   "A supervisor publicly disagreed with has to defend the decision rather than consider it."),
 C("A supervisor being sharp under pressure is:",
   ["A sign of a problem with you", "Very rarely about you",
    "Grounds for a complaint", "Best matched in kind"], 1,
   "The right response is steadiness; a pattern rather than a week is a different matter.")]),

("What is not acceptable", 10, """<p>Everything so far has been about ordinary difficulty between people trying to do a job. This chapter is about the things that are not that, because a track written for people starting out should say plainly where the line is rather than leave them to work it out.</p>

<p><b>What this covers.</b> Bullying — persistent, targeted, humiliating behaviour rather than somebody being sharp on a bad day. Harassment of any kind, including sexual, and including from customers rather than colleagues. Discrimination because of who somebody is. Being pressured into something dishonest. And being told to do something unsafe, or to work in a way that puts you or a customer at risk.</p>

<p><b>The first thing to know, and it is the one people most need.</b> None of these is something to put up with as part of learning the job. There is a version of retail culture that treats a hard time as initiation, and it is wrong. Being new means you know less, not that you are owed less.</p>

<p><b>What to do, and the order is deliberate.</b> Write it down as it happens — what, when, who was there, what was said. Memory is the first thing to go and the first thing questioned, and a contemporaneous note is worth more than a confident recollection months later. Then tell somebody: your supervisor if they are not the problem, their manager if they are, or whatever route your business has. Say it once, clearly, with the record.</p>

<p><b>If nothing happens.</b> Go higher, once. Many businesses have somebody specific for this, and where yours does not, the owner or the most senior person available is the route. And if there is genuinely nowhere — that tells you something important about the business rather than about you.</p>

<p><b>The customer version, which is common and under-discussed.</b> A customer being abusive, threatening, or making comments about your appearance or who you are is not something to absorb because they are a customer. Step away, get somebody, and expect the business to back you. A shop that requires staff to endure that is not managing a customer relationship, it is failing at something basic.</p>

<p><b>And unsafe work.</b> Climbing on something not meant for it, lifting alone what needs two, working with a spill uncleaned, being alone somewhere you should not be alone. You are entitled to decline and to say why. Nothing in a shop is worth an injury, and the pressure to get on with it is exactly what these situations are made of.</p>

<blockquote>WORTH KNOWING: Writing it down at the time is the single most useful thing on this page. It costs two minutes, it is often never needed, and where it is needed there is no substitute for it.</blockquote>"""
, [
 C("The most useful immediate action when something unacceptable happens is to:",
   ["Confront the person", "Write down what, when, who was there, and what was said",
    "Tell colleagues", "Wait to see if it recurs"], 1,
   "A contemporaneous note is worth more than a confident recollection months later."),
 C("The view that a hard time is part of being new is:",
   ["Traditional but harmless", "Wrong",
    "Understandable", "Common in retail"], 1,
   "Being new means you know less, not that you are owed less."),
 C("A customer being abusive or making personal comments is:",
   ["Part of the job", "Not something to absorb because they are a customer",
    "Handled by ignoring it", "A supervisor's judgement"], 1,
   "Step away, get somebody, and expect the business to back you.")]),

("Okelewo Stores: the Saturday two people did not turn up", 10, """<p>Ten months in. A Saturday at the Ibadan branch with two of the five scheduled staff absent — one genuinely ill, one who simply did not appear and did not ring.</p>

<p><b>What that actually meant.</b> Three people covering a Saturday designed for five, in a shop that takes a large share of its week's money that day. No question of doing everything; the only question was what to drop.</p>

<p><b>What the supervisor did in the first ten minutes.</b> Told the three of them the situation plainly rather than pretending it was manageable. Named what was being dropped — facing, the stockroom, the promotional rebuild — and what was not: tills covered, chilled and bread filled, ends checked. Then asked whether anybody could stay two hours later, and accepted the one no without comment.</p>

<p><b>What Ada did.</b> Stayed the two hours. Took the queue when it built rather than finishing her own task first. Wrote nothing down all day and then spent four minutes at close writing the longest handover note she had ever left, because Sunday's opener was walking into an unfilled stockroom and half a promotion.</p>

<p><b>What she did not do.</b> Say anything about the colleague who had not rung. Not to the supervisor and not to the other two, both of whom raised it. Her reasoning afterwards was simple: she did not know why, it was not her business, and the supervisor plainly already knew.</p>

<p><b>What happened to that colleague.</b> Nothing that anybody was told about, which was the correct outcome from where Ada was standing even though it was unsatisfying. He was there the following week and things were normal.</p>

<p><b>The part Ada found hardest, in her own account.</b> Not the extra hours. Being asked twice by colleagues what she thought about the absence, and saying nothing both times, felt like being unhelpful — and it took her several weeks to be sure it had been right. That is worth including because the advice in chapter 4 sounds easy on a page and is uncomfortable in a stockroom with somebody waiting for you to agree with them.</p>

<p><b>What the day cost and what it bought.</b> The branch traded roughly normally, the Sunday shift started badly anyway, and everybody was tired. What it bought was that the three of them worked together differently afterwards — and the specific thing that changed was that the supervisor started saying what was being dropped on ordinary days too, not just bad ones, which turned out to be more useful than the Saturday.</p>

<blockquote>IMPLEMENTATION TIP: On a short-staffed day, the most valuable thing anybody can do is decide out loud what is not being done. Trying to do everything badly is worse than doing less on purpose, and somebody has to say which.</blockquote>"""
, [
 C("The supervisor's first action was to:",
   ["Call for agency cover", "Tell the three plainly what was being dropped and what was not",
    "Reorganise the rota", "Contact the absent staff"], 1,
   "Trying to do everything badly is worse than doing less on purpose."),
 C("Ada said nothing about the colleague who had not rung because:",
   ["She was too busy", "She did not know why, it was not her business, and the supervisor already knew",
    "She was told not to", "It would have caused an argument"], 1,
   "Both other colleagues raised it and she did not join in."),
 C("What changed afterwards that proved most useful was that the supervisor began:",
   ["Rostering more staff", "Saying what was being dropped on ordinary days too",
    "Recording absences", "Holding briefings"], 1,
   "More useful than anything that happened on the Saturday itself.")]),

("Review, and the three habits", 10, """<p>The module in short, then the practice.</p>

<p><b>A shift is trading to be covered, not hours to be present for.</b> You owe the next shift a section they can pick up, the information they need, and no accumulated problems. You are owed the same, which is what makes it work.</p>

<p><b>Lateness lands on a named person.</b> That is why it is forgiven less than being slow or not knowing something. Aim ten minutes early; ring early when you cannot; give the real time; do not swap shifts casually.</p>

<p><b>The handover is the team's real infrastructure.</b> Four things in three sentences, and the test is whether they discover anything in their first hour that you already knew. Write it where you can. Never leave a job half-done and silent.</p>

<p><b>Do your share of the work nobody wants</b>, help in small amounts before being asked, do not keep score out loud, and do not join the running criticism of anybody.</p>

<p><b>When somebody is not pulling their weight:</b> consider you might be wrong, ask them once lightly, tell the supervisor once factually, then let it go. Do not match their effort downward.</p>

<p><b>Your supervisor is improvising more than they let on.</b> Ask early, disagree privately, be reliable without being checked, and do not take a bad week personally.</p>

<p><b>And the line.</b> Bullying, harassment, discrimination, dishonesty and unsafe work are not part of learning the job. Write it down at the time, tell somebody, go higher once if nothing happens.</p>

<p><b>The three habits.</b> One: one sentence of handover at the end of every shift, including the days nothing happened. Two: arrive ten minutes early, permanently, so that the day something goes wrong you are merely on time. Three: take your turn at the job nobody wants, visibly, without mentioning that you are doing it.</p>

<p><b>Why those three and not the others.</b> Because each is entirely within your control, none depends on anybody else's behaviour, and together they produce most of what makes somebody easy to work with — which is the quality that gets a person kept, trained and eventually promoted, and it is much rarer than competence.</p>

<p><b>And a note about the size of this module.</b> Everything here is about other people, which means none of it works perfectly and some of it will not work at all in a badly run branch. That is not a reason to skip it. In a good team these habits make you valuable quickly; in a poor one they make you the person who is easy to work with, which is what somebody remembers when they are asked for a reference or when a better branch has a vacancy. The habits pay in both cases, just through different routes.</p>

<blockquote>WORTH KNOWING: The next module is the hard moments — angry customers, accidents, emergencies and theft in progress. This one was about the ordinary shift going well; the next is about what to do on the days it does not.</blockquote>"""
, [
 C("The three habits are the handover sentence, arriving ten minutes early, and:",
   ["Reporting problems", "Taking your turn at the job nobody wants, without mentioning it",
    "Helping colleagues", "Asking the supervisor questions"], 1,
   "Chosen because each is entirely within your control and none depends on anybody else."),
 C("Being easy to work with is described as:",
   ["Less important than competence", "Much rarer than competence",
    "A matter of personality", "Assessed informally"], 1,
   "It is the quality that gets somebody kept, trained and eventually promoted."),
 C("The handover sentence should be given:",
   ["When something happened", "Including the days nothing happened",
    "Weekly", "Only at closing"], 1,
   "'Nothing outstanding, delivery came, all put away' is useful and it builds the habit.")]),
]


QUESTIONS = [
 Q("Somebody covering trading rather than working hours will:", ["Leave promptly at five", "Arrive before the start so they can begin on time", "Work more hours", "Take fewer breaks"], 1,
   "And not leave a section half-filled because the next person will meet it.", "Ch1 §2", "What a shift is"),
 Q("The colleague who leaves a delivery half-worked is usually:", ["Being lazy", "Working their hours rather than covering trading", "Overloaded", "Untrained"], 1,
   "And they usually do not know there is a difference.", "Ch1 §3", "What a shift is"),
 Q("What makes the shift-owes-shift arrangement work rather than a lecture is:", ["Supervision", "That you are owed the same", "Policy", "Rota design"], 1,
   "A team where everybody does it is one where nobody starts by discovering a mess.", "Ch1 §5", "What a shift is"),
 Q("Being the person doing this when most colleagues are not is:", ["Pointless", "Thankless for a while and still the right side to be on", "A reason to leave", "Noticed immediately"], 1,
   "Somebody notices within a couple of months, and you stop spending mornings fixing yesterday.", "Ch1 §6", "What a shift is"),
 Q("Colleagues forgive being slow or not knowing the range because those faults:", ["Are common", "Cost them nothing", "Improve with time", "Are expected of new staff"], 1,
   "Lateness costs them directly, which is why it accumulates differently.", "Ch2 §3", "Turning up"),
 Q("Five minutes late twice a week is:", ["Negligible", "Not a small thing to the person covering it", "Within tolerance", "A recording matter"], 1,
   "It is the commonest reason a team quietly stops helping somebody.", "Ch2 §3", "Turning up"),
 Q("The ten-minute margin is described as:", ["Good discipline", "Arithmetic about variance", "A company rule", "Excessive"], 1,
   "Transport in this market is not reliable enough to plan to the minute.", "Ch2 §4", "Turning up"),
 Q("Ringing ahead when late converts an absence into:", ["An excused lateness", "A delay somebody can plan around", "A recorded event", "A supervisor's problem"], 1,
   "The call is worth far more than the minutes.", "Ch2 §5", "Turning up"),
 Q("Ringing in sick as early as possible matters because the person building cover at seven:", ["Is more sympathetic", "Can do something, where the one finding out at nine cannot", "Records it accurately", "Can arrange overtime"], 1,
   "And a long explanation is not needed.", "Ch2 §6", "Turning up"),
 Q("Swapping or dropping accepted shifts casually:", ["Is normal practice", "Makes everybody else's rota less reliable", "Requires notice only", "Is a supervisor matter"], 1,
   "A rota is a promise several people have planned around.", "Ch2 §7", "Turning up"),
 Q("A handover consists of four things in about:", ["A written form", "Three sentences", "Five minutes", "A checklist"], 1,
   "What happened, what is outstanding, what is coming, and anything not obvious.", "Ch3 §2", "Handover"),
 Q("The test of a good handover is that the other person discovers nothing in their first hour that:", ["Was written down", "You already knew", "Went wrong", "Was their responsibility"], 1,
   "Easy to check afterwards, which makes it a real standard.", "Ch3 §3", "Handover"),
 Q("Written handover reaches:", ["More reliably", "Somebody who was not there", "The manager", "The record"], 1,
   "A spoken one only reaches the person standing in front of you.", "Ch3 §4", "Handover"),
 Q("'The chilled delivery is done except the yoghurts, on the trolley in the back' takes about:", ["A minute", "Four seconds", "Ten seconds", "A written note"], 1,
   "And converts an abandoned job into a handed-over one.", "Ch3 §5", "Handover"),
 Q("The commonest failure in receiving a handover is:", ["Forgetting it", "Not listening because you are already thinking about starting", "Not writing it down", "Asking too little"], 1,
   "You are being given free the information you would otherwise spend an hour discovering.", "Ch3 §6", "Handover"),
 Q("Every shop has jobs people avoid, and somebody who is always elsewhere for them is:", ["Rarely noticed", "Noticed within about a fortnight", "Managed by the rota", "Forgiven if pleasant"], 1,
   "No amount of being pleasant compensates.", "Ch4 §2", "Colleagues"),
 Q("Help offered before being asked should be:", ["Substantial", "Small, frequent and unremarked", "Recorded", "Reciprocal"], 1,
   "That is what builds the thing that means people help you when you need it.", "Ch4 §3", "Colleagues"),
 Q("Mentioning an imbalance in workload constantly:", ["Resolves it", "Makes it corrosive rather than merely present", "Is fair", "Prompts action"], 1,
   "A genuinely one-sided pattern over months is a supervisor conversation instead.", "Ch4 §4", "Colleagues"),
 Q("The position of neither defending nor joining criticism of a colleague is:", ["Cowardly", "Workable and costs nothing", "Impossible in a small team", "Seen as disloyal"], 1,
   "It always gets back, and the joiner is remembered as much as the starter.", "Ch4 §5", "Colleagues"),
 Q("Telling a new colleague the things that are not written down takes about:", ["An hour", "Ten minutes", "A shift", "A week"], 1,
   "And it is remembered for a year.", "Ch4 §6", "Colleagues"),
 Q("The first response to a colleague seemingly not pulling their weight is to:", ["Ask them", "Consider that you might be wrong", "Report it", "Do less yourself"], 1,
   "People who are struggling often look like people who are not trying.", "Ch5 §2", "Not pulling their weight"),
 Q("'Could you take the bins tonight, I did them the last two?' works because:", ["It is assertive", "A surprising share of imbalance is not deliberate", "It involves the supervisor", "It sets a precedent"], 1,
   "A light ask resets it without anybody losing face.", "Ch5 §3", "Not pulling their weight"),
 Q("After telling the supervisor once, you should:", ["Follow up weekly", "Genuinely let it go", "Escalate if nothing changes", "Tell colleagues"], 1,
   "Continuing to raise it makes you the problem in the conversation, however right you were.", "Ch5 §5", "Not pulling their weight"),
 Q("The most damaging response to a colleague doing less is:", ["Telling them", "Doing their work silently and resentfully for months", "Reporting it", "Ignoring it"], 1,
   "Along with discussing it with colleagues and matching their effort downward.", "Ch5 §6", "Not pulling their weight"),
 Q("Trying to fix another person's performance from beside them:", ["Usually works", "Is what makes people leave jobs they otherwise liked", "Is expected", "Is a supervisor's request"], 1,
   "Some situations do not get resolved and are tolerated for reasons nobody explains.", "Ch5 §7", "Not pulling their weight"),
 Q("A typical supervisor is described as:", ["Formally trained", "A former assistant promoted eighteen months ago, improvising", "An outside hire", "Experienced in management"], 1,
   "Which makes the useful behaviours toward them fairly obvious.", "Ch6 §2", "Your supervisor"),
 Q("What is worth more to a supervisor than enthusiasm is:", ["Speed", "Being reliable without being checked", "Product knowledge", "Availability"], 1,
   "Alongside bringing solutions and telling them things early.", "Ch6 §3", "Your supervisor"),
 Q("The reason a late request is often refused when an early one is not:", ["Favouritism", "Notice changes what is possible", "Policy thresholds", "The reason given"], 1,
   "Worth knowing before assuming a refusal was about you.", "Ch6 §4", "Your supervisor"),
 Q("Disagreeing quietly by doing it your own way is:", ["A reasonable compromise", "One of the three things not to do", "Better than arguing", "Acceptable if it works"], 1,
   "Say it once privately, then do it.", "Ch6 §5", "Your supervisor"),
 Q("A supervisor being wrong about safety or honesty should be:", ["Left until later", "Said plainly at the time, and taken further if unresolved", "Reported anonymously", "Handled by colleagues"], 1,
   "Everything else is a preference and can wait.", "Ch6 §6", "Your supervisor"),
 Q("Bullying is distinguished from ordinary sharpness by being:", ["Louder", "Persistent, targeted and humiliating", "Witnessed", "Recorded"], 1,
   "Rather than somebody having a bad day.", "Ch7 §2", "The line"),
 Q("The idea that a hard time is part of being new is described as:", ["Traditional", "Wrong", "Character-building", "Common"], 1,
   "Being new means you know less, not that you are owed less.", "Ch7 §3", "The line"),
 Q("The first step when something unacceptable happens is:", ["Report it", "Write it down as it happens", "Confront it", "Tell a colleague"], 1,
   "Memory is the first thing to go and the first thing questioned.", "Ch7 §4", "The line"),
 Q("If the supervisor is the problem, you go to:", ["A colleague", "Their manager", "The union", "Nobody"], 1,
   "Or whatever route the business provides.", "Ch7 §4", "The line"),
 Q("A business with genuinely nowhere to raise these things tells you something about:", ["Your position", "The business", "The industry", "Your supervisor"], 1,
   "Rather than about you.", "Ch7 §5", "The line"),
 Q("Being told to lift alone what needs two people is something you are entitled to:", ["Attempt carefully", "Decline, and say why", "Report afterwards", "Do once"], 1,
   "The pressure to get on with it is exactly what these situations are made of.", "Ch7 §7", "The line"),
 Q("On the short-staffed Saturday, three staff covered a day designed for:", ["Four", "Five", "Six", "Three"], 1,
   "In a shop taking a large share of its week's money that day.", "Ch8 §2", "The short Saturday"),
 Q("The supervisor named what was being dropped, which included:", ["The tills", "Facing, the stockroom and the promotional rebuild", "Chilled and bread", "The ends"], 1,
   "And named what was not being dropped as well.", "Ch8 §3", "The short Saturday"),
 Q("Ada's four minutes at close were spent:", ["Counting the drawer", "Writing the longest handover note she had left", "Checking the ends", "Reporting the absence"], 1,
   "Because Sunday's opener was walking into an unfilled stockroom and half a promotion.", "Ch8 §4", "The short Saturday"),
 Q("When both colleagues raised the absent staff member, Ada:", ["Agreed", "Did not join in", "Defended him", "Reported the conversation"], 1,
   "She did not know why, it was not her business, and the supervisor already knew.", "Ch8 §5", "The short Saturday"),
 Q("The absent colleague's outcome was:", ["Dismissal", "Nothing anybody was told about", "A formal warning", "A rota change"], 1,
   "Which was the correct outcome from where Ada was standing even though it was unsatisfying.", "Ch8 §6", "The short Saturday"),
 Q("The most valuable thing on a short-staffed day is:", ["Working faster", "Deciding out loud what is not being done", "Calling for help", "Prioritising customers"], 1,
   "Trying to do everything badly is worse than doing less on purpose.", "Ch8 §8", "The short Saturday"),
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

    rebalance(QUESTIONS, "shopfloor:the_shift:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "shopfloor:the_shift:checks")

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
        "title": "RF 6 — The Shift and the People On It",
        "desc": ("Doing the job alongside other people. What a shift owes the one after it, "
                 "why lateness is forgiven less than any other fault, the handover as the "
                 "team's real infrastructure, working next to people you did not choose, what "
                 "to do when somebody is not pulling their weight, your supervisor, and where "
                 "the line is between ordinary difficulty and what nobody should accept."),
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
