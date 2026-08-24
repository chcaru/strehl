"""Inventory: public core functionality with no caller outside its own module.

Motivation. Two verified features were found sitting unwired tonight:
the exposure machinery (fact 1346, since wired) and the lateral CA correction
(fact 1414, still unwired -- 4 hits, all in optics.rs, nothing calls it). The
owner's complaint is that the fleet's work is not reaching his photograph, and
this is the mechanism by which that happens silently.

Why the compiler cannot help: `dead_code` does not fire on `pub` items in a
LIBRARY crate, because they are part of the public API by definition. So a
`pub fn` that nothing calls is invisible to `cargo build`, `cargo clippy` and
every test that does not happen to exercise it.

Scope, deliberately narrow to keep the signal-to-noise usable:
  * free functions and consts declared at module top level (`^pub fn`,
    `^pub const`), NOT methods inside `impl` blocks -- those are called as
    `.name()` and a name-based search cannot resolve the receiver.
  * a "reference" is the identifier appearing in any OTHER .rs file in the
    workspace, including tests and benches.

This is a TRIAGE instrument, not a verdict. Every hit needs a human read:
a plugin entry point, a trait method, or an API intended for third parties is
SUPPOSED to have no in-tree caller. The output is a list to look at.
"""
import io
import os
import re
import sys
from collections import defaultdict

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
CRATES = os.path.join(ROOT, "crates")

DECL = re.compile(r"^pub (?:fn|const) ([A-Za-z_][A-Za-z0-9_]*)", re.M)


def rust_files():
    for dirpath, dirnames, filenames in os.walk(CRATES):
        dirnames[:] = [d for d in dirnames if d not in ("target", ".git")]
        for fn in filenames:
            if fn.endswith(".rs"):
                yield os.path.join(dirpath, fn)


def main():
    files = sorted(rust_files())
    text = {}
    for p in files:
        with io.open(p, encoding="utf-8", errors="replace") as f:
            text[p] = f.read()

    decls = defaultdict(list)          # name -> [defining file, ...]
    for p in files:
        for m in DECL.finditer(text[p]):
            decls[m.group(1)].append(p)

    # Count references per name across all files, once, rather than re-scanning
    # each file per name: 52 files x ~900 names is slow enough to matter.
    refs = defaultdict(set)            # name -> {file, ...}
    ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    for p in files:
        for m in ident.finditer(text[p]):
            n = m.group(0)
            if n in decls:
                refs[n].add(p)

    orphans = []
    for name, sites in sorted(decls.items()):
        if len(sites) != 1:
            continue                   # same name in two modules; ambiguous
        home = sites[0]
        elsewhere = refs[name] - {home}
        if not elsewhere:
            orphans.append((os.path.relpath(home, ROOT).replace("\\", "/"), name))

    print(f"scanned {len(files)} rust files, {len(decls)} top-level pub fn/const names")
    print(f"NO REFERENCE OUTSIDE DEFINING FILE: {len(orphans)}")
    print()
    by_file = defaultdict(list)
    for rel, name in orphans:
        by_file[rel].append(name)
    for rel in sorted(by_file, key=lambda r: -len(by_file[r])):
        print(f"  {rel}  ({len(by_file[rel])})")
        for name in sorted(by_file[rel]):
            print(f"      {name}")


if __name__ == "__main__":
    sys.exit(main())
