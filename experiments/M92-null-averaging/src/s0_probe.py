"""M92 S0 -- timing and feasibility probe.  Writes nothing but a log.

Measures the cost of the three expensive steps so the pre-registration can name
a repetition count that will actually run: one RAW decode, one focus_fields on a
576^2 padded ROI cube, and one dsig draw.
"""
import glob
import os
import sys
import time

import numpy as np
import rawpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "m57-shape-metric", "src"))
import m57lib as K  # noqa: E402

ROOT = r"D:\personal\macro"
PAD = 32


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "112MSDCF", "*.ARW")))[6:68]
    print("files", len(files))

    t = time.time()
    with rawpy.imread(files[0]) as r:
        v = r.raw_image_visible
        g1 = v[0::2, 1::2].astype(np.float32)
        g2 = v[1::2, 0::2].astype(np.float32)
    plane = 0.5 * (g1 + g2) - K.BLACK
    t_dec = time.time() - t
    print(f"decode+quad: {t_dec:.2f}s   plane {plane.shape}")

    n = 8
    t = time.time()
    cube = np.empty((n, 576, 576), np.float32)
    for i, f in enumerate(files[:n]):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[0::2, 1::2].astype(np.float32)
            g2 = v[1::2, 0::2].astype(np.float32)
        p = 0.5 * (g1 + g2) - K.BLACK
        cube[i] = p[0:576, 0:576]
    print(f"{n} decodes: {time.time()-t:.2f}s  -> full stack "
          f"{(time.time()-t)/n*len(files):.0f}s")

    big = np.empty((len(files), 576, 576), np.float32)
    for i in range(len(files)):
        big[i] = cube[i % n]
    t = time.time()
    fine, coarse, reg = K.L1.focus_fields(big, 1.14469, 1.47)
    print(f"focus_fields on ({len(files)},576,576): {time.time()-t:.2f}s")

    t = time.time()
    ia, ib = K.splits(len(files))["parity"]
    ma, nea = K.merge_subset(big, coarse, reg, ia, pad=PAD)
    mb, _ = K.merge_subset(big, coarse, reg, ib, pad=PAD)
    print(f"two merge_subset: {time.time()-t:.2f}s   n_eff {nea:.3f}  "
          f"shape {ma.shape}")

    rs1 = K.RingStats(ma, mb)
    rng = np.random.default_rng(0)
    t = time.time()
    R = 20
    for _ in range(R):
        aa = ma + rng.standard_normal(ma.shape).astype(np.float32)
        bb = mb + rng.standard_normal(mb.shape).astype(np.float32)
        K.dsig(rs1, K.RingStats(aa, bb))
    print(f"{R} dsig draws: {time.time()-t:.2f}s  -> {1000*(time.time()-t)/R:.1f} ms/draw")

    print("full-plane memory for a 62-frame stack: "
          f"{62*plane.shape[0]*plane.shape[1]*4/1e9:.2f} GB")


if __name__ == "__main__":
    main()
