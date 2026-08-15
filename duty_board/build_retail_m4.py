#!/usr/bin/env python3
"""Build 'People' into academy_retail_data.json.

Module 4 of Retail Leadership Essentials, and the one module 1 named as the
slowest lever and the one that determines the other three.

The risk here is generic HR content. What keeps it specific: it is about a
retail shop floor in this market — hourly staff, thin margins over the pay
floor, transport that makes punctuality partly structural, family obligations
that arrive without notice, and a cash-handling job where suspicion lands on
everybody unless the records can attribute. None of that is in a general
management course and all of it is what a branch manager actually deals with.

Sango carries the worked example: the manager module 1 described as steady,
with the lowest turnover in the group, who is quietly the most valuable person
in the business.

STANDS ALONE. No other module or track assumed.

Run from the app package directory:  python3 build_retail_m4.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "people"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The lever that moves the others", 11, """<p>Availability, service, loss and cost are all delivered by people. A manager can design a perfect replenishment routine and it will not happen if the person who owns it has decided this job is temporary.</p>

<p><b>Which is why this is the slowest lever and the one worth the most.</b> A layout change works this week. A pricing change works immediately. A team takes months to build and it then delivers everything else for years — and when it goes, everything else goes with it quietly, one leaver at a time.</p>

<p><b>What turnover actually costs a branch</b>, because most managers have never added it up.</p>

<p>Recruiting takes your time and somebody else's. The first month is paid at full rate for perhaps half the output. Mistakes during learning cost real money — wrong prices, mis-scans, count errors, a till difference nobody can explain. The rest of the team covers the gap and gets tired. And each departure makes the next one more likely, because people who watch colleagues leave start wondering.</p>

<p><b>A rough figure is enough to change behaviour.</b> On a branch of fifteen paying ₦90,000 a month, one departure costs somewhere around two months of that person's pay by the time you count recruitment, the learning period and the cover — call it ₦180,000. Lose six in a year and it is over a million, before whatever the mistakes cost you.</p>

<p><b>The comparison that makes the point.</b> That is usually more than every controllable cost saving a branch manager is asked to find in the same year — and unlike those savings, it costs nothing to achieve. You are not spending to reduce turnover; you are stopping a leak.</p>

<p><b>What this module is not.</b> It is not about being liked, and it is not a set of motivational techniques. Retail staff in this market are mostly working for the money, at pay set above you, in a job many of them will leave within two years. Nothing in this module changes those facts. What it changes is the large part of why people leave that has nothing to do with pay, which is where a branch manager has almost all their influence.</p>

<p><b>And one thing to hold throughout.</b> The people on your floor are handling your stock and your cash all day, with less supervision than any other part of the business, for less money than anybody else in it. That is worth remembering before assuming anything about anyone.</p>

<blockquote>WATCH-OUT: Turnover is invisible as a cost because it never appears as a line on any report. It shows up as recruitment time, as mistakes, as a tired team and as availability slipping — all of which get attributed to something else.</blockquote>

<p><b>One number worth having before you go further.</b> How many people left your branch in the last twelve months, and how many are on the floor. Six departures from a team of fifteen is forty per cent turnover, which sounds abstract until you translate it: two in five of the people serving your customers today were not there a year ago, and will not be there next year. That is the condition every other module in this track has to work inside.</p>"""
, [
 C("One departure from a branch of fifteen paying ₦90,000 costs roughly:",
   ["₦90,000", "Around ₦180,000 once recruitment, learning and cover are counted",
    "₦45,000", "Nothing measurable"], 1,
   "Six in a year is over a million, before whatever the mistakes cost."),
 C("Reducing turnover differs from every other cost saving because you are:",
   ["Spending to save", "Not spending at all — you are stopping a leak",
    "Trading quality for cost", "Deferring a cost"], 1,
   "It usually exceeds every controllable saving a branch manager is asked to find in a year."),
 C("Turnover is invisible as a cost because it:",
   ["Is small", "Never appears as a line on any report",
    "Is head office's budget", "Varies too much"], 1,
   "It shows up as recruitment time, mistakes, a tired team and availability slipping — all attributed elsewhere.")]),

("Hiring: what you are actually selecting for", 11, """<p>Most branch hiring is done under pressure, from whoever is available, with a conversation lasting under fifteen minutes. It then determines a year of your life.</p>

<p><b>What you are actually selecting for, in order.</b></p>

<p><b>Reliability.</b> Will this person be here, on time, on the days they said. Everything else is irrelevant if the answer is no, and it is the hardest thing to assess in an interview because everybody says yes.</p>

<p><b>Temperament with customers.</b> Not charm — steadiness. Somebody who does not take a rude customer personally at four on a Saturday.</p>

<p><b>Honesty, as far as you can judge it.</b> Which is not far, and is why the systems and routines matter more than your instinct about a person.</p>

<p><b>Willingness to learn.</b> Retail changes constantly, and somebody who resents being shown a new way of doing something will resist every improvement you make for two years.</p>

<p><b>Experience comes fifth</b>, and often counts against you. Somebody who has worked three shops with bad habits takes longer to train than somebody with none, because you are removing before you are adding.</p>

<p><b>Questions that tell you something.</b> Not "are you reliable" but "tell me about the last time you were late for something that mattered — what happened?" Not "do you like working with people" but "tell me about the most difficult customer you have dealt with." Past behaviour, specifically described, is the only interview evidence worth anything, and a candidate who cannot produce an example usually does not have one.</p>

<p><b>The practical checks worth the time.</b> Two references actually telephoned, not read — people write things they will not say. Ask the previous employer one question: would you take them back? The pause before the answer tells you more than the answer.</p>

<p><b>The pressure to hire somebody's relative.</b> It is common, it is not automatically wrong, and it needs one rule: the same standard and the same process as anybody else. Where a person is hired around the process, everybody on the floor knows within a week, and you have taught your team that who you know matters more than how you work — which costs you more than any single hire is worth.</p>

<p><b>And be honest in the interview about the job.</b> The hours, the standing, the Saturdays, the customers. A person who takes the job knowing what it is stays. One who was sold something else leaves in six weeks, and you pay for that twice.</p>

<blockquote>IMPLEMENTATION TIP: Telephone both references and ask the one question — would you take them back. It takes ten minutes, almost nobody does it, and the hesitation before a polite answer has saved more bad hires than any interview technique.</blockquote>

<p><b>Hiring under pressure, which is when you will actually be doing it.</b> Somebody has left, the rota has a hole, and the temptation is to take whoever can start Monday. That decision is made in an hour and lived with for a year. Where you genuinely cannot wait, hire for the shortest commitment you can and be honest that it is a trial — a bad permanent hire made in haste costs far more than a month of cover, and it is much harder to undo.</p>"""
, [
 C("Prior retail experience in a candidate:",
   ["Is the strongest predictor", "Comes fifth, and can count against you",
    "Should be required", "Reduces training time reliably"], 1,
   "Three shops of bad habits takes longer to train than none, because you are removing before adding."),
 C("The interview question worth asking about reliability is:",
   ["Are you reliable?", "Tell me about the last time you were late for something that mattered",
    "Do you have transport?", "What are your hours?"], 1,
   "Past behaviour specifically described is the only interview evidence worth anything."),
 C("Hiring a relative around the normal process teaches your team that:",
   ["You value loyalty", "Who you know matters more than how you work",
    "Standards are flexible", "Referrals are welcome"], 1,
   "Everybody on the floor knows within a week, and it costs more than any single hire is worth.")]),

("The first two weeks", 11, """<p>Whether somebody stays a year is largely decided in their first fortnight, and most branches spend that fortnight showing them where things are.</p>

<p><b>What a new person is actually deciding.</b> Not whether they can do the work — they assume they can. Whether they are welcome, whether anybody noticed they arrived, whether the job is what they were told, and whether the person in charge is fair. Those four questions get answered in the first few days regardless of what anybody intends.</p>

<p><b>The cheapest things that work, and none costs money.</b></p>

<p><b>Be there on their first morning.</b> If the manager is absent on day one, the message is unmistakable and unintended.</p>

<p><b>Give them a name, not a rota slot.</b> One person responsible for them for two weeks, who they can ask the question they are embarrassed to ask you.</p>

<p><b>Tell them what good looks like on day one</b>, specifically. Not "we have high standards" — what the shelf should look like at four o'clock, what happens when a customer is rude, what to do when the till is short.</p>

<p><b>Give them something real within the first week.</b> Somebody who spends ten days watching concludes they are not needed, and they are half right.</p>

<p><b>Check in at the end of the first week, in private, and ask a question they can answer honestly.</b> Not "how is it going" — "what has been most confusing so far?" It costs five minutes and it surfaces the thing that would otherwise have made them leave in month two.</p>

<p><b>The particular risk in a cash-handling job.</b> A new person put on a till before they are ready will make a difference, and the way you handle that first difference sets everything. Treated as a learning moment with the process explained, they become careful. Treated as a suspicion, they become frightened — and a frightened cashier hides small problems, which is exactly the behaviour you least want.</p>

<p><b>The most common failure is not unkindness.</b> It is a busy branch where nobody has time, so the new person is parked with whoever is free, learns from three people with three methods, and concludes within a fortnight that the place is disorganised. That judgement is usually accurate, and it is entirely fixable at no cost.</p>

<blockquote>IMPLEMENTATION TIP: Write a one-page first-week plan and reuse it for every hire — who they shadow each day, what they are shown, what they should be able to do by Friday. It takes an hour once, it removes the parked-with-whoever-is-free problem permanently, and it makes the second week productive rather than remedial.</blockquote>

<p><b>What to tell the existing team before somebody starts.</b> Their name, when they start, what they will be doing, and who is looking after them. It takes thirty seconds and it prevents the version where a new person spends their first morning being asked who they are by people who did not know they were coming — which tells them, accurately, that the branch does not communicate.</p>"""
, [
 C("A new cashier's first till shortage is best treated as:",
   ["A suspicion to note", "A learning moment with the process explained",
    "A disciplinary matter", "A reason to move them off the till"], 1,
   "A frightened cashier hides small problems, which is exactly the behaviour you least want."),
 C("The most common induction failure is:",
   ["Unkindness", "A busy branch parking the new person with whoever is free",
    "Inadequate pay", "Poor scheduling"], 1,
   "They learn from three people with three methods and conclude the place is disorganised — usually accurately."),
 C("The end-of-first-week question worth asking is:",
   ["How is it going?", "What has been most confusing so far?",
    "Do you have any questions?", "Are you settling in?"], 1,
   "It costs five minutes and surfaces the thing that would otherwise have made them leave in month two.")]),

("Training that survives a Saturday", 11, """<p>Retail training mostly happens by watching somebody who is busy, and the result is a team where everybody does the same task differently and nobody knows which way is right.</p>

<p><b>Why the standard method fails.</b> Showing somebody once, while serving, transfers about a third of what was intended. The person then practises their approximation until it is a habit, and correcting a habit costs several times what teaching it properly would have.</p>

<p><b>What works on a shop floor, given nobody has an hour.</b></p>

<p><b>Short and repeated beats long and once.</b> Ten minutes on one thing, done properly, then used that day. A two-hour session at the end of a shift teaches almost nothing, because the audience is tired and will not use any of it until next week.</p>

<p><b>Show, then watch them do it, then leave.</b> The middle step is the one that gets skipped and the only one that reveals whether it landed. Somebody who nods is not somebody who understood.</p>

<p><b>Explain why, not only how.</b> A person told to rotate stock does it when watched. A person told that last month's expiry write-off cost the branch ₦40,000 does it when nobody is looking, which is the only version that matters.</p>

<p><b>One method, written down.</b> Where three people do something three ways, none of them is wrong exactly, and a new starter learns whichever they happened to see. Decide the way, show everybody the way, and correct departures early and lightly.</p>

<p><b>Who trains matters more than what.</b> The person you assign teaches their own habits along with the task. Assigning your fastest worker is not the same as assigning your most careful one, and a new starter shadowing somebody who cuts corners has been taught to cut corners with your authority behind it.</p>

<p><b>Train for the things that go wrong, not only the things that go right.</b> Most training covers the normal transaction. Almost none covers the rude customer, the card that fails, the price that is wrong on the shelf, the colleague who does not turn up. Those are the moments where a branch's reputation is made, and they are the ones staff are least prepared for.</p>

<blockquote>WATCH-OUT: The staff member everybody asks is your real training system, whatever the process says. Find out who it is — it is often not who you would expect — and make sure what they are teaching is what you want taught, because they are teaching it either way.</blockquote>

<p><b>And train the people who have been there longest, too.</b> Training is usually aimed entirely at new starters, so somebody four years in has never been shown anything since their first week and is running on habits formed then — some of which are now wrong. Ten minutes with an experienced person on something that has changed is often the highest-value training in the branch, and it is almost never done because they are assumed to know.</p>"""
, [
 C("Showing somebody a task once while serving transfers about:",
   ["Everything, if they pay attention", "A third of what was intended",
    "Half, on average", "Enough for most tasks"], 1,
   "They then practise their approximation until it is a habit, and correcting a habit costs several times more."),
 C("Telling a person why a task matters rather than only how produces:",
   ["Better understanding of the system", "The version that happens when nobody is looking",
    "Faster training", "Fewer questions"], 1,
   "A person told last month's expiry write-off cost ₦40,000 rotates stock unwatched."),
 C("Assigning your fastest worker to train a new starter risks:",
   ["Overwhelming them", "Teaching your corner-cutting with your authority behind it",
    "Slowing the floor", "Confusing the standard"], 1,
   "The person you assign teaches their own habits along with the task.")]),

("The rota as an instrument", 11, """<p>The rota is the thing a branch manager touches most often and thinks about least. It is simultaneously your largest controllable cost, your service level, and the single biggest factor in whether your team stays.</p>

<p><b>What it does to cost and service at once.</b> Staffing to trade rather than to habit is the rare change that improves both — most branches are overstaffed in the morning and short in the hours that actually convert. Comparing your hourly staffing to your hourly sales for one week usually shows it plainly, and fixing it costs nothing.</p>

<p><b>What it does to people, which is the part managers underestimate.</b> A person's life is built around their rota — childcare, a second job, a college class, a two-hour commute. A rota published late, or changed at short notice, does not merely inconvenience them; it makes the job incompatible with the rest of their life. That, far more often than pay, is why hourly retail staff leave.</p>

<p><b>Three things worth more than they cost.</b></p>

<p><b>Publish it early and to a fixed rhythm.</b> Same day each week, as far ahead as you can manage. Predictability is worth more to most staff than any single favourable shift.</p>

<p><b>Change it as little as possible, and never silently.</b> If you must change somebody's shift, tell them personally rather than letting them discover it.</p>

<p><b>Be visibly fair about the shifts nobody wants.</b> Saturdays, evenings, closing. Rotate them and be seen to rotate them. A team that believes the unpopular shifts are distributed by favour will accept it and resent it, and the resentment surfaces somewhere else entirely.</p>

<p><b>The transport reality.</b> In this market punctuality is partly structural — traffic, a bus that does not come, a route that floods. A manager who treats every lateness identically is being fair in form and unfair in substance. The useful distinction is between a person who is occasionally caught by something real and a person for whom it is always something, and you can only tell the difference by keeping track.</p>

<p><b>And the rota tells your team what you think of them.</b> Somebody given the worst shifts every week has been sent a message whether or not one was intended, and they will read it accurately. It is worth looking at your own rota over a month and asking who has quietly come off worst.</p>

<blockquote>IMPLEMENTATION TIP: Publish the rota the same day every week, at least a week out, and hold to it. It is free, it takes discipline rather than effort, and in most branches it does more for retention than anything else within a manager's gift.</blockquote>

<p><b>Where somebody asks for a change you cannot make.</b> Say so plainly and quickly rather than leaving it open. A person told no on Tuesday can make other arrangements; a person left hoping for three weeks cannot, and will resent both the answer and the delay. The refusal is rarely what damages a relationship — the silence is.</p>"""
, [
 C("A rota published late or changed at short notice principally causes staff to leave because it:",
   ["Reduces their hours", "Makes the job incompatible with the rest of their life",
    "Feels disrespectful", "Creates uncertainty about pay"], 1,
   "Childcare, a second job, a class, a two-hour commute — and it matters more than pay far more often."),
 C("Staffing to trade rather than to habit is unusual among changes because it:",
   ["Requires no approval", "Improves both cost and service at once",
    "Is quick to implement", "Needs no data"], 1,
   "Most branches are overstaffed in the morning and short in the hours that convert."),
 C("Treating every lateness identically, in a market where transport is unreliable, is:",
   ["Fair and consistent", "Fair in form and unfair in substance",
    "The only defensible approach", "Required for discipline"], 1,
   "The useful distinction is between somebody occasionally caught by something real and somebody for whom it is always something.")]),

("The conversation nobody wants to have", 11, """<p>Every branch manager has at least one conversation they have been postponing. The postponement is the problem, not the conversation — and the cost compounds while it is deferred.</p>

<p><b>What delay actually costs.</b> The behaviour continues, so the branch keeps paying for it. Everybody else sees it unaddressed and adjusts their own standard accordingly, which is the larger cost. And the eventual conversation becomes far harder, because the person can reasonably ask why this has been acceptable for four months.</p>

<p><b>That last point is worth sitting with.</b> A standard you tolerate for a quarter has become the standard, and correcting it later feels arbitrary to the person on the receiving end — because from where they sit, it is.</p>

<p><b>The shape that works, and it takes about four minutes.</b></p>

<p><b>Private, promptly, and specific.</b> Not "your attitude" — "on Tuesday you left the till without locking it, twice."</p>

<p><b>Say what the standard is</b>, plainly, so there is no ambiguity about what you are asking for.</p>

<p><b>Ask what is going on.</b> Genuinely, and then be quiet. A surprising proportion of persistent problems have a cause the person would tell you if asked — a sick parent, a second job, a colleague making their shift difficult — and some of those you can actually solve.</p>

<p><b>Agree what changes and by when.</b> Specific enough that both of you will know next week whether it happened.</p>

<p><b>Then follow up.</b> This is the step that is skipped and it is the one that decides whether the conversation mattered. A concern raised and never mentioned again teaches the person it was not serious.</p>

<p><b>What to avoid.</b> Doing it on the floor where others can hear, which humiliates and produces defensiveness rather than change. Saving up six things for one conversation, which overwhelms and lets the person dispute the weakest item and dismiss the rest. And softening it so far that the person leaves genuinely unaware there was a problem, which happens more often than managers believe.</p>

<p><b>The one that must not wait.</b> Anything involving money or safety. A till difference, a missing item, a fire door propped open — these are addressed the same day, calmly and without accusation, because the record needs to show it was addressed and because waiting turns a small matter into an investigation.</p>

<blockquote>WATCH-OUT: The test for whether you have been clear is whether the person could repeat back what you are asking for. Managers frequently soften a message until it disappears, then are surprised a month later that nothing changed — and from the other side, nothing was ever asked.</blockquote>

<p><b>The conversation that is not a reprimand, and is rarer.</b> Telling somebody specifically what they did well, promptly, in front of others where appropriate. Most managers do this in generalities at team briefings, which carries almost nothing. “The way you handled that customer at the till this morning — you let her finish before answering, and it defused it” is worth more than a month of “well done everyone”, and it costs the same fifteen seconds.</p>"""
, [
 C("You have been putting off a conversation about a cashier's lateness for four months. The biggest cost so far is:",
   ["Four months of lateness", "Everybody else watching it go unaddressed and adjusting their own standard",
    "Your own frustration", "How hard the conversation now is"], 1,
   "A standard tolerated for a quarter has become the standard."),
 C("Saving up six issues for one conversation:",
   ["Is efficient", "Lets the person dispute the weakest item and dismiss the rest",
    "Shows a pattern", "Is fairer"], 1,
   "It overwhelms, and the weakest item becomes the whole conversation."),
 C("The test of whether you were clear is whether the person:",
   ["Agreed", "Could repeat back what you are asking for",
    "Apologised", "Seemed to understand"], 1,
   "Managers soften a message until it disappears, then are surprised nothing changed.")]),

("Why people leave", 11, """<p>Ask a departing retail worker why they are going and most will say money, because it is the answer that ends the conversation politely. Ask them six months later and the answer is usually different.</p>

<p><b>What actually drives hourly retail turnover, roughly in order.</b></p>

<p><b>The immediate manager.</b> Being treated unfairly, spoken to badly in front of others, or never noticed at all. This is consistently the largest single factor and it is entirely within your control.</p>

<p><b>The rota.</b> Unpredictable, late, or visibly unfair. Covered in its own chapter because it is that important.</p>

<p><b>Being treated as disposable.</b> No training, no explanation, no interest in whether they stay. People leave places where they believe nobody would notice.</p>

<p><b>A colleague.</b> One difficult person can drive out three good ones while remaining perfectly acceptable to the manager, because the behaviour happens where you are not.</p>

<p><b>Then pay</b>, which matters enormously and which you mostly cannot change — and which is precisely why the four above deserve your attention.</p>

<p><b>The signals that precede a departure by weeks.</b> Someone who has stopped offering to cover. Someone who was chatty and has gone quiet. Punctuality slipping in a person who was reliable. Annual leave taken in single days rather than a block, which frequently means interviews. None of these is proof, and all of them are worth a private word.</p>

<p><b>The conversation to have while they still work for you.</b> "How is this going for you?", asked in private, twice a year, and then listened to. It is the cheapest retention tool available and most managers only ask on the way out, when the answer is designed to avoid a difficult exit.</p>

<p><b>And the exit conversation, done properly.</b> Ask what would have made them stay, accept the answer without defending, and write it down. Three leavers giving the same answer is data — and it is usually about something you could have fixed for nothing.</p>

<p><b>The uncomfortable one.</b> Sometimes the honest answer is you. A manager who never hears that is not a manager nobody has a problem with; they are one nobody will tell. Which is why the twice-yearly private question matters more than any exit interview.</p>

<p><b>The leaver worth trying to keep, and the one worth letting go.</b> Not everybody should be retained. A person who has become a drag on the team is a departure to accept gracefully, and managers sometimes spend more effort keeping a difficult member than they ever spent on their best. Be clear with yourself about which category somebody is in before the conversation begins, because that judgement is much harder to make once a counter-offer is on the table.</p>

<blockquote>IMPLEMENTATION TIP: Ask every leaver one question — what would have made you stay? Write down the answers and read them all together after a year. The pattern is usually clear, usually cheap to fix, and usually not what you expected.</blockquote>"""
, [
 C("The largest single driver of hourly retail turnover is:",
   ["Pay", "The immediate manager", "Hours", "The commute"], 1,
   "Being treated unfairly, spoken to badly in front of others, or never noticed at all."),
 C("A reliable person taking annual leave in single days rather than a block frequently means:",
   ["Family obligations", "Interviews", "Illness", "A second job"], 1,
   "It is not proof, and it is worth a private word."),
 C("A manager who has never been told they are part of the problem is:",
   ["Doing well", "One nobody will tell",
    "Unusually fair", "Well insulated"], 1,
   "Which is why a twice-yearly private question matters more than any exit interview.")]),

("Okelewo: what Sango does", 11, """<p>Sango is the second Abeokuta branch. Its manager is regarded at head office as steady rather than strong — unremarkable sales, no dramas, nothing to report. He has the lowest staff turnover in a group of eleven branches and is quietly the most valuable manager in the business.</p>

<p><b>What he actually does, which took somebody a week to notice.</b></p>

<p><b>The rota goes up on Wednesday for the following week, every week, without exception.</b> It has done for three years. When he changes somebody's shift he tells them himself. Staff at Sango can plan their lives, and two of them have turned down better-paid work elsewhere for that reason alone.</p>

<p><b>Every new starter gets the same first week</b>, from a page he wrote once. One named person, the same things shown in the same order, and a private conversation on Friday.</p>

<p><b>He does the unpopular shifts himself, in rotation.</b> Not all of them, and visibly some of them. Nobody at Sango believes the closing rota is decided by favour, because they can see him on it.</p>

<p><b>He has difficult conversations within a day and they last four minutes.</b> His team describe him as fair rather than nice, and one of them said he is the only manager they have had who tells you straight away.</p>

<p><b>What it produces.</b> Two departures a year against a group average of six. His branch trains people the other branches later take — three current supervisors elsewhere in the group came from Sango, which the business had never counted as an output.</p>

<p><b>Why head office had missed it.</b> They were reading sales, and his are ordinary. Nothing about a branch that simply works generates a report. The absence of problems is invisible in exactly the way the absence of a lost sale is, and it is why steady managers are consistently undervalued in retail.</p>

<p><b>What is worth taking from it.</b> Nothing he does is clever, expensive, or difficult to copy. A rota on time, a first week that is the same every time, unpopular shifts shared visibly, and conversations held promptly. Four habits, none costing money, producing roughly ₦700,000 a year of avoided turnover cost at that branch alone — before counting what his branch's stability does for its availability and its losses.</p>

<blockquote>IMPLEMENTATION TIP: Pick the one of Sango's four you are furthest from and do only that for a quarter. For most managers it is the rota, it is the cheapest, and it produces a visible change in how a team behaves within about six weeks.</blockquote>

<p><b>Why nobody had copied him.</b> Because nothing he does looks like management. There is no initiative, no programme, no announcement — a rota goes up on a Wednesday and a new person gets the same first week. Practices that are invisible do not spread on their own, which is an argument for a business asking its steady branches what they do rather than only asking its struggling ones what is wrong.</p>"""
, [
 C("Head office had missed what Sango's manager was doing because:",
   ["He does not report it", "They were reading sales, and nothing about a branch that works generates a report",
    "He is not ambitious", "His branch is small"], 1,
   "The absence of problems is invisible, which is why steady managers are undervalued in retail."),
 C("Two of Sango's staff turned down better-paid work elsewhere because:",
   ["The branch is closer", "They can plan their lives around a rota published on time every week",
    "They were promised promotion", "The team is friendly"], 1,
   "Predictability is worth more to most hourly staff than a single favourable shift."),
 C("Sango's team describe their manager as:",
   ["Nice", "Fair rather than nice",
    "Demanding", "Easy-going"], 1,
   "One of them said he is the only manager they have had who tells you straight away.")]),

("The people routine", 11, """<p>This is the chapter to keep. None of it takes long; all of it is the kind of thing that gets postponed indefinitely unless it has a day attached.</p>

<p><b>Weekly.</b> Publish the rota, same day, at least a week ahead. Look at who has the unpopular shifts this week and over the month. And notice who you have not spoken to properly — in a branch of fifteen there is usually somebody you have not had a real conversation with in a fortnight, and it is rarely the loudest person.</p>

<p><b>Whenever it arises.</b> The difficult conversation, within a day. Private, specific, four minutes, with a follow-up date. Anything involving money or safety the same day, calmly.</p>

<p><b>Every new starter.</b> The same first week from the same page. A named person for a fortnight. The Friday conversation asking what has been most confusing.</p>

<p><b>Twice a year, per person.</b> Ten minutes in private: how is this going for you, what would make it better, and what do you want to be doing in a year. Then listen without defending. In a branch of fifteen that is five hours a year, and it is the highest-return five hours available to you.</p>

<p><b>Every leaver.</b> What would have made you stay. Written down and read together annually.</p>

<p><b>And the check on yourself, quarterly.</b> Who has left, who is showing the signals, and who on the team you would be genuinely sorry to lose — and whether that last person knows it. Most managers have never told their best staff that they are their best staff, on the reasonable but wrong assumption that it is obvious.</p>

<p><b>What this adds up to.</b> Perhaps two hours a month, none of it urgent, all of it easy to skip. Against a turnover cost that is usually the largest recoverable number in a branch after availability, and that no report will ever show you.</p>

<p><b>The one to start with if you start with one.</b> The rota, published to a fixed day and held to. It is free, it is entirely within your control, it requires discipline rather than skill, and in most branches it changes how a team behaves within six weeks.</p>

<blockquote>IMPLEMENTATION TIP: Put the twice-yearly ten-minute conversations in the calendar for the whole team now, spread across the year, rather than intending to do them. Scheduled they mostly happen; intended they almost never do.</blockquote>

<p><b>A closing word on what this module is asking of you.</b> Nothing in it requires you to be a natural with people, and several of the habits work better if you are not — a manager who finds the difficult conversation uncomfortable and has it anyway, briefly and specifically, is more effective than one who is comfortable and rambles. What the module asks for is regularity: the same rota day, the same first week, the same two conversations a year. Consistency is available to everybody, and in this part of the job it beats talent.</p>"""
, [
 C("The twice-yearly private conversation is described as the highest-return five hours because it:",
   ["Satisfies HR", "Surfaces what would otherwise become a resignation",
    "Improves productivity", "Sets objectives"], 1,
   "Ten minutes per person across a branch of fifteen, listened to without defending."),
 C("Most managers have never told their best staff they are their best staff because:",
   ["It causes complacency", "They assume it is obvious",
    "It invites pay demands", "It is unprofessional"], 1,
   "The assumption is reasonable and wrong, and the person often does not know."),
 C("If you start with only one habit from this module it should be:",
   ["The exit question", "The rota, published to a fixed day and held to",
    "The first-week plan", "The twice-yearly conversation"], 1,
   "Free, entirely within your control, requiring discipline rather than skill, and visible within six weeks.")]),
]


QUESTIONS = [
 Q("People is described as the slowest lever because a team:", ["Resists change", "Takes months to build and then delivers everything else for years", "Is expensive", "Turns over constantly"], 1,
   "And when it goes, everything else goes with it quietly, one leaver at a time.", "Ch1 §2", "Why people matter"),
 Q("One departure at ₦90,000 a month costs roughly:", ["₦90,000", "₦180,000", "₦45,000", "₦360,000"], 1,
   "Recruitment, the learning period and the cover.", "Ch1 §5", "Why people matter"),
 Q("Reducing turnover is unusual as a saving because you are:", ["Investing for return", "Stopping a leak rather than spending", "Trading cost for quality", "Deferring expense"], 1,
   "It usually exceeds every controllable saving a branch manager is asked to find.", "Ch1 §6", "Why people matter"),
 Q("Turnover is invisible as a cost because it shows up as:", ["A payroll line", "Recruitment time, mistakes, a tired team and availability slipping", "Overtime", "Training spend"], 1,
   "All of which get attributed to something else.", "Ch1 §9", "Why people matter"),
 Q("The first thing you are selecting for when hiring is:", ["Experience", "Reliability", "Charm", "Product knowledge"], 1,
   "Everything else is irrelevant if the person is not there on the days they said.", "Ch2 §3", "Hiring"),
 Q("Prior experience in three shops with bad habits means training takes:", ["Less time", "Longer, because you are removing before adding", "The same time", "No time"], 1,
   "Experience comes fifth and can count against you.", "Ch2 §7", "Hiring"),
 Q("The reference question worth asking is:", ["Was their work satisfactory?", "Would you take them back?", "Why did they leave?", "How long were they with you?"], 1,
   "The pause before the answer tells you more than the answer.", "Ch2 §9", "Hiring"),
 Q("Being honest in interview about the hours and Saturdays matters because a person sold something else:", ["Complains", "Leaves in six weeks, and you pay for that twice", "Works badly", "Renegotiates"], 1,
   "A person who takes the job knowing what it is stays.", "Ch2 §11", "Hiring"),
 Q("Whether somebody stays a year is largely decided in:", ["The first month's pay", "Their first fortnight", "The first appraisal", "The probation period"], 1,
   "And most branches spend that fortnight showing them where things are.", "Ch3 §1", "The first two weeks"),
 Q("A new person spending ten days watching concludes:", ["The job is easy", "They are not needed, and they are half right", "Training is thorough", "The branch is busy"], 1,
   "Give them something real within the first week.", "Ch3 §6", "The first two weeks"),
 Q("A new cashier's first till difference handled as a suspicion produces:", ["Care", "A frightened cashier who hides small problems", "Improved accuracy", "A resignation"], 1,
   "Exactly the behaviour you least want.", "Ch3 §8", "The first two weeks"),
 Q("The commonest induction failure is a busy branch:", ["Overloading the new starter", "Parking them with whoever is free", "Underpaying them", "Rushing training"], 1,
   "Three people with three methods, and a conclusion that the place is disorganised.", "Ch3 §9", "The first two weeks"),
 Q("Showing a task once while serving transfers about:", ["All of it", "A third", "Half", "Most of it"], 1,
   "The person then practises their approximation until it is a habit.", "Ch4 §2", "Training"),
 Q("Which step in show-watch-leave is most often skipped?", ["Show", "Watching them do it", "Leaving them to it", "Following up"], 1,
   "It is the only step that reveals whether it landed. Somebody who nods is not somebody who understood.", "Ch4 §4", "Training"),
 Q("Explaining why a task matters produces:", ["Faster learning", "The version that happens when nobody is looking", "Fewer questions", "Better morale"], 1,
   "Which is the only version that matters.", "Ch4 §5", "Training"),
 Q("Where three people do a task three ways:", ["Choose the fastest", "Decide one method, write it down, and correct departures early", "Let each keep their own", "Retrain everybody"], 1,
   "A new starter otherwise learns whichever they happened to see.", "Ch4 §6", "Training"),
 Q("Most retail training covers the normal transaction and omits:", ["Product knowledge", "The rude customer, the failed card, the wrong shelf price", "Cash handling", "Health and safety"], 1,
   "Those are the moments where a branch's reputation is made.", "Ch4 §8", "Training"),
 Q("Staffing to trade rather than habit is unusual because it improves:", ["Cost only", "Cost and service at once", "Service only", "Neither reliably"], 1,
   "Most branches are overstaffed in the morning and short when trade converts.", "Ch5 §2", "The rota"),
 Q("A rota published late causes departures mainly because it:", ["Reduces hours", "Makes the job incompatible with the rest of a person's life", "Suggests disorganisation", "Affects pay"], 1,
   "Childcare, a second job, a class, a long commute.", "Ch5 §3", "The rota"),
 Q("Predictability in a rota is worth more to most staff than:", ["Higher pay", "Any single favourable shift", "Shorter hours", "A better location"], 1,
   "Same day each week, as far ahead as you can manage.", "Ch5 §5", "The rota"),
 Q("Unpopular shifts should be rotated and:", ["Compensated", "Seen to be rotated", "Volunteered for", "Assigned by seniority"], 1,
   "A team believing they are distributed by favour will accept it and resent it.", "Ch5 §7", "The rota"),
 Q("Treating every lateness identically where transport is unreliable is:", ["Consistent and fair", "Fair in form and unfair in substance", "Legally required", "The only workable rule"], 1,
   "Distinguish somebody occasionally caught by something real from somebody for whom it is always something.", "Ch5 §8", "The rota"),
 Q("The largest cost of postponing a difficult conversation is:", ["The behaviour continuing", "Everybody else adjusting their standard", "Manager stress", "The eventual difficulty"], 1,
   "A standard tolerated for a quarter has become the standard.", "Ch6 §2", "Difficult conversations"),
 Q("After asking what is going on, the manager should:", ["Offer a solution", "Be quiet", "Restate the standard", "Set a deadline"], 1,
   "A surprising proportion of persistent problems have a cause the person would tell you if asked.", "Ch6 §6", "Difficult conversations"),
 Q("The step most often skipped, which decides whether the conversation mattered, is:", ["Being specific", "Following up", "Privacy", "Agreeing the standard"], 1,
   "A concern raised and never mentioned again teaches the person it was not serious.", "Ch6 §8", "Difficult conversations"),
 Q("Which must be addressed the same day?", ["Persistent lateness", "Anything involving money or safety", "Poor service", "Uniform standards"], 1,
   "Calmly and without accusation — waiting turns a small matter into an investigation.", "Ch6 §10", "Difficult conversations"),
 Q("Doing a difficult conversation on the floor where others can hear produces:", ["A clear message", "Defensiveness rather than change", "Faster resolution", "Team learning"], 1,
   "It humiliates, and humiliation does not produce a change in behaviour.", "Ch6 §9", "Difficult conversations"),
 Q("Departing staff say money because:", ["It is usually true", "It ends the conversation politely", "It is easiest to measure", "They expect a counter-offer"], 1,
   "Asked six months later the answer is usually different.", "Ch7 §1", "Why people leave"),
 Q("One difficult colleague can drive out three good ones while:", ["Being disciplined", "Remaining perfectly acceptable to the manager", "Underperforming visibly", "Complaining constantly"], 1,
   "The behaviour happens where you are not.", "Ch7 §6", "Why people leave"),
 Q("Which precedes a departure by weeks?", ["A pay request", "Someone who has stopped offering to cover", "A complaint", "A transfer request"], 1,
   "Along with a chatty person going quiet and reliable punctuality slipping.", "Ch7 §8", "Why people leave"),
 Q("The exit question worth asking is:", ["Why are you leaving?", "What would have made you stay?", "Where are you going?", "Would you return?"], 1,
   "Three leavers giving the same answer is data, usually about something cheap to fix.", "Ch7 §10", "Why people leave"),
 Q("Sango's manager was undervalued by head office because they were reading:", ["Costs", "Sales", "Turnover", "Complaints"], 1,
   "Nothing about a branch that simply works generates a report.", "Ch8 §7", "Okelewo Sango"),
 Q("Sango's turnover against the group average was:", ["Six against six", "Two against six", "Four against six", "Two against four"], 1,
   "And three current supervisors elsewhere in the group came from that branch.", "Ch8 §6", "Okelewo Sango"),
 Q("Sango's manager does the unpopular shifts:", ["All of them", "Some of them, visibly, in rotation", "None, by seniority", "Only at Christmas"], 1,
   "Nobody there believes the closing rota is decided by favour, because they can see him on it.", "Ch8 §5", "Okelewo Sango"),
 Q("The four habits at Sango produce roughly what in avoided turnover cost annually?", ["₦180,000", "₦700,000", "₦2m", "₦70,000"], 1,
   "Before counting what stability does for that branch's availability and losses.", "Ch8 §8", "Okelewo Sango"),
 Q("What is notable about Sango's four habits is that they are:", ["Difficult to sustain", "Not clever, expensive or hard to copy", "Specific to that branch", "Dependent on his experience"], 1,
   "A rota on time, a consistent first week, shared unpopular shifts, prompt conversations.", "Ch8 §8", "Okelewo Sango"),
 Q("The twice-yearly private conversation should ask how it is going, what would make it better, and:", ["What they earn elsewhere", "What they want to be doing in a year", "Whether they are happy", "How the team is"], 1,
   "Then listen without defending.", "Ch9 §5", "The routine"),
 Q("In a branch of fifteen, the twice-yearly conversations amount to:", ["Two hours a year", "Five hours a year", "A day a month", "Twenty hours a year"], 1,
   "And they are the highest-return five hours available.", "Ch9 §5", "The routine"),
 Q("The weekly people check includes the rota, the unpopular shifts, and noticing:", ["Who is late", "Who you have not spoken to properly", "Who is busiest", "Who wants overtime"], 1,
   "It is rarely the loudest person.", "Ch9 §2", "The routine"),
 Q("Scheduled conversations mostly happen and intended ones:", ["Happen later", "Almost never do", "Happen when needed", "Are replaced by meetings"], 1,
   "Which is why they go in the calendar for the whole team now.", "Ch9 §9", "The routine"),
 Q("The people routine amounts to roughly:", ["Two hours a month", "A day a week", "Two hours a week", "An hour a quarter"], 1,
   "None of it urgent, all of it easy to skip, against the largest recoverable number after availability.", "Ch9 §7", "The routine"),
 Q("The habit to start with is:", ["The exit question", "The rota published to a fixed day", "The first-week page", "The quarterly self-check"], 1,
   "Free, within your control, discipline rather than skill, visible within six weeks.", "Ch9 §8", "The routine"),
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
    rebalance(QUESTIONS, "retail:people:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:people:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 4 — People",
        "desc": ("The slowest lever and the one that determines the others. What turnover "
                 "actually costs, what you are selecting for when you hire, the first two "
                 "weeks that decide whether somebody stays a year, training that survives a "
                 "Saturday, the rota as your largest instrument, the conversation nobody "
                 "wants to have, and why people really leave."),
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
