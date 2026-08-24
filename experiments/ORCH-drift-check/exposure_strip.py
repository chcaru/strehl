"""Before/after strip for the exposure change, plus provenance for the files.

The gallery already contained *-exposed.tif files of unknown origin, so this
first reports what each variant actually is -- modification time and mean
display level -- and only then builds something to look at. Judging a render
without knowing which binary and which flags produced it is how the last two
wrong conclusions of the night started.

Writes a downscaled full-frame strip so the overall brightness is judgeable,
and a 100% crop strip so the exposure change can be checked not to have
destroyed highlight detail.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\ORCH-gallery"
STEM = "bee-3-cpl"


def stats(path):
    a = tifffile.imread(path)
    y = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]) / 65535.0
    return {
        "mtime": os.path.getmtime(path),
        "shape": a.shape,
        "mean": float(y.mean()),
        "p50": float(np.percentile(y, 50)),
        "p99": float(np.percentile(y, 99)),
        "clip": 100.0 * float((a >= 65535).mean()),
    }, a


def main():
    import datetime
    variants = [
        ("srgb (what the owner saw)", f"{STEM}-srgb.tif"),
        ("exposed (pre-existing, origin unknown)", f"{STEM}-exposed.tif"),
        ("EXPOSED (this preview, +1.54 stops)", f"{STEM}-srgb-EXPOSED.tif"),
    ]
    loaded = []
    print(f"{'variant':<40} {'mtime':<20} {'mean':>7} {'p50':>7} {'p99':>7} {'clip%':>7}")
    for label, fn in variants:
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            print(f"{label:<40} MISSING")
            continue
        s, a = stats(p)
        ts = datetime.datetime.fromtimestamp(s["mtime"]).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{label:<40} {ts:<20} {s['mean']:>7.4f} {s['p50']:>7.4f} "
              f"{s['p99']:>7.4f} {s['clip']:>7.4f}")
        loaded.append((label, a))

    if len(loaded) < 2:
        print("\nNot enough variants to compare.")
        return 1

    # Full-frame strip, downscaled, for overall brightness.
    thumbs = []
    for _, a in loaded:
        im = Image.fromarray((a >> 8).astype(np.uint8))
        im.thumbnail((900, 900), Image.LANCZOS)
        thumbs.append(im)
    w = sum(t.width for t in thumbs) + 20 * (len(thumbs) - 1)
    h = max(t.height for t in thumbs)
    strip = Image.new("RGB", (w, h), (24, 24, 24))
    x = 0
    for t in thumbs:
        strip.paste(t, (x, 0))
        x += t.width + 20
    p1 = os.path.join(OUT, f"{STEM}-EXPOSURE-FULL.png")
    strip.save(p1)

    # 100% crop strip, centred, to check highlight detail survived.
    ch, cw = 520, 520
    crops = []
    for _, a in loaded:
        cy, cx = a.shape[0] // 2, a.shape[1] // 2
        c = a[cy - ch // 2:cy + ch // 2, cx - cw // 2:cx + cw // 2]
        crops.append(Image.fromarray((c >> 8).astype(np.uint8)))
    w = sum(c.width for c in crops) + 20 * (len(crops) - 1)
    strip2 = Image.new("RGB", (w, ch), (24, 24, 24))
    x = 0
    for c in crops:
        strip2.paste(c, (x, 0))
        x += c.width + 20
    p2 = os.path.join(OUT, f"{STEM}-EXPOSURE-CROP.png")
    strip2.save(p2)

    print(f"\nwrote {p1}")
    print(f"wrote {p2}")
    print("order, left to right: " + " | ".join(l for l, _ in loaded))
    return 0


if __name__ == "__main__":
    sys.exit(main())
