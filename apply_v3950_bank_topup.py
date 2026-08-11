#!/usr/bin/env python3
"""Duty Board v3.95.0 — Selling 1 & 2 banks to the 35 standard.

Ten new questions each for customers and items_prices, drawn from
their v3.86/v3.87 manual chapters, then both full banks rebalanced.
No lesson changes — read progress is untouched; deploy refreshes
questions only.

Deploy: apply -> commit ->
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_questions --kwargs "{'only': 'customers'}"
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_questions --kwargs "{'only': 'items_prices'}"

Anchored, idempotent. Requires v3.94.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_sales_pro_data.json"
CHECK_ONLY = "--check" in sys.argv

Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

NEW_CUSTOMERS = [
Q("Creating a customer with 'only a name, details later' means:", ["Faster onboarding, no downside", "Every document inherits blanks and year-end dimensions were never captured", "The system fills the rest", "Nothing until year 2"], 1, "The master record is a contract with your future reports.", "Ch1"),
Q("In the Customer Group tree, customers attach to:", ["Any node", "Leaves only — group nodes hold children, not customers", "The root", "Two nodes at once"], 1, "Leaves attach; parents roll up.", "Ch2"),
Q("The extra power territories have that customer groups lack:", ["Colours", "Territories can carry targets", "More levels", "Currencies"], 1, "Geography as a dimension with goals attached.", "Ch3"),
Q("A 30-branch chain managed as one relationship gets its territory set:", ["Per branch, fragmenting the chain", "Where the relationship is managed — head office — with branch geography on shipping addresses", "Randomly", "As Export"], 1, "Don't fragment one chain unless regions are genuinely separate relationships.", "Ch3, Ch5"),
Q("When the client's procurement officer changes, you:", ["Rename the customer", "Edit or replace the Contact and re-flag primary — the customer and history are untouched", "Create a new customer", "Edit old documents"], 1, "Company-level customer, person-level contacts: that separation is why the layer exists.", "Ch4"),
Q("Branches become separate customers only when:", ["They have different addresses", "They are separate commercial relationships — the test is who owes the money", "They are far apart", "They sell different items"], 1, "One payer, one customer; franchisees who pay independently ARE customers.", "Ch5"),
Q("The credit limit caps:", ["Lifetime purchases", "Current unpaid exposure — open invoices plus committed-but-unbilled orders", "Order count", "Discount depth"], 1, "Exposure is what you'd lose now, not history.", "Ch6"),
Q("The credit block's value is that policy executes:", ["In month-end review", "Automatically at the point of entry, before goods leave", "After delivery", "Only for new customers"], 1, "The system does the one job charm cannot.", "Ch6"),
Q("MediPlus (30 branches, central payment) is modelled as:", ["30 customers", "One customer, ~30 shipping addresses, group Pharmacy — Chain", "One customer per state", "A supplier"], 1, "One statement, one limit that actually caps the chain, branch delivery history intact.", "Ch5, Ch8"),
Q("'The quotation shows the wrong address' is fixed by:", ["Editing the quotation", "Correcting the primary flags on the master — documents follow", "A new customer", "Deleting the address"], 1, "The anti-fix cures one document and subscribes to the ticket.", "Ch9"),
]

NEW_ITEMS = [
Q("An item with Is Sales Item unticked:", ["Appears at rate 0", "Is invisible to selling documents no matter how much stock exists", "Appears with a warning", "Can be quoted but not invoiced"], 1, "Rate-0 means unpriced; absence means not a sales item — the symptom distinguishes the diseases.", "Ch1, Ch9"),
Q("Standard Selling Rate on the item is:", ["The pricing system", "A fallback for brand-new setups — real rates live in Item Price records", "The cost", "The carton rate"], 1, "Scaffolding, not where pricing happens.", "Ch1"),
Q("The item's Default UOM is:", ["The selling unit", "The stock-keeping unit — what the warehouse counts", "The carton", "Whatever the customer wants"], 1, "Every bin quantity and valuation speaks this unit.", "Ch2"),
Q("The classic UOM field bug is:", ["A missing conversion factor", "A carton rate sitting on a unit row — 5 priced as cartons, picked as units", "Too many UOMs", "Fractional units"], 1, "Every rate must know its unit.", "Ch2, Ch9"),
Q("Designing item-group leaves per size (S, M, L) means:", ["Good granularity", "You actually wanted the variant system — one template, size variants", "More reports", "Faster entry"], 1, "Variants stop the tree absorbing jobs that aren't its.", "Ch3"),
Q("A Price List and currency relate as:", ["A list can hold many currencies", "One list, exactly one currency — the list IS a currency context", "Currency is per item", "Currency is per customer only"], 1, "Structural, not a sticker on a folder.", "Ch4"),
Q("A document's price list lands from:", ["Random selection", "The customer's default list, else the global default in Selling Settings", "The last document", "The warehouse"], 1, "The defaulting chain, recited cold.", "Ch4"),
Q("A retired price list with history is:", ["Deleted", "Disabled — history preserved, list withheld from new documents", "Renamed Misc", "Emptied"], 1, "Deleting a list with history is the wrong end.", "Ch4"),
Q("The bulk repricing workflow is:", ["300 manual edits", "Export with record IDs → edit in the sheet → re-import in update mode", "A support ticket", "New price lists per quarter"], 1, "With floor edit-rate off, this import is the only door prices move through.", "Ch6"),
Q("A USD price list on an NGN document produces:", ["An error", "Automatic conversion at the exchange rate, shown on the document", "Dollars on a naira invoice", "Zero rates"], 1, "Customer sees naira; the list stays dollars; the bridge is auditable — and converted rates are never hand-rounded.", "Ch7"),
]


def rebalance(questions):
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

    if len(data["customers"]["questions"]) >= 35 and len(data["items_prices"]["questions"]) >= 35:
        print("Already applied. Nothing to do.")
        return
    if '"3.94.0"' not in init:
        sys.exit("ABORT: not at v3.94.0.")

    problems = []
    for name, batch in (("customers", NEW_CUSTOMERS), ("items_prices", NEW_ITEMS)):
        if len(batch) != 10:
            problems.append(f"  {name}: {len(batch)} new questions (want 10)")
        for q in batch:
            if len(q["opts"]) != 4 or not (0 <= q["ans"] <= 3):
                problems.append(f"  {name}: malformed '{q['q'][:40]}'")
    if "ERPNext" in json.dumps({"a": NEW_CUSTOMERS, "b": NEW_ITEMS}):
        problems.append("  ERPNext branding leakage")
    if problems:
        print("ABORT — not clean:")
        print("\n".join(problems))
        sys.exit(1)

    for name, batch in (("customers", NEW_CUSTOMERS), ("items_prices", NEW_ITEMS)):
        merged = rebalance(data[name]["questions"] + batch)
        dist = {c: sum(1 for q in merged if q["ans"] == i) for i, c in enumerate("ABCD")}
        if max(dist.values()) > 10:
            print(f"ABORT — {name} spread failed: {dist}")
            sys.exit(1)
        print(f"{name}: bank {len(data[name]['questions'])} -> {len(merged)}, spread {dist}")
        if not CHECK_ONLY:
            data[name]["questions"] = merged

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.94.0"', '"3.95.0"'))
    print("  data: Selling 1 & 2 banks at the 35 standard — every module now 35")
    print("wrote __version__ -> 3.95.0")


if __name__ == "__main__":
    main()
