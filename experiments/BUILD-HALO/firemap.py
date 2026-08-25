"""Full-frame overlay of where the bimodality detector fires.

Mandate (B)'s first deliverable, and a gate: if firing lands on the rim, the
two-layer model is the right model and unmixing is worth building. If it fires
everywhere or nowhere in particular, the model is wrong and must not be forced.

Deliberately full-frame. The per-band firing table already says firing is
monotone in the collapsed radius, but a table cannot show whether the firing
pixels form a coherent rim tracing the silhouette or a scatter of speckle that
happens to correlate with it. Those have identical statistics and completely
different consequences, and only a picture separates them.
"""

from __future__ import annotations

import argparse
import os

import numpy as np

from fullframe import box_downsample, develop, read16, write_png


def load_raw(path: str, w: int, h: int, full: float) -> np.ndarray:
    a = np.fromfile(path, dtype="<u2")
    assert a.size == w * h, f"{path}: {a.size} values, expected {w * h}"
    return a.reshape(h, w).astype(np.float32) / 65535.0 * full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True, help="directory of .raw maps")
    ap.add_argument("--base", required=True, help="16-bit linear TIFF to overlay on")
    ap.add_argument("--gain", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--fires", type=float, default=1.5)
    a = ap.parse_args()

    base = read16(a.base)
    h, w = base.shape[:2]
    z2 = load_raw(os.path.join(a.dump, "second_mode_z.raw"), w, h, 6.0)
    z1 = load_raw(os.path.join(a.dump, "first_mode_z.raw"), w, h, 6.0)

    # BOTH modes must clear the baseline. Requiring only the second is what made
    # the first detector fire on 54.2% of clean ground: where neither peak is
    # real the ratio tends to 1 by noise alone, so it was measuring the ABSENCE
    # of a dominant peak rather than the presence of two.
    fires = ((z2 >= a.fires) & (z1 >= a.fires)).astype(np.float32)

    # Downsample the MASK, not a thresholded picture of it: at 1400 px a 2 px
    # rim is sub-pixel, and nearest-neighbour sampling would drop most of it and
    # make a continuous rim look like a dashed one.
    small_base = box_downsample(base, a.width)
    small_fire = box_downsample(fires[:, :, None], a.width)[:, :, 0]

    rgb = develop(small_base, a.gain).astype(np.float32)
    # Desaturate underneath so the overlay reads against a busy subject.
    grey = rgb.mean(axis=2, keepdims=True)
    rgb = 0.45 * rgb + 0.55 * grey
    alpha = np.clip(small_fire, 0.0, 1.0)[:, :, None]
    hot = np.array([255.0, 40.0, 40.0], np.float32)
    out = np.clip(rgb * (1 - alpha) + hot * alpha, 0, 255).astype(np.uint8)

    write_png(a.out, out)
    print(
        f"wrote {a.out}  fires on {100.0 * fires.mean():.2f}% of the plane "
        f"(z1 and z2 both >= {a.fires})"
    )


if __name__ == "__main__":
    main()
