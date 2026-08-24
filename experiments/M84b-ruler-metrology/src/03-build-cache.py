"""M84 step 03 - decode-once cache.

Decodes every frame of a stack ONCE and writes two durable artefacts:

  * `cache/<stack>-q4.npy`   uint16, (N, H/4, W/4) box-mean of the quad-grid green
                              plane (pre-black-subtraction, so it is lossless in
                              intent and re-derivable), for whole-frame geometry.
  * `cache/<stack>-meta.json` black level, white level, plane shape, frame names.

Nothing here is a milestone claim; it is a cache. Every downstream script states
which cache it read and re-derives the numbers it quotes.

Reads READ-ONLY from D:\\personal\\macro. Rule 32 idiom: copy inside the `with`.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import rawpy

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache"
CORPUS = pathlib.Path(r"D:\personal\macro")


def quad_green(path: pathlib.Path) -> tuple[np.ndarray, int, int]:
    """Green quad plane (G1+G2)/2 in DN, NOT black-subtracted, plus levels."""
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
        white = int(raw.white_level)
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2), black, white


def box4(plane: np.ndarray) -> np.ndarray:
    h, w = plane.shape
    h -= h % 4
    w -= w % 4
    return plane[:h, :w].reshape(h // 4, 4, w // 4, 4).mean(axis=(1, 3))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: 03-build-cache.py <stack>", file=sys.stderr)
        return 2
    stack = argv[1]
    d = CORPUS / stack
    frames = sorted(d.glob("*.ARW"))
    if not frames:
        print(f"FATAL: {d} holds no ARW files", file=sys.stderr)
        return 2
    CACHE.mkdir(parents=True, exist_ok=True)

    p0, black, white = quad_green(frames[0])
    s0 = box4(p0)
    arr = np.zeros((len(frames), s0.shape[0], s0.shape[1]), dtype=np.uint16)
    t0 = time.perf_counter()
    for i, f in enumerate(frames):
        pl, b, wl = quad_green(f)
        if b != black or wl != white:
            print(f"FATAL: levels move at frame {i}: {b}/{wl} vs {black}/{white}", file=sys.stderr)
            return 3
        arr[i] = np.rint(box4(pl)).astype(np.uint16)
        if (i + 1) % 25 == 0 or i + 1 == len(frames):
            print(f"  {i + 1}/{len(frames)} {time.perf_counter() - t0:.1f}s", flush=True)
    np.save(CACHE / f"{stack}-q4.npy", arr)
    meta = {
        "stack": stack,
        "n_frames": len(frames),
        "frames": [f.name for f in frames],
        "black_level": black,
        "white_level": white,
        "quad_plane_shape": [int(p0.shape[0]), int(p0.shape[1])],
        "q4_shape": [int(x) for x in arr.shape],
        "note": "q4 is a 4x4 box mean of the quad-grid green plane, NOT black-subtracted",
    }
    (CACHE / f"{stack}-meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {stack}: {arr.shape} black={black} white={white}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
