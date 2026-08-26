"""Two things BUILD-TRIAGE's own harness never checks."""
import os, sys, json, io, contextlib, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "BUILD-TRIAGE"))
import triage, tri, mutatetest

REAL = r"C:\dev\strehl-out\BUILD-TRIAGE\triage.json"
doc = json.load(open(REAL, encoding="utf-8"))

print("=" * 70)
print("A. Does the gate see NESTED fields, or only top-level + evidence?")
print("=" * 70)
nested = []
for r in doc["rows"]:
    for k, v in list(r.items()) + list((r.get("evidence") or {}).items()):
        if isinstance(v, dict):
            nested.append((r["subject"], k, sorted(v.keys())))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            nested.append((r["subject"], k + "[]", sorted(v[0].keys())))
print("nested dict-valued fields inside rows: %d" % len(nested))
for s, k, ks in nested[:5]:
    print("   %s.%s -> %s" % (s, k, ks))
print("-> gate coverage is %s for this data"
      % ("COMPLETE (no nested fields exist)" if not nested else "INCOMPLETE"))

print()
print("blocks that ship WITHOUT any definition mechanism:")
for block in ("counts", "constants", "fields"):
    print("   %-10s %2d keys" % (block, len(doc.get(block, {}))))
undef_counts = sorted(set(doc["counts"]) - set(doc["fields"]))
print("   'counts' keys with no entry in 'fields': %d" % len(undef_counts))
for k in undef_counts[:9]:
    print("        %r" % k)

print()
print("=" * 70)
print("B. When a gate fires, is triage.json ACTUALLY not written?")
print("=" * 70)
scratch = tempfile.mkdtemp(prefix="vtriage-")
real_out = tri.OUT
tri.OUT = scratch
try:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mutatetest.mutate_definitions()
    wrote = os.path.exists(os.path.join(scratch, "triage.json"))
    print("redirected tri.OUT to a scratch dir, ran the definition mutations")
    print("   mutations killed (rc=0)      : %s" % (rc == 0))
    print("   triage.json written anyway?  : %s" % wrote)
    print("   -> gate %s block the write" % ("does NOT" if wrote else "DOES"))
finally:
    tri.OUT = real_out
print("real triage.json untouched:", os.path.exists(REAL),
      "sha16", __import__("hashlib").sha256(open(REAL,"rb").read()).hexdigest()[:16].upper())
