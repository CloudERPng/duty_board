# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyProjectDecision(Document):
	"""A decision taken on the project, and why.

	RAID is Risks, Actions, Issues and Decisions; this app had three of the four.
	On an implementation the decisions ARE the audit trail — when something is
	questioned in month five, the document that settles it is the one recording
	who agreed what, when, and what else was considered.

	track_changes is on deliberately: an edited decision keeps its history, so
	the log cannot be quietly rewritten after the fact.
	"""

	pass
