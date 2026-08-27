"""Bound the resampling term, and show how sqrt(rc^2-rn^2) amplifies scatter."""
import math, sys
from pathlib import Path
import numpy as np, tifffile
REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(REPO / "experiments" / "M88b-merge-sharpness" / "src"))
sys.path.insert(0, str(REPO / "experiments" / "M88-optical-ceiling" / "src"))
import m88blib as M
ESF = Path(r"C:\dev\strehl-out\V-GATHER\esf"); W, CMIN = 96, 2000.0
def rd(n):
    for c in (ESF/f"{n}.tif", ESF/f"mem-{n}.tif"):
        if c.exists(): return M.read_merge_plane(c, "G")
def ax(ref,y,x):
    w=ref[y:y+W,x:x+W].astype(float)
    return "horizontal" if np.abs(np.diff(w.mean(1))).sum()>=np.abs(np.diff(w.mean(0))).sum() else "vertical"
def scan(ref,arm):
    out=[]
    for y in range(128,ref.shape[0]-W-128,W):
        for x in range(128,ref.shape[1]-W-128,W):
            d=M.paired_delta_registered(ref,arm,(y,x,W,W),ax(ref,y,x))
            if d.get("error") or d["contrast_off"]<CMIN: continue
            out.append((d["rise_off_um"]-d["rise_on_um"], d["rise_off_um"], d["rise_on_um"]))
    return np.array(out)
sub="109MSDCF"
pl,npl,fu = rd(f"{sub}--cr-plane"), rd(f"{sub}--nn-plane"), rd(f"{sub}--cr-fullres")
rng=np.random.default_rng(20240607)
for lab, arm, sign in (("KERNEL cr->nn (BUILD-SHARP's 14.97 term)", npl, +1),
                       ("FLIP   cr-plane->cr-fullres", fu, +1)):
    a=scan(pl,arm); d=a[:,0]
    bs=np.array([np.median(rng.choice(d,len(d),replace=True)) for _ in range(4000)])
    lo,hi=np.percentile(bs,[2.5,97.5])
    print(f"\n{lab}   n={len(d)}")
    print(f"  median rise difference (ref-arm) = {np.median(d):+.4f} um   "
          f"95% bootstrap CI [{lo:+.4f}, {hi:+.4f}]")
    mr=(np.median(a[:,1])+np.median(a[:,2]))/2
    def to_a(dd): 
        return math.copysign(math.sqrt(abs(2*mr*dd)), dd)
    print(f"  mean rise level ~{mr:.2f} um -> implied BUILD-SHARP 'a' = "
          f"{to_a(np.median(d)):+.3f} um, CI [{to_a(lo):+.3f}, {to_a(hi):+.3f}]")
print("\n=== sqrt amplification of the 'a' statistic at rise = 49.2 um ===")
print(f"  {'rise diff (um)':>15} {'-> a (um)':>12}")
for dd in (0.05,0.1,0.2,0.5,1.0,2.333):
    print(f"  {dd:15.3f} {math.sqrt(2*49.2296*dd):12.3f}")
print("\n=== budget closure if the resampling row is removed ===")
for a,lab in ((14.97,"BUILD-SHARP's published term"),(0.0,"V-GATHER: term not measurable"),
              (4.44,"a 0.2 um rise difference"),(7.0,"a 0.5 um rise difference")):
    pred=math.sqrt(30.44**2+a**2+7.61**2)
    print(f"  a={a:6.2f} ({lab:32s}) -> predicted {pred:6.2f} um vs measured 35.69 um "
          f"= {100*(35.69-pred)/35.69:+6.2f}%   unattributed "
          f"{math.sqrt(max(35.69**2-pred**2,0)):5.2f} um")
