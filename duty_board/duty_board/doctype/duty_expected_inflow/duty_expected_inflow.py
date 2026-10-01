# Copyright (c) 2026, Xlevel Retail Systems Ltd
from frappe.model.document import Document
from frappe.utils import nowdate


class DutyExpectedInflow(Document):
	def validate(self):
		# the date it was ticked, cleared if it is unticked again
		if self.received and not self.received_on:
			self.received_on = nowdate()
		elif not self.received:
			self.received_on = None
