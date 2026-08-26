"""Tonal placement of faithful vs presentation renders.

NOT a quality measurement. Both sides are 8-bit JPEG past a tone curve and
the presentation side is additionally percentile-normalised per image, so
nothing here may be read as better or worse. It answers ONE question:
does the grade actually move the tones, and by how much.
"""
import os, glob
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

base = r"C:\dev\strehl-out\SHIP-V2-ICC"
fa = {os.path.basename(p).split("--")[0]: p for p in glob.glob(os.path.join(base, "_faithful", "*.jpg"))}
pr = {os.path.basename(p).split("--")[0]: p for p in glob.glob(os.path.join(base, "_presentation", "*.jpg"))}
keys = sorted(set(fa) & set(pr))
print(f"paired subjects: {len(keys)}  (faithful {len(fa)}, presentation {len(pr)})\n")

def stats(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    y = 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
    return (np.percentile(y,1), np.median(y), np.percentile(y,99), y.mean(),
            a.reshape(-1,3).std(axis=1).mean())

print(f"{'subject':<36} {'p1':>6} {'med':>6} {'p99':>6} | {'p1':>6} {'med':>6} {'p99':>6} | {'range x':>8}")
print("-"*100)
dm=[]; dr=[]
for k in keys:
    f = stats(fa[k]); p = stats(pr[k])
    rf = f[2]-f[0]; rp = p[2]-p[0]
    ratio = rp/rf if rf>0 else float('nan')
    dm.append(p[1]-f[1]); dr.append(ratio)
    print(f"{k:<36} {f[0]:6.1f} {f[1]:6.1f} {f[2]:6.1f} | {p[0]:6.1f} {p[1]:6.1f} {p[2]:6.1f} | {ratio:8.2f}")
print("-"*100)
print(f"median shift  : {np.median(dm):+.1f} of 255")
print(f"tonal range   : {np.median(dr):.2f}x  (min {np.min(dr):.2f}, max {np.max(dr):.2f})")
lo = [k for k,r in zip(keys,dr) if r < 1.02]
print(f"subjects where the grade did essentially nothing (<1.02x): {len(lo)} {lo if lo else ''}")
