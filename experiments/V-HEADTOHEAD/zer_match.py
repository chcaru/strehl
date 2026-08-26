"""Settle subject 2 with a TONE MATCH THAT IS ACTUALLY A TONE MATCH.

Two errors are being corrected here, both mine.
  1. zer_look.py normalised each panel by ITS OWN 1/99.7 percentiles and called
     the result tone-matched.  It is not: it equalises two endpoints, not the
     curve between them.  Zerene's median is 0.0463 and strehl's is 0.2142, so
     that stretch pushed Zerene's background to black and strehl's to grey and
     manufactured the appearance that strehl resolved more.
  2. zer_crush.py hypothesised black clipping.  REFUTED: the fraction of green
     pixels at or below 0.01 is 1e-5 (zerene) and 0 (strehl).  Nothing is
     crushed.

The correct instrument is HISTOGRAM MATCHING: a monotone pointwise remap of one
arm onto the other's distribution.  Monotone and pointwise means it cannot add
or destroy spatial detail -- it can only equalise the transfer curve, which is
exactly the confound.  Zerene's transfer function is unknown and unknowable from
the file, so this is the only tone control available that does not require it.

Fooling direction: histogram matching equalises the GLOBAL distribution, not the
local one, so a residual local-contrast difference can survive.  Stated.
"""
import numpy as np, tifffile, json, os, spec, shapecmp
from arms import Arm
from scipy import ndimage
from PIL import Image, ImageDraw
Z = r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"
S = r"C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff"
A, B, TX, TY = 1.0017487, 0.00032, 10.86, 5.75
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD\subj2"
def load(p):
    a = tifffile.memmap(p, mode="r")
    g = np.empty(a.shape[:2], np.float32); clip = np.zeros(a.shape[:2], bool)
    for y0 in range(0, a.shape[0], 256):
        y1 = min(y0+256, a.shape[0]); blk = np.asarray(a[y0:y1], np.uint16)
        g[y0:y1] = blk[:, :, 1].astype(np.float32)/65535.0
        clip[y0:y1] = blk.max(axis=2) >= 65535
    del a; return g, clip
def match_lut(src, ref, nb=65536):
    hs, _ = np.histogram(np.clip(src, 0, 1), nb, (0, 1))
    hr, _ = np.histogram(np.clip(ref, 0, 1), nb, (0, 1))
    cs = np.cumsum(hs).astype(np.float64); cs /= cs[-1]
    cr = np.cumsum(hr).astype(np.float64); cr /= cr[-1]
    lut = np.interp(cs, cr, np.linspace(0, 1, nb)).astype(np.float32)
    return lut
def apply_lut(g, lut):
    idx = np.clip((g*(len(lut)-1)).astype(np.int32), 0, len(lut)-1)
    return lut[idx]
def mapper(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    return (A*x - B*y + TX, B*x + A*y + TY)
if __name__ == "__main__":
    gz, cz = load(Z); gs, cs = load(S)
    lut = match_lut(gs, gz)
    print("monotone LUT?", bool(np.all(np.diff(lut) >= -1e-9)),
          f"  maps strehl median {np.median(gs):.4f} -> {apply_lut(np.array([[np.median(gs)]],np.float32),lut)[0,0]:.4f}"
          f"  (zerene median {np.median(gz):.4f})")
    gsm = apply_lut(gs, lut)
    print(f"after match: strehl median {np.median(gsm):.5f}  p01 {np.percentile(gsm,1):.5f}  p99 {np.percentile(gsm,99):.5f}")
    Az = Arm("zerene", gz, lambda x, y: (x, y), 1.0, cz)
    Asm = Arm("strehl-matched", gsm, mapper, A, cs)
    T = 256; Ts = int(round(T*A)); rois = []
    for y in range(300, gz.shape[0]-T-300, T//2):
        for x in range(300, gz.shape[1]-T-300, T//2):
            tz = gz[y:y+T, x:x+T]
            if cz[y:y+T, x:x+T].any(): continue
            if (tz - ndimage.uniform_filter(tz, 9)).std() < 0.012: continue
            sx, sy = mapper(x+T/2.0, y+T/2.0); y0, x0 = int(round(sy-Ts/2)), int(round(sx-Ts/2))
            if y0 < 0 or x0 < 0 or y0+Ts > gs.shape[0] or x0+Ts > gs.shape[1]: continue
            if cs[y0:y0+Ts, x0:x0+Ts].any(): continue
            rois.append((y, x))
    print(f"ROIs: {len(rois)}")
    out = {}
    out["null"] = shapecmp.shape_ratio(Az, Arm("clone", gz, lambda x, y: (x, y), 1.0, cz),
                                       rois, "NULL CONTROL", "zerene", "clone", T)
    bl = ndimage.gaussian_filter(gz, 0.5)
    out["pos"] = shapecmp.shape_ratio(Az, Arm("blur", bl, lambda x, y: (x, y), 1.0, cz),
                                      rois, "POSITIVE CONTROL sigma=0.5 px", "zerene", "blur", T); del bl
    out["real"] = shapecmp.shape_ratio(Az, Asm, rois,
        "REAL, HISTOGRAM-MATCHED: Zerene PMax vs strehl SHIP-V2 (63 identical frames)",
        "zerene", "strehl", T)
    json.dump(out, open("zer_shape_matched.json", "w"), indent=1)
    # LOOK, with the SAME monotone match applied -- no per-panel stretch at all.
    def panel(name, zy, zx, TT=420):
        with tifffile.TiffFile(Z) as tf: az = tf.asarray()[zy:zy+TT, zx:zx+TT, 1].astype(np.float32)/65535.
        sx, sy = mapper(zx+TT/2.0, zy+TT/2.0); Tss = int(round(TT*A))
        y0, x0 = int(round(sy-Tss/2)), int(round(sx-Tss/2))
        with tifffile.TiffFile(S) as tf: a_s = tf.asarray()[y0:y0+Tss, x0:x0+Tss, 1].astype(np.float32)/65535.
        a_s = apply_lut(a_s, lut)
        lo, hi = np.percentile(az, 0.5), np.percentile(az, 99.5)   # ONE stretch, from Zerene, used for BOTH
        f = lambda a: (np.clip((a-lo)/(hi-lo+1e-9), 0, 1)*255).astype(np.uint8)
        tiles = [("ZERENE PMax", f(az)), ("STREHL SHIP-V2, histogram-matched to Zerene", f(a_s))]
        W = sum(t[1].shape[1] for t in tiles)+12*3; H = max(t[1].shape[0] for t in tiles)+40
        c = Image.new("RGB", (W, H), (24,24,24)); d = ImageDraw.Draw(c); xo = 12
        for lbl, t in tiles:
            c.paste(Image.fromarray(np.dstack([t]*3)), (xo, 30)); d.text((xo+2, 10), lbl, fill=(235,)*3); xo += t.shape[1]+12
        p = os.path.join(OUT, name+".png"); c.save(p); print("wrote", p)
    panel("frost_matched_1", 2400, 3600); panel("frost_matched_2", 1200, 2600)
