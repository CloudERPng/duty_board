#!/usr/bin/env python3
"""Duty Board v3.68.0 — the service-line dimension (allocation instrument).

The accounting-vs-ERP decision needs "who spends what on which service
line at what cost" — and today accounting hours are indistinguishable
from internal work. This adds the dimension with near-zero tagging
burden:

- Schema: Work Session +work_type (Select: Accounting Service / ERP
  Delivery / ERP Support / Internal & Product). Optional at input.
- Deriver (controller validate, catches EVERY creation path): explicit
  choice wins; else project_task -> ERP Delivery; duty_issue -> ERP
  Support; else STICKY — the user's last work_type on an unlinked
  session. First-ever unlinked session stays untyped (visible in the
  report as Untyped rather than silently guessed).
- Backfill patch (committed in-repo): stamps historical linked sessions
  (task->Delivery, issue->Support). Unlinked history stays untyped for
  a per-team bulk classification you run once (SQL provided in the
  deploy notes) — that also seeds each person's sticky default.
- cost_to_serve: hour-kind split now reads work_type with derivation
  fallback for old rows — one source of truth, no drift.
- NEW service_line_allocation(months): user x work_type -> hours + cost
  (per-user rates), the report the accounting decision falls out of.
  Rendered as a second section in the 💰 Cost-to-serve dialog.

Schema -> bench migrate && bench build --app duty_board && bench restart.
Anchored, idempotent. Requires v3.67.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
COM = "duty_board/commercial.py"
WSDT = "duty_board/duty_board/doctype/work_session/work_session.json"
WSPY = "duty_board/duty_board/doctype/work_session/work_session.py"
PATCHES = "duty_board/patches.txt"
BACKFILL = "duty_board/patches/backfill_work_type.py"
CHECK_ONLY = "--check" in sys.argv

WORK_TYPES = "Accounting Service\nERP Delivery\nERP Support\nInternal & Product"

# --- 2. controller deriver ---------------------------------------------------
WSPY_OLD = '''class WorkSession(Document):
\tdef validate(self):
\t\tself.enforce_own_session()
\t\tself.set_duration()'''
WSPY_NEW = '''class WorkSession(Document):
\tdef validate(self):
\t\tself.enforce_own_session()
\t\tself.set_duration()
\t\tself.set_work_type()

\tdef set_work_type(self):
\t\t"""Service line: explicit choice wins; else derived from linkage;
\t\telse sticky (user's last choice on unlinked work). Left empty when
\t\tnothing is known — Untyped is visible, a silent guess is not."""
\t\tif self.work_type:
\t\t\treturn
\t\tif self.project_task:
\t\t\tself.work_type = "ERP Delivery"
\t\telif self.duty_issue:
\t\t\tself.work_type = "ERP Support"
\t\telse:
\t\t\tlast = frappe.db.get_value(
\t\t\t\t"Work Session",
\t\t\t\t{
\t\t\t\t\t"user": self.user,
\t\t\t\t\t"work_type": ["in", ["Accounting Service", "Internal & Product"]],
\t\t\t\t},
\t\t\t\t"work_type",
\t\t\t\torder_by="creation desc",
\t\t\t)
\t\t\tif last:
\t\t\t\tself.work_type = last'''

# --- 4. cost_to_serve reads work_type with fallback --------------------------
CTS_OLD = '''\t\t\tsum(case when coalesce(duty_issue, '') != '' then duration else 0 end) as support_secs,
\t\t\tsum(case when coalesce(project_task, '') != '' then duration else 0 end) as delivery_secs'''
CTS_NEW = '''\t\t\tsum(case when work_type = 'ERP Support' or (coalesce(work_type,'') = '' and coalesce(duty_issue, '') != '') then duration else 0 end) as support_secs,
\t\t\tsum(case when work_type = 'ERP Delivery' or (coalesce(work_type,'') = '' and coalesce(project_task, '') != '') then duration else 0 end) as delivery_secs'''

# --- 5. the allocation endpoint, appended at end of commercial.py -----------
ALLOC = '''

@frappe.whitelist()
def service_line_allocation(months=1):
\t"""Person x service line: hours and loaded cost. The instrument the
\taccounting-vs-ERP capacity decision falls out of."""
\trequire_staff()
\tfrom duty_board.accounting import _books_manager

\tif not _books_manager():
\t\tfrappe.throw(_("Managers only."), frappe.PermissionError)
\tmonths = max(1, min(cint(months) or 1, 12))
\tsince = frappe.utils.add_months(today(), -months)
\trows = frappe.db.sql(
\t\t"""
\t\tselect user,
\t\t\tcase
\t\t\t\twhen coalesce(work_type, '') != '' then work_type
\t\t\t\twhen coalesce(project_task, '') != '' then 'ERP Delivery'
\t\t\t\twhen coalesce(duty_issue, '') != '' then 'ERP Support'
\t\t\t\telse 'Untyped'
\t\t\tend as line,
\t\t\tsum(duration) as secs
\t\tfrom `tabWork Session`
\t\twhere start_time >= %s and coalesce(duration, 0) > 0
\t\tgroup by user, line
\t\t""",
\t\t(since,),
\t\tas_dict=True,
\t)
\tfrom duty_board.permissions import get_user_rate

\tLINES = ["Accounting Service", "ERP Delivery", "ERP Support", "Internal & Product", "Untyped"]
\tpeople = {}
\tfor r in rows:
\t\tp = people.setdefault(r.user, {"user": r.user, "full_name": frappe.utils.get_fullname(r.user), "total_hours": 0.0, "cost": 0.0, "lines": {k: 0.0 for k in LINES}})
\t\thours = flt(r.secs) / 3600.0
\t\tp["lines"][r.line if r.line in p["lines"] else "Untyped"] += hours
\t\tp["total_hours"] += hours
\tfor p in people.values():
\t\tp["cost"] = round(p["total_hours"] * flt(get_user_rate(p["user"])))
\t\tp["total_hours"] = round(p["total_hours"], 1)
\t\tp["lines"] = {k: round(v, 1) for k, v in p["lines"].items()}
\tout = sorted(people.values(), key=lambda x: -x["total_hours"])
\treturn {"months": months, "lines": LINES, "rows": out}
'''

# --- 6. append allocation section to the cost dialog ------------------------
DLG_OLD = '''\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("Hours from work sessions with a customer; fee shown where known (accounting fee today). Red rows: attention cost exceeds known fee — a renewal-conversation list, not an invoice list.")}</p>
\t\t\t\t`);
\t\t\t\td.show();'''
DLG_NEW = '''\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("Hours from work sessions with a customer; fee shown where known (accounting fee today). Red rows: attention cost exceeds known fee — a renewal-conversation list, not an invoice list.")}</p>
\t\t\t\t\t<div class="duty-alloc"><div class="text-muted" style="font-size:12px">${__("Loading service-line allocation…")}</div></div>
\t\t\t\t`);
\t\t\t\td.show();
\t\t\t\tfrappe.call({
\t\t\t\t\tmethod: "duty_board.commercial.service_line_allocation",
\t\t\t\t\targs: { months: 1 },
\t\t\t\t\tcallback: (ar) => {
\t\t\t\t\t\tconst a = ar.message || {};
\t\t\t\t\t\tconst lines = a.lines || [];
\t\t\t\t\t\tconst hdr = lines.map((l) => `<th>${frappe.utils.escape_html(l.replace("Accounting Service", "Accounting").replace("Internal & Product", "Internal"))}</th>`).join("");
\t\t\t\t\t\tconst body = (a.rows || []).map((p) => `<tr>
\t\t\t\t\t\t\t<td><b>${frappe.utils.escape_html(p.full_name)}</b></td>
\t\t\t\t\t\t\t${lines.map((l) => `<td>${p.lines[l] ? `<b>${p.lines[l]}</b>` : `<span class="text-muted">—</span>`}</td>`).join("")}
\t\t\t\t\t\t\t<td><b>${p.total_hours}</b></td><td>${naira(p.cost)}</td>
\t\t\t\t\t\t</tr>`).join("");
\t\t\t\t\t\t$(d.body).find(".duty-alloc").html(`
\t\t\t\t\t\t\t<h5 style="margin:14px 0 6px">👤 ${__("By person × service line — hours (last month)")}</h5>
\t\t\t\t\t\t\t<table class="table table-sm" style="font-size:12px"><tr><th>${__("Person")}</th>${hdr}<th>${__("Total")}</th><th>${__("Cost")}</th></tr>${body}</table>
\t\t\t\t\t\t\t<p class="text-muted" style="font-size:11px">${__("Untyped = unlinked sessions logged before service lines existed (or a person's first unlinked session). Bulk-classify history once and the column empties; the sticky default keeps it empty.")}</p>
\t\t\t\t\t\t`);
\t\t\t\t\t},
\t\t\t\t});'''

BACKFILL_BODY = '''"""Stamp work_type onto historical Work Sessions where derivable from
linkage: project_task -> ERP Delivery, duty_issue -> ERP Support.

Unlinked history is deliberately left untyped — it needs a human call
(Accounting vs Internal), made once per team via bulk SQL, which also
seeds each person's sticky default. Idempotent: only touches rows where
work_type is empty.
"""

import frappe


def execute():
	if not frappe.db.has_column("Work Session", "work_type"):
		return
	frappe.db.sql(
		"""update `tabWork Session`
		set work_type = 'ERP Delivery'
		where coalesce(work_type, '') = '' and coalesce(project_task, '') != ''"""
	)
	frappe.db.sql(
		"""update `tabWork Session`
		set work_type = 'ERP Support'
		where coalesce(work_type, '') = '' and coalesce(duty_issue, '') != ''"""
	)
	frappe.db.commit()
'''


def add_field(dt_path):
    with io.open(dt_path, encoding="utf-8") as f:
        dt = json.load(f)
    if any(fl["fieldname"] == "work_type" for fl in dt["fields"]):
        return False
    dt["fields"].append({
        "fieldname": "work_type", "fieldtype": "Select",
        "label": "Service Line", "options": WORK_TYPES,
    })
    if "field_order" in dt:
        dt["field_order"].append("work_type")
    with io.open(dt_path, "w", encoding="utf-8") as f:
        json.dump(dt, f, indent=1)
        f.write("\n")
    return True


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, COM, WSPY, PATCHES):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def set_work_type(" in files[WSPY]:
        print("Already applied. Nothing to do.")
        return
    if '"3.67.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.67.0.")

    checks = [
        (WSPY, WSPY_OLD, "controller"), (COM, CTS_OLD, "cost_to_serve split"),
        (JS, DLG_OLD, "cost dialog"),
    ]
    problems = [f"  [{files[f].count(o)}] {label}" for f, o, label in checks if files[f].count(o) != 1]
    if "backfill_work_type" in files[PATCHES]:
        problems.append("  backfill already registered")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_field(os.path.join(root, WSDT))
    print("  doctype: Work Session +work_type")

    with io.open(os.path.join(root, WSPY), "w", encoding="utf-8") as f:
        f.write(files[WSPY].replace(WSPY_OLD, WSPY_NEW, 1))
    print("  work_session.py: deriver + sticky default")

    with io.open(os.path.join(root, BACKFILL), "w", encoding="utf-8") as f:
        f.write(BACKFILL_BODY)
    with io.open(os.path.join(root, PATCHES), "w", encoding="utf-8") as f:
        f.write(files[PATCHES].rstrip("\n") + "\nduty_board.patches.backfill_work_type\n")
    print("  backfill patch created + registered (in-repo, committed with the rest)")

    com = files[COM].replace(CTS_OLD, CTS_NEW, 1) + ALLOC
    with io.open(os.path.join(root, COM), "w", encoding="utf-8") as f:
        f.write(com)
    print("  commercial.py: cost_to_serve reads work_type; service_line_allocation added")

    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(files[JS].replace(DLG_OLD, DLG_NEW, 1))
    print("  duty_board.js: allocation table in cost dialog")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.67.0"', '"3.68.0"'))
    print("wrote __init__.py -> 3.68.0")


if __name__ == "__main__":
    main()
