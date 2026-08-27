"""Statistic F2. Two defects measured in F are repaired:

 1. F anchored the content gate at 0.05-0.12 cyc/px and claimed defocus could
    not move it. At macro blur scales it can: loOK% fell to 2.9% on TEXT. The
    anchor moves to 0.02-0.05 cyc/px (20-50 px features).
 2. F subtracted a noise floor estimated as the 10th percentile of patches. On
    a densely textured subject fewer than 10% of patches are featureless, so it
    over-subtracted -- medSA hit 0.000 on wrapped-text-1. No noise subtraction
    is used. Instead the site must show a real FOCUS RESPONSE in the detail
    band, which noise cannot fake because noise does not vary with focus.

Bias statement, stated because it is one-sided: the merge averages, so the
master carries LESS noise than any single frame. With no noise subtraction that
biases F DOWNWARD. F > 1 is therefore a lower bound; F < 1 is not conclusive.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB

B_ANCHOR = 0            # 0.02-0.05 cyc/px
B_HI = [3, 4, 5]        # 0.15-0.30 cyc/px
GATE_LO, GATE_HI = 0.5, 2.0
FOCUS_RESP_MIN = 2.0
MIN_FRAMES = 4        # a denominator thinner than this is not an envelope
MIN_SITES = 10


def evaluate(z, numer=None, dropbest=False, refkeep=1, mgain=1.0,
             refidx=None, minframes=None, Moverride=None, respmin=None):
    M = z["M"].astype(np.float64) * (mgain ** 2) if Moverride is None else Moverride.astype(np.float64)
    A = z["A"].astype(np.float64)
    if refidx is not None:
        A = A[refidx]
    A = A[::refkeep]
    if numer is not None:
        M = A[numer].copy()
    nf, ns = A.shape[0], A.shape[1]
    HM = M[:, B_HI].sum(axis=1); LM = M[:, B_ANCHOR]
    HA = A[:, :, B_HI].sum(axis=2); LA = A[:, :, B_ANCHOR]
    reg = np.isfinite(HA)
    # GAIN NORMALISATION. Without it a pure gain on the master shifts sites
    # across the content gate and changes which frame wins the argmax, and the
    # statistic moves although nothing is sharper: AMPmaxdiff read 26 on
    # wrapped-text-1. gnorm is ONE scalar per subject, so it cannot absorb a
    # per-site content difference, which is what the gate must still catch.
    with np.errstate(invalid="ignore", divide="ignore"):
        gnorm = float(np.nanmedian(np.where(reg, LA / LM[None, :], np.nan)))
    if not np.isfinite(gnorm) or gnorm <= 0:
        gnorm = 1.0
    rlo = (LM[None, :] * gnorm) / LA
    valid = reg & (rlo >= GATE_LO) & (rlo <= GATE_HI)
    # focus response over REGISTERED frames -- noise does not vary with focus
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
    mf = MIN_FRAMES if minframes is None else minframes
    rm = FOCUS_RESP_MIN if respmin is None else respmin
    site_ok = ((n_ok >= mf) & np.isfinite(Hbest) & (Hbest > 0) & (HM > 0)
               & np.isfinite(resp) & (resp >= rm))
    F = (HM / Hbest) / (LM / Lbest)
    noise_bias = np.where(Hbest > 0, np.nanmin(HR, axis=0) / np.maximum(Hbest, 1e-30), np.nan)
    return dict(F=F, ok=site_ok, gnorm=gnorm, bestk=bestk, n_ok=n_ok, resp=resp, nsites=len(M),
                nframes=nf, noise_bias=noise_bias,
                r_resp=int((np.isfinite(resp) & (resp < rm)).sum()),
                r_few=int(((n_ok < mf) & (~np.isfinite(resp) | (resp >= rm))).sum()))


def summarise(r):
    f = r["F"][r["ok"]]
    f = f[np.isfinite(f)]
    if f.size == 0:
        return None
    return float(np.median(f)), float(np.percentile(f, 10)), float(np.percentile(f, 90)), int(f.size)




