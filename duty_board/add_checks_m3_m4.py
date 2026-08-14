#!/usr/bin/env python3
"""Closer track — end-of-lesson check questions, modules 3 and 4.

Completes the track: 108 checks across 36 chapters.

Same rules as modules 1 and 2. Formative, never scored, never on a transcript,
never drawn from the exam bank — the last of those is verified automatically
after writing, because five drafts in the previous pass duplicated exam
questions and a check that repeats the paper both teaches nothing and leaks it.

Run from the app package directory:  python3 add_checks_m3_m4.py
Then:  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_lesson_checks
"""

import io
import json
import re
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv


def c(q, opts, ans, why):
    return {"q": q, "opts": opts, "ans": ans, "why": why}


CHECKS = {
"reports_analytics": {
"The reports section — directory, roles and dates": [
 c("You cannot find a report a colleague mentioned. Most likely:",
   ["It has been removed in an update", "Your role does not include it",
    "It only appears once data exists", "It is filed under a different category"], 1,
   "Individual performance data is personal. A report you cannot find is almost always a role restriction rather than a missing feature."),
 c("You paste a conversion figure into a message. You must also carry:",
   ["The report's category", "Your role level", "The date range it was read over", "The branch filter"], 2,
   "Every metric on the page refreshes with the date filter, so a number without its period is not a claim anyone can check."),
 c("The Compare toggle matters because:",
   ["It doubles the sample size", "Direction is usually more actionable than the absolute figure",
    "It removes cancelled orders", "It is required for exports"], 1,
   "62% is a number. 62% against 71% last month is a conversation — absolutes tell you where you are, comparisons where you are heading."),
],
"The dashboard and the reports — two different instruments": [
 c("The dashboard is best used to:",
   ["Draw conclusions for a review", "Notice something worth investigating in a report",
    "Compare completed months", "Export figures for a board pack"], 1,
   "Notice with the dashboard, conclude with the reports. A tile that looks wrong is a reason to open a report, not a finding."),
 c("Not Ready reads higher than Total Orders for the same month because:",
   ["The tile is counting a different product set", "Not Ready ignores the timeframe and shows the whole book",
    "Duplicates are counted twice", "Total Orders excludes cancelled orders"], 1,
   "Terminal tiles are period-scoped; in-flight tiles are not. Once you know which is which, the dashboard stops looking broken."),
 c("Duplicates are removed from the Delivery Rate calculation because:",
   ["They are usually cancelled anyway", "A duplicate was never a real chance to deliver",
    "They belong to a different branch", "The customer ordered twice deliberately"], 1,
   "Counting them would penalise the team for the system correctly spotting the same order twice."),
],
"Closer Summary — reading individual performance": [
 c("A closer shows low volume and high AOV. The right reading is:",
   ["An underperformer to coach on activity", "A specialist, not a slacker",
    "Someone avoiding difficult orders", "A data error worth checking"], 1,
   "Ranking them on volume alone will drive away your best upseller. Read pairs of columns, never one at a time."),
 c("Which pattern most warrants a difficult conversation?",
   ["High volume, low conversion", "Low volume, high AOV",
    "Good conversion, slow response", "Low volume, low conversion, rising cancellations"], 3,
   "The other three are a confirmation problem, a specialist, and a coachable habit. Only the fourth is a performance concern on its own."),
 c("Which metric moves first when something is going wrong?",
   ["Revenue", "Conversion rate", "Response time", "AOV"], 2,
   "Response time is the leading indicator. A manager working from delivered revenue is always reacting to something weeks old."),
],
"Team Performance — comparing units fairly": [
 c("Headcount is the most important column because:",
   ["It shows which team is growing", "It is the denominator that makes comparison honest",
    "It determines the team's target", "It drives the auto-assignment rules"], 1,
   "It measures nothing about performance and makes every other comparison meaningful."),
 c("A unit whose top performer produces most of its revenue has:",
   ["The strongest team culture", "A concentration risk — that person's resignation is a revenue event",
    "Been assigned the best leads", "Reached its capacity ceiling"], 1,
   "The report shows you the peak. You have to ask about the spread, because a flat distribution is more robust even with a less remarkable best individual."),
 c("Before comparing two units you should check:",
   ["Their headcount only", "That they cover the same categories and countries",
    "That both use Shift Management", "Their average AOV"], 1,
   "Closers are scoped to both, so two teams may be working structurally different demand. Otherwise the league table measures territory rather than skill."),
],
"Product Sales Analysis — what is actually selling": [
 c("One product at 40% of revenue is:",
   ["A success to protect and extend", "A concentration risk to raise even while numbers look good",
    "Evidence the range is too narrow", "Normal for a growing business"], 1,
   "The business inherits every risk attached to that product, and the numbers look fine right up until they do not."),
 c("Average Selling Price runs well below list. The question to ask is:",
   ["Whether list price is too high", "Whether the discounting is policy or habit",
    "Whether the product should be discontinued", "Whether returns are being counted"], 1,
   "Discounting nobody decided on is margin leaving the business without anyone choosing to spend it."),
 c("Rising units together with a rising return rate means:",
   ["Growth worth investing behind", "A product being sold to people it does not suit",
    "A stock cover problem", "A seasonal peak"], 1,
   "The returns arrive after the celebration. Read Trend and Return Rate together before acting on either."),
],
"Marketing ROAS — the money view": [
 c("A campaign shows ROAS of 2.0 on products carrying 50% margin. It is:",
   ["Comfortably profitable", "Roughly break-even before any overhead",
    "Losing money on revenue terms", "Impossible to judge without lead volume"], 1,
   "ROAS measures revenue, not profit. The threshold that matters is specific to your margins, and every business should know its own."),
 c("Cheap leads with expensive orders points at:",
   ["The advertising", "The funnel — follow-up, capacity, speed of first contact",
    "The product price", "Attribution error"], 1,
   "No amount of budget reallocation fixes a conversion problem. Read the efficiency ladder downward to find where money is lost."),
 c("A campaign's ROAS is only as honest as:",
   ["The ad platform's reporting", "The Lead Channel recorded at order creation",
    "The delivery rate that month", "The size of the budget"], 1,
   "This is the direct line between one closer's carelessness in a form field and a marketing decision worth millions."),
],
"Revenue Cohort Trends — does anybody come back": [
 c("A cohort row that collapses after month one means:",
   ["The cohort was too small to read", "Revenue was bought once and must be bought again",
    "Those customers were acquired through the wrong channel", "The product was discontinued"], 1,
   "Two businesses with identical monthly revenue can be in completely different health. This is the only report that shows it."),
 c("Recent cohorts decay faster than older ones. This is:",
   ["A seasonal effect to ignore", "A leading indicator that something has worsened",
    "Expected, since they have had less time", "A sign acquisition has improved"], 1,
   "Cohort decay moves before revenue does. Total revenue is the lagging measure."),
 c("The newest row in the matrix should be treated as:",
   ["The most reliable, being most current", "Provisional — it has had least time to behave",
    "The benchmark for older rows", "Excluded from analysis entirely"], 1,
   "It is the thinnest evidence in the table and the one people look at first, because it is new."),
],
"Reading reports as a set — the investigation path": [
 c("Before opening a second report you should:",
   ["Export the first for the record", "Write down the explanation you believe, then look for what would disprove it",
    "Check your role permissions", "Align both to the same branch filter"], 1,
   "A manager who checks only for confirmation will find it in a directory this size every single time."),
 c("A product declines and its return rate is flat, while campaign ROAS has fallen. This is:",
   ["A quality story", "A demand-generation story",
    "A stock cover story", "A pricing story"], 1,
   "Elevated returns would make it quality. Flat returns with falling ROAS points at demand generation instead — same symptom, opposite remedy."),
 c("The most expensive mistakes in this module are:",
   ["Misread numbers", "Correctly read numbers acted on without asking what else was true",
    "Reports run over the wrong branch", "Figures quoted without their period"], 1,
   "Cutting a campaign that was fine, coaching a closer handling bad leads, discontinuing a product that was merely mis-targeted."),
],
"The traps — periods, denominators, lag and small numbers": [
 c("Month-to-date revenue looks poor against last month's total. The fix is:",
   ["Wait until the month closes", "Compare day eleven against day eleven",
    "Exclude cancellations from both", "Use the Compare toggle instead"], 1,
   "A partial period compared against a finished one will always look worse, because it is measuring less time."),
 c("Why does the denominator matter when setting a target on a rate?",
   ["It changes how the chart is scaled", "People optimise for what is measured, including in unintended ways",
    "It determines who can see the report", "Rates are unreliable below 100 orders"], 1,
   "A delivery rate excluding cancelled orders gives a team the incentive to cancel marginal ones. Know the denominator before you set the target."),
 c("A closer tops the table on four orders. You should:",
   ["Hold them up as the example", "Check the base before believing the rate",
    "Assume their orders were unusually easy", "Recalculate excluding cancellations"], 1,
   "Percentages on small bases move violently. The loudest movements in any ranking are usually the smallest samples."),
],
},
"team_workflow": {
"Distributing the work": [
 c("Auto-assignment is running well. Does the New Lead card still need a daily look?",
   ["No — the rules handle distribution", "Yes — auto-assignment distributes, it does not supervise",
    "Only when volume is unusually high", "Only if Shift Management is enabled"], 1,
   "Nothing notices that a lead has waited since Tuesday. Skip the scan for a week and the cost appears as orders never converted, not as a failure."),
 c("Round-robin spreads orders evenly by count. The limitation is:",
   ["It ignores branch boundaries", "Even by count is not even by effort",
    "It cannot respect daily caps", "It excludes always-available closers"], 1,
   "A closer receiving a run of complicated orders carries more work than the count suggests, and no rule can see it."),
 c("You reassign a struggling closer's order on day eight rather than day one. It is now:",
   ["Equivalent — the order is unchanged", "A rescue rather than a lead",
    "Ineligible for the follow-up pool", "Counted against the new closer"], 1,
   "Reassign early. The same order eight days later has a customer who has been waiting and may have bought elsewhere."),
],
"Capacity — caps, coverage and the New Lead queue": [
 c("New Leads cluster in one country while closers sit under their caps. This names:",
   ["A router fault", "A coverage gap rather than a general shortage",
    "Caps set too low", "A seasonal spike"], 1,
   "Concentration tells you where. Filter the queue by category and country before concluding anything about headcount."),
 c("A closer accepts a higher cap. The real test of whether it was right is:",
   ["Whether their volume rises", "Whether they end the day with untouched morning orders",
    "Whether their conversion holds", "Whether New Leads fall"], 1,
   "A cap above what someone can handle produces a hidden backlog inside one list, where customers are unserved but appear served."),
 c("When capacity frees after a backlog, work:",
   ["Highest value first", "Newest first, while interest is fresh",
    "Oldest first", "Evenly across categories"], 2,
   "Caps reset daily, so a backlog never clears retroactively. The oldest customers have waited longest and are closest to gone."),
],
"Running closer shifts": [
 c("The safe rollout order for Shift Management is:",
   ["Roster first, then enable", "Everyone always-available, then remove the flag person by person",
    "Pilot one team, then extend", "Enable overnight when volume is low"], 1,
   "Starting always-available keeps behaviour identical, so a coverage gap cannot be created by accident."),
 c("A client reports orders waiting overnight. The question is:",
   ["Whether store routing is misconfigured", "Whether lead coverage has a gap",
    "Whether daily caps reset correctly", "Whether the sweep ran"], 1,
   "Store orders were never subject to shifts, so an overnight backlog is always a roster gap."),
 c("Three closers are on duty, all covering the same category. The roster is:",
   ["Fully staffed", "Covered by hours but not by category",
    "Over-staffed for that window", "Compliant provided caps are set"], 1,
   "Coverage is about what those on duty can actually receive, not merely that somebody is there."),
],
"Governing the follow-up recovery team": [
 c("A pool threshold set too long produces:",
   ["A pool nobody can keep up with", "Leads that die of age before anyone rescues them",
    "Cancellations attributed to the wrong closer", "Sweep failures"], 1,
   "Watch how long your best closers persist before their attempts stop — that is the right threshold, and it is usually under ten days."),
 c("The pool grows steadily alongside a rising cancellation rate. This suggests:",
   ["The threshold is too short", "Orders are being created from softer interest than before",
    "The recovery team is understaffed", "The sweep is running twice"], 1,
   "That is a confirmation problem at the front, not a recovery problem at the back — and it is the reading people miss."),
 c("You should choose follow-up members for:",
   ["Seniority", "The highest conversion rates",
    "Patience and the ability to pick up another person's conversation", "Availability outside core hours"], 2,
   "The work is phoning people already phoned, about an order they hesitated over, using someone else's notes."),
],
"Managing cart recovery": [
 c("Many carts Contacted, few Recovered. This needs:",
   ["More staff on recovery", "Coaching on script, offer or timing",
    "A stricter prioritisation rule", "Faster contact after abandonment"], 1,
   "A Not Contacted pile-up is a staffing gap. Calls happening without landing is a different problem entirely."),
 c("Why is a standing rule better than judging each cart on merit?",
   ["It is more accurate", "It survives a busy week without requiring a decision",
    "It satisfies privacy requirements", "It removes the need for prioritisation"], 1,
   "A better rule that requires judgement on every row gets abandoned the first time the team is stretched."),
 c("A team consistently recovering last week's carts rather than yesterday's is:",
   ["Working the highest-value rows first", "Prioritising by whatever is at the top of the screen",
    "Following the documented policy", "Limited by phone availability"], 1,
   "Nominally by value, actually by convenience. Watch the age of what is being worked, not only the recovery count."),
],
"The manager's guardrails": [
 c("A request arrives to let a closer see revenue figures. This is:",
   ["A Settings checkbox to toggle", "A disclosure decision belonging to whoever owns that policy",
    "Automatic once they reach a volume threshold", "Available only to follow-up members"], 1,
   "Money visibility is a role decision, never a workaround arranged quietly."),
 c("The pattern behind every manager-only power is that it either:",
   ["Requires desk access, or affects billing", "Governs others' work, or reveals money",
    "Changes historical records, or affects reporting", "Is dangerous, or is rarely needed"], 1,
   "Closers get everything needed to work their own book and nothing that governs anyone else's. Every request fits one category or the other."),
 c("Can a manager tidy an order's timeline after mishandling?",
   ["Yes, with System Manager rights", "Yes, by adding a correcting note that supersedes it",
    "No — the record accumulates and stays", "Only within the same day"], 2,
   "A record that could be tidied by whoever looked worst in it would settle no arguments, which is the whole reason the timeline is worth consulting."),
],
"Duplicate — the power that belongs to you alone": [
 c("Two orders, same number, same day, same items. Most likely:",
   ["A genuine repeat purchase", "A genuine duplicate — the customer called twice or two closers took one enquiry",
    "A system error to report", "A test order"], 1,
   "Same items is the signature. Different items on the same day is usually a customer adding a purchase."),
 c("A closer reports disproportionately many suspected duplicates. The conversation is about:",
   ["Their diligence, which should be recognised", "How they create orders, not how they spot them",
    "Whether detection settings need tightening", "Their daily cap"], 1,
   "The duplicate banner at creation exists to prevent this, and it informs rather than blocks — so it can be clicked past."),
 c("Recording the reason on each duplicate matters because:",
   ["It is required before saving", "A pattern by lead channel is a finding about the source, not the team",
    "It restores the order to the numbers", "It notifies the original closer"], 1,
   "Six months later the pattern is only visible if somebody wrote down why each one was marked."),
],
"Reading your team's numbers, and the conversation after": [
 c("The unit's conversion has fallen. Your first step is:",
   ["Rank individuals and start at the bottom", "Rule out a structural cause before any individual conversation",
    "Raise caps to increase volume", "Reassign the unit's orders"], 1,
   "If the whole unit moved, you would be coaching people for a change in the leads, the stock position or the delivery side."),
 c("When cancellations are genuinely a performance matter, the metric to work on is:",
   ["The cancellation rate itself", "Conversion rate", "Order creation and confirmation", "Response time"], 2,
   "Cancellations are fixed at order creation, not at cancellation. The remedy is almost always upstream of the number that looks bad."),
 c("A performance conversation without an agreed change and a review date:",
   ["Is still useful as a warning", "Will be repeated in a month with the same numbers",
    "Should be recorded in the timeline", "Requires escalation to a director"], 1,
   "Name the one metric, agree what will be different, and put a date on it. A fortnight is usually enough to see movement."),
],
"The manager's week": [
 c("Which belongs in the daily rhythm?",
   ["Revenue per agent", "Releasing stale pool claims",
    "Category and country coverage", "Role assignment audit"], 1,
   "Distribution and stale claims are where captured demand is lost within a single day. The rest are weekly, monthly or quarterly."),
 c("Most of what goes wrong in this system is:",
   ["A configuration error", "An omission that produces no error message",
    "A permissions failure", "A reporting lag"], 1,
   "A lead nobody distributed, a claim nobody released, a roster gap nobody noticed. The cost appears as customers who quietly bought elsewhere."),
 c("A busy week means the monthly review gets dropped. This is:",
   ["Sensible triage", "Backwards — those reviews prevent next month's crisis",
    "Acceptable if the daily habits held", "Only a problem if repeated twice"], 1,
   "Put them in a calendar rather than a good intention, and treat a missed review as an event worth noticing."),
],
},
}


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    total = 0
    problems = []
    for mod_key, chapters in CHECKS.items():
        mod = data[mod_key]
        by_title = {l["title"]: l for l in mod["lessons"]}
        bank = {norm(q["q"]) for q in mod["questions"]}
        for title, checks in chapters.items():
            if title not in by_title:
                sys.exit("ABORT: chapter not found in %s: %s" % (mod_key, title))
            for i, ch in enumerate(checks):
                ch["sort"] = i
                if norm(ch["q"]) in bank:
                    problems.append("EXAM OVERLAP  %s / %s" % (mod_key, ch["q"][:56]))
                if len(ch["opts"]) < 3:
                    problems.append("TOO FEW OPTS  %s / %s" % (mod_key, ch["q"][:56]))
                if not 0 <= ch["ans"] < len(ch["opts"]):
                    problems.append("BAD ANSWER    %s / %s" % (mod_key, ch["q"][:56]))
                if len((ch.get("why") or "").strip()) < 40:
                    problems.append("WEAK WHY      %s / %s" % (mod_key, ch["q"][:56]))
            if not CHECK_ONLY:
                by_title[title]["checks"] = checks
            total += len(checks)
        missing = [l["title"] for l in mod["lessons"] if l["title"] not in chapters]
        print("%-18s %d chapters covered%s" % (
            mod_key, len(chapters), "" if not missing else "  MISSING: %s" % missing))

    if problems:
        print("\nABORT — %d problem(s):" % len(problems))
        print("\n".join("  " + p for p in problems))
        sys.exit(1)
    print("\n%d checks, no exam overlap, all well formed." % total)

    if CHECK_ONLY:
        print("--check given; nothing written.")
        return
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("Written. Push with:")
    print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_lesson_checks")


if __name__ == "__main__":
    main()
