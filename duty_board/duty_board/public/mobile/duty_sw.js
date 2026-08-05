/* Duty Board service worker: push + notification click */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
	let d = {};
	try {
		d = e.data.json();
	} catch (err) {
		d = { body: e.data ? e.data.text() : "" };
	}
	e.waitUntil(
		self.registration.showNotification(d.title || "Duty Board", {
			body: d.body || "",
			icon: "/assets/duty_board/mobile/icon-192.png",
			badge: "/assets/duty_board/mobile/icon-192.png",
			data: { url: "/app/duty-board" },
		})
	);
});

self.addEventListener("notificationclick", (e) => {
	e.notification.close();
	e.waitUntil(
		clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
			for (const c of list) {
				if ("focus" in c) {
					c.navigate("/app/duty-board");
					return c.focus();
				}
			}
			return clients.openWindow("/app/duty-board");
		})
	);
});
