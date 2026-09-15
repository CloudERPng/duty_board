import frappe
from frappe import _
from frappe.model.document import Document


class DutyPartner(Document):
	def validate(self):
		if self.rate is not None and not (0 < float(self.rate) <= 50):
			frappe.throw(_("Rate must be between 0 and 50 percent."))
		self.email = (self.email or "").strip().lower()
