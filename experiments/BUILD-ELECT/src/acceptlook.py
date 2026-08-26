"""The owner's acceptance test, as a picture. Three arms, one crop, one tone
transform fixed from the measured far field so panels are comparable."""
import numpy as np, tifffile, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

O = r"C:\dev\strehl-out\BUILD-ELECT\accept"
ARMS = [("mean (shipped)", "fb-mean"), ("max  (H5's fix)", "fb-max"),
        ("hp   (my sec.4 fix)", "fb-hp")]
imgs = {t: tifffile.imread(rf"{O}\{f}.tiff").astype(np.float32) for t, f in ARMS}
ref = imgs["mean (shipped)"]
lum = ref.mean(axis=2)

lo, hi = np.percentile(lum, [5, 95]); m = lum < 0.5 * (lo + hi)
lab, n = ndimage.label(m); sizes = ndimage.sum(m, lab, range(1, n + 1))
m = lab == (1 + int(np.argmax(sizes)))
pad = 8
d_out = ndimage.distance_transform_edt(~np.pad(m, pad, constant_values=False))[pad:-pad, pad:-pad]

# Locate the crop by the artifact itself: the brightest patch of the d=10-35 band.
band = (d_out >= 10) & (d_out <= 35)
score = ndimage.uniform_filter(np.where(band, lum, 0.0), 201)
score[~ndimage.binary_dilation(band, iterations=40)] = 0
cy, cx = np.unravel_index(np.argmax(score), score.shape)
H = 460
cy = int(np.clip(cy, H, lum.shape[0] - H)); cx = int(np.clip(cx, H, lum.shape[1] - H))
print(f"crop centre from argmax of band brightness: y={cy} x={cx}")

white = float(np.median(lum[(d_out > 600) & (d_out < 1400)]))
def view(a): return np.clip(a / (white * 1.15), 0, 1) ** (1 / 2.2)

fig, ax = plt.subplots(2, 3, figsize=(18, 12))
sl = (slice(cy - H, cy + H), slice(cx - H, cx + H))
for k, (title, f) in enumerate(ARMS):
    a = imgs[title]
    ax[0][k].imshow(view(a[sl]))
    b = (d_out[sl] >= 10) & (d_out[sl] <= 35)
    lm = a[sl].mean(axis=2)
    ax[0][k].set_title(f"{title}\nband luma {np.median(lm[b]):.0f} DN "
                       f"= {100*np.median(lm[b])/white:.1f}% of far field")
    ax[0][k].contour(d_out[sl], levels=[0.5], colors="r", linewidths=0.6)
    if k == 0:
        ax[1][k].imshow(view(a[sl])); ax[1][k].set_title("same crop, silhouette in red")
        ax[1][k].contour(d_out[sl], levels=[0.5], colors="r", linewidths=0.6)
    else:
        d = np.abs(a[sl] - ref[sl]).mean(axis=2)
        ax[1][k].imshow(d, cmap="inferno", vmin=0, vmax=1500)
        ax[1][k].set_title(f"|{title.split()[0]} - mean|, {100*(d>0).mean():.1f}% of crop moved\n"
                           f"median in band {np.median(d[b]):.0f} DN")
        ax[1][k].contour(d_out[sl], levels=[0.5], colors="c", linewidths=0.6)
for r in ax:
    for a_ in r: a_.set_xticks([]); a_.set_yticks([])
fig.suptitle("flower-bud: does either candidate fix remove the bright ring? "
             "(linear render, one fixed tone transform)", fontsize=14)
plt.tight_layout()
out = r"C:\dev\strehl-out\BUILD-ELECT\pics\ACCEPT-fb-arms.png"
plt.savefig(out, dpi=78); print("wrote", out)
