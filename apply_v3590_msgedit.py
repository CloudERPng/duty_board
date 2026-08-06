#!/usr/bin/env python3
"""Duty Board v3.59.0 — edit sent messages (30-minute window).

Staff may edit their OWN messages within 30 minutes of sending, on all
three surfaces. Edited messages show an "edited" marker by the time,
WhatsApp-style. Editing may also clear an attachment.

Governance: client-room messages are client-visible, so editing one
rewrites what a client may already have read. Per decision, a room edit
leaves an internal audit whisper — "✏ {who} edited a message (was: …)"
— so the trail survives even though the message itself changes.

Server enforces everything (own message, 30-min window, staff): client
clocks are not trusted. The window is a module constant.

Doctype JSON edits (edited_on field) are done structurally via a helper,
not string anchors, so field_order and fields stay in sync.

Deploy: bench migrate && bench build --app duty_board && bench restart
  (migrate creates the edited_on columns.)

Anchored where it can be, all-or-nothing, idempotent. Requires v3.58.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
API = "duty_board/api.py"
CR = "duty_board/client_room.py"
DM = "duty_board/dm.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# ---------------------------------------------------------------------------
# client_room.py — room edit endpoint (with the audit whisper) + payload field
# ---------------------------------------------------------------------------

CR_PAYLOAD_OLD = '\t\t\t"name", "message", "internal", "owner", "creation",\n\t\t\t"attachment_url", "attachment_name", "ref",'
CR_PAYLOAD_NEW = '\t\t\t"name", "message", "internal", "owner", "creation", "edited_on",\n\t\t\t"attachment_url", "attachment_name", "ref",'

CR_STR_OLD = '\tfor r in rows:\n\t\tr.creation = str(r.creation)\n\t\tr.who = names.setdefault('
CR_STR_NEW = '\tfor r in rows:\n\t\tr.creation = str(r.creation)\n\t\tr.edited_on = str(r.edited_on) if r.get("edited_on") else None\n\t\tr.who = names.setdefault('

CR_ENDPOINT_OLD = '# ---------------- staff face ----------------'
CR_ENDPOINT_NEW = '''@frappe.whitelist()
def edit_room_message(name, message=None, drop_attachment=0):
\t"""Edit own room message within 30 min. Because the room is client-visible,
\tthe original text is preserved as an internal audit whisper."""
\tfrom duty_board.api import _within_edit_window

\tdoc = frappe.get_doc("Client Room Message", name)
\tif doc.owner != frappe.session.user:
\t\tfrappe.throw(_("You can only edit your own messages."))
\tif frappe.db.get_value("User", doc.owner, "user_type") != "System User":
\t\tfrappe.throw(_("Not permitted."), frappe.PermissionError)
\tif not _within_edit_window(doc.creation):
\t\tfrappe.throw(_("The 30-minute edit window has passed."))
\troom = frappe.get_doc("Client Room", doc.room)
\told_text = doc.message
\ttext = (message or "").strip()
\tif not text and not doc.attachment_url:
\t\tfrappe.throw(_("A message cannot be empty."))
\tdoc.message = text or "📎"
\tif cint(drop_attachment):
\t\tdoc.attachment_url = None
\t\tdoc.attachment_name = None
\tdoc.edited_on = frappe.utils.now_datetime()
\tdoc.save(ignore_permissions=True)
\t# Governance trail: a whisper only staff see, naming the edit and the
\t# text as the client may already have read it.
\twho = frappe.utils.get_fullname(frappe.session.user)
\t_post(room, _("✏ {0} edited a message (was: {1})").format(who, (old_text or "")[:200]), internal=1)
\tfrappe.db.commit()
\tfrappe.publish_realtime("duty_client_room", {"room": room.name})
\treturn {"ok": 1}


# ---------------- staff face ----------------'''

# ---------------------------------------------------------------------------
# dm.py — DM edit endpoint + thread field
# ---------------------------------------------------------------------------

DM_FIELDS_OLD = '\t\tfields=["name", "sender", "recipient", "message", "creation"],'
DM_FIELDS_NEW = '\t\tfields=["name", "sender", "recipient", "message", "creation", "edited_on"],'

DM_STR_OLD = '\tfor r in rows:\n\t\tr.creation = str(r.creation)\n\t\tr.sender_name = names.setdefault('
DM_STR_NEW = '\tfor r in rows:\n\t\tr.creation = str(r.creation)\n\t\tr.edited_on = str(r.edited_on) if r.get("edited_on") else None\n\t\tr.sender_name = names.setdefault('

DM_ENDPOINT_OLD = '@frappe.whitelist()\ndef mark_dm_seen(with_user):'
DM_ENDPOINT_NEW = '''@frappe.whitelist()
def edit_dm(name, message=None, drop_attachment=0):
\t"""Edit own DM within 30 minutes. DMs have no attachments; drop is ignored."""
\tfrom duty_board.api import _within_edit_window

\trequire_staff()
\tme = frappe.session.user
\tdoc = frappe.get_doc("Duty DM", name)
\tif doc.sender != me:
\t\tfrappe.throw(_("You can only edit your own messages."))
\tif not _within_edit_window(doc.creation):
\t\tfrappe.throw(_("The 30-minute edit window has passed."))
\ttext = (message or "").strip()
\tif not text:
\t\tfrappe.throw(_("A message cannot be empty."))
\tif len(text) > MAX_LENGTH:
\t\tfrappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
\tdoc.message = text
\tdoc.edited_on = frappe.utils.now_datetime()
\tdoc.save(ignore_permissions=True)
\tfrappe.db.commit()
\tpayload = {
\t\t"name": doc.name, "sender": doc.sender, "recipient": doc.recipient,
\t\t"message": text, "creation": str(doc.creation), "edited_on": str(doc.edited_on),
\t\t"edit": 1,
\t}
\tfrappe.publish_realtime("duty_board_dm", payload, user=doc.recipient)
\tfrappe.publish_realtime("duty_board_dm", payload, user=me)
\treturn payload


@frappe.whitelist()
def mark_dm_seen(with_user):'''


DOCTYPES = {
    "duty_board/duty_board/doctype/team_message/team_message.json": "attachment_type",
    "duty_board/duty_board/doctype/client_room_message/client_room_message.json": "ref",
    "duty_board/duty_board/doctype/duty_dm/duty_dm.json": "seen",
}


def add_edited_field(path):
    """Insert an edited_on Datetime after the given trailing field. Returns
    (changed, reason)."""
    after = DOCTYPES[path]
    with io.open(path, encoding="utf-8") as f:
        d = json.load(f)
    if any(x["fieldname"] == "edited_on" for x in d["fields"]):
        return False, "already has edited_on"
    fld = {
        "fieldname": "edited_on",
        "fieldtype": "Datetime",
        "label": "Edited On",
        "read_only": 1,
    }
    # fields array
    idx = next((i for i, x in enumerate(d["fields"]) if x["fieldname"] == after), None)
    if idx is None:
        return False, f"anchor field {after} not found"
    d["fields"].insert(idx + 1, fld)
    # field_order
    if "field_order" in d:
        if after in d["field_order"]:
            oi = d["field_order"].index(after)
            d["field_order"].insert(oi + 1, "edited_on")
        else:
            d["field_order"].append("edited_on")
    return True, d


# ---------------------------------------------------------------------------
# api.py — module constant + team edit endpoint + payload field
# ---------------------------------------------------------------------------

API_CONST_OLD = "@frappe.whitelist()\ndef send_message(\n\tmessage=None,"
API_CONST_NEW = '''EDIT_WINDOW_SECONDS = 30 * 60


def _within_edit_window(creation):
\tfrom frappe.utils import time_diff_in_seconds, now_datetime

\treturn time_diff_in_seconds(now_datetime(), creation) <= EDIT_WINDOW_SECONDS


@frappe.whitelist()
def edit_message(name, message=None, drop_attachment=0):
\t"""Edit own Team Message within the window. Optionally clear attachment."""
\trequire_staff()
\tdoc = frappe.get_doc("Team Message", name)
\tif doc.user != frappe.session.user:
\t\tfrappe.throw(_("You can only edit your own messages."))
\tif not _within_edit_window(doc.creation):
\t\tfrappe.throw(_("The 30-minute edit window has passed."))
\ttext = (message or "").strip()
\tif not text and not doc.attachment:
\t\tfrappe.throw(_("A message cannot be empty."))
\tdoc.message = text
\tif cint(drop_attachment):
\t\tdoc.attachment = None
\t\tdoc.attachment_name = None
\t\tdoc.attachment_type = None
\tdoc.edited_on = frappe.utils.now_datetime()
\tdoc.save(ignore_permissions=True)
\tfrappe.db.commit()
\tpayload = _message_payload(doc.as_dict(), _reactions_for([doc.name]))
\tfrappe.publish_realtime("duty_board_message_edit", payload)
\treturn payload


@frappe.whitelist()
def send_message(
\tmessage=None,'''

API_PAYLOAD_OLD = '\t\t\t"attachment_type",\n\t\t\t"creation",\n\t\t],\n\t\torder_by="creation desc",\n\t\tlimit=min(cint(limit) or 50, 200),'
API_PAYLOAD_NEW = '\t\t\t"attachment_type",\n\t\t\t"creation",\n\t\t\t"edited_on",\n\t\t],\n\t\torder_by="creation desc",\n\t\tlimit=min(cint(limit) or 50, 200),'

# _message_payload must echo edited_on. Find its dict return.
API_MP_OLD = '\t\t"creation": str(r.get("creation")),\n\t\t"reactions": reactions.get(r.get("name"), {}),\n\t}'
API_MP_NEW = '\t\t"creation": str(r.get("creation")),\n\t\t"edited_on": str(r.get("edited_on")) if r.get("edited_on") else None,\n\t\t"reactions": reactions.get(r.get("name"), {}),\n\t}'


# ---------------------------------------------------------------------------
# JS — edit affordance + edited marker on all three renderers
# ---------------------------------------------------------------------------

JS_EDITED_HELPER_OLD = "\tformat_message_text(m) {"
JS_EDITED_HELPER_NEW = '''\tedited_tag(m) {
\t\treturn m.edited_on ? ` <span class="duty-msg-edited" title="${__("edited")}">${__("edited")}</span>` : "";
\t}

\tcan_edit(creation) {
\t\tif (!creation) return false;
\t\tconst t = frappe.datetime.str_to_obj(creation).getTime();
\t\treturn Date.now() - t <= 30 * 60 * 1000;
\t}

\tedit_prompt(kind, name, current, hasAttach, onDone) {
\t\tconst d = new frappe.ui.Dialog({
\t\t\ttitle: __("Edit message"),
\t\t\tfields: [
\t\t\t\t{ fieldname: "text", fieldtype: "Small Text", label: __("Message"), default: current || "" },
\t\t\t\thasAttach
\t\t\t\t\t? { fieldname: "drop", fieldtype: "Check", label: __("Remove the attachment"), default: 0 }
\t\t\t\t\t: null,
\t\t\t].filter(Boolean),
\t\t\tprimary_action_label: __("Save"),
\t\t\tprimary_action: (v) => {
\t\t\t\tconst method =
\t\t\t\t\tkind === "team"
\t\t\t\t\t\t? "duty_board.api.edit_message"
\t\t\t\t\t\t: kind === "room"
\t\t\t\t\t\t? "duty_board.client_room.edit_room_message"
\t\t\t\t\t\t: "duty_board.dm.edit_dm";
\t\t\t\tfrappe.call({
\t\t\t\t\tmethod: method,
\t\t\t\t\targs: { name: name, message: v.text || "", drop_attachment: v.drop ? 1 : 0 },
\t\t\t\t\tcallback: (r) => { d.hide(); if (onDone) onDone(r.message); },
\t\t\t\t});
\t\t\t},
\t\t});
\t\td.show();
\t}

\tformat_message_text(m) {'''

# team renderer: add edited tag + pencil action
JS_TEAM_TIME_OLD = '\t\t\t\t<span class="duty-msg-time">${when}</span>\n\t\t\t\t<a class="duty-msg-reply" title="${__("Reply")}">↩</a>'
JS_TEAM_TIME_NEW = '\t\t\t\t<span class="duty-msg-time">${when}${this.edited_tag(m)}</span>\n\t\t\t\t${mine && this.can_edit(m.creation) ? `<a class="duty-msg-edit" title="${__("Edit")}">✏</a>` : ""}\n\t\t\t\t<a class="duty-msg-reply" title="${__("Reply")}">↩</a>'

# team: bind the pencil (hook near the reply binding)
JS_TEAM_BIND_OLD = '\t\t\t$row.find(".duty-msg-reply").on("click", () => this.set_reply(m));'
JS_TEAM_BIND_NEW = '''\t\t\t$row.find(".duty-msg-reply").on("click", () => this.set_reply(m));
\t\t\t$row.find(".duty-msg-edit").on("click", () =>
\t\t\t\tthis.edit_prompt("team", m.name, m.message, !!m.attachment, () => this.load_messages())
\t\t\t);'''

# room renderer (cr_msg): edited tag + pencil for own staff msgs
JS_ROOM_TIME_OLD = '\t\t\t\t<span class="duty-msg-time">${frappe.datetime.str_to_user(m.creation)}</span>\n\t\t\t\t${m.is_staff ? "" :'
JS_ROOM_TIME_NEW = '\t\t\t\t<span class="duty-msg-time">${frappe.datetime.str_to_user(m.creation)}${this.edited_tag(m)}</span>\n\t\t\t\t${m.mine && this.can_edit(m.creation) ? `<a class="duty-cr-edit" data-name="${m.name}" data-text="${frappe.utils.escape_html(m.message || "")}" data-att="${m.attachment_url ? 1 : 0}" title="${__("Edit")}">✏</a>` : ""}\n\t\t\t\t${m.is_staff ? "" :'

# DM renderer — anchor on the unique dm_row body; reuse its existing `mine`.
JS_DM_TIME_OLD = '''\t\t\t\t<span class="duty-msg-text">${this.linkify(frappe.utils.escape_html(m.message || ""))}</span>
\t\t\t\t<span class="duty-msg-time">${when}</span>
\t\t\t</div>`;
\t}'''
JS_DM_TIME_NEW = '''\t\t\t\t<span class="duty-msg-text">${this.linkify(frappe.utils.escape_html(m.message || ""))}</span>
\t\t\t\t<span class="duty-msg-time">${when}${this.edited_tag(m)}</span>${mine && this.can_edit(m.creation) ? ` <a class="duty-dm-edit" data-name="${m.name}" data-text="${frappe.utils.escape_html(m.message || "")}" title="${__("Edit")}">✏</a>` : ""}
\t\t\t</div>`;
\t}'''

# DM edit-in-place: when a realtime DM carries edit:1, update the row not append
JS_DM_HANDLE_OLD = '''\thandle_dm(m) {
\t\tif (!m || !m.name) return;
\t\tconst me = frappe.session.user;
\t\tconst other = m.sender === me ? m.recipient : m.sender;'''
JS_DM_HANDLE_NEW = '''\thandle_dm(m) {
\t\tif (!m || !m.name) return;
\t\tconst me = frappe.session.user;
\t\tconst other = m.sender === me ? m.recipient : m.sender;
\t\tif (m.edit) {
\t\t\t// An edit, not a new message: rewrite the row wherever it is shown.
\t\t\t[
\t\t\t\tthis._dm_dialog && $(this._dm_dialog.body),
\t\t\t\tthis.$chatface && this.$chatface.find(".duty-ch-dm"),
\t\t\t].forEach(($scope) => {
\t\t\t\tif (!$scope || !$scope.length) return;
\t\t\t\tconst $row = $scope.find(`[data-name="${m.name}"]`);
\t\t\t\tif ($row.length) $row.replaceWith(this.dm_row(m));
\t\t\t});
\t\t\treturn;
\t\t}'''

# DM pencil: delegated so it survives thread re-render (both dialog and face)
JS_DM_BIND_OLD = '\t\t$host.find(".duty-dm-btn-send").on("click", send);'
JS_DM_BIND_NEW = '''\t\t$list.on("click", ".duty-dm-edit", (e) => {
\t\t\tconst $t = $(e.currentTarget);
\t\t\tthis.edit_prompt("dm", $t.data("name"), $t.data("text"), false, () => load(null));
\t\t});
\t\t$host.find(".duty-dm-btn-send").on("click", send);'''

# styles
JS_STYLE_OLD = '\t\t\t.duty-daytabs a.on { background: #0F5C55; border-color: #0F5C55; color: #fff; }'
JS_STYLE_NEW = JS_STYLE_OLD + '''
\t\t\t.duty-msg-edited { font-size: 10px; color: var(--text-muted, #9aa4a0); font-style: italic; margin-left: 4px; }
\t\t\t.duty-msg-edit, .duty-cr-edit, .duty-dm-edit { cursor: pointer; opacity: .6; margin-left: 6px; }
\t\t\t.duty-msg-edit:hover, .duty-cr-edit:hover, .duty-dm-edit:hover { opacity: 1; }'''

# room pencil: delegated binding alongside the existing reply binding
JS_ROOM_BIND_OLD = '\t\t$msgs2.find(".duty-cr-reply").on("click", (e) => {'
JS_ROOM_BIND_NEW = '''\t\t$msgs2.find(".duty-cr-edit").on("click", (e) => {
\t\t\tconst $t = $(e.currentTarget);
\t\t\tthis.edit_prompt("room", $t.data("name"), $t.data("text"), !!$t.data("att"),
\t\t\t\t() => { if (this._open_room) this.load_client_room(this._open_room); });
\t\t});
\t\t$msgs2.find(".duty-cr-reply").on("click", (e) => {'''

# realtime: apply a team edit to an open board without a full reload
JS_RT_OLD = '\t\tfrappe.realtime.on("duty_board_message", (m) => {\n\t\t\tthis.handle_incoming(m);\n\t\t\tthis.ch_ping();\n\t\t});'
JS_RT_NEW = '''\t\tfrappe.realtime.on("duty_board_message", (m) => {
\t\t\tthis.handle_incoming(m);
\t\t\tthis.ch_ping();
\t\t});
\t\tfrappe.realtime.on("duty_board_message_edit", (m) => {
\t\t\tconst $row = this.$list && this.$list.find(`.duty-msg[data-name="${m.name}"]`);
\t\t\tif ($row && $row.length) {
\t\t\t\t$row.find(".duty-msg-text").html(this.format_message_text(m));
\t\t\t\tif (!$row.find(".duty-msg-edited").length) {
\t\t\t\t\t$row.find(".duty-msg-time").append(
\t\t\t\t\t\t` <span class="duty-msg-edited">${__("edited")}</span>`
\t\t\t\t\t);
\t\t\t\t}
\t\t\t}
\t\t});'''


def main():
    root = os.getcwd()
    need = [INIT, API, CR, DM, JS] + list(DOCTYPES)
    data = {}
    for p in need:
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        if not p.endswith(".json"):
            with io.open(fp, encoding="utf-8") as f:
                data[p] = f.read()

    if "def edit_message(" in data[API]:
        print("Already applied. Nothing to do.")
        return
    if '"3.58.1"' not in data[INIT]:
        sys.exit("ABORT: not at v3.58.1 — apply earlier patches first.")

    string_edits = [
        (API, API_CONST_OLD, API_CONST_NEW),
        (API, API_PAYLOAD_OLD, API_PAYLOAD_NEW),
        (API, API_MP_OLD, API_MP_NEW),
        (CR, CR_PAYLOAD_OLD, CR_PAYLOAD_NEW),
        (CR, CR_STR_OLD, CR_STR_NEW),
        (CR, CR_ENDPOINT_OLD, CR_ENDPOINT_NEW),
        (DM, DM_FIELDS_OLD, DM_FIELDS_NEW),
        (DM, DM_STR_OLD, DM_STR_NEW),
        (DM, DM_ENDPOINT_OLD, DM_ENDPOINT_NEW),
        (JS, JS_EDITED_HELPER_OLD, JS_EDITED_HELPER_NEW),
        (JS, JS_TEAM_TIME_OLD, JS_TEAM_TIME_NEW),
        (JS, JS_TEAM_BIND_OLD, JS_TEAM_BIND_NEW),
        (JS, JS_ROOM_TIME_OLD, JS_ROOM_TIME_NEW),
        (JS, JS_ROOM_BIND_OLD, JS_ROOM_BIND_NEW),
        (JS, JS_DM_TIME_OLD, JS_DM_TIME_NEW),
        (JS, JS_DM_HANDLE_OLD, JS_DM_HANDLE_NEW),
        (JS, JS_DM_BIND_OLD, JS_DM_BIND_NEW),
        (JS, JS_RT_OLD, JS_RT_NEW),
        (JS, JS_STYLE_OLD, JS_STYLE_NEW),
    ]

    problems = []
    for f, old, _new in string_edits:
        n = data[f].count(old)
        if n != 1:
            problems.append(f"  [{n}] {f}: {old[:48]!r}")
    for p in DOCTYPES:
        ok, res = add_edited_field(p)
        if not ok and res != "already has edited_on":
            problems.append(f"  doctype {p}: {res}")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(string_edits)} string anchors + {len(DOCTYPES)} doctypes matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    # doctypes
    for p in DOCTYPES:
        ok, res = add_edited_field(p)
        if ok:
            with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
                json.dump(res, f, indent=1)
                f.write("\n")
            print(f"  doctype: edited_on -> {os.path.basename(p)}")

    # string edits, grouped per file so each writes once
    out = dict(data)
    for f, old, new in string_edits:
        out[f] = out[f].replace(old, new, 1)

    for f in (API, CR, DM, JS, INIT):
        content = out[f]
        if f == INIT:
            content = content.replace('"3.58.1"', '"3.59.0"')
        with io.open(os.path.join(root, f), "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"  wrote {f}")

    print("wrote __init__.py -> 3.59.0")


if __name__ == "__main__":
    main()
