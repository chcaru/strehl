"""M87 step 13 -- arm F2: two-layer unmixing, the simplest version that can work.

Model, per background pixel x, after dividing every frame by its own global
level L(k) so that the sweep's 18.09% photometric drift cannot enter the fit:

    Itilde_k(x)  =  B(x) + alpha_k(x) * ( F(x) - B(x) )

with alpha_k(x) = ( m * G_{sigma_k} )(x), m the foreground matte and
sigma_k = c * |k - k_F| the foreground's defocus blur at frame k.  That is a
straight line in alpha, so the unveiled background is simply the INTERCEPT of a
two-parameter least-squares fit of Itilde_k against alpha_k across the stack --
the value the pixel would have at alpha = 0, i.e. with the foreground's
defocused contribution subtracted.

Detector (deliberately NOT bimodality; M63 refuted bimodality as an occlusion
detector, facts 967-969).  The fit is only applied where the model has
LEVERAGE:

    max_k alpha_k(x) >= A_MIN          the pixel is veiled at all
    range_k alpha_k(x) >= A_RANGE      the veiling actually varies, so the
                                       intercept is identified
    R^2 >= R_MIN                       the line describes the data

Everywhere else the merge is passed through untouched, so the placebo bar X2 is
satisfied by construction and the interesting number is the detector's
FALSE-POSITIVE RATE: how much of a region with no occluding edge it claims.

One free parameter, c, calibrated by grid search on median R^2.  Deliberate
breakage for bar X4: c x 2, c x 0.5, and swapped layer order (alpha -> 1-alpha).
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
A_MIN = 0.05
A_RANGE = 0.05
R_MIN = 0.50
C_GRID = [0.02, 0.05, 0.10, 0.20, 0.40, 0.80]


def fit(lumas, matte, kF, c, gain, swap=False):
    """Accumulate the per-pixel regression of Itilde_k on alpha_k."""
    n, h, w = lumas.shape
    s1 = np.zeros((h, w), np.float64)
    sa = np.zeros((h, w), np.float64)
    saa = np.zeros((h, w), np.float64)
    si = np.zeros((h, w), np.float64)
    sai = np.zeros((h, w), np.float64)
    sii = np.zeros((h, w), np.float64)
    amax = np.full((h, w), -np.inf, np.float32)
    amin = np.full((h, w), np.inf, np.float32)
    for k in range(n):
        sig = c * abs(k - kF)
        a = ndi.gaussian_filter(matte, sig) if sig > 0.3 else matte.copy()
        if swap:
            a = 1.0 - a
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
    b = (s1 * sai - sa * si) / den
    a0 = (si - b * sa) / s1
    ss_tot = sii - si * si / s1
    ss_res = sii - a0 * si - b * sai
    r2 = 1.0 - ss_res / np.where(ss_tot < 1e-9, np.nan, ss_tot)
    return a0.astype(np.float32), b.astype(np.float32), r2.astype(np.float32), \
        amax, amin


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    Lk = np.load(OUT / "05-Lk.npy")
    n, h, w = lumas.shape
    gain = (np.median(Lk) / Lk).astype(np.float32)
    kF = int(np.bincount(argbest[mask]).argmax())
    matte = mask.astype(np.float32)
    print(f"k_F={kF}  n={n}", flush=True)

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]

    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True
    band = inner & (~mask) & (dist >= 2) & (dist <= 40)

    print("\ncalibrating c (median R^2 over the near-edge band):", flush=True)
    best_c, best_r2 = None, -np.inf
    cal = {}
    for c in C_GRID:
        _, _, r2, _, _ = fit(lumas, matte, kF, c, gain)
        m = float(np.nanmedian(r2[band]))
        cal[c] = m
        print(f"  c={c:5.2f} px/frame   median R^2 = {m:.4f}", flush=True)
        if m > best_r2:
            best_c, best_r2 = c, m
    print(f"  -> c = {best_c} (median R^2 {best_r2:.4f})")

    variants = {
        "F2": (best_c, False),
        "F2-break-psf-x2": (best_c * 2, False),
        "F2-break-psf-half": (best_c * 0.5, False),
        "F2-break-swap": (best_c, True),
    }
    base = M2.score_iso(sel, p, nv, boot=500)
    print(f"\nF0 shipped-semantics merge : ISO={base['ISO']:.5f} "
          f"CI[{base['ISO_ci'][0]:.5f},{base['ISO_ci'][1]:.5f}]")

    res = {"c": best_c, "cal": cal, "kF": kF,
           "F0": {k: v for k, v in base.items() if k not in ("o", "pts", "qt")}}
    for tag, (c, swap) in variants.items():
        a0, b, r2, amax, amin = fit(lumas, matte, kF, c, gain, swap)
        apply = (~mask) & (amax >= A_MIN) & ((amax - amin) >= A_RANGE) \
            & np.isfinite(r2) & (r2 >= R_MIN) & np.isfinite(a0)
        fixed = sel.copy()
        fixed[apply] = (a0[apply] / gain[argbest[apply]]).astype(np.float32)
        r = M2.score_iso(fixed, p, nv, boot=500)
        cov_band = float(apply[band].mean())
        cov_far = float(apply[inner & (~mask) & (dist >= 60)].mean())
        res[tag] = {"c": c, "swap": swap, "coverage_band": cov_band,
                    "coverage_far": cov_far,
                    **{k: v for k, v in r.items() if k not in ("o", "pts", "qt")}}
        print(f"  {tag:<20} ISO={r['ISO']:.5f} "
              f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  "
              f"({100 * (1 - r['ISO'] / base['ISO']):+.1f}% vs F0)  "
              f"coverage band {cov_band:.3f} far {cov_far:.3f}", flush=True)
        np.save(CACHE / f"13-{tag}.npy", fixed)
        if tag == "F2":
            np.save(CACHE / "13-apply.npy", apply)
            np.save(CACHE / "13-r2.npy", r2)
            np.save(CACHE / "13-amax.npy", amax)

    json.dump(res, open(DATA / "13-unmix.json", "w"), indent=1)
    print("\nwrote data/13-unmix.json")


if __name__ == "__main__":
    main()
