"""hwarp.py -- can the contrast-proportional signal on bee be residual MISREGISTRATION?

hmixrun.py estimates the selection share at 0.85 on bee-1-cpl and 0.00 on 119MSDCF.
That statistic separates NOISE from CONTRAST-PROPORTIONAL incoherence.  It does NOT
separate selection from alignment, because a registration error is also proportional
to scene content.  Both remaining candidates therefore sit inside the 0.85.

bee is the worst possible subject for that ambiguity and I already measured why: its
two arms are related by a SPATIALLY VARYING displacement rather than a translation
(two independently 4/4-commissioned correlation windows disagreed, +0,+7 against
+4,-2), and held-out registration error reached 17-27 px.  pair_stats removes a
per-tile CONSTANT shift exactly, as a phase ramp.  What it cannot remove is warp
WITHIN a tile, and that residue is contrast-proportional.

So: measure the per-tile shift field the instrument is already estimating.  A large,
spatially structured field means local misregistration is live on this subject and
the 0.85 cannot be attributed to frame choice.  A small, unstructured field weakens
that alternative.  Also reports f for BORDER vs INTERIOR tiles, because a sibling
lane lost a defect to a self-test that asserted only the mean of a field whose
defect was at the borders, and every number I ship is a median over tiles.
"""
import os, sys, numpy as np, softcheck as S, hcoh as HC, hsel as HS

T=HC.T; P=HC.PRIMARY

def shifts(A,B,oy,ox):
    sy=np.empty(len(oy)); sx=np.empty(len(oy)); f=np.empty(len(oy))
    for k in range(len(oy)):
        a=A[oy[k]:oy[k]+T, ox[k]:ox[k]+T].astype(np.float32)
        b=B[oy[k]:oy[k]+T, ox[k]:ox[k]+T].astype(np.float32)
        FA=HC._ft(a); FB=HC._ft(b); FBc,dy,dx=HC._subpix(FA,FB)
        sy[k]=dy; sx[k]=dx
        m=HC.MASK[P]
        X=(FA*np.conj(FBc))[m].sum()
        f[k]=1.0-float(np.abs(X)/np.sqrt((np.abs(FA)**2)[m].sum()*(np.abs(FBc)**2)[m].sum()))
    return sy,sx,f

for subj,n in (("119MSDCF",32),("bee-1-cpl",298)):
    A,B=HS.load_pair(subj,n)
    oy,ox=HS.all_tiles(A.shape); sy0,sx0,m=HS.align(A,B,oy,ox)
    oy,ox=oy[m],ox[m]
    yy=oy+sy0; xx=ox+sx0
    sy,sx,f=shifts(A,B,oy,ox) if (sy0==0 and sx0==0) else shifts(A,B,oy,ox)
    r=np.hypot(sy,sx)
    print("\n%s N=%d  global shift (%d,%d)  tiles %d"%(subj,n,sy0,sx0,len(oy)))
    print("  PER-TILE residual shift magnitude (px), after the global integer shift:")
    print("    median %.3f   p90 %.3f   p99 %.3f   max %.3f   std(sy) %.3f  std(sx) %.3f"%(
        np.median(r),np.percentile(r,90),np.percentile(r,99),r.max(),sy.std(),sx.std()))
    # spatial structure: is the field smooth (real warp) or scattered (fit noise)?
    H,W=A.shape[:2]; gy=(oy//T).astype(int); gx=(ox//T).astype(int)
    nb=[]
    for k in range(len(oy)):
        d=(np.abs(gy-gy[k])<=1)&(np.abs(gx-gx[k])<=1); d[k]=False
        if d.sum(): nb.append(np.hypot(sy[k]-sy[d].mean(), sx[k]-sx[d].mean()))
    nb=np.array(nb)
    print("  spatial structure: median |tile shift - mean of its 8 neighbours| = %.3f px"%np.median(nb))
    print("     (small vs the field's own spread %.3f means a SMOOTH field = real warp;"%r.std())
    print("      comparable means a scattered field = fitting noise)")
    bord=(oy<T)|(ox<T)|(oy+2*T>H)|(ox+2*T>W)
    print("  f at 0.20-0.25   border tiles %3d: %.4f   |   interior %3d: %.4f   (median over all %.4f)"%(
        bord.sum(),np.median(f[bord]),(~bord).sum(),np.median(f[~bord]),np.median(f)))
    print("  residual shift    border %.3f px  |  interior %.3f px"%(np.median(r[bord]),np.median(r[~bord])))
    del A,B
