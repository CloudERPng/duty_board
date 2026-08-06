#!/usr/bin/env python3
"""Duty Board v3.59.6 HOTFIX — ‹ Chats actually goes back to Chats.

THE BUG (a collision between two of our own patches): the v3.59.4
mobile back button clears the open conversation and refreshes the
rail — but refresh_chat still carried the v3.57.6 auto-open ("nothing
open? open the first rail entry"), which for staff is the pinned Duty
Room. Back → rail flashes for one round-trip → auto-open fires → you
are bounced straight back into Duty Room. Stuck.

THE FIX: the auto-open is gated to desktop (>991px), where it is
correct — two panes, the centre must show something. On mobile the
rail IS a destination: entering 💬 lands on the conversation list, and
‹ Chats stays there. WhatsApp behaviour on both counts.

ALSO (per decision): 🤝 Clients leaves the mobile tab bar and moves
into the ⋯ More sheet, keeping its join-request badge — reachable but
out of the way while the Chat face earns its keep. Desktop Client
Rooms is untouched (approvals and the directory live there). Deleting
it outright later is a two-line follow-up once the team stops missing
it.

JS only: bench build --app duty_board && bench restart, then close and
reopen the phone app.

Anchored, all-or-nothing, idempotent. Requires v3.59.5.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '''\t\t\t\tif (!this._ch_open) {
\t\t\t\t\t// First rail entry: Duty Room for staff (pinned), the most
\t\t\t\t\t// recent room for consultants (who have no team entry).
\t\t\t\t\tconst first = (this._convos || [])[0];
\t\t\t\t\tif (first) this.open_convo(first.kind, String(first.id));
\t\t\t\t}'''

A1_NEW = '''\t\t\t\tif (!this._ch_open && !window.matchMedia("(max-width: 991px)").matches) {
\t\t\t\t\t// Desktop only: two panes, the centre must show something —
\t\t\t\t\t// Duty Room for staff (pinned), newest room for consultants.
\t\t\t\t\t// On mobile the rail IS the destination; auto-opening here is
\t\t\t\t\t// what bounced ‹ Chats straight back into the conversation.
\t\t\t\t\tconst first = (this._convos || [])[0];
\t\t\t\t\tif (first) this.open_convo(first.kind, String(first.id));
\t\t\t\t}'''

A2_OLD = '\t\t\t\t<a data-tab="clients"><span>🤝</span>${__("Clients")}<b class="duty-tab-badge duty-tab-clients" style="display:none"></b></a>\n'
A2_NEW = ''

A3_OLD = '\t\t\t{ icon: "⚠", label: __("Issues"), badge: "duty-tab-issues", go: () => this.set_mtab("issues") },'
A3_NEW = ('\t\t\t{ icon: "🤝", label: __("Client Rooms"), badge: "duty-tab-clients", go: () => this.set_mtab("clients") },\n'
          + A3_OLD)

A4_OLD = '\t\tconst primary = ["me", "chat", "clients", "projects", "library"];'
A4_NEW = '\t\tconst primary = ["me", "chat", "projects", "library"];'

EDITS = [
    ("refresh_chat: auto-open desktop-only", A1_OLD, A1_NEW),
    ("tab bar: 🤝 removed", A2_OLD, A2_NEW),
    ("More sheet: 🤝 Client Rooms with badge", A3_OLD, A3_NEW),
    ("primary tabs: clients out", A4_OLD, A4_NEW),
]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if 'primary = ["me", "chat", "projects", "library"]' in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.5"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.5 — apply apply_v3595_mobile_dash_fix.py first.")

    problems = [f"  [{files[JS].count(o)}] {label}" for label, o, _ in EDITS if files[JS].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = files[JS]
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(out)

    init = files[INIT].replace('"3.59.5"', '"3.59.6"')
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init)
    print("wrote __init__.py -> 3.59.6")


if __name__ == "__main__":
    main()
