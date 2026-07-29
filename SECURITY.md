# Security

## Access model

Duty Board serves two authenticated populations on one Frappe site:

- **Staff** — System Users using the desk SPA (`/app/duty-board`)
- **Clients** — Website Users using the portal (`/portal`)

Every `@frappe.whitelist()` endpoint declares its audience through
`duty_board/permissions.py`:

| Class | Guard | Examples |
|---|---|---|
| Staff only | `require_staff()` (aliased as `_staff_only()`) | board, chat, DMs, projects, sales, accounting ops, document hub |
| Any authenticated user | `require_authenticated()` | push subscription endpoints |
| Client room member | `client_room._client_room()` membership resolution | every `client_*` portal endpoint |
| Public guest | `@frappe.whitelist(allow_guest=True)`, explicit | join request, verification pages |

UI visibility is never relied upon for security: Frappe exposes all
whitelisted methods over REST to any session, and `frappe.get_all`
bypasses row permissions.

## Enforcement

`duty_board/tests/test_permissions.py` logs in as a Website User and calls
every staff endpoint in `api`, `projects`, `sales`, `dm`, and the document
hub, asserting `PermissionError` on each. Run it as part of every deploy:

```
bench --site <site> run-tests --module duty_board.tests.test_permissions
```

Any new whitelisted endpoint must add its guard first and, if not staff-only,
register itself in the test's `NON_STAFF` map with a justification.

## Reporting

Report suspected vulnerabilities privately to the Xlevel engineering lead.
Do not open public issues for security reports.
