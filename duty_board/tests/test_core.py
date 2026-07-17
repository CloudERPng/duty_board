import frappe
from frappe.tests.utils import FrappeTestCase

from duty_board.api import _is_break, user_day_window
from duty_board import projects, sales


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

	def _any_customer(self):
		rows = frappe.get_all("Customer", limit=1)
		if not rows:
			self.skipTest("no Customer on this site")
		return rows[0].name

	def test_card_todo_sync_both_ways(self):
		proj = projects.create_project("__Unit Test Project", customer=self._any_customer())
		board = projects.create_task(proj, "Sync test card", assignee="Administrator")
		card_name = board["tasks"]["To Do"][0]["name"]
		linked = frappe.db.get_value("Duty Project Task", card_name, "linked_todo")
		self.assertTrue(linked, "assignment should create a linked todo")
		self.assertEqual(frappe.db.get_value("Daily Todo", linked, "status"), "Open")
		self.assertEqual(
			frappe.db.get_value("Daily Todo", linked, "customer"),
			frappe.db.get_value("Duty Project", proj, "customer"),
			"todo should inherit the project's customer",
		)

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

	def test_lead_task_rides_the_plan(self):
		lead = sales.create_lead("__Unit Test Prospect", lead_owner="Administrator", value=500000)
		payload = sales.add_lead_task(lead, "Call the MD", assignee="Administrator")
		task = payload["tasks"][0]
		todo = frappe.get_doc("Daily Todo", task["name"])
		self.assertEqual(todo.lead, lead)
		self.assertEqual(todo.lead_title, "__Unit Test Prospect")
		# done from the plan side is done on the lead
		todo.status = "Done"
		todo.save(ignore_permissions=True)
		self.assertEqual(sales.get_lead(lead)["tasks"][0]["status"], "Done")

	def test_closed_lead_leaves_the_board(self):
		lead = sales.create_lead("__Unit Test Prospect 2", lead_owner="Administrator", value=100)
		sales.close_lead(lead, "Won")
		open_names = [
			l["name"]
			for col in sales.get_pipeline()["pipeline"].values()
			for l in col["leads"]
		]
		self.assertNotIn(lead, open_names)
		self.assertIn(lead, [r["name"] for r in sales.get_closed_leads("Won")])

	def test_move_task_rejects_unknown_column(self):
		proj = projects.create_project("__Unit Test Project 2", customer=self._any_customer())
		board = projects.create_task(proj, "Column guard")
		card_name = board["tasks"]["To Do"][0]["name"]
		with self.assertRaises(frappe.ValidationError):
			projects.move_task(card_name, "Nonsense")
