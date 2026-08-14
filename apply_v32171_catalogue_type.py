#!/usr/bin/env python3
"""Duty Board v3.217.1 — CATALOGUE TYPE SIZES.

The catalogue was set at the same sizes as the dense operational lists it sits
beside, which is wrong for what it is. A list of orders is scanned; a catalogue
is read, and read by somebody deciding whether to spend money. Everything in
the card grid and the track detail moves up a step or two.

  card title      17   -> 19.5   detail title    24  -> 28
  card meta     11.5   -> 13     section body  13.5  -> 15
  card blurb    12.5   -> 14     section head    11  -> 11.5
  card more       12   -> 13     note          12.5  -> 13.5
  badge         11.5   -> 12.5   list item    inherit -> 14.5

Line height rises with it, and the card blurb clamps at three lines rather than
four so cards stay a comparable height at the larger size.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.217.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

EDITS = [
    ("\t.cattag { margin-left: auto; font-size: 11.5px; font-weight: 700; border-radius: 99px; padding: 3px 10px; }",
     "\t.cattag { margin-left: auto; font-size: 12.5px; font-weight: 700; border-radius: 99px; padding: 4px 12px; }",
     "badge"),

    ("\t.catasg { font-size: 12.5px; font-weight: 700; color: var(--brand-700); cursor: pointer; }",
     "\t.catasg { font-size: 14px; font-weight: 700; color: var(--brand-700); cursor: pointer; }",
     "assign link"),

    ("\t.catdesc { font-size: 12.5px; color: #4A5A55; line-height: 1.6; margin-top: 5px; }",
     "\t.catdesc { font-size: 14px; color: #4A5A55; line-height: 1.65; margin-top: 6px; }",
     "row description"),

    ("\t.catnote { font-size: 12.5px; margin-top: 8px; background: #FFF7E6; border: 1px solid #F3E0B5;",
     "\t.catnote { font-size: 13.5px; line-height: 1.6; margin-top: 10px; background: #FFF7E6; border: 1px solid #F3E0B5;",
     "note"),

    ("\t.catreq { display: inline-block; margin-top: 8px; font-size: 12.5px; font-weight: 700;",
     "\t.catreq { display: inline-block; margin-top: 8px; font-size: 14px; font-weight: 700;",
     "request link"),

    ("\t.catname { font-family: Fraunces, Georgia, serif; font-size: 17px; line-height: 1.25; font-weight: 600; }",
     "\t.catname { font-family: Fraunces, Georgia, serif; font-size: 19.5px; line-height: 1.28; font-weight: 600; }",
     "card title"),

    ("\t.catmeta { font-size: 11.5px; color: #6B7C77; margin-top: 4px; }",
     "\t.catmeta { font-size: 13px; color: #6B7C77; margin-top: 6px; }",
     "card meta"),

    ("\t.catblurb { font-size: 12.5px; line-height: 1.55; color: #4A5A55; margin-top: 9px;\n\t\tdisplay: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }",
     "\t.catblurb { font-size: 14px; line-height: 1.6; color: #4A5A55; margin-top: 11px;\n\t\tdisplay: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }",
     "card blurb"),

    ("\t.catpend { font-size: 11.5px; background: #FFF7E6; border-radius: 7px; padding: 5px 9px; margin-top: 9px; color: #7A5312; }",
     "\t.catpend { font-size: 12.5px; line-height: 1.5; background: #FFF7E6; border-radius: 7px; padding: 7px 11px; margin-top: 11px; color: #7A5312; }",
     "pending note"),

    ("\t.catmore { font-size: 12px; font-weight: 700; color: var(--brand-700); margin-top: auto; padding-top: 11px; }",
     "\t.catmore { font-size: 13px; font-weight: 700; color: var(--brand-700); margin-top: auto; padding-top: 13px; }",
     "details link"),

    ("\t.catback { cursor: pointer; font-size: 12.5px; color: var(--brand-700); font-weight: 700; }",
     "\t.catback { cursor: pointer; font-size: 14px; color: var(--brand-700); font-weight: 700; }",
     "back link"),

    ("\t.catdtitle { font-family: Fraunces, Georgia, serif; font-size: 24px; font-weight: 600; margin: 2px 0 2px; }",
     "\t.catdtitle { font-family: Fraunces, Georgia, serif; font-size: 28px; line-height: 1.2; font-weight: 600; margin: 4px 0 2px; letter-spacing: -.2px; }",
     "detail title"),

    ("\t.catsec { margin-top: 16px; font-size: 13.5px; line-height: 1.6; }",
     "\t.catsec { margin-top: 20px; font-size: 15px; line-height: 1.65; }",
     "detail section"),

    ("\t.catsec b { display: block; font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase;",
     "\t.catsec b { display: block; font-size: 11.5px; letter-spacing: 1.5px; text-transform: uppercase;",
     "section heading"),

    ("\t.catlist li { margin: 3px 0; }",
     "\t.catlist li { margin: 5px 0; font-size: 14.5px; }",
     "course list"),

    ("\t.catcard { border: 1px solid #E4EAE8; border-radius: 14px; padding: 15px 16px; background: #fff;",
     "\t.catcard { border: 1px solid #E4EAE8; border-radius: 14px; padding: 18px 19px; background: #fff;",
     "card padding"),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "font-size: 19.5px" in files[PORTAL]:
        print("Already applied. Nothing to do.")
        return
    if '"3.217.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.217.0.")

    problems = []
    for old, _new, label in EDITS:
        n = files[PORTAL].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(EDITS))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for old, new, _label in EDITS:
        files[PORTAL] = files[PORTAL].replace(old, new, 1)
    with io.open(os.path.join(root, PORTAL), "w", encoding="utf-8") as f:
        f.write(files[PORTAL])
    print("  portal.html: catalogue type sizes raised")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.217.0"', '"3.217.1"'))
    print("wrote __init__.py -> 3.217.1")


if __name__ == "__main__":
    main()
