"""V-CALIB s4 -- what the flats can and cannot calibrate, given the drift.

READ-ONLY on D:.

s3 established three things that constrain this step:

  a. THREE SHUTTER SETS ARE SATURATED. 1/5, 1/8 and 1/10 read exactly 15871 DN
     in the green quincunx on every frame with zero spread. 1/13's second half
     is saturated too. Saturated frames carry no noise information at all and
     are excluded here rather than argued about.

  b. THE DRIFT IS NOT SMALL. Implied illumination -- level divided by exposure
     time -- rises from about 6.6e4 to about 3.0e5 DN/s across the session.
     The owner warned that illumination "may have drifted"; the measurement
     says it drifted by roughly a factor of four and a half, monotonically.
     Step 1 below tests that this single common curve explains every set,
     because if it does not, the cause is not the sky and the flats are unsafe
     for anything.

  c. THE SETS ARE INTERLEAVED, staggered 30 s apart and each spanning ~320 s,
     so at any moment several shutter speeds are being exposed. That is what
     makes the common-curve test possible.

What survives a 4.5x illumination drift, and what does not:

  GAIN -- survives, IF measured from the DIFFERENCE of two consecutive frames
     at the same shutter. Consecutive frames are ~8 s apart, so the drift
     between them is small; differencing cancels the fixed pattern and leaves
     2x the temporal variance, while the mean of the pair gives the signal.
     This is the standard two-flat photon-transfer method and it is chosen here
     specifically BECAUSE it is drift-robust, not by habit.

  PRNU -- survives. Photo-response non-uniformity is a per-pixel multiplicative
     gain. Normalising each frame by its own mean removes any global
     illumination scalar exactly, whatever its value.

  A PHOTON-TRANSFER CURVE ACROSS SETS -- does NOT survive, and is not attempted.
     Regressing variance on mean across sets whose illumination moved by 4.5x
     for a reason unrelated to exposure would fit the sky, not the sensor.
"""
import json
import os
import sys

import numpy as np
import rawpy

LOGS = r"C:\dev\strehl-out\V-CALIB\logs"
CROP = 1024
BLACK = 512
SAT = 15871.0
SAT_GUARD = 0.90 * SAT     # stay clear of the knee, not just the clip

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "m57-shape-metric",
                                "src"))
import m57lib as M57                                            # noqa: E402


def load_green(path):
    """Return the two green planes as float64, black-subtracted.

    Green only: R and B sit under different filter transmissions, so a
    statistic built from all four planes moves with colour balance as well as
    with brightness. The two green planes are kept separate because they are
    on different rows and share no pixel.
    """
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        h, w = v.shape
        y0, x0 = (h - CROP) // 2, (w - CROP) // 2
        y0 -= y0 % 2
        x0 -= x0 % 2
        c = np.asarray(v[y0:y0 + CROP, x0:x0 + CROP], dtype=np.float64) - BLACK
    return c[0::2, 1::2], c[1::2, 0::2]


def main():
    rows = json.load(open(os.path.join(LOGS, "flatlevel.json"),
                          encoding="utf-8"))
    rows.sort(key=lambda r: r["t"])
    t0 = rows[0]["t"]

    # ---- 1. Does ONE illumination curve explain every set? ----------------
    print(f"{'=' * 96}")
    print("  1. IS THE DRIFT A SINGLE COMMON ILLUMINATION CURVE?")
    print(f"{'=' * 96}")
    print("  If the sky is the cause, level/exposure_time is a function of "
          "TIME ALONE and every")
    print("  shutter set must land on one curve. Binned by 30 s; a set is "
          "shown only where it is")
    print("  unsaturated (level < 90% of 15871).")
    ok = [r for r in rows if r["lvl"] < SAT_GUARD]
    print(f"\n  usable (unsaturated) frames: {len(ok)} of {len(rows)}")
    bins = {}
    for r in ok:
        b = int((r["t"] - t0) // 30)
        bins.setdefault(b, []).append(r)
    print(f"\n  {'t (s)':>7}{'n':>4}{'shutters':>10}"
          f"{'illum DN/s: median':>21}{'spread max/min':>16}")
    spreads = []
    for b in sorted(bins):
        g = bins[b]
        ill = np.array([r["lvl"] / r["ExposureTime"] for r in g])
        ns = len({r["ExposureTime"] for r in g})
        if ns < 2:
            continue
        sp = float(ill.max() / max(ill.min(), 1e-9))
        spreads.append(sp)
        print(f"  {b * 30:>7}{len(g):>4}{ns:>10}{np.median(ill):>21.0f}"
              f"{sp:>16.3f}")
    print(f"\n  median cross-shutter spread within a 30 s bin: "
          f"{np.median(spreads):.3f}x")
    print(f"  illumination range over session: "
          f"{min(r['lvl'] / r['ExposureTime'] for r in ok):.0f} -> "
          f"{max(r['lvl'] / r['ExposureTime'] for r in ok):.0f} DN/s "
          f"= {max(r['lvl'] / r['ExposureTime'] for r in ok) / min(r['lvl'] / r['ExposureTime'] for r in ok):.2f}x")
    verdict = ("SUPPORTED -- one sky curve explains the sets"
               if np.median(spreads) < 1.25 else
               "NOT SUPPORTED -- sets disagree at matched times")
    print(f"  COMMON-CURVE HYPOTHESIS: {verdict}")

    # ---- 2. Gain, from consecutive-frame differences ----------------------
    print(f"\n{'=' * 96}")
    print("  2. GAIN, from consecutive-frame differences (drift-robust)")
    print(f"{'=' * 96}")
    by = {}
    for r in ok:
        by.setdefault(r["ExposureTime"], []).append(r)
    print(f"  {'shutter':>9}{'pairs':>7}{'signal DN':>12}"
          f"{'var/2 DN^2':>13}{'g DN/e-':>10}")
    pts = []
    for et in sorted(by, reverse=True):
        g = sorted(by[et], key=lambda r: r["t"])
        npair = 0
        for i in range(0, len(g) - 1, 2):
            a1, a2 = load_green(g[i]["SourceFile"])
            b1, b2 = load_green(g[i + 1]["SourceFile"])
            for A, B in ((a1, b1), (a2, b2)):
                m = 0.5 * (A.mean() + B.mean())
                if m <= 0 or m > SAT_GUARD:
                    continue
                # Difference cancels the fixed pattern; its variance is 2x
                # the per-frame temporal variance.
                v = 0.5 * np.var(A - B, ddof=1)
                pts.append((m, v, et))
                npair += 1
            if npair >= 8:
                break
        sel = [p for p in pts if p[2] == et]
        if sel:
            mm = float(np.mean([p[0] for p in sel]))
            vv = float(np.mean([p[1] for p in sel]))
            ets = f"1/{1 / et:.0f}" if et < 1 else f"{et}"
            print(f"  {ets:>9}{len(sel):>7}{mm:>12.1f}{vv:>13.1f}"
                  f"{vv / max(mm, 1e-9):>10.4f}")

    # Photon transfer within the drift-robust points: var = g*S + (RN*g)^2.
    S = np.array([p[0] for p in pts])
    V = np.array([p[1] for p in pts])
    A = np.vstack([S, np.ones_like(S)]).T
    coef, *_ = np.linalg.lstsq(A, V, rcond=None)
    g_fit, b_fit = float(coef[0]), float(coef[1])
    g_model = M57.gain_dn_per_e(100)
    rn_fit = np.sqrt(max(b_fit, 0.0)) / g_fit if g_fit > 0 else float("nan")
    print(f"\n  photon-transfer fit over {len(S)} drift-robust points:")
    print(f"    g   = {g_fit:.4f} DN/e-   (m57lib model at ISO 100: "
          f"{g_model:.4f};  measured/model = {g_fit / g_model:.3f})")
    print(f"    b   = {b_fit:.2f} DN^2  ->  RN = {rn_fit:.3f} e-  "
          f"(m57lib: {M57.read_noise_e(100):.3f} e-)")

    # ---- 3. PRNU ---------------------------------------------------------
    print(f"\n{'=' * 96}")
    print("  3. PRNU, from per-frame-normalised flats (drift-invariant)")
    print(f"{'=' * 96}")
    et_best = max((et for et in by if len(by[et]) >= 12),
                  key=lambda e: np.mean([r["lvl"] for r in by[e]]))
    g = sorted(by[et_best], key=lambda r: r["t"])[:20]
    ets = f"1/{1 / et_best:.0f}" if et_best < 1 else f"{et_best}"
    print(f"  using shutter {ets}, n = {len(g)} frames, "
          f"mean level {np.mean([r['lvl'] for r in g]):.0f} DN")
    cube = []
    for r in g:
        p1, _ = load_green(r["SourceFile"])
        cube.append(p1 / p1.mean())          # kills the illumination scalar
    cube = np.stack(cube, 0)
    mu = cube.mean(0)
    n = cube.shape[0]
    lvl = float(np.mean([r["lvl"] for r in g]))
    # Residual temporal noise still in the mean, in normalised units.
    shot_dn = np.sqrt(g_fit * lvl + b_fit)
    floor = (shot_dn / lvl) / np.sqrt(n)
    # Low-order illumination shape is the LENS, not the sensor: remove a
    # smooth surface so PRNU is pixel-to-pixel response, not vignetting.
    from scipy import ndimage
    smooth = ndimage.uniform_filter(mu, 65)
    flat = mu / smooth
    raw_sd = float(np.std(flat))
    prnu = float(np.sqrt(max(raw_sd ** 2 - floor ** 2, 0.0)))
    print(f"  spatial sd of the {n}-frame mean, vignetting removed: "
          f"{100 * raw_sd:.4f}%")
    print(f"  averaging floor (temporal noise / sqrt n):            "
          f"{100 * floor:.4f}%")
    print(f"  PRNU (quadrature-corrected):                          "
          f"{100 * prnu:.4f}%  of signal")
    print(f"  vignetting removed (smooth surface, 65 px): "
          f"{100 * (mu.max() - mu.min()):.2f}% peak-to-peak before removal")

    dst = os.path.join(LOGS, "flatcal.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(dict(g_fit=g_fit, b_fit=b_fit, rn_fit=rn_fit,
                       g_model=g_model, prnu=prnu, prnu_floor=floor,
                       n_pts=len(S), shutter_prnu=et_best, level=lvl), f,
                  indent=1)
    print(f"\nwrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
