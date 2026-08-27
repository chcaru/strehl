"""What the viewer sees, beside what the data could look like.

The measurements say the pipeline applies a roughly linear gain and clips,
rather than an opto-electronic transfer function:

  exponent vs a LINEAR rawpy decode      bee-1-cpl 0.90, coffee-bubbles 1.17
  reference exponents, computed not quoted   linear 1.0000, sRGB 0.4743

and the shipped TIFF declares sRGB in its ImageDescription. If that reading is
right the consequences are visible, not statistical, so this renders them.

THE ONE THING THIS MUST NOT DO is flatter either side. Both columns get the
SAME data and differ only by the transfer function applied on the way to 8-bit:

  AS SHIPPED   master/65535 straight to 8-bit. This is what every viewer that
               honours the sRGB label does with these values.
  sRGB APPLIED treat the values as linear scene-referred, encode with the real
               piecewise sRGB curve, then to 8-bit.

No autoscaling, no per-tile percentile window, no white balance change, no
saturation. Section 91: a per-crop window biases gain and makes crops
incomparable, and that is exactly the mistake that would make this pair lie.

If AS SHIPPED looks correct and sRGB APPLIED looks washed out, the data is
already encoded and the exponent fits are wrong. If AS SHIPPED looks dark and
muddy and sRGB APPLIED looks like a photograph, the label is a lie and the
pipeline owes its output a transfer function.
"""
import os
import glob

import numpy as np
import tifffile

from orch_contact import png_rgb, draw_text, LABEL_H

OUT_ROOT = r"C:\dev\strehl-out"
SUBJECTS = ["bee-1-cpl", "coffee-bubbles", "tweezers-cpl", "flat-on-ruler-cpl"]
TILE = 620


def srgb_encode(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def downsample(a, tile):
    """Plain box decimation to `tile`. No resampler choice enters the picture,
    because the point here is tone, and a fancy kernel would only add a
    variable I would then have to defend."""
    h, w = a.shape[:2]
    f = max(h // tile, w // tile, 1)
    h2, w2 = (h // f) * f, (w // f) * f
    b = a[:h2, :w2].reshape(h2 // f, f, w2 // f, f, 3).mean(axis=(1, 3))
    return b


def main():
    cols = []
    for s in SUBJECTS:
        cand = [p for p in glob.glob(os.path.join(OUT_ROOT, "SHIP-V2", "*.tiff"))
                if os.path.basename(p).startswith(s)]
        if not cand:
            print("skip %s (no master)" % s)
            continue
        m = tifffile.imread(cand[0])[..., :3].astype(np.float64)  # tifffile, not PIL
        small = downsample(m, TILE) / 65535.0
        y = 0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]
        shipped = np.clip(small, 0, 1)
        applied = srgb_encode(small)
        print("%-22s median as-shipped %.4f   after sRGB %.4f   clipped %.2f%%"
              % (s, float(np.median(y)),
                 float(np.median(srgb_encode(y))),
                 100.0 * float(np.mean(small >= 0.999))))
        cols.append((s, shipped, applied))

    if not cols:
        raise SystemExit("nothing to render")
    # Masters differ in width (7032 vs 7040 sensel), so decimation lands on
    # 639 or 640 px. Crop every tile to the common size rather than resampling
    # one to match another -- a resample here would put a kernel between the
    # two things the picture is meant to compare.
    th = min(c[1].shape[0] for c in cols)
    tw = min(c[1].shape[1] for c in cols)
    canvas = np.zeros((2 * (th + LABEL_H), len(cols) * tw, 3), dtype=np.uint8)
    for cx, (name, a, b) in enumerate(cols):
        for ry, (img, tag) in enumerate(((a, "AS SHIPPED"), (b, "sRGB APPLIED"))):
            y0, x0 = ry * (th + LABEL_H), cx * tw
            canvas[y0:y0 + th, x0:x0 + tw] = (img[:th, :tw] * 255).astype(np.uint8)
            draw_text(canvas, "%s  %s" % (name[:18], tag), y0 + th + 4, x0 + 4)

    out = os.path.join(OUT_ROOT, "ORCH-CONTACT", "tone-pair.png")
    png_rgb(canvas, out)
    print("\nwrote %s  %dx%d" % (out, canvas.shape[1], canvas.shape[0]))


if __name__ == "__main__":
    main()
