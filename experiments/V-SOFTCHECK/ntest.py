"""Test or kill the N hypothesis: does per-coefficient max-selection inside the
merge inflate the master with bracket length N?

Two arms, SAME subject, SAME pin, SAME exposure (+2.33), SAME focus RANGE.
  ARM A: all 63 frames.
  ARM B: every 2nd frame -- 32 frames, first DSC00001 and last DSC00063 both
         preserved.  DENSITY is subsampled, RANGE is not (trap 4).
Each arm's reference is the per-site max over ITS OWN input frames, so both are
complete brackets with respect to what their own merge was given.
Single-frame renders were verified byte-identical across the two source
directories at matched exposure (1AD1F0D9CC2A02A6), so arm B reuses arm A's
even-index frames rather than re-rendering them.

PREDICTION, registered before the run.  If the >1 low-band readings on deep
stacks are an N-driven order statistic in the numerator, halving N must pull the
low bands DOWN toward 1.  If the low bands do not move, the hypothesis is dead.
"""
import os, sys, numpy as np, softcheck as S
T=256; NT=300
EDGES=np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
z=np.load(os.path.join(S.ROOT,"cache","113MSDCF--lin--T128.npz"))
coefs=z["coefs"].copy(); coefs[:,0,:]*=2.0
sel=np.argsort(z["m_lo"])[::-1][:NT]
oy=(z["oy"][sel]*2).astype(int); ox=(z["ox"][sel]*2).astype(int)
A=os.path.join(S.ROOT,"srgb","113MSDCF")
B=os.path.join(S.ROOT,"srgb-stride","113MSDCF-s2")
def rings(img,yy,xx):
    H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)
def boot(v,B_=1500,seed=11):
    r=np.random.default_rng(seed); n=len(v)
    return np.percentile([np.median(v[r.integers(0,n,n)]) for _ in range(B_)],[2.5,97.5])
MA=S.load_luma(os.path.join(A,"master.tiff"),"srgb")
MB=S.load_luma(os.path.join(B,"master.tiff"),"srgb")
assert MA.shape==(4688,7032) and MB.shape==(4688,7032),(MA.shape,MB.shape)
# The two merges chose different reference frames (63 -> 31, 32 -> 16), so arm
# B's output geometry is shifted.  Register the arms to each other with an
# INTEGER-ONLY shift: sub-pixel resampling would add blur to the very quantity
# being measured.
cy,cx=MA.shape[0]//2,MA.shape[1]//2; w=1024
a=MA[cy-w//2:cy+w//2,cx-w//2:cx+w//2].astype(np.float32); a-=a.mean()
b=MB[cy-w//2:cy+w//2,cx-w//2:cx+w//2].astype(np.float32); b-=b.mean()
cc=np.fft.ifft2(np.fft.fft2(a)*np.conj(np.fft.fft2(b))).real
sy,sx=np.unravel_index(np.argmax(cc),cc.shape)
sy=int(sy)-w if sy>w//2 else int(sy); sx=int(sx)-w if sx>w//2 else int(sx)
print(f"arm B geometry offset vs arm A : dy={sy} dx={sx} px (integer only)\n")
res={}
for name,M,idx,off in [("A N=63",MA,list(range(63)),(0,0)),
                       ("B N=32",MB,list(range(0,63,2)),(sy,sx))]:
    yy=oy+off[0]; xx=ox+off[1]
    Mr=rings(M,yy,xx)
    Fr=np.zeros((len(idx),NT,len(masks))); Fl=np.zeros_like(Fr)
    for j,k in enumerate(idx):
        F=S.load_luma(os.path.join(A,f"f{k:03d}.tiff"),"srgb")
        dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
        Fr[j]=rings(F,np.round(yy+dy).astype(int),np.round(xx+dx).astype(int))
        Fl[j]=rings(F,yy,xx); del F
    reg=np.median(Mr[:,3]/np.maximum(Fr[:,:,3].max(0),1e-30))
    lit=np.median(Mr[:,3]/np.maximum(Fl[:,:,3].max(0),1e-30))
    if not reg<lit:
        sys.exit(f"ABORT {name}: registration self-check failed ({reg:.4f} !< {lit:.4f})")
    print(f"  {name} registration self-check PASS: registered {reg:.4f} < literal {lit:.4f}")
    res[name]=(Mr,Fr,len(idx))
print(f"\n113MSDCF  matched focus RANGE, halved N   pin 9b05d0b7 / 44C2F2CD2E5B2894\n")
print(f"  {'band cyc/px':>11s} {'A N=63':>21s} {'B N=32':>21s}   {'A-B':>8s}")
for bnd in range(len(masks)):
    row=[]
    for name in ["A N=63","B N=32"]:
        Mr,Fr,n=res[name]
        r=Mr[:,bnd]/np.maximum(Fr[:,:,bnd].max(0),1e-30)
        row.append((np.median(r),boot(r)))
    print(f"   {EDGES[bnd]:.2f}-{EDGES[bnd+1]:.2f} {row[0][0]:8.4f} [{row[0][1][0]:.4f},{row[0][1][1]:.4f}]"
          f" {row[1][0]:8.4f} [{row[1][1][0]:.4f},{row[1][1][1]:.4f}] {row[0][0]-row[1][0]:+8.4f}")
