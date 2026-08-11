#!/usr/bin/env python3
"""Duty Board v3.98.0 — ZhiftERP certification split into self-contained tracks.

1. New file academy_tracks_split.py with split_zhifterp_tracks():
   - creates Duty Products "ZhiftERP Selling" and "ZhiftERP Procurement"
   - re-points Selling modules to ZhiftERP Selling, Buying/Procurement
     modules to ZhiftERP Procurement
   - renames module titles "Buying N — ..." -> "Procurement N — ..."
   - re-points both certification tracks to their new products
   - prints a full diagnostic table of every ZhiftERP-family module
     (name, product, active, lesson count, question count) — which will
     also show exactly what state the missing Selling 4/6/7 are in.
2. academy_procure_pro_data.json: module titles Buying -> Procurement
   (lockstep with the DB rename so refresh-by-title keeps matching).
3. academy_seed_procure_pro.py: product -> "ZhiftERP Procurement"
   (future modules land in the right group).
4. academy_seed_sales_pro.py: product -> "ZhiftERP Selling" (idempotent
   re-seed of any missing Selling module recreates it under the right
   product).

Deploy: apply -> commit -> then on the server:
  bench --site xlevel.clouderp.one execute duty_board.academy_tracks_split.split_zhifterp_tracks

Anchored, idempotent. Requires v3.97.0.
Run from ~/frappe-bench/apps/duty_board.
"""

import io
import json
import os
import sys

INIT = "duty_board/__init__.py"
DATA_PATH = "duty_board/academy_procure_pro_data.json"
PROC_SEEDER = "duty_board/academy_seed_procure_pro.py"
SALES_SEEDER = "duty_board/academy_seed_sales_pro.py"
SPLIT_PATH = "duty_board/academy_tracks_split.py"
CHECK_ONLY = "--check" in sys.argv

SPLIT = '''"""One-off migration: split the ZhiftERP certification into self-contained
product groups — ZhiftERP Selling and ZhiftERP Procurement — and rename
Buying modules to Procurement.

Run:  bench --site xlevel.clouderp.one execute duty_board.academy_tracks_split.split_zhifterp_tracks
Idempotent. Prints a diagnostic table of every ZhiftERP-family module.
"""

import frappe

SELLING_PRODUCT = "ZhiftERP Selling"
PROCURE_PRODUCT = "ZhiftERP Procurement"


def _ensure_product(title, sort_order):
\tif not frappe.db.exists("Duty Product", title):
\t\tfrappe.get_doc({"doctype": "Duty Product", "title": title, "active": 1, "sort_order": sort_order}).insert(
\t\t\tignore_permissions=True
\t\t)
\t\tprint(f"created Duty Product: {title}")


def split_zhifterp_tracks():
\t_ensure_product(SELLING_PRODUCT, 5)
\t_ensure_product(PROCURE_PRODUCT, 6)

\tmods = frappe.get_all(
\t\t"Duty Training Module",
\t\tfilters={"product": ["in", ["ZhiftERP", SELLING_PRODUCT, PROCURE_PRODUCT]]},
\t\tfields=["name", "title", "product", "active", "sort_order"],
\t\torder_by="sort_order asc, title asc",
\t)
\tfor m in mods:
\t\ttitle = m.title
\t\tif title.startswith("Buying "):
\t\t\tnew_title = "Procurement " + title[len("Buying "):]
\t\t\tfrappe.db.set_value("Duty Training Module", m.name, "title", new_title)
\t\t\tprint(f"renamed: {title} -> {new_title}")
\t\t\ttitle = new_title
\t\tif title.startswith("Selling ") and m.product != SELLING_PRODUCT:
\t\t\tfrappe.db.set_value("Duty Training Module", m.name, "product", SELLING_PRODUCT)
\t\t\tprint(f"re-pointed to {SELLING_PRODUCT}: {title}")
\t\telif title.startswith("Procurement ") and m.product != PROCURE_PRODUCT:
\t\t\tfrappe.db.set_value("Duty Training Module", m.name, "product", PROCURE_PRODUCT)
\t\t\tprint(f"re-pointed to {PROCURE_PRODUCT}: {title}")

\tfor track_title, product in (
\t\t("ZhiftERP Sales Professional", SELLING_PRODUCT),
\t\t("ZhiftERP Procurement Professional", PROCURE_PRODUCT),
\t):
\t\tname = frappe.db.get_value("Duty Certification Track", {"title": track_title}, "name")
\t\tif name and frappe.db.get_value("Duty Certification Track", name, "product") != product:
\t\t\tfrappe.db.set_value("Duty Certification Track", name, "product", product)
\t\t\tprint(f"track re-pointed: {track_title} -> {product}")

\tfrappe.db.commit()

\tprint("\\n=== DIAGNOSTIC: ZhiftERP-family modules ===")
\tmods = frappe.get_all(
\t\t"Duty Training Module",
\t\tfilters={"product": ["in", ["ZhiftERP", SELLING_PRODUCT, PROCURE_PRODUCT]]},
\t\tfields=["name", "title", "product", "active", "audience", "sort_order"],
\t\torder_by="product asc, sort_order asc",
\t)
\tfor m in mods:
\t\tlessons = frappe.db.count("Duty Lesson", {"module": m.name})
\t\tquestions = frappe.db.count("Duty Quiz Question", {"module": m.name})
\t\tflag = "" if (m.active and lessons and questions) else "   <-- CHECK"
\t\tprint(
\t\t\tf"  [{m.product}] sort={m.sort_order} active={m.active} aud={m.audience} "
\t\t\tf"lessons={lessons} questions={questions}  {m.title}{flag}"
\t\t)
\tleft = [m for m in mods if m.product == "ZhiftERP"]
\tif left:
\t\tprint(f"\\nWARNING: {len(left)} module(s) still under the old ZhiftERP product (unmatched titles).")
\texpected = [f"Selling {i}" for i in range(1, 9)]
\tpresent = {m.title.split(" — ")[0] for m in mods}
\tmissing = [e for e in expected if e not in present]
\tif missing:
\t\tprint(f"\\nMISSING SELLING MODULES: {missing}")
\t\tprint("Fix: re-run the sales seed (idempotent — recreates missing modules under the new product and re-appends to the track):")
\t\tprint("  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.seed_sales_pro_track")
\t\tprint("Then refresh their manual content:")
\t\tprint("  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_lessons")
\t\tprint("  bench --site xlevel.clouderp.one execute duty_board.academy_seed_sales_pro.refresh_questions")
\tprint("\\nSplit complete.")
'''


def main():
    root = os.getcwd()
    with io.open(os.path.join(root, INIT), encoding="utf-8") as f:
        init = f.read()
    with io.open(os.path.join(root, DATA_PATH), encoding="utf-8") as f:
        data = json.load(f)
    with io.open(os.path.join(root, PROC_SEEDER), encoding="utf-8") as f:
        proc = f.read()
    with io.open(os.path.join(root, SALES_SEEDER), encoding="utf-8") as f:
        sales = f.read()

    if os.path.exists(os.path.join(root, SPLIT_PATH)):
        print("Already applied. Nothing to do.")
        return
    if '"3.97.0"' not in init:
        sys.exit("ABORT: not at v3.97.0.")

    checks = []
    if data["suppliers"]["title"] != "Buying 1 — Suppliers & the Supply Base":
        checks.append("  suppliers title anchor mismatch")
    if data["items_costs"]["title"] != "Buying 2 — Purchase Items, Costs & UOMs":
        checks.append("  items_costs title anchor mismatch")
    if proc.count('"product": "ZhiftERP",') != 2:
        checks.append(f"  proc seeder product anchors: {proc.count(chr(34)+'product'+chr(34)+': '+chr(34)+'ZhiftERP'+chr(34)+',')} (want 2: module + track)")
    if 'frappe.db.exists("Duty Product", "ZhiftERP")' not in proc:
        checks.append("  proc seeder ensure-product anchor missing")
    if sales.count('"product": "ZhiftERP",') != 2:
        checks.append("  sales seeder product anchors != 2")
    if 'frappe.db.exists("Duty Product", "ZhiftERP")' not in sales:
        checks.append("  sales seeder ensure-product anchor missing")
    if checks:
        print("ABORT — anchors not clean:")
        print("\n".join(checks))
        sys.exit(1)

    print("Anchors clean: 2 data titles, 2 product refs per seeder, ensure-product blocks found.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    data["suppliers"]["title"] = "Procurement 1 — Suppliers & the Supply Base"
    data["items_costs"]["title"] = "Procurement 2 — Purchase Items, Costs & UOMs"
    with io.open(os.path.join(root, DATA_PATH), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")

    proc = proc.replace('"product": "ZhiftERP",', '"product": "ZhiftERP Procurement",')
    proc = proc.replace(
        'if not frappe.db.exists("Duty Product", "ZhiftERP"):\n\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP", "active": 1, "sort_order": 0}).insert(',
        'if not frappe.db.exists("Duty Product", "ZhiftERP Procurement"):\n\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP Procurement", "active": 1, "sort_order": 6}).insert(',
    )
    proc = proc.replace('print("created Duty Product: ZhiftERP")', 'print("created Duty Product: ZhiftERP Procurement")')
    with io.open(os.path.join(root, PROC_SEEDER), "w", encoding="utf-8") as f:
        f.write(proc)

    sales = sales.replace('"product": "ZhiftERP",', '"product": "ZhiftERP Selling",')
    sales = sales.replace(
        'if not frappe.db.exists("Duty Product", "ZhiftERP"):\n\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP", "active": 1, "sort_order": 0}).insert(',
        'if not frappe.db.exists("Duty Product", "ZhiftERP Selling"):\n\t\tfrappe.get_doc({"doctype": "Duty Product", "title": "ZhiftERP Selling", "active": 1, "sort_order": 5}).insert(',
    )
    sales = sales.replace('print("created Duty Product: ZhiftERP")', 'print("created Duty Product: ZhiftERP Selling")')
    with io.open(os.path.join(root, SALES_SEEDER), "w", encoding="utf-8") as f:
        f.write(sales)

    with io.open(os.path.join(root, SPLIT_PATH), "w", encoding="utf-8") as f:
        f.write(SPLIT)

    with io.open(os.path.join(root, INIT), "w", encoding="utf-8") as f:
        f.write(init.replace('"3.97.0"', '"3.98.0"'))
    print("  data: Procurement 1 & 2 titles renamed")
    print("  seeders: products -> ZhiftERP Selling / ZhiftERP Procurement")
    print("  created: academy_tracks_split.py (migration + diagnostics)")
    print("wrote __version__ -> 3.98.0")


if __name__ == "__main__":
    main()
