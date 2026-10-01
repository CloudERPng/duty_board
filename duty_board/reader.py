import frappe


def get_context(context):
	# The mobile reader page, served at /reader. Named 'reader' on purpose: a
	# www/library.py would collide with the duty_board.library module the API
	# runs on — the deploy script routes any .py without a Document subclass to
	# the app root, and would overwrite it. Keep this file's name distinct.
	# Guests are sent to log in and back; the library.* endpoints it calls each
	# enforce their own permission, so this page shows nothing a user could not
	# already see on the desk.
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/reader"
		raise frappe.Redirect
	context.no_cache = 1
	context.user = frappe.session.user
	return context
