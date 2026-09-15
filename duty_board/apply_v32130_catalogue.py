#!/usr/bin/env python3
"""Duty Board v3.213.0 - THE WHOLE CATALOGUE, AND PAID SEATS BECOME ASSIGNABLE.

Two problems, one root.

v3.212.0's catalogue hid any track that was neither Paid nor matched to the
room's products, so a client whose products did not line up saw "No
certification tracks are available yet" and had nothing to browse or buy. A
catalogue that lists only what you already hold is not a catalogue.

The worse one, found while fixing it: client_training_admin_options filtered the
assign dialog by product alone. A Paid track bought with real money, whose
product is not among the room's ERP products, would never have appeared there.
We could have taken payment for seats the client then could not use.

Both now read one shared function, academy.track_catalogue, which returns every
published client track with this room's standing against it:

  included  - covered by their products; assign freely
  entitled  - a Paid track with live seats; assign until they run out
  offered   - not bought, or outside their products; visible with a price or a
              note, never assignable

The catalogue shows all three, assignable first, with Assign to staff beside
anything they may use and Request seats beside anything they may buy. The assign
dialog asks the same function for assignable rows only, so entitlement and
product membership can never disagree again. Assigning is entirely the client
administrator's to do; staff involvement is now only confirming payment.

Deploy: apply -> bench build --app duty_board -> clear-cache +
clear-website-cache -> restart. No schema. Anchored, idempotent.
Requires v3.212.1. Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
CR = "duty_board/client_room.py"
ACAD = "duty_board/academy.py"
PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv


CAT_OLD = '@frappe.whitelist()\ndef academy_catalogue():\n\t"""Every active client track, marked Included or Paid, with this room\'s\n\tseat position and any order already in flight."""\n\tfrom duty_board.client_room import _room_products\n\n\troom = _room_admin()\n\tprods = _room_products(room)\n\tout = []\n\tfor t in frappe.get_all(\n\t\t"Duty Certification Track",\n\t\tfilters={"active": 1, "audience": "Client"},\n\t\tfields=["name", "title", "product", "description", "access", "seat_price"],\n\t\torder_by="access asc, product asc, title asc",\n\t):\n\t\tn = frappe.db.count("Duty Certification Track Module", {"parent": t.name})\n\t\tif not n:\n\t\t\tcontinue\n\t\taccess = t.access or "Included"\n\t\tincluded = access != "Paid" and (t.product or "").strip().lower() in prods\n\t\tent = entitlement_for(room.name, t.name) if access == "Paid" else None\n\t\tused = seats_used(room.name, t.name) if access == "Paid" else 0\n\t\tpending = frappe.db.get_value(\n\t\t\t"Duty Academy Order",\n\t\t\t{"room": room.name, "track": t.name, "status": "Requested"},\n\t\t\t["name", "seats"], as_dict=True,\n\t\t)\n\t\tif access != "Paid" and not included:\n\t\t\tcontinue  # an included track outside their products is simply not theirs\n\t\tout.append({\n\t\t\t"track": t.name,\n\t\t\t"title": t.title,\n\t\t\t"product": t.product,\n\t\t\t"description": t.description,\n\t\t\t"courses": n,\n\t\t\t"access": access,\n\t\t\t"included": included,\n\t\t\t"seat_price": flt(t.seat_price),\n\t\t\t"seats": ent["seats"] if ent else None,\n\t\t\t"seats_used": used,\n\t\t\t"seats_left": max(ent["seats"] - used, 0) if ent else None,\n\t\t\t"expires_on": ent["expires_on"] if ent else None,\n\t\t\t"pending": pending.name if pending else None,\n\t\t\t"pending_seats": pending.seats if pending else None,\n\t\t})\n\treturn out\n\n\n'

CAT_NEW = 'def track_catalogue(room, assignable_only=False):\n\t"""Every PUBLISHED client track and this room\'s standing against it.\n\n\tThree states, and the catalogue shows all three, because a client should see\n\twhat exists rather than only what they already hold:\n\t  included  - covered by the products on their room; assign freely\n\t  entitled  - a Paid track with live seats; assign until the seats run out\n\t  offered   - not bought, or outside their products; visible with a price or\n\t              a note, never assignable\n\t"""\n\tfrom duty_board.client_room import _room_products\n\n\tprods = _room_products(room)\n\tout = []\n\tfor t in frappe.get_all(\n\t\t"Duty Certification Track",\n\t\tfilters={"active": 1, "audience": "Client"},\n\t\tfields=["name", "title", "product", "description", "access", "seat_price"],\n\t\torder_by="product asc, title asc",\n\t):\n\t\tn = frappe.db.count("Duty Certification Track Module", {"parent": t.name})\n\t\tif not n:\n\t\t\tcontinue\n\t\taccess = t.access or "Included"\n\t\tpaid = access == "Paid"\n\t\tincluded = not paid and (t.product or "").strip().lower() in prods\n\t\tent = entitlement_for(room.name, t.name) if paid else None\n\t\tused = seats_used(room.name, t.name) if paid else 0\n\t\tleft = max(ent["seats"] - used, 0) if ent else None\n\t\tassignable = included or bool(left)\n\t\tif assignable_only and not assignable:\n\t\t\tcontinue\n\t\tpending = frappe.db.get_value(\n\t\t\t"Duty Academy Order",\n\t\t\t{"room": room.name, "track": t.name, "status": "Requested"},\n\t\t\t["name", "seats"], as_dict=True,\n\t\t)\n\t\tout.append({\n\t\t\t"track": t.name,\n\t\t\t"name": t.name,\n\t\t\t"title": t.title,\n\t\t\t"product": t.product,\n\t\t\t"description": t.description,\n\t\t\t"courses": n,\n\t\t\t"modules": n,\n\t\t\t"access": access,\n\t\t\t"included": included,\n\t\t\t"assignable": assignable,\n\t\t\t"seat_price": flt(t.seat_price),\n\t\t\t"seats": ent["seats"] if ent else None,\n\t\t\t"seats_used": used,\n\t\t\t"seats_left": left,\n\t\t\t"expires_on": ent["expires_on"] if ent else None,\n\t\t\t"pending": pending.name if pending else None,\n\t\t\t"pending_seats": pending.seats if pending else None,\n\t\t})\n\tout.sort(key=lambda r: (not r["assignable"], r["access"] != "Included", r["title"]))\n\treturn out\n\n\n@frappe.whitelist()\ndef academy_catalogue():\n\troom = _room_admin()\n\treturn track_catalogue(room)\n\n\n'

OPT_OLD = '\t"""Who can be assigned, and what to. Tracks are filtered to the room\'s\n\tproducts by the same rule the staff assign dialog uses."""\n\troom = _require_room_admin()\n\tprods = _room_products(room)\n\ttracks = []\n\tfor t in frappe.get_all(\n\t\t"Duty Certification Track",\n\t\tfilters={"active": 1, "audience": "Client"},\n\t\tfields=["name", "title", "product"],\n\t\torder_by="product asc, title asc",\n\t):\n\t\tif (t.product or "").strip().lower() not in prods:\n\t\t\tcontinue\n\t\tn = frappe.db.count("Duty Certification Track Module", {"parent": t.name})\n\t\tif n:\n\t\t\ttracks.append({"name": t.name, "title": t.title, "product": t.product, "modules": n})'

OPT_NEW = '\t"""Who can be assigned, and what to. Assignable means covered by the room\'s\n\tproducts OR carrying live purchased seats - one shared reading with the\n\tcatalogue, so a bought track can never be missing from this list."""\n\troom = _require_room_admin()\n\tfrom duty_board.academy import track_catalogue\n\n\ttracks = track_catalogue(room, assignable_only=True)'

P_OLD = '\t\t\t\t\t${rows.length ? rows.map((r) => `\n\t\t\t\t\t<div class="catrow">\n\t\t\t\t\t\t<div class="cattop">\n\t\t\t\t\t\t\t<b>${esc(r.title)}</b>\n\t\t\t\t\t\t\t<span class="cattag ${r.access === "Paid" ? "paid" : "inc"}">${r.access === "Paid" ? money(r.seat_price) + " per seat" : "Included"}</span>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t\t<div class="muted" style="font-size:12px">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"}</div>\n\t\t\t\t\t\t${r.description ? `<div class="catdesc">${esc(r.description)}</div>` : ""}\n\t\t\t\t\t\t${r.access === "Paid"\n\t\t\t\t\t\t\t? (r.pending\n\t\t\t\t\t\t\t\t? `<div class="catnote">Request for ${r.pending_seats} seat(s) received — we will confirm once payment is processed.</div>`\n\t\t\t\t\t\t\t\t: (r.seats\n\t\t\t\t\t\t\t\t\t? `<div class="catnote ok">${r.seats_left} of ${r.seats} seats available${r.expires_on ? " · until " + esc(String(r.expires_on).slice(0, 10)) : ""}</div>\n\t\t\t\t\t\t\t\t\t   <a class="catreq" data-t="${esc(r.track)}" data-n="${esc(r.title)}" data-p="${r.seat_price}">Request more seats</a>`\n\t\t\t\t\t\t\t\t\t: `<a class="catreq" data-t="${esc(r.track)}" data-n="${esc(r.title)}" data-p="${r.seat_price}">Request seats</a>`))\n\t\t\t\t\t\t\t: ""}\n\t\t\t\t\t</div>`).join("")\n\t\t\t\t\t\t: `<span class="muted">No certification tracks are available yet.</span>`}'

P_NEW = '\t\t\t\t\t${rows.length ? rows.map((r) => `\n\t\t\t\t\t<div class="catrow">\n\t\t\t\t\t\t<div class="cattop">\n\t\t\t\t\t\t\t<b>${esc(r.title)}</b>\n\t\t\t\t\t\t\t<span class="cattag ${r.included ? "inc" : r.seats_left ? "own" : "paid"}">${\n\t\t\t\t\t\t\t\tr.included ? "Included" : r.seats_left ? r.seats_left + " seat" + (r.seats_left === 1 ? "" : "s") + " left" : r.access === "Paid" ? money(r.seat_price) + " per seat" : "Not in your subscription"}</span>\n\t\t\t\t\t\t</div>\n\t\t\t\t\t\t<div class="muted" style="font-size:12px">${esc(r.product || "")} · ${r.courses} course${r.courses === 1 ? "" : "s"}</div>\n\t\t\t\t\t\t${r.description ? `<div class="catdesc">${esc(r.description)}</div>` : ""}\n\t\t\t\t\t\t${r.pending\n\t\t\t\t\t\t\t? `<div class="catnote">Request for ${r.pending_seats} seat(s) received — we will confirm once payment is processed.</div>`\n\t\t\t\t\t\t\t: r.seats\n\t\t\t\t\t\t\t\t? `<div class="catnote ok">${r.seats_left} of ${r.seats} seats available${r.expires_on ? " · until " + esc(String(r.expires_on).slice(0, 10)) : ""}</div>`\n\t\t\t\t\t\t\t\t: (!r.included && r.access !== "Paid")\n\t\t\t\t\t\t\t\t\t? `<div class="catnote">This track comes with a product you are not subscribed to. Ask us about adding it.</div>`\n\t\t\t\t\t\t\t\t\t: ""}\n\t\t\t\t\t\t<div class="catacts">\n\t\t\t\t\t\t\t${r.assignable ? `<a class="catasg" data-t="${esc(r.track)}">Assign to staff</a>` : ""}\n\t\t\t\t\t\t\t${r.access === "Paid" && !r.pending ? `<a class="catreq" data-t="${esc(r.track)}" data-n="${esc(r.title)}" data-p="${r.seat_price}">${r.seats ? "Request more seats" : "Request seats"}</a>` : ""}\n\t\t\t\t\t\t</div>\n\t\t\t\t\t</div>`).join("")\n\t\t\t\t\t\t: `<span class="muted">No certification tracks have been published yet.</span>`}'

H_OLD = '\t\t\thost.querySelectorAll(".catreq").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => requestSeats(a.getAttribute("data-t"), a.getAttribute("data-n"), a.getAttribute("data-p"))));'

H_NEW = '\t\t\thost.querySelectorAll(".catreq").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => requestSeats(a.getAttribute("data-t"), a.getAttribute("data-n"), a.getAttribute("data-p"))));\n\t\t\thost.querySelectorAll(".catasg").forEach((a) =>\n\t\t\t\ta.addEventListener("click", () => openAssign(a.getAttribute("data-t"))));'

A_OLD = 'function openAssign() {'

A_NEW = 'function openAssign(preselect) {'

A2_OLD = '\t\t\t\t\t\t<select id="admtrack">${o.tracks.map((t) => `<option value="${esc(t.name)}">${esc(t.title)} · ${t.modules} course${t.modules === 1 ? "" : "s"}</option>`).join("")}</select></div>'

A2_NEW = '\t\t\t\t\t\t<select id="admtrack">${o.tracks.map((t) => `<option value="${esc(t.name)}"${t.name === preselect ? " selected" : ""}>${esc(t.title)} · ${t.modules} course${t.modules === 1 ? "" : "s"}${t.seats_left ? ` · ${t.seats_left} seat${t.seats_left === 1 ? "" : "s"} left` : ""}</option>`).join("")}</select></div>'

CSS_OLD = '\t.cattag.paid { background: #FFF7E6; color: #8A5A0B; }'

CSS_NEW = '\t.cattag.paid { background: #FFF7E6; color: #8A5A0B; }\n\t.cattag.own { background: #E8F3EF; color: #0C4A43; }\n\t.catacts { display: flex; gap: 16px; margin-top: 8px; }\n\t.catasg { font-size: 12.5px; font-weight: 700; color: var(--brand-700); cursor: pointer; }'



def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, CR, ACAD, PORTAL):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def track_catalogue(" in files[ACAD]:
        print("Already applied. Nothing to do.")
        return
    if '"3.212.1"' not in files[INIT]:
        sys.exit("ABORT: not at v3.212.1.")

    edits = [
        (ACAD, CAT_OLD, CAT_NEW, "track_catalogue"),
        (CR, OPT_OLD, OPT_NEW, "assign options use the catalogue"),
        (PORTAL, P_OLD, P_NEW, "catalogue rows"),
        (PORTAL, H_OLD, H_NEW, "assign-from-catalogue hook"),
        (PORTAL, A_OLD, A_NEW, "openAssign preselect arg"),
        (PORTAL, A2_OLD, A2_NEW, "track select preselect + seats"),
        (PORTAL, CSS_OLD, CSS_NEW, "catalogue css"),
    ]

    problems = []
    for f, old, _new, label in edits:
        n = files[f].count(old)
        if n != 1:
            problems.append("  [%d != 1] %s" % (n, label))
    if problems:
        print("ABORT - anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)
    print("All %d anchors matched exactly once." % len(edits))

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    for f, old, new, _label in edits:
        files[f] = files[f].replace(old, new, 1)
    for p in (CR, ACAD, PORTAL):
        with io.open(os.path.join(root, p), "w", encoding="utf-8") as f:
            f.write(files[p])
    print("  academy.py: track_catalogue - three states, one reading")
    print("  client_room.py: assign dialog reads the same function")
    print("  portal.html: full catalogue + assign from catalogue")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.212.1"', '"3.213.0"'))
    print("wrote __init__.py -> 3.213.0")


if __name__ == "__main__":
    main()
