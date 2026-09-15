#!/usr/bin/env python3
"""Duty Board v3.219.0 — ACADEMY HEALTH: seeing a cohort stall before the client does.

Every academy screen on the staff side is per-room: open a room, then the
dialog. So the way we currently learn that a client's cohort has stalled is
that the client tells us — and a client who has paid for seats nobody used does
not usually open with "how can we help". A stalled cohort is a renewal lost
quietly, months before anyone names the reason.

academy.health() reads every active room in one pass and reports what actually
predicts a failed engagement:

  never signed in   people invited who have never logged in at all — almost
                    always a lost invitation, and the cheapest thing to fix
  stalled           assigned a fortnight ago and not one chapter opened
  overdue           past a due date their administrator set
  blocked           out of exam attempts, waiting on an administrator who may
                    not have noticed
  idle seats        seats paid for and not yet assigned to anybody
  waiting           seat orders raised and not yet approved

Rooms are scored and sorted worst first, because the list is only useful if the
room that needs a call is at the top of it. The score weights never-signed-in
and idle seats most heavily: those are the two states where the client has
already paid and received nothing, which is where goodwill is lost fastest.

Reached from the SPA menu and the rail overflow as "Academy health", staff only.

Deploy: apply -> bench build --app duty_board -> clear-cache -> restart.
No schema. Anchored, idempotent. Requires v3.218.1.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
ACAD = "duty_board/academy.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv


PY_OLD = '''# ---------------- nudges: the cadence that replaces a facilitator ----------------'''

PY_NEW = '''# ---------------- academy health: the cross-room view ----------------


def _room_health(room, customer, today_d):
\tfrom duty_board.client_room import _last_signed_in

\tmembers = [
\t\tm.user for m in frappe.get_all(
\t\t\t"Client Room Member", filters={"room": room, "active": 1}, fields=["user"]
\t\t) if m.user
\t]
\tif not members:
\t\treturn None
\tseen = _last_signed_in(members)
\tnever = [u for u in members if not seen.get(u)]

\trecs = frappe.get_all(
\t\t"Duty Training Record",
\t\tfilters={"room": room},
\t\tfields=["name", "module", "trainee", "trainee_name", "status", "due_on", "creation"],
\t)
\tassigned = len(recs)
\tcomplete = sum(1 for r in recs if r.status == "Completed")
\toverdue = stalled = blocked = 0
\topen_recs = [r for r in recs if r.status != "Completed"]
\tfor r in open_recs:
\t\tif r.due_on and getdate(r.due_on) < today_d:
\t\t\toverdue += 1
\t\tif (today_d - getdate(r.creation)).days >= DORMANT_AFTER_DAYS and not frappe.db.exists(
\t\t\t"Duty Lesson Progress", {"user": r.trainee, "module": r.module}
\t\t):
\t\t\tstalled += 1
\tfor r in open_recs:
\t\ttry:
\t\t\tfrom duty_board.client_room import _quiz_state

\t\t\tst = _quiz_state(r.module, r.trainee, r.name)
\t\t\tif not st["passed"] and st["attempts_left"] == 0:
\t\t\t\tblocked += 1
\t\texcept Exception:
\t\t\tcontinue

\t# seats bought and not yet put to use
\tidle = 0
\tfor e in frappe.get_all(
\t\t"Duty Academy Entitlement",
\t\tfilters={"room": room, "status": "Active"}, fields=["track", "seats", "expires_on"],
\t):
\t\tif e.expires_on and getdate(e.expires_on) < today_d:
\t\t\tcontinue
\t\tidle += max(cint(e.seats) - seats_used(room, e.track), 0)

\twaiting = frappe.get_all(
\t\t"Duty Academy Order", filters={"room": room, "status": "Requested"},
\t\tfields=["name", "total"],
\t)

\t# worst first: the two states where a client has paid and received nothing
\t# weigh heaviest, because that is where goodwill goes fastest
\tscore = len(never) * 4 + idle * 4 + blocked * 3 + stalled * 2 + overdue
\treturn {
\t\t"room": room,
\t\t"customer": customer or room,
\t\t"members": len(members),
\t\t"never": len(never),
\t\t"never_names": [frappe.utils.get_fullname(u) for u in never[:6]],
\t\t"assigned": assigned,
\t\t"complete": complete,
\t\t"rate": round(complete * 100.0 / assigned) if assigned else None,
\t\t"overdue": overdue,
\t\t"stalled": stalled,
\t\t"blocked": blocked,
\t\t"idle_seats": idle,
\t\t"waiting_orders": len(waiting),
\t\t"waiting_value": sum(flt(w.total) for w in waiting),
\t\t"score": score,
\t}


@frappe.whitelist()
def health():
\t"""Every active room's academy standing, worst first."""
\t_staff_only()
\ttoday_d = getdate(today())
\tout = []
\tfor r in frappe.get_all(
\t\t"Client Room", filters={"status": "Active"}, fields=["name", "customer"]
\t):
\t\ttry:
\t\t\trow = _room_health(r.name, r.customer, today_d)
\t\texcept Exception:
\t\t\tfrappe.log_error(frappe.get_traceback(), "duty_board academy health")
\t\t\tcontinue
\t\tif row:
\t\t\tout.append(row)
\tout.sort(key=lambda x: (-x["score"], x["customer"]))
\ttotals = {
\t\t"rooms": len(out),
\t\t"attention": sum(1 for x in out if x["score"]),
\t\t"never": sum(x["never"] for x in out),
\t\t"stalled": sum(x["stalled"] for x in out),
\t\t"blocked": sum(x["blocked"] for x in out),
\t\t"idle_seats": sum(x["idle_seats"] for x in out),
\t\t"waiting_orders": sum(x["waiting_orders"] for x in out),
\t}
\treturn {"rooms": out, "totals": totals}


# ---------------- nudges: the cadence that replaces a facilitator ----------------'''


JS_OLD = '''\t\t\tpage.add_menu_item(__("🎓 Team training"), () => board.team_training_dialog());'''
JS_NEW = '''\t\t\tpage.add_menu_item(__("🎓 Team training"), () => board.team_training_dialog());
\t\t\tpage.add_menu_item(__("\\u{1F4C8} Academy health"), () => board.academy_health_dialog());
\t\t\tboard._more_extra = board._more_extra || [];
\t\t\tboard._more_extra.push({ icon: "\\u{1F4C8}", label: __("Academy health"), go: () => board.academy_health_dialog() });'''

JS_DLG_OLD = '''\tacademy_orders_dialog() {'''
JS_DLG_NEW = '''\tacademy_health_css() {\n\t\tif (document.getElementById("duty-ah-css")) return;\n\t\tconst s = document.createElement("style");\n\t\ts.id = "duty-ah-css";\n\t\ts.textContent = `\n\t\t\t.duty-ah-top { display: flex; flex-wrap: wrap; gap: 8px; }\n\t\t\t.duty-ah-chip { background: #F4F7F6; border-radius: 8px; padding: 6px 11px; font-size: 12px; color: #6B7C77; }\n\t\t\t.duty-ah-chip b { font-size: 15px; color: #0A473F; margin-right: 4px; }\n\t\t\t.duty-ah-chip.warn { background: #FFF7E6; color: #7A5312; }\n\t\t\t.duty-ah-chip.warn b { color: #B27409; }\n\t\t\t.duty-ah-hot td { background: #FFFCF5; }\n\t\t\t.duty-ah-go { cursor: pointer; font-weight: 600; }`;\n\t\tdocument.head.appendChild(s);\n\t}\n\n\tacademy_health_dialog() {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst d = new frappe.ui.Dialog({ title: `\\u{1F4C8} ${__("Academy health")}`, size: "extra-large" });
\t\td.set_primary_action(`\\u{1F9FE} ${__("Seat orders")}`, () => { d.hide(); this.academy_orders_dialog(); });
\t\tfrappe.call({
\t\t\tmethod: "duty_board.academy.health",
\t\t\tcallback: (r) => {
\t\t\t\tconst res = r.message || { rooms: [], totals: {} };
\t\t\t\tconst t = res.totals;
\t\t\t\tconst chip = (n, label, warn) =>
\t\t\t\t\t`<span class="duty-ah-chip${warn && n ? " warn" : ""}"><b>${n}</b> ${label}</span>`;
\t\t\t\t$(d.body).html(`
\t\t\t\t\t<div class="duty-ah-top">
\t\t\t\t\t\t${chip(t.rooms || 0, __("rooms"))}
\t\t\t\t\t\t${chip(t.attention || 0, __("need attention"), 1)}
\t\t\t\t\t\t${chip(t.never || 0, __("never signed in"), 1)}
\t\t\t\t\t\t${chip(t.stalled || 0, __("not started"), 1)}
\t\t\t\t\t\t${chip(t.blocked || 0, __("blocked"), 1)}
\t\t\t\t\t\t${chip(t.idle_seats || 0, __("idle seats"), 1)}
\t\t\t\t\t\t${chip(t.waiting_orders || 0, __("orders waiting"), 1)}
\t\t\t\t\t</div>
\t\t\t\t\t${res.rooms.length ? `<table class="table table-sm" style="font-size:12px;margin-top:12px">
\t\t\t\t\t\t<tr><th>${__("Customer")}</th><th>${__("People")}</th><th>${__("Assigned")}</th>
\t\t\t\t\t\t<th>${__("Complete")}</th><th>${__("Never in")}</th><th>${__("Not started")}</th>
\t\t\t\t\t\t<th>${__("Overdue")}</th><th>${__("Blocked")}</th><th>${__("Idle seats")}</th><th>${__("Waiting")}</th></tr>
\t\t\t\t\t\t${res.rooms.map((x) => `<tr class="${x.score ? "duty-ah-hot" : ""}">
\t\t\t\t\t\t\t<td><a class="duty-ah-go" data-r="${esc(x.room)}">${esc(x.customer)}</a></td>
\t\t\t\t\t\t\t<td>${x.members}</td><td>${x.assigned}</td>
\t\t\t\t\t\t\t<td>${x.complete}${x.rate === null ? "" : ` (${x.rate}%)`}</td>
\t\t\t\t\t\t\t<td>${x.never ? `<b title="${esc((x.never_names || []).join(", "))}">${x.never}</b>` : "\\u2014"}</td>
\t\t\t\t\t\t\t<td>${x.stalled || "\\u2014"}</td><td>${x.overdue || "\\u2014"}</td>
\t\t\t\t\t\t\t<td>${x.blocked ? `<b>${x.blocked}</b>` : "\\u2014"}</td>
\t\t\t\t\t\t\t<td>${x.idle_seats ? `<b>${x.idle_seats}</b>` : "\\u2014"}</td>
\t\t\t\t\t\t\t<td>${x.waiting_orders || "\\u2014"}</td></tr>`).join("")}
\t\t\t\t\t</table>
\t\t\t\t\t<p class="text-muted" style="font-size:11.5px;margin-top:10px">${__("Sorted worst first. Never-signed-in and idle seats weigh heaviest — those are the states where a client has paid and received nothing. Hover a never-signed-in count to see who.")}</p>`
\t\t\t\t\t\t: `<div class="text-muted">${__("No active rooms with members.")}</div>`}
\t\t\t\t`);
\t\t\t\t$(d.body).find(".duty-ah-go").on("click", (e) => {
\t\t\t\t\tconst room = $(e.currentTarget).data("r");
\t\t\t\t\td.hide();
\t\t\t\t\tfrappe.set_route("Form", "Client Room", room);
\t\t\t\t});
\t\t\t},
\t\t});
\t\td.show();
\t}

\tacademy_orders_dialog() {'''

CSS_MARK = "/* duty_board academy health */"
CSS_JS_OLD = '''\tacademy_health_dialog() {'''
CSS_JS_NEW = '''\tacademy_health_css() {
\t\tif (document.getElementById("duty-ah-css")) return;
\t\tconst s = document.createElement("style");
\t\ts.id = "duty-ah-css";
\t\ts.textContent = `
\t\t\t.duty-ah-top { display: flex; flex-wrap: wrap; gap: 8px; }
\t\t\t.duty-ah-chip { background: #F4F7F6; border-radius: 8px; padding: 6px 11px; font-size: 12px; color: #6B7C77; }
\t\t\t.duty-ah-chip b { font-size: 15px; color: #0A473F; margin-right: 4px; }
\t\t\t.duty-ah-chip.warn { background: #FFF7E6; color: #7A5312; }
\t\t\t.duty-ah-chip.warn b { color: #B27409; }
\t\t\t.duty-ah-hot td { background: #FFFCF5; }
\t\t\t.duty-ah-go { cursor: pointer; font-weight: 600; }`;
\t\tdocument.head.appendChild(s);
\t}

\tacademy_health_dialog() {
\t\tthis.academy_health_css();'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, ACAD, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def academy_health_dialog" in files[JS] or "def health(" in files[ACAD]:
        print("Already applied. Nothing to do.")
        return
    if '"3.218.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.218.1.")

    edits = [
        (ACAD, PY_OLD, PY_NEW, "health endpoint"),
        (JS, JS_OLD, JS_NEW, "menu entry"),
        (JS, JS_DLG_OLD, JS_DLG_NEW + "\n\t\tthis.academy_health_css();" if False else JS_DLG_NEW, "health dialog"),
    ]
    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (ACAD, JS):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  academy.py: cross-room health")
    print("  duty_board.js: Academy health dialog + menu")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.218.1"', '"3.219.0"'))
    print("wrote __init__.py -> 3.219.0")


if __name__ == "__main__":
    main()
