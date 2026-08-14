#!/usr/bin/env python3
"""Closer track — Team & Workflow Management to standard.

Five chapters at a 1,161 mean become nine. This is the manager-only module and
the last one blocking the Closer Manager track.

Four chapters are new, all built on ground the track already covers:
  ch2  Capacity — caps, coverage and the New Lead queue
  ch7  Duplicate — the power that belongs to you alone
  ch8  Reading your team's numbers, and the conversation after
  ch9  The manager's week

Run from the app package directory:  python3 rebuild_closer_team.py
Then:  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons
"""

import io
import json
import re
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv

L = [
("Distributing the work", 8, """<p>Every order needs an owner, and getting leads to the right closers quickly is a manager's first operational duty. An unowned order is not merely unworked — it is invisible in every list organised by closer, which is most of them.</p>

<p><b>New Lead review is a management responsibility.</b> New leads are visible to managers and team leads for review and distribution, and auto-assignment rules — round-robin, capacity-based — do the routine spreading. But the rules only place what they can place, and what they cannot place waits for you.</p>

<p><b>Assignment happens two ways, and they coexist.</b> Automatic assignment follows your rules, respecting shifts and daily limits when Shift Management is on. Manual assignment lets you pick a closer on any order at any time, from the drawer's assignment section or the assignment dialog.</p>

<p><b>Manual assignment is never blocked by shifts or limits.</b> The picker highlights who is on shift as a courtesy, nothing more. This matters because it is your release valve: when the automatic rules have correctly declined to overload somebody, you can still make a deliberate exception for an urgent or high-value order. The system stops itself; it does not stop you.</p>

<p>The corollary is that it will not warn you either. Manually assigning forty orders to a closer already at their limit is entirely possible and entirely your responsibility.</p>

<p><b>Reassignment is equally yours.</b> The drawer's Agent section moves any order to a different closer — the tool for absences, escalations and load balancing. Use it early rather than late: an order reassigned on day one is a lead, and the same order reassigned on day eight is usually a rescue.</p>

<p><b>Distribution is a daily habit, not a configuration.</b> Auto-assignment distributes; it does not supervise. Nothing in the system notices that a lead has been waiting since Tuesday, or that one closer received twelve orders while another received two because of the shape of the roster.</p>

<blockquote>WATCH-OUT: A daily scan of the New Lead card on the dashboard — one click into the pre-filtered list — is how leads stop waiting unnoticed. Skip it for a week and the oldest waiting customers are the ones who have already bought elsewhere, which means the cost of the omission never appears as a failure. It appears as orders that were simply never converted.</blockquote>

<p><b>Distribution is also a fairness question.</b> Round-robin spreads evenly by count, which is not the same as evenly by effort. A closer who happens to receive a run of complicated orders carries more work than the count suggests, and the automatic rules cannot see it. Watching who is struggling and reassigning deliberately is the part of distribution that no rule performs for you.</p>"""),

("Capacity — caps, coverage and the New Lead queue", 8, """<p>Three settings decide whether demand reaches a human: each closer's daily cap, the categories they cover, and the countries they cover. Together they form your capacity, and the New Lead queue is the instrument that tells you whether it is enough.</p>

<p><b>How an order becomes a New Lead.</b> The router tries to assign each incoming order automatically. It can only place it with a closer who covers that order's category and country and who is under their daily cap. When no such closer exists, the order stops at New Lead and waits. It is re-checked continuously and assigned the moment capacity frees.</p>

<p><b>So the queue is a measurement, not a fault.</b> Orders sitting in New Lead are demand the business captured and cannot currently serve. That is a staffing statement, and it is the most direct one the system produces.</p>

<p><b>Read the shape, not just the size.</b> A queue that grows through the day and empties overnight means capacity is tight but adequate. A queue that grows and stays means the business is turning away money it has already paid to attract — and the remedy is more closers, higher caps, or wider coverage, never a closer working faster.</p>

<p><b>Concentration is the more useful signal.</b> New Leads clustered in one category or one country do not indicate a general shortage; they name a specific gap. A category with too few trained closers, or a country whose volume has outgrown its team, will show up here long before it shows up in revenue. Filter the queue by category and country before concluding anything about headcount.</p>

<p><b>Raising a cap is not free.</b> A cap set below what a closer can genuinely handle leaves capacity unused while leads queue. A cap set above it produces a hidden backlog inside one person's list, where the customers at the bottom are unserved but appear served in every report. The test is not whether the closer accepts the higher number; it is whether they end the day with untouched orders from the morning.</p>

<blockquote>IMPLEMENTATION TIP: Before adding headcount, check whether your existing coverage is the constraint. A country with three closers all scoped to one category will queue orders from every other category while those three sit under their caps. Widening coverage is faster and cheaper than hiring, and the queue will tell you which it needs.</blockquote>

<blockquote>WATCH-OUT: Because caps reset daily, a New Lead backlog does not clear itself retroactively. Yesterday's unassigned orders compete with today's fresh demand for the same finite capacity, and the oldest are the ones whose customers have waited longest. When capacity frees, oldest first is almost always right.</blockquote>"""),

("Running closer shifts", 8, """<p>Closer Shift Management is a manager-owned feature, off by default. Nothing changes until you enable it, and disabling it fully restores prior behaviour. It was built self-contained because closers are not necessarily staff with formal HR records — the schedule lives with the closer, not with a payroll system.</p>

<p><b>The operating rules you are accountable for.</b> Closers receive automatic online leads only while a shift is active. A lead arriving when nobody is on shift waits, and is picked up within about ten minutes of coverage returning. Always-available closers bypass the schedule entirely. Overnight shifts — an end time earlier than the start — run past midnight. And the daily limits layer on top: on shift and under limit, or no automatic lead.</p>

<p>The limit resets at midnight server time regardless of shift shape, which means an overnight closer receives a fresh allowance partway through their shift rather than at the end of it. Worth knowing before you interpret their numbers.</p>

<p><b>The rollout that cannot go wrong.</b> Mark every closer always-available first — behaviour stays identical to today, so nothing breaks and nobody notices. Then remove the flag person by person as you add their real shifts. Coverage gaps become impossible to create by accident, because a closer without a schedule is still receiving leads until you deliberately switch them over.</p>

<p>The opposite order is the tempting one and the one that hurts: build the roster first, enable the feature, and discover the gap at two in the morning when leads begin queuing behind a schedule nobody had tested.</p>

<p><b>What shifts do not control.</b> Manual assignment is never blocked. Store orders bypass shifts entirely — a paid order is never held waiting behind a roster. And shifts do not create a clock-in obligation: availability follows the schedule whether or not the closer is at their desk, which is a supervision matter rather than a system one.</p>

<blockquote>CONSULTANT NOTE: If a client reports "orders waiting overnight", the question is lead coverage, not store routing. Store orders were never subject to shifts, so an overnight backlog is always a roster gap.</blockquote>

<blockquote>IMPLEMENTATION TIP: Review the roster against the queue rather than against the rota you intended. If New Leads consistently accumulate in a particular window, that window is under-covered no matter how the schedule looks on paper.</blockquote>

<p><b>One further consideration when building the roster.</b> Coverage is not only about hours; it is about categories and countries. A shift with three closers on duty who all cover the same category leaves every other category queuing, even though the rota looks fully staffed. When you check coverage, check what those on duty can actually receive — not merely that somebody is there.</p>"""),

("Governing the follow-up recovery team", 8, """<p>The follow-up workflow is managed at three points, and all three are yours.</p>

<p><b>The switch.</b> Managers — System Manager, CRM Manager, CRM Director — can disable or enable the whole workflow from the Follow-Up page header, without going near the desk. Disabled means the nightly sweep stops and every pool action is blocked: claim, convert, release, manual reassign. Existing in-pool flags survive and reactivate on re-enable, so switching off is a pause rather than a demolition. Non-privileged users attempting the toggle are refused.</p>

<p><b>The threshold.</b> The pool threshold sets how old a stalled order must be, in days from creation, before the nightly sweep collects it. The default is ten days; the effective minimum is one.</p>

<p>Match it to how long your closers genuinely work a lead before it should escape them. Set it too short and the pool fills with leads the original closer had not finished trying, which wastes the recovery team on work already in hand. Set it too long and leads die of age before anyone rescues them. If you do not know the right number, watch how long your best closers persist before their attempts stop — that is the answer, and it is usually shorter than ten days.</p>

<p><b>The team.</b> Only Closers flagged Follow-Up Team Member see or work the pool. The flag lives on the Closer record, and the same person can be an ordinary closer and a follow-up member at once.</p>

<p>Choose for temperament rather than seniority. The work is phoning people who have already been phoned, about an order they hesitated over, using somebody else's notes. Patience and the ability to pick up another person's conversation matter more than pace.</p>

<p><b>You also hold the override:</b> managers can release any claimed order back to the pool, not only their own claims. This is how an order claimed by somebody now on leave returns to circulation, and it is worth scanning for — a claimed order nobody is working is worse than an unclaimed one, because the pool shows it as attended to.</p>

<blockquote>IMPLEMENTATION TIP: The attribution rules are your recruitment pitch for the team. Recovery members are never penalised for cancellations — those stay with the original closer — and earn full credit on every delivered save. There is no downside to taking hard leads, and saying so explicitly is what makes the role attractive rather than a punishment posting.</blockquote>

<p><b>Watch the pool's size as a diagnostic.</b> A pool that grows steadily is telling you either that the threshold is too short, or that leads are stalling upstream faster than they used to. The second is the more important reading and the one people miss: a rising pool alongside a rising cancellation rate usually means orders are being created from softer interest than before, which is a confirmation problem at the front rather than a recovery problem at the back.</p>"""),

("Managing cart recovery", 8, """<p>Abandoned carts are a managed funnel, not a scavenger hunt. Left to individual enthusiasm they get worked when somebody has a quiet afternoon, which is to say rarely and unevenly.</p>

<p><b>The Recovery Status column is your pipeline view</b> — Not Contacted, then Contacted, then Recovered or Lost — and each transition failure has a different cause.</p>

<p>A pile-up in <b>Not Contacted</b> is a staffing or prioritisation gap: nobody is picking these up, and every day they age reduces the chance of recovery. Plenty <b>Contacted</b> but little <b>Recovered</b> is a different problem entirely — the calls are happening and not landing, which points at the script, the offer, or the timing rather than at effort.</p>

<p>That distinction matters because the two look identical in a revenue report and require opposite responses. One needs people; the other needs coaching.</p>

<p><b>Prioritisation policy is yours to set</b>, and the levers are cart value, phone availability, and session duration. Higher-value carts justify more effort. A captured phone number enables the recovery call, which is the highest-yield channel by a distance. Longer sessions signal higher intent — somebody who spent four minutes on the form was seriously considering it.</p>

<p><b>A simple standing rule outperforms ad-hoc enthusiasm.</b> "Phones first, by value, same day" is a policy a team can follow without deciding anything, and it beats a better rule that requires judgement on every row. The point of a standing rule is that it survives a busy week.</p>

<p><b>Watch the age of what is being worked.</b> A team consistently recovering carts from last week rather than yesterday is a team whose prioritisation is nominally by value and actually by whatever is at the top of the screen.</p>

<blockquote>WATCH-OUT: The privacy posture is a management responsibility, not an individual one. Only actively entered data is captured, no payment details are ever stored, and follow-up must be transparent about how details were obtained with an easy opt-out. Recovery that feels like surveillance costs more trust than it recovers revenue — and the damage does not stay with the one customer who complained.</blockquote>

<p><b>Set an expiry on effort.</b> A cart that has been Contacted twice without a decision is not going to become an order because somebody calls a third time, and the attempt costs a customer's goodwill as well as an hour. Decide the number of attempts your team makes, write it down, and let them mark the rest Lost without feeling they gave up. A policy nobody has stated becomes each person's private guess, and the anxious ones over-call while the busy ones do not call at all.</p>"""),

("The manager's guardrails", 8, """<p>Threaded through every part of this system is a consistent set of powers belonging to managers alone. Held as one list, they describe the shape of the whole permission model.</p>

<p><b>Sight.</b> Managers and directors see all orders across the team; closers see their own. All reports across teams and branches are open to sales managers; agents see their slice.</p>

<p><b>Money.</b> Revenue, spend and ROAS are visible to Directors, Managers, Product Managers and administrators only — and this is a role decision rather than a Settings checkbox. A closer whose dashboard shows no Delivered Value Trend is seeing the access model work.</p>

<p><b>Assignment.</b> Manual assignment and reassignment of any order, at any time, unblocked by shifts or limits.</p>

<p><b>Workflow switches.</b> Enabling and disabling Shift Management and the Follow-Up Workflow, setting the pool threshold, and flagging follow-up team members.</p>

<p><b>Pool override.</b> Releasing any claimed order, and sending any eligible order to the pool — closers can only send their own.</p>

<p><b>The pattern behind the list</b> is worth stating because it answers questions the list does not. The system gives closers everything needed to work their own book and nothing that governs anyone else's work or reveals money. Every manager-only power falls into one of those two categories.</p>

<p>So when a request arrives to "let a closer do X", the useful question is which category X sits in. If it governs other people's work — assignment, thresholds, releasing another person's claim — it is a supervision power and the answer is a role change made deliberately. If it reveals money, it is a disclosure decision and belongs to whoever owns that policy. Neither is a workaround to be arranged quietly.</p>

<blockquote>CONSULTANT NOTE: Requests of this kind almost always arrive as small operational conveniences — "she covers for me on Fridays, can she just reassign?" Granting them informally produces a permission model nobody can describe six months later. Granting them as a role change produces one that survives an audit and a staff change.</blockquote>

<p><b>The corollary for your own conduct.</b> These powers are visible. Reassignment, pool releases, duplicate marking and status changes all record who acted and when, in the same timeline a closer's actions appear in. A manager who uses the override casually is as legible as a closer who uses Not Reachable casually, and the standard you hold yourself to on the record is the one your team will assume applies to them.</p>

<p><b>One power that is not on the list, deliberately.</b> Nothing here lets a manager alter history. Status changes, notes and claims accumulate in the timeline and stay there. If an order was mishandled, the record shows it was mishandled and shows the correction alongside — which is what makes the timeline worth consulting at all. A record that could be tidied by whoever looked worst in it would settle no arguments.</p>"""),

("Duplicate — the power that belongs to you alone", 7, """<p>Of every status in the system, one is deliberately withheld from closers: <b>Duplicate</b>. The system may set it automatically when an order's details match another arriving the same day, and a Closer Manager may set it manually. A closer never can.</p>

<p><b>The reason is a conflict of interest, and it is worth stating plainly to your team.</b> Marking an order duplicate removes it from the working numbers — it stops counting as something to convert, and it is excluded from the delivery rate calculation. If closers held that power, it would become a route to a clean conversion rate: any awkward order could quietly leave the denominator. Placing it with a manager keeps the decision with somebody whose own numbers it does not flatter.</p>

<p><b>What this means for you operationally.</b> Closers will bring you suspected duplicates, and each one is a small judgement rather than a formality. Two orders on the same number, same day, same items is usually genuine — the customer called twice, or two closers picked up one enquiry. Two orders on the same number, same day, different items is usually not: a customer adding a second purchase is a good outcome, and marking it duplicate destroys a real sale and a real customer relationship.</p>

<p><b>The automatic detection has the same shape and the same limits.</b> It compares details on same-day orders, which catches the common case cleanly and cannot know what a phone call would reveal. Treat automatic flags as a queue to review rather than a decision already made.</p>

<p><b>Watch the pattern as well as the case.</b> A closer who frequently reports duplicates may be diligent — or may be creating them by typing customer names rather than searching first. The duplicate banner at order creation exists precisely to prevent this, and it informs rather than blocks, so it can be clicked past. If one closer's suspected duplicates are disproportionate, the conversation is about how they create orders, not about how they spot them.</p>

<blockquote>IMPLEMENTATION TIP: Record the reason when you mark a duplicate, in the same spirit as a cancellation reason. Six months later, a pattern of duplicates concentrated on one lead channel or one campaign is a finding about the lead source rather than about your team — but only if somebody wrote down why each one was marked.</blockquote>

<p><b>What to tell your team.</b> Closers sometimes read the restriction as distrust. It is worth explaining the reasoning once, plainly: the power is withheld because it removes orders from the numbers that judge the person using it, and no system should ask an individual to be impartial about their own score. Framed that way it is a protection rather than a limitation — nobody can be suspected of tidying their own denominator, because nobody can.</p>"""),

("Reading your team's numbers, and the conversation after", 8, """<p>The reports module teaches what each column means. This chapter is about what to do on Monday morning with what they say, because the gap between reading a number and improving it is entirely a management skill.</p>

<p><b>Start with the unit, not the individual.</b> Team Performance before Closer Summary. If the whole unit's conversion has moved, no individual conversation is the right first step — you would be coaching people for a change in the leads, the stock position, or the delivery side. Ruling that out takes two minutes and prevents the most common management error in this system.</p>

<p><b>Then read individuals in pairs of columns, never one at a time.</b> High volume with low conversion is a confirmation problem at the point of order creation. Low volume with high average order value is a specialist, and ranking them on volume will drive away your best upseller. Good conversion with slow response time is a habit sitting on top of real skill, which is the most coachable pattern there is. Low volume, low conversion and a rising cancellation rate together is the only combination that genuinely warrants a difficult conversation.</p>

<p><b>Compare like with like before comparing anybody.</b> Closers are scoped to categories and countries, so two people may be working structurally different demand. A closer covering a category with thin stock cover will show cancellations that belong to the warehouse. Filtering by branch, team and date range is not a courtesy — it is what makes the comparison mean anything.</p>

<p><b>Watch leading indicators rather than results.</b> Response time deteriorates before conversion does. Cancellation rate moves before revenue does. A manager working from delivered revenue is always reacting to something that happened weeks ago.</p>

<p><b>The conversation itself.</b> Bring the number and the period, and open with the question rather than the conclusion — what does this look like from where you sit? Half the time the explanation is structural and you will learn something. When it is genuinely a performance matter, the metric to work on is almost always upstream of the one that looks bad: cancellations are fixed at order creation, not at cancellation.</p>

<blockquote>WATCH-OUT: Every metric here can be gamed, and closers work out how quickly. Conversion improves if difficult orders are avoided. Cancellation rate improves if dead orders are left open rather than closed honestly. Reading columns together is what makes gaming visible — it produces a shape that does not make sense.</blockquote>

<p><b>Say what happens next, and when you will look again.</b> A performance conversation with no agreed change and no follow-up date is a conversation that will be repeated in a month with the same numbers. Name the one metric being worked on, agree what will be different, and put a date on the review — a fortnight is usually enough for response time or cancellation rate to move.</p>"""),

("The manager's week", 7, """<p>Everything in this module is a capability. This chapter is the rhythm that turns them into a managed operation, and it is deliberately short enough to actually follow.</p>

<p><b>Daily.</b> Scan the New Lead card and clear what can be distributed. Check the follow-up pool for claimed orders nobody is working and release them. Look at the age of the oldest unworked order in the book — one number, and the most honest single indicator of whether the team is keeping up.</p>

<p><b>Daily, if you run shifts.</b> Check that the coming twenty-four hours have coverage. A gap found today is a roster change; a gap found tomorrow is a queue.</p>

<p><b>Weekly.</b> Read Team Performance before Closer Summary. Review the abandoned cart pipeline for a Not Contacted pile-up. Look at where New Leads concentrated during the week — by category and country — because that is your capacity gap named precisely. Review any duplicates marked and why.</p>

<p><b>Monthly.</b> Revenue per agent rather than revenue. Cancellation rates across the team, looking for individuals drifting rather than the average. Whether the pool threshold still matches how long your closers genuinely work a lead. Whether caps still match what people can handle — in both directions, since a cap set too low leaves capacity unused while leads queue.</p>

<p><b>Quarterly.</b> Coverage: are categories and countries still matched to where demand actually is? Follow-up team composition. Role assignments, which drift as people change jobs and nobody revisits the permission that came with the old one.</p>

<p><b>The judgement underneath the list.</b> Most of what goes wrong in this system is not a failure but an omission — a lead nobody distributed, a claim nobody released, a roster gap nobody noticed, a cap nobody revisited. None of those produces an error message. They produce customers who quietly bought elsewhere, and the cost never appears in a report as a failure.</p>

<blockquote>IMPLEMENTATION TIP: If you keep only one habit from this module, keep the daily New Lead scan. It takes a minute, it is the point where captured demand is most likely to be lost, and it is the only one on this list where a single day of neglect has a customer on the other end of it.</blockquote>

<p><b>Protect the rhythm from the crisis.</b> Every week contains something urgent, and the weekly and monthly items are the ones that get dropped for it — which is precisely backwards, because they are the reviews that prevent next month's crisis. Put them in a calendar rather than a good intention, and treat a missed monthly review as an event worth noticing rather than a week that got busy.</p>"""),
]


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data["team_workflow"]
    old = [len(re.sub(r"<[^>]+>", " ", l["html"])) for l in mod["lessons"]]
    print("before: %d chapters, mean %d" % (len(old), sum(old) / len(old)))
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
