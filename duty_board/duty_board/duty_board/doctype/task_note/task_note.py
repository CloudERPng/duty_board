import frappe
from frappe import _
from frappe.model.document import Document


class TaskNote(Document):
	def validate(self):
		if "System Manager" not in frappe.get_roles():
			if self.user != frappe.session.user:
				frappe.throw(_("You can only add notes as yourself."))
		if not (self.note or "").strip():
			frappe.throw(_("Note cannot be empty."))
		self.note = self.note.strip()
