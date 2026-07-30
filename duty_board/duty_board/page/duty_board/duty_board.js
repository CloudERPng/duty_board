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
	page.add_inner_button(__("👤 My Dashboard"), () => board.show_face("me"), __("⇄ View"));
	frappe.call({
		method: "duty_board.accounting.books_access",
		callback: (r) => {
			board.books_acc = (r.message && r.message.allowed && r.message) || null;
			if (board.books_acc) {
				page.add_inner_button(__("📒 Books"), () => board.show_face("books"), __("⇄ View"));
				$('.duty-tabbar a[data-tab="books"]').show();
				if (board.books_acc.manager) {
					page.add_inner_button(__("💰 Cost to serve"), () => board.cost_dialog(), __("⇄ View"));
				}
			}
		},
	});
	frappe.call({
		method: "duty_board.commercial.pricing_queue",
		callback: (r) => {
			const q = r.message || {};
			board.is_pricer = !!q.pricer;
			page.add_inner_button(__("🎓 Team training"), () => board.team_training_dialog(), __("⇄ View"));
			page.add_inner_button(__("📚 Library"), () => board.show_face("library"), __("⇄ View"));
			if (q.pricer) {
				page.add_inner_button(__("💼 CR pricing ({0})", [(q.queue || []).length]), () => board.pricing_dialog(), __("⇄ View"));
			}
		},
	});
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
				<div class="duty-pj-side">
					<div class="duty-pj-sidehead">
						<input type="text" class="form-control input-sm duty-pj-filter" placeholder="${__("Filter projects…")}">
						<button class="btn btn-sm btn-default duty-proj-new" title="${__("New Project")}">＋</button>
					</div>
					<div class="duty-proj-tabs"></div>
				</div>
				<div class="duty-pj-main">
					<div class="duty-pj-title"></div>
					<div class="duty-kanban-wrap"></div>
				</div>
			</div>
		`).appendTo(page.body);
		this.$projects.find(".duty-proj-new").on("click", () => this.new_project_dialog());
		this.$library = $(`<div class="duty-library" style="display:none"></div>`).appendTo(page.body);
		this.$projects.find(".duty-pj-filter").on("input", (e) => {
			this._pj_filter = e.target.value;
			this.render_project_tabs();
		});
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
		this.$me = $(`<div class="duty-me" style="display:none"></div>`).appendTo(page.body);
		this.$books = $(`<div class="duty-books" style="display:none"></div>`).appendTo(page.body);
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
				<div class="duty-chat-typing" style="display:none"></div>
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
		this._last_typing = 0;
		this.$input.on("input", () => {
			const now = Date.now();
			if (now - this._last_typing < 2500) return;
			this._last_typing = now;
			frappe.call({ method: "duty_board.api.duty_typing", freeze: false });
		});
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
		frappe.realtime.on("duty_board_typing", (n) => {
			if (!n || n.user === frappe.session.user) return;
			const $t = $(".duty-chat-typing");
			if (!$t.length) return;
			$t.text(`${n.who} ${__("is typing…")}`).show();
			clearTimeout(this._typing_hide);
			this._typing_hide = setTimeout(() => $t.hide(), 4000);
		});
		frappe.realtime.on("duty_client_typing", (n) => {
			if (!n || !n.room || n.room !== this._open_room) return;
			const me_first = (this.name_map[frappe.session.user] || "").split(" ")[0];
			if (n.staff && n.who === me_first) return;
			const $t = this.$clients.find(".duty-cr-typing");
			if (!$t.length) return;
			$t.text(
				n.client
					? `${n.who} (${__("client")}) ${__("is typing…")}`
					: `${n.who} ${__("is typing…")}`
			).show();
			clearTimeout(this._cr_typing_hide);
			this._cr_typing_hide = setTimeout(() => $t.hide(), 4000);
		});
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
				<a data-tab="clients"><span>🤝</span>${__("Clients")}<b class="duty-tab-badge duty-tab-clients" style="display:none"></b></a>
				<a data-tab="me"><span>👤</span>${__("Me")}</a>
				<a data-tab="books" style="display:none"><span>📒</span>${__("Books")}</a>
			</div>
		`).appendTo("body");
		$bar.find("a").on("click", (e) => {
			const tab = $(e.currentTarget).data("tab");
			if (frappe.get_route_str() !== "duty-board") {
				localStorage.setItem("duty_mtab", tab);
				frappe.set_route("duty-board").then(() => this.set_mtab(tab));
				return;
			}
			this.set_mtab(tab);
		});
		this.set_mtab(localStorage.getItem("duty_mtab") || "board");
		// dim the bar when the user wanders off to other desk screens
		const sync_bar = () => $bar.toggleClass("duty-tabbar-away", frappe.get_route_str() !== "duty-board");
		frappe.router.on("change", sync_bar);
		sync_bar();
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
		} else if (tab === "me") {
			this.show_face("me");
		} else if (tab === "books") {
			this.show_face("books");
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
		const when = this.smart_time(m.creation);
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
				${m.reply_snippet ? `<div class="duty-msg-quote ${m.reply_to ? "duty-msg-quote-link" : ""}" ${m.reply_to ? `data-target="${m.reply_to}"` : ""}>${frappe.utils.escape_html(m.reply_snippet)}</div>` : ""}
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
			$row.find(".duty-msg-time").text(when);
			$row.find(".duty-msg-reply, .duty-msg-react, .duty-msg-issue, .duty-msg-del").remove();
		} else {
			$row.find(".duty-msg-reply").on("click", () => this.set_reply(m));
			$row.find(".duty-msg-quote-link").on("click", (e) => {
				e.stopPropagation();
				const target = $(e.currentTarget).data("target");
				const $t = this.$list.find(`.duty-msg[data-name="${target}"]`);
				if (!$t.length) {
					frappe.show_alert({ message: __("That message is further up — use Load earlier."), indicator: "orange" }, 3);
					return;
				}
				$t[0].scrollIntoView({ behavior: "smooth", block: "center" });
				$t.addClass("duty-msg-flash");
				setTimeout(() => $t.removeClass("duty-msg-flash"), 1600);
			});
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
		this._on_call = data.on_call || null;
		const cr_attn = (data.rooms_unread || 0) + (data.rooms_joins || 0);
		$(".duty-tab-clients").text(cr_attn).toggle(cr_attn > 0);
		this._rooms_joins = data.rooms_joins || 0;
		$(".duty-cr-barjoins").html(
			this._rooms_joins
				? ` <span class="duty-cr-joinpill">🙋 ${this._rooms_joins} ${__("waiting")}</span>`
				: ""
		);
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
								${x.customer ? `<span class="duty-task-customer">${frappe.utils.escape_html(x.customer)}${x.unit && x.unit !== "General" ? ` <span class="duty-cr-unitchip">${frappe.utils.escape_html(x.unit)}</span>` : ""}${x.renewal ? (x.renewal.frozen ? ` <span class="duty-renew duty-renew-frozen">⏸ ${__("FROZEN — renewal overdue")}</span>` : x.renewal.days_left < 0 ? ` <span class="duty-renew duty-renew-over">🔴 ${__("expired")} ${-x.renewal.days_left}d</span>` : x.renewal.days_left <= 14 ? ` <span class="duty-renew duty-renew-warn">⏳ ${__("renews in")} ${x.renewal.days_left}d</span>` : ` <span class="duty-renew duty-renew-calm" title="${frappe.utils.escape_html(x.renewal.date)}">🔄 ${__("renews in")} ${x.renewal.days_left}d</span>`) : ""}</span>` : ""}
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
		const when = this.smart_time(m.creation);
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
		this._cr_last_typing = 0;
		$input.on("input", () => {
			const now = Date.now();
			if (now - this._cr_last_typing < 2500) return;
			this._cr_last_typing = now;
			frappe.call({
				method: "duty_board.client_room.staff_typing",
				args: { name: x.name },
				freeze: false,
			});
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
		const prev_face = this.face;
		if (face === "projects" && prev_face !== "projects") this._pj_open = {};
		if (face === "clients" && prev_face !== "clients") {
			this._cr_open = {};
			Object.keys(localStorage)
				.filter((k) => k.indexOf("duty_cr_fold_") === 0)
				.forEach((k) => localStorage.removeItem(k));
		}
		this.face = face;
		this.body.toggle(face === "board");
		this.$projects.toggle(face === "projects");
		this.$sales.toggle(face === "sales");
		this.$clients.toggle(face === "clients");
		this.$me.toggle(face === "me");
		this.$books.toggle(face === "books");
		if (this.$library) this.$library.toggle(face === "library");
		if (face === "library") this.refresh_library();
		if (face === "books") this.refresh_books();
		if (face === "projects") this.refresh_projects();
		if (face === "sales") this.refresh_sales();
		if (face === "clients") this.refresh_clients();
		if (face === "me") this.refresh_me();
	}

	_me_host() {
		// DOM truth: exactly one .duty-me, attached, bound to this instance
		const $all = $(".duty-me");
		console.log("[duty-me] host nodes found:", $all.length, "| instance node attached:", !!(this.$me && this.$me[0] && document.body.contains(this.$me[0])));
		let $host = $all.filter((i, el) => document.body.contains(el)).last();
		if (!$host.length) {
			$host = $('<div class="duty-me"></div>').appendTo(this.page && this.page.body ? this.page.body : document.body);
			console.log("[duty-me] host rebuilt");
		}
		$(".duty-me").not($host[0]).remove();
		this.$me = $host;
		return $host;
	}

	refresh_me(month) {
		const V = "js v2.59.3";
		console.log("[duty-me]", V, "refresh_me start, month:", month || "(current)");
		this._me_host().show();
		this.$me.html(`<div class="text-muted" style="padding:30px">${__("Loading your dashboard…")} <span style="opacity:.5">(${V})</span></div>`);
		const url = "/api/method/duty_board.api.my_dashboard" + (month ? `?month=${encodeURIComponent(month)}` : "");
		console.log("[duty-me] fetching", url);
		fetch(url, { credentials: "same-origin" })
			.then((res) => {
				console.log("[duty-me] response status", res.status);
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				return res.json();
			})
			.then((j) => {
				console.log("[duty-me] payload keys:", j && j.message ? Object.keys(j.message).join(",") : "NONE");
				if (!j || !j.message) throw new Error("empty payload");
				console.log("[duty-me] render begin");
				this._me_host();
				this.render_my_dashboard(j.message);
				const node = this.$me[0];
				const rect = node.getBoundingClientRect();
				console.log("[duty-me] painted:", this.$me.find(".duty-mtile").length, "tiles | innerHTML:", node.innerHTML.length, "chars | visible height:", Math.round(rect.height), "| offsetParent:", !!node.offsetParent);
				if (rect.height < 60 || !node.offsetParent) {
					console.warn("[duty-me] node invisible — escalating to overlay");
					$(".duty-me-overlay").remove();
					const $ov = $(`
						<div class="duty-me-overlay">
							<div class="duty-me-ovbar"><b>👤 ${__("My Dashboard")}</b><a class="duty-me-ovclose">✕</a></div>
							<div class="duty-me-ovbody"></div>
						</div>`).appendTo(document.body);
					$ov.find(".duty-me-ovclose").on("click", () => $ov.remove());
					this.$me = $ov.find(".duty-me-ovbody");
					this.render_my_dashboard(j.message);
					console.log("[duty-me] overlay tiles:", this.$me.find(".duty-mtile").length);
				}
			})
			.catch((err) => {
				console.error("[duty-me] FAILED:", err);
				this.$me.html(`<div style="color:#b91c1c;padding:30px;white-space:pre-wrap">Dashboard failed: ${frappe.utils.escape_html(err.message)}\n${frappe.utils.escape_html((err.stack || "").split("\n").slice(0, 4).join("\n"))}</div>`);
			});
	}

	render_my_dashboard(m) {
		const esc = frappe.utils.escape_html;
		const t = m.tiles || {};
		const tile = (v, l) => (v === null || v === undefined) ? "" : `<div class="duty-mtile"><b>${esc(String(v))}</b><span>${esc(l)}</span></div>`;
		this.$me.html(`
			<div class="duty-me-head">
				<div>
					<h2>👤 ${esc(m.full_name)}</h2>
					<span class="text-muted">${__("Your work, your numbers — visible to you alone on this view.")}</span>
				</div>
				<div class="duty-me-clock">
					<span class="duty-me-dot ${m.duty && m.duty.on ? "on" : "off"}">●</span>
					<span>${m.duty && m.duty.on ? __("On duty") : __("Off duty")} · ${esc((m.duty || {}).today || "0h 0m")} ${__("today")}</span>
					${m.duty && m.duty.on
						? `<button class="btn btn-sm btn-default duty-me-clockout">${__("Clock Out")}</button>`
						: `<button class="btn btn-sm btn-primary duty-me-clockin">${__("Clock In")}</button>`}
				</div>
			</div>
			<div class="duty-mtiles">
				${tile(t.open_now, __("open now"))}
				${tile(t.in_progress, __("in progress"))}
				${tile(t.resolved_30, __("resolved · 30 days"))}
				${tile(t.avg_res, __("avg resolution"))}
				${tile(t.sla_pct !== null && t.sla_pct !== undefined ? t.sla_pct + "%" : null, __("within SLA"))}
				${tile(t.my_stars !== null && t.my_stars !== undefined ? "★ " + t.my_stars : null, __("client rating") + ` (${t.my_rated_n || 0})`)}
				${tile(t.hours_30, __("hours logged · 30d"))}
				${tile(t.updates_30, __("updates posted · 30d"))}
				${tile(t.messages_30, __("messages · 30d"))}
			</div>
			<div class="duty-me-charts">
				<div class="duty-me-chart"><h4>${__("Resolved per week")}</h4><div class="duty-ch-weekly"></div></div>
				<div class="duty-me-chart"><h4>${__("Open workload by type")}</h4><div class="duty-ch-type"></div></div>
				<div class="duty-me-chart"><h4>${__("Hours by customer · 30d")}</h4><div class="duty-ch-hours"></div></div>
			</div>
			${(m.pending_requests || []).length ? `
			<div class="duty-me-reqs">
				<h4>📨 ${__("Meeting requests awaiting approval")}</h4>
				${m.pending_requests.map((r) => `
					<div class="duty-req-row">
						<b>${esc(r.date)}${r.time ? " · " + esc(r.time) : ""}</b> ${esc(r.topic)}
						<span class="text-muted">· ${esc(r.customer || "")}${r.by ? " — " + esc(r.by) : ""}</span>
						<span class="duty-req-btns">
							<button class="btn btn-xs btn-primary duty-req-ok" data-id="${esc(r.name)}">✓ ${__("Confirm")}</button>
							<button class="btn btn-xs btn-default duty-req-no" data-id="${esc(r.name)}">✗ ${__("Decline")}</button>
						</span>
					</div>`).join("")}
			</div>` : ""}
			<div class="duty-me-cal">
				<div class="duty-me-calhead">
					<button class="btn btn-xs duty-cal-prev">◀</button>
					<h4 class="duty-cal-title"></h4>
					<button class="btn btn-xs duty-cal-next">▶</button>
				</div>
				<div class="duty-cal-grid"></div>
				<div class="duty-cal-legend">
					<span><i class="cdot cmeet"></i> ${__("meetings")}</span>
					<span><i class="cdot ctodo"></i> ${__("plan items")}</span>
					<span><i class="cdot cdue"></i> ${__("due")}</span>
					<span><i class="cdot cres"></i> ${__("resolved")}</span>
					<span><i class="cdot chrs"></i> ${__("hours on duty")}</span>
				</div>
			</div>
			<div class="duty-me-open">
				<h4>${__("Your open queue")}</h4>
				${(m.open_list || []).map((i) => {
					const today = frappe.datetime.get_today();
					const dueCls = !i.due ? "" : i.due < today ? " overdue" : i.due === today ? " duetoday" : "";
					return `
					<div class="duty-me-row" data-name="${esc(i.name)}">
						<span class="duty-sev duty-sev-${(i.severity || "medium").toLowerCase()}">${__(i.severity || "Medium")}</span>
						<span class="duty-me-title">${esc(i.title)}</span>
						<span class="duty-me-cust">${esc(i.customer || "—")}</span>
						<span class="duty-me-due${dueCls}">${i.due ? esc(i.due) : ""}</span>
					</div>`;
				}).join("") || `<div class="text-muted">${__("Nothing assigned — enjoy it while it lasts.")}</div>`}
			</div>
		`);
		const mk = (sel, type, data, height = 190) => {
			const $el = this.$me.find(sel);
			if (!data || !data.labels || !data.labels.length) {
				$el.html(`<div class="text-muted" style="padding:24px 0">${__("No data yet")}</div>`);
				return;
			}
			try {
				new frappe.Chart($el[0], {
					data: { labels: data.labels, datasets: [{ values: data.values }] },
					type, height, colors: ["#0F5C55", "#2563eb", "#d97706", "#7c3aed", "#dc2626", "#0e7490", "#65a30d", "#db2777"],
				});
			} catch (err) {
				console.error("chart", sel, err);
				$el.html(data.labels.map((l, i) => `<div style="display:flex;gap:8px;font-size:12px;padding:2px 0"><span style="flex:1">${frappe.utils.escape_html(String(l))}</span><b>${frappe.utils.escape_html(String(data.values[i]))}</b></div>`).join(""));
			}
		};
		mk(".duty-ch-weekly", "bar", m.weekly);
		mk(".duty-ch-type", "donut", m.by_type);
		mk(".duty-ch-hours", "donut", m.hours_by_customer);
		try {
			this.render_my_dashboard_cal(m);
		} catch (err) {
			console.error("calendar:", err);
			this.$me.find(".duty-cal-grid").html(`<div style="color:#b91c1c">calendar failed: ${frappe.utils.escape_html(err.message)}</div>`);
		}
		this.load_my_training();
		this.$me.find(".duty-me-row").on("click", (e) => this.issue_detail_dialog($(e.currentTarget).data("name")));
		this.$me.find(".duty-me-clockin").on("click", () =>
			frappe.call({
				method: "duty_board.api.clock_in",
				callback: () => this.refresh_me((this._me_data || {}).month),
			})
		);
		this.$me.find(".duty-me-clockout").on("click", () =>
			frappe.prompt(
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1 },
				(v) =>
					frappe.call({
						method: "duty_board.api.clock_out",
						args: { reason: v.reason },
						callback: () => this.refresh_me((this._me_data || {}).month),
					}),
				__("Clock Out")
			)
		);
		this.$me.find(".duty-req-ok").on("click", (e) =>
			frappe.call({
				method: "duty_board.client_room.confirm_meeting",
				args: { id: $(e.currentTarget).data("id") },
				callback: () => {
					frappe.show_alert({ message: __("Meeting confirmed"), indicator: "green" });
					this.refresh_me((this._me_data || {}).month);
				},
			})
		);
		this.$me.find(".duty-req-no").on("click", (e) => {
			const id = $(e.currentTarget).data("id");
			frappe.prompt(
				{ fieldname: "reason", fieldtype: "Small Text", label: __("Why not? (client sees this)") },
				(v) =>
					frappe.call({
						method: "duty_board.client_room.decline_meeting",
						args: { id, reason: v.reason || null },
						callback: () => {
							frappe.show_alert({ message: __("Declined"), indicator: "orange" });
							this.refresh_me((this._me_data || {}).month);
						},
					}),
				__("Decline meeting")
			);
		});
	}

	load_my_training() {
		if (!this.$me.find(".duty-me-training").length)
			this.$me.append(`<div class="duty-me-training" style="margin-top:18px"></div>`);
		frappe.call({
			method: "duty_board.client_room.my_training",
			callback: (r) => this.render_my_training(r.message || []),
		});
		if (!this.$me.find(".duty-me-certs").length)
			this.$me.append(`<div class="duty-me-certs" style="margin-top:14px"></div>`);
		frappe.call({
			method: "duty_board.client_room.my_certificates",
			callback: (r) => {
				const certs = r.message || [];
				const $c = this.$me.find(".duty-me-certs");
				if (!certs.length) return $c.empty();
				$c.html(`
					<div class="duty-lead-section">🎖 ${__("My certificates")}</div>
					${certs
						.map(
							(x) => `
					<div class="duty-cr-msrow">
						<span>🏅 <b>${frappe.utils.escape_html(x.product)} — ${frappe.utils.escape_html(x.track_title)}</b>
						${x.status !== "Valid" ? `<span class="duty-lead-chip" style="color:#b45309">${__(x.status)}</span>` : ""}</span>
						<span class="text-muted" style="font-size:var(--text-sm)">${x.serial} · ${x.issued_on}
							· <a href="/api/method/duty_board.client_room.my_certificate_file?serial=${encodeURIComponent(x.serial)}" target="_blank">⬇ ${__("PDF")}</a>
							· <a href="/verify?serial=${encodeURIComponent(x.serial)}" target="_blank">✓ ${__("verify")}</a></span>
					</div>`
						)
						.join("")}
				`);
			},
		});
	}

	render_my_training(rows) {
		const $t = this.$me.find(".duty-me-training");
		if (!$t.length) return;
		$t.html(`
			<div class="duty-lead-section">🎓 ${__("My training")} <a class="duty-me-trassign">＋ ${__("Assign to a colleague")}</a></div>
			${rows.length
				? rows
						.map(
							(r) => `
				<div class="duty-cr-msrow" style="cursor:pointer" data-record="${r.name}">
					<span>${r.status === "Completed" ? "🏅" : "📖"} <b>${frappe.utils.escape_html(r.module_title)}</b>${r.product ? ` <span class="text-muted">· ${frappe.utils.escape_html(r.product)}</span>` : ""}</span>
					<span class="text-muted" style="font-size:var(--text-sm)">
						${r.status === "Completed"
							? `✓ ${__("certified")} ${r.completed_on || ""}`
							: `📚 ${r.lessons_done}/${r.lessons_total} ${__("lessons")}${r.lessons_total && r.lessons_done === r.lessons_total ? " · ✓ " + __("all read") : ""}`}
					</span>
				</div>`
						)
						.join("")
				: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No training assigned to you yet.")}</div>`}
		`);
		$t.find("[data-record]").on("click", (e) => this.my_course_dialog($(e.currentTarget).data("record")));
		$t.find(".duty-me-trassign").on("click", () =>
			frappe.call({
				method: "duty_board.client_room.training_modules_for_staff",
				callback: (r) => {
					const mods = r.message || [];
					if (!mods.length)
						return frappe.msgprint(
							__("No consultant-facing courses yet. Create a Duty Training Module with audience Consultant or Both, and add its Duty Lessons in the desk.")
						);
					frappe.call({
						method: "duty_board.client_room.staff_tracks",
						callback: (tr) => {
							const tracks = tr.message || [];
							frappe.prompt(
								[
									{
										fieldname: "track",
										fieldtype: "Select",
										label: __("Whole track (assigns every course in it)"),
										options: [{ value: "", label: __("— single course instead —") }].concat(
											tracks.map((t) => ({
												value: t.name,
												label: `🎓 ${t.title} (${t.module_count} ${__("courses")})${t.product ? " · " + t.product : ""}${t.audience === "Client" ? " · " + __("client track — product knowledge") : ""}`,
											}))
										),
									},
									{
										fieldname: "module",
										fieldtype: "Select",
										label: __("Single course"),
										options: [{ value: "", label: "" }].concat(
											mods.map((m) => ({ value: m.name, label: `${m.title}${m.product ? " · " + m.product : ""}` }))
										),
									},
									{
										fieldname: "user",
										fieldtype: "Autocomplete",
										label: __("Consultant"),
										options: this.staff_options(),
										reqd: 1,
									},
								],
								(v) => {
									if (!v.track && !v.module)
										return frappe.msgprint(__("Pick a whole track or a single course."));
									if (v.track) {
										frappe.call({
											method: "duty_board.client_room.training_assign_track",
											args: { track: v.track, user: v.user },
											callback: (rr) => {
												const m = rr.message || {};
												frappe.show_alert({
													message: __("🎓 Track assigned: {0} new, {1} already had.", [m.created || 0, m.existing || 0]),
													indicator: "green",
												});
												if (v.user === frappe.session.user && m.records) this.render_my_training(m.records);
											},
										});
									} else {
										frappe.call({
											method: "duty_board.client_room.training_assign_staff",
											args: { module: v.module, user: v.user },
											callback: (rr) => {
												frappe.show_alert({ message: __("🎓 Assigned."), indicator: "green" });
												if (v.user === frappe.session.user && rr.message) this.render_my_training(rr.message);
											},
										});
									}
								},
								__("Assign consultant training"),
								__("Assign")
							);
						},
					});
				},
			})
		);
	}

	my_course_dialog(record) {
		frappe.call({
			method: "duty_board.client_room.my_course",
			args: { record: record },
			callback: (r) => {
				const c = r.message;
				if (!c) return;
				const d = new frappe.ui.Dialog({ title: `📖 ${c.title}`, size: "large" });
				const render = (cc) => {
					const allRead = cc.lessons.length && cc.lessons.every((l) => l.done);
					const qz = cc.quiz || {};
					$(d.body).html(`
						${cc.description ? `<div class="text-muted" style="margin-bottom:10px">${frappe.utils.escape_html(cc.description)}</div>` : ""}
						${cc.status === "Completed" || qz.passed
							? `<div style="background:#EDF7F5;border:1px solid #B7DFD6;border-radius:10px;padding:9px 13px;margin-bottom:10px;font-weight:700;color:#0C4A43">🏅 ${__("Certified")} · ${__("best score")} ${qz.best}%${qz.attempts > 1 ? ` · ${qz.attempts} ${__("attempts")}` : ""}</div>`
							: qz.bank >= 10
								? allRead
									? `<div style="display:flex;gap:10px;align-items:center;margin-bottom:10px"><button type="button" class="btn btn-sm btn-primary duty-me-quiz">📝 ${__("Take the test")}</button><span class="text-muted" style="font-size:var(--text-sm)">${qz.attempts ? `${__("best so far")} ${qz.best}% · ` : ""}10 ${__("questions, pass at 70%")}</span></div>`
									: `<div class="text-muted" style="font-size:var(--text-sm);margin-bottom:10px">📝 ${__("The test unlocks when every lesson is read.")}</div>`
								: ""}
						${cc.lessons.length
							? cc.lessons
									.map(
										(l, i) => `
							<div class="duty-cr-msrow" style="cursor:pointer" data-lesson="${l.name}">
								<span>${l.done ? "✅" : "⚪"} <b>${i + 1}. ${frappe.utils.escape_html(l.title)}</b></span>
								<span class="text-muted" style="font-size:var(--text-sm)">~${l.est_minutes} ${__("min")}</span>
							</div>`
									)
									.join("")
							: `<div class="text-muted">${__("Lessons are being prepared for this course.")}</div>`}
					`);
					$(d.body).find("[data-lesson]").on("click", (e) => {
						d.hide();
						this.my_lesson_dialog($(e.currentTarget).data("lesson"), record, cc);
					});
					$(d.body).find(".duty-me-quiz").on("click", () => {
						d.hide();
						this.my_quiz_dialog(record);
					});
				};
				render(c);
				d.show();
			},
		});
	}

	my_lesson_dialog(lesson, record, course) {
		frappe.call({
			method: "duty_board.client_room.my_lesson",
			args: { lesson: lesson },
			callback: (r) => {
				const l = r.message;
				if (!l) return;
				const lessons = (course && course.lessons) || [];
				const idx = lessons.findIndex((x) => x.name === lesson);
				const next = idx >= 0 ? lessons[idx + 1] : null;
				const d = new frappe.ui.Dialog({ title: (course && course.title) || __("Lesson"), size: "extra-large" });
				let secs = l.seconds || 0;
				let beat = null;
				$(d.body).html(`
					<style>
						.duty-lw { max-width: 74ch; margin: 0 auto; }
						.duty-lw-head { background: linear-gradient(120deg,#0A473F,#0F5C55 60%,#146B62); color: #fff;
							border-radius: 12px; padding: 16px 22px; margin-bottom: 20px; }
						.duty-lw-head .k { font-size: 11px; letter-spacing: 2px; text-transform: uppercase; opacity: .75; }
						.duty-lw-head h2 { margin: 4px 0 0; font-size: 22px; color: #fff; }
						.duty-lw-head .m { font-size: 12px; opacity: .85; margin-top: 6px; }
						.duty-lw-body { font-family: Georgia, "Times New Roman", serif; font-size: 17px; line-height: 1.85; color: #1F2A28; }
						.duty-lw-body p { margin: 0 0 14px; }
						.duty-lw-body b { color: #0C4A43; }
						.duty-lw-body ol { counter-reset: n; list-style: none; padding-left: 6px; }
						.duty-lw-body ol li { counter-increment: n; position: relative; padding-left: 40px; margin: 10px 0; }
						.duty-lw-body ol li:before { content: counter(n); position: absolute; left: 0; top: 2px;
							width: 26px; height: 26px; border-radius: 50%; background: #0F5C55; color: #fff;
							font-family: Inter, sans-serif; font-size: 13px; font-weight: 700;
							display: flex; align-items: center; justify-content: center; }
						.duty-lw-body ul { padding-left: 20px; }
						.duty-lw-body ul li { margin: 8px 0; }
						.duty-lw-body ul li::marker { color: #0F5C55; }
						.duty-lw-body blockquote { margin: 18px 0; padding: 13px 16px 13px 46px; border-radius: 12px;
							font-family: Inter, sans-serif; font-size: 14px; line-height: 1.6; position: relative; }
						.duty-lw-body blockquote:before { position: absolute; left: 14px; top: 12px; font-size: 18px; }
						.duty-lw-body blockquote.bq-note { background: #EEF7F4; border: 1px solid #CBE7DE; }
						.duty-lw-body blockquote.bq-note:before { content: "📌"; }
						.duty-lw-body blockquote.bq-tip { background: #FFF7E6; border: 1px solid #F3E0B5; }
						.duty-lw-body blockquote.bq-tip:before { content: "💡"; }
						.duty-lw-body blockquote.bq-warn { background: #FDECEA; border: 1px solid #F4C7C0; }
						.duty-lw-body blockquote.bq-warn:before { content: "⚠️"; }
						.duty-lw-foot { display: flex; gap: 12px; align-items: center; margin-top: 22px;
							border-top: 1px solid var(--border-color,#E7ECEA); padding-top: 14px; }
						.duty-lw-dots { display: flex; gap: 5px; margin-right: auto; }
						.duty-lw-dots i { width: 9px; height: 9px; border-radius: 50%; background: #D9E4E0; }
						.duty-lw-dots i.done { background: #0F5C55; }
						.duty-lw-dots i.cur { outline: 2px solid #0F5C55; outline-offset: 2px; }
					</style>
					<div class="duty-lw">
						<div class="duty-lw-head">
							<div class="k">${frappe.utils.escape_html((course && course.product) || "")} · ${__("Lesson")} ${idx + 1} ${__("of")} ${lessons.length}</div>
							<h2>${frappe.utils.escape_html(l.title)}</h2>
							<div class="m">⏱ ~${l.est_minutes} ${__("min read")}</div>
						</div>
						<div class="duty-lw-body"></div>
						<div class="duty-lw-foot">
							<span class="duty-lw-dots">${lessons.map((x, k) => `<i class="${x.done || x.name === lesson && l.done ? "done" : ""} ${k === idx ? "cur" : ""}"></i>`).join("")}</span>
							${l.done
								? `<span style="color:#15803d;font-weight:700;font-family:Inter,sans-serif">✓ ${__("Read")}</span>`
								: `<button type="button" class="btn btn-sm btn-primary duty-me-lread">✓ ${__("Mark as read")}${next ? " · " + __("next lesson") + " →" : ""}</button>`}
							${l.done && next ? `<button type="button" class="btn btn-sm btn-primary" data-next>${__("Next lesson")} →</button>` : ""}
							<button type="button" class="btn btn-sm btn-default" data-back>← ${__("Lessons")}</button>
						</div>
					</div>
				`);
				const $b = $(d.body).find(".duty-lw-body");
				$b.html(l.html);
				$b.find("blockquote").each(function () {
					const t = $(this).text();
					$(this).addClass(t.indexOf("WATCH-OUT") === 0 ? "bq-warn" : t.indexOf("IMPLEMENTATION TIP") === 0 ? "bq-tip" : "bq-note");
				});
				if (!l.done) {
					beat = setInterval(() => {
						if (document.visibilityState !== "visible" || !$(d.body).is(":visible")) return;
						secs += 20;
						frappe.call({ method: "duty_board.client_room.my_lesson_beat", args: { lesson: lesson, secs: 20 } });
					}, 20000);
				}
				d.onhide = () => {
					if (beat) clearInterval(beat);
				};
				const go_next = () => {
					d.hide();
					if (next) this.my_lesson_dialog(next.name, record, course);
					else {
						this.load_my_training();
						this.my_course_dialog(record);
					}
				};
				$(d.body).find(".duty-me-lread").on("click", () =>
					frappe.call({
						method: "duty_board.client_room.my_lesson_done",
						args: { lesson: lesson },
						callback: (rr) => {
							if (rr.message) {
								course = rr.message;
								go_next();
							}
						},
					})
				);
				$(d.body).find("[data-next]").on("click", go_next);
				$(d.body).find("[data-back]").on("click", () => {
					d.hide();
					this.my_course_dialog(record);
				});
				d.show();
			},
		});
	}

	books_dialog() {
		// legacy entry point — Books is a face now
		this.show_face("books");
	}

	refresh_books() {
		if (!this.books_period) this.books_period = frappe.datetime.now_date().slice(0, 7);
		if (!this.books_tab) this.books_tab = (this.books_acc && this.books_acc.tab) || "matrix";
		this.render_books_shell();
	}

	_books_shift_period(delta) {
		const [y, mo] = this.books_period.split("-").map(Number);
		const d = new Date(y, mo - 1 + delta, 1);
		this.books_period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
		this.render_books_shell();
	}

	render_books_shell() {
		const mgr = this.books_acc && this.books_acc.manager;
		const tabs = [
			["matrix", "📊 " + __("Matrix")],
			["round", "📅 " + __("My round")],
			["register", "🗓 " + __("Register")],
			["followups", "📨 " + __("Follow-ups")],
			["onboarding", "🚀 " + __("Onboarding")],
		];
		if (mgr) tabs.push(["profit", "₦ " + __("Profitability")], ["billing", "💰 " + __("Billing")], ["kpi", "📈 " + __("KPIs")]);
		this.$books.html(`
			<style>
				.duty-books-head { display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
					background: linear-gradient(120deg,#0A473F,#0F5C55 60%,#146B62); color: #fff;
					border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; }
				.duty-books-head b.per { font-size: 16px; }
				.duty-books-pulse { display: flex; gap: 14px; margin-left: auto; flex-wrap: wrap; font-size: 12px; }
				.duty-books-pulse span { opacity: .92; white-space: nowrap; }
				.duty-books-tabs { display: flex; gap: 6px; overflow-x: auto; margin-bottom: 12px; padding-bottom: 2px; }
				.duty-books-tabs a { padding: 7px 14px; border-radius: 999px; font-size: 13px; font-weight: 700;
					background: var(--bg-light-gray,#F4F7F6); color: #334; cursor: pointer; white-space: nowrap; }
				.duty-books-tabs a.on { background: #0F5C55; color: #fff; }
				.duty-books-panel { padding-bottom: 90px; }
				.duty-books-panel table { background: #fff; }
			</style>
			<div class="duty-books-head">
				<button class="btn btn-xs btn-default" data-bprev>‹</button>
				<b class="per">${this.books_period}</b>
				<button class="btn btn-xs btn-default" data-bnext>›</button>
				<span class="duty-books-pulse" data-pulse></span>
			</div>
			<div class="duty-books-tabs">
				${tabs.map(([k, l]) => `<a data-btab="${k}" class="${this.books_tab === k ? "on" : ""}">${l}</a>`).join("")}
			</div>
			<div class="duty-books-panel"><div class="text-muted">${__("Loading…")}</div></div>
		`);
		this.$books.find("[data-bprev]").on("click", () => this._books_shift_period(-1));
		this.$books.find("[data-bnext]").on("click", () => this._books_shift_period(1));
		this.$books.find("[data-btab]").on("click", (e) => {
			this.books_tab = $(e.currentTarget).data("btab");
			this.render_books_shell();
		});
		frappe.call({
			method: "duty_board.accounting.books_pulse",
			args: { period: this.books_period },
			callback: (r) => {
				const p = r.message;
				if (!p) return;
				this.$books.find("[data-pulse]").html(`
					<span>🤝 ${p.clients} ${__("clients")}</span>
					<span>✅ ${p.done}/${p.total} ${__("done")}</span>
					${p.late ? `<span style="color:#FCA5A5">⏰ ${p.late} ${__("late")}</span>` : ""}
					${p.neglect ? `<span style="color:#FCA5A5">⚠ ${p.neglect} ${__("neglected")}</span>` : ""}
					${p.open_q || p.open_r ? `<span>📨 ${p.open_q}❓ ${p.open_r}📎</span>` : ""}
					${p.fee_total ? `<span>₦${Number(p.fee_total).toLocaleString()}/mo</span>` : ""}
					${p.unpaid_count ? `<span style="color:#FCD34D">💰 ${p.unpaid_count} ${__("unpaid")} · ₦${Number(p.unpaid_total).toLocaleString()}</span>` : ""}
				`);
			},
		});
		this.render_books_panel();
	}

	render_books_panel() {
		const $p = this.$books.find(".duty-books-panel");
		const fn = {
			matrix: "_bpanel_matrix",
			round: "_bpanel_round",
			register: "_bpanel_register",
			followups: "_bpanel_followups",
			onboarding: "_bpanel_onboarding",
			profit: "_bpanel_profit",
			billing: "_bpanel_billing",
			kpi: "_bpanel_kpi",
		}[this.books_tab];
		if (fn) this[fn]($p);
	}

	_bpanel_matrix($p) {
		frappe.call({
			method: "duty_board.accounting.books_matrix",
			args: { period: this.books_period },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const STAT = { Pending: ["·", "#94a3b8"], "In Progress": ["◐", "#b45309"], "In Review": ["👁", "#7c3aed"], Delivered: ["✓", "#0F5C55"], Acknowledged: ["✓✓", "#15803d"] };
				$p.html(`
					<div style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:8px">
						<button class="btn btn-xs btn-default" data-sync>⟳ ${__("Sync clients")}</button>
						<button class="btn btn-xs btn-primary" data-open>📂 ${__("Open period")}</button>
					</div>
					${m.rooms.length
						? `<div style="overflow-x:auto"><table class="table table-bordered" style="font-size:var(--text-sm);margin:0">
							<thead><tr><th style="min-width:170px">${__("Client")}</th><th>${__("Bookkeeper")}</th>${m.types.map((t) => `<th style="min-width:110px">${frappe.utils.escape_html(t.title)}${t.optional ? " *" : ""}</th>`).join("")}</tr></thead>
							<tbody>${m.rooms
								.map(
									(row) => `<tr>
								<td><b>${frappe.utils.escape_html(row.customer)}</b>
									${row.scope ? `<br><span style="font-size:10px;font-weight:700;color:#0e7490">◳ ${frappe.utils.escape_html(row.scope)}</span>` : ""}
									${(!row.scope || row.scope.includes("Bookkeeping")) && row.posted_through ? `<br><span style="font-size:10px;font-weight:700;color:${row.lag <= 1 ? "#15803d" : row.lag <= 3 ? "#b45309" : "#b91c1c"}">📮 ${__("posted thru")} ${row.posted_through.slice(5)} · ${__("lag")} ${row.lag}wd</span>` : (!row.scope || row.scope.includes("Bookkeeping") ? `<br><span style="font-size:10px;color:#94a3b8">📮 ${__("no attestation")}</span>` : "")}
									${row.fee ? `<br><span class="text-muted" style="font-size:11px">₦${Number(row.fee).toLocaleString()}/mo</span>` : ""}</td>
								<td><a class="duty-bk-room" data-room="${row.room}" data-bk="${row.bookkeeper || ""}" data-opt="${frappe.utils.escape_html(row.optionals)}" data-scope="${frappe.utils.escape_html(row.scope || "")}" data-fye="${row.fye_month || ""}" style="cursor:pointer">${row.bookkeeper_name ? frappe.utils.escape_html(row.bookkeeper_name.split(" ")[0]) : "— " + __("set")}</a>
									<a class="duty-bk-pb" data-room="${row.room}" title="${__("Client playbook")}" style="cursor:pointer;margin-left:6px">📖</a></td>
								${m.types
									.map((t) => {
										const c = row.cells[t.name];
										if (!c) {
											const lines = (row.scope || "").split(",").map((s) => s.trim()).filter(Boolean);
											if (lines.length && t.service_line && !lines.includes(t.service_line)) {
												return `<td class="text-muted" style="text-align:center;opacity:.35" title="${__("Outside this client's service scope")}">·</td>`;
											}
											const enabled = !t.optional || (row.optionals || "").split(",").map((s) => s.trim()).some((s) => s === t.title || s === t.name);
											if (enabled && t.frequency === "Quarterly") {
												const mo = Number(m.period.slice(5, 7));
												const qm = mo <= 3 ? 3 : mo <= 6 ? 6 : mo <= 9 ? 9 : 12;
												const qname = ["", "", "", "Mar", "", "", "Jun", "", "", "Sep", "", "", "Dec"][qm];
												return `<td class="text-muted" style="text-align:center;font-size:10px" title="${__("Quarterly — next occurrence opens with the {0} period", [qname])}">↻ ${qname}</td>`;
											}
											return `<td class="text-muted" style="text-align:center">—</td>`;
										}
										const [ic, col] = STAT[c.status] || ["·", "#94a3b8"];
										return `<td style="text-align:center;cursor:pointer;${c.late ? "background:#FDECEA;" : ""}" class="duty-bk-cell" data-name="${c.name}" title="${frappe.utils.escape_html((c.notes || "") + (c.assigned_to ? " · " + c.assigned_to : ""))}">
											<span style="color:${col};font-weight:800">${ic}</span>
											<div style="font-size:10px;color:${c.late ? "#b91c1c" : "#94a3b8"}">${c.due_date ? c.due_date.slice(5) : ""}${c.late ? " ⚠" : ""}</div>
											${c.assigned_to ? `<div style="font-size:10px;color:#64748b">${frappe.utils.escape_html((c.assigned_to || "").split("@")[0])}</div>` : ""}
										</td>`;
									})
									.join("")}
							</tr>`
								)
								.join("")}</tbody>
						</table></div>
						<div class="text-muted" style="font-size:11px;margin-top:8px">· ${__("Pending")} &nbsp; ◐ ${__("In progress")} &nbsp; 👁 ${__("In review")} &nbsp; ✓ ${__("Delivered")} &nbsp; ✓✓ ${__("Acknowledged by client")} &nbsp; * ${__("optional per room")} &nbsp; ${__("red = past due")}</div>`
						: `<div class="text-muted">${__("No accounting clients found — set accounting_services to 'On Board' on the Customer, then Sync.")}</div>`}
				`);
				$p.find("[data-sync]").on("click", () =>
					frappe.call({ method: "duty_board.accounting.sync_accounting_clients", callback: (rr) => { frappe.show_alert({ message: __("Synced: {0} clients, {1} rooms created", [rr.message.customers, rr.message.rooms_created]), indicator: "green" }); this.render_books_shell(); } })
				);
				$p.find("[data-open]").on("click", () =>
					frappe.call({ method: "duty_board.accounting.books_open_period", args: { period: this.books_period }, callback: (rr) => { frappe.show_alert({ message: __("{0} deliverables, {1} document requests opened", [rr.message.spawned, rr.message.requests || 0]), indicator: "green" }); this.render_books_shell(); } })
				);
				$p.find(".duty-bk-cell").on("click", (e) => this.books_cell_dialog($(e.currentTarget).data("name")));
				$p.find(".duty-bk-pb").on("click", (e) => this.books_playbook_dialog($(e.currentTarget).data("room")));
				$p.find(".duty-bk-room").on("click", (e) => {
					const room = $(e.currentTarget).data("room");
					const current = ($(e.currentTarget).data("opt") || "").split(",").map((s) => s.trim()).filter(Boolean);
					const opts = m.types.filter((t) => t.optional);
					const LINES = ["Bookkeeping", "Payroll & HR", "Tax"];
					const curScope = ($(e.currentTarget).data("scope") || "").split(",").map((s) => s.trim()).filter(Boolean);
					const scopeSel = curScope.length ? curScope : LINES;
					frappe.prompt(
						[
							{ fieldname: "bookkeeper", fieldtype: "Autocomplete", label: __("Bookkeeper (default owner)"), options: this.staff_options(), default: $(e.currentTarget).data("bk") || "" },
							{
								fieldname: "scope",
								fieldtype: "MultiCheck",
								label: __("Service scope — all three checked = Full Books"),
								columns: 3,
								options: LINES.map((l) => ({ label: l, value: l, checked: scopeSel.includes(l) })),
							},
							{
								fieldname: "fye_month",
								fieldtype: "Select",
								label: __("Financial year end month (annual tax deliverables)"),
								options: ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
								default: String($(e.currentTarget).data("fye") || ""),
								description: __("CIT / annual returns spawn 6 months after this month; blank = skipped"),
							},
							{
								fieldname: "optionals",
								fieldtype: "MultiCheck",
								label: __("Service tier — optional deliverables this client pays for"),
								columns: 1,
								options: opts.map((t) => ({ label: t.title + (t.service_line && t.service_line !== "Bookkeeping" ? " · " + t.service_line : ""), value: t.title, checked: current.includes(t.title) || current.includes(t.name) })),
							},
						],
						(v) =>
							frappe.call({
								method: "duty_board.accounting.books_set_room",
								args: { name: room, bookkeeper: v.bookkeeper || null, optionals: (v.optionals || []).join(", "), scope: (v.scope || []).join(", "), fye_month: v.fye_month || 0 },
								callback: () => this.render_books_shell(),
							}),
						__("Client setup"),
						__("Save")
					);
				});
			},
		});
	}

	_bpanel_round($p) {
		frappe.call({
			method: "duty_board.accounting.books_daily_round",
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				$p.html(`
					<div class="text-muted" style="font-size:12px;margin-bottom:10px">📅 ${m.date} — ${__("two taps per client: where are the books posted through, and anything worth noting. Sessions you've clocked already show as ●.")}</div>
					${m.rows
						.map(
							(x, i) => `
					<div style="border:1px solid var(--border-color,#E7ECEA);border-radius:10px;padding:10px 12px;margin-bottom:8px;background:#fff" data-row="${i}">
						<div style="display:flex;gap:8px;align-items:center;margin-bottom:7px">
							<b>${frappe.utils.escape_html(x.customer)}</b>
							<span title="${__("worked today (session tagged)")}">${x.worked_today ? "●" : "○"}</span>
							${x.logged_today ? `<span style="color:#15803d;font-size:11px;font-weight:700">✓ ${__("attested")}</span>` : ""}
							<span style="margin-left:auto;font-size:11px;color:${x.lag === null ? "#94a3b8" : x.lag <= 1 ? "#15803d" : x.lag <= 3 ? "#b45309" : "#b91c1c"}">${x.posted_through ? __("posted thru {0} · lag {1}wd", [x.posted_through, x.lag]) : __("no attestation yet")}</span>
						</div>
						<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
							<input type="date" class="form-control input-sm bk-pt" style="width:150px" value="${x.posted_through || ""}" max="${m.date}">
							<input type="number" class="form-control input-sm bk-tx" style="width:90px" placeholder="${__("tx posted")}" value="${x.tx_posted ?? ""}">
							<input type="number" class="form-control input-sm bk-q" style="width:90px" placeholder="${__("queries")}" value="${x.queries_raised ?? ""}">
							<input type="text" class="form-control input-sm bk-note" style="flex:1;min-width:140px" placeholder="${__("note (optional)")}" value="${frappe.utils.escape_html(x.note || "")}">
							<button class="btn btn-xs btn-primary bk-save" data-room="${x.room}">💾</button>
						</div>
					</div>`
						)
						.join("") || `<div class="text-muted">${__("No accounting clients assigned to you.")}</div>`}
				`);
				$p.find(".bk-save").on("click", (e) => {
					const $row = $(e.currentTarget).closest("[data-row]");
					frappe.call({
						method: "duty_board.accounting.books_log_day",
						args: {
							room: $(e.currentTarget).data("room"),
							posted_through: $row.find(".bk-pt").val() || null,
							tx_posted: $row.find(".bk-tx").val() || 0,
							queries_raised: $row.find(".bk-q").val() || 0,
							note: $row.find(".bk-note").val() || null,
						},
						callback: () => {
							frappe.show_alert({ message: __("Attested"), indicator: "green" });
							this.render_books_shell();
						},
					});
				});
			},
		});
	}

	_bpanel_register($p) {
		frappe.call({
			method: "duty_board.accounting.books_register",
			args: { period: this.books_period },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const CELL = { both: ["●", "#0F5C55"], worked: ["◐", "#b45309"], logged: ["◔", "#7c3aed"], none: ["·", "#cbd5e1"], future: ["", "#fff"] };
				$p.html(`
					<div style="overflow-x:auto"><table class="table table-bordered" style="font-size:11px;margin:0">
						<thead><tr><th style="min-width:150px">${__("Client")}</th>${m.days.map((ds) => `<th style="text-align:center;padding:4px 5px">${ds.slice(8)}</th>`).join("")}<th>${__("Lag")}</th></tr></thead>
						<tbody>${m.rooms
							.map(
								(row) => `<tr ${row.neglected ? 'style="background:#FDECEA"' : ""}>
							<td><b>${frappe.utils.escape_html(row.customer)}</b>${row.neglected ? ` <span style="color:#b91c1c;font-weight:800">⚠ ${row.streak}${__("wd")}</span>` : ""}</td>
							${m.days.map((ds) => { const [ic, col] = CELL[row.cells[ds]] || CELL.none; return `<td style="text-align:center;color:${col};font-weight:800;padding:4px 5px">${ic}</td>`; }).join("")}
							<td style="font-size:10px;font-weight:700;color:${row.lag === null ? "#94a3b8" : row.lag <= 1 ? "#15803d" : row.lag <= 3 ? "#b45309" : "#b91c1c"}">${row.posted_through ? row.lag + "wd" : "—"}</td>
						</tr>`
							)
							.join("")}</tbody>
					</table></div>
					<div class="text-muted" style="font-size:11px;margin-top:8px">● ${__("worked + attested")} &nbsp; ◐ ${__("worked, no attestation")} &nbsp; ◔ ${__("attested, no session")} &nbsp; · ${__("untouched")} &nbsp; ${__("red row = {0}+ working days untouched", [m.neglect_days])}</div>
				`);
			},
		});
	}

	_bpanel_followups($p, room_filter) {
		frappe.call({
			method: "duty_board.accounting.books_followups",
			args: { room: room_filter || null },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const roomName = (rm) => { const x = m.rooms.find((y) => y.room === rm); return x ? x.customer : rm; };
				$p.html(`
					<div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap">
						<select class="form-control input-sm" data-roomsel style="width:220px">
							<option value="">${__("All clients")}</option>
							${m.rooms.map((x) => `<option value="${x.room}" ${room_filter === x.room ? "selected" : ""}>${frappe.utils.escape_html(x.customer)}</option>`).join("")}
						</select>
						<span style="margin-left:auto;display:flex;gap:8px">
							<button class="btn btn-xs btn-primary" data-addq>❓ ${__("New question")}</button>
							<button class="btn btn-xs btn-default" data-addr>📎 ${__("New request")}</button>
						</span>
					</div>
					<div style="font-size:12px;font-weight:800;margin-bottom:6px">❓ ${__("Questions")} (${m.queries.length})</div>
					${m.queries
						.map(
							(q) => `
					<div style="border:1px solid var(--border-color,#E7ECEA);border-radius:10px;padding:9px 12px;margin-bottom:7px;background:${q.status === "Answered" ? "#F4FBF8" : "#fff"}">
						<div style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">
							<b style="font-size:13px">${frappe.utils.escape_html(roomName(q.room))}</b>
							<span class="text-muted" style="font-size:11px">${[q.ref_date, q.amount ? "₦" + Number(q.amount).toLocaleString() : null, q.reference].filter(Boolean).map(frappe.utils.escape_html).join(" · ")}</span>
							${q.recipients ? `<span style="font-size:11px;color:#0e7490;font-weight:700">👤 ${frappe.utils.escape_html(q.recipients.split(",").map((s) => s.trim().split("@")[0]).join(", "))}</span>` : ""}
							<span style="margin-left:auto;font-size:11px;font-weight:700;color:${q.status === "Answered" ? "#15803d" : "#b45309"}">${q.status === "Answered" ? "💬 " + __("answered") : __("open") + " · " + q.age_wd + "wd"}</span>
						</div>
						<div style="font-size:13px;margin-top:3px">${frappe.utils.escape_html(q.question)}</div>
						${q.answer ? `<div style="font-size:13px;margin-top:5px;padding:7px 10px;background:#fff;border:1px solid #CBE7DE;border-radius:8px">💬 <b>${frappe.utils.escape_html(q.answered_by || "")}</b>: ${frappe.utils.escape_html(q.answer)} <button class="btn btn-xs btn-primary" data-resolve="${q.name}" style="margin-left:8px">✓ ${__("Resolve")}</button></div>` : ""}
					</div>`
						)
						.join("") || `<div class="text-muted" style="margin-bottom:8px">${__("No open questions.")}</div>`}
					<div style="font-size:12px;font-weight:800;margin:10px 0 6px">📎 ${__("Document requests")} (${m.requests.length})</div>
					${m.requests
						.map(
							(x) => `
					<div style="border:1px solid var(--border-color,#E7ECEA);border-radius:10px;padding:8px 12px;margin-bottom:6px;display:flex;gap:8px;align-items:center;background:${x.overdue ? "#FDECEA" : "#fff"}">
						<b style="font-size:13px">${frappe.utils.escape_html(roomName(x.room))}</b>
						<span style="font-size:13px">${frappe.utils.escape_html(x.title)}</span>
						${x.recipients ? `<span style="font-size:11px;color:#0e7490;font-weight:700">👤 ${frappe.utils.escape_html(x.recipients.split(",").map((s) => s.trim().split("@")[0]).join(", "))}</span>` : ""}
						<span class="text-muted" style="font-size:11px;margin-left:auto">${x.due_date ? __("due") + " " + x.due_date + (x.overdue ? " ⚠" : "") : ""}</span>
						<button class="btn btn-xs btn-default" data-waive="${x.name}">${__("Waive")}</button>
					</div>`
						)
						.join("") || `<div class="text-muted">${__("Nothing outstanding.")}</div>`}
					${m.received && m.received.length
						? `<div style="font-size:12px;font-weight:800;margin:10px 0 6px">📥 ${__("Recently received")}</div>` +
							m.received
								.map(
									(x) => `
					<div style="border:1px solid #CBE7DE;background:#F4FBF8;border-radius:10px;padding:8px 12px;margin-bottom:6px;display:flex;gap:8px;align-items:center">
						<b style="font-size:13px">${frappe.utils.escape_html(roomName(x.room))}</b>
						<span style="font-size:13px">${frappe.utils.escape_html(x.title)}</span>
						<span class="text-muted" style="font-size:11px;margin-left:auto">${frappe.utils.escape_html(x.fulfilled_by || "")} · ${x.fulfilled_on || ""}</span>
						${x.attachment_url ? `<a class="btn btn-xs btn-default" href="/api/method/duty_board.accounting.books_request_file?name=${encodeURIComponent(x.name)}" target="_blank">📎 ${__("Open")}</a>` : ""}
					</div>`
								)
								.join("")
						: ""}
				`);
				const reload = (rm) => this._bpanel_followups($p, rm !== undefined ? rm : room_filter);
				$p.find("[data-roomsel]").on("change", (e) => reload($(e.currentTarget).val() || null));
				$p.find("[data-resolve]").on("click", (e) =>
					frappe.call({ method: "duty_board.accounting.books_resolve_query", args: { name: $(e.currentTarget).data("resolve") }, callback: () => reload() })
				);
				$p.find("[data-waive]").on("click", (e) =>
					frappe.call({ method: "duty_board.accounting.books_waive_request", args: { name: $(e.currentTarget).data("waive") }, callback: () => reload() })
				);
				const memOpts = (rm, sel) => ((m.members || {})[rm] || []).map((u) => ({ label: u.full_name || u.user, value: u.user, checked: (sel || []).includes(u.user) }));
				const bindMembers = (dlg) => {
					const refresh = () => {
						const mc = dlg.fields_dict.recipients;
						if (!mc) return;
						mc.df.options = memOpts(dlg.get_value("room"));
						mc.refresh();
					};
					dlg.fields_dict.room.df.onchange = refresh;
					refresh();
				};
				$p.find("[data-addq]").on("click", () => {
					const dlg = frappe.prompt(
						[
							{ fieldname: "room", fieldtype: "Select", label: __("Client"), options: m.rooms.map((x) => ({ label: x.customer, value: x.room })), reqd: 1, default: room_filter || (m.rooms[0] && m.rooms[0].room) },
							{ fieldname: "recipients", fieldtype: "MultiCheck", label: __("Send to (none checked = everyone in the room)"), columns: 2, options: [] },
							{ fieldname: "question", fieldtype: "Small Text", label: __("Question"), reqd: 1 },
							{ fieldname: "ref_date", fieldtype: "Date", label: __("Transaction date") },
							{ fieldname: "amount", fieldtype: "Currency", label: __("Amount") },
							{ fieldname: "reference", fieldtype: "Data", label: __("Reference (narration, counterparty…)") },
						],
						(v) =>
							frappe.call({
								method: "duty_board.accounting.books_add_query",
								args: { room: v.room, question: v.question, ref_date: v.ref_date || null, amount: v.amount || null, reference: v.reference || null, recipients: (v.recipients || []).join(", ") },
								callback: () => reload(),
							}),
						__("Ask the client"),
						__("Send")
					);
					bindMembers(dlg);
				});
				$p.find("[data-addr]").on("click", () => {
					const dlg = frappe.prompt(
						[
							{ fieldname: "room", fieldtype: "Select", label: __("Client"), options: m.rooms.map((x) => ({ label: x.customer, value: x.room })), reqd: 1, default: room_filter || (m.rooms[0] && m.rooms[0].room) },
							{ fieldname: "recipients", fieldtype: "MultiCheck", label: __("Send to (none checked = everyone in the room)"), columns: 2, options: [] },
							{ fieldname: "title", fieldtype: "Data", label: __("Document"), reqd: 1 },
							{ fieldname: "detail", fieldtype: "Small Text", label: __("Detail") },
							{ fieldname: "due_date", fieldtype: "Date", label: __("Due") },
						],
						(v) =>
							frappe.call({
								method: "duty_board.accounting.books_add_request",
								args: { room: v.room, title: v.title, detail: v.detail || null, due_date: v.due_date || null, recipients: (v.recipients || []).join(", ") },
								callback: () => reload(),
							}),
						__("Request a document"),
						__("Send")
					);
					bindMembers(dlg);
				});
			},
		});
	}

	books_playbook_dialog(room) {
		frappe.call({
			method: "duty_board.accounting.books_playbook_get",
			args: { room: room },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const d = new frappe.ui.Dialog({
					title: `📖 ${frappe.utils.escape_html(m.customer)} — ${__("playbook")}`,
					size: "large",
					fields: [
						{
							fieldname: "playbook",
							fieldtype: "Text",
							label: __("Everything a covering bookkeeper must know"),
							default: m.playbook,
						},
					],
					primary_action_label: __("Save"),
					primary_action: (v) =>
						frappe.call({
							method: "duty_board.accounting.books_playbook_set",
							args: { room: room, playbook: v.playbook || "" },
							callback: () => {
								frappe.show_alert({ message: __("Playbook saved"), indicator: "green" });
								d.hide();
							},
						}),
				});
				d.$body.find("textarea").css({ "min-height": "320px", "font-family": "ui-monospace, monospace", "font-size": "13px" });
				d.show();
			},
		});
	}

	books_cell_dialog(name) {
		frappe.call({
			method: "duty_board.accounting.books_cell",
			args: { name: name },
			callback: (r) => {
				const c = r.message;
				if (!c) return;
				const d = new frappe.ui.Dialog({
					title: `${frappe.utils.escape_html(c.customer)} — ${frappe.utils.escape_html(c.type_title)} · ${c.period}`,
					size: "large",
					fields: [
						{ fieldname: "status", fieldtype: "Select", label: __("Status"), options: "Pending\nIn Progress\nIn Review\nDelivered", default: c.status === "Acknowledged" ? "Delivered" : c.status },
						{ fieldname: "assigned_to", fieldtype: "Autocomplete", label: __("Assigned to"), options: this.staff_options(), default: c.assigned_to || "" },
						{ fieldname: "reviewer", fieldtype: "Autocomplete", label: __("Reviewer (split clients)"), options: this.staff_options(), default: c.reviewer || "" },
						{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes"), default: c.notes || "" },
					],
					primary_action_label: __("Save"),
					primary_action: (v) => {
						const save = () =>
							frappe.call({
								method: "duty_board.accounting.books_set",
								args: { name: name, status: v.status || null, assigned_to: v.assigned_to || null, reviewer: v.reviewer || null, notes: v.notes || null },
								callback: () => {
									d.hide();
									this.render_books_shell();
								},
							});
						if (v.status === "Delivered" && c.open_items > 0 && c.status !== "Delivered") {
							frappe.confirm(
								__("{0} checklist item(s) are still open — deliver anyway?", [c.open_items]),
								save
							);
						} else save();
					},
				});
				const done = c.items.filter((i) => i.status === "Done").length;
				const $chk = $(`
					<div style="margin-bottom:14px">
						${c.due_date ? `<div class="text-muted" style="font-size:12px;margin-bottom:8px">📅 ${__("due")} ${c.due_date}${c.status === "Acknowledged" ? ` · <b style="color:#15803d">✓✓ ${__("acknowledged by client")}</b>` : ""}</div>` : ""}
						${c.items.length
							? `<div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
									<b style="font-size:13px">${__("Close checklist")}</b>
									<span style="font-size:12px;font-weight:700;color:${done === c.items.length ? "#15803d" : "#0F5C55"}">${done}/${c.items.length}</span>
									<span style="flex:1;height:5px;background:#E7ECEA;border-radius:99px;overflow:hidden"><i style="display:block;height:100%;width:${c.items.length ? Math.round((done / c.items.length) * 100) : 0}%;background:#0F5C55"></i></span>
								</div>` +
								c.items
									.map(
										(i) => `
							<div style="display:flex;gap:9px;align-items:baseline;padding:4px 0;border-top:1px dashed #EEF2F0">
								<a class="duty-chk" data-name="${i.name}" data-done="${i.status === "Done" ? 0 : 1}" style="cursor:pointer;font-size:15px">${i.status === "Done" ? "☑" : "☐"}</a>
								<span style="font-size:13px;${i.status === "Done" ? "color:#94a3b8;text-decoration:line-through" : ""}">${frappe.utils.escape_html(i.item)}</span>
								<span class="text-muted" style="font-size:10px;margin-left:auto;white-space:nowrap">${i.status === "Done" ? frappe.utils.escape_html((i.done_by || "").split(" ")[0]) + " · " + (i.done_on || "") : ""}</span>
							</div>`
									)
									.join("")
							: `<div class="text-muted" style="font-size:12px">${__("No checklist for this deliverable type — add one on the type in the desk.")}</div>`}
					</div>`);
				$(d.body).prepend($chk);
				$chk.find(".duty-chk").on("click", (e) =>
					frappe.call({
						method: "duty_board.accounting.books_tick_check",
						args: { name: $(e.currentTarget).data("name"), done: $(e.currentTarget).data("done") },
						callback: () => {
							d.hide();
							this.books_cell_dialog(name);
						},
					})
				);
				d.show();
			},
		});
	}

	_bpanel_onboarding($p) {
		frappe.call({
			method: "duty_board.accounting.books_onboarding",
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const card = (v) => `
					<div style="border:1px solid var(--border-color,#E7ECEA);border-radius:12px;padding:12px 14px;margin-bottom:10px;background:#fff">
						<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px">
							<b style="font-size:14px">${frappe.utils.escape_html(v.customer)}</b>
							<span style="font-size:12px;font-weight:700;color:${v.done === v.total ? "#15803d" : "#0F5C55"}">${v.done}/${v.total}</span>
							<span style="flex:1;height:6px;background:#E7ECEA;border-radius:99px;overflow:hidden"><i style="display:block;height:100%;width:${v.total ? Math.round((v.done / v.total) * 100) : 0}%;background:#0F5C55"></i></span>
						</div>
						${v.steps
							.map(
								(s) => `
						<div style="display:flex;gap:9px;align-items:baseline;padding:4px 0;border-top:1px dashed #EEF2F0">
							<a class="duty-ob-tick" data-name="${s.name}" data-done="${s.status === "Done" ? 0 : 1}" style="cursor:pointer;font-size:15px">${s.status === "Done" ? "☑" : "☐"}</a>
							<span style="font-size:13px;${s.status === "Done" ? "color:#94a3b8;text-decoration:line-through" : ""}">${frappe.utils.escape_html(s.step)}</span>
							<span class="text-muted" style="font-size:10px;margin-left:auto;white-space:nowrap">${s.status === "Done" ? frappe.utils.escape_html((s.done_by || "").split(" ")[0]) + " · " + (s.done_on || "") : ""}</span>
						</div>`
							)
							.join("")}
					</div>`;
				$p.html(`
					${m.active.length ? m.active.map(card).join("") : `<div class="text-muted" style="margin-bottom:10px">${__("No clients mid-onboarding.")}</div>`}
					${m.not_started.length
						? `<div style="font-size:12px;font-weight:800;margin:6px 0">${__("Not started")}</div>` +
							m.not_started
								.map(
									(x) => `<div style="display:flex;gap:8px;align-items:center;padding:6px 0"><span style="font-size:13px">${frappe.utils.escape_html(x.customer)}</span><button class="btn btn-xs btn-default duty-ob-start" data-room="${x.room}" style="margin-left:auto">🚀 ${__("Start onboarding")}</button></div>`
								)
								.join("")
						: ""}
					${m.complete.length
						? `<details style="margin-top:10px"><summary class="text-muted" style="font-size:12px;cursor:pointer">✅ ${__("Completed")} (${m.complete.length})</summary>${m.complete.map(card).join("")}</details>`
						: ""}
				`);
				$p.find(".duty-ob-tick").on("click", (e) =>
					frappe.call({
						method: "duty_board.accounting.books_tick_onboarding",
						args: { name: $(e.currentTarget).data("name"), done: $(e.currentTarget).data("done") },
						callback: () => this._bpanel_onboarding($p),
					})
				);
				$p.find(".duty-ob-start").on("click", (e) =>
					frappe.call({
						method: "duty_board.accounting.books_start_onboarding",
						args: { room: $(e.currentTarget).data("room") },
						callback: () => this._bpanel_onboarding($p),
					})
				);
			},
		});
	}

	_bpanel_kpi($p) {
		frappe.call({
			method: "duty_board.accounting.books_kpi",
			args: { period: this.books_period },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const pct = (v) => (v === null ? "—" : `<span style="font-weight:700;color:${v >= 90 ? "#15803d" : v >= 70 ? "#b45309" : "#b91c1c"}">${v}%</span>`);
				const num = (v, unit) => (v === null ? "—" : `${v}${unit || ""}`);
				$p.html(`
					<div style="font-size:12px;font-weight:800;margin-bottom:6px">📈 ${__("Trend — last 6 periods")}</div>
					<div style="overflow-x:auto"><table class="table table-bordered" style="font-size:var(--text-sm);margin:0;background:#fff">
						<thead><tr><th></th>${m.trend.map((t) => `<th style="text-align:center">${t.period.slice(2)}</th>`).join("")}</tr></thead>
						<tbody>
							<tr><td>${__("Deliverables done")}</td>${m.trend.map((t) => `<td style="text-align:center">${t.done}/${t.total}</td>`).join("")}</tr>
							<tr><td>${__("On-time rate")}</td>${m.trend.map((t) => `<td style="text-align:center">${pct(t.on_time_pct)}</td>`).join("")}</tr>
							<tr><td>${__("FS close cycle (days after month end)")}</td>${m.trend.map((t) => `<td style="text-align:center">${num(t.fs_cycle, "d")}</td>`).join("")}</tr>
							<tr><td>${__("Avg posting lag (wd, attested)")}</td>${m.trend.map((t) => `<td style="text-align:center">${num(t.avg_lag, "")}</td>`).join("")}</tr>
						</tbody>
					</table></div>
					<div style="font-size:12px;font-weight:800;margin:14px 0 6px">🤝 ${__("Per client — 6-period window")}</div>
					<div style="overflow-x:auto"><table class="table table-bordered" style="font-size:var(--text-sm);margin:0;background:#fff">
						<thead><tr><th>${__("Client")}</th><th style="text-align:center">${__("Done")}</th><th style="text-align:center">${__("On-time")}</th><th style="text-align:center">${__("FS cycle")}</th><th style="text-align:center">${__("Posting lag")}</th><th style="text-align:center">${__("Client ack (days)")}</th></tr></thead>
						<tbody>${m.by_client
							.map(
								(c) => `<tr>
							<td><b>${frappe.utils.escape_html(c.customer)}</b></td>
							<td style="text-align:center">${c.done}/${c.total}</td>
							<td style="text-align:center">${pct(c.on_time_pct)}</td>
							<td style="text-align:center">${num(c.fs_cycle, "d")}</td>
							<td style="text-align:center">${num(c.avg_lag, "wd")}</td>
							<td style="text-align:center">${num(c.ack_days, "d")}</td>
						</tr>`
							)
							.join("")}</tbody>
					</table></div>
					<div style="font-size:12px;font-weight:800;margin:14px 0 6px">👥 ${__("Per bookkeeper — 6-period window")}</div>
					<table class="table table-bordered" style="font-size:var(--text-sm);margin:0;background:#fff">
						<thead><tr><th>${__("Bookkeeper")}</th><th style="text-align:center">${__("Delivered")}</th><th style="text-align:center">${__("On-time")}</th><th style="text-align:center">${__("Open this period")}</th></tr></thead>
						<tbody>${m.staff
							.map(
								(s) => `<tr>
							<td><b>${frappe.utils.escape_html(s.first)}</b> <span class="text-muted" style="font-size:11px">${frappe.utils.escape_html(s.user)}</span></td>
							<td style="text-align:center">${s.done}/${s.total}</td>
							<td style="text-align:center">${pct(s.on_time_pct)}</td>
							<td style="text-align:center">${s.open_now || ""}</td>
						</tr>`
							)
							.join("") || `<tr><td colspan="4" class="text-muted">${__("No assigned deliverables in the window.")}</td></tr>`}</tbody>
					</table>
					<div style="font-size:12px;font-weight:800;margin:14px 0 6px">🚩 ${__("Fee review — below ₦{0}/hr for 3 consecutive months", [Number(m.floor).toLocaleString()])}</div>
					${m.fee_review.length
						? m.fee_review
								.map(
									(f) => `
					<div style="border:1px solid #F4C7C0;background:#FDECEA;border-radius:10px;padding:9px 12px;margin-bottom:6px;display:flex;gap:10px;align-items:center;flex-wrap:wrap">
						<b>${frappe.utils.escape_html(f.customer)}</b>
						<span style="font-size:12px">₦${Number(f.fee).toLocaleString()}/mo</span>
						<span style="font-size:12px;margin-left:auto">${m.last3.map((p, i) => `${p.slice(5)}: <b style="color:#b91c1c">₦${Number(f.rates[i]).toLocaleString()}/hr</b>`).join(" · ")}</span>
					</div>`
								)
								.join("")
						: `<div class="text-muted" style="font-size:12px">${__("No clients flagged — every engagement is above the floor (or lacks 3 months of tagged hours).")}</div>`}
					<div style="font-size:12px;font-weight:800;margin:14px 0 6px">👜 ${__("Capacity — who takes the next client?")}</div>
					<table class="table table-bordered" style="font-size:var(--text-sm);margin:0;background:#fff">
						<thead><tr><th>${__("Bookkeeper")}</th><th style="text-align:center">${__("Clients owned")}</th><th style="text-align:center">${__("Open this period")}</th><th style="text-align:center">${__("Avg hrs/mo (3mo)")}</th></tr></thead>
						<tbody>${(m.capacity || [])
							.map(
								(c, i) => `<tr ${i === 0 ? 'style="background:#F4FBF8"' : ""}>
							<td><b>${frappe.utils.escape_html(c.first)}</b>${i === 0 ? ` <span style="font-size:11px;font-weight:700;color:#15803d">← ${__("lightest load")}</span>` : ""}</td>
							<td style="text-align:center">${c.clients}</td>
							<td style="text-align:center">${c.open_now || ""}</td>
							<td style="text-align:center">${c.hours3 || "—"}</td>
						</tr>`
							)
							.join("") || `<tr><td colspan="4" class="text-muted">${__("No bookkeepers assigned yet.")}</td></tr>`}</tbody>
					</table>
					<div class="text-muted" style="font-size:11px;margin-top:8px">${__("Floor is configurable in Duty Settings. Lag and rates depend on attestations and customer-tagged sessions — the disciplines feed the numbers.")}</div>
				`);
			},
		});
	}

	_bpanel_billing($p) {
		frappe.call({
			method: "duty_board.accounting.books_billing",
			args: { period: this.books_period },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const badge = (row) => {
					if (!row.invoice) return `<span style="color:${row.fee ? "#b45309" : "#94a3b8"};font-weight:700">${frappe.utils.escape_html(row.status)}</span>`;
					const col = row.docstatus === 0 ? "#7c3aed" : row.outstanding > 0 ? "#b91c1c" : "#15803d";
					const label = row.docstatus === 0 ? __("Draft — review & submit") : row.outstanding > 0 ? __("Unpaid") : __("Paid");
					return `<a href="/app/sales-invoice/${encodeURIComponent(row.invoice)}" style="color:${col};font-weight:700">${label} · ${frappe.utils.escape_html(row.invoice)}</a>`;
				};
				$p.html(`
					<div style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:8px">
						<button class="btn btn-xs btn-primary" data-gen>🧾 ${__("Generate {0} invoices now", [m.period])}</button>
					</div>
					<table class="table table-bordered" style="font-size:var(--text-sm);margin:0;background:#fff">
						<thead><tr><th>${__("Client")}</th><th style="text-align:right">${__("Fee/mo")}</th><th>${__("This period")} (${m.period})</th></tr></thead>
						<tbody>${m.rows
							.map(
								(row) => `<tr>
							<td><b>${frappe.utils.escape_html(row.customer)}</b></td>
							<td style="text-align:right">${row.fee ? "₦" + Number(row.fee).toLocaleString() : `<span style="color:#b91c1c;font-weight:700">${__("no fee set")}</span>`}</td>
							<td>${badge(row)}</td>
						</tr>`
							)
							.join("")}</tbody>
					</table>
					<div style="font-size:12px;font-weight:800;margin:14px 0 6px">💰 ${__("Awaiting payment")} (${m.unpaid.length}) — ₦${Number(m.unpaid_total).toLocaleString()}</div>
					${m.unpaid.length
						? `<table class="table table-bordered" style="font-size:var(--text-sm);margin:0;background:#fff">
							<thead><tr><th>${__("Client")}</th><th>${__("Invoice")}</th><th style="text-align:right">${__("Outstanding")}</th><th>${__("Due")}</th></tr></thead>
							<tbody>${m.unpaid
								.map(
									(u) => `<tr ${u.days_overdue ? 'style="background:#FDECEA"' : ""}>
								<td><b>${frappe.utils.escape_html(u.customer)}</b></td>
								<td><a href="/app/sales-invoice/${encodeURIComponent(u.name)}">${frappe.utils.escape_html(u.name)}</a></td>
								<td style="text-align:right;font-weight:700">₦${Number(u.outstanding_amount).toLocaleString()}</td>
								<td style="font-size:12px;${u.days_overdue ? "color:#b91c1c;font-weight:700" : ""}">${u.due_date || "—"}${u.days_overdue ? ` · ${u.days_overdue}${__("d overdue")}` : ""}</td>
							</tr>`
								)
								.join("")}</tbody>
						</table>`
						: `<div class="text-muted">${__("Nothing outstanding — everyone has paid.")}</div>`}
					<div class="text-muted" style="font-size:11px;margin-top:8px">${__("Invoices auto-generate on the 28th as drafts; submit them in the desk. Payment status reads the ERP's outstanding amounts.")}</div>
				`);
				$p.find("[data-gen]").on("click", () =>
					frappe.call({
						method: "duty_board.accounting.books_generate_invoices",
						args: { period: this.books_period },
						callback: (rr) => {
							const o = rr.message;
							frappe.show_alert({ message: __("{0} created, {1} already existed{2}", [o.created, o.existing, o.no_fee.length ? ", no fee: " + o.no_fee.join(", ") : ""]), indicator: o.no_fee.length ? "orange" : "green" });
							this.render_books_shell();
						},
					})
				);
			},
		});
	}

	_bpanel_profit($p) {
		frappe.call({
			method: "duty_board.accounting.books_profitability",
			args: { period: this.books_period },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const totF = m.rows.reduce((a, x) => a + (x.fee || 0), 0);
				const totH = m.rows.reduce((a, x) => a + (x.hours || 0), 0);
				$p.html(`
					${m.rows.length
						? `<table class="table table-bordered" style="font-size:var(--text-sm);margin:0">
							<thead><tr><th>${__("Client")}</th><th style="text-align:right">${__("Fee/mo")}</th><th style="text-align:right">${__("Hours")}</th><th style="text-align:right">₦/${__("hr")}</th><th>${__("Who worked it")}</th></tr></thead>
							<tbody>
								${m.rows
									.map(
										(x) => `<tr>
									<td><b>${frappe.utils.escape_html(x.customer)}</b></td>
									<td style="text-align:right">₦${Number(x.fee || 0).toLocaleString()}</td>
									<td style="text-align:right">${x.hours}</td>
									<td style="text-align:right;font-weight:800;${x.rate !== null && x.fee && x.rate < (m.floor || 5000) ? "color:#b91c1c" : "color:#0F5C55"}">${x.rate !== null ? "₦" + Number(x.rate).toLocaleString() : "—"}</td>
									<td class="text-muted" style="font-size:11px">${x.team.map((t) => `${frappe.utils.escape_html(t.first)} ${t.hours}h`).join(" · ") || "—"}</td>
								</tr>`
									)
									.join("")}
								<tr style="background:var(--bg-light-gray,#F4F7F6)"><td><b>${__("Total")}</b></td><td style="text-align:right"><b>₦${Number(totF).toLocaleString()}</b></td><td style="text-align:right"><b>${Math.round(totH * 10) / 10}</b></td><td style="text-align:right"><b>${totH ? "₦" + Number(Math.round(totF / totH)).toLocaleString() : "—"}</b></td><td></td></tr>
							</tbody>
						</table>
						<div class="text-muted" style="font-size:11px;margin-top:8px">${__("Sorted worst rate first. Hours from Work Sessions tagged to the customer; sessions without a customer are invisible here — tagging discipline is the price of this number.")}</div>`
						: `<div class="text-muted">${__("No accounting clients for this period.")}</div>`}
				`);
			},
		});
	}

	my_quiz_dialog(record) {
		frappe.call({
			method: "duty_board.client_room.my_quiz_start",
			args: { record: record },
			callback: (r) => {
				const t = r.message;
				if (!t) return;
				const d = new frappe.ui.Dialog({ title: `📝 ${__("Assessment")} — 10 ${__("questions")}`, size: "large" });
				$(d.body).html(
					t.questions
						.map(
							(q, i) => `
					<div style="margin-bottom:16px" data-q="${q.name}">
						<div style="font-weight:700;margin-bottom:6px">${i + 1}. ${frappe.utils.escape_html(q.question)}</div>
						${q.options
							.map(
								(o, j) => `
							<label style="display:flex;gap:8px;align-items:flex-start;padding:5px 8px;border-radius:8px;cursor:pointer">
								<input type="radio" name="qz_${i}" value="${j}" style="margin-top:3px">
								<span>${frappe.utils.escape_html(o)}</span>
							</label>`
							)
							.join("")}
					</div>`
						)
						.join("") + `<div class="text-muted" style="font-size:var(--text-sm)">${__("Unanswered questions count as wrong. Unlimited retakes — your best score stands.")}</div>`
				);
				d.set_primary_action(__("Submit answers"), () => {
					const answers = {};
					$(d.body).find("[data-q]").each(function () {
						const chosen = $(this).find("input:checked").val();
						if (chosen !== undefined) answers[$(this).data("q")] = parseInt(chosen, 10);
					});
					d.get_primary_btn().prop("disabled", true);
					frappe.call({
						method: "duty_board.client_room.my_quiz_submit",
						args: { attempt: t.attempt, answers: JSON.stringify(answers) },
						callback: (rr) => {
							d.hide();
							this.my_quiz_result_dialog(rr.message, record);
						},
					});
				});
				d.show();
			},
		});
	}

	my_quiz_result_dialog(res, record) {
		if (!res) return;
		const d = new frappe.ui.Dialog({ title: res.passed ? `🏅 ${__("Passed")}` : `📝 ${__("Not this time")}` });
		$(d.body).html(`
			<div style="text-align:center;padding:8px 0 4px">
				<div style="font-size:44px;font-weight:800;color:${res.passed ? "#15803d" : "#b45309"}">${res.score}%</div>
				<div class="text-muted">${__("pass mark")} ${res.pass_mark}% · ${__("attempt")} ${res.attempts}${res.attempts > 1 ? ` · ${__("best")} ${res.best}%` : ""}</div>
				${res.newly_certified ? `<div style="margin-top:8px;font-weight:700;color:#0C4A43">🎓 ${__("Course completed — certified.")}</div>` : ""}
			</div>
			${!res.passed && (res.wrong || []).length
				? `<div style="margin-top:10px"><b>${__("Review these areas, then retake:")}</b>${res.wrong.map((w) => `<div class="text-muted" style="font-size:var(--text-sm);margin:4px 0">• ${frappe.utils.escape_html(w)}</div>`).join("")}</div>`
				: ""}
			<div style="display:flex;gap:10px;justify-content:flex-end;margin-top:12px">
				${!res.passed ? `<button type="button" class="btn btn-sm btn-primary" data-retake>↻ ${__("Retake now")}</button>` : ""}
				<button type="button" class="btn btn-sm btn-default" data-close>${__("Close")}</button>
			</div>
		`);
		$(d.body).find("[data-retake]").on("click", () => { d.hide(); this.my_quiz_dialog(record); });
		$(d.body).find("[data-close]").on("click", () => { d.hide(); this.load_my_training(); this.my_course_dialog(record); });
		d.show();
	}

	render_my_dashboard_cal(m) {
		const [Y, M] = m.month.split("-").map(Number);
		this.$me.find(".duty-cal-title").text(frappe.datetime.month_name ? m.month : new Date(Y, M - 1, 1).toLocaleString("default", { month: "long", year: "numeric" }));
		const first = new Date(Y, M - 1, 1);
		const startPad = (first.getDay() + 6) % 7; // Monday-first
		const dim = new Date(Y, M, 0).getDate();
		const today = frappe.datetime.get_today();
		let cells = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((d) => `<div class="duty-cal-dow">${d}</div>`).join("");
		for (let i = 0; i < startPad; i++) cells += `<div class="duty-cal-cell empty"></div>`;
		for (let d = 1; d <= dim; d++) {
			const key = `${Y}-${String(M).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
			const info = (m.days || {})[key] || {};
			cells += `<div class="duty-cal-cell${key === today ? " today" : ""}" data-day="${key}">
				<span class="dnum">${d}</span>
				${info.meet ? `<span class="cbadge cmeet">📅${info.meet}</span>` : ""}
				${info.todo ? `<span class="cbadge ctodo">📋${info.todo}</span>` : ""}
				${info.due ? `<span class="cbadge cdue">${info.due}</span>` : ""}
				${info.res ? `<span class="cbadge cres">${info.res}</span>` : ""}
				${info.hrs ? `<span class="cbadge chrs">${info.hrs}h</span>` : ""}
			</div>`;
		}
		this.$me.find(".duty-cal-grid").html(cells);
		const shift = (delta) => {
			const nd = new Date(Y, M - 1 + delta, 1);
			this.refresh_me(`${nd.getFullYear()}-${String(nd.getMonth() + 1).padStart(2, "0")}`);
		};
		this.$me.find(".duty-cal-prev").off("click").on("click", () => shift(-1));
		this.$me.find(".duty-cal-next").off("click").on("click", () => shift(1));
		this._me_data = m;
		this.$me.find(".duty-cal-cell:not(.empty)").on("click", (e) => this.me_day_dialog($(e.currentTarget).data("day")));
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
		const q = ((this._pj_filter || "") + "").toLowerCase();
		const list = (this._projects || []).filter(
			(p) => !q || (p.project_name + " " + (p.customer || "")).toLowerCase().indexOf(q) >= 0
		);
		const groups = {};
		list.forEach((p) => (groups[p.customer || __("Internal")] = groups[p.customer || __("Internal")] || []).push(p));
		this._pj_open = this._pj_open || {};
		const active = this.current_project;
		Object.keys(groups)
			.sort()
			.forEach((cust) => {
				const ps = groups[cust];
				const has_active = ps.some((p) => p.name === active);
				const open = q ? true : has_active || this._pj_open[cust];
				const over = ps.reduce((a, p) => a + (p.overdue || 0), 0);
				$(`<div class="duty-pj-cust"><span class="duty-cr-caret">${open ? "▾" : "▸"}</span> ${frappe.utils.escape_html(cust)} <span class="duty-pj-count">${ps.length}</span>${!open && over ? ` <span class="duty-proj-over">⚠ ${over}</span>` : ""}</div>`)
					.appendTo($tabs)
					.on("click", () => {
						if (open) delete this._pj_open[cust];
						else this._pj_open[cust] = 1;
						this.render_project_tabs();
					});
				if (!open) return;
				ps.forEach((p) => {
					const pc = this.proj_color(p.name);
					$(`
					<a class="duty-pj-item ${p.name === active ? "active" : ""}" data-name="${p.name}" style="border-left:3px solid ${pc}">
						<span class="t">${frappe.utils.escape_html(p.project_name)}</span>
						<span class="s">✓ ${p.done}/${p.total}${p.overdue ? ` <span class="duty-proj-over">⚠ ${p.overdue}</span>` : ""}${p.suspended ? " ⏸" : ""}</span>
						<span class="duty-proj-bar"><span style="width:${p.pct || 0}%;background:${pc}"></span></span>
					</a>`)
						.appendTo($tabs)
						.on("click", () => {
							this.current_project = p.name;
							localStorage.setItem("duty_proj", p.name);
							this.render_project_tabs();
							this.load_kanban(p.name);
						});
				});
			});
		if (!list.length)
			$tabs.append(`<div class="text-muted" style="padding:10px;font-size:12.5px">${q ? __("No projects match.") : __("No projects yet.")}</div>`);
		const cur = (this._projects || []).find((p) => p.name === active);
		const $t = this.$projects.find(".duty-pj-title");
		if (cur) {
			const target = cur.target_date
				? ` <span class="duty-proj-target ${cur.days_left != null && cur.days_left < 0 ? "duty-lead-over" : ""}">🎯 ${frappe.datetime.str_to_user(cur.target_date)}${cur.days_left != null ? ` (${cur.days_left}d)` : ""}</span>`
				: "";
			$t.html(target ? `<span class="text-muted" style="font-size:12.5px">${target}</span>` : "");
		} else $t.empty();
	}

	render_calendar(project, data, $wrap) {
		const tasks = [];
		Object.keys(data.tasks || {}).forEach((col) =>
			(data.tasks[col] || []).forEach((t) => tasks.push(Object.assign({ column: col }, t)))
		);
		const base = this._cal_base ? new Date(this._cal_base) : new Date();
		base.setDate(1);
		const y = base.getFullYear();
		const mo = base.getMonth();
		const monthName = base.toLocaleString("default", { month: "long", year: "numeric" });
		const first = (base.getDay() + 6) % 7; // Monday-first
		const dim = new Date(y, mo + 1, 0).getDate();
		const byday = {};
		let undated = 0;
		tasks.forEach((t) => {
			if (!t.due_date) { undated++; return; }
			(byday[t.due_date] = byday[t.due_date] || []).push(t);
		});
		const URG = { Critical: "#B0443C", High: "#A96F1A", Medium: "#0E5A4A", Low: "#6B7772" };
		const today = frappe.datetime.get_today();
		let cells = "";
		for (let i = 0; i < first; i++) cells += `<div class="duty-cal-cell duty-cal-pad"></div>`;
		for (let d = 1; d <= dim; d++) {
			const iso = `${y}-${String(mo + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
			const items = (byday[iso] || [])
				.map(
					(t) => `<div class="duty-cal-task ${t.column === "Completed" ? "done" : ""}" draggable="true" data-name="${t.name}" style="border-left:3px solid ${URG[t.urgency] || "#6B7772"}" title="${frappe.utils.escape_html(t.title)}${t.assignee ? " · " + frappe.utils.escape_html((this.name_map[t.assignee] || t.assignee).split(" ")[0]) : ""}">${frappe.utils.escape_html(t.title)}</div>`
				)
				.join("");
			cells += `<div class="duty-cal-cell ${iso === today ? "today" : ""}" data-day="${iso}"><span class="d"><a class="duty-cal-add" title="${__("Add a task on this day")}">＋</a>${d}</span>${items}</div>`;
		}
		$wrap.append(`
			<div class="duty-cal-head">
				<a class="duty-cal-nav" data-n="-1">‹</a>
				<b>${monthName}</b>
				<a class="duty-cal-nav" data-n="1">›</a>
				<a class="duty-cal-today">${__("Today")}</a>
				${undated ? `<span class="text-muted" style="margin-left:auto;font-size:12px">${undated} ${__("task(s) without a date — visible on the board")}</span>` : ""}
			</div>
			<div class="duty-cal-grid">
				${["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((w) => `<div class="duty-cal-dow">${__(w)}</div>`).join("")}
				${cells}
			</div>`);
		$wrap.find(".duty-cal-nav").on("click", (e) => {
			const b = new Date(y, mo + parseInt($(e.currentTarget).data("n"), 10), 1);
			this._cal_base = b.toISOString();
			this.render_kanban(project, data);
		});
		$wrap.find(".duty-cal-today").on("click", () => {
			this._cal_base = null;
			this.render_kanban(project, data);
		});
		$wrap.find(".duty-cal-task").each((_, el) => {
			el.addEventListener("dragstart", (e) => e.dataTransfer.setData("text", $(el).data("name")));
			$(el).on("click", () =>
				frappe.call({
					method: "duty_board.projects.get_card",
					args: { name: $(el).data("name") },
					callback: (r) => r.message && this.task_dialog(project, r.message),
				})
			);
		});
		$wrap.find(".duty-cal-cell:not(.duty-cal-pad)").each((_, el) => {
			$(el).on("click", (e) => {
				if ($(e.target).closest(".duty-cal-task").length) return;
				const day = $(el).data("day");
				frappe.prompt(
					[
						{ fieldname: "title", fieldtype: "Data", label: __("Task"), reqd: 1 },
						{ fieldname: "assignee", fieldtype: "Autocomplete", label: __("Assignee"), options: this.staff_options() },
						{ fieldname: "urgency", fieldtype: "Select", label: __("Urgency"), options: ["Low", "Medium", "High", "Critical"], default: "Medium" },
					],
					(v) =>
						frappe.call({
							method: "duty_board.projects.create_task",
							args: { project: project, title: v.title, column: "To Do", assignee: v.assignee || null, due_date: day, urgency: v.urgency },
							callback: (r) => r.message && this.render_kanban(project, r.message),
						}),
					__("New task · {0}", [frappe.datetime.str_to_user(day)]),
					__("Add")
				);
			});
			el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("over"); });
			el.addEventListener("dragleave", () => el.classList.remove("over"));
			el.addEventListener("drop", (e) => {
				e.preventDefault();
				el.classList.remove("over");
				const name = e.dataTransfer.getData("text");
				if (!name) return;
				frappe.call({
					method: "duty_board.projects.reschedule_task",
					args: { name: name, due_date: $(el).data("day") },
					callback: (r) => r.message && this.render_kanban(project, r.message),
				});
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
						${t.awaiting_client && t.column !== "Completed" ? `<span class="duty-cr-mswait">⏳ ${__("client")}</span>` : ""}
						${(t.working || []).length ? `<span class="duty-kb-working">⏱ ${t.working.map((u) => `<b style="color:${this.user_color(u)}">${frappe.utils.escape_html((this.name_map[u] || u).split(" ")[0])}</b>`).join(", ")}</span>` : ""}
						${t.stale_days >= 7 && t.column !== "Completed" ? `<span class="duty-stale ${t.stale_days >= 14 ? "duty-stale-red" : ""}">🕸 ${t.stale_days}d</span>` : ""}
						${t.notes ? `<span>💬 ${t.notes}</span>` : ""}
						${t.subs_total ? `<span style="font-weight:700;color:${t.subs_done === t.subs_total ? "#15803d" : "#6B7772"}">☑ ${t.subs_done}/${t.subs_total}</span>` : ""}
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
				<span class="duty-pj-views">
					<a class="duty-pj-v ${(this._pj_view || "board") === "board" ? "on" : ""}" data-v="board">▦ ${__("Board")}</a>
					<a class="duty-pj-v ${this._pj_view === "cal" ? "on" : ""}" data-v="cal">📅 ${__("Calendar")}</a>
				</span>
				<a class="duty-proj-archive">${__("Archive project")}</a>
			</div>
		`).appendTo($wrap);
		$bar.find(".duty-pj-v").on("click", (e) => {
			this._pj_view = $(e.currentTarget).data("v");
			this.render_kanban(project, data);
		});
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
		if ((this._pj_view || "board") === "cal") {
			this.render_calendar(project, data, $wrap);
			return;
		}
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
				{
					fieldname: "awaiting_client",
					fieldtype: "Check",
					label: __("⏳ Awaiting client action (nudges them on the portal)"),
					default: t.awaiting_client ? 1 : 0,
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
						awaiting_client: v.awaiting_client ? 1 : 0,
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
			<div class="duty-lead-section">☑ ${__("Subtasks")}${t.subs_total ? ` <span class="text-muted" style="font-weight:400">${t.subs_done}/${t.subs_total}</span>` : ""}</div>
			<div class="duty-subs">
				${(t.subtasks || []).map((s) => `
				<div class="duty-sub" style="display:flex;gap:9px;align-items:center;padding:5px 0;border-bottom:1px solid #F0EEE8">
					<input type="checkbox" data-sub="${s.row}" ${s.status === "Done" ? "checked" : ""}>
					<span style="flex:1;min-width:0;${s.status === "Done" ? "text-decoration:line-through;color:#96A09B" : ""}">${frappe.utils.escape_html(s.title)}${s.note ? ` <span class="text-muted" title="${frappe.utils.escape_html(s.note)}">🗒</span>` : ""}</span>
					${s.assignee_first ? `<span class="text-muted" style="font-size:11.5px;white-space:nowrap">${frappe.utils.escape_html(s.assignee_first)}</span>` : ""}
					${s.due_date ? `<span class="text-muted" style="font-size:11.5px;white-space:nowrap">${s.due_date.slice(5)}</span>` : ""}
					<a data-subedit="${s.row}" style="cursor:pointer;color:#96A09B" title="${__("Edit")}">✎</a>
					<a data-subdel="${s.row}" style="cursor:pointer;color:#B0443C" title="${__("Remove")}">×</a>
				</div>`).join("")}
				<div style="display:flex;gap:7px;margin:8px 0 2px">
					<input type="text" class="form-control input-sm duty-sub-new" placeholder="${__("Add a subtask…")}">
					<button type="button" class="btn btn-sm btn-default duty-sub-add">＋</button>
				</div>
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
		const subCall = (method, args) =>
			frappe.call({ method: "duty_board.projects." + method, args: args, callback: (r) => reopen(r) });
		$x.find("[data-sub]").on("change", (e) =>
			subCall("subtask_toggle", { task: t.name, row: $(e.currentTarget).data("sub") })
		);
		$x.find("[data-subdel]").on("click", (e) =>
			frappe.confirm(__("Remove this subtask?"), () =>
				subCall("subtask_delete", { task: t.name, row: $(e.currentTarget).data("subdel") })
			)
		);
		$x.find("[data-subedit]").on("click", (e) => {
			const row = $(e.currentTarget).data("subedit");
			const s = (t.subtasks || []).find((z) => z.row === row) || {};
			frappe.prompt(
				[
					{ fieldname: "title", fieldtype: "Data", label: __("Subtask"), default: s.title, reqd: 1 },
					{ fieldname: "assignee", fieldtype: "Autocomplete", label: __("Assignee"), options: this.staff_options(), default: s.assignee || "" },
					{ fieldname: "due_date", fieldtype: "Date", label: __("Due (on or before the card due date)"), default: s.due_date || "" },
					{ fieldname: "note", fieldtype: "Small Text", label: __("Note"), default: s.note || "" },
				],
				(v) => subCall("subtask_update", { task: t.name, row: row, title: v.title, assignee: v.assignee || "", due_date: v.due_date || "", note: v.note || "" }),
				__("Edit subtask"), __("Save")
			);
		});
		const addSub = () => {
			const title = ($x.find(".duty-sub-new").val() || "").trim();
			if (!title) return;
			frappe.prompt(
				[
					{ fieldname: "assignee", fieldtype: "Autocomplete", label: __("Assignee"), options: this.staff_options() },
					{ fieldname: "due_date", fieldtype: "Date", label: __("Due (on or before the card due date)") },
					{ fieldname: "note", fieldtype: "Small Text", label: __("Note") },
				],
				(v) => subCall("subtask_add", { task: t.name, title: title, assignee: v.assignee || null, due_date: v.due_date || null, note: v.note || null }),
				__("New subtask"), __("Add")
			);
		};
		$x.find(".duty-sub-add").on("click", addSub);
		$x.find(".duty-sub-new").on("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addSub(); } });
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
				<b>🤝 ${__("Client Rooms")}<span class="duty-cr-barjoins"></span></b>
				<button class="btn btn-sm btn-primary duty-cr-new">＋ ${__("New Room")}</button>
			</div>
		`).appendTo($list);
		$bar.find(".duty-cr-new").on("click", () =>
			frappe.prompt(
				[
					{ fieldname: "customer", fieldtype: "Link", label: __("Customer"), options: "Customer", reqd: 1 },
					{ fieldname: "unit", fieldtype: "Data", label: __("Unit"), default: "General",
					  description: __("General, HR, Finance… separate rooms keep departments confidential.") },
				],
				(v) =>
					frappe.call({
						method: "duty_board.client_room.create_room",
						args: { customer: v.customer, unit: v.unit || "General" },
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
		const cust_unread = {};
		const cust_unread_sys = {};
		const cust_joins = {};
		let total_unread = 0;
		let total_joins = 0;
		this._rooms.forEach((r) => {
			cust_unread[r.customer] = (cust_unread[r.customer] || 0) + (r.unread_client || 0);
			cust_unread_sys[r.customer] = (cust_unread_sys[r.customer] || 0) + (r.unread_other || 0);
			cust_joins[r.customer] = (cust_joins[r.customer] || 0) + (r.join_requests || 0);
			total_unread += r.unread_client ? 1 : 0;
			total_joins += r.join_requests || 0;
		});
		$(".duty-cr-barjoins").html(
			total_joins ? ` <span class="duty-cr-joinpill">🙋 ${total_joins} ${__("waiting")}</span>` : ""
		);
		const cr_attn2 = total_unread + total_joins;
		$(".duty-tab-clients").text(cr_attn2).toggle(cr_attn2 > 0);
		let prev_cust = null;
		this._rooms.forEach((r) => {
			const folded = !(this._cr_open || {})[r.customer];
			if (r.customer !== prev_cust) {
				prev_cust = r.customer;
				$(`<div class="duty-cr-cust"><span class="duty-cr-caret">${folded ? "▸" : "▾"}</span> ${frappe.utils.escape_html(r.customer)}${folded && cust_unread[r.customer] ? ` <span class="duty-cr-unread" title="${__("new client message(s)")}">${cust_unread[r.customer]}</span>` : ""}${folded && cust_unread_sys[r.customer] ? ` <span class="duty-cr-unread duty-cr-unread-sys" title="${__("system & colleague message(s)")}">${cust_unread_sys[r.customer]}</span>` : ""}${folded && cust_joins[r.customer] ? ` <span class="duty-cr-joinpill">🙋 ${cust_joins[r.customer]}</span>` : ""}</div>`)
					.appendTo($list)
					.on("click", () => {
						this._cr_open = this._cr_open || {};
						if (folded) this._cr_open[r.customer] = 1;
						else delete this._cr_open[r.customer];
						this.render_room_list();
					});
			}
			if (folded) return;
			$(`
				<a class="duty-cr-item ${r.name === this._open_room ? "active" : ""} ${r.status !== "Active" ? "duty-cr-frozen" : ""}">
					<b style="color:${this.proj_color(r.name)}">${r.health ? `<span class="duty-health duty-health-${r.health.state}" title="${frappe.utils.escape_html((r.health.reasons || []).join(" · ") || __("healthy"))}">●</span> ` : ""}${frappe.utils.escape_html(r.unit || "General")}${r.renewal ? (r.renewal.frozen ? ` <span class="duty-renew duty-renew-frozen">⏸</span>` : r.renewal.days_left < 0 ? ` <span class="duty-renew duty-renew-over">🔴 ${-r.renewal.days_left}d</span>` : r.renewal.days_left <= 30 ? ` <span class="duty-renew duty-renew-warn">⏳ ${r.renewal.days_left}d</span>` : "") : ""}${r.unread_client ? ` <span class="duty-cr-unread" title="${__("new client message(s)")}">${r.unread_client}</span>` : ""}${r.unread_other ? ` <span class="duty-cr-unread duty-cr-unread-sys" title="${__("system & colleague message(s)")}">${r.unread_other}</span>` : ""}${r.join_requests ? ` <span class="duty-cr-joinpill" title="${__("Join requests awaiting approval")}">🙋 ${r.join_requests}</span>` : ""}${r.renewal ? (r.renewal.frozen ? ` <span class="duty-renew duty-renew-frozen">⏸</span>` : r.renewal.days_left < 0 ? ` <span class="duty-renew duty-renew-over" title="${__("renewal overdue")}">🔴 ${-r.renewal.days_left}d</span>` : r.renewal.days_left <= 30 ? ` <span class="duty-renew duty-renew-warn" title="${__("renews soon")}">⏳ ${r.renewal.days_left}d</span>` : "") : ""}</b>
					${r.status !== "Active" ? `<span class="duty-cr-status">${__(r.status)}</span>` : ""}
					<span class="duty-cr-last">${frappe.utils.escape_html(r.last || "")}</span>
					<span class="duty-cr-members">👥 ${r.members}</span>
				</a>
			`)
				.appendTo($list)
				.on("click", () => this.open_client_room(r.name));
		});
	}

	jump_to_msg(msg_id) {
		const $t = $(`.duty-cr-msgs .duty-cr-msg[data-name="${msg_id}"]`);
		if (!$t.length) {
			frappe.show_alert(
				{ message: __("The origin message is further up — load earlier messages, then try again."), indicator: "orange" },
				4
			);
			return false;
		}
		$t[0].scrollIntoView({ behavior: "smooth", block: "center" });
		$t.addClass("duty-msg-flash");
		setTimeout(() => $t.removeClass("duty-msg-flash"), 2000);
		return true;
	}

	view_origin(room_name, msg_id) {
		if (this._open_room === room_name && $(".duty-cr-msgs").length) {
			this.jump_to_msg(msg_id);
			return;
		}
		this.show_face("clients");
		this.open_client_room(room_name);
		setTimeout(() => this.jump_to_msg(msg_id), 1300);
	}

	open_client_room(name) {
		this._open_room = name;
		frappe.call({
			method: "duty_board.client_room.mark_room_seen",
			args: { name: name },
			callback: () => this.refresh_clients(true),
		});
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
			<div class="duty-cr-msg ${m.internal ? "duty-cr-internal" : m.mine ? "duty-cr-mine" : m.is_staff ? "duty-cr-staff" : "duty-cr-client"}" data-name="${m.name}">
				<a class="duty-cr-reply" title="${__("Reply")}">↩</a>
				<span class="duty-msg-who" style="color:${this.user_color(m.owner)}">${m.internal ? "🔒 " : ""}${frappe.utils.escape_html((m.who || m.owner).split(" ")[0])}${m.is_staff ? "" : ` · ${__("client")}`}</span>
				${m.ref ? `<a class="duty-cr-quote" data-target="${m.ref}"><b>${frappe.utils.escape_html(m.ref_who || "")}</b>: ${frappe.utils.escape_html(m.ref_text || "")}</a>` : ""}
				<span class="duty-msg-text">${frappe.utils.escape_html(m.message)}</span>
				${m.attachment_url ? `<span class="duty-cr-att">${m.is_image ? `<a href="/api/method/duty_board.client_room.room_file?msg=${m.name}" target="_blank"><img src="/api/method/duty_board.client_room.room_file?msg=${m.name}"></a>` : m.is_audio ? `<audio controls preload="none" src="/api/method/duty_board.client_room.room_file?msg=${m.name}" style="display:block;margin-top:6px;max-width:240px"></audio>` : `<a class="duty-issue-filelink" href="/api/method/duty_board.client_room.room_file?msg=${m.name}" target="_blank">📎 ${frappe.utils.escape_html(m.attachment_name || "file")}</a>`}</span>` : ""}
				<span class="duty-msg-time">${frappe.datetime.str_to_user(m.creation)}</span>
				${m.is_staff ? "" : `<a class="duty-cr-mktask" data-mid="${m.name}" data-text="${frappe.utils.escape_html(m.message.slice(0, 120))}" title="${__("Make task from this")}">➕</a><a class="duty-cr-mkchreq" data-mid="${m.name}" data-text="${frappe.utils.escape_html(m.message.slice(0, 120))}" title="${__("Draft change request from this")}">💱</a>`}
			</div>`;
	}

	render_client_room(x) {
		if (x.name !== this._open_room) return;
		const $room = this.$clients.find(".duty-cr-room").show();
		this.$clients.addClass("cr-room-open");
		const counts = { Queued: 0, "In Progress": 0, Done: 0 };
		(x.tasks || []).forEach((t) => (counts[t.status] = (counts[t.status] || 0) + 1));
		$room.html(`
			<div class="duty-cr-ribbon">🤝 ${__("{0} can read this room — whispers 🔒 excepted", [frappe.utils.escape_html(x.customer)])}</div>
			<div class="duty-cr-head">
				<a class="duty-cr-back">‹ ${__("Rooms")}</a>
				<b>${frappe.utils.escape_html(x.customer)}</b>
				<span class="duty-cr-taskchips">📋 ${counts.Queued} ${__("queued")} · ${counts["In Progress"]} ${__("in progress")} · ${counts.Done} ${__("done")}</span>
				<span class="duty-cr-owner" title="${__("Account manager")}">★ ${x.owner_user ? frappe.utils.escape_html((this.name_map[x.owner_user] || x.owner_user).split(" ")[0]) : `<i>${__("unowned")}</i>`}</span>
				${(() => {
					const seen = (x.members || []).map((m) => m.last_seen).filter(Boolean).sort().pop();
					return seen ? `<span class="duty-cr-lastseen">👀 ${__("client seen")} ${frappe.datetime.comment_when(seen)}</span>` : "";
				})()}
				<a class="duty-cr-academy" title="${__("Training Academy")}">🎓</a>
				<a class="duty-cr-deps" title="${__("Client dependencies — what we're waiting on")}">📋</a>
				<a class="duty-cr-scope" title="${__("Room scope & support plan")}">⚖</a>
				<a class="duty-cr-uat" title="${__("Acceptance testing (UAT)")}">🧪</a>
				<a class="duty-cr-tl" title="${__("Delivery accountability timeline")}">📜</a>
				<a class="duty-cr-metrics" title="${__("Live metrics for this customer")}">📈</a>
				<a class="duty-cr-report" title="${__("Generate last month's service report")}">📊</a>
				<a class="duty-cr-rename" title="${__("Rename room")}">✏</a>
				<a class="duty-cr-delete" title="${__("Delete room (System Manager)")}">🗑</a>
				<span class="duty-cr-tools">
					<a class="duty-cr-shelfbtn">📚 ${__("Shelf")}</a>
					<a class="duty-cr-membersbtn">👥 ${__("Members")}${(x.requests || []).length ? ` <b class="duty-cr-reqbadge">${x.requests.length}</b>` : ""}</a>
					${frappe.user.has_role("System Manager") ? `<a class="duty-cr-freeze">${x.status === "Active" ? "🧊 " + __("Freeze") : "▶ " + __("Unfreeze")}</a>` : ""}
				</span>
			</div>
			<div class="duty-cr-main">
			<div class="duty-cr-chatcol">
			<div class="duty-cr-msgs">${(x.messages || []).map((m) => this.cr_msg(m)).join("") || `<div class="text-muted">${__("No messages yet.")}</div>`}</div>
			<div class="duty-cr-typing" style="display:none"></div>
			<div class="duty-cr-replychip"></div>
			<div class="duty-cr-pending"></div>
			<div class="duty-cr-emojis" style="display:none"></div>
			<div class="duty-cr-compose">
				<label class="duty-cr-int"><input type="checkbox" class="duty-cr-internal-toggle"> 🔒 ${__("Internal")}</label>
				<label class="duty-cr-attach" title="${__("Attach image / file")}">📎<input type="file" hidden></label>
				<a class="duty-cr-emojibtn" title="${__("Emoji")}">😊</a>
				<textarea rows="2" class="form-control duty-cr-input" placeholder="${__("Message {0}... Enter to send", [frappe.utils.escape_html(x.customer)])}"></textarea>
				<button type="button" class="btn btn-primary btn-sm duty-cr-send">${__("Send")}</button>
			</div>
			</div>
			<div class="duty-cr-side ${this._cr_tasks_open === false ? "folded" : ""}">
			<div class="duty-cr-tasksbar">
				<a class="duty-cr-taskstoggle"><b>${this._cr_tasks_open === false ? "◂" : "▸"} 📋 ${this._cr_tasks_open === false ? "" : `${__("Tasks")} (${(x.tasks || []).length})`}</b></a>
				${this._cr_tasks_open === false ? "" : `<select class="form-control input-sm duty-cr-tfilter">
					<option value="">${__("All")}</option>
					<option ${this._cr_tfilter === "Queued" ? "selected" : ""}>Queued</option>
					<option ${this._cr_tfilter === "In Progress" ? "selected" : ""}>In Progress</option>
					<option ${this._cr_tfilter === "Done" ? "selected" : ""}>Done</option>
				</select>`}
			</div>
			<div class="duty-cr-sidebody">
			<div class="duty-cr-tasks">
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
			<div class="duty-cr-mstones"></div>
			<div class="duty-cr-chreqs"></div>
			<div class="duty-cr-meetings"></div>
			<div class="duty-cr-unsettled"></div>
			</div>
			</div>
			</div>
		`);
		const $msgs = $room.find(".duty-cr-msgs");
		$msgs.scrollTop($msgs[0].scrollHeight);
		const $input = $room.find(".duty-cr-input");
		const $int = $room.find(".duty-cr-internal-toggle");
		const restyle = () => $room.find(".duty-cr-compose").toggleClass("duty-cr-composing-internal", $int.is(":checked"));
		$int.on("change", restyle);
		this._cr_reply = null;
		const show_reply = () => {
			const $rc = $room.find(".duty-cr-replychip").empty();
			if (this._cr_reply) {
				$(`<span class="duty-file-chip">↩ <b>${frappe.utils.escape_html(this._cr_reply.who)}</b>: ${frappe.utils.escape_html(this._cr_reply.text)} <a>×</a></span>`)
					.appendTo($rc)
					.find("a")
					.on("click", () => {
						this._cr_reply = null;
						show_reply();
					});
			}
		};
		const $msgs2 = $room.find(".duty-cr-msgs");
		$msgs2.find(".duty-cr-reply").on("click", (e) => {
			const $m = $(e.currentTarget).closest(".duty-cr-msg");
			const mm = (x.messages || []).find((q) => q.name === $m.data("name"));
			if (!mm) return;
			this._cr_reply = {
				name: mm.name,
				who: (mm.who || mm.owner).split(" ")[0],
				text: (mm.message || "📎").slice(0, 80),
			};
			if (mm.internal) {
				$int.prop("checked", true);
				restyle();
			}
			show_reply();
			$input.trigger("focus");
		});
		$msgs2.find(".duty-cr-quote").on("click", (e) => {
			const target = $(e.currentTarget).data("target");
			const $t = $msgs2.find(`.duty-cr-msg[data-name="${target}"]`);
			if (!$t.length) {
				frappe.show_alert({ message: __("That message is further up the history."), indicator: "orange" }, 3);
				return;
			}
			$t[0].scrollIntoView({ behavior: "smooth", block: "center" });
			$t.addClass("duty-msg-flash");
			setTimeout(() => $t.removeClass("duty-msg-flash"), 1600);
		});
		const EMOJIS = ["😀","😂","🙏","👍","👌","🙌","🎉","❤️","🔥","💯","😅","😢","😡","🤔","👀","✅","❌","⏳","📌","💡","📞","🤝","🚀","🙈"];
		$room.find(".duty-cr-emojibtn").on("click", () => {
			const $e = $room.find(".duty-cr-emojis");
			if ($e.is(":visible")) return $e.hide();
			if (!$e.children().length) {
				EMOJIS.forEach((em) =>
					$(`<a>${em}</a>`)
						.appendTo($e)
						.on("click", () => {
							const el = $input[0];
							const p = el.selectionStart || el.value.length;
							el.value = el.value.slice(0, p) + em + el.value.slice(p);
							el.focus();
							el.selectionStart = el.selectionEnd = p + em.length;
						})
				);
			}
			$e.css("display", "flex");
		});
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
					ref: this._cr_reply ? this._cr_reply.name : null,
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
			const mid = $(e.currentTarget).data("mid");
			frappe.prompt(
				[
					{ fieldname: "title", fieldtype: "Data", label: __("Issue title"), default: seed, reqd: 1 },
					{ fieldname: "detail", fieldtype: "Small Text", label: __("Details (client-visible)") },
				],
				(v) =>
					frappe.call({
						method: "duty_board.client_room.make_task_from_message",
						args: { name: x.name, title: v.title, detail: v.detail || null, msg: mid || null },
						callback: (r) => r.message && this.render_client_room(r.message),
					}),
				__("Log client-visible issue"),
				__("Create")
			);
		});
		$room.find(".duty-cr-mkchreq").on("click", (e) => {
			const mid = $(e.currentTarget).data("mid");
			const seed = $(e.currentTarget).data("text");
			frappe.prompt(
				[{ fieldname: "title", fieldtype: "Data", label: __("Change request title"), default: seed, reqd: 1 }],
				(v) =>
					frappe.call({
						method: "duty_board.client_room.chreq_from_message",
						args: { name: x.name, msg: mid, title: v.title },
						callback: (r) => {
							if (r.message) {
								this.render_client_room(r.message);
								this.chreqs_dialog(r.message);
							}
						},
					}),
				__("Draft change request — the client's message becomes the original request"),
				__("Draft")
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
		const $us = $room.find(".duty-cr-unsettled");
		if ($us.length && (x.unsettled || []).length) {
			$us.html(
				`<div class="duty-lead-section">📅 ${__("How did these go?")}</div>` +
					x.unsettled
						.map(
							(m) => `
					<div class="duty-cr-meeting">
						<b>${frappe.utils.escape_html(m.topic)}</b>
						<span>${frappe.datetime.str_to_user(m.meeting_date).slice(0, 5)} ${m.start_time}</span>
						<a class="duty-cr-mheld" data-id="${m.name}">✓ ${__("Held")}</a>
						<a class="duty-cr-mmissed" data-id="${m.name}">✗ ${__("Missed")}</a>
					</div>`
						)
						.join("")
			);
			const settle = (id, outcome) =>
				frappe.prompt(
					{ fieldname: "note", fieldtype: "Small Text", label: __("Note (client sees this — optional)") },
					(v) =>
						frappe.call({
							method: "duty_board.client_room.settle_meeting_outcome",
							args: { id: id, outcome: outcome, note: v.note || null },
							callback: (r) => r.message && this.render_client_room(r.message),
						}),
					outcome === "Held" ? __("Meeting held") : __("Meeting missed"),
					__("Save")
				);
			$us.find(".duty-cr-mheld").on("click", (e) => settle($(e.currentTarget).data("id"), "Held"));
			$us.find(".duty-cr-mmissed").on("click", (e) => settle($(e.currentTarget).data("id"), "Missed"));
		} else if ($us.length) {
			$us.empty();
		}
		const $ms = $room.find(".duty-cr-mstones");
		if ($ms.length) {
			const mst = x.milestones || [];
			const done = mst.filter((m) => m.status === "Approved").length;
			const waiting = mst.filter((m) => m.status === "Awaiting Approval").length;
			const current = mst.find((m) => m.status === "In Progress");
			$ms.html(`
				<div class="duty-lead-section">🏁 ${__("Milestones")} <a class="duty-cr-msmanage">${__("Manage")}</a></div>
				${mst.length
					? `<div class="duty-cr-msline">
							<div class="duty-cr-msbar"><i style="width:${Math.round((done / mst.length) * 100)}%"></i></div>
							<span>${done}/${mst.length} ${__("approved")}${waiting ? ` · <b class="duty-cr-mswait">⏳ ${waiting} ${__("awaiting client")}</b>` : ""}${current ? ` · 🔵 ${frappe.utils.escape_html(current.title)}` : ""}</span>
						</div>`
					: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No milestones yet — Manage to seed the Xlevel method.")}</div>`}
			`);
			$ms.find(".duty-cr-msmanage").on("click", () => this.milestones_dialog(x));
		}
		const $cq = $room.find(".duty-cr-chreqs");
		if ($cq.length) {
			const crs = x.change_requests || [];
			const waiting = crs.filter((c) => c.status === "Awaiting Approval").length;
			const approved = crs.filter((c) => ["Approved", "In Delivery", "Delivered"].includes(c.status));
			const declined = crs.filter((c) => c.status === "Declined").length;
			$cq.html(`
				<div class="duty-lead-section">💱 ${__("Change requests")} <a class="duty-cr-cqmanage">${__("Manage")}</a></div>
				${crs.length
					? `<div class="text-muted" style="font-size:var(--text-sm)">
							${approved.length}/${crs.length} ${__("approved")}${waiting ? ` · <b class="duty-cr-mswait">⏳ ${waiting} ${__("awaiting client")}</b>` : ""}${declined ? ` · ↩ ${declined} ${__("declined")}` : ""}${approved.length ? ` · ${approved.map((c) => c.approved_fmt).filter(Boolean).join(" + ") || ""}` : ""}
						</div>`
					: `<div class="text-muted" style="font-size:var(--text-sm)">${__("No change requests — paid scope beyond the subscription starts here.")}</div>`}
			`);
			$cq.find(".duty-cr-cqmanage").on("click", () => this.chreqs_dialog(x));
		}
		const $mt = $room.find(".duty-cr-meetings");
		if ($mt.length && (x.meetings || []).length) {
			$mt.html(
				`<div class="duty-lead-section">📅 ${__("Meetings")}</div>` +
					x.meetings
						.map(
							(m) => `
					<div class="duty-cr-meeting">
						<span class="duty-cr-mstatus ${m.status === "Confirmed" ? "ok" : "wait"}">${m.status === "Confirmed" ? "✅" : "⏳"}</span>
						<b>${frappe.utils.escape_html(m.topic)}</b>
						<span>${frappe.datetime.str_to_user(m.meeting_date).slice(0, 5)} ${m.start_time} · ${m.staff.map(frappe.utils.escape_html).join(", ")}${m.requested_first ? ` · 🙋 ${frappe.utils.escape_html(m.requested_first)}` : ""}</span>
						${m.status === "Pending" ? `<a class="duty-cr-mconfirm" data-id="${m.name}">✔ ${__("Confirm")}</a><a class="duty-cr-mdecline" data-id="${m.name}">✖</a>` : ""}
					</div>`
						)
						.join("")
			);
			$mt.find(".duty-cr-mconfirm").on("click", (e) =>
				frappe.call({
					method: "duty_board.client_room.confirm_meeting",
					args: { id: $(e.currentTarget).data("id") },
					callback: (r) => r.message && this.render_client_room(r.message),
				})
			);
			$mt.find(".duty-cr-mdecline").on("click", (e) => {
				const id = $(e.currentTarget).data("id");
				frappe.prompt(
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Why not? (client sees this)") },
					(v) =>
						frappe.call({
							method: "duty_board.client_room.decline_meeting",
							args: { id: id, reason: v.reason || null },
							callback: (r) => r.message && this.render_client_room(r.message),
						}),
					__("Decline meeting"),
					__("Decline")
				);
			});
		} else if ($mt.length) {
			$mt.empty();
		}
		$room.find(".duty-cr-shelfbtn").on("click", () => this.room_shelf_dialog(x));
		$room.find(".duty-cr-back").on("click", () => this.$clients.removeClass("cr-room-open"));
		$room.find(".duty-cr-academy").on("click", () => this.academy_dialog(x));
		$room.find(".duty-cr-deps").on("click", () => this.deps_dialog(x));
		$room.find(".duty-cr-uat").on("click", () => this.uat_dialog(x));
		$room.find(".duty-cr-tl").on("click", () => this.timeline_dialog(x));
		$room.find(".duty-cr-scope").on("click", () => {
			frappe.call({ method: "frappe.client.get_value", args: { doctype: "Client Room", filters: { name: x.name }, fieldname: ["scope_note", "support_plan", "project"] }, callback: (rv) => {
				const cur = rv.message || {};
				frappe.prompt(
					[
						{ fieldname: "support_plan", fieldtype: "Data", label: __("Support plan (shown to client, e.g. 'Unlimited support · changes quoted via CR')"), default: cur.support_plan || "" },
						{ fieldname: "scope_note", fieldtype: "Small Text", label: __("Contract scope — supported modules & boundaries"), default: cur.scope_note || "" },
						{ fieldname: "project", fieldtype: "Link", options: "Duty Project", label: __("Project board for this room (tasks, milestones, CR delivery)"), default: cur.project || "" },
					],
					(v) => frappe.call({ method: "duty_board.commercial.set_room_scope", args: { name: x.name, scope_note: v.scope_note || "", support_plan: v.support_plan || "" }, callback: () =>
						frappe.call({ method: "duty_board.client_room.room_set_project", args: { name: x.name, project: v.project || null }, callback: () => frappe.show_alert({ message: __("⚖ Scope & project saved"), indicator: "green" }) })
					}),
					__("Room scope"), __("Save")
				);
			}});
		});
		$room.find(".duty-cr-metrics").on("click", () =>
			frappe.call({
				method: "duty_board.client_room.room_metrics",
				args: { name: x.name },
				callback: (r) => {
					const m = r.message || {};
					const d = new frappe.ui.Dialog({ title: `📈 ${x.customer} — ${__("Live metrics")}` });
					const tile = (v, l) => (v === null || v === undefined) ? "" : `<div class="duty-mtile"><b>${frappe.utils.escape_html(String(v))}</b><span>${frappe.utils.escape_html(l)}</span></div>`;
					$(d.body).html(`<div class="duty-mtiles">
						${tile(m.open_now, __("open now"))}
						${tile(m.new_30, __("new · 30 days"))}
						${tile(m.resolved_30, __("completed · 30 days"))}
						${tile(m.avg_ack, __("avg response"))}
						${tile(m.avg_res, __("avg resolution"))}
						${tile(m.ack_pct !== null ? m.ack_pct + "%" : null, __("responded within SLA"))}
						${tile(m.res_pct !== null ? m.res_pct + "%" : null, __("resolved within SLA"))}
						${tile(m.avg_stars !== null ? "★ " + m.avg_stars : null, __("client rating") + ` (${m.rated_n})`)}
						${tile(m.ms_pct !== null ? m.ms_pct + "%" : null, __("milestones approved") + ` (${m.ms_done}/${m.ms_total})`)}
					</div>`);
					if (!$(d.body).find(".duty-mtile").length)
						$(d.body).html(`<div class="text-muted">${__("Numbers appear as work happens.")}</div>`);
					d.show();
				},
			})
		);
		$room.find(".duty-cr-report").on("click", () =>
			frappe.confirm(
				__("Generate last month's service report and place it on this room's shelf? The client is notified."),
				() =>
					frappe.call({
						method: "duty_board.client_room.generate_service_report",
						args: { name: x.name },
						callback: (r) => {
							if (r.message)
								frappe.show_alert({
									message: __("📊 {0} report published to the shelf", [r.message.label]),
									indicator: "green",
								});
							this.load_client_room(x.name);
						},
					})
			)
		);
		$room.find(".duty-cr-rename").on("click", () =>
			frappe.prompt(
				{ fieldname: "unit", fieldtype: "Data", label: __("Room name"), default: x.unit || "General", reqd: 1 },
				(v) =>
					frappe.call({
						method: "duty_board.client_room.rename_room_unit",
						args: { name: x.name, unit: v.unit },
						callback: (r) => {
							if (r.message) this.render_client_room(r.message);
							this.refresh_clients(true);
						},
					}),
				__("Rename room"),
				__("Rename")
			)
		);
		$room.find(".duty-cr-delete").on("click", () =>
			frappe.confirm(
				__("Delete <b>{0} · {1}</b>?<br><br>All messages, members, shelf documents and meetings in this room are permanently removed. Client-visible issues survive and move to the General room.", [
					frappe.utils.escape_html(x.customer),
					frappe.utils.escape_html(x.unit || "General"),
				]),
				() =>
					frappe.call({
						method: "duty_board.client_room.delete_room",
						args: { name: x.name },
						callback: () => {
							this._open_room = null;
							this.refresh_clients();
							frappe.show_alert({ message: __("Room deleted"), indicator: "orange" });
						},
					})
			)
		);
		$room.find(".duty-cr-owner").on("click", () =>
			frappe.prompt(
				{
					fieldname: "owner",
					fieldtype: "Autocomplete",
					label: __("Account manager"),
					options: this.staff_options(),
					default: x.owner_user || "",
				},
				(v) =>
					frappe.call({
						method: "duty_board.client_room.set_room_owner",
						args: { name: x.name, owner: v.owner || null },
						callback: (r) => r.message && this.render_client_room(r.message),
					}),
				__("Who owns this account?"),
				__("Set")
			)
		);
		$room.find(".duty-cr-membersbtn").on("click", () => this.room_members_dialog(x));
		$room.find(".duty-cr-freeze").on("click", () =>
			frappe.call({
				method: "duty_board.client_room.set_room_status",
				args: { name: x.name, status: x.status === "Active" ? "Frozen" : "Active" },
				callback: () => this.load_client_room(x.name),
			})
		);
	}

	pricing_dialog() {
		frappe.call({
			method: "duty_board.commercial.pricing_queue",
			callback: (r) => {
				const q = (r.message || {}).queue || [];
				const d = new frappe.ui.Dialog({ title: __("💼 CRs awaiting your pricing"), size: "large" });
				$(d.body).html(
					q.length
						? q.map((z) => `<div style="border:1px solid #e2e8f0;border-radius:8px;padding:8px;margin-bottom:8px${z.age_days > 2 ? ";background:#fffbeb" : ""}">
							<b>${frappe.utils.escape_html(z.customer)}</b> · ${frappe.utils.escape_html(z.title)}
							<span style="float:right;font-size:11px;font-weight:700;color:${z.age_days > 2 ? "#b45309" : "#64748b"}">${z.age_days}d ${__("waiting")}</span>
							<div class="text-muted" style="font-size:12px;margin:4px 0">${frappe.utils.escape_html((z.original_request || z.reason || "").slice(0, 300))}</div>
							<button class="btn btn-xs btn-primary" data-price="${z.name}">${__("Decide")}</button>
						</div>`).join("")
						: `<p class="text-muted">${__("Queue clear — nothing awaiting pricing.")}</p>`
				);
				$(d.body).find("[data-price]").on("click", (e) => {
					const id = $(e.currentTarget).data("price");
					frappe.prompt(
						[
							{ fieldname: "decision", fieldtype: "Select", label: __("Decision"), options: ["Priced", "Covered by Subscription", "Goodwill", "Rejected", "Deferred"], reqd: 1 },
							{ fieldname: "price", fieldtype: "Currency", label: __("Price (₦, for Priced)") },
							{ fieldname: "estimate_hours", fieldtype: "Float", label: __("Estimated hours") },
							{ fieldname: "note", fieldtype: "Small Text", label: __("Note (kept on the CR)") },
						],
						(v) => frappe.call({
							method: "duty_board.commercial.chreq_price",
							args: { name: id, decision: v.decision, price: v.price || 0, estimate_hours: v.estimate_hours || 0, note: v.note || null },
							callback: () => { d.hide(); this.pricing_dialog(); },
						}),
						__("Price this CR"), __("Apply")
					);
				});
				d.show();
			},
		});
	}

	cost_dialog() {
		frappe.call({
			method: "duty_board.commercial.cost_to_serve",
			args: { months: 1 },
			callback: (r) => {
				const m = r.message || {};
				const d = new frappe.ui.Dialog({ title: __("💰 Cost to serve — last {0} month(s)", [m.months]), size: "extra-large" });
				const naira = (v) => (v || v === 0 ? "₦" + Number(v).toLocaleString() : "—");
				$(d.body).html(`
					${!m.rate ? `<div style="background:#fffbeb;border-radius:8px;padding:8px;font-size:12px;margin-bottom:8px">⚠ ${__("Set the blended staff cost rate in Duty Settings to see costs and margins.")}</div>` : ""}
					<table class="table table-sm" style="font-size:12px"><tr><th>${__("Customer")}</th><th>${__("Hours")}</th><th>${__("Support")}</th><th>${__("Delivery")}</th><th>${__("Cost")}</th><th>${__("Known fee/mo")}</th><th></th></tr>
					${(m.rows || []).map((z) => `<tr style="${z.fee_covers === false ? "background:#fef2f2" : ""}">
						<td><b>${frappe.utils.escape_html(z.customer)}</b><br><span class="text-muted">${z.staff_count} ${__("staff")}</span></td>
						<td><b>${z.hours}</b></td><td>${z.support_hours}</td><td>${z.delivery_hours}</td>
						<td>${naira(z.cost)}</td><td>${naira(z.monthly_fee)}</td>
						<td>${z.fee_covers === false ? `<b style="color:#b91c1c">${__("under water")}</b>` : z.fee_covers ? `<span style="color:#15803d">✓</span>` : ""}</td>
					</tr>`).join("")}</table>
					<p class="text-muted" style="font-size:11px">${__("Hours from work sessions with a customer; fee shown where known (accounting fee today). Red rows: attention cost exceeds known fee — a renewal-conversation list, not an invoice list.")}</p>
				`);
				d.show();
			},
		});
	}

	book_matcher(query, cb) {
		frappe.call({
			method: "duty_board.library.search_books",
			args: { query: query },
			callback: (r) => {
				const hits = r.message || [];
				if (!hits.length) { cb(null); return; }
				const d = new frappe.ui.Dialog({ title: __("🔎 Is it one of these?"), size: "large" });
				$(d.body).html(
					hits.map((h, i) => `
					<div class="duty-bkm" data-i="${i}" style="display:flex;gap:12px;border:1px solid #E8E5DD;border-radius:10px;padding:10px 12px;margin-bottom:8px;cursor:pointer">
						${h.thumbnail ? `<img src="${h.thumbnail}" style="width:52px;height:78px;object-fit:cover;border-radius:6px;flex:none">` : `<div style="width:52px;height:78px;background:#EFEDE6;border-radius:6px;flex:none"></div>`}
						<div style="min-width:0">
							<b style="font-size:13.5px">${frappe.utils.escape_html(h.title)}${h.subtitle ? `: ${frappe.utils.escape_html(h.subtitle)}` : ""}</b>
							<div class="text-muted" style="font-size:12px">${frappe.utils.escape_html(h.authors)}${h.year ? ` · ${h.year}` : ""}${h.publisher ? ` · ${frappe.utils.escape_html(h.publisher)}` : ""}${h.pages ? ` · ${h.pages}p` : ""}</div>
							${h.description ? `<div class="text-muted" style="font-size:11.5px;margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${frappe.utils.escape_html(h.description)}</div>` : ""}
						</div>
					</div>`).join("") +
					`<a class="duty-bkm-none" style="cursor:pointer;font-size:12.5px;color:#6B7772">${__("None of these — fill details by hand")}</a>`
				);
				$(d.body).find(".duty-bkm").on("click", (e) => { d.hide(); cb(hits[$(e.currentTarget).data("i")]); });
				$(d.body).find(".duty-bkm-none").on("click", () => { d.hide(); cb(null); });
				d.show();
			},
			error: () => cb(null),
		});
	}

	refresh_library() {
		frappe.call({
			method: "duty_board.library.library",
			callback: (r) => {
				const m0 = r.message || {};
				const books = m0.books || [];
				const mgr = !!m0.manager;
				this._lib_mgr = mgr;
				const $L = this.$library.empty();
				const STARS = (v) => "★".repeat(Math.round(v)) + "☆".repeat(5 - Math.round(v));
				const groups = {};
				books.forEach((b) => (groups[b.category || __("Uncategorised")] = groups[b.category || __("Uncategorised")] || []).push(b));
				const cats = Object.keys(groups).sort((a, b2) => (a === __("Uncategorised")) - (b2 === __("Uncategorised")) || a.localeCompare(b2));
				$L.append(`<div style="display:flex;align-items:center;gap:12px;margin:4px 0 14px">
					<h3 style="margin:0">📚 ${__("Library")}</h3>
					${mgr ? `<span style="margin-left:auto"><input type="file" accept=".pdf,.epub" class="duty-bk-file" style="font-size:12px">
					<button class="btn btn-sm btn-primary duty-bk-up">📚 ${__("Convert & add")}</button></span>` : ""}
				</div>`);
				if (!books.length) $L.append(`<div class="text-muted">${__("No books on the shelf yet.")}</div>`);
				cats.forEach((cat) => {
					$L.append(`<div style="font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#6B7772;margin:16px 0 8px">${frappe.utils.escape_html(cat)} <span style="color:#b3b8b5">${groups[cat].length}</span></div>`);
					const $row = $(`<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px"></div>`).appendTo($L);
					groups[cat].forEach((b) => {
						$(`<div class="duty-bk" data-book="${b.name}" style="border:1px solid #E8E5DD;border-radius:12px;padding:12px 14px;cursor:pointer;background:#fff;display:flex;gap:12px">
							${b.cover ? `<img src="${b.cover}" style="width:56px;height:84px;object-fit:cover;border-radius:6px;flex:none;align-self:flex-start">` : ""}
							<div style="min-width:0;flex:1">
							<div style="display:flex;gap:8px;align-items:baseline">
								<b style="font-size:14px;flex:1">${frappe.utils.escape_html(b.title)}</b>
								<span style="font-size:11.5px;font-weight:700;border-radius:99px;padding:2px 9px;background:${b.pct >= 100 ? "#E4EEEA" : b.pct ? "#FBF3E4" : "#EFEDE6"};color:${b.pct >= 100 ? "#0E5A4A" : b.pct ? "#A96F1A" : "#6B7772"}">${b.pct >= 100 ? __("finished") : b.pct ? b.pct + "%" : __("new")}</span>
							</div>
							${b.author ? `<div class="text-muted" style="font-size:12px">${frappe.utils.escape_html(b.author)}</div>` : ""}
							<div style="font-size:12px;margin-top:4px;color:#A96F1A">${b.rating_n ? `${STARS(b.rating_avg)} <span class="text-muted">${b.rating_avg} · ${b.rating_n}</span>` : `<span class="text-muted">${__("no ratings yet")}</span>`}</div>
							${b.description ? `<div class="text-muted" style="font-size:12px;margin-top:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${frappe.utils.escape_html(b.description)}</div>` : ""}
							<div class="text-muted" style="font-size:11px;margin-top:6px">${b.chapter_count} ${__("chapters")}${b.words ? ` · ~${Math.round(b.words / 200)} ${__("min")}` : ""}${b.last_read_at ? ` · ${__("read")} ${b.last_read_at.slice(0, 10)}` : ""}
								${mgr ? `<a class="duty-bk-fetch" data-book="${b.name}" style="float:right;color:#0E5A4A;margin-left:8px">🔎 ${__("fetch")}</a><a class="duty-bk-edit" data-book="${b.name}" style="float:right;color:#6B7772;margin-left:8px">${__("edit")}</a><a class="duty-bk-del" data-book="${b.name}" style="float:right;color:#B0443C">${__("remove")}</a>` : ""}</div>
							<div style="height:4px;background:#EFEDE6;border-radius:99px;margin-top:8px"><div style="height:4px;width:${b.pct}%;background:#0E5A4A;border-radius:99px"></div></div>
							</div>
						</div>`).appendTo($row);
					});
				});
				$L.find(".duty-bk-fetch").on("click", (e) => {
					e.stopPropagation();
					const bk = $(e.currentTarget).data("book");
					const b = books.find((x) => x.name === bk) || {};
					this.book_matcher(b.title + " " + (b.author || ""), (meta) => {
						if (!meta) return;
						frappe.call({
							method: "duty_board.library.apply_book_meta",
							args: { book: bk, title: meta.title, author: meta.authors || "", description: meta.description || "", category: b.category || meta.categories || "", cover_url: meta.thumbnail || null },
							callback: () => this.refresh_library(),
						});
					});
				});
				$L.find(".duty-bk").on("click", (e) => {
					if ($(e.target).is(".duty-bk-del,.duty-bk-edit,.duty-bk-fetch")) return;
					this.open_reader($(e.currentTarget).data("book"));
				});
				$L.find(".duty-bk-del").on("click", (e) => {
					e.stopPropagation();
					const bk = $(e.currentTarget).data("book");
					frappe.confirm(__("Remove this book and everyone's reading progress in it?"), () =>
						frappe.call({ method: "duty_board.library.delete_book", args: { book: bk }, callback: () => this.refresh_library() })
					);
				});
				$L.find(".duty-bk-edit").on("click", (e) => {
					e.stopPropagation();
					const bk = $(e.currentTarget).data("book");
					const b = books.find((x) => x.name === bk) || {};
					frappe.prompt(
						[
							{ fieldname: "title", fieldtype: "Data", label: __("Title"), default: b.title, reqd: 1 },
							{ fieldname: "author", fieldtype: "Data", label: __("Author"), default: b.author || "" },
							{ fieldname: "category", fieldtype: "Data", label: __("Category"), default: b.category || "" },
							{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: b.description || "" },
						],
						(v) => frappe.call({ method: "duty_board.library.update_book", args: { book: bk, title: v.title, author: v.author || "", category: v.category || "", description: v.description || "" }, callback: () => this.refresh_library() }),
						__("Edit book"), __("Save")
					);
				});
				if (mgr) {
					$L.find(".duty-bk-up").on("click", () => {
						const f = $L.find(".duty-bk-file")[0].files[0];
						if (!f) return;
						const guess = f.name.replace(/\.(pdf|epub)$/i, "").replace(/[_\-]+/g, " ").replace(/\(z-lib[^)]*\)|z-?library|1lib\.\w+/gi, "").trim();
						this.book_matcher(guess, (meta) =>
						frappe.prompt(
							[
								{ fieldname: "title", fieldtype: "Data", label: __("Title"), default: (meta && meta.title) || guess, reqd: 1 },
								{ fieldname: "author", fieldtype: "Data", label: __("Author"), default: (meta && meta.authors) || "" },
								{ fieldname: "category", fieldtype: "Data", label: __("Category (shelf section, e.g. Leadership, ERP, Sales)"), default: (meta && meta.categories) || "" },
								{ fieldname: "description", fieldtype: "Small Text", label: __("Why the team should read it"), default: (meta && meta.description) || "" },
							],
							(v) => {
								v.cover_url = (meta && meta.thumbnail) || null;
								const fd = new FormData();
								fd.append("file", f);
								fd.append("is_private", "1");
								fetch("/api/method/upload_file", { method: "POST", headers: { "X-Frappe-CSRF-Token": frappe.csrf_token }, body: fd })
									.then((res) => res.json())
									.then((j) => {
										const url = j.message && j.message.file_url;
										if (!url) throw new Error("upload failed");
										return frappe.call({ method: "duty_board.library.convert_pdf", args: { file_url: url, title: v.title, author: v.author || null, category: v.category || null, description: v.description || null, cover_url: v.cover_url } });
									})
									.then(() => frappe.show_alert({ message: __("📚 Converting in the background — you'll be notified when it's on the shelf."), indicator: "blue" }))
									.catch(() => frappe.msgprint(__("Upload failed — try again.")));
							},
							__("New book"), __("Convert")
						));
					});
				}
			},
		});
	}

	open_reader(book) {
		frappe.call({
			method: "duty_board.library.open_book",
			args: { book: book },
			callback: (r) => {
				const m = r.message;
				if (!m) return;
				const $L = this.$library.empty();
				let cur = m.current;
				let opened_at = Date.now();
				const doneSet = new Set(m.done || []);
				$L.append(`
					<div style="display:flex;align-items:center;gap:12px;margin:4px 0 10px">
						<a class="duty-rd-back" style="cursor:pointer;font-weight:600;color:#6B7772">‹ ${__("Library")}</a>
						<b style="font-size:16px">${frappe.utils.escape_html(m.title)}</b>
						${m.author ? `<span class="text-muted" style="font-size:12.5px">${frappe.utils.escape_html(m.author)}</span>` : ""}
						<span style="margin-left:auto" class="duty-rd-stars"></span>
						<a class="duty-rd-revs" style="cursor:pointer;font-size:12.5px;color:#0E5A4A"></a>
						<span class="duty-rd-opts" style="display:inline-flex;gap:2px;background:#f0efe9;border-radius:8px;padding:2px;margin-left:6px">
							<a class="duty-rd-opt" data-o="toc" title="${__("Show/hide contents")}">☰</a>
							<a class="duty-rd-opt" data-o="two" title="${__("Two-page spread")}">▥</a>
							<a class="duty-rd-opt" data-o="just" title="${__("Justify text")}">≣</a>
							<a class="duty-rd-fs" data-d="-1" title="${__("Smaller text")}" style="padding:3px 8px;cursor:pointer;text-decoration:none;color:#6B7772">A−</a>
							<a class="duty-rd-fs" data-d="1" title="${__("Larger text")}" style="padding:3px 8px;cursor:pointer;text-decoration:none;color:#182420;font-weight:700">A＋</a>
						</span>
					</div>
					<div class="duty-rd-revpanel" style="display:none;border:1px solid #E8E5DD;border-radius:12px;padding:12px 14px;margin-bottom:10px"></div>
					<div style="display:flex;gap:20px">
						<div class="duty-rd-toc" style="width:250px;flex:none;position:sticky;top:60px;align-self:flex-start;max-height:calc(100vh - 140px);overflow-y:auto;border-right:1px solid #E8E5DD;padding-right:10px"></div>
						<div class="duty-rd-col" style="flex:1;min-width:0">
							<div class="duty-rd-scroller"><div class="duty-rd-body" style="font-size:16px;line-height:1.8;color:#182420"></div></div>
							<div class="duty-rd-nav" style="display:flex;gap:8px;padding:16px 0 40px;border-top:1px solid #E8E5DD;margin-top:18px;align-items:center">
								<button class="btn btn-sm btn-default duty-rd-prev">‹ ${__("Previous")}</button>
								<span class="duty-rd-pgbtns" style="display:none;margin:0 auto">
									<button class="btn btn-sm btn-default duty-rd-pgprev">‹ ${__("Page")}</button>
									<button class="btn btn-sm btn-default duty-rd-pgnext">${__("Page")} ›</button>
								</span>
								<button class="btn btn-sm btn-primary duty-rd-next" style="margin-left:auto">${__("Finish chapter & continue")} ›</button>
							</div>
						</div>
					</div>`);
				const $toc = $L.find(".duty-rd-toc");
				const $bd = $L.find(".duty-rd-body");
				const $sc = $L.find(".duty-rd-scroller");
				const chIdx = (name) => m.chapters.findIndex((c) => c.name === name);
				const prefs = Object.assign({ toc: 1, two: 0, just: 1, fs: 16 }, JSON.parse(localStorage.getItem("duty_rd_prefs") || "{}"));
				const GAP = 56;
				const applyPrefs = () => {
					localStorage.setItem("duty_rd_prefs", JSON.stringify(prefs));
					$L.find(".duty-rd-opt").each((_, el) => {
						const on = prefs[$(el).data("o")];
						$(el).css({ padding: "3px 9px", "border-radius": "6px", cursor: "pointer", "text-decoration": "none",
							background: on ? "#fff" : "transparent", color: on ? "#182420" : "#6B7772",
							"box-shadow": on ? "0 1px 2px rgba(0,0,0,.08)" : "none", "font-weight": on ? "700" : "400" });
					});
					$toc.toggle(!!prefs.toc);
					$bd.css({ "font-size": prefs.fs + "px", "line-height": "1.8",
						"text-align": prefs.just ? "justify" : "left", hyphens: prefs.just ? "auto" : "none" });
					$L.find(".duty-rd-pgbtns").toggle(!!prefs.two);
					if (prefs.two) {
						$sc.css({ height: "calc(100vh - 250px)", "overflow-x": "auto", "overflow-y": "hidden" });
						$bd.css({ "max-width": "none" });
						requestAnimationFrame(() => {
							const w = $sc[0].clientWidth;
							const colw = Math.floor((w - GAP) / 2);
							$bd.css({ height: "100%", "column-width": colw + "px", "column-gap": GAP + "px", "column-fill": "auto" });
						});
					} else {
						$sc.css({ height: "", "overflow-x": "", "overflow-y": "" });
						$bd.css({ "max-width": "840px", height: "", "column-width": "", "column-gap": "", "column-fill": "" });
						$L.find(".duty-rd-nav").css("max-width", "840px");
					}
				};
				const pageBy = (dir) => {
					const el = $sc[0];
					el.scrollBy({ left: dir * (el.clientWidth + GAP), behavior: "smooth" });
				};
				const renderToc = () => {
					$toc.empty();
					m.chapters.forEach((c) => {
						$(`<a style="display:block;padding:6px 8px;border-radius:8px;margin:1px 0;cursor:pointer;font-size:12.5px;${c.name === cur ? "background:#eef2f0;font-weight:700" : ""};color:#182420;text-decoration:none">${doneSet.has(c.name) ? "✅ " : ""}${c.idx_no}. ${frappe.utils.escape_html(c.title)}</a>`)
							.appendTo($toc)
							.on("click", () => go(c.name, 0));
					});
				};
				const loadReviews = () =>
					frappe.call({
						method: "duty_board.library.book_reviews",
						args: { book: book },
						callback: (rr) => {
							const rv = rr.message || { rows: [], avg: 0, n: 0 };
							const mine = rv.rows.find((z) => z.mine) || {};
							const stars = mine.stars || 0;
							$L.find(".duty-rd-stars").html(
								[1, 2, 3, 4, 5].map((i) => `<a data-s="${i}" style="cursor:pointer;font-size:17px;color:${i <= stars ? "#A96F1A" : "#D8D4C8"};text-decoration:none">★</a>`).join("")
							);
							$L.find(".duty-rd-stars a").on("click", (e) => {
								const s = $(e.currentTarget).data("s");
								frappe.prompt(
									{ fieldname: "review", fieldtype: "Small Text", label: __("A line for your colleagues (optional)"), default: mine.review || "" },
									(v) => frappe.call({ method: "duty_board.library.rate_book", args: { book: book, stars: s, review: v.review || "" }, callback: loadReviews }),
									__("Rate “{0}” — {1}★", [m.title, s]), __("Save")
								);
							});
							$L.find(".duty-rd-revs").text(rv.n ? `💬 ${rv.n} ${__("review(s)")} · ${rv.avg}★` : __("be the first to review"));
							$L.find(".duty-rd-revpanel").html(
								rv.rows.filter((z) => z.stars || z.review).map((z) => `
								<div style="padding:7px 0;border-bottom:1px solid #F0EEE8;font-size:13px">
									<b>${frappe.utils.escape_html(z.who)}</b>
									<span style="color:#A96F1A">${"★".repeat(z.stars || 0)}</span>
									<span class="text-muted" style="font-size:11px;float:right">${z.when}</span>
									${z.review ? `<div style="margin-top:2px">${frappe.utils.escape_html(z.review)}</div>` : ""}
								</div>`).join("") || `<div class="text-muted">${__("No reviews yet.")}</div>`
							);
						},
					});
				$L.find(".duty-rd-revs").on("click", () => $L.find(".duty-rd-revpanel").slideToggle(120));
				const save = (donech) => {
					let pct;
					if (prefs.two) {
						const el = $sc[0];
						pct = el.scrollWidth > el.clientWidth ? Math.round((el.scrollLeft / (el.scrollWidth - el.clientWidth)) * 100) : 100;
					} else {
						pct = document.documentElement.scrollHeight > window.innerHeight
							? Math.round((window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100)
							: 100;
					}
					const mins = Math.round((Date.now() - opened_at) / 60000);
					opened_at = Date.now();
					frappe.call({ method: "duty_board.library.mark", args: { book: book, chapter: cur, scroll_pct: pct, minutes: mins, done: donech || null }, callback: () => {} });
				};
				let scrollT = null;
				this._rd_scroll = () => {
					clearTimeout(scrollT);
					scrollT = setTimeout(() => { if (this.face === "library" && this._reading === book) save(null); }, 1500);
				};
				$(window).off("scroll.dutyrd").on("scroll.dutyrd", this._rd_scroll);
				this._reading = book;
				const go = (name, scrollPct) => {
					frappe.call({
						method: "duty_board.library.chapter",
						args: { name: name },
						callback: (rr) => {
							cur = name;
							$bd.html(rr.message.content || `<p class="text-muted">${__("Empty chapter.")}</p>`);
							renderToc();
							applyPrefs();
							requestAnimationFrame(() => {
								if (prefs.two) {
									const el = $sc[0];
									el.scrollLeft = scrollPct ? ((el.scrollWidth - el.clientWidth) * scrollPct) / 100 : 0;
								} else {
									const h = document.documentElement.scrollHeight - window.innerHeight;
									window.scrollTo(0, scrollPct ? (h * scrollPct) / 100 : 0);
								}
							});
							save(null);
						},
					});
				};
				$L.find(".duty-rd-back").on("click", () => { save(null); this._reading = null; $(document).off("keydown.dutyrd"); this.refresh_library(); });
				$L.find(".duty-rd-opt").on("click", (e) => {
					const o = $(e.currentTarget).data("o");
					prefs[o] = prefs[o] ? 0 : 1;
					applyPrefs();
				});
				$L.find(".duty-rd-fs").on("click", (e) => {
					prefs.fs = Math.min(22, Math.max(13, (prefs.fs || 16) + parseInt($(e.currentTarget).data("d"), 10)));
					applyPrefs();
				});
				$L.find(".duty-rd-pgprev").on("click", () => pageBy(-1));
				$L.find(".duty-rd-pgnext").on("click", () => pageBy(1));
				$(document).off("keydown.dutyrd").on("keydown.dutyrd", (e) => {
					if (this.face !== "library" || !this._reading || !prefs.two) return;
					if (e.key === "ArrowRight") pageBy(1);
					if (e.key === "ArrowLeft") pageBy(-1);
				});
				$L.find(".duty-rd-prev").on("click", () => { const i = chIdx(cur); if (i > 0) go(m.chapters[i - 1].name, 0); });
				$L.find(".duty-rd-next").on("click", () => {
					doneSet.add(cur);
					save(cur);
					const i = chIdx(cur);
					if (i < m.chapters.length - 1) go(m.chapters[i + 1].name, 0);
					else { renderToc(); frappe.show_alert({ message: __("📚 Book finished — rate it for the team!"), indicator: "green" }); }
				});
				$bd.html(m.content || "");
				renderToc();
				loadReviews();
				applyPrefs();
				$sc.on("scroll", () => { if (prefs.two) this._rd_scroll(); });
				$(window).off("resize.dutyrd").on("resize.dutyrd", () => { if (this._reading) applyPrefs(); });
				requestAnimationFrame(() => {
					if (prefs.two) {
						const el = $sc[0];
						el.scrollLeft = m.scroll_pct ? ((el.scrollWidth - el.clientWidth) * m.scroll_pct) / 100 : 0;
					} else {
						const h = document.documentElement.scrollHeight - window.innerHeight;
						window.scrollTo(0, m.scroll_pct ? (h * m.scroll_pct) / 100 : 0);
					}
				});
			},
		});
	}

	team_training_dialog() {
		frappe.call({
			method: "duty_board.client_room.training_team_overview",
			callback: (r) => {
				const m = r.message || { people: [] };
				const d = new frappe.ui.Dialog({ title: __("🎓 Team training & certification"), size: "extra-large" });
				$(d.body).html(
					(m.people || []).map((p) => `
					<div style="border:1px solid #E8E5DD;border-radius:12px;padding:11px 14px;margin-bottom:10px">
						<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
							<b style="font-size:14px">${frappe.utils.escape_html(p.name)}</b>
							<span style="font-size:11.5px;font-weight:700;border-radius:99px;padding:3px 10px;background:${p.completed === p.assigned ? "#E4EEEA" : "#FBF3E4"};color:${p.completed === p.assigned ? "#0E5A4A" : "#A96F1A"}">${p.completed}/${p.assigned} ${__("courses complete")}</span>
							${(p.certificates || []).map((c) => `<span title="${frappe.utils.escape_html(c.title)} · ${c.on}" style="font-size:11.5px;background:#EFEDE6;border-radius:99px;padding:3px 10px">🎓 ${frappe.utils.escape_html(c.product || c.title)}</span>`).join("")}
							<span class="text-muted" style="font-size:11.5px;margin-left:auto">${p.last_active ? __("last active") + " " + p.last_active : __("no activity yet")}</span>
						</div>
						<div style="margin-top:7px">
							${(p.rows || []).map((z) => `
							<div style="display:flex;gap:9px;align-items:center;padding:4px 0;border-bottom:1px solid #F5F3EE;font-size:12.5px">
								<span>${z.status === "Completed" ? "✅" : z.lessons_done ? "▶" : "○"}</span>
								<span style="flex:1;min-width:0">${frappe.utils.escape_html(z.title)}${z.product ? ` <span class="text-muted" style="font-size:11px">· ${frappe.utils.escape_html(z.product)}</span>` : ""}</span>
								<span class="text-muted" style="font-size:11.5px;white-space:nowrap">${z.lessons_done}/${z.lessons_total} ${__("lessons")}</span>
								${z.quiz_attempts ? `<span title="${z.quiz_attempts} ${__("attempt(s) in total")}" style="font-size:11.5px;white-space:nowrap;font-weight:700;color:${z.quiz_passed ? "#0E5A4A" : "#A96F1A"}">${__("quiz")} ${z.quiz_best}% ${z.quiz_passed ? `✓ ${z.quiz_to_pass === 1 ? __("first try") : __("passed on attempt {0}", [z.quiz_to_pass])}` : `${__("not passed")} · ${z.quiz_attempts}× ${__("so far")}`}</span>` : ""}
								${z.completed_on ? `<span class="text-muted" style="font-size:11px;white-space:nowrap">${z.completed_on}</span>` : ""}
							</div>`).join("")}
						</div>
					</div>`).join("") || `<div class="text-muted">${__("No staff training assignments yet — assign tracks from the Me face (My training → Assign to a colleague).")}</div>`
				);
				d.show();
			},
		});
	}

	timeline_dialog(x) {
		frappe.call({
			method: "duty_board.timeline.timeline",
			args: { room: x.name },
			callback: (r) => {
				const t = r.message || { events: [], summary: {} };
				const d = new frappe.ui.Dialog({ title: __("📜 {0} — Delivery timeline", [x.customer]), size: "extra-large" });
				const CHIP = { client: ["CLIENT", "#A96F1A", "#FBF3E4"], xlevel: ["XLEVEL", "#0E5A4A", "#E4EEEA"], info: ["", "", ""] };
				$(d.body).html(`
					<div style="border:1px solid #E8E5DD;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13px">
						<b>${__("Attributed waiting time")}</b> — ${__("client")}: <b style="color:#A96F1A">${t.summary.client_days || 0} ${__("day(s)")}</b> ·
						Xlevel: <b style="color:#0E5A4A">${t.summary.xlevel_days || 0} ${__("day(s)")}</b>
						<div class="text-muted" style="font-size:11.5px;margin-top:3px">${__("Client days = dependency lateness + CR approval waits · Xlevel days = acceptance-defect open time. Every line is a recorded system event.")}</div>
					</div>
					<div style="max-height:55vh;overflow-y:auto">
						${(t.events || []).map((e) => {
							const c = CHIP[e.who] || CHIP.info;
							return `<div style="display:flex;gap:10px;align-items:baseline;padding:5px 2px;border-bottom:1px solid #F0EEE8;font-size:12.5px">
								<span class="text-muted" style="white-space:nowrap;font-size:11.5px">${e.when}</span>
								<span>${e.icon}</span>
								<span style="flex:1">${frappe.utils.escape_html(e.text)}</span>
								${c[0] ? `<span style="font-size:9px;font-weight:800;letter-spacing:1px;color:${c[1]};background:${c[2]};border-radius:99px;padding:2px 8px">${c[0]}</span>` : ""}
							</div>`;
						}).join("") || `<div class="text-muted">${__("Nothing recorded yet.")}</div>`}
					</div>
					<button class="btn btn-sm btn-default" data-pdf style="margin-top:10px">📄 ${__("Export as PDF")}</button>`);
				$(d.body).find("[data-pdf]").on("click", (e) => {
					$(e.currentTarget).prop("disabled", true).text(__("Generating…"));
					frappe.call({
						method: "duty_board.timeline.timeline_pdf",
						args: { room: x.name },
						callback: (rr) => {
							if (rr.message && rr.message.file_url) window.open(rr.message.file_url, "_blank");
							$(e.currentTarget).prop("disabled", false).text("📄 " + __("Export as PDF"));
						},
					});
				});
				d.show();
			},
		});
	}

	uat_dialog(x) {
		frappe.call({
			method: "duty_board.uat.uat_state",
			args: { room: x.name },
			callback: (r) => {
				const m = r.message || {};
				const rows = m.rows || [];
				const p = m.progress || {};
				const d = new frappe.ui.Dialog({ title: __("🧪 {0} — Acceptance testing", [x.customer]), size: "extra-large" });
				const CH = { "Passed": "✅", "Failed": "❌", "Blocked": "⛔", "Blocked by Issue": "🔧", "Waived": "⚪", "Awaiting Client": "🕐" };
				const reload = () => { d.hide(); this.uat_dialog(x); };
				const call = (method, args) => frappe.call({ method: "duty_board.uat." + method, args: args, callback: reload });
				const secs = {};
				rows.forEach((z) => (secs[z.section || "General"] = secs[z.section || "General"] || []).push(z));
				$(d.body).html(`
					${m.uat_due && !m.signoff ? `<div class="text-muted" style="font-size:12px;margin-bottom:6px">🗓 ${__("Window ends")} ${m.uat_due}</div>` : ""}
					${m.signoff ? `<div style="background:#E4EEEA;border-radius:10px;padding:9px 12px;font-size:13px;margin-bottom:10px">✍ <b>${__("Signed off")}</b> ${__("by")} ${frappe.utils.escape_html(m.signoff.signed_full)} · ${m.signoff.signed_at} · ${m.signoff.passed}/${m.signoff.total} ${__("passed")}${m.signoff.exceptions ? `<br><span class="text-muted" style="font-size:12px">${__("Exceptions")}: ${frappe.utils.escape_html(m.signoff.exceptions)}</span>` : ""}</div>` : ""}
					${rows.length ? `<div style="font-size:12.5px;margin-bottom:8px"><b>${p.passed || 0}</b>/${p.total || 0} ${__("passed")}${p.failed ? ` · <b style="color:#b91c1c">${p.failed} ${__("failed")}</b>` : ""}${p.blocked ? ` · ${p.blocked} ${__("blocked")}` : ""}${p.waived ? ` · ${p.waived} ${__("waived")}` : ""}${p.awaiting ? ` · ${p.awaiting} ${__("awaiting client")}` : ""}</div>` : ""}
					${!rows.length ? `
						<p class="text-muted">${__("No acceptance cases yet — pick which template bank(s) to seed for this engagement.")} ${(m.templates || []).length ? "" : __("None exist yet — a manager creates them under Duty UAT Template.")}</p>
						<button class="btn btn-sm btn-primary" data-seed ${(m.templates || []).length ? "" : "disabled"}>🧪 ${__("Seed UAT…")}</button>`
					: Object.keys(secs).map((s) => `
						<div style="font-size:11px;font-weight:800;letter-spacing:1px;margin:10px 0 4px;color:#6B7772;text-transform:uppercase">${frappe.utils.escape_html(s)}</div>
						${secs[s].map((z) => `
						<div style="border:1px solid #E8E5DD;border-radius:10px;padding:8px 11px;margin-bottom:6px;display:flex;gap:9px;align-items:center;flex-wrap:wrap">
							<span>${CH[z.status] || ""}</span>
							<b style="font-size:13px;flex:1;min-width:180px">${z.code ? `<span class="text-muted" style="font-weight:600;font-size:11px">${frappe.utils.escape_html(z.code)}</span> ` : ""}${frappe.utils.escape_html(z.title)}</b>
							<span class="text-muted" style="font-size:11.5px">${z.attempts.length ? z.attempts.length + "× " + __("tested") : ""}</span>
							<span class="text-muted" style="font-size:11.5px;font-weight:700">${__(z.status)}</span>
							${z.issue ? `<a style="font-size:11.5px" onclick="frappe.set_route('Form','Duty Issue','${z.issue}')">🔧 ${z.issue}</a>` : ""}
							<span style="white-space:nowrap">
								${z.status !== "Waived" && !m.signoff ? `<button class="btn btn-xs btn-default" data-rec="${z.name}" title="${__("Record a result on the client's behalf")}">✍ ${__("record")}</button>` : ""}
								<button class="btn btn-xs btn-default" data-edit="${z.name}">✎</button>
								${m.manager && z.status !== "Waived" && !m.signoff ? `<button class="btn btn-xs btn-default" data-waive="${z.name}">${__("waive")}</button>` : ""}
								<button class="btn btn-xs btn-default" data-del="${z.name}" style="color:#B0443C">×</button>
							</span>
						</div>`).join("")}`).join("") + `
						<button class="btn btn-sm btn-primary" data-addcase style="margin-top:6px">＋ ${__("Add a case for this engagement")}</button>
						${!m.signoff ? `<button class="btn btn-sm btn-default" data-seed style="margin-top:6px">🧪 ${__("Seed another template…")}</button>` : ""}
						${m.manager && Object.keys(rows.reduce((a, z) => { if (z.template) a[z.template] = 1; return a; }, {})).length && !m.signoff ? `<button class="btn btn-sm btn-default" data-unseed style="margin-top:6px;color:#B0443C">${__("Unseed a template…")}</button>` : ""}`}
				`);
				const seededFrom = {};
				rows.forEach((z) => { if (z.template) seededFrom[z.template] = 1; });
				const roomProds = (m.room_products || "").toLowerCase();
				$(d.body).find("[data-seed]").on("click", () =>
					frappe.prompt(
						[{
							fieldname: "templates", fieldtype: "MultiCheck", label: __("Template banks to seed"), columns: 2,
							options: (m.templates || []).map((t) => ({
								label: seededFrom[t] ? t + " (" + __("already seeded") + ")" : t,
								value: t,
								checked: !seededFrom[t] && roomProds.indexOf(t.toLowerCase()) >= 0 ? 1 : 0,
							})),
						},
						{ fieldname: "due", fieldtype: "Date", label: __("Testing window ends (optional — drives client reminders)") }],
						(v) => {
							const chosen = v.templates || [];
							if (!chosen.length) return;
							call("uat_seed", { room: x.name, templates: chosen.join(","), due: v.due || null });
						},
						__("Seed acceptance tests"), __("Seed")
					)
				);
				$(d.body).find("[data-unseed]").on("click", () =>
					frappe.prompt(
						{ fieldname: "template", fieldtype: "Select", label: __("Remove untested cases seeded from"), options: Object.keys(seededFrom), reqd: 1 },
						(v) => call("uat_unseed", { room: x.name, template: v.template }),
						__("Unseed template"), __("Remove")
					)
				);
				$(d.body).find("[data-addcase]").on("click", () => frappe.prompt(
					[
						{ fieldname: "section", fieldtype: "Data", label: __("Section"), default: "General" },
						{ fieldname: "title", fieldtype: "Data", label: __("Scenario"), reqd: 1 },
						{ fieldname: "steps", fieldtype: "Small Text", label: __("Steps") },
						{ fieldname: "expected", fieldtype: "Small Text", label: __("Expected result") },
					],
					(v) => call("uat_case_add", { room: x.name, title: v.title, section: v.section, steps: v.steps || null, expected: v.expected || null }),
					__("New acceptance case"), __("Add")
				));
				$(d.body).find("[data-edit]").on("click", (e) => {
					const id = $(e.currentTarget).data("edit");
					const z = rows.find((q) => q.name === id) || {};
					frappe.prompt(
						[
							{ fieldname: "section", fieldtype: "Data", label: __("Section"), default: z.section },
							{ fieldname: "title", fieldtype: "Data", label: __("Scenario"), default: z.title, reqd: 1 },
							{ fieldname: "steps", fieldtype: "Small Text", label: __("Steps"), default: z.steps },
							{ fieldname: "expected", fieldtype: "Small Text", label: __("Expected result"), default: z.expected },
						],
						(v) => call("uat_case_update", { name: id, title: v.title, section: v.section, steps: v.steps || "", expected: v.expected || "" }),
						__("Edit case"), __("Save")
					);
				});
				$(d.body).find("[data-rec]").on("click", (e) => {
					const id = $(e.currentTarget).data("rec");
					frappe.prompt(
						[
							{ fieldname: "result", fieldtype: "Select", label: __("Result"), options: ["Pass", "Fail", "Blocked"], reqd: 1 },
							{ fieldname: "observed", fieldtype: "Small Text", label: __("What happened (required for Fail/Blocked)") },
						],
						(v) => call("uat_record", { name: id, result: v.result, observed: v.observed || null }),
						__("Record on client's behalf"), __("Record")
					);
				});
				$(d.body).find("[data-waive]").on("click", (e) => frappe.prompt(
					{ fieldname: "reason", fieldtype: "Data", label: __("Waived because"), reqd: 1 },
					(v) => call("uat_waive", { name: $(e.currentTarget).data("waive"), reason: v.reason }),
					__("Waive case"), __("Waive")
				));
				$(d.body).find("[data-del]").on("click", (e) => frappe.confirm(__("Delete this case (and its attempt history)?"), () =>
					call("uat_case_delete", { name: $(e.currentTarget).data("del") })
				));
				d.show();
			},
		});
	}

	deps_dialog(x) {
		frappe.call({
			method: "duty_board.commercial.deps_list",
			args: { room: x.name },
			callback: (r) => {
				const rows = r.message || [];
				const d = new frappe.ui.Dialog({ title: __("📋 Awaiting from {0}", [x.customer]), size: "large" });
				const badge = (s, o) => s === "Received" ? "✅" : s === "Waived" ? "⚪" : s === "Provided" ? "📨" : o ? "🔴" : "🕐";
				$(d.body).html(`
					${rows.length ? `<table class="table table-sm" style="font-size:12px"><tr><th></th><th>${__("Item")}</th><th>${__("Due")}</th><th>${__("Age")}</th><th>${__("Blocks")}</th><th></th></tr>
					${rows.map((z) => `<tr style="${z.overdue ? "background:#fef2f2" : ""}">
						<td>${badge(z.status, z.overdue)}</td>
						<td><b>${frappe.utils.escape_html(z.title)}</b><br><span class="text-muted">${frappe.utils.escape_html(z.category || "")}${z.provided_note ? " · 💬 " + frappe.utils.escape_html(z.provided_note) : ""}</span></td>
						<td>${z.due_date || "—"}${z.overdue ? `<br><b style="color:#b91c1c">${z.days_late}d ${__("late")}</b>` : ""}</td>
						<td>${z.age_days}d${z.remind_count ? `<br>🔔×${z.remind_count}` : ""}</td>
						<td style="max-width:140px">${frappe.utils.escape_html(z.blocks || "")}</td>
						<td style="white-space:nowrap">
							${z.status === "Awaiting" || z.status === "Provided" ? `<button class="btn btn-xs btn-success" data-recv="${z.name}">✓ ${__("received")}</button> <button class="btn btn-xs btn-default" data-rem="${z.name}">🔔</button>` : ""}
							${z.status === "Provided" ? `<button class="btn btn-xs btn-default" data-back="${z.name}" title="${__("not usable — reopen")}">↩</button>` : ""}
							${z.status === "Awaiting" ? `<button class="btn btn-xs btn-default" data-waive="${z.name}">${__("waive")}</button>` : ""}
						</td></tr>`).join("")}</table>` : `<p class="text-muted">${__("Nothing awaited from this client.")}</p>`}
					<button class="btn btn-sm btn-primary" data-adddep>＋ ${__("New dependency")}</button>
				`);
				const reload = () => { d.hide(); this.deps_dialog(x); };
				$(d.body).find("[data-recv]").on("click", (e) => frappe.call({ method: "duty_board.commercial.dep_receive", args: { name: $(e.currentTarget).data("recv") }, callback: reload }));
				$(d.body).find("[data-rem]").on("click", (e) => frappe.call({ method: "duty_board.commercial.dep_remind", args: { name: $(e.currentTarget).data("rem") }, callback: () => frappe.show_alert({ message: __("🔔 Reminder posted to the room"), indicator: "blue" }) }));
				$(d.body).find("[data-back]").on("click", (e) => frappe.prompt({ fieldname: "note", fieldtype: "Data", label: __("Why isn't it usable?") }, (v) => frappe.call({ method: "duty_board.commercial.dep_reopen", args: { name: $(e.currentTarget).data("back"), note: v.note }, callback: reload }), __("Reopen"), __("Reopen")));
				$(d.body).find("[data-waive]").on("click", (e) => frappe.prompt({ fieldname: "reason", fieldtype: "Data", label: __("Reason") }, (v) => frappe.call({ method: "duty_board.commercial.dep_waive", args: { name: $(e.currentTarget).data("waive"), reason: v.reason }, callback: reload }), __("Waive"), __("Waive")));
				$(d.body).find("[data-adddep]").on("click", () => frappe.prompt(
					[
						{ fieldname: "title", fieldtype: "Data", label: __("What do we need?"), reqd: 1 },
						{ fieldname: "category", fieldtype: "Select", label: __("Category"), options: ["Data / Template", "Opening Balances", "Master Data", "Approval / Sign-off", "Credentials / Access", "Process Decision", "Test Results / UAT", "Training Attendance", "Document", "Payment", "Named Staff", "Other"], default: "Other" },
						{ fieldname: "detail", fieldtype: "Small Text", label: __("Detail / format expected") },
						{ fieldname: "due_date", fieldtype: "Date", label: __("Due") },
						{ fieldname: "blocks", fieldtype: "Data", label: __("What this blocks (shown to management)") },
					],
					(v) => frappe.call({ method: "duty_board.commercial.dep_add", args: { room: x.name, title: v.title, category: v.category, detail: v.detail || null, due_date: v.due_date || null, blocks: v.blocks || null }, callback: reload }),
					__("New dependency"), __("Request")
				));
				d.show();
			},
		});
	}

	academy_dialog(x) {
		const d = new frappe.ui.Dialog({ title: `🎓 ${x.customer} — ${__("Training Academy")}`, size: "large" });
		const load = () =>
			frappe.call({
				method: "duty_board.client_room.room_training",
				args: { name: x.name },
				callback: (r) =>
					frappe.call({
						method: "duty_board.client_room.training_modules",
						callback: (mr) => render(r.message || [], mr.message || []),
					}),
			});
		const render = (rows, mods) => {
			const members = (x.members || []).filter((m) => m.user);
			const by_trainee = {};
			rows.forEach((r) => {
				(by_trainee[r.trainee_name] = by_trainee[r.trainee_name] || []).push(r);
			});
			$(d.body).html(`
				<div class="duty-acad-row" style="background:var(--bg-light-gray,#F4F7F6);border-radius:8px;padding:7px 10px">
					🛒 <b>${__("Products")}</b>
					<span class="text-muted">${x.products ? frappe.utils.escape_html(x.products) : __("none — members inherit no certification tracks")}</span>
					<a class="duty-acad-prods" style="margin-left:auto;cursor:pointer">✎ ${__("Edit")}</a>
				</div>
				${Object.keys(by_trainee)
					.map(
						(t) => `
					<div class="duty-lead-section">👤 ${frappe.utils.escape_html(t)}</div>
					${by_trainee[t]
						.map(
							(r) => `
						<div class="duty-acad-row">
							${r.status === "Completed" ? "🏅" : "📖"} <b>${frappe.utils.escape_html(r.module_title)}</b>
							${r.product ? `<span class="text-muted">${frappe.utils.escape_html(r.product)}</span>` : ""}
							${r.status === "Completed"
								? `<span class="duty-acad-done">✓ ${__("certified")} ${r.completed_on}</span>`
								: `<button type="button" class="btn btn-xs btn-primary duty-acad-complete" data-id="${r.name}">🏅 ${__("Mark completed — issue certificate")}</button>`}
						</div>`
						)
						.join("")}`
					)
					.join("") || `<div class="text-muted">${__("No training assigned in this room yet.")}</div>`}
				<div class="duty-lead-section">＋ ${__("Assign training")}</div>
				<div class="duty-cr-addmem" style="flex-wrap:wrap">
					<select class="form-control input-sm duty-acad-user" style="flex:1">
						${members.map((m) => `<option value="${frappe.utils.escape_html(m.user)}">${frappe.utils.escape_html(m.full_name || m.user)}</option>`).join("")}
					</select>
					<select class="form-control input-sm duty-acad-mod" style="flex:1">
						${mods.map((m) => `<option value="${m.name}">${frappe.utils.escape_html((m.product ? m.product + " · " : "") + m.title)}</option>`).join("")}
					</select>
					<button type="button" class="btn btn-sm btn-primary duty-acad-assign">＋</button>
					<a class="duty-acad-newmod" style="cursor:pointer;font-size:var(--text-xs);align-self:center">＋ ${__("new module")}</a>
				</div>
				<div class="duty-cr-addmem duty-acad-trackrow" style="flex-wrap:wrap;margin-top:6px;display:none">
					<select class="form-control input-sm duty-acad-track" style="flex:1"></select>
					<button type="button" class="btn btn-sm btn-primary duty-acad-assigntrack">🎓 ${__("Assign whole track")}</button>
				</div>
			`);
			frappe.call({
				method: "duty_board.client_room.room_tracks_for_assign",
				args: { name: x.name },
				callback: (tr) => {
					const tracks = tr.message || [];
					if (!tracks.length) return;
					const $row = $(d.body).find(".duty-acad-trackrow");
					$row.find(".duty-acad-track").html(
						tracks
							.map(
								(t) =>
									`<option value="${t.name}">🎓 ${frappe.utils.escape_html((t.product ? t.product + " · " : "") + t.title)} (${t.module_count} ${__("courses")})</option>`
							)
							.join("")
					);
					$row.show();
					$row.find(".duty-acad-assigntrack").on("click", () =>
						frappe.call({
							method: "duty_board.client_room.training_assign_track_room",
							args: {
								name: x.name,
								track: $row.find(".duty-acad-track").val(),
								user: $(d.body).find(".duty-acad-user").val(),
							},
							callback: (rr) => {
								const m = rr.message || {};
								frappe.show_alert({
									message: __("🎓 Track assigned: {0} new, {1} already had.", [m.created || 0, m.existing || 0]),
									indicator: "green",
								});
								d.hide();
								this.academy_dialog(x);
							},
						})
					);
				},
			});
			$(d.body).find(".duty-acad-assign").on("click", () =>
				frappe.call({
					method: "duty_board.client_room.training_assign",
					args: {
						name: x.name,
						module: $(d.body).find(".duty-acad-mod").val(),
						user: $(d.body).find(".duty-acad-user").val(),
					},
					callback: () => load(),
				})
			);
			$(d.body).find(".duty-acad-complete").on("click", (e) =>
				frappe.confirm(
					__("Mark completed and issue the branded certificate to the client's shelf?"),
					() =>
						frappe.call({
							method: "duty_board.client_room.training_complete",
							args: { record: $(e.currentTarget).data("id") },
							callback: () => {
								load();
								this.load_client_room(x.name);
							},
						})
				)
			);
			$(d.body).find(".duty-acad-newmod").on("click", () =>
				frappe.prompt(
					[
						{ fieldname: "title", fieldtype: "Data", label: __("Module title"), reqd: 1 },
						{ fieldname: "product", fieldtype: "Link", options: "Duty Product", label: __("Product") },
					],
					(v) =>
						frappe.call({
							method: "duty_board.client_room.training_module_add",
							args: { title: v.title, product: v.product || "" },
							callback: () => load(),
						}),
					__("New training module"),
					__("Add")
				)
			);
		};
		$(d.body).on("click", ".duty-acad-prods", () =>
			frappe.call({
				method: "duty_board.client_room.product_options",
				callback: (pr) => {
					const opts = pr.message || [];
					if (!opts.length)
						return frappe.msgprint(
							__("No products defined yet — product names come from your certification tracks and training modules in the desk.")
						);
					const current = (x.products || "").split(",").map((s) => s.trim()).filter(Boolean);
					frappe.prompt(
						[
							{
								fieldname: "products",
								fieldtype: "MultiCheck",
								label: __("Products"),
								columns: 2,
								options: opts.map((o) => ({ label: o, value: o, checked: current.includes(o) })),
							},
						],
						(v) =>
							frappe.call({
								method: "duty_board.client_room.room_set_products",
								args: { name: x.name, products: (v.products || []).join(", ") },
								callback: (r) => {
									if (r.message) {
										x.products = r.message.products;
										this.render_client_room(r.message);
										load();
									}
								},
							}),
						__("Room products — members see and can pursue the client tracks of these products"),
						__("Save")
					);
				},
			})
		);
		load();
		d.show();
	}

	milestones_dialog(x) {
		const d = new frappe.ui.Dialog({ title: `🏁 ${x.customer} — ${__("Milestones")}`, size: "large" });
		const CHIP = {
			"Upcoming": ["⚪", "#6b7280"], "In Progress": ["🔵", "#0E7490"],
			"Awaiting Approval": ["🟠", "#b45309"], "Approved": ["✅", "#15803d"],
		};
		const render = (data) => {
			const mst = data.milestones || [];
			$(d.body).html(`
				<div class="duty-cr-mslist">
					${mst
						.map((m, i) => {
							const [icon, color] = CHIP[m.status];
							const locked = m.status === "Approved";
							return `
						<div class="duty-cr-msrow ${locked ? "locked" : ""}">
							<span style="color:${color};white-space:nowrap">${icon} <b>${frappe.utils.escape_html(m.title)}</b></span>
							${m.target_date ? `<span class="text-muted">🎯 ${m.target_date}</span>` : ""}
							${m.project && m.cards_total ? `<span class="duty-cr-msev ${m.cards_done === m.cards_total ? "ready" : ""}">📋 ${m.cards_done}/${m.cards_total} ${__("tasks")}</span>` : ""}
							${locked
								? `<span class="duty-cr-mssig">${__("Signed off by")} <b>${frappe.utils.escape_html(m.approved_full || "")}</b> · ${m.approved_at}${m.approval_note ? ` · “${frappe.utils.escape_html(m.approval_note)}”` : ""}</span>`
								: `<span class="duty-cr-msacts">
									${i > 0 ? `<a data-a="up" data-id="${m.name}">↑</a>` : ""}
									${i < mst.length - 1 ? `<a data-a="down" data-id="${m.name}">↓</a>` : ""}
									<a data-a="edit" data-id="${m.name}">✎</a>
									<a data-a="tasks" data-id="${m.name}">📋 ${__("Tasks")}</a>
									${m.status === "Upcoming" ? `<a data-a="start" data-id="${m.name}">▶ ${__("Start")}</a>` : ""}
									${m.status === "In Progress" ? `<a data-a="ask" data-id="${m.name}" class="duty-cr-msask ${m.project && m.cards_total && m.cards_done === m.cards_total ? "glow" : ""}">🏁 ${__("Request approval")}${m.project && m.cards_total && m.cards_done === m.cards_total ? " — " + __("board complete!") : ""}</a>` : ""}
									${m.status === "Awaiting Approval" ? `<b class="duty-cr-mswait">${__("client's move")}</b>` : ""}
									<a data-a="del" data-id="${m.name}" style="color:var(--red-600,#dc2626)">🗑</a>
								</span>`}
							${m.description ? `<div class="duty-cr-msdesc text-muted">${frappe.utils.escape_html(m.description)}</div>` : ""}
						</div>`;
						})
						.join("") || ""}
				</div>
				${!mst.length ? `<button type="button" class="btn btn-sm btn-primary duty-cr-msseed">🏁 ${__("Seed the Xlevel method (7 phases)")}</button>` : ""}
				<div class="duty-lead-section">＋ ${__("Add milestone")}</div>
				<div class="duty-cr-addmem" style="flex-wrap:wrap">
					<input type="text" class="form-control input-sm duty-ms-title" placeholder="${__("Title")}" style="flex:2">
					<input type="date" class="form-control input-sm duty-ms-date" style="flex:1">
					<button type="button" class="btn btn-sm btn-primary duty-ms-add">＋</button>
				</div>
				<p class="text-muted duty-attach-hint">${__("Approved phases are permanent — they are the client's formal sign-off and cannot be edited or deleted.")}</p>
			`);
			const call = (method, args) =>
				frappe.call({
					method: "duty_board.client_room." + method,
					args: args,
					callback: (r) => {
						if (r.message) {
							render(r.message);
							this.render_client_room(r.message);
						}
					},
				});
			$(d.body).find(".duty-cr-msseed").on("click", () =>
				frappe.prompt(
					[
						{
							fieldname: "plan_type",
							fieldtype: "Select",
							label: __("Project plan"),
							options: [
								{ value: "standard", label: __("Standard CloudERP.One Implementation — 7 phases + 47 standard tasks") },
								{ value: "crm", label: __("CRM on CloudERP.One Implementation — 7 phases + 35 standard tasks") },
								{ value: "", label: __("Milestones only (no tasks)") },
							],
							default: "standard",
						},
					],
					(v) => {
						if (v.plan_type && !x.project)
							frappe.show_alert({ message: __("Creating a project for this room…"), indicator: "blue" });
						call("milestones_seed", { name: x.name, plan_type: v.plan_type || null });
					},
					__("Seed the project plan — tasks arrive unassigned in To Do, due dates paced from today"),
					__("Seed")
				)
			);
			$(d.body).find(".duty-ms-add").on("click", () => {
				const t = $(d.body).find(".duty-ms-title").val().trim();
				if (!t) return;
				call("milestone_add", {
					name: x.name, title: t,
					target_date: $(d.body).find(".duty-ms-date").val() || null,
				});
			});
			$(d.body).find(".duty-cr-msacts a").on("click", (e) => {
				const a = $(e.currentTarget).data("a");
				const id = $(e.currentTarget).data("id");
				if (a === "up" || a === "down") return call("milestone_move", { id: id, direction: a });
				if (a === "start") return call("milestone_set_status", { id: id, status: "In Progress" });
				if (a === "ask")
					return frappe.confirm(
						__("Tell the client this phase is complete and request their formal sign-off?"),
						() => call("milestone_request_approval", { id: id })
					);
				if (a === "tasks") {
					const m = (x.milestones || []).find((z) => z.name === id) || {};
					frappe.call({
						method: "duty_board.client_room.milestone_task_options",
						args: { id: id },
						callback: (r) => {
							const opts = r.message || [];
							const pd = new frappe.ui.Dialog({
								title: `📋 ${frappe.utils.escape_html(m.title || "")} — ${__("tasks in this phase")}`,
							});
							$(pd.body).html(
								opts.length
									? opts
											.map(
												(o) => `
									<label style="display:flex;gap:8px;align-items:baseline;padding:5px 2px;border-bottom:1px dashed var(--border-color);font-size:var(--text-sm)">
										<input type="checkbox" value="${o.name}" ${o.checked ? "checked" : ""}>
										<b>${frappe.utils.escape_html(o.title)}</b>
										<span class="text-muted">${frappe.utils.escape_html(o.project_title)} · ${o.column}</span>
										${o.elsewhere ? `<span class="duty-lead-chip">${__("in another phase")}</span>` : ""}
									</label>`
											)
											.join("") +
											`<p class="text-muted duty-attach-hint">${__("Ticked tasks appear under this phase on the client's plan — title and status become client-visible.")}</p>
											<button type="button" class="btn btn-sm btn-primary duty-ms-tsave">${__("Save")}</button>`
									: `<div class="text-muted">${__("No project tasks exist for this customer yet.")}</div>`
							);
							$(pd.body).find(".duty-ms-tsave").on("click", () => {
								const picked = $(pd.body)
									.find("input:checked")
									.map((i, el) => el.value)
									.get();
								frappe.call({
									method: "duty_board.client_room.milestone_set_tasks",
									args: { id: id, tasks: JSON.stringify(picked) },
									callback: (rr) => {
										pd.hide();
										if (rr.message) {
											render(rr.message);
											this.render_client_room(rr.message);
										}
									},
								});
							});
							pd.show();
						},
					});
					return;
				}
				if (a === "del")
					return frappe.confirm(__("Delete this milestone?"), () =>
						call("milestone_delete", { id: id })
					);
				if (a === "edit") {
					const m = (x.milestones || []).find((z) => z.name === id) || {};
					frappe.prompt(
						[
							{ fieldname: "title", fieldtype: "Data", label: __("Title"), default: m.title, reqd: 1 },
							{ fieldname: "description", fieldtype: "Small Text", label: __("Description (client-visible)"), default: m.description },
							{ fieldname: "target_date", fieldtype: "Date", label: __("Target date"), default: m.target_date },
						],
						(v) =>
							call("milestone_update", {
								id: id, title: v.title,
								description: v.description || "",
								target_date: v.target_date || "",
							}),
						__("Edit milestone"),
						__("Save")
					);
				}
			});
		};
		render(x);
		d.show();
	}

	chreqs_dialog(x) {
		if (!document.getElementById("xcr-css")) {
			const f = document.createElement("link");
			f.rel = "stylesheet";
			f.href = "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&display=swap";
			document.head.appendChild(f);
			const s = document.createElement("style");
			s.id = "xcr-css";
			s.textContent = `
			.xcr{--ink:#182420;--mut:#6B7772;--fnt:#96A09B;--ln:#E8E5DD;--soft:#EFEDE6;--brand:#0E5A4A;--bsoft:#E4EEEA;--amber:#A96F1A;--asoft:#FBF3E4;--red:#B0443C;--good:#2E7D5B;font-size:13.5px;color:var(--ink)}
			.xcr-sum{font-size:12px;color:var(--mut);margin:0 2px 12px}
			.xcr-row{display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid var(--ln);border-radius:12px;margin-bottom:8px;cursor:pointer;background:#fff;transition:box-shadow .1s}
			.xcr-row:hover{box-shadow:0 2px 10px -4px rgba(24,36,32,.18)}
			.xcr-dot{width:10px;height:10px;border-radius:50%;flex:none}
			.xcr-row .t{font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
			.xcr-row .s{font-size:12px;color:var(--fnt);margin-left:auto;white-space:nowrap;display:flex;gap:10px;align-items:center}
			.xcr-chip{font-size:11px;font-weight:700;letter-spacing:.04em;border-radius:99px;padding:3px 10px;background:var(--soft);color:var(--mut);white-space:nowrap}
			.xcr-chip.amber{background:var(--asoft);color:var(--amber)}
			.xcr-chip.green{background:var(--bsoft);color:var(--brand)}
			.xcr-chip.red{background:#FBEDEB;color:var(--red)}
			.xcr-amt{font-family:'Fraunces',serif;font-weight:600;font-size:14px;color:var(--ink)}
			.xcr-back{font-size:12.5px;font-weight:600;color:var(--mut);cursor:pointer;display:inline-block;margin-bottom:10px}
			.xcr-back:hover{color:var(--ink)}
			.xcr-h{font-family:'Fraunces',serif;font-weight:600;font-size:20px;letter-spacing:-.01em;margin:0 0 10px}
			.xcr-steps{display:flex;gap:0;margin:14px 0 16px}
			.xcr-step{flex:1;text-align:center;font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--fnt);position:relative;padding-top:14px}
			.xcr-step::before{content:"";position:absolute;top:4px;left:50%;transform:translateX(-50%);width:9px;height:9px;border-radius:50%;background:var(--ln)}
			.xcr-step::after{content:"";position:absolute;top:8px;left:calc(50% + 8px);right:calc(-50% + 8px);height:2px;background:var(--ln)}
			.xcr-step:last-child::after{display:none}
			.xcr-step.on{color:var(--brand)}.xcr-step.on::before{background:var(--brand)}
			.xcr-step.now{color:var(--ink)}.xcr-step.now::before{background:var(--brand);box-shadow:0 0 0 3px var(--bsoft)}
			.xcr-step.bad{color:var(--red)}.xcr-step.bad::before{background:var(--red)}
			.xcr-note{border-radius:10px;padding:9px 12px;font-size:12.5px;margin-bottom:12px}
			.xcr-note.amber{background:var(--asoft);color:var(--amber)}
			.xcr-note.green{background:var(--bsoft);color:var(--brand)}
			.xcr-f{display:grid;grid-template-columns:110px 1fr;gap:7px 14px;margin:12px 0}
			.xcr-f dt{font-size:10.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--fnt);padding-top:2px}
			.xcr-f dd{margin:0;font-size:13px;color:var(--ink);white-space:pre-wrap}
			.xcr-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px solid var(--ln)}
			.xcr-acts button{border:0;border-radius:9px;padding:7px 14px;font-size:12.5px;font-weight:600;cursor:pointer;background:var(--soft);color:var(--ink)}
			.xcr-acts button.pri{background:var(--brand);color:#fff}
			.xcr-acts button.dngr{background:#FBEDEB;color:var(--red)}
			.xcr-new{display:flex;gap:8px;margin-top:12px}
			.xcr-new input{flex:1;border:1px solid var(--ln);border-radius:10px;padding:8px 12px;font-size:13px}
			.xcr-new button{border:0;border-radius:10px;padding:8px 16px;background:var(--brand);color:#fff;font-weight:600;cursor:pointer}
			.xcr-empty{color:var(--fnt);font-size:13px;padding:18px 4px}`;
			document.head.appendChild(s);
		}
		const d = new frappe.ui.Dialog({ title: `${x.customer} — ${__("Change requests")}`, size: "large" });
		let view = null;
		const PRICE_CHIP = (c) => {
			const ps = c.pricing_status || "Awaiting Pricing";
			if (c.status === "Declined") return `<span class="xcr-chip red">${__("declined")}</span>`;
			if (ps === "Awaiting Pricing") return `<span class="xcr-chip amber">${__("awaiting pricing")}</span>`;
			if (ps === "Priced") return `<span class="xcr-amt">${frappe.utils.escape_html(c.cost_fmt || "")}</span>`;
			if (ps === "Covered by Subscription") return `<span class="xcr-chip green">${__("covered")}</span>`;
			if (ps === "Goodwill") return `<span class="xcr-chip green">${__("goodwill")}</span>`;
			return `<span class="xcr-chip">${__(ps.toLowerCase())}</span>`;
		};
		const DOT = (c) =>
			c.status === "Declined" ? "var(--red)"
			: ["Approved", "Delivered"].includes(c.status) ? "var(--good)"
			: c.status === "In Delivery" ? "#0E7490"
			: (c.pricing_status || "Awaiting Pricing") === "Awaiting Pricing" || c.status === "Awaiting Approval" ? "var(--amber)"
			: "var(--fnt)";
		const call = (method, args) =>
			frappe.call({
				method: "duty_board.client_room." + method,
				args: args,
				callback: (r) => {
					if (r.message) {
						render(r.message);
						this.render_client_room(r.message);
					}
				},
			});
		const stepper = (c) => {
			const ps = c.pricing_status || "Awaiting Pricing";
			const free = ["Covered by Subscription", "Goodwill"].includes(ps);
			const steps = free
				? [__("Drafted"), ps === "Goodwill" ? __("Goodwill") : __("Covered"), __("In delivery"), __("Delivered")]
				: [__("Drafted"), __("Priced"), __("Client approval"), __("Approved"), __("In delivery"), __("Delivered")];
			let idx = 0;
			if (free) idx = c.status === "Delivered" ? 3 : c.status === "In Delivery" ? 2 : 1;
			else if (c.status === "Delivered") idx = 5;
			else if (c.status === "In Delivery") idx = 4;
			else if (c.status === "Approved") idx = 3;
			else if (c.status === "Awaiting Approval") idx = 2;
			else idx = ps === "Priced" ? 1 : 0;
			const bad = c.status === "Declined";
			return `<div class="xcr-steps">${steps
				.map((s, i) => `<div class="xcr-step ${bad && i === 2 ? "bad" : i < idx ? "on" : i === idx ? "now" : ""}">${s}</div>`)
				.join("")}</div>`;
		};
		const render = (data) => {
			const crs = data.change_requests || [];
			if (view && !crs.some((z) => z.name === view)) view = null;
			if (!view) {
				const waitP = crs.filter((z) => (z.pricing_status || "Awaiting Pricing") === "Awaiting Pricing" && z.status !== "Declined").length;
				const waitC = crs.filter((z) => z.status === "Awaiting Approval").length;
				$(d.body).html(`<div class="xcr">
					<div class="xcr-sum">${crs.length} ${__("total")}${waitP ? ` · <b style="color:var(--amber)">${waitP} ${__("awaiting pricing")}</b>` : ""}${waitC ? ` · ${waitC} ${__("with the client")}` : ""}</div>
					${crs.length ? crs.map((c) => `
						<div class="xcr-row" data-open="${c.name}">
							<span class="xcr-dot" style="background:${DOT(c)}"></span>
							<span class="t">${frappe.utils.escape_html(c.title)}</span>
							<span class="s">
								${c.cards_total ? `<span>${c.cards_done}/${c.cards_total} ${__("tasks")}</span>` : ""}
								${PRICE_CHIP(c)}
								<span class="xcr-chip">${__(c.status)}</span>
								<span style="color:var(--ln)">›</span>
							</span>
						</div>`).join("") : `<div class="xcr-empty">${__("No change requests yet — work beyond the subscription starts its life here.")}</div>`}
					<div class="xcr-new">
						<input type="text" maxlength="140" placeholder="${__("New change request — title…")}">
						<button>＋ ${__("Draft it")}</button>
					</div>
				</div>`);
				$(d.body).find(".xcr-row").on("click", (e) => { view = $(e.currentTarget).data("open"); render(data); });
				const $in = $(d.body).find(".xcr-new input");
				$(d.body).find(".xcr-new button").on("click", () => {
					const t = ($in.val() || "").trim();
					if (t) call("chreq_add", { name: x.name, title: t });
				});
				return;
			}
			const c = crs.find((z) => z.name === view);
			const ps = c.pricing_status || "Awaiting Pricing";
			const locked = ["Approved", "In Delivery", "Delivered"].includes(c.status);
			const F = [
				[__("Request"), c.original_request], [__("Why"), c.reason], [__("Scope"), c.scope_impact],
				[__("Timeline"), c.timeline_impact], [__("Resources"), c.resource_impact], [__("Risks"), c.risks],
			].filter((z) => (z[1] || "").trim());
			$(d.body).html(`<div class="xcr">
				<span class="xcr-back">‹ ${__("All change requests")}</span>
				<div class="xcr-h">${frappe.utils.escape_html(c.title)}</div>
				<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
					${PRICE_CHIP(c)}<span class="xcr-chip">${__(c.status)}</span>
					${c.invoice_status ? `<span class="xcr-chip ${c.invoice_status === "Paid" ? "green" : "amber"}">${__(c.invoice_status.toLowerCase())}</span>` : ""}
					${c.cards_total ? `<span class="xcr-chip">${c.cards_done}/${c.cards_total} ${__("tasks")}</span>` : ""}
				</div>
				${stepper(c)}
				${c.status === "Draft" && ps === "Awaiting Pricing" ? `<div class="xcr-note amber">⏳ ${this.is_pricer ? __("In YOUR pricing queue — decide below and it moves.") : __("In the pricing queue — it reaches the client once priced or covered.")}</div>` : ""}
				${c.status === "Draft" && ps === "Priced" ? `<div class="xcr-note green">${__("Priced and ready — send it to the client for formal approval.")}</div>` : ""}
				${["Covered by Subscription", "Goodwill"].includes(ps) && !locked && c.status !== "Declined" ? `<div class="xcr-note green">${__("No charge — work can proceed; start delivery when ready.")}</div>` : ""}
				${c.status === "Awaiting Approval" ? `<div class="xcr-note amber">${__("With the client for sign-off.")}</div>` : ""}
				${c.status === "Declined" ? `<div class="xcr-note amber">↩ ${frappe.utils.escape_html(c.decline_reason || __("Declined by the client."))}</div>` : ""}
				${["Approved", "In Delivery", "Delivered"].includes(c.status) && c.approved_full ? `<div class="xcr-note green">✍ ${__("Approved by")} ${frappe.utils.escape_html(c.approved_full)} · ${frappe.utils.escape_html(c.approved_at || "")}</div>` : ""}
				${F.length ? `<dl class="xcr-f">${F.map((z) => `<dt>${z[0]}</dt><dd>${frappe.utils.escape_html(z[1])}</dd>`).join("")}</dl>` : ""}
				<div class="xcr-acts">
					${ps === "Awaiting Pricing" && c.status !== "Declined" && this.is_pricer ? `<button data-a="price" class="pri">${__("Price now")}</button>` : ""}
					${!locked ? `<button data-a="edit">${__("Edit")}</button>` : ""}
					<button data-a="tasks">${__("Tasks")}</button>
					<button data-a="newtask">＋ ${__("New task")}</button>
					${c.source_message ? `<button data-a="origin">${__("Origin")}</button>` : ""}
					${c.status === "Draft" && ps === "Priced" ? `<button data-a="ask" class="pri">${__("Send for approval")}</button>` : ""}
					${!locked && ["Covered by Subscription", "Goodwill"].includes(ps) && c.status !== "Declined" ? `<button data-a="deliver" class="pri">${__("Start delivery")}</button>` : ""}
					${c.status === "Awaiting Approval" ? `<button data-a="recall">${__("Recall")}</button>` : ""}
					${c.status === "Declined" ? `<button data-a="reopen">${__("Revise")}</button>` : ""}
					${c.status === "Approved" ? `<button data-a="deliver" class="pri">${__("Start delivery")}</button>` : ""}
					${c.status === "In Delivery" ? `<button data-a="done" class="pri">${__("Mark delivered")}</button>` : ""}
					${["Draft", "Declined"].includes(c.status) ? `<button data-a="del" class="dngr">${__("Delete")}</button>` : ""}
				</div>
			</div>`);
			$(d.body).find(".xcr-back").on("click", () => { view = null; render(data); });
			$(d.body).find(".xcr-acts button").on("click", (e) => {
				const a = $(e.currentTarget).data("a");
				const id = c.name;
				if (a === "price")
					return frappe.prompt(
						[
							{ fieldname: "decision", fieldtype: "Select", label: __("Decision"), options: ["Priced", "Covered by Subscription", "Goodwill", "Rejected", "Deferred"], reqd: 1 },
							{ fieldname: "price", fieldtype: "Currency", label: __("Price (₦, for Priced)") },
							{ fieldname: "estimate_hours", fieldtype: "Float", label: __("Estimated hours") },
							{ fieldname: "note", fieldtype: "Small Text", label: __("Note (kept on the CR)") },
						],
						(v) =>
							frappe.call({
								method: "duty_board.commercial.chreq_price",
								args: { name: id, decision: v.decision, price: v.price || 0, estimate_hours: v.estimate_hours || 0, note: v.note || null },
								callback: () =>
									frappe.call({
										method: "duty_board.client_room.get_room",
										args: { name: x.name },
										callback: (rr) => {
											if (rr.message) {
												render(rr.message);
												this.render_client_room(rr.message);
											}
										},
									}),
							}),
						__("Price this CR"),
						__("Apply")
					);
				if (a === "ask")
					return frappe.confirm(
						__("Send “{0}” to the client for formal approval? They will see the scope, cost and timeline impacts.", [frappe.utils.escape_html(c.title)]),
						() => call("chreq_request_approval", { id: id })
					);
				if (a === "newtask")
					return frappe.prompt(
						[
							{ fieldname: "title", fieldtype: "Data", label: __("Task title"), reqd: 1 },
							{ fieldname: "assignee", fieldtype: "Autocomplete", label: __("Assignee"), options: this.staff_options() },
							{ fieldname: "due_date", fieldtype: "Date", label: __("Due") },
						],
						(v) => call("chreq_new_task", { id: id, title: v.title, assignee: v.assignee || null, due_date: v.due_date || null }),
						__("New delivery task for this CR"),
						__("Create")
					);
				if (a === "origin") { d.hide(); return this.jump_to_msg(c.source_message); }
				if (a === "recall") return call("chreq_set_status", { id: id, status: "Draft" });
				if (a === "deliver") return call("chreq_set_status", { id: id, status: "In Delivery" });
				if (a === "done") return call("chreq_set_status", { id: id, status: "Delivered" });
				if (a === "reopen") return call("chreq_reopen", { id: id });
				if (a === "del")
					return frappe.confirm(__("Delete this change request?"), () => { view = null; call("chreq_delete", { id: id }); });
				if (a === "tasks") {
					return frappe.call({
						method: "duty_board.client_room.chreq_task_options",
						args: { id: id },
						callback: (r) => {
							const opts = r.message || {};
							if (!opts.project) {
								frappe.msgprint(__("Link a project to this room first — tasks live on the project board."));
								return;
							}
							const td = new frappe.ui.Dialog({ title: `${__("Tasks delivering")} “${c.title}”` });
							$(td.body).html(
								(opts.tasks || [])
									.map(
										(t) => `
								<label class="duty-cr-mstask ${t.elsewhere ? "elsewhere" : ""}" style="display:flex;gap:8px;align-items:center;padding:4px 0">
									<input type="checkbox" data-name="${t.name}" ${t.checked ? "checked" : ""} ${t.elsewhere ? "disabled" : ""}>
									<span>${frappe.utils.escape_html(t.title)}</span>
									<span class="text-muted" style="margin-left:auto">${__(t.column)}${t.elsewhere ? " · " + __("on another CR") : ""}</span>
								</label>`
									)
									.join("") || `<div class="text-muted">${__("No cards on this project board yet.")}</div>`
							);
							td.set_primary_action(__("Save"), () => {
								const chosen = [];
								$(td.body).find("input:checked").each(function () {
									chosen.push($(this).data("name"));
								});
								frappe.call({
									method: "duty_board.client_room.chreq_set_tasks",
									args: { id: id, tasks: JSON.stringify(chosen) },
									callback: (r2) => {
										td.hide();
										if (r2.message) {
											render(r2.message);
											this.render_client_room(r2.message);
										}
									},
								});
							});
							td.show();
						},
					});
				}
				if (a === "edit") {
					return frappe.prompt(
						[
							{ fieldname: "title", fieldtype: "Data", label: __("Title"), default: c.title, reqd: 1 },
							{ fieldname: "reason", fieldtype: "Small Text", label: __("Business reason"), default: c.reason },
							{ fieldname: "scope_impact", fieldtype: "Text", label: __("Scope impact (client sees this)"), default: c.scope_impact },
							{ fieldname: "timeline_impact", fieldtype: "Data", label: __("Timeline impact — e.g. +2 weeks"), default: c.timeline_impact },
							{ fieldname: "cost_impact", fieldtype: "Currency", label: __("Cost impact"), default: c.cost_impact },
							{ fieldname: "resource_impact", fieldtype: "Small Text", label: __("Resources"), default: c.resource_impact },
							{ fieldname: "risks", fieldtype: "Small Text", label: __("Risks"), default: c.risks },
							{ fieldname: "quotation", fieldtype: "Link", options: "Quotation", label: __("Quotation"), default: c.quotation },
						],
						(v) =>
							call("chreq_update", {
								id: id, title: v.title, reason: v.reason || null,
								scope_impact: v.scope_impact || null, timeline_impact: v.timeline_impact || null,
								cost_impact: v.cost_impact || 0, resource_impact: v.resource_impact || null,
								risks: v.risks || null, quotation: v.quotation || null,
							}),
						__("Edit change request"),
						__("Save")
					);
				}
			});
		};
		render(x);
		d.show();
	}

	room_shelf_dialog(x) {
		const d = new frappe.ui.Dialog({ title: `📚 ${x.customer} — ${__("Shelf")}` });
		const load = () =>
			frappe.call({
				method: "duty_board.client_room.get_room",
				args: { name: x.name },
				callback: (r) => r.message && render(r.message.shelf || []),
			});
		const render = (docs) => {
			$(d.body).html(`
				<div class="duty-cr-shelflist">
					${docs
						.map(
							(s) =>
								`<div class="duty-cr-mem"><a href="/api/method/duty_board.client_room.staff_shelf_file?id=${encodeURIComponent(s.name)}" target="_blank"><b>📄 ${frappe.utils.escape_html(s.title)}</b></a> ${s.category ? `<span class="duty-lead-chip">${frappe.utils.escape_html(s.category)}</span>` : ""} <span class="text-muted">${s.creation}</span> <a class="duty-cr-shelfrm" data-name="${s.name}" style="margin-left:auto;color:var(--red-600,#dc2626)">${__("Remove")}</a></div>`
						)
						.join("") || `<div class="text-muted">${__("Empty shelf — add the manuals and agreements this client should always have.")}</div>`}
				</div>
				<div class="duty-lead-section">＋ ${__("Add document")}</div>
				<div class="duty-cr-addmem" style="flex-wrap:wrap">
					<input type="text" class="form-control input-sm duty-sh-title" placeholder="${__("Title")}" style="flex:2">
					<input type="text" class="form-control input-sm duty-sh-cat" placeholder="${__("Category (optional)")}" style="flex:1">
					<label class="btn btn-sm btn-default" style="margin:0">📎 ${__("Choose file")}<input type="file" hidden class="duty-sh-file"></label>
					<button type="button" class="btn btn-sm btn-primary duty-sh-add">＋ ${__("Publish")}</button>
				</div>
				<p class="text-muted duty-attach-hint">${__("Everything here is permanently visible on the client's portal.")}</p>
			`);
			let pending = null;
			$(d.body).find(".duty-sh-file").on("change", (e) => {
				pending = e.target.files[0] || null;
				if (pending) $(e.target).parent().contents().first()[0].textContent = "📎 " + pending.name.slice(0, 24) + " ";
			});
			$(d.body).find(".duty-cr-shelfrm").on("click", (e) =>
				frappe.confirm(__("Remove from the client's shelf?"), () =>
					frappe.call({
						method: "duty_board.client_room.shelf_remove",
						args: { doc_name: $(e.currentTarget).data("name") },
						callback: load,
					})
				)
			);
			$(d.body).find(".duty-sh-add").on("click", async () => {
				const title = $(d.body).find(".duty-sh-title").val().trim();
				const cat = $(d.body).find(".duty-sh-cat").val().trim();
				if (!title || !pending) {
					frappe.msgprint(__("A title and a file are both needed."));
					return;
				}
				try {
					const up = await this.upload_private_file(pending);
					frappe.call({
						method: "duty_board.client_room.shelf_add",
						args: {
							name: x.name,
							title: title,
							category: cat || null,
							attachment_url: up.file_url,
							attachment_name: up.file_name,
						},
						callback: (r) => r.message && render(r.message.shelf || []),
					});
				} catch (err) {
					frappe.msgprint(__("Upload failed: {0}", [frappe.utils.escape_html(err.message || "")]));
				}
			});
		};
		render(x.shelf || []);
		d.show();
	}

	room_members_dialog(x) {
		const d = new frappe.ui.Dialog({ title: `👥 ${x.customer}` });
		const render = (data) => {
			$(d.body).html(`
				<div class="duty-cr-memlist">
					${(data.members || [])
						.map(
							(m) =>
								`<div class="duty-cr-mem">${m.is_admin ? "★ " : ""}<b>${frappe.utils.escape_html(m.full_name)}</b> <span class="text-muted">${frappe.utils.escape_html(m.user)}${m.is_admin ? " · " + __("administrator") : ""}</span> <a class="duty-cr-memadmin" data-name="${m.name}" data-on="${m.is_admin ? 0 : 1}">${m.is_admin ? "☆ " + __("Demote") : "★ " + __("Make admin")}</a> <a class="duty-cr-memrm" data-name="${m.name}">${__("Remove")}</a></div>`
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
				<div class="duty-lead-section">📅 ${__("Bookable for meetings")}</div>
				<div class="duty-cr-bookable">
					${[{ user: frappe.session.user, full_name: frappe.session.user_fullname || frappe.session.user }]
						.concat(this.team_members() || [])
						.filter((s, i, arr) => s.user !== "Administrator" && arr.findIndex((z) => z.user === s.user) === i)
						.map(
							(s) =>
								`<label style="margin-right:12px;font-size:var(--text-sm)"><input type="checkbox" value="${frappe.utils.escape_html(s.user)}" ${(data.meeting_staff || []).includes(s.user) ? "checked" : ""}> ${frappe.utils.escape_html((s.full_name || s.user).split(" ")[0])}</label>`
						)
						.join("")}
					<button type="button" class="btn btn-sm btn-primary duty-cr-booksave">${__("Save")}</button>
				</div>
				<p class="text-muted duty-attach-hint">${__("Ticked staff appear in the client's meeting picker. Nobody ticked = everyone bookable.")}</p>
			`);
			$(d.body).find(".duty-cr-booksave").on("click", () => {
				const users = $(d.body)
					.find(".duty-cr-bookable input:checked")
					.map((i, el) => el.value)
					.get();
				frappe.call({
					method: "duty_board.client_room.set_meeting_staff",
					args: { name: x.name, users: JSON.stringify(users) },
					callback: (r) => r.message && render(r.message),
				});
			});
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
			$(d.body).find(".duty-cr-memadmin").on("click", (e) =>
				frappe.call({
					method: "duty_board.client_room.member_set_admin",
					args: { member_name: $(e.currentTarget).data("name"), on: $(e.currentTarget).data("on") },
					callback: (r) => {
						if (r.message) {
							render(r.message);
							this.render_client_room(r.message);
						}
					},
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

	kb_dialog() {
		const d = new frappe.ui.Dialog({ title: `📚 ${__("Knowledge Base")}`, size: "large" });
		$(d.body).html(`
			<input type="text" class="form-control duty-kb-q" placeholder="${__("Search solutions… (2+ letters)")}">
			<div class="duty-kb-results" style="margin-top:10px"></div>
		`);
		let t = null;
		$(d.body).find(".duty-kb-q").on("input", (e) => {
			clearTimeout(t);
			t = setTimeout(() => {
				frappe.call({
					method: "duty_board.api.kb_search",
					args: { query: e.target.value },
					callback: (r) => {
						const rows = r.message || [];
						$(d.body).find(".duty-kb-results").html(
							rows
								.map(
									(a) => `
							<div class="duty-kb-art">
								<b>${frappe.utils.escape_html(a.title)}</b>
								${a.product ? `<span class="duty-lead-chip">${frappe.utils.escape_html(a.product)}</span>` : ""}
								${a.problem ? `<div class="text-muted" style="font-size:var(--text-xs)">${frappe.utils.escape_html(a.problem.slice(0, 160))}</div>` : ""}
								<div class="duty-kb-sol">${frappe.utils.escape_html(a.solution)}</div>
							</div>`
								)
								.join("") || `<div class="text-muted">${__("Nothing yet — resolve issues and promote the good ones.")}</div>`
						);
					},
				});
			}, 250);
		});
		d.show();
		setTimeout(() => $(d.body).find(".duty-kb-q").trigger("focus"), 200);
	}

	team_load_dialog() {
		const d = new frappe.ui.Dialog({ title: `👥 ${__("Team load & skills")}`, size: "large" });
		const render = (rows) => {
			$(d.body).html(
				(rows || [])
					.map(
						(r) => `
					<div class="duty-load-row">
						<b>${frappe.utils.escape_html(r.full_name)}</b>
						<span class="duty-load-n ${r.open + r.in_progress >= 5 ? "hot" : ""}">${r.open} ${__("open")} · ${r.in_progress} ${__("active")}</span>
						<span class="duty-load-skills">
							${r.skills.map((s) => `<span class="duty-lead-chip">${frappe.utils.escape_html(s.skill)} <a data-id="${s.name}" data-user="${frappe.utils.escape_html(r.user)}" class="duty-skill-x">×</a></span>`).join("")}
							<a class="duty-skill-add" data-user="${frappe.utils.escape_html(r.user)}">＋ ${__("skill")}</a>
						</span>
					</div>`
					)
					.join("")
			);
			$(d.body).find(".duty-skill-add").on("click", (e) =>
				frappe.prompt(
					{ fieldname: "skill", fieldtype: "Data", label: __("Skill (e.g. ZhiftPOS, Payroll, Stock)"), reqd: 1 },
					(v) =>
						frappe.call({
							method: "duty_board.api.skill_add",
							args: { user: $(e.currentTarget).data("user"), skill: v.skill },
							callback: (r) => render(r.message),
						}),
					__("Add skill"),
					__("Add")
				)
			);
			$(d.body).find(".duty-skill-x").on("click", (e) =>
				frappe.call({
					method: "duty_board.api.skill_remove",
					args: { name: $(e.currentTarget).data("id") },
					callback: (r) => render(r.message),
				})
			);
		};
		frappe.call({
			method: "duty_board.api.staff_workload",
			callback: (r) => render(r.message),
		});
		d.show();
	}

	me_day_dialog(day) {
		const m = this._me_data || {};
		const items = (m.day_items || {})[day] || { meetings: [], tasks: [] };
		const esc = frappe.utils.escape_html;
		const d = new frappe.ui.Dialog({ title: `📆 ${day}` });
		$(d.body).html(`
			${items.meetings.length ? `<div class="duty-lead-section">📅 ${__("Meetings")}</div>` : ""}
			${items.meetings.map((mt) => `
				<div class="duty-day-row">
					<b>${esc(mt.time || "")}</b> ${esc(mt.topic)}
					${mt.customer ? `<span class="text-muted">· ${esc(mt.customer)}</span>` : ""}
					${mt.status === "Pending" ? `<span class="duty-day-pending">${__("pending")}</span>` : ""}
					<a class="duty-day-move" data-kind="meeting" data-name="${esc(mt.name)}" title="${__("Reschedule")}">✎</a>
				</div>`).join("")}
			${(items.todos || []).length ? `<div class="duty-lead-section">📋 ${__("Plan items")}</div>` : ""}
			${(items.todos || []).map((td) => `
				<div class="duty-day-row duty-day-todo">
					<input type="checkbox" data-name="${esc(td.name)}" ${td.done ? "checked" : ""}>
					<b>${esc(td.time || "")}</b> <span class="${td.done ? "duty-todo-done" : ""}">${esc(td.text)}</span>
					${td.customer ? `<span class="text-muted">· ${esc(td.customer)}</span>` : ""}
					<a class="duty-day-move" data-kind="todo" data-name="${esc(td.name)}" title="${__("Move")}">✎</a>
				</div>`).join("")}
			${items.tasks.length ? `<div class="duty-lead-section">⚠ ${__("Tasks due")}</div>` : ""}
			${items.tasks.map((t) => `
				<div class="duty-day-row duty-day-task" data-name="${esc(t.name)}">
					<span class="duty-sev duty-sev-${(t.severity || "medium").toLowerCase()}">${__(t.severity || "Medium")}</span>
					${esc(t.title)} <span class="text-muted">· ${esc(t.customer || "")}</span>
					<a class="duty-day-move" data-kind="task" data-name="${esc(t.name)}" title="${__("Change due date")}">✎</a>
				</div>`).join("")}
			${!items.meetings.length && !items.tasks.length ? `<div class="text-muted">${__("Nothing scheduled.")}</div>` : ""}
			<div class="duty-day-actions">
				<button class="btn btn-xs btn-default duty-day-newtodo">＋ ${__("To-do")}</button>
				<button class="btn btn-xs btn-default duty-day-newtask">＋ ${__("Task due this day")}</button>
				<button class="btn btn-xs btn-primary duty-day-newmeet">＋ ${__("Meeting")}</button>
			</div>
		`);
		$(d.body).find(".duty-day-move").on("click", (e) => {
			e.stopPropagation();
			const kind = $(e.currentTarget).data("kind");
			const name = $(e.currentTarget).data("name");
			d.hide();
			const fields = [{ fieldname: "date", fieldtype: "Date", label: __("New date"), default: day, reqd: 1 }];
			if (kind !== "task") fields.push({ fieldname: "time", fieldtype: "Time", label: __("Time") });
			frappe.prompt(fields, (v) => {
				const done = () => {
					frappe.show_alert({ message: __("Moved"), indicator: "green" });
					this.refresh_me((this._me_data || {}).month);
				};
				if (kind === "meeting")
					frappe.call({ method: "duty_board.api.reschedule_meeting", args: { name, meeting_date: v.date, start_time: v.time || null }, callback: done });
				else if (kind === "todo")
					frappe.call({ method: "duty_board.api.update_todo", args: { name, date: v.date, due_time: v.time || null }, callback: done });
				else
					frappe.call({ method: "duty_board.api.update_issue", args: { name, due_date: v.date }, callback: done });
			}, __("Reschedule"));
		});
		$(d.body).find(".duty-day-todo input").on("change", (e) => {
			frappe.call({
				method: "duty_board.api.toggle_todo",
				args: { name: $(e.currentTarget).data("name"), done: e.currentTarget.checked ? 1 : 0 },
				callback: () => this.refresh_me((this._me_data || {}).month),
			});
		});
		$(d.body).find(".duty-day-task").on("click", (e) => {
			d.hide();
			this.issue_detail_dialog($(e.currentTarget).data("name"));
		});
		$(d.body).find(".duty-day-newtodo").on("click", () => {
			d.hide();
			frappe.prompt(
				[
					{ fieldname: "description", fieldtype: "Data", label: __("To-do"), reqd: 1 },
					{ fieldname: "due_time", fieldtype: "Time", label: __("Time (optional)") },
				],
				(v) =>
					frappe.call({
						method: "duty_board.api.add_todo",
						args: { description: v.description, date: day, due_time: v.due_time || null },
						callback: () => {
							frappe.show_alert({ message: __("Added to your plan"), indicator: "green" });
							this.refresh_me((this._me_data || {}).month);
						},
					}),
				`📋 ${day}`
			);
		});
		$(d.body).find(".duty-day-newtask").on("click", () => {
			d.hide();
			this.create_issue_dialog({ due_date: day });
		});
		$(d.body).find(".duty-day-newmeet").on("click", () => {
			d.hide();
			this.me_meeting_dialog(day);
		});
		d.show();
	}

	me_meeting_dialog(day) {
		const md = new frappe.ui.Dialog({
			title: __("📅 New Meeting"),
			fields: [
				{ fieldname: "topic", fieldtype: "Data", label: __("Topic"), reqd: 1 },
				{ fieldname: "meeting_date", fieldtype: "Date", label: __("Date"), default: day, reqd: 1 },
				{ fieldname: "start_time", fieldtype: "Time", label: __("Time") },
				{ fieldname: "duration_mins", fieldtype: "Int", label: __("Duration (mins)"), default: 30 },
				{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: __("Customer (optional — the room hears about it)") },
				{
					fieldname: "attendees",
					fieldtype: "MultiSelectList",
					label: __("Attendees"),
					get_data: () =>
						this.team_members().map((t) => ({ value: t.user, description: t.full_name })),
				},
			],
			primary_action_label: __("Schedule"),
			primary_action: (v) => {
				frappe.call({
					method: "duty_board.api.create_meeting",
					args: {
						topic: v.topic,
						meeting_date: v.meeting_date,
						start_time: v.start_time || null,
						duration_mins: v.duration_mins || 30,
						customer: v.customer || null,
						attendees: v.attendees && v.attendees.length ? JSON.stringify(v.attendees) : null,
					},
					callback: () => {
						md.hide();
						frappe.show_alert({ message: __("Meeting scheduled"), indicator: "green" });
						this.refresh_me((this._me_data || {}).month);
					},
				});
			},
		});
		md.show();
	}

	load_updates(x, $host) {
		const render = (rows) => {
			$host.html(`
				<div class="duty-lead-section">📝 ${__("Updates")}</div>
				${(rows || [])
					.map(
						(u) => `<div class="duty-upd-row"><span class="duty-upd-meta">${frappe.utils.escape_html(u.by)} · ${frappe.utils.escape_html(u.when)}</span>${frappe.utils.escape_html(u.note)}</div>`
					)
					.join("") || `<div class="text-muted" style="font-size:var(--text-xs)">${__("No updates yet — post progress and the client's room hears it.")}</div>`}
				<div class="duty-upd-compose">
					<input type="text" class="form-control input-sm duty-upd-in" placeholder="${__("Post a progress update…")}">
					<button type="button" class="btn btn-xs btn-primary duty-upd-send">${__("Post")}</button>
				</div>
			`);
			const post = () => {
				const note = $host.find(".duty-upd-in").val().trim();
				if (!note) return;
				frappe.call({
					method: "duty_board.api.issue_update_add",
					args: { name: x.name, note },
					callback: (r) => render(r.message),
				});
			};
			$host.find(".duty-upd-send").on("click", post);
			$host.find(".duty-upd-in").on("keydown", (e) => {
				if (e.key === "Enter") post();
			});
		};
		frappe.call({
			method: "duty_board.api.issue_updates",
			args: { name: x.name },
			callback: (r) => render(r.message),
		});
	}

	load_similar(x, $host) {
		frappe.call({
			method: "duty_board.api.similar_issues",
			args: { name: x.name },
			callback: (r) => {
				const m = r.message || {};
				if (!(m.issues || []).length && !(m.kb || []).length) return;
				$host.html(`
					<div class="duty-lead-section">🧠 ${__("Similar past work")}</div>
					${(m.kb || [])
						.map(
							(k) => `<div class="duty-sim-row">📚 <b>${frappe.utils.escape_html(k.title)}</b><span class="text-muted">${frappe.utils.escape_html(k.solution)}</span></div>`
						)
						.join("")}
					${(m.issues || [])
						.map(
							(i) => `<div class="duty-sim-row">✅ <b>${frappe.utils.escape_html(i.title)}</b> <span class="duty-lead-chip">${frappe.utils.escape_html(i.customer || "")}</span>${i.resolution ? `<span class="text-muted">${frappe.utils.escape_html(i.resolution)}</span>` : ""}</div>`
						)
						.join("")}
				`);
			},
		});
	}

	sla_chip(x) {
		const s = x.sla || {};
		const live = (v) => v && (v.state === "pending" || v.state === "overdue");
		const pick = live(s.ack) ? s.ack : live(s.res) ? s.res : null;
		if (!pick) return "";
		if (pick.state === "overdue")
			return `<span class="duty-sla duty-sla-over">🔴 SLA ${frappe.utils.escape_html(pick.detail || "")}</span>`;
		if (pick.state === "pending")
			return `<span class="duty-sla">⏳ ${frappe.utils.escape_html(pick.detail || "")}</span>`;
		return "";
	}

	sla_meta(x) {
		const s = x.sla || {};
		const bit = (label, v) => {
			if (!v || !v.state) return "";
			if (v.state === "met") return `<span class="duty-sla duty-sla-met">✓ ${label} ${__("SLA met")}</span>`;
			if (v.state === "missed") return `<span class="duty-sla duty-sla-over">✗ ${label} ${__("SLA missed")}</span>`;
			if (v.state === "overdue") return `<span class="duty-sla duty-sla-over">🔴 ${label} ${frappe.utils.escape_html(v.detail || "")}</span>`;
			return `<span class="duty-sla">⏳ ${label} ${frappe.utils.escape_html(v.detail || "")}</span>`;
		};
		const a = bit(__("response"), s.ack);
		const b = bit(__("resolution"), s.res);
		return a || b ? `<div class="duty-issue-meta">${a} ${b}</div>` : "";
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
		if (this.issue_type_filter) {
			shown = shown.filter((x) => (x.issue_type || "Support") === this.issue_type_filter);
		}
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
					${x.issue_type && x.issue_type !== "Support" ? `<span class="duty-type-chip">${frappe.utils.escape_html(x.issue_type)}</span>` : ""}
					${this.sla_chip(x)}
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
						<a class="duty-oncall-chip" title="${__("On-call for out-of-hours urgents — click to change (System Manager)")}">${this._on_call ? `🌙 ${frappe.utils.escape_html(this._on_call.first)}` : `🌙 ${__("no on-call")}`}</a>
						<button class="btn btn-xs btn-default duty-kb-open">📚 ${__("KB")}</button>
						<button class="btn btn-xs btn-default duty-team-load">👥 ${__("Load")}</button>
						<button class="btn btn-xs btn-default duty-issue-new">＋ ${__("New")}</button>
					</div>
					<select class="form-control input-sm duty-issue-scope" title="${__("Status")}">
						<option value="open" ${scope === "open" ? "selected" : ""}>${__("Open")}</option>
						<option value="resolved" ${scope === "resolved" ? "selected" : ""}>${__("Resolved")}</option>
						<option value="closed" ${scope === "closed" ? "selected" : ""}>${__("Closed")}</option>
						<option value="all" ${scope === "all" ? "selected" : ""}>${__("All")}</option>
					</select>
					<select class="form-control input-sm duty-issue-typefilter" title="${__("Filter by type")}">
						<option value="">${__("All types")}</option>
						${["Support", "Bug", "Feature Request", "Configuration", "Training", "Data Correction", "Integration", "Billing", "Implementation"].map((t) => `<option value="${t}" ${this.issue_type_filter === t ? "selected" : ""}>${__(t)}</option>`).join("")}
					</select>
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
		$wrap.find(".duty-issue-typefilter").on("change", (e) => {
			this.issue_type_filter = e.target.value || "";
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
		$wrap.find(".duty-kb-open").on("click", () => this.kb_dialog());
		$wrap.find(".duty-team-load").on("click", () => this.team_load_dialog());
		$wrap.find(".duty-oncall-chip").on("click", () =>
			frappe.prompt(
				{ fieldname: "user", fieldtype: "Link", options: "User", label: __("On-call person"), default: this._on_call ? this._on_call.user : "" },
				(v) =>
					frappe.call({
						method: "duty_board.api.set_on_call",
						args: { user: v.user || "" },
						callback: () => this.refresh(),
					}),
				__("Set on-call"),
				__("Save")
			)
		);
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
					fieldname: "issue_type",
					fieldtype: "Select",
					label: __("Type"),
					options: "Support\nBug\nFeature Request\nConfiguration\nTraining\nData Correction\nIntegration\nBilling\nImplementation",
					default: "Support",
				},
				{
					fieldname: "due_date",
					fieldtype: "Date",
					label: __("Due Date"),
					default: prefill.due_date || undefined,
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
						issue_type: v.issue_type,
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
						${x.issue_type ? `<span class="duty-type-chip">${frappe.utils.escape_html(x.issue_type)}</span>` : ""}
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
					${this.sla_meta(x)}
					<div class="duty-upd-host"></div>
					<div class="duty-sim-host"></div>
					<div class="duty-issue-meta"><a class="duty-issue-rca">📋 ${__("RCA report")}</a> · <a class="duty-issue-kb">📚 ${__("Promote to KB")}</a> · <a class="duty-issue-chreq">💱 ${__("To change request")}</a> ·${x.source_message && x.source_type === "Client Room" ? ` <a class="duty-issue-origin">💬 ${__("View origin")}</a> ·` : ""} <a class="duty-issue-vis">${x.client_visible ? "👁 " + __("Client-visible — click to hide") : "🙈 " + __("Hidden from client — click to publish")}</a>${x.client_stars ? ` · <span class="duty-stars">${"★".repeat(x.client_stars)}${"☆".repeat(5 - x.client_stars)}</span>` : x.client_rating ? ` · ${x.client_rating === "Up" ? "👍 " + __("Client satisfied") : "👎 " + __("Client unhappy")}` : ""}${x.client_confirmed_at ? ` · <span class="duty-confirmed">✅ ${__("client confirmed")}</span>` : ""}${x.acknowledged_first ? ` · 👀 ${__("Acknowledged by")} ${frappe.utils.escape_html(x.acknowledged_first)}` : x.client_visible ? ` · <a class="duty-issue-ack">👀 ${__("Acknowledge")}</a>` : ""}</div>
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
			$(d.body).find(".duty-issue-ack").on("click", () =>
				frappe.call({
					method: "duty_board.api.acknowledge_issue",
					args: { name: name },
					callback: (r) => {
						if (r.message) render(r.message);
						if (this._open_room) this.load_client_room(this._open_room);
					},
				})
			);
			this.load_updates(x, $(d.body).find(".duty-upd-host"));
			this.load_similar(x, $(d.body).find(".duty-sim-host"));
			$(d.body).find(".duty-issue-origin").on("click", () => {
				d.hide();
				this.view_origin(x.source, x.source_message);
			});
			$(d.body).find(".duty-issue-chreq").on("click", () =>
				frappe.confirm(
					__("Draft a change request from this ticket? Use this when the ask is new paid scope, not subscription support."),
					() =>
						frappe.call({
							method: "duty_board.client_room.chreq_from_issue",
							args: { issue: name },
							callback: (r) => {
								if (r.message) {
									d.hide();
									frappe.show_alert({ message: __("💱 Change request drafted — open the client room to price and send it."), indicator: "green" });
									if (this._open_room === r.message.name) this.render_client_room(r.message);
								}
							},
						})
				)
			);
			$(d.body).find(".duty-issue-kb").on("click", () =>
				frappe.prompt(
					[
						{ fieldname: "title", fieldtype: "Data", label: __("Title"), default: x.title, reqd: 1 },
						{ fieldname: "product", fieldtype: "Data", label: __("Product") },
						{ fieldname: "solution", fieldtype: "Small Text", label: __("Solution"), default: x.resolution, reqd: 1 },
					],
					(v) =>
						frappe.call({
							method: "duty_board.api.kb_promote",
							args: Object.assign({ issue: x.name, problem: x.description || "" }, v),
							callback: () =>
								frappe.show_alert({ message: __("📚 Added to the knowledge base"), indicator: "green" }),
						}),
					__("Promote to knowledge base"),
					__("Promote")
				)
			);
			$(d.body).find(".duty-issue-rca").on("click", () =>
				frappe.call({
					method: "duty_board.client_room.rca_get",
					args: { issue: x.name },
					callback: (r) => {
						const ex = r.message || {};
						frappe.prompt(
							[
								{ fieldname: "what_happened", fieldtype: "Small Text", label: __("What happened"), default: ex.what_happened, reqd: 1 },
								{ fieldname: "root_cause", fieldtype: "Small Text", label: __("Root cause"), default: ex.root_cause, reqd: 1 },
								{ fieldname: "resolution_action", fieldtype: "Small Text", label: __("How we resolved it"), default: ex.resolution_action, reqd: 1 },
								{ fieldname: "prevention", fieldtype: "Small Text", label: __("What we changed so it cannot recur"), default: ex.prevention, reqd: 1 },
							],
							(v) =>
								frappe.call({
									method: "duty_board.client_room.rca_publish",
									args: Object.assign({ issue: x.name }, v),
									callback: () =>
										frappe.show_alert({
											message: __("📋 RCA published to the client's shelf"),
											indicator: "green",
										}),
								}),
							__("Incident report — published to the client's shelf as a branded PDF"),
							ex.what_happened ? __("Republish (updates the shelf copy)") : __("Publish")
						);
					},
				})
			);
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
								[{ value: frappe.session.user, description: __("Me") }].concat(
									this.team_members().map((t) => ({ value: t.user, description: t.full_name }))
								),
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
			</details>
			<details class="duty-sessions-details">
				<summary>${__("Upcoming")} (${(this.my_upcoming || []).length})</summary>
				${upcoming || `<div class="text-muted duty-history-empty">${__("Nothing scheduled ahead.")}</div>`}
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
			</details>
			<details class="duty-sessions-details">
				<summary>${__("Earlier days")}</summary>
				<div class="duty-history-link"><a>${__("Open work history ▸")}</a></div>
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
		let open_set;
		try {
			open_set = new Set(JSON.parse(localStorage.getItem("duty_staff_open") || "[]"));
		} catch (e) {
			open_set = new Set();
		}
		rows.forEach((r) => {
			const s = this.status_meta(r.status);
			const opened = open_set.has(r.user);
			const $card = $(`
				<div class="duty-card duty-card-click ${opened ? "" : "collapsed"}">
					<div class="duty-card-head">
						<span class="duty-card-caret">${opened ? "▾" : "▸"}</span>
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
			$card.find(".duty-card-head").on("click", (e) => {
				if ($(e.target).closest(".duty-dm-btn").length) return;
				const now_open = $card.hasClass("collapsed");
				$card.toggleClass("collapsed", !now_open);
				$card.find(".duty-card-caret").text(now_open ? "▾" : "▸");
				if (now_open) open_set.add(r.user);
				else open_set.delete(r.user);
				localStorage.setItem("duty_staff_open", JSON.stringify([...open_set]));
			});
			$card.find(".duty-card-more").on("click", (e) => {
				e.stopPropagation();
				this.show_member(r);
			});
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

	smart_time(s) {
		if (!s) return "";
		const d = new Date(s.replace(" ", "T"));
		if (isNaN(d)) return s;
		const hm = s.slice(11, 16);
		const now = new Date();
		const day0 = (x) => { const y = new Date(x.getFullYear(), x.getMonth(), x.getDate()); return y; };
		const today = day0(now);
		const that = day0(d);
		if (that.getTime() === today.getTime()) return hm;
		const monday = new Date(today);
		monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
		if (that >= monday && that < today) return d.toLocaleDateString(undefined, { weekday: "long" }) + " " + hm;
		return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) + ", " + hm;
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
			.duty-layout { display: flex; gap: 18px; align-items: flex-start; }
			.duty-main {
				flex: 1 1 0; min-width: 0;
				background: #fcfcfd; border: 1px solid var(--border-color);
				border-top: 4px solid #2563eb;
				border-radius: 14px; padding: 14px;
			}
			.duty-issues {
				background: #fbfbfa; border: 1px solid var(--border-color);
				border-top: 4px solid #d97706;
				border-radius: 14px; padding: 14px;
			}
			.duty-side {
				flex: 0 0 33%; max-width: 33%; position: sticky; top: 56px;
				background: #fafcfc; border: 1px solid var(--border-color);
				border-top: 4px solid #0F5C55;
				border-radius: 14px; padding: 12px;
			}
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
			.duty-tabbar-away { opacity: 0.92; box-shadow: 0 -2px 10px rgba(15, 92, 85, 0.25); }
			.duty-tabbar-away a.active { color: inherit; font-weight: 500; }
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
			.duty-msg-mine { background: #e7f4ec; border-radius: 10px; padding: 4px 8px; }
			.duty-msg-mine .duty-msg-who { color: var(--green-600, #2e7d32); }
			.duty-msg-time { margin-left: 8px; font-size: var(--text-xs); color: var(--text-muted); }
			.duty-chat-send { display: flex; gap: 8px; align-items: flex-end; }
			.duty-chat-input { resize: none; overflow-y: auto; max-height: 120px; line-height: 1.45; }
			.duty-msg-text { white-space: pre-wrap; word-break: break-word; color: #000; font-size: 15px; }
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
			.duty-issue-scope { min-width: 108px; }
			.duty-issues-toolbar-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
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
				padding: 10px 10px; cursor: pointer;
				background: #fff; border: 1px solid #dfe3e8; border-radius: 10px;
				margin-bottom: 10px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
			}
			.duty-issue-row:hover { background: var(--gray-50, #fafafa); border-color: #c7ced6; }
			.duty-issue-mine { border-left: 3px solid var(--blue-400, #60a5fa); padding-left: 8px; }
			.duty-issue-title { font-weight: 600; flex: 1; min-width: 140px; }
			.duty-issue-who, .duty-issue-meta { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-issue-status {
				font-size: var(--text-xs); font-weight: 700; padding: 1px 8px; border-radius: 99px;
				background: var(--blue-100, #e3f2fd); color: var(--blue-700, #1565c0);
			}
			.duty-issue-due { font-size: var(--text-xs); color: var(--text-muted); font-variant-numeric: tabular-nums; }
			.duty-health { font-size: 11px; }
			.duty-health-green { color: #16a34a; }
			.duty-health-amber { color: #d97706; }
			.duty-health-red { color: #dc2626; }
			.duty-oncall-chip { font-size: var(--text-xs); font-weight: 700; cursor: pointer; background: #ede9fe; color: #5b21b6; border-radius: 99px; padding: 2px 10px; white-space: nowrap; }
			.duty-kb-art { padding: 9px 4px; border-bottom: 1px dashed var(--border-color); }
			.duty-kb-sol { font-size: var(--text-sm); background: #f0fdfa; border-radius: 8px; padding: 7px 10px; margin-top: 5px; white-space: pre-wrap; }
			.duty-load-row { display: flex; gap: 12px; align-items: baseline; padding: 8px 4px; border-bottom: 1px dashed var(--border-color); flex-wrap: wrap; }
			.duty-load-n { font-weight: 700; font-size: var(--text-sm); }
			.duty-load-n.hot { color: #dc2626; }
			.duty-load-skills { display: flex; gap: 6px; flex-wrap: wrap; align-items: baseline; }
			.duty-skill-x { cursor: pointer; margin-left: 3px; }
			.duty-skill-add { cursor: pointer; font-size: var(--text-xs); font-weight: 700; }
			.duty-upd-row { padding: 7px 4px; border-bottom: 1px dashed var(--border-color); font-size: var(--text-sm); white-space: pre-wrap; }
			.duty-upd-meta { display: block; font-size: var(--text-xs); color: var(--text-muted); font-weight: 700; }
			.duty-upd-compose { display: flex; gap: 8px; margin-top: 8px; }
			.duty-upd-compose input { flex: 1; }
			.duty-sim-row { padding: 6px 4px; border-bottom: 1px dashed var(--border-color); font-size: var(--text-sm); display: flex; gap: 8px; flex-wrap: wrap; align-items: baseline; }
			.duty-sim-row .text-muted { font-size: var(--text-xs); width: 100%; }
			.duty-type-chip { font-size: var(--text-xs); background: #ede9fe; color: #5b21b6; border-radius: 99px; padding: 1px 8px; font-weight: 700; white-space: nowrap; }
			.duty-stars { color: #f59e0b; letter-spacing: 1px; }
			.duty-confirmed { color: #166534; font-weight: 700; font-size: var(--text-xs); }
			.duty-sla { font-size: var(--text-xs); background: #fef3c7; color: #92400e; border-radius: 99px; padding: 1px 8px; font-weight: 700; white-space: nowrap; }
			.duty-sla-over { background: #fee2e2; color: #b91c1c; }
			.duty-sla-met { background: #dcfce7; color: #166534; }
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
			.duty-projects { display: flex; gap: 0; align-items: stretch; min-height: calc(100vh - 120px); }
			.duty-pj-side { width: 250px; flex: none; border-right: 1px solid #e5e7eb; padding: 8px 8px 8px 0; overflow-y: auto; max-height: calc(100vh - 110px); }
			.duty-pj-sidehead { display: flex; gap: 6px; margin-bottom: 8px; }
			.duty-pj-main { flex: 1; min-width: 0; padding-left: 14px; }
			.duty-pj-title { font-size: 15px; padding: 2px 0 10px; }
			.duty-pj-cust { font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: #6B7772; padding: 7px 4px 4px; cursor: pointer; user-select: none; }
			.duty-pj-count { color: #b3b8b5; font-weight: 600; }
			.duty-pj-item { display: block; padding: 6px 8px; border-radius: 8px; margin: 2px 0; cursor: pointer; text-decoration: none; color: inherit; }
			.duty-pj-item:hover { background: #f5f4f0; text-decoration: none; color: inherit; }
			.duty-pj-item.active { background: #eef2f0; }
			.duty-pj-item .t { display: block; font-weight: 600; font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.duty-pj-item .s { display: block; font-size: 11px; color: #8a938f; }
			.duty-pj-views { display: inline-flex; gap: 2px; margin-left: 14px; background: #f0efe9; border-radius: 8px; padding: 2px; }
			.duty-pj-v { font-size: 12px; padding: 3px 10px; border-radius: 6px; cursor: pointer; color: #6B7772; text-decoration: none; }
			.duty-pj-v.on { background: #fff; color: #182420; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,.08); }
			.duty-cal-head { display: flex; gap: 10px; align-items: center; margin: 8px 0; }
			.duty-cal-nav, .duty-cal-today { cursor: pointer; padding: 2px 8px; border-radius: 6px; background: #f0efe9; text-decoration: none; color: #182420; font-size: 12.5px; }
			.duty-cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
			.duty-cal-dow { font-size: 10.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; color: #1a1a1a; padding: 6px 8px; background: #faf9f6; border-bottom: 1px solid #e5e7eb; }
			.duty-cal-cell { min-height: 92px; border-right: 1px solid #f0eee8; border-bottom: 1px solid #f0eee8; padding: 4px 5px; }
			.duty-cal-cell .d { font-size: 11.5px; color: #000; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }
			.duty-cal-add { visibility: hidden; cursor: pointer; color: #0E5A4A; font-weight: 700; text-decoration: none; padding: 0 3px; }
			.duty-cal-cell:hover .duty-cal-add { visibility: visible; }
			.duty-cal-cell:not(.duty-cal-pad) { cursor: pointer; }
			.duty-cal-cell.today { background: #f2f7f4; }
			.duty-cal-cell.today .d { color: #0E5A4A; font-weight: 800; }
			.duty-cal-cell.over { background: #e4eeea; }
			.duty-cal-pad { background: #fbfaf7; }
			.duty-cal-task { font-size: 11.5px; color: #000; font-weight: 500; background: #fff; border: 1px solid #eceae4; border-radius: 6px; padding: 2px 5px; margin-top: 3px; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.duty-cal-task.done { text-decoration: line-through; color: #96A09B; }
			.duty-proj-tabs { display: block; }
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
			.duty-cr-list {
				flex: 0 0 340px; display: flex; flex-direction: column; gap: 8px;
				background: var(--bg-light-gray, #f4f6f8); border: 1px solid var(--border-color);
				border-radius: 12px; padding: 12px; align-self: flex-start;
				max-height: calc(100vh - 185px); overflow-y: auto;
			}
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
			.duty-cr-room {
				flex: 1; border: 1px solid var(--border-color); border-radius: 12px;
				background: var(--card-bg); padding: 0 14px 14px; min-width: 0;
				display: flex; flex-direction: column; height: calc(100vh - 185px);
			}
			.duty-cr-ribbon {
				margin: 0 -14px 10px; padding: 7px 14px; border-radius: 12px 12px 0 0;
				background: #fef3c7; color: #92400e; font-size: var(--text-xs); font-weight: 700;
			}
			.duty-cr-head { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
			.duty-cr-taskchips { font-size: var(--text-xs); color: var(--text-muted); font-weight: 600; }
			.duty-cr-tools { margin-left: auto; display: flex; gap: 12px; }
			.duty-cr-tools a { cursor: pointer; font-size: var(--text-xs); font-weight: 600; }
			.duty-cr-main { display: flex; gap: 0; flex: 1 1 auto; min-height: 0; }
			.duty-cr-chatcol { padding-right: 14px; }
			.duty-cr-chatcol { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; min-height: 0; }
			.duty-cr-side {
				width: clamp(360px, 32%, 520px); flex: none;
				border-left: 3px solid var(--border-color);
				background: var(--bg-light-gray, #f8fafc);
				border-radius: 0 12px 12px 0;
				padding: 10px 12px; display: flex; flex-direction: column; min-height: 0;
			}
			.duty-cr-side .duty-cr-tasksbar { border-bottom: 2px solid var(--border-color); padding-bottom: 6px; margin-bottom: 8px; }
			.duty-cr-side.folded { width: 46px; padding-left: 6px; }
			.duty-cr-side.folded .duty-cr-sidebody { display: none; }
			.duty-cr-sidebody { overflow-y: auto; min-height: 0; flex: 1 1 auto; }
			.duty-cr-tasks { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; flex: none; }
			.duty-sessions-details { margin-top: 8px; width: 100%; }
			.duty-sessions-details > summary { cursor: pointer; font-weight: 600; }
			.duty-cr-back { display: none; }
			@media (max-width: 767px) {
				/* two screens: the list OR the room, never the stack */
				.duty-clients.cr-room-open .duty-cr-list { display: none; }
				.duty-clients:not(.cr-room-open) .duty-cr-room { display: none !important; }
				.duty-cr-back {
					display: inline-block; font-weight: 700; font-size: var(--text-md);
					color: var(--text-color); padding: 4px 10px 4px 0; white-space: nowrap;
				}
				/* conversation first; work folds beneath */
				.duty-cr-main { flex-direction: column; }
				.duty-cr-side {
					width: 100%; border-left: none; border-top: 3px solid var(--border-color);
					border-radius: 0; padding: 10px 4px 0; order: 1; margin-top: 10px;
				}
				.duty-cr-side.folded { width: 100%; }
				.duty-cr-sidebody { max-height: 38vh; }
				/* calm header: name + essentials, tools scroll, counts retire */
				.duty-cr-head {
					position: sticky; top: 0; z-index: 6; background: var(--bg-color, #fff);
					padding: 8px 0 6px; margin-bottom: 4px; flex-wrap: nowrap;
					overflow-x: auto; -webkit-overflow-scrolling: touch; scrollbar-width: none;
				}
				.duty-cr-head::-webkit-scrollbar { display: none; }
				.duty-cr-head > b { white-space: nowrap; }
				.duty-cr-taskchips, .duty-cr-lastseen { display: none; }
				.duty-cr-ribbon {
					font-size: 11px; white-space: nowrap; overflow: hidden;
					text-overflow: ellipsis; padding: 4px 10px;
				}
				/* room list rows: thumb-sized */
				.duty-cr-item { padding: 12px 12px; }
				/* composer: message field full-width on top, controls beneath */
				.duty-cr-compose { flex-wrap: wrap; gap: 8px 12px; }
				.duty-cr-compose textarea.duty-cr-input { flex: 1 1 100%; width: 100%; order: -1; }
				.duty-cr-compose button.duty-cr-send { margin-left: auto; }
			}
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
			.duty-cr-msgs { display: flex; flex-direction: column; gap: 8px; flex: 1 1 auto; min-height: 120px; overflow-y: auto; padding: 4px 0 8px; }
			.duty-cr-msg {
				border-radius: 10px; padding: 7px 11px; width: fit-content; min-width: 140px;
				max-width: 88%; position: relative; font-size: 15px;
				overflow-wrap: break-word; word-break: normal;
			}
			.duty-cr-msg .duty-msg-who { white-space: nowrap; }
			.duty-cr-reply {
				position: absolute; right: 6px; top: 4px; cursor: pointer; font-size: var(--text-xs);
				visibility: hidden; opacity: 0.6; text-decoration: none;
			}
			.duty-cr-msg:hover .duty-cr-reply { visibility: visible; }
			.duty-cr-quote {
				display: block; background: rgba(15, 92, 85, 0.08); border-left: 3px solid #0F5C55;
				border-radius: 6px; padding: 3px 8px; font-size: var(--text-xs); margin: 2px 0 4px;
				cursor: pointer; color: var(--text-color); text-decoration: none;
			}
			.duty-msg-flash { outline: 2px solid #0F5C55; border-radius: 10px; }
			.duty-msg-quote-link { cursor: pointer; }
			.duty-cr-emojis {
				flex-wrap: wrap; gap: 2px; border: 1px solid var(--border-color); border-radius: 10px;
				padding: 5px; margin-bottom: 5px; background: var(--card-bg);
			}
			.duty-cr-emojis a { font-size: 19px; padding: 2px 5px; cursor: pointer; border-radius: 6px; text-decoration: none; }
			.duty-cr-emojis a:hover { background: var(--gray-100, #f5f5f5); }
			.duty-cr-emojibtn { cursor: pointer; align-self: center; font-size: 18px; text-decoration: none; }
			.duty-cr-staff { background: #ecfdf5; align-self: flex-end; }
			.duty-cr-mine { background: #cdeedd; align-self: flex-end; border: 1px solid #b5e3cd; }
			.duty-cr-unread-sys { background: #eceae4 !important; color: #6B7772 !important; }
			.duty-cr-client { background: var(--gray-100, #f3f4f6); align-self: flex-start; }
			.duty-cr-internal { background: #fef9c3; border: 1px dashed #d97706; align-self: flex-end; }
			.duty-cr-msg .duty-msg-who { display: block; font-size: var(--text-xs); font-weight: 700; }
			.duty-cr-mktask { position: absolute; right: -26px; top: 6px; cursor: pointer; text-decoration: none; opacity: 0.5; }
			.duty-cr-msg:hover .duty-cr-mktask { opacity: 1; }
			.duty-cr-compose { display: flex; gap: 8px; align-items: flex-end; }
			.duty-cr-compose textarea { flex: 1; resize: none; font-size: 16px; }
			.duty-me-overlay {
				position: fixed; inset: 0; z-index: 1200; background: var(--bg-color, #fff);
				overflow-y: auto; padding: 0 16px 60px;
			}
			.duty-me-ovbar {
				position: sticky; top: 0; background: inherit; z-index: 2;
				display: flex; justify-content: space-between; align-items: center;
				padding: 14px 4px 10px; font-size: var(--text-lg);
			}
			.duty-me-ovclose { cursor: pointer; font-size: 22px; color: var(--text-muted); padding: 4px 10px; }
			.duty-me-ovbody { max-width: 1100px; margin: 0 auto; }
			.duty-me { padding: 8px 4px 40px; max-width: 1100px; margin: 0 auto; }
			.duty-me-head h2 { margin: 4px 0 2px; }
			.duty-me .duty-mtiles { margin: 14px 0 18px; }
			.duty-me-charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 20px; }
			.duty-me-chart { background: #fff; border: 1px solid var(--border-color); border-radius: 12px; padding: 10px 12px 4px; }
			.duty-me-chart h4 { margin: 2px 0 0; font-size: var(--text-sm); color: var(--text-muted); }
			.duty-me-reqs { background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; padding: 12px; margin-bottom: 20px; }
			.duty-me-reqs h4 { margin: 0 0 8px; }
			.duty-req-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 7px 4px; border-bottom: 1px dashed #fde68a; font-size: var(--text-sm); }
			.duty-req-btns { margin-left: auto; display: flex; gap: 6px; }
			.duty-me-cal { background: #fff; border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; margin-bottom: 20px; }
			.duty-me-calhead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
			.duty-me-calhead h4 { margin: 0; }
			.duty-cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
			.duty-cal-dow { text-align: center; font-size: var(--text-xs); color: var(--text-muted); font-weight: 700; padding: 2px 0; }
			.duty-cal-cell { min-height: 64px; border: 1px solid var(--border-color); border-radius: 8px; padding: 3px 4px; position: relative; }
			.duty-cal-cell.empty { border: none; }
			.duty-cal-cell.today { border-color: #0F5C55; box-shadow: inset 0 0 0 1px #0F5C55; }
			.duty-cal-cell .dnum { font-size: var(--text-xs); color: var(--text-muted); font-weight: 700; }
			.cbadge { display: inline-block; font-size: 10px; font-weight: 700; border-radius: 6px; padding: 0 5px; margin: 1px 2px 0 0; color: #fff; }
			.cbadge.cmeet, .cdot.cmeet { background: #7c3aed; }
			.cbadge.ctodo, .cdot.ctodo { background: #0F5C55; }
			.duty-day-todo input { margin-right: 6px; vertical-align: -1px; }
			.duty-todo-done { text-decoration: line-through; color: var(--text-muted); }
			.cbadge.cdue, .cdot.cdue { background: #dc2626; }
			.duty-cal-cell:not(.empty) { cursor: pointer; }
			.duty-cal-cell:not(.empty):hover { background: var(--gray-50, #fafafa); }
			.duty-day-row { padding: 8px 4px; border-bottom: 1px dashed var(--border-color); font-size: var(--text-sm); }
			.duty-day-task { cursor: pointer; }
			.duty-day-task:hover { background: var(--gray-50, #fafafa); }
			.duty-day-pending { color: #b45309; font-size: var(--text-xs); font-weight: 700; margin-left: 6px; }
			.duty-day-actions { display: flex; gap: 10px; margin-top: 12px; }
			.cbadge.cres, .cdot.cres { background: #16a34a; }
			.cbadge.chrs, .cdot.chrs { background: #2563eb; }
			.duty-cal-legend { display: flex; gap: 16px; margin-top: 8px; font-size: var(--text-xs); color: var(--text-muted); }
			.cdot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; vertical-align: -1px; }
			.duty-me-open { background: #fff; border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; }
			.duty-me-open h4 { margin: 0 0 8px; }
			.duty-me-row {
				display: grid; grid-template-columns: 74px minmax(0, 1fr) auto 96px;
				align-items: center; gap: 10px; padding: 9px 6px;
				border-bottom: 1px dashed var(--border-color); cursor: pointer;
			}
			.duty-me-row:hover { background: var(--gray-50, #fafafa); }
			.duty-me-title { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
			.duty-me-cust {
				font-size: var(--text-xs); background: #ede9fe; color: #5b21b6;
				border-radius: 99px; padding: 2px 10px; font-weight: 700; white-space: nowrap;
				max-width: 180px; overflow: hidden; text-overflow: ellipsis;
			}
			.duty-me-due { font-size: var(--text-xs); font-weight: 700; color: var(--text-muted); text-align: right; }
			.duty-me-due.duetoday { color: #b45309; }
			.duty-me-due.overdue { color: #dc2626; }
			.duty-me-clock { display: flex; align-items: center; gap: 8px; font-size: var(--text-sm); }
			.duty-me-dot.on { color: #16a34a; }
			.duty-me-dot.off { color: #9ca3af; }
			.duty-me-head { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; }
			.duty-day-move { margin-left: auto; cursor: pointer; color: var(--text-muted); padding: 0 4px; }
			.duty-day-move:hover { color: var(--text-color); }
			@media (max-width: 767px) {
				.duty-me-row { grid-template-columns: 64px minmax(0, 1fr) 84px; }
				.duty-me-cust { display: none; }
			}
			@media (max-width: 767px) { .duty-cal-cell { min-height: 46px; } }
			.duty-mtiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
			.duty-mtile { background: #f0fdfa; border-radius: 12px; padding: 14px 10px; text-align: center; }
			.duty-mtile b { display: block; font-size: 22px; color: #0F5C55; }
			.duty-mtile span { font-size: 11px; color: var(--text-muted); }
						.duty-cr-int { font-size: var(--text-xs); font-weight: 700; align-self: center; white-space: nowrap; }
			.duty-cr-composing-internal textarea { background: #fef9c3; border-color: #d97706; }
			.duty-cr-mem { padding: 6px 0; border-bottom: 1px dashed var(--border-color); display: flex; gap: 8px; align-items: center; }
			.duty-cr-mem a { margin-left: auto; cursor: pointer; font-size: var(--text-xs); }
			.duty-cr-addmem { display: flex; gap: 6px; margin-top: 10px; }
			.duty-cr-joinlink { display: flex; gap: 6px; }
			.duty-cr-approve { color: var(--green-600, #16a34a); font-weight: 700; cursor: pointer; margin-left: auto; }
			.duty-cr-rejectq { color: var(--red-600, #dc2626); font-weight: 700; cursor: pointer; }
			.duty-acad-row { display: flex; gap: 10px; align-items: baseline; padding: 6px 4px; border-bottom: 1px dashed var(--border-color); font-size: var(--text-sm); flex-wrap: wrap; }
			.duty-acad-done { color: #166534; font-weight: 700; font-size: var(--text-xs); }
			.duty-cr-msline { display: flex; flex-direction: column; gap: 4px; font-size: var(--text-sm); margin-bottom: 8px; }
			.duty-cr-msbar { height: 7px; background: var(--bg-light-gray, #f1f5f9); border-radius: 99px; overflow: hidden; }
			.duty-cr-msbar i { display: block; height: 100%; background: #0F5C55; border-radius: 99px; }
			.duty-cr-mswait { color: #b45309; }
			.duty-cr-msmanage { float: right; cursor: pointer; font-size: var(--text-xs); font-weight: 700; }
			.duty-cr-msrow { padding: 8px 4px; border-bottom: 1px dashed var(--border-color); display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
			.duty-cr-msrow.locked { background: #f0fdf4; border-radius: 8px; }
			.duty-cr-mssig { font-size: var(--text-xs); color: #166534; }
			.duty-cr-msacts a { margin-right: 8px; cursor: pointer; font-weight: 700; }
			.duty-cr-msask { color: #b45309; }
			.duty-cr-msask.glow { background: #fef3c7; border-radius: 8px; padding: 2px 8px; }
			.duty-cr-msev { font-size: var(--text-xs); background: var(--bg-light-gray, #f1f5f9); border-radius: 99px; padding: 2px 9px; }
			.duty-cr-msev.ready { background: #dcfce7; color: #166534; font-weight: 700; }
			.duty-cr-msdesc { width: 100%; font-size: var(--text-xs); }
			.duty-cr-meeting {
				display: flex; gap: 8px; align-items: center; font-size: var(--text-sm);
				padding: 4px 0; border-bottom: 1px dashed var(--border-color); flex-wrap: wrap;
			}
			.duty-cr-meeting a { cursor: pointer; font-weight: 700; }
			.duty-cr-mconfirm, .duty-cr-mheld { color: var(--green-600, #16a34a); }
			.duty-cr-mmissed { color: var(--red-600, #dc2626); }
			.duty-cr-mdecline { color: var(--red-600, #dc2626); }
			.duty-cr-cust {
				font-size: var(--text-xs); font-weight: 800; color: var(--text-muted);
				text-transform: uppercase; letter-spacing: 0.04em; margin: 10px 2px 2px;
				cursor: pointer; user-select: none;
			}
			.duty-cr-cust:hover { color: var(--text-color); }
			.duty-cr-caret { display: inline-block; width: 12px; color: var(--text-muted); }
			.duty-renew { font-size: var(--text-xs); border-radius: 99px; padding: 2px 9px; font-weight: 700; white-space: nowrap; }
			.duty-renew-calm { background: #f0fdfa; color: #0f766e; }
			.duty-renew-warn { background: #fef3c7; color: #92400e; }
			.duty-renew-over { background: #fee2e2; color: #b91c1c; }
			.duty-renew-frozen { background: #b91c1c; color: #fff; }
			.duty-cr-unitchip {
				font-size: var(--text-xs); background: var(--bg-light-gray, #f1f5f9);
				border-radius: 99px; padding: 2px 9px; font-weight: 700;
			}
			.duty-cr-joinpill {
				background: #fef3c7; color: #92400e; border-radius: 99px;
				padding: 0 8px; font-size: 10px; font-weight: 700; white-space: nowrap;
			}
			.duty-cr-unread {
				background: var(--red-500, #ef4444); color: #fff; border-radius: 99px;
				padding: 0 7px; font-size: 10px; font-weight: 700;
			}
			.duty-chat-typing, .duty-cr-typing {
				font-size: var(--text-xs); color: var(--text-muted); font-style: italic;
				padding: 2px 4px; min-height: 16px;
			}
			.duty-cr-owner { font-size: var(--text-xs); font-weight: 700; cursor: pointer; color: #b45309; }
			.duty-cr-rename, .duty-cr-delete { cursor: pointer; font-size: var(--text-sm); opacity: 0.55; }
			.duty-cr-rename:hover, .duty-cr-delete:hover { opacity: 1; }
			.duty-cr-lastseen { font-size: var(--text-xs); color: var(--text-muted); }
			.duty-issue-ack { cursor: pointer; font-weight: 700; }
			.duty-cr-reqbadge {
				background: var(--red-500, #ef4444); color: #fff; border-radius: 99px;
				padding: 0 6px; font-size: 10px; font-style: normal;
			}
			@media (max-width: 767px) {
				.duty-clients { flex-direction: column; }
				.duty-cr-list { flex: 1 1 auto; width: 100%; }
				.duty-cr-room { width: 100%; height: auto; }
				.duty-cr-msgs { max-height: 46vh; flex: none; }
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
			.duty-card.collapsed .duty-card-body { display: none; }
			.duty-card-caret { color: var(--text-muted); font-size: var(--text-sm); width: 14px; flex: none; align-self: center; }
			.duty-card-head { cursor: pointer; }
			.duty-card.collapsed { padding-bottom: 10px; }
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
