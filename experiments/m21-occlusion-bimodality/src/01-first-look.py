import numpy as np, rawpy, glob, os
from scipy.ndimage import uniform_filter, sobel
BLACK=512; R=13
def focus_field(g):
    gx=sobel(g,axis=1,mode='reflect')/8.0; gy=sobel(g,axis=0,mode='reflect')/8.0
    mag=np.sqrt(gx*gx+gy*gy)
    return uniform_filter(mag, 2*R+1)
def load(stack, crop=None, nmax=None):
    fs=sorted(glob.glob(os.path.join(stack,"*.ARW")))
    if nmax: fs=fs[:nmax]
    out=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        if crop: g=g[crop[0]:crop[1],crop[2]:crop[3]]
        out.append(focus_field(g))
    return np.stack(out), len(fs)

def bimodality(V):
    """V: (K,H,W) through-focus focus volume. Returns (n_peaks, dip_depth, argmax)."""
    K=V.shape[0]
    # light smoothing along the focus axis to suppress per-frame noise
    Vs=np.copy(V)
    Vs[1:-1]=(V[:-2]+2*V[1:-1]+V[2:])/4.0
    mx=Vs.max(0); mn=Vs.min(0); rng=np.maximum(mx-mn,1e-6)
    # a peak is a strict interior local max rising at least `thr` of the range above BOTH neighbours
    thr=0.04
    ispk=np.zeros_like(Vs,bool)
    ispk[1:-1]=(Vs[1:-1]>Vs[:-2]+thr*rng)&(Vs[1:-1]>Vs[2:]+thr*rng)
    npk=ispk.sum(0)
    # dip depth between the two highest peaks
    idx=np.argsort(Vs,0)
    return npk, mx, mn, np.argmax(Vs,0)

print("=== TEST: is the through-focus curve BIMODAL at occluding edges? ===")
print("    Review proposal R2. Claim: a veiled background pixel has TWO peaks, one at the")
print("    foreground depth and one at its own, and no selector can be right there.\n")
CROP=(600,1624,900,1924)   # 1024x1024 of the CFA green plane
for name,path,nmax in (("109MSDCF (real focus sweep)", r"C:\dev\macro\test\109MSDCF", None),
                       ("coffee-bubbles (NULL: no focus change)", r"D:\personal\macro\coffee-bubbles", None)):
    V,n=load(path,CROP,nmax)
    npk,mx,mn,am=bimodality(V)
    contrast=(mx-mn)/np.maximum(mx,1e-6)
    strong=contrast>0.10                       # only pixels with a real focus response
    multi=(npk>=2)&strong
    print(f"{name}: {n} frames, volume {V.shape}")
    print(f"   pixels with a real through-focus response (>10% modulation): {strong.mean()*100:5.1f}%")
    print(f"   of those, MULTI-PEAKED (>=2 interior peaks):                 {multi.sum()/max(strong.sum(),1)*100:5.1f}%")
    if 'MSDCF' in name:
        # does multi-peakedness concentrate where the winner field has a DEPTH STEP?
        amf=uniform_filter(am.astype(np.float32),9)
        step=np.abs(np.gradient(amf)[0])+np.abs(np.gradient(amf)[1])
        hi=step>np.percentile(step[strong],90)  # top decile of depth-step magnitude
        lo=step<np.percentile(step[strong],50)
        a=multi[strong&hi].mean()*100; b=multi[strong&lo].mean()*100
        print(f"   multi-peaked rate at DEPTH STEPS (top decile of |grad winner|): {a:5.1f}%")
        print(f"   multi-peaked rate on SMOOTH depth (bottom half):               {b:5.1f}%")
        print(f"   ENRICHMENT at depth steps: {a/max(b,1e-6):.2f}x")
    print()
