# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""Central authorization for Duty Board.

Every whitelisted endpoint in this app must fall into exactly one class:
  - staff only              → require_staff()
  - authenticated (any)     → require_authenticated()   (e.g. push subscription)
  - client room member      → client_room._client_room() membership resolution
  - deliberately public     → @frappe.whitelist(allow_guest=True), documented

Frappe exposes every whitelisted method over REST to any authenticated
session — including portal Website Users — and frappe.get_all bypasses
row permissions. UI visibility is not security; these guards are.
"""

import frappe
from frappe import _


def require_staff():
	"""Throw unless the session user is an enabled System User."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)


def require_authenticated():
	"""Throw for Guest; any logged-in user (staff or portal client) passes."""
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
