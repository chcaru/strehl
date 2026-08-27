import numpy as np, tifffile, warnings
from PIL import Image
from scipy.ndimage import uniform_filter
warnings.simplefilter("ignore")
P = r"C:\dev\strehl-out\V-HIGHLIGHT\u-bee-3-cpl.tiff"
N, OY, OX = 1024, 800, 1200
clean = tifffile.imread(P)[OY:OY+N, OX:OX+N, 1].astype(np.float64)
pil   = np.array(Image.open(P))[OY:OY+N, OX:OX+N, 1].astype(np.float64) * 256.0
hp = lambda a, r: a - uniform_filter(a, r)
ops = [("identity", lambda a: a), ("3x3 box mean", lambda a: uniform_filter(a,3)),
       ("high-pass r=201", lambda a: hp(a,201))]

def d_uq(a):    return len(np.unique(a)) <= 300
def d_mult(a):  u=np.unique(a); return len(u)>1 and np.all(np.mod(u,256)==0)
def d_gap(a):   u=np.unique(a); return len(u)>2 and np.median(np.diff(u)) > 8.0

dets = [("ORCH len(unique)<=300", d_uq), ("all values mult of 256", d_mult), ("median level gap > 8 DN", d_gap)]
print("Does the detector fire on the DAMAGED array?  (must be True to be useful)")
print("%-24s %-12s %-14s %-16s" % ("detector","identity","3x3 box mean","high-pass r=201"))
for nm, d in dets:
    row = []
    for _, f in ops:
        row.append("FIRES" if d(f(pil)) else "silent")
    print("%-24s %-12s %-14s %-16s" % (nm, row[0], row[1], row[2]))
print()
print("Negative control -- same detectors on the CLEAN array (must all be silent):")
for nm, d in dets:
    row = ["FALSE POS" if d(f(clean)) else "silent" for _, f in ops]
    print("%-24s %-12s %-14s %-16s" % (nm, row[0], row[1], row[2]))
