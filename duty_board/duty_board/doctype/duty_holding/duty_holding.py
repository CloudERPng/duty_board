# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyHolding(Document):
	"""One listed thing you own or have owned. Quantity and cost are never stored here — they are walked from the trades, so they cannot drift."""

	pass
