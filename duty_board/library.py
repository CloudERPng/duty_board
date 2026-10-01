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
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

# The Library is System Manager only. It holds licensed books rather than
# operational data, so the audience is narrower than staff-at-large — every
# whitelisted endpoint in this module is gated, not only the page, because a
# rail entry that is merely hidden is not a permission.
from duty_board.permissions import require_sysadmin


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
	require_sysadmin()
	user = frappe.session.user
	from duty_board.uat import _is_manager

	manager = _is_manager()
	books = frappe.get_all(
		"Duty Book",
		filters={"active": 1},
		fields=["name", "title", "author", "description", "category", "cover",
				"chapter_count", "format", "page_count", "source_file", "shelf_status", "plan_month", "plan_note",
				"revisit_after", "times_read", "last_finished"],
		order_by="creation desc",
		limit_page_length=0,
	)
	all_reviews = frappe.get_all(
		"Duty Book Review", fields=["book", "user", "stars"], limit_page_length=0
	)
	# Word counts and progress were each fetched per book — two round trips per
	# row, so forty books was fine and a thousand would not have been. Both are
	# now one query, grouped in Python.
	words_by_book = {
		r[0]: cint(r[1])
		for r in frappe.db.sql(
			"select book, sum(words) from `tabDuty Book Chapter` group by book"
		)
	}
	prog_by_book = {
		r.book: r
		for r in frappe.get_all(
			"Duty Book Progress",
			filters={"user": user},
			fields=["book", "chapter", "page", "chapters_done", "last_read_at"],
			limit_page_length=0,
		)
	}
	# topics and authors in two queries, grouped in Python — the same discipline
	# as the word counts above, so shelf size does not change the query count
	topics_by_book = {}
	for r in frappe.get_all(
		"Duty Book Topic", fields=["parent", "topic"], limit_page_length=0
	):
		topics_by_book.setdefault(r.parent, []).append(r.topic)
	authors_by_book = {}
	for r in frappe.get_all(
		"Duty Book Author", fields=["parent", "author"], limit_page_length=0
	):
		authors_by_book.setdefault(r.parent, []).append(r.author)
	for b in books:
		b.words = words_by_book.get(b.name, 0)
		b.topic_list = topics_by_book.get(b.name, [])
		b.author_list = authors_by_book.get(b.name, [])
		p = prog_by_book.get(b.name)
		done = len([c for c in (p.chapters_done or "").split(",") if c]) if p else 0
		b.done_chapters = done
		if b.format == "PDF":
			# a page-based book measures progress by the furthest page reached
			b.resume_page = cint(p.page) if p else 0
			b.pct = min(100, int(b.resume_page * 100 / b.page_count)) if b.page_count else 0
		else:
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
	require_sysadmin()
	user = frappe.session.user
	b = frappe.get_doc("Duty Book", book)
	p = _progress(user, book)
	if b.format == "PDF":
		# Fixed-page book: the browser renders the file itself. Nothing here is
		# chaptered, so the text reader's fields are returned empty on purpose.
		return {
			"format": "PDF",
			"title": b.title,
			"author": b.author,
			"file_url": b.source_file,
			"page_count": cint(b.page_count),
			"page": max(1, cint(p.page)) if p else 1,
			"comic": (b.category or "").strip().lower() == "comic",
			"rtl": (b.reading_direction or "") == "Right to left",
			"last_read_at": str(p.last_read_at) if p and p.last_read_at else None,
			"chapters": [], "done": [], "current": None, "scroll_pct": 0, "content": "",
		}
	chapters = frappe.get_all(
		"Duty Book Chapter",
		filters={"book": book},
		fields=["name", "idx_no", "title", "words"],
		order_by="idx_no asc",
		limit_page_length=0,
	)
	done = [c for c in (p.chapters_done or "").split(",") if c] if p else []
	cur = p.chapter if p and p.chapter else (chapters[0].name if chapters else None)
	return {
		"format": "Text",
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
	require_sysadmin()
	ch = frappe.get_doc("Duty Book Chapter", name)
	return {"name": ch.name, "title": ch.title, "content": ch.content, "idx_no": ch.idx_no}


@frappe.whitelist()
def mark(book, chapter=None, scroll_pct=0, minutes=0, done=None, page=None):
	"""Save the reader's position. `done` marks a chapter completed.
	`page` is the PDF reader's position; the furthest page is what counts."""
	require_sysadmin()
	user = frappe.session.user
	p = _progress(user, book)
	if not p:
		p = frappe.get_doc(
			{"doctype": "Duty Book Progress", "user": user, "book": book}
		).insert(ignore_permissions=True)
	if chapter:
		p.chapter = chapter
	if page is not None:
		p.page = max(cint(p.page), cint(page))
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
	require_sysadmin()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("The reading overview is for managers."), frappe.PermissionError)
	rows = frappe.get_all(
		"Duty Book Progress",
		fields=["user", "book", "chapter", "page", "chapters_done", "last_read_at", "minutes"],
		order_by="last_read_at desc",
		limit_page_length=0,
	)
	books = {
		b.name: b
		for b in frappe.get_all("Duty Book", fields=["name", "title", "chapter_count", "format", "page_count"])
	}
	out = []
	for r in rows:
		b = books.get(r.book)
		if not b:
			continue
		if b.format == "PDF":
			done, total = cint(r.page), cint(b.page_count)
		else:
			done, total = len([c for c in (r.chapters_done or "").split(",") if c]), cint(b.chapter_count)
		out.append(
			{
				"user": r.user,
				"who": frappe.utils.get_fullname(r.user),
				"book": b.title,
				"pct": min(100, int(done * 100 / total)) if total else 0,
				"done": done,
				"total": total,
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


COMIC_EXTS = (".cbz", ".cbr")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


def _looks_manga(title, description):
	t = f"{title or ''} {description or ''}".lower()
	return any(k in t for k in ("manga", "manhwa", "tankobon", "shonen", "shojo", "seinen"))


def _natural_key(name):
	"""'page2.jpg' before 'page10.jpg' — the order a comic was scanned in."""
	import re

	return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _comic_to_pdf(content_bytes, file_name):
	"""A CBZ (zip) or CBR (rar) of page images, joined into one PDF in reading
	order. Returns (pdf_bytes, page_count). The PDF path then treats it like
	any other page-image book — rendering, page memory, covers and offline all
	come for free, which is the whole point of not building a comic reader.

	CBR needs the `rarfile` module and an `unrar` binary on the server; if
	either is missing the error says so plainly rather than failing deep."""
	import io

	from PIL import Image

	low = (file_name or "").lower()
	names, read = [], None
	if low.endswith(".cbz"):
		import zipfile

		zf = zipfile.ZipFile(io.BytesIO(content_bytes))
		names = [n for n in zf.namelist() if not n.endswith("/")]
		read = zf.read
	elif low.endswith(".cbr"):
		try:
			import rarfile
		except ImportError:
			frappe.throw(_("CBR needs the rarfile package: bench pip install rarfile"))
		try:
			rf = rarfile.RarFile(io.BytesIO(content_bytes))
			names = [i.filename for i in rf.infolist() if not i.isdir()]
			read = rf.read
		except rarfile.RarCannotExec:
			frappe.throw(_("CBR needs the unrar tool on the server: sudo apt install unrar"))
	else:
		frappe.throw(_("Not a comic archive."))
	pages = sorted(
		[n for n in names if n.lower().endswith(IMAGE_EXTS) and not n.split("/")[-1].startswith((".", "__"))],
		key=_natural_key,
	)
	if not pages:
		frappe.throw(_("No page images found inside this archive."))
	images = []
	for n in pages:
		try:
			im = Image.open(io.BytesIO(read(n)))
			im.load()
			if im.mode in ("RGBA", "P", "LA"):
				im = im.convert("RGB")
			elif im.mode != "RGB":
				im = im.convert("RGB")
			images.append(im)
		except Exception:
			continue  # a corrupt page is skipped, not fatal
	if not images:
		frappe.throw(_("None of the pages in this archive could be read as images."))
	out = io.BytesIO()
	images[0].save(out, format="PDF", save_all=True, append_images=images[1:], resolution=150.0)
	return out.getvalue(), len(images)


def _pdf_page_count(content_bytes):
	import io
	from pypdf import PdfReader

	return len(PdfReader(io.BytesIO(content_bytes)).pages)


def _convert_job(file_url, title, author, description, requested_by, category=None, cover_url=None, as_text=0):
	fname = frappe.db.get_value("File", {"file_url": file_url}, "name")
	fdoc = frappe.get_doc("File", fname)
	fmt, chapters, page_count = "Text", [], 0
	is_comic = (fdoc.file_name or "").lower().endswith(COMIC_EXTS)
	if is_comic:
		# join the page images into a PDF and swap the File's content for it,
		# so everything downstream sees a plain page-image book
		pdf_bytes, page_count = _comic_to_pdf(fdoc.get_content(), fdoc.file_name)
		new_name = fdoc.file_name.rsplit(".", 1)[0] + ".pdf"
		pdf_doc = frappe.get_doc({
			"doctype": "File", "file_name": new_name, "is_private": 1, "content": pdf_bytes,
		}).insert(ignore_permissions=True)
		file_url = pdf_doc.file_url
		fdoc = pdf_doc
		fname = pdf_doc.name
		fmt = "PDF"
		category = category or "Comic"
	if is_comic:
		pass  # already a page-image PDF with its page_count; nothing else to convert
	elif (fdoc.file_name or "").lower().endswith(".epub"):
		chapters, meta_title, meta_author = _epub_to_chapters(fdoc.get_content())
		title = title or meta_title
		author = author or meta_author
	elif cint(as_text):
		# the old path: extract the words and lose the layout. Kept for the
		# rare PDF that is really just prose and wanted in the flowing reader.
		chapters, method = _pdf_to_chapters(fdoc.get_content())
	else:
		# A PDF's meaning is in its layout — tables, code, figures, columns —
		# and text extraction throws that away by design. Keep the file and
		# let the browser render the pages.
		fmt = "PDF"
		page_count = _pdf_page_count(fdoc.get_content())
		if not page_count:
			frappe.throw(_("This PDF has no pages."))
	book = frappe.get_doc(
		{
			"doctype": "Duty Book",
			"title": (title or fdoc.file_name.rsplit(".", 1)[0])[:140],
			"author": (author or "")[:140] or None,
			"description": (description or "")[:500] or None,
			"category": (category or "")[:80] or None,
			"active": 1,
			"format": fmt,
			"source_file": file_url if fmt == "PDF" else None,
			"page_count": page_count,
			"chapter_count": len(chapters),
			"reading_direction": "Right to left" if (is_comic and _looks_manga(title, description)) else "Left to right",
		}
	).insert(ignore_permissions=True)
	if fmt == "PDF":
		# the File was uploaded loose; attach it so it is not orphaned
		frappe.db.set_value("File", fname, {"attached_to_doctype": "Duty Book", "attached_to_name": book.name,
											"attached_to_field": "source_file"}, update_modified=False)
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
			(_("“{0}” — {1} pages, on the shelf.").format(book.title, page_count) if fmt == "PDF"
			 else _("“{0}” — {1} chapters, on the shelf.").format(book.title, len(chapters))),
		)
	except Exception:
		pass


@frappe.whitelist()
def convert_pdf(file_url, title=None, author=None, description=None, category=None, cover_url=None, as_text=0):
	"""Managers: put an uploaded PDF/ePub on the shelf (background job).
	PDFs are kept as pages unless as_text=1 asks for the old text extraction."""
	require_sysadmin()
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
		as_text=cint(as_text),
		requested_by=frappe.session.user,
	)
	return {"queued": 1}


@frappe.whitelist()
def delete_book(book):
	require_sysadmin()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("Only managers manage the Library."), frappe.PermissionError)
	for c in frappe.get_all("Duty Book Chapter", filters={"book": book}, pluck="name"):
		frappe.delete_doc("Duty Book Chapter", c, ignore_permissions=True, force=True)
	for p in frappe.get_all("Duty Book Progress", filters={"book": book}, pluck="name"):
		frappe.delete_doc("Duty Book Progress", p, ignore_permissions=True, force=True)
	for bm in frappe.get_all("Duty Book Bookmark", filters={"book": book}, pluck="name"):
		frappe.delete_doc("Duty Book Bookmark", bm, ignore_permissions=True, force=True)
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
	require_sysadmin()
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
	require_sysadmin()
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
	require_sysadmin()
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
def set_cover(book, file_url=None, data_b64=None, clear=0):
	"""Managers: set a book's cover by hand. Either an already-uploaded File
	(file_url) or raw image bytes (data_b64 — how the reader sends a PDF's
	first page). The image is re-saved as a public File attached to the book
	so every reader's browser can load it; an upload left private would show
	only for whoever uploaded it."""
	require_sysadmin()
	from duty_board.uat import _is_manager

	if not _is_manager():
		frappe.throw(_("Only managers manage the Library."), frappe.PermissionError)
	if not frappe.db.exists("Duty Book", book):
		frappe.throw(_("Book not found."))
	if cint(clear):
		frappe.db.set_value("Duty Book", book, "cover", None, update_modified=False)
		frappe.db.commit()
		return {"ok": 1, "cover": None}

	content, ext = None, "jpg"
	if data_b64:
		import base64

		raw = data_b64.split(",", 1)[1] if data_b64.startswith("data:") else data_b64
		content = base64.b64decode(raw)
		ext = "png" if content[:8] == b"\x89PNG\r\n\x1a\n" else "jpg"
	elif file_url:
		fname = frappe.db.get_value("File", {"file_url": file_url}, "name")
		if not fname:
			frappe.throw(_("Upload the image first."))
		fdoc = frappe.get_doc("File", fname)
		content = fdoc.get_content()
		ext = (fdoc.file_name or "").rsplit(".", 1)[-1].lower() or "jpg"
		if ext not in ("jpg", "jpeg", "png", "webp"):
			frappe.throw(_("Covers must be JPG, PNG or WebP."))
	if not content:
		frappe.throw(_("No image received."))
	if len(content) > 3 * 1024 * 1024:
		frappe.throw(_("Keep the cover under 3 MB."))
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"cover-{book}.{ext}",
			"is_private": 0,
			"content": content,
			"attached_to_doctype": "Duty Book",
			"attached_to_name": book,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value("Duty Book", book, "cover", f.file_url, update_modified=False)
	frappe.db.commit()
	return {"ok": 1, "cover": f.file_url}


@frappe.whitelist()
def apply_book_meta(book, title=None, author=None, description=None, category=None, cover_url=None):
	"""Enrich an existing shelved book from a picked search match."""
	require_sysadmin()
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
	require_sysadmin()
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
	require_sysadmin()
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
	require_sysadmin()
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
	require_sysadmin()
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
	require_sysadmin()
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
	require_sysadmin()
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
def bookmark_add(book, chapter=None, scroll_pct=0, note=None, page=None):
	require_sysadmin()
	if not chapter and not page:
		frappe.throw(_("A bookmark needs a chapter or a page."))
	frappe.get_doc({
		"doctype": "Duty Book Bookmark",
		"user": frappe.session.user,
		"book": book,
		"chapter": chapter or None,
		"page": cint(page) or None,
		"scroll_pct": flt(scroll_pct),
		"note": (note or "")[:300] or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return bookmarks(book)


@frappe.whitelist()
def bookmark_remove(name):
	require_sysadmin()
	doc = frappe.get_doc("Duty Book Bookmark", name)
	if doc.user != frappe.session.user:
		frappe.throw(_("Not your bookmark."), frappe.PermissionError)
	frappe.delete_doc("Duty Book Bookmark", name, ignore_permissions=True)
	frappe.db.commit()
	return bookmarks(doc.book)


@frappe.whitelist()
def bookmarks(book):
	"""The caller's ribbons in one book, chapter-ordered."""
	require_sysadmin()
	return frappe.db.sql(
		"""
		select b.name, b.chapter, b.page, b.scroll_pct, b.note, b.creation,
		       c.title as ch_title, c.idx_no
		from `tabDuty Book Bookmark` b
		left join `tabDuty Book Chapter` c on c.name = b.chapter
		where b.book = %s and b.user = %s
		order by coalesce(c.idx_no, b.page) asc, b.scroll_pct asc
		""",
		(book, frappe.session.user),
		as_dict=True,
	)


# ───────────────────────────── the reading plan ──────────────────────────────
#
# A personal library of a thousand books curated one at a time needs something
# a shelf cannot give: a record of what you INTEND, made at the moment you make
# the decision. Curation is the process, so the intent is captured when the book
# lands rather than in a planning screen nobody remembers to open.
#
# Three decisions worth keeping:
#
#   REFERENCE IS EXCLUDED. A book kept to be searched rather than read has no
#   place in a plan — including it would turn the plan into a catalogue, which
#   is exactly what makes reading plans get abandoned.
#
#   THE WHEN IS A MONTH, NOT A DATE. A hard due date turns reading into homework
#   and gets ignored within a fortnight. YYYY-MM is soft enough to be honest and
#   specific enough to sort.
#
#   RE-READS ARE ROWS, NOT A COUNTER. The interesting question about a re-read is
#   when, and what it gave you that time. A counter cannot hold either, and a
#   book that was a 3 at thirty and a 5 at forty is the whole point of keeping it.

PLAN_STATUSES = ("To read", "Reading", "Read", "Abandoned")


def _month_key(d=None):
	d = d or frappe.utils.nowdate()
	return str(d)[:7]


@frappe.whitelist()
def reading_plan(month=None):
	"""The plan: due now, overdue, coming, and due to revisit.

	One query for the books and one for the reads — never per book, because this
	has to stay usable at a thousand.
	"""
	require_sysadmin()
	now = _month_key(month)
	today = frappe.utils.nowdate()

	books = frappe.get_all(
		"Duty Book",
		filters={"active": 1},
		fields=["name", "title", "author", "category", "cover", "chapter_count",
				"shelf_status", "plan_month", "plan_note", "revisit_after",
				"times_read", "last_finished"],
		order_by="plan_month asc, title asc",
		limit_page_length=0,
	)

	prog = {}
	for p in frappe.get_all(
		"Duty Book Progress",
		filters={"user": frappe.session.user},
		fields=["book", "chapter", "chapters_done", "last_read_at"],
		limit_page_length=0,
	):
		prog[p.book] = p

	out = {"this_month": [], "overdue": [], "upcoming": [], "revisit": [],
		   "reading": [], "unplanned": 0, "reference": 0, "month": now}

	for b in books:
		if b.shelf_status == "Reference":
			out["reference"] += 1
			continue
		p = prog.get(b.name)
		done = len([c for c in ((p.chapters_done if p else "") or "").split(",") if c])
		b.pct = int(done * 100 / b.chapter_count) if b.chapter_count else 0
		b.resume_chapter = p.chapter if p else None
		b.last_read_at = str(p.last_read_at)[:16] if p and p.last_read_at else None

		if b.shelf_status == "Reading":
			out["reading"].append(b)
			continue
		if b.revisit_after and str(b.revisit_after) <= today and b.shelf_status == "Read":
			out["revisit"].append(b)
			continue
		if b.shelf_status != "To read":
			continue
		if not b.plan_month:
			out["unplanned"] += 1
			continue
		if b.plan_month < now:
			out["overdue"].append(b)
		elif b.plan_month == now:
			out["this_month"].append(b)
		else:
			out["upcoming"].append(b)

	out["upcoming"] = out["upcoming"][:20]
	return out


@frappe.whitelist()
def set_book_plan(book, shelf_status=None, plan_month=None, plan_note=None, revisit_after=None):
	"""Set intent on a book. Called at curation time and whenever it changes."""
	require_sysadmin()
	doc = frappe.get_doc("Duty Book", book)
	if shelf_status is not None:
		if shelf_status not in list(PLAN_STATUSES) + ["Reference"]:
			frappe.throw(_("Unknown status."))
		doc.shelf_status = shelf_status
	if plan_month is not None:
		pm = (plan_month or "").strip()
		if pm and not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", pm):
			frappe.throw(_("Planned month should look like 2027-03."))
		doc.plan_month = pm or None
	if plan_note is not None:
		doc.plan_note = (plan_note or "").strip() or None
	if revisit_after is not None:
		doc.revisit_after = revisit_after or None
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def start_reading(book):
	"""Open a reading. Idempotent — re-opening an unfinished one does nothing."""
	require_sysadmin()
	doc = frappe.get_doc("Duty Book", book)
	if not any(r for r in (doc.reads or []) if not r.finished_on):
		doc.append("reads", {"started_on": frappe.utils.nowdate()})
	doc.shelf_status = "Reading"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


@frappe.whitelist()
def finish_reading(book, note=None, rating=None, revisit_after=None):
	"""Close the open reading, or record one that was never opened."""
	require_sysadmin()
	doc = frappe.get_doc("Duty Book", book)
	open_row = next((r for r in (doc.reads or []) if not r.finished_on), None)
	if not open_row:
		open_row = doc.append("reads", {"started_on": frappe.utils.nowdate()})
	open_row.finished_on = frappe.utils.nowdate()
	if note:
		open_row.note = note.strip()[:2000]
	if rating:
		open_row.rating = cint(rating)
	doc.shelf_status = "Read"
	doc.plan_month = None
	if revisit_after:
		doc.revisit_after = revisit_after
	finished = [r for r in doc.reads if r.finished_on]
	doc.times_read = len(finished)
	doc.last_finished = max(str(r.finished_on) for r in finished)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1, "times_read": doc.times_read}


def revisit_nudge():
	"""Monthly: books that have come due for another pass.

	Monthly rather than daily on purpose — a revisit is not urgent, and a nudge
	that arrives often enough to be ignored is worse than none.

	cron: 0 8 1 * *
	"""
	from duty_board.notify import _kv, _send, _shell

	today = frappe.utils.nowdate()
	rows = frappe.get_all(
		"Duty Book",
		filters={"active": 1, "shelf_status": "Read",
				 "revisit_after": ["<=", today]},
		fields=["name", "title", "author", "last_finished", "times_read"],
		order_by="revisit_after asc",
		limit_page_length=0,
	)
	if not rows:
		return
	admins = frappe.get_all(
		"Has Role", filters={"role": "System Manager", "parenttype": "User"}, pluck="parent"
	)
	admins = [a for a in set(admins)
			  if a not in ("Administrator", "Guest") and frappe.db.get_value("User", a, "enabled")]
	if not admins:
		return
	body = "".join(
		f'<tr><td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px;font-weight:700">'
		f'{frappe.utils.escape_html(r.title[:60])}<br>'
		f'<span style="color:#8A9994;font-weight:500">{frappe.utils.escape_html(r.author or "")}</span></td>'
		f'<td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px">{r.last_finished or "—"}</td>'
		f'<td style="padding:7px 10px;border-bottom:1px solid #EDF2EF;font-size:12px">{cint(r.times_read) or 1}\u00d7</td></tr>'
		for r in rows[:25]
	)
	inner = (
		f'<p style="font-size:13.5px">{_("<b>{0} book(s)</b> have come due for another pass.").format(len(rows))}</p>'
		'<table style="border-collapse:collapse;width:100%">'
		f'<tr><th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Book")}</th>'
		f'<th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Last read")}</th>'
		f'<th style="text-align:left;padding:7px 10px;font-size:11px;color:#65736F">{_("Times")}</th></tr>'
		f"{body}</table>"
	)
	for u in admins:
		_send(u, f"[Library] {len(rows)} book(s) due for a revisit", _shell(_("Worth another pass"), inner))


# ───────────────────── authors, topics and collected highlights ──────────────
#
# The library's author and category were plain Data fields: one category per
# book, and 'Drucker', 'Peter Drucker' and 'P. Drucker' as three different
# people with no way to gather anything under one of them. Links autocomplete,
# so drift stops at entry rather than being cleaned up later, and a book can
# carry the several topics it actually belongs to.
#
# The old fields are kept and maintained alongside — they are what the shelf
# tile and every existing view already read, and rewriting all of that to prove
# a point would risk more than it gains.


@frappe.whitelist()
def backfill_authors_topics(dry_run=1):
	"""Create Author and Topic records from the existing freehand fields.

	Run once after migrating. Idempotent: a second run finds everything already
	linked and does nothing. Splits on the usual separators so 'Kahneman &
	Tversky' becomes two authors rather than one oddly named one.

	bench --site <site> execute duty_board.library.backfill_authors_topics
	bench --site <site> execute duty_board.library.backfill_authors_topics --kwargs "{'dry_run': 0}"
	"""
	require_sysadmin()
	dry = cint(dry_run)
	made_a = made_t = linked = 0
	for b in frappe.get_all("Duty Book", fields=["name", "author", "category"], limit_page_length=0):
		doc = frappe.get_doc("Duty Book", b.name)
		changed = False
		if not (doc.authors or []) and (b.author or "").strip():
			for a in _split_names(b.author):
				if not frappe.db.exists("Duty Author", a):
					made_a += 1
					if not dry:
						frappe.get_doc({"doctype": "Duty Author", "author_name": a}).insert(
							ignore_permissions=True
						)
				if not dry:
					doc.append("authors", {"author": a})
				changed = True
		if not (doc.topics or []) and (b.category or "").strip():
			for t in _split_names(b.category):
				if not frappe.db.exists("Duty Topic", t):
					made_t += 1
					if not dry:
						frappe.get_doc({"doctype": "Duty Topic", "topic_name": t}).insert(
							ignore_permissions=True
						)
				if not dry:
					doc.append("topics", {"topic": t})
				changed = True
		if changed:
			linked += 1
			if not dry:
				doc.save(ignore_permissions=True)
	if not dry:
		frappe.db.commit()
	print(
		"%s: %d author(s), %d topic(s) created; %d book(s) linked"
		% ("DRY RUN" if dry else "DONE", made_a, made_t, linked)
	)
	if dry:
		print('Re-run with --kwargs "{\'dry_run\': 0}" to apply.')
	return {"authors": made_a, "topics": made_t, "books": linked}


def _split_names(raw):
	"""Split a freehand author line into people.

	Commas DO separate authors — that is how most of a real shelf is written.
	The first version refused to split on them, protecting the rarer
	'Surname, Firstname' form and getting the common case wrong.

	Both are now handled by looking at the shape rather than picking one rule:
	exactly two comma-parts where the second is one or two short words with no
	surname-like length is read as an inverted single name ('Drucker, Peter'),
	and everything else is read as a list.
	"""
	raw = (raw or "").strip()
	if not raw:
		return []
	# ampersands, semicolons, slashes and the word 'and' always separate
	chunks = re.split(r"\s*(?:&|;|/|\band\b|\bwith\b)\s*", raw, flags=re.I)
	out = []
	for chunk in chunks:
		chunk = chunk.strip()
		if not chunk:
			continue
		# strip spaces and trailing commas but NOT full stops — an initial is
		# 'P.' and losing the stop turns it into a different name
		parts = [p.strip(" ,") for p in chunk.split(",") if p.strip(" ,")]
		if len(parts) == 2 and _looks_inverted(parts[0], parts[1]):
			out.append("{1} {0}".format(parts[0], parts[1]))
		else:
			out.extend(parts)
	seen = []
	for n in out:
		n = re.sub(r"\s+", " ", n).strip(" ,")
		if n and n.lower() not in [x.lower() for x in seen]:
			seen.append(n)
	return seen[:8]


def _looks_inverted(first, second):
	"""'Drucker, Peter' — a surname then given names, rather than two people.

	The tell is that the second part is one or two given names with no
	connecting words. 'Drucker, Peter' inverts; 'Kahneman, Daniel Tversky' does
	not, and neither does anything with three or more words after the comma.
	"""
	words = second.split()
	if not 1 <= len(words) <= 2:
		return False
	# initials such as 'P.' or 'P. F.' are a strong signal of an inverted name
	if all(re.fullmatch(r"[A-Z]\.?", w) for w in words):
		return True
	# a single given name after a single surname
	return len(first.split()) == 1 and len(words) == 1



@frappe.whitelist()
def set_book_taxonomy(book, authors=None, topics=None):
	"""Replace a book's authors and topics. Creates any name not seen before."""
	require_sysadmin()
	doc = frappe.get_doc("Duty Book", book)
	if authors is not None:
		# run the typed line through the same splitter the backfill uses, so a
		# name entered by hand and one read from an epub end up identical
		names = []
		for raw in _as_list(authors):
			for n in _split_names(raw) or [raw]:
				if n not in names:
					names.append(n)
		doc.set("authors", [])
		for a in names:
			if not frappe.db.exists("Duty Author", a):
				frappe.get_doc({"doctype": "Duty Author", "author_name": a}).insert(
					ignore_permissions=True
				)
			doc.append("authors", {"author": a})
		# the freehand line stays in step so the shelf tile keeps working
		doc.author = ", ".join(names)
	if topics is not None:
		names = _as_list(topics)
		doc.set("topics", [])
		for t in names:
			if not frappe.db.exists("Duty Topic", t):
				frappe.get_doc({"doctype": "Duty Topic", "topic_name": t}).insert(
					ignore_permissions=True
				)
			doc.append("topics", {"topic": t})
		if names:
			doc.category = names[0]
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": 1}


def _as_list(v):
	if isinstance(v, str):
		try:
			v = frappe.parse_json(v)
		except Exception:
			v = [x.strip() for x in v.split(",")]
	out = []
	for x in v or []:
		x = (x or "").strip()
		if x and x not in out:
			out.append(x)
	return out[:12]


@frappe.whitelist()
def taxonomy():
	"""Every author and topic with a count, for the browse facets."""
	require_sysadmin()
	auth = frappe.db.sql(
		"""select ba.author as name, count(*) as n
		   from `tabDuty Book Author` ba
		   join `tabDuty Book` b on b.name = ba.parent and b.active = 1
		   group by ba.author order by n desc, ba.author asc""",
		as_dict=True,
	)
	top = frappe.db.sql(
		"""select bt.topic as name, count(*) as n
		   from `tabDuty Book Topic` bt
		   join `tabDuty Book` b on b.name = bt.parent and b.active = 1
		   group by bt.topic order by n desc, bt.topic asc""",
		as_dict=True,
	)
	return {"authors": auth, "topics": top}


@frappe.whitelist()
def my_highlights(book=None, q=None, limit=200):
	"""Every highlight across the library, newest first.

	Stored per book and never shown together, which meant the most valuable
	thing a personal library produces — the distillate of everything you thought
	worth keeping — existed only inside individual books.
	"""
	require_sysadmin()
	filters = {"user": frappe.session.user}
	if book:
		filters["book"] = book
	rows = frappe.get_all(
		"Duty Book Highlight",
		filters=filters,
		fields=["name", "book", "chapter", "text", "note", "creation"],
		order_by="creation desc",
		limit_page_length=cint(limit) or 200,
	)
	needle = (q or "").strip().lower()
	if needle:
		rows = [
			r for r in rows
			if needle in (r.text or "").lower() or needle in (r.note or "").lower()
		]
	titles = {}
	if rows:
		for b in frappe.get_all(
			"Duty Book",
			filters={"name": ["in", list({r.book for r in rows})]},
			fields=["name", "title", "author"],
		):
			titles[b.name] = b
	ch_titles = {}
	chapters = list({r.chapter for r in rows if r.chapter})
	if chapters:
		for c in frappe.get_all(
			"Duty Book Chapter", filters={"name": ["in", chapters]},
			fields=["name", "title", "idx_no"]
		):
			ch_titles[c.name] = c
	for r in rows:
		bb = titles.get(r.book) or frappe._dict()
		r.book_title = bb.get("title")
		r.book_author = bb.get("author")
		cc = ch_titles.get(r.chapter) or frappe._dict()
		r.chapter_title = cc.get("title")
		r.chapter_no = cc.get("idx_no")
		r.on = str(r.creation)[:10]
	return {"highlights": rows, "total": len(rows)}
