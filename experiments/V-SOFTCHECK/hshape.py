"""hshape.py -- discriminate the SOURCE of half-stack incoherence by its contrast profile.

My first separator (hselrun.py) FAILED ITS OWN COMMISSIONING and is retained as the
artifact.  Its premise was that noise incoherence dies as tile contrast rises while
selection incoherence does not, so the high-contrast decile would bound selection.
The NOISE_rejected_at_top gate refuted that directly: white noise at 0.05 sigma
reads 0.5785 in the TOP decile.  There is no noise-immune decile, so there is no
bound of that kind and I withdrew it.

WHAT WORKS INSTEAD.  Amplitude is the confound, not shape.  Matched at the
LOW-contrast end -- where every mechanism is noise-dominated and they cannot be told
apart -- the mechanisms differ in how fast f falls as contrast RISES:

  additive noise      f = Nz/(S+Nz), Nz independent of S  ->  falls steeply
  frame-choice        the difference is a DEFOCUS difference at real detail, so it
                      is proportional to scene content   ->  falls slowly, or not at all

So: tune each plant until it matches the real pair in the bottom decile, then read
the TOP decile.  Whichever plant the real data resembles there names the mechanism.
The matching removes amplitude entirely and leaves only shape.

THE SELECTION PLANT IS THE ONE THAT HAD TO BE BUILT PROPERLY.  A pure blur is NOT
a valid model of frame choice: gamma is normalised, so a smooth MTF difference
barely moves it (this is the documented property that makes sub-pixel registration
admissible here).  Real frame choice is chosen PER PIXEL, so within one tile some
sites come from one frame and some from another.  The plant therefore mixes sharp
and defocused content under a random BLOB MASK at 20-60 px -- the same scale band
the falsification lane convicted -- with INDEPENDENT masks in the two arms.

My first structured plant was circular and I discarded it: it injected a fraction of
the real A-B difference, which is the very thing under test.
"""
import os, sys, json, numpy as np, softcheck as S, hcoh as HC, hsel as HS, ncurve as NC

T=HC.T; P=HC.PRIMARY; E=HC.E; MASK=HC.MASK

def prof(A,B,oy,ox,order,nq=10):
    f,_=HC.pair_stats(A,B,oy,ox,oy,ox)
    return [float(np.median(f[idx,P])) for idx in np.array_split(order,nq)], f

def bottom(A,B,oy,ox,order,nq=10):
    idx=np.array_split(order,nq)[0]
    f,_=HC.pair_stats(A,B,oy[idx],ox[idx],oy[idx],ox[idx])
    return float(np.median(f[:,P]))

def blobs(shape,scale,rng):
    """Binary mask with structure at `scale` px: low-res noise, upsampled, thresholded."""
    h=max(2,shape[0]//scale); w=max(2,shape[1]//scale)
    lo=rng.standard_normal((h,w)).astype(np.float32)
    yi=np.linspace(0,h-1,shape[0]); xi=np.linspace(0,w-1,shape[1])
    y0=np.clip(yi.astype(int),0,h-2); x0=np.clip(xi.astype(int),0,w-2)
    fy=(yi-y0)[:,None]; fx=(xi-x0)[None,:]
    up=(lo[y0][:,x0]*(1-fy)*(1-fx) + lo[y0+1][:,x0]*fy*(1-fx)
        + lo[y0][:,x0+1]*(1-fy)*fx + lo[y0+1][:,x0+1]*fy*fx)
    return (up>0).astype(np.float32)

def make_noise(A,s,rng):
    sd=float(A[::8,::8].std())
    n1=rng.standard_normal(A.shape).astype(np.float32)*sd*s
    n2=rng.standard_normal(A.shape).astype(np.float32)*sd*s
    return A+n1, A+n2

def make_select(A,Ab,c,scale,rng):
    m1=blobs(A.shape,scale,rng); m2=blobs(A.shape,scale,rng)
    a=A + c*(1.0-m1)*(Ab-A)
    b=A + c*(1.0-m2)*(Ab-A)
    return a.astype(np.float32), b.astype(np.float32)
