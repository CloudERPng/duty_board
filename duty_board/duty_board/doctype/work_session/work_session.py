import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, time_diff_in_seconds


class WorkSession(Document):
	def validate(self):
		self.enforce_own_session()
		self.set_duration()
		self.set_work_type()

	def set_work_type(self):
		"""Service line: explicit choice wins; else derived from linkage;
		else sticky (user's last choice on unlinked work). Left empty when
		nothing is known — Untyped is visible, a silent guess is not."""
		if self.work_type:
			return
		if self.project_task:
			self.work_type = "ERP Delivery"
		elif self.duty_issue:
			self.work_type = "ERP Support"
		else:
			last = frappe.db.get_value(
				"Work Session",
				{
					"user": self.user,
					"work_type": ["in", ["Accounting Service", "Internal & Product"]],
				},
				"work_type",
				order_by="creation desc",
			)
			if last:
				self.work_type = last

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
