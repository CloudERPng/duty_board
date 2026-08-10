#!/usr/bin/env python3
"""Duty Board v3.79.0 — file attachments on project tasks.

Tasks had nowhere for evidence — screenshots, client documents, config
exports. Now:

- Multiple files per task, uploaded from the task card (📎 section:
  chips + an Add files button, multi-select). Standard Frappe File
  rows (attached_to Duty Project Task, private) via the same
  upload_file pattern chat already uses.
- CLICK TO VIEW, not download: images render in a preview dialog,
  PDFs render in an inline viewer dialog (iframe), other types open in
  a browser tab — the browser decides, nothing forces a download.
- 🗑 per file on the card (staff).
- Board cards show a 📎 n count chip when a task has files (batched
  into the existing board query block — no extra round trips).
- get_card returns the file list alongside everything else.

No schema (File is core). bench build --app duty_board && bench
restart. Anchored, idempotent. Requires v3.78.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import os
import sys

INIT = "duty_board/__init__.py"
JS = "duty_board/duty_board/page/duty_board/duty_board.js"
PROJ = "duty_board/projects.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1. board: batched attach counts ----------------------------------------
BC_OLD = '''\t\tfor a in frappe.get_all(
\t\t\t"Work Session",
\t\t\tfilters={"project_task": ["in", names]},
\t\t\tfields=["project_task", "sum(duration) as secs"],
\t\t\tgroup_by="project_task",
\t\t):
\t\t\tactual_secs[a.project_task] = a.secs or 0'''
BC_NEW = '''\t\tfor a in frappe.get_all(
\t\t\t"Work Session",
\t\t\tfilters={"project_task": ["in", names]},
\t\t\tfields=["project_task", "sum(duration) as secs"],
\t\t\tgroup_by="project_task",
\t\t):
\t\t\tactual_secs[a.project_task] = a.secs or 0
\t\tfor fc in frappe.get_all(
\t\t\t"File",
\t\t\tfilters={"attached_to_doctype": "Duty Project Task", "attached_to_name": ["in", names]},
\t\t\tfields=["attached_to_name", "count(name) as cnt"],
\t\t\tgroup_by="attached_to_name",
\t\t):
\t\t\tfile_counts[fc.attached_to_name] = fc.cnt'''

BC2_OLD = '\tnote_counts, working, sub_counts, actual_secs = {}, {}, {}, {}'
BC2_NEW = '\tnote_counts, working, sub_counts, actual_secs, file_counts = {}, {}, {}, {}, {}'

BC3_OLD = '''\t\tt.actual_hours = round((actual_secs.get(t.name, 0) or 0) / 3600.0, 1)'''
BC3_NEW = '''\t\tt.actual_hours = round((actual_secs.get(t.name, 0) or 0) / 3600.0, 1)
\t\tt.file_count = file_counts.get(t.name, 0)'''

# --- 2. get_card: file list ---------------------------------------------------
GC_OLD = '''\t\t"estimate_hours": doc.estimate_hours,'''
GC_NEW = '''\t\t"estimate_hours": doc.estimate_hours,
\t\t"files": [
\t\t\t{
\t\t\t\t"name": f.name,
\t\t\t\t"file_name": f.file_name,
\t\t\t\t"file_url": f.file_url,
\t\t\t\t"kind": (
\t\t\t\t\t"image" if (f.file_name or "").lower().rsplit(".", 1)[-1] in ("png", "jpg", "jpeg", "gif", "webp")
\t\t\t\t\telse "pdf" if (f.file_name or "").lower().endswith(".pdf")
\t\t\t\t\telse "other"
\t\t\t\t),
\t\t\t}
\t\t\tfor f in frappe.get_all(
\t\t\t\t"File",
\t\t\t\tfilters={"attached_to_doctype": "Duty Project Task", "attached_to_name": name},
\t\t\t\tfields=["name", "file_name", "file_url"],
\t\t\t\torder_by="creation asc",
\t\t\t)
\t\t],'''

# --- 3. delete endpoint (after update_task's save) ---------------------------
DEL_ANCHOR = '''\tfrappe.publish_realtime("duty_board_note", {"kind": "card", "id": name})
\treturn get_card(name)'''
DEL_NEW = '''\tfrappe.publish_realtime("duty_board_note", {"kind": "card", "id": name})
\treturn get_card(name)


@frappe.whitelist()
def task_file_delete(name, file):
\t"""Remove one attachment from a task."""
\trequire_staff()
\trow = frappe.db.get_value(
\t\t"File", file, ["attached_to_doctype", "attached_to_name"], as_dict=True
\t)
\tif not row or row.attached_to_doctype != "Duty Project Task" or row.attached_to_name != name:
\t\tfrappe.throw(_("Not found."))
\tfrappe.delete_doc("File", file, ignore_permissions=True, force=True)
\tfrappe.db.commit()
\treturn get_card(name)'''

# --- 4. JS: 📎 section in the card (after the est-hours label) ---------------
FS_OLD = '''\t\t\t\t<label class="duty-ld-f"><span>⏱ ${__("Est. hours")}</span><input type="number" step="0.5" min="0" data-f="estimate_hours" value="${t.estimate_hours || ""}" placeholder="${__("e.g. 4")}">${t.actual_hours ? `<small class="duty-est-act ${t.estimate_hours && t.actual_hours > t.estimate_hours ? "over" : ""}">${__("logged")} ${t.actual_hours}h${t.estimate_hours ? ` / ${t.estimate_hours}h` : ""}</small>` : ""}</label>'''
FS_NEW = '''\t\t\t\t<label class="duty-ld-f"><span>⏱ ${__("Est. hours")}</span><input type="number" step="0.5" min="0" data-f="estimate_hours" value="${t.estimate_hours || ""}" placeholder="${__("e.g. 4")}">${t.actual_hours ? `<small class="duty-est-act ${t.estimate_hours && t.actual_hours > t.estimate_hours ? "over" : ""}">${__("logged")} ${t.actual_hours}h${t.estimate_hours ? ` / ${t.estimate_hours}h` : ""}</small>` : ""}</label>
\t\t\t\t<div class="duty-ld-files">
\t\t\t\t\t<span class="duty-ld-files-h">📎 ${__("Files")}</span>
\t\t\t\t\t<div class="duty-tf-list">${(t.files || []).map((f) => `<span class="duty-tf-chip" data-url="${f.file_url}" data-kind="${f.kind}" data-fn="${frappe.utils.escape_html(f.file_name || "")}">${f.kind === "image" ? "🖼" : f.kind === "pdf" ? "📄" : "📁"} ${frappe.utils.escape_html(f.file_name || "file")}<a class="duty-tf-del" data-file="${f.name}" title="${__("Remove")}">✕</a></span>`).join("")}</div>
\t\t\t\t\t<label class="btn btn-xs btn-default duty-tf-add">＋ ${__("Add files")}<input type="file" multiple style="display:none"></label>
\t\t\t\t</div>'''

# --- 5. JS: handlers — anchored on the card dialog's existing save binding ---
# We attach after the phase/blocked dropdowns are live; anchor the ENUMERATE
# comment zone via the first save call site opening (v.milestone line's parent
# is too deep) — instead use a unique nearby handler registration:
H_ANCHOR = None  # resolved at runtime below

HANDLERS = '''
\t\t// --- task file attachments: preview, upload, delete ---
\t\tconst tfReload = () => frappe.call({ method: "duty_board.projects.get_card", args: { name: t.name }, callback: (rr) => { if (rr.message) { d.hide(); this.task_dialog(project, rr.message); } } });
\t\t$(d.body).find(".duty-tf-chip").on("click", (e) => {
\t\t\tif ($(e.target).hasClass("duty-tf-del")) return;
\t\t\tconst $c = $(e.currentTarget);
\t\t\tconst url = $c.data("url"), kind = $c.data("kind"), fn = $c.data("fn");
\t\t\tif (kind === "image") {
\t\t\t\tconst pd = new frappe.ui.Dialog({ title: fn, size: "extra-large" });
\t\t\t\t$(pd.body).html(`<div style="text-align:center"><img src="${url}" style="max-width:100%;max-height:74vh;border-radius:8px"></div>`);
\t\t\t\tpd.show();
\t\t\t} else if (kind === "pdf") {
\t\t\t\tconst pd = new frappe.ui.Dialog({ title: fn, size: "extra-large" });
\t\t\t\t$(pd.body).html(`<iframe src="${url}" style="width:100%;height:76vh;border:none;border-radius:8px"></iframe>`);
\t\t\t\tpd.show();
\t\t\t} else {
\t\t\t\twindow.open(url, "_blank");
\t\t\t}
\t\t});
\t\t$(d.body).find(".duty-tf-del").on("click", (e) => {
\t\t\te.stopPropagation();
\t\t\tconst file = $(e.currentTarget).data("file");
\t\t\tfrappe.confirm(__("Remove this file from the task?"), () =>
\t\t\t\tfrappe.call({ method: "duty_board.projects.task_file_delete", args: { name: t.name, file: file }, callback: (rr) => { if (rr.message) { d.hide(); this.task_dialog(project, rr.message); } } }));
\t\t});
\t\t$(d.body).find(".duty-tf-add input").on("change", async (e) => {
\t\t\tconst files = Array.from(e.target.files || []);
\t\t\tif (!files.length) return;
\t\t\tfrappe.show_alert({ message: __("Uploading {0} file(s)…", [files.length]), indicator: "blue" });
\t\t\tfor (const f of files) {
\t\t\t\tconst fd = new FormData();
\t\t\t\tfd.append("file", f, f.name);
\t\t\t\tfd.append("is_private", "1");
\t\t\t\tfd.append("doctype", "Duty Project Task");
\t\t\t\tfd.append("docname", t.name);
\t\t\t\tawait fetch("/api/method/upload_file", { method: "POST", headers: { "X-Frappe-CSRF-Token": frappe.csrf_token }, body: fd });
\t\t\t}
\t\t\tfrappe.show_alert({ message: __("Uploaded."), indicator: "green" });
\t\t\ttfReload();
\t\t});
'''

# --- 6. JS: board 📎 chip -----------------------------------------------------
KB_OLD = '''\t\t\t\t${t.blocked ? `<div class="duty-kb-blk">🔒 ${__("blocked by")} ${frappe.utils.escape_html(t.blocked_title || "")}</div>` : ""}'''
KB_NEW = '''\t\t\t\t${t.blocked ? `<div class="duty-kb-blk">🔒 ${__("blocked by")} ${frappe.utils.escape_html(t.blocked_title || "")}</div>` : ""}
\t\t\t\t${t.file_count ? `<span class="duty-kb-files">📎 ${t.file_count}</span>` : ""}'''

CSS_OLD = '\t\t\t.duty-fx-flag td { background: #FEF6F0; }'
CSS_NEW = '''\t\t\t.duty-fx-flag td { background: #FEF6F0; }
\t\t\t.duty-ld-files { margin-top: 6px; }
\t\t\t.duty-ld-files-h { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: #8a958f; display: block; margin-bottom: 4px; }
\t\t\t.duty-tf-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
\t\t\t.duty-tf-chip { display: inline-flex; gap: 6px; align-items: center; font-size: 12px; background: #F0F4F3; border: 1px solid #E4EAE8; border-radius: 20px; padding: 3px 10px; cursor: pointer; max-width: 240px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
\t\t\t.duty-tf-chip:hover { background: #E7F0ED; }
\t\t\t.duty-tf-del { opacity: .55; margin-left: 2px; text-decoration: none; }
\t\t\t.duty-tf-del:hover { opacity: 1; }
\t\t\t.duty-kb-files { font-size: 10.5px; color: #65736F; font-weight: 700; }'''


def main():
    root = os.getcwd()
    files = {}
    for p in (INIT, JS, PROJ):
        with io.open(os.path.join(root, p), encoding="utf-8") as f:
            files[p] = f.read()

    if "def task_file_delete(" in files[PROJ]:
        print("Already applied. Nothing to do.")
        return
    if '"3.78.0"' not in files[INIT]:
        sys.exit("ABORT: not at v3.78.0.")

    # runtime-resolve the handler anchor: the card dialog binds the phase-save
    # via the first save call site — we hook right before "d.show()" inside
    # the card dialog. Find the unique save-site-1 text and the d.show() that
    # follows it.
    js = files[JS]
    save1 = "\t\t\t\t\testimate_hours: v.estimate_hours || null,"
    checks = [
        (PROJ, BC_OLD, "board file counts", 1), (PROJ, BC2_OLD, "maps", 1),
        (PROJ, BC3_OLD, "task file_count", 1), (PROJ, GC_OLD, "get_card files", 1),
        (PROJ, DEL_ANCHOR, "delete endpoint anchor", 1),
        (JS, FS_OLD, "files section", 1), (JS, KB_OLD, "board chip", 1),
        (JS, CSS_OLD, "css", 1), (JS, save1, "save site 1 locator", 1),
    ]
    problems = [f"  [{files[f].count(o)} != {n}] {label}" for f, o, label, n in checks if files[f].count(o) != n]
    # the d.show() after save1: find it
    i = js.find(save1)
    j = js.find("\t\td.show();", i)
    if j < 0:
        problems.append("  d.show() after save site not found")
    if problems:
        print("ABORT — anchors not clean:")
        print("\n".join(problems))
        sys.exit(1)

    print("All anchors matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    pj = files[PROJ]
    for o, n in [(BC_OLD, BC_NEW), (BC2_OLD, BC2_NEW), (BC3_OLD, BC3_NEW), (GC_OLD, GC_NEW), (DEL_ANCHOR, DEL_NEW)]:
        pj = pj.replace(o, n, 1)
    with io.open(os.path.join(root, PROJ), "w", encoding="utf-8") as f:
        f.write(pj)
    print("  projects.py: board counts, get_card files, task_file_delete")

    js = js.replace(FS_OLD, FS_NEW, 1).replace(KB_OLD, KB_NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    i = js.find(save1)
    j = js.find("\t\td.show();", i)
    js = js[:j] + HANDLERS + js[j:]
    with io.open(os.path.join(root, JS), "w", encoding="utf-8") as f:
        f.write(js)
    print("  duty_board.js: files section, preview/upload/delete handlers, board chip")

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(files[INIT].replace('"3.78.0"', '"3.79.0"'))
    print("wrote __init__.py -> 3.79.0")


if __name__ == "__main__":
    main()
