"""Levels sweep, third attempt: a location estimator with adequate sample.

TWO FAILED INSTRUMENTS PRECEDE THIS ONE, both kept in the record:

  levels_sweep.py    peak floor `pk > 0.02` was INERT -- admitted every tile
                     including featureless ones, giving 27.47 px "bias" at
                     N = 256 where narrowing is nearly a no-op.
  levels_sweep_v2.py unambiguity floor 2.0 was too STRICT -- 4 of 100 tiles
                     cleared it and the sweep ran at n = 0..2 per level. It
                     printed "ORCH ORDERING HOLDS" from a SINGLE tile.

The second failure is the more instructive. ORCH's advice was to log the sample
count at every level and require it to VARY. I implemented exactly that as gate
Q1, and Q1 PASSED -- because the counts varied between 2, 1 and 0. A count that
varies by collapsing to zero satisfies a variation test and has measured
nothing. Adequacy is a separate requirement from variation and neither implies
the other.

The root cause of both is the design, not the threshold: merged-against-control
is a CROSS-IMAGE registration between two genuinely different renders, so the
correlation peak is legitimately weak and no floor setting has both sample and
reliability. Replaced with a planted-shift design, which is what ORCH's location
claim is actually about -- can a location estimator recover a displacement under
narrowing -- and which has strong correlation by construction because both arms
are the same content.

Design: plant a known sub-pixel shift by Fourier phase ramp at full depth,
narrow BOTH copies to N levels, recover by phase correlation, and compare
against the recovery at FULL depth rather than against the planted truth. That
cancels any estimator bias and isolates the narrowing.

PRE-REGISTERED, before these numbers exist:

  R1 ADEQUACY, not merely variation: n >= 30 at every level. If n falls below
     30 anywhere, the sweep is void at that level and I report it as void
     rather than reading a number off it.
  R2 at N = 256 the recovered shift sits within 0.02 px of the full-depth
     recovery, confirming the instrument is quiet when nothing is done to it.
  R3 location degrades monotonically and crosses 0.2 px at some N_L.
  R4 ORDERING, the live question: dispersion A crosses 20% at N_A = 4 on the
     already-measured ladder. ORCH's rule requires the more fragile family to
     break FIRST, i.e. N_A > N_L. If N_L < 4, location is the more robust
     family and ORCH's ordering HOLDS. If N_L > 4, it is REVERSED on this data.

Writes: C:\\dev\\strehl-out\\M111-pil-audit\\levels_sweep_v3.json
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M111-pil-audit"
MERGED = os.path.join(r"C:\dev\strehl-out\ORCH-thennow", "marker-HEAD-8f46f04.tif")
TILE = 256
STRIDE = 384
LEVELS = [256, 128, 64, 48, 32, 24, 16, 12, 8, 6, 4, 3, 2]
PLANT_DY, PLANT_DX = 0.37, -0.23


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


def fshift(y, dy, dx):
    F = np.fft.fft2(y)
    ky = np.fft.fftfreq(y.shape[0])[:, None]
    kx = np.fft.fftfreq(y.shape[1])[None, :]
    return np.real(np.fft.ifft2(F * np.exp(-2j * np.pi * (ky * dy + kx * dx))))


def offset(a, b):
    a, b = a - a.mean(), b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    cross = np.fft.rfft2(a * win) * np.conj(np.fft.rfft2(b * win))
    mag = np.abs(cross)
    mag[mag == 0] = 1e-12
    r = np.fft.irfft2(cross / mag, s=a.shape)
    pk = np.unravel_index(np.argmax(r), r.shape)
    peak = float(r[pk])

    def refine(axis):
        i, n = pk[axis], r.shape[axis]
        am = r[((i - 1) % n, pk[1])] if axis == 0 else r[(pk[0], (i - 1) % n)]
        ap = r[((i + 1) % n, pk[1])] if axis == 0 else r[(pk[0], (i + 1) % n)]
        den = am - 2 * peak + ap
        d = 0.0 if abs(den) < 1e-12 else 0.5 * (am - ap) / den
        v = i + float(np.clip(d, -1, 1))
        return v if v <= n / 2 else v - n

    return refine(0), refine(1), peak


def main():
    os.makedirs(OUT, exist_ok=True)
    mt = tifffile.imread(MERGED)
    assert mt.dtype == np.uint16, mt.dtype
    h, w = mt.shape[0], mt.shape[1]
    tiles = []
    for y0 in range(200, h - TILE - 200, STRIDE):
        for x0 in range(200, w - TILE - 200, STRIDE):
            y = luma(mt[y0:y0 + TILE, x0:x0 + TILE])
            if y.std() < 5.0:
                continue
            tiles.append(y)
    print("tiles %d   plant (%.2f, %.2f) px" % (len(tiles), PLANT_DY, PLANT_DX))

    base = []
    for y in tiles:
        s = fshift(y, PLANT_DY, PLANT_DX)
        dy, dx, pk = offset(s, y)
        base.append({"A": float(gradmag(y).mean()), "dy": dy, "dx": dx,
                     "shifted": s, "y": y})
    bdy = float(np.median([b["dy"] for b in base]))
    bdx = float(np.median([b["dx"] for b in base]))
    print("full-depth recovery: dy %+.4f dx %+.4f  (planted %+.2f %+.2f)"
          % (bdy, bdx, PLANT_DY, PLANT_DX))

    print("\n%6s %9s %8s %16s %14s" % ("N", "A abs%", "n_loc", "L med|dev| px", "status"))
    print("-" * 60)
    rows = []
    for n in LEVELS:
        A, dev = [], []
        for b in base:
            qy, qs = narrow(b["y"], n), narrow(b["shifted"], n)
            A.append(100.0 * (float(gradmag(qy).mean()) - b["A"]) / max(b["A"], 1e-9))
            dy, dx, pk = offset(qs, qy)
            if not np.isfinite(dy) or not np.isfinite(dx):
                continue
            dev.append(float(np.hypot(dy - b["dy"], dx - b["dx"])))
        void = len(dev) < 30
        r = {"N": n, "A_median_abs_pct": float(np.median(np.abs(A))),
             "n_location": len(dev),
             "L_median_abs_dev_px": float(np.median(dev)) if dev else float("nan"),
             "void": bool(void)}
        rows.append(r)
        print("%6d %9.2f %8d %16.4f %14s"
              % (n, r["A_median_abs_pct"], r["n_location"], r["L_median_abs_dev_px"],
                 "VOID n<30" if void else "ok"))

    live = [r for r in rows if not r["void"]]
    r1 = len(live) == len(rows)
    r2 = rows[0]["L_median_abs_dev_px"] < 0.02

    def cross(key, th):
        for r in live:
            if r[key] > th:
                return r["N"]
        return None

    n_a, n_l = cross("A_median_abs_pct", 20.0), cross("L_median_abs_dev_px", 0.2)
    r3 = n_l is not None
    ordering = ("HOLDS" if (n_a is not None and n_l is not None and n_a > n_l)
                else ("REVERSED" if (n_a is not None and n_l is not None) else "UNRESOLVED"))

    print("\n[pre-registered gates]")
    print("  R1 adequacy n>=30 at EVERY level : %s  (counts %s)"
          % ("PASS" if r1 else "FAIL", [r["n_location"] for r in rows]))
    print("  R2 quiet at N=256 (<0.02 px)     : %s  (%.4f px)"
          % ("PASS" if r2 else "FAIL", rows[0]["L_median_abs_dev_px"]))
    print("  R3 location crosses 0.2 px       : %s  (N_L=%s)"
          % ("PASS" if r3 else "FAIL", n_l))
    print("  R4 ORDERING (ORCH needs N_A>N_L) : %s  (N_A=%s, N_L=%s)"
          % (ordering, n_a, n_l))

    verdict = {"HOLDS": "ORCH FAMILY ORDERING HOLDS: location is the more robust family",
               "REVERSED": ("ORCH FAMILY ORDERING REVERSED ON M111 DATA: "
                            "dispersion is the more robust family"),
               "UNRESOLVED": "UNRESOLVED"}[ordering]
    print("\nVERDICT: %s" % verdict)
    doc = {"tile": TILE, "stride": STRIDE, "n_tiles": len(tiles),
           "plant_px": [PLANT_DY, PLANT_DX],
           "full_depth_recovery": {"dy": bdy, "dx": bdx},
           "rows": rows, "A_cross_20pct_at_N": n_a, "L_cross_0p2px_at_N": n_l,
           "gates": {"R1_adequacy": bool(r1), "R2_quiet": bool(r2),
                     "R3_location_crosses": bool(r3), "R4_ordering": ordering},
           "verdict": verdict}
    dst = os.path.join(OUT, "levels_sweep_v3.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
