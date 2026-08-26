"""Crop the restoration next to its reference, large, for looking at.

Ringing is the failure mode of any deconvolution and it is not reliably visible
in a summary statistic: a high-pass metric scores overshoot as a WIN, which is
exactly the trap this project walked into in section 13. So the picture is the
instrument here, and it is written large on purpose. The standing discipline in
BUILD-SHARP.md is that a retraction was already forced once by reading a 900 px
crop; the rule is not "look at the picture", it is "look at a large enough
picture".

Also prints a numeric overshoot probe beside each crop: the maximum excursion
BEYOND the local flat level within a few pixels of the strongest edge in the
crop. Ringing is a signed, localised overshoot, so it has a number, and the
number and the picture have to agree before either is believed.
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import tifffile


def to_srgb8(a: np.ndarray) -> np.ndarray:
    x = np.clip(a / 65535.0, 0.0, 1.0)
    s = np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return np.clip(s * 255.0, 0, 255).astype(np.uint8)


def strongest_edge(g: np.ndarray) -> tuple[int, int]:
    gy, gx = np.gradient(g.astype(np.float64))
    m = np.hypot(gx, gy)
    m[:40, :] = m[-40:, :] = m[:, :40] = m[:, -40:] = 0
    idx = int(np.argmax(m))
    return idx // g.shape[1], idx % g.shape[1]


def overshoot(ref: np.ndarray, arm: np.ndarray) -> dict:
    """Excursion beyond the reference's own local range, near strong edges.

    A zero-phase contrast boost moves values toward the local extremes. Ringing
    is when it moves them PAST the extremes, into levels the reference never
    reached anywhere in the neighbourhood. That is the quantity here: for every
    pixel, how far outside the reference's local [min, max] window did the arm
    land, in DN and as a fraction of the local range.
    """
    from scipy.ndimage import maximum_filter, minimum_filter  # noqa: PLC0415

    lo = minimum_filter(ref, size=9)
    hi = maximum_filter(ref, size=9)
    rng = np.maximum(hi - lo, 1.0)
    over = np.maximum(arm - hi, 0.0) + np.maximum(lo - arm, 0.0)
    frac = over / rng
    strong = rng > np.percentile(rng, 99.0)
    return {
        "max_overshoot_dn": float(over.max()),
        "p99.99_overshoot_dn": float(np.percentile(over, 99.99)),
        "mean_overshoot_frac_at_strong_edges": float(frac[strong].mean()),
        "p99_overshoot_frac_at_strong_edges": float(np.percentile(frac[strong], 99.0)),
        "pixels_overshooting_pct": float(100.0 * np.mean(over > 0.5)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=760, help="crop side; the pair is 2x this wide")
    args = ap.parse_args()

    ref = tifffile.imread(args.ref).astype(np.float64)
    arm = tifffile.imread(args.arm).astype(np.float64)
    assert ref.shape == arm.shape, f"{ref.shape} vs {arm.shape}"
    g = ref[:, :, 1] if ref.ndim == 3 else ref

    print(f"overshoot probe, whole frame, green plane, {os.path.basename(args.arm)}:")
    stats = overshoot(g, arm[:, :, 1] if arm.ndim == 3 else arm)
    for k, v in stats.items():
        print(f"  {k:38s} {v:12.5f}")

    y, x = strongest_edge(g)
    s = args.size
    y0 = int(np.clip(y - s // 2, 0, g.shape[0] - s))
    x0 = int(np.clip(x - s // 2, 0, g.shape[1] - s))
    print(f"  strongest edge at (y={y}, x={x}); crop origin ({y0}, {x0}) size {s}")

    a = to_srgb8(ref[y0 : y0 + s, x0 : x0 + s])
    b = to_srgb8(arm[y0 : y0 + s, x0 : x0 + s])
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
        b = np.stack([b] * 3, -1)
    gap = np.zeros((s, 8, 3), np.uint8)
    gap[:, :, 0] = 255
    pair = np.concatenate([a, gap, b], axis=1)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    from PIL import Image  # noqa: PLC0415

    Image.fromarray(pair).save(args.out)
    print(f"  wrote {args.out}  ({pair.shape[1]} x {pair.shape[0]} px; left = ref, right = arm)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
