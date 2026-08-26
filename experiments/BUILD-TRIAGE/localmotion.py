#!/usr/bin/env python3
"""Local, non-rigid motion: did the SUBJECT change shape during the bracket?

The stage-1 detector measures rigid translation of the whole frame by phase
correlation.  That is precisely the component the aligner removes, so it fires
on drift and is blind to the thing that actually damages a merge: a subject
that DEFORMS -- bubbles creeping, foam collapsing, a petal relaxing.
coffee-bubbles proves the blindness: it scores 3.0 px of global path, which is
nothing, while its 1:1 crops plainly show the merge and the winning frame
disagreeing about where the specular rims are.

The discriminator used here: ADJACENT frames in a bracket are one focus step
apart, so their coarse structure is very nearly identical.  Take a dense run of
CONSECUTIVE frames, low-pass hard (which removes the focus difference, since
defocus is a high-frequency loss), register out the rigid part, and correlate.
What is left is the scene changing under the camera.

Reported per block and per subject, so a subject that moved in one place --
which is what bubbles and foam do -- is not averaged into looking static.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
from focuscurve import GRID_C, GRID_R, green_plane, phase_shift  # noqa: E402


def boxdown(g: np.ndarray, f: int) -> np.ndarray:
    h, w = (g.shape[0] // f) * f, (g.shape[1] // f) * f
    return g[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--run", type=int, default=16, help="consecutive frames")
    ap.add_argument("--down", type=int, default=4)
    args = ap.parse_args()

    d = os.path.join(tri.RAW, args.subject)
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
    n = len(files)
    run = min(args.run, n)
    start = max(0, n // 2 - run // 2)
    sel = list(range(start, start + run))

    low = []
    for k in sel:
        low.append(boxdown(green_plane(os.path.join(d, files[k])), args.down))

    h, w = low[0].shape
    per_pair: list[float] = []
    blockmin = np.ones((GRID_R, GRID_C), np.float64)
    for i in range(1, len(low)):
        a, b = low[i - 1], low[i]
        dy, dx = phase_shift(a, b)
        bb = np.roll(np.roll(b, int(dy), axis=0), int(dx), axis=1)
        m = 8 + int(max(abs(dy), abs(dx)))
        vals = []
        for r in range(GRID_R):
            for c in range(GRID_C):
                y0 = int(r / GRID_R * h) + m
                y1 = int((r + 1) / GRID_R * h) - m
                x0 = int(c / GRID_C * w) + m
                x1 = int((c + 1) / GRID_C * w) - m
                if y1 - y0 < 8 or x1 - x0 < 8:
                    continue
                v = ncc(a[y0:y1, x0:x1], bb[y0:y1, x0:x1])
                if np.isfinite(v):
                    vals.append(v)
                    blockmin[r, c] = min(blockmin[r, c], v)
        if vals:
            per_pair.append(float(np.median(vals)))

    res = {
        "subject": args.subject,
        "n_frames": n,
        "run": sel,
        "down": args.down,
        "pair_ncc_median": [round(v, 5) for v in per_pair],
        "worst_pair_ncc": round(float(np.min(per_pair)), 5) if per_pair else None,
        "median_pair_ncc": round(float(np.median(per_pair)), 5) if per_pair else None,
        "worst_block_ncc": round(float(blockmin.min()), 5),
        "block_min_ncc": [[round(float(v), 5) for v in row] for row in blockmin],
        "n_blocks_below_0995": int((blockmin < 0.995).sum()),
        "n_blocks_below_098": int((blockmin < 0.98).sum()),
    }
    out = os.path.join(tri.OUT, "motion", args.subject + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"{args.subject:<38s} med_pair={res['median_pair_ncc']}  "
          f"worst_pair={res['worst_pair_ncc']}  "
          f"worst_block={res['worst_block_ncc']}  "
          f"blocks<0.98={res['n_blocks_below_098']}/{GRID_R * GRID_C}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
