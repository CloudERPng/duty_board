#!/usr/bin/env python3
"""Duty Board v3.216.0 — THE ROSTER: clients onboard their own people.

v3.211.0 handed assignment across the membrane and v3.213.0 handed the
catalogue over, but membership stayed with us: add_member and remove_member are
both _staff_only(), and the join flow needs a staff approval. So a client buys
twenty-five seats and then needs us to put twenty-five people in the room, one
at a time. We fixed the registrar problem for assignment and left it standing at
the step that comes first.

The administrator can now:
  - invite colleagues in bulk, pasting addresses however they have them
  - deactivate a leaver, which ends access without touching their history
  - reactivate a returner, who finds their progress exactly where it was

Deactivation is not deletion. Training records, attempts and certificates all
survive, because a certificate records what somebody demonstrated on a date and
staff turnover does not make that untrue. A returning employee resumes; an
auditor can still see who passed what.

This is the largest trust extension in the academy so far — a client can now
create login accounts on our system — so the guards are deliberately tight:

  - administrator-only, resolved from their own room membership as always
  - 50 addresses per call, and malformed ones are reported rather than skipped
  - an address belonging to a System User is refused outright: no client may
    attach one of our own staff accounts to their room
  - an address already active in a DIFFERENT client's room is refused: rooms
    are the privacy boundary and one invite must never straddle two
  - every invite is narrated into the room, so the audit trail is visible to
    both sides rather than accumulating silently
  - an administrator cannot deactivate themselves, nor the last administrator,
    which is the rule the existing promote/demote path already keeps

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.215.0. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


PY_OLD = '''# ---------------- academy, staff face: consultant training ----------------'''

PY_NEW = '''# ---------------- the roster: the client's own onboarding ----------------

INVITE_MAX = 50


def _parse_emails(blob):
\t"""Accept however they have the list: commas, semicolons, newlines, spaces."""
\tif isinstance(blob, (list, tuple)):
\t\traw = list(blob)
\telse:
\t\traw = re.split(r"[,;\\s]+", blob or "")
\tout, seen = [], set()
\tfor e in raw:
\t\te = (e or "").strip().lower()
\t\tif not e or e in seen:
\t\t\tcontinue
\t\tseen.add(e)
\t\tout.append(e)
\treturn out


@frappe.whitelist()
def client_admin_people():
\t"""The room roster as the administrator sees it, leavers included."""
\troom = _require_room_admin()
\trows = frappe.get_all(
\t\t"Client Room Member",
\t\tfilters={"room": room.name},
\t\tfields=["name", "user", "active", "is_admin", "last_seen"],
\t\torder_by="active desc, is_admin desc, creation asc",
\t)
\tout = []
\tfor m in rows:
\t\tif not m.user:
\t\t\tcontinue
\t\tassigned = frappe.db.count(
\t\t\t"Duty Training Record", {"room": room.name, "trainee": m.user}
\t\t)
\t\tdone = frappe.db.count(
\t\t\t"Duty Training Record",
\t\t\t{"room": room.name, "trainee": m.user, "status": "Completed"},
\t\t)
\t\tout.append({
\t\t\t"user": m.user,
\t\t\t"full_name": frappe.utils.get_fullname(m.user),
\t\t\t"active": cint(m.active),
\t\t\t"is_admin": cint(m.is_admin),
\t\t\t"is_self": m.user == frappe.session.user,
\t\t\t"assigned": assigned,
\t\t\t"complete": done,
\t\t\t"last_seen": str(m.last_seen) if m.last_seen else None,
\t\t})
\treturn out


@frappe.whitelist()
def client_admin_invite(emails):
\t"""Bulk-invite colleagues. Reports every address it would not take and
\twhy, rather than silently dropping them — a half-applied roster that
\tlooks complete is worse than an error."""
\troom = _require_room_admin()
\taddrs = _parse_emails(emails)
\tif not addrs:
\t\tfrappe.throw(_("Paste at least one email address."))
\tif len(addrs) > INVITE_MAX:
\t\tfrappe.throw(
\t\t\t_("{0} addresses at once is over the limit of {1}. Send them in batches.").format(
\t\t\t\tlen(addrs), INVITE_MAX
\t\t\t)
\t\t)
\tinvited, rejoined, already, refused = [], [], [], []
\tfor email in addrs:
\t\tif not frappe.utils.validate_email_address(email):
\t\t\trefused.append({"email": email, "why": _("not a valid email address")})
\t\t\tcontinue
\t\tuser = frappe.db.get_value("User", email, ["name", "user_type", "enabled"], as_dict=True)
\t\tif user and user.user_type != "Website User":
\t\t\t# never let a client attach one of our own staff accounts to their room
\t\t\trefused.append({"email": email, "why": _("this address cannot be added here")})
\t\t\tcontinue
\t\tif user:
\t\t\telsewhere = frappe.db.exists(
\t\t\t\t"Client Room Member",
\t\t\t\t{"user": email, "active": 1, "room": ["!=", room.name]},
\t\t\t)
\t\t\tif elsewhere:
\t\t\t\trefused.append({"email": email, "why": _("this address already belongs to another organisation")})
\t\t\t\tcontinue
\t\tmember = frappe.db.get_value(
\t\t\t"Client Room Member", {"room": room.name, "user": email}, ["name", "active"], as_dict=True
\t\t)
\t\tif member and cint(member.active):
\t\t\talready.append(email)
\t\t\tcontinue
\t\tif not user:
\t\t\tfrappe.get_doc({
\t\t\t\t"doctype": "User",
\t\t\t\t"email": email,
\t\t\t\t"first_name": email.split("@")[0].strip(),
\t\t\t\t"user_type": "Website User",
\t\t\t\t"send_welcome_email": 1,
\t\t\t}).insert(ignore_permissions=True)
\t\telif not cint(user.enabled):
\t\t\tfrappe.db.set_value("User", email, "enabled", 1, update_modified=False)
\t\tif member:
\t\t\tfrappe.db.set_value("Client Room Member", member.name, "active", 1, update_modified=False)
\t\t\trejoined.append(email)
\t\telse:
\t\t\tfrappe.get_doc({
\t\t\t\t"doctype": "Client Room Member",
\t\t\t\t"room": room.name, "user": email, "active": 1,
\t\t\t}).insert(ignore_permissions=True)
\t\t\tinvited.append(email)
\tfrappe.db.commit()
\tif invited or rejoined:
\t\ttry:
\t\t\t_post(
\t\t\t\troom,
\t\t\t\t_("👥 {0} added {1} colleague(s) to the portal{2}.").format(
\t\t\t\t\tfrappe.utils.get_fullname(frappe.session.user),
\t\t\t\t\tlen(invited) + len(rejoined),
\t\t\t\t\t_(" ({0} rejoining)").format(len(rejoined)) if rejoined else "",
\t\t\t\t),
\t\t\t)
\t\texcept Exception:
\t\t\tfrappe.log_error(frappe.get_traceback(), "duty_board invite narration")
\treturn {
\t\t"invited": invited, "rejoined": rejoined,
\t\t"already": already, "refused": refused,
\t\t"people": client_admin_people(),
\t}


@frappe.whitelist()
def client_admin_set_active(user, on=0):
\t"""End or restore a colleague's access. Never deletes: training records,
\tattempts and certificates all survive, so a returner resumes where they
\tstopped and a leaver's certificate stays true."""
\troom = _require_room_admin()
\ton = cint(on)
\trow = frappe.db.get_value(
\t\t"Client Room Member", {"room": room.name, "user": user}, ["name", "is_admin", "active"], as_dict=True
\t)
\tif not row:
\t\tfrappe.throw(_("Not found."), frappe.PermissionError)
\tif not on:
\t\tif user == frappe.session.user:
\t\t\tfrappe.throw(_("You cannot remove your own access."))
\t\tif cint(row.is_admin) and len(_room_admins(room)) <= 1:
\t\t\tfrappe.throw(_("Appoint another administrator before removing this one."))
\tfrappe.db.set_value("Client Room Member", row.name, "active", 1 if on else 0, update_modified=False)
\tfrappe.db.commit()
\ttry:
\t\t_post(
\t\t\troom,
\t\t\t_("👥 {0} {1} access for {2}.").format(
\t\t\t\tfrappe.utils.get_fullname(frappe.session.user),
\t\t\t\t_("restored") if on else _("ended"),
\t\t\t\tfrappe.utils.get_fullname(user),
\t\t\t),
\t\t)
\texcept Exception:
\t\tpass
\treturn client_admin_people()


# ---------------- academy, staff face: consultant training ----------------'''

IMP_OLD = '''import json

import frappe'''
IMP_NEW = '''import json
import re

import frappe'''


# --- portal ----------------------------------------------------------------
BTN_OLD = '''\t\t\t\t\t\t<button id="admcat" style="background:#E2E8E5;color:#2A3833">Catalogue</button>'''
BTN_NEW = '''\t\t\t\t\t\t<button id="admppl" style="background:#E2E8E5;color:#2A3833">People</button>
\t\t\t\t\t\t<button id="admcat" style="background:#E2E8E5;color:#2A3833">Catalogue</button>'''

HOOK_OLD = '''\t\t\tdocument.getElementById("admcat").onclick = openCatalogue;'''
HOOK_NEW = '''\t\t\tdocument.getElementById("admcat").onclick = openCatalogue;
\t\t\tdocument.getElementById("admppl").onclick = openPeople;'''

FN_OLD = '''function openCatalogue() {'''

FN_NEW = '''function openPeople() {
\tconst host = document.getElementById("adminhost");
\tconst paint = (people) => {
\t\tconst live = people.filter((p) => p.active);
\t\tconst gone = people.filter((p) => !p.active);
\t\tconst row = (p) => `
\t\t\t<div class="pplrow${p.active ? "" : " off"}">
\t\t\t\t<div class="pplwho">
\t\t\t\t\t<b>${esc(p.full_name)}</b>${p.is_admin ? ` <span class="ppladm">administrator</span>` : ""}
\t\t\t\t\t<span class="muted">${esc(p.user)}${p.assigned ? ` \u00b7 ${p.complete} of ${p.assigned} complete` : " \u00b7 no training yet"}</span>
\t\t\t\t</div>
\t\t\t\t${p.is_self ? `<span class="muted" style="font-size:12px">you</span>`
\t\t\t\t\t: `<a class="pplset" data-u="${esc(p.user)}" data-on="${p.active ? 0 : 1}">${p.active ? "End access" : "Restore"}</a>`}
\t\t\t</div>`;
\t\thost.innerHTML = `
\t\t\t<div class="admwrap">
\t\t\t\t<div class="admhead"><div><b>People</b><span class="muted"> \u00b7 who from your organisation can use the portal</span></div>
\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="loadAdminTraining()">Back</button></div>
\t\t\t\t<div class="admfield"><label>Invite colleagues</label>
\t\t\t\t\t<textarea id="pplmails" rows="3" placeholder="Paste email addresses \u2014 commas, spaces or one per line"></textarea></div>
\t\t\t\t<button id="pplgo">Send invitations</button>
\t\t\t\t<div id="pplres"></div>
\t\t\t\t<div class="duty-lead-section" style="margin-top:18px;font-weight:700;font-size:13px">Active \u00b7 ${live.length}</div>
\t\t\t\t${live.map(row).join("") || `<span class="muted">Nobody yet.</span>`}
\t\t\t\t${gone.length ? `<div class="duty-lead-section" style="margin-top:16px;font-weight:700;font-size:13px">No longer active \u00b7 ${gone.length}</div>${gone.map(row).join("")}` : ""}
\t\t\t\t<p class="muted" style="font-size:11.5px;margin-top:12px">Ending access does not delete anything. Their progress and certificates are kept, and a returning colleague picks up exactly where they stopped.</p>
\t\t\t</div>`;
\t\tdocument.getElementById("pplgo").onclick = () => {
\t\t\tconst v = document.getElementById("pplmails").value.trim();
\t\t\tif (!v) return alert("Paste at least one email address.");
\t\t\tdocument.getElementById("pplgo").disabled = true;
\t\t\tapi("client_admin_invite", { emails: v })
\t\t\t\t.then((r) => {
\t\t\t\t\tconst bits = [];
\t\t\t\t\tif (r.invited.length) bits.push(`<div class="catnote ok">${r.invited.length} invitation(s) sent.</div>`);
\t\t\t\t\tif (r.rejoined.length) bits.push(`<div class="catnote ok">${r.rejoined.length} colleague(s) restored.</div>`);
\t\t\t\t\tif (r.already.length) bits.push(`<div class="catnote">${r.already.length} already had access.</div>`);
\t\t\t\t\tif (r.refused.length) bits.push(`<div class="catnote">${r.refused.map((x) => `${esc(x.email)} \u2014 ${esc(x.why)}`).join("<br>")}</div>`);
\t\t\t\t\tpaint(r.people);
\t\t\t\t\tdocument.getElementById("pplres").innerHTML = bits.join("");
\t\t\t\t})
\t\t\t\t.catch((e) => { document.getElementById("pplgo").disabled = false; fail(e); });
\t\t};
\t\thost.querySelectorAll(".pplset").forEach((a) =>
\t\t\ta.addEventListener("click", () =>
\t\t\t\tapi("client_admin_set_active", { user: a.getAttribute("data-u"), on: a.getAttribute("data-on") })
\t\t\t\t\t.then(paint).catch(fail)));
\t};
\tapi("client_admin_people").then(paint).catch(fail);
}
function openCatalogue() {'''

CSS_OLD = '''\t.catacts { display: flex; gap: 16px; margin-top: 8px; }'''
CSS_NEW = '''\t.catacts { display: flex; gap: 16px; margin-top: 8px; }
\t.pplrow { display: flex; align-items: center; gap: 12px; padding: 9px 0; border-top: 1px solid #F0F4F2; }
\t.pplrow.off { opacity: .55; }
\t.pplwho { flex: 1; min-width: 0; font-size: 13.5px; }
\t.pplwho span { display: block; font-size: 12px; }
\t.ppladm { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px;
\t\tcolor: var(--brand-700); background: var(--brand-50); border-radius: 99px; padding: 2px 8px; }
\t.pplset { font-size: 12px; font-weight: 700; color: var(--brand-700); cursor: pointer; white-space: nowrap; }
\t.admfield textarea { width: 100%; max-width: 460px; padding: 9px 11px; border: 1px solid #DCE4E1;
\t\tborder-radius: 9px; font-size: 14px; font-family: inherit; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def client_admin_invite(" in files[CR]:
        print("Already applied. Nothing to do.")
        return
    if '"3.215.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.215.0.")

    edits = [
        (CR, IMP_OLD, IMP_NEW, "re import"),
        (CR, PY_OLD, PY_NEW, "roster endpoints"),
        (PORTAL, BTN_OLD, BTN_NEW, "People button"),
        (PORTAL, HOOK_OLD, HOOK_NEW, "People hook"),
        (PORTAL, FN_OLD, FN_NEW, "openPeople"),
        (PORTAL, CSS_OLD, CSS_NEW, "roster css"),
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
    for p in (CR, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: roster, bulk invite, end/restore access")
    print("  portal.html: People view")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.215.0"', '"3.216.0"'))
    print("wrote __init__.py -> 3.216.0")


if __name__ == "__main__":
    main()
