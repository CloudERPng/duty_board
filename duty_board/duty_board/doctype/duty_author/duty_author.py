# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyAuthor(Document):
	"""A record rather than a freehand string, so the name is written once.

	The library's author and category fields were plain Data, which meant
	'Drucker', 'Peter Drucker' and 'P. Drucker' were three different authors and
	nothing could be gathered under one of them. A Link autocompletes, so drift
	stops at the point of entry rather than being cleaned up later.
	"""

	pass
