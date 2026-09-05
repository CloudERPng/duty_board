#!/usr/bin/env python3
"""Rebuild consultant module c4 — Reports & the Numbers.

Written against the CRM360/Pangea screenshots rather than inferred: every card
name, column, tab and filter below was read off the product. Where a figure is
quoted it is the one the product showed (ROAS 2.79x against ROI 178.7% on the
same spend and revenue), because a consultant course that invents numbers
teaches staff to tell clients things that are not true.

Target shape matches the finished tracks: ~490 words a chapter, three checks
each, one DRILL, and a <!--deep--> tail for the readers who want the argument
rather than the summary.
"""

import io
import json
import re

PATH = "academy_consultant_data.json"

CH = []

# ─────────────────────────────────────────────────────────── 1. the directory
CH.append({
 "title": "The report directory — categories, roles, and the universal date filter",
 "est": 5,
 "html": """
<p>Nineteen reports sit under Reports, and a consultant's first question is never
"what does this report say" but <b>"who is this report for"</b>. Show a closer the
cluster view and you have handed them their colleagues' numbers; show a cluster
lead only their own summary and you have hidden the job from them.</p>

<table border="1" cellpadding="5"><tr><th>Report</th><th>Whose screen</th></tr>
<tr><td>My Summary</td><td>the closer — their own orders, nobody else's</td></tr>
<tr><td>Orders Status (Overview / Closer Performance)</td><td>closer managers</td></tr>
<tr><td>Team Closer Summary</td><td>team leads — their team, and themselves in it</td></tr>
<tr><td>Cluster Members Status</td><td>cluster leads</td></tr>
<tr><td>Digital Marketer Leads · Ad Buyer Categories · Marketing ROAS</td><td>media buyers (also called digital marketers, also called ad buyers — three names, one role)</td></tr>
<tr><td>Upsell / Cross-sell</td><td>closers</td></tr>
<tr><td>Product Sales · Attribution · Cohort Trends · Branch Performance</td><td>the business — owner, manager, you</td></tr></table>

<p><b>Scope is not a filter you apply; it is applied to you.</b> Cluster Members
Status states it outright: <i>scope follows your reporting tier automatically</i>.
The same URL shows a cluster lead their cluster and a manager the lot. When a
client says "the report is wrong, I can't see Lagos", the first check is their
tier, not the data.</p>

<p><b>The date control is not one control.</b> Most reports carry a period
selector — Daily, Monthly, Custom — and several carry a second field, <b>Date
Type</b>, which decides <i>which</i> date is being filtered: order date, delivery
date, and so on. Two reports over "August" disagree constantly and almost always
because one counted when the order arrived and the other when it landed. Establish
the date type before you debug the numbers.</p>

<blockquote><b>DRILL:</b> A team lead says their delivery rate is 45% but the
manager's screen shows 58% for the same week. Where do you look first? — Not at
the data. At scope and date type: the lead sees their team, the manager sees
everyone, and one of the two screens may be filtering on delivery date rather than
order date. Reconcile the question before reconciling the figures.</blockquote>

<!--deep--><p><b>Why the role mapping matters more than the feature list.</b> Every
report here is technically available to explain, and a demonstration that walks all
nineteen teaches nothing. What a client remembers is <i>this is your screen, that
one is your manager's</i>. Deployments fail on people not knowing which number they
are accountable for, far more often than on a report being wrong.</p>

<p><b>The reports that answer the same question differently.</b> Orders Status,
Team Closer Summary and Cluster Members Status all count orders by closer. They are
not redundant — they differ in scope and in what they let you do next. Knowing why
three exist is the difference between configuring a client's reporting and
listing it.</p>
""",
 "checks": [
  {"q": "A closer asks why they cannot see their colleague's numbers on My Summary. The correct answer is:",
   "opts": ["My Summary is scoped to the person viewing it; a manager's view exists and is a different report",
            "A permission is missing and should be granted",
            "The report is broken and needs a refresh",
            "They should use Cluster Members Status instead"],
   "ans": 0, "why": "Scope follows reporting tier by design, not by configuration error.", "sort": 0},
  {"q": "Two reports disagree about August. The first thing to establish is:",
   "opts": ["Which date type each is filtering on, and each viewer's scope",
            "Whether the database needs reindexing",
            "Which report was opened most recently",
            "The brand filter"],
   "ans": 0, "why": "Order date versus delivery date, and tier scope, explain most disagreements before any data is at fault.", "sort": 1},
  {"q": "'Media buyer', 'digital marketer' and 'ad buyer' in this system are:",
   "opts": ["Three names for the same role", "Three separate roles with different permissions",
            "A hierarchy, buyer above marketer", "Country-specific job titles"],
   "ans": 0, "why": "One role, three labels — worth saying plainly to a client before it confuses a training session.", "sort": 2},
 ]})

# ───────────────────────────────────────────────────────── 2. closer summary
CH.append({
 "title": "Closer Summary — every column, the red flags, the coaching reads",
 "est": 5,
 "html": """
<p>Orders Status carries six cards and two tabs. The cards: <b>Total Orders ·
Total Value · Pending · Delivered · Confirmation Rate · Delivery Rate</b>. The
tabs: <b>Overview</b>, and <b>Closer Performance</b>, which is the coaching screen.</p>

<p>Closer Performance lists, per closer: <b>Total Orders · Confirmed · Delivered ·
Value · Confirmation Rate</b>. Two rates, and they fail for different reasons —
this is the whole of the chapter.</p>

<table border="1" cellpadding="5"><tr><th>Pattern</th><th>What it means</th><th>Coaching read</th></tr>
<tr><td>Low confirmation, delivery fine on what confirms</td><td>losing the customer on the call</td><td>a closer problem — script, objection handling, speed to first call</td></tr>
<tr><td>Confirmation good, delivery poor</td><td>the customer said yes and the order died after</td><td>rarely the closer — dispatch, stock, address quality, agent coverage</td></tr>
<tr><td>Both low, volume high</td><td>quantity without quality</td><td>check lead source before blaming anyone</td></tr>
<tr><td>Both 100%, volume 1</td><td>nothing at all</td><td>a single order proves nothing; say so rather than praising it</td></tr></table>

<p><b>"Unassigned" appears as a row in the closer list.</b> It is not a person. It
is orders nobody owns, and it carries a value like any other row — four orders
worth ₦77,000 in the screen this chapter was written from. That row is a finding,
not a closer: it means leads arrived while no one was on shift, or auto-assignment
had nobody eligible. Never coach it; escalate it.</p>

<p><b>The denominator discipline.</b> Confirmation Rate is colour-coded, and a red
0.0% on three orders and a red 0.0% on ninety are entirely different facts. The
colour treats them identically. Read the volume column first, every time, or you
will performance-manage somebody for a bad Tuesday.</p>

<blockquote><b>DRILL:</b> A closer shows 2 orders, 2 confirmed, 2 delivered, 100%.
The client wants them made team lead. Your answer? — On two orders you know
nothing. Ask for the same view over a quarter. A rate without a denominator is a
rumour, and promoting on one is how a client stops trusting the reports.</blockquote>

<!--deep--><p><b>Why confirmation and delivery must never be averaged into one
"performance" number.</b> A client will ask for it — a single score, sortable. It
would merge a problem the closer owns with one they do not, and the person at the
bottom would be whoever happened to sell into a region with poor dispatch. Refuse
it and explain why; that refusal is most of what they are paying you for.</p>

<p><b>The conversation this report actually starts.</b> Not "who is worst" but "why
does this row look like that". Closers know things the report cannot — a product
out of stock, a brand the market has turned on. The report tells you where to ask;
it does not tell you the answer.</p>
""",
 "checks": [
  {"q": "A closer's confirmation rate is high but delivery rate is poor. The likeliest cause is:",
   "opts": ["Something after the sale — dispatch, stock, address quality",
            "The closer is mis-selling", "The report is filtered wrongly", "The customer never existed"],
   "ans": 0, "why": "Confirmation is the closer's; what happens after the yes usually is not.", "sort": 0},
  {"q": "'Unassigned' shows in the Closer Performance list with four orders. It should be treated as:",
   "opts": ["A finding to escalate — orders nobody owns",
            "A closer with a poor record", "A rounding artefact", "Deleted orders"],
   "ans": 0, "why": "It means auto-assignment found nobody eligible, or leads arrived with no coverage.", "sort": 1},
  {"q": "Before reading any rate on this report you should first read:",
   "opts": ["The order count behind it", "The brand filter", "The colour coding", "The total value"],
   "ans": 0, "why": "A rate on two orders and a rate on two hundred are coloured the same and mean nothing alike.", "sort": 2},
 ]})

# ──────────────────────────────────────────────────────── 3. team + cluster
CH.append({
 "title": "Team Performance — aggregates and the fairness metric",
 "est": 4,
 "html": """
<p><b>Team Closer Summary</b> is the team lead's screen — their team, and
themselves inside it. Cards: <b>Total Orders · Delivered · Delivery Rate ·
Cancelled · Rejected · Delivered Value</b>. Filters run wide: period, state,
marketer, brand, category, branch, country.</p>

<p>Two panels do the work. <b>Closers in Scope</b> — closer, team manager, orders,
delivered, delivery %, cancelled. And <b>Top Delivery Rates</b>, a bar chart,
green for good and red for poor, on a fixed 0–100 axis.</p>

<p><b>That fixed axis is the fairness problem in one picture.</b> A closer with one
order and one delivery draws a full green bar identical to a closer with forty of
forty. The chart is honest about rate and silent about weight. Read it beside the
Orders column or do not read it at all.</p>

<p><b>The fairness metric, stated plainly:</b> compare rates only within comparable
volume, and compare volume only within comparable opportunity. A closer working a
strong brand in a well-covered branch is not being compared like-for-like with one
working a thin category in a region where dispatch is weak. The filters exist so
you can hold those things still — filter to one brand, one branch, then compare.</p>

<p><b>Cluster Members Status</b> is the tier above: one row per cluster member, one
column per order status — New Lead, Qualified, Confirmed, Assigned, Agent Notified,
Dispatch Assigned, Order Accepted, Processing, Delivery In Progress, Delivered,
Delivered Order Cancelled, Failed, Cancelled, Returned, Rejected, Duplicate, On
Hold — and a Totals row. It answers a different question: not <i>how good is this
person</i> but <i>where is the work stuck</i>. A column that is heavy across every
member is a process fault, not a people fault.</p>

<blockquote><b>DRILL:</b> Top Delivery Rates shows nine closers at 100% and one at
50%, and the client wants the 50% one managed out. What do you say? — Ask for the
Orders column. If the nine are on one order each and the tenth is on twenty, the
tenth is the only person you have any evidence about, and they are probably your
best closer.</blockquote>

<!--deep--><p><b>Reading a status column rather than a person row.</b> The cluster
matrix is usually taught row-wise, because rows are people and people are what
managers ask about. Read it column-wise and it becomes an operations report: a
stack in Agent Notified across ten members means agents are not responding; a stack
in Assigned means closers are not calling. Neither shows up row by row.</p>

<p><b>Where "Delivered Order Cancelled" sits.</b> It has its own column for a
reason — an order that was delivered and then cancelled is a different failure from
one cancelled before dispatch, and it costs the business the delivery. When that
column is non-zero, the conversation is about returns and refusals, not selling.</p>
""",
 "checks": [
  {"q": "The Top Delivery Rates chart plots every closer on a 0–100 axis. Its main limitation is:",
   "opts": ["It shows rate without weight — one order can draw a full bar",
            "It cannot be filtered", "It excludes cancelled orders", "It only shows the top three"],
   "ans": 0, "why": "Rate is meaningless without the order count beside it.", "sort": 0},
  {"q": "A single status column is heavy across every cluster member. That indicates:",
   "opts": ["A process fault at that stage", "A training need for one person",
            "A reporting error", "Seasonal demand"],
   "ans": 0, "why": "What is common to everyone is not about any of them.", "sort": 1},
  {"q": "Comparing two closers fairly on this report requires:",
   "opts": ["Holding brand, branch and period still, then comparing within similar volume",
            "Sorting by delivery rate", "Using the widest date range available", "Comparing delivered value only"],
   "ans": 0, "why": "Opportunity differs by brand, branch and period; the filters exist to remove that difference.", "sort": 2},
 ]})

# ───────────────────────────────────────────────────────────────── 4. ROAS
CH.append({
 "title": "ROAS — the formula, the profitability threshold, the budget loop",
 "est": 6,
 "html": """
<p>Marketing ROAS is the budget report, and the most misread screen in the product.
Cards: <b>Total Spend · Ad-Attributed Leads · Delivered Orders · Delivered Revenue ·
Delivery Rate · ROAS · ROI</b>. Tabs: <b>By Campaign · By Order · By Product ·
By Marketer · Spend Entries</b>. Filters: period, from, to, campaign, country,
brand — plus a <b>Log Ad Spend</b> button, which matters more than it looks.</p>

<p><b>ROAS and ROI are the same arithmetic said two ways, and clients confuse
them.</b> On one real period: spend ₦256,549,638, delivered revenue ₦714,888,736 —
<b>ROAS 2.79x</b> and <b>ROI 178.7%</b>. ROAS is revenue ÷ spend. ROI is the gain
over spend, so it is always ROAS minus one, expressed as a percentage. Neither is
profit.</p>

<p><b>The theorem to carry into every client conversation: ROAS measures revenue,
not profit. Profitability needs ROAS greater than 1 ÷ gross margin.</b> At 50%
margins the threshold is 2.0 — a campaign at 2.0 broke even. At 30% margins it is
3.33. Compute the client's own threshold in the first reporting session and write
it on the report, because without it every number here flatters.</p>

<p><b>The attribution caveat, which the product states and consultants skip.</b>
Ad-Attributed Leads counts only leads that arrived through a tracked campaign form,
credited to an ad buyer. It <i>excludes phone, WhatsApp and manually entered
orders</i>, so it is lower than Total Leads Generated on the Digital Marketer Leads
tab. The two figures are both right and will never match. Say that before a client
finds it themselves.</p>

<p><b>Spend Entries is where the report is true or false.</b> Spend is logged by
hand — date, campaign, country, amount, owner, notes — and every ROAS on the screen
inherits whatever was typed. A campaign with spend missing shows a spectacular
ROAS. Check the entries before you interpret the ratios; a 10.14x that nobody can
explain is usually an unlogged invoice, not a genius.</p>

<blockquote><b>DRILL:</b> A client sees ROAS 2.4x and wants to triple the budget.
Their gross margin is 35%. Your answer? — Their threshold is 1 ÷ 0.35 = 2.86. At
2.4 they are losing money on that campaign. Tripling it triples the loss. Fix
targeting and creative first, and if it has not crossed 2.86 in two weeks, cut
it.</blockquote>

<!--deep--><p><b>The budget loop, in order.</b> Sort by ROAS descending. Identify
the top three to five and consider raising their budgets. Identify everything under
the client's own profitability threshold. Optimise those first — targeting,
creative, offer — and if ROAS has not moved within two weeks, reduce or pause.
Re-run monthly. The loop only works if the threshold was computed from the client's
margin rather than borrowed from an article.</p>

<p><b>Why By Marketer is the tab that starts arguments.</b> It ranks people by
spend, delivered value, delivered % and ROAS. A buyer with a small budget and a
narrow product will out-ROAS one carrying the flagship spend, every time. Rank
within comparable budget or the report becomes a weapon rather than an
instrument.</p>
""",
 "checks": [
  {"q": "A client's gross margin is 40%. Their ROAS profitability threshold is:",
   "opts": ["2.5", "1.4", "4.0", "0.4"],
   "ans": 0, "why": "1 ÷ 0.40 = 2.5. Below that, revenue does not cover the cost of goods plus the ad spend.", "sort": 0},
  {"q": "Ad-Attributed Leads is lower than Total Leads Generated because it:",
   "opts": ["Excludes phone, WhatsApp and manually entered orders",
            "Counts only delivered orders", "Excludes repeat customers", "Is calculated weekly"],
   "ans": 0, "why": "Only leads through a tracked campaign form are credited to an ad buyer.", "sort": 1},
  {"q": "One campaign shows ROAS 10.14x, far above every other. Check first:",
   "opts": ["Whether all its ad spend has been logged in Spend Entries",
            "Whether to double its budget immediately", "The delivery rate", "The brand filter"],
   "ans": 0, "why": "Spend is entered by hand; missing spend produces a spectacular and false ratio.", "sort": 2},
 ]})

# ────────────────────────────────────────────────── 5. product + attribution
CH.append({
 "title": "Product Sales & Channel Attribution — mix, pricing signals, channel truth",
 "est": 5,
 "html": """
<p><b>Product Sales</b> answers what is selling. Cards: <b>Total Units Sold · Total
Sales Amount · Unique SKUs Sold · Top Product</b>. The distribution chart carries a
toggle — <b>By Sales</b> or <b>By Units</b> — and that toggle is the chapter.</p>

<p>A product's share of units and its share of naira are different numbers, and the
gap between them is a pricing signal. On one real period a product held 12.5% of
units and 7% of sales; another held 0.7% of units and 14.4% of sales. The first
moves volume at a low price, the second is a high-value item selling rarely.
Neither fact is visible with the toggle in one position, which is why clients who
only ever look at one of them make the wrong call about which line to push.</p>

<p>The <b>Product Performance</b> table gives product group, SKU, product name,
units sold, sales value, units % and sales % — the two percentages side by side, so
you can read the divergence without toggling at all.</p>

<p><b>Attribution</b> answers where revenue comes from. Revenue by Channel, with
channel, revenue, orders, average order and share, over the usual timeframe
control. The channels are real routes, not campaigns: WhatsApp, Repeat Customer,
WordPress, Phone.</p>

<p><b>Repeat Customer is a channel, and that is the most useful thing on the
screen.</b> It separates revenue you paid to acquire from revenue you already
earned. A client celebrating strong revenue while their non-repeat channels shrink
is watching their own base carry them, and that is a finite trick. The average
order column is the second read: a channel with fewer orders but a far higher
average is worth more attention than its share suggests.</p>

<blockquote><b>DRILL:</b> Attribution shows WhatsApp at 54.3% of revenue on 11
orders; Repeat Customer at 35.3% on 13. The client wants to cut WhatsApp spend
because it has fewer orders. Your answer? — WhatsApp's average order is ₦51,591
against ₦28,346. Fewer orders, larger ones. Cutting it removes the most valuable
route, and Repeat Customer is not a route you can buy more of.</blockquote>

<!--deep--><p><b>Why Attribution and ROAS will not reconcile, and should not.</b>
Attribution counts revenue by the channel it arrived through, all of it. ROAS
counts only what a tracked campaign form attributed to an ad buyer, and excludes
phone, WhatsApp and manual orders entirely. A client comparing the two and finding
a gap has found the design, not a fault. Explain it once, early, in writing.</p>

<p><b>Unique SKUs Sold, the quiet number.</b> It counts breadth. A month where
units and revenue held steady but unique SKUs fell means the range is narrowing —
fewer lines carrying the same weight. That is a concentration risk long before it
is a revenue problem, and nothing else on the dashboard shows it.</p>
""",
 "checks": [
  {"q": "A product holds 0.7% of units and 14.4% of sales value. It is:",
   "opts": ["A high-value item selling in low volume", "A loss-leader",
            "A data error", "The best-selling product"],
   "ans": 0, "why": "The gap between unit share and value share is the pricing signal.", "sort": 0},
  {"q": "'Repeat Customer' appearing as a channel in Attribution lets you:",
   "opts": ["Separate revenue you paid to acquire from revenue the existing base produced",
            "Measure delivery performance", "Track ad spend", "Identify duplicate orders"],
   "ans": 0, "why": "A business carried by its own base is not growing, however good the revenue looks.", "sort": 1},
  {"q": "Attribution revenue and ROAS delivered revenue do not match. This is:",
   "opts": ["Expected — ROAS counts only ad-attributed orders", "A bug to report",
            "A date filter error", "A currency conversion issue"],
   "ans": 0, "why": "Attribution counts every channel; ROAS counts only tracked campaign forms.", "sort": 2},
 ]})

# ──────────────────────────────────────────────────────────── 6. cohorts
CH.append({
 "title": "Revenue Cohorts — the matrix, healthy retention, warning signs",
 "est": 5,
 "html": """
<p><b>Cohort Trends</b> groups customers by when they first bought and tracks what
each group spends in the months after. It is the only report here that answers
whether the business is building anything, as opposed to selling something.</p>

<p>Read it as a matrix: a row per cohort — the month they first bought — and a
column per month since. The first column is acquisition. Everything to its right is
retention, and retention is the whole point.</p>

<table border="1" cellpadding="5"><tr><th>What you see</th><th>What it means</th></tr>
<tr><td>Row falls sharply after month 1, near zero by month 3</td><td>a one-purchase business — every naira of growth must be bought</td></tr>
<tr><td>Row declines then flattens</td><td>a genuine repeat base; the flat part is the asset</td></tr>
<tr><td>Recent rows thinner than older rows at the same age</td><td>acquisition quality is falling — the newer customers are worth less</td></tr>
<tr><td>A row that rises after month 2</td><td>usually a reorder cadence landing, not a miracle</td></tr></table>

<p><b>That last row is where this report meets the rest of the product.</b>
After-sales reorder scheduling puts a chase call on delivered orders at a computed
date — fourteen days for a single-unit order, twenty-nine for multi-unit, so the
call lands a day or two before a thirty-day supply runs out. A cohort that lifts in
month one is often that machinery working. If cohorts are flat and the reorder
cadence is switched off, you have found the client's cheapest available growth.</p>

<p><b>The comparison that matters is same-age, not same-month.</b> Comparing a
January cohort's month-six figure against an August cohort's month-one figure tells
you nothing except that January had longer. Read down a column, not across a
row.</p>

<blockquote><b>DRILL:</b> A client's revenue is up 30% year on year, but every
cohort row flattens near zero by month three. What have you found? — A business
buying its growth. Revenue is rising because acquisition is rising, and the day ad
spend stops, so does revenue. That is a strategy conversation, not a reporting
one, and this is the only screen that shows it.</blockquote>

<!--deep--><p><b>Why cohorts are the report clients ask for last and need
most.</b> Every other screen rewards a good month. This one asks whether last
year's good months are still paying, and the answer is frequently uncomfortable.
Bring it to a quarterly review rather than a weekly one — it moves too slowly to
watch and too meaningfully to skip.</p>

<p><b>The small-cohort trap.</b> An early month with nine customers will swing
wildly and mean almost nothing; a later month with nine hundred will move slowly
and mean a great deal. Cohort tables invite eye-reading across a grid where the
rows have wildly different weights. Check the cohort size before believing any row,
the same discipline as the denominator on Closer Performance.</p>
""",
 "checks": [
  {"q": "Cohort rows fall to near zero by month three while revenue grows. The business is:",
   "opts": ["Buying its growth — revenue depends on continued acquisition",
            "Retaining well", "Under-pricing", "Over-delivering"],
   "ans": 0, "why": "No retention means every naira of growth must be purchased again.", "sort": 0},
  {"q": "Cohorts should be compared:",
   "opts": ["At the same age — down a column, not across a row",
            "In the same calendar month", "By total revenue only", "Against the largest cohort"],
   "ans": 0, "why": "An older cohort has simply had longer; only same-age comparison is meaningful.", "sort": 1},
  {"q": "A cohort lifts in month one. The likeliest explanation in this product is:",
   "opts": ["The after-sales reorder chase landing on cadence", "A data error",
            "A price rise", "Seasonal demand"],
   "ans": 0, "why": "Delivered orders schedule a reorder call at 14 days single-unit, 29 multi-unit.", "sort": 2},
 ]})

# ─────────────────────────────────────────────────────────────────── apply
d = json.load(io.open(PATH, encoding="utf-8"))
d["c4"]["lessons"] = CH
d["c4"]["desc"] = ("The report library at consultant level: who each report belongs to and how "
                   "scope follows reporting tier, the two rates on Closer Performance and what "
                   "each failure means, fairness when comparing closers, ROAS against the client's "
                   "own profitability threshold, the mix and channel reads, and cohorts as the "
                   "test of whether anything is being built.")
io.open(PATH, "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")

wc = lambda h: len(re.sub(r"<[^>]+>", " ", h).split())
print("c4 rebuilt — %d chapters" % len(CH))
for i, c in enumerate(CH, 1):
    print("  ch%d %4dw %d checks  %s" % (i, wc(c["html"]), len(c["checks"]), c["title"][:52]))
print("  mean %d words | %d checks total" % (
    sum(wc(c["html"]) for c in CH) // len(CH), sum(len(c["checks"]) for c in CH)))
