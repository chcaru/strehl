"""Reachability audit: which pub modules have no caller outside themselves?

Applies discipline 800. `pub` suppresses dead_code in a lib crate, so a module
can carry thousands of green-tested lines and never be reached from the product.
This asks, for every `pub mod` declared at HEAD, whether anything outside the
module's own file and its own test/example harness ever names it.

Read-only. Reads git blobs as bytes via subprocess (never via `>` redirection,
which re-encodes on Windows).
"""
import collections
import re
import subprocess
import sys

REPO = r"C:\dev\blog\death-of-software\projects\strehl"


def git(*args):
    p = subprocess.run(
        ["git"] + list(args), cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return p.stdout.decode("utf-8", "replace"), p.returncode


head, rc = git("rev-parse", "HEAD")
assert rc == 0, "cannot read HEAD"
head = head.strip()

tree, rc = git("ls-tree", "-r", "--name-only", "HEAD")
assert rc == 0, "cannot list tree"
files = [f for f in tree.splitlines() if f.endswith(".rs")]

libs = [f for f in files if f.endswith("/src/lib.rs")]
mains = [f for f in files if f.endswith("/src/main.rs")]
assert libs, "no lib.rs found at HEAD"

# module name -> declaring lib.rs
declared = {}
for lib in libs:
    src, rc = git("show", "HEAD:" + lib)
    assert rc == 0, "cannot read " + lib
    for m in re.finditer(r"^\s*pub mod\s+([a-z0-9_]+)\s*;", src, re.M):
        declared[m.group(1)] = lib

# Cache every source file's text once.
text = {}
for f in files:
    src, rc = git("show", "HEAD:" + f)
    if rc == 0:
        text[f] = src


def is_own_or_harness(path, mod):
    base = path.rsplit("/", 1)[-1]
    if base == mod + ".rs":
        return True
    if ("/" + mod + "/") in path:
        return True
    if "/tests/" in path or "/examples/" in path or "/benches/" in path:
        return True
    if base in ("lib.rs", "main.rs") and path in declared.values():
        # a bare `pub mod x;` line is a declaration, not a use; handled below
        return False
    return False


rows = []
for mod, lib in sorted(declared.items()):
    pat = re.compile(r"\b" + re.escape(mod) + r"\s*::")
    use_pat = re.compile(r"\buse\s+(?:crate|self|super|[a-z_]+)::" + re.escape(mod) + r"\b")
    callers = collections.Counter()
    harness = 0
    for path, src in text.items():
        hits = len(pat.findall(src)) + len(use_pat.findall(src))
        if not hits:
            continue
        if is_own_or_harness(path, mod):
            harness += hits
            continue
        # exclude the pure declaration line in the declaring lib.rs
        if path == lib:
            body = re.sub(r"^\s*pub mod\s+" + re.escape(mod) + r"\s*;.*$", "", src, flags=re.M)
            hits = len(pat.findall(body)) + len(use_pat.findall(body))
            if not hits:
                continue
        callers[path] += hits
    lines = len(text.get(lib.rsplit("/", 1)[0] + "/" + mod + ".rs", "").splitlines())
    rows.append((mod, lines, sum(callers.values()), harness, dict(callers)))

print("HEAD = %s" % head)
print("crates with lib.rs: %d   with main.rs: %d" % (len(libs), len(mains)))
print("pub modules declared: %d\n" % len(declared))

unreached = [r for r in rows if r[2] == 0]
print("=" * 72)
print("UNREACHED: declared pub, zero references outside own file + harness")
print("=" * 72)
if not unreached:
    print("  (none)")
for mod, lines, ncall, nharn, _ in sorted(unreached, key=lambda r: -r[1]):
    print("  %-24s %5d lines   harness refs: %d" % (mod, lines, nharn))

print("\n" + "=" * 72)
print("REACHED (caller count, top callers)")
print("=" * 72)
for mod, lines, ncall, nharn, callers in sorted(rows, key=lambda r: r[2]):
    if ncall == 0:
        continue
    top = sorted(callers.items(), key=lambda kv: -kv[1])[:2]
    top_s = ", ".join("%s x%d" % (p.rsplit("/", 1)[-1], n) for p, n in top)
    print("  %-24s %5d lines   refs: %4d   [%s]" % (mod, lines, ncall, top_s))

sys.exit(0)
