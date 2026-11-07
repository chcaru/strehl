"""Locally-sharpest single-frame composite from SCENE-LINEAR masters, streamed.

usage: localref-linear.py build CAPTURE_DIR WARP_MAP OUT_DIR FIRST STEP COUNT [tile]
       localref-linear.py score OUT_DIR/composite.npy ARM_LINEAR.tif [...]

Like localref.py, but every single-frame render (STREHL_FRAME_PARITY=i-i under
one warp map, so pixel-aligned) is a scene-linear float master, so no render's
tone anchors enter the comparison; each master is folded into the composite
and deleted at once, keeping disk use to one frame. Per tile the frame with the
most green high-pass (x - box3) energy wins; the composite keeps that frame's
linear luminance.

score: dark pixels of the composite (9x9 mean below 2% of its 99.5th
percentile) binned by distance to bright pixels (above 25%); per bin, arm mean
luminance / composite mean luminance. A merge that adds glow reads above 1;
with linear masters a level offset reads as a ratio that does not fall back to
1 far from edges.

Can be fooled: the composite is an in-focus observation only on a planar
subject without depth discontinuities inside a tile; its tile seams are kept
out of the masks by the 9x9 means.
"""
import os
import subprocess
import sys
import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, uniform_filter

S = r"C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe"


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


if sys.argv[1] == "build":
    cap, warp, out = sys.argv[2], sys.argv[3], sys.argv[4]
    first, step, count = int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
    t = int(sys.argv[8]) if len(sys.argv) > 8 else 64
    best = comp = None
    env = dict(os.environ, STREHL_WARPMAP=warp)
    for n in range(count):
        i = first + n * step
        env["STREHL_FRAME_PARITY"] = f"{i}-{i}"
        lin = os.path.join(out, "frame-lin.tif")
        srgb = os.path.join(out, "frame-srgb.tif")
        r = subprocess.run([S, "stack", cap, "-o", srgb, "--srgb", "--linear-master", lin],
                           env=env, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"frame {i}: exit {r.returncode}\n{r.stderr[-2000:]}")
        a = tifffile.imread(lin).astype(np.float32)
        os.remove(lin)
        os.remove(srgb)
        y = luma(a)
        g = a[..., 1]
        hp = (g - uniform_filter(g, 3)) ** 2
        h, w = y.shape
        th, tw = h // t, w // t
        e = hp[: th * t, : tw * t].reshape(th, t, tw, t).mean((1, 3))
        if best is None:
            best = np.full((th, tw), -1.0, np.float32)
            comp = np.zeros((h, w), np.float32)
            src = np.full((th, tw), -1, np.int32)
        win = e > best
        best[win] = e[win]
        src[win] = i
        m = np.kron(win, np.ones((t, t), bool))
        mm = np.zeros((h, w), bool)
        mm[: th * t, : tw * t] = m
        comp[mm] = y[mm]
        print(f"frame {i}: wins {int(win.sum())} tiles", flush=True)
    np.save(os.path.join(out, "composite.npy"), comp)
    np.save(os.path.join(out, "composite-source.npy"), src)
    print(f"composite of {count} frames -> {out}/composite.npy")
    sys.exit(0)

ref = np.load(sys.argv[2])
m = uniform_filter(ref, 9)
top = np.quantile(m, 0.995)
bright = m > 0.25 * top
dark = m < 0.02 * top
inner = np.zeros_like(dark)
inner[100:-100, 100:-100] = True
dist = distance_transform_edt(~bright)
edges = [2, 8, 16, 32, 64, 128, 256]
print(f"bright level {top:.4f}; dark fraction {dark.mean():.3f}")
for p in sys.argv[3:]:
    a = uniform_filter(luma(tifffile.imread(p).astype(np.float32)), 3)
    if a.shape != ref.shape:
        sys.exit(f"{p}: shape {a.shape} differs from composite {ref.shape}")
    cells = []
    for lo, hi in zip(edges, edges[1:]):
        sel = dark & inner & (dist >= lo) & (dist < hi)
        cells.append(f"{lo}-{hi}px {a[sel].mean() / ref[sel].mean():.2f}")
    sel = dark & inner
    print(f"{os.path.basename(p):18s} dark mean {a[sel].mean():.5f} (ref {ref[sel].mean():.5f}) | " + " ".join(cells))
