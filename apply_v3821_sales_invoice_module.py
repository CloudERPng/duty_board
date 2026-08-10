#!/usr/bin/env python3
"""Duty Board v3.82.1 — Selling 7: The Sales Invoice, Payments & Collections.

The invoice had lessons inside Module 6 but no dedicated session — wrong
for the accounting event of the entire cycle. This adds a full seventh
module (4 lessons, 12-question proctored bank) and upgrades the seeder:
an already-seeded track gets the new module APPENDED, not skipped.

Deploy: apply -> commit -> re-run the seed (idempotent; it will add only
what's missing):
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track

Anchored, idempotent. Requires v3.82.0.
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

L = lambda t, est, html: {"title": t, "est": est, "html": html}
Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

MODULE = {
"title": "Selling 7 — The Sales Invoice, Payments & Collections",
"desc": "The accounting event in full: creating invoices from orders and delivery notes, what submission books, due dates and payment terms, Payment Entry mechanics including advances and allocation, credit notes, and the receivables discipline that turns sales into cash.",
"lessons": [
L("The invoice as the accounting event", "5", "<p>Everything before it was commitment and movement; the <b>Sales Invoice</b> is where money becomes real. Submitting it books <b>revenue</b> and the customer's <b>receivable</b> into the ledgers on its <b>posting date</b>. Make it from the Sales Order (billing before or alongside delivery) or from the Delivery Note (billing what actually shipped) — either way quantities, rates and taxes flow and the order's billed-quantity ledger counts down.</p><p>Two dates matter and are not the same: the <b>posting date</b> is when the books record it; the <b>due date</b> is when the customer must pay — computed from the <b>Payment Terms</b> (Net 30, 50% advance / 50% on delivery, and so on). Terms belong on the customer or the order so the invoice inherits them instead of someone deciding at billing time.</p>"),
L("Statuses & the collections story", "5", "<p>An invoice's status is the collections narrative in one word: <b>Unpaid</b> when submitted, <b>Partly Paid</b> as money arrives, <b>Paid</b> when cleared, <b>Overdue</b> the moment the due date passes unpaid, and <b>Credit Note Issued</b> when a return has been raised against it. The invoice list filtered to Overdue, sorted oldest first, IS the collections worklist — a sales professional opens it weekly, not when cash runs short.</p><p>One special case to know: an invoice with <b>Update Stock</b> ticked moves inventory itself — used when the delivery note step is skipped (counter sales, services with materials). In the standard flow the DN moves stock and the invoice moves money; don't tick Update Stock on an invoice made from a DN or stock moves twice.</p>"),
L("Payment Entry mechanics", "5", "<p>Money is recorded with a <b>Payment Entry</b> — made from the invoice so the reference and allocation come pre-filled. It handles every real-world shape: a <b>full</b> payment closes the invoice; a <b>partial</b> payment leaves it Partly Paid with the outstanding visible; <b>one payment across several invoices</b> is a single entry allocated over each reference; small shortfalls can be <b>written off</b> within your write-off limit instead of chasing ₦150 forever.</p><p><b>Advances</b> work in reverse order: a Payment Entry taken against the customer <i>before</i> the invoice exists sits as an advance, then gets <b>allocated</b> to the invoice when raised — the 50%-upfront deals your enterprise clients sign are exactly this mechanic. Mode of Payment and the bank account on the entry are what make bank reconciliation painless later.</p>"),
L("Credit notes & receivables discipline", "4", "<p>Corrections and returns reverse through a <b>credit note</b> — a Sales Invoice with <b>Is Return</b> against the original — pulling revenue and receivable back with a paper trail; the original flips to Credit Note Issued. Never \"fix\" a submitted invoice by editing history: the credit-note-plus-reinvoice pattern is what auditors, and FIRS, expect to find.</p><p>Discipline is the difference between sales and cash: the <b>Accounts Receivable</b> report ages who-owes-what into buckets (0-30, 31-60, 61-90, 90+); a <b>Statement of Account</b> sent monthly keeps customers honest; and every overdue invoice should have a next follow-up — which in this house means a dated next step on the Duty Board pipeline, not a hope.</p>"),
],
"questions": [
Q("Revenue and the customer's receivable hit the ledgers when:", ["The Sales Order is submitted", "The Sales Invoice is submitted", "The Delivery Note is submitted", "The payment arrives"], 1, "The invoice is the accounting event; earlier documents commit and move stock.", "Accounting event §1"),
Q("Posting date vs due date — the difference is:", ["None, they match", "Posting is when the books record it; due is when the customer must pay", "Posting is for taxes only", "Due date is the delivery date"], 1, "Two dates, two meanings: books vs payment deadline.", "Accounting event §1"),
Q("The due date on an invoice is computed from:", ["The posting date plus 30 always", "The Payment Terms (inherited from customer or order)", "The delivery date", "Selling Settings"], 1, "Payment terms templates drive the due date.", "Accounting event §1"),
Q("Billing exactly what shipped is best done by creating the invoice from:", ["Scratch", "The Delivery Note", "The quotation", "The packing slip"], 1, "Invoice-from-DN bills shipped quantities precisely.", "Accounting event §1"),
Q("An invoice past its due date and unpaid reads:", ["Unpaid", "Overdue", "Expired", "Blocked"], 1, "Overdue is the past-due status — and the collections filter.", "Statuses §2"),
Q("Update Stock on a Sales Invoice means:", ["Nothing", "The invoice itself moves inventory — for flows that skip the DN", "Stock is reserved", "The DN is cancelled"], 1, "Update-stock invoices replace the DN's stock movement; never combine with a DN-based invoice.", "Statuses §2"),
Q("A customer pays ₦2m against a ₦5m invoice. The invoice now shows:", ["Paid", "Partly Paid", "Overdue", "Unpaid"], 1, "Partial receipts leave the invoice Partly Paid with outstanding visible.", "Payments §3"),
Q("One bank transfer settling four invoices is recorded as:", ["Four Payment Entries", "One Payment Entry allocated across the four references", "A journal entry only", "Four credit notes"], 1, "One entry, multiple allocated references.", "Payments §3"),
Q("A 50% advance received before the invoice exists is handled by:", ["Waiting for the invoice", "A Payment Entry against the customer, later allocated to the invoice", "A negative invoice", "A discount"], 1, "Advances sit on the customer and allocate when the invoice is raised.", "Payments §3"),
Q("A customer underpays by ₦180 on a ₦2m invoice. The pragmatic close-out:", ["Chase the ₦180 forever", "Write off the difference within the write-off limit on the Payment Entry", "Cancel the invoice", "Edit the invoice total"], 1, "Small differences write off; the invoice closes honestly.", "Payments §3"),
Q("A submitted invoice has a wrong rate. The correct fix is:", ["Edit the submitted invoice", "Credit note against it, then re-invoice correctly", "Delete it", "A journal to patch the ledger"], 1, "Credit-note-and-reinvoice preserves the audit trail regulators expect.", "Credit notes §4"),
Q("After a credit note is raised against an invoice, the original shows:", ["Cancelled", "Credit Note Issued", "Returned", "Paid"], 1, "The status ties the original to its reversal.", "Credit notes §4"),
],
}

SEED_ORDER_OLD = 'ORDER = ["customers", "items_prices", "quotations", "sales_orders", "delivery", "taxes_invoicing"]'
SEED_ORDER_NEW = 'ORDER = ["customers", "items_prices", "quotations", "sales_orders", "delivery", "taxes_invoicing", "sales_invoice"]'

TRACK_OLD = '''	if frappe.db.exists("Duty Certification Track", {"title": TRACK["title"]}):
		print(f"track exists: {TRACK['title']}")
	else:'''
TRACK_NEW = '''	existing_track = frappe.db.get_value("Duty Certification Track", {"title": TRACK["title"]}, "name")
	if existing_track:
		tr = frappe.get_doc("Duty Certification Track", existing_track)
		have = {r.module for r in tr.get("modules") or []}
		added = 0
		for k in ORDER:
			if module_names[k] not in have:
				tr.append("modules", {"module": module_names[k]})
				added += 1
		if added:
			tr.save(ignore_permissions=True)
			print(f"track exists: {TRACK['title']} — appended {added} new module(s)")
		else:
			print(f"track exists: {TRACK['title']} — complete")
	else:'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()

    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)
    with io.open(os.path.join(root, SEED_PATH), encoding="utf-8") as f:
        seed = f.read()

    if "sales_invoice" in data:
        print("Already applied. Nothing to do.")
        return
    if '"3.82.0"' not in init:
        sys.exit("ABORT: not at v3.82.0.")
    problems = []
    if seed.count(SEED_ORDER_OLD) != 1:
        problems.append(f"  [{seed.count(SEED_ORDER_OLD)}] ORDER line")
    if seed.count(TRACK_OLD) != 1:
        problems.append(f"  [{seed.count(TRACK_OLD)}] track block")
    if len(MODULE["questions"]) != 12 or len(MODULE["lessons"]) != 4:
        problems.append("  module content counts wrong")
    for q in MODULE["questions"]:
        if len(q["opts"]) != 4 or not (0 <= q["ans"] <= 3):
            problems.append(f"  malformed question '{q['q'][:40]}'")
    if "ERPNext" in json.dumps(MODULE):
        problems.append("  ERPNext branding leakage")
    if problems:
        print("ABORT — not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("Anchors + content sane (4 lessons, 12 questions, branding clean).")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data["sales_invoice"] = MODULE
    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    seed = seed.replace(SEED_ORDER_OLD, SEED_ORDER_NEW, 1).replace(TRACK_OLD, TRACK_NEW, 1)
    with io.open(os.path.join(root, SEED_PATH), "w", encoding="utf-8") as f:
        f.write(seed)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.82.0"', '"3.82.1"'))
    print("  data +sales_invoice module · seeder ORDER extended · track-append logic")
    print("wrote __init__.py -> 3.82.1")


if __name__ == "__main__":
    main()
