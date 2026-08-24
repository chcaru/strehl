"""Whole-frame comparison for `marker`, which cannot be rigidly registered.

R1 in `then_vs_now_all.py` refused this stack at correlation 0.2464 (fact 1433):
the judged render is unaligned and HEAD applies alignment's ~7-10% FOV crop, so
the two differ by a SCALE change and no integer offset registers them. Rather
than relax the bar, present the whole frame -- which is the right view anyway,
because the defect that matters on this stack is a large-scale colour feature.

**THIS PANEL IS NOT A SHARPNESS COMPARISON.** Both sides are downscaled to a
common size, which destroys exactly the resolution difference the bee3 and
lavendar montages exist to show. It is a COLOUR and EXPOSURE comparison only,
and it is labelled as such in the image so it cannot be quoted as anything else.

What it shows, both measured:
  * old: 4.773% of pixels blown (luma p99.9 = 1.0000); new: 0.000% (p99.9 =
    0.9520), because --auto-exposure chose -0.24 stops. It can darken, and here
    it did.
  * new: 2.002% magenta (fact 1432) where LibRaw renders neutral white. The fix
    is assigned to M109. This montage must show the defect, not hide it -- a
    before/after that omits a regression is a advertisement, not a measurement.
"""
import os
import numpy as np
import tifffile
import cv2

OUTDIR = r"C:\dev\strehl-out\ORCH-thennow"
OLD = r"C:\dev\strehl-out\marker.tif"
NEW = os.path.join(OUTDIR, "marker-HEAD-8f46f04.tif")
STOPS = -0.24
W, H = 860, 573


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def prep(a):
    f = np.clip(a.astype(np.float32) / 65535.0, 0, 1)
    return cv2.resize((f * 255).astype(np.uint8)[..., ::-1], (W, H),
                      interpolation=cv2.INTER_AREA)


def label(img, text, sub, sub2=None):
    img = img.copy()
    h = 118 if sub2 else 96
    cv2.rectangle(img, (0, 0), (img.shape[1], h), (0, 0, 0), -1)
    cv2.putText(img, text, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.80,
                (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, sub, (14, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                (190, 190, 190), 1, cv2.LINE_AA)
    if sub2:
        cv2.putText(img, sub2, (14, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                    (150, 190, 255), 1, cv2.LINE_AA)
    return img


def main():
    old = tifffile.imread(OLD)
    new = tifffile.imread(NEW)

    def blown(a):
        f = a.astype(np.float32) / 65535.0
        lum = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
        return 100.0 * (lum >= 0.999).mean()

    def magenta(a):
        f = a.astype(np.float32) / 65535.0
        R, G, B = f[..., 0], f[..., 1], f[..., 2]
        return 100.0 * ((R - G > 0.06) & (B - G > 0.06)).mean()

    ob, nb = blown(old), blown(new)
    om, nm = magenta(old), magenta(new)
    print(f"old: blown {ob:.3f}%  magenta {om:.3f}%")
    print(f"new: blown {nb:.3f}%  magenta {nm:.3f}%")

    gain = 2.0 ** STOPS
    lin = srgb_to_linear(old.astype(np.float32) / 65535.0)
    omatch = (np.clip(linear_to_srgb(np.clip(lin * gain, 0, 1)), 0, 1) * 65535).astype(np.uint16)

    p1 = label(prep(old), "1. THEN - what you judged",
               f"8.24 MP binned . no colour mgmt . {ob:.2f}% BLOWN")
    p2 = label(prep(omatch), "2. THEN, exposure-matched",
               f"same old pixels, {STOPS:+.2f} stops - the CONTROL")
    p3 = label(prep(new), "3. NOW - HEAD 8f46f04",
               f"32.99 MP . aligned 299/299 . sRGB . {STOPS:+.2f} stops . {nb:.2f}% blown",
               f"REGRESSION: {nm:.2f}% magenta - clipped-green defect, fix assigned (fact 1432)")

    gap = np.full((H, 10, 3), 40, np.uint8)
    strip = np.hstack([p1, gap, p2, gap, p3])
    foot = np.full((44, strip.shape[1], 3), 24, np.uint8)
    cv2.putText(foot, "WHOLE FRAME, DOWNSCALED - colour and exposure only. This is NOT a sharpness "
                      "comparison; see THEN-vs-NOW-bee3/lavendar for that.",
                (14, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (170, 170, 170), 1, cv2.LINE_AA)
    out = os.path.join(OUTDIR, "THEN-vs-NOW-marker-wholeframe.png")
    cv2.imwrite(out, np.vstack([strip, foot]))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
