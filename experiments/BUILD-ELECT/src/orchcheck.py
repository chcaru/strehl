"""Read ORCH's own crop and ask what the sRGB ceiling is doing at their rim.

ORCH's argument is: R-G peaks at +22 against an interior of +11 and a background
of -4, and "a mixture of two endpoints cannot exceed both endpoints", so the
peak must be a reconstruction artifact in chroma.

That inference is sound in LINEAR light. Their measurement is on an 8-bit sRGB
PNG rendered at +1.45 stops, and there is a second way to make a peak there that
involves no reconstruction at all:

  a per-channel CEILING. Moving from bud toward a blown background, R and G both
  climb. The instant R reaches 255 while G is still climbing, R-G = 255 - G and
  must FALL. So R-G necessarily peaks just before R clips, and then collapses to
  0 where both channels are pinned. That is an overshoot exceeding both
  endpoints, produced by clipping, present in no linear quantity.

The two are separable by reading the pixels ORCH did not print: the CHANNEL
VALUES in the background, and how close to 255 the rim's shoulder gets. If the
background is pinned at 255 and the peak sits on the shoulder of that pinning,
the ceiling is live. If the background is well below 255, this mechanism is dead
and ORCH's inference survives.

Prints the same rows ORCH printed, plus the clipping census they did not.
"""
import os
import numpy as np
from PIL import Image

ASSET = r"C:\dev\strehl-out\VIEW-SHIP\assets\flower-bud-alone-cpl--SHIP-V2--1to1.png"


def main():
    if not os.path.exists(ASSET):
        print(f"MISSING: {ASSET}")
        return 1
    im = np.asarray(Image.open(ASSET).convert("RGB")).astype(np.int32)
    print("=" * 78)
    print("ORCH's crop: what is the 8-bit ceiling doing at the rim?")
    print("=" * 78)
    print(f"  asset {im.shape[1]} x {im.shape[0]}, dtype uint8")

    sus = im[20:220, 350:560]
    R, G, B = sus[:, :, 0], sus[:, :, 1], sus[:, :, 2]
    print(f"  ORCH's suspect region {sus.shape[:2]}")
    for nm, ch in (("R", R), ("G", G), ("B", B)):
        print(f"    {nm}: min {ch.min():3d}  max {ch.max():3d}  "
              f"at 255: {100.0 * (ch >= 255).mean():5.2f}%  "
              f"at >=250: {100.0 * (ch >= 250).mean():5.2f}%")

    rg = R - G
    print(f"  R-G over region: min {rg.min():+d} max {rg.max():+d}")

    print()
    print("  ORCH's rows, with the clip census they did not print.")
    print("  'CLIP' marks any channel at 255; 'near' marks any >= 250.")
    for row in (40, 60, 90, 120):
        if row >= sus.shape[0]:
            continue
        print(f"\n  row {row}:")
        print("     x    R    G    B   R-G  B-G  flag")
        for xx in range(96, 140):
            if xx >= sus.shape[1]:
                break
            r, g, b = int(R[row, xx]), int(G[row, xx]), int(B[row, xx])
            f = "CLIP" if max(r, g, b) >= 255 else (
                "near" if max(r, g, b) >= 250 else "")
            print(f"   {xx:3d}  {r:3d}  {g:3d}  {b:3d}  {r-g:+4d} {b-g:+4d}  {f}")

    print()
    print("  VERDICT INPUT")
    bg = sus[:, 150:, :]
    print(f"    far-right background block {bg.shape[:2]}: "
          f"R {np.median(bg[:,:,0]):.0f} G {np.median(bg[:,:,1]):.0f} "
          f"B {np.median(bg[:,:,2]):.0f}, "
          f"{100.0 * (bg.max(2) >= 255).mean():.2f}% of px have a channel at 255")
    print("    If that background is NOT pinned at 255, the ceiling mechanism")
    print("    is dead here and ORCH's 'cannot exceed both endpoints' stands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
