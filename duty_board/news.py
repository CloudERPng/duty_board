# Copyright (c) 2026, Xlevel Retail Systems Ltd
"""The staff news feed — a daily magazine for accounting, finance, SaaS
and IT, ingested from RSS/Atom. Images come from the feeds themselves or
from each article's og:image (the picture publishers choose for sharing).
Full articles stay at the source — the reader shows the feed's own
summary and a Read-at-source link. Copyright stays clean; attention
comes home."""

import hashlib
import re
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime, today

from duty_board.permissions import require_staff_or_consultant

DEFAULT_FEEDS = [
	("Accounting", "https://www.accountingtoday.com/feed?rss=true"),
	("Finance", "https://www.cfodive.com/feeds/news/"),
	("SaaS", "https://techcrunch.com/feed/"),
	("IT", "https://www.theregister.com/headlines.atom"),
	("Africa Tech", "https://techcabal.com/feed/"),
	("Business NG", "https://nairametrics.com/feed/"),
]

UA = {"User-Agent": "Mozilla/5.0 (compatible; DutyBoardNews/1.0)"}
CACHE_KEY = "duty_news_refreshed_at"
CACHE_MINUTES = 120
ROTATE_N = 12
CURSOR_KEY = "duty_news_cursor"
KEEP_DAYS = 14


def _feeds():
	raw = frappe.db.get_single_value("Duty Settings", "news_feeds") or ""
	out = []
	for line in raw.splitlines():
		if "|" in line:
			cat, url = line.split("|", 1)
			if url.strip().startswith("http"):
				out.append((cat.strip() or "News", url.strip()))
	return out or DEFAULT_FEEDS


def _get(url, limit=400_000, timeout=6):
	req = urllib.request.Request(url, headers=UA)
	with urllib.request.urlopen(req, timeout=timeout) as r:
		return r.read(limit)


def _strip_html(s):
	s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s or "", flags=re.S | re.I)
	s = re.sub(r"<[^>]+>", " ", s)
	s = re.sub(r"&nbsp;", " ", s)
	s = re.sub(r"&amp;", "&", s)
	s = re.sub(r"&#8217;|&rsquo;", "'", s)
	s = re.sub(r"&quot;|&#8220;|&#8221;|&ldquo;|&rdquo;", '"', s)
	s = re.sub(r"\s+", " ", s).strip()
	return s


def _imgs_in(html):
	return re.findall(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html or "", flags=re.I)


def _og_image(link):
	try:
		head = _get(link, limit=60_000, timeout=5).decode("utf-8", "ignore")
		m = re.search(
			r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', head, re.I
		) or re.search(
			r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', head, re.I
		)
		return m.group(1) if m else None
	except Exception:
		return None


def _text(el, *tags):
	for t in tags:
		x = el.find(t)
		if x is not None and (x.text or "").strip():
			return x.text.strip()
	return ""


def _parse(xml_bytes, category):
	"""RSS 2.0 and Atom, namespace-tolerant."""
	xml_s = re.sub(rb'xmlns="[^"]+"', b"", xml_bytes, count=1)  # default-ns removal for Atom
	root = ET.fromstring(xml_s)
	items = []
	channel_title = ""
	ch = root.find("channel")
	nodes = []
	if ch is not None:  # RSS
		channel_title = _text(ch, "title")
		nodes = ch.findall("item")
	else:  # Atom
		channel_title = _text(root, "title")
		nodes = root.findall("entry")
	for n in nodes[:25]:
		title = _strip_html(_text(n, "title"))[:290]
		link = _text(n, "link")
		if not link:  # Atom link href
			ln = n.find("link")
			if ln is not None:
				link = ln.get("href") or ""
		desc = ""
		for tag in ("description", "summary"):
			d = n.find(tag)
			if d is not None and d.text:
				desc = d.text
				break
		content = ""
		for c in n.iter():
			if c.tag.endswith("encoded") or c.tag.endswith("}content") or c.tag == "content":
				content = c.text or ""
				if content:
					break
		img = None
		for c in n.iter():
			tag = c.tag.lower()
			if tag.endswith("}content") or tag.endswith("}thumbnail") or tag == "enclosure":
				u = c.get("url") or ""
				if u.startswith("http") and (
					"image" in (c.get("type") or "") or re.search(r"\.(jpe?g|png|webp|gif)", u, re.I) or tag.endswith("thumbnail") or tag.endswith("}content")
				):
					img = u
					break
		body_imgs = _imgs_in(content or desc)
		if not img and body_imgs:
			img = body_imgs[0]
		pub = _text(n, "pubDate", "published", "updated")
		when = None
		if pub:
			try:
				when = parsedate_to_datetime(pub).replace(tzinfo=None)
			except Exception:
				try:
					when = frappe.utils.get_datetime(pub[:19].replace("T", " "))
				except Exception:
					when = None
		summary = _strip_html(content or desc)[:1400]
		if title and link:
			items.append({
				"title": title,
				"link": link[:490],
				"category": category,
				"source": _strip_html(channel_title)[:80],
				"image": (img or "")[:490],
				"extra": "\n".join(dict.fromkeys(body_imgs[1:4])),
				"published": when,
				"summary": summary,
			})
	return items


def _refresh(feed_slice=None):
	total = 0
	for category, url in feed_slice if feed_slice is not None else _feeds():
		try:
			items = _parse(_get(url), category)
		except Exception:
			continue
		for it in items:
			guid = hashlib.md5(it["link"].encode()).hexdigest()
			if frappe.db.exists("Duty News Item", {"guid": guid}):
				continue
			if not it["image"]:
				it["image"] = (_og_image(it["link"]) or "")[:490]
			try:
				frappe.get_doc({
					"doctype": "Duty News Item",
					"guid": guid,
					"title": it["title"],
					"link": it["link"],
					"source": it["source"],
					"category": it["category"],
					"image": it["image"],
					"published": it["published"] or now_datetime(),
					"summary": it["summary"],
					"extra_images": it["extra"],
				}).insert(ignore_permissions=True)
				total += 1
			except Exception:
				pass
	# prune the old
	frappe.db.delete("Duty News Item", {"published": ["<", add_days(today(), -KEEP_DAYS)]})
	frappe.db.commit()
	return total


def refresh_rotation():
	"""Background worker: harvest the NEXT ROTATE_N feeds, round-robin.
	The cursor persists in DefaultValue, so the cycle survives restarts;
	with ~40 feeds and a 2h cadence the whole set turns over in ~7h while
	every round still lands fresh stories."""
	feeds = _feeds()
	if not feeds:
		return
	try:
		cur = cint(frappe.db.get_default(CURSOR_KEY) or 0) % len(feeds)
	except Exception:
		cur = 0
	ring = feeds[cur:] + feeds[:cur]
	batch = ring[:ROTATE_N]
	frappe.db.set_default(CURSOR_KEY, (cur + len(batch)) % len(feeds))
	frappe.db.commit()
	_refresh(batch)


@frappe.whitelist()
def get_news(category=None, force=None):
	"""The stand: instant from the shelf; a stale shelf enqueues the
	rotating harvest in the background so no reader ever pays for it.
	Only a completely empty stand (day one) harvests a starter batch
	inline."""
	require_staff_or_consultant()
	last = frappe.cache().get_value(CACHE_KEY)
	stale = True
	if last and not cint(force):
		try:
			stale = (now_datetime() - frappe.utils.get_datetime(last)).total_seconds() > CACHE_MINUTES * 60
		except Exception:
			stale = True
	if stale or cint(force):
		frappe.cache().set_value(CACHE_KEY, str(now_datetime()))
		if not frappe.db.count("Duty News Item"):
			try:
				_refresh(_feeds()[:6])
			except Exception:
				frappe.log_error(frappe.get_traceback()[-1500:], "news bootstrap")
		else:
			try:
				frappe.enqueue(
					"duty_board.news.refresh_rotation",
					queue="default",
					job_name="duty_news_rotation",
				)
			except Exception:
				frappe.log_error(frappe.get_traceback()[-1500:], "news enqueue")
	filters = {"category": category} if category and category != "All" else {}
	rows = frappe.get_all(
		"Duty News Item",
		filters=filters,
		fields=["name", "title", "source", "category", "link", "image", "published", "summary", "extra_images"],
		order_by="published desc",
		limit=60,
	)
	cats = sorted({r.category for r in frappe.get_all("Duty News Item", fields=["category"], distinct=True) if r.category})
	return {
		"items": [
			{
				"name": r.name, "title": r.title, "source": r.source,
				"category": r.category, "link": r.link, "image": r.image,
				"published": str(r.published)[:16] if r.published else "",
				"summary": r.summary or "",
				"extra_images": [u for u in (r.extra_images or "").splitlines() if u.startswith("http")],
			}
			for r in rows
		],
		"categories": cats,
	}
