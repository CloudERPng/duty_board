"""Duty Board direct messages.

Privacy model: the Duty DM doctype grants no role except System Manager,
so staff cannot browse threads in the desk. All access flows through the
endpoints below, which only ever return conversations the session user
is a party to.
"""

import frappe
from frappe import _
from frappe.utils import cint

MAX_LENGTH = 1000


def _validate_recipient(to):
	me = frappe.session.user
	if not to or to == me:
		frappe.throw(_("Pick a colleague to message."))
	u = frappe.db.get_value("User", to, ["enabled", "user_type"], as_dict=True)
	if not u or not u.enabled or u.user_type != "System User":
		frappe.throw(_("Cannot message that user."))


@frappe.whitelist()
def send_dm(to, message):
	me = frappe.session.user
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Message is empty."))
	if len(message) > MAX_LENGTH:
		frappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
	_validate_recipient(to)

	doc = frappe.get_doc(
		{
			"doctype": "Duty DM",
			"sender": me,
			"recipient": to,
			"message": message,
			"seen": 0,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	payload = {
		"name": doc.name,
		"sender": me,
		"recipient": to,
		"message": message,
		"creation": str(doc.creation),
		"sender_name": frappe.utils.get_fullname(me),
	}
	frappe.publish_realtime("duty_board_dm", payload, user=to)
	frappe.publish_realtime("duty_board_dm", payload, user=me)

	first = frappe.utils.get_fullname(me).split(" ")[0]
	try:
		from duty_board.push import push_to_user

		push_to_user(to, _("✉ DM from {0}").format(first), message[:120])
	except Exception:
		pass
	return payload


@frappe.whitelist()
def get_dm_thread(with_user, before=None, limit=30):
	me = frappe.session.user
	if with_user == me:
		frappe.throw(_("That's you."))
	cap = min(cint(limit) or 30, 100)

	# both parties constrained to the pair; self-DMs cannot exist, so this
	# yields exactly the me<->with_user thread
	filters = {
		"sender": ["in", [me, with_user]],
		"recipient": ["in", [me, with_user]],
	}
	if before:
		filters["creation"] = ["<", before]

	rows = frappe.get_all(
		"Duty DM",
		filters=filters,
		fields=["name", "sender", "recipient", "message", "creation"],
		order_by="creation desc",
		limit=cap,
	)
	has_more = len(rows) >= cap
	rows.reverse()
	names = {}
	for r in rows:
		r.creation = str(r.creation)
		r.sender_name = names.setdefault(
			r.sender, frappe.db.get_value("User", r.sender, "full_name") or r.sender
		)
	return {"messages": rows, "has_more": has_more}


@frappe.whitelist()
def mark_dm_seen(with_user):
	frappe.db.sql(
		"""update `tabDuty DM` set seen = 1
		where recipient = %s and sender = %s and seen = 0""",
		(frappe.session.user, with_user),
	)
	frappe.db.commit()
	return {"ok": True}


def get_unread_map(user):
	rows = frappe.get_all(
		"Duty DM",
		filters={"recipient": user, "seen": 0},
		fields=["sender", "count(name) as cnt"],
		group_by="sender",
	)
	return {r.sender: r.cnt for r in rows}
