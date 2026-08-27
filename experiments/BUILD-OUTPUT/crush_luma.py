"""Are the "crushed" pixels dark, or are they saturated colour?

`orch_printready.py` counts a pixel as crushed when ANY channel is <= 35/65535,
by taking a mean over the flattened three-channel array. That statistic cannot
tell these two things apart:

  * a genuinely black pixel -- all three channels near zero, no detail, the
    thing a print gate should care about; and
  * a strongly saturated pixel whose colour is outside the sRGB gamut, which
    `image_out::gamut_map` projects onto the gamut surface. A point ON the
    surface has one channel at exactly 0.0 by definition. Its other two
    channels can be anything, including full brightness.

The second is not shadow crush. It is a correctly rendered saturated colour,
and the pixel may be bright yellow or bright blue. Calling it "crush" and
gating on it would fail a master for being colourful.

This script reads the crushed pixels and reports what the OTHER channels are
doing, plus the BT.709 luminance of those pixels. If the crushed population is
bright, the crush statistic is measuring the gamut wall, not the tone scale.

It also reports how many DISTINCT values the surviving channels take across the
crushed population, because that is the question the brief actually asks: has
shadow detail been destroyed? If the other two channels still carry hundreds of
distinct levels, no detail has been lost -- the information is all still there,
just not in the channel that hit the wall.

Usage: python crush_luma.py <dir> <glob>
"""

import sys
import pathlib
import numpy as np
import tifffile

CRUSH = 35  # the threshold orch_printready.py uses, in 16-bit DN
CLIP = 65500


def bt709(a):
    """Luminance, on the 0..1 scale, from 16-bit display-encoded samples.

    Deliberately computed on the ENCODED values rather than linearised ones.
    The question here is "would a person looking at this file call the pixel
    dark", and a person looks at the encoded picture.
    """
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) / 65535.0


def main():
    root = pathlib.Path(sys.argv[1])
    pat = sys.argv[2] if len(sys.argv) > 2 else "*.tiff"
    files = sorted(root.glob(pat))
    if not files:
        print(f"no files matching {pat} in {root}")
        return

    print("Pixels with at least one channel <= 35, characterised.")
    print("'brightest other' = the max of the two surviving channels, as a %% of full scale.")
    print()
    hdr = (
        f"{'subject':<40} {'crushPX':>8} {'ch':>3} {'medLuma':>8} {'p90Luma':>8} "
        f"{'>25% luma':>10} {'medOther':>9} {'distinct':>9}"
    )
    print(hdr)
    print("-" * len(hdr))

    for f in files:
        a = tifffile.imread(str(f))
        if a.ndim != 3 or a.shape[2] != 3:
            print(f"{f.stem:<40} not RGB, skipped")
            continue
        low = (a <= CRUSH).any(axis=2)
        n = int(low.sum())
        if n == 0:
            print(f"{f.stem[:40]:<40} {0:>8} {'-':>3}")
            continue
        # Which channel is doing the crushing, for the majority of them.
        per_ch = [(int((a[..., c] <= CRUSH).sum()), c) for c in range(3)]
        per_ch.sort(reverse=True)
        ch = "RGB"[per_ch[0][1]]

        px = a[low]  # (n, 3)
        luma = bt709(px.astype(np.float64))
        other = np.sort(px.astype(np.int32), axis=1)[:, 1:]  # drop the lowest
        brightest = other.max(axis=1) / 65535.0
        frac_bright = float((luma > 0.25).mean())
        distinct = int(np.unique(other.reshape(-1)).size)

        print(
            f"{f.stem[:40]:<40} {100.0*n/low.size:>7.4f}% {ch:>3} "
            f"{np.median(luma):>8.4f} {np.percentile(luma, 90):>8.4f} "
            f"{100.0*frac_bright:>9.2f}% {np.median(brightest):>9.4f} {distinct:>9}"
        )

    print()
    print("Same treatment at the top of the scale: pixels with at least one channel >= 65500.")
    print()
    hdr2 = (
        f"{'subject':<40} {'clipPX':>8} {'ch':>3} {'medLuma':>8} {'dimmest':>9} "
        f"{'<75% luma':>10} {'distinct':>9}"
    )
    print(hdr2)
    print("-" * len(hdr2))
    for f in files:
        a = tifffile.imread(str(f))
        if a.ndim != 3 or a.shape[2] != 3:
            continue
        hi = (a >= CLIP).any(axis=2)
        n = int(hi.sum())
        if n == 0:
            print(f"{f.stem[:40]:<40} {0:>8} {'-':>3}")
            continue
        per_ch = [(int((a[..., c] >= CLIP).sum()), c) for c in range(3)]
        per_ch.sort(reverse=True)
        ch = "RGB"[per_ch[0][1]]
        px = a[hi]
        luma = bt709(px.astype(np.float64))
        # The DIMMEST surviving channel. If a pixel is a genuine blown
        # highlight all three are at the top and this is ~1.0. If it is a
        # saturated colour on the gamut wall, this is low.
        dim = np.sort(px.astype(np.int32), axis=1)[:, 0] / 65535.0
        print(
            f"{f.stem[:40]:<40} {100.0*n/hi.size:>7.4f}% {ch:>3} "
            f"{np.median(luma):>8.4f} {np.median(dim):>9.4f} "
            f"{100.0*float((luma < 0.75).mean()):>9.2f}% "
            f"{int(np.unique(px.reshape(-1)).size):>9}"
        )


if __name__ == "__main__":
    main()
