#!/usr/bin/env python3
"""Why did C4 move the mean by +1406 DN?  A rescale cannot do that.

Either catmull_rom_scale is wrong, or the CONTROL is comparing two windows
that hold different content -- which would be this project's signature error
committed inside the very instrument built to avoid it.  Settle it on
synthetic data where the right answer is known in closed form.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

N = 768
print("synthetic checks of catmull_rom_scale")

const = np.full((N, N), 1234.5, np.float32)
r = tri.catmull_rom_scale(const, 0.99)
print(f"  constant 1234.5 -> mean {r.mean():.4f}  max|err| {np.abs(r - 1234.5).max():.6f}")

yy = np.arange(N, dtype=np.float32)[:, None] * np.ones((1, N), np.float32)
r = tri.catmull_rom_scale(yy, 0.99)
c = (N - 1) / 2.0
want = (np.arange(N, dtype=np.float32) - c) * 0.99 + c
print(f"  vertical ramp: max|err| vs closed form "
      f"{np.abs(r - want[:, None]).max():.6f}")
xr = np.arange(N, dtype=np.float32)[None, :] * np.ones((N, 1), np.float32)
r = tri.catmull_rom_scale(xr, 0.99)
print(f"  horizontal ramp: max|err| vs closed form "
      f"{np.abs(r - want[None, :]).max():.6f}")

# How far does content actually move at the edge of a 512 window inside 768?
for k in (0.991277, 0.95):
    d = (1 - k) * (N - 1) / 2.0
    print(f"  k={k}: content at the frame edge moves {d:.2f} px")

# And on real pixels: is the mean shift explained by displacement?
src = os.path.join(tri.LIN, "109MSDCF.tiff")
if os.path.exists(src):
    y = tri.luma(tri.load16(src))
    cy, cx = 1312, 2912
    tile = np.ascontiguousarray(y[cy:cy + 512, cx:cx + 512])
    print(f"\n real pixels at ({cx},{cy}):")
    print(f"  tile mean            {tile.mean():10.2f} DN")
    for dy in (-8, -4, -2, 0, 2, 4, 8):
        t2 = y[cy + dy:cy + dy + 512, cx:cx + 512]
        print(f"  window shifted {dy:+3d}px  {t2.mean():10.2f} DN   "
              f"(delta {t2.mean() - tile.mean():+9.2f})")
    big = np.ascontiguousarray(y[cy - 128:cy + 512 + 128, cx - 128:cx + 512 + 128])
    rs = tri.catmull_rom_scale(big, 0.991277)
    print(f"  big mean {big.mean():.2f} -> rescaled-whole mean {rs.mean():.2f} DN "
          f"(delta {rs.mean() - big.mean():+.2f}) <- whole-frame mean IS conserved")
    print(f"  centre 512 of big     {big[128:640, 128:640].mean():10.2f} DN")
    print(f"  centre 512 of rescale {rs[128:640, 128:640].mean():10.2f} DN")
