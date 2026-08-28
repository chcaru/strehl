"""Find the integer shift, if any, that best aligns two same-size renders.

Usage:
    python shiftprobe.py <a.tiff> <b.tiff> [radius]

Scans integer (dx, dy) in [-radius, radius] and reports the mean |diff| of the
overlap for each, sorted. A half-pixel resample shows up as "0,0 is best but
not zero"; a true off-by-one shows up as a non-zero argmin.
"""

import sys

import numpy as np
import tifffile


def main() -> int:
    a = np.asarray(tifffile.imread(sys.argv[1])).astype(np.int32)
    b = np.asarray(tifffile.imread(sys.argv[2])).astype(np.int32)
    r = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    if a.shape != b.shape:
        print(f"shape mismatch {a.shape} {b.shape}")
        return 2
    h, w = a.shape[0], a.shape[1]
    # Work on a central patch so no shift runs off the edge, and so border
    # effects cannot dominate the statistic.
    y0, x0 = h // 4, w // 4
    ph, pw = h // 2, w // 2
    base = a[y0 : y0 + ph, x0 : x0 + pw]
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            shifted = b[y0 + dy : y0 + dy + ph, x0 + dx : x0 + dx + pw]
            d = np.abs(base - shifted)
            out.append((float(d.mean()), dx, dy, int((d == 0).sum()), d.size))
    out.sort()
    print(f"patch {pw}x{ph} at ({x0},{y0}) of {w}x{h}")
    for m, dx, dy, eq, n in out[:6]:
        print(f"  dx={dx:+d} dy={dy:+d}  mean|diff|={m:9.4f}  exact={100.0 * eq / n:7.3f} %")
    m, dx, dy, _, _ = out[0]
    print(f"  ARGMIN: dx={dx:+d} dy={dy:+d} (mean |diff| {m:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
