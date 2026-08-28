"""Map the estimator's response curve on both signs. A linear slope-1 response
on both sides means the SIGN arm's shortfall is an artifact of something else;
a kink near where red crosses green means the estimator has a deadzone."""
import numpy as np, vc_ca
from vc_commission import plant_radial, OLD, CAP

img = vc_ca.load(OLD % "dry-erase-marker-head-cpl")
H, W = img.shape[:2]; centre = (H/2.0, W/2.0)
S = vc_ca.sites(img[:, :, 1], centre); S = S[::max(1, len(S)//CAP)][:CAP]

def per_site(im):
    out = {}
    for i, (py, px, nx, ny, r, m, al) in enumerate(S):
        pg = vc_ca.profile(im[:, :, 1], py, px, nx, ny)
        pr = vc_ca.profile(im[:, :, 0], py, px, nx, ny)
        if pg is None or pr is None: continue
        s = vc_ca.shift(pr, pg)
        if s is None: continue
        out[i] = (s/al) / r * 1e6
    return out

base = per_site(img)
b0 = np.median(list(base.values()))
print("baseline absolute ppmR = %+.1f   (optics.rs documents +131.6..+255.5 for these masters)" % b0)
print("\n planted   paired-delta   residual   implied absolute")
print(" -------   ------------   --------   ----------------")
rows=[]
for a in (-1000.,-750.,-500.,-250.,-100.,0.,+100.,+250.,+500.,+750.,+1000.):
    p = per_site(plant_radial(img, 0, a*1e-6, centre))
    common = sorted(set(base) & set(p))
    d = np.median([p[i]-base[i] for i in common])
    rows.append((a,d))
    print("  %+7.0f     %+8.1f      %+7.1f     %+8.1f" % (a, d, d-a, b0+d))
A=np.array([r[0] for r in rows]); D=np.array([r[1] for r in rows])
neg=A<0; pos=A>0
sn=np.polyfit(A[neg],D[neg],1)[0]; sp=np.polyfit(A[pos],D[pos],1)[0]
print("\n slope on NEGATIVE plants: %.3f" % sn)
print(" slope on POSITIVE plants: %.3f" % sp)
print(" asymmetry ratio         : %.3f" % (sp/sn))
