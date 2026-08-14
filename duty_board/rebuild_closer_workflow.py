#!/usr/bin/env python3
"""Closer track — Closer Workflow & Follow-Up to standard.

Six chapters at a 1,323 mean become nine at standard depth. This is the module
a working closer lives in every day, so it carries the most practice weight in
the track.

Three chapters are new:
  ch2  Your daily limit — the cap, and what it protects
  ch8  Working a shift well — the closer's day
  ch9  When it goes wrong — recovering from the common mistakes

Two corrections ride along, both found while deepening:

  * Chapter 7 (was 6) said the dashboard's status cards follow the selected
    period-to-date timeframe. Only the terminal cards do; in-flight cards
    ignore the timeframe and show the whole book. Corrected to match.
  * Chapter 4 (was 3) listed "Rescheduled" among terminal statuses that can
    never be pooled. Delivery Rescheduled is not terminal — an order with a
    future delivery date simply is not stalled, which is a different and
    better reason for excluding it. Reworded as eligibility rather than
    finality.

Run from the app package directory:  python3 rebuild_closer_workflow.py
Then:  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons
"""

import io
import json
import re
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv

L = [
("How leads reach you — shifts and assignment", 8, """<p>New online leads are assigned to closers automatically, and understanding the rules that govern that assignment is the difference between a closer who wonders why their list is empty and one who knows.</p>

<p><b>When Closer Shift Management is enabled, only closers whose shift is active right now receive automatic leads.</b> There is no clock-in and nothing to press. Availability follows the schedule: if the current time falls inside one of your assigned shifts, you are on shift.</p>

<p><b>What happens when nobody is on shift.</b> The lead waits as a New Lead. It is not discarded, not lost, and not given to somebody unsuitable. The system re-checks roughly every ten minutes and assigns it the moment a qualifying closer comes on shift. This is worth internalising, because it is the reassurance behind the whole design: the queue is a waiting room, not a bin.</p>

<p><b>Always-available closers</b> receive leads at any hour regardless of the schedule. The flag exists for supervisors and overflow cover — the people who are meant to absorb what the roster cannot.</p>

<p><b>Overnight shifts work exactly as you would hope.</b> An end time earlier than the start — 10:00 pm to 6:00 am — is understood as running past midnight into the next morning. You do not need to split it into two shifts, and doing so would create a gap at the boundary.</p>

<p><b>Daily limits sit on top of shifts, not inside them.</b> To receive an automatic lead you must be both on shift <i>and</i> under your daily assignment limit. Two independent gates, and failing either one is enough to stop the flow. The limit resets at midnight server time regardless of where you are in your shift — which means an overnight closer receives a fresh allowance partway through the night rather than at the end of it.</p>

<p><b>Two important exemptions.</b> Online store orders route as they always have and are never held back by shifts — a customer who has already paid is not asked to wait for a roster. And manual assignment always works: a manager can hand any closer any lead at any time, and shifts never block it. The picker shows who is on shift as a hint, nothing more.</p>

<blockquote>IMPLEMENTATION TIP: If leads stop arriving mid-shift, check your daily count before assuming a fault. Reaching your limit looks exactly like the system having gone quiet, and it is by far the more common explanation.</blockquote>

<blockquote>CONSULTANT NOTE: The whole feature is off by default. Until a manager enables Shift Management, assignment behaves exactly as it always did — and turning it off again fully restores that behaviour.</blockquote>"""),

("Your daily limit — the cap, and what it protects", 7, """<p>Every closer has a maximum number of orders they may be assigned in a day. New closers often read the cap as a restriction on how much they are allowed to earn. It is the opposite: it is the thing that makes what you already hold workable.</p>

<p><b>What the cap actually protects.</b> A closer holding two hundred orders does not work two hundred orders. They work perhaps forty properly and let the rest age, and the customers at the bottom of that list are unserved while appearing, in every report, to be served. The cap prevents a queue forming inside one person's screen where nobody can see it.</p>

<p><b>It is also what makes the New Lead queue meaningful.</b> When every closer for a country and category has reached their limit, incoming orders stop at New Lead rather than being pushed onto somebody already full. That queue is then a visible, measurable signal that demand has outrun capacity — a number a manager can act on. Without caps there would be no signal at all, only quietly deteriorating service that shows up months later as cancellations.</p>

<p><b>The reset is daily, at midnight server time</b>, and it is independent of your shift pattern. If you work overnight, your allowance refreshes partway through the night rather than when your shift ends.</p>

<p><b>The two gates, once more, because closers confuse them constantly.</b> Shift governs <i>when</i> you may receive leads. The cap governs <i>how many</i>. You need both open. On shift but at your limit: nothing arrives. Under your limit but off shift: nothing arrives. Neither situation is a fault, and neither is worth a support ticket.</p>

<p><b>What the cap does not do.</b> It does not stop a manager assigning you work manually — manual assignment bypasses it. It does not remove orders you already hold. And it does not limit how many orders you can <i>deliver</i>, only how many new ones can be pushed to you automatically in a day. A closer who works their existing list down does not thereby earn more automatic leads that day; the counter is about what arrived, not what remains.</p>

<blockquote>IMPLEMENTATION TIP: If you are consistently hitting your cap early and clearing your list well before the day ends, that is a conversation to have with your team lead rather than a frustration to sit on. A cap set below what you can genuinely handle is capacity the business is leaving unused — and New Leads are probably queuing while you wait.</blockquote>

<blockquote>WATCH-OUT: The reverse is the more common problem and the harder one to admit. If you reach your cap daily and end each day with untouched orders from the morning, asking for a higher cap will make things worse, not better. The constraint is not the allowance; it is the hours.</blockquote>"""),

("The follow-up pool — the idea and the fairness rule", 8, """<p>Leads that are not picking up, asking for callbacks, or otherwise stalling tend to die quietly. They sit in a non-delivered status with nobody actively chasing them, and because they are not failures yet, nothing flags them. Over months this is one of the largest silent losses in a call-centre operation.</p>

<p><b>The Follow-Up Workflow gives those leads a recovery path.</b> Stalled orders gather in a shared Follow-Up Pool. A dedicated Follow-Up Team picks them out, works them, and either routes them back into delivery or closes them out honestly.</p>

<p><b>The whole design rests on one principle: fair attribution.</b> The original closer keeps credit for the lead until it is actually delivered. Only on successful delivery does the follow-up closer who recovered it earn the credit. Cancellations stay with the original closer, so failure is never laundered onto the recovery team.</p>

<p>That rule is doing more work than it appears. Consider the alternative designs and what each would produce. If credit transferred on entry to the pool, every closer would dump difficult leads there the moment they got hard, and the pool would become a bin for the unwanted. If cancellations transferred with the lead, the recovery team's numbers would be destroyed by other people's poorly confirmed orders, and nobody would want the job. The rule as built makes the pool safe to use and safe to work in, which is why it is stated as a principle rather than buried as a detail.</p>

<p><b>The vocabulary, because these words have precise meanings here.</b> The <b>pool</b> is the shared list under Follow-Up in the left navigation. A <b>Follow-Up Team Member</b> is a Closer whose record carries that flag — only they see the pool. To <b>claim</b> is to take an unclaimed order so that only you work it. To <b>convert</b> is to route a claimed order back into delivery. To <b>release</b> is to return it for someone else.</p>

<p><b>One distinction to hold firmly: "In Follow-Up" is an internal flag, not a status.</b> A pooled order keeps whatever status it last had. This is why a lead can be in the pool and Not Picking at the same time, and why the pool never appears in the lifecycle you learned in the previous module. It sits alongside the lifecycle rather than inside it.</p>

<blockquote>CONSULTANT NOTE: The same person can be a normal closer and a follow-up member at once — the two are independent flags on the Closer record. In smaller teams this is the usual arrangement rather than the exception.</blockquote>

<p><b>A note on who should be on the follow-up team.</b> The work is different from ordinary closing. A follow-up member phones people who have already been phoned, often more than once, about an order they hesitated over. Patience matters more than pace, and the ability to read someone else's notes and pick up their conversation matters more than either. It is not a junior job and it is not a punishment posting — the leads in the pool are the hardest in the book, which is exactly why they are worth recovering.</p>"""),

("Sending a stalled lead to follow-up", 8, """<p>Orders enter the pool two ways, and the difference between them is the difference between a safety net and good practice.</p>

<p><b>The nightly sweep</b> runs shortly after midnight and adds every order older than the configured threshold — ten days from creation by default — that is not in a finished status and not already pooled. This is the net. It catches what nobody caught.</p>

<p><b>The manual route</b> is for a closer who already knows a lead is stuck. Open the order, open its Actions menu, choose <b>Reassign to Follow-Up</b>, and confirm. There is no reason to let a lead you know is stalled sit for ten days waiting to be swept, and every day it waits makes recovery less likely.</p>

<p><b>The option only appears under four conditions.</b> The workflow must be enabled; you must be the order's closer; the order must not already be pooled; and it must sit in an eligible stalled status — the not-picking, call-back, on-hold family. If the action is missing, one of those four is the reason.</p>

<p><b>Now the part closers most need to hear, because it governs whether they use the feature at all.</b> Sending an order to the pool does <b>not</b> remove it from you and does <b>not</b> change its status. You remain the closer. The lead stays in your reports. Your daily counter is not reduced.</p>

<p>Treat the pool as a safety net for the lead rather than a hand-off of credit. It is help, not surrender. A closer who avoids the pool because they think they are giving something away simply keeps a dying lead to themselves — and nobody wins that.</p>

<p><b>What cannot be pooled, and why.</b> Finished orders — Delivered, Cancelled, Duplicate — are never eligible, by sweep or by hand. There is nothing to recover from an order that has reached its end.</p>

<p>Delivery Rescheduled is also excluded, but for a different reason worth understanding rather than memorising. A rescheduled order is not finished; it is simply <i>not stalled</i>. It has a future delivery date and a plan attached. The pool exists for orders that have stopped moving with nobody attending to them, and a rescheduled order is the opposite of that. Putting it in the pool would have the recovery team chasing a customer who is already expecting delivery on Thursday.</p>

<blockquote>WATCH-OUT: If you find yourself wanting to pool an order that does not qualify, the honest question is whether the status on it is accurate. An order you believe is stalled but which shows as Rescheduled is usually an order whose status was never updated after the reschedule fell through.</blockquote>

<p><b>How soon should you pool something?</b> The sweep waits ten days by default, which is a sensible net but a poor plan. Ten days on a lead that stopped answering on day two is eight days of nothing happening. If you have made three genuine attempts across two or three days with no contact and no pattern to work with, that lead is stalled — pool it and let a fresh voice try. Waiting for the sweep is not diligence; it is delay with a system doing the waiting for you.</p>"""),

("Working the pool — claim, convert, release", 8, """<p>Follow-up team members open the pool from <b>Follow-Up</b> in the left navigation. Each row is a pooled order: the ID, which opens the drawer in place; the customer; its unchanged status; phone; value; when it entered the pool; and <b>Claimed By</b> — a name, or "unclaimed".</p>

<p>Filter between All Pool, Claimed by Me and Unclaimed, search by order, name or phone, and page through fifty at a time.</p>

<p><b>Claim before you work.</b> Claiming an unclaimed order makes it yours: the actions flip to Release and Convert, and an audit comment is logged. If someone beats you to it by a moment you will see "Already claimed by…" — refresh and pick another rather than trying again.</p>

<p>The claim is what stops two people phoning the same customer within an hour of each other. That call is not merely wasteful; it tells the customer the business does not know what it is doing, on a lead that was already fragile.</p>

<p><b>Review before acting.</b> Open the drawer in place, read the history and the comments, add your own attempt notes, and close — the list refreshes itself. This is not a formality. A pooled lead usually carries a reason it stalled, and the previous closer's notes are the difference between opening with "I understand you asked us to call after five" and opening with a question the customer has already answered twice.</p>

<p><b>Convert when the customer is ready.</b> The dialog optionally takes a delivery agent, or you may choose to set one later, and the order's status returns to Assigned so the delivery side picks it up.</p>

<p><b>The converted order stays in the pool until it is actually Delivered.</b> This is deliberate, and it is the design decision most worth understanding: the recovery team's job is not finished when a customer says yes. It is finished when the goods arrive. Leaving the order visible means somebody is still watching a lead that has already stalled once and is more likely than average to stall again.</p>

<p>Convert on an unclaimed order claims and converts in one click, for the case where you have just spoken to the customer and there is nothing to deliberate.</p>

<p><b>Release an order you cannot continue</b> — it returns unclaimed for anyone else. You can only release your own claims; managers can release anyone's, which is how an order claimed by someone now on leave gets back into circulation.</p>

<p><b>Dead leads are cancelled through the normal order flow</b>, not released and abandoned. Wrong number, refusal, genuine duplicate: cancel it properly with a reason. The cancellation records against the original closer, never the recovery team.</p>

<blockquote>IMPLEMENTATION TIP: Release honestly and early. An order claimed and then ignored is worse than an unclaimed one, because it looks attended to. If you claim three and only get to one, release the other two before you finish for the day.</blockquote>"""),

("Attribution — who gets the credit, and when", 8, """<p>The attribution rules exist to keep the numbers fair between the original closer and the recovery team. Walk the life of a pooled order and each step becomes obvious.</p>

<p><b>Enters the pool</b>, by sweep or by hand. The closer is unchanged, the counter untouched, the order is in the pool.</p>

<p><b>Claimed.</b> Still no change to ownership or counters. Claiming is a work lock, not a transfer — it says who is calling, not who owns the outcome.</p>

<p><b>Converted.</b> Routed back to delivery, still the original closer's on paper, and still in the pool.</p>

<p><b>Delivered.</b> Now the follow-up closer becomes the order's closer, earns the credit, and their counter increments under the standard online-lead rule. The order leaves the pool.</p>

<p><b>Cancelled from the pool.</b> It stays the original closer's and leaves the pool. The failure never moves.</p>

<p><b>In one sentence:</b> the original closer carries the lead — and the risk — right up until a successful delivery; only a delivered recovery moves the credit.</p>

<p><b>Why the credit moves only at delivery, and not at conversion.</b> Conversion means a customer said yes on a phone call. Delivery means goods arrived and, on cash on delivery, money was collected. Between those two points a meaningful proportion of recovered orders fail again — these are, by definition, leads that already stalled once. Moving credit at conversion would reward the recovery team for the easy half of the work and leave the original closer carrying failures they had no ability to influence.</p>

<p><b>And why cancellations never move.</b> A cancelled lead is usually a lead that should not have been created in the state it was, or was confirmed too loosely at the front. That is information about the original closer's work, and it belongs in their numbers. If cancellations transferred, the fastest route to a clean cancellation rate would be to pool every doubtful order and let somebody else absorb the consequence.</p>

<blockquote>IMPLEMENTATION TIP: This is the answer to the question every closer asks first — "if I send my lead to follow-up, do I lose it?" No. You keep it, and you keep it in your reports, unless and until somebody else actually lands it. The only thing you can lose by pooling a lead is a delivery you were not going to make.</blockquote>

<p><b>One consequence worth spelling out for follow-up team members.</b> Because credit only arrives on delivery, your own numbers depend on orders reaching customers rather than on customers agreeing on the phone. That makes the decision to convert with a delivery agent attached, rather than leaving it to be set later, a decision about your own outcome as well as the customer's. A converted order with nobody lined up to carry it is a conversion that can quietly stall a second time.</p>"""),

("Your numbers — the dashboard and My Summary", 8, """<p>Two screens tell a closer how they are doing, and they answer different questions.</p>

<p><b>The dashboard is the pulse.</b> Status cards, each clickable straight into the Orders list pre-filtered to exactly those orders — and, for a closer, automatically narrowed to your own. A build-up in an early card means leads are waiting on you. A build-up mid-flow means fulfilment needs a push rather than you.</p>

<p><b>One thing about the dashboard that catches almost everyone.</b> Not every card responds to the timeframe control. Cards for terminal outcomes — total orders, delivered, cancelled — are scoped to the period you selected. Cards for in-flight statuses such as Agent Notified or Delivery In Progress ignore the timeframe entirely and show the whole book as it stands right now. Change the timeframe and watch which cards move; it takes half a minute and it stops you reading a lifetime figure as though it were this week's.</p>

<p>The practical rule that follows: never divide an in-flight card by a period-scoped one. The result will look like a percentage and mean nothing.</p>

<p><b>My Summary is the scoreboard.</b> Your totals, delivered count, the value-band mix of your orders, a status breakdown, and your delivered list for the period. Where the dashboard tells you what to do next, My Summary tells you how the period has gone.</p>

<p><b>The metrics, and how to read them honestly.</b></p>

<p><b>Conversion Rate</b> is Delivered divided by Total Orders — the efficiency headline. Seventy per cent means seven of every ten orders you created actually landed.</p>

<p><b>AOV</b> is Revenue divided by Delivered, and a high AOV usually signals upselling skill rather than luck with the order book.</p>

<p><b>Cancellation Rate</b> is Cancelled divided by Total, and above roughly twenty to twenty-five per cent it is read as confirming too loosely before creating the order. It is the metric most worth watching yourself, because it moves before anybody else notices and it is entirely within your control.</p>

<p><b>Response time</b> to new assignments rounds out the picture, and it is the leading indicator of the three — it deteriorates before conversion does.</p>

<p><b>Read them together rather than one at a time.</b> Rising volume with falling conversion is not growth. Good conversion with a slow response time is a habit problem sitting on top of real skill. Low volume with high AOV is a specialist, and being ranked on volume alone would misread them entirely.</p>

<blockquote>WATCH-OUT: Revenue figures on dashboards and reports are role-gated — closers see volume and activity, not money. If your dashboard shows no Delivered Value Trend, that is the access model working, not a fault.</blockquote>"""),

("Working a shift well — the closer's day", 8, """<p>Everything in this module is a mechanism. This chapter is about the day those mechanisms are meant to support, because two closers with identical tools and identical caps routinely produce very different numbers.</p>

<p><b>Open with the queue, not the inbox.</b> Before anything else, set your filters: your orders, your call-backs due today, anything of yours that has not moved in three days. That is your worklist. A closer who begins by scrolling the full list begins by choosing, without deciding to, which customers get attention.</p>

<p><b>Work the promises first.</b> A customer who asked you to call at ten expects a call at ten. A kept callback converts at a far better rate than a cold re-attempt, and a missed one usually becomes a cancellation with extra steps. Everything else on your list can move; a promise cannot.</p>

<p><b>Then work the oldest.</b> Among orders with no scheduled commitment, age is the best available priority. The customer who has waited longest is the one most likely to have bought elsewhere, and their order is the one closest to becoming a silent loss.</p>

<p><b>Set the status honestly at the end of every attempt, and write the note while the call is still in your head.</b> "Called 2pm, no answer, second attempt today, asked yesterday for after 5pm because he works" tells the next person exactly what to do. "Called, no answer" tells them nothing and they will repeat your work.</p>

<p><b>Pool what has genuinely stalled, without waiting for the sweep.</b> If you know a lead is stuck — three attempts, no contact, no pattern to work with — send it to follow-up the same day. You keep it in your reports either way, so the only question is whether somebody is still trying.</p>

<p><b>Watch your own cancellation rate rather than waiting to be told about it.</b> It is the metric that most reliably reflects a habit, and the habit it reflects is confirming too loosely at the point of order creation. If it is climbing, the fix is upstream of everything else you do.</p>

<p><b>Close the day where you would want to start it.</b> Release any follow-up claims you did not get to. Update the statuses of anything you attempted. Leave your list in a state where a colleague picking it up tomorrow would understand it without asking you.</p>

<blockquote>IMPLEMENTATION TIP: The single highest-return habit in this chapter is the note after every conversation. It costs fifteen seconds, it is what makes a callback land well, and it is the only thing that survives your absence, your leave, and your eventual promotion.</blockquote>

<p><b>A word about pace.</b> The instinct under pressure is to make more calls. The closers with the best conversion rates are rarely the ones making the most attempts; they are the ones whose attempts land at the time the customer asked for, opening with what the customer already told somebody. That is a filing habit rather than a phone habit, and it is why the first act of a good shift is setting filters rather than dialling.</p>"""),

("When it goes wrong — recovering from the common mistakes", 7, """<p>Everybody makes these. What separates a good closer is speed and honesty in putting them right, because almost all of them get harder to fix with time.</p>

<p><b>You created a duplicate order.</b> You typed the customer's name rather than searching, and now the same person has two records or two live orders. Do not simply abandon one — an abandoned order still sits in somebody's list and counts in the numbers. Raise it: only a Closer Manager or the system can mark an order Duplicate, so tell your manager which order should stand and which should go, and say why. The correction takes a minute; the fragmented customer history, if left, is permanent.</p>

<p><b>You entered the wrong phone number.</b> If you catch it before the order goes to an agent, correct it and re-confirm with the customer. If it has already gone out and delivery failed, the status is Failed/Returned and the recovery is a corrected number plus a reschedule — not a cancellation. A wrong digit is an administrative error, and cancelling for it converts your mistake into a lost sale.</p>

<p><b>You set the wrong Lead Channel.</b> It is set once at creation and it feeds marketing attribution, so an error here quietly moves budget toward a source that did not earn it. Tell your team lead rather than shrugging: one wrong channel is noise, but a closer who habitually guesses is a distortion in the reports that nobody will trace back to a form field.</p>

<p><b>You marked a customer Not Reachable after one attempt.</b> Not Picking is one failed attempt; Not Reachable means contact has failed persistently. Using the second where you meant the first tells everyone downstream to stop trying. If you have done it, set the status back and make the attempt — nothing is lost provided you catch it.</p>

<p><b>You claimed follow-up orders and could not get to them.</b> Release them. A claimed order that nobody is working is worse than an unclaimed one, because the pool shows it as attended to and no one else will pick it up.</p>

<p><b>You cannot move an order and you are sure something is broken.</b> Almost always the next move belongs to somebody else — Order Accepted, Dispatch Assigned, Delivery In Progress, Delivered and Rejected are all set by the agent, from the agent app, and by nobody else. Check whose move it is before raising a ticket. If the order has genuinely sat with an agent too long, the remedy is a call to that agent.</p>

<blockquote>WATCH-OUT: The tempting response to every one of these is to make the record tidy rather than accurate — cancel the duplicate quietly, mark the unreachable customer as reached, leave the wrong channel alone. Each of those is a small false entry in a database other people make decisions from, and each is visible in a timeline that carries your name and a timestamp. Correcting a mistake costs a minute of mild embarrassment. Concealing one costs your credibility the first time somebody checks.</blockquote>"""),
]


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data["closer_workflow"]
    old = [(l["title"], len(re.sub(r"<[^>]+>", " ", l["html"]))) for l in mod["lessons"]]
    print("before: %d chapters, mean %d" % (len(old), sum(n for _t, n in old) / len(old)))
    new = [{"title": t, "est": e, "html": h} for t, e, h in L]
    lens = [len(re.sub(r"<[^>]+>", " ", x["html"])) for x in new]
    print("after:  %d chapters, mean %d\n" % (len(new), sum(lens) / len(lens)))
    for x, n in zip(new, lens):
        print("   %-56s %5d%s" % (x["title"][:56], n, "  <-- SHORT" if n < 2500 else ""))
    if CHECK_ONLY:
        print("\n--check given; nothing written.")
        return
    mod["lessons"] = new
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\nWritten.")


if __name__ == "__main__":
    main()
