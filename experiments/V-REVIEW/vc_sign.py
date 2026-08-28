"""SIGN symmetry on the EXACT plant. A global translation gives an exactly known
per-site normal displacement (dx*nx+dy*ny) with no windowing ambiguity, unlike a
radial dilation whose displacement varies across the window. This is the arm that
tests the property the '1.82x magenta' counter lacked."""
import numpy as np, vc_ca
from scipy.ndimage import gaussian_filter, shift as ndshift

N=600
rng=np.random.default_rng(7)
b=gaussian_filter(rng.random((N,N)).astype(np.float32),3.0)
b=(b-b.min())/(b.max()-b.min()); img0=(b*40000+8000).astype(np.uint16)

def meas(dx,nx,ny):
    R=ndshift(img0.astype(np.float32),(0.0,dx),order=3,mode="nearest")
    out=[]
    for k in range(60):
        py=120+(k%10)*40; px=120+(k//10)*60
        pg=vc_ca.profile(img0,py,px,nx,ny); pr=vc_ca.profile(R.astype(np.uint16),py,px,nx,ny)
        if pg is None or pr is None: continue
        s=vc_ca.shift(pr,pg)
        if s is not None: out.append(s)
    return float(np.median(out)), len(out)

print("A. sign symmetry, normal along +x (true normal displacement = dx)")
res={}
for dx in (-2.0,-1.0,-0.5,-0.25,-0.1,0.1,0.25,0.5,1.0,2.0):
    m,n=meas(dx,1.0,0.0); res[dx]=m
    print("   true %+5.2f px -> %+8.4f px   gain %.3f  (n=%d)" % (dx,m,m/dx,n))
gp=np.mean([res[d]/d for d in res if d>0]); gn=np.mean([res[d]/d for d in res if d<0])
print("   mean gain POSITIVE %.4f   NEGATIVE %.4f   ASYMMETRY %.4f" % (gp,gn,gp/gn))

print("\nB. projection: same translation seen by a normal at 45deg (true = dx*cos45)")
dx=1.0
m,n=meas(dx,np.cos(np.pi/4),np.sin(np.pi/4))
print("   true %+.4f px -> %+.4f px   gain %.3f" % (dx*np.cos(np.pi/4),m,m/(dx*np.cos(np.pi/4))))

print("\nC. detection floor (smallest translation recovered within 20%%)")
floor=None
for dx in (0.50,0.25,0.10,0.05,0.02,0.01):
    m,_=meas(dx,1.0,0.0)
    ok=abs(m-dx)<=0.20*dx
    print("   %+.3f px -> %+.4f px  %s" % (dx,m,"ok" if ok else "below floor"))
    if ok: floor=dx
print("   FLOOR = %s px" % (("%.3f"%floor) if floor else "not established"))
