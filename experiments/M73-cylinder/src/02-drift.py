"""M73 step 02 — bound the inter-frame drift and rotation from INTENSITY ONLY.

A focus bracket is not a static scene: the lens breathes, so magnification walks
with the focus index. The cylinder invariant survives a pure radial scale change
(a scale `s` moves a pixel's scene coordinate by `(x - xc) * ds`, a function of
`x` alone, so it perturbs the per-column centre and not the along-`y` residual),
but it does **not** survive a rotation: a rotation by `dphi` maps `x -> x + y
dphi`, which makes the apparent depth at fixed `x` vary linearly with `y`.

This measures both, by phase correlation of the high-pass mean-free detail image
between the first and last frame, in a top band and a bottom band separately:

* a common horizontal shift is translation,
* a differential horizontal shift between the bands is rotation,
* a differential *vertical* shift between the bands is magnification along `y`.

No focus operator is involved. The numbers feed the pre-registration's declared
sensitivity, they do not feed any fit.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import rawpy
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACKS = ["wrapped-text-1", "wrapped-text-2"]
BAND = 400  # plane px, the height of each correlation band


def green_luma(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = float(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    return 0.5 * (cfa[0:h:2, 1:w:2] + cfa[1:h:2, 0:w:2]) - black


def detail(img: np.ndarray) -> np.ndarray:
    return img - ndimage.gaussian_filter(img, 40.0, mode="nearest")


def phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Sub-pixel (dy, dx) taking `a` onto `b`, by phase correlation.

    Both bands are the SAME crop of two frames, so a defocus difference changes
    the amplitude spectrum but not the phase ramp; phase correlation is the right
    tool precisely because one of the two frames is blurred relative to the other.
    """
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    fa = np.fft.rfft2(a * win)
    fb = np.fft.rfft2(b * win)
    cross = fa.conj() * fb
    cross /= np.abs(cross) + 1e-12
    corr = np.fft.irfft2(cross, s=a.shape)
    peak = np.unravel_index(int(np.argmax(corr)), corr.shape)

    def refine(axis: int) -> float:
        i = peak[axis]
        n = corr.shape[axis]
        idx = [peak[0], peak[1]]
        vals = []
        for d in (-1, 0, 1):
            idx[axis] = (i + d) % n
            vals.append(corr[idx[0], idx[1]])
        c0, c1, c2 = vals
        denom = c0 - 2 * c1 + c2
        sub = 0.0 if abs(denom) < 1e-20 else 0.5 * (c0 - c2) / denom
        pos = i + sub
        return pos - n if pos > n / 2 else pos

    return refine(0), refine(1)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, dict] = {}
    for stack in STACKS:
        frames = sorted((CORPUS / stack).glob("*.ARW"))
        a_img = detail(green_luma(frames[0]))
        b_img = detail(green_luma(frames[-1]))
        h, w = a_img.shape
        x0, x1 = w // 2 - 700, w // 2 + 700
        top = slice(BAND // 2, BAND // 2 + BAND)
        bot = slice(h - BAND // 2 - BAND, h - BAND // 2)
        dy_t, dx_t = phase_shift(a_img[top, x0:x1], b_img[top, x0:x1])
        dy_b, dx_b = phase_shift(a_img[bot, x0:x1], b_img[bot, x0:x1])
        # Band centre separation in plane px.
        sep = (bot.start + bot.stop) / 2 - (top.start + top.stop) / 2
        rot_rad = (dx_b - dx_t) / sep
        mag_y = (dy_b - dy_t) / sep
        print(f"\n=== {stack}: frame {frames[0].name} -> {frames[-1].name} ===")
        print(f"top band   dy {dy_t:+8.3f}  dx {dx_t:+8.3f}")
        print(f"bottom band dy {dy_b:+8.3f}  dx {dx_b:+8.3f}")
        print(f"band separation : {sep:.0f} plane px")
        print(f"rotation        : {np.degrees(rot_rad):+.4f} deg over the whole stack")
        print(f"y-magnification : {mag_y * 100:+.4f}% over the whole stack")
        report[stack] = {
            "first": frames[0].name,
            "last": frames[-1].name,
            "dy_top": dy_t,
            "dx_top": dx_t,
            "dy_bottom": dy_b,
            "dx_bottom": dx_b,
            "band_separation_px": sep,
            "rotation_deg_total": float(np.degrees(rot_rad)),
            "y_magnification_pct_total": float(mag_y * 100),
        }
    (OUT / "02-drift.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nwrote", OUT / "02-drift.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
