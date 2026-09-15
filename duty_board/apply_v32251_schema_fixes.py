#!/usr/bin/env python3
"""Duty Board v3.225.1 — AUDIT CHUNK C: two Select values that do not exist.

Both found by comparing every Select value used in code against the options
actually defined on the field. Neither would ever have been reported as a bug
by a user in those words, because neither produces an error message.

1. training_team_overview filtered Duty Certificate by status "Issued".
   The field's options are Valid / Recertification Required / Revoked. There
   has never been an "Issued" status, so the filter matched nothing and the
   staff team-training overview showed every consultant as holding no
   certificates at all — silently, and consistently, so it looked like the
   truth rather than a fault. Now filtered the way the rest of the file does
   it, status != Revoked, which also correctly keeps a certificate that is
   valid but flagged for recertification.

2. radar_promote created a Duty Lead with source "Radar". That value is not in
   the field's options either, and Frappe validates Select on insert — so
   promoting a Sales Radar entry to a Lead raised a validation error and the
   promotion failed outright. Radar is the semantically correct source for a
   lead that came from the pre-pipeline, so it is added to the options rather
   than swapped for an approximation.

Deploy: apply -> bench migrate (one Select option) -> bench build --app
duty_board -> clear-cache -> restart. Anchored, idempotent. Requires v3.225.0.
"""

import io
import json as _json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
SALES = "duty_board/sales.py"
LEADDT = "duty_board/duty_board/doctype/duty_lead/duty_lead.json"
CHECK_ONLY = "--check" in sys.argv


CERT_OLD = '''\t\tfilters={"user": ["in", users], "status": "Issued"},'''
CERT_NEW = '''\t\tfilters={"user": ["in", users], "status": ["!=", "Revoked"]},'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, SALES):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    with io.open(os.path.join(root, LEADDT), encoding="utf-8") as f:
        lead = _json.load(f)
    src_field = next((x for x in lead["fields"] if x["fieldname"] == "source"), None)
    if not src_field:
        sys.exit("ABORT: Duty Lead has no source field.")
    already_opt = "Radar" in (src_field.get("options") or "").split("\n")

    if files[CR].count(CERT_OLD) == 0 and already_opt:
        print("Already applied. Nothing to do.")
        return
    if '"3.225.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.225.0.")

    n = files[CR].count(CERT_OLD)
    if n != 1:
        sys.exit("ABORT - certificate filter matched %d times, expected 1." % n)
    if '"source": "Radar",' not in files[SALES]:
        sys.exit("ABORT - radar_promote source assignment not found.")
    print("All 2 anchors matched exactly once.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    files[CR] = files[CR].replace(CERT_OLD, CERT_NEW, 1)
    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(files[CR])
    print("  client_room.py: team overview no longer filters on a status that does not exist")

    if not already_opt:
        opts = [o for o in (src_field.get("options") or "").split("\n")]
        # keep the leading blank, append Radar before Other if present
        if "Other" in opts:
            opts.insert(opts.index("Other"), "Radar")
        else:
            opts.append("Radar")
        src_field["options"] = "\n".join(opts)
        with io.open(os.path.join(root, LEADDT), "w", encoding="utf-8") as f:
            _json.dump(lead, f, indent=1)
            f.write("\n")
        print("  Duty Lead: source gains the Radar option")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.225.0"', '"3.225.1"'))
    print("wrote __init__.py -> 3.225.1")


if __name__ == "__main__":
    main()
