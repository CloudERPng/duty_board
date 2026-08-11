#!/usr/bin/env python3
"""Duty Board v3.129.0 — ZhiftERP Payroll track: infrastructure
+ Payroll 1: The Payroll Function & Salary Structures (pass 1 of 8).

Creates duty_board/academy_payroll_pro_data.json and
duty_board/academy_seed_payroll_pro.py (faithful mirror of the HR
seeder: proctored modules, track-append idempotency,
refresh_lessons/refresh_questions). The track that completes the
trilogy: HR feeds it, finance receives it. Module 1 ships at manual
depth from birth: 9 chapters, 35-bank.

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_payroll_pro.seed_payroll_pro_track

Anchored, idempotent. Requires v3.128.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_payroll_pro_data.json"
SEEDER_PATH = "duty_board/academy_seed_payroll_pro.py"
CHECK_ONLY = "--check" in sys.argv

L = lambda t, est, html: {"title": t, "est": est, "html": html}
Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

SEEDER = '''"""ZhiftERP Payroll Professional track seed — the compensation
curriculum: the organ between HR and finance.

Content lives in academy_payroll_pro_data.json. Modules are
PROCTORED: timed 60s/question, 10 served from each 35-question bank.
Modules are added pass by pass; re-running the seed appends new
modules to the existing track (idempotent per module and for the
track).

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_payroll_pro.seed_payroll_pro_track
"""

import json
import os

import frappe

ORDER = ["payroll_function"]

TRACK = {
\t"title": "ZhiftERP Payroll Professional",
\t"serial_prefix": "ZERP-PAYPRO",
\t"description": "The complete payroll certification: salary structures and components, Nigerian statutory deductions and compliance, the payroll run as ritual, payslips and confidentiality, variable pay, increments and pay governance, exits and full-and-final, and the advanced payroll layer — proctored examinations from the first structure to the function that survives its people.",
}


def _data():
\tpath = os.path.join(os.path.dirname(__file__), "academy_payroll_pro_data.json")
\twith open(path) as f:
\t\treturn json.load(f)


def seed_payroll_pro_track():
\tdata = _data()
\tif not frappe.db.exists("Duty Product", "ZhiftERP Payroll"):
\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP Payroll", "active": 1, "sort_order": 10}).insert(
\t\t\tignore_permissions=True
\t\t)
\t\tprint("created Duty Product: ZhiftERP Payroll")

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
\t\t\t\t"product": "ZhiftERP Payroll",
\t\t\t\t"description": m["desc"],
\t\t\t\t"active": 1,
\t\t\t\t"audience": "Both",
\t\t\t\t"sort_order": 110 + i,
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
\t\t\t\t"product": "ZhiftERP Payroll",
\t\t\t\t"audience": "Consultant",
\t\t\t\t"serial_prefix": TRACK["serial_prefix"],
\t\t\t\t"description": TRACK["description"],
\t\t\t\t"active": 1,
\t\t\t\t"modules": [{"module": module_names[k]} for k in ORDER],
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tprint(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

\tfrappe.db.commit()
\tprint("ZhiftERP Payroll Professional track ready.")


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
L("Chapter 1 — Payroll: the organ between", "13", "<p>Welcome to the sixth certification — and the one two tracks deliberately deferred. The HR track drew its boundary in its first chapter (<i>HR owns the inputs payroll consumes</i>); the Accounts track carried only payroll's journal and its tax custody. This track is the organ BETWEEN: <b>payroll</b> — the function that consumes the people facts, computes the pay, holds the state's money in passing, and writes the largest recurring entry in most trading firms' books.</p><p><b>The two boundaries, now seen from inside.</b> Payroll's position defines its discipline: UPSTREAM, it receives the HR track's packages (the attendance close's days and categories, the leave interface's treatments, the movement notifications with effective dates, the joiner and separation packages — module by module, the HR track built payroll's supplier network, and this track is the customer whose specifications those handoffs met); DOWNSTREAM, it delivers to finance (the payroll journal into the ledger — Accounts 2's lawful catalogue receiving its biggest monthly resident; the statutory custody accounts — Accounts 5's machinery receiving PAYE and pension in passing; the bank payment run — Accounts 3's separations governing the money's actual movement) and to the WORKFORCE (the salaries themselves, and the payslips that account for them — module 4). A function with this many counterparties runs on interfaces or it runs on apologies — the HR track's closing law (<i>interfaces over blur</i>), now taught from the middle of the sandwich.</p><p><b>The precision stakes.</b> Why payroll's error tolerance is the firm's lowest, taught before any machinery: a stock error costs money; a salary error costs money AND trust, at a ratio no other function faces — the underpaid worker's family felt the shortfall at the market before the correction posted (the error is personal, immediate, and remembered), the overpaid worker's clawback is a grievance regardless of the error's honesty, and the workforce recalibrates its trust in EVERY firm system by whether the pay lands right (the firm whose payroll is exact earns patience for every other imperfection; the one whose payroll wobbles is distrusted on things it does perfectly). Add the state's stakes — the statutory deductions held in custody (module 2), where error compounds into penalty — and the function's character emerges: payroll is the discipline where 'approximately right' does not exist, which is why this track's laws will be the academy's strictest.</p><p><b>The trilogy completed.</b> The scope, stated: this track covers the salary structures (this module), the Nigerian statutory layer at full depth (module 2 — the track's ten-chapter deep module, sibling to the tax module it extends), the run itself (module 3), the payslip and its confidentiality (module 4), variable pay (module 5), the review machinery (module 6), exits and special cases (module 7), and the structural layer (module 8). What stays at the boundaries it honours: the PEOPLE decisions (who is hired, promoted, disciplined — the HR track's terrain, consumed here as effective-dated facts), the LEDGER's wider life (the accounts beyond payroll's entries — the Accounts track's terrain, fed here), and the tax POSITIONS where law is unclear (the adviser's terrain, in the settled grammar of both prior tracks). The consultant completing this track holds all three organs — the people, the pay, and the books — and the joins between them, which is the full anatomy of how a Nigerian trading firm keeps its people paid, legal, and accounted.</p>"),
L("Chapter 2 — Pay in structure: the vocabulary & the philosophy", "13", "<p>Before components and formulas, the vocabulary that every offer conversation, statutory computation, and payslip dispute turns on — and the design philosophy that makes pay a STRUCTURE rather than a pile of negotiations. The foundations chapter.</p><p><b>The three numbers.</b> Every compensation conversation involves three figures that Nigerian practice constantly conflates, and the consultant untangles them on day one: <b>GROSS</b> — the earnings before deductions (the sum of the salary components — the number the structure defines and module 2's computations mostly reference); <b>NET</b> — what lands in the account (gross minus the employee's deductions: the statutory shares, the governed recoveries — the number the WORKER means when they say 'my salary', which is why Chapter 6's net-preview discipline exists: the offer stated in gross to a candidate thinking in net is the misunderstanding that sours week four's payday); and the <b>EMPLOYER'S TOTAL COST</b> — gross plus the employer's own statutory contributions (the pension employer share, the levies of module 2 — the number the OWNER should budget with, and rarely does until shown: the ₦250k gross hire costs meaningfully more than ₦250k, and the budget that ignores the employer layer discovers it in module 2's remittance season). Three numbers, three audiences, one structure computing all of them — the vocabulary is the first deliverable.</p><p><b>Pay as structure: the design philosophy.</b> The thesis this module builds toward its law: compensation in a governed firm is COMPUTED from structure — the component definitions (Chapter 3), the salary structures per grade (Chapter 4), the person's assignment (Chapter 5) — not NEGOTIATED from memory (the per-person arrangement recalled by the founder, adjusted by mood, discovered at dispute). The structure's dividends, enumerated: CONSISTENCY (same grade, same structure — the pay-disparity time bomb of HR 2's offer chapter, defused at its source), COMPUTABILITY (the statutory layer computes from component definitions — module 2 is only possible because Chapter 3's flags exist), EXPLAINABILITY (every payslip line traceable to a structure line — module 4's query-killing transparency), and CHANGEABILITY (the review that moves a band moves everyone on it — module 6's machinery, impossible against 27 private arrangements). The philosophy's honest cost, stated too: structure constrains improvisation — which is the point, and the owner who wants to 'just add something for Tunde this month' will meet Chapter 7's governance and module 5's channels, because the something-for-Tunde that bypasses structure is the favour disease (the HR track's oldest villain) wearing a bank transfer.</p><p><b>The component conventions.</b> The Nigerian structural reality previewed for Chapter 3: pay here is conventionally STRUCTURED into named components — basic, housing, transport, and the allowances beyond — a convention with teeth, because statutory computations and common practice reference the components (the pension contribution's base is conventionally basic-plus-housing-plus-transport; benefit conventions and some computations key off basic) — so component design is not cosmetic labelling: the SPLIT chosen (what share of gross sits in basic) has downstream consequences the accountant and adviser weigh, and the consultant's job is the machinery that makes whatever split the professionals choose compute correctly, evenly, forever. The chapter closes where the module's law will: the structure is the single source of pay truth — everything else in this track is machinery for defining it, computing from it, governing it, and explaining it.</p>"),
L("Chapter 3 — Salary components: the anatomy", "14", "<p>The atoms of pay: the SALARY COMPONENTS — defined once, flagged precisely, reused everywhere. The component chapter, where module 2's computability is won or lost.</p><p><b>Earnings components.</b> The additions, defined as masters: <b>basic</b> (the anchor component — the conventions that reference it make its share a design decision, not a default), <b>housing</b> and <b>transport</b> (the classic Nigerian trio completed — together with basic forming the conventional base for the pension computation module 2 details), the further allowances the firm's structure uses (meal, utility, and the like — named per the firm's policy, resisted per the sprawl warning below), and the VARIABLE earnings that module 5 governs (overtime, bonus, commission — defined here as components with their flags, populated there by their documents). Each earnings component carries its flags: taxability (feeding module 2's PAYE base), statutory-base membership (in or out of the pension base — the flag the computation reads), and the formula-versus-amount nature below.</p><p><b>Deduction components.</b> The subtractions, in their two families: the STATUTORY deductions (employee PAYE, the employee pension share, NHF where applicable — module 2's whole terrain, defined here as components whose formulas the statutory chapter will fill), and the GOVERNED recoveries (the loan repayment, the salary-advance recovery, the documented deduction of HR 7's separation package — each a component that posts only from its authorising document, never from a typed number: module 5 holds their governance, and the improvised-deduction conviction of two prior tracks holds here hardest of all, because THIS is the layer where improvised deductions actually execute).</p><p><b>Formula versus amount.</b> The component's computational nature: AMOUNT components (the fixed figure the structure states — basic as a stated sum), FORMULA components (computed from others — housing as a percentage of basic, the pension share as its statutory rate on its statutory base, PAYE as module 2's full computation), and the design discipline that keeps structures maintainable: formulas reference NAMED bases (the pension formula reads the flagged base, not a hardcoded sum of three components — so the structure that adds a component to the base changes one flag, not five formulas), the precedence is explicit (components computing from components compute in order — the circular formula is the structure that cannot run), and the formulas live in the STRUCTURE layer, not scattered per person (Chapter 4's whole argument).</p><p><b>Component governance: the sprawl warning.</b> The master-data laws, sixth appearance, with this layer's specific disease named: COMPONENT SPRAWL — the allowance invented per negotiation ('special duty allowance' for one hire, 'transition allowance' for another) until the component list is a museum of old deals, every statutory flag a per-component audit, and every payslip a glossary. The fixes are the familiar ones: components created by the narrowest pen (Chapter 7), named from a governed list, justified by policy (a component exists because a CLASS of pay exists, not because a negotiation happened — the one-off lands in module 5's additional-pay machinery with its document, not in the component list), flagged at creation with the accountant's confirmation (the taxability flag set wrong on day one mis-computes every person, every month, until found — the component review is module 2's pre-season ritual for exactly this reason), and audited annually beside the structures (the component nobody's structure uses is retired, not kept 'just in case'). The chapter's one-liner for the implementation file: <b>few components, precisely flagged, formula-driven — the payroll that is easy to explain is the payroll that was designed this way.</b></p>"),
L("Chapter 4 — The salary structure: the master", "13", "<p>The components assemble into the layer's central master: the SALARY STRUCTURE — the named template of components and formulas that defines what a class of employees earns. The structure chapter.</p><p><b>The structure as template.</b> One structure per pay CLASS — in a graded firm, per grade (HR 1's band architecture receiving its payroll payload: the grade that carried leave entitlements and offer bands now carries its salary structure), with the structure holding the component set (which earnings, which deductions), the formulas and amounts (or the amount SLOTS the assignment fills — the structure defining housing as 25% of basic while the assignment states the person's basic), and the effective machinery (structures versioned by date — the review that changes a structure creates the new version from its effective date, the old preserved: module 6 consumes this, and the frozen-history conviction of five tracks lands in payroll as the rule that a past month's structure is as sealed as its ledger).</p><p><b>The design conversation.</b> Structures designed WITH the owner and accountant, from three inputs: the GRADE architecture (HR 1's bands — the structure count should roughly equal the grade count: the eleven-person firm with three grades runs three structures, and Chapter 9 will convict the 27-structures-for-27-people anti-pattern as the spreadsheet payroll wearing a system), the COMPONENT conventions (Chapter 3's split decisions, made once here — the basic share, the base flags, with the professionals' input on their consequences), and the MARKET position (HR 2's labour-market conversation, now with its machinery: the band's range lives in the structure's assignment rules — the grade 2 structure serving basics from X to Y, placements within it governed by the offer and review disciplines). The design output is small and load-bearing: a page per structure, signed, dated — the compensation constitution, beside the settings walks of every track.</p><p><b>Amendments as events.</b> The structure's change discipline, in the academy's settled grammar: structure changes are EVENTS (the annual review's new version — module 6; the statutory change that moves a formula — module 2's reform landscape landing here; the component added to a class), effective-DATED (computing forward from their date, never silently rewriting the past — the March that was computed stays computed: the attendance close's one-version law, now at the structure layer), ANNOUNCED (the pay change nobody explained is module 4's query storm pre-ordered), and made by the narrowest pen (Chapter 7). The anti-pattern buried here by name: the quiet mid-year tweak — the formula nudged in place, no version, no date, no announcement — which makes every payslip before and after the tweak inconsistent with one of them, and converts the next dispute from a lookup into an archaeology.</p><p><b>What the structure buys, summarised.</b> The template's dividends, collected for the sales conversation every consultant will have: the new hire priced in minutes (the offer from the band, the assignment from the structure — HR 2's discipline now with its engine), the review executed in hours (the version that moves a class — module 6), the statutory change absorbed in one edit (the formula updated once, every person on the structure correct next run — module 2's reform resilience), and the audit answered by pointing (WHY is this person paid this? — the structure, the assignment, the dates: three documents, no recollections). The structure is to pay what the chart was to accounts — the language, designed once, spoken everywhere — and the next chapter connects it to the people who earn from it.</p>"),
L("Chapter 5 — The assignment: person meets structure", "13", "<p>The structure defines the class; the ASSIGNMENT connects the person — the effective-dated record that says which structure, from when, with which amounts. The joining chapter.</p><p><b>The assignment's anatomy.</b> Per employee: the STRUCTURE assigned (from their grade — the alignment that should be automatic and is audited because it drifts), the BASE amounts the structure's slots require (the person's basic, from which the formulas cascade — the one number the offer actually negotiated, landing in the one place it belongs), and the EFFECTIVE DATE (from which this assignment computes — the field the whole run reads, and the field every event of module 6 and HR 7 writes: the increment's date, the promotion's date, the structure version's date). The assignment is a DOCUMENT (created by the events that own it — the joiner package's onboarding, the review's increment, the promotion's re-pricing — never a quiet edit), and its history is the person's pay story: the assignments in sequence, each with its authorising event, is the answer to every 'since when' dispute the function will ever host.</p><p><b>The offer link: HR 2's discipline lands.</b> The joining of the two tracks, made explicit: the offer from the grade's band (HR 2's law) becomes the assignment at onboarding (the joiner package carrying the agreed basic and the start date — the boundary's cleanest crossing when the offer was structural, and its messiest when it wasn't: the improvised offer arrives at payroll as a number with no structure to live in, and the consultant meets the resulting per-person 'structures' in every cleanup engagement). The proration reality at the edges: the mid-month joiner's first pay computed by the firm's stated day-count convention (calendar days or working days — a POLICY, chosen once, applied evenly, printed in the policy page, because the proration argued per case is the fairness leak module 7 will meet again at exits), and the convention's mirror applying to every mid-month event (the increment effective mid-month, the leaver's final days — one convention, every edge).</p><p><b>The no-structure employee.</b> The error state named and fenced: the active employee with no current assignment is a run-time failure waiting for month-end (the run either skips them — the missed salary — or someone types a number — the improvisation this track exists to end), and the fence is structural: the joiner checklist's assignment line (HR 2's day-one readiness including the pay machinery), the pre-run validation that lists the unassigned (module 3's run discipline), and the monthly read that should always be empty. Its sibling error, equally fenced: the DOUBLE assignment (overlapping effective ranges — two answers to one month's question), refused by validation and resolved by dating discipline.</p><p><b>Currency, precision & the small print.</b> The layer's technical hygiene, briefly and completely: amounts in the payroll currency at the ledger's precision (the precision mismatch that manufactures kobo residue at the payroll journal is Accounts 8's conviction arriving home), rounding rules stated per the firm's convention (the net rounded where practice rounds it, the difference carried to its component, never dropped — the kobo that vanishes monthly across 27 people is small money and large sloppiness), and annualisation conventions explicit (the annual package quoted at twelve months of gross unless the firm's terms say otherwise — the thirteenth-month arrangement, where the firm offers one, being module 5's governed variable pay, not a quiet convention). Small print, written down — because payroll's disputes live in exactly these crevices, and the policy page that pre-answers them is the function's quietest time-saver.</p>"),
L("Chapter 6 — The gross-to-net walk & the modeling discipline", "14", "<p>The chapter that makes the structure REAL: one worked example, gross to net, every stop narrated — and the modeling discipline that puts this walk at the offer desk, where it prevents the most common compensation dispute in the trade. The arithmetic chapter.</p><p><b>The worked example: ₦250,000 gross.</b> A grade 2 employee on the case-study structure — basic ₦125,000 (50%), housing ₦62,500 (25%), transport ₦37,500 (15%), utility allowance ₦25,000 (10%) — walked to net: <b>Step 1, the statutory base</b> — the pension base per the convention (basic + housing + transport = ₦225,000), flagged in Chapter 3's machinery, summed by the formula, not by hand. <b>Step 2, the employee statutory shares</b> — the employee pension contribution at its statutory rate (8% of the base = ₦18,000 — module 2 holds the law's detail; this chapter holds the flow), and PAYE per the current regime's computation on the taxable income after allowable deductions (the pension contribution reducing the taxable base before the bands apply — the interaction the spreadsheet payroll most often gets wrong, and the reason module 2 is this track's deep module: for this walk, the computed PAYE lands, illustratively, near ₦14,000 monthly under the reformed regime's bands for this income — the EXACT figure is module 2's terrain and the configuration's output, never a memorised number). <b>Step 3, net</b> — gross ₦250,000 minus ₦18,000 pension minus ~₦14,000 PAYE = <b>≈ ₦218,000 to the account</b>. <b>Step 4, the employer's total cost</b> — gross PLUS the employer pension share (10% of the base = ₦22,500) plus the levies module 2 details: the ₦250k hire costs the firm ₦272,500+ monthly — the third number, delivered to the owner with the walk.</p><p><b>The walk's teaching uses.</b> The example is machinery, not decoration: it is the CONFIGURATION TEST (the consultant runs this exact walk against the configured structure at implementation — the computed slip matching the hand walk to the naira is the go-live gate for the payroll layer: Accounts 1's posting-map verification, payroll edition), the TRAINING artifact (the payroll seat that can narrate this walk can answer module 4's queries; the one that cannot is operating a black box), and the DISPUTE settler (the payslip challenged is walked, line by line, against the structure — the drill-down culture of six tracks, at the payslip).</p><p><b>The modeling discipline: net at the offer desk.</b> The chapter's operational payoff: <b>candidates think in net</b> — the offer stated as gross to a candidate budgeting in take-home is the misunderstanding that surfaces at the first payday as a grievance wearing a calculator — and the discipline is the net PREVIEW at the offer stage: the offer conversation equipped with the modeled slip (this gross, on this structure, yields this net — the modeling run the system makes trivial and the spreadsheet made heroic), the acceptance informed (HR 2's offer discipline gaining its missing number), and the same modeling serving the REVIEW conversations (module 6 — the increment's net effect shown, because the ₦20k gross increase that yields ₦14k net is a conversation better had with the number on the table) and the owner's budget (the employer-cost model per planned hire — HR 2's multi-million-naira-decision framing, now with its calculator).</p><p><b>The annualisation note.</b> The walk's yearly shadow, closing the chapter: the statutory computations are ANNUAL creatures computed monthly (module 2's mechanics — the PAYE bands are annual bands, the reliefs annual reliefs, the monthly computation an instalment of a yearly truth), which is why mid-year changes ripple (the increment that moves the annual projection adjusts the remaining months' instalments) and why the year-end true-up disciplines exist (module 2's terrain). For this module, the takeaway is the frame: every monthly slip is one-twelfth of an annual story the statutory layer is keeping — and the consultant who holds that frame configures and explains; the one who doesn't debugs mysteries every January.</p>"),
L("Chapter 7 — Governing the pay masters", "13", "<p>The layer's governance: who may touch the structures, components, and assignments — the narrowest pen in the firm — and the disciplines that keep the compensation constitution from eroding one favour at a time. The governance chapter.</p><p><b>The narrowest pen.</b> The edit rights, tiered to the stakes: COMPONENTS and their flags (the atoms whose mis-flag mis-computes everyone — edited by the configure authority alone, with the accountant's sign-off on statutory flags: module 8 will seat this in the four-authorities pattern, but the rule lands now), STRUCTURES and their versions (the class-level truth — the same door, changed only by the events module 6 and module 2 define), and ASSIGNMENTS (the person-level connection — written by their owning events through the standing flows: the joiner package, the increment, the promotion, the separation — with the DIRECT edit right held by almost no one, because the assignment edited outside an event is precisely the negotiated-from-memory pay this track's first law forbids). The tiering's logic is blast radius: the component wounds everyone, the structure wounds a class, the assignment wounds a person — and the pen narrows as the radius widens.</p><p><b>The quiet-edit refusal.</b> The disease this governance exists to refuse, named in its native habitat: the owner's <i>just adjust Tunde's basic this month</i> — the request every payroll seat receives, monthly, forever — met not with a lecture but with the CHANNELS: the one-off payment belongs in module 5's additional-pay machinery (documented, approved, visible on the slip as what it is), the permanent change belongs in module 6's review or HR 7's movement events (effective-dated, authorised, joined), and the direct edit belongs nowhere — because the quiet adjustment is invisible to the review (module 6 prices a band the private deals have already left), inconsistent at dispute (the payslip that matches no structure defends no one), and contagious (the first quiet favour recruits the second — the HR track's evenness law, at the layer where unevenness is denominated in naira). The consultant's gift to the payroll seat is exactly this paragraph, laminated: the channels exist so that saying yes is always possible and saying yes QUIETLY never is.</p><p><b>The audit trail & the reconciliation habit.</b> The layer's self-evidence: every structure version, component change, and assignment carrying its who-when-why (the versioning machinery plus the change log — the pay story readable end to end), the quarterly STRUCTURE-TO-REALITY read (every active employee's assignment against their grade — the drift audit: the grade 3 person on a grade 2 structure is either an error or an undocumented decision, and both need surfacing), and the component review before each statutory season (module 2's pre-season ritual — the flags re-confirmed against the current law with the adviser, because the reform that moved a base definition moves a flag, and the flag moves everyone).</p><p><b>The confidentiality overlay.</b> The governance's custody dimension, previewed for module 4's full treatment: the pay masters sit in the SENSITIVE tier of the HR track's permission design — the structures arguably readable more widely (the published band is HR 2's transparency choice, made deliberately), the ASSIGNMENTS emphatically not (the person's actual pay visible to the payroll function, the approver chain, and the person — and no one else by default: the compensation leak is the trade's fastest culture poison, and module 4 will treat the whole custody discipline). For this chapter, the governance conclusion: the pay masters are the firm's most consequential small dataset — a few structures, a few dozen assignments — governed by the narrowest pens, changed only by events, evidenced by trail, and fenced by the tightest tier. Small data, maximal governance: the inverse of every other layer's scale, and exactly right.</p>"),
L("Chapter 8 — Case study: HealthTrade's structures are born", "16", "<p>The pay machinery, installed where five tracks prepared its ground. Every chapter clocks in.</p><p><b>The design sessions (Ch. 2-4).</b> The compensation constitution built in two sittings with the MD and the accountant: the component set defined ONCE — the classic trio plus one utility allowance, statutory flags set with the accountant's sign-off (the pension base flagged as basic+housing+transport; taxability confirmed per component), and the sprawl fence agreed (new components by policy only — the 'special duty allowance' one early negotiation had invented is retired into the utility component with its holder's consent and a documented step-up: the museum's first exhibit, closed). THREE structures for three grades — not twenty-seven for twenty-seven (the spreadsheet era's per-person tabs formally convicted at the whiteboard) — each a page: component shares, formula bases, the band's assignment range, signed and dated. The vocabulary lands in the same sitting: the MD sees the three numbers for a grade 2 hire — ₦250k gross, ≈₦218k net, ₦272.5k+ employer cost — and the budget conversation audibly changes (<i>I have been budgeting gross for eleven years</i>).</p><p><b>The load (Ch. 5).</b> Twenty-seven assignments, effective-dated, each from its document: the existing contracts mapped to their grade structures (twenty-four land cleanly in-band), and the three exceptions surfaced honestly — two legacy arrangements above band (documented as red-circled personal-to-holder terms with the adviser's shape: honoured, dated, and closed to inheritance) and one BELOW band (a quiet historic unfairness the structure exposes in an afternoon — corrected at the next run, effective-dated, with the back-conversation the MD chooses to have: the structure's first justice, delivered by architecture). The no-structure read runs empty; the double-assignment validation catches one overlapping date from the load and the dating is fixed the same hour.</p><p><b>The walk as the gate (Ch. 6).</b> The configuration test: the ₦250k walk run by hand on the whiteboard, then computed by the configured structure — the two slips matching to the naira on the second attempt (the first attempt catches a utility-allowance taxability flag set wrong: the mis-flag that would have mis-computed ten people monthly, found by the walk exactly as the chapter promised — the go-live gate doing its one job). The modeling discipline installs at the offer desk the same week: the next hire's offer conversation includes the modeled net slip, and the candidate's acceptance email says so (<i>first offer I've received that told me my take-home</i> — the employer-brand dividend HR 2 predicted, arriving through payroll).</p><p><b>The governance tested (Ch. 7).</b> Month two delivers the inevitable: <i>just add thirty to Tunde's pay this month — he sorted the generator</i>. The channels answer: the one-off lands in the additional-pay machinery as a documented, approved, visible bonus line (module 5's machinery, previewed live — thirty seconds of process, the favour granted WITHOUT the quiet edit), and the payroll seat's note in the file is the chapter's thesis in the wild: <i>said yes through the channel; the structure never moved.</i> The quarterly drift read runs clean; the component review is calendared before the statutory season. The layer ends its first quarter with three structures, twenty-seven true assignments, a tested walk, one closed museum exhibit, one corrected unfairness, and a governance that has already survived its first favour — the foundation module 2's statutory depth will now compute upon.</p>"),
L("Chapter 9 — Common mistakes & the first law", "13", "<p>The pay-structure layer's scar tissue — the diseases every payroll cleanup begins with. Symptom → disease → fix.</p><p><b>Pattern 1 — the spreadsheet payroll.</b> Symptom: the monthly workbook, one tab per person or one row per arrangement; formulas nobody dares touch; the computation that lives in one head and one file. Disease: pay without masters (Ch. 1-2) — every month a fresh improvisation on last month's copy. Fix: the migration engagement — components defined, structures built per grade, assignments loaded from documents, the walk as the gate — and the workbook retired to read-only history beside HR 1's staff spreadsheet.</p><p><b>Pattern 2 — negotiated-from-memory pay.</b> Symptom: 'his arrangement is different'; amounts recalled, not recorded; the dispute settled by whoever remembers loudest. Disease: the founder's memory as the pay master (Ch. 2, 7). Fix: every arrangement surfaced into an assignment with its document, the exceptions red-circled honestly, and the memory retired — the structure answering 'since when and why' by pointing.</p><p><b>Pattern 3 — the per-person structure.</b> Symptom: twenty-seven structures for twenty-seven people; every review twenty-seven edits; the 'structure' layer as the spreadsheet wearing a doctype. Disease: the template's point missed (Ch. 4) — class machinery used as person storage. Fix: structures per grade, amounts in assignments, the band's range doing the individual work — the structure count collapsing to the grade count.</p><p><b>Pattern 4 — the mis-flagged component.</b> Symptom: PAYE persistently 'a bit off'; the pension base disputed at remittance; the year-end true-up that surprises. Disease: the flag set wrong at birth, computing wrong for everyone since (Ch. 3). Fix: flags set with the accountant at creation, the walk as the configuration gate, the pre-season component review — one flag, checked, versus twelve months of quiet error.</p><p><b>Pattern 5 — the quiet edit.</b> Symptom: payslips matching no structure; the review pricing a band the private deals have left; the favour that recruited its successors. Disease: the pen too wide and the channels unknown (Ch. 7). Fix: the narrowest pen tiered by blast radius, the channels laminated (one-offs to additional pay, permanence to events), and the drift read quarterly — saying yes always possible, saying yes quietly never.</p><p><b>Pattern 6 — gross confusion.</b> Symptom: the payday grievance in week four ('this is not what we agreed'); the owner's budget missing the employer layer; three numbers used interchangeably in every conversation. Disease: the vocabulary never taught (Ch. 2, 6). Fix: the three numbers in every offer and review conversation, the net preview at the offer desk, the employer-cost model in the owner's budget — one walk, three audiences, zero surprises.</p><p><b>The first law.</b> The sixth track opens where five tracks' grammar demands: <b>pay is computed from structure, not negotiated from memory — few components precisely flagged, structures per grade versioned by date, assignments written only by their owning events, the gross-to-net walk as the gate and the teacher, and every favour granted through a channel that leaves the structure standing.</b> The structure is pay's single source of truth: consistent by design, computable by flags, explainable by pointing, and changeable by class. Seven modules stand on it — and module 2 now takes the walk's hardest steps at full depth: the statutory layer, where the state rides every payslip and the reformed law sets the bands.</p>"),
]

QUESTIONS = [
Q("Payroll's position is:", ["Standalone", "The organ between — HR feeds it people facts, finance receives its entries, the workforce receives its output", "Part of HR", "Part of accounts"], 1, "A function with this many counterparties runs on interfaces or apologies.", "Ch1"),
Q("A salary error costs:", ["Money only", "Money AND trust at a ratio no other function faces — the workforce calibrates every system by whether pay lands right", "Nothing lasting", "Only penalties"], 1, "Payroll is the discipline where 'approximately right' does not exist.", "Ch1"),
Q("The three numbers are:", ["Basic, housing, transport", "Gross, net, and the employer's total cost — three audiences, one structure computing all", "Monthly, annual, daily", "Min, mid, max"], 1, "The candidate thinks in net; the owner should budget employer cost.", "Ch2"),
Q("The ₦250k gross hire costs the firm:", ["₦250k", "Meaningfully more — gross plus the employer pension share and levies: ₦272,500+ in the walk", "Less after tax", "₦218k"], 1, "The budget that ignores the employer layer discovers it at remittance season.", "Ch2, Ch6"),
Q("Component conventions have teeth because:", ["Names matter aesthetically", "Statutory computations reference them — the pension base is conventionally basic+housing+transport", "Payslips need labels", "Tradition"], 1, "The split chosen has downstream consequences the professionals weigh.", "Ch2"),
Q("Structure constrains improvisation:", ["As a flaw", "As the point — the something-for-Tunde that bypasses structure is the favour disease wearing a bank transfer", "Temporarily", "Rarely"], 1, "The channels exist so yes is possible and quiet yes is not.", "Ch2, Ch7"),
Q("Formulas reference:", ["Hardcoded sums", "NAMED bases — adding a component to the base changes one flag, not five formulas", "Last month", "Nothing"], 1, "The maintainability discipline.", "Ch3"),
Q("Governed recoveries post from:", ["Typed numbers", "Their authorising documents — never improvised at the layer where improvised deductions actually execute", "Memory", "Requests"], 1, "The conviction of two prior tracks, held hardest here.", "Ch3"),
Q("Component sprawl is:", ["Flexibility", "The allowance invented per negotiation until the list is a museum of old deals", "Necessary", "Harmless"], 1, "A component exists because a CLASS of pay exists.", "Ch3"),
Q("A mis-set taxability flag:", ["Affects one slip", "Mis-computes every person on it, every month, until found", "Self-corrects", "Is cosmetic"], 1, "The pre-season component review exists for exactly this.", "Ch3"),
Q("The structure count should roughly equal:", ["The headcount", "The grade count — three grades, three structures; not twenty-seven for twenty-seven", "The branch count", "One"], 1, "Per-person structures are the spreadsheet wearing a doctype.", "Ch4"),
Q("A past month's structure is:", ["Editable", "As sealed as its ledger — versions compute forward from their dates", "A draft", "Irrelevant"], 1, "The frozen-history conviction lands in payroll.", "Ch4"),
Q("The quiet mid-year formula tweak:", ["Saves a version", "Makes every payslip before or after inconsistent with one of them — disputes become archaeology", "Is efficient", "Is standard"], 1, "Amendments are events: dated, versioned, announced.", "Ch4"),
Q("The structure buys:", ["Complexity", "Hires priced in minutes, reviews in hours, statutory changes in one edit, audits answered by pointing", "Rigidity only", "Nothing"], 1, "The structure is to pay what the chart was to accounts.", "Ch4"),
Q("The assignment's one negotiated number is:", ["The net", "The person's basic, landing in the one place it belongs — the formulas cascade from it", "The tax", "The date"], 1, "The offer's output, structurally housed.", "Ch5"),
Q("An assignment history is:", ["Clutter", "The person's pay story — each assignment with its authorising event answers every 'since when'", "Optional", "Private only"], 1, "Written by events: the joiner package, the increment, the promotion.", "Ch5"),
Q("Proration conventions are:", ["Argued per case", "A policy chosen once and applied to every edge — joiners, increments, leavers alike", "The manager's call", "Unnecessary"], 1, "The fairness leak, fenced at the policy page.", "Ch5"),
Q("The no-structure active employee is:", ["Fine", "A run-time failure waiting for month-end — fenced by the joiner checklist and pre-run validation", "Normal briefly", "Payroll's choice"], 1, "The monthly read that should always be empty.", "Ch5"),
Q("In the worked example, the pension base is:", ["The full gross", "₦225,000 — basic + housing + transport, summed by the flag, not by hand", "Basic only", "Net"], 1, "The convention, mechanised.", "Ch6"),
Q("The pension contribution's PAYE interaction is:", ["None", "It reduces the taxable base before the bands apply — the interaction spreadsheets most often get wrong", "It adds to tax", "Annual only"], 1, "The reason module 2 is the deep module.", "Ch6"),
Q("The walk's first use is:", ["Decoration", "The configuration test — the computed slip matching the hand walk to the naira is the go-live gate", "Marketing", "Training only"], 1, "The posting-map verification, payroll edition.", "Ch6"),
Q("Candidates think in:", ["Gross", "Net — the offer without a net preview surfaces at the first payday as a grievance wearing a calculator", "Annual figures", "Employer cost"], 1, "The modeling discipline at the offer desk.", "Ch6"),
Q("Statutory computations are:", ["Monthly creatures", "Annual creatures computed monthly — every slip one-twelfth of a yearly story", "Weekly", "One-off"], 1, "Why mid-year changes ripple and January debugs mysteries.", "Ch6"),
Q("The pen narrows as:", ["Seniority rises", "The blast radius widens — components wound everyone, structures a class, assignments a person", "Time passes", "Firms grow"], 1, "The tiered edit rights' logic.", "Ch7"),
Q("The assignment edited outside an event is:", ["Efficient", "Precisely the negotiated-from-memory pay the first law forbids", "Rare", "Reversible"], 1, "Direct edit rights held by almost no one.", "Ch7"),
Q("'Just adjust Tunde's basic this month' is answered by:", ["Refusal", "The channels — one-offs to additional pay, permanence to events; yes without the quiet edit", "The edit", "Escalation"], 1, "The paragraph the consultant laminates for the payroll seat.", "Ch7"),
Q("The quiet favour is contagious because:", ["It isn't", "The first recruits the second — unevenness at the layer where it is denominated in naira", "People forget", "It's visible"], 1, "The evenness law, at its most expensive address.", "Ch7"),
Q("The pay masters are:", ["Big data, light governance", "Small data, maximal governance — a few structures and dozens of assignments, narrowest pens, tightest tier", "Public", "Ungoverned"], 1, "The inverse of every other layer's scale, and exactly right.", "Ch7"),
Q("HealthTrade's structure count landed at:", ["Twenty-seven", "Three, for three grades — the per-person tabs formally convicted at the whiteboard", "One", "Ten"], 1, "The spreadsheet era closed.", "Ch8"),
Q("The load's below-band discovery was:", ["Ignored", "A historic unfairness exposed in an afternoon and corrected at the next run — the structure's first justice", "Red-circled", "Disputed"], 1, "Delivered by architecture.", "Ch8"),
Q("The walk's first attempt caught:", ["Nothing", "A utility-allowance taxability flag set wrong — the mis-flag that would have mis-computed ten people monthly", "A formula typo", "A rounding error"], 1, "The go-live gate doing its one job.", "Ch8"),
Q("The generator favour was granted:", ["By quiet edit", "Through the additional-pay channel — documented, approved, visible; 'the structure never moved'", "In cash", "Not at all"], 1, "Thirty seconds of process; the governance surviving its first favour.", "Ch8"),
Q("Red-circled arrangements are:", ["Deleted", "Honoured, documented as personal-to-holder, dated, and closed to inheritance", "Extended to peers", "Secret"], 1, "The exceptions surfaced honestly, with the adviser's shape.", "Ch8"),
Q("The spreadsheet payroll's fix is:", ["Better formulas", "The migration — components, structures per grade, assignments from documents, the walk as gate, the workbook retired", "A newer workbook", "More tabs"], 1, "Beside HR 1's staff spreadsheet in read-only history.", "Ch9"),
Q("This module's law is:", ["Pay is negotiated", "Pay is computed from structure, not negotiated from memory — flagged components, graded structures, event-written assignments, the walk as gate, favours through channels", "Nets are approximate", "Structures are optional"], 1, "The single source of pay truth.", "Ch9"),
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
    if '"3.128.0"' not in init:
        sys.exit("ABORT: not at v3.128.0.")

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
    print(f"Payroll 1: 9 chapters ({total:,} chars, min {min(len(l['html']) for l in LESSONS):,}), bank {len(bank)}, spread {dist}")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data = {
        "payroll_function": {
            "title": "Payroll 1 — The Payroll Function & Salary Structures",
            "desc": "The foundation of the payroll certification: payroll as the organ between HR and finance, the three numbers and pay-as-structure philosophy, salary components with their statutory flags, the salary structure per grade, effective-dated assignments, the gross-to-net walk with the modeling discipline, and the governance of the pay masters.",
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
        f.write(init.replace('"3.128.0"', '"3.129.0"'))
    print("  created: academy_payroll_pro_data.json (Payroll 1)")
    print("  created: academy_seed_payroll_pro.py (product, track ZERP-PAYPRO, refresh functions)")
    print("wrote __version__ -> 3.129.0")


if __name__ == "__main__":
    main()
