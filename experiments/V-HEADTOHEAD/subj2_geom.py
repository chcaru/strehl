"""SUBJECT 2 -- the marker-stroke board.  Coarse similarity fit between the
prior stack and strehl's 109MSDCF, by brute-force scale + shift on 8x box
downsamples.  We only need feature correspondence good enough to crop the SAME
occluding edge at 1:1 from each file; NOTHING IS RESAMPLED for the crops.

CAVEAT that must travel with every subject-2 result: these are DIFFERENT
CAPTURES.  prior = 63 frames dated 2026-05-07, Lightroom-developed with
crs:Contrast2012="+100"; strehl = 22 frames dated 2026-05-17 from raw.  Subject
2 therefore CANNOT support a sharpness or noise number.  It is admissible only
for the presence or absence of a structural artifact at an occluding edge.
"""
import numpy as np, tifffile, os
from scipy import ndimage

PRIOR = r"C:\dev\macro\out\stack_v3.tif"
STREHL = r"C:\dev\strehl-out\SHIP-V2\109MSDCF--SHIP-V2.tiff"

def box(a, k):
    h, w = a.shape
    return a[:h//k*k, :w//k*k].reshape(h//k, k, w//k, k).mean((1, 3))

def load_g(p, k=8):
    with tifffile.TiffFile(p) as tf:
        a = tf.asarray()[:, :, 1].astype(np.float32)
    g = box(a, k)
    del a
    return g

def norm(a):
    a = a - a.mean()
    return a / (a.std() + 1e-9)

if __name__ == "__main__":
    gp = norm(load_g(PRIOR)); gs = norm(load_g(STREHL))
    print("prior/8", gp.shape, " strehl/8", gs.shape)
    best = None
    for s in np.arange(0.90, 1.121, 0.005):
        zs = ndimage.zoom(gs, 1.0/s, order=1)
        H = min(gp.shape[0], zs.shape[0]); W = min(gp.shape[1], zs.shape[1])
        A = np.fft.rfft2(gp[:H, :W]); B = np.fft.rfft2(zs[:H, :W])
        R = A * np.conj(B); R /= np.abs(R) + 1e-12
        c = np.fft.irfft2(R, s=(H, W))
        i = np.unravel_index(np.argmax(c), c.shape)
        pk = c[i]
        dy = i[0] - (H if i[0] > H//2 else 0); dx = i[1] - (W if i[1] > W//2 else 0)
        if best is None or pk > best[0]:
            best = (pk, s, dy, dx)
        print(f"  scale {s:.3f}  peak {pk:.4f}  dy {dy:+4d} dx {dx:+4d}")
    pk, s, dy, dx = best
    print(f"\nBEST: strehl is {s:.4f}x the prior's scale, shift dy {dy*8:+d} dx {dx*8:+d} full-res px, peak {pk:.4f}")
    np.save("subj2_geom.npy", np.array([s, dy*8.0, dx*8.0, pk]))
