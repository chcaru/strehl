"""Diagnose the frame->merge geometry. Do not trust the log's coverage number;
measure the scale, and show the correlation-vs-scale curve so a broad or
ambiguous peak cannot be mistaken for a fit."""
import sys, numpy as np
from pathlib import Path
from scipy import ndimage
import bestframe as B

RAW = Path(r"D:\personal\macro"); GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")

def curve(subj, fname, down=8, band=(2.0, 8.0), scales=np.arange(0.86, 1.061, 0.0025)):
    m = B.luma(B.read_merge(GAL / f"{subj}.tiff"))
    f = B.luma(B.decode(RAW / subj / fname))
    md = B.boxdown(m, down); fd = B.boxdown(f, down)
    A = B._prep(B.dog(md, *band)); FA = np.fft.rfft2(A); H, W = md.shape
    res = []
    for s in scales:
        Z = ndimage.zoom(fd, 1.0 / s, order=1)
        if Z.shape[0] < H or Z.shape[1] < W: continue
        oy, ox = (Z.shape[0] - H) // 2, (Z.shape[1] - W) // 2
        C = B._prep(B.dog(Z[oy:oy+H, ox:ox+W], *band))
        R = np.fft.irfft2(FA * np.conj(np.fft.rfft2(C)), A.shape)
        k = int(np.argmax(R)); uy, ux = np.unravel_index(k, R.shape)
        uy = uy - H if uy > H//2 else uy; ux = ux - W if ux > W//2 else ux
        res.append((s, float(R.flat[k]), down*s*(ux+ox), down*s*(uy+oy)))
    res = np.array(res)
    b = res[np.argmax(res[:, 1])]
    print(f"\n=== {subj} / {fname}  down={down} band={band}")
    print(f"  merge {m.shape}  frame {f.shape}")
    for r in res[::4]:
        bar = "#" * int(60 * r[1] / max(res[:,1].max(), 1e-9))
        print(f"   s={r[0]:.4f} peak={r[1]:.4f} t=({r[2]:+8.1f},{r[3]:+8.1f}) {bar}")
    print(f"  BEST s={b[0]:.4f} peak={b[1]:.4f} t=({b[2]:+.1f},{b[3]:+.1f})")
    sec = np.sort(res[:, 1])[-1] / np.sort(res[:, 1])[-2] if len(res) > 1 else 0
    print(f"  peak/2nd-peak = {sec:.4f}   half-width of max: "
          f"{np.sum(res[:,1] > 0.5*b[1])} of {len(res)} scale steps")
    return b

if __name__ == "__main__":
    curve("flowers-cpl", "DSC00212.ARW")     # reference frame 88 of 176
    curve("bee-1-cpl", "DSC00150.ARW")       # mid-stack
    curve("flowers-cpl", "DSC00124.ARW")     # first frame, the one that fit at s=0.99
