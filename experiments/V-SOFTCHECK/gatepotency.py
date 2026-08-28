import os, numpy as np, softcheck as S, hcoh as HC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\bee-1-cpl"
A=S.load_luma(os.path.join(d,"N298-A.tiff"),"srgb"); B=S.load_luma(os.path.join(d,"N298-B.tiff"),"srgb")
oy,ox=HC.pick_tiles(A); y,x=oy[0:120],ox[0:120]; P=HC.PRIMARY
k=(y>=7)&(x>=11); yk,xk=y[k],x[k]
base,_=HC.pair_stats(A,B,yk,xk,yk,xk); basis=float(np.median(base[:,P]))
Ar=np.roll(np.roll(A,7,0),11,1); Br=np.roll(np.roll(B,7,0),11,1)
print("gate: |NULL_SHIFT_BOTH - basis| < 5e-3     basis(same tiles) = %.6f"%basis)
for dx in (0,1,2,4,8,16):
    f,_=HC.pair_stats(Ar,Br,yk+7,xk+11+dx,yk+7,xk+11+dx); v=float(np.median(f[:,P]))
    dev=abs(v-basis)
    print("  origin x mismatched by %2d px  f=%.6f  dev=%.3e  gate %s"%(dx,v,dev,"PASS" if dev<5e-3 else "FIRES"))
