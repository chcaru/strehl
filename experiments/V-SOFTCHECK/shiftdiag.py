import os, numpy as np, softcheck as S, hcoh as HC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\bee-1-cpl"
A=S.load_luma(os.path.join(d,"N298-A.tiff"),"srgb"); B=S.load_luma(os.path.join(d,"N298-B.tiff"),"srgb")
H,W=A.shape[:2]; T=HC.T if hasattr(HC,"T") else 256
oy,ox=HC.pick_tiles(A); y,x=oy[0:120],ox[0:120]
P=HC.PRIMARY
base_all,_=HC.pair_stats(A,B,y,x,y,x); b_all=float(np.median(base_all[:,P]))
k=(y>=7)&(x>=11)
print("image %dx%d  T=%d  tiles=%d  kept by k: %d  dropped: %d"%(H,W,T,len(y),k.sum(),(~k).sum()))
print("max shifted tile extent: y %d/%d   x %d/%d"%((y[k]+7).max()+T,H,(x[k]+11).max()+T,W))
b_k=float(np.median(base_all[k,P]))
Ar=np.roll(np.roll(A,7,0),11,1); Br=np.roll(np.roll(B,7,0),11,1)
fS,_=HC.pair_stats(Ar,Br,y[k]+7,x[k]+11,y[k]+7,x[k]+11); s_k=float(np.median(fS[:,P]))
print()
print("  BASE  over ALL 120 tiles          %.6f"%b_all)
print("  BASE  over the SAME tiles as arm  %.6f"%b_k)
print("  NULL_SHIFT_BOTH (same tiles)      %.6f"%s_k)
print()
print("  dev vs ALL-tile BASE   %.3e   <5e-3: %s"%(abs(s_k-b_all),abs(s_k-b_all)<5e-3))
print("  dev vs SAME-tile BASE  %.3e   <5e-3: %s"%(abs(s_k-b_k),abs(s_k-b_k)<5e-3))
per=np.abs(fS[:,P]-base_all[k,P])
print("  per-tile |shifted-base|: median %.3e  p90 %.3e  max %.3e"%(np.median(per),np.percentile(per,90),per.max()))
