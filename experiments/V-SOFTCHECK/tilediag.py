import os, numpy as np, softcheck as S, hcoh as HC
for subj,n in (("119MSDCF",32),("bee-1-cpl",298)):
    d=os.path.join(r"C:\dev\strehl-out\V-SOFTCHECK\hcoh",subj)
    A=S.load_luma(os.path.join(d,"N%03d-A.tiff"%n),"srgb"); B=S.load_luma(os.path.join(d,"N%03d-B.tiff"%n),"srgb")
    oy,ox=HC.pick_tiles(A); P=HC.PRIMARY
    f,_=HC.pair_stats(A,B,oy,ox,oy,ox)
    v=f[:,P]
    print("%s N=%d  (no global align, identical code path, f at 0.20-0.25)"%(subj,n))
    print("   tiles   0:120  median %.4f      <- what commission() reports as BASE"%np.median(v[:120]))
    print("   tiles   0:300  median %.4f"%np.median(v[:300]))
    print("   tiles 120:300  median %.4f"%np.median(v[120:300]))
    print("   rank vs f: tiles are ordered by DESCENDING 0.02-0.05 energy")
    for lo,hi in ((0,60),(60,120),(120,180),(180,240),(240,300)):
        print("      tiles %3d-%3d  median f %.4f"%(lo,hi,np.median(v[lo:hi])))
    del A,B
