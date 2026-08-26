"""Is the residual "motion" landing on real structure, or on empty regions?

Viewing the top-ranked motion sites at 1:1 (Part 3) produced a consistent
impression: the highest-scoring sites are blown white, dark noise, or
featureless soft grey.  An impression is not a measurement, so this measures
it.

For every hot cluster the verdict nominates, crop the delivered master at that
site and compute local structure (RMS of the gradient magnitude, in the
tone-mapped master -- this is a WITHIN-image comparison, never a between-image
one, so it does not cross a tone curve).  Compare it against the distribution
of the same statistic over a dense grid of sites in the SAME master, and report
the percentile.

The two readings this can produce are opposite and both are informative:

  * hot sites at LOW percentiles -> the residual is concentrated where there
    is nothing to correlate, i.e. it is estimator noise in low-information
    regions, and a ghost there would be invisible anyway.

  * hot sites at HIGH percentiles -> the residual is on real detail, which is
    where a ghost would actually show, and the visual check becomes decisive.

CONTROL: the same statistic is computed for each master's CONTROL site (chosen
by crops.py for texture, not by motion) and for the grid, so the three
distributions can be compared.  If hot and grid percentiles were identical the
test would have no discrimination and that would be visible here.

USAGE
    python experiments/BUILD-GHOST/hotsites.py
"""
from __future__ import annotations

import json
import os

import numpy as np
import tifffile

DATA = os.path.join(r"C:\dev\strehl-out\BUILD-GHOST", "data")
SHIP = r"C:\dev\strehl-out\SHIP-V1"
CROP = 512
GRID = 24          # grid sites per axis for the reference distribution


def structure(patch: np.ndarray) -> float:
    """RMS gradient magnitude of the luminance of a uint16 patch."""
    y = patch.astype(np.float32).mean(axis=2)
    gy, gx = np.gradient(y)
    return float(np.sqrt(np.mean(gy * gy + gx * gx)))


def main() -> int:
    verdict = json.load(open(os.path.join(DATA, "verdict.json")))
    rows = [r for r in verdict["rows"] if r.get("n_hot_clusters")]
    print("=" * 100)
    print("PART 3 CONTROL  does the residual land on structure, or on empty regions?")
    print("=" * 100)
    print("percentile of local structure (RMS gradient) at each hot site,")
    print("against a %dx%d grid of sites in the SAME master\n" % (GRID, GRID))
    print(f"{'subject':38s} {'hot':>4s} {'median pct':>11s} {'min':>6s} {'max':>6s}  sites")

    all_pct, n_sub = [], 0
    out = {}
    for r in rows:
        name = r["subject"]
        p = os.path.join(SHIP, name + ".tiff")
        if not os.path.exists(p):
            continue
        a = tifffile.imread(p)
        assert a.dtype == np.uint16, f"{name}: expected uint16, got {a.dtype}"
        h, w = a.shape[:2]

        # reference distribution over the same master
        ys = np.linspace(0, h - CROP, GRID).astype(int)
        xs = np.linspace(0, w - CROP, GRID).astype(int)
        ref = np.array([structure(a[y:y + CROP, x:x + CROP]) for y in ys for x in xs])

        pcts = []
        for c in r["hot"]:
            cy, cx = c["peak_plane_yx"]
            y = int(np.clip(int(cy) * 2 - CROP // 2, 0, h - CROP))
            x = int(np.clip(int(cx) * 2 - CROP // 2, 0, w - CROP))
            s = structure(a[y:y + CROP, x:x + CROP])
            pcts.append(float((ref < s).mean() * 100.0))
        if not pcts:
            continue
        n_sub += 1
        all_pct.extend(pcts)
        out[name] = {"pcts": pcts, "n_hot": r["n_hot_clusters"]}
        print(f"{name:38s} {len(pcts):4d} {np.median(pcts):11.1f} "
              f"{min(pcts):6.1f} {max(pcts):6.1f}  "
              + " ".join(f"{v:.0f}" for v in pcts))
        del a

    all_pct = np.array(all_pct)
    print(f"\nsubjects with hot sites {n_sub}   sites examined {len(all_pct)}")
    print(f"median percentile across all hot sites  {np.median(all_pct):.1f}")
    print(f"sites below the 50th percentile         "
          f"{int((all_pct < 50).sum())}/{len(all_pct)}")
    print(f"sites below the 25th percentile         "
          f"{int((all_pct < 25).sum())}/{len(all_pct)}")
    print(f"sites above the 75th percentile         "
          f"{int((all_pct > 75).sum())}/{len(all_pct)}")
    print(f"  (partition: <25 {int((all_pct < 25).sum())}  "
          f"25-50 {int(((all_pct >= 25) & (all_pct < 50)).sum())}  "
          f"50-75 {int(((all_pct >= 50) & (all_pct <= 75)).sum())}  "
          f">75 {int((all_pct > 75).sum())}  "
          f"sums to {len(all_pct)})")
    print("\nIf the residual were tracking real moving detail these would sit high.")

    json.dump({"grid": GRID, "crop": CROP, "n_sites": len(all_pct),
               "median_pct": float(np.median(all_pct)),
               "per_subject": out},
              open(os.path.join(DATA, "hotsites.json"), "w"), indent=2, default=float)
    print(f"\nwrote {os.path.join(DATA, 'hotsites.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
