import numpy as np, tifffile, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

fig, axes = plt.subplots(2, 3, figsize=(19, 11))
for row, (tag, p) in enumerate((
        ("coffee-bean", r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"),
        ("flower-bud",  r"C:\dev\strehl-out\ORCH-rim\fb-1cacb61-lin.tif"))):
    img = tifffile.imread(p)
    assert img.dtype == np.uint16
    a = img.astype(np.float32)[::8, ::8]
    lum = a.mean(axis=2)
    lo, hi = np.percentile(lum, [5, 95])
    thr = 0.5 * (lo + hi)
    m = lum < thr
    lab, n = ndimage.label(m)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    big = lab == (1 + int(np.argmax(sizes)))
    white = float(np.percentile(lum, 99.5))
    view = np.clip(a / white, 0, 1) ** (1 / 2.2)

    axes[row][0].imshow(view); axes[row][0].set_title(f"{tag}: linear render (gamma view)")
    axes[row][1].imshow(m, cmap="gray")
    axes[row][1].set_title(f"lum < {thr:.0f}  ->  {m.mean()*100:.1f}% of frame, {n} components")
    axes[row][2].imshow(big, cmap="gray")
    axes[row][2].set_title(f"LARGEST component = {big.mean()*100:.1f}% of frame\n"
                           f"(this is what the distance axis is measured from)")
    for ax in axes[row]: ax.set_xticks([]); ax.set_yticks([])
    print(f"{tag}: p5={lo:.0f} p95={hi:.0f} thr={thr:.0f} "
          f"mask={m.mean()*100:.2f}% largest={big.mean()*100:.2f}% ncomp={n}")
plt.tight_layout()
out = r"C:\dev\strehl-out\BUILD-ELECT\pics\RING-masks.png"
plt.savefig(out, dpi=80); print("wrote", out)
