frappe.listview_settings["Client Document"] = {
    add_fields: [
        "status", "checked_out_by", "current_version",
        "is_financial_statement", "review_status", "approved_version", "publish_seq",
    ],
    get_indicator(doc) {
        if (doc.status === "Checked Out") {
            const mine = doc.checked_out_by === frappe.session.user;
            return [
                mine ? __("Checked Out (You)") : __("Checked Out"),
                mine ? "blue" : "orange",
                "status,=,Checked Out",
            ];
        }
        if (doc.is_financial_statement && doc.review_status === "Changes Requested") {
            return [__("Changes Requested"), "orange", "review_status,=,Changes Requested"];
        }
        if (doc.is_financial_statement && doc.review_status === "Approved") {
            const current = Number(doc.approved_version || 0) === Number(doc.publish_seq || 1);
            return current
                ? [__("✔ Client Approved"), "green", "review_status,=,Approved"]
                : [__("Approved (stale)"), "orange", "review_status,=,Approved"];
        }
        if (doc.is_financial_statement && doc.review_status === "Awaiting Client Review") {
            return [__("Awaiting Client Review"), "blue", "review_status,=,Awaiting Client Review"];
        }
        return [__("Available"), "green", "status,=,Available"];
    },
};
