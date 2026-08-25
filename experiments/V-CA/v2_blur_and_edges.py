"""V-CA v2 -- two questions the corpus leaves open on the CA arms.

Q_A  How large is the improvement on the SAME population M107b's W3 and M110's
     decile-10 used (top-decile luma gradient), so the 61.0 % headline can be
     placed on a ladder with the whole-frame figure?

Q_B  Does the CA arm pay resampling blur?  There is no `anti` arm (fact 1529:
     no strength knob; running one needs a source change), so this cannot be a
     clean placebo.  What it CAN do is bound the nuisance: red is the only
     plane resampled differently, so compare the high-band energy change in
     RED against the change in GREEN, which is resampled identically in both
     arms and therefore carries only demosaic coupling.  A large red-specific
     high-band loss is what a blur-driven "improvement" would look like.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")


def luma(f):
    return 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]


def lap(a):
    o = np.zeros_like(a)
    o[1:-1, 1:-1] = (4*a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1]
                     - a[1:-1, :-2] - a[1:-1, 2:])
    return o


def run(subject, on_name="ca"):
    off = tifffile.imread(str(ROOT / subject / "default.tif")).astype(np.float32)
    on = tifffile.imread(str(ROOT / subject / f"{on_name}.tif")).astype(np.float32)
    print(f"\n===== {subject}: default -> {on_name} =====")

    yo = luma(off)
    gy = np.zeros_like(yo); gx = np.zeros_like(yo)
    gy[1:-1, :] = np.abs(yo[2:, :] - yo[:-2, :])
    gx[:, 1:-1] = np.abs(yo[:, 2:] - yo[:, :-2])
    g = gy + gx
    thr = float(np.percentile(g[::7, ::7], 90.0))
    edge = g >= thr

    do = np.abs(off[..., 0] - luma(off)); dn = np.abs(on[..., 0] - luma(on))
    print(f"  Q_A mean|R-Y|   whole frame  {do.mean():8.1f} -> {dn.mean():8.1f}"
          f"  {100*(dn.mean()/do.mean()-1):+7.2f}%")
    print(f"      mean|R-Y|   top-decile gradient (n={int(edge.sum())})"
          f"  {do[edge].mean():8.1f} -> {dn[edge].mean():8.1f}"
          f"  {100*(dn[edge].mean()/do[edge].mean()-1):+7.2f}%")

    print("  Q_B high-band (Laplacian) RMS, whole frame:")
    for ci, nm in ((0, "R"), (1, "G"), (2, "B")):
        a = float(np.sqrt((lap(off[..., ci])**2).mean()))
        b = float(np.sqrt((lap(on[..., ci])**2).mean()))
        print(f"      {nm}: {a:10.2f} -> {b:10.2f}   {100*(b/a-1):+7.3f}%")
    print("  Q_B high-band (Laplacian) RMS, on edge pixels only:")
    for ci, nm in ((0, "R"), (1, "G"), (2, "B")):
        la = lap(off[..., ci]); lb = lap(on[..., ci])
        a = float(np.sqrt((la[edge]**2).mean())); b = float(np.sqrt((lb[edge]**2).mean()))
        print(f"      {nm}: {a:10.2f} -> {b:10.2f}   {100*(b/a-1):+7.3f}%")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        run(s)
