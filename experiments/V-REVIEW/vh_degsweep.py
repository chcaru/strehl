"""Is there ANY trend stiffness that separates a real rim from a bare penumbra?

The residual statistic needs a trend model. Too stiff and the subject's own
penumbra curvature leaks into the residual (measured: 1011 DN on an unplanted
bee-1-cpl). Too loose and the trend absorbs the rim it is meant to expose.

This sweeps the stiffness and measures BOTH failure modes on the same axis:
  - the largest residual on FIVE UNPLANTED clean hosts  (false-positive floor)
  - the residual recovered from a planted rim            (sensitivity)
A degree is usable only if the second clears the first by a margin. If no
degree does, a radial-profile detector cannot do this job and I will say so
rather than tune until the table looks agreeable.
"""
import os, sys
import numpy as np, tifffile
from scipy.ndimage import distance_transform_edt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "ORCH-drift-check"))
import halo_profile as H, halo2

FAITH = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
CLEAN = ["bee-1-cpl","bee-2-cpl","bee-3-cpl","flower-bud-alone-cpl","coffee-bean"]
DEGS = [2,3,4,5,6]


def bands_of(y):
    g, why = halo2.geom(y)
    if g is None: return None, None
    ys,d,own,ab,fl = g["ys"],g["d"],g["own"],g["ab"],g["farlevel"]
    mids, vals = [], []
    for lo,hi in halo2.BANDS:
        m = own & (d>=lo) & (d<hi)
        if int(m.sum()) <= H.MIN_BANDPX: continue
        nb = sum(1 for b in range(halo2.NAZ) if int((m&(ab==b)).sum())>=halo2.MIN_AZ_PX)
        if nb/float(halo2.NAZ) < halo2.MIN_COV: continue
        mids.append(0.5*(lo+hi)); vals.append(float(np.median(ys[m]))-fl)
    return np.array(mids,float), np.array(vals,float)


def resid_amp(mid, val, deg):
    if mid is None or len(val) < deg+3: return None
    x = np.log(mid)
    co = np.polyfit(x,val,deg); r0 = val-np.polyval(co,x)
    keep = np.argsort(r0)[:-2]
    co = np.polyfit(x[keep],val[keep],deg)
    return float(np.max(val-np.polyval(co,x)))


print("Loading hosts...")
host = {}
for s in CLEAN:
    y = H.luma(tifffile.imread(os.path.join(FAITH,s+".tiff"))).astype(np.float32)
    host[s] = y
y = host["bee-1-cpl"]
ys4 = y[::4,::4]; t,subj = H.segment(ys4)
big = np.repeat(np.repeat(subj,4,0),4,1)[:y.shape[0],:y.shape[1]]
d = distance_transform_edt(~big).astype(np.float32)

print("\n%-5s | %s | %s | %s" % ("deg","worst UNPLANTED clean host (DN)",
                                "narrow 800/1600/3200 DN","broad 800/1600/3200 DN"))
print("-"*104)
rows=[]
for deg in DEGS:
    fp = []
    for s in CLEAN:
        m,v = bands_of(host[s]); a = resid_amp(m,v,deg)
        if a is not None: fp.append((a,s))
    worst,ws = max(fp) if fp else (float("nan"),"-")
    nar,bro = [],[]
    for A in (800,1600,3200):
        r = A*np.exp(-((d-30.0)**2)/(2*14.0**2)); r[big]=0
        m,v = bands_of(np.clip(y+r,0,65535)); nar.append(resid_amp(m,v,deg))
        r = A*np.exp(-((d-80.0)**2)/(2*40.0**2)); r[big]=0
        m,v = bands_of(np.clip(y+r,0,65535)); bro.append(resid_amp(m,v,deg))
    rows.append((deg,worst,ws,nar,bro))
    print("%-5d | %8.0f  (%-20s) | %6.0f %6.0f %6.0f | %6.0f %6.0f %6.0f" % (
        deg,worst,ws,nar[0],nar[1],nar[2],bro[0],bro[1],bro[2]))

print("\nSEPARATION: planted residual divided by the worst unplanted clean host.")
print("A usable degree needs the 3200 DN rim comfortably above 1.0 on BOTH shapes.")
print("%-5s %12s %12s" % ("deg","narrow 3200","broad 3200"))
for deg,worst,ws,nar,bro in rows:
    print("%-5d %11.2fx %11.2fx" % (deg, nar[2]/worst, bro[2]/worst))
