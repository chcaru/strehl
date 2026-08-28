"""Fit the displacement the lateral-CA correction applies, per channel.

Usage:
    python cafit.py <ca-off.tiff> <ca-on.tiff>

Bit-exactness says the two renders differ. It does not say whether the
difference is the RIGHT KIND of difference. A lateral chromatic aberration
correction has a specific signature: displacement proportional to radius from
the optical centre, zero on green (the reference channel), and OPPOSITE in sign
between red and blue. Anything else -- a constant offset, a random field, the
same sign on R and B -- would mean the correction is not doing what it claims.

Both inputs are the same render with the correction off and on, so the scene
content is identical and a local gradient (Lucas-Kanade) estimate measures the
applied displacement directly rather than the scene's own colour structure.

Fits shift = alpha * (p - centre) blockwise and reports alpha per channel plus
the displacement it implies at the image corner, in pixels.
"""

import sys

import numpy as np
import tifffile

B = 128  # block side


def block_shift(a, b):
    """Lucas-Kanade translation taking `a` onto `b` over one block."""
    gy, gx = np.gradient(a)
    d = b - a
    A = np.array([[(gx * gx).sum(), (gx * gy).sum()], [(gx * gy).sum(), (gy * gy).sum()]])
    if np.linalg.cond(A) > 1e8:
        return None
    return np.linalg.solve(A, np.array([-(gx * d).sum(), -(gy * d).sum()]))


def main() -> int:
    off = np.asarray(tifffile.imread(sys.argv[1])).astype(np.float64)
    on = np.asarray(tifffile.imread(sys.argv[2])).astype(np.float64)
    h, w = off.shape[0], off.shape[1]
    cx, cy = w / 2.0, h / 2.0
    print(f"{w}x{h}, centre ({cx:.1f},{cy:.1f}), {B}px blocks")
    print(f"{'ch':>3}  {'alpha (px/px)':>14}  {'corner px':>10}  {'blocks':>7}  {'r (radial fit)':>15}")
    for c, name in enumerate("RGB"):
        rs, ss = [], []
        for by in range(0, h - B, B):
            for bx in range(0, w - B, B):
                s = block_shift(off[by : by + B, bx : bx + B, c], on[by : by + B, bx : bx + B, c])
                if s is None:
                    continue
                px, py = bx + B / 2 - cx, by + B / 2 - cy
                r = np.hypot(px, py)
                if r < 1.0:
                    continue
                # Radial component of the measured shift.
                rs.append(r)
                ss.append((s[0] * px + s[1] * py) / r)
        rs, ss = np.array(rs), np.array(ss)
        alpha = float((rs * ss).sum() / (rs * rs).sum())
        pred = alpha * rs
        ss_res = ((ss - pred) ** 2).sum()
        ss_tot = ((ss - ss.mean()) ** 2).sum()
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        corner = alpha * np.hypot(cx, cy)
        print(f"{name:>3}  {alpha:14.3e}  {corner:10.4f}  {len(rs):7d}  {r2:15.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
