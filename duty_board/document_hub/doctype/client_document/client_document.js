// Client Document — form UI for check-out / check-in workflow

frappe.ui.form.on("Client Document", {
    refresh(frm) {
        if (frm.is_new()) return;

        frm.page.clear_actions_menu();

        const is_manager =
            frappe.user.has_role("System Manager") ||
            frappe.user.has_role("Duty Board Manager");

        // ---- Status banner ----
        if (frm.doc.status === "Checked Out") {
            const holder = frm.doc.checked_out_by;
            const since = frappe.datetime.comment_when(frm.doc.checked_out_at);
            const mine = holder === frappe.session.user;
            frm.dashboard.set_headline(
                mine
                    ? __("You have this checked out ({0}). Check it in when done.", [since])
                    : __("Checked out by {0} ({1}).", [
                          frappe.user.full_name(holder),
                          since,
                      ]),
                mine ? "blue" : "orange"
            );
        }

        // ---- Download latest ----
        if (frm.doc.latest_file) {
            frm.add_custom_button(__("Download Latest (v{0})", [frm.doc.current_version]), () => {
                frappe.call({
                    method: "duty_board.document_hub.doctype.client_document.client_document.log_download",
                    args: { name: frm.doc.name },
                });
                window.open(frm.doc.latest_file, "_blank");
            });
        }

        // ---- Check Out ----
        if (frm.doc.status === "Available") {
            frm.add_custom_button(__("Check Out"), () => {
                frappe.call({
                    method: "duty_board.document_hub.doctype.client_document.client_document.checkout",
                    args: { name: frm.doc.name },
                    freeze: true,
                    freeze_message: __("Checking out..."),
                    callback(r) {
                        frm.reload_doc();
                        if (r.message && r.message.file_url) {
                            window.open(r.message.file_url, "_blank");
                        }
                        frappe.show_alert({
                            message: __("Checked out. Edit locally, then Check In your new version."),
                            indicator: "green",
                        });
                    },
                });
            }).addClass("btn-primary");
        }

        // ---- Check In ----
        const can_checkin =
            frm.doc.status === "Checked Out" &&
            (frm.doc.checked_out_by === frappe.session.user || is_manager);

        if (can_checkin) {
            frm.add_custom_button(__("Check In"), () => show_checkin_dialog(frm)).addClass(
                "btn-primary"
            );
        }

        // ---- Force Release (managers only) ----
        if (
            frm.doc.status === "Checked Out" &&
            is_manager &&
            frm.doc.checked_out_by !== frappe.session.user
        ) {
            frm.add_custom_button(__("Force Release"), () => {
                frappe.prompt(
                    {
                        fieldname: "reason",
                        fieldtype: "Small Text",
                        label: __("Reason (optional)"),
                    },
                    (values) => {
                        frappe.call({
                            method: "duty_board.document_hub.doctype.client_document.client_document.force_release",
                            args: { name: frm.doc.name, reason: values.reason },
                            freeze: true,
                            callback() {
                                frm.reload_doc();
                                frappe.show_alert({
                                    message: __("Lock released."),
                                    indicator: "orange",
                                });
                            },
                        });
                    },
                    __("Force Release Document"),
                    __("Release")
                );
            });
        }

        // ---- Restore a previous version ----
        if (frm.doc.status === "Available" && (frm.doc.versions || []).length > 1) {
            frm.add_custom_button(__("Restore Version..."), () => {
                const options = (frm.doc.versions || [])
                    .filter((v) => v.version_no !== frm.doc.current_version)
                    .map((v) => `v${v.version_no} — ${v.change_note || ""}`);

                frappe.prompt(
                    {
                        fieldname: "version",
                        fieldtype: "Select",
                        label: __("Version to restore"),
                        options: options.join("\n"),
                        reqd: 1,
                    },
                    (values) => {
                        const version_no = parseInt(values.version.replace("v", ""), 10);
                        frappe.call({
                            method: "duty_board.document_hub.doctype.client_document.client_document.restore_version",
                            args: { name: frm.doc.name, version_no },
                            freeze: true,
                            callback(r) {
                                frm.reload_doc();
                                frappe.show_alert({
                                    message: __("Restored as v{0}.", [r.message.version]),
                                    indicator: "green",
                                });
                            },
                        });
                    },
                    __("Restore Previous Version"),
                    __("Restore")
                );
            });
        }

        // ---- Activity log shortcut ----
        frm.add_custom_button(__("Activity Log"), () => {
            frappe.set_route("List", "Document Activity", { document: frm.doc.name });
        });
    },
});

function show_checkin_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __("Check In — v{0}", [(frm.doc.current_version || 0) + 1]),
        fields: [
            {
                fieldname: "file",
                fieldtype: "Attach",
                label: __("Updated File"),
                reqd: 1,
            },
            {
                fieldname: "change_note",
                fieldtype: "Small Text",
                label: __("What Changed"),
                reqd: 1,
                description: __("Required. e.g. 'Updated pricing tab for 2026 rates'"),
            },
        ],
        primary_action_label: __("Check In"),
        primary_action(values) {
            frappe.call({
                method: "duty_board.document_hub.doctype.client_document.client_document.checkin",
                args: {
                    name: frm.doc.name,
                    file_url: values.file,
                    change_note: values.change_note,
                },
                freeze: true,
                freeze_message: __("Checking in..."),
                callback(r) {
                    d.hide();
                    frm.reload_doc();
                    frappe.show_alert({
                        message: __("Checked in as v{0}.", [r.message.version]),
                        indicator: "green",
                    });
                },
            });
        },
    });
    d.show();
}
