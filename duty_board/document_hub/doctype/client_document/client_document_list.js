frappe.listview_settings["Client Document"] = {
    add_fields: ["status", "checked_out_by", "current_version"],
    get_indicator(doc) {
        if (doc.status === "Checked Out") {
            const mine = doc.checked_out_by === frappe.session.user;
            return [
                mine ? __("Checked Out (You)") : __("Checked Out"),
                mine ? "blue" : "orange",
                "status,=,Checked Out",
            ];
        }
        return [__("Available"), "green", "status,=,Available"];
    },
};
