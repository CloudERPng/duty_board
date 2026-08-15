#!/usr/bin/env python3
"""Build 'The Branch Without You' into academy_retail_data.json.

Module 8 of Retail Leadership Essentials.

Module 1 argued that a branch which cannot run two hours without its manager is
not a compliment but a description of something unbuilt. This module is the
building: a deputy who can actually decide, standards that survive absence,
handling a crisis, leading a team through change, and handing a branch over.

The crisis chapter is written for this market and its first rule is that people
come before stock and before cash. That is stated plainly rather than implied,
because staff need to have heard it from their manager before the day it
matters, and because a branch manager who has never said it out loud may find
their team taking risks to protect goods that are insured.

STANDS ALONE. No other module or track assumed.

Run from the app package directory:  python3 build_retail_m8.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "without_you"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("The two-week test", 11, """<p>There is a single question that measures how well a branch is built: if you were away for two weeks with no contact, what would be different when you came back?</p>

<p><b>The honest answers, and most managers give one of the first two.</b> Everything would fall apart. Some things would slip and it would take a fortnight to recover. Or the branch would run, a few decisions would wait for you, and the rest would be as you left it.</p>

<p>Only the third describes a branch that has been built rather than operated.</p>

<p><b>Why this is not a vanity measure.</b> You will be away. Illness, leave, training, a family matter, a day you cannot get across the city. A branch that only works when you are in it is not a branch performing well — it is a branch performing well on the days you are there, which is a different and much smaller thing.</p>

<p><b>And it costs you personally.</b> A manager who cannot be absent cannot be promoted, because the business cannot afford to move them. That is a genuinely common trap: the most indispensable manager in a chain is frequently the one who has been in the same branch for six years.</p>

<p><b>What actually makes a branch run without you.</b> Three things, and none of them is about your team trying harder.</p>

<p><b>Somebody who can decide.</b> Not somebody who can do the tasks — somebody with the authority and the judgement to make the calls that arise, and who has been allowed to make them while you were present.</p>

<p><b>Standards that exist outside your head.</b> If what good looks like is known only to you, it degrades the moment you are not there to correct it. Written down, it survives.</p>

<p><b>Routines with names and times attached.</b> The habits from earlier in this track — the afternoon fill, the count, the rota day — do not depend on you if they belong to somebody specific on a specific day.</p>

<p><b>The test to run rather than imagine.</b> Take a day off and do not answer the telephone. Then find out what happened, without blame. Whatever went wrong is your list, and it is a much cheaper way to discover it than being genuinely unavailable in a week that matters.</p>

<blockquote>WATCH-OUT: Being needed constantly feels like being valuable and is usually evidence of something not yet built. The manager whose phone rings all day on their day off is not being conscientious — they are looking at the result of decisions they never delegated.</blockquote>

<p><b>And the version of this that catches good managers.</b> A branch can look resilient because the manager works six days and answers the phone on the seventh, so nothing ever visibly fails. That is not resilience — it is a manager absorbing the fragility personally, and it is invisible from outside precisely because it works. The test is not whether things go wrong; it is what happens when you genuinely are not reachable.</p>"""
, [
 C("A manager who cannot be absent for two weeks:",
   ["Is highly valuable", "Cannot be promoted, because the business cannot afford to move them",
    "Should reduce their workload", "Needs more staff"], 1,
   "The most indispensable manager in a chain is frequently the one who has been in the same branch for six years."),
 C("The cheapest way to find out what would fail in your absence is to:",
   ["Ask your deputy", "Take a day off and not answer the telephone",
    "Review the routines", "Write a handover note"], 1,
   "Whatever went wrong is your list, and finding it deliberately beats discovering it in a week that matters."),
 C("If what good looks like exists only in your head, it:",
   ["Is applied consistently", "Degrades the moment you are not there to correct it",
    "Transfers by example", "Is learned by the team"], 1,
   "A standard held only in your head is corrected only when you are present to correct it, so it degrades every day you are not there.")]),

("Building a deputy who can actually decide", 11, """<p>Most branches have a second-in-command who can run the shop and cannot make a decision. That is not a deputy; it is a senior member of staff with a title, and it is the commonest gap in retail management.</p>

<p><b>The difference, stated precisely.</b> Somebody who can do everything you do while following your instructions is covering. Somebody who can decide what should happen when a situation arises that nobody anticipated is deputising. Only the second is any use in a real absence, because real absences are full of unanticipated situations.</p>

<p><b>Why most deputies never develop.</b> They are never allowed to decide while you are present, so they learn to bring things to you — and the arrangement works perfectly until you are not there. On the day it matters they have had no practice, and they either freeze or guess.</p>

<p><b>How to build one, and it takes about six months.</b></p>

<p><b>Give away real decisions while you are there.</b> The rota, an ordering category, a supplier conversation, the handling of a specific complaint. Real ones, with real consequences, chosen so that a poor decision is recoverable.</p>

<p><b>Let them make it badly.</b> This is the part managers cannot do. If you overrule the first three decisions, you have taught them that the delegation was decorative. Where the decision is defensible and not what you would have done, live with it — that is the whole exercise.</p>

<p><b>Ask before you tell.</b> When they bring you a problem, ask what they think should happen before offering a view. Most of the time their answer is adequate, and answering their own question repeatedly is what builds judgement.</p>

<p><b>Explain your reasoning, not just your conclusion.</b> A deputy who knows what you decided can repeat it. One who knows why you decided it can handle the case you never discussed.</p>

<p><b>Tell them what they can decide without you, in specifics.</b> Amounts, situations, limits. A deputy uncertain of their authority defaults to doing nothing, which in your absence is exactly the failure mode you were trying to prevent.</p>

<p><b>And tell the team.</b> Authority that the rest of the branch does not know about is not authority — staff will simply wait for you. Saying plainly that this person decides in your absence, in front of everybody, is what makes it real.</p>

<blockquote>IMPLEMENTATION TIP: Hand over one genuine decision this month — the rota is usually the right one — and do not touch it for eight weeks, even when you would have done it differently. The discomfort of that is the price of having a deputy, and there is no version that avoids it.</blockquote>

<p><b>Where you should not delegate the decision.</b> Anything affecting a person's standing, anything involving significant money, and anything that would be difficult to reverse. A deputy given those too early is being set up rather than developed, and the failure damages them more than it damages the branch. Build up to them: the rota before the disciplinary conversation, an ordering category before a supplier negotiation.</p>"""
, [
 C("Somebody who can do everything you do while following instructions is:",
   ["Deputising", "Covering",
    "Ready for promotion", "A supervisor"], 1,
   "Deputising is deciding what should happen in a situation nobody anticipated — and real absences are full of those."),
 C("Overruling a deputy's first three decisions teaches them that:",
   ["The standard is high", "The delegation was decorative",
    "They need more training", "You are still responsible"], 1,
   "Where a decision is defensible and not what you would have done, live with it — that is the whole exercise."),
 C("A deputy uncertain of their authority will:",
   ["Ask a colleague", "Default to doing nothing",
    "Decide cautiously", "Call you"], 1,
   "Which in your absence is exactly the failure mode you were trying to prevent.")]),

("Standards that survive your absence", 11, """<p>Everything a branch does well that exists only as a habit in somebody's head is one departure away from being lost. Writing it down is unglamorous, takes a few hours in total, and is the difference between a branch and a branch that happens to have a good manager.</p>

<p><b>What is worth writing, which is less than people assume.</b> Not a manual. Half a dozen single pages covering the things that go wrong when nobody does them: opening and closing, the first week for a new starter, the replenishment routine, cash handling and the count, what happens when a delivery is short, and what to do when the till or the power fails.</p>

<p><b>Why one page each.</b> A twenty-page document is written once, filed, and never opened. A page pinned where the task happens is read by somebody who needs it at the moment they need it, which is the only time anybody reads anything in a branch.</p>

<p><b>Write what is actually done, not what should be done.</b> A procedure describing an ideal nobody follows teaches a new person that the written standard is decorative, and they will then treat every other written standard the same way. If the real practice is wrong, fix the practice first and then write it.</p>

<p><b>Have somebody else test it.</b> Give the page to a person who does not do that task and ask them to follow it. Everything they cannot do from the page is a step you knew and did not write, which is most of the value of the exercise and takes ten minutes to discover.</p>

<p><b>Keep it current or throw it away.</b> An out-of-date procedure is worse than none, because it is confidently wrong. When something changes, the page changes the same week or it goes in the bin — and a small number of accurate pages beats a folder of aspirational ones.</p>

<p><b>What this protects against beyond your absence.</b> Staff turnover, which module 4 established is substantial in retail. Every departure takes knowledge with it, and a branch that has written down its six or seven critical routines loses considerably less each time somebody leaves.</p>

<p><b>And what it does for you personally.</b> A branch that is documented is a branch somebody else can be given, which is the precondition for you being given a different one.</p>

<blockquote>IMPLEMENTATION TIP: Write one page this week for whichever routine causes the most trouble when you are not there. Then hand it to somebody who does not do that job and watch them try to follow it. The gaps they hit in ten minutes are the reason the routine keeps failing.</blockquote>

<p><b>Where to keep them.</b> Not in a folder in the office. At the place the task happens — the opening page by the door, the cash page by the safe, the receiving page in the bay. A procedure that requires somebody to go and look for it will be consulted once, on their first day, and never again.</p>"""
, [
 C("A procedure describing an ideal nobody follows teaches new staff that:",
   ["The standard is aspirational", "Written standards are decorative",
    "The task is difficult", "Practice varies"], 1,
   "And they will then treat every other written standard the same way."),
 C("Testing a written routine means:",
   ["Reviewing it yourself", "Giving it to somebody who does not do that task and watching them follow it",
    "Checking it against policy", "Asking the team to confirm"], 1,
   "Everything they cannot do from the page is a step you knew and did not write."),
 C("You find a pinned procedure describing a step the branch changed six months ago. Leaving it there is worse than having nothing because it is:",
   ["Ignored anyway", "Confidently wrong",
    "Cluttering the wall", "Hard to find"], 1,
   "When something changes, the page changes the same week or it goes in the bin.")]),

("When something goes badly wrong", 11, """<p>Every branch has days that are not about trading. A power failure that runs for hours, a flood, a fire alarm, a robbery, a serious accident, a system that stops working on a Saturday, or a crowd situation outside. A manager who has thought about these in advance handles them; one who has not improvises under pressure.</p>

<p><b>The rule that comes before every other rule, and it should be said to your team out loud rather than assumed.</b> <b>People come before stock and before cash.</b> Goods are insured, money is replaceable, and neither is worth an injury to anybody in your branch or to a customer.</p>

<p><b>In a robbery, specifically, and this is the one to be clearest about.</b> Comply. Do not resist, do not chase, do not argue, do not attempt to protect the till or the safe. Give what is asked for. Your staff need to have heard you say this before it happens, because in the moment a person who has not been told may try to protect the business and be hurt doing it.</p>

<p>Afterwards: get everybody safe, call whoever your business says to call, do not clean up or move anything, and look after your people — including the ones who seem fine, who are frequently not.</p>

<p><b>Fire, flood or a structural problem.</b> Everybody out first, count them, and only then think about anything else. Know your exits and check they are clear, which is a weekly thirty-second job and the single most common finding in any safety inspection.</p>

<p><b>A serious accident, to staff or a customer.</b> Care first, then record what happened while it is fresh — what, when, where, who was present, what was done. Not to allocate blame but because an accurate contemporaneous record protects everybody, including the injured person.</p>

<p><b>The operational failures, which are more frequent and less dangerous.</b> Power, system, water, a key supplier failing. These need a plan rather than a reaction: what can we still do, what do we tell customers, at what point do we close, and who decides. Deciding that in advance takes fifteen minutes and prevents an hour of confusion on the day.</p>

<p><b>What to tell customers.</b> Something true, promptly, and the same thing from everybody. A branch where three staff give three explanations turns a problem into a shambles, and a queue told plainly what is happening is remarkably tolerant.</p>

<p><b>And afterwards, always.</b> Tell your manager the same day. Write down what happened while people remember. And ask the team what would have made it go better — the person who was on the floor when it happened knows things you do not.</p>

<blockquote>WATCH-OUT: Your team will do what they have seen or been told, and if they have been told nothing they will improvise — which in a robbery can mean somebody trying to protect a till. Say the rule out loud, more than once, before the day it matters.</blockquote>

<p><b>And afterwards, take it seriously for longer than feels necessary.</b> People who were present at something frightening are frequently fine for a week and not fine afterwards, and the ones who insisted they were unaffected at the time are often the ones to watch. Check in privately a fortnight later, and know what support your business can offer before you need to know it. A manager who handles the incident well and the aftermath badly has done half the job.</p>"""
, [
 C("The rule that comes before all others in an emergency is:",
   ["Protect the stock", "People come before stock and before cash",
    "Contact head office", "Secure the till"], 1,
   "Goods are insured and money is replaceable; an injury is not."),
 C("A member of staff asks what they should do if the branch is robbed. You tell them to:",
   ["Protect the safe if they safely can", "Comply — not resist, chase or argue",
    "Trigger an alarm discreetly", "Delay until help arrives"], 1,
   "They need to have heard you say so before it happens, or somebody may try to protect the business and be hurt."),
 C("Where three members of staff give three explanations for a failure, the branch:",
   ["Covers all possibilities", "Turns a problem into a shambles",
    "Reassures customers", "Buys time"], 1,
   "A queue told plainly and consistently what is happening is remarkably tolerant.")]),

("Leading a team through change", 11, """<p>Refits, new systems, range changes, new procedures, a new owner. Change arrives at a branch from elsewhere, usually with less notice than the manager would like, and how it is handled determines whether it costs you a fortnight or a quarter.</p>

<p><b>What your team is actually worried about.</b> Not the change in the abstract. Whether their job is safe, whether their hours change, whether they will look incompetent at something new, and whether it will make their day harder. Address those four directly and most resistance disappears, because most resistance is anxiety wearing an argument.</p>

<p><b>Tell them early, even when you do not know everything.</b> "Here is what I know, here is what I do not, and I will tell you when I do" is a complete and honest position, and it beats silence. Silence gets filled with rumour, and rumour is always worse than the truth and much harder to correct afterwards.</p>

<p><b>Do not oversell it.</b> If a new system will be harder for six weeks, say so. A manager who promises it will be easy loses their credibility in week two and then has nothing left with which to get the team through weeks three to six.</p>

<p><b>Do not distance yourself from it.</b> "Head office says we have to do this" tells your team that you do not believe in it and that complaining to you is worthwhile. You can disagree upward and still own it downward, and that is the position of every manager in the middle of anything.</p>

<p><b>Expect the dip.</b> Any change makes performance worse before it makes it better, because people are learning while doing. Knowing that in advance stops the second week being treated as a failure and abandoned at exactly the point most changes are abandoned.</p>

<p><b>Get people involved in the parts that are genuinely open.</b> The layout of a section, the order of a routine, who trains whom. Not fake consultation about something already decided, which is worse than none — but the real choices that remain, which are usually more than a manager assumes.</p>

<p><b>And find your early adopters.</b> In any team two or three people take to something new quickly. Give them a role in it. Change spreads sideways between colleagues far better than downwards from a manager, and the person your team actually listens to is often not the person with the title.</p>

<p><b>What to do when the change is genuinely bad for your branch.</b> Say so upward, once, with the specifics — and then implement it properly while the case is considered. A manager who implements badly to prove a point damages their own team and loses the argument anyway, because the failure gets attributed to the branch rather than to the decision. Make the case in writing and let the results speak; if you were right, the evidence arrives on its own.</p>

<blockquote>IMPLEMENTATION TIP: Before any change lands, answer the four questions your team has — job, hours, competence, difficulty — out loud and unprompted. Most of what a manager mistakes for resistance is one of those four going unanswered.</blockquote>"""
, [
 C("Your team is objecting to a new system on operational grounds. Most of what you are hearing is:",
   ["Genuine disagreement with the decision", "Anxiety wearing an argument",
    "Concern about customers", "Habit"], 1,
   "Job, hours, looking incompetent, and whether it makes the day harder — address those four and most of it disappears."),
 C("Saying 'head office says we have to do this' tells your team:",
   ["The origin of the decision", "That you do not believe in it and complaining to you is worthwhile",
    "That it is not negotiable", "The context"], 1,
   "You can disagree upward and still own it downward."),
 C("Performance getting worse before it gets better should be:",
   ["Treated as a warning", "Expected, so the second week is not treated as failure",
    "Reported upward", "Avoided by slower rollout"], 1,
   "That is exactly the point at which most changes are abandoned.")]),

("Developing the people below you", 11, """<p>The single clearest signal of a good branch manager, visible from outside, is how many people have been promoted out of their branch. It is also the thing managers are least rewarded for and most reluctant to do.</p>

<p><b>Why the reluctance is understandable.</b> Developing somebody means losing them. You invest a year, they become genuinely useful, and another branch takes them — and you are back to training somebody. The incentive plainly points the other way.</p>

<p><b>Why to do it anyway, and the reasons are practical rather than noble.</b> Your branch runs better with capable people in it, whatever happens later. People who are being developed stay longer than people who are not, so you keep them for more of the time. Your reputation as somebody who grows people is what gets you the good candidates when you have a vacancy. And a manager whose branch produces supervisors is a manager the business can promote, because there is somebody to take over.</p>

<p><b>What development actually is at branch level.</b> Not courses. Giving somebody a piece of the job that is genuinely theirs, with the standard explained and the outcome owned — a category to order, a routine to run, a new starter to bring on, a supplier to deal with. Responsibility with a name on it, in the ordinary run of the week.</p>

<p><b>Tell people what you see in them.</b> Most staff have no idea their manager rates them, and a person who knows they are regarded as promotable behaves differently and stays longer. It costs one sentence and managers withhold it out of a vague concern about complacency, which is almost never what happens.</p>

<p><b>Be honest about what is missing too.</b> "You are ready except for X, and here is how we work on X" is worth more than encouragement, and it is what somebody can act on. Vague encouragement followed by an unexplained non-promotion is how good people leave.</p>

<p><b>And let them go when it is time.</b> Blocking somebody's promotion to keep your branch running is understandable, visible to everybody, and the fastest way to become a manager nobody wants to work for. The people watching that decision are your remaining team, and they draw the obvious conclusion about their own prospects.</p>

<blockquote>IMPLEMENTATION TIP: Name the two people on your team you would back for promotion, tell each of them so, and give each one thing that is genuinely theirs to run this quarter. That is the whole of development at branch level and it costs no budget at all.</blockquote>

<p><b>Be honest about who is not going further, too.</b> Not everybody wants promotion and not everybody is suited to it, and treating a capable, contented member of staff as a development project they never asked to be is its own kind of disrespect. Ask what somebody actually wants before deciding what to give them — some of your best people want to do their job well and go home, and a branch needs them at least as much as it needs the ambitious ones.</p>"""
, [
 C("Blocking a capable person's promotion to keep your branch running is:",
   ["Sometimes necessary", "Visible to everybody, and the fastest way to become a manager nobody wants to work for",
    "A short-term measure", "Justified by continuity"], 1,
   "Your remaining team draws the obvious conclusion about their own prospects."),
 C("Development at branch level mainly consists of:",
   ["Training courses", "Giving somebody a piece of the job that is genuinely theirs",
    "Appraisal conversations", "Job rotation"], 1,
   "Responsibility with a name on it, in the ordinary run of the week."),
 C("Managers withhold telling somebody they are rated because of a concern about complacency, which is:",
   ["Usually justified", "Almost never what happens",
    "Reasonable for junior staff", "Standard practice"], 1,
   "A person who knows they are regarded as promotable behaves differently and stays longer.")]),

("Handing over a branch", 11, """<p>At some point you will leave a branch — promoted, moved, or gone. What you leave behind is the most public and lasting judgement on how you managed it, and it is almost always done badly because it happens in a fortnight at the end of everything else.</p>

<p><b>What a good handover contains.</b> The state of the branch honestly stated, including the things you did not fix. The routines and who owns them. The people — who is capable, who is struggling, who is a flight risk, and what conversations are outstanding. The current problems and what has been tried. The relationships: who at head office to speak to about what, which suppliers are difficult, who at other branches is helpful. And anything about to happen that is not yet visible.</p>

<p><b>The temptation to leave a tidy picture.</b> Every departing manager wants their branch to look well run, and the honest handover is the one that says where it is not. A successor who discovers three months later that a problem was known and not mentioned will say so, and it costs more than the problem would have.</p>

<p><b>Do not solve everything in the last fortnight.</b> A flurry of changes at the end leaves your successor with a branch mid-transition and no idea why any of it was done. Finish what you can finish, stop what should stop, and hand over the rest as an open item with your view attached.</p>

<p><b>Introduce them properly.</b> To the team individually if you can, to the key people outside the branch, and to the regulars who will notice. Ten minutes each and it saves your successor two months.</p>

<p><b>And then leave properly.</b> Do not take calls from your old team for months, do not comment on decisions the new manager makes, and do not let anybody use you as a route around them. It is flattering to be missed and it undermines the person who has to do the job now.</p>

<p><b>What this looks like from the other side.</b> You will also inherit a branch one day. Expect an incomplete handover, spend your first two weeks reading and watching rather than changing, and ask the team what they think should be different — they usually know, they have usually never been asked, and it is the fastest way to understand what you have taken on.</p>

<blockquote>WATCH-OUT: The most common handover failure is omission rather than dishonesty — the problem you meant to mention, the conversation you were going to have. Write the handover over two weeks rather than in one sitting, because the things worth saying occur to you while you are doing the job, not while you are writing about it.</blockquote>

<p><b>Hand over the relationships you cannot write down.</b> The supplier contact who will do you a favour, the person in distribution who answers quickly, the peer who helped you with a problem. These are worth more than most of the operational detail and they are the first thing lost in a transition, because they exist as a set of names in one person's head. Introduce rather than list.</p>"""
, [
 C("The most common handover failure is:",
   ["Dishonesty about performance", "Omission — the problem you meant to mention",
    "Excessive detail", "Late delivery"], 1,
   "Write it over two weeks, because the things worth saying occur to you while doing the job."),
 C("Solving everything in your last fortnight leaves your successor with:",
   ["A clean start", "A branch mid-transition and no idea why any of it was done",
    "Improved figures", "Fewer problems"], 1,
   "Finish what you can, stop what should stop, and hand over the rest with your view attached."),
 C("Taking calls from your old team after you leave:",
   ["Maintains continuity", "Undermines the person who has to do the job now",
    "Helps the transition", "Is expected"], 1,
   "It is flattering to be missed, and it should not be indulged.")]),

("Okelewo: what happened when Sango's manager was promoted", 11, """<p>The Sango manager — steady, unremarkable sales, lowest turnover in the group — was made area manager for the Abeokuta branches. The interesting part is what happened to his branch afterwards, because it tested everything in this module.</p>

<p><b>What he had already built, without calling it succession planning.</b> A deputy who had been running the rota and the ordering for a year, including the weeks he was present. Six single pages covering opening, closing, the first week, replenishment, the count, and what to do when the power fails. Routines that belonged to named people on named days. And two people he had told, explicitly, that he thought they could run a branch.</p>

<p><b>What the handover contained.</b> Eleven pages written over three weeks. The state of the branch including two things he had never fixed — a supplier whose deliveries were persistently late, and a member of staff whose performance he had been managing for four months without resolution. He named both.</p>

<p><b>What happened in the first quarter after he left.</b> Sales flat. Losses unchanged. One departure. His deputy took the branch and made three changes in the first month, two of which he would not have made and one of which was better than anything he had done.</p>

<p><b>What the business noticed, finally.</b> That the branch had not depended on him, which meant the thing they had been valuing him for — being steady — was actually a set of transferable arrangements. Two of those six pages were adopted across the group. Nobody had asked him for them in three years.</p>

<p><b>The contrast that made the point.</b> A manager at another branch left the same quarter. That branch took two months to stabilise, lost three staff in the transition, and the successor spent her first six weeks discovering arrangements that existed only in her predecessor's head. Nothing about that manager had been worse — his sales had been better — and his branch had been built on him rather than on anything anybody could inherit.</p>

<p><b>And the personal outcome.</b> The steady manager was promoted precisely because he could be moved. The stronger performer could not be, and was still in the same branch eighteen months later, working the same hours, being told he was doing well.</p>

<p><b>What the deputy did afterwards is the honest ending.</b> Three changes in the first month, one of which the former manager thought was a mistake and which worked. A successor is not a copy, and a branch built properly is one somebody else can improve rather than merely maintain — a manager whose arrangements only work when operated exactly as they left them has built something more fragile than they think.</p>

<blockquote>IMPLEMENTATION TIP: The question this chapter turns on is worth asking of yourself directly. If you were promoted next month, what would your successor find that exists only in your head — and how long would it take you to write down the six pages that would fix it?</blockquote>"""
, [
 C("The Sango handover named two things the manager had never fixed. This was:",
   ["A risk to his reputation", "The point — a successor discovering a known problem later costs more",
    "Unnecessary detail", "Unusual candour"], 1,
   "Every departing manager wants the branch to look well run, and the honest handover says where it is not."),
 C("The stronger-performing manager at another branch could not be promoted because:",
   ["His results were inconsistent", "His branch had been built on him rather than on anything inheritable",
    "He lacked experience", "No vacancy existed"], 1,
   "He was still in the same branch eighteen months later, working the same hours, being told he was doing well."),
 C("Two of the six pages were adopted across the group, and nobody had asked for them in three years because:",
   ["They were confidential", "Practices that are invisible do not spread on their own",
    "They were branch-specific", "He had not offered them"], 1,
   "A business tends to ask its struggling branches what is wrong and its steady ones nothing at all.")]),
("Review, and the resilience routine", 11, """<p>This is the chapter to keep. Everything in this module is slow work with no deadline, which means it happens only if it is on a list.</p>

<p><b>The test (Chapter 1).</b> If you were away two weeks with no contact, what would be different? A deputy who can decide, standards outside your head, routines with names and times. Take a day off and do not answer the phone — what breaks is your list.</p>

<p><b>The deputy (Chapter 2).</b> Covering is doing your tasks; deputising is deciding in a situation nobody anticipated. Give away real decisions while you are present, let the first three be made badly, ask before you tell, explain reasoning rather than conclusions, state their authority in specifics, and tell the team.</p>

<p><b>Written standards (Chapter 3).</b> Half a dozen single pages, describing what is actually done, tested by somebody who does not do the task, current or binned.</p>

<p><b>Emergencies (Chapter 4).</b> People before stock and cash, said out loud before the day. Comply in a robbery. Everybody out and counted in a fire. Care first then record. One consistent explanation to customers. Tell your manager the same day.</p>

<p><b>Change (Chapter 5).</b> Answer the four worries — job, hours, competence, difficulty. Tell them early including what you do not know. Do not oversell it, do not distance yourself from it, expect the dip, and use your early adopters.</p>

<p><b>Developing people (Chapter 6).</b> Responsibility with a name on it. Tell people what you see in them and what is missing. Let them go when it is time.</p>

<p><b>Handover (Chapter 7).</b> Honest including what you did not fix. No flurry of changes at the end. Introduce them properly, then leave properly.</p>

<p><b>The routine itself.</b> Quarterly: one real decision handed over and left alone. One page written or refreshed. One conversation with somebody about where they are going. Annually: a day off with the phone off, and the handover note you would write if you were promoted next month — written whether or not you are.</p>

<p><b>Why that last one is worth doing when nothing is happening.</b> Writing the handover note you do not need is the fastest way to find out what exists only in your head. It takes two hours, nobody sees it, and the list it produces is precisely the work in this module.</p>

<blockquote>IMPLEMENTATION TIP: Write that handover note this quarter with no intention of leaving. Everything you find yourself explaining rather than pointing at is something that lives only with you — and that list is the whole of what this module is asking you to build.</blockquote>

<p><b>A closing word on why this module is last before the routine.</b> Everything else in this track improves a branch while you are running it. This one is what makes the improvement survive you — and a manager who does all of the rest and none of this leaves behind a branch that reverts within two quarters, which is a great deal of work to have done for nothing.</p>"""
, [
 C("Writing a handover note when you are not leaving is worth doing because it:",
   ["Prepares for promotion", "Finds out what exists only in your head",
    "Satisfies a policy", "Documents the branch"], 1,
   "Two hours, nobody sees it, and the list it produces is the work of this module."),
 C("The quarterly resilience routine includes a page written, a conversation about somebody's direction, and:",
   ["A team briefing", "One real decision handed over and left alone",
    "A stock count", "A branch inspection"], 1,
   "Left alone is the part that makes it a handover rather than a delegation you supervise."),
 C("Everything in this module is:",
   ["Urgent when it arises", "Slow work with no deadline, so it happens only if it is on a list",
    "Head office's responsibility", "Done during quiet periods"], 1,
   "Which is why the chapter ends with a routine rather than with encouragement.")]),

]


QUESTIONS = [
 Q("The two-week test asks what would be different if you were:", ["Working reduced hours", "Away for two weeks with no contact", "Moved to another branch", "Off the floor"], 1,
   "Only 'the branch would run and a few decisions would wait' describes one that has been built.", "Ch1 §1", "The two-week test"),
 Q("A manager who cannot be absent:", ["Is indispensable and valued", "Cannot be promoted", "Should hire more staff", "Is working correctly"], 1,
   "The most indispensable manager in a chain is frequently the one who has been in the same branch for six years.", "Ch1 §5", "The two-week test"),
 Q("The three things that make a branch run without you are a deputy who can decide, routines with names attached, and:", ["A larger team", "Standards that exist outside your head", "Better systems", "Head office support"], 1,
   "None of them is about your team trying harder.", "Ch1 §6", "The two-week test"),
 Q("The way to test your branch's resilience is to:", ["Ask your deputy", "Take a day off and not answer the phone", "Review the routines", "Run a drill"], 1,
   "Whatever went wrong is your list, discovered cheaply.", "Ch1 §10", "The two-week test"),
 Q("Somebody who can do your tasks while following instructions is:", ["A deputy", "Covering", "Ready to promote", "Deputising"], 1,
   "Deputising is deciding in a situation nobody anticipated.", "Ch2 §2", "The deputy"),
 Q("Most deputies never develop because they are:", ["Not capable", "Never allowed to decide while you are present", "Undertrained", "Too junior"], 1,
   "The arrangement works perfectly until you are not there.", "Ch2 §3", "The deputy"),
 Q("When a deputy brings you a problem you should:", ["Give the answer", "Ask what they think should happen first", "Handle it yourself", "Refer to the procedure"], 1,
   "Answering their own question repeatedly is what builds judgement.", "Ch2 §6", "The deputy"),
 Q("Explaining your reasoning rather than your conclusion means a deputy can:", ["Repeat your decision", "Handle the case you never discussed", "Justify it upward", "Train others"], 1,
   "One who knows what you decided can only repeat it.", "Ch2 §7", "The deputy"),
 Q("Authority the rest of the team does not know about:", ["Still applies", "Is not authority — they will wait for you", "Works informally", "Is safer"], 1,
   "Saying plainly in front of everybody that this person decides is what makes it real.", "Ch2 §9", "The deputy"),
 Q("How much should be written down?", ["A full manual", "About half a dozen single pages", "Everything critical", "One document per role"], 1,
   "A twenty-page document is filed and never opened.", "Ch3 §2", "Written standards"),
 Q("A procedure describing what should be done rather than what is done teaches staff that:", ["Standards are high", "Written standards are decorative", "The task is hard", "Practice varies"], 1,
   "If the real practice is wrong, fix the practice first and then write it.", "Ch3 §4", "Written standards"),
 Q("A written routine is tested by:", ["Manager review", "Giving it to somebody who does not do that task", "Comparing to policy", "Team confirmation"], 1,
   "Everything they cannot do from the page is a step you knew and did not write.", "Ch3 §5", "Written standards"),
 Q("An out-of-date procedure is worse than none because it is:", ["Confusing", "Confidently wrong", "Ignored", "Hard to update"], 1,
   "It changes the same week or it goes in the bin.", "Ch3 §6", "Written standards"),
 Q("Beyond your absence, written routines protect against:", ["Audit findings", "Staff turnover taking knowledge with it", "Head office scrutiny", "Seasonal pressure"], 1,
   "A branch that has written down its critical routines loses less each time somebody leaves.", "Ch3 §7", "Written standards"),
 Q("The rule that precedes all others in an emergency is:", ["Secure the cash", "People before stock and cash", "Call head office", "Clear the building"], 1,
   "Goods are insured and money is replaceable.", "Ch4 §2", "Emergencies"),
 Q("In a robbery, staff should:", ["Trigger an alarm", "Comply", "Delay the intruder", "Protect the safe"], 1,
   "They need to have heard you say so before it happens.", "Ch4 §3", "Emergencies"),
 Q("After a robbery you should not:", ["Call for help", "Clean up or move anything", "Check on your staff", "Record what happened"], 1,
   "And look after your people, including the ones who seem fine.", "Ch4 §4", "Emergencies"),
 Q("In a fire or flood the first action is:", ["Secure the till", "Everybody out and counted", "Call the manager", "Shut down systems"], 1,
   "Exits checked weekly is a thirty-second job and the most common safety finding.", "Ch4 §5", "Emergencies"),
 Q("After a serious accident, an accurate contemporaneous record:", ["Allocates blame", "Protects everybody, including the injured person", "Satisfies insurers only", "Is optional"], 1,
   "Care first, then record what happened while it is fresh.", "Ch4 §6", "Emergencies"),
 Q("Three staff giving three explanations during a failure:", ["Covers all bases", "Turns a problem into a shambles", "Reassures customers", "Is unavoidable"], 1,
   "A queue told plainly and consistently is remarkably tolerant.", "Ch4 §8", "Emergencies"),
 Q("Most resistance to change is:", ["Disagreement", "Anxiety wearing an argument", "Habit", "Concern for customers"], 1,
   "Job, hours, looking incompetent, and whether the day gets harder.", "Ch5 §2", "Change"),
 Q("When you do not know everything about a coming change you should:", ["Wait until you do", "Say what you know and what you do not", "Say nothing yet", "Refer them upward"], 1,
   "Silence gets filled with rumour, which is always worse and harder to correct.", "Ch5 §3", "Change"),
 Q("Promising a hard change will be easy costs you:", ["Nothing much", "Your credibility in week two", "Time", "Team goodwill only"], 1,
   "And you then have nothing left to get the team through weeks three to six.", "Ch5 §4", "Change"),
 Q("Performance dipping during a change should be:", ["Escalated", "Expected", "Prevented", "Hidden"], 1,
   "It is exactly when most changes are abandoned.", "Ch5 §6", "Change"),
 Q("Change spreads:", ["Downward from the manager", "Sideways between colleagues", "Through written procedure", "By enforcement"], 1,
   "The person your team actually listens to is often not the one with the title.", "Ch5 §8", "Change"),
 Q("The clearest external signal of a good branch manager is:", ["Sales growth", "How many people have been promoted out of their branch", "Low shrinkage", "Customer feedback"], 1,
   "It is also what managers are least rewarded for.", "Ch6 §1", "Developing people"),
 Q("Developing people is reluctantly done because:", ["It takes budget", "It means losing them", "It requires courses", "Results are slow"], 1,
   "The incentive plainly points the other way.", "Ch6 §2", "Developing people"),
 Q("People who are being developed:", ["Leave sooner", "Stay longer than people who are not", "Cost more", "Need more supervision"], 1,
   "So you keep them for more of the time.", "Ch6 §3", "Developing people"),
 Q("Development at branch level mainly means:", ["Formal training", "Giving somebody a piece of the job that is genuinely theirs", "Appraisals", "Shadowing"], 1,
   "Responsibility with a name on it, in the ordinary run of the week.", "Ch6 §4", "Developing people"),
 Q("Vague encouragement followed by an unexplained non-promotion is:", ["Normal", "How good people leave", "Unavoidable", "A timing issue"], 1,
   "'You are ready except for X, and here is how we work on X' is what somebody can act on.", "Ch6 §6", "Developing people"),
 Q("A good handover includes the routines, the people, the relationships and:", ["Only what is working", "The things you did not fix", "The sales history", "Head office contacts alone"], 1,
   "A successor discovering later that a problem was known and unmentioned costs more than the problem.", "Ch7 §2", "Handover"),
 Q("Making a flurry of changes in your final fortnight leaves your successor:", ["A better branch", "A branch mid-transition with no idea why", "Fewer problems", "Clear priorities"], 1,
   "Hand over the open items with your view attached instead.", "Ch7 §4", "Handover"),
 Q("Introducing your successor to the team, key contacts and regulars saves them:", ["A week", "About two months", "Little", "One quarter"], 1,
   "Ten minutes each.", "Ch7 §5", "Handover"),
 Q("After leaving, taking calls from your old team:", ["Eases the transition", "Undermines the person doing the job now", "Is expected", "Helps continuity"], 1,
   "It is flattering to be missed and it should not be indulged.", "Ch7 §6", "Handover"),
 Q("Inheriting a branch, your first two weeks should be spent:", ["Making changes", "Reading and watching, and asking the team what should be different", "Reviewing figures", "Meeting head office"], 1,
   "They usually know, and have usually never been asked.", "Ch7 §7", "Handover"),
 Q("Sango's deputy had been running the rota and ordering for:", ["A month", "A year, including while he was present", "The handover period", "Two weeks"], 1,
   "Which is what made him able to decide rather than merely cover.", "Ch8 §2", "Okelewo succession"),
 Q("In the first quarter after the promotion, Sango's branch:", ["Declined", "Was flat on sales and losses with one departure", "Improved sharply", "Lost three staff"], 1,
   "His deputy made three changes, one of which was better than anything he had done.", "Ch8 §4", "Okelewo succession"),
 Q("What the business finally noticed was that being steady was:", ["A personality", "A set of transferable arrangements", "Luck", "Branch-specific"], 1,
   "Two of his six pages were adopted across the group.", "Ch8 §5", "Okelewo succession"),
 Q("The comparison branch took two months to stabilise because it had been built:", ["With fewer staff", "On its manager rather than on anything inheritable", "Without systems", "In a harder location"], 1,
   "His sales had been better, and he was still in the same branch eighteen months later.", "Ch8 §6", "Okelewo succession"),
 Q("The steady manager was promoted precisely because:", ["His figures improved", "He could be moved", "He asked", "A vacancy arose"], 1,
   "The stronger performer could not be.", "Ch8 §7", "Okelewo succession"),
 Q("Nobody had asked for the six pages in three years because:", ["They were informal", "Practices that are invisible do not spread on their own", "He kept them private", "They were branch-specific"], 1,
   "A business asks its struggling branches what is wrong and its steady ones nothing at all.", "Ch8 §5", "Okelewo succession"),
 Q("Handing over a real decision requires leaving it alone for about:", ["A week", "Eight weeks", "A month", "A quarter"], 1,
   "Even when you would have done it differently — the discomfort is the price of having a deputy.", "Ch2 §10", "The deputy"),
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
    rebalance(QUESTIONS, "retail:without_you:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:without_you:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))
    if len(LESSONS) != 9:
        raise SystemExit("ABORT: %d chapters, expected 9" % len(LESSONS))

    mod = {
        "title": "RL 8 — The Branch Without You",
        "desc": ("Building something that survives your absence. The two-week test, a deputy "
                 "who can decide rather than cover, standards written down, what to do when "
                 "something goes badly wrong, leading a team through change, developing the "
                 "people below you, and handing a branch over honestly."),
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
