"""How much of a source frame's measured "edge" at a site is grain, not detail?

WHY THIS EXISTS
---------------
`compare.py` reported `flowers-cpl` losing badly to its own source frames at
three background sites -- ratio 0.37 to 0.52, "the merge is 3 px blurrier".
The source arm at those sites carries 45.2 DN of pixel noise against the
merge's 6.7 DN, because a merge averages many frames and a single frame does
not.  An edge metric run on grain returns a number, and that number is not an
edge.

The crop cannot settle it.  At a mean level of 8444 DN a 91 DN/px modulation is
about 1%, which after the display transfer is under one 8-bit level: both arms
look blank whether or not one of them holds real structure.  "Look at the
picture" is the right instinct and the wrong instrument HERE, and mistaking the
two is how a confident wrong answer gets published.

THE DISCRIMINATOR
-----------------
Adjacent frames in a focus bracket share their SUBJECT but not their GRAIN.
Grain is independent between exposures; structure is not.  So average k
neighbouring frames at the same site and re-measure:

    grain-dominated  -> edge falls as 1/sqrt(k)   (k=3 -> x0.577)
    structure-domin. -> edge is preserved         (k=3 -> x1.0)

The measured falloff places the site on that axis and yields a grain fraction
directly.  This is a measurement, not a rendering, so it is immune to the
display problem that defeated the crop.

Neighbours are taken with a small stride so they are genuinely different
exposures, and close enough that focus has not materially changed -- which the
script checks rather than assumes, by requiring the neighbours' own edge
slopes to agree within a tolerance before their mean is trusted.

CAVEAT ON SCOPE
---------------
This runs on the raw CFA green plane, NOT on the merged output, so it speaks
only about what the SOURCE frames contain.  That is exactly the question it is
asked: is the source arm's apparent advantage real signal or grain.  It makes
no claim about the merge.

Usage:
    python grainprobe.py <subject> --frame K --at LABEL:X,Y [--at ...]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
import sitescan as SS  # noqa: E402

STRIDE = 2          # frames apart: different exposure, ~same focus
K = 5               # neighbours averaged


def commission() -> None:
    """A null and a powered plant, on synthetic data with known composition.

    Pure grain must be recovered as ~100% grain and pure structure as ~0%,
    otherwise the grain fraction this script reports means nothing.
    """
    rng = np.random.default_rng(4242)
    n, lvl, sigma = 256, 8000.0, 45.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    struct = lvl * (1.0 + 0.02 * np.sin(xx * 0.9) * np.cos(yy * 0.7))

    def falloff(frames: list[np.ndarray]) -> float:
        singles = [tri.edge_slope(f) for f in frames]
        return tri.edge_slope(np.mean(frames, axis=0)) / float(np.mean(singles))

    pure_grain = [np.full((n, n), lvl) + rng.normal(0, sigma, (n, n))
                  for _ in range(K)]
    pure_struct = [struct.copy() for _ in range(K)]
    f_grain, f_struct = falloff(pure_grain), falloff(pure_struct)
    expect = 1.0 / np.sqrt(K)
    assert abs(f_grain - expect) < 0.06, (
        f"commission: pure grain fell to x{f_grain:.3f}, expected "
        f"x{expect:.3f} (1/sqrt({K})); the discriminator is not calibrated")
    assert f_struct > 0.97, (
        f"commission: pure structure fell to x{f_struct:.3f}; averaging is "
        "destroying signal, so the test cannot separate the two cases")
    # A powered mixture: half the edge power from each. Must land in between.
    mixed = [struct + rng.normal(0, sigma, (n, n)) for _ in range(K)]
    f_mix = falloff(mixed)
    assert expect < f_mix < 1.0, \
        f"commission: 50/50 mixture landed at x{f_mix:.3f}, outside the range"
    print(f"  commission  pure grain x{f_grain:.3f} (expect x{expect:.3f}); "
          f"pure structure x{f_struct:.3f}; mixture x{f_mix:.3f}  OK")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--frame", type=int, required=True)
    ap.add_argument("--at", action="append", required=True,
                    metavar="LABEL:X,Y")
    ap.add_argument("--half", type=int, default=119)
    ap.add_argument("--min-ncc", type=float, default=0.45)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    print(f"grainprobe {args.subject} frame {args.frame} "
          f"(neighbours +-{STRIDE}, k={K})")
    commission()

    d = os.path.join(tri.RAW, args.subject)
    files = sorted({os.path.normcase(f): f for f in os.listdir(d)
                    if f.lower().endswith(".arw")}.values())
    n = len(files)
    assert 0 <= args.frame < n, f"frame {args.frame} outside 0..{n-1}"

    my = tri.luma(tri.load16(os.path.join(tri.LIN, args.subject + ".tiff")))

    # Neighbour indices, clamped inside the bracket.
    off = [(i - K // 2) * STRIDE for i in range(K)]
    idx = [int(np.clip(args.frame + o, 0, n - 1)) for o in off]
    assert len(set(idx)) == K, \
        f"neighbours collapsed to {sorted(set(idx))}; too near a bracket end"

    planes = [SS.green_plane(os.path.join(d, files[k])) for k in idx]
    ref = planes[K // 2]

    res = {"subject": args.subject, "frame": args.frame, "neighbours": idx,
           "stride": STRIDE, "k": K, "half_px_rawG": args.half,
           "decode": "rawpy CFA green, black-subtracted, no demosaic/WB/matrix",
           "method": "edge_slope of the mean of k neighbours vs mean of their "
                     "individual edge_slopes; grain averages down as 1/sqrt(k), "
                     "structure does not",
           "sites": {}}

    h_ = args.half
    for spec in args.at:
        label, xy = spec.split(":", 1)
        x, y = (int(v) for v in xy.split(","))
        loc = SS.locate(my, ref, x, y, 64, SS.SEARCH_G)
        gx, gy = loc["gx"], loc["gy"]
        ncc, scale = loc["ncc"], loc["scale"]
        assert ncc >= args.min_ncc, (
            f"{label}: site located at ncc={ncc:.4f}, below the {args.min_ncc} "
            "gate; the window is not the same place in both arms")

        tiles = [p[gy - h_:gy + h_, gx - h_:gx + h_].astype(np.float64)
                 for p in planes]
        singles = [tri.edge_slope(t) for t in tiles]
        # Focus must not have moved across the neighbourhood, or the average is
        # blurring the subject rather than only the grain. Check, do not assume.
        spread = float(max(singles) / max(min(singles), 1e-9))
        avg = tri.edge_slope(np.mean(tiles, axis=0))
        mean_single = float(np.mean(singles))
        fall = avg / mean_single if mean_single > 0 else float("nan")

        # Decompose: measured^2 = structure^2 + grain^2, and averaging k frames
        # leaves structure^2 + grain^2/k.
        #   fall^2 = (s^2 + g^2/k) / (s^2 + g^2)
        # -> grain fraction of edge POWER:
        gp = (1.0 - fall * fall) / (1.0 - 1.0 / K)
        gp = float(np.clip(gp, 0.0, 1.0))
        sig = float(mean_single * np.sqrt(max(1.0 - gp, 0.0)))

        ok = spread < 1.25
        res["sites"][label] = {
            "merge_xy": [x, y], "green_xy": [gx, gy],
            "ncc": round(ncc, 4), "scale": round(scale, 4),
            "edge_single_dnpx": round(mean_single, 2),
            "edge_avg_dnpx": round(avg, 2),
            "falloff": round(fall, 4),
            "falloff_if_pure_grain": round(1.0 / np.sqrt(K), 4),
            "grain_power_fraction": round(gp, 4),
            "edge_structure_dnpx": round(sig, 2),
            "neighbour_spread": round(spread, 3),
            "focus_stable_across_neighbours": ok,
        }
        verdict = ("GRAIN -- little or no real detail in the source here"
                   if gp > 0.70 else
                   "STRUCTURE -- the source genuinely holds detail here"
                   if gp < 0.30 else "MIXED")
        print(f"  {label:>12s} ncc={ncc:.3f}  single={mean_single:7.1f} "
              f"avg={avg:7.1f} DN/px  falloff x{fall:.3f} "
              f"(pure grain x{1/np.sqrt(K):.3f})\n"
              f"               grain={100*gp:5.1f}% of edge power -> real "
              f"structure {sig:6.1f} DN/px   {verdict}"
              + ("" if ok else f"\n               WARNING: focus moved across "
                               f"neighbours (spread x{spread:.2f}); "
                               f"falloff is not grain-only"))

    out = os.path.join(tri.OUT, "grainprobe",
                       args.subject + (args.tag or "") + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
