"""hsel.py -- separate NOISE incoherence from SELECTION incoherence.

WHY THIS EXISTS.  The orchestrator proposed f (half-stack disagreement) as the
discriminator between selection, alignment and depth dilution, to be applied by
three lanes.  My delivered f CANNOT do that job and I measured why: incoherence
rises monotonically as tile contrast FALLS (119MSDCF top-60 tiles 0.2334, bottom-60
0.8834).  That gradient is the signature of an independent-noise term, and on this
data it is larger than the effect being discriminated.  A lane reading raw f would
attribute a noise floor to selection.

THE SEPARATION.  Under the additive model with common scene power S and independent
per-half noise power Nz in a ring,

    gamma = S / (S + Nz)          f = Nz / (S + Nz)

so a pure-noise term drives f -> 0 as scene contrast S grows.  A SELECTION term is
different in kind: choosing a different frame per pixel in half A than half B
injects a difference that is PROPORTIONAL to scene content, alpha*S, giving

    f -> alpha / (1 + alpha)   as S -> infinity,  a NON-ZERO floor.

So the high-contrast limit of f is an upper bound on selection incoherence, and it
is assumption-light: I do not fit a functional form or extrapolate.  I stratify
tiles by contrast measured in a DISJOINT band (0.02-0.05 cyc/px) and report the
top-decile value directly.

COMMISSIONED IN BOTH DIRECTIONS, which is the whole point:
  NOISE plant       incoherence with NO contrast proportionality.  Must move the
                    low-contrast deciles and must NOT move the top decile.
  STRUCTURED plant  a graded fraction q of the real, scene-structured A-B
                    difference.  Must move the top decile MONOTONICALLY in q.
  q=0 arm           the improvement end: must read ~0, proving the bound is free to
                    exonerate and is not bounded below by construction.

DISTRIBUTIONS, NOT MEANS.  A sibling lane lost a defect because its self-test
asserted only the mean of a field whose defect was at the borders.  Every number
here is reported with p10/median/p90 and separately for border and interior tiles.
"""
import os, sys, numpy as np, softcheck as S, hcoh as HC

T=HC.T; P=HC.PRIMARY; E=HC.E; NB=HC.NB
ROOT=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh"

def all_tiles(shape):
    H,W=shape[:2]
    ys=list(range(0,H-T,T)); xs=list(range(0,W-T,T))
    oy=[];ox=[]
    for y in ys:
        for x in xs: oy.append(y); ox.append(x)
    return np.array(oy),np.array(ox)

def contrast(img,oy,ox):
    """Scene contrast proxy in 0.02-0.05 cyc/px -- DISJOINT from every reported
    band, so the stratifying variable cannot be the thing being measured."""
    out=np.empty(len(oy))
    for k in range(len(oy)):
        t=img[oy[k]:oy[k]+T, ox[k]:ox[k]+T].astype(np.float32)
        Ft=HC._ft(t); out[k]=(np.abs(Ft)**2)[HC.EST_MASK>0].mean()
    return out

def stratified(A,B,oy,ox,cw,nq=10):
    f,_=HC.pair_stats(A,B,oy,ox,oy,ox)
    order=np.argsort(cw)
    qs=np.array_split(order,nq)
    rows=[]
    for qi,idx in enumerate(qs):
        rows.append(dict(decile=qi, n=len(idx),
                         contrast=float(np.median(cw[idx])),
                         p10=float(np.percentile(f[idx,P],10)),
                         med=float(np.median(f[idx,P])),
                         p90=float(np.percentile(f[idx,P],90)),
                         perband=[float(np.median(f[idx,b])) for b in range(NB)]))
    return f,rows

def load_pair(subj,n):
    d=os.path.join(ROOT,subj)
    A=S.load_luma(os.path.join(d,"N%03d-A.tiff"%n),"srgb")
    B=S.load_luma(os.path.join(d,"N%03d-B.tiff"%n),"srgb")
    return A,B

def align(A,B,oy,ox):
    sy,sx=HC.align_int(A,B); best=None
    for dy,dx in [(0,0),(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,-1)]:
        yy=oy+sy+dy; xx=ox+sx+dx
        m=(yy>=0)&(yy+T<=A.shape[0])&(xx>=0)&(xx+T<=A.shape[1])
        if m.sum()<50: continue
        f,_=HC.pair_stats(A,B,oy[m],ox[m],yy[m],xx[m])
        v=float(np.median(f[:,P]))
        if best is None or v<best[0]: best=(v,int(sy+dy),int(sx+dx),m)
    return best[1],best[2],best[3]
