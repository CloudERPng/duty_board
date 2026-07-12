import frappe
from frappe import _
from frappe.model.document import Document

MAX_LENGTH = 1000


class TeamMessage(Document):
	def validate(self):
		if "System Manager" not in frappe.get_roles():
			if self.user != frappe.session.user:
				frappe.throw(_("You can only send messages as yourself."))
		if not (self.message or "").strip() and not self.attachment:
			frappe.throw(_("Message cannot be empty."))
		if self.message and len(self.message) > MAX_LENGTH:
			frappe.throw(_("Message is too long (max {0} characters).").format(MAX_LENGTH))
		self.message = (self.message or "").strip()
