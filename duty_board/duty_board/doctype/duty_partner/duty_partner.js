frappe.ui.form.on("Duty Partner", {
	refresh(frm) {
		if (frm.is_new()) return;
		const showLink = (link) => {
			if (!link) { frappe.msgprint(__("Login created, but no link could be generated — check Error Log.")); return; }
			const d = new frappe.ui.Dialog({ title: __("Send this link to the partner"), fields: [
				{ fieldtype: "Small Text", fieldname: "link", label: __("Set-password link (valid 24 hours)"), default: link, read_only: 1 },
				{ fieldtype: "HTML", fieldname: "h", options: `<p class="text-muted">${__("Paste it into WhatsApp or email. It takes them to a page to choose a password, then to their portal at /partner.")}</p>` },
			], primary_action_label: __("Copy link"), primary_action: () => { frappe.utils.copy_to_clipboard(link); d.hide(); } });
			d.show();
		};
		if (frm.doc.user) {
			frm.add_custom_button(__("Open portal as they see it"), () => window.open("/partner", "_blank"));
			frm.add_custom_button(__("New login link"), () => frappe.call({
				method: "duty_board.partners.partner_login_link", args: { name: frm.doc.name }, freeze: true,
				callback: (r) => showLink(r.message.link),
			}));
			frm.dashboard.set_headline(__("Portal login: {0}", [frm.doc.user]));
		} else {
			frm.add_custom_button(__("Invite to portal"), () => {
				frappe.confirm(__("Create a portal login for {0}? A welcome email is attempted, and you also get a link to send yourself.", [frm.doc.email]), () => {
					frappe.call({
						method: "duty_board.partners.partner_invite", args: { name: frm.doc.name }, freeze: true,
						callback: (r) => { showLink(r.message.link); frm.reload_doc(); },
					});
				});
			}).addClass("btn-primary");
		}
		frappe.call({ method: "duty_board.partners.partner_overview", callback: (r) => {
			const me = (r.message.rows || []).find((x) => x.name === frm.doc.name);
			if (me) frm.dashboard.add_indicator(__("Accrued {0} · {1} client(s) · {2} open lead(s)",
				[format_currency(me.accrued, "NGN"), me.clients.length, me.open_leads]), me.accrued ? "green" : "grey");
		} });
	},
});
