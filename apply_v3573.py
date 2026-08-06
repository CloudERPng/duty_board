#!/usr/bin/env python3
"""Duty Board v3.57.3 — Chat face housekeeping.

1. BADGE BUG: opening a conversation now clears its unread pill
   immediately (optimistic zero in the rail cache) and a reconciling
   refresh_chat fires ~1.5s later, after mark_*_seen has committed.
   Previously the rail re-rendered from a stale cache, so counts
   survived until you left the face and came back.

2. LIVE RAIL: the duty_client_room realtime event now pings the rail,
   so a client or colleague posting in ANY room bumps that room to the
   top with a fresh pill while you watch. (Team and DM events were
   wired in v3.57.0; rooms were the gap.)

3. NEW DM: a ✏ button in the rail head opens a staff picker — type to
   filter, click or Enter to open the thread. This restores a way to
   start a first-ever DM now that chat has left the My Day face.

4. BREATHING ROOM: message rows in the Chat face get WhatsApp-ish
   vertical rhythm — more gap between messages, taller line-height,
   wider gutters. Scoped to .duty-chatface only, so the mobile board
   chat tab and client portal are untouched.

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.2.
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. rail head gets the ✏ new-chat button --------------------------------

A1_OLD = '\t\t\t\t\t<div class="duty-ch-railhead"><b>\\ud83d\\udcac ${__("Chats")}</b><span class="duty-ch-total"></span></div>'
A1_NEW = '\t\t\t\t\t<div class="duty-ch-railhead"><b>\\ud83d\\udcac ${__("Chats")}</b><span class="duty-ch-total"></span><a class="duty-ch-new" title="${__("New direct message")}">\\u270f</a></div>'

# --- 2. bind it -------------------------------------------------------------

A2_OLD = '\t\tthis.$chatface.find(".duty-ch-sidetoggle").on("click", () => this.toggle_ch_side());'
A2_NEW = A2_OLD + '\n\t\tthis.$chatface.find(".duty-ch-new").on("click", () => this.new_dm_dialog());'

# --- 3. open_convo clears the pill it just read -----------------------------

A3_OLD = '\t\tthis._ch_open = { kind: kind, id: id };'
A3_NEW = '''\t\tthis._ch_open = { kind: kind, id: id };
\t\t// Optimistic: the pill dies the moment you open the conversation.
\t\t// The server watermark (mark_*_seen) commits asynchronously, so a
\t\t// reconciling refresh follows once it has had time to land.
\t\tconst cv = (this._convos || []).find((c) => c.kind === kind && String(c.id) === String(id));
\t\tif (cv) { cv.unread = 0; cv.unread_client = 0; cv.unread_other = 0; }
\t\tclearTimeout(this._ch_reconcile);
\t\tthis._ch_reconcile = setTimeout(() => { if (this.face === "chat") this.refresh_chat(true); }, 1500);'''

# --- 4. room traffic pings the rail -----------------------------------------

A4_OLD = '''\t\tfrappe.realtime.on("duty_client_room", (n) => {
\t\t\tif (n && n.room && this._open_room === n.room) this.load_client_room(n.room);
\t\t\telse if (this.face === "clients") this.refresh_clients(true);
\t\t});'''

A4_NEW = '''\t\tfrappe.realtime.on("duty_client_room", (n) => {
\t\t\tif (n && n.room && this._open_room === n.room) this.load_client_room(n.room);
\t\t\telse if (this.face === "clients") this.refresh_clients(true);
\t\t\tthis.ch_ping();
\t\t});'''

# --- 5. the picker ----------------------------------------------------------

A5_OLD = '\ttoggle_ch_side() {'

A5_NEW = '''\tnew_dm_dialog() {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst people = this.team_members();
\t\tif (!people.length) {
\t\t\tfrappe.show_alert({ message: __("Colleague list is still loading — try again in a moment."), indicator: "orange" });
\t\t\treturn;
\t\t}
\t\tconst d = new frappe.ui.Dialog({ title: __("New direct message") });
\t\t$(d.body).html(`
\t\t\t<input type="text" class="form-control duty-ndm-q" placeholder="${__("Type a name\\u2026")}">
\t\t\t<div class="duty-ndm-list"></div>
\t\t`);
\t\tconst $q = $(d.body).find(".duty-ndm-q");
\t\tconst $list = $(d.body).find(".duty-ndm-list");
\t\tconst pick = (user) => {
\t\t\td.hide();
\t\t\tthis.open_convo("dm", user);
\t\t};
\t\tconst paint = () => {
\t\t\tconst q = ($q.val() || "").toLowerCase();
\t\t\tconst rows = people
\t\t\t\t.filter((p) => !q || (p.full_name || p.user).toLowerCase().indexOf(q) >= 0)
\t\t\t\t.sort((a, b) => (a.full_name || a.user).localeCompare(b.full_name || b.user));
\t\t\t$list.html(
\t\t\t\trows.length
\t\t\t\t\t? rows
\t\t\t\t\t\t.map(
\t\t\t\t\t\t\t(p) => `
\t\t\t\t\t\t<a class="duty-ndm-row" data-user="${esc(p.user)}">
\t\t\t\t\t\t\t<span class="duty-ch-av" style="background:${this.user_color(p.user)}">${esc((p.full_name || p.user).trim().charAt(0).toUpperCase())}</span>
\t\t\t\t\t\t\t<span>${esc(p.full_name || p.user)}</span>
\t\t\t\t\t\t</a>`
\t\t\t\t\t\t)
\t\t\t\t\t\t.join("")
\t\t\t\t\t: `<div class="text-muted duty-plan-empty">${__("Nobody matches.")}</div>`
\t\t\t);
\t\t\t$list.find(".duty-ndm-row").on("click", (e) => pick($(e.currentTarget).attr("data-user")));
\t\t};
\t\t$q.on("input", frappe.utils.debounce(paint, 120));
\t\t$q.on("keydown", (e) => {
\t\t\tif (e.key === "Enter") {
\t\t\t\tconst $first = $list.find(".duty-ndm-row").first();
\t\t\t\tif ($first.length) pick($first.attr("data-user"));
\t\t\t}
\t\t});
\t\tpaint();
\t\td.show();
\t\tsetTimeout(() => $q.focus(), 150);
\t}

''' + A5_OLD

# --- 6. styles: picker + message breathing room ------------------------------

A6_OLD = '\t\t\t.duty-ch-room .duty-cr-back, .duty-ch-room .duty-cr-mtabs { display: none !important; }'

A6_NEW = A6_OLD + '''
\t\t\t.duty-ch-new { margin-left: auto; cursor: pointer; font-size: 15px; opacity: .7; text-decoration: none; }
\t\t\t.duty-ch-new:hover { opacity: 1; text-decoration: none; }
\t\t\t.duty-ndm-q { margin-bottom: 8px; }
\t\t\t.duty-ndm-list { max-height: 320px; overflow-y: auto; }
\t\t\t.duty-ndm-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px; cursor: pointer; color: inherit; text-decoration: none; }
\t\t\t.duty-ndm-row:hover { background: var(--bg-light-gray, #f2f2f2); color: inherit; text-decoration: none; }
\t\t\t.duty-ndm-row .duty-ch-av { width: 32px; height: 32px; min-width: 32px; font-size: 13px; }
\t\t\t/* WhatsApp rhythm — Chat face only; mobile board tab and portal untouched. */
\t\t\t.duty-chatface .duty-chat-list { padding: 16px 20px; }
\t\t\t.duty-chatface .duty-chat-list .duty-msg { margin-bottom: 14px; line-height: 1.55; }
\t\t\t.duty-chatface .duty-cr-msgs { padding: 16px 20px; }
\t\t\t.duty-chatface .duty-cr-msgs .duty-cr-msg { margin-bottom: 14px; line-height: 1.55; }
\t\t\t.duty-chatface .duty-dm-list { padding: 16px 20px; }
\t\t\t.duty-chatface .duty-dm-list .duty-msg { margin-bottom: 14px; line-height: 1.55; }'''

EDITS = [
    ("rail head: \\u270f new-chat button", A1_OLD, A1_NEW),
    ("constructor: bind new-chat", A2_OLD, A2_NEW),
    ("open_convo: optimistic pill clear + reconcile", A3_OLD, A3_NEW),
    ("realtime: room traffic pings the rail", A4_OLD, A4_NEW),
    ("methods: new_dm_dialog", A5_OLD, A5_NEW),
    ("styles: picker + message rhythm", A6_OLD, A6_NEW),
]


def main():
    js_path = os.path.join(os.getcwd(), JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run from ~/frappe-bench/apps/duty_board")
    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    if "width: 360px; min-width: 360px" not in src:
        sys.exit("ABORT: v3.57.2 not applied — run apply_v3572.py first.")
    if "duty-ch-new" in src:
        print("Already applied — duty-ch-new present. Nothing to do.")
        return

    problems = [f"  [{src.count(o)} matches] {label}" for label, o, _ in EDITS if src.count(o) != 1]
    if problems:
        print("ABORT — anchors did not match exactly once:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out = src
    for label, old, new in EDITS:
        out = out.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(js_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"\nwrote {JS}")

    init_path = os.path.join(os.getcwd(), INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.2"', '"3.57.3"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.3")
    else:
        print("NOTE: __init__.py not at 3.57.2 — version left untouched.")


if __name__ == "__main__":
    main()
