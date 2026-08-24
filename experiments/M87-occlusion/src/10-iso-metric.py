"""M87 step 10 -- validate metric v2.2 (isotonic-residual overshoot, ISO).

Runs, on identical boundary points and normals inside ROI_LEG of the cached
bee-3-cpl volume:

  V1  sensitivity : the gate-0 and gate-2 merges
  V4  control C2  : every single frame in the stack (paired, same geometry)
  V2  placebo C1  : the mask translated into empty background
  V3  placebo C3  : a disc planted in flat background

V4 is the primary falsifier. If single frames score anywhere near the merge,
the rim is scene content -- rim light on the hairs -- and not something merging
invented.
"""

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

MARGIN = 22
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)


def rep(tag, r):
    if r is None:
        print(f"  {tag:<30} INSUFFICIENT")
        return
    print(f"  {tag:<30} ISO={r['ISO']:.5f} "
          f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}] "
          f"mean={r['ISO_mean']:.5f} p90={r['ISO_p90']:.5f} "
          f"f>1%={r['frac_gt_01']:.3f} d*={r['d_star']:.0f} n={r['n']}")


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    g2m = np.load(CACHE / "bee3-leg-g2.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    n = lumas.shape[0]

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    print(f"boundary {len(pts)}  valid {val.sum()}", flush=True)

    print("\n--- V1 sensitivity (merges) ---")
    rg0 = M2.score_iso(sel, p, nv)
    rg2 = M2.score_iso(g2m, p, nv)
    rep("merge gate 0", rg0)
    rep("merge gate 2", rg2)

    print("\n--- V4 control C2: single frames, same geometry ---", flush=True)
    kF = int(np.bincount(argbest[mask]).argmax())
    iso_k = np.empty(n)
    for k in range(n):
        f = np.asarray(lumas[k], np.float32)
        r = M2.score_iso(f, p, nv, boot=0)
        iso_k[k] = r["ISO"]
        if k in (0, kF, n - 1) or k % 50 == 0:
            print(f"  frame {k:3d}  ISO={r['ISO']:.5f}  mean={r['ISO_mean']:.5f} "
                  f"p90={r['ISO_p90']:.5f}  f>1%={r['frac_gt_01']:.3f}", flush=True)
    np.save(OUT / "10-iso-k.npy", iso_k)
    print(f"\n  single frames: min {iso_k.min():.5f} (k={int(iso_k.argmin())})  "
          f"median {np.median(iso_k):.5f}  max {iso_k.max():.5f} "
          f"(k={int(iso_k.argmax())})")
    print(f"  merge gate0 {rg0['ISO']:.5f}  =  "
          f"{rg0['ISO'] / max(iso_k.max(), 1e-9):.2f}x the WORST single frame, "
          f"{rg0['ISO'] / max(np.median(iso_k), 1e-9):.2f}x the median frame")

    print("\n--- V2 placebo C1: mask translated into empty background ---")
    best = np.load(CACHE / "bee3-leg-best.npy")
    off = (0, 520)
    sm = np.zeros_like(mask)
    sm[:, off[1]:] = mask[:, :mask.shape[1] - off[1]]
    sp, sn = M2.boundary_normals(sm, roi=INNER)
    sv = M2.valid_profiles(sm, sp, sn, d_max=M2.D_MAX)
    # keep only profiles that never touch the true subject
    keep = ~np.array([mask[np.clip(np.rint(sp[j, 0] + sn[j, 0] * np.arange(65)),
                                   0, mask.shape[0] - 1).astype(int),
                            np.clip(np.rint(sp[j, 1] + sn[j, 1] * np.arange(65)),
                                    0, mask.shape[1] - 1).astype(int)].any()
                      for j in range(len(sp))])
    sv = sv & keep & (~mask[np.clip(np.rint(sp[:, 0]), 0, mask.shape[0] - 1).astype(int),
                            np.clip(np.rint(sp[:, 1]), 0, mask.shape[1] - 1).astype(int)])
    print(f"  shifted boundary {len(sp)}  valid+clean {sv.sum()}")
    rc1 = M2.score_iso(sel, sp[sv], sn[sv])
    rep("C1 shifted mask, gate-0 merge", rc1)

    print("\n--- V3 placebo C3: disc planted in flat background ---")
    # find the largest circle of background that is far from the subject
    dist = ndi.distance_transform_edt(~mask)
    dist[:MARGIN + 80] = 0
    dist[-(MARGIN + 80):] = 0
    dist[:, :MARGIN + 80] = 0
    dist[:, -(MARGIN + 80):] = 0
    cy, cx = np.unravel_index(int(dist.argmax()), dist.shape)
    print(f"  flattest point ({cy},{cx}) at distance {dist[cy, cx]:.0f} from subject")
    yy, xx = np.ogrid[: mask.shape[0], : mask.shape[1]]
    disc = ((yy - cy) ** 2 + (xx - cx) ** 2) <= 40 ** 2
    dp, dn = M2.boundary_normals(disc, roi=INNER)
    dv = M2.valid_profiles(disc, dp, dn, d_max=M2.D_MAX)
    rc3 = M2.score_iso(sel, dp[dv], dn[dv])
    rep("C3 planted disc, gate-0 merge", rc3)

    out = {"kF": kF,
           "gate0": {k: v for k, v in rg0.items() if k not in ("o", "pts", "qt")},
           "gate2": {k: v for k, v in rg2.items() if k not in ("o", "pts", "qt")},
           "C1": {k: v for k, v in rc1.items() if k not in ("o", "pts", "qt")}
           if rc1 else None,
           "C3": {k: v for k, v in rc3.items() if k not in ("o", "pts", "qt")}
           if rc3 else None,
           "frames": {"min": float(iso_k.min()), "median": float(np.median(iso_k)),
                      "max": float(iso_k.max()), "argmax": int(iso_k.argmax())}}
    json.dump(out, open(DATA / "10-iso.json", "w"), indent=1)
    np.save(CACHE / "10-p.npy", p)
    np.save(CACHE / "10-nv.npy", nv)
    np.save(CACHE / "10-o-gate0.npy", rg0["o"])
    np.save(CACHE / "10-pts-gate0.npy", rg0["pts"])
    print("\nwrote data/10-iso.json")


if __name__ == "__main__":
    main()
