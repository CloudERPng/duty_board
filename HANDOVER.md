# Duty Board — Handover Brief · v3.228.2

**App:** `duty_board` on Frappe/ERPNext v15 · **Live site:** `xlevel.clouderp.one`
**Repo:** https://github.com/CloudERPng/duty_board · **Bench:** `bench@newv15`, `~/frappe-bench`
**Last full brief:** v2.90.0, covering v2.91.0 → v3.7.0.
**Section 12 below** covers v3.206.0 → v3.226.3. Between v3.7.0 and v3.206.0 the
git log is the record — this brief was not maintained through that span, which is
itself worth knowing before trusting anything here as complete.

---

## 1. What this application is

Xlevel's service-delivery operating system: staff attendance & daily planning,
team chat & DMs, project boards (now with subtasks), support issues with SLAs
and RCA, client collaboration rooms, a controlled Document Hub, a training
Academy with certification tracks, a full Accounting Services unit, and — new
in this span — a **commercial layer** (dependencies, CR pricing gate,
cost-to-serve, room scope) and a **redesigned client portal**.

Commercial model encoded in the software: **subscriptions include unlimited
in-scope support; change requests are the only billable object; pricing is
done exclusively by the CR pricer** (Duty Settings → `cr_pricer`, in practice
olamide@xlevelretail.com, optional deputy).

## 2. Surfaces & personas

| Surface | Route | Who |
|---|---|---|
| Staff SPA | `/app/duty-board` | System Users. Faces: board (Me), Clients, Projects, Sales, Books; header tools: Document Hub, 💼 CR pricing (pricer), 💰 Cost to serve (Books managers) |
| Client portal | `/portal` | Website Users (room members). Tabs: Home / Projects / Training / Documents; PWA (Add to Home Screen, web push) |
| Join flow | portal join/verify | Guests → staff approve |

Test personas: staff `olamide@xlevelretail.com`; client `olamideshodunke@gmail.com`
(Saheed, Audacious Business Concepts).

## 3. Code map (module rule: new domains get new modules)

| File | Domain |
|---|---|
| `api.py` | attendance, plan/todos, team chat, issues, meetings-staff, board |
| `client_room.py` | the staff↔client membrane: rooms, messages, tasks, milestones, CRs, meetings, training-client, deliverable/followup client wrappers, join flow |
| `accounting.py` | Books: cadence engine, matrix, round, register, follow-ups, invoicing/VAT, chase, KPIs, onboarding, playbooks |
| `commercial.py` | dependencies, CR pricing gate, cost-to-serve, room scope |
| `projects.py` | boards, cards, **subtasks**, card↔todo sync, sessions-on-cards |
| `sales.py` / `dm.py` / `push.py` | leads pipeline / DMs / web push |
| `permissions.py` | `require_staff()` / `require_authenticated()` — the single guard |
| `document_hub/` | Client Document check-out/in, versions |
| `academy_seed*.py` | track seeds (Bookkeeper, Closer, Closer Manager, Consultant, client tracks) |
| `page/duty_board/duty_board.js` | staff SPA (~8k lines) |
| `www/portal.html` | client portal (single file, skin2 token layer + queue engine) |
| `tests/test_permissions.py` | negative access-control suite |

## 4. Security model (post-review hardening, v3.2.0)

Every whitelisted endpoint declares an audience: staff (`require_staff`,
aliased `_staff_only`), authenticated (push), room member (`_client_room()`
membership resolution — the only client door), or explicit guest.
**Enforcement:** `bench --site xlevel.clouderp.one run-tests --module
duty_board.tests.test_permissions` — logs in as a Website User and calls every
staff endpoint in api/projects/sales/dm/commercial/document-hub expecting
PermissionError. Run it on every deploy. New staff endpoints are covered
automatically; non-staff endpoints must register in the test's `NON_STAFF` map.
(cssutils box-shadow ERRORs in test output are harmless framework noise.)

## 5. The commercial layer (v3.3.x)

- **Duty Client Dependency** (`DEP-YYYY-#####`): staff 📋 dialog per room
  (add/receive/reopen/waive/remind, reminder count); portal "Awaiting from
  you" with client "I've provided this"; `delay_split()` = client-delay days.
- **CR pricing gate** on Duty Change Request: `pricing_status`
  (Awaiting Pricing default → Priced / Covered by Subscription / Goodwill /
  Rejected / Deferred), `estimate_hours`, `released`, `invoice_status`.
  Clients see a CR only when `released` **and** status ≥ Awaiting Approval.
  **Priced = submission** (status→Awaiting Approval, submitted_on, client
  push). Work statuses blocked until covered/goodwill or priced+approved —
  enforced in `chreq_set_status`; `chreq_request_approval` refuses unpriced.
  Pricer UI: 💼 queue (age-badged) + "Price now" inside the CR detail.
- **Cost-to-serve** (`commercial.cost_to_serve`, Books-managers): Work Session
  hours per customer split support(issue)/delivery(card) × `staff_cost_rate`
  vs known fees; red rows = renewal-conversation list.
- **Room scope**: `scope_note`, `support_plan` on Client Room (⚖ dialog, also
  hosts the **project picker** since v3.6.0); portal plan banner.

## 6. Projects: subtasks (v3.7.0) — the three rules

Child table **Duty Project Subtask** (title, assignee, due, status, note,
done_by/on, linked todo). Rules as decided:
1. **Clamp-and-notify** — card due moved earlier ⇒ later subtasks clamp to it,
   assignees notified; subtask due always ≤ card due.
2. **Progress-only for clients** — task detail shows "N of M steps done".
3. **Hard block** — card cannot enter Completed with open subtasks
   (enforced in both `move_task` and `update_task`; error names the items).
Assigned subtasks spawn Daily Todos (`📌 title · under "card"`), synced on
done/reopen/delete; last-done nudges the card owner. Board chip ☑ n/m.
Time tracking stays on the card; CR/milestone counters count **cards** only.

## 7. Portal design system (v3.4.x)

Token skin (`<style id="skin2">` layered after the legacy stylesheet):
paper `#F6F5F1`, single accent viridian `#0E5A4A`, Fraunces (display) +
Instrument Sans (UI), colour reserved for status (amber waiting / red late /
green good). Home = greeting hero + **Needs-you queue** (one spine, five
feeders: deps, accountant queries, doc requests, released CR approvals,
deliverable sign-offs) + bounded conversation + numbers rail. Desktop home is
a named-area grid `"err/hello/queue+rail/chat+rail/left+rail/foot"` at
max-width 1280; **any new direct child of `.wrap` must receive a grid area or
auto-placement hoists it to the top** (chat and foot both bit us). Queue items
reuse legacy element ids (`dp_/qa_/rf_`) so original action functions work
untouched. Staff-side list/detail pattern lives in `chreqs_dialog` (`xcr-`
scoped stylesheet) — the template for future dialog rebuilds.

## 8. The offline harness (build tool — keep using it)

`/home/claude/harness/` in the dev container: `portal_test.html` = portal with
`const api` spliced for a `__FIX` fixture map; `shot.js`/`audit.js` run
Playwright Chromium (`/opt/pw-browsers/chromium-1194/.../chrome`,
`--no-sandbox`) and dump **numeric bounding boxes/computed styles** at 1440 and
390 px. Refresh the harness from source after every portal edit; audit before
shipping. This replaced the deploy→screenshot→guess loop; when vision is
unreliable, numbers aren't.

## 9. Deploy ritual (unchanged, sacred)

Zip from the package dir excluding `modules.txt`, `hooks.py`, `*.zip` →
`unzip -o` into `apps/duty_board/duty_board/` → `migrate` **only when doctypes
changed** → `bench build --app duty_board` + `clear-cache` →
`supervisorctl restart` web+workers → desk hard-refresh (stubborn:
`localStorage.clear()`); portal clients hard-refresh / reopen PWA. Then run the
permission suite. md5sums recorded per release in chat; git is source of truth.

**Migrations in this span:** v3.0.0 (service-line fields), v3.1.0 (follow-up
recipients), v3.3.0 (dependency doctype + CR/room/settings fields), v3.6.1
(Duty Project title_field), v3.7.0 (subtask doctype + table field).

## 10. Settings that must hold values

Duty Settings: `cr_pricer` (= olamide@xlevelretail.com; **blank means nobody
can price**), `cr_pricer_deputy` (optional), `staff_cost_rate` (₦/h — blank
disables cost columns), Books managers/monthly requests/invoice item/rate
floor/tax template as before. Room-level: bookkeeper, meeting_staff,
owner_user, books_scope/FYE, scope_note/support_plan, project.

## 11. Deferred queue (agreed, not forgotten)

Sibling staff dialogs (deps/follow-ups/milestones) → xcr list/detail; staff
shell four-workspace regrouping (My Work / Delivery / Clients / Books);
portal phase-2 (Projects/Training/Documents layouts, emoji strip in section
headers, rail meeting/team cards); UAT/acceptance states → Delivery
Accountability Timeline (derived from deps + sessions + CR/milestone events);
capacity planning; opportunistic modularisation + request-path db.commit
cleanup + config extraction (review items); per-line document-request lists;
remaining Academy waves (ZhiftCRM role tracks, then POS→HMS→ERP→HR).

## 12. Working discipline (hard-won)

Read the producer before patching the consumer (three violations this span,
three hotfixes: member full_name, `_room_project`, client_get_staff fields).
Anchor replacements must assert count==1 and be applied **per-patch with
per-patch writes** — batch scripts that assert mid-way lose everything.
Duplicate-def scan after every Python edit; `node --check` after every JS
edit. Two `if (a === "ask")` handlers exist in the JS (milestones + CR) —
anchor on unique surrounding text. Tabs, not spaces, in anchors.

---

## 12. The academy becomes a product · v3.206.0 → v3.226.3

Written at the end of the span it describes. Everything before section 12 predates
it and may have drifted; the git log is authoritative where they disagree.

### What changed, in one line
The training academy went from an internal learning aid to something sellable:
proctored assessments, seats bought and enforced, clients administering their own
people, and a public catalogue.

### The commercial spine
- **Duty Academy Order** (`AOR-YYYY-#####`) → **Duty Academy Entitlement** (`AEN-`).
  A client's administrator requests seats from the catalogue; a proforma is emailed
  and filed on their shelf; **a human approves against a payment reference** and
  that approval, and only that, grants the seats. There is no automatic path from
  money to access, deliberately.
- **A seat is one named learner on one track**, however many courses it holds.
  Enforced in `academy.seat_gate`, called from both the administrator's bulk assign
  and a learner's self-pursue — either door alone would leak seats.
- **Duty Training Cohort** groups a client's staff for an intake, with an exam
  window. `cohort_scorecard` produces the sponsor's report; `cohort_scorecard_publish`
  renders it to their Documents shelf.

### Assessment integrity
- Proctoring (v3.78.0, staff-only until now) is open to the portal: one question at
  a time, server-stamped, countdown, focus-loss counted, no going back.
- Per-module policy on `Duty Training Module`: `max_attempts`, `retake_wait_hours`,
  `hide_wrong_answers`. **Every field defaults to the old behaviour**, so nothing
  changed until deliberately set.
- Attempt caps are enforced on the **client path only**. Staff testing stays ungated.
- `Duty Training Record.extra_attempts` lets an administrator unblock one person
  without loosening policy for everybody.

### Teaching, not just testing
- **Duty Lesson Check** — three formative questions per chapter, never scored, never
  on a transcript, with a written rationale read at the moment a learner is wrong.
  Presence is the switch: a lesson with no checks behaves exactly as before.
- **Duty Lesson Question** — a learner's question lives with the chapter, not in the
  room. Staff answer from a queue; the learner is emailed. A published answer shows
  to everyone reading that chapter **without the asker's name or timestamp**, because
  somebody who thinks their confusion will be displayed under their own name does not
  ask.

### Client self-service
The room administrator (`Client Room Member.is_admin`, reusing the existing role
rather than a second flag) can invite colleagues in bulk, end and restore access,
browse the catalogue, request seats, assign tracks with due dates, see per-person
detail, grant an extra attempt, and export the roster. Staff involvement is now
confirming payment and answering questions.

**Deactivation never deletes.** Records, attempts and certificates survive, so a
returning employee resumes and a leaver's certificate stays true.

### Access, and what a client keeps
`_learning_room()` passes `allow_frozen`: reading, checks, assessments and
certificates survive a renewal freeze while chat, projects, tickets, the catalogue
and new assignment do not. **Seats are a purchase, not a subscription** — and a pure
academy client with no ERP subscription would otherwise have been locked out by a
gate that never applied to them. Seat expiry blocks new assignment only.

### Public surface
`/academy` lists every published client track with price or Free; `/academy?track=`
gives the full page including a **sample chapter** where `Duty Lesson.is_sample` is
ticked. Nothing else about a client is reachable there — exposure was audited.

### Scheduled work
`academy.setup_academy_jobs` installs two Scheduled Job Type records: nudges daily
07:00, administrator digest Mondays 08:00. **hooks.py is excluded from the deploy
zip**, so scheduling ships as records, following `notify.py`.

### Settings that must be set before selling
`Duty Settings`: `academy_bank_details`, `academy_approver`, `academy_vat_rate`,
`academy_tutors`. Empty values degrade quietly rather than erroring, which is
convenient and easy to forget.

### The audit, v3.224.1 → v3.226.3
Six chunks — access control, reachability, schema, correctness, front end,
background — plus the test suite. **Eight defects, every one silent.** Certificate
downloads returning `null`; a team overview filtering on a certificate status that
never existed; Radar→Lead promotion failing on an invalid Select value; a 40,000-query
health load waiting for volume; an unguarded exam-score division; consultant-written
notes rendered raw into staff sessions; reminders recorded but never delivered.

Two scanners produced confidently wrong results before being corrected. **Self-test
every pattern against a known positive before believing a clean scan**, and chase
every finding rather than trusting a count.

Tools left in the app for reuse:
`audit_academy.py` (content standards), `academy_repair.py` (push corrections into
an already-seeded site, since seeds are insert-only and skip existing modules),
`tag_topics.py`, `fix_answer_spread.py`.

### Open, and deliberately not closed
- **Concurrency was never examined.** The seat gate under simultaneous assignment is
  the one with money attached; pool-claim collisions and exam double-submit are next.
- ~40 staff-to-staff template interpolations remain unescaped in the SPA.
- `ignore_permissions=True` is used widely and has never been counted.
- `_meeting_caps_check` counts the daily rule by `meeting_date` and the weekly rule
  by `creation`. The error messages match one reading, the docstring the other.
- Content: `who_for` and `outcomes` are empty on every track, no chapter is marked
  `is_sample`, and only the Closer track meets the content standard.

---

## 13. The finance track, and a fourth audit chunk · v3.226.4 → v3.228.2

### Accounting & Finance for Non-Finance Managers — complete
Eight modules, 72 chapters, 216 check questions, 338 exam questions, ~49,000
words. Every module audits `ok` on depth, bank size, answer spread, topic
tagging, check coverage, rationale quality, banned phrases and HTML validity.

Order written: the reading spine first (P&L, balance sheet, cash), then the
deciding modules (cost, pricing, budgets, money), and the framing module last —
because framing is easier once you know what you are framing.

**Design principle: read before prepare.** This audience will never draft a set
of accounts; they will be handed one. Every chapter starts from a document or a
decision and works back to the idea.

**Written for this market rather than the textbook one.** Standard advice
assumes stable prices and cheap credit. Followed literally here it recommends
pricing off historical cost during a devaluation, paying suppliers early, and
funding vehicles on demand facilities. The track says otherwise and explains
why.

### Things learned the hard way, worth not relearning
- **The first draft of a question bank came out 72% guessable**, 29 of 40
  answers in position B — the same defect that made four legacy tracks
  worthless. It is apparently what an author produces by default, so the
  rebalance is now part of every builder rather than a later repair.
- **Check questions duplicated exam questions in three consecutive modules.**
  Fixed by design rather than detection: checks are written scenario-first,
  exam questions computational.
- **Chapters were short in every module** and needed an extension pass every
  time. Budget for it.
- `seed_finance_track` skipped an existing track wholesale, so module 2 was
  created and never joined the track. Idempotent-by-skip is right for content
  and wrong for a module list.
- `push_closer_lessons` reads one data file despite its general-sounding use.
  `push_lessons(family=…)` is the generic one; `finance` was missing from
  `ALL_FAMILIES`, which would also have silently skipped 216 checks.

### Audit chunk G: name resolution — `audit_names.py`
Four NameErrors shipped in one day, all passing `py_compile`, three failing
silently:

| Name | Consequence |
|---|---|
| `cint` in academy_repair | bench command died on first run |
| `_nth_working_day` in accounting | quarterly review nudge has never fired |
| `json` in accounting | error-logging path would raise |
| `_on_track` in client_room | achievement screen's only upsell silently absent since built |

Chunks B and C checked that endpoints and fields resolve. Neither checked that
**names** resolve, which is cheaper than both. `audit_names.py` now does, and
self-tests against a known-bad module before believing a clean run.

**Run it before shipping any Python change:** `python3 audit_names.py`

### Still open
Everything listed in section 12 remains open — concurrency was never examined,
~40 staff-to-staff interpolations remain unescaped, `ignore_permissions` has
never been counted, and the meeting cap counts days and weeks by different
fields. Add to that: the finance track is written but has never been walked
end to end as a client, and Duty Settings still needs `academy_bank_details`,
`academy_approver`, `academy_vat_rate` and `academy_tutors` before anything can
be sold.
