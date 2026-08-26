"""couch-fibers-cpl: the owner calls this audited-good and print-worthy, and it is
nothing but dense fine structure. H5 says dense fine structure against a bright
backdrop fools a density-based focus measure. So this subject is a free test of
H5's sufficient condition -- if density alone were enough, the best-audited image
in the library would be the worst."""
import numpy as np, tifffile, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

p = r"C:\dev\strehl-out\BUILD-ELECT\accept\couch-shipped.tiff"
img = tifffile.imread(p); assert img.dtype == np.uint16
a = img.astype(np.float32)
lum = a.mean(axis=2)
lo, hi = np.percentile(lum, [5, 95])
print(f"couch-fibers  {img.shape}")
print(f"  luma p1={np.percentile(lum,1):.0f} p5={lo:.0f} p50={np.median(lum):.0f} "
      f"p95={hi:.0f} p99={np.percentile(lum,99):.0f} max={lum.max():.0f}")
print(f"  bimodality: p95/p5 = {hi/max(lo,1):.2f}   "
      f"(flower-bud 15.90, coffee-bean 17.96)")
frac_dark = float((lum < 0.5*(lo+hi)).mean()*100)
print(f"  fraction below the midpoint threshold: {frac_dark:.1f}%")

white = float(np.percentile(lum, 99.5))
view = np.clip(a/white, 0, 1) ** (1/2.2)
fig, ax = plt.subplots(1, 3, figsize=(19, 6))
ax[0].imshow(view[::8, ::8]); ax[0].set_title("couch-fibers-cpl: full frame (gamma view)")
cy, cx = lum.shape[0]//2, lum.shape[1]//2
ax[1].imshow(view[cy-400:cy+400, cx-400:cx+400]); ax[1].set_title("centre, 1:1 800px crop")
ax[2].hist(lum[::16, ::16].ravel(), bins=200)
ax[2].set_yscale("log"); ax[2].set_title("luma histogram (log count)\nbimodal = subject on a sweep")
for k in (0, 1): ax[k].set_xticks([]); ax[k].set_yticks([])
plt.tight_layout()
out = r"C:\dev\strehl-out\BUILD-ELECT\pics\COUCH-look.png"
plt.savefig(out, dpi=80); print("wrote", out)
