"""M35 step 2: does M33's log-fit advantage survive a change of aperture?

Runs the SAME code over three stacks so that any difference between them is
optics and not implementation.  coffee-bean is recomputed here rather than quoted
from M33 -- that makes this an internal replication of M33 as a by-product, and
it removes "they used different code" as an explanation for any disagreement.

    119MSDCF     33 frames   f/5.6   ISO  50
    coffee-bean 105 frames   f/8     ISO  50     (M33's stack, recomputed)
    112MSDCF     79 frames   f/11    ISO 500

Two gates before any calibration number is allowed to mean anything:

  ADEQUACY.  The dense grid is itself sampled, so it has its own deficit, and it
  is honest ground truth for spacing h only if that deficit is much smaller than
  the one being measured.  Deficit grows roughly as h^2 near a smooth peak, so
  fit log(deficit) against log(h) over h in {2,3,4} and extrapolate to h=1.
  Headroom = deficit(2)/deficit(1).  M33 measured 3.87x on coffee-bean and said a
  x4 grid would NOT have been adequate.  A stack that fails this gate is reported
  as inadequate, not analysed anyway.

  BOUNDARY.  A pixel whose peak lands at the edge of the decimated stack has no
  interpolable peak at all.  119MSDCF has 7.38% of pixels there against 112's
  2.08%, so this is not a negligible exclusion and it is applied to every stack
  identically.

PRE-REGISTERED before running:
  P1  Every stack passes adequacy at h=2 with headroom > 3.
  P2  The parabola's calibration ratio is < 0.6 on every stack -- fact 271's
      anti-correlation is a property of the estimator, not of coffee-bean.
  P3  The log fit beats the parabola on every stack (higher calibration ratio).
  P4  The log fit's advantage SHRINKS as the aperture closes, because a
      diffraction-dominated response is less Gaussian than a defocus-dominated
      one.  Ordering predicted: 119 (f/5.6) > coffee-bean (f/8) > 112 (f/11).
  P5  The implied Gaussian width grows as the aperture closes (fact 274's
      mechanism, read across stacks instead of across spacings).
"""
import numpy as np, os, json

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
M33 = os.path.join(HERE, "..", "..", "m33-subframe-offset", "out", "cache", "dense_focus.npy")

SPACINGS = [2, 3, 4]
FLOOR = 0.01          # pixels with true deficit below this are excluded from the
                      # within-2x statistic; the ratio est/true is meaningless there
                      # and M33's point mass (discipline 180) lives right at 0.

SRC = {
    "119MSDCF":    (os.path.join(CACHE, "119MSDCF_focus.npy"), 5.6, 50),
    "coffee-bean": (M33, 8.0, 50),
    "112MSDCF":    (os.path.join(CACHE, "112MSDCF_focus.npy"), 11.0, 500),
}


def fits(y0, ym, yp):
    """Parabolic and log-domain three-point peak estimates from base-subtracted
    samples at x = -1, 0, +1.  Returns (deficit_parabola, deficit_log, valid)."""
    b = (yp - ym) / 2.0
    c = (yp - 2 * y0 + ym) / 2.0
    ok = (c < -1e-12) & (y0 > 0) & (ym > 0) & (yp > 0)
    cc = np.where(ok, c, -1.0)
    peak_par = y0 - b ** 2 / (4 * cc)
    d_par = np.where(ok, 1.0 - y0 / np.maximum(peak_par, 1e-12), 0.0)

    L0, Lm, Lp = np.log(np.maximum(y0, 1e-12)), np.log(np.maximum(ym, 1e-12)), np.log(np.maximum(yp, 1e-12))
    den = Lm - 2 * L0 + Lp
    okl = ok & (den < -1e-12)
    xs = np.where(okl, 0.5 * (Lm - Lp) / np.where(okl, den, -1.0), 0.0)
    xs = np.clip(xs, -1, 1)
    peak_log = L0 + 0.25 * (Lp - Lm) * xs
    d_log = np.where(okl, 1.0 - np.exp(np.minimum(L0 - peak_log, 0.0)), 0.0)
    return np.clip(d_par, 0, 1), np.clip(d_log, 0, 1), okl


res = {}
for name, (path, fmark, iso) in SRC.items():
    dense = np.asarray(np.load(path, mmap_mode="r"), np.float32)
    nd, Hh, Ww = dense.shape
    base = dense.min(0)
    tp = np.maximum(dense.max(0) - base, 1e-6)
    yy, xx = np.mgrid[0:Hh, 0:Ww]
    print(f"\n=== {name}  n={nd}  f/{fmark}  ISO{iso} ===")

    arms = {}
    for h in SPACINGS:
        sub = dense[::h]
        ns = sub.shape[0]
        cp = np.maximum(sub.max(0) - base, 1e-6)
        true_def = np.clip(1.0 - cp / tp, 0, 1)
        k = sub.argmax(0)
        inner = (k >= 1) & (k <= ns - 2)
        km = np.clip(k, 1, ns - 2)
        y0 = sub[km, yy, xx] - base
        ym = sub[km - 1, yy, xx] - base
        yp = sub[km + 1, yy, xx] - base
        d_par, d_log, okl = fits(y0, ym, yp)
        m = inner & okl
        arms[h] = dict(
            n_sub=int(ns), valid=float(m.mean()),
            true_mean=float(true_def[m].mean()),
            true_all_mean=float(true_def.mean()),
            par_mean=float(d_par[m].mean()), log_mean=float(d_log[m].mean()),
        )
        big = m & (true_def > FLOOR)
        for tag, est in (("par", d_par), ("log", d_log)):
            r = est[big] / true_def[big]
            arms[h][f"{tag}_ratio"] = float(est[m].mean() / max(true_def[m].mean(), 1e-12))
            arms[h][f"{tag}_within2x"] = float(((r >= 0.5) & (r <= 2.0)).mean())
        arms[h]["n_scored"] = int(big.sum())
        print(f"  h={h} ({ns:3d} fr) valid {m.mean():.3%}  true {arms[h]['true_mean']:.5f}"
              f"   par {arms[h]['par_ratio']:.3f} ({arms[h]['par_within2x']:.1%})"
              f"   log {arms[h]['log_ratio']:.3f} ({arms[h]['log_within2x']:.1%})")

    # --- adequacy: extrapolate the deficit ladder back to h = 1 --------------
    hs = np.array(SPACINGS, float)
    dv = np.array([arms[h]["true_mean"] for h in SPACINGS])
    slope, inter = np.polyfit(np.log(hs), np.log(dv), 1)
    d1 = float(np.exp(inter))
    headroom = arms[2]["true_mean"] / d1
    # implied Gaussian width: for a Gaussian, mean deficit over uniform phase is
    # ~ h^2 / (24 sigma^2) to leading order, so sigma = h / sqrt(24 * deficit)
    sig_imp = {h: float(h / np.sqrt(24 * arms[h]["true_mean"])) for h in SPACINGS}
    print(f"  ladder slope {slope:.3f} (2.0 = exactly quadratic)   deficit(h=1) {d1:.5f}"
          f"   ADEQUACY HEADROOM {headroom:.2f}x  ->  {'PASS' if headroom > 3 else 'FAIL'}")
    print(f"  implied Gaussian sigma (dense frames): "
          + "  ".join(f"h={h}:{sig_imp[h]:.2f}" for h in SPACINGS))

    res[name] = dict(n_frames=int(nd), f_marked=fmark, iso=iso, arms=arms,
                     ladder_slope=float(slope), deficit_h1=d1,
                     adequacy_headroom=float(headroom), adequate=bool(headroom > 3),
                     implied_sigma=sig_imp)
    del dense

print("\n=== cross-stack summary (h=2, the operational spacing) ===")
print(f"{'stack':13s} {'f':>5s} {'true':>8s} {'par':>7s} {'log':>7s} {'log/par':>8s} {'adeq':>7s}")
for name in ["119MSDCF", "coffee-bean", "112MSDCF"]:
    a = res[name]["arms"][2]
    print(f"{name:13s} {res[name]['f_marked']:5.1f} {a['true_mean']:8.5f}"
          f" {a['par_ratio']:7.3f} {a['log_ratio']:7.3f}"
          f" {a['log_ratio']/max(a['par_ratio'],1e-9):8.2f} {res[name]['adequacy_headroom']:6.2f}x")

json.dump(dict(spacings=SPACINGS, floor=FLOOR, stacks=res),
          open(os.path.join(OUT, "02-generality.json"), "w"), indent=1)
print("wrote 02-generality.json")
