"""M97e -- 1:1 crop comparison of the robust election against its own baseline.

ORCH asked for an image, not a table: "those stacks don't look too good yet."

This script does NOT pick the crop by hand. Hand-picking a crop is choosing the
evidence after seeing it, and on a change that alters 4-10% of pixels you can
find a flattering crop and a damning crop in the same render. Instead it finds
the WINDOW OF MAXIMUM CHANGE by a box filter over the absolute difference and
crops there. The same rule runs on the plant and on the trap, so the two crops
are comparable to each other.

Display transform: both arms are scaled by ONE factor derived from the BASELINE
only, then gamma 1/2.2. The soft arm never gets its own normalisation, because a
per-arm normalisation would hide or invent a brightness change.

The third panel is |difference| amplified by a stated fixed factor. It is the
only panel with a free parameter and the factor is printed on stdout.

Outputs: C:\\dev\\strehl-out\\M97e\\crops\\
"""

import sys
import json
from pathlib import Path

import numpy as np

try:
    import tifffile
except ImportError:
    tifffile = None
from PIL import Image

OUT = Path(r"C:\dev\strehl-out\M97e")
CROPS = OUT / "crops"
CROPS.mkdir(parents=True, exist_ok=True)

CROP = 420          # 1:1 pixels, no resampling anywhere
AMP = 8.0           # difference amplification, stated not tuned
MARGIN = 260        # keep the crop window off the frame edge


def load(path):
    if tifffile is not None:
        a = tifffile.imread(str(path))
    else:
        a = np.array(Image.open(path))
    return a.astype(np.float64)


def find_window(diff, crop, margin):
    """Integral-image box sum of the difference; return the crop origin."""
    m = diff.mean(axis=2) if diff.ndim == 3 else diff
    h, w = m.shape
    ii = np.zeros((h + 1, w + 1), dtype=np.float64)
    ii[1:, 1:] = m.cumsum(axis=0).cumsum(axis=1)
    step = 20
    ys = range(margin, h - crop - margin, step)
    xs = range(margin, w - crop - margin, step)
    best, by, bx = -1.0, margin, margin
    for y in ys:
        for x in xs:
            s = (ii[y + crop, x + crop] - ii[y, x + crop]
                 - ii[y + crop, x] + ii[y, x])
            if s > best:
                best, by, bx = s, y, x
    return by, bx, best / (crop * crop)


def tone(a, scale):
    v = np.clip(a * scale, 0.0, 1.0)
    return (np.power(v, 1.0 / 2.2) * 255.0 + 0.5).astype(np.uint8)


def label(img, text):
    """One-pixel-tall separator plus a text strip drawn with PIL."""
    from PIL import ImageDraw
    h = 18
    strip = Image.new("RGB", (img.shape[1], h), (16, 16, 16))
    ImageDraw.Draw(strip).text((4, 3), text, fill=(235, 235, 235))
    return np.vstack([np.array(strip), img])


def compare(name, base_path, arm_path, arm_label):
    base = load(base_path)
    arm = load(arm_path)
    if base.shape != arm.shape:
        raise SystemExit(f"shape mismatch {base.shape} vs {arm.shape}")

    diff = np.abs(arm - base)
    changed = (diff.max(axis=2) > 0).mean() if diff.ndim == 3 else (diff > 0).mean()

    y, x, dens = find_window(diff, CROP, MARGIN)

    # ONE scale, from the baseline, applied to both arms.
    scale = 1.0 / max(np.percentile(base[y:y + CROP, x:x + CROP], 99.5), 1.0)

    b = tone(base[y:y + CROP, x:x + CROP], scale)
    a = tone(arm[y:y + CROP, x:x + CROP], scale)
    d = np.clip(diff[y:y + CROP, x:x + CROP] * scale * AMP, 0.0, 1.0)
    d = (np.power(d, 1.0 / 2.2) * 255.0 + 0.5).astype(np.uint8)

    gap = np.full((CROP + 18, 8, 3), 32, dtype=np.uint8)
    panel = np.hstack([
        label(b, "OFF (= HEAD)"),
        gap,
        label(a, arm_label),
        gap,
        label(d, f"|diff| x{AMP:g}"),
    ])
    dst = CROPS / f"{name}.png"
    Image.fromarray(panel).save(dst)

    stats = {
        "stack": name,
        "crop_origin_xy": [int(x), int(y)],
        "crop_px": CROP,
        "changed_pixel_fraction_whole_frame": float(changed),
        "mean_abs_diff_dn_in_crop": float(dens),
        "max_abs_diff_dn_whole_frame": float(diff.max()),
        "amplification": AMP,
        "png": str(dst),
    }
    print(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    results = []
    # TRAP FIRST. ORCH asked for the trap before the plant.
    results.append(compare(
        "trap-coffee-bean",
        OUT / "coffee-bean-off.tif",
        OUT / "coffee-bean-soft-paired.tif",
        "SOFT (robust election)",
    ))
    results.append(compare(
        "plant-foam",
        OUT / "foam-off100.tif",
        OUT / "foam-soft100-paired.tif",
        "SOFT (robust election)",
    ))
    (CROPS / "crop-stats.json").write_text(json.dumps(results, indent=2))
    print("wrote", CROPS / "crop-stats.json")
