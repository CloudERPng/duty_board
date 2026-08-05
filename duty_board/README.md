# Duty Board

A minimal Frappe/ERPNext app for remote teams: staff clock in when they start the day,
clock out (with a reason) whenever they step away, and clock back in when they return.
A single live board shows who is On Duty, Away, or Off Duty at a glance, and a script
report gives per-day hours.

## What's inside

| Piece | Name | Purpose |
|---|---|---|
| DocType | **Duty Log** | One row per clock in/out event (user, type, time, reason) |
| Page | **Duty Board** (`/app/duty-board`) | Big Clock In / Clock Out button + live team status grid, auto-refreshes every 60s |
| Report | **Daily Duty Summary** | Per staff per day: first in, last out, breaks, total hours on duty |

## Install

```bash
cd ~/frappe-bench
bench get-app /path/to/duty_board        # or push to git and: bench get-app <repo-url>
bench --site yoursite.clouderp.one install-app duty_board
bench --site yoursite.clouderp.one migrate
bench build --app duty_board
bench restart
```

Works on Frappe/ERPNext v14 and v15. No dependency on the HR module — it links to
**User**, so any enabled System User appears on the board automatically.

## Daily flow for staff

1. Open **Duty Board** (type "Duty Board" in the awesomebar, or bookmark `/app/duty-board`).
2. Tap **Clock In** to start the day.
3. Stepping away? Tap **Clock Out** and pick a reason (Lunch, Power outage, Errand, ... or **End of day**).
4. Back at your desk? Tap **Clock In** again.

## For the manager

- The same **Duty Board** page shows everyone: green = On Duty, amber = Away (with reason),
  blue = Done for the Day, grey = not clocked in.
- **Daily Duty Summary** report gives hours per person per day, exportable to Excel.
- Only System Managers can edit or back-date Duty Logs; staff entries are always
  timestamped server-side and can only be created for themselves.

## Notes

- Board shows all enabled System Users except Administrator. To hide service accounts,
  disable them or change the filter in `duty_board/api.py` → `get_board()`.
- The "End of day" reason is treated as ending the day (not counted as a break).
