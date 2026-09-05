# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyPlannedOutflow(Document):
	"""Money you intend to spend once, on a date.

	Neither a fixed cost nor a standing order: it does not recur, so it must not
	carry forward when missed, and it does not post itself, because deciding to
	spend it is the whole point. It competes with the growth targets rather than
	pausing them — a television does not make a savings target smaller, and the
	shortfall it creates should be visible rather than absorbed.
	"""

	pass
