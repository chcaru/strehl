#!/usr/bin/env python3
"""Verify the tile_stats block-reduction refactor did not move any number.

The reshape/transpose form and the direct reduction form must agree.  They are
NOT expected to be bit-identical (the old form accumulated in float32, the new
one in float64), so this prints the actual relative difference and gates on it
being far below the smallest effect this study will claim.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

TS = 128


def old_tile_stats(g1, g2, ts):
    h, w = g1.shape
    nr, nc = h // ts, w // ts
    g1 = g1[: nr * ts, : nc * ts]
    g2 = g2[: nr * ts, : nc * ts]

    def blocks(x):
        return x.reshape(nr, ts, nc, ts).transpose(0, 2, 1, 3).reshape(nr, nc, -1)

    level = blocks(0.5 * (g1 + g2)).mean(axis=2)
    b1, b2 = ora.bands(g1), ora.bands(g2)
    var = np.zeros((ora.NBAND, nr, nc), np.float64)
    cov = np.zeros((ora.NBAND, nr, nc), np.float64)
    for b in range(ora.NBAND):
        p1, p2 = blocks(b1[b]), blocks(b2[b])
        var[b] = 0.5 * ((p1 * p1).mean(axis=2) + (p2 * p2).mean(axis=2))
        cov[b] = (p1 * p2).mean(axis=2)
    return {"level": level, "var": var, "cov": cov, "nr": nr, "nc": nc}


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "flowers-cpl"
    fs = ora.frames_of(subject)
    ok = True
    for k in (0, len(fs) // 2, len(fs) - 1):
        g1, g2 = ora.green_pair(fs[k])
        a = old_tile_stats(g1, g2, TS)
        b = ora.tile_stats(g1, g2, TS)
        for key in ("level", "var", "cov"):
            d = np.abs(a[key] - b[key])
            scale = np.abs(a[key]).max()
            rel = float(d.max() / scale) if scale > 0 else 0.0
            if rel > 1e-5:
                ok = False
            print(f"  frame {k:4d}  {key:6s}  max |old-new| = {d.max():.6e}  "
                  f"relative to max |old| ({scale:.4g}) = {rel:.3e}")
    print(f"\nrefactor is numerically inert to <1e-5 relative: "
          f"{'PASS' if ok else 'FAIL'}")
    print("The smallest effect this study reports is a 5% band-power change")
    print("(the P4 detection floor), which is 5000x larger than this bound.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
