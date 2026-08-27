"""Split-half reliability, corrected.

r = Pearson correlation of the high-pass field between two DISJOINT 20-frame
stacks of the same subject/arm.  Real detail is identical between halves (r->1);
photon noise is independent (r->0).

Three controls, all required:
  TEX reference : same statistic in the BUSIEST tiles.  If the two halves were
                  mutually mis-registered, r would collapse there too.  A high
                  r_tex with a low r_flat proves registration is fine and the
                  flat-tile high-pass really is noise.
  NULL          : half vs itself -> r = 1 exactly.
  POSITIVE      : inject IDENTICAL fine structure into both halves at rising
                  amplitude -> r must RISE monotonically toward 1.
"""
import os, json
import numpy as np, tifffile

OUT = r"C:\dev\strehl-out\V-GATHER"

def luma(im): return 0.2126*im[:,:,0] + 0.7152*im[:,:,1] + 0.0722*im[:,:,2]
def load(s,h,a): return luma(tifffile.imread(os.path.join(OUT,f"sp-{s}-{h}-g{a}.tiff"))[:,:,:3].astype(np.float64))
def centre(y,n):
    h,w=y.shape; return y[h//2-n//2:h//2+n//2, w//2-n//2:w//2+n//2]

def int_shift(a,b,maxs=48):
    n=1024; A=centre(a,n)-centre(a,n).mean(); B=centre(b,n)-centre(b,n).mean()
    w=np.outer(np.hanning(n),np.hanning(n))
    R=np.fft.rfft2(A*w)*np.conj(np.fft.rfft2(B*w)); m=np.abs(R); m[m==0]=1
    cc=np.fft.fftshift(np.fft.irfft2(R/m,s=(n,n))); k=n//2
    win=cc[k-maxs:k+maxs+1,k-maxs:k+maxs+1]
    iy,ix=np.unravel_index(np.argmax(win),win.shape); return iy-maxs, ix-maxs

def boxblur(y,r):
    k=2*r+1
    c=np.cumsum(np.pad(y,((r+1,r),(0,0)),mode="edge"),axis=0); y1=(c[k:]-c[:-k])/k
    c=np.cumsum(np.pad(y1,((0,0),(r+1,r)),mode="edge"),axis=1); return (c[:,k:]-c[:,:-k])/k
def hp(y,r=3): return y-boxblur(y,r)

def corr_in(sel, he, ho, t=256):
    H,W = he.shape; xs=[]; ys=[]
    for i in range(H//t):
        for j in range(W//t):
            if sel[i,j]:
                xs.append(he[i*t:(i+1)*t, j*t:(j+1)*t].ravel())
                ys.append(ho[i*t:(i+1)*t, j*t:(j+1)*t].ravel())
    x=np.concatenate(xs); y=np.concatenate(ys); x=x-x.mean(); y=y-y.mean()
    return float((x*y).mean()/np.sqrt((x*x).mean()*(y*y).mean())), float(np.sqrt((x*x).mean()))

def run(subj, arm, inject_same=0.0, seed=5, t=256, n=3072):
    e=load(subj,"even",arm); o=load(subj,"odd",arm)
    dy,dx=int_shift(e,o); o=np.roll(np.roll(o,dy,0),dx,1)
    E=centre(e,n); O=centre(o,n)
    if inject_same:
        rng=np.random.default_rng(seed)
        s=rng.normal(0,inject_same,E.shape)   # IDENTICAL in both halves
        E=E+s; O=O+s
    M=(E+O)/2.0
    st=M.reshape(n//t,t,n//t,t).std(axis=(1,3))
    flat = st<=np.quantile(st,0.25); tex = st>=np.quantile(st,0.75)
    he,ho=hp(E),hp(O)
    rf,af=corr_in(flat,he,ho,t); rt,at=corr_in(tex,he,ho,t)
    return {"arm":arm,"shift":[int(dy),int(dx)],"r_flat":rf,"r_tex":rt,
            "hp_rms_flat":af,"hp_rms_tex":at}

if __name__=="__main__":
    print(f"{'subject':16s}{'arm':4s}{'shift':10s}{'r_FLAT':>9s}{'r_TEX':>9s}{'hpRMSflat':>11s}{'hpRMStex':>11s}")
    res={}
    for subj in ("foam","wrapped-text-1"):
        res[subj]={}
        for arm in ("0","1"):
            d=run(subj,arm); res[subj][arm]=d
            print(f"{subj:16s}g{arm:3s}{str(d['shift']):10s}{d['r_flat']:9.4f}{d['r_tex']:9.4f}"
                  f"{d['hp_rms_flat']:11.2f}{d['hp_rms_tex']:11.2f}",flush=True)
    print()
    print("NULL  r(half, itself) = 1.000000 by construction (identity), not informative; the")
    print("      informative reference is r_TEX above.")
    print()
    for amp in (0.0, 40.0, 120.0, 400.0):
        d=run("foam","0",inject_same=amp)
        print(f"POSCTL foam g0  identical structure sd={amp:6.1f} -> r_flat={d['r_flat']:7.4f} "
              f"hp_rms_flat={d['hp_rms_flat']:8.2f}   (r_flat must RISE)",flush=True)
    with open(os.path.join(OUT,"reliab2.json"),"w") as f: json.dump(res,f,indent=1)
