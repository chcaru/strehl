"""Test ORCH's replacement triage rule (value vs position) against M111's data.

ORCH's corrected rule: LOCATION statistics (displacements, centroids, peak
positions) are largely immune to a narrowed reader; DISPERSION statistics
(noise power, sd, SNR, band/gradient energy, flatness, kurtosis) absorb the
quantisation variance directly and are destroyed. M113 measured a location
estimator at -0.4%/+0.1% under a 118x narrowing, and rms degrading 2.8x.

M111 has a problem with this as stated. BOTH of M111's statistics are built
from gradient energy, so both are DISPERSION and both are predicted destroyed.
Measured (section 19), the cross-arm boundary-hardness contrast moved -8.7% --
real, but nothing like 2.8x -- and the cross-arm interior-flatness contrast
moved -0.0%/+3.0%, i.e. nearly immune. A rule that classifies my most protected
statistic as destroyed is mispredicting, in the direction that costs re-runs.

The suspicion, from section 20: the rule classifies the RAW QUANTITY, but a
statistic is usually a COMPOSITION of raw quantities, and composition cancels.
Position-vs-value should predict the terms; disparity should predict how much
survives forming a ratio of them. If so the two findings compose rather than
conflict, and the rule needs a composition clause rather than a replacement.

PRE-REGISTERED, before these numbers exist. Median over tiles, tifffile against
PIL, every other line identical:

  L  LOCATION (sub-pixel phase-correlation offset, merged against control)
     ORCH predicts immune. Registered: |median dx,dy bias| < 0.05 px. If it
     exceeds 0.2 px, ORCH's location claim fails on M111's data and M113's
     result does not transfer.

  A  DISPERSION, ABSOLUTE (mean gradient energy, merged arm, rescaled)
     ORCH predicts destroyed. Registered: |median shift| > 20%.

  W  DISPERSION, WITHIN-ARM RATIO (inside/outside by bright-quartile mask)
     Registered: intermediate, between A and X, and governed by disparity
     per section 20.

  X  DISPERSION, CROSS-ARM CONTRAST (merged W over control W)
     ORCH's rule predicts destroyed, same as A. M111 predicts PROTECTED:
     registered |median shift| < 5%, and strictly less than A.

  VERDICT CONDITIONS
    If L passes and A passes and X < 5% < A, then ORCH's rule is right about
    raw quantities and wrong about compositions of them, and needs a
    composition clause -- it must classify the STATISTIC, not its terms.
    If X >= 20%, M111's section 19 number was a one-ROI artefact and ORCH's
    rule stands unmodified.
    If L fails, the location half does not transfer and that is the headline.

Also reports DISTINCT LEVELS PER INTEGRATION WINDOW under PIL, which is the
quantity ORCH says decides -- not levels in the file, not in the ROI.

Writes: C:\\dev\\strehl-out\\M111-pil-audit\\value_vs_position.json
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\M111-pil-audit"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(ORCHDIR, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(ORCHDIR, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")
TILE = 256
STRIDE = int(os.environ.get("M111_STRIDE", "256"))
SCALE = 65535.0 / 255.0


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float32)
            + 0.7152 * a[..., 1].astype(np.float32)
            + 0.0722 * a[..., 2].astype(np.float32))


def gradmag(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def subpixel_offset(a, b):
    """Sub-pixel (dy, dx) aligning b onto a, phase correlation + parabolic peak."""
    a = a - a.mean()
    b = b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa = np.fft.rfft2(a * win)
    fb = np.fft.rfft2(b * win)
    cross = fa * np.conj(fb)
    mag = np.abs(cross)
    mag[mag == 0] = 1e-12
    r = np.fft.irfft2(cross / mag, s=a.shape)
    pk = np.unravel_index(np.argmax(r), r.shape)

    def refine(axis):
        i = pk[axis]
        n = r.shape[axis]
        im, ip = (i - 1) % n, (i + 1) % n
        idx_m = (im, pk[1]) if axis == 0 else (pk[0], im)
        idx_p = (ip, pk[1]) if axis == 0 else (pk[0], ip)
        y0, y1, y2 = r[idx_m], r[pk], r[idx_p]
        den = y0 - 2 * y1 + y2
        d = 0.0 if abs(den) < 1e-12 else 0.5 * (y0 - y2) / den
        v = i + float(np.clip(d, -1, 1))
        return v if v <= n / 2 else v - n

    return refine(0), refine(1), float(r[pk])


def main():
    os.makedirs(OUT, exist_ok=True)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    mp, cp = np.asarray(Image.open(MERGED)), np.asarray(Image.open(CTRL))
    assert mt.dtype == np.uint16 and ct.dtype == np.uint16
    assert mp.dtype == np.uint8 and cp.dtype == np.uint8
    h, w = min(mt.shape[0], ct.shape[0]), min(mt.shape[1], ct.shape[1])
    print("common crop %dx%d  tile %d  stride %d" % (h, w, TILE, STRIDE))

    L, A, W, X, LV, DISP = [], [], [], [], [], []
    for y0 in range(200, h - TILE - 200, STRIDE):
        for x0 in range(200, w - TILE - 200, STRIDE):
            sy, sx = slice(y0, y0 + TILE), slice(x0, x0 + TILE)
            ymt, yct = luma(mt[sy, sx]), luma(ct[sy, sx])
            ymp, ycp = luma(mp[sy, sx]), luma(cp[sy, sx])
            if ymt.std() < 1.0 or yct.std() < 1.0:
                continue
            LV.append(int(np.unique(mp[sy, sx]).size))

            dyt, dxt, pt = subpixel_offset(ymt, yct)
            dyp, dxp, pp = subpixel_offset(ymp, ycp)
            if min(pt, pp) < 0.02:
                dyt = dxt = dyp = dxp = np.nan
            L.append((dyt, dxt, dyp, dxp))

            gmt, gmp = gradmag(ymt), gradmag(ymp)
            gct, gcp = gradmag(yct), gradmag(ycp)
            at, ap = float(gmt.mean()), float(gmp.mean()) * SCALE
            A.append(100.0 * (ap - at) / max(at, 1e-9))

            def wr(y, g):
                m = y >= np.percentile(y, 75)
                i, o = float(g[m].mean()), float(g[~m].mean())
                return i / max(o, 1e-9), max(i, o) / max(min(i, o), 1e-9)

            wmt, dmt = wr(ymt, gmt)
            wmp, _ = wr(ymp, gmp)
            wct, _ = wr(yct, gct)
            wcp, _ = wr(ycp, gcp)
            W.append(100.0 * (wmp - wmt) / max(abs(wmt), 1e-9))
            DISP.append(dmt)
            xt, xp = wmt / max(wct, 1e-9), wmp / max(wcp, 1e-9)
            X.append(100.0 * (xp - xt) / max(abs(xt), 1e-9))

    n = len(A)
    Larr = np.array(L, float)
    ok = np.isfinite(Larr).all(axis=1)
    dbias_y = float(np.median(Larr[ok, 2] - Larr[ok, 0]))
    dbias_x = float(np.median(Larr[ok, 3] - Larr[ok, 1]))
    a_med = float(np.median(np.abs(A)))
    w_med = float(np.median(np.abs(W)))
    x_med = float(np.median(np.abs(X)))
    lv_med = float(np.median(LV))

    print("\ntiles %d   usable location tiles %d" % (n, int(ok.sum())))
    print("distinct PIL levels per %dpx window: median %.0f  min %d  max %d"
          % (TILE, lv_med, min(LV), max(LV)))
    print("\n%-46s %12s" % ("statistic", "median shift"))
    print("-" * 60)
    print("%-46s %9.4f px" % ("L  location: sub-pixel offset bias (dy)", dbias_y))
    print("%-46s %9.4f px" % ("L  location: sub-pixel offset bias (dx)", dbias_x))
    print("%-46s %11.2f%%" % ("A  dispersion, absolute (mean grad energy)", a_med))
    print("%-46s %11.2f%%" % ("W  dispersion, within-arm ratio", w_med))
    print("%-46s %11.2f%%" % ("X  dispersion, cross-arm contrast", x_med))

    l_ok = max(abs(dbias_y), abs(dbias_x)) < 0.05
    l_fail = max(abs(dbias_y), abs(dbias_x)) > 0.2
    a_ok = a_med > 20.0
    x_ok = x_med < 5.0
    print("\n[pre-registered gates]")
    print("  L  location bias < 0.05 px            : %s" % ("PASS" if l_ok else
          ("FAIL-HARD" if l_fail else "MARGINAL")))
    print("  A  absolute dispersion shift > 20%%     : %s" % ("PASS" if a_ok else "FAIL"))
    print("  X  cross-arm contrast shift < 5%%       : %s" % ("PASS" if x_ok else "FAIL"))
    print("  X < A (composition protects)          : %s" % ("PASS" if x_med < a_med else "FAIL"))

    if l_fail:
        verdict = "ORCH LOCATION CLAIM FAILS ON M111 DATA"
    elif l_ok and a_ok and x_ok and x_med < a_med:
        verdict = ("ORCH RULE RIGHT ABOUT RAW QUANTITIES, WRONG ABOUT COMPOSITIONS "
                   "-- needs a composition clause")
    elif x_med >= 20.0:
        verdict = "M111 SECTION 19 WAS A ONE-ROI ARTEFACT; ORCH RULE STANDS"
    else:
        verdict = "MIXED -- see gates"
    print("\nVERDICT: %s" % verdict)

    doc = {"n_tiles": n, "tile": TILE, "stride": STRIDE,
           "pil_levels_per_window": {"median": lv_med, "min": min(LV), "max": max(LV)},
           "L_offset_bias_px": {"dy": dbias_y, "dx": dbias_x},
           "A_absolute_median_abs_shift_pct": a_med,
           "W_within_arm_median_abs_shift_pct": w_med,
           "X_cross_arm_median_abs_shift_pct": x_med,
           "median_within_arm_disparity": float(np.median(DISP)),
           "gates": {"L_under_0p05px": bool(l_ok), "L_hard_fail": bool(l_fail),
                     "A_over_20pct": bool(a_ok), "X_under_5pct": bool(x_ok),
                     "X_less_than_A": bool(x_med < a_med)},
           "verdict": verdict}
    dst = os.path.join(OUT, "value_vs_position.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
