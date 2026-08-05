import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class DutyIssue(Document):
	def validate(self):
		if not self.raised_by:
			self.raised_by = frappe.session.user
		if self.status == "Resolved" and not self.resolved_at:
			self.resolved_at = now_datetime()
		elif self.status in ("Open", "In Progress"):
			self.resolved_at = None
