"""Is the sign asymmetry in the ESTIMATOR or in the real edges?
Synthetic concentric rings: edge normals are exactly radial (align=1.0) and the
edge profile is symmetric by construction. If the estimator is linear and
symmetric here, the asymmetry seen on dry-erase is a property of real edge
structure (ringing/contrast asymmetry), not of the instrument."""
import numpy as np, vc_ca
from scipy.ndimage import gaussian_filter, map_coordinates

N = 2000; C = N/2.0
Y, X = np.mgrid[0:N, 0:N].astype(np.float32)
R = np.hypot(X-C, Y-C)
ring = (np.sin(R/14.0)*0.5+0.5)
img0 = gaussian_filter(ring, 1.1)
img0 = (img0*40000+8000).astype(np.uint16)
img = np.dstack([img0, img0, img0])

def plant(im, ch, eps):
    out = im.copy()
    ys = C + (Y-C)/(1.0+eps); xs = C + (X-C)/(1.0+eps)
    out[:,:,ch] = np.clip(map_coordinates(im[:,:,ch].astype(np.float32),
                    [ys,xs], order=3, mode="nearest"),0,65535).astype(np.uint16)
    return out

S = vc_ca.sites(img[:,:,1], (C,C))
print("synthetic qualifying sites: %d" % len(S))
S = S[::max(1,len(S)//200)][:200]
al = np.array([s[6] for s in S])
print("align |n.rhat|: min %.3f  median %.3f  max %.3f" % (al.min(), np.median(al), al.max()))

def per_site(im):
    out={}
    for i,(py,px,nx,ny,r,m,a) in enumerate(S):
        pg=vc_ca.profile(im[:,:,1],py,px,nx,ny); pr=vc_ca.profile(im[:,:,0],py,px,nx,ny)
        if pg is None or pr is None: continue
        s=vc_ca.shift(pr,pg)
        if s is None: continue
        out[i]=(s/a)/r*1e6
    return out

base=per_site(img)
print("\n planted   paired-delta   residual")
rows=[]
for a_ in (-1000.,-500.,-250.,0.,+250.,+500.,+1000.):
    p=per_site(plant(img,0,a_*1e-6))
    common=sorted(set(base)&set(p))
    d=np.median([p[i]-base[i] for i in common])
    rows.append((a_,d))
    print("  %+7.0f     %+8.1f      %+7.1f" % (a_,d,d-a_))
A=np.array([r[0] for r in rows]); D=np.array([r[1] for r in rows])
sn=np.polyfit(A[A<0],D[A<0],1)[0]; sp=np.polyfit(A[A>0],D[A>0],1)[0]
print("\n slope NEG %.3f   slope POS %.3f   asymmetry %.3f" % (sn,sp,sp/sn))
