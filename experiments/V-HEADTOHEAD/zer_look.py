"""LOOK at subject 2 (frost) at 1:1 -- Zerene PMax vs strehl SHIP-V2, matched
frames.  Each arm reads its OWN integer box at the registered location; nothing
is resampled.  Per-panel display normalisation is affine on that panel's own
percentiles, so the two panels are tone-matched and only STRUCTURE is compared.
"""
import numpy as np, tifffile, os, json
from PIL import Image, ImageDraw
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD\subj2"; os.makedirs(OUT, exist_ok=True)
Z = r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"
S = r"C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff"
A, B, TX, TY = 1.0017487, 0.00032, 10.86, 5.75      # from zercmp.py similarity fit
def zmap(x, y): return (A*x - B*y + TX, B*x + A*y + TY)
def win(path, y, x, T):
    with tifffile.TiffFile(path) as tf:
        return tf.asarray()[y:y+T, x:x+T, :3].astype(np.float32)/65535.0
def disp(a):
    lo, hi = np.percentile(a, 1.0), np.percentile(a, 99.7)
    return np.clip((a-lo)/(hi-lo+1e-9), 0, 1)
def panel(name, zy, zx, T=420):
    az = win(Z, zy, zx, T)
    sx, sy = zmap(zx + T/2.0, zy + T/2.0)
    Ts = int(round(T*A)); y0, x0 = int(round(sy-Ts/2)), int(round(sx-Ts/2))
    as_ = win(S, y0, x0, Ts)
    tiles = [("ZERENE PMax  (63 developed frames)", disp(az)),
             ("STREHL SHIP-V2  (the same 63 raw frames)", disp(as_))]
    W = sum(t[1].shape[1] for t in tiles) + 12*(len(tiles)+1)
    H = max(t[1].shape[0] for t in tiles) + 40
    c = Image.new("RGB", (W, H), (24, 24, 24)); d = ImageDraw.Draw(c); xo = 12
    for lbl, t in tiles:
        c.paste(Image.fromarray((t*255).astype(np.uint8)), (xo, 30))
        d.text((xo+2, 10), lbl, fill=(235, 235, 235)); xo += t.shape[1]+12
    f = os.path.join(OUT, name+".png"); c.save(f); print("wrote", f)
if __name__ == "__main__":
    panel("frost_dendrite_1", 1200, 2600)
    panel("frost_dendrite_2", 2400, 3600)
    panel("frost_dark_flat",   700,  600)
