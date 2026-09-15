#!/usr/bin/env python3
"""Duty Board v3.211.0 — THE CLIENT TRAINING ADMINISTRATOR.

Self-serve removes the facilitator but, until now, kept us as the registrar:
every enrolment ran from our SPA. At 500 learners that is us doing a client's
HR admin forever, which is exactly the cost that made self-serve attractive in
the first place. This hands that work back across the membrane.

The room administrator (Client Room Member.is_admin — the person who already
approves joins and promotes colleagues) gains a training panel on the portal:

  - a live dashboard: people, assigned, in progress, complete, completion rate,
    overdue
  - the roster with each person's progress and what is outstanding
  - bulk assignment of a certification track to selected colleagues, with a due
    date, without touching us
  - due dates on training records, and a nudge that notifies a learner directly

Reusing is_admin is a deliberate call rather than a shortcut: that person is
already the client's designated administrator, and a second flag would need a
second promotion workflow. If a client ever needs HR separated from the project
contact, a distinct training_admin field is a small follow-up.

  Duty Training Record: +due_on (Date). Overdue = due_on past and not Completed.

  client_training_admin_home returns {"admin": 0} rather than throwing for
  ordinary members, so the portal can call it unconditionally and simply not
  paint the panel. Every mutation throws.

Assignment is guarded exactly as the staff path is: the track must be active,
client-audience, and within the room's products, and the target must be an
active member of the caller's own room. An administrator can arm their own
people and nobody else's.

Deploy: apply -> bench migrate (new field) -> bench build --app duty_board ->
clear-cache + clear-website-cache -> restart. Anchored, idempotent.
Requires v3.210.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
TRDT = "duty_board/duty_board/doctype/duty_training_record/duty_training_record.json"
CHECK_ONLY = "--check" in sys.argv


PY_OLD = '''# ---------------- academy, staff face: consultant training ----------------'''

PY_NEW = '''# ---------------- academy, client face: the training administrator ----------------


def _require_room_admin():
\t"""The client's own administrator. Same person who approves joins and
\tpromotes colleagues — see room_member_admin. Mutations only."""
\troom = _client_room()
\tif not cint(
\t\tfrappe.db.get_value(
\t\t\t"Client Room Member",
\t\t\t{"room": room.name, "user": frappe.session.user, "active": 1},
\t\t\t"is_admin",
\t\t)
\t):
\t\tfrappe.throw(_("Only your organisation's administrator can do that."), frappe.PermissionError)
\treturn room


def _admin_rows(room):
\tmembers = frappe.get_all(
\t\t"Client Room Member",
\t\tfilters={"room": room.name, "active": 1},
\t\tfields=["user"],
\t)
\tusers = [m.user for m in members if m.user]
\trecs = frappe.get_all(
\t\t"Duty Training Record",
\t\tfilters={"room": room.name},
\t\tfields=["name", "module", "trainee", "trainee_name", "status", "due_on", "completed_on"],
\t) if users else []
\tmods = list({r.module for r in recs})
\ttitles = {
\t\tm.name: m.title
\t\tfor m in frappe.get_all(
\t\t\t"Duty Training Module", filters={"name": ["in", mods or [""]]},
\t\t\tfields=["name", "title"],
\t\t)
\t}
\ttoday_d = getdate(today())
\tfor r in recs:
\t\tr["title"] = titles.get(r.module, r.module)
\t\tr["overdue"] = bool(
\t\t\tr.due_on and r.status != "Completed" and getdate(r.due_on) < today_d
\t\t)
\treturn users, recs


@frappe.whitelist()
def client_training_admin_home():
\t"""Dashboard for the client's administrator. Returns {"admin": 0} for an
\tordinary member rather than throwing, so the portal can ask without
\tknowing in advance."""
\troom = _client_room()
\tis_admin = cint(
\t\tfrappe.db.get_value(
\t\t\t"Client Room Member",
\t\t\t{"room": room.name, "user": frappe.session.user, "active": 1},
\t\t\t"is_admin",
\t\t)
\t)
\tif not is_admin:
\t\treturn {"admin": 0}
\tusers, recs = _admin_rows(room)
\tby_user = {}
\tfor r in recs:
\t\tby_user.setdefault(r.trainee, []).append(r)
\tpeople = []
\tfor u in users:
\t\trows = by_user.get(u, [])
\t\tpeople.append({
\t\t\t"user": u,
\t\t\t"full_name": frappe.utils.get_fullname(u),
\t\t\t"assigned": len(rows),
\t\t\t"complete": sum(1 for r in rows if r.status == "Completed"),
\t\t\t"overdue": sum(1 for r in rows if r["overdue"]),
\t\t\t"courses": [
\t\t\t\t{
\t\t\t\t\t"record": r.name, "title": r["title"], "status": r.status,
\t\t\t\t\t"due_on": str(r.due_on) if r.due_on else None,
\t\t\t\t\t"overdue": r["overdue"],
\t\t\t\t}
\t\t\t\tfor r in sorted(rows, key=lambda x: x["title"])
\t\t\t],
\t\t})
\tpeople.sort(key=lambda p: (-p["overdue"], -(p["assigned"] - p["complete"]), p["full_name"]))
\tassigned = len(recs)
\tcomplete = sum(1 for r in recs if r.status == "Completed")
\treturn {
\t\t"admin": 1,
\t\t"stats": {
\t\t\t"people": len(users),
\t\t\t"assigned": assigned,
\t\t\t"in_progress": sum(1 for r in recs if r.status in ("Reading", "Assigned")),
\t\t\t"complete": complete,
\t\t\t"rate": round(complete * 100 / assigned) if assigned else None,
\t\t\t"overdue": sum(1 for r in recs if r["overdue"]),
\t\t},
\t\t"people": people,
\t}


@frappe.whitelist()
def client_training_admin_options():
\t"""Who can be assigned, and what to. Tracks are filtered to the room's
\tproducts by the same rule the staff assign dialog uses."""
\troom = _require_room_admin()
\tprods = _room_products(room)
\ttracks = []
\tfor t in frappe.get_all(
\t\t"Duty Certification Track",
\t\tfilters={"active": 1, "audience": "Client"},
\t\tfields=["name", "title", "product"],
\t\torder_by="product asc, title asc",
\t):
\t\tif (t.product or "").strip().lower() not in prods:
\t\t\tcontinue
\t\tn = frappe.db.count("Duty Certification Track Module", {"parent": t.name})
\t\tif n:
\t\t\ttracks.append({"name": t.name, "title": t.title, "product": t.product, "modules": n})
\tpeople = [
\t\t{"user": m.user, "full_name": frappe.utils.get_fullname(m.user)}
\t\tfor m in frappe.get_all(
\t\t\t"Client Room Member",
\t\t\tfilters={"room": room.name, "active": 1},
\t\t\tfields=["user"],
\t\t)
\t\tif m.user
\t]
\tpeople.sort(key=lambda p: p["full_name"])
\treturn {"tracks": tracks, "people": people}


@frappe.whitelist()
def client_training_admin_assign(users, track, due_on=None):
\t"""Bulk-assign a track to colleagues. Existing records are left alone and
\tnot duplicated; only the due date is applied to them."""
\troom = _require_room_admin()
\tif isinstance(users, str):
\t\tusers = json.loads(users)
\tif not users:
\t\tfrappe.throw(_("Choose at least one person."))
\tt = frappe.db.get_value(
\t\t"Duty Certification Track", track, ["title", "product", "audience", "active"], as_dict=True
\t)
\tif not t or not cint(t.active) or t.audience != "Client":
\t\tfrappe.throw(_("Not found."))
\tif (t.product or "").strip().lower() not in _room_products(room):
\t\tfrappe.throw(_("That track is not part of your subscription."))
\tmods = frappe.get_all(
\t\t"Duty Certification Track Module", filters={"parent": track}, pluck="module", order_by="idx asc"
\t)
\tif not mods:
\t\tfrappe.throw(_("That track has no courses yet."))
\tcreated, existing = 0, 0
\tfor u in users:
\t\tmade = 0
\t\tif not frappe.db.exists("Client Room Member", {"room": room.name, "user": u, "active": 1}):
\t\t\tfrappe.throw(_("{0} is not an active member of your room.").format(u))
\t\tfor m in mods:
\t\t\tname = frappe.db.get_value(
\t\t\t\t"Duty Training Record", {"room": room.name, "module": m, "trainee": u}, "name"
\t\t\t)
\t\t\tif name:
\t\t\t\tif due_on:
\t\t\t\t\tfrappe.db.set_value("Duty Training Record", name, "due_on", due_on, update_modified=False)
\t\t\t\texisting += 1
\t\t\t\tcontinue
\t\t\tfrappe.get_doc({
\t\t\t\t"doctype": "Duty Training Record",
\t\t\t\t"room": room.name,
\t\t\t\t"module": m,
\t\t\t\t"trainee": u,
\t\t\t\t"trainee_name": frappe.utils.get_fullname(u),
\t\t\t\t"status": "Assigned",
\t\t\t\t"due_on": due_on or None,
\t\t\t}).insert(ignore_permissions=True)
\t\t\tcreated += 1
\t\t\tmade += 1
\t\tif made:
\t\t\ttry:
\t\t\t\tfrom duty_board.api import _notify_user

\t\t\t\t_notify_user(u, _("🎓 New training assigned"), t.title)
\t\t\texcept Exception:
\t\t\t\tpass
\tfrappe.db.commit()
\treturn {"created": created, "existing": existing, "home": client_training_admin_home()}


@frappe.whitelist()
def client_training_admin_due(record, due_on=None):
\troom = _require_room_admin()
\tif frappe.db.get_value("Duty Training Record", record, "room") != room.name:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\tfrappe.db.set_value("Duty Training Record", record, "due_on", due_on or None, update_modified=False)
\tfrappe.db.commit()
\treturn client_training_admin_home()


@frappe.whitelist()
def client_training_admin_nudge(user):
\t"""A reminder from their own administrator, not from us."""
\troom = _require_room_admin()
\tif not frappe.db.exists("Client Room Member", {"room": room.name, "user": user, "active": 1}):
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\topen_rows = frappe.get_all(
\t\t"Duty Training Record",
\t\tfilters={"room": room.name, "trainee": user, "status": ["!=", "Completed"]},
\t\tfields=["module"],
\t)
\tif not open_rows:
\t\tfrappe.throw(_("They have nothing outstanding."))
\ttry:
\t\tfrom duty_board.api import _notify_user

\t\t_notify_user(
\t\t\tuser,
\t\t\t_("🎓 Training reminder"),
\t\t\t_("{0} course(s) still outstanding — {1} asked us to remind you.").format(
\t\t\t\tlen(open_rows), frappe.utils.get_fullname(frappe.session.user)
\t\t\t),
\t\t)
\texcept Exception:
\t\tpass
\treturn {"nudged": len(open_rows)}


# ---------------- academy, staff face: consultant training ----------------'''


# --- portal: the admin panel ----------------------------------------------
P_HOST_OLD = '''\t\t<div id="acad"><span class="muted">No training records yet.</span></div>'''
P_HOST_NEW = '''\t\t<div id="adminhost"></div>
\t\t<div id="acad"><span class="muted">No training records yet.</span></div>'''

P_CALL_OLD = '''function loadTraining() {
\tstopBeat();
\tacadFocus("");'''
P_CALL_NEW = '''function loadTraining() {
\tstopBeat();
\tacadFocus("");
\tloadAdminTraining();'''

P_FN_OLD = '''function acadFocus(mode) {'''

P_FN_NEW = '''function loadAdminTraining() {
\t/* Painted only for the room administrator. The endpoint answers
\t   {admin:0} for everyone else rather than erroring, so this can be called
\t   unconditionally on every training load. */
\tconst host = document.getElementById("adminhost");
\tif (!host) return;
\tapi("client_training_admin_home")
\t\t.then((h) => {
\t\t\tif (!h || !h.admin) { host.innerHTML = ""; return; }
\t\t\twindow._adm = h;
\t\t\tconst s = h.stats;
\t\t\tconst tile = (n, l, warn) =>
\t\t\t\t`<div class="atile${warn ? " warn" : ""}"><b>${n}</b><span>${l}</span></div>`;
\t\t\thost.innerHTML = `
\t\t\t\t<div class="admwrap">
\t\t\t\t\t<div class="admhead">
\t\t\t\t\t\t<div><b>Team training</b><span class="muted"> \u00b7 you administer this for your organisation</span></div>
\t\t\t\t\t\t<button id="admassign">\uFF0B Assign training</button>
\t\t\t\t\t</div>
\t\t\t\t\t<div class="atiles">
\t\t\t\t\t\t${tile(s.people, "people")}
\t\t\t\t\t\t${tile(s.assigned, "assigned")}
\t\t\t\t\t\t${tile(s.complete, "complete")}
\t\t\t\t\t\t${tile(s.rate === null ? "\u2014" : s.rate + "%", "completion")}
\t\t\t\t\t\t${tile(s.overdue, "overdue", s.overdue > 0)}
\t\t\t\t\t</div>
\t\t\t\t\t${h.people.length
\t\t\t\t\t\t? h.people.map((p) => `
\t\t\t\t\t\t<div class="admrow">
\t\t\t\t\t\t\t<div class="admwho">
\t\t\t\t\t\t\t\t<b>${esc(p.full_name)}</b>
\t\t\t\t\t\t\t\t<span class="muted">${p.assigned ? `${p.complete} of ${p.assigned} complete` : "nothing assigned"}${p.overdue ? ` \u00b7 <span class="admlate">${p.overdue} overdue</span>` : ""}</span>
\t\t\t\t\t\t\t</div>
\t\t\t\t\t\t\t<div class="admbar"><i style="width:${p.assigned ? Math.round((p.complete / p.assigned) * 100) : 0}%"></i></div>
\t\t\t\t\t\t\t${p.assigned > p.complete ? `<a class="admnudge" data-u="${esc(p.user)}">Remind</a>` : ""}
\t\t\t\t\t\t</div>`).join("")
\t\t\t\t\t\t: `<span class="muted">Nobody is enrolled yet.</span>`}
\t\t\t\t</div>`;
\t\t\tdocument.getElementById("admassign").onclick = openAssign;
\t\t\thost.querySelectorAll(".admnudge").forEach((a) =>
\t\t\t\ta.addEventListener("click", () => {
\t\t\t\t\ta.textContent = "\u2026";
\t\t\t\t\tapi("client_training_admin_nudge", { user: a.getAttribute("data-u") })
\t\t\t\t\t\t.then(() => { a.textContent = "Reminded"; a.classList.add("done"); })
\t\t\t\t\t\t.catch((e) => { a.textContent = "Remind"; fail(e); });
\t\t\t\t}));
\t\t})
\t\t.catch(() => { host.innerHTML = ""; });
}
function openAssign() {
\tconst host = document.getElementById("adminhost");
\tapi("client_training_admin_options")
\t\t.then((o) => {
\t\t\tif (!o.tracks.length) {
\t\t\t\talert("No certification tracks are available on your subscription yet.");
\t\t\t\treturn;
\t\t\t}
\t\t\thost.innerHTML = `
\t\t\t\t<div class="admwrap">
\t\t\t\t\t<div class="admhead"><div><b>Assign training</b></div>
\t\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="loadAdminTraining()">Cancel</button></div>
\t\t\t\t\t<div class="admfield"><label>Track</label>
\t\t\t\t\t\t<select id="admtrack">${o.tracks.map((t) => `<option value="${esc(t.name)}">${esc(t.title)} \u00b7 ${t.modules} course${t.modules === 1 ? "" : "s"}</option>`).join("")}</select></div>
\t\t\t\t\t<div class="admfield"><label>Due date <span class="muted">(optional)</span></label>
\t\t\t\t\t\t<input type="date" id="admdue"></div>
\t\t\t\t\t<div class="admfield"><label>People</label>
\t\t\t\t\t\t<div class="admpeople">${o.people.map((p) => `<label class="admchk"><input type="checkbox" value="${esc(p.user)}"> ${esc(p.full_name)}</label>`).join("")}</div></div>
\t\t\t\t\t<button id="admgo">Assign</button>
\t\t\t\t</div>`;
\t\t\tdocument.getElementById("admgo").onclick = () => {
\t\t\t\tconst users = Array.from(host.querySelectorAll(".admpeople input:checked")).map((i) => i.value);
\t\t\t\tif (!users.length) return alert("Choose at least one person.");
\t\t\t\tdocument.getElementById("admgo").disabled = true;
\t\t\t\tapi("client_training_admin_assign", {
\t\t\t\t\tusers: JSON.stringify(users),
\t\t\t\t\ttrack: document.getElementById("admtrack").value,
\t\t\t\t\tdue_on: document.getElementById("admdue").value || null,
\t\t\t\t})
\t\t\t\t\t.then((r) => { loadAdminTraining(); loadTraining(); })
\t\t\t\t\t.catch((e) => { document.getElementById("admgo").disabled = false; fail(e); });
\t\t\t};
\t\t})
\t\t.catch(fail);
}
function acadFocus(mode) {'''

CSS_OLD = '''\t/* ---- the reading room ---- */
\tbody[data-acad] #mycerts, body[data-acad] #mytracks { display: none !important; }'''

CSS_NEW = '''\t/* ---- client training administrator ---- */
\t.admwrap { border: 1px solid #E4EAE8; border-radius: 14px; padding: 16px 18px; margin-bottom: 20px; background: #fff; }
\t.admhead { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
\t.admhead > div { flex: 1; min-width: 160px; font-size: 14px; }
\t.atiles { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
\t.atile { flex: 1; min-width: 92px; background: #F4F7F6; border-radius: 10px; padding: 9px 12px; }
\t.atile b { display: block; font-size: 21px; color: var(--brand-700); line-height: 1.2; }
\t.atile span { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6B7C77; }
\t.atile.warn { background: #FFF7E6; }
\t.atile.warn b { color: #B27409; }
\t.admrow { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-top: 1px solid #F0F4F2; flex-wrap: wrap; }
\t.admwho { flex: 1; min-width: 150px; font-size: 13.5px; }
\t.admwho span { display: block; font-size: 12px; }
\t.admlate { color: #B27409; font-weight: 700; }
\t.admbar { flex: 0 0 110px; height: 6px; border-radius: 99px; background: #E9EFEC; overflow: hidden; }
\t.admbar i { display: block; height: 100%; background: var(--brand); }
\t.admnudge { font-size: 12px; font-weight: 700; color: var(--brand-700); cursor: pointer; }
\t.admnudge.done { color: #6B7C77; cursor: default; }
\t.admfield { margin-bottom: 12px; font-size: 13px; }
\t.admfield label { display: block; font-weight: 700; margin-bottom: 4px; }
\t.admfield select, .admfield input[type="date"] { width: 100%; max-width: 340px; padding: 8px 10px;
\t\tborder: 1px solid #DCE4E1; border-radius: 9px; font-size: 14px; background: #fff; }
\t.admpeople { display: flex; flex-wrap: wrap; gap: 6px 16px; }
\t.admchk { font-weight: 400; font-size: 13.5px; display: flex; gap: 6px; align-items: center; margin: 0; }

\t/* ---- the reading room ---- */
\tbody[data-acad] #mycerts, body[data-acad] #mytracks, body[data-acad] #adminhost { display: none !important; }'''


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = json.load(f)
    added = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        added = True
    if added:
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_training_admin_home(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.210.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.210.0.")

    edits = [
        (CR, PY_OLD, PY_NEW, "training admin endpoints"),
        (PORTAL, P_HOST_OLD, P_HOST_NEW, "admin host div"),
        (PORTAL, P_CALL_OLD, P_CALL_NEW, "loadTraining calls admin"),
        (PORTAL, P_FN_OLD, P_FN_NEW, "admin panel + assign"),
        (PORTAL, CSS_OLD, CSS_NEW, "admin css + focus hide"),
    ]

    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, TRDT), [
        {"fieldname": "due_on", "fieldtype": "Date", "label": "Due On"},
    ])
    print("  Duty Training Record: +due_on")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: client training administrator endpoints")
    print("  portal.html: dashboard, assignment, nudges, css")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.210.0"', '"3.211.0"'))
    print("wrote __init__.py -> 3.211.0")


if __name__ == "__main__":
    main()
