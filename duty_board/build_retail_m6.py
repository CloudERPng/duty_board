#!/usr/bin/env python3
"""Build 'Customers and the Local Market' into academy_retail_data.json.

Module 6 of Retail Leadership Essentials.

This is where the track most has to earn its claim to be written for this
market rather than adapted from somewhere else. Market days, month-end pay
cycles, traders paid daily against salaries paid monthly, school resumption,
the religious calendar, fuel scarcity, and competitors who are a table outside
your door and pay no rent — none of that is in a general retail course and all
of it determines what happens at a Nigerian branch on any given week.

Distinct from what this track already covers. Module 2 treated footfall,
conversion and basket as numbers. Module 3 covered availability and
findability. This module is about who the customers actually are, why they come
back, what service a branch can genuinely deliver, and the local conditions a
manager should be reading.

STANDS ALONE. No other module or track assumed.

Run from the app package directory:  python3 build_retail_m6.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "customers"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Who actually shops here", 11, """<p>Most branch managers can describe their customers in general terms and very few can describe them specifically. The difference matters, because almost every decision you make about range, hours, layout and staffing is a bet on who is coming through the door.</p>

<p><b>What you should be able to say without checking.</b> Who your busiest hour serves and why they come then. What proportion are regulars against passing trade. What they mostly buy together. Where they come from — walking, driving, from the bus stop, from the offices behind you. And what they buy elsewhere that they could buy from you.</p>

<p><b>How to find out, since almost none of it is in a report.</b> Stand still and watch for twenty minutes at three different hours. Ask your counter staff, who know the regulars by face and often by name. And ask customers, occasionally and lightly — most people will tell you why they came in if you sound interested rather than surveying them.</p>

<p><b>The catchment is smaller than managers assume.</b> For most branches the great majority of trade comes from a short distance — the streets around you, the workplaces within walking range, the transport that stops nearby. That is a useful discipline: it means your market is a specific and knowable set of people rather than a general public, and you can go and look at it.</p>

<p><b>Different customers at different hours, in the same shop.</b> Early morning is often people on their way somewhere. Midday can be workers from nearby offices. Late afternoon brings people going home, and weekends are a different population entirely. A branch staffed and stocked as though one customer type arrives all day is serving each of them slightly badly.</p>

<p><b>The question worth asking about anything you are considering.</b> Which of my customers is this for? A range change, a promotion, a layout decision, a change of hours — if the answer is "customers generally", it has not been thought through. The Ikeja promotions in chapter eight are exactly this failure.</p>

<p><b>And what your regulars are worth.</b> A customer who comes weekly and spends ₦6,000 is worth over ₦300,000 a year to your branch. Losing four of them quietly costs more than most of the things a manager spends their week worrying about, and nothing anywhere will tell you it happened.</p>

<blockquote>IMPLEMENTATION TIP: Write down, without checking anything, who your busiest hour serves and what they come for. Then stand and watch that hour twice. The gap between what you wrote and what you saw is the most useful twenty minutes available to you this month.</blockquote>

<p><b>And watch what people do not buy.</b> Somebody who picks a thing up, looks at the price and puts it back has told you something no report contains. So has the customer who asks for a size, a variant or a brand you do not carry — that request is a gap in your range rather than a failure of availability, and the two need entirely different responses. A branch that collects those requests for a month usually finds three or four lines it should be stocking and one it should not.</p>"""
, [
 C("A customer coming weekly and spending ₦6,000 is worth annually over:",
   ["₦72,000", "₦300,000", "₦24,000", "₦600,000"], 1,
   "Losing four of them quietly costs more than most of what a manager spends the week worrying about."),
 C("You are considering a promotion and the answer to 'which of my customers is this for' is 'customers generally'. That means:",
   ["It has broad appeal", "It has not been thought through",
    "It should be tested first", "The range is too narrow"], 1,
   "The Ikeja promotions are exactly this failure."),
 C("A branch stocked and staffed as though one customer type arrives all day is:",
   ["Efficient", "Serving each of them slightly badly",
    "Correctly simplified", "Following the average"], 1,
   "Early morning, midday, late afternoon and weekends are frequently different populations.")]),

("Why they come back", 11, """<p>Retail talks constantly about attracting customers and rarely about keeping them, which is the wrong way round: the customer you already have costs nothing to acquire and is the cheapest sale available to you.</p>

<p><b>The arithmetic that ought to change behaviour.</b> Twenty regulars spending ₦6,000 a week are ₦6.2m of annual sales. Replacing them requires attracting twenty new customers and persuading them to come back repeatedly, which is expensive and slow. Keeping them requires being reliably decent, which is neither.</p>

<p><b>What actually brings people back, roughly in order.</b></p>

<p><b>Having what they came for.</b> Availability is the largest single factor in retail loyalty and it is boring, which is why it gets less attention than it deserves.</p>

<p><b>Not being annoyed.</b> A queue that did not move, being ignored, a price at the till different from the shelf, an unhelpful response to a reasonable question. Customers tolerate a great deal and leave over accumulations of small friction.</p>

<p><b>Being recognised.</b> Not a loyalty scheme — a member of staff who knows a regular's face and says so. It costs nothing, cannot be bought, and is one of the few things a small branch can do better than a large chain.</p>

<p><b>Then price</b>, which matters enormously and which you do not control, and which is exactly why the first three deserve your attention.</p>

<p><b>How customers actually leave.</b> Not with a complaint. They come slightly less often, then buy fewer things, then stop — and every stage of that is invisible in your figures because your total sales absorb it. By the time a manager notices, the person has been gone for months and cannot be asked why.</p>

<p><b>Which means the signal to watch is not complaints.</b> It is whether your regulars are still regular. Your counter staff know this before any report does — ask them who they have not seen for a while, and follow up on two of the names.</p>

<p><b>The recovery that pays for itself.</b> A customer who has a bad experience and sees it put right properly frequently becomes more loyal than one who never had a problem. That is not a reason to create problems, and it is a reason to treat the ones you have as opportunities rather than as damage to be contained.</p>

<blockquote>WATCH-OUT: Customers leaving is the quietest thing that happens in a branch. Nobody complains, nothing appears in a report, and total sales hide it for months. The only early warning available to you is your staff noticing that a face has stopped appearing.</blockquote>

<p><b>A caution about loyalty schemes.</b> Where your business runs one, it will tell you what your enrolled customers do, which is not the same as what your customers do — the people who sign up are systematically your more committed shoppers. Useful for understanding your regulars, misleading if read as the whole picture. The passing trade and the occasional shopper are invisible in it, and they are frequently the group you are losing.</p>"""
, [
 C("Customers who stop shopping with you typically:",
   ["Complain first", "Come less often, buy less, then stop — invisible in the totals",
    "Tell a member of staff", "Switch suddenly"], 1,
   "By the time a manager notices, the person has been gone for months and cannot be asked why."),
 C("Of everything that brings a customer back, the one that outranks the rest is:",
   ["A competitive price", "Having what they came for",
    "Friendly staff", "A convenient layout"], 1,
   "It is boring, which is why it gets less attention than it deserves."),
 C("The early warning that a branch is losing regulars comes from:",
   ["The complaints log", "Staff noticing a face has stopped appearing",
    "The sales report", "Basket analysis"], 1,
   "Ask them who they have not seen for a while, and follow up on two of the names.")]),

("Service a branch can actually deliver", 11, """<p>Service in retail is usually discussed in language nobody can act on — delight the customer, go the extra mile. A branch manager needs something a tired member of staff can do at four on a Saturday.</p>

<p><b>The four things that constitute service in a shop</b>, and they are all specific.</p>

<p><b>Acknowledge people.</b> Eye contact and a word within a few seconds of somebody approaching, even when you cannot serve them yet. Most complaints about being ignored are about the seconds before service rather than the service.</p>

<p><b>Know the answer or find it.</b> "I don't know" is acceptable; "I don't know" followed by walking away is not. The standard is that nobody is left holding a question.</p>

<p><b>Do not argue about small amounts.</b> A dispute over ₦200 that costs a regular customer is a bad trade, and staff need to be told explicitly where their discretion ends — otherwise they will either give away too much or defend the ₦200 to the last.</p>

<p><b>Finish the transaction properly.</b> The last ten seconds are what people remember: the receipt handed rather than pushed, the bag packed sensibly, something said.</p>

<p><b>Why this is a management problem rather than a personality one.</b> Service collapses when staff are stretched, unclear about their authority, or dealing with a system that makes the right thing difficult. A cashier who cannot resolve a ₦200 shelf-price discrepancy without finding a supervisor will make the customer wait, and that is a design failure rather than an attitude failure.</p>

<p><b>Give explicit discretion and say what it is.</b> Up to a stated amount, your staff can settle a pricing dispute, replace a damaged item or make a small gesture without asking anybody. That single decision improves service more than any amount of instruction about attitude, and the amount can be small.</p>

<p><b>The rude customer, which staff need prepared before it happens.</b> Stay calm, do not match their tone, resolve what you can, and involve a supervisor at the point where you are being abused rather than merely complained at. Staff who have been told this in advance handle it; staff who have not either capitulate or escalate it, and both are worse.</p>

<blockquote>IMPLEMENTATION TIP: Decide the amount your staff may settle a dispute for without asking, tell them, and then support the decisions they make with it. The second half matters more than the first — a member of staff overruled once will never use the discretion again.</blockquote>

<p><b>What service does not mean.</b> Not agreeing with every complaint, not giving away goods to avoid a difficult conversation, and not standing while a member of your staff is abused. Firmness delivered politely is service; capitulation is not, and staff who watch a manager give in to whoever is loudest learn that the rules apply to reasonable customers only — which is unfair to the reasonable ones and to the staff.</p>"""
, [
 C("A cashier who cannot settle a ₦200 shelf-price dispute without finding a supervisor represents:",
   ["An attitude problem", "A design failure",
    "Correct control", "A training gap"], 1,
   "Service collapses when staff are unclear about their authority or the system makes the right thing difficult."),
 C("Having given staff discretion to settle small disputes, the part that matters more is:",
   ["Setting the limit correctly", "Supporting the decisions they make with it",
    "Recording each use", "Reviewing it monthly"], 1,
   "A member of staff overruled once will never use the discretion again."),
 C("Most complaints about being ignored concern:",
   ["The quality of service given", "The seconds before service",
    "Queue length", "Staff numbers"], 1,
   "Eye contact and a word within a few seconds, even when you cannot serve them yet.")]),

("The queue", 11, """<p>The queue is where most customers form their opinion of your branch, where you lose sales you never see, and where your staffing decisions become visible to the public.</p>

<p><b>What matters is not its length.</b> A queue of eight moving steadily is a better experience than a queue of three that has not moved because the person at the front has a problem. Customers tolerate waiting and do not tolerate waiting without apparent progress.</p>

<p><b>The abandoned queue is a pure invisible loss.</b> Somebody who leaves a full basket appears in no report you will ever read, and they are the customer most likely not to come back — they have already spent the time and got nothing for it.</p>

<p><b>Four things that fix most queue problems, none requiring more staff.</b></p>

<p><b>Open a till before you need it, not after.</b> By the time a queue has formed, opening a second till clears it slowly. Watching the shape of the trade and opening a minute early is a different experience for everybody.</p>

<p><b>Move the problem transaction sideways.</b> A price check, a dispute, a complicated return blocks everybody behind it. Resolving it away from the till, or at another point, is nearly always possible and almost never done.</p>

<p><b>Acknowledge the queue.</b> A member of staff who says the wait is noticed and being dealt with changes the experience substantially without shortening it by a second.</p>

<p><b>Staff to the shape of the day, not the average.</b> Most branches have two or three predictable peaks and are staffed evenly across the day. Comparing your hourly transactions to your hourly staffing for one week shows it plainly and usually costs nothing to fix.</p>

<p><b>What a manager should personally do.</b> Stand near the queue at your busiest hour and watch, without serving. You are looking for what stops it moving, how many people leave, and whether anybody is doing anything about either. Serving on the till at that hour feels helpful and prevents you seeing any of it — you become part of the queue rather than somebody able to fix it.</p>

<p><b>And the cost, roughly.</b> If five people abandon a queue on a Saturday with baskets averaging ₦5,000, that is ₦25,000 of sales lost in an afternoon on a branch with staff standing in the wrong place. Over a year of Saturdays it is a substantial number, and it has never appeared in any report anybody has shown you.</p>

<blockquote>WATCH-OUT: Working the till at your busiest hour is the most natural thing a capable manager does and it removes the only person in the branch who can see the whole picture. Watch the hour before you decide to work it.</blockquote>

<p><b>Where the second queue forms that nobody counts.</b> The customer service point, the deli or cut counter, the collection desk. These are frequently staffed by one person who also has other duties, and a wait there is invisible to anybody watching the tills. If your branch has such a point, watch it separately — it is often the worst experience in the shop and the one least often measured.</p>"""
, [
 C("Which is the better customer experience?",
   ["A queue of three that has not moved", "A queue of eight moving steadily",
    "Two queues of four", "A queue with a greeter"], 1,
   "Customers tolerate waiting and do not tolerate waiting without apparent progress."),
 C("Working the till yourself at the busiest hour:",
   ["Is the best use of a manager", "Removes the only person who can see the whole picture",
    "Reduces the queue fastest", "Sets the right example"], 1,
   "Watch the hour before you decide to work it."),
 C("Five abandoned baskets averaging ₦5,000 on a Saturday afternoon cost:",
   ["Nothing measurable", "₦25,000, appearing in no report",
    "Five transactions", "A day's margin"], 1,
   "On a branch with staff standing in the wrong place, repeated across a year of Saturdays.")]),

("Complaints, and the ones you never hear", 11, """<p>For every customer who complains, a considerably larger number simply leave. That single fact should change how a branch treats the ones who do speak up: they are a small, self-selected group doing you a favour.</p>

<p><b>What a complaint actually is.</b> Information you would otherwise have paid for, delivered free, by somebody sufficiently invested in your branch to bother. Most retail complaints are also about something specific and fixable rather than about the branch in general.</p>

<p><b>Handling one, and it takes four steps.</b> Listen without interrupting or explaining. Acknowledge the specific thing that went wrong. Fix what can be fixed now. And say what will stop it recurring, where you can honestly say anything.</p>

<p><b>The step that gets skipped is the first.</b> Staff and managers begin explaining while the customer is still speaking — the delivery was late, the system was down, we are short-staffed. All of it may be true and none of it is what the person is there for, and interrupting to explain converts a complaint into an argument.</p>

<p><b>What not to do.</b> Do not argue about whether it happened. Do not handle it where other customers are listening if it can be moved. Do not promise something you cannot deliver in order to end the conversation, which buys ten minutes and costs the relationship when it does not happen.</p>

<p><b>Record them, even the small ones.</b> Three complaints about the same thing is a pattern and a single one is an incident, and you cannot tell which you have without a record. A notebook by the till is sufficient — the point is that they exist somewhere other than in the memory of whoever was on duty.</p>

<p><b>The complaints that never reach you.</b> Most dissatisfaction is expressed to a member of staff and goes no further, or to nobody at all. Asking your team weekly what customers have grumbled about surfaces far more than any formal channel, because grumbling is what most people actually do.</p>

<p><b>And a note about complaints on the phone or online.</b> They are public in a way a counter complaint is not, and they reach people who have never been to your branch. Whatever your business's arrangements, the branch-level rule is the same: respond quickly, do not argue in public, and move the specifics somewhere private.</p>

<blockquote>IMPLEMENTATION TIP: Ask your team once a week what customers have grumbled about, and write the answers down. It takes two minutes, it surfaces the complaints that never become complaints, and it is the only way to find out about the problem everybody has been apologising for and nobody has mentioned to you.</blockquote>

<p><b>Close the loop with the person who raised it.</b> Where a complaint leads to something changing, tell them if you can — and tell the member of staff who received it either way. A team that never hears what happened to a complaint concludes that reporting them achieves nothing, and stops passing them on, which removes your best source of information about the branch.</p>"""
, [
 C("A customer who complains is best understood as:",
   ["A problem to contain", "A small self-selected group doing you a favour",
    "A risk to the branch's reputation", "An exception"], 1,
   "For every one who complains, a considerably larger number simply leave."),
 C("The most commonly skipped step in handling a complaint is:",
   ["Fixing it", "Listening without explaining",
    "Apologising", "Following up"], 1,
   "Interrupting to explain, however true the explanation, converts a complaint into an argument."),
 C("Asking your team weekly what customers have grumbled about works better than a formal channel because:",
   ["It is faster", "Grumbling is what most people actually do",
    "Staff are more accurate", "It avoids paperwork"], 1,
   "Most dissatisfaction is expressed to a member of staff and goes no further.")]),

("Your competitors, honestly", 11, """<p>Most branch managers know their competitors exist and could not tell you specifically what they do better. That is a gap worth closing, because your customers make the comparison constantly whether or not you do.</p>

<p><b>Who you are actually competing with.</b> Not only the similar shop down the road. The open market, the trader with a table outside, the person selling from a kiosk, the supermarket a bus ride away, and increasingly whatever can be delivered. Each takes a different part of your trade, and a manager who thinks only about the formal competitor is missing most of it.</p>

<p><b>The informal competitor deserves specific attention.</b> A trader outside your door pays no rent, no staff, no electricity and no tax, and can undercut you on any single line. You will not win on price and it is a waste of energy to try. What you have is availability, range, consistency, a receipt, being open when you say you will be, and somewhere to come back to if something is wrong. Those are real advantages and most branches never say them out loud to their own staff.</p>

<p><b>Go and look, properly, twice a year.</b> Walk your competitors as a customer. What is their range, their pricing on the twenty lines that matter to you, their availability, their queue, their staff? Half an hour each. Almost no branch manager does this and every one who does comes back with something specific.</p>

<p><b>What to bring back.</b> Not a general impression that they are cheaper. Specific comparisons on lines that matter, something they do better that you could copy this month, and something you do better that your team should know about.</p>

<p><b>Watch for the change rather than the state.</b> A competitor's prices are what they are. A competitor who has just extended their hours, taken on staff, refitted, or started stocking your best category has done something, and that is what will show up in your figures next quarter.</p>

<p><b>And be honest upward about what you cannot match.</b> If a competitor's pricing on a key category is genuinely lower and you are losing that trade, saying so with the specifics is useful information for whoever sets your prices. Saying it vaguely as an excuse for a sales shortfall is not, and the difference is entirely in whether you have the numbers.</p>

<blockquote>IMPLEMENTATION TIP: Visit two competitors this quarter and price twenty lines that matter to you. It takes an hour, it is the only way to know whether the price complaints you hear are accurate, and it converts a general anxiety about competition into a specific list somebody can act on.</blockquote>

<p><b>Take somebody with you.</b> A supervisor or a senior member of staff walking a competitor with you sees things you will not, argues with your conclusions usefully, and comes back invested in what you do about it. It is also one of the few pieces of development available to a branch that costs nothing — and a person who has walked a competitor understands why your own standards matter in a way no briefing achieves.</p>"""
, [
 C("Against a trader outside your door paying no rent or staff, competing on price is:",
   ["Necessary on key lines", "A waste of energy",
    "Possible with approval", "The only option"], 1,
   "What you have is availability, range, consistency, a receipt, and somewhere to come back to."),
 C("When looking at a competitor, what matters more than their current state is:",
   ["Their pricing", "What has changed — new hours, staff, a refit, a new category",
    "Their size", "Their staff numbers"], 1,
   "That is what will show up in your figures next quarter."),
 C("Reporting that a competitor is cheaper becomes useful rather than an excuse when:",
   ["It is raised early", "You have the specific line-by-line numbers",
    "Sales have fallen", "Your manager asks"], 1,
   "The difference is entirely in whether you have done the comparison.")]),

("Reading your local calendar", 11, """<p>Trade in this market is shaped by a calendar that no national sales report reflects, and a manager who knows their own version of it can staff, order and plan against it instead of being surprised by it every year.</p>

<p><b>The pay cycle, which is the strongest single pattern.</b> Salaried customers concentrate spending in the days after month-end and thin out sharply toward the end of the month. Traders and daily-paid customers spend far more evenly. The mix of the two in your catchment determines the shape of your month, and it is worth knowing which you have — a branch serving offices behaves nothing like one serving a market.</p>

<p><b>Market days.</b> Where a local market runs on particular days, footfall and basket both move, and often in opposite directions — more people, smaller baskets, or the reverse. It is local, it is entirely predictable, and it should be in your rota.</p>

<p><b>School terms and resumption.</b> Resumption weeks change what sells and compress spending on everything else. The date is known months ahead and most branches are still surprised.</p>

<p><b>The religious calendar.</b> Ramadan and the Eid period, Christmas and Easter each change trading hours, what sells, when people shop, and staff availability. In a mixed catchment two calendars operate at once. Your own branch's pattern is knowable from last year if anybody wrote it down.</p>

<p><b>Fuel, power and transport.</b> A fuel shortage, a road closure, or an extended outage changes footfall within a day and is the commonest cause of a week that makes no sense. Worth noting on the day rather than reconstructing at month end, because in three weeks nobody will remember which week it was.</p>

<p><b>Weather</b>, particularly heavy rain, which suppresses footfall sharply and briefly and then produces a compensating day afterwards.</p>

<p><b>What to do with all of it.</b> Keep a simple record: what happened, what week, what the figures did. One line a week. After a year you have your branch's own calendar, which is worth more than any general advice about seasonality because it is about your catchment rather than about retail in general.</p>

<p><b>And use it forwards.</b> Most managers explain the past with these factors and few plan with them. Resumption week is on a date, month-end is on a date, the market day is every week — staffing and ordering against them is available to anybody who looks a fortnight ahead.</p>

<blockquote>IMPLEMENTATION TIP: Keep one line a week for a year: the week, anything unusual locally, and what sales did. It costs a minute a week and it produces a calendar for your specific branch that nobody else in the business has, including the people who set your targets.</blockquote>

<p><b>Use it in the conversation about your target too.</b> A branch whose catchment is heavily salaried will miss a monthly target set evenly across the weeks and recover it in the last few days, every month, and a manager who can say that with a year of their own records is in a far better position than one explaining it afresh each time. The record is not only for planning — it is the evidence that your pattern is structural rather than a performance problem.</p>"""
, [
 C("A branch serving nearby offices and one serving a market differ mainly because of:",
   ["Range preferences", "The pay cycle — salaried spending concentrates after month-end, daily-paid spreads evenly",
    "Opening hours", "Basket size"], 1,
   "The mix in your catchment determines the shape of your month."),
 C("The commonest cause of a trading week that makes no sense is:",
   ["A competitor promotion", "Fuel, power or transport disruption",
    "A pricing change", "Staff shortage"], 1,
   "Worth noting on the day, because in three weeks nobody will remember which week it was."),
 C("Most managers use the local calendar to:",
   ["Plan a fortnight ahead", "Explain the past rather than plan with it",
    "Set targets", "Negotiate with head office"], 1,
   "Resumption week is on a date, month-end is on a date, and the market day is every week.")]),

("Okelewo: who Ikeja was actually selling to", 11, """<p>Module 2 followed the Ikeja manager's promotions — sales up nine per cent, margin down two points, a net loss of about ₦2.4m across three quarters. This chapter is about the question nobody asked at the time: who were the promotions for?</p>

<p><b>What the catchment turned out to be.</b> The branch sits between a cluster of offices and a busy transport stop. Two distinct populations: office workers at midday buying small and specific, and commuters in the late afternoon buying for home. Weekend trade is a third group again, largely families from the surrounding streets.</p>

<p><b>What the promotions were.</b> Multi-buy offers on bulk household lines, run at full-week duration, promoted in-store from the entrance.</p>

<p><b>Who those were for.</b> The weekend family shopper, who is roughly a fifth of the branch's trade. The midday office customer will not carry a multi-buy back to work, and the commuter is standing with a bag on a crowded bus. Four-fifths of the branch's traffic was structurally unable to take up the offer, and a third of the volume that did came from customers who would have bought the line anyway.</p>

<p><b>So the branch discounted heavily to its own regulars for goods they were already buying</b>, while the two populations that make up most of its trade saw a display in the entrance that was not aimed at them.</p>

<p><b>What the same money would have done.</b> The midday customer buys small, quickly, and at a predictable hour — that population responds to availability and speed rather than to price, and the branch was thinnest on exactly the lines they bought, at exactly the hour they arrived. Nothing about that required a discount.</p>

<p><b>The manager's own account afterwards.</b> He had never been asked who his customers were, only what his sales were. He knew the branch was busy at midday and had never thought about it as a different customer with different needs, because nothing in his reporting or his monthly conversation had ever prompted the question.</p>

<p><b>What changed.</b> Promotions chosen by which population they suit and run at the hours those people are present. Midday stocking and staffing built around the office customer. A quarter later, sales were up on a smaller promotional spend and margin had recovered a point and a half.</p>

<blockquote>IMPLEMENTATION TIP: Take your last promotion and ask which of your customer populations it was for, and what proportion of your trade they represent. If the honest answer is a minority, that is where a large share of your promotional money went — and it is a question that takes two minutes and is almost never asked.</blockquote>

<p><b>The general lesson from Ikeja, which is not about promotions.</b> A branch has more than one customer, and almost every decision suits one of them better than the others. That is unavoidable and it should be deliberate — the failure at Ikeja was not choosing the weekend shopper, it was never noticing that a choice was being made. Whenever you change anything, name who it is for and name who it is not for. The second half is the part that gets skipped.</p>"""
, [
 C("Ikeja's multi-buy promotions were structurally unsuited to:",
   ["The weekend family shopper", "The midday office customer and the afternoon commuter, who are four-fifths of trade",
    "All of its customers", "The transport-stop trade only"], 1,
   "One will not carry a multi-buy back to work and the other is standing on a crowded bus."),
 C("The midday office population responds to:",
   ["Price promotions", "Availability and speed",
    "Range breadth", "Loyalty offers"], 1,
   "The branch was thinnest on exactly their lines at exactly their hour, and nothing about that required a discount."),
 C("The Ikeja manager had never thought about midday as a different customer because:",
   ["He was inexperienced", "Nothing in his reporting or monthly conversation had ever prompted the question",
    "The data was unavailable", "Head office set the promotions"], 1,
   "He had been asked what his sales were, never who his customers are.")]),

("The customer routine", 11, """<p>This is the chapter to keep. All of it is watching and asking rather than analysing, and all of it is free.</p>

<p><b>Weekly.</b> Twenty minutes standing still at a busy hour, not serving — watching what stops the queue, who is leaving, and what people are looking for. And two minutes asking your team what customers have grumbled about this week, written down.</p>

<p><b>Weekly, one line.</b> What happened locally, and what sales did. A market day, a fuel queue, heavy rain, a road closed, resumption week. After a year it is your branch's own calendar.</p>

<p><b>Monthly.</b> Ask your counter staff which regulars they have not seen for a while, and follow up on two names. Read your recorded complaints as a set rather than as incidents, looking for the same thing appearing three times.</p>

<p><b>Quarterly.</b> Walk two competitors as a customer and price twenty lines that matter. Look at your last promotion and ask which population it was for. And ask, of your catchment, whether anything has changed — a new employer, a closed one, a road, a competitor opening.</p>

<p><b>And once, then whenever it changes.</b> Write down who your customers are by hour and by day, and what each group comes for. It is the document every other decision in this module depends on, almost no branch has it, and it takes an afternoon of watching to produce.</p>

<p><b>What this is worth.</b> Nothing here produces a number you can put in a report, which is why it gets skipped. What it produces is a manager who can answer why the figures moved, which promotions to run, when to staff, and which customers are quietly leaving — and those four answers are worth more over a year than most of the analysis a branch manager is asked for.</p>

<p><b>The one to start with.</b> Twenty minutes standing still at your busiest hour, this week, not serving. Almost every manager who does it for the first time comes back with something they had been walking past for a year.</p>

<blockquote>WATCH-OUT: Every habit in this module competes with something urgent and loses, because none of it is urgent and all of it is important. If it is not in the week deliberately, it will not happen — and unlike the figures, nothing will ever remind you that it did not.</blockquote>

<p><b>What to do with what the watching tells you.</b> Write it down at the time, on the floor, in a sentence — three or four specific observations rather than a general impression. Specific ones can be assigned to somebody with a date. A general sense that the queue felt slow on Saturday changes nothing; “the second till was opened eleven minutes after the queue reached six, twice” changes the rota.</p>"""
, [
 C("Your busiest hour is about to start and the queue is building. The routine asks you to spend it:",
   ["On the till, where you are most useful", "Standing still and watching, not serving",
    "Reviewing the day's figures", "Briefing the team"], 1,
   "Watching what stops the queue, who is leaving, and what people are looking for."),
 C("Nothing in the customer routine produces a number for a report, which is why it:",
   ["Should be delegated", "Gets skipped",
    "Is done quarterly", "Belongs to head office"], 1,
   "What it produces is a manager who can answer why the figures moved and which customers are quietly leaving."),
 C("The document every other decision in this module depends on is:",
   ["The complaints log", "Who your customers are by hour and by day, and what each comes for",
    "The competitor price list", "The local calendar"], 1,
   "Almost no branch has it, and it takes an afternoon of watching to produce.")]),
]


QUESTIONS = [
 Q("A weekly customer spending ₦6,000 is worth annually over:", ["₦72,000", "₦300,000", "₦24,000", "₦150,000"], 1,
   "Losing four quietly costs more than most of what a manager spends the week worrying about.", "Ch1 §7", "Who shops here"),
 Q("For most branches the great majority of trade comes from:", ["A wide catchment", "A short distance — the streets, workplaces and transport nearby", "Passing traffic", "Weekend visitors"], 1,
   "Your market is a specific and knowable set of people rather than a general public.", "Ch1 §4", "Who shops here"),
 Q("A branch staffed and stocked for one customer type all day is:", ["Efficient", "Serving each group slightly badly", "Correctly simplified", "Following demand"], 1,
   "Early morning, midday, late afternoon and weekends are frequently different populations.", "Ch1 §5", "Who shops here"),
 Q("The question to ask of any range, layout or promotion decision is:", ["What will it cost?", "Which of my customers is this for?", "Has it worked elsewhere?", "What does head office say?"], 1,
   "If the answer is 'customers generally', it has not been thought through.", "Ch1 §6", "Who shops here"),
 Q("Most of what you need to know about your customers is found by:", ["Analysing basket data", "Standing still and watching, and asking your counter staff", "Surveying", "Reviewing loyalty records"], 1,
   "Almost none of it is in a report.", "Ch1 §3", "Who shops here"),
 Q("The largest single factor in retail loyalty is:", ["Price", "Having what they came for", "Staff friendliness", "Location"], 1,
   "It is boring, which is why it gets less attention than it deserves.", "Ch2 §4", "Retention"),
 Q("Customers leaving a branch typically:", ["Complain first", "Come less often, buy less, then stop", "Switch suddenly", "Tell staff why"], 1,
   "Every stage is invisible because total sales absorb it.", "Ch2 §8", "Retention"),
 Q("Being recognised by a member of staff is valuable partly because it is:", ["Cheap to systematise", "One of the few things a small branch does better than a large chain", "Measurable", "Expected"], 1,
   "It costs nothing and cannot be bought.", "Ch2 §6", "Retention"),
 Q("A customer whose bad experience is put right properly frequently becomes:", ["Neutral", "More loyal than one who never had a problem", "A repeat complainer", "Price-sensitive"], 1,
   "A reason to treat problems as opportunities rather than damage to be contained.", "Ch2 §10", "Retention"),
 Q("The early warning of losing regulars is:", ["Falling sales", "Staff noticing a face has stopped appearing", "Complaints rising", "Basket size falling"], 1,
   "Ask them who they have not seen for a while.", "Ch2 §9", "Retention"),
 Q("Most complaints about being ignored are about:", ["The service received", "The seconds before service", "Queue length", "Product knowledge"], 1,
   "Eye contact and a word within a few seconds, even when you cannot serve them yet.", "Ch3 §3", "Service"),
 Q("The standard when a member of staff does not know an answer is that:", ["They say so", "Nobody is left holding a question", "They guess helpfully", "They call a supervisor"], 1,
   "'I don't know' is acceptable; 'I don't know' followed by walking away is not.", "Ch3 §4", "Service"),
 Q("A cashier unable to settle a ₦200 shelf-price dispute alone is:", ["Correctly controlled", "A design failure", "Following policy", "Undertrained"], 1,
   "Service collapses when staff are unclear about their authority.", "Ch3 §7", "Service"),
 Q("Having granted discretion to settle small disputes, the harder part is:", ["Setting the amount", "Supporting the decisions staff make with it", "Recording use", "Reviewing it"], 1,
   "A member of staff overruled once will never use it again.", "Ch3 §8", "Service"),
 Q("Staff should involve a supervisor with a difficult customer at the point they are:", ["Complained at", "Being abused", "Contradicted", "Delayed"], 1,
   "Staff told this in advance handle it; staff who have not either capitulate or escalate.", "Ch3 §9", "Service"),
 Q("What matters about a queue is not its length but:", ["Its speed of formation", "Whether it is visibly moving", "The number of tills", "The time of day"], 1,
   "Customers tolerate waiting and do not tolerate waiting without apparent progress.", "Ch4 §2", "The queue"),
 Q("A second till should be opened:", ["When the queue reaches five", "Before you need it", "At peak hours only", "When a customer complains"], 1,
   "By the time a queue has formed, a second till clears it slowly.", "Ch4 §5", "The queue"),
 Q("A price check or complicated return at the till should be:", ["Handled quickly in place", "Moved sideways, away from the till", "Deferred", "Escalated"], 1,
   "It blocks everybody behind it, and moving it is nearly always possible and almost never done.", "Ch4 §6", "The queue"),
 Q("Working the till at your busiest hour:", ["Is the best use of a manager", "Removes the only person who can see the whole picture", "Reduces the wait fastest", "Sets an example"], 1,
   "You become part of the queue rather than somebody able to fix it.", "Ch4 §9", "The queue"),
 Q("Five abandoned baskets averaging ₦5,000 cost:", ["Nothing recorded", "₦25,000, appearing in no report", "Five transactions", "A day's margin"], 1,
   "Repeated across a year of Saturdays it is a substantial number.", "Ch4 §10", "The queue"),
 Q("A customer who complains should be understood as:", ["A risk", "A small self-selected group doing you a favour", "An exception", "A reputational threat"], 1,
   "For every one who complains, a considerably larger number simply leave.", "Ch5 §1", "Complaints"),
 Q("The step most often skipped when handling a complaint is:", ["Fixing it", "Listening without explaining", "Apologising", "Recording it"], 1,
   "Interrupting to explain converts a complaint into an argument, however true the explanation.", "Ch5 §4", "Complaints"),
 Q("Promising something you cannot deliver to end a complaint:", ["Buys useful time", "Buys ten minutes and costs the relationship", "Is acceptable if minor", "Defuses the situation"], 1,
   "It fails when the promise does not happen.", "Ch5 §5", "Complaints"),
 Q("Three complaints about the same thing is a pattern; one is an incident. You cannot tell which without:", ["A formal channel", "A record", "A manager present", "A survey"], 1,
   "A notebook by the till is sufficient — the point is that they exist outside somebody's memory.", "Ch5 §6", "Complaints"),
 Q("Asking staff weekly what customers grumbled about works because:", ["Staff recall better", "Grumbling is what most people actually do", "It avoids forms", "It is quicker"], 1,
   "Most dissatisfaction is expressed to a member of staff and goes no further.", "Ch5 §7", "Complaints"),
 Q("Competing on price against a trader with no rent, staff or electricity is:", ["Necessary on key lines", "A waste of energy", "Possible selectively", "Head office's decision"], 1,
   "What you have is availability, range, consistency, a receipt and somewhere to come back to.", "Ch6 §3", "Competitors"),
 Q("Competitors should be walked as a customer:", ["Monthly", "Twice a year", "When sales fall", "Annually"], 1,
   "Half an hour each, and almost no branch manager does it.", "Ch6 §4", "Competitors"),
 Q("What matters more than a competitor's current state is:", ["Their pricing", "What has changed", "Their size", "Their range"], 1,
   "New hours, staff, a refit or a new category will show in your figures next quarter.", "Ch6 §6", "Competitors"),
 Q("Reporting that a competitor is cheaper is useful rather than an excuse when you have:", ["Raised it early", "The line-by-line numbers", "Falling sales", "Customer feedback"], 1,
   "The difference is entirely in whether you have done the comparison.", "Ch6 §7", "Competitors"),
 Q("What to bring back from a competitor visit is:", ["A general impression", "Specific comparisons, something to copy, and something you do better", "Their price list", "A photograph"], 1,
   "Not a general impression that they are cheaper.", "Ch6 §5", "Competitors"),
 Q("The strongest single pattern in the local calendar is:", ["Weather", "The pay cycle", "Market days", "School terms"], 1,
   "Salaried spending concentrates after month-end; daily-paid customers spread evenly.", "Ch7 §2", "Local calendar"),
 Q("A branch serving offices behaves differently from one serving a market because of:", ["Range", "The mix of salaried and daily-paid customers", "Opening hours", "Competition"], 1,
   "It determines the shape of your month.", "Ch7 §2", "Local calendar"),
 Q("School resumption weeks are:", ["Unpredictable", "Known months ahead, and most branches are still surprised", "Only relevant to some ranges", "Handled centrally"], 1,
   "They change what sells and compress spending on everything else.", "Ch7 §4", "Local calendar"),
 Q("Fuel, power or transport disruption should be noted:", ["At month end", "On the day", "In the quarterly review", "Only if severe"], 1,
   "In three weeks nobody will remember which week it was.", "Ch7 §6", "Local calendar"),
 Q("Most managers use local calendar factors to:", ["Plan ahead", "Explain the past", "Set targets", "Negotiate"], 1,
   "Resumption week is on a date, month-end is on a date, the market day is every week.", "Ch7 §9", "Local calendar"),
 Q("Ikeja's promotions suited which of its populations?", ["The midday office customer", "The weekend family shopper, about a fifth of trade", "The afternoon commuter", "All three"], 1,
   "Four-fifths of traffic was structurally unable to take up a multi-buy.", "Ch8 §4", "Okelewo Ikeja"),
 Q("A third of the promotional volume at Ikeja came from:", ["New customers", "Customers who would have bought the line anyway", "Bulk buyers", "Passing trade"], 1,
   "The branch discounted heavily to its own regulars for goods they were already buying.", "Ch8 §4", "Okelewo Ikeja"),
 Q("The midday office population would have responded to:", ["A deeper discount", "Availability and speed", "A loyalty offer", "Extended hours"], 1,
   "The branch was thinnest on their lines at exactly their hour, and nothing about that required a discount.", "Ch8 §5", "Okelewo Ikeja"),
 Q("The Ikeja manager had never considered midday a distinct customer because:", ["He was new", "Nothing in his reporting or monthly conversation prompted the question", "The data did not exist", "Promotions were central"], 1,
   "He had been asked what his sales were, never who his customers are.", "Ch8 §6", "Okelewo Ikeja"),
 Q("After the change, Ikeja's sales rose on a smaller promotional spend and margin recovered by:", ["Half a point", "A point and a half", "Three points", "Nothing yet"], 1,
   "Promotions chosen by which population they suit, run at the hours those people are present.", "Ch8 §7", "Okelewo Ikeja"),
 Q("The weekly twenty minutes should be spent:", ["Serving at the peak", "Standing still and watching", "Reviewing reports", "Briefing staff"], 1,
   "Watching what stops the queue, who leaves, and what people are looking for.", "Ch9 §2", "The routine"),
 Q("The customer routine gets skipped because none of it:", ["Takes long", "Produces a number for a report", "Requires approval", "Involves the team"], 1,
   "What it produces is a manager who can answer why the figures moved.", "Ch9 §7", "The routine"),
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
    rebalance(QUESTIONS, "retail:customers:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:customers:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 6 — Customers and the Local Market",
        "desc": ("Who actually shops at your branch, why they come back, and the local "
                 "conditions that shape your trade. Service a tired member of staff can "
                 "deliver on a Saturday, the queue, the complaints you never hear, "
                 "competitors including the ones paying no rent, and the pay cycle, market "
                 "days and calendar no national report reflects."),
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
