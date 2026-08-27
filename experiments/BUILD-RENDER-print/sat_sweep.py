"""Sweep `SATURATED_CHROMA`, the threshold that gates the five gamut verdicts.

ORCH's standing pre-flight question for any instrument:

    What property of the input decides whether this check can see anything,
    and have I varied it?

For the corrected gamut table that property is `SATURATED_CHROMA`. It decides
which pixels are allowed to count as carrying colour, so it decides both the
per-subject `sat_severe_pct` and the "10 of 26 have no saturated content at
all" partition. I set it to 20.0 by choosing a value that behaved sensibly on
two commissioning arms and never swept it -- exactly the failure the block
sweep in `modulation.py` exposed, where a hardcoded threshold turned out to
equal the ceiling at one end of the grid and the check could not fire at all.

The five subjects this gates were reported to the owner as not sendable to a
lab, so a threshold artefact here has a real cost.

WHAT WOULD FALSIFY THE CHOICE
-----------------------------
Not "the numbers move" -- they must move, the threshold selects a population.
The choice is unsound if the ORDER of subjects reshuffles, because the verdicts
are a ranking: the worst five were named. A threshold that merely rescales
everything leaves the ranking intact and the verdicts stand. A threshold that
reorders means "the worst five" is an artefact of 20.0.

So the reported quantity is Spearman rank correlation against the shipped
threshold, plus the membership of the top five at each grid point. Those are
magnitudes rather than booleans, per the standing finding that a boolean pass
carries no scale and so cannot self-check.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parent))

from printqa import SRGB_ICM, SWOP_ICM, gamut_stats  # noqa: E402

GRID = (5.0, 10.0, 15.0, 20.0, 30.0, 40.0)
SHIPPED = 20.0


def rank(values: dict[str, float]) -> dict[str, int]:
    """Dense ranking, worst first. NaN sorts last."""
    ordered = sorted(values, key=lambda k: (-values[k] if not np.isnan(values[k]) else -1e9))
    return {k: i for i, k in enumerate(ordered)}


def spearman(a: dict[str, int], b: dict[str, int]) -> float:
    keys = sorted(set(a) & set(b))
    ra = np.array([a[k] for k in keys], dtype=float)
    rb = np.array([b[k] for k in keys], dtype=float)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / denom) if denom > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("masters", type=Path, help="directory of *--SHIP-V2.tiff masters")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    paths = sorted(args.masters.glob("*--SHIP-V2.tiff"))
    if args.limit:
        paths = paths[: args.limit]
    if not paths:
        raise SystemExit(f"no masters under {args.masters}")

    swop = ImageCms.getOpenProfile(str(SWOP_ICM))
    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))

    per_thr: dict[float, dict[str, float]] = {t: {} for t in GRID}
    per_sat: dict[float, dict[str, float]] = {t: {} for t in GRID}
    print(f"  scoring {len(paths)} masters across {len(GRID)} thresholds, one ICC pass each\n")
    for p in paths:
        arr = tifffile.imread(str(p))
        if arr.dtype != np.uint16:
            raise SystemExit(f"{p.name}: dtype {arr.dtype}, expected uint16")
        st = gamut_stats(arr, swop, srgb, sat_grid=GRID)
        name = p.name.replace("--SHIP-V2.tiff", "")
        for t in GRID:
            per_thr[t][name] = st["sat_grid"][t]["sat_severe_pct"]
            per_sat[t][name] = st["sat_grid"][t]["sat_pct"]

    ref_rank = rank(per_thr[SHIPPED])
    ref_top5 = [k for k, v in sorted(ref_rank.items(), key=lambda kv: kv[1])][:5]

    # Two DIFFERENT populations, kept in separate columns because collapsing
    # them is the error this table exists to avoid: "has no saturated colour at
    # all" and "has saturated colour the press held" both produce a severe
    # figure of 0.00 and mean opposite things.
    # `gamut_corrected.py:151` buckets a subject as "the question does not
    # arise" when sat_pct < 0.5, so 0.5 is a SECOND threshold I chose and never
    # swept. It is reported here beside the exact-zero count because the two
    # differ sharply, and because I described the bucket to ORCH as "no
    # saturated content AT ALL" -- which is what the exact-zero column measures
    # and is not what the code does.
    print(
        f"  {'C*>=':>6} {'sat==0':>8} {'sat<0.5%':>9} {'zero sev':>9} "
        f"{'med sev%':>9} {'rho vs 20':>10}  top-5 kept"
    )
    print("  " + "-" * 76)
    for t in GRID:
        vals = per_thr[t]
        no_sat = sum(1 for v in per_sat[t].values() if v == 0.0)
        under = sum(1 for v in per_sat[t].values() if v < 0.5)
        zero_sev = sum(1 for v in vals.values() if v == 0.0)
        med = float(np.median(list(vals.values())))
        rho = spearman(ref_rank, rank(vals))
        top5 = [k for k, v in sorted(rank(vals).items(), key=lambda kv: kv[1])][:5]
        kept = len(set(top5) & set(ref_top5))
        mark = "  <- shipped" if t == SHIPPED else ""
        print(
            f"  {t:6.0f} {no_sat:4d}/{len(vals):<3} {under:5d}/{len(vals):<3} "
            f"{zero_sev:6d}/{len(vals):<3} {med:9.2f} {rho:10.3f}  {kept}/5{mark}"
        )

    print("\n  top five at the shipped threshold, worst first:")
    for i, k in enumerate(ref_top5, 1):
        row = " ".join(f"{per_thr[t][k]:7.2f}" for t in GRID)
        print(f"    {i}. {k:<34} {row}")
    print(f"       {'':<37}" + " ".join(f"{t:7.0f}" for t in GRID) + "   <- C*>=")
    return 0


if __name__ == "__main__":
    sys.exit(main())
