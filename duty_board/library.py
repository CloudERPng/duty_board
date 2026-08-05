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

from duty_board.permissions import require_staff, require_staff_or_consultant


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
	require_staff_or_consultant()
	user = frappe.session.user
	from duty_board.uat import _is_manager

	manager = _is_manager()
	books = frappe.get_all(
		"Duty Book",
		filters={"active": 1},
		fields=["name", "title", "author", "description", "category", "cover", "chapter_count"],
		order_by="creation desc",
	)
	all_reviews = frappe.get_all(
		"Duty Book Review", fields=["book", "user", "stars"], limit_page_length=0
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
		rv = [r for r in all_reviews if r.book == b.name and cint(r.stars)]
		b.rating_n = len(rv)
		b.rating_avg = round(sum(cint(r.stars) for r in rv) / len(rv), 1) if rv else 0
		mine = next((r for r in all_reviews if r.book == b.name and r.user == user), None)
		b.my_stars = cint(mine.stars) if mine else 0
	return {"books": books, "manager": 1 if manager else 0}


@frappe.whitelist()
def open_book(book):
	"""Chapter list + full text of the resume chapter."""
	require_staff_or_consultant()
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
		"last_read_at": str(p.last_read_at) if p and p.last_read_at else None,
		"content": frappe.db.get_value("Duty Book Chapter", cur, "content") if cur else "",
	}


@frappe.whitelist()
def chapter(name):
	require_staff_or_consultant()
	ch = frappe.get_doc("Duty Book Chapter", name)
	return {"name": ch.name, "title": ch.title, "content": ch.content, "idx_no": ch.idx_no}


@frappe.whitelist()
def mark(book, chapter=None, scroll_pct=0, minutes=0, done=None):
	"""Save the reader's position. `done` marks a chapter completed."""
	require_staff_or_consultant()
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
	require_staff_or_consultant()
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


# ---------------- in-app PDF conversion ----------------


def _pdf_to_chapters(content_bytes):
	"""Extract chaptered HTML from a PDF. Prefers pdfminer.six (font-size
	heading detection); falls back to pypdf plain text with heuristics.
	Returns (chapters, method) or throws for scanned/imageonly PDFs."""
	import io
	import re

	chapters = []
	method = None
	try:
		from pdfminer.high_level import extract_pages
		from pdfminer.layout import LTTextContainer, LTChar

		sizes = {}
		lines = []  # (size, text)
		for page in extract_pages(io.BytesIO(content_bytes)):
			for el in page:
				if isinstance(el, LTTextContainer):
					for line in el:
						if not hasattr(line, "get_text"):
							continue
						txt = line.get_text().strip()
						if not txt:
							continue
						sz = 0
						for ch in line:
							if isinstance(ch, LTChar):
								sz = max(sz, round(ch.size, 1))
						lines.append((sz, txt))
						sizes[sz] = sizes.get(sz, 0) + len(txt)
		if not lines:
			raise ValueError("no text")
		body_size = max(sizes, key=sizes.get)
		heading_min = body_size * 1.18
		method = "pdfminer"
		cur = {"title": None, "paras": []}
		buf = []

		def flush_para():
			if buf:
				cur["paras"].append(" ".join(buf))
				buf.clear()

		def flush_ch():
			flush_para()
			if cur["paras"] or cur["title"]:
				chapters.append(dict(cur))
			cur["title"] = None
			cur["paras"] = []

		for sz, txt in lines:
			if sz >= heading_min and len(txt) < 120:
				flush_ch()
				cur["title"] = txt
			else:
				buf.append(txt)
				if txt.endswith((".", "?", "!", ":", "”", '"')):
					flush_para()
		flush_ch()
	except Exception:
		# ---- fallback: pypdf ----
		from pypdf import PdfReader

		reader = PdfReader(io.BytesIO(content_bytes))
		pages = [p.extract_text() or "" for p in reader.pages]
		total_chars = sum(len(p) for p in pages)
		if total_chars < 40 * max(len(pages), 1):
			frappe.throw(
				_("This PDF looks scanned (page images, not text) — it needs OCR. Send it to Claude for conversion instead.")
			)
		method = "pypdf"
		text = "\n".join(pages)
		raw_lines = [l.strip() for l in text.split("\n")]
		ch_re = re.compile(r"^(chapter|part|section)\s+([0-9ivxlc]+|one|two|three|four|five|six|seven|eight|nine|ten)\b[\s:.\-—]*(.*)$", re.I)
		cur = {"title": None, "paras": []}
		buf = []

		def flush_para():
			if buf:
				cur["paras"].append(" ".join(buf))
				buf.clear()

		def flush_ch():
			flush_para()
			if cur["paras"] or cur["title"]:
				chapters.append(dict(cur))
			cur["title"] = None
			cur["paras"] = []

		for l in raw_lines:
			m = ch_re.match(l)
			if m and len(l) < 90:
				flush_ch()
				cur["title"] = l
			elif not l:
				flush_para()
			else:
				buf.append(l)
		flush_ch()
	# no structure found → paginate into parts
	if len(chapters) <= 1:
		paras = chapters[0]["paras"] if chapters else []
		chapters = []
		per = 60
		for i in range(0, len(paras), per):
			chapters.append({"title": _("Part {0}").format(i // per + 1), "paras": paras[i : i + per]})
	out = []
	for i, ch in enumerate(chapters, start=1):
		title = (ch["title"] or _("Chapter {0}").format(i)).strip()[:140]
		paras = [p for p in ch["paras"] if p.strip()]
		html = f"<h2>{frappe.utils.escape_html(title)}</h2>" + "".join(
			f"<p>{frappe.utils.escape_html(p)}</p>" for p in paras
		)
		out.append({"title": title, "content": html, "words": sum(len(p.split()) for p in paras)})
	if not out:
		frappe.throw(_("No readable text found in this PDF."))
	return out, method


def _convert_job(file_url, title, author, description, requested_by, category=None, cover_url=None):
	fname = frappe.db.get_value("File", {"file_url": file_url}, "name")
	fdoc = frappe.get_doc("File", fname)
	if (fdoc.file_name or "").lower().endswith(".epub"):
		chapters, meta_title, meta_author = _epub_to_chapters(fdoc.get_content())
		title = title or meta_title
		author = author or meta_author
	else:
		chapters, method = _pdf_to_chapters(fdoc.get_content())
	book = frappe.get_doc(
		{
			"doctype": "Duty Book",
			"title": (title or fdoc.file_name.rsplit(".", 1)[0])[:140],
			"author": (author or "")[:140] or None,
			"description": (description or "")[:500] or None,
			"category": (category or "")[:80] or None,
			"active": 1,
			"chapter_count": len(chapters),
		}
	).insert(ignore_permissions=True)
	for i, ch in enumerate(chapters, start=1):
		frappe.get_doc(
			{
				"doctype": "Duty Book Chapter",
				"book": book.name,
				"idx_no": i,
				"title": ch["title"],
				"content": ch["content"],
				"words": ch["words"],
			}
		).insert(ignore_permissions=True)
	frappe.db.commit()
	_save_cover(book.name, cover_url)
	frappe.db.commit()
	try:
		from duty_board.api import _notify_user

		_notify_user(
			requested_by,
			_("📚 Book ready"),
			_("“{0}” — {1} chapters, on the shelf.").format(book.title, len(chapters)),
		)
	except Exception:
		pass


@frappe.whitelist()
def convert_pdf(file_url, title=None, author=None, description=None, category=None, cover_url=None):
	"""Managers: turn an uploaded PDF into a Library book (background job)."""
	require_staff()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("Only managers stock the Library."), frappe.PermissionError)
	frappe.enqueue(
		"duty_board.library._convert_job",
		queue="long",
		timeout=1200,
		file_url=file_url,
		title=title,
		author=author,
		description=description,
		category=category,
		cover_url=cover_url,
		requested_by=frappe.session.user,
	)
	return {"queued": 1}


@frappe.whitelist()
def delete_book(book):
	require_staff()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("Only managers manage the Library."), frappe.PermissionError)
	for c in frappe.get_all("Duty Book Chapter", filters={"book": book}, pluck="name"):
		frappe.delete_doc("Duty Book Chapter", c, ignore_permissions=True, force=True)
	for p in frappe.get_all("Duty Book Progress", filters={"book": book}, pluck="name"):
		frappe.delete_doc("Duty Book Progress", p, ignore_permissions=True, force=True)
	frappe.delete_doc("Duty Book", book, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": 1}


# ---------------- epub conversion (stdlib only, near-lossless) ----------------

_OK_TAGS = {"h1", "h2", "h3", "h4", "p", "ul", "ol", "li", "b", "strong", "i", "em",
	"blockquote", "br", "hr", "table", "thead", "tbody", "tr", "td", "th", "img", "a", "sub", "sup"}


def _sanitize_html(raw, images):
	"""Whitelist tags, strip attributes (keep img src via provided map, a href)."""
	from html.parser import HTMLParser

	out = []

	class S(HTMLParser):
		def handle_starttag(self, tag, attrs):
			a = dict(attrs)
			if tag == "image":  # svg-wrapped figure: <svg><image xlink:href=…>
				href = a.get("xlink:href") or a.get("href") or ""
				srcd = images.get(href.split("/")[-1])
				if srcd:
					out.append(f'<img src="{srcd}" style="max-width:100%">')
				return
			if tag not in _OK_TAGS:
				return
			if tag == "img":
				src_att = a.get("src") or ""
				srcd = images.get(src_att.split("/")[-1])
				if not srcd and src_att.startswith("https://"):
					srcd = frappe.utils.escape_html(src_att)
				if srcd:
					out.append(f'<img src="{srcd}" style="max-width:100%">')
				return
			if tag == "a" and a.get("href", "").startswith("http"):
				out.append(f'<a href="{frappe.utils.escape_html(a["href"])}" target="_blank">')
				return
			out.append(f"<{tag}>")

		def handle_endtag(self, tag):
			if tag in _OK_TAGS and tag not in ("img", "br", "hr"):
				out.append(f"</{tag}>")

		def handle_data(self, data):
			out.append(frappe.utils.escape_html(data))

	S().feed(raw)
	html = "".join(out)
	# collapse pathological whitespace
	import re

	return re.sub(r"(\s*<p>\s*</p>\s*)+", "", html)


def _epub_to_chapters(content_bytes):
	import io
	import posixpath
	import re
	import zipfile
	from xml.etree import ElementTree as ET

	z = zipfile.ZipFile(io.BytesIO(content_bytes))
	container = ET.fromstring(z.read("META-INF/container.xml"))
	opf_path = container.find(".//{*}rootfile").get("full-path")
	opf_dir = posixpath.dirname(opf_path)
	opf = ET.fromstring(z.read(opf_path))
	manifest = {}
	for item in opf.findall(".//{*}manifest/{*}item"):
		manifest[item.get("id")] = {
			"href": item.get("href"),
			"type": item.get("media-type") or "",
		}
	spine = [it.get("idref") for it in opf.findall(".//{*}spine/{*}itemref")]
	meta_title = (opf.findtext(".//{*}metadata/{*}title") or "").strip()
	meta_author = (opf.findtext(".//{*}metadata/{*}creator") or "").strip()

	def zread(href):
		p = posixpath.normpath(posixpath.join(opf_dir, href))
		return z.read(p)

	# small images → data URIs
	import base64

	images = {}
	for it in manifest.values():
		if it["type"].startswith("image/"):
			try:
				raw = zread(it["href"])
				if len(raw) <= 300 * 1024:
					images[it["href"].split("/")[-1]] = (
						f"data:{it['type']};base64," + base64.b64encode(raw).decode()
					)
			except Exception:
				pass

	# toc titles (ncx or nav)
	toc = {}
	for it in manifest.values():
		if it["href"].endswith(".ncx"):
			try:
				ncx = ET.fromstring(zread(it["href"]))
				for np in ncx.findall(".//{*}navPoint"):
					lbl = (np.findtext(".//{*}text") or "").strip()
					srcel = np.find(".//{*}content")
					if lbl and srcel is not None:
						toc[srcel.get("src").split("#")[0].split("/")[-1]] = lbl
			except Exception:
				pass

	chapters = []
	for idref in spine:
		it = manifest.get(idref)
		if not it or "html" not in it["type"]:
			continue
		try:
			raw = zread(it["href"]).decode("utf-8", "ignore")
		except Exception:
			continue
		body = re.search(r"<body[^>]*>(.*)</body>", raw, re.S | re.I)
		body = body.group(1) if body else raw
		html = _sanitize_html(body, images)
		text = re.sub(r"<[^>]+>", " ", html)
		words = len(text.split())
		if words < 15 and "<img" not in html:
			continue  # cover pages, blank separators
		fname = it["href"].split("/")[-1]
		title = toc.get(fname)
		if not title:
			m = re.search(r"<h[12]>(.*?)</h[12]>", html, re.S)
			title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None
		chapters.append(
			{
				"title": (title or _("Chapter {0}").format(len(chapters) + 1))[:140],
				"content": html,
				"words": words,
			}
		)
	if not chapters:
		frappe.throw(_("No readable chapters found in this ePub."))
	return chapters, meta_title, meta_author


@frappe.whitelist()
def rate_book(book, stars, review=None):
	require_staff_or_consultant()
	stars = cint(stars)
	if stars < 1 or stars > 5:
		frappe.throw(_("Stars must be 1–5."))
	user = frappe.session.user
	name = frappe.db.exists("Duty Book Review", {"book": book, "user": user})
	doc = frappe.get_doc("Duty Book Review", name) if name else frappe.get_doc(
		{"doctype": "Duty Book Review", "book": book, "user": user}
	)
	doc.stars = stars
	if review is not None:
		doc.review = (review or "").strip()[:1000] or None
	doc.updated_at = now_datetime()
	doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return book_reviews(book)


@frappe.whitelist()
def book_reviews(book):
	require_staff_or_consultant()
	rows = frappe.get_all(
		"Duty Book Review",
		filters={"book": book},
		fields=["user", "stars", "review", "updated_at"],
		order_by="updated_at desc",
		limit_page_length=0,
	)
	for r in rows:
		r.who = frappe.utils.get_fullname(r.user)
		r.when = str(r.updated_at)[:10] if r.updated_at else ""
		r.mine = 1 if r.user == frappe.session.user else 0
	rated = [r for r in rows if cint(r.stars)]
	return {
		"rows": rows,
		"avg": round(sum(cint(r.stars) for r in rated) / len(rated), 1) if rated else 0,
		"n": len(rated),
	}


@frappe.whitelist()
def update_book(book, title=None, author=None, category=None, description=None):
	require_staff()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("Only managers manage the Library."), frappe.PermissionError)
	vals = {}
	if title and title.strip():
		vals["title"] = title.strip()[:140]
	if author is not None:
		vals["author"] = (author or "").strip()[:140] or None
	if category is not None:
		vals["category"] = (category or "").strip()[:80] or None
	if description is not None:
		vals["description"] = (description or "").strip()[:500] or None
	if vals:
		frappe.db.set_value("Duty Book", book, vals, update_modified=False)
		frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def apply_book_meta(book, title=None, author=None, description=None, category=None, cover_url=None):
	"""Enrich an existing shelved book from a picked search match."""
	require_staff()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("Only managers manage the Library."), frappe.PermissionError)
	update_book(book, title=title, author=author, category=category, description=description)
	_save_cover(book, cover_url)
	frappe.db.commit()
	return {"ok": 1}


# ---------------- external metadata (Google Books) ----------------


@frappe.whitelist()
def search_books(query):
	"""Book metadata search: Google Books first, Open Library fallback
	(Google's keyless API is often blocked/empty from datacenter IPs)."""
	require_staff_or_consultant()
	q = (query or "").strip()
	if not q:
		return []
	hits = _google_books(q)
	if not hits:
		hits = _open_library(q)
	return hits


def _google_books(q):
	import requests

	try:
		r = requests.get(
			"https://www.googleapis.com/books/v1/volumes",
			params={"q": q, "maxResults": 6, "printType": "books"},
			timeout=8,
		)
		if r.status_code != 200:
			return []
		items = (r.json() or {}).get("items") or []
	except Exception:
		return []
	out = []
	for it in items:
		v = it.get("volumeInfo") or {}
		img = (v.get("imageLinks") or {}).get("thumbnail") or ""
		out.append(
			{
				"title": v.get("title") or "",
				"subtitle": v.get("subtitle") or "",
				"authors": ", ".join(v.get("authors") or []),
				"description": (v.get("description") or "")[:800],
				"categories": ", ".join(v.get("categories") or []),
				"year": (v.get("publishedDate") or "")[:4],
				"publisher": v.get("publisher") or "",
				"pages": v.get("pageCount") or 0,
				"thumbnail": img.replace("http://", "https://"),
			}
		)
	return out


def _open_library(q):
	import requests

	try:
		r = requests.get(
			"https://openlibrary.org/search.json",
			params={
				"q": q,
				"limit": 6,
				"fields": "key,title,subtitle,author_name,first_publish_year,publisher,number_of_pages_median,cover_i,subject",
			},
			timeout=8,
		)
		if r.status_code != 200:
			return []
		docs = (r.json() or {}).get("docs") or []
	except Exception:
		return []
	out = []
	for i, d in enumerate(docs):
		desc = ""
		if i < 3 and d.get("key"):
			try:
				w = requests.get(f"https://openlibrary.org{d['key']}.json", timeout=5).json()
				dd = w.get("description")
				desc = (dd.get("value") if isinstance(dd, dict) else dd or "")[:800]
			except Exception:
				pass
		out.append(
			{
				"title": d.get("title") or "",
				"subtitle": d.get("subtitle") or "",
				"authors": ", ".join(d.get("author_name") or []),
				"description": desc,
				"categories": ", ".join((d.get("subject") or [])[:3]),
				"year": str(d.get("first_publish_year") or ""),
				"publisher": ", ".join((d.get("publisher") or [])[:1]),
				"pages": d.get("number_of_pages_median") or 0,
				"thumbnail": f"https://covers.openlibrary.org/b/id/{d['cover_i']}-M.jpg" if d.get("cover_i") else "",
			}
		)
	return out


def _save_cover(book_name, cover_url):
	if not cover_url or not cover_url.startswith("https://"):
		return
	import requests

	try:
		r = requests.get(cover_url, timeout=10)
		if r.status_code != 200 or len(r.content) > 2 * 1024 * 1024:
			return
		f = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"cover-{book_name}.jpg",
				"is_private": 0,
				"content": r.content,
				"attached_to_doctype": "Duty Book",
				"attached_to_name": book_name,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Duty Book", book_name, "cover", f.file_url, update_modified=False)
	except Exception:
		pass


# ─────────────── highlights: solitary reading, ambient team learning ───────────────

def _hl_norm(t):
	import re as _re

	return _re.sub(r"\s+", " ", (t or "").strip())[:500]


@frappe.whitelist()
def highlight_add(book, chapter, text, note=None):
	"""Mark a passage; visible to the whole team by design."""
	require_staff_or_consultant()
	text = _hl_norm(text)
	if len(text) < 3:
		frappe.throw(_("Select a little more text."))
	frappe.get_doc({
		"doctype": "Duty Book Highlight",
		"user": frappe.session.user,
		"book": book,
		"chapter": chapter,
		"text": text,
		"note": (note or "")[:500] or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return highlights(chapter)


@frappe.whitelist()
def highlight_remove(name):
	"""Only your own marks come off the page."""
	require_staff_or_consultant()
	doc = frappe.get_doc("Duty Book Highlight", name)
	if doc.user != frappe.session.user:
		frappe.throw(_("Not your highlight."), frappe.PermissionError)
	frappe.delete_doc("Duty Book Highlight", name, ignore_permissions=True)
	frappe.db.commit()
	return highlights(doc.chapter)


@frappe.whitelist()
def highlights(chapter):
	"""Every mark on this chapter, grouped by passage: who, notes, and
	whether the caller is among the markers."""
	require_staff_or_consultant()
	rows = frappe.get_all(
		"Duty Book Highlight",
		filters={"chapter": chapter},
		fields=["name", "user", "text", "note", "creation"],
		order_by="creation asc",
	)
	me = frappe.session.user
	groups = {}
	for r in rows:
		g = groups.setdefault(r.text, {"text": r.text, "n": 0, "mine": None, "notes": [], "users": []})
		g["n"] += 1
		first = frappe.utils.get_fullname(r.user).split(" ")[0]
		g["users"].append(first)
		if r.user == me:
			g["mine"] = r.name
		if r.note:
			g["notes"].append({"who": first, "note": r.note})
	return list(groups.values())


@frappe.whitelist()
def my_highlights(book):
	"""The caller's marks across one book, chapter-ordered."""
	require_staff_or_consultant()
	rows = frappe.db.sql(
		"""
		select h.name, h.text, h.note, h.chapter, c.title as ch_title, c.idx_no
		from `tabDuty Book Highlight` h
		join `tabDuty Book Chapter` c on c.name = h.chapter
		where h.book = %s and h.user = %s
		order by c.idx_no asc, h.creation asc
		""",
		(book, frappe.session.user),
		as_dict=True,
	)
	return rows


@frappe.whitelist()
def search_in_book(book, q):
	"""Find a phrase across the book's chapters; returns snippets."""
	require_staff_or_consultant()
	q = (q or "").strip()
	if len(q) < 2:
		return []
	import re as _re

	out = []
	for ch in frappe.get_all(
		"Duty Book Chapter",
		filters={"book": book},
		fields=["name", "title", "idx_no", "content"],
		order_by="idx_no asc",
	):
		plain = _re.sub(r"<[^>]+>", " ", ch.content or "")
		plain = _re.sub(r"\s+", " ", plain)
		i = plain.lower().find(q.lower())
		if i < 0:
			continue
		start = max(0, i - 70)
		snippet = ("…" if start else "") + plain[start : i + len(q) + 90] + "…"
		out.append({"chapter": ch.name, "title": ch.title, "idx_no": ch.idx_no, "snippet": snippet})
		if len(out) >= 30:
			break
	return out


# ─────────────────────────── bookmarks ───────────────────────────

@frappe.whitelist()
def bookmark_add(book, chapter, scroll_pct=0, note=None):
	require_staff_or_consultant()
	frappe.get_doc({
		"doctype": "Duty Book Bookmark",
		"user": frappe.session.user,
		"book": book,
		"chapter": chapter,
		"scroll_pct": flt(scroll_pct),
		"note": (note or "")[:300] or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return bookmarks(book)


@frappe.whitelist()
def bookmark_remove(name):
	require_staff_or_consultant()
	doc = frappe.get_doc("Duty Book Bookmark", name)
	if doc.user != frappe.session.user:
		frappe.throw(_("Not your bookmark."), frappe.PermissionError)
	frappe.delete_doc("Duty Book Bookmark", name, ignore_permissions=True)
	frappe.db.commit()
	return bookmarks(doc.book)


@frappe.whitelist()
def bookmarks(book):
	"""The caller's ribbons in one book, chapter-ordered."""
	require_staff_or_consultant()
	return frappe.db.sql(
		"""
		select b.name, b.chapter, b.scroll_pct, b.note, b.creation,
		       c.title as ch_title, c.idx_no
		from `tabDuty Book Bookmark` b
		join `tabDuty Book Chapter` c on c.name = b.chapter
		where b.book = %s and b.user = %s
		order by c.idx_no asc, b.scroll_pct asc
		""",
		(book, frappe.session.user),
		as_dict=True,
	)
