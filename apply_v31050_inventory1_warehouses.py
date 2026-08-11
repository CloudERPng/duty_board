#!/usr/bin/env python3
"""Duty Board v3.105.0 — ZhiftERP Inventory Management track: infrastructure
+ Inventory 1: Warehouses & the Stock Architecture (pass 1 of 8).

Creates duty_board/academy_inventory_pro_data.json and
duty_board/academy_seed_inventory_pro.py (faithful mirror of the
procurement seeder: proctored modules, track-append idempotency,
refresh_lessons/refresh_questions). Module 1 ships at manual depth
from birth: 9 chapters, 35-bank.

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_inventory_pro.seed_inventory_pro_track

Anchored, idempotent. Requires v3.104.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_inventory_pro_data.json"
SEEDER_PATH = "duty_board/academy_seed_inventory_pro.py"
CHECK_ONLY = "--check" in sys.argv

L = lambda t, est, html: {"title": t, "est": est, "html": html}
Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

SEEDER = '''"""ZhiftERP Inventory Management Professional track seed — the warehouse curriculum.

Content lives in academy_inventory_pro_data.json. Modules are PROCTORED:
timed 60s/question, 10 served from each 35-question bank. Modules are
added pass by pass; re-running the seed appends new modules to the
existing track (idempotent per module and for the track).

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_inventory_pro.seed_inventory_pro_track
"""

import json
import os

import frappe

ORDER = ["warehouses"]

TRACK = {
\t"title": "ZhiftERP Inventory Management Professional",
\t"serial_prefix": "ZERP-INVPRO",
\t"description": "The complete inventory certification: warehouse architecture and the stock ledger, stock entries and internal movements, serial and batch operations, reconciliation and counting, valuation, the multi-branch network, stock health analytics, and the advanced inventory layer — proctored examinations from the warehouse tree to the reports that run stock.",
}


def _data():
\tpath = os.path.join(os.path.dirname(__file__), "academy_inventory_pro_data.json")
\twith open(path) as f:
\t\treturn json.load(f)


def seed_inventory_pro_track():
\tdata = _data()
\tif not frappe.db.exists("Duty Product", "ZhiftERP Inventory Management"):
\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP Inventory Management", "active": 1, "sort_order": 7}).insert(
\t\t\tignore_permissions=True
\t\t)
\t\tprint("created Duty Product: ZhiftERP Inventory Management")

\tmodule_names = {}
\tfor i, key in enumerate(ORDER):
\t\tm = data[key]
\t\texisting = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
\t\tif existing:
\t\t\tmodule_names[key] = existing
\t\t\tprint(f"module exists: {m['title']}")
\t\t\tcontinue
\t\tmod = frappe.get_doc(
\t\t\t{
\t\t\t\t"doctype": "Duty Training Module",
\t\t\t\t"title": m["title"],
\t\t\t\t"product": "ZhiftERP Inventory Management",
\t\t\t\t"description": m["desc"],
\t\t\t\t"active": 1,
\t\t\t\t"audience": "Both",
\t\t\t\t"sort_order": 60 + i,
\t\t\t\t"pass_mark": 70,
\t\t\t\t"timed_mode": 1,
\t\t\t\t"seconds_per_question": 60,
\t\t\t\t"questions_served": 10,
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tmodule_names[key] = mod.name
\t\tfor j, l in enumerate(m["lessons"]):
\t\t\tfrappe.get_doc(
\t\t\t\t{
\t\t\t\t\t"doctype": "Duty Lesson",
\t\t\t\t\t"module": mod.name,
\t\t\t\t\t"title": l["title"],
\t\t\t\t\t"sort_order": j,
\t\t\t\t\t"est_minutes": l["est"],
\t\t\t\t\t"content": l["html"],
\t\t\t\t}
\t\t\t).insert(ignore_permissions=True)
\t\tfor q in m["questions"]:
\t\t\tfrappe.get_doc(
\t\t\t\t{
\t\t\t\t\t"doctype": "Duty Quiz Question",
\t\t\t\t\t"module": mod.name,
\t\t\t\t\t"question": q["q"],
\t\t\t\t\t"opt_a": q["opts"][0],
\t\t\t\t\t"opt_b": q["opts"][1],
\t\t\t\t\t"opt_c": q["opts"][2],
\t\t\t\t\t"opt_d": q["opts"][3],
\t\t\t\t\t"correct": "ABCD"[q["ans"]],
\t\t\t\t\t"rationale": q["why"],
\t\t\t\t\t"source": q["src"],
\t\t\t\t\t"active": 1,
\t\t\t\t}
\t\t\t).insert(ignore_permissions=True)
\t\tprint(f"seeded module: {m['title']} ({len(m['lessons'])} lessons, {len(m['questions'])} questions, proctored)")

\texisting_track = frappe.db.get_value("Duty Certification Track", {"title": TRACK["title"]}, "name")
\tif existing_track:
\t\ttr = frappe.get_doc("Duty Certification Track", existing_track)
\t\thave = {r.module for r in tr.get("modules") or []}
\t\tadded = 0
\t\tfor k in ORDER:
\t\t\tif module_names[k] not in have:
\t\t\t\ttr.append("modules", {"module": module_names[k]})
\t\t\t\tadded += 1
\t\tif added:
\t\t\ttr.save(ignore_permissions=True)
\t\t\tprint(f"track exists: {TRACK['title']} — appended {added} new module(s)")
\t\telse:
\t\t\tprint(f"track exists: {TRACK['title']} — complete")
\telse:
\t\tfrappe.get_doc(
\t\t\t{
\t\t\t\t"doctype": "Duty Certification Track",
\t\t\t\t"title": TRACK["title"],
\t\t\t\t"product": "ZhiftERP Inventory Management",
\t\t\t\t"audience": "Consultant",
\t\t\t\t"serial_prefix": TRACK["serial_prefix"],
\t\t\t\t"description": TRACK["description"],
\t\t\t\t"active": 1,
\t\t\t\t"modules": [{"module": module_names[k]} for k in ORDER],
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tprint(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

\tfrappe.db.commit()
\tprint("ZhiftERP Inventory Management Professional track ready.")


def refresh_lessons(only=None):
\t"""Replace lesson content on ALREADY-SEEDED modules from the data
\tfile (matched by title). Clears lesson read-progress for refreshed
\tmodules. Questions untouched. Pass only=<module_key> for a single
\tmodule."""
\tdata = _data()
\trefreshed = 0
\tkeys = [only] if only else ORDER
\tfor key in keys:
\t\tif key not in data:
\t\t\tprint(f"unknown module key: {key}")
\t\t\tcontinue
\t\tm = data[key]
\t\tmod = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
\t\tif not mod:
\t\t\tprint(f"module not seeded yet (skipped): {m['title']}")
\t\t\tcontinue
\t\tfor row in frappe.get_all("Duty Lesson", filters={"module": mod}, pluck="name"):
\t\t\tfrappe.delete_doc("Duty Lesson", row, ignore_permissions=True, force=True)
\t\tfor row in frappe.get_all("Duty Lesson Progress", filters={"module": mod}, pluck="name"):
\t\t\tfrappe.delete_doc("Duty Lesson Progress", row, ignore_permissions=True, force=True)
\t\tfor j, l in enumerate(m["lessons"]):
\t\t\tfrappe.get_doc(
\t\t\t\t{
\t\t\t\t\t"doctype": "Duty Lesson",
\t\t\t\t\t"module": mod,
\t\t\t\t\t"title": l["title"],
\t\t\t\t\t"sort_order": j,
\t\t\t\t\t"est_minutes": l["est"],
\t\t\t\t\t"content": l["html"],
\t\t\t\t}
\t\t\t).insert(ignore_permissions=True)
\t\trefreshed += 1
\t\tprint(f"refreshed: {m['title']} ({len(m['lessons'])} lessons)")
\tfrappe.db.commit()
\tprint(f"{refreshed} module(s) refreshed. Read-progress reset for refreshed modules.")


def refresh_questions(only=None):
\t"""Replace a seeded module's question bank from the data file
\t(matched by title). Past attempts keep stored results. Pass
\tonly=<module_key> for one module, else all in ORDER."""
\tdata = _data()
\tkeys = [only] if only else ORDER
\tfor key in keys:
\t\tif key not in data:
\t\t\tprint(f"unknown module key: {key}")
\t\t\tcontinue
\t\tm = data[key]
\t\tmod = frappe.db.get_value("Duty Training Module", {"title": m["title"]}, "name")
\t\tif not mod:
\t\t\tprint(f"module not seeded yet (skipped): {m['title']}")
\t\t\tcontinue
\t\tfor row in frappe.get_all("Duty Quiz Question", filters={"module": mod}, pluck="name"):
\t\t\tfrappe.delete_doc("Duty Quiz Question", row, ignore_permissions=True, force=True)
\t\tfor q in m["questions"]:
\t\t\tfrappe.get_doc(
\t\t\t\t{
\t\t\t\t\t"doctype": "Duty Quiz Question",
\t\t\t\t\t"module": mod,
\t\t\t\t\t"question": q["q"],
\t\t\t\t\t"opt_a": q["opts"][0],
\t\t\t\t\t"opt_b": q["opts"][1],
\t\t\t\t\t"opt_c": q["opts"][2],
\t\t\t\t\t"opt_d": q["opts"][3],
\t\t\t\t\t"correct": "ABCD"[q["ans"]],
\t\t\t\t\t"rationale": q["why"],
\t\t\t\t\t"source": q["src"],
\t\t\t\t\t"active": 1,
\t\t\t\t}
\t\t\t).insert(ignore_permissions=True)
\t\tprint(f"bank refreshed: {m['title']} ({len(m['questions'])} questions)")
\tfrappe.db.commit()
\tprint("Question banks refreshed.")
'''

LESSONS = [
L("Chapter 1 — What a warehouse is (and is not)", "13", "<p>Welcome to the third certification. Selling taught money-in; Procurement taught money-out; this track teaches the thing both of them move: <b>stock — where it sits, how it moves, what it is worth, and who answers for it</b>. And it begins where stock begins: the warehouse.</p><p><b>A warehouse is a named place stock can be.</b> Not necessarily a building: the system's warehouse is an ACCOUNTABILITY unit — a distinct place with a distinct answer to <i>what is here and who answers for it</i>. A physical store is a warehouse; so is the quarantine bay inside it, the van doing branch deliveries, the goods sitting in transit between two branches, and the stock at your repacker's site that never stopped being yours. One building can hold several warehouses; one warehouse (the van, the transit) can have no building at all. The test is never architecture; it is custody: <b>where a distinct accountability exists, a distinct warehouse names it</b> — the principle this whole module unpacks.</p><p><b>Two kinds of node.</b> Warehouses live in a TREE: <b>leaf warehouses</b> actually hold stock — every stock movement names a leaf; <b>group warehouses</b> hold structure — they aggregate their children for reporting and hold nothing themselves. Lagos Region is a group; Ikeja Branch Store is a leaf. Trying to move stock into a group node fails by design, and the refusal is teaching you the model: stock exists in PLACES; groups exist so places can be READ together.</p><p><b>The warehouse carries money.</b> Every warehouse's stock has a value (Chapter 6 makes this operational), and in the books each warehouse's holdings roll into the firm's stock asset. This is why warehouse design is never merely logistics: creating a warehouse creates a bucket of company value with a custodian's name implicitly on it, and deleting, merging, or misusing warehouses moves the accounting ground under the operation.</p><p><b>What the item knew, the warehouse localises.</b> Buying 2 built the item — one identity, one UOM discipline, one cost story. The warehouse dimension crosses it: every stock fact in this system is an <b>item-AT-warehouse</b> fact. PARA-500 does not have a quantity; it has a quantity AT Central, AT Ibadan, AT Quarantine, AT In-Transit — and the sum is the firm's position while the parts are the operation's truth. Every screen, report, and document in this track reads or writes that two-dimensional grid, and holding the grid in your head — items down, warehouses across — is the single mental model that makes the rest of the curriculum easy.</p>"),
L("Chapter 2 — Designing the tree", "14", "<p>The warehouse tree is designed once and lived with for years, which makes its design hour the same kind of hour as the settings walk: the consultant writing a constitution. The principles, in the order to apply them.</p><p><b>Start from accountability, not architecture.</b> List the distinct custodies the client actually runs: the central store, each branch's stock room, the quarantine bay, goods-in-transit between locations, the facilities/consumables store, any supplier-side stock (the subcontractor holding your materials), returns staging where returns are triaged. Each distinct custody becomes a leaf. What does NOT become a warehouse: shelf positions, aisles, and fridges inside one custody — that is bin-level detail, and modelling every shelf as a warehouse (the sprawl disease, Chapter 9) drowns the tree in places nobody separately answers for. The line to hold: <i>would a stock difference here be a different PERSON'S problem?</i> Yes — warehouse. No — location detail within one.</p><p><b>Shape the tree for reading.</b> Groups exist for rollups, so group by how the firm asks questions: All Warehouses → Branches (group) → each branch leaf; Central operations grouped with their logical rooms; regions as intermediate groups only when the firm genuinely reads by region. Depth discipline: two or three levels serve almost every trading firm — a five-level tree is bureaucracy nobody navigates. The tree can be re-shaped later (groups re-parented) far more easily than leaves can be merged, so err simple.</p><p><b>Name for the decade.</b> Names appear on every document, filter, and report forever: short, unambiguous, consistently patterned — the branch name leading (Ikeja Store, Ikeja Quarantine) so sorted lists group naturally, and no cleverness that needs explaining to the third cohort of staff. Where branches are companies-within-the-company (separate accountability entirely), the design conversation escalates beyond warehouses — flag it, don't improvise it.</p><p><b>One custody, one leaf — both directions.</b> Every physical custody has exactly one system twin, and every system leaf means one real custody. The diseases are symmetrical: the physical room with no system warehouse (its stock booked into a neighbour, its differences invisible — the storeroom that exists in the building and not in the books); and the system warehouse with no physical meaning (created for a forgotten reason, accumulating misc postings — a junk drawer with a naira value). The annual tree review (this track's calendar will own it) walks both lists.</p><p><b>Defaults finish the design.</b> A tree is used by documents, and documents choose warehouses by DEFAULTS (Chapter 7): the design is complete only when every routine flow lands in the right leaf without a human choosing — because the human, at speed, chooses wrong, and the wrong-warehouse posting is this track's most routine support ticket. Design the tree, then wire the defaults, then watch the first week's postings: the three steps of a warehouse implementation, in order.</p>"),
L("Chapter 3 — The stock ledger: the append-only book", "14", "<p>Underneath every screen in this track sits one structure, and understanding it makes everything else transparent: the <b>stock ledger</b> — the append-only book of every stock movement the firm has ever made.</p><p><b>What an entry is.</b> Every time stock moves, the ledger gains a dated line: item, warehouse, quantity in or out, the running balance after, the valuation effect (Chapter 6 and module 5), and — decisively — <b>which document caused it</b>. A receipt writes IN lines; a delivery writes OUT lines; a transfer writes an OUT at source and an IN at destination; a reconciliation writes the adjusting difference. The ledger is written ONLY by documents: no screen edits it directly, no administrator pencils a balance, and this is not a limitation but the entire design — the ledger is the firm's stock testimony, and testimony that can be quietly rewritten proves nothing.</p><p><b>Append-only, permanently.</b> Corrections do not erase; they append. The wrong entry stands, and the correcting entry stands beside it, dated, attributed, explained by its own document — the same immutability doctrine both money tracks taught (the invoice never edited, the credit note appended), because it is the same ledger philosophy applied to goods. When a client asks <i>can we just fix the number</i>, the consultant's answer is this chapter: the number is a running balance COMPUTED from history; fixing it means appending the movement that makes history true (usually a reconciliation — module 4), never editing history to match a wish.</p><p><b>The bin: the ledger, summarised.</b> For each item-at-warehouse, the system maintains the current position — the running totals the ledger implies: actual quantity, plus the promised dimensions (Chapter 4). Reading a bin is reading the ledger's last line; reading the LEDGER is reading how it got there — and the second read is the diagnostic superpower: any surprising balance decomposes into its history, entry by entry, document by document, until the surprise has a name (the transfer that never completed, the receipt posted to the wrong branch, the delivery that went out twice). Consultants who reach for the ledger first resolve in minutes what screen-starers escalate.</p><p><b>Chronology is load-bearing.</b> Entries carry posting date and time, and the ledger is a TIMELINE: stock-as-at-a-date, valuation at each moment, and every dispute's evidence all read it in order. Backdating a movement rewrites every balance after it — sometimes legitimately (the receipt entered a day late, policy-governed), always consequentially (module 5 walks the valuation ripple). The gate disciplines both trading tracks taught (post at the event, never batch Friday into Monday) were protecting THIS structure; now you can see what they protect.</p><p><b>The auditor's favourite table.</b> Everything this track will do — counts, valuations, branch networks, health reports — is a conversation with this ledger. The firm whose people understand that stops arguing with screens and starts reading history; and the audit, internal or external, that can walk any balance back to documents is the audit that ends early. One book, appended forever, written only by documents: hold that sentence; the track is its elaboration.</p>"),
L("Chapter 4 — The four numbers of a bin", "13", "<p>Both trading tracks used the projected-stock arithmetic; this chapter makes you its owner. For every item-at-warehouse, four numbers describe the position, and reading them together is the warehouse professional's core literacy.</p><ul><li><b>Actual</b> — what the ledger says is physically here now: the sum of every in minus every out. The number a count would verify (module 4 tests it), the number custody answers for.</li><li><b>Reserved</b> — what is promised OUT: submitted sales orders' undelivered quantities holding their claim (Selling 4's machinery). Physically present, commercially spoken for — sellable to no one else.</li><li><b>Incoming</b> — what is promised IN: submitted purchase orders' unreceived quantities (Procurement 5's machinery), plus inbound transfers en route. Not here yet, but coverage the planners may count.</li><li><b>Projected = actual − reserved + incoming</b> — the number decisions read: what will be here when promises keep. Reorder triggers watch it (Procurement 3), sales availability reads it (Selling 4), and planning plans it.</li></ul><p><b>Reading a bin like a professional.</b> The four numbers are a diagnosis in one row. Actual 500, reserved 480, projected 20: the shelf looks full and the branch is nearly sold out — the picker sees boxes, the system sees promises, and the system is right. Actual 40, incoming 300, projected 340: thin shelf, healthy position — panic buying now duplicates the Emzor order already coming. Actual 200, reserved 0, incoming 0, and no movement for months: the dead-stock read (module 7 prices it). The literacy is refusing to read ACTUAL alone — every actual-only decision (the sale promised off the visible shelf, the purchase panicked off the visible gap) is a decision made with a quarter of the information.</p><p><b>Where the promises live.</b> Reserved and incoming are not typed anywhere — they are COMPUTED from open documents, which is why both trading tracks' hygiene rules were really inventory rules: the ghost reservation (the stale sales order hiding sellable stock) corrupts RESERVED; the phantom incoming (the stale purchase order promising goods forever) corrupts INCOMING; and both corrupt PROJECTED, the number everything downstream trusts. The sweeps those tracks installed are, from this track's chair, ledger hygiene — and the warehouse team has standing to demand them, because the warehouse inherits every planning error the corrupted number causes.</p><p><b>Per-warehouse, then rolled.</b> Each number is item-AT-warehouse; the firm-level view sums the leaves — and the difference matters operationally: the firm may hold plenty while Ibadan holds none (a TRANSFER problem, not a purchase problem — module 6's terrain), and projected-at-Central answers a different question from projected-everywhere. The grid again: read the cell for operations, the rollup for strategy, and never confuse the two.</p>"),
L("Chapter 5 — The logical rooms", "13", "<p>The tree's most powerful idea is the warehouse with no walls: the <b>logical room</b> — a leaf that names a custody state rather than a building. You have met every one of them in the earlier tracks; this chapter assembles them as a family and gives the design rule they share.</p><ul><li><b>Quarantine</b> (Procurement 6's rejected warehouse): stock in your possession but out of your sellable truth — damaged arrivals, failed inspections, short-dated rejections awaiting their fate. Its balance is a to-do list with a value; its weekly review is already on the procurement calendar.</li><li><b>In-transit</b>: stock between two of your own custodies — on the truck from Central to Ibadan, owned by the firm and held by nobody's shelf. The two-step transfer (module 2 runs its mechanics, module 6 its governance) parks the goods here between dispatch and receipt, so at every moment SOMETHING answers for them: the sender no longer, the receiver not yet, the transit room precisely. Its balance is the network's bloodstream, and its AGING is the network's diagnostic — transit stock older than any truck journey is a truck that never arrived, a receipt never confirmed, or a leak (module 6 owns the discipline).</li><li><b>Supplier-side / subcontract stock</b> (Procurement 8): your materials at their site — ownership retained, location external, exposure visible as a balance instead of a hope.</li><li><b>Returns staging</b>: customer returns landing for triage before their fate (restock, quarantine, write-off — Selling 5's fork needs a floor to stand on). A distinct room where the firm's return volume justifies distinct accountability; folded into quarantine where it does not.</li><li><b>The facilities/consumables store</b>: not glamorous, but internal consumption (Procurement 3's Material Issue) needs a custody to issue FROM, or consumables shrinkage hides in the trading rooms.</li></ul><p><b>The shared design rule.</b> Each logical room exists because a DISTINCT QUESTION needs a standing answer: what is rejected and undecided? what is between branches? what is at the subcontractor? what returned and awaits triage? Where the firm genuinely runs the state, the room earns its leaf; where it does not (a single-location firm with no transfers needs no transit room), creating the room manufactures ceremony. The consultant's judgment is the same proportionality every track has practised — model the states the client LIVES, not the states the software offers.</p><p><b>The rooms are custody, not exile.</b> A recurring client misunderstanding, worth pre-empting: stock in quarantine or transit has not left the company — it counts in the firm's stock value, appears in the rollups, and belongs to someone's answerability. The rooms exist to make states VISIBLE, not to make stock disappear; and the monthly read of every logical room's balance and aging (this track's calendar will consolidate it) is how the visible states stay managed instead of sedimenting — because a logical room nobody reads becomes exactly what it was built to prevent: a place where stock quietly stops being anyone's problem.</p>"),
L("Chapter 6 — Stock and money: the custodian's number", "13", "<p>Every warehouse balance is also a naira figure, and this chapter is the bridge this track keeps crossing: stock as VALUE, and the warehouse as a custody of company money that happens to sit on shelves.</p><p><b>How value gets there.</b> Each ledger entry carries valuation: goods arrive at their landed cost (the Procurement 6 truth — PO rate plus allocated charges), leave at the valuation the method computes (module 5 teaches FIFO and moving-average mechanics), and the item-at-warehouse balance is therefore both a quantity AND an amount. Summed per warehouse: the <b>warehouse-wise stock value</b> — Central holding ₦48m, Ibadan ₦11m, Quarantine ₦600k, In-Transit ₦2.1m — and summed altogether, the stock asset the balance sheet reports. The operational reading and the accountant's reading are the same numbers at different rollups, which is exactly why the gate disciplines mattered: a receipt posted wrong is a misstatement, not a typo.</p><p><b>The custodian's number.</b> Attach the value to the accountability and warehouse management changes character: the Ibadan storekeeper is not minding shelves — they are answerable for ₦11m of company assets, and the systems this track teaches (documents for every movement, counts on a cadence, variances investigated) are how that answerability is made fair: the custodian who moves stock only by documents can PROVE their custody; the one who obliges undocumented favours cannot, and inherits every difference as suspicion. Framed this way in training, the disciplines stop being bureaucracy and become the storekeeper's own protection — the framing that makes go-live adoption stick.</p><p><b>Value concentrates attention.</b> The warehouse-wise value read orders the priorities: the counting programme weights toward where the money sits (module 4's cycle design); security and access follow value; and the logical rooms' readings become money readings — ₦600k aging in quarantine is a decision backlog with interest, ₦2.1m in transit is working capital on wheels. The MD who will not read a stock report will read this one, and the consultant should hand it to them monthly.</p><p><b>Shrinkage is the gap's name.</b> Where the ledger says more than the shelf holds, the difference has a value and a family of causes — unrecorded movements, theft, damage never written, gate errors compounding — and module 4 (counting) plus module 7 (the shrinkage trend) turn it from an annual shock into a managed number. For now, hold the accounting shape: the variance a count confirms becomes a written adjustment with a naira cost, landing where the accountant directs — visible, owned, trended. The firm that knows its shrinkage rate manages it; the firm that discovers it annually budgets by superstition.</p><p><b>The bridge's rule.</b> Every operational stock decision is silently a money decision — the transfer is value moving between custodies, the write-off is value leaving with a signature, the count variance is value confessing. This track teaches the operations; the money meaning rides every one of them, and the consultant who narrates BOTH — this movement, this value, this accountability — is teaching inventory the way owners hear it.</p>"),
L("Chapter 7 — Defaults & the choosing of warehouses", "13", "<p>Documents move stock, and every document must answer: WHICH warehouse? The answer should almost never be a human deciding at speed — it should be a default, designed once. This chapter wires the tree to the documents.</p><p><b>The default chain.</b> Warehouse selection resolves top-down: the <b>item's default warehouse</b> (per company — and where the setup supports it, per item-and-branch context) seeds document rows; document-level defaults (the receiving warehouse on a purchase document, the source on a delivery) override per transaction; and the row-level field remains editable for the genuine exception. The design goal from Chapter 2, restated as configuration: <b>every routine flow lands in the right leaf with zero human choices</b> — replenishment receipts into Central, branch sales out of the branch store, rejections into that branch's quarantine — because the human at speed picks the top of the dropdown, and the top of the dropdown is how Ibadan's stock ends up in Abeokuta.</p><p><b>Per-flow defaults, walked.</b> The implementation checklist: purchase receiving defaults to the central store (or the branch, where branches receive directly — a policy decided, not assumed); sales and POS at each branch default to THAT branch's leaf (the per-branch default the multi-location setup lives or dies by); stock entries for issues default from the facilities store; return flows default into staging/quarantine, never silently into sellable. Each default is a sentence of policy — <i>we receive centrally; branches sell their own stock; consumables issue from facilities</i> — and the consultant reads the sentences back to the client before wiring them, because a default nobody chose is still a policy, just an accidental one.</p><p><b>The wrong-warehouse disease.</b> The most routine ticket in multi-location support: stock posted to the wrong leaf — the receipt into the wrong branch, the sale out of a store that never held the goods, the transfer's destination mistyped. The damage is quiet and compounding: two warehouses now both lie (one high, one low), counts at both will surprise, and negative-stock pressure builds where the goods were never booked (module 5 meets what negative stock does to valuation). The response pattern: diagnose from the ledger (Chapter 3's read — the mispost has a document, a date, and an author), correct by MOVEMENT (a transfer putting the stock where it physically is — never an edit, the append-only law), and fix the DEFAULT or permission that made the wrong choice easy — because a mispost is almost never a careless person; it is a dropdown that offered the wrong thing first.</p><p><b>Restriction as the stronger wire.</b> Beyond defaults, the permission layer can BIND: branch users restricted to their branch's warehouses so the wrong leaf is not merely un-defaulted but unavailable. The trade is flexibility for safety, and the multi-branch answer is usually safety — the Ikeja cashier has no honest reason to move Abeokuta's stock, and the restriction that prevents it prevents the ticket, the recount, and the argument. Module 8 owns the full permissions posture; plant the principle here: <b>defaults make the right choice easy; restrictions make the wrong choice impossible; a mature setup uses both</b>.</p>"),
L("Chapter 8 — Case study: designing HealthTrade's network", "16", "<p>HealthTrade — whose suppliers, purchases, and money the Procurement track built — now gets its warehouse constitution. The design session, run as Chapters 1-7 taught it.</p><p><b>Step 1 — the custody list (Ch. 1-2).</b> The walk-through with the MD and the storekeepers lists the real custodies: the Central store (Surulere), two branch stock rooms (Ibadan, Abeokuta), the quarantine bay inside Central, goods moving between locations weekly, consumables (cleaning, stationery) currently living — badly — on a corner of Central's racking, the repacker holding bulk paracetamol (the Procurement 8 subcontract), and returns arriving at whichever counter the customer chose. Eight distinct answerabilities; the shelf-vs-warehouse line holds twice (the fridge inside Central: same custodian, location detail, NOT a warehouse; the consumables corner: different question entirely — its own room).</p><p><b>Step 2 — the tree (Ch. 2, 5).</b> Drawn shallow: <i>All Warehouses</i> → <b>Central Store</b>, <b>Central Quarantine</b>, <b>Facilities Store</b>, <b>In-Transit</b>, <b>Repacker (Subcontract)</b>, and a <b>Branches</b> group holding <b>Ibadan Store</b> and <b>Abeokuta Store</b> (each with its small quarantine leaf — the branch that rejects a delivery needs its own bay). Returns staging is FOLDED into quarantine for now — the volume does not yet earn a room, and the decision is written down with its revisit trigger (if return triage exceeds a shelf, split it). Names patterned, branch-first; three levels nowhere exceeded.</p><p><b>Step 3 — the defaults wired (Ch. 7).</b> Purchasing receives to Central (the Procurement 3 policy — branches replenish by transfer, never buy retail); each branch's sales default out of its own store; issues default from Facilities; rejections default to the local quarantine. Branch users are RESTRICTED to their branch leaves plus read on Central (they may see what they can request — module 6's flows will use it). The defaults are read back as policy sentences and the MD signs the page.</p><p><b>Step 4 — the first reads (Ch. 3-6).</b> Week one's numbers, walked with the team: the warehouse-wise value (Central ₦48m, branches ₦9m and ₦7m, quarantine ₦140k, transit ₦800k mid-week, repacker ₦1.2m) — the MD's monthly page from day one, each figure introduced as somebody's custody. A bin read run live for PARA-500 at Ibadan: actual 96, reserved 40 (the weekend's counter orders), incoming 60 (Tuesday's transfer, in transit now), projected 116 — and the storekeeper's <i>but the shelf shows 96</i> becomes the four-numbers lesson on the spot. One ledger walk: a surprising Abeokuta balance decomposed entry by entry to a receipt posted there in error during setup week — corrected by transfer (the stock is physically at Central), the default that allowed it tightened, the append-only law demonstrated better than any slide.</p><p><b>What the design bought (Ch. 9 previews).</b> Every place stock can be now has a name, a value, and an owner; every routine flow lands right unattended; the logical rooms make rejection, transit, and subcontract states visible instead of anecdotal; and the modules ahead — movements, counting, valuation, the network — inherit a floor that can carry them. The constitution took one afternoon; the alternative is discovering it piecemeal through a year of tickets.</p>"),
L("Chapter 9 — Common mistakes & the first law", "13", "<p>The architecture layer's scar tissue — the design mistakes that surface as everyone else's tickets for years. Symptom → disease → fix.</p><p><b>Pattern 1 — warehouse sprawl.</b> Symptom: forty warehouses for an eleven-person firm; nobody can say what half are for. Disease: places created per whim — a warehouse per shelf, per project, per mood (Ch. 2) — custody diluted until no balance is anyone's answer. Fix: the accountability test applied ruthlessly in a consolidation pass — stock moved by documented transfers into the custodies that are real, empty husks disabled; and creation rights narrowed so the tree grows by decision, not convenience.</p><p><b>Pattern 2 — the flat sixty.</b> Symptom: every leaf a direct child of the root; branch reporting assembled by hand each month. Disease: the tree grown without groups (Ch. 2) — structure never designed, only accumulated. Fix: groups introduced and leaves re-parented (structure is re-shapeable; this is the cheap fix in the family) to mirror how the firm actually asks its questions.</p><p><b>Pattern 3 — the room with no twin.</b> Symptom: a physical storeroom whose stock lives, in the books, inside a neighbouring warehouse; differences there are invisible by construction. Disease: custody without a leaf (Ch. 2, 5) — the map missing a territory. Fix: the leaf created, a counted opening moved in by document, defaults corrected — and its mirror twin hunted in the same pass: system warehouses with no physical meaning, absorbing misc postings as a valued junk drawer.</p><p><b>Pattern 4 — actual-only decisions.</b> Symptom: sales promised off the visible shelf while orders held it; purchases panicked while a delivery rode the road. Disease: the four numbers unread (Ch. 4) — decisions made on a quarter of the position. Fix: the bin literacy taught (projected as the deciding number), and the promise hygiene enforced upstream — the ghost and phantom sweeps this track now has standing to demand.</p><p><b>Pattern 5 — the unread logical rooms.</b> Symptom: quarantine holds eleven months of undecided stock; the transit room's balance never returns to zero. Disease: rooms built for visibility, then never read (Ch. 5) — the states visible to no one become states managed by no one. Fix: each room's balance-and-aging on a named calendar rhythm; a room the firm will not commit to reading is a room to fold back until it will.</p><p><b>Pattern 6 — the wrong-warehouse epidemic.</b> Symptom: recurring misposts between branches; counts at both keep surprising. Disease: defaults undesigned and permissions unbound (Ch. 7) — the dropdown offering the wrong leaf first to a user allowed to take it. Fix: the mispost corrected by movement, then the default rewired and the restriction applied — the ticket answered at the layer that generated it.</p><p><b>The first law.</b> Selling's laws began with masters; Procurement's began with the supply base; this track's begins with the map: <b>the warehouse tree is the map of custody — every place stock can be is named, valued, and owned, and stock lives only in named places.</b> Design the map from accountability, wire the defaults so documents walk it unattended, keep the logical rooms read, and the ledger beneath it all stays a book worth believing. Seven modules stand on this floor; module 2 starts moving stock across it.</p>"),
]

QUESTIONS = [
Q("The system's warehouse is fundamentally:", ["A building", "An accountability unit — a named place with a distinct answer for what is here and who answers", "A shelf", "A report"], 1, "Custody, not architecture, is the test.", "Ch1"),
Q("Stock moves only into:", ["Group nodes", "Leaf warehouses — groups aggregate for reading and hold nothing", "Either freely", "The root"], 1, "The refusal teaches the model.", "Ch1"),
Q("Every stock fact in the system is:", ["An item fact", "An item-AT-warehouse fact — the two-dimensional grid", "A company total", "A guess"], 1, "The grid is the mental model the whole track reads and writes.", "Ch1"),
Q("The shelf-vs-warehouse line asks:", ["Is it big enough", "Would a stock difference here be a different PERSON'S problem", "Does it have a door", "Is it refrigerated"], 1, "Yes: warehouse. No: location detail within one custody.", "Ch2"),
Q("Tree depth for most trading firms is:", ["Five levels minimum", "Two or three levels — a deep tree is bureaucracy nobody navigates", "One flat level", "Unlimited"], 1, "Err simple; groups re-shape more easily than leaves merge.", "Ch2"),
Q("The two symmetrical design diseases are:", ["Big and small warehouses", "The physical room with no system twin, and the system leaf with no physical meaning", "Groups and leaves", "Old and new names"], 1, "A missing territory, and a valued junk drawer.", "Ch2, Ch9"),
Q("The warehouse design is complete only when:", ["The tree is drawn", "Every routine flow lands in the right leaf with zero human choices — defaults wired", "Names are chosen", "The MD approves"], 1, "Tree, then defaults, then watch week one.", "Ch2, Ch7"),
Q("The stock ledger is written by:", ["Administrators", "Documents only — no screen edits it, no balance is pencilled", "The storekeeper", "Month-end journals"], 1, "Testimony that can be rewritten proves nothing.", "Ch3"),
Q("Fixing a wrong balance means:", ["Editing the number", "Appending the movement that makes history true — corrections append, never erase", "Deleting the entry", "Restarting the ledger"], 1, "The balance is computed from history.", "Ch3"),
Q("Reading the ledger (vs the bin) is:", ["Redundant", "The diagnostic superpower — any surprising balance decomposes into documents until the surprise has a name", "Slower and worse", "For auditors only"], 1, "Ledger-readers resolve what screen-starers escalate.", "Ch3"),
Q("Backdating a movement:", ["Changes nothing", "Rewrites every balance after it — sometimes legitimate, always consequential", "Is impossible", "Only affects reports"], 1, "The gate disciplines were protecting the chronology.", "Ch3"),
Q("The four numbers of a bin are:", ["Cost, price, margin, tax", "Actual, reserved, incoming, projected", "In, out, lost, found", "Min, max, avg, count"], 1, "Projected = actual − reserved + incoming.", "Ch4"),
Q("Actual 500, reserved 480, projected 20 means:", ["A full healthy shelf", "The shelf looks full and the branch is nearly sold out — the system sees the promises", "A counting error", "Time to buy"], 1, "The picker sees boxes; the system is right.", "Ch4"),
Q("Actual 40, incoming 300 means:", ["Panic buy now", "Thin shelf, healthy position — buying now duplicates the order already coming", "A ledger fault", "Dead stock"], 1, "Actual-only decisions use a quarter of the information.", "Ch4"),
Q("Reserved and incoming are:", ["Typed by planners", "Computed from open documents — which is why the ghost and phantom sweeps are ledger hygiene", "Estimates", "Month-end figures"], 1, "The warehouse inherits every corruption of the promises.", "Ch4"),
Q("Firm-level stock plentiful while Ibadan holds none is:", ["A purchase problem", "A transfer problem — read the cell for operations, the rollup for strategy", "Impossible", "A pricing issue"], 1, "The grid's two readings answer different questions.", "Ch4"),
Q("A logical room is:", ["A mistake", "A leaf naming a custody state rather than a building — quarantine, transit, supplier-side, staging", "A group node", "A report filter"], 1, "The warehouse with no walls.", "Ch5"),
Q("In-transit stock aging beyond any truck journey means:", ["Normal delay", "A truck that never arrived, a receipt never confirmed, or a leak", "Faster trucks needed", "Nothing"], 1, "The transit room's aging is the network's diagnostic.", "Ch5"),
Q("Stock in quarantine or transit:", ["Has left the company", "Counts in the firm's value and belongs to someone's answerability — visible, not exiled", "Is written off", "Is the supplier's"], 1, "The rooms make states visible, not stock disappear.", "Ch5"),
Q("A logical room the firm will not read:", ["Still helps", "Becomes the thing it was built to prevent — stock that is nobody's problem", "Reads itself", "Should multiply"], 1, "Model the states the client lives, then read them.", "Ch5, Ch9"),
Q("The warehouse-wise stock value read shows:", ["Selling prices", "Each custody's naira figure — Central ₦48m is somebody's answerability", "Only totals", "Budgets"], 1, "The operational and accounting readings are the same numbers.", "Ch6"),
Q("Framing documents-for-every-movement to storekeepers as:", ["Surveillance", "Their own protection — the documented custodian can PROVE their custody", "Bureaucracy", "Optional"], 1, "The framing that makes adoption stick.", "Ch6"),
Q("₦600k aging in quarantine is:", ["Free storage", "A decision backlog with interest — the money reading of the logical room", "Profit", "The supplier's problem"], 1, "Value concentrates attention.", "Ch6"),
Q("The firm that discovers shrinkage annually:", ["Manages it", "Budgets by superstition — counts and trends turn it into a managed number", "Has none", "Is normal"], 1, "The gap has a value and a family of causes.", "Ch6"),
Q("Warehouse selection on documents should be:", ["A human choosing at speed", "Resolved by the default chain — item defaults, document defaults, row override for exceptions", "Random", "Always Central"], 1, "The human at speed picks the top of the dropdown.", "Ch7"),
Q("Each default is:", ["A technical detail", "A sentence of policy — read back to the client, because an unchosen default is an accidental policy", "Invisible", "Permanent"], 1, "We receive centrally; branches sell their own stock.", "Ch7"),
Q("A wrong-warehouse posting is corrected by:", ["Editing the entry", "A MOVEMENT putting stock where it physically is — then fixing the default that made it easy", "Deleting the document", "A recount alone"], 1, "The append-only law, and the fix at the generating layer.", "Ch7"),
Q("Defaults vs restrictions:", ["Are the same", "Defaults make the right choice easy; restrictions make the wrong choice impossible — mature setups use both", "Are alternatives", "Are optional"], 1, "The Ikeja cashier has no honest reason to move Abeokuta's stock.", "Ch7"),
Q("In the design session, the fridge inside Central became:", ["Its own warehouse", "Location detail — same custodian, so not a warehouse; the consumables corner earned a room", "A group", "Quarantine"], 1, "The line held twice, both directions.", "Ch8"),
Q("Returns staging was folded into quarantine because:", ["Returns are rare forever", "The volume does not yet earn a room — decided, written down, with its revisit trigger", "Staging is wrong", "The MD said so"], 1, "Proportionality, documented.", "Ch8"),
Q("The storekeeper's 'but the shelf shows 96' became:", ["An argument", "The four-numbers lesson live — actual 96, reserved 40, incoming 60, projected 116", "A recount", "A ticket"], 1, "The bin read is the literacy.", "Ch8"),
Q("The setup-week mispost was resolved by:", ["Editing the receipt", "Ledger diagnosis, correction by transfer, and tightening the default that allowed it", "Ignoring it", "A write-off"], 1, "The full response pattern, demonstrated.", "Ch8"),
Q("Warehouse sprawl is fixed by:", ["More warehouses", "The accountability test, a documented consolidation pass, and narrowed creation rights", "Renaming", "A bigger tree"], 1, "The tree grows by decision, not convenience.", "Ch9"),
Q("The cheap fix in the disease family is:", ["Merging leaves", "Re-parenting with groups — structure re-shapes far more easily than custodies merge", "Starting over", "None exists"], 1, "Which is why erring simple at design is safe.", "Ch9"),
Q("This module's law is:", ["Warehouses are buildings", "The warehouse tree is the map of custody — every place stock can be is named, valued, and owned", "Fewer warehouses always", "Stock lives anywhere"], 1, "Stock lives only in named places; seven modules stand on this floor.", "Ch9"),
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

    if os.path.exists(os.path.join(root, DATA_PATH)):
        print("Already applied. Nothing to do.")
        return
    if '"3.104.0"' not in init:
        sys.exit("ABORT: not at v3.104.0.")

    problems = []
    if len(LESSONS) != 9:
        problems.append(f"  {len(LESSONS)} lessons (want 9)")
    short = [f"{l['title'][:40]} ({len(l['html'])})" for l in LESSONS if len(l["html"]) < 2500]
    if short:
        problems.append(f"  below manual depth: {short}")
    if len(QUESTIONS) != 35:
        problems.append(f"  {len(QUESTIONS)} questions (want 35)")
    for q in QUESTIONS:
        if len(q["opts"]) != 4 or not (0 <= q["ans"] <= 3):
            problems.append(f"  malformed '{q['q'][:40]}'")
    if "ERPNext" in json.dumps({"l": LESSONS, "q": QUESTIONS}):
        problems.append("  ERPNext branding leakage")
    if problems:
        print("ABORT — not clean:")
        print("\n".join(problems))
        sys.exit(1)

    bank = rebalance(list(QUESTIONS))
    dist = {c: sum(1 for q in bank if q["ans"] == i) for i, c in enumerate("ABCD")}
    if max(dist.values()) > 10:
        print(f"ABORT — spread failed: {dist}")
        sys.exit(1)

    total = sum(len(l["html"]) for l in LESSONS)
    print(f"Inventory 1: 9 chapters ({total:,} chars, min {min(len(l['html']) for l in LESSONS):,}), bank {len(bank)}, spread {dist}")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data = {
        "warehouses": {
            "title": "Inventory 1 — Warehouses & the Stock Architecture",
            "desc": "The foundation of the inventory certification: the warehouse as an accountability unit, tree design, the append-only stock ledger, the four numbers of a bin, the logical rooms, stock as custody of value, and the defaults that wire documents to the tree.",
            "lessons": LESSONS,
            "questions": bank,
        }
    }
    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    with io.open(os.path.join(root, SEEDER_PATH), "w", encoding="utf-8") as f:
        f.write(SEEDER)
    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.104.0"', '"3.105.0"'))
    print("  created: academy_inventory_pro_data.json (Inventory 1)")
    print("  created: academy_seed_inventory_pro.py (product, track ZERP-INVPRO, refresh functions)")
    print("wrote __version__ -> 3.105.0")


if __name__ == "__main__":
    main()
