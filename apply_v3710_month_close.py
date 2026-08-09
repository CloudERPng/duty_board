#!/usr/bin/env python3
"""Duty Board v3.71.0 — month-close: paid months stay paid.

The structural flaw in live-computed earnings: nothing recorded what was
actually PAID, so rate changes, session edits, or late client
confirmations could silently move a month you'd already transferred.
Worst case was a double-pay: auto-paid at base in month M, client
confirms with stars in M+1, issue pays again in full.

This adds:
- Duty Payout Record — per person per closed month: the frozen figures
  (hours/amounts/resolutions/phases/grand), who closed it, when.
- Duty Paid Resolution — registry of every resolution included in a
  closed payout (issue, user, amount, sla) — the delta rule's memory.
- DELTA RULE in _resolution_items: an issue already paid (auto, base)
  that is later confirmed pays only the multiplier DIFFERENCE in the
  confirmation month ("upgrade" items); an already-paid issue never
  pays base twice.
- close_month(year, month) — manager-only, only for fully-ended months,
  refuses double-close. Writes snapshots + registry in one pass.
- earnings_summary serves CLOSED months from the snapshot (flagged);
  my_earnings overlays the person's frozen totals on a closed last
  month (🔒 shown on the card).
- UI: 🔒 Close button on the payout table's last-month view; closed
  months show who closed and when instead.

Schema (2 doctypes) -> bench migrate && bench build && bench restart.
Anchored, idempotent. Requires v3.70.2.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
EARN = "duty_board/earnings.py"
PRDIR = "duty_board/duty_board/doctype/duty_payout_record"
PDDIR = "duty_board/duty_board/doctype/duty_paid_resolution"
CHECK_ONLY = "--check" in sys.argv


def _dt(name, fields, order):
    return {
        "actions": [], "autoname": "hash",
        "creation": "2026-08-09 12:00:00.000000", "doctype": "DocType",
        "engine": "InnoDB", "field_order": order, "fields": fields,
        "links": [], "modified": "2026-08-09 12:00:00.000000",
        "modified_by": "Administrator", "module": "Duty Board",
        "name": name, "naming_rule": "Random", "owner": "Administrator",
        "permissions": [{"create": 1, "delete": 1, "read": 1, "report": 1, "role": "System Manager", "write": 1}],
        "sort_field": "modified", "sort_order": "DESC", "states": [],
    }


PAYOUT_DT = _dt(
    "Duty Payout Record",
    [
        {"fieldname": "year", "fieldtype": "Int", "label": "Year", "reqd": 1},
        {"fieldname": "month", "fieldtype": "Int", "label": "Month", "reqd": 1},
        {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1},
        {"fieldname": "full_name", "fieldtype": "Data", "label": "Full Name"},
        {"fieldname": "paid_hours", "fieldtype": "Float", "label": "Paid Hours", "precision": "1"},
        {"fieldname": "linked_hours", "fieldtype": "Float", "label": "Linked Hours", "precision": "1"},
        {"fieldname": "unlinked_hours", "fieldtype": "Float", "label": "Unlinked Hours", "precision": "1"},
        {"fieldname": "capped", "fieldtype": "Check", "label": "Capped"},
        {"fieldname": "hours_amt", "fieldtype": "Currency", "label": "Hours Amount"},
        {"fieldname": "res_count", "fieldtype": "Int", "label": "Resolutions"},
        {"fieldname": "res_amt", "fieldtype": "Currency", "label": "Resolution Amount"},
        {"fieldname": "sla_amt", "fieldtype": "Currency", "label": "SLA Amount"},
        {"fieldname": "phase_amt", "fieldtype": "Currency", "label": "Phase Amount"},
        {"fieldname": "grand", "fieldtype": "Currency", "label": "Grand Total"},
        {"fieldname": "closed_by", "fieldtype": "Link", "label": "Closed By", "options": "User"},
        {"fieldname": "closed_on", "fieldtype": "Datetime", "label": "Closed On"},
    ],
    ["year", "month", "user", "full_name", "paid_hours", "linked_hours", "unlinked_hours", "capped", "hours_amt", "res_count", "res_amt", "sla_amt", "phase_amt", "grand", "closed_by", "closed_on"],
)

PAID_DT = _dt(
    "Duty Paid Resolution",
    [
        {"fieldname": "issue", "fieldtype": "Link", "label": "Issue", "options": "Duty Issue", "reqd": 1},
        {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "reqd": 1},
        {"fieldname": "month_key", "fieldtype": "Data", "label": "Month (YYYY-MM)"},
        {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount Paid"},
        {"fieldname": "sla_amount", "fieldtype": "Currency", "label": "SLA Paid"},
    ],
    ["issue", "user", "month_key", "amount", "sla_amount"],
)

# --- earnings.py edit 1: delta rule in _resolution_items --------------------
R1_OLD = '''\t\tamount = base * mult / n_assn
\t\tsla_amt = (st["sla"] / n_assn) if cint(i.sla_res_met) else 0
\t\tout.append({'''
R1_NEW = '''\t\tamount = base * mult / n_assn
\t\tsla_amt = (st["sla"] / n_assn) if cint(i.sla_res_met) else 0
\t\tpaid = frappe.get_all(
\t\t\t"Duty Paid Resolution",
\t\t\tfilters={"issue": i.name, "user": user},
\t\t\tfields=["amount", "sla_amount"],
\t\t\tlimit=1,
\t\t)
\t\tif paid:
\t\t\tif mode != "confirmed":
\t\t\t\tcontinue  # auto-pay already settled in a closed month
\t\t\tdelta = amount - flt(paid[0].amount)
\t\t\tif delta <= 0.5:
\t\t\t\tcontinue  # confirmation adds nothing beyond what was paid
\t\t\tamount = delta
\t\t\tsla_amt = max(sla_amt - flt(paid[0].sla_amount), 0)
\t\t\tmode = "upgrade"
\t\tout.append({'''

# --- earnings.py edit 2: closed-month serving in earnings_summary -----------
R2_OLD = '''\tyear, month = cint(year) or t.year, cint(month) or t.month
\tusers = frappe.get_all('''
R2_NEW = '''\tyear, month = cint(year) or t.year, cint(month) or t.month
\tsnap = frappe.get_all(
\t\t"Duty Payout Record",
\t\tfilters={"year": year, "month": month},
\t\tfields=[
\t\t\t"user", "full_name", "paid_hours", "capped", "linked_hours",
\t\t\t"unlinked_hours", "hours_amt", "res_count", "res_amt", "sla_amt",
\t\t\t"phase_amt", "grand", "closed_by", "closed_on",
\t\t],
\t)
\tif snap:
\t\trows = [
\t\t\t{
\t\t\t\t"user": s.user, "full_name": s.full_name,
\t\t\t\t"paid_hours": flt(s.paid_hours), "capped": cint(s.capped),
\t\t\t\t"linked_hours": flt(s.linked_hours), "unlinked_hours": flt(s.unlinked_hours),
\t\t\t\t"hours_amt": flt(s.hours_amt), "res_count": cint(s.res_count),
\t\t\t\t"res_amt": flt(s.res_amt) + flt(s.sla_amt), "phase_amt": flt(s.phase_amt),
\t\t\t\t"grand": flt(s.grand),
\t\t\t}
\t\t\tfor s in snap
\t\t]
\t\trows.sort(key=lambda x: -x["grand"])
\t\treturn {
\t\t\t"year": year, "month": month,
\t\t\t"label": f"{calendar.month_abbr[month]} {year}",
\t\t\t"closed": 1,
\t\t\t"closed_by": frappe.utils.get_fullname(snap[0].closed_by) if snap[0].closed_by else "",
\t\t\t"closed_on": str(snap[0].closed_on)[:10] if snap[0].closed_on else "",
\t\t\t"rows": rows,
\t\t}
\tusers = frappe.get_all('''

# --- earnings.py edit 3: my_earnings overlays closed last month -------------
R3_OLD = '''\tthis_m = _compute(user, t.year, t.month)
\tpy, pm = _prev_month(t.year, t.month)
\tlast_m = _compute(user, py, pm)
\treturn {"this_month": this_m, "last_month": last_m}'''
R3_NEW = '''\tthis_m = _compute(user, t.year, t.month)
\tpy, pm = _prev_month(t.year, t.month)
\tlast_m = _compute(user, py, pm)
\trec = frappe.get_all(
\t\t"Duty Payout Record",
\t\tfilters={"year": py, "month": pm, "user": user},
\t\tfields=["hours_amt", "res_amt", "sla_amt", "phase_amt", "grand", "paid_hours", "capped"],
\t\tlimit=1,
\t)
\tif rec:
\t\tr = rec[0]
\t\tlast_m["closed"] = 1
\t\tlast_m["hours"]["paid_hours"] = flt(r.paid_hours)
\t\tlast_m["hours"]["capped"] = cint(r.capped)
\t\tlast_m["totals"] = {
\t\t\t"hours": flt(r.hours_amt), "resolutions": flt(r.res_amt),
\t\t\t"sla": flt(r.sla_amt), "phases": flt(r.phase_amt), "grand": flt(r.grand),
\t\t}
\treturn {"this_month": this_m, "last_month": last_m}'''

# --- earnings.py edit 4: close_month endpoint (appended) --------------------
R4_APPEND = '''

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
'''

# --- JS edit 1: close button / closed banner in payout table ----------------
J1_OLD = '''</b></td></tr></table>
\t\t\t\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("⛔ = monthly cap reached. Watch the unlinked share — a rising unlinked fraction means hours are drifting away from issues and tasks.")}</p>` : `<p class="text-muted" style="font-size:12px">${__("No earnings recorded for")} ${frappe.utils.escape_html(P.label || "")}.</p>`}`);'''
J1_NEW = '''</b></td></tr></table>
\t\t\t\t\t\t\t\t\t\t${P.closed ? `<p style="font-size:12px;color:#0B6B4F;font-weight:700">🔒 ${__("Closed")} ${frappe.utils.escape_html(P.closed_on || "")}${P.closed_by ? ` ${__("by")} ${frappe.utils.escape_html(P.closed_by)}` : ""} — ${__("these figures are frozen.")}</p>` : !isCur ? `<button class="btn btn-xs btn-default duty-pay-close" data-y="${P.year}" data-m="${P.month}">🔒 ${__("Close")} ${frappe.utils.escape_html(P.label || "")} — ${__("freeze these figures")}</button>` : ""}
\t\t\t\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("⛔ = monthly cap reached. Watch the unlinked share — a rising unlinked fraction means hours are drifting away from issues and tasks.")}</p>` : `<p class="text-muted" style="font-size:12px">${__("No earnings recorded for")} ${frappe.utils.escape_html(P.label || "")}.</p>`}`);'''

J2_OLD = '''\t\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay-tog a").on("click", (ev) => loadPay($(ev.currentTarget).data("y"), $(ev.currentTarget).data("m")));'''
J2_NEW = '''\t\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay-tog a").on("click", (ev) => loadPay($(ev.currentTarget).data("y"), $(ev.currentTarget).data("m")));
\t\t\t\t\t\t\t\t\t$(d.body).find(".duty-pay-close").on("click", (ev) => {
\t\t\t\t\t\t\t\t\t\tconst y = $(ev.currentTarget).data("y"), m = $(ev.currentTarget).data("m");
\t\t\t\t\t\t\t\t\t\tfrappe.confirm(__("Close this month? Figures freeze permanently — rate changes and record edits will no longer move them."), () =>
\t\t\t\t\t\t\t\t\t\t\tfrappe.call({ method: "duty_board.earnings.close_month", args: { year: y, month: m }, callback: () => { frappe.show_alert({ message: __("Month closed."), indicator: "green" }); loadPay(y, m); } }));
\t\t\t\t\t\t\t\t\t});'''

# --- JS edit 2: 🔒 on the Me-card closed month + upgrade item label ---------
J3_OLD = '<summary><b>${esc(c.label)}</b><span class="duty-earn-grand">${naira(c.totals.grand)}</span></summary>'
J3_NEW = '<summary><b>${esc(c.label)}</b>${c.closed ? `<span class="duty-earn-lock">🔒 ${__("closed")}</span>` : ""}<span class="duty-earn-grand">${naira(c.totals.grand)}</span></summary>'

J4_OLD = '${x.mode === "confirmed" ? (x.stars ? "★".repeat(x.stars) : __("confirmed")) : __("auto (7d)")}'
J4_NEW = '${x.mode === "confirmed" ? (x.stars ? "★".repeat(x.stars) : __("confirmed")) : x.mode === "upgrade" ? `${x.stars ? "★".repeat(x.stars) + " " : ""}${__("upgrade")}` : __("auto (7d)")}'

CSS_OLD = '\t\t\t.duty-pay-tot td { border-top: 2px solid #123C35 !important; background: #F4F8F6; }'
CSS_NEW = '''\t\t\t.duty-pay-tot td { border-top: 2px solid #123C35 !important; background: #F4F8F6; }
\t\t\t.duty-earn-lock { font-size: 11px; font-weight: 700; color: #7A8783; background: #F0F4F3; border-radius: 20px; padding: 2px 8px; }
\t\t\t.duty-pay-close { margin: 6px 0 2px; }'''


def write_dt(root, dirpath, dtjson, classname):
    d = os.path.join(root, dirpath)
    os.makedirs(d, exist_ok=True)
    base = os.path.basename(dirpath)
    with io.open(os.path.join(d, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(d, base + ".json"), "w", encoding="utf-8") as f:
        json.dump(dtjson, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(d, base + ".py"), "w", encoding="utf-8") as f:
        f.write(f"import frappe\nfrom frappe.model.document import Document\n\n\nclass {classname}(Document):\n\tpass\n")


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, EARN):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def close_month(" in files[EARN]:
        print("Already applied. Nothing to do.")
        return
    if '"3.70.2"' not in files[INIT]:
        sys.exit("ABORT: not at v3.70.2.")

    checks = [
        (EARN, R1_OLD, "delta rule"), (EARN, R2_OLD, "summary closed-serve"),
        (EARN, R3_OLD, "my_earnings overlay"),
        (JS, J1_OLD, "close button"), (JS, J2_OLD, "close binding"),
        (JS, J3_OLD, "card lock badge"), (JS, J4_OLD, "upgrade label"),
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

    write_dt(root, PRDIR, PAYOUT_DT, "DutyPayoutRecord")
    write_dt(root, PDDIR, PAID_DT, "DutyPaidResolution")
    print("  doctypes: Duty Payout Record + Duty Paid Resolution created")

    e = files[EARN]
    for o, n in [(R1_OLD, R1_NEW), (R2_OLD, R2_NEW), (R3_OLD, R3_NEW)]:
        e = e.replace(o, n, 1)
    e += R4_APPEND
    with io.open(os.path.join(root, EARN), "w", encoding="utf-8") as f:
        f.write(e)
    print("  earnings.py: delta rule, closed-month serving, overlay, close_month")

    js = files[JS]
    for o, n in [(J1_OLD, J1_NEW), (J2_OLD, J2_NEW), (J3_OLD, J3_NEW), (J4_OLD, J4_NEW), (CSS_OLD, CSS_NEW)]:
        js = js.replace(o, n, 1)
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: close action, closed banner, 🔒 badge, upgrade label")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.70.2"', '"3.71.0"'))
    print("wrote __init__.py -> 3.71.0")


if __name__ == "__main__":
    main()
