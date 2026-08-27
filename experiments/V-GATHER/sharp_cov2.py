"""Coverage evaluation. Two normalisations, both computed, because the choice
between them is a physics question and not a taste one.

  RAW      Fcov_i = (H_master,i * gnorm) / H_oracle,i
  LONORM   F2's F  = (H_M/H_best) / (L_M/L_best)   -- per-site LO normalisation

LONORM exists in F2 to cancel a contrast difference between two DIFFERENT image
pipelines. Here numerator and denominator are the SAME pipeline at the SAME
pinned exposure, so there is nothing left for it to cancel -- and it does active
harm: macro defocus attenuates the 0.02-0.05 cyc/px anchor too (measured
earlier: F's anchor is NOT defocus-invariant), so dividing by L_j/L_best
partially UNDOES the defocus in a single-frame numerator and inflates the
floor. An inflated floor understates the coverage gain.

gnorm is ONE scalar per subject and is proportional to 1/g^2, so (H_M * gnorm)
is exactly gain-invariant while remaining a pure energy ratio per site.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB
import sharp_F2 as S2

B_ANCHOR, B_HI = S2.B_ANCHOR, S2.B_HI
LPCORR_KEY = "CL"
FOCUS_RESP_MIN = 2.0
MIN_FRAMES = 4
MIN_SITES = 10


def evaluate(z, numer=None, dropbest=False, refkeep=1, mgain=1.0,
             Moverride=None, mode="raw", respmin=None, minframes=None):
    M = (z["M"].astype(np.float64) * (mgain ** 2)) if Moverride is None else Moverride.astype(np.float64)
    A = z["A"].astype(np.float64)[::refkeep]
    if numer is not None:
        M = A[numer].copy()
    ns = A.shape[1]
    HM = M[:, B_HI].sum(axis=1); LM = M[:, B_ANCHOR]
    HA = A[:, :, B_HI].sum(axis=2); LA = A[:, :, B_ANCHOR]
    reg = np.isfinite(HA)
    # ORACLE ELIGIBILITY: registration only. A frame that is merely DEFOCUSED
    # must stay in -- it is the measurement that a single frame does not cover
    # this site. It cannot corrupt an argmax on absolute detail because defocus
    # only ever LOWERS detail.
    valid = reg.copy()
    HR = np.where(reg, HA, np.nan)
    with np.errstate(invalid="ignore"):
        resp = np.nanmax(HR, axis=0) / np.maximum(np.nanmin(HR, axis=0), 1e-30)
    if dropbest:
        bk0 = np.argmax(np.where(valid, HA, -np.inf), axis=0)
        valid[bk0, np.arange(ns)] = False
    HV = np.where(valid, HA, -np.inf)
    n_ok = valid.sum(axis=0)
    bestk = np.argmax(HV, axis=0)
    Hbest = HV[bestk, np.arange(ns)]
    Lbest = LA[bestk, np.arange(ns)]
    # NO GAIN NORMALISATION. Two attempts at one both failed, and the failures
    # were instructive:
    #   v1  median(LA/LM) over ALL frames is a defocus average, not a gain --
    #       the CEILING ARM caught it reading a constant below 1.
    #   v2  median(Lbest/LM) is a gain for the master but NOT for a
    #       single-frame numerator, whose own anchor is defocused at exactly
    #       the sites that matter. It inflated the FLOOR to 1.000 on a
    #       299-frame stack of couch fibres, which is physically impossible.
    # Any normaliser estimated from the image is contaminated by the thing
    # being measured. So there is none. Gauge invariance is obtained BY
    # CONSTRUCTION instead: numerator and denominator are renders from one
    # binary with one pinned --exposure, verified in the render logs. That is
    # stronger than a correction, and it makes two arms EXACT rather than
    # empirical: F(oracle) = Hbest/Hbest = 1 identically, and a single-frame
    # numerator satisfies F = Hj/Hbest <= 1 identically, so the floor can
    # never cross the ceiling.
    gnorm = 1.0
    mf = MIN_FRAMES if minframes is None else minframes
    rm = FOCUS_RESP_MIN if respmin is None else respmin
    ok = ((n_ok >= mf) & np.isfinite(Hbest) & (Hbest > 0) & (HM > 0)
          & np.isfinite(resp) & (resp >= rm))
    if mode == "raw":
        F = (HM * gnorm) / Hbest
    else:
        F = (HM / Hbest) / (LM / Lbest)
    nb = np.where(Hbest > 0, np.nanmin(HR, axis=0) / np.maximum(Hbest, 1e-30), np.nan)
    return dict(F=F, ok=ok, bestk=bestk, n_ok=n_ok, resp=resp, gnorm=gnorm,
                noise_bias=nb, nsites=len(M), nframes=A.shape[0],
                r_resp=int((np.isfinite(resp) & (resp < rm)).sum()),
                r_few=int(((n_ok < mf) & (~np.isfinite(resp) | (resp >= rm))).sum()))


