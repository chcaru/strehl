"""BUILD-RESAMP -- the applicability limit of the slanted-edge pipeline.

BUILD-SHARP has now lost two instruments to the same variable.  Their shape
test needed no amplitude reference and had an exact null at every blur level,
and it still went blind at a 10-90% edge width of 4.33 px while both renders
sit at 13.5 and 17.9 px -- more than 3x past the threshold.  The confound was
never in the statistic, it was in the variable: any instrument whose usable
range is bounded by edge sharpness fails on a comparison OF edge sharpness.

So this file does not argue that a slanted-edge MTF is immune.  It sweeps a
synthetic edge across 1.9 px to 18 px of 10-90% width and asks whether the
recovered MTF50 tracks the known blur over the WHOLE range, with no region
where sensitivity collapses.  Whatever width it stops tracking at is a stated
applicability limit, and our renders must sit inside it or the reading is void.

The synthetic ESF is a pure Gaussian CDF with NO pixel aperture, so both
answers are exact and there is nothing fitted:

    MTF(f)          = exp(-2 pi^2 sigma^2 f^2)
    MTF50           = sqrt(ln2 / 2) / (pi sigma) = 0.187241 / sigma
    10-90% width    = 2 x 1.281552 x sigma       = 2.563103 x sigma

Adding a pixel aperture would multiply in a sinc that I would then have to
divide back out -- a second thing to get wrong, in the file whose job is to be
trustworthy.  It is stated rather than modelled.

Two sweeps.  The clean one answers the question as put.  The noisy one is
there because the per-render commissioning already showed this pipeline's
ESTIMATOR VARIANCE, not its estimand, is what carries the confound: the fork's
ESF fit residual is 2.54x ours and its recovery is correspondingly lower.  An
applicability limit measured only on noiseless data would be the optimistic
half of the answer.

All figures print to 6 significant figures.  A ':.1f' in BUILD-SHARP's
commissioning printed 'amplitude floor 0.0 DN' for 0.00815 and nearly retired a
working instrument.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slanted_edge as se  # noqa: E402

ERF = np.vectorize(math.erf)
SLOPE = math.tan(math.radians(5.0))       # inside [MIN_ANGLE_DEG, MAX_ANGLE_DEG]
CONTRAST = 20000.0                        # DN, linear
PEDESTAL = 5000.0                         # DN, linear


def synth(sigma, h=se.LENGTH, w=se.WIDTH, noise=0.0, seed=7):
    """A slanted step blurred by an exact Gaussian, in linear DN."""
    y = np.arange(h, dtype=np.float64)[:, None]
    x = np.arange(w, dtype=np.float64)[None, :]
    icept = w / 2.0 - SLOPE * (h - 1) / 2.0
    d = (x - (SLOPE * y + icept)) / math.sqrt(1.0 + SLOPE * SLOPE)
    cdf = 0.5 * (1.0 + ERF(d / (sigma * math.sqrt(2.0))))
    img = PEDESTAL + CONTRAST * cdf
    if noise > 0.0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return img


def width_1090(e):
    """10-90% width in px, measured from the recovered ESF itself."""
    n = se.OVERSAMPLE * 4
    lo, hi = np.median(e[:n]), np.median(e[-n:])
    if hi == lo:
        return np.nan
    t = (e - lo) / (hi - lo)
    if t[0] > t[-1]:
        t = 1.0 - t
    xs = np.arange(len(t)) / se.OVERSAMPLE
    try:
        a = np.interp(0.1, t, xs)
        b = np.interp(0.9, t, xs)
    except Exception:
        return np.nan
    return float(b - a)


def sweep(noise, label):
    print(f"\n=== {label} ===")
    print(f"  {'sigma':>7}{'true w10-90':>13}{'meas w10-90':>13}"
          f"{'true MTF50':>13}{'meas MTF50':>13}{'meas/true':>11}"
          f"{'ESF resid':>11}")
    rows = []
    for sigma in (0.74, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.02):
        img = synth(sigma, noise=noise)
        r = se.measure_roi(img)
        tw = 2.563103 * sigma
        tm = 0.187241 / sigma
        if r is None:
            print(f"  {sigma:>7.4g}{tw:>13.6g}{'REJECTED':>13}"
                  f"{tm:>13.6g}{'--':>13}{'--':>11}{'--':>11}")
            rows.append((sigma, tw, np.nan))
            continue
        mw = width_1090(r["esf"])
        mm = r["mtf50"]
        print(f"  {sigma:>7.4g}{tw:>13.6g}{mw:>13.6g}"
              f"{tm:>13.6g}{mm:>13.6g}{mm/tm:>11.6g}{r['esf_resid']:>11.6g}")
        rows.append((sigma, tw, mm / tm))
    ok = [(w, r) for _, w, r in rows if np.isfinite(r) and abs(r - 1.0) <= 0.05]
    bad = [(w, r) for _, w, r in rows if not (np.isfinite(r) and abs(r - 1.0) <= 0.05)]
    if ok:
        print(f"\n  tracks to within 5%: w10-90 "
              f"{min(w for w, _ in ok):.6g} .. {max(w for w, _ in ok):.6g} px")
    if bad:
        print("  OUTSIDE 5%: " + ", ".join(
            f"w={w:.4g}px ({r:.4g}x)" if np.isfinite(r) else f"w={w:.4g}px (rejected)"
            for w, r in bad))
    else:
        print("  no region of collapse over the swept range")
    return rows


def main():
    print("applicability sweep of slanted_edge.py")
    print(f"  geometry ROI {se.LENGTH} along x {se.WIDTH} across, "
          f"ESF support +/-{se.HALF} px, {se.OVERSAMPLE}x bins, slant 5.0 deg")
    print(f"  contrast {CONTRAST:.6g} DN on a {PEDESTAL:.6g} DN pedestal, linear")

    # NULL: the same synthetic measured twice must be bit-identical.  A plant
    # is large by construction and survives a broken instrument; the null is
    # what catches a defect big enough to swallow the plant.
    a = se.measure_roi(synth(2.0))
    b = se.measure_roi(synth(2.0))
    d = float(np.max(np.abs(a["m"] - b["m"])))
    print(f"\n  NULL   same synthetic twice, max |dMTF| = {d:.6e}   "
          f"{'PASS' if d == 0.0 else 'FAIL'}")

    clean = sweep(0.0, "CLEAN -- no noise, the question as put")
    sweep(200.0, "NOISY -- sigma 200 DN, 1.0% of contrast")
    sweep(600.0, "NOISY -- sigma 600 DN, 3.0% of contrast")

    # ---- place our two renders against the limit ---------------------------
    # BUILD-SHARP measured these 10-90% widths on the same two renders.
    ws = np.array([w for _, w, r in clean if np.isfinite(r)])
    rs = np.array([r for _, w, r in clean if np.isfinite(r)])
    print("\n=== WHAT THIS COSTS THE HEAD-TO-HEAD ===")
    print(f"  {'render':<26}{'w10-90 px':>11}{'inflation':>11}")
    infl = {}
    for name, w in (("wrapped-text-1 strehl", 13.52),
                    ("wrapped-text-1 fork", 17.86)):
        v = float(np.interp(w, ws, rs))
        infl[name] = v
        print(f"  {name:<26}{w:>11.6g}{v:>11.6g}")
    a = infl["wrapped-text-1 fork"] / infl["wrapped-text-1 strehl"]
    print(f"\n  ratio of inflations, fork / strehl = {a:.6g}")
    print("  The two renders do not share an inflation factor because they do")
    print("  not share an edge width, so a cross-render MTF50 comparison")
    print(f"  carries a {100*(a-1):.4g}% systematic bias from edge width alone,")
    print("  in the direction that makes the FORK read sharper.")


if __name__ == "__main__":
    main()
