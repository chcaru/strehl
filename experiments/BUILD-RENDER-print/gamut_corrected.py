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

import argparse
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
from softproof import commission_comparison  # noqa: E402


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
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--profile",
        type=Path,
        nargs="+",
        default=[SWOP_ICM],
        help="one or more output profiles; the FIRST is the reference column. "
        "Defaults to RSWOP so today's numbers do not change silently.",
    )
    ap.add_argument("--root", type=Path, default=Path(r"C:\dev\strehl-out\SHIP-V2-ICC"))
    ap.add_argument("--limit", type=int, default=0, help="first N subjects only")
    args = ap.parse_args()

    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    profiles = []
    for p in args.profile:
        if not p.exists():
            print(f"  PROFILE NOT FOUND: {p}")
            return 1
        profiles.append((p.stem, ImageCms.getOpenProfile(str(p))))

    if not commission(profiles[0][1], srgb):
        return 1
    if not commission_comparison(profiles, srgb):
        return 1

    rows = []
    paths = sorted(glob.glob(str(args.root / "*.tiff")))
    if args.limit:
        paths = paths[: args.limit]
    for p in paths:
        name = os.path.basename(p).replace("--SHIP-V2-ICC.tiff", "")
        rgb16 = read_master(Path(p))
        per = {pn: gamut_stats(rgb16, prof, srgb) for pn, prof in profiles}
        rows.append((name, per))

    ref = profiles[0][0]
    rows.sort(key=lambda r: -r[1][ref]["sat_severe_pct"])

    if len(profiles) == 1:
        print(f"\n{'subject':<38}{'meanC':>7}{'sat%':>8}{'severe%':>9}"
              f"{'satSevere%':>12}{'relLoss90':>11}  reading")
        print("-" * 100)
        no_colour = 0
        for name, per in rows:
            s = per[ref]
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
        print(f"subjects with no saturated content: {no_colour} of {len(rows)}")
        over = [(n, per[ref]["severe_pct"] - per[ref]["sat_severe_pct"]) for n, per in rows]
        over.sort(key=lambda r: -r[1])
        print("\nlargest over-reports by the unconditioned statistic (severe% - satSevere%):")
        for n, d in over[:6]:
            print(f"    {n:<38} {d:6.2f} points of the old number was near-neutral drift")
        return 0

    # Comparison mode. The delta column is the point: it decomposes a verdict
    # into how much was the image and how much was the measuring stick.
    others = [pn for pn, _ in profiles[1:]]
    head = f"\n{'subject':<38}{'sat%':>7}{ref[:11]:>12}"
    for o in others:
        head += f"{o[:11]:>12}{'delta':>9}"
    print(head + "   reading")
    print("-" * (52 + 21 * len(others) + 24))
    rescued, unchanged, still_bad = 0, 0, 0
    for name, per in rows:
        s = per[ref]
        line = f"{name:<38}{s['sat_pct']:7.2f}{s['sat_severe_pct']:12.2f}"
        verdict = "no saturated content" if s["sat_pct"] < 0.5 else ""
        for o in others:
            d = per[o]["sat_severe_pct"] - s["sat_severe_pct"]
            line += f"{per[o]['sat_severe_pct']:12.2f}{d:+9.2f}"
        if s["sat_pct"] >= 0.5:
            best = min(per[o]["sat_severe_pct"] for o in others)
            if s["sat_severe_pct"] > 10.0 and best <= 10.0:
                verdict, rescued = "RESCUED by the wider profile", rescued + 1
            elif s["sat_severe_pct"] > 10.0:
                verdict, still_bad = "loses colour on BOTH", still_bad + 1
            else:
                verdict, unchanged = "held on both", unchanged + 1
        print(line + f"   {verdict}")
    print("-" * (52 + 21 * len(others) + 24))
    n_nocolour = sum(1 for _, per in rows if per[ref]["sat_pct"] < 0.5)
    print(
        f"rescued {rescued}   loses on both {still_bad}   held on both {unchanged}   "
        f"no saturated content {n_nocolour}   total {len(rows)}"
    )
    print(
        "\nRESCUED means the verdict was the PROFILE, not the image: the same\n"
        "pixels are printable on the wider gamut. 'loses colour on BOTH' is the\n"
        "subset a wider paper does not save."
    )

    # A profile that CONTAINS the source gamut cannot fail this test, and its
    # clean sweep of zeros looks exactly like a paper that holds every colour.
    # The masters are sRGB files; sRGB is a strict subset of DCI-P3 and of most
    # wide-gamut RGB spaces, so a zero there is arithmetic, not evidence.
    for o in others:
        worst = max(per[o]["sat_severe_pct"] for _, per in rows)
        if worst == 0.0:
            print(
                f"\n!! READ THIS BEFORE BELIEVING {o}: it lost NO saturated colour on\n"
                f"   any of the {len(rows)} subjects. The masters are sRGB-encoded, so if\n"
                f"   {o}'s gamut contains sRGB then a zero is guaranteed by\n"
                "   construction and this comparison CANNOT FAIL against it. Treat it\n"
                "   as a CEILING -- it bounds how much of the verdict is attributable\n"
                "   to the reference profile, and it does NOT establish that any real\n"
                "   paper holds these colours. A fine-art inkjet gamut is not a\n"
                "   superset of sRGB: it is wider in some greens and narrower in some\n"
                "   saturated blues. The true answer lies between the two columns."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
