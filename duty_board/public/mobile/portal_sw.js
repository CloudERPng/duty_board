/* Xlevel client portal service worker: push antenna + notification tap. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
self.addEventListener("push", (event) => {
	let data = {};
	try {
		data = event.data ? event.data.json() : {};
	} catch (e) {
		data = { title: "Xlevel", body: event.data ? event.data.text() : "" };
	}
	event.waitUntil(
		self.registration.showNotification(data.title || "Xlevel", {
			body: data.body || "",
			icon: "/assets/duty_board/mobile/icon-192.png",
			badge: "/assets/duty_board/mobile/icon-192.png",
			tag: data.tag || "xlevel-portal",
			renotify: true,
			vibrate: [180, 60, 180],
		})
	);
});
self.addEventListener("notificationclick", (event) => {
	event.notification.close();
	event.waitUntil(
		self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
			for (const c of list) {
				if (c.url.includes("/portal")) return c.focus();
			}
			return self.clients.openWindow("/portal");
		})
	);
});
