"""How many of the 7 bands did profile() actually WALK?

A verdict of clean computed from 4 bands is not the same claim as one computed
from 7, and the current output prints both as "MEASURED ... bump 0.0". If the
walk stops early the instrument has not looked where a halo would be, and the
pass is a skip wearing a pass's label.
"""
import os, sys, json
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
stems = sorted(x[:-5] for x in os.listdir(FAITH) if x.endswith(".tiff"))
print("%-26s %-14s %5s %10s %9s   %s" % ("subject","verdict","bands","overshoot","bump","outermost band walked"))
short = []; res = {}
for s in stems:
    y = H.luma(tifffile.imread(os.path.join(FAITH, s + ".tiff")))
    v, ov, bp, pen, fl, bands, why = H.profile(y)
    nb = len(bands) if bands else 0
    outer = ("%d-%d" % (bands[-1][0], bands[-1][1])) if bands else "-"
    print("%-26s %-14s %5s %10s %9s   %s%s" % (
        s, v, nb if bands else "-",
        ("%.1f"%ov) if ov is not None else "-",
        ("%.1f"%bp) if bp is not None else "-",
        outer, "   <== TRUNCATED" if bands and nb < len(H.NEAR) else ""))
    res[s] = dict(verdict=v, overshoot=ov, bump=bp, nbands=nb, outer=outer, why=why)
    if bands and nb < len(H.NEAR):
        short.append((s, nb, outer, v))

print("\nTRUNCATED WALKS: %d of %d subjects never reached the outermost band 80-120" % (len(short), len(stems)))
for s, nb, outer, v in short:
    print("   %-26s walked %d/7, stopped at %-8s verdict %s" % (s, nb, outer, v))
json.dump(res, open(r"D:\strehl-out\V-REVIEW\halo\trunc.json","w"), indent=1)
