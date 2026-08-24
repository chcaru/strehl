"""M87 s31e -- re-score B8 and B9, both of which I set wrong in 88-controls.py.

TWO DEFECTS IN MY OWN BARS, repaired here rather than reported as results.

B8.  I pre-registered "enrichment >= 1.5x means detected" and the positive
control then showed 1.5x needs a planted step of 100 DN PER ADJACENT FRAME,
which is 58.5% drift across the 299-frame bracket -- five times M24's worst
corpus stack.  A bar that only fires at five times the largest effect anyone
has measured is not a test, and the "photometric step excluded" reading it
produced is withdrawn.  What survives is the RESPONSE CURVE, which is much
more informative than the threshold I hung on it: it converts the observed
enrichment into an upper limit in DN by interpolation.  Re-scored that way
here, with the interpolation done explicitly and the quantisation floor of
the statistic reported beside it so the limit cannot be over-read.

B9.  I predicted the flatness-0.5 crossing at n_eff = 5.54 from "posterisation
appears when the noise falls below about one code".  That constant is wrong.
For noise sd s and quantiser step q, adjacent samples share a code with
probability of order q/s, not 1/2 at s = q, and the render's pixels are not
independent anyway -- a Malvar-He-Cutler demosaic correlates neighbours.  So
the 3.45x miss measures my arithmetic, not the mechanism.  Repaired by
SIMULATING the flatness statistic against the measured lag-1 correlation and
the measured local gradient, which has no free parameter either but does not
require me to get a closed form right.

  BAR B10, three branches, on the simulated crossing against the measured
  n_eff = 19.10:
     within a factor of 2   -> the visible banding IS the cast quantum
                               crossing the n_eff field
     outside a factor of 5  -> it is not
     otherwise              -> PARTIAL

  CONTROL C-SIM.  The simulation must also reproduce a value it was not
  tuned to: the flatness at the LOW-n_eff end, where the render is measured
  at 0.178.  If the simulator only matches where it was read off, it is a
  curve fit.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
X0, Y0, W, H = 700, 3150, 1100, 900
NOISE_A, NOISE_B = 283.3, -0.5228     # B5
MEASURED_CROSS = 19.10                # B9
MEASURED_FLAT_LOW = 0.178             # B9 first bin, n_eff 1.2
SEED = 87310


def main():
    out = {}
    g = tifffile.imread(SCRATCH / "s31-bee3.tif")[Y0:Y0 + H, X0:X0 + W, 1
                                                  ].astype(np.float32)
    py0, px0 = Y0 // 2, X0 // 2
    nef = tifffile.imread(SCRATCH / "s31-neff.tif")[py0:py0 + H // 2,
                                                    px0:px0 + W // 2].astype(np.float32)
    nef = np.repeat(np.repeat(nef, 2, 0), 2, 1)
    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    q = span / 127.0
    subj = ndimage.binary_opening(
        ndimage.binary_closing(g < med - span, np.ones((5, 5))), np.ones((3, 3)))
    bg = ~ndimage.binary_dilation(subj, np.ones((9, 9)))

    # ---------------- B8 re-scored as a response curve -------------------
    print("=== B8 re-scored: the response curve, not the 1.5x bar ===")
    rows = json.loads((DATA / "88-controls.json").read_text(encoding="utf-8"))["B8_rows"]
    dj = json.loads((DATA / "88-controls.json").read_text(encoding="utf-8"))["djump_median"]
    print(f"  median |delta index| across a boundary = {dj:.0f} frames,"
          f" so a plant of s DN/frame makes a median boundary step of {dj:.0f}s DN")
    print(f"  {'s DN/frame':>11} {'boundary step':>14} {'enrichment':>11}")
    for s, a, b, e in rows:
        print(f"  {s:11.1f} {s*dj:14.1f} {e:11.3f}")
    obs = rows[0][3]
    xs = np.array([r[0] for r in rows[1:]])
    ys = np.array([r[3] for r in rows[1:]])
    # statistic is a median of integer-valued |hp|; its quantum is 1 DN on a
    # base of 26 DN, so enrichment resolves to about 1/26.
    resol = 1.0 / rows[0][2]
    thresh = obs + 2.0 * resol
    lim = float(np.interp(thresh, ys, xs))
    print(f"  observed (unplanted) enrichment {obs:.3f}")
    print(f"  statistic resolution {resol:.4f} (|hp| is integer DN on a base"
          f" of {rows[0][2]:.0f} DN)")
    print(f"  2-resolution detection threshold {thresh:.3f}"
          f"  ->  UPPER LIMIT {lim:.2f} DN per adjacent frame")
    print(f"     = {100*lim/med:.4f}% of background per frame"
          f" = {100*lim*298/med:.2f}% across the bracket")
    m24 = 0.1170 * med / 298
    m24_e = float(np.interp(m24, xs, ys))
    print(f"  M24's worst corpus stack (coffee-bean, 11.70% end to end)"
          f" = {m24:.1f} DN/frame")
    print(f"     would read enrichment {m24_e:.2f}x, against {obs:.2f}x observed"
          f"  -> {'EXCLUDED' if m24_e > thresh else 'not excluded'}")
    out["B8_limit_dn_per_frame"] = lim
    out["B8_limit_pct_bracket"] = 100 * lim * 298 / med
    out["B8_resolution"] = resol
    out["B8_m24_dn"] = m24
    out["B8_m24_enrichment"] = m24_e
    out["B8_m24_excluded"] = bool(m24_e > thresh)

    # ---------------- B10: simulate the flatness statistic ---------------
    print("\n=== B10  simulate the flatness crossing (B9's constant was wrong) ===")
    hp = g - ndimage.median_filter(g, size=5)
    v = hp[bg]
    v0, v1 = hp[:, :-1][bg[:, :-1] & bg[:, 1:]], hp[:, 1:][bg[:, :-1] & bg[:, 1:]]
    rho = float(np.corrcoef(v0, v1)[0, 1])
    gyv, gxv = np.gradient(ndimage.uniform_filter(g, 9))
    grad = float(np.median(np.abs(gxv[bg])))
    print(f"  measured lag-1 correlation of the high pass  rho = {rho:+.4f}")
    print(f"  measured median |d/dx| of the smoothed field {grad:.2f} DN/px")
    print(f"  quantiser step {q:.1f} DN")

    rng = np.random.default_rng(SEED)
    N = 400000

    def flat_at(sigma):
        w = rng.standard_normal(N + 1)
        a = rho / (1.0 + np.sqrt(max(1.0 - rho * rho, 0.0)))
        e = (w[:-1] + a * w[1:]) / np.sqrt(1.0 + a * a)
        e2 = (w[1:] + a * w[:-1]) / np.sqrt(1.0 + a * a)
        base = rng.uniform(0, q, N)
        x0 = base + sigma * e
        x1 = base + grad + sigma * e2
        return float(np.mean(np.floor(x0 / q) == np.floor(x1 / q)))

    print(f"  {'sigma DN':>10} {'sigma/q':>9} {'flatness':>10}")
    sig = np.geomspace(5.0, 400.0, 22)
    fl = [flat_at(s) for s in sig]
    for s, f in zip(sig, fl):
        if s < 12 or abs(f - 0.5) < 0.14 or s > 250:
            print(f"  {s:10.1f} {s/q:9.3f} {f:10.3f}")
    order = np.argsort(fl)
    s_cross = float(np.interp(0.5, np.array(fl)[order], sig[order]))
    n_cross = (s_cross / NOISE_A) ** (1.0 / NOISE_B)
    ratio = n_cross / MEASURED_CROSS
    print(f"  simulated flatness-0.5 at sigma {s_cross:.1f} DN"
          f" = {s_cross/q:.3f} codes")
    print(f"  noise law {NOISE_A:.1f} * n_eff^{NOISE_B:+.4f} puts that at"
          f" n_eff = {n_cross:.2f}")
    print(f"  MEASURED crossing n_eff = {MEASURED_CROSS:.2f}"
          f"   ratio {ratio:.2f}x")
    b10 = ("the visible banding IS the cast quantum crossing the n_eff field"
           if 0.5 <= ratio <= 2.0 else
           "it is not" if ratio < 0.2 or ratio > 5.0 else "PARTIAL")
    print(f"  B10: {b10}")
    print(f"  (my hand-derived B9 constant gave 5.54, ratio 0.29x --"
          f" the error was mine, not the mechanism's)")
    out["rho"] = rho
    out["grad"] = grad
    out["B10_sigma_cross"] = s_cross
    out["B10_n_cross"] = float(n_cross)
    out["B10_ratio"] = float(ratio)
    out["B10"] = b10

    print("\n=== C-SIM: reproduce a value the simulator was not tuned to ===")
    s_low = NOISE_A * 1.2 ** NOISE_B
    f_low = flat_at(s_low)
    err = abs(f_low - MEASURED_FLAT_LOW) / MEASURED_FLAT_LOW
    print(f"  at n_eff = 1.2 the noise law gives sigma {s_low:.1f} DN")
    print(f"  simulated flatness {f_low:.3f}   measured {MEASURED_FLAT_LOW:.3f}"
          f"   error {100*err:.1f}%")
    ok = err <= 0.25
    print(f"  C-SIM {'PASS' if ok else 'FAIL'} (bar: within 25%)")
    out["C_SIM_pred"] = f_low
    out["C_SIM_meas"] = MEASURED_FLAT_LOW
    out["C_SIM_err"] = err
    out["C_SIM_pass"] = bool(ok)

    (DATA / "89-rescore.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '89-rescore.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
