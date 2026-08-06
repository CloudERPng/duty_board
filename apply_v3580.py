#!/usr/bin/env python3
"""Duty Board v3.58.0 — the join-request door gets a real lock.

THE HOLE: submit_join_request (guest-reachable) accepted a PASSWORD
chosen by the requester. approve_join enabled the account and never
touched credentials. So anyone holding a live invite token — tokens
get forwarded around WhatsApp groups — could plant
finance-director@theclient.com with their own password, look plausible
in the approval queue, and walk into that client's room (chat,
financial statements, document shelf) the moment a staff member
clicked approve.

THE FIX, four layers:

1. NO GUEST CREDENTIALS. The password parameter is gone from the
   endpoint and the field is gone from the join page. Frappe drops
   unknown kwargs, so stale cached join pages that still POST a
   password are harmlessly ignored.

2. NO PRE-APPROVAL EMAILS. Account creation no longer fires Frappe's
   welcome email (which carried its own password link before anyone
   had approved anything). Silence until a human decides.

3. SCRAMBLE ON APPROVE — the retroactive layer. approve_join now
   overwrites the password of any join-created, never-logged-in
   account with 32 random bytes (all sessions logged out) BEFORE
   enabling it. Anything ALREADY sitting in Pending with a planted
   password is neutralized at the moment of approval. The set-password
   link in the approval email — which _send_join_approved_email
   already sends to never-logged-in users — becomes the only way in.
   Legitimate pending requesters who chose a password simply set a
   fresh one from that link: mild friction, and the only safe
   treatment since a planted request is indistinguishable from a real
   one.

4. RATE LIMIT. 10 submissions per IP per hour via frappe's own
   rate_limiter, stacked exactly as core stacks it on reset_password.
   Sits on top of the existing gates (invite token, dedupe, 20-pending
   room cap).

Deploy: bench restart && bench --site <site> clear-website-cache
(no build — Python and a www template only).

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.57.9.
"""

import io
import os
import sys

PY = "duty_board/client_room.py"
HTML = "duty_board/www/join.html"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# ---------------------------- client_room.py ---------------------------------

P1_OLD = 'from frappe.utils.pdf import get_pdf'
P1_NEW = 'from frappe.utils.pdf import get_pdf\nfrom frappe.rate_limiter import rate_limit'

P2_OLD = '''@frappe.whitelist(allow_guest=True)
def submit_join_request(token, full_name, email, phone=None, password=None):'''
P2_NEW = '''@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def submit_join_request(token, full_name, email, phone=None):'''

P3_OLD = '''\tcreated_user = 0
\tif not frappe.db.exists("User", email):
\t\tpassword = (password or "").strip()
\t\tif password and len(password) < 8:
\t\t\tfrappe.throw(_("Password must be at least 8 characters."))
\t\tu = frappe.get_doc(
\t\t\t{
\t\t\t\t"doctype": "User",
\t\t\t\t"email": email,
\t\t\t\t"first_name": full_name,
\t\t\t\t"user_type": "Website User",
\t\t\t\t"enabled": 0,
\t\t\t\t"send_welcome_email": 0 if password else 1,
\t\t\t}
\t\t)
\t\tif password:
\t\t\tu.new_password = password
\t\tu.insert(ignore_permissions=True)
\t\tcreated_user = 1'''

P3_NEW = '''\tcreated_user = 0
\tif not frappe.db.exists("User", email):
\t\t# No guest-chosen credentials and no pre-approval emails: the account
\t\t# sits disabled and silent until a staff member approves, and the
\t\t# approval email's set-password link is the only way to credentials.
\t\tfrappe.get_doc(
\t\t\t{
\t\t\t\t"doctype": "User",
\t\t\t\t"email": email,
\t\t\t\t"first_name": full_name,
\t\t\t\t"user_type": "Website User",
\t\t\t\t"enabled": 0,
\t\t\t\t"send_welcome_email": 0,
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tcreated_user = 1'''

P4_OLD = '''\tadd_member(req.room, req.email, req.full_name)
\tif frappe.db.get_value("User", req.email, "user_type") == "Website User":
\t\tfrappe.db.set_value("User", req.email, "enabled", 1, update_modified=False)'''

P4_NEW = '''\tadd_member(req.room, req.email, req.full_name)
\tif frappe.db.get_value("User", req.email, "user_type") == "Website User":
\t\tif req.created_user and not frappe.db.get_value("User", req.email, "last_login"):
\t\t\t# Retroactive lock: requests submitted before v3.58.0 could carry a
\t\t\t# requester-chosen password. Scramble it (and any sessions) before
\t\t\t# enabling, so the approval email's set-password link is the only
\t\t\t# door — for planted requests and legitimate ones alike.
\t\t\tfrom frappe.utils.password import update_password
\t\t\tupdate_password(req.email, frappe.generate_hash(length=32), logout_all_sessions=True)
\t\tfrappe.db.set_value("User", req.email, "enabled", 1, update_modified=False)'''

# ---------------------------- www/join.html ----------------------------------

H1_OLD = '\t<input id="pw" placeholder="Choose a password (min 8 characters)" maxlength="60" type="password">\n'
H1_NEW = ''

H2_OLD = '''\tconst pw = document.getElementById("pw").value;
\tif (!name || !email) return show("Name and email are required.", false);
\tif (pw && pw.length < 8) return show("Password must be at least 8 characters.", false);'''
H2_NEW = '\tif (!name || !email) return show("Name and email are required.", false);'

H3_OLD = '\t\tbody: JSON.stringify({ token: token, full_name: name, email: email, phone: phone, password: pw }),'
H3_NEW = '\t\tbody: JSON.stringify({ token: token, full_name: name, email: email, phone: phone }),'

H4_OLD = '\t\t\t\tshow(pw ? "Request sent ✔ Once approved, log in with your email and password." : "Request sent ✔ You\'ll receive a welcome email once approved.", true);'
H4_NEW = '\t\t\t\tshow("Request sent ✔ Once your Xlevel team approves, you\'ll get an email with a link to set your password.", true);'

PY_EDITS = [
    ("import rate_limit", P1_OLD, P1_NEW),
    ("submit_join_request: no password param, 10/hr/IP", P2_OLD, P2_NEW),
    ("user creation: no credentials, no emails", P3_OLD, P3_NEW),
    ("approve_join: scramble before enable", P4_OLD, P4_NEW),
]
HTML_EDITS = [
    ("join page: password field removed", H1_OLD, H1_NEW),
    ("join page: password JS removed", H2_OLD, H2_NEW),
    ("join page: password out of the payload", H3_OLD, H3_NEW),
    ("join page: one honest success message", H4_OLD, H4_NEW),
]


def main():
    root = os.getcwd()
    files = {PY: None, HTML: None}
    for p in files:
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "@rate_limit(limit=10, seconds=60 * 60)" in files[PY]:
        print("Already applied. Nothing to do.")
        return

    problems = []
    for label, old, _ in PY_EDITS:
        if files[PY].count(old) != 1:
            problems.append(f"  [{files[PY].count(old)} matches] client_room.py: {label}")
    for label, old, _ in HTML_EDITS:
        if files[HTML].count(old) != 1:
            problems.append(f"  [{files[HTML].count(old)} matches] join.html: {label}")
    if problems:
        print("ABORT — anchors did not match exactly once:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(PY_EDITS) + len(HTML_EDITS)} anchors matched exactly once.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    out_py = files[PY]
    for label, old, new in PY_EDITS:
        out_py = out_py.replace(old, new, 1)
        print(f"  applied client_room.py: {label}")
    with io.open(os.path.join(root, PY), "w", encoding="utf-8") as f:
        f.write(out_py)

    out_html = files[HTML]
    for label, old, new in HTML_EDITS:
        out_html = out_html.replace(old, new, 1)
        print(f"  applied join.html: {label}")
    with io.open(os.path.join(root, HTML), "w", encoding="utf-8") as f:
        f.write(out_html)

    print(f"\nwrote {PY} and {HTML}")

    init_path = os.path.join(root, INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.57.9"', '"3.58.0"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.58.0")
    else:
        print("NOTE: version was not 3.57.9 — left untouched.")


if __name__ == "__main__":
    main()
