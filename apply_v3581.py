#!/usr/bin/env python3
"""Duty Board v3.58.1 — the promised APPROVED badge, plus one weed pulled.

1. DOCUMENT HUB REVIEW BADGES (the twice-promised item). The Client
   Document payload has carried review_status / approved_on /
   approved_version all along; nothing on the staff side rendered them.
   Now:

   FORM — an indicator chip beside the title for financial statements:
     ✅ APPROVED by client — 2026-08-04     (green)
     ✅ Approved v2 — but v3 is now published (orange: STALE approval —
        approval binds to a published version, same rule
        client_statement_file uses before stamping the PDF)
     ✏ Client requested changes            (orange)
     👀 Awaiting client review              (blue)
   Chips stack with the existing Checked Out headline instead of
   fighting it for the one headline slot.

   LIST — indicators grow beyond Checked Out/Available, priority:
   Checked Out (workflow first) > Changes Requested (action needed) >
   Client Approved / Approved (stale) > Awaiting Client Review >
   Available. Each filters the list on click, as list indicators do.

2. DUPLICATE _renewal_info DELETED. get_rooms called
   _renewal_info(r.customer) twice back-to-back per room — a copy-paste
   twin doing every renewal lookup twice on every Clients-face poll.
   Output identical; half the work gone.

Deploy: bench build --app duty_board && bench restart
        && bench --site <site> clear-cache

Anchored, all-or-nothing, idempotent. Run from ~/frappe-bench/apps/duty_board.
Requires v3.58.0.
"""

import io
import os
import sys

FORM = "duty_board/document_hub/doctype/client_document/client_document.js"
LIST = "duty_board/document_hub/doctype/client_document/client_document_list.js"
CR = "duty_board/client_room.py"
INIT = "duty_board/__init__.py"
CHECK_ONLY = "--check" in sys.argv

# --- 1a. form: review badge chips -------------------------------------------

F1_OLD = '        frm.page.clear_actions_menu();'

F1_NEW = '''        frm.page.clear_actions_menu();

        // ---- Client review badge (financial statements) ----
        if (frm.doc.is_financial_statement && frm.doc.review_status) {
            const rs = frm.doc.review_status;
            if (rs === "Approved") {
                const current =
                    Number(frm.doc.approved_version || 0) === Number(frm.doc.publish_seq || 1);
                if (current) {
                    frm.dashboard.add_indicator(
                        __("✅ APPROVED by client — {0}", [(frm.doc.approved_on || "").slice(0, 10)]),
                        "green"
                    );
                } else {
                    // Approval binds to a published version; a republish makes it stale.
                    frm.dashboard.add_indicator(
                        __("✅ Approved v{0} — but v{1} is now published", [
                            frm.doc.approved_version,
                            frm.doc.publish_seq,
                        ]),
                        "orange"
                    );
                }
            } else if (rs === "Changes Requested") {
                frm.dashboard.add_indicator(__("✏ Client requested changes"), "orange");
            } else if (rs === "Awaiting Client Review") {
                frm.dashboard.add_indicator(__("👀 Awaiting client review"), "blue");
            }
        }'''

# --- 1b. list: full rewrite (522-byte file, cleanest as a whole) -------------

L_NEW = '''frappe.listview_settings["Client Document"] = {
    add_fields: [
        "status", "checked_out_by", "current_version",
        "is_financial_statement", "review_status", "approved_version", "publish_seq",
    ],
    get_indicator(doc) {
        if (doc.status === "Checked Out") {
            const mine = doc.checked_out_by === frappe.session.user;
            return [
                mine ? __("Checked Out (You)") : __("Checked Out"),
                mine ? "blue" : "orange",
                "status,=,Checked Out",
            ];
        }
        if (doc.is_financial_statement && doc.review_status === "Changes Requested") {
            return [__("Changes Requested"), "orange", "review_status,=,Changes Requested"];
        }
        if (doc.is_financial_statement && doc.review_status === "Approved") {
            const current = Number(doc.approved_version || 0) === Number(doc.publish_seq || 1);
            return current
                ? [__("✔ Client Approved"), "green", "review_status,=,Approved"]
                : [__("Approved (stale)"), "orange", "review_status,=,Approved"];
        }
        if (doc.is_financial_statement && doc.review_status === "Awaiting Client Review") {
            return [__("Awaiting Client Review"), "blue", "review_status,=,Awaiting Client Review"];
        }
        return [__("Available"), "green", "status,=,Available"];
    },
};
'''

# --- 2. client_room.py: the doubled renewal lookup ---------------------------

C1_OLD = '''\t\ttry:
\t\t\tr.renewal = _renewal_info(r.customer)
\t\texcept Exception:
\t\t\tr.renewal = None
\t\ttry:
\t\t\tr.renewal = _renewal_info(r.customer)
\t\texcept Exception:
\t\t\tr.renewal = None'''

C1_NEW = '''\t\ttry:
\t\t\tr.renewal = _renewal_info(r.customer)
\t\texcept Exception:
\t\t\tr.renewal = None'''


def main():
    root = os.getcwd()
    files = {}
    for p in (FORM, LIST, CR):
        fp = os.path.join(root, p)
        if not os.path.exists(fp):
            sys.exit(f"ABORT: {p} not found. Run from ~/frappe-bench/apps/duty_board")
        with io.open(fp, encoding="utf-8") as f:
            files[p] = f.read()

    if "Client review badge (financial statements)" in files[FORM]:
        print("Already applied. Nothing to do.")
        return

    problems = []
    if files[FORM].count(F1_OLD) != 1:
        problems.append(f"  [{files[FORM].count(F1_OLD)} matches] form: clear_actions_menu anchor")
    if files[CR].count(C1_OLD) != 1:
        problems.append(f"  [{files[CR].count(C1_OLD)} matches] client_room.py: doubled renewal block")
    if "review_status" in files[LIST]:
        problems.append("  list js already mentions review_status — inspect before overwriting")
    if problems:
        print("ABORT — preconditions not met:")
        print("\n".join(problems))
        sys.exit(1)

    print("All 3 preconditions met.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(os.path.join(root, FORM), "w", encoding="utf-8") as f:
        f.write(files[FORM].replace(F1_OLD, F1_NEW, 1))
    print("  applied: form review badge chips")

    with io.open(os.path.join(root, LIST), "w", encoding="utf-8") as f:
        f.write(L_NEW)
    print("  applied: list indicators rewritten")

    with io.open(os.path.join(root, CR), "w", encoding="utf-8") as f:
        f.write(files[CR].replace(C1_OLD, C1_NEW, 1))
    print("  applied: doubled _renewal_info removed")

    init_path = os.path.join(root, INIT)
    with io.open(init_path, encoding="utf-8") as f:
        init = f.read()
    new_init = init.replace('"3.58.0"', '"3.58.1"')
    if new_init != init:
        with io.open(init_path, "w", encoding="utf-8") as f:
            f.write(new_init)
        print("wrote duty_board/__init__.py  -> 3.58.1")
    else:
        print("NOTE: version was not 3.58.0 — left untouched.")


if __name__ == "__main__":
    main()
