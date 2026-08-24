"""Build native-resolution side-by-side crops so a human can look.

Comparing crops from memory is how I talked myself into a sharpness win earlier
tonight that was not there. Everything goes side by side, at 1:1, or it does not
get claimed.

Picks the highest-detail tile in each of several radius bands, because a scale
misregistration grows with radius and the interesting comparison is where the
subject and the error overlap.
"""

import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw


def pick(g: np.ndarray, r_lo: float, r_hi: float, size: int) -> tuple[int, int]:
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0) / np.hypot(h / 2.0, w / 2.0)
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    T = size
    ny, nx = (h - 1) // T, (w - 1) // T
    e = gy[: ny * T, : nx * T].reshape(ny, T, nx, T).mean(axis=(1, 3))
    rt = r[: ny * T, : nx * T].reshape(ny, T, nx, T).mean(axis=(1, 3))
    m = (rt >= r_lo) & (rt < r_hi)
    if not m.any():
        return h // 2, w // 2
    e = np.where(m, e, -1.0)
    iy, ix = np.unravel_index(int(np.argmax(e)), e.shape)
    return iy * T, ix * T


def to8(a: np.ndarray) -> np.ndarray:
    return (a >> 8).astype(np.uint8)


def main(argv: list[str]) -> int:
    out, a_lbl, a_p, b_lbl, b_p = argv[1], argv[2], argv[3], argv[4], argv[5]
    A, B = tifffile.imread(a_p), tifffile.imread(b_p)
    g = A[:, :, 1].astype(np.float32)
    size = 420
    bands = [(0.05, 0.20, "centre"), (0.35, 0.50, "mid"), (0.55, 0.70, "outer")]

    panels = []
    for lo, hi, name in bands:
        y, x = pick(g, lo, hi, size)
        ca, cb = to8(A[y : y + size, x : x + size]), to8(B[y : y + size, x : x + size])
        strip = np.concatenate([ca, cb], axis=1)
        im = Image.fromarray(strip)
        d = ImageDraw.Draw(im)
        d.text((6, 4), f"{a_lbl}   [{name} r, y={y} x={x}]", fill=(255, 255, 0))
        d.text((size + 6, 4), f"{b_lbl}", fill=(255, 255, 0))
        d.line([(size, 0), (size, size)], fill=(255, 255, 0), width=2)
        panels.append(np.asarray(im))
        print(f"{name:>7} band: tile at y={y} x={x}")

    full = np.concatenate(panels, axis=0)
    Image.fromarray(full).save(out)
    print(f"wrote {out}  ({full.shape[1]}x{full.shape[0]}, 1:1 native pixels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
