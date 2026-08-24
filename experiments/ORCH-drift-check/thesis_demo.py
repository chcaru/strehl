"""Selection versus estimation, on the owner's own photograph, at the exposure
that makes the difference visible.

This is the project's thesis reduced to one image. `--gate 0` is pure
selection: every output pixel is exactly one frame's pixel and nothing is
averaged (M87 `halo.rs` header). `--gate 2` is the shipped estimator: frames
whose regularised focus response is within the gate of the winner's are
averaged, so the output is an estimate rather than a choice.

`leaf-2-cpl` is the right subject because it needed +3.19 stops -- a 9.13x
gain -- which multiplies whatever noise survives the merge by 9.13 and makes
the comparison legible instead of theoretical. **The exposure is FIXED at
--exposure=3.19 for both arms**, not auto, so the two renders differ in the
merge alone and not in the tone mapping.

The comparison crop is chosen on the MEAN of the two renders, so neither arm
selects the view (discipline 671). The flat region used for the noise number
is chosen the same way, for the same reason.
"""
import os
import re
import subprocess
import time
import numpy as np
import tifffile
from PIL import Image

NAME = "leaf-2-cpl"
SRC = r"D:\personal\macro\%s" % NAME
OUT = r"C:\dev\strehl-out\ORCH-thesis"
EXE = r".cargo-target-orch\release\strehl.exe"
STOPS = "3.19"
os.makedirs(OUT, exist_ok=True)

NEFF = re.compile(r"^\s*[\d.]+\s+[\d.]+\s+([\d.]+)\s+[\d.]+%", re.M)

arms = {}
for tag, gate in (("selection-gate0", "0"), ("estimation-gate2", "2")):
    dst = os.path.join(OUT, "%s-%s.tif" % (NAME, tag))
    if not os.path.exists(dst):
        print("rendering %s (--gate %s) ..." % (tag, gate), flush=True)
        t0 = time.perf_counter()
        r = subprocess.run(
            [EXE, "stack", SRC, "--out", dst, "--srgb",
             "--exposure=" + STOPS, "--gate", gate],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit((r.stderr or "")[-3000:])
        m = NEFF.search(r.stderr or "")
        print("  %.1f s%s" % (time.perf_counter() - t0,
                              (", mean n_eff %s" % m.group(1)) if m else ""), flush=True)
    arms[tag] = tifffile.imread(dst).astype(np.float32) / 65535.0

a = arms["selection-gate0"]
b = arms["estimation-gate2"]
assert a.shape == b.shape, (a.shape, b.shape)
mean = 0.5 * (a + b)

# --- the flat region, chosen on the mean so neither arm selects it ----------
g = mean.mean(axis=2)
s = 16
gs = g[::s, ::s]
gx = np.zeros_like(gs); gy = np.zeros_like(gs)
gx[:, 1:-1] = gs[:, 2:] - gs[:, :-2]
gy[1:-1, :] = gs[2:, :] - gs[:-2, :]
e = gx * gx + gy * gy
k = 200 // (2 * s)
c = np.zeros((e.shape[0] + 1, e.shape[1] + 1))
np.cumsum(np.cumsum(e.astype(np.float64), 0), 1, out=c[1:, 1:])
H, W = e.shape
m = 3 * k  # keep the window off the frame edge
y0 = np.clip(np.arange(H) - k, 0, H); y1 = np.clip(np.arange(H) + k, 0, H)
x0 = np.clip(np.arange(W) - k, 0, W); x1 = np.clip(np.arange(W) + k, 0, W)
tot = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
       - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
tot[:m, :] = np.inf; tot[-m:, :] = np.inf
tot[:, :m] = np.inf; tot[:, -m:] = np.inf
fy, fx = np.unravel_index(int(np.argmin(tot)), tot.shape)
fy, fx = fy * s, fx * s
F = 200


def hp_sigma(img, y, x, n=F):
    """Noise as the SD of a 3x3 Laplacian residual, normalised so that white
    noise of SD s reads back s. Insensitive to the smooth gradient a flat
    region still carries, which a raw SD is not."""
    p = img[y:y + n, x:x + n].mean(axis=2).astype(np.float64)
    lap = (4 * p[1:-1, 1:-1] - p[:-2, 1:-1] - p[2:, 1:-1]
           - p[1:-1, :-2] - p[1:-1, 2:])
    return float(lap.std() / np.sqrt(20.0))


sa, sb = hp_sigma(a, fy, fx), hp_sigma(b, fy, fx)
print()
print("flat region at y=%d x=%d (%dx%d), chosen on the MEAN of both arms" % (fy, fx, F, F))
print("  selection  --gate 0 : sigma %.6f" % sa)
print("  estimation --gate 2 : sigma %.6f" % sb)
print("  ratio               : %.4fx   (%.1f%% less noise)"
      % (sb / sa, 100 * (1 - sb / sa)))
print("  equivalent frames averaged : %.2f" % ((sa / sb) ** 2))

# --- the detail crop, also chosen on the mean ------------------------------
gsd = g[::8, ::8]
gx = np.zeros_like(gsd); gy = np.zeros_like(gsd)
gx[:, 1:-1] = gsd[:, 2:] - gsd[:, :-2]
gy[1:-1, :] = gsd[2:, :] - gsd[:-2, :]
ed = gx * gx + gy * gy
kk = 700 // 16
cc = np.zeros((ed.shape[0] + 1, ed.shape[1] + 1))
np.cumsum(np.cumsum(ed.astype(np.float64), 0), 1, out=cc[1:, 1:])
H, W = ed.shape
y0 = np.clip(np.arange(H) - kk, 0, H); y1 = np.clip(np.arange(H) + kk, 0, H)
x0 = np.clip(np.arange(W) - kk, 0, W); x1 = np.clip(np.arange(W) + kk, 0, W)
td = (cc[np.ix_(y1, x1)] - cc[np.ix_(y0, x1)]
      - cc[np.ix_(y1, x0)] + cc[np.ix_(y0, x0)])
dy, dx = np.unravel_index(int(np.argmax(td)), td.shape)
dy, dx = dy * 8, dx * 8
N = 700
y = int(np.clip(dy - N // 2, 0, a.shape[0] - N))
x = int(np.clip(dx - N // 2, 0, a.shape[1] - N))

bar = np.full((N, 6, 3), 255, np.uint8)
Image.fromarray(np.concatenate([
    (a[y:y + N, x:x + N] * 255).astype(np.uint8), bar,
    (b[y:y + N, x:x + N] * 255).astype(np.uint8)], axis=1)).save(
    os.path.join(OUT, "SBS-detail-SELECTION-left-ESTIMATION-right.png"))

fbar = np.full((F, 6, 3), 255, np.uint8)
Image.fromarray(np.concatenate([
    (a[fy:fy + F, fx:fx + F] * 255).astype(np.uint8), fbar,
    (b[fy:fy + F, fx:fx + F] * 255).astype(np.uint8)], axis=1)).save(
    os.path.join(OUT, "SBS-flat-SELECTION-left-ESTIMATION-right.png"))

# The flat patch again at 4x nearest-neighbour, because 200 px of noise is not
# legible at 1:1 on a screenshot and the whole point is that you can see it.
za = np.repeat(np.repeat(a[fy:fy + F, fx:fx + F], 4, 0), 4, 1)
zb = np.repeat(np.repeat(b[fy:fy + F, fx:fx + F], 4, 0), 4, 1)
zbar = np.full((F * 4, 8, 3), 255, np.uint8)
Image.fromarray(np.concatenate([
    (za * 255).astype(np.uint8), zbar, (zb * 255).astype(np.uint8)], axis=1)).save(
    os.path.join(OUT, "SBS-flat-4x-SELECTION-left-ESTIMATION-right.png"))

print()
print("detail crop at y=%d x=%d" % (y, x))
print("wrote %s" % OUT)
