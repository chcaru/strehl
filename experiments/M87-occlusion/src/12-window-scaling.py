"""M87 step 12 -- DECISIVE: does the halo scale with the SELECTOR'S WINDOW?

PREDICTION REGISTERED BEFORE RUNNING (this file is committed before it is
executed; see the commit that introduces it).

Two hypotheses now make different, checkable predictions about the same number.

  H_veil  (the dispatch brief's two-layer model): the rim is irreducible
          occlusion physics. Its width is set by the FOREGROUND'S DEFOCUS BLUR
          RADIUS, which is a property of the optics and the sweep, not of the
          merge. Changing the focus-measure window must therefore leave the rim
          width essentially unchanged, and ISO roughly constant.

  H_yoke  (measured mechanism, step 11): a background pixel within the focus
          measure's spatial support of the silhouette has its focus field
          dominated by the FOREGROUND'S edge, because the gradient window
          straddles the silhouette. Those pixels are yoked to the foreground's
          focus decision and elect k ~ k_F, which is the frame in which they are
          LEAST veiled and therefore -- the foreground being dark -- brightest.
          Beyond the support the yoke releases and selection is arbitrary.
          Prediction: rim width scales with WINDOW_RADIUS + REGULARISER_RADIUS,
          and shrinking the support shrinks ISO.

Supporting measurements already in hand (step 11, bee-3-cpl ROI_LEG):
  * percentile rank of the elected value in its own through-focus distribution:
    0.675 in d in [3,25] against 0.429 at d >= 60;
  * median |k_elected - k_F|: 32 near, 96 far;
  * (merge - median_k)/(max_k - median_k) peaks at ~0.48 near d = 6-13 and
    crosses zero at d ~ 33, against a shipped support radius of
    WINDOW_RADIUS + REGULARISER_RADIUS = 13 + 8 = 21 plane px.

Decision rule, fixed now:
  * if d0 (the zero crossing) and ISO both fall by >= 40% when the support is
    cut from 21 px to 8 px, and rise when it is raised to 41 px, H_yoke is
    supported and H_veil is not the operative cause;
  * if d0 and ISO change by < 15% across that 5x range of support, H_yoke is
    refuted and the rim is optics, as the brief argues;
  * anything between is reported as mixed and quantified.

This does not test whether veiling EXISTS -- step 11 shows it does. It tests
whether veiling is the thing that puts a visible rim in the output.
"""

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"

MARGIN = 22
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
ISO = 100.0
SETTINGS = [(3, 2), (5, 3), (13, 8), (25, 16), (41, 24)]


def field(luma, wr, rr):
    g = L.sobel_mag(luma)
    f = L.clamped_box(g, wr) / L.green_luma_sigma(luma, ISO)
    return L.clamped_box(f, rr) if rr > 0 else f


def main():
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    n, h, w = lumas.shape

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]

    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    dr = np.rint(dist).astype(np.int32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True
    bg = inner & (~mask)
    vmed = np.load(CACHE / "11-vmed.npy")
    vmax = np.load(CACHE / "11-vmax.npy")

    res = {}
    for wr, rr in SETTINGS:
        best = np.full((h, w), -np.inf, np.float32)
        arg = np.zeros((h, w), np.int32)
        for k in range(n):
            f = field(np.asarray(lumas[k], np.float32), wr, rr)
            better = f > best
            best[better] = f[better]
            arg[better] = k
        sel = np.take_along_axis(
            np.asarray(lumas, np.float32).reshape(n, -1), arg.reshape(1, -1), axis=0
        ).reshape(h, w) if False else None
        sel = np.empty((h, w), np.float32)
        for k in range(n):
            m = arg == k
            if m.any():
                sel[m] = np.asarray(lumas[k], np.float32)[m]

        r = M2.score_iso(sel, p, nv, boot=500)
        frac = {}
        for d in range(1, 97):
            s = bg & (dr == d)
            if s.sum() < 200:
                continue
            frac[d] = float((sel[s].mean() - vmed[s].mean())
                            / max(vmax[s].mean() - vmed[s].mean(), 1e-6))
        ds = sorted(frac)
        peak = max(ds, key=lambda d: frac[d])
        d0 = next((d for d in ds if d > peak and frac[d] <= 0.0), None)
        support = wr + rr
        res[f"{wr}_{rr}"] = {"wr": wr, "rr": rr, "support": support,
                             "ISO": r["ISO"], "ISO_ci": r["ISO_ci"],
                             "ISO_mean": r["ISO_mean"], "d_star": r["d_star"],
                             "frac_peak_d": peak, "frac_peak": frac[peak],
                             "d0": d0}
        print(f"  wr={wr:3d} rr={rr:3d}  support={support:3d}  "
              f"ISO={r['ISO']:.5f} CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  "
              f"d*={r['d_star']:.0f}  frac peak {frac[peak]:.3f} @d={peak}  "
              f"d0={d0}", flush=True)
        np.save(CACHE / f"12-sel-{wr}-{rr}.npy", sel)

    json.dump(res, open(DATA / "12-window.json", "w"), indent=1)
    print("\nwrote data/12-window.json")


if __name__ == "__main__":
    main()
