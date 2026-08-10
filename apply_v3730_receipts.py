#!/usr/bin/env python3
"""Duty Board v3.73.0 — honest delivery + read receipts, WhatsApp grammar.

What existed: group ✓✓ computed from the single last_seen watermark
(so "delivered" was really "read", mislabeled); DMs stored a per-message
`seen` flag (mark_dm_seen) but never showed it; nothing tracked
delivery anywhere.

This adds:
- Chat Seen +last_delivered — advanced whenever a staff member's app
  polls the server (get_board heartbeat, team messages, DM threads):
  app open = messages reached their client, the honest web equivalent
  of "reached the device". Consultants are branched out before the
  touch, so they never pollute the audience.
- GROUP (team chat), on your own messages:
  ✓ grey = sent · ✓✓ grey = delivered to everyone · ✓✓ blue = read by
  everyone, with a read-count beside it and a tooltip listing exactly
  who has Read / Delivered / Pending.
- DM, on your own messages:
  ✓ grey = sent · ✓✓ grey = delivered (peer's app has it, via their
  last_delivered) · ✓✓ blue = read (the existing per-message seen
  flag, at last rendered).

Schema (one field) -> bench migrate && bench build --app duty_board &&
bench restart. Anchored, idempotent. Requires v3.72.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
API = "duty_board/api.py"
DM = "duty_board/dm.py"
CSDT = "duty_board/duty_board/doctype/chat_seen/chat_seen.json"
CHECK_ONLY = "--check" in sys.argv

# --- 1. api.py: the touch helper (before get_messages) ----------------------
H_OLD = '''def get_messages(limit=50, before=None, after=None):
\trequire_staff()'''
H_NEW = '''def _touch_delivered(user):
\t"""Advance the user's delivery watermark: their app is open and
\treceiving, so everything up to now has reached their client."""
\ttry:
\t\tname = frappe.db.get_value("Chat Seen", {"user": user}, "name")
\t\tif name:
\t\t\tfrappe.db.set_value("Chat Seen", name, "last_delivered", frappe.utils.now(), update_modified=False)
\t\telse:
\t\t\tfrappe.get_doc({"doctype": "Chat Seen", "user": user, "last_delivered": frappe.utils.now()}).insert(ignore_permissions=True)
\texcept Exception:
\t\tpass  # receipts must never break a poll


def get_messages(limit=50, before=None, after=None):
\trequire_staff()
\t_touch_delivered(frappe.session.user)'''

# --- 2. api.py: get_board heartbeat touch (staff only, after consultant branch)
B_OLD = '''\tif require_staff_or_consultant():
\t\treturn _consultant_board()
\tnow = now_datetime()
\tsession = frappe.session.user'''
B_NEW = '''\tif require_staff_or_consultant():
\t\treturn _consultant_board()
\tnow = now_datetime()
\tsession = frappe.session.user
\t_touch_delivered(session)'''

# --- 3. api.py: get_messages returns the delivered map too ------------------
M_OLD = '\trows_seen = frappe.get_all("Chat Seen", fields=["user", "last_seen"])'
M_NEW = '\trows_seen = frappe.get_all("Chat Seen", fields=["user", "last_seen", "last_delivered"])'

M2_OLD = '''\tseen = {s.user: str(s.last_seen) for s in rows_seen if s.user in alive}
\treturn {'''
M2_NEW = '''\tseen = {s.user: str(s.last_seen) for s in rows_seen if s.user in alive and s.last_seen}
\tdelivered = {s.user: str(s.last_delivered) for s in rows_seen if s.user in alive and s.last_delivered}
\treturn {'''

M3_OLD = '\t\t"seen": seen,'
M3_NEW = '''\t\t"seen": seen,
\t\t"delivered": delivered,'''

# --- 4. dm.py: thread returns seen flag + peer's delivery watermark ---------
D_OLD = '\t\tfields=["name", "sender", "recipient", "message", "creation", "edited_on"],'
D_NEW = '\t\tfields=["name", "sender", "recipient", "message", "creation", "edited_on", "seen"],'

D2_OLD = '\treturn {"messages": rows, "has_more": has_more}'
D2_NEW = '''\tfrom duty_board.api import _touch_delivered

\t_touch_delivered(frappe.session.user)
\tpeer_delivered = frappe.db.get_value("Chat Seen", {"user": with_user}, "last_delivered")
\treturn {"messages": rows, "has_more": has_more, "peer_delivered": str(peer_delivered) if peer_delivered else None}'''

# --- 5. JS: capture delivered map -------------------------------------------
J1_OLD = '\t\t\t\tthis.seen_map = data.seen || {};'
J1_NEW = '''\t\t\t\tthis.seen_map = data.seen || {};
\t\t\t\tthis.delivered_map = data.delivered || {};'''

# --- 6. JS: group tick logic rewritten --------------------------------------
J2_OLD = '''\t\tconst me = frappe.session.user;
\t\tthis.$list.find(".duty-msg-mine").each((_, el) => {
\t\t\tconst $row = $(el);
\t\t\tconst creation = $row.data("creation");
\t\t\tif (!creation) return;
\t\t\tconst readers = Object.keys(this.seen_map || {}).filter(
\t\t\t\t(u) => u !== me && this.seen_map[u] >= creation
\t\t\t);
\t\t\tlet $seen = $row.find(".duty-msg-seen");
\t\t\tif (!readers.length) {
\t\t\t\t$seen.remove();
\t\t\t\treturn;
\t\t\t}
\t\t\tconst names = readers.map((u) => ((this.name_map || {})[u] || u).split(" ")[0]).join(", ");
\t\t\tif (!$seen.length) {
\t\t\t\t$seen = $(`<span class="duty-msg-seen"></span>`).insertAfter($row.find(".duty-msg-time"));
\t\t\t}
\t\t\t$seen.text(`✓✓ ${readers.length}`).attr("title", __("Seen by {0}", [names]));
\t\t});'''
J2_NEW = '''\t\tconst me = frappe.session.user;
\t\tconst first = (u) => (((this.name_map || {})[u] || u).split(" ")[0]);
\t\tconst audience = [...new Set([...Object.keys(this.seen_map || {}), ...Object.keys(this.delivered_map || {})])].filter((u) => u !== me);
\t\tthis.$list.find(".duty-msg-mine").each((_, el) => {
\t\t\tconst $row = $(el);
\t\t\tconst creation = $row.data("creation");
\t\t\tif (!creation) return;
\t\t\tconst readers = audience.filter((u) => (this.seen_map || {})[u] >= creation);
\t\t\tconst dlv = audience.filter((u) => readers.indexOf(u) < 0 && ((this.delivered_map || {})[u] >= creation || (this.seen_map || {})[u] >= creation));
\t\t\tconst pending = audience.filter((u) => readers.indexOf(u) < 0 && dlv.indexOf(u) < 0);
\t\t\tlet $seen = $row.find(".duty-msg-seen");
\t\t\tif (!$seen.length) {
\t\t\t\t$seen = $(`<span class="duty-msg-seen"></span>`).insertAfter($row.find(".duty-msg-time"));
\t\t\t}
\t\t\tconst allRead = audience.length && readers.length === audience.length;
\t\t\tconst allDlv = audience.length && !pending.length;
\t\t\tconst tick = allRead || allDlv || readers.length || dlv.length ? "✓✓" : "✓";
\t\t\tconst cls = allRead ? "tick-read" : "tick-dlv";
\t\t\tconst parts = [];
\t\t\tif (readers.length) parts.push(`${__("Read")}: ${readers.map(first).join(", ")}`);
\t\t\tif (dlv.length) parts.push(`${__("Delivered")}: ${dlv.map(first).join(", ")}`);
\t\t\tif (pending.length) parts.push(`${__("Pending")}: ${pending.map(first).join(", ")}`);
\t\t\t$seen.removeClass("tick-read tick-dlv").addClass(cls)
\t\t\t\t.text(`${tick}${readers.length ? " " + readers.length : ""}`)
\t\t\t\t.attr("title", parts.join(" · "));
\t\t});'''

# --- 7. JS: capture peer_delivered at BOTH DM thread call sites (count==2) --
J3_OLD = '''\t\t\t\tmethod: "duty_board.dm.get_dm_thread",
\t\t\t\targs: { with_user: user, before: before },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst data = r.message || {};
\t\t\t\t\tconst msgs = data.messages || [];'''
J3_NEW = '''\t\t\t\tmethod: "duty_board.dm.get_dm_thread",
\t\t\t\targs: { with_user: user, before: before },
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst data = r.message || {};
\t\t\t\t\tthis._dm_peer_delivered = data.peer_delivered || null;
\t\t\t\t\tconst msgs = data.messages || [];'''

# --- 8. JS: DM row gets the tick --------------------------------------------
J4_OLD = '''\t\t\t\t<span class="duty-msg-time">${when}${this.edited_tag(m)}</span>${mine && this.can_edit(m.creation) ? ` <a class="duty-dm-edit" data-name="${m.name}" data-text="${frappe.utils.escape_html(m.message || "")}" title="${__("Edit")}">✏</a>` : ""}'''
J4_NEW = '''\t\t\t\t<span class="duty-msg-time">${when}${this.edited_tag(m)}</span>${mine ? (m.seen ? ` <span class="duty-msg-seen tick-read" title="${__("Read")}">✓✓</span>` : this._dm_peer_delivered && m.creation <= this._dm_peer_delivered ? ` <span class="duty-msg-seen tick-dlv" title="${__("Delivered")}">✓✓</span>` : ` <span class="duty-msg-seen tick-dlv" title="${__("Sent")}">✓</span>`) : ""}${mine && this.can_edit(m.creation) ? ` <a class="duty-dm-edit" data-name="${m.name}" data-text="${frappe.utils.escape_html(m.message || "")}" title="${__("Edit")}">✏</a>` : ""}'''

# --- 9. JS: tick colours ------------------------------------------------------
CSS_OLD = '\t\t\t.duty-lv-clash i { font-weight: 400; }'
CSS_NEW = '''\t\t\t.duty-lv-clash i { font-weight: 400; }
\t\t\t.duty-msg-seen.tick-dlv { color: #9aa4a0; }
\t\t\t.duty-msg-seen.tick-read { color: #3B82F6; font-weight: 700; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, API, DM):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def _touch_delivered(" in files[API]:
        print("Already applied. Nothing to do.")
        return
    if '"3.72.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.72.0.")

    checks = [
        (API, H_OLD, "touch helper", 1), (API, B_OLD, "board heartbeat", 1),
        (API, M_OLD, "seen fetch", 1), (API, M2_OLD, "delivered map", 1),
        (API, M3_OLD, "payload", 1), (DM, D_OLD, "dm fields", 1),
        (DM, D2_OLD, "dm return", 1), (JS, J1_OLD, "capture delivered", 1),
        (JS, J2_OLD, "group ticks", 1), (JS, J3_OLD, "dm peer capture", 2),
        (JS, J4_OLD, "dm row tick", 1), (JS, CSS_OLD, "css", 1),
    ]
    problems = [
        f"  [{files[f].count(o)} != {n}] {label}"
        for f, o, label, n in checks
        if files[f].count(o) != n
    ]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(checks)} anchors matched (dm peer capture intentionally x2).")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, CSDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "last_delivered" for fl in dt["fields"]):
        dt["fields"].append({"fieldname": "last_delivered", "fieldtype": "Datetime", "label": "Last Delivered"})
        if "field_order" in dt:
            dt["field_order"].append("last_delivered")
        with io.open(os.path.join(root, CSDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    print("  Chat Seen +last_delivered")

    a = files[API]
    for o, n in [(H_OLD, H_NEW), (B_OLD, B_NEW), (M_OLD, M_NEW), (M2_OLD, M2_NEW), (M3_OLD, M3_NEW)]:
        a = a.replace(o, n, 1)
    with io.open(os.path.join(root, API), "w", encoding="utf-8") as f:
        f.write(a)
    print("  api.py: touch helper, heartbeat, delivered map in payload")

    d = files[DM].replace(D_OLD, D_NEW, 1).replace(D2_OLD, D2_NEW, 1)
    with io.open(os.path.join(root, DM), "w", encoding="utf-8") as f:
        f.write(d)
    print("  dm.py: seen flag + peer watermark in thread")

    js = files[JS]
    js = js.replace(J1_OLD, J1_NEW, 1).replace(J2_OLD, J2_NEW, 1)
    js = js.replace(J3_OLD, J3_NEW, 2)
    js = js.replace(J4_OLD, J4_NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: group tick grammar, DM ticks (both call sites), colours")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.72.0"', '"3.73.0"'))
    print("wrote __init__.py -> 3.73.0")


if __name__ == "__main__":
    main()
