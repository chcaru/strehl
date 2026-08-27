"""Same instrument, gate-0 renders (elected frame, no merge averaging)."""
from __future__ import annotations
import os, sys, math
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma import hp
from mtfsim2 import gather_mtf
OUT = r"C:\dev\strehl-out\V-GATHER"
T, NB = 128, 24
_win=np.hanning(T)[:,None]*np.hanning(T)[None,:]
_fy=np.fft.fftshift(np.fft.fftfreq(T))[:,None]; _fx=np.fft.fftshift(np.fft.fftfreq(T))[None,:]
_rad=np.sqrt(_fx**2+_fy**2); _edges=np.linspace(0,0.5,NB+1)
_masks=[(_rad>=_edges[i])&(_rad<_edges[i+1]) for i in range(NB)]
_ctr=0.5*(_edges[:-1]+_edges[1:])
def load(s,a,tag): return tifffile.imread(os.path.join(OUT,f"{s}-{tag}-g{a}.tiff"))[:,:,:3].astype(np.float64)
def chroma(im): return im[:,:,0]-im[:,:,2]
def luma(im): return 0.2126*im[:,:,0]+0.7152*im[:,:,1]+0.0722*im[:,:,2]
def spec(img,idx):
    acc=np.zeros(NB)
    for ty,tx in idx:
        t=img[ty*T:(ty+1)*T,tx*T:(tx+1)*T]
        P=np.abs(np.fft.fftshift(np.fft.fft2((t-t.mean())*_win)))**2
        for i in range(NB): acc[i]+=P[_masks[i]].mean()
    return acc/len(idx)
def run(s,tag,q=0.05):
    i0,i1=load(s,"0",tag),load(s,"1",tag)
    h=(min(i0.shape[0],i1.shape[0])//T)*T; w=(min(i0.shape[1],i1.shape[1])//T)*T
    st=((luma(i0)[:h,:w]+luma(i1)[:h,:w])/2).reshape(h//T,T,w//T,T).std(axis=(1,3))
    idx=np.argwhere(st<=np.quantile(st,q))
    a=spec(chroma(i0)[:h,:w],idx); b=spec(chroma(i1)[:h,:w],idx)
    la=spec(luma(i0)[:h,:w],idx); lb=spec(luma(i1)[:h,:w],idx)
    del i0,i1; return a,b,la,lb,len(idx)
pred=np.array([(gather_mtf("catmull-rom",f)/gather_mtf("catmull-rom",2*f))**2 if 2*f<0.5 else np.nan for f in _ctr])
print("CHROMA (R-B) band-power ratio g1/g0 -- MERGE (pyramid, 20 fr) vs GATE-0 (elected frame, no merge)")
print(f"{'f':>8} {'PRED':>7} | " + " | ".join(f"{s[:9]:>9} merge  gate0" for s in ("foam","couch-fib")))
res={}
for s in ("foam","couch-fibers-cpl"):
    res[s]={"merge":run(s,"q"),"gate0":run(s,"gate0")}
    print(f"  {s}: merge {res[s]['merge'][4]} tiles, gate0 {res[s]['gate0'][4]} tiles", flush=True)
print()
print(f"{'f':>8} {'PRED':>7}" + "".join(f"{s[:8]+' mrg':>13}{s[:8]+' g0':>13}" for s in ("foam","couch")))
for i in range(NB):
    pp=f"{pred[i]:7.3f}" if not math.isnan(pred[i]) else "    n/a"
    row=f"{_ctr[i]:8.4f} {pp}"
    for s in ("foam","couch-fibers-cpl"):
        m=res[s]["merge"]; g=res[s]["gate0"]
        row+=f"{m[1][i]/m[0][i]:13.3f}{g[1][i]/g[0][i]:13.3f}"
    print(row)
print()
print("CREATED-vs-RESTORED over f < 0.25, both render modes:")
print(f"{'subject':20s} {'mode':>7} {'tot excess':>12} {'restored':>11} {'created':>11} {'created %':>10}")
lim=[i for i in range(NB) if 2*_ctr[i]<0.5]
for s in ("foam","couch-fibers-cpl"):
    for mode in ("merge","gate0"):
        p0,p1=res[s][mode][0],res[s][mode][1]
        tot=sum(p1[i]-p0[i] for i in lim); rest=sum(p0[i]*(pred[i]-1) for i in lim)
        print(f"{s:20s} {mode:>7} {tot:12.4e} {rest:11.3e} {tot-rest:11.3e} {100*(tot-rest)/tot:10.1f}")
print()
print("LUMA band-power ratio, same tiles (for contrast):")
print(f"{'f':>8} {'PRED':>7}" + "".join(f"{s[:8]+' mrg':>13}{s[:8]+' g0':>13}" for s in ("foam","couch")))
for i in range(0,NB,2):
    pp=f"{pred[i]:7.3f}" if not math.isnan(pred[i]) else "    n/a"
    row=f"{_ctr[i]:8.4f} {pp}"
    for s in ("foam","couch-fibers-cpl"):
        m=res[s]["merge"]; g=res[s]["gate0"]
        row+=f"{m[3][i]/m[2][i]:13.3f}{g[3][i]/g[2][i]:13.3f}"
    print(row)
