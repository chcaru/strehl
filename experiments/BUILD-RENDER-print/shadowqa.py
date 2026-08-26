"""Does the shadow detail in these masters survive a press?

`printqa.py` answers "what colour cannot be reached". This answers the other
half of the print question and the one the corpus's darkest subjects actually
turn on: **does the tonal SEPARATION inside the shadows survive the round
trip**, or does it collapse into one ink.

The distinction matters because a subject can be perfectly in gamut and still
print as a black rectangle. `coffee-bubbles` has a median L* of 2.61 with
89.64% of its pixels below L* 5; on an emissive display that reads as a rich
dark field with visible surface structure, which is exactly what it looked
like when it was rendered.

WHY THIS IS NOT A FOREGONE CONCLUSION, AND WHY IT IS MEASURED RATHER THAN
ASSERTED: the transform runs with **black-point compensation**, which maps the
source black to the destination black and therefore *preserves* relative
shadow spacing by construction. A good lab uses BPC. So the honest prior is
that BPC rescues these shadows, and the instrument has to be able to say so.
Both controls below are built to allow that answer.

The measurement is deliberately NOT "how much did L* move" -- a uniform shift
is a rendering choice, not a loss. It is how much of the *spread between*
shadow pixels survives, plus how many distinct levels are left to carry it.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from printqa import (  # noqa: E402
    SRGB_ICM,
    SWOP_ICM,
    printable_rgb8,
    read_master,
    rgb_to_lab,
)

from PIL import ImageCms  # noqa: E402

SHADOW_L = 10.0
"""Where "shadow" ends, in L*.

Chosen to sit above the corpus's dark subjects rather than inside them:
`coffee-bubbles` has p90 = 5.14 and `foam` p50 = 9.55, so a threshold of 10
captures essentially all of the first and half of the second. A threshold
tight enough to sit inside the distribution would measure the threshold rather
than the subject.
"""

MIN_SHADOW_PIXELS = 10_000
"""Below this the spread statistic is reported as NOT MEASURED rather than
computed. A percentile spread over a handful of pixels is noise wearing a
number, and this project has shipped enough of those."""


def lab_of_rgb8(rgb8: np.ndarray) -> np.ndarray:
    return rgb_to_lab(rgb8.astype(np.float64) / 255.0)


def spread(values: np.ndarray) -> float:
    """p90 - p10 of L*, the separation a viewer would read as shadow detail."""
    lo, hi = np.percentile(values, [10, 90])
    return float(hi - lo)


def levels(values: np.ndarray) -> int:
    """Distinct L* levels at 0.1 quantisation -- how many steps carry the spread."""
    return int(np.unique(np.round(values, 1)).size)


def survival(master_l: np.ndarray, print_l: np.ndarray) -> dict:
    ms, ps = spread(master_l), spread(print_l)
    return {
        "master_spread": ms,
        "print_spread": ps,
        "ratio": (ps / ms) if ms > 1e-9 else float("nan"),
        "master_levels": levels(master_l),
        "print_levels": levels(print_l),
    }


def ramp(lo_dn: int, hi_dn: int, n: int = 512) -> np.ndarray:
    """A neutral 8-bit sRGB ramp, as an image the transform will accept."""
    v = np.linspace(lo_dn, hi_dn, n).round().astype(np.uint8)
    return np.repeat(v[None, :, None], 64, axis=0).repeat(3, axis=2)


def commission(swop, srgb) -> bool:
    """Two arms that must disagree, or the statistic is not reading anything.

    * SHADOW arm  -- a ramp confined to the deep shadows. This is the arm under
      test; it is allowed to survive, and if it does that is the finding.
    * MIDTONE arm -- the same ramp width placed in the midtones, where no print
      process has trouble. This one MUST survive. If the midtone ramp also
      collapses, the instrument is measuring its own transform rather than the
      press, and every shadow number it produces is worthless.

    A third arm checks the statistic is not simply blind: a ramp deliberately
    flattened to a constant must report a spread of 0, so "survived" cannot be
    what the code says when it has failed to look.
    """
    print("=" * 78)
    print("COMMISSIONING shadow-survival")
    print("=" * 78)
    ok = True

    arms = {"shadow (0-30 DN)": ramp(0, 30), "midtone (110-140 DN)": ramp(110, 140)}
    results = {}
    for name, img in arms.items():
        m = lab_of_rgb8(img)[..., 0].ravel()
        p = lab_of_rgb8(printable_rgb8(img, swop, srgb))[..., 0].ravel()
        r = survival(m, p)
        results[name] = r
        print(
            f"  {name:<22} master spread {r['master_spread']:6.2f} L*  "
            f"-> print {r['print_spread']:6.2f} L*   ratio {r['ratio']:5.2f}   "
            f"levels {r['master_levels']:4d} -> {r['print_levels']:4d}"
        )

    mid = results["midtone (110-140 DN)"]["ratio"]
    if not (mid > 0.80):
        print(f"  FAIL  midtone ramp lost separation (ratio {mid:.2f}); the")
        print("        transform itself is compressing and no shadow number can be")
        print("        attributed to the press.")
        ok = False
    else:
        print(f"  PASS  midtone control survives (ratio {mid:.2f} > 0.80), so a")
        print("        shadow loss, if any, is attributable to the shadows.")

    flat = np.full((64, 512, 3), 12, dtype=np.uint8)
    fl = lab_of_rgb8(flat)[..., 0].ravel()
    if spread(fl) != 0.0:
        print(f"  FAIL  blindness control: a constant field reported spread {spread(fl):.3f}")
        ok = False
    else:
        print("  PASS  blindness control: a constant field reports spread 0.00,")
        print("        so the statistic is reading the image and not a constant.")

    sh = results["shadow (0-30 DN)"]["ratio"]
    print(f"\n  shadow arm ratio {sh:.2f} -- reported, NOT gated: this arm is the")
    print("  question, not the control. BPC may legitimately preserve it.")
    print("=" * 78)
    print("COMMISSIONED" if ok else "NOT COMMISSIONED -- results below are void")
    print("=" * 78)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"C:\dev\strehl-out\SHIP-V2-ICC")
    ap.add_argument("--profile", default=str(SWOP_ICM))
    args = ap.parse_args()

    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    swop = ImageCms.getOpenProfile(str(args.profile))

    if not commission(swop, srgb):
        return 1

    paths = sorted(glob.glob(os.path.join(args.dir, "*.tiff")))
    print(f"\nprofile: {Path(args.profile).name}   subjects: {len(paths)}")
    print(f"shadow = L* < {SHADOW_L:g};  spread = p90-p10 of L* among shadow pixels\n")
    print(
        f"{'subject':<38}{'%shadow':>8}{'master':>8}{'print':>8}"
        f"{'ratio':>7}{'lvls m->p':>12}  verdict"
    )
    print("-" * 96)

    measured = 0
    not_measured = 0
    crushed = []
    for p in paths:
        name = os.path.basename(p).replace("--SHIP-V2-ICC.tiff", "")
        rgb16 = read_master(Path(p))
        lab = rgb_to_lab(rgb16.astype(np.float64) / 65535.0)
        mask = lab[..., 0] < SHADOW_L
        pct = 100.0 * mask.mean()
        if mask.sum() < MIN_SHADOW_PIXELS:
            not_measured += 1
            print(f"{name:<38}{pct:7.2f}%{'':>8}{'':>8}{'':>7}{'':>12}  NOT MEASURED (<{MIN_SHADOW_PIXELS} px)")
            continue

        rgb8 = (rgb16 >> 8).astype(np.uint8)
        pr8 = printable_rgb8(rgb8, swop, srgb)
        m = lab[..., 0][mask]
        pl = lab_of_rgb8(pr8)[..., 0][mask]
        r = survival(m, pl)
        measured += 1
        verdict = "holds"
        if r["ratio"] < 0.60:
            verdict = "CRUSHED"
            crushed.append((name, pct, r["ratio"]))
        elif r["ratio"] < 0.80:
            verdict = "compressed"
        print(
            f"{name:<38}{pct:7.2f}%{r['master_spread']:8.2f}{r['print_spread']:8.2f}"
            f"{r['ratio']:7.2f}{r['master_levels']:6d}->{r['print_levels']:<5d}  {verdict}"
        )

    print("-" * 96)
    print(f"measured {measured}   NOT MEASURED {not_measured}   total {len(paths)}")
    print(f"of the measured: {len(crushed)} CRUSHED (ratio < 0.60)")
    for n, pct, r in crushed:
        print(f"    {n:<38} {pct:5.1f}% of frame in shadow, ratio {r:.2f}")
    print(
        "\nCAVEAT: SWOP is web-coated offset. A fine-art inkjet on rag paper has a\n"
        "        deeper black and holds more shadow separation than this, so treat\n"
        "        a CRUSHED verdict as a print-class warning, not a lab verdict."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
