# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyNetWorthPoint(Document):
	"""What everything was worth on a day. Balances are computed and never stored, which is right — but it means there is no past unless a point is kept, and a line you cannot draw is a line you never see."""

	pass
