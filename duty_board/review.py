"""Review — the month put away, where the money went, and what is coming.

Four things that share one property: they are all already implied by data the
app holds and none of them could be seen.

MONTH CLOSE. Nothing marked a month finished. On the 1st the target line moved,
the expenses reset, and whether the previous month was met simply stopped being
visible — so "how many months have I actually hit?" was unanswerable. A close
records the month as it stood, and records it FROZEN: editing a target in
November must not rewrite the verdict on August, because history that changes
is not history.

NET WORTH OVER TIME. Balances are computed and never stored, which is right —
a stored balance drifts. But it means there is no past unless a point is kept
deliberately, and a line nobody can draw is a line nobody sees.

WHERE THE MONEY GOES. Every movement carries a category and nothing ever added
them up. The interesting figure is not the total spent but the part that is
neither a target nor a fixed cost, because that is the part that explains a
target being missed.

WHAT IS COMING. Standing orders, due dates and balances are all known
separately. Projecting them forward turns "you were short on the 28th" into
"the 28th will be tight", which is the difference between a report and a
warning.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_first_day, getdate, nowdate

from duty_board.permissions import require_sysadmin


def _ym(d=None):
	return str(d or nowdate())[:7]


def _prev_ym(ym=None):
	first = getdate((ym or _ym()) + "-01")
	return str(add_months(first, -1))[:7]


# ───────────────────────────── net worth ─────────────────────────────────────


def _net_worth_now():
	"""Everything, in naira, split by what kind of thing it is."""
	from duty_board.money import _balances
	from duty_board.shares import _positions
	from duty_board.targets import _rate_map

	fx = _rate_map()
	bal = _balances()
	buckets = {"cash": 0.0, "savings": 0.0, "investments": 0.0, "shares": 0.0, "debt": 0.0}
	unpriced = []
	for a in frappe.get_all(
		# in_net_worth was invented — the doctype has no such field. Every active
		# account counts, and a credit card counts against rather than being
		# excluded, which is what an opt-out flag would have been used for.
		"Duty Bank Account", filters={"active": 1},
		fields=["name", "account_type", "currency"], limit_page_length=0):
		rate = fx.get(a.currency)
		v = flt(bal.get(a.name, 0))
		if not rate:
			if abs(v) > 0.005:
				unpriced.append(a.currency)
			continue
		ngn = v * rate
		if a.account_type in ("Credit Card", "Loan"):
			# a loan is debt exactly as a card is; leaving it out overstated net
			# worth and made the trajectory line measure the wrong thing
			buckets["debt"] += abs(ngn)
		elif a.account_type == "Savings":
			buckets["savings"] += ngn
		elif a.account_type == "Investment":
			buckets["investments"] += ngn
		else:
			buckets["cash"] += ngn
	for h in _positions().values():
		if h.qty > 0 and h.last_price:
			rate = fx.get(h.currency)
			if rate:
				buckets["shares"] += h.value * rate
			elif h.value:
				unpriced.append(h.currency)
	# bonds, carried as chosen — missing entirely until now, so net worth
	# understated by the whole of any bond held
	try:
		from duty_board.bonds import bond_summary

		for r in bond_summary():
			rate = fx.get(r["currency"])
			if rate:
				buckets["investments"] += flt(r["value"]) * flt(rate)
			elif r["value"]:
				unpriced.append(r["currency"])
	except Exception:
		pass
	total = (buckets["cash"] + buckets["savings"] + buckets["investments"]
			 + buckets["shares"] - buckets["debt"])
	return total, buckets, sorted(set(unpriced))


@frappe.whitelist()
def snapshot_net_worth(on_date=None, note=None):
	"""Keep today's figure. One point per day — a second run updates it."""
	require_sysadmin()
	on = on_date or nowdate()
	total, b, _u = _net_worth_now()
	payload = dict(b, ngn_total=total, note=note or None)
	if frappe.db.exists("Duty Net Worth Point", on):
		frappe.db.set_value("Duty Net Worth Point", on, payload)
	else:
		frappe.get_doc(dict({"doctype": "Duty Net Worth Point", "on_date": on},
							**payload)).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "total": total}


def scheduled_snapshot():
	"""Weekly. cron: 0 6 * * 1"""
	try:
		snapshot_net_worth()
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1200:], "net worth snapshot")


@frappe.whitelist()
def net_worth_series(months=12):
	require_sysadmin()
	since = str(add_months(getdate(nowdate()), -abs(cint(months) or 12)))
	rows = frappe.get_all(
		"Duty Net Worth Point", filters={"on_date": [">=", since]},
		fields=["on_date", "ngn_total", "cash", "savings", "investments", "shares", "debt", "note"],
		order_by="on_date asc", limit_page_length=0)
	total, b, unpriced = _net_worth_now()
	pts = [{"d": str(r.on_date), "p": flt(r.ngn_total),
			"cash": flt(r.cash), "savings": flt(r.savings),
			"investments": flt(r.investments), "shares": flt(r.shares),
			"debt": flt(r.debt)} for r in rows]
	# today's live figure completes the line — without it the chart stops at the
	# last snapshot and always looks a week out of date
	if not pts or pts[-1]["d"] != nowdate():
		pts.append(dict(b, d=nowdate(), p=total))

	trends = {k: _trend(pts, v) for k, v in
			  (("month", 30), ("quarter", 91), ("year", 365))}
	# the run rate that matters: what it has actually done lately, which is a
	# better guide than a figure averaged over a year that includes a house move
	run = next((t for t in (trends.get("quarter"), trends.get("month"),
							trends.get("year")) if t and t.get("per_month")), None)
	since = _trend(pts, 3650)
	return {"points": pts, "now": total, "buckets": b, "unpriced": unpriced,
			"trends": trends,
			"per_month": (run or {}).get("per_month"),
			"since": since,
			"projected_year": (total + (run or {}).get("per_month", 0) * 12) if run else None,
			"reconstructed": len([r for r in rows if (r.get("note") or "") == "reconstructed"]),
			"first": pts[0]["d"] if pts else None}


# ────────────────────────────── month close ──────────────────────────────────


@frappe.whitelist()
def close_month(month=None):
	"""Judge a month and put it away, frozen."""
	require_sysadmin()
	from duty_board.targets import expenses as ex_for, targets as tg

	ym = month or _prev_ym()
	t = tg()
	ex = ex_for(ym)
	nw, buckets, _u = _net_worth_now()

	# targets() reports the CURRENT month; closing a past month can only record
	# what is knowable now, so that is said rather than implied
	same_month = (ym == t.get("month"))
	needed = flt(t.get("ngn_month") or 0) if same_month else flt(ex.get("ngn_due") or 0)
	raised = flt(t.get("ngn_raised") or 0) if same_month else flt(ex.get("ngn_paid") or 0)

	detail = {
		"targets": [{"title": r["title"], "currency": r["currency"],
					 "monthly": r["monthly"], "raised": r.get("raised"),
					 "met": r["met"], "still": r["still"]}
					for r in (t.get("targets") or [])] if same_month else [],
		"expenses": [{"title": r["title"], "currency": r["currency"],
					  "amount": r["amount"], "paid": r["paid"], "settled": r["settled"]}
					 for r in (ex.get("expenses") or [])],
		"buckets": buckets,
		"partial": 0 if same_month else 1,
	}
	payload = {
		"closed_on": frappe.utils.now(),
		"ngn_needed": needed, "ngn_raised": raised,
		"ngn_short": max(0.0, needed - raised),
		"targets_met": len([r for r in (t.get("targets") or []) if r["met"]]) if same_month else 0,
		"targets_total": len(t.get("targets") or []) if same_month else 0,
		"expenses_paid": len([r for r in (ex.get("expenses") or []) if r["settled"]]),
		"expenses_total": len(ex.get("expenses") or []),
		"net_worth": nw,
		"detail": json.dumps(detail),
	}
	if frappe.db.exists("Duty Month Close", ym):
		frappe.db.set_value("Duty Month Close", ym, payload)
	else:
		frappe.get_doc(dict({"doctype": "Duty Month Close", "month": ym},
							**payload)).insert(ignore_permissions=True)
	snapshot_net_worth(note=_("month close {0}").format(ym))
	frappe.db.commit()
	return {"ok": 1, "month": ym, "short": payload["ngn_short"]}


def scheduled_close():
	"""1st of the month, closing the one just gone. cron: 30 5 1 * *"""
	try:
		close_month(_prev_ym())
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1500:], "month close")


@frappe.whitelist()
def month_history(limit=18):
	require_sysadmin()
	rows = frappe.get_all(
		"Duty Month Close",
		fields=["month", "ngn_needed", "ngn_raised", "ngn_short", "targets_met",
				"targets_total", "expenses_paid", "expenses_total", "net_worth", "note"],
		order_by="month desc", limit_page_length=cint(limit) or 18)
	for r in rows:
		r.met = 1 if flt(r.ngn_short) <= 0.005 else 0
		r.pct = (min(100, int(flt(r.ngn_raised) * 100 / flt(r.ngn_needed)))
				 if flt(r.ngn_needed) > 0 else 100)
	hit = len([r for r in rows if r.met])
	return {"months": rows, "hit": hit, "of": len(rows),
			"current": _ym(), "closed_current": bool(frappe.db.exists("Duty Month Close", _ym()))}


# ───────────────────────────── where it goes ─────────────────────────────────


@frappe.whitelist()
def spending(months=6):
	"""Money out, by category, with the part that is neither target nor fixed cost.

	Transfers are excluded throughout: moving money between your own accounts is
	not spending, and counting it would make the total meaningless.
	"""
	require_sysadmin()
	from duty_board.targets import _rate_map

	fx = _rate_map()
	since = str(get_first_day(add_months(getdate(nowdate()), -(abs(cint(months) or 6) - 1))))
	accs = {a.name: a.currency for a in frappe.get_all(
		"Duty Bank Account", fields=["name", "currency"], limit_page_length=0)}

	# Categories marked 'Not spending' are money that moved without leaving you —
	# a share purchase turns cash into shares and you still own it. Counting that
	# as spending made a discretionary figure of a million where the truth was
	# close to nothing.
	kinds = {c.name: c.kind for c in frappe.get_all(
		"Duty Money Category", fields=["name", "kind"], limit_page_length=0)}

	# Committed is matched by the LINK between an expense settlement and the
	# movement it posted, not by two free-text fields happening to agree. The
	# string match reported nothing committed whenever an expense had no
	# category, which is most of them.
	settled_moves = {p.money_move for p in frappe.get_all(
		"Duty Expense Payment", filters={"money_move": ["is", "set"]},
		fields=["money_move"], limit_page_length=0) if p.money_move}

	by_cat, by_month, total, unpriced = {}, {}, 0.0, set()
	excluded = 0.0
	for m in frappe.get_all(
		"Duty Money Move",
		filters={"kind": "Out", "move_date": [">=", since]},
		fields=["name", "move_date", "account", "amount", "category",
				"counterparty", "standing_order"],
		limit_page_length=0):
		rate = fx.get(accs.get(m.account))
		if not rate:
			unpriced.add(accs.get(m.account) or "?")
			continue
		v = flt(m.amount) * rate
		cat = (m.category or "").strip()
		if kinds.get(cat) == "Not spending":
			excluded += v
			continue
		label = cat or _("Uncategorised")
		is_fixed = 1 if (m.name in settled_moves or m.standing_order
						 or kinds.get(cat) == "Fixed cost") else 0
		c = by_cat.setdefault(label, {"category": label, "total": 0.0, "n": 0,
									  "fixed": is_fixed})
		c["total"] += v
		c["n"] += 1
		if is_fixed:
			c["fixed"] = 1
		ym = str(m.move_date)[:7]
		by_month[ym] = by_month.get(ym, 0.0) + v
		total += v

	cats = sorted(by_cat.values(), key=lambda x: -x["total"])
	for c in cats:
		c["pct"] = round(c["total"] * 100 / total, 1) if total else 0
	# Months ELAPSED in the window, not months that happen to have spending. The
	# two differ whenever a month is quiet or the window opens mid-month, and the
	# difference always flatters: dividing a month's spending by one and calling
	# it typical is how a fortnight of records becomes a monthly average.
	n_months = 0
	if by_month:
		first = min(by_month)
		fy, fm = [int(x) for x in first.split("-")]
		ny, nm = [int(x) for x in _ym().split("-")]
		n_months = (ny - fy) * 12 + (nm - fm) + 1
	n_months = max(1, n_months)
	committed = sum(c["total"] for c in cats if c["fixed"])
	return {
		"since": since, "months": n_months, "months_with_data": len(by_month),
		"total": total,
		"per_month": total / n_months,
		"categories": cats[:14],
		"committed": committed,
		"discretionary": total - committed,
		"discretionary_per_month": (total - committed) / n_months,
		"by_month": [{"m": k, "v": by_month[k]} for k in sorted(by_month)],
		"unpriced": sorted(unpriced),
		"excluded": excluded,
	}


# ────────────────────────────── what is coming ───────────────────────────────


@frappe.whitelist()
def forecast(days=45):
	"""Every known commitment ahead, and where each account runs out.

	Known means scheduled: standing orders and fixed costs with a due day.
	Ordinary spending is NOT projected — a forecast that guesses is one nobody
	can act on, and being wrong about a date is worse than being silent.
	"""
	require_sysadmin()
	from duty_board.money import _balances
	from duty_board.targets import _rate_map

	fx = _rate_map()
	horizon = add_days(nowdate(), abs(cint(days) or 45))
	bal = _balances()
	accs = {a.name: a for a in frappe.get_all(
		"Duty Bank Account", filters={"active": 1},
		fields=["name", "nickname", "currency", "account_type"], limit_page_length=0)}

	events = []
	for o in frappe.get_all(
		"Duty Standing Order", filters={"active": 1},
		fields=["name", "title", "from_account", "to_account", "amount",
				"frequency", "next_date"], limit_page_length=0):
		d = o.next_date
		guard = 0
		while d and str(d) <= str(horizon) and guard < 24:
			events.append({"date": str(d), "title": o.title, "kind": "standing order",
						   "account": o.from_account, "amount": -flt(o.amount),
						   "to_account": o.to_account})
			from duty_board.money import _next_after

			d = _next_after(d, o.frequency)
			guard += 1

	today_ym = _ym()
	for e in frappe.get_all(
		"Duty Monthly Expense", filters={"active": 1},
		fields=["name", "title", "amount", "currency", "due_day", "account",
				"standing_order", "start_month", "end_month"], limit_page_length=0):
		if e.standing_order or not e.due_day or not e.account:
			continue  # already counted, or no date to place it on
		for k in range(0, 3):
			first = add_months(get_first_day(getdate(nowdate())), k)
			ym = str(first)[:7]
			if str(ym) < str(e.start_month or "") or (e.end_month and str(ym) > str(e.end_month)):
				continue
			if ym == today_ym and frappe.db.exists(
					"Duty Expense Payment", "%s::%s" % (e.name, ym)):
				continue
			try:
				d = str(getdate("%s-%02d" % (ym, min(28, cint(e.due_day)))))
			except Exception:
				continue
			if d < nowdate() or d > str(horizon):
				continue
			events.append({"date": d, "title": e.title, "kind": "fixed cost",
						   "account": e.account, "amount": -flt(e.amount),
						   "to_account": None})

	# planned one-offs join the walk, so an October television shows up beside
	# the standing orders and, if it is what tips an account, the warning says so
	for o in frappe.get_all(
		"Duty Planned Outflow",
		filters={"status": ["in", ["Planned", "Committed"]],
				 "due_on": ["<=", horizon], "account": ["is", "set"]},
		fields=["name", "title", "amount", "due_on", "account", "confidence"],
		limit_page_length=0):
		if str(o.due_on) < nowdate():
			continue
		events.append({"date": str(o.due_on), "title": o.title,
					   "kind": "planned (%s)" % (o.confidence or "Certain").lower(),
					   "account": o.account, "amount": -flt(o.amount),
					   "to_account": None})

	events.sort(key=lambda x: x["date"])

	# walk each account forward and note the first day it goes under
	run = {a: flt(bal.get(a, 0)) for a in accs}
	trouble, ledger = {}, []
	for ev in events:
		a = ev["account"]
		if a not in run:
			continue
		run[a] += ev["amount"]
		if ev.get("to_account") and ev["to_account"] in run:
			run[ev["to_account"]] += -ev["amount"]
		ev["balance_after"] = run[a]
		ev["nickname"] = (accs.get(a) or {}).get("nickname")
		ev["currency"] = (accs.get(a) or {}).get("currency")
		if run[a] < 0 and a not in trouble:
			trouble[a] = {"account": a, "nickname": ev["nickname"],
						  "currency": ev["currency"], "date": ev["date"],
						  "short_by": abs(run[a])}
		ledger.append(ev)

	out_total = 0.0
	for ev in ledger:
		rate = fx.get(ev.get("currency"))
		if rate and ev["amount"] < 0:
			out_total += abs(ev["amount"]) * rate
	return {"events": ledger[:60], "trouble": list(trouble.values()),
			"horizon": str(horizon), "days": cint(days) or 45,
			"committed_ngn": out_total}


@frappe.whitelist()
def backfill_categories(dry_run=1):
	"""Turn the free-text categories already recorded into records.

	Run once after migrating. Categories were plain Data and are now a Link, so
	anything typed before this exists as a string with no record behind it — the
	value still displays but nothing can be grouped or coloured by it.

	Kind is guessed and then left to you: 'Shares', 'Interest' and 'Market fall'
	are money that did not leave, 'Standing order' is a fixed cost, everything
	else is spending. A guess is fine here because it is visible and editable,
	which is not true of a guess buried in a total.

	bench --site <site> execute duty_board.review.backfill_categories
	bench --site <site> execute duty_board.review.backfill_categories --kwargs "{'dry_run': 0}"
	"""
	require_sysadmin()
	dry = cint(dry_run)
	NOT_SPENDING = {"Shares", "Interest", "Market fall", "Transfer"}
	FIXED = {"Standing order", "Fixed cost", "Rent", "Salary"}

	seen = set()
	for tbl, fld in (("Duty Money Move", "category"), ("Duty Monthly Expense", "category")):
		for r in frappe.db.sql(
			"select distinct `%s` as c from `tab%s` where ifnull(`%s`,'') != ''"
			% (fld, tbl, fld), as_dict=True):
			if r.c:
				seen.add(r.c.strip())
	made = []
	for c in sorted(seen):
		if frappe.db.exists("Duty Money Category", c):
			continue
		kind = ("Not spending" if c in NOT_SPENDING
				else "Fixed cost" if c in FIXED else "Spending")
		made.append("%s (%s)" % (c, kind))
		if not dry:
			frappe.get_doc({"doctype": "Duty Money Category", "category_name": c,
							"kind": kind}).insert(ignore_permissions=True)
	if not dry:
		frappe.db.commit()
	print("%s: %d category record(s) %s" % ("DRY RUN" if dry else "DONE", len(made),
										   "would be created" if dry else "created"))
	for m in made:
		print("   %s" % m)
	if dry and made:
		print('Re-run with --kwargs "{\'dry_run\': 0}" to apply.')
	return {"created": len(made), "detail": made}


@frappe.whitelist()
def categories():
	require_sysadmin()
	rows = frappe.get_all("Duty Money Category", fields=["name", "kind", "active"],
						  order_by="kind asc, name asc", limit_page_length=0)
	used = {r.category: r.n for r in frappe.db.sql(
		"""select category, count(*) n from `tabDuty Money Move`
		   where ifnull(category,'') != '' group by category""", as_dict=True)}
	for r in rows:
		r.used = used.get(r.name, 0)
	return rows


@frappe.whitelist()
def save_category(name=None, category_name=None, kind="Spending", active=1):
	require_sysadmin()
	if name and frappe.db.exists("Duty Money Category", name):
		frappe.db.set_value("Duty Money Category", name,
							{"kind": kind, "active": cint(active)})
	else:
		frappe.get_doc({"doctype": "Duty Money Category",
						"category_name": category_name or name,
						"kind": kind, "active": cint(active)}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


def _net_worth_on(on_date):
	"""What everything was worth on a past date, from the transactions.

	Balances as of that day come from the ledger; share holdings are walked from
	the trades and priced at the closes stored for that date.

	FX USES TODAY'S RATE THROUGHOUT, and that is a choice rather than a
	shortcut. Rates are stored one-per-currency with no history, so the
	alternative would be inventing past ones. Holding the rate still has a real
	virtue: the line then shows money you actually gained or spent rather than
	the naira moving underneath you, which for a portfolio held mostly in naira
	is the more useful of the two questions. It is stated on screen.
	"""
	from duty_board.money import _balances
	from duty_board.targets import _portfolio_value_on, _rate_map

	fx = _rate_map()
	bal = _balances(as_of=on_date)
	b = {"cash": 0.0, "savings": 0.0, "investments": 0.0, "shares": 0.0, "debt": 0.0}
	for a in frappe.get_all(
		"Duty Bank Account", filters={"active": 1},
		fields=["name", "account_type", "currency"], limit_page_length=0):
		rate = fx.get(a.currency)
		if not rate:
			continue
		ngn = flt(bal.get(a.name, 0)) * rate
		if a.account_type in ("Credit Card", "Loan"):
			b["debt"] += abs(ngn)
		elif a.account_type == "Savings":
			b["savings"] += ngn
		elif a.account_type == "Investment":
			b["investments"] += ngn
		else:
			b["cash"] += ngn
	for ccy, rate in fx.items():
		try:
			v, _approx = _portfolio_value_on(add_days(on_date, 1), ccy)
		except Exception:
			v = 0.0
		b["shares"] += flt(v) * flt(rate)
	# bonds were missing from net worth entirely, so it understated by the whole
	# of any bond held. Carried value, which for amortised cost is what was paid
	# drifting to par.
	try:
		from duty_board.bonds import bond_summary

		for r in bond_summary():
			rate = fx.get(r["currency"])
			if rate:
				b["investments"] += flt(r["value"]) * flt(rate)
	except Exception:
		pass
	total = b["cash"] + b["savings"] + b["investments"] + b["shares"] - b["debt"]
	return total, b


@frappe.whitelist()
def backfill_net_worth(weeks=52, dry_run=1):
	"""Reconstruct the weekly line from what the ledger already knows.

	A trajectory needs points, and weekly snapshots started days ago — so the
	chart would have been useless until Christmas. Every figure here is derived
	from transactions that were already recorded, so this is recovering history
	rather than inventing it.

	Existing points are left alone: one taken on the day is better evidence than
	one reconstructed afterwards, and overwriting a real observation with a
	recomputation is how a record stops being a record.

	bench --site <site> execute duty_board.review.backfill_net_worth
	bench --site <site> execute duty_board.review.backfill_net_worth --kwargs "{'dry_run': 0, 'weeks': 52}"
	"""
	require_sysadmin()
	dry = cint(dry_run)
	n = abs(cint(weeks) or 52)
	have = set(frappe.get_all("Duty Net Worth Point", pluck="on_date", limit_page_length=0))
	have = {str(x) for x in have}

	# no point reaching back before there was anything to see
	first_move = frappe.db.get_value("Duty Money Move", {}, "move_date", order_by="move_date asc")
	floor = str(first_move) if first_move else None

	# Weekly points only, against a ledger that begins days ago, wrote a single
	# point and left the chart saying it had nothing. The cadence now follows the
	# data: every day for the recent stretch, weekly further back. A short
	# history deserves a dense line, not an empty one.
	made, skipped = [], 0
	today = getdate(nowdate())
	dates = []
	for i in range(60, -1, -1):
		dates.append(str(add_days(today, -i)))
	for i in range(n, 8, -1):
		dates.append(str(add_days(today, -7 * i)))
	dates = sorted(set(dates))
	for on in dates:
		if on in have:
			skipped += 1
			continue
		if floor and on < floor:
			continue
		total, b = _net_worth_on(on)
		if not total and not any(b.values()):
			continue
		made.append((on, total))
		if not dry:
			frappe.get_doc(dict({"doctype": "Duty Net Worth Point", "on_date": on,
								 "ngn_total": total, "note": "reconstructed"},
								**b)).insert(ignore_permissions=True)
	if not dry:
		frappe.db.commit()
	print("%s: %d point(s) %s, %d already recorded and left alone"
		  % ("DRY RUN" if dry else "DONE", len(made),
			 "would be written" if dry else "written", skipped))
	for on, t in made[-8:]:
		print("   %s  %s" % (on, f"{t:,.2f}"))
	if dry and made:
		print('Re-run with --kwargs "{\'dry_run\': 0}" to apply.')
	return {"written": len(made), "skipped": skipped}


MIN_SPAN_FOR_RATE = 14


def _trend(points, days):
	"""Change over a window, against the nearest point at or before its start."""
	if len(points) < 2:
		return None
	cutoff = str(add_days(getdate(nowdate()), -abs(days)))
	older = [p for p in points if p["d"] <= cutoff]
	base = older[-1] if older else points[0]
	now = points[-1]
	if base["d"] == now["d"]:
		return None
	delta = now["p"] - base["p"]
	span = max(1, (getdate(now["d"]) - getdate(base["d"])).days)
	return {"from": base["d"], "from_value": base["p"], "delta": delta,
			"pct": round(delta * 100 / base["p"], 1) if base["p"] else None,
			# Extrapolating five days to a month produces a confident number
			# from nothing. Below a fortnight the change is reported and the
			# rate is not.
			"per_month": (delta * 30.0 / span) if span >= MIN_SPAN_FOR_RATE else None,
			"days": span}


@frappe.whitelist()
def runway(months_of_spending=3):
	"""How long the cash lasts with nothing coming in.

	The most sobering number a person can be shown about their own finances, and
	nothing here showed it. Every input already existed — fixed costs, the
	spending average, cash to hand — they had simply never been divided.

	CASH MEANS CASH. Investments and shares are excluded: a pension you cannot
	draw and a stock you would have to sell at whatever Monday offers are not
	what carries you through a bad quarter. Counting them would produce a
	comfortable number and a false one.

	Debt is netted off, because a card balance is somebody else's money sitting
	in your account.
	"""
	require_sysadmin()
	from duty_board.money import _balances
	from duty_board.targets import _rate_map

	fx = _rate_map()
	bal = _balances()
	cash, debt, unpriced = 0.0, 0.0, set()
	for a in frappe.get_all(
		"Duty Bank Account", filters={"active": 1},
		fields=["name", "account_type", "currency"], limit_page_length=0):
		rate = fx.get(a.currency)
		v = flt(bal.get(a.name, 0))
		if not rate:
			if abs(v) > 0.005:
				unpriced.add(a.currency)
			continue
		ngn = v * rate
		if a.account_type in ("Credit Card", "Loan"):
			debt += abs(ngn)
		elif a.account_type in ("Current", "Savings", "Cash"):
			cash += ngn
	available = cash - debt

	# what a month actually costs: the fixed costs you owe plus what you
	# ordinarily spend on everything else
	fixed = 0.0
	for e in frappe.get_all(
		"Duty Monthly Expense", filters={"active": 1},
		fields=["amount", "currency", "start_month", "end_month"], limit_page_length=0):
		ym = _ym()
		if str(ym) < str(e.start_month or "") or (e.end_month and str(ym) > str(e.end_month)):
			continue
		rate = fx.get(e.currency)
		if rate:
			fixed += flt(e.amount) * rate

	sp = spending(abs(cint(months_of_spending) or 3))
	discretionary = flt(sp.get("discretionary_per_month") or 0)
	burn = fixed + discretionary

	# THE DOUBLE-COUNT RISK, which is the real hazard in mixing planned and
	# actual. Fixed costs are counted from the setup; a payment against one is
	# excluded from ordinary spending only if it was recorded through the tick
	# (which links the movement) or by a standing order or a Fixed-cost
	# category. Paid as a plain Out with an ordinary category, it lands in
	# discretionary too and the same rent is counted twice.
	#
	# Rather than guess and silently subtract, the overlap is named.
	fixed_names = {(e.title or "").strip().lower() for e in frappe.get_all(
		"Duty Monthly Expense", filters={"active": 1}, fields=["title"], limit_page_length=0)}
	suspect = []
	if fixed_names:
		since_sp = sp.get("since")
		for m in frappe.get_all(
			"Duty Money Move",
			filters={"kind": "Out", "move_date": [">=", since_sp]},
			fields=["name", "counterparty", "note", "amount", "category", "standing_order"],
			limit_page_length=0):
			if m.standing_order:
				continue
			blob = ("%s %s" % (m.counterparty or "", m.note or "")).strip().lower()
			if not blob:
				continue
			for fn in fixed_names:
				if fn and fn in blob:
					suspect.append({"move": m.name, "matched": fn,
									"amount": flt(m.amount), "category": m.category})
					break

	# HOW MUCH HISTORY IS BEHIND THE AVERAGE. spending() divides by the number
	# of months that HAVE spending, so a fortnight of records divides by one and
	# calls a partial month a typical one. Until there are a few complete months
	# the discretionary figure is noise, and a runway built on noise is worse
	# than one built on the fixed costs alone.
	first = frappe.db.get_value("Duty Money Move", {}, "move_date", order_by="move_date asc")
	elapsed = 0
	if first:
		fy, fm = [int(x) for x in str(first).split("-")[:2]]
		ny, nm = [int(x) for x in _ym().split("-")]
		elapsed = (ny - fy) * 12 + (nm - fm) + 1
	thin = elapsed < 3

	# what is actually in "other", so the figure can be argued with
	top = [c for c in (sp.get("categories") or []) if not c.get("fixed")][:5]
	for c in top:
		c["per_month"] = c["total"] / max(1, sp.get("months") or 1)

	return {
		"cash": cash, "debt": debt, "available": available,
		"fixed": fixed, "discretionary": discretionary, "burn": burn,
		# two answers, because they carry different confidence. Fixed costs are
		# a commitment you have written down; ordinary spending is an estimate
		# from however much history exists.
		"months_fixed": round(available / fixed, 1) if fixed > 0 else None,
		"months": round(available / burn, 1) if burn > 0 else None,
		"thin_history": 1 if thin else 0,
		"months_of_data": elapsed,
		"discretionary_top": top,
		"double_count": suspect[:6],
		"double_count_n": len(suspect),
		"unpriced": sorted(unpriced),
		"spending_window": sp.get("months"),
	}


@frappe.whitelist()
def exposure():
	"""How much of you is not in naira.

	A naira move is probably the largest single risk to this net worth and
	nothing showed the size of it. Converted at the rates you set, so the
	figure is only as good as those — which is why the rate and its date are
	reported alongside rather than left implied.
	"""
	require_sysadmin()
	from duty_board.money import _balances
	from duty_board.shares import _positions
	from duty_board.targets import _rate_map

	fx = _rate_map()
	bal = _balances()
	by = {}

	def add(ccy, ngn, kind):
		e = by.setdefault(ccy, {"currency": ccy, "total": 0.0, "cash": 0.0,
								"invested": 0.0, "shares": 0.0, "debt": 0.0})
		e[kind] += ngn
		e["total"] += -ngn if kind == "debt" else ngn

	unpriced = set()
	for a in frappe.get_all(
		"Duty Bank Account", filters={"active": 1},
		fields=["name", "account_type", "currency"], limit_page_length=0):
		rate = fx.get(a.currency)
		v = flt(bal.get(a.name, 0))
		if not rate:
			if abs(v) > 0.005:
				unpriced.add(a.currency)
			continue
		ngn = v * rate
		if a.account_type in ("Credit Card", "Loan"):
			add(a.currency, abs(ngn), "debt")
		elif a.account_type == "Investment":
			add(a.currency, ngn, "invested")
		else:
			add(a.currency, ngn, "cash")
	for h in _positions().values():
		if h.qty > 0 and h.last_price:
			rate = fx.get(h.currency)
			if rate:
				add(h.currency, h.value * rate, "shares")
			else:
				unpriced.add(h.currency)
	try:
		from duty_board.bonds import bond_summary

		for r in bond_summary():
			rate = fx.get(r["currency"])
			if rate:
				add(r["currency"], flt(r["value"]) * flt(rate), "invested")
			elif r["value"]:
				unpriced.add(r["currency"])
	except Exception:
		pass

	total = sum(e["total"] for e in by.values())
	for e in by.values():
		e["share"] = round(e["total"] * 100 / total, 1) if total else 0
		e["rate"] = fx.get(e["currency"])
		if e["currency"] != "NGN":
			d = frappe.db.get_value("Duty FX Rate", e["currency"], "as_of")
			e["rate_as_of"] = str(d) if d else None
	rows = sorted(by.values(), key=lambda e: -e["total"])
	foreign = sum(e["total"] for e in rows if e["currency"] != "NGN")
	return {
		"currencies": rows, "total": total,
		"foreign": foreign,
		"foreign_pct": round(foreign * 100 / total, 1) if total else 0,
		"unpriced": sorted(unpriced),
	}
