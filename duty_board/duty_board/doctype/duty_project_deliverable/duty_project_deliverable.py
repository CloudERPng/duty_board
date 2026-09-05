# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyProjectDeliverable(Document):
	"""A named thing the client accepts, against criteria agreed beforehand.

	Phases already approve, but a phase is a container: signing one off says
	nothing about which document was reviewed, by whom, or against what. On an
	implementation the acceptance record is per deliverable, and criteria set
	before the work starts are what stop sign-off becoming an argument about
	taste at the end.
	"""

	pass
