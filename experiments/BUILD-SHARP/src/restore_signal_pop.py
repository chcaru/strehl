"""Is the restoration inert because the noise is wrong, or because the SIGNAL
estimate is taken over the wrong population?

s24 blamed sigma^2 (a single frame's variance handed to a 205-frame merge) and
proposed the merged-plane variance as the fix. The sigma sweep refutes that fix:
the merge's own noise reduction is 0.534x in amplitude, i.e. 0.285x in variance,
and at sigma^2 x 0.5 AND x 0.25 the render is still byte-identical to OFF. The
correct sigma^2 does not wake the filter. So the deficit is not all in sigma^2.

The other term in the Wiener criterion is S, the SIGNAL power, and `design_fir`
takes it from `power_at(r, f)` -- a statistic of the WHOLE plane. A macro frame
is mostly out-of-focus background. If the whole-plane average is dominated by
regions that contain no detail, then S is being estimated on the population that
has the least to restore, and the criterion sigma^2/S < h(1-h) is being decided
by the background rather than by the subject.

That predicts something specific and falsifiable: the ratio between the power in
the sharpest tiles and the whole-plane mean IS the factor by which a
detail-population fit would raise S. If that ratio is comparable to the ~4-10x
by which the sigma sweep had to be understated before the filter fired, the two
explanations are the same explanation, and the honest fix is a local or
detail-weighted S rather than a lie about the noise.

CAVEAT, stated because it bounds the claim: this measures the DELIVERED green
plane, not the pre-restore CFA plane that `power_at` actually sees. The absolute
powers therefore differ. The quantity read here is the RATIO between tile
populations, which is a property of the scene's layout and survives a monotone
pipeline far better than the levels do. It is evidence about heterogeneity, not
a substitute for instrumenting `power_at`, which lives in a file I do not own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

TILE = 256
SCALE = 1.035063
BANDS = [
    ("0.19-0.29 (deficit band 1)", 0.20 / SCALE, 0.30 / SCALE),
    ("0.29-0.39 (deficit band 2)", 0.30 / SCALE, 0.40 / SCALE),
]


def band_power(t: np.ndarray) -> list[float]:
    n = t.shape[0]
    c = t - t.mean()
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    f = np.fft.fft2(c * w)
    p = (np.abs(f) ** 2) / (n * n) ** 2 / (w ** 2).mean()
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.hypot(fy, fx)
    return [float(p[(r >= lo) & (r < hi)].sum()) for _, lo, hi in BANDS]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: restore_signal_pop.py <off.tif>")
    a = tifffile.imread(sys.argv[1])
    g = a[:, :, 1].astype(np.float64)
    h, w = g.shape
    coords, sharp, powers = [], [], []
    for y in range(TILE, h - 2 * TILE, TILE):
        for x in range(TILE, w - 2 * TILE, TILE):
            t = g[y:y + TILE, x:x + TILE]
            coords.append((y, x))
            sharp.append(float(np.abs(np.diff(t, axis=0)).mean()
                               + np.abs(np.diff(t, axis=1)).mean()))
            powers.append(band_power(t))
    sharp = np.asarray(sharp)
    powers = np.asarray(powers)
    order = np.argsort(sharp)
    n = len(order)
    top = order[-max(1, n // 20):]
    bot = order[: max(1, n // 20)]

    print(f"{Path(sys.argv[1]).name}: {n} tiles of {TILE}x{TILE}")
    print()
    print(f"  {'band':28s} {'plane mean':>12s} {'sharpest 5%':>12s} "
          f"{'flattest 5%':>12s} {'sharp/mean':>11s}")
    print("  " + "-" * 79)
    for i, (lbl, _, _) in enumerate(BANDS):
        m = float(powers[:, i].mean())
        s = float(powers[top, i].mean())
        f = float(powers[bot, i].mean())
        print(f"  {lbl:28s} {m:12.4f} {s:12.4f} {f:12.4f} {s/m:11.2f}x")
    print()
    print("  `sharp/mean` is the factor by which a fit restricted to detail tiles")
    print("  would raise S over the whole-plane fit that `power_at` performs.")
    print("  Compare it against the understatement the sigma sweep required")
    print("  (inert at sigma^2 x 0.25, firing at x 0.1, so between 4x and 10x).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
