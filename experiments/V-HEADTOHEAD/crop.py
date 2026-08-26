"""1:1 side-by-side crops for LOOKING.  Prior is shown sRGB-encoded from linear;
strehl is shown as shipped.  Both are then matched only by a per-crop affine on
display luma so the eye compares STRUCTURE, not grade.  No resampling of either
arm: the strehl crop is simply the correspondingly larger integer box, and the
pair is laid out side by side at their own native pixel sizes."""
import numpy as np, os, sys, h2h
from PIL import Image
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD\crops"
os.makedirs(OUT, exist_ok=True)
P, S = h2h.open_arms()

def srgb(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, 12.92*v, 1.055*np.power(v, 1/2.4) - 0.055)

def crop(name, y, x, T, match=True):
    p = np.asarray(P[y:y+T, x:x+T, :], np.float64)
    cxs, cys = h2h.prior_to_strehl(x + T/2.0, y + T/2.0)
    Ts = int(round(T * h2h.SCALE))
    sy = int(round(cys - Ts/2.0)); sx = int(round(cxs - Ts/2.0))
    s = np.asarray(S[sy:sy+Ts, sx:sx+Ts, :], np.float64) / 65535.0
    pd = srgb(p)
    sd = s.copy()
    if match:
        # affine match on display luma so tone/grade does not drive the eye
        lp = pd.mean(axis=2); ls = sd.mean(axis=2)
        a = lp.std() / (ls.std() + 1e-9); b = lp.mean() - a * ls.mean()
        sd = np.clip(sd * a + b, 0, 1)
    h = max(pd.shape[0], sd.shape[0])
    canvas = np.zeros((h + 22, pd.shape[1] + sd.shape[1] + 12, 3), np.uint8)
    canvas[:, :] = 40
    canvas[22:22+pd.shape[0], :pd.shape[1]] = (pd*255).astype(np.uint8)
    canvas[22:22+sd.shape[0], pd.shape[1]+12:pd.shape[1]+12+sd.shape[1]] = (sd*255).astype(np.uint8)
    im = Image.fromarray(canvas)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.text((4, 5), f"PRIOR (focus-stack fork)  {T}x{T}", fill=(255,255,255))
    d.text((pd.shape[1]+16, 5), f"STREHL  {Ts}x{Ts} (same scene area, 3.5% more px)", fill=(255,255,255))
    im.save(os.path.join(OUT, name + ".png"))
    print("wrote", name, "prior", (y,x,T), "strehl", (sy,sx,Ts))

if __name__ == "__main__":
    for a in sys.argv[1:]:
        n, y, x, T = a.split(",")
        crop(n, int(y), int(x), int(T))
