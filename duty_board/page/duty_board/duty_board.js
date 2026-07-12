frappe.pages["duty-board"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Duty Board"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), () => board.refresh(), "refresh");
	page.add_menu_item(__("Time Report"), () =>
		frappe.set_route("query-report", "Daily Duty Summary")
	);
	page.add_menu_item(__("Work Sessions Report"), () =>
		frappe.set_route("query-report", "Work Sessions")
	);
	page.add_menu_item(__("Duty Log List"), () => frappe.set_route("List", "Duty Log"));

	const board = new DutyBoard(page);
	board.refresh();

	board.timer = setInterval(() => {
		if (frappe.get_route_str() === "duty-board") board.refresh(true);
	}, 60 * 1000);
};

class DutyBoard {
	constructor(page) {
		this.page = page;
		this.body = $(`
			<div class="duty-board">
				<div class="duty-me"></div>
				<div class="duty-task"></div>
				<div class="duty-my-sessions"></div>
				<div class="duty-team-title">${__("Team — Today")}</div>
				<div class="duty-team"></div>
				<div class="duty-updated text-muted"></div>
			</div>
		`).appendTo(page.body);
		this.inject_style();
	}

	refresh(silent) {
		frappe.call({
			method: "duty_board.api.get_board",
			freeze: !silent,
			callback: (r) => r.message && this.render(r.message),
		});
	}

	action(method, args) {
		frappe.call({
			method: `duty_board.api.${method}`,
			args: args || {},
			freeze: true,
			freeze_message: __("Saving..."),
			callback: (r) => r.message && this.render(r.message),
		});
	}

	clock_out_dialog() {
		const d = new frappe.ui.Dialog({
			title: __("Clock Out"),
			fields: [
				{
					fieldname: "reason",
					fieldtype: "Select",
					label: __("Reason"),
					reqd: 1,
					options: [
						"Lunch",
						"Gone for prayers",
						"Short break",
						"Errand",
						"Power outage",
						"Internet outage",
						"Offline meeting",
						"Personal",
						"End of day",
					].join("\n"),
				},
				{
					fieldname: "details",
					fieldtype: "Data",
					label: __("Details (optional)"),
				},
			],
			primary_action_label: __("Clock Out"),
			primary_action: (values) => {
				d.hide();
				let reason = values.reason;
				if (values.details && values.reason !== "End of day") {
					reason = `${values.reason} — ${values.details}`;
				}
				this.action("clock_out", { reason: reason });
			},
		});
		d.show();
	}

	start_task_dialog(switching) {
		const d = new frappe.ui.Dialog({
			title: switching ? __("Switch Task") : __("Start Task"),
			fields: [
				{
					fieldname: "activity",
					fieldtype: "Data",
					label: __("What are you working on?"),
					reqd: 1,
				},
				{
					fieldname: "customer",
					fieldtype: "Link",
					label: __("Customer (optional)"),
					options: "Customer",
				},
			],
			primary_action_label: __("Start Timer"),
			primary_action: (values) => {
				d.hide();
				this.action("start_task", {
					activity: values.activity,
					customer: values.customer || null,
				});
			},
		});
		d.show();
	}

	render(data) {
		this.render_me(data.me);
		this.render_task(data.me);
		this.render_my_sessions(data.my_sessions, data.me);
		this.render_team(data.board);
		this.body
			.find(".duty-updated")
			.text(__("Last updated {0}", [frappe.datetime.now_time()]));
	}

	render_me(me) {
		const $me = this.body.find(".duty-me").empty();
		if (!me) {
			$me.html(`<div class="text-muted">${__("Your user is not on the board.")}</div>`);
			return;
		}
		const s = this.status_meta(me.status);
		const on_duty = me.status === "On Duty";
		$me.html(`
			<div class="duty-me-card">
				<div>
					<div class="duty-me-status">
						<span class="duty-dot" style="background:${s.color}"></span>
						${__("You are")} <b style="color:${s.color}">${__(me.status)}</b>
						${me.reason ? `<span class="text-muted">· ${frappe.utils.escape_html(me.reason)}</span>` : ""}
					</div>
					<div class="duty-me-sub text-muted">
						${__("On duty today")}: <b>${this.fmt_duration(me.on_duty_seconds)}</b>
						${me.since ? " · " + __("Since") + " " + this.fmt_time(me.since) : ""}
					</div>
				</div>
				<button class="btn btn-lg ${on_duty ? "btn-danger" : "btn-success"} duty-main-btn">
					${on_duty ? __("Clock Out") : __("Clock In")}
				</button>
			</div>
		`);
		$me.find(".duty-main-btn").on("click", () => {
			on_duty ? this.clock_out_dialog() : this.action("clock_in");
		});
	}

	render_task(me) {
		const $task = this.body.find(".duty-task").empty();
		if (!me || me.status !== "On Duty") return;

		if (me.task) {
			const t = me.task;
			$task.html(`
				<div class="duty-task-card duty-task-running">
					<div class="duty-task-info">
						<div class="duty-task-label">${__("Working on")}</div>
						<div class="duty-task-name">
							${frappe.utils.escape_html(t.activity)}
							${t.customer ? `<span class="duty-task-customer">${frappe.utils.escape_html(t.customer)}</span>` : ""}
						</div>
						<div class="text-muted duty-task-since">
							${__("Running")}: <b>${this.fmt_duration(t.seconds)}</b>
							· ${__("Started")} ${this.fmt_time(t.start_time)}
						</div>
					</div>
					<div class="duty-task-actions">
						<button class="btn btn-default duty-switch-btn">${__("Switch Task")}</button>
						<button class="btn btn-primary duty-stop-btn">${__("Stop")}</button>
					</div>
				</div>
			`);
			$task.find(".duty-stop-btn").on("click", () => this.action("stop_task"));
			$task.find(".duty-switch-btn").on("click", () => this.start_task_dialog(true));
		} else {
			$task.html(`
				<div class="duty-task-card">
					<div class="duty-task-info text-muted">${__("No task running. What are you working on?")}</div>
					<button class="btn btn-primary duty-start-btn">${__("Start Task")}</button>
				</div>
			`);
			$task.find(".duty-start-btn").on("click", () => this.start_task_dialog(false));
		}
	}

	render_my_sessions(sessions, me) {
		const $s = this.body.find(".duty-my-sessions").empty();
		if (!me || !sessions || !sessions.length) return;
		const rows = sessions
			.map(
				(x) => `
				<div class="duty-session-row ${!x.end_time ? "duty-session-live" : ""}">
					<span class="duty-session-activity">${frappe.utils.escape_html(x.activity)}</span>
					${x.customer ? `<span class="duty-task-customer">${frappe.utils.escape_html(x.customer)}</span>` : ""}
					<span class="duty-session-time text-muted">
						${this.fmt_time(x.start_time)} – ${x.end_time ? this.fmt_time(x.end_time) : __("now")}
						· ${this.fmt_duration(x.duration)}
					</span>
				</div>`
			)
			.join("");
		$s.html(`
			<details class="duty-sessions-details">
				<summary>${__("My tasks today")} (${sessions.length})</summary>
				${rows}
			</details>
		`);
	}

	render_team(rows) {
		const $team = this.body.find(".duty-team").empty();
		if (!rows || !rows.length) {
			$team.html(`<div class="text-muted">${__("No staff found.")}</div>`);
			return;
		}
		rows.forEach((r) => {
			const s = this.status_meta(r.status);
			$team.append(`
				<div class="duty-card">
					<div class="duty-card-head">
						${frappe.avatar(r.user, "avatar-medium")}
						<div class="duty-card-name">
							<div class="duty-name">${frappe.utils.escape_html(r.full_name)}</div>
							<div class="duty-badge" style="color:${s.color};background:${s.bg}">
								<span class="duty-dot" style="background:${s.color}"></span>${__(r.status)}
							</div>
						</div>
					</div>
					<div class="duty-card-body text-muted">
						${
							r.task
								? `<div class="duty-card-task">▸ ${frappe.utils.escape_html(r.task.activity)}${
										r.task.customer
											? ` <span class="duty-task-customer">${frappe.utils.escape_html(r.task.customer)}</span>`
											: ""
								  } <span class="text-muted">(${this.fmt_duration(r.task.seconds)})</span></div>`
								: ""
						}
						${r.reason && r.status === "Away" ? `<div class="duty-reason">${frappe.utils.escape_html(r.reason)}</div>` : ""}
						${r.since ? `<div>${__("Since")} ${this.fmt_time(r.since)}</div>` : `<div>${__("Not clocked in today")}</div>`}
						<div>${__("On duty")}: ${this.fmt_duration(r.on_duty_seconds)}${r.breaks ? " · " + __("Breaks") + ": " + r.breaks : ""}</div>
					</div>
				</div>
			`);
		});
	}

	status_meta(status) {
		return (
			{
				"On Duty": { color: "var(--green-600, #2e7d32)", bg: "var(--green-100, #e8f5e9)" },
				Away: { color: "var(--orange-600, #ef6c00)", bg: "var(--orange-100, #fff3e0)" },
				"Done for the Day": { color: "var(--blue-600, #1565c0)", bg: "var(--blue-100, #e3f2fd)" },
				"Off Duty": { color: "var(--gray-600, #757575)", bg: "var(--gray-100, #f5f5f5)" },
			}[status] || { color: "var(--gray-600)", bg: "var(--gray-100)" }
		);
	}

	fmt_time(dt) {
		return frappe.datetime.str_to_user(dt).split(" ").slice(1).join(" ") || dt;
	}

	fmt_duration(seconds) {
		if (!seconds) return "0m";
		const h = Math.floor(seconds / 3600);
		const m = Math.round((seconds % 3600) / 60);
		return h ? `${h}h ${m}m` : `${m}m`;
	}

	inject_style() {
		if ($("#duty-board-style").length) return;
		$(`<style id="duty-board-style">
			.duty-board { padding: var(--padding-md) 0; }
			.duty-me-card {
				display: flex; justify-content: space-between; align-items: center; gap: 16px;
				padding: 20px; border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg, 10px); background: var(--card-bg);
				flex-wrap: wrap;
			}
			.duty-me-status { font-size: var(--text-lg); }
			.duty-me-sub { margin-top: 4px; }
			.duty-main-btn { min-width: 160px; }
			.duty-task-card {
				display: flex; justify-content: space-between; align-items: center; gap: 16px;
				margin-top: 10px; padding: 14px 20px; border: 1px dashed var(--border-color);
				border-radius: var(--border-radius-lg, 10px); background: var(--card-bg);
				flex-wrap: wrap;
			}
			.duty-task-running { border-style: solid; border-color: var(--green-500, #4caf50); }
			.duty-task-label {
				font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em;
				color: var(--text-muted); font-weight: 600;
			}
			.duty-task-name { font-size: var(--text-base); font-weight: 600; margin: 2px 0; }
			.duty-task-customer {
				display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 99px;
				background: var(--bg-purple, #f3e8fd); color: var(--purple-600, #6b21a8);
				font-size: var(--text-xs); font-weight: 600;
			}
			.duty-task-actions { display: flex; gap: 8px; }
			.duty-sessions-details { margin-top: 8px; font-size: var(--text-sm); }
			.duty-sessions-details summary { cursor: pointer; color: var(--text-muted); }
			.duty-session-row { padding: 6px 4px; border-bottom: 1px solid var(--border-color); }
			.duty-session-live .duty-session-activity { font-weight: 600; }
			.duty-session-time { margin-left: 8px; }
			.duty-team-title {
				margin: 24px 0 10px; font-weight: 600; color: var(--text-muted);
				text-transform: uppercase; letter-spacing: 0.04em; font-size: var(--text-sm);
			}
			.duty-team {
				display: grid; gap: 12px;
				grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
			}
			.duty-card {
				border: 1px solid var(--border-color); border-radius: var(--border-radius-lg, 10px);
				padding: 14px; background: var(--card-bg);
			}
			.duty-card-head { display: flex; align-items: center; gap: 10px; }
			.duty-name { font-weight: 600; }
			.duty-badge {
				display: inline-flex; align-items: center; gap: 5px; margin-top: 3px;
				font-size: var(--text-xs); font-weight: 600; padding: 2px 8px; border-radius: 99px;
			}
			.duty-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
			.duty-card-body { margin-top: 10px; font-size: var(--text-sm); line-height: 1.6; }
			.duty-card-task { color: var(--text-color); font-weight: 500; }
			.duty-reason { font-style: italic; }
			.duty-updated { margin-top: 16px; font-size: var(--text-xs); }
		</style>`).appendTo("head");
	}
}
