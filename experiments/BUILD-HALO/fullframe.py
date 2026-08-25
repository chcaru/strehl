"""Full-frame, clean, viewable renders. THE primary instrument for this build.

WHY THIS FILE EXISTS
--------------------
Every halo claim in this build until now was judged on 384 px crops at frozen
ROIs, and that hid the severity completely. At full-frame scale the defect is a
bright aura tracing the whole silhouette -- the first thing the eye lands on --
while the crop statistics were reporting a 10% amplitude reduction. The owner
looked at a full frame and said the renders look horrible. He was right and the
crops were not wrong so much as beside the point.

There was also a second, dumber reason I could not see it: the previous scripts
wrote 8-bit output with `tifffile.imwrite(...)` to paths ending in `.png`.
tifffile ignores the extension and writes TIFF, so every "PNG" this build
produced was a TIFF wearing a PNG's name, and no ordinary viewer -- including
mine -- would open it. **This module writes real PNGs and asserts the magic
bytes**, because a deliverable nobody can open is not a deliverable.

CLEAN MEANS CLEAN. No ROI rectangles, no labels, no annotations, ever. The
`baseline-full` set had diagnostic boxes burned in, which is fine for diagnosis
and catastrophic as something to judge a print by. Annotated variants go in a
separate directory with `-annot` in the name.
"""

from __future__ import annotations

import os

import numpy as np
import tifffile

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def read16(path: str) -> np.ndarray:
    """16-bit TIFF, asserted. Never PIL for a 16-bit RGB read."""
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: dtype {a.dtype}, expected uint16"
    return a


def box_downsample(a: np.ndarray, target_w: int) -> np.ndarray:
    """Integer box-average down to about `target_w`, then exact-resize the rest.

    Box-averaging in LINEAR light before the transfer curve. Downsampling after
    a gamma curve is a real error -- it averages perceptual values and darkens
    edges -- and this whole build is about not making that class of mistake.
    """
    h, w = a.shape[:2]
    f = max(1, w // target_w)
    if f > 1:
        h2, w2 = (h // f) * f, (w // f) * f
        a = a[:h2, :w2]
        a = a.reshape(h2 // f, f, w2 // f, f, -1).mean(axis=(1, 3))
    # remaining fractional step, nearest -- sub-pixel accuracy is irrelevant at
    # viewing scale and a second interpolation would only soften it
    h, w = a.shape[:2]
    if w != target_w:
        yi = (np.arange(int(round(h * target_w / w))) * (w / target_w)).astype(int)
        xi = (np.arange(target_w) * (w / target_w)).astype(int)
        a = a[np.clip(yi, 0, h - 1)][:, np.clip(xi, 0, w - 1)]
    return a


def develop(a: np.ndarray, gain: float) -> np.ndarray:
    """Linear camera-native to a viewable 8-bit sRGB-encoded array.

    FOR LOOKING AT ONLY. Nothing is ever measured on the output of this
    function -- the standing project rule is that quality is never judged on a
    curve-encoded render, and this applies the curve on purpose so a human can
    see what the owner sees.
    """
    v = np.clip(a.astype(np.float64) / 65535.0 * gain, 0.0, 1.0)
    v = np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)
    return (v * 255.0 + 0.5).astype(np.uint8)


def write_png(path: str, rgb8: np.ndarray) -> None:
    """Write a REAL png, and prove it.

    PIL is correct and safe here: this is an 8-bit WRITE. The project rule that
    bans PIL is about READING 16-bit RGB TIFFs, where it silently downconverts
    to 8 bits and the loss is invisible. Neither hazard applies to writing an
    8-bit preview that is already 8-bit by construction.
    """
    from PIL import Image

    assert rgb8.dtype == np.uint8 and rgb8.ndim == 3 and rgb8.shape[2] == 3, rgb8.shape
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    Image.fromarray(rgb8, "RGB").save(path, optimize=True)
    with open(path, "rb") as f:
        head = f.read(8)
    assert head == PNG_MAGIC, (
        f"{path} is not a PNG -- magic {head!r}. This is the exact defect that "
        f"made every earlier preview in this build unopenable."
    )


def full_frame(src_tif: str, out_png: str, gain: float, width: int = 1400) -> tuple:
    a = read16(src_tif)
    small = box_downsample(a, width)
    write_png(out_png, develop(small, gain))
    return small.shape[1], small.shape[0]


def main():
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="16-bit linear TIFF")
    ap.add_argument("--out", required=True, help="output .png")
    ap.add_argument("--gain", type=float, default=None)
    ap.add_argument("--subject", default=None, help="read display_gain from the ROI plan")
    ap.add_argument("--plan", default=r"C:\dev\strehl-out\roi-plan.json")
    ap.add_argument("--width", type=int, default=1400)
    a = ap.parse_args()
    gain = a.gain
    if gain is None:
        gain = json.load(open(a.plan))[a.subject]["display_gain"]
    w, h = full_frame(a.src, a.out, gain, a.width)
    print(f"wrote {a.out}  {w}x{h}  gain {gain:.4f}  CLEAN (no annotations)")


if __name__ == "__main__":
    main()
