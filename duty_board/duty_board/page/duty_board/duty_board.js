frappe.pages["duty-board"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Duty Board"),
		single_column: true,
	});

	page.set_secondary_action(__("Refresh"), () => board.refresh(), "refresh");
	page.add_menu_item(__("Plan Calendar"), () =>
		frappe.set_route("List", "Daily Todo", "Calendar")
	);
	page.add_menu_item(__("Time Report"), () =>
		frappe.set_route("query-report", "Daily Duty Summary")
	);
	page.add_menu_item(__("Work Sessions Report"), () =>
		frappe.set_route("query-report", "Work Sessions")
	);
	page.add_menu_item(__("Duty Log List"), () => frappe.set_route("List", "Duty Log"));

	const board = new DutyBoard(page);
	board.refresh();

	board.face_btn = null;
	board.sales_btn = null;
	page.add_inner_button(__("🏠 Board"), () => board.show_face("board"), __("⇄ View"));
	page.add_inner_button(__("📁 Projects"), () => board.show_face("projects"), __("⇄ View"));
	page.add_inner_button(__("💼 Sales"), () => board.show_face("sales"), __("⇄ View"));
	page.add_inner_button(__("🤝 Clients"), () => board.show_face("clients"), __("⇄ View"));
	page.add_inner_button(__("📄 Document Hub"), () => frappe.set_route("List", "Client Document"));

	board.timer = setInterval(() => {
		if (board._halted) return;
		if (frappe.get_route_str() !== "duty-board") return;
		if (board.face === "projects") board.refresh_projects(true);
		else if (board.face === "sales") board.refresh_sales(true);
		else if (board.face === "clients") board.refresh_clients(true);
		else board.refresh(true);
	}, 60 * 1000);
	board.main_timer = board.timer;
};

class DutyBoard {
	constructor(page) {
		this.page = page;
		this.body = $(`
			<div class="duty-board duty-layout">
				<div class="duty-left">
					<div class="duty-issues"></div>
					<div class="duty-issues-rail" style="display:none" title="${__("Open Issues")}">
						<span class="duty-rail-badge duty-issues-rail-badge" style="display:none"></span>
						<span class="duty-rail-label">⚠ ${__("Issues")}</span>
					</div>
				</div>
				<div class="duty-main">
					<div class="duty-me"></div>
					<div class="duty-task"></div>
					<div class="duty-plan"></div>
					<div class="duty-my-sessions"></div>
					<div class="duty-team-title">${__("Team — Today")}</div>
					<div class="duty-team"></div>
					<div class="duty-updated text-muted"></div>
				</div>
				<div class="duty-side">
					<div class="duty-chat"></div>
					<div class="duty-chat-rail" style="display:none" title="${__("Open Duty Room")}">
						<span class="duty-rail-badge" style="display:none"></span>
						<span class="duty-rail-label">💬 ${__("Duty Room")}</span>
					</div>
				</div>
			</div>
		`).appendTo(page.body);
		this.face = "board";
		this.$projects = $(`
			<div class="duty-projects" style="display:none">
				<div class="duty-proj-head">
					<div class="duty-proj-tabs"></div>
					<button class="btn btn-sm btn-default duty-proj-new">＋ ${__("New Project")}</button>
				</div>
				<div class="duty-kanban-wrap"></div>
			</div>
		`).appendTo(page.body);
		this.$projects.find(".duty-proj-new").on("click", () => this.new_project_dialog());
		this.$sales = $(`
			<div class="duty-sales" style="display:none">
				<div class="duty-sales-head">
					<div class="duty-sales-total"></div>
					<div class="duty-sales-actions">
						<a class="duty-sales-arch" data-outcome="Won">🏆 ${__("Won")}</a>
						<a class="duty-sales-arch" data-outcome="Lost">✖ ${__("Lost")}</a>
						<button class="btn btn-sm btn-primary duty-lead-new">＋ ${__("New Lead")}</button>
					</div>
				</div>
				<div class="duty-sales-wrap"></div>
			</div>
		`).appendTo(page.body);
		this.$sales.find(".duty-lead-new").on("click", () => this.new_lead_dialog());
		this.$sales.find(".duty-sales-arch").on("click", (e) =>
			this.closed_leads_dialog($(e.currentTarget).data("outcome"))
		);
		this.$clients = $(`
			<div class="duty-clients" style="display:none">
				<div class="duty-cr-list"></div>
				<div class="duty-cr-room" style="display:none"></div>
			</div>
		`).appendTo(page.body);
		this.name_map = {};
		this.inject_style();
		this.setup_pwa();
		this.init_chat();
		this.setup_mobile_tabs();
		document.addEventListener(
			"click",
			(e) => {
				const btn = e.target.closest && e.target.closest(".duty-dm-btn");
				if (!btn) return;
				e.preventDefault();
				e.stopPropagation();
				this.open_dm($(btn).data("user"), $(btn).data("name"));
			},
			true
		);
	}

	// ---------------- Team chat ----------------

	init_chat() {
		this.unread = 0;
		this.base_title = document.title;
		this._mentions = [];
		this._reply = null;
		this._file = null;
		const $c = this.body.find(".duty-chat");
		$c.html(`
			<div class="duty-chat-card">
				<div class="duty-chat-head">
					<span>💬 ${__("Duty Room")} <span class="duty-chat-badge" style="display:none"></span></span>
					<span class="duty-chat-tools">
						<a class="duty-chat-notif" style="display:none">${__("Enable notifications")}</a>
						<a class="duty-chat-search-toggle" title="${__("Search messages")}">🔍</a>
						<a class="duty-chat-collapse" title="${__("Collapse")}">»</a>
					</span>
				</div>
				<div class="duty-search-bar" style="display:none">
					<input type="text" class="form-control input-sm duty-search-input" placeholder="${__("Search messages...")}">
					<a class="duty-search-close">×</a>
				</div>
				<div class="duty-search-notice" style="display:none"></div>
				<div class="duty-chat-list"></div>
				<div class="duty-reply-bar" style="display:none"></div>
				<div class="duty-attach-bar" style="display:none"></div>
				<div class="duty-chat-send">
					<label class="btn btn-default btn-sm duty-attach-btn" title="${__("Attach file, image or video (max 25 MB)")}">📎<input type="file" class="duty-file-input" hidden></label>
					<div class="duty-chat-input-wrap">
						<textarea rows="1" class="form-control duty-chat-input" maxlength="1000"
							placeholder="${__("Message the team — @ to mention, Shift+Enter for a new line...")}"></textarea>
						<div class="duty-mention-menu" style="display:none"></div>
					</div>
					<button class="btn btn-primary btn-sm duty-chat-btn">${__("Send")}</button>
				</div>
			</div>
		`);

		this.$chat = $c.find(".duty-chat-card");
		this.$rail = this.body.find(".duty-chat-rail");
		this.chat_open = localStorage.getItem("duty_chat_open") !== "0";
		if (this.is_mobile()) this.chat_open = true;
		this.last_seen = localStorage.getItem("duty_chat_seen") || "";
		this.apply_chat_state();
		$c.find(".duty-chat-collapse").on("click", () => this.toggle_chat(false));
		this.$rail.on("click", () => this.toggle_chat(true));
		this.$list = $c.find(".duty-chat-list");
		this.$badge = $c.find(".duty-chat-badge");
		this.$input = $c.find(".duty-chat-input");
		this.$mmenu = $c.find(".duty-mention-menu");
		this.$replybar = $c.find(".duty-reply-bar");
		this.$attachbar = $c.find(".duty-attach-bar");

		this.seen_map = {};
		this.load_messages();

		frappe.realtime.on("duty_board_seen", (d) => {
			if (d && d.user) {
				this.seen_map[d.user] = d.last_seen;
				this.update_receipts();
			}
		});
		frappe.realtime.on("duty_board_reaction", (d) => {
			if (!d || !d.message) return;
			const $row = this.$list.find(`.duty-msg[data-name="${d.message}"]`);
			if ($row.length) this.render_reactions($row, d.reactions || {}, d.message);
		});

		$c.find(".duty-chat-search-toggle").on("click", () => {
			$c.find(".duty-search-bar").toggle();
			$c.find(".duty-search-input").focus();
		});
		$c.find(".duty-search-close").on("click", () => {
			$c.find(".duty-search-bar").hide();
			$c.find(".duty-search-input").val("");
			this.exit_search();
		});
		$c.find(".duty-search-input").on("keydown", (e) => {
			if (e.key === "Enter") this.run_search($c.find(".duty-search-input").val());
			if (e.key === "Escape") $c.find(".duty-search-close").click();
		});

		frappe.realtime.on("duty_board_message", (m) => this.handle_incoming(m));
		this._sync_timer = setInterval(() => this.sync_messages(), 25 * 1000);
		frappe.realtime.on("duty_board_notify", (d) => this.notify_event(d));
		frappe.realtime.on("duty_board_dm", (m) => this.handle_dm(m));
		frappe.realtime.on("duty_client_room", (n) => {
			if (n && n.room && this._open_room === n.room) this.load_client_room(n.room);
			else if (this.face === "clients") this.refresh_clients(true);
		});
		frappe.realtime.on("duty_board_note", (n) => {
			if (!n || !n.id) return;
			if (n.kind === "card" && this._open_card_ctx && this._open_card_ctx.id === n.id) {
				frappe.call({
					method: "duty_board.projects.get_card",
					args: { name: n.id },
					callback: (r) => {
						const ctx = this._open_card_ctx;
						if (r.message && ctx && ctx.id === n.id) this.update_notes(ctx.$x, r.message.notes);
					},
				});
			}
			if (n.kind === "lead" && this._open_lead_ctx && this._open_lead_ctx.id === n.id) {
				frappe.call({
					method: "duty_board.sales.get_lead",
					args: { name: n.id },
					callback: (r) => {
						const ctx = this._open_lead_ctx;
						if (r.message && ctx && ctx.id === n.id) this.update_notes(ctx.$x, r.message.notes);
					},
				});
			}
		});
		frappe.realtime.on("duty_board_message_deleted", (d) => {
			if (d && d.name) {
				this.$list.find(`.duty-msg[data-name="${d.name}"]`).fadeOut(200, function () {
					$(this).remove();
				});
			}
		});
		this._due_timer = setInterval(() => this.check_due_todos(), 30 * 1000);

		$c.find(".duty-chat-btn").on("click", () => this.send_chat());
		this.$input.on("keydown", (e) => {
			if (this.$mmenu.is(":visible")) {
				if (e.key === "Enter" || e.key === "Tab") {
					e.preventDefault();
					const $a = this.$mmenu.find(".active");
					this.pick_mention(($a.length ? $a : this.$mmenu.children().first()).data("user"));
					return;
				}
				if (e.key === "ArrowDown" || e.key === "ArrowUp") {
					e.preventDefault();
					this.move_mention(e.key === "ArrowDown" ? 1 : -1);
					return;
				}
				if (e.key === "Escape") {
					this.$mmenu.hide();
					return;
				}
			}
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				this.send_chat();
			}
		});
		this.$input.on("input click", () => this.update_mention_menu());
		this.$input.on("input", () => this.autosize_input());
		this.$input.on("paste", (e) => {
			const items = (e.originalEvent.clipboardData || {}).items || [];
			for (const it of items) {
				if (it.kind === "file") {
					const f = it.getAsFile();
					if (f) {
						e.preventDefault();
						this.set_file(f);
						break;
					}
				}
			}
		});
		$c.find(".duty-file-input").on("change", (e) => {
			if (e.target.files[0]) this.set_file(e.target.files[0]);
			e.target.value = "";
		});

		document.addEventListener("visibilitychange", () => {
			if (!document.hidden && this.chat_open && (!this.is_mobile() || this.mtab === "chat")) {
				this.mark_caught_up();
			}
		});

		const $notif = $c.find(".duty-chat-notif");
		if (window.Notification && Notification.permission === "default") {
			$notif.show().on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				Notification.requestPermission().then(() => {
					$notif.hide();
					if (this._sw) this.maybe_subscribe_push(this._sw);
				});
			});
		}
	}

	notify_event(d) {
		if (!d || !d.title) return;
		frappe.show_alert(
			{
				message: `<b>${frappe.utils.escape_html(d.title)}</b><br>${frappe.utils.escape_html(d.body || "")}`,
				indicator: "blue",
			},
			8
		);
		this.ping();
		if (window.Notification && Notification.permission === "granted") {
			try {
				new Notification(d.title, {
					body: d.body || "",
					tag: "duty-notify",
					renotify: true,
				});
			} catch (e) {
				/* ignore */
			}
		}
		this.refresh(true);
	}

	check_due_todos() {
		if (this._halted) return;
		if (frappe.get_route_str() !== "duty-board") return;
		this._due_alerted = this._due_alerted || {};
		const now = new Date();
		(this.my_todos || []).forEach((t) => {
			if (t.status !== "Open" || !t.due_time || this._due_alerted[t.name]) return;
			const parts = t.due_time.split(":");
			const due = new Date();
			due.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
			const mins = (due - now) / 60000;
			if (mins > 0 && mins <= 5) {
				this._due_alerted[t.name] = true;
				this.notify_event({
					title: __("Starting in {0} min", [Math.ceil(mins)]),
					body: t.description,
				});
			}
		});
	}

	touch_issues() {
		this._issues_alt = null;
		this._issues_alt_scope = null;
		this.refresh(true);
	}

	check_overdue_issues(issues) {
		const today = frappe.datetime.get_today();
		if (localStorage.getItem("duty_overdue_day") === today) return;
		const mine = (issues || []).filter(
			(x) => this.issue_is_mine(x) && x.due_date && x.due_date < today
		);
		if (!mine.length) return;
		localStorage.setItem("duty_overdue_day", today);
		const titles = mine
			.slice(0, 3)
			.map((x) => x.title)
			.join(" · ");
		this.notify_event({
			title: __("{0} of your issue(s) are overdue", [mine.length]),
			body: titles + (mine.length > 3 ? " …" : ""),
		});
	}

	user_color(user) {
		const palette = [
			"#0E7490", "#B45309", "#6D28D9", "#BE185D", "#15803D", "#B91C1C",
			"#1D4ED8", "#0F766E", "#A16207", "#7C2D12", "#4D7C0F", "#86198F",
		];
		let h = 0;
		for (let i = 0; i < (user || "").length; i++) h = (h * 31 + user.charCodeAt(i)) >>> 0;
		return palette[h % palette.length];
	}

	handle_incoming(m) {
		if (!m || !m.name) return;
		if (this.search_mode) return;
		if (this.$list.find(`.duty-msg[data-name="${m.name}"]`).length) return;
		const mine = m.user === frappe.session.user;
		const seen_live =
			mine ||
			(this.chat_open && !document.hidden && (!this.is_mobile() || this.mtab === "chat"));
		try {
			this.append_message(m, !seen_live);
		} catch (e) {
			console.error("Duty Room: failed to render message", m && m.name, e);
		}
		this.scroll_chat();
		if (seen_live) {
			this.mark_caught_up(m.creation);
		} else {
			this.bump_unread();
		}
		if (!mine) {
			const mentioned = (m.mentions || []).includes(frappe.session.user);
			this.ping();
			if (mentioned) setTimeout(() => this.ping(), 450);
			this.desktop_notify(m, mentioned);
		}
	}

	sync_messages() {
		if (this._halted || this.search_mode) return;
		if (frappe.get_route_str() !== "duty-board") return;
		const latest = this.latest_creation();
		if (!latest) return;
		frappe.call({
			method: "duty_board.api.get_messages",
			args: { after: latest },
			error: () => {
				this._fail_count = (this._fail_count || 0) + 1;
				if (this._fail_count >= 3) this.halt_polling();
			},
			callback: (r) => {
				this._fail_count = 0;
				const msgs = (r.message && r.message.messages) || [];
				msgs.forEach((m) => this.handle_incoming(m));
			},
		});
	}

	is_mobile() {
		return window.matchMedia("(max-width: 767px)").matches;
	}

	setup_mobile_tabs() {
		if (!this.is_mobile()) return;
		$("body").addClass("duty-mobile");
		const $bar = $(`
			<div class="duty-tabbar">
				<a data-tab="board"><span>🏠</span>${__("Board")}</a>
				<a data-tab="plan"><span>✓</span>${__("Plan")}</a>
				<a data-tab="issues"><span>⚠</span>${__("Issues")}<b class="duty-tab-badge duty-tab-issues" style="display:none"></b></a>
				<a data-tab="chat"><span>💬</span>${__("Chat")}<b class="duty-tab-badge duty-tab-chat" style="display:none"></b></a>
				<a data-tab="projects"><span>📁</span>${__("Projects")}</a>
				<a data-tab="sales"><span>💼</span>${__("Sales")}</a>
				<a data-tab="clients"><span>🤝</span>${__("Clients")}</a>
			</div>
		`).appendTo("body");
		$bar.find("a").on("click", (e) => this.set_mtab($(e.currentTarget).data("tab")));
		this.set_mtab(localStorage.getItem("duty_mtab") || "board");
	}

	set_mtab(tab) {
		this.mtab = tab;
		localStorage.setItem("duty_mtab", tab);
		if (tab === "projects") {
			this.show_face("projects");
		} else if (tab === "sales") {
			this.show_face("sales");
		} else if (tab === "clients") {
			this.show_face("clients");
		} else {
			this.show_face("board");
			this.body.attr("data-mtab", tab);
		}
		$(".duty-tabbar a")
			.removeClass("active")
			.filter(`[data-tab="${tab}"]`)
			.addClass("active");
		if (tab === "chat") {
			this.mark_caught_up();
			this.scroll_chat();
		}
	}

	setup_pwa() {
		if (!("serviceWorker" in navigator)) return;
		if (!document.querySelector('link[rel="manifest"]')) {
			$('<link rel="manifest" href="/assets/duty_board/mobile/manifest.webmanifest">').appendTo("head");
		}
		navigator.serviceWorker
			.register("/duty_sw.js", { scope: "/" })
			.then((reg) => {
				this._sw = reg;
				this.maybe_subscribe_push(reg);
			})
			.catch(() => {
				/* SW route not configured yet — PWA features stay off */
			});
	}

	async maybe_subscribe_push(reg) {
		try {
			if (!window.Notification || Notification.permission !== "granted") return;
			if (!reg.pushManager) return;
			const r = await frappe.call({ method: "duty_board.push.get_push_config" });
			const key = r.message && r.message.public_key;
			if (!key) return;
			let sub = await reg.pushManager.getSubscription();
			if (!sub) {
				sub = await reg.pushManager.subscribe({
					userVisibleOnly: true,
					applicationServerKey: this.urlb64_to_uint8(key),
				});
			}
			frappe.call({
				method: "duty_board.push.save_push_subscription",
				args: { subscription: JSON.stringify(sub.toJSON()) },
			});
		} catch (e) {
			/* push unsupported or denied on this device — realtime still works */
		}
	}

	urlb64_to_uint8(s) {
		const pad = "=".repeat((4 - (s.length % 4)) % 4);
		const b = (s + pad).replace(/-/g, "+").replace(/_/g, "/");
		const raw = atob(b);
		return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
	}

	halt_polling() {
		if (this._halted) return;
		this._halted = true;
		clearInterval(this.main_timer);
		clearInterval(this._sync_timer);
		clearInterval(this._due_timer);
		this.stop_title_flash();
		frappe.msgprint({
			title: __("Connection lost"),
			message: __(
				"Duty Board can no longer reach the server — your session has probably expired. Please log in again, then reopen the board."
			),
			primary_action: {
				label: __("Log in again"),
				action: () => (window.location.href = "/login?redirect-to=/app/duty-board"),
			},
		});
	}

	toggle_chat(open) {
		this.chat_open = open;
		localStorage.setItem("duty_chat_open", open ? "1" : "0");
		this.apply_chat_state();
		if (open) {
			this.mark_caught_up();
			this.scroll_chat();
			this.$input.focus();
		}
	}

	apply_chat_state() {
		this.body.toggleClass("duty-chat-collapsed", !this.chat_open);
		this.body.find(".duty-chat").toggle(this.chat_open);
		this.$rail.toggle(!this.chat_open);
	}

	autosize_input() {
		const el = this.$input[0];
		el.style.height = "auto";
		el.style.height = Math.min(el.scrollHeight, 120) + "px";
	}

	team_members() {
		return Object.keys(this.name_map || {})
			.map((u) => ({ user: u, full_name: this.name_map[u] }))
			.filter((x) => x.user !== frappe.session.user);
	}

	update_mention_menu() {
		const val = this.$input.val() || "";
		const caret = this.$input[0].selectionStart;
		const match = val.slice(0, caret).match(/@([\w .-]*)$/);
		if (!match) {
			this.$mmenu.hide();
			return;
		}
		const q = match[1].toLowerCase();
		const opts = this.team_members()
			.filter((x) => x.full_name.toLowerCase().includes(q) || x.user.toLowerCase().includes(q))
			.slice(0, 6);
		if ("all".startsWith(q)) {
			opts.unshift({ user: "__all__", full_name: __("all — notify everyone") });
		}
		if (!opts.length) {
			this.$mmenu.hide();
			return;
		}
		this.$mmenu.empty();
		opts.forEach((o, ix) => {
			$(`<div class="duty-mention-opt ${ix === 0 ? "active" : ""}" data-user="${o.user}">${frappe.utils.escape_html(o.full_name)}</div>`)
				.appendTo(this.$mmenu)
				.on("mousedown", (e) => {
					e.preventDefault();
					this.pick_mention(o.user);
				});
		});
		this.$mmenu.show();
	}

	move_mention(dir) {
		const $opts = this.$mmenu.children();
		let ix = $opts.index(this.$mmenu.find(".active"));
		ix = (ix + dir + $opts.length) % $opts.length;
		$opts.removeClass("active").eq(ix).addClass("active");
	}

	pick_mention(user) {
		if (!user) return;
		const handle = user === "__all__" ? "@all" : "@" + (this.name_map[user] || user).split(" ")[0];
		const val = this.$input.val();
		const caret = this.$input[0].selectionStart;
		const before = val.slice(0, caret).replace(/@([\w .-]*)$/, handle + " ");
		this.$input.val(before + val.slice(caret)).focus();
		if (user !== "__all__" && !this._mentions.includes(user)) this._mentions.push(user);
		this.$mmenu.hide();
		this.autosize_input();
	}

	set_reply(m) {
		this._reply = m;
		const who = (m.full_name || m.user).split(" ")[0];
		const snip = (m.message || m.attachment_name || "").slice(0, 60);
		this.$replybar
			.html(`↩ ${__("Replying to")} <b>${frappe.utils.escape_html(who)}</b>: ${frappe.utils.escape_html(snip)} <a class="duty-reply-x">×</a>`)
			.show();
		this.$replybar.find(".duty-reply-x").on("click", () => {
			this._reply = null;
			this.$replybar.hide();
		});
		if (!this.chat_open) this.toggle_chat(true);
		this.$input.focus();
	}

	set_file(f) {
		const MAX = 25 * 1024 * 1024;
		if (f.size > MAX) {
			frappe.msgprint(__("File too large (max 25 MB). For big videos, share a link instead."));
			return;
		}
		this._file = f;
		this.$attachbar
			.html(`📎 ${frappe.utils.escape_html(f.name)} <span class="text-muted">(${(f.size / 1048576).toFixed(1)} MB)</span> <a class="duty-attach-x">×</a>`)
			.show();
		this.$attachbar.find(".duty-attach-x").on("click", () => {
			this._file = null;
			this.$attachbar.hide();
		});
	}

	async send_chat() {
		const text = (this.$input.val() || "").trim();
		if (!text && !this._file) return;

		let kept = this._mentions.filter((u) => {
			const h = "@" + (this.name_map[u] || u).split(" ")[0];
			return text.includes(h);
		});
		if (/@all\b/i.test(text)) {
			kept = this.team_members().map((x) => x.user);
		}
		const args = { message: text, mentions: JSON.stringify(kept) };
		if (this._reply) {
			args.reply_to = this._reply.name;
			args.reply_snippet = (
				(this._reply.full_name || this._reply.user).split(" ")[0] +
				": " +
				(this._reply.message || this._reply.attachment_name || "")
			).slice(0, 120);
		}
		const file = this._file;

		this.$input.val("");
		this.autosize_input();
		this._mentions = [];
		this._reply = null;
		this._file = null;
		this.$replybar.hide();
		this.$attachbar.hide();
		this.$mmenu.hide();

		if (file) {
			try {
				const fd = new FormData();
				fd.append("file", file, file.name);
				fd.append("is_private", "1");
				const res = await fetch("/api/method/upload_file", {
					method: "POST",
					headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
					body: fd,
				});
				const out = await res.json();
				const fu = out.message && out.message.file_url;
				if (!res.ok || !fu) {
					throw new Error(
						(out._server_messages && JSON.parse(JSON.parse(out._server_messages)[0]).message) ||
							out.exception ||
							`HTTP ${res.status}`
					);
				}
				args.attachment = fu;
				args.attachment_name = file.name;
				args.attachment_type = file.type.startsWith("image/")
					? "image"
					: file.type.startsWith("video/")
					? "video"
					: "file";
			} catch (e) {
				frappe.msgprint(__("Upload failed: {0}", [frappe.utils.escape_html(e.message || "unknown error")]));
				return;
			}
		}
		frappe.call({ method: "duty_board.api.send_message", args: args });
	}

	format_message_text(m) {
		let html = frappe.utils.escape_html(m.message || "");
		return html.replace(/@([\w-]+)/g, '<span class="duty-mention">@$1</span>');
	}

	append_message(m, is_new, in_search, $insert_after) {
		const mine = m.user === frappe.session.user;
		const mentioned = !mine && (m.mentions || []).includes(frappe.session.user);
		const when = m.creation
			? frappe.datetime.str_to_user(m.creation).split(" ").slice(1).join(" ")
			: "";
		let attach = "";
		if (m.attachment) {
			const url = frappe.utils.escape_html(m.attachment);
			if (m.attachment_type === "image") {
				attach = `<div class="duty-msg-attach"><a href="${url}" target="_blank"><img src="${url}"></a></div>`;
			} else if (m.attachment_type === "video") {
				attach = `<div class="duty-msg-attach"><video src="${url}" controls preload="metadata"></video></div>`;
			} else {
				attach = `<div class="duty-msg-attach"><a href="${url}" target="_blank">📎 ${frappe.utils.escape_html(m.attachment_name || "file")}</a></div>`;
			}
		}
		const $row = $(`
			<div class="duty-msg ${mine ? "duty-msg-mine" : ""} ${mentioned ? "duty-msg-mentioned" : ""} ${is_new ? "duty-msg-new" : ""}" data-creation="${frappe.utils.escape_html(m.creation || "")}" data-name="${frappe.utils.escape_html(m.name || "")}">
				${m.reply_snippet ? `<div class="duty-msg-quote">${frappe.utils.escape_html(m.reply_snippet)}</div>` : ""}
				<span class="duty-msg-who" style="color:${this.user_color(m.user)}">${frappe.utils.escape_html(mine ? __("You") : (m.full_name || m.user).split(" ")[0])}</span>
				<span class="duty-msg-text">${this.format_message_text(m)}</span>
				<span class="duty-msg-time">${when}</span>
				<a class="duty-msg-reply" title="${__("Reply")}">↩</a>
				<a class="duty-msg-react" title="${__("React")}">🙂</a>
				<a class="duty-msg-issue" title="${__("Raise issue from this message")}">⚠</a>
				${frappe.user.has_role("System Manager") ? `<a class="duty-msg-del" title="${__("Delete for everyone")}">🗑</a>` : ""}
				${attach}
			</div>
		`);
		if ($insert_after && $insert_after.length) {
			$row.insertAfter($insert_after);
		} else {
			$row.appendTo(this.$list);
		}
		if (is_new && !in_search) this.ensure_divider($row);
		if (in_search) {
			const day = m.creation ? frappe.datetime.str_to_user(m.creation).split(" ")[0] : "";
			$row.find(".duty-msg-time").text(`${day} ${when}`);
			$row.find(".duty-msg-reply, .duty-msg-react, .duty-msg-issue, .duty-msg-del").remove();
		} else {
			$row.find(".duty-msg-reply").on("click", () => this.set_reply(m));
			$row.find(".duty-msg-react").on("click", (e) => {
				e.stopPropagation();
				this.react_picker($row, m.name);
			});
			$row.find(".duty-msg-del").on("click", (e) => {
				e.stopPropagation();
				frappe.confirm(
					__("Delete this message for everyone? Attachments go with it. This cannot be undone."),
					() =>
						frappe.call({
							method: "duty_board.api.delete_message",
							args: { name: m.name },
						})
				);
			});
			$row.find(".duty-msg-issue").on("click", (e) => {
				e.stopPropagation();
				this.create_issue_dialog({
					description: m.message || "",
					source_type: "Chat",
					source: m.name,
				});
			});
			if (m.reactions && Object.keys(m.reactions).length) {
				this.render_reactions($row, m.reactions, m.name);
			}
		}
		if (!$insert_after) {
			const $rows = this.$list.find(".duty-msg");
			if ($rows.length > 400) $rows.slice(0, $rows.length - 400).remove();
		}
		return $row;
	}

	load_messages() {
		frappe.call({
			method: "duty_board.api.get_messages",
			callback: (r) => {
				const data = r.message || {};
				const msgs = data.messages || [];
				this.seen_map = data.seen || {};
				this.$list.empty();
				this.$list.append(
					`<div class="duty-load-earlier"><a>${__("Load earlier messages")}</a></div>`
				);
				this.$list.find(".duty-load-earlier a").on("click", () => this.load_earlier());
				this.oldest = msgs.length ? msgs[0].creation : null;
				if (!data.has_more) this.$list.find(".duty-load-earlier").hide();
				let new_count = 0;
				msgs.forEach((m) => {
					try {
						const is_new =
							m.user !== frappe.session.user &&
							!!this.last_seen &&
							m.creation > this.last_seen;
						if (is_new) new_count += 1;
						this.append_message(m, is_new);
					} catch (e) {
						console.error("Duty Room: failed to render message", m && m.name, e);
					}
				});
				if (!this.last_seen && msgs.length) {
					this.set_seen(msgs[msgs.length - 1].creation);
				}
				this.update_receipts();
				this.scroll_chat();
				if (new_count) {
					if (this.chat_open && !document.hidden && (!this.is_mobile() || this.mtab === "chat")) {
						this.mark_caught_up();
					} else {
						this.unread = new_count - 1;
						this.bump_unread();
					}
				}
			},
		});
	}

	load_earlier() {
		if (!this.oldest) return;
		frappe.call({
			method: "duty_board.api.get_messages",
			args: { before: this.oldest },
			callback: (r) => {
				const data = r.message || {};
				const msgs = data.messages || [];
				if (msgs.length) {
					const old_h = this.$list[0].scrollHeight;
					let $anchor = this.$list.find(".duty-load-earlier");
					msgs.forEach((m) => {
						try {
							$anchor = this.append_message(m, false, false, $anchor) || $anchor;
						} catch (e) {
							console.error("Duty Room: failed to render message", m && m.name, e);
						}
					});
					this.oldest = msgs[0].creation;
					this.update_receipts();
					this.$list.scrollTop(this.$list[0].scrollHeight - old_h);
				}
				if (!data.has_more) this.$list.find(".duty-load-earlier").hide();
			},
		});
	}

	run_search(query) {
		query = (query || "").trim();
		if (query.length < 2) return;
		frappe.call({
			method: "duty_board.api.search_messages",
			args: { query: query },
			callback: (r) => {
				this.search_mode = true;
				this.$list.empty();
				const results = r.message || [];
				this.$chat
					.find(".duty-search-notice")
					.text(
						results.length
							? __("{0} result(s) for “{1}” — press × to return to chat", [results.length, query])
							: __("No messages match “{0}”", [query])
					)
					.show();
				results.forEach((m) => {
					try {
						this.append_message(m, false, true);
					} catch (e) {
						console.error("Duty Room: failed to render message", m && m.name, e);
					}
				});
				this.$list.scrollTop(0);
			},
		});
	}

	exit_search() {
		if (!this.search_mode) return;
		this.search_mode = false;
		this.$chat.find(".duty-search-notice").hide();
		this.load_messages();
	}

	update_receipts() {
		const me = frappe.session.user;
		this.$list.find(".duty-msg-mine").each((_, el) => {
			const $row = $(el);
			const creation = $row.data("creation");
			if (!creation) return;
			const readers = Object.keys(this.seen_map || {}).filter(
				(u) => u !== me && this.seen_map[u] >= creation
			);
			let $seen = $row.find(".duty-msg-seen");
			if (!readers.length) {
				$seen.remove();
				return;
			}
			const names = readers.map((u) => ((this.name_map || {})[u] || u).split(" ")[0]).join(", ");
			if (!$seen.length) {
				$seen = $(`<span class="duty-msg-seen"></span>`).insertAfter($row.find(".duty-msg-time"));
			}
			$seen.text(`✓✓ ${readers.length}`).attr("title", __("Seen by {0}", [names]));
		});
	}

	render_reactions($row, map, name) {
		let $box = $row.find(".duty-msg-reactions");
		if (!$box.length) $box = $(`<div class="duty-msg-reactions"></div>`).appendTo($row);
		$box.empty();
		const me = frappe.session.user;
		Object.keys(map || {}).forEach((emoji) => {
			const users = map[emoji] || [];
			if (!users.length) return;
			const mine = users.includes(me);
			const names = users.map((u) => ((this.name_map || {})[u] || u).split(" ")[0]).join(", ");
			$(`<span class="duty-react-chip ${mine ? "duty-react-mine" : ""}" title="${frappe.utils.escape_html(names)}">${emoji} ${users.length}</span>`)
				.appendTo($box)
				.on("click", () =>
					frappe.call({
						method: "duty_board.api.toggle_reaction",
						args: { message: name, emoji: emoji },
					})
				);
		});
	}

	react_picker($row, name) {
		$(".duty-react-picker").remove();
		const emojis = ["👍", "❤️", "😂", "🎉", "✅", "👀"];
		const $p = $(`<div class="duty-react-picker"></div>`);
		emojis.forEach((e) => {
			$(`<span>${e}</span>`)
				.appendTo($p)
				.on("click", (ev) => {
					ev.stopPropagation();
					$p.remove();
					frappe.call({
						method: "duty_board.api.toggle_reaction",
						args: { message: name, emoji: e },
					});
				});
		});
		$row.append($p);
		setTimeout(() => $(document).one("click", () => $p.remove()), 0);
	}

	ensure_divider($row) {
		if (this.$list.find(".duty-new-divider").length) return;
		$(`<div class="duty-new-divider"><span>${__("New")}</span></div>`).insertBefore($row);
	}

	set_seen(creation) {
		if (creation && creation > (this.last_seen || "")) {
			this.last_seen = creation;
			localStorage.setItem("duty_chat_seen", creation);
		}
	}

	latest_creation() {
		const $last = this.$list.find(".duty-msg").last();
		return $last.data("creation") || "";
	}

	mark_caught_up(creation) {
		this.set_seen(creation || this.latest_creation());
		this.clear_unread();
		clearTimeout(this._seen_t);
		this._seen_t = setTimeout(() => {
			frappe.call({ method: "duty_board.api.set_chat_seen" });
		}, 800);
		clearTimeout(this._divider_t);
		this._divider_t = setTimeout(() => {
			this.$list.find(".duty-new-divider").remove();
			this.$list.find(".duty-msg-new").removeClass("duty-msg-new");
		}, 5000);
	}

	scroll_chat() {
		this.$list.scrollTop(this.$list[0].scrollHeight);
	}

	bump_unread() {
		this.unread += 1;
		this.$badge.text(this.unread).show();
		this.$rail.find(".duty-rail-badge").text(this.unread).show();
		$(".duty-tab-chat").text(this.unread).show();
		document.title = `(${this.unread}) ${this.base_title}`;
		this.start_title_flash();
	}

	start_title_flash() {
		if (this._flash_t) return;
		this._flash_t = setInterval(() => {
			document.title = document.title.startsWith("🔴")
				? `(${this.unread}) ${this.base_title}`
				: `🔴 ${this.unread} — ${this.base_title}`;
		}, 1400);
	}

	stop_title_flash() {
		clearInterval(this._flash_t);
		this._flash_t = null;
	}

	clear_unread() {
		this.unread = 0;
		this.$badge.hide();
		this.$rail.find(".duty-rail-badge").hide();
		$(".duty-tab-chat").hide();
		this.stop_title_flash();
		document.title = this.base_title;
	}

	ping() {
		try {
			const Ctx = window.AudioContext || window.webkitAudioContext;
			this._actx = this._actx || new Ctx();
			const ctx = this._actx;
			const tone = (freq, at, dur) => {
				const o = ctx.createOscillator();
				const g = ctx.createGain();
				o.type = "sine";
				o.frequency.value = freq;
				g.gain.setValueAtTime(0.4, ctx.currentTime + at);
				o.connect(g);
				g.connect(ctx.destination);
				o.start(ctx.currentTime + at);
				g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + at + dur);
				o.stop(ctx.currentTime + at + dur + 0.05);
			};
			tone(880, 0, 0.15);
			tone(1174.66, 0.13, 0.15);
			tone(1567.98, 0.26, 0.3);
		} catch (e) {
			/* sound blocked until first interaction — fine */
		}
	}

	desktop_notify(m, mentioned) {
		if (!window.Notification || Notification.permission !== "granted") return;
		if (!document.hidden && !mentioned) return;
		try {
			const who = (m.full_name || m.user).split(" ")[0];
			new Notification(`${who} — Duty Room${mentioned ? " (mention)" : ""}`, {
				body: m.message || m.attachment_name || "",
				tag: "duty-room",
				renotify: true,
				requireInteraction: mentioned,
			});
		} catch (e) {
			/* ignore */
		}
	}

	refresh(silent) {
		if (this._halted) return;
		frappe.call({
			method: "duty_board.api.get_board",
			freeze: !silent,
			error: () => {
				this._fail_count = (this._fail_count || 0) + 1;
				if (this._fail_count >= 3) this.halt_polling();
			},
			callback: (r) => {
				this._fail_count = 0;
				if (r.message) this.render(r.message);
			},
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
					depends_on: "eval:doc.reason && doc.reason!=='End of day'",
				},
				{
					fieldname: "summary",
					fieldtype: "Small Text",
					label: __("What did you get done today?"),
					depends_on: "eval:doc.reason==='End of day'",
				},
			],
			primary_action_label: __("Clock Out"),
			primary_action: (values) => {
				d.hide();
				let reason = values.reason;
				if (values.details && values.reason !== "End of day") {
					reason = `${values.reason} — ${values.details}`;
				}
				this.action("clock_out", {
					reason: reason,
					summary: values.reason === "End of day" ? values.summary || null : null,
				});
			},
		});
		d.show();
	}

	start_task_dialog(switching) {
		const NEW_TASK = __("✍️ Something else (type below)");
		const open_todos = (this.my_todos || []).filter((t) => t.status === "Open");
		const todo_map = {};
		const options = [NEW_TASK];
		open_todos.forEach((t) => {
			const label = t.customer ? `${t.description} [${t.customer}]` : t.description;
			if (!todo_map[label]) {
				todo_map[label] = t;
				options.push(label);
			}
		});

		const fields = [];
		if (open_todos.length) {
			fields.push({
				fieldname: "todo_pick",
				fieldtype: "Select",
				label: __("Pick from today's plan"),
				options: options.join("\n"),
				default: options.length > 1 ? options[1] : NEW_TASK,
			});
		}
		fields.push(
			{
				fieldname: "activity",
				fieldtype: "Data",
				label: __("What are you working on?"),
				depends_on: open_todos.length
					? `eval:doc.todo_pick==='${NEW_TASK}'`
					: undefined,
				mandatory_depends_on: open_todos.length
					? `eval:doc.todo_pick==='${NEW_TASK}'`
					: undefined,
				reqd: open_todos.length ? 0 : 1,
			},
			{
				fieldname: "customer",
				fieldtype: "Link",
				label: __("Customer (optional)"),
				options: "Customer",
			}
		);

		const current = this.current_task;
		if (switching && current && current.todo) {
			fields.push({
				fieldname: "complete_previous",
				fieldtype: "Check",
				label: __("I completed: {0}", [frappe.utils.escape_html(current.activity)]),
				default: 1,
			});
		}

		const d = new frappe.ui.Dialog({
			title: switching ? __("Switch Task") : __("Start Task"),
			fields: fields,
			primary_action_label: __("Start Timer"),
			primary_action: (values) => {
				let activity = values.activity;
				let todo = null;
				let customer = values.customer || null;

				if (values.todo_pick && values.todo_pick !== NEW_TASK) {
					const picked = todo_map[values.todo_pick];
					if (picked) {
						activity = picked.description;
						todo = picked.name;
						customer = customer || picked.customer || null;
					}
				}
				if (!activity || !activity.trim()) {
					frappe.msgprint(__("Please describe what you are working on."));
					return;
				}
				d.hide();
				this.action("start_task", {
					activity: activity,
					customer: customer,
					todo: todo,
					complete_previous: values.complete_previous ? 1 : 0,
				});
			},
		});
		d.show();
	}

	stop_task_flow() {
		const current = this.current_task;
		if (current && current.todo) {
			const d = new frappe.ui.Dialog({
				title: __("Stop Task"),
				fields: [
					{
						fieldname: "completed",
						fieldtype: "Check",
						label: __("I completed: {0}", [
							frappe.utils.escape_html(current.activity),
						]),
						default: 1,
					},
				],
				primary_action_label: __("Stop Timer"),
				primary_action: (values) => {
					d.hide();
					this.action("stop_task", { completed: values.completed ? 1 : 0 });
				},
			});
			d.show();
		} else {
			this.action("stop_task", { completed: 0 });
		}
	}

	render(data) {
		if (data.day_summary) {
			this.show_day_summary(data.day_summary);
		}
		this.dm_unread = data.dm_unread || this.dm_unread || {};
		this.my_todos = data.my_todos || [];
		this.my_upcoming = data.my_upcoming || [];
		this.overdue_count = data.overdue_count || 0;
		this.current_task = data.me && data.me.task;
		this.name_map = {};
		(data.board || []).forEach((r) => (this.name_map[r.user] = r.full_name));
		this.render_me(data.me);
		this.render_task(data.me);
		this.render_plan(data.me);
		this.render_my_sessions(data.my_sessions, data.me);
		this.render_issues(data.issues, data.me);
		this.render_team(data.board);
		this.body
			.find(".duty-updated")
			.text(__("Last updated {0}", [frappe.datetime.now_time()]));
	}

	show_day_summary(d) {
		const row = (label, secs, cls) =>
			`<tr class="${cls || ""}">
				<td>${label}</td>
				<td style="text-align:right"><b>${this.fmt_duration(secs)}</b></td>
			</tr>`;
		const remarks = (d.remarks || [])
			.map(
				(r) =>
					`<div class="duty-daynum-remark duty-daynum-${r.kind}">${frappe.utils.escape_html(r.text)}</div>`
			)
			.join("");
		const dlg = new frappe.ui.Dialog({
			title: __("Your Day in Numbers"),
			primary_action_label: __("Close"),
			primary_action: () => dlg.hide(),
		});
		$(dlg.body).html(`
			<table class="duty-daynum-table">
				<tr class="duty-daynum-head"><td>${__("Expected on duty")}</td>
					<td style="text-align:right">${this.fmt_duration(d.expected_duty)}</td></tr>
				${row(__("Actual hours on duty"), d.duty, d.duty < d.expected_duty ? "duty-daynum-short" : "duty-daynum-ok")}
				<tr class="duty-daynum-head"><td>${__("Expected break")}</td>
					<td style="text-align:right">${this.fmt_duration(d.expected_break)}</td></tr>
				${row(__("Actual break time"), d.breaks, d.breaks > d.expected_break ? "duty-daynum-short" : "duty-daynum-ok")}
				${row(__("Hours booked to tasks"), d.task)}
				${row(__("Hours attached to a customer"), d.customer)}
			</table>
			${remarks}
		`);
		dlg.show();
	}

	task_history_dialog() {
		const d = new frappe.ui.Dialog({ title: __("My Task History"), size: "large" });
		$(d.body).html(`
			<div class="duty-history-list"><div class="text-muted">${__("Loading...")}</div></div>
			<div class="duty-history-more" style="display:none; text-align:center; margin-top:8px">
				<button class="btn btn-default btn-sm">${__("Load older")}</button>
			</div>
		`);
		const $list = $(d.body).find(".duty-history-list");
		let before = null;
		let last_date = null;
		let first_load = true;
		const load = () => {
			frappe.call({
				method: "duty_board.api.get_task_history",
				args: { before: before },
				callback: (r) => {
					const data = r.message || {};
					if (first_load) {
						$list.empty();
						first_load = false;
					}
					(data.sessions || []).forEach((x) => {
						if (x.date !== last_date) {
							last_date = x.date;
							$list.append(
								`<div class="duty-history-day">${frappe.datetime.str_to_user(x.date)}</div>`
							);
						}
						const $row = $(`
							<div class="duty-session-row">
								<span class="duty-session-activity">${frappe.utils.escape_html(x.activity)}</span>
								${x.customer ? `<span class="duty-task-customer">${frappe.utils.escape_html(x.customer)}</span>` : ""}
								<span class="duty-session-time text-muted">
									${this.fmt_time(x.start_time)} – ${x.end_time ? this.fmt_time(x.end_time) : __("open")}
									· ${this.fmt_duration(x.duration)}
								</span>
								<a class="duty-session-notes" title="${__("Notes")}">📝${x.notes ? " " + x.notes : ""}</a>
							</div>`).appendTo($list);
						$row.find(".duty-session-notes").on("click", (e) => {
							e.preventDefault();
							this.note_dialog(x.name, x.activity, true);
						});
					});
					before = data.next_before;
					$(d.body).find(".duty-history-more").toggle(!!data.has_more);
					if (!$list.children().length) {
						$list.html(`<div class="text-muted">${__("No earlier tasks yet.")}</div>`);
					}
				},
			});
		};
		$(d.body).find(".duty-history-more button").on("click", load);
		load();
		d.show();
	}

	dm_row(m) {
		const mine = m.sender === frappe.session.user;
		const when = m.creation ? frappe.datetime.str_to_user(m.creation) : "";
		return `
			<div class="duty-msg ${mine ? "duty-msg-mine" : ""}" data-name="${m.name}">
				<span class="duty-msg-who" style="color:${this.user_color(m.sender)}">${mine ? __("You") : frappe.utils.escape_html((m.sender_name || m.sender).split(" ")[0])}</span>
				<span class="duty-msg-text">${frappe.utils.escape_html(m.message || "")}</span>
				<span class="duty-msg-time">${when}</span>
			</div>`;
	}

	set_dm_badge(user, n) {
		const $b = this.body.find(`.duty-dm-btn[data-user="${user}"] .duty-dm-badge`);
		if (n) $b.text(n).show();
		else $b.hide();
	}

	mark_dm_seen(user) {
		frappe.call({ method: "duty_board.dm.mark_dm_seen", args: { with_user: user } });
		if (this.dm_unread) delete this.dm_unread[user];
		this.set_dm_badge(user, 0);
	}

	open_dm(user, full_name) {
		if (!user || user === frappe.session.user) return;
		full_name = full_name || this.name_map[user] || user;
		if (this._dm_dialog && this._dm_with === user) {
			this._dm_dialog.show();
			return;
		}
		if (this._dm_dialog) this._dm_dialog.hide();
		const d = (this._dm_dialog = new frappe.ui.Dialog({
			title: `✉ ${full_name.split(" ")[0]}`,
		}));
		this._dm_with = user;
		d.onhide = () => {
			if (this._dm_with === user) this._dm_with = null;
		};
		$(d.body).html(`
			<div class="duty-dm-list"><div class="text-muted">${__("Loading...")}</div></div>
			<div class="duty-dm-send">
				<textarea rows="1" class="form-control duty-dm-input" maxlength="1000"
					placeholder="${__("Message {0}... Enter to send, Shift+Enter for a new line", [frappe.utils.escape_html(full_name.split(" ")[0])])}"></textarea>
				<button class="btn btn-primary btn-sm duty-dm-btn-send">${__("Send")}</button>
			</div>
		`);
		const $list = $(d.body).find(".duty-dm-list");
		const $input = $(d.body).find(".duty-dm-input");
		let oldest = null;
		const load = (before) => {
			frappe.call({
				method: "duty_board.dm.get_dm_thread",
				args: { with_user: user, before: before },
				callback: (r) => {
					const data = r.message || {};
					const msgs = data.messages || [];
					if (msgs.length) oldest = msgs[0].creation;
					if (!before) {
						$list.empty();
						if (data.has_more) {
							$list.append(
								`<div class="duty-load-earlier"><a>${__("Load earlier")}</a></div>`
							);
							$list.find(".duty-load-earlier a").on("click", () => load(oldest));
						}
						$list.append(msgs.map((m) => this.dm_row(m)).join(""));
						if (!msgs.length) {
							$list.append(
								`<div class="text-muted duty-plan-empty">${__("No messages yet — say hello.")}</div>`
							);
						}
						$list.scrollTop($list[0].scrollHeight);
					} else {
						const old_h = $list[0].scrollHeight;
						const $anchor = $list.find(".duty-load-earlier");
						$anchor.after(msgs.map((m) => this.dm_row(m)).join(""));
						if (!data.has_more) $anchor.hide();
						$list.scrollTop($list[0].scrollHeight - old_h);
					}
					this.mark_dm_seen(user);
				},
			});
		};
		const send = () => {
			const text = ($input.val() || "").trim();
			if (!text) return;
			$input.val("");
			frappe.call({
				method: "duty_board.dm.send_dm",
				args: { to: user, message: text },
				callback: (r) => {
					const m = r.message;
					if (m && !$list.find(`[data-name="${m.name}"]`).length) {
						$list.find(".duty-plan-empty").remove();
						$list.append(this.dm_row(m));
						$list.scrollTop($list[0].scrollHeight);
					}
				},
			});
		};
		$(d.body).find(".duty-dm-btn-send").on("click", send);
		$input.on("keydown", (e) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				send();
			}
		});
		d.show();
		load(null);
		this.set_dm_badge(user, 0);
	}

	handle_dm(m) {
		if (!m || !m.name) return;
		const me = frappe.session.user;
		const other = m.sender === me ? m.recipient : m.sender;
		const dialog_open =
			this._dm_with === other && this._dm_dialog && this._dm_dialog.$wrapper.is(":visible");
		if (dialog_open) {
			const $list = $(this._dm_dialog.body).find(".duty-dm-list");
			if (!$list.find(`[data-name="${m.name}"]`).length) {
				$list.find(".duty-plan-empty").remove();
				$list.append(this.dm_row(m));
				$list.scrollTop($list[0].scrollHeight);
			}
			if (m.sender !== me) this.mark_dm_seen(other);
			return;
		}
		if (m.sender !== me) {
			this.dm_unread = this.dm_unread || {};
			this.dm_unread[m.sender] = (this.dm_unread[m.sender] || 0) + 1;
			this.set_dm_badge(m.sender, this.dm_unread[m.sender]);
			this.ping();
			const first = (m.sender_name || m.sender).split(" ")[0];
			frappe.show_alert(
				{
					message: `<b>✉ ${frappe.utils.escape_html(first)}</b><br>${frappe.utils.escape_html((m.message || "").slice(0, 80))}`,
					indicator: "blue",
				},
				6
			);
			if (window.Notification && Notification.permission === "granted" && document.hidden) {
				try {
					new Notification(`✉ ${first} — DM`, {
						body: (m.message || "").slice(0, 120),
						tag: "duty-dm",
						renotify: true,
					});
				} catch (e) {
					/* ignore */
				}
			}
		}
	}

	// ---------------- Projects face ----------------

	proj_color(name) {
		return this.user_color("proj:" + name);
	}

	show_face(face) {
		this.face = face;
		this.body.toggle(face === "board");
		this.$projects.toggle(face === "projects");
		this.$sales.toggle(face === "sales");
		this.$clients.toggle(face === "clients");
		if (face === "projects") this.refresh_projects();
		if (face === "sales") this.refresh_sales();
		if (face === "clients") this.refresh_clients();
	}

	toggle_face() {
		this.show_face(this.face === "projects" ? "board" : "projects");
	}

	toggle_sales() {
		this.show_face(this.face === "sales" ? "board" : "sales");
	}

	refresh_projects(silent) {
		frappe.call({
			method: "duty_board.projects.get_projects",
			freeze: false,
			error: () => {
				this._fail_count = (this._fail_count || 0) + 1;
				if (this._fail_count >= 3) this.halt_polling();
			},
			callback: (r) => {
				this._fail_count = 0;
				this._projects = r.message || [];
				this.render_project_tabs();
				const remembered = localStorage.getItem("duty_proj");
				if (!this.current_project && remembered && this._projects.find((p) => p.name === remembered)) {
					this.current_project = remembered;
				}
				if (this.current_project && !this._projects.find((p) => p.name === this.current_project)) {
					this.current_project = null;
				}
				if (!this.current_project && this._projects.length) {
					this.current_project = this._projects[0].name;
				}
				if (this.current_project) this.load_kanban(this.current_project);
				else this.$projects.find(".duty-kanban-wrap").html(
					`<div class="text-muted duty-plan-empty">${__("No projects yet — create the first one.")}</div>`
				);
			},
		});
	}

	render_project_tabs() {
		const $tabs = this.$projects.find(".duty-proj-tabs").empty();
		(this._projects || []).forEach((p) => {
			const bits = [`${p.total} ${__("tasks")}`, `✓ ${p.done}`];
			if (p.overdue) bits.push(`<span class="duty-proj-over">⚠ ${p.overdue}</span>`);
			if (p.suspended) bits.push(`⏸ ${p.suspended}`);
			const pc = this.proj_color(p.name);
			const target = p.target_date
				? `<span class="duty-proj-target ${p.days_left != null && p.days_left < 0 ? "duty-lead-over" : ""}">🎯 ${frappe.datetime.str_to_user(p.target_date)}${p.days_left != null ? ` (${p.days_left}d)` : ""}</span>`
				: "";
			$(`
				<a class="duty-proj-tab ${p.name === this.current_project ? "active" : ""}" data-name="${p.name}" style="border-left: 4px solid ${pc}">
					<span class="duty-proj-name" style="color:${pc}">${frappe.utils.escape_html(p.project_name)}</span>
					${p.customer ? `<span class="duty-proj-cust">${frappe.utils.escape_html(p.customer)}</span>` : ""}
					<span class="duty-proj-stats">${bits.join(" · ")}</span>
					<span class="duty-proj-bar"><span style="width:${p.pct || 0}%; background:${pc}"></span></span>
					${target}
				</a>
			`)
				.appendTo($tabs)
				.on("click", () => {
					this.current_project = p.name;
					localStorage.setItem("duty_proj", p.name);
					this.render_project_tabs();
					this.load_kanban(p.name);
				});
		});
	}

	load_kanban(project) {
		frappe.call({
			method: "duty_board.projects.get_project_board",
			args: { project: project },
			callback: (r) => r.message && this.render_kanban(project, r.message),
		});
	}

	kb_card(t) {
		const who = t.assignee
			? `<span style="color:${this.user_color(t.assignee)}">${frappe.utils.escape_html((this.name_map[t.assignee] || t.assignee).split(" ")[0])}</span>`
			: `<span class="text-muted">${__("unassigned")}</span>`;
		return `
			<div class="duty-kb-card" draggable="true" data-name="${t.name}" style="border-left: 3px solid ${this._kb_color || "var(--border-color)"}">
				<div class="duty-kb-top">
					<span class="duty-sev duty-sev-${(t.urgency || "medium").toLowerCase()}">${__(t.urgency)}</span>
					${t.due_date ? `<span class="duty-kb-due ${t.overdue ? "duty-issue-overdue" : ""}">${t.overdue ? "⚠ " : ""}${frappe.datetime.str_to_user(t.due_date)}</span>` : ""}
				</div>
				<div class="duty-kb-title">${frappe.utils.escape_html(t.title)}</div>
				<div class="duty-kb-meta">
					${who}
					<span class="duty-lead-badges">
						${(t.working || []).length ? `<span class="duty-kb-working">⏱ ${t.working.map((u) => `<b style="color:${this.user_color(u)}">${frappe.utils.escape_html((this.name_map[u] || u).split(" ")[0])}</b>`).join(", ")}</span>` : ""}
						${t.stale_days >= 7 && t.column !== "Completed" ? `<span class="duty-stale ${t.stale_days >= 14 ? "duty-stale-red" : ""}">🕸 ${t.stale_days}d</span>` : ""}
						${t.notes ? `<span>💬 ${t.notes}</span>` : ""}
					</span>
				</div>
			</div>`;
	}

	render_kanban(project, data) {
		if (project !== this.current_project) return;
		const $wrap = this.$projects.find(".duty-kanban-wrap").empty();
		const proj = (this._projects || []).find((p) => p.name === project);
		this._kb_color = this.proj_color(project);
		const $bar = $(`
			<div class="duty-kb-bar">
				<span>
					<b style="color:${this._kb_color}">${frappe.utils.escape_html(proj ? proj.project_name : project)}</b>
					${proj && proj.customer ? `<span class="duty-proj-cust-inline">· ${frappe.utils.escape_html(proj.customer)}</span>` : ""}
				</span>
				<a class="duty-proj-archive">${__("Archive project")}</a>
			</div>
		`).appendTo($wrap);
		$bar.find(".duty-proj-archive").on("click", () =>
			frappe.confirm(__("Archive this project? Its board disappears from the tabs (nothing is deleted)."), () =>
				frappe.call({
					method: "duty_board.projects.archive_project",
					args: { name: project },
					callback: () => {
						this.current_project = null;
						this.refresh_projects();
					},
				})
			)
		);
		const $board = $(`<div class="duty-kanban"></div>`).appendTo($wrap);
		(data.columns || []).forEach((col) => {
			const cards = (data.tasks && data.tasks[col]) || [];
			const $col = $(`
				<div class="duty-kb-col" data-col="${col}">
					<div class="duty-kb-col-head">${__(col)} <span class="duty-kb-count">${cards.length}</span></div>
					${col === "To Do" ? `<input type="text" class="form-control input-sm duty-kb-add" placeholder="${__("Add a task and press Enter...")}">` : ""}
					<div class="duty-kb-cards" data-col="${col}">
						${cards.map((t) => this.kb_card(t)).join("")}
					</div>
				</div>
			`).appendTo($board);

			$col.find(".duty-kb-add").on("keydown", (e) => {
				if (e.key !== "Enter") return;
				const title = e.target.value.trim();
				if (!title) return;
				e.target.value = "";
				frappe.call({
					method: "duty_board.projects.create_task",
					args: { project: project, title: title },
					callback: (r) => r.message && this.render_kanban(project, r.message),
				});
			});

			$col.on("dragover", (e) => {
				e.preventDefault();
				$col.addClass("duty-kb-over");
			});
			$col.on("dragleave drop", () => $col.removeClass("duty-kb-over"));
			$col.on("drop", (e) => {
				e.preventDefault();
				const name = e.originalEvent.dataTransfer.getData("text");
				if (!name) return;
				frappe.call({
					method: "duty_board.projects.move_task",
					args: { name: name, column: col },
					callback: (r) => {
						if (r.message) this.render_kanban(project, r.message);
						this.refresh_projects_counts();
						if (this._open_room) this.load_client_room(this._open_room);
					},
				});
			});
		});

		const task_index = {};
		(data.columns || []).forEach((c) =>
			((data.tasks && data.tasks[c]) || []).forEach((t) => (task_index[t.name] = t))
		);
		$board.find(".duty-kb-card").each((_, el) => {
			const $card = $(el);
			el.addEventListener("dragstart", (e) => {
				e.dataTransfer.setData("text", $card.data("name"));
			});
			$card.on("click", () =>
				frappe.call({
					method: "duty_board.projects.get_card",
					args: { name: $card.data("name") },
					callback: (r) => r.message && this.task_dialog(project, r.message),
				})
			);
		});
	}

	refresh_projects_counts() {
		frappe.call({
			method: "duty_board.projects.get_projects",
			callback: (r) => {
				this._projects = r.message || [];
				this.render_project_tabs();
			},
		});
	}

	staff_options() {
		return [{ label: __("Unassigned"), value: "" }].concat(
			[{ user: frappe.session.user, full_name: __("Me") }]
				.concat(this.team_members())
				.map((x) => ({ label: x.full_name, value: x.user }))
		);
	}

	task_dialog(project, t) {
		if (!t) return;
		const d = new frappe.ui.Dialog({
			title: frappe.utils.escape_html(t.title.slice(0, 50)),
			fields: [
				{ fieldname: "title", fieldtype: "Data", label: __("Task"), default: t.title, reqd: 1 },
				{
					fieldname: "assignee",
					fieldtype: "Autocomplete",
					label: __("Assign to"),
					options: this.staff_options(),
					default: t.assignee || "",
					description: __("Assigning puts this on their daily plan — done there is done here."),
				},
				{ fieldname: "due_date", fieldtype: "Date", label: __("Due Date"), default: t.due_date || "" },
				{
					fieldname: "urgency",
					fieldtype: "Select",
					label: __("Urgency"),
					options: "Low\nMedium\nHigh\nCritical",
					default: t.urgency || "Medium",
				},
				{
					fieldname: "column",
					fieldtype: "Select",
					label: __("Column"),
					options: "To Do\nIn Progress\nCompleted\nSuspended",
					default: t.column,
				},
				{
					fieldname: "client_visible",
					fieldtype: "Check",
					label: __("Visible to client (shows on their portal)"),
					default: t.client_visible ? 1 : 0,
				},
				{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: t.description || "" },
				{ fieldname: "extras", fieldtype: "HTML" },
			],
			primary_action_label: __("Save"),
			primary_action: (v) => {
				d.hide();
				frappe.call({
					method: "duty_board.projects.update_task",
					args: {
						name: t.name,
						title: v.title,
						assignee: v.assignee || null,
						due_date: v.due_date || null,
						urgency: v.urgency,
						column: v.column,
						description: v.description || null,
						client_visible: v.client_visible ? 1 : 0,
					},
					callback: (r) => {
						if (r.message) this.render_kanban(project, r.message);
						this.refresh_projects_counts();
						if (this._open_room) this.load_client_room(this._open_room);
					},
				});
			},
			secondary_action_label: __("Delete"),
			secondary_action: () => {
				frappe.confirm(__("Delete this task?"), () => {
					d.hide();
					frappe.call({
						method: "duty_board.projects.delete_task",
						args: { name: t.name },
						callback: (r) => {
							if (r.message) this.render_kanban(project, r.message);
							this.refresh_projects_counts();
						},
					});
				});
			},
		});
		const me_working = (t.working || []).includes(frappe.session.user);
		const $x = $(d.fields_dict.extras.wrapper).html(`
			${(t.working || []).length ? `<div class="duty-issue-meta">⏱ ${__("Working on it now")}: ${t.working.map((u) => `<span style="color:${this.user_color(u)}">${frappe.utils.escape_html((this.name_map[u] || u).split(" ")[0])}</span>`).join(", ")}</div>` : ""}
			<div class="duty-lead-close" style="justify-content:flex-start; margin-top:8px">
				${t.column !== "Completed" && !me_working ? `<button type="button" class="btn btn-sm btn-default duty-card-start">▶ ${__("Start work")}</button>` : ""}
				${me_working ? `<button type="button" class="btn btn-sm btn-default duty-card-stop">⏸ ${__("Stop work")}</button>` : ""}
			</div>
			<div class="duty-lead-section">💬 ${__("Chat")}</div>
			<div class="duty-lead-notes">
				${(t.notes_list || t.notes || []).map
					? ""
					: ""}
			</div>
		`);
		const notes = Array.isArray(t.notes) ? t.notes : [];
		$x.find(".duty-lead-notes").html(
			notes.length
				? notes
						.map(
							(n) =>
								`<div class="duty-lead-note"><b>${frappe.utils.escape_html(n.who)}</b> <span class="duty-msg-time">${frappe.datetime.str_to_user(n.when)}</span><br>${this.fmt_note(n.note)}</div>`
						)
						.join("")
				: `<div class="text-muted">${__("No notes yet.")}</div>`
		);
		$x.append(`
			<div class="duty-lead-addnote">
				<input type="text" class="form-control input-sm duty-cn-text" placeholder="${__("Message this thread — @ to mention, Enter to send...")}">
			</div>
		`);
		const reopen = (r) => {
			d.hide();
			if (r.message) this.task_dialog(project, r.message);
			this.load_kanban(project);
			if (this._open_room) this.load_client_room(this._open_room);
		};
		$x.find(".duty-card-start").on("click", () =>
			frappe.call({
				method: "duty_board.projects.start_card_work",
				args: { name: t.name },
				callback: (r) => {
					reopen(r);
					this.refresh(true);
				},
			})
		);
		$x.find(".duty-card-stop").on("click", () =>
			frappe.call({
				method: "duty_board.projects.stop_card_work",
				args: { name: t.name },
				callback: (r) => {
					reopen(r);
					this.refresh(true);
				},
			})
		);
		this.attach_mention_picker($x.find(".duty-cn-text"));
		this._open_card_ctx = { id: t.name, $x: $x };
		d.onhide = () => {
			if (this._open_card_ctx && this._open_card_ctx.id === t.name) this._open_card_ctx = null;
		};
		$x.find(".duty-cn-text").on("keydown", (e) => {
			if (e.key !== "Enter") return;
			e.preventDefault();
			e.stopPropagation();
			const note = e.target.value.trim();
			if (!note) return;
			frappe.call({
				method: "duty_board.projects.add_card_note",
				args: { name: t.name, note: note },
				callback: reopen,
			});
		});
		d.show();
	}

	new_project_dialog() {
		frappe.prompt(
			[
				{ fieldname: "project_name", fieldtype: "Data", label: __("Project name"), reqd: 1 },
				{ fieldname: "customer", fieldtype: "Link", label: __("Customer"), options: "Customer", reqd: 1 },
				{ fieldname: "target_date", fieldtype: "Date", label: __("Target Date") },
			],
			(v) => {
				frappe.call({
					method: "duty_board.projects.create_project",
					args: { project_name: v.project_name, customer: v.customer, target_date: v.target_date || null },
					callback: (r) => {
						this.current_project = r.message;
						localStorage.setItem("duty_proj", r.message);
						this.refresh_projects();
					},
				});
			},
			__("New Project"),
			__("Create")
		);
	}

	// ---------------- Clients face ----------------

	refresh_clients(silent) {
		frappe.call({
			method: "duty_board.client_room.get_rooms",
			freeze: false,
			error: () => {
				this._fail_count = (this._fail_count || 0) + 1;
				if (this._fail_count >= 3) this.halt_polling();
			},
			callback: (r) => {
				this._fail_count = 0;
				this._rooms = r.message || [];
				this.render_room_list();
				if (this._open_room) this.load_client_room(this._open_room, true);
			},
		});
	}

	render_room_list() {
		const $list = this.$clients.find(".duty-cr-list").empty();
		const $bar = $(`
			<div class="duty-cr-bar">
				<b>🤝 ${__("Client Rooms")}</b>
				<button class="btn btn-sm btn-primary duty-cr-new">＋ ${__("New Room")}</button>
			</div>
		`).appendTo($list);
		$bar.find(".duty-cr-new").on("click", () =>
			frappe.prompt(
				{ fieldname: "customer", fieldtype: "Link", label: __("Customer"), options: "Customer", reqd: 1 },
				(v) =>
					frappe.call({
						method: "duty_board.client_room.create_room",
						args: { customer: v.customer },
						callback: (r) => {
							this.refresh_clients();
							if (r.message) this.open_client_room(r.message);
						},
					}),
				__("New Client Room"),
				__("Create")
			)
		);
		if (!(this._rooms || []).length) {
			$list.append(`<div class="text-muted duty-plan-empty">${__("No client rooms yet.")}</div>`);
			return;
		}
		this._rooms.forEach((r) => {
			$(`
				<a class="duty-cr-item ${r.name === this._open_room ? "active" : ""} ${r.status !== "Active" ? "duty-cr-frozen" : ""}">
					<b style="color:${this.proj_color(r.name)}">${frappe.utils.escape_html(r.customer)}</b>
					${r.status !== "Active" ? `<span class="duty-cr-status">${__(r.status)}</span>` : ""}
					<span class="duty-cr-last">${frappe.utils.escape_html(r.last || "")}</span>
					<span class="duty-cr-members">👥 ${r.members}</span>
				</a>
			`)
				.appendTo($list)
				.on("click", () => this.open_client_room(r.name));
		});
	}

	open_client_room(name) {
		this._open_room = name;
		this.render_room_list();
		this.load_client_room(name);
	}

	load_client_room(name, silent) {
		frappe.call({
			method: "duty_board.client_room.get_room",
			args: { name: name },
			callback: (r) => r.message && this.render_client_room(r.message),
		});
	}

	cr_msg(m) {
		return `
			<div class="duty-cr-msg ${m.internal ? "duty-cr-internal" : m.is_staff ? "duty-cr-staff" : "duty-cr-client"}">
				<span class="duty-msg-who" style="color:${this.user_color(m.owner)}">${m.internal ? "🔒 " : ""}${frappe.utils.escape_html((m.who || m.owner).split(" ")[0])}${m.is_staff ? "" : ` · ${__("client")}`}</span>
				<span class="duty-msg-text">${frappe.utils.escape_html(m.message)}</span>
				${m.attachment_url ? `<span class="duty-cr-att">${m.is_image ? `<a href="/api/method/duty_board.client_room.room_file?msg=${m.name}" target="_blank"><img src="/api/method/duty_board.client_room.room_file?msg=${m.name}"></a>` : `<a class="duty-issue-filelink" href="/api/method/duty_board.client_room.room_file?msg=${m.name}" target="_blank">📎 ${frappe.utils.escape_html(m.attachment_name || "file")}</a>`}</span>` : ""}
				<span class="duty-msg-time">${frappe.datetime.str_to_user(m.creation)}</span>
				${m.is_staff ? "" : `<a class="duty-cr-mktask" data-text="${frappe.utils.escape_html(m.message.slice(0, 120))}" title="${__("Make task from this")}">➕</a>`}
			</div>`;
	}

	render_client_room(x) {
		if (x.name !== this._open_room) return;
		const $room = this.$clients.find(".duty-cr-room").show();
		const counts = { Queued: 0, "In Progress": 0, Done: 0 };
		(x.tasks || []).forEach((t) => (counts[t.status] = (counts[t.status] || 0) + 1));
		$room.html(`
			<div class="duty-cr-ribbon">🤝 ${__("{0} can read this room — whispers 🔒 excepted", [frappe.utils.escape_html(x.customer)])}</div>
			<div class="duty-cr-head">
				<b>${frappe.utils.escape_html(x.customer)}</b>
				<span class="duty-cr-taskchips">📋 ${counts.Queued} ${__("queued")} · ${counts["In Progress"]} ${__("in progress")} · ${counts.Done} ${__("done")}</span>
				<span class="duty-cr-tools">
					<a class="duty-cr-membersbtn">👥 ${__("Members")}${(x.requests || []).length ? ` <b class="duty-cr-reqbadge">${x.requests.length}</b>` : ""}</a>
					${frappe.user.has_role("System Manager") ? `<a class="duty-cr-freeze">${x.status === "Active" ? "🧊 " + __("Freeze") : "▶ " + __("Unfreeze")}</a>` : ""}
				</span>
			</div>
			<div class="duty-cr-tasksbar">
				<a class="duty-cr-taskstoggle"><b>${this._cr_tasks_open === false ? "▸" : "▾"} 📋 ${__("Work")} (${(x.tasks || []).length})</b></a>
				<select class="form-control input-sm duty-cr-tfilter">
					<option value="">${__("All")}</option>
					<option ${this._cr_tfilter === "Queued" ? "selected" : ""}>Queued</option>
					<option ${this._cr_tfilter === "In Progress" ? "selected" : ""}>In Progress</option>
					<option ${this._cr_tfilter === "Done" ? "selected" : ""}>Done</option>
				</select>
			</div>
			<div class="duty-cr-tasks" ${this._cr_tasks_open === false ? 'style="display:none"' : ""}>
				${(x.tasks || [])
					.filter((t) => !this._cr_tfilter || t.status === this._cr_tfilter)
					.map(
						(t) => `
					<a class="duty-cr-task" data-name="${t.name}" data-kind="${t.kind}">
						<span class="duty-crt-pill duty-crt-${(t.status || "").replace(/ /g, "").toLowerCase()}">${__(t.status)}</span>
						<span class="duty-crt-title">${t.kind === "issue" ? "⚠ " : "📁 "}${t.client_requested ? "🙋 " : ""}${frappe.utils.escape_html(t.title)}</span>
						${t.assignee_first ? `<span class="duty-crt-who">${frappe.utils.escape_html(t.assignee_first)}</span>` : ""}
						${t.reported ? `<span class="duty-crt-stamps">${__("Rep")} ${t.reported.slice(0, 10)}${t.started ? ` · ${__("Start")} ${t.started.slice(0, 10)}` : ""}${t.done ? ` · ${__("Done")} ${t.done.slice(0, 10)}` : ""}</span>` : ""}
					</a>`
					)
					.join("")}
				<a class="duty-cr-openissues">⚠ ${__("Open issue register for {0}", [frappe.utils.escape_html(x.customer)])} ›</a>
			</div>
			<div class="duty-cr-msgs">${(x.messages || []).map((m) => this.cr_msg(m)).join("") || `<div class="text-muted">${__("No messages yet.")}</div>`}</div>
			<div class="duty-cr-pending"></div>
			<div class="duty-cr-compose">
				<label class="duty-cr-int"><input type="checkbox" class="duty-cr-internal-toggle"> 🔒 ${__("Internal")}</label>
				<label class="duty-cr-attach" title="${__("Attach image / file")}">📎<input type="file" hidden></label>
				<textarea rows="2" class="form-control duty-cr-input" placeholder="${__("Message {0}... Enter to send", [frappe.utils.escape_html(x.customer)])}"></textarea>
				<button type="button" class="btn btn-primary btn-sm duty-cr-send">${__("Send")}</button>
			</div>
		`);
		const $msgs = $room.find(".duty-cr-msgs");
		$msgs.scrollTop($msgs[0].scrollHeight);
		const $input = $room.find(".duty-cr-input");
		const $int = $room.find(".duty-cr-internal-toggle");
		const restyle = () => $room.find(".duty-cr-compose").toggleClass("duty-cr-composing-internal", $int.is(":checked"));
		$int.on("change", restyle);
		this._cr_pending = null;
		const show_pending = () => {
			const $p = $room.find(".duty-cr-pending").empty();
			if (this._cr_pending) {
				$(`<span class="duty-file-chip">📎 ${frappe.utils.escape_html(this._cr_pending.name)} <a>×</a></span>`)
					.appendTo($p)
					.find("a")
					.on("click", () => {
						this._cr_pending = null;
						show_pending();
					});
			}
		};
		const take_file = (f) => {
			if (!f) return;
			if (f.size > 15 * 1024 * 1024) {
				frappe.msgprint(__("File too large (max 15 MB)."));
				return;
			}
			this._cr_pending = f;
			show_pending();
		};
		$room.find(".duty-cr-attach input").on("change", (e) => {
			take_file(e.target.files[0]);
			e.target.value = "";
		});
		$input.on("paste", (e) => {
			for (const it of (e.originalEvent.clipboardData || {}).items || []) {
				if (it.kind === "file") {
					const f = it.getAsFile();
					if (f) {
						e.preventDefault();
						take_file(f);
						break;
					}
				}
			}
		});
		const send = async () => {
			const text = ($input.val() || "").trim();
			if (!text && !this._cr_pending) return;
			$input.val("");
			let up = null;
			if (this._cr_pending) {
				try {
					up = await this.upload_private_file(this._cr_pending);
					this._cr_pending = null;
					show_pending();
				} catch (err) {
					frappe.msgprint(__("Upload failed: {0}", [frappe.utils.escape_html(err.message || "")]));
					return;
				}
			}
			frappe.call({
				method: "duty_board.client_room.post_message",
				args: {
					name: x.name,
					message: text,
					internal: $int.is(":checked") ? 1 : 0,
					attachment_url: up ? up.file_url : null,
					attachment_name: up ? up.file_name : null,
				},
				callback: (r) => r.message && this.render_client_room(r.message),
			});
		};
		$room.find(".duty-cr-send").on("click", send);
		this.attach_mention_picker(
			$input,
			() =>
				(x.members || []).map((m) => ({
					user: m.user,
					full_name: `${m.full_name} · ${__("client")}`,
				}))
		);
		$input.on("keydown", (e) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				send();
			}
		});
		$room.find(".duty-cr-mktask").on("click", (e) => {
			const seed = $(e.currentTarget).data("text");
			frappe.prompt(
				{ fieldname: "title", fieldtype: "Data", label: __("Task title"), default: seed, reqd: 1 },
				(v) =>
					frappe.call({
						method: "duty_board.client_room.make_task_from_message",
						args: { name: x.name, title: v.title },
						callback: (r) => r.message && this.render_client_room(r.message),
					}),
				__("Make client-visible task"),
				__("Create")
			);
		});
		$room.find(".duty-cr-taskstoggle").on("click", () => {
			this._cr_tasks_open = this._cr_tasks_open === false;
			this.render_client_room(x);
		});
		$room.find(".duty-cr-tfilter").on("change", (e) => {
			this._cr_tfilter = e.target.value;
			this.render_client_room(x);
		});
		$room.find(".duty-cr-task").on("click", (e) => {
			const $t = $(e.currentTarget);
			if ($t.data("kind") === "issue") {
				this.issue_detail_dialog($t.data("name"));
			} else {
				frappe.call({
					method: "duty_board.projects.get_card",
					args: { name: $t.data("name") },
					callback: (r) => r.message && this.task_dialog(r.message.project, r.message),
				});
			}
		});
		$room.find(".duty-cr-openissues").on("click", () => {
			this._force_cfilter = true;
			this.issue_customer_filter = x.customer;
			this.issues_open = true;
			localStorage.setItem("duty_issues_side", "1");
			this.show_face("board");
			this.refresh(true);
		});
		$room.find(".duty-cr-membersbtn").on("click", () => this.room_members_dialog(x));
		$room.find(".duty-cr-freeze").on("click", () =>
			frappe.call({
				method: "duty_board.client_room.set_room_status",
				args: { name: x.name, status: x.status === "Active" ? "Frozen" : "Active" },
				callback: () => this.load_client_room(x.name),
			})
		);
	}

	room_members_dialog(x) {
		const d = new frappe.ui.Dialog({ title: `👥 ${x.customer}` });
		const render = (data) => {
			$(d.body).html(`
				<div class="duty-cr-memlist">
					${(data.members || [])
						.map(
							(m) =>
								`<div class="duty-cr-mem"><b>${frappe.utils.escape_html(m.full_name)}</b> <span class="text-muted">${frappe.utils.escape_html(m.user)}</span> <a class="duty-cr-memrm" data-name="${m.name}">${__("Remove")}</a></div>`
						)
						.join("") || `<div class="text-muted">${__("No client members yet.")}</div>`}
				</div>
				${
					(data.requests || []).length
						? `<div class="duty-lead-section">🙋 ${__("Waiting for approval")}</div>` +
							data.requests
								.map(
									(q) =>
										`<div class="duty-cr-mem"><b>${frappe.utils.escape_html(q.full_name)}</b> <span class="text-muted">${frappe.utils.escape_html(q.email)}${q.phone ? " · " + frappe.utils.escape_html(q.phone) : ""}</span> <a class="duty-cr-approve" data-name="${q.name}">✔ ${__("Approve")}</a> <a class="duty-cr-rejectq" data-name="${q.name}">✖</a></div>`
								)
								.join("")
						: ""
				}
				<div class="duty-lead-section">🔗 ${__("Invite link")}</div>
				<div class="duty-cr-joinlink">
					<input type="text" class="form-control input-sm" readonly value="${frappe.utils.escape_html(data.join_url || "")}">
					<button type="button" class="btn btn-sm btn-default duty-cr-copylink">${__("Copy")}</button>
				</div>
				<p class="text-muted duty-attach-hint">${__("Share this with the client — anyone who submits the form appears above for approval.")}</p>
				<div class="duty-cr-addmem">
					<input type="text" class="form-control input-sm duty-cr-em" placeholder="${__("client email")}">
					<input type="text" class="form-control input-sm duty-cr-nm" placeholder="${__("full name")}">
					<button type="button" class="btn btn-sm btn-primary duty-cr-addbtn">＋</button>
				</div>
				<p class="text-muted duty-attach-hint">${__("New members get a welcome email with a password link. Their portal: {0}", ["<b>" + location.origin + "/portal</b>"])}</p>
			`);
			$(d.body).find(".duty-cr-addbtn").on("click", () => {
				const email = $(d.body).find(".duty-cr-em").val().trim();
				const nm = $(d.body).find(".duty-cr-nm").val().trim();
				if (!email) return;
				frappe.call({
					method: "duty_board.client_room.add_member",
					args: { name: x.name, email: email, full_name: nm },
					callback: (r) => r.message && render(r.message),
				});
			});
			$(d.body).find(".duty-cr-copylink").on("click", (e) => {
				const $inp = $(d.body).find(".duty-cr-joinlink input");
				$inp.trigger("select");
				try {
					navigator.clipboard.writeText($inp.val());
					frappe.show_alert({ message: __("Link copied"), indicator: "green" }, 3);
				} catch (err) {
					document.execCommand("copy");
				}
			});
			$(d.body).find(".duty-cr-approve").on("click", (e) =>
				frappe.call({
					method: "duty_board.client_room.approve_join",
					args: { request_name: $(e.currentTarget).data("name") },
					callback: (r) => r.message && render(r.message),
				})
			);
			$(d.body).find(".duty-cr-rejectq").on("click", (e) =>
				frappe.call({
					method: "duty_board.client_room.reject_join",
					args: { request_name: $(e.currentTarget).data("name") },
					callback: (r) => r.message && render(r.message),
				})
			);
			$(d.body).find(".duty-cr-memrm").on("click", (e) =>
				frappe.confirm(__("Remove this member's access?"), () =>
					frappe.call({
						method: "duty_board.client_room.remove_member",
						args: { member_name: $(e.currentTarget).data("name") },
						callback: () => this.load_client_room(x.name),
					}).then(() => d.hide())
				)
			);
		};
		render(x);
		d.show();
	}

	// ---------------- Sales face ----------------

	attach_mention_picker($input, extra) {
		const $wrap = $input.parent();
		$wrap.addClass("duty-mention-host");
		const $dd = $('<div class="duty-mention-dd" style="display:none"></div>').appendTo($wrap);
		const staff = () =>
			[{ user: frappe.session.user, full_name: this.name_map[frappe.session.user] || frappe.session.user }]
				.concat(this.team_members())
				.concat((typeof extra === "function" ? extra() : extra) || []);
		const frag = () => {
			const v = $input.val();
			const pos = $input[0].selectionStart;
			const m = v.slice(0, pos).match(/@([A-Za-z0-9._-]*)$/);
			return m ? { start: pos - m[0].length, text: m[1], pos: pos } : null;
		};
		const close = () => $dd.hide().empty();
		const render = () => {
			const f = frag();
			if (!f) return close();
			const q = f.text.toLowerCase();
			const opts = staff()
				.filter(
					(s) =>
						(s.full_name || s.user).toLowerCase().includes(q) ||
						s.user.toLowerCase().includes(q)
				)
				.slice(0, 6);
			if (!opts.length) return close();
			$dd.empty().show();
			opts.forEach((s) => {
				$(
					`<a class="duty-mention-opt" style="color:${this.user_color(s.user)}">${frappe.utils.escape_html(s.full_name || s.user)}</a>`
				)
					.appendTo($dd)
					.on("mousedown", (e) => {
						e.preventDefault();
						const f2 = frag();
						if (!f2) return close();
						const v = $input.val();
						const first = (s.full_name || s.user).split(" ")[0];
						$input.val(v.slice(0, f2.start) + "@" + first + " " + v.slice(f2.pos));
						close();
						$input.focus();
					});
			});
		};
		$input.on("input keyup click", render);
		$input.on("blur", () => setTimeout(close, 150));
		$input.on("keydown", (e) => {
			if (e.key === "Enter" && $dd.is(":visible")) {
				e.preventDefault();
				e.stopImmediatePropagation();
				$dd.find(".duty-mention-opt").first().trigger("mousedown");
			}
			if (e.key === "Escape") close();
		});
	}

	update_notes($x, notes) {
		notes = Array.isArray(notes) ? notes : [];
		$x.find(".duty-lead-notes").html(
			notes.length
				? notes
						.map(
							(n) =>
								`<div class="duty-lead-note"><b>${frappe.utils.escape_html(n.who)}</b> <span class="duty-msg-time">${frappe.datetime.str_to_user(n.when)}</span><br>${this.fmt_note(n.note)}</div>`
						)
						.join("")
				: `<div class="text-muted">${__("No messages yet.")}</div>`
		);
	}

	fmt_note(text) {
		return frappe.utils
			.escape_html(text || "")
			.replace(/@([A-Za-z0-9._-]+)/g, '<b class="duty-note-mention">@$1</b>');
	}

	naira(v) {
		if (v === null || v === undefined) return "";
		try {
			return format_currency(v || 0, frappe.boot.sysdefaults.currency);
		} catch (e) {
			return (v || 0).toLocaleString();
		}
	}

	refresh_sales(silent) {
		frappe.call({
			method: "duty_board.sales.get_pipeline",
			freeze: false,
			error: () => {
				this._fail_count = (this._fail_count || 0) + 1;
				if (this._fail_count >= 3) this.halt_polling();
			},
			callback: (r) => {
				this._fail_count = 0;
				if (r.message) this.render_pipeline(r.message);
			},
		});
	}

	lead_card(l) {
		const owner = `<span style="color:${this.user_color(l.lead_owner)}">${frappe.utils.escape_html((this.name_map[l.lead_owner] || l.lead_owner).split(" ")[0])}</span>`;
		return `
			<div class="duty-kb-card duty-lead-card" draggable="true" data-name="${l.name}" style="border-left: 3px solid ${this.user_color(l.lead_owner)}">
				<div class="duty-lead-company">${frappe.utils.escape_html(l.company)}</div>
				${l.value ? `<div class="duty-lead-value">${this.naira(l.value)}</div>` : ""}
				${l.contact_name ? `<div class="duty-lead-contact">${frappe.utils.escape_html(l.contact_name)}</div>` : ""}
				<div class="duty-kb-meta">
					${owner}
					<span class="duty-lead-badges">
						${l.stale_days >= 7 ? `<span class="duty-stale ${l.stale_days >= 14 ? "duty-stale-red" : ""}" title="${__("Days since last touch")}">🕸 ${l.stale_days}d</span>` : ""}
						${l.expected_close ? `<span class="${l.close_overdue ? "duty-lead-over" : ""}" title="${__("Expected close")}">🎯 ${frappe.datetime.str_to_user(l.expected_close)}</span>` : ""}
						${l.tasks_open ? `<span class="${l.tasks_overdue ? "duty-lead-over" : ""}">📋 ${l.tasks_open}</span>` : ""}
						${l.notes ? `<span>💬 ${l.notes}</span>` : ""}
					</span>
				</div>
			</div>`;
	}

	render_pipeline(data) {
		this.$sales
			.find(".duty-sales-total")
			.html(
				`💼 <b>${__("Pipeline")}</b> · ${data.total.count} ${__("leads")}` +
					(data.show_values && data.total.value != null
						? ` · <b class="duty-lead-value">${this.naira(data.total.value)}</b> ${__("open")}`
						: "")
			);
		const $wrap = this.$sales.find(".duty-sales-wrap").empty();
		const $board = $(`<div class="duty-kanban duty-sales-kanban"></div>`).appendTo($wrap);
		const index = {};
		(data.stages || []).forEach((stage) => {
			const col = (data.pipeline && data.pipeline[stage]) || { leads: [], count: 0, value: 0 };
			col.leads.forEach((l) => (index[l.name] = l));
			const $col = $(`
				<div class="duty-kb-col" data-col="${stage}">
					<div class="duty-kb-col-head">
						<span>${__(stage)} <span class="duty-kb-count">${col.count}</span></span>
						<span class="duty-kb-sum">${col.value ? this.naira(col.value) : ""}</span>
					</div>
					<div class="duty-kb-cards" data-col="${stage}">
						${col.leads.map((l) => this.lead_card(l)).join("")}
					</div>
				</div>
			`).appendTo($board);
			$col.on("dragover", (e) => {
				e.preventDefault();
				$col.addClass("duty-kb-over");
			});
			$col.on("dragleave drop", () => $col.removeClass("duty-kb-over"));
			$col.on("drop", (e) => {
				e.preventDefault();
				const name = e.originalEvent.dataTransfer.getData("text");
				if (!name) return;
				frappe.call({
					method: "duty_board.sales.move_lead",
					args: { name: name, stage: stage },
					callback: (r) => r.message && this.render_pipeline(r.message),
				});
			});
		});
		$board.find(".duty-lead-card").each((_, el) => {
			const $card = $(el);
			el.addEventListener("dragstart", (e) =>
				e.dataTransfer.setData("text", $card.data("name"))
			);
			$card.on("click", () => this.lead_dialog($card.data("name")));
		});
	}

	new_lead_dialog() {
		const d = new frappe.ui.Dialog({
			title: `💼 ${__("New Lead")}`,
			fields: [
				{ fieldname: "company", fieldtype: "Data", label: __("Company / Prospect"), reqd: 1 },
				{
					fieldname: "lead_owner",
					fieldtype: "Autocomplete",
					label: __("Owner"),
					options: this.staff_options().filter((o) => o.value),
					default: frappe.session.user,
					reqd: 1,
				},
				{ fieldname: "value", fieldtype: "Currency", label: __("Lead Value") },
				{ fieldname: "contact_name", fieldtype: "Data", label: __("Contact Name") },
				{ fieldname: "email", fieldtype: "Data", label: __("Email") },
				{ fieldname: "phone", fieldtype: "Data", label: __("Phone") },
				{ fieldname: "expected_close", fieldtype: "Date", label: __("Expected Close") },
				{
					fieldname: "source",
					fieldtype: "Select",
					label: __("Source"),
					options: "\nReferral\nExisting Client\nWebsite\nCold Outreach\nEvent\nOther",
				},
				{ fieldname: "description", fieldtype: "Small Text", label: __("What they do & need") },
			],
			primary_action_label: __("Create"),
			primary_action: (v) => {
				d.hide();
				frappe.call({
					method: "duty_board.sales.create_lead",
					args: v,
					callback: () => this.refresh_sales(),
				});
			},
		});
		d.show();
	}

	lead_dialog(name) {
		frappe.call({
			method: "duty_board.sales.get_lead",
			args: { name: name },
			callback: (r) => r.message && this.render_lead_dialog(r.message),
		});
	}

	render_lead_dialog(x) {
		if (this._lead_dialog) this._lead_dialog.hide();
		const d = (this._lead_dialog = new frappe.ui.Dialog({
			title: `💼 ${x.company}`,
			size: "large",
			fields: [
				{ fieldname: "company", fieldtype: "Data", label: __("Company / Prospect"), default: x.company, reqd: 1 },
				{
					fieldname: "lead_owner",
					fieldtype: "Autocomplete",
					label: __("Owner"),
					options: this.staff_options().filter((o) => o.value),
					default: x.lead_owner,
				},
				...(x.can_edit_value
					? [{ fieldname: "value", fieldtype: "Currency", label: __("Lead Value"), default: x.value }]
					: []),
				{ fieldname: "contact_name", fieldtype: "Data", label: __("Contact Name"), default: x.contact_name },
				{ fieldname: "email", fieldtype: "Data", label: __("Email"), default: x.email },
				{ fieldname: "phone", fieldtype: "Data", label: __("Phone"), default: x.phone },
				{ fieldname: "expected_close", fieldtype: "Date", label: __("Expected Close"), default: x.expected_close || "" },
				{
					fieldname: "source",
					fieldtype: "Select",
					label: __("Source"),
					options: "\nReferral\nExisting Client\nWebsite\nCold Outreach\nEvent\nOther",
					default: x.source || "",
				},
				{ fieldname: "description", fieldtype: "Small Text", label: __("What they do & need"), default: x.description },
				{ fieldname: "extras", fieldtype: "HTML" },
			],
			primary_action_label: __("Save"),
			primary_action: (v) => {
				d.hide();
				frappe.call({
					method: "duty_board.sales.update_lead",
					args: Object.assign({ name: x.name }, v),
					callback: () => this.refresh_sales(),
				});
			},
		}));
		const contact_bits = [];
		if (x.email) contact_bits.push(`<a href="mailto:${x.email}">✉ ${frappe.utils.escape_html(x.email)}</a>`);
		if (x.phone) contact_bits.push(`<a href="tel:${x.phone}">📞 ${frappe.utils.escape_html(x.phone)}</a>`);
		const $x = $(d.fields_dict.extras.wrapper).html(`
			${contact_bits.length ? `<div class="duty-lead-links">${contact_bits.join(" · ")}</div>` : ""}
			<div class="duty-lead-section">📋 ${__("Tasks")}</div>
			<div class="duty-lead-tasks">
				${(x.tasks || [])
					.map(
						(t) => `
					<label class="duty-lead-task ${t.status === "Done" ? "duty-lead-task-done" : ""}">
						<input type="checkbox" data-name="${t.name}" ${t.status === "Done" ? "checked" : ""}>
						<span>${frappe.utils.escape_html(t.description)}</span>
						${t.date ? `<span class="duty-kb-due ${t.overdue ? "duty-issue-overdue" : ""}">${frappe.datetime.str_to_user(t.date)}</span>` : ""}
						${t.due_time ? `<span class="duty-time-chip">${t.due_time}</span>` : ""}
						<span style="color:${this.user_color(t.user)}">${frappe.utils.escape_html((this.name_map[t.user] || t.user).split(" ")[0])}</span>
					</label>`
					)
					.join("") || `<div class="text-muted">${__("No tasks yet.")}</div>`}
			</div>
			<div class="duty-lead-addtask">
				<input type="text" class="form-control input-sm duty-lt-desc" placeholder="${__("New task...")}">
				<input type="date" class="form-control input-sm duty-lt-date">
				<input type="time" class="form-control input-sm duty-lt-time">
				<select class="form-control input-sm duty-lt-who">
					${this.staff_options().filter((o) => o.value).map((o) => `<option value="${o.value}" ${o.value === x.lead_owner ? "selected" : ""}>${frappe.utils.escape_html(o.label)}</option>`).join("")}
				</select>
				<button type="button" class="btn btn-sm btn-default duty-lt-add">＋</button>
			</div>
			<div class="duty-lead-section">💬 ${__("Chat")}</div>
			<div class="duty-lead-notes">
				${(x.notes || [])
					.map(
						(n) => `<div class="duty-lead-note"><b>${frappe.utils.escape_html(n.who)}</b> <span class="duty-msg-time">${frappe.datetime.str_to_user(n.when)}</span><br>${this.fmt_note(n.note)}</div>`
					)
					.join("") || `<div class="text-muted">${__("No notes yet.")}</div>`}
			</div>
			<div class="duty-lead-addnote">
				<input type="text" class="form-control input-sm duty-ln-text" placeholder="${__("Message this thread — @ to mention, Enter to send...")}">
			</div>
			<div class="duty-lead-close">
				<button type="button" class="btn btn-sm btn-success duty-lead-won">🏆 ${__("Mark Won")}</button>
				<button type="button" class="btn btn-sm btn-default duty-lead-lost">✖ ${__("Mark Lost")}</button>
			</div>
		`);
		$x.find("input[type=checkbox]").on("change", (e) =>
			frappe.call({
				method: "duty_board.sales.toggle_lead_task",
				args: { name: $(e.target).data("name"), done: e.target.checked ? 1 : 0 },
				callback: (r) => r.message && this.render_lead_dialog(r.message),
			})
		);
		const add_task = () => {
			const desc = $x.find(".duty-lt-desc").val().trim();
			if (!desc) return;
			frappe.call({
				method: "duty_board.sales.add_lead_task",
				args: {
					lead: x.name,
					description: desc,
					date: $x.find(".duty-lt-date").val() || null,
					time: $x.find(".duty-lt-time").val() || null,
					assignee: $x.find(".duty-lt-who").val(),
				},
				callback: (r) => r.message && this.render_lead_dialog(r.message),
			});
		};
		$x.find(".duty-lt-add").on("click", (e) => {
			e.preventDefault();
			add_task();
		});
		$x.find(".duty-lt-desc").on("keydown", (e) => {
			if (e.key !== "Enter") return;
			e.preventDefault();
			e.stopPropagation();
			add_task();
		});
		this.attach_mention_picker($x.find(".duty-ln-text"));
		this._open_lead_ctx = { id: x.name, $x: $x };
		d.onhide = () => {
			if (this._open_lead_ctx && this._open_lead_ctx.id === x.name) this._open_lead_ctx = null;
		};
		$x.find(".duty-ln-text").on("keydown", (e) => {
			if (e.key !== "Enter") return;
			e.preventDefault();
			e.stopPropagation();
			const note = e.target.value.trim();
			if (!note) return;
			frappe.call({
				method: "duty_board.sales.add_lead_note",
				args: { lead: x.name, note: note },
				callback: (r) => r.message && this.render_lead_dialog(r.message),
			});
		});
		const close_lead = (outcome) =>
			frappe.confirm(
				outcome === "Won"
					? __("Mark {0} as WON? 🎉 It moves to the Won archive.", [frappe.utils.escape_html(x.company)])
					: __("Mark {0} as lost? It moves to the Lost archive.", [frappe.utils.escape_html(x.company)]),
				() => {
					d.hide();
					frappe.call({
						method: "duty_board.sales.close_lead",
						args: { name: x.name, outcome: outcome },
						callback: (r) => {
							if (r.message) this.render_pipeline(r.message);
							if (outcome === "Won")
								frappe.show_alert(
									{ message: `🎉 ${frappe.utils.escape_html(x.company)} — ${__("WON!")}`, indicator: "green" },
									7
								);
						},
					});
				}
			);
		$x.find(".duty-lead-won").on("click", () => close_lead("Won"));
		$x.find(".duty-lead-lost").on("click", () => close_lead("Lost"));
		d.show();
	}

	closed_leads_dialog(outcome) {
		frappe.call({
			method: "duty_board.sales.get_closed_leads",
			args: { outcome: outcome },
			callback: (r) => {
				const rows = r.message || [];
				const d = new frappe.ui.Dialog({
					title: outcome === "Won" ? `🏆 ${__("Won leads")}` : `✖ ${__("Lost leads")}`,
				});
				$(d.body).html(
					rows.length
						? rows
								.map(
									(l) => `
							<div class="duty-lead-closedrow">
								<b>${frappe.utils.escape_html(l.company)}</b>
								${l.value ? `<span class="duty-lead-value">${this.naira(l.value)}</span>` : ""}
								<span style="color:${this.user_color(l.lead_owner)}">${frappe.utils.escape_html((this.name_map[l.lead_owner] || l.lead_owner).split(" ")[0])}</span>
								${l.closed_on ? `<span class="duty-msg-time">${frappe.datetime.str_to_user(l.closed_on)}</span>` : ""}
								<a class="duty-lead-reopen" data-name="${l.name}">${__("Reopen")}</a>
							</div>`
								)
								.join("")
						: `<div class="text-muted">${__("Nothing here yet.")}</div>`
				);
				$(d.body)
					.find(".duty-lead-reopen")
					.on("click", (e) =>
						frappe.call({
							method: "duty_board.sales.reopen_lead",
							args: { name: $(e.currentTarget).data("name") },
							callback: () => {
								d.hide();
								this.refresh_sales();
							},
						})
					);
				d.show();
			},
		});
	}

	note_dialog(session, activity, can_add) {
		const d = new frappe.ui.Dialog({
			title: __("Notes — {0}", [frappe.utils.escape_html((activity || "").slice(0, 40))]),
		});
		const render_list = (notes) => {
			const items = (notes || [])
				.map(
					(n) => `
					<div class="duty-note-item">
						<div class="duty-note-meta">
							<span style="color:${this.user_color(n.user)}">${frappe.utils.escape_html((n.full_name || n.user).split(" ")[0])}</span>
							<span class="text-muted">${frappe.datetime.str_to_user(n.creation)}</span>
						</div>
						<div class="duty-note-text">${frappe.utils.escape_html(n.note)}</div>
					</div>`
				)
				.join("");
			$(d.body)
				.find(".duty-note-list")
				.html(items || `<div class="text-muted">${__("No notes yet.")}</div>`);
		};
		$(d.body).html(`
			<div class="duty-note-list"></div>
			${
				can_add
					? `<div class="duty-note-add">
						<textarea rows="2" class="form-control duty-note-input"
							placeholder="${__("Add a note... Enter to save, Shift+Enter for a new line")}"></textarea>
						<button class="btn btn-primary btn-sm duty-note-save">${__("Add")}</button>
					</div>`
					: ""
			}
		`);
		frappe.call({
			method: "duty_board.api.get_task_notes",
			args: { session: session },
			callback: (r) => render_list(r.message),
		});
		const save = () => {
			const val = ($(d.body).find(".duty-note-input").val() || "").trim();
			if (!val) return;
			$(d.body).find(".duty-note-input").val("");
			frappe.call({
				method: "duty_board.api.add_task_note",
				args: { session: session, note: val },
				callback: (r) => {
					render_list(r.message);
					this.refresh(true);
				},
			});
		};
		$(d.body).find(".duty-note-save").on("click", save);
		$(d.body).find(".duty-note-input").on("keydown", (e) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				save();
			}
		});
		d.show();
	}

	async upload_private_file(file) {
		const fd = new FormData();
		fd.append("file", file, file.name);
		fd.append("is_private", "1");
		const res = await fetch("/api/method/upload_file", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
			body: fd,
		});
		const out = await res.json();
		const fu = out.message && out.message.file_url;
		if (!res.ok || !fu) {
			throw new Error(out.exception || `HTTP ${res.status}`);
		}
		return { file_url: fu, file_name: file.name };
	}

	issue_is_mine(x) {
		const me = frappe.session.user;
		return x.raised_by === me || (x.assignees || []).includes(me);
	}

	render_issues(issues, me) {
		this._issues = issues = issues || [];
		this._issues_me = me;
		const $wrap = this.body.find(".duty-issues").empty();
		const $rail = this.body.find(".duty-issues-rail");
		if (!me) {
			$rail.hide();
			return;
		}
		this.check_overdue_issues(issues);
		if (this.issues_open === undefined) {
			this.issues_open = localStorage.getItem("duty_issues_side") === "1";
		}
		if (this.is_mobile()) this.issues_open = true;
		this.issue_status_filter = this.issue_status_filter || "open";

		$rail.find(".duty-issues-rail-badge").text(issues.length).toggle(issues.length > 0);
		$(".duty-tab-issues").text(issues.length).toggle(issues.length > 0);
		this.body.toggleClass("duty-issues-collapsed", !this.issues_open);
		$wrap.toggle(this.issues_open);
		$rail.toggle(!this.issues_open);
		$rail.off("click").on("click", () => {
			this.issues_open = true;
			localStorage.setItem("duty_issues_side", "1");
			this.render_issues(this._issues, this._issues_me);
		});
		if (!this.issues_open) return;

		const scope = this.issue_status_filter;
		let items;
		if (scope === "open") {
			items = issues;
		} else if (this._issues_alt && this._issues_alt_scope === scope) {
			items = this._issues_alt;
		} else {
			$wrap.html(
				`<div class="duty-issues-card"><div class="text-muted" style="margin-top:8px">${__("Loading...")}</div></div>`
			);
			frappe.call({
				method: "duty_board.api.get_issues",
				args: { scope: scope },
				callback: (r) => {
					this._issues_alt = r.message || [];
					this._issues_alt_scope = scope;
					this.render_issues(this._issues, this._issues_me);
				},
				error: () => {
					$wrap.html(
						`<div class="duty-issues-card"><div class="text-muted" style="margin-top:8px">${__("Could not load issues — press F12, check the console, and report the red error.")}</div></div>`
					);
				},
			});
			return;
		}

		const mine = issues.filter((x) => this.issue_is_mine(x)).length;
		const ufilter = this.issue_user_filter || "";
		const customers = [...new Set(items.map((x) => x.customer).filter(Boolean))].sort();
		let cfilter = this.issue_customer_filter || "";
		if (this._force_cfilter) {
			if (cfilter && !customers.includes(cfilter)) customers.push(cfilter);
			this._force_cfilter = false;
		} else if (cfilter && !customers.includes(cfilter)) {
			cfilter = "";
			this.issue_customer_filter = "";
		}
		let shown = cfilter ? items.filter((x) => x.customer === cfilter) : items;
		if (ufilter === "__me__") {
			shown = shown.filter((x) => (x.assignees || []).includes(frappe.session.user));
		} else if (ufilter === "__none__") {
			shown = shown.filter((x) => !(x.assignees || []).length);
		} else if (ufilter) {
			shown = shown.filter((x) => (x.assignees || []).includes(ufilter));
		}
		const today = frappe.datetime.get_today();

		const rows = shown
			.map((x) => {
				const active = ["Open", "In Progress"].includes(x.status);
				const overdue = x.due_date && x.due_date < today && active;
				const names = (x.assignees || [])
					.map(
						(u) =>
							`<span style="color:${this.user_color(u)}">${frappe.utils.escape_html((this.name_map[u] || u).split(" ")[0])}</span>`
					)
					.join(", ");
				const stamp = x.resolved_at
					? `${__("resolved")} ${this.fmt_stamp(x.resolved_at)}`
					: `${__("raised")} ${this.fmt_stamp(x.creation)}`;
				return `
				<div class="duty-issue-row ${this.issue_is_mine(x) ? "duty-issue-mine" : ""}" data-name="${x.name}">
					<span class="duty-sev duty-sev-${(x.severity || "medium").toLowerCase()}">${__(x.severity)}</span>
					<span class="duty-issue-title">${frappe.utils.escape_html(x.title)}</span>
					<span class="duty-task-customer">${frappe.utils.escape_html(x.customer || "")}</span>
					${names ? `<span class="duty-issue-who">→ ${names}</span>` : ""}
					${x.status !== "Open" ? `<span class="duty-issue-status duty-ist-${x.status.replace(/ /g, "").toLowerCase()}">${__(x.status)}</span>` : ""}
					${x.due_date && active ? `<span class="duty-issue-due ${overdue ? "duty-issue-overdue" : ""}">${overdue ? "⚠ " : ""}${__("due")} ${frappe.datetime.str_to_user(x.due_date)}</span>` : ""}
					<span class="duty-issue-raised">${stamp}</span>
				</div>`;
			})
			.join("");

		const staff_opts = [
			`<option value="">${__("Anyone")}</option>`,
			`<option value="__me__" ${ufilter === "__me__" ? "selected" : ""}>${__("Me")}</option>`,
		]
			.concat(
				this.team_members().map(
					(t) =>
						`<option value="${t.user}" ${ufilter === t.user ? "selected" : ""}>${frappe.utils.escape_html(t.full_name)}</option>`
				)
			)
			.concat([
				`<option value="__none__" ${ufilter === "__none__" ? "selected" : ""}>${__("Unassigned")}</option>`,
			])
			.join("");

		$wrap.html(`
			<div class="duty-issues-card">
				<div class="duty-chat-head">
					<span>⚠ ${__("Issues")}
						<span class="duty-plan-count">${issues.length} ${__("open")}${mine ? ` · ${mine} ${__("mine")}` : ""}</span>
					</span>
					<span class="duty-chat-tools">
						<a class="duty-issues-collapse" title="${__("Collapse")}">«</a>
					</span>
				</div>
				<div class="duty-issues-toolbar">
					<div class="duty-issues-toolbar-row">
						<select class="form-control input-sm duty-issue-scope" title="${__("Status")}">
							<option value="open" ${scope === "open" ? "selected" : ""}>${__("Open")}</option>
							<option value="resolved" ${scope === "resolved" ? "selected" : ""}>${__("Resolved")}</option>
							<option value="closed" ${scope === "closed" ? "selected" : ""}>${__("Closed")}</option>
							<option value="all" ${scope === "all" ? "selected" : ""}>${__("All")}</option>
						</select>
						<button class="btn btn-xs btn-default duty-issue-new">＋ ${__("New")}</button>
					</div>
					<select class="form-control input-sm duty-issue-filter" title="${__("Filter by customer")}">
						<option value="">${__("All customers")}</option>
						${customers
							.map(
								(c) =>
									`<option value="${frappe.utils.escape_html(c)}" ${c === cfilter ? "selected" : ""}>${frappe.utils.escape_html(c)}</option>`
							)
							.join("")}
					</select>
					<select class="form-control input-sm duty-issue-user" title="${__("Filter by assignee")}">
						${staff_opts}
					</select>
				</div>
				<div class="duty-issues-list">
					${rows || `<div class="text-muted duty-plan-empty">${__("Nothing here with these filters.")}</div>`}
				</div>
			</div>
		`);
		$wrap.find(".duty-issues-collapse").on("click", () => {
			this.issues_open = false;
			localStorage.setItem("duty_issues_side", "0");
			this.render_issues(this._issues, this._issues_me);
		});
		$wrap.find(".duty-issue-scope").on("change", (e) => {
			this.issue_status_filter = e.target.value;
			this._issues_alt = null;
			this._issues_alt_scope = null;
			this.render_issues(this._issues, this._issues_me);
		});
		$wrap.find(".duty-issue-filter").on("change", (e) => {
			this.issue_customer_filter = e.target.value || "";
			this.render_issues(this._issues, this._issues_me);
		});
		$wrap.find(".duty-issue-user").on("change", (e) => {
			this.issue_user_filter = e.target.value || "";
			this.render_issues(this._issues, this._issues_me);
		});
		$wrap.find(".duty-issue-new").on("click", () => this.create_issue_dialog({}));
		$wrap.find(".duty-issue-row").on("click", (e) =>
			this.issue_detail_dialog($(e.currentTarget).data("name"))
		);
	}

	create_issue_dialog(prefill) {
		prefill = prefill || {};
		const all_staff = () =>
			[{ user: frappe.session.user, full_name: __("Me") }]
				.concat(this.team_members())
				.map((x) => ({ value: x.user, description: x.full_name }));
		const d = new frappe.ui.Dialog({
			title: __("New Issue"),
			fields: [
				{
					fieldname: "title",
					fieldtype: "Data",
					label: __("Title"),
					reqd: 1,
					default: prefill.title || (prefill.description || "").slice(0, 80),
				},
				{
					fieldname: "customer",
					fieldtype: "Link",
					label: __("Customer"),
					options: "Customer",
					reqd: 1,
					default: prefill.customer || "",
				},
				{
					fieldname: "severity",
					fieldtype: "Select",
					label: __("Severity"),
					options: "Low\nMedium\nHigh\nCritical",
					default: "Medium",
					reqd: 1,
				},
				{
					fieldname: "due_date",
					fieldtype: "Date",
					label: __("Due Date"),
				},
				{
					fieldname: "assignees",
					fieldtype: "MultiSelectList",
					label: __("Assign to"),
					get_data: all_staff,
				},
				{
					fieldname: "description",
					fieldtype: "Small Text",
					label: __("Description"),
					default: prefill.description || "",
				},
				{ fieldname: "attach_html", fieldtype: "HTML" },
			],
			primary_action_label: __("Create Issue"),
			primary_action: async (v) => {
				const files = this._pending_issue_files || [];
				const uploaded = [];
				if (files.length) {
					frappe.show_alert(
						{ message: __("Uploading {0} file(s)...", [files.length]), indicator: "blue" },
						4
					);
					try {
						for (const f of files) {
							uploaded.push((await this.upload_private_file(f)).file_url);
						}
					} catch (e) {
						frappe.msgprint(
							__("Upload failed: {0}", [frappe.utils.escape_html(e.message || "")])
						);
						return;
					}
				}
				d.hide();
				frappe.call({
					method: "duty_board.api.create_issue",
					args: {
						title: v.title,
						customer: v.customer,
						severity: v.severity,
						due_date: v.due_date || null,
						description: v.description || null,
						assignees:
							v.assignees && v.assignees.length ? JSON.stringify(v.assignees) : null,
						source_type: prefill.source_type || "Manual",
						source: prefill.source || null,
						attachments: uploaded.length ? JSON.stringify(uploaded) : null,
					},
					callback: (r) => {
						if (r.message) {
							frappe.show_alert(
								{ message: __("Issue {0} created", [r.message.name]), indicator: "green" },
								5
							);
							this.touch_issues();
						}
					},
				});
			},
		});
		d.show();

		this._pending_issue_files = [];
		const MAX = 25 * 1024 * 1024;
		const $area = $(d.fields_dict.attach_html.wrapper).html(`
			<div class="duty-attach-area">
				<label class="btn btn-xs btn-default">📎 ${__("Attach image / file")}<input type="file" multiple hidden></label>
				<div class="duty-pending-files"></div>
				<div class="text-muted duty-attach-hint">${__("Tip: paste a screenshot straight into the description box.")}</div>
			</div>
		`);
		const add_file = (f) => {
			if (f.size > MAX) {
				frappe.msgprint(__("{0} is too large (max 25 MB).", [frappe.utils.escape_html(f.name)]));
				return;
			}
			this._pending_issue_files.push(f);
			render_chips();
		};
		const render_chips = () => {
			const $c = $area.find(".duty-pending-files").empty();
			this._pending_issue_files.forEach((f, ix) => {
				const $chip = $(
					`<span class="duty-file-chip">📎 ${frappe.utils.escape_html(f.name)} <a>×</a></span>`
				).appendTo($c);
				$chip.find("a").on("click", () => {
					this._pending_issue_files.splice(ix, 1);
					render_chips();
				});
			});
		};
		$area.find("input[type=file]").on("change", (e) => {
			[...e.target.files].forEach(add_file);
			e.target.value = "";
		});
		const $desc = d.fields_dict.description.$input;
		$desc.on("paste", (e) => {
			const items = (e.originalEvent.clipboardData || {}).items || [];
			for (const it of items) {
				if (it.kind === "file") {
					const f = it.getAsFile();
					if (f) {
						e.preventDefault();
						add_file(f);
						break;
					}
				}
			}
		});
	}

	issue_detail_dialog(name) {
		const d = new frappe.ui.Dialog({ title: name, size: "large" });
		const render = (x) => {
			const today = frappe.datetime.get_today();
			const overdue = x.due_date && x.due_date < today && ["Open", "In Progress"].includes(x.status);
			const names = (x.assignees || [])
				.map(
					(u) =>
						`<span style="color:${this.user_color(u)}">${frappe.utils.escape_html((this.name_map[u] || u).split(" ")[0])}</span>`
				)
				.join(", ");
			const i_am_working = (x.working || []).includes(frappe.session.user);
			const working_names = (x.working || [])
				.map(
					(u) =>
						`<span style="color:${this.user_color(u)}">${frappe.utils.escape_html((this.name_map[u] || u).split(" ")[0])}</span>`
				)
				.join(", ");
			$(d.body).html(`
				<div class="duty-issue-detail">
					<div class="duty-issue-detail-head">
						<span class="duty-sev duty-sev-${(x.severity || "medium").toLowerCase()}">${__(x.severity)}</span>
						<b>${frappe.utils.escape_html(x.title)}</b>
						<span class="duty-task-customer">${frappe.utils.escape_html(x.customer || "")}</span>
						<span class="duty-issue-status">${__(x.status)}</span>
					</div>
					<div class="text-muted duty-issue-meta">
						${__("Raised by")} ${frappe.utils.escape_html((this.name_map[x.raised_by] || x.raised_by || "").split(" ")[0])}
						· ${frappe.datetime.str_to_user(x.created)}
						${x.due_date ? ` · ${__("Due")} <span class="${overdue ? "duty-issue-overdue" : ""}">${frappe.datetime.str_to_user(x.due_date)}</span>` : ""}
						${x.source_type && x.source_type !== "Manual" ? ` · ${__("From")} ${__(x.source_type)}` : ""}
					</div>
					${names ? `<div class="duty-issue-meta">${__("Assigned to")}: ${names}</div>` : ""}
					${working_names ? `<div class="duty-issue-meta">⏱ ${__("Working on it now")}: ${working_names}</div>` : ""}
					<div class="duty-issue-meta"><a class="duty-issue-vis">${x.client_visible ? "👁 " + __("Client-visible — click to hide") : "🙈 " + __("Hidden from client — click to publish")}</a></div>
					${x.description ? `<div class="duty-issue-desc">${frappe.utils.escape_html(x.description)}</div>` : ""}
					${
						(x.attachments || []).length
							? `<div class="duty-issue-files">${x.attachments
									.map((f) =>
										f.is_image
											? `<a href="${f.file_url}" target="_blank"><img src="${f.file_url}" title="${frappe.utils.escape_html(f.file_name)}"></a>`
											: `<a href="${f.file_url}" target="_blank" class="duty-issue-filelink">📎 ${frappe.utils.escape_html(f.file_name)}</a>`
									)
									.join("")}</div>`
							: ""
					}
					${x.resolution ? `<div class="duty-issue-resolution"><b>${__("Resolution")}:</b> ${frappe.utils.escape_html(x.resolution)}${x.resolved_at ? ` <span class="text-muted">(${frappe.datetime.str_to_user(x.resolved_at)})</span>` : ""}</div>` : ""}
					<div class="duty-issue-actions">
						${["Open", "In Progress"].includes(x.status) && !i_am_working ? `<button class="btn btn-sm btn-default duty-issue-start">▶ ${__("Start work")}</button>` : ""}
						${i_am_working ? `<button class="btn btn-sm btn-default duty-issue-stopwork">⏸ ${__("Stop work")}</button>` : ""}
						${["Open", "In Progress"].includes(x.status) ? `<button class="btn btn-sm btn-primary" data-act="Resolved">${__("Resolve")}</button>` : ""}
						${["Open", "In Progress", "Resolved"].includes(x.status) ? `<button class="btn btn-sm btn-default" data-act="Closed">${__("Close")}</button>` : ""}
						${["Resolved", "Closed"].includes(x.status) ? `<button class="btn btn-sm btn-default" data-act="Open">${__("Reopen")}</button>` : ""}
						<button class="btn btn-sm btn-default duty-issue-edit">✎ ${__("Edit")}</button>
						${this.issue_is_mine(x) || frappe.user.has_role("System Manager") ? `<label class="btn btn-sm btn-default duty-issue-attach">📎 ${__("Add file")}<input type="file" hidden></label>` : ""}
					</div>
				</div>
			`);
			$(d.body)
				.find(".duty-issue-actions button[data-act]")
				.on("click", (e) => {
					const act = $(e.currentTarget).data("act");
					const apply = (resolution) =>
						frappe.call({
							method: "duty_board.api.update_issue_status",
							args: { name: name, status: act, resolution: resolution || null },
							callback: (r) => {
								if (r.message) render(r.message);
								this.touch_issues();
							},
						});
					if (act === "Resolved") {
						frappe.prompt(
							{
								fieldname: "resolution",
								fieldtype: "Small Text",
								label: __("What was done?"),
								reqd: 1,
							},
							(v) => apply(v.resolution),
							__("Resolve Issue"),
							__("Resolve")
						);
					} else {
						apply();
					}
				});
			const work_call = (method) =>
				frappe.call({
					method: `duty_board.api.${method}`,
					args: { name: name },
					callback: (r) => {
						if (r.message) render(r.message);
						this.touch_issues();
						if (this._open_room) this.load_client_room(this._open_room);
					},
				});
			$(d.body).find(".duty-issue-vis").on("click", () =>
				frappe.call({
					method: "duty_board.api.set_issue_visibility",
					args: { name: name, visible: x.client_visible ? 0 : 1 },
					callback: (r) => {
						if (r.message) render(r.message);
						if (this._open_room) this.load_client_room(this._open_room);
					},
				})
			);
			$(d.body).find(".duty-issue-start").on("click", () => work_call("start_issue_work"));
			$(d.body).find(".duty-issue-stopwork").on("click", () => work_call("stop_issue_work"));
			$(d.body).find(".duty-issue-attach input").on("change", async (e) => {
				const f = e.target.files[0];
				e.target.value = "";
				if (!f) return;
				if (f.size > 25 * 1024 * 1024) {
					frappe.msgprint(__("File too large (max 25 MB)."));
					return;
				}
				try {
					const up = await this.upload_private_file(f);
					frappe.call({
						method: "duty_board.api.attach_to_issue",
						args: { name: name, file_url: up.file_url },
						callback: (r) => r.message && render(r.message),
					});
				} catch (err) {
					frappe.msgprint(__("Upload failed: {0}", [frappe.utils.escape_html(err.message || "")]));
				}
			});
			$(d.body).find(".duty-issue-edit").on("click", () => {
				const ed = new frappe.ui.Dialog({
					title: __("Edit Issue"),
					fields: [
						{
							fieldname: "severity",
							fieldtype: "Select",
							label: __("Severity"),
							options: "Low\nMedium\nHigh\nCritical",
							default: x.severity,
						},
						{
							fieldname: "due_date",
							fieldtype: "Date",
							label: __("Due Date"),
							default: x.due_date || "",
						},
						{
							fieldname: "add_assignees",
							fieldtype: "MultiSelectList",
							label: __("Add assignees"),
							get_data: () =>
								this.team_members().map((t) => ({ value: t.user, description: t.full_name })),
						},
					],
					primary_action_label: __("Save"),
					primary_action: (v) => {
						ed.hide();
						frappe.call({
							method: "duty_board.api.update_issue",
							args: {
								name: name,
								severity: v.severity,
								due_date: v.due_date || null,
								add_assignees:
									v.add_assignees && v.add_assignees.length
										? JSON.stringify(v.add_assignees)
										: null,
							},
							callback: (r) => {
								if (r.message) render(r.message);
								this.touch_issues();
							},
						});
					},
				});
				ed.show();
			});
		};
		frappe.call({
			method: "duty_board.api.get_issue",
			args: { name: name },
			callback: (r) => r.message && render(r.message),
		});
		d.show();
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
							${t.todo ? '<span class="duty-plan-tag">' + __("Plan") + "</span> " : ""}
							${frappe.utils.escape_html(t.activity)}
							${t.customer ? `<span class="duty-task-customer">${frappe.utils.escape_html(t.customer)}</span>` : ""}
						</div>
						<div class="text-muted duty-task-since">
							${__("Running")}: <b>${this.fmt_duration(t.seconds)}</b>
							· ${__("Started")} ${this.fmt_time(t.start_time)}
						</div>
					</div>
					<div class="duty-task-actions">
						${t.issue ? `<a class="duty-task-issuechip" title="${__("Open issue")}">${t.issue}</a>` : ""}
						${t.card ? `<a class="duty-task-issuechip" style="border-color:#a7f3d0;color:#0f766e;background:#ecfdf5" data-card="${t.card}" title="${__("Open project card")}">📁</a>` : ""}
						<button class="btn btn-default duty-issue-btn" title="${__("Raise issue from this task")}">⚠</button>
						<button class="btn btn-default duty-note-btn" title="${__("Task notes")}">📝${t.notes ? " " + t.notes : ""}</button>
						<button class="btn btn-default duty-invite-btn" title="${__("Invite a colleague to this task")}">👤+</button>
						<button class="btn btn-default duty-taskcust-btn" title="${__("Set / change customer")}">✎</button>
						<button class="btn btn-default duty-switch-btn">${__("Switch Task")}</button>
						<button class="btn btn-primary duty-stop-btn">${__("Stop")}</button>
					</div>
				</div>
			`);
			$task.find(".duty-stop-btn").on("click", () => this.stop_task_flow());
			$task.find(".duty-switch-btn").on("click", () => this.start_task_dialog(true));
			$task.find(".duty-invite-btn").on("click", () => this.invite_task_dialog());
			$task.find(".duty-taskcust-btn").on("click", () => this.task_customer_dialog(t.customer));
			$task.find(".duty-note-btn").on("click", () => this.note_dialog(t.name, t.activity, true));
			$task.find(".duty-task-issuechip").on("click", (e) => {
				const card = $(e.currentTarget).data("card");
				if (card) {
					frappe.call({
						method: "duty_board.projects.get_card",
						args: { name: card },
						callback: (r) => r.message && this.task_dialog(r.message.project, r.message),
					});
				} else {
					this.issue_detail_dialog(t.issue);
				}
			});
			$task.find(".duty-issue-btn").on("click", () =>
				this.create_issue_dialog({
					title: t.activity,
					customer: t.customer,
					source_type: "Task",
					source: t.name,
				})
			);
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

	todo_chips(t) {
		let chips = "";
		if (t.lead_title)
			chips += `<span class="duty-lead-chip">💼 ${frappe.utils.escape_html(t.lead_title)}</span>`;
		if (t.project)
			chips += `<span class="duty-proj-chip">📁 ${frappe.utils.escape_html(t.project)}</span>`;
		if (t.due_time) chips += `<span class="duty-time-chip">${t.due_time}</span>`;
		if (t.customer)
			chips += `<span class="duty-task-customer">${frappe.utils.escape_html(t.customer)}</span>`;
		if (t.assigned_by && t.assigned_by !== t.user) {
			const who = this.name_map[t.assigned_by] || t.assigned_by;
			chips += `<span class="duty-from-chip">${__("from")} ${frappe.utils.escape_html(who)}</span>`;
		}
		if (t.carry_count > 0)
			chips += `<span class="duty-carry-chip">${__("carried")} ×${t.carry_count}</span>`;
		return chips;
	}

	render_plan(me) {
		const $plan = this.body.find(".duty-plan").empty();
		if (!me) return;
		const todos = this.my_todos || [];
		const done = todos.filter((t) => t.status === "Done").length;
		const open = todos.length - done;

		const rows = todos
			.map(
				(t) => `
				<div class="duty-todo-row ${t.status === "Done" ? "duty-todo-done" : ""}" data-name="${t.name}">
					<input type="checkbox" class="duty-todo-check" ${t.status === "Done" ? "checked" : ""}>
					<span class="duty-todo-desc">${frappe.utils.escape_html(t.description)}</span>
					${this.todo_chips(t)}
					${
						t.status === "Open"
							? `<a class="duty-todo-edit" title="${__("Edit / set customer")}">✎</a><a class="duty-todo-share" title="${__("Invite a colleague")}">👤+</a><a class="duty-todo-carry" title="${__("Move to tomorrow")}">→</a>`
							: ""
					}
					<a class="duty-todo-remove" title="${__("Remove")}">&times;</a>
				</div>`
			)
			.join("");

		const upcoming = (this.my_upcoming || [])
			.map(
				(t) => `
				<div class="duty-todo-row" data-name="${t.name}">
					<span class="duty-upcoming-date">${frappe.datetime.str_to_user(t.date)}</span>
					<span class="duty-todo-desc">${frappe.utils.escape_html(t.description)}</span>
					${this.todo_chips(t)}
					<a class="duty-todo-remove" title="${__("Remove")}">&times;</a>
				</div>`
			)
			.join("");

		const plan_open = localStorage.getItem("duty_plan_open") !== "0";
		$plan.html(`
			<details class="duty-plan-card duty-plan-details" ${plan_open ? "open" : ""}>
				<summary class="duty-plan-head">
					<span>${__("My Plan for Today")}
						${todos.length ? `<span class="duty-plan-count">${done}/${todos.length} ${__("done")}</span>` : ""}
					</span>
				</summary>
				${
					this.overdue_count
						? `<div class="duty-overdue">
							${__("You have {0} unfinished item(s) from previous days.", [this.overdue_count])}
							<button class="btn btn-xs btn-default duty-bring-old">${__("Bring to today")}</button>
						   </div>`
						: ""
				}
				<div class="duty-plan-actions-row">
					${open ? `<a class="duty-carry-all">${__("Carry unfinished → tomorrow")}</a>` : ""}
					<button class="btn btn-xs btn-default duty-todo-more-btn">＋ ${__("More")}</button>
				</div>
				${rows || `<div class="text-muted duty-plan-empty">${__("Nothing planned yet. What do you want to get done today?")}</div>`}
				<div class="duty-plan-add">
					<input type="text" class="form-control duty-todo-input" placeholder="${__("Add a to-do and press Enter...")}">
					<button class="btn btn-default btn-sm duty-todo-add-btn">${__("Add")}</button>
				</div>
				${
					upcoming
						? `<details class="duty-sessions-details"><summary>${__("Upcoming")} (${this.my_upcoming.length})</summary>${upcoming}</details>`
						: ""
				}
			</details>
		`);
		$plan.find(".duty-plan-details").on("toggle", (e) => {
			localStorage.setItem("duty_plan_open", e.target.open ? "1" : "0");
		});

		const add = () => {
			const val = $plan.find(".duty-todo-input").val();
			if (val && val.trim()) this.action("add_todo", { description: val.trim() });
		};
		$plan.find(".duty-todo-add-btn").on("click", add);
		$plan.find(".duty-todo-input").on("keydown", (e) => {
			if (e.key === "Enter") add();
		});
		$plan.find(".duty-todo-more-btn").on("click", () => this.add_todo_dialog());
		$plan.find(".duty-bring-old").on("click", () => this.action("bring_old_todos"));
		$plan.find(".duty-carry-all").on("click", () => {
			frappe.confirm(__("Move all unfinished items to tomorrow?"), () =>
				this.action("carry_all")
			);
		});
		$plan.find(".duty-todo-check").on("change", (e) => {
			const name = $(e.target).closest(".duty-todo-row").data("name");
			this.action("toggle_todo", { name: name, done: e.target.checked ? 1 : 0 });
		});
		$plan.find(".duty-todo-carry").on("click", (e) => {
			const name = $(e.target).closest(".duty-todo-row").data("name");
			this.action("carry_todo", { name: name });
		});
		$plan.find(".duty-todo-remove").on("click", (e) => {
			const name = $(e.target).closest(".duty-todo-row").data("name");
			frappe.confirm(__("Remove this to-do?"), () =>
				this.action("remove_todo", { name: name })
			);
		});
		$plan.find(".duty-todo-edit").on("click", (e) => {
			const name = $(e.target).closest(".duty-todo-row").data("name");
			const t = (this.my_todos || []).find((x) => x.name === name);
			if (t) this.edit_todo_dialog(t);
		});
		$plan.find(".duty-todo-share").on("click", (e) => {
			const name = $(e.target).closest(".duty-todo-row").data("name");
			this.share_todo_dialog(name);
		});
	}

	share_todo_dialog(name) {
		const d = new frappe.ui.Dialog({
			title: __("Invite colleagues to this to-do"),
			fields: [
				{
					fieldname: "users",
					fieldtype: "MultiSelectList",
					label: __("Colleagues"),
					reqd: 1,
					get_data: () =>
						this.team_members().map((x) => ({ value: x.user, description: x.full_name })),
				},
			],
			primary_action_label: __("Invite"),
			primary_action: (v) => {
				d.hide();
				this.action("share_todo", { name: name, users: JSON.stringify(v.users || []) });
			},
		});
		d.show();
	}

	edit_todo_dialog(t) {
		const d = new frappe.ui.Dialog({
			title: __("Edit To-do"),
			fields: [
				{ fieldname: "description", fieldtype: "Data", label: __("To-do"), default: t.description, reqd: 1 },
				{ fieldname: "customer", fieldtype: "Link", label: __("Customer"), options: "Customer", default: t.customer || "" },
				{ fieldname: "due_time", fieldtype: "Time", label: __("Time (optional)"), default: t.due_time || "" },
			],
			primary_action_label: __("Save"),
			primary_action: (v) => {
				d.hide();
				this.action("update_todo", {
					name: t.name,
					description: v.description,
					customer: v.customer || null,
					due_time: v.due_time || null,
				});
			},
		});
		d.show();
	}

	invite_task_dialog() {
		const d = new frappe.ui.Dialog({
			title: __("Invite colleagues to this task"),
			fields: [
				{
					fieldname: "users",
					fieldtype: "MultiSelectList",
					label: __("Colleagues"),
					reqd: 1,
					get_data: () =>
						this.team_members().map((x) => ({ value: x.user, description: x.full_name })),
				},
			],
			primary_action_label: __("Invite"),
			primary_action: (v) => {
				d.hide();
				this.action("invite_to_task", { users: JSON.stringify(v.users || []) });
				frappe.show_alert({ message: __("Invitation sent — it lands on their plan."), indicator: "green" }, 5);
			},
		});
		d.show();
	}

	task_customer_dialog(current) {
		const d = new frappe.ui.Dialog({
			title: __("Set customer for this task"),
			fields: [
				{
					fieldname: "customer",
					fieldtype: "Link",
					label: __("Customer (clear to remove)"),
					options: "Customer",
					default: current || "",
				},
			],
			primary_action_label: __("Save"),
			primary_action: (v) => {
				d.hide();
				this.action("set_task_customer", { customer: v.customer || null });
			},
		});
		d.show();
	}

	add_todo_dialog() {
		const d = new frappe.ui.Dialog({
			title: __("Add To-do"),
			fields: [
				{
					fieldname: "description",
					fieldtype: "Data",
					label: __("To-do"),
					reqd: 1,
				},
				{
					fieldname: "for_users",
					fieldtype: "MultiSelectList",
					label: __("For (leave empty = just you)"),
					get_data: () =>
						this.team_members().map((x) => ({
							value: x.user,
							description: x.full_name,
						})),
					description: __("Pick one or more colleagues — each gets their own copy, marked as from you."),
				},
				{
					fieldname: "date",
					fieldtype: "Date",
					label: __("Date"),
					default: frappe.datetime.get_today(),
					reqd: 1,
				},
				{
					fieldname: "due_time",
					fieldtype: "Time",
					label: __("Time (optional — used for ordering the list)"),
				},
				{
					fieldname: "customer",
					fieldtype: "Link",
					label: __("Customer (optional)"),
					options: "Customer",
				},
			],
			primary_action_label: __("Add"),
			primary_action: (values) => {
				d.hide();
				this.action("add_todo", {
					description: values.description,
					for_users:
						values.for_users && values.for_users.length
							? JSON.stringify(values.for_users)
							: null,
					date: values.date,
					due_time: values.due_time || null,
					customer: values.customer || null,
				});
			},
		});
		d.show();
	}

	render_my_sessions(sessions, me) {
		const $s = this.body.find(".duty-my-sessions").empty();
		if (!me) return;
		sessions = sessions || [];
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
					<a class="duty-session-notes" data-session="${x.name}" title="${__("Notes")}">📝${x.notes ? " " + x.notes : ""}</a>
				</div>`
			)
			.join("");
		$s.html(`
			<details class="duty-sessions-details">
				<summary>${__("My tasks today")} (${sessions.length})</summary>
				${rows || `<div class="text-muted duty-history-empty">${__("No tasks yet today.")}</div>`}
				<div class="duty-history-link"><a>${__("Earlier days ▸")}</a></div>
			</details>
		`);
		$s.find(".duty-session-notes").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const id = $(e.currentTarget).data("session");
			const sess = sessions.find((s) => s.name === id);
			this.note_dialog(id, sess ? sess.activity : "", true);
		});
		$s.find(".duty-history-link a").on("click", () => this.task_history_dialog());
	}

	render_team(rows) {
		const $team = this.body.find(".duty-team").empty();
		if (!rows || !rows.length) {
			$team.html(`<div class="text-muted">${__("No staff found.")}</div>`);
			return;
		}
		rows.forEach((r) => {
			const s = this.status_meta(r.status);
			const $card = $(`
				<div class="duty-card duty-card-click" title="${__("View {0}'s day", [frappe.utils.escape_html(r.full_name)])}">
					<div class="duty-card-head">
						${frappe.avatar(r.user, "avatar-medium")}
						<div class="duty-card-name">
							<div class="duty-name-row">
								<div class="duty-name" style="color:${this.user_color(r.user)}">${frappe.utils.escape_html(r.full_name)}</div>
								${r.user !== frappe.session.user ? `<a class="duty-dm-btn" data-user="${r.user}" data-name="${frappe.utils.escape_html(r.full_name)}" title="${__("Direct message")}">✉<b class="duty-dm-badge" ${(this.dm_unread || {})[r.user] ? "" : 'style="display:none"'}>${(this.dm_unread || {})[r.user] || ""}</b></a>` : ""}
							</div>
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
						${r.summary && r.status === "Done for the Day" ? `<div class="duty-summary">“${frappe.utils.escape_html(r.summary)}”</div>` : ""}
						${r.since ? `<div>${__("Since")} ${this.fmt_time(r.since)}</div>` : `<div>${__("Not clocked in today")}</div>`}
						<div>
							${__("On duty")}: ${this.fmt_duration(r.on_duty_seconds)}${r.breaks ? " · " + __("Breaks") + ": " + r.breaks : ""}
							${r.todos_total ? " · " + __("Plan") + `: ${r.todos_done}/${r.todos_total}` : ""}
						</div>
						<div class="duty-card-more">${__("View day")} ›</div>
					</div>
				</div>
			`).appendTo($team);
			$card.on("click", () => this.show_member(r));
		});
	}

	show_member(r) {
		const todo_rows = (r.todos || [])
			.map(
				(t) => `
				<div class="duty-todo-row ${t.status === "Done" ? "duty-todo-done" : ""}">
					<span class="duty-detail-tick">${t.status === "Done" ? "✅" : "⬜"}</span>
					<span class="duty-todo-desc">${frappe.utils.escape_html(t.description)}</span>
					${this.todo_chips(t)}
				</div>`
			)
			.join("");

		const session_rows = (r.sessions || [])
			.map(
				(x) => `
				<div class="duty-session-row ${!x.end_time ? "duty-session-live" : ""}">
					<span class="duty-session-activity">${frappe.utils.escape_html(x.activity)}</span>
					${x.customer ? `<span class="duty-task-customer">${frappe.utils.escape_html(x.customer)}</span>` : ""}
					<span class="duty-session-time text-muted">
						${this.fmt_time(x.start_time)} – ${x.end_time ? this.fmt_time(x.end_time) : __("now")}
						· ${this.fmt_duration(x.duration)}
					</span>
					<a class="duty-session-notes" data-session="${x.name}" title="${__("Notes")}">📝${x.notes ? " " + x.notes : ""}</a>
				</div>`
			)
			.join("");

		const s = this.status_meta(r.status);
		const d = new frappe.ui.Dialog({
			title: __("{0} — Today", [r.full_name]),
			size: "large",
		});
		$(d.body).html(`
			<div class="duty-detail">
				<div class="duty-detail-status">
					<span class="duty-badge" style="color:${s.color};background:${s.bg}">
						<span class="duty-dot" style="background:${s.color}"></span>${__(r.status)}
					</span>
					${r.reason && r.status === "Away" ? `<span class="duty-reason">· ${frappe.utils.escape_html(r.reason)}</span>` : ""}
					<span class="text-muted">
						· ${__("On duty")}: ${this.fmt_duration(r.on_duty_seconds)}${
							r.breaks ? " · " + __("Breaks") + ": " + r.breaks : ""
						}
					</span>
				</div>
				<div class="duty-detail-title">${__("Plan")} ${r.todos_total ? `(${r.todos_done}/${r.todos_total})` : ""}</div>
				${todo_rows || `<div class="text-muted">${__("No plan recorded today.")}</div>`}
				<div class="duty-detail-title">${__("Tasks Worked On")}</div>
				${session_rows || `<div class="text-muted">${__("No tasks tracked today.")}</div>`}
				${
					r.summary
						? `<div class="duty-detail-title">${__("End of Day Summary")}</div>
						   <div class="duty-summary">“${frappe.utils.escape_html(r.summary)}”</div>`
						: ""
				}
			</div>
		`);
		$(d.body).find(".duty-session-notes").on("click", (e) => {
			e.preventDefault();
			const id = $(e.currentTarget).data("session");
			const sess = (r.sessions || []).find((s) => s.name === id);
			this.note_dialog(id, sess ? sess.activity : "", r.user === frappe.session.user);
		});
		d.show();
	}

	status_meta(status) {
		return (
			{
				"On Duty": { color: "var(--green-600, #2e7d32)", bg: "var(--green-100, #e8f5e9)" },
				Away: { color: "var(--orange-600, #ef6c00)", bg: "var(--orange-100, #fff3e0)" },
				"Done for the Day": { color: "var(--blue-600, #1565c0)", bg: "var(--blue-100, #e3f2fd)" },
				"On Leave": { color: "var(--purple-600, #6b21a8)", bg: "var(--bg-purple, #f3e8fd)" },
				"Off Duty": { color: "var(--gray-600, #757575)", bg: "var(--gray-100, #f5f5f5)" },
			}[status] || { color: "var(--gray-600)", bg: "var(--gray-100)" }
		);
	}

	fmt_stamp(dt) {
		if (!dt) return "";
		const p = frappe.datetime.str_to_user(dt).split(" ");
		return p[0] + (p[1] ? " " + p[1].slice(0, 5) : "");
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
		if ($("#duty-board-style").length) $("#duty-board-style").remove();
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
			.duty-plan-tag {
				display: inline-block; padding: 1px 8px; border-radius: 99px;
				background: var(--blue-100, #e3f2fd); color: var(--blue-600, #1565c0);
				font-size: var(--text-xs); font-weight: 700;
			}
			.duty-task-actions { display: flex; gap: 8px; }
			.duty-plan-card {
				margin-top: 10px; padding: 14px 20px; border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg, 10px); background: var(--card-bg);
			}
			.duty-plan-head {
				font-weight: 600; margin-bottom: 8px; display: flex;
				justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;
			}
			.duty-plan-actions { display: inline-flex; align-items: center; gap: 12px; font-weight: 400; }
			.duty-carry-all { cursor: pointer; font-size: var(--text-sm); color: var(--text-muted); }
			.duty-carry-all:hover { color: var(--text-color); }
			.duty-overdue {
				display: flex; justify-content: space-between; align-items: center; gap: 10px;
				margin-bottom: 10px; padding: 8px 12px; border-radius: 8px; flex-wrap: wrap;
				background: var(--orange-100, #fff3e0); color: var(--orange-700, #e65100);
				font-size: var(--text-sm);
			}
			.duty-time-chip {
				display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 99px;
				background: var(--gray-100, #f5f5f5); color: var(--gray-700, #616161);
				font-size: var(--text-xs); font-weight: 600; font-variant-numeric: tabular-nums;
			}
			.duty-from-chip {
				display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 99px;
				background: var(--blue-100, #e3f2fd); color: var(--blue-700, #1565c0);
				font-size: var(--text-xs); font-weight: 600;
			}
			.duty-carry-chip {
				display: inline-block; margin-left: 6px; padding: 1px 8px; border-radius: 99px;
				background: var(--orange-100, #fff3e0); color: var(--orange-700, #e65100);
				font-size: var(--text-xs); font-weight: 600;
			}
			.duty-upcoming-date {
				font-size: var(--text-xs); color: var(--text-muted); min-width: 82px;
				font-variant-numeric: tabular-nums;
			}
			.duty-plan-details > summary { cursor: pointer; list-style: none; }
			.duty-plan-details > summary::-webkit-details-marker { display: none; }
			.duty-plan-details > summary::after { content: " ▾"; color: var(--text-muted); font-size: var(--text-xs); }
			.duty-plan-details:not([open]) > summary::after { content: " ▸"; }
			.duty-plan-actions-row {
				display: flex; justify-content: flex-end; align-items: center; gap: 12px;
				margin: 6px 0 4px; font-weight: 400;
			}
			.duty-todo-edit, .duty-todo-share {
				cursor: pointer; color: var(--text-muted); padding: 0 4px;
				visibility: hidden; font-size: var(--text-sm);
			}
			.duty-todo-row:hover .duty-todo-edit,
			.duty-todo-row:hover .duty-todo-share { visibility: visible; }
			.duty-todo-carry {
				cursor: pointer; color: var(--text-muted); font-weight: 700;
				padding: 0 6px; visibility: hidden;
			}
			.duty-todo-row:hover .duty-todo-carry { visibility: visible; }
			.duty-plan-count { color: var(--text-muted); font-size: var(--text-sm); font-weight: 500; }
			.duty-plan-empty { padding: 4px 0 8px; }
			.duty-todo-row {
				display: flex; align-items: center; gap: 8px; padding: 6px 2px;
				border-bottom: 1px solid var(--border-color);
			}
			.duty-todo-row:last-of-type { border-bottom: none; }
			.duty-todo-check { margin: 0; cursor: pointer; }
			.duty-todo-desc { flex: 1; }
			.duty-todo-done .duty-todo-desc { text-decoration: line-through; color: var(--text-muted); }
			.duty-todo-remove {
				cursor: pointer; color: var(--text-muted); font-size: 16px;
				padding: 0 6px; visibility: hidden;
			}
			.duty-todo-row:hover .duty-todo-remove { visibility: visible; }
			.duty-plan-add { display: flex; gap: 8px; margin-top: 10px; }
			.duty-plan-add .duty-todo-input { flex: 1; }
			.duty-sessions-details { margin-top: 8px; font-size: var(--text-sm); }
			.duty-layout { display: flex; gap: 16px; align-items: flex-start; }
			.duty-main { flex: 1 1 0; min-width: 0; }
			.duty-side { flex: 0 0 33%; max-width: 33%; position: sticky; top: 56px; }
			.duty-chat-collapsed .duty-side { flex: 0 0 auto; max-width: none; }
			.duty-chat-rail {
				writing-mode: vertical-rl; cursor: pointer; user-select: none;
				border: 1px solid var(--border-color); border-radius: 10px;
				background: var(--card-bg); padding: 14px 8px; font-weight: 600;
				color: var(--text-muted); display: flex; align-items: center; gap: 8px;
			}
			.duty-chat-rail:hover { color: var(--text-color); border-color: var(--gray-400, #bdbdbd); }
			.duty-rail-badge {
				writing-mode: horizontal-tb; min-width: 20px; text-align: center;
				padding: 1px 6px; border-radius: 99px; background: var(--red-500, #ef4444);
				color: #fff; font-size: var(--text-xs); font-weight: 700;
			}
			.duty-chat-card {
				border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg, 10px); background: var(--card-bg);
				padding: 10px 16px; display: flex; flex-direction: column;
				height: calc(100vh - 140px); min-height: 320px;
			}
			.duty-chat-head {
				font-weight: 600; display: flex;
				justify-content: space-between; align-items: center; gap: 10px;
			}
			.duty-chat-collapse {
				cursor: pointer; font-size: 16px; font-weight: 700;
				color: var(--text-muted); padding: 0 4px; margin-left: 8px;
			}
			.duty-chat-collapse:hover { color: var(--text-color); }
			@media (max-width: 991px) {
				.duty-layout { flex-direction: column; }
				.duty-side { position: static; flex: 1 1 auto; max-width: 100%; width: 100%; }
				.duty-left { position: static; flex: 1 1 auto; max-width: 100%; width: 100%; order: 2; }
				.duty-issues-card { height: auto; }
				.duty-issues-list { max-height: 300px; }
				.duty-issues-rail { writing-mode: horizontal-tb; justify-content: center; padding: 8px 14px; width: 100%; }
				.duty-chat-card { height: auto; }
				.duty-chat-list { max-height: 260px; }
				.duty-chat-rail { writing-mode: horizontal-tb; justify-content: center; padding: 8px 14px; width: 100%; }
			}
			@media (max-width: 767px) {
				body.duty-mobile .page-head { display: none; }
				body.duty-mobile .duty-board { padding-bottom: 76px; }
				.duty-tabbar {
					position: fixed; left: 0; right: 0; bottom: 0; z-index: 100;
					display: flex; background: var(--card-bg, #fff);
					border-top: 1px solid var(--border-color);
					padding: 6px 0 calc(6px + env(safe-area-inset-bottom));
					box-shadow: 0 -2px 10px rgba(0,0,0,0.06);
				}
				.duty-tabbar a {
					flex: 1; text-align: center; font-size: 11px; color: var(--text-muted);
					text-decoration: none; display: flex; flex-direction: column;
					align-items: center; gap: 2px; position: relative;
				}
				.duty-tabbar a span { font-size: 20px; line-height: 1; filter: grayscale(1); opacity: 0.75; }
				.duty-tabbar a.active { color: #0F5C55; font-weight: 700; }
				.duty-tabbar a.active span { filter: none; opacity: 1; }
				.duty-tab-badge {
					position: absolute; top: -3px; right: 22%;
					background: var(--red-500, #ef4444); color: #fff; border-radius: 99px;
					min-width: 16px; padding: 0 4px; font-size: 10px; line-height: 16px; font-style: normal;
				}
				.duty-board[data-mtab] .duty-left, .duty-board[data-mtab] .duty-side,
				.duty-board[data-mtab] .duty-plan, .duty-board[data-mtab] .duty-my-sessions,
				.duty-board[data-mtab] .duty-me, .duty-board[data-mtab] .duty-task,
				.duty-board[data-mtab] .duty-team-title, .duty-board[data-mtab] .duty-team,
				.duty-board[data-mtab] .duty-updated { display: none; }
				.duty-board[data-mtab="board"] .duty-me,
				.duty-board[data-mtab="board"] .duty-task,
				.duty-board[data-mtab="board"] .duty-team-title,
				.duty-board[data-mtab="board"] .duty-updated { display: block; }
				.duty-board[data-mtab="board"] .duty-team { display: grid; }
				.duty-board[data-mtab="plan"] .duty-plan,
				.duty-board[data-mtab="plan"] .duty-my-sessions { display: block; }
				.duty-board.duty-layout[data-mtab] { display: block; }
				.duty-board[data-mtab="issues"] .duty-left { display: block; }
				.duty-board[data-mtab="chat"] .duty-side { display: block; }
				.duty-board[data-mtab="issues"] .duty-left,
				.duty-board[data-mtab="chat"] .duty-side {
					position: static; width: 100%; max-width: 100%; flex: none;
				}
				.duty-board[data-mtab="issues"] .duty-issues-toolbar-row .duty-issue-scope,
				.duty-board[data-mtab="issues"] .duty-issue-filter,
				.duty-board[data-mtab="issues"] .duty-issue-user { width: 100%; }
				.duty-board[data-mtab="issues"] .duty-issues-rail { display: none !important; }
				.duty-board[data-mtab="chat"] .duty-chat-rail { display: none !important; }
				.duty-board[data-mtab="chat"] .duty-chat-card { height: calc(100vh - 175px); min-height: 0; }
				.duty-board[data-mtab="issues"] .duty-issues-card { height: calc(100vh - 175px); min-height: 0; }
				.duty-chat-collapse, .duty-issues-collapse { display: none; }
				.duty-chat-input, .duty-todo-input, .duty-search-input { font-size: 16px; }
				.duty-tabbar a, .duty-todo-row, .duty-issue-row, .duty-msg { -webkit-tap-highlight-color: rgba(15,92,85,0.1); }
			}
			.duty-chat-badge {
				display: inline-block; min-width: 20px; text-align: center; padding: 1px 7px;
				border-radius: 99px; background: var(--red-500, #ef4444); color: #fff;
				font-size: var(--text-xs); font-weight: 700; margin-left: 6px;
			}
			.duty-chat-tools a { font-size: var(--text-xs); color: var(--text-muted); cursor: pointer; font-weight: 400; }
			.duty-chat-list {
				flex: 1 1 auto; overflow-y: auto; margin: 10px 0;
				border-top: 1px solid var(--border-color); padding-top: 8px;
			}
			.duty-load-earlier { text-align: center; padding: 4px 0 8px; }
			.duty-load-earlier a { cursor: pointer; font-size: var(--text-xs); color: var(--text-muted); }
			.duty-load-earlier a:hover { color: var(--text-color); }
			.duty-msg { padding: 4px 2px; font-size: var(--text-sm); line-height: 1.5; }
			.duty-msg-who { font-weight: 700; color: var(--text-color); margin-right: 6px; }
			.duty-msg-mine .duty-msg-who { color: var(--green-600, #2e7d32); }
			.duty-msg-time { margin-left: 8px; font-size: var(--text-xs); color: var(--text-muted); }
			.duty-chat-send { display: flex; gap: 8px; align-items: flex-end; }
			.duty-chat-input { resize: none; overflow-y: auto; max-height: 120px; line-height: 1.45; }
			.duty-msg-text { white-space: pre-wrap; word-break: break-word; color: #000; }
			[data-theme="dark"] .duty-msg-text { color: var(--text-color); }
			.duty-chat-input-wrap { flex: 1; position: relative; }
			.duty-attach-btn { margin: 0; cursor: pointer; }
			.duty-mention-menu {
				position: absolute; bottom: 100%; left: 0; margin-bottom: 4px; z-index: 100;
				background: var(--card-bg, #fff); border: 1px solid var(--border-color);
				border-radius: 8px; box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,0.12));
				min-width: 220px; overflow: hidden;
			}
			.duty-mention-opt { padding: 7px 12px; cursor: pointer; font-size: var(--text-sm); }
			.duty-mention-opt.active, .duty-mention-opt:hover { background: var(--gray-100, #f5f5f5); }
			.duty-mention {
				color: var(--blue-600, #1565c0); font-weight: 700;
				background: var(--blue-100, #e3f2fd); border-radius: 4px; padding: 0 3px;
			}
			.duty-msg-mentioned { background: var(--yellow-50, #fffbeb); border-radius: 6px; }
			.duty-msg-new { background: var(--blue-50, #eff6ff); border-radius: 6px; }
			.duty-new-divider {
				display: flex; align-items: center; gap: 8px; margin: 8px 0;
				color: var(--red-500, #ef4444); font-size: var(--text-xs);
				font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
			}
			.duty-new-divider::before, .duty-new-divider::after {
				content: ""; flex: 1; border-top: 1px solid var(--red-300, #fca5a5);
			}
			.duty-msg-quote {
				border-left: 3px solid var(--gray-400, #bdbdbd); color: var(--text-muted);
				font-size: var(--text-xs); padding: 2px 8px; margin: 2px 0 3px; font-style: italic;
			}
			.duty-search-bar { display: flex; gap: 6px; align-items: center; margin-top: 8px; }
			.duty-search-bar .duty-search-input { flex: 1; }
			.duty-search-close { cursor: pointer; font-size: 18px; font-weight: 700; color: var(--text-muted); padding: 0 6px; }
			.duty-search-notice {
				margin-top: 6px; padding: 4px 8px; border-radius: 6px;
				background: var(--gray-100, #f5f5f5); color: var(--text-muted); font-size: var(--text-xs);
			}
			.duty-msg-seen {
				margin-left: 8px; font-size: var(--text-xs);
				color: var(--blue-500, #3b82f6); font-weight: 600; cursor: default;
			}
			.duty-msg-react {
				cursor: pointer; margin-left: 6px; visibility: hidden; font-size: var(--text-sm);
				filter: grayscale(1); opacity: 0.7;
			}
			.duty-msg:hover .duty-msg-react { visibility: visible; }
			.duty-msg { position: relative; }
			.duty-react-picker {
				position: absolute; right: 8px; top: -34px; z-index: 100;
				background: var(--card-bg, #fff); border: 1px solid var(--border-color);
				border-radius: 99px; box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,0.12));
				padding: 4px 10px; display: flex; gap: 8px; font-size: 18px;
			}
			.duty-react-picker span { cursor: pointer; }
			.duty-react-picker span:hover { transform: scale(1.25); }
			.duty-msg-reactions { margin: 2px 0 2px 2px; display: flex; gap: 6px; flex-wrap: wrap; }
			.duty-react-chip {
				cursor: pointer; border: 1px solid var(--border-color); border-radius: 99px;
				padding: 0 8px; font-size: var(--text-xs); background: var(--gray-100, #f5f5f5);
			}
			.duty-react-chip.duty-react-mine {
				border-color: var(--blue-500, #3b82f6); background: var(--blue-100, #e3f2fd);
			}
			.duty-msg-reply {
				cursor: pointer; color: var(--text-muted); margin-left: 8px;
				visibility: hidden; font-size: var(--text-sm);
			}
			.duty-msg:hover .duty-msg-reply { visibility: visible; }
			.duty-msg-attach { margin: 4px 0 2px; }
			.duty-msg-attach img {
				max-width: 260px; max-height: 180px; border-radius: 8px;
				border: 1px solid var(--border-color); display: block;
			}
			.duty-msg-attach video {
				max-width: 320px; max-height: 220px; border-radius: 8px;
				border: 1px solid var(--border-color); display: block; background: #000;
			}
			.duty-reply-bar, .duty-attach-bar {
				font-size: var(--text-xs); color: var(--text-muted);
				padding: 4px 8px; margin-bottom: 6px; border-radius: 6px;
				background: var(--gray-100, #f5f5f5);
			}
			.duty-reply-bar a, .duty-attach-bar a { cursor: pointer; margin-left: 8px; font-weight: 700; }
			.duty-sessions-details summary { cursor: pointer; color: var(--text-muted); }
			.duty-session-row { padding: 6px 4px; border-bottom: 1px solid var(--border-color); }
			.duty-session-live .duty-session-activity { font-weight: 600; }
			.duty-session-notes {
				cursor: pointer; margin-left: 8px; color: var(--text-muted);
				font-size: var(--text-xs); text-decoration: none;
			}
			.duty-session-notes:hover { color: var(--text-color); }
			.duty-left { flex: 0 0 25%; max-width: 25%; position: sticky; top: 56px; }
			.duty-issues-collapsed .duty-left { flex: 0 0 auto; max-width: none; }
			.duty-issues-rail {
				writing-mode: vertical-rl; cursor: pointer; user-select: none;
				border: 1px solid var(--border-color); border-radius: 10px;
				background: var(--card-bg); padding: 14px 8px; font-weight: 600;
				color: var(--text-muted); display: flex; align-items: center; gap: 8px;
			}
			.duty-issues-rail:hover { color: var(--text-color); border-color: var(--gray-400, #bdbdbd); }
			.duty-issues-card {
				border: 1px solid var(--border-color);
				border-radius: var(--border-radius-lg, 10px); background: var(--card-bg);
				padding: 10px 16px; display: flex; flex-direction: column;
				height: calc(100vh - 140px); min-height: 320px;
			}
			.duty-issues-toolbar { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
			.duty-issues-toolbar-row { display: flex; gap: 8px; align-items: center; }
			.duty-issues-toolbar-row .duty-issue-scope { flex: 1; }
			.duty-ist-resolved { background: var(--green-100, #e8f5e9); color: var(--green-700, #2e7d32); }
			.duty-ist-closed { background: var(--gray-200, #eeeeee); color: var(--gray-700, #616161); }
			.duty-issues-list {
				flex: 1 1 auto; overflow-y: auto; margin-top: 8px;
				border-top: 1px solid var(--border-color); padding-top: 4px;
			}
			.duty-issues-collapse {
				cursor: pointer; font-size: 16px; font-weight: 700;
				color: var(--text-muted); padding: 0 4px;
			}
			.duty-issues-collapse:hover { color: var(--text-color); }
			.duty-issue-raised {
				font-size: var(--text-xs); color: var(--text-muted);
				font-variant-numeric: tabular-nums; margin-left: auto;
			}
			.duty-issue-row {
				display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
				padding: 7px 4px; border-bottom: 1px solid var(--border-color); cursor: pointer;
			}
			.duty-issue-row:hover { background: var(--gray-50, #fafafa); }
			.duty-issue-mine { border-left: 3px solid var(--blue-400, #60a5fa); padding-left: 8px; }
			.duty-issue-title { font-weight: 600; flex: 1; min-width: 140px; }
			.duty-issue-who, .duty-issue-meta { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-issue-status {
				font-size: var(--text-xs); font-weight: 700; padding: 1px 8px; border-radius: 99px;
				background: var(--blue-100, #e3f2fd); color: var(--blue-700, #1565c0);
			}
			.duty-issue-due { font-size: var(--text-xs); color: var(--text-muted); font-variant-numeric: tabular-nums; }
			.duty-issue-overdue { color: var(--red-600, #dc2626); font-weight: 700; }
			.duty-sev {
				font-size: var(--text-xs); font-weight: 700; padding: 1px 8px; border-radius: 99px;
				text-transform: uppercase; letter-spacing: 0.03em;
			}
			.duty-sev-low { background: var(--gray-100, #f5f5f5); color: var(--gray-700, #616161); }
			.duty-sev-medium { background: var(--blue-100, #e3f2fd); color: var(--blue-700, #1565c0); }
			.duty-sev-high { background: var(--orange-100, #fff3e0); color: var(--orange-700, #e65100); }
			.duty-sev-critical { background: var(--red-100, #fee2e2); color: var(--red-700, #b91c1c); }
			.duty-msg-issue {
				cursor: pointer; margin-left: 6px; visibility: hidden;
				font-size: var(--text-sm); opacity: 0.7;
			}
			.duty-msg:hover .duty-msg-issue { visibility: visible; }
			.duty-msg-del {
				cursor: pointer; visibility: hidden; font-size: var(--text-xs);
				margin-left: 4px; opacity: 0.6; text-decoration: none;
			}
			.duty-msg-del:hover { opacity: 1; }
			.duty-msg:hover .duty-msg-del { visibility: visible; }
			.duty-issue-detail-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: var(--text-base); }
			.duty-issue-meta { margin-top: 4px; }
			.duty-issue-desc { margin: 10px 0; white-space: pre-wrap; }
			.duty-issue-resolution {
				margin: 10px 0; padding: 8px 12px; border-radius: 8px;
				background: var(--green-100, #e8f5e9); font-size: var(--text-sm); white-space: pre-wrap;
			}
			.duty-issue-actions { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; align-items: center; }
			.duty-task-issuechip {
				cursor: pointer; font-size: var(--text-xs); font-weight: 700;
				border: 1px solid var(--orange-300, #fdba74); color: var(--orange-700, #e65100);
				background: var(--orange-100, #fff3e0); border-radius: 99px; padding: 3px 10px;
				align-self: center;
			}
			.duty-issue-actions .duty-issue-attach { margin: 0; }
			.duty-issue-files { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
			.duty-issue-files img {
				max-width: 180px; max-height: 130px; border-radius: 8px;
				border: 1px solid var(--border-color); display: block;
			}
			.duty-issue-filelink {
				border: 1px solid var(--border-color); border-radius: 8px;
				padding: 6px 10px; font-size: var(--text-sm); align-self: center;
			}
			.duty-attach-area { margin-top: 4px; }
			.duty-attach-hint { font-size: var(--text-xs); margin-top: 4px; }
			.duty-pending-files { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
			.duty-file-chip {
				border: 1px solid var(--border-color); border-radius: 99px;
				padding: 2px 10px; font-size: var(--text-xs); background: var(--gray-100, #f5f5f5);
			}
			.duty-file-chip a { cursor: pointer; font-weight: 700; margin-left: 4px; }
			.duty-history-link { margin-top: 8px; font-size: var(--text-xs); }
			.duty-history-link a { cursor: pointer; color: var(--text-muted); }
			.duty-history-link a:hover { color: var(--text-color); }
			.duty-history-list { max-height: 60vh; overflow-y: auto; }
			.duty-history-day {
				font-weight: 700; margin: 12px 0 4px; color: var(--text-muted);
				font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.04em;
			}
			.duty-proj-chip {
				font-size: var(--text-xs); border-radius: 99px; padding: 1px 8px;
				background: #ecfdf5; color: #0f766e; font-weight: 600;
			}
			.duty-projects { padding-bottom: 76px; }
			.duty-proj-head { display: flex; gap: 12px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 12px; }
			.duty-proj-tabs { display: flex; gap: 8px; flex-wrap: wrap; flex: 1; }
			.duty-proj-tab {
				border: 1px solid var(--border-color); border-radius: 10px; padding: 8px 14px;
				background: var(--card-bg); cursor: pointer; text-decoration: none;
				display: flex; flex-direction: column; gap: 2px; min-width: 140px;
			}
			.duty-proj-tab.active { border-color: #0F5C55; box-shadow: 0 0 0 1px #0F5C55 inset; }
			.duty-proj-name { font-weight: 700; color: var(--text-color); }
			.duty-proj-stats { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-proj-over { color: var(--red-600, #dc2626); font-weight: 700; }
			.duty-proj-bar {
				display: block; height: 5px; border-radius: 99px;
				background: var(--gray-200, #e5e7eb); overflow: hidden; margin-top: 4px;
			}
			.duty-proj-bar span { display: block; height: 100%; border-radius: 99px; }
			.duty-proj-target { font-size: var(--text-xs); color: var(--text-muted); font-weight: 600; }
			.duty-kb-working { font-weight: 600; }
			.duty-kb-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
			.duty-kb-bar a { cursor: pointer; font-size: var(--text-xs); color: var(--text-muted); }
			.duty-kanban { display: flex; gap: 12px; align-items: flex-start; overflow-x: auto; padding-bottom: 8px; }
			.duty-kb-col {
				flex: 1 1 0; min-width: 230px; background: var(--gray-50, #fafafa);
				border: 1px solid var(--border-color); border-radius: 10px; padding: 10px;
			}
			.duty-kb-col-head { font-weight: 700; margin-bottom: 8px; display: flex; justify-content: space-between; }
			.duty-kb-col[data-col="To Do"] { border-top: 3px solid #64748b; }
			.duty-kb-col[data-col="To Do"] .duty-kb-col-head { color: #475569; }
			.duty-kb-col[data-col="In Progress"] { border-top: 3px solid #d97706; }
			.duty-kb-col[data-col="In Progress"] .duty-kb-col-head { color: #b45309; }
			.duty-kb-col[data-col="Completed"] { border-top: 3px solid #16a34a; }
			.duty-kb-col[data-col="Completed"] .duty-kb-col-head { color: #15803d; }
			.duty-kb-col[data-col="Suspended"] { border-top: 3px solid #7c3aed; }
			.duty-kb-col[data-col="Suspended"] .duty-kb-col-head { color: #6d28d9; }
			.duty-clients { padding-bottom: 76px; display: flex; gap: 14px; align-items: flex-start; }
			.duty-cr-list { flex: 0 0 280px; display: flex; flex-direction: column; gap: 8px; }
			.duty-cr-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
			.duty-cr-item {
				border: 1px solid var(--border-color); border-radius: 10px; padding: 10px 12px;
				background: var(--card-bg); cursor: pointer; text-decoration: none;
				display: flex; flex-direction: column; gap: 2px;
			}
			.duty-cr-item.active { border-color: #0F5C55; box-shadow: 0 0 0 1px #0F5C55 inset; }
			.duty-cr-frozen { opacity: 0.6; }
			.duty-cr-status { font-size: var(--text-xs); font-weight: 700; color: #0369a1; }
			.duty-cr-last { font-size: var(--text-xs); color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.duty-cr-members { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-cr-room { flex: 1; border: 1px solid var(--border-color); border-radius: 12px; background: var(--card-bg); padding: 0 14px 14px; min-width: 0; }
			.duty-cr-ribbon {
				margin: 0 -14px 10px; padding: 7px 14px; border-radius: 12px 12px 0 0;
				background: #fef3c7; color: #92400e; font-size: var(--text-xs); font-weight: 700;
			}
			.duty-cr-head { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
			.duty-cr-taskchips { font-size: var(--text-xs); color: var(--text-muted); font-weight: 600; }
			.duty-cr-tools { margin-left: auto; display: flex; gap: 12px; }
			.duty-cr-tools a { cursor: pointer; font-size: var(--text-xs); font-weight: 600; }
			.duty-cr-tasks { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
			.duty-cr-task {
				display: flex; gap: 10px; align-items: center; padding: 5px 8px;
				border-radius: 8px; cursor: pointer; text-decoration: none;
			}
			.duty-cr-task:hover { background: var(--gray-100, #f5f5f5); }
			.duty-crt-pill { font-size: 10px; font-weight: 700; border-radius: 99px; padding: 2px 9px; flex: none; }
			.duty-crt-queued { background: #f1f5f9; color: #475569; }
			.duty-crt-inprogress { background: #fef3c7; color: #b45309; }
			.duty-crt-done { background: #dcfce7; color: #15803d; }
			.duty-crt-suspended { background: #ede9fe; color: #6d28d9; }
			.duty-crt-title { flex: 1; color: var(--text-color); font-size: var(--text-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.duty-crt-who { font-size: var(--text-xs); color: var(--text-muted); flex: none; }
			.duty-cr-openissues { cursor: pointer; font-size: var(--text-xs); font-weight: 700; margin-top: 2px; }
			.duty-cr-tasksbar { display: flex; gap: 10px; align-items: center; margin-bottom: 6px; }
			.duty-cr-taskstoggle { cursor: pointer; text-decoration: none; color: var(--text-color); }
			.duty-cr-tfilter { width: auto; margin-left: auto; }
			.duty-crt-stamps { flex-basis: 100%; font-size: 10px; color: var(--text-muted); }
			.duty-cr-task { flex-wrap: wrap; }
			.duty-cr-att img { max-width: 220px; max-height: 160px; border-radius: 10px; display: block; margin-top: 6px; border: 1px solid var(--border-color); }
			.duty-cr-attach { cursor: pointer; align-self: center; margin: 0; font-size: 16px; }
			.duty-cr-pending { margin-bottom: 4px; }
			.duty-issue-vis { cursor: pointer; font-weight: 600; }
			.duty-cr-msgs { display: flex; flex-direction: column; gap: 8px; max-height: 42vh; overflow-y: auto; padding: 4px 0 8px; }
			.duty-cr-msg { border-radius: 10px; padding: 7px 11px; max-width: 88%; position: relative; }
			.duty-cr-staff { background: #ecfdf5; align-self: flex-end; }
			.duty-cr-client { background: var(--gray-100, #f3f4f6); align-self: flex-start; }
			.duty-cr-internal { background: #fef9c3; border: 1px dashed #d97706; align-self: flex-end; }
			.duty-cr-msg .duty-msg-who { display: block; font-size: var(--text-xs); font-weight: 700; }
			.duty-cr-mktask { position: absolute; right: -26px; top: 6px; cursor: pointer; text-decoration: none; opacity: 0.5; }
			.duty-cr-msg:hover .duty-cr-mktask { opacity: 1; }
			.duty-cr-compose { display: flex; gap: 8px; align-items: flex-end; }
			.duty-cr-compose textarea { flex: 1; resize: none; font-size: 16px; }
			.duty-cr-int { font-size: var(--text-xs); font-weight: 700; align-self: center; white-space: nowrap; }
			.duty-cr-composing-internal textarea { background: #fef9c3; border-color: #d97706; }
			.duty-cr-mem { padding: 6px 0; border-bottom: 1px dashed var(--border-color); display: flex; gap: 8px; align-items: center; }
			.duty-cr-mem a { margin-left: auto; cursor: pointer; font-size: var(--text-xs); }
			.duty-cr-addmem { display: flex; gap: 6px; margin-top: 10px; }
			.duty-cr-joinlink { display: flex; gap: 6px; }
			.duty-cr-approve { color: var(--green-600, #16a34a); font-weight: 700; cursor: pointer; margin-left: auto; }
			.duty-cr-rejectq { color: var(--red-600, #dc2626); font-weight: 700; cursor: pointer; }
			.duty-cr-reqbadge {
				background: var(--red-500, #ef4444); color: #fff; border-radius: 99px;
				padding: 0 6px; font-size: 10px; font-style: normal;
			}
			@media (max-width: 767px) {
				.duty-clients { flex-direction: column; }
				.duty-cr-list { flex: 1 1 auto; width: 100%; }
				.duty-cr-room { width: 100%; }
			}
			.duty-lead-chip {
				font-size: var(--text-xs); border-radius: 99px; padding: 1px 8px;
				background: #fef3c7; color: #92400e; font-weight: 600;
			}
			.duty-sales { padding-bottom: 76px; }
			.duty-sales-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
			.duty-sales-total { font-size: var(--text-lg); }
			.duty-sales-actions { display: flex; gap: 14px; align-items: center; }
			.duty-sales-arch { cursor: pointer; font-weight: 600; font-size: var(--text-sm); }
			.duty-kb-sum { font-size: var(--text-xs); color: var(--text-muted); font-weight: 600; }
			.duty-sales-kanban .duty-kb-col[data-col="New"] { border-top: 3px solid #64748b; }
			.duty-sales-kanban .duty-kb-col[data-col="New"] .duty-kb-col-head { color: #475569; }
			.duty-sales-kanban .duty-kb-col[data-col="Contacted"] { border-top: 3px solid #0284c7; }
			.duty-sales-kanban .duty-kb-col[data-col="Contacted"] .duty-kb-col-head { color: #0369a1; }
			.duty-sales-kanban .duty-kb-col[data-col="Qualified"] { border-top: 3px solid #0F5C55; }
			.duty-sales-kanban .duty-kb-col[data-col="Qualified"] .duty-kb-col-head { color: #0F5C55; }
			.duty-sales-kanban .duty-kb-col[data-col="Proposal"] { border-top: 3px solid #d97706; }
			.duty-sales-kanban .duty-kb-col[data-col="Proposal"] .duty-kb-col-head { color: #b45309; }
			.duty-sales-kanban .duty-kb-col[data-col="Negotiation"] { border-top: 3px solid #dc2626; }
			.duty-sales-kanban .duty-kb-col[data-col="Negotiation"] .duty-kb-col-head { color: #b91c1c; }
			.duty-lead-card:hover { box-shadow: 0 3px 10px rgba(0,0,0,0.08); transform: translateY(-1px); transition: all 0.12s; }
			.duty-lead-company { font-weight: 700; color: var(--text-color); }
			.duty-lead-value { color: #0F5C55; font-weight: 700; }
			.duty-lead-contact { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-lead-badges { display: flex; gap: 8px; font-size: var(--text-xs); }
			.duty-lead-over { color: var(--red-600, #dc2626); font-weight: 700; }
			.duty-stale { color: #b45309; font-weight: 700; }
			.duty-stale-red { color: var(--red-600, #dc2626); }
			.duty-lead-links { margin-bottom: 10px; font-weight: 600; }
			.duty-lead-section { font-weight: 700; margin: 14px 0 6px; border-top: 1px solid var(--border-color); padding-top: 10px; }
			.duty-lead-task { display: flex; gap: 8px; align-items: center; padding: 4px 0; cursor: pointer; font-weight: normal; }
			.duty-lead-task span:first-of-type { flex: 1; color: var(--text-color); }
			.duty-lead-task-done span:first-of-type { text-decoration: line-through; color: var(--text-muted); }
			.duty-lead-addtask { display: flex; gap: 6px; margin-top: 8px; }
			.duty-lead-addtask .duty-lt-desc { flex: 2; font-size: 16px; }
			.duty-lead-addtask .duty-lt-date, .duty-lead-addtask .duty-lt-time, .duty-lead-addtask .duty-lt-who { flex: 1; min-width: 90px; }
			.duty-lead-addtask { flex-wrap: wrap; }
			.duty-lead-note { padding: 6px 0; border-bottom: 1px dashed var(--border-color); }
			.duty-note-mention { color: #0F5C55; }
			.duty-mention-host { position: relative; }
			.duty-mention-dd {
				position: absolute; bottom: 100%; left: 0; margin-bottom: 4px;
				background: var(--card-bg, #fff); border: 1px solid var(--border-color);
				border-radius: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);
				display: flex; flex-direction: column; min-width: 220px; z-index: 1060;
				overflow: hidden;
			}
			.duty-mention-opt { padding: 7px 14px; cursor: pointer; font-weight: 600; text-decoration: none; }
			.duty-mention-opt:hover { background: var(--gray-100, #f5f5f5); }
			.duty-lead-addnote { margin-top: 8px; }
			.duty-lead-addnote input { font-size: 16px; }
			.duty-lead-close { display: flex; gap: 10px; margin-top: 16px; justify-content: flex-end; }
			.duty-lead-closedrow { display: flex; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-color); flex-wrap: wrap; }
			.duty-lead-closedrow b { flex: 1; }
			.duty-lead-reopen { cursor: pointer; font-size: var(--text-xs); }
			.duty-proj-cust { font-size: var(--text-xs); color: var(--text-color); font-weight: 600; }
			.duty-proj-cust-inline { font-size: var(--text-sm); color: var(--text-muted); font-weight: 600; }
			.duty-kb-count { color: var(--text-muted); font-weight: 600; }
			.duty-kb-add { margin-bottom: 8px; font-size: 16px; }
			.duty-kb-cards { min-height: 40px; display: flex; flex-direction: column; gap: 8px; }
			.duty-kb-over { outline: 2px dashed #0F5C55; outline-offset: -4px; }
			.duty-kb-card {
				background: var(--card-bg, #fff); border: 1px solid var(--border-color);
				border-radius: 8px; padding: 8px 10px; cursor: grab;
			}
			.duty-kb-card:active { cursor: grabbing; }
			.duty-kb-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
			.duty-kb-due { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-kb-title { font-weight: 600; color: var(--text-color); }
			.duty-kb-meta { font-size: var(--text-xs); margin-top: 4px; }
			@media (max-width: 767px) {
				.duty-kb-col { min-width: 240px; flex: 0 0 240px; }
			}
			.duty-name-row { display: flex; align-items: center; gap: 8px; min-width: 0; }
			.duty-name-row .duty-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.duty-dm-btn {
				cursor: pointer; text-decoration: none; font-size: var(--text-sm);
				opacity: 0.5; position: relative; padding: 0 3px; flex: none;
			}
			.duty-dm-btn:hover { opacity: 1; }
			.duty-dm-badge {
				position: absolute; top: -8px; right: -10px;
				background: var(--red-500, #ef4444); color: #fff; border-radius: 99px;
				min-width: 16px; text-align: center; padding: 0 4px;
				font-size: 10px; line-height: 16px; font-style: normal;
			}
			.duty-dm-list {
				max-height: 46vh; min-height: 220px; overflow-y: auto;
				margin-bottom: 10px; border-bottom: 1px solid var(--border-color); padding-bottom: 6px;
			}
			.duty-dm-send { display: flex; gap: 8px; align-items: flex-end; }
			.duty-dm-send textarea { flex: 1; resize: none; font-size: 16px; }
			.duty-note-list { max-height: 300px; overflow-y: auto; }
			.duty-note-item { padding: 7px 0; border-bottom: 1px solid var(--border-color); }
			.duty-note-meta { font-size: var(--text-xs); display: flex; gap: 10px; font-weight: 600; }
			.duty-note-text { white-space: pre-wrap; word-break: break-word; margin-top: 2px; font-size: var(--text-sm); }
			.duty-note-add { display: flex; gap: 8px; margin-top: 12px; align-items: flex-end; }
			.duty-note-add textarea { flex: 1; resize: none; }
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
			.duty-card-click { cursor: pointer; transition: box-shadow 0.15s ease, border-color 0.15s ease; }
			.duty-card-click:hover { border-color: var(--gray-400, #bdbdbd); box-shadow: var(--shadow-sm, 0 1px 4px rgba(0,0,0,0.08)); }
			.duty-card-more { margin-top: 6px; font-size: var(--text-xs); color: var(--text-muted); }
			.duty-detail-status { margin-bottom: 6px; }
			.duty-detail-title {
				margin: 14px 0 6px; font-weight: 600; font-size: var(--text-sm);
				text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted);
			}
			.duty-detail-tick { width: 22px; }
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
			.duty-summary { font-style: italic; color: var(--text-color); margin: 2px 0; }
			.duty-updated { margin-top: 16px; font-size: var(--text-xs); }
			.duty-daynum-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
			.duty-daynum-table td { padding: 7px 4px; border-bottom: 1px solid var(--border-color); }
			.duty-daynum-head td { color: var(--text-muted); font-size: var(--text-sm); border-bottom: none; padding-bottom: 2px; }
			.duty-daynum-short td b { color: var(--red-600, #dc2626); }
			.duty-daynum-ok td b { color: var(--green-600, #2e7d32); }
			.duty-daynum-remark {
				margin-top: 8px; padding: 8px 12px; border-radius: 8px; font-size: var(--text-sm);
			}
			.duty-daynum-warn { background: var(--orange-100, #fff3e0); color: var(--orange-700, #e65100); }
			.duty-daynum-good { background: var(--green-100, #e8f5e9); color: var(--green-700, #2e7d32); }
		</style>`).appendTo("head");
	}
}
