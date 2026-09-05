# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyBookRead(Document):
	"""One pass through a book.

	A separate row per reading rather than a counter on the book, because the
	interesting question about a re-read is not how many times but when, and
	what it gave you that time — which a counter cannot hold.
	"""

	pass
