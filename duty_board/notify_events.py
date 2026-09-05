"""Assignment and progress notifications for tasks and issues.

WHY THIS IS ONE MODULE.

The signals were scattered and inconsistent: create_task notified nobody,
update_task emailed consultants only, issues fired a realtime ping, and nothing
anywhere told the person who *assigned* the work that it had moved. Fixing that
by adding calls at each site would have produced the same drift again, so every
event goes through announce() here and every hook site is one line.

WHO GETS TOLD — the watcher set.

  the assignee(s)              they are doing the work
  whoever assigned it          they asked for it and are waiting on it
  the creator                  they raised it

minus whoever performed the action, because nobody needs telling what they just
did. That set is why assigned_by had to be added: without it, a person who
assigns work to somebody else has no way of hearing that it was finished, which
was the specific gap reported.

HOW LOUD.

Three channels per event: an email carrying the full detail, a DM, and a
Notification Log entry. That is deliberate rather than excessive — realtime
only reaches somebody who is looking, push needs a subscription, and the bell
is the only one that survives being offline. The DM is what makes it
unmissable, which was the request.

The DM is sent as the actor rather than from a system account, so it reads as
"Ada assigned you this" in the thread the recipient already uses.

VOLUME CONTROL. announce() returns without sending when the only watcher is the
actor, which is the common case for somebody working their own card.
"""

import frappe
from frappe import _

MAX_DM = 900


def deep_link(doctype, name):
	"""Absolute URL that opens this exact ticket or card on the board.

	The board reads ?issue= / ?task= on load and opens the item, so the
	recipient lands on the thing the message is about rather than on the board
	and a search. Built from frappe.utils.get_url so it is correct on any site.
	"""
	try:
		from urllib.parse import quote

		key = "issue" if doctype == "Duty Issue" else "task"
		return "{0}/app/duty-board?{1}={2}".format(
			frappe.utils.get_url().rstrip("/"), key, quote(str(name), safe="")
		)
	except Exception:
		return None


def _fullname(user):
	try:
		return frappe.utils.get_fullname(user) or user
	except Exception:
		return user


def _first(user):
	return _fullname(user).split(" ")[0]


def task_watchers(doc, exclude=None):
	"""Assignee, whoever assigned it, and the creator — minus the actor."""
	out = {doc.get("assignee"), doc.get("assigned_by"), doc.get("owner")}
	return _clean(out, exclude)


def issue_watchers(doc, exclude=None):
	out = {doc.get("raised_by"), doc.get("owner")}
	for a in doc.get("assignees") or []:
		out.add(a.get("user"))
		out.add(a.get("assigned_by"))
	return _clean(out, exclude)


def _clean(users, exclude):
	exclude = exclude or frappe.session.user
	out = []
	for u in users:
		if not u or u == exclude or u in ("Administrator", "Guest"):
			continue
		row = frappe.db.get_value("User", u, ["enabled", "user_type"], as_dict=True)
		if row and row.enabled and row.user_type == "System User" and u not in out:
			out.append(u)
	return out


def _dm(to, actor, message):
	"""Insert a DM directly.

	send_dm is whitelisted and calls require_staff against the session, which is
	wrong for a system-generated message — it would refuse inside a background
	job and refuses for a consultant actor. The doctype is the same, so the row
	is written directly and the thread is identical to a typed one.
	"""
	if not to or not actor or to == actor:
		return
	try:
		frappe.get_doc(
			{
				"doctype": "Duty DM",
				"sender": actor,
				"recipient": to,
				"message": (message or "")[:MAX_DM],
				"seen": 0,
			}
		).insert(ignore_permissions=True)
		frappe.publish_realtime("duty_dm_new", {"from": actor}, user=to)
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "duty notify dm")


def _bell(to, doctype, name, subject, body):
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": to,
				"type": "Alert",
				"document_type": doctype,
				"document_name": name,
				"subject": subject[:140],
				"email_content": body or "",
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "duty notify bell")


def _email(to, subject, title, rows, note=None, link=None):
	try:
		from duty_board.notify import _kv, _send, _shell

		inner = _kv(rows)
		if note:
			inner += f'<p style="margin:12px 0 0;padding:10px 12px;background:#f6f8f7;border-radius:6px">{frappe.utils.escape_html(note)[:900]}</p>'
		if link:
			inner += (
				'<p style="margin:18px 0 0">'
				f'<a href="{link}" style="display:inline-block;background:#0F5C55;color:#fff;'
				'text-decoration:none;padding:10px 18px;border-radius:6px;font-weight:600;'
				f'font-size:14px">{_("Open it on the board")}</a></p>'
				f'<p style="margin:8px 0 0;font-size:11px;color:#8a9490">{link}</p>'
			)
		_send(to, subject, _shell(title, inner))
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "duty notify email")


def _rows_for(doc, kind):
	from duty_board.notify import _issue_rows, _task_rows

	rows = _issue_rows(doc) if kind == "issue" else _task_rows(doc)
	who = doc.get("assigned_by") if kind == "task" else None
	if who:
		rows = rows + [(_("Assigned by"), _fullname(who))]
	return rows


def announce(doc, kind, headline, body=None, actor=None, note=None, extra=None):
	"""Tell everybody who cares, on all three channels.

	headline is the one-line summary used as the DM, the bell subject and the
	email subject. body adds detail to the DM and the bell. note is free text
	shown as a quoted block in the email — a progress update, a resolution.
	"""
	actor = actor or frappe.session.user
	watchers = issue_watchers(doc, actor) if kind == "issue" else task_watchers(doc, actor)
	if not watchers:
		return 0

	doctype = "Duty Issue" if kind == "issue" else "Duty Project Task"
	label = _("Ticket") if kind == "issue" else _("Task")
	link = deep_link(doctype, doc.name)
	rows = _rows_for(doc, kind)
	if extra:
		rows = rows + list(extra)
	dm_text = headline if not body else "{0}\n{1}".format(headline, body)
	if note:
		dm_text = "{0}\n\n{1}".format(dm_text, note[:400])
	# the DM renderer linkifies bare URLs, so the plain address is clickable
	if link:
		dm_text = "{0}\n{1}".format(dm_text, link)

	for u in watchers:
		_dm(u, actor, dm_text)
		_bell(u, doctype, doc.name, headline, body or "")
		_email(u, "[Duty Board] {0}: {1}".format(headline, (doc.title or "")[:70]),
			   "{0} — {1}".format(label, headline), rows, note, link=link)
	return len(watchers)
