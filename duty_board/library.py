# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""The Library: ebooks as chaptered HTML with per-user resume.

Books arrive as JSON bundles (converted from PDF in the dev container):
  {"title": ..., "author": ..., "description": ...,
   "chapters": [{"title": ..., "content": "<h2>..</h2><p>..</p>", "words": 1234}, ...]}

Import on the server:
  bench --site xlevel.clouderp.one execute duty_board.library.import_book_json \
      --kwargs "{'path': '/home/bench/book.json'}"

Reading position = current chapter + scroll depth (%), saved as the reader
scrolls; completed chapters tracked; minutes accumulated coarsely.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

from duty_board.permissions import require_staff


def import_book_json(path):
	data = json.load(open(path))
	book = frappe.get_doc(
		{
			"doctype": "Duty Book",
			"title": data["title"][:140],
			"author": (data.get("author") or "")[:140] or None,
			"description": (data.get("description") or "")[:500] or None,
			"active": 1,
			"chapter_count": len(data.get("chapters") or []),
		}
	).insert(ignore_permissions=True)
	for i, ch in enumerate(data.get("chapters") or [], start=1):
		frappe.get_doc(
			{
				"doctype": "Duty Book Chapter",
				"book": book.name,
				"idx_no": i,
				"title": (ch.get("title") or f"Chapter {i}")[:140],
				"content": ch.get("content") or "",
				"words": cint(ch.get("words")),
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"Imported: {book.title} ({book.chapter_count} chapters) as {book.name}")
	return book.name


def _progress(user, book):
	name = frappe.db.exists("Duty Book Progress", {"user": user, "book": book})
	return frappe.get_doc("Duty Book Progress", name) if name else None


@frappe.whitelist()
def library():
	"""All active books with the caller's progress."""
	require_staff()
	user = frappe.session.user
	books = frappe.get_all(
		"Duty Book",
		filters={"active": 1},
		fields=["name", "title", "author", "description", "chapter_count"],
		order_by="creation desc",
	)
	for b in books:
		b.words = cint(
			frappe.db.sql(
				"select sum(words) from `tabDuty Book Chapter` where book=%s", b.name
			)[0][0]
		)
		p = _progress(user, b.name)
		done = len([c for c in (p.chapters_done or "").split(",") if c]) if p else 0
		b.done_chapters = done
		b.pct = int(done * 100 / b.chapter_count) if b.chapter_count else 0
		b.last_read_at = str(p.last_read_at)[:16] if p and p.last_read_at else None
		b.resume_chapter = p.chapter if p else None
	return books


@frappe.whitelist()
def open_book(book):
	"""Chapter list + full text of the resume chapter."""
	require_staff()
	user = frappe.session.user
	b = frappe.get_doc("Duty Book", book)
	chapters = frappe.get_all(
		"Duty Book Chapter",
		filters={"book": book},
		fields=["name", "idx_no", "title", "words"],
		order_by="idx_no asc",
		limit_page_length=0,
	)
	p = _progress(user, book)
	done = [c for c in (p.chapters_done or "").split(",") if c] if p else []
	cur = p.chapter if p and p.chapter else (chapters[0].name if chapters else None)
	return {
		"title": b.title,
		"author": b.author,
		"chapters": chapters,
		"done": done,
		"current": cur,
		"scroll_pct": flt(p.scroll_pct) if p else 0,
		"content": frappe.db.get_value("Duty Book Chapter", cur, "content") if cur else "",
	}


@frappe.whitelist()
def chapter(name):
	require_staff()
	ch = frappe.get_doc("Duty Book Chapter", name)
	return {"name": ch.name, "title": ch.title, "content": ch.content, "idx_no": ch.idx_no}


@frappe.whitelist()
def mark(book, chapter=None, scroll_pct=0, minutes=0, done=None):
	"""Save the reader's position. `done` marks a chapter completed."""
	require_staff()
	user = frappe.session.user
	p = _progress(user, book)
	if not p:
		p = frappe.get_doc(
			{"doctype": "Duty Book Progress", "user": user, "book": book}
		).insert(ignore_permissions=True)
	if chapter:
		p.chapter = chapter
	p.scroll_pct = flt(scroll_pct)
	p.minutes = cint(p.minutes) + cint(minutes)
	if done:
		cur = [c for c in (p.chapters_done or "").split(",") if c]
		if done not in cur:
			cur.append(done)
		p.chapters_done = ",".join(cur)
	p.last_read_at = now_datetime()
	p.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def reading_overview():
	"""Managers: who is where in which book."""
	require_staff()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("The reading overview is for managers."), frappe.PermissionError)
	rows = frappe.get_all(
		"Duty Book Progress",
		fields=["user", "book", "chapter", "chapters_done", "last_read_at", "minutes"],
		order_by="last_read_at desc",
		limit_page_length=0,
	)
	books = {
		b.name: b
		for b in frappe.get_all("Duty Book", fields=["name", "title", "chapter_count"])
	}
	out = []
	for r in rows:
		b = books.get(r.book)
		if not b:
			continue
		done = len([c for c in (r.chapters_done or "").split(",") if c])
		out.append(
			{
				"user": r.user,
				"who": frappe.utils.get_fullname(r.user),
				"book": b.title,
				"pct": int(done * 100 / b.chapter_count) if b.chapter_count else 0,
				"done": done,
				"total": b.chapter_count,
				"last": str(r.last_read_at)[:16] if r.last_read_at else None,
				"minutes": cint(r.minutes),
			}
		)
	return out
