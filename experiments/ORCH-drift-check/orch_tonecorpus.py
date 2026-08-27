"""Is EVERY master linear, and does the JPEG path differ from the TIFF path?

orch_tone.py measured coffee-bubbles at exponent ~1.0-1.3 against a LINEAR rawpy
decode, with its median at 2517 DN -- 3.84% of a 16-bit scale. If that holds
across the corpus it is the most consequential defect found in this project:
the pipeline writes linear data into a file whose ImageDescription declares
sRGB, and every viewer that honours the label renders it near-black.

The decisive evidence is NOT the fitted exponent. Exponents came back with
r2 0.95-0.97 and a 0.31 spread across frames of one subject, because a merge
selects sharp pixels and its histogram is not any single frame's. The decisive
evidence is arithmetic and needs no source frame at all:

  a scene whose highlights CLIP at 65535 but whose median sits at 3.8% is
  4.7 stops below clipping. sRGB-encoding a scene with linear median 0.038
  puts the median at 1.055*0.038^(1/2.4)-0.055 = 0.215, or 14,100 DN.

So: median near 14,000 DN means encoded; median near 2,500 DN means linear.
Nothing about the source decode enters that comparison.

The second question matters just as much. The deliverable gallery LOOKED FINE in
the contact sheets. If those JPEGs carry a curve the TIFFs lack, then the defect
is specific to the TIFF writer and the JPEG path already knows how to do it --
which makes the fix small and localises it. If both are linear, the gallery
sheets were flattered by the viewer and the problem is upstream of both.
"""
import os
import glob

import numpy as np
import tifffile

OUT_ROOT = r"C:\dev\strehl-out"
QS = np.array([10, 25, 50, 75, 90, 99], dtype=np.float64)


def srgb_encode(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]).astype(np.float64)


def main():
    files = [p for p in glob.glob(os.path.join(OUT_ROOT, "SHIP-V2", "*.tif*"))
             if os.path.splitext(p)[1].lower() == ".tiff"]
    files.sort()
    print("TIFF MASTERS  n=%d" % len(files))
    print("%-34s %8s %8s %8s %8s %9s   %s"
          % ("subject", "p50", "p50frac", "p90frac", "p99frac",
             "srgb_p50", "verdict"))
    lin = enc = 0
    for p in files:
        y = luma(tifffile.imread(p)[..., :3].astype(np.float64))
        q = np.percentile(y, QS) / 65535.0
        p50 = q[2]
        # what the median WOULD read if this linear scene were sRGB-encoded
        pred = float(srgb_encode(p50))
        # and what it would read if it were already encoded: itself
        if abs(p50 - pred) < abs(p50 - p50):
            v = "?"
        v = "LINEAR" if p50 < 0.5 * pred else "ENCODED"
        if v == "LINEAR":
            lin += 1
        else:
            enc += 1
        print("%-34s %8.0f %8.4f %8.4f %8.4f %9.4f   %s"
              % (os.path.basename(p)[:34], p50 * 65535, p50, q[4], q[5], pred, v))
    print("\npartition: %d LINEAR, %d ENCODED, %d total" % (lin, enc, len(files)))
    assert lin + enc == len(files), "partition leak"

    print("\nreference: what these curves put a 0.038 linear median at")
    for name, fn in (("linear (identity)", lambda v: v),
                     ("sRGB", srgb_encode),
                     ("gamma 2.2", lambda v: np.power(v, 1 / 2.2))):
        print("   %-20s %.4f  (%.0f DN)" % (name, fn(0.038), fn(0.038) * 65535))

    # --- the JPEG comparison -------------------------------------------------
    gal = os.path.join(OUT_ROOT, "VIEW-SHIP", "assets")
    jpg = sorted(glob.glob(os.path.join(gal, "*.jpg")))
    print("\nGALLERY JPEGS  n=%d  dir=%s" % (len(jpg), gal))
    if not jpg:
        print("  none found -- cannot compare paths")
        return
    from PIL import Image      # safe: these are 8-bit on disk, never 16-bit
    print("%-40s %8s %8s   %s" % ("file", "p50", "p50frac", "verdict"))
    jl = je = 0
    for p in jpg[:30]:
        a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
        q = float(np.percentile(luma(a), 50)) / 255.0
        v = "LINEAR-ISH" if q < 0.12 else "ENCODED"
        if v == "ENCODED":
            je += 1
        else:
            jl += 1
        print("%-40s %8.1f %8.4f   %s"
              % (os.path.basename(p)[:40], q * 255, q, v))
    print("\npartition: %d ENCODED, %d LINEAR-ISH, %d examined" % (je, jl, je + jl))

    print("\nWHAT THIS CANNOT SEE:")
    print("  - a genuinely dark subject also has a low median; the corpus-wide")
    print("    count is the guard, since 26 subjects are not all dark")
    print("  - it reads luma only, so a per-channel curve would be missed")
    print("  - PIL is used ONLY on 8-bit JPEGs here; it right-shifts 16-bit")
    print("    TIFFs silently, which is why the TIFF arm uses tifffile")


if __name__ == "__main__":
    main()
