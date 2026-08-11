#!/usr/bin/env python3
"""Duty Board v3.121.0 — ZhiftERP HR track: infrastructure
+ HR 1: The Employee Master & Organisational Structure (pass 1 of 8).

Creates duty_board/academy_hr_pro_data.json and
duty_board/academy_seed_hr_pro.py (faithful mirror of the accounts
seeder: proctored modules, track-append idempotency,
refresh_lessons/refresh_questions). Payroll is deliberately excluded
from this track's scope. Module 1 ships at manual depth from birth:
9 chapters, 35-bank.

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one execute duty_board.academy_seed_hr_pro.seed_hr_pro_track

Anchored, idempotent. Requires v3.120.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_hr_pro_data.json"
SEEDER_PATH = "duty_board/academy_seed_hr_pro.py"
CHECK_ONLY = "--check" in sys.argv

L = lambda t, est, html: {"title": t, "est": est, "html": html}
Q = lambda q, opts, ans, why, src: {"q": q, "opts": opts, "ans": ans, "why": why, "src": src}

SEEDER = '''"""ZhiftERP HR Professional track seed — the people curriculum
(payroll excluded by scope).

Content lives in academy_hr_pro_data.json. Modules are PROCTORED:
timed 60s/question, 10 served from each 35-question bank. Modules are
added pass by pass; re-running the seed appends new modules to the
existing track (idempotent per module and for the track).

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed_hr_pro.seed_hr_pro_track
"""

import json
import os

import frappe

ORDER = ["employee_master"]

TRACK = {
\t"title": "ZhiftERP HR Professional",
\t"serial_prefix": "ZERP-HRPRO",
\t"description": "The complete people certification (payroll excluded): the employee master and organisational structure, recruitment and onboarding, attendance and shifts, leave management, performance and appraisals, training and development, lifecycle events and separation, and the advanced HR layer — proctored examinations from the person's record to the structure that holds a workforce.",
}


def _data():
\tpath = os.path.join(os.path.dirname(__file__), "academy_hr_pro_data.json")
\twith open(path) as f:
\t\treturn json.load(f)


def seed_hr_pro_track():
\tdata = _data()
\tif not frappe.db.exists("Duty Product", "ZhiftERP HR"):
\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP HR", "active": 1, "sort_order": 9}).insert(
\t\t\tignore_permissions=True
\t\t)
\t\tprint("created Duty Product: ZhiftERP HR")

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
\t\t\t\t"product": "ZhiftERP HR",
\t\t\t\t"description": m["desc"],
\t\t\t\t"active": 1,
\t\t\t\t"audience": "Both",
\t\t\t\t"sort_order": 100 + i,
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
\t\t\t\t"product": "ZhiftERP HR",
\t\t\t\t"audience": "Consultant",
\t\t\t\t"serial_prefix": TRACK["serial_prefix"],
\t\t\t\t"description": TRACK["description"],
\t\t\t\t"active": 1,
\t\t\t\t"modules": [{"module": module_names[k]} for k in ORDER],
\t\t\t}
\t\t).insert(ignore_permissions=True)
\t\tprint(f"created track: {TRACK['title']} ({TRACK['serial_prefix']}, {len(ORDER)} modules)")

\tfrappe.db.commit()
\tprint("ZhiftERP HR Professional track ready.")


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
L("Chapter 1 — The people layer: the fifth master", "13", "<p>Welcome to the fifth certification. Four tracks taught four masters — the customer, the supplier, the item, the account — and every one of them was operated BY people this academy kept naming without recording: the storekeeper whose custody Inventory 1 framed, the till operator whose sessions Accounts 3 reconciled, the approver whose two names every threshold demanded. This track records them: the <b>people layer</b> — the employee as the fifth master, and the machinery that manages a workforce from its first application to its last working day.</p><p><b>What HR-in-the-system buys.</b> The same purchase every master made, at its most personal: ONE RECORD per person (the employee master — this module), holding the whole lifecycle (hired, confirmed, promoted, transferred, developed, separated — modules 2-7 in order), operated by DOCUMENTS (the leave application, the appraisal, the transfer letter — each an auditable event, not a corridor conversation), read by RHYTHMS (the attendance reads, the leave planning, the appraisal cycles), and structured to survive its administrators (module 8's handover, because the HR-in-one-head disease is the founder-bottleneck's most personal organ). The firm whose people machinery runs on the system answers every people question — who works here, since when, on what terms, approved by whom, developed how — from one place; the firm whose HR lives in a folder and a memory answers none of them without archaeology, and pays for it precisely at the worst moments: the dispute, the audit, the departure.</p><p><b>The scope line, drawn deliberately.</b> This track EXCLUDES payroll — not because payroll is unimportant but because it is a different discipline with a different owner: the salary computation, the statutory custodies, the payment run belong to the finance function (the Accounts track's modules 2 and 5 already carry the payroll journal and the PAYE machinery), and the boundary between the two is itself curriculum: HR OWNS the inputs payroll consumes — who is employed (this module), who attended (module 3), who was on leave (module 4), who was promoted to what grade (module 7) — and the clean handoff of those inputs, on a calendar, is where the two functions mesh. A firm whose HR and payroll disagree about who worked in March has a boundary problem this track's disciplines prevent.</p><p><b>The tone this track carries.</b> One difference from every prior track, named at the door: the other masters were RECORDS OF THINGS — items, accounts, companies. This master is a record OF A PERSON, and that changes the governance's flavour throughout: the data is held in CUSTODY (confidentiality as a design requirement, not a courtesy — module 8 gives it structure), the documents affect livelihoods (the warning letter, the appraisal rating, the separation — each carrying procedural fairness as a discipline, module 7's core), and the system's job is to make the firm's dealings with its people CONSISTENT and EVIDENCED — which protects the honest employee exactly as the counting disciplines protected the honest custodian: the academy's oldest framing, now applied to the people it was always quietly about.</p>"),
L("Chapter 2 — The employee master: anatomy of the person's record", "14", "<p>The record itself, section by section — because every module ahead reads or writes some part of it, and the consultant must know exactly what lives where.</p><ul><li><b>Identity</b> — the person's names (as their legal documents state them — the record that will feed contracts, statutory filings, and certificates does not improvise spellings), the employee NUMBER (the naming-series law's fifth appearance: chosen once, never re-used — a departed employee's number is retired with them, because re-issued numbers merge two people's histories in every report forever), photograph, date of birth, gender, marital status.</li><li><b>Employment</b> — the fields the whole system reads: <b>date of joining</b> (the anchor of tenure, probation, leave accrual, and every service computation), employment TYPE (Chapter 4), STATUS (Active, on notice, Left — Chapter 4's discipline), the org placement (company, branch, department, designation, grade — Chapter 3), and <b>reports to</b> — the manager field, which Chapter 3 will crown as the approval spine.</li><li><b>Contacts &amp; emergency</b> — personal and company contact details, address, and the emergency contact whose absence is only ever discovered on the day it is needed: the field the annual verification (Chapter 6) checks first, because it is the one the firm hopes never to use and must never find stale.</li><li><b>Identifiers &amp; compliance</b> — the national and tax identifiers the Nigerian employment context requires (the tax identification the PAYE machinery will reference — held here, consumed by the payroll function across the boundary), bank details for that same handoff, and pension administrator details (the employee's chosen PFA — Accounts 5 met the remittance side; the CHOICE lives here).</li><li><b>Documents</b> — the attachment discipline: the offer and contract, the credentials as verified (Chapter's 6 verification note), the ID copies, and later the lifecycle's paper trail (confirmations, promotion letters, warnings — modules 2 and 7 file into this record). The employee master is the FILE — the paper folder's successor, complete or the folder quietly remains the real record (Chapter 9's pattern).</li><li><b>Dates that govern</b> — beyond joining: confirmation date (probation's end — module 2), contract end dates for fixed-term staff (Chapter 4 — an expiry the system must see coming), and the document-expiry family Chapter 6 tracks.</li></ul><p><b>The custody frame, operationalised.</b> This record holds a person's identity documents, bank details, family contacts, and — as the lifecycle accumulates — their disciplinary and performance history: data whose exposure harms a real person, held under a data-protection duty Nigerian law now articulates (the consultant's altitude: a registered duty of care over personal data exists, its details are the compliance professional's terrain, and the SYSTEM'S contribution is structural — the permission design of Chapter 5 and module 8 that makes <i>who can see what</i> a configuration, not a hope). The working rule taught from day one: employee data is read on NEED, not curiosity — and the system's role-based fences are how the rule survives staff turnover in HR itself.</p>"),
L("Chapter 3 — The organisational structure: trees, lists & the spine", "14", "<p>The employee record places its person INTO a structure, and the structure is this academy's favourite subject wearing its people clothes: trees and lists, designed from what must be read — plus one field that outranks them all.</p><p><b>The structural vocabulary.</b> <b>Company</b> — the legal employer (the multi-company frontier of Accounts 8: people are employed by legal persons, and the employee of the trading company is not the employee of the property company); <b>branch</b> — the location (the field that will align with the warehouse tree and cost centers — Chapter 7's join); <b>department</b> — the functional grouping (Operations, Sales, Finance, Admin — the tree that mirrors how work is actually organised); <b>designation</b> — the role's name (Storekeeper, Branch Manager, Accountant — a LIST, governed like every value list this academy has met: named owner, conventions, no duplicates-by-spelling); and <b>grade</b> — the level (the band structure that will carry benefit entitlements and leave policies — module 4 reads it — and, across the boundary, the payroll structure's key).</p><p><b>Designing the structure: the accountability law, again.</b> The design hour runs on the cost-center chapter's exact logic (Accounts 6), because it is the same design: departments mirror ACCOUNTABILITY (a department exists when someone owns it and its people are managed as a group — the eleven-person firm needs three or four, not nine), the tree stays SHALLOW (the two-level rule, fifth appearance), designations name real roles (the vanity org chart — Senior Executive Assistant Coordinator titles for an eleven-person firm — is chart sprawl's people edition, and it costs real money later when grades and policies attach to inflated titles), and the whole structure aligns with the cost-center tree it shadows (the department that is also a cost center reads its people and its money as one unit — the alignment Chapter 7 completes). The change discipline transfers whole: restructures are EVENTS (the department merged, the designations renamed — with the history's treatment decided deliberately), never casual edits.</p><p><b>The reporting spine.</b> The <b>reports-to</b> field — each employee's named manager — deserves its own section because it is the structure's living part: the trees say where people SIT; the spine says who ANSWERS FOR whom, and the system runs its workflows along it — the leave application routing to the applicant's manager (module 4), the appraisal conducted by the manager (module 5), the expense claim, the shift change, the resignation notice all riding the same field. The disciplines that keep the spine honest: EVERY active employee has a manager (the spine with gaps strands workflows — the leave request that routes nowhere), the spine is a TREE (no cycles, no self-reporting; the founder at the root), it is MAINTAINED at every lifecycle event (the promotion that moves a manager without re-pointing their reports breaks every workflow beneath them — module 7's transfer discipline), and it reflects REALITY (the spine that says A reports to B while everyone knows A reports to C routes every approval to the wrong desk — the org chart of record and the org chart of fact must be the same chart, which is a governance conversation before it is a data entry).</p><p><b>The structure's readers.</b> Why the design matters beyond tidiness: headcount reads by department and branch (module 8's analytics), leave and attendance policies attach by grade and branch (modules 3-4), approval chains ride the spine, and the payroll boundary consumes the grades — every downstream module reads this chapter's decisions, which is the definition of a master done right, and the reason the design hour happens at implementation with the owner in the room rather than being reverse-engineered from habits later.</p>"),
L("Chapter 4 — Employment types & the status discipline", "13", "<p>Two small fields govern more downstream behaviour than any others on the record: the employment TYPE and the STATUS. The taxonomy, and the discipline.</p><p><b>The types.</b> The working set for Nigerian trading firms: <b>full-time</b> (the permanent core), <b>part-time</b> (the retail reality — the weekend till staff, the market-day extras), <b>contract / fixed-term</b> (employed to a date — the type whose END DATE is a first-class field the system must see coming: the contract expiring unnoticed converts a deliberate arrangement into an accidental one, with legal implications the employment lawyer owns and the expiry-tracking machinery of Chapter 6 prevents), <b>intern / trainee</b> (the pipeline the academy's own onboarding curriculum serves — module 6's terrain), and the <b>casual</b> labour reality of warehouse peaks (engaged properly or not at all — the daily-paid loader who exists in no system is a liability wearing a wheelbarrow: unrecorded, uninsured, and unprovable in every direction). The type drives policy attachment (leave entitlements differ by type — module 4), benefits eligibility, and the statutory obligations the accountant confirms per type — which is why the type is set at CREATION from the offer's terms (module 2's handoff) and changed only as the lifecycle event it is (the intern confirmed to full-time is module 7's promotion machinery, not an edit).</p><p><b>The statuses.</b> The record's lifecycle state: <b>Active</b> (the working population — every report's default filter), the notice-period states where used (resignation submitted, exit in progress — module 7's machinery), <b>Left</b> (separated — the terminal state that Chapter 2's number-retirement law protects), and the probation overlay (the confirmed/unconfirmed distinction riding the confirmation-date field — module 2 runs probation as a process; this field records its outcome). The <b>status discipline</b> is the chapter's conviction: statuses drive EVERYTHING downstream — the Active filter defines headcount (the analytics of module 8 are only as true as the statuses), leave accrual runs for active staff (the departed employee still accruing leave is a liability quietly growing — module 4), attendance expects the active roster (module 3's absence reads misfire when ghosts remain), approval spines break when a Left manager still holds reports (Chapter 3's maintenance law), and — across the boundary — payroll pays the active list, which makes a stale status literally expensive: <b>the ghost employee</b> (left in fact, Active in the system) is the people layer's phantom stock, and like every phantom this academy has met, it corrupts every read that touches it until someone posts the truth.</p><p><b>The status change as document.</b> The cure is the academy's standard one: statuses change by DOCUMENTED EVENTS, not edits — the separation process (module 7) sets Left with its date and its paper trail; the confirmation process sets confirmed with its letter; the contract renewal extends the end date with its addendum — each change carrying who, when, why, and the attachment. A status history that reads as a sequence of documents is an employment history that survives any dispute; one that reads as unexplained edits is the folder-and-memory system wearing a database costume — and the monthly status hygiene read (the Active list walked against reality: does everyone on it still work here? does everyone working here appear on it?) is the people layer's smallest, highest-yield ritual, module 8's calendar carrying it from this chapter forward.</p>"),
L("Chapter 5 — The user link: self-service & the joined identity", "13", "<p>The employee record describes a person; the USER account lets that person act — and the link between the two is where the people layer becomes participatory instead of administrative. The join, its dividends, and its governance.</p><p><b>The join.</b> Each employee record links to a system user (their login), and the join creates the identity the workflows need: the person who logs in IS employee so-and-so, which means the system can show them THEIR record, route THEIR requests along THEIR spine, and stamp THEIR documents with an identity nobody typed. Not every employee needs a user (the warehouse loader whose attendance is captured at a device may never log in — the record exists regardless; the user is optional), but every user who is staff should link to their employee record — the unlinked staff user is a workflow orphan whose leave requests route nowhere and whose approvals carry no organisational weight.</p><p><b>Self-service: the dividend.</b> What the join buys, itemised — and it is the people layer's biggest efficiency purchase: employees SEE their own record (their details, their leave balance, their attendance history, their documents — the transparency that kills a whole category of HR queries: the balance question answered by a glance instead of an email), REQUEST through documents (the leave application, the attendance regularisation, the expense claim — each born as a document in the right queue instead of a corridor conversation someone must remember to transcribe), UPDATE what is theirs to update (the phone number, the address, the emergency contact — with the governed fields fenced: Chapter 6 draws the line between self-service fields and HR-only fields), and RECEIVE what is theirs to receive (the payslip across the boundary, the appraisal form, the policy acknowledgment). The culture note the consultant carries: self-service adoption is a TRAINING outcome, not a toggle — the workforce that learns week one that requests go through the system (because paper requests are politely redirected, every time) builds the habit; the one where both channels stay open forever builds neither.</p><p><b>Approvals riding the spine.</b> The join plus the reports-to field is the approval machinery: the leave application knows its approver (the applicant's manager, from the spine), the workflow escalates along the tree, and the approval lands stamped and dated — module 4 will run this at full depth; this chapter's contribution is the wiring insight that the SPINE is the single point of maintenance: fix the manager field and every workflow above it self-corrects, which is why Chapter 3 made its maintenance a law.</p><p><b>The permission frame.</b> The join's governance, previewed for module 8's full treatment: the employee role sees SELF (own record, own requests, own balances — and nothing of anyone else's), the manager sees their TEAM (the reports beneath them — their leave calendar, their attendance, their appraisals: the spine defining the visibility exactly as it defines the routing), and HR sees the population — with the sensitive layers (disciplinary records, medical notes where held, the compensation fields across the boundary) fenced tighter still. The design conviction, stated here because the user link is where violations happen: people data leaks along over-broad permissions, not through dramatic breaches — the report every user can run, the list view with one column too many — and the permission walk (module 8) audits exactly those edges. Confidentiality is a configuration before it is a policy.</p>"),
L("Chapter 6 — Governing the people master", "13", "<p>The fifth master gets the governance every master earned — creation gated, changes evented, expiries tracked, and the annual verification — with the custody flavour Chapter 1 promised. The governance chapter.</p><p><b>Creation: one door.</b> Employee records are created by HR (or the office holding the HR hat — the sizing honesty as always) through ONE flow: the recruitment pipeline's conversion (module 2 — the applicant who accepted becomes the employee, carrying the offer's terms so the record is born from its documents), or the governed direct creation for the rare walk-in hire (with the same checklist: documents collected, credentials sighted, identifiers captured, the duplicate check run — the person who worked here before, left, and returned is a REHIRE with history, not a duplicate: the record linked or the histories merge-proofed, because two records for one person is the duplicate-jungle disease at its most personally consequential — split leave histories, split tenure, split everything).</p><p><b>Changes: fields have owners.</b> The field-level governance the custody frame demands: <b>self-service fields</b> (contacts, address, emergency contact — the person's own, updated freely with the change logged), <b>HR-governed fields</b> (the org placement, type, status, grade, dates — changed only by the lifecycle documents that own them: Chapter 4's law, generalised), and <b>the joined-function fields</b> (bank details — the fraud-relevant field: changed by a governed process with verification, because the masters-not-messages defence of the money tracks applies to salaries exactly as it applied to supplier payments — the <i>my account changed</i> email the week before payday gets the same known-channel verification, and the payroll boundary is notified of every change through the standing handoff, never a side note).</p><p><b>Expiry tracking: the calendar in the record.</b> The people master carries dates that EXPIRE, and the system's job is to see them coming: fixed-term contract end dates (Chapter 4's conviction — surfaced 60 and 30 days out, so renewal or separation is a decision, not an accident), probation ends (the confirmation due — module 2: the probation that lapses unaddressed converts to confirmation by default in most readings of Nigerian practice, which is fine when intended and expensive when not — the employment lawyer's terrain, the system's reminder), document expiries where the role carries them (the driver's licence for the van custodian — Inventory 6's driver accountability meeting this track; the professional licences of the pharmacist superintendent — the regulated trade's compliance riding an HR field; work permits for expatriate staff), and certification expiries (module 6's training layer feeding back — the forklift certificate, the first-aider's renewal). The expiry read is a standing worklist — dated, owned, worked — the aging-report discipline of four tracks applied to the calendar inside the person's record.</p><p><b>The annual verification.</b> The people master's cycle count: annually (and at every lifecycle event as a touch-point), each employee confirms their record's accuracy — contacts current, emergency contact reachable, documents complete — through self-service where the join exists, through a signed form where it does not; HR reconciles the returned confirmations, chases the silent, and files the completion. Twenty minutes per employee per year, and the dividend lands exactly where Chapter 2 warned: the emergency contact that answers, the address that receives the letter, the record that stands up in the dispute. The master that is verified annually is a master; the one that is not is a snapshot aging toward fiction — the counting law's people edition, closing the governance loop.</p>"),
L("Chapter 7 — The people layer meets the other four", "13", "<p>Four tracks named people this track now records — and the joins between the employee master and the other masters are where the academy's layers become one system. The join map.</p><ul><li><b>The custodian</b> — Inventory 1 made every warehouse answer to a person; the employee record IS that person, and the join completes the design: the warehouse's custodian named as an employee (not a free-text name that survives their departure as a ghost), the user-permission restrictions (the branch user fenced to their leaves) riding the same identity, and the custody handover at transfer or separation (module 7) triggering the warehouse machinery's own handover — the count that confirms custody before it changes hands, now scheduled by an HR event instead of remembered by luck.</li><li><b>The till operator &amp; the van custodian</b> — Accounts 3's sessions and Inventory 6's tailgates both reconcile per PERSON: the operator identity on every session is the employee, their clean-close streaks and variance rates are readable per employee record — and module 5 will make the connection explicit: the operational reads four tracks built (accuracy rates, clean sessions, count records) are PERFORMANCE EVIDENCE, sitting ready for the appraisal that references records instead of impressions.</li><li><b>The salesperson</b> — the selling track's sales-team machinery joins here: the salesperson record linked to the employee, targets and attributions riding the join, the commission computations (across the payroll boundary) fed by it.</li><li><b>The approver</b> — every two-names pattern this academy installed (the write-off's signatures, the payment run's releaser, the journal's second eyes) is ultimately a PERSON holding a role; the employee lifecycle maintains those holdings (the approver who resigns triggers the mandate-review discipline — Accounts 3's same-week signatory removal, now fired by the HR event that knows first), which is the deepest join of all: <b>the HR system knows about departures before every other control does, and the separation checklist (module 7) is where every other track's access gets revoked.</b></li><li><b>The branch &amp; cost center alignment</b> — the employee's branch aligns with the warehouse tree's branches and the cost-center tree's leaves (the three trees naming the same operational units — the design hour of Chapter 3 checking the alignment deliberately), so that the branch's people, stock, and money read as one unit: the branch scorecard (Inventory 6), the branch P&amp;L (Accounts 6), and the branch headcount (module 8) describing one thing three ways — and, across the boundary, the payroll cost landing on the cost center where the person works, which is Accounts 6's addressed-payroll line closing its loop.</li></ul><p><b>The join discipline.</b> One rule governs all of them: joins are made by LINK, not by retyping (the free-text name that drifts from the record it meant is the join that silently breaks), and the separation checklist is the join map read in reverse — every link the person holds, listed and resolved before Left is final. The people layer, joined this way, is not a parallel HR system beside the business; it is the business's own structure, finally knowing who its people are.</p>"),
L("Chapter 8 — Case study: HealthTrade's people layer is born", "16", "<p>The fifth master, installed. The firm this academy has grown — eleven people at the start of the Selling track, near thirty by the Accounts track's close — finally gets its people layer, and every chapter clocks in.</p><p><b>The load (Ch. 2, 6).</b> The existing workforce — 27 people across three branches and head office — enters properly: records created from documents (contracts pulled from the paper folders, identifiers captured, credentials sighted and marked verified where originals were produced; the two files with missing contracts flagged and regularised with the employment adviser — the load surfacing the paper gaps exactly as the opening stock count surfaced the phantom cartons), employee numbers issued from the series (the decade view), photographs taken in an afternoon, and the duplicate check earning its keep once: a returning employee — left year one, rehired at Akure — nearly loaded fresh; caught, linked as the rehire she is, tenure history whole.</p><p><b>The structure designed (Ch. 3).</b> The design hour with the MD: four departments (Operations, Sales &amp; Service, Finance &amp; Admin, and the Distribution unit — shallow, owned, real), designations rationalised (eleven titles collapse to eight that name actual roles — the <i>Senior Officer II</i> vanity retired), three grades (the band structure the leave policies of module 4 will attach to), and the three-tree alignment checked deliberately: branches, warehouses, cost centers naming the same units, one row per unit on the alignment sheet. The reporting spine wired last and checked as a tree: every active employee a manager, no gaps, no cycles, the MD at the root — and one reality correction made out loud (the spine said the Akure supervisor reported to head office; everyone knew she reported to the Ibadan manager who mentors the new branch; the field corrected to the fact, and the first leave request a week later routes correctly because it was).</p><p><b>The joins made (Ch. 5, 7).</b> User accounts linked for the 19 staff who log in; the custodian joins completed (every warehouse's custodian now an employee link — the free-text names of the Inventory era retired), the till operators joined to their session identities, the van custodian's driver's licence expiry entered into the tracking (14 months out — the worklist's first resident), and the approver map documented: who holds which two-names roles, so the separation checklist knows what to revoke. Self-service launches with the one-channel discipline — the first paper leave request is politely redirected the same day, and by week three the queue is the only channel anyone tries.</p><p><b>The hygiene catch (Ch. 4, 6).</b> Month two's first status read walks the Active list against reality and finds the expected ghost: a weekend till assistant who stopped coming in the previous quarter — no resignation, no process, just absence that faded into assumption — still Active, still accruing leave, still on the roster the attendance module (module 3) is about to expect. Resolved by the document the situation deserves (the abandonment process the employment adviser confirms, the separation recorded with its trail, Left set with its date), and the lesson filed for the module ahead: the ghost was harmless in a folder-and-memory world and expensive in a system world — <b>which is the system working</b>, because every machine this academy has installed made the undocumented visible by refusing to pretend alongside it. The people layer ends its first quarter with 27 true records, one clean structure, a working spine, and its first ritual — the monthly status read — on the calendar with a name.</p>"),
L("Chapter 9 — Common mistakes & the first law", "13", "<p>The people master's scar tissue — the diseases every consultant meets in the first week of every HR engagement. Symptom → disease → fix.</p><p><b>Pattern 1 — the spreadsheet workforce.</b> Symptom: the staff list in a spreadsheet, three versions old, each department keeping its own; headcount answered differently by everyone asked. Disease: the fifth master never created (Ch. 1) — people data without a system of record. Fix: the governed load (records from documents, numbers from the series, duplicates checked), the spreadsheet retired to read-only history, and the status read instituted so the new record stays true.</p><p><b>Pattern 2 — the paper file as the real record.</b> Symptom: the system holds names and dates; everything that matters lives in folders; every dispute starts with a filing-cabinet search. Disease: the master as index instead of file (Ch. 2) — attachments never made, documents never migrated. Fix: the document load (contracts, IDs, letters scanned to the record — the backlog priced once), the lifecycle documents born digital thereafter, and the folder demoted to the archive it should be.</p><p><b>Pattern 3 — the broken spine.</b> Symptom: leave requests routing nowhere or to departed managers; approvals by corridor because the system's chain is wrong; an org chart nobody believes. Disease: the reports-to field unmaintained (Ch. 3) — reality and record diverged. Fix: the spine walked (every active employee, a real manager, tree-shaped), the lifecycle events re-pointing reports as they move people, and the spine's accuracy owned as part of every transfer and separation.</p><p><b>Pattern 4 — the ghost roster.</b> Symptom: headcount reports nobody trusts; leave accruing for the departed; payroll (across the boundary) paying a list HR cannot vouch for. Disease: statuses changed by memory or never (Ch. 4) — the phantom-stock disease in its people form. Fix: status changes by documented events only, the monthly Active-list walk, and the separation process (module 7) as the single door to Left.</p><p><b>Pattern 5 — the everything-eyes HR.</b> Symptom: any user able to list employees with personal columns; salary-adjacent fields visible to the curious; the disciplinary note that circulated. Disease: confidentiality as policy without configuration (Ch. 5) — the custody frame unenforced. Fix: the permission design (self / team / HR / sensitive tiers), the report and list-view edges audited, and module 8's permission walk on the annual calendar.</p><p><b>Pattern 6 — the vanity structure.</b> Symptom: nine departments for eleven people; inflated designations; grades that map to nothing. Disease: the structure designed from aspiration instead of accountability (Ch. 3). Fix: the design hour re-run honestly — departments that are owned, titles that name roles, grades that carry real policies — and the restructure executed as the event it is.</p><p><b>The first law.</b> Four tracks began with masters; the fifth begins with the most consequential one: <b>one person, one record, whole lifecycle — the employee master is a person's record held in the firm's custody: created once from documents, governed always by events, joined everywhere by link, verified annually, and read on need, not curiosity.</b> The structure places the person, the spine answers for them, the statuses tell the truth, and the joins make four tracks' named people real. Seven modules stand on this record; module 2 begins where every employee begins — the pipeline that found them.</p>"),
]

QUESTIONS = [
Q("The employee is:", ["An HR detail", "The fifth master — the person every other track named without recording", "A payroll row", "A user account"], 1, "Customer, supplier, item, account... employee.", "Ch1"),
Q("This track excludes payroll because:", ["Payroll is unimportant", "It is a different discipline with a different owner — HR owns the INPUTS payroll consumes", "It is too hard", "The law forbids it"], 1, "Who is employed, who attended, who was on leave — the clean handoff is where the functions mesh.", "Ch1"),
Q("The people master differs from the other four because:", ["It is smaller", "It records a PERSON — custody, confidentiality, and procedural fairness change the governance's flavour", "It has no documents", "It changes less"], 1, "The academy's protections framing, applied to the people it was always about.", "Ch1"),
Q("Employee numbers are:", ["Reusable after departure", "Retired with the person — re-issued numbers merge two people's histories forever", "Optional", "The phone extension"], 1, "The naming-series law's fifth appearance.", "Ch2"),
Q("The date of joining anchors:", ["Nothing much", "Tenure, probation, leave accrual, and every service computation", "Only the contract", "The user account"], 1, "The field the whole system reads.", "Ch2"),
Q("The emergency contact is checked first at verification because:", ["It changes most", "It is the field the firm hopes never to use and must never find stale", "It is legally required", "It is easy"], 1, "Its absence is discovered only on the day it is needed.", "Ch2"),
Q("Employee data is read on:", ["Curiosity", "NEED — and the role-based fences are how the rule survives turnover in HR itself", "Seniority", "Request"], 1, "Confidentiality is a configuration before it is a policy.", "Ch2, Ch5"),
Q("Departments exist when:", ["The org chart looks better", "Someone owns them and their people are managed as a group — accountability, not aspiration", "There are ten employees", "Titles require them"], 1, "The eleven-person firm needs three or four, not nine.", "Ch3"),
Q("The reports-to field is:", ["Decoration", "The approval spine — leave, appraisals, claims, and notices all route along it", "The payroll key", "Optional"], 1, "The trees say where people sit; the spine says who answers for whom.", "Ch3"),
Q("The spine's disciplines are:", ["Set once, forget", "Every active employee has a manager, tree-shaped, maintained at every event, reflecting reality", "Annual updates", "HR's memory"], 1, "The record's chart and the factual chart must be the same chart.", "Ch3"),
Q("The three-tree alignment means:", ["One tree replaces the others", "Branches, warehouses, and cost centers naming the same units — people, stock, and money reading as one", "HR owns all trees", "Nothing"], 1, "The branch scorecard, P&L, and headcount describing one thing three ways.", "Ch3, Ch7"),
Q("A fixed-term contract's end date is:", ["A note", "A first-class field the system must see coming — expiry unnoticed converts deliberate into accidental", "The anniversary", "HR's memory"], 1, "Surfaced 60 and 30 days out; renewal or separation as a decision.", "Ch4"),
Q("The daily-paid loader in no system is:", ["Flexible labour", "A liability wearing a wheelbarrow — unrecorded, uninsured, unprovable in every direction", "Standard practice", "Cheap"], 1, "Engaged properly or not at all.", "Ch4"),
Q("The ghost employee is:", ["Harmless", "The people layer's phantom stock — corrupting every read until someone posts the truth", "A payroll issue only", "Rare"], 1, "Left in fact, Active in the system.", "Ch4"),
Q("Statuses change by:", ["Edits when remembered", "Documented events — separation, confirmation, renewal — each carrying who, when, why, and the attachment", "Annual review", "The manager's word"], 1, "A status history of documents survives any dispute.", "Ch4"),
Q("The monthly status read asks:", ["Who was late?", "Does everyone Active still work here, and does everyone working here appear?", "Who is on leave?", "Nothing"], 1, "The people layer's smallest, highest-yield ritual.", "Ch4"),
Q("An unlinked staff user is:", ["Fine", "A workflow orphan — requests route nowhere, approvals carry no organisational weight", "More secure", "Standard"], 1, "Every staff user links to their employee record.", "Ch5"),
Q("Self-service's biggest dividend is:", ["Fewer meetings", "Requests born as documents in the right queue, and the balance question answered by a glance", "Prettier records", "Less training"], 1, "It kills a whole category of HR queries.", "Ch5"),
Q("Self-service adoption is:", ["A toggle", "A training outcome — paper requests politely redirected every time, until the habit builds", "Automatic", "Optional"], 1, "Two channels open forever builds neither.", "Ch5"),
Q("People data leaks along:", ["Dramatic breaches", "Over-broad permissions — the report anyone can run, the list view with one column too many", "Paper only", "Email"], 1, "The permission walk audits exactly those edges.", "Ch5"),
Q("A returning former employee is:", ["A new record", "A REHIRE with history — linked, not duplicated; two records for one person splits everything", "A duplicate to merge later", "Refused"], 1, "The duplicate-jungle disease at its most personally consequential.", "Ch6"),
Q("Bank detail changes on the employee record get:", ["Quick edits", "The masters-not-messages defence — known-channel verification, the payroll boundary notified", "Email confirmation", "No process"], 1, "The 'my account changed' email before payday is the supplier fraud's HR twin.", "Ch6"),
Q("The expiry worklist tracks:", ["Birthdays", "Contract ends, probation ends, licences, permits, and certifications — dated, owned, worked", "Leave balances", "Anniversaries"], 1, "The aging-report discipline applied to the calendar inside the record.", "Ch6"),
Q("A lapsed probation, in most readings of practice:", ["Extends automatically", "Converts to confirmation by default — fine when intended, expensive when not", "Ends employment", "Means nothing"], 1, "The lawyer's terrain, the system's reminder.", "Ch6"),
Q("The annual verification is:", ["Bureaucracy", "The people master's cycle count — each employee confirms their record; HR reconciles and chases", "Optional", "The audit"], 1, "The unverified master is a snapshot aging toward fiction.", "Ch6"),
Q("Warehouse custodians are recorded as:", ["Free-text names", "Employee LINKS — the name that survives departure as a ghost is the join that silently broke", "User accounts only", "Cost centers"], 1, "Joins are made by link, not by retyping.", "Ch7"),
Q("Operational reads (clean sessions, count records) are:", ["Operations' business only", "Performance evidence sitting ready — the appraisal that references records instead of impressions", "Deleted annually", "Private"], 1, "Module 5 makes the connection explicit.", "Ch7"),
Q("HR knows about departures:", ["Last", "Before every other control does — the separation checklist is where every track's access gets revoked", "Never officially", "From payroll"], 1, "The deepest join: the approver who resigns triggers the mandate review.", "Ch7"),
Q("HealthTrade's load surfaced:", ["Nothing", "Two missing contracts regularised and one near-duplicate rehire caught and linked", "Only photographs", "Payroll errors"], 1, "The load surfacing paper gaps as the count surfaced phantoms.", "Ch8"),
Q("The spine's reality correction was:", ["Cosmetic", "The Akure supervisor re-pointed to her factual manager — and the first leave request routed correctly", "Refused", "Deferred"], 1, "The record corrected to the fact, out loud.", "Ch8"),
Q("The weekend assistant ghost was:", ["Deleted", "Resolved by the abandonment process with its trail — Left set with its date", "Left Active", "Rehired"], 1, "The undocumented made visible because the system refused to pretend.", "Ch8"),
Q("The vanity structure costs because:", ["Titles are free", "Grades and policies attach to inflated titles later — real money on aspirational paper", "It doesn't", "Auditors object"], 1, "Nine departments for eleven people.", "Ch9"),
Q("The paper folder is demoted by:", ["Decree", "The document load priced once, lifecycle documents born digital, the folder as archive", "Shredding", "Time"], 1, "The master as file, not index.", "Ch9"),
Q("The spreadsheet workforce's fix includes:", ["Better spreadsheets", "The governed load, the spreadsheet retired to read-only history, the status read keeping the record true", "More versions", "A bigger folder"], 1, "People data with a system of record.", "Ch9"),
Q("This module's law is:", ["HR is paperwork", "One person, one record, whole lifecycle — created from documents, governed by events, joined by link, read on need", "Records are optional below 50 staff", "The folder is the record"], 1, "The most consequential master, held in custody.", "Ch9"),
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
    if '"3.120.0"' not in init:
        sys.exit("ABORT: not at v3.120.0.")

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
    print(f"HR 1: 9 chapters ({total:,} chars, min {min(len(l['html']) for l in LESSONS):,}), bank {len(bank)}, spread {dist}")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data = {
        "employee_master": {
            "title": "HR 1 — The Employee Master & Organisational Structure",
            "desc": "The foundation of the people certification: the employee as the fifth master, the person's record and its custody frame, the organisational trees and the reporting spine, employment types and the status discipline, the user link and self-service, master governance, and the joins to every other track.",
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
        f.write(init.replace('"3.120.0"', '"3.121.0"'))
    print("  created: academy_hr_pro_data.json (HR 1)")
    print("  created: academy_seed_hr_pro.py (product, track ZERP-HRPRO, refresh functions)")
    print("wrote __version__ -> 3.121.0")


if __name__ == "__main__":
    main()
