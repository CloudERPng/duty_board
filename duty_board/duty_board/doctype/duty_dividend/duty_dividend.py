# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyDividend(Document):
	"""Cash a holding paid out. Tracked apart from price because a stock flat on price with a good yield is not dead money, and a shares tab that counts only capital movement says it is."""

	pass
