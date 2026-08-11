"""One-off migration: split the ZhiftERP certification into self-contained
product groups — ZhiftERP Selling and ZhiftERP Procurement — and rename
Buying modules to Procurement.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_tracks_split.split_zhifterp_tracks
Idempotent. Prints a diagnostic table of every ZhiftERP-family module.
"""

import frappe

SELLING_PRODUCT = "ZhiftERP Selling"
PROCURE_PRODUCT = "ZhiftERP Procurement"


def _ensure_product(title, sort_order):
	if not frappe.db.exists("Duty Product", title):
		frappe.get_doc({"doctype": "Duty Product", "title": title, "active": 1, "sort_order": sort_order}).insert(
			ignore_permissions=True
		)
		print(f"created Duty Product: {title}")


def split_zhifterp_tracks():
	_ensure_product(SELLING_PRODUCT, 5)
	_ensure_product(PROCURE_PRODUCT, 6)

	mods = frappe.get_all(
		"Duty Training Module",
		filters={"product": ["in", ["ZhiftERP", SELLING_PRODUCT, PROCURE_PRODUCT]]},
		fields=["name", "title", "product", "active", "sort_order"],
		order_by="sort_order asc, title asc",
	)
	for m in mods:
		title = m.title
		if title.startswith("Buying "):
			new_title = "Procurement " + title[len("Buying "):]
			frappe.db.set_value("Duty Training Module", m.name, "title", new_title)
			print(f"renamed: {title} -> {new_title}")
			title = new_title
		if title.startswith("Selling ") and m.product != SELLING_PRODUCT:
			frappe.db.set_value("Duty Training Module", m.name, "product", SELLING_PRODUCT)
			print(f"re-pointed to {SELLING_PRODUCT}: {title}")
		elif title.startswith("Procurement ") and m.product != PROCURE_PRODUCT:
			frappe.db.set_value("Duty Training Module", m.name, "product", PROCURE_PRODUCT)
			print(f"re-pointed to {PROCURE_PRODUCT}: {title}")

	for track_title, product in (
		("ZhiftERP Sales Professional", SELLING_PRODUCT),
		("ZhiftERP Procurement Professional", PROCURE_PRODUCT),
	):
		name = frappe.db.get_value("Duty Certification Track", {"title": track_title}, "name")
		if name and frappe.db.get_value("Duty Certification Track", name, "product") != product:
			frappe.db.set_value("Duty Certification Track", name, "product", product)
			print(f"track re-pointed: {track_title} -> {product}")

	frappe.db.commit()

	print("\n=== DIAGNOSTIC: ZhiftERP-family modules ===")
	mods = frappe.get_all(
		"Duty Training Module",
		filters={"product": ["in", ["ZhiftERP", SELLING_PRODUCT, PROCURE_PRODUCT]]},
		fields=["name", "title", "product", "active", "audience", "sort_order"],
		order_by="product asc, sort_order asc",
	)
	for m in mods:
		lessons = frappe.db.count("Duty Lesson", {"module": m.name})
		questions = frappe.db.count("Duty Quiz Question", {"module": m.name})
		flag = "" if (m.active and lessons and questions) else "   <-- CHECK"
		print(
			f"  [{m.product}] sort={m.sort_order} active={m.active} aud={m.audience} "
			f"lessons={lessons} questions={questions}  {m.title}{flag}"
		)
	left = [m for m in mods if m.product == "ZhiftERP"]
	if left:
		print(f"\nWARNING: {len(left)} module(s) still under the old ZhiftERP product (unmatched titles).")
	expected = [f"Selling {i}" for i in range(1, 9)]
	present = {m.title.split(" — ")[0] for m in mods}
	missing = [e for e in expected if e not in present]
	if missing:
		print(f"\nMISSING SELLING MODULES: {missing}")
		print("Fix: re-run the sales seed (idempotent — recreates missing modules under the new product and re-appends to the track):")
		print("  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track")
		print("Then refresh their manual content:")
		print("  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_lessons")
		print("  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_questions")
	print("\nSplit complete.")
