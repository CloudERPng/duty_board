# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyRecurringTask(Document):
	"""A task that comes back: a weekly reconciliation, a hypercare check.

	The rule is the record; the tasks it makes are ordinary tasks with nothing
	special about them, so they sort, move, get timed and appear in every report
	exactly as a hand-made task does. A parallel kind of task that behaved
	differently would leak into the effort report and the curve.
	"""

	pass
