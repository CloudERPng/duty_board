#!/usr/bin/env python3
"""Duty Board v3.222.0 - THE SHOP WINDOW.

Everything in the academy sits behind a login inside a client room, so there
was no link a salesperson could send, no page a prospective buyer could read,
and no way to encounter the catalogue without already being a customer with an
account. Fifteen planned tracks with nowhere to point anyone is a catalogue
with no front door.

  /academy         every published client track as a card - price or Free,
                   course count, study time, description
  /academy?track=  the full page: what it covers, who it is for, what staff
                   will be able to do, the ordered course list with study time,
                   how it is assessed, and a sample chapter

  Duty Lesson: +is_sample. Tick one chapter per track and it is readable in
  full on the public page. This is the answer to the only real objection a
  buyer has behind a paywall - is the writing any good - and it is answered by
  showing them, not by claiming it.

  /verify gains one line pointing at the catalogue. That page is seen by
  employers and recruiters checking somebody's credential: an audience that by
  definition values verified training and arrived voluntarily.

Entitlement never appears here, because there is no room to have entitlement
in. Prices and content, nothing else.

Deploy: apply -> bench migrate (one field) -> bench build --app duty_board ->
clear-cache + clear-website-cache -> restart. Anchored, idempotent.
Requires v3.221.1.
"""

import io
import json as _json
import os
import sys

INIT = "duty_board/__init__.py"
VERIFY = "duty_board/www/verify.html"
LSDT = "duty_board/duty_board/doctype/duty_lesson/duty_lesson.json"
WWW = "duty_board/www"
CHECK_ONLY = "--check" in sys.argv


ACADEMY_PY = 'import frappe\n\nno_cache = 1\n\n\ndef get_context(context):\n\t"""The shop window.\n\n\tEverything else in the academy sits behind a login inside a client room, so\n\tuntil now there was no link a salesperson could send and no way for anybody\n\tto encounter the catalogue without already being a customer with an account.\n\tThis page is that link.\n\n\tIt shows what exists and what it costs. It never shows entitlement, because\n\tthere is no room to have entitlement in — and it never shows lesson content\n\texcept a chapter deliberately marked as a sample."""\n\tcontext.no_cache = 1\n\tslug = (frappe.form_dict.get("track") or "").strip()\n\tcontext.track = None\n\tcontext.tracks = []\n\n\trows = frappe.get_all(\n\t\t"Duty Certification Track",\n\t\tfilters={"active": 1, "audience": "Client"},\n\t\tfields=["name", "title", "product", "description", "access", "seat_price",\n\t\t\t\t"who_for", "outcomes"],\n\t\torder_by="product asc, title asc",\n\t)\n\tfor t in rows:\n\t\tmods = frappe.get_all(\n\t\t\t"Duty Certification Track Module", filters={"parent": t.name},\n\t\t\tfields=["module"], order_by="idx asc",\n\t\t)\n\t\tif not mods:\n\t\t\tcontinue\n\t\tcourses, minutes, sample = [], 0, None\n\t\tfor m in mods:\n\t\t\ttitle = frappe.db.get_value("Duty Training Module", m.module, "title") or m.module\n\t\t\tmins = 0\n\t\t\tfor l in frappe.get_all(\n\t\t\t\t"Duty Lesson", filters={"module": m.module},\n\t\t\t\tfields=["name", "title", "est_minutes", "content", "is_sample"],\n\t\t\t\torder_by="sort_order asc, creation asc",\n\t\t\t):\n\t\t\t\tmins += frappe.utils.cint(l.est_minutes) or 5\n\t\t\t\tif not sample and frappe.utils.cint(l.is_sample):\n\t\t\t\t\tsample = {\n\t\t\t\t\t\t"course": title, "title": l.title,\n\t\t\t\t\t\t"html": frappe.utils.sanitize_html(l.content or ""),\n\t\t\t\t\t}\n\t\t\tminutes += mins\n\t\t\tcourses.append({"title": title, "minutes": mins})\n\t\tt.courses = courses\n\t\tt.minutes = minutes\n\t\tt.hours = round(minutes / 60.0, 1) if minutes >= 60 else None\n\t\tt.sample = sample\n\t\tt.paid = (t.access or "Included") == "Paid"\n\t\tt.price = frappe.utils.fmt_money(t.seat_price, currency="NGN") if t.paid else None\n\t\tcontext.tracks.append(t)\n\n\tif slug:\n\t\tcontext.track = next((x for x in context.tracks if x.name == slug), None)\n\treturn context\n'

ACADEMY_HTML = '<!DOCTYPE html>\n<html><head>\n<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{% if track %}{{ track.title }} — {% endif %}CloudERP.One Academy</title>\n<meta name="description" content="Certification tracks for retail, distribution and finance teams — written from live operations, assessed under proctored conditions, verifiable by serial.">\n<style>\n\tbody { font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif; background: #F4F7F6; color: #16211F; margin: 0; }\n\t.top { background: linear-gradient(120deg,#0A473F,#0F5C55 55%,#146B62); color: #fff; padding: 18px 22px; font-weight: 800; }\n\t.top a { color: #fff; text-decoration: none; }\n\t.wrap { max-width: 1040px; margin: 34px auto 60px; padding: 0 18px; }\n\t.lede { font-size: 17px; line-height: 1.65; color: #33423E; max-width: 640px; margin-bottom: 30px; }\n\t.lede h1 { font-size: 30px; line-height: 1.2; margin: 0 0 12px; color: #0A473F; }\n\t.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }\n\t.card { background: #fff; border: 1px solid #E7ECEA; border-radius: 16px; padding: 20px; display: flex; flex-direction: column; text-decoration: none; color: inherit; }\n\t.card:hover { border-color: #0F5C55; }\n\t.tag { align-self: flex-start; font-size: 12.5px; font-weight: 700; border-radius: 99px; padding: 4px 12px; margin-bottom: 10px; }\n\t.tag.free { background: #E4F3EC; color: #0C6B4F; }\n\t.tag.paid { background: #FFF7E6; color: #8A5A0B; }\n\t.name { font-size: 19px; font-weight: 700; line-height: 1.28; }\n\t.meta { font-size: 13px; color: #6B7C77; margin-top: 6px; }\n\t.blurb { font-size: 14px; line-height: 1.6; color: #4A5A55; margin-top: 11px; }\n\t.more { font-size: 13px; font-weight: 700; color: #0F5C55; margin-top: auto; padding-top: 14px; }\n\t.detail { background: #fff; border: 1px solid #E7ECEA; border-radius: 16px; padding: 30px; }\n\t.detail h1 { font-size: 30px; line-height: 1.2; margin: 6px 0 4px; color: #0A473F; }\n\t.sec { margin-top: 24px; font-size: 15.5px; line-height: 1.7; }\n\t.sec b { display: block; font-size: 11.5px; letter-spacing: 1.5px; text-transform: uppercase; color: #0F5C55; margin-bottom: 6px; }\n\t.sec p { margin: 0; }\n\tol.courses { margin: 6px 0 0; padding-left: 22px; font-size: 15px; line-height: 1.8; }\n\t.sample { margin-top: 26px; border-top: 2px solid #E7ECEA; padding-top: 22px; }\n\t.sample .body { font-family: Georgia, "Times New Roman", serif; font-size: 16.5px; line-height: 1.75; color: #16211F; max-width: 660px; }\n\t.sample .body blockquote { border-left: 3px solid #CBE7DE; margin: 16px 0; padding: 2px 0 2px 16px; color: #33423E; }\n\t.cta { margin-top: 30px; background: #F4F7F6; border-radius: 12px; padding: 18px 20px; font-size: 15px; line-height: 1.65; }\n\t.back { font-size: 13.5px; font-weight: 700; color: #0F5C55; text-decoration: none; }\n\t.foot { margin-top: 40px; font-size: 12.5px; color: #93A19C; line-height: 1.7; }\n\t@media (max-width: 900px) { .grid { grid-template-columns: repeat(2, 1fr); } }\n\t@media (max-width: 620px) { .grid { grid-template-columns: 1fr; } .detail { padding: 22px; } }\n</style></head><body>\n<div class="top"><a href="/academy">CloudERP.One Academy</a></div>\n<div class="wrap">\n{% if track %}\n\t<a class="back" href="/academy">&larr; All certifications</a>\n\t<div class="detail" style="margin-top:12px">\n\t\t<span class="tag {{ \'paid\' if track.paid else \'free\' }}">{{ track.price + \' per seat\' if track.paid else \'Free\' }}</span>\n\t\t<h1>{{ track.title }}</h1>\n\t\t<div class="meta">{{ track.product }} · {{ track.courses|length }} course{{ \'\' if track.courses|length == 1 else \'s\' }}{% if track.hours %} · about {{ track.hours }} hours of study{% endif %}</div>\n\t\t{% if track.description %}<div class="sec"><b>What this covers</b><p>{{ track.description }}</p></div>{% endif %}\n\t\t{% if track.who_for %}<div class="sec"><b>Who it is for</b><p>{{ track.who_for }}</p></div>{% endif %}\n\t\t{% if track.outcomes %}<div class="sec"><b>What your staff will be able to do</b><p>{{ track.outcomes }}</p></div>{% endif %}\n\t\t<div class="sec"><b>Courses</b><ol class="courses">\n\t\t\t{% for c in track.courses %}<li>{{ c.title }}{% if c.minutes %} <span style="color:#6B7C77">· {{ c.minutes }} min</span>{% endif %}</li>{% endfor %}\n\t\t</ol></div>\n\t\t<div class="sec"><b>How it is assessed</b><p>Each course ends with a timed, proctored assessment drawn at random from a larger question bank. Passing every course earns a certificate carrying a serial anyone can <a href="/verify">verify</a>. Certificates do not expire.</p></div>\n\t\t{% if track.sample %}\n\t\t<div class="sample">\n\t\t\t<div class="sec" style="margin-top:0"><b>A sample chapter</b><p style="color:#6B7C77;font-size:14px">From {{ track.sample.course }} — read it and judge the writing for yourself.</p></div>\n\t\t\t<h2 style="font-size:22px;margin:18px 0 12px">{{ track.sample.title }}</h2>\n\t\t\t<div class="body">{{ track.sample.html }}</div>\n\t\t</div>\n\t\t{% endif %}\n\t\t<div class="cta"><b>Interested?</b> Training is delivered through your CloudERP.One portal. Speak to Xlevel Retail Systems and we will set your organisation up — your administrator then invites staff and assigns courses themselves.</div>\n\t</div>\n{% else %}\n\t<div class="lede">\n\t\t<h1>Certifications for people who run things</h1>\n\t\tWritten from live retail, distribution and finance operations rather than from a textbook. Your staff read at their own pace, sit a proctored assessment, and earn a certificate with a serial anyone can <a href="/verify">verify</a>.\n\t</div>\n\t<div class="grid">\n\t{% for t in tracks %}\n\t\t<a class="card" href="/academy?track={{ t.name | urlencode }}">\n\t\t\t<span class="tag {{ \'paid\' if t.paid else \'free\' }}">{{ t.price + \' / seat\' if t.paid else \'Free\' }}</span>\n\t\t\t<span class="name">{{ t.title }}</span>\n\t\t\t<span class="meta">{{ t.product }} · {{ t.courses|length }} course{{ \'\' if t.courses|length == 1 else \'s\' }}{% if t.hours %} · ~{{ t.hours }} hrs{% endif %}</span>\n\t\t\t{% if t.description %}<span class="blurb">{{ t.description }}</span>{% endif %}\n\t\t\t<span class="more">See what it covers &rarr;</span>\n\t\t</a>\n\t{% else %}\n\t\t<div style="color:#6B7C77">No certifications published yet.</div>\n\t{% endfor %}\n\t</div>\n{% endif %}\n\t<div class="foot">CloudERP.One Academy · Xlevel Retail Systems Ltd<br>Certificates are verifiable at <a href="/verify">/verify</a>.</div>\n</div></body></html>\n'

VER_OLD = '\t<div class="muted">Credentials are issued by Xlevel Retail Systems Ltd through the CloudERP.One Academy and verified against the live registry.</div>'

VER_NEW = '\t<div class="muted">Credentials are issued by Xlevel Retail Systems Ltd through the CloudERP.One Academy and verified against the live registry.<br>\n\t\t<a href="/academy" style="color:#0F5C55;font-weight:700;text-decoration:none">See what the Academy certifies &rarr;</a></div>'



def add_fields(path, new_fields):
    with io.open(path, encoding="utf-8") as f:
        dt = _json.load(f)
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
            _json.dump(dt, f, indent=1)
            f.write("\n")
    return added


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, VERIFY), encoding="utf-8") as f:
        verify = f.read()

    if os.path.exists(os.path.join(root, WWW, "academy.py")):
        print("Already applied. Nothing to do.")
        return
    if '"3.221.1"' not in init:
        sys.exit("ABORT: not at v3.221.1.")

    n = verify.count(VER_OLD)
    if n != 1:
        sys.exit("ABORT - verify anchor matched %d times, expected 1." % n)
    print("All 1 anchors matched exactly once.")

    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    add_fields(os.path.join(root, LSDT), [
        {"fieldname": "is_sample", "fieldtype": "Check", "label": "Public Sample Chapter"},
    ])
    print("  Duty Lesson: +is_sample")

    with io.open(os.path.join(root, WWW, "academy.py"), "w", encoding="utf-8") as f:
        f.write(ACADEMY_PY)
    with io.open(os.path.join(root, WWW, "academy.html"), "w", encoding="utf-8") as f:
        f.write(ACADEMY_HTML)
    print("  www/academy.py + academy.html")

    with io.open(os.path.join(root, VERIFY), "w", encoding="utf-8") as f:
        f.write(verify.replace(VER_OLD, VER_NEW, 1))
    print("  verify.html: link to the catalogue")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.221.1"', '"3.222.0"'))
    print("wrote __init__.py -> 3.222.0")


if __name__ == "__main__":
    main()
