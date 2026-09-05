# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


# Frappe derives the controller class from the doctype name with spaces
# stripped — "Duty FX Rate" means DutyFXRate, not DutyFxRate. This was generated
# by title-casing the folder name, which lowercased the X in FX and produced a
# class Frappe could not find, so the table existed and every write to it raised
# ImportError.
class DutyFXRate(Document):
	"""One rate, to NGN, with the date and where it came from.

	Deliberately one row per currency rather than a history: this converts a
	target into today's money, and yesterday's rate would answer a question
	nobody asked.
	"""

	pass
