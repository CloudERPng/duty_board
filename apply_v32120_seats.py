#!/usr/bin/env python3
"""Duty Board v3.212.0 — SEATS: catalogue, order, proforma, approval, enforcement.

Until now entitlement was a comma-separated product string on the room, which
works when training is a consequence of being an ERP client and collapses the
moment it is sold. This adds the commercial spine for selling seats.

The flow, end to end:
  1. The client's administrator opens the catalogue and sees every certification
     track available to them, marked Included (covered by their subscription's
     products, unchanged behaviour) or Paid with a per-seat price.
  2. They request a paid track with a seat count. A Duty Academy Order is raised,
     a proforma is rendered, filed on their Documents shelf and emailed to them
     with the bank details, and the approver is notified.
  3. Payment lands. A human — the academy approver in Duty Settings, defaulting
     to the CR pricer — approves the order against a payment reference. Nothing
     is automatic; money is confirmed by a person.
  4. Approval writes a Duty Academy Entitlement: seats, granted date, optional
     expiry. That record, not the product string, is what unlocks a paid track.
  5. Assignment consumes seats. A seat is one named learner on one track. When
     they run out, the administrator is refused and told how many are left.

Seat accounting is deliberately generous in one direction and strict in the
other: a seat is counted per distinct learner per track, so assigning someone a
nine-course track burns one seat rather than nine; but a seat is never silently
reclaimed, because a learner who has begun holds it.

Expiry blocks NEW assignment only. People already learning finish, and issued
certificates never lapse — a certificate records what someone demonstrated on a
date, and that stays true when a subscription does not.

  Duty Settings: +academy_bank_details, +academy_approver, +academy_vat_rate
  Duty Certification Track: +access (Included/Paid), +seat_price
  Duty Academy Order (AOR-YYYY-#####), Duty Academy Entitlement (AEN-YYYY-#####)
  New module duty_board/academy.py — carries both faces, so like client_room.py
  it is not registered in the staff-denial permission suite; every client
  endpoint resolves the room from membership first and every mutation is
  administrator-guarded.

Deploy: apply -> bench migrate -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. Anchored, idempotent. Requires v3.211.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
ACAD = "duty_board/academy.py"
PORTAL = "duty_board/www/portal.html"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
DSDT = "duty_board/duty_board/doctype/duty_settings/duty_settings.json"
TRKDT = "duty_board/duty_board/doctype/duty_certification_track/duty_certification_track.json"
DT_DIR = "duty_board/duty_board/doctype"
CHECK_ONLY = "--check" in sys.argv


ORDER_JSON = {
    "actions": [], "autoname": "format:AOR-{YYYY}-{#####}",
    "creation": "2026-08-13 14:00:00.000000", "doctype": "DocType", "engine": "InnoDB",
    "field_order": [
        "room", "track", "track_title", "seats", "unit_price", "amount", "vat",
        "total", "status", "requested_by", "requested_on", "note", "payment_ref",
        "approved_by", "approved_on", "decline_reason", "entitlement",
    ],
    "fields": [
        {"fieldname": "room", "fieldtype": "Link", "label": "Client Room", "options": "Client Room", "reqd": 1, "in_list_view": 1},
        {"fieldname": "track", "fieldtype": "Link", "label": "Track", "options": "Duty Certification Track", "reqd": 1},
        {"fieldname": "track_title", "fieldtype": "Data", "label": "Track Title", "in_list_view": 1},
        {"fieldname": "seats", "fieldtype": "Int", "label": "Seats", "reqd": 1, "in_list_view": 1},
        {"fieldname": "unit_price", "fieldtype": "Currency", "label": "Price per Seat"},
        {"fieldname": "amount", "fieldtype": "Currency", "label": "Amount"},
        {"fieldname": "vat", "fieldtype": "Currency", "label": "VAT"},
        {"fieldname": "total", "fieldtype": "Currency", "label": "Total", "in_list_view": 1},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status",
         "options": "Requested\nApproved\nDeclined\nCancelled", "default": "Requested", "in_list_view": 1},
        {"fieldname": "requested_by", "fieldtype": "Data", "label": "Requested By"},
        {"fieldname": "requested_on", "fieldtype": "Datetime", "label": "Requested On"},
        {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
        {"fieldname": "payment_ref", "fieldtype": "Data", "label": "Payment Reference"},
        {"fieldname": "approved_by", "fieldtype": "Data", "label": "Approved By"},
        {"fieldname": "approved_on", "fieldtype": "Datetime", "label": "Approved On"},
        {"fieldname": "decline_reason", "fieldtype": "Small Text", "label": "Decline Reason"},
        {"fieldname": "entitlement", "fieldtype": "Data", "label": "Entitlement", "read_only": 1},
    ],
    "index_web_pages_for_search": 1, "links": [],
    "modified": "2026-08-13 14:00:00.000000", "modified_by": "Administrator",
    "module": "Duty Board", "name": "Duty Academy Order", "owner": "Administrator",
    "permissions": [{"create": 1, "delete": 1, "email": 1, "export": 1, "print": 1,
                     "read": 1, "report": 1, "role": "System Manager", "share": 1, "write": 1}],
    "sort_field": "modified", "sort_order": "DESC", "states": [], "title_field": "track_title",
}

ENT_JSON = {
    "actions": [], "autoname": "format:AEN-{YYYY}-{#####}",
    "creation": "2026-08-13 14:00:00.000000", "doctype": "DocType", "engine": "InnoDB",
    "field_order": ["room", "track", "seats", "granted_on", "expires_on", "status", "source_order", "note"],
    "fields": [
        {"fieldname": "room", "fieldtype": "Link", "label": "Client Room", "options": "Client Room", "reqd": 1, "in_list_view": 1},
        {"fieldname": "track", "fieldtype": "Link", "label": "Track", "options": "Duty Certification Track", "reqd": 1, "in_list_view": 1},
        {"fieldname": "seats", "fieldtype": "Int", "label": "Seats", "reqd": 1, "in_list_view": 1},
        {"fieldname": "granted_on", "fieldtype": "Date", "label": "Granted On"},
        {"fieldname": "expires_on", "fieldtype": "Date", "label": "Expires On"},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status",
         "options": "Active\nExpired\nRevoked", "default": "Active", "in_list_view": 1},
        {"fieldname": "source_order", "fieldtype": "Data", "label": "Source Order"},
        {"fieldname": "note", "fieldtype": "Small Text", "label": "Note"},
    ],
    "index_web_pages_for_search": 1, "links": [],
    "modified": "2026-08-13 14:00:00.000000", "modified_by": "Administrator",
    "module": "Duty Board", "name": "Duty Academy Entitlement", "owner": "Administrator",
    "permissions": [{"create": 1, "delete": 1, "email": 1, "export": 1, "print": 1,
                     "read": 1, "report": 1, "role": "System Manager", "share": 1, "write": 1}],
    "sort_field": "modified", "sort_order": "DESC", "states": [],
}

CTRL = '''# Copyright (c) 2026, Xlevel Retail Systems Ltd
import frappe
from frappe.model.document import Document


class {cls}(Document):
\tpass
'''


ACADEMY_PY = '''"""Academy commerce: catalogue, seat orders, entitlements.

Selling training needs an object that a product string cannot express: how many
people were paid for, from when, until when. That is Duty Academy Entitlement,
and it is the only thing that unlocks a Paid track.

This module carries both faces — the client administrator raising an order, and
staff approving it — so like client_room.py it is deliberately absent from the
staff-denial permission suite. Every client endpoint resolves the room from
membership as its first act, and every mutation is administrator-guarded.

Approval is manual and always will be. Money is confirmed by a person.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, today
from frappe.utils.pdf import get_pdf


def _staff_only():
\tfrom duty_board.permissions import require_staff

\trequire_staff()


def _room():
\tfrom duty_board.client_room import _client_room

\treturn _client_room()


def _room_admin():
\tfrom duty_board.client_room import _require_room_admin

\treturn _require_room_admin()


def _settings():
\treturn frappe.get_cached_doc("Duty Settings")


def _approver():
\ts = _settings()
\treturn (s.get("academy_approver") or s.get("cr_pricer") or "").strip()


def _track_modules(track):
\treturn frappe.get_all(
\t\t"Duty Certification Track Module", filters={"parent": track},
\t\tpluck="module", order_by="idx asc",
\t)


def seats_used(room, track):
\t"""One seat is one named learner on one track, however many courses that
\ttrack contains. Counted from live training records, so it cannot drift."""
\tmods = _track_modules(track)
\tif not mods:
\t\treturn 0
\trows = frappe.get_all(
\t\t"Duty Training Record",
\t\tfilters={"room": room, "module": ["in", mods]},
\t\tfields=["trainee"],
\t)
\treturn len({r.trainee for r in rows if r.trainee})


def entitlement_for(room, track):
\t"""Total live seats for a room/track. Several orders accumulate. An expiry
\tin the past stops counting toward NEW assignment."""
\trows = frappe.get_all(
\t\t"Duty Academy Entitlement",
\t\tfilters={"room": room, "track": track, "status": "Active"},
\t\tfields=["name", "seats", "expires_on"],
\t)
\ttoday_d = getdate(today())
\tlive = [r for r in rows if not r.expires_on or getdate(r.expires_on) >= today_d]
\texpired = [r for r in rows if r.expires_on and getdate(r.expires_on) < today_d]
\treturn {
\t\t"seats": sum(cint(r.seats) for r in live),
\t\t"expired_seats": sum(cint(r.seats) for r in expired),
\t\t"any": bool(rows),
\t\t"expires_on": min(
\t\t\t(str(r.expires_on) for r in live if r.expires_on), default=None
\t\t),
\t}


def seat_gate(room, track, new_learners):
\t"""Raise unless there is room for this many additional named learners.
\tCalled from every path that can put somebody on a paid track."""
\tif not new_learners:
\t\treturn
\taccess = frappe.db.get_value("Duty Certification Track", track, "access") or "Included"
\tif access != "Paid":
\t\treturn
\tent = entitlement_for(room, track)
\tif not ent["seats"]:
\t\tif ent["expired_seats"]:
\t\t\tfrappe.throw(_("Your seats for this track have expired. Request more to continue."))
\t\tfrappe.throw(_("This track has not been purchased yet. Request seats from the catalogue."))
\tleft = ent["seats"] - seats_used(room, track)
\tif new_learners > left:
\t\tfrappe.throw(
\t\t\t_("Not enough seats: {0} left of {1}, and you are assigning {2} more people.").format(
\t\t\t\tmax(left, 0), ent["seats"], new_learners
\t\t\t)
\t\t)


# ---------------- client face ----------------


@frappe.whitelist()
def academy_catalogue():
\t"""Every active client track, marked Included or Paid, with this room's
\tseat position and any order already in flight."""
\tfrom duty_board.client_room import _room_products

\troom = _room_admin()
\tprods = _room_products(room)
\tout = []
\tfor t in frappe.get_all(
\t\t"Duty Certification Track",
\t\tfilters={"active": 1, "audience": "Client"},
\t\tfields=["name", "title", "product", "description", "access", "seat_price"],
\t\torder_by="access asc, product asc, title asc",
\t):
\t\tn = frappe.db.count("Duty Certification Track Module", {"parent": t.name})
\t\tif not n:
\t\t\tcontinue
\t\taccess = t.access or "Included"
\t\tincluded = access != "Paid" and (t.product or "").strip().lower() in prods
\t\tent = entitlement_for(room.name, t.name) if access == "Paid" else None
\t\tused = seats_used(room.name, t.name) if access == "Paid" else 0
\t\tpending = frappe.db.get_value(
\t\t\t"Duty Academy Order",
\t\t\t{"room": room.name, "track": t.name, "status": "Requested"},
\t\t\t["name", "seats"], as_dict=True,
\t\t)
\t\tif access != "Paid" and not included:
\t\t\tcontinue  # an included track outside their products is simply not theirs
\t\tout.append({
\t\t\t"track": t.name,
\t\t\t"title": t.title,
\t\t\t"product": t.product,
\t\t\t"description": t.description,
\t\t\t"courses": n,
\t\t\t"access": access,
\t\t\t"included": included,
\t\t\t"seat_price": flt(t.seat_price),
\t\t\t"seats": ent["seats"] if ent else None,
\t\t\t"seats_used": used,
\t\t\t"seats_left": max(ent["seats"] - used, 0) if ent else None,
\t\t\t"expires_on": ent["expires_on"] if ent else None,
\t\t\t"pending": pending.name if pending else None,
\t\t\t"pending_seats": pending.seats if pending else None,
\t\t})
\treturn out


def _proforma_html(order, room):
\tesc = frappe.utils.escape_html
\tbank = (_settings().get("academy_bank_details") or "").strip()
\tfmt = lambda v: frappe.utils.fmt_money(v, currency="NGN")
\treturn """<html><head><meta charset="utf-8"><style>
@page {{ size: A4 portrait; margin: 18mm 16mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #16211F; font-size: 12px; }}
h1 {{ font-size: 20px; margin: 0 0 2px; color: #0A473F; }}
.sub {{ color: #6B7C77; font-size: 11px; margin-bottom: 20px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
th {{ text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .8px;
\tcolor: #6B7C77; border-bottom: 1px solid #DCE4E1; padding: 6px 4px; }}
td {{ padding: 7px 4px; border-bottom: 1px solid #F0F4F2; }}
.tot td {{ font-weight: 700; border-bottom: none; }}
.bank {{ margin-top: 22px; background: #F4F7F6; border-radius: 8px; padding: 12px 14px;
\twhite-space: pre-wrap; font-size: 11.5px; }}
.foot {{ margin-top: 24px; color: #6B7C77; font-size: 10px; border-top: 1px solid #DCE4E1; padding-top: 8px; }}
</style></head><body>
<h1>Proforma invoice {name}</h1>
<div class="sub">{customer} &middot; issued {issued} &middot; CloudERP.One Academy</div>
<table>
\t<tr><th>Description</th><th style="text-align:center">Seats</th>
\t\t<th style="text-align:right">Per seat</th><th style="text-align:right">Amount</th></tr>
\t<tr><td>{track} &mdash; certification track ({courses} courses)</td>
\t\t<td style="text-align:center">{seats}</td>
\t\t<td style="text-align:right">{unit}</td>
\t\t<td style="text-align:right">{amount}</td></tr>
\t<tr><td colspan="3" style="text-align:right">VAT</td><td style="text-align:right">{vat}</td></tr>
\t<tr class="tot"><td colspan="3" style="text-align:right">Total due</td>
\t\t<td style="text-align:right">{total}</td></tr>
</table>
<div class="bank">{bank}</div>
<div class="foot">One seat entitles one named member of your staff to the full track and, on passing
each assessment, a verifiable certificate. Seats are activated once payment is confirmed.
Xlevel Retail Systems Ltd.</div>
</body></html>""".format(
\t\tname=esc(order.name), customer=esc(room.customer or room.name),
\t\tissued=frappe.utils.format_date(today(), "d MMMM yyyy"),
\t\ttrack=esc(order.track_title), courses=len(_track_modules(order.track)),
\t\tseats=order.seats, unit=fmt(order.unit_price), amount=fmt(order.amount),
\t\tvat=fmt(order.vat), total=fmt(order.total),
\t\tbank=esc(bank) or "Bank details will follow by email.",
\t)


@frappe.whitelist()
def academy_request(track, seats, note=None):
\t"""Raise a seat order. Files a proforma on the client's shelf, emails it
\twith the bank details, and tells the approver. Grants nothing."""
\tfrom duty_board.client_room import _post

\troom = _room_admin()
\tseats = cint(seats)
\tif seats < 1:
\t\tfrappe.throw(_("How many seats do you need?"))
\tt = frappe.db.get_value(
\t\t"Duty Certification Track", track,
\t\t["title", "access", "seat_price", "active", "audience"], as_dict=True,
\t)
\tif not t or not cint(t.active) or t.audience != "Client":
\t\tfrappe.throw(_("Not found."))
\tif (t.access or "Included") != "Paid":
\t\tfrappe.throw(_("That track is already included in your subscription."))
\tif frappe.db.exists("Duty Academy Order", {"room": room.name, "track": track, "status": "Requested"}):
\t\tfrappe.throw(_("You already have a request in progress for this track."))
\tunit = flt(t.seat_price)
\tamount = unit * seats
\trate = flt(_settings().get("academy_vat_rate") or 7.5)
\tvat = round(amount * rate / 100, 2)
\torder = frappe.get_doc({
\t\t"doctype": "Duty Academy Order",
\t\t"room": room.name, "track": track, "track_title": t.title, "seats": seats,
\t\t"unit_price": unit, "amount": amount, "vat": vat, "total": amount + vat,
\t\t"status": "Requested", "requested_by": frappe.session.user,
\t\t"requested_on": now_datetime(), "note": note,
\t}).insert(ignore_permissions=True)
\tfrappe.db.commit()

\tpdf = get_pdf(_proforma_html(order, room))
\tfname = "Proforma_%s.pdf" % order.name
\tf = frappe.get_doc({
\t\t"doctype": "File", "file_name": fname, "content": pdf, "is_private": 1
\t}).insert(ignore_permissions=True)
\tfrappe.get_doc({
\t\t"doctype": "Client Shelf Doc", "room": room.name,
\t\t"title": _("Proforma invoice — {0}").format(order.track_title),
\t\t"category": _("Training"), "file_url": f.file_url, "file_name": fname, "active": 1,
\t}).insert(ignore_permissions=True)
\tfrappe.db.commit()

\tfmt = lambda v: frappe.utils.fmt_money(v, currency="NGN")
\ttry:
\t\tfrappe.sendmail(
\t\t\trecipients=[frappe.session.user],
\t\t\tcc=[_approver()] if _approver() else None,
\t\t\tsubject=_("Proforma {0} — {1} ({2} seats)").format(order.name, t.title, seats),
\t\t\tmessage="""<p>Thank you for your request.</p>
<p><b>{title}</b> &mdash; {seats} seat(s) at {unit} per seat.<br>
Amount {amount} &middot; VAT {vat} &middot; <b>Total due {total}</b></p>
<p>The proforma is attached and is also on your Documents shelf in the portal.
Payment details are on the proforma. Your seats are activated once we confirm payment.</p>
<p>&mdash; CloudERP.One Academy &middot; Xlevel Retail Systems Ltd</p>""".format(
\t\t\t\ttitle=frappe.utils.escape_html(t.title), seats=seats, unit=fmt(unit),
\t\t\t\tamount=fmt(amount), vat=fmt(vat), total=fmt(amount + vat),
\t\t\t),
\t\t\tattachments=[{"fname": fname, "fcontent": pdf}],
\t\t)
\texcept Exception:
\t\tfrappe.log_error(frappe.get_traceback(), "duty_board academy proforma email")
\ttry:
\t\t_post(room, _("🧾 Seat request raised: {0} — {1} seat(s). Proforma {2} is on your Documents shelf.").format(
\t\t\tt.title, seats, order.name))
\texcept Exception:
\t\tpass
\ttry:
\t\tfrom duty_board.api import _notify_user

\t\tif _approver():
\t\t\t_notify_user(_approver(), _("🧾 Academy seat request"),
\t\t\t\t_("{0} — {1} seats · {2}").format(room.customer or room.name, seats, fmt(amount + vat)))
\texcept Exception:
\t\tpass
\treturn {"order": order.name, "total": order.total}


@frappe.whitelist()
def academy_my_orders():
\troom = _room_admin()
\treturn frappe.get_all(
\t\t"Duty Academy Order",
\t\tfilters={"room": room.name},
\t\tfields=["name", "track_title", "seats", "total", "status", "requested_on", "decline_reason"],
\t\torder_by="creation desc", limit_page_length=25,
\t)


# ---------------- staff face ----------------


@frappe.whitelist()
def orders(status=None):
\t_staff_only()
\tfilters = {"status": status} if status else {}
\trows = frappe.get_all(
\t\t"Duty Academy Order", filters=filters,
\t\tfields=["name", "room", "track", "track_title", "seats", "unit_price",
\t\t\t\t"amount", "vat", "total", "status", "requested_by", "requested_on",
\t\t\t\t"payment_ref", "entitlement"],
\t\torder_by="creation desc", limit_page_length=80,
\t)
\tfor r in rows:
\t\tr["customer"] = frappe.db.get_value("Client Room", r.room, "customer") or r.room
\treturn rows


@frappe.whitelist()
def order_approve(name, payment_ref=None, expires_on=None):
\t"""Confirm payment and grant the seats. Deliberately manual."""
\t_staff_only()
\tfrom duty_board.client_room import _post

\to = frappe.get_doc("Duty Academy Order", name)
\tif o.status != "Requested":
\t\tfrappe.throw(_("This order is already {0}.").format(o.status))
\tif not (payment_ref or "").strip():
\t\tfrappe.throw(_("Record the payment reference — approval is the confirmation that money arrived."))
\tent = frappe.get_doc({
\t\t"doctype": "Duty Academy Entitlement",
\t\t"room": o.room, "track": o.track, "seats": o.seats,
\t\t"granted_on": today(), "expires_on": expires_on or None,
\t\t"status": "Active", "source_order": o.name,
\t}).insert(ignore_permissions=True)
\to.db_set({
\t\t"status": "Approved", "payment_ref": payment_ref,
\t\t"approved_by": frappe.session.user, "approved_on": now_datetime(),
\t\t"entitlement": ent.name,
\t}, update_modified=False)
\tfrappe.db.commit()
\troom = frappe.get_doc("Client Room", o.room)
\ttry:
\t\t_post(room, _("✅ Seats activated: {0} — {1} seat(s). Your administrator can now assign them.").format(
\t\t\to.track_title, o.seats))
\texcept Exception:
\t\tpass
\ttry:
\t\tfrappe.sendmail(
\t\t\trecipients=[o.requested_by],
\t\t\tsubject=_("Seats activated — {0}").format(o.track_title),
\t\t\tmessage="""<p>Payment received, thank you.</p>
<p><b>{title}</b> &mdash; {seats} seat(s) are now active{exp}.</p>
<p>Open the portal, go to Training, and assign them to your colleagues.</p>
<p>&mdash; CloudERP.One Academy &middot; Xlevel Retail Systems Ltd</p>""".format(
\t\t\t\ttitle=frappe.utils.escape_html(o.track_title), seats=o.seats,
\t\t\t\texp=(" until %s" % frappe.utils.format_date(expires_on, "d MMMM yyyy")) if expires_on else "",
\t\t\t),
\t\t)
\texcept Exception:
\t\tfrappe.log_error(frappe.get_traceback(), "duty_board academy approval email")
\treturn {"order": o.name, "entitlement": ent.name}


@frappe.whitelist()
def order_decline(name, reason=None):
\t_staff_only()
\to = frappe.get_doc("Duty Academy Order", name)
\tif o.status != "Requested":
\t\tfrappe.throw(_("This order is already {0}.").format(o.status))
\to.db_set({"status": "Declined", "decline_reason": reason,
\t\t\t  "approved_by": frappe.session.user, "approved_on": now_datetime()},
\t\t\t update_modified=False)
\tfrappe.db.commit()
\treturn {"order": o.name}
'''


# --- client_room.py: entitlement-aware track visibility + seat gate --------
TFR_OLD = '''\ttracks = [t for t in tracks if (t.product or "").strip().lower() in prods]'''

TFR_NEW = '''\ttracks = _visible_tracks(room, tracks, prods)'''

VIS_OLD = '''def _tracks_for_room(room, user):'''

VIS_NEW = '''def _visible_tracks(room, tracks, prods):
\t"""Included tracks come with the room's products, as they always have.
\tPaid tracks appear only where seats have actually been bought."""
\tfrom duty_board.academy import entitlement_for

\tout = []
\tfor t in tracks:
\t\tif (t.get("access") or "Included") == "Paid":
\t\t\tif entitlement_for(room.name, t.name)["seats"]:
\t\t\t\tout.append(t)
\t\t\tcontinue
\t\tif (t.product or "").strip().lower() in prods:
\t\t\tout.append(t)
\treturn out


def _tracks_for_room(room, user):'''

TFF_OLD = '''\t\tfields=["name", "title", "product", "description"],
\t\torder_by="product asc, title asc",
\t)'''

TFF_NEW = '''\t\tfields=["name", "title", "product", "description", "access"],
\t\torder_by="product asc, title asc",
\t)'''

# seat consumption on the client administrator's bulk assign
ASSIGN_OLD = '''\tif not mods:
\t\tfrappe.throw(_("That track has no courses yet."))
\tcreated, existing = 0, 0'''

ASSIGN_NEW = '''\tif not mods:
\t\tfrappe.throw(_("That track has no courses yet."))
\tfrom duty_board.academy import seat_gate

\tfresh = [
\t\tu for u in users
\t\tif not frappe.db.exists(
\t\t\t"Duty Training Record", {"room": room.name, "module": mods[0], "trainee": u}
\t\t)
\t]
\tseat_gate(room.name, track, len(fresh))
\tcreated, existing = 0, 0'''

# seat consumption when a learner starts a track themselves
PURSUE_OLD = '''def client_pursue_track(track):'''
PURSUE_NEW = '''def client_pursue_track(track):
\t_pursue_seat_gate(track)'''

PGATE_OLD = '''@frappe.whitelist()
def client_pursue_track(track):'''
PGATE_NEW = '''def _pursue_seat_gate(track):
\t"""A learner starting a paid track burns a seat too — otherwise the
\tadministrator's careful count is undone from the other side."""
\tfrom duty_board.academy import seat_gate, seats_used

\troom = _client_room()
\tmods = frappe.get_all(
\t\t"Duty Certification Track Module", filters={"parent": track}, pluck="module"
\t)
\tif not mods:
\t\treturn
\talready = frappe.db.exists(
\t\t"Duty Training Record",
\t\t{"room": room.name, "module": ["in", mods], "trainee": frappe.session.user},
\t)
\tseat_gate(room.name, track, 0 if already else 1)


@frappe.whitelist()
def client_pursue_track(track):'''


# --- portal: catalogue inside the admin panel ------------------------------
P_BTN_OLD = '''\t\t\t\t\t\t<button id="admassign">\uFF0B Assign training</button>'''
P_BTN_NEW = '''\t\t\t\t\t\t<button id="admcat" style="background:#E2E8E5;color:#2A3833">Catalogue</button>
\t\t\t\t\t\t<button id="admassign">\uFF0B Assign training</button>'''

P_HOOK_OLD = '''\t\t\tdocument.getElementById("admassign").onclick = openAssign;'''
P_HOOK_NEW = '''\t\t\tdocument.getElementById("admassign").onclick = openAssign;
\t\t\tdocument.getElementById("admcat").onclick = openCatalogue;'''

P_CAT_OLD = '''function openAssign() {'''
P_CAT_NEW = '''function openCatalogue() {
\tconst host = document.getElementById("adminhost");
\tconst money = (v) => "\u20A6" + Number(v || 0).toLocaleString();
\tapi("academy_catalogue")
\t\t.then((rows) => {
\t\t\thost.innerHTML = `
\t\t\t\t<div class="admwrap">
\t\t\t\t\t<div class="admhead"><div><b>Certification catalogue</b><span class="muted"> \u00b7 what your organisation can train on</span></div>
\t\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="loadAdminTraining()">Back</button></div>
\t\t\t\t\t${rows.length ? rows.map((r) => `
\t\t\t\t\t<div class="catrow">
\t\t\t\t\t\t<div class="cattop">
\t\t\t\t\t\t\t<b>${esc(r.title)}</b>
\t\t\t\t\t\t\t<span class="cattag ${r.access === "Paid" ? "paid" : "inc"}">${r.access === "Paid" ? money(r.seat_price) + " per seat" : "Included"}</span>
\t\t\t\t\t\t</div>
\t\t\t\t\t\t<div class="muted" style="font-size:12px">${esc(r.product || "")} \u00b7 ${r.courses} course${r.courses === 1 ? "" : "s"}</div>
\t\t\t\t\t\t${r.description ? `<div class="catdesc">${esc(r.description)}</div>` : ""}
\t\t\t\t\t\t${r.access === "Paid"
\t\t\t\t\t\t\t? (r.pending
\t\t\t\t\t\t\t\t? `<div class="catnote">Request for ${r.pending_seats} seat(s) received \u2014 we will confirm once payment is processed.</div>`
\t\t\t\t\t\t\t\t: (r.seats
\t\t\t\t\t\t\t\t\t? `<div class="catnote ok">${r.seats_left} of ${r.seats} seats available${r.expires_on ? " \u00b7 until " + esc(String(r.expires_on).slice(0, 10)) : ""}</div>
\t\t\t\t\t\t\t\t\t   <a class="catreq" data-t="${esc(r.track)}" data-n="${esc(r.title)}" data-p="${r.seat_price}">Request more seats</a>`
\t\t\t\t\t\t\t\t\t: `<a class="catreq" data-t="${esc(r.track)}" data-n="${esc(r.title)}" data-p="${r.seat_price}">Request seats</a>`))
\t\t\t\t\t\t\t: ""}
\t\t\t\t\t</div>`).join("")
\t\t\t\t\t\t: `<span class="muted">No certification tracks are available yet.</span>`}
\t\t\t\t</div>`;
\t\t\thost.querySelectorAll(".catreq").forEach((a) =>
\t\t\t\ta.addEventListener("click", () => requestSeats(a.getAttribute("data-t"), a.getAttribute("data-n"), a.getAttribute("data-p"))));
\t\t})
\t\t.catch(fail);
}
function requestSeats(track, title, price) {
\tconst host = document.getElementById("adminhost");
\tconst money = (v) => "\u20A6" + Number(v || 0).toLocaleString();
\thost.innerHTML = `
\t\t<div class="admwrap">
\t\t\t<div class="admhead"><div><b>Request seats \u2014 ${esc(title)}</b></div>
\t\t\t\t<button style="background:#E2E8E5;color:#2A3833" onclick="openCatalogue()">Cancel</button></div>
\t\t\t<div class="admfield"><label>How many seats?</label>
\t\t\t\t<input type="number" id="seatn" min="1" value="5" style="max-width:140px"></div>
\t\t\t<div class="admfield"><label>Anything we should know <span class="muted">(optional)</span></label>
\t\t\t\t<input type="text" id="seatnote" placeholder="e.g. for the Ikeja branch team"></div>
\t\t\t<div class="catnote" id="seatsum">${money(price)} per seat \u00b7 VAT added on the proforma</div>
\t\t\t<button id="seatgo">Request seats</button>
\t\t\t<p class="muted" style="font-size:11.5px;margin-top:10px">You will receive a proforma invoice by email with our bank details. Seats are activated once we confirm your payment.</p>
\t\t</div>`;
\tconst upd = () => {
\t\tconst n = parseInt(document.getElementById("seatn").value, 10) || 0;
\t\tdocument.getElementById("seatsum").textContent =
\t\t\t`${n} \u00d7 ${money(price)} = ${money(n * Number(price))} plus VAT`;
\t};
\tdocument.getElementById("seatn").addEventListener("input", upd);
\tupd();
\tdocument.getElementById("seatgo").onclick = () => {
\t\tconst n = parseInt(document.getElementById("seatn").value, 10) || 0;
\t\tif (n < 1) return alert("How many seats do you need?");
\t\tdocument.getElementById("seatgo").disabled = true;
\t\tapi("academy_request", { track: track, seats: n, note: document.getElementById("seatnote").value || null })
\t\t\t.then((r) => {
\t\t\t\thost.innerHTML = `<div class="admwrap"><div class="catnote ok">
\t\t\t\t\tRequest ${esc(r.order)} received. The proforma is on its way to your inbox and is filed under Documents.
\t\t\t\t\tWe will activate your seats once payment is confirmed.</div>
\t\t\t\t\t<button style="background:#E2E8E5;color:#2A3833;margin-top:12px" onclick="loadAdminTraining()">Back to team training</button></div>`;
\t\t\t})
\t\t\t.catch((e) => { document.getElementById("seatgo").disabled = false; fail(e); });
\t};
}
function openAssign() {'''

CSS2_OLD = '''\t/* ---- the reading room ---- */'''
CSS2_NEW = '''\t.catrow { border-top: 1px solid #F0F4F2; padding: 12px 0; }
\t.cattop { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; font-size: 14.5px; }
\t.cattag { margin-left: auto; font-size: 11.5px; font-weight: 700; border-radius: 99px; padding: 3px 10px; }
\t.cattag.inc { background: var(--brand-50); color: var(--brand-700); }
\t.cattag.paid { background: #FFF7E6; color: #8A5A0B; }
\t.catdesc { font-size: 12.5px; color: #4A5A55; line-height: 1.6; margin-top: 5px; }
\t.catnote { font-size: 12.5px; margin-top: 8px; background: #FFF7E6; border: 1px solid #F3E0B5;
\t\tcolor: #7A5312; border-radius: 9px; padding: 8px 12px; }
\t.catnote.ok { background: var(--brand-50); border-color: #CBE7DE; color: #0C4A43; }
\t.catreq { display: inline-block; margin-top: 8px; font-size: 12.5px; font-weight: 700;
\t\tcolor: var(--brand-700); cursor: pointer; }

\t/* ---- the reading room ---- */'''


# --- staff SPA: orders queue ----------------------------------------------
JS_OLD = '''\t\td.set_primary_action(`\\u{1F465} ${__("Cohorts")}`, () => { d.hide(); this.cohorts_dialog(x); });'''
JS_NEW = '''\t\td.set_primary_action(`\\u{1F465} ${__("Cohorts")}`, () => { d.hide(); this.cohorts_dialog(x); });
\t\td.set_secondary_action_label(`\\u{1F9FE} ${__("Seat orders")}`);
\t\td.set_secondary_action(() => { d.hide(); this.academy_orders_dialog(); });'''

JS_DLG_OLD = '''\tcohorts_dialog(x) {'''
JS_DLG_NEW = '''\tacademy_orders_dialog() {
\t\tconst esc = frappe.utils.escape_html;
\t\tconst d = new frappe.ui.Dialog({ title: `\\u{1F9FE} ${__("Academy seat orders")}`, size: "extra-large" });
\t\tconst money = (v) => format_currency(v, "NGN");
\t\tconst load = () =>
\t\t\tfrappe.call({
\t\t\t\tmethod: "duty_board.academy.orders",
\t\t\t\tcallback: (r) => {
\t\t\t\t\tconst rows = r.message || [];
\t\t\t\t\t$(d.body).html(rows.length ? `
\t\t\t\t\t\t<table class="table table-sm" style="font-size:12px">
\t\t\t\t\t\t\t<tr><th>${__("Order")}</th><th>${__("Customer")}</th><th>${__("Track")}</th>
\t\t\t\t\t\t\t<th>${__("Seats")}</th><th>${__("Total")}</th><th>${__("Status")}</th><th></th></tr>
\t\t\t\t\t\t\t${rows.map((o) => `<tr>
\t\t\t\t\t\t\t\t<td>${esc(o.name)}</td><td>${esc(o.customer)}</td><td>${esc(o.track_title)}</td>
\t\t\t\t\t\t\t\t<td>${o.seats}</td><td>${money(o.total)}</td>
\t\t\t\t\t\t\t\t<td>${o.status === "Requested" ? `<b style="color:#B45309">${esc(o.status)}</b>` : esc(o.status)}</td>
\t\t\t\t\t\t\t\t<td>${o.status === "Requested"
\t\t\t\t\t\t\t\t\t? `<a class="duty-ao-ok" data-n="${esc(o.name)}">${__("Approve")}</a> \\u00b7 <a class="duty-ao-no" data-n="${esc(o.name)}">${__("Decline")}</a>`
\t\t\t\t\t\t\t\t\t: esc(o.payment_ref || "")}</td></tr>`).join("")}
\t\t\t\t\t\t</table>
\t\t\t\t\t\t<p class="text-muted" style="font-size:11.5px">${__("Approving is the act that confirms money arrived. Seats activate immediately and the client is emailed.")}</p>`
\t\t\t\t\t\t: `<div class="text-muted">${__("No seat orders yet.")}</div>`);
\t\t\t\t\t$(d.body).find(".duty-ao-ok").on("click", (e) => {
\t\t\t\t\t\tconst n = $(e.currentTarget).data("n");
\t\t\t\t\t\tconst ad = new frappe.ui.Dialog({
\t\t\t\t\t\t\ttitle: __("Approve {0}", [n]),
\t\t\t\t\t\t\tfields: [
\t\t\t\t\t\t\t\t{ fieldname: "payment_ref", fieldtype: "Data", label: __("Payment reference"), reqd: 1,
\t\t\t\t\t\t\t\t  description: __("Bank reference or receipt number — this is your record that payment landed.") },
\t\t\t\t\t\t\t\t{ fieldname: "expires_on", fieldtype: "Date", label: __("Seats expire on (optional)") },
\t\t\t\t\t\t\t],
\t\t\t\t\t\t\tprimary_action_label: __("Activate seats"),
\t\t\t\t\t\t\tprimary_action: (v) => {
\t\t\t\t\t\t\t\tad.hide();
\t\t\t\t\t\t\t\tfrappe.call({
\t\t\t\t\t\t\t\t\tmethod: "duty_board.academy.order_approve",
\t\t\t\t\t\t\t\t\targs: { name: n, payment_ref: v.payment_ref, expires_on: v.expires_on },
\t\t\t\t\t\t\t\t\tcallback: () => { frappe.show_alert({ message: __("Seats activated"), indicator: "green" }); load(); },
\t\t\t\t\t\t\t\t});
\t\t\t\t\t\t\t},
\t\t\t\t\t\t});
\t\t\t\t\t\tad.show();
\t\t\t\t\t});
\t\t\t\t\t$(d.body).find(".duty-ao-no").on("click", (e) => {
\t\t\t\t\t\tconst n = $(e.currentTarget).data("n");
\t\t\t\t\t\tfrappe.prompt(
\t\t\t\t\t\t\t{ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") },
\t\t\t\t\t\t\t(v) => frappe.call({
\t\t\t\t\t\t\t\tmethod: "duty_board.academy.order_decline",
\t\t\t\t\t\t\t\targs: { name: n, reason: v.reason },
\t\t\t\t\t\t\t\tcallback: load,
\t\t\t\t\t\t\t}),
\t\t\t\t\t\t\t__("Decline {0}", [n]), __("Decline")
\t\t\t\t\t\t);
\t\t\t\t\t});
\t\t\t\t},
\t\t\t});
\t\tload();
\t\td.show();
\t}

\tcohorts_dialog(x) {'''


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


def write_doctype(root, folder, spec, cls):
    d = os.path.join(root, DT_DIR, folder)
    if not os.path.isdir(d):
        os.makedirs(d)
    for fname, body in (
        ("__init__.py", ""),
        (folder + ".json", json.dumps(spec, indent=1) + "\n"),
        (folder + ".py", CTRL.format(cls=cls)),
    ):
        p = os.path.join(d, fname)
        if not os.path.exists(p):
            with io.open(p, "w", encoding="utf-8") as f:
                f.write(body)


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, PORTAL, JS):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if os.path.exists(os.path.join(root, ACAD)):
        print("Already applied. Nothing to do.")
        return
    if '"3.211.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.211.0.")

    edits = [
        (CR, VIS_OLD, VIS_NEW, "_visible_tracks"),
        (CR, TFR_OLD, TFR_NEW, "track filter uses entitlement"),
        (CR, TFF_OLD, TFF_NEW, "track fields include access"),
        (CR, ASSIGN_OLD, ASSIGN_NEW, "admin assign seat gate"),
        (CR, PGATE_OLD, PGATE_NEW, "_pursue_seat_gate"),
        (CR, PURSUE_OLD, PURSUE_NEW, "pursue calls the gate"),
        (PORTAL, P_BTN_OLD, P_BTN_NEW, "catalogue button"),
        (PORTAL, P_HOOK_OLD, P_HOOK_NEW, "catalogue hook"),
        (PORTAL, P_CAT_OLD, P_CAT_NEW, "catalogue + request"),
        (PORTAL, CSS2_OLD, CSS2_NEW, "catalogue css"),
        (JS, JS_OLD, JS_NEW, "seat orders action"),
        (JS, JS_DLG_OLD, JS_DLG_NEW, "orders dialog"),
    ]

    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    write_doctype(root, "duty_academy_order", ORDER_JSON, "DutyAcademyOrder")
    write_doctype(root, "duty_academy_entitlement", ENT_JSON, "DutyAcademyEntitlement")
    print("  doctypes: Duty Academy Order + Entitlement")

    add_fields(os.path.join(root, DSDT), [
        {"fieldname": "academy_bank_details", "fieldtype": "Small Text", "label": "Academy Bank Details"},
        {"fieldname": "academy_approver", "fieldtype": "Data", "label": "Academy Approver"},
        {"fieldname": "academy_vat_rate", "fieldtype": "Float", "label": "Academy VAT %", "default": "7.5"},
    ])
    add_fields(os.path.join(root, TRKDT), [
        {"fieldname": "access", "fieldtype": "Select", "label": "Access",
         "options": "Included\nPaid", "default": "Included"},
        {"fieldname": "seat_price", "fieldtype": "Currency", "label": "Price per Seat"},
    ])
    print("  Duty Settings + Duty Certification Track fields")

    with io.open(os.path.join(root, ACAD), "w", encoding="utf-8") as f:
        f.write(ACADEMY_PY)
    print("  academy.py written")

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, PORTAL, JS):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  client_room.py: entitlement-aware visibility + seat gates")
    print("  portal.html: catalogue, seat request")
    print("  duty_board.js: seat orders queue")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.211.0"', '"3.212.0"'))
    print("wrote __init__.py -> 3.212.0")


if __name__ == "__main__":
    main()
