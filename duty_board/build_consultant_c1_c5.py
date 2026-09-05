#!/usr/bin/env python3
"""Rebuild consultant modules c1 (Platform & Dashboard) and c5 (Closers & Shifts).

c1 needed correcting, not merely extending: the previous text described four core
cards including "Total Revenue", timeframe presets of Today/Yesterday, a chart
called "Revenue Trend", and a worked example in AED. The product has twenty-four
status cards, a Day/Week/Month/Quarter/Year timeframe, charts named Delivered
Value Trend, Outcome Breakdown and Status Distribution, and runs in NGN. A
consultant taught the old version would have been wrong in front of a client
within a minute of opening the dashboard.

c5 was closer to the mark. Its shift specifics are preserved and the settings
behaviour is corrected against the CRM360 Settings screens, whose help text is
quoted where the exact wording is what a consultant has to be able to repeat.
"""

import io
import json
import re

PATH = "academy_consultant_data.json"

# ══════════════════════════════════════════════════ c1 — Platform & Dashboard
C1 = []

C1.append({
 "title": "Access, credentials, and sessions — what you'll support daily",
 "est": 4,
 "html": """
<p>Half of week-one tickets are access, and none of them are interesting. Know
the shape cold so you can clear them in a sentence.</p>

<p><b>What a person needs to log in:</b> an account created by an administrator,
the tenant URL, and a modern browser. Nothing else. There is no self-registration —
if somebody has no account, an administrator creates one, and that is the whole
answer to "how do I sign up".</p>

<p><b>The tenant URL is per client.</b> Sessions belong to a browser and a tenant.
A consultant working three clients in one browser will be logged into one of them,
and the symptom is data that looks wrong rather than an error message. Use separate
profiles or a private window per tenant and you remove a whole category of
confusion — including your own.</p>

<p><b>The two failures that look identical and are not.</b> "I can log in but the
page is empty" is almost always scope: the account exists, has no reporting tier
or no assigned records, and is correctly showing nothing. "I cannot log in" is
credentials. Establish which you are looking at before touching anything, because
the fixes are in different places and one of them is not yours.</p>

<p><b>The account and the person are different objects.</b> A User is who logs in.
A Closer is the sales record that leads attach to, and it links to a User. Creating
one does not create the other, and the commonest onboarding fault in the whole
product is a closer who exists as a person, exists as a User, and has no Closer
record — so auto-assignment never sees them and they sit idle wondering why no
leads arrive. That is chapter one of module five, and it starts here.</p>

<blockquote><b>DRILL:</b> A new starter says the dashboard is blank on day one.
Two questions, in order? — Can they see anything at all, or is the page empty?
Empty means scope, so check their tier and whether a Closer record exists. If they
cannot reach a page at all, it is credentials or the wrong tenant URL. Do not
begin with the data.</blockquote>

<!--deep--><p><b>Why access tickets are worth answering well rather than fast.</b>
They are a client's first experience of your support, they arrive in the first
week when confidence is being formed, and they are the only tickets where the
answer is always knowable. A consultant who is crisp here buys a great deal of
patience for the harder questions later.</p>

<p><b>The session trap in a training session.</b> Running a workshop from one
browser, demonstrating as an administrator, then telling closers "your screen will
look like this" — it will not. Administrators see everything; closers see their
own. Demonstrate from a closer's login when teaching closers, or you will train
them on a screen they never get.</p>
""",
 "checks": [
  {"q": "A user logs in successfully but sees an empty dashboard. The likeliest cause is:",
   "opts": ["Scope — no reporting tier or no records assigned to them",
            "A corrupted browser cache", "Their password expired", "The tenant is down"],
   "ans": 0, "why": "Logging in proves credentials work; an empty page after that is almost always scope.", "sort": 0},
  {"q": "A User account and a Closer record are:",
   "opts": ["Different objects — a User logs in, a Closer receives leads",
            "The same record with two names", "Created together automatically", "Interchangeable"],
   "ans": 0, "why": "A person with a User and no Closer record will never be auto-assigned a lead.", "sort": 1},
  {"q": "Demonstrating the product to closers is best done from:",
   "opts": ["A closer's login, because an administrator sees screens they never will",
            "The administrator account, for full visibility",
            "A shared training account", "Whichever is already open"],
   "ans": 0, "why": "Training on a screen the audience cannot reach teaches them the wrong product.", "sort": 2},
 ]})

C1.append({
 "title": "The dashboard — layout, hierarchy, and role-based views",
 "est": 4,
 "html": """
<p>The dashboard answers "where is work piling up" in seconds, and it is built in
three bands, top to bottom.</p>

<p><b>Band one: the timeframe.</b> A caption states the current scope in words —
<i>Showing this month</i> — with the selector at the right: <b>Day · Week · Month ·
Quarter · Year</b>. Everything below obeys it. Read the caption before reading any
number; it is the single commonest cause of a client and a consultant looking at
different figures on the same screen.</p>

<p><b>Band two: the status cards.</b> Around two dozen of them, each a label and a
number, laid out in rows. They fall into two groups sitting side by side —
lifecycle cards describing where orders are in the flow, and performance cards
describing outcomes and rates for the period. Most are live counts; some are
percentages, such as <b>Delivery Rate (Period)</b>.</p>

<p><b>Every card is a shortcut.</b> Click one and the Orders list opens filtered to
exactly the orders behind that number. For a closer the list narrows to their own.
This is the fastest route in the product from "there are 45 on hold" to the
specific list to work, and clients routinely never discover it.</p>

<p><b>The set of cards is not fixed.</b> It is driven by the system and the
selected timeframe, so the row can change as the business configuration changes.
That is intentional — the dashboard surfaces the buckets that matter rather than a
permanent list. Teach it as a live surface, not a layout to memorise.</p>

<p><b>Band three: three charts.</b> <b>Delivered Value Trend</b> (revenue
progression), <b>Outcome Breakdown</b> (operational outcomes), and <b>Status
Distribution</b> (share by status). The next chapters take the cards and the charts
in turn.</p>

<blockquote><b>DRILL:</b> A client says the dashboard "changed overnight — cards
have moved". Is this a fault? — Almost certainly not. The card set follows system
configuration and the selected timeframe. Check what changed in configuration
before raising anything, and reassure them the surface is meant to move.</blockquote>

<!--deep--><p><b>Why the caption matters more than the selector.</b> The selector
shows a highlighted button; the caption says <i>Showing this month</i> in plain
words. In a call, ask the client to read you the caption rather than describe the
buttons. It removes an entire class of misunderstanding in one sentence.</p>

<p><b>The card that teaches the product.</b> AGENT UPDATE holds orders just
updated by delivery agents, so closers can see current agent activity without
hunting. It exists because closers were chasing agents for information the system
already had. When a client asks what a card is <i>for</i> rather than what it
counts, that is the shape of the answer.</p>
""",
 "checks": [
  {"q": "Clicking a dashboard status card:",
   "opts": ["Opens the Orders list filtered to exactly those orders",
            "Exports the count to CSV", "Changes the timeframe", "Opens a report"],
   "ans": 0, "why": "It is the fastest route from a count to the list you must act on; for a closer it narrows to their own orders.", "sort": 0},
  {"q": "The set of status cards shown can change over time because:",
   "opts": ["It is driven by system configuration and the selected timeframe",
            "Cards rotate weekly", "Users can reorder them", "It depends on browser width"],
   "ans": 0, "why": "The dashboard surfaces the buckets that currently matter rather than a fixed list.", "sort": 1},
  {"q": "The dashboard timeframe options are:",
   "opts": ["Day, Week, Month, Quarter, Year", "Today, Yesterday, Last 7 days, Custom",
            "Daily and Monthly only", "A free date range only"],
   "ans": 0, "why": "Five presets, with a caption stating the current scope in words.", "sort": 2},
 ]})

C1.append({
 "title": "KPI cards — every formula, and reading them as a set",
 "est": 5,
 "html": """
<p>There is no single "revenue" card. The dashboard is a wall of order counts by
status, plus a few rates, and reading it means reading the <b>shape</b> rather than
any one number.</p>

<p><b>The lifecycle cards</b> follow an order through its life: Total Orders,
Agent Update, Assigned, Agent Notified, Dispatch Assigned, Order Accepted, Delivery
In Progress, Delivery Rescheduled, and onward to the outcomes — Delivered,
Cancelled, Rejected, Duplicate, No Stock, Failed / Returned, Not Reachable, Not
Picking, Call Back, Not Ready, On Hold.</p>

<p><b>The period cards</b> are a different animal and get misread constantly:
<b>Assigned (Period) · Rescheduled (Today) · Rescheduled (Tomorrow) · Rejected
(Period) · Delivery Rate (Period)</b>. A card without "(Period)" and one with it
are answering different questions, and a client comparing them will find a
discrepancy that is not one.</p>

<p><b>Delivery Rate (Period)</b> is the only ratio in the wall: delivered against
total, as a percentage. Everything else is a count. A rate and a count do not move
together — a good month can raise the count and lower the rate, and that is the
most useful sentence you can teach a client about this screen.</p>

<p><b>Read them as a set, in three moves.</b> First, a big number in an early-stage
bucket means leads are waiting and nobody is working them. Second, a build-up in a
mid-stage bucket points at delivery or fulfilment rather than at closers. Third,
when a number surprises you, click through immediately — the list behind the count
almost always explains it faster than reasoning about it does.</p>

<blockquote><b>DRILL:</b> Not Ready shows 37,839 while Delivered shows 12 for the
same month. Is the business failing? — No: those two cards are not scoped alike.
Delivered is counting the period; the large lifecycle counts are standing
populations that accumulate. Click both before concluding anything — the shape of
the wall is a map, not a scoreboard.</blockquote>

<!--deep--><p><b>Why "scan at the start of each shift" is the actual
instruction.</b> The cards reward a habit, not an analysis. Thirty seconds at the
top of a shift tells a closer where the work is; the same wall studied for twenty
minutes tells them very little more. Teach the habit and the click-through, and
leave the deep reads to the reports.</p>

<p><b>The trap in teaching formulas here.</b> Consultants like formulas because
they are teachable. Most of these cards are counts of a status, so the formula is
the status definition — which means module two, on the order lifecycle, is where
the real teaching happens. Explaining a card without knowing what its status means
operationally is how a consultant sounds fluent and helps nobody.</p>
""",
 "checks": [
  {"q": "'Assigned' and 'Assigned (Period)' differ because:",
   "opts": ["One is a standing count and the other is scoped to the period",
            "One includes cancelled orders", "One is a percentage", "They are duplicates"],
   "ans": 0, "why": "Comparing them produces a discrepancy that is not a fault.", "sort": 0},
  {"q": "A month where delivered orders rose but Delivery Rate (Period) fell means:",
   "opts": ["Total orders grew faster than deliveries — a count and a rate can move apart",
            "The data is wrong", "Deliveries were double-counted", "The timeframe was changed"],
   "ans": 0, "why": "A rate has a denominator; a count does not.", "sort": 1},
  {"q": "A build-up in a mid-stage lifecycle bucket most likely points at:",
   "opts": ["Delivery or fulfilment", "Closer performance", "Ad spend", "Lead quality"],
   "ans": 0, "why": "Early-stage build-up means leads unworked; mid-stage means the order is stuck after the sale.", "sort": 2},
 ]})

C1.append({
 "title": "Timeframes — the filter that rules the page",
 "est": 4,
 "html": """
<p>One control, top right, five options: <b>Day · Week · Month · Quarter ·
Year</b>. It drives the cards and the charts together, and a caption beneath the
page title states the result in words — <i>Showing this month</i>.</p>

<p><b>It is the first thing to check and almost the last thing anyone checks.</b>
Nearly every "these numbers are wrong" conversation ends here. Two people on a call
looking at the same dashboard on different timeframes will disagree indefinitely
and neither will be wrong.</p>

<p><b>The timeframe is not the same control as a report's date filter.</b> Reports
carry their own — Daily, Monthly, Custom with from and to — and several carry a
<b>Date Type</b> field deciding which date is filtered, such as Order Date. The
dashboard has no Date Type: it is a live operational surface, not an analysis
tool. Expecting it to reconcile to a report on a chosen date basis is a category
error, and worth saying out loud before a client tries it.</p>

<p><b>What each window is actually good for.</b> Day is the shift view — what
arrived and what is stuck right now. Week is the coordination view, long enough to
absorb a bad Tuesday. Month is the management view and the default for most
conversations. Quarter and Year exist for trend, and are the wrong lens for
operational decisions, because a fortnight of trouble disappears inside a
quarter.</p>

<blockquote><b>DRILL:</b> A client insists delivery rate has collapsed; your screen
shows it healthy. Neither of you has changed anything. First move? — Ask them to
read the caption aloud. If they are on Day and you are on Month, you are both
looking at the truth and at different truths. Agree the window before agreeing
anything else.</blockquote>

<!--deep--><p><b>Why the operational default should be Month, and the operational
habit should be Day.</b> Month is where targets, budgets and conversations live, so
it is the right default for a screen a manager opens. Day is where work is, so it
is the right habit for a closer at the start of a shift. A client who sets one
default for everybody has made one of those two groups worse off.</p>

<p><b>The reconciliation conversation, had once and early.</b> Dashboard and
reports will differ. The dashboard is live and scoped by a simple window; reports
carry date type, brand, branch, country and tier scope. Put that in writing at
handover and you will not have the same call every month.</p>
""",
 "checks": [
  {"q": "The dashboard timeframe differs from a report's date filter chiefly because:",
   "opts": ["Reports also carry a Date Type deciding which date is filtered",
            "The dashboard cannot be filtered", "Reports are always monthly", "The dashboard uses UTC"],
   "ans": 0, "why": "The dashboard is a live operational surface; reports are analysis tools with more control.", "sort": 0},
  {"q": "Two people disagree about the same dashboard figure. The first move is:",
   "opts": ["Have them read the timeframe caption aloud", "Clear the browser cache",
            "Check the database", "Compare user roles"],
   "ans": 0, "why": "Different windows produce different truths, and neither party is wrong.", "sort": 1},
  {"q": "Quarter and Year are the wrong lens for operational decisions because:",
   "opts": ["A fortnight of trouble disappears inside them", "They load slowly",
            "They exclude cancelled orders", "They are manager-only"],
   "ans": 0, "why": "Trend windows smooth away exactly the signal an operational decision needs.", "sort": 2},
 ]})

C1.append({
 "title": "The charts — reading, interaction, cross-reads",
 "est": 4,
 "html": """
<p>Three charts sit below the cards, and each answers a different question.</p>

<p><b>Delivered Value Trend</b> — subtitled <i>revenue progression</i>. Value
delivered over the selected window, plotted as a line with the area beneath it
filled. It answers "is money actually landing", and it moves only when orders
reach Delivered. A flat line with busy cards above it means plenty of activity and
nothing completing.</p>

<p><b>Outcome Breakdown</b> — subtitled <i>operational outcomes</i>. A bar chart
comparing how orders ended. It answers "when orders finish, how do they finish",
which is the question the status wall cannot answer because counts sitting in
mid-flight drown it.</p>

<p><b>Status Distribution</b> — subtitled <i>share by status</i>. A doughnut giving
proportion rather than count. It answers "what does the book look like", and it is
the chart to show a client who is anxious about one large number: a frightening
count is often an unremarkable share.</p>

<p><b>The cross-read that matters.</b> Take Delivered Value Trend against Outcome
Breakdown. Rising value with a healthy outcome mix is a good month. Rising value
with a worsening mix means volume is covering a quality problem, and it will stop
covering it. Neither chart shows that alone; the pair does, and pointing it out is
the sort of thing clients remember a consultant for.</p>

<p><b>What the charts are not.</b> They are a live operational read on the selected
window, not analysis. Cohorts, attribution, product mix and return on ad spend all
live in Reports, and a client trying to run strategy off the dashboard charts is
using a thermometer to plan a holiday.</p>

<blockquote><b>DRILL:</b> Delivered Value Trend is flat for three weeks then spikes
at the end. The client is delighted. What do you check? — Whether orders were
completing all along or whether a batch was marked delivered in one go. A spike at
a period end is often an administrative event rather than a commercial one, and the
Outcome Breakdown beside it usually says which.</blockquote>

<!--deep--><p><b>Why proportion calms people and counts alarm them.</b> A client
seeing 37,839 in a bucket reacts to the digits. The same figure as a slice of a
doughnut is a shape they can judge. When a conversation is heated, move it to
Status Distribution — not to soften the news, but because share is the honest frame
for "is this normal".</p>

<p><b>The habit worth installing.</b> Cards to find where work is stuck; charts to
find whether the month is behaving; reports for anything that requires a decision
about money. Three surfaces, three jobs. Clients who conflate them end up making
budget decisions off a live counter.</p>
""",
 "checks": [
  {"q": "Delivered Value Trend moves only when orders:",
   "opts": ["Reach Delivered", "Are created", "Are assigned to a closer", "Are dispatched"],
   "ans": 0, "why": "A flat line under busy cards means activity that is not completing.", "sort": 0},
  {"q": "Rising delivered value alongside a worsening outcome mix means:",
   "opts": ["Volume is covering a quality problem", "The month is healthy",
            "The charts disagree and one is wrong", "Ad spend has increased"],
   "ans": 0, "why": "Neither chart shows it alone; the cross-read does.", "sort": 1},
  {"q": "A client wants to plan ad budget from the dashboard charts. The right answer is:",
   "opts": ["Move them to Reports — the charts are a live operational read, not analysis",
            "Export the charts to CSV", "Switch the timeframe to Year", "Add a custom chart"],
   "ans": 0, "why": "Cohorts, attribution, product mix and ROAS all live in Reports for a reason.", "sort": 2},
 ]})

# ══════════════════════════════════════════════════ c5 — Closers & Shifts
C5 = []

C5.append({
 "title": "The Closer record — what it is, and the golden rule",
 "est": 4,
 "html": """
<p>A Closer is the record representing a salesperson who works leads and orders,
and almost everything in the product routes through it. Auto-assignment targets
closers. Orders attribute to them. The follow-up pool draws from them. Every
performance report counts by them.</p>

<p><b>The golden rule: the Closer must link to a User account, and the link is by
email.</b> Get that link wrong and everything downstream behaves strangely without
erroring — the person logs in and sees nothing that belongs to them, or leads
assign to a name nobody recognises. It is the single highest-value check in the
entire administration module, and it takes four seconds.</p>

<p><b>Two records, one person, and neither creates the other.</b> A User is who
logs in. A Closer is who receives work. Creating a User does not create a Closer.
The commonest onboarding fault in the product is a real person with a working login
and no Closer record: they are present, they are enabled, they are waiting, and
auto-assignment cannot see them at all.</p>

<p><b>What happens when a closer leaves.</b> The instinct is to delete. Do not.
Their orders, their history and every report they appear in depend on the record
existing. Disable it instead — new assignments stop, history is preserved, and the
reports remain truthful about the months they worked. A deleted closer takes their
past with them, and the first month-end after that is painful.</p>

<blockquote><b>DRILL:</b> A client reports a closer "not receiving any leads" on
their first morning. What do you check, in order? — Does a Closer record exist at
all; is it enabled; does it link to the right User by email; does the person have
categories or a remit that matches the leads arriving. In practice the answer is
one of the first three about nine times in ten.</blockquote>

<!--deep--><p><b>Why the golden rule is stated as a rule rather than a step.</b>
Steps get skipped when somebody is in a hurry; rules get checked. A consultant who
says "confirm the User link by email" at every handover, every time, prevents more
support tickets than any amount of training on the rest of the form.</p>

<p><b>The symptom that never says what it is.</b> Nothing errors when the link is
wrong. The person simply has an empty screen and a suspicion that the software is
broken, and clients escalate that as a bug. Recognising the shape of it — quiet,
plausible, and entirely a configuration fault — is what separates a consultant
from a manual.</p>
""",
 "checks": [
  {"q": "A Closer record links to a User account by:",
   "opts": ["Email", "Employee number", "Phone number", "Full name"],
   "ans": 0, "why": "The link is by email, and getting it wrong fails silently.", "sort": 0},
  {"q": "A closer leaves the business. You should:",
   "opts": ["Disable the record, preserving history and stopping new assignments",
            "Delete the record", "Reassign it to their replacement", "Leave it enabled"],
   "ans": 0, "why": "Deleting takes their orders and their appearance in every past report with them.", "sort": 1},
  {"q": "A new starter can log in but receives no leads. The likeliest cause is:",
   "opts": ["No Closer record exists, or it is disabled or linked to the wrong User",
            "The dashboard is cached", "Their password is temporary", "Shift management is off"],
   "ans": 0, "why": "A User account alone is invisible to auto-assignment.", "sort": 2},
 ]})

C5.append({
 "title": "Anatomy — the six blocks of a Closer",
 "est": 5,
 "html": """
<p>The form is one scrolling page. Read it as six blocks and it stops being a list
of fields.</p>

<table border="1" cellpadding="5"><tr><th>Block</th><th>What it decides</th></tr>
<tr><td><b>Identity</b></td><td>the link to the User account by email — the golden-rule field — plus the display name that appears on leads, orders and every report, and a contact number</td></tr>
<tr><td><b>Status</b></td><td>whether the record is enabled, and therefore whether auto-assignment can see it at all</td></tr>
<tr><td><b>Remit</b></td><td>the categories, brands, branches or countries this closer works — what they are eligible to receive</td></tr>
<tr><td><b>Reporting</b></td><td>team manager and tier — which decides not only who manages them but what they can see, because scope follows reporting tier automatically</td></tr>
<tr><td><b>Availability</b></td><td>shift-related flags, including whether they are always available regardless of shift</td></tr>
<tr><td><b>Follow-up</b></td><td>whether this person participates in the follow-up pool</td></tr>
</table>

<p><b>The block clients get wrong is Remit.</b> It is not a preference or a
specialism — it is an eligibility filter. A closer with a narrow remit receives few
leads and looks like a poor performer on every report, when the truth is that the
system was never offering them work. Before coaching anybody on volume, read their
remit.</p>

<p><b>Reporting is two decisions dressed as one field.</b> Setting a team manager
places the person in a hierarchy for management, and it also determines what they
see, because scope follows tier. A closer promoted to team lead without their
reporting record being updated will manage a team they cannot see.</p>

<blockquote><b>DRILL:</b> A closer's confirmation rate is fine but they receive a
third of the volume of their colleagues, and the client wants them on a performance
plan. What do you check first? — Remit. If they are eligible for one category in
one branch while colleagues cover four, the volume gap is configuration, not
effort, and a performance plan would be an injustice with a report behind
it.</blockquote>

<!--deep--><p><b>Why availability sits apart from status.</b> Enabled asks whether
this person works here. Availability asks whether they are on right now. They are
different questions and conflating them produces the classic fault of disabling
somebody for a fortnight's leave and then wondering why their history vanished from
the team view. Leave is availability; departure is status.</p>

<p><b>The field that quietly decides fairness.</b> Reports compare closers, and
almost every comparison assumes equal opportunity. Remit is where opportunity is
actually set. A consultant who reads remits before reading rankings is doing the
job; one who reads rankings first is producing a league table of
configuration.</p>
""",
 "checks": [
  {"q": "A closer receives far fewer leads than colleagues. Before coaching, check:",
   "opts": ["Their remit — categories, brands, branches, countries they are eligible for",
            "Their confirmation rate", "Their login history", "The dashboard timeframe"],
   "ans": 0, "why": "Remit is an eligibility filter; a narrow one produces low volume that looks like poor effort.", "sort": 0},
  {"q": "Setting a closer's team manager also affects:",
   "opts": ["What they can see, because scope follows reporting tier",
            "Their commission rate", "Their shift pattern", "Their login credentials"],
   "ans": 0, "why": "A promoted closer whose reporting record is not updated manages a team they cannot see.", "sort": 1},
  {"q": "A closer takes two weeks' leave. The correct handling is:",
   "opts": ["Availability, not status — do not disable the record",
            "Disable the record until they return", "Delete and recreate", "Clear their remit"],
   "ans": 0, "why": "Enabled asks whether they work here; availability asks whether they are on now.", "sort": 2},
 ]})

C5.append({
 "title": "Creating a closer — the eleven steps, and the recipes",
 "est": 5,
 "html": """
<p>The sequence matters, and step one is the golden rule.</p>

<p><b>One.</b> Confirm the User account exists, or create it first. <b>Two.</b>
Open a new Closer record. <b>Three.</b> Link the User — by email, checked, not
assumed. <b>Four.</b> Set the full name as it should appear on leads, orders and
reports. <b>Five.</b> Add the contact number. <b>Six.</b> Set enabled.
<b>Seven.</b> Set the remit — categories, brands, branches, countries.
<b>Eight.</b> Set reporting: team manager and tier. <b>Nine.</b> Set availability,
including the always-available flag if it applies. <b>Ten.</b> Decide follow-up
pool membership. <b>Eleven.</b> Save, then verify by having the person log in and
confirm they can see their own screen.</p>

<p><b>Step eleven is the one that gets skipped and the only one that proves the
other ten.</b> Everything before it is intention; a successful login showing the
right screen is evidence. Build it into every handover.</p>

<p><b>Three recipes worth carrying.</b></p>

<p><b>The generalist:</b> wide remit, no team manager where the client is flat,
follow-up pool on. Suits a small operation where everyone works everything and
volume matters more than specialism.</p>

<p><b>The specialist:</b> narrow remit — one category or brand — follow-up pool
often off. Suits a client with technical products where product knowledge converts
better than availability. Warn them explicitly that this closer will show low
volume on every report by design.</p>

<p><b>The team lead:</b> normal remit plus a reporting tier that grants team
scope, and typically always-available so they can absorb leads nobody else can
take. The distinguishing setting is reporting, not remit.</p>

<blockquote><b>DRILL:</b> A client asks you to create twenty closers before a
Monday launch. What do you insist on? — That the twenty User accounts exist first,
and that each of the twenty logs in and confirms their screen before launch. Twenty
records created correctly and none verified is a Monday morning spent on the phone
instead of selling.</blockquote>

<!--deep--><p><b>Why the specialist recipe needs a warning attached.</b> Narrow
remit is a legitimate design and it guarantees the person looks weak on Team
Closer Summary and Closer Performance. If the client does not know that in advance,
the first month-end produces a conversation about a "poor performer" who is doing
exactly what was configured. Say it while configuring, not while defending.</p>

<p><b>Bulk creation and the temptation to skip verification.</b> At twenty records
the verification step feels disproportionate. It is precisely at twenty that it
matters most: a single mistyped email in a batch is invisible until the person
complains, and by then the launch has happened.</p>
""",
 "checks": [
  {"q": "The final step in creating a closer is:",
   "opts": ["Have the person log in and confirm they see their own screen",
            "Save the record", "Set the remit", "Notify the team manager"],
   "ans": 0, "why": "Everything before it is intention; a successful login is evidence.", "sort": 0},
  {"q": "Configuring a specialist closer with a narrow remit requires you to:",
   "opts": ["Warn the client they will show low volume on every report by design",
            "Increase their targets", "Disable follow-up pool membership", "Set them always-available"],
   "ans": 0, "why": "Otherwise the first month-end becomes a conversation about a 'poor performer' who is correctly configured.", "sort": 1},
  {"q": "The setting that distinguishes a team lead from a closer is:",
   "opts": ["Reporting tier, which grants team scope", "A wider remit",
            "A higher order target", "Follow-up pool membership"],
   "ans": 0, "why": "Scope follows reporting tier; remit only decides what work they can receive.", "sort": 2},
 ]})

C5.append({
 "title": "Lifecycle & troubleshooting — disable, adjust, diagnose",
 "est": 4,
 "html": """
<p>Day-to-day management is three verbs: disable, adjust, diagnose.</p>

<p><b>Disable</b> for leave and departures. New assignments stop; all history is
preserved; every past report stays truthful. Never delete a closer who has ever
held an order.</p>

<p><b>Adjust</b> the remit as the business moves — a new brand, a branch opening, a
category retired. Remit is the single most-changed field on the record and the one
most likely to be forgotten when something new launches. A client adding a product
line and wondering why nobody is receiving those leads has almost always added the
category and not the remits.</p>

<p><b>Diagnose</b> with one ordered list, which resolves the overwhelming majority
of "this closer is not working properly" tickets.</p>

<table border="1" cellpadding="5"><tr><th>Check</th><th>Symptom it explains</th></tr>
<tr><td>Does a Closer record exist?</td><td>logs in fine, receives nothing, ever</td></tr>
<tr><td>Is it enabled?</td><td>received leads until a date, then stopped</td></tr>
<tr><td>Is the User link correct, by email?</td><td>their screen is empty or shows somebody else's work</td></tr>
<tr><td>Does the remit match the leads arriving?</td><td>receives some leads but far fewer than colleagues</td></tr>
<tr><td>Is shift management on, and are they on shift?</td><td>receives leads at some hours and not others</td></tr>
<tr><td>Is the reporting tier right?</td><td>can work but cannot see their team</td></tr>
</table>

<p><b>Work that list in order and stop at the first thing that is wrong.</b>
Consultants who diagnose by intuition tend to reach for the interesting explanation
— assignment rules, shift logic — when the answer is usually the second row.</p>

<blockquote><b>DRILL:</b> A closer received leads every day until the 14th and
nothing since. Where do you start? — Something changed on the 14th, so start with
enabled and with remit rather than with the record existing. A clean stop on a date
is a change, not a misconfiguration from the beginning.</blockquote>

<!--deep--><p><b>Why the ordered list beats experience.</b> An experienced
consultant recognises patterns and jumps to the likely cause, which is fast and
occasionally wrong in a way that costs an hour. The list is slower for the first
two checks and never wrong. Use the list in front of a client and your intuition
afterwards.</p>

<p><b>The ticket that is not about the closer at all.</b> "Nobody is receiving
leads" — plural — is rarely a closer problem. Look at whether leads are arriving at
all, whether the campaign form is still published, and whether shift coverage
lapsed. One closer is a record; everybody is a system.</p>
""",
 "checks": [
  {"q": "A closer received leads until the 14th and nothing since. Start with:",
   "opts": ["What changed on the 14th — enabled status and remit",
            "Whether the Closer record exists", "The User email link", "Their browser"],
   "ans": 0, "why": "A clean stop on a date indicates a change, not an original misconfiguration.", "sort": 0},
  {"q": "A client launches a new product category and nobody receives those leads. The likeliest cause is:",
   "opts": ["Closer remits were not updated to include the new category",
            "The category was created incorrectly", "Shift management is off", "The dashboard is cached"],
   "ans": 0, "why": "Remit is the most-changed field and the one most often forgotten at launch.", "sort": 1},
  {"q": "'Nobody is receiving leads' — plural — should be diagnosed as:",
   "opts": ["A system question: are leads arriving, is the form published, has shift coverage lapsed",
            "Twenty separate closer records", "A reporting tier fault", "A browser issue"],
   "ans": 0, "why": "One closer is a record; everybody is a system.", "sort": 2},
 ]})

C5.append({
 "title": "Shift Management — the concept and its rules",
 "est": 5,
 "html": """
<p>Shift Management decides which closers are eligible for <b>automatic assignment
of new online leads</b>, so that leads only reach people who are actually working.
It is off by default, and the product says so plainly: <i>behaviour is unchanged
while off</i>.</p>

<p><b>Three rules, quoted because the exact wording is what you must be able to
repeat to a client.</b></p>

<p><b>One:</b> when on, <i>only on-shift (or always-available) closers receive
auto-assigned leads</i>. The always-available flag on a closer is the deliberate
exception — typically team leads and anyone who must be able to absorb work at any
hour.</p>

<p><b>Two:</b> <i>manual assignment by managers is never blocked by shifts</i>. A
manager can always hand an order to anybody. Shifts govern the machine, not the
people, and clients worry about this until they hear it said.</p>

<p><b>Three:</b> <i>the Shifts scheduling page appears in the menu once this is
on</i>. A client who cannot find Shifts has not enabled shift management, and that
is the entire support answer.</p>

<p><b>Auto catch-up unassigned leads</b> is the companion setting: it periodically
re-runs assignment for online New Lead orders left without a closer — leads that
arrived while nobody was on shift — so they are picked up once coverage resumes. It
has no effect while shift management is off. Recommend it on, because without it a
gap in coverage becomes a permanent set of orphaned leads rather than a delay.</p>

<p><b>The consequence to state before switching it on.</b> Turn shift management on
with thin coverage and leads will sit unassigned outside covered hours. That is the
system working as designed, and it will be reported as a fault. Establish coverage
first, enable second.</p>

<blockquote><b>DRILL:</b> A client enables shift management on Friday and reports on
Monday that "leads are being lost overnight". What has happened, and what is the
fix? — Nothing is lost. Leads arrived with nobody on shift and were left
unassigned. Turn auto catch-up on so they are picked up when coverage resumes, and
review whether overnight coverage is needed at all.</blockquote>

<!--deep--><p><b>Why "manual assignment is never blocked" is the sentence that
sells the feature.</b> Managers resist shift management because it sounds like a
constraint on them. It is not — it constrains automatic routing only. Say that
first and the conversation changes from resistance to scheduling.</p>

<p><b>The always-available flag as a safety valve.</b> Every shift design needs
somebody who catches what the schedule misses. Setting one or two people
always-available costs nothing while coverage is good and prevents the overnight
orphan problem entirely while a client is still learning to schedule.</p>
""",
 "checks": [
  {"q": "With shift management on, manual assignment by a manager is:",
   "opts": ["Never blocked by shifts", "Blocked outside shift hours",
            "Allowed only for always-available closers", "Queued until coverage resumes"],
   "ans": 0, "why": "Shifts govern automatic routing only — the sentence that resolves most manager resistance.", "sort": 0},
  {"q": "A client cannot find the Shifts page in the menu. The reason is:",
   "opts": ["Shift management has not been enabled — the page appears once it is on",
            "They lack permission", "It is under Reports", "It requires a separate licence"],
   "ans": 0, "why": "The scheduling page is revealed by the setting, not by a role.", "sort": 1},
  {"q": "'Auto catch-up unassigned leads' exists to:",
   "opts": ["Re-run assignment for online leads that arrived while nobody was on shift",
            "Reassign leads from underperforming closers", "Balance workload evenly",
            "Recover deleted leads"],
   "ans": 0, "why": "Without it, a coverage gap leaves permanently orphaned leads rather than delayed ones.", "sort": 2},
 ]})

C5.append({
 "title": "Shifts — setup, the coverage grid, the acceptance test, rollout",
 "est": 5,
 "html": """
<p>Setup runs in one order, and each step depends on the one before it.</p>

<p><b>Step one — enable.</b> Switch Enable Shift Management on and leave auto
catch-up on. The Shifts page appears in the menu.</p>

<p><b>Step two — templates.</b> Define the shift patterns the business actually
runs: the working day, any evening or weekend cover, and their hours. Templates are
patterns, not people.</p>

<p><b>Step three — assign closers to shifts.</b> This is where patterns become
coverage. Set the always-available flag on whoever must receive work regardless —
usually team leads.</p>

<p><b>Step four — read the coverage grid.</b> The grid shows hours against people,
and the only thing you are looking for is <b>gaps</b>: hours when leads can arrive
and nobody is eligible. Every gap is a decision — cover it, accept it and rely on
auto catch-up, or stop advertising into it.</p>

<p><b>The acceptance test, before rollout.</b> Create a test lead inside covered
hours and confirm it assigns. Create one in an uncovered hour and confirm it sits
unassigned and is then picked up when coverage resumes. Both halves matter: the
first proves the system works, the second proves the client understands what
happens when it does not.</p>

<p><b>Rollout.</b> Enable on a quiet day, not a Monday. Watch one full cycle
including an uncovered period. Only then extend to further brands or countries. A
client who enables shift management across the whole operation on their busiest
morning will judge the feature on its worst possible hour.</p>

<blockquote><b>DRILL:</b> The coverage grid shows nobody on shift between 22:00 and
07:00, and the client advertises around the clock. What are the three options? —
Cover the hours, rely on auto catch-up and accept a morning delay, or stop the ads
overnight. There is no fourth option where leads arrive at 02:00 and are worked at
02:00 by nobody.</blockquote>

<!--deep--><p><b>Why the uncovered-hour test is the one clients remember.</b>
Demonstrating success proves nothing they doubted. Demonstrating a lead arriving
into a gap, sitting, and then being collected turns the feature from a risk into a
mechanism they can reason about. It also settles the "leads are being lost"
conversation before it happens.</p>

<p><b>Coverage as a commercial question, not a scheduling one.</b> The grid looks
like a rota problem and is actually an advertising one. Hours you cannot cover are
hours you should think hard about buying traffic into. That reframing is worth more
to the client than the shift configuration itself.</p>
""",
 "checks": [
  {"q": "The purpose of reading the coverage grid is to find:",
   "opts": ["Gaps — hours when leads can arrive and nobody is eligible",
            "Which closer works most hours", "Overtime costs", "Delivery performance by hour"],
   "ans": 0, "why": "Every gap is a decision: cover it, accept it with catch-up, or stop advertising into it.", "sort": 0},
  {"q": "The acceptance test before rollout should include:",
   "opts": ["A lead created in an uncovered hour, confirmed to be picked up when coverage resumes",
            "Only a successful assignment inside covered hours",
            "A load test", "Disabling a closer mid-shift"],
   "ans": 0, "why": "Proving what happens in a gap is what prevents the 'leads are being lost' escalation.", "sort": 1},
  {"q": "Shift management should be enabled:",
   "opts": ["On a quiet day, watching one full cycle including an uncovered period",
            "On the busiest morning to prove capacity", "Across all brands at once",
            "Only after removing always-available flags"],
   "ans": 0, "why": "A client who enables on their busiest morning judges the feature on its worst hour.", "sort": 2},
 ]})

# ─────────────────────────────────────────────────────────────────── apply
d = json.load(io.open(PATH, encoding="utf-8"))
d["c1"]["lessons"] = C1
d["c1"]["desc"] = ("The platform as a consultant supports it: access and the two records behind "
                   "one person, the dashboard's three bands, the status wall and how to read it "
                   "as a shape, the timeframe that rules the page, and what the three charts "
                   "answer that the cards cannot.")
d["c5"]["lessons"] = C5
d["c5"]["desc"] = ("Administration at consultant level: the Closer record and the golden rule, "
                   "the six blocks and why remit decides fairness, the creation sequence and its "
                   "three recipes, an ordered diagnosis that beats intuition, and shift management "
                   "from its rules to a rollout that survives its first uncovered hour.")
io.open(PATH, "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")

wc = lambda h: len(re.sub(r"<[^>]+>", " ", h).split())
for name, mod in (("c1", C1), ("c5", C5)):
    print("%s — %d chapters" % (name, len(mod)))
    for i, c in enumerate(mod, 1):
        print("  ch%d %4dw %d checks  %s" % (i, wc(c["html"]), len(c["checks"]), c["title"][:50]))
    print("  mean %d words" % (sum(wc(c["html"]) for c in mod) // len(mod)))
