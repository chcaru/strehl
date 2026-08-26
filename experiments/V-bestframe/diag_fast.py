"""Can raw Bayer green (no demosaic) drive registration? It is ~5x cheaper than a
full postprocess, which makes a cheap pre-pass fit of s(k), t(k) affordable."""
import time, numpy as np, rawpy
from pathlib import Path
from scipy import ndimage
import bestframe as B

RAW = Path(r"D:\personal\macro"); GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")

def raw_green_half(p):
    with rawpy.imread(str(p)) as r:
        v = r.raw_image_visible
        pat = r.raw_pattern
        gy, gx = [(i // 2, i % 2) for i in range(4) if pat[i // 2, i % 2] == 1][0]
        g = v[gy::2, gx::2].astype(np.float32)
        blk = float(np.mean(r.black_level_per_channel))
    return np.maximum(g - blk, 0.0)

m = B.luma(B.read_merge(GAL / "flowers-cpl.tiff"))
md = B.boxdown(m, 8)
scales = np.arange(0.86, 1.0401, 0.0025)

def fit(md, fd, band=(4.0, 16.0)):
    A = B._prep(B.dog(md, *band)); FA = np.fft.rfft2(A); H, W = md.shape
    out = []
    for s in scales:
        Z = ndimage.zoom(fd, 1.0 / s, order=1)
        if Z.shape[0] < H or Z.shape[1] < W: continue
        oy, ox = (Z.shape[0]-H)//2, (Z.shape[1]-W)//2
        C = B._prep(B.dog(Z[oy:oy+H, ox:ox+W], *band))
        R = np.fft.irfft2(FA*np.conj(np.fft.rfft2(C)), A.shape)
        k = int(np.argmax(R)); uy, ux = np.unravel_index(k, R.shape)
        uy = uy-H if uy > H//2 else uy; ux = ux-W if ux > W//2 else ux
        out.append((s, float(R.flat[k]), 8*s*(ux+ox), 8*s*(uy+oy)))
    o = np.array(out); return o[np.argmax(o[:,1])]

fs = sorted((RAW / "flowers-cpl").glob("*.ARW"))
print("k     file            s_raw   peak   tx      ty     | tone  t_decode")
for k in (0, 22, 44, 88, 132, 175):
    t0 = time.time(); g = raw_green_half(fs[k]); t1 = time.time()
    for tone, lab in ((lambda a: a, "lin "), (np.sqrt, "sqrt"), (np.log1p, "log ")):
        fd = B.boxdown(tone(g), 4)
        b = fit(md, fd)
        print(f"{k:4d} {fs[k].name}  {b[0]:.4f} {b[1]:.4f} {b[2]:+8.1f} {b[3]:+7.1f} | {lab} "
              f"{t1-t0:.2f}s")
