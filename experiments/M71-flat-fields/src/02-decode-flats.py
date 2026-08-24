"""M71 step 02 -- decode the 360 flats into per-group-half CFA statistics.

Runs the mandatory drift normalisation at the point of decode: every frame is
divided by ITS OWN per-plane spatial mean before it enters any temporal
accumulator. Global illumination drift is a per-frame scalar and this is what
divides it out. What survives is either sensor noise or SPATIALLY STRUCTURED
drift, and separating those two is PR-8.

Structure recovered in step 00 and assumed here:
  9 shutter speeds x (20 frames CPL-on, ~4.7 min intermission, 20 frames CPL-off)

Rule 32 is load-bearing in this file. `raw_image_visible` is a VIEW into
LibRaw's buffer and is invalid the instant the `with` block exits; use-after-
free does not reliably crash. Every read of it below allocates and copies on
the same line, inside the block.

Rule 7 / M68: visible geometry is (4688, 7028). raw_pattern [[0,1],[3,2]] with
color_desc RGBG gives R at (even,even), G1 at (even,odd), G2 at (odd,even),
B at (odd,odd) -- so G1 and G2 share neither a row parity nor a column parity,
which is what makes them the cleanest pair for a row/column-blind null.

No demosaicing anywhere. Standing project rule, and demosaicing would destroy
exactly the per-pixel statistics this milestone exists to measure.

Outputs (all regenerable, all .npy hence gitignored by format):
  out/cache/{tag}-{plane}-mean.npy  float32 (2344,3514) normalised temporal mean
  out/cache/{tag}-{plane}-var.npy   float32 (2344,3514) normalised temporal variance
  out/cache/{tag}-blocks.npy        float32 (4,20,73,109) per-frame 32x32 block
                                    means of the normalised frames. White noise
                                    is suppressed 1024x here, so this isolates
                                    low-frequency per-frame structure -- the
                                    instrument for PR-8 and for PR-6's placebo.
  data/02-frames.json               per-frame scalars, no pixels
"""

from __future__ import annotations

import csv
import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
CSV_PATH = HERE / "data" / "exif-all.csv"
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "02-frames.json"

BLACK = 512.0
WHITE = 15360.0          # AGENTS.md rig section; the container max is 16383
CONTAINER_MAX = 16383.0
PLANES = ("R", "G1", "G2", "B")
BLK = 32                 # block size on the PLANE lattice (= 64 sensor px)
NB_R, NB_C = 73, 109     # 2344//32, 3514//32


def parse_dt(s: str):
    from datetime import datetime
    date, rest = s.split(" ", 1)
    y, mo, d = date.split(":")
    if rest[-6] in "+-":
        rest = rest[:-6]
    hms, frac = rest.split(".") if "." in rest else (rest, "0")
    h, mi, se = hms.split(":")
    return datetime(int(y), int(mo), int(d), int(h), int(mi), int(se),
                    int(round(float("0." + frac) * 1e6)))


def planes_of(vis: np.ndarray) -> dict[str, np.ndarray]:
    """Split a visible CFA frame into its four planes. No interpolation."""
    return {
        "R": vis[0::2, 0::2],
        "G1": vis[0::2, 1::2],
        "G2": vis[1::2, 0::2],
        "B": vis[1::2, 1::2],
    }


def block_mean(a: np.ndarray) -> np.ndarray:
    return (a[: NB_R * BLK, : NB_C * BLK]
            .reshape(NB_R, BLK, NB_C, BLK)
            .mean(axis=(1, 3)))


def main() -> None:
    rows = [r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig"))
            if Path(r["Directory"]).name == "flat-fields"]
    assert len(rows) == 360, f"expected 360 flats, got {len(rows)}"
    for r in rows:
        r["_dt"] = parse_dt(r["SubSecDateTimeOriginal"])
        r["_exp"] = float(Fraction(r["ExposureTime"]))

    groups: dict[float, list] = {}
    for r in rows:
        groups.setdefault(r["_exp"], []).append(r)
    for k in groups:
        groups[k].sort(key=lambda r: r["_dt"])
        assert len(groups[k]) == 40, f"group {k} has {len(groups[k])} frames"
    assert len(groups) == 9, f"expected 9 exposure groups, got {len(groups)}"

    CACHE.mkdir(parents=True, exist_ok=True)
    frame_records = []
    t_start = time.time()

    for exp in sorted(groups):
        for half, sl in (("A", slice(0, 20)), ("B", slice(20, 40))):
            frames = groups[exp][sl]
            tag = f"e{Fraction(exp).denominator if Fraction(exp).numerator == 1 else exp}-{half}"
            nsum = {p: np.zeros((2344, 3514), np.float64) for p in PLANES}
            nsq = {p: np.zeros((2344, 3514), np.float64) for p in PLANES}
            clipmap = {p: np.zeros((2344, 3514), np.uint8) for p in PLANES}
            blocks = np.zeros((4, 20, NB_R, NB_C), np.float32)
            means = {p: [] for p in PLANES}

            for j, r in enumerate(frames):
                path = str(Path(r["SourceFile"]))
                with rawpy.imread(path) as raw:
                    # Rule 32: allocate and copy INSIDE the with block.
                    vis = raw.raw_image_visible.astype(np.float32)
                    bl = list(raw.black_level_per_channel)
                assert vis.shape == (4688, 7028), f"{path}: {vis.shape}"
                assert set(bl) == {512}, f"{path}: black {bl}"
                n_hi = int((vis >= WHITE).sum())
                n_max = int((vis >= CONTAINER_MAX).sum())
                vmin, vmax = float(vis.min()), float(vis.max())
                vis -= BLACK
                rec = {"file": r["FileName"], "exp": exp, "half": half,
                       "t": r["SubSecDateTimeOriginal"],
                       "raw_min": vmin, "raw_max": vmax,
                       "frac_ge_white": n_hi / vis.size,
                       "frac_ge_container": n_max / vis.size}
                pl = planes_of(vis)
                for pi, p in enumerate(PLANES):
                    a = pl[p]
                    m = float(a.mean())
                    means[p].append(m)
                    rec[f"mean_{p}"] = m
                    rec[f"max_{p}"] = float(a.max())
                    hi = a >= (WHITE - BLACK)
                    rec[f"clip_{p}"] = float(hi.mean())
                    clipmap[p] += hi
                    a = a / np.float32(m)
                    nsum[p] += a
                    nsq[p] += np.square(a, dtype=np.float64)
                    blocks[pi, j] = block_mean(a)
                frame_records.append(rec)
                del vis, pl

            n = 20.0
            for p in PLANES:
                mu = (nsum[p] / n)
                var = (nsq[p] - n * mu * mu) / (n - 1.0)
                np.save(CACHE / f"{tag}-{p}-mean.npy", mu.astype(np.float32))
                np.save(CACHE / f"{tag}-{p}-var.npy",
                        np.maximum(var, 0.0).astype(np.float32))
                np.save(CACHE / f"{tag}-{p}-clip.npy", clipmap[p])
            np.save(CACHE / f"{tag}-blocks.npy", blocks)
            print(f"{tag:10s} exp={exp:.5f}s  "
                  + "  ".join(f"{p}={np.mean(means[p]):8.1f}" for p in PLANES)
                  + "  clip%=" + "/".join(
                      f"{100 * (clipmap[p] > 0).mean():.1f}" for p in PLANES)
                  + f"  [{time.time() - t_start:5.1f}s]")
            sys.stdout.flush()

    OUT.write_text(json.dumps(frame_records, indent=1), encoding="utf-8")
    print(f"\n{len(frame_records)} frames -> {OUT}   {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
