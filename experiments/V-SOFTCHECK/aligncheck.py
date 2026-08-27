"""Per-subject commissioning of align_int, plus the sensitivity of R to a bad shift.
An aligner that works on one subject is not an aligner that works."""
import numpy as np, softcheck as S
from ncurve import rings, pick_tiles, align_int, T
ROOT=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve"
SUBJ=[("bee-1-cpl",299,149),("113MSDCF",63,31),("flower-bud-alone-cpl",205,102)]
PLANT=[(7,11),(-5,3),(13,-9),(0,0)]
for subj,nf,nh in SUBJ:
    F=S.load_luma(fr"{ROOT}\{subj}\master-N{nf:03d}.tiff","srgb")
    print(f"\n{subj}  N={nf}")
    print("  aligner commissioning (planted roll -> recovered additive offset):")
    nfail=0
    for py,px in PLANT:
        Mt=np.roll(np.roll(F,py,0),px,1); ry,rx=align_int(F,Mt)
        ok = (ry,rx)==(py,px)
        nfail += 0 if ok else 1
        print(f"    planted {py:+4d},{px:+4d}   recovered {ry:+4d},{rx:+4d}   {'ok' if ok else 'FAIL'}")
    print(f"    {len(PLANT)-nfail}/{len(PLANT)} recovered")
    Hh=S.load_luma(fr"{ROOT}\{subj}\master-N{nh:03d}.tiff","srgb")
    oy,ox=pick_tiles(F); base=rings(F,oy,ox)
    sy,sx=align_int(F,Hh)
    print(f"  measured arm shift {sy:+d},{sx:+d}")
    print("  sensitivity of R(0.20-0.25) to a DELIBERATELY WRONG shift:")
    for dy,dx in [(0,0),(1,0),(0,1),(3,3),(7,0),(0,11),(11,11)]:
        y=oy+sy+dy; x=ox+sx+dx
        k=(y>=0)&(y+T<=F.shape[0])&(x>=0)&(x+T<=F.shape[1])
        R=float(np.median((rings(Hh,y[k],x[k])/np.maximum(base[k],1e-30))[:,3]))
        print(f"    offset error {dy:+3d},{dx:+3d}   R = {R:.4f}"
              + ("   <-- correct shift" if (dy,dx)==(0,0) else ""))
    del F,Hh
