#!/usr/bin/env python3
"""Build 'The Manager's Week' into academy_retail_data.json.

Module 9 of Retail Leadership Essentials, and the last.

The risk in a capstone is that it restates the other eight modules. This one
earns its place by answering a different question: eight modules have each
proposed habits, and a branch manager has a job. What does the week actually
look like, in what order, and what has to be given up to make room?

The organising claim is that a manager fails at this track not by disagreeing
with it but by agreeing with all of it and doing none of it, because every
habit in it is important and none is urgent.

STANDS ALONE. No other module or track assumed.

Run from the app package directory:  python3 build_retail_m9.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "the_week"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Why a rhythm rather than a list", 11, """<p>Eight modules have each proposed a handful of habits. Taken together they are more than any manager will do from intention, and this is the point at which most training quietly fails — not because anybody disagreed with it, but because they agreed with all of it and did none of it.</p>

<p><b>The reason is structural rather than personal.</b> Everything in this track is important and none of it is urgent. A queue is urgent. A delivery is urgent. A customer at the counter is urgent. Counting your top lines, having the conversation you have been putting off, and writing a page of procedure are none of them, and they will lose to the urgent thing every single day if the contest is left to be decided each morning.</p>

<p><b>What a rhythm does that a list does not.</b> A list is re-prioritised every day, and the important-but-not-urgent items sink. A rhythm removes the decision: the count happens on Tuesday because it happens on Tuesday, not because you judged this morning that it was the best use of the next twenty minutes. You will always judge that it is not.</p>

<p><b>The three properties of a rhythm that survives.</b></p>

<p><b>Small enough to do on a bad week.</b> If your routine only works on quiet weeks, it does not work — quiet weeks are not the ones where things go wrong.</p>

<p><b>Fixed to a day or a time rather than a frequency.</b> "Weekly" becomes fortnightly and then monthly. "Tuesday after the delivery" holds.</p>

<p><b>Owned by a name, including yours.</b> Anything belonging to the branch in general belongs to nobody, which module 4 established about replenishment and is true of everything.</p>

<p><b>What this module is.</b> Not new material. The habits from the eight modules, arranged into a week, a month and a quarter that a real branch manager can actually keep, with a view about what to drop when the week goes wrong — because it will, and having decided in advance what survives is the difference between a routine that bends and one that breaks.</p>

<p><b>And a realistic expectation.</b> You will keep perhaps two-thirds of this in a normal month. That is a success rather than a failure. A manager doing two-thirds of these habits is doing more deliberate management than most people in the job, and the alternative to two-thirds is not all of it — it is none of it.</p>

<blockquote>WATCH-OUT: The failure mode is not rejecting the routine. It is adopting all of it enthusiastically for three weeks, missing a fortnight during a difficult month, and never restarting — because a routine that has lapsed feels like a failure rather than something to pick up on Monday.</blockquote>

<p><b>Build it in order rather than all at once.</b> Start with the daily fifteen minutes for a month, because it is the smallest and it changes what you notice. Add the weekly hour in month two. Leave the monthly and quarterly work until those two are genuinely automatic. A manager who adopts the whole structure in week one is running an experiment that ends in about three weeks; one who adds a layer a month is still running it a year later.</p>"""
, [
 C("Everything in this track loses to the urgent thing daily because it is:",
   ["Difficult", "Important and not urgent",
    "Poorly defined", "Unrewarded"], 1,
   "A queue is urgent; counting your top lines is not, and the contest is decided the same way every morning."),
 C("You keep a list of everything this track recommends and re-prioritise it each morning. The predictable result is:",
   ["Broad coverage", "The important-but-not-urgent items sink, every day",
    "Better focus", "Efficient delegation"], 1,
   "The count happens on Tuesday because it happens on Tuesday, not because you judged it the best use of twenty minutes."),
 C("Keeping about two-thirds of the routine in a normal month is:",
   ["A failure to address", "A success — the alternative to two-thirds is none of it",
    "The minimum acceptable", "A sign of overload"], 1,
   "A manager doing two-thirds is doing more deliberate management than most people in the job.")]),

("The daily fifteen minutes", 11, """<p>Most of a branch manager's day is reactive and should be. The part that is not needs to be small, early, and the same every day.</p>

<p><b>Before the doors open, or as close to it as your shift allows.</b></p>

<p><b>Walk the floor as a customer would.</b> Not an inspection — the route somebody entering would take. Gaps on the lines that matter, anything obviously wrong, and whether the branch looks like somewhere you would shop. Three minutes.</p>

<p><b>Check the three things that must be right.</b> The float counted and the shift opened. Cash from yesterday dealt with. Anything left over from the previous day that will bite today.</p>

<p><b>Look at yesterday's numbers, briefly.</b> Not to analyse — to notice. Anything unusual gets remembered rather than investigated now.</p>

<p><b>Say the day's one thing.</b> Whatever matters most today, said to whoever is on: the delivery is at eleven, we were short on the chilled section yesterday, there is a promotion starting. Thirty seconds, and it is the difference between a team that knows the day's shape and one that discovers it.</p>

<p><b>Then during the day, two things that are not fifteen minutes but are decisions.</b></p>

<p><b>Do not work the busiest hour.</b> Watch it instead, at least twice a week. The queue, what stops it, who leaves, whether the shelves are thinning. Serving during it feels essential and removes the only person able to see the whole picture.</p>

<p><b>Have the difficult conversation the day it arises.</b> Four minutes, privately, specifically. Postponed to a better moment it becomes a week, then a month, and by then the standard has moved.</p>

<p><b>And at close.</b> The drawer counted and any difference explained while somebody remembers. Conflicts, failures and anything unresolved cleared rather than carried. Two minutes, and it is what stops a small thing becoming an investigation.</p>

<blockquote>IMPLEMENTATION TIP: Do the fifteen minutes before you open your messages rather than after. A manager who starts the day with the inbox has handed the first hour to whoever wrote to them, and the walk gets postponed to a moment that does not arrive.</blockquote>

<p><b>Where your shift does not allow a pre-opening walk.</b> Plenty of managers start mid-morning or work the late shift. Do it at the start of your own day rather than the branch's — the point is that it happens before you are absorbed, not that it happens at eight. And on a late shift the closing equivalent is more valuable anyway: walking the floor at the end tells you what the day did to the branch, which the morning cannot.</p>

<p><b>Why fifteen minutes and not thirty.</b> Because thirty will not survive. A routine sized for a good day is abandoned on the first difficult one, and a manager who has abandoned it twice stops attempting it. Fifteen minutes fits into the worst morning you are likely to have, which is the only test that matters — and on the days you have longer, the walk simply takes longer without the routine depending on it.</p>"""
, [
 C("Doing the morning walk, the route to take is:",
   ["An inspection order, back to front", "The one a customer entering would take",
    "Stockroom first, then floor", "Whatever the rota suggests"], 1,
   "You are looking at whether the branch looks like somewhere you would shop."),
 C("The daily fifteen minutes should happen:",
   ["After clearing messages", "Before opening your messages",
    "At the first quiet moment", "After the delivery"], 1,
   "Starting with the inbox hands the first hour to whoever wrote to you, and the walk gets postponed."),
 C("Twice a week, what should you be doing during the busiest hour?",
   ["Serving, where you are most useful", "Standing where you can see it, not serving",
    "Catching up on admin while the deputy covers", "Checking the stockroom"], 1,
   "Serving during it removes the only person able to see the whole picture.")]),

("The weekly hour", 11, """<p>One hour a week, protected, is where most of the change in a branch actually comes from. It is also the first thing surrendered when the week gets difficult, which is why it needs a slot rather than an intention.</p>

<p><b>Twenty minutes: the numbers.</b> Transactions and basket against the same week last year. Margin against the prior month. Availability on your top forty lines, counted rather than estimated. Markdown and its main reason. Hours against trade. And one thing you saw on the floor that is not a number.</p>

<p>Written down and kept, so that after twelve weeks you have a series rather than a snapshot.</p>

<p><b>Fifteen minutes: the count.</b> Your highest-value or highest-risk lines, counted blind, by somebody who does not look after them. It is the item that tells you whether everything else is working.</p>

<p><b>Ten minutes: people.</b> Publish the rota, same day, a week ahead. Look at who has the unpopular shifts this week and across the month. And notice who you have not had a real conversation with — in a branch of fifteen there is always somebody, and it is rarely the loudest person.</p>

<p><b>Fifteen minutes: the one cause.</b> Not an instance — a cause. The reason a gap keeps appearing, the reason the same complaint recurs, the reason the rota keeps failing. One thing, chosen because it is both moving and worth money, worked on for fifteen minutes.</p>

<p><b>Why the last one matters more than its size suggests.</b> Fifteen minutes a week is thirteen hours a year on causes rather than instances. Most branch managers spend approximately none, which is why they meet the same problem every month for years and describe their job as firefighting.</p>

<p><b>Choose the slot deliberately.</b> Not Monday, which is full of the weekend. Not Friday, which is full of the weekend coming. Mid-week, after the delivery, at a time your branch is predictably quiet — and tell your team it exists so that being unavailable is a known arrangement rather than you hiding.</p>

<blockquote>IMPLEMENTATION TIP: Put the hour in as a recurring appointment and treat it exactly as you would a meeting with your area manager — because a meeting with your area manager does not get moved when the branch is busy, and this is worth more than most of them.</blockquote>

<p><b>What to do when the hour gets taken.</b> It will — a delivery fails, somebody does not turn up, a customer situation runs long. Move it to a named alternative slot the same week rather than skipping it, and decide that alternative in advance so the decision is not being made under pressure. An hour moved is a routine; an hour skipped twice is a routine that has ended.</p>

<p><b>What to do with the hour when nothing is wrong.</b> Some weeks the numbers are unremarkable, the count is clean and no cause is pressing. Do not give the hour back — use it on the work that never becomes urgent: a page of procedure, a conversation with somebody about where they are going, the beginnings of a case you will submit next quarter. The quiet weeks are the only time that work is ever going to get done, and a manager who returns the hour on those weeks will find it has quietly stopped being an hour at all.</p>"""
, [
 C("Fifteen minutes a week spent on causes rather than instances amounts annually to:",
   ["Two hours", "Thirteen hours",
    "Fifty hours", "One day"], 1,
   "Most branch managers spend approximately none, which is why they meet the same problem every month for years."),
 C("The weekly hour should be scheduled:",
   ["Monday morning", "Mid-week, after the delivery, at a predictably quiet time",
    "Friday afternoon", "Whenever the branch is calm"], 1,
   "And your team should know it exists, so being unavailable is a known arrangement rather than you hiding."),
 C("Which weekly item tells you whether the others are working?",
   ["The numbers review", "The blind count of top lines",
    "The rota", "The cause work"], 1,
   "Counted by somebody who does not look after those lines.")]),

("The monthly two hours", 11, """<p>Monthly work is the level at which patterns become visible. Weekly figures are noisy; monthly ones say something, and a manager who only ever looks weekly is reacting to variation.</p>

<p><b>Forty minutes: read the month properly.</b> Sales broken into its parts against last year. Margin, and if it moved, decomposed by category and markdown reason before anybody asks. Availability across the four weeks. Losses by category rather than as a total. And the gaps you recorded marked with which of the four causes produced each.</p>

<p><b>Twenty minutes: the exception reports.</b> Refunds, voids, discounts and write-offs by person and by hour. You are looking for concentration rather than volume — the same person, the same hour, the same line, against what the rest of the branch does. Almost every month this shows nothing, and that is a result rather than a waste.</p>

<p><b>Twenty minutes: people.</b> Who left, who is showing the signals, who you would be sorry to lose and whether they know it. The twice-yearly ten-minute conversations, two or three of them, spread so they actually happen.</p>

<p><b>Twenty minutes: upward.</b> Your monthly conversation, prepared rather than attended. Margin, availability, losses and turnover brought before being asked. One thing going wrong with what you are doing about it. One thing you need, with a number attached.</p>

<p><b>Twenty minutes: outward.</b> Ask your counter staff which regulars they have not seen. Read your recorded complaints as a set rather than as incidents. Check the access and keys list against who actually still works here.</p>

<p><b>And the monthly habit that costs nothing.</b> Walk the branch with somebody else's eyes — a manager from another branch, a new starter in their first fortnight — and ask what they would change first. After a year in a place you have stopped seeing it, and this is the only reliable way to see it again.</p>

<blockquote>WATCH-OUT: The monthly review is the one most often replaced by attending a meeting about the month. Reading your own figures for forty minutes before that meeting is what makes you the person in the room who knows what happened rather than the person being told.</blockquote>

<p><b>Two hours a month, spread rather than blocked.</b> The month-end reading needs a single sitting because it is analysis. The people work, the exception reports and the outward look do not — twenty minutes each, on different days, is easier to protect and works just as well. Trying to find two clear hours in a branch is how the monthly work gets postponed to a quieter month that does not exist.</p>

<p><b>Do it in the first week of the month, not the last.</b> Reading last month during the final days of this one means acting on it with a fortnight already gone. The figures are usually available within the first few days, and a problem identified on the fourth leaves you most of a month to do something about it — which is the difference between a monthly review that changes anything and one that describes what has already happened.</p>"""
, [
 C("Looking at exception reports and finding nothing is:",
   ["A waste of twenty minutes", "A result",
    "A sign to look harder", "Evidence the report is wrong"], 1,
   "You are looking for concentration rather than volume, and almost every month shows none."),
 C("Attending the monthly meeting without reading your own figures first makes you:",
   ["Appropriately prepared", "The person being told rather than the person who knows",
    "Efficient with time", "Reliant on the pack"], 1,
   "Forty minutes beforehand is what changes which of the two you are."),
 C("Walking your branch with somebody else's eyes matters because after a year:",
   ["Standards drift", "You have stopped seeing it",
    "The layout dates", "Staff stop noticing"], 1,
   "It is the only reliable way to see your own branch again.")]),

("The quarterly half day", 11, """<p>Once a quarter, half a day away from the floor. It is the hardest thing in this module to protect and the one that separates a manager who is improving a branch from one who is maintaining it.</p>

<p><b>What belongs in it.</b></p>

<p><b>The composite look.</b> Your quarter's numbers as a series rather than three months. What has actually moved, what has not moved despite attention, and what you were wrong about.</p>

<p><b>One case, properly built.</b> The thing your branch most needs, measured for three weeks beforehand, priced, with what you have already done stated — timed to arrive before your business decides its budgets rather than when the problem becomes urgent to you.</p>

<p><b>Two competitors walked as a customer.</b> Twenty lines priced. Something they do better that you could copy this month.</p>

<p><b>The resilience work.</b> One real decision handed to your deputy and left alone. One page of procedure written or refreshed. One conversation with somebody about where they are going.</p>

<p><b>Dead stock and space.</b> Clear what does not sell, and decide before you clear it what is going into the space — otherwise you have converted one problem into a gap.</p>

<p><b>And one deliberate look outward.</b> Has anything changed in your catchment — an employer opened or closed, a road, a competitor, a new development. These move slowly enough to be invisible weekly and fast enough to matter over a year.</p>

<p><b>Where to do it.</b> Not in the branch. A manager sitting in the office at the back of their own shop will be interrupted within eleven minutes, and the half day becomes four interrupted fragments that achieve none of it. Anywhere else, with the phone off, and your deputy holding the branch — which is also, conveniently, the practice they need.</p>

<p><b>What this is genuinely worth.</b> Nearly everything a branch manager achieves beyond keeping the shop running comes from this half day: the case that gets funded, the cause that gets fixed, the person who gets developed. Two days a year, and most managers never take one.</p>

<p><b>And it is worth asking for rather than assuming.</b> If your business does not expect branch managers to be off the floor, say what you intend to do with the time and what came out of the last one. Framed as a day away it sounds like a privilege; framed as the half day that produced the storeroom case and the availability recovery, it is straightforward to approve — and much easier to protect once somebody above you knows it exists.</p>

<blockquote>IMPLEMENTATION TIP: Book the four half days for the year now, in the calendar, with dates. Booked in advance they mostly survive; intended each quarter they never happen, and the reason is always something that felt more important at the time and is not remembered three months later.</blockquote>"""
, [
 C("You have booked the quarterly half day. Where you do it matters, and the answer is:",
   ["The branch office, so you are reachable", "Anywhere but the branch, phone off, deputy holding it",
    "Head office", "On the floor, observing"], 1,
   "A manager in the office at the back of their own shop is interrupted within eleven minutes."),
 C("Booking the four half days in advance rather than intending them matters because:",
   ["It signals commitment", "Intended each quarter they never happen",
    "It helps the rota", "Head office expects it"], 1,
   "Something always feels more important at the time and is not remembered three months later."),
 C("You are about to clear two bays of stock that has not moved in a year. The thing to settle first is:",
   ["The markdown percentage", "What is going into the space afterwards",
    "Who authorises the write-down", "The disposal route"], 1,
   "Otherwise you have converted one problem into a gap.")]),

("Protecting the time", 11, """<p>Everything above is straightforward to agree with and difficult to keep, and the difficulty is not discipline. It is that a branch generates interruptions faster than any individual can absorb them.</p>

<p><b>Where the time actually goes.</b> Covering absence. Serving because the queue is long. Answering questions your team could answer themselves. Doing things faster than explaining them. Messages from the centre. And the genuinely unpredictable, which is a smaller share of the day than most managers believe.</p>

<p><b>The four that are recoverable.</b></p>

<p><b>Questions your team could answer.</b> Every one you answer trains them to bring the next. Ask what they think first — most of the time their answer is adequate and the habit changes within a month.</p>

<p><b>Doing rather than explaining.</b> Faster today, every time, and the reason your Tuesday looks the same in a year.</p>

<p><b>Covering absence.</b> Sometimes unavoidable and frequently a rota built without slack. If you are covering weekly, that is a staffing pattern rather than bad luck, and it is a case to make upward with the hours attached.</p>

<p><b>Messages.</b> Twice a day at fixed points rather than continuously. A branch manager reading messages as they arrive is available to everybody and present for nobody.</p>

<p><b>The sentence that protects more time than any technique.</b> "I am not available between two and three on Wednesdays." Said once to your team, kept for a month, and it becomes a fact about the branch rather than a request.</p>

<p><b>What to drop when the week goes wrong</b>, decided now rather than in the moment. Drop the monthly reading, drop the competitor visit, drop the page of procedure. <b>Keep the count, keep the difficult conversation, and keep the rota.</b> Those three have consequences that compound if missed and the others do not, and having ranked them in advance means a bad week costs you the right things.</p>

<p><b>And restart without ceremony.</b> A routine missed for a fortnight is picked up on Monday, not abandoned and mourned. The most common way this module fails is not never starting — it is stopping once and treating that as the answer.</p>

<blockquote>IMPLEMENTATION TIP: Decide today which three items survive a bad week and write them somewhere you will see. When the bad week arrives you will not be in any condition to rank them, and whatever is dropped in the moment tends to be whatever is next in the diary rather than whatever matters least.</blockquote>

<p><b>The interruptions worth accepting without resentment.</b> A member of staff with a genuine problem, a customer situation that needs you, a colleague asking for help. These are the job rather than an intrusion on it, and a manager visibly irritated at being interrupted for something real teaches their team to stop bringing things — which costs far more than the fifteen minutes. Protect the time from drift and habit, not from people.</p>"""
, [
 C("Which three items should survive a bad week?",
   ["The monthly reading, the competitor visit, the procedure page", "The count, the difficult conversation, the rota",
    "The numbers review, the walk, the messages", "Whatever is next in the diary"], 1,
   "Those three have consequences that compound if missed; the others do not."),
 C("A manager reading messages continuously is:",
   ["Responsive", "Available to everybody and present for nobody",
    "Well informed", "Efficient"], 1,
   "Twice a day at fixed points recovers more time than any other single change."),
 C("Covering absence weekly is:",
   ["Part of the job", "A staffing pattern rather than bad luck, and a case to make upward",
    "Unavoidable in retail", "A sign of a committed manager"], 1,
   "With the hours attached, it becomes a request somebody can act on.")]),

("Your first ninety days in a branch", 11, """<p>If you are new to a branch — promoted into it or moved — the routine above is where you are going, and the first three months are a different job.</p>

<p><b>The first two weeks: look, do not change.</b> Walk the floor at every hour of the day. Watch a delivery arrive. Stand by the queue on a Saturday. Read the numbers back a year. Meet every member of staff individually for ten minutes and ask what works, what does not, and what they would change.</p>

<p>The instinct is to demonstrate value by changing something quickly. Resist it for a fortnight — a change made in week one is made without information, and the credibility it costs when it is wrong is expensive to recover.</p>

<p><b>The exception, and it is the only one.</b> Anything unsafe is fixed immediately. Blocked exits, an electrical hazard, an unlocked safe. Those do not wait for you to understand the branch.</p>

<p><b>Weeks three to six: fix two things, visibly.</b> Chosen because they are quick, they matter to the team, and they are things people have already told you about. Fixing something your staff have complained about for a year does more for your standing than any amount of explaining your approach.</p>

<p><b>Weeks six to twelve: establish the rhythm.</b> The rota day. The weekly hour. The count. The daily walk. Start them now, while everything is new and nobody has expectations of how you work — habits established in the first quarter hold, and habits introduced in month eight are experienced as a change.</p>

<p><b>What to be careful about with your predecessor.</b> Do not criticise them, to anybody. Their arrangements may have had reasons you have not discovered yet, some of your team liked them, and a manager who arrives finding fault teaches everybody what will be said about them later.</p>

<p><b>And the thing new managers most often get wrong.</b> Trying to be liked in the first month. It is understandable, it produces decisions you will have to reverse, and it does not work — teams judge a new manager on whether they are fair, clear and reliable, and those take a quarter to demonstrate. Being liked is what happens afterwards, if it happens.</p>

<p><b>And tell your team what you are doing and why.</b> A new manager who starts a weekly count, a rota day and a protected hour without explanation is experienced as somebody imposing procedures. The same manager who says plainly in the first fortnight what they intend to change and what they are leaving alone is experienced as somebody with a plan — and the second version gets cooperation on the things that inconvenience people, which several of these do.</p>

<blockquote>IMPLEMENTATION TIP: Ask every member of staff the same three questions in your first fortnight — what works, what does not, what would you change. Write the answers down. The things mentioned by three or more people are your first two fixes, and they will be right.</blockquote>"""
, [
 C("A new manager should resist changing anything for a fortnight, except:",
   ["Obvious inefficiencies", "Anything unsafe",
    "Staffing problems", "Pricing errors"], 1,
   "A change made in week one is made without information."),
 C("Habits established in the first quarter hold; habits introduced in month eight are:",
   ["More considered", "Experienced as a change",
    "Better accepted", "Easier to justify"], 1,
   "Which is why the rhythm starts while everything is still new."),
 C("Criticising your predecessor to the team teaches everybody:",
   ["Your standards", "What will be said about them later",
    "The direction of travel", "That things will improve"], 1,
   "Their arrangements may have had reasons you have not discovered, and some of your team liked them.")]),

("Okelewo: a week at Sango", 11, """<p>An ordinary week at the branch with the lowest turnover in the group. Nothing in it is remarkable, which is the point — this is what the whole track looks like when it has become a routine rather than an intention.</p>

<p><b>Monday.</b> Fifteen minutes before opening: floor walk, float and shift checks, yesterday's numbers, and the day's one thing to whoever is on. Two deliveries. He covers a break and serves for twenty minutes. Somebody's shift request is answered the same morning with a no and a reason.</p>

<p><b>Tuesday.</b> The same fifteen minutes. The weekly count at ten, blind, done by the person who runs the tills rather than the storekeeper. Two differences, one investigated and one recorded as unexplained. He watches the lunchtime hour from the end of an aisle without serving, and notes that the second till opened nine minutes after the queue reached six.</p>

<p><b>Wednesday.</b> Rota published for the following week, as it has been for three years. The protected hour, two till three, phone off, in the back office with the door shut and the team told. Numbers written down and filed with the previous eleven weeks. Fifteen minutes on one cause: the chilled section thinning by four every afternoon, which turns out to be a fill slot nobody owns after two o'clock.</p>

<p><b>Thursday.</b> A difficult conversation at nine — a cashier late three times in a fortnight, four minutes, private, specific, with a follow-up date. He asks his deputy to decide something he would have decided himself, and does not revisit it. Afternoon fill slot assigned to a named person from today.</p>

<p><b>Friday.</b> The new starter's end-of-first-week conversation: what has been most confusing. He asks the counter staff which regulars they have not seen. Two names, one followed up. Short-dated stock walked and marked down.</p>

<p><b>What it added up to.</b> About four hours of deliberate management across a week of perhaps fifty. One cause fixed, one conversation had, one person developed, one number recorded, one problem noticed.</p>

<p><b>And what it did not include.</b> Any crisis, any dramatic intervention, any initiative. Sango's figures that week were unremarkable, as they usually are — which is what it looks like when a branch is being managed rather than rescued.</p>

<p><b>One thing to notice about the Thursday.</b> He asked his deputy to decide something he would have decided himself, and did not revisit it. That takes a few seconds, costs nothing, and is the only item in the week that builds anything for next year rather than this one. It is also the easiest of the whole list to skip, because nobody notices its absence — including the deputy, who simply carries on being somebody who covers.</p>

<blockquote>IMPLEMENTATION TIP: Compare that week with your own last one. Not to find fault — to see which of the five days contained anything that was not a reaction. For most managers the honest answer is none, and the gap between that and four hours is the whole of what this track is asking for.</blockquote>"""
, [
 C("Set against a working week of perhaps fifty hours, the deliberate management in Sango's week came to:",
   ["Twenty hours", "About four",
    "Half a day", "Fifteen hours"], 1,
   "One cause fixed, one conversation had, one person developed, one number recorded, one problem noticed."),
 C("Watching the lunchtime hour rather than serving produced:",
   ["A staffing complaint", "The observation that the second till opened nine minutes after the queue reached six",
    "A customer count", "A service score"], 1,
   "Specific enough to change the rota; a general sense that the queue felt slow would not have been."),
 C("Sango's figures that week were unremarkable, which is:",
   ["A concern", "What it looks like when a branch is managed rather than rescued",
    "A reason to intervene", "Typical of a quiet week"], 1,
   "The week contained no crisis, no dramatic intervention and no initiative.")]),

("What this track was asking for", 11, """<p>Nine modules, and they reduce to a small number of things.</p>

<p><b>Know what you are for (Module 1).</b> A supervisor makes today go well; a manager makes next quarter go well using today as evidence. Five things only you can do, and a busy week is not automatically a managerial one.</p>

<p><b>Know your numbers, including which ones lie (Module 2).</b> Sales in four parts. Margin, which the sales report will never mention. Contribution rather than allocated profit. And the most dangerous figure on any report is the one you are measured on.</p>

<p><b>Close the gap on the shelf (Module 3).</b> The largest recoverable loss in most branches, invisible in every report, with four causes needing four different fixes.</p>

<p><b>Build a team that stays (Module 4).</b> The slowest lever and the one that determines the others. A rota published on time does more for retention than anything else within a manager's gift.</p>

<p><b>Prevent loss by design (Module 5).</b> Make the honest thing easy. Count blind. And most suspicions turn out to be process failures.</p>

<p><b>Know who actually shops with you (Module 6).</b> Every decision suits one of your customers better than the others; the failure is not choosing, it is not noticing a choice was made.</p>

<p><b>Be heard where the decisions are made (Module 7).</b> Range, price, headcount and investment are decided elsewhere. Everything you get from the centre is drawn against a balance built by being right before.</p>

<p><b>Build something that survives you (Module 8).</b> A deputy who can decide, standards outside your head, and a handover that names what you did not fix.</p>

<p><b>Then do it on a rhythm (Module 9).</b> Because all of it is important and none of it is urgent.</p>

<p><b>The two outputs to judge yourself on.</b> Losses that did not happen, which are invisible and for which you will get no credit. And a branch that works when you are not in it. Neither appears in a report, both take a year, and they are what the job actually is.</p>

<p><b>And the sentence worth keeping.</b> Almost nothing in this track is clever. A rota on time, forty lines counted, a conversation held on the day, a number brought before it was asked for. It is available to anybody, it is what the best managers in this business are quietly already doing, and the reason it is worth learning is that so few people do it deliberately.</p>

<p><b>Where to go from here.</b> Nothing in this track needs a course to continue. The habits improve by being kept, the numbers become more useful the longer the series runs, and judgement builds from having made calls and seen how they turned out. What is worth adding is other people: a peer at another branch to compare notes with, and somebody senior who will tell you plainly when you are wrong. Those two do more for a manager over five years than any amount of material, including this.</p>

<blockquote>IMPLEMENTATION TIP: Pick three habits — not nine — and hold them for a quarter. The count, the rota day, and the protected hour are the three I would choose, because each is small, each is entirely within your control, and each produces something visible within six weeks.</blockquote>"""
, [
 C("The two outputs to judge yourself on are a branch that works without you, and:",
   ["Sales growth", "Losses that did not happen",
    "Staff satisfaction", "Findings closed"], 1,
   "Neither appears in a report, both take a year, and they are what the job actually is."),
 C("Of the nine modules' habits, how many should you take on at once?",
   ["All of them", "Three",
    "One per module", "Six"], 1,
   "The count, the rota day and the protected hour: each small, each within your control, each visible within six weeks."),
 C("The reason this material is worth learning is that:",
   ["It is difficult to master", "So few people do it deliberately",
    "It is not widely known", "It requires resources"], 1,
   "Almost nothing in the track is clever, and it is what the best managers are quietly already doing.")]),
]


QUESTIONS = [
 Q("Training of this kind fails because managers:", ["Disagree with it", "Agree with all of it and do none of it", "Lack the skills", "Are not supported"], 1,
   "Everything in it is important and none of it is urgent.", "Ch1 §1", "Rhythm"),
 Q("A rhythm beats a list because it:", ["Covers more", "Removes the daily decision", "Is easier to recall", "Can be shared"], 1,
   "You will always judge that the count is not the best use of the next twenty minutes.", "Ch1 §4", "Rhythm"),
 Q("A routine should be fixed to:", ["A frequency", "A day or a time", "A workload", "A target"], 1,
   "'Weekly' becomes fortnightly and then monthly; 'Tuesday after the delivery' holds.", "Ch1 §6", "Rhythm"),
 Q("Keeping two-thirds of the routine in a normal month is:", ["Inadequate", "A success", "The minimum", "A sign of overload"], 1,
   "The alternative to two-thirds is not all of it — it is none of it.", "Ch1 §9", "Rhythm"),
 Q("The commonest failure mode is:", ["Never starting", "Stopping once and treating that as the answer", "Doing too much", "Delegating it"], 1,
   "A lapsed routine is picked up on Monday, not abandoned and mourned.", "Ch1 §10", "Rhythm"),
 Q("The morning walk should follow:", ["A checklist", "The route a customer would take", "The stockroom first", "The rota"], 1,
   "You are looking at whether the branch looks like somewhere you would shop.", "Ch2 §3", "The day"),
 Q("The daily fifteen minutes should be done:", ["After messages", "Before opening your messages", "At the first quiet moment", "After the delivery"], 1,
   "Otherwise the first hour belongs to whoever wrote to you.", "Ch2 §9", "The day"),
 Q("The day's one thing said to whoever is on takes:", ["Five minutes", "Thirty seconds", "A briefing", "A written note"], 1,
   "It is the difference between a team that knows the day's shape and one that discovers it.", "Ch2 §6", "The day"),
 Q("The busiest hour should be:", ["Worked", "Watched at least twice a week", "Covered by a deputy", "Used for admin"], 1,
   "Serving during it removes the only person able to see the whole picture.", "Ch2 §8", "The day"),
 Q("The difficult conversation should happen:", ["At the weekly review", "The day it arises", "When there is time", "At the month end"], 1,
   "Postponed it becomes a week, then a month, and by then the standard has moved.", "Ch2 §9", "The day"),
 Q("How long is the weekly protected block?", ["Twenty minutes", "One hour", "Half a day", "Two hours"], 1,
   "It is where most of the change in a branch actually comes from.", "Ch3 §1", "The week"),
 Q("Fifteen minutes a week on causes amounts annually to:", ["Two hours", "Thirteen hours", "Fifty hours", "Five hours"], 1,
   "Most branch managers spend approximately none.", "Ch3 §6", "The week"),
 Q("The weekly hour is best scheduled:", ["Monday", "Mid-week after the delivery", "Friday", "Whenever quiet"], 1,
   "And the team should know it exists, so being unavailable is a known arrangement.", "Ch3 §7", "The week"),
 Q("Which weekly item verifies that the others are working?", ["The numbers", "The blind count", "The rota", "The cause work"], 1,
   "Counted by somebody who does not look after those lines.", "Ch3 §4", "The week"),
 Q("Weekly numbers should be kept rather than read because after twelve weeks you have:", ["A report", "A series rather than a snapshot", "An audit trail", "A benchmark"], 1,
   "You notice a departure in the week it starts rather than the quarter it shows up.", "Ch3 §3", "The week"),
 Q("Monthly work matters because weekly figures are:", ["Unavailable", "Noisy", "Incomplete", "Delayed"], 1,
   "A manager who only looks weekly is reacting to variation.", "Ch4 §1", "The month"),
 Q("Exception reports showing nothing are:", ["A wasted review", "A result", "A sign to look harder", "Evidence of a reporting fault"], 1,
   "You are looking for concentration rather than volume.", "Ch4 §4", "The month"),
 Q("Reading your own figures before the monthly meeting makes you:", ["Better prepared generally", "The person who knows rather than the person being told", "Faster in the meeting", "Less reliant on the pack"], 1,
   "Forty minutes beforehand changes which of the two you are.", "Ch4 §8", "The month"),
 Q("The monthly upward preparation brings margin, availability, losses and turnover:", ["If asked", "Before being asked", "Quarterly", "Only when adverse"], 1,
   "Plus one thing going wrong and one thing you need, with a number.", "Ch4 §6", "The month"),
 Q("Walking your branch with somebody else's eyes is needed because after a year:", ["Standards slip", "You have stopped seeing it", "The layout dates", "Staff stop noticing"], 1,
   "It is the only reliable way to see your own branch again.", "Ch4 §8", "The month"),
 Q("The quarterly half day should be spent:", ["In the branch office", "Away from the branch with the phone off", "At head office", "On the floor"], 1,
   "A manager in their own back office is interrupted within eleven minutes.", "Ch5 §8", "The quarter"),
 Q("Quarterly half days should be:", ["Taken when quiet", "Booked in advance with dates", "Requested each time", "Combined with leave"], 1,
   "Intended each quarter, they never happen.", "Ch5 §10", "The quarter"),
 Q("Before clearing dead stock you should decide:", ["The markdown level", "What goes into the space", "The disposal route", "Who approves it"], 1,
   "Otherwise you have converted one problem into a gap.", "Ch5 §6", "The quarter"),
 Q("A quarterly case should be timed to arrive:", ["When the problem is urgent", "Before your business decides its budgets", "At the year end", "With the quarterly report"], 1,
   "Measured for three weeks beforehand, priced, with what you have already done stated.", "Ch5 §3", "The quarter"),
 Q("Two days a year of quarterly half days produce:", ["Marginal gains", "Nearly everything achieved beyond keeping the shop running", "Compliance", "Reporting material"], 1,
   "The case that gets funded, the cause that gets fixed, the person who gets developed.", "Ch5 §9", "The quarter"),
 Q("Every question you answer that your team could answer:", ["Saves time", "Trains them to bring the next", "Builds trust", "Ensures consistency"], 1,
   "Ask what they think first — most of the time their answer is adequate.", "Ch6 §3", "Protecting time"),
 Q("Messages should be handled:", ["As they arrive", "Twice a day at fixed points", "Once weekly", "By the deputy"], 1,
   "Reading continuously makes you available to everybody and present for nobody.", "Ch6 §6", "Protecting time"),
 Q("Covering absence weekly indicates:", ["Commitment", "A staffing pattern rather than bad luck", "Poor rota discipline", "Seasonal pressure"], 1,
   "It is a case to make upward with the hours attached.", "Ch6 §5", "Protecting time"),
 Q("Which three survive a bad week?", ["The monthly read, the competitor visit, the procedure page", "The count, the difficult conversation, the rota", "The walk, the numbers, the messages", "Whatever is next in the diary"], 1,
   "Those three have consequences that compound if missed.", "Ch6 §8", "Protecting time"),
 Q("What should be decided in advance rather than in the moment?", ["The weekly slot", "What gets dropped when the week goes wrong", "The rota day", "The cause to work on"], 1,
   "In a bad week you will not be in any condition to rank them.", "Ch6 §10", "Protecting time"),
 Q("A new manager should change nothing for a fortnight except:", ["Obvious inefficiencies", "Anything unsafe", "Staffing", "Pricing"], 1,
   "A change made in week one is made without information.", "Ch7 §3", "First ninety days"),
 Q("Weeks three to six should be spent:", ["Reviewing figures", "Fixing two things visibly", "Restructuring", "Meeting head office"], 1,
   "Chosen because they are quick, they matter to the team, and people have already told you about them.", "Ch7 §4", "First ninety days"),
 Q("Habits introduced in month eight rather than the first quarter are:", ["Better informed", "Experienced as a change", "More readily accepted", "Easier to justify"], 1,
   "Habits established in the first quarter hold.", "Ch7 §5", "First ninety days"),
 Q("Criticising your predecessor teaches the team:", ["Your standards", "What will be said about them later", "The direction of travel", "That change is coming"], 1,
   "Some of your team liked them, and their arrangements may have had reasons.", "Ch7 §6", "First ninety days"),
 Q("New managers most often err by:", ["Changing too little", "Trying to be liked in the first month", "Being too formal", "Delegating too early"], 1,
   "Teams judge a new manager on whether they are fair, clear and reliable.", "Ch7 §7", "First ninety days"),
 Q("The three questions to ask every member of staff in your first fortnight are what works, what does not, and:", ["Who is difficult", "What would you change", "How are the figures", "What do you need"], 1,
   "Things mentioned by three or more people are your first two fixes.", "Ch7 §8", "First ninety days"),
 Q("Sango's week contained roughly how much deliberate management?", ["Twenty hours", "About four hours", "Half a day", "Twelve hours"], 1,
   "Across a week of perhaps fifty.", "Ch8 §7", "A week at Sango"),
 Q("The blind count at Sango was done by:", ["The storekeeper", "The person who runs the tills", "The manager", "A colleague from another branch"], 1,
   "Two differences, one investigated and one recorded as unexplained.", "Ch8 §3", "A week at Sango"),
 Q("Watching the lunchtime hour produced:", ["A staffing complaint", "The observation that the second till opened nine minutes late", "A customer count", "A service score"], 1,
   "Specific enough to change the rota.", "Ch8 §3", "A week at Sango"),
 Q("Sango's figures that week were unremarkable, which is what it looks like when a branch is:", ["Underperforming", "Managed rather than rescued", "Coasting", "Between initiatives"], 1,
   "No crisis, no dramatic intervention, no initiative.", "Ch8 §8", "A week at Sango"),
 Q("The two outputs to judge yourself on are losses that did not happen and:", ["Sales growth", "A branch that works when you are not in it", "Staff satisfaction", "Margin recovery"], 1,
   "Neither appears in a report and both take a year.", "Ch9 §11", "Closing"),
 Q("How many habits should you take on at once?", ["All nine", "Three", "One per module", "As many as fit"], 1,
   "The count, the rota day and the protected hour.", "Ch9 §13", "Closing"),
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

    rebalance(QUESTIONS, "retail:the_week:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:the_week:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 9 — The Manager's Week",
        "desc": ("Eight modules of habits against a job that generates interruptions faster "
                 "than anybody can absorb them. The daily fifteen minutes, the weekly hour, "
                 "the monthly two hours and the quarterly half day, what to drop when the "
                 "week goes wrong, your first ninety days in a branch, and an ordinary week "
                 "at a branch where all of it has become routine."),
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
