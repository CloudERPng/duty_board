#!/usr/bin/env python3
"""Deepen the thin chapters in the ZhiftPOS operator modules.

Seven chapters sit below the 2,500-character floor. Each needs only 66 to 133
characters to pass, which would be a cheat — a sentence of padding clears the
audit and teaches nobody anything. Each gets a substantive paragraph instead.

The constraint that governs every addition: nothing here asserts product
behaviour the chapter does not already state. The additions are consequences,
habits and worked reasoning built on facts already established in that chapter
or an earlier one. Where I would have to guess at how the software behaves, I
say nothing.

That is the discipline the Closer track failed. It shipped four order statuses
the product does not have, because the author reasoned about what such a system
would plausibly do rather than what this one does.

Anchored and idempotent: each addition is keyed to an exact closing string, and
a chapter already carrying its marker is skipped.

Run from the app package directory:  python3 deepen_pos_chapters.py
"""

import io
import json
import re
import sys

DATA = "academy_pos_pro_data.json"
MARKER = "<!--deepened-->"
FLOOR = 2500
CHECK_ONLY = "--check" in sys.argv


# module -> chapter index -> paragraph appended at the end of the chapter
ADDITIONS = {
"shift_sale": {
 1: "<p><b>Two habits that make the open worth the two minutes.</b> Count the "
    "float into the drawer rather than out of it — money counted as it goes in "
    "is counted once, deliberately, instead of being reconstructed under time "
    "pressure when the first customer is already waiting. And open the shift "
    "before unlocking the door rather than after the first person is at the "
    "counter, because an opening count taken with somebody watching is the one "
    "most likely to be rounded.</p>"
    "<p><b>And the reason this matters beyond your own evening.</b> Your "
    "opening figure is the baseline for every variance the business will "
    "review. A branch whose opening counts are typed rather than counted "
    "produces a month of variances that mean nothing, and the manager reading "
    "them cannot tell a genuine shortage from a habit. The count is the thing "
    "that makes every later number real.</p>",
 2: "<p><b>Why the fixed-quantity rules exist rather than being an "
    "inconvenience.</b> Bonus items, bundle components and voucher lines all "
    "represent a decision made somewhere other than the counter — a promotion "
    "configured centrally, a bundle priced as a unit, a voucher whose value is "
    "its face value. Allowing the till to edit them individually would let the "
    "counter quietly undo a pricing decision the business made deliberately, "
    "one line at a time, with nothing to show it had happened.</p>"
    "<p><b>The practical consequence at a busy counter.</b> When a control is "
    "greyed out, it is not broken and it is not worth fighting. Remove the "
    "bundle by its main line and rebuild if the customer wants something "
    "different, and if a promoted price looks wrong, complete the sale and "
    "raise it afterwards rather than trying to correct it at the till while "
    "somebody waits.</p>",
},
"concessions_returns": {
 1: "<p><b>Writing an explanation somebody else can use.</b> The explanation "
    "field is read later by a person who was not at the counter and does not "
    "remember the customer. 'Damaged' tells them nothing they could not "
    "already see from the reason field; 'outer carton crushed in transit, two "
    "of six units affected, customer took both at 20% off' tells them what "
    "happened, how much was involved and whether it is likely to recur.</p>"
    "<p><b>And a note on picking the true reason.</b> Under queue pressure the "
    "temptation is to choose whichever reason sits nearest the top of the "
    "list. Doing so costs nothing today and quietly ruins the month-end "
    "figures, because the markdown report can only be as accurate as the "
    "reasons fed into it — a shop whose reasons are chosen for speed produces "
    "a report that cannot point at any cause at all.</p>",
},
"extended_counters": {
 0: "<p><b>What follows from naming the money.</b> Once each console is "
    "understood as a financial arrangement rather than a service, the controls "
    "stop looking like friction. A phone number is required on a lay-by "
    "because somebody has to be reachable when an instalment is missed. A "
    "staff purchase shows the employee's balance before anything is added "
    "because lending without disclosing the position is how a debt becomes a "
    "dispute. Each control exists because of the money, not because of the "
    "process.</p>"
    "<p><b>The common failure across all of them.</b> A side book — a "
    "notebook of lay-bys behind the counter, staff purchases recorded on a "
    "list, airtime sold from a private float. Every one of these begins as "
    "somebody being helpful when the system seemed slow, and every one ends "
    "with money the business cannot account for and a person who cannot be "
    "cleared. If it is a financial arrangement, it goes through the "
    "console.</p>",
 2: "<p><b>Why the weekly check is the whole discipline.</b> A lay-by is the "
    "only arrangement at the counter where doing nothing has a cost that "
    "compounds. Goods sit out of the sellable pool, a deposit sits owed, and "
    "the customer's memory of the arrangement fades along with your own. "
    "Checked weekly, an overdue instalment is a phone call. Checked "
    "quarterly, it is a negotiation about goods somebody no longer wants at a "
    "price that has since changed.</p>"
    "<p><b>What to say on the call.</b> Not a demand — a reminder of the "
    "amount, the date and what happens next, since the customer agreed to a "
    "printed schedule and most missed instalments are forgetfulness rather "
    "than difficulty. Where somebody genuinely cannot pay, that is worth "
    "knowing early too, because a lay-by terminated by agreement is far "
    "cheaper for both sides than one terminated by silence.</p>",
 4: "<p><b>The practical shape of the consumed-on-issue rule.</b> Because the "
    "code is spent the moment it is issued, an airtime sale has no safe "
    "reversal at the counter: there is nothing to take back and nothing to "
    "return to stock. Every other line on a receipt can be corrected by a "
    "return; this one cannot, and that asymmetry is worth holding in mind when "
    "a customer is uncertain which denomination they wanted.</p>"
    "<p><b>Two habits that follow.</b> Confirm the carrier and the amount out "
    "loud before completing payment, because the confirmation costs three "
    "seconds and the mistake costs the face value. And hand the slip over "
    "directly rather than leaving it on the counter — an airtime slip left "
    "beside a till is the same exposure as leaving the equivalent cash there, "
    "and it is far easier to pick up.</p>",
},
"voucher_programme": {
 1: "<p><b>What the two clocks mean in practice.</b> A sellable card sitting "
    "in a drawer for eight months has lost none of its validity, because its "
    "clock has not started — it starts when a customer buys it. A "
    "complimentary card, by contrast, begins ageing the moment it is "
    "activated, which is why activating a large batch far ahead of the "
    "campaign that will use it quietly shortens the life of every card in "
    "it.</p>"
    "<p><b>The handling consequence.</b> Sellable stock can be held "
    "comfortably; complimentary stock should be activated in the quantity a "
    "campaign will actually issue, and the rest left inert. That is not "
    "caution about theft alone — it is the difference between a hundred cards "
    "reaching customers with their full validity and a hundred cards arriving "
    "with two months already spent.</p>",
},
}


def main():
    data = json.load(io.open(DATA, encoding="utf-8"))
    touched = 0
    report = []
    for mod_key, chapters in ADDITIONS.items():
        if mod_key not in data:
            sys.exit("ABORT: module %r not present" % mod_key)
        lessons = data[mod_key]["lessons"]
        for idx, para in sorted(chapters.items()):
            if idx >= len(lessons):
                sys.exit("ABORT: %s has no chapter %d" % (mod_key, idx + 1))
            l = lessons[idx]
            if MARKER in l["html"]:
                report.append("  %-20s ch%-2d already deepened" % (mod_key, idx + 1))
                continue
            before = len(re.sub(r"<[^>]+>", " ", l["html"]))
            after = before + len(re.sub(r"<[^>]+>", " ", para))
            report.append("  %-20s ch%-2d %5d -> %5d  %s"
                          % (mod_key, idx + 1, before, after,
                             "ok" if after >= FLOOR else "STILL THIN"))
            if not CHECK_ONLY:
                l["html"] = l["html"].rstrip() + "\n" + MARKER + para
            touched += 1

    print("\n".join(report))
    print("\nchapters extended: %d" % touched)

    if CHECK_ONLY:
        print("--check given; nothing written.")
        return

    with io.open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    thin = [(k, i + 1, n) for k, m in data.items()
            for i, l in enumerate(m["lessons"])
            for n in [len(re.sub(r"<[^>]+>", " ", l["html"]))] if n < FLOOR]
    print("chapters still below the %d floor across the whole track: %d"
          % (FLOOR, len(thin)))
    for k, i, n in thin:
        print("   %-20s ch%-2d %d" % (k, i, n))


if __name__ == "__main__":
    main()
