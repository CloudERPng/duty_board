/* Xlevel Library service worker — offline reading.
   The shelf and each opened book are cached in localStorage by the page; this
   worker caches the app shell (the /library HTML and the pdf.js assets) so the
   reader opens with no signal. It never caches the API — the page handles that
   itself and falls back to its saved copy — so progress is always live when
   online and read-only from cache when not. */
const SHELL = "xlevel-reader-shell-v1";
const ASSETS = [
	"/reader",
	"/assets/duty_board/pdfjs/pdf.min.js",
	"/assets/duty_board/pdfjs/pdf.worker.min.js",
	"/assets/duty_board/mobile/icon-192.png",
];

self.addEventListener("install", (e) => {
	self.skipWaiting();
	e.waitUntil(caches.open(SHELL).then((c) => c.addAll(ASSETS).catch(() => {})));
});
self.addEventListener("activate", (e) => {
	e.waitUntil(
		caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== SHELL).map((k) => caches.delete(k)))).then(() => self.clients.claim())
	);
});
self.addEventListener("fetch", (event) => {
	const req = event.request;
	if (req.method !== "GET") return;
	const url = new URL(req.url);
	// never touch the API or cross-origin — let the page manage those
	if (url.pathname.startsWith("/api/") || url.origin !== self.location.origin) return;
	// app shell + assets: cache first, fall back to network, then update the cache
	if (url.pathname === "/reader" || url.pathname.startsWith("/assets/duty_board/pdfjs/") || url.pathname.startsWith("/assets/duty_board/mobile/")) {
		event.respondWith(
			caches.match(req).then((hit) =>
				hit || fetch(req).then((res) => {
					const copy = res.clone();
					caches.open(SHELL).then((c) => c.put(req, copy)).catch(() => {});
					return res;
				}).catch(() => hit)
			)
		);
	}
	// book cover images: cache them as they are read, so a saved book shows its cover offline
	else if (/\.(png|jpg|jpeg|webp|gif)$/i.test(url.pathname) && url.pathname.startsWith("/files/")) {
		event.respondWith(
			caches.match(req).then((hit) => hit || fetch(req).then((res) => {
				const copy = res.clone();
				caches.open(SHELL).then((c) => c.put(req, copy)).catch(() => {});
				return res;
			}).catch(() => hit))
		);
	}
});
