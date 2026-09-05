#!/usr/bin/env python3
"""Rebuild consultant modules c2 (Orders, Customers & Fulfilment) and c3 (Campaign Engine).

c2 carried a factual error worth naming: it taught "the thirteen statuses". The
Cluster Members Status report lists seventeen columns and the dashboard shows more
again, and the settings screens name the four terminal ones outright — Delivered,
Cancelled, Duplicate, Rescheduled. Counting them wrongly is the kind of detail a
client checks in front of you.

c2 also omitted the Follow-Up Pool and After Sales entirely, which are two of the
seven workspaces in the left menu and both governed by settings a consultant
configures. They are folded in where they belong rather than bolted on.

c3 was already close to the product. It is corrected against the builder
screenshots — package pricing is a fixed bundle amount, not a multiple; the upsell
is a single offer; preset country hides the country field — and extended with the
publish artefacts and the WordPress plugin, which is where consultants are actually
called.
"""

import io
import json
import re

PATH = "academy_consultant_data.json"

# ═══════════════════════════════════════ c2 — Orders, Customers & Fulfilment
C2 = []

C2.append({
 "title": "The orders list — search, filters, and who sees what",
 "est": 4,
 "html": """
<p>Orders is the operational heart, and visibility is scoped from the first pixel:
closers see their own, managers see everything. Teach that before any conversation
about missing orders, because "I can't find it" is usually scope rather than
search.</p>

<p><b>The columns, and what each is for:</b> Order (customer name with phone
beneath) · Created · Status · Category · Closer · Branch · Brand · Value ·
Delivery · Last Updated · Call. Two carry more than they appear to — <b>Category</b>
shows the product with its source beneath it, so you can see at a glance whether an
order came from a campaign form or arrived online; and <b>Brand</b> can hold more
than one.</p>

<p><b>The top bar is three controls and two buttons:</b> a search across customer,
phone and order; a status filter; a closer filter; then <b>Create Order</b>, <b>More
filters</b> and <b>Reset</b>. Reset exists because the filters persist, and a
client convinced that orders have disappeared has very often left a filter on from
yesterday. Check Reset before you check anything else.</p>

<p><b>More filters opens the advanced set</b>, and it is where real diagnosis
happens: Channel · Assigned Agent · Digital Marketer · Country · Brand · Category ·
Branch · <b>Date Type</b> · From Date · To Date. Date Type is the one to point out —
it decides which date the range applies to, so the same range answers a different
question depending on what is selected.</p>

<p><b>The scale changes how you teach it.</b> A working installation runs to
hundreds of thousands of orders across thousands of pages. Nobody browses this
list. The competent motion is filter first, then read — and the fastest route in
is usually not this screen at all but a dashboard card, which opens the list
already filtered to exactly the orders behind that number.</p>

<blockquote><b>DRILL:</b> A manager says half their orders vanished this morning.
First three checks? — Reset the filters; confirm the date range and Date Type; then
confirm their scope. Data loss is the last hypothesis, not the first, and in
practice it is the first check about nine times in ten.</blockquote>

<!--deep--><p><b>Why Date Type deserves a sentence in every handover.</b> A client
reconciling "August orders" against "August deliveries" will get two different
numbers and conclude something is broken. They are filtering the same range on
different dates. Said once at handover, it never becomes a ticket; discovered by a
finance manager at month end, it becomes an escalation.</p>

<p><b>The Call button is a design statement.</b> It sits on the row, not behind the
order, because the intended motion is to work the list rather than to study it. When
a client asks why there is no bulk-edit, that is the answer: this screen is for
acting on one order at a time, quickly.</p>
""",
 "checks": [
  {"q": "A manager reports that orders have disappeared. Check first:",
   "opts": ["Filters, date range and Date Type — then scope",
            "The database", "Whether orders were deleted", "The brand configuration"],
   "ans": 0, "why": "Filters persist between sessions; a filter left on yesterday is the usual cause.", "sort": 0},
  {"q": "The Date Type field in advanced filters decides:",
   "opts": ["Which date the from/to range applies to", "How dates are displayed",
            "The reporting period", "Whether to include cancelled orders"],
   "ans": 0, "why": "The same range answers a different question depending on the date selected.", "sort": 1},
  {"q": "The fastest route to the orders behind a dashboard count is:",
   "opts": ["Click the card — the list opens already filtered",
            "Search by status", "Use advanced filters", "Export and sort"],
   "ans": 0, "why": "Nobody browses a list of hundreds of thousands of orders; the card does the filtering.", "sort": 2},
 ]})

C2.append({
 "title": "Creating an order — every field, and the duplicate check",
 "est": 5,
 "html": """
<p><b>Create Order</b> sits top-right of the Orders list. The dialog is
unremarkable until the duplicate check fires, which is the part worth teaching.</p>

<p><b>The fields, with the traps.</b> Customer name searches existing customers as
you type — selecting a match pulls in their details rather than creating a second
customer record, and skipping past the match is how duplicate customers are born.
Phone is the identity field in practice, because it is what the duplicate check
uses. Address, category, items, quantity and value follow; brand and cost centre
derive from the category rather than being chosen.</p>

<p><b>The duplicate check is configurable, and a consultant sets it.</b> Four
settings govern it. <b>Enable Duplicate Check</b> is the master switch and covers
both the public form and manual order paths. <b>Duplicate Check Window (days)</b>
decides how far back to look — and zero disables the window entirely. <b>Require
Matching Items</b>, when on, means duplicates must share the same set of item codes;
turn it off to flag any prior order from the same phone regardless of what was
ordered. <b>Run on Manual Orders</b> gives closers a duplicate-warning banner while
creating an order, <b>and they can override and proceed</b>.</p>

<p><b>That override is deliberate and worth defending to a client.</b> A customer
genuinely may order twice in a day. A hard block would turn a warning into lost
revenue and teach closers to work around the system. The banner informs; the human
decides.</p>

<p><b>Open-Order Consolidation is the neighbouring behaviour</b> and gets confused
with duplication. When on, a new online order from a customer who already has an
open, not-yet-dispatched order in the same city and state is <i>merged into that
existing order</i> rather than creating a second — one delivery, one fee. It is off
by default. The consolidation window is short by design: one day means the same
calendar day, and widening it increases the chance of merging genuinely different
addresses.</p>

<blockquote><b>DRILL:</b> A client wants duplicate warnings to become a hard block
because closers ignore them. Your answer? — The override exists because legitimate
repeat orders exist. If closers are overriding routinely, the window or the matching
rule is wrong, not the override. Tighten the configuration and look at why the
warning is firing so often.</blockquote>

<!--deep--><p><b>Duplication and consolidation solve opposite halves of one
problem.</b> The duplicate check stops you recording the same order twice.
Consolidation stops you <i>delivering</i> twice to somebody who ordered twice
legitimately. A client who turns on one and expects the other's behaviour will
report a fault that is a misunderstanding.</p>

<p><b>Why Restrict Order Merge to Same Brand is off by default.</b> Cross-brand
merges within the same business and currency are allowed, because the saving is the
delivery fee and brands often operate together. Turn it on only where brands run as
independent units that should never share a delivery — and know that doing so costs
the client that saving.</p>
""",
 "checks": [
  {"q": "'Duplicate Check Window (days)' set to 0 means:",
   "opts": ["The window is disabled entirely", "Only same-day orders are checked",
            "All history is checked", "The check runs but does not warn"],
   "ans": 0, "why": "Zero disables the window rather than narrowing it to today.", "sort": 0},
  {"q": "A closer sees a duplicate warning while creating a manual order. They:",
   "opts": ["Can override and proceed — the banner informs, the human decides",
            "Are blocked until a manager approves", "Must delete the prior order",
            "Should always cancel"],
   "ans": 0, "why": "A hard block would lose legitimate repeat orders and teach closers to work around the system.", "sort": 1},
  {"q": "Open-Order Consolidation merges a new online order when the customer has an open order:",
   "opts": ["Not yet dispatched, in the same city and state, within the window",
            "Of any age anywhere", "With the same items only", "From the same brand only"],
   "ans": 0, "why": "One delivery, one fee — and the window is short so genuinely different addresses are not merged.", "sort": 2},
 ]})

C2.append({
 "title": "The statuses — lifecycle, owners, and what counts as finished",
 "est": 6,
 "html": """
<p>Status drives visibility, responsibility, every KPI and the automations behind
them. There are more of them than people expect — the cluster report alone carries
seventeen columns — so learn the <b>shape</b> rather than the list.</p>

<p><b>The spine, in order:</b> New Lead → Qualified → Confirmed → Assigned → Agent
Notified → Dispatch Assigned → Order Accepted → Processing → Delivery In Progress →
<b>Delivered</b>.</p>

<p><b>The departures from it,</b> each meaning something different: Delivery
Rescheduled · On Hold · Not Ready · Call Back · Not Picking · Not Reachable · No
Stock · Failed / Returned · Rejected · Cancelled · Duplicate · <b>Delivered Order
Cancelled</b>.</p>

<p><b>Four statuses are terminal, and the product names them:</b> <b>Delivered,
Cancelled, Duplicate, Rescheduled</b>. This is not trivia — it is the rule the
follow-up pool uses. Orders <i>not</i> in a terminal status automatically enter the
pool after a configured number of days from creation. Everything else keeps being
chased.</p>

<p><b>Delivered Order Cancelled has its own status for a reason.</b> An order
cancelled before dispatch costs a phone call. One cancelled after delivery costs
the delivery, the product's journey back, and often the product. They are different
failures and a client who lumps them together will misjudge where the money is
going.</p>

<p><b>Ownership changes with status, and that is the teaching point.</b> Up to
Confirmed the order belongs to the closer. From Assigned through Delivery In
Progress it belongs to dispatch and the agent. Coaching a closer on statuses they
do not own is the commonest management error this product enables, and chapter two
of module four is the report where it shows up.</p>

<blockquote><b>DRILL:</b> A client asks you to add a status called "Pending
Payment". What do you ask first? — Who owns an order in that state, what moves it
out, and whether it is terminal. A status without an owner and an exit becomes a
place orders go to be forgotten, and the follow-up pool will not rescue them if it
is marked terminal.</blockquote>

<!--deep--><p><b>Why the not-terminal rule matters more than the status list.</b> A
consultant who memorises seventeen statuses can recite them. One who understands
that non-terminal means "still being chased" can predict what the system will do to
any order in front of them, including ones added after they learned the list.</p>

<p><b>The statuses that describe the customer rather than the order.</b> Not
Picking, Not Reachable, Call Back — these record a failure to make contact, not a
stage of fulfilment. Grouped with the fulfilment statuses in a chart they distort
it; read as a group of their own they are a contactability report, and often the
most actionable thing on the dashboard.</p>
""",
 "checks": [
  {"q": "The four terminal statuses are:",
   "opts": ["Delivered, Cancelled, Duplicate, Rescheduled",
            "Delivered, Cancelled, Rejected, Failed",
            "Delivered and Cancelled only",
            "Delivered, Returned, Duplicate, On Hold"],
   "ans": 0, "why": "Non-terminal orders automatically enter the follow-up pool; terminal ones do not.", "sort": 0},
  {"q": "'Delivered Order Cancelled' is a separate status because:",
   "opts": ["Cancelling after delivery costs the delivery and often the product",
            "It is a data migration artefact", "It only applies to COD",
            "It is the same as Returned"],
   "ans": 0, "why": "A cancellation before dispatch and one after are different failures with different costs.", "sort": 1},
  {"q": "Before adding a new status for a client, establish:",
   "opts": ["Who owns an order in it, what moves it out, and whether it is terminal",
            "Its colour", "Which report it appears on", "Whether closers can see it"],
   "ans": 0, "why": "A status without an owner and an exit becomes a place orders go to be forgotten.", "sort": 2},
 ]})

C2.append({
 "title": "The details drawer — anatomy, timeline, and actions",
 "est": 5,
 "html": """
<p>Click any row and a drawer opens from the right with the list still live behind
it. Click another row to switch orders; close with the X.</p>

<p><b>The header</b> carries the order ID — a readable code combining the company
and a sequence, such as <i>Daggo Company-CRM-ORD-08-000024</i> — the customer name,
and a <b>Copy details</b> button. Beneath it the status chips lay out the journey
travelled: Assigned → Agent Notified → Order Accepted → Delivered. That strip is
the fastest read on the screen.</p>

<p><b>The field block:</b> Status · Order Date &amp; Time · Closer · Dispatch Agent
· Expected Delivery · Actual Delivery · and <b>Commitment Fee</b>, with a Record
Commitment Fee action. Expected against Actual is the pair to read together —
whether the promise was kept.</p>

<p><b>Then five blocks that answer five different questions.</b> <b>Customer</b> —
name, email, phone numbers, and a Call customer action. <b>Lead</b> — where it came
from: source such as WhatsApp, the originating number, whether a digital marketer
was captured, and the origin. <b>Invoice</b> — the linked sales invoice.
<b>Delivery</b> — status and delivered date. <b>Address</b>. <b>Items</b> — item,
quantity, unit rate, amount, edit and delete per line, an Add Item action, and the
order value.</p>

<p><b>"Digital marketer: Not captured" is a finding, not a blank.</b> It means this
order cannot be attributed to an ad buyer, so it will never appear in Marketing
ROAS. A client whose ROAS looks thin should be shown how many of their orders carry
that line — it is usually the explanation.</p>

<blockquote><b>DRILL:</b> A client says an order "is not showing in ROAS". Where do
you look? — The Lead block. If the digital marketer was not captured, or the origin
is phone or WhatsApp rather than a tracked form, the order is correctly excluded.
Ad-attributed leads count only tracked campaign forms.</blockquote>

<!--deep--><p><b>Why Copy details exists.</b> Support conversations happen in
WhatsApp and on phone calls, not inside the product. One button that produces a
pasteable summary removes a dozen transcription errors a week. Show it to every
client; almost nobody finds it alone.</p>

<p><b>The invoice link is the boundary between CRM and accounts.</b> An order is a
sales conversation; an invoice is a financial document with its own lifecycle.
Clients ask for them to be the same thing and they should not be — the moment they
merge, cancelling an order starts amending accounting records.</p>
""",
 "checks": [
  {"q": "'Digital marketer: Not captured' on an order means:",
   "opts": ["It cannot be attributed to an ad buyer and will not appear in Marketing ROAS",
            "The order is invalid", "The closer forgot a field", "The customer is new"],
   "ans": 0, "why": "Ad-attributed leads count only orders arriving through a tracked campaign form.", "sort": 0},
  {"q": "The pair of fields that shows whether a delivery promise was kept is:",
   "opts": ["Expected Delivery against Actual Delivery", "Order Date against Status",
            "Closer against Dispatch Agent", "Invoice against Order Value"],
   "ans": 0, "why": "Everything else describes the order; those two describe the promise.", "sort": 1},
  {"q": "The order and its sales invoice are kept as separate records because:",
   "opts": ["An invoice is a financial document with its own lifecycle",
            "The database requires it", "Invoices are optional", "Only accounts can see invoices"],
   "ans": 0, "why": "Merging them would mean cancelling an order amends accounting records.", "sort": 2},
 ]})

C2.append({
 "title": "Editing items — recalculation, locks, and delivery-fee care",
 "est": 4,
 "html": """
<p>The Items block is the only part of an order that changes money, so it carries
the most care.</p>

<p><b>The mechanics.</b> Add Item opens a picker; choose the item, set quantity,
and the unit rate fills from the product with the line amount computed beside it.
Each line can be edited or deleted, and the order value recalculates
immediately.</p>

<p><b>Recalculation is instant and total.</b> There is no draft state to review
before committing — change a quantity and the order value has changed. Teach closers
to confirm the new total aloud to the customer before ending the call, because the
system will not prompt them and the customer will remember the first figure.</p>

<p><b>Where editing gets dangerous is after dispatch.</b> An order whose value
changes once an agent is carrying it creates a mismatch between what the customer
was told, what the agent expects to collect, and what the invoice says. The
discipline is simple and worth stating as a rule: <b>if the order has left, do not
edit the items — cancel and re-raise, or record the difference deliberately.</b>
The system will let you; that is not the same as it being safe.</p>

<p><b>Cash on delivery makes this sharper.</b> The agent collects a figure. If it
was edited after they set out, the agent and the customer will disagree at the door
and the agent will lose. Every value change after dispatch needs a call to whoever
is carrying it.</p>

<p><b>The invoice is linked, not merged.</b> Editing items changes the order;
whether and how that flows to a submitted invoice is an accounts question with its
own rules. Never assume an edited order silently corrects a submitted invoice.</p>

<blockquote><b>DRILL:</b> A customer adds an item while the agent is en route, COD.
What do you tell the closer to do? — Edit the order, then call the agent with the
new total before they arrive. The edit is the easy half; the call is the half that
stops an argument at the door.</blockquote>

<!--deep--><p><b>Why there is no confirmation step on recalculation.</b> Speed. This
is a call-centre product and a modal between every quantity change would cost more
in aggregate than the errors it prevents. The trade is deliberate, and the mitigation
is the habit — say the total aloud — rather than the interface.</p>

<p><b>The audit question a client eventually asks.</b> "Who changed this value?"
Point them at the order's own history rather than reconstructing from the invoice.
Establishing that habit early prevents the version of this conversation that happens
after money has gone missing.</p>
""",
 "checks": [
  {"q": "Editing an item's quantity on an order:",
   "opts": ["Recalculates the order value immediately, with no draft state",
            "Requires manager approval", "Creates a new order version", "Is blocked after Confirmed"],
   "ans": 0, "why": "There is no confirmation step, which is why the habit of confirming the total aloud matters.", "sort": 0},
  {"q": "An order is edited after dispatch on a COD delivery. The essential extra step is:",
   "opts": ["Call the agent with the new total before they arrive",
            "Email the customer", "Re-run the duplicate check", "Reassign the closer"],
   "ans": 0, "why": "Otherwise the agent and the customer disagree at the door and the agent loses.", "sort": 1},
  {"q": "An edited order and a submitted invoice:",
   "opts": ["Do not silently reconcile — the invoice follows accounting rules",
            "Always update together", "Cannot both exist", "Are the same record"],
   "ans": 0, "why": "The link is a reference, not a merge.", "sort": 2},
 ]})

C2.append({
 "title": "Assignment, the follow-up pool, and after-sales",
 "est": 6,
 "html": """
<p>Three mechanisms decide who is working an order and when it comes back. A
consultant configures all three, and clients confuse them constantly.</p>

<p><b>Assignment.</b> Orders reach a closer automatically or by hand. Automatic
assignment respects shift management when it is on — only on-shift or
always-available closers receive auto-assigned leads — and <b>manual assignment by
a manager is never blocked</b>. In the drawer, Closer and Dispatch Agent are
separate fields because they are separate jobs: one sold it, one is carrying
it.</p>

<p><b>The follow-up pool</b> catches stalled orders. Orders <i>not</i> in a terminal
status enter the pool automatically after a configured number of days from creation
— the threshold is a setting, and the product's own default is ten. The pool itself
is a workspace: filters across pool, status, country, brand and branch, columns for
order, customer, category, status, phone, value, sent-on and claimed-by, and three
actions — <b>Claim</b>, <b>Release</b>, <b>Convert</b>.</p>

<p><b>Claim is a lock, and that is the point.</b> An unclaimed order shows
"unclaimed" and anyone may take it; a claimed one shows who holds it. Two people
cannot ring the same customer an hour apart, which is the failure the pool exists to
prevent. Release puts it back rather than abandoning it.</p>

<p><b>After-sales is the opposite motion:</b> not chasing a stalled order but
returning to a completed one. When enabled, delivered orders schedule a reorder
chase on a computed date — <b>fourteen days for a single-unit order, twenty-nine for
multi-unit</b>, the latter chosen so the call lands one or two days before a
thirty-day supply runs out. The workspace shows active cases, contacted, completed
and escalated, with tabs for My Cases, Team, Unassigned, Scheduled and Done.</p>

<p><b>"Unassigned" in after-sales is explained on screen:</b> <i>manual bucket — no
eligible closer was available at sweep time</i>. It is a coverage finding, not a
person's backlog.</p>

<blockquote><b>DRILL:</b> A client sets the follow-up threshold to one day, and the
pool fills with thousands of orders. What has gone wrong? — Nothing technical. A
one-day threshold means every order not terminal by tomorrow is "stalled", which is
most of them. The threshold should sit just beyond a normal fulfilment cycle;
inside it, the pool stops meaning anything.</blockquote>

<!--deep--><p><b>Why the reorder cadence is a number worth defending.</b>
Twenty-nine days is not arbitrary — it is thirty minus the lead time to redeliver.
A client who moves it to thirty-five has decided their customers should run out
before being asked. Explain the reasoning and they usually leave it alone.</p>

<p><b>Backfill lookback exists to protect closers.</b> When the backfill runs, only
delivered orders within the lookback are considered, so switching after-sales on for
an established client does not bury the team under two years of historical
cases.</p>
""",
 "checks": [
  {"q": "Orders enter the follow-up pool automatically when they are:",
   "opts": ["Not in a terminal status after the configured number of days from creation",
            "Cancelled", "Older than 30 days regardless of status", "Unassigned"],
   "ans": 0, "why": "Terminal orders — Delivered, Cancelled, Duplicate, Rescheduled — are finished and excluded.", "sort": 0},
  {"q": "The Claim action in the follow-up pool exists to:",
   "opts": ["Stop two people working the same customer",
            "Assign commission", "Change the order status", "Notify the manager"],
   "ans": 0, "why": "Claimed shows who holds it; Release puts it back rather than abandoning it.", "sort": 1},
  {"q": "The multi-unit after-sales reorder cadence is 29 days because:",
   "opts": ["It leaves one to two days to redeliver before a 30-day supply runs out",
            "It is one month minus a day", "It matches the billing cycle",
            "It avoids weekends"],
   "ans": 0, "why": "The call is timed to land before the customer runs out, not after.", "sort": 2},
 ]})

C2.append({
 "title": "Customers — directory, quick actions, and tag discipline",
 "est": 4,
 "html": """
<p>The customer directory is the other axis on the same data: orders answer "what
is happening", customers answer "who is this". It is role-scoped like orders.</p>

<p><b>What a customer record carries:</b> identity — name, phone, email — and
history: their orders, what they have spent, when they last bought, and where they
came from. The timeline is the part consultants underuse. Before any conversation
with a customer, it is the difference between "how can I help" and "I see the
Baozem order was rescheduled twice — let me sort that".</p>

<p><b>Phone is the identity field.</b> It is what the duplicate check uses, what
after-sales dials, and what a customer gives on a call. Email is frequently absent
and never a reliable key. Any client planning a data migration should be told this
before they map their columns, not after.</p>

<p><b>Repeat Customer is a channel in Attribution</b>, and this is where that number
comes from. A customer record with several orders is the asset the business built;
the directory is where you can see whether there are many of them or a few. A client
whose directory is mostly single-order records is buying every sale, however good
this month looks.</p>

<p><b>Tag discipline, since tags are free text and free text rots.</b> Three rules:
agree the vocabulary before anyone types, keep it short enough to remember, and
review it quarterly. Fuel, fuel and Petrol are three tags to a database and one idea
to a human. Consultants who set this up on day one save clients a cleanup that
otherwise never happens.</p>

<blockquote><b>DRILL:</b> A client wants to tag customers by twelve behavioural
segments. What do you advise? — Start with three or four they will actually use.
Twelve tags means inconsistent tagging within a month, and inconsistent tags are
worse than none because they look like data. Add more when the first four are being
used correctly.</blockquote>

<!--deep--><p><b>Why the customer directory is the right screen for a retention
conversation and cohorts is the right screen for a retention decision.</b> The
directory shows individuals and is persuasive; cohorts show the pattern and are
correct. Use the first to make a client care and the second to work out what to
do.</p>

<p><b>The migration trap.</b> Clients arriving with spreadsheets have customers
keyed on name or email. Both produce duplicates on arrival — two Felix Akhigbes,
one customer with three email addresses. Key on phone, deduplicate before import,
and accept that some records will need a human. Doing it afterwards costs several
times more.</p>
""",
 "checks": [
  {"q": "The reliable identity field for a customer is:",
   "opts": ["Phone", "Email", "Full name", "Customer ID"],
   "ans": 0, "why": "It is what the duplicate check uses and what after-sales dials; email is often absent.", "sort": 0},
  {"q": "A client's directory is almost entirely single-order customers. That means:",
   "opts": ["They are buying every sale — there is little repeat base",
            "Their data is incomplete", "Their delivery rate is poor", "Tags need cleaning"],
   "ans": 0, "why": "Repeat Customer revenue in Attribution comes from exactly these records.", "sort": 1},
  {"q": "A client wants twelve customer tags on day one. Advise:",
   "opts": ["Start with three or four they will use consistently",
            "Implement all twelve for completeness", "Use free text and review later",
            "Tag automatically by product"],
   "ans": 0, "why": "Inconsistent tags are worse than none, because they look like data.", "sort": 2},
 ]})

# ═══════════════════════════════════════════════ c3 — The Campaign Engine
C3 = []

C3.append({
 "title": "Lead forms — what they are, end to end",
 "est": 4,
 "html": """
<p>A lead form is a hosted page where a customer chooses a product, enters their
details and places an order without speaking to anyone first. It replaces the old
funnel — advertisement, phone number, agent, manual order — with a page that
creates the order itself.</p>

<p><b>The whole path, so you can hold it in one sentence:</b> a media buyer builds
a form, publishes it, embeds it on a landing page or Facebook tab, the ad sends
traffic to it, a submission arrives, and it becomes an order attributed to that
buyer and that campaign. Every report in module four downstream of "ad-attributed"
depends on this chain being intact.</p>

<p><b>Campaigns → Lead Forms</b> lists them: form name with its <b>token</b> beneath
(or <i>DRAFT</i>), default item, digital marketer, status — Published or Draft —
lead count, and last submission. Actions per row: Duplicate, Edit, Details.</p>

<p><b>Each media buyer sees only the forms they created.</b> That is a visibility
rule, not a permission fault, and it is the first thing to say when a buyer reports
that forms are missing. An administrator sees all of them.</p>

<p><b>Duplicate is the most useful button on the screen.</b> A working form is a
tested configuration — category, packages, fields, appearance. Duplicating it for a
new campaign preserves everything that was got right and changes only what needs to
change. Teach it early or clients rebuild from scratch each time and introduce a new
mistake every time.</p>

<blockquote><b>DRILL:</b> A media buyer says their leads stopped arriving overnight
and nothing was changed. What do you check on this screen? — The form's status. A
form reverted to Draft is unpublished and its embed stops producing submissions,
while the page it sits on continues to look perfectly normal.</blockquote>

<!--deep--><p><b>Why the form list is also a performance report.</b> Lead count and
last submission sit on every row. A form with hundreds of leads and a last
submission three weeks old is either a campaign that ended or an embed that broke,
and this screen is where the difference is visible earliest — well before anyone
notices in ROAS.</p>

<p><b>The draft that never shipped.</b> Forms accumulate. A client with a hundred
and fifty-nine of them has perhaps a dozen live, and the rest are experiments. That
is fine, but it makes the list unnavigable, so agree a naming convention on day one:
campaign, country, product. Nobody ever does this retrospectively.</p>
""",
 "checks": [
  {"q": "A media buyer cannot see forms a colleague created. This is:",
   "opts": ["The visibility rule — each buyer sees only their own forms",
            "A permission fault to fix", "A filter left applied", "A licensing limit"],
   "ans": 0, "why": "Administrators see all forms; buyers see their own by design.", "sort": 0},
  {"q": "Leads stop arriving from a form that was working. Check first:",
   "opts": ["Whether the form is still Published rather than Draft",
            "The ad budget", "The closer roster", "The duplicate check window"],
   "ans": 0, "why": "An unpublished form stops producing submissions while the page still looks normal.", "sort": 1},
  {"q": "Duplicating an existing form for a new campaign is preferred because:",
   "opts": ["It preserves a tested configuration and changes only what must change",
            "It is faster to load", "It shares the same token", "It inherits the lead count"],
   "ans": 0, "why": "Rebuilding from scratch introduces a fresh mistake each time.", "sort": 2},
 ]})

C3.append({
 "title": "Step 1: Basics — every field, and why each converts",
 "est": 4,
 "html": """
<p>The builder is three steps — <b>Basics</b>, <b>Builder</b>, <b>Upsell</b> — and
you can move between them freely, with a Save draft at any point and a Resume draft
picker to come back later.</p>

<p><b>Form title</b> is internal: it names the form in the list and in reports.
Name it so a stranger can find it — campaign, product, country.</p>

<p><b>Digital marketer</b> is the attribution field, and it is the most consequential
box on the page. It decides who this form's leads are credited to in Marketing ROAS.
Set it wrong and the buyer's numbers are wrong for the life of the campaign.</p>

<p><b>Redirect URL</b> sends the customer somewhere after submitting — a thank-you
page, usually, and the place a conversion pixel fires. <b>Success message</b> is
what they see if you do not redirect. Use one or the other deliberately rather than
leaving both at defaults.</p>

<p><b>Submit button text</b> is a conversion lever and costs nothing to test.
<b>Quantity display mode</b> — radio buttons, for instance — changes how the customer
chooses how many, and radio buttons make the intended quantity visible rather than
leaving a number field at one.</p>

<p><b>Preset country</b> is the field with a hidden consequence, stated plainly on
screen: <i>if set, buyers won't see the country field and state/city will use this
country</i>. For a single-market campaign that is one fewer field and a better
conversion rate. For a multi-country campaign it silently misfiles every order.</p>

<blockquote><b>DRILL:</b> A client running Nigeria and Ghana from one form reports
that Ghanaian orders show as Nigeria. What happened? — Preset country is set. It
hides the field and forces the value. One form per country, or no preset — those
are the only two correct answers.</blockquote>

<!--deep--><p><b>Why every removed field raises conversion and lowers data
quality.</b> Each box is a chance to abandon and a fact you wanted. Preset country
is free — the customer gains, you lose nothing, because you knew the country
already. Removing address line 2 is a trade. Removing phone is not a trade at all;
it is removing the only reliable identity field the system has.</p>

<p><b>The attribution field deserves a checklist entry.</b> It is a dropdown, it
defaults to somebody, and nobody notices it at publish time. Six weeks later a
buyer's ROAS is inexplicable and the cause is one unchanged dropdown.</p>
""",
 "checks": [
  {"q": "Setting Preset Country on a form:",
   "opts": ["Hides the country field and forces state and city to that country",
            "Sets a default the customer can change", "Filters the product list",
            "Restricts which closers receive the leads"],
   "ans": 0, "why": "Excellent for a single-market campaign, silently wrong for a multi-country one.", "sort": 0},
  {"q": "The Digital Marketer field on a form decides:",
   "opts": ["Who the leads are credited to in Marketing ROAS",
            "Who can edit the form", "Which closer receives the orders",
            "The form's brand"],
   "ans": 0, "why": "Set wrong, it makes that buyer's return figures wrong for the life of the campaign.", "sort": 1},
  {"q": "Removing the phone field from a form is:",
   "opts": ["Removing the only reliable identity field the system has",
            "A reasonable conversion optimisation", "Required for GDPR", "Impossible"],
   "ans": 0, "why": "Phone drives the duplicate check, after-sales dialling and customer matching.", "sort": 2},
 ]})

C3.append({
 "title": "Step 2: Builder — routing, products, packages, fields",
 "est": 6,
 "html": """
<p>Step 2 does four jobs, and the first is structural.</p>

<p><b>Order dimensions.</b> Choose one <b>Product Category</b> — it is required —
and <b>Resolved Brand</b> and <b>Resolved Cost Center</b> fill automatically and are
read-only. The category is not a label; it is the routing decision. It determines
the brand the order belongs to, the cost centre it books against, and which closers
are eligible to receive it, because remit is set by category. Choose it wrong and
the order goes to the wrong people and the wrong ledger.</p>

<p><b>Core field options.</b> Every built-in field carries two independent toggles,
<b>Required</b> and <b>Visible</b>: Full Name, Email, Phone, Address Line 1, Address
Line 2, Country, State/Province, City, Postal Code. Two toggles rather than one is
deliberate — a field can be visible and optional, which is how you ask for an email
without losing the customers who will not give one.</p>

<p><b>Offer packages</b>, and here is the mechanism people get wrong. A package
carries a label, a buy quantity, a free quantity, a <b>fixed package amount</b> and
a discount amount, with one marked default. The fixed amount is <b>the price of the
whole package, not a multiple of the unit price</b>. "Buy 1" at 18,500 and "Buy 2"
at 30,000 is a bundle at 15,000 each — the saving is the offer. Enter 37,000 for the
two-pack and you have built a package with no reason to exist.</p>

<p><b>Linked items</b> are the actual products behind it, with type, quantity, price
and a default. <b>Additional questions</b> add custom fields — pickup store, delivery
instructions, financing — on top of the core order fields rather than instead of
them.</p>

<blockquote><b>DRILL:</b> A client's two-pack sells nothing while the single sells
well. First thing to check? — The fixed package amount. If the two-pack is priced at
exactly twice the single, there is no offer, and customers are correctly declining
to buy two of something at no saving.</blockquote>

<!--deep--><p><b>Why packages beat quantity fields.</b> A quantity box asks the
customer to do arithmetic and decide. A package makes the decision for them and
shows the saving. The same order value arrives more often — which is the whole of
offer design, and it lives in five fields on this screen.</p>

<p><b>Free quantity is the other lever, and it reads differently.</b> Buy two get
one free is the same money as a third off three, and converts differently in
different markets. It costs nothing to run both as separate forms and let the
numbers decide — which is what Duplicate is for.</p>
""",
 "checks": [
  {"q": "The Fixed Package Amount on an offer package is:",
   "opts": ["The price of the whole package, not a multiple of the unit price",
            "The per-unit price within the package", "A maximum spend",
            "The discount applied"],
   "ans": 0, "why": "Buy 2 at 30,000 against Buy 1 at 18,500 is a bundle at 15,000 each; the saving is the offer.", "sort": 0},
  {"q": "Product Category on a form is structural because it determines:",
   "opts": ["Brand, cost centre and which closers are eligible to receive the order",
            "Only how the form is labelled", "The form's appearance",
            "Which country the form serves"],
   "ans": 0, "why": "Brand and cost centre resolve from it automatically, and closer remit is set by category.", "sort": 1},
  {"q": "Core fields carry both Required and Visible toggles so that:",
   "opts": ["A field can be shown but optional", "Required fields can be hidden",
            "Fields can be reordered", "Validation can be disabled"],
   "ans": 0, "why": "It is how you ask for an email without losing customers who will not give one.", "sort": 2},
 ]})

C3.append({
 "title": "Appearance, upsell, publish — and what publishing produces",
 "est": 5,
 "html": """
<p><b>Appearance</b> sits beside the builder: button background and text colour,
page and card background, heading colour, input border colour and radius, and font
family. <b>Open live preview</b> opens a separate tab showing the theme as you
edit.</p>

<p><b>The trust principle beats the brand guideline.</b> A form that looks like the
page it is embedded in converts better than one that looks like software. Match the
client's landing page, not their logo palette — the customer never saw the brand
book and is deciding, in about a second, whether this page is real.</p>

<p><b>Step 3 is a single upsell,</b> shown after submit. The product says so:
<i>configure the single post-submit offer shown on step 3</i>. One offer. The fields
are the offer itself plus its persuasion: upsell item, a product-details URL, an
optional logo, heading, description, form width, text colour, <b>button text</b>,
<b>decline text</b> and optional <b>scarcity text</b>.</p>

<p><b>The decline text is not a formality.</b> "No, I don't want this additional
offer" is a real sentence a real person reads, and writing it graciously rather
than manipulatively is the difference between a customer who declines and completes
and one who abandons a purchase they had already made.</p>

<p><b>Publish produces two artefacts, and the token is the important one.</b> The
Details panel shows the token, status, default item, leads and last submission, plus
an <b>iframe snippet</b> pointing at the hosted form with the token in the query
string. Buttons: Edit form, Preview, Copy URL, <b>Copy embed</b>, Open form.</p>

<p><b>The token identifies the form everywhere</b> — in the iframe, in the WordPress
shortcode, in support conversations. When a client reports a problem with "the liver
form", ask for the token. There are usually three forms with similar names and only
one of them is live.</p>

<blockquote><b>DRILL:</b> A client's embedded form shows an old price. They swear
they updated it. What is the likeliest cause? — They edited a different form. Ask
for the token in the embed on the live page and compare it with the token of the
form they edited. Duplicated forms with similar names are the usual
explanation.</blockquote>

<!--deep--><p><b>Why the upsell is limited to one.</b> Two consecutive upsells
convert the second far worse and cost goodwill on an order already won. The
constraint is a design opinion, and a good one — a client asking for a chain of
three is asking to spend a completed sale on a maybe.</p>

<p><b>Scarcity text, and the line not to cross.</b> Optional limited-time copy
raises conversion. Copy that is untrue — a countdown that resets, a stock figure
that is invented — raises conversion once and costs the customer permanently.
Advise clients to use it only where it is true.</p>
""",
 "checks": [
  {"q": "Step 3 of the form builder allows:",
   "opts": ["A single post-submit upsell offer", "Up to three chained upsells",
            "One upsell per product", "Unlimited offers"],
   "ans": 0, "why": "Consecutive upsells convert worse and risk goodwill on an order already won.", "sort": 0},
  {"q": "When a client reports a problem with a form, ask for:",
   "opts": ["The token", "The form name", "The campaign name", "The product"],
   "ans": 0, "why": "Names are duplicated; the token identifies the form in the embed, the shortcode and support.", "sort": 1},
  {"q": "Form appearance should be matched to:",
   "opts": ["The landing page it is embedded in", "The client's logo colours",
            "The CRM's own theme", "Whatever converts best generally"],
   "ans": 0, "why": "A form that looks like the page around it reads as real; one that looks like software does not.", "sort": 2},
 ]})

C3.append({
 "title": "Embedding — iframe, WordPress plugin, and the CORS decision",
 "est": 5,
 "html": """
<p>A published form has to reach a customer, and there are two routes. This chapter
is where consultants actually get called.</p>

<p><b>The iframe</b> is universal. Copy embed gives a snippet pointing at the hosted
form with the token in the query string, sized to full width with a maximum and a
fixed height. It works on any page that accepts HTML — a Facebook tab, a microsite,
a landing page builder. It is the fallback that always works.</p>

<p><b>The WordPress plugin</b> is the better route for WordPress clients, because
the form renders in the page rather than inside a frame. Install it from the
WordPress admin by upload, or by FTP if the client's host forbids uploads. Then the
shortcode:</p>

<p><code>[pangea_form token="your_token_here"]</code></p>

<p><b>Three attributes.</b> <b>token</b> is required. <b>theme</b> takes auto,
inherit or minimal — <i>inherit</i> makes the form adopt the site's own styling,
which is the trust principle again. <b>class</b> adds a CSS class for anything
bespoke. There is a Gutenberg block and Elementor support for clients who do not
paste shortcodes.</p>

<p><b>The decision that needs you: Proxy Mode.</b> By default submissions go
straight from the visitor's browser to the CRM, which requires CORS to be configured
on the CRM. Where that cannot be done, enable <b>Proxy API Calls</b> in the plugin
settings and submissions route through the client's WordPress server instead —
WordPress to CRM. No CORS at all, at the cost of two hops instead of one and a
little latency.</p>

<p><b>Diagnose it by the symptom.</b> A form that renders perfectly and fails
silently on submit is the classic CORS signature. Before rebuilding anything, turn
on proxy mode and try again — it takes a minute and resolves it or rules it
out.</p>

<blockquote><b>DRILL:</b> A client's form displays correctly but nothing arrives in
Submissions. Where do you start? — Not with the form. Submit a test through the
hosted URL directly: if that works, the form is fine and the problem is the embed —
CORS, and proxy mode is the fix. If the hosted URL also fails, the problem is the
form.</blockquote>

<!--deep--><p><b>Why the hosted URL is the diagnostic tool.</b> It removes the
client's site from the equation entirely. Every embedding problem divides into "the
form is broken" and "the page hosting it is broken", and one test tells you which
half you are in. Consultants who skip it debug both halves at once.</p>

<p><b>Multiple forms on one page.</b> Supported, and worth knowing before a client
asks — a comparison page with a form per product is a legitimate design. Each needs
its own token, which is another reason for a naming convention that survives
contact with a real campaign.</p>
""",
 "checks": [
  {"q": "A form renders correctly but submissions fail silently. Test first:",
   "opts": ["The hosted URL directly, to see whether the form or the embed is at fault",
            "The closer roster", "The duplicate check", "The product category"],
   "ans": 0, "why": "It removes the client's site from the equation and halves the problem in one step.", "sort": 0},
  {"q": "Proxy Mode in the WordPress plugin:",
   "opts": ["Routes submissions through WordPress to the CRM, avoiding CORS at the cost of latency",
            "Caches the form for speed", "Hides the token from the page source",
            "Allows multiple forms per page"],
   "ans": 0, "why": "Two hops instead of one, and no CORS configuration needed.", "sort": 1},
  {"q": "The shortcode theme attribute 'inherit' makes the form:",
   "opts": ["Adopt the surrounding site's styling", "Use the CRM's default theme",
            "Strip all styling", "Match the brand palette"],
   "ans": 0, "why": "The same trust principle as appearance: it should look like the page, not like software.", "sort": 2},
 ]})

C3.append({
 "title": "Submissions and abandoned carts — what each list is telling you",
 "est": 5,
 "html": """
<p>Two lists sit under Campaigns beside Lead Forms, and they answer opposite
questions: who finished, and who did not.</p>

<p><b>Submissions</b> are completed forms. The list runs newest first with summary
cards above it and a timespan control, and the action that matters is <b>convert</b>
— a submission becomes an order, attributed to the form and therefore to the media
buyer who owns it. A submission that is never converted is a customer who filled in
your form and was ignored.</p>

<p><b>Abandoned carts</b> are the other half: <i>customers who started but did not
complete their order</i>. Interaction starts the tracking — a product chosen,
details being typed — so a page view alone creates nothing. The columns are contact
(name, phone, email), items, campaign, when it was abandoned, <b>resumes</b>, and a
<b>Convert</b> action.</p>

<p><b>Resumes is the most underused number in the product.</b> It counts how many
times that person came back to the form. A cart with three resumes is somebody who
returned twice and still did not finish — that is not a cold lead, it is a person
with an unresolved objection, and they are worth calling before a fresh lead
is.</p>

<p><b>The scale is the point.</b> A working installation shows tens of thousands of
abandoned carts against a much smaller number of submissions. That ratio is not a
failure; it is normal for public forms, and it means the recovery list is a
permanent standing asset rather than a queue to be cleared. Teach clients to work it
by priority, forever, rather than to try to empty it.</p>

<blockquote><b>DRILL:</b> A client asks whether they should reduce form fields
because their abandoned cart count is enormous. Your answer? — Look at where
abandonment happens before removing anything. A large count is expected. Removing
phone to reduce it would cost you the only field that makes recovery possible, and
recovery is worth more than the abandonment you prevented.</blockquote>

<!--deep--><p><b>Why abandoned carts are a better lead source than most paid
traffic.</b> The person chose a product and began giving you their details. They are
further down the funnel than anyone an advertisement will reach today, and they cost
nothing to contact. A client spending on cold traffic while ignoring a cart list is
buying what they already have.</p>

<p><b>The priority order worth writing on the wall:</b> recent and high value with a
phone number first; then anything with multiple resumes; then the rest by freshness.
Beyond a few days the return collapses, so a cart list worked weekly is worth a
fraction of one worked daily.</p>
""",
 "checks": [
  {"q": "An abandoned cart record is created when a visitor:",
   "opts": ["Interacts — chooses a product or starts entering details — then leaves",
            "Views the form page", "Submits and cancels", "Clicks the advertisement"],
   "ans": 0, "why": "A page view alone creates nothing; interaction starts the tracking.", "sort": 0},
  {"q": "The 'resumes' column indicates:",
   "opts": ["How many times the person returned to the form without finishing",
            "How many recovery calls were made", "Times the form was edited",
            "Duplicate submissions"],
   "ans": 0, "why": "Multiple resumes means an unresolved objection, not a cold lead.", "sort": 1},
  {"q": "Tens of thousands of abandoned carts against far fewer submissions is:",
   "opts": ["Normal for public forms — the list is a standing asset to work by priority",
            "Evidence the form is broken", "A reason to remove fields",
            "A tracking error"],
   "ans": 0, "why": "The list is never cleared; it is worked by priority, and recency matters most.", "sort": 2},
 ]})

C3.append({
 "title": "Cart recovery — prioritisation, outreach, conversion",
 "est": 5,
 "html": """
<p>Recovery is a discipline, not a task, and it lives or dies on the order in which
the list is worked.</p>

<p><b>The priority order.</b> First: high value, phone present, abandoned within
about two hours — call these before anything else, including fresh leads. Second:
any value, phone present, within twenty-four hours. Third: multiple resumes at any
age, because repeated return means real intent. Last: everything else, by
freshness.</p>

<p><b>Speed dominates every other factor.</b> The same cart converts dramatically
better at two hours than at two days, and by a week it is close to a cold call. If a
client can only do one thing with this list, it is to work the top of it today
rather than all of it eventually.</p>

<p><b>What to say, and what not to.</b> The customer chose a product and stopped;
they know they did. Opening with "I saw you didn't complete your order" is accurate
and slightly accusatory. Opening with the product — "I'm calling about the Baozem
order, I can complete it for you now" — treats it as an order in progress, which is
what it is.</p>

<p><b>The three real objections</b> behind most abandonment: price, trust, and a
practical obstacle — delivery time, payment method, an address they were unsure
about. The last is the most common and the easiest to solve, and you only find it by
asking. Nobody abandons a form because the button was the wrong colour.</p>

<p><b>Convert closes the loop.</b> The cart becomes an order attributed to the same
form and campaign, so recovered revenue lands in the right place in ROAS. A client
recovering carts and raising the orders manually is losing the attribution and will
under-report their own campaigns.</p>

<blockquote><b>DRILL:</b> A client assigns cart recovery to whoever is free. What do
you recommend instead? — Name someone. A list worked by whoever has a spare moment
is worked at the wrong end and never twice by the same person, so nobody learns which
objections recur. One owner working the top daily beats five people working it
occasionally.</blockquote>

<!--deep--><p><b>Why recovery belongs to a closer rather than to marketing.</b> It
is a sales conversation with an objection to handle, not a message to send. Clients
often route it to whoever runs campaigns, because the cart came from a form.
Attribution belongs to the form; the phone call belongs to somebody who sells.</p>

<p><b>The number to report to a client, monthly.</b> Recovered revenue as a share of
abandoned value, and the median age at recovery. The first proves the discipline is
worth funding; the second shows whether it is being worked daily or in
bursts.</p>
""",
 "checks": [
  {"q": "The highest-priority abandoned carts are:",
   "opts": ["High value with a phone number, abandoned within about two hours",
            "The oldest, so they are not lost", "The largest by item count",
            "Those with no phone number"],
   "ans": 0, "why": "Conversion collapses with age; the top of the list today beats the whole list eventually.", "sort": 0},
  {"q": "Recovered carts should be closed using Convert rather than raising an order manually because:",
   "opts": ["Convert preserves attribution to the form and campaign",
            "It is faster", "Manual orders are blocked", "It avoids the duplicate check"],
   "ans": 0, "why": "Raising manually loses the attribution and under-reports the campaign in ROAS.", "sort": 1},
  {"q": "The most common objection behind abandonment is:",
   "opts": ["A practical obstacle — delivery, payment method, address uncertainty",
            "Price alone", "Form design", "Brand unfamiliarity"],
   "ans": 0, "why": "It is also the easiest to solve, and you only find it by asking.", "sort": 2},
 ]})

# ─────────────────────────────────────────────────────────────────── apply
d = json.load(io.open(PATH, encoding="utf-8"))
d["c2"]["lessons"] = C2
d["c2"]["desc"] = ("Orders end to end at consultant level: the list and why filters explain most "
                   "missing orders, order creation with the duplicate and consolidation settings "
                   "you configure, the status spine and the four terminal statuses that drive the "
                   "follow-up pool, the drawer, editing money safely, assignment and after-sales, "
                   "and the customer directory as the other axis on the same data.")
d["c3"]["lessons"] = C3
d["c3"]["desc"] = ("The campaign engine: lead forms end to end, the three builder steps with "
                   "package pricing and the routing that product category decides, publishing and "
                   "the token, embedding by iframe or WordPress plugin including the CORS "
                   "decision, and the two lists — submissions and abandoned carts — with the "
                   "recovery discipline that turns the second into revenue.")
io.open(PATH, "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False) + "\n")

wc = lambda h: len(re.sub(r"<[^>]+>", " ", h).split())
for name, mod in (("c2", C2), ("c3", C3)):
    print("%s — %d chapters" % (name, len(mod)))
    for i, c in enumerate(mod, 1):
        print("  ch%d %4dw %d checks  %s" % (i, wc(c["html"]), len(c["checks"]), c["title"][:48]))
    print("  mean %d words" % (sum(wc(c["html"]) for c in mod) // len(mod)))
