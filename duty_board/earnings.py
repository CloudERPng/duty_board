"""Performance earnings — computed from data, never stored.

Every figure derives live from Work Sessions, Duty Issues, and Duty
Milestones, so a correction to the underlying record corrects the
payout. Month attribution: sessions by start_time; resolutions by
client_confirmed_at, else resolved_at+7d (auto-pay at base); phase
bonuses by approved_at. All calendar months.
"""

import calendar
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from duty_board.permissions import require_staff


def _settings():
	s = frappe.get_cached_doc("Duty Settings")
	return {
		"cap": cint(s.get("payable_hours_cap")) or 120,
		"m4": flt(s.get("rating_mult_4")) or 1.1,
		"m5": flt(s.get("rating_mult_5")) or 1.25,
		"sla": flt(s.get("sla_bonus")) or 0,
		"phase": flt(s.get("phase_signoff_bonus")) or 0,
	}


def _rates(user):
	row = frappe.get_all(
		"Duty User Rate",
		filters={"user": user, "parenttype": "Duty Settings"},
		fields=["tracked_hourly_rate", "resolution_rate"],
		limit=1,
	)
	if not row:
		return 0.0, 0.0
	return flt(row[0].tracked_hourly_rate), flt(row[0].resolution_rate)


def _month_bounds(year, month):
	start = date(year, month, 1)
	end = date(year, month, calendar.monthrange(year, month)[1])
	return start, end


def _hours_component(user, start, end, cap, rate):
	rows = frappe.db.sql(
		"""select coalesce(sum(duration),0),
			coalesce(sum(case when coalesce(duty_issue,'') != '' or coalesce(project_task,'') != '' then duration else 0 end),0),
			count(*)
		from `tabWork Session`
		where user=%s and coalesce(customer,'') != ''
			and start_time >= %s and start_time < %s and coalesce(duration,0) > 0""",
		(user, str(start), str(end + timedelta(days=1))),
	)[0]
	total_h = flt(rows[0]) / 3600.0
	linked_h = flt(rows[1]) / 3600.0
	paid_h = min(total_h, cap)
	return {
		"sessions": cint(rows[2]),
		"hours": round(total_h, 1),
		"linked_hours": round(linked_h, 1),
		"unlinked_hours": round(max(total_h - linked_h, 0), 1),
		"paid_hours": round(paid_h, 1),
		"cap": cap,
		"capped": 1 if total_h > cap else 0,
		"amount": round(paid_h * rate),
	}


def _resolution_items(user, start, end, base, st):
	"""Client-requested issues this user is an assignee on, earning in
	[start, end]: confirmed in month, or resolved+7d landing in month
	while still unconfirmed."""
	if not base and not st["sla"]:
		return []
	names = frappe.get_all(
		"Duty Issue Assignee", filters={"user": user}, pluck="parent"
	)
	if not names:
		return []
	issues = frappe.get_all(
		"Duty Issue",
		filters={
			"name": ["in", names],
			"client_requested": 1,
			"resolved_at": ["is", "set"],
		},
		fields=[
			"name", "title", "customer", "resolved_at",
			"client_confirmed_at", "client_stars", "sla_res_met",
		],
	)
	out = []
	win_s, win_e = start, end
	for i in issues:
		if i.client_confirmed_at:
			pay_date = getdate(i.client_confirmed_at)
			mode = "confirmed"
		else:
			pay_date = getdate(i.resolved_at) + timedelta(days=7)
			if pay_date > getdate(today()):
				continue  # grace window still open
			mode = "auto"
		if not (win_s <= pay_date <= win_e):
			continue
		n_assn = max(
			frappe.db.count("Duty Issue Assignee", {"parent": i.name}), 1
		)
		mult = 1.0
		if mode == "confirmed":
			stars = cint(i.client_stars)
			mult = st["m5"] if stars >= 5 else st["m4"] if stars == 4 else 1.0
		amount = base * mult / n_assn
		sla_amt = (st["sla"] / n_assn) if cint(i.sla_res_met) else 0
		paid = frappe.get_all(
			"Duty Paid Resolution",
			filters={"issue": i.name, "user": user},
			fields=["amount", "sla_amount"],
			limit=1,
		)
		if paid:
			if mode != "confirmed":
				continue  # auto-pay already settled in a closed month
			delta = amount - flt(paid[0].amount)
			if delta <= 0.5:
				continue  # confirmation adds nothing beyond what was paid
			amount = delta
			sla_amt = max(sla_amt - flt(paid[0].sla_amount), 0)
			mode = "upgrade"
		out.append({
			"issue": i.name,
			"title": i.title,
			"customer": i.customer,
			"mode": mode,
			"stars": cint(i.client_stars) if mode == "confirmed" else None,
			"split": n_assn,
			"amount": round(amount),
			"sla_amount": round(sla_amt),
			"date": str(pay_date),
		})
	out.sort(key=lambda x: x["date"])
	return out


def _phase_items(user, start, end, bonus):
	if not bonus:
		return []
	projects = frappe.get_all(
		"Duty Project Consultant", filters={"user": user}, pluck="parent"
	)
	if not projects:
		return []
	rows = frappe.get_all(
		"Duty Milestone",
		filters={
			"project": ["in", projects],
			"status": "Approved",
			"approved_at": ["between", [str(start), str(end + timedelta(days=1))]],
			"baseline_date": ["is", "set"],
		},
		fields=["name", "title", "project", "approved_at", "baseline_date"],
	)
	out = []
	for m in rows:
		if getdate(m.approved_at) > getdate(m.baseline_date):
			continue  # late sign-off pays zero — the locked decision
		n = max(frappe.db.count("Duty Project Consultant", {"parent": m.project}), 1)
		pname = frappe.db.get_value("Duty Project", m.project, "project_name") or m.project
		out.append({
			"phase": m.title,
			"project": pname,
			"approved": str(getdate(m.approved_at)),
			"baseline": str(m.baseline_date),
			"split": n,
			"amount": round(bonus / n),
		})
	return out


def _compute(user, year, month):
	st = _settings()
	hr_rate, res_rate = _rates(user)
	start, end = _month_bounds(year, month)
	hours = _hours_component(user, start, end, st["cap"], hr_rate)
	resolutions = _resolution_items(user, start, end, res_rate, st)
	phases = _phase_items(user, start, end, st["phase"])
	res_amt = sum(r["amount"] for r in resolutions)
	sla_amt = sum(r["sla_amount"] for r in resolutions)
	ph_amt = sum(p["amount"] for p in phases)
	return {
		"year": year,
		"month": month,
		"label": f"{calendar.month_abbr[month]} {year}",
		"rates": {"hourly": round(hr_rate), "resolution": round(res_rate), "sla": round(st["sla"])},
		"sla_count": sum(1 for r in resolutions if r["sla_amount"]),
		"hours": hours,
		"resolutions": resolutions,
		"phases": phases,
		"totals": {
			"hours": hours["amount"],
			"resolutions": res_amt,
			"sla": sla_amt,
			"phases": ph_amt,
			"grand": hours["amount"] + res_amt + sla_amt + ph_amt,
		},
	}


def _prev_month(year, month):
	return (year - 1, 12) if month == 1 else (year, month - 1)


@frappe.whitelist()
def my_earnings():
	require_staff()
	user = frappe.session.user
	t = getdate(today())
	this_m = _compute(user, t.year, t.month)
	py, pm = _prev_month(t.year, t.month)
	last_m = _compute(user, py, pm)
	rec = frappe.get_all(
		"Duty Payout Record",
		filters={"year": py, "month": pm, "user": user},
		fields=["hours_amt", "res_amt", "sla_amt", "phase_amt", "grand", "paid_hours", "capped"],
		limit=1,
	)
	if rec:
		r = rec[0]
		last_m["closed"] = 1
		last_m["hours"]["paid_hours"] = flt(r.paid_hours)
		last_m["hours"]["capped"] = cint(r.capped)
		last_m["totals"] = {
			"hours": flt(r.hours_amt), "resolutions": flt(r.res_amt),
			"sla": flt(r.sla_amt), "phases": flt(r.phase_amt), "grand": flt(r.grand),
		}
	return {"this_month": this_m, "last_month": last_m}


@frappe.whitelist()
def earnings_summary(year=None, month=None):
	"""Manager payout table: every staff member with any earning
	component, plus the linked/unlinked hours instrument."""
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	t = getdate(today())
	year, month = cint(year) or t.year, cint(month) or t.month
	snap = frappe.get_all(
		"Duty Payout Record",
		filters={"year": year, "month": month},
		fields=[
			"user", "full_name", "paid_hours", "capped", "linked_hours",
			"unlinked_hours", "hours_amt", "res_count", "res_amt", "sla_amt",
			"phase_amt", "grand", "closed_by", "closed_on",
		],
	)
	if snap:
		rows = [
			{
				"user": s.user, "full_name": s.full_name,
				"paid_hours": flt(s.paid_hours), "capped": cint(s.capped),
				"linked_hours": flt(s.linked_hours), "unlinked_hours": flt(s.unlinked_hours),
				"hours_amt": flt(s.hours_amt), "res_count": cint(s.res_count),
				"res_amt": flt(s.res_amt) + flt(s.sla_amt), "phase_amt": flt(s.phase_amt),
				"grand": flt(s.grand),
			}
			for s in snap
		]
		rows.sort(key=lambda x: -x["grand"])
		return {
			"year": year, "month": month,
			"label": f"{calendar.month_abbr[month]} {year}",
			"closed": 1,
			"closed_by": frappe.utils.get_fullname(snap[0].closed_by) if snap[0].closed_by else "",
			"closed_on": str(snap[0].closed_on)[:10] if snap[0].closed_on else "",
			"rows": rows,
		}
	users = frappe.get_all(
		"Duty User Rate",
		filters={"parenttype": "Duty Settings"},
		pluck="user",
	)
	out = []
	for u in sorted(set(users)):
		c = _compute(u, year, month)
		if not c["totals"]["grand"] and not c["hours"]["hours"]:
			continue
		out.append({
			"user": u,
			"full_name": frappe.utils.get_fullname(u),
			"paid_hours": c["hours"]["paid_hours"],
			"capped": c["hours"]["capped"],
			"linked_hours": c["hours"]["linked_hours"],
			"unlinked_hours": c["hours"]["unlinked_hours"],
			"hours_amt": c["totals"]["hours"],
			"res_count": len(c["resolutions"]),
			"res_amt": c["totals"]["resolutions"] + c["totals"]["sla"],
			"phase_amt": c["totals"]["phases"],
			"grand": c["totals"]["grand"],
		})
	out.sort(key=lambda x: -x["grand"])
	return {"year": year, "month": month, "label": f"{calendar.month_abbr[month]} {year}", "rows": out}


@frappe.whitelist()
def close_month(year, month):
	"""Freeze a fully-ended month: write per-person Duty Payout Records
	and register every paid resolution so the delta rule has memory.
	Idempotent by refusal: a closed month cannot be closed again."""
	require_staff()
	if "System Manager" not in frappe.get_roles():
		frappe.throw(_("Managers only."), frappe.PermissionError)
	year, month = cint(year), cint(month)
	_start, end = _month_bounds(year, month)
	if end >= getdate(today()):
		frappe.throw(_("The month hasn't ended yet — close it after it's over."))
	if frappe.db.exists("Duty Payout Record", {"year": year, "month": month}):
		frappe.throw(_("That month is already closed."))
	users = sorted(set(frappe.get_all(
		"Duty User Rate", filters={"parenttype": "Duty Settings"}, pluck="user"
	)))
	mkey = f"{year:04d}-{month:02d}"
	now = frappe.utils.now()
	closed = 0
	for u in users:
		c = _compute(u, year, month)
		if not c["totals"]["grand"] and not c["hours"]["hours"]:
			continue
		frappe.get_doc({
			"doctype": "Duty Payout Record",
			"year": year, "month": month, "user": u,
			"full_name": frappe.utils.get_fullname(u),
			"paid_hours": c["hours"]["paid_hours"],
			"linked_hours": c["hours"]["linked_hours"],
			"unlinked_hours": c["hours"]["unlinked_hours"],
			"capped": c["hours"]["capped"],
			"hours_amt": c["totals"]["hours"],
			"res_count": len(c["resolutions"]),
			"res_amt": c["totals"]["resolutions"],
			"sla_amt": c["totals"]["sla"],
			"phase_amt": c["totals"]["phases"],
			"grand": c["totals"]["grand"],
			"closed_by": frappe.session.user,
			"closed_on": now,
		}).insert(ignore_permissions=True)
		for item in c["resolutions"]:
			existing = frappe.get_all(
				"Duty Paid Resolution",
				filters={"issue": item["issue"], "user": u},
				fields=["name", "amount", "sla_amount"],
				limit=1,
			)
			if existing:
				frappe.db.set_value("Duty Paid Resolution", existing[0].name, {
					"amount": flt(existing[0].amount) + item["amount"],
					"sla_amount": flt(existing[0].sla_amount) + item["sla_amount"],
				})
			else:
				frappe.get_doc({
					"doctype": "Duty Paid Resolution",
					"issue": item["issue"], "user": u, "month_key": mkey,
					"amount": item["amount"], "sla_amount": item["sla_amount"],
				}).insert(ignore_permissions=True)
		closed += 1
	frappe.db.commit()
	return {"closed": closed, "label": f"{calendar.month_abbr[month]} {year}"}
