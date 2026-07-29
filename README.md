# Duty Board — Xlevel Service Delivery Platform

A Frappe/ERPNext v15 app that runs Xlevel's service-delivery operation end to
end: staff attendance and daily planning, team chat and DMs, project boards,
support issues with SLAs, client collaboration rooms, a controlled document
hub, a training academy with certification tracks, and a full accounting-
services unit — one connected workflow from client request to delivered,
attested, invoiced work.

**One relationship, one thread:** client request → issue/task → assigned
consultant → tracked work session → client-visible progress → resolution →
SLA/RCA → report → acknowledgement → invoice.

## Surfaces

| Surface | Route | Audience |
|---|---|---|
| Staff SPA | `/app/duty-board` | System Users — board, plan, chat, projects, clients, Books, academy |
| Client portal | `/portal` | Website Users — room, deliverables, follow-ups, documents, meetings, training |
| Join flow | portal join/verify pages | Guests — request access, staff approve |

Installable on mobile via Add to Home Screen (PWA manifest + service worker +
web push included).

## Modules

- **Attendance & plan** — server-side clock in/out, work sessions, Daily
  Todos synced two-way with project tasks, weekly digests
- **Projects** — boards, cards, milestones with client approval, change
  requests
- **Support** — issues, SLA warnings, RCA, knowledge base
- **Client rooms** — the staff↔client membrane: messaging with an internal
  side, document shelves, meetings with ICS invites, metrics, renewals
- **Document Hub** — check-out/check-in, immutable versions, stale-lock
  alerts
- **Academy** — training modules, question banks, certification tracks
  (staff and client audiences), certificates
- **Accounting Services** — client cadence matrix by service line
  (Bookkeeping / Payroll & HR / Tax), daily attestation, statutory and
  annual deliverables, follow-ups, auto-invoicing with VAT, payment chase,
  profitability and KPIs

## Security model

See [SECURITY.md](SECURITY.md). Every whitelisted endpoint declares its
audience via `duty_board/permissions.py`; negative permission tests enforce
that portal users are denied on all staff endpoints:

```bash
bench --site <site> run-tests --module duty_board.tests.test_permissions
```

## Install

```bash
cd ~/frappe-bench
bench get-app https://github.com/CloudERPng/duty_board.git
bench --site <site> install-app duty_board
bench --site <site> migrate && bench build --app duty_board
```

Scheduler jobs (digests, chase, invoicing, SLA warnings) are declared in
`hooks.py`; a server-side cron review after install is recommended.

## License

MIT — see [LICENSE](LICENSE).
