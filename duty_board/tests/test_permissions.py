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

# module → endpoints that are NOT staff-only (everything else in it must be)
NON_STAFF = {
	"duty_board.api": set(),
	"duty_board.projects": set(),
	"duty_board.sales": set(),
	"duty_board.dm": set(),
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

	def test_document_hub_denies_clients(self):
		self._assert_denied(
			"duty_board.document_hub.doctype.client_document.client_document"
		)

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
