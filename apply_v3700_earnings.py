#!/usr/bin/env python3
"""Duty Board v3.70.0 — performance earnings, per the locked decisions.

Components, per person per calendar month:
1. HOURS — every Work Session with a customer (linked or not, decision
   12c/13b), by start_time, capped (settings, default 120h/month) × the
   person's tracked_hourly_rate. Manager view shows the linked/unlinked
   split so drift in the service-line data stays visible.
2. RESOLUTIONS — client-REQUESTED Duty Issues resolved by the assignees:
   pays on client confirmation (client_confirmed_at month) at base ×
   rating multiplier (4★/5★, settings); unconfirmed auto-pays BASE 7
   days after resolved_at (attributed to that month). Split equally
   among the issue's assignees.
3. SLA KICKER — flat bonus per within-SLA resolution (sla_res_met).
4. PHASE BONUS — milestones Approved ON/BEFORE their baseline_date only
   (late sign-off pays zero), bonus split equally among the project's
   consultants, attributed to the approved_at month.

Schema: Duty User Rate +tracked_hourly_rate, +resolution_rate (Currency).
Duty Settings +payable_hours_cap (120), +rating_mult_4 (1.1),
+rating_mult_5 (1.25), +sla_bonus, +phase_signoff_bonus (Currency).

Surfaces: Me face 💵 Earnings card (this month + last month, itemised);
manager per-person payout table appended to the 💰 Cost-to-serve dialog.

Schema -> bench migrate && bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.69.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
URDT = "duty_board/duty_board/doctype/duty_user_rate/duty_user_rate.json"
DSDT = "duty_board/duty_board/doctype/duty_settings/duty_settings.json"
EARN = "duty_board/earnings.py"
CHECK_ONLY = "--check" in sys.argv

EARN_PY = '''"""Performance earnings — computed from data, never stored.

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
'''

# --- JS: earnings card placeholder + loader (piggyback the leave card) ------
PLACE_OLD = '''\t\t\t<div class="duty-me-leave"></div>
\t\t\t<div class="duty-me-cal">'''
PLACE_NEW = '''\t\t\t<div class="duty-me-leave"></div>
\t\t\t<div class="duty-me-earn"></div>
\t\t\t<div class="duty-me-cal">'''

LOAD_OLD = '''\t\tthis._load_leave_card();
\t\tthis.$me.find(".duty-req-sg").on("click", (e) =>'''
LOAD_NEW = '''\t\tthis._load_leave_card();
\t\tthis._load_earnings_card();
\t\tthis.$me.find(".duty-req-sg").on("click", (e) =>'''

# --- JS: earnings card methods, before _load_leave_card ---------------------
METH_OLD = '\t_load_leave_card() {'
METH_NEW = '''\t_load_earnings_card() {
\t\tconst $host = this.$me.find(".duty-me-earn");
\t\tif (!$host.length) return;
\t\tfrappe.call({
\t\t\tmethod: "duty_board.earnings.my_earnings",
\t\t\tcallback: (r) => r.message && this._render_earnings_card(r.message),
\t\t});
\t}

\t_render_earnings_card(E) {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst $host = this.$me.find(".duty-me-earn");
\t\tif (!$host.length) return;
\t\tconst naira = (n) => "₦" + (n || 0).toLocaleString();
\t\tconst tm = E.this_month, lm = E.last_month;
\t\tif (!tm.totals.grand && !lm.totals.grand) { $host.empty(); return; }
\t\tconst block = (c, open) => `
\t\t\t<details ${open ? "open" : ""} class="duty-earn-m">
\t\t\t\t<summary><b>${esc(c.label)}</b><span class="duty-earn-grand">${naira(c.totals.grand)}</span></summary>
\t\t\t\t<div class="duty-earn-line">⏱ ${__("Customer hours")}: <b>${c.hours.paid_hours}h</b>${c.hours.capped ? ` <span class="duty-earn-cap">(${__("capped from")} ${c.hours.hours}h)</span>` : ""} × ${__("rate")} = <b>${naira(c.totals.hours)}</b> <span class="text-muted">· ${c.hours.linked_hours}h ${__("linked")} / ${c.hours.unlinked_hours}h ${__("unlinked")}</span></div>
\t\t\t\t${c.resolutions.length ? `<div class="duty-earn-line">✅ ${__("Resolutions")} (${c.resolutions.length}): <b>${naira(c.totals.resolutions)}</b>${c.totals.sla ? ` + ${__("SLA")} <b>${naira(c.totals.sla)}</b>` : ""}</div>
\t\t\t\t<div class="duty-earn-items">${c.resolutions.map((x) => `<div>${esc(x.title)} <span class="text-muted">· ${esc(x.customer || "")}${x.mode === "confirmed" ? (x.stars ? ` · ${"★".repeat(x.stars)}` : " · " + __("confirmed")) : " · " + __("auto (7d)")}${x.split > 1 ? ` · ÷${x.split}` : ""}</span><b style="margin-left:auto">${naira(x.amount + x.sla_amount)}</b></div>`).join("")}</div>` : ""}
\t\t\t\t${c.phases.length ? `<div class="duty-earn-line">🚩 ${__("Phase sign-offs on baseline")}: <b>${naira(c.totals.phases)}</b></div>
\t\t\t\t<div class="duty-earn-items">${c.phases.map((p) => `<div>${esc(p.phase)} <span class="text-muted">· ${esc(p.project)} · ${__("approved")} ${esc(p.approved)}${p.split > 1 ? ` · ÷${p.split}` : ""}</span><b style="margin-left:auto">${naira(p.amount)}</b></div>`).join("")}</div>` : ""}
\t\t\t</details>`;
\t\t$host.html(`
\t\t\t<div class="duty-me-reqs duty-earn-card">
\t\t\t\t<h4>💵 ${__("Earnings")}</h4>
\t\t\t\t${block(tm, true)}
\t\t\t\t${block(lm, false)}
\t\t\t</div>`);
\t}

\t_load_leave_card() {'''

# --- JS: manager payout table appended to the 💰 dialog ----------------------
DLG_OLD = '''\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("Untyped = unlinked sessions logged before service lines existed (or a person's first unlinked session). Bulk-classify history once and the column empties; the sticky default keeps it empty.")}</p>
\t\t\t\t\t\t`);
\t\t\t\t\t},
\t\t\t\t});'''
DLG_NEW = '''\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("Untyped = unlinked sessions logged before service lines existed (or a person's first unlinked session). Bulk-classify history once and the column empties; the sticky default keeps it empty.")}</p>
\t\t\t\t\t\t\t<div class="duty-pay"><div class="text-muted" style="font-size:12px">${__("Loading payouts…")}</div></div>
\t\t\t\t\t\t`);
\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\tmethod: "duty_board.earnings.earnings_summary",
\t\t\t\t\t\t\tcallback: (pr) => {
\t\t\t\t\t\t\t\tconst P = pr.message || {};
\t\t\t\t\t\t\t\tconst rows = (P.rows || []).map((p) => `<tr>
\t\t\t\t\t\t\t\t\t<td><b>${frappe.utils.escape_html(p.full_name)}</b></td>
\t\t\t\t\t\t\t\t\t<td>${p.paid_hours}h${p.capped ? " ⛔" : ""}<div class="text-muted" style="font-size:10.5px">${p.linked_hours}h ${__("linked")} / ${p.unlinked_hours}h ${__("unlinked")}</div></td>
\t\t\t\t\t\t\t\t\t<td>${naira(p.hours_amt)}</td>
\t\t\t\t\t\t\t\t\t<td>${p.res_count}</td>
\t\t\t\t\t\t\t\t\t<td>${naira(p.res_amt)}</td>
\t\t\t\t\t\t\t\t\t<td>${naira(p.phase_amt)}</td>
\t\t\t\t\t\t\t\t\t<td><b>${naira(p.grand)}</b></td>
\t\t\t\t\t\t\t\t</tr>`).join("");
\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay").html(rows
\t\t\t\t\t\t\t\t\t? `<h5 style="margin:14px 0 6px">💵 ${__("Payouts")} — ${frappe.utils.escape_html(P.label || "")}</h5>
\t\t\t\t\t\t\t\t\t\t<table class="table table-sm" style="font-size:12px"><tr><th>${__("Person")}</th><th>${__("Paid hours")}</th><th>${__("Hours ₦")}</th><th>${__("Res.")}</th><th>${__("Res. ₦")}</th><th>${__("Phase ₦")}</th><th>${__("Total")}</th></tr>${rows}</table>
\t\t\t\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("⛔ = monthly cap reached. Watch the unlinked share — a rising unlinked fraction means hours are drifting away from issues and tasks.")}</p>`
\t\t\t\t\t\t\t\t\t: "");
\t\t\t\t\t\t\t},
\t\t\t\t\t\t});
\t\t\t\t\t},
\t\t\t\t});'''

# --- JS: CSS -----------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-lv-ask .duty-lv-note { max-width: 220px; }'
CSS_NEW = '''\t\t\t.duty-lv-ask .duty-lv-note { max-width: 220px; }
\t\t\t.duty-earn-m { border-bottom: 1px dashed var(--border-color, #eee); padding: 6px 0; }
\t\t\t.duty-earn-m:last-child { border-bottom: none; }
\t\t\t.duty-earn-m summary { cursor: pointer; display: flex; gap: 10px; align-items: baseline; list-style: none; }
\t\t\t.duty-earn-grand { margin-left: auto; font-weight: 800; color: #0E8A63; }
\t\t\t.duty-earn-line { font-size: 13px; margin: 6px 0 2px; }
\t\t\t.duty-earn-cap { color: #B45309; font-weight: 700; font-size: 12px; }
\t\t\t.duty-earn-items { margin: 2px 0 6px 18px; display: flex; flex-direction: column; gap: 2px; }
\t\t\t.duty-earn-items > div { display: flex; gap: 8px; align-items: baseline; font-size: 12.5px; }'''


def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = json.load(f)
    added = False
    for fl in new_fields:
        if any(x["fieldname"] == fl["fieldname"] for x in dt["fields"]):
            continue
        dt["fields"].append(fl)
        if "field_order" in dt:
            dt["field_order"].append(fl["fieldname"])
        added = True
    if added:
        with io.open(path, "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if os.path.exists(os.path.join(root, EARN)):
        print("Already applied. Nothing to do.")
        return
    if '"3.69.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.69.0.")

    checks = [
        (JS, PLACE_OLD, "earn placeholder"), (JS, LOAD_OLD, "earn loader"),
        (JS, METH_OLD, "earn methods"), (JS, DLG_OLD, "payout table"),
        (JS, CSS_OLD, "css"),
    ]
    problems = [f"  [{files[f].count(o)}] {label}" for f, o, label in checks if files[f].count(o) != 1]
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print(f"All {len(checks)} anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, URDT), [
        {"fieldname": "tracked_hourly_rate", "fieldtype": "Currency", "label": "Tracked Hourly Rate (₦/h)", "in_list_view": 1},
        {"fieldname": "resolution_rate", "fieldtype": "Currency", "label": "Per-Resolution Rate (₦)", "in_list_view": 1},
    ])
    print("  Duty User Rate +tracked_hourly_rate +resolution_rate")

    add_fields(os.path.join(root, DSDT), [
        {"fieldname": "earnings_section", "fieldtype": "Section Break", "label": "Performance Earnings"},
        {"fieldname": "payable_hours_cap", "fieldtype": "Int", "label": "Payable Hours Cap (per month)", "default": "120"},
        {"fieldname": "rating_mult_4", "fieldtype": "Float", "label": "4-Star Multiplier", "default": "1.1", "precision": "2"},
        {"fieldname": "rating_mult_5", "fieldtype": "Float", "label": "5-Star Multiplier", "default": "1.25", "precision": "2"},
        {"fieldname": "sla_bonus", "fieldtype": "Currency", "label": "Within-SLA Resolution Bonus (₦)"},
        {"fieldname": "phase_signoff_bonus", "fieldtype": "Currency", "label": "Phase Sign-off Bonus (₦, on-baseline only)"},
    ])
    print("  Duty Settings +earnings section (cap, multipliers, SLA + phase bonuses)")

    with io.open(os.path.join(root, EARN), "w", encoding="utf-8") as f:
        f.write(EARN_PY)
    print("  duty_board/earnings.py created")

    js = files[JS]
    for o, n in [(PLACE_OLD, PLACE_NEW), (LOAD_OLD, LOAD_NEW), (METH_OLD, METH_NEW), (DLG_OLD, DLG_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: 💵 Earnings card + manager payout table")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.69.0"', '"3.70.0"'))
    print("wrote __init__.py -> 3.70.0")


if __name__ == "__main__":
    main()
