#!/usr/bin/env python3
"""Closer track — deepen the remaining Orders & Pipeline chapters.

The lifecycle chapters were corrected in the previous pass. The five that
remain are accurate but compressed — dense reference summaries rather than
taught lessons, running 1,052 to 1,969 characters against a 2,700-3,300
standard.

Nothing here invents product surface. Every fact was already asserted in the
existing text; what is added is the reasoning behind each rule, what it costs
when ignored, and a closing sense of what good practice looks like.

One correction rides along: chapter 7's tip cited an order sitting "in
Processing for four days". Processing is retired, so the example now uses a
status that exists.

Run from the app package directory:  python3 deepen_closer_m1.py
Then:  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons
"""

import io
import json
import re
import sys

DATA = "academy_closer_data.json"
CHECK_ONLY = "--check" in sys.argv


CHAPTERS = {
"The Orders workspace": ("""<p>The Orders page is where a closer lives. Everything else in ZhiftCRM is somewhere you visit; this is the room you work in, and how quickly you can bend it into a worklist is most of the difference between a closer who handles forty orders a day and one who handles fifteen.</p>

<p>Open it from <b>Orders</b> in the left sidebar. What loads is a table of every order you have access to, and that phrase is doing real work: a closer sees only their assigned orders, while managers and directors see every order across the team. This is not a permissions detail to skim. It means the number at the top of your screen is <i>your</i> book, not the company's, and a manager comparing their view to yours is looking at a different list. When someone asks how many orders are open, the honest answer begins with "for whom?"</p>

<p><b>Reading the columns.</b> Left to right: Order ID, Customer Name, Phone, Status as a colour-coded badge, Channel, Amount, Agent, and Created Date. Column widths are adjustable — drag the borders when something truncates, because a clipped address or half-shown name is how the wrong order gets worked.</p>

<p>Two columns deserve more attention than they usually get. <b>Channel</b> records where the lead came from — Phone, WhatsApp, Instagram, Facebook, Website — and it is the foundation of every marketing report the business runs. <b>Agent</b> is the assigned closer, and it answers the only question that matters when an order stalls: whose problem is this right now?</p>

<p><b>Search accepts almost anything.</b> A customer name, whole or partial. A phone fragment — typing <code>0551</code> matches any number containing those digits, which is how you find the customer who gave you their number over a bad line and you only caught the middle. An order ID, to jump straight there. A city name. The list filters as you type; there is no Enter to press.</p>

<p><b>But filters are where the speed is.</b> The status dropdown narrows to a single stage. Advanced Filters opens the full panel: channel, assigned agent, digital marketer, country, brand, category, branch, and a date range against your chosen date type.</p>

<p>The habit worth building is this: stop scrolling. Scrolling works on an order book of a few dozen. On a book of hundreds of thousands it is not slow, it is useless — you will never reach the bottom, so the orders at the bottom never get worked, and nobody notices because nobody scrolled that far. A closer who begins each session by setting <i>my orders, Call Back, today</i> has turned an unreadable table into a ten-minute worklist. A closer who begins by scrolling has begun by choosing which customers to abandon, without meaning to and without knowing which ones.</p>

<blockquote>IMPLEMENTATION TIP: By the end of your first week you should have three or four filter combinations you reach for without thinking — your call-backs for today, your orders awaiting agent acceptance, anything of yours that has not moved in three days. Those are not reports you run. They are the three doors you walk through every morning.</blockquote>""", 8),

"Creating an order": ("""<p>Click <b>New Order</b> at the top-right of the Orders page and the create dialog opens. The form is short. The discipline inside it is what keeps the customer database worth having, and the cost of skipping that discipline is paid months later by somebody who is not you.</p>

<p><b>Customer name first — and search before you type.</b> The field live-searches existing customers, and selecting a match auto-fills phone, email and address from the profile. This is the most consequential habit in the form. A duplicate customer record does not announce itself; it quietly splits one person's history in two, so the repeat buyer who has ordered eleven times looks like two strangers who ordered six and five. Every judgement downstream then goes wrong: their value to the business, their return rate, and whether the closer picking up their next call knows they are talking to a regular.</p>

<p>So when a similar name appears, verify by phone before creating anew. Names collide constantly — in a book of any size you will have several customers sharing one — and the phone number is the thing that does not.</p>

<p><b>Phone is required, and it drives everything.</b> Enter it with the country code; the system validates the format. Consider what depends on this one field: the call that confirms the order, the delivery person's call at the door, and the recovery call if delivery fails. A digit wrong here does not produce an error message. It produces an order that travels all the way to a customer's street and comes back, having consumed picking, packing, dispatch and a rider's afternoon. Read it back to the customer. Four seconds, and the cheapest four seconds in the process.</p>

<p><b>The duplicate banner.</b> When you leave the phone field, the system checks for a prior order on the same number inside the configured detection window. A match raises an amber banner showing that order's ID, date and items.</p>

<p>Note what it does and does not do: <b>it informs, it does not block</b>. That is deliberate. A customer ordering the same product again three weeks later is a good outcome, and software that refused it would be wrong. So the decision is yours, and it is a real one. For a legitimate repeat purchase, tick <b>Proceed anyway</b>. If it is the same order arriving twice — the customer called again because nobody called them back, or two closers picked up one enquiry — close the dialog and work the existing order. Creating the second does not just clutter the list; it puts two closers on one customer, and the customer notices.</p>

<p>Numbers are normalised on their last ten digits, so <code>08012345678</code> and <code>+2348012345678</code> are recognised as the same customer. You need not guess which format a colleague used.</p>

<p><b>Then the rest.</b> Email is optional, but a customer with no email cannot be reached by any automated journey — so an empty email field is a quiet decision to reach that person by phone only, for the life of the relationship.</p>

<p><b>Lead Channel is set once, at creation</b>, and it feeds marketing attribution, which eventually feeds decisions about where money is spent. A channel guessed rather than known does not stay a small inaccuracy; it becomes budget moved toward a source that was not actually performing. If you do not know, ask — "how did you hear about us?" costs one line of the conversation.</p>

<p>Complete the items, the delivery address, and any notes. The address deserves the same read-back treatment as the phone number, and for the same reason.</p>

<blockquote>CONSULTANT NOTE: The duplicate check on manually created orders runs only if the administrator has enabled "Run on Manual Orders" under Duplicate Order Detection in settings. If closers report never seeing the banner, check that setting before concluding the feature is broken.</blockquote>""", 8),

"Inside an order — the details drawer": ("""<p>Click any row and the Order Details Drawer slides in from the right. The list stays live behind it, so you can move between orders without losing your place — which matters more than it sounds, because the alternative is re-applying your filters twenty times a day.</p>

<p><b>Read it top to bottom.</b> The header carries the order ID, a colour-coded status badge and the creation date: green is good news, yellow is in motion, red is trouble. Below that, customer information, where the name and phone are both clickable — the name opens the profile, the phone places the call.</p>

<p>Then the order items: each line with unit price, quantity and line total, with the order total beneath. Then the delivery address. Then agent assignment — who owns it now, with reassignment available to managers. Then notes, in chronological order, each attributed and timestamped.</p>

<p><b>At the bottom sits the section that settles arguments.</b> The Status Timeline records every status change the order has ever had, newest first, each with its timestamp and the name of the person who made it. This is the complete audit trail, and learning to read it is the single most useful drawer skill.</p>

<p>Consider what it lets you say. A customer complains that delivery took a week. Without the timeline you have an apology and a guess. With it you have a fact: the order was Assigned on Monday, Agent Notified on Monday afternoon, and sat there until Thursday because no agent had accepted it. That is not a slow delivery — it is three days lost at a specific handover, owned by a specific person. The complaint becomes a fixable problem instead of a mood.</p>

<p>It also protects you. When a manager asks why an order stalled, the timeline shows whether it stalled in your hands or somebody else's, with times. A closer who checks the timeline before responding to any dispute is never guessing about their own work.</p>

<p><b>Action buttons adapt to status and role.</b> Update Status offers only the moves that are valid from where the order currently is — which is why you will sometimes look for a status and not find it. That is the system enforcing the lifecycle, not a fault. Alongside it: Assign or Reassign, Add Note, Edit Items, and Print or Export.</p>

<blockquote>IMPLEMENTATION TIP: Make the timeline your first stop on any dispute — before calling anyone, know where the bottleneck actually was. It turns "the delivery was slow" into "the order sat at Agent Notified for three days, and here is whose queue that was." One is a complaint. The other is a management conversation with evidence attached.</blockquote>

<blockquote>WATCH-OUT: Because the timeline names whoever made each change, it is also a record of your own status discipline. A pattern of orders moved to Not Reachable within minutes of being assigned, or Cancelled without a note, reads exactly as it looks. Assume every status you set will one day be read back to you with a timestamp beside it.</blockquote>""", 8),

"Customers & quick actions": ("""<p>The Customers directory is the other half of a closer's toolkit. The Orders page is organised around transactions; this is organised around people, with every profile carrying full order history, notes and contact details. When you are about to speak to somebody, this is the page that tells you who you are speaking to.</p>

<p>Open any profile and the Quick Actions bar across the top does your most common work in one click.</p>

<p><b>New Order</b> opens the create dialog with name, phone, email and address pre-filled from the profile. Always create repeat orders this way rather than starting fresh on the Orders page. It is not merely faster — it eliminates the duplicate-customer risk entirely, because you are working from an existing record rather than typing a name that might or might not match one. Every duplicate customer in the database was created by somebody in a hurry who started from the wrong page.</p>

<p><b>WhatsApp</b> opens a conversation with the number pre-filled — WhatsApp Web on desktop, the app on mobile. It needs a valid number with country code; without one the button disables, which is itself a useful signal that the number on file will not work for anything else either.</p>

<p><b>Phone</b> is click-to-call where telephony is integrated, and otherwise copies the number for your dialler.</p>

<p><b>Add Note</b> writes a timestamped, attributed note straight onto the record and the timeline.</p>

<p><b>Build the note habit, and treat it as part of the call rather than admin afterwards.</b> One note after every customer conversation: what was discussed, what was promised, and when to act next. It takes fifteen seconds and it is the difference between a customer relationship the company owns and one that lives only in your head.</p>

<p>The reason that matters is turnover and absence. When you are on leave, the colleague picking up your customer reads your notes or improvises. When a customer says "I already explained this to someone", the note is what makes that true rather than embarrassing. And when a dispute arrives three months later about what was promised on price or delivery date, the note written at the time carries weight that a recollection does not.</p>

<p><b>What good looks like.</b> Open the profile before the call, not after. Read the last two notes and the recent order history — thirty seconds — so you begin the conversation knowing whether this is a first-time buyer or somebody on their ninth order. Customers notice being known, and it converts.</p>

<blockquote>IMPLEMENTATION TIP: Write the note as if the next person to read it has never spoken to this customer, because usually they have not. "Called, no answer" helps nobody. "Called 2pm, no answer; second attempt today; asked yesterday for delivery after 5pm because he works" tells the next closer exactly what to do and when.</blockquote>""", 8),

"Abandoned carts — the almost-customers": ("""<p>An abandoned cart is created when a visitor opens one of your lead forms, starts filling it in, and leaves without submitting. The system keeps whatever they did enter — and that partial data is recoverable revenue sitting in a list.</p>

<p><b>The session lifecycle.</b> A session begins when the form loads. The moment the visitor interacts with it, engagement is detected. As they type, each completed field is captured. If they leave without submitting, the session is classified abandoned and the partial record is saved. If they later come back and complete the form, the abandonment is excluded — so you never chase somebody who has already bought.</p>

<p><b>Why people abandon.</b> The recurring culprits are distraction, sticker shock at the total, second thoughts, form friction, and technical failure. Notice what none of those is: a decision not to buy. They all mean "not yet" rather than "no", and that is the entire reason recovery works.</p>

<p><b>Why it is worth your time.</b> The cost of acquiring this customer has already been paid. The advert was created, the money was spent, the click happened, and the interest was proven by the act of starting the form. A recovery call is therefore the cheapest sales conversation available to you — you are not finding a customer, you are finishing one. It is consistently among the highest-return activities a sales team performs, and it is usually the one nobody has time for.</p>

<p><b>Find them under Campaigns, then Abandoned Carts.</b> Each row is one abandoned session, carrying whatever contact details were captured — a dash means the visitor never reached that field — the lead form they came through, the products selected, the cart value, when it was abandoned, the session duration, and a Recovery Status of Not Contacted, Contacted, Recovered or Lost.</p>

<p><b>Prioritise by cart value and phone availability.</b> A captured phone number is the difference between a recovery call and a lost ghost, so a high-value cart with no phone is worth less of your time than a modest one you can actually ring. Session duration is the quiet third signal: somebody who spent four minutes on the form was seriously considering it, and a long session with a captured number is the strongest row on the page.</p>

<p><b>How to open the call matters.</b> You are contacting somebody who did not choose to be contacted, about an order they did not place. Lead with the fact rather than a pitch — you noticed they had started an order and wanted to check whether anything went wrong. Half the time something did: the form broke, the total surprised them, the delivery estimate did not work. Each of those is answerable, and answering it is the recovery.</p>

<blockquote>WATCH-OUT: Privacy is part of the craft. The system captures only what the visitor actively typed — no fingerprinting, no cross-site tracking, no payment data. When you follow up, be straightforward about how you came to have their details and make opting out easy. A recovery call that feels like surveillance costs you the customer you were trying to recover, and reputational damage does not stay with one order.</blockquote>""", 8),
}


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    mod = data["orders_pipeline"]
    hit = 0
    for l in mod["lessons"]:
        new = CHAPTERS.get(l["title"])
        if not new:
            continue
        html, est = new
        before = len(re.sub(r"<[^>]+>", " ", l["html"]))
        after = len(re.sub(r"<[^>]+>", " ", html))
        print("  %-46s %5d -> %5d" % (l["title"][:46], before, after))
        if not CHECK_ONLY:
            l["html"] = html
            l["est"] = est
        hit += 1
    if hit != len(CHAPTERS):
        sys.exit("ABORT: matched %d of %d chapters — titles may have changed." % (hit, len(CHAPTERS)))
    if CHECK_ONLY:
        print("\n--check given; nothing written.")
        return
    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\nWritten. Push with:")
    print("  bench --site xlevel.clouderp.one execute duty_board.academy_repair.push_closer_lessons")


if __name__ == "__main__":
    main()
