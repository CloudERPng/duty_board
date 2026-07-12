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

	board.timer = setInterval(() => {
		if (frappe.get_route_str() === "duty-board") board.refresh(true);
	}, 60 * 1000);
};

class DutyBoard {
	constructor(page) {
		this.page = page;
		this.body = $(`
			<div class="duty-board duty-layout">
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
		this.inject_style();
		this.init_chat();
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

		frappe.realtime.on("duty_board_message", (m) => {
			const mine = m.user === frappe.session.user;
			const seen_live = mine || (this.chat_open && !document.hidden);
			this.append_message(m, !seen_live);
			this.scroll_chat();
			if (seen_live) {
				this.mark_caught_up(m.creation);
			} else {
				this.bump_unread();
			}
			if (!mine) {
				const mentioned = (m.mentions || []).includes(frappe.session.user);
				this.ping();
				if (mentioned) setTimeout(() => this.ping(), 250);
				this.desktop_notify(m, mentioned);
			}
		});

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
			if (!document.hidden && this.chat_open) this.mark_caught_up();
		});

		const $notif = $c.find(".duty-chat-notif");
		if (window.Notification && Notification.permission === "default") {
			$notif.show().on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				Notification.requestPermission().then(() => $notif.hide());
			});
		}
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
				<span class="duty-msg-who">${frappe.utils.escape_html(mine ? __("You") : (m.full_name || m.user).split(" ")[0])}</span>
				<span class="duty-msg-text">${this.format_message_text(m)}</span>
				<span class="duty-msg-time">${when}</span>
				<a class="duty-msg-reply" title="${__("Reply")}">↩</a>
				<a class="duty-msg-react" title="${__("React")}">🙂</a>
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
			$row.find(".duty-msg-reply, .duty-msg-react").remove();
		} else {
			$row.find(".duty-msg-reply").on("click", () => this.set_reply(m));
			$row.find(".duty-msg-react").on("click", (e) => {
				e.stopPropagation();
				this.react_picker($row, m.name);
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
					const is_new =
						m.user !== frappe.session.user &&
						!!this.last_seen &&
						m.creation > this.last_seen;
					if (is_new) new_count += 1;
					this.append_message(m, is_new);
				});
				if (!this.last_seen && msgs.length) {
					this.set_seen(msgs[msgs.length - 1].creation);
				}
				this.update_receipts();
				this.scroll_chat();
				if (new_count) {
					if (this.chat_open && !document.hidden) {
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
						$anchor = this.append_message(m, false, false, $anchor);
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
				results.forEach((m) => this.append_message(m, false, true));
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
			const names = readers.map((u) => (this.name_map[u] || u).split(" ")[0]).join(", ");
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
			const names = users.map((u) => (this.name_map[u] || u).split(" ")[0]).join(", ");
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
		document.title = `(${this.unread}) ${this.base_title}`;
	}

	clear_unread() {
		this.unread = 0;
		this.$badge.hide();
		this.$rail.find(".duty-rail-badge").hide();
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
				g.gain.setValueAtTime(0.25, ctx.currentTime + at);
				o.connect(g);
				g.connect(ctx.destination);
				o.start(ctx.currentTime + at);
				g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + at + dur);
				o.stop(ctx.currentTime + at + dur + 0.05);
			};
			tone(880, 0, 0.18);
			tone(1174.66, 0.15, 0.22);
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
			});
		} catch (e) {
			/* ignore */
		}
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
						<button class="btn btn-default duty-switch-btn">${__("Switch Task")}</button>
						<button class="btn btn-primary duty-stop-btn">${__("Stop")}</button>
					</div>
				</div>
			`);
			$task.find(".duty-stop-btn").on("click", () => this.stop_task_flow());
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

	todo_chips(t) {
		let chips = "";
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
							? `<a class="duty-todo-carry" title="${__("Move to tomorrow")}">→</a>`
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

		$plan.html(`
			<div class="duty-plan-card">
				${
					this.overdue_count
						? `<div class="duty-overdue">
							${__("You have {0} unfinished item(s) from previous days.", [this.overdue_count])}
							<button class="btn btn-xs btn-default duty-bring-old">${__("Bring to today")}</button>
						   </div>`
						: ""
				}
				<div class="duty-plan-head">
					<span>${__("My Plan for Today")}
						${todos.length ? `<span class="duty-plan-count">${done}/${todos.length} ${__("done")}</span>` : ""}
					</span>
					<span class="duty-plan-actions">
						${open ? `<a class="duty-carry-all">${__("Carry unfinished → tomorrow")}</a>` : ""}
						<button class="btn btn-xs btn-default duty-todo-more-btn">＋ ${__("More")}</button>
					</span>
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
			</div>
		`);

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
					fieldname: "for_user",
					fieldtype: "Link",
					label: __("For (staff)"),
					options: "User",
					default: frappe.session.user,
					description: __("Pick a colleague to add this to their plan — it will show as from you."),
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
					for_user: values.for_user || null,
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
			const $card = $(`
				<div class="duty-card duty-card-click" title="${__("View {0}'s day", [frappe.utils.escape_html(r.full_name)])}">
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
				.duty-chat-card { height: auto; }
				.duty-chat-list { max-height: 260px; }
				.duty-chat-rail { writing-mode: horizontal-tb; justify-content: center; padding: 8px 14px; width: 100%; }
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
			.duty-msg-text { white-space: pre-wrap; word-break: break-word; }
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
