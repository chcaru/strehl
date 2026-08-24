"""M87 step 17 -- does PER-PIXEL depth rescue the unmixing on real data?

On the plant (step 16) the two-layer unmixing works: with the modelled alpha it
recovers the known unveiled background to RMSE 1.71% of level and takes ISO from
0.0306 to 0.0065, a 79% reduction. On bee-3-cpl (step 13) the same estimator
moved ISO by +3.7% and fitted with median R^2 = 0.131.

The most obvious difference between the two: the plant has ONE global k_F,
because its occluder is a flat bar at a single depth. The bee's leg spans depth,
so |k - k_F| -- and therefore sigma_k, and therefore alpha_k -- is a per-pixel
quantity, and step 13 forced a single global k_F on the whole subject.

Test: take k_F per pixel from the merge's own elected-frame map inside the
subject, propagate it into the background by nearest subject pixel, quantise
into NBIN depth bins, and build alpha_k per bin. If the unmixing now works, the
step-13 negative was a depth-resolution failure and the Rust recipe must carry a
per-pixel k_F. If it still fails, the two-layer model does not describe this
scene.
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
NBIN = 10
C_GRID = [0.1, 0.2, 0.4, 0.8]
A_MIN, A_RANGE, R_MIN = 0.05, 0.05, 0.50


def main():
    grid = [float(x) for x in sys.argv[1:]] or C_GRID
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    Lk = np.load(OUT / "05-Lk.npy")
    n, h, w = lumas.shape
    gain = (np.median(Lk) / Lk).astype(np.float32)

    # per-pixel k_F: the elected frame inside the subject, median-smoothed to
    # suppress speckle, then propagated outward by nearest subject pixel.
    kf_in = ndi.median_filter(argbest.astype(np.float32), size=15)
    _, (iy, ix) = ndi.distance_transform_edt(~mask, return_indices=True)
    kf = kf_in[iy, ix].astype(np.float32)
    print(f"k_F map: min {kf.min():.0f} median {np.median(kf):.0f} "
          f"max {kf.max():.0f}", flush=True)

    edges = np.quantile(kf, np.linspace(0, 1, NBIN + 1))
    edges[0] -= 1
    edges[-1] += 1
    binid = np.clip(np.digitize(kf, edges[1:-1]), 0, NBIN - 1)
    centres = np.array([np.median(kf[binid == j]) for j in range(NBIN)])
    print("bin centres:", np.round(centres).astype(int))

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True
    band = inner & (~mask) & (dist >= 2) & (dist <= 40)
    matte = mask.astype(np.float32)

    base = M2.score_iso(sel, p, nv, boot=500)
    print(f"\nF0 : ISO={base['ISO']:.5f}", flush=True)
    res = {"F0_ISO": base["ISO"]}

    for c in grid:
        s1 = np.zeros((h, w), np.float64)
        sa = np.zeros((h, w), np.float64)
        saa = np.zeros((h, w), np.float64)
        si = np.zeros((h, w), np.float64)
        sai = np.zeros((h, w), np.float64)
        sii = np.zeros((h, w), np.float64)
        amax = np.full((h, w), -np.inf, np.float32)
        amin = np.full((h, w), np.inf, np.float32)
        for k in range(n):
            a = np.empty((h, w), np.float32)
            for j in range(NBIN):
                sig = c * abs(k - centres[j])
                blur = ndi.gaussian_filter(matte, sig) if sig > 0.3 else matte
                m = binid == j
                a[m] = blur[m]
            v = np.asarray(lumas[k], np.float32) * gain[k]
            s1 += 1.0
            sa += a
            saa += a * a
            si += v
            sai += a * v
            sii += v * v
            np.maximum(amax, a, out=amax)
            np.minimum(amin, a, out=amin)
        den = s1 * saa - sa * sa
        den = np.where(np.abs(den) < 1e-9, np.nan, den)
        bslope = (s1 * sai - sa * si) / den
        a0 = (si - bslope * sa) / s1
        ss_tot = sii - si * si / s1
        ss_res = sii - a0 * si - bslope * sai
        r2 = 1.0 - ss_res / np.where(ss_tot < 1e-9, np.nan, ss_tot)

        apply = (~mask) & (amax >= A_MIN) & ((amax - amin) >= A_RANGE) \
            & np.isfinite(r2) & (r2 >= R_MIN) & np.isfinite(a0)
        fixed = sel.copy()
        fixed[apply] = (a0[apply] / gain[argbest[apply]]).astype(np.float32)
        r = M2.score_iso(fixed, p, nv, boot=500)
        med_r2 = float(np.nanmedian(r2[band]))
        print(f"  c={c:4.2f}  medR2(band)={med_r2:.4f}  "
              f"cover band={apply[band].mean():.3f}  "
              f"ISO={r['ISO']:.5f} ({100 * (1 - r['ISO'] / base['ISO']):+.1f}%)",
              flush=True)
        res[f"c{c}"] = {"median_r2": med_r2, "coverage_band": float(apply[band].mean()),
                        "ISO": r["ISO"], "ISO_ci": r["ISO_ci"]}
        np.save(CACHE / f"17-fixed-c{c}.npy", fixed)

    json.dump(res, open(DATA / f"17-perpixel{'' if grid == C_GRID else '-ext'}.json",
                        "w"), indent=1)
    print("\nwrote data/17-perpixel.json")


if __name__ == "__main__":
    main()
