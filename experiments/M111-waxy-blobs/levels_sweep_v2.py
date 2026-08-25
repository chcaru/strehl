"""Corrected location instrument for the levels sweep, plus a recheck of my own
earlier location claim.

TWO DEFECTS FOUND IN MY OWN WORK, both of which ORCH's latest notice predicts:

D1. levels_sweep.py reported a location bias of 27.47 px at N = 256, where the
    narrowing is nearly a no-op. That is an instrument failure, not a result.
    Cause: the peak-quality floor `pk > 0.02` admitted essentially every tile,
    including featureless ones with no registration peak at all, whose "offset"
    is independent noise in each arm. This is exactly ORCH's warning that a
    control whose sampling saturates has tested nothing -- and I did not print
    the sample count, so I could not see it saturating.

D2. value_vs_position.py reported L as the median SIGNED difference and I cited
    -0.0687 px as support for ORCH's immunity claim. A median signed difference
    cancels symmetric per-tile scatter, so it cannot distinguish "every tile is
    accurate" from "tiles are wildly wrong in both directions". The honest
    statistic is the median ABSOLUTE per-tile deviation. My earlier number was
    weaker evidence than I presented it as.

Fixes: an unambiguity floor (peak against the best rival peak outside a
exclusion radius), the sample count printed AT EVERY LEVEL and required to
vary, and median absolute deviation throughout.

PRE-REGISTERED, before these numbers exist:

  Q1 the support floor does NOT saturate: admitted tile count must vary across
     the sweep. If it is constant, the floor is inert and this instrument has
     tested nothing either -- same defect, one level up.
  Q2 with the floor applied, location bias at N = 256 falls below 0.1 px,
     confirming D1 was a support defect and not a real degradation.
  Q3 ordering: dispersion (A) crosses 20% at N_A; location crosses 0.2 px at
     N_L. ORCH's rule requires N_A > N_L. On the broken run A crossed at N = 4,
     which is BELOW ORCH's stated 12-level location bound, so if the corrected
     location number also breaks near 12 the ordering is REVERSED on this data
     and dispersion is the more robust family.
  Q4 D2 is real: median |deviation| at N = 256 exceeds the median signed bias
     by more than 3x, confirming cancellation was masking scatter.

Writes: C:\\dev\\strehl-out\\M111-pil-audit\\levels_sweep_v2.json
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M111-pil-audit"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(ORCHDIR, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(ORCHDIR, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")
TILE = 256
STRIDE = 512
LEVELS = [256, 128, 64, 48, 32, 24, 16, 12, 8, 6, 4, 3, 2]
UNAMBIGUITY = 2.0


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float32)
            + 0.7152 * a[..., 1].astype(np.float32)
            + 0.0722 * a[..., 2].astype(np.float32))


def gradmag(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def narrow(y, n):
    lo, hi = float(y.min()), float(y.max())
    if hi - lo < 1e-9:
        return y.copy()
    return np.round((y - lo) / (hi - lo) * (n - 1)) / (n - 1) * (hi - lo) + lo


def offset(a, b):
    """Sub-pixel (dy, dx, unambiguity). Unambiguity = peak / best rival peak."""
    a, b = a - a.mean(), b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    cross = np.fft.rfft2(a * win) * np.conj(np.fft.rfft2(b * win))
    mag = np.abs(cross)
    mag[mag == 0] = 1e-12
    r = np.fft.irfft2(cross / mag, s=a.shape)
    pk = np.unravel_index(np.argmax(r), r.shape)
    peak = float(r[pk])
    rival = r.copy()
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            rival[(pk[0] + dy) % r.shape[0], (pk[1] + dx) % r.shape[1]] = -np.inf
    best_rival = float(rival.max())
    amb = peak / max(best_rival, 1e-12)

    def refine(axis):
        i, n = pk[axis], r.shape[axis]
        am = r[((i - 1) % n, pk[1])] if axis == 0 else r[(pk[0], (i - 1) % n)]
        ap = r[((i + 1) % n, pk[1])] if axis == 0 else r[(pk[0], (i + 1) % n)]
        den = am - 2 * peak + ap
        d = 0.0 if abs(den) < 1e-12 else 0.5 * (am - ap) / den
        v = i + float(np.clip(d, -1, 1))
        return v if v <= n / 2 else v - n

    return refine(0), refine(1), amb


def main():
    os.makedirs(OUT, exist_ok=True)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    h, w = min(mt.shape[0], ct.shape[0]), min(mt.shape[1], ct.shape[1])
    tiles = []
    for y0 in range(200, h - TILE - 200, STRIDE):
        for x0 in range(200, w - TILE - 200, STRIDE):
            ym = luma(mt[y0:y0 + TILE, x0:x0 + TILE])
            yc = luma(ct[y0:y0 + TILE, x0:x0 + TILE])
            if ym.std() < 1.0 or yc.std() < 1.0:
                continue
            tiles.append((ym, yc))
    print("tiles %d   unambiguity floor %.1f" % (len(tiles), UNAMBIGUITY))

    base = []
    for ym, yc in tiles:
        gm = gradmag(ym)
        dy, dx, amb = offset(ym, yc)
        base.append({"A": float(gm.mean()), "dy": dy, "dx": dx, "amb": amb})
    n_base = sum(1 for b in base if b["amb"] >= UNAMBIGUITY)
    print("baseline tiles clearing the floor: %d of %d" % (n_base, len(tiles)))

    print("\n%6s %9s %10s %14s %14s" % ("N", "A abs%", "n_loc", "L med|dev| px",
                                        "L med signed"))
    print("-" * 60)
    rows = []
    for n in LEVELS:
        A, dev, signed = [], [], []
        for (ym, yc), b in zip(tiles, base):
            qm, qc = narrow(ym, n), narrow(yc, n)
            A.append(100.0 * (float(gradmag(qm).mean()) - b["A"]) / max(b["A"], 1e-9))
            if b["amb"] < UNAMBIGUITY:
                continue
            dy, dx, amb = offset(qm, qc)
            if amb < UNAMBIGUITY:
                continue
            dev.append(float(np.hypot(dy - b["dy"], dx - b["dx"])))
            signed.append(dy - b["dy"])
        r = {"N": n, "A_median_abs_pct": float(np.median(np.abs(A))),
             "n_location": len(dev),
             "L_median_abs_dev_px": float(np.median(dev)) if dev else float("nan"),
             "L_median_signed_px": float(np.median(signed)) if signed else float("nan")}
        rows.append(r)
        print("%6d %9.2f %10d %14.4f %14.4f"
              % (n, r["A_median_abs_pct"], r["n_location"],
                 r["L_median_abs_dev_px"], r["L_median_signed_px"]))

    counts = [r["n_location"] for r in rows]
    q1 = len(set(counts)) > 1
    q2 = rows[0]["L_median_abs_dev_px"] < 0.1

    def cross(key, th):
        for r in rows:
            if r[key] > th:
                return r["N"]
        return None

    n_a, n_l = cross("A_median_abs_pct", 20.0), cross("L_median_abs_dev_px", 0.2)
    q3_orch = (n_a is not None and n_l is not None and n_a > n_l)
    q4 = (abs(rows[0]["L_median_abs_dev_px"])
          > 3.0 * abs(rows[0]["L_median_signed_px"]) - 1e-12)

    print("\n[pre-registered gates]")
    print("  Q1 support floor does not saturate    : %s  (counts %s)"
          % ("PASS" if q1 else "FAIL", counts))
    print("  Q2 N=256 location bias < 0.1 px       : %s  (%.4f px)"
          % ("PASS" if q2 else "FAIL", rows[0]["L_median_abs_dev_px"]))
    print("  Q3 ORCH ordering N_A > N_L            : %s  (A@20%% N=%s, L@0.2px N=%s)"
          % ("PASS" if q3_orch else "FAIL", n_a, n_l))
    print("  Q4 signed median masked scatter       : %s  (|dev| %.4f vs signed %.4f)"
          % ("PASS" if q4 else "FAIL", rows[0]["L_median_abs_dev_px"],
             rows[0]["L_median_signed_px"]))
    verdict = ("ORCH ORDERING HOLDS" if q3_orch else
               "ORCH ORDERING REVERSED ON M111 DATA: dispersion is the more robust family")
    print("\nVERDICT: %s" % verdict)

    doc = {"tile": TILE, "stride": STRIDE, "n_tiles": len(tiles),
           "unambiguity_floor": UNAMBIGUITY, "baseline_tiles_clearing_floor": n_base,
           "rows": rows, "A_cross_20pct_at_N": n_a, "L_cross_0p2px_at_N": n_l,
           "gates": {"Q1_floor_varies": bool(q1), "Q2_clean_at_256": bool(q2),
                     "Q3_orch_ordering": bool(q3_orch), "Q4_signed_masked": bool(q4)},
           "verdict": verdict}
    dst = os.path.join(OUT, "levels_sweep_v2.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
