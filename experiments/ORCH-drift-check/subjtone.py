#!/usr/bin/env python3
"""Does the SUBJECT have tonal separation, or is the frame actually washed?

scripts/tone_profile.py flags WASHED from the frame-global median and p99.9.
On a white-sweep presentation -- a small subject on a large blown backdrop,
which is a standard macro studio setup, not a mistake -- that statistic is
measuring BACKDROP AREA. Grow the sweep and the median rises with no change
whatever to the subject's rendering. It is the same defect I retracted in
SS35: a summary statistic whose value is set by the region nobody is judging.

So split the frame first and report each region's span on its own.

The instrument is only worth anything if it can still say "washed", so it
ships with its own plant: --plant C compresses the SUBJECT pixels toward
their own mean by factor C in linear light, leaving the backdrop untouched.
A real washed subject must drive subject_span down. If planting does not
move the number, the number is not reading the subject and every verdict it
has ever printed is void.

Segmentation is by luma against a high threshold, because the one thing that
is certain about a white sweep is that it is the bright mode. It is reported,
not assumed: the printed subject_frac lets you see whether the split is
plausible, and a split that captures 2% or 98% of the frame should be
disbelieved regardless of what the spans say.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# sRGB display space; the renderer's output is already encoded.
def to_linear(x: np.ndarray) -> np.ndarray:
    a = 0.055
    return np.where(x <= 0.04045, x / 12.92, ((x + a) / (1 + a)) ** 2.4)


def to_srgb(x: np.ndarray) -> np.ndarray:
    a = 0.055
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, (1 + a) * x ** (1 / 2.4) - a)


def luma(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def span_stats(v: np.ndarray) -> dict:
    if v.size < 1000:
        return {}
    p = np.percentile(v, [1, 5, 50, 95, 99, 99.9])
    return {
        "n": v.size,
        "p1": p[0], "p5": p[1], "med": p[2], "p95": p[3], "p99": p[4], "p999": p[5],
        "span_50_999": p[5] - p[2],
        "span_5_95": p[3] - p[1],
        "sd": float(np.std(v)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--thresh", type=float, default=None,
                    help="luma above this is backdrop; default: auto from the bright mode")
    ap.add_argument("--plant", type=float, default=None,
                    help="commissioning plant: compress SUBJECT tones by this factor "
                         "toward their own mean, in linear light. 0.1 = badly washed.")
    args = ap.parse_args()

    print(f"{'subject':38s} {'sub%':>6s} {'SUBJECT span':>13s} {'sub sd':>7s} "
          f"{'BACKDROP span':>14s} {'bk med':>7s}  verdict")
    print("-" * 108)

    rc = 0
    for path in args.images:
        p = Path(path)
        rgb = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255.0
        y = luma(rgb)

        if args.thresh is not None:
            thr = args.thresh
        else:
            # The sweep is the bright mode. Take it as everything within 12% of
            # the 99.5th percentile -- high enough to exclude subject highlights,
            # low enough to catch sweep shading and vignetting.
            hi = float(np.percentile(y, 99.5))
            thr = hi * 0.88

        backdrop = y >= thr
        subject = ~backdrop

        if args.plant is not None and subject.any():
            lin = to_linear(rgb)
            m = lin[subject].mean(axis=0)
            lin[subject] = m + (lin[subject] - m) * args.plant
            rgb = to_srgb(lin)
            y = luma(rgb)
            # segment ONCE, on the unplanted frame; re-segmenting would let the
            # plant move the boundary and hide itself.

        ss = span_stats(y[subject])
        bs = span_stats(y[backdrop])
        frac = float(subject.mean())

        if not ss or not bs:
            print(f"{p.stem:38s}  degenerate split (sub%={frac*100:.2f}) -- disbelieve")
            rc = 1
            continue

        # A washed SUBJECT is the real defect. Threshold chosen to sit well below
        # every healthy subject measured on this gallery and well above a 0.1 plant.
        washed = ss["span_5_95"] < 0.10
        verdict = "SUBJECT WASHED" if washed else "subject has range"
        if frac < 0.02 or frac > 0.98:
            verdict += "  (SPLIT DEGENERATE - disbelieve)"

        print(f"{p.stem:38s} {frac*100:5.1f}% "
              f"{ss['span_5_95']:13.3f} {ss['sd']:7.3f} "
              f"{bs['span_5_95']:14.3f} {bs['med']:7.3f}  {verdict}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
