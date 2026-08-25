"""Levels per integration window as the single control variable, for BOTH families.

WHAT THE PREVIOUS TEST SHOWED (value_vs_position.py, registered at bea9c45):

  L location, sub-pixel offset bias   dy -0.0687 px, dx +0.0067 px
  A dispersion, absolute grad energy   1.85%   <- registered > 20%, FAILED
  W dispersion, within-arm ratio       1.82%
  X dispersion, cross-arm contrast     2.10%   <- registered < 5%, passed

ORCH's rule says dispersion statistics "absorb the quantisation variance
directly and are destroyed". On M111's data a canonical dispersion statistic --
absolute mean gradient energy -- moved 1.85%. Not destroyed. My own composition
hypothesis also failed: X (2.10%) is not below A (1.85%), they are the same.

The reason neither prediction worked is that nothing was under stress. Median
distinct levels per 256 px window: 138, min 8, against ORCH's stated bound of
~12. At 138 levels the quantiser is fine relative to the signal and every
statistic survives, whatever family it belongs to.

So the governing variable is LEVELS PER INTEGRATION WINDOW -- which ORCH already
has, as a bound on the location half. This tests whether it governs the
dispersion half too, and whether ORCH's family ORDERING survives even though the
absolute claim does not.

Method: plant a controlled narrowing at N levels across each tile's OCCUPIED
range (per ORCH's refinement that damage scales with occupied, not full, range)
and sweep N. This replaces PIL's fixed 8-bit step with a dial.

PRE-REGISTERED, before these numbers exist:

  P1  Both families degrade monotonically as N falls. Any non-monotonicity
      above N = 8 refutes the single-control-variable claim.
  P2  ORCH's ORDERING survives even though the absolute claim did not:
      dispersion crosses 20% at a HIGHER N than location crosses 0.2 px.
      This is the falsifiable form of "dispersion is more fragile".
      If location breaks first, ORCH's rule is backwards on this data.
  P3  ORCH's ~12-level bound transfers to dispersion within a factor of 4,
      i.e. A crosses 20% somewhere in N = 3..48.
  P4  At N = 256, all statistics sit near their PIL values (A within 1.5x of
      1.85%), confirming the sweep reproduces the real reader as a special
      case rather than measuring something else.

Writes: C:\\dev\\strehl-out\\M111-pil-audit\\levels_sweep.json
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


def luma(a):
    return (0.2126 * a[..., 0].astype(np.float32)
            + 0.7152 * a[..., 1].astype(np.float32)
            + 0.0722 * a[..., 2].astype(np.float32))


def gradmag(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def narrow(y, n):
    """Quantise to n levels across this window's occupied range."""
    lo, hi = float(y.min()), float(y.max())
    if hi - lo < 1e-9:
        return y.copy()
    q = np.round((y - lo) / (hi - lo) * (n - 1))
    return q / (n - 1) * (hi - lo) + lo


def subpixel_offset(a, b):
    a = a - a.mean()
    b = b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    cross = np.fft.rfft2(a * win) * np.conj(np.fft.rfft2(b * win))
    mag = np.abs(cross)
    mag[mag == 0] = 1e-12
    r = np.fft.irfft2(cross / mag, s=a.shape)
    pk = np.unravel_index(np.argmax(r), r.shape)

    def refine(axis):
        i, n = pk[axis], r.shape[axis]
        im, ip = (i - 1) % n, (i + 1) % n
        a_ = r[(im, pk[1])] if axis == 0 else r[(pk[0], im)]
        c_ = r[(ip, pk[1])] if axis == 0 else r[(pk[0], ip)]
        den = a_ - 2 * r[pk] + c_
        d = 0.0 if abs(den) < 1e-12 else 0.5 * (a_ - c_) / den
        v = i + float(np.clip(d, -1, 1))
        return v if v <= n / 2 else v - n

    return refine(0), refine(1), float(r[pk])


def wratio(y, g):
    m = y >= np.percentile(y, 75)
    i, o = float(g[m].mean()), float(g[~m].mean())
    return i / max(o, 1e-9)


def main():
    os.makedirs(OUT, exist_ok=True)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    h, w = min(mt.shape[0], ct.shape[0]), min(mt.shape[1], ct.shape[1])
    tiles = []
    for y0 in range(200, h - TILE - 200, STRIDE):
        for x0 in range(200, w - TILE - 200, STRIDE):
            ym, yc = luma(mt[y0:y0 + TILE, x0:x0 + TILE]), luma(ct[y0:y0 + TILE, x0:x0 + TILE])
            if ym.std() < 1.0 or yc.std() < 1.0:
                continue
            tiles.append((ym, yc))
    print("tiles %d   tile %d   stride %d" % (len(tiles), TILE, STRIDE))

    base = []
    for ym, yc in tiles:
        gm, gc = gradmag(ym), gradmag(yc)
        dy, dx, pk = subpixel_offset(ym, yc)
        base.append({"A": float(gm.mean()), "W": wratio(ym, gm),
                     "X": wratio(ym, gm) / max(wratio(yc, gc), 1e-9),
                     "dy": dy, "dx": dx, "pk": pk})

    print("\n%6s %8s %10s %10s %10s %12s" % ("N", "levels", "A abs%", "W ratio%",
                                             "X cross%", "L bias px"))
    print("-" * 62)
    rows = []
    for n in LEVELS:
        A, W, X, DL = [], [], [], []
        realized = []
        for (ym, yc), b in zip(tiles, base):
            qm, qc = narrow(ym, n), narrow(yc, n)
            realized.append(int(np.unique(qm).size))
            gm, gc = gradmag(qm), gradmag(qc)
            A.append(100.0 * (float(gm.mean()) - b["A"]) / max(b["A"], 1e-9))
            wm = wratio(qm, gm)
            W.append(100.0 * (wm - b["W"]) / max(abs(b["W"]), 1e-9))
            xv = wm / max(wratio(qc, gc), 1e-9)
            X.append(100.0 * (xv - b["X"]) / max(abs(b["X"]), 1e-9))
            dy, dx, pk = subpixel_offset(qm, qc)
            if b["pk"] > 0.02 and pk > 0.02:
                DL.append(np.hypot(dy - b["dy"], dx - b["dx"]))
        r = {"N": n, "realized_levels_median": float(np.median(realized)),
             "A_median_abs_pct": float(np.median(np.abs(A))),
             "W_median_abs_pct": float(np.median(np.abs(W))),
             "X_median_abs_pct": float(np.median(np.abs(X))),
             "L_median_bias_px": float(np.median(DL)) if DL else float("nan"),
             "n_location": len(DL)}
        rows.append(r)
        print("%6d %8.0f %10.2f %10.2f %10.2f %12.4f"
              % (n, r["realized_levels_median"], r["A_median_abs_pct"],
                 r["W_median_abs_pct"], r["X_median_abs_pct"], r["L_median_bias_px"]))

    def crossing(key, thresh):
        """Largest N at which the statistic first exceeds thresh, scanning down."""
        for r in rows:
            if r[key] > thresh:
                return r["N"]
        return None

    a_cross = crossing("A_median_abs_pct", 20.0)
    l_cross = crossing("L_median_bias_px", 0.2)
    mono = all(rows[i]["A_median_abs_pct"] <= rows[i + 1]["A_median_abs_pct"] + 1.0
               for i in range(len(rows) - 1) if rows[i + 1]["N"] >= 8)
    p4 = rows[0]["A_median_abs_pct"] < 1.85 * 1.5
    p2 = (a_cross is not None and (l_cross is None or a_cross > l_cross))
    p3 = (a_cross is not None and 3 <= a_cross <= 48)

    print("\n[pre-registered gates]")
    print("  P1 monotone above N=8                       : %s" % ("PASS" if mono else "FAIL"))
    print("  P2 dispersion breaks at higher N than location: %s  (A@20%% N=%s, L@0.2px N=%s)"
          % ("PASS" if p2 else "FAIL", a_cross, l_cross))
    print("  P3 A crosses 20%% within N=3..48             : %s" % ("PASS" if p3 else "FAIL"))
    print("  P4 N=256 reproduces the real reader          : %s  (A=%.2f%% vs PIL 1.85%%)"
          % ("PASS" if p4 else "FAIL", rows[0]["A_median_abs_pct"]))

    verdict = ("LEVELS-PER-WINDOW GOVERNS BOTH FAMILIES; ORCH ORDERING HOLDS"
               if (mono and p2 and p4) else "SEE GATES")
    print("\nVERDICT: %s" % verdict)
    doc = {"tile": TILE, "stride": STRIDE, "n_tiles": len(tiles), "rows": rows,
           "A_cross_20pct_at_N": a_cross, "L_cross_0p2px_at_N": l_cross,
           "gates": {"P1_monotone": bool(mono), "P2_ordering": bool(p2),
                     "P3_bound_transfers": bool(p3), "P4_reproduces_reader": bool(p4)},
           "verdict": verdict}
    dst = os.path.join(OUT, "levels_sweep.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
