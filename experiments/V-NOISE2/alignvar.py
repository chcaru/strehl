"""alignvar.py -- does align_image_stack's -m/-t choice change the registration?

WHY.  PREREGISTRATION.md sec.2 fixes the comparator pipeline as
`align_image_stack -l -m -C --use-given-order`.  On both deep subjects (`fba`,
205 frames; `bee`, 299) that aborts at the default pruning distance with

    After control points pruning reference images has no control points
    ... Increase error distance (-t parameter) ... or don't optimize HFOV.

so the pre-registered command does not run and SOME deviation is forced.  Hugin
names two remedies and this lane has now MEASURED that both work on bee's first
20 frames:

    -l    -C -t 3    exit=0   61.1s   20/20     (drop -m: no HFOV optimisation)
    -l -m -C -t 25   exit=0  126.6s   20/20     (keep -m: looser pruning)

The choice is not free.  align_image_stack registers the COMPARATOR arms only
-- strehl aligns itself -- so a worse alignment degrades enfuse and
focus-stack and leaves strehl untouched, and that error runs IN STREHL'S
FAVOUR.  It is therefore exactly the kind of choice this lane may not make by
argument.

ON DISCIPLINE the answer is already clear and this script cannot overturn it:
raising -t changes which control points are discarded as outliers, applied to
every frame alike; dropping -m changes the OPTIMISATION MODEL, removing the
field-of-view freedom that absorbs focus breathing -- and focus breathing is
the one geometric effect a focus stack is guaranteed to contain.  Keeping -m is
the smaller deviation.  This script asks what that decision COSTS, so the
report can state a number instead of a preference.

THE STATISTIC IS THE LANE'S OWN, AND IT IS A PAIR.  Split each aligned set into
even and odd frames, average each half, and measure per tile:

    noise  = robust sigma of (even_avg - odd_avg) / level      lower is better
    scene  = high-pass energy of (even_avg + odd_avg) / 2      higher is better

Misregistration inflates the first (the halves no longer cancel) AND deflates
the second (averaging misaligned frames blurs).  The pair is what makes the
answer interpretable: an alignment that is merely BLURRIER also looks quieter,
and would win on noise alone.  This is M127's "lowest noise and highest scene
content in the same tiles" logic applied to registration rather than to a
merge.

Both sets are cropped by -C and may not share a raster, so everything is
measured inside a common centred window, which is stated in the output.

Usage:  python alignvar.py <dirA> <dirB> [labelA] [labelB]
"""
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

T = 384          # tile side, matching noisefree.T's scale of analysis
EDGE = 16        # tile margin dropped before any statistic
HP = 4           # high-pass box size, matching noisefree.HP


def load_avg(paths):
    """Mean of a list of aligned TIFFs, as float32 luma, plus the raster."""
    acc, n, shp = None, 0, None
    for p in paths:
        a = tifffile.imread(p)
        if a.ndim == 3 and a.shape[2] == 4:
            a = a[:, :, :3]
        a = a.astype(np.float32)
        if a.dtype != np.float32:
            a = a.astype(np.float32)
        y = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
        if acc is None:
            acc, shp = np.zeros_like(y), y.shape
        elif y.shape != shp:
            raise SystemExit(f"raster changed inside one set: {y.shape} vs {shp}")
        acc += y
        n += 1
    return acc / n, shp


def stats(ev, od, cy, cx, half):
    """Per-tile (noise, scene) inside a centred window."""
    a = ev[cy - half:cy + half, cx - half:cx + half]
    b = od[cy - half:cy + half, cx - half:cx + half]
    ns, sc = [], []
    h, w = a.shape
    for y in range(0, h - T + 1, T):
        for x in range(0, w - T + 1, T):
            ta = a[y:y + T, x:x + T][EDGE:-EDGE, EDGE:-EDGE]
            tb = b[y:y + T, x:x + T][EDGE:-EDGE, EDGE:-EDGE]
            lvl = 0.5 * (ta.mean() + tb.mean())
            if lvl <= 1e-6:
                continue
            d = ta - tb
            ns.append(float(np.sqrt(0.5 * d.var())) / lvl)
            m = 0.5 * (ta + tb)
            hp = m - uniform_filter(m, HP)
            sc.append(float(np.sqrt(hp.var())) / lvl)
    return np.array(ns), np.array(sc)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__.strip().splitlines()[-1])
    dirs = [sys.argv[1], sys.argv[2]]
    labs = sys.argv[3:5] if len(sys.argv) >= 5 else ["A", "B"]

    sets = []
    for d in dirs:
        fs = sorted(f for f in os.listdir(d) if f.startswith("al_")
                    and f.endswith(".tif"))
        if not fs:
            raise SystemExit(f"no al_*.tif under {d}")
        ev, shp = load_avg([os.path.join(d, f) for f in fs[0::2]])
        od, _ = load_avg([os.path.join(d, f) for f in fs[1::2]])
        sets.append((ev, od, shp, len(fs)))

    shps = [s[2] for s in sets]
    h = min(s[0] for s in shps)
    w = min(s[1] for s in shps)
    half = (min(h, w) // (2 * T)) * T
    print("=" * 92)
    print("alignvar -- registration quality of two align_image_stack settings")
    print("=" * 92)
    for lab, d, s in zip(labs, dirs, sets):
        px = s[2][0] * s[2][1] / 1e6
        print(f"  {lab:26s} {s[3]:3d} frames  raster {s[2][0]}x{s[2][1]}"
              f"  = {px:5.1f} Mpx  {d}")

    # -------------------------------------------------- THE CROP IS THE ANSWER
    # -C crops to the rectangle every frame still covers AFTER warping, so the
    # surviving area is a direct readout of how well the frames were brought
    # into a common geometry.  It is also a HARD BLOCKER on the paired
    # statistic below: two different crops of one scene are two different
    # SCENES, and a centred window in each samples different content.  A scene
    # term computed across them measures what happens to be in the middle of
    # each crop, not registration quality.  Refuse rather than report it.
    areas = [s[2][0] * s[2][1] for s in sets]
    keep = min(areas) / max(areas)
    print(f"\n  surviving area ratio {keep * 100:.1f}%  "
          f"({'comparable' if keep > 0.90 else 'NOT comparable'})")
    if keep <= 0.90:
        big = labs[int(np.argmax(areas))]
        small = labs[int(np.argmin(areas))]
        print(f"\n  VERDICT FROM THE CROP ALONE, and it needs no other "
              f"statistic:")
        print(f"    '{small}' retains only {keep * 100:.1f}% of the area that "
              f"'{big}' retains.")
        print(f"    -C keeps exactly the rectangle all frames share after "
              f"warping, so losing {100 - keep * 100:.0f}% of it means the "
              f"frames were\n    brought into agreement over a far smaller "
              f"region.  '{big}' is the better registration.")
        print(f"\n  The paired noise/scene statistic below is WITHHELD: the two "
              f"rasters are different crops of the scene,\n  so a centred "
              f"window in each covers different content and any ratio between "
              f"them is a scene difference\n  wearing the clothes of a "
              f"registration difference.  Reporting it would be the exact "
              f"error this lane exists\n  to catch -- an earlier run of this "
              f"script printed 'noise x0.5527 scene x0.5087' and called it a "
              f"TRADE.")
        return 0

    print(f"  common centred window: {2 * half}x{2 * half}  tile {T}  edge {EDGE}")
    print()
    print(f"  {'setting':26s} {'tiles':>6s} {'noise (lower better)':>22s} "
          f"{'scene (higher better)':>23s}")

    out = []
    for lab, (ev, od, shp, nf) in zip(labs, sets):
        cy, cx = shp[0] // 2, shp[1] // 2
        ns, sc = stats(ev, od, cy, cx, half)
        out.append((lab, ns, sc))
        print(f"  {lab:26s} {len(ns):6d} {np.median(ns):22.6f} "
              f"{np.median(sc):23.6f}")

    (la, na, sa), (lb, nb, sb) = out
    if len(na) != len(nb):
        print("\n  tile counts differ; not paired")
        return 0
    rn = np.median(nb) / np.median(na)
    rs = np.median(sb) / np.median(sa)
    print(f"\n  {lb} relative to {la}:  noise x{rn:.4f}   scene x{rs:.4f}")
    print("\n  READING (the pair is what makes this interpretable):")
    if rn > 1.0 and rs < 1.0:
        print(f"    {lb} is BOTH noisier and softer -> unambiguously the worse "
              f"registration.")
    elif rn < 1.0 and rs > 1.0:
        print(f"    {lb} is BOTH quieter and sharper -> unambiguously the "
              f"better registration.")
    else:
        print(f"    the two statistics disagree, so the difference is a "
              f"sharpness/noise TRADE and not a registration quality ordering;\n"
              f"    neither setting is 'better' on this evidence alone.")
    print(f"\n  scale: a 1% move in either statistic is the size of the "
          f"identity floor this lane measured for the noise ratio (1.0-1.4%),\n"
          f"  so differences below ~1.4% are not differences.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
