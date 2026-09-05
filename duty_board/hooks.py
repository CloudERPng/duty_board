app_name = "duty_board"
app_title = "Duty Board"
app_publisher = "Xlevel Retail Systems Ltd"
app_description = "Simple remote-staff duty clock in/out tracker with a live status board"
app_email = "support@clouderp.one"
app_license = "MIT"

scheduler_events = {
    "daily": [
        "duty_board.accounting.scheduled_open_period",
    ],
    "cron": {
        # hourly, so each user's local midnight is caught within the hour
        "15 * * * *": ["duty_board.tasks.auto_clock_out"],
        "* * * * *": ["duty_board.reminders.fire_due"],
        # Monday 07:00 site time
        "0 6 * * 1": ["duty_board.review.scheduled_snapshot"],
        "0 7 * * 1": [
            "duty_board.tasks.weekly_digest",
            # Monday portfolio aging — the Oversight face as an email
            "duty_board.notify.weekly_aging_digest",
        ],
        # Monday 08:00 site time — weekly pulse into each client room
        "0 8 * * 1": ["duty_board.client_room.weekly_room_pulse"],
        "0 7 1 * *": ["duty_board.client_room.monthly_service_reports"],
        "0 6 * * *": ["duty_board.projects.run_recurring"],
        "30 9 * * 1-5": ["duty_board.accounting.books_client_chase"],
        "0 18 * * 1-5": [
            "duty_board.accounting.books_evening_digest",
            # tickets nobody has opened at all — distinct from the stale ladder,
            # which measures silence after somebody has engaged
            "duty_board.notify.unacknowledged_sweep",
        ],
        # second-day escalation: past 48h the assignee has had four reminders,
        # so it goes above them, once per ticket, ever
        "0 9 * * 1-5": ["duty_board.notify.escalate_silent_issues"],
        "0 7 28 * *": ["duty_board.accounting.scheduled_generate_invoices"],
        # 1st of the month: books that have come due for another pass. Monthly
        # rather than daily on purpose — a revisit is never urgent, and a nudge
        # frequent enough to be ignored is worse than none at all.
        "0 8 1 * *": ["duty_board.library.revisit_nudge"],
        # the month just gone, judged and put away before anyone looks at the new one
        "30 5 1 * *": ["duty_board.review.scheduled_close"],
        # NGX closes at 16:00 WAT; this runs after it, weekdays only. It emails
        # only when a ticker fails to price — a working fetcher stays quiet.
        "30 16 * * 1-5": ["duty_board.shares.scheduled_fetch_prices"],
        # the market tape: twice on weekdays, mid-session and after the close.
        # The source updates daily, so hourly would be eight requests for the
        # same numbers — and the strip carries its own timestamp anyway.
        "0 13,17 * * 1-5": ["duty_board.shares.scheduled_fetch_tape"],
        # standing orders post themselves, because they run at the bank whether
        # or not anybody opens this — the ledger mirrors reality rather than
        # waiting to be told
        "0 6 * * *": ["duty_board.money.run_due_standing_orders"],
        # then the shortfall watch, after the day's postings have landed
        "0 7 * * *": ["duty_board.money.shortfall_watch"],
    },
    "hourly": [
        "duty_board.document_hub.doctype.client_document.client_document.alert_stale_checkouts",
        "duty_board.client_room.meeting_reminders",
        "duty_board.api.sla_warnings",
    ],
}

doc_events = {
    "Daily Todo": {
        "on_update": "duty_board.projects.on_todo_update",
        "on_trash": "duty_board.projects.on_todo_trash",
    },
    "Communication": {
        "after_insert": "duty_board.accounting.handle_communication",
    },
}
