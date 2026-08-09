#!/usr/bin/env python3
"""Duty Board v3.68.3 — review item 3: meeting confirm reflects instantly.

Reported: clicking Confirm on a meeting request appears to do nothing —
the meeting IS confirmed server-side, but the screen doesn't show it
until a manual reload. Both staff confirm surfaces relied entirely on a
background refresh to repaint; when that refresh goes stale, the user
sees nothing.

Fix — optimistic UI on both surfaces:
- Me face (requests block): on server ok, the clicked row's buttons are
  replaced inline with "✅ Confirmed" immediately, then refresh_me runs
  as before.
- Client-room meetings: on server ok, the row's Pending pill and action
  links flip to "✅ Confirmed" immediately; render_client_room still
  runs with the returned payload, with a load_client_room fallback if
  the payload is ever empty.

The user always sees the state change at the click, regardless of what
the background refresh does.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.68.2.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. Me face: optimistic flip --------------------------------------------
ME_OLD = '''this.$me.find(".duty-req-ok").on("click", (e) =>
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.client_room.confirm_meeting",
\t\t\t\targs: { id: $(e.currentTarget).data("id") },
\t\t\t\tcallback: () => {
\t\t\t\t\tfrappe.show_alert({ message: __("Meeting confirmed"), indicator: "green" });
\t\t\t\t\tthis.refresh_me((this._me_data || {}).month);
\t\t\t\t},
\t\t\t})
\t\t);'''
ME_NEW = '''this.$me.find(".duty-req-ok").on("click", (e) => {
\t\t\tconst $row = $(e.currentTarget).closest(".duty-req-row");
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.client_room.confirm_meeting",
\t\t\t\targs: { id: $(e.currentTarget).data("id") },
\t\t\t\tcallback: () => {
\t\t\t\t\t// Optimistic: show the result at the click, before any refresh.
\t\t\t\t\t$row.find(".duty-req-btns").html(`<span style="color:#0E8A63;font-weight:700">✅ ${__("Confirmed")}</span>`);
\t\t\t\t\tfrappe.show_alert({ message: __("Meeting confirmed"), indicator: "green" });
\t\t\t\t\tthis.refresh_me((this._me_data || {}).month);
\t\t\t\t},
\t\t\t});
\t\t});'''

# --- 2. Client-room face: optimistic flip + fallback reload -----------------
CR_OLD = '''\t\t\t$mt.find(".duty-cr-mconfirm").on("click", (e) =>
\t\t\t\tfrappe.call({
\t\t\t\t\tmethod: "duty_board.client_room.confirm_meeting",
\t\t\t\t\targs: { id: $(e.currentTarget).data("id") },
\t\t\t\t\tcallback: (r) => r.message && this.render_client_room(r.message),
\t\t\t\t})
\t\t\t);'''
CR_NEW = '''\t\t\t$mt.find(".duty-cr-mconfirm").on("click", (e) => {
\t\t\t\tconst $row = $(e.currentTarget).closest("div");
\t\t\t\tconst roomName = x.name;
\t\t\t\tfrappe.call({
\t\t\t\t\tmethod: "duty_board.client_room.confirm_meeting",
\t\t\t\t\targs: { id: $(e.currentTarget).data("id") },
\t\t\t\t\tcallback: (r) => {
\t\t\t\t\t\t// Optimistic: flip this row now; full re-render follows.
\t\t\t\t\t\t$row.find(".duty-cr-mconfirm, .duty-cr-msuggest, .duty-cr-mdecline").remove();
\t\t\t\t\t\t$row.find(".pill").removeClass("queued").addClass("done").text("✅ " + __("Confirmed"));
\t\t\t\t\t\t$row.append(`<span style="color:#0E8A63;font-weight:700;font-size:12px"> ✅ ${__("Confirmed")}</span>`);
\t\t\t\t\t\tif (r.message) this.render_client_room(r.message);
\t\t\t\t\t\telse this.load_client_room(roomName);
\t\t\t\t\t},
\t\t\t\t});
\t\t\t});'''

EDITS = [
    ("me-face optimistic confirm", ME_OLD, ME_NEW),
    ("room-face optimistic confirm", CR_OLD, CR_NEW),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "Optimistic: show the result at the click" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.68.2"' not in init:
        sys.exit("ABORT: not at v3.68.2.")

    problems = [f"  [{js.count(o)}] {label}" for label, o, _ in EDITS if js.count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(EDITS)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for label, old, new in EDITS:
        js = js.replace(old, new, 1)
        print(f"  applied: {label}")
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.68.2"', '"3.68.3"'))
    print("wrote __init__.py -> 3.68.3")


if __name__ == "__main__":
    main()
