"""M84b step 10 - geometry reconnaissance, NAVIGATION ONLY.

Builds an all-in-focus composite of the angled stack from the q4 cache so the
true scene geometry can be read at a glance, and dumps contrast-stretched native
crops at chosen (frame, x, y) so the tick localiser can be designed against the
real subject rather than an assumed one (rule 13).

NOTHING HERE IS A MILESTONE CLAIM. The composite uses a per-pixel argmax, which
rule 4 forbids as evidence; it is used here purely to see the scene. Every
registered measurement uses the spatially aggregated statistic of the
pre-registration section 6.1.

Reads READ-ONLY from D:\\personal\\macro and from cache/.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy
from PIL import Image
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
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


def stretch(a: np.ndarray, lo: float = 0.5, hi: float = 99.5) -> np.ndarray:
    p0, p1 = np.percentile(a, [lo, hi])
    if p1 <= p0:
        p1 = p0 + 1.0
    return np.clip((a - p0) / (p1 - p0), 0.0, 1.0)


def png(path: pathlib.Path, a01: np.ndarray) -> None:
    Image.fromarray((a01 * 255.0 + 0.5).astype(np.uint8)).save(path)


def composite(stack: str) -> None:
    cube = np.load(CACHE / f"{stack}-q4.npy").astype(np.float32)
    meta = json.loads((CACHE / f"{stack}-meta.json").read_text())
    cube -= float(meta["black_level"])
    np.clip(cube, 1.0, None, out=cube)
    n, h, w = cube.shape
    print(f"{stack}: cube {cube.shape}, black {meta['black_level']}")

    resp = np.empty_like(cube)
    for i in range(n):
        f = cube[i]
        gx = ndimage.sobel(f, axis=1)
        gy = ndimage.sobel(f, axis=0)
        e = gx * gx + gy * gy
        lvl = ndimage.uniform_filter(f, 25)
        resp[i] = ndimage.uniform_filter(e, 25) / (lvl * lvl)

    idx = np.argmax(resp, axis=0)
    best = np.take_along_axis(cube, idx[None], axis=0)[0]
    conf = resp.max(axis=0) / (np.median(resp, axis=0) + 1e-12)

    png(OUT / f"10-aif-{stack}.png", stretch(best))
    png(OUT / f"10-aifidx-{stack}.png", idx.astype(np.float32) / max(n - 1, 1))
    png(OUT / f"10-aifconf-{stack}.png", stretch(np.log10(conf), 1, 99))
    np.save(OUT / f"10-aifidx-{stack}.npy", idx.astype(np.int16))
    np.save(OUT / f"10-aifconf-{stack}.npy", conf.astype(np.float32))
    print(f"  wrote 10-aif-{stack}.png ; conf median {np.median(conf):.2f}")


def crop(stack: str, frame: int, x0: int, y0: int, w: int, h: int, tag: str) -> None:
    frames = sorted((CORPUS / stack).glob("*.ARW"))
    plane, _ = quad_green(frames[frame])
    sub = plane[y0 : y0 + h, x0 : x0 + w]
    png(OUT / f"10-crop-{tag}.png", stretch(sub, 1, 99))
    print(f"  crop {tag}: frame {frame} [{x0},{y0},{w},{h}] -> {sub.shape}")


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    what = argv[1] if len(argv) > 1 else "all"
    if what in ("all", "aif"):
        composite("highly-angled-ruler-mm-cpl")
        composite("flat-on-ruler-cpl")
    if what in ("all", "crop"):
        for spec in argv[2:]:
            stack, fr, x0, y0, w, h, tag = spec.split(",")
            crop(stack, int(fr), int(x0), int(y0), int(w), int(h), tag)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

