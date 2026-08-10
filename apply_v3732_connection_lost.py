#!/usr/bin/env python3
"""Duty Board v3.73.2 — "Connection lost" only when it's true.

Reported: the "session has probably expired" modal appears often while
the session is fine (desktop and mobile), dismiss-and-continue works.

Root cause: six pollers on independent timers shared ONE failure
counter; any error of any kind incremented it and three tripped the
modal — so a single network blip or a bench restart failed several
parallel polls at once and instantly "expired" a healthy session. No
actual session check was ever made.

Fix — diagnose, don't count:
- Network-level failures (offline, status 0), 5xx (server restarting),
  and timeouts: show a throttled "Reconnecting…" toast (once per
  minute) and keep polling. Never the modal.
- Auth-status failures (401/403): run ONE verification ping to
  frappe.auth.get_logged_user (throttled, single-flight). Session
  verified alive -> transient, carry on. Ping itself returns 401/403 ->
  genuinely logged out -> halt + modal, now guaranteed accurate.
- Safety net: if reconnect toasts stack up (5+), run the same
  verification anyway, so a weird logout that presents as network
  errors still gets caught.
- consultant_check semantics on the board poll preserved (first
  failure only), via its own flag.

Mobile app uses the same bundle — fixed there too.

JS only. bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.73.1.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

# --- 1. the four identical simple handlers (sync_messages, projects,
#        clients, sales) — replaced as one anchor, count == 4 ---------------
E4_OLD = '''\t\t\terror: () => {
\t\t\t\tthis._fail_count = (this._fail_count || 0) + 1;
\t\t\t\tif (this._fail_count >= 3) this.halt_polling();
\t\t\t},'''
E4_NEW = '''\t\t\terror: (x) => this._poll_failed(x),'''

# --- 2. the board refresh handler (has consultant_check) --------------------
EB_OLD = '''\t\t\terror: () => {
\t\t\t\tthis._fail_count = (this._fail_count || 0) + 1;
\t\t\t\tif (this._fail_count === 1) this.consultant_check();
\t\t\t\tif (this._fail_count >= 3) this.halt_polling();
\t\t\t},'''
EB_NEW = '''\t\t\terror: (x) => {
\t\t\t\tif (!this._cc_done) {
\t\t\t\t\tthis._cc_done = 1;
\t\t\t\t\tthis.consultant_check();
\t\t\t\t}
\t\t\t\tthis._poll_failed(x);
\t\t\t},'''

# --- 3. the chat rail handler (own counter) ---------------------------------
EC_OLD = '''\t\t\terror: () => {
\t\t\t\tthis._ch_fail = (this._ch_fail || 0) + 1;
\t\t\t\tif (this._ch_fail >= 3) this.halt_polling();
\t\t\t},'''
EC_NEW = '''\t\t\terror: (x) => this._poll_failed(x),'''

# --- 4. the diagnosis methods, before halt_polling --------------------------
M_OLD = '\thalt_polling() {'
M_NEW = '''\t_poll_failed(x) {
\t\tif (this._halted) return;
\t\tconst status = (x && (x.status || (x.xhr && x.xhr.status) || (x.responseJSON && x.responseJSON.http_status_code))) || 0;
\t\tif (!navigator.onLine || status === 0 || status >= 500 || status === 417) {
\t\t\tthis._note_reconnecting();
\t\t\treturn;
\t\t}
\t\tif (status === 401 || status === 403) {
\t\t\tthis._verify_session();
\t\t\treturn;
\t\t}
\t\t// other 4xx: endpoint-specific problem, not connectivity — ignore here
\t}

\t_note_reconnecting() {
\t\tconst now = Date.now();
\t\tthis._reconn_count = (this._reconn_count || 0) + 1;
\t\tif (this._reconn_count >= 5) {
\t\t\tthis._reconn_count = 0;
\t\t\tthis._verify_session();
\t\t\treturn;
\t\t}
\t\tif (this._reconn_toast_at && now - this._reconn_toast_at < 60000) return;
\t\tthis._reconn_toast_at = now;
\t\tfrappe.show_alert({ message: __("Reconnecting to Duty Board…"), indicator: "orange" }, 4);
\t}

\t_verify_session() {
\t\tconst now = Date.now();
\t\tif (this._auth_checking) return;
\t\tif (this._auth_checked_at && now - this._auth_checked_at < 10000) return;
\t\tthis._auth_checking = true;
\t\t$.ajax({ url: "/api/method/frappe.auth.get_logged_user", timeout: 8000 })
\t\t\t.done(() => {
\t\t\t\tthis._reconn_count = 0; // session alive — it was transient
\t\t\t})
\t\t\t.fail((xhr) => {
\t\t\t\tif (xhr && (xhr.status === 401 || xhr.status === 403)) this.halt_polling();
\t\t\t\telse this._note_reconnecting();
\t\t\t})
\t\t\t.always(() => {
\t\t\t\tthis._auth_checking = false;
\t\t\t\tthis._auth_checked_at = Date.now();
\t\t\t});
\t}

\thalt_polling() {'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        js = f.read()

    if "_poll_failed(x)" in js and "_verify_session()" in js:
        print("Already applied. Nothing to do.")
        return
    if '"3.73.1"' not in init:
        sys.exit("ABORT: not at v3.73.1.")

    checks = [(E4_OLD, "simple handlers", 4), (EB_OLD, "board handler", 1), (EC_OLD, "chat handler", 1), (M_OLD, "methods anchor", 1)]
    problems = [f"  [{js.count(o)} != {n}] {label}" for o, label, n in checks if js.count(o) != n]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched (simple handlers intentionally x4).")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    js = js.replace(E4_OLD, E4_NEW, 4)
    js = js.replace(EB_OLD, EB_NEW, 1)
    js = js.replace(EC_OLD, EC_NEW, 1)
    js = js.replace(M_OLD, M_NEW, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.73.1"', '"3.73.2"'))
    print("  duty_board.js: 6 handlers -> diagnosis; verify-before-halt added")
    print("wrote __init__.py -> 3.73.2")


if __name__ == "__main__":
    main()
