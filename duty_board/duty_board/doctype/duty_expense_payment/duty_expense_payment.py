# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyExpensePayment(Document):
	"""One month of one expense, settled. Named expense::month so marking it twice updates rather than duplicating — a standing order posting and a hand tick must not both count."""

	pass
