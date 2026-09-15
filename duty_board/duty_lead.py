import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class DutyLead(Document):
	def validate(self):
		# Attribution follows `partner`; the timestamp is the evidence. When
		# staff assign a partner to an existing lead by hand, stamp it now —
		# the twelve-month lapse runs from this moment, not from the lead's
		# creation, because the partner had no say in when we opened it.
		if self.partner and not self.partner_registered_on:
			self.partner_registered_on = now_datetime()
			if self.status == "Won":
				frappe.throw(_("This lead is already Won. Attribute the customer directly with a Duty Partner Client record instead."))
		if not self.partner:
			self.partner_registered_on = None
