"""WHERE are the notch tiles, and are they a real population or an artifact?

The notch bin carries n=17 of 1660 tiles on tweezers -- 1%. Three facts about it
now sit uneasily together:

  - amplitude ratio moves a lot with the gate  (0.9918 at g2 -> 0.3111 at g4)
  - correlation does NOT                       (0.0946 at g2 ->  0.1156 at g4)
  - the reference's content there is structured (lag1 0.7140 vs noise pole 0.2107)

If the sub-gate fallback were the whole story, the gate that cuts L1's averaged
fraction from 36.8% to 0.1% should have moved the correlation too. It did not.
So either the notch tiles are a peculiar population that disagrees for a
different reason entirely, or the bin is too thin to mean anything.

tweezers' tile-amplitude distribution is bimodal -- 725 tiles at 3-18 DN, 838 at
272-810, and only 79 in the whole 18-272 valley. A bin sitting inside a sparse
valley of a bimodal distribution is exactly where a tiny, unrepresentative
population hides.

This prints the tiles themselves rather than another summary of them: position,
amplitude, ratio, correlation, local luminance, and distance to the nearest
strong edge. If they cluster at the subject outline, the "notch" is the
occlusion halo re-parameterised, and it belongs to BUILD-HALO rather than to the
fallback. If they are scattered, it is a real amplitude-organised effect.

No verdict line without the rows above it.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

TILE = 128
S_LO, S_HI = 0.535, 1.874
LO, HI = 31.0, 53.0
MAX_ROWS = 40


def bandpass(g: np.ndarray) -> np.ndarray:
    return ndimage.gaussian_filter(g, S_LO) - ndimage.gaussian_filter(g, S_HI)


def corr(a, b):
    a = a.ravel().astype(np.float64) - a.mean()
    b = b.ravel().astype(np.float64) - b.mean()
    na, nb = np.sqrt((a * a).sum()), np.sqrt((b * b).sum())
    return float("nan") if na < 1e-12 or nb < 1e-12 else float((a * b).sum() / (na * nb))


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: notchtiles.py <dir> <subject> [lo] [hi]", file=sys.stderr)
        return 2
    global LO, HI
    d, subject = Path(sys.argv[1]), sys.argv[2]
    if len(sys.argv) >= 5:
        LO, HI = float(sys.argv[3]), float(sys.argv[4])
    R = tifffile.imread(d / f"{subject}--ctrl.tiff")
    T = tifffile.imread(d / f"{subject}--blend.tiff")
    gr, gt = R[:, :, 1].astype(np.float32), T[:, :, 1].astype(np.float32)
    lit = gr > np.quantile(gr[::4, ::4], 0.20)
    br, bt = bandpass(gr), bandpass(gt)

    # Strong-edge map and the distance to it, the same proxy shape.py used, so
    # the two probes' "distance to edge" numbers are comparable.
    gm = ndimage.gaussian_gradient_magnitude(gr, 2.0)
    strong = gm > np.quantile(gm[::4, ::4], 0.99)
    dist = ndimage.distance_transform_edt(~strong)

    h, w = gr.shape
    rows, alld = [], []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            sl = (slice(y, y + TILE), slice(x, x + TILE))
            if lit[sl].mean() < 0.5:
                continue
            ar = float(np.abs(br[sl]).mean())
            if ar < 1e-6:
                continue
            alld.append(float(np.median(dist[sl])))
            if not (LO <= ar < HI):
                continue
            rows.append(
                (
                    x,
                    y,
                    ar,
                    float(np.abs(bt[sl]).mean()) / ar,
                    corr(br[sl], bt[sl]),
                    float(gr[sl].mean()),
                    float(np.median(dist[sl])),
                    float(lit[sl].mean()),
                )
            )

    print(f"{subject}: {len(rows)} tiles with refAmp in [{LO:.0f},{HI:.0f})   "
          f"of {len(alld)} scored tiles\n")
    print(f"  {'x':>6}{'y':>6}{'refAmp':>9}{'ratio':>8}{'r':>8}{'meanY':>9}{'distEdge':>10}{'lit':>7}")
    ordered = sorted(rows, key=lambda t: t[1])
    for r in ordered[:MAX_ROWS]:
        print(f"  {r[0]:6d}{r[1]:6d}{r[2]:9.1f}{r[3]:8.3f}{r[4]:8.3f}{r[5]:9.0f}{r[6]:10.1f}{r[7]:7.2f}")
    if len(ordered) > MAX_ROWS:
        print(f"  ... {len(ordered) - MAX_ROWS} further tiles not printed")

    if rows:
        dn = np.array([r[6] for r in rows])
        da = np.array(alld)
        xs = np.array([r[0] for r in rows])
        ys = np.array([r[1] for r in rows])
        print(f"\n  mean ratio {np.mean([r[3] for r in rows]):.4f}   "
              f"mean r {np.nanmean([r[4] for r in rows]):.4f}")
        print(f"  distance-to-strong-edge   notch tiles p50 {np.median(dn):8.1f} px")
        print(f"                            ALL   tiles p50 {np.median(da):8.1f} px")
        print(f"  spatial spread            x {xs.min():5d}-{xs.max():5d}   "
              f"y {ys.min():5d}-{ys.max():5d}   (frame {w} x {h})")
        fx = (xs.max() - xs.min() + TILE) / w
        fy = (ys.max() - ys.min() + TILE) / h
        print(f"  bounding box covers       {fx:.2f} of width, {fy:.2f} of height")
        # How many DISTINCT tile rows the population occupies. A defect confined
        # to a few scan-line bands looks completely different from one spread
        # over the frame, and the bounding box alone cannot tell them apart --
        # two tiles at opposite corners give a full-frame box.
        urow = len(set(ys.tolist()))
        ucol = len(set(xs.tolist()))
        print(f"  occupies                  {urow} distinct tile rows of "
              f"{len(range(0, h - TILE + 1, TILE))}, {ucol} distinct columns of "
              f"{len(range(0, w - TILE + 1, TILE))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
