"""Render visual diagnostics for the frozen coffee-bean flat sites."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import uniform_filter

import measure


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagnostics"


def center_crop(image: np.ndarray, size: int) -> np.ndarray:
    y = (image.shape[0] - size) // 2
    x = (image.shape[1] - size) // 2
    return image[y : y + size, x : x + size]


def highpass(image: np.ndarray) -> np.ndarray:
    return image / uniform_filter(image, 9) - 1.0


def residual_image(residual: np.ndarray, sigma: float) -> np.ndarray:
    return (np.clip(residual / (4.0 * sigma) + 0.5, 0.0, 1.0) * 255).astype(
        np.uint8
    )


def panel(site: dict, subject: dict) -> None:
    fork_y, fork_x, fork_size = site["boxes_y_x_size"]["fork"]
    strehl_y, strehl_x, strehl_size = site["boxes_y_x_size"]["strehl"]
    fork = measure.linear_green_box(
        measure.COFFEE_FORK, fork_y, fork_x, fork_size
    )
    strehl = measure.linear_green_box(
        measure.COFFEE_STREHL, strehl_y, strehl_x, strehl_size
    )
    fork_hp = highpass(fork)
    strehl_hp = highpass(strehl)
    fork_sigma = float(fork_hp.std())
    strehl_sigma = float(strehl_hp.std())
    common = max(fork_sigma, strehl_sigma)
    tiles = [
        residual_image(fork_hp, fork_sigma),
        residual_image(strehl_hp, strehl_sigma),
        residual_image(fork_hp, common),
        residual_image(strehl_hp, common),
    ]
    tiles = [center_crop(tile, 360) for tile in tiles]
    labels = [
        f"fork own sigma {fork_sigma:.5f}",
        f"strehl own sigma {strehl_sigma:.5f}",
        "fork common sigma",
        "strehl common sigma",
    ]
    gap = 8
    top = 26
    canvas = np.full(
        (360 + top, 4 * 360 + 3 * gap, 3), 30, dtype=np.uint8
    )
    output = Image.fromarray(canvas)
    draw = ImageDraw.Draw(output)
    cursor = 0
    for tile, label in zip(tiles, labels):
        output.paste(Image.fromarray(tile).convert("RGB"), (cursor, top))
        draw.text((cursor + 3, 6), label, fill=(255, 255, 120))
        cursor += 360 + gap
    output.save(
        OUT
        / (
            f"coffee-rank{site['rank']:02d}-"
            f"y{site['reference_y']}-x{site['reference_x']}.png"
        )
    )


def main() -> None:
    result = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    subject = next(
        item for item in result["subjects"] if item["subject"] == "coffee-bean"
    )
    OUT.mkdir(exist_ok=True)
    for site in subject["sites"]:
        panel(site, subject)
    print(f"wrote {len(subject['sites'])} panels to {OUT}")


if __name__ == "__main__":
    main()
