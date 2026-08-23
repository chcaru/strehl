"""Loading stacks -- real or simulated -- behind one interface.

The committed analysis scripts read real stacks with `rawpy` and take
`raw_image_visible`.  A simulated stack presents the same thing: a (K, H, W)
uint16 CFA array with `raw_pattern = [[0,1],[3,2]]`, black 512, usable white
15360.  Nothing downstream needs to know which it is.

`green_luma` and `green_value` reproduce `m9-support/src/tile.rs` exactly:

  * **luma** (what the focus measure eats): `0.5 * (max(G1-512,0) +
    max(G2-512,0))` -- clamped, because a negative signal has no meaning in
    the noise model that normalises it;
  * **green** (what the merge outputs and the sigma is taken over):
    `0.5 * ((G1-512) + (G2-512))` -- **not** clamped, because clamping the
    evaluation channel would truncate the very noise distribution being
    measured.

Getting those two the wrong way round is a silent, plausible-looking bug: the
ratio would be biased low on dark ROIs and the port would look *better* than
the original.
"""

from __future__ import annotations

import glob
import os

import numpy as np

BLACK = 512.0


def stack_paths(directory: str, pattern: str = "*.ARW") -> list[str]:
    p = sorted(glob.glob(os.path.join(directory, pattern)))
    if not p:
        p = sorted(glob.glob(os.path.join(directory, "*.[aA][rR][wW]")))
    assert p, f"no frames in {directory}"
    return p


def load_real(directory: str, limit: int | None = None,
              pattern: str = "*.ARW") -> np.ndarray:
    import rawpy

    paths = stack_paths(directory, pattern)
    if limit:
        paths = paths[:limit]
    out = []
    for p in paths:
        with rawpy.imread(p) as r:
            out.append(np.asarray(r.raw_image_visible, dtype=np.uint16).copy())
    return np.stack(out)


def iso_of(directory: str, pattern: str = "*.ARW") -> float:
    import exifread

    p = stack_paths(directory, pattern)[0]
    with open(p, "rb") as fh:
        tags = exifread.process_file(fh, details=False,
                                     stop_tag="EXIF ISOSpeedRatings")
    return float(str(tags["EXIF ISOSpeedRatings"]).strip("[]"))


def green_planes(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """`(G1, G2)` for `raw_pattern = [[0,1],[3,2]]`."""
    return raw[..., 0::2, 1::2], raw[..., 1::2, 0::2]


def green_luma(raw: np.ndarray) -> np.ndarray:
    g1, g2 = green_planes(raw)
    return 0.5 * (np.maximum(g1.astype(np.float64) - BLACK, 0.0)
                  + np.maximum(g2.astype(np.float64) - BLACK, 0.0))


def green_value(raw: np.ndarray) -> np.ndarray:
    g1, g2 = green_planes(raw)
    return 0.5 * ((g1.astype(np.float64) - BLACK)
                  + (g2.astype(np.float64) - BLACK))


class Roi:
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)

    @classmethod
    def parse(cls, s: str) -> "Roi":
        return cls(*[int(v) for v in s.split(",")])

    def __str__(self):
        return f"{self.x},{self.y},{self.w},{self.h}"


def tiles(raw: np.ndarray, roi: Roi, margin: int):
    """Return `(luma_tile, value_roi)` -- `(K, H+2m, W+2m)` and `(K, H, W)`.

    Asserts rather than clamps if the tile leaves the plane (discipline 191):
    a silently shrunk tile changes the border policy of every box mean inside
    it, which is exactly the kind of difference that would show up as a
    plausible-but-wrong number.
    """
    g1, g2 = green_planes(raw)
    ph, pw = g1.shape[-2], g1.shape[-1]
    ty, tx = roi.y - margin, roi.x - margin
    th, tw = roi.h + 2 * margin, roi.w + 2 * margin
    assert ty >= 0 and tx >= 0 and ty + th <= ph and tx + tw <= pw, (
        f"tile {tx},{ty},{tw},{th} leaves the {pw}x{ph} green plane")
    sub = raw[..., 2 * ty:2 * (ty + th), 2 * tx:2 * (tx + tw)]
    luma = green_luma(sub)
    val = green_value(
        raw[..., 2 * roi.y:2 * (roi.y + roi.h), 2 * roi.x:2 * (roi.x + roi.w)])
    return luma, val
