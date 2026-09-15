"""What the catalogue is missing, per track. Run on the site."""
import frappe
rows = frappe.get_all("Duty Certification Track",
    filters={"active": 1},
    fields=["name","title","audience","access","seat_price","category",
            "product","description","who_for","outcomes"],
    order_by="category asc, title asc", limit_page_length=0)
print("%-46s %-9s %-6s %s" % ("track","audience","access","missing"))
n_bad = 0
for t in rows:
    miss = []
    if not (t.category or "").strip(): miss.append("category")
    if not (t.description or "").strip(): miss.append("description")
    if not (t.who_for or "").strip(): miss.append("who_for")
    if not (t.outcomes or "").strip(): miss.append("outcomes")
    if (t.access or "") == "Paid" and not t.seat_price: miss.append("SEAT_PRICE")
    if not frappe.db.exists("Duty Lesson", {"is_sample": 1,
        "module": ["in", frappe.get_all("Duty Certification Track Module",
                    {"parent": t.name}, pluck="module") or [""]]}):
        miss.append("sample")
    if miss:
        n_bad += 1
        print("%-46s %-9s %-6s %s" % (t.title[:46], t.audience, t.access or "Included", ", ".join(miss)))
print("\n%d of %d tracks incomplete" % (n_bad, len(rows)))
