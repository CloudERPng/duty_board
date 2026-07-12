import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime


class DutyLog(Document):
	def validate(self):
		self.enforce_own_log()
		self.prevent_duplicate_state()

	def enforce_own_log(self):
		"""Staff may only log for themselves. System Manager can correct records."""
		if "System Manager" in frappe.get_roles():
			return
		if self.user != frappe.session.user:
			frappe.throw(_("You can only clock in or out for yourself."))
		# Staff cannot back-date or forward-date logs
		self.log_time = now_datetime()

	def prevent_duplicate_state(self):
		"""Block Clock In when already in, and Clock Out when already out (per day)."""
		day = getdate(self.log_time)
		last = frappe.get_all(
			"Duty Log",
			filters={
				"user": self.user,
				"name": ["!=", self.name or ""],
				"log_time": [
					"between",
					[f"{day} 00:00:00", f"{day} 23:59:59"],
				],
			},
			fields=["log_type", "log_time"],
			order_by="log_time desc",
			limit=1,
		)
		last_type = last[0].log_type if last else "Clock Out"
		if self.log_type == last_type:
			if self.log_type == "Clock In":
				frappe.throw(_("You are already clocked in."))
			else:
				frappe.throw(_("You are not clocked in."))
