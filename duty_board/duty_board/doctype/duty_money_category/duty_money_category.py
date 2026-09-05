# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyMoneyCategory(Document):
	"""A record rather than free text.

	Typed categories drift — Fuel, fuel, Petrol — and a spending screen built on
	near-duplicates is a pile rather than an answer. A Link autocompletes, so
	drift stops at the point of entry rather than being cleaned up later. The
	same reasoning as authors and topics in the Library.
	"""

	pass
