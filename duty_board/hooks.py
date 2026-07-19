app_name = "duty_board"
app_title = "Duty Board"
app_publisher = "Xlevel Retail Systems Ltd"
app_description = "Simple remote-staff duty clock in/out tracker with a live status board"
app_email = "support@clouderp.one"
app_license = "MIT"

scheduler_events = {
	"cron": {
		# hourly, so each user's local midnight is caught within the hour
		"15 * * * *": ["duty_board.tasks.auto_clock_out"],
		# Monday 07:00 site time
		"0 7 * * 1": ["duty_board.tasks.weekly_digest"],
                # Monday 08:00 site time — weekly pulse into each client room
                "0 8 * * 1": ["duty_board.client_room.weekly_room_pulse"],
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
	}
}
