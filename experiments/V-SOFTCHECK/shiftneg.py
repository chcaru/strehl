import os, numpy as np, softcheck as S, hcoh as HC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\bee-1-cpl"
A=S.load_luma(os.path.join(d,"N298-A.tiff"),"srgb"); B=S.load_luma(os.path.join(d,"N298-B.tiff"),"srgb")
oy,ox=HC.pick_tiles(A); y,x=oy[0:120],ox[0:120]; P=HC.PRIMARY; T=256
k=(y>=7)&(x>=11); yk,xk=y[k],x[k]
Ar=np.roll(np.roll(A,7,0),11,1); Br=np.roll(np.roll(B,7,0),11,1)
# (i) is the exact 0 a PREDICTION?  the tiles must be bit-identical arrays.
same=all(np.array_equal(A[yy:yy+T,xx:xx+T], Ar[yy+7:yy+7+T,xx+11:xx+11+T]) for yy,xx in zip(yk[:20],xk[:20]))
print("(i) shifted tiles bit-identical to originals (20 sampled): %s"%same)
print("    -> f MUST be identical.  exact 0 is arithmetic, not a short-circuit.")
base,_=HC.pair_stats(A,B,yk,xk,yk,xk); b=float(np.median(base[:,P]))
# (ii) CAN this arm fail?  offset the tile origin by ONE pixel against the roll.
for dy,dx,lab in ((7,10,"x off by 1"),(6,11,"y off by 1"),(7,11,"correct")):
    f,_=HC.pair_stats(Ar,Br,yk+dy,xk+dx,yk+dy,xk+dx); v=float(np.median(f[:,P]))
    print("(ii) roll(7,11), tiles offset (%d,%2d) %-11s f=%.6f  dev=%.3e"%(dy,dx,lab,v,abs(v-b)))
