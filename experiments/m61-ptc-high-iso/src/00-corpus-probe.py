"""00 -- exploratory probe of the corpus, BEFORE any measurement is designed.

Not a measurement.  This exists so that the pre-registration in `01-*.py` is
written against the data that actually exists rather than against the brief's
description of it, and so that rule 7 (never compute over the full decoded
buffer) and rule 32 (`raw_image_visible` is a view, copy inside the `with`)
are discharged in one place where they are visible.

Reports, per corpus directory:
  * frame count, EXIF ISO, exposure time, aperture
  * `raw_image_visible` shape and `raw_pattern`
  * per-plane min / mean / p99.9 / max of frame 0 and of the middle frame
  * the fraction of pixels at or above the 15360 white level

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m61-ptc-high-iso/src/00-corpus-probe.py
"""

from __future__ import annotations

import glob
import os
import time

import numpy as np

CORPUS = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data",
                   "corpus-probe.txt")
BLACK = 512
WHITE = 15360
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s, flush=True)
    LINES.append(s)


def exif_of(path: str) -> dict[str, str]:
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    out = {}
    for k in ("EXIF ISOSpeedRatings", "EXIF ExposureTime", "EXIF FNumber",
              "Image Model", "EXIF DateTimeOriginal"):
        out[k] = str(t[k]) if k in t else "?"
    return out


def planes(raw: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "R": raw[0::2, 0::2],
        "G1": raw[0::2, 1::2],
        "G2": raw[1::2, 0::2],
        "B": raw[1::2, 1::2],
    }


def main() -> int:
    import rawpy

    t0 = time.time()
    say("M61 corpus probe -- exploratory, no measurement here")
    say(f"corpus: {CORPUS}")
    say()
    dirs = sorted(d for d in glob.glob(os.path.join(CORPUS, "*"))
                  if os.path.isdir(d))
    for d in dirs:
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
        if not fs:
            continue
        e = exif_of(fs[0])
        say(f"=== {os.path.basename(d):<16} {len(fs):>4} frames   "
            f"ISO {e['EXIF ISOSpeedRatings']:<6} "
            f"exp {e['EXIF ExposureTime']:<8} f/{e['EXIF FNumber']:<6} "
            f"{e['Image Model']}  {e['EXIF DateTimeOriginal']}")
        for idx in (0, len(fs) // 2):
            with rawpy.imread(fs[idx]) as rr:
                vis = np.asarray(rr.raw_image_visible, dtype=np.uint16).copy()
                pat = np.asarray(rr.raw_pattern).tolist()
                full = rr.raw_image.shape
            pl = planes(vis)
            sat = float((vis >= WHITE).mean())
            say(f"    frame {idx:>4}  visible {vis.shape} full {full} "
                f"pattern {pat}  >=white {100 * sat:.4f}%")
            for nm, p in pl.items():
                pf = p.astype(np.float64) - BLACK
                say(f"      {nm:<2} min {pf.min():>8.1f} mean {pf.mean():>9.2f}"
                    f" p50 {np.percentile(pf, 50):>8.1f}"
                    f" p99.9 {np.percentile(pf, 99.9):>8.1f}"
                    f" max {pf.max():>8.1f}")
        say()
    say(f"[{time.time() - t0:.0f}s]")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
