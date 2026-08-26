#!/usr/bin/env python3
"""Timing + capture census probe.  Cheap: reads the Bayer plane, never demosaics.

Two things it settles before any instrument is built:

  * how long a raw green-plane read costs, which decides whether a
    through-focus curve over 299 frames x 26 subjects is affordable;
  * the aperture / shutter / ISO census, because the diffraction verdict is
    not something you can measure out of a merged TIFF -- it is written in the
    EXIF of the frames that made it.
"""
from __future__ import annotations

import os
import time

import numpy as np
import rawpy


def green_plane(path: str) -> np.ndarray:
    """The G plane of the CFA, at half linear resolution, black-subtracted.

    No demosaic, no white balance, no matrix.  This is only ever used to RANK
    frames against each other inside one bracket -- never compared against
    anything that has been through a different transformation.
    """
    with rawpy.imread(path) as r:
        cfa = r.raw_image_visible
        pat = r.raw_pattern
        black = float(np.mean(r.black_level_per_channel))
        ys, xs = np.where(pat == 1)
        g = np.zeros((cfa.shape[0] // 2, cfa.shape[1] // 2), np.float32)
        for y, x in zip(ys, xs):
            g += cfa[y::2, x::2][: g.shape[0], : g.shape[1]].astype(np.float32)
        return g / len(ys) - black


def main() -> int:
    root = r"D:\personal\macro"
    subs = sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)) and d != "flat-fields")

    f = sorted(os.listdir(os.path.join(root, subs[0])))[0]
    p = os.path.join(root, subs[0], f)
    t0 = time.time()
    g = green_plane(p)
    t1 = time.time()
    print(f"green_plane: {t1 - t0:.2f}s  shape={g.shape} dtype={g.dtype} "
          f"min={g.min():.0f} max={g.max():.0f}")

    print(f"\n{'SUBJECT':<38s} {'N':>4s} {'APER':>7s} {'SHUT':>10s} {'ISO':>6s} "
          f"{'FOCAL':>7s} {'LENS'}")
    for s in subs:
        d = os.path.join(root, s)
        fs = sorted(x for x in os.listdir(d) if x.lower().endswith(".arw"))
        if not fs:
            print(f"{s:<38s} {0:>4d}  (no ARW)")
            continue
        ap = sh = iso = fl = lens = "?"
        try:
            import exifread  # type: ignore
            with open(os.path.join(d, fs[0]), "rb") as fh:
                tags = exifread.process_file(fh, details=False)
            ap = str(tags.get("EXIF FNumber", "?"))
            sh = str(tags.get("EXIF ExposureTime", "?"))
            iso = str(tags.get("EXIF ISOSpeedRatings", "?"))
            fl = str(tags.get("EXIF FocalLength", "?"))
            lens = str(tags.get("EXIF LensModel", tags.get("MakerNote LensType", "?")))
        except Exception as e:  # noqa: BLE001
            lens = f"exif-unavailable ({type(e).__name__})"
        print(f"{s:<38s} {len(fs):>4d} {ap:>7s} {sh:>10s} {iso:>6s} {fl:>7s} {lens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
