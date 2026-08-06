#!/usr/bin/env python3
"""Duty Board v3.59.4 — the phone gets the same Chat as the web.

Until now the mobile \U0001f4ac tab showed the pre-v3.57 world: the team chat
panel alone — no rail, no client rooms, no DMs. Four changes make the
phone behave like the web Chat face, WhatsApp-shaped:

1. ROUTE. The mobile \U0001f4ac tab now opens the Chat FACE (set_mtab gains a
   chat branch) instead of the board's legacy chat panel.

2. BACK. Opening a conversation slides to a full-screen view with a
   sticky header — "\u2039 Chats · {name}" — and the back link returns to
   the rail (refreshing it so read badges are honest). Previously the
   conversation view was a one-way door.

3. CHAT/TASKS TABS. The room's existing \U0001f4ac Chat / \U0001f4cb Tasks pills
   (built in the Clients-face mobile work, hidden inside the Chat face
   by a desktop-era rule) come back on mobile: the !important hide is
   now scoped to \u2265992px, where the task column shows instead. The
   rt-tasks toggle rules were global all along, so they just work.

4. BREAKPOINT BUG. is_mobile() is \u2264767px but the mobile layout kicks
   in at \u2264991px — tablets in between got the mobile CSS with no way to
   open a conversation. The convo-open logic now uses the same 991px
   line as the layout.

JS only: bench build --app duty_board && bench restart.
Anchored, all-or-nothing, idempotent. Requires v3.59.3.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. mobile 💬 tab routes to the Chat face --------------------------------

A1_OLD = '\t\t} else if (tab === "clients") {\n\t\t\tthis.show_face("clients");\n\t\t} else if (tab === "me") {'
A1_NEW = '''\t\t} else if (tab === "chat") {
\t\t\tthis.show_face("chat");
\t\t} else if (tab === "clients") {
\t\t\tthis.show_face("clients");
\t\t} else if (tab === "me") {'''

# --- 2. conversation open: back header + correct breakpoint ------------------

A2_OLD = '\t\tif (this.is_mobile()) $c.addClass("ch-convo-open");'
A2_NEW = '''\t\tif (window.matchMedia("(max-width: 991px)").matches) {
\t\t\t// Full-screen conversation with a way back — WhatsApp shape.
\t\t\tconst esc = frappe.utils.escape_html;
\t\t\tconst conv = (this._convos || []).find(
\t\t\t\t(c) => c.kind === kind && String(c.id) === String(id)
\t\t\t);
\t\t\tconst title =
\t\t\t\t(conv && conv.title) ||
\t\t\t\t(kind === "team" ? __("Duty Room") : kind === "dm" ? this.name_map[id] || id : id);
\t\t\tconst $center = $c.find(".duty-ch-center");
\t\t\t$center.find(".duty-ch-mhead").remove();
\t\t\t$center.prepend(`
\t\t\t\t<div class="duty-ch-mhead">
\t\t\t\t\t<a class="duty-ch-mback">\u2039 ${__("Chats")}</a>
\t\t\t\t\t<b>${esc(title)}</b>
\t\t\t\t\t${conv && conv.subtitle && kind === "room" ? `<span class="duty-ch-munit">${esc(conv.subtitle)}</span>` : ""}
\t\t\t\t</div>`);
\t\t\t$center.find(".duty-ch-mback").on("click", () => {
\t\t\t\t$c.removeClass("ch-convo-open");
\t\t\t\tthis._ch_open = null;
\t\t\t\tthis.refresh_chat(true);
\t\t\t});
\t\t\t$c.addClass("ch-convo-open");
\t\t}'''

# --- 3. scope the mtabs hide to desktop; keep back hidden everywhere ---------

A3_OLD = '\t\t\t.duty-ch-room .duty-cr-back, .duty-ch-room .duty-cr-mtabs { display: none !important; }'
A3_NEW = '''\t\t\t.duty-ch-room .duty-cr-back { display: none !important; }
\t\t\t@media (min-width: 992px) {
\t\t\t\t/* Desktop shows the task column; the \U0001f4ac/\U0001f4cb pills are mobile's. */
\t\t\t\t.duty-ch-room .duty-cr-mtabs { display: none !important; }
\t\t\t}
\t\t\t@media (max-width: 991px) {
\t\t\t\t.duty-ch-sidetoggle { display: none !important; }
\t\t\t}'''

# --- 4. mobile header styles inside the ≤991 block ---------------------------

A4_OLD = '\t\t\t\t.duty-chatface.ch-convo-open .duty-ch-center { display: flex; }'
A4_NEW = A4_OLD + '''
\t\t\t\t.duty-ch-mhead { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--border-color, #e6e6e6); background: var(--fg-color, #fafafa); position: sticky; top: 0; z-index: 6; }
\t\t\t\t.duty-ch-mhead b { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px; }
\t\t\t\t.duty-ch-mback { font-weight: 700; color: #0F5C55; text-decoration: none; white-space: nowrap; cursor: pointer; }
\t\t\t\t.duty-ch-mback:hover { text-decoration: none; color: #0F5C55; }
\t\t\t\t.duty-ch-munit { background: var(--bg-light-gray, #eef2f1); color: #0f766e; border: 1px solid #d5e5e2; border-radius: 8px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 16px; white-space: nowrap; }'''

EDITS = [
    ("set_mtab: \U0001f4ac routes to the Chat face", A1_OLD, A1_NEW),
    ("open_convo: back header + 991px breakpoint", A2_OLD, A2_NEW),
    ("css: mtabs hide desktop-only, sidetoggle mobile-hidden", A3_OLD, A3_NEW),
    ("css: mobile conversation header", A4_OLD, A4_NEW),
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

    if "duty-ch-mhead" in files[JS]:
        print("Already applied. Nothing to do.")
        return
    if '"3.59.3"' not in files[INIT]:
        sys.exit("ABORT: not at v3.59.3 — apply apply_v3593_switch_ux.py first.")

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

    init = files[INIT].replace('"3.59.3"', '"3.59.4"')
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init)
    print("wrote __init__.py -> 3.59.4")


if __name__ == "__main__":
    main()
