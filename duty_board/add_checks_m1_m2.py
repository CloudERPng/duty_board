#!/usr/bin/env python3
"""Closer track — end-of-lesson check questions, modules 1 and 2.

Three per chapter, formative. Not drawn from the exam bank, never scored, never
on a transcript. Passing all three is what marks the lesson read.

The rationale is the point of the whole exercise. It is read at the exact moment
a learner is wrong and paying attention, which is the most teachable second in
the course — so each one explains the reasoning rather than announcing the
answer. Where a rationale can name the consequence of getting it wrong in
practice, it does.

Written against the deepened chapters, so every check has something in the text
to have understood. Distractors are plausible-wrong rather than obviously wrong;
a check a learner passes by elimination has taught nothing.

Run from the app package directory:  python3 add_checks_m1_m2.py
Then:  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_lesson_checks
"""

import io
import json
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv


def c(q, opts, ans, why):
    return {"q": q, "opts": opts, "ans": ans, "why": why}


CHECKS = {
"orders_pipeline": {
"The Orders workspace": [
 c("A manager says there are 4,000 open orders; your list shows 180. Who is wrong?",
   ["The manager — the dashboard over-counts", "Nobody — closers see only their own orders, managers see all",
    "You — your filters are hiding orders", "The system, which needs a refresh"], 1,
   "Access shapes the number. A closer's list is their own book; a manager's is the whole team's. Always ask 'for whom?' before comparing counts."),
 c("Typing 0551 into search will match:",
   ["Only orders whose phone begins 0551", "Only order IDs containing 0551",
    "Any number containing those digits anywhere", "Nothing — search needs a full number"], 2,
   "Fragment matching is how you find a customer whose number you only half caught over a bad line."),
 c("Why does the chapter argue against scrolling the order list?",
   ["It is slower than using filters", "Rows load in pages, so scrolling misses some",
    "On a large book you never reach the bottom, so those customers are never worked",
    "Scrolling clears the status filter"], 2,
   "It is not a speed problem. Scrolling silently decides which customers get no attention — and nobody notices, because nobody scrolled that far."),
],
"Creating an order": [
 c("You are creating an order for a customer whose name resembles an existing record. You should:",
   ["Create the new one — names collide often", "Verify by phone number before creating anew",
    "Ask a manager to merge them afterwards", "Add a note explaining the similarity"], 1,
   "Names collide constantly; phone numbers do not. A duplicate customer splits one person's history in two and every judgement downstream goes wrong."),
 c("The duplicate banner appears. What does it do?",
   ["Blocks creation until a manager approves", "Informs you and leaves the decision with you",
    "Automatically merges the two orders", "Cancels the earlier order"], 1,
   "A repeat purchase three weeks later is a good outcome. Software that refused it would be wrong — so the judgement is yours, and it is a real one."),
 c("Why does Lead Channel deserve care when it is only one dropdown?",
   ["It routes the order to the right closer", "It determines the delivery priority",
    "It feeds marketing attribution, and so where budget is spent", "It is required before the order can be saved"], 2,
   "A channel guessed rather than asked becomes budget moved toward a source that was not performing. One careless field, one wrong spending decision."),
],
"New Lead — when the router cannot place an order": [
 c("An order sits at New Lead. What has happened?",
   ["It failed validation", "A manager is holding it for review",
    "No closer could be assigned — caps or coverage are exhausted", "The customer has not confirmed"], 2,
   "New Lead is capacity overflow, not unreviewed demand. Nothing is wrong with the order; nobody was free to take it."),
 c("Two constraints decide where the router can place an order. They are:",
   ["Order value and customer history", "The closer's daily cap, and their category and country coverage",
    "Shift schedule and branch", "Product availability and delivery distance"], 1,
   "A closer is not a generic pair of hands. Knowing the products and the delivery geography is what lets them answer without putting the customer on hold."),
 c("New Leads grow through the day and are still there next morning. This means:",
   ["Capacity is tight but adequate", "The router has failed and needs restarting",
    "The business is turning away demand it has already paid to attract", "Closers are working too slowly"], 2,
   "A queue that empties overnight is tight capacity. A queue that persists is unserved demand — and the remedy is closers, caps or coverage, never speed."),
],
"The delivery spine — Assigned through to Delivered": [
 c("An order is Assigned. What does that tell you?",
   ["The closer has contacted the customer", "It has an owner who has not yet acted on it",
    "It is with an agent awaiting acceptance", "It is ready for dispatch"], 1,
   "Assigned means waiting for its closer. A list thick with Assigned at day's end is untouched work, not difficult work."),
 c("Which of these can a closer set?",
   ["Order Accepted", "Delivery In Progress", "Agent Notified", "Delivered"], 2,
   "Agent Notified is the closer's handover. Accepted, In Progress and Delivered are agent-only, from the agent app."),
 c("Why do so many spine statuses belong to the agent alone?",
   ["Agents are more senior", "Each records a physical fact only the person present can attest to",
    "Closers are too busy to update them", "The mobile app is faster than the desktop"], 1,
   "Letting an office-based closer assert a delivery would turn a record of what happened into a record of what somebody assumed — and custody would be untraceable."),
],
"When the path breaks — the exception statuses": [
 c("The customer did not answer. One attempt. The correct status is:",
   ["Not Reachable", "Not Picking", "Cancelled", "On Hold"], 1,
   "Not Picking is one failed attempt. Not Reachable means contact has failed persistently — the first deserves another try, the second usually does not."),
 c("The customer asked you to wait until next month. The correct status is:",
   ["On Hold", "Not Ready", "Delivery Rescheduled", "Call Back"], 0,
   "On Hold records the customer's decision to pause. Not Ready is our side not being ready — a different fact about a different party."),
 c("A delivery agent declines an order after being notified. This is recorded as:",
   ["Cancelled", "Failed / Returned", "Rejected", "Not Ready"], 2,
   "Rejected is the delivery side declining to carry it — not the customer refusing. The order returns to the closer to place elsewhere."),
],
"Who may move an order — and why it is not you": [
 c("An order has sat at Agent Notified all morning. You should:",
   ["Move it to Order Accepted so it progresses", "Contact the agent — only they can accept it",
    "Cancel and recreate it", "Mark it Not Ready"], 1,
   "A stalled order is chased by calling the person whose move it is. Nothing on your screen will fix it; a thirty-second call will."),
 c("The pattern behind who may set what is:",
   ["Seniority — managers set more statuses", "Whoever witnessed the event records it",
    "Whoever created the order owns all its statuses", "Whichever device is being used"], 1,
   "Agent-only statuses record physical events; closer-only statuses record the state of a conversation. Once you see that, the list stops being arbitrary."),
 c("Why can a closer not mark an order Duplicate?",
   ["It requires desk access", "Duplicates are only ever detected automatically",
    "It removes the order from the numbers that judge the person using it", "It would break the audit trail"], 2,
   "Marking an order duplicate takes it out of your own conversion rate. The decision belongs to someone it does not flatter."),
],
"Inside an order — the details drawer": [
 c("The drawer opens over the list rather than replacing it. Why does that matter?",
   ["It loads faster", "The list stays live, so you keep your filters between orders",
    "It allows two orders to be edited at once", "It prevents accidental status changes"], 1,
   "The alternative is re-applying your filters twenty times a day, which is how people end up scrolling instead."),
 c("You cannot find a status you expected in Update Status. This means:",
   ["Your role lacks permission", "It is not a valid move from the current status",
    "Another closer has locked the order", "The status has been retired"], 1,
   "Update Status offers only valid next moves. That is the lifecycle being enforced, not a fault to report."),
 c("The Status Timeline records who made each change. For you, that means:",
   ["Nothing — it is for managers", "Your own status discipline is permanently legible",
    "You can edit entries you made in error", "Only failed deliveries are logged"], 1,
   "Assume every status you set will one day be read back with a timestamp and your name beside it. That is exactly what makes the timeline useful."),
],
"Customers & quick actions": [
 c("The best way to create a repeat order is:",
   ["New Order from the Orders page", "New Order from the customer's profile, pre-filled",
    "Copy the previous order", "Ask a manager to clone it"], 1,
   "Working from the profile eliminates the duplicate-customer risk entirely. Every duplicate in the database was created by somebody starting from the wrong page."),
 c("A useful note after a call reads:",
   ["Called, no answer", "Customer contacted",
    "Called 2pm, no answer; second attempt today; asked for after 5pm as he works", "Will try again"], 2,
   "Write as though the next reader has never spoken to this customer, because usually they have not."),
 c("The WhatsApp quick action is disabled for a customer. This tells you:",
   ["WhatsApp is not integrated on your account", "The customer has opted out of messaging",
    "There is no valid number with country code on file", "The profile is archived"], 2,
   "A disabled button is also a warning that the number on file will not work for the confirmation call or the doorstep call either."),
],
"Abandoned carts — the almost-customers": [
 c("A visitor abandons a form, then returns later and completes it. The abandonment is:",
   ["Kept, so the recovery team can still call", "Excluded — you never chase someone who already bought",
    "Merged with the resulting order", "Marked Recovered automatically"], 1,
   "Chasing a customer who has already bought is the fastest way to make recovery calls feel like surveillance."),
 c("Why is cart recovery unusually high-return work?",
   ["Abandoned customers accept discounts more readily", "The acquisition cost is already spent and interest is proven",
    "Recovered orders carry higher margins", "They are exempt from the daily cap"], 1,
   "You are not finding a customer; you are finishing one. The advert was already paid for and the click already happened."),
 c("Two carts: high value, no phone; modest value, phone captured. Work first:",
   ["The high-value one — value outranks all", "The one with the phone",
    "Neither until they are classified", "Whichever is most recent"], 1,
   "A captured number is the difference between a recovery call and a lost ghost. Phone availability first, then value."),
],
},
"closer_workflow": {
"How leads reach you — shifts and assignment": [
 c("A lead arrives when nobody is on shift. What happens to it?",
   ["It is discarded", "It routes to an always-available closer only",
    "It waits as a New Lead and is assigned within about ten minutes of coverage returning", "It is held until the next working day"], 2,
   "The queue is a waiting room, not a bin. No lead is ever lost — which is the reassurance the whole shift design rests on."),
 c("A manager needs to give you an order while you are off shift. Can they?",
   ["No — shifts block all assignment", "Yes — manual assignment is never blocked by shifts or limits",
    "Only if you are flagged always-available", "Only for store orders"], 1,
   "The picker highlights who is on shift as a courtesy, nothing more. Automatic rules stop themselves; they do not stop a manager."),
 c("An overnight shift runs 10:00 pm to 6:00 am. You should enter it as:",
   ["Two shifts split at midnight", "One shift — an end time before the start runs past midnight",
    "A shift plus the always-available flag", "One shift per calendar day"], 1,
   "Splitting it creates a gap at the boundary, which is exactly when nobody is watching."),
],
"Your daily limit — the cap, and what it protects": [
 c("You are on shift and leads have stopped arriving. Most likely:",
   ["Shift Management was disabled", "You have reached your daily limit",
    "Your closer record was deactivated", "The lead source has gone quiet"], 1,
   "Shift and cap are two independent gates. Hitting the cap looks exactly like the system going quiet, which is why it is worth checking first."),
 c("You work 10pm to 6am. Your allowance refreshes:",
   ["When your shift ends at 6am", "Partway through the night, at midnight server time",
    "When your first order is delivered", "At the start of the shift"], 1,
   "The reset is independent of shift shape, so an overnight closer gets fresh capacity mid-shift rather than as they finish."),
 c("The cap exists mainly to:",
   ["Limit how much a closer can earn", "Spread orders evenly between branches",
    "Prevent a hidden queue forming inside one closer's list", "Reduce system load"], 2,
   "A closer holding two hundred orders works forty. The rest age unseen while appearing, in every report, to be served."),
],
"The follow-up pool — the idea and the fairness rule": [
 c("The follow-up pool exists because stalled leads:",
   ["Are usually fraudulent", "Die quietly with nobody chasing them, since they are not failures yet",
    "Cannot be worked by their original closer", "Distort the daily cap"], 1,
   "Nothing flags a lead that has merely stopped moving. Over months this is one of the largest silent losses in a call centre."),
 c("If credit transferred the moment a lead entered the pool, the likely result would be:",
   ["Faster recovery of hard leads", "Closers dumping every difficult lead into the pool",
    "Better attribution accuracy", "Fewer cancellations"], 1,
   "The pool would become a bin for the unwanted. The attribution rule is what keeps it a safety net instead."),
 c("A pooled order shows Not Picking. Is that a contradiction?",
   ["Yes — pooling should have changed the status", "No — pooling is a flag, and the order keeps its status",
    "Yes — Not Picking orders cannot be pooled", "Only if the sweep pooled it rather than the closer"], 1,
   "The pool sits alongside the lifecycle rather than inside it, which is why it never appears among the statuses you learned."),
],
"Sending a stalled lead to follow-up": [
 c("You send your stalled lead to the pool. What happens to your ownership?",
   ["It transfers to the follow-up team", "Nothing — you remain the closer and it stays in your reports",
    "It transfers only if someone claims it", "Your daily counter is reduced by one"], 1,
   "It is help, not surrender. The only thing you can lose by pooling a lead is a delivery you were not going to make."),
 c("An order shows Delivery Rescheduled. Can it be pooled?",
   ["Yes, any non-delivered order can", "No — it is not stalled; it has a date and a plan",
    "Only by a manager", "Only after the sweep threshold passes"], 1,
   "The pool is for orders that stopped moving with nobody attending. Pooling a rescheduled order sends the team chasing a customer already expecting Thursday."),
 c("Three attempts across two days, no contact, no pattern. You should:",
   ["Wait for the nightly sweep at day ten", "Pool it now",
    "Mark it Cancelled", "Mark it Not Reachable and stop"], 1,
   "Ten days on a lead that stopped answering on day two is eight days of nothing happening. Waiting for the sweep is delay, not diligence."),
],
"Working the pool — claim, convert, release": [
 c("Why claim an order before working it?",
   ["It is required before you can view details", "It stops two people phoning the same customer",
    "It transfers credit to you", "It removes it from the original closer"], 1,
   "That duplicate call is not merely wasteful — it tells a fragile customer the business does not know what it is doing."),
 c("A converted order stays in the pool until:",
   ["A manager removes it", "The customer confirms by message",
    "It is actually Delivered", "The end of the day"], 2,
   "The recovery team's job finishes when goods arrive, not when a customer says yes. These leads have already stalled once."),
 c("You claimed three and worked one. Before finishing, you should:",
   ["Leave them claimed to continue tomorrow", "Convert the other two",
    "Release the two you did not work", "Cancel them"], 2,
   "A claimed order nobody is working looks attended to, so nobody else picks it up. That is worse than leaving it unclaimed."),
],
"Attribution — who gets the credit, and when": [
 c("A follow-up closer converts a pooled order. At that moment, credit sits with:",
   ["The follow-up closer", "The original closer — credit moves only on delivery",
    "Neither, until cancellation or delivery", "Both, split evenly"], 1,
   "Conversion is a phone call. Delivery is goods and money — and a meaningful share of recovered orders stall a second time in between."),
 c("Why must cancellations stay with the original closer?",
   ["The recovery team has no cancellation metric", "Otherwise pooling doubtful orders becomes the route to a clean rate",
    "Because only the original closer can cancel", "To keep the pool small"], 1,
   "A cancelled lead usually reflects how it was confirmed at the front. That is information about the original closer's work."),
 c("For a follow-up member, the practical consequence of credit arriving only at delivery is:",
   ["Convert as many orders as possible, quickly", "Attach a delivery agent at conversion rather than leaving it for later",
    "Claim only high-value orders", "Avoid orders older than the threshold"], 1,
   "A converted order with nobody lined up to carry it is a conversion that can quietly stall again — and your credit stalls with it."),
],
"Your numbers — the dashboard and My Summary": [
 c("You switch the dashboard from Week to Month. Which card does NOT change?",
   ["Delivered", "Cancelled", "Agent Notified", "Total Orders"], 2,
   "In-flight cards ignore the timeframe and show the whole book. Only terminal cards are period-scoped."),
 c("Dividing an in-flight card by Total Orders gives you:",
   ["A useful stalled-order rate", "Nothing meaningful — an all-time figure over one period",
    "The conversion rate", "A figure only managers may see"], 1,
   "The result looks like a percentage and means nothing, which is precisely what makes it dangerous."),
 c("Your dashboard shows no Delivered Value Trend. This is:",
   ["A fault to report", "The role-based access model working — closers see activity, not money",
    "A sign your orders have no value recorded", "A timeframe problem"], 1,
   "Revenue is role-gated to directors, managers and administrators. Its absence is the design, not a bug."),
],
"Working a shift well — the closer's day": [
 c("You open your shift. The first thing you do is:",
   ["Dial the top of the list", "Set your filters — your orders, call-backs due, anything unmoved for three days",
    "Check the team dashboard", "Read the follow-up pool"], 1,
   "A closer who begins by scrolling begins by choosing which customers get no attention, without deciding to."),
 c("Among orders with no scheduled commitment, work:",
   ["Highest value first", "Newest first, while interest is fresh",
    "Oldest first", "Whichever branch is busiest"], 2,
   "The customer who has waited longest is the one most likely to have bought elsewhere — and closest to becoming a silent loss."),
 c("The highest-return habit in a closer's day is:",
   ["Making more calls per hour", "Writing one note after every conversation",
    "Checking the dashboard hourly", "Claiming pool orders early"], 1,
   "It costs fifteen seconds, makes the next callback land, and is the only thing that survives your absence, your leave and your promotion."),
],
"When it goes wrong — recovering from the common mistakes": [
 c("You created a duplicate order. You should:",
   ["Mark one Duplicate yourself", "Cancel one quietly",
    "Tell your manager which should stand — only they or the system can mark Duplicate", "Abandon the second"], 2,
   "An abandoned order still sits in a list and counts in the numbers. And closers cannot set Duplicate, by design."),
 c("A delivery failed because you mistyped one digit of the phone number. Recover by:",
   ["Cancelling and creating a new order", "Correcting the number and rescheduling",
    "Marking it Not Reachable", "Pooling it for follow-up"], 1,
   "A wrong digit is an administrative error. Cancelling for it converts your mistake into a lost sale."),
 c("You marked a customer Not Reachable after a single attempt. You should:",
   ["Leave it — the status is close enough", "Set it back and make the attempt",
    "Cancel it and let the sweep find it", "Add a note explaining the error"], 1,
   "Not Reachable tells everyone downstream to stop trying. Caught early, nothing is lost — the correction costs a minute."),
],
},
}


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    total = 0
    for mod_key, chapters in CHECKS.items():
        mod = data[mod_key]
        by_title = {l["title"]: l for l in mod["lessons"]}
        for title, checks in chapters.items():
            if title not in by_title:
                sys.exit("ABORT: chapter not found in %s: %s" % (mod_key, title))
            for i, ch in enumerate(checks):
                ch["sort"] = i
            if not CHECK_ONLY:
                by_title[title]["checks"] = checks
            total += len(checks)
        missing = [l["title"] for l in mod["lessons"] if l["title"] not in chapters]
        print("%-18s %d chapters covered%s" % (
            mod_key, len(chapters), "" if not missing else "  MISSING: %s" % missing))
    print("\n%d check questions across %d modules." % (total, len(CHECKS)))
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
