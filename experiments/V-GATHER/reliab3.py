"""Split-half reliability with PER-TILE integer re-registration.

The whole-image version failed its own control (r_TEX ~ 0), which means the two
half-stacks are not on a common geometry: each half solves its own alignment
from its own reference frame, so a small residual rotation/scale displaces the
edges of a 3072 px crop by several pixels.  Re-register EACH 256 px tile by an
integer shift (search +-6 px) before correlating; that removes translation
locally and leaves only sub-pixel residual.

Control that decides whether the fix worked: r_TEX must come up to ~1.
If it does, r_FLAT is then interpretable.
"""
import os, json
import numpy as np, tifffile

OUT=r"C:\dev\strehl-out\V-GATHER"
def luma(im): return 0.2126*im[:,:,0]+0.7152*im[:,:,1]+0.0722*im[:,:,2]
def load(s,h,a): return luma(tifffile.imread(os.path.join(OUT,f"sp-{s}-{h}-g{a}.tiff"))[:,:,:3].astype(np.float64))
def centre(y,n):
    h,w=y.shape; return y[h//2-n//2:h//2+n//2, w//2-n//2:w//2+n//2]
def boxblur(y,r):
    k=2*r+1
    c=np.cumsum(np.pad(y,((r+1,r),(0,0)),mode="edge"),axis=0); y1=(c[k:]-c[:-k])/k
    c=np.cumsum(np.pad(y1,((0,0),(r+1,r)),mode="edge"),axis=1); return (c[:,k:]-c[:,:-k])/k
def hp(y,r=3): return y-boxblur(y,r)

def tile_corr(A,B,r0,c0,t,maxs=6):
    """best integer-shift Pearson r of high-pass, tile at (r0,c0) size t."""
    a=A[r0:r0+t, c0:c0+t]
    best=(-2.0,0,0)
    for dy in range(-maxs,maxs+1):
        for dx in range(-maxs,maxs+1):
            b=B[r0+dy:r0+dy+t, c0+dx:c0+dx+t]
            if b.shape!=a.shape: continue
            x=a-a.mean(); y=b-b.mean()
            d=np.sqrt((x*x).mean()*(y*y).mean())
            if d==0: continue
            r=float((x*y).mean()/d)
            if r>best[0]: best=(r,dy,dx)
    return best

def run(subj,arm,t=256,n=3072,maxs=6):
    e=load(subj,"even",arm); o=load(subj,"odd",arm)
    E=centre(e,n+2*maxs+8); O=centre(o,n+2*maxs+8)
    M=(E+O)/2.0
    he,ho=hp(E),hp(O)
    off=maxs+4
    rows=[]
    for i in range(n//t):
        for j in range(n//t):
            r0,c0=off+i*t, off+j*t
            s=float(M[r0:r0+t, c0:c0+t].std())
            r,dy,dx=tile_corr(he,ho,r0,c0,t,maxs)
            amp=float(np.sqrt((he[r0:r0+t,c0:c0+t]**2).mean()))
            rows.append((s,r,amp,dy,dx))
    rows.sort(key=lambda z:z[0])
    k=len(rows)//4
    flat=rows[:k]; tex=rows[-k:]
    f=lambda g:(float(np.mean([z[1] for z in g])), float(np.sqrt(np.mean([z[2]**2 for z in g]))))
    rf,af=f(flat); rt,at=f(tex)
    sh=set((z[3],z[4]) for z in rows)
    return {"arm":arm,"r_flat":rf,"r_tex":rt,"hp_flat":af,"hp_tex":at,
            "n_tiles":len(rows),"distinct_shifts":len(sh),
            "shift_span":[max(abs(z[3]) for z in rows), max(abs(z[4]) for z in rows)]}

if __name__=="__main__":
    print(f"{'subject':16s}{'arm':5s}{'r_FLAT':>9s}{'r_TEX':>9s}{'hpFLAT':>10s}{'hpTEX':>10s}{'shifts':>8s}{'span':>10s}")
    res={}
    for subj in ("foam","wrapped-text-1"):
        res[subj]={}
        for arm in ("0","1"):
            d=run(subj,arm); res[subj][arm]=d
            print(f"{subj:16s}g{arm:4s}{d['r_flat']:9.4f}{d['r_tex']:9.4f}{d['hp_flat']:10.2f}"
                  f"{d['hp_tex']:10.2f}{d['distinct_shifts']:8d}{str(d['shift_span']):>10s}",flush=True)
    print()
    print("r_TEX is the control: it must approach 1 for r_FLAT to mean anything.")
    json.dump(res,open(os.path.join(OUT,"reliab3.json"),"w"),indent=1)
