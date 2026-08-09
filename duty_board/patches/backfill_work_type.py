"""Stamp work_type onto historical Work Sessions where derivable from
linkage: project_task -> ERP Delivery, duty_issue -> ERP Support.

Unlinked history is deliberately left untyped — it needs a human call
(Accounting vs Internal), made once per team via bulk SQL, which also
seeds each person's sticky default. Idempotent: only touches rows where
work_type is empty.
"""

import frappe


def execute():
	if "duty_board" not in frappe.get_installed_apps():
		return
	if not frappe.db.has_column("Work Session", "work_type"):
		return
	frappe.db.sql(
		"""update `tabWork Session`
		set work_type = 'ERP Delivery'
		where coalesce(work_type, '') = '' and coalesce(project_task, '') != ''"""
	)
	frappe.db.sql(
		"""update `tabWork Session`
		set work_type = 'ERP Support'
		where coalesce(work_type, '') = '' and coalesce(duty_issue, '') != ''"""
	)
	frappe.db.commit()
