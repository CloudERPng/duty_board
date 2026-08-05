/* Xlevel portal: drafts survive re-renders. Every keystroke in the
   composer (or any textarea) mirrors into memory; a short guard
   restores any draft found wiped while the field is empty and
   unfocused. */
(function () {
	var D = {};
	var intent = 0;
	document.addEventListener("input", function (e) {
		var t = e.target;
		if (!t) return;
		if (t.id === "text" || t.tagName === "TEXTAREA") {
			D[t.id || t.className || "ta"] = t.value;
		}
	});
	document.addEventListener("click", function () { intent = Date.now(); });
	document.addEventListener("keydown", function (e) { if (e.key === "Enter") intent = Date.now(); });
	setInterval(function () {
		var els = [].slice.call(document.querySelectorAll("#text, textarea"));
		els.forEach(function (el) {
			var k = el.id || el.className || "ta";
			if (!D[k] || el.value || document.activeElement === el) return;
			if (Date.now() - intent < 2500) delete D[k]; // sent or cleared on purpose
			else el.value = D[k]; // wiped by a re-render — bring it back
		});
	}, 700);
})();
