"""Scope check: on which corpus subjects is the lateral-CA correction INERT?

An arm rendered with STREHL_FIX_CA=off is coefficient-independent. If the
shipped (CA ON) render is bit-identical to it, the correction did not reach
the pixels -- regardless of what the banner printed.

This exists because `highly-angled-ruler-mm-cpl` scored 0.02414 on all three
arms to five decimals, and all three TIFFs turned out to share one SHA256
while the banner said `CORRECTING ... (gear matched; default on)`.

Decimated by 8 in both axes for speed; a geometric warp of ~0.5-2 px moves
far more than 1/64 of the pixels, so a zero here is a real zero. Commissioned
below by requiring that at least one subject reports NON-inert -- a comparator
that says "identical" for everything is broken, not informative.
"""
import glob
import os
import sys

import tifffile

OUT = r"D:\strehl-out\BUILD-CROP\sfout"
STRIDE = 8


def main() -> int:
    names = sorted(
        {
            os.path.basename(f).split(".")[0]
            for f in glob.glob(os.path.join(OUT, "*.tiff"))
            if not os.path.basename(f).startswith("_")
        }
    )
    print(f"{'subject':<38} {'ship-vs-off':>14} {'ship-vs-refit':>14}")
    print("-" * 70)
    inert, live, missing = [], [], []
    for n in names:
        try:
            s = tifffile.imread(os.path.join(OUT, n + ".shipped.tiff"))[::STRIDE, ::STRIDE]
            o = tifffile.imread(os.path.join(OUT, n + ".off.tiff"))[::STRIDE, ::STRIDE]
            r = tifffile.imread(os.path.join(OUT, n + ".refit.tiff"))[::STRIDE, ::STRIDE]
        except (FileNotFoundError, OSError):
            missing.append(n)
            print(f"{n:<38} {'MISSING ARM':>14}")
            continue
        d_off = int((s != o).sum())
        d_ref = int((s != r).sum())
        (inert if d_off == 0 else live).append(n)
        tag = "  <- CA INERT" if d_off == 0 else ""
        print(f"{n:<38} {d_off:>14,} {d_ref:>14,}{tag}")

    print()
    print(f"scored subjects : {len(names) - len(missing)}")
    print(f"CA INERT        : {len(inert)}")
    for n in inert:
        print("     ", n)
    if missing:
        print(f"MISSING ARMS    : {len(missing)}")
        for n in missing:
            print("     ", n)

    # Commissioning: a comparator that finds everything identical is dead.
    if not live:
        print("\nCOMMISSION FAIL: no subject showed ANY difference -- comparator is dead.")
        return 2
    print(f"\nCOMMISSION OK: comparator distinguishes ({len(live)} subjects DO differ).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
