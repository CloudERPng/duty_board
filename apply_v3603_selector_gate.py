#!/usr/bin/env python3
"""v3.60.3 — fix the project selector gate off-by-one."""

import io
import os
import sys

PORTAL = "duty_board/www/portal.html"
CHECK_ONLY = "--check" in sys.argv

OLD = '''\t\t\t// Selector only earns its place with 2+ real projects (General always
\t\t\t// present, so ">2 entries" means "more than one actual project").
\t\t\tif (window._projs.length <= 2) { wrap.style.display = "none"; window._psel = ""; return; }'''
NEW = '''\t\t\t// Show once there is at least one real project besides General.
\t\t\t// client_projects() returns [each real project..., General], so 2+
\t\t\t// entries means one-or-more real projects to choose between.
\t\t\tif (window._projs.length < 2) { wrap.style.display = "none"; window._psel = ""; return; }'''


def main():
    root = os.getcwd()
    fp = os.path.join(root, PORTAL)
    with io.open(fp, encoding="utf-8") as f:
        html = f.read()

    if 'Show once there is at least one real project' in html:
        print("Already applied. Nothing to do.")
        return
    if html.count(OLD) != 1:
        print(f"ABORT — gate anchor found {html.count(OLD)} times (expected 1).")
        sys.exit(1)

    print("Anchor matched.")
    if CHECK_ONLY:
        print("--check given; no files written.")
        return

    with io.open(fp, "w", encoding="utf-8") as f:
        f.write(html.replace(OLD, NEW, 1))
    print("  portal: selector gate fixed (<= 2  ->  < 2)")

    ip = os.path.join(root, "duty_board/__init__.py")
    with io.open(ip, encoding="utf-8") as f:
        init = f.read()
    if '"3.60.2"' in init:
        with io.open(ip, "w", encoding="utf-8") as f:
            f.write(init.replace('"3.60.2"', '"3.60.3"'))
        print("wrote __init__.py -> 3.60.3")
    else:
        print("NOTE: version not 3.60.2 — left untouched.")


if __name__ == "__main__":
    main()
