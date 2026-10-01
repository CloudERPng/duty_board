"""Growth targets — what must still go in this month, and what is owed from before.

THE WHOLE DESIGN IS ONE IDEA: measure against a cumulative line rather than a
monthly quota.

    required by month N = baseline + (monthly x months elapsed)

Miss August and September's line has already risen by two months' worth while
your actual has not, so the August shortfall is still sitting in the gap. That
is the additive behaviour asked for, and it needs no carry-forward logic, no
per-month ledger and nothing to go stale. It also means a strong month eats an
earlier miss by itself, which a quota-per-month model gets wrong — under that
model a good September would show as "done" while August stayed permanently
missed.

WHAT COUNTS AS GROWTH IS THE BALANCE ITSELF. Not deposits, not interest, not
purchases — the number. A savings account grows by deposits or by interest and
the target does not care which, which is exactly what was asked for. A share
portfolio grows by buying more or by the market moving, likewise. The
consequence worth knowing: a withdrawal counts against you, because it is a
target for what the pot is worth rather than for what you paid in.

THE BASELINE IS STORED, NOT RECOMPUTED. It could be derived from the balance on
the day, and then a correction to an old transaction would silently move the
goalposts and make a met target unmet months later. It is suggested when the
target is created and then left alone.
"""

import frappe
from frappe import _
from frappe.utils import (add_days, add_months, cint, flt, get_first_day,
							  getdate, nowdate)

from duty_board.permissions import require_sysadmin


def _month_key(d=None):
	return str(d or nowdate())[:7]


def _months_between(start_ym, end_ym):
	"""Inclusive count. August to August is 1 — one month's growth is due by
	the end of the first month, not the end of the second."""
	try:
		sy, sm = [int(x) for x in str(start_ym).split("-")[:2]]
		ey, em = [int(x) for x in str(end_ym).split("-")[:2]]
	except Exception:
		return 0
	return max(0, (ey - sy) * 12 + (em - sm) + 1)



# ─────────────────── cadence: monthly, weekly, working day ───────────────────
#
# The line generalises without changing shape:
#
#     required = baseline + amount x periods elapsed
#
# Only the definition of a period moves. What needed real thought was noise: a
# working-day target reads as failed every morning before the money goes in, and
# a dashboard that pulses red daily is one you stop seeing.
#
# So a target is not BEHIND until its period has closed. Today's amount is due;
# only a period that finished unmet is overdue. Three states rather than two —
# met, due, behind — and red keeps meaning something.
#
# Working days respect both the configured workdays and the public holidays in
# Duty Settings. accounting._working_days_between honours the first and not the
# second, which would quietly overstate every month with a holiday in it.


def _workdays_and_holidays():
	day_idx = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
	days = {0, 1, 2, 3, 4}
	hols = set()
	try:
		cfg = frappe.get_cached_doc("Duty Settings")
		raw = (cfg.get("workdays") or "").strip()
		if raw:
			parsed = {day_idx[t.strip()[:3].lower()] for t in raw.split(",")
					  if t.strip()[:3].lower() in day_idx}
			if parsed:
				days = parsed
		for h in (cfg.get("public_holidays") or []):
			d = h.get("holiday_date") or h.get("date")
			if d:
				hols.add(str(d))
	except Exception:
		pass
	return days, hols


def _working_days(d1, d2):
	"""Working days from d1 to d2 inclusive, holidays excluded."""
	from datetime import timedelta

	if not d1 or not d2:
		return 0
	d1, d2 = getdate(d1), getdate(d2)
	if d1 > d2:
		return 0
	days, hols = _workdays_and_holidays()
	n, d = 0, d1
	while d <= d2:
		if d.weekday() in days and str(d) not in hols:
			n += 1
		d = d + timedelta(days=1)
	return n


def _target_start(t):
	"""A date for every cadence. Monthly targets start on the 1st of their month."""
	if t.get("start_date"):
		return getdate(t.get("start_date"))
	return getdate(str(t.get("start_month") or _month_key()) + "-01")


def _periods(t, upto=None):
	"""Periods elapsed including the one running, and those already closed.

	The gap between the two is the grace: what is due now but not yet late.
	"""
	upto = getdate(upto or nowdate())
	start = _target_start(t)
	cad = t.get("cadence") or "Monthly"
	if upto < start:
		return 0, 0
	if cad == "Working day":
		n = _working_days(start, upto)
		return n, max(0, n - 1)
	if cad == "Weekly":
		n = (upto - start).days // 7 + 1
		return n, max(0, n - 1)
	n = _months_between(str(start)[:7], str(upto)[:7])
	return n, max(0, n - 1)


def _month_equivalent(t, when=None):
	"""What this target asks for in the CURRENT month.

	The dashboard frames everything by month because that is how cash is
	thought about, so a daily target contributes its month's worth rather than
	one day's. Counted from the periods actually falling in the month, not from
	an average, so February is not billed as though it were March.
	"""
	amt = flt(t.get("monthly_amount"))
	cad = t.get("cadence") or "Monthly"
	when = getdate(when or nowdate())
	first = get_first_day(when)
	last = getdate(str(add_months(first, 1)))
	start = _target_start(t)
	from_d = max(first, start)
	if cad == "Working day":
		to_d = add_days(last, -1)
		return amt * _working_days(from_d, to_d) if from_d <= to_d else 0.0
	if cad == "Weekly":
		to_d = add_days(last, -1)
		if from_d > to_d:
			return 0.0
		return amt * ((to_d - from_d).days // 7 + 1)
	return amt if start <= add_days(last, -1) else 0.0


def _cadence_label(t):
	cad = t.get("cadence") or "Monthly"
	return {"Working day": _("a working day"), "Weekly": _("a week")}.get(cad, _("a month"))


def _portfolio_value():
	from duty_board.shares import _positions

	out = {}
	for h in _positions().values():
		if h.qty > 0 and h.last_price:
			out[h.currency] = out.get(h.currency, 0.0) + h.value
	return out


@frappe.whitelist()
def suggest_baseline(target_kind, account=None, start_month=None):
	"""What it was worth at the start of that month, as a starting suggestion."""
	require_sysadmin()
	ym = start_month or _month_key()
	first = str(get_first_day(getdate(ym + "-01")))
	if target_kind == "Account" and account:
		from duty_board.money import _balances

		return {"baseline": flt(_balances(as_of=frappe.utils.add_days(first, -1)).get(account, 0))}
	if target_kind == "Bond Portfolio":
		# amortised cost is a straight line, so a past carrying value is exact
		# rather than a guess — no "approximate" flag needed here
		return {"baseline": flt(sum(
			_bond_value_on(first, c) for c in
			{r["currency"] for r in _bond_rows()} or {"NGN"}))}
	# For a portfolio the value on a past date needs the holdings AND the prices
	# of that day. Rather than half-reconstruct it, today's value is offered and
	# labelled as such — a wrong baseline quietly distorts every month after it.
	vals = _portfolio_value()
	return {"baseline": flt(sum(vals.values())) if vals else 0.0,
			"approximate": 1 if ym < _month_key() else 0}


@frappe.whitelist()
def targets():
	"""Every target with where it stands, this month and cumulatively."""
	require_sysadmin()
	rows = frappe.get_all(
		"Duty Growth Target", filters={"active": 1},
		fields=["name", "title", "target_kind", "account", "currency",
				"monthly_amount", "start_month", "baseline", "note",
				"cadence", "start_date"],
		order_by="target_kind asc, title asc", limit_page_length=0)
	if not rows:
		return {"targets": [], "month": _month_key()}

	from duty_board.money import _balances

	bal = _balances()
	pv = _portfolio_value()
	bv = _bond_value()
	_accs = frappe.get_all("Duty Bank Account", fields=["name", "nickname", "currency"],
						   limit_page_length=0)
	acc_names = {a.name: a.nickname for a in _accs}
	acc_ccy = {a.name: a.currency for a in _accs}

	now = _month_key()
	today = getdate(nowdate())
	month_end = getdate(str(add_months(get_first_day(today), 1)))
	days_left = max(0, (month_end - today).days)

	# what each account was worth at the start of this month, so progress made
	# SINCE then can be separated from progress made before it
	month_start = str(get_first_day(today))
	from duty_board.money import _balances as _bal_at

	start_bal = _bal_at(as_of=frappe.utils.add_days(month_start, -1))

	out = []
	for t in rows:
		elapsed, closed = _periods(t)
		if elapsed <= 0:
			continue  # not started yet
		monthly = flt(t.monthly_amount)
		base = flt(t.baseline)

		mismatch = None
		if t.target_kind == "Account":
			actual = flt(bal.get(t.account, 0))
			what = acc_names.get(t.account, t.account)
			# A target in a different currency from its account converts the
			# wrong number and understates or overstates the naira headline
			# without anything looking wrong. Caught here as well as on save,
			# since targets created before the check exist already.
			real = acc_ccy.get(t.account)
			if real and real != t.currency:
				mismatch = real
		elif t.target_kind == "Bond Portfolio":
			actual = flt(bv.get(t.currency, 0))
			what = _("Bond portfolio")
		else:
			actual = flt(pv.get(t.currency, 0))
			what = _("Share portfolio")

		# raised this month: what it is worth now against the start of the month.
		# Exact for an account. For the portfolio the value on a past date needs
		# that day's prices for every holding, so it is marked approximate rather
		# than quietly presented as a fact.
		approx = 0
		if t.target_kind == "Account":
			month_open = flt(start_bal.get(t.account, 0))
		elif t.target_kind == "Bond Portfolio":
			# Carrying value at the start of the month. Amortised cost is a
			# straight line, so a month's drift is arithmetic rather than a
			# price — no approximation and no marking needed.
			month_open = _bond_value_on(month_start, t.currency)
		else:
			# The portfolio's value at the start of the month, computed from the
			# holdings held THEN and the last close on or before that date. The
			# first version fudged it — right in the opening month and zero in
			# every month after, so the figure would have looked plausible in
			# August and then silently stopped moving.
			month_open, approx = _portfolio_value_on(month_start, t.currency)
		raised = actual - month_open

		# required now, and required by the end of the last CLOSED period. The
		# difference is grace: a working-day target is not late at nine in the
		# morning, and a dashboard that says otherwise every day is one nobody
		# reads by Thursday.
		required = base + monthly * elapsed
		required_closed = base + monthly * closed
		prev_required = required_closed
		grown = actual - base
		still = required - actual
		carried = max(0.0, required_closed - actual)

		out.append({
			"name": t.name, "title": t.title, "kind": t.target_kind,
			"what": what, "currency": t.currency, "note": t.note,
			"monthly": monthly, "start_month": t.start_month, "months": elapsed,
			"baseline": base, "actual": actual, "grown": grown,
			"required": required, "still": still,
			"carried": carried,
			"this_month": max(0.0, still - carried),
			"ahead": max(0.0, -still),
			"met": 1 if still <= 0.005 else 0,
			# three states, not two: met, due (this period is still open),
			# behind (a period closed unmet)
			"state": ("met" if still <= 0.005
					  else "behind" if carried > 0.005 else "due"),
			"cadence": t.get("cadence") or "Monthly",
			"start_date": str(t.get("start_date")) if t.get("start_date") else None,
			"cadence_label": _cadence_label(t),
			"per_period": monthly,
			"periods": elapsed,
			"month_worth": _month_equivalent(t),
			"mismatch": mismatch,
			"raised": raised, "raised_approx": approx,
			"rate": None,  # filled below, once the rate map is read
			"pct": min(100, int(grown * 100 / (monthly * elapsed))) if monthly and elapsed and grown > 0 else 0,
		})

	behind = [r for r in out if not r["met"]]

	# The headline: everything still to find, in NGN. Anything whose currency
	# has no rate is counted SEPARATELY rather than dropped or assumed at 1 —
	# a total that quietly omits a shortfall is worse than one that says it is
	# incomplete.
	fx = _rate_map()
	for r in out:
		r["rate"] = fx.get(r["currency"])
	ngn, unconverted, used = 0.0, [], {}
	ngn_month, ngn_raised = 0.0, 0.0
	# Every currency in play that has no rate. This was tracked for the
	# still-to-find figure and NOT for the month's bill or what has been raised,
	# so those two dropped foreign targets in silence — which looks exactly like
	# no conversion happening at all, and understates by the whole of the missing
	# currency. One list now covers all three.
	no_rate = {}
	for r in out:
		rate = fx.get(r["currency"])
		if rate:
			ngn_month += r["month_worth"] * rate
			ngn_raised += r["raised"] * rate
			if r["currency"] != "NGN":
				used[r["currency"]] = rate
		else:
			c = no_rate.setdefault(r["currency"], {"currency": r["currency"],
												   "monthly": 0.0, "still": 0.0})
			c["monthly"] += r["month_worth"]
	for r in behind:
		rate = fx.get(r["currency"])
		if rate:
			ngn += r["still"] * rate
		else:
			no_rate.setdefault(r["currency"], {"currency": r["currency"],
											   "monthly": 0.0, "still": 0.0})
			no_rate[r["currency"]]["still"] += r["still"]
	unconverted = list(no_rate.values())

	# Expenses belong in the same headline. Growth targets and fixed costs are
	# both "money that must be found this month", and splitting them across two
	# figures would mean doing the addition yourself every time you looked —
	# which is exactly the daily friction this is meant to remove.
	ex = expenses(now)
	ngn += flt(ex.get("ngn_outstanding") or 0)
	ngn_month += flt(ex.get("ngn_due") or 0)
	ngn_raised += flt(ex.get("ngn_paid") or 0)
	for u in ex.get("unconverted") or []:
		hit = next((x for x in unconverted if x["currency"] == u["currency"]), None)
		if hit:
			hit["still"] = hit.get("still", 0) + u["amount"]
		else:
			unconverted.append({"currency": u["currency"], "monthly": 0.0,
								"still": u["amount"]})

	# MONEY IN HAND — the balance of accounts money arrives in on its way
	# elsewhere. Deliberately NOT added to raised: raised is money that has done
	# its job, and this has not yet. Counting an inflow as raised and then the
	# expense it pays as raised again would count one note twice. As the expense
	# is paid the amount leaves this figure and appears in that one, which is a
	# pipeline rather than a double count.
	in_hand, in_hand_accs = 0.0, []
	for a_ in frappe.get_all(
		"Duty Bank Account", filters={"active": 1, "funding": 1},
		fields=["name", "nickname", "currency"], limit_page_length=0):
		v = flt(bal.get(a_.name, 0))
		rate = fx.get(a_.currency)
		if rate:
			in_hand += v * rate
		in_hand_accs.append({"nickname": a_.nickname, "currency": a_.currency,
							 "balance": v, "ngn": (v * rate) if rate else None})

	# Planned one-offs COMPETE with the targets — a television does not make a
	# savings target smaller. They are added to what the month asks for and to
	# what is still to find, so the shortfall they create is visible rather than
	# absorbed. Only what is due this month counts; October's TV is October's
	# problem and appears in the forecast, not in today's figure.
	try:
		of = outflows(6)
	except Exception:
		of = {}
	out_month = flt(of.get("this_month_ngn") or 0)
	ngn += out_month
	ngn_month += out_month

	per_day = (ngn / days_left) if days_left > 0 else None
	return {
		"targets": out, "month": now, "days_left": days_left,
		"behind": len(behind),
		# deliberately NOT a plain sum of `still` — that adds GBP to NGN and
		# produced a headline nearly a million naira light
		"mismatches": [r["title"] for r in out if r.get("mismatch")],
		"ngn_needed": ngn,
		"ngn_month": ngn_month,
		"ngn_raised": ngn_raised,
		"ngn_per_day": per_day,
		"outflow_month": out_month,
		# The list itself, not merely the totals. It was left out, so the header
		# figures were right and the panel that lists them was permanently empty
		# — the worst shape of bug, because the numbers agreeing made it look
		# like there was nothing to show.
		"outflows": of.get("outflows") or [],
		"outflow_n": of.get("this_month_n") or 0,
		"outflow_overdue": of.get("overdue") or 0,
		"outflow_by_month": of.get("by_month") or [],
		"in_hand": in_hand,
		"in_hand_accounts": in_hand_accs,
		# what is genuinely missing once money already sitting there is counted
		"shortfall": max(0.0, ngn - in_hand),
		"expenses": ex.get("expenses") or [],
		"expense_due": ex.get("ngn_due") or 0.0,
		"expense_paid": ex.get("ngn_paid") or 0.0,
		"expense_outstanding": ex.get("ngn_outstanding") or 0.0,
		"expenses_unsettled": ex.get("unsettled") or 0,
		"rates_used": used,
		"unconverted": unconverted,
		# so the interface can say a figure is incomplete rather than merely wrong
		"incomplete": 1 if unconverted else 0,
		"missing_rates": [u["currency"] for u in unconverted],
	}


@frappe.whitelist()
def save_target(name=None, **kwargs):
	require_sysadmin()
	allowed = ("title", "target_kind", "account", "currency", "monthly_amount",
			   "cadence", "start_month", "start_date", "baseline", "active", "note")
	doc = frappe.get_doc("Duty Growth Target", name) if name else frappe.new_doc("Duty Growth Target")
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not doc.title or not flt(doc.monthly_amount):
		frappe.throw(_("A target needs a name and a monthly amount."))
	if not doc.start_month or not str(doc.start_month)[:7].count("-"):
		frappe.throw(_("Starting month should look like 2026-08."))
	if doc.target_kind == "Account" and not doc.account:
		frappe.throw(_("Choose the account this applies to."))
	if doc.target_kind == "Account" and doc.account:
		real = frappe.db.get_value("Duty Bank Account", doc.account, "currency")
		if real and real != doc.currency:
			frappe.throw(_("That account is in {0}, so the target has to be in {0} too — otherwise the naira total converts the wrong number and nothing looks wrong.").format(real))
	# Changing cadence mid-stream moves the line — monthly to working-day takes
	# periods elapsed from 3 to 60 — so it needs a fresh start and baseline
	# rather than a silent recomputation that turns a met target unmet.
	if name and kwargs.get("cadence"):
		was = frappe.db.get_value("Duty Growth Target", name, "cadence") or "Monthly"
		if was != kwargs["cadence"] and not kwargs.get("start_date") and not kwargs.get("start_month"):
			frappe.throw(_("Changing how often this runs moves the whole line. Set a new starting date and opening balance at the same time."))
	if doc.cadence in ("Weekly", "Working day") and not doc.start_date:
		doc.start_date = getdate(str(doc.start_month or _month_key()) + "-01")
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def delete_target(name):
	require_sysadmin()
	frappe.delete_doc("Duty Growth Target", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


# ─────────────────────────────── rates ───────────────────────────────────────
#
# NGN IS THE HONEST DIFFICULTY HERE. Public rate APIs publish the official rate,
# and for the naira that has at times been a long way from the rate anybody
# actually transacts at. So the stored rate is YOURS: typed, dated, and marked
# with where it came from. Fetching is offered as a convenience and is labelled
# 'official' rather than presented as the rate.
#
# A converted total is only ever as good as the rate under it, so every screen
# that shows one also shows the rate and its date. A single blended number with
# no rate beside it is the thing to avoid.

FX_URL = "https://open.er-api.com/v6/latest/{base}"


@frappe.whitelist()
def rates():
	"""Every stored rate, plus which currencies still need one."""
	require_sysadmin()
	stored = {r.currency: r for r in frappe.get_all(
		"Duty FX Rate", fields=["currency", "rate_to_ngn", "as_of", "source"],
		limit_page_length=0)}
	need = set()
	for c in frappe.get_all("Duty Bank Account", filters={"active": 1},
							pluck="currency", limit_page_length=0):
		if c and c != "NGN":
			need.add(c)
	for c in frappe.get_all("Duty Holding", filters={"active": 1},
							pluck="currency", limit_page_length=0):
		if c and c != "NGN":
			need.add(c)
	today = nowdate()
	out = []
	for c in sorted(need):
		r = stored.get(c)
		out.append({
			"currency": c,
			"rate": flt(r.rate_to_ngn) if r else None,
			"as_of": str(r.as_of) if r and r.as_of else None,
			"source": (r.source if r else None),
			"stale_days": frappe.utils.date_diff(today, r.as_of) if r and r.as_of else None,
		})
	return {"rates": out, "missing": [r["currency"] for r in out if not r["rate"]]}


def _rate_map():
	m = {"NGN": 1.0}
	for r in frappe.get_all("Duty FX Rate", fields=["currency", "rate_to_ngn"],
							limit_page_length=0):
		if flt(r.rate_to_ngn) > 0:
			m[r.currency] = flt(r.rate_to_ngn)
	return m


@frappe.whitelist()
def set_rate(currency, rate_to_ngn, as_of=None, source=None):
	require_sysadmin()
	if flt(rate_to_ngn) <= 0:
		frappe.throw(_("A rate has to be above zero."))
	name = currency
	if frappe.db.exists("Duty FX Rate", name):
		frappe.db.set_value("Duty FX Rate", name, {
			"rate_to_ngn": flt(rate_to_ngn), "as_of": as_of or nowdate(),
			"source": source or "manual"})
	else:
		frappe.get_doc({"doctype": "Duty FX Rate", "currency": currency,
						"rate_to_ngn": flt(rate_to_ngn), "as_of": as_of or nowdate(),
						"source": source or "manual"}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def fetch_rates():
	"""Official rates, as a convenience. Labelled as such, never silently used.

	Only fills currencies that have no rate at all — a rate you set by hand is
	never overwritten by a published one, because you set it for a reason.
	"""
	require_sysadmin()
	import requests

	from duty_board.shares import _ipv4_only, _HEADERS

	cur = rates()
	want = [r["currency"] for r in cur["rates"]]
	if not want:
		return {"ok": 1, "set": [], "note": _("No foreign currencies in use.")}
	u3, prev = _ipv4_only()
	try:
		r = requests.get(FX_URL.format(base="NGN"), timeout=20, headers=_HEADERS)
	except Exception as e:
		return {"ok": 0, "error": str(e)[:160]}
	finally:
		u3.allowed_gai_family = prev
	if r.status_code != 200:
		return {"ok": 0, "error": "HTTP %s" % r.status_code}
	try:
		data = r.json()
		per_ngn = data.get("rates") or {}
	except Exception:
		return {"ok": 0, "error": _("Unreadable response.")}

	done, skipped = [], []
	existing = {x["currency"]: x for x in cur["rates"]}
	for c in want:
		if existing.get(c, {}).get("source") == "manual" and existing[c].get("rate"):
			skipped.append(c)
			continue
		v = flt(per_ngn.get(c))
		if v <= 0:
			continue
		# the API gives units per NGN; the stored rate is NGN per unit
		set_rate(c, 1.0 / v, as_of=nowdate(), source="official")
		done.append("%s @ %.2f" % (c, 1.0 / v))
	return {"ok": 1, "set": done, "kept_manual": skipped,
			"note": _("These are official published rates and may differ from what you would actually get. Rates you set by hand were left alone.")}



def _bond_rows():
	try:
		from duty_board.bonds import bond_summary

		return bond_summary()
	except Exception:
		return []


def _bond_value(on=None):
	"""Carrying value of the bond book, per currency."""
	out = {}
	try:
		from duty_board.bonds import bond_summary

		for r in bond_summary():
			out[r["currency"]] = out.get(r["currency"], 0.0) + flt(r["value"])
	except Exception:
		pass
	return out


def _bond_value_on(on_date, currency):
	"""What the bonds were carried at on a past date.

	Amortised cost is a straight line from purchase to par, so a past value is
	computable exactly rather than needing that day's marks — which is one
	practical advantage of carrying them this way.
	"""
	try:
		from duty_board.bonds import amortised

		total = 0.0
		for b in frappe.get_all(
			"Duty Bond", filters={"active": 1, "currency": currency},
			fields=["name", "valuation", "mark_price"], limit_page_length=0):
			v, _f = amortised(b.name, on=on_date)
			total += flt(v)
		return total
	except Exception:
		return 0.0


def _portfolio_value_on(on_date, currency):
	"""What the portfolio was worth on a date, and whether that is exact.

	Quantity held is walked from the trades up to that date, and each holding is
	priced at its last close on or before it. Where a holding has no price point
	that old, today's price is used and the answer is flagged approximate rather
	than presented as a fact — a value assembled from a mix of dates is a real
	answer, and it is not the same kind of answer as one assembled from a single
	day's closes.
	"""
	cutoff = frappe.utils.add_days(on_date, -1)
	qty = {}
	for t in frappe.get_all(
		"Duty Trade", filters={"trade_date": ["<=", cutoff]},
		fields=["holding", "kind", "quantity"],
		order_by="trade_date asc, creation asc", limit_page_length=0):
		q = flt(t.quantity)
		qty[t.holding] = qty.get(t.holding, 0.0) + (q if t.kind == "Buy" else -q)
	live = {h: q for h, q in qty.items() if q > 0.0000001}
	if not live:
		return 0.0, 0

	meta = {h.name: h for h in frappe.get_all(
		"Duty Holding", filters={"name": ["in", list(live)]},
		fields=["name", "currency", "last_price"], limit_page_length=0)}

	total, guessed = 0.0, 0
	for h, q in live.items():
		m = meta.get(h)
		if not m or m.currency != currency:
			continue
		px = frappe.db.get_value(
			"Duty Price Point",
			{"holding": h, "price_date": ["<=", cutoff]},
			"price", order_by="price_date desc")
		if px is None:
			px = flt(m.last_price)
			guessed = 1
		total += q * flt(px)
	return total, guessed


# ────────────────────────────── monthly expenses ─────────────────────────────
#
# Fixed costs behave differently from growth targets and are modelled
# differently rather than bent to fit.
#
# A TARGET IS A CUMULATIVE LINE; AN EXPENSE IS A MONTHLY OBLIGATION. Missing a
# subscription in August does not mean two are owed in September. Missed rent
# does. So carrying forward is a property of the expense, off by default,
# because only you know which kind each one is.
#
# THEY COME AND GO VIA A START AND AN END MONTH rather than by being deleted.
# An expense that ended in June should stop counting and still be true about
# June, which deleting it would not be.
#
# PAYMENT IS MARKED, NOT INFERRED. Guessing from transaction categories would be
# wrong occasionally and silently, which is the worst way to be wrong about
# money. Where a standing order pays it, that posting marks it — the machine
# knows, so you should not have to tell it.


def _expense_due(e, ym):
	"""Is this expense owed in that month?"""
	if str(ym) < str(e.start_month or ""):
		return False
	if e.end_month and str(ym) > str(e.end_month):
		return False
	return True


def _prev_months(start_ym, upto_ym, limit=36):
	out, y, m = [], None, None
	try:
		y, m = [int(x) for x in str(start_ym).split("-")[:2]]
	except Exception:
		return out
	while len(out) < limit:
		ym = "%04d-%02d" % (y, m)
		if ym >= str(upto_ym):
			break
		out.append(ym)
		m += 1
		if m > 12:
			m, y = 1, y + 1
	return out


@frappe.whitelist()
def expenses(month=None):
	"""Every expense owed this month, what is paid, and what is still owed."""
	require_sysadmin()
	ym = month or _month_key()
	rows = frappe.get_all(
		"Duty Monthly Expense", filters={"active": 1},
		fields=["name", "title", "amount", "currency", "category", "start_month",
				"end_month", "due_day", "carries_forward", "account",
				"standing_order", "note"],
		order_by="due_day asc, title asc", limit_page_length=0)
	if not rows:
		return {"expenses": [], "month": ym, "ngn_due": 0.0, "ngn_paid": 0.0,
				"ngn_outstanding": 0.0, "unconverted": []}

	paid, moved, counts = {}, {}, {}
	for p in frappe.get_all(
		"Duty Expense Payment",
		filters={"expense": ["in", [r.name for r in rows]]},
		fields=["expense", "pay_month", "amount", "money_move"], limit_page_length=0):
		# summed, not assigned: a month can hold several payments now, and
		# assigning would have counted only the last one — so a rent paid in two
		# halves would have read as half paid with the other half outstanding.
		m = paid.setdefault(p.expense, {})
		m[p.pay_month] = m.get(p.pay_month, 0.0) + flt(p.amount)
		if p.pay_month == ym:
			moved.setdefault(p.expense, p.money_move)
			counts[p.expense] = counts.get(p.expense, 0) + 1

	fx = _rate_map()
	out = []
	ngn_due = ngn_paid = 0.0
	no_rate = {}
	for e in rows:
		if not _expense_due(e, ym):
			continue
		amt = flt(e.amount)
		mine = paid.get(e.name, {})
		this_paid = flt(mine.get(ym, 0))

		# arrears, only where the expense says they accumulate
		arrears = 0.0
		if cint(e.carries_forward):
			for pm in _prev_months(e.start_month, ym):
				if e.end_month and pm > str(e.end_month):
					continue
				arrears += max(0.0, amt - flt(mine.get(pm, 0)))

		owed = max(0.0, amt + arrears - this_paid)
		rate = fx.get(e.currency)
		if rate:
			ngn_due += (amt + arrears) * rate
			ngn_paid += this_paid * rate
		else:
			c = no_rate.setdefault(e.currency, {"currency": e.currency, "amount": 0.0})
			c["amount"] += owed

		out.append({
			"name": e.name, "title": e.title, "amount": amt, "currency": e.currency,
			"category": e.category, "due_day": e.due_day, "note": e.note,
			"account": e.account, "standing_order": e.standing_order,
			"carries_forward": cint(e.carries_forward),
			"arrears": arrears, "paid": this_paid, "owed": owed,
			"settled": 1 if owed <= 0.005 else 0,
			"rate": rate, "ngn": (owed * rate) if rate else None,
			"money_move": moved.get(e.name),
			"payments": counts.get(e.name, 0),
			"part_paid": 1 if (this_paid > 0.005 and owed > 0.005) else 0,
		})

	out.sort(key=lambda r: (r["settled"], -(r["ngn"] or 0)))
	return {
		"expenses": out, "month": ym,
		"ngn_due": ngn_due, "ngn_paid": ngn_paid,
		"ngn_outstanding": sum((r["ngn"] or 0) for r in out),
		"unconverted": list(no_rate.values()),
		"count": len(out),
		"unsettled": len([r for r in out if not r["settled"]]),
	}


def _ensure_cat(name):
	if not frappe.db.exists("Duty Money Category", name):
		try:
			frappe.get_doc({"doctype": "Duty Money Category", "category_name": name,
							"kind": "Fixed cost"}).insert(ignore_permissions=True)
		except Exception:
			return None
	return name


@frappe.whitelist()
def mark_expense_paid(expense, month=None, amount=None, paid_on=None,
					  source="manual", account=None, move_cash=1):
	"""Settle one month of one expense, and take the money out of an account.

	Ticking used to record only that it was settled, leaving the payment to be
	entered separately — two actions for one event, and either half could be
	forgotten. A dashboard saying paid while the balance still holds the money,
	or the reverse, is worse than one that asks a question.

	Skippable, for a payment already recorded some other way. Where a standing
	order settles this, the order has already moved the money and nothing more
	is posted.
	"""
	require_sysadmin()
	ym = month or _month_key()
	e = frappe.get_doc("Duty Monthly Expense", expense)
	amt = flt(amount) if amount is not None else flt(e.amount)
	name = "%s::%s" % (expense, ym)
	on = paid_on or nowdate()

	acc = account or e.account
	mv = None
	if acc and cint(move_cash) and source != "standing order":
		acc_ccy = frappe.db.get_value("Duty Bank Account", acc, "currency")
		if acc_ccy != e.currency:
			mv = {"skipped": _("That account is in {0} and the cost is in {1}, so the money was not moved — record it on the account with the amount that actually left.").format(acc_ccy, e.currency)}
		else:
			doc = frappe.get_doc({
				"doctype": "Duty Money Move", "move_date": on, "kind": "Out",
				"account": acc, "amount": abs(amt),
				"category": e.category or _ensure_cat(_("Fixed cost")),
				"counterparty": e.title,
				"note": _("{0} — {1}").format(e.title, ym),
			})
			doc.insert(ignore_permissions=True)
			mv = {"name": doc.name, "amount": abs(amt), "account": acc}

	# EVERY PAYMENT IS ITS OWN RECORD. The name used to be expense::month, so a
	# month could hold exactly one — a second payment replaced the first and
	# tried to delete its movement, which the link correctly refused. Rent paid
	# in two halves, or a bill part-settled and finished later, is ordinary and
	# was impossible.
	payload = {"amount": amt, "paid_on": on, "source": source}
	if mv and mv.get("name"):
		payload["money_move"] = mv["name"]
	frappe.get_doc(dict({"doctype": "Duty Expense Payment", "expense": expense,
						 "pay_month": ym}, **payload)).insert(ignore_permissions=True)
	frappe.db.commit()
	paid = _paid_for(expense, ym)
	return {"ok": 1, "cash": mv, "paid": paid, "due": flt(e.amount),
			"outstanding": max(0.0, flt(e.amount) - paid),
			"settled": 1 if paid + 0.005 >= flt(e.amount) else 0}


def _paid_for(expense, ym):
	"""Everything paid against one month of one cost."""
	return sum(flt(r.amount) for r in frappe.get_all(
		"Duty Expense Payment", filters={"expense": expense, "pay_month": ym},
		fields=["amount"], limit_page_length=0))


@frappe.whitelist()
def unmark_expense_paid(expense, month=None, all_of_them=0):
	"""Unsettle a month, and take its payment back out with it.

	Leaving the movement behind would quietly overstate what was spent and leave
	a payment nobody could account for.
	"""
	require_sysadmin()
	ym = month or _month_key()
	# Removes the LAST payment, not the month. Where a cost was paid in
	# instalments, unticking should undo the most recent one rather than wipe
	# the lot — the earlier payments really happened.
	rows = frappe.get_all(
		"Duty Expense Payment", filters={"expense": expense, "pay_month": ym},
		fields=["name", "money_move", "amount"],
		order_by="paid_on desc, creation desc", limit_page_length=0)
	if not rows:
		return {"ok": 1, "removed": 0}
	if cint(all_of_them):
		targets_ = rows
	else:
		targets_ = rows[:1]
	for r in targets_:
		if r.money_move and frappe.db.exists("Duty Money Move", r.money_move):
			# the payment goes first, or its link forbids removing the movement
			frappe.db.set_value("Duty Expense Payment", r.name, "money_move", None)
			frappe.delete_doc("Duty Money Move", r.money_move, ignore_permissions=True)
		frappe.delete_doc("Duty Expense Payment", r.name, ignore_permissions=True)
	frappe.db.commit()
	left = _paid_for(expense, ym)
	return {"ok": 1, "removed": len(targets_), "still_paid": left,
			"remaining": len(rows) - len(targets_)}


@frappe.whitelist()
def save_expense(name=None, **kwargs):
	require_sysadmin()
	allowed = ("title", "amount", "currency", "category", "start_month", "end_month",
			   "due_day", "carries_forward", "account", "standing_order", "active", "note")
	doc = frappe.get_doc("Duty Monthly Expense", name) if name else frappe.new_doc("Duty Monthly Expense")
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not doc.title or not flt(doc.amount):
		frappe.throw(_("An expense needs a name and an amount."))
	if doc.end_month and doc.start_month and str(doc.end_month) < str(doc.start_month):
		frappe.throw(_("It cannot end before it starts."))
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def delete_expense(name):
	require_sysadmin()
	frappe.db.delete("Duty Expense Payment", {"expense": name})
	frappe.delete_doc("Duty Monthly Expense", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


def on_standing_order_posted(standing_order, on_date=None):
	"""Called when a standing order posts — settles whatever it pays.

	The machine already knows this happened, so you should not have to tell it.
	"""
	ym = str(on_date or nowdate())[:7]
	for e in frappe.get_all("Duty Monthly Expense",
							filters={"standing_order": standing_order, "active": 1},
							fields=["name", "amount"], limit_page_length=0):
		try:
			mark_expense_paid(e.name, ym, e.amount, on_date, source="standing order")
		except Exception:
			frappe.log_error(frappe.get_traceback()[-800:], "expense auto-settle")


# ─────────────────────────── planned one-off outflows ────────────────────────
#
# A one-off is neither a fixed cost nor a standing order. It does not recur, so
# it must not carry forward when missed; it does not post itself, because
# deciding to spend it is the point.
#
# IT COMPETES WITH THE TARGETS RATHER THAN PAUSING THEM. Buying a television
# does not make a savings target smaller. The month's requirement stands and the
# outflow sits beside it, so the shortfall is visible rather than absorbed — the
# figure that answers "can I actually afford this given what I have already
# promised myself".

OUTFLOW_OPEN = ("Planned", "Committed")


@frappe.whitelist()
def outflows(months=6):
	"""Everything planned ahead, with what each month asks for."""
	require_sysadmin()
	rows = frappe.get_all(
		"Duty Planned Outflow",
		filters={"status": ["in", list(OUTFLOW_OPEN) + ["Done"]]},
		fields=["name", "title", "amount", "currency", "due_on", "confidence",
				"status", "account", "category", "money_move", "note"],
		order_by="due_on asc", limit_page_length=0)
	fx = _rate_map()
	today = nowdate()
	horizon = str(add_months(getdate(today), abs(cint(months) or 6)))

	acc = {a.name: a.nickname for a in frappe.get_all(
		"Duty Bank Account", fields=["name", "nickname"], limit_page_length=0)}

	out, by_month = [], {}
	for r in rows:
		d = str(r.due_on)
		rate = fx.get(r.currency)
		ngn = flt(r.amount) * rate if rate else None
		days = frappe.utils.date_diff(d, today)
		r_ = {
			"name": r.name, "title": r.title, "amount": flt(r.amount),
			"currency": r.currency, "due_on": d, "days": days,
			"confidence": r.confidence or "Certain", "status": r.status,
			"account": r.account, "account_name": acc.get(r.account),
			"category": r.category, "note": r.note,
			"money_move": r.money_move, "ngn": ngn,
			"overdue": 1 if (days < 0 and r.status in OUTFLOW_OPEN) else 0,
		}
		out.append(r_)
		if r.status in OUTFLOW_OPEN and d <= horizon and ngn is not None:
			m = by_month.setdefault(d[:7], {"month": d[:7], "likely": 0.0, "all": 0.0, "n": 0})
			m["all"] += ngn
			# only what is Certain counts toward the firm line; Likely and Maybe
			# widen the worst case rather than the commitment
			if (r.confidence or "Certain") == "Certain":
				m["likely"] += ngn
			m["n"] += 1

	openrows = [r for r in out if r["status"] in OUTFLOW_OPEN]
	this_month = _month_key()
	tm = [r for r in openrows if r["due_on"][:7] == this_month]
	return {
		"outflows": out,
		"open": len(openrows),
		"this_month_ngn": sum((r["ngn"] or 0) for r in tm),
		"this_month_n": len(tm),
		"overdue": len([r for r in openrows if r["overdue"]]),
		"by_month": [by_month[k] for k in sorted(by_month)],
		"unconverted": sorted({r["currency"] for r in openrows if r["ngn"] is None}),
	}


@frappe.whitelist()
def save_outflow(name=None, **kwargs):
	require_sysadmin()
	allowed = ("title", "amount", "currency", "due_on", "confidence", "status",
			   "account", "category", "note")
	doc = (frappe.get_doc("Duty Planned Outflow", name) if name
		   else frappe.new_doc("Duty Planned Outflow"))
	was_done = doc.get("status") == "Done"
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not doc.title or not flt(doc.amount):
		frappe.throw(_("A planned outflow needs a name and an amount."))
	if not doc.due_on:
		frappe.throw(_("When do you expect to spend it?"))
	doc.save(ignore_permissions=True)

	# Marking it done posts the money, the same as paying a fixed cost — the
	# alternative is a dashboard that says spent while the balance still holds it.
	if doc.status == "Done" and not was_done and not doc.money_move:
		_post_outflow(doc)
	elif doc.status != "Done" and was_done and doc.money_move:
		_unpost_outflow(doc)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


def _post_outflow(doc):
	if not doc.account:
		frappe.throw(_("Say which account it came out of before marking it done."))
	acc_ccy = frappe.db.get_value("Duty Bank Account", doc.account, "currency")
	if acc_ccy != doc.currency:
		frappe.throw(_("That account is in {0} and this is in {1}. Record the movement on the account with the amount that actually left.").format(acc_ccy, doc.currency))
	mv = frappe.get_doc({
		"doctype": "Duty Money Move", "move_date": doc.due_on, "kind": "Out",
		"account": doc.account, "amount": abs(flt(doc.amount)),
		"category": doc.category or _ensure_cat(_("One-off")),
		"counterparty": doc.title,
		"note": _("Planned: {0}").format(doc.title),
	})
	mv.insert(ignore_permissions=True)
	doc.db_set("money_move", mv.name, update_modified=False)


def _unpost_outflow(doc):
	"""Un-doing removes the payment with it, or the spend is counted twice."""
	if doc.money_move and frappe.db.exists("Duty Money Move", doc.money_move):
		frappe.delete_doc("Duty Money Move", doc.money_move, ignore_permissions=True)
	doc.db_set("money_move", None, update_modified=False)


@frappe.whitelist()
def delete_outflow(name):
	require_sysadmin()
	doc = frappe.get_doc("Duty Planned Outflow", name)
	if doc.money_move and frappe.db.exists("Duty Money Move", doc.money_move):
		frappe.delete_doc("Duty Money Move", doc.money_move, ignore_permissions=True)
	frappe.delete_doc("Duty Planned Outflow", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}
