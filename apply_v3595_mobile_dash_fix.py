#!/usr/bin/env python3
"""Duty Board v3.59.5 HOTFIX — the mobile dashboard un-wrecked.

WHAT THE VIDEO SHOWED: the dashboard inside a "\U0001f464 My Dashboard \u2715"
panel, rendered wider than the phone and stacked twice.

THE CHAIN THAT CAUSED IT:
1. v3.57.9 made page load fire show_face("board") so the desktop day
   tabs paint on first load — but ran it UNCONDITIONALLY. On mobile it
   fires AFTER the tab bar has already restored the saved tab, hiding
   the dashboard host mid-fetch.
2. refresh_me still carries a v2.59.3-era emergency fallback: measure
   the rendered node, and if invisible, "escalate" — build a fixed
   overlay panel, repoint this.$me at it, and render the dashboard a
   second time. With (1) hiding the host on every mobile launch, the
   fallback fired on every mobile launch: overlay presentation (no
   mobile styling -> the width blowout), a second dashboard copy, and
   the async gamify/radar/rooms widgets landing in whichever host
   this.$me pointed to at that moment (the duplicate stack).

THE FIX:
- The load-time show_face("board") is scoped to desktop (>991px),
  where the day tabs it exists for actually live. Mobile returns to
  tab-bar restoration, which worked.
- The escalation block is deleted outright. A fallback that responds
  to "host hidden" by double-rendering into an unstyled panel does not
  fix anything — it hides face-state bugs behind a second copy of the
  UI. If the host is hidden, the correct behaviour is: the render is
  there when the face shows. The diagnostic console.log lines stay;
  they are how this was found.

JS only: bench build --app duty_board && bench restart, then on the
phone close and reopen the installed app (or hard-refresh Safari/Chrome).

Anchored, all-or-nothing, idempotent. Requires v3.59.4.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '\tif (!board._is_consultant) board.show_face("board");'
A1_NEW = '''\t// Desktop only: this exists so the day tabs paint on first load.
\t// On mobile it fired AFTER the tab bar restored the saved tab, hiding
\t// the dashboard host mid-fetch and triggering the old overlay fallback.
\tif (!board._is_consultant && !window.matchMedia("(max-width: 991px)").matches) {
\t\tboard.show_face("board");
\t}'''

A2_OLD = '''\t\t\t\tif (rect.height < 60 || !node.offsetParent) {
\t\t\t\t\tconsole.warn("[duty-me] node invisible — escalating to overlay");
\t\t\t\t\t$(".duty-me-overlay").remove();
\t\t\t\t\tconst $ov = $(`
\t\t\t\t\t\t<div class="duty-me-overlay">
\t\t\t\t\t\t\t<div class="duty-me-ovbar"><b>👤 ${__("My Dashboard")}</b><a class="duty-me-ovclose">✕</a></div>
\t\t\t\t\t\t\t<div class="duty-me-ovbody"></div>
\t\t\t\t\t\t</div>`).appendTo(document.body);
\t\t\t\t\t$ov.find(".duty-me-ovclose").on("click", () => $ov.remove());
\t\t\t\t\tthis.$me = $ov.find(".duty-me-ovbody");
\t\t\t\t\tthis.render_my_dashboard(j.message);
\t\t\t\t\tconsole.log("[duty-me] overlay tiles:", this.$me.find(".duty-mtile").length);
\t\t\t\t}'''

A2_NEW = '''\t\t\t\t// v2.59.3 "escalate to overlay" fallback removed (v3.59.5): it
\t\t\t\t// answered a hidden host by double-rendering the dashboard into an
\t\t\t\t// unstyled fixed panel, masking face-state bugs. If the host is
\t\t\t\t// hidden, the render simply waits for the face to show.
\t\t\t\t$(".duty-me-overlay").remove();'''

EDITS = [
    ("page load: board face is desktop-only", A1_OLD, A1_NEW),
    ("refresh_me: overlay fallback retired", A2_OLD, A2_NEW),
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

    if 'fallback removed (v3.59.5)' in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.4"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.4 — apply apply_v3594_mobile_chat.py first.")

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

    init = files[INIT].replace('"3.59.4"', '"3.59.5"')
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init)
    print("wrote __init__.py -> 3.59.5")


if __name__ == "__main__":
    main()
