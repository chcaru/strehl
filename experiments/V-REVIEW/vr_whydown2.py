"""Decompose: clean band, plant-alone band, sum without clipping, sum with clipping.

Adding a zero-mean mid-scale field LOWERED the band reading.  One of these is
responsible and the ladder cannot be reported until it is named.
"""
import os, sys
import numpy as np, cv2, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V
import orch_blotch as OB

FY, FX, W = 2254, 5926, OB.WIN
print("orch_blotch radii: LO_R=%s HI_R=%s NOISE_R=%s WIN=%s"
      % (OB.LO_R, OB.HI_R, OB.NOISE_R, OB.WIN))


def box(a, r):
    return cv2.blur(a, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)


img = tifffile.imread(V.master_path("112MSDCF"))
h, w = img.shape[:2]
rng = np.random.default_rng(7)
n = rng.standard_normal((h, w), dtype=np.float32)
m = box(n, 100) - box(box(n, 100), 400)
m *= (800.0 / m.std())

lum_clean = V.lum_of(img[:, :, :3].astype(np.float32))
noclip = img.astype(np.float32) + m[:, :, None]
lum_noclip = V.lum_of(noclip)
clipped = np.clip(noclip, 0, 65535)
lum_clip = V.lum_of(clipped)

blk = lum_clean[FY:FY + W, FX:FX + W]
print("window pixels below   800 DN: %.3f%%" % (100 * (blk < 800).mean()))
print("window pixels above 64735 DN: %.3f%%" % (100 * (blk > 65535 - 800).mean()))
print("window luminance p1 %.0f  p50 %.0f  p99 %.0f" % tuple(np.percentile(blk, [1, 50, 99])))
nclip_lo = (noclip < 0).mean() * 100
nclip_hi = (noclip > 65535).mean() * 100
print("WHOLE IMAGE clipped by the plant: low %.3f%%  high %.3f%%" % (nclip_lo, nclip_hi))
sub = noclip[FY:FY + W, FX:FX + W]
print("WINDOW      clipped by the plant: low %.3f%%  high %.3f%%"
      % ((sub < 0).mean() * 100, (sub > 65535).mean() * 100))

for tag, L in (("clean", lum_clean), ("clean+plant NO clip", lum_noclip),
               ("clean+plant clipped", lum_clip)):
    r, bd, nd, md = OB.blotch_ratio(L[FY:FY + W, FX:FX + W])
    print("%-22s blotch %.5f  band %8.2f  noise %8.2f  mean %9.2f" % (tag, r, bd, nd, md))

mw = m[FY:FY + W, FX:FX + W].astype(np.float32)
r, bd, nd, md = OB.blotch_ratio(mw + 10000.0)
print("%-22s band %8.2f   (plant alone, sd in window %.1f DN)" % ("PLANT ALONE", bd, mw.std()))
