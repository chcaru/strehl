"""CORRECTED coverage test. My first version counted len(bands), which is
ALWAYS 7 -- pinched bands are appended as None and `continue`d, not stopped.
The statistic is computed from `vals`, which BREAKS at the first None. So the
number of bands actually examined is len(vals), and it is not printed anywhere.

Consequence to test: a subject can return "MEASURED ... clean" having looked
only at 2-32 px, never at 32-120 where a halo lives.
"""
import os, sys, json
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
stems = sorted(x[:-5] for x in os.listdir(FAITH) if x.endswith(".tiff"))
print("%-36s %-13s %6s %10s %8s  %s" % ("subject","verdict","used","overshoot","bump","deepest band the statistic SAW"))
res = {}; part = {"full":0,"partial":0,"unmeas":0}
for s in stems:
    y = H.luma(tifffile.imread(os.path.join(FAITH, s + ".tiff")))
    v, ov, bp, pen, fl, bands, why = H.profile(y)
    if bands is None:
        print("%-36s %-13s %6s %10s %8s  %s" % (s, v, "-", "-", "-", why))
        res[s] = dict(verdict=v, used=0, why=why); part["unmeas"] += 1; continue
    vals = []
    for b in bands:
        if b[3] is None: break
        vals.append(b)
    used = len(vals)
    deepest = "%d-%d" % (vals[-1][0], vals[-1][1]) if vals else "-"
    blind = ""
    if used < len(H.NEAR):
        blind = "   BLIND beyond %d px" % vals[-1][1]
        part["partial"] += 1
    else:
        part["full"] += 1
    print("%-36s %-13s %6s %10.1f %8.1f  %s%s" % (s, v, "%d/7"%used, ov, bp, deepest, blind))
    res[s] = dict(verdict=v, used=used, overshoot=ov, bump=bp, deepest=deepest)

print("\nCOVERAGE PARTITION (must sum to %d)" % len(stems))
print("  full 7-band walk        : %d" % part["full"])
print("  PARTIAL walk (blind)    : %d" % part["partial"])
print("  UNMEASURABLE            : %d" % part["unmeas"])
print("  total                   : %d" % sum(part.values()))
json.dump(res, open(r"D:\strehl-out\V-REVIEW\halo\trunc2.json","w"), indent=1)
