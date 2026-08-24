"""M87 s31d -- the positive control B6 needs, and the posterisation threshold.

87 returned a NULL: election-index boundaries carry 1.04x the |high-pass| of
non-boundary background, against a rot180 null of 0.93x.  That is a claim
about my instrument until I show the instrument can respond, so this script
plants the exact mechanism ORCH hypothesised and sweeps its amplitude.

THE PLANT.  ORCH's photometric-step hypothesis is that the winner field jumps
between two frame indices and, if those frames differ photometrically, the
render carries a signed step there.  So plant precisely that:

        g'(x) = g(x) + s * index(x)

which gives every pair of adjacent frame indices a photometric difference of
exactly s DN.  It is MONOTONE in frame index, which M99 fact 23 requires: a
non-monotone plant understates an election-sensitive effect by about 11x.
Sweeping s calibrates the null in DN -- "the test would have seen s >= X, and
the render shows less than that".

  BAR B8, three branches.  s_min = smallest planted per-frame step whose
  enrichment reaches the 1.5x of B6.
      s_min <= 10 DN  -> the null is TIGHT; a photometric step is excluded
      s_min >= 100 DN -> the test is BLUNT and B6's null means little
      otherwise       -> MODERATE, report s_min as the exclusion limit

THE SECOND QUESTION.  If the arcs carry no brightness step, why are they
visible?  B5 measured noise = 283.3 * n_eff^-0.5228 across a 218x range of
n_eff, and ORCH's diagnostic cast has a quantum of 115.7 DN.  Those two
numbers cross.  Posterisation appears where the noise falls below about one
code, so the prediction, again with no free parameter, is

        n_eff_crossing = (283.3 / 115.7)^2 = 5.99

  BAR B9, three branches, on the measured flatness-0.5 crossing:
      within a factor of 2 of 5.99  -> the visible banding IS the cast
                                       quantum crossing the n_eff field
      outside a factor of 5         -> it is not
      otherwise                     -> PARTIAL
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
B6_YES = 1.5
PLANT_S = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0]
B8_TIGHT, B8_BLUNT = 10.0, 100.0
NOISE_A, NOISE_B = 283.3, -0.5228      # measured in 87-election.py


def main():
    out = {}
    g = tifffile.imread(SCRATCH / "s31-bee3.tif")[Y0:Y0 + H, X0:X0 + W, 1
                                                  ].astype(np.float32)
    py0, px0 = Y0 // 2, X0 // 2
    idx = tifffile.imread(SCRATCH / "s31-index.tif")[py0:py0 + H // 2,
                                                     px0:px0 + W // 2].astype(np.float32)
    nef = tifffile.imread(SCRATCH / "s31-neff.tif")[py0:py0 + H // 2,
                                                    px0:px0 + W // 2].astype(np.float32)
    idx = np.repeat(np.repeat(idx, 2, 0), 2, 1)
    nef = np.repeat(np.repeat(nef, 2, 0), 2, 1)

    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    dn_code = span / 127.0
    subj = ndimage.binary_opening(
        ndimage.binary_closing(g < med - span, np.ones((5, 5))), np.ones((3, 3)))
    bg = ~ndimage.binary_dilation(subj, np.ones((9, 9)))

    gy, gx = np.gradient(idx)
    bnd = ndimage.binary_dilation((np.abs(gy) + np.abs(gx)) > 0.5,
                                  np.ones((3, 3))) & bg
    off = bg & ~ndimage.binary_dilation(bnd, np.ones((7, 7)))
    jump = np.abs(np.diff(idx, axis=1))
    jump = jump[(jump > 0) & bg[:, 1:]]
    print("=== the population ===")
    print(f"  boundary px {int(bnd.sum())}, off-boundary px {int(off.sum())}")
    print(f"  |delta index| across a boundary: median {np.median(jump):.0f},"
          f" p90 {np.percentile(jump, 90):.0f}, max {jump.max():.0f}")
    out["boundary_px"] = int(bnd.sum())
    out["off_px"] = int(off.sum())
    out["djump_median"] = float(np.median(jump))
    out["djump_p90"] = float(np.percentile(jump, 90))

    def enrichment(field):
        hp = field - ndimage.median_filter(field, size=5)
        a = float(np.median(np.abs(hp[bnd])))
        b = float(np.median(np.abs(hp[off])))
        return a, b, a / b

    print("\n=== B8  positive control: plant a monotone per-frame step ===")
    a0, b0, e0 = enrichment(g)
    print(f"  s =   0.0 DN (as rendered)  on {a0:7.1f}  off {b0:7.1f}"
          f"   enrichment {e0:5.2f}x")
    rows = [[0.0, a0, b0, e0]]
    s_min = None
    for s in PLANT_S:
        a, b, e = enrichment(g + s * idx)
        star = ""
        if e >= B6_YES and s_min is None:
            s_min, star = s, "   <-- detected"
        print(f"  s = {s:5.1f} DN               on {a:7.1f}  off {b:7.1f}"
              f"   enrichment {e:5.2f}x{star}")
        rows.append([s, a, b, e])
    out["B8_rows"] = rows
    out["B8_s_min"] = s_min
    if s_min is None:
        b8 = "the test is BLUNT and B6's null means little"
    elif s_min <= B8_TIGHT:
        b8 = "the null is TIGHT; a photometric step is excluded"
    elif s_min >= B8_BLUNT:
        b8 = "the test is BLUNT and B6's null means little"
    else:
        b8 = f"MODERATE; exclusion limit {s_min:.0f} DN per frame"
    print(f"  B8: {b8}")
    out["B8"] = b8

    if s_min is not None:
        pct = 100.0 * s_min / med
        print(f"  {s_min:.0f} DN per adjacent frame is {pct:.4f}% of the"
              f" background level, i.e. {pct*298:.1f}% across the 299-frame"
              f" bracket.")
        print(f"  M24's noisiest corpus stack drifts 11.70% end to end,"
              f" = {0.1170*med/298:.2f} DN per adjacent frame.")
        out["B8_pct_per_frame"] = pct
        out["B8_pct_bracket"] = pct * 298
        out["m24_worst_dn_per_frame"] = 0.1170 * med / 298

    print("\n=== B9  does the cast quantum cross the n_eff field? ===")
    pred = (NOISE_A / dn_code) ** (-1.0 / NOISE_B)
    print(f"  noise(n_eff) = {NOISE_A:.1f} * n_eff^{NOISE_B:+.4f} DN  (B5)")
    print(f"  one output code {dn_code:.1f} DN")
    print(f"  predicted crossing at n_eff = {pred:.2f}")
    u8 = np.clip((g - med) / span * 127.0 + 127.0, 0, 255).astype(np.uint8)
    same = np.zeros_like(u8, bool)
    same[:, :-1] = u8[:, :-1] == u8[:, 1:]
    m = bg.astype(np.float32)
    cnt = ndimage.uniform_filter(m, 15)
    flat = ndimage.uniform_filter(same.astype(np.float32) * m, 15) / np.maximum(cnt, 1e-6)
    nlo = ndimage.uniform_filter(nef * m, 15) / np.maximum(cnt, 1e-6)
    sel = bg & (cnt > 0.95) & (nlo >= 1.0)
    xs, ys = nlo[sel], flat[sel]
    ed = np.unique(np.percentile(xs, np.linspace(0, 100, 17)))
    print(f"  {'n_eff':>9} {'flat frac':>10} {'pred noise':>11} {'n':>8}")
    prev = None
    cross = None
    for i in range(len(ed) - 1):
        b = (xs >= ed[i]) & (xs < ed[i + 1])
        if b.sum() < 500:
            continue
        xm, ym = float(np.median(xs[b])), float(np.median(ys[b]))
        print(f"  {xm:9.1f} {ym:10.3f} {NOISE_A*xm**NOISE_B:11.1f} {int(b.sum()):8d}")
        if prev and prev[1] < 0.5 <= ym:
            x0_, y0_ = prev
            cross = x0_ + (0.5 - y0_) * (xm - x0_) / (ym - y0_)
        prev = (xm, ym)
    out["B9_pred"] = float(pred)
    out["B9_cross"] = float(cross) if cross else None
    if cross is None:
        b9 = "no crossing in range"
    else:
        r = cross / pred
        b9 = ("the visible banding IS the cast quantum crossing n_eff"
              if 0.5 <= r <= 2.0 else
              "it is not" if r < 0.2 or r > 5.0 else "PARTIAL")
        print(f"  measured flatness-0.5 crossing at n_eff = {cross:.2f}"
              f"   ratio to prediction {r:.2f}x")
    print(f"  B9: {b9}")
    out["B9"] = b9

    DATA.mkdir(exist_ok=True)
    (DATA / "88-controls.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '88-controls.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
