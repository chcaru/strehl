"""Correcting the gamut table: how much of it was near-neutrals, not colour?

`printqa.py` reported per-subject `severe%` -- pixels losing more than 5 Lab
units of chroma to the press. LOOKING at `flowers-cpl` showed that number can
be dominated by featureless background bokeh where MASTER and PRINTABLE are
indistinguishable by eye. The loss is real; its significance is not, because
it is taken off a near-neutral.

This re-scores every master with the loss conditioned on there being
saturation to lose, and prints the old and new columns side by side so the
size of the over-report is visible rather than quietly corrected.

`sat%` is printed alongside deliberately: a low `satSevere%` means "the press
held the colour" only if `sat%` says there was colour there. Where `sat%` is
near zero the subject simply has no saturated content and the print question
does not arise -- which is a different fact from passing, and it is reported
as one.
"""

from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
from PIL import ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parent))

from printqa import (  # noqa: E402
    SATURATED_CHROMA,
    SRGB_ICM,
    SWOP_ICM,
    gamut_stats,
    read_master,
)


def patch(rgb: tuple[int, int, int]) -> np.ndarray:
    """A uniform 16-bit field of one colour, as a master would be read."""
    a = np.zeros((256, 256, 3), dtype=np.uint16)
    for i, v in enumerate(rgb):
        a[..., i] = v * 257
    return a


def commission(swop, srgb) -> bool:
    """The new statistic must DISCRIMINATE, not merely exist.

    Two fields are pushed through the identical path:

    * TINTED NEUTRAL -- a barely-coloured grey. It may lose chroma, and the old
      unconditioned statistic is allowed to fire on it. The new one must not,
      and `sat%` must report ~0 so the zero is legible as "nothing to lose".
    * SATURATED      -- a strong colour well outside SWOP. Both statistics must
      fire, or the new one is simply blind and would exonerate everything.

    If both arms score the same on `satSevere%`, the conditioning has achieved
    nothing and the corrected table is not worth printing.
    """
    print("=" * 78)
    print(f"COMMISSIONING saturation-conditioned loss (threshold C* >= {SATURATED_CHROMA:g})")
    print("=" * 78)
    arms = {
        "tinted neutral": patch((140, 146, 152)),
        "saturated green": patch((10, 210, 40)),
    }
    got = {}
    for name, img in arms.items():
        s = gamut_stats(img, swop, srgb)
        got[name] = s
        print(
            f"  {name:<18} meanC {s['mean_chroma']:6.2f}   "
            f"severe% {s['severe_pct']:7.2f}   sat% {s['sat_pct']:7.2f}   "
            f"satSevere% {s['sat_severe_pct']:7.2f}"
        )
    ok = True
    tn, sat = got["tinted neutral"], got["saturated green"]
    if tn["sat_severe_pct"] > 0.01:
        print(f"  FAIL  the tinted neutral scored {tn['sat_severe_pct']:.2f}% saturated loss;")
        print("        the conditioning is not excluding near-neutrals.")
        ok = False
    else:
        print("  PASS  tinted neutral scores 0.00% saturated loss, and sat% "
              f"{tn['sat_pct']:.2f} says why.")
    if not sat["sat_severe_pct"] > 50.0:
        print(f"  FAIL  the saturated field scored only {sat['sat_severe_pct']:.2f}%;")
        print("        the new statistic is blind and would exonerate everything.")
        ok = False
    else:
        print(f"  PASS  saturated field scores {sat['sat_severe_pct']:.2f}%, so the "
              "statistic still fires")
        print("        where real colour is genuinely lost.")
    print("=" * 78)
    print("COMMISSIONED" if ok else "NOT COMMISSIONED -- table below is void")
    print("=" * 78)
    return ok


def main() -> int:
    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    swop = ImageCms.getOpenProfile(str(SWOP_ICM))
    if not commission(swop, srgb):
        return 1

    rows = []
    for p in sorted(glob.glob(r"C:\dev\strehl-out\SHIP-V2-ICC\*.tiff")):
        name = os.path.basename(p).replace("--SHIP-V2-ICC.tiff", "")
        s = gamut_stats(read_master(Path(p)), swop, srgb)
        rows.append((name, s))

    rows.sort(key=lambda r: -r[1]["sat_severe_pct"])
    print(f"\n{'subject':<38}{'meanC':>7}{'sat%':>8}{'severe%':>9}"
          f"{'satSevere%':>12}{'relLoss90':>11}  reading")
    print("-" * 100)
    no_colour = 0
    for name, s in rows:
        if s["sat_pct"] < 0.5:
            reading = "no saturated content -- question does not arise"
            no_colour += 1
        elif s["sat_severe_pct"] > 10.0:
            reading = "REAL colour loss"
        elif s["sat_severe_pct"] > 2.0:
            reading = "some colour loss"
        else:
            reading = "press holds its colour"
        rel = s["sat_rel_loss_p90"]
        rel_s = "     n/a" if np.isnan(rel) else f"{100 * rel:10.1f}%"
        print(
            f"{name:<38}{s['mean_chroma']:7.2f}{s['sat_pct']:8.2f}"
            f"{s['severe_pct']:9.2f}{s['sat_severe_pct']:12.2f}{rel_s}  {reading}"
        )
    print("-" * 100)
    over = [(n, s["severe_pct"] - s["sat_severe_pct"]) for n, s in rows]
    over.sort(key=lambda r: -r[1])
    print(f"subjects with no saturated content: {no_colour} of {len(rows)}")
    print("\nlargest over-reports by the unconditioned statistic (severe% - satSevere%):")
    for n, d in over[:6]:
        print(f"    {n:<38} {d:6.2f} points of the old number was near-neutral drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
