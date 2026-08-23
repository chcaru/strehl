"""V14 -- M29 sec 2/3.  (a) exact numeric response of the static-map pipeline on a
SYNTHETIC FLAT (g == const, so g/blur(g) == 1 identically): this is the pure
algebra, no scene.  Compare with the doc's linearised 0.885 and its adopted
empirical 0.92.  (b) reproduce script 03's real-data response table.  (c) measure
g/blur24(g) at the plant location. (d) PRNU bound from script 01's cross-stack r."""
import glob, os, json
import numpy as np, rawpy
from scipy.ndimage import gaussian_filter
BLACK, SIG = 512.0, 24.0
PY, PX = 900, 1200

def mapify(frames):
    acc=None
    for g in frames:
        r=g/np.maximum(gaussian_filter(g,SIG),1.0)
        acc=r if acc is None else acc+r
    m=acc/len(frames)-1.0
    return (m-gaussian_filter(m,SIG)).astype(np.float32)

print("=== (a) PURE ALGEBRA: synthetic flat g == 3000, no scene at all ===")
N=768; c=N//2
yy,xx=np.mgrid[0:N,0:N]; d2=((yy-c)**2+(xx-c)**2).astype(np.float32)
print(f"{'sigma_p':>8s}{'b=sp2/(sp2+576)':>17s}{'(1-b)^2':>10s}{'(1-b)':>8s}"
      f"{'numeric R':>11s}{'A=1%':>9s}{'A=16%':>9s}")
for sp in (3.0,6.0,12.0):
    s=np.exp(-d2/(2*sp**2)).astype(np.float32)
    b=sp**2/(sp**2+SIG**2)
    g0=np.full((N,N),3000.0,np.float32)
    base=mapify([g0])
    vals=[]
    for A in (0.01,0.04,0.16):
        m=mapify([g0*(1.0-A*s)])
        vals.append(-float((m-base)[c,c])/A)
    print(f"{sp:8.1f}{b:17.4f}{(1-b)**2:10.4f}{1-b:8.4f}{vals[1]:11.4f}"
          f"{vals[0]:9.4f}{vals[2]:9.4f}")

print("\n=== (b)+(c) REAL DATA, 109MSDCF frame 0, plant at (900,1200) ===")
fs=sorted(glob.glob(r"D:\personal\macro\109MSDCF\*.ARW"))
with rawpy.imread(fs[0]) as r: g0=r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
h,w=g0.shape
lo0=np.maximum(gaussian_filter(g0,SIG),1.0)
print(f"  g/blur24(g) at plant, frame 0            = {(g0/lo0)[PY,PX]:.4f}")
rels=[]
for f in fs[:20]:
    with rawpy.imread(f) as r: g=r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
    rels.append(float((g/np.maximum(gaussian_filter(g,SIG),1.0))[PY,PX]))
print(f"  mean over 20 frames (script 04's 'rel')   = {np.mean(rels):.4f}   "
      f"(04-limit.json 109 loc0 rel = 0.2924)")
yy,xx=np.mgrid[0:h,0:w]; d2r=((yy-PY)**2+(xx-PX)**2).astype(np.float32); del yy,xx
base1=mapify([g0])
print(f"\n  {'depth':>7s}{'sig=3':>9s}{'sig=6':>9s}{'sig=12':>9s}   (script 03 table)")
tab={}
for A in (0.01,0.04,0.16):
    row=[]
    for sp in (3.0,6.0,12.0):
        m=mapify([g0*(1.0-A*np.exp(-d2r/(2*sp**2)))])
        row.append(-float((m-base1)[PY,PX])/A)
    tab[A]=row
    print(f"  {100*A:6.1f}%{row[0]:9.3f}{row[1]:9.3f}{row[2]:9.3f}")
print("\n  measured / pure-algebra, at fixed location -- should be CONSTANT "
      "if R = k*(g/blur):")
alg={3.0:None,6.0:None,12.0:None}
for i,sp in enumerate((3.0,6.0,12.0)):
    b=sp**2/(sp**2+SIG**2); alg[sp]=(1-b)**2
print("  " + "  ".join(f"sig={sp:.0f}: {tab[0.04][i]/alg[sp]:.4f}"
                       for i,sp in enumerate((3.0,6.0,12.0))))

print("\n=== (d) PRNU / common-static bound from script 01's own cross-stack r ===")
j=json.load(open(r"C:\dev\blog\death-of-software\projects\strehl\experiments"
                 r"\m29-static-defects\out\01-static.json"))
sd={k:v["rms"] for k,v in j["meta"].items()}
print(f"  {'pair':32s}{'r':>10s}{'null':>10s}{'sqrt(|r|*s1*s2)':>17s}")
best=[]
for p in j["pairs"]:
    if p["a"].startswith(("112","113")) and p["b"].startswith(("112","113")): continue
    v=np.sqrt(abs(p["r"])*sd[p["a"]]*sd[p["b"]])
    n=np.sqrt(abs(p["null"])*sd[p["a"]]*sd[p["b"]])
    print(f"  {p['a']+' x '+p['b']:32s}{p['r']:10.5f}{p['null']:10.5f}"
          f"{100*v:14.3f}%  (null {100*n:.3f}%)")
    best.append(max(v,n))
print(f"\n  tightest bound on any component COMMON to two different-subject "
      f"stacks: {100*min(best):.3f}%")
print(f"  M29 sec4 assumes the n=20 flat map floor is {0.120:.3f}% (pure photon).")
