#!/usr/bin/env python3
"""Duty Board v3.59.7 — the Duty Room stops wasting the phone.

THE CAUSE (one line, found at 10802): the mobile media block still
carried `.duty-chat-list { max-height: 260px; }` — the team chat's old
life as a SIDE PANEL on the board face. The full-height override that
fixed this in the legacy mobile route was scoped to
`.duty-board[data-mtab="chat"]`, which v3.59.4 bypassed. So inside the
Chat face on a phone: a 260px message list, the composer floating
mid-screen, and the bottom 40% of the card dead white. Desktop never
hits that media block, which is why only mobile suffered.

THE FIX, scoped to the Chat face at ≤991px:
- The team card becomes a proper full-height flex column: the list
  grows (cap removed), the composer sits at the bottom where thumbs
  live.
- The card's internal "\U0001f4ac Duty Room" title — a duplicate of the
  "\u2039 Chats · Duty Room" header directly above it — is hidden. The
  \U0001f50d message search and the enable-notifications link survive,
  right-aligned in the freed row.

Client rooms and desktop are untouched.

JS only: bench build --app duty_board && bench restart, then close and
reopen the phone app.

Anchored, all-or-nothing, idempotent. Requires v3.59.6.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

A1_OLD = '\t\t\t\t.duty-ch-munit { background: var(--bg-light-gray, #eef2f1); color: #0f766e; border: 1px solid #d5e5e2; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 16px; white-space: nowrap; }'

A1_NEW = A1_OLD + '''
\t\t\t\t/* Team chat: full-height column. Kills the 260px side-panel cap
\t\t\t\t   that survived from the board-face era (see 10802). */
\t\t\t\t.duty-chatface .duty-ch-team,
\t\t\t\t.duty-chatface .duty-ch-team .duty-chat,
\t\t\t\t.duty-chatface .duty-ch-team .duty-chat-card { display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0; }
\t\t\t\t.duty-chatface .duty-ch-team .duty-chat-list { flex: 1 1 auto; min-height: 0; overflow-y: auto; max-height: none !important; }
\t\t\t\t/* The card's own title duplicates the \u2039 Chats header one line up;
\t\t\t\t   \U0001f50d search and enable-notifications keep the row, right-aligned. */
\t\t\t\t.duty-chatface .duty-ch-team .duty-chat-head > span:first-child { display: none; }
\t\t\t\t.duty-chatface .duty-ch-team .duty-chat-head { justify-content: flex-end; padding: 2px 4px; }'''

EDITS = [("mobile chatface: team card full height + dedup header", A1_OLD, A1_NEW)]


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "Kills the 260px side-panel cap" in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.6"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.6 — apply apply_v3596_back_fix.py first.")

    problems = [f"  [{files[JS].count(o)}] {label}" for label, o, _ in EDITS if files[JS].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("Anchor matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = files[JS]
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(out)

    init = files[INIT].replace('"3.59.6"', '"3.59.7"')
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init)
    print("wrote __init__.py -> 3.59.7")


if __name__ == "__main__":
    main()
