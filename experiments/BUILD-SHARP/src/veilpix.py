import sys, numpy as np, tifffile
from PIL import Image
R = r"C:\dev\strehl-out\BUILD-SHARP\veil"
OUT = r"C:\dev\strehl-out\BUILD-SHARP\pictures\veil"
import os; os.makedirs(OUT, exist_ok=True)

def load(s, arm):
    return tifffile.imread(rf"{R}\{s}\{arm}\linear-srgb.tif").astype(np.float32)

def tone(a, p=99.5):
    hi = np.percentile(a, p)
    x = np.clip(a/hi, 0, 1) ** (1/2.2)
    return (x*255).astype(np.uint8)

for s in ("coffee-bean", "flower-bud-alone-cpl", "couch-fibers-cpl"):
    A, B = load(s, "A"), load(s, "B")
    hi = np.percentile(A, 99.5)
    # full-frame downscale side by side, plus signed difference
    h, w = A.shape[:2]
    k = max(1, w // 1400)
    a = tone(A[::k, ::k], 99.5); b = tone(B[::k, ::k], 99.5)
    # use the SAME normaliser for both so a level shift is visible, not tonemapped away
    def tone_fixed(x): return (np.clip(x/hi,0,1)**(1/2.2)*255).astype(np.uint8)
    a = tone_fixed(A[::k, ::k]); b = tone_fixed(B[::k, ::k])
    d = (B - A)[::k, ::k].mean(axis=2)
    dv = np.clip(d/2000.0, -1, 1)
    dm = np.zeros(dv.shape + (3,), np.uint8)
    dm[..., 0] = (np.clip(dv, 0, 1)*255)      # red  = B brighter
    dm[..., 2] = (np.clip(-dv, 0, 1)*255)     # blue = B darker
    gap = np.full((a.shape[0], 12, 3), 255, np.uint8)
    im = np.concatenate([a, gap, b, gap, dm], axis=1)
    Image.fromarray(im).save(rf"{OUT}\AB-{s}.png")
    print(s, "->", im.shape, " |dB-A| mean", float(np.abs(B-A).mean()),
          " frac |d|>500DN", float((np.abs(B-A).mean(axis=2) > 500).mean()))
