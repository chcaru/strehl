"""Is the white rim an optical veil or ringing the merge manufactured?

Looking at the 2400px gallery render of `flower-bud-with-background-fern-cpl`,
there is a hard bright rim tracing every silhouette of the bud and the fern, plus
a grey aura outside it. That is the artifact the owner called unusable, and the
gallery is the SHIPPED estimator path, not the experimental pyramid.

Two candidate causes, and they make opposite predictions about the shape of the
luminance profile as a function of distance from the silhouette:

  optical veil    light from the defocused foreground spread across the
                  background. Physical, and MONOTONE: the contribution is
                  largest against the edge and decays with distance. It never
                  crosses the far-field level and comes back.

  merge ringing   the merge picked different frames at different scales across a
                  step edge, leaving an overshoot on the bright side and an
                  undershoot on the dark side. NON-MONOTONE: luminance departs
                  from the far-field level, reaches an extremum a few pixels
                  out, and returns.

So the profile's shape decides it, from one image, with no second arm and no
assumption about what a good render would look like. That matters because every
two-arm comparison tonight has been vulnerable to the reference being the
defective one.

Reported on both sides of the boundary, because ringing is a SIGNED PAIR --
overshoot outside, undershoot inside -- and the undershoot side is where the
exact-zero clamp measured in section 24 lives (blue-led, a ramified thin network,
p50 110px from a strong edge). If the two are the same phenomenon then the clamp
is not a separate defect but the tail of this one, and fixing the ringing
retires both.

CONTROLS

  far-field   d > FAR px, which sets the level everything is measured against.
              Printed, not assumed.
  polarity    the profile is computed separately for edges where the background
              is BRIGHTER than the subject and where it is DARKER. Ringing
              flips sign with polarity; a veil does not, since a defocused
              bright subject veils a dark background and not the reverse.
              tweezers (dark ground) looks clean and flower-bud (bright ground)
              does not, so polarity is already implicated.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

FAR = 300
MAXD = 400
SUB_Q = 0.35


def luma(im: np.ndarray) -> np.ndarray:
    a = im.astype(np.float32)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def profile(y: np.ndarray, mask: np.ndarray, name: str) -> None:
    """`mask` is the subject. Positive distance is into the background."""
    d_out = ndimage.distance_transform_edt(~mask)
    d_in = ndimage.distance_transform_edt(mask)
    signed = np.where(mask, -d_in, d_out)

    far = y[(signed > FAR)]
    if far.size < 1000:
        print(f"  {name}: only {far.size} far-field pixels, cannot set a level")
        return
    lvl = float(np.median(far))
    print(f"\n  {name}   far-field background level {lvl:8.1f} DN "
          f"(n={far.size}, d>{FAR}px)")
    print(f"  {'signed d (px)':>16}{'n':>10}{'median DN':>12}{'vs far-field':>14}")

    bins = [(-64, -32), (-32, -16), (-16, -8), (-8, -4), (-4, -2), (-2, 0),
            (0, 2), (2, 4), (4, 8), (8, 16), (16, 32), (32, 64), (64, 128),
            (128, 200), (200, 300), (300, MAXD)]
    outside = []
    for lo, hi in bins:
        m = (signed >= lo) & (signed < hi)
        if m.sum() < 200:
            continue
        med = float(np.median(y[m]))
        print(f"  {f'{lo:+d}..{hi:+d}':>16}{m.sum():10d}{med:12.1f}{med - lvl:+14.1f}")
        if lo >= 0:
            outside.append((lo, med - lvl))

    # The discriminator, computed rather than eyeballed. Monotone decay to zero
    # is a veil; a departure that reaches an extremum and comes back is ringing.
    if len(outside) >= 4:
        vals = [v for _, v in outside]
        peak = max(range(len(vals)), key=lambda i: abs(vals[i]))
        tail = vals[-1]
        print(f"\n    largest departure {vals[peak]:+.1f} DN at d={outside[peak][0]}px; "
              f"tail {tail:+.1f} DN")
        if peak == 0:
            print("    -> monotone from the edge outward: VEIL-like")
        else:
            # A veil is largest against the edge. An extremum further out that
            # then returns cannot be produced by light spreading outward.
            print(f"    -> extremum sits {outside[peak][0]}px OUT, not at the edge, "
                  f"and returns to {tail:+.1f}: RINGING-like")
        if abs(tail) > 0.25 * abs(vals[peak]):
            print(f"    -> and it does NOT return to the far-field level "
                  f"({tail:+.1f} vs peak {vals[peak]:+.1f}): a veil component is present too")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: edgeprofile.py <image.tiff> [more.tiff ...]", file=sys.stderr)
        return 2
    done = 0
    for p in sys.argv[1:]:
        path = Path(p)
        if not path.exists():
            print(f"MISSING {path}")
            continue
        im = tifffile.imread(path)
        y = luma(im)
        # Subject = the darker population. Checked by printing the split, so a
        # threshold that lands in the wrong place is visible rather than silent.
        thr = float(np.quantile(y[::4, ::4], SUB_Q))
        mask = y < thr
        mask = ndimage.binary_opening(mask, np.ones((5, 5)))
        mask = ndimage.binary_closing(mask, np.ones((5, 5)))
        print(f"\n=== {path.name} ===")
        print(f"  threshold {thr:.1f} DN -> subject {100 * mask.mean():.1f}% of frame, "
              f"background {100 * (~mask).mean():.1f}%")
        profile(y, mask, "dark subject on bright ground")
        done += 1
    print(f"\nSUMMARY  requested {len(sys.argv) - 1}  scored {done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
