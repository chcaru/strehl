"""Re-walk the 4 clean-but-blind subjects past the cell-pinch truncation.

The truncation is not arbitrary: its comment says the surviving pixels are "a
directional sliver, and their median is not the background level at that
distance". So simply deleting it would measure the artifact it guards against.
The question is therefore not "what is the median out there" but "is that
median entitled to be read as a background level".

DISCRIMINATOR: a real rim surrounds the silhouette; a sliver points one way.
For every band I report angular COVERAGE about the dominant part's centroid
(fraction of 16 azimuth bins holding >=20 px) and the spread of the per-bin
medians. A band with low coverage or huge azimuthal spread is a sliver and its
median carries no verdict.

Controls: two subjects that complete a full 7/7 walk, measured identically. A
coverage number means nothing without knowing what a healthy band scores.
"""
import os, sys, json
import numpy as np, tifffile
from scipy.ndimage import distance_transform_edt, label

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
BLIND = ["leaf-2-cpl", "lead-1-cpl", "couch-fibers-cpl", "pencil-flatter-angle-cpl"]
CTRL  = ["bee-1-cpl", "flower-bud-alone-cpl"]
NB = 16
MINBIN = 20

def walk(stem):
    y = H.luma(tifffile.imread(os.path.join(FAITH, stem + ".tiff")))
    ys = y[::4, ::4]
    t, subj = H.segment(ys)
    lab, n = label(subj)
    sizes = np.bincount(lab.ravel())[1:]
    dom = int(np.argmax(sizes)) + 1
    d, ind = distance_transform_edt(~subj, return_indices=True); d = d * 4
    own = (lab[ind[0], ind[1]] == dom) & (~subj)
    far = (d >= 400) & (d < 900)
    fl = float(np.median(ys[far])) if far.sum() > 200 else float("nan")
    yy, xx = np.nonzero(lab == dom)
    cy, cx = yy.mean(), xx.mean()
    gy, gx = np.mgrid[0:ys.shape[0], 0:ys.shape[1]]
    ang = np.arctan2(gy - cy, gx - cx)
    abin = ((ang + np.pi) / (2 * np.pi) * NB).astype(int) % NB
    out = []
    dens0 = None
    for lo, hi in H.NEAR:
        m = own & (d >= lo) & (d < hi)
        npx = int(m.sum())
        dens = npx / float(hi - lo)
        if dens0 is None: dens0 = dens
        ratio = dens / dens0 if dens0 > 0 else 0.0
        if npx <= H.MIN_BANDPX:
            out.append(dict(lo=lo, hi=hi, n=npx, dens=ratio, med=None, cov=0.0, spread=None)); continue
        med = float(np.median(ys[m])) - fl
        bins = []
        for b in range(NB):
            mb = m & (abin == b)
            if int(mb.sum()) >= MINBIN:
                bins.append(float(np.median(ys[mb])) - fl)
        cov = len(bins) / float(NB)
        spread = (max(bins) - min(bins)) if len(bins) >= 2 else None
        p90 = float(np.percentile(ys[m], 90)) - fl
        out.append(dict(lo=lo, hi=hi, n=npx, dens=ratio, med=med, cov=cov,
                        spread=spread, nbins=len(bins), p90=p90))
    return out, fl

res = {}
for stem in BLIND + CTRL:
    prof, fl = walk(stem)
    res[stem] = prof
    kind = "BLIND" if stem in BLIND else "control(7/7)"
    print("\n=== %-26s %-13s farfield %.0f ===" % (stem, kind, fl))
    print("   band      n px   dens   median DN   azim.cov   azim.spread   p90 DN   status")
    for b in prof:
        pinched = b["dens"] < H.MIN_CELL_DENS
        st = "PINCHED (walk stopped here)" if pinched else ""
        if b["med"] is None:
            print("   %3d-%-3d %7d  %5.2f      -           -            -          -    too few px" % (
                b["lo"], b["hi"], b["n"], b["dens"])); continue
        print("   %3d-%-3d %7d  %5.2f  %+9.1f    %4.0f%%     %9s  %+8.1f   %s" % (
            b["lo"], b["hi"], b["n"], b["dens"], b["med"], b["cov"] * 100,
            ("%.0f" % b["spread"]) if b["spread"] is not None else "-", b["p90"], st))

json.dump(res, open(r"D:\strehl-out\V-REVIEW\halo\blind.json", "w"), indent=1)
print("\n\nVERDICT INPUT: leaf-2-cpl 50-80 px band")
b = [x for x in res["leaf-2-cpl"] if x["lo"] == 50][0]
print("   median %+.1f DN from %d px, azimuthal coverage %.0f%% (%d/%d bins)" % (
    b["med"], b["n"], b["cov"] * 100, b["nbins"], NB))
print("   azimuthal spread of per-direction medians: %.0f DN" % b["spread"])
print("   cell density has fallen to %.1f%% of the innermost band" % (b["dens"] * 100))
ctl = [x for x in res["bee-1-cpl"] if x["lo"] == 50][0]
print("   control bee-1-cpl same band: coverage %.0f%%, spread %.0f DN, density %.0f%%" % (
    ctl["cov"] * 100, ctl["spread"], ctl["dens"] * 100))
