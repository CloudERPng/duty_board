#!/usr/bin/env python3
"""Duty Board v3.204.0 — DM ATTACHMENTS.

Direct messages gain the same attachment capability as client-room chat:
images render inline, video and audio play inline, other files download —
with the DM privacy model preserved (a new dm_file proxy serves a file to
the two parties only; the Duty DM doctype still grants no desk roles).

Changes:
  1. Duty DM doctype: attachment_url + attachment_name fields.
  2. dm.py: send_dm accepts an attachment (ownership-verified, message
     optional when a file is present, mirroring rooms); get_dm_thread
     returns the fields; edit_dm honours drop_attachment; dm_file serves
     party-only; push preview shows the attachment name when no text.
  3. duty_board.js: dm_att_html renderer (image / video / audio / link),
     wire_dm_attach helper (📎 button, paste-to-attach, pending chip,
     25 MB guard), wired into BOTH DM surfaces (✉ dialog + Chat face);
     edit prompt offers "Remove the attachment" when one exists.

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one migrate        # new doctype fields
  bench --site xlevel.clouderp.one clear-cache    # page JS refresh
  (users hard-refresh the browser once)

Anchored, idempotent. Requires v3.203.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

JS = "duty_board/duty_board/page/duty_board/duty_board.js"
DM = "duty_board/dm.py"
DT = "duty_board/duty_board/doctype/duty_dm/duty_dm.json"

# Each fix: (path, old, new, expected_count)
FIXES = [

# ---------------------------------------------------------------- doctype
(DT,
'''  "seen",
  "edited_on"
 ],''',
'''  "seen",
  "attachment_url",
  "attachment_name",
  "edited_on"
 ],''', 1),

(DT,
'''  {
   "fieldname": "edited_on",''',
'''  {
   "fieldname": "attachment_url",
   "fieldtype": "Data",
   "label": "Attachment URL",
   "read_only": 1
  },
  {
   "fieldname": "attachment_name",
   "fieldtype": "Data",
   "label": "Attachment Name",
   "read_only": 1
  },
  {
   "fieldname": "edited_on",''', 1),

# ---------------------------------------------------------------- dm.py
(DM,
'''@frappe.whitelist()
def send_dm(to, message):
	require_staff()
	me = frappe.session.user
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Message is empty."))
	if len(message) > MAX_LENGTH:
		frappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
	_validate_recipient(to)
''',
'''@frappe.whitelist()
def send_dm(to, message=None, attachment_url=None, attachment_name=None):
	require_staff()
	me = frappe.session.user
	message = (message or "").strip()
	if not message and not attachment_url:
		frappe.throw(_("Message is empty."))
	if len(message) > MAX_LENGTH:
		frappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
	_validate_recipient(to)

	if attachment_url:
		owned = frappe.db.get_value(
			"File", {"file_url": attachment_url, "owner": me}, "file_name"
		)
		if not owned:
			frappe.throw(_("Upload not found — try attaching again."))
		attachment_name = (attachment_name or owned)[:120]
	else:
		attachment_url = None
		attachment_name = None
''', 1),

(DM,
'''			"message": message,
			"seen": 0,''',
'''			"message": message or "📎",
			"attachment_url": attachment_url,
			"attachment_name": attachment_name,
			"seen": 0,''', 1),

(DM,
'''		"recipient": to,
		"message": message,
		"creation": str(doc.creation),''',
'''		"recipient": to,
		"message": doc.message,
		"attachment_url": attachment_url,
		"attachment_name": attachment_name,
		"creation": str(doc.creation),''', 1),

(DM,
'''		push_to_user(to, _("✉ DM from {0}").format(first), message[:120])''',
'''		preview = message or ("📎 " + (attachment_name or _("Attachment")))
		push_to_user(to, _("✉ DM from {0}").format(first), preview[:120])''', 1),

(DM,
'''		fields=["name", "sender", "recipient", "message", "creation", "edited_on", "seen"],''',
'''		fields=[
			"name", "sender", "recipient", "message", "creation", "edited_on",
			"seen", "attachment_url", "attachment_name",
		],''', 1),

(DM,
'''	"""Edit own DM within 30 minutes. DMs have no attachments; drop is ignored."""''',
'''	"""Edit own DM within 30 minutes; drop_attachment removes the file."""''', 1),

(DM,
'''	text = (message or "").strip()
	if not text:
		frappe.throw(_("A message cannot be empty."))
	if len(text) > MAX_LENGTH:
		frappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
	doc.message = text''',
'''	text = (message or "").strip()
	if cint(drop_attachment):
		doc.attachment_url = None
		doc.attachment_name = None
	if not text and not doc.attachment_url:
		frappe.throw(_("A message cannot be empty."))
	if len(text) > MAX_LENGTH:
		frappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
	doc.message = text or "📎"''', 1),

(DM,
'''	payload = {
		"name": doc.name, "sender": doc.sender, "recipient": doc.recipient,
		"message": text, "creation": str(doc.creation), "edited_on": str(doc.edited_on),
		"edit": 1,
	}''',
'''	payload = {
		"name": doc.name, "sender": doc.sender, "recipient": doc.recipient,
		"message": doc.message, "creation": str(doc.creation), "edited_on": str(doc.edited_on),
		"attachment_url": doc.attachment_url, "attachment_name": doc.attachment_name,
		"edit": 1,
	}''', 1),

(DM,
'''def get_unread_map(user):''',
'''@frappe.whitelist()
def dm_file(msg):
	"""Serve a DM attachment to the two parties only — same privacy model
	as the thread endpoints: nobody else, staff or not, can fetch it."""
	require_staff()
	m = frappe.get_doc("Duty DM", msg)
	user = frappe.session.user
	if user not in (m.sender, m.recipient):
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if not m.attachment_url:
		frappe.throw(_("No attachment."))
	fname = frappe.db.get_value("File", {"file_url": m.attachment_url})
	if not fname:
		frappe.throw(_("File missing."))
	from duty_board.client_room import _serve_file

	fdoc = frappe.get_doc("File", fname)
	return _serve_file(fdoc, m.attachment_name or fdoc.file_name)


def get_unread_map(user):''', 1),

# ---------------------------------------------------------------- JS: renderer
(JS,
'''				<span class="duty-msg-text">${this.linkify(frappe.utils.escape_html(m.message || ""))}</span>''',
'''				<span class="duty-msg-text">${this.linkify(frappe.utils.escape_html(m.message || ""))}</span>${this.dm_att_html(m)}''', 1),

(JS,
'''<a class="duty-dm-edit" data-name="${m.name}" data-text="${frappe.utils.escape_html(m.message || "")}" title="${__("Edit")}">✏</a>''',
'''<a class="duty-dm-edit" data-name="${m.name}" data-text="${frappe.utils.escape_html(m.message || "")}" data-att="${m.attachment_url ? 1 : 0}" title="${__("Edit")}">✏</a>''', 1),

# ---------------------------------------------------------------- JS: helpers
(JS,
'''		return { file_url: fu, file_name: file.name };
	}
''',
'''		return { file_url: fu, file_name: file.name };
	}

	dm_att_html(m) {
		if (!m.attachment_url) return "";
		const url = `/api/method/duty_board.dm.dm_file?msg=${encodeURIComponent(m.name)}`;
		const ext = (m.attachment_name || "").toLowerCase().split(".").pop();
		if (["png", "jpg", "jpeg", "gif", "webp"].includes(ext))
			return `<span class="duty-dm-att" style="display:block;margin-top:6px"><a href="${url}" target="_blank"><img src="${url}" style="max-width:220px;max-height:220px;border-radius:8px" loading="lazy"></a></span>`;
		if (["webm", "ogg", "mp3", "m4a", "wav"].includes(ext))
			return `<span class="duty-dm-att" style="display:block;margin-top:6px"><audio controls preload="none" src="${url}" style="max-width:240px"></audio></span>`;
		if (["mp4", "mov", "m4v", "3gp"].includes(ext))
			return `<span class="duty-dm-att" style="display:block;margin-top:6px"><video controls preload="metadata" src="${url}" style="max-width:260px;max-height:220px;border-radius:8px"></video></span>`;
		return `<span class="duty-dm-att" style="display:block;margin-top:6px"><a href="${url}" target="_blank">📎 ${frappe.utils.escape_html(m.attachment_name || "file")}</a></span>`;
	}

	wire_dm_attach($send, $input) {
		let pending = null;
		const $btn = $(
			`<label class="btn btn-default btn-sm duty-dm-attach" title="${__("Attach a photo, video or file")}" style="margin:0;align-self:flex-end">📎<input type="file" hidden accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip"></label>`
		);
		const $chip = $(
			`<div class="duty-dm-pend text-muted" style="display:none;font-size:12px;padding:2px 2px 4px;cursor:pointer" title="${__("Remove")}"></div>`
		);
		$send.prepend($btn);
		$send.before($chip);
		const show = () => {
			if (pending) $chip.text(`📎 ${pending.name} ✕`).show();
			else $chip.hide();
		};
		const take = (f) => {
			if (!f) return;
			if (f.size > 25 * 1024 * 1024) {
				frappe.msgprint(__("That file is larger than 25 MB — send something smaller."));
				return;
			}
			pending = f;
			show();
		};
		$btn.find("input").on("change", (e) => {
			take(e.target.files[0]);
			e.target.value = "";
		});
		$chip.on("click", () => {
			pending = null;
			show();
		});
		$input.on("paste", (e) => {
			for (const it of (e.originalEvent.clipboardData || {}).items || []) {
				if (it.kind === "file") {
					const f = it.getAsFile();
					if (f) {
						e.preventDefault();
						take(f);
						break;
					}
				}
			}
		});
		return {
			has: () => !!pending,
			consume: async () => {
				if (!pending) return null;
				const up = await this.upload_private_file(pending);
				pending = null;
				show();
				return up;
			},
		};
	}
''', 1),

# ------------------------------------------- JS: wire both DM surfaces
(JS,
'''		const $list = $(d.body).find(".duty-dm-list");
		const $input = $(d.body).find(".duty-dm-input");''',
'''		const $list = $(d.body).find(".duty-dm-list");
		const $input = $(d.body).find(".duty-dm-input");
		const att = this.wire_dm_attach($(d.body).find(".duty-dm-send"), $input);''', 1),

(JS,
'''		const $list = $host.find(".duty-dm-list");
		const $input = $host.find(".duty-dm-input");''',
'''		const $list = $host.find(".duty-dm-list");
		const $input = $host.find(".duty-dm-input");
		const att = this.wire_dm_attach($host.find(".duty-dm-send"), $input);''', 1),

# The identical send() closure exists on BOTH surfaces — replaced on both.
(JS,
'''		const send = () => {
			const text = ($input.val() || "").trim();
			if (!text) return;
			$input.val("");
			frappe.call({
				method: "duty_board.dm.send_dm",
				args: { to: user, message: text },''',
'''		const send = async () => {
			const text = ($input.val() || "").trim();
			if (!text && !att.has()) return;
			$input.val("");
			let up = null;
			try {
				up = await att.consume();
			} catch (err) {
				frappe.msgprint(__("Upload failed: {0}", [frappe.utils.escape_html(err.message || "")]));
				return;
			}
			frappe.call({
				method: "duty_board.dm.send_dm",
				args: {
					to: user,
					message: text,
					attachment_url: up ? up.file_url : null,
					attachment_name: up ? up.file_name : null,
				},''', 2),

# Edit prompt: offer attachment removal when the row has one.
(JS,
'''			this.edit_prompt("dm", $t.data("name"), $t.data("text"), false, () => load(null));''',
'''			this.edit_prompt("dm", $t.data("name"), $t.data("text"), $t.data("att") == 1, () => load(null));''', 1),
]


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    if '"3.204.0"' in init:
        print("Already applied. Nothing to do.")
        return
    if '"3.203.0"' not in init:
        sys.exit("ABORT: not at v3.203.0.")

    contents = {}
    for path, old, new, want in FIXES:
        if path not in contents:
            with io.open(os.path.join(root, path), encoding="utf-8") as f:
                contents[path] = f.read()
        got = contents[path].count(old)
        if got != want:
            sys.exit(f"ABORT: anchor x{got} (want {want}) in {path}:\n{old[:120]}...")
        contents[path] = contents[path].replace(old, new)
    print(f"All {len(FIXES)} anchors verified across {len(contents)} files.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for path, text in contents.items():
        with io.open(os.path.join(root, path), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  wrote {path}")
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.203.0"', '"3.204.0"'))
    print("wrote __version__ -> 3.204.0")


if __name__ == "__main__":
    main()
