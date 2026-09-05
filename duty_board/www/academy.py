import frappe

no_cache = 1

# The order the catalogue reads in. Entry level first, then role tracks, then the
# specialist ones — somebody browsing should meet the cheapest, broadest thing
# before the NGN95,000 consultant certificate. Deliberate rather than alphabetical.
CATEGORY_ORDER = [
	"Retail & Point of Sale",
	"CRM & Ecommerce",
	"ERP by Role",
	"Finance, Control & Compliance",
	"Leadership & Management",
]


# A face and a sentence per family, drawn rather than photographed: nothing to
# host, nothing to 404 in two years, and it takes the page's own colour. Kept in
# step with the portal deliberately — a client should meet the same catalogue
# whether they arrive through the shop window or through their own login.
CAT_META = {
	"Retail & Point of Sale": {
		"blurb": "The counter and everything behind it \u2014 the till, the shift, the stock that moves through it, and the people who answer for the drawer at close.",
		"art": '<rect x="10" y="26" width="52" height="30" rx="4"/><path d="M18 26V16h36v10"/><path d="M22 38h28M22 46h16"/>',
	},
	"CRM & Ecommerce": {
		"blurb": "Leads, orders and the campaigns that create them \u2014 from the form a customer fills in to the call that closes it and the report that judges the spend.",
		"art": '<path d="M12 18h10l7 26h28l6-18H24"/><circle cx="32" cy="54" r="4"/><circle cx="52" cy="54" r="4"/>',
	},
	"ERP by Role": {
		"blurb": "One system, learned the way people actually work in it \u2014 a track per role, so a storekeeper and a payroll officer each get their own product rather than a tour of everyone else\u2019s.",
		"art": '<rect x="10" y="12" width="22" height="18" rx="3"/><rect x="40" y="12" width="22" height="18" rx="3"/><rect x="10" y="42" width="22" height="18" rx="3"/><rect x="40" y="42" width="22" height="18" rx="3"/>',
	},
	"Finance, Control & Compliance": {
		"blurb": "The books, the controls around them and the statutory work that follows \u2014 written for people who sign things rather than for people who read about signing things.",
		"art": '<path d="M36 10 12 20v14c0 14 10 24 24 30 14-6 24-16 24-30V20Z"/><path d="M27 34l7 7 13-14"/>',
	},
	"Leadership & Management": {
		"blurb": "Running a team rather than doing its work: what to look at weekly, what to say when a number is bad, and how to tell coaching from performance management.",
		"art": '<circle cx="24" cy="22" r="8"/><circle cx="48" cy="22" r="8"/><path d="M10 56c0-9 6-14 14-14s14 5 14 14"/><path d="M38 44c2-1 5-2 10-2 8 0 14 5 14 14"/>',
	},
	"Other": {
		"blurb": "Everything that does not sit in one of the families above.",
		"art": '<path d="M14 14h30a8 8 0 0 1 8 8v36H22a8 8 0 0 1-8-8Z"/><path d="M22 58a8 8 0 0 1 8-8h28"/>',
	},
}


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
	# The catalogue is three levels now, matching the client portal: families,
	# then the tracks in one, then the track. One page of everything was fine at
	# a dozen tracks and will not be at fifty.
	fam = (frappe.form_dict.get("family") or "").strip()
	context.family = fam
	context.cat_meta = CAT_META
	context.track = None
	context.tracks = []
	context.groups = []

	rows = frappe.get_all(
		"Duty Certification Track",
		filters={"active": 1, "audience": ["in", ["Client", "Both"]],
				 "private_to_room": ["in", [None, ""]]},
		fields=["name", "title", "product", "category", "description", "access",
				"seat_price", "who_for", "outcomes"],
		order_by="title asc",
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

	# Group for display. Every track carries its own Duty Product, so ordering by
	# product scattered the catalogue alphabetically — retail tracks separated by
	# ERP ones, and nothing reading as a family. Uncategorised tracks fall to the
	# end rather than disappearing.
	buckets = {}
	for t in context.tracks:
		buckets.setdefault(t.get("category") or "Other", []).append(t)
	for cat in CATEGORY_ORDER:
		if buckets.get(cat):
			context.groups.append({"title": cat, "tracks": buckets.pop(cat)})
	for cat in sorted(buckets):
		context.groups.append({"title": cat, "tracks": buckets[cat]})

	for g in context.groups:
		m = CAT_META.get(g["title"]) or CAT_META["Other"]
		g["blurb"] = m["blurb"]
		g["art"] = m["art"]
		g["free"] = len([t for t in g["tracks"] if not t.get("paid")])

	if fam:
		context.group = next((g for g in context.groups if g["title"] == fam), None)
	if slug:
		context.track = next((x for x in context.tracks if x.name == slug), None)
	return context
