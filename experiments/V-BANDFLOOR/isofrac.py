r"""Isolated fraction: what share of each subject's strong edges the rim axis
can speak to at all. rimv6 excludes edges still climbing at t=+7 px, because
max(q[+2..+7]) is not a rim measurement on them. rimaxis reports this per
subject and this lane must too -- a clean number over a quarter of the edges is
not a clean number over the subject.
"""
import os, sys
import numpy as np
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-GATHER")))
import rimv6, rimaxis, rimab
OUT = r"C:\dev\strehl-out\V-BANDFLOOR"
print("%-22s %8s %8s %9s %7s" % ("subject", "n_sel", "n_all", "isolated", "cut"))
for s in sys.argv[1:]:
    a = os.path.join(OUT, s + "__A-unset.tiff")
    b = os.path.join(OUT, s + "__B-coarse8.tiff")
    if not (os.path.exists(a) and os.path.exists(b)):
        print("%-22s MISSING" % s); continue
    gA, cmA, _ = rimab.load(a)
    gB, cmB, _ = rimab.load(b)
    cm = cmA | cmB
    gm = 0.5 * (gA + gB)
    rois = rimaxis.pick_rois(gm, cm, n=rimab.NTILE)
    ref = ndimage.gaussian_filter(gm, rimab.SMOOTH).astype(np.float32)
    best = rimab.choose(ref, cm, rois)
    cut, sel = best[1], best[2]
    n_all = len(rimv6.select(ref, cm, rois, rimab.T, cut, min_reach=-1e9))
    print("%-22s %8d %8d %8.1f%% %7.2f" % (s, len(sel), n_all,
          100.0*len(sel)/max(n_all,1), cut))
    del gA, gB, gm, ref
