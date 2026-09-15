frappe.ui.form.on("Duty Partner Statement", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Issued") return;
		frm.add_custom_button(__("Mark as paid"), () => {
			frappe.prompt([
				{ fieldname: "paid_on", fieldtype: "Date", label: __("Paid on"), reqd: 1, default: frappe.datetime.get_today() },
				{ fieldname: "ref", fieldtype: "Data", label: __("Payment reference") },
			], (v) => frappe.call({
				method: "duty_board.partners.statement_mark_paid",
				args: { name: frm.doc.name, paid_on: v.paid_on, reference: v.ref || null }, freeze: true,
				callback: () => frm.reload_doc(),
			}), __("Record payment of {0}", [format_currency(frm.doc.net_payable, "NGN")]), __("Mark paid"));
		}).addClass("btn-primary");
	},
});
