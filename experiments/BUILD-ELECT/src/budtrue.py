"""Section 21 measured 336 px from ORCH's feature. Re-run at the true address.

Section 21.6 carried this as an open item and got its size wrong:

    "I did not reproduce ORCH's +22 exactly (I read ~+17 in 8-bit at their
     stated address), most likely a small address offset. Not chased."

It was not small and the address was not theirs. The assumed origin (2864,864)
came from BUILD-TRIAGE's ORCH_DETAIL site table, and the asset section 21
actually measured against is a DIFFERENT file: the ORCH-DETAIL png and the
VIEW-SHIP asset have different hashes and different sizes (874643 vs 698373
bytes). Two artifacts with the same subject name and the same 800x800 shape.

The producer settles it. build_view.pick_crop steps by CROP=800, so every origin
it can emit is a multiple of 800 and (2864,864) is not one. The gallery index
records the origin per card:

    flower-bud-alone-cpl-- : (3200, 800)

Offset from what section 21 used: (+336, -64).

ORCH's peak at region (row 40, x 114) is asset (60, 464), so the true absolute
address is (3200+464, 800+60) = (3664, 860), and their flat control row 120 is
absolute y = 800+140 = 940.

WHAT THIS COSTS SECTION 21
  Still good, because they were not measured through the address:
    - the reproduction census (frame-wide, 0 of 99,010,560 samples)
    - the clipping census (measured on ORCH's asset region directly)
  Must be re-measured, because they were:
    - the default arm's overshoot, the lateral-CA refutation, the n=1 null,
      the edge-sharpness comparison, and every margin in section 22.2.

  Section 21's arm-to-arm comparisons are internally valid -- one address, one
  statistic, all arms -- so they establish that SOMETHING at (3328,924) behaves
  that way. They do not establish it of ORCH's rim, which is the claim section
  21 made.

ADDRESS VERIFICATION, BEFORE ANY RE-MEASUREMENT
  ORCH published the pixel: "At the peak the pixel is R=159 G=137 B=128", and a
  transect whose green runs 145 143 142 141 140 137 137 139 144 155. That is a
  positive control on the address itself, and it is theirs rather than mine. If
  the asset at (60,464) does not read 159/137/128, the mapping is still wrong
  and nothing below should be believed. This script refuses to continue.
"""
import os
import numpy as np
import tifffile
from PIL import Image

from budfringe7 import esf, over_of, load, GRID

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
SHIP = r"C:\dev\strehl-out\SHIP-V2"
ASSET = (r"C:\dev\strehl-out\VIEW-SHIP\assets"
         r"\flower-bud-alone-cpl--SHIP-V2--1to1.png")

ORIGIN = (3200, 800)
OLD = (3328, 924, 1004)
NEW = (ORIGIN[0] + 464, ORIGIN[1] + 60, ORIGIN[1] + 140)
ORCH_PIXEL = (159, 137, 128)
ORCH_GREEN = [145, 143, 142, 141, 140, 137, 137, 139, 144, 155]

ARMS = [
    ("ORCH master  g4.5 sRGB",
     os.path.join(SHIP, "flower-bud-alone-cpl--SHIP-V2.tiff"), True),
    ("g2.0 LINEAR (the default)", os.path.join(OUT, "fb-noflags.tiff"), False),
    ("g2.0 LINEAR --fix-ca off", os.path.join(OUT, "fb-caoff.tiff"), False),
    ("n=1 pyramid (NO election)", os.path.join(OUT, "one-fb-pyramid.tiff"), False),
]


def rise_1090(p):
    lo, hi = float(p.min()), float(p.max())
    if hi - lo < 1.0:
        return float("nan")
    t10, t90 = lo + 0.1 * (hi - lo), lo + 0.9 * (hi - lo)
    idx = np.where((p >= t10) & (p <= t90))[0]
    return float(idx.max() - idx.min()) if idx.size else float("nan")


def main():
    print("=" * 78)
    print("TRUE ADDRESS -- section 21 was 336 px away from ORCH's rim")
    print("=" * 78)
    print(f"  section 21 used : ABS ({OLD[0]},{OLD[1]}), control row {OLD[2]}")
    print(f"  gallery origin  : {ORIGIN}  (build_view steps by 800)")
    print(f"  true address    : ABS ({NEW[0]},{NEW[1]}), control row {NEW[2]}")
    print(f"  offset          : ({NEW[0]-OLD[0]:+d}, {NEW[1]-OLD[1]:+d})")

    print("\n  [0] ADDRESS CONTROL -- ORCH's own published pixel")
    with Image.open(ASSET) as im:
        av = np.asarray(im.convert("RGB")).astype(np.int32)
    got = tuple(int(v) for v in av[60, 464])
    print(f"    asset(60,464) reads R={got[0]} G={got[1]} B={got[2]}")
    print(f"    ORCH published    R={ORCH_PIXEL[0]} G={ORCH_PIXEL[1]} "
          f"B={ORCH_PIXEL[2]}")
    gline = [int(v) for v in av[60, 458:468, 1]]
    print(f"    green 458..467 : {gline}")
    print(f"    ORCH's transect: {ORCH_GREEN}")
    if got != ORCH_PIXEL:
        print("\n    ADDRESS CONTROL FAILED. The mapping is still wrong and")
        print("    nothing below would mean anything. Refusing to measure.")
        return 1
    print("    MATCH. The address is ORCH's, verified on ORCH's numbers.")

    print("\n  [1] the take-7 sweep, re-run at the true address")
    print("      OVER at the true address, with the section 21 value beside it")
    for name, path, srgb in ARMS:
        if not os.path.exists(path):
            print(f"\n    {name}: MISSING -- not a pass")
            continue
        a = load(path)
        u = "8bit" if srgb else "DN"
        print(f"\n    {name}   [{u}]")
        print(f"      {'N':>4} {'rows':>5} {'OVER(true)':>11} {'CTL(true)':>10} "
              f"{'OVER(sec21)':>12}")
        for n in GRID:
            ov = over_of(esf(a, NEW[1], NEW[0], srgb, True, n))
            ct = over_of(esf(a, NEW[2], NEW[0], srgb, False, n))
            o21 = over_of(esf(a, OLD[1], OLD[0], srgb, True, n))
            print(f"      {n:>4} {2*n+1:>5} {ov:>11.1f} {ct:>10.1f} "
                  f"{o21:>12.1f}")
        del a

    print("\n  [2] edge sharpness at the true address")
    print(f"      {'arm':<32} {'10-90% rise':>12}")
    for name, path, srgb in ARMS:
        if not os.path.exists(path):
            continue
        a = load(path)
        s = 257.0 if srgb else 1.0
        rows = []
        xp = NEW[0]
        for y in range(NEW[1] - 20, NEW[1] + 21):
            band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0) / s
            w = band[xp - 12:xp + 13, 1]
            xp = xp - 12 + int(np.argmax(np.abs(np.diff(w, prepend=w[:1]))))
            rows.append(band[xp - 60:xp + 61, 1])
        print(f"      {name:<32} {rise_1090(np.mean(rows, axis=0)):>9.1f} px")
        del a

    print("\n  Read column OVER(sec21) against OVER(true): where they differ,")
    print("  section 21 reported a feature that is not the one ORCH described.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
