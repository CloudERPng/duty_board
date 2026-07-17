import frappe
from frappe.tests.utils import FrappeTestCase

from duty_board.api import _is_break, user_day_window
from duty_board import projects


class TestDutyBoardCore(FrappeTestCase):
	def test_is_break(self):
		self.assertTrue(_is_break("Lunch"))
		self.assertTrue(_is_break("Gone for prayers"))
		self.assertFalse(_is_break("End of day"))
		self.assertFalse(_is_break("Auto clock-out (forgot to clock out)"))

	def test_user_day_window_spans_a_day(self):
		start, end = user_day_window("Administrator")
		self.assertLess(start, end)
		self.assertAlmostEqual((end - start).total_seconds(), 86399, delta=5)

	def test_card_todo_sync_both_ways(self):
		proj = projects.create_project("__Unit Test Project")
		board = projects.create_task(proj, "Sync test card", assignee="Administrator")
		card_name = board["tasks"]["To Do"][0]["name"]
		linked = frappe.db.get_value("Duty Project Task", card_name, "linked_todo")
		self.assertTrue(linked, "assignment should create a linked todo")
		self.assertEqual(frappe.db.get_value("Daily Todo", linked, "status"), "Open")

		# card -> Completed ticks the todo
		projects.move_task(card_name, "Completed")
		self.assertEqual(frappe.db.get_value("Daily Todo", linked, "status"), "Done")

		# reopening the todo pulls the card back to In Progress
		todo = frappe.get_doc("Daily Todo", linked)
		todo.status = "Open"
		todo.save(ignore_permissions=True)
		self.assertEqual(
			frappe.db.get_value("Duty Project Task", card_name, "column"), "In Progress"
		)

		# ticking the todo done completes the card
		todo.reload()
		todo.status = "Done"
		todo.save(ignore_permissions=True)
		self.assertEqual(
			frappe.db.get_value("Duty Project Task", card_name, "column"), "Completed"
		)

	def test_move_task_rejects_unknown_column(self):
		proj = projects.create_project("__Unit Test Project 2")
		board = projects.create_task(proj, "Column guard")
		card_name = board["tasks"]["To Do"][0]["name"]
		with self.assertRaises(frappe.ValidationError):
			projects.move_task(card_name, "Nonsense")
