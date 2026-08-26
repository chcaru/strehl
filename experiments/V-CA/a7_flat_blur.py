import numpy as np, tifffile, sys
def lin(u16):
    a = u16.astype(np.float32)/65535.0
    return np.where(a <= 0.04045, a/12.92, ((a+0.055)/1.055)**2.4).astype(np.float32)
def sobel(g):
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:,1:-1] = g[:,2:]-g[:,:-2]; gy[1:-1,:] = g[2:,:]-g[:-2,:]
    return np.hypot(gx,gy)
def hp(a):
    # 3x3 box high-pass: HF = a - box3(a).  Separable, float32.
    b = a.copy()
    b[:,1:-1] = (a[:,:-2]+a[:,1:-1]+a[:,2:])/3.0
    c = b.copy()
    c[1:-1,:] = (b[:-2,:]+b[1:-1,:]+b[2:,:])/3.0
    return a - c
PAIRS = [
 ("bee-1-cpl",       r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\bee-1-cpl.tiff",       r"C:\dev\strehl-out\REVIEW\ca\bee-1-cpl--cafix.tiff"),
 ("coffee-bubbles",  r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\coffee-bubbles.tiff",  r"C:\dev\strehl-out\V-ca\coffee-bubbles--cafix.tiff"),
 ("foam",            r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\foam.tiff",            r"C:\dev\strehl-out\V-ca\foam--cafix.tiff"),
 ("couch-fibers-cpl",r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\couch-fibers-cpl.tiff",r"C:\dev\strehl-out\V-ca\couch-fibers-cpl--cafix.tiff"),
 ("flowers-cpl",     r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\flowers-cpl.tiff",     r"C:\dev\strehl-out\V-ca\flowers-cpl--cafix.tiff"),
 ("wrapped-text-1",  r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\wrapped-text-1.tiff",  r"C:\dev\strehl-out\V-ca\wrapped-text-1--cafix.tiff"),
]
print("HF RMS ratio ON/OFF per channel.  In the FLAT set there is NO fringe to remove,")
print("so any HF loss there is BLUR, not correction.  R is the only channel the")
print("correction touches in camera space (l5_green_is_never_touched).\n")
print("%-18s %-6s %8s %8s %8s   %8s %8s %8s" % ("subject","","R flat","G flat","B flat","R edge","G edge","B edge"))
for name, po, pn in PAIRS:
    o = tifffile.imread(po); n = tifffile.imread(pn)
    assert o.dtype == np.uint16 and n.dtype == np.uint16, "not uint16"
    lo, ln_ = lin(o), lin(n); del o, n
    g = sobel(0.5*(lo[:,:,1]+ln_[:,:,1]))
    flat = g <= np.quantile(g,0.50); edge = g >= np.quantile(g,0.99); del g
    out = []
    for i in range(3):
        ho, hn = hp(lo[:,:,i]), hp(ln_[:,:,i])
        for m in (flat, edge):
            ro = float(np.sqrt(np.mean(ho[m]**2))); rn = float(np.sqrt(np.mean(hn[m]**2)))
            out.append(rn/ro if ro else float("nan"))
        del ho, hn
    print("%-18s %-6s %8.4f %8.4f %8.4f   %8.4f %8.4f %8.4f"
          % (name,"ratio", out[0],out[2],out[4], out[1],out[3],out[5]))
    del lo, ln_, flat, edge
