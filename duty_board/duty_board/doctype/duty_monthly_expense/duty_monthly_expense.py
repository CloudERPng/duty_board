# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyMonthlyExpense(Document):
	"""A fixed cost that comes round every month. Not a cumulative target: it is owed, then paid or not, and next month it is owed again."""

	pass
