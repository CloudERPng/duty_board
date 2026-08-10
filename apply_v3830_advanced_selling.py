#!/usr/bin/env python3
"""Duty Board v3.83.0 — Selling 8: Advanced Selling.

Plugs the five flagged gaps as the capstone module — deep Selling
Settings, Product Bundles, Blanket Orders, Sales Person (internal team
tree, contribution & targets), and Sales Partner (external channel &
commission) — 5 lessons, 15-question proctored bank (10 served),
appended to the ZERP-SALESPRO track by the existing append logic.

Deploy: apply -> commit -> re-run the seed (idempotent, adds only this):
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track

Anchored, idempotent. Requires v3.82.1.
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
"title": "Selling 8 — Advanced Selling: Settings, Bundles, Blanket Orders & Sales Teams",
"desc": "The advanced layer: Selling Settings in depth, Product Bundles, Blanket Orders for long-term rate agreements, and the two sales-team structures — Sales Person (internal, contribution and targets) and Sales Partner (external channel and commission).",
"lessons": [
L("Selling Settings — the full tour", "6", "<p><b>Selling Settings</b> is where selling policy becomes system behaviour; a consultant should be able to defend every switch. The naming pair — <b>Customer Naming By</b> (name vs naming series) — decides whether customers are \"Alpha Pharmacy\" or \"CUST-00042\"; chains with duplicate branch names need the series. <b>Default Customer Group</b>, <b>Default Territory</b>, and the default <b>Selling Price List</b> pre-fill every new record — set them to your commonest case so lazy data entry lands correctly.</p><p>The discipline switches: <b>Maintain Same Rate Throughout Sales Cycle</b> (the agreed rate can't drift between order, delivery, and invoice — and its companion action setting decides whether a drift is a hard <i>Stop</i> or just a <i>Warning</i>); <b>Allow User to Edit Price List Rate</b> (untick it and rates come only from Item Prices — the strongest anti-\"special price\" control you have); <b>Validate Selling Price Against Purchase Rate</b> (blocks selling below cost — margin protection at the point of entry); <b>Allow Item to be Added Multiple Times</b>; and the global <b>over-delivery allowance</b> that Module 4's per-item tolerance falls back to. Policy questions from clients — \"can we stop staff discounting?\", \"can we prevent below-cost sales?\" — are usually answered in this one screen.</p>"),
L("Product Bundles", "5", "<p>A <b>Product Bundle</b> sells several stock items as one line: a \"Pharmacy Starter Pack\" parent containing shelf units, a scanner, and a printer. The parent item is <b>non-stock</b> (it never has warehouse quantity — untick Maintain Stock); the bundle definition lists the child items and quantities.</p><p>The mechanics to remember: the customer sees and pays the <b>parent's price</b> (one line, one rate on the quotation and invoice), while the <b>Delivery Note explodes the bundle</b> into its <b>packed items</b> — the children — and it's the children that move stock from the warehouse. Hampers, promo packs, starter kits, install kits: whenever you price as one thing but pick as many things, it's a bundle — never a workaround item with stock nobody counts.</p>"),
L("Blanket Orders", "5", "<p>A <b>Blanket Order</b> is a long-term rate-and-quantity agreement: the customer commits to, say, 10,000 cartons over six months at ₦820 — better than rack rate, weaker than an order for everything at once. Create the blanket order with items, agreed quantities, rates, and the from/to dates.</p><p>Individual <b>Sales Orders are then drawn against it</b>: reference the blanket order and the row inherits the agreed rate automatically, and the blanket order tracks its <b>drawdown</b> — ordered quantity against committed quantity — so both sides see how much of the commitment remains. Use it instead of stretching a quotation's validity for months: a quotation is an offer awaiting an answer; a blanket order is an agreement being consumed.</p>"),
L("Sales Person — the internal team", "5", "<p><b>Sales Person</b> models your own team as a <b>tree</b> — Sales Director → Regional Managers → Field Reps — so results roll up the hierarchy. On a transaction, the <b>Sales Team</b> section assigns one or more sales persons each with a <b>contribution %</b> (summing to 100): a deal worked by two reps splits credit 60/40 and reports show each person's contributed revenue, not double-counted totals.</p><p>Set <b>targets</b> per sales person (by item group and period) and read the <b>Sales Person-wise Transaction Summary</b> against them — commissions, league tables, and performance conversations all come from this structure. If a client asks \"can we see sales by rep?\", the honest answer is: only if sales persons are assigned on documents — the discipline precedes the report.</p>"),
L("Sales Partner — the external channel", "5", "<p>A <b>Sales Partner</b> is outside your company — a reseller, referral agent, or channel distributor who brings the deal — carrying a <b>commission rate</b>. Selecting the partner on a Sales Order or Invoice stamps the channel and computes the <b>total commission</b> on that document automatically.</p><p>The distinction to keep sharp: <b>Sales Person is your staff</b> (tree, contribution %, targets); <b>Sales Partner is an external business</b> (flat entity, commission %). A transaction can carry both — your rep worked the deal a referral partner introduced. The <b>Sales Partner-wise Transaction Summary</b> totals each channel's business and owed commission — pay partners from the report, not from their claims.</p>"),
],
"questions": [
Q("A retail chain has many branches with similar names. Customer Naming By should be:", ["Customer name", "Naming series", "Territory", "Manual entry"], 1, "Series naming avoids collisions and keeps records unambiguous.", "Settings §1"),
Q("The strongest control to stop staff typing \"special prices\" on documents is:", ["A memo", "Unticking Allow User to Edit Price List Rate", "A smaller price list", "Removing their login"], 1, "Rates then come only from Item Price records.", "Settings §1"),
Q("Blocking sales below cost at the point of entry uses:", ["A pricing rule", "Validate Selling Price Against Purchase Rate", "Credit limits", "A report review"], 1, "The validation setting is margin protection built into entry.", "Settings §1"),
Q("Maintain Same Rate Throughout Sales Cycle can be configured to respond to a drift with:", ["Silence only", "A Stop or a Warning, per the action setting", "Automatic correction", "An email"], 1, "The companion action setting chooses hard block vs warning.", "Settings §1"),
Q("A Product Bundle's parent item must be:", ["A stock item with quantity", "A non-stock item (Maintain Stock unticked)", "A serialized item", "A service"], 1, "The parent is never counted in the warehouse; only children are.", "Bundles §2"),
Q("On a bundle sale, warehouse stock is deducted for:", ["The parent item", "The packed child items on the Delivery Note", "Neither", "Both parent and children"], 1, "The DN explodes the bundle; children move stock.", "Bundles §2"),
Q("The customer's invoice for a bundle shows:", ["Every child item priced separately", "One line at the parent's price", "Only the children", "The warehouse breakdown"], 1, "Price lives on the parent; picking lives on the children.", "Bundles §2"),
Q("A customer commits to 10,000 cartons over six months at an agreed rate. Model it as:", ["One giant Sales Order", "A Blanket Order drawn down by individual Sales Orders", "A quotation valid six months", "A pricing rule"], 1, "Blanket orders are consumed agreements; quotations are offers.", "Blanket §3"),
Q("A Sales Order drawn against a blanket order inherits:", ["Nothing", "The agreed rate, while the blanket tracks drawdown", "Only the quantity", "The delivery date"], 1, "Rate flows from the agreement; drawdown is tracked against commitment.", "Blanket §3"),
Q("How much of a blanket commitment remains is read from:", ["The customer's memory", "The blanket order's ordered-vs-committed quantities", "The last invoice", "Stock levels"], 1, "The blanket order itself tracks its consumption.", "Blanket §3"),
Q("Two reps split a deal 60/40. This is recorded via:", ["Two invoices", "Sales Team rows with contribution percentages summing to 100", "A note", "Two sales partners"], 1, "Contribution % splits credit without double-counting revenue.", "Sales Person §4"),
Q("Sales Person is structured as:", ["A flat list", "A tree so results roll up the hierarchy", "One per territory", "A customer group"], 1, "The tree gives regional and directorial roll-ups.", "Sales Person §4"),
Q("\"Show me sales by rep\" only works if:", ["The report is installed", "Sales persons are assigned on the transactions", "Targets are set", "Partners are defined"], 1, "The discipline of assignment precedes the report.", "Sales Person §4"),
Q("Sales Person vs Sales Partner — the distinction is:", ["None", "Person is internal staff with contribution %; Partner is an external business with commission %", "Person earns commission, partner doesn't", "Partner is a customer"], 1, "Internal tree vs external channel — a document can carry both.", "Sales Partner §5"),
Q("Commission owed to a reseller is paid from:", ["The partner's own claim", "The Sales Partner-wise Transaction Summary", "The rep's report", "The delivery notes"], 1, "Pay channels from the system's totals, not their invoices' claims.", "Sales Partner §5"),
],
}

ORDER_OLD = 'ORDER = ["customers", "items_prices", "quotations", "sales_orders", "delivery", "taxes_invoicing", "sales_invoice"]'
ORDER_NEW = 'ORDER = ["customers", "items_prices", "quotations", "sales_orders", "delivery", "taxes_invoicing", "sales_invoice", "advanced"]'


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)
    with io.open(os.path.join(root, SEED_PATH), encoding="utf-8") as f:
        seed = f.read()

    if "advanced" in data:
        print("Already applied. Nothing to do.")
        return
    if '"3.82.1"' not in init:
        sys.exit("ABORT: not at v3.82.1.")
    problems = []
    if seed.count(ORDER_OLD) != 1:
        problems.append(f"  [{seed.count(ORDER_OLD)}] ORDER line")
    if len(MODULE["lessons"]) != 5 or len(MODULE["questions"]) != 15:
        problems.append("  content counts wrong")
    for q in MODULE["questions"]:
        if len(q["opts"]) != 4 or not (0 <= q["ans"] <= 3):
            problems.append(f"  malformed question '{q['q'][:40]}'")
    if "ERPNext" in json.dumps(MODULE):
        problems.append("  ERPNext branding leakage")
    if problems:
        print("ABORT — not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("Anchors + content sane (5 lessons, 15 questions, branding clean).")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data["advanced"] = MODULE
    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, SEED_PATH), "w", encoding="utf-8") as f:
        f.write(seed.replace(ORDER_OLD, ORDER_NEW, 1))
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.82.1"', '"3.83.0"'))
    print("  data +advanced module · seeder ORDER extended (track-append handles the rest)")
    print("wrote __init__.py -> 3.83.0")


if __name__ == "__main__":
    main()
