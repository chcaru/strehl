"""Cache G1/G2 tiles across the focus bracket.

The measurement compares the *same photosites* in a frame where a region is in
focus against one where the same region is defocused. That matching is the whole
design: identical sensitivity mismatch, identical PRNU, near-identical exposure,
so the only thing that can differ is what the optics delivered.
"""

import json
import os
import sys
import time

import numpy as np
import rawpy

SRC = r"D:\personal\macro\bee-3-cpl"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

TILE = 384                      # binned px
TILES = {                       # binned-green coordinates, from r0_recon
    "T1": (512, 2560),
    "T2": (768, 2816),
    "T3": (1280, 512),
    "T4": (1024, 768),
}
STEP = 6


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".arw"))
    files = files[::STEP]
    print("caching %d of %d frames, %d tiles of %d binned px"
          % (len(files), len(os.listdir(SRC)), len(TILES), TILE))

    store = {k: [] for k in TILES}
    names = []
    t0 = time.time()
    for n, fn in enumerate(files):
        # `raw_image_visible` is a VIEW into memory owned by the LibRaw object.
        # Slicing it after the `with` block closes is a use-after-free and takes
        # the interpreter down with an access violation (0xC0000005), silently
        # and with no traceback. Every read must be copied inside the block.
        with rawpy.imread(os.path.join(SRC, fn)) as r:
            vis = r.raw_image_visible
            for k, (by, bx) in TILES.items():
                g1 = np.array(vis[0::2, 1::2][by:by + TILE, bx:bx + TILE])
                g2 = np.array(vis[1::2, 0::2][by:by + TILE, bx:bx + TILE])
                store[k].append(np.stack([g1, g2]))
        names.append(fn)
        if n % 10 == 0:
            print("   %3d/%d  %s  %.1fs" % (n, len(files), fn, time.time() - t0), flush=True)

    np.savez_compressed(
        os.path.join(OUT, "tiles.npz"),
        names=np.array(names),
        **{k: np.stack(v) for k, v in store.items()},
    )
    meta = {"tile": TILE, "tiles": {k: list(v) for k, v in TILES.items()},
            "step": STEP, "n_frames": len(files), "black": 512, "white": 16383,
            "seconds": round(time.time() - t0, 1)}
    with open(os.path.join(OUT, "tiles_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
