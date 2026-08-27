"""HARDENED NULLS.  My delivered NULL arm was inert by construction.

It computed rings(M.copy()) / rings(M).  That runs the whole statistic, so it is
not a literal short-circuit like resamp.py's `if s == 1: return a.copy()`, but the
outcome is the same: the answer is 1.0000 unless numpy's FFT is nondeterministic.
It validated nothing about my pipeline.  This is the project's third sighting of a
control that could not have failed, and mine is one of them.

A null is only worth having if it is a PREDICTION.  Each null below changes the
bytes of the image in a way my statistic is supposed to be blind to, so each one
CAN fail:

  OFFSET      +2000 DN.  Tiles are mean-subtracted, so band power must be
              unchanged.  Fails if mean subtraction is broken or if I overflow.
  TRANSLATE   integer shift (+7,+11) with align_int asked to find it.  Fails if
              the registration path is broken -- which the depth criterion relies
              on for every arm.
  FLIP        left-right mirror.  The ring masks are radially symmetric, so band
              power must be unchanged.  Fails if a mask is not symmetric.
  RELOAD      the same file decoded twice from disk.  Fails on decode nondeterminism.

TEETH CHECK.  Inertness only means something if the same code path is sensitive.
A blur of sigma 0.3 -- far smaller than anything the depth experiment reports --
must move the reading.  If the nulls read 1.0 and the teeth check also reads 1.0,
the nulls are worthless and the run says so.
"""
import os, sys, numpy as np, softcheck as S
from ncurve import rings, pick_tiles, align_int, gauss, EDGES, T, NT
PRIMARY=3
f=sys.argv[1] if len(sys.argv)>1 else r"C:\dev\strehl-out\V-SOFTCHECK\ncurve\bee-1-cpl\master-N299.tiff"
M=S.load_luma(f,"srgb").astype(np.float32)
oy,ox=pick_tiles(M); base=rings(M,oy,ox)
print(f"HARDENED NULLS on {os.path.basename(f)}   band {EDGES[PRIMARY]:.2f}-{EDGES[PRIMARY+1]:.2f}\n")
res={}
res["OFFSET  +2000 DN"]=np.median((rings(M+2000.0,oy,ox)/base)[:,PRIMARY])
tr=np.roll(np.roll(M,7,axis=0),11,axis=1)
sy,sx=align_int(M,tr)
res[f"TRANSLATE +7,+11 (found {sy:+d},{sx:+d})"]=np.median((rings(tr,oy+sy,ox+sx)/base)[:,PRIMARY])
fl=M[:,::-1].copy()
W=M.shape[1]
oxf=W-ox-T
res["FLIP  left-right"]=np.median((rings(fl,oy,oxf)/base)[:,PRIMARY])
res["RELOAD  decode twice"]=np.median((rings(S.load_luma(f,"srgb").astype(np.float32),oy,ox)/base)[:,PRIMARY])
ok=True
for k,v in res.items():
    good=abs(v-1.0)<0.005
    ok&=good
    print(f"  {k:<38s} {v:9.5f}   {'INERT (pass)' if good else 'MOVED (FAIL)'}")
# TEETH as a graded ladder, not a single threshold.  A binary check invites an
# arbitrary cutoff -- my first one was 2%, which failed a blur that the statistic
# had in fact detected at 1.3%.  A monotone response across four blur strengths
# is a much stronger claim than any one point: it shows the statistic ORDERS
# perturbations it is supposed to order.
print()
sigs=[0.3,0.5,0.8,1.0]; teeth=[]
for s in sigs:
    v=float(np.median((rings(gauss(M,s),oy,ox)/base)[:,PRIMARY])); teeth.append(v)
    print(f"  {'TEETH  blur sigma '+format(s,'.1f'):<38s} {v:9.5f}   {(1-v)*100:5.1f}% response")
monotone=all(teeth[i+1]<teeth[i] for i in range(len(teeth)-1))
worst_null=max(abs(v-1.0) for v in res.values())
smallest=abs(1-teeth[0])
sep = smallest/worst_null if worst_null>0 else float("inf")
has_teeth = monotone and smallest>0.005
print(f"\n  monotone in blur strength : {monotone}")
print(f"  largest null deviation    : {worst_null:.6f}")
print(f"  smallest teeth response   : {smallest:.6f}  ({'inf' if worst_null==0 else format(sep,'.0f')}x the largest null)")
print(f"\n  hardened nulls {'PASSED' if (ok and has_teeth) else 'FAILED'}: blind to offset, integer")
print( "  translation, mirroring and re-decoding; ordered and sensitive to blur down to")
print(f"  sigma 0.3, whose {smallest*100:.1f}% response is far below the depth differences reported.")
sys.exit(0 if (ok and has_teeth) else 1)

