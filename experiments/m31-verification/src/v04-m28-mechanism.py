"""V04 -- What IS the deterministic residual?  M28 S1 says "accumulating
geometric warp" (breathing).  Test the three candidates head to head."""
import os
import numpy as np
CACHE=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"
a_raw=np.load(os.path.join(CACHE,"109MSDCF.npy")).astype(np.float64)
n=len(a_raw); ISO=160.0; g_dn=ISO/436.8; rn2=(4.20*g_dn)**2
def area_mean(a,d):
    N,h,w=a.shape; h2,w2=(h//d)*d,(w//d)*d
    return a[:,:h2,:w2].reshape(N,h2//d,d,w2//d,d).mean(axis=(2,4))
flat=a_raw.reshape(n,-1)
gmed=np.median(flat,axis=1); gmed/=np.median(gmed)
a8=area_mean(a_raw/gmed[:,None,None],8)
ref=np.median(a8,axis=0)
sig=np.sqrt(np.maximum(g_dn*np.maximum(ref,0)+rn2,1e-6))/8.
gy,gx=np.gradient(ref); grad=np.sqrt(gy**2+gx**2)
h=w=ref.shape[0]
yy,xx=np.mgrid[0:h,0:w]
r=np.sqrt((yy-(h-1)/2.)**2+(xx-(w-1)/2.)**2)
edges=np.linspace(0,r.max(),9)

print("=== TEST A: does the BREATHING prediction |grad|*r/sigma reproduce the")
print("            observed radial |z| profile (whole-stack ref, median gain)? ===")
z=np.median(np.abs(a8-ref)/sig,axis=0)
rows=[]
for i in range(8):
    m=(r>=edges[i])&(r<edges[i+1])
    rows.append((float(np.median(r[m])),float(np.median(z[m])),
                 float(np.median(grad[m])),float(np.median(sig[m]))))
print(f"{'bin':>3s}{'r':>8s}{'obs |z|':>9s}{'|grad|':>8s}{'sigma':>7s}{'grad*r/sig':>12s}{'pred(norm b1)':>15s}")
base=rows[1]
for i,(rr,zz,gg,ss) in enumerate(rows):
    pred=(gg*rr/ss)/(base[2]*base[0]/base[3])*base[1]
    print(f"{i:3d}{rr:8.1f}{zz:9.2f}{gg:8.2f}{ss:7.3f}{gg*rr/ss:12.2f}{pred:15.2f}")
print("  -> breathing predicts a NEARLY FLAT profile in noise-normalised units;")
print("     observed rises 1.82x.  b7/b1 obs %.2f  pred %.2f" %
      (rows[7][1]/rows[1][1], (rows[7][2]*rows[7][0]/rows[7][3])/(rows[1][2]*rows[1][0]/rows[1][3])))

print("\n=== TEST B: strip a per-frame scalar gain from the whole-stack residual ===")
c=(a8*ref).sum(axis=(1,2))/(ref*ref).sum()
z2=np.median(np.abs(a8-c[:,None,None]*ref)/sig,axis=0)
p1=[float(np.median(z[(r>=edges[i])&(r<edges[i+1])])) for i in range(8)]
p2=[float(np.median(z2[(r>=edges[i])&(r<edges[i+1])])) for i in range(8)]
print("  before: "+" ".join(f"{v:6.2f}" for v in p1)+f"   out/in {p1[-1]/p1[0]:.2f}")
print("  after : "+" ".join(f"{v:6.2f}" for v in p2)+f"   out/in {p2[-1]/p2[0]:.2f}")
print(f"  per-frame fitted scalar range {c.min():.5f}..{c.max():.5f} (p-p {100*(c.max()-c.min()):.2f}%)")

print("\n=== TEST C: is the residual proportional to |grad| (geometric) or to S")
print("            (photometric)?  Median |delta| in DN, split by quartile. ===")
d16=np.abs(a8[16:]-a8[:-16]).mean(axis=0)
d1=np.abs(a8[1:]-a8[:-1]).mean(axis=0)
for nm,vals in (("|grad| quartile",grad),("level S quartile",ref)):
    q=np.percentile(vals,[25,50,75])
    print(f"  {nm}")
    for i,(lo,hi) in enumerate(zip([-1e9]+list(q),list(q)+[1e9])):
        m=(vals>=lo)&(vals<hi)
        print(f"    q{i+1}: n={m.sum():6d}  median |grad| {np.median(grad[m]):7.2f}  "
              f"median S {np.median(ref[m]):8.1f}  <|d1|> {np.median(d1[m]):7.3f}  "
              f"<|d16|> {np.median(d16[m]):8.3f}  ratio {np.median(d16[m])/np.median(d1[m]):5.2f}")

print("\n=== TEST D: log-log slope of pairwise |z| vs separation (linear => 1.0) ===")
for nm,gv in (("median gain",np.median(flat,axis=1)),("mean gain",flat.mean(axis=1)),
              ("no gain",np.ones(n))):
    gg=gv/np.median(gv)
    A=area_mean(a_raw/gg[:,None,None],8); R=np.median(A,axis=0)
    S=np.sqrt(np.maximum(g_dn*np.maximum(R,0)+rn2,1e-6))/8.
    ks=np.array([1,2,4,8,16]); vals=np.array([np.median(np.abs(A[k:]-A[:-k])/(S*np.sqrt(2.))) for k in ks])
    sl=np.polyfit(np.log(ks),np.log(vals),1)[0]
    inc=np.log2(vals[1:]/vals[:-1])
    print(f"  {nm:12s} vals "+" ".join(f"{v:7.3f}" for v in vals)+
          f"   overall loglog slope {sl:.3f}   per-octave slopes "+" ".join(f"{x:5.2f}" for x in inc))
