import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, time_diff_in_seconds


class WorkSession(Document):
	def validate(self):
		self.enforce_own_session()
		self.set_duration()

	def enforce_own_session(self):
		if "System Manager" in frappe.get_roles():
			return
		if self.user != frappe.session.user:
			frappe.throw(_("You can only log work sessions for yourself."))

	def set_duration(self):
		if self.start_time and self.end_time:
			if get_datetime(self.end_time) < get_datetime(self.start_time):
				frappe.throw(_("End Time cannot be before Start Time."))
			self.duration = time_diff_in_seconds(self.end_time, self.start_time)
		else:
			self.duration = 0
