# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyPricePoint(Document):
	"""One close, for one holding, on one day.

	Named {holding}::{date} so a second write for the same day updates rather
	than duplicating — a fetcher that runs twice, or a manual entry on a day
	already fetched, must not produce two points and a zig-zag in the chart.
	"""

	pass
