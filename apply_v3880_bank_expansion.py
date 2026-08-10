#!/usr/bin/env python3
"""Duty Board v3.88.0 — question banks at manual depth (Selling 1 & 2).

The banks still reflected the brief materials, and carried a tell:
every correct answer sat at option B. Both fixed:
- Selling 1 and Selling 2 banks grow 12 -> 25 questions each, the 13
  new per module drawn from the manual chapters (case-study
  application, support-pattern diagnosis, deeper mechanics), correct
  answers spread across positions.
- Seeder gains refresh_questions(only=None): replaces a seeded
  module's question bank from the data file. Attempts/scores keep
  their stored results; future sittings draw from the new bank.
- 10-of-25 served makes every sitting a materially different paper.

Going forward every manual-depth pass ships its bank expansion in the
same patch.

Deploy: apply -> commit -> refresh both banks:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_questions --kwargs "{'only': 'customers'}"
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_questions --kwargs "{'only': 'items_prices'}"

Anchored, idempotent. Requires v3.87.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_sales_pro_data.json"
SEED_PATH = "duty_board/academy_seed_sales_pro.py"
CHECK_ONLY = "--check" in sys.argv

Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

NEW_CUSTOMERS = [
Q("At onboarding, when is the right moment to capture a company customer's TIN?", ["At onboarding, while goodwill is high", "At first invoice", "When FIRS asks", "Only for government customers"], 0, "Chasing TINs at invoice time stalls billing; capture at creation.", "Ch1"),
Q("A healthy B2B customer record carries at least which three contacts?", ["Three procurement officers", "MD, chairman, secretary", "Commercial, operational, and finance contacts", "Any three staff"], 2, "Quotations, deliveries, and collections each need a named person.", "Ch4"),
Q("The customer's territory for a 30-branch chain managed from head office should be:", ["Split across all branch territories", "The head office's territory, with branch geography on shipping addresses", "The largest branch's territory", "Export"], 1, "One relationship, one territory; branch geography lives on addresses.", "Ch3, Ch5"),
Q("Franchise branches that buy and pay independently should be modelled as:", ["Shipping addresses of the franchisor", "One customer with 30 contacts", "Separate customers — the test is who owes the money", "A customer group only"], 2, "Independent payers are independent commercial relationships.", "Ch5"),
Q("What makes 'Default Customer Group' safe rather than a landfill?", ["Pointing it at the root group", "A real common leaf plus a weekly review of newly created customers", "Disabling customer creation", "A naming series"], 1, "Defaults are a safety net; the review catches misfiles young.", "Ch2, Ch7"),
Q("Credit limits should be reviewed:", ["Never — they're policy", "Only when a customer complains", "On a cadence (e.g. quarterly) against AR ageing", "Daily"], 2, "Flawless payers at high utilisation get raises; 61-90 dwellers get cuts.", "Ch6"),
Q("A rep hits the credit block. Per the workflow, the message to the controller carries:", ["An apology and a promise", "Amount over, the customer's ageing, expected payment date", "The customer's phone number", "A discount proposal"], 1, "Three facts let the controller decide in sixty seconds.", "Ch6"),
Q("A support user asks you to grant their login the credit bypass 'so this stops happening'. You:", ["Grant it — it's one checkbox", "Escalate to management — it's a request to disable credit control", "Grant it for a week", "Delete the credit limit instead"], 1, "Permanent bypass for sales is credit control switched off.", "Ch9"),
Q("MediPlus's 30 branch addresses are best entered by:", ["Typing all 30 by hand", "One address reused with edits per order", "A data import of the address file", "Asking drivers to remember"], 2, "Thirty structured records is an import job, not an afternoon of typing.", "Ch8"),
Q("Reports show most sales under 'All Customer Groups'. The backward fix is:", ["Nothing — history is history", "Delete those customers", "A one-time regrouping exercise; reports speak from when assignments are true", "Rename the root group"], 2, "Forward hygiene plus one cleanup; unassigned history stays unsegmentable until regrouped.", "Ch9"),
Q("The deepest law of foundations support is:", ["Documents are downstream of masters — find the lying master", "Users cause all tickets", "Restart the server first", "Escalate everything"], 0, "Every recurring document symptom traces to a master-data disease.", "Ch9"),
Q("Why must the Credit Controller role sit in finance rather than sales?", ["Finance works longer hours", "The person who wants the deal must not be the one who waives the risk", "Sales lacks system access", "It's a licensing rule"], 1, "Separation of desire and approval is the point of the role.", "Ch6"),
Q("Verifying a new customer setup end-to-end is best done by:", ["Waiting for the first live order", "A draft test quotation checking list, currency, contact, addresses — then deleted", "Reading the record twice", "Asking the customer"], 1, "Ten minutes of draft-document verification beats a wrong first shipment.", "Ch8"),
]

NEW_ITEMS = [
Q("On a document row, 'Price List Rate' vs 'Rate' means:", ["They are always equal", "List's looked-up truth vs what this document charges — overrides change Rate only", "Rate is tax-inclusive", "Price List Rate is editable, Rate is not"], 1, "The pair is how override reporting compares charged against list.", "Ch5"),
Q("A planned price change for the 1st of next month is executed cleanly by:", ["A reminder to edit prices that morning", "Validity-dated new Item Price rows (valid-from the 1st) with old rows ended the day before", "A pricing rule", "Editing rates on open quotations"], 1, "The change executes itself at midnight with a perfect trail.", "Ch6"),
Q("Bulk repricing imports must run in:", ["Create mode — new rows are safer", "Update mode matched on record ID", "Delete-then-create", "Any mode"], 1, "Create mode orphans the live rows; update amends the real records.", "Ch6"),
Q("Before editing the exported price sheet, the workflow requires:", ["Manager sign-off", "A dated backup export — it IS the rollback and the price history", "Closing all quotations", "Disabling the price list"], 1, "Dated exports make any Monday's prices reconstructible.", "Ch6"),
Q("Brand analysis across Beverages should rely on:", ["Brand-flavoured item group leaves", "The Brand field on items, keeping the tree one-question", "Separate price lists per brand", "Item codes containing brand names"], 1, "Brand has its own field; the tree answers only 'what kind of product'.", "Ch3"),
Q("A polo shirt in five sizes is correctly modelled as:", ["Five unrelated items", "Five item-group leaves", "One template item with variants", "One item, sizes in remarks"], 2, "Variants exist precisely for true variations of one product.", "Ch3"),
Q("An export deal struck at a locked exchange rate is handled by:", ["Editing the USD price list", "A deliberate conversion-rate override on that document", "A new price list per deal", "Charging in naira cash"], 1, "The list stays pure; the deal's rate is visible on the document.", "Ch7"),
Q("Kobo-level fractions from currency conversion are absorbed by:", ["Hand-rounding the row rate", "Currency precision and the document's rounding row", "Ignoring them", "A discount"], 1, "Payment allocation must later match the document to the kobo.", "Ch7"),
Q("Standard Selling Rate on the item is:", ["The pricing system", "A fallback used when no Item Price exists — scaffolding, not policy", "The maximum price", "The cost price"], 1, "Real rates live in Item Price records against lists.", "Ch1"),
Q("Item and Item Price rows both declare a UOM so that:", ["Print formats look complete", "The carton rate can never silently price a unit row — the 12x error", "Stock reports run faster", "Imports validate"], 1, "Every rate knows its unit; incoherence is the silent multiplier bug.", "Ch2, Ch5"),
Q("A service item blocking invoices for 'insufficient stock' has:", ["Is Sales Item unticked", "Maintain Stock ticked in error", "No item group", "No price"], 1, "Services must not maintain stock; the flag was mis-set at creation.", "Ch1"),
Q("Distributor prices moved when retail was repriced. The structural fix is:", ["Reprice distributors back", "A separate distributor price list replacing the %-off coupling", "A memo", "Locking the retail list"], 1, "Channels coupled by a discount reprice together; separate lists decouple.", "Ch9"),
Q("With sales-floor rate editing off, prices change through:", ["Any user's document edits", "The owned import workflow — one owner, one method, one trail", "Support tickets", "Month-end journals"], 1, "One door for price movement is what survives audits and arguments.", "Ch6"),
]

REFRESH_Q_SRC = '''

def refresh_questions(only=None):
	"""Replace a seeded module's question bank from the data file
	(matched by title). Past attempts keep their stored results; future
	sittings draw from the new bank. Pass only=<module_key> for one
	module, else all in ORDER."""
	data = _data()
	keys = [only] if only else ORDER
	for key in keys:
		if key not in data:
			print(f"unknown module key: {key}")
			continue
		m = data[key]
		mod = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
		if not mod:
			print(f"module not seeded yet (skipped): {m['title']}")
			continue
		for row in frappe.get_all("Duty Quiz Question", filters={"module": mod}, pluck="name"):
			frappe.delete_doc("Duty Quiz Question", row, ignore_permissions=True, force=True)
		for q in m["questions"]:
			frappe.get_doc(
				{
					"doctype": "Duty Quiz Question",
					"module": mod,
					"question": q["q"],
					"opt_a": q["opts"][0],
					"opt_b": q["opts"][1],
					"opt_c": q["opts"][2],
					"opt_d": q["opts"][3],
					"correct": "ABCD"[q["ans"]],
					"rationale": q["why"],
					"source": q["src"],
					"active": 1,
				}
			).insert(ignore_permissions=True)
		print(f"bank refreshed: {m['title']} ({len(m['questions'])} questions)")
	frappe.db.commit()
	print("Question banks refreshed.")
'''




def rebalance(questions):
    """Deterministically spread correct answers across A-D by swapping
    the correct option into position (index % 4). Kills the all-B tell."""
    for i, q in enumerate(questions):
        target = i % 4
        a = q["ans"]
        if a != target:
            q["opts"][a], q["opts"][target] = q["opts"][target], q["opts"][a]
            q["ans"] = target
    return questions

def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)
    with io.open(os.path.join(root, SEED_PATH), encoding="utf-8") as f:
        seed = f.read()

    if len(data["customers"]["questions"]) >= 25:
        print("Already applied. Nothing to do.")
        return
    if '"3.87.0"' not in init:
        sys.exit("ABORT: not at v3.87.0.")

    problems = []
    if "def refresh_lessons(only=None)" not in seed:
        problems.append("  seeder missing refresh_lessons(only) — chain broken")
    if "def refresh_questions(" in seed:
        problems.append("  refresh_questions already present")
    for name, batch in (("customers", NEW_CUSTOMERS), ("items_prices", NEW_ITEMS)):
        if len(batch) != 13:
            problems.append(f"  {name}: {len(batch)} new questions (want 13)")
        for q in batch:
            if len(q["opts"]) != 4 or not (0 <= q["ans"] <= 3):
                problems.append(f"  {name}: malformed '{q['q'][:40]}'")
    if "ERPNext" in json.dumps(NEW_CUSTOMERS + NEW_ITEMS):
        problems.append("  ERPNext branding leakage")
    if problems:
        print("ABORT — not clean:")
        print("\n".join(problems))
        sys.exit(1)

    for name, batch in (("customers", NEW_CUSTOMERS), ("items_prices", NEW_ITEMS)):
        merged = rebalance(data[name]["questions"] + batch)
        dist = {c: sum(1 for q in merged if q["ans"] == i) for i, c in enumerate("ABCD")}
        print(f"  {name}: bank -> {len(merged)}; answer spread after rebalance {dist}")
        if max(dist.values()) > 8:
            print("ABORT — rebalance failed to spread answers")
            sys.exit(1)
        data[name]["questions"] = merged

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, SEED_PATH), "w", encoding="utf-8") as f:
        f.write(seed + REFRESH_Q_SRC)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.87.0"', '"3.88.0"'))
    print("  data: +13 questions each (Selling 1 & 2) · seeder: +refresh_questions(only=...)")
    print("wrote __init__.py -> 3.88.0")


if __name__ == "__main__":
    main()
