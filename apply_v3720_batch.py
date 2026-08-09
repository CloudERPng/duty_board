#!/usr/bin/env python3
"""Duty Board v3.72.0 — the agreed follow-up batch, five items:

1. OVERLAP VISIBILITY: each pending leave request in the approvals block
   now shows who ELSE is already approved (or pending) away during any
   part of that period — "⚠ also away: …" — so approving never
   accidentally empties a function.
2. APPROVER NUDGE: submitting a leave request notifies every System
   Manager immediately (realtime + web push via _notify_user) instead
   of waiting to be discovered on the Me face.
3. CAP PROGRESS: the earnings hours line reads "41.7h / 120h × ₦300" —
   staff see the ceiling approaching instead of hitting it blind.
4. NOT-FIXED FIX (real bug from the review): client_reopen cleared
   client_confirmed_at but NOT resolved_at — so an issue the client
   rejected still auto-paid base 7 days after the ORIGINAL resolution.
   Reopen now clears resolved_at and sla_res_met too: a rejected
   resolution earns nothing until genuinely re-resolved.
5. PUBLIC HOLIDAYS: new child table in Duty Settings (Duty Holiday:
   date + name). Holidays no longer consume leave days (_workdays
   skips them) and no meeting slots are offered on them. Fill the
   Nigerian calendar once a year.

Schema (child doctype + settings field) -> bench migrate && bench build
--app duty_board && bench restart. Anchored, idempotent. Requires v3.71.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
LEAVE = "duty_board/leave.py"
EARN = "duty_board/earnings.py"
CR = "duty_board/client_room.py"
DSDT = "duty_board/duty_board/doctype/duty_settings/duty_settings.json"
HDIR = "duty_board/duty_board/doctype/duty_holiday"
CHECK_ONLY = "--check" in sys.argv

HOLIDAY_DT = {
    "actions": [], "autoname": "hash",
    "creation": "2026-08-09 13:00:00.000000", "doctype": "DocType",
    "engine": "InnoDB", "istable": 1,
    "field_order": ["holiday_date", "title"],
    "fields": [
        {"fieldname": "holiday_date", "fieldtype": "Date", "label": "Date", "reqd": 1, "in_list_view": 1},
        {"fieldname": "title", "fieldtype": "Data", "label": "Holiday", "in_list_view": 1},
    ],
    "links": [], "modified": "2026-08-09 13:00:00.000000",
    "modified_by": "Administrator", "module": "Duty Board",
    "name": "Duty Holiday", "naming_rule": "Random", "owner": "Administrator",
    "permissions": [], "sort_field": "modified", "sort_order": "DESC", "states": [],
}

# --- 1. leave.py: holidays helper + _workdays skips them --------------------
WD_OLD = '''def _workdays(start, end):
\t"""Weekdays (Mon-Fri) inclusive between two dates."""
\ts, e = getdate(start), getdate(end)
\tif e < s:
\t\treturn 0
\tn, d = 0, s
\twhile d <= e:
\t\tif d.weekday() < 5:
\t\t\tn += 1
\t\td += timedelta(days=1)
\treturn n'''
WD_NEW = '''def holidays():
\t"""Public-holiday dates from Duty Settings (Duty Holiday child rows)."""
\ttry:
\t\ts = frappe.get_cached_doc("Duty Settings")
\t\treturn {getdate(h.holiday_date) for h in (s.get("public_holidays") or []) if h.holiday_date}
\texcept Exception:
\t\treturn set()


def _workdays(start, end):
\t"""Weekdays (Mon-Fri) inclusive between two dates, public holidays
\texcluded — a holiday inside a leave range costs no leave day."""
\ts, e = getdate(start), getdate(end)
\tif e < s:
\t\treturn 0
\thols = holidays()
\tn, d = 0, s
\twhile d <= e:
\t\tif d.weekday() < 5 and d not in hols:
\t\t\tn += 1
\t\td += timedelta(days=1)
\treturn n'''

# --- 2. leave.py: overlap names on pending approvals ------------------------
OV_OLD = '''\t\t\tp.remaining = max(_entitlement(p.user) - _taken(p.user, getdate(p.start_date).year), 0)
\t\tdata["pending"] = pend'''
OV_NEW = '''\t\t\tp.remaining = max(_entitlement(p.user) - _taken(p.user, getdate(p.start_date).year), 0)
\t\t\tothers = frappe.get_all(
\t\t\t\t"Duty Leave Request",
\t\t\t\tfilters={
\t\t\t\t\t"user": ["!=", p.user],
\t\t\t\t\t"status": ["in", ["Approved", "Pending"]],
\t\t\t\t\t"start_date": ["<=", p.end_date],
\t\t\t\t\t"end_date": [">=", p.start_date],
\t\t\t\t},
\t\t\t\tfields=["user", "status"],
\t\t\t)
\t\t\tseen = {}
\t\t\tfor o in others:
\t\t\t\tif o.user not in seen or o.status == "Approved":
\t\t\t\t\tseen[o.user] = o.status
\t\t\tp.also_away = [
\t\t\t\t{"name": frappe.utils.get_fullname(u), "status": st}
\t\t\t\tfor u, st in seen.items()
\t\t\t]
\t\tdata["pending"] = pend'''

# --- 3. leave.py: notify System Managers on new request ---------------------
NT_OLD = '''\t).insert(ignore_permissions=True)
\tfrappe.db.commit()
\treturn my_leave()'''
NT_NEW = '''\t).insert(ignore_permissions=True)
\tfrappe.db.commit()
\ttry:
\t\tfrom duty_board.api import _notify_user

\t\tfull = frappe.utils.get_fullname(user)
\t\tsms = {
\t\t\tu
\t\t\tfor u in frappe.get_all(
\t\t\t\t"Has Role",
\t\t\t\tfilters={"role": "System Manager", "parenttype": "User"},
\t\t\t\tpluck="parent",
\t\t\t)
\t\t\tif u not in ("Administrator", user)
\t\t\tand frappe.db.get_value("User", u, "enabled")
\t\t}
\t\tfor sm in sms:
\t\t\t_notify_user(
\t\t\t\tsm,
\t\t\t\t_("🌴 Leave request: {0}").format(full),
\t\t\t\t_("{0} → {1} · {2} day(s). Approve on your Me screen.").format(str(s), str(e), days),
\t\t\t)
\texcept Exception:
\t\tfrappe.log_error(frappe.get_traceback(), "leave request notify")
\treturn my_leave()'''

# --- 4. client_room.py: not-fixed clears resolved_at + sla_res_met ----------
RF_OLD = '\tfrappe.db.set_value("Duty Issue", row.name, "client_confirmed_at", None, update_modified=False)'
RF_NEW = '''\tfrappe.db.set_value("Duty Issue", row.name, "client_confirmed_at", None, update_modified=False)
\t# A rejected resolution is not a resolution: clear resolved_at so the
\t# earnings auto-pay clock stops, and sla_res_met so a failed fix
\t# doesn't keep its SLA credit. Both re-set on genuine re-resolution.
\tfrappe.db.set_value("Duty Issue", row.name, "resolved_at", None, update_modified=False)
\tfrappe.db.set_value("Duty Issue", row.name, "sla_res_met", 0, update_modified=False)'''

# --- 5. client_room.py: no meeting slots on holidays ------------------------
MS_OLD = '''\tfrom duty_board.leave import is_on_leave
\tfor u in staff_list:
\t\tif is_on_leave(u, d):
\t\t\treturn []  # a requested attendee is on leave that day'''
MS_NEW = '''\tfrom duty_board.leave import holidays, is_on_leave
\tif d in holidays():
\t\treturn []  # public holiday — nobody is bookable
\tfor u in staff_list:
\t\tif is_on_leave(u, d):
\t\t\treturn []  # a requested attendee is on leave that day'''

# --- 6. earnings.py: cap in payload -----------------------------------------
CAP_OLD = '''\t\t"paid_hours": round(paid_h, 1),
\t\t"capped": 1 if total_h > cap else 0,'''
CAP_NEW = '''\t\t"paid_hours": round(paid_h, 1),
\t\t"cap": cap,
\t\t"capped": 1 if total_h > cap else 0,'''

# --- 7. JS: cap progress on the hours line ----------------------------------
JC_OLD = '<span class="duty-earn-calc"><b>${c.hours.paid_hours}h</b> × ${naira(c.rates.hourly)}'
JC_NEW = '<span class="duty-earn-calc"><b>${c.hours.paid_hours}h</b><span class="text-muted"> / ${c.hours.cap || 120}h</span> × ${naira(c.rates.hourly)}'

# --- 8. JS: also-away line on approval rows ---------------------------------
JA_OLD = '''\t\t\t\t<span class="text-muted">${p.remaining} ${__("left")}${p.note ? " · " + esc(p.note) : ""}</span>'''
JA_NEW = '''\t\t\t\t<span class="text-muted">${p.remaining} ${__("left")}${p.note ? " · " + esc(p.note) : ""}</span>
\t\t\t\t${(p.also_away || []).length ? `<span class="duty-lv-clash">⚠ ${__("also away then")}: ${p.also_away.map((a) => `${esc(a.name)}${a.status === "Pending" ? ` <i>(${__("pending")})</i>` : ""}`).join(", ")}</span>` : ""}'''

# --- 9. JS: CSS --------------------------------------------------------------
CSS_OLD = '\t\t\t.duty-pay-close { margin: 6px 0 2px; }'
CSS_NEW = '''\t\t\t.duty-pay-close { margin: 6px 0 2px; }
\t\t\t.duty-lv-clash { width: 100%; font-size: 12px; color: #B45309; font-weight: 700; }
\t\t\t.duty-lv-clash i { font-weight: 400; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, LEAVE, EARN, CR):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def holidays():" in files[LEAVE]:
        print("Already applied. Nothing to do.")
        return
    if '"3.71.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.71.0.")

    checks = [
        (LEAVE, WD_OLD, "workdays+holidays"), (LEAVE, OV_OLD, "overlap names"),
        (LEAVE, NT_OLD, "approver nudge"), (CR, RF_OLD, "not-fixed fix"),
        (CR, MS_OLD, "holiday slots"), (EARN, CAP_OLD, "cap payload"),
        (JS, JC_OLD, "cap progress"), (JS, JA_OLD, "also-away line"),
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

    # holiday child doctype
    hdir = os.path.join(root, HDIR)
    os.makedirs(hdir, exist_ok=True)
    with io.open(os.path.join(hdir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("")
    with io.open(os.path.join(hdir, "duty_holiday.json"), "w", encoding="utf-8") as f:
        json.dump(HOLIDAY_DT, f, indent=1)
        f.write("\n")
    with io.open(os.path.join(hdir, "duty_holiday.py"), "w", encoding="utf-8") as f:
        f.write("import frappe\nfrom frappe.model.document import Document\n\n\nclass DutyHoliday(Document):\n\tpass\n")
    print("  doctype: Duty Holiday (child) created")

    # settings field
    with io.open(os.path.join(root, DSDT), encoding="utf-8") as f:
        dt = json.load(f)
    if not any(fl["fieldname"] == "public_holidays" for fl in dt["fields"]):
        dt["fields"].append({
            "fieldname": "holidays_section", "fieldtype": "Section Break", "label": "Public Holidays",
        })
        dt["fields"].append({
            "fieldname": "public_holidays", "fieldtype": "Table",
            "label": "Public Holidays", "options": "Duty Holiday",
        })
        if "field_order" in dt:
            dt["field_order"].extend(["holidays_section", "public_holidays"])
        with io.open(os.path.join(root, DSDT), "w", encoding="utf-8") as f:
            json.dump(dt, f, indent=1)
            f.write("\n")
    print("  Duty Settings +public_holidays table")

    files[LEAVE] = files[LEAVE].replace(WD_OLD, WD_NEW, 1).replace(OV_OLD, OV_NEW, 1).replace(NT_OLD, NT_NEW, 1)
    files[CR] = files[CR].replace(RF_OLD, RF_NEW, 1).replace(MS_OLD, MS_NEW, 1)
    files[EARN] = files[EARN].replace(CAP_OLD, CAP_NEW, 1)
    files[JS] = files[JS].replace(JC_OLD, JC_NEW, 1).replace(JA_OLD, JA_NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    files[INIT] = files[INIT].replace('"3.71.0"', '"3.72.0"')

    for p in (LEAVE, CR, EARN, JS, INIT):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  leave.py / client_room.py / earnings.py / duty_board.js patched")
    print("wrote __init__.py -> 3.72.0")


if __name__ == "__main__":
    main()
