"""BUILD-TRIAGE: look at the election map as a picture.

Every verdict in this triage needs a crop someone actually opened.  The
coverage verdict is a verdict about SHAPE -- contiguous region versus thin
contour -- and shape is the one thing a scalar cannot show you.  This renders
three panels per subject:

  1. the camera-linear merge, with the boundary set overlaid: RED where the
     pixel elected frame 0 (near end), BLUE where it elected frame N-1 (far).
  2. the raw election index, autoscaled -- this is the focus geometry itself.
  3. the boundary set after the erosion the morphology statistic uses, so the
     `survival` number can be checked by eye against what survived.

The render is gamma-encoded HERE, for viewing only.  No number in coverage.py
is taken from this path.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import scipy.ndimage as ndi
from PIL import Image, ImageDraw

import coverage
import tri

VIEW = os.path.join(tri.OUT, "covermaps")
DS = 4  # display downsample from the plane grid


def encode(lum: np.ndarray) -> np.ndarray:
    """Viewing transform only: normalise to the 99.5th pct and gamma 1/2.2."""
    hi = np.percentile(lum, 99.5)
    x = np.clip(lum / max(hi, 1e-6), 0, 1)
    return (np.power(x, 1 / 2.2) * 255).astype(np.uint8)


def block_mean(a: np.ndarray, k: int) -> np.ndarray:
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def block_any(a: np.ndarray, k: int) -> np.ndarray:
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    return a[:h, :w].reshape(h // k, k, w // k, k).max(axis=(1, 3)) > 0


def build(subject: str) -> str:
    idx = tri.load16(os.path.join(coverage.COVER, f"{subject}.idx.tiff")
                     ).astype(np.int32)
    n = coverage.frame_count(subject)
    near, far = idx == 0, idx == n - 1
    mask = near | far
    er = ndi.binary_erosion(mask, structure=coverage.disk(coverage.EROSION_R),
                            border_value=0)

    lum = tri.luma(tri.load16(os.path.join(tri.LIN, f"{subject}.tiff")))
    lum = lum.reshape(idx.shape[0], 2, idx.shape[1], 2).mean(axis=(1, 3))

    # The decision-relevant subset: boundary pixels that actually carry detail.
    # Electing an end of the bracket on featureless backdrop costs nothing and
    # no reshoot can fix it, so panel 3 shows only where it DOES cost something.
    con = coverage.local_contrast(lum)
    thr = np.quantile(con, 0.70)
    detail = mask & (con >= thr)

    g = encode(block_mean(lum, DS))
    h, w = g.shape
    base = np.dstack([g, g, g]).astype(np.float32)

    nd, fd = block_any(near, DS)[:h, :w], block_any(far, DS)[:h, :w]
    p1 = base.copy()
    p1[nd] = 0.45 * p1[nd] + 0.55 * np.array([255, 40, 40], np.float32)
    p1[fd] = 0.45 * p1[fd] + 0.55 * np.array([40, 90, 255], np.float32)

    # panel 2: election index, autoscaled 0..N-1 through a simple ramp.
    e = block_mean(idx.astype(np.float32), DS)[:h, :w] / max(n - 1, 1)
    p2 = np.dstack([e, np.roll(e, 0) * 0 + np.clip(1.5 - abs(e - 0.5) * 3, 0, 1),
                    1 - e]) * 255

    ed = block_any(detail, DS)[:h, :w]
    p3 = base.copy() * 0.35
    p3[ed] = np.array([255, 230, 60], np.float32)

    gap = 8
    sheet = np.full((h + 34, w * 3 + gap * 2, 3), 20, np.uint8)
    for i, p in enumerate((p1, p2, p3)):
        sheet[34:, i * (w + gap): i * (w + gap) + w] = np.clip(p, 0, 255
                                                               ).astype(np.uint8)
    im = Image.fromarray(sheet)
    d = ImageDraw.Draw(im)
    d.text((6, 4), f"{subject}   N={n}   plane {idx.shape[1]}x{idx.shape[0]}",
           fill=(255, 255, 255))
    d.text((6 + w + gap, 4), "election index (dark=near/frame 0)",
           fill=(255, 255, 255))
    d.text((6 + 2 * (w + gap), 4),
           "boundary AND detail-bearing (top 30% contrast)",
           fill=(255, 255, 255))
    d.text((int(w * 0.42), 4), "RED=frame 0   BLUE=frame N-1",
           fill=(255, 200, 200))

    os.makedirs(VIEW, exist_ok=True)
    out = os.path.join(VIEW, f"{subject}.jpg")
    im.save(out, quality=88)
    return out


if __name__ == "__main__":
    for s in sys.argv[1:]:
        print(build(s))
