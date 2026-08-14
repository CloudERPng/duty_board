#!/usr/bin/env python3
"""Closer track — Reports & Analytics to standard.

Six chapters at a 1,065 mean, the thinnest module in the estate, teaching people
to read numbers they will act on. Under-teaching here does more damage than
under-teaching anywhere else in the track: a closer who misreads a screen gets
one order wrong; a manager who misreads a report moves budget.

Rebuilt as nine chapters. Three are new:

  ch2  The dashboard and the reports — two different instruments
  ch8  Reading reports as a set — the investigation path
  ch9  The traps — denominators, periods, attribution lag, small numbers

The other six are deepened from what was already there. The old chapter 6 mixed
cohorts with cross-report reading; those are now separate chapters, because they
are different skills and the second one is the whole point of the module.

Chapter 2 now teaches the rule that explains both dashboard anomalies: terminal
status tiles are scoped to the selected timeframe, while in-flight status tiles
ignore it and show the whole book as it stands. That is why NOT READY can read
91,166 against a monthly TOTAL ORDERS of 46,472 — and it is the reason nobody
should ever divide an in-flight tile by Total Orders. Delivery Rate excludes
duplicates, since an order flagged as a duplicate was never a real chance to
deliver. One small [CONFIRM] remains on the exact rate arithmetic.

Run from the app package directory:  python3 rebuild_closer_reports.py
Then:  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons
"""

import io
import json
import re
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv


L = [
("The reports section — directory, roles and dates", 8, """<p>Open <b>Reports</b> from the left sidebar and the landing page presents every report as a directory, grouped by category: Sales, Marketing, Product, Customer, Operations and After-Sales.</p>

<p>Under Sales sit Closer Summary, Team Performance and Orders Status. Marketing carries ROAS, Channel Attribution, Campaign Form Funnel and Digital Marketer Leads. Product holds Product Sales Analysis; Customer holds Revenue Cohort Trends; Operations holds Branch Performance and Fulfilment Health; After-Sales holds the After-Sales Summary and Upsell/Cross-Sell.</p>

<p><b>What you can see depends on your role</b>, and the pattern is worth understanding rather than memorising. Sales agents reach their own Closer Summary and often Team Performance read-only. Team leads see team-level reports with drill-down into their own people. Sales managers see all sales and operations reports across teams and branches. Marketing managers see the marketing set. Administrators and executives see everything.</p>

<p>The practical consequence: <b>a report you cannot find is almost always a role restriction rather than a missing feature.</b> Before raising a ticket asking where a report went, check whether it was ever yours to see. The restriction is deliberate — individual performance data is personal, and a business that lets everybody read everybody's conversion rate has created a problem for itself that no report will solve.</p>

<p><b>The date filter tops every report and is the single most important control on the page.</b> It offers presets from Today through Last Year, a custom calendar range for precise windows, and on some reports a Compare toggle that lays the previous period alongside with percentage-change indicators. Change the range and every chart, table and metric on the page refreshes together.</p>

<p>That "together" matters more than it sounds. It means a screenshot of a report without its date range is meaningless, and a number quoted in a meeting without its period is an argument waiting to happen. When you take a figure out of a report — into a message, a slide, an email — carry the date range with it. Two people looking at the same report over different windows will reach opposite conclusions and both be right.</p>

<p><b>The Compare toggle is where most of the insight lives.</b> A conversion rate of 62% is a number. A conversion rate of 62% against 71% last month is a conversation. Absolute figures tell you where you are; comparisons tell you where you are heading, and the direction is usually the more actionable of the two.</p>

<blockquote>CONSULTANT NOTE: Unlike the dashboard's period-to-date pills, reports offer completed prior periods and custom ranges. This is where last month's finished numbers actually live — the dashboard cannot show you a closed month.</blockquote>"""),

("The dashboard and the reports — two different instruments", 8, """<p>New managers routinely mistake the dashboard for a report, quote a tile in a meeting, and discover later that it did not mean what they assumed. The two surfaces answer different questions, and knowing which you are looking at is the first analytical skill in this module.</p>

<p><b>The dashboard answers "what is happening now".</b> It opens on a set of tiles — Total Orders, Assigned, Agent Notified, Dispatch Assigned, Order Accepted, Delivery In Progress, Delivery Rescheduled, Not Picking, Call Back, Not Ready, Rejected, Delivered, Cancelled, Not Reachable, Duplicate, Failed/Returned, On Hold — with a timeframe control offering Day, Week, Month, Quarter and Year. It is an instrument for the present: where is the book right now, what is piling up, what is moving.</p>

<p><b>The reports answer "what happened".</b> They offer finished periods, custom ranges and comparison. They are the instrument for review, coaching and decisions about money.</p>

<p>Use the dashboard to notice; use the reports to conclude. A tile that looks wrong is a reason to open a report, not a finding in itself.</p>

<p><b>Now the rule that catches almost everyone, and it is the most important thing in this module.</b></p>

<p><b>Only some of the tiles respond to the timeframe control.</b></p>

<p>Tiles for <b>terminal</b> statuses — Total Orders, Delivered, Cancelled and the rest of the outcomes an order finishes in — are scoped to the period you selected. Choose Month and you see this month's delivered orders.</p>

<p>Tiles for <b>in-flight</b> statuses — Agent Notified, Delivery Rescheduled, Delivery In Progress, and the other stages an order passes through on its way somewhere — <b>ignore the timeframe entirely</b>. They show the total sitting in that status right now, whatever period you picked. Switch from Day to Year and they do not move.</p>

<p><b>Once you know that, the dashboard stops looking broken.</b> On a real dashboard showing one month, Total Orders read 46,472 while Not Ready read 91,166 — nearly double. That is not an error and the tiles are not counting the same thing: 46,472 orders arrived this month, and 91,166 orders are sitting in Not Ready across the entire book, most of them from earlier periods.</p>

<p><b>The consequence you must carry.</b> Never treat the tiles as slices of one pie. They do not sum to Total Orders and were never meant to. Never compute a percentage by dividing an in-flight tile by Total Orders — you would be dividing an all-time figure by one month, and the answer would be meaningless in a way that looks perfectly plausible.</p>

<p>The distinction is also useful rather than merely a caution. A terminal tile answers <i>how did we do</i>. An in-flight tile answers <i>what is stuck right now</i>, and a large in-flight number is a backlog whether or not it arrived this month. Delivery Rescheduled sitting high says something about the book today that no period-scoped figure would reveal.</p>

<p><b>Delivery Rate has its own rule: duplicates are removed from the calculation.</b> An order identified as a duplicate was never a real opportunity to deliver, so counting it against delivery performance would penalise the team for the system correctly spotting the same order twice.</p>

<blockquote>[CONFIRM] Worked against a live dashboard, Delivered of 25,466 over Total Orders less Duplicates of 45,342 gives 56.2%, where the tile read 56.3%. The small gap is most likely live data moving between tile loads, but the exact definition is worth confirming with your administrator before quoting the figure in a review.</blockquote>

<blockquote>IMPLEMENTATION TIP: Two questions before you quote any tile. Does this one move when I change the timeframe? And for a rate: what has been taken out of the denominator? Change the timeframe control and watch which tiles move — thirty seconds, once, and you will never misread the dashboard again.</blockquote>"""),

("Closer Summary — reading individual performance", 8, """<p>The Closer Summary is the go-to report for individual performance — read daily by team leads, weekly and monthly by managers running reviews, coaching and incentives. One row per agent, and every column earns its place.</p>

<p><b>Total Orders</b> is raw activity volume. Read it last, not first. Low volume can mean underperformance, or it can mean complex high-value work, or a closer covering a category with thinner demand. Context first, judgement second.</p>

<p><b>Delivered Orders</b> is the true count of completed sales — cancellations, returns and anything still in flight stripped out. This is the number that corresponds to money.</p>

<p><b>Conversion Rate</b>, Delivered divided by Total, is the most important efficiency metric on the row. Seventy per cent means seven of every ten orders a closer created reached the customer. The team average sits alongside so you are comparing against the room rather than against an idea in your head.</p>

<p><b>Revenue</b> is the bottom-line contribution of those delivered orders, and <b>AOV</b> — Revenue divided by Delivered — is the order-value profile. A notably high AOV usually marks a skilled upseller, someone who reliably turns one item into two.</p>

<p><b>Cancellation Rate</b>, Cancelled divided by Total, is the diagnostic column. Above roughly twenty to twenty-five per cent is a red flag, and it almost always means the same thing: orders created without proper confirmation at the front. A closer under pressure to show volume can create orders from soft interest, and every one of those becomes a cancellation later. The rate catches it.</p>

<p><b>Response Time</b> is average speed to respond to new assignments and enquiries — the leading indicator that moves before conversion does.</p>

<p><b>Read pairs, not columns.</b> This is the whole craft of the report, because no single column tells you what to do:</p>

<p>High volume with low conversion is a confirmation problem — the closer is creating orders faster than they are qualifying them. Low volume with high AOV is a specialist, not a slacker, and ranking them on volume will drive away your best upseller. Good conversion with slow response is a coaching win waiting to happen — the skill is there, the habit is not. Low volume with low conversion and a rising cancellation rate is the pattern that actually needs a conversation, and it is the only one of the four that does.</p>

<blockquote>IMPLEMENTATION TIP: Filter by date range, branch or team before comparing anybody. A closer in a branch with thin stock cover will show cancellations that belong to the warehouse, not to them. Comparing like with like is not a courtesy; it is what makes the report usable.</blockquote>

<blockquote>WATCH-OUT: Every metric here can be gamed, and closers work out how quickly. Conversion improves if you avoid difficult orders. Cancellation rate improves if you leave dead orders open instead of closing them honestly. Read the columns together and the gaming shows up as a shape that does not make sense — which is exactly why you read pairs.</blockquote>"""),

("Team Performance — comparing units fairly", 8, """<p>The Team Performance report rolls individual agents up into their organisational units — one row per team or branch — and its entire craft is <b>normalisation</b>: making units of different sizes comparable without pretending they are the same.</p>

<p><b>Headcount</b> is active agents in the unit, and it is the most important column on the row despite measuring nothing about performance. It is the denominator that makes every other comparison honest.</p>

<p><b>Total Orders, Delivered Orders and Total Revenue</b> are the combined outputs — the raw scale of what the unit did.</p>

<p><b>Revenue per Agent</b>, Revenue divided by Headcount, is the fair-comparison metric and the one to lead with. A team of fifteen producing more total revenue than a team of five has told you almost nothing; a team of five producing more revenue per agent has told you something worth acting on.</p>

<p><b>Average Conversion Rate</b> is the unit-wide delivered-to-total ratio, <b>Top Performer</b> surfaces each unit's standout automatically, and <b>Average AOV</b> gives the unit's order-value profile.</p>

<p><b>Why ranking on raw revenue is the classic error.</b> Consider two teams. One has fifteen agents and produces the larger revenue total; the other has five and produces less. Rank on totals and the large team wins, gets the praise and probably gets the next hire. Rank on revenue per agent and the picture may invert completely — and the second view is the one that predicts what happens if you add a person to either team.</p>

<p>A large team beating a small one on totals while losing on revenue per agent is not winning. It is absorbing more people to produce less each, which is the shape of a team that is growing headcount faster than capability.</p>

<p><b>Reading Top Performer carefully.</b> It is useful for spotting talent and dangerous as a summary. A unit whose top performer produces a large share of its revenue is a unit with a concentration risk — that person's resignation is a revenue event. A unit with a flat distribution is more robust even if its best individual is less remarkable. The report shows you the peak; you have to ask about the spread.</p>

<blockquote>WATCH-OUT: Never rank teams on raw revenue alone. A big team beating a small one on totals while losing on revenue per agent is shrinking, not winning — and rewarding it teaches every team lead that the route to recognition is headcount rather than performance.</blockquote>

<blockquote>IMPLEMENTATION TIP: Before comparing two units, check whether they cover the same categories and countries. Closers are scoped to both, so two teams may be working structurally different demand. Comparing them without saying so produces a league table that measures territory rather than skill.</blockquote>"""),

("Product Sales Analysis — what is actually selling", 8, """<p>One row per product, and the columns answer the commercial questions managers actually ask — not what is popular, but what the business should do next.</p>

<p><b>Units Sold and Revenue</b> give delivered volume and value per product. Delivered is the operative word: this report counts what reached customers, not what was ordered.</p>

<p><b>Percentage of Total Revenue</b> measures concentration, and it is the column with the most strategic weight. A single product at forty per cent of revenue means the business leans on it — and inherits every risk attached to it: a supply interruption, a price move by a competitor, a quality problem, a platform banning its advertising. Top three products above half of revenue is a diversification warning worth raising even while the numbers look good, because the numbers look good right up until they do not.</p>

<p><b>Average Selling Price</b> is the discipline column. When ASP runs meaningfully below list price, agents are discounting. The question is not whether that is bad — sometimes it is exactly right — but whether it is policy or habit. Discounting that nobody decided on is margin leaving the business without anybody choosing to spend it.</p>

<p><b>Trend</b> shows rising, flat or declining against the prior period. Both directions demand action. A growing product needs stock cover ahead of demand, because the fastest way to kill momentum is to run out. A declining product needs a cause found before a conclusion is drawn: seasonality, a competitor's move, a price change, fading marketing spend, or a quality problem surfacing. Each of those has a different remedy, and the report will not tell you which one it is — it tells you where to look.</p>

<p><b>Return Rate</b> above roughly ten per cent needs attention, and the three usual causes are quality, misleading description, and mismatched expectation. They are distinguishable: quality problems cluster by batch or period, description problems affect every unit sold through a particular channel, and expectation problems show up alongside high ASP discounting where a customer was talked into something.</p>

<p><b>Filter by date, category and branch.</b> Regional preference differences are frequently the most actionable finding in the whole report — a product that under-performs nationally while selling strongly in two branches is not a weak product, it is a mis-targeted one, and that is a marketing decision rather than a discontinuation.</p>

<blockquote>IMPLEMENTATION TIP: Read Trend and Return Rate together before acting on either. Rising units with a rising return rate is not growth; it is a product being sold to people it does not suit, and the returns will arrive after the celebration.</blockquote>"""),

("Marketing ROAS — the money view", 8, """<p>ROAS is where money meets marketing, and it is the report most likely to be quoted confidently by someone who has misunderstood it. One row per campaign.</p>

<p><b>Ad Spend</b> is what the campaign cost. <b>Revenue Generated</b> is the delivered-order value attributed to it. <b>ROAS</b> is Revenue divided by Spend — the headline number.</p>

<p><b>Here is the misunderstanding to avoid.</b> Below 1.0, a campaign is returning less revenue than it consumed in spend, which is unambiguously bad. But 1.0 is not the break-even line, because <b>ROAS measures revenue, not profit</b>. A campaign at 2.0 on products carrying fifty per cent margin has generated exactly enough gross margin to pay for itself — before warehousing, before delivery, before the closer's time, before any overhead at all. That campaign is losing money while showing a number that sounds like a success.</p>

<p>The threshold that matters is therefore specific to your margins, and every business should know its own. Ask what ROAS actually covers cost here, write it down, and judge campaigns against that rather than against 1.0.</p>

<p><b>The efficiency ladder</b> — Leads Generated, Cost per Lead, Cost per Order — tells you where money is being lost when ROAS disappoints. Read it downward: what you paid for attention, what you paid for a lead, what you paid for an actual order. A campaign with cheap leads and expensive orders is not an advertising problem; it is a conversion problem, and no amount of budget reallocation will fix it.</p>

<p><b>Lead-to-Order Conversion</b> is that same insight as a single number. Weak conversion with cheap leads points squarely at the funnel — the follow-up, the closer capacity, the speed of first contact — rather than at the ads. This is the point where the marketing report and the New Lead backlog meet: leads arriving faster than the team can work them will show as poor campaign performance, and the campaign will get cut for a failure that belonged to staffing.</p>

<blockquote>IMPLEMENTATION TIP: Shift spend from low-ROAS to high-ROAS campaigns in small steps, and re-read after each move rather than making one large reallocation. Attribution depends on delivered orders, which lag the spend by the length of your delivery cycle — so a campaign switched off this week was being judged on incomplete data.</blockquote>

<blockquote>WATCH-OUT: A campaign's ROAS is only as honest as the Lead Channel recorded at order creation. Channels guessed rather than asked will attribute revenue to the wrong campaign, and budget will follow the attribution. This is the direct line between one closer's carelessness in a form field and a marketing decision worth millions of naira.</blockquote>"""),

("Revenue Cohort Trends — does anybody come back", 8, """<p>The Revenue Cohort Trends report is the long lens, and it answers a question no other report in the directory can: are we building a customer base, or renting one?</p>

<p><b>How a cohort works.</b> Customers are grouped by the month of their first purchase — everyone who first bought in March is the March cohort, permanently. Each cohort's spending is then tracked across the months that follow, laid out as a matrix: cohorts down the side, months across the top.</p>

<p><b>Reading the matrix is a matter of reading rows, not cells.</b> A row that stays strong across subsequent months means those customers came back. A row that collapses after month one means the business bought that revenue once and will have to buy it again — every naira of next month's revenue will have to come from new customers acquired at full cost.</p>

<p>That distinction is the difference between a business that compounds and one that runs to stand still. Two companies with identical monthly revenue can be in completely different health, and this is the only report that shows it.</p>

<p><b>Comparing rows tells you whether things are improving.</b> If recent cohorts hold up better than older ones, something changed for the better — a product improvement, better after-sales, a retention campaign. If they decay faster, something has worsened, and it usually worsened before revenue showed it. Cohort decay is a leading indicator; total revenue is a lagging one.</p>

<p><b>Who reads it, and for what.</b> Marketing managers use it to judge whether retention campaigns actually retain. Executives use it to judge the health of the base rather than the size of the month. Product managers use it to see whether an improvement drove repeat purchase or merely satisfied the people who complained.</p>

<p><b>The trap is impatience.</b> A cohort needs months to say anything. The most recent row is always the thinnest evidence in the table, and it is the one people look at first because it is the newest. Judge cohorts that have had time to behave, and treat the latest row as provisional.</p>

<blockquote>IMPLEMENTATION TIP: If you read only one thing here, read whether month-two retention is rising or falling across recent cohorts. Almost everything a business does to improve retention shows up there first, and it shows up months before it appears in revenue.</blockquote>

<p><b>One practical caution about cohort size.</b> A cohort is only as trustworthy as the number of customers in it. A month in which the business acquired thirty first-time buyers will produce a row that swings wildly — three of them returning is ten per cent, four is thirteen, and neither difference means anything. Check how many customers a cohort contains before reading its shape, and treat small cohorts as anecdote rather than evidence.</p>

<p><b>And one about what a cohort cannot tell you.</b> The report groups customers by when they first bought, not by what they bought or where they came from. Two customers in the same March row may have arrived through entirely different campaigns, bought entirely different products, and been served by different branches. A cohort that decays badly is a signal to go looking — into Channel Attribution, into Product Sales Analysis — rather than a finding on its own. It tells you retention is weak; it does not tell you for whom.</p>"""),

("Reading reports as a set — the investigation path", 8, """<p>Single-report conclusions are how managers get confidently misled. The directory is designed as an investigation path rather than a filing cabinet, and the skill that separates a manager who uses reports from one who merely opens them is knowing which report answers the question the last one raised.</p>

<p><b>Start with the pattern, not the report.</b> Something looks wrong: a closer's numbers fell, a product slowed, a campaign disappointed. The instinct is to act on the report where you noticed it. The discipline is to ask what else would be true if each possible explanation were correct — and then go and look.</p>

<p><b>Worked example one: a closer's conversion is falling.</b> The Closer Summary shows it, and the obvious reading is a performance problem. Before coaching anybody, check Team Performance: if the whole unit's cancellation rate is rising at the same time, this is not one closer. Then check ROAS and cost per lead: cheap leads arriving in volume from a new campaign will convert worse regardless of who works them. The closer may be handling worse raw material at the same rate as before. Coaching them would be both unfair and useless.</p>

<p><b>Worked example two: a product's trend is declining.</b> Product Sales Analysis shows the fall. If Return Rate is also elevated, this is a quality or expectation story and marketing spend will not fix it — it will accelerate the returns. If Return Rate is flat and ROAS on that product's campaigns has fallen, it is a demand-generation story instead. Same symptom, opposite remedies, and the only thing distinguishing them sits in a different report.</p>

<p><b>Worked example three: revenue is flat while order volume rises.</b> Check AOV on the Closer Summary. If AOV is falling, discounting or a shift to cheaper products is eating the gain — and Product Sales Analysis will show which, through Average Selling Price against list.</p>

<p><b>The habit underneath all three.</b> Write down the explanation you believe before you open the second report, then look for the thing that would disprove it. A manager who checks only for confirmation will find it in a directory this size every single time.</p>

<blockquote>CONSULTANT NOTE: Every report cross-references its neighbours by design. When a report leaves you with a conclusion and no next question, you have probably stopped early.</blockquote>

<blockquote>WATCH-OUT: The most expensive mistakes in this module are not misread numbers. They are correctly read numbers acted on without asking what else was true — cutting a campaign that was fine, coaching a closer who was handling bad leads, discontinuing a product that was merely mis-targeted.</blockquote>"""),

("The traps — periods, denominators, lag and small numbers", 8, """<p>Four failure modes account for most wrong conclusions drawn from these reports. None of them involves a broken report; all of them involve a correct number read without its conditions.</p>

<p><b>1. The period trap.</b> A figure without its date range means nothing, and two people comparing figures over different ranges will argue indefinitely without discovering why. Worse is the partial period: a month-to-date figure compared against a completed month will always look worse, because it is measuring less time. If you must compare a period in progress, compare it against the same point in the previous period — day eleven against day eleven — never against a finished one.</p>

<p><b>2. The denominator trap.</b> Every rate is a fraction, and the bottom half is where the meaning hides. Conversion is Delivered divided by Total, so anything that changes what counts as Total moves it without anybody's performance changing. A delivery rate that excludes cancelled orders is a different number from one that includes them, and a team judged on the first has an incentive to cancel marginal orders. Know the denominator before you set a target on the rate, because people optimise for what is measured, including in ways nobody intended.</p>

<p><b>3. The attribution lag trap.</b> Marketing reports depend on delivered orders, and delivery takes time. A campaign switched on this week has spent all its money and delivered only some of its orders, so its ROAS is understated — sometimes severely. Judge campaigns over a window at least as long as your delivery cycle, and be especially careful about killing a young campaign for underperformance it has not had time to demonstrate either way.</p>

<p><b>4. The small-numbers trap.</b> A closer with four orders and three deliveries shows seventy-five per cent conversion. So does a closer with four hundred and three hundred. They are not comparable claims, and the first is barely a claim at all — one more failed delivery would take it to sixty. Percentages on small bases move violently and mean little, which is why the loudest movements in any ranking are usually the smallest samples. Look at the base before you believe the rate, and be sceptical of anyone who tops a table on volumes far below their peers.</p>

<blockquote>IMPLEMENTATION TIP: Four questions before acting on any figure. What period is this? What is in the denominator? Has enough time passed for it to be complete? How big is the base? A manager who asks those four is wrong far less often than one who reads faster.</blockquote>

<blockquote>WATCH-OUT: These traps are most dangerous when a number agrees with what you already believed. Scepticism arrives naturally for figures that surprise us and has to be applied deliberately to figures that do not.</blockquote>"""),
]


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data["reports_analytics"]
    old = [(l["title"], len(re.sub(r"<[^>]+>", " ", l["html"]))) for l in mod["lessons"]]
    print("before: %d chapters, mean %d" % (len(old), sum(n for _t, n in old) / len(old)))
    for t, n in old:
        print("   %-52s %5d" % (t[:52], n))

    new = [{"title": t, "est": e, "html": h} for t, e, h in L]
    lens = [len(re.sub(r"<[^>]+>", " ", x["html"])) for x in new]
    print("\nafter: %d chapters, mean %d" % (len(new), sum(lens) / len(lens)))
    for x, n in zip(new, lens):
        print("   %-52s %5d%s" % (x["title"][:52], n, "  <-- SHORT" if n < 2500 else ""))

    if CHECK_ONLY:
        print("\n--check given; nothing written.")
        return
    mod["lessons"] = new
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\nWritten. Push with:")
    print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons")


if __name__ == "__main__":
    main()
