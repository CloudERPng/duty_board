import frappe
from frappe.tests.utils import FrappeTestCase

from duty_board.api import _is_break, user_day_window
from duty_board import projects, sales, client_room


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

	def test_stage_move_writes_auto_note(self):
		lead = sales.create_lead("__Unit Test Prospect 3", lead_owner="Administrator")
		sales.move_lead(lead, "Contacted")
		notes = [n["note"] for n in sales.get_lead(lead)["notes"]]
		self.assertIn("→ Contacted", notes)

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

	def test_parse_mentions(self):
		from duty_board.api import parse_mentions

		found = parse_mentions("please chase this @administrator thanks")
		self.assertIn("Administrator", found)
		self.assertEqual(parse_mentions("no mentions here"), [])

	def test_card_notes(self):
		proj = projects.create_project("__Unit Test Project N", customer=self._any_customer())
		board = projects.create_task(proj, "Noted card")
		card = board["tasks"]["To Do"][0]["name"]
		payload = projects.add_card_note(card, "blocked on client VPN")
		self.assertEqual(len(payload["notes"]), 1)
		self.assertIn("VPN", payload["notes"][0]["note"])

	def test_thread_participants_collected(self):
		proj = projects.create_project("__Unit Test Project P", customer=self._any_customer())
		board = projects.create_task(proj, "Thread card", assignee="Administrator")
		card = board["tasks"]["To Do"][0]["name"]
		# posting must not raise even with participants + mentions in play
		payload = projects.add_card_note(card, "update for @administrator and the room")
		self.assertEqual(len(payload["notes"]), 1)

	def test_start_card_requires_clock_in(self):
		proj = projects.create_project("__Unit Test Project T", customer=self._any_customer())
		board = projects.create_task(proj, "Timer card")
		card = board["tasks"]["To Do"][0]["name"]
		with self.assertRaises(frappe.ValidationError):
			projects.start_card_work(card)

	def test_client_room_membrane(self):
		room = client_room.create_room(self._any_customer())
		payload = client_room.post_message(room, "visible to client")
		client_room.post_message(room, "whisper: internal only", internal=1)
		doc = frappe.get_doc("Client Room", room)
		public, _more = client_room._room_payload(doc, include_internal=False)
		texts = [m["message"] for m in public]
		self.assertIn("visible to client", texts)
		self.assertNotIn("whisper: internal only", " ".join(texts))
		both, _more = client_room._room_payload(doc, include_internal=True)
		self.assertEqual(len(both), len(public) + 1)

	def test_room_requests_land_on_issue_register(self):
		room = client_room.create_room(self._any_customer())
		client_room.make_task_from_message(room, "POS not printing receipts")
		issue = frappe.get_all(
			"Duty Issue",
			filters={"source_type": "Client Room", "source": room, "client_visible": 1},
			fields=["name", "customer", "status"],
			limit=1,
		)
		self.assertTrue(issue, "room request should create a Duty Issue")
		self.assertEqual(issue[0].status, "Open")
		titles = [t["title"] for t in client_room._visible_tasks(frappe.get_doc("Client Room", room))]
		self.assertIn("POS not printing receipts", titles)

	def test_join_request_flow(self):
		room = client_room.create_room(self._any_customer())
		token = frappe.db.get_value("Client Room", room, "invite_token")
		self.assertTrue(token)
		client_room.submit_join_request(token, "Test Client", "__unittest_client@example.com")
		req = frappe.get_all(
			"Client Join Request",
			filters={"room": room, "email": "__unittest_client@example.com"},
			limit=1,
		)
		self.assertTrue(req)
		client_room.approve_join(req[0].name)
		self.assertTrue(
			frappe.db.exists(
				"Client Room Member",
				{"room": room, "user": "__unittest_client@example.com", "active": 1},
			)
		)

	def test_room_member_mentions_scoped_to_room(self):
		room1 = client_room.create_room(self._any_customer())
		frappe.get_doc(
			{"doctype": "Client Room Member", "room": room1, "user": "Administrator", "active": 1}
		).insert(ignore_permissions=True)
		doc = frappe.get_doc("Client Room", room1)
		hits = client_room._room_member_mentions(doc, "please confirm @administrator")
		self.assertIn("Administrator", hits)
		self.assertEqual(client_room._room_member_mentions(doc, "no mentions"), [])

	def test_join_with_password_creates_disabled_user(self):
		room = client_room.create_room(self._any_customer())
		token = frappe.db.get_value("Client Room", room, "invite_token")
		email = "__unittest_pw_client@example.com"
		client_room.submit_join_request(token, "PW Client", email, password="secret123!")
		self.assertEqual(frappe.db.get_value("User", email, "enabled"), 0)
		req = frappe.get_all(
			"Client Join Request", filters={"room": room, "email": email}, limit=1
		)[0].name
		client_room.approve_join(req)
		self.assertEqual(frappe.db.get_value("User", email, "enabled"), 1)

	def test_shelf_membrane(self):
		room = client_room.create_room(self._any_customer())
		rows = client_room._shelf_rows(frappe.get_doc("Client Room", room))
		self.assertEqual(rows, [])

	def test_urgent_valve_counting(self):
		room_name = client_room.create_room(self._any_customer())
		room = frappe.get_doc("Client Room", room_name)
		for i in range(3):
			d = client_room._new_client_issue(room, f"urgent {i}", requested=1)
			frappe.db.set_value("Duty Issue", d.name, "severity", "High", update_modified=False)
		count = frappe.db.count(
			"Duty Issue",
			{
				"customer": room.customer,
				"client_requested": 1,
				"severity": "High",
				"creation": [">=", frappe.utils.today()],
			},
		)
		self.assertGreaterEqual(count, 3)

	def test_room_unread_counting(self):
		room = client_room.create_room(self._any_customer())
		client_room.post_message(room, "unread check one")
		# a different viewer has not seen it
		count = client_room._room_unread(room, "someone.else@example.com")
		self.assertGreaterEqual(count, 1)
		# the author has effectively seen their own message
		self.assertEqual(client_room._room_unread(room, frappe.session.user), 0)

	def test_narration_stays_behind_visibility(self):
		room_name = client_room.create_room(self._any_customer())
		room = frappe.get_doc("Client Room", room_name)
		d = client_room._new_client_issue(room, "narrated issue", requested=1)
		before = frappe.db.count("Client Room Message", {"room": room_name})
		frappe.db.set_value("Duty Issue", d.name, "client_visible", 0, update_modified=False)
		client_room.narrate_issue(d.name, "started")
		self.assertEqual(
			frappe.db.count("Client Room Message", {"room": room_name}), before,
			"hidden issues must not narrate",
		)
		frappe.db.set_value("Duty Issue", d.name, "client_visible", 1, update_modified=False)
		client_room.narrate_issue(d.name, "done")
		self.assertEqual(
			frappe.db.count("Client Room Message", {"room": room_name}), before + 1
		)

	def test_move_task_rejects_unknown_column(self):
		proj = projects.create_project("__Unit Test Project 2", customer=self._any_customer())
		board = projects.create_task(proj, "Column guard")
		card_name = board["tasks"]["To Do"][0]["name"]
		with self.assertRaises(frappe.ValidationError):
			projects.move_task(card_name, "Nonsense")
