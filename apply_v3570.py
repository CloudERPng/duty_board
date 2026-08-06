#!/usr/bin/env python3
"""Duty Board v3.57.0 — the Chat face.

Applies every edit by exact-string match. If any anchor is missing or
ambiguous the script aborts BEFORE writing, so a partial apply is not
possible. Re-running after a successful apply is a no-op.

Usage (from ~/frappe-bench/apps/duty_board):
    python3 apply_v3570.py            # apply
    python3 apply_v3570.py --check    # report only, write nothing
"""

import io
import os
import sys

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
INIT = "duty_board/__init__.py"

CHECK_ONLY = "--check" in sys.argv

# ---------------------------------------------------------------------------
# 1. Constructor — the Chat face shell
# ---------------------------------------------------------------------------

A1_OLD = '\t\tthis.$me = $(`<div class="duty-me" style="display:none"></div>`).appendTo(page.body);'

A1_NEW = '''\t\tthis.$chatface = $(`
\t\t\t<div class="duty-chatface" style="display:none">
\t\t\t\t<div class="duty-ch-rail">
\t\t\t\t\t<div class="duty-ch-railhead"><b>\\ud83d\\udcac ${__("Chats")}</b><span class="duty-ch-total"></span></div>
\t\t\t\t\t<div class="duty-ch-search"><input type="text" class="form-control input-sm" placeholder="${__("Search chats\\u2026")}"></div>
\t\t\t\t\t<div class="duty-ch-list"></div>
\t\t\t\t</div>
\t\t\t\t<div class="duty-ch-center">
\t\t\t\t\t<a class="duty-ch-sidetoggle" style="display:none" title="${__("Show or hide the task column")}">\\ud83d\\udccb</a>
\t\t\t\t\t<div class="duty-ch-room duty-cr-room" style="display:none"></div>
\t\t\t\t\t<div class="duty-ch-team" style="display:none"></div>
\t\t\t\t\t<div class="duty-ch-dm" style="display:none"></div>
\t\t\t\t\t<div class="duty-ch-blank">${__("Pick a conversation on the left.")}</div>
\t\t\t\t</div>
\t\t\t</div>
\t\t`).appendTo(page.body);
\t\tif (localStorage.getItem("duty_ch_side") === "0") this.$chatface.addClass("ch-side-hidden");
\t\tthis.$chatface.find(".duty-ch-sidetoggle").on("click", () => this.toggle_ch_side());
\t\tthis.$chatface.find(".duty-ch-search input").on("input", frappe.utils.debounce((e) => {
\t\t\tthis._ch_q = e.target.value;
\t\t\tthis.render_chat_rail();
\t\t}, 200));
''' + A1_OLD

# ---------------------------------------------------------------------------
# 2. Left rail button
# ---------------------------------------------------------------------------

A2_OLD = '\t\t{ id: "clients", ic: RSVG.rooms, label: __("Client Rooms"), go: () => board.show_face("clients") },'

A2_NEW = ('\t\t{ id: "chat", ic: \'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>\', '
          'label: __("Chat"), go: () => board.show_face("chat") },\n' + A2_OLD)

# ---------------------------------------------------------------------------
# 3. show_face — visibility + refresh + park the team chat on the way out
# ---------------------------------------------------------------------------

A3_OLD = '\t\tthis.$clients.toggle(face === "clients");'
A3_NEW = ('\t\tif (this.$chatface) this.$chatface.toggle(face === "chat");\n'
          '\t\tif (face !== "chat") this._ch_return_team();\n' + A3_OLD)

A4_OLD = '\t\tif (face === "clients") this.refresh_clients();'
A4_NEW = '\t\tif (face === "chat") this.refresh_chat();\n' + A4_OLD

# The Clients face and the Chat face both render into a .duty-cr-room node.
# Only one may hold a rendered room at a time, or global .duty-cr-msgs
# lookups (jump_to_msg) can hit the hidden copy.
A5_OLD = '\t\tconst prev_face = this.face;'
A5_NEW = ('\t\tconst prev_face = this.face;\n'
          '\t\tif (face === "chat" && prev_face !== "chat") {\n'
          '\t\t\tthis.$clients.find(".duty-cr-room").empty().hide();\n'
          '\t\t\tthis.$clients.removeClass("cr-room-open");\n'
          '\t\t\tthis._open_room = null;\n'
          '\t\t\tthis._ch_open = null;\n'
          '\t\t}\n'
          '\t\tif (face !== "chat" && prev_face === "chat") {\n'
          '\t\t\tthis.$chatface.find(".duty-ch-room").empty().hide();\n'
          '\t\t\tthis._open_room = null;\n'
          '\t\t}')

# ---------------------------------------------------------------------------
# 4. render_client_room renders into whichever face is asking
# ---------------------------------------------------------------------------

A6_OLD = '\t\tconst $room = this.$clients.find(".duty-cr-room").show();'
A6_NEW = '\t\tconst $room = this._cr_host().show();'

# ---------------------------------------------------------------------------
# 5. Realtime — keep the rail live
# ---------------------------------------------------------------------------

A7_OLD = '\t\tfrappe.realtime.on("duty_board_message", (m) => this.handle_incoming(m));'
A7_NEW = ('\t\tfrappe.realtime.on("duty_board_message", (m) => {\n'
          '\t\t\tthis.handle_incoming(m);\n'
          '\t\t\tthis.ch_ping();\n'
          '\t\t});')

A8_OLD = '\t\tfrappe.realtime.on("duty_board_dm", (m) => this.handle_dm(m));'
A8_NEW = ('\t\tfrappe.realtime.on("duty_board_dm", (m) => {\n'
          '\t\t\tthis.handle_dm(m);\n'
          '\t\t\tthis.ch_ping();\n'
          '\t\t});')

# ---------------------------------------------------------------------------
# 6. open_dm — extract the thread body so the dialog and the Chat face share
#    one implementation, and drop the broken typing call (`x` was never in
#    scope here; staff_typing takes a room, which a DM does not have).
# ---------------------------------------------------------------------------

A9_OLD = '''\t\tthis._cr_last_typing = 0;
\t\t$input.on("input", () => {
\t\t\tconst now = Date.now();
\t\t\tif (now - this._cr_last_typing < 2500) return;
\t\t\tthis._cr_last_typing = now;
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.client_room.staff_typing",
\t\t\t\targs: { name: x.name },
\t\t\t\tfreeze: false,
\t\t\t});
\t\t});
\t\td.show();'''

A9_NEW = '\t\td.show();'

# ---------------------------------------------------------------------------
# 7. The new methods
# ---------------------------------------------------------------------------

A10_OLD = '\tinject_style() {'

A10_NEW = '''\t// ---------------- Chat face ----------------

\t_cr_host() {
\t\t// render_client_room paints into whichever face is currently asking.
\t\tif (this.face === "chat") return this.$chatface.find(".duty-ch-room");
\t\treturn this.$clients.find(".duty-cr-room");
\t}

\tch_ping() {
\t\t// Debounced: a burst of realtime events costs one rail refresh.
\t\tif (this.face !== "chat") return;
\t\tclearTimeout(this._ch_t);
\t\tthis._ch_t = setTimeout(() => this.refresh_chat(true), 700);
\t}

\trefresh_chat(silent) {
\t\tfrappe.call({
\t\t\tmethod: "duty_board.chat.get_rail",
\t\t\tfreeze: false,
\t\t\terror: () => {
\t\t\t\tthis._ch_fail = (this._ch_fail || 0) + 1;
\t\t\t\tif (this._ch_fail >= 3) this.halt_polling();
\t\t\t},
\t\t\tcallback: (r) => {
\t\t\t\tthis._ch_fail = 0;
\t\t\t\tthis._convos = r.message || [];
\t\t\t\tthis.render_chat_rail();
\t\t\t\tif (!this._ch_open) this.open_convo("team", "__team__");
\t\t\t},
\t\t});
\t}

\trender_chat_rail() {
\t\tconst $list = this.$chatface.find(".duty-ch-list");
\t\tconst esc = frappe.utils.escape_html;
\t\tconst q = (this._ch_q || "").toLowerCase();
\t\tconst all = this._convos || [];
\t\tconst rows = all.filter(
\t\t\t(c) =>
\t\t\t\t!q ||
\t\t\t\t(c.title || "").toLowerCase().indexOf(q) >= 0 ||
\t\t\t\t(c.subtitle || "").toLowerCase().indexOf(q) >= 0
\t\t);
\t\tconst total = all.reduce((n, c) => n + (c.unread || 0), 0);
\t\tthis.$chatface
\t\t\t.find(".duty-ch-total")
\t\t\t.text(total ? (total > 99 ? "99+" : total) : "")
\t\t\t.toggle(!!total);
\t\tif (!rows.length) {
\t\t\t$list.html(
\t\t\t\t`<div class="text-muted duty-plan-empty">${q ? __("No chats match.") : __("No conversations yet.")}</div>`
\t\t\t);
\t\t\treturn;
\t\t}
\t\tconst open = this._ch_open || {};
\t\t$list.html(
\t\t\trows
\t\t\t\t.map((c) => {
\t\t\t\t\tconst on = open.kind === c.kind && String(open.id) === String(c.id);
\t\t\t\t\tconst initial = (c.title || "?").trim().charAt(0).toUpperCase();
\t\t\t\t\tconst badge = c.unread
\t\t\t\t\t\t? `<span class="duty-ch-badge ${c.unread_client ? "is-client" : ""}">${c.unread > 99 ? "99+" : c.unread}</span>`
\t\t\t\t\t\t: "";
\t\t\t\t\tconst join = c.join_requests
\t\t\t\t\t\t? `<span class="duty-ch-join" title="${__("Join requests waiting")}">\\ud83d\\ude4b ${c.join_requests}</span>`
\t\t\t\t\t\t: "";
\t\t\t\t\tconst frozen = c.kind === "room" && c.status && c.status !== "Active";
\t\t\t\t\treturn `
\t\t\t\t\t<a class="duty-ch-row ${on ? "on" : ""} ${c.unread ? "unread" : ""} ${frozen ? "frozen" : ""}"
\t\t\t\t\t   data-kind="${esc(c.kind)}" data-id="${esc(String(c.id))}">
\t\t\t\t\t\t<span class="duty-ch-av" style="background:${c.kind === "team" ? "#0f766e" : this.proj_color(String(c.id))}">${c.kind === "team" ? "\\ud83d\\udcac" : c.kind === "dm" ? "\\u2709" : esc(initial)}</span>
\t\t\t\t\t\t<span class="duty-ch-body">
\t\t\t\t\t\t\t<span class="duty-ch-l1">
\t\t\t\t\t\t\t\t<b class="duty-ch-title">${esc(c.title || "")}</b>
\t\t\t\t\t\t\t\t<span class="duty-ch-when">${c.last_when ? esc(this.smart_time(c.last_when)) : ""}</span>
\t\t\t\t\t\t\t</span>
\t\t\t\t\t\t\t<span class="duty-ch-l2">
\t\t\t\t\t\t\t\t<span class="duty-ch-prev">${esc(c.last || __("No messages yet"))}</span>
\t\t\t\t\t\t\t\t${join}${badge}
\t\t\t\t\t\t\t</span>
\t\t\t\t\t\t\t<span class="duty-ch-sub">${esc(c.subtitle || "")}</span>
\t\t\t\t\t\t</span>
\t\t\t\t\t</a>`;
\t\t\t\t})
\t\t\t\t.join("")
\t\t);
\t\t$list.find(".duty-ch-row").on("click", (e) => {
\t\t\tconst $r = $(e.currentTarget);
\t\t\t// .attr not .data — room ids and emails must not be coerced.
\t\t\tthis.open_convo($r.attr("data-kind"), $r.attr("data-id"));
\t\t});
\t}

\topen_convo(kind, id) {
\t\tif (!kind || !id) return;
\t\tthis._ch_open = { kind: kind, id: id };
\t\tconst $c = this.$chatface;
\t\t$c.find(".duty-ch-blank").hide();
\t\t$c.find(".duty-ch-room, .duty-ch-team, .duty-ch-dm").hide();
\t\t$c.find(".duty-ch-sidetoggle").toggle(kind === "room");
\t\tif (kind === "team") this._ch_show_team();
\t\telse if (kind === "room") this._ch_show_room(id);
\t\telse if (kind === "dm") this._ch_show_dm(id);
\t\telse return;
\t\tthis.render_chat_rail();
\t\tif (this.is_mobile()) $c.addClass("ch-convo-open");
\t}

\t_ch_show_team() {
\t\tconst $host = this.$chatface.find(".duty-ch-team").show();
\t\t// Move the live node — every handler, observer and draft comes along.
\t\tif (this.$chat && this.$chat.parent()[0] !== $host[0]) this.$chat.appendTo($host);
\t\tthis.chat_open = true;
\t\tthis.apply_chat_state();
\t\tthis.clear_unread();
\t\tthis.scroll_chat();
\t}

\t_ch_return_team() {
\t\tconst $home = this.body.find(".duty-chat");
\t\tif (this.$chat && $home.length && this.$chat.parent()[0] !== $home[0]) {
\t\t\tthis.$chat.appendTo($home);
\t\t\tthis.apply_chat_state();
\t\t}
\t}

\t_ch_show_room(name) {
\t\tthis._ch_return_team();
\t\tthis.$chatface.find(".duty-ch-room").show();
\t\tthis.open_client_room(name);
\t}

\t_ch_show_dm(user) {
\t\tthis._ch_return_team();
\t\tconst $host = this.$chatface.find(".duty-ch-dm").show();
\t\tthis._ch_dm = this.build_dm_thread($host, user, this.name_map[user] || user);
\t}

\ttoggle_ch_side() {
\t\tconst hide = !this.$chatface.hasClass("ch-side-hidden");
\t\tthis.$chatface.toggleClass("ch-side-hidden", hide);
\t\tlocalStorage.setItem("duty_ch_side", hide ? "0" : "1");
\t}

\tbuild_dm_thread($host, user, full_name) {
\t\t// One implementation, two hosts: the ✉ dialog and the Chat face.
\t\tconst esc = frappe.utils.escape_html;
\t\tconst first = (full_name || user).split(" ")[0];
\t\t$host.html(`
\t\t\t<div class="duty-dm-list"><div class="text-muted">${__("Loading...")}</div></div>
\t\t\t<div class="duty-dm-send">
\t\t\t\t<textarea rows="1" class="form-control duty-dm-input" maxlength="1000"
\t\t\t\t\tplaceholder="${__("Message {0}... Enter to send, Shift+Enter for a new line", [esc(first)])}"></textarea>
\t\t\t\t<button class="btn btn-primary btn-sm duty-dm-btn-send">${__("Send")}</button>
\t\t\t</div>
\t\t`);
\t\tconst $list = $host.find(".duty-dm-list");
\t\tconst $input = $host.find(".duty-dm-input");
\t\tlet oldest = null;
\t\tconst load = (before) => {
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.dm.get_dm_thread",
\t\t\t\targs: { with_user: user, before: before },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst data = r.message || {};
\t\t\t\t\tconst msgs = data.messages || [];
\t\t\t\t\tif (msgs.length) oldest = msgs[0].creation;
\t\t\t\t\tif (!before) {
\t\t\t\t\t\t$list.empty();
\t\t\t\t\t\tif (data.has_more) {
\t\t\t\t\t\t\t$list.append(`<div class="duty-load-earlier"><a>${__("Load earlier")}</a></div>`);
\t\t\t\t\t\t\t$list.find(".duty-load-earlier a").on("click", () => load(oldest));
\t\t\t\t\t\t}
\t\t\t\t\t\t$list.append(msgs.map((m) => this.dm_row(m)).join(""));
\t\t\t\t\t\tif (!msgs.length) {
\t\t\t\t\t\t\t$list.append(`<div class="text-muted duty-plan-empty">${__("No messages yet — say hello.")}</div>`);
\t\t\t\t\t\t}
\t\t\t\t\t\t$list.scrollTop($list[0].scrollHeight);
\t\t\t\t\t} else {
\t\t\t\t\t\tconst old_h = $list[0].scrollHeight;
\t\t\t\t\t\tconst $anchor = $list.find(".duty-load-earlier");
\t\t\t\t\t\t$anchor.after(msgs.map((m) => this.dm_row(m)).join(""));
\t\t\t\t\t\tif (!data.has_more) $anchor.hide();
\t\t\t\t\t\t$list.scrollTop($list[0].scrollHeight - old_h);
\t\t\t\t\t}
\t\t\t\t\tthis.mark_dm_seen(user);
\t\t\t\t},
\t\t\t});
\t\t};
\t\tconst send = () => {
\t\t\tconst text = ($input.val() || "").trim();
\t\t\tif (!text) return;
\t\t\t$input.val("");
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.dm.send_dm",
\t\t\t\targs: { to: user, message: text },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst m = r.message;
\t\t\t\t\tif (m && !$list.find(`[data-name="${m.name}"]`).length) {
\t\t\t\t\t\t$list.find(".duty-plan-empty").remove();
\t\t\t\t\t\t$list.append(this.dm_row(m));
\t\t\t\t\t\t$list.scrollTop($list[0].scrollHeight);
\t\t\t\t\t}
\t\t\t\t},
\t\t\t});
\t\t};
\t\t$host.find(".duty-dm-btn-send").on("click", send);
\t\t$input.on("keydown", (e) => {
\t\t\tif (e.key === "Enter" && !e.shiftKey) {
\t\t\t\te.preventDefault();
\t\t\t\tsend();
\t\t\t}
\t\t});
\t\tload(null);
\t\tthis.set_dm_badge(user, 0);
\t\treturn { user: user, $list: $list, append: (m) => {
\t\t\tif (!$list.find(`[data-name="${m.name}"]`).length) {
\t\t\t\t$list.find(".duty-plan-empty").remove();
\t\t\t\t$list.append(this.dm_row(m));
\t\t\t\t$list.scrollTop($list[0].scrollHeight);
\t\t\t}
\t\t} };
\t}

''' + A10_OLD

# ---------------------------------------------------------------------------
# 8. Styles
# ---------------------------------------------------------------------------

# NB: newline-terminated. Bare '.duty-chat-rail {' also matches the mobile
# override at ~10185; the trailing \n pins it to the block-opening line.
A11_OLD = '\t\t\t.duty-chat-rail {\n'

A11_NEW = '''\t\t\t.duty-chatface { display: flex; gap: 0; height: calc(100vh - 150px); min-height: 420px; border: 1px solid var(--border-color, #e0e0e0); border-radius: 10px; overflow: hidden; background: var(--card-bg, #fff); }
\t\t\t.duty-ch-rail { width: 320px; min-width: 320px; display: flex; flex-direction: column; border-right: 1px solid var(--border-color, #e0e0e0); background: var(--fg-color, #fafafa); }
\t\t\t.duty-ch-railhead { display: flex; align-items: center; gap: 8px; padding: 12px 14px 8px; font-size: 15px; }
\t\t\t.duty-ch-total { background: #ef4444; color: #fff; border-radius: 10px; padding: 0 7px; font-size: 11px; font-weight: 700; line-height: 18px; }
\t\t\t.duty-ch-search { padding: 0 12px 10px; }
\t\t\t.duty-ch-list { flex: 1; overflow-y: auto; }
\t\t\t.duty-ch-row { display: flex; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--border-color, #ececec); cursor: pointer; text-decoration: none; color: inherit; }
\t\t\t.duty-ch-row:hover { background: var(--bg-light-gray, #f2f2f2); text-decoration: none; color: inherit; }
\t\t\t.duty-ch-row.on { background: var(--bg-light-gray, #e8f2f1); box-shadow: inset 3px 0 0 #0f766e; }
\t\t\t.duty-ch-row.frozen { opacity: .55; }
\t\t\t.duty-ch-av { width: 40px; height: 40px; min-width: 40px; border-radius: 50%; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; }
\t\t\t.duty-ch-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
\t\t\t.duty-ch-l1, .duty-ch-l2 { display: flex; align-items: center; gap: 6px; }
\t\t\t.duty-ch-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
\t\t\t.duty-ch-row.unread .duty-ch-title { font-weight: 800; }
\t\t\t.duty-ch-when { font-size: 11px; color: var(--text-muted, #888); white-space: nowrap; }
\t\t\t.duty-ch-prev { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: var(--text-muted, #777); }
\t\t\t.duty-ch-row.unread .duty-ch-prev { color: var(--text-color, #333); }
\t\t\t.duty-ch-sub { font-size: 11px; color: var(--text-muted, #999); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
\t\t\t.duty-ch-badge { background: #6b7280; color: #fff; border-radius: 10px; padding: 0 7px; font-size: 11px; font-weight: 700; line-height: 18px; }
\t\t\t.duty-ch-badge.is-client { background: #ef4444; }
\t\t\t.duty-ch-join { background: #f59e0b; color: #fff; border-radius: 10px; padding: 0 6px; font-size: 10px; font-weight: 700; line-height: 17px; }
\t\t\t.duty-ch-center { flex: 1; min-width: 0; position: relative; display: flex; flex-direction: column; }
\t\t\t.duty-ch-center > .duty-ch-room, .duty-ch-center > .duty-ch-team, .duty-ch-center > .duty-ch-dm { flex: 1; min-height: 0; }
\t\t\t.duty-ch-blank { margin: auto; color: var(--text-muted, #999); }
\t\t\t.duty-ch-sidetoggle { position: absolute; top: 10px; right: 12px; z-index: 5; cursor: pointer; font-size: 15px; opacity: .65; }
\t\t\t.duty-ch-sidetoggle:hover { opacity: 1; }
\t\t\t.duty-chatface.ch-side-hidden .duty-cr-side { display: none !important; }
\t\t\t.duty-ch-team { display: flex; flex-direction: column; }
\t\t\t.duty-ch-team .duty-chat-card { flex: 1; min-height: 0; border: 0; border-radius: 0; box-shadow: none; }
\t\t\t.duty-ch-team .duty-chat-collapse { display: none !important; }
\t\t\t.duty-ch-dm { display: flex; flex-direction: column; padding: 12px; }
\t\t\t.duty-ch-dm .duty-dm-list { flex: 1; min-height: 0; overflow-y: auto; }
\t\t\t.duty-ch-room .duty-cr-back, .duty-ch-room .duty-cr-mtabs { display: none !important; }
\t\t\t@media (max-width: 991px) {
\t\t\t\t.duty-chatface { height: calc(100dvh - 120px); border: 0; border-radius: 0; }
\t\t\t\t.duty-ch-rail { width: 100%; min-width: 0; border-right: 0; }
\t\t\t\t.duty-ch-center { display: none; }
\t\t\t\t.duty-chatface.ch-convo-open .duty-ch-rail { display: none; }
\t\t\t\t.duty-chatface.ch-convo-open .duty-ch-center { display: flex; }
\t\t\t}
''' + A11_OLD

# ---------------------------------------------------------------------------
# 9. render_my_rooms dead-click: this.open_room has never existed, and the
#    `&&` guard swallowed it, so the dashboard room chips switched face and
#    then did nothing. The method is open_client_room.
# ---------------------------------------------------------------------------

A12_OLD = '\t\t\t\t\tsetTimeout(() => this.open_room && this.open_room(room), 400);'
A12_NEW = '\t\t\t\t\tsetTimeout(() => this.open_client_room(room), 400);'

EDITS = [
    ("constructor: Chat face shell", A1_OLD, A1_NEW),
    ("rail: Chat button", A2_OLD, A2_NEW),
    ("show_face: visibility", A3_OLD, A3_NEW),
    ("show_face: refresh", A4_OLD, A4_NEW),
    ("show_face: single rendered room", A5_OLD, A5_NEW),
    ("render_client_room: portable host", A6_OLD, A6_NEW),
    ("realtime: team -> rail", A7_OLD, A7_NEW),
    ("realtime: dm -> rail", A8_OLD, A8_NEW),
    ("open_dm: drop broken typing call", A9_OLD, A9_NEW),
    ("methods: Chat face", A10_OLD, A10_NEW),
    ("styles: Chat face", A11_OLD, A11_NEW),
    ("render_my_rooms: dead open_room call", A12_OLD, A12_NEW),
]


def main():
    root = os.getcwd()
    js_path = os.path.join(root, JS)
    if not os.path.exists(js_path):
        sys.exit(f"ABORT: {JS} not found. Run this from ~/frappe-bench/apps/duty_board")

    with io.open(js_path, encoding="utf-8") as f:
        src = f.read()

    # Idempotency: already applied?
    if "duty-chatface" in src:
        print("Already applied — duty-chatface present. Nothing to do.")
        return

    # Dry pass: every anchor must appear exactly once BEFORE we write anything.
    problems = []
    for label, old, _new in EDITS:
        n = src.count(old)
        if n != 1:
            problems.append(f"  [{n} matches] {label}")
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
    print(f"\nwrote {JS}  ({len(src.splitlines())} -> {len(out.splitlines())} lines)")

    init_path = os.path.join(root, INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.56.0"', '"3.57.0"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.57.0")
    else:
        print("NOTE: __init__.py was not at 3.56.0 — version left untouched.")


if __name__ == "__main__":
    main()
