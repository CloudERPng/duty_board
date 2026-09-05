# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyMarketTape(Document):
	"""The last full-market snapshot.

	A Single rather than a table of 142 rows, and stored in the database rather
	than the cache — the cache empties on every restart, which is exactly how
	the shares footer came to claim nothing had ever run while prices sat on
	screen. A tape that forgets itself on a deploy is worse than no tape.
	"""

	pass
