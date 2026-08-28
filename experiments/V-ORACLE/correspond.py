#!/usr/bin/env python3
"""Measure the raw-frame -> master correspondence, per tile.

THE THREAT THIS ADDRESSES.  Stage A scores the bracket in RAW FRAME
coordinates.  The eye, and the merged master, live in ALIGNED MASTER
coordinates.  The aligner exists precisely because those two differ: a macro
focus bracket breathes, so scene content moves between frames and between any
frame and the master.  If tile (r,c) of the raw frame is not the same scene
patch as tile (r,c) of the master, then every site verdict is measuring two
different places and is worthless -- and it would fail in the direction of
manufacturing a merge defect, because a sharp raw tile compared against a
DIFFERENT, genuinely-empty master tile reads exactly like "we threw detail
away".  So this control is adverse to my current leading hypothesis, which is
the only kind worth running.

METHOD.  Take the master's green-equivalent plane (master luma decimated 2x,
which puts it on the same sampling lattice as one Bayer green sub-plane).
For a grid of tiles, phase-correlate the master patch against the same-indexed
patch of a frame, and report the displacement.  Report the DISTRIBUTION of
displacements, not a mean: a mean displacement of zero is exactly what a pure
scale change about the centre produces, so a mean would hide the worst case.

Every tile lands in a counted outcome: LOCKED (a clear correlation peak),
WEAK (peak present but low contrast -- displacement reported but not trusted)
or NOSIG (no usable structure in one of the two patches, so no answer is
possible and none is claimed).  The three counts sum to the tile count.

Usage:  python correspond.py <subject> [--frames 0,3,50,88,175]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

PATCH = 256          # green px; big enough to hold structure, small enough to be local
PEAK_RATIO = 3.0     # peak / (robust background) required to call a tile LOCKED
MIN_STD = 2.0        # DN; below this a patch is flat and cannot be registered


def master_green(subject):
    """Master luma resampled onto the green sub-plane lattice.

    Point-decimation by 2 rather than a box average: a box average is a blur,
    and blurring the merge before comparing it to a frame would bias every
    comparison against the merge.  Registration only needs common structure,
    and point sampling keeps both arms' passbands as close as they can be.
    """
    a = tifffile.imread(os.path.join(ora.MASTERS, subject + ".tiff"))
    lum = (0.2126 * a[:, :, 0].astype(np.float32)
           + 0.7152 * a[:, :, 1].astype(np.float32)
           + 0.0722 * a[:, :, 2].astype(np.float32))
    return lum[::2, ::2]


def pc_shift(a, b):
    """Phase correlation of two equal-size patches -> (dy, dx, peak_ratio)."""
    a = a - a.mean()
    b = b - b.mean()
    w = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    A = np.fft.rfft2(a * w)
    B = np.fft.rfft2(b * w)
    R = A * np.conj(B)
    m = np.abs(R)
    R = np.where(m > 1e-12, R / np.maximum(m, 1e-12), 0)
    c = np.fft.irfft2(R, s=a.shape)
    j = int(np.argmax(c))
    dy, dx = np.unravel_index(j, c.shape)
    peak = float(c.flat[j])
    bg = float(np.quantile(np.abs(c), 0.99))
    if dy > a.shape[0] // 2:
        dy -= a.shape[0]
    if dx > a.shape[1] // 2:
        dx -= a.shape[1]
    return float(dy), float(dx), peak / max(bg, 1e-12)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--frames", default="")
    ap.add_argument("--ref", default="master",
                    help="'master' = register frames to the delivered master; "
                         "'frame0' = register frames to frame 0.  The second is "
                         "the one stage A actually depends on, because stage A "
                         "only ever compares frames WITH EACH OTHER at a tile.")
    args = ap.parse_args()

    fs = ora.frames_of(args.subject)
    if args.frames:
        idx = [int(x) for x in args.frames.split(",")]
    else:
        n = len(fs)
        idx = sorted({0, n // 4, n // 2, 3 * n // 4, n - 1})
    if args.ref == "master":
        M = master_green(args.subject)
        reflabel = "delivered master"
    else:
        M, _ = ora.green_pair(fs[0])
        M = M.astype(np.float32)
        reflabel = "frame 0 (raw)"
    print(f"{args.subject}: reference = {reflabel} {M.shape}, "
          f"{len(fs)} frames, probing {idx}")

    allmag = []
    allpr = []
    for k in idx:
        g1, _ = ora.green_pair(fs[k])
        H = min(M.shape[0], g1.shape[0])
        W = min(M.shape[1], g1.shape[1])
        nr, nc = H // PATCH, W // PATCH
        locked = weak = nosig = 0
        mags = []
        prs = []
        for r in range(nr):
            for c in range(nc):
                sl = (slice(r * PATCH, (r + 1) * PATCH),
                      slice(c * PATCH, (c + 1) * PATCH))
                pm, pf = M[sl].astype(np.float64), g1[sl].astype(np.float64)
                if pm.std() < MIN_STD or pf.std() < MIN_STD:
                    nosig += 1
                    continue
                dy, dx, pr = pc_shift(pm, pf)
                prs.append(pr)
                if pr >= PEAK_RATIO:
                    locked += 1
                    mags.append((dy * dy + dx * dx) ** 0.5)
                else:
                    weak += 1
                    mags.append((dy * dy + dx * dx) ** 0.5)
        tot = locked + weak + nosig
        assert tot == nr * nc, f"{tot} != {nr * nc}"
        m = np.array(mags) if mags else np.array([np.nan])
        p = np.array(prs) if prs else np.array([np.nan])
        allmag.append(m)
        allpr.append(p)
        # WEAK tiles keep their displacement in the distribution.  Dropping them
        # would let a tile that failed to register read as a tile that
        # registered perfectly -- the exact "skipped reads as passed" failure
        # the brief forbids.  They are reported separately so the reader can
        # discount them, but they are never silently removed.
        print(f"  frame {k:4d}: tiles {nr}x{nc}={tot}  "
              f"LOCKED={locked} WEAK={weak} NOSIG={nosig}  "
              f"peakratio med={np.nanmedian(p):5.2f}  "
              f"|shift| green px (all registered): med={np.nanmedian(m):6.2f} "
              f"p90={np.nanpercentile(m, 90):6.2f} max={np.nanmax(m):7.2f}")

    a = np.concatenate(allmag)
    a = a[np.isfinite(a)]
    print(f"\nALL LOCKED TILES ({a.size}):  median={np.median(a):.2f}  "
          f"p90={np.percentile(a, 90):.2f}  p99={np.percentile(a, 99):.2f}  "
          f"max={a.max():.2f} green px")
    tile = 128
    print(f"stage A tile is {tile} green px.  Fraction of locked tiles whose")
    print(f"displacement exceeds half a stage-A tile ({tile // 2} green px): "
          f"{100.0 * (a > tile / 2).mean():.2f}%")
    print(f"                        exceeds a quarter ({tile // 4} green px): "
          f"{100.0 * (a > tile / 4).mean():.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
