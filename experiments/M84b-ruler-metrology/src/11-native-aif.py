"""M84b step 11 - native-resolution all-in-focus over a ROI, NAVIGATION ONLY.

Streams every frame of a stack at full quad-grid resolution, keeps only a ROI,
and accumulates a running best-response composite plus the response cube reduced
to a column profile. Memory stays at a few tens of MB.

NOTHING HERE IS A MILESTONE CLAIM. The composite uses a per-pixel argmax, which
rule 4 forbids as evidence. It exists so the tick localiser can be designed
against the real subject (rule 13). The registered measurements in later steps
use the spatially aggregated statistic of pre-registration section 6.1.

Also writes `11-colprof-<tag>.npy`, shape (N, W), the level-normalised squared
gradient averaged down the ROI's rows. That IS the registered aggregated
statistic's raw material and later steps read it.

Reads READ-ONLY from D:\\personal\\macro.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import rawpy
from PIL import Image
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")


def quad_green(path: pathlib.Path) -> tuple[np.ndarray, int]:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black, black


def stretch(a: np.ndarray, lo: float = 1.0, hi: float = 99.0) -> np.ndarray:
    p0, p1 = np.percentile(a, [lo, hi])
    if p1 <= p0:
        p1 = p0 + 1.0
    return np.clip((a - p0) / (p1 - p0), 0.0, 1.0)


def main(argv: list[str]) -> int:
    if len(argv) != 7:
        print("usage: 11-native-aif.py <stack> <x0> <y0> <w> <h> <tag>", file=sys.stderr)
        return 2
    stack, x0, y0, w, h, tag = argv[1], *map(int, argv[2:6]), argv[6]
    OUT.mkdir(exist_ok=True)
    frames = sorted((CORPUS / stack).glob("*.ARW"))
    n = len(frames)
    print(f"{stack}: {n} frames, ROI [{x0},{y0},{w},{h}]")

    best_r = np.full((h, w), -np.inf, np.float32)
    best_v = np.zeros((h, w), np.float32)
    best_i = np.zeros((h, w), np.int16)
    med_acc = np.zeros((h, w), np.float32)
    colprof = np.zeros((n, w), np.float32)
    levels = np.zeros(n, np.float32)

    t0 = time.time()
    for i, fp in enumerate(frames):
        plane, _ = quad_green(fp)
        sub = np.ascontiguousarray(plane[y0 : y0 + h, x0 : x0 + w])
        del plane
        np.clip(sub, 1.0, None, out=sub)
        levels[i] = float(sub.mean())
        gx = ndimage.sobel(sub, axis=1)
        gy = ndimage.sobel(sub, axis=0)
        e = gx * gx + gy * gy
        lvl = ndimage.uniform_filter(sub, 33)
        r = ndimage.uniform_filter(e, 33) / (lvl * lvl)
        colprof[i] = r.mean(axis=0)
        med_acc += r
        hit = r > best_r
        best_r[hit] = r[hit]
        best_v[hit] = sub[hit]
        best_i[hit] = i
        if i % 50 == 0:
            print(f"  frame {i:3d}  {time.time() - t0:6.1f}s  level {levels[i]:8.1f}")

    conf = best_r / (med_acc / n + 1e-12)
    Image.fromarray((stretch(best_v) * 255 + 0.5).astype(np.uint8)).save(
        OUT / f"11-aif-{tag}.png"
    )
    Image.fromarray(
        (best_i.astype(np.float32) / max(n - 1, 1) * 255 + 0.5).astype(np.uint8)
    ).save(OUT / f"11-idx-{tag}.png")
    Image.fromarray((stretch(np.log10(conf)) * 255 + 0.5).astype(np.uint8)).save(
        OUT / f"11-conf-{tag}.png"
    )
    np.save(OUT / f"11-colprof-{tag}.npy", colprof)
    np.save(OUT / f"11-bestv-{tag}.npy", best_v)
    np.save(OUT / f"11-besti-{tag}.npy", best_i)
    np.save(OUT / f"11-conf-{tag}.npy", conf.astype(np.float32))
    (OUT / f"11-meta-{tag}.json").write_text(
        json.dumps(
            {
                "stack": stack,
                "roi": [x0, y0, w, h],
                "n_frames": n,
                "frames": [f.name for f in frames],
                "levels": levels.tolist(),
                "operator": "uniform_filter(sobel_x^2+sobel_y^2,33) / uniform_filter(I,33)^2",
                "note": "argmax composite is NAVIGATION ONLY, not evidence (rule 4)",
            },
            indent=1,
        )
    )
    print(f"  done in {time.time() - t0:.1f}s; conf median {np.median(conf):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
