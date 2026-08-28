"""ORCH ask #2: the absolute FLAT energy column (energy-vs-scale slope) for
every subject -- plus the column ORCH's version cannot produce: the split-half
signal fraction, which says whether those sites are ACTUALLY noise or structure.

The slope is read off one image and, as slopetest.py shows, cannot separate
reddened noise from structure. The signal fraction is read off two disjoint
frame halves and can. Where both exist, disagreement is the point.
"""
import os
import sys
import numpy as np
import slopetest as st
import nscale as ns

OUT = r"C:\dev\strehl-out\V-BANDFLOOR"

# (label, path, optional ODD path for the reproducibility column)
JOBS = [
    ("112MSDCF  lin", "nscale/112MSDCF__EVEN__A-unset.tiff", "nscale/112MSDCF__ODD__A-unset.tiff"),
    ("113MSDCF  lin", "nscale/113MSDCF__EVEN__A-unset.tiff", "nscale/113MSDCF__ODD__A-unset.tiff"),
    ("119MSDCF  lin", "nscale/119MSDCF__EVEN__A-unset.tiff", "nscale/119MSDCF__ODD__A-unset.tiff"),
    ("bee-2-cpl lin", "nscale/bee-2-cpl__EVEN__A-unset.tiff", "nscale/bee-2-cpl__ODD__A-unset.tiff"),
    ("coffee-bub lin", "nscale/coffee-bubbles__N19__A-unset.tiff", None),
    ("dry-erase lin", "nscale/dry-erase-marker-head-cpl__N299__A-unset.tiff", None),
    ("leaf-2-cpl lin", "nscale/leaf-2-cpl__N182__A-unset.tiff", None),
    ("paper     lin", "paper/paper__EVEN__A-unset.tiff", "paper/paper__ODD__A-unset.tiff"),
    ("112MSDCF srgb", "bf112/srgb__A-unset.tiff", None),
    ("paper    srgb", "paper/srgb__A-unset.tiff", None),
]

print("Bands = committed contrast_ms.py SIGMAS", st.SIGMAS)
print("slope = FLAT energy(coarsest)/FLAT energy(finest). ORCH's rule: >1 STRUCTURE, <1 NOISE.")
print("sigfrac = split-half Cov(EVEN,ODD)/Var per band at the SAME sites. 1.0 = all real.")
print()
hdr = "%-15s %8s %s  %6s %-10s | %s" % (
    "subject", "clip%", " ".join("%8s" % ("b%d" % j) for j in range(6)),
    "slope", "ORCH says", " ".join("%6s" % ("sf%d" % j) for j in range(6)))
print(hdr)
print("-" * len(hdr))

for lbl, pa, pb in JOBS:
    fa = os.path.join(OUT, pa)
    if not os.path.exists(fa):
        print("%-15s MISSING %s" % (lbl, pa))
        continue
    ge, cm, cf = ns.load64(fa)
    fl, ed, nx = st.sites(ge)
    be = st.octaves(ge)
    ef = [st.energy(fl, b, nx) for b in be]
    slope = ef[-1] / max(ef[0], 1e-30)
    verdict = "STRUCTURE" if slope > 1.0 else "NOISE"
    sfs = ""
    if pb and os.path.exists(os.path.join(OUT, pb)):
        go, _, cf2 = ns.load64(os.path.join(OUT, pb))
        bo = st.octaves(go)
        sfs = " ".join("%6.3f" % st.sigfrac(fl, be[j], bo[j], nx) for j in range(6))
        cf = max(cf, cf2)
    print("%-15s %7.4f %s  %6.3f %-10s | %s"
          % (lbl, 100 * cf, " ".join("%8.2f" % v for v in ef), slope, verdict, sfs))
