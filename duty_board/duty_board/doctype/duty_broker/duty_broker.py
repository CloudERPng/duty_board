# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyBroker(Document):
	"""Where shares are actually held. The same stock can sit at two brokers, so the broker belongs on the trade rather than on the holding — you may buy MTNN through one and add to it through another."""

	pass
