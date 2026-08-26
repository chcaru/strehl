"""Is the clamped-away content UNDERSHOOT at edges (ORCH's hypothesis)?
Ringing predicts: D concentrated in a narrow band adjacent to strong edges,
falling off with distance. Diffuse shadow bias predicts: no distance structure.
Edges located on the CLAMPED arm (a fixed reference for both)."""
import sys
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter, distance_transform_edt
def G(p):
    im=tifffile.imread(p); assert im.dtype==np.uint16; return im[:,:,1].astype(np.float32)
cp, up = sys.argv[1], sys.argv[2]
gc, gu = G(cp), G(up)
d = gu - gc                       # negative => clamp lifted it
sm = gaussian_filter(gc, 3.0, mode="reflect")
gy, gx = np.gradient(sm)
mag = np.sqrt(gy*gy+gx*gx)
strong = mag > np.percentile(mag[::3,::3], 99.0)     # top 1% edges
dist = distance_transform_edt(~strong)
print("distance from a top-1%% edge -> mean signed D (DN), and |D|>=8 rate")
print("%10s %14s %14s %12s" % ("dist px","mean D","rms D","frac|D|>=8"))
for lo,hi in [(0,2),(2,4),(4,8),(8,16),(16,32),(32,64),(64,128),(128,10**6)]:
    m = (dist>=lo)&(dist<hi)
    n=int(m.sum())
    if n<1000: continue
    dm=d[m]
    print("%10s %14.1f %14.1f %11.1f%%" % ("%d-%d"%(lo,hi), dm.mean(),
          float(np.sqrt((dm.astype(np.float64)**2).mean())), 100.0*(np.abs(dm)>=8).mean()))
print("\nsame, but by LUMINANCE decile of the clamped arm (shadow test)")
qs=np.percentile(gc[::3,::3], np.arange(0,101,10))
print("%10s %14s %14s %12s" % ("lum decile","mean D","rms D","frac|D|>=8"))
for i in range(10):
    m=(gc>=qs[i])&(gc<qs[i+1]) if i<9 else (gc>=qs[i])
    n=int(m.sum())
    if n<1000: continue
    dm=d[m]
    print("%10d %14.1f %14.1f %11.1f%%" % (i+1, dm.mean(),
          float(np.sqrt((dm.astype(np.float64)**2).mean())), 100.0*(np.abs(dm)>=8).mean()))
