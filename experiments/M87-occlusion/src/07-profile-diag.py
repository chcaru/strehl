"""M87 step 7 -- LOOK at the mean edge-normal profile before redesigning again.

v2.1 scored ROI_LEG at O = -0.017 with d* pinned at the top of the search
window, which says the search window [4,32] and the baseline window [48,64] are
both inside the edge transition, not outside it. Print the actual curve, at
d_max = 128, for the merge and -- paired, same points, same normals -- for
single frames. Then choose the windows from the data and register them.
"""

import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DMAX = 128


def main():
    g = tifffile.imread(r"C:\dev\strehl-out\bee3-g0.tif")[..., 1].astype(np.float32)
    mask, tau = L.foreground_mask(g)
    roi = L.ROIS["ROI_LEG"]
    pts, nrm = M2.boundary_normals(mask, roi=roi)
    val = M2.valid_profiles(mask, pts, nrm, d_max=DMAX)
    print(f"boundary pts {len(pts)}  valid {val.sum()}", flush=True)
    p, nv = pts[val], nrm[val]

    prof, _, _ = M2.sample_profiles(g, p, nv, d_max=DMAX)
    b = np.median(prof[:, 110:129], axis=1)
    good = b > 1.0
    q = prof[good] / b[good][:, None]
    qbar = q.mean(axis=0)
    qmed = np.median(q, axis=0)

    # placebo, same treatment
    sm = L.shifted_mask(mask)
    sroi = (roi[0] + 512, min(roi[1] + 512, g.shape[0]),
            roi[2] + 512, min(roi[3] + 512, g.shape[1]))
    sp, sn = M2.boundary_normals(sm, roi=sroi)
    sv = M2.valid_profiles(sm, sp, sn, d_max=DMAX)
    sprof, _, _ = M2.sample_profiles(g, sp[sv], sn[sv], d_max=DMAX)
    sb = np.median(sprof[:, 110:129], axis=1)
    sg = sb > 1.0
    sq = sprof[sg] / sb[sg][:, None]
    sbar = sq.mean(axis=0)

    print("\n  d   qbar_LEG   qmed_LEG   qbar_C1shift")
    for d in range(0, DMAX + 1):
        print(f"{d:4d}   {qbar[d]:8.4f}   {qmed[d]:8.4f}   {sbar[d]:8.4f}")

    np.save(OUT / "07-qbar-leg.npy", qbar)
    np.save(OUT / "07-qbar-c1.npy", sbar)
    np.save(CACHE / "07-pts.npy", p[good] if good.shape[0] == p.shape[0] else p)


if __name__ == "__main__":
    main()
