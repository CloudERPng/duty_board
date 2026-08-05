# Document Hub — Duty Board Module (v1.0)

Check-out / check-in document management for client Excel and Word deliverables.
Built as a module inside the `duty_board` app.

## What it does

- **Client Document** — one record per living document, linked to Customer, with category, status, and full version history
- **Check Out** locks the document to you; everyone else sees who has it and since when
- **Check In** requires the updated file + a mandatory change note, auto-increments the version. Old versions are never overwritten
- **Force Release** — managers (System Manager or Duty Board Manager) can break a stuck lock; the previous holder gets notified
- **Restore Version** — promotes any old version as a new version (non-destructive rollback)
- **Document Activity** — full audit trail: created, checked out/in, force released, restored, downloaded
- **Stale checkout alerts** — scheduled task pings the holder and managers when a lock exceeds 48 hours

## Installation

### 1. Copy the module into duty_board

```
apps/duty_board/duty_board/document_hub/
├── __init__.py
└── doctype/
    ├── __init__.py
    ├── client_document/
    │   ├── __init__.py
    │   ├── client_document.json
    │   ├── client_document.py
    │   ├── client_document.js
    │   └── client_document_list.js
    ├── document_version/
    │   ├── __init__.py
    │   └── document_version.json
    └── document_activity/
        ├── __init__.py
        └── document_activity.json
```

### 2. Register the module

Add to `apps/duty_board/duty_board/modules.txt`:

```
Document Hub
```

### 3. Wire the scheduler in hooks.py

Add (or merge into your existing `scheduler_events`) in `apps/duty_board/duty_board/hooks.py`:

```python
scheduler_events = {
    "hourly": [
        "duty_board.document_hub.doctype.client_document.client_document.alert_stale_checkouts",
    ],
}
```

### 4. Migrate

```bash
cd ~/frappe-bench
bench --site yoursite migrate
bench --site yoursite clear-cache
bench restart
```

### 5. Roles

The module reuses your existing **Duty Board User** role for team access.
If you want a manager tier below System Manager, create a **Duty Board Manager**
role — it automatically gets Force Release and check-in override rights
(see `FORCE_RELEASE_ROLES` in `client_document.py`).

## Duty Room integration point

Notifications currently go through the standard Notification Log (bell icon).
To also post events into the Duty Room group chat, edit `notify_team()` in
`client_document.py` — there is a marked TODO. Insert your Duty Room message
doctype creation there and every checkout/checkin/release event will land in
the chat automatically.

## Daily workflow

1. Open the Client Document list, filter by client
2. **Check Out** → latest file opens/downloads, record locks to you
3. Edit in Excel/Word locally
4. **Check In** → attach updated file + write what changed → lock released, version bumped
5. Teammate sees the new version and the note

## Notes

- Direct edits to checkout fields are blocked server-side; the buttons are the only path
- `restore_version` never deletes anything — restoring v3 when you're on v5 creates v6 with v3's file
- Files are stored as standard Frappe File attachments; set them private by default if these contain client-sensitive data (System Settings → Files, or force `is_private` in a File hook)
