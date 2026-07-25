import frappe

no_cache = 1


def get_context(context):
	context.no_cache = 1
	serial = (frappe.form_dict.get("serial") or "").strip()
	context.serial = serial
	context.cert = None
	if serial:
		context.cert = frappe.db.get_value(
			"Duty Certificate",
			{"serial": serial},
			["serial", "holder_name", "track_title", "product", "issued_on", "status"],
			as_dict=True,
		)
	if context.cert:
		context.cert.issued_fmt = frappe.utils.format_date(context.cert.issued_on, "d MMMM yyyy")
	return context
