"""Personal money — accounts, movements, standing orders and the shortfall watch.

SYSADMIN ONLY. This is one person's private finances sitting inside a shared
business tool, so every endpoint calls require_sysadmin rather than relying on
a hidden menu. A hidden rail entry is not a permission.

THREE DECISIONS THAT SHAPE EVERYTHING ELSE.

  NO BALANCE IS EVER STORED. Every figure is opening balance plus the movements
  since, computed on read. A stored balance drifts the first time anything is
  edited, deleted or back-dated, and then quietly lies — which in a personal
  ledger is worse than being slow.

  CURRENCIES ARE NEVER SILENTLY ADDED TOGETHER. Totals are per currency. Where a
  single figure is wanted, the rate is supplied and shown with its date, so a
  converted number is always visibly an estimate rather than a fact. A cross-
  currency transfer records both real amounts rather than deriving one from a
  rate — because the rate you actually got is not the rate anybody published.

  THE FORECAST IS PESSIMISTIC ON PURPOSE. It counts money leaving in the window
  and only counts money arriving where that arrival is itself a standing order.
  Salary and client payments are not projected, because a warning that assumes
  income you have not received is not a warning.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

from duty_board.permissions import require_sysadmin

WINDOW_DAYS = 7

FREQ_DAYS = {"Weekly": 7, "Fortnightly": 14}
FREQ_MONTHS = {"Monthly": 1, "Quarterly": 3, "Yearly": 12}


def _category(name, kind="Spending"):
	"""Category is a Link now, so anything written here must exist as a record."""
	if not frappe.db.exists("Duty Money Category", name):
		try:
			frappe.get_doc({"doctype": "Duty Money Category",
							"category_name": name, "kind": kind}).insert(ignore_permissions=True)
		except Exception:
			return None
	return name


def _next_after(d, frequency):
	d = getdate(d)
	if frequency in FREQ_DAYS:
		return add_days(d, FREQ_DAYS[frequency])
	return add_months(d, FREQ_MONTHS.get(frequency, 1))


def _balances(as_of=None):
	"""{account: balance} from opening plus every movement, in three queries.

	Never per account — this stays the same cost at four accounts or forty.
	"""
	accounts = frappe.get_all(
		"Duty Bank Account",
		fields=["name", "opening_balance", "opening_date", "currency"],
		limit_page_length=0,
	)
	bal = {a.name: flt(a.opening_balance) for a in accounts}
	filters = {}
	if as_of:
		filters["move_date"] = ["<=", as_of]
	moves = frappe.get_all(
		"Duty Money Move",
		filters=filters,
		fields=["account", "to_account", "kind", "amount", "amount_received"],
		limit_page_length=0,
	)
	for m in moves:
		amt = flt(m.amount)
		if m.kind in ("In", "Growth"):
			# Growth raises the balance exactly as a deposit does — the difference
			# is only in what it means, so it is separated for reporting rather
			# than for arithmetic. A fall is entered negative.
			bal[m.account] = bal.get(m.account, 0) + amt
		elif m.kind == "Out":
			bal[m.account] = bal.get(m.account, 0) - amt
		elif m.kind == "Transfer":
			bal[m.account] = bal.get(m.account, 0) - amt
			if m.to_account:
				# the received amount is what actually landed; it differs from the
				# sent amount whenever the two accounts hold different currencies
				got = flt(m.amount_received) or amt
				bal[m.to_account] = bal.get(m.to_account, 0) + got
	return bal


@frappe.whitelist()
def overview(rates=None):
	"""Everything the money screen needs, in one call.

	rates is an optional {"GBP": 2000} map for the converted headline. Absent, no
	converted total is offered — a made-up rate is worse than no total.
	"""
	require_sysadmin()
	today = nowdate()
	bal = _balances()

	banks = {
		b.name: b
		for b in frappe.get_all(
			"Duty Bank", fields=["name", "bank_name", "country", "colour", "active"],
			limit_page_length=0,
		)
	}
	accounts = frappe.get_all(
		"Duty Bank Account",
		filters={"active": 1},
		fields=["name", "nickname", "bank", "account_type", "currency",
				"opening_balance", "opening_date", "target_balance", "credit_limit",
				"account_no", "sort_order", "note"],
		order_by="sort_order asc, nickname asc",
		limit_page_length=0,
	)

	# standing orders due inside the window, grouped by the account they hit
	horizon = add_days(today, WINDOW_DAYS)
	# Every order, paused included — the list exists to show what you have set
	# up, and a paused one you cannot see is one you cannot resume. `active` must
	# be SELECTED as well as filtered on: it was filtered and not selected, so
	# the browser saw undefined on every row and drew all of them as paused.
	orders = frappe.get_all(
		"Duty Standing Order",
		fields=["name", "title", "from_account", "to_account", "amount", "active",
				"frequency", "next_date", "auto_post", "counterparty", "last_posted"],
		order_by="active desc, next_date asc",
		limit_page_length=0,
	)
	out_soon, in_soon = {}, {}
	due_list = []
	for o in orders:
		if not o.next_date:
			continue
		# a paused order is shown but never counted toward what is due or
		# committed against an account — it is not going to run
		if not cint(o.active):
			continue
		o.overdue = str(o.next_date) < today
		o.due_in = frappe.utils.date_diff(o.next_date, today)
		if str(o.next_date) <= str(horizon):
			out_soon[o.from_account] = out_soon.get(o.from_account, 0) + flt(o.amount)
			if o.to_account:
				in_soon[o.to_account] = in_soon.get(o.to_account, 0) + flt(o.amount)
			due_list.append(o)

	# contributions and growth apart, so an investment can show a real return
	flows = {}
	for r in frappe.db.sql(
		"""select account, kind, sum(amount) as amt
		   from `tabDuty Money Move` group by account, kind""",
		as_dict=True,
	):
		flows.setdefault(r.account, {})[r.kind] = flt(r.amt)
	for r in frappe.db.sql(
		"""select to_account as account, sum(coalesce(nullif(amount_received,0), amount)) as amt
		   from `tabDuty Money Move` where kind='Transfer' and to_account is not null
		   group by to_account""",
		as_dict=True,
	):
		flows.setdefault(r.account, {})["TransferIn"] = flt(r.amt)

	rows = []
	for a in accounts:
		b = banks.get(a.bank) or frappe._dict()
		a.balance = flt(bal.get(a.name, 0))
		a.bank_name = b.get("bank_name") or a.bank
		a.colour = b.get("colour") or "#0F5C55"
		a.country = b.get("country")
		a.committed = flt(out_soon.get(a.name, 0))
		a.incoming = flt(in_soon.get(a.name, 0))
		# what is left once the window's standing orders have run
		a.projected = a.balance - a.committed + a.incoming
		a.short_by = max(0.0, -a.projected) if a.committed else 0.0
		a.at_risk = 1 if a.committed and a.projected < 0 else 0
		if a.target_balance:
			a.target_pct = min(100, int(a.balance * 100 / flt(a.target_balance))) if flt(a.target_balance) else 0
		# A credit card is a liability. Its balance is what is owed, so it counts
		# AGAINST the total rather than toward it, and the useful figure on the
		# card is what is left of the limit rather than what has been spent.
		f = flows.get(a.name, {})
		a.growth = flt(f.get("Growth", 0))
		# what you actually put in: opening, deposits and transfers in, less what
		# you took out — growth deliberately excluded, since it is the return
		a.contributed = (flt(a.opening_balance) + flt(f.get("In", 0))
						 + flt(f.get("TransferIn", 0)) - flt(f.get("Out", 0))
						 - flt(f.get("Transfer", 0)))
		a.grows = 1 if a.account_type in ("Investment", "Savings") else 0
		a.return_pct = (round(a.growth * 100 / a.contributed, 1)
						if a.grows and a.contributed > 0 and a.growth else None)
		a.is_credit = 1 if a.account_type == "Credit Card" else 0
		# A loan is a debt like a card, but it is repaid rather than revolved:
		# the balance is stored negative and climbs toward zero, so the progress
		# worth showing is how much of the original has been cleared.
		a.is_loan = 1 if a.account_type == "Loan" else 0
		if a.is_loan:
			a.owed = abs(min(0.0, flt(a.balance)))
			orig = flt(a.limit) or None
			a.paid_off = max(0.0, orig - a.owed) if orig else None
			a.paid_pct = (round(a.paid_off * 100 / orig, 1)
						  if (orig and orig > 0) else None)
		if a.is_credit:
			a.owed = abs(a.balance)
			a.limit = flt(a.credit_limit)
			a.available = max(0.0, a.limit - a.owed) if a.limit else None
			a.used_pct = min(100, int(a.owed * 100 / a.limit)) if a.limit else None
		rows.append(a)

	by_currency = {}
	for a in rows:
		c = by_currency.setdefault(a.currency, {"currency": a.currency, "total": 0.0,
												"projected": 0.0, "accounts": 0,
												"cash": 0.0, "cash_accounts": 0,
												"invested": 0.0, "invested_accounts": 0,
												"owed": 0.0, "available": 0.0})
		if a.is_credit:
			# shown apart as well as netted, because "I have X and owe Y" is the
			# thing you actually want to know
			c["owed"] += a.owed
			c["available"] += flt(a.available or 0)
			c["total"] -= a.owed
			c["projected"] -= a.owed
		elif a.is_loan:
			# owed, not held — it reduces the currency total like a card does
			c["owed"] += a.owed
			c["total"] -= a.owed
			c["projected"] -= a.owed
		elif a.account_type == "Investment":
			# Investments were being added to the cash line, so a naira total of
			# 18.8m read as spendable when 18.8m of it was pension. Money you
			# could spend today and money locked in a fund are not the same
			# number and must not share one.
			c["invested"] += a.balance
			c["invested_accounts"] += 1
			c["total"] += a.balance
			c["projected"] += a.projected
		else:
			c["cash"] += a.balance
			c["cash_accounts"] += 1
			c["total"] += a.balance
			c["projected"] += a.projected
		c["accounts"] += 1

	converted = None
	rate_map = frappe.parse_json(rates) if isinstance(rates, str) else (rates or None)
	if rate_map:
		base = rate_map.get("__base") or "NGN"
		tot = 0.0
		ok = True
		for c in by_currency.values():
			if c["currency"] == base:
				tot += c["total"]
			elif rate_map.get(c["currency"]):
				tot += c["total"] * flt(rate_map[c["currency"]])
			else:
				ok = False
		converted = {"base": base, "total": tot, "complete": ok} if ok or tot else None

	recent = frappe.get_all(
		"Duty Money Move",
		fields=["name", "move_date", "kind", "account", "to_account", "amount",
				"amount_received", "category", "counterparty", "note", "standing_order"],
		order_by="move_date desc, creation desc",
		limit_page_length=25,
	)
	names = {a.name: a.nickname for a in accounts}
	cur = {a.name: a.currency for a in accounts}
	for r in recent:
		r.account_name = names.get(r.account, r.account)
		r.to_name = names.get(r.to_account) if r.to_account else None
		r.currency = cur.get(r.account)
		r.to_currency = cur.get(r.to_account) if r.to_account else None

	for o in orders:
		o.from_name = names.get(o.from_account, o.from_account)
		o.to_name = names.get(o.to_account) if o.to_account else None
		o.currency = cur.get(o.from_account)

	# shares ride along on the same call — the card sits beside the currency
	# totals, so fetching it separately would mean the page renders complete and
	# then jumps
	try:
		from duty_board.shares import portfolio_summary

		shares = portfolio_summary()
	except Exception:
		shares = []

	# bonds ride along too, on their own line rather than folded into shares:
	# an equity position and a bond held to maturity are different decisions and
	# a single "investments" figure would hide the split
	try:
		from duty_board.bonds import bond_summary

		bond_rows = bond_summary()
	except Exception:
		bond_rows = []

	return {
		"shares": shares,
		"bonds": bond_rows,
		"accounts": rows,
		"by_currency": sorted(by_currency.values(), key=lambda x: -x["total"]),
		"converted": converted,
		"due": due_list,
		"orders": orders,
		"recent": recent,
		"window": WINDOW_DAYS,
		"today": today,
	}


@frappe.whitelist()
def move_money(kind, account, amount, move_date=None, to_account=None,
			   amount_received=None, category=None, counterparty=None, note=None):
	"""Record money in, out, or between accounts."""
	require_sysadmin()
	if kind not in ("In", "Out", "Transfer", "Growth"):
		frappe.throw(_("Unknown kind."))
	# Growth alone may be negative — a portfolio can fall, and recording that is
	# the point. Everything else has a direction already, so a negative there
	# would silently mean the opposite of what was intended.
	if kind == "Growth":
		if flt(amount) == 0:
			frappe.throw(_("A value change of nothing is not a change."))
	elif flt(amount) <= 0:
		frappe.throw(_("Amount has to be more than nothing."))
	if kind == "Transfer":
		if not to_account:
			frappe.throw(_("A transfer needs an account to go into."))
		if to_account == account:
			frappe.throw(_("That is the same account."))
	doc = frappe.get_doc({
		"doctype": "Duty Money Move",
		"move_date": move_date or nowdate(),
		"kind": kind,
		"account": account,
		"to_account": to_account if kind == "Transfer" else None,
		"amount": flt(amount),
		"amount_received": flt(amount_received) or None,
		"category": category,
		"counterparty": counterparty,
		"note": note,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def delete_move(name):
	require_sysadmin()
	frappe.delete_doc("Duty Money Move", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def post_standing_order(name, on_date=None, force=0):
	"""Run one standing order now and roll it to its next date.

	Refused where the account will not cover it, because none of these accounts
	has an overdraft and the bank would have refused too. `force` exists for the
	case where it genuinely did go through — a facility arranged since, a credit
	that has not been recorded yet — since a ledger that will not record what
	happened is worse than one that questions it.
	"""
	require_sysadmin()
	o = frappe.get_doc("Duty Standing Order", name)
	when = on_date or o.next_date or nowdate()
	if not cint(force):
		bal, ok = _funds_available(o.from_account, o.amount, when)
		if not ok:
			frappe.throw(
				_("{0} holds {1} on {2} and this needs {3}. None of your accounts has an overdraft, so this transfer would have failed at the bank. Record the money going in first, or post it anyway if it really did go through.").format(
					o.from_account, flt(bal), when, flt(o.amount)),
				title=_("Not enough in the account"),
				exc=InsufficientFunds)
	frappe.get_doc({
		"doctype": "Duty Money Move",
		"move_date": when,
		"kind": "Transfer" if o.to_account else "Out",
		"account": o.from_account,
		"to_account": o.to_account or None,
		"amount": flt(o.amount),
		"category": _category("Standing order", "Fixed cost"),
		"counterparty": o.counterparty or o.title,
		"note": o.title,
		"standing_order": o.name,
	}).insert(ignore_permissions=True)
	o.last_posted = when
	o.next_date = _next_after(when, o.frequency)
	o.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "next_date": str(o.next_date)}


@frappe.whitelist()
def skip_standing_order(name):
	"""Roll a standing order forward without posting it — the month it did not run."""
	require_sysadmin()
	o = frappe.get_doc("Duty Standing Order", name)
	o.next_date = _next_after(o.next_date or nowdate(), o.frequency)
	o.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "next_date": str(o.next_date)}


def run_due_standing_orders():
	"""Post anything due today or earlier that is set to post automatically.

	A standing order executes at the bank whether or not anybody opens this app,
	so the ledger mirrors that rather than waiting to be told. Anything left off
	auto_post waits for a confirmation instead.

	cron: 0 6 * * *
	"""
	today = nowdate()
	unpaid = []
	for name in frappe.get_all(
		"Duty Standing Order",
		filters={"active": 1, "auto_post": 1, "next_date": ["<=", today]},
		pluck="name",
	):
		try:
			# _post_inner rather than the whitelisted endpoint: that one calls
			# require_sysadmin against the session, and a scheduled job has none.
			# The loop lets an order dormant for months catch up rather than
			# posting once and claiming to be current — capped so a bad date
			# cannot spin.
			for _i in range(36):
				o = frappe.get_doc("Duty Standing Order", name)
				if not o.next_date or str(o.next_date) > today:
					break
				_post_inner(o)
		except frappe.ValidationError as e:
			# not an error in the code — an order that could not be paid. It
			# stays due, and somebody is told rather than finding a strange
			# balance later.
			unpaid.append(str(e))
		except Exception:
			frappe.log_error(frappe.get_traceback()[-1500:], "standing order post")

	if unpaid:
		frappe.log_error("\n".join(unpaid), "standing orders not paid - insufficient funds")
		try:
			# same route the shortfall warning already uses, rather than a
			# notifier of my own invention
			from duty_board.notify import _send, _shell

			rows = "".join("<li>%s</li>" % frappe.utils.escape_html(u) for u in unpaid[:12])
			for u in _money_admins():
				_send(u, "[Money] %d standing order(s) not paid" % len(unpaid),
					  _shell(_("Standing orders not paid"),
							 "<p>These were due and the account would not cover them, so "
							 "nothing was posted and they remain due:</p><ul>%s</ul>"
							 "<p>Put the money in and post them from Money, or skip "
							 "them.</p>" % rows))
		except Exception:
			frappe.log_error(frappe.get_traceback()[-800:], "standing order unpaid notice")
	return {"unpaid": len(unpaid), "detail": unpaid}


def _settle_expense(order, on_date):
	"""A standing order that pays a fixed cost settles it, without being told."""
	try:
		from duty_board.targets import on_standing_order_posted

		on_standing_order_posted(order, on_date)
	except Exception:
		frappe.log_error(frappe.get_traceback()[-800:], "expense settle on SO")


class InsufficientFunds(frappe.ValidationError):
	"""Raised where an account will not cover a payment.

	Its own class so the client can recognise it without matching on the text,
	which would break the first time the wording changed or was translated.
	"""


def _money_admins():
	"""Who hears about money problems. The same list shortfall_watch uses."""
	return [
		u for u in set(frappe.get_all(
			"Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent"
		))
		if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
	]


def _funds_available(account, amount, on_date):
	"""What the account holds on a date, and whether it covers the amount.

	None of these accounts has an overdraft, so a payment that would take one
	below zero is a payment that would have BOUNCED at the bank. Recording it
	anyway invents a transaction and produces a balance that never existed —
	which then leaks into runway, the forecast and every funding figure.
	"""
	bal = flt(_balances(as_of=on_date).get(account, 0))
	return bal, bal + 0.005 >= flt(amount)


def _post_inner(o, force=0):
	when = o.next_date
	if not cint(force):
		bal, ok = _funds_available(o.from_account, o.amount, when)
		if not ok:
			# A scheduled run must not invent a payment. The bank would have
			# refused this, so the order stays due and is reported rather than
			# posted — a wrong balance is far more expensive than a late one.
			raise frappe.ValidationError(
				_("{0}: {1} has {2} on {3} and the order needs {4}.").format(
					o.title, o.from_account, flt(bal), when, flt(o.amount)))
	frappe.get_doc({
		"doctype": "Duty Money Move",
		"move_date": when,
		"kind": "Transfer" if o.to_account else "Out",
		"account": o.from_account,
		"to_account": o.to_account or None,
		"amount": flt(o.amount),
		"category": _category("Standing order", "Fixed cost"),
		"counterparty": o.counterparty or o.title,
		"note": o.title,
		"standing_order": o.name,
	}).insert(ignore_permissions=True)
	o.last_posted = when
	o.next_date = _next_after(when, o.frequency)
	o.save(ignore_permissions=True)
	frappe.db.commit()
	# whatever fixed cost this order pays is now settled for that month —
	# the machine knows it happened, so nobody should have to tick it
	_settle_expense(o.name, when)


def shortfall_watch():
	"""Warn a week ahead where a funding account will not cover what is due.

	Pessimistic by design: money leaving in the window is counted in full, and
	money arriving is counted only where the arrival is itself a standing order.
	Salary and client payments are not projected, because a warning that assumes
	income you have not received is not a warning.

	cron: 0 7 * * *
	"""
	from duty_board.notify import _send, _shell

	today = nowdate()
	horizon = add_days(today, WINDOW_DAYS)
	bal = _balances()
	accounts = {
		a.name: a
		for a in frappe.get_all(
			"Duty Bank Account", filters={"active": 1},
			fields=["name", "nickname", "currency", "bank"], limit_page_length=0,
		)
	}
	out_soon, in_soon, detail = {}, {}, {}
	for o in frappe.get_all(
		"Duty Standing Order",
		filters={"active": 1, "next_date": ["<=", horizon]},
		fields=["name", "title", "from_account", "to_account", "amount", "next_date"],
		order_by="next_date asc",
		limit_page_length=0,
	):
		out_soon[o.from_account] = out_soon.get(o.from_account, 0) + flt(o.amount)
		detail.setdefault(o.from_account, []).append(o)
		if o.to_account:
			in_soon[o.to_account] = in_soon.get(o.to_account, 0) + flt(o.amount)

	risks = []
	for acc, committed in out_soon.items():
		a = accounts.get(acc)
		if not a:
			continue
		have = flt(bal.get(acc, 0)) + flt(in_soon.get(acc, 0))
		if have >= committed:
			continue
		risks.append({"account": a, "have": have, "committed": committed,
					  "gap": committed - have, "orders": detail.get(acc, [])})
	if not risks:
		return

	admins = [
		u for u in set(frappe.get_all(
			"Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent"
		))
		if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
	]
	if not admins:
		return

	blocks = ""
	for r in risks:
		a = r["account"]
		lines = "".join(
			f'<tr><td style="padding:5px 10px;border-bottom:1px solid #EDF2EF;font-size:12px">'
			f'{frappe.utils.escape_html(o.title)}</td>'
			f'<td style="padding:5px 10px;border-bottom:1px solid #EDF2EF;font-size:12px">{o.next_date}</td>'
			f'<td style="padding:5px 10px;border-bottom:1px solid #EDF2EF;font-size:12px;text-align:right">'
			f'{a.currency} {flt(o.amount):,.2f}</td></tr>'
			for o in r["orders"]
		)
		blocks += (
			f'<div style="margin:0 0 18px"><div style="font-weight:800;font-size:14px;margin-bottom:2px">'
			f'{frappe.utils.escape_html(a.nickname)}</div>'
			f'<div style="font-size:12.5px;color:#C94646;font-weight:700;margin-bottom:7px">'
			f'{_("Short by")} {a.currency} {r["gap"]:,.2f} — {_("holding")} {a.currency} {r["have"]:,.2f} '
			f'{_("against")} {a.currency} {r["committed"]:,.2f} {_("due")}</div>'
			f'<table style="border-collapse:collapse;width:100%">{lines}</table></div>'
		)
	inner = (
		f'<p style="font-size:13.5px">{_("Standing orders in the next {0} days exceed what the funding account will hold.").format(WINDOW_DAYS)}</p>'
		+ blocks
	)
	for u in admins:
		_send(u, "[Money] %s account(s) short in the next %d days" % (len(risks), WINDOW_DAYS),
			  _shell(_("Shortfall ahead"), inner))


@frappe.whitelist()
def save_standing_order(name=None, **kwargs):
	"""Create or amend one. The full list had no way to edit or stop an order —
	they could be created and then only skipped, one month at a time."""
	require_sysadmin()
	allowed = ("title", "from_account", "to_account", "amount", "frequency",
			   "next_date", "active", "auto_post", "counterparty", "note")
	doc = frappe.get_doc("Duty Standing Order", name) if name else frappe.new_doc("Duty Standing Order")
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not doc.title or not doc.from_account or not flt(doc.amount):
		frappe.throw(_("A standing order needs a name, a funding account and an amount."))
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def toggle_standing_order(name, active):
	"""Pause or resume. Pausing keeps the history; deleting would lose it."""
	require_sysadmin()
	frappe.db.set_value("Duty Standing Order", name, "active", cint(active))
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def delete_standing_order(name):
	require_sysadmin()
	frappe.delete_doc("Duty Standing Order", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def revalue_account(account, new_balance, move_date=None, note=None):
	"""Record what an account is now worth, and book the difference as growth.

	A pension or a fund does not tell you it earned 412.60 — it tells you the
	pot is now worth 18,940. So the natural entry is the new value, and the
	difference against the computed balance becomes a Growth move, positive or
	negative. Entering a gain by hand would mean doing that subtraction yourself
	every month, and getting it wrong once puts the ledger permanently out.
	"""
	require_sysadmin()
	acc = frappe.get_doc("Duty Bank Account", account)
	on = move_date or nowdate()
	current = flt(_balances(as_of=on).get(account, 0))
	delta = flt(new_balance) - current
	if abs(delta) < 0.005:
		return {"ok": 1, "delta": 0, "note": "already at that value"}
	doc = frappe.get_doc({
		"doctype": "Duty Money Move",
		"move_date": on,
		"kind": "Growth",
		"account": account,
		"amount": delta,
		"category": _category(_("Interest") if delta > 0 else _("Market fall"), "Not spending"),
		"note": note or _("Revalued to {0}").format(flt(new_balance)),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "delta": delta, "currency": acc.currency}


@frappe.whitelist()
def statement(account, days=180):
	"""One account's movements with a running balance.

	The face only ever showed the last 25 movements across every account mixed
	together, which answers 'what happened lately' and not 'what happened on
	this account' — the question you actually ask when a balance looks wrong.

	The opening figure is computed as the balance the day before the window, so
	the running column reconciles to the account's real balance rather than
	starting from zero and disagreeing with the card.
	"""
	require_sysadmin()
	acc = frappe.get_doc("Duty Bank Account", account)
	since = add_days(nowdate(), -abs(cint(days) or 180))
	opening = flt(_balances(as_of=add_days(since, -1)).get(account, 0))

	rows = frappe.get_all(
		"Duty Money Move",
		filters={"move_date": [">=", since]},
		or_filters=[{"account": account}, {"to_account": account}],
		fields=["name", "move_date", "kind", "account", "to_account", "amount",
				"amount_received", "category", "counterparty", "note",
				"standing_order", "creation"],
		order_by="move_date asc, creation asc",
		limit_page_length=0,
	)
	names = {a.name: a.nickname for a in frappe.get_all(
		"Duty Bank Account", fields=["name", "nickname"], limit_page_length=0)}

	out, run = [], opening
	for r in rows:
		if r.kind == "Transfer" and r.to_account == account:
			# the receiving leg: what actually landed, which on a cross-currency
			# transfer is not what left
			delta = flt(r.amount_received) or flt(r.amount)
			label = _("from {0}").format(names.get(r.account, r.account))
		elif r.kind == "Transfer":
			delta = -flt(r.amount)
			label = _("to {0}").format(names.get(r.to_account, r.to_account))
		elif r.kind in ("In", "Growth"):
			delta = flt(r.amount)
			label = r.counterparty or r.category or ""
		else:
			delta = -flt(r.amount)
			label = r.counterparty or r.category or ""
		run += delta
		out.append({
			"name": r.name, "date": str(r.move_date), "kind": r.kind,
			"delta": delta, "balance": run, "label": label,
			"category": r.category, "note": r.note,
			"standing_order": r.standing_order,
		})
	out.reverse()  # newest first to read, computed oldest first to be right
	return {
		"account": account, "nickname": acc.nickname, "bank": acc.bank,
		"currency": acc.currency, "since": since,
		"opening": opening, "closing": run, "rows": out,
		"in_total": sum(r["delta"] for r in out if r["delta"] > 0),
		"out_total": -sum(r["delta"] for r in out if r["delta"] < 0),
	}


@frappe.whitelist()
def renewals(horizon=90):
	"""Customers whose annual renewal falls due, bucketed by how soon.

	monthly_fee is an ANNUAL figure despite its name — commercial.py already
	says so, and this reads it the same way rather than repeating the mistake
	the field name invites.

	Overdue renewals are shown as their own bucket rather than folded into the
	first thirty days. A renewal that passed is a different conversation from
	one coming up, and averaging them into one number loses the one that needs
	a call today.
	"""
	require_sysadmin()
	today = nowdate()
	end = add_days(today, abs(cint(horizon) or 90))

	rows = frappe.get_all(
		"Customer",
		filters={"renewal_date": ["is", "set"], "disabled": 0},
		fields=["name", "customer_name", "renewal_date", "monthly_fee",
				"default_currency"],
		order_by="renewal_date asc", limit_page_length=0)

	# The whole book, not just the window. Every active customer with a renewal
	# date and what they are worth a year — the query already fetches them and
	# was throwing away everything past ninety days.
	book_items = [{"amount": flt(r.monthly_fee),
				   "currency": r.default_currency or "NGN"} for r in rows]

	buckets = {"overdue": [], "d30": [], "d60": [], "d90": []}
	for r in rows:
		if not r.renewal_date:
			continue
		d = str(r.renewal_date)
		days = frappe.utils.date_diff(d, today)
		if days < 0:
			key = "overdue"
		elif days <= 30:
			key = "d30"
		elif days <= 60:
			key = "d60"
		elif days <= 90:
			key = "d90"
		else:
			continue
		buckets[key].append({
			"customer": r.name,
			"name": r.customer_name or r.name,
			"due": d,
			"days": days,
			"amount": flt(r.monthly_fee),
			"currency": r.default_currency or "NGN",
		})

	def total(items):
		by = {}
		for i in items:
			by[i["currency"]] = by.get(i["currency"], 0.0) + i["amount"]
		return [{"currency": c, "amount": v} for c, v in sorted(by.items())]

	out = {}
	for k, items in buckets.items():
		out[k] = {"items": items, "count": len(items), "totals": total(items)}
	# the whole window in one figure, for the header — overdue included, since a
	# renewal that has passed is still money not collected
	all_items = [i for b in buckets.values() for i in b]
	out["summary"] = {
		"customers": len(all_items),
		"totals": total(all_items),
		"overdue_customers": len(buckets["overdue"]),
		"overdue_totals": total(buckets["overdue"]),
	}
	# Accounting services: a monthly fee, not an annual renewal, so it is its own
	# list rather than a bucket in the renewal window. accounting_services is a
	# Select holding "On Board" — not a checkbox — which is how accounting.py has
	# always read it, and reading it two ways would be worse than either.
	acc_rows = frappe.get_all(
		"Customer",
		filters={"accounting_services": "On Board", "disabled": 0},
		fields=["name", "customer_name", "accounting_fees", "default_currency"],
		order_by="accounting_fees desc", limit_page_length=0)
	acc_items, acc_by_ccy = [], {}
	for a_ in acc_rows:
		fee = flt(a_.accounting_fees)
		ccy = a_.default_currency or "NGN"
		acc_items.append({"customer": a_.name, "name": a_.customer_name or a_.name,
						  "monthly": fee, "annual": fee * 12, "currency": ccy})
		acc_by_ccy[ccy] = acc_by_ccy.get(ccy, 0.0) + fee
	out["accounting"] = {
		"items": acc_items,
		"customers": len(acc_items),
		"monthly": [{"currency": c, "amount": v} for c, v in sorted(acc_by_ccy.items())],
		"annual": [{"currency": c, "amount": v * 12} for c, v in sorted(acc_by_ccy.items())],
		"no_fee": len([i for i in acc_items if not i["monthly"]]),
	}

	out["book"] = {
		"customers": len(book_items),
		"totals": total(book_items),
		"no_fee": len([i for i in book_items if not i["amount"]]),
	}
	out["missing"] = cint(frappe.db.count(
		"Customer", {"renewal_date": ["is", "not set"], "disabled": 0}))
	out["no_fee"] = len([i for b in buckets.values() for i in b if not i["amount"]])
	out["horizon"] = cint(horizon) or 90
	return out


@frappe.whitelist()
def save_renewal(customer, renewal_date=None, monthly_fee=None, disabled=None):
	"""Edit a renewal from the list you spotted the problem in.

	Writes straight to Customer, which is where the fields live — a renewal is
	the customer's fact, not a copy of it, and a copy would drift the first time
	somebody edited the customer directly.

	monthly_fee is the ANNUAL figure despite its name. Renaming it properly is a
	bigger job than this and would touch commercial.py and the client rooms; it
	is read consistently as annual everywhere instead.
	"""
	require_sysadmin()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("No such customer."))
	vals = {}
	if renewal_date is not None:
		vals["renewal_date"] = renewal_date or None
	if monthly_fee is not None:
		fee = flt(monthly_fee)
		if fee < 0:
			frappe.throw(_("A renewal fee cannot be negative."))
		vals["monthly_fee"] = fee
	if disabled is not None:
		vals["disabled"] = cint(disabled)
	if not vals:
		return {"ok": 1}
	frappe.db.set_value("Customer", customer, vals)
	frappe.db.commit()
	return {"ok": 1, "customer": customer}


@frappe.whitelist()
def roll_renewal(customer, years=1):
	"""Push the renewal on by a year from its own date, not from today.

	Rolling from today would quietly move an anniversary every time it was
	renewed late — a customer renewed three weeks after their date would drift
	three weeks a year. From the existing date the anniversary holds.
	"""
	require_sysadmin()
	cur = frappe.db.get_value("Customer", customer, "renewal_date")
	if not cur:
		frappe.throw(_("That customer has no renewal date to move."))
	new = add_months(getdate(cur), 12 * abs(cint(years) or 1))
	frappe.db.set_value("Customer", customer, "renewal_date", new)
	frappe.db.commit()
	return {"ok": 1, "renewal_date": str(new), "was": str(cur)}


@frappe.whitelist()
def save_accounting_fee(customer, accounting_fees=None, off_board=None):
	"""Edit the monthly accounting fee, or take a customer off the service."""
	require_sysadmin()
	if not frappe.db.exists("Customer", customer):
		frappe.throw(_("No such customer."))
	vals = {}
	if accounting_fees is not None:
		fee = flt(accounting_fees)
		if fee < 0:
			frappe.throw(_("A fee cannot be negative."))
		vals["accounting_fees"] = fee
	if cint(off_board):
		# the field is a Select, so it is set to blank rather than unchecked
		vals["accounting_services"] = ""
	if vals:
		frappe.db.set_value("Customer", customer, vals)
		frappe.db.commit()
	return {"ok": 1}
