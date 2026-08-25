"""Function-level reachability: which `pub fn` are never called outside their own file?

Extends experiments/ORCH-drift-check/reachability.py (module level, fact 1553)
down one level. In this project the binary is the product and the library is not
published, so a `pub fn` with no external caller is suspicious rather than
legitimate API surface.

KNOWN FALSE-POSITIVE SOURCE, stated up front: methods that implement a trait are
invoked through dynamic or generic dispatch and will look uncalled to a
name-based scan. This script detects `impl <Trait> for` blocks and marks
functions inside them, so they can be excluded from the headline count rather
than silently inflating it.

Read-only. Reads git blobs as bytes via subprocess.
"""
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
assert rc == 0
head = head.strip()

tree, rc = git("ls-tree", "-r", "--name-only", "HEAD")
assert rc == 0
files = [f for f in tree.splitlines() if f.endswith(".rs")]

text = {}
for f in files:
    src, rc = git("show", "HEAD:" + f)
    if rc == 0:
        text[f] = src

# Locate `impl <something> for <something>` blocks by brace matching so that
# trait-implementing methods can be separated out.
def trait_impl_spans(src):
    spans = []
    for m in re.finditer(r"^impl(?:<[^>]*>)?\s+[^\{]*\bfor\b[^\{]*\{", src, re.M):
        depth = 0
        i = m.end() - 1
        while i < len(src):
            if src[i] == "{":
                depth += 1
            elif src[i] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), i))
                    break
            i += 1
    return spans


PROD = [f for f in text if "/tests/" not in f and "/examples/" not in f and "/benches/" not in f]

rows = []
for path in sorted(PROD):
    src = text[path]
    spans = trait_impl_spans(src)
    for m in re.finditer(r"^\s*pub(?:\s*\([^)]*\))?\s+(?:async\s+)?fn\s+([a-z0-9_]+)", src, re.M):
        name = m.group(1)
        if name.startswith("_"):
            continue
        pos = m.start()
        in_trait = any(a <= pos <= b for a, b in spans)
        pat = re.compile(r"\b" + re.escape(name) + r"\s*[(:<]")
        external = 0
        harness = 0
        # Count references inside the declaring file too, minus the declaration
        # itself. Excluding the own file (the previous version of this script)
        # measures "pub but only used locally", which is a visibility smell and
        # not dead code -- it flagged 76 functions, almost all false positives.
        own = len(pat.findall(src))
        if re.match(r"\s*pub", m.group(0)):
            own = max(0, own - 1)
        for other, osrc in text.items():
            if other == path:
                continue
            n = len(pat.findall(osrc))
            if not n:
                continue
            if "/tests/" in other or "/examples/" in other or "/benches/" in other:
                harness += n
            else:
                external += n
        if external == 0 and own == 0:
            rows.append((path, name, in_trait, harness))

by_mod = {}
for path, name, in_trait, harness in rows:
    by_mod.setdefault(path, []).append((name, in_trait, harness))

print("HEAD = %s" % head)
print("production .rs files scanned: %d" % len(PROD))
print()

hard = [r for r in rows if not r[2] and r[3] == 0]
harness_only = [r for r in rows if not r[2] and r[3] > 0]
traity = [r for r in rows if r[2]]

print("=" * 74)
print("A. pub fn with ZERO references anywhere, incl. its own file: %d" % len(hard))
print("   (genuine dead code; trait-impl methods excluded, see C)")
print("=" * 74)
cur = None
for path, name, _, _ in sorted(hard):
    if path != cur:
        print("  %s" % path)
        cur = path
    print("      %s" % name)

print()
print("=" * 74)
print("B. pub fn reached ONLY from tests/examples/benches: %d" % len(harness_only))
print("=" * 74)
cur = None
for path, name, _, h in sorted(harness_only, key=lambda r: (-r[3], r[0])):
    print("  %-52s %-30s harness x%d" % (path.rsplit("/", 1)[-1], name, h))

print()
print("C. trait-impl methods excluded from the counts above: %d" % len(traity))
sys.exit(0)
