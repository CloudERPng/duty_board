"""Duty Board bridge: lets other modules (Document Hub, portals, schedulers)
post system messages into the Duty Room without touching Team Message
internals or api.py.

Usage from any server code on this bench:

	from duty_board.bridge import post_to_duty_room
	post_to_duty_room(f"📄 {fname} checked out by {who}")

- In a user-triggered action (checkout, check-in), the message posts as
  that user automatically.
- In scheduled jobs (stale-checkout alerts), there is no session user, so
  it posts as Administrator; pass user=... to override.
- Clients render it like any chat message: realtime, unread counters,
  25s sync fallback — all standard.

Do NOT insert Team Message documents directly from other modules; this
helper is the supported path and keeps payload/realtime behavior in one
place.
"""

import frappe


def post_to_duty_room(text, user=None):
	text = (text or "").strip()
	if not text:
		return None
	if not user:
		session = getattr(frappe, "session", None)
		user = session.user if session and session.user not in (None, "Guest") else "Administrator"

	doc = frappe.get_doc(
		{"doctype": "Team Message", "user": user, "message": text[:2000]}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	try:
		from duty_board.api import _message_payload

		payload = _message_payload(doc.as_dict(), {})
		frappe.publish_realtime("duty_board_message", payload)
	except Exception:
		frappe.log_error(f"bridge publish failed for {doc.name}", "Duty Board Bridge")
	return doc.name
