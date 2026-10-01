# Copyright (c) 2026, Xlevel Retail Systems Ltd
import frappe
from frappe import _
from frappe.model.document import Document


class DutyDayPlan(Document):
	def validate(self):
		seen = set()
		for r in self.budgets:
			r.key = (r.key or "").strip().lower().replace(" ", "_")[:40]
			if not r.key:
				frappe.throw(_("Every budget needs a key."))
			if r.key in seen:
				frappe.throw(_("Budget key {0} is used twice.").format(r.key))
			seen.add(r.key)
			if r.kind == "Fixed" and not r.start_time:
				frappe.throw(_("A Fixed budget needs a start time ({0}).").format(r.title))
