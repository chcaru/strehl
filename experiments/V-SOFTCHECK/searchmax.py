"""Registration-proof denominator.

My weakest component is the global affine registration (24 phase-correlation
anchors, 6 parameters).  On flower-bud-alone-cpl its fit rms is 3.45 px
median / 18 px p90, and a mis-placed tile READS LOW, which INFLATES the
ratio.  So replace the denominator with a max over BOTH frame index and a
small displacement window: for every tile, every frame, take the best band
energy over offsets in +-8 px.  That can only RAISE the reference, so it is
conservative for a "master is softer" conclusion, and it cannot be fooled by
my own fit error.

It has its own order statistic (max over 25 offsets x N frames), so the
identical construction is run on the N+1 iid noised-master null, whose true
ratio is 1.000 by construction, and the null is reported beside it.
Integral images are built once per frame, so 25 offsets cost little.
"""
import os, sys, time, numpy as np, softcheck as S
from scipy import ndimage

subj = sys.argv[1]; R = 8; STEP_O = 4
T, STEP, MARGIN, GAU = 128, 64, 176, "lin"
d = os.path.join(S.ROOT, GAU, subj)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
N = len(fl); assert [int(f[1:4]) for f in fl] == list(range(N)), "non-contiguous frames"
M = S.load_luma(os.path.join(d, "master.tiff"), GAU); H, W = M.shape
oy, ox, sh = S.build_grid(H, W, T, STEP, MARGIN); nt = len(oy)
cy, cx = oy + T/2.0, ox + T/2.0
offs = [(dy,dx) for dy in range(-R,R+1,STEP_O) for dx in range(-R,R+1,STEP_O)]
print(f"{subj}: N={N} tiles={nt} offsets={len(offs)} (+-{R}px step {STEP_O})", flush=True)

Mm = S.tile_means(S.dog(M,S.S_MID)**2, oy, ox, T)
Mh = S.tile_means(S.dog(M,S.S_HI )**2, oy, ox, T)
Mlo= S.tile_means(S.dog(M,S.S_LOW)**2, oy, ox, T)
bm = np.full(nt,-np.inf); bh = np.full(nt,-np.inf); t0=time.time(); rl=[]
for k, fn in enumerate(fl):
    F = S.load_luma(os.path.join(d, fn), GAU)
    coef, rms, kp, tot = S.register(M, F); rl.append(rms)
    dd = S.disp_at(coef, cy, cx)
    Am = S.dog(F,S.S_MID)**2; Ah = S.dog(F,S.S_HI)**2
    for (ay,ax) in offs:
        yy = np.clip(np.round(oy+dd[:,0]).astype(int)+ay, 0, H-T)
        xx = np.clip(np.round(ox+dd[:,1]).astype(int)+ax, 0, W-T)
        vm = S.tile_means(Am, yy, xx, T)
        take = vm > bm
        if take.any():
            vh = S.tile_means(Ah, yy, xx, T); bm[take]=vm[take]; bh[take]=vh[take]
    if k % 20 == 0: print(f"  {fn} rms={rms:.2f} ({time.time()-t0:.0f}s)", flush=True)
CN = 0.185088; sel = Mlo >= np.median(Mlo)
r_ns = np.median(Mm[sel]/bm[sel])
r_sb = np.median((Mm-CN*Mh)[sel]/(bm-CN*bh)[sel])
print(f"  SEARCH-MAX ratio  NOSUB {r_ns:.4f}   SUB {r_sb:.4f}   (fit rms median {np.median(rl):.2f}px)")

G_HI = 0.421466
c0 = np.load(os.path.join(S.ROOT,"cache",f"{subj}--{GAU}--T{T}.npz"))
sig = np.sqrt(np.maximum(np.median(c0["f_hi_none"],axis=0),0)/G_HI).reshape(sh)
smap = ndimage.zoom(sig,(H/sh[0],W/sh[1]),order=1).astype(np.float32)
smap = np.pad(smap,[(0,max(0,H-smap.shape[0])),(0,max(0,W-smap.shape[1]))],mode="edge")[:H,:W]
rng = np.random.default_rng(7); nm=np.full(nt,-np.inf); nh=np.full(nt,-np.inf)
for k in range(N+1):
    Fn = M + smap*rng.standard_normal(M.shape).astype(np.float32)
    Am = S.dog(Fn,S.S_MID)**2; Ah = S.dog(Fn,S.S_HI)**2
    if k == 0:
        n0m = S.tile_means(Am,oy,ox,T); n0h = S.tile_means(Ah,oy,ox,T); continue
    for (ay,ax) in offs:
        yy=np.clip(oy+ay,0,H-T); xx=np.clip(ox+ax,0,W-T)
        vm=S.tile_means(Am,yy,xx,T); take=vm>nm
        if take.any():
            vh=S.tile_means(Ah,yy,xx,T); nm[take]=vm[take]; nh[take]=vh[take]
np.savez_compressed(os.path.join(S.ROOT,"cache",f"{subj}--searchmax.npz"),
                    Mm=Mm,Mh=Mh,Mlo=Mlo,bm=bm,bh=bh,nm=nm,nh=nh,n0m=n0m,n0h=n0h,N=N,rms=np.array(rl))
print(f"  SEARCH-MAX null   NOSUB {np.median(n0m[sel]/nm[sel]):.4f}"
      f"   SUB {np.median((n0m-CN*n0h)[sel]/(nm-CN*nh)[sel]):.4f}   (truth 1.000 by construction)")
