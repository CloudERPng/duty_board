import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class DutyPartnerStatement(Document):
	def validate(self):
		self.gross = round(sum(flt(l.commission) for l in self.lines), 2)
		self.wht_amount = round(self.gross * flt(self.wht_rate) / 100.0, 2) if self.gross > 0 else 0
		self.net_payable = round(self.gross - self.wht_amount, 2)
		pname = frappe.db.get_value("Duty Partner", self.partner, "partner_name") or self.partner
		self.title = "%s — %s to %s" % (pname, self.period_start, self.period_end)
		if self.status == "Paid" and not self.paid_on:
			frappe.throw(_("Enter the date the partner was paid."))
