"""IS THE FLAGGED ELEVATION ISOTROPIC (a halo) OR DIRECTIONAL (a scene gradient)?

A rim artifact surrounds the silhouette: it should raise the near bands on EVERY
side. A graduated backdrop or a lit falloff raises one side and lowers the other,
and a single global far-field median averages the two -- so the near band on the
bright side reads elevated against a reference that does not describe it.

METHOD. Reproduce halo_profile's geometry exactly, then cut the background into
8 angular sectors about the dominant component's centroid. For each sector
measure its OWN far-field level and its own near-band profile, and score the
overshoot twice:

    over_global : near bands referenced to the ONE global far field (what the
                  instrument does today)
    over_local  : near bands referenced to THAT SECTOR'S far field

If over_global is large and over_local collapses, the elevation is a property of
the reference, not of the near field -- ORCH hypothesis 3. If over_global is
positive in only a few sectors while its opposite sectors go negative, it is
directional -- hypothesis 1.

CLEAN SUBJECTS ARE INCLUDED AS CONTROLS. A far-field spread of N DN means
nothing until you know what N is on a subject nobody disputes.
"""
import json, os, sys
import numpy as np
from scipy.ndimage import (binary_closing, binary_opening, distance_transform_edt,
                           label)

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

CACHE = r"D:\strehl-out\V-REVIEW\halo\cache"
NSEC = 8
SUB = 4

FLAGGED = ["flat-on-ruler-cpl", "tweezers-cpl", "lavendar-cpl", "119MSDCF"]
CONTROL = ["bee-1-cpl", "pencil-flatter-angle-cpl", "couch-fibers-cpl",
           "flowers-cpl", "leaf-2-cpl", "dry-erase-marker-head-cpl"]


def geometry(y):
    t, subj = H.segment(y)
    lab, nlab = label(subj)
    sizes = np.bincount(lab.ravel())[1:]
    dom = int(np.argmax(sizes)) + 1
    d, ind = distance_transform_edt(~subj, return_indices=True)
    d = d * SUB
    own = (lab[ind[0], ind[1]] == dom) & (~subj)
    far = (d >= H.FAR[0]) & (d < H.FAR[1])
    ys, xs = np.nonzero(lab == dom)
    return d, own, far, float(ys.mean()), float(xs.mean())


def run(stem):
    a = np.load(os.path.join(CACHE, stem + ".tiff.npy"))
    y = a[::2, ::2]                      # cache is sub=2; instrument walks sub=4
    d, own, far, cy, cx = geometry(y)
    gl = float(np.median(y[far]))

    yy, xx = np.mgrid[0:y.shape[0], 0:y.shape[1]]
    ang = np.arctan2(yy - cy, xx - cx)
    sec = ((ang + np.pi) / (2 * np.pi) * NSEC).astype(int) % NSEC

    rows = []
    for s in range(NSEC):
        m_far = far & (sec == s)
        if int(m_far.sum()) < H.MIN_BANDPX:
            rows.append((s, None, None, None, int(m_far.sum())))
            continue
        loc = float(np.median(y[m_far]))
        vg, vl = [], []
        for lo, hi in H.NEAR:
            m = own & (sec == s) & (d >= lo) & (d < hi)
            if int(m.sum()) <= H.MIN_BANDPX:
                continue
            med = float(np.median(y[m]))
            vg.append(med - gl)
            vl.append(med - loc)
        if len(vg) < 3:
            rows.append((s, loc, None, None, int(m_far.sum())))
            continue
        rows.append((s, loc, max(vg), max(vl), int(m_far.sum())))

    levels = [r[1] for r in rows if r[1] is not None]
    og = [r[2] for r in rows if r[2] is not None]
    ol = [r[3] for r in rows if r[3] is not None]
    return {
        "stem": stem, "global_far": gl,
        "sector_far_min": min(levels) if levels else None,
        "sector_far_max": max(levels) if levels else None,
        "sector_far_spread": (max(levels) - min(levels)) if levels else None,
        "n_sectors": len(og),
        "over_global": og, "over_local": ol,
        "pos_global": sum(1 for v in og if v > 200),
        "pos_local": sum(1 for v in ol if v > 200),
        "max_global": max(og) if og else None,
        "max_local": max(ol) if ol else None,
    }


out = []
print("%-27s %8s %9s %7s %7s %7s %7s" % (
    "subject", "farfield", "far-spread", "maxOG", "maxOL", "pos/8G", "pos/8L"))
print("-" * 82)
for group, stems in (("FLAGGED", FLAGGED), ("CONTROL (clean)", CONTROL)):
    print("-- %s" % group)
    for s in stems:
        r = run(s)
        out.append(r)
        print("%-27s %8.0f %9.0f %7s %7s %5d/%d %5d/%d" % (
            s, r["global_far"], r["sector_far_spread"] or -1,
            ("%.0f" % r["max_global"]) if r["max_global"] is not None else "-",
            ("%.0f" % r["max_local"]) if r["max_local"] is not None else "-",
            r["pos_global"], r["n_sectors"], r["pos_local"], r["n_sectors"]))

with open(r"D:\strehl-out\V-REVIEW\halo\sector.json", "w") as fh:
    json.dump(out, fh, indent=1)
print("\nmaxOG = worst near-band elevation using the ONE global far field")
print("maxOL = same, but each sector referenced to its OWN far field")
print("pos/8 = sectors whose elevation exceeds the 200 DN bar (isotropy count)")
