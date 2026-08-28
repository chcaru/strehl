"""Simplest possible ground truth: translate R by a known sub-pixel amount along
a known direction. No radial geometry, no r-division. If the estimator reads
0.85x here, the gain is intrinsic to the shift estimator itself."""
import numpy as np, vc_ca
from scipy.ndimage import gaussian_filter, shift as ndshift

N=600
rng=np.random.default_rng(7)
base=gaussian_filter(rng.random((N,N)).astype(np.float32),3.0)
base=(base-base.min())/(base.max()-base.min())
img0=(base*40000+8000).astype(np.uint16)

print(" true dx    measured (median over 60 windows)   gain")
for dx in (0.10,0.25,0.50,1.00,2.00):
    R=ndshift(img0.astype(np.float32),(0.0,dx),order=3,mode="nearest")
    meas=[]
    for k in range(60):
        py=120+ (k%10)*40; px=120+(k//10)*60
        pg=vc_ca.profile(img0.astype(np.uint16),py,px,1.0,0.0)
        pr=vc_ca.profile(R.astype(np.uint16),py,px,1.0,0.0)
        if pg is None or pr is None: continue
        s=vc_ca.shift(pr,pg)
        if s is not None: meas.append(s)
    m=float(np.median(meas))
    print("  %+.2f px   %+.4f px  (n=%d)                %.3f" % (dx,m,len(meas),m/dx))
