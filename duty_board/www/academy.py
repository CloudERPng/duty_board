import frappe

no_cache = 1


def get_context(context):
	"""The shop window.

	Everything else in the academy sits behind a login inside a client room, so
	until now there was no link a salesperson could send and no way for anybody
	to encounter the catalogue without already being a customer with an account.
	This page is that link.

	It shows what exists and what it costs. It never shows entitlement, because
	there is no room to have entitlement in — and it never shows lesson content
	except a chapter deliberately marked as a sample."""
	context.no_cache = 1
	slug = (frappe.form_dict.get("track") or "").strip()
	context.track = None
	context.tracks = []

	rows = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": "Client"},
		fields=["name", "title", "product", "description", "access", "seat_price",
				"who_for", "outcomes"],
		order_by="product asc, title asc",
	)
	for t in rows:
		mods = frappe.get_all(
			"Duty Certification Track Module", filters={"parent": t.name},
			fields=["module"], order_by="idx asc",
		)
		if not mods:
			continue
		courses, minutes, sample = [], 0, None
		for m in mods:
			title = frappe.db.get_value("Duty Training Module", m.module, "title") or m.module
			mins = 0
			for l in frappe.get_all(
				"Duty Lesson", filters={"module": m.module},
				fields=["name", "title", "est_minutes", "content", "is_sample"],
				order_by="sort_order asc, creation asc",
			):
				mins += frappe.utils.cint(l.est_minutes) or 5
				if not sample and frappe.utils.cint(l.is_sample):
					sample = {
						"course": title, "title": l.title,
						"html": frappe.utils.sanitize_html(l.content or ""),
					}
			minutes += mins
			courses.append({"title": title, "minutes": mins})
		t.courses = courses
		t.minutes = minutes
		t.hours = round(minutes / 60.0, 1) if minutes >= 60 else None
		t.sample = sample
		t.paid = (t.access or "Included") == "Paid"
		t.price = frappe.utils.fmt_money(t.seat_price, currency="NGN") if t.paid else None
		context.tracks.append(t)

	if slug:
		context.track = next((x for x in context.tracks if x.name == slug), None)
	return context
