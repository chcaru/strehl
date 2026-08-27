"""Commission the shipping-grid ring instrument BEFORE trusting shipband.py.

Four arm types, per band, on the full-resolution shipping grid:
  NULL      master untouched, reference untouched  -> must NOT move
  DEGRADE   master blurred                         -> ratio must FALL
  IMPROVE   master unsharp-masked                  -> ratio must RISE
  REFPERT   every reference frame blurred          -> ratio must RISE

The IMPROVE arm is the one this project has been burned by omitting: a
statistic whose sign is bounded below by zero passes every degrade-only
commissioning trivially while being unable to charge for the defect it exists
to catch.  The REFPERT arm exists because an inert denominator certifies half
an instrument.
"""
import os, sys, numpy as np, softcheck as S
from scipy import ndimage
T=256; subj="119MSDCF"
EDGES=np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--shipring.npz"))
Fr,oy,ox,N=z["Fr"],z["oy"],z["ox"],int(z["N"])
zc=np.load(os.path.join(S.ROOT,"cache",f"{subj}--srgb--T256.npz")); coefs=zc["coefs"]
d=os.path.join(S.ROOT,"srgb",subj)
def rings(img,yy,xx):
    H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)
M=S.load_luma(os.path.join(d,"master.tiff"),"srgb")
def ratio(Mr,Fx):
    return np.array([np.median(Mr[:,b]/np.maximum(Fx[:,:,b].max(0),1e-30)) for b in range(len(masks))])
base=ratio(rings(M,oy,ox),Fr)
arms={"NULL     ":ratio(rings(M.copy(),oy,ox),Fr),
      "DEGRADE  ":ratio(rings(ndimage.gaussian_filter(M,0.8,mode="reflect"),oy,ox),Fr),
      "IMPROVE  ":ratio(rings(M+0.7*(M-ndimage.gaussian_filter(M,1.2,mode="reflect")),oy,ox),Fr)}
Fb=np.zeros_like(Fr)
for k in range(N):
    F=S.load_luma(os.path.join(d,f"f{k:03d}.tiff"),"srgb")
    dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
    Fb[k]=rings(ndimage.gaussian_filter(F,0.8,mode="reflect"),
                np.round(oy+dy).astype(int),np.round(ox+dx).astype(int)); del F
arms["REFPERT  "]=ratio(rings(M,oy,ox),Fb)
print(f"\nCOMMISSIONING, shipping grid, {subj}   (band 0.20-0.25 cyc/px starred)\n")
hdr="  band cyc/px  " + "".join(f"{k}" for k in ["baseline ","NULL     ","DEGRADE  ","IMPROVE  ","REFPERT  "])
print(hdr)
for b in range(len(masks)):
    star="*" if abs(EDGES[b]-0.20)<1e-9 else " "
    row=f" {star}{EDGES[b]:.2f}-{EDGES[b+1]:.2f}  {base[b]:8.4f} "
    for k in ["NULL     ","DEGRADE  ","IMPROVE  ","REFPERT  "]:
        row+=f"{arms[k][b]:8.4f} "
    print(row)
print("\nVERDICT PER ARM (band 0.20-0.25 cyc/px, the only promotable band):")
b=3
print(f"  NULL     {arms['NULL     '][b]:.6f} vs baseline {base[b]:.6f}  "
      f"delta {abs(arms['NULL     '][b]-base[b]):.2e}  {'PASS (inert)' if abs(arms['NULL     '][b]-base[b])<1e-9 else 'FAIL - moved'}")
for k,want in [("DEGRADE  ","fall"),("IMPROVE  ","rise"),("REFPERT  ","rise")]:
    got="fall" if arms[k][b]<base[b] else "rise"
    print(f"  {k}{arms[k][b]:.4f} vs {base[b]:.4f}  want {want}, got {got}  "
          f"{'PASS' if got==want else 'FAIL'}  ({100*(arms[k][b]/base[b]-1):+.1f}%)")
