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


CONSULTANT_ROLE = "Duty Consultant"


def is_consultant(user=None):
	"""External consultant: a System User carrying the Duty Consultant role.
	They get desk credentials (so the Duty Board page opens) but must never
	pass require_staff — their access is the explicit allowlist of
	require_staff_or_consultant endpoints, each with its own scoping."""
	user = user or frappe.session.user
	if not user or user in ("Guest", "Administrator"):
		return False
	return CONSULTANT_ROLE in frappe.get_roles(user)


def require_staff():
	"""Throw unless the session user is an enabled System User who is NOT
	an external consultant. This single check walls consultants out of
	every staff endpoint; doors are opened one by one via
	require_staff_or_consultant."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if is_consultant(user):
		frappe.throw(_("Not permitted."), frappe.PermissionError)


def require_staff_or_consultant():
	"""System-User gate that ADMITS consultants. Returns True when the
	caller is a consultant so the endpoint can apply its scoping filters
	(room membership, issue assignment, project membership)."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	if frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	return is_consultant(user)


def setup_consultants(dry_run=1):
	"""bench execute duty_board.permissions.setup_consultants --kwargs "{'dry_run': 0}"
	Creates the Duty Consultant role. Idempotent."""
	from frappe.utils import cint

	made = []
	if not frappe.db.exists("Role", CONSULTANT_ROLE):
		if not cint(dry_run):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": CONSULTANT_ROLE,
				"desk_access": 1,
			}).insert(ignore_permissions=True)
			frappe.db.commit()
		made.append(f"Role '{CONSULTANT_ROLE}'")

	# --- Duty Board page access diagnosis & repair -------------------
	# frappe's Page.is_permitted allows everyone when no roles are set,
	# BUT a site-level Custom Role record (made via 'Role Permissions
	# for Page and Report') overrides that and restricts to its list.
	page_roles = [
		d.role for d in frappe.get_all(
			"Has Role", filters={"parent": "duty-board", "parenttype": "Page"},
			fields=["role"],
		)
	]
	cr_name = frappe.db.get_value("Custom Role", {"page": "duty-board"})
	cr_roles = []
	if cr_name:
		cr_roles = [
			d.role for d in frappe.get_all(
				"Has Role", filters={"parent": cr_name, "parenttype": "Custom Role"},
				fields=["role"],
			)
		]
	print(f"Page 'duty-board' — standard roles: {page_roles or 'NONE (open)'}"
		f" | Custom Role: {cr_name or 'none'} → {cr_roles or '—'}")
	effective = cr_roles or page_roles
	if effective and CONSULTANT_ROLE not in effective:
		if cr_name:
			if not cint(dry_run):
				doc = frappe.get_doc("Custom Role", cr_name)
				doc.append("roles", {"role": CONSULTANT_ROLE})
				doc.save(ignore_permissions=True)
				frappe.db.commit()
			made.append(f"'{CONSULTANT_ROLE}' appended to Custom Role {cr_name}")
		else:
			print("⚠ page restricted via standard roles — add Duty Consultant "
				"to the Page doc's roles or clear them.")

	print(("DRY RUN — would apply: " if cint(dry_run) else "Applied: ")
		+ (", ".join(made) or "nothing (already in place)"))


def require_authenticated():
	"""Throw for Guest; any logged-in user (staff or portal client) passes."""
	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw(_("Not permitted."), frappe.PermissionError)


def consultant_customers(user=None):
	"""Customers whose rooms the consultant is an active member of."""
	user = user or frappe.session.user
	rooms = frappe.get_all(
		'Client Room Member', filters={'user': user, 'active': 1}, pluck='room'
	)
	if not rooms:
		return set()
	return set(
		frappe.get_all(
			'Client Room', filters={'name': ['in', rooms]}, pluck='customer'
		)
	)


def consultant_room_names(user=None):
	user = user or frappe.session.user
	return set(
		frappe.get_all(
			'Client Room Member', filters={'user': user, 'active': 1}, pluck='room'
		)
	)


def consultant_project_names(user=None):
	"""Projects the consultant is granted on, via the consultants child table."""
	user = user or frappe.session.user
	return set(
		frappe.get_all(
			"Duty Project Consultant", filters={"user": user}, pluck="parent"
		)
	)


def get_user_rate(user):
	"""Hourly cost for cost-to-serve. Priority: explicit per-user row in
	Duty Settings → consultant default (consultant_cost_per_hour, else 3×
	staff rate) → staff rate."""
	from frappe.utils import flt

	row = frappe.db.get_value(
		"Duty User Rate",
		{"parent": "Duty Settings", "user": user},
		"hourly_cost",
	)
	if row:
		return flt(row)
	staff_rate = flt(frappe.db.get_single_value("Duty Settings", "staff_cost_rate"))
	if is_consultant(user):
		c = flt(frappe.db.get_single_value("Duty Settings", "consultant_cost_per_hour"))
		return c or staff_rate * 3
	return staff_rate
