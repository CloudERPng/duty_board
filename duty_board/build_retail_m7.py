#!/usr/bin/env python3
"""Build 'Managing Upward and Across' into academy_retail_data.json.

Module 7 of Retail Leadership Essentials.

Module 1 named representing the branch upward as one of the five things only a
branch manager can do, and left it there. This module is the how.

The framing that keeps it out of politics: a branch manager controls a small
area and depends on decisions made elsewhere for range, price, headcount,
systems and investment. Getting those decisions to reflect what is true at your
branch is not manoeuvring — it is the part of the job that determines whether
the other six modules can be acted on at all.

STANDS ALONE. No other module or track assumed.

Run from the app package directory:  python3 build_retail_m7.py
"""

import collections
import io
import json
import os
import random
import re

KEY = "upward"
DATA = "academy_retail_data.json"

C = lambda q, opts, ans, why: {"q": q, "opts": opts, "ans": ans, "why": why}
Q = lambda q, opts, ans, why, src, topic: {
    "q": q, "opts": opts, "ans": ans, "why": why, "src": src, "topic": topic}


LESSONS = [
("Why this is a skill rather than politics", 11, """<p>Branch managers are often uncomfortable with the idea of managing upward, because it sounds like manoeuvring. It is the opposite: the alternative to doing it well is a business making decisions about your branch on worse information than it could have had.</p>

<p><b>The structural fact underneath.</b> You control availability, service, loss and your team. You do not control range, price, headcount, systems or investment. Every one of those is decided by somebody who has never served a customer at your counter, using data that reaches them in summary — and their decision then constrains everything you can do.</p>

<p><b>So the question is not whether to influence those decisions.</b> It is whether the person making them hears an accurate account of your branch or a vague one, and that is entirely within your control.</p>

<p><b>What head office actually knows about your branch.</b> Your sales against target. Possibly your stock figure and your losses. That is usually the whole of it. They do not know that your delivery arrives at your busiest hour, that a competitor opened in March, that your best category is out of stock nine days a month, or that your storeroom cannot be organised because of how it was built. None of that reaches anybody unless you send it.</p>

<p><b>The credibility account, which is the whole mechanism.</b> Everything you get from the centre — a decision, an exception, a piece of investment, the benefit of the doubt in a bad quarter — is drawn against a balance built by being right before. It is built slowly, by accurate reporting, requests that turn out to be justified, and problems flagged early that then materialise as described.</p>

<p><b>And it is spent quickly.</b> One overstated case, one number that does not survive checking, one crisis you did not mention until it was unavoidable. After that, everything you say is discounted, and the discount applies to the requests that genuinely matter.</p>

<p><b>The two failures, and both are common.</b> The manager who never raises anything, whose branch is assumed to be fine until it visibly is not. And the manager who raises everything, whose messages become background noise and whose genuine emergency arrives in a queue of complaints.</p>

<p><b>What good looks like.</b> Infrequent, specific, quantified, and right. A manager who sends four things a year that all turn out to be true is listened to on the fifth. That is the entire technique, and it is available to anybody willing to check their facts before sending.</p>

<blockquote>WATCH-OUT: The manager who never raises anything is not being uncomplaining, they are being invisible. When a decision is made about their branch, nobody has any reason to think it is different from any other — which is how a branch ends up with a range, a delivery schedule or a headcount that suits somewhere else entirely.</blockquote>

<p><b>And a word about the person above you.</b> They are managing several branches, receiving the same partial information about each, and are usually not withholding help — they simply do not know. A manager who assumes indifference behaves accordingly and gets it; one who assumes the person would act if they knew, and then tells them properly, is right far more often than the first. Start from that assumption until something specific tells you otherwise.</p>"""
, [
 C("Everything you get from the centre is drawn against a balance built by:",
   ["Seniority", "Being right before",
    "How often you ask", "Your branch's sales"], 1,
   "Accurate reporting, justified requests, and problems flagged early that then materialise as described."),
 C("Your branch has never flagged anything to head office in two years. The consequence is that you are:",
   ["Regarded as low-maintenance", "Invisible",
    "Trusted with more", "Left alone usefully"], 1,
   "When a decision is made about their branch, nobody has reason to think it differs from any other."),
 C("Head office typically knows your sales against target, possibly your stock and losses, and:",
   ["Your local conditions", "Very little else",
    "Your staffing position", "Your competitor situation"], 1,
   "None of the rest reaches anybody unless you send it.")]),

("What the centre actually needs from you", 11, """<p>Managing upward is usually discussed as asking for things. Most of it is supplying things — and a manager who is a good source of information is treated very differently from one who is only ever a source of requests.</p>

<p><b>What the people above you are actually short of.</b> Not data; they have more than they can read. They are short of interpretation — what the numbers mean at ground level, whether a national pattern is showing up locally, and what is happening that no report captures. You are one of the few people who can supply that, and almost nobody does.</p>

<p><b>Four things worth sending unprompted.</b></p>

<p><b>An explanation before it is requested.</b> If your figures moved unusually, say why in two lines the week it happens. It saves somebody a query, it demonstrates you noticed, and it means your explanation is on the record before anybody has formed their own.</p>

<p><b>What customers are asking for that you cannot supply.</b> Range gaps, brands requested repeatedly, sizes that sell out immediately. Whoever buys your range works largely from national data, and a specific branch-level observation is genuinely useful to them.</p>

<p><b>What a competitor has done.</b> Not their prices in general — a change: an opening, a refit, extended hours, a category they have started stocking. That is early warning nobody else in the business has.</p>

<p><b>Something that worked.</b> Managers report problems and almost never report a fix. A change you made that improved something is exactly what the business would like to spread and cannot, because nobody tells anybody.</p>

<p><b>The frequency to aim for.</b> Brief and occasional. A short note when something is genuinely worth knowing, not a weekly bulletin — which becomes something to be skimmed and then ignored, taking your genuinely important messages with it.</p>

<p><b>Why this pays back directly.</b> A manager who has supplied useful information for six months is a manager whose request is read carefully rather than filed. That is not a trick; it is that they have demonstrated their observations about their branch are accurate, which is precisely what a request asks somebody to believe.</p>

<p><b>And answer quickly when asked.</b> A query from the centre that sits for a week costs you more than it costs them. Being the branch that replies is a small, cumulative, entirely real advantage — and it is available to anybody regardless of how their branch is performing.</p>

<blockquote>IMPLEMENTATION TIP: Send one short note this month with something useful and no request attached. It is the single cheapest deposit into the credibility account, and most branch managers have never made one.</blockquote>

<p><b>Be careful what you volunteer about other branches.</b> Passing on what a peer is doing badly, however accurately, marks you as somebody whose observations come with an agenda — and it reaches them. Information about your own branch and about the market outside is yours to send. Information about a colleague's branch is theirs, and the exception is only where something is genuinely serious, in which case it goes through whoever your business names rather than into a conversation.</p>"""
, [
 C("The people above you are short of data, or of something else?",
   ["More data", "Interpretation — what the numbers mean at ground level",
    "Faster reporting", "Formal analysis"], 1,
   "You are one of the few people who can supply it, and almost nobody does."),
 C("Managers report problems and almost never report:",
   ["Costs", "Something that worked",
    "Competitor activity", "Customer requests"], 1,
   "A change that improved something is exactly what the business would like to spread and cannot."),
 C("Sending an explanation for an unusual figure before being asked means:",
   ["It appears defensive", "Your explanation is on the record before anybody forms their own",
    "It delays the report", "It invites scrutiny"], 1,
   "It also saves somebody a query and demonstrates you noticed.")]),

("Making a case that gets funded", 11, """<p>Most branch requests fail not because they were unreasonable but because they arrived as a complaint rather than a case, and the person receiving them could not act on a complaint even if they agreed with it.</p>

<p><b>The five parts, and a case missing any of them will not be approved.</b></p>

<p><b>What is happening, specifically and with a number.</b> Not "we keep running out of stock" but "our top twelve lines were unavailable on 14% of days last quarter."</p>

<p><b>What it is costing.</b> The single most important part and the one most often left out. A rough figure, honestly derived, beats no figure entirely — and if you cannot estimate the cost, you have not established that this is worth anybody's money.</p>

<p><b>What you are asking for, precisely.</b> An amount, a decision, a change to a schedule. A request that ends with something needing to be done about it puts the work of specifying it onto somebody who knows your branch less well than you do.</p>

<p><b>What it will return</b>, and be conservative. A recovery you can defend beats an optimistic one that makes the whole case look like advocacy.</p>

<p><b>What you have already done.</b> This is what separates a manager from a complainant. Having fixed the half that was yours before asking for help with the half that is not changes the reception of the request entirely.</p>

<p><b>Timing, which decides more than the content.</b> A request made when budgets are being set is a candidate. The same request made two months later is an interruption. Find out when your business decides these things and put your case in before that, not when the problem becomes urgent to you.</p>

<p><b>Keep it to a page.</b> Anybody who can approve your request has a great deal to read. A page that states the problem, the cost, the ask and the return will be read; four pages of context will be skimmed and deferred.</p>

<p><b>And ask for one thing at a time.</b> Three requests in one message become a negotiation in which the weakest is used to decline the set. Send the strongest, get it decided, then send the next.</p>

<blockquote>IMPLEMENTATION TIP: Before sending any request, check it has a number attached to the cost of doing nothing. If it does not, do not send it yet — that number is what turns a request into a decision somebody can justify making.</blockquote>

<p><b>What to do when the answer is no.</b> Ask what would need to be true for it to be yes. It is one sentence, it is not an argument, and the reply is usually specific — a lower amount, a different year, evidence you have not supplied, or a constraint you did not know about. That converts a rejection into a route, and a manager who returns six months later having met the stated condition is very difficult to refuse twice.</p>"""
, [
 C("The part of a case most often left out is:",
   ["What is happening", "What it is costing",
    "What you are asking for", "The expected return"], 1,
   "If you cannot estimate the cost, you have not established that this is worth anybody's money."),
 C("Sending three requests in one message:",
   ["Saves time", "Becomes a negotiation in which the weakest is used to decline the set",
    "Shows the full picture", "Improves prioritisation"], 1,
   "Send the strongest, get it decided, then send the next."),
 C("A request timed to when budgets are being set is a candidate; the same request two months later is:",
   ["Equally valid", "An interruption",
    "Better evidenced", "More urgent"], 1,
   "Find out when your business decides these things and put your case in before that.")]),

("Reporting bad news", 11, """<p>How a manager handles bad news does more for their standing than anything they do when things are going well, and most of the damage is done by delay rather than by the news itself.</p>

<p><b>Why managers delay, and the reasons are understandable.</b> Hoping it recovers before anybody asks. Wanting to have a solution first. Not wanting to be the branch with the problem. Each is reasonable and each converts a manageable situation into a discovered one.</p>

<p><b>What discovery costs you.</b> Bad news you report is a manager on top of their branch. The same news discovered elsewhere is a manager who either did not know or did not say, and both are worse than the news. The distinction is entirely in the sequence, and the sequence is the only part you control.</p>

<p><b>The shape that works.</b> What has happened. What it means in money or in risk. What you are doing about it. What you need from anybody else. And when you will report again.</p>

<p>That last part matters more than it appears — a date to report back converts an anxiety into a managed situation and stops the person above you having to chase.</p>

<p><b>Do not bring only a problem, and do not wait for a full solution.</b> Somewhere between the two is a partial plan and an honest statement of what you cannot solve alone, which is what a competent manager sends and is available within a day of noticing almost anything.</p>

<p><b>Own the part that is yours, plainly.</b> A manager who explains a bad quarter entirely through footfall, competition and pricing is not believed even when they are right, because nobody's branch is entirely somebody else's fault. Naming the part you got wrong — and what you have changed — buys credibility for the part that genuinely is not yours.</p>

<p><b>Never let a number surprise your manager in a meeting.</b> If your figures are going to look bad in a review, say so beforehand. Being told privately is a courtesy; finding out in front of others is an ambush, and people remember being ambushed for a long time regardless of whose fault the number was.</p>

<p><b>And the one that must go up immediately.</b> Anything involving safety, money missing, or a legal exposure. These are not judgement calls about timing — same day, factually, to whoever your business says. Delay on these is the thing that ends careers rather than the underlying event.</p>

<blockquote>WATCH-OUT: Most of the damage from bad news is done in the gap between knowing and saying. The news itself is usually survivable; a pattern of finding out late from somewhere else is not.</blockquote>

<p><b>Report the near miss as well.</b> The delivery that nearly did not arrive, the shortage you covered at the last moment, the till that failed for an hour on a Saturday. None of these ends up as bad news and each is a signal about something fragile. Managers absorb them silently as part of doing the job, which is admirable and means the business never learns that a process is running on somebody's improvisation.</p>"""
, [
 C("Bad news discovered elsewhere rather than reported by you makes you:",
   ["Unlucky", "A manager who either did not know or did not say",
    "Appropriately cautious", "Consistent"], 1,
   "The distinction is entirely in the sequence, and the sequence is the only part you control."),
 C("Explaining a bad quarter entirely through footfall, competition and pricing:",
   ["Is accurate reporting", "Is not believed even when true, because nobody's branch is entirely somebody else's fault",
    "Protects the team", "Is the right framing"], 1,
   "Naming the part you got wrong buys credibility for the part that genuinely is not yours."),
 C("The element of a bad-news report that stops your manager having to chase is:",
   ["The explanation", "A date when you will report again",
    "The action plan", "The cost estimate"], 1,
   "It converts an anxiety into a managed situation.")]),

("The target conversation", 11, """<p>Targets are set before the year starts, by people using assumptions, and they are then treated as facts for twelve months. A manager who cannot discuss one intelligently is left either promising things they cannot deliver or defending a shortfall with generalities.</p>

<p><b>Two entirely different situations that look identical in a report.</b> The branch underperformed against a reasonable expectation. Or the expectation was wrong. Both appear as a red number, and only one of them is a performance problem.</p>

<p><b>How to tell which you have.</b> Break the shortfall into its parts — how many people came, how many bought, how much they spent — and compare each with the same period last year. If fewer people came and the proportion who bought went up, the market moved and your branch held its share. If the same number came and fewer bought, that is yours.</p>

<p>That analysis takes twenty minutes and it is the difference between a diagnosis and an excuse.</p>

<p><b>When to challenge a target, which is at the start.</b> A target you believe is wrong should be discussed when it is set, with your reasoning, in writing, once. Accepting it silently and disputing it in month eight is the worst available option — by then it looks like an explanation for failure rather than a judgement, and you were the person best placed to know.</p>

<p><b>How to challenge it.</b> Not by asking for a lower number. By stating what you think the branch will do and why, with the specifics: the competitor that opened, the employer that closed, the road that changed, the year that included an unrepeatable month. Then accept the decision either way and get on with it.</p>

<p><b>The commitment worth being careful about.</b> A manager who agrees to a number they privately believe is unreachable has bought four months of peace and spent their credibility on it. It is better to say, once and calmly, what you think is achievable and why, and then deliver that.</p>

<p><b>Where you are ahead, say why.</b> A branch beating its target because of something structural — a competitor closed, a new employer opened nearby — should say so rather than accepting the credit. It sounds counterintuitive and it is exactly what makes you believed in the quarter you fall short.</p>

<blockquote>IMPLEMENTATION TIP: When your target is set, write one paragraph on what you think the branch will actually do and the two or three specific reasons. Send it once. Whatever happens afterwards, you have a dated statement of your own judgement, which is worth a great deal in a difficult conversation eight months later.</blockquote>

<p><b>What to do with a target you have already missed.</b> Not defend the year — fix the quarter. A manager who spends a review arguing about a number that is already in the past has used the meeting on something nobody can change, and has said nothing about what happens next. State the shortfall, state the cause with the four numbers, and spend the rest of the time on the two things you are doing about the remaining months. That is the part your manager can actually help with.</p>"""
, [
 C("A branch beating its target for a structural reason should:",
   ["Accept the credit", "Say so",
    "Raise it next year", "Report it quietly"], 1,
   "It sounds counterintuitive and it is exactly what makes you believed in the quarter you fall short."),
 C("A target you believe is wrong should be challenged:",
   ["When the shortfall appears", "When it is set, in writing, once",
    "At the half year", "Through your peers"], 1,
   "Disputing it in month eight looks like an explanation for failure rather than a judgement."),
 C("Agreeing to a number you privately believe is unreachable buys:",
   ["Goodwill", "Four months of peace, spent from your credibility",
    "Time to improve", "A better relationship"], 1,
   "Better to say once and calmly what you think is achievable, and then deliver it.")]),

("Saying no, and saying not yet", 11, """<p>A branch manager receives more instructions, initiatives and requests than a branch can absorb. Accepting all of them is not cooperation — it is a decision to do most of them badly, made silently.</p>

<p><b>What actually happens when a manager says yes to everything.</b> The initiatives that arrive with attention get done. The rest are started and abandoned. Nobody is told which is which, so the business believes it has fifteen things running and has four. And the manager is regarded as unreliable rather than overloaded, because from outside those look the same.</p>

<p><b>The reply that works, and it is not no.</b> "Yes, and here is what comes off." Naming what will be delayed or dropped to make room converts a refusal into a prioritisation question, which is the right conversation and the one the person asking is usually able to have.</p>

<p><b>Say it at the time, not by quietly not doing it.</b> Silent non-compliance is the commonest response to an overloaded branch and the most damaging, because the business does not find out until it matters and the manager has spent credibility they did not know they were spending.</p>

<p><b>Where you genuinely cannot do something, say why in terms of the business's own priorities.</b> Not "I do not have time" but "doing this properly is two days, and the two days are currently on the availability work that is worth ₦140,000 a month — which would you rather have?" That is a question somebody can answer, and it demonstrates that your time is allocated rather than merely full.</p>

<p><b>The initiative you should push back on hardest.</b> Anything requiring your team's attention during trading hours at a busy period. The cost is invisible to whoever asked and entirely visible on your floor, and it is worth being specific about what it will do to your queue rather than accepting and absorbing it.</p>

<p><b>And accept gracefully when overruled.</b> You will make the case, be turned down, and have to do it anyway. Doing it properly at that point is what preserves the ability to make the next case — a manager who complies resentfully or half-heartedly has confirmed that their objection was about willingness rather than judgement.</p>

<blockquote>IMPLEMENTATION TIP: Keep a short list of what your branch is currently working on. When something new arrives, reply with the list and ask which item it displaces. It is a two-line reply, it is not a refusal, and it moves the decision to the person who is entitled to make it.</blockquote>

<p><b>The instruction that arrives with no name on it.</b> A message to all branches, from somewhere, with a deadline. It is worth establishing who actually owns it before spending your team's time, because a proportion of these are optional, superseded, or aimed at branches unlike yours. One question costs a minute; assuming and complying can cost your team a day for nothing.</p>"""
, [
 C("A manager who accepts every initiative is regarded as:",
   ["Cooperative", "Unreliable rather than overloaded",
    "Overstretched", "Committed"], 1,
   "From outside, an abandoned initiative and an unreliable manager look the same."),
 C("The reply that works better than refusing is:",
   ["I'll try", "Yes, and here is what comes off",
    "Not this quarter", "Can somebody else do it?"], 1,
   "It converts a refusal into a prioritisation question, which is the right conversation."),
 C("Having made your case and been overruled, doing the work properly:",
   ["Concedes the point", "Preserves your ability to make the next case",
    "Wastes the effort", "Signals agreement"], 1,
   "Complying resentfully confirms that the objection was about willingness rather than judgement.")]),

("The people who can actually help you", 11, """<p>Branch managers direct almost all their upward effort at their own line manager, and a large share of what they need is decided by somebody else entirely.</p>

<p><b>Who those people usually are.</b> Whoever buys your range and sets your prices. Whoever runs distribution and decides your delivery schedule. Whoever handles finance and can tell you what your figures are actually built from. Whoever manages systems, when something at your counter does not work as it should. And your peers running other branches.</p>

<p><b>What a buyer needs from a branch, and rarely gets.</b> Specific information about what customers ask for and do not find, what is not selling and why, and what a competitor is doing on a category. Most buyers work from national data and would value a specific branch-level observation — the request they turn down is the vague one, not the informed one.</p>

<p><b>Distribution is where the most fixable problems sit.</b> A delivery window that lands at your busiest hour, a sequence that means your branch is always last, a vehicle size that does not suit your access. These are frequently changeable, almost never raised, and a manager who asks once with the reason usually gets somewhere.</p>

<p><b>Your peers are the most under-used resource in any chain.</b> Another manager has solved the problem you have, has the same problem and would join a case for fixing it, or has a range or layout arrangement worth copying. Half an hour on the phone or a visit to each other's branches is free, and almost no chain does it systematically.</p>

<p><b>The reciprocity that makes any of this work.</b> Be useful to these people before you need them. Answer the buyer's question quickly, take the call about somebody else's stock, tell a peer what you found. A manager who only appears when they want something gets a different response from one who has been helpful for a year, and the difference is entirely unremarkable and entirely real.</p>

<p><b>And keep your line manager informed when you go sideways.</b> Not permission — information. Going around somebody rather than alongside them is the thing that damages a relationship, and a sentence saying you have asked distribution about the delivery window costs nothing and prevents all of it.</p>

<blockquote>IMPLEMENTATION TIP: Pick one person outside your line — a buyer, somebody in distribution, a peer at a comparable branch — and make contact this month with something useful rather than a request. It is the cheapest investment available to a branch manager and it pays over years.</blockquote>

<p><b>And be findable when they need you.</b> Much of what a buyer, a distributor or a systems person has to do involves getting an answer from a branch. The branch that is reachable, replies the same day and gives a straight answer becomes the one they call first — which sounds like a burden and is in fact how a branch manager acquires informal influence over decisions they are not formally part of.</p>"""
, [
 C("A buyer working from national data will most value from a branch:",
   ["A sales summary", "Specific observations about what customers ask for and do not find",
    "A range request", "Competitor pricing generally"], 1,
   "The request they turn down is the vague one, not the informed one."),
 C("The most under-used resource available to a branch manager is:",
   ["The finance team", "Their peers running other branches",
    "Head office analytics", "The buying team"], 1,
   "Another manager has solved your problem, shares it, or has something worth copying — and almost no chain does this systematically."),
 C("When approaching somebody outside your line, you should tell your own manager:",
   ["To ask permission", "As information, in a sentence",
    "Only if it succeeds", "Afterwards, in the monthly report"], 1,
   "Going around somebody rather than alongside them is what damages a relationship.")]),

("Okelewo: the manager who got the refit", 11, """<p>The Lagos branch had the worst storeroom in the group — at the end of a corridor, badly shelved, with a back door that opened onto an alley. Two managers had asked for it to be sorted out and been turned down. The third got it approved in six weeks.</p>

<p><b>What the first two had sent.</b> A request to refit the storeroom because it was unsafe, disorganised and made the job difficult. Both were true. Neither was approved, and neither manager was told why — the request simply did not compete with anything else asking for money that year.</p>

<p><b>What the third sent, on one page.</b></p>

<p><b>The problem, with a number.</b> Stock in the storeroom that could not be found within five minutes on 40% of attempts, measured over three weeks. Gaps on the shelf while stock sat in the back, counted at four in the afternoon: an average of nine lines a day.</p>

<p><b>The cost.</b> Those nine lines priced at their actual sales rate and margin: about ₦190,000 a month in earnings not made. Plus the category's losses, which ran two points above the group average and had been attributed to theft.</p>

<p><b>The ask.</b> ₦1.4m for shelving, lighting and a door that closes, with a quotation attached.</p>

<p><b>The return.</b> Conservatively half the availability loss, so under fifteen months to pay back, before anything the loss reduction contributed.</p>

<p><b>What she had already done.</b> Reorganised what could be reorganised without money, introduced an afternoon replenishment slot, and put a named person on receiving. The remaining problem was the room itself, and she said so.</p>

<p><b>Why it worked.</b> Not because she wrote better. Because the request had stopped being about a storeroom that was unpleasant and had become an investment with a payback period, submitted three weeks before the capital budget was set, by a manager who had visibly fixed everything she could fix first.</p>

<p><b>And the part worth noticing.</b> The measurements took her about four hours spread over three weeks. The two previous requests had taken ten minutes each. Neither of those managers was wrong about the storeroom — they simply asked for money in a way that gave nobody a reason to say yes.</p>

<p><b>What she did after it was approved.</b> Reported the result at three months against what she had promised — including that the loss reduction had been smaller than hoped and the availability recovery larger. Nobody asked her to. It is the reason her next two requests were approved without much discussion, and it is the step almost every manager skips: a case that reports back is a case the approver can point to when defending the next one.</p>

<blockquote>IMPLEMENTATION TIP: Take the request your branch most needs and spend three hours measuring what it is actually costing. That is usually the entire difference between a request that has been turned down twice and one that gets approved.</blockquote>"""
, [
 C("The first two storeroom requests failed because they:",
   ["Were unreasonable", "Gave nobody a reason to say yes",
    "Went to the wrong person", "Asked for too much"], 1,
   "Both were true about the storeroom being unsafe and disorganised; neither competed with anything else asking for money."),
 C("The successful request differed mainly in that it was:",
   ["Better written", "An investment with a payback period, timed before the capital budget",
    "Sent to a more senior person", "Smaller in amount"], 1,
   "Submitted by a manager who had visibly fixed everything she could fix first."),
 C("The measurement work behind the successful request took about:",
   ["Ten minutes", "Four hours over three weeks",
    "A full week", "A month"], 1,
   "The two previous requests had taken ten minutes each, which is the entire difference.")]),

("The upward routine", 11, """<p>This is the chapter to keep. Managing upward is mostly a small number of habits done consistently rather than anything that happens in a meeting.</p>

<p><b>Monthly, with your own manager.</b> Bring margin, availability, losses and staff turnover rather than only sales — and bring them before being asked. One thing that is going wrong, with what you are doing about it. And one thing you need, with a number attached.</p>

<p><b>Whenever it happens.</b> Bad news the same week, in the five-part shape: what happened, what it means, what you are doing, what you need, when you will report again. Anything involving safety, missing money or legal exposure the same day.</p>

<p><b>Quarterly.</b> One considered case for something your branch needs, timed against when your business actually decides. Contact with one person outside your line, offering something rather than asking. And a look at your own list — what are we working on, and is it still the right list.</p>

<p><b>Annually, at target setting.</b> One paragraph on what you think the branch will do and why, sent once, dated. Whatever happens afterwards you have a record of your own judgement.</p>

<p><b>And the habit underneath all of it.</b> Check your numbers before you send them. A figure that does not survive scrutiny costs more than the thing you were asking for, because it applies a discount to everything you send afterwards — and you will not be told that it happened.</p>

<p><b>What this is worth.</b> Range, price, headcount, systems and investment are decided elsewhere and they constrain everything else in this track. A manager who is heard on those gets a branch that can be improved; a manager who is not gets a branch where most of the constraints are permanent. That is a large difference and it is decided by perhaps two hours a month.</p>

<p><b>The one to start with.</b> Bring one number to your next monthly conversation that nobody asked for — availability on your top lines, or your turnover figure, or what a specific problem is costing. It changes what that conversation is about, permanently, and it costs one evening of preparation.</p>

<blockquote>WATCH-OUT: Everything in this module rests on being right. There is no technique that survives a manager whose numbers do not check out — and there is no technique needed by one whose numbers always do.</blockquote>

<p><b>A closing note on tone.</b> Nothing in this module requires being assertive, political or confident in meetings. The manager in the worked example got a refit two others could not, and she did it with a page of arithmetic and three weeks of counting. Being right, being specific and being consistent are available to quiet people, and in this part of the job they beat presence — which is worth knowing if the phrase “managing upward” has always sounded like something other people do.</p>"""
, [
 C("The monthly conversation should bring margin, availability, losses and turnover:",
   ["When asked for them", "Before being asked",
    "Quarterly instead", "Only if adverse"], 1,
   "Along with one thing going wrong and one thing you need, with a number attached."),
 C("A figure that does not survive scrutiny costs more than the request because it:",
   ["Delays the decision", "Applies a discount to everything you send afterwards",
    "Requires correction", "Wastes the meeting"], 1,
   "And you will not be told that it happened."),
 C("The difference between a manager who is heard upward and one who is not is:",
   ["Their branch's size", "Whether most of their constraints are permanent",
    "Their seniority", "How often they report"], 1,
   "Range, price, headcount, systems and investment are decided elsewhere and constrain everything else.")]),
]


QUESTIONS = [
 Q("Managing upward is not politics because the alternative is:", ["Slower decisions", "A business deciding about your branch on worse information than it could have had", "More autonomy", "Less scrutiny"], 1,
   "Their decision then constrains everything you can do.", "Ch1 §1", "Why it matters"),
 Q("Head office typically knows your sales against target and:", ["Your local conditions", "Very little else", "Your staffing", "Your competitors"], 1,
   "None of the rest reaches anybody unless you send it.", "Ch1 §4", "Why it matters"),
 Q("The credibility account is built by:", ["Seniority", "Being right before", "Frequency of contact", "Branch performance"], 1,
   "And spent quickly by one overstated case or one number that does not survive checking.", "Ch1 §5", "Why it matters"),
 Q("A manager who raises everything finds that:", ["They are well informed", "Their messages become background noise", "They get faster answers", "They are consulted more"], 1,
   "Their genuine emergency arrives in a queue of complaints.", "Ch1 §7", "Why it matters"),
 Q("A manager who never raises anything is:", ["Uncomplaining", "Invisible", "Efficient", "Trusted"], 1,
   "Their branch ends up with a range, schedule or headcount that suits somewhere else.", "Ch1 §9", "Why it matters"),
 Q("The part of a case most often missing is:", ["The problem", "What it is costing", "The ask", "The timing"], 1,
   "If you cannot estimate the cost, you have not established this is worth anybody's money.", "Ch2 §4", "Making a case"),
 Q("What separates a manager from a complainant in a request is:", ["The tone", "What you have already done", "The evidence", "The amount asked"], 1,
   "Having fixed the half that was yours changes the reception entirely.", "Ch2 §7", "Making a case"),
 Q("A request should be timed to arrive:", ["When the problem becomes urgent", "Before budgets are set", "At the quarter end", "After a bad month"], 1,
   "The same request two months later is an interruption.", "Ch2 §8", "Making a case"),
 Q("A case should be:", ["Thorough, with full context", "One page", "Presented verbally", "Sent with alternatives"], 1,
   "Anybody who can approve your request has a great deal to read.", "Ch2 §9", "Making a case"),
 Q("Three requests in one message:", ["Are efficient", "Let the weakest be used to decline the set", "Show priorities", "Get a fuller answer"], 1,
   "Send the strongest, get it decided, then send the next.", "Ch2 §10", "Making a case"),
 Q("Most of the damage from bad news is done:", ["By the news", "In the gap between knowing and saying", "In the meeting", "By the numbers"], 1,
   "A pattern of finding out late from somewhere else is not survivable.", "Ch3 §9", "Bad news"),
 Q("The five-part bad news report ends with:", ["An apology", "When you will report again", "The cost", "A request"], 1,
   "It converts an anxiety into a managed situation and stops the person above you chasing.", "Ch3 §4", "Bad news"),
 Q("You should bring:", ["Only a problem", "A partial plan and an honest statement of what you cannot solve alone", "Only a full solution", "Options for others to choose"], 1,
   "Available within a day of noticing almost anything.", "Ch3 §5", "Bad news"),
 Q("Explaining a bad quarter entirely through external factors:", ["Is accurate", "Is not believed even when true", "Protects the branch", "Is standard"], 1,
   "Nobody's branch is entirely somebody else's fault.", "Ch3 §6", "Bad news"),
 Q("If your figures will look bad in a review you should:", ["Prepare an explanation", "Say so beforehand", "Raise it in the meeting", "Wait to be asked"], 1,
   "People remember being ambushed for a long time regardless of whose fault the number was.", "Ch3 §7", "Bad news"),
 Q("A red number against target may mean underperformance or:", ["Poor reporting", "That the expectation was wrong", "A market shift only", "A data error"], 1,
   "Both look identical in a report and only one is a performance problem.", "Ch4 §2", "Targets"),
 Q("Distinguishing the two takes about:", ["An hour", "Twenty minutes", "A day", "A week"], 1,
   "Break the shortfall into how many came, how many bought, and how much they spent.", "Ch4 §4", "Targets"),
 Q("If fewer people came and the proportion who bought rose:", ["The branch underperformed", "The market moved and your branch held its share", "Service improved only", "Pricing worked"], 1,
   "A completely different conversation from the same shortfall stated as one number.", "Ch4 §3", "Targets"),
 Q("A target you believe is wrong should be raised:", ["At the half year", "When it is set, in writing, once", "When the shortfall appears", "Through your manager's manager"], 1,
   "By month eight it looks like an explanation for failure.", "Ch4 §5", "Targets"),
 Q("A branch beating target for a structural reason should:", ["Accept the credit", "Say why", "Request a higher target", "Report it quietly"], 1,
   "It is exactly what makes you believed in the quarter you fall short.", "Ch4 §8", "Targets"),
 Q("A manager who says yes to everything creates a business that believes it has:", ["A committed manager", "Fifteen things running when it has four", "Adequate capacity", "Good compliance"], 1,
   "And the manager is regarded as unreliable rather than overloaded.", "Ch5 §2", "Saying no"),
 Q("The reply that works better than a refusal is:", ["I'll try", "Yes, and here is what comes off", "Not this quarter", "Who else could do it?"], 1,
   "It converts a refusal into a prioritisation question.", "Ch5 §3", "Saying no"),
 Q("Silent non-compliance is damaging because:", ["It is dishonest", "The business does not find out until it matters", "It sets an example", "It delays projects"], 1,
   "And the manager has spent credibility they did not know they were spending.", "Ch5 §4", "Saying no"),
 Q("Saying you do not have time is weaker than saying:", ["It is not a priority", "What the two days are currently on and what that is worth", "Ask somebody else", "Not this month"], 1,
   "It demonstrates that your time is allocated rather than merely full.", "Ch5 §5", "Saying no"),
 Q("Complying resentfully after being overruled confirms that your objection was about:", ["Judgement", "Willingness", "Capacity", "Priorities"], 1,
   "Doing it properly is what preserves the ability to make the next case.", "Ch5 §7", "Saying no"),
 Q("Which decisions affecting a branch are made outside the line manager?", ["None significant", "Range, price, delivery schedule and systems", "Only investment", "Only staffing"], 1,
   "A large share of what a branch needs is decided by somebody else entirely.", "Ch6 §2", "Working across"),
 Q("Distribution problems are described as:", ["Rarely fixable", "Frequently changeable and almost never raised", "Head office policy", "Contractual"], 1,
   "A delivery window at your busiest hour, a sequence that leaves you last, a vehicle that does not suit your access.", "Ch6 §4", "Working across"),
 Q("The most under-used resource in a chain is:", ["Central analytics", "Peers at other branches", "The buying team", "Finance"], 1,
   "Half an hour on the phone is free and almost no chain does it systematically.", "Ch6 §5", "Working across"),
 Q("The reciprocity that makes lateral relationships work is:", ["Formal agreements", "Being useful before you need them", "Regular meetings", "Shared targets"], 1,
   "A manager who only appears when they want something gets a different response.", "Ch6 §6", "Working across"),
 Q("When you approach somebody outside your line you should tell your manager:", ["To get permission", "As information", "Only if it works", "In the monthly report"], 1,
   "Going around somebody rather than alongside them is what damages a relationship.", "Ch6 §7", "Working across"),
 Q("The two previous storeroom requests failed because they:", ["Asked for too much", "Gave nobody a reason to say yes", "Were badly timed only", "Went to the wrong person"], 1,
   "Both were true about the storeroom; neither competed with anything else asking for money.", "Ch7 §2", "Okelewo refit"),
 Q("The successful request measured stock unfindable within five minutes on:", ["10% of attempts", "40% of attempts", "70% of attempts", "25% of attempts"], 1,
   "Measured over three weeks, alongside nine lines a day gapped while stock sat in the back.", "Ch7 §3", "Okelewo refit"),
 Q("The availability loss was priced at about:", ["₦19,000 a month", "₦190,000 a month", "₦1.9m a month", "₦90,000 a month"], 1,
   "Plus category losses running two points above the group average and attributed to theft.", "Ch7 §4", "Okelewo refit"),
 Q("The ₦1.4m ask was justified on a payback of under:", ["Six months", "Fifteen months", "Three years", "Five years"], 1,
   "Conservatively half the availability loss, before anything the loss reduction contributed.", "Ch7 §6", "Okelewo refit"),
 Q("The measurement behind the successful request took:", ["Ten minutes", "About four hours over three weeks", "A full week", "A month"], 1,
   "Which is the entire difference between the request that failed twice and the one approved.", "Ch7 §9", "Okelewo refit"),
 Q("The monthly conversation should include margin, availability, losses and turnover:", ["When requested", "Before being asked", "Only when adverse", "Quarterly"], 1,
   "Plus one thing going wrong and one thing you need, with a number.", "Ch8 §2", "The routine"),
 Q("Anything involving safety, missing money or legal exposure goes up:", ["The same week", "The same day", "At the monthly review", "Once established"], 1,
   "These are not judgement calls about timing.", "Ch8 §3", "The routine"),
 Q("At target setting you should send:", ["A negotiation", "One dated paragraph on what you think the branch will do and why", "Nothing until the figures", "A request for adjustment"], 1,
   "Whatever happens afterwards, you have a record of your own judgement.", "Ch8 §5", "The routine"),
 Q("A figure that does not survive scrutiny:", ["Is corrected and forgotten", "Discounts everything you send afterwards", "Delays one decision", "Requires an apology"], 1,
   "And you will not be told that it happened.", "Ch8 §6", "The routine"),
 Q("The whole upward routine amounts to roughly:", ["A day a week", "Two hours a month", "A morning a week", "An hour a quarter"], 1,
   "Against decisions that determine whether most of your constraints are permanent.", "Ch8 §7", "The routine"),
 Q("The habit to start with is bringing to your next monthly conversation:", ["A request", "One number nobody asked for", "Your sales analysis", "A list of problems"], 1,
   "It changes what that conversation is about, permanently, for one evening of preparation.", "Ch8 §8", "The routine"),
 Q("Everything in this module rests on:", ["Relationships", "Being right", "Frequency", "Presentation"], 1,
   "There is no technique that survives a manager whose numbers do not check out.", "Ch8 §9", "The routine"),
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
    rebalance(QUESTIONS, "retail:upward:exam")
    rebalance([c for _t, _e, _h, ch in LESSONS for c in ch], "retail:upward:checks")

    bank = {re.sub(r"[^a-z0-9 ]", "", q["q"].lower()).strip() for q in QUESTIONS}
    dupes = [c["q"] for _t, _e, _h, ch in LESSONS for c in ch
             if re.sub(r"[^a-z0-9 ]", "", c["q"].lower()).strip() in bank]
    if dupes:
        raise SystemExit("ABORT: %d check(s) duplicate exam questions:\n  %s"
                         % (len(dupes), "\n  ".join(dupes)))

    mod = {
        "title": "RL 7 — Managing Upward and Across",
        "desc": ("Range, price, headcount, systems and investment are decided elsewhere and "
                 "constrain everything you do. The credibility account, building a case that "
                 "gets funded, reporting bad news, the target conversation, saying no without "
                 "refusing, and the people outside your line who can actually help."),
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
