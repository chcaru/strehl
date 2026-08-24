"""M70 s04 - the decisive measurement: through-focus band power over the corpus.

For every frame of every stack, for a fixed deterministic grid of green-quincunx
patches, measure the radially-averaged power in six frequency bands and the
w^2-weighted patch level that the photon-transfer noise model needs.

Nothing is decided here; s04 only produces `out/tfs-<stack>.npz`. The
pre-registered criteria are scored in s05. This separation is deliberate: the
patch grid, the bands and the criteria were all fixed in PREREGISTRATION.md,
committed at 80572ec, before this script computed a single corpus spectrum.

Rule 17: no patch is selected by its focus behaviour. The grid is fixed by
fraction of the active area and is identical for every stack.
"""

from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402

ROOT = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

PATCH = 256  # GQ samples -> 511 x 511 sensor px
TILE = 128  # Welch tile, 50% overlap -> 3 x 3 = 9 tiles per patch

ROW_FRAC = (0.20, 0.40, 0.60, 0.80)
COL_FRAC = (0.15, 0.32, 0.49, 0.66, 0.83, 0.95)

BAND_NAMES = [b[0] for b in M.BANDS]


def patch_centres(patch: int = PATCH):
    """Fixed grid. GQ crop of `size` needs a (2*size-1) sensor bounding box, so
    every centre must sit at least `size-1` px from every active-area edge."""
    half = patch - 1
    out = []
    for rf in ROW_FRAC:
        for cf in COL_FRAC:
            rc = int(round(rf * L.ACTIVE_H))
            cc = int(round(cf * L.ACTIVE_W))
            rc = min(max(rc, half), L.ACTIVE_H - 1 - half)
            cc = min(max(cc, half), L.ACTIVE_W - 1 - half)
            # m5_lib requires an even sensor centre so the Bayer phase of the
            # crop is identical for every patch and every stack.
            out.append((rc - (rc % 2), cc - (cc % 2)))
    return out


CENTRES = patch_centres()


def measure_frame(args):
    path, patch, tile = args
    a = L.load_active(path)
    npatch = len(CENTRES)
    pw = np.zeros((npatch, len(BAND_NAMES)), dtype=np.float64)
    lvl = np.zeros(npatch, dtype=np.float64)
    for i, (rc, cc) in enumerate(CENTRES):
        p = L.crop_lattice(a, "GQ", rc, cc, patch)
        f, pr, c = L.spectrum(p, "GQ", tile=tile, window="hann", sector="iso")
        ba = M.band_average(f, pr, c)
        for j, name in enumerate(BAND_NAMES):
            pw[i, j] = ba[name][0]
        lvl[i] = M.w2_weighted_mean(np.clip(p, 0.0, None), tile)
    del a
    return pw, lvl


def run_stack(stack: str, iso: float, patch: int = PATCH, tile: int = TILE,
              tag: str = "", nproc: int = 6):
    d = os.path.join(ROOT, stack)
    frames = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
    k = len(frames)
    jobs = [(os.path.join(d, f), patch, tile) for f in frames]
    t0 = time.time()
    with Pool(nproc) as pool:
        res = pool.map(measure_frame, jobs, chunksize=1)
    power = np.stack([r[0] for r in res])  # (K, P, B)
    level = np.stack([r[1] for r in res])  # (K, P)
    dt = time.time() - t0
    name = f"tfs-{stack}{tag}.npz"
    np.savez_compressed(
        os.path.join(OUT, name),
        power=power,
        level=level,
        frames=np.array(frames),
        centres=np.array(CENTRES),
        bands=np.array(BAND_NAMES),
        iso=np.float64(iso),
        patch=np.int64(patch),
        tile=np.int64(tile),
    )
    print(f"  {stack:16s} K={k:4d} patches={power.shape[1]} "
          f"{dt:7.1f}s ({dt / max(k, 1):.2f} s/frame) -> {name}", flush=True)
    return name


def main() -> None:
    with open(os.path.join(OUT, "exif-census.json"), encoding="utf-8") as fh:
        census = {c["stack"]: c for c in json.load(fh)}
    # `n` in the census counts every file exiftool saw (some stacks carry JPGs
    # alongside the ARWs); the ARW count from disk is authoritative.
    narw = {
        s: len([f for f in os.listdir(os.path.join(ROOT, s)) if f.lower().endswith(".arw")])
        for s in census
    }
    order = sorted(census, key=lambda s: narw[s])
    only = sys.argv[1:] or None
    print(f"patch={PATCH} GQ samples ({2 * PATCH - 1} sensor px), tile={TILE}, "
          f"{len(CENTRES)} patches/frame, bands={BAND_NAMES}", flush=True)
    for stack in order:
        if only and stack not in only:
            continue
        iso_hist = census[stack]["iso"]
        iso = float(max(iso_hist, key=lambda k: iso_hist[k]))
        assert len(iso_hist) == 1, (stack, iso_hist)
        run_stack(stack, iso)


if __name__ == "__main__":
    main()
