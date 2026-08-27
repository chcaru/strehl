"""WHY does glob('**') under-reach? Measure it; do not assert a mechanism.

I told the orchestrator the gap was directory reparse points. The commissioning
suite then planted a decoy behind a junction and glob FOUND it -- so either the
mechanism is wrong or the decoy does not reproduce it. Classify every path that
os.walk returns and glob does not, and let the classification name the cause.
"""
import fnmatch
import glob as g
import os

ROOT = r"C:\dev"
PAT = "strehl*.exe"


def walked(root):
    out = []
    for dirpath, _d, files in os.walk(root):
        for f in files:
            if fnmatch.fnmatch(f.lower(), PAT):
                out.append(os.path.join(dirpath, f))
    return out


w = walked(ROOT)
q = g.glob(os.path.join(ROOT, "**", PAT), recursive=True)
W = {os.path.normcase(p) for p in w}
Q = {os.path.normcase(p) for p in q}
print("os.walk  %4d paths" % len(W))
print("glob **  %4d paths" % len(Q))
missed = sorted(W - Q)
print("missed by glob: %d" % len(missed))
print("found by glob but not os.walk: %d" % len(Q - W))

dotted, reparse, other = [], [], []
for p in missed:
    rel = os.path.relpath(p, ROOT)
    parts = rel.split(os.sep)
    if any(x.startswith(".") for x in parts):
        dotted.append(p)
        continue
    # walk up looking for a reparse point on the path
    d, hit = os.path.dirname(p), False
    while len(d) > len(ROOT):
        try:
            if os.lstat(d).st_file_attributes & 0x400:
                hit = True
                break
        except OSError:
            pass
        d = os.path.dirname(d)
    (reparse if hit else other).append(p)

print("\nCLASSIFICATION OF THE MISSES  (must sum to %d)" % len(missed))
print("  dot-prefixed component in path : %4d" % len(dotted))
print("  under a directory reparse point: %4d" % len(reparse))
print("  neither                        : %4d" % len(other))
print("  sum                            : %4d"
      % (len(dotted) + len(reparse) + len(other)))
for name, lst in (("dotted", dotted), ("reparse", reparse), ("other", other)):
    for p in lst[:3]:
        print("   %-8s %s" % (name, p))
