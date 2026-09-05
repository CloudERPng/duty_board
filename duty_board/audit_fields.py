#!/usr/bin/env python3
"""Every field named in a get_all must exist on that doctype.

Written after three field-name errors in one day: `contributed` (not a field on
the position), `on_date` (the column is price_date), and `_dstr` before them.
py_compile passes and audit_names passes, because a wrong column is only wrong
when the query actually runs — which on a hot path means the page is dead.

Run: python3 audit_fields.py
"""
import glob
import io
import json
import re

STD = {"name", "owner", "creation", "modified", "modified_by", "idx", "docstatus",
       "parent", "parenttype", "parentfield", "_user_tags", "_comments", "_assign"}
OPS = {"as_dict", "limit_page_length", "pluck", "filters", "fields", "order_by",
       "limit", "in", "not", "is", "like", "between", "group_by", "distinct",
       "ignore_permissions", "update_modified", "start", "page_length", "or_filters"}


def load():
    out = {}
    for j in glob.glob("duty_board/doctype/*/*.json"):
        try:
            d = json.load(open(j))
        except Exception:
            continue
        if d.get("doctype") != "DocType":
            continue
        out[d["name"]] = {f["fieldname"] for f in d.get("fields", [])} | STD
    return out


def main():
    fields, bad = load(), []
    for py in glob.glob("*.py"):
        src = io.open(py, encoding="utf-8").read()
        for m in re.finditer(r'get_all\(\s*["\']([A-Z][\w ]+)["\'](.{0,500}?)\)', src, re.S):
            dt, blob = m.group(1), m.group(2)
            if dt not in fields:
                continue
            used = set(re.findall(r'["\'](\w+)["\']\s*:', blob))
            fl = re.findall(r"fields=\[([^\]]*)\]", blob)
            if fl:
                used |= set(re.findall(r'["\'](\w+)["\']', fl[0]))
            used |= set(re.findall(r'order_by=["\'](\w+)', blob))
            used |= set(re.findall(r'pluck=["\'](\w+)["\']', blob))
            for u in used - fields[dt] - OPS:
                bad.append((py, dt, u))
    for b in sorted(set(bad)):
        print("  %-18s %-30s %s" % b)
    print("\n%d unknown field(s) referenced." % len(set(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
