"""SUBJECT 2 -- occluding-edge LOOK at 1:1.  Registration failed (subj2_geom.py
peak 0.0277, no maximum), so nothing here is registered or differenced: each
crop is located INDEPENDENTLY on the same physical feature and shown at native
resolution.  A halo is a local structure; it does not need registration to be
seen, only the same edge at 1:1.

ARMS
  prior  C:\dev\macro\out\stack_test2_rec2020.tif   63 frames 2026-05-07, LR
                                                    develop with Contrast +100
  zerene D:\edited\macro\test2\...ZS PMax.tif       THE SAME 63 developed frames
  strehl C:\dev\strehl-out\SHIP-V2\109MSDCF...      22 frames 2026-05-17, raw

The prior/zerene pair is frame-matched to each other.  strehl is a DIFFERENT
CAPTURE of the same scene and is admissible here only for artifact presence.
"""
import numpy as np, tifffile, os
from PIL import Image
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD\subj2"
os.makedirs(OUT, exist_ok=True)
ARMS = [
 ("PRIOR focus-stack",  r"C:\dev\macro\out\stack_test2_rec2020.tif"),
 ("ZERENE PMax",        r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
 ("STREHL SHIP-V2",     r"C:\dev\strehl-out\SHIP-V2\109MSDCF--SHIP-V2.tiff"),
]
def read_win(path, cy, cx, T):
    with tifffile.TiffFile(path) as tf:
        pg = tf.pages[0]
        H, W = pg.shape[0], pg.shape[1]
        y = int(np.clip(cy*H - T//2, 0, H-T)); x = int(np.clip(cx*W - T//2, 0, W-T))
        a = tf.asarray()[y:y+T, x:x+T, :3].astype(np.float32)
    if a.max() > 1.5: a /= 65535.0
    return a, (y, x, H, W)
def disp(a, is_linear):
    lo = np.percentile(a, 0.5); hi = np.percentile(a, 99.5)
    v = np.clip((a-lo)/(hi-lo+1e-9), 0, 1)
    return (v**(1/2.2) if is_linear else v)
def panel(name, cy, cx, T=440):
    tiles = []
    for (lbl, p) in ARMS:
        a, meta = read_win(p, cy, cx, T)
        lin = p.endswith(".tif") and "SHIP" not in p
        v = disp(a, lin)
        t = (v*255).astype(np.uint8)
        tiles.append((lbl, t, meta))
    Wtot = T*len(tiles) + 12*(len(tiles)+1)
    canvas = Image.new("RGB", (Wtot, T+40), (24, 24, 24))
    from PIL import ImageDraw
    d = ImageDraw.Draw(canvas)
    for i, (lbl, t, meta) in enumerate(tiles):
        canvas.paste(Image.fromarray(t), (12 + i*(T+12), 30))
        d.text((14 + i*(T+12), 10), f"{lbl}  y{meta[0]} x{meta[1]}", fill=(235, 235, 235))
    f = os.path.join(OUT, f"{name}.png"); canvas.save(f); print("wrote", f)
if __name__ == "__main__":
    panel("occl_teal_over_red_lowerleft", 0.735, 0.355)
    panel("occl_teal_over_black_bar",     0.455, 0.335)
    panel("occl_red_over_blue_upper",     0.230, 0.560)
    panel("occl_red_over_black_right",    0.455, 0.600)
