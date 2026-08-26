"""Pictures. A crop of the real pixels around a straight piece of silhouette,
stretched LINEARLY (no tone curve), plus the registered ray profile beside it.
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment

SRC, LABEL, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

shape, lum = load_lum(SRC, "G")
subject, backdrop, diag = segment(lum)
sd = (ndimage.distance_transform_edt(~subject)
      - ndimage.distance_transform_edt(subject)).astype(np.float32)
far = float(np.median(lum[backdrop & (sd > 600) & (sd < 1400)]))

er = ndimage.binary_erosion(subject, iterations=1, border_value=1)
bnd = subject & ~er
dens = ndimage.uniform_filter(bnd.astype(np.float32), size=41, mode="nearest")
fi = dens * 41 * 41 / 41.0

h, w = subject.shape
ys, xs = np.nonzero(bnd)
ok = (ys > 500) & (ys < h - 500) & (xs > 500) & (xs < w - 500) & (fi[ys, xs] <= 1.0)
ys, xs = ys[ok], xs[ok]
print(f"{LABEL}: {ys.size} straight boundary points away from the frame edge")

# pick the straight point whose outward 300 px stays in backdrop the longest
sm = ndimage.gaussian_filter(sd, 4.0)
gy, gx = np.gradient(sm)
n = np.sqrt(gy * gy + gx * gx) + 1e-6
best, bi = -1, 0
step = max(1, ys.size // 3000)
for i in range(0, ys.size, step):
    y0, x0 = ys[i], xs[i]
    ny, nx = gy[y0, x0] / n[y0, x0], gx[y0, x0] / n[y0, x0]
    t = np.arange(0, 300, 4.0)
    yy = np.clip(y0 + ny * t, 0, h - 1).astype(int)
    xx = np.clip(x0 + nx * t, 0, w - 1).astype(int)
    sc = backdrop[yy, xx].sum() + 0.001 * min(y0, h - y0, x0, w - x0)
    if sc > best:
        best, bi = sc, i
y0, x0 = int(ys[bi]), int(xs[bi])
ny, nx = gy[y0, x0] / n[y0, x0], gx[y0, x0] / n[y0, x0]
print(f"  crop anchored at (x={x0}, y={y0}), outward normal ({nx:+.2f},{ny:+.2f})")

# rotate so the outward normal points right, then take a rectangle
ang = np.degrees(np.arctan2(ny, nx))
CH, CW = 420, 460
pad = 700
sub = lum[max(0, y0 - pad):y0 + pad, max(0, x0 - pad):x0 + pad]
cy, cx = y0 - max(0, y0 - pad), x0 - max(0, x0 - pad)
rot = ndimage.rotate(sub, ang, reshape=False, order=1, mode="nearest")
# rotation is about the array centre; find where the anchor went
h2, w2 = sub.shape
a = np.radians(-ang)
dy, dx = cy - h2 / 2, cx - w2 / 2
ry = h2 / 2 + (dx * np.sin(a) + dy * np.cos(a))
rx = w2 / 2 + (dx * np.cos(a) - dy * np.sin(a))
ry, rx = int(round(ry)), int(round(rx))
crop = rot[max(0, ry - CH // 2):ry + CH // 2, max(0, rx - 60):rx + CW]

lo, hi = 0.35 * far, 1.06 * far
disp = np.clip((crop - lo) / (hi - lo), 0, 1)

fig = plt.figure(figsize=(13, 5.2), dpi=150)
ax = fig.add_axes([0.04, 0.12, 0.42, 0.80])
ax.imshow(disp, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
ax.axvline(60, color="#00b0ff", lw=1.0)
for t, c in ((60 + 34, "#ff3b30"), (60 + 65, "#ffd400")):
    ax.axvline(t, color=c, lw=1.0, ls="--")
ax.set_title(f"{LABEL}: linear pixels, no tone curve\n"
             f"blue = silhouette, red = +34 px, yellow = +65 px", fontsize=9)
ax.set_xlabel("px outward from the silhouette")
ax.set_xticks([60, 60 + 50, 60 + 100, 60 + 150, 60 + 200, 60 + 250, 60 + 300])
ax.set_xticklabels([0, 50, 100, 150, 200, 250, 300])
ax.set_yticks([])

jp = Path(r"C:\dev\strehl-out\V-RIM\json2") / f"{LABEL}-rays.json"
ax2 = fig.add_axes([0.55, 0.12, 0.42, 0.80])
if jp.exists():
    d = json.loads(jp.read_text())
    for key, col, lab in (("all", "#333333", "all rays"),
                          ("straight", "#0066cc", "straightest quartile"),
                          ("fringed", "#cc0000", "most fringed quartile")):
        r = d.get(key)
        if not r:
            continue
        g = np.array(r["grid"]); m = np.array(r["med"])
        ax2.plot(g, (m - r["far"]) / r["far"] * 100, color=col, lw=1.4,
                 label=f"{lab} (n={r['n']})")
    ax2.axhline(0, color="#888888", lw=0.8)
    ax2.axvline(0, color="#00b0ff", lw=0.8)
    ax2.set_xlim(-20, 300)
    ax2.legend(fontsize=8)
ax2.set_xlabel("px outward from the ray's own edge crossing")
ax2.set_ylabel("backdrop luminance, % of that ray's far field")
ax2.set_title("registered ray profile (linear)", fontsize=9)
ax2.grid(alpha=0.25)
p = OUT / f"{LABEL}-ring.png"
fig.savefig(p)
print(f"  wrote {p}")
