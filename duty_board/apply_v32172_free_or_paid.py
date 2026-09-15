#!/usr/bin/env python3
"""Duty Board v3.217.2 - FREE OR PAID, SAID PLAINLY.

The card badge was doing two jobs and therefore neither. A paid track you had
already bought read "7 seats left" with the price nowhere on the card, and a
free one read "Included", which describes an entitlement rather than a cost. An
administrator scanning the grid could not answer the first question anybody
asks: does this cost money?

The two are now separate.

  A price chip, top right, always present and always commercial:
      Free                 -  or  -    N45,000 / seat

  A state line under the meta, always present and always about entitlement:
      Included with your subscription
      7 of 10 seats available
      No seats purchased yet
      Request for 5 seats received
      Comes with ZhiftCRM - not in your subscription

So the chip answers "what does it cost" and the line answers "where do I
stand", at a glance, on every card. The detail view carries the same chip
beneath its title.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.217.1. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


BADGE_OLD = '\tconst badge = (r) =>\n\t\tr.included ? `<span class="cattag inc">Included</span>`\n\t\t: r.seats_left ? `<span class="cattag own">${r.seats_left} seat${r.seats_left === 1 ? "" : "s"} left</span>`\n\t\t: r.access === "Paid" ? `<span class="cattag paid">${money(r.seat_price)} / seat</span>`\n\t\t: `<span class="cattag out">Not subscribed</span>`;'

BADGE_NEW = '\tconst priceTag = (r) =>\n\t\tr.access === "Paid"\n\t\t\t? `<span class="cattag paid">${money(r.seat_price)} / seat</span>`\n\t\t\t: `<span class="cattag free">Free</span>`;\n\tconst stateLine = (r) =>\n\t\tr.included ? `<span class="catstate ok">\\u2713 Included with your subscription</span>`\n\t\t: r.pending ? `<span class="catstate wait">Request for ${r.pending_seats} seat${r.pending_seats === 1 ? "" : "s"} received</span>`\n\t\t: r.seats ? `<span class="catstate ok">\\u2713 ${r.seats_left} of ${r.seats} seats available</span>`\n\t\t: r.access === "Paid" ? `<span class="catstate buy">No seats purchased yet</span>`\n\t\t: `<span class="catstate out">Comes with ${esc(r.product || "another product")} \\u2014 not in your subscription</span>`;'

TOP_OLD = '\t\t\t\t\t\t<div class="catcardtop">${badge(r)}</div>'

TOP_NEW = '\t\t\t\t\t\t<div class="catcardtop">${priceTag(r)}</div>'

META_OLD = '\t\t\t\t\t\t\t<div class="catmeta">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"}${r.minutes ? " · " + hrs(r.minutes) : ""}</div>'

META_NEW = '\t\t\t\t\t\t\t<div class="catmeta">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"}${r.minutes ? " · " + hrs(r.minutes) : ""}</div>\n\t\t\t\t\t\t\t<div class="catstateline">${stateLine(r)}</div>'

PEND_OLD = '\t\t\t\t\t\t\t${r.pending ? `<div class="catpend">Request for ${r.pending_seats} seat(s) received</div>` : ""}\n'

PEND_NEW = ''

DET_OLD = '\t\t\t<div class="catmeta" style="margin-bottom:14px">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"} · about ${hrs(r.minutes)} of study</div>'

DET_NEW = '\t\t\t<div class="catmeta">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"} · about ${hrs(r.minutes)} of study</div>\n\t\t\t<div class="catdprice">${r.access === "Paid" ? `<span class="cattag paid">${money(r.seat_price)} per seat</span>` : `<span class="cattag free">Free</span>`}</div>'

CSS_OLD = '\t.cattag.out { background: #F1F4F3; color: #6B7C77; }'

CSS_NEW = '\t.cattag.out { background: #F1F4F3; color: #6B7C77; }\n\t.cattag.free { background: #E4F3EC; color: #0C6B4F; }\n\t.catstateline { margin-top: 8px; }\n\t.catstate { font-size: 12.5px; font-weight: 600; line-height: 1.45; }\n\t.catstate.ok { color: #0C6B4F; }\n\t.catstate.wait { color: #8A5A0B; }\n\t.catstate.buy { color: #6B7C77; font-weight: 500; }\n\t.catstate.out { color: #6B7C77; font-weight: 500; }\n\t.catdprice { margin: 10px 0 4px; }'



def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "const priceTag" in files[PORTAL]:
        print("Already applied. Nothing to do.")
        return
    if '"3.217.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.217.1.")

    edits = [
        (BADGE_OLD, BADGE_NEW, "price chip + state line"),
        (TOP_OLD, TOP_NEW, "card chip"),
        (META_OLD, META_NEW, "card state line"),
        (PEND_OLD, PEND_NEW, "retire the pending block"),
        (DET_OLD, DET_NEW, "detail chip"),
        (CSS_OLD, CSS_NEW, "css"),
    ]
    problems = []
    for old, _new, label in edits:
        n = files[PORTAL].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for old, new, _label in edits:
        files[PORTAL] = files[PORTAL].replace(old, new, 1)
    with io.open(os.path.join(root, PORTAL), "w", encoding="utf-8") as f:
        f.write(files[PORTAL])
    print("  portal.html: price chip and entitlement state separated")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.217.1"', '"3.217.2"'))
    print("wrote __init__.py -> 3.217.2")


if __name__ == "__main__":
    main()
