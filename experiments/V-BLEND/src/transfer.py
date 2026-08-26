"""What is the shape of the BEFORE -> AFTER mapping in the shadows?

Distinguishes three mechanisms that all produce zeros:
  a smooth encoding difference  -> a single-valued monotone curve, no pile-up
  a level/offset error          -> AFTER = BEFORE - c, then clamped at 0
  a hard clamp                  -> a knee: AFTER tracks BEFORE, then collapses
Also writes a map of WHERE the zeros are, since a packaging or border artifact
looks nothing like a subject-shaped one.
"""
import sys, os
import numpy as np, tifffile
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sub = sys.argv[1]
L = r"C:\dev\strehl-out\V-BLEND\lin"
B = tifffile.imread(f"{L}\\{sub}-before.tiff"); assert B.dtype == np.uint16
A = tifffile.imread(f"{L}\\{sub}-after.tiff");  assert A.dtype == np.uint16
print(f"{sub}: shapes {B.shape} {A.shape}")

ch = 2 if "flower-bud" in sub else 1
cn = "BGR"[0] if False else ["R", "G", "B"][ch]
b = B[:, :, ch].astype(np.float32).ravel()
a = A[:, :, ch].astype(np.float32).ravel()
del B, A

print(f"\nchannel {cn}: BEFORE value -> what AFTER reads there")
print(f"  {'BEFORE bin':>16} {'npx':>12} {'AFTER med':>10} {'AFTER p10':>10} {'AFTER p90':>10} {'% AFTER==0':>11}")
edges = [0, 250, 500, 1000, 2000, 3000, 4000, 6000, 8000, 12000, 16000, 24000, 32000, 65536]
for i in range(len(edges)-1):
    m = (b >= edges[i]) & (b < edges[i+1])
    n = int(m.sum())
    if n < 100: continue
    av = a[m]
    print(f"  {edges[i]:7d}-{edges[i+1]:7d} {n:12,d} {np.median(av):10.0f} "
          f"{np.percentile(av,10):10.0f} {np.percentile(av,90):10.0f} {100.0*(av==0).mean():10.3f}%")

# a monotone single-valued curve cannot send one BEFORE bin to both 0 and full signal
m = (b >= 2000) & (b < 4000)
av = a[m]
print(f"\n  BEFORE in [2000,4000): AFTER spans p1={np.percentile(av,1):.0f} to "
      f"p99={np.percentile(av,99):.0f}, and {100.0*(av==0).mean():.2f}% sit at exactly 0.")
print("  A single-valued encoding curve cannot map one input level to both 0 and full signal.")

os.makedirs(r"C:\dev\strehl-out\V-BLEND\pics", exist_ok=True)
A2 = tifffile.imread(f"{L}\\{sub}-after.tiff")[:, :, ch]
B2 = tifffile.imread(f"{L}\\{sub}-before.tiff")[:, :, ch]
z = (A2 == 0)
ds = 8
h, w = z.shape; h -= h % ds; w -= w % ds
zm = z[:h, :w].reshape(h//ds, ds, w//ds, ds).mean(axis=(1, 3))
bm = B2[:h, :w].reshape(h//ds, ds, w//ds, ds).mean(axis=(1, 3))
fig, ax = plt.subplots(1, 2, figsize=(15, 5.2))
ax[0].imshow(np.clip(bm/np.percentile(bm, 99.5), 0, 1)**0.45, cmap="gray")
ax[0].set_title(f"BEFORE arm ({cn} channel), gamma-stretched for viewing")
im = ax[1].imshow(zm, cmap="inferno", vmin=0, vmax=1)
ax[1].set_title(f"fraction of {cn} pixels clamped to EXACTLY 0 in the AFTER arm")
for x in ax: x.axis("off")
fig.colorbar(im, ax=ax[1], fraction=0.03)
fig.suptitle(f"{sub}: camera-linear, no tone curve, no colour matrix, both arms")
plt.tight_layout()
out = rf"C:\dev\strehl-out\V-BLEND\pics\{sub}-clamp-map.png"
plt.savefig(out, dpi=120)
print(f"\nwrote {out}")
