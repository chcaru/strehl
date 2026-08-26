"""Does ANY frame have sharp trichomes where the merge pours milk?

H4 at the band -- the location the owner actually cares about. Earlier I tested
H4 at pale-wash, an interior ROI, and at three bee ROIs. Never here. Single
frames across the bracket already exist in ORCH-rim, so this costs no render.
"""
import glob, re, numpy as np, tifffile, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

MERGE = r"C:\dev\strehl-out\BUILD-ELECT\accept\fb-mean.tiff"
frames = sorted(glob.glob(r"C:\dev\strehl-out\ORCH-rim\fb-f*-lin.tif"),
                key=lambda p: int(re.search(r"f(\d+)", p).group(1)))
print("frames found:", [re.search(r"fb-f(\d+)", p).group(1) for p in frames])

ref = tifffile.imread(MERGE).astype(np.float32)
lum = ref.mean(axis=2)
lo, hi = np.percentile(lum, [5, 95]); m = lum < 0.5 * (lo + hi)
lab, n = ndimage.label(m); sizes = ndimage.sum(m, lab, range(1, n + 1))
m = lab == (1 + int(np.argmax(sizes)))
pad = 8
d_out = ndimage.distance_transform_edt(~np.pad(m, pad, constant_values=False))[pad:-pad, pad:-pad]
white = float(np.median(lum[(d_out > 600) & (d_out < 1400)]))

cy, cx, H = 872, 3701, 230           # same locus as ACCEPT-fb-arms, tighter
sl = (slice(cy - H, cy + H), slice(cx - H, cx + H))
band = (d_out[sl] >= 8) & (d_out[sl] <= 40)

def view(a): return np.clip(a / (white * 1.15), 0, 1) ** (1 / 2.2)
def sharp(a):
    """Peak gradient of the high-pass inside the band: 'are there crisp hairs'."""
    g = a.mean(axis=2)
    hp = g - ndimage.gaussian_filter(g, 8.0)
    gx = ndimage.sobel(hp, 1) * 0.125; gy = ndimage.sobel(hp, 0) * 0.125
    mag = np.hypot(gx, gy)
    return float(np.percentile(mag[band], 99.5)), float(np.median(g[band]))

panels = [("MERGE (mean)", ref[sl])]
for p in frames:
    panels.append((re.search(r"fb-(f\d+)", p).group(1),
                   tifffile.imread(p).astype(np.float32)[sl]))

fig, axes = plt.subplots(2, 4, figsize=(20, 10.5))
print(f"\n{'panel':>14}{'band luma DN':>15}{'% far field':>13}{'hp p99.5 |grad|':>18}")
for ax, (tag, a) in zip(axes.ravel(), panels):
    s, l = sharp(a)
    ax.imshow(view(a)); ax.set_xticks([]); ax.set_yticks([])
    ax.contour(d_out[sl], levels=[0.5], colors="r", linewidths=0.5)
    ax.set_title(f"{tag}\nband {l:.0f} DN = {100*l/white:.0f}%   hp|grad| p99.5 = {s:.0f}")
    print(f"{tag:>14}{l:>15.0f}{100*l/white:>13.1f}{s:>18.1f}")
for ax in axes.ravel()[len(panels):]: ax.axis("off")
fig.suptitle("flower-bud: the milk band in the merge, and in single frames across the bracket",
             fontsize=14)
plt.tight_layout()
out = r"C:\dev\strehl-out\BUILD-ELECT\pics\BAND-frames.png"
plt.savefig(out, dpi=78); print("\nwrote", out)
