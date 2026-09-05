# Copyright (c) 2026, Xlevel Retail Systems Ltd
# For license information, please see license.txt

"""FGN and other bonds, which are not shares with a coupon.

Four things make them different, and each of them would produce a wrong number
if the equity model were reused:

  * QUOTED PER 100 OF FACE. A price of 96.80 against 5,000,000 of face means
    4,840,000, not 96.80 a unit.
  * BOUGHT WITH ACCRUED INTEREST. Between coupon dates you pay the seller the
    interest they earned and get it back at the next coupon. It is a
    prepayment, not a cost. On a 5m purchase that can be 300,000 misallocated —
    the holding looks that much more expensive and the first coupon looks like
    a windfall.
  * REPAID AT PAR. Maturity returns capital; it is not a gain.
  * PRICE PULLS TO PAR REGARDLESS. A bond bought at 96.80 drifts to 100 because
    maturity approaches, not because anything happened. Carrying it at
    amortised cost reports that drift as what it is; carrying it at market and
    calling the drift a gain does not.

TAX. Interest on FGN and State bonds is exempt under s.163(1)(n) of the Nigeria
Tax Act 2025. The 10% withholding on short-term instruments applies where the
remaining tenor at payment falls under a year, so the SAME bond is exempt for
most of its life and taxed on its final coupons — which makes exemption a
property of each payment rather than of the holding.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

from duty_board.permissions import require_sysadmin

WHT = 0.10
# a coupon paid with less than this remaining to maturity is treated as
# short-term and withheld against
SHORT_TERM_DAYS = 365


def _sched(bond, since=None):
	"""Coupon dates six months apart, ending at maturity.

	Anchored on the earliest of the stated coupon date and when you first bought
	— not walked back indefinitely. My first version walked back to the earliest
	date the arithmetic allowed and produced eighty-one coupons reaching to 1994
	on a 2034 bond, which is true of the instrument and useless to a holder.
	"""
	first, mat = getdate(bond.first_coupon), getdate(bond.maturity)
	floor = getdate(since) if since else first
	d = first
	guard = 0
	while d > floor and guard < 120:
		guard += 1
		d = add_months(d, -6)
	out = []
	while d <= mat and len(out) < 120:
		out.append(str(d))
		d = add_months(d, 6)
	return out


def _bracket(bond, on):
	"""The coupon dates either side of a settlement date.

	The schedule is anchored on the first coupon, so a settlement BEFORE it has
	no preceding date in the list. That is the ordinary case for a bond bought
	shortly after issue, and my first version returned zero accrued for it —
	silently, which is the worst way to be wrong about money. The bracket is
	extended backwards as far as the settlement needs.
	"""
	dates = _sched(bond, since=on)
	prev = None
	for d in dates:
		if d <= str(on):
			prev = d
		else:
			return prev or str(add_months(getdate(d), -6)), d
	return prev, None


def accrued_on(bond, face, on):
	"""Interest the seller has earned since the last coupon, day-counted."""
	prev, nxt = _bracket(bond, on)
	if not prev or not nxt:
		return 0.0, 0, 0
	period = (getdate(nxt) - getdate(prev)).days
	held = (getdate(on) - getdate(prev)).days
	if period <= 0 or held <= 0:
		return 0.0, held, period
	half = flt(face) * flt(bond.coupon_rate) / 100.0 / 2.0
	return half * held / period, held, period


def _taxed(bond, pay_date):
	"""Whether a coupon on this date bears withholding.

	FGN and State are exempt outright. For anything else, and for the final
	stretch of a government bond where the paying agent applies the short-term
	rule, the remaining tenor at payment decides it — which is why this is
	asked per payment and not per bond.
	"""
	if (bond.issuer or "FGN") in ("Corporate", "Other"):
		return True
	return (getdate(bond.maturity) - getdate(pay_date)).days < SHORT_TERM_DAYS


@frappe.whitelist()
def bond_schedule(bond, face_value=None):
	"""The coupon calendar, each payment marked exempt or taxed."""
	require_sysadmin()
	b = frappe.get_doc("Duty Bond", bond)
	face = flt(face_value) or _position(bond)["face"]
	half = face * flt(b.coupon_rate) / 100.0 / 2.0
	bought = frappe.db.get_value(
		"Duty Bond Trade", {"bond": bond, "kind": "Buy"}, "trade_date",
		order_by="trade_date asc")
	paid = {str(r.pay_date) for r in frappe.get_all(
		"Duty Coupon", filters={"bond": bond}, fields=["pay_date"], limit_page_length=0)}
	out = []
	for d in _sched(b, since=bought):
		t = _taxed(b, d)
		out.append({
			"date": d, "gross": half,
			"tax": half * WHT if t else 0.0,
			"net": half * (1 - WHT) if t else half,
			"taxed": 1 if t else 0,
			"paid": 1 if d in paid else 0,
			"future": 1 if d > nowdate() else 0,
		})
	first_taxed = next((x["date"] for x in out if x["taxed"] and not x["paid"]), None)
	return {
		"bond": bond, "face": face, "rows": out,
		"first_taxed": first_taxed,
		"exempt_note": (_("FGN and State coupons are exempt from tax. The final coupons are shown as taxed because the paying agent applies the short-term rule once under a year remains.")
						if (b.issuer or "FGN") in ("FGN", "State")
						else _("Corporate coupons bear 10% withholding throughout.")),
	}


def _position(bond):
	"""Face held, what was paid for it, and accrued still outstanding."""
	b = frappe.get_doc("Duty Bond", bond)
	face = cost = acc_out = 0.0
	for t in frappe.get_all(
		"Duty Bond Trade", filters={"bond": bond},
		fields=["kind", "trade_date", "face_value", "clean_price", "accrued", "charges"],
		order_by="trade_date asc, creation asc", limit_page_length=0):
		principal = flt(t.face_value) * flt(t.clean_price) / 100.0
		if t.kind == "Buy":
			face += flt(t.face_value)
			cost += principal + flt(t.charges)
			acc_out += flt(t.accrued)
		else:
			if face > 0:
				cost -= cost * min(flt(t.face_value), face) / face
			face -= flt(t.face_value)
	# accrued already returned by coupons received since
	returned = sum(flt(r.accrued_returned) for r in frappe.get_all(
		"Duty Coupon", filters={"bond": bond},
		fields=["accrued_returned"], limit_page_length=0))
	return {"face": face, "cost": cost, "accrued_outstanding": max(0.0, acc_out - returned)}


def amortised(bond, on=None):
	"""Carrying value: what you paid, drifting to par as maturity approaches.

	Straight line between the weighted purchase date and maturity. Not the
	effective-interest method an auditor would use, and said so rather than
	implied — for a personal book the difference is small and the simplicity is
	worth more than the last decimal.
	"""
	b = frappe.get_doc("Duty Bond", bond)
	pos = _position(bond)
	if pos["face"] <= 0:
		return 0.0, None
	on = str(on or nowdate())
	first = frappe.db.get_value(
		"Duty Bond Trade", {"bond": bond, "kind": "Buy"}, "trade_date",
		order_by="trade_date asc")
	if not first:
		return pos["cost"], None
	total = (getdate(b.maturity) - getdate(first)).days
	gone = (getdate(on) - getdate(first)).days
	if total <= 0:
		return pos["face"], 1.0
	frac = max(0.0, min(1.0, gone / total))
	return pos["cost"] + (pos["face"] - pos["cost"]) * frac, frac


def net_ytm(bond, face, price_per_100, settle):
	"""Yield to maturity, net of withholding where it applies.

	Bisection on the half-year discount rate. Coupons are taxed or not by their
	own remaining tenor, which is what makes this worth computing rather than
	reading off the coupon rate.
	"""
	b = frappe.get_doc("Duty Bond", bond)
	half = flt(face) * flt(b.coupon_rate) / 100.0 / 2.0
	settle = getdate(settle)
	flows = []
	for d in _sched(b):
		if getdate(d) <= settle:
			continue
		net = half * (1 - WHT) if _taxed(b, d) else half
		flows.append((getdate(d), net))
	flows.append((getdate(b.maturity), flt(face)))
	price = flt(face) * flt(price_per_100) / 100.0
	if price <= 0 or not flows:
		return None
	lo, hi = 0.0001, 2.0
	for _i in range(200):
		r = (lo + hi) / 2
		pv = sum(a / (1 + r / 2) ** (((d - settle).days) / 182.5) for d, a in flows)
		if pv > price:
			lo = r
		else:
			hi = r
	return round((lo + hi) / 2 * 100, 3)


@frappe.whitelist()
def save_bond(name=None, **kwargs):
	require_sysadmin()
	allowed = ("bond_name", "issuer", "currency", "coupon_rate", "first_coupon",
			   "maturity", "broker", "active", "valuation", "mark_price", "mark_on", "note")
	doc = frappe.get_doc("Duty Bond", name) if name else frappe.new_doc("Duty Bond")
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not doc.bond_name:
		frappe.throw(_("Name the bond as the market quotes it."))
	if doc.maturity and doc.first_coupon and getdate(doc.first_coupon) > getdate(doc.maturity):
		frappe.throw(_("The coupon date cannot be after maturity."))
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


@frappe.whitelist()
def record_bond_trade(bond, kind, face_value, clean_price, trade_date=None,
					  source="Secondary", charges=0, account=None, note=None,
					  move_cash=1):
	"""Buy or sell, with accrued interest computed rather than typed.

	An auction fills at par on a coupon date, so no accrued changes hands; a
	secondary purchase between coupon dates does. Getting that wrong is the
	single largest misstatement available here.
	"""
	require_sysadmin()
	b = frappe.get_doc("Duty Bond", bond)
	face, clean = flt(face_value), flt(clean_price)
	if face <= 0:
		frappe.throw(_("Face value has to be more than nothing."))
	on = trade_date or nowdate()
	if getdate(on) > getdate(b.maturity):
		frappe.throw(_("That is after the bond matures."))

	acc = 0.0
	if source == "Secondary":
		acc, _held, _period = accrued_on(b, face, on)

	if kind == "Sell":
		held = _position(bond)["face"]
		if face > held + 0.005:
			frappe.throw(_("You hold {0} of face, so {1} cannot be sold.").format(held, face))

	principal = face * clean / 100.0
	ch = flt(charges)
	cash = (principal + acc + ch) if kind == "Buy" else (principal + acc - ch)

	doc = frappe.get_doc({
		"doctype": "Duty Bond Trade", "bond": bond, "kind": kind, "source": source,
		"trade_date": on, "face_value": face, "clean_price": clean,
		"accrued": acc, "charges": ch, "cash": cash,
		"account": account or None, "note": note or None,
	})
	doc.insert(ignore_permissions=True)

	moved = None
	if account and cint(move_cash):
		acc_ccy = frappe.db.get_value("Duty Bank Account", account, "currency")
		if acc_ccy != b.currency:
			moved = {"skipped": _("That account is in {0} and the bond in {1}, so the cash was not posted.").format(acc_ccy, b.currency)}
		else:
			mv = frappe.get_doc({
				"doctype": "Duty Money Move", "move_date": on,
				"kind": "Out" if kind == "Buy" else "In",
				"account": account, "amount": abs(cash),
				"category": _cat(),
				"counterparty": b.bond_name,
				"note": _("{0} {1} of {2}").format(kind, face, b.bond_name),
			})
			mv.insert(ignore_permissions=True)
			doc.db_set("cash_move", mv.name, update_modified=False)
			moved = {"name": mv.name, "amount": abs(cash)}
	frappe.db.commit()
	return {"ok": 1, "name": doc.name, "accrued": acc, "principal": principal,
			"cash": cash, "moved": moved,
			"ytm": net_ytm(bond, face, clean, on) if kind == "Buy" else None}


def _cat():
	from duty_board.shares import _ensure_category

	return _ensure_category(_("Bonds"), "Not spending")


@frappe.whitelist()
def record_coupon(bond, gross, pay_date=None, tax=None, account=None,
				  note=None, move_cash=1):
	"""A coupon received, with any prepaid accrued separated out of income.

	The tax is worked out from the issuer and the remaining tenor unless you
	state it, because the paying agent's deduction is the fact that matters and
	it will not always match the rule.
	"""
	require_sysadmin()
	b = frappe.get_doc("Duty Bond", bond)
	on = pay_date or nowdate()
	g = flt(gross)
	if g <= 0:
		frappe.throw(_("A coupon has to be more than nothing."))
	t = flt(tax) if tax is not None else (g * WHT if _taxed(b, on) else 0.0)
	if t > g:
		frappe.throw(_("Withholding cannot exceed the gross."))
	net = g - t

	# the accrued you prepaid comes back in this coupon and is not income
	outstanding = _position(bond)["accrued_outstanding"]
	returned = min(outstanding, net)

	doc = frappe.get_doc({
		"doctype": "Duty Coupon", "bond": bond, "pay_date": on,
		"gross": g, "tax": t, "net": net,
		"accrued_returned": returned, "income": net - returned,
		"account": account or None, "note": note or None,
	})
	doc.insert(ignore_permissions=True)

	moved = None
	if account and cint(move_cash):
		acc_ccy = frappe.db.get_value("Duty Bank Account", account, "currency")
		if acc_ccy == b.currency:
			mv = frappe.get_doc({
				"doctype": "Duty Money Move", "move_date": on, "kind": "In",
				"account": account, "amount": net, "category": _cat(),
				"counterparty": b.bond_name,
				"note": _("Coupon - {0}").format(b.bond_name),
			})
			mv.insert(ignore_permissions=True)
			doc.db_set("money_move", mv.name, update_modified=False)
			moved = {"name": mv.name, "amount": net}
		else:
			moved = {"skipped": _("Account currency differs from the bond; cash not posted.")}
	frappe.db.commit()
	return {"ok": 1, "name": doc.name, "net": net,
			"accrued_returned": returned, "income": net - returned, "moved": moved}


@frappe.whitelist()
def bonds():
	"""Every bond held, carried as chosen, with income and yield."""
	require_sysadmin()
	rows, by_ccy = [], {}
	for b in frappe.get_all(
		"Duty Bond", filters={"active": 1},
		fields=["name", "bond_name", "issuer", "currency", "coupon_rate",
				"first_coupon", "maturity", "broker", "valuation", "mark_price", "mark_on"],
		order_by="maturity asc", limit_page_length=0):
		pos = _position(b.name)
		# A bond you hold none of still belongs on the list. Filtering it out
		# meant a newly created bond had no row, and therefore no Buy button —
		# so the first purchase was impossible to record. It shows as "none
		# held yet" instead.
		held = pos["face"] > 0.005
		amt, frac = amortised(b.name)
		if b.valuation == "Manual mark" and flt(b.mark_price):
			value = pos["face"] * flt(b.mark_price) / 100.0
			basis = _("marked at {0}").format(b.mark_price)
		else:
			value = amt
			basis = _("amortised cost")
		coupons = frappe.get_all(
			"Duty Coupon", filters={"bond": b.name},
			fields=["gross", "tax", "net", "income", "pay_date"], limit_page_length=0)
		income = sum(flt(c.income) for c in coupons)
		first_buy = frappe.db.get_value(
			"Duty Bond Trade", {"bond": b.name, "kind": "Buy"},
			["trade_date", "clean_price"], as_dict=True, order_by="trade_date asc")
		days_left = (getdate(b.maturity) - getdate(nowdate())).days
		rows.append(dict(b, **{
			"held": 1 if held else 0,
			"face": pos["face"], "cost": pos["cost"],
			"accrued_outstanding": pos["accrued_outstanding"],
			"value": value, "basis": basis, "amortised_frac": frac,
			"income": income, "coupons": len(coupons),
			"unrealised": value - pos["cost"],
			"days_to_maturity": days_left,
			"years_to_maturity": round(days_left / 365.0, 1),
			"ytm": (net_ytm(b.name, pos["face"], flt(first_buy.clean_price), first_buy.trade_date)
					if first_buy else None),
			"running_yield": (round(pos["face"] * flt(b.coupon_rate) / 100.0 * 100 / value, 2)
							  if value else None),
		}))
		if not held:
			continue
		c = by_ccy.setdefault(b.currency, {"currency": b.currency, "face": 0.0,
										   "value": 0.0, "cost": 0.0, "income": 0.0,
										   "annual_coupon": 0.0})
		c["face"] += pos["face"]
		c["value"] += value
		c["cost"] += pos["cost"]
		c["income"] += income
		c["annual_coupon"] += pos["face"] * flt(b.coupon_rate) / 100.0
	for c in by_ccy.values():
		c["running_yield"] = (round(c["annual_coupon"] * 100 / c["value"], 2)
							  if c["value"] else None)
	return {"bonds": rows, "by_currency": sorted(by_ccy.values(), key=lambda c: -c["value"])}


@frappe.whitelist()
def coupon_calendar(months=18):
	"""What is due, across every bond, so income can be planned rather than noticed."""
	require_sysadmin()
	until = str(add_months(getdate(nowdate()), abs(cint(months) or 18)))
	out = []
	for b in frappe.get_all("Duty Bond", filters={"active": 1},
							fields=["name", "bond_name", "currency"], limit_page_length=0):
		# a coupon of zero on a bond you own none of is noise, and it was
		# filling the calendar with "NGN 0.00" entries
		if _position(b.name)["face"] <= 0.005:
			continue
		s = bond_schedule(b.name)
		for r in s["rows"]:
			if r["future"] and r["date"] <= until:
				out.append(dict(r, bond=b.name, bond_name=b.bond_name,
								currency=b.currency))
	out.sort(key=lambda r: r["date"])
	by_month = {}
	for r in out:
		m = by_month.setdefault(r["date"][:7], {"month": r["date"][:7], "net": 0.0, "n": 0})
		m["net"] += r["net"]
		m["n"] += 1
	return {"rows": out[:60], "by_month": [by_month[k] for k in sorted(by_month)],
			"next": out[0] if out else None,
			"twelve_month_net": sum(r["net"] for r in out
									if r["date"] <= str(add_months(getdate(nowdate()), 12)))}


def bond_summary():
	"""One tile per currency for the money rail.

	Bonds sit OUTSIDE the target weights — those govern equities, where a
	position can be sized freely. A bond comes in lots and is bought to be held,
	so it is an allocation decision of its own rather than a slice of the same
	pie. It gets its own line and its own total.
	"""
	out = {}
	try:
		data = bonds()
	except Exception:
		return []
	for c in data.get("by_currency", []):
		out[c["currency"]] = {
			"currency": c["currency"],
			"value": c["value"],
			"cost": c["cost"],
			"face": c["face"],
			"annual_coupon": c["annual_coupon"],
			"running_yield": c.get("running_yield"),
			"income": c["income"],
			"holdings": len([b for b in data.get("bonds", [])
							 if b["currency"] == c["currency"] and b.get("held")]),
		}
	return sorted(out.values(), key=lambda x: -x["value"])
