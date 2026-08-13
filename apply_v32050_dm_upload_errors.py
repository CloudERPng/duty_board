#!/usr/bin/env python3
"""Duty Board v3.205.0 — DM ATTACHMENT SEND: LOUD FAILURES.

v3.204.0's send path handled upload failure with a msgprint that can
render behind the DM dialog, after the input was already cleared — so a
rejected upload (typically a video over the site's max_file_size, which
defaults to 10 MB) looked like "nothing happened".

This patch:
  1. On upload failure: restores the typed text into the input, keeps
     the pending file for retry, and raises a red frappe.show_alert
     (always on top) plus a console.error with the cause.
  2. upload_private_file (shared with rooms) now surfaces the real
     server message — including a clean "file too large" for HTTP 413
     and Frappe's _server_messages payloads — instead of a JSON parse
     failure or a bare HTTP status.

Pair with the server-side unblock:
  bench --site xlevel.clouderp.one set-config max_file_size 26214400

Deploy: apply -> commit -> bench clear-cache -> hard refresh.
Anchored, idempotent. Requires v3.204.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
CHECK_ONLY = "--check" in sys.argv

FIXES = [

# Both DM send closures (desktop dialog + Chat face) — identical text, x2.
(JS,
'''			let up = null;
			try {
				up = await att.consume();
			} catch (err) {
				frappe.msgprint(__("Upload failed: {0}", [frappe.utils.escape_html(err.message || "")]));
				return;
			}''',
'''			let up = null;
			try {
				up = await att.consume();
			} catch (err) {
				$input.val(text);
				frappe.show_alert(
					{
						message: __("Upload failed: {0}", [frappe.utils.escape_html(err.message || String(err))]),
						indicator: "red",
					},
					8
				);
				console.error("DM upload failed", err);
				return;
			}''', 2),

# upload_private_file: real error surfacing (shared by rooms and DMs).
(JS,
'''		const out = await res.json();
		const fu = out.message && out.message.file_url;
		if (!res.ok || !fu) {
			throw new Error(out.exception || `HTTP ${res.status}`);
		}
		return { file_url: fu, file_name: file.name };''',
'''		let out = {};
		try {
			out = await res.json();
		} catch (e) {
			throw new Error(
				res.status === 413
					? __("The file is larger than the server allows — ask the admin to raise max_file_size.")
					: `HTTP ${res.status}`
			);
		}
		const fu = out.message && out.message.file_url;
		if (!res.ok || !fu) {
			let emsg = out.exception || `HTTP ${res.status}`;
			try {
				const sm = JSON.parse(JSON.parse(out._server_messages)[0]);
				if (sm && sm.message) emsg = sm.message.replace(/<[^>]+>/g, "");
			} catch (e) {
				/* keep emsg */
			}
			throw new Error(emsg);
		}
		return { file_url: fu, file_name: file.name };''', 1),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    if '"3.205.0"' in init:
        print("Already applied. Nothing to do.")
        return
    if '"3.204.0"' not in init:
        sys.exit("ABORT: not at v3.204.0.")

    with io.open(os.path.join(root, JS), encoding="utf-8") as f:
        text = f.read()
    for path, old, new, want in FIXES:
        got = text.count(old)
        if got != want:
            sys.exit(f"ABORT: anchor x{got} (want {want}):\n{old[:120]}...")
        text = text.replace(old, new)
    print(f"All {len(FIXES)} anchors verified.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(text)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.204.0"', '"3.205.0"'))
    print("wrote duty_board.js; __version__ -> 3.205.0")


if __name__ == "__main__":
    main()
