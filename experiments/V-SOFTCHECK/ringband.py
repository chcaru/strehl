"""Second, independent instrument: exact-band FFT ring power per tile.

Why a second instrument.  My DoG E_mid is not confined to one narrow band --
its measured half-power band is [0.131, 0.338] cyc/output-px -- so I cannot
answer "which band carries my focus signal?" with it.  A Hann-windowed FFT of
each 128px tile, integrated over radial rings, gives exact band edges and is
built from different primitives (no gaussian_filter, no integral images), so
it is an independent check on the DoG result as well.

Everything is per TILE.  In a focus stack "in focus" is a property of a tile
in a frame, not of a frame, so every best/worst frame choice here is made
per tile.  Tiles themselves are still selected by E_lo, the focus-
insensitive coarse band.

Frequencies are cyc per OUTPUT pixel of the gauge.  On the linear gauge one
output pixel is one Bayer quad (3516x2344 vs a 7032x4688 sensor), so
cyc/photosite = cyc/output-px / 2.  Both conventions are printed.
"""
import os, sys, time, numpy as np, softcheck as S
from analyze import load

subj = sys.argv[1]; NT = int(sys.argv[2]) if len(sys.argv) > 2 else 300
T, GAU = 128, "lin"
EDGES = np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50])
d = os.path.join(S.ROOT, GAU, subj)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff")); N=len(fl)
c = load(subj, GAU, T)
oy=np.asarray(c["oy"]); ox=np.asarray(c["ox"]); lo=np.asarray(c["m_lo"]); coefs=np.asarray(c["coefs"])
sel = np.argsort(lo)[::-1][:NT]
oy=oy[sel]; ox=ox[sel]; cy=oy+T/2.0; cx=ox+T/2.0
M = S.load_luma(os.path.join(d,"master.tiff"), GAU); H,W = M.shape
w1 = np.hanning(T); WIN = np.outer(w1,w1).astype(np.float32)
f1 = np.fft.fftfreq(T); R = np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks = [(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
nb = len(masks)

def rings(img, yy, xx):
    tl = np.stack([img[y:y+T, x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl = (tl - tl.mean(axis=(1,2), keepdims=True)) * WIN
    P = np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks], axis=1)   # (ntiles, nbands)

t0=time.time()
Mr = rings(M, oy.astype(int), ox.astype(int))
Fr = np.zeros((N, NT, nb), np.float64); Fm = np.zeros((N, NT))
for k, fn in enumerate(fl):
    F = S.load_luma(os.path.join(d, fn), GAU)
    dd = S.disp_at(coefs[k], cy, cx)
    yy = np.clip(np.round(oy+dd[:,0]).astype(int),0,H-T); xx = np.clip(np.round(ox+dd[:,1]).astype(int),0,W-T)
    Fr[k] = rings(F, yy, xx)
    Fm[k] = S.tile_means(S.dog(F,S.S_MID)**2, yy, xx, T)
    if k%40==0: print(f"  {fn} ({time.time()-t0:.0f}s)", flush=True)
Mm = S.tile_means(S.dog(M,S.S_MID)**2, oy.astype(int), ox.astype(int), T)
np.savez_compressed(os.path.join(S.ROOT,"cache",f"{subj}--ring.npz"),
                    Mr=Mr,Fr=Fr,Mm=Mm,Fm=Fm,EDGES=EDGES,N=N,oy=oy,ox=ox)
print(f"  saved {subj}--ring.npz  ({time.time()-t0:.0f}s)")
