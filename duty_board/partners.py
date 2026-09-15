"""Partner programme — people who bring Xlevel leads and earn a percentage of
what those clients pay, for the lifetime of the client.

Rules, as agreed (Sept 2026), and where each one lives in code:

- Commission is a percentage of Implementation and Subscription revenue only,
  net of VAT. Which invoice lines count is decided by Duty Settings ›
  Commissionable Items, matched against Item Group and Item Name. Hardware,
  message fees and change requests never count. → _commissionable_lines()
- Commission is earned when the client PAYS, not when we invoice. The
  partner's figures come from submitted Payment Entries allocated to those
  invoices, pro-rated to the commissionable share of each invoice.
  → _earnings_for()
- Lifetime of the client. A Duty Partner Client row is created at conversion
  and only ends when the client itself does. → attribute_on_conversion()
- Attribution is decided by the partner registering the lead from their
  portal — the timestamp is the evidence — and lapses 12 months later if the
  lead has not converted. → partner_lead_add(), LEAD_LAPSE_MONTHS
- The rate is per partner, locked onto the client on the day it converts.
  Changing a partner's rate later affects new conversions only.
- Statements are issued monthly for the previous calendar month:
  every Payment Entry allocation in the month against a commissionable
  invoice of an attributed client becomes a line, once — a line is keyed by
  (payment entry, invoice) and is never statemented twice. Credit notes
  submitted in the month post negative lines in proportion to how much of
  the original invoice had been paid. WHT is deducted at the partner's rate
  (or the Duty Settings default); the net figure is what Xlevel pays.
  → generate_statements(), statement_mark_paid()

Partners are Website Users linked from Duty Partner.user. They see: their
leads, their converted clients (renewal date, invoices, what was paid and
when), and their accrued earnings. Nothing else about anyone.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_first_day, get_last_day, getdate, now_datetime, nowdate, today
from duty_board.permissions import require_staff

LEAD_LAPSE_MONTHS = 12


# ---------------------------------------------------------------- resolver

def _partner():
	"""The calling Website User's partner record. The only door partners have."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	name = frappe.db.get_value("Duty Partner", {"user": user}, "name")
	if not name:
		frappe.throw(_("No partner record is linked to your account — contact Xlevel."), frappe.PermissionError)
	doc = frappe.get_doc("Duty Partner", name)
	if doc.status != "Active":
		frappe.throw(_("Your partner account is not active — contact Xlevel."), frappe.PermissionError)
	return doc


def _partner_lead_owner():
	"""Who at Xlevel owns a lead a partner registers. Settings first, then
	the on-call user, then any manager — a lead with no owner is invisible
	to the pipeline, which is worse than the wrong owner."""
	for fld in ("partner_lead_owner", "on_call_user"):
		u = frappe.db.get_single_value("Duty Settings", fld)
		if u and frappe.db.exists("User", {"name": u, "enabled": 1}):
			return u
	mgrs = frappe.get_all("Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent")
	for u in mgrs:
		if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled"):
			return u
	frappe.throw(_("No staff member is set to receive partner leads — ask Xlevel to set one in Duty Settings."))


def _commissionable_terms():
	raw = frappe.db.get_single_value("Duty Settings", "partner_commissionable") or "Implementation\nSubscription"
	return [t.strip().lower() for t in raw.splitlines() if t.strip()]


def _commissionable_share(invoice_name, terms):
	"""Fraction of an invoice's net amount that is commissionable (0..1)."""
	items = frappe.get_all(
		"Sales Invoice Item", filters={"parent": invoice_name},
		fields=["item_group", "item_name", "net_amount", "amount"])
	total = sum(flt(i.net_amount or i.amount) for i in items)
	if not total:
		return 0.0
	hit = 0.0
	for i in items:
		hay = ((i.item_group or "") + " " + (i.item_name or "")).lower()
		if any(t in hay for t in terms):
			hit += flt(i.net_amount or i.amount)
	return hit / total


def _payments_for(si):
	"""Every settlement of one submitted invoice, as [{ref, date, amount}]
	on the VAT-inclusive basis payments are made on.

	Sources, in order: Payment Entries allocated to it; Journal Entries that
	credit it; the invoice's own paid_amount when it was settled at creation
	(POS-style). If those still fall short of grand_total − outstanding, the
	difference is a residual dated on the invoice — outstanding is the ledger's
	truth and the partner must not lose commission because a receipt was
	recorded some way this code does not know. Refs are unique per invoice so
	statements can key on (ref, invoice)."""
	out = []
	for p in frappe.db.sql("""
		select pe.name as ref, pe.posting_date as date, per.allocated_amount as amount
		from `tabPayment Entry Reference` per
		join `tabPayment Entry` pe on pe.name = per.parent
		where per.reference_doctype = 'Sales Invoice' and per.reference_name = %s and pe.docstatus = 1
		order by pe.posting_date asc""", si.name, as_dict=True):
		if flt(p.amount) > 0:
			out.append({"ref": p.ref, "date": p.date, "amount": flt(p.amount)})
	for j in frappe.db.sql("""
		select je.name as ref, je.posting_date as date, jea.credit_in_account_currency as amount
		from `tabJournal Entry Account` jea
		join `tabJournal Entry` je on je.name = jea.parent
		where jea.reference_type = 'Sales Invoice' and jea.reference_name = %s and je.docstatus = 1
		order by je.posting_date asc""", si.name, as_dict=True):
		if flt(j.amount) > 0:
			out.append({"ref": j.ref, "date": j.date, "amount": flt(j.amount)})
	if flt(si.get("paid_amount")) > 0:
		out.append({"ref": si.name + "/POS", "date": si.posting_date, "amount": flt(si.paid_amount)})
	settled = flt(si.grand_total) - flt(si.outstanding_amount)
	known = sum(x["amount"] for x in out)
	if settled - known > 1:
		out.append({"ref": si.name + "/RECONCILED", "date": si.posting_date, "amount": round(settled - known, 2)})
	elif known - settled > 1:
		# over-counted (a JE and a PE for the same receipt, say): scale to truth
		f = settled / known if known else 0
		for x in out:
			x["amount"] = round(x["amount"] * f, 2)
	return out


def _earnings_for(pclient):
	"""Every submitted invoice for one attributed client, with what has been
	paid, when, and the partner's accrued cut. Cash basis: commission accrues
	on paid amounts only, on the commissionable share, net of VAT."""
	terms = _commissionable_terms()
	rate = flt(pclient.rate) / 100.0
	inv = frappe.get_all(
		"Sales Invoice",
		filters={"customer": pclient.customer, "docstatus": 1, "is_return": 0,
				 "posting_date": [">=", pclient.attributed_on or "1900-01-01"]},
		fields=["name", "posting_date", "due_date", "net_total", "grand_total",
				"outstanding_amount", "status", "paid_amount"],
		order_by="posting_date desc", limit_page_length=0)
	rows, accrued, paid_net_total = [], 0.0, 0.0
	for si in inv:
		share = _commissionable_share(si.name, terms)
		pays = _payments_for(si)
		paid_gross = sum(p["amount"] for p in pays)
		# payments are against the gross (VAT-inclusive) invoice; strip VAT in
		# the same ratio as the invoice's net-to-gross
		net_ratio = flt(si.net_total) / flt(si.grand_total) if flt(si.grand_total) else 0
		paid_net = paid_gross * net_ratio
		cut = paid_net * share * rate
		accrued += cut
		paid_net_total += paid_net * share
		rows.append({
			"invoice": si.name, "date": str(si.posting_date), "due_date": str(si.due_date) if si.due_date else None,
			"net_total": flt(si.net_total), "grand_total": flt(si.grand_total),
			"outstanding": flt(si.outstanding_amount), "status": si.status,
			"commissionable_share": round(share, 4),
			"commissionable_net": round(flt(si.net_total) * share, 2),
			"paid_gross": round(paid_gross, 2),
			"paid_on": str(max(p["date"] for p in pays)) if pays else None,
			"payments": [{"date": str(p["date"]), "amount": p["amount"], "ref": p["ref"]} for p in pays],
			"your_cut": round(cut, 2),
		})
	return rows, round(accrued, 2), round(paid_net_total, 2)


# ---------------------------------------------------------------- portal

@frappe.whitelist()
def partner_me():
	p = _partner()
	clients = frappe.get_all("Duty Partner Client", filters={"partner": p.name, "status": "Active"},
							 fields=["name", "customer", "rate", "attributed_on"])
	# never unpack into `_` here — it is frappe's translator, used below
	accrued = sum(_earnings_for(c)[1] for c in clients)
	open_leads = frappe.db.count("Duty Lead", {"partner": p.name, "status": "Open"})
	won = frappe.db.count("Duty Lead", {"partner": p.name, "status": "Won"})
	sts = frappe.get_all("Duty Partner Statement", filters={"partner": p.name, "status": ["!=", "Void"]},
						 fields=["status", "gross", "net_payable"])
	statemented_gross = sum(flt(x.gross) for x in sts)
	return {
		"partner": p.partner_name, "contact": p.contact_name, "rate": flt(p.rate),
		"since": str(p.agreement_date) if p.agreement_date else None,
		"clients": len(clients), "open_leads": open_leads, "won_leads": won,
		"accrued": round(accrued, 2),
		"paid_out": round(sum(flt(x.net_payable) for x in sts if x.status == "Paid"), 2),
		"awaiting": round(sum(flt(x.net_payable) for x in sts if x.status == "Issued"), 2),
		"unstatemented": round(max(0.0, accrued - statemented_gross), 2),
		"note": _("Accrued is the gross commission on everything your clients have paid. "
				  "Each month it is confirmed on a statement, withholding tax is deducted, and the net is paid to you."),
	}


@frappe.whitelist()
def partner_leads():
	p = _partner()
	rows = frappe.get_all(
		"Duty Lead", filters={"partner": p.name},
		fields=["name", "company", "contact_name", "email", "phone", "stage", "status",
				"value", "expected_close", "closed_on", "partner_registered_on", "erp_customer",
				"next_step", "next_step_due", "modified"],
		order_by="modified desc", limit_page_length=0)
	for r in rows:
		reg = getdate(r.partner_registered_on) if r.partner_registered_on else None
		r.lapses_on = str(add_months(reg, LEAD_LAPSE_MONTHS)) if reg else None
		r.lapsed = bool(reg and r.status == "Open" and getdate(today()) > getdate(r.lapses_on))
		r.value = flt(r.value)
		# staff internals stay inside
		r.pop("modified", None)
	return {"rows": rows}


@frappe.whitelist()
def partner_lead_add(company, contact_name, email=None, phone=None, description=None,
					 value=None, expected_close=None):
	"""A partner registers a lead. The registration timestamp is what settles
	attribution, so it is set here and never editable."""
	p = _partner()
	company = (company or "").strip()
	if not company or not (contact_name or "").strip():
		frappe.throw(_("Company and contact name are required."))
	if not (email or phone):
		frappe.throw(_("Give at least an email or a phone number for the contact."))
	dup = frappe.db.get_value("Duty Lead", {"company": ["like", company], "status": "Open"},
							  ["name", "partner"], as_dict=True)
	if dup and dup.partner and dup.partner != p.name:
		frappe.throw(_("A lead for this company is already registered by another partner."))
	if dup and not dup.partner:
		frappe.throw(_("Xlevel is already in contact with this company, so it cannot be registered as a partner lead. "
					   "If you believe you introduced them first, contact Xlevel."))
	owner = _partner_lead_owner()
	doc = frappe.get_doc({
		"doctype": "Duty Lead", "company": company[:140], "lead_owner": owner,
		"contact_name": contact_name.strip()[:140], "email": (email or "").strip() or None,
		"phone": (phone or "").strip() or None, "description": (description or "").strip()[:2000] or None,
		"value": flt(value) or None, "expected_close": expected_close or None,
		"stage": "New", "status": "Open", "source": "Partner",
		"partner": p.name, "partner_registered_on": now_datetime(),
	})
	doc.insert(ignore_permissions=True)
	frappe.get_doc({"doctype": "Duty Lead Note", "lead": doc.name,
					"note": _("🤝 Registered by partner {0}{1}").format(
						p.partner_name, (" — " + description.strip()[:300]) if description else "")}).insert(ignore_permissions=True)
	try:
		from duty_board.api import _notify_user
		_notify_user(owner, _("New partner lead"), _("{0} registered {1} — it is yours to work").format(p.partner_name, company))
	except Exception:
		pass
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def partner_clients():
	p = _partner()
	out = []
	for c in frappe.get_all("Duty Partner Client", filters={"partner": p.name},
							fields=["name", "customer", "rate", "attributed_on", "status", "lead"],
							order_by="attributed_on desc"):
		rows, accrued, paid_net = _earnings_for(c)
		renewal = None
		try:
			renewal = frappe.db.get_value("Customer", c.customer, "renewal_date")
		except Exception:
			pass
		nxt = [r for r in rows if r["outstanding"] > 0]
		nxt.sort(key=lambda r: r["due_date"] or "9999")
		out.append({
			"customer": c.customer, "rate": flt(c.rate), "since": str(c.attributed_on) if c.attributed_on else None,
			"status": c.status, "renewal_date": str(renewal) if renewal else None,
			"next_due": nxt[0] if nxt else None,
			"invoices": rows, "accrued": accrued, "paid_commissionable_net": paid_net,
			"commissionable_total": round(sum(r["commissionable_net"] for r in rows), 2),
			"commissionable_unpaid": round(max(0.0, sum(r["commissionable_net"] for r in rows) - paid_net), 2),
		})
	return {"rows": out}


# ---------------------------------------------------------------- staff

def attribute_on_conversion(lead_doc, customer):
	"""Called from sales.lead_won_convert. Locks the partner's rate onto the
	new client. Idempotent on customer."""
	partner = lead_doc.get("partner")
	if not partner:
		return None
	if frappe.db.exists("Duty Partner Client", {"customer": customer}):
		return frappe.db.get_value("Duty Partner Client", {"customer": customer}, "name")
	reg = lead_doc.get("partner_registered_on")
	if reg and getdate(reg) < add_months(getdate(today()), -LEAD_LAPSE_MONTHS):
		# lapsed: the lead is Won for Xlevel but earns the partner nothing.
		frappe.get_doc({"doctype": "Duty Lead Note", "lead": lead_doc.name,
						"note": _("⚠ Partner registration lapsed ({0} months) — no attribution.").format(LEAD_LAPSE_MONTHS)}).insert(ignore_permissions=True)
		return None
	rate = frappe.db.get_value("Duty Partner", partner, "rate")
	pc = frappe.get_doc({
		"doctype": "Duty Partner Client", "partner": partner, "customer": customer,
		"lead": lead_doc.name, "rate": flt(rate), "attributed_on": nowdate(), "status": "Active",
	}).insert(ignore_permissions=True)
	return pc.name


@frappe.whitelist()
def partner_invite(name):
	"""Managers: create the partner's portal login and send the welcome mail."""
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	p = frappe.get_doc("Duty Partner", name)
	if p.user and frappe.db.exists("User", p.user):
		return {"user": p.user, "existing": 1}
	email = p.email
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		first = (p.contact_name or p.partner_name).split(" ")[0]
		user = frappe.get_doc({
			"doctype": "User", "email": email, "first_name": first,
			"last_name": " ".join((p.contact_name or "").split(" ")[1:]) or None,
			"user_type": "Website User", "send_welcome_email": 1,
		})
		user.insert(ignore_permissions=True)
	p.db_set("user", user.name, update_modified=False)
	# The welcome mail depends on an outgoing account and the scheduler, so
	# also hand back a set-password link the manager can send by WhatsApp.
	link = None
	try:
		link = user.reset_password(send_email=False)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "partner_invite reset link")
	frappe.db.commit()
	return {"user": user.name, "link": link}


@frappe.whitelist()
def partner_login_link(name):
	"""Managers: a fresh set-password link for an already-invited partner."""
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	p = frappe.get_doc("Duty Partner", name)
	if not p.user or not frappe.db.exists("User", p.user):
		frappe.throw(_("Invite the partner first."))
	link = frappe.get_doc("User", p.user).reset_password(send_email=False)
	frappe.db.commit()
	return {"link": link}


@frappe.whitelist()
def partner_overview():
	"""Managers: every partner with their leads, clients and accrued figure."""
	require_staff()
	out = []
	for p in frappe.get_all("Duty Partner", fields=["name", "partner_name", "status", "rate", "user", "email"],
							order_by="status asc, partner_name asc"):
		clients = frappe.get_all("Duty Partner Client", filters={"partner": p.name, "status": "Active"},
								 fields=["name", "customer", "rate", "attributed_on"])
		accrued = sum(_earnings_for(c)[1] for c in clients)
		sts = frappe.get_all("Duty Partner Statement", filters={"partner": p.name, "status": ["!=", "Void"]},
							 fields=["status", "net_payable"])
		out.append({
			"name": p.name, "partner": p.partner_name, "status": p.status, "rate": flt(p.rate),
			"invited": bool(p.user), "email": p.email,
			"open_leads": frappe.db.count("Duty Lead", {"partner": p.name, "status": "Open"}),
			"won_leads": frappe.db.count("Duty Lead", {"partner": p.name, "status": "Won"}),
			"clients": [c.customer for c in clients], "accrued": round(accrued, 2),
			"awaiting": round(sum(flt(x.net_payable) for x in sts if x.status == "Issued"), 2),
			"paid_out": round(sum(flt(x.net_payable) for x in sts if x.status == "Paid"), 2),
		})
	return {"rows": out}


# ---------------------------------------------------------------- statements

def _wht_rate(partner_name):
	r = frappe.db.get_value("Duty Partner", partner_name, "wht_rate")
	if r is None or flt(r) == 0:
		r = frappe.db.get_single_value("Duty Settings", "partner_wht_rate")
	return flt(r)


def _already_statemented(partner_name):
	"""Set of (payment_entry, invoice) and ('CN', credit_note) keys already on
	a non-void statement, so nothing is ever paid twice."""
	rows = frappe.db.sql("""
		select l.payment_entry, l.invoice, l.kind
		from `tabDuty Partner Statement Line` l
		join `tabDuty Partner Statement` s on s.name = l.parent
		where s.partner = %s and s.status != 'Void'""", partner_name, as_dict=True)
	out = set()
	for r in rows:
		out.add(("CN", r.invoice) if r.kind == "Credit note" else (r.payment_entry, r.invoice))
	return out


def _statement_lines(pclient, start, end, done, terms):
	"""Lines for one attributed client in a period: payments allocated in the
	period, and credit notes submitted in the period."""
	rate = flt(pclient.rate)
	lines = []
	invs = frappe.get_all(
		"Sales Invoice",
		filters={"customer": pclient.customer, "docstatus": 1, "is_return": 0,
				 "posting_date": [">=", pclient.attributed_on or "1900-01-01"]},
		fields=["name", "posting_date", "net_total", "grand_total", "outstanding_amount", "paid_amount"],
		limit_page_length=0)
	for si in invs:
		pays = [p for p in _payments_for(si) if getdate(start) <= getdate(p["date"]) <= getdate(end)]
		if not pays:
			continue
		share = _commissionable_share(si.name, terms)
		if share <= 0:
			continue
		net_ratio = flt(si.net_total) / flt(si.grand_total) if flt(si.grand_total) else 0
		for p in pays:
			if (p["ref"], si.name) in done:
				continue
			paid_net = p["amount"] * net_ratio * share
			lines.append({
				"kind": "Payment", "customer": pclient.customer, "invoice": si.name,
				"payment_entry": p["ref"], "event_date": p["date"],
				"paid_gross": p["amount"], "paid_net": round(paid_net, 2),
				"share": round(share * 100, 2), "rate": rate, "commission": round(paid_net * rate / 100.0, 2),
			})
	# credit notes: reverse commission in proportion to what had been paid on
	# the original. An unpaid original never earned anything, so nothing to reverse.
	cns = frappe.get_all(
		"Sales Invoice",
		filters={"customer": pclient.customer, "is_return": 1, "docstatus": 1,
				 "posting_date": ["between", [start, end]], "return_against": ["is", "set"]},
		fields=["name", "posting_date", "net_total", "return_against"])
	for cn in cns:
		if ("CN", cn.name) in done:
			continue
		orig = frappe.db.get_value("Sales Invoice", cn.return_against, ["net_total", "grand_total", "outstanding_amount"], as_dict=True)
		if not orig or flt(orig.grand_total) <= 0:
			continue
		paid_frac = max(0.0, min(1.0, 1 - flt(orig.outstanding_amount) / flt(orig.grand_total)))
		if paid_frac <= 0:
			continue
		share = _commissionable_share(cn.name, terms)
		if share <= 0:
			continue
		credit_net = abs(flt(cn.net_total)) * share * paid_frac
		lines.append({
			"kind": "Credit note", "customer": pclient.customer, "invoice": cn.name,
			"payment_entry": None, "event_date": cn.posting_date,
			"paid_gross": -abs(flt(cn.net_total)), "paid_net": -round(credit_net, 2),
			"share": round(share * 100, 2), "rate": rate, "commission": -round(credit_net * rate / 100.0, 2),
		})
	return lines


@frappe.whitelist()
def generate_statements(period_end=None, partner=None, dry_run=1, period_start=None):
	"""Managers: one statement per active partner for a period — by default
	the calendar month before this one. Pass period_start and period_end for
	any range (a catch-up from a client's attribution date to today, say).
	Idempotent — payments and credit notes already on a statement are
	skipped, so running it twice produces nothing the second time. Partners
	with no lines get no statement."""
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	dry = cint(dry_run)
	if period_start or period_end:
		end = getdate(period_end) if period_end else getdate(today())
		start = getdate(period_start) if period_start else get_first_day(end)
	else:
		end = get_last_day(add_months(getdate(today()), -1))
		start = get_first_day(end)
	if start > end:
		frappe.throw(_("Period start is after its end."))
	if end > getdate(today()):
		frappe.throw(_("A statement cannot run into the future — payments not yet received cannot be on it."))
	terms = _commissionable_terms()
	filters = {"status": "Active"}
	if partner:
		filters["name"] = partner
	out = []
	for p in frappe.get_all("Duty Partner", filters=filters, fields=["name", "partner_name"]):
		done = _already_statemented(p.name)
		lines = []
		for c in frappe.get_all("Duty Partner Client", filters={"partner": p.name},
								fields=["name", "customer", "rate", "attributed_on", "status"]):
			lines += _statement_lines(c, start, end, done, terms)
		gross = round(sum(l["commission"] for l in lines), 2)
		out.append({"partner": p.partner_name, "lines": len(lines), "gross": gross})
		if not lines or dry:
			continue
		st = frappe.get_doc({
			"doctype": "Duty Partner Statement", "partner": p.name,
			"period_start": str(start), "period_end": str(end), "status": "Issued",
			"issued_on": nowdate(), "wht_rate": _wht_rate(p.name), "lines": lines,
		})
		st.insert(ignore_permissions=True)
		out[-1]["statement"] = st.name
		out[-1]["net_payable"] = st.net_payable
		if frappe.db.get_value("Duty Partner", p.name, "user"):
			try:
				from duty_board.api import _notify_user
				_notify_user(frappe.db.get_value("Duty Partner", p.name, "user"), _("Statement issued"),
							 _("Your statement for {0} to {1} is ready: {2} net of WHT.").format(
								 start, end, frappe.format_value(st.net_payable, {"fieldtype": "Currency"})))
			except Exception:
				pass
	if not dry:
		frappe.db.commit()
	return {"period": [str(start), str(end)], "dry_run": dry, "partners": out}


def generate_statements_job():
	"""Scheduler entry (hooks.py scheduler_events › monthly): statements for
	last month, for real. Runs as Administrator, so the role check is passed
	by calling the engine with the manager gate satisfied."""
	frappe.set_user("Administrator")
	return generate_statements(dry_run=0)


@frappe.whitelist()
def statement_mark_paid(name, paid_on, reference=None):
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	st = frappe.get_doc("Duty Partner Statement", name)
	if st.status != "Issued":
		frappe.throw(_("Only an issued statement can be marked paid."))
	st.status, st.paid_on, st.paid_reference = "Paid", paid_on, reference
	st.save(ignore_permissions=True)
	frappe.db.commit()
	if frappe.db.get_value("Duty Partner", st.partner, "user"):
		try:
			from duty_board.api import _notify_user
			_notify_user(frappe.db.get_value("Duty Partner", st.partner, "user"), _("Commission paid"),
						 _("{0} paid on {1} for {2} to {3}.").format(
							 frappe.format_value(st.net_payable, {"fieldtype": "Currency"}), paid_on, st.period_start, st.period_end))
		except Exception:
			pass
	return {"ok": 1}


@frappe.whitelist()
def partner_statements():
	p = _partner()
	rows = frappe.get_all(
		"Duty Partner Statement", filters={"partner": p.name, "status": ["!=", "Void"]},
		fields=["name", "period_start", "period_end", "status", "gross", "wht_rate", "wht_amount",
				"net_payable", "issued_on", "paid_on", "paid_reference"],
		order_by="period_end desc", limit_page_length=0)
	for r in rows:
		r.lines = frappe.get_all(
			"Duty Partner Statement Line", filters={"parent": r.name},
			fields=["kind", "customer", "invoice", "event_date", "paid_gross", "paid_net", "share", "rate", "commission"],
			order_by="event_date asc")
		for k in ("period_start", "period_end", "issued_on", "paid_on"):
			r[k] = str(r[k]) if r.get(k) else None
		for l in r.lines:
			l.event_date = str(l.event_date) if l.event_date else None
	paid_out = sum(flt(r.net_payable) for r in rows if r.status == "Paid")
	awaiting = sum(flt(r.net_payable) for r in rows if r.status == "Issued")
	return {"rows": rows, "paid_out": round(paid_out, 2), "awaiting": round(awaiting, 2)}


# ---------------------------------------------------------------- Duty Board face (managers)

def _require_manager():
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)


@frappe.whitelist()
def partner_save(name=None, partner_name=None, contact_name=None, email=None, phone=None,
				 rate=None, wht_rate=None, agreement_date=None, notes=None):
	"""Create or edit a partner from the Duty Board Partners face."""
	_require_manager()
	if name:
		doc = frappe.get_doc("Duty Partner", name)
	else:
		doc = frappe.new_doc("Duty Partner")
		doc.status = "Active"
	if partner_name is not None:
		doc.partner_name = (partner_name or "").strip()[:140]
	if contact_name is not None:
		doc.contact_name = (contact_name or "").strip()[:140] or None
	if email is not None:
		if doc.user and (email or "").strip().lower() != (doc.email or ""):
			frappe.throw(_("The portal login is already created on {0}; the email cannot change now.").format(doc.email))
		doc.email = (email or "").strip().lower()
	if phone is not None:
		doc.phone = (phone or "").strip() or None
	if rate is not None and str(rate) != "":
		doc.rate = flt(rate)
	if wht_rate is not None:
		doc.wht_rate = flt(wht_rate) or None
	if agreement_date is not None:
		doc.agreement_date = agreement_date or None
	if notes is not None:
		doc.notes = (notes or "").strip() or None
	if not doc.partner_name or not doc.email:
		frappe.throw(_("Partner name and email are required."))
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def partner_set_status(name, status):
	_require_manager()
	if status not in ("Active", "Suspended", "Ended"):
		frappe.throw(_("Unknown status."))
	frappe.db.set_value("Duty Partner", name, "status", status)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def partner_detail(name):
	"""Everything about one partner for the manager's screen: leads, clients
	with earnings, statements, and the money summary."""
	_require_manager()
	p = frappe.get_doc("Duty Partner", name)
	leads = frappe.get_all(
		"Duty Lead", filters={"partner": p.name},
		fields=["name", "company", "contact_name", "stage", "status", "value", "lead_owner",
				"partner_registered_on", "expected_close", "erp_customer", "next_step", "next_step_due"],
		order_by="modified desc", limit_page_length=0)
	for l in leads:
		reg = getdate(l.partner_registered_on) if l.partner_registered_on else None
		l.lapses_on = str(add_months(reg, LEAD_LAPSE_MONTHS)) if reg else None
		l.lapsed = bool(reg and l.status == "Open" and getdate(today()) > getdate(l.lapses_on))
		l.owner_name = frappe.utils.get_fullname(l.lead_owner) if l.lead_owner else None
		l.partner_registered_on = str(l.partner_registered_on) if l.partner_registered_on else None
	clients = []
	accrued = 0.0
	for c in frappe.get_all("Duty Partner Client", filters={"partner": p.name},
							fields=["name", "customer", "rate", "attributed_on", "status", "lead"],
							order_by="attributed_on desc"):
		rows, a, paid_net = _earnings_for(c)
		accrued += a
		renewal = None
		try:
			renewal = frappe.db.get_value("Customer", c.customer, "renewal_date")
		except Exception:
			pass
		outstanding = sum(r["outstanding"] for r in rows)
		clients.append({
			"name": c.name, "customer": c.customer, "rate": flt(c.rate), "status": c.status,
			"since": str(c.attributed_on) if c.attributed_on else None, "lead": c.lead,
			"renewal_date": str(renewal) if renewal else None,
			"invoices": len(rows), "outstanding": round(outstanding, 2),
			"commissionable_total": round(sum(r["commissionable_net"] for r in rows), 2),
			# same basis as the other columns: net of VAT, commissionable share only
			"commissionable_unpaid": round(max(0.0, sum(r["commissionable_net"] for r in rows) - paid_net), 2),
			"paid_commissionable_net": paid_net, "accrued": a,
		})
	sts = frappe.get_all(
		"Duty Partner Statement", filters={"partner": p.name},
		fields=["name", "period_start", "period_end", "status", "gross", "wht_rate", "wht_amount",
				"net_payable", "issued_on", "paid_on", "paid_reference"],
		order_by="period_end desc", limit_page_length=0)
	for st in sts:
		for k in ("period_start", "period_end", "issued_on", "paid_on"):
			st[k] = str(st[k]) if st.get(k) else None
	statemented = sum(flt(x.gross) for x in sts if x.status != "Void")
	return {
		"partner": {
			"name": p.name, "partner_name": p.partner_name, "contact_name": p.contact_name,
			"email": p.email, "phone": p.phone, "status": p.status, "rate": flt(p.rate),
			"wht_rate": flt(p.wht_rate) if p.wht_rate else None, "effective_wht": _wht_rate(p.name),
			"agreement_date": str(p.agreement_date) if p.agreement_date else None,
			"user": p.user, "notes": p.notes,
		},
		"leads": leads, "clients": clients, "statements": sts,
		"money": {
			"accrued": round(accrued, 2),
			"paid_out": round(sum(flt(x.net_payable) for x in sts if x.status == "Paid"), 2),
			"awaiting": round(sum(flt(x.net_payable) for x in sts if x.status == "Issued"), 2),
			"unstatemented": round(max(0.0, accrued - statemented), 2),
		},
	}


@frappe.whitelist()
def partner_client_add(partner, customer, rate=None, lead=None, from_date=None):
	"""Managers: attribute an existing customer to a partner by hand — for a
	lead that was Won before the partner programme existed. `from_date` is the
	date from which the client's invoices count toward commission: today if
	the partner's involvement starts now, or earlier if they brought the
	client originally. Payments already on a statement are never re-counted."""
	_require_manager()
	if frappe.db.exists("Duty Partner Client", {"customer": customer}):
		frappe.throw(_("{0} is already attributed to a partner.").format(customer))
	r = flt(rate) if rate not in (None, "") else flt(frappe.db.get_value("Duty Partner", partner, "rate"))
	since = getdate(from_date) if from_date else getdate(nowdate())
	if since > getdate(nowdate()):
		frappe.throw(_("The start date cannot be in the future."))
	pc = frappe.get_doc({
		"doctype": "Duty Partner Client", "partner": partner, "customer": customer,
		"lead": lead or None, "rate": r, "attributed_on": str(since), "status": "Active",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": pc.name}
