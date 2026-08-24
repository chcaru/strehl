"""Is the per-frame level change PHOTOMETRY or REDISTRIBUTION?

A patch median can change for two entirely different reasons:

  * the frame really received less light (photometry -- a gain fixes it), or
  * defocus moved light from one place to another (redistribution -- a gain
    does NOT fix it, and applying one destroys real image content).

Blur conserves total flux. So the whole-frame mean above black is blind to
redistribution and sensitive only to photometry. That is the decisive statistic
and it is what this measures, per CFA plane, along with the clipped fraction
(clipping breaks the conservation argument) and a coarse tile map so the
spatial shape of whatever is left can be characterised.
"""
import glob
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rawpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO = r"D:\personal\macro"
TILES = 24


def _one(path):
    with rawpy.imread(path) as r:
        raw = r.raw_image_visible
        black = float(np.mean(r.black_level_per_channel))
        white = float(r.white_level)
        colors = r.raw_colors_visible
        norm = (raw.astype(np.float32) - black) / (white - black)
        H, W = norm.shape
        means = np.empty(4)
        for c in range(4):
            m = colors == c
            means[c] = float(norm[m].mean()) if m.any() else np.nan
        gm = (colors == 1) | (colors == 3)
        g = norm[gm]
        gmean = float(g.mean())
        gmed = float(np.median(g))
        clipped = float(np.mean(raw >= white - 1))
        near_black = float(np.mean(norm <= 0.0))
        # Coarse tile means on the green photosites, sensor-fixed.
        th, tw = H // TILES, W // TILES
        tile = np.empty((TILES, TILES))
        for i in range(TILES):
            for j in range(TILES):
                sub = norm[i * th:(i + 1) * th, j * tw:(j + 1) * tw]
                sm = gm[i * th:(i + 1) * th, j * tw:(j + 1) * tw]
                tile[i, j] = sub[sm].mean()
    return means, gmean, gmed, clipped, near_black, tile


def run(stack, workers=8):
    files = sorted(glob.glob(os.path.join(MACRO, stack, "*.ARW")))
    n = len(files)
    means = np.empty((n, 4))
    gmean = np.empty(n)
    gmed = np.empty(n)
    clip = np.empty(n)
    nb = np.empty(n)
    tiles = np.empty((n, TILES, TILES))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for k, (m, gm, gd, c, b, tl) in enumerate(ex.map(_one, files, chunksize=2)):
            means[k], gmean[k], gmed[k], clip[k], nb[k], tiles[k] = m, gm, gd, c, b, tl
    print("%s: %d frames in %.0f s" % (stack, n, time.time() - t0))
    print("  whole-frame GREEN MEAN  %.6f .. %.6f  ratio %.4f (%.4f stops)"
          % (gmean.min(), gmean.max(), gmean.max() / gmean.min(),
             np.log2(gmean.max() / gmean.min())))
    print("  whole-frame GREEN MEDIAN %.6f .. %.6f  ratio %.4f"
          % (gmed.min(), gmed.max(), gmed.max() / gmed.min()))
    print("  clipped fraction        %.6f .. %.6f" % (clip.min(), clip.max()))
    print("  at-or-below-black frac  %.6f .. %.6f" % (nb.min(), nb.max()))
    print("  per-plane mean ratios (max/min): R %.4f G1 %.4f B %.4f G2 %.4f"
          % tuple(means.max(axis=0) / means.min(axis=0)))
    out = os.path.join(HERE, "data", "flux-%s.npz" % stack)
    np.savez_compressed(out, means=means, gmean=gmean, gmed=gmed, clip=clip,
                        near_black=nb, tiles=tiles,
                        files=np.array([os.path.basename(f) for f in files]))
    print("  wrote %s" % out)


if __name__ == "__main__":
    for s in sys.argv[1:] or ["bee-3-cpl", "lavendar-cpl", "leaf-2-cpl",
                              "bee-2-cpl"]:
        run(s)
