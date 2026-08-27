"""Corrected: avoid the degenerate Nyquist DFT bin (build-resamp-mtf.rs uses
0.48 for exactly this reason). f_site = 2*f_out must never equal 0.5."""
from __future__ import annotations
import math
import numpy as np
PHASE_SAMPLES = 64
def tap_cr(t):
    a=abs(t)
    return 1.5*a**3-2.5*a**2+1.0 if a<1 else (-0.5*a**3+2.5*a**2-4*a+2 if a<2 else 0.0)
def tap_nearest(t): return 1.0 if abs(t)<0.5 else 0.0
def tap_l3(t):
    a=abs(t)
    if a>=3: return 0.0
    if a<1e-12: return 1.0
    pt=math.pi*t; return (math.sin(pt)/pt)*(math.sin(pt/3)/(pt/3))
KERN={"nearest":(tap_nearest,1),"catmull-rom":(tap_cr,2),"lanczos3":(tap_l3,3)}
def gather_mtf(name,f):
    tap,sup=KERN[name]; acc=0.0
    for p in range(PHASE_SAMPLES):
        phi=(p+0.5)/PHASE_SAMPLES
        w=[(n-phi,tap(n-phi)) for n in range(-sup+1,sup+1)]
        s=sum(v for _,v in w)
        if abs(s)<1e-12: continue
        re=sum(v/s*math.cos(2*math.pi*f*d) for d,v in w)
        im=sum(v/s*math.sin(2*math.pi*f*d) for d,v in w)
        acc+=math.hypot(re,im)
    return acc/PHASE_SAMPLES
def sample1d(sig,x,name):
    tap,sup=KERN[name]; i=math.floor(x); phi=x-i; num=den=0.0
    for n in range(-sup+1,sup+1):
        w=tap(n-phi); j=min(max(i+n,0),len(sig)-1); num+=w*sig[j]; den+=w
    return num/den if abs(den)>1e-12 else 0.0
N,MARGIN=400,16
def run(f_out,kern,phases=PHASE_SAMPLES):
    L=N+2*MARGIN; full=np.cos(2*math.pi*f_out*np.arange(L*4,dtype=float)); out={}
    for arm,pitch in (("OLD plane (pitch 2)",2),("NEW fullres (pitch 1)",1)):
        src=full[::pitch]; ks=np.arange(N)+MARGIN
        f_site=2*f_out
        amps,rmss,corrs=[],[],[]
        for p in range(phases):
            sh=(p+0.5)/phases
            got=np.array([sample1d(src,(2*k+sh)/pitch,kern) for k in ks])
            truth=np.cos(2*math.pi*f_out*(2*ks+sh))
            th=2*math.pi*f_site*np.arange(N)
            amps.append(2*abs((got*np.exp(-1j*th)).sum())/N)
            rmss.append(float(np.sqrt(((got-truth)**2).mean())))
            g,t=got-got.mean(),truth-truth.mean()
            corrs.append(float((g*t).sum()/math.sqrt((g*g).sum()*(t*t).sum())))
        out[arm]=dict(amp=float(np.mean(amps)),lo=float(np.min(amps)),hi=float(np.max(amps)),
                      rms=float(np.mean(rmss)),corr=float(np.mean(corrs)),
                      corr_lo=float(np.min(corrs)))
    return out
print("=== HEADLINE: f_out = 0.24 cyc/full-res px (0.48 cyc/site -- non-degenerate) ===")
r=run(0.24,"catmull-rom"); o,n=r["OLD plane (pitch 2)"],r["NEW fullres (pitch 1)"]
pred_o,pred_n=gather_mtf("catmull-rom",0.48),gather_mtf("catmull-rom",0.24)
print(f"  5.1 model : OLD {pred_o:.4f}  NEW {pred_n:.4f}  ratio {pred_n/pred_o:.4f}x")
print(f"  MEASURED  : OLD {o['amp']:.4f}  NEW {n['amp']:.4f}  ratio {n['amp']/o['amp']:.4f}x")
print(f"  per-phase amplitude spread  OLD [{o['lo']:.4f}, {o['hi']:.4f}]  "
      f"NEW [{n['lo']:.4f}, {n['hi']:.4f}]")
print(f"  fidelity  : rms {o['rms']:.4f} -> {n['rms']:.4f}   corr {o['corr']:.4f} -> {n['corr']:.4f}")
print("\n=== the number 5.1 actually quotes, at the OLD path's exact Nyquist ===")
print("  gather_mtf(CR, 0.50) = 0.6251 is a PHASE AVERAGE. Per sub-pixel phase:")
L=N+2*MARGIN; full=np.cos(2*math.pi*0.25*np.arange(L*4,dtype=float)); src=full[::2]
ks=np.arange(N)+MARGIN; amps=[]
for p in range(PHASE_SAMPLES):
    sh=(p+0.5)/PHASE_SAMPLES
    got=np.array([sample1d(src,(2*k+sh)/2,"catmull-rom") for k in ks])
    amps.append(float(np.abs((got*np.exp(-1j*2*math.pi*0.5*np.arange(N))).sum())/N))
print(f"  amplitude at 0.25 cyc/full-res px, OLD arm, over 64 phases:")
print(f"    min {min(amps):.4f}   median {np.median(amps):.4f}   max {max(amps):.4f}   "
      f"mean {np.mean(amps):.4f}   ratio max/min = {max(amps)/max(min(amps),1e-9):.1f}x")
print("\n=== SWEEP: amplitude (what gather_mtf models) vs correlation (fidelity) ===")
print(f"{'f_out':>6} {'OLD amp':>8} {'NEW amp':>8} {'amp ratio':>10} {'5.1 pred':>9} "
      f"{'OLD corr':>9} {'NEW corr':>9}")
for f_out in (0.04,0.08,0.12,0.16,0.20,0.24,0.26,0.30,0.34,0.38,0.42,0.46):
    r=run(f_out,"catmull-rom"); o,n=r["OLD plane (pitch 2)"],r["NEW fullres (pitch 1)"]
    fp=2*f_out
    pred=(gather_mtf("catmull-rom",f_out)/gather_mtf("catmull-rom",fp)) if fp<0.5 else float("nan")
    print(f"{f_out:6.2f} {o['amp']:8.4f} {n['amp']:8.4f} {n['amp']/o['amp']:10.3f} {pred:9.3f} "
          f"{o['corr']:9.4f} {n['corr']:9.4f}")
print("\n=== POTENCY / BLIND SPOT: nearest, the worst kernel in the enum ===")
for f_out in (0.12,0.24):
    r=run(f_out,"nearest")
    print(f"  f_out={f_out}: OLD amp {r['OLD plane (pitch 2)']['amp']:.4f} "
          f"rms {r['OLD plane (pitch 2)']['rms']:.4f} | model gather_mtf(nearest,{2*f_out:.2f}) "
          f"= {gather_mtf('nearest',2*f_out):.4f}")
