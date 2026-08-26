"""Can strehl be compared against ZERENE STACKER PMax on IDENTICAL frames?

  zerene  D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif
          built from D:\edited\macro\test2\20260507-DSC00001..00063.tif
  strehl  C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff
          built from D:\personal\macro\113MSDCF\DSC00001..00063.ARW

Same 63 exposures, same session, one developed through Lightroom and one from
raw.  This is the same class of pipeline confound already declared for the
prior arm, and it is the best matched comparison available against a commercial
state-of-the-art stacker.

Step 1 only: headers, and a coarse scale+shift fit good enough to decide whether
a real comparison is possible at all.  If the phase-correlation peak is weak the
attempt is ABANDONED and reported as abandoned, not massaged.
"""
import numpy as np, tifffile, os
from scipy import ndimage
Z = r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"
S = r"C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff"
def box(a, k):
    h, w = a.shape
    return a[:h//k*k, :w//k*k].reshape(h//k, k, w//k, k).mean((1, 3))
for p in (Z, S):
    with tifffile.TiffFile(p) as tf:
        pg = tf.pages[0]
        sw = pg.tags.get("Software")
        print(f"{os.path.basename(p):<45} {pg.shape} {pg.dtype} photometric={pg.photometric} "
              f"software={sw.value if sw else None}")
def g8(p, k=8):
    with tifffile.TiffFile(p) as tf: a = tf.asarray()[:, :, 1].astype(np.float32)
    o = box(a, k); del a
    o = o - o.mean(); return o/(o.std()+1e-9)
gz, gs = g8(Z), g8(S)
print("zerene/8", gz.shape, "strehl/8", gs.shape)
best = None
for s in np.arange(0.96, 1.061, 0.004):
    zs = ndimage.zoom(gs, 1.0/s, order=1)
    H = min(gz.shape[0], zs.shape[0]); W = min(gz.shape[1], zs.shape[1])
    A = np.fft.rfft2(gz[:H, :W]); B = np.fft.rfft2(zs[:H, :W])
    R = A*np.conj(B); R /= np.abs(R)+1e-12
    c = np.fft.irfft2(R, s=(H, W)); i = np.unravel_index(np.argmax(c), c.shape); pk = c[i]
    dy = i[0]-(H if i[0] > H//2 else 0); dx = i[1]-(W if i[1] > W//2 else 0)
    if best is None or pk > best[0]: best = (pk, s, dy, dx)
    print(f"  scale {s:.3f} peak {pk:.4f} dy {dy:+5d} dx {dx:+5d}")
pk, s, dy, dx = best
print(f"\nBEST scale {s:.4f} shift dy {dy*8:+d} dx {dx*8:+d} px  peak {pk:.4f}")
print("VERDICT:", "usable" if pk > 0.08 else "TOO WEAK -- abandon")
np.save("zer_geom.npy", np.array([s, dy*8.0, dx*8.0, pk]))
