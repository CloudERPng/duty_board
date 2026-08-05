import frappe
from frappe import _
from frappe.model.document import Document


class MessageReaction(Document):
	def validate(self):
		if "System Manager" not in frappe.get_roles():
			if self.user != frappe.session.user:
				frappe.throw(_("You can only react as yourself."))
