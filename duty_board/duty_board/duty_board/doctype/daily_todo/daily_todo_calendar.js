frappe.views.calendar["Daily Todo"] = {
	field_map: {
		start: "start",
		end: "end",
		id: "id",
		title: "title",
		allDay: "allDay",
		color: "color",
	},
	order_by: "date",
	get_events_method:
		"duty_board.duty_board.doctype.daily_todo.daily_todo.get_events",
	filters: [
		{
			fieldtype: "Link",
			fieldname: "user",
			options: "User",
			label: __("User"),
		},
		{
			fieldtype: "Link",
			fieldname: "customer",
			options: "Customer",
			label: __("Customer"),
		},
		{
			fieldtype: "Select",
			fieldname: "status",
			options: "\nOpen\nDone",
			label: __("Status"),
		},
	],
};
