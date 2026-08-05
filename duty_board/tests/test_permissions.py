# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Negative access-control tests.

A portal client is an authenticated Website User on the same site, and every
@frappe.whitelist() method is callable over REST. These tests log in as a
Website User and call every staff endpoint; each must raise PermissionError.

Run:  bench --site xlevel.clouderp.one run-tests --module duty_board.tests.test_permissions
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

CLIENT_EMAIL = "perm-test-client@example.com"
CONSULTANT_EMAIL = "perm-test-consultant@example.com"

# module → endpoints an external consultant MAY call (opened deliberately,
# each with its own membership/assignment scoping). Everything else must
# deny the Duty Consultant role even though they are System Users.
CONSULTANT_ALLOWED = {
	"duty_board.api": {
		"consultant_gate", "get_board", "get_issues", "get_issue",
		"issue_updates", "issue_update_add", "update_issue",
		"update_issue_status", "start_issue_work", "stop_issue_work",
		"create_issue", "remove_assignee", "my_dashboard", "cr_accept", "my_customer_options", "checklist_add", "checklist_toggle", "checklist_remove",
	},
	"duty_board.projects": {
		"get_projects", "get_project_board", "create_task", "get_card",
		"move_task", "update_task", "reschedule_task", "add_card_note",
		"start_card_work", "stop_card_work", "subtask_add",
		"subtask_update", "subtask_toggle", "subtask_delete",
	},
	"duty_board.sales": set(),
	"duty_board.dm": set(),
	"duty_board.commercial": set(),
	"duty_board.gamify": set(),
	"duty_board.news": {"get_news"},
	"duty_board.notify": set(),
	"duty_board.uat": set(),
	"duty_board.timeline": set(),
	"duty_board.library": {
		"library", "open_book", "chapter", "mark", "reading_overview",
		"rate_book", "book_reviews", "search_books",
		"highlight_add", "highlight_remove", "highlights", "my_highlights", "search_in_book",
		"bookmark_add", "bookmark_remove", "bookmarks",
	},
	"duty_board.accounting": set(),
}

# module → endpoints that are NOT staff-only (everything else in it must be)
NON_STAFF = {
	"duty_board.api": set(),
	"duty_board.projects": set(),
	"duty_board.sales": set(),
	"duty_board.dm": set(),
	"duty_board.commercial": set(),
	"duty_board.gamify": set(),
	"duty_board.news": set(),
	"duty_board.notify": set(),
	"duty_board.uat": set(),
	"duty_board.timeline": set(),
	"duty_board.library": set(),
	"duty_board.accounting": {
		# client portal endpoints, guarded by room membership resolution
		"client_get_deliverables",
		"client_ack_deliverable",
		"client_get_followups",
		"client_answer_query",
		"client_fulfill_request",
	},
}


def _whitelisted(module_path):
	mod = frappe.get_module(module_path)
	out = []
	for name, fn in inspect.getmembers(mod, inspect.isfunction):
		if fn.__module__ != module_path:
			continue
		if fn in frappe.whitelisted or getattr(fn, "__wrapped__", None) in frappe.whitelisted:
			out.append((name, fn))
	return out


class TestStaffEndpointsDenyClients(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", CLIENT_EMAIL):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": CLIENT_EMAIL,
					"first_name": "Perm",
					"last_name": "TestClient",
					"user_type": "Website User",
					"enabled": 1,
				}
			).insert(ignore_permissions=True)
		from duty_board.permissions import CONSULTANT_ROLE

		if not frappe.db.exists("Role", CONSULTANT_ROLE):
			frappe.get_doc(
				{"doctype": "Role", "role_name": CONSULTANT_ROLE, "desk_access": 1}
			).insert(ignore_permissions=True)
		if not frappe.db.exists("User", CONSULTANT_EMAIL):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": CONSULTANT_EMAIL,
					"first_name": "Perm",
					"last_name": "TestConsultant",
					"user_type": "System User",
					"enabled": 1,
					"roles": [{"role": CONSULTANT_ROLE}],
				}
			).insert(ignore_permissions=True)
		frappe.db.commit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _assert_denied(self, module_path):
		allowed_failures = NON_STAFF.get(module_path, set())
		for name, fn in _whitelisted(module_path):
			if name in allowed_failures:
				continue
			frappe.set_user(CLIENT_EMAIL)
			sig = inspect.signature(fn)
			kwargs = {
				p.name: None
				for p in sig.parameters.values()
				if p.default is inspect.Parameter.empty
				and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
			}
			with self.assertRaises(
				frappe.PermissionError,
				msg=f"{module_path}.{name} did NOT deny a Website User",
			):
				fn(**kwargs)
			frappe.set_user("Administrator")

	def test_api_denies_clients(self):
		self._assert_denied("duty_board.api")

	def test_projects_denies_clients(self):
		self._assert_denied("duty_board.projects")

	def test_sales_denies_clients(self):
		self._assert_denied("duty_board.sales")

	def test_dm_denies_clients(self):
		self._assert_denied("duty_board.dm")

	def test_commercial_denies_clients(self):
		self._assert_denied("duty_board.commercial")

	def test_gamify_denies_clients(self):
		self._assert_denied("duty_board.gamify")

	def test_news_denies_clients(self):
		self._assert_denied("duty_board.news")

	def test_notify_denies_clients(self):
		self._assert_denied("duty_board.notify")

	def test_uat_denies_clients(self):
		self._assert_denied("duty_board.uat")

	def test_timeline_denies_clients(self):
		self._assert_denied("duty_board.timeline")

	def test_library_denies_clients(self):
		self._assert_denied("duty_board.library")

	def test_document_hub_denies_clients(self):
		self._assert_denied(
			"duty_board.document_hub.doctype.client_document.client_document"
		)

	def _assert_consultant_denied(self, module_path):
		"""A consultant is a System User — the exact trap require_staff's
		hardening exists for. Everything outside CONSULTANT_ALLOWED must
		raise PermissionError."""
		allowed = CONSULTANT_ALLOWED.get(module_path, set())
		also_open = NON_STAFF.get(module_path, set())
		for name, fn in _whitelisted(module_path):
			if name in allowed or name in also_open:
				continue
			frappe.set_user(CONSULTANT_EMAIL)
			sig = inspect.signature(fn)
			kwargs = {
				p.name: None
				for p in sig.parameters.values()
				if p.default is inspect.Parameter.empty
				and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
			}
			with self.assertRaises(
				frappe.PermissionError,
				msg=f"{module_path}.{name} did NOT deny a Duty Consultant (System User)",
			):
				fn(**kwargs)
			frappe.set_user("Administrator")

	def test_consultant_denied_api(self):
		self._assert_consultant_denied("duty_board.api")

	def test_consultant_denied_projects(self):
		self._assert_consultant_denied("duty_board.projects")

	def test_consultant_denied_sales(self):
		self._assert_consultant_denied("duty_board.sales")

	def test_consultant_denied_dm(self):
		self._assert_consultant_denied("duty_board.dm")

	def test_consultant_denied_commercial(self):
		self._assert_consultant_denied("duty_board.commercial")

	def test_consultant_denied_uat(self):
		self._assert_consultant_denied("duty_board.uat")

	def test_consultant_denied_timeline(self):
		self._assert_consultant_denied("duty_board.timeline")

	def test_consultant_denied_library(self):
		self._assert_consultant_denied("duty_board.library")

	def test_consultant_denied_accounting(self):
		self._assert_consultant_denied("duty_board.accounting")

	def test_guest_denied_everywhere(self):
		frappe.set_user("Guest")
		from duty_board.permissions import require_authenticated, require_staff

		with self.assertRaises(frappe.PermissionError):
			require_staff()
		with self.assertRaises(frappe.PermissionError):
			require_authenticated()
		frappe.set_user("Administrator")

	def test_staff_passes_guard(self):
		frappe.set_user("Administrator")
		from duty_board.permissions import require_staff

		require_staff()  # must not raise
