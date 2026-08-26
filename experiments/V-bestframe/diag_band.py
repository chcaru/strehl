"""Which correlation band survives heavy defocus? A registration that fails on
the blurred frames would silently mis-map exactly the tiles under test."""
import numpy as np
from pathlib import Path
from scipy import ndimage
import bestframe as B

RAW = Path(r"D:\personal\macro"); GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
m = B.luma(B.read_merge(GAL / "flowers-cpl.tiff"))

def best(md, fd, band, scales):
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
        out.append((s, float(R.flat[k]), ux, uy))
    o = np.array(out); b = o[np.argmax(o[:,1])]
    contrast = b[1] / np.median(o[:,1])
    return b, contrast

scales = np.arange(0.86, 1.0401, 0.0025)
for fname in ("DSC00124.ARW", "DSC00212.ARW", "DSC00299.ARW"):
    f = B.luma(B.decode(RAW / "flowers-cpl" / fname))
    print(f"\n--- {fname}")
    for down, band in ((8, (2, 8)), (8, (4, 16)), (16, (1, 4)), (16, (2, 8)), (32, (1, 4))):
        md, fd = B.boxdown(m, down), B.boxdown(f, down)
        b, c = best(md, fd, band, scales)
        print(f"   down={down:2d} band={str(band):8s} -> s={b[0]:.4f} peak={b[1]:.4f} "
              f"peak/median={c:5.2f}  physical scale {band[0]*down}-{band[1]*down} px")
