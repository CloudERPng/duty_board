# Changelog

Notable releases. Versions follow `duty_board/__init__.py`.

## v3.7.0 — Subtasks
- Duty Project Subtask child table: assignee, due (≤ card), note, status,
  linked Daily Todo; clamp-and-notify on earlier card dates; hard block on
  completing cards with open subtasks; progress-only ("N of M steps") on
  the client portal; ☑ n/m board chips; card-dialog checklist section

## v3.6.x — Project linking & CR-born tasks
- ⚖ room dialog gains a Duty Project picker (room_set_project)
- "＋ New task" in the CR detail spawns a linked To Do card
  (lazy-creating the room's requests project); Duty Project links
  display project names (title_field)

## v3.5.x — Staff CR dialog as list/detail
- Calm list rows (dot/title/tasks/pricing/status), single-stepper detail,
  contextual actions; "Price now" in-detail for the pricer; client
  approval overlay carries the full particulars incl. the original request

## v3.4.x — Client portal redesign (approved mock)
- Token skin (paper/viridian/Fraunces+Instrument Sans), SVG tab icons,
  merged service bar, "Needs your attention" queue unifying deps,
  queries, doc requests, CR approvals and deliverable sign-offs;
  named-area grid; mobile app-shell polish; offline Playwright harness
  with numeric DOM audits introduced for portal verification

## v3.3.x — Commercial layer (commercial.py)
- Client Dependency Register (staff dialog + portal "Awaiting from you",
  reminders, delay_split)
- CR pricing gate: Awaiting Pricing default, invisible to clients until
  released; sole pricer (Duty Settings) decides Priced/Covered/Goodwill/
  Rejected/Deferred; Priced = submission (status → Awaiting Approval,
  push); work blocked until covered/goodwill or priced+approved;
  invoice_status; pricing queue + notifications
- Cost-to-serve (managers): work-session hours per customer vs blended
  cost rate and known fees
- Room scope: scope_note + support_plan, portal plan banner

## v3.2.0 — Hardening release
- Central authorization module (`permissions.py`); staff guard applied to
  every endpoint in `api`, `projects`, `sales`, `dm`, and the document hub
  (71 endpoints swept); push endpoints gated to authenticated users
- Negative permission test suite: Website Users are denied on every staff
  endpoint
- Fixed `share_todo` (dead variable reference raised NameError)
- Meeting ICS times computed with real datetime arithmetic (23:00 meetings
  no longer produce hour 24)
- Clients' People list narrowed to their service team (room owner,
  bookkeeper, meeting staff, staff who have spoken in the room)
- Repo hygiene: LICENSE, SECURITY.md, CHANGELOG.md; stale release zip
  removed from source control

## v3.0.0 – v3.1.2
- Service-scoped accounting clients (Bookkeeping / Payroll & HR / Tax),
  annual deliverables, FYE-derived CIT
- Targeted follow-ups, staff file access fix, Books open to all staff,
  assignee attestation
- Meeting-confirm todo length hotfix

## v2.51 – v2.99
- Client portal architecture, issue logging, Document Hub, Academy &
  certification (Bookkeeper, Closer, Closer Manager, Consultant tracks),
  Accounting Services unit (cadence engine, attestation, close matrix,
  follow-ups, auto-invoicing with VAT, payment chase), whole-track
  assignment, weekly/monthly digests
