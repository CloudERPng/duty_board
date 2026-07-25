"""Academy content seed — ZhiftCRM Vol 1 consultant course.

Approved from the red-pen document (25-07-2026). Lessons go live under the
v2.68/2.69 reader; QUESTIONS is inert data until the quiz engine release
consumes it.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_seed.seed_crm_foundations
Idempotent: refuses to run twice.
"""

import frappe

MODULE_TITLE = "ZhiftCRM — Introduction & Platform Foundations"

L = []

L.append(("The operating model", 4, """
<p>ZhiftCRM is a sales-and-fulfilment CRM built for call-centre-led commerce with cash-on-delivery fulfilment — the model that dominates direct-response e-commerce across Nigeria and West Africa. It is not a generic contact database with a pipeline bolted on: every part of it assumes that marketing generates leads, a closer confirms each order by phone, and a field delivery agent takes the goods to the customer and collects payment at the door.</p>
<p><b>The single most useful thing to hold in your head is the operating spine</b>, because every screen, status, and report maps back to it:</p>
<ol>
<li><b>Lead capture</b> — a lead arrives from an online lead form tied to an ad campaign, or is entered by hand from a call, WhatsApp message, or walk-in.</li>
<li><b>Closer confirmation</b> — a closer works the lead, reaches the customer, confirms they genuinely want the order, and firms up product, quantity, price, and delivery address.</li>
<li><b>Dispatch</b> — a delivery agent is assigned and notified, accepts the order, and carries it out.</li>
<li><b>Delivery &amp; collection</b> — the agent delivers and, for COD, collects payment, later reconciled as an agent collection.</li>
</ol>
<p>Everything else in the product — holds, reschedules, the follow-up pool, abandoned-cart recovery — exists to handle the many ways this spine stalls or breaks in the real world. When you meet an unfamiliar feature, ask which break in the spine it repairs.</p>
"""))

L.append(("How a business is structured inside ZhiftCRM", 4, """
<p>A ZhiftCRM tenant is multi-dimensional by design, so one deployment can serve a group running several brands out of several locations:</p>
<ul>
<li><b>Brands and branches</b> — every order is tagged with a brand and a branch, so a single tenant can run multiple retail brands across multiple sites and still report on each cleanly.</li>
<li><b>Categories, with category-first routing</b> — the product category an order is placed under automatically resolves the order's brand and cost centre. Staff never choose a brand by hand.</li>
<li><b>Multi-currency, Naira default</b> — order values carry the order's currency, defaulting to ₦. The country on the order drives the currency.</li>
<li><b>Two people work every order</b> — the closer (owns and confirms it) and the delivery agent (physically delivers it) are tracked and filtered separately everywhere. Keep the two roles distinct in your own explanations.</li>
</ul>
<blockquote><b>CONSULTANT NOTE:</b> Category-first routing is a configuration decision you make with the client during onboarding, not something day-to-day staff touch. Get the category → brand → cost-centre mapping right early: lead forms, manual orders, and every downstream report depend on it. A missing or wrong mapping is one of the most common causes of orders landing under the wrong brand.</blockquote>
<p>ZhiftCRM is managed SaaS on the CloudERP.One platform — clients reach it in a browser at their own tenant address, nothing to install. Administration is split deliberately into two layers: the <b>front office</b> (the everyday app plus a small Settings screen the client's own managers control) and the <b>back office</b> (company details, users, roles, security, pipeline, catalogue, branches, duplicate detection — administered by the implementation team). Knowing that boundary saves you hunting for a setting on the wrong screen.</p>
"""))

L.append(("The role & access model", 4, """
<p>What a person sees and can do is governed entirely by their role, and roles also decide who can see commercially sensitive figures — so mapping the client's real organisation onto these roles is one of the first and most consequential things you do. Roles are assigned in the back office.</p>
<ul>
<li><b>CRM Director</b> — everything: all sections, full report set.</li>
<li><b>CRM Manager</b> — everything: all sections, full report set.</li>
<li><b>CRM Closer</b> — Dashboard, Customers, Agents, Orders, Follow-Up, Call Centre (Call History and Closer Performance only — no live Call-Centre dashboard or settings), Reports, Help, Employee Self Service. Reporting: own summary, product sales, upsell/cross-sell.</li>
<li><b>CRM Marketing Agent</b> — Dashboard, Segments, Campaigns, Journeys, WhatsApp, Reports, Help, Employee Self Service. Marketing report set.</li>
<li><b>Customer Service</b> — treated like a closer for access purposes.</li>
<li><b>AD Buyer</b> — Dashboard, Campaigns, Orders, Reports, Help, Employee Self Service. Ad-buyer report set.</li>
<li><b>Product Manager</b> — the same operational areas as a closer, but with the closer report set plus money visibility (next lesson).</li>
</ul>
<blockquote><b>CONSULTANT NOTE:</b> Build the role map with the client before you create a single user: directors and operations heads → Director/Manager; sales floor → Closer; ad-buying team → AD Buyer; campaign team → Marketing Agent; support → Customer Service. The money-visibility line usually settles who is a Manager versus a Closer — raise it explicitly.</blockquote>
"""))

L.append(("Who sees money, and the Call Centre switch", 3, """
<p>This is the rule consultants are asked about most, and getting it wrong erodes client trust immediately: <b>revenue, spend, and return-on-ad-spend figures are shown only to CRM Directors, CRM Managers, Product Managers, and system administrators.</b> Closers and ad buyers see volume and activity numbers only — never revenue or spend. The Delivered Value Trend on the dashboard is likewise hidden from front-line closer and marketing users.</p>
<blockquote><b>WATCH-OUT:</b> Never promise a client that "everyone can see the sales figures." They cannot, by design, and it is not a per-user checkbox on the front-office Settings screen. If a front-line user genuinely needs to see money, that is a deliberate role decision in the back office — for example a Manager or Product Manager profile.</blockquote>
<p>Independently of role, the <b>Call Centre can be switched off for a person</b>. When it is, they lose every Call Centre screen regardless of what their role would otherwise allow. Treat the role and the Call Centre switch as <b>two gates</b> an order-handling user must pass to reach calling features.</p>
"""))

L.append(("Signing in & account recovery", 3, """
<p>First sign-in and password recovery are the very first support questions every rollout generates, so walk them fluently. The sign-in screen is branded per tenant and has two fields: the first accepts <b>an email address or a username</b> (most staff use their work email); the password is case-sensitive. On success, the user lands on the dashboard for their role.</p>
<p><b>When a sign-in is refused:</b> check for typos and stray spaces, confirm Caps Lock is off, and make sure the most recently set password is being used. If it still fails, use <i>Forgot your password?</i>. If the page will not load at all, the problem is the connection or the web address — not the credentials.</p>
<p><b>Password reset is fully self-service</b> — no administrator needed. From the sign-in screen: Forgot your password? → enter the account email → submit. The reset email carries a link to a Create New Password page with New and Confirm fields that must match.</p>
<blockquote><b>IMPLEMENTATION TIP:</b> The confirmation message is intentionally identical whether or not the email is on file ("if an account exists, reset instructions have been sent"). That is a security feature that stops attackers probing for valid accounts — reassure clients it is deliberate, not a bug.</blockquote>
<blockquote><b>CONSULTANT NOTE:</b> Accounts themselves are created by an administrator or HR, never by the user — provisioning lives in the back office. On tenants using Employee Self Service, a user must be linked to an employee record before parts of the system open for them, so coordinate account creation with HR onboarding.</blockquote>
"""))

L.append(("Reading the dashboard: roles, timeframe, status cards", 4, """
<p>The dashboard answers one question at a glance — what is happening in the business right now — and it is the screen you will use most in a client health check. <b>There is no single dashboard:</b> ad-buying users see a view built around advertising performance, marketing users see campaign activity and lead generation, and everyone else — closers, operations, managers, directors, administrators — sees the default operations dashboard.</p>
<blockquote><b>IMPLEMENTATION TIP:</b> If a client says "my dashboard looks nothing like the manual," your first check is their role, not a bug. An ad-buyer or marketing role explains the difference immediately.</blockquote>
<p>A single <b>timeframe control</b> at the top-right governs every widget on the page: five period-to-date pills — Day, Week, Month, Quarter, Year — defaulting to Month on every load. The subtlety to teach clients: each timeframe runs <b>from the start of the chosen period up to today</b>. There is no "yesterday," no "last month," and no custom range on the dashboard — for a completed prior period, use the Orders list filters or Reports instead.</p>
<p>The row of <b>status cards</b> summarises where orders sit, in two groups: lifecycle cards (waiting, in progress, completed) and performance cards (outcomes and rates). <b>Every card is clickable</b> — a shortcut into the Orders list pre-filtered to exactly the orders behind that number; a closer's click-through narrows to their own orders. That is the fastest path from "that number looks wrong" to the specific orders to act on.</p>
<blockquote><b>CONSULTANT NOTE:</b> The exact set of cards is driven by the system and the timeframe — the row is not a fixed list. Teach clients to read the two groups instead: a build-up in an early lifecycle card means leads are waiting; a build-up mid-flow points to a fulfilment bottleneck.</blockquote>
"""))

L.append(("The insight charts & revenue on the dashboard", 3, """
<p>Below the cards sit three charts. Read them as a set:</p>
<ul>
<li><b>Delivered Value Trend</b> — an area chart of delivered-order value over the timeframe (time across, ₦ up). This is the revenue view.</li>
<li><b>Outcome Breakdown</b> — a bar chart counting orders by how they turned out: Assigned, Delivered, Cancelled, Failed, Returned. Healthy means a tall Delivered bar relative to the negatives.</li>
<li><b>Status Distribution</b> — a donut of the share of orders in each status, including in-progress, so bunching at a stage is visible at a glance.</li>
</ul>
<p>A flat Delivered Value Trend alongside a large in-progress segment usually means value is waiting to be realised as orders complete — <b>not</b> that sales have stopped.</p>
<p>Consistent with the access model: the Delivered Value Trend is hidden for front-line closer and marketing users and shown to managers, directors, and administrators. The operations dashboard also deliberately omits period-over-period comparison tiles, channel-mix breakdowns, top-product tables, and agent leaderboards — those live on the Marketing and Ad-Buyer dashboards.</p>
"""))

L.append(("Front-office Settings: channels, scoring weights, SLAs", 5, """
<p>The front-office Settings screen is deliberately small — one screen of three cards a client's own managers control: <b>Communication Channels, Lead Scoring Weights, and Service SLAs</b>. They are genuine behavioural levers, so they belong on your onboarding checklist. Changes are <b>not live until Save settings is pressed</b>; the button stays disabled until something changes and signals unsaved changes — so a client who "changed a setting and nothing happened" has almost always not saved.</p>
<p><b>Communication Channels</b> turns each way of reaching customers on or off system-wide: Email, SMS, WhatsApp, Push, and the Call Centre. Two specifics: the <b>WhatsApp switch is gated</b> — it cannot be turned on until a WhatsApp Business account is connected (it reads Not connected until then; Manage opens the connection panel). And the Call Centre switch here is far-reaching: off removes Call Centre access across the system, tying back to the per-person gate you met earlier.</p>
<p><b>Lead Scoring Weights</b> decide how a customer's 0–1 priority score is blended from three factors: Engagement (how actively they interact), Monetary (how much they are worth), and Recency (how recently they were active). <b>The three weights must sum to exactly 1.0</b> — a badge shows the running total, green at 1.0, amber when off. Example: 0.40 / 0.35 / 0.25 emphasises activity first, then value, then recency.</p>
<blockquote><b>IMPLEMENTATION TIP:</b> Treat the weights as a client conversation, not a default to leave alone. A repeat-purchase business usually leans on Monetary and Recency; a top-of-funnel, high-volume acquisition business leans on Engagement and Recency. Set them deliberately at onboarding, confirm the badge is green before leaving the screen, and revisit after the first month of real data.</blockquote>
<p><b>Service SLAs</b> set two time targets, both in minutes: First response and Resolution. They are single, <b>system-wide</b> targets — not per-priority-level.</p>
<blockquote><b>CONSULTANT NOTE:</b> Guide clients toward targets they can realistically hit most of the time: too tight produces constant misses and a demoralised team; too loose and issues drift unnoticed. Pick numbers against actual staffing, then review as workload changes.</blockquote>
"""))

L.append(("The back-office boundary & the shared vocabulary", 3, """
<p>So you never hunt for a control on the wrong screen: the following are all <b>back-office administration, never front-office Settings</b> — company name, logo, language, timezone, currency and date formats; user accounts (creating, editing, deactivating, password resets); roles and access; security policy; order pipeline stages, channels, product catalogue, and branches; and duplicate-order detection. When a client asks to change any of these, it is an administrator task.</p>
<p><b>The vocabulary the rest of the library assumes:</b></p>
<ul>
<li><b>Closer</b> — the sales person who owns and works an order, confirms it with the customer, drives it to delivery.</li>
<li><b>Delivery agent</b> — the field staff member who delivers and, for COD, collects payment.</li>
<li><b>Digital marketer</b> — the person credited with generating a lead; every lead form and its submissions are attributed to one.</li>
<li><b>Category-first routing</b> — the category resolves an order's brand and cost centre automatically.</li>
<li><b>Lead form / Submission</b> — a hosted online order form tied to a campaign; a submission is the raw lead it captures, awaiting conversion.</li>
<li><b>Follow-up pool</b> — a shared workspace of stalled orders that a dedicated team claims and works.</li>
<li><b>COD / Collection</b> — cash on delivery; a collection is the reconciliation record of cash an agent has collected.</li>
<li><b>Lead score</b> — the 0–1 priority score blending Engagement, Monetary, Recency by the Settings weights.</li>
<li><b>Tenant / workspace</b> — one client's isolated deployment; its name shows top-left in the app shell.</li>
</ul>
"""))

LESSONS = L

# (question, [4 options], correct index, rationale, source) — consumed by the quiz engine release.
QUESTIONS = [
	("The ZhiftCRM operating spine, in order, is:", ["Lead capture → dispatch → closer confirmation → delivery & collection", "Lead capture → closer confirmation → dispatch → delivery & collection", "Closer confirmation → lead capture → dispatch → delivery & collection", "Dispatch → lead capture → closer confirmation → delivery & collection"], 1, "The spine is capture, confirm, dispatch, deliver-and-collect; every screen and status maps back to it.", "§1.1"),
	("Features like holds, the follow-up pool, and abandoned-cart recovery exist primarily to:", ["Replace the closer's role", "Handle the ways the operating spine stalls or breaks", "Generate additional leads", "Reconcile agent collections"], 1, "Everything beyond the spine exists to repair its real-world breakages.", "§1.1"),
	("Category-first routing automatically resolves which two things from an order's product category?", ["Closer and delivery agent", "Brand and cost centre", "Currency and country", "Branch and warehouse"], 1, "The category resolves brand and cost centre so staff never pick a brand by hand.", "§1.2"),
	("Who configures the category → brand → cost-centre mapping, and when?", ["Day-to-day staff, per order", "The consultant with the client, during onboarding", "The customer, at checkout", "The delivery agent, at dispatch"], 1, "It is an onboarding configuration decision; a wrong mapping is a common cause of orders under the wrong brand.", "§1.2"),
	("What drives an order's currency?", ["The brand on the order", "The country on the order", "The closer's profile", "The branch's timezone"], 1, "Country on the order drives currency, defaulting to ₦.", "§1.2"),
	("The two people tracked and filtered separately on every order are:", ["Closer and digital marketer", "Closer and delivery agent", "Manager and closer", "Delivery agent and customer"], 1, "The closer owns the sale; the agent delivers and collects — kept distinct throughout the system.", "§1.2"),
	("A client asks you to create three new user accounts. Where does that happen?", ["The front-office Settings screen", "The back office", "The user's own profile page", "The dashboard"], 1, "User accounts, roles, and security are back-office administration — never front-office Settings.", "§1.3, §5.5"),
	("Which two roles reach everything, including the full report set?", ["CRM Director and CRM Closer", "CRM Director and CRM Manager", "CRM Manager and Product Manager", "CRM Director and AD Buyer"], 1, "Director and Manager both reach all sections and all reports.", "§2.1"),
	("Within the Call Centre area, a CRM Closer can reach:", ["The live Call-Centre dashboard and settings", "Call History and Closer Performance only", "Nothing at all", "Everything a Manager can"], 1, "Closers get Call History and Closer Performance; no live dashboard, no settings.", "§2.1"),
	("For access purposes, the Customer Service profile is treated like:", ["A manager", "A closer", "An ad buyer", "A marketing agent"], 1, "Customer Service is closer-equivalent for access.", "§2.1"),
	("What distinguishes a Product Manager from a CRM Closer?", ["A completely different set of screens", "The same operational areas, but with money visibility", "Access to Journeys and Segments", "Nothing — they are identical"], 1, "Product Managers work closer-like areas but are inside the money-visibility circle.", "§2.1, §2.2"),
	("Revenue, spend, and ROAS figures are visible to which set of users?", ["Everyone", "Directors, Managers, Product Managers, and system administrators", "Closers and ad buyers", "Anyone the client ticks a checkbox for in Settings"], 1, "Money is shown only to that set; closers and ad buyers see volume and activity only.", "§2.2"),
	("A client insists one of their sales-floor closers must see revenue figures. The correct response is:", ["Tick the per-user option in front-office Settings", "Explain it is a deliberate role decision made in the back office — e.g. a Manager or Product Manager profile", "Tell them it is impossible for anyone", "Turn on the Call Centre switch for that user"], 1, "There is no per-user checkbox; visibility follows role, changed deliberately in the back office.", "§2.2"),
	("A user's role allows the Call Centre, but their Call Centre switch is off. They can reach:", ["Only Call History", "All calling features, since the role allows it", "No Call Centre screens at all", "Only the live Call-Centre dashboard"], 2, "Role and switch are two gates — the switch off removes every Call Centre screen regardless of role.", "§2.3"),
	("The first field of the sign-in screen accepts:", ["Email address only", "Username only", "An email address or a username", "A phone number"], 2, "Either works; most staff use their work email.", "§3.1"),
	("A user cannot sign in but the page loads fine. Which of these is NOT part of the first-line checklist?", ["Check for typos and stray spaces", "Confirm Caps Lock is off", "Use the most recently set password", "Ask an administrator to reset the account for them"], 3, "Reset is self-service via Forgot your password? — no administrator needed at first line.", "§3.1, §3.2"),
	("After submitting a password-reset request, the confirmation message is identical whether or not the email exists. Why?", ["A known bug awaiting a fix", "To stop attackers probing for valid accounts", "To save on email costs", "Because the system cannot check"], 1, "It is a deliberate security feature — reassure clients accordingly.", "§3.2"),
	("On tenants using Employee Self Service, what must exist before parts of the system open for a new user?", ["A WhatsApp Business connection", "A link between the user and an employee record", "A completed first order", "A password older than 24 hours"], 1, "Coordinate account creation with HR onboarding — the user must be linked to an employee record.", "§3, note"),
	("A client complains their dashboard \u201clooks nothing like the manual.\u201d Your first check is:", ["Their browser version", "Their role", "The tenant's timezone", "The timeframe pill"], 1, "Ad-buyer and marketing roles get different dashboards; role explains it immediately.", "§4.1"),
	("The dashboard timeframe control offers:", ["Day, Week, Month, Quarter, Year — period-to-date, defaulting to Month", "Custom date ranges", "Yesterday and Last Month presets", "A per-widget timeframe"], 0, "Five period-to-date pills, Month default, one control governing every widget.", "§4.2"),
	("A client wants dashboard numbers for last month (the completed period). You should:", ["Change the Month pill — it shows last month", "Use the Orders list filters or the Reports section", "Ask support to enable custom ranges", "Read the Quarter pill instead"], 1, "Dashboard timeframes are strictly period-to-date; completed prior periods live in Orders filters or Reports.", "§4.2"),
	("Clicking a status card on the dashboard:", ["Opens a help article", "Opens the Orders list pre-filtered to exactly those orders", "Refreshes the page", "Downloads a CSV"], 1, "Cards are shortcuts into the pre-filtered Orders list — for a closer, narrowed to their own orders.", "§4.3"),
	("The status-card row on a client's dashboard has changed since last month. This means:", ["A defect to report", "Nothing unusual — the card set is driven by the system and timeframe, not fixed", "Their licence downgraded", "Their role changed"], 1, "The row is not a fixed list; teach the two groups (lifecycle vs performance) instead of memorising cards.", "§4.3"),
	("The three operations-dashboard insight charts are:", ["Delivered Value Trend, Outcome Breakdown, Status Distribution", "Revenue, Conversion, Leaderboard", "Channel Mix, Top Products, Agent League", "Leads, Calls, Deliveries"], 0, "Area trend of delivered value, outcome bars, and a status donut.", "§4.4"),
	("A flat Delivered Value Trend beside a large in-progress segment in the Status Distribution usually means:", ["Sales have stopped", "Value is waiting to be realised as in-progress orders complete", "The chart is broken", "Revenue visibility is off"], 1, "Read the charts as a set — value is queued, not absent.", "§4.4"),
	("A manager changed a Settings value and \u201cnothing happened.\u201d The most likely cause is:", ["A caching bug", "They did not press Save settings", "Their role blocks Settings", "The tenant is frozen"], 1, "Changes are not live until Save settings; the button signals unsaved changes.", "§5.1"),
	("The WhatsApp channel switch cannot be enabled because:", ["It requires a Director role", "No WhatsApp Business account is connected yet", "SMS must be enabled first", "The tenant is outside Nigeria"], 1, "WhatsApp is gated on a connected Business account; until then it reads Not connected.", "§5.2"),
	("The three lead-scoring weights must:", ["Each be at least 0.2", "Sum to exactly 1.0", "Sum to 100", "Be equal"], 1, "The badge shows the running total — green at exactly 1.0, amber otherwise.", "§5.3"),
	("For a repeat-purchase business, the recommended lean in scoring weights is toward:", ["Engagement and Monetary", "Monetary and Recency", "Engagement only", "Recency only"], 1, "Repeat-purchase leans Monetary + Recency; high-volume acquisition leans Engagement + Recency.", "§5.3, tip"),
	("The Service SLA card sets:", ["Per-priority response targets in hours", "Two system-wide targets in minutes: First response and Resolution", "One target per closer", "Targets per communication channel"], 1, "Two single, system-wide minute targets — not per priority level.", "§5.4"),
]


def seed_crm_foundations():
	if frappe.db.exists("Duty Training Module", {"title": MODULE_TITLE}):
		print(f"'{MODULE_TITLE}' already exists — nothing done.")
		return
	mod = frappe.get_doc(
		{
			"doctype": "Duty Training Module",
			"title": MODULE_TITLE,
			"product": "ZhiftCRM",
			"description": "Volume 1 of the consultant enablement library: the operating model, roles and money visibility, sign-in, the dashboard, and the front-office configuration levers.",
			"active": 1,
			"audience": "Consultant",
			"sort_order": 1,
			"pass_mark": 70,
		}
	).insert(ignore_permissions=True)
	for i, (title, mins, html) in enumerate(LESSONS):
		frappe.get_doc(
			{
				"doctype": "Duty Lesson",
				"module": mod.name,
				"title": title,
				"sort_order": i,
				"est_minutes": mins,
				"content": html.strip(),
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"Seeded '{MODULE_TITLE}' with {len(LESSONS)} lessons (module {mod.name}). Question bank ({len(QUESTIONS)} questions) staged for the quiz engine release.")


def seed_crm_foundations_questions():
	"""Load the Vol 1 question bank. Idempotent per module."""
	mod = frappe.db.get_value("Duty Training Module", {"title": MODULE_TITLE}, "name")
	if not mod:
		print("Module not found — run seed_crm_foundations first.")
		return
	if frappe.db.count("Duty Quiz Question", {"module": mod}):
		print("Question bank already loaded — nothing done.")
		return
	for q, opts, ans, why, src in QUESTIONS:
		frappe.get_doc(
			{
				"doctype": "Duty Quiz Question",
				"module": mod,
				"question": q,
				"opt_a": opts[0],
				"opt_b": opts[1],
				"opt_c": opts[2],
				"opt_d": opts[3],
				"correct": "ABCD"[ans],
				"rationale": why,
				"source": src,
				"active": 1,
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"Loaded {len(QUESTIONS)} questions for '{MODULE_TITLE}'.")
