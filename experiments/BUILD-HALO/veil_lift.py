"""Where did the correction actually land, and what shape is it.

The band tables and the profiler disagreed on `coffee-bean`, and the picture
showed why neither could settle it: the correction is not a smooth radial
function of distance-from-subject at all. Averaging it into annuli destroys the
only property that matters -- whether the lift has a BOUNDARY.

Two failure shapes have to be told apart and a scalar cannot do it:

  gate contour      a hard-edged region of near-constant lift. The correction
                    switched on across a line. Visible as a wedge or blob.
  noise rectify     high-frequency speckle. An extremum over frames biases a
                    featureless region upward by the max of N samples, and the
                    debias term is not removing all of it.

So: print the lift as a picture, and measure the gradient of the LIFT ITSELF.
A smooth veil correction has a small gradient everywhere. A gate contour has a
huge p99.9 gradient and a small median -- the same tail test that caught the
sec 32 contour, which a median could not see because a contour is a curve and
occupies a vanishing fraction of the pixels.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def luma(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p)).astype(np.float32)
    if a.ndim == 3:
        return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return a


def main() -> int:
    out = Path(sys.argv[1])
    stem = sys.argv[2]

    off = luma(out / f"{stem}-off.tif")
    on = luma(out / f"{stem}-on.tif")
    lift = on - off

    print(f"{stem}: lift over the whole frame")
    for q in (0.1, 1, 10, 25, 50, 75, 90, 99, 99.9):
        print(f"  p{q:<5} {np.percentile(lift, q):>+10.0f} DN")
    print(f"  touched (|lift| > 1 DN): {100 * (np.abs(lift) > 1).mean():.2f}% of frame")

    # Gradient of the lift, measured ONLY where the lift exists, and compared
    # against the OFF arm's gradient over that SAME population.
    #
    # The first version of this compared against the whole frame, which on
    # `coffee-bean` is 40% bean. The bean's surface texture set a p99.9 gradient
    # of 10353 DN, the backdrop lacework scored 4507, and the ratio came out at
    # 0.44 with a confident "smooth" verdict on a lift that is plainly lacy to
    # the eye. A statistic computed over the wrong population answers a question
    # nobody asked. Restrict to the treated set.
    treated = np.abs(lift) > 1.0
    gy, gx = np.gradient(lift)
    g = np.hypot(gy, gx)
    oy, ox = np.gradient(off)
    og = np.hypot(oy, ox)
    print("\n  gradient of the LIFT vs the OFF arm, both over the TREATED set only")
    if treated.any():
        for q in (50, 90, 99, 99.9):
            a, b = np.percentile(g[treated], q), np.percentile(og[treated], q)
            print(f"  p{q:<5} lift {a:>9.1f}   off {b:>9.1f}   ratio {a / max(b, 1e-6):>6.2f}x")

    # Lacework: what fraction of the treated set is on its own boundary.
    #
    # This is scale-free and it is the statistic that actually names the defect.
    # A solid region of radius r has perimeter/area ~ 2/r, so a smooth veil
    # correction scores near zero however large it is. A set that toggles at the
    # scale of paper fibre is nearly all boundary and scores near one.
    t = treated
    edge = np.zeros_like(t)
    edge[:-1, :] |= t[:-1, :] & ~t[1:, :]
    edge[1:, :] |= t[1:, :] & ~t[:-1, :]
    edge[:, :-1] |= t[:, :-1] & ~t[:, 1:]
    edge[:, 1:] |= t[:, 1:] & ~t[:, :-1]
    lace = edge.sum() / max(t.sum(), 1)
    print(f"\n  lacework (treated pixels on their own boundary): {100 * lace:.2f}%")

    print()
    if lace > 0.25:
        print("  VERDICT: LACEWORK. The correction toggles at texture scale. It "
              "will read as dirt on a smooth backdrop however right the mean is.")
    elif treated.any() and np.percentile(g[treated], 50) > np.percentile(og[treated], 50):
        print("  VERDICT: SPECKLE. The lift is rougher than the scene it sits on "
              "-- noise rectification, not a veil correction.")
    else:
        print("  VERDICT: smooth and solid. The lift has no boundary and no speckle.")

    pics = out / "pics"
    pics.mkdir(exist_ok=True)
    step = max(1, off.shape[1] // 900)
    v = lift[::step, ::step]
    # Symmetric signed map: grey = untouched, white = lifted, black = darkened.
    s = float(np.percentile(np.abs(lift), 99.5)) or 1.0
    img = np.clip(0.5 + 0.5 * v / s, 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(pics / f"{stem}-lift.png")
    print(f"\n  wrote {stem}-lift.png  (grey = untouched, white = lifted, "
          f"full scale +-{s:.0f} DN)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
