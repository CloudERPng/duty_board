import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class DailyTodo(Document):
	def validate(self):
		self.enforce_ownership()
		if self.status == "Done" and not self.completed_at:
			self.completed_at = now_datetime()
		elif self.status == "Open":
			self.completed_at = None

	def enforce_ownership(self):
		session = frappe.session.user
		if self.private:
			# Private is owner-only with no manager exception. The check runs
			# before the System Manager bypass on purpose.
			if self.user != session:
				frappe.throw(_("This to-do is private."), frappe.PermissionError)
			if self.assigned_by or self.project_task or self.duty_issue or self.lead:
				frappe.throw(_("A to-do someone else assigned, or one linked to a project, issue or lead, cannot be private — the people on the other end of that link need to see it."))
		if "System Manager" in frappe.get_roles():
			return
		if self.is_new():
			# you may create for yourself, or for a colleague if it is
			# attributed to you as the assigner
			if self.user != session and self.assigned_by != session:
				frappe.throw(
					_("To add a to-do for someone else it must be attributed to you.")
				)
		else:
			# once created, only the owner manages their plan
			if self.user != session:
				frappe.throw(_("You can only manage your own to-do list."))


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Feed for the Daily Todo calendar view. Staff only — consultants are
	System Users and must not read the team's day."""
	from duty_board.permissions import require_staff

	require_staff()
	from frappe.desk.calendar import get_event_conditions

	conditions = get_event_conditions("Daily Todo", filters)
	rows = frappe.db.sql(
		f"""
		select name, user, full_name, description, customer,
		       status, date, due_time, carry_count
		from `tabDaily Todo`
		where date between %(start)s and %(end)s {conditions}
		  and (ifnull(private, 0) = 0 or user = %(me)s)
		order by date asc, due_time asc
		""",
		{"start": start, "end": end, "me": frappe.session.user},
		as_dict=True,
	)

	events = []
	for r in rows:
		first_name = (r.full_name or r.user).split(" ")[0]
		title = f"{first_name}: {r.description}"
		if r.due_time:
			title = f"{str(r.due_time)[:5]} · {title}"
		if r.customer:
			title = f"{title} [{r.customer}]"

		if r.status == "Done":
			color = "#22c55e"  # green
		elif (r.carry_count or 0) > 0:
			color = "#f59e0b"  # amber — carried item
		else:
			color = "#0e7490"  # brand teal

		events.append(
			{
				"id": r.name,
				"title": title,
				"start": str(r.date),
				"end": str(r.date),
				"allDay": 1,
				"color": color,
			}
		)
	return events


# ---- desk-level enforcement. The board endpoints filter private rows
# themselves; these two close the raw list and form views at /app/daily-todo,
# where the All role would otherwise read everything. Wired from hooks.py:
#   permission_query_conditions = {"Daily Todo": "duty_board.duty_board.doctype.daily_todo.daily_todo.permission_query_conditions"}
#   has_permission = {"Daily Todo": "duty_board.duty_board.doctype.daily_todo.daily_todo.has_permission"}


def permission_query_conditions(user=None):
	user = user or frappe.session.user
	return f"(ifnull(`tabDaily Todo`.private, 0) = 0 or `tabDaily Todo`.user = {frappe.db.escape(user)})"


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if doc.get("private") and doc.get("user") != user:
		return False
	return True
