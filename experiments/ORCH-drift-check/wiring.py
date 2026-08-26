"""Which strehl-core modules reach a shipped binary, and which are dark?

A module can be reached three ways:
  CLI    - referenced from crates/strehl-cli/src/**      (the shipped `strehl` binary)
  CORE   - referenced from another crates/strehl-core/src/*.rs (so it may reach the
           CLI transitively; resolved by fixed point below)
  EX     - referenced only from crates/*/examples/**     (experiments; ships nothing)

Prints a table and, at the end, the set of modules that are DARK: present in
lib.rs, non-trivial, and not reachable from the CLI by any path.

Read-only. Takes no arguments. Run from the strehl repo root.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
# allow running from anywhere: locate the repo by walking up for crates/
for cand in [Path.cwd()] + list(Path.cwd().parents):
    if (cand / "crates" / "strehl-core" / "src" / "lib.rs").exists():
        REPO = cand
        break
else:
    print("could not locate strehl repo root (crates/strehl-core/src/lib.rs)")
    sys.exit(2)

core_src = REPO / "crates" / "strehl-core" / "src"
lib = (core_src / "lib.rs").read_text(encoding="utf-8", errors="replace")
mods = re.findall(r"^pub mod (\w+);", lib, re.M)

cli_src = sorted((REPO / "crates" / "strehl-cli" / "src").glob("*.rs"))
examples = sorted((REPO / "crates").glob("*/examples/*.rs"))


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


cli_text = {p.name: read(p) for p in cli_src}
ex_text = {p.name: read(p) for p in examples}
core_text = {p.stem: read(p) for p in core_src.glob("*.rs") if p.stem != "lib"}

# A reference to module M is `M::`, `use strehl_core::M`, or `use crate::M`.
def refs(text, m):
    pats = [rf"\b{m}::", rf"use strehl_core::{m}\b", rf"use crate::{m}\b",
            rf"use strehl_core::\{{[^}}]*\b{m}\b", rf"crate::{m}::"]
    return sum(len(re.findall(p, text)) for p in pats)


rows = []
for m in mods:
    n_cli = sum(refs(t, m) for t in cli_text.values())
    cli_files = sorted(f for f, t in cli_text.items() if refs(t, m))
    n_core = sum(refs(t, m) for k, t in core_text.items() if k != m)
    core_files = sorted(k for k, t in core_text.items() if k != m and refs(t, m))
    n_ex = sum(refs(t, m) for t in ex_text.values())
    loc = len(read(core_src / f"{m}.rs").splitlines())
    rows.append(dict(mod=m, loc=loc, cli=n_cli, core=n_core, ex=n_ex,
                     cli_files=cli_files, core_files=core_files))

# Fixed point: a module is LIVE if referenced from the CLI, or referenced by a
# module that is itself LIVE.
live = {r["mod"] for r in rows if r["cli"] > 0}
by_mod = {r["mod"]: r for r in rows}
changed = True
while changed:
    changed = False
    for r in rows:
        if r["mod"] in live:
            continue
        if any(c in live for c in r["core_files"]):
            live.add(r["mod"])
            changed = True

print(f"repo: {REPO}")
print(f"{len(mods)} core modules; {len(cli_src)} CLI sources; {len(examples)} examples\n")
hdr = f"{'module':<16}{'loc':>6}{'cli':>6}{'core':>6}{'ex':>6}  {'status':<10} reached-via"
print(hdr)
print("-" * 100)
for r in sorted(rows, key=lambda r: (r["mod"] in live, -r["loc"])):
    status = "LIVE" if r["mod"] in live else "** DARK **"
    via = ",".join(r["cli_files"])[:34] or ("via:" + ",".join(c for c in r["core_files"] if c in live)[:30])
    print(f"{r['mod']:<16}{r['loc']:>6}{r['cli']:>6}{r['core']:>6}{r['ex']:>6}  {status:<10} {via}")

dark = [r for r in rows if r["mod"] not in live]
print()
print("=" * 100)
if not dark:
    print("no dark modules: every core module reaches the shipped CLI")
else:
    tot = sum(r["loc"] for r in dark)
    print(f"DARK: {len(dark)} module(s), {tot} lines, unreachable from the shipped CLI")
    for r in sorted(dark, key=lambda r: -r["loc"]):
        print(f"  {r['mod']:<16}{r['loc']:>6} loc   examples-only refs: {r['ex']}")
