"""Is the soft tail real softness, or is it focus breathing?

WHY. Instrument v3 reports the master sharper than the per-site best frame at
every block size, but with a tail: 16.3% of sites at block 64 (28.9% at block
16) read softer. Dumping the worst site showed master and frame displaying
DIFFERENT SUBJECT CONTENT at the same coordinates -- the master showing smooth
subject interior, the frame showing the silhouette edge about 100 px further
left. That is focus breathing: magnification changes as the rack moves, and the
registration in v3 is a single global translation over a 2560 px tile, which
cannot absorb a scale change. The worst site sits at the tile's far corner,
where a scale error has its largest lever arm. So the tail may be an artifact of
comparing two different places.

THE TEST. Registration error and softness are different claims and they predict
different things. If the tail is misregistration, the sites that read soft will
be the sites with large residual local displacement, and residual displacement
will grow with distance from the tile centre. If the tail is genuine softness,
soft sites will be scattered with no such relationship. Measuring the residual
per site separates them, and the answer does not depend on which one I expect.

Then the verdict is recomputed with per-site local registration, which absorbs
breathing to first order, so the cost of the artifact is stated as a number
rather than as an argument.

Usage:
  python breathing_check.py <master.tiff> <framesdir> <x> <y> <size> [block]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from softness_verdict3 import (  # noqa: E402
    luma_linear, detail, contrast, shift_of, warp, build_envelope, boot_ci,
    HP_SIGMA,
)

PAD = 32


def local_shift(a, b):
    wa = cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(
        a.astype(np.float32) * wa, b.astype(np.float32) * wa)
    return dx, dy, resp


def block_detail_at(img, y0, x0, block, floor):
    """High-pass energy of one block, same estimator as v3, noise floor removed."""
    f = img[y0 - PAD : y0 + block + PAD, x0 - PAD : x0 + block + PAD].astype(np.float32)
    hp = f - cv2.GaussianBlur(f, (0, 0), HP_SIGMA)
    core = hp[PAD : PAD + block, PAD : PAD + block]
    return max(float(np.mean(core * core)) - floor, 0.0)


def main():
    mpath, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    block = int(sys.argv[6]) if len(sys.argv) > 6 else 64

    master = luma_linear(tifffile.imread(mpath)[y : y + size, x : x + size])
    files = sorted(fdir.glob("frame-*.tiff"))
    tiles, floors, names = [], [], []
    for f in files:
        t = luma_linear(tifffile.imread(str(f))[y : y + size, x : x + size])
        dx, dy = shift_of(master, t)
        t = warp(t, dx, dy)
        tiles.append(t)
        floors.append(detail(t, block)[1])
        names.append(f.stem.replace("frame-", ""))

    cm = contrast(master, block)
    cfloor = float(np.percentile(cm, 65))
    env, win, valid = build_envelope(tiles, block, cfloor)
    live = (cm > cfloor) & valid
    md, mfloor = detail(master, block)
    ratio = md / np.maximum(env, 1e-12)

    ny, nx = cm.shape
    cy0, cx0 = ny / 2, nx / 2
    rows = []
    for by in range(ny):
        for bx in range(nx):
            if not live[by, bx]:
                continue
            y0, x0 = by * block, bx * block
            if y0 < PAD or x0 < PAD or y0 + block + PAD > size or x0 + block + PAD > size:
                continue
            w = win[by, bx]
            a = master[y0 - PAD : y0 + block + PAD, x0 - PAD : x0 + block + PAD]
            b = tiles[w][y0 - PAD : y0 + block + PAD, x0 - PAD : x0 + block + PAD]
            dx, dy, _ = local_shift(a, b)
            resid = float(np.hypot(dx, dy))
            radius = float(np.hypot(by - cy0, bx - cx0)) * block
            shifted = warp(tiles[w], -dx, -dy) if resid > 0.05 else tiles[w]
            d_loc = block_detail_at(shifted, y0, x0, block, floors[w])
            rows.append((ratio[by, bx], resid, radius,
                         md[by, bx] / max(d_loc, 1e-12)))

    r = np.array(rows)
    glob, resid, radius, loc = r[:, 0], r[:, 1], r[:, 2], r[:, 3]
    soft = glob < 1.0

    print(f"tile ({x},{y}) {size}x{size} block {block}: {len(r)} sites, "
          f"{int(soft.sum())} read soft under global registration\n")

    print("  RESIDUAL LOCAL DISPLACEMENT, master vs the frame that won the site")
    print(f"    sites reading SOFT (ratio<1) : median {np.median(resid[soft]):6.2f} px"
          f"   90th pct {np.percentile(resid[soft], 90):6.2f} px")
    print(f"    sites reading SHARP(ratio>1) : median {np.median(resid[~soft]):6.2f} px"
          f"   90th pct {np.percentile(resid[~soft], 90):6.2f} px")
    ratio_of_medians = np.median(resid[soft]) / max(np.median(resid[~soft]), 1e-9)
    print(f"    soft sites carry {ratio_of_medians:.2f}x the residual displacement")

    print("\n  DISPLACEMENT vs DISTANCE FROM TILE CENTRE"
          "  (breathing is a scale error: grows with radius)")
    qs = np.quantile(radius, [0, 0.25, 0.5, 0.75, 1.0])
    for i in range(4):
        m = (radius >= qs[i]) & (radius <= qs[i + 1])
        if m.sum() < 5:
            continue
        print(f"    radius {qs[i]:6.0f}..{qs[i + 1]:6.0f} px : "
              f"median residual {np.median(resid[m]):6.2f} px, "
              f"{100 * (glob[m] < 1).mean():5.1f}% read soft   (n={int(m.sum())})")
    cc = float(np.corrcoef(radius, resid)[0, 1])
    print(f"    Pearson r(radius, residual) = {cc:+.3f}")

    print("\n  VERDICT RECOMPUTED WITH PER-SITE LOCAL REGISTRATION")
    for label, v in (("global translation only", glob), ("local per-site", loc)):
        lo, hi = boot_ci(v)
        print(f"    {label:<26} median {np.median(v):6.4f}  "
              f"CI [{lo:.4f}, {hi:.4f}]  softer {100 * (v < 1).mean():5.1f}%")


if __name__ == "__main__":
    main()
