#!/usr/bin/env python3
"""Name-resolution audit — every name a module loads must be defined somewhere.

Written after four NameErrors shipped in one day, each of which py_compile
passed happily because a syntax check does not care whether a name exists:

  cint in academy_repair            — a bench command that died on first run
  _nth_working_day in accounting    — a quarterly scheduled job that never fired
  json in accounting                — an error-logging path that would raise
  _on_track in client_room          — inside a try/except, so the achievement
                                      screen's only upsell silently produced
                                      nothing for as long as it existed

Three of those four failed silently. That is the class of defect this whole
codebase keeps producing, and it is the cheapest one to detect: a module either
resolves its names or it does not.

Deliberately conservative. It flags a name only when nothing in the module
could plausibly define it — imports, assignments, parameters, comprehension
targets, except-handlers, with-targets, globals, function and class names are
all treated as definitions. False negatives are accepted; a false positive
would train people to ignore the output, which is how the test suite died.

  python3 audit_names.py            # the app package
  python3 audit_names.py --all      # include one-shot build scripts too
"""

import ast
import builtins
import glob
import io
import os
import sys

SKIP_PREFIX = ("apply_v", "build_finance_", "add_checks_", "rebuild_closer_",
               "fix_", "deepen_", "tag_topics", "audit_")
BUILTIN = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__"}


def defined_names(tree):
    """Everything this module could plausibly be defining."""
    out = set(BUILTIN)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                out.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            for t in ast.walk(n.optional_vars):
                if isinstance(t, ast.Name):
                    out.add(t.id)
        elif isinstance(n, ast.Global):
            out.update(n.names)
    return out


def loaded_names(tree):
    return {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def self_test():
    """Prove the checker catches a known-bad module before believing a clean run.

    A scanner whose silence has never been tested is not evidence of anything —
    the lesson from the access-control audit, where a clean result turned out to
    be a pattern that could not see past a stacked decorator.
    """
    bad = ast.parse("import os\ndef f():\n    return cint(os.sep)\n")
    assert loaded_names(bad) - defined_names(bad) == {"cint"}, "checker is broken"
    good = ast.parse("from frappe.utils import cint\ndef f():\n    return cint(1)\n")
    assert not (loaded_names(good) - defined_names(good)), "checker over-reports"


def main():
    self_test()
    include_scripts = "--all" in sys.argv
    files, problems = [], []
    for path in sorted(glob.glob("*.py") + glob.glob("*/*.py")):
        base = os.path.basename(path)
        if base.startswith(SKIP_PREFIX) and not include_scripts:
            continue
        if "/doctype/" in path:
            continue
        files.append(path)
        try:
            tree = ast.parse(io.open(path, encoding="utf-8").read())
        except SyntaxError as e:
            problems.append((path, "SYNTAX: %s" % e))
            continue
        missing = sorted(loaded_names(tree) - defined_names(tree))
        if missing:
            problems.append((path, ", ".join(missing)))

    print("checker self-test passed")
    print("modules scanned: %d%s" % (len(files), "" if include_scripts else "  (build scripts skipped; --all to include)"))
    if problems:
        print("\nUNRESOLVED NAMES:")
        for p, m in problems:
            print("  %-30s %s" % (p, m))
        print("\n%d module(s) with findings." % len(problems))
        sys.exit(1)
    print("\nno unresolved names.")


if __name__ == "__main__":
    main()
