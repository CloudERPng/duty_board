# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyGrowthTarget(Document):
	"""A thing that must be worth more each month than it was the month before.

	The target is a cumulative LINE rather than a monthly quota, which is what
	makes misses carry forward without any carry-forward logic: the line has
	already moved on whether or not you kept up, so a shortfall stays visible
	until it is made good — and a strong month eats an earlier miss by itself.
	"""

	pass
