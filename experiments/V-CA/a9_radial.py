import numpy as np, tifffile
def lin(u):
    a=u.astype(np.float32)/65535.0
    return np.where(a<=0.04045,a/12.92,((a+0.055)/1.055)**2.4).astype(np.float32)
def sobel(g):
    gx=np.zeros_like(g); gy=np.zeros_like(g)
    gx[:,1:-1]=g[:,2:]-g[:,:-2]; gy[1:-1,:]=g[2:,:]-g[:-2,:]
    return np.hypot(gx,gy)
def rs(v):
    if v.size==0: return float("nan")
    m=np.median(v); return float(1.4826*np.median(np.abs(v-m)))
PAIRS=[("bee-1-cpl",r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\bee-1-cpl.tiff",r"C:\dev\strehl-out\REVIEW\ca\bee-1-cpl--cafix.tiff"),
       ("foam",r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\foam.tiff",r"C:\dev\strehl-out\V-ca\foam--cafix.tiff"),
       ("flowers-cpl",r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\flowers-cpl.tiff",r"C:\dev\strehl-out\V-ca\flowers-cpl--cafix.tiff")]
print("sigma(R-G) ON/OFF on the EDGE set, by normalised field radius (1.0 = half-diagonal).")
print("The profile declares support only to r = 0.788 -- 'Declared, not enforced'")
print("(optics.rs:365). Bins beyond it are EXTRAPOLATION. n = edge px in bin.\n")
EDGES=[0.0,0.2,0.4,0.6,0.788,0.9,1.0]
hdr="%-14s" % "subject"
for i in range(len(EDGES)-1):
    mark="*" if EDGES[i]>=0.788 else " "
    hdr += "%11s" % ("%.2f-%.2f%s"%(EDGES[i],EDGES[i+1],mark))
print(hdr)
for name,po,pn in PAIRS:
    o=tifffile.imread(po); n=tifffile.imread(pn)
    assert o.dtype==np.uint16 and n.dtype==np.uint16
    lo,ln_=lin(o),lin(n); del o,n
    H,W=lo.shape[:2]
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    r=np.hypot(yy-(H-1)/2.0,xx-(W-1)/2.0)/np.hypot((H-1)/2.0,(W-1)/2.0); del yy,xx
    g=sobel(0.5*(lo[:,:,1]+ln_[:,:,1])); edge=g>=np.quantile(g,0.99); del g
    row="%-14s"%name; ns=[]
    for i in range(len(EDGES)-1):
        m=edge&(r>=EDGES[i])&(r<EDGES[i+1])
        if m.sum()<2000: row+="%11s"%"n<2k"; ns.append(int(m.sum())); continue
        a=rs((lo[:,:,0]-lo[:,:,1])[m]); b=rs((ln_[:,:,0]-ln_[:,:,1])[m])
        row+="%11.4f"%(b/a if a else float("nan")); ns.append(int(m.sum()))
    print(row); print("%-14s"%"   n"+"".join("%11d"%x for x in ns))
    del lo,ln_,edge,r
print("\n* = beyond the profile's declared support radius.")
