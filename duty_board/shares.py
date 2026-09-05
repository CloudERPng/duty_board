"""Shares — individual holdings, trades, and what they have actually made.

COST BASIS IS WEIGHTED AVERAGE, and that is a decision rather than an accident.

FIFO would be more faithful to how a tax authority looks at a disposal, and it
is meaningfully harder: every sell has to be matched against particular earlier
buys, and the answer changes depending on which. Weighted average is what most
personal portfolio tools use, it is stable, and it cannot be argued with once
stated. It IS stated — on the screen, not just here — because a costing method
applied silently to somebody's money is the kind of assumption that only
surfaces when it has already misled them.

If these numbers ever need to go on a tax return, they are a starting point and
not a filing. That is said on screen too.

NOTHING IS STORED THAT CAN BE DERIVED. Quantity held, average cost, realised
gain and unrealised gain are all walked from the trades every time they are
asked for. A stored position drifts the first time a trade is corrected or
back-dated, and then quietly lies.

The walk is chronological because it has to be: a sale's realised gain depends
on the average cost AT THAT MOMENT, not on the average cost today. Selling half
a holding before a later cheap purchase gives a different answer from selling it
after, and only a chronological walk gets that right.

Prices are entered by hand. Nothing here fetches a quote — there is no API key,
no dependency to rot, and a stale price is visible as a date rather than hidden
behind a number that looks live.
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

from duty_board.permissions import require_sysadmin


def _positions():
	"""Walk every trade in date order and return the state of each holding.

	One query for holdings, one for trades. Never per holding.
	"""
	holdings = {
		h.name: h
		for h in frappe.get_all(
			"Duty Holding",
			fields=["name", "symbol", "holding_name", "currency", "exchange",
					"last_price", "price_as_of", "checked_on", "active", "note", "target_weight",
					"pe_ratio", "forward_pe", "eps", "market_cap",
					"week52_low", "week52_high", "next_earnings",
					"financial_year_end", "fundamentals_as_of"],
			limit_page_length=0,
		)
	}
	if not holdings:
		return {}

	for h in holdings.values():
		h.qty = 0.0
		h.cost = 0.0            # cost of what is still held
		h.realised = 0.0        # gain banked on sales, after charges
		h.invested = 0.0        # cash out on buys, charges included
		h.returned = 0.0        # cash back from sales, charges deducted
		h.trades = 0
		h.first_trade = None
		h.last_trade = None

	# A parcel belongs to a broker, so the same holding can sit at two of them.
	# The walk stays per holding — average cost and realised gain are properties
	# of the position, not of where it is kept — and a per-broker split is
	# carried alongside for the views that need it.
	for h in holdings.values():
		h.brokers = {}

	for t in frappe.get_all(
		"Duty Trade",
		fields=["name", "holding", "kind", "trade_date", "quantity", "price",
				"charges", "account", "note", "broker"],
		order_by="trade_date asc, creation asc",
		limit_page_length=0,
	):
		h = holdings.get(t.holding)
		if not h:
			continue
		bk = t.broker or _("Unassigned")
		b_ = h.brokers.setdefault(bk, {"broker": bk, "qty": 0.0, "cost": 0.0})
		q, px, ch = flt(t.quantity), flt(t.price), flt(t.charges)
		h.trades += 1
		h.first_trade = h.first_trade or str(t.trade_date)
		h.last_trade = str(t.trade_date)

		if t.kind == "Buy":
			# charges are part of what the shares cost you
			h.cost += q * px + ch
			h.qty += q
			h.invested += q * px + ch
			b_["qty"] += q
			b_["cost"] += q * px + ch
		else:
			if h.qty <= 0:
				continue
			sold = min(q, h.qty)
			# average cost AT THIS MOMENT — the reason this walk is chronological
			avg = h.cost / h.qty if h.qty else 0.0
			proceeds = sold * px - ch
			h.realised += proceeds - (avg * sold)
			h.cost -= avg * sold
			h.qty -= sold
			h.returned += proceeds
			# a sale reduces the parcel at the broker it was sold from
			bsold = min(sold, b_["qty"])
			if b_["qty"] > 0:
				b_["cost"] -= (b_["cost"] / b_["qty"]) * bsold
			b_["qty"] -= bsold

	divs = _dividend_map()
	for h in holdings.values():
		d = divs.get(h.name) or {}
		h.div_net = flt(d.get("net", 0))
		h.div_tax = flt(d.get("tax", 0))
		h.div_12m = flt(d.get("net_12m", 0))
		h.avg_cost = (h.cost / h.qty) if h.qty > 0 else 0.0
		h.value = h.qty * flt(h.last_price) if h.last_price else 0.0
		h.unrealised = (h.value - h.cost) if (h.qty > 0 and h.last_price) else 0.0
		# total return is capital plus income. Reporting only capital makes a
		# high-yield holding look inert, which on the NGX is a common and
		# expensive misreading.
		h.total_gain = h.realised + h.unrealised + h.div_net
		h.yield_pct = (round(h.div_12m * 100 / h.value, 2)
					   if (h.value and h.div_12m) else None)
		# against what was actually put in — `invested` is cash out on buys,
		# charges included. I first wrote `contributed`, which is not a field on
		# this object at all and threw on the first request the money page makes.
		h.total_return_pct = (round((h.unrealised + h.realised + h.div_net) * 100 / h.invested, 2)
							  if flt(h.invested) > 0 else None)
		h.gain_pct = (round(h.unrealised * 100 / h.cost, 2)
					  if h.cost > 0 and h.last_price else None)
		h.open = 1 if h.qty > 0.0000001 else 0
		for b2_ in h.brokers.values():
			b2_["value"] = b2_["qty"] * flt(h.last_price) if h.last_price else 0.0
		h.broker_list = sorted(
			[b2_ for b2_ in h.brokers.values() if b2_["qty"] > 0.0000001],
			key=lambda x: -x["value"])
		# a holding with no trades is one being watched rather than owned; one
		# with trades and nothing left is closed. Three different things.
		h.watching = 1 if not h.trades else 0
		# two different facts, and conflating them made a quiet stock look like a
		# failed fetch: when it last TRADED, and when we last LOOKED
		h.stale_days = (frappe.utils.date_diff(nowdate(), h.price_as_of)
						if h.price_as_of else None)
		h.checked_days = (frappe.utils.date_diff(nowdate(), h.checked_on)
						  if h.get("checked_on") else None)
	return holdings


@frappe.whitelist()
def portfolio():
	"""Everything the shares tab and the summary card need, in one call."""
	require_sysadmin()
	pos = _positions()
	rows = sorted(
		pos.values(),
		key=lambda h: (-(h.open or 0), -(h.value or 0), (h.symbol or "").upper()),
	)

	# what share of the portfolio each holding is — computed against open
	# positions in the SAME currency, since a percentage of a blended total
	# would need a rate and would mean nothing without one
	tot_by_ccy = {}
	for h in rows:
		if h.open:
			tot_by_ccy[h.currency] = tot_by_ccy.get(h.currency, 0.0) + h.value
	# Target weights are percentages meant to total 100. They are still divided
	# by their own sum when planning, so a set that totals 97 or 104 still
	# produces a sensible plan rather than an error — but the total is reported
	# so it can be corrected. That warning is the whole reason to use
	# percentages rather than bare proportions: with proportions every set is
	# valid and nothing can ever be wrong.
	wsum = {}
	for h in rows:
		if flt(h.target_weight) > 0:
			wsum[h.currency] = wsum.get(h.currency, 0.0) + flt(h.target_weight)
	for h in rows:
		t = tot_by_ccy.get(h.currency, 0.0)
		h.weight_pct = round(h.value * 100 / t, 1) if (h.open and t > 0) else None
		ws = wsum.get(h.currency, 0.0)
		h.target_pct = (round(flt(h.target_weight) * 100 / ws, 1)
						if (flt(h.target_weight) > 0 and ws > 0) else None)
		h.drift = (round((h.weight_pct or 0) - h.target_pct, 1)
				   if h.target_pct is not None else None)

	by_ccy = {}
	for h in rows:
		c = by_ccy.setdefault(h.currency, {
			"currency": h.currency, "value": 0.0, "cost": 0.0,
			"unrealised": 0.0, "realised": 0.0, "holdings": 0,
		})
		c["value"] += h.value
		c["cost"] += h.cost
		c["unrealised"] += h.unrealised
		c["realised"] += h.realised
		c["dividends"] = c.get("dividends", 0.0) + h.div_net
		c["dividends_12m"] = c.get("dividends_12m", 0.0) + h.div_12m
		if h.open:
			c["holdings"] += 1
	for c in by_ccy.values():
		# the headline percentage: what the open position is up or down, against
		# what it cost. Realised gain is reported beside it rather than folded in,
		# because money already banked is a different fact from paper movement.
		c["gain_pct"] = round(c["unrealised"] * 100 / c["cost"], 2) if c["cost"] > 0 else None

	# what the weights actually add up to, per currency, so the tab can say
	weights_total = {c: round(v, 2) for c, v in wsum.items()}

	# EVERY broker on record, not only those already holding something. Built
	# from the master and then filled in from the positions — the earlier version
	# derived the list from holdings alone, so a broker you had just opened an
	# account with never appeared in the buy dialog, which is precisely when you
	# need it.
	by_broker = {}
	for b in frappe.get_all("Duty Broker", filters={"active": 1},
							fields=["name", "account_ref"],
							order_by="broker_name asc", limit_page_length=0):
		by_broker[b.name] = {"broker": b.name, "account_ref": b.account_ref,
							 "value": 0.0, "cost": 0.0, "holdings": 0,
							 "currency": None}
	for h in rows:
		if not h.open:
			continue
		for b in (h.broker_list or []):
			e = by_broker.setdefault(b["broker"], {"broker": b["broker"], "value": 0.0,
												   "cost": 0.0, "holdings": 0,
												   "currency": None})
			e["value"] += b["value"]
			e["cost"] += b["cost"]
			e["holdings"] += 1
			e["currency"] = e["currency"] or h.currency
	broker_rows = sorted(by_broker.values(), key=lambda x: (-x["value"], x["broker"]))

	return {
		"brokers": broker_rows,
		"weights_total": weights_total,
		"holdings": rows,
		"by_currency": sorted(by_ccy.values(), key=lambda c: -c["value"]),
		"basis": "weighted average",
	}


@frappe.whitelist()
def trades(holding=None, limit=200):
	"""Trade history, newest first, with the running position after each."""
	require_sysadmin()
	filters = {"holding": holding} if holding else {}
	rows = frappe.get_all(
		"Duty Trade", filters=filters,
		fields=["name", "holding", "kind", "trade_date", "quantity", "price",
				"charges", "account", "note"],
		order_by="trade_date desc, creation desc",
		limit_page_length=frappe.utils.cint(limit) or 200,
	)
	sym = {h.name: h.symbol for h in frappe.get_all("Duty Holding", fields=["name", "symbol"])}
	for r in rows:
		r.symbol = sym.get(r.holding, r.holding)
		r.gross = flt(r.quantity) * flt(r.price)
		r.net = r.gross + flt(r.charges) if r.kind == "Buy" else r.gross - flt(r.charges)
	return rows


@frappe.whitelist()
def save_holding(name=None, **kwargs):
	require_sysadmin()
	allowed = ("symbol", "holding_name", "currency", "exchange", "last_price",
			   "price_as_of", "active", "note", "financial_year_end", "target_weight")
	doc = frappe.get_doc("Duty Holding", name) if name else frappe.new_doc("Duty Holding")
	for k in allowed:
		if k in kwargs and kwargs[k] is not None:
			doc.set(k, kwargs[k])
	if not doc.symbol or not doc.currency:
		frappe.throw(_("A holding needs a ticker and a currency."))
	if kwargs.get("last_price") and not doc.price_as_of:
		doc.price_as_of = nowdate()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "name": doc.name}


def _ensure_category(name, kind):
	"""Categories are records now, so one referenced here must exist."""
	if not frappe.db.exists("Duty Money Category", name):
		frappe.get_doc({"doctype": "Duty Money Category", "category_name": name,
						"kind": kind}).insert(ignore_permissions=True)
	return name


@frappe.whitelist()
def record_trade(holding, kind, quantity, price, charges=0, trade_date=None,
				 account=None, note=None, move_cash=1, broker=None):
	"""Buy or sell. A sell beyond what is held is refused rather than clamped.

	Clamping would silently record something that did not happen; refusing says
	the position and the trade disagree, which is a real thing to know.
	"""
	require_sysadmin()
	if kind not in ("Buy", "Sell"):
		frappe.throw(_("A trade is a Buy or a Sell."))
	if flt(quantity) <= 0 or flt(price) < 0:
		frappe.throw(_("Quantity must be above zero and price cannot be negative."))
	if kind == "Sell":
		pos = _positions().get(holding) or frappe._dict()
		held = flt(pos.qty)
		if flt(quantity) > held + 0.0000001:
			frappe.throw(_("You hold {0}, so {1} cannot be sold.").format(held, flt(quantity)))
		# and not more than that broker is actually holding, or the parcels go
		# negative while the total still looks right
		if broker:
			at = next((b["qty"] for b in (pos.broker_list or [])
					   if b["broker"] == broker), 0.0)
			if flt(quantity) > flt(at) + 0.0000001:
				frappe.throw(_("{0} holds {1} of these, so {2} cannot be sold from there.").format(
					broker, flt(at), flt(quantity)))
	doc = frappe.get_doc({
		"doctype": "Duty Trade",
		"holding": holding, "kind": kind, "broker": broker or None,
		"trade_date": trade_date or nowdate(),
		"quantity": flt(quantity), "price": flt(price), "charges": flt(charges),
		"account": account or None, "note": note or None,
	})
	doc.insert(ignore_permissions=True)

	# Move the cash. This used to be left to you, on the reasoning that a
	# statement import might also record it and double-count — but movements
	# here are typed by hand, so that could only happen by typing it twice.
	# The cost of the caution was a bank balance silently wrong until you
	# remembered, which is worse than a duplicate you can see and delete.
	cash = None
	if account and cint(move_cash):
		acc_ccy = frappe.db.get_value("Duty Bank Account", account, "currency")
		hold_ccy = frappe.db.get_value("Duty Holding", holding, "currency")
		if acc_ccy != hold_ccy:
			# a conversion happened and no rate here would be the one you got
			cash = {"skipped": _("Account is in {0} and the holding in {1}, so the cash was not moved — record it on the account with the amount that actually left.").format(acc_ccy, hold_ccy)}
		else:
			gross = flt(quantity) * flt(price)
			amount = gross + flt(charges) if kind == "Buy" else gross - flt(charges)
			sym = frappe.db.get_value("Duty Holding", holding, "symbol")
			mv = frappe.get_doc({
				"doctype": "Duty Money Move",
				"move_date": doc.trade_date,
				"kind": "Out" if kind == "Buy" else "In",
				"account": account,
				"amount": abs(amount),
				"category": _ensure_category(_("Shares"), "Not spending"),
				"counterparty": sym,
				"note": _("{0} {1} {2} @ {3}").format(kind, flt(quantity), sym, flt(price)),
			})
			mv.insert(ignore_permissions=True)
			# linked so deleting the trade takes the movement with it rather
			# than leaving an orphan nobody can explain later
			doc.db_set("cash_move", mv.name, update_modified=False)
			cash = {"name": mv.name, "amount": abs(amount),
					"kind": "Out" if kind == "Buy" else "In"}
	frappe.db.commit()
	return {"ok": 1, "name": doc.name, "cash": cash}


@frappe.whitelist()
def set_price(holding, last_price, price_as_of=None):
	"""Mark a holding to market. Manual, and dated so staleness is visible."""
	require_sysadmin()
	on = price_as_of or nowdate()
	frappe.db.set_value("Duty Holding", holding, {
		"last_price": flt(last_price), "price_as_of": on,
	})
	# a hand-entered price joins the history too, or the chart would show gaps
	# exactly where you cared enough to type one in
	_store_point(holding, on, flt(last_price), "manual")
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def delete_trade(name):
	require_sysadmin()
	mv = frappe.db.get_value("Duty Trade", name, "cash_move")
	if mv and frappe.db.exists("Duty Money Move", mv):
		frappe.delete_doc("Duty Money Move", mv, ignore_permissions=True)
	frappe.delete_doc("Duty Trade", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


def portfolio_summary():
	"""Compact figures for the card beside the currency totals on Money."""
	pos = _positions()
	out = {}
	for h in pos.values():
		c = out.setdefault(h.currency, {"currency": h.currency, "value": 0.0,
										"cost": 0.0, "unrealised": 0.0,
										"realised": 0.0, "holdings": 0})
		c["value"] += h.value
		c["cost"] += h.cost
		c["unrealised"] += h.unrealised
		c["realised"] += h.realised
		c["dividends"] = c.get("dividends", 0.0) + h.div_net
		c["dividends_12m"] = c.get("dividends_12m", 0.0) + h.div_12m
		if h.open:
			c["holdings"] += 1
	for c in out.values():
		c["gain_pct"] = round(c["unrealised"] * 100 / c["cost"], 2) if c["cost"] > 0 else None
	return [c for c in out.values() if c["holdings"] or c["value"] or c["realised"]]


# ─────────────────────── price fetching and price history ────────────────────
#
# NGX quotes are scraped from AFX, which publishes a page per ticker. There is
# no free NGX API: the exchange's own Market Data API is built for
# redistributors and priced accordingly, and everything else covering NGX is a
# paid aggregator. For a personal portfolio of a dozen holdings, one page per
# ticker once a day is the right trade.
#
# THE FAILURE BEHAVIOUR MATTERS MORE THAN THE FETCH. A scraper breaks when the
# page is redesigned — not if, when. So nothing here ever overwrites a good
# price with a guess, a failed fetch leaves the previous price and its previous
# DATE untouched, and the tab shows how old each price is. A stale number that
# looks stale is safe; a stale number that looks live is how somebody sells the
# wrong thing.
#
# The page carries the price and the trading day it belongs to in one sentence,
# which is why this source was chosen over a table: the date is what makes
# staleness visible rather than assumed.

# Sources are tried in order until one answers. That is not over-engineering:
# AFX turned out to be unreachable from this server — outbound HTTPS works, and
# example.com and google answer, but that host drops traffic from the hosting
# range. Any single source can do this, and a portfolio that stops pricing
# because one site changed its mind about datacentre IPs is a bad design.
#
# stockanalysis.com leads because it is server-rendered, carries the price, the
# move and the closing date together, and marks the data as delayed rather than
# implying it is live. AFX stays as the fallback for the day the first one
# changes shape.
#
# NGX's own price list is deliberately NOT here: it requires JavaScript, so
# plain requests receives a redirect notice rather than a price.

SA_URL = "https://stockanalysis.com/quote/ngx/{ticker}/"
_HEADERS = {
	"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
				   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
	"Accept": "text/html,application/xhtml+xml",
	"Accept-Language": "en-GB,en;q=0.9",
}
AFX_URL = "https://afx.kwayisi.org/ngx/{ticker}.html"

# The change block is OPTIONAL. A stock that has not traded shows no move at
# all — SEPLAT is one — and requiring '+0.85 (3.26%)' meant the price could not
# be read for exactly the quiet stocks whose price is least likely to be known
# from memory. Decimals are optional too, since a round price is still a price.
SA_RE = re.compile(
	r"([\d,]+(?:\.\d+)?)\s*"
	# either a full move, or a bare dash where a move would be
	r"(?:(?:[+\-\u2212][\d,.]+\s*\([^)]*\)|[-\u2013\u2212])\s*)?"
	r"At\s+close:\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})", re.I)
SA_PRICE_ONLY = re.compile(r"Currency is NGN\s*.{0,200}?([\d,]+(?:\.\d+)?)", re.S)
PRICE_RE = re.compile(r"share price of[^)]*\(([A-Z0-9\.\-]+)\)\s*is\s*NGN\s*([\d,]+(?:\.\d+)?)", re.I)
PRICE_RE2 = re.compile(r"is\s*NGN\s*([\d,]+(?:\.\d+)?)", re.I)
DATE_RE = re.compile(r"closed its last trading day\s*\(([^)]+)\)", re.I)
CLOSE_RE = re.compile(r"at\s*([\d,]+(?:\.\d+)?)\s*NGN per share", re.I)


def _flatten(html):
	t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.S | re.I)
	t = re.sub(r"<[^>]+>", " ", t)
	return re.sub(r"\s+", " ", t)


def _money(v):
	try:
		n = flt(str(v).replace(",", ""))
	except Exception:
		return None
	return n if n > 0 else None


def _parse_sa(html):
	"""stockanalysis.com — '26.95 +0.85 (3.26%) At close: Aug 7, 2026'."""
	text = _flatten(html)
	m = SA_RE.search(text)
	if m:
		price = _money(m.group(1))
		if not price:
			return None
		on = None
		for fmt in ("%b %d, %Y", "%B %d, %Y"):
			try:
				from datetime import datetime

				on = datetime.strptime(m.group(2).strip(), fmt).strftime("%Y-%m-%d")
				break
			except Exception:
				continue
		return {"price": price, "as_of": on}
	m2 = SA_PRICE_ONLY.search(text)
	if m2:
		price = _money(m2.group(1))
		if price:
			return {"price": price, "as_of": None}
	return None


def _parse_afx(html):
	"""AFX — the price and its trading day in one sentence.

	Returns None rather than a guess: an unparseable page must look like a
	failed fetch, not like a price.
	"""
	text = _flatten(html)
	price = None
	m = PRICE_RE.search(text)
	if m:
		price = m.group(2)
	else:
		m2 = CLOSE_RE.search(text) or PRICE_RE2.search(text)
		if m2:
			price = m2.group(1)
	price = _money(price) if price else None
	if not price:
		return None
	on = None
	d = DATE_RE.search(text)
	if d:
		try:
			from datetime import datetime

			raw = d.group(1).split(",", 1)[-1].strip()
			on = datetime.strptime(raw, "%B %d, %Y").strftime("%Y-%m-%d")
		except Exception:
			on = None
	return {"price": price, "as_of": on}


SOURCES = (
	("stockanalysis", SA_URL, lambda t: t.strip().upper(), _parse_sa),
	("afx", AFX_URL, lambda t: t.strip().lower(), _parse_afx),
)


class _NoPage(Exception):
	"""Could not reach it. Distinct from reaching it and not understanding it —
	one is the network, the other is the parser, and a report that conflates
	them sends you looking in the wrong place."""


def _ipv4_only():
	"""Force IPv4 for one fetch, then restore.

	One source published AAAA records while this server has no IPv6 route, so
	Python picked IPv6 and got 'Network is unreachable' before a byte left the
	box. Restored afterwards so nothing else on the bench inherits it.
	"""
	import socket

	import urllib3.util.connection as u3

	prev = u3.allowed_gai_family
	u3.allowed_gai_family = lambda: socket.AF_INET
	return u3, prev


def _fetch_one(symbol):
	"""Try each source in turn. Returns the result and which source gave it."""
	import requests

	headers = _HEADERS
	problems = []
	u3, prev = _ipv4_only()
	try:
		for name, tpl, shape, parse in SOURCES:
			url = tpl.format(ticker=shape(symbol or ""))
			try:
				r = requests.get(url, timeout=15, headers=headers)
			except Exception as e:
				problems.append("%s: unreachable (%s)" % (name, str(e)[:60]))
				continue
			if r.status_code != 200:
				problems.append("%s: HTTP %s" % (name, r.status_code))
				continue
			got = parse(r.text)
			if got:
				got["source"] = name
				return got
			problems.append("%s: reached, no price found" % name)
	finally:
		u3.allowed_gai_family = prev
	raise _NoPage("; ".join(problems) or "no source answered")


@frappe.whitelist()
def fetch_prices(only=None):
	"""Fetch every active holding's price. Safe to run by hand or on a schedule.

	Reports per ticker rather than silently succeeding, because a fetcher whose
	failures are invisible is worse than no fetcher.
	"""
	require_sysadmin()
	names = [only] if only else None
	filters = {"active": 1}
	if names:
		filters["name"] = ["in", names]
	rows = frappe.get_all("Duty Holding", filters=filters,
						  fields=["name", "symbol"], limit_page_length=0)
	got, failed, why = [], [], {}
	for h in rows:
		try:
			res = _fetch_one(h.symbol)
		except _NoPage as e:
			failed.append(h.symbol)
			why[h.symbol] = _("could not reach the page") + " — " + str(e)
			continue
		except Exception as e:
			failed.append(h.symbol)
			why[h.symbol] = str(e)[:160]
			continue
		if not res:
			failed.append(h.symbol)
			# reached it and did not understand it: the page has changed shape,
			# which is a different problem from being offline
			why[h.symbol] = _("page reached but no price found in it")
			continue
		on = res.get("as_of") or nowdate()
		src = res.get("source") or "fetch"
		_store_point(h.name, on, res["price"], src)
		# last_price is only advanced, never rolled back to an older quote
		cur_on = frappe.db.get_value("Duty Holding", h.name, "price_as_of")
		if not cur_on or str(on) >= str(cur_on):
			frappe.db.set_value("Duty Holding", h.name,
								{"last_price": res["price"], "price_as_of": on})
		frappe.db.set_value("Duty Holding", h.name, "checked_on", nowdate(),
							update_modified=False)
		got.append("%s %s (%s, %s)" % (h.symbol, res["price"], on, src))
	frappe.db.commit()
	# An end-of-day source returns the last COMPLETED session. Fetching during a
	# session therefore returns yesterday, correctly, and that surprised us both
	# — so the result says so rather than leaving it to be inferred from dates.
	newest = max([g.split("(")[-1][:10] for g in got], default=None)
	out = {"fetched": len(got), "failed": failed, "why": why, "detail": got,
		   "ran_at": frappe.utils.now(), "newest_close": newest,
		   "note": (_("Prices are for the {0} close — the last session that had finished when this ran.").format(newest)
					if newest and newest < nowdate() else None)}
	frappe.cache().set_value("duty_price_fetch", out)
	return out


def _store_point(holding, on, price, source):
	"""One point per holding per day — a second write updates rather than adds."""
	name = "%s::%s" % (holding, on)
	if frappe.db.exists("Duty Price Point", name):
		frappe.db.set_value("Duty Price Point", name,
							{"price": flt(price), "source": source})
		return
	frappe.get_doc({
		"doctype": "Duty Price Point", "holding": holding,
		"price_date": on, "price": flt(price), "source": source,
	}).insert(ignore_permissions=True)


def scheduled_fetch_prices():
	"""Weekdays after the NGX close. Quiet unless something failed.

	cron: 30 16 * * 1-5  (server time)
	"""
	try:
		res = fetch_prices()
	except Exception:
		frappe.log_error(frappe.get_traceback()[-2000:], "ngx price fetch")
		return
	# fundamentals move slowly, so once a week is plenty and it is the same page
	if frappe.utils.getdate().weekday() == 4:
		try:
			fetch_fundamentals()
		except Exception:
			frappe.log_error(frappe.get_traceback()[-1200:], "ngx fundamentals")
	if not res.get("failed"):
		return
	# only the failures are worth an email; a working fetcher should be silent
	from duty_board.notify import _send, _shell

	admins = [a for a in set(frappe.get_all(
		"Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent"))
		if a not in ("Administrator", "Guest") and frappe.db.get_value("User", a, "enabled")]
	why = res.get("why") or {}
	rows_html = "".join(
		"<li><b>%s</b> — %s</li>" % (frappe.utils.escape_html(t),
									 frappe.utils.escape_html(why.get(t, "")))
		for t in res["failed"])
	body = (
		"<p style='font-size:13.5px'>%s</p><ul style='font-size:12.5px'>%s</ul>"
		"<p style='font-size:12px;color:#8A9994'>%s</p>"
		% (_("These tickers did not price today. Their last known prices are unchanged and are now a day staler."),
		   rows_html,
		   _("'Could not reach the page' is a network problem. 'No price found' means the source changed shape and the parser needs updating. Prices can still be entered by hand.")))
	for u in admins:
		_send(u, "[Money] %d ticker(s) did not price" % len(res["failed"]),
			  _shell(_("Price fetch"), body))


@frappe.whitelist()
def price_series(holding=None, days=180):
	"""Closes for the chart. One holding, or every one being tracked."""
	require_sysadmin()
	since = frappe.utils.add_days(nowdate(), -abs(frappe.utils.cint(days) or 180))
	filters = {"price_date": [">=", since]}
	if holding:
		filters["holding"] = holding
	rows = frappe.get_all(
		"Duty Price Point", filters=filters,
		fields=["holding", "price_date", "price"],
		order_by="price_date asc", limit_page_length=0,
	)
	out = {}
	for r in rows:
		out.setdefault(r.holding, []).append(
			{"d": str(r.price_date), "p": flt(r.price)})
	return {"series": out, "since": since,
			"last_fetch": frappe.cache().get_value("duty_price_fetch") or None}


# ───────────────── fundamentals and historical backfill ──────────────────────
#
# Both come off pages already being fetched for the price, so this adds no new
# source and no new thing to break independently.
#
# FINANCIAL YEAR END IS NOT FETCHED, and that is not an oversight. No free
# source publishes it as a field — not stockanalysis, not AFX, not NGX's public
# pages. It could be inferred from the period ends on a financials page, but an
# inferred year end presented as a fact is exactly the kind of number that gets
# believed and is occasionally wrong. So it is a field you type, and the nearest
# published thing — the next earnings date — is fetched beside it.

STATS = {
	"pe_ratio": r"PE Ratio\s*\|?\s*([\d.,]+)",
	"forward_pe": r"Forward PE\s*\|?\s*([\d.,]+)",
	"eps": r"\bEPS\s*\|?\s*([\-\d.,]+)",
}
MCAP_RE = re.compile(r"Market Cap\s*\|?\s*([\d.,]+\s*[TBMK]?)", re.I)
W52_RE = re.compile(r"52-Week Range\s*\|?\s*([\d.,]+)\s*-\s*([\d.,]+)", re.I)
EARN_RE = re.compile(r"Earnings Date\s*\|?\s*([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})", re.I)
# cells may be separated by whitespace or by the pipes a stripped HTML table
# leaves behind, so the separator is explicit rather than assumed to be spaces
_SEP = r"\s*\|?\s*"
HIST_ROW = re.compile(
	r"([A-Z][a-z]{2}\s+\d{1,2},\s*\d{4})" + _SEP +
	r"([\d,]+\.\d+)" + _SEP + r"([\d,]+\.\d+)" + _SEP +
	r"([\d,]+\.\d+)" + _SEP + r"([\d,]+\.\d+)" + _SEP + r"([\d,]+\.\d+)")


def _as_date(raw):
	from datetime import datetime

	for fmt in ("%b %d, %Y", "%B %d, %Y"):
		try:
			return datetime.strptime((raw or "").strip(), fmt).strftime("%Y-%m-%d")
		except Exception:
			continue
	return None


def _parse_stats(html):
	"""The fundamentals table on the overview page. Absent keys stay absent."""
	t = _flatten(html)
	out = {}
	for field, pat in STATS.items():
		m = re.search(pat, t, re.I)
		if m:
			v = _money(m.group(1))
			if v is not None:
				out[field] = v
	m = MCAP_RE.search(t)
	if m:
		out["market_cap"] = re.sub(r"\s+", "", m.group(1))
	m = W52_RE.search(t)
	if m:
		lo, hi = _money(m.group(1)), _money(m.group(2))
		if lo and hi:
			out["week52_low"], out["week52_high"] = lo, hi
	m = EARN_RE.search(t)
	if m:
		on = _as_date(m.group(1))
		if on:
			out["next_earnings"] = on
	return out


@frappe.whitelist()
def fetch_fundamentals(only=None):
	"""P/E and friends, off the same overview page the price comes from."""
	require_sysadmin()
	filters = {"active": 1}
	if only:
		filters["name"] = ["in", [only]]
	rows = frappe.get_all("Duty Holding", filters=filters,
						  fields=["name", "symbol"], limit_page_length=0)
	done, failed = [], []
	u3, prev = _ipv4_only()
	try:
		import requests

		for h in rows:
			try:
				r = requests.get(SA_URL.format(ticker=h.symbol.strip().upper()),
								 timeout=15, headers=_HEADERS)
				stats = _parse_stats(r.text) if r.status_code == 200 else None
			except Exception:
				stats = None
			if not stats:
				failed.append(h.symbol)
				continue
			stats["fundamentals_as_of"] = nowdate()
			frappe.db.set_value("Duty Holding", h.name, stats)
			done.append(h.symbol)
	finally:
		u3.allowed_gai_family = prev
	frappe.db.commit()
	return {"updated": len(done), "failed": failed}


@frappe.whitelist()
def backfill_history(holding=None):
	"""Load the published daily closes so a chart is useful today, not in a month.

	About fifty trading days per holding — one page of the history table. It is
	deliberately not paginated: fifty days draws a real line, and walking three
	pages per ticker turns a polite scrape into a noisy one.

	Existing points are updated rather than duplicated, so this is safe to run
	more than once.
	"""
	require_sysadmin()
	filters = {"active": 1}
	if holding:
		filters["name"] = ["in", [holding]]
	rows = frappe.get_all("Duty Holding", filters=filters,
						  fields=["name", "symbol"], limit_page_length=0)
	added, failed = {}, []
	u3, prev = _ipv4_only()
	try:
		import requests

		for h in rows:
			url = SA_URL.format(ticker=h.symbol.strip().upper()) + "history/"
			try:
				r = requests.get(url, timeout=20, headers=_HEADERS)
			except Exception:
				failed.append(h.symbol)
				continue
			if r.status_code != 200:
				failed.append(h.symbol)
				continue
			n = 0
			for m in HIST_ROW.finditer(_flatten(r.text)):
				on = _as_date(m.group(1))
				close = _money(m.group(5))
				if not on or not close:
					continue
				_store_point(h.name, on, close, "history")
				n += 1
			if n:
				added[h.symbol] = n
			else:
				failed.append(h.symbol)
	finally:
		u3.allowed_gai_family = prev
	frappe.db.commit()
	return {"loaded": added, "failed": failed,
			"total": sum(added.values())}


# ──────────────────────────── the market tape ────────────────────────────────
#
# The whole NGX in one request. stockanalysis publishes every listed stock on a
# single page with symbol, price and the day's move, which is the only polite
# way to do a market tape — 142 tickers fetched individually would be 142
# requests an hour and would get the server blocked, deservedly.
#
# NGX's own site was the obvious source and cannot be used: it requires
# JavaScript, so plain requests receives a redirect notice rather than a price.
# Checked before writing a parser against it.
#
# CADENCE. The source says it updates daily, so hourly would be eight requests
# for the same numbers. It runs twice on weekdays — once mid-session and once
# after the close — and the tape carries the time it was taken, so nothing has
# to be assumed about how fresh it is.

LIST_URL = "https://stockanalysis.com/list/nigerian-stock-exchange/"
# Parsed from the table cells rather than from a flattened line, because a
# stripped HTML table and the markdown rendering of the same page look nothing
# alike — one has spaces between cells and the other has pipes. The first
# version matched pipes, which is what a fetched-as-markdown copy looks like and
# NOT what requests actually receives, so it reached the page and parsed zero
# rows. Cells are now taken from <td> elements, which is what is really there.
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
TD_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
SYM_RE = re.compile(r"/quote/ngx/([A-Z0-9\.\-]{1,14})/", re.I)


def _cell(html):
	return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def _parse_tape(html):
	"""Every row of the market list.

	Finds the price and change columns by shape rather than by position, so an
	added or reordered column does not silently shift the numbers — which is
	the failure that would go unnoticed, because a wrong price still looks like
	a price.
	"""
	out, seen = [], set()
	for tr in TR_RE.finditer(html or ""):
		block = tr.group(1)
		sym = None
		m = SYM_RE.search(block)
		if m:
			sym = m.group(1).upper()
		cells = [_cell(c) for c in TD_RE.findall(block)]
		if not cells:
			continue
		if not sym:
			cand = [c for c in cells[:3] if re.fullmatch(r"[A-Z0-9]{2,14}", c or "")]
			sym = cand[0] if cand else None
		if not sym or sym in seen:
			continue

		# the change column is the one that looks like a percentage; the price is
		# the last plain number before it
		pct, pct_at = None, None
		for i, c in enumerate(cells):
			if re.fullmatch(r"-?\d+(\.\d+)?%", c or ""):
				try:
					pct, pct_at = flt(c.replace("%", "")), i
				except Exception:
					pass
				break
			if c == "-" and i >= 3:
				pct_at = i
				break
		price = None
		hunt = range(pct_at - 1, 0, -1) if pct_at else range(len(cells) - 1, 0, -1)
		for i in hunt:
			c = (cells[i] or "").replace(",", "")
			if re.fullmatch(r"\d+(\.\d+)?", c):
				price = _money(c)
				if price:
					break
		if not price:
			continue
		name = ""
		for c in cells[1:4]:
			if c and not re.fullmatch(r"[A-Z0-9]{2,14}", c) and not re.match(r"^[\d.,]+[TBMK]?$", c):
				name = c[:48]
				break
		seen.add(sym)
		out.append({"s": sym, "n": name, "p": price, "c": pct})
	return out


@frappe.whitelist()
def fetch_tape():
	"""Pull the whole market and store it. One request."""
	require_sysadmin()
	import requests

	u3, prev = _ipv4_only()
	try:
		r = requests.get(LIST_URL, timeout=25, headers=_HEADERS)
	except Exception as e:
		return {"ok": 0, "error": str(e)[:180]}
	finally:
		u3.allowed_gai_family = prev
	if r.status_code != 200:
		return {"ok": 0, "error": "HTTP %s" % r.status_code}

	rows = _parse_tape(r.text)
	if not rows:
		# reached and not understood — the page changed shape. Keep whatever is
		# already stored rather than replacing a good tape with an empty one.
		return {"ok": 0, "error": _("Page reached but no rows parsed — the source has changed shape.")}

	doc = frappe.get_single("Duty Market Tape")
	doc.payload = json.dumps(rows)
	doc.stocks = len(rows)
	doc.gainers = len([x for x in rows if (x["c"] or 0) > 0])
	doc.losers = len([x for x in rows if (x["c"] or 0) < 0])
	doc.fetched_at = frappe.utils.now()
	doc.as_of = nowdate()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "stocks": doc.stocks, "gainers": doc.gainers, "losers": doc.losers}


@frappe.whitelist()
def market_tape():
	"""What the ticker strip renders. Empty is a valid answer, not an error."""
	require_sysadmin()
	doc = frappe.get_single("Duty Market Tape")
	if not doc.payload:
		return {"rows": [], "fetched_at": None}
	try:
		rows = json.loads(doc.payload)
	except Exception:
		return {"rows": [], "fetched_at": None}
	return {"rows": rows, "fetched_at": str(doc.fetched_at or ""),
			"stocks": doc.stocks, "gainers": doc.gainers, "losers": doc.losers}


def scheduled_fetch_tape():
	"""Weekdays, mid-session and after the close. cron: 0 13,17 * * 1-5"""
	try:
		fetch_tape()
	except Exception:
		frappe.log_error(frappe.get_traceback()[-1500:], "ngx tape")


@frappe.whitelist()
def delete_holding(name):
	"""Remove a holding. Refused if it has ever been traded.

	A holding with trades is history, not a watchlist entry — deleting it would
	silently remove realised gains from the totals. Those are marked inactive
	instead, which keeps the record and takes them off the screen.
	"""
	require_sysadmin()
	n = frappe.db.count("Duty Trade", {"holding": name})
	if n:
		frappe.throw(_("{0} has {1} trade(s) recorded. It can be hidden but not deleted, so the gains it produced stay in your totals.").format(name, n))
	frappe.db.delete("Duty Price Point", {"holding": name})
	frappe.delete_doc("Duty Holding", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def hide_holding(name, active=0):
	"""Take a traded holding off the screen without losing what it did."""
	require_sysadmin()
	frappe.db.set_value("Duty Holding", name, "active", cint(active))
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def allocate(amount, holdings, charges_pct=0, weights=None):
	"""Spread an amount across chosen stocks and say how many shares to buy.

	THREE DECISIONS, all arguable and all stated rather than assumed.

	WHOLE SHARES ONLY. Fractions are not a thing on the NGX, so every quantity
	is floored. That leaves a remainder, which is reported rather than hidden —
	an allocator that quietly spends 3% less than you gave it is worse than one
	that tells you.

	CHARGES COME OFF THE TOP. You enter the rate; nothing here assumes what
	your broker takes. Default is zero, which is wrong for everybody but wrong
	visibly rather than wrong quietly.

	EQUAL MONEY, NOT EQUAL SHARES, and not weighted by price or size. Equal
	money is the only split that needs no view about the companies. Weights are
	accepted if you have a view of your own.

	The remainder is then swept: cheapest share first, one more bought wherever
	it still fits, until nothing does. That turns a typical 2-4% idle remainder
	into well under one share's worth.
	"""
	require_sysadmin()
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter the amount you have to invest."))
	picks = _as_list_json(holdings)
	if not picks:
		frappe.throw(_("Choose at least one stock."))
	w = _as_dict_json(weights)

	rows = frappe.get_all(
		"Duty Holding", filters={"name": ["in", picks]},
		fields=["name", "symbol", "holding_name", "currency", "last_price", "price_as_of"],
		limit_page_length=0)
	rows = [r for r in rows if flt(r.last_price) > 0]
	if not rows:
		frappe.throw(_("None of the chosen stocks has a price yet. Fetch prices first."))

	ccy = {r.currency for r in rows}
	if len(ccy) > 1:
		frappe.throw(_("Those stocks are in different currencies, so one amount cannot be split across them."))

	fee = flt(charges_pct) / 100.0
	investable = amount / (1 + fee) if fee else amount

	total_w = sum(flt(w.get(r.name, 1)) or 1 for r in rows)
	plan = []
	for r in rows:
		share = (flt(w.get(r.name, 1)) or 1) / total_w
		budget = investable * share
		qty = int(budget // flt(r.last_price))
		plan.append({
			"holding": r.name, "symbol": r.symbol, "name": r.holding_name,
			"price": flt(r.last_price), "priced_on": str(r.price_as_of or ""),
			"target": budget, "qty": qty,
		})

	# sweep the remainder: cheapest first, one more share wherever it still fits
	spent = sum(p["qty"] * p["price"] for p in plan)
	left = investable - spent
	for p in sorted(plan, key=lambda x: x["price"]):
		while left >= p["price"]:
			p["qty"] += 1
			left -= p["price"]
			spent += p["price"]

	for p in plan:
		p["cost"] = p["qty"] * p["price"]
		p["pct"] = round(p["cost"] * 100 / spent, 1) if spent else 0
	plan.sort(key=lambda x: -x["cost"])

	charges = spent * fee
	return {
		"currency": rows[0].currency,
		"amount": amount, "investable": investable,
		"spent": spent, "charges": charges,
		"leftover": amount - spent - charges,
		"plan": plan, "charges_pct": flt(charges_pct),
	}


def _as_list_json(v):
	if isinstance(v, str):
		try:
			v = frappe.parse_json(v)
		except Exception:
			v = [x.strip() for x in v.split(",")]
	return [x for x in (v or []) if x]


def _as_dict_json(v):
	if not v:
		return {}
	if isinstance(v, str):
		try:
			v = frappe.parse_json(v)
		except Exception:
			return {}
	return v if isinstance(v, dict) else {}


@frappe.whitelist()
def diagnose_price(symbol):
	"""Show exactly what each source says for one ticker, live.

	Written because 'traded 2d ago' on ACCESSCORP, ZENITHBANK and GTCO cannot be
	explained by those stocks being quiet — they are among the most liquid on the
	exchange. Rather than reason about it from cached copies of the pages, this
	fetches them now and reports the raw text around the match, the date parsed
	from it, and what is currently stored.

	bench --site <site> execute duty_board.shares.diagnose_price --kwargs "{'symbol': 'ACCESSCORP'}"
	"""
	require_sysadmin()
	import requests

	out = {"symbol": symbol, "today": nowdate(), "sources": []}
	row = frappe.db.get_value("Duty Holding", {"symbol": symbol},
							  ["name", "last_price", "price_as_of", "checked_on"], as_dict=True)
	out["stored"] = row

	u3, prev = _ipv4_only()
	try:
		for name, tpl, shape, parse in SOURCES:
			url = tpl.format(ticker=shape(symbol))
			rec = {"source": name, "url": url}
			try:
				r = requests.get(url, timeout=20, headers=_HEADERS)
				rec["status"] = r.status_code
				if r.status_code == 200:
					flat = _flatten(r.text)
					got = parse(r.text)
					rec["parsed"] = got
					# the raw words around the close date, so a wrong match is
					# visible rather than inferred
					m = re.search(r".{90}At\s+close:.{40}", flat, re.I)
					rec["around_close"] = m.group(0).strip() if m else None
					m2 = re.search(r".{60}last trading day.{60}", flat, re.I)
					rec["around_last_trade"] = m2.group(0).strip() if m2 else None
			except Exception as e:
				rec["error"] = str(e)[:200]
			out["sources"].append(rec)
	finally:
		u3.allowed_gai_family = prev

	# the market list carries every ticker in one page — if IT is fresher than
	# the quote page, the fetcher should be reading it instead
	try:
		tape = frappe.get_single("Duty Market Tape")
		rows = json.loads(tape.payload or "[]")
		hit = next((x for x in rows if x.get("s") == symbol), None)
		out["tape"] = {"fetched_at": str(tape.fetched_at or ""), "row": hit}
	except Exception:
		out["tape"] = None

	print(json.dumps(out, indent=1, default=str))
	return out


@frappe.whitelist()
def allocate_to_weights(amount, charges_pct=0, currency=None):
	"""Apportion new money so the portfolio moves toward its target weights.

	NOTHING IS SOLD. That constraint is what makes this more than a division
	sum: a holding already above its target cannot be trimmed, so its value is
	frozen and the money it would have released has to be spread across the
	rest. Doing that once is not enough either — freezing one holding raises
	everyone else's share of what remains, which can push a second holding above
	its target. The loop repeats until nothing new is over.

	With enough money everybody lands exactly on target. With too little, the
	underweight holdings are brought to a common shortfall rather than the
	first few being filled completely — which is what "as close as possible"
	honestly means when you cannot sell.

	Weights are proportions, not percentages: 2/1/1 is the same as 50/25/25.
	"""
	require_sysadmin()
	amount = flt(amount)
	if amount <= 0:
		frappe.throw(_("Enter the amount you have to invest."))

	pos = _positions()
	rows = [h for h in pos.values()
			if cint(h.active) and flt(h.target_weight) > 0 and flt(h.last_price) > 0]
	if not rows:
		frappe.throw(_("Set a target weight on at least one holding first, and make sure it has a price."))

	ccys = {h.currency for h in rows}
	cur = currency or (list(ccys)[0] if len(ccys) == 1 else None)
	if not cur:
		frappe.throw(_("Those holdings are in different currencies. Choose one to plan for."))
	rows = [h for h in rows if h.currency == cur]

	fee = flt(charges_pct) / 100.0
	investable = amount / (1 + fee) if fee else amount

	value = {h.name: flt(h.value) for h in rows}
	weight = {h.name: flt(h.target_weight) for h in rows}
	total_after = sum(value.values()) + investable

	# water-filling: freeze whatever is already above target, redistribute, repeat
	frozen = set()
	ideal = {}
	for _pass in range(len(rows) + 1):
		pool = [n for n in value if n not in frozen]
		wpool = sum(weight[n] for n in pool)
		if wpool <= 0:
			break
		avail = total_after - sum(value[n] for n in frozen)
		ideal = {n: weight[n] / wpool * avail for n in pool}
		over = [n for n in pool if value[n] > ideal[n] + 0.005]
		if not over:
			break
		frozen |= set(over)

	by = {h.name: h for h in rows}
	plan, spent = [], 0.0
	for name, want in ideal.items():
		h = by[name]
		gap = max(0.0, want - value[name])
		qty = int(gap // flt(h.last_price))
		plan.append({"holding": name, "symbol": h.symbol, "name": h.holding_name,
					 "price": flt(h.last_price), "held": flt(h.qty),
					 "value_now": value[name], "target_value": want,
					 "gap": gap, "qty": qty, "cost": qty * flt(h.last_price),
					 "currency": cur, "watching": 1 if not h.trades else 0})
		spent += qty * flt(h.last_price)

	# whole shares leave a remainder; give it to whoever is furthest below target
	# rather than to whoever is cheapest — the objective is the weights
	left = investable - spent
	guard = 0
	while guard < 400:
		guard += 1
		short = sorted(
			[p for p in plan if p["price"] <= left],
			key=lambda p: ((p["value_now"] + p["cost"]) / p["target_value"]) if p["target_value"] else 9)
		if not short:
			break
		p = short[0]
		p["qty"] += 1
		p["cost"] += p["price"]
		spent += p["price"]
		left -= p["price"]

	after_total = sum(value.values()) + spent
	for p in plan:
		after = p["value_now"] + p["cost"]
		p["after_value"] = after
		p["after_pct"] = round(after * 100 / after_total, 1) if after_total else 0
		p["target_pct"] = round(p["target_value"] * 100 / total_after, 1) if total_after else 0
		p["frozen"] = 1 if p["holding"] in frozen else 0
	for name in frozen:
		h = by[name]
		after = value[name]
		plan.append({"holding": name, "symbol": h.symbol, "name": h.holding_name,
					 "price": flt(h.last_price), "held": flt(h.qty),
					 "value_now": value[name], "target_value": 0.0, "gap": 0.0,
					 "qty": 0, "cost": 0.0, "currency": cur,
					 "watching": 0, "frozen": 1, "after_value": after,
					 "after_pct": round(after * 100 / after_total, 1) if after_total else 0,
					 "target_pct": round(weight[name] * 100 / sum(weight.values()), 1)})
	plan.sort(key=lambda p: -p["cost"])

	return {
		"currency": cur, "amount": amount, "investable": investable,
		"spent": spent, "charges": spent * fee,
		"leftover": amount - spent - spent * fee,
		"plan": plan,
		"frozen": [by[n].symbol for n in frozen],
		"value_before": sum(value.values()), "value_after": after_total,
		"weights_total": round(sum(weight.values()), 2),
	}


@frappe.whitelist()
def weight_requirement(charges_pct=1.0, currency=None):
	"""What it would cost to reach the target weights, buying only.

	The inverse of allocate_to_weights, and it has a closed form. Since nothing
	is sold, every holding's value is a floor: for holding i to be w_i of the
	portfolio, the portfolio must total at least v_i / w_i. The largest of those
	ratios is binding, and the holding that produces it is the anchor — the one
	whose existing size dictates how large everything else must become.

	That is the number worth showing. A holding at 47% against a 20% target does
	not need trimming by 27 points; it needs the portfolio to more than triple,
	and no amount of staring at the percentage says so.

	Quantities are rounded UP, so no holding lands fractionally short of its
	target and the figure quoted is genuinely sufficient rather than nearly.
	"""
	require_sysadmin()
	pos = _positions()
	rows = [h for h in pos.values()
			if cint(h.active) and flt(h.target_weight) > 0 and flt(h.last_price) > 0]
	if not rows:
		frappe.throw(_("Set a target weight on at least one holding first, and make sure it has a price."))

	ccys = {h.currency for h in rows}
	cur = currency or (list(ccys)[0] if len(ccys) == 1 else None)
	if not cur:
		frappe.throw(_("Those holdings are in different currencies. Choose one to plan for."))
	rows = [h for h in rows if h.currency == cur]

	wtotal = sum(flt(h.target_weight) for h in rows)
	if wtotal <= 0:
		frappe.throw(_("Weights come to nothing."))

	# the portfolio total every holding's own floor demands, and which one binds
	need_total, anchor = 0.0, None
	for h in rows:
		share = flt(h.target_weight) / wtotal
		t = flt(h.value) / share if share else 0.0
		if t > need_total:
			need_total, anchor = t, h

	fee = flt(charges_pct) / 100.0
	held_now = sum(flt(h.value) for h in rows)
	plan, spend = [], 0.0
	for h in rows:
		share = flt(h.target_weight) / wtotal
		want = share * need_total
		gap = max(0.0, want - flt(h.value))
		import math

		qty = int(math.ceil(gap / flt(h.last_price) - 1e-9)) if gap > 0 else 0
		cost = qty * flt(h.last_price)
		spend += cost
		plan.append({
			"holding": h.name, "symbol": h.symbol, "name": h.holding_name,
			"price": flt(h.last_price), "held": flt(h.qty),
			"value_now": flt(h.value),
			"now_pct": round(flt(h.value) * 100 / held_now, 1) if held_now else 0,
			"target_pct": round(share * 100, 1),
			"target_value": want, "gap": gap, "qty": qty, "cost": cost,
			"is_anchor": 1 if (anchor and h.name == anchor.name) else 0,
			"watching": 1 if not h.trades else 0,
			"currency": cur,
		})
	after = held_now + spend
	for p in plan:
		p["after_pct"] = round((p["value_now"] + p["cost"]) * 100 / after, 2) if after else 0
	plan.sort(key=lambda p: -p["cost"])

	return {
		"currency": cur,
		"held_now": held_now,
		"need_total": need_total,
		"anchor": anchor.symbol if anchor else None,
		"anchor_pct": (round(flt(anchor.value) * 100 / held_now, 1)
					   if anchor and held_now else None),
		"anchor_target": (round(flt(anchor.target_weight) * 100 / wtotal, 1)
						  if anchor else None),
		"spend": spend,
		"charges": spend * fee,
		"cash_needed": spend + spend * fee,
		"charges_pct": flt(charges_pct),
		"weights_total": round(wtotal, 2),
		"value_after": after,
		"plan": plan,
	}


# ─────────────────────────────── brokers ─────────────────────────────────────


@frappe.whitelist()
def brokers():
	require_sysadmin()
	rows = frappe.get_all("Duty Broker", filters={"active": 1},
						  fields=["name", "broker_name", "account_ref", "note"],
						  order_by="broker_name asc", limit_page_length=0)
	held = {}
	for h in _positions().values():
		if not h.open:
			continue
		for b in (h.broker_list or []):
			e = held.setdefault(b["broker"], {"value": 0.0, "n": 0, "currency": h.currency})
			e["value"] += b["value"]
			e["n"] += 1
	for r in rows:
		e = held.get(r.name) or {}
		r.value = e.get("value", 0.0)
		r.holdings = e.get("n", 0)
		r.currency = e.get("currency")
	# a parcel with no broker recorded is a real state and should be visible
	loose = held.get(_("Unassigned"))
	return {"brokers": rows,
			"unassigned": {"value": loose["value"], "holdings": loose["n"]} if loose else None}


@frappe.whitelist()
def save_broker(name=None, broker_name=None, account_ref=None, active=1):
	require_sysadmin()
	if name and frappe.db.exists("Duty Broker", name):
		frappe.db.set_value("Duty Broker", name,
							{"account_ref": account_ref, "active": cint(active)})
	else:
		frappe.get_doc({"doctype": "Duty Broker", "broker_name": broker_name or name,
						"account_ref": account_ref, "active": cint(active)}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def backfill_broker(broker="ARM ONE", dry_run=1):
	"""Put every trade that has no broker onto one.

	Everything bought so far went through a single broker; the field simply did
	not exist. Rather than leave those parcels as 'Unassigned' for ever, they are
	assigned once and the split starts working from the next purchase.
	"""
	require_sysadmin()
	dry = cint(dry_run)
	if not frappe.db.exists("Duty Broker", broker):
		if not dry:
			frappe.get_doc({"doctype": "Duty Broker", "broker_name": broker}).insert(ignore_permissions=True)
	rows = frappe.get_all("Duty Trade", filters={"broker": ["in", [None, ""]]},
						  fields=["name", "holding", "kind", "quantity"], limit_page_length=0)
	if not dry:
		for r in rows:
			frappe.db.set_value("Duty Trade", r.name, "broker", broker, update_modified=False)
		frappe.db.commit()
	print("%s: %d trade(s) %s to %s"
		  % ("DRY RUN" if dry else "DONE", len(rows),
			 "would move" if dry else "moved", broker))
	if dry and rows:
		print('Re-run with --kwargs "{\'dry_run\': 0}" to apply.')
	return {"moved": len(rows), "broker": broker}


# ────────────────────────────── dividends ────────────────────────────────────


@frappe.whitelist()
def record_dividend(holding, gross, pay_date=None, tax=0, broker=None,
					account=None, note=None, move_cash=1):
	"""A dividend paid, and the cash it put in an account.

	Kept apart from price movement because they answer different questions. A
	stock flat on price with a good yield is not dead money, and a shares tab
	that counts only capital says it is — which on the NGX, where yields are
	high, is a materially wrong picture.
	"""
	require_sysadmin()
	g, t = flt(gross), flt(tax)
	if g <= 0:
		frappe.throw(_("A dividend has to be more than nothing."))
	if t > g:
		frappe.throw(_("Withholding tax cannot exceed the gross."))
	on = pay_date or nowdate()
	pos = _positions().get(holding) or frappe._dict()
	doc = frappe.get_doc({
		"doctype": "Duty Dividend", "holding": holding, "pay_date": on,
		"broker": broker or None, "gross": g, "tax": t, "net": g - t,
		"account": account or None, "qty_held": flt(pos.get("qty") or 0),
		"note": note or None,
	})
	doc.insert(ignore_permissions=True)

	cash = None
	if account and cint(move_cash):
		acc_ccy = frappe.db.get_value("Duty Bank Account", account, "currency")
		hold_ccy = frappe.db.get_value("Duty Holding", holding, "currency")
		if acc_ccy != hold_ccy:
			cash = {"skipped": _("That account is in {0} and the holding in {1}, so the cash was not posted — record it on the account with the amount that actually arrived.").format(acc_ccy, hold_ccy)}
		else:
			sym = frappe.db.get_value("Duty Holding", holding, "symbol")
			mv = frappe.get_doc({
				"doctype": "Duty Money Move", "move_date": on, "kind": "In",
				"account": account, "amount": g - t,
				"category": _ensure_category(_("Dividends"), "Not spending"),
				"counterparty": sym,
				"note": _("Dividend — {0}").format(sym),
			})
			mv.insert(ignore_permissions=True)
			doc.db_set("money_move", mv.name, update_modified=False)
			cash = {"name": mv.name, "amount": g - t}
	frappe.db.commit()
	return {"ok": 1, "name": doc.name, "cash": cash}


@frappe.whitelist()
def delete_dividend(name):
	require_sysadmin()
	mv = frappe.db.get_value("Duty Dividend", name, "money_move")
	if mv and frappe.db.exists("Duty Money Move", mv):
		frappe.delete_doc("Duty Money Move", mv, ignore_permissions=True)
	frappe.delete_doc("Duty Dividend", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


def _dividend_map():
	"""Net and gross received per holding, all time and last twelve months."""
	since = frappe.utils.add_months(nowdate(), -12)
	out = {}
	for r in frappe.get_all("Duty Dividend",
							fields=["holding", "gross", "tax", "net", "pay_date"],
							limit_page_length=0):
		e = out.setdefault(r.holding, {"gross": 0.0, "tax": 0.0, "net": 0.0,
									   "net_12m": 0.0, "n": 0})
		e["gross"] += flt(r.gross)
		e["tax"] += flt(r.tax)
		e["net"] += flt(r.net)
		e["n"] += 1
		if str(r.pay_date) >= str(since):
			e["net_12m"] += flt(r.net)
	return out


@frappe.whitelist()
def broker_breakdown():
	"""Every parcel: which stock, at which broker, and what it is worth.

	The strip above the holdings gives a total per broker and the row gives a
	total per stock; neither answers "how many DANGCEM are at ARM ONE", which is
	the question a broker statement asks. This is that grid, readable either way
	round — by broker for reconciliation, by stock for concentration.
	"""
	require_sysadmin()
	pos = _positions()
	cells, brokers, syms = [], {}, {}
	for h in pos.values():
		if not h.open:
			continue
		for b in (h.broker_list or []):
			avg = (b["cost"] / b["qty"]) if b["qty"] else 0.0
			cell = {
				"broker": b["broker"], "holding": h.name, "symbol": h.symbol,
				"name": h.holding_name, "currency": h.currency,
				"qty": b["qty"], "cost": b["cost"], "avg_cost": avg,
				"price": flt(h.last_price), "value": b["value"],
				# a parcel's own gain, against what that parcel cost — it can
				# differ from the holding's because the two were bought at
				# different times through different brokers
				"unrealised": b["value"] - b["cost"] if h.last_price else 0.0,
			}
			cell["gain_pct"] = (round(cell["unrealised"] * 100 / b["cost"], 2)
								if b["cost"] > 0 and h.last_price else None)
			cells.append(cell)
			bk = brokers.setdefault(b["broker"], {"broker": b["broker"], "value": 0.0,
												  "cost": 0.0, "lines": 0,
												  "currency": h.currency})
			bk["value"] += b["value"]
			bk["cost"] += b["cost"]
			bk["lines"] += 1
			sy = syms.setdefault(h.symbol, {"symbol": h.symbol, "value": 0.0,
											"qty": 0.0, "brokers": 0,
											"currency": h.currency})
			sy["value"] += b["value"]
			sy["qty"] += b["qty"]
			sy["brokers"] += 1

	for bk in brokers.values():
		bk["unrealised"] = bk["value"] - bk["cost"]
		bk["gain_pct"] = (round(bk["unrealised"] * 100 / bk["cost"], 2)
						  if bk["cost"] > 0 else None)
	total = sum(b["value"] for b in brokers.values())
	for bk in brokers.values():
		bk["share"] = round(bk["value"] * 100 / total, 1) if total else 0
	for sy in syms.values():
		sy["share"] = round(sy["value"] * 100 / total, 1) if total else 0

	cells.sort(key=lambda c: (c["broker"], -c["value"]))
	return {
		"cells": cells,
		"brokers": sorted(brokers.values(), key=lambda b: -b["value"]),
		"symbols": sorted(syms.values(), key=lambda s: -s["value"]),
		"total": total,
		# a stock held in more than one place is the case this view exists for
		"split": sorted([s["symbol"] for s in syms.values() if s["brokers"] > 1]),
	}


def _price_on(holding, on_date, cache):
	"""Closing price at or before a date. Carried forward, never guessed."""
	key = (holding, on_date)
	if key in cache:
		return cache[key]
	# the field is price_date. Existing code twenty lines up queries it
	# correctly; I wrote on_date from memory and never checked the doctype.
	row = frappe.get_all("Duty Price Point",
						 filters={"holding": holding, "price_date": ["<=", on_date]},
						 fields=["price", "price_date"],
						 order_by="price_date desc", limit_page_length=1)
	v = (flt(row[0].price), str(row[0].price_date)) if row else (None, None)
	cache[key] = v
	return v


@frappe.whitelist()
def performance(from_date=None, to_date=None):
	"""What the portfolio and each holding did between two dates.

	PRICE MOVEMENT IS NOT PERFORMANCE. Buy a million naira of something halfway
	through a period and a naive "end minus start" reports a million of gain.
	What is returned instead is:

	    gain = (value at end - value at start) - money put in + money taken out
	           + dividends received in the window

	so contributions and withdrawals are stripped out and only what the holdings
	actually did remains. The percentage is against the starting value plus the
	money added, because that is what was at risk.

	Where a holding has no stored price at the start — bought inside the window,
	or history not backfilled that far — the position is stated as beginning at
	zero and the row says so, rather than quietly reporting a gain that is
	really a purchase.
	"""
	require_sysadmin()
	to_d = str(to_date or nowdate())
	from_d = str(from_date or add_months(getdate(to_d), -3))
	if from_d >= to_d:
		frappe.throw(_("The start has to come before the end."))

	cache = {}
	pos = _positions()
	rows, incomplete = [], []

	for h in pos.values():
		trades = frappe.get_all(
			"Duty Trade", filters={"holding": h.name},
			fields=["kind", "trade_date", "quantity", "price", "charges"],
			order_by="trade_date asc, creation asc", limit_page_length=0)
		if not trades:
			continue

		# units held on each boundary, walked from the trades themselves
		q_start = q_end = 0.0
		added = removed = 0.0
		for t in trades:
			d, q = str(t.trade_date), flt(t.quantity)
			cash = q * flt(t.price)
			if d < from_d:
				q_start += q if t.kind == "Buy" else -q
			if d <= to_d:
				q_end += q if t.kind == "Buy" else -q
			if from_d <= d <= to_d:
				if t.kind == "Buy":
					added += cash + flt(t.charges)
				else:
					removed += cash - flt(t.charges)
		if q_start <= 0.0000001 and q_end <= 0.0000001 and not added and not removed:
			continue

		p0, p0_on = _price_on(h.name, from_d, cache)
		p1, p1_on = _price_on(h.name, to_d, cache)
		if p1 is None:
			p1 = flt(h.last_price)
			p1_on = str(h.price_as_of or "")
		if p0 is None and q_start > 0:
			incomplete.append(h.symbol)

		v0 = q_start * flt(p0) if p0 else 0.0
		v1 = q_end * flt(p1) if p1 else 0.0

		div = sum(flt(x.net) for x in frappe.get_all(
			"Duty Dividend",
			filters={"holding": h.name, "pay_date": ["between", [from_d, to_d]]},
			fields=["net"], limit_page_length=0))

		gain = (v1 - v0) - added + removed + div
		base = v0 + added
		rows.append({
			"holding": h.name, "symbol": h.symbol, "name": h.holding_name,
			"currency": h.currency,
			"qty_start": q_start, "qty_end": q_end,
			"price_start": p0, "price_start_on": p0_on,
			"price_end": p1, "price_end_on": p1_on,
			"value_start": v0, "value_end": v1,
			"bought": added, "sold": removed, "dividends": div,
			"gain": gain,
			"gain_pct": round(gain * 100 / base, 2) if base > 0 else None,
			"no_start_price": 1 if (p0 is None and q_start > 0) else 0,
			"new_in_period": 1 if (q_start <= 0.0000001 and q_end > 0) else 0,
		})

	rows.sort(key=lambda r: -abs(r["gain"]))
	by_ccy = {}
	for r in rows:
		c = by_ccy.setdefault(r["currency"], {
			"currency": r["currency"], "value_start": 0.0, "value_end": 0.0,
			"bought": 0.0, "sold": 0.0, "dividends": 0.0, "gain": 0.0})
		for k in ("value_start", "value_end", "bought", "sold", "dividends", "gain"):
			c[k] += r[k]
	for c in by_ccy.values():
		base = c["value_start"] + c["bought"]
		c["gain_pct"] = round(c["gain"] * 100 / base, 2) if base > 0 else None

	# a portfolio line across the window, from the stored closes
	series, day = [], getdate(from_d)
	end = getdate(to_d)
	step = max(1, (end - day).days // 90 or 1)
	while day <= end:
		d = str(day)
		total = 0.0
		for r in rows:
			q = 0.0
			for t in frappe.get_all(
				"Duty Trade", filters={"holding": r["holding"], "trade_date": ["<=", d]},
				fields=["kind", "quantity"], limit_page_length=0):
				q += flt(t.quantity) if t.kind == "Buy" else -flt(t.quantity)
			if q > 0:
				px, _on = _price_on(r["holding"], d, cache)
				if px:
					total += q * px
		series.append({"d": d, "p": total})
		day = add_days(day, step)

	return {
		"from_date": from_d, "to_date": to_d,
		"rows": rows,
		"by_currency": sorted(by_ccy.values(), key=lambda c: -c["value_end"]),
		"series": series,
		"incomplete": sorted(set(incomplete)),
	}
