"""M87 step 8 -- the PAIRED edge-normal comparison: merge vs every single frame.

Step 7 showed the mean edge-normal profile of the merge rising monotonically to
its far value with no overshoot, which is not what the eye sees. The reason is
that "should be" has no absolute reference: the card is not stationary, so
q_j(d) mixes halo with scene.

There is, however, a physically realisable paired reference. A SINGLE EXPOSURE
of this scene has a monotone edge-spread profile by construction -- one lens,
one focus, one convolution. Whatever the merge has that no single frame has,
the merge invented. So measure

    Delta_k(d) = qbar_merge(d) - qbar_frame_k(d)

on the SAME boundary points, the SAME normals, each profile normalised by its
OWN far value in each image. A positive bump in Delta at small d is a bright
rim the merge created; Delta == 0 everywhere means the rim is scene content.

This is control C2 from PREREGISTRATION section 3, executed as an exactly
paired test, and it is the primary falsifier W1.

Also emitted:
  * the envelope max_k qbar_k(d) and min_k qbar_k(d) -- the merge cannot leave
    the envelope, since a gate-0 merge writes one frame's value per pixel, so
    the envelope is a hard sanity check on the whole construction;
  * per-profile Delta_j for the false-positive accounting and for the map.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

MARGIN = 22
ROI = (1200, 1900, 300, 1400)
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
DMAX = 96
DBASE = (80, 96)


def qbar_of(img, p, nv, dmax=DMAX, dbase=DBASE):
    prof, _, _ = M2.sample_profiles(img, p, nv, dmax)
    b = np.median(prof[:, dbase[0]:dbase[1] + 1], axis=1)
    ok = b > 1.0
    q = prof / np.where(ok, b, 1.0)[:, None]
    q[~ok] = np.nan
    return np.nanmean(q, axis=0), q


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    g2m = np.load(CACHE / "bee3-leg-g2.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    n = lumas.shape[0]

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=DMAX)
    p, nv = pts[val], nrm[val]
    print(f"boundary {len(pts)}  valid {val.sum()}", flush=True)

    qm, qm_j = qbar_of(sel, p, nv)
    qg2, _ = qbar_of(g2m, p, nv)

    qk = np.empty((n, DMAX + 1), np.float64)
    for k in range(n):
        f = np.asarray(lumas[k], np.float32)
        qk[k], _ = qbar_of(f, p, nv)
        if k % 50 == 0:
            print(f"  frame {k}", flush=True)
    np.save(OUT / "08-qk.npy", qk)
    np.save(OUT / "08-qm.npy", qm)
    np.save(OUT / "08-qg2.npy", qg2)

    env_hi = np.nanmax(qk, axis=0)
    env_lo = np.nanmin(qk, axis=0)
    qk_med = np.nanmedian(qk, axis=0)

    kF = int(np.bincount(argbest[mask]).argmax())
    print(f"\nmodal elected frame inside the mask (k_F) = {kF}")

    print("\n  d   qbar_merge  qbar_gate2   qbar_kF   qbar_med_k   env_lo   env_hi"
          "    D_kF     D_med")
    for d in range(0, DMAX + 1):
        print(f"{d:4d}   {qm[d]:9.4f}  {qg2[d]:9.4f}  {qk[kF][d]:9.4f}  "
              f"{qk_med[d]:9.4f}  {env_lo[d]:7.4f}  {env_hi[d]:7.4f}  "
              f"{qm[d] - qk[kF][d]:+7.4f}  {qm[d] - qk_med[d]:+7.4f}")

    def bump(delta, lo=2, hi=48):
        seg = delta[lo:hi + 1]
        i = int(np.nanargmax(seg)) + lo
        return float(seg.max()), i

    for tag, ref in (("kF", qk[kF]), ("median-frame", qk_med),
                     ("best-frame(min bump)", None)):
        if ref is None:
            amps = [bump(qm - qk[k])[0] for k in range(n)]
            j = int(np.argmin(amps))
            a, d = bump(qm - qk[j])
            print(f"\nBUMP vs {tag}: k={j}  amplitude {a:+.4f} at d={d}")
        else:
            a, d = bump(qm - ref)
            print(f"\nBUMP vs {tag}: amplitude {a:+.4f} at d={d}")

    json.dump({"kF": kF, "n": int(val.sum())},
              open(DATA / "08-paired.json", "w"), indent=1)
    np.save(CACHE / "08-pts.npy", p)
    np.save(CACHE / "08-nrm.npy", nv)
    np.save(CACHE / "08-qmj.npy", qm_j.astype(np.float32))


if __name__ == "__main__":
    main()
