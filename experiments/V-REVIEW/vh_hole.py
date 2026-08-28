"""RIM OR GRADIENT? Fill the instrument's unmeasured 120-400 px hole.

halo_profile measures d=2..120 then jumps to the 400-900 far field. A halo is
a LOCAL rim: it must decay to the background within roughly 100 px. A lighting
falloff across a flat card declines smoothly over the whole frame. Those two
are indistinguishable inside 120 px and trivially distinguishable across 400.

Also prints what the REAL profile() reports, so any disagreement with my own
band walk is visible rather than assumed.
"""
import os, sys
import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, label

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
FINE = [(2,6),(6,12),(12,20),(20,32),(32,50),(50,80),(80,120),(120,170),
        (170,230),(230,300),(300,400),(400,550),(550,700),(700,900)]
SUBS = ["flat-on-ruler-cpl","tweezers-cpl","lavendar-cpl","119MSDCF",
        "bee-1-cpl","leaf-2-cpl","flower-bud-alone-cpl","bee-2-cpl"]
FLAG = {"flat-on-ruler-cpl":"HALO","tweezers-cpl":"HALO","lavendar-cpl":"HALO",
        "119MSDCF":"HALO"}

print("%-24s %-6s %9s %9s  %s" % ("subject","known","overshoot","bump","real profile() verdict"))
rows = {}
for stem in SUBS:
    f = os.path.join(FAITH, stem + ".tiff")
    if not os.path.exists(f):
        print("%-24s MISSING" % stem); continue
    y = H.luma(tifffile.imread(f))
    v, ov, bp, pen, fl, bands, why = H.profile(y)
    print("%-24s %-6s %9s %9s  %s %s" % (
        stem, FLAG.get(stem,"clean"),
        ("%.1f"%ov) if ov is not None else "-",
        ("%.1f"%bp) if bp is not None else "-", v, why or ""))

    ys = y[::4,::4]
    t, subj = H.segment(ys)
    lab, n = label(subj)
    dom = int(np.argmax(np.bincount(lab.ravel())[1:]))+1
    d, ind = distance_transform_edt(~subj, return_indices=True); d = d*4
    own = (lab[ind[0],ind[1]]==dom) & (~subj)
    far = (d>=400)&(d<900)
    flv = float(np.median(ys[far]))
    prof = []
    for lo,hi in FINE:
        m = own & (d>=lo) & (d<hi)
        prof.append((lo,hi,float(np.median(ys[m]))-flv if int(m.sum())>200 else None,int(m.sum())))
    rows[stem] = prof

print("\n\nRADIAL PROFILE THROUGH THE HOLE (DN relative to 400-900 far field)")
print("     the instrument sees only the first 7 columns")
hdr = "%-24s" % "subject"
for lo,hi in FINE: hdr += "%9s" % ("%d-%d"%(lo,hi))
print(hdr)
print("-"*len(hdr))
for stem in SUBS:
    if stem not in rows: continue
    line = "%-24s" % (stem + (" *" if stem in FLAG else ""))
    for lo,hi,v,n in rows[stem]:
        line += "%9s" % (("%+.0f"%v) if v is not None else ".")
    print(line)

print("\nDECAY TEST: a rim must be gone by 170 px. value at 120-170 as %% of peak")
for stem in SUBS:
    if stem not in rows: continue
    p = {(lo,hi):v for lo,hi,v,n in rows[stem]}
    pk = max([v for (lo,hi),v in p.items() if v is not None and hi<=120], default=None)
    nxt = p.get((120,170)); n2 = p.get((230,300))
    if pk is None or pk <= 0:
        print("  %-24s peak<=0, not a rim candidate" % stem); continue
    print("  %-24s peak %+7.0f  ->120-170 %s (%s)  ->230-300 %s (%s)" % (
        stem, pk,
        ("%+7.0f"%nxt) if nxt is not None else "  n/a",
        ("%3.0f%%"%(100*nxt/pk)) if nxt is not None else " - ",
        ("%+7.0f"%n2) if n2 is not None else "  n/a",
        ("%3.0f%%"%(100*n2/pk)) if n2 is not None else " - "))
