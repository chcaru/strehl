"""Spatially-resolved acuity: WHERE does the pyramid merge lose its ~10%?

ORCH's question, and it is the right one, because a global scalar cannot
adjudicate a localised defect -- that failure has now appeared three times
tonight (M122's hf energy, trend.py's gradient RMS, accept.py's acuity).
`accept.py` says couch-fibers-cpl loses 10.2%. It cannot say whether that is:

  UNIFORM    every tile ~0.90.  A flat MTF deficit. restore.rs can pay this
             back -- it is a sharpening problem, not a merge defect.

  STRUCTURED most tiles ~1.00 and a few annihilated. A real merge defect
             hiding behind a frame-wide mean, and sharpening would amplify
             the surviving noise in the dead regions rather than fix them.

The discriminating statistic is NOT the mean ratio -- that is the number we
already have and it cannot tell these apart. It is the CONCENTRATION of the
deficit: sort tiles by how much high-frequency energy they lost in absolute
terms, and ask what share of the total loss the worst 5% carry.

  uniform    -> worst 5% of tiles carry ~5-10% of the deficit
  structured -> worst 5% of tiles carry most of it

couch-fibers-cpl is the ideal subject for this: no silhouette, no smear, and
both arms clip exactly 0, so there is no artifact to inflate either side and
no clipped pixels to exclude.

Usage:  python acuitymap.py <CTRL.tiff> <BLEND.tiff> [--tile 128]
"""

import sys

import numpy as np
import tifffile


def box_blur(a, r):
    """Separable box blur, edge-replicated, via cumulative sums.

    Dependency-free on purpose: scipy is not a stated dependency of this repo
    and a silent import failure inside a 30-minute measurement is a bad trade
    for a filter that is six lines.
    """
    k = 2 * r + 1
    out = a
    for axis in (0, 1):
        out = np.swapaxes(out, 0, axis)
        pad = np.concatenate(
            [np.repeat(out[:1], r, axis=0), out, np.repeat(out[-1:], r, axis=0)], axis=0
        )
        c = np.cumsum(pad, axis=0, dtype=np.float64)
        c = np.concatenate([np.zeros((1,) + c.shape[1:]), c], axis=0)
        out = (c[k:] - c[:-k]) / k
        out = np.swapaxes(out, 0, axis)
    return out


def fine_energy(img, r=2):
    """Per-pixel high-frequency energy: the 2 px high-pass, squared.

    Same band `acuity.py` scores, so this decomposes a number we already have
    rather than introducing a second, differently-calibrated one.
    """
    g = img.astype(np.float64)
    return (g - box_blur(g, r)) ** 2


def tile_sum(e, t):
    h, w = e.shape
    nh, nw = h // t, w // t
    return e[: nh * t, : nw * t].reshape(nh, t, nw, t).sum(axis=(1, 3))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tile = 128
    if "--tile" in sys.argv:
        tile = int(sys.argv[sys.argv.index("--tile") + 1])
    if len(args) != 2:
        print(__doc__)
        return 2
    ctrl_p, blend_p = args

    ctrl = tifffile.imread(ctrl_p)
    blend = tifffile.imread(blend_p)
    if ctrl.shape != blend.shape:
        raise SystemExit(
            f"SHAPE MISMATCH {ctrl.shape} vs {blend.shape} -- a resolution "
            f"mismatch silently wrecks every gradient statistic; this is the "
            f"binned-output trap ORCH hit and it must be a hard error"
        )
    print(f"shape {ctrl.shape} {ctrl.dtype}   tile {tile}px")

    # Green plane. One plane, not luminance: a luminance mix would blend three
    # differently-demosaiced planes and blur the very band being measured.
    ce = fine_energy(ctrl[..., 1])
    be = fine_energy(blend[..., 1])

    ct = tile_sum(ce, tile)
    bt = tile_sum(be, tile)
    print(f"tiles {ct.shape[0]}x{ct.shape[1]} = {ct.size}")

    # Global, as a commissioning check: this must reproduce accept.py's ~0.90
    # to within a few points, or the two instruments are not measuring the same
    # thing and the decomposition below describes something else.
    g_ratio = np.sqrt(bt.sum() / ct.sum())
    print(f"\nglobal fine-band ratio (RMS)        {g_ratio:.4f}")
    print("  (commissioning: should land near accept.py's acuity ratio;")
    print("   a large disagreement means this is decomposing a DIFFERENT number)")

    # Per-tile ratio, guarding tiles with negligible reference energy: a ratio
    # of two near-zero numbers is noise that would dominate any percentile.
    floor = np.percentile(ct, 5)
    live = ct > max(floor, 1e-9)
    ratio = np.full(ct.shape, np.nan)
    ratio[live] = np.sqrt(bt[live] / ct[live])
    r = ratio[live]
    print(f"\nlive tiles {live.sum()} of {ct.size} (reference energy above p5)")
    print("per-tile ratio distribution:")
    for p in (1, 5, 25, 50, 75, 95, 99):
        print(f"  p{p:<3d} {np.percentile(r, p):.4f}")
    print(f"  mean {r.mean():.4f}   sd {r.std():.4f}")

    # THE DISCRIMINATOR. Absolute energy lost per tile, sorted descending.
    deficit = np.clip(ct - bt, 0, None)
    total = deficit.sum()
    if total <= 0:
        print("\nno tile lost energy; there is no deficit to localise")
        return 0
    order = np.sort(deficit.ravel())[::-1]
    cum = np.cumsum(order) / total
    n = order.size
    print(f"\nconcentration of the deficit ({total:.3e} total energy lost):")
    for frac in (0.01, 0.05, 0.10, 0.25, 0.50):
        k = max(1, int(round(frac * n)))
        print(f"  worst {frac*100:5.1f}% of tiles carry {cum[k-1]*100:5.1f}% of the loss")

    k5 = max(1, int(round(0.05 * n)))
    share5 = cum[k5 - 1]
    print("\nVERDICT")
    if share5 > 0.50:
        print(f"  STRUCTURED -- worst 5% of tiles carry {share5*100:.1f}% of the loss.")
        print("  The deficit is localised. This is a merge defect wearing a")
        print("  frame-wide average as a disguise, and sharpening would amplify")
        print("  noise in the dead regions rather than restore them.")
    elif share5 < 0.20:
        print(f"  UNIFORM -- worst 5% of tiles carry only {share5*100:.1f}% of the loss.")
        print("  The deficit is spread across the frame: a flat MTF cost, which")
        print("  is a sharpening problem and is payable by restore.rs.")
    else:
        print(f"  MIXED -- worst 5% carry {share5*100:.1f}%. Neither story is clean;")
        print("  report the percentile table rather than a one-word verdict.")

    # How many tiles actually got WORSE vs BETTER -- micro-contrast is up
    # globally, so a uniform-softness story has to explain both at once.
    print(f"\ntiles where blend has MORE fine energy: {(r > 1.0).sum()} of {r.size}"
          f" ({(r > 1.0).mean()*100:.1f}%)")
    print(f"tiles below 0.80: {(r < 0.80).sum()} ({(r < 0.80).mean()*100:.1f}%)")
    print(f"tiles below 0.50: {(r < 0.50).sum()} ({(r < 0.50).mean()*100:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
