"""LOOK at the flat/defocused ROI with the high-pass residual stretched hard.
Grain looks like grain; texture looks like texture.  Both arms are stretched by
THEIR OWN sigma so neither is flattered, and a second panel stretches both by
the SAME factor so the amplitude difference is visible too."""
import numpy as np, os, sys, arms
from PIL import Image, ImageDraw
from scipy import ndimage
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD\crops"; os.makedirs(OUT, exist_ok=True)
P = arms.prior_arm(); S = arms.strehl_arm()

def hp(a, r=4):
    return a / ndimage.uniform_filter(a, 2*r+1) - 1.0

def panel(name, y, x, T):
    va = P.g[y:y+T, x:x+T].astype(np.float64)
    cx, cy = S.px(x+T/2.0, y+T/2.0); Ts = int(round(T*S.scale))
    y0 = int(round(cy-Ts/2)); x0 = int(round(cx-Ts/2))
    vb = S.g[y0:y0+Ts, x0:x0+Ts].astype(np.float64)
    ha, hb = hp(va), hp(vb)
    sa, sb = ha.std(), hb.std()
    common = max(sa, sb)
    def img(h, s):
        return (np.clip(h/(4*s) + 0.5, 0, 1)*255).astype(np.uint8)
    tiles = [img(ha, sa), img(hb, sb), img(ha, common), img(hb, common)]
    labs = [f"PRIOR own-sigma ({sa*100:.3f}% rms)", f"STREHL own-sigma ({sb*100:.3f}% rms)",
            f"PRIOR common-sigma", f"STREHL common-sigma"]
    H = max(t.shape[0] for t in tiles); W = sum(t.shape[1] for t in tiles) + 3*10
    c = np.full((H+22, W, 3), 30, np.uint8)
    xo = 0
    for t, l in zip(tiles, labs):
        c[22:22+t.shape[0], xo:xo+t.shape[1]] = t[:, :, None]
        xo += t.shape[1] + 10
    im = Image.fromarray(c); d = ImageDraw.Draw(im); xo = 0
    for t, l in zip(tiles, labs):
        d.text((xo+3, 6), l, fill=(255,255,120)); xo += t.shape[1]+10
    im.save(os.path.join(OUT, name+".png"))
    print(name, f"prior hp rms {sa*100:.4f}%  strehl hp rms {sb*100:.4f}%  ratio {sb/sa:.4f}")

panel("hp_flat", 968, 584, 320)
panel("hp_detail", 3272, 4616, 320)
panel("hp_paper_infocus", 4150, 2600, 320)
