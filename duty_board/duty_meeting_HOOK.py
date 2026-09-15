# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DutyMeeting(Document):
	"""A meeting, and the calendar invitation that goes with it.

	RESCHEDULING USED TO LEAVE EVERY CALENDAR WRONG. The invitation was sent on
	confirmation and withdrawn on cancellation, and nothing sat in between — so
	moving a confirmed meeting updated this record and nobody's calendar heard
	about it. Attendees turned up at the old time, or did not turn up at all.

	The re-send lives here rather than in an endpoint on purpose: a date can be
	changed from the desk form, from a script, or from a future screen nobody
	has written yet, and a fix that only covers one route is a fix that comes
	undone the first time somebody uses another.
	"""

	WATCHED = ("meeting_date", "start_time", "duration_mins", "topic")

	def on_update(self):
		if self.status != "Confirmed":
			# an unconfirmed meeting has no invitation out there to correct
			return
		before = self.get_doc_before_save()
		if not before:
			return
		if before.status != "Confirmed":
			# confirm_meeting sends its own invitation; re-sending here would
			# put two in every inbox
			return
		changed = [f for f in self.WATCHED if str(before.get(f) or "") != str(self.get(f) or "")]
		if not changed:
			return
		try:
			from duty_board.client_room import _send_meeting_invite

			# SEQUENCE bumps inside, so the calendar replaces the old entry
			# rather than adding a second one
			_send_meeting_invite(self, "REQUEST")
			frappe.logger().info(
				"duty_meeting %s re-invited after change to %s" % (self.name, ", ".join(changed)))
		except Exception:
			frappe.log_error(frappe.get_traceback()[-800:], "meeting re-invite")
