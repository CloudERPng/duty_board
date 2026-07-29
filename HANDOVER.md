# Duty Board — Handover Brief · v3.7.0

**App:** `duty_board` on Frappe/ERPNext v15 · **Live site:** `xlevel.clouderp.one`
**Repo:** https://github.com/CloudERPng/duty_board · **Bench:** `bench@newv15`, `~/frappe-bench`
**Last brief:** v2.90.0. This one covers everything through v3.7.0 (span: v2.91.0 → v3.7.0, ~45 releases).

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
