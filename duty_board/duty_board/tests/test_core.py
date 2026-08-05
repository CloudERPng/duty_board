import frappe
from frappe.tests.utils import FrappeTestCase

from duty_board.api import _is_break, user_day_window
from duty_board import api, projects, sales, client_room


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

	def _fresh_room(self):
		"""A throwaway customer + room: immune to whatever the site remembers."""
		cust = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "DB Test " + frappe.generate_hash(length=8),
		}).insert(ignore_permissions=True)
		return cust.name, client_room.create_room(cust.name)

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
		email = f"__unittest_pw_{frappe.generate_hash(length=8)}@example.com"
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

	def test_meeting_slots_respect_timed_todos(self):
		import frappe.utils as fu
		# next Monday, guaranteed weekday
		d = fu.getdate(fu.today())
		d = fu.add_days(d, (7 - d.weekday()) % 7 or 7)
		date = str(d)
		frappe.get_doc({
			"doctype": "Daily Todo", "user": "Administrator", "date": date,
			"description": "busy hour", "status": "Open", "due_time": "10:30:00",
		}).insert(ignore_permissions=True)
		slots = client_room._meeting_slots(["Administrator"], date)
		self.assertNotIn("10:00", slots, "a timed todo must block its hour")
		self.assertIn("11:00", slots)

	def test_meeting_day_cap_blanks_the_day(self):
		import frappe.utils as fu
		d = fu.getdate(fu.today())
		d = fu.add_days(d, ((7 - d.weekday()) % 7 or 7) + 1)  # next Tuesday
		date = str(d)
		room = client_room.create_room(self._any_customer())
		cust = frappe.db.get_value("Client Room", room, "customer")
		for i, slot in enumerate(["09:00:00", "11:00:00"]):
			frappe.get_doc({
				"doctype": "Duty Meeting", "room": room, "customer": cust,
				"topic": f"cap {i}", "meeting_date": date, "start_time": slot,
				"status": "Pending",
				"attendees": [{"user": "Administrator"}],
			}).insert(ignore_permissions=True)
		self.assertEqual(client_room._meeting_slots(["Administrator"], date), [],
			"two meetings must blank the whole day")

	def test_meeting_ics_shape(self):
		room_name = client_room.create_room(self._any_customer())
		room = frappe.get_doc("Client Room", room_name)
		doc = frappe.get_doc({
			"doctype": "Duty Meeting", "room": room_name, "customer": room.customer,
			"topic": "ics test", "meeting_date": "2026-08-03", "start_time": "14:00:00",
			"status": "Confirmed", "attendees": [{"user": "Administrator"}],
		}).insert(ignore_permissions=True)
		ics = client_room._meeting_ics(doc)
		self.assertIn("DTSTART;TZID=Africa/Lagos:20260803T140000", ics)
		self.assertIn("DTEND;TZID=Africa/Lagos:20260803T150000", ics)
		self.assertIn("SUMMARY:Xlevel meeting: ics test", ics)

	def test_settle_outcome_posts_to_room(self):
		room_name = client_room.create_room(self._any_customer())
		room = frappe.get_doc("Client Room", room_name)
		doc = frappe.get_doc({
			"doctype": "Duty Meeting", "room": room_name, "customer": room.customer,
			"topic": "settle test", "meeting_date": "2026-07-01", "start_time": "11:00:00",
			"status": "Confirmed", "attendees": [{"user": "Administrator"}],
		}).insert(ignore_permissions=True)
		before = frappe.db.count("Client Room Message", {"room": room_name})
		client_room.settle_meeting_outcome(doc.name, "Held", "great session")
		self.assertEqual(frappe.db.get_value("Duty Meeting", doc.name, "outcome"), "Held")
		self.assertEqual(
			frappe.db.count("Client Room Message", {"room": room_name}), before + 1
		)

	def test_department_walls(self):
		cust = self._any_customer()
		general = client_room.create_room(cust)
		hr = client_room.create_room(cust, "HR")
		self.assertNotEqual(general, hr, "units must make distinct rooms")
		g_room = frappe.get_doc("Client Room", general)
		h_room = frappe.get_doc("Client Room", hr)
		hr_issue = client_room._new_client_issue(h_room, "salary review", requested=1)
		loose = frappe.get_doc({
			"doctype": "Duty Issue", "title": "loose customer issue",
			"customer": cust, "status": "Open", "client_visible": 1,
		}).insert(ignore_permissions=True)
		g_titles = [x["title"] for x in client_room._work_rows(g_room) if x["kind"] == "issue"]
		h_titles = [x["title"] for x in client_room._work_rows(h_room) if x["kind"] == "issue"]
		self.assertNotIn("salary review", g_titles, "HR issues must not leak to General")
		self.assertIn("salary review", h_titles)
		self.assertIn("loose customer issue", g_titles, "General sweeps the unclaimed")
		self.assertNotIn("loose customer issue", h_titles)

	def test_approved_milestone_is_immutable(self):
		cust, room_name = self._fresh_room()
		room = frappe.get_doc("Client Room", room_name)
		client_room.milestones_seed(room_name)
		rows = client_room._milestone_rows(room)
		self.assertEqual(len(rows), 7, "the Xlevel method has seven phases")
		m = rows[0]
		frappe.db.set_value("Duty Milestone", m.name, {
			"status": "Approved", "approved_full": "Test Client",
		}, update_modified=False)
		with self.assertRaises(frappe.ValidationError):
			client_room.milestone_update(m.name, title="tamper attempt")
		with self.assertRaises(frappe.ValidationError):
			client_room.milestone_delete(m.name)
		with self.assertRaises(frappe.ValidationError):
			client_room.milestone_request_approval(m.name)
		self.assertEqual(
			frappe.db.get_value("Duty Milestone", m.name, "title"), rows[0].title
		)

	def test_milestone_project_customer_guard(self):
		room_name = client_room.create_room(self._any_customer())
		other_cust = frappe.get_doc({
			"doctype": "Customer", "customer_name": "Milestone Guard Other Ltd",
		}).insert(ignore_permissions=True)
		stray = frappe.get_doc({
			"doctype": "Duty Project", "project_name": "stray project",
			"customer": other_cust.name,
		}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			client_room._validate_milestone_project(room_name, stray.name)

	def test_milestone_task_linkage(self):
		cust, room_name = self._fresh_room()
		room = frappe.get_doc("Client Room", room_name)
		client_room.milestones_seed(room_name)
		ms = client_room._milestone_rows(room)[0]
		proj = frappe.get_doc({
			"doctype": "Duty Project", "project_name": "linkage project",
			"customer": room.customer,
		}).insert(ignore_permissions=True)
		cards = []
		for i, col in enumerate(["To Do", "Completed"]):
			c = frappe.get_doc({
				"doctype": "Duty Project Task", "project": proj.name,
				"title": f"card {i}", "column": col,
			}).insert(ignore_permissions=True)
			cards.append(c.name)
		import json as _json
		client_room.milestone_set_tasks(ms.name, _json.dumps(cards))
		row = [r for r in client_room._milestone_rows(room) if r.name == ms.name][0]
		self.assertEqual(row.cards_total, 2)
		self.assertEqual(row.cards_done, 1)
		self.assertEqual(len(row.tasks), 2)
		client_room.milestone_set_tasks(ms.name, _json.dumps([cards[0]]))
		row = [r for r in client_room._milestone_rows(room) if r.name == ms.name][0]
		self.assertEqual(row.cards_total, 1, "unticking must release the card")

	def test_sla_business_hours(self):
		from duty_board import api as dapi
		from datetime import datetime
		# Friday 16:00 + 4 business hours crosses the weekend to Monday 11:00
		fri = datetime(2026, 7, 17, 16, 0)
		due = dapi._bh_add(fri, 4)
		self.assertEqual((due.weekday(), due.hour), (0, 11))
		# elapsed business minutes over that same span
		self.assertEqual(dapi._bh_between(fri, due), 240)
		ack_due, res_due = dapi.sla_dues("High", fri)
		self.assertEqual((ack_due.weekday(), ack_due.hour), (4, 18))
		self.assertTrue(res_due > ack_due)

	def test_sla_met_on_quick_resolve(self):
		cust, _room = self._fresh_room()
		p = api.create_issue(title="sla probe", customer=cust, severity="High")
		row = frappe.db.get_value(
			"Duty Issue", p["name"], ["sla_ack_due", "sla_res_due"], as_dict=True
		)
		self.assertTrue(row.sla_ack_due and row.sla_res_due, "dues stamped at birth")
		api.acknowledge_issue(p["name"])
		self.assertEqual(
			frappe.db.get_value("Duty Issue", p["name"], "sla_ack_met"), 1
		)
		api.update_issue_status(p["name"], "Resolved", resolution="done fast")
		self.assertEqual(
			frappe.db.get_value("Duty Issue", p["name"], "sla_res_met"), 1
		)

	def test_report_stats(self):
		from datetime import datetime, timedelta
		cust, room_name = self._fresh_room()
		room = frappe.get_doc("Client Room", room_name)
		p = api.create_issue(
			title="report probe", customer=room.customer, severity="High"
		)
		frappe.db.set_value("Duty Issue", p["name"], "client_visible", 1, update_modified=False)
		api.acknowledge_issue(p["name"])
		api.update_issue_status(p["name"], "Resolved", resolution="ok")
		start = datetime.now() - timedelta(days=1)
		end = datetime.now() + timedelta(days=1)
		s = client_room._report_stats(room, start, end)
		self.assertEqual(s["new"], 1)
		self.assertEqual(s["resolved"], 1)
		self.assertTrue(s["activity"])
		self.assertEqual(s["ack_pct"], 100)
		self.assertEqual(s["res_pct"], 100)
		html = client_room._report_html(room, "Test Month", s)
		self.assertIn("Monthly Service Report", html)
		self.assertIn("100%", html)

	def test_academy_certificate_flow(self):
		cust, room_name = self._fresh_room()
		room = frappe.get_doc("Client Room", room_name)
		email = f"__acad_{frappe.generate_hash(length=8)}@example.com"
		client_room.add_member(room_name, email, "Acad Trainee")
		mod = client_room.training_module_add("Test Module Alpha", "ZhiftPOS")
		client_room.training_assign(room_name, mod["name"], email)
		rows = client_room._training_rows(room)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].status, "Assigned")
		client_room.training_complete(rows[0].name)
		rows = client_room._training_rows(room)
		self.assertEqual(rows[0].status, "Completed")
		self.assertTrue(rows[0].certificate_shelf)
		self.assertEqual(
			frappe.db.get_value("Client Shelf Doc", rows[0].certificate_shelf, "category"),
			"Certificate",
		)

	def test_rca_publish_and_update(self):
		cust, room_name = self._fresh_room()
		p = api.create_issue(title="rca probe", customer=cust, severity="Critical")
		frappe.db.set_value("Duty Issue", p["name"], "client_visible", 1, update_modified=False)
		client_room.rca_publish(
			p["name"],
			what_happened="it broke",
			root_cause="a wire",
			resolution_action="fixed wire",
			prevention="wire audit",
		)
		rca = frappe.db.get_value(
			"Duty RCA", {"issue": p["name"]}, ["name", "shelf_doc", "root_cause"], as_dict=True
		)
		self.assertTrue(rca and rca.shelf_doc)
		self.assertEqual(rca.root_cause, "a wire")
		client_room.rca_publish(
			p["name"],
			what_happened="it broke",
			root_cause="a deeper wire",
			resolution_action="fixed wire",
			prevention="wire audit",
		)
		self.assertEqual(
			frappe.db.get_value("Duty RCA", {"issue": p["name"]}, "root_cause"),
			"a deeper wire",
		)
		self.assertEqual(frappe.db.count("Duty RCA", {"issue": p["name"]}), 1)

	def test_kb_and_similar(self):
		cust, room_name = self._fresh_room()
		p = api.create_issue(
			title="printer spooler jammed badly", customer=cust, severity="High"
		)
		api.update_issue_status(p["name"], "Resolved", resolution="restarted spooler service")
		art = api.kb_promote(p["name"])
		self.assertTrue(art["name"])
		hits = api.kb_search("spooler")
		self.assertTrue(any(h.name == art["name"] for h in hits))
		p2 = api.create_issue(
			title="printer spooler stuck again", customer=cust, severity="High"
		)
		sim = api.similar_issues(p2["name"])
		self.assertTrue(any(i.name == p["name"] for i in sim["issues"]))
		self.assertTrue(any(k.name == art["name"] for k in sim["kb"]))

	def test_workload_and_skills(self):
		me = frappe.session.user
		before = api.skill_add(me, "UnitTestSkillZ")
		mine = next(r for r in before if r["user"] == me)
		self.assertTrue(any(s["skill"] == "UnitTestSkillZ" for s in mine["skills"]))
		rec = next(s for s in mine["skills"] if s["skill"] == "UnitTestSkillZ")
		after = api.skill_remove(rec["name"])
		mine = next(r for r in after if r["user"] == me)
		self.assertFalse(any(s["skill"] == "UnitTestSkillZ" for s in mine["skills"]))

	def test_room_health(self):
		cust, room_name = self._fresh_room()
		h = client_room._room_health(room_name)
		self.assertEqual(h["state"], "green")
		p = api.create_issue(title="unhappy probe", customer=cust, severity="Low")
		frappe.db.set_value("Duty Issue", p["name"], {
			"client_rating": "Down", "client_visible": 1,
		}, update_modified=False)
		h = client_room._room_health(room_name)
		self.assertIn(h["state"], ("amber", "red"))
		self.assertTrue(h["reasons"])

	def test_meeting_caps(self):
		cust, room_name = self._fresh_room()
		room = frappe.get_doc("Client Room", room_name)
		staff_user = frappe.session.user
		# staff daily cap: two meetings on the date → third refused
		for i in range(2):
			frappe.get_doc({
				"doctype": "Duty Meeting", "room": room_name, "customer": cust,
				"topic": f"cap probe {i}", "meeting_date": "2026-08-03",
				"start_time": f"1{i}:00:00", "duration_mins": 60, "status": "Confirmed",
				"requested_by": "Administrator",
				"attendees": [{"user": staff_user}],
			}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			client_room._meeting_caps_check(room, [staff_user], "2026-08-03")
		# customer daily cap: today's request already exists → refused
		cust2, room2_name = self._fresh_room()
		room2 = frappe.get_doc("Client Room", room2_name)
		frappe.get_doc({
			"doctype": "Duty Meeting", "room": room2_name, "customer": cust2,
			"topic": "today probe", "meeting_date": "2026-08-05",
			"start_time": "10:00:00", "duration_mins": 60, "status": "Pending",
			"requested_by": "Administrator",
			"attendees": [{"user": staff_user}],
		}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			client_room._meeting_caps_check(room2, [], "2026-08-06")

	def test_renewal_math_and_freeze(self):
		if not frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "renewal_date"}):
			frappe.get_doc({
				"doctype": "Custom Field", "dt": "Customer",
				"fieldname": "renewal_date", "label": "Renewal Date",
				"fieldtype": "Date",
			}).insert(ignore_permissions=True)
		cust, room_name = self._fresh_room()
		room = frappe.get_doc("Client Room", room_name)
		self.assertIsNone(client_room._renewal_info(cust), "no date set → no renewal info")
		frappe.db.set_value("Customer", cust, "renewal_date",
			frappe.utils.add_days(frappe.utils.today(), 23))
		info = client_room._renewal_info(cust)
		self.assertEqual(info["days_left"], 23)
		self.assertFalse(info["frozen"])
		frappe.db.set_value("Customer", cust, "renewal_date",
			frappe.utils.add_days(frappe.utils.today(), -10))
		info = client_room._renewal_info(cust)
		self.assertEqual(info["days_left"], -10)
		self.assertFalse(info["frozen"], "inside grace — not frozen")
		frappe.db.set_value("Customer", cust, "renewal_date",
			frappe.utils.add_days(frappe.utils.today(), -15))
		info = client_room._renewal_info(cust)
		self.assertTrue(info["frozen"], "past grace — frozen")
		with self.assertRaises(frappe.PermissionError):
			client_room._renewal_gate(room, allow_frozen=False)
		client_room._renewal_gate(room, allow_frozen=True)  # notice path passes

	def test_move_task_rejects_unknown_column(self):
		proj = projects.create_project("__Unit Test Project 2", customer=self._any_customer())
		board = projects.create_task(proj, "Column guard")
		card_name = board["tasks"]["To Do"][0]["name"]
		with self.assertRaises(frappe.ValidationError):
			projects.move_task(card_name, "Nonsense")
