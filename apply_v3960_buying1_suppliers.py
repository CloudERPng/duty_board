#!/usr/bin/env python3
"""Duty Board v3.96.0 — the Procurement track opens (Buying pass 1 of 8).

Creates the ZhiftERP Procurement Professional certification
infrastructure — academy_procure_pro_data.json + academy_seed_procure_pro.py
(mirroring the sales seeder: idempotent seed with track-append,
refresh_lessons(only=), refresh_questions(only=)) — and ships Buying 1:
Suppliers & the Supply Base at manual depth from birth: 9 chapters,
35-question bank, no thin-seed-then-rewrite cycle this time.

Modules sort at 30+ so the track groups after Selling in My Training.

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_procure_pro.seed_procure_pro_track

Anchored, idempotent. Requires v3.95.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_procure_pro_data.json"
SEEDER_PATH = "duty_board/academy_seed_procure_pro.py"
CHECK_ONLY = "--check" in sys.argv

L = lambda t, est, html: {"title": t, "est": est, "html": html}
Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

LESSONS = [
L("Chapter 1 — The Supplier master, field by field", "15", "<p>Selling taught that documents are downstream of masters; procurement obeys the same law from the other side of the counter. Every purchase order, receipt and purchase invoice begins with WHO you are buying from — a <b>Supplier</b> record — and the quality of that record decides whether your payables reconcile, your costs report truthfully, and your import exposure is visible or a surprise. This chapter walks the record field by field, through a buyer's eyes.</p><ul><li><b>Supplier Name</b> — the registered trading name, exactly as their invoices will carry it, because your accounts team will match paper to record for years. The identity-scheme decision (name-keyed vs series-keyed IDs) mirrors the selling side and is made once in Buying Settings — Buying 8's treatment; the preview: supply bases dense with similar names (three different Emzor distributors, five generic-pharma importers) want the series.</li><li><b>Supplier Type</b> — Company or Individual. More than a label in Nigeria: it drives the WHT rate your firm must withhold when paying them (Buying 7's chapter — companies and individuals are withheld at different rates), so misclassifying a supplier misclassifies a tax obligation.</li><li><b>Supplier Group</b> — the segmentation backbone (Chapter 2), assigned at creation.</li><li><b>Country and Currency</b> — the supplier's billing currency is a structural fact: a Mumbai API manufacturer bills USD, a Lagos logistics firm bills NGN, and the record's currency drives every document's default and your FX-exposure reporting (Chapter 4). Set it to what their invoices actually say, not what you wish.</li><li><b>Default Payment Terms</b> — the credit THEY extend YOU: Net 30 from a manufacturer, advance-only from a new importer. Inherited by every purchase document (Chapter 4), and collectively these fields ARE your firm's short-term funding structure (Chapter 6).</li><li><b>Default Price List / tax category</b> — the buying price list holding their agreed rates (Buying 2), and the tax posture governing what you withhold and what input VAT you claim (Buying 7).</li><li><b>TIN and bank details</b> — their tax identity (your WHT remittances reference it) and where payment runs will send money: captured at onboarding, verified from their letterhead, because payment-detail fraud lives in casually edited bank fields — Chapter 7 makes changing these a controlled event.</li></ul><p><b>The onboarding standard.</b> As with customers: a supplier created with only a name is a payables mess on layaway. Group, currency, terms, TIN, bank details, contact — set before the first purchase order, in one sitting, from documents the supplier provided. The master record is a contract with your future month-ends; sign it properly.</p>"),
L("Chapter 2 — Supplier Groups: designing the supply-base tree", "13", "<p>Supplier Group is the mirror of Selling 1's customer tree, and the design logic transfers consciously: one tree, one question, leaves assignable in two seconds. The question here: <b>what KIND of supply is this?</b> — because every spend report, every risk review, and every negotiation strategy will be cut by this tree.</p><p><b>The mechanics.</b> Groups form a tree (group nodes and leaves); suppliers attach to leaves; reports roll up through parents. Purchase analytics grouped by supplier group is your spend-mix instrument — where the money goes, by category, per period — and the tree you design is the shape of every answer it gives.</p><p><b>Designing for a Nigerian trading reality.</b> A pharmacy-and-retail distributor's supply base might read: <i>All Supplier Groups → Manufacturers (→ Pharma — Local · Pharma — Import · FMCG) · Distributors &amp; Wholesalers · Importers &amp; Clearing · Services (→ Logistics · Professional · Facilities) · Utilities &amp; Statutory</i>. A dozen leaves. The tests, verbatim from the selling side because they ARE the same tests: every supplier lands somewhere obvious in two seconds; every branch answers a question management actually asks (what did we spend on logistics this quarter? how import-dependent is our pharma line?); and no leaf is a landfill — a Misc that accumulates everything classifies nothing.</p><p><b>What the tree is NOT.</b> Not a payment-priority ranking (that lives in terms and the payment run, Buying 7), not a quality grade (the scorecard carries that, Buying 8), not geography (country fields and addresses answer where). One tree, one question — mixed-question trees rot from the first ambiguous supplier onward.</p><p><b>Why category cuts matter commercially.</b> Three standing conversations run off this tree. <b>Import dependence:</b> the share of spend under import-side leaves is your FX-vulnerability number — the board question after every naira move, answerable in one grouping. <b>Category concentration:</b> one leaf dominated by one supplier is a single point of failure wearing a group name; the quarterly read flags where a second source is owed (Buying 4's RFQ discipline is the remedy). <b>Negotiation posture:</b> consolidated category spend is leverage — the distributor who knows their full FMCG number negotiates it; the one who buys the same category through five unconnected records at five prices funds everyone else's discounts.</p><p><b>The default group.</b> Buying Settings names one for hurried creation: point it at the genuinely commonest leaf, never the root, never Misc — and keep the weekly new-supplier review that catches misfiles while they are young. The safety net is a net, not a filing system.</p>"),
L("Chapter 3 — Contacts & addresses: the people and places of supply", "13", "<p>A supplier is a company; you cannot phone a company, and goods do not ship from a concept. The people layer (Contacts) and the places layer (Addresses) mirror Selling 1's Chapters 4-5 exactly — linked records, primary flags, the customer machinery pointed the other way — with buy-side stakes of their own.</p><p><b>Contacts — who you actually deal with.</b> The sales manager who takes your orders, the accounts receivable clerk who chases YOUR payments, the logistics coordinator who books deliveries: each a Contact linked to the supplier, with designation, emails, phones, and a primary flag. The buy-side reason the layer matters: <b>continuity through their staff turnover</b>. When the sales rep who knew your account resigns, your record survives — the new rep's details replace the old contact, and five years of purchase history stay attached to the company, not to a person's phone number in someone's handset. Firms that keep supplier relationships in individual staff WhatsApps rebuild them from zero at every resignation — theirs or yours.</p><p><b>Addresses — where paper goes and goods come from.</b> One supplier, many places: the head office that receives your purchase orders and issues invoices (billing), the factory or warehouse goods actually ship from (shipping), sometimes a clearing agent's address for import flows. Address type and primary flags govern which lands on which document — the PO prints the right office; the receipt expects goods from the right origin. The consequential case: <b>a supplier with multiple fulfilment points</b> (a manufacturer shipping from Lagos or Ogun depending on line) keeps each as an address, and the purchase order's chosen address tells your receiving team what origin to expect — paperwork that matches the truck at the gate.</p><p><b>Primary-flag discipline, buy-side edition.</b> The wrong primary contact means your POs email into a void (the resigned rep's dead inbox — orders placed and never acknowledged); the wrong primary address means documents address the factory while their accounts office waits. Both present later as mysterious delays; both fix at the master in one move, never document-by-document — the anti-fix conviction transfers verbatim from the selling side.</p><p><b>Bank details are not an address, and are guarded harder.</b> Where payment goes lives on the supplier record and in the payment run — and a change to it is a controlled event: verified against supplier letterhead or a known contact by phone, never actioned from an email alone, because supplier-impersonation fraud is precisely an email asking you to update bank details before the next run. Buying 7 builds the payment-run control; the master-level habit starts here: bank fields change rarely, verifiably, and with a second pair of eyes.</p>"),
L("Chapter 4 — Currencies, terms & the document default chain", "13", "<p>Three master fields — currency, payment terms, price list — flow from the supplier record onto every purchase document, and this chapter is that defaulting chain plus the two buy-side realities riding it: FX exposure and inherited credit.</p><p><b>The chain, recited cold.</b> A purchase document naming a supplier inherits: their <b>currency</b> (the document transacts in it — a USD manufacturer's PO is a USD PO, converted for your books at the exchange rate, displayed on the document exactly as the selling side's multi-currency machinery worked); their <b>payment terms</b> (the due-date engineering of Buying 7 starts from the master's template); their <b>buying price list</b> (agreed purchase rates, Buying 2); their tax defaults (what you withhold, what input VAT you record — Buying 7). Nobody re-decides these per document; the master decided, and the document executes — which is the entire architecture of not making Tuesday's data-entry clerk the author of your commercial arrangements.</p><p><b>FX exposure, made visible.</b> Every foreign-currency supplier is a naira risk position: the USD PO priced at today's rate lands as a payable whose naira cost moves with the market until settled. The record-level discipline that makes exposure REPORTABLE: supplier currency set to what they actually bill (never NGN-because-we-pay-from-a-naira-account — the conversion happens at payment either way; recording it wrong just hides the exposure), and import-side supplier groups (Chapter 2) so the aggregate foreign position is one grouping away. What your Montaigne-class selling clients ask about receivables, your own finance asks about payables: how much of what we owe is not in naira, and when does it fall due?</p><p><b>Their terms are your credit facility.</b> Net-30 from a supplier is thirty days of interest-free funding on every purchase — collectively, supplier terms are usually a trading firm's largest single credit line. Which is why the master's terms field deserves negotiation attention, not default acceptance: the onboarding conversation that moves a key supplier from advance-only to Net-15 to Net-30 as trust builds is treasury work conducted by procurement, and the record is where each stage is encoded. The mirror discipline from selling applies with roles reversed — you are now the customer whose payment behaviour is being scored, and Chapter 6 makes the case that paying WELL is a procurement strategy, not a finance nicety.</p><p><b>One supplier, one record, however many currencies tempt you.</b> The supplier who bills you USD for imports and NGN for local warehousing is still one supplier — one record in their PRIMARY billing currency, with the minority-currency flow handled at document level. Two records for one company (Emzor USD and Emzor NGN) is the duplicate disease in procurement clothing: split payables, split history, split negotiating knowledge — and their statement reconciles against neither half.</p>"),
L("Chapter 5 — The payable posture: managing what you owe", "13", "<p>Selling 7 built the receivables craft; this chapter is its mirror — the deliberate management of what your firm owes — because payables run on decisions exactly as collections do, and a firm that only ever reacts to supplier calls is running its funding structure by whoever shouts loudest.</p><p><b>The payables ledger as one screen.</b> Every submitted purchase invoice (Buying 7) stands as a payable aging by its due date; the <b>Accounts Payable report</b> buckets it — 0-30, 31-60, 61-90, 90+ — per supplier, exactly as AR bucketed customers. The professional read is different from AR's, though: right-column entries in AR were money owed TO you going stale; right-column entries in AP are your firm's payment PROMISES going broken — supplier trust burning, credit terms about to shorten, and eventually supply itself at risk. The read: due-this-week (fund it), coming-due (schedule it), overdue (explain it, personally, before the supplier calls).</p><p><b>Paying well is procurement strategy.</b> The firm that pays on the day earns three things no negotiation can buy: priority allocation when supply is short (the distributor with scarce stock ships to who pays), terms extension over time (Net-15 becomes Net-30 for the account that never slips), and pricing candour (suppliers pad quotes to slow payers — the risk premium is invisible but real, and your firm pays it in every rate). Late payment is a loan taken from your supplier at the price of all three. Sometimes that loan is worth taking — cash crunches are real — but it should be TAKEN, deliberately, with a call and a date, not defaulted into by an unread AP report.</p><p><b>The supplier statement reconciliation.</b> Monthly, key suppliers send statements; the discipline is reconciling them against your ledger while discrepancies are one month deep: invoices they show that you never recorded (goods received, paper lost — Buying 6-7's three-way match catches most), payments you show that they have not applied (your reference discipline at fault, or their allocation — the remittance-advice habit from Selling 7, now written by you), and disputed items flagged on both sides. A supplier account reconciled monthly never produces the year-end archaeology where two firms discover they disagree by millions and neither can say why.</p><p><b>Advance payments to suppliers.</b> The buy-side advance — deposit against an import order, mobilisation on a contract — mirrors Selling 7 Chapter 5 with the roles reversed: a Payment Entry against the supplier with no invoice yet, sitting as YOUR credit on THEIR account, allocated when their invoice lands. The same black hole threatens in reverse: advances never allocated mean invoices paid twice or supplier balances nobody trusts — the monthly unallocated read covers both directions of trade.</p>"),
L("Chapter 6 — Supplier lifecycle: onboarding, hold & retirement", "13", "<p>Suppliers have lifecycles — vetted in, paused when trouble surfaces, retired when the relationship ends — and each stage has a correct instrument. Improvised lifecycle management is how firms keep buying from suppliers they resolved to drop, and how they delete history they later need in a dispute.</p><p><b>Onboarding as a gate, not a formality.</b> Before the first purchase order: the record built to Chapter 1's standard (group, currency, terms, TIN, bank details verified from supplier documents), and for regulated goods, the compliance layer — a pharma supplier's NAFDAC standing and documentation checked and filed, because your downstream batch discipline (Selling 5's recall drill) is only as good as the provenance of what enters your warehouse. The onboarding checklist is short, written, and owned; a supplier who cannot complete it is telling you something worth hearing before money moves.</p><p><b>Hold — the pause with teeth.</b> When a quality dispute erupts, documentation lapses, or fraud is suspected, the supplier is placed <b>on hold</b> — and the hold has a TYPE: block everything, block new invoices, or block payments — plus an optional release date. The type is the craft: a quality investigation blocks new purchase documents while existing invoices still settle honestly (you owe what you owe); a payment dispute blocks the payment run while receiving continues; a full block freezes the relationship pending resolution. The hold does what memos cannot: the buyer who did not get the memo physically cannot raise the PO. Every hold carries an owner and a next step — an unowned hold is either forgotten (supply quietly resumes) or eternal (a dead record blocking a live relationship).</p><p><b>Disable, never delete.</b> A retired supplier — closed down, replaced, relationship ended — is <b>disabled</b>: invisible to new documents, fully present in history. Deletion is the wrong end for exactly the selling-side reasons: the purchase history, the price trail, the dispute evidence, the batch provenance all reference the record. The supplier you dropped over quality in 2024 is the record you need intact in 2026 when a batch from their era surfaces in a complaint.</p><p><b>Duplicates, merged early.</b> The same company entered twice — once by each buyer, once per currency (Chapter 4's conviction), once with a spelling variant — splits payables and history until merged. The search-before-create reflex is the prevention (third module in this manual family to say so, because it is the same disease in every master); the cure is a deliberate merge while the duplicate is young, not a two-year archaeology.</p><p><b>The review cadence.</b> Quarterly, the supply base gets thirty minutes: new suppliers correctly filed (the weekly habit rolled up), holds reviewed against their next steps, concentration flags from Chapter 2's tree, and terms renegotiation candidates (Chapter 4). A supply base is a portfolio; portfolios get reviewed.</p>"),
L("Chapter 7 — Compliance & the Nigerian buy-side frame", "13", "<p>Buying in Nigeria carries obligations selling never taught, and the supplier master is where each one anchors. This chapter frames them now so the document modules land on prepared ground — each gets its full mechanics later; a professional carries the MAP from day one.</p><p><b>WHT — this time you withhold.</b> Selling 7 taught the deduction from the receiving side: your customers withheld from you. Procurement reverses the role: when YOUR firm pays qualifying suppliers for services and contracts, YOU are the withholding agent — deducting at the supplier-type-appropriate rate (companies and individuals differ; the accountant owns the schedule), remitting to FIRS against the supplier's TIN, and issuing the credit evidence they will chase you for exactly as you chase your customers. The master-level anchors: <b>Supplier Type</b> set correctly (it selects the rate class) and <b>TIN captured</b> (remittance requires it). Buying 7 carries the payment-entry mechanics; the posture to internalise now is symmetry — every discipline you wished your customers had about WHT certificates, your suppliers wish about yours.</p><p><b>Input VAT — the other half of the 21st.</b> The VAT on your purchase invoices is <b>input VAT</b>: claimable against the output VAT your sales collect, netted in the monthly FIRS filing (Selling 6 taught the output side and the deadline). The claim is only as good as its paper — a proper tax invoice from a VAT-registered supplier, recorded against the right tax head — which makes supplier tax hygiene a cash matter: unclaimable input VAT is real money donated monthly. The master anchors: the supplier's tax registration captured, the buy-side tax templates defaulting correctly.</p><p><b>Import documentation.</b> For the import-side supply base (Chapter 2's tree made it visible): Form M, letters of credit, bills of lading, PAAR, clearing-agent chains — the document trail that landed cost is built from (Buying 6 treats landed cost mechanics). The record-keeping habit: import paperwork files against the purchase cycle's documents, so the true cost of a container is assembled from records, not reconstructed from a clearing agent's memory.</p><p><b>Regulated goods provenance.</b> Pharma and food supply chains carry NAFDAC obligations UPSTREAM: the supplier's registration status, product listings, and batch documentation are onboarding requirements (Chapter 6's gate) and standing records — because when Selling 5's recall drill runs, the question after WHICH CUSTOMERS is WHICH SUPPLIER, and the answer must be as fast.</p><p><b>Payment-detail fraud, the standing threat.</b> Chapter 3 set the rule; it bears its own paragraph: bank-detail changes verified out-of-band, payment runs built from the master's verified details, and any email requesting an urgent account change treated as hostile until proven otherwise. The control is boring; the losses it prevents are not.</p>"),
L("Chapter 8 — Case study: building the supply base for a pharmacy distributor", "16", "<p>Everything in this module, executed once. HealthTrade Ltd — the dual-channel vendor whose SELLING architecture Selling 2 built — now gets its supply base done properly. Read actively; every step names its chapter.</p><p><b>The business.</b> HealthTrade buys: pharma from two local manufacturers and one Indian exporter; FMCG from a Lagos mega-distributor; logistics from a haulage firm; clearing from an agent handling the import lane. Six suppliers, three currencies of exposure, one afternoon of master-data work.</p><p><b>Step 1 — the tree (Ch. 2).</b> Supplier groups: Manufacturers (→ Pharma — Local · Pharma — Import), Distributors &amp; Wholesalers, Services (→ Logistics · Clearing &amp; Professional). Six leaves, each answering a spend question the MD actually asks — import dependence is now one grouping away, forever.</p><p><b>Step 2 — the two local manufacturers (Ch. 1, 4).</b> Records built to standard: Company type (corporate WHT class), Pharma — Local, NGN, Net-30 terms as negotiated, TINs from their letterheads, bank details from their account-opening letters — filed. Contacts: each firm's sales manager and accounts officer, primaries flagged (Ch. 3). Their NAFDAC documentation checked and filed at onboarding (Ch. 6-7's gate).</p><p><b>Step 3 — the Indian exporter (Ch. 4, 7).</b> Currency USD — what their invoices actually say. Terms: 30% advance, balance against shipping documents — encoded as their template, the advance flow ready for Buying 7's mechanics (Ch. 5's advance discipline). Addresses: Mumbai head office (billing) and the factory (origin) — the receiving team will know what the paperwork should match (Ch. 3). The import-documentation file opens with their record (Ch. 7).</p><p><b>Step 4 — the mega-distributor and the services pair (Ch. 1-3).</b> The FMCG distributor: Company, NGN, Net-15 (to be renegotiated upward as volume proves — the treasury note is on the record, Ch. 4). The haulage firm and the clearing agent: Services leaves — and the clearing agent is Individual type, which the accountant confirms changes the WHT class (Ch. 1, 7). Every record: contacts, TINs, verified bank details.</p><p><b>Step 5 — the payable posture, scheduled (Ch. 5).</b> The AP report's weekly read lands in Friday's routine (due-this-week funded, overdue explained proactively); monthly statement reconciliation is agreed with both manufacturers from month one; the unallocated-advances read covers the exporter's deposit flow.</p><p><b>Step 6 — the near-miss that proves the controls (Ch. 3, 7).</b> Week three: an email arrives from the haulage firm's domain-lookalike asking to update bank details before the next run. The rule holds — out-of-band verification by phone to the known contact — and the fraud dies in one call. The control cost nothing; its absence would have cost a payment run.</p><p><b>What the afternoon bought:</b> spend reportable by category and currency from day one; WHT classes and TINs ready before the first payment; terms encoded as negotiated, with the renegotiation path noted; import exposure visible in one grouping; provenance documentation filed for the recall that will someday ask; and a payables posture that will make HealthTrade the customer its suppliers ship to first when stock is short. Master data is strategy stored where documents can execute it.</p>"),
L("Chapter 9 — Common mistakes & support patterns", "13", "<p>The supply-base scar tissue: the tickets you will meet, the disease behind each, the fix — and the law this module hands to the rest of the track.</p><p><b>Pattern 1 — \"The PO went out and nobody at the supplier saw it.\"</b> Disease: primary contact is the resigned rep's dead inbox (Ch. 3). Fix at the master — replace the contact, re-flag primary; the anti-fix (typing addresses per document) subscribes to the ticket. The selling side's first pattern, mirrored exactly, because it is the same machinery.</p><p><b>Pattern 2 — \"We have this supplier twice and their statement matches neither.\"</b> Disease: the duplicate — per buyer, per spelling, or per currency (Ch. 4, 6). Split payables, split history, no negotiating memory. Fix: merge while young; prevention is search-before-create, the law of every master in this manual family.</p><p><b>Pattern 3 — \"Everything we buy from them shows due immediately.\"</b> Disease: terms never set on the master, so no due-date engineering exists (Ch. 4) — the AP report reads as a wall of now, and the payment run cannot prioritise. Fix: encode the actual agreed terms; the documents that follow inherit sanity. (The already-issued invoices keep their dates — correcting forward is the honest scope.)</p><p><b>Pattern 4 — \"Our naira costs jumped and nobody saw it coming.\"</b> Disease: foreign suppliers recorded as NGN because payment leaves a naira account (Ch. 4) — the FX exposure was real but invisible. Fix: currencies set to what invoices say; import-side grouping (Ch. 2) so the aggregate position is one report.</p><p><b>Pattern 5 — \"We resolved to stop buying from them, and a PO went out Tuesday.\"</b> Disease: the resolution lived in a meeting, not a hold (Ch. 6). Fix: the hold with the right type and an owner — the buyer who missed the memo cannot miss the block.</p><p><b>Pattern 6 — \"A supplier says we owe invoices we have never seen.\"</b> Disease: no statement-reconciliation habit (Ch. 5) — goods received against paper that never reached the ledger, discovered at relationship-threatening age. Fix: monthly reconciliation with key suppliers; the three-way match (Buying 6-7) closes the gap going forward.</p><p><b>Pattern 7 — \"Finance updated bank details from an email and the run paid a fraudster.\"</b> Disease: the control that existed in policy but not in practice (Ch. 3, 7). Fix — after the painful recovery attempt — is procedural and absolute: out-of-band verification for every detail change, no exceptions for urgency, BECAUSE of urgency. The fraud's entire design is that the email arrives the day before the run.</p><p><b>The law, mirrored.</b> Selling opened with: documents are downstream of masters. Procurement's first module closes the same way, from the other chair: <b>purchase documents are downstream of supplier masters</b> — the PO's currency, the receipt's expectations, the invoice's terms, the payment's destination and withholding all execute what the record encodes. Build the record right and the buying cycle — Material Requests onward, starting next module — mostly runs itself. The consultant who fixes supplier masters closes procurement tickets permanently; the one who fixes documents subscribes to them.</p>"),
]

QUESTIONS = [
Q("Supplier Type (Company vs Individual) matters in Nigeria because:", ["It is cosmetic", "It drives the WHT rate class your firm must withhold when paying them", "It sets the currency", "It controls stock"], 1, "Misclassifying a supplier misclassifies a tax obligation.", "Ch1"),
Q("A supplier's currency field should be set to:", ["NGN always, since payment leaves a naira account", "What their invoices actually say", "The cheapest currency", "USD for imports regardless"], 1, "Recording it wrong just hides the FX exposure.", "Ch1, Ch4"),
Q("A supplier created with only a name is:", ["Fast and harmless", "A payables mess on layaway — group, currency, terms, TIN, bank details come first", "Automatically completed", "Blocked by the system"], 1, "The master record is a contract with your future month-ends.", "Ch1"),
Q("The supplier-group tree answers the single question:", ["Who pays fastest", "What KIND of supply is this", "Where the supplier is located", "Which buyer owns them"], 1, "One tree, one question — spend reports are cut by it.", "Ch2"),
Q("Import dependence is answered by:", ["Guesswork", "The share of spend under import-side supplier-group leaves", "The bank statement", "The customer tree"], 1, "The board question after every naira move, one grouping away.", "Ch2"),
Q("One category leaf dominated by one supplier signals:", ["Efficiency", "A single point of failure — a second source is owed", "Loyalty to reward", "Nothing"], 1, "The quarterly concentration read flags it; RFQ discipline remedies it.", "Ch2"),
Q("Buying the same category through five unconnected records at five prices means:", ["Healthy competition", "You fund everyone else's discounts — consolidated spend is leverage", "Better risk spread", "Lower prices"], 1, "The distributor who knows their full category number negotiates it.", "Ch2"),
Q("Supplier contacts exist so that:", ["Emails look formal", "Relationships survive staff turnover — theirs and yours", "The tree stays clean", "Payments accelerate"], 1, "History attaches to the company, not to a phone in someone's handset.", "Ch3"),
Q("A manufacturer shipping from two possible origins is modelled with:", ["Two supplier records", "Multiple addresses — the PO's chosen address tells receiving what to expect", "A remark", "Two currencies"], 1, "Paperwork that matches the truck at the gate.", "Ch3"),
Q("POs emailing into a void usually trace to:", ["Server issues", "The primary contact being a resigned rep's dead inbox", "Wrong currency", "Missing TIN"], 1, "Fix at the master; documents follow.", "Ch3, Ch9"),
Q("A supplier bank-detail change request arriving by email is:", ["Actioned before the next run", "Treated as hostile until verified out-of-band with a known contact", "Forwarded to the bank", "Ignored forever"], 1, "The fraud's design is urgency the day before the run.", "Ch3, Ch7, Ch9"),
Q("The document default chain inherits from the supplier master:", ["Only the name", "Currency, payment terms, buying price list, and tax defaults", "The warehouse", "The customer group"], 1, "The master decided; documents execute.", "Ch4"),
Q("Supplier payment terms are collectively:", ["A courtesy", "Usually the firm's largest single credit line — thirty days of interest-free funding per purchase", "A tax matter", "Irrelevant to treasury"], 1, "Terms negotiation is treasury work conducted by procurement.", "Ch4"),
Q("A supplier billing USD for imports and NGN for local services gets:", ["Two records, one per currency", "One record in the primary billing currency; minority flows handled at document level", "Three records", "A merged customer record"], 1, "Two records for one company is the duplicate disease in procurement clothing.", "Ch4"),
Q("Right-column (90+) entries in Accounts Payable are:", ["Money owed to you going stale", "Your payment promises going broken — trust burning, terms at risk", "Tax credits", "Healthy float"], 1, "AP's right columns read differently from AR's.", "Ch5"),
Q("Paying suppliers on the day earns:", ["Nothing measurable", "Priority allocation in shortage, terms extension, and pricing candour", "Only goodwill", "Penalties"], 1, "Suppliers pad quotes to slow payers; the premium is invisible but paid in every rate.", "Ch5"),
Q("Taking extra time to pay in a cash crunch should be:", ["Defaulted into silently", "Taken deliberately — with a call and a date", "Denied", "Hidden from the supplier"], 1, "The loan is sometimes worth taking; it is never worth stumbling into.", "Ch5"),
Q("Monthly supplier-statement reconciliation catches:", ["Nothing new", "Their invoices you never recorded, your payments they never applied — at one month deep", "Only fraud", "Tax errors only"], 1, "Never the year-end archaeology where two firms disagree by millions.", "Ch5"),
Q("An advance paid to a supplier is recorded as:", ["Unrecorded until their invoice", "A Payment Entry against the supplier, sitting as your credit, allocated when the invoice lands", "An expense", "A negative PO"], 1, "The unallocated black hole threatens in both directions of trade.", "Ch5"),
Q("Supplier onboarding for regulated pharma goods includes:", ["Only bank details", "NAFDAC standing and documentation checked and filed before money moves", "A handshake", "A trial order first"], 1, "Downstream recall discipline is only as good as upstream provenance.", "Ch6, Ch7"),
Q("The supplier hold's TYPE matters because:", ["It doesn't", "Quality issues block new purchases while honest debts still settle; payment disputes block the run while receiving continues", "All holds are total", "It sets the release date only"], 1, "The type is the craft; the block does what memos cannot.", "Ch6"),
Q("Every supplier hold carries:", ["A release date only", "An owner and a next step", "A penalty", "Board approval"], 1, "Unowned holds are forgotten or eternal.", "Ch6"),
Q("A retired supplier is:", ["Deleted for cleanliness", "Disabled — invisible to new documents, fully present in history", "Renamed", "Merged into Misc"], 1, "The 2024 quality-dispute record is the evidence you need intact in 2026.", "Ch6"),
Q("The prevention for supplier duplicates is:", ["Quarterly purges", "Search before create — the same law as every master in this manual family", "Locking creation", "One buyer only"], 1, "The cure is a deliberate merge while the duplicate is young.", "Ch6, Ch9"),
Q("In procurement, WHT works as:", ["Your customers withhold from you", "YOUR firm withholds when paying qualifying suppliers, remits to FIRS against their TIN, and issues the evidence", "A VAT substitute", "Optional"], 1, "The role reverses: you are now the withholding agent.", "Ch7"),
Q("The master-level anchors for WHT compliance are:", ["Currency and address", "Supplier Type (rate class) and TIN (remittance reference)", "Price list and group", "Hold type"], 1, "Set at onboarding, used at every qualifying payment.", "Ch1, Ch7"),
Q("Input VAT on purchases is:", ["A cost, always", "Claimable against output VAT in the monthly filing — if the paper is proper", "Ignored", "Withheld from suppliers"], 1, "Unclaimable input VAT is real money donated monthly.", "Ch7"),
Q("Import paperwork (Form M, bills of lading, PAAR) should be:", ["Kept by the clearing agent", "Filed against the purchase cycle's documents as landed cost is assembled", "Discarded after clearing", "Emailed monthly"], 1, "True container cost comes from records, not an agent's memory.", "Ch7"),
Q("In the HealthTrade build, the clearing agent's Individual type mattered because:", ["It changed the currency", "It changes the WHT class — confirmed with the accountant", "It blocked the record", "It set the group"], 1, "Supplier Type is a tax fact wearing a form field.", "Ch8"),
Q("The domain-lookalike bank-change email in the case study died because:", ["The firewall caught it", "Out-of-band phone verification to the known contact was the rule, urgency or not", "The bank refused", "It was ignored by luck"], 1, "The control cost nothing; its absence would have cost a payment run.", "Ch8"),
Q("The Indian exporter's addresses (Mumbai office + factory) let:", ["Two records exist", "Receiving know what origin the paperwork should match", "Currency conversion", "Faster clearing"], 1, "Billing and origin are different places on one record.", "Ch8"),
Q("Terms 'to be renegotiated upward as volume proves' belong:", ["In a buyer's memory", "As a note on the record — treasury work encoded where procurement executes", "Nowhere", "In the group name"], 1, "The renegotiation path is part of the master's story.", "Ch4, Ch8"),
Q("'Everything shows due immediately' traces to:", ["A system bug", "Terms never set on the master — no due-date engineering exists", "FX rates", "The hold"], 1, "Encode the agreed terms; documents inherit sanity forward.", "Ch9"),
Q("The fix scope for missing terms is:", ["Rewriting old invoices' dates", "Correcting forward — issued invoices keep their dates", "Deleting history", "A new supplier record"], 1, "Honest scope: the master governs what comes next.", "Ch9"),
Q("This module's law is:", ["Suppliers manage themselves", "Purchase documents are downstream of supplier masters", "Payables beat receivables", "Holds are optional"], 1, "The PO's currency, the receipt's expectations, the payment's destination all execute the record.", "Ch9"),
]


def rebalance(questions):
    for i, q in enumerate(questions):
        target = i % 4
        a = q["ans"]
        if a != target:
            q["opts"][a], q["opts"][target] = q["opts"][target], q["opts"][a]
            q["ans"] = target
    return questions


SEEDER = '''"""ZhiftERP Procurement Professional track seed — the buying curriculum.

Content lives in academy_procure_pro_data.json. Modules are PROCTORED:
timed 60s/question, 10 served from each 35-question bank. Modules are
added pass by pass; re-running the seed appends new modules to the
existing track (idempotent per module and for the track).

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_procure_pro.seed_procure_pro_track
"""

import json
import os

import frappe

ORDER = ["suppliers"]

TRACK = {
\t"title": "ZhiftERP Procurement Professional",
\t"serial_prefix": "ZERP-PROCPRO",
\t"description": "The complete buying certification: supplier management, purchase items and costs, material requests, sourcing, purchase orders, receiving and quality, purchase invoicing and payments with Nigerian withholding and input-VAT practice, and the advanced buying layer — proctored examinations from the supply base to the reports that run procurement.",
}


def _data():
\tpath = os.path.join(os.path.dirname(__file__), "academy_procure_pro_data.json")
\twith open(path) as f:
\t\treturn json.load(f)


def seed_procure_pro_track():
\tdata = _data()
\tif not frappe.db.exists("Duty Product", "ZhiftERP"):
\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP", "active": 1, "sort_order": 0}).insert(
\t\t\tignore_permissions=True
\t\t)
\t\tprint("created Duty Product: ZhiftERP")

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
\t\t\t\t"product": "ZhiftERP",
\t\t\t\t"description": m["desc"],
\t\t\t\t"active": 1,
\t\t\t\t"audience": "Both",
\t\t\t\t"sort_order": 30 + i,
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
\t\t\t\t"product": "ZhiftERP",
\t\t\t\t"audience": "Consultant",
\t\t\t\t"serial_prefix": TRACK["serial_prefix"],
\t\t\t\t"description": TRACK["description"],
\t\t\t\t"active": 1,
\t\t\t\t"modules": [{"module": module_names[k]} for k in ORDER],
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tprint(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

\tfrappe.db.commit()
\tprint("ZhiftERP Procurement Professional track ready.")


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


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()

    if os.path.exists(os.path.join(root, DATA_PATH)) and os.path.exists(os.path.join(root, SEEDER_PATH)):
        print("Already applied. Nothing to do.")
        return
    if '"3.95.0"' not in init:
        sys.exit("ABORT: not at v3.95.0.")

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
    print(f"Buying 1: 9 chapters ({total:,} chars, min {min(len(l['html']) for l in LESSONS):,}), bank {len(bank)}, spread {dist}")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data = {
        "suppliers": {
            "title": "Buying 1 — Suppliers & the Supply Base",
            "desc": "The supplier master field by field, the supply-base tree, contacts and addresses, currencies and terms, the payable posture, supplier lifecycle, and the Nigerian buy-side compliance frame — the foundations every purchase document stands on.",
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
        f.write(init.replace('"3.95.0"', '"3.96.0"'))
    print("  created: academy_procure_pro_data.json (Buying 1)")
    print("  created: academy_seed_procure_pro.py (seed + refresh machinery, sort 30+)")
    print("wrote __version__ -> 3.96.0")


if __name__ == "__main__":
    main()
