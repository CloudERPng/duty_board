# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

from frappe.model.document import Document


class DutyBond(Document):
	"""A bond held to maturity, or marked by hand if it might be sold.

	Not a share with a coupon: quoted per 100 of face rather than per unit, bought with accrued interest that is a prepayment rather than a cost, and repaid at par, which is a return of capital rather than a gain."""

	pass
