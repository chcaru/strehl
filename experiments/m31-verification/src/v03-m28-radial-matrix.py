"""V03 -- M28 S1's decisive comparison is 1.82x (whole-stack ref) vs 0.98x
(adjacent ref).  But script 02 used the MEDIAN gain and script 04 the MEAN gain,
so the comparison changes two things at once.  Full 3x3 matrix."""
import os
import numpy as np
CACHE = r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"
a_raw = np.load(os.path.join(CACHE,"109MSDCF.npy")).astype(np.float64)
n=len(a_raw); ISO=160.0; g_dn=ISO/436.8; rn2=(4.20*g_dn)**2
def area_mean(a,d):
    N,h,w=a.shape; h2,w2=(h//d)*d,(w//d)*d
    return a[:,:h2,:w2].reshape(N,h2//d,d,w2//d,d).mean(axis=(2,4))
flat=a_raw.reshape(n,-1)
GAINS={"median":np.median(flat,axis=1),"mean":flat.mean(axis=1),"none":np.ones(n)}

h=w=1536//8
yy,xx=np.mgrid[0:h,0:w]
r=np.sqrt((yy-(h-1)/2.)**2+(xx-(w-1)/2.)**2)
edges=np.linspace(0,r.max(),9)
def radial(m):
    return [float(np.median(m[(r>=edges[i])&(r<edges[i+1])])) for i in range(8)]

print(f"{'gain':8s} {'reference':22s} " + "".join(f"{('b'+str(i)):>7s}" for i in range(8)) + "   out/in")
for gname,gv in GAINS.items():
    gg=gv/np.median(gv)
    a8=area_mean(a_raw/gg[:,None,None],8)
    # whole-stack median reference (script 02's S1 radial)
    ref=np.median(a8,axis=0)
    sig=np.sqrt(np.maximum(g_dn*np.maximum(ref,0)+rn2,1e-6))/8.
    p=radial(np.median(np.abs(a8-ref)/sig,axis=0))
    print(f"{gname:8s} {'whole-stack median':22s} " + "".join(f"{v:7.2f}" for v in p) + f"  {p[-1]/p[0]:6.2f}")
    # adjacent 1st difference
    s1=np.sqrt(np.maximum(g_dn*np.maximum((a8[:-1]+a8[1:])/2.,0)+rn2,1e-6))/8.
    p=radial(np.median(np.abs(a8[1:]-a8[:-1])/(s1*np.sqrt(2.)),axis=0))
    print(f"{gname:8s} {'adjacent 1st-diff':22s} " + "".join(f"{v:7.2f}" for v in p) + f"  {p[-1]/p[0]:6.2f}")
    # adjacent 2nd difference (the M28 detector)
    rn=(a8[:-2]+a8[2:])/2.
    s2=np.sqrt(np.maximum(g_dn*np.maximum(rn,0)+rn2,1e-6))/8.
    p=radial(np.median(np.abs(a8[1:-1]-rn)/(s2*np.sqrt(1.5)),axis=0))
    print(f"{gname:8s} {'adjacent 2nd-diff':22s} " + "".join(f"{v:7.2f}" for v in p) + f"  {p[-1]/p[0]:6.2f}")
    print()

# is the radial trend tracking signal LEVEL (photometric) or gradient (geometric)?
gg=np.median(flat,axis=1); gg/=np.median(gg)
a8=area_mean(a_raw/gg[:,None,None],8); ref=np.median(a8,axis=0)
gy,gx=np.gradient(ref); grad=np.sqrt(gy**2+gx**2)
print("radial bin:      " + "".join(f"{('b'+str(i)):>9s}" for i in range(8)))
print("median level DN: " + "".join(f"{v:9.1f}" for v in radial(ref)))
print("median |grad|:   " + "".join(f"{v:9.2f}" for v in radial(grad)))
