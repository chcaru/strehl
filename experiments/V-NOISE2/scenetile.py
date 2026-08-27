"""scenetile.py -- is strehl's lower scene term lost detail, or averaged-down
fixed-pattern noise?

WHY.  hd2.py's scene/noise decomposition foreclosed the "cleaner because
blurrier" objection on 113 -- strehl held the lowest noise AND the highest
scene term -- but on 119 it did the opposite: strehl 0.00681 against enfuse
0.01224, so strehl carries 44% LESS fine structure in the same tiles.  On the
corpus's softest subject (V-EYES sec.5.5 measures 119MSDCF at 0.8110 against a
per-site best frame) that is exactly the alternative explanation this lane
cannot wave away, and it cannot be answered by pointing at a separate
sharpness run.

THE DISCRIMINATION.  The tiles that decomposition runs on are the FLAT ones --
the bottom quartile by max-over-frames high-pass variance, i.e. the tiles
chosen for having the least subject detail in them.  So its "scene term" is
not mostly subject detail; it is whatever fine structure is common to both
half-stacks.  Two candidates:

  (a) genuine faint detail, which strehl has lost -> a real resolution deficit
  (b) fixed-pattern noise.  V-CALIB measures PRNU at 0.286% of signal and DSNU
      at 0.389 DN on this body.  The frames are ALIGNED before fusion, so a
      given scene point lands on DIFFERENT sensor sites across frames; the
      fixed pattern is therefore NOT common across aligned frames, and
      AVERAGING suppresses it while SELECTION does not.  strehl averages 84.7%
      of the finest band on 119; `enfuse --hard-mask` selects one frame's
      pixel.  Under (b) strehl SHOULD show a lower scene term in flat tiles and
      it would mean nothing about resolution.

(a) and (b) make opposite predictions in the DETAIL tiles -- the top quartile
by the same statistic, where genuine subject structure dominates and the
fixed pattern is a much smaller fraction of the residual:

  under (a) strehl trails on the scene term in DETAIL tiles too
  under (b) strehl's deficit is confined to FLAT tiles and closes in DETAIL

Registered before running, as the lane requires.  Neither outcome is a pass or
a fail; they are different results and both get reported.

CAVEAT, stated up front rather than discovered later.  In DETAIL tiles the
half-difference is NOT a clean noise estimate: scene structure only cancels
between halves if the halves are registered, and residual misregistration puts
scene into the difference.  That inflates the noise term and DEFLATES the
scene term, and it does so worst on the arm whose halves sit furthest apart --
which is strehl.  So the detail-tile scene term is a LOWER BOUND for strehl and
the comparison there runs AGAINST strehl.  If strehl closes the gap anyway,
that is meaningful; if it does not, this measurement cannot separate (a) from
misregistration and says so.

Usage:  python scenetile.py <key> [<key> ...]
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
from noisefree import Arm, sigmas as _sigmas                       # noqa: E402
from halfdiff import half_sigma                                    # noqa: E402
from hd2 import SUBJECTS, paths_for, scales_for, bits_of, ROOT     # noqa: E402


def decomp(arms, cells):
    """flat-ROI sigma, half-diff sigma, and the quadrature scene term."""
    out = {}
    for k, (A, B) in arms.items():
        fl, nz = [], []
        for (y, x) in cells:
            ca, cb = A.rgb(y, x), B.rgb(y, x)
            if ca is None or cb is None or ca.shape != cb.shape:
                continue
            s1 = _sigmas(ca)
            s2 = half_sigma(ca, cb, shift=(k == "strehl"))
            if s1 is None or s2 is None:
                continue
            fl.append(s1[0])
            nz.append(s2[0])
        if not fl:
            continue
        f, n = float(np.median(fl)), float(np.median(nz))
        out[k] = [f, n, float(np.sqrt(max(f * f - n * n, 0.0))),
                  min((n / f) ** 2, 1.0), len(fl)]
    return out


def run(key):
    meta = SUBJECTS[key]
    census, spec = paths_for(key)
    sc = scales_for(key)
    z = np.load(census)
    cells = [tuple(c) for c in z["cells"]]
    emax = z["emax"]
    flat_idx = list(z["flat"])
    q = len(flat_idx)
    detail_idx = list(np.argsort(emax)[-q:])

    arms = {}
    for k, (pa, pb, lab) in spec.items():
        if os.path.exists(pa) and os.path.exists(pb):
            arms[k] = (Arm(pa, sc[k], bits_of(pa), lab),
                       Arm(pb, sc[k], bits_of(pb), lab))

    print("=" * 100)
    print(f"SCENE TERM BY TILE CLASS -- {key} = {meta['name']} "
          f"({meta['n']} frames, {meta['depth']}, {meta['regime']}-dominated)")
    print(f"  FLAT   = bottom {q} of {len(cells)} by max-over-frames high-pass "
          f"variance   emax median {np.median(emax[flat_idx]):.6g}")
    print(f"  DETAIL = top    {q} of {len(cells)} by the same statistic"
          f"              emax median {np.median(emax[detail_idx]):.6g}")
    print(f"  separation {np.median(emax[detail_idx]) / np.median(emax[flat_idx]):.2f}x")
    print("=" * 100)

    res = {}
    for tag, idx in (("FLAT", flat_idx), ("DETAIL", detail_idx)):
        d = decomp(arms, [cells[i] for i in idx])
        res[tag] = d
        print(f"\n--- {tag} tiles ---")
        print(f"  {'arm':10s} {'flat-ROI sig':>14s} {'noise sig':>12s} "
              f"{'scene term':>12s} {'noise frac':>11s} {'n':>5s}")
        for k, v in d.items():
            print(f"  {k:10s} {v[0]:14.6f} {v[1]:12.5f} {v[2]:12.5f} "
                  f"{v[3] * 100:10.1f}% {v[4]:5d}")
        if "strehl" in d:
            best = max(d, key=lambda kk: d[kk][2])
            print(f"  highest scene term: {best}"
                  f"{'  <- strehl' if best == 'strehl' else '  <- NOT strehl'}")

    print("\n--- the discrimination ---")
    print(f"  {'arm':10s} {'scene FLAT':>12s} {'scene DETAIL':>14s} "
          f"{'ratio to strehl, FLAT':>22s} {'ratio to strehl, DETAIL':>24s}")
    sf = res["FLAT"].get("strehl", [0, 0, 1])[2]
    sd = res["DETAIL"].get("strehl", [0, 0, 1])[2]
    verdict = {}
    for k in res["FLAT"]:
        a = res["FLAT"][k][2]
        b = res["DETAIL"].get(k, [0, 0, np.nan])[2]
        verdict[k] = [a / sf if sf else np.nan, b / sd if sd else np.nan]
        print(f"  {k:10s} {a:12.5f} {b:14.5f} {verdict[k][0]:22.3f} "
              f"{verdict[k][1]:24.3f}")

    comps = [k for k in verdict if k != "strehl"]
    if comps:
        wf = max(verdict[k][0] for k in comps)
        wd = max(verdict[k][1] for k in comps)
        print(f"\n  worst comparator/strehl scene ratio: FLAT {wf:.3f}, "
              f"DETAIL {wd:.3f}")
        if wf > 1.05 and wd <= 1.05:
            print("  -> the deficit is CONFINED TO FLAT TILES and closes in "
                  "DETAIL.  Consistent with (b),")
            print("     fixed-pattern structure that averaging suppresses and "
                  "selection retains, and NOT")
            print("     with a resolution deficit.  Note this comparison runs "
                  "against strehl in DETAIL.")
        elif wd > 1.05:
            print("  -> strehl trails on the scene term in DETAIL tiles TOO.  "
                  "Consistent with (a), a real")
            print("     resolution deficit -- but DETAIL-tile half-differences "
                  "are inflated by residual")
            print("     misregistration, worst on strehl, so this CANNOT "
                  "separate (a) from misregistration.")
        else:
            print("  -> strehl holds the highest scene term in both classes; "
                  "the blur objection does not arise.")
    d = os.path.join(ROOT, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "scenetile.json"), "w", encoding="utf-8") as fh:
        json.dump({"flat": res["FLAT"], "detail": res["DETAIL"]}, fh, indent=2,
                  default=float)
    print(f"  written {os.path.join(d, 'scenetile.json')}")


def main():
    keys = [a for a in sys.argv[1:] if a in SUBJECTS]
    if not keys:
        raise SystemExit(__doc__)
    for k in keys:
        run(k)
        print()


if __name__ == "__main__":
    main()
