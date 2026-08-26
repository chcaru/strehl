#!/usr/bin/env python3
"""Stage 1: the through-focus curve, per subject, per region, from the RAW frames.

This stage never compares a merge against a frame.  It only compares FRAMES
AGAINST EACH OTHER, all decoded by the identical path (rawpy CFA green plane,
black-subtracted, no demosaic, no white balance, no matrix).  Every number here
is therefore inside one transformation and safe.

What it settles, and none of it needs a merge:

  BEST FRAME per region -- which frame stage 2 should render as the source arm.

  COVERAGE GAP.  For a region, walk the focus response F(k) across the bracket.
  If the maximum sits AT AN END of the bracket, the bracket ran out before the
  subject did: no frame was ever in focus there, and which end tells you which
  way to extend.  If the maximum is interior and the curve rises and falls
  around it, that region was covered.  This is a statement about the CAPTURE and
  the merge cannot fix it.

  MOTION.  Frame-to-frame displacement of a fixed central window, by phase
  correlation.  A bracket that walks steadily is drift; one that jumps is
  motion.  `foam` is known to have moved, which makes it a positive control for
  this detector rather than merely a subject.

  FLATNESS.  A region whose best frame still holds almost no high-frequency
  energy has nothing to be sharp about -- either it is genuinely featureless or
  the optics never delivered.  Flagged, not judged, here.

Usage:  python focuscurve.py <subject> [--frames N] [--grid CxR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import rawpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

# Grid in FRACTIONAL frame coordinates.  Fractional coordinates map between the
# raw plane and any merge render without knowing either one's coverage k, because
# every scaling in this pipeline is about the frame centre.
GRID_C, GRID_R = 6, 4


def green_plane(path: str) -> np.ndarray:
    with rawpy.imread(path) as r:
        cfa = r.raw_image_visible
        pat = r.raw_pattern
        black = float(np.mean(r.black_level_per_channel))
        ys, xs = np.where(pat == 1)
        g = np.zeros((cfa.shape[0] // 2, cfa.shape[1] // 2), np.float32)
        for y, x in zip(ys, xs):
            g += cfa[y::2, x::2][: g.shape[0], : g.shape[1]].astype(np.float32)
        return g / len(ys) - black


def hf_blocks(g: np.ndarray, nc: int, nr: int, half: int) -> np.ndarray:
    """High-frequency energy per grid block, in DN.

    A plain Laplacian-of-the-block RMS: shift-invariant enough for ranking and
    cheap enough to run over a whole bracket.  Ranking only -- absolute DN
    comparisons against a merge happen in stage 2, in linear sRGB, never here.
    """
    h, w = g.shape
    out = np.zeros((nr, nc), np.float32)
    for r in range(nr):
        for c in range(nc):
            cy = int((r + 0.5) / nr * h)
            cx = int((c + 0.5) / nc * w)
            y0 = max(0, min(h - 2 * half, cy - half))
            x0 = max(0, min(w - 2 * half, cx - half))
            t = g[y0:y0 + 2 * half, x0:x0 + 2 * half]
            lap = (4 * t[1:-1, 1:-1] - t[:-2, 1:-1] - t[2:, 1:-1]
                   - t[1:-1, :-2] - t[1:-1, 2:])
            out[r, c] = float(np.sqrt((lap ** 2).mean()))
    return out


def phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Integer displacement b relative to a, by phase correlation."""
    A = np.fft.fft2(a - a.mean())
    B = np.fft.fft2(b - b.mean())
    R = A * np.conj(B)
    m = np.abs(R)
    R = np.divide(R, m, out=np.zeros_like(R), where=m > 0)
    c = np.real(np.fft.ifft2(R))
    j = int(np.argmax(c))
    dy, dx = divmod(j, c.shape[1])
    if dy > c.shape[0] // 2:
        dy -= c.shape[0]
    if dx > c.shape[1] // 2:
        dx -= c.shape[1]
    return float(dy), float(dx)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--frames", type=int, default=40)
    ap.add_argument("--half", type=int, default=192)
    args = ap.parse_args()

    d = os.path.join(tri.RAW, args.subject)
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
    n = len(files)
    assert n > 0, f"{args.subject}: no ARW frames"
    idx = (np.unique(np.linspace(0, n - 1, min(args.frames, n)).round().astype(int))
           if n > args.frames else np.arange(n))

    curves = np.zeros((len(idx), GRID_R, GRID_C), np.float32)
    levels = np.zeros(len(idx), np.float32)
    shifts: list[tuple[float, float]] = []
    prev = None
    for i, k in enumerate(idx):
        g = green_plane(os.path.join(d, files[k]))
        curves[i] = hf_blocks(g, GRID_C, GRID_R, args.half)
        levels[i] = float(g.mean())
        h, w = g.shape
        cen = g[h // 2 - 256:h // 2 + 256, w // 2 - 256:w // 2 + 256]
        if prev is not None:
            shifts.append(phase_shift(prev, cen))
        prev = cen

    res: dict = {
        "subject": args.subject,
        "n_frames": n,
        "sampled": [int(v) for v in idx],
        "grid": [GRID_R, GRID_C],
        "half_px_rawG": args.half,
        "level_dn": [round(float(v), 2) for v in levels],
        "blocks": [],
    }

    for r in range(GRID_R):
        for c in range(GRID_C):
            f = curves[:, r, c]
            a = int(np.argmax(f))
            fmax, fmin = float(f.max()), float(f.min())
            rng = fmax - fmin
            # At an end of the bracket?  Use the sampled ladder's own ends.
            at_end = "near" if a == 0 else ("far" if a == len(idx) - 1 else "")
            # How much of the peak is resolved: the drop from the peak to the
            # bracket end on the side the peak sits nearest.  A covered region
            # falls away on BOTH sides.
            dl = (fmax - float(f[0])) / rng if rng > 0 else 0.0
            dr = (fmax - float(f[-1])) / rng if rng > 0 else 0.0
            res["blocks"].append({
                "r": r, "c": c,
                "u": round((c + 0.5) / GRID_C, 4),
                "v": round((r + 0.5) / GRID_R, 4),
                "argmax_sample": a,
                "best_frame": int(idx[a]),
                "hf_max_dn": round(fmax, 3),
                "hf_min_dn": round(fmin, 3),
                "hf_at_first": round(float(f[0]), 3),
                "hf_at_last": round(float(f[-1]), 3),
                "fall_near": round(dl, 4),
                "fall_far": round(dr, 4),
                "at_end": at_end,
                "curve": [round(float(v), 3) for v in f],
            })

    if shifts:
        sy = np.array([s[0] for s in shifts])
        sx = np.array([s[1] for s in shifts])
        step = np.sqrt(sy ** 2 + sx ** 2)
        res["motion"] = {
            "per_step_px_rawG": [round(float(v), 2) for v in step],
            "total_px_rawG": round(float(np.sqrt(sy.sum() ** 2 + sx.sum() ** 2)), 2),
            "path_px_rawG": round(float(step.sum()), 2),
            "max_step_px_rawG": round(float(step.max()), 2),
            "median_step_px_rawG": round(float(np.median(step)), 2),
        }

    out = os.path.join(tri.OUT, "focus", args.subject + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    ends = sum(1 for b in res["blocks"] if b["at_end"])
    print(f"{args.subject:<38s} n={n:<4d} sampled={len(idx):<3d} "
          f"blocks_at_bracket_end={ends}/{GRID_R * GRID_C}  "
          f"motion_path={res.get('motion', {}).get('path_px_rawG', '?')}px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
