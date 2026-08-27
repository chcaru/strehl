"""Quantitative dust census across the whole corpus, with a commissioned statistic.

The eye found dust in two masters. That is enough to know the defect is real and not
enough to know how much of the corpus carries it, which is what decides whether the
correction is a blocker or a polish item.

The statistic: dust is a *coherent dark* structure, sensor noise is *symmetric*. So
high-pass the smoothest eligible block and measure the ASYMMETRY of the residual
histogram -- specifically the dark-tail excess, the fraction of pixels below -k*MAD minus
the fraction above +k*MAD. Noise contributes zero to that difference by construction, at
any noise level, so the statistic does not need to know how noisy a given master is. A
skew-based measure is used rather than a blob count because a blob detector needs a size
prior and dust ranges from single-frame discs to long smeared trails.

Commissioning is mandatory and runs first: plant discs of known depth into each master's
own block and require the statistic to move. A census whose detector was never shown to
respond would report the same clean number whether the corpus is clean or the detector is
blind, and tonight four instruments have already done exactly that.
"""
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from orch_smoothcrop import CROP, HP_WIN, boxblur, pick_smooth  # noqa: E402

K = 3.0
PLANT_DN = 60.0
PLANT_R = 30


def residual(blk):
    return blk - boxblur(blk, HP_WIN)


def dark_excess(res):
    """Percent of pixels in the dark tail beyond the matching bright tail."""
    mad = float(np.median(np.abs(res - np.median(res))))
    if mad <= 0:
        return 0.0, 0.0
    t = K * 1.4826 * mad
    dark = float((res < -t).mean())
    bright = float((res > t).mean())
    return (dark - bright) * 100.0, t


def plant(blk, rng):
    z = blk.copy()
    yy, xx = np.mgrid[0:z.shape[0], 0:z.shape[1]]
    for _ in range(8):
        cy = int(rng.integers(PLANT_R, z.shape[0] - PLANT_R))
        cx = int(rng.integers(PLANT_R, z.shape[1] - PLANT_R))
        z[((yy - cy) ** 2 + (xx - cx) ** 2) < PLANT_R ** 2] -= PLANT_DN
    return z


def main(paths):
    rng = np.random.default_rng(77)
    rows = []
    print(f"{'subject':34s} {'real':>8s} {'planted':>9s} {'gain':>7s} {'MAD thr':>9s}")
    print("-" * 74)
    for p in paths:
        p = pathlib.Path(p)
        a = tifffile.imread(str(p))
        rgb = a[:, :, :3].astype(np.float32)
        lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        y0, x0, e, _ = pick_smooth(lum)
        if e is None:
            print(f"{p.stem[:34]:34s} {'no eligible block':>28s}")
            del a, rgb, lum
            continue
        blk = lum[y0:y0 + CROP, x0:x0 + CROP].copy()
        del a, rgb, lum
        real, thr = dark_excess(residual(blk))
        pl, _ = dark_excess(residual(plant(blk, rng)))
        gain = pl - real
        rows.append((p.stem, real, pl, gain, thr, x0, y0))
        print(f"{p.stem[:34]:34s} {real:7.3f}% {pl:8.3f}% {gain:6.3f} {thr:8.1f}")
        del blk

    print()
    deaf = [r for r in rows if r[3] < 0.15]
    live = [r for r in rows if r[3] >= 0.15]
    dusty = sorted([r for r in live if r[1] >= 0.10], key=lambda r: -r[1])
    quiet = [r for r in live if r[1] < 0.10]
    print(f"masters examined                   : {len(rows)}")
    print(f"detector responded to the plant    : {len(live)}")
    print(f"detector DEAF (census meaningless) : {len(deaf)}  "
          f"{[r[0] for r in deaf] if deaf else ''}")
    print(f"  of the responsive ones:")
    print(f"    dark-tail excess >= 0.10%      : {len(dusty)}")
    print(f"    below that                     : {len(quiet)}")
    print(f"partition sums to                  : {len(deaf) + len(dusty) + len(quiet)}"
          f" of {len(rows)}")
    if dusty:
        print(f"\nranked by dark-tail excess (a {PLANT_DN:.0f} DN plant moves the "
              f"statistic by the 'gain' column, so these are in comparable units):")
        for stem, real, pl, gain, thr, x0, y0 in dusty:
            print(f"   {real:7.3f}%  {stem:38s} crop ({x0},{y0})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
