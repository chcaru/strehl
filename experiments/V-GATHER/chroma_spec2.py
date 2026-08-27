"""Fixes three things in chroma_spec.py:
 (1) absolute band spectra, so a ratio PEAK can be told from a denominator DIP;
 (2) a NO-HIGH-PASS variant -- the 7x7 box kills the lowest bands, and the
     'created at low f' claim must not rest on 1e-6 of residual transmission;
 (3) a GRADED potency curve for the maze plant instead of one arbitrary
     threshold (the previous PASS bar of x20 was my number, not the data's).
"""
from __future__ import annotations
import os, sys, math
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma import hp, boxblur
from mtfsim2 import gather_mtf

OUT = r"C:\dev\strehl-out\V-GATHER"
T, NB = 128, 24
_win = np.hanning(T)[:, None] * np.hanning(T)[None, :]
_fy = np.fft.fftshift(np.fft.fftfreq(T))[:, None]
_fx = np.fft.fftshift(np.fft.fftfreq(T))[None, :]
_rad = np.sqrt(_fx**2 + _fy**2)
_edges = np.linspace(0.0, 0.5, NB+1)
_masks = [(_rad >= _edges[i]) & (_rad < _edges[i+1]) for i in range(NB)]
_ctr = 0.5*(_edges[:-1]+_edges[1:])
_corner = (np.abs(_fx) > 0.38) & (np.abs(_fy) > 0.38)
_axes = ((np.abs(_fx) > 0.38) & (np.abs(_fy) < 0.08)) | ((np.abs(_fy) > 0.38) & (np.abs(_fx) < 0.08))

def load(s,a): return tifffile.imread(os.path.join(OUT, f"{s}-q-g{a}.tiff"))[:,:,:3].astype(np.float64)
def chroma(im): return im[:,:,0]-im[:,:,2]
def luma(im): return 0.2126*im[:,:,0]+0.7152*im[:,:,1]+0.0722*im[:,:,2]

def tiles(l0,l1,q):
    h=(min(l0.shape[0],l1.shape[0])//T)*T; w=(min(l0.shape[1],l1.shape[1])//T)*T
    st=((l0[:h,:w]+l1[:h,:w])/2).reshape(h//T,T,w//T,T).std(axis=(1,3))
    return h,w,np.argwhere(st<=np.quantile(st,q))

def spec(img,idx):
    acc=np.zeros(NB); cor=0.; ax=0.
    for ty,tx in idx:
        t=img[ty*T:(ty+1)*T, tx*T:(tx+1)*T]
        P=np.abs(np.fft.fftshift(np.fft.fft2((t-t.mean())*_win)))**2
        for i in range(NB): acc[i]+=P[_masks[i]].mean()
        cor+=P[_corner].mean(); ax+=P[_axes].mean()
    n=len(idx); return acc/n, cor/n, ax/n

def run(s,q=0.05,plant=None,use_hp=True):
    i0,i1=load(s,"0"),load(s,"1")
    if plant is not None: i1=plant(i1)
    h,w,idx=tiles(luma(i0),luma(i1),q)
    f=(lambda x: hp(x)) if use_hp else (lambda x: x)
    a=spec(f(chroma(i0))[:h,:w],idx); b=spec(f(chroma(i1))[:h,:w],idx)
    del i0,i1; return a,b,len(idx)

print("="*96); print("GRADED POTENCY -- planted diagonal-Nyquist chroma maze, foam, q=0.05"); print("="*96)
print(f"{'amp DN':>7} {'corner x':>10} {'axis x':>9} {'selectivity':>12}")
for amp in (0.0, 2.0, 5.0, 10.0, 20.0, 40.0):
    def mk(a=amp):
        def g(im):
            yy,xx=np.mgrid[0:im.shape[0],0:im.shape[1]]
            k=a*((-1.0)**(xx+yy)); o=im.copy(); o[:,:,0]+=k; o[:,:,2]-=k; return o
        return g
    (p0,k0,a0),(p1,k1,a1),n=run("foam",0.05,plant=mk())
    print(f"{amp:7.1f} {k1/k0:10.3f} {a1/a0:9.3f} {(k1/k0)/(a1/a0):12.2f}")
print("  -> monotone and corner-selective: the instrument sees a maze. amp=0 row is the")
print("     UNPLANTED arm ratio, i.e. the real g1/g0.")

print(); print("="*96)
print("ABSOLUTE band power (is the 0.37 feature a PEAK in g1 or a DIP in g0?)")
print("="*96)
SUBJ=["foam","couch-fibers-cpl","lavendar-cpl","flower-bud-alone-cpl","coffee-bubbles"]
pred=np.array([(gather_mtf("catmull-rom",f)/gather_mtf("catmull-rom",2*f))**2 if 2*f<0.5 else np.nan for f in _ctr])
for s in SUBJ[:3]:
    (p0,_,_),(p1,_,_),n=run(s,0.05)
    print(f"\n  {s} ({n} tiles)   [high-passed; the box cancels exactly in the ratio]")
    print(f"    {'f':>8} {'g0 power':>12} {'g1 power':>12} {'ratio':>8} {'PRED':>8} {'excess/PRED':>12}")
    for i in range(NB):
        pr=f"{pred[i]:8.3f}" if not math.isnan(pred[i]) else "     n/a"
        ex=f"{(p1[i]/p0[i])/pred[i]:12.3f}" if not math.isnan(pred[i]) else "         n/a"
        print(f"    {_ctr[i]:8.4f} {p0[i]:12.4e} {p1[i]:12.4e} {p1[i]/p0[i]:8.3f}{pr}{ex}")

print(); print("="*96)
print("NO-HIGH-PASS: the low bands, where the restoration model predicts ~1.000")
print("   any excess here CANNOT be restoration -- the kernel has nothing to restore at DC")
print("="*96)
print(f"{'f':>8} {'PRED':>7}" + "".join(f"{s[:11]:>13}" for s in SUBJ))
raw={}
for s in SUBJ:
    (p0,_,_),(p1,_,_),n=run(s,0.05,use_hp=False); raw[s]=(p0,p1)
for i in range(8):
    print(f"{_ctr[i]:8.4f} {pred[i]:7.3f}" + "".join(f"{raw[s][1][i]/raw[s][0][i]:13.3f}" for s in SUBJ))
print()
print("CREATED-vs-RESTORED split over f < 0.25 (plane Nyquist), no-high-pass spectra:")
print(f"{'subject':24s} {'tot excess pwr':>15} {'restored':>10} {'created':>10} {'created %':>10}")
lim=[i for i in range(NB) if 2*_ctr[i]<0.5]
for s in SUBJ:
    p0,p1=raw[s]
    tot=sum(p1[i]-p0[i] for i in lim)
    rest=sum(p0[i]*(pred[i]-1.0) for i in lim)
    crea=tot-rest
    print(f"{s:24s} {tot:15.4e} {rest:10.3e} {crea:10.3e} {100*crea/tot:10.1f}")
