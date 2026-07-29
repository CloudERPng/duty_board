# Changelog

Notable releases. Versions follow `duty_board/__init__.py`.

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
