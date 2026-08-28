"""Arm B, correctly scoped. The previous arm used ISOTROPIC texture, which has no
dominant orientation and which the site picker (coherence>=0.55) REJECTS. On a
coherent edge the profile's perpendicular average is over a constant, so a
translation must be recovered as exactly its normal component."""
import numpy as np, vc_ca
from scipy.ndimage import gaussian_filter, shift as ndshift

N=600
def striped(theta):
    """Coherent bar pattern whose edge normal is theta."""
    Y,X=np.mgrid[0:N,0:N].astype(np.float32)
    t=X*np.cos(theta)+Y*np.sin(theta)
    a=gaussian_filter((np.sin(t/9.0)*0.5+0.5).astype(np.float32),1.0)
    return (a*40000+8000).astype(np.uint16)

print("theta  coherence  true n-component   measured    gain")
for deg in (0,20,45,70,90):
    th=np.deg2rad(deg); nx,ny=np.cos(th),np.sin(th)
    img0=striped(th)
    gy,gx=np.gradient(img0.astype(np.float32))
    Jxx=float(np.sum(gx*gx));Jyy=float(np.sum(gy*gy));Jxy=float(np.sum(gx*gy))
    coh=np.sqrt((Jxx-Jyy)**2+4*Jxy**2)/(Jxx+Jyy)
    dx=1.0
    R=ndshift(img0.astype(np.float32),(0.0,dx),order=3,mode="nearest")
    true=dx*nx
    out=[]
    for k in range(40):
        py=150+(k%8)*40; px=150+(k//8)*60
        pg=vc_ca.profile(img0,py,px,nx,ny); pr=vc_ca.profile(R.astype(np.uint16),py,px,nx,ny)
        if pg is None or pr is None: continue
        s=vc_ca.shift(pr,pg)
        if s is not None: out.append(s)
    if not out:
        print(" %3d    %.3f      %+.4f          (no sites)" % (deg,coh,true)); continue
    m=float(np.median(out))
    g = m/true if abs(true)>1e-9 else float("nan")
    print(" %3d    %.3f      %+.4f px       %+.4f px  %s" %
          (deg,coh,true,m,("%.3f"%g) if abs(true)>1e-9 else "n/a (true=0)"))
