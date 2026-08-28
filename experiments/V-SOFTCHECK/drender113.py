"""Matched-range depth arms for 113MSDCF, the subject my standing 0.114 came from.

63 frames, so N=32 vs N=63 is the same doubling at matched range that A1' tests on
bee.  Both arms span the FULL range by construction, so no focus mask is needed and
the comparison has no range confound at all.

Re-rendered rather than inherited: ncurve's logs for this subject were written by a
different run and one of the bee logs in that tree is zero bytes, so no arm there is
usable as a gauge without its own exposure record.
"""
import os, sys, numpy as np, drender as D
SUBJ="113MSDCF"; EXPO="2.33"
if __name__=="__main__":
    h=D.pin(); print("pin sha256 %s...  SHIP-V4 ok"%h[:16])
    src,allf=D.frames(SUBJ); NF=len(allf)
    print("%s: %d frames, exposure %s on every arm"%(SUBJ,NF,EXPO))
    a=sorted(set(np.linspace(0,NF-1,32).round().astype(int).tolist()))
    assert a[0]==0 and a[-1]==NF-1, "range not preserved"
    D.merge_arm(SUBJ,"N032",a,EXPO)
    D.merge_arm(SUBJ,"N063",list(range(NF)),EXPO)
    print("done")
