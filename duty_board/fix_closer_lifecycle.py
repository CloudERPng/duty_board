#!/usr/bin/env python3
"""Closer track — correct the Orders & Pipeline lifecycle.

The module taught a lifecycle ZhiftCRM does not run. Chapters 3 and 4 described
New Lead -> Qualified -> Confirmed -> Assigned -> Processing -> Delivery In
Progress -> Delivered, and treated Agent Notified and Order Accepted as things
"deployed tenants often add". The truth is the other way round: Qualified,
Confirmed and Processing are retired, and the agent-side statuses are the spine.
New Lead exists but means something entirely different from what was taught —
capacity overflow, not unreviewed demand.

A closer certified on the old material would meet four statuses they were taught
that do not exist, and seven they had never seen.

This patch replaces two chapters with four, correcting the lifecycle and adding
the fact the module most needed and never had: WHO may set each status. It also
rewrites the six questions that tested retired statuses.

  before: 7 chapters, lifecycle wrong, no actor matrix, 6 bad questions
  after:  9 chapters, lifecycle correct, actor matrix taught, bank corrected

Chapters 1, 2, 5(drawer), 6(quick actions) and 7(abandoned) keep their content
here and are deepened in the following pass — they are accurate, only compressed.

Run from the app package directory:  python3 fix_closer_lifecycle.py
Then push to the site:
  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons
"""

import io
import json
import os
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv


CH_NEW_LEAD = {
    "title": "New Lead — when the router cannot place an order",
    "est": 7,
    "html": """<p><b>New Lead is not a queue of unreviewed work. It is a capacity signal.</b>
Orders arrive continuously, and ZhiftCRM tries to assign each one to a closer automatically.
When it succeeds the order lands on somebody's list as <b>Assigned</b>. When it cannot, the
order stops at <b>New Lead</b> and waits.</p>

<p>Understanding why it could not is the whole of this chapter, because a growing New Lead
count is not a closer problem to work through — it is a staffing problem to escalate.</p>

<p><b>Two constraints decide where an order can go.</b></p>

<ol>
<li><b>Every closer has a daily cap.</b> A maximum number of orders they may be given in a
day. The cap exists so that work is distributed rather than dumped: a closer holding two
hundred orders works none of them properly, and the customer at the bottom of that list is
effectively unserved while appearing to be served.</li>
<li><b>Every closer is scoped to a category and a country.</b> A closer is not a generic
pair of hands. They are assigned to particular product categories and a particular country,
because knowing the products and the delivery geography is what lets them answer a customer's
question without putting them on hold.</li>
</ol>

<p><b>So an order becomes a New Lead in one of two situations.</b> Either every closer in
that order's country has reached their daily cap, or the closers covering that order's
category have. In both cases the router has nowhere legitimate to put the order, and it
declines to break its own rules rather than overload somebody quietly.</p>

<blockquote>IMPLEMENTATION TIP: This is why New Lead volume is a management number rather than
a closer number. Orders sitting in New Lead are demand the business captured and cannot
currently serve. If the count grows through the day and empties overnight, capacity is merely
tight. If it grows and stays, the business is turning away money it has already paid to
attract — and the fix is more closers, higher caps, or wider category coverage, not a closer
working faster.</blockquote>

<p><b>What this means for you as a closer.</b> You will rarely act on a New Lead directly;
they are distributed by managers and team leads, or picked up automatically as caps reset and
capacity frees. What matters is that you understand what you are looking at when you see the
number, and that you never assume a New Lead was skipped because something was wrong with it.
Nothing is wrong with it. Nobody was free.</p>

<p><b>The pattern worth watching.</b> New Leads concentrated in one country or one category
point at a specific gap rather than a general shortage — a category with too few trained
closers, or a country whose volume has outgrown its team. That is a far more useful thing to
report upward than "we have a lot of new leads", and noticing it is the kind of observation
that gets a closer promoted.</p>

<blockquote>WATCH-OUT: Because the cap is daily, a New Lead backlog does not clear itself
retroactively. Yesterday's unassigned orders are competing with today's fresh demand for the
same finite capacity, and the oldest orders are the ones whose customers have been waiting
longest and are most likely to have bought elsewhere. When capacity frees, oldest first is
almost always the right order to work.</blockquote>""",
}

CH_SPINE = {
    "title": "The delivery spine — Assigned through to Delivered",
    "est": 8,
    "html": """<p>Every order carries a status, and statuses drive everything: which filters an
order appears in, who is responsible for it right now, which orders count as revenue, and what
automation fires. Learn the spine and you can answer the only question that matters about any
order on your screen — <i>whose move is it?</i></p>

<p><b>Assigned.</b> The order has an owner. A specific closer has been given it, their name
appears in the Agent column, and — importantly — <b>they have not yet done anything with it</b>.
Assigned is the status of an order waiting for its closer to act. If your list is thick with
Assigned orders at the end of a shift, that is not a backlog of difficult work; it is a
backlog of untouched work.</p>

<p><b>Agent Notified.</b> The closer has passed the order to an agent. This is the handover
point where the order stops being a conversation and starts being a delivery. Until the agent
responds, the order sits here.</p>

<p><b>Order Accepted.</b> The agent has accepted it. Note carefully: <b>only the agent can set
this, and only from the agent mobile app.</b> A closer cannot accept an order on an agent's
behalf, however obvious the acceptance seems. If an order has been sitting at Agent Notified
for hours, the closer's remedy is to contact the agent — not to move the status.</p>

<p><b>Dispatch Assigned.</b> The agent has handed the order to a delivery person. Again, agent
app only. The order now has a named human physically responsible for it.</p>

<p><b>Delivery In Progress.</b> The delivery person is out and on the way. Agent app only. The
courier owns the moment; the closer monitors and stays reachable in case the customer calls.</p>

<p><b>Delivered.</b> The positive terminal status. The goods are with the customer and, on a
cash-on-delivery order, the money has been collected. Only the agent can set it, from the app.
This is the status that turns an order into revenue and updates the closer's conversion
numbers.</p>

<blockquote>IMPLEMENTATION TIP: Read the spine as an alternating sequence of custody. Assigned
and Agent Notified are the closer's moves. Order Accepted, Dispatch Assigned, Delivery In
Progress and Delivered are the agent's. Four of the six stages are somebody else's to make,
which is why chasing an order means chasing a person, not clicking a button.</blockquote>

<p><b>Why so much of the spine belongs to the agent.</b> Each agent-only status records a
physical fact — a person accepted responsibility, a rider took the parcel, the parcel moved,
the customer received it and paid. Letting an office-based closer assert any of those would
turn a record of what happened into a record of what somebody assumed happened, and the first
time a parcel went missing there would be no way to tell where custody broke.</p>

<blockquote>WATCH-OUT: A closer who reports "I marked it delivered" has either misremembered or
is describing a different system. If the numbers show orders being resolved without agent
involvement, that is worth investigating rather than accepting.</blockquote>

<p><b>The old lifecycle.</b> If you have worked on an older ZhiftCRM deployment you may
remember <i>Qualified</i>, <i>Confirmed</i> and <i>Processing</i>. Those statuses are retired.
Anything written against them — old notes, old training, old reports — describes a pipeline
that no longer runs.</p>""",
}

CH_EXCEPTIONS = {
    "title": "When the path breaks — the exception statuses",
    "est": 8,
    "html": """<p>Real order books stall. The exception statuses record <i>how</i>, and choosing
the right one is closer craft: each tells a different person to do a different thing next, and
each lands differently in the numbers.</p>

<p><b>Call Back.</b> The customer answered but asked you to try another time. Note the time
they gave and honour it. A kept callback converts; a missed one becomes a cancellation with
extra steps.</p>

<p><b>Not Picking.</b> The customer is not answering. Set by closer or agent, depending on who
was calling. It is not a verdict — it is one failed attempt, recorded.</p>

<p><b>Not Reachable.</b> Contact has failed persistently: dead number, unreachable line,
repeated attempts with nothing. Closer-set. The distinction from Not Picking is the difference
between "did not answer this time" and "cannot be reached at all", and it matters because the
first deserves another attempt and the second usually does not.</p>

<p><b>Not Ready.</b> The order cannot proceed yet — usually stock or preparation. Closer-set.
The order is fine; the business is not ready to send it.</p>

<p><b>On Hold.</b> The customer asked you to wait. Closer-only, and the only exception status
that records the <i>customer's</i> decision to pause rather than a failure to reach them or a
problem on our side. Holds must not live forever: resolve the reason and move the order on.</p>

<p><b>Delivery Rescheduled.</b> The delivery date is being changed at the customer's request.
Either a closer can set it before the order goes to an agent, or the agent can after it has.
Record the new date and make sure both the customer and the delivery side are working to the
same one.</p>

<p><b>Rejected.</b> A delivery agent declined an order after being notified of it. Agent app
only. This is not the customer rejecting anything — it is the delivery side declining to carry
it, and it puts the order back in front of the closer to place elsewhere.</p>

<p><b>Cancelled.</b> Deliberately terminated before delivery. Either a closer or an agent may
set it. Always record why. Cancelled orders earn nothing but still count in volume, so they
pull directly against your conversion rate — which is exactly the incentive intended, because
a high cancellation rate usually means orders were being created without proper confirmation
at the front.</p>

<p><b>Failed / Returned.</b> One status covering two closely related outcomes: a delivery was
attempted and did not complete, or the goods went out and came back. Closer-set. Investigate
rather than close it out — a meaningful share recover through a reschedule or an address
correction, and the ones that do not still tell you something about the address quality or the
product coming from a particular channel.</p>

<p><b>Duplicate.</b> The system can set this automatically when an order's details match
another arriving the same day. A Closer Manager may also set it manually. <b>A closer cannot.</b>
That restriction is deliberate: marking an order duplicate makes it disappear from the working
numbers, which is a decision with enough consequence to sit above the person whose numbers it
affects.</p>

<blockquote>WATCH-OUT: The tempting misuse of the exception statuses is to reach for whichever
one makes your own list look tidiest. Not Reachable on a customer you called once, Duplicate on
an order you would rather not work, Cancelled on a hold you did not follow up. Each of those is
a small lie in a database that other people make decisions from — and each is visible, because
the pattern of a closer's status use is one of the first things a manager looks at.</blockquote>

<p><b>The judgement to carry.</b> Ask what you want to happen next. If the answer is "someone
should call again", that is Not Picking or Call Back. If it is "nothing until the customer says
so", that is On Hold. If it is "nobody should ever touch this again", that is Cancelled — and
it needs a reason written down.</p>""",
}

CH_ACTORS = {
    "title": "Who may move an order — and why it is not you",
    "est": 7,
    "html": """<p>The most common question a new closer asks is why an order will not move. The
answer is almost never that something is broken. It is that the next move belongs to somebody
else, and the system is holding the line.</p>

<p><b>The agent, from the mobile app, and nobody else:</b> Order Accepted, Dispatch Assigned,
Delivery In Progress, Delivered, Rejected.</p>

<p><b>The closer, and not the agent:</b> Not Reachable, Not Ready, On Hold, Failed / Returned.</p>

<p><b>Either, depending on who is holding the order:</b> Call Back, Not Picking, Delivery
Rescheduled, Cancelled.</p>

<p><b>The system, or a Closer Manager — never a closer:</b> Duplicate.</p>

<p><b>Read the pattern rather than memorising the list.</b> Every agent-only status records a
physical event: a parcel was accepted, handed over, carried, delivered, or refused. Only the
person who was there can attest to it. Every closer-only status records the state of a
<i>conversation</i>: the customer cannot be reached, has asked to wait, or the order came back.
Only the person on the phone knows that. The shared statuses are the ones where either party
might be the one holding the order at the time.</p>

<p>Once you see that, the list stops being arbitrary. The rule is simply: <b>the person who
witnessed it is the person who records it.</b></p>

<blockquote>IMPLEMENTATION TIP: This is what turns "the order is stuck" into an action. An order
sitting at Agent Notified is waiting on an agent to accept — so call the agent. An order at
Delivery In Progress that has not moved all afternoon is with a delivery person — so ask the
agent to check. Neither is fixed by anything on your screen, and both are fixed by a
thirty-second call.</blockquote>

<p><b>Duplicate deserves its own word.</b> A closer cannot mark an order duplicate, and the
reason is worth understanding rather than resenting. A duplicate order leaves the working
numbers — it stops counting as something to convert. If closers could apply it, the status
would become a way to quietly remove awkward orders from your own conversion rate. Putting it
with the Closer Manager keeps the decision with someone whose numbers it does not flatter. If
you believe an order is a genuine duplicate, raise it; do not work around it.</p>

<blockquote>WATCH-OUT: If you find yourself wanting a status you do not have, that is usually a
signal to talk to a person, not to find a workaround. Asking an agent to mark something
delivered so it clears your list, or marking a reachable customer Not Reachable so it stops
appearing, both corrupt the record in ways that surface later — in a delivery investigation, or
in a manager's review of your status pattern.</blockquote>

<p><b>What good looks like.</b> A closer who knows this matrix does not raise support tickets
about orders that will not move. They look at the status, work out whose move it is, and either
make it or chase the person who can.</p>""",
}

# --- six questions that tested retired statuses ------------------------------
NEW_QUESTIONS = {
    "The correct happy-path order of the lifecycle is:": {
        "q": "The correct order of the delivery spine is:",
        "opts": [
            "Assigned, Agent Notified, Order Accepted, Dispatch Assigned, Delivery In Progress, Delivered",
            "Assigned, Order Accepted, Agent Notified, Delivery In Progress, Dispatch Assigned, Delivered",
            "Agent Notified, Assigned, Dispatch Assigned, Order Accepted, Delivered, Delivery In Progress",
            "Assigned, Dispatch Assigned, Agent Notified, Order Accepted, Delivered, Delivery In Progress",
        ],
        "ans": 0,
        "why": "The closer assigns and notifies; the agent then accepts, assigns dispatch, travels and delivers.",
        "src": "Spine §1",
        "topic": "The delivery spine",
    },
    "What does 'Qualified' certify about an order?": {
        "q": "An order stops at New Lead. What has happened?",
        "opts": [
            "It failed validation and needs correcting",
            "A manager has held it back for review",
            "No closer could be assigned — caps or category and country coverage are exhausted",
            "The customer has not yet approved the order",
        ],
        "ans": 2,
        "why": "New Lead is capacity overflow: every eligible closer for that country and category has hit their daily cap.",
        "src": "New Lead §1",
        "topic": "New Lead and capacity",
    },
    "'Confirmed' means:": {
        "q": "An order has sat at Agent Notified since this morning. What should the closer do?",
        "opts": [
            "Move it to Order Accepted so it can progress",
            "Contact the agent — only they can accept it, from the agent app",
            "Cancel it and create a replacement order",
            "Mark it Not Ready until the agent responds",
        ],
        "ans": 1,
        "why": "Order Accepted is agent-only and app-only. A stalled order is chased by calling the person whose move it is.",
        "src": "Actors §2",
        "topic": "Who may move an order",
    },
    "An order counts toward revenue when it reaches:": {
        "q": "An order counts toward revenue when it reaches:",
        "opts": ["Order Accepted", "Dispatch Assigned", "Delivery In Progress", "Delivered"],
        "ans": 3,
        "why": "Delivered is the positive terminal status — goods with the customer and, on COD, the money collected.",
        "src": "Spine §6",
        "topic": "The delivery spine",
    },
    "A Returned order's effect on revenue is:": {
        "q": "Which status can a closer NOT set?",
        "opts": ["On Hold", "Not Reachable", "Duplicate", "Failed / Returned"],
        "ans": 2,
        "why": "Duplicate is set automatically by the system or by a Closer Manager — never by the closer whose numbers it affects.",
        "src": "Actors §4",
        "topic": "Who may move an order",
    },
    "After Delivery In Progress, an order can move to:": {
        "q": "A delivery agent declines an order after being notified. Which status records that?",
        "opts": ["Cancelled", "Rejected", "Failed / Returned", "Not Ready"],
        "ans": 1,
        "why": "Rejected is the delivery side declining to carry the order, set by the agent in the app. It returns to the closer to place elsewhere.",
        "src": "Exceptions §7",
        "topic": "Exception statuses",
    },
}


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data["orders_pipeline"]
    lessons = mod["lessons"]

    if any(l["title"].startswith("New Lead —") for l in lessons):
        print("Already applied. Nothing to do.")
        return

    titles = [l["title"] for l in lessons]
    want = ["The order lifecycle I — the happy path",
            "The order lifecycle II — holds, breaks & recoveries"]
    for w in want:
        if w not in titles:
            sys.exit("ABORT: expected chapter not found: %s" % w)

    i = titles.index(want[0])
    print("Replacing chapters %d and %d with four corrected chapters." % (i + 1, i + 2))
    new_lessons = lessons[:i] + [CH_NEW_LEAD, CH_SPINE, CH_EXCEPTIONS, CH_ACTORS] + lessons[i + 2:]

    fixed = 0
    for q in mod["questions"]:
        rep = NEW_QUESTIONS.get(q["q"])
        if rep:
            q.update(rep)
            fixed += 1
    print("Rewrote %d of %d questions that tested retired statuses." % (fixed, len(NEW_QUESTIONS)))
    if fixed != len(NEW_QUESTIONS):
        sys.exit("ABORT: not every stale question matched — bank may have been edited.")

    mod["lessons"] = new_lessons
    import re
    lens = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in new_lessons]
    print("\nChapters now %d. New chapter lengths: %s" % (
        len(new_lessons), ", ".join(str(l) for l in lens[i:i + 4])))

    if CHECK_ONLY:
        print("--check given; nothing written.")
        return
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\nWritten. Push to the site with:")
    print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons")


if __name__ == "__main__":
    main()
