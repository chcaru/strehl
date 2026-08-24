"""M103: is the +37% edge acutance real, or a brightness-normalisation artifact?

WHY
---
`src/photo.py` reported acutance rising monotonically with radius, +37% at the
frame edge, and I published that in report section 9 as the photograph getting
sharper. The orchestrator has since measured, with a purpose-built
orientation instrument, that the residual reaches the render as ~1 px rather
than 150, and my paired run of that instrument (src/aniso_pair.py) returns a
NULL: every annulus CI overlaps and the centre -- where geometry forbids any
scale-induced change -- moves as much as the edge.

Two measurements of the same pair of files disagree. One of them is wrong and I
need to know which before I correct or defend the claim.

THE SUSPECT
-----------
photo.py's acutance is

    mean(|grad|^2) / mean(intensity)^2

with the numerator AND denominator computed inside each arm separately. The tile
SELECTION is paired (the std>1 test is applied to the `before` tile only, so the
same tiles are used in both arms), but the NORMALISATION is not. Any difference
in brightness between the two renders therefore enters the reported ratio
directly, and as the inverse square:

    ratio_reported = (G_after / G_before) * (m_before / m_after)^2

so the two renders being 5% different in mean level at some radius would move the
reported acutance ratio by ~11% with no change in sharpness whatsoever. The two
files do differ at the top end (max 56833 vs 59493 DN), which is what prompted
this check.

WHAT THIS SCRIPT DOES
---------------------
Recomputes photo.py's exact bins and exact tile selection, and splits the
reported ratio into its two factors:

    G_ratio  = mean|grad|^2 after / before      <- the sharpness part
    m_ratio  = mean intensity after / before    <- the brightness part

If G_ratio is flat near 1.0 while the published ratio rises to 1.37, the
published number was brightness, not sharpness.

CONTROLS
--------
PLACEBO      before vs before: every ratio must be exactly 1.0.
POSITIVE     before vs a deliberately dimmed copy of before (x0.95, sharpness
             untouched by construction): the normalised acutance MUST report a
             spurious ~1.108x "improvement" and the unnormalised G_ratio must
             report exactly 1.0. This demonstrates the artifact exists and is
             the size the algebra predicts, rather than asserting it.

USAGE
  python acutance_check.py <before.tiff> <after.tiff> <out.json>
"""

import json
import os
import sys

import numpy as np
import tifffile

T = 256
BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


def tile_stats(g):
    gy, gx = np.gradient(g.astype(np.float64))
    return float((gx * gx + gy * gy).mean()), float(g.mean())


def collect(ga, gb, h, w):
    """photo.py's selection and binning, but keeping the two factors apart."""
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cx, cy))
    recs = []
    for y in range(0, h - T + 1, T):
        for x in range(0, w - T + 1, T):
            ta, tb = ga[y:y + T, x:x + T], gb[y:y + T, x:x + T]
            if ta.std() < 1.0:          # selection on `before`, as photo.py does
                continue
            r = float(np.hypot(x + T / 2 - cx, y + T / 2 - cy)) / rmax
            Ga, ma = tile_stats(ta)
            Gb, mb = tile_stats(tb)
            recs.append((r, Ga, ma, Gb, mb))
    return recs


def report(recs, title):
    print(f"\n{title}")
    print(f"  {'r/rmax':>10} {'tiles':>6} {'acut_ratio':>11} {'G_ratio':>9} "
          f"{'m_ratio':>9} {'predicted':>10}")
    rows = []
    for lo, hi in BINS:
        sel = [t for t in recs if lo <= t[0] < hi]
        if not sel:
            continue
        Ga = np.mean([t[1] for t in sel])
        ma = np.mean([t[2] for t in sel])
        Gb = np.mean([t[3] for t in sel])
        mb = np.mean([t[4] for t in sel])
        # photo.py averaged the per-tile normalised value, so reproduce that too
        acut_a = np.mean([t[1] / (t[2] ** 2) for t in sel if t[2] > 0])
        acut_b = np.mean([t[3] / (t[4] ** 2) for t in sel if t[4] > 0])
        ratio = acut_b / acut_a
        g_ratio = Gb / Ga
        m_ratio = mb / ma
        pred = g_ratio / (m_ratio ** 2)
        rows.append({"lo": lo, "hi": hi, "n": len(sel),
                     "acut_ratio": float(ratio), "G_ratio": float(g_ratio),
                     "m_ratio": float(m_ratio), "predicted": float(pred),
                     "mean_before": float(ma), "mean_after": float(mb)})
        print(f"  {lo:.1f}-{hi:.1f}".ljust(12)
              + f"{len(sel):>6} {ratio:>11.4f} {g_ratio:>9.4f} "
                f"{m_ratio:>9.4f} {pred:>10.4f}")
    allsel = recs
    Ga = np.mean([t[1] for t in allsel]); Gb = np.mean([t[3] for t in allsel])
    ma = np.mean([t[2] for t in allsel]); mb = np.mean([t[4] for t in allsel])
    print(f"  {'whole':>10} {len(allsel):>6} {'':>11} {Gb / Ga:>9.4f} "
          f"{mb / ma:>9.4f}")
    return rows


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    before_p, after_p, out_p = sys.argv[1:4]
    A = tifffile.imread(before_p)
    B = tifffile.imread(after_p)
    if A.shape != B.shape:
        sys.exit(f"shape mismatch {A.shape} vs {B.shape}")
    h, w = A.shape[:2]
    ga = A[..., 1].astype(np.float64)
    gb = B[..., 1].astype(np.float64)
    print(f"{w}x{h}  before={os.path.basename(before_p)}  "
          f"after={os.path.basename(after_p)}")
    print("acut_ratio reproduces photo.py's published number.")
    print("G_ratio is the same comparison with the intensity normalisation")
    print("REMOVED. predicted = G_ratio / m_ratio^2 and should track acut_ratio,")
    print("which confirms the decomposition is arithmetically complete.")

    real = collect(ga, gb, h, w)
    rows_real = report(real, "REAL PAIR (shipped -> M103)")

    placebo = collect(ga, ga, h, w)
    rows_pl = report(placebo, "PLACEBO (before vs before) -- must be all 1.0000")

    dim = ga * 0.95
    rows_pos = report(collect(ga, dim, h, w),
                      "POSITIVE CONTROL (before vs before x0.95, sharpness "
                      "identical by construction)")
    print("  ^ a pure 5% dimming must read G_ratio 1.0000 and acut_ratio "
          "~1.1080 (=1/0.95^2).")

    pl_bad = max(abs(r["acut_ratio"] - 1.0) for r in rows_pl)
    print(f"\nPLACEBO max |acut_ratio - 1| = {pl_bad:.2e} "
          f"-- {'PASS' if pl_bad < 1e-9 else 'FAIL'}")

    json.dump({"before": before_p, "after": after_p, "real": rows_real,
               "placebo": rows_pl, "positive_dim095": rows_pos},
              open(out_p, "w"), indent=1)
    print(f"wrote {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
