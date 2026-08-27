"""Statistic F evaluator + commissioning, driven from the band cache."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB

B_LO, B_HI, B_NZ = SB.B_LO, SB.B_HI, SB.B_NZ
GATE_LO, GATE_HI = 0.5, 2.0     # defocus is a low-pass: it CANNOT move the low
                                # band by more than this. Outside => not the
                                # same content => not a measurement.
NOISE_MAX = 0.50                # refuse a site where noise is more than half
                                # the detail band in either arm
MIN_FRAMES = 3


def nfloor(Pb):
    """MEASURED per-image noise spectrum: 10th percentile over patches, per band."""
    return np.nanpercentile(Pb, 10, axis=0)


def corrected(Pb, nf):
    scale = np.clip(Pb[..., B_NZ] / max(float(nf[B_NZ]), 1e-30), 0.0, None)
    return Pb - nf * scale[..., None]


def detail(Pb, nf):
    c = corrected(Pb, nf)
    D = np.clip(c[..., B_HI].sum(axis=-1), 0.0, None)
    raw = Pb[..., B_HI].sum(axis=-1)
    return D, np.divide(D, raw, out=np.zeros_like(D), where=raw > 0)


def evaluate(z, numer=None, refblur=0.0, refsharp=0.0, dropbest=False,
             refkeep=1, mgain=1.0, mblur=0.0, msharp=0.0, refidx=None,
             minframes=None):
    M = z["M"].astype(np.float64) * (mgain ** 2)
    A = z["A"].astype(np.float64)
    if refidx is not None:
        A = A[refidx]
    A = A[::refkeep]
    nb = M.shape[1]
    fc = np.array([0.035, 0.085, 0.135, 0.175, 0.225, 0.275, 0.325, 0.385, 0.46])
    if mblur > 0:
        M = M * np.exp(-4 * np.pi ** 2 * mblur ** 2 * fc ** 2)[None, :]
    if msharp > 0:
        M = M * (1 + msharp * (1 - np.exp(-4 * np.pi ** 2 * 1.0 * fc ** 2)))[None, :] ** 2
    if refblur > 0:
        A = A * np.exp(-4 * np.pi ** 2 * refblur ** 2 * fc ** 2)[None, None, :]
    if refsharp > 0:
        A = A * (1 + refsharp * (1 - np.exp(-4 * np.pi ** 2 * 1.0 * fc ** 2)))[None, None, :] ** 2
    if numer is not None:
        M = A[numer].copy()
    nfM = nfloor(M)
    DM, sM = detail(M, nfM)
    LM = M[:, B_LO]
    nf, ns = A.shape[0], A.shape[1]
    DA = np.full((nf, ns), np.nan); sA = np.full((nf, ns), np.nan)
    LA = np.full((nf, ns), np.nan)
    for k in range(nf):
        ok = np.isfinite(A[k, :, 0])
        if ok.sum() < 5: continue
        nfk = nfloor(A[k][ok])
        d, s = detail(A[k], nfk)
        DA[k][ok] = d[ok]; sA[k][ok] = s[ok]; LA[k][ok] = A[k][ok, B_LO]
    ratio_lo = LM[None, :] / LA
    valid = np.isfinite(DA) & (ratio_lo >= GATE_LO) & (ratio_lo <= GATE_HI) & (sA >= NOISE_MAX)
    if dropbest:
        DAt = np.where(valid, DA, -np.inf)
        bk = np.argmax(DAt, axis=0)
        valid[bk, np.arange(ns)] = False
    DAt = np.where(valid, DA, -np.inf)
    n_ok = valid.sum(axis=0)
    bestk = np.argmax(DAt, axis=0)
    Dbest = DAt[bestk, np.arange(ns)]
    Lbest = LA[bestk, np.arange(ns)]
    mf = MIN_FRAMES if minframes is None else minframes
    site_ok = (n_ok >= mf) & (sM >= NOISE_MAX) & np.isfinite(Dbest) & (Dbest > 0) & (DM > 0)
    F = (DM / Dbest) / (LM / Lbest)
    return dict(F=F, ok=site_ok, bestk=bestk, n_ok=n_ok, sM=sM, sA=sA,
                nsites=len(M), nframes=nf,
                r_fewframes=int(((n_ok < mf) & (sM >= NOISE_MAX)).sum()),
                r_noisy=int((sM < NOISE_MAX).sum()),
                r_bad=int((site_ok & ~((DM > 0) & np.isfinite(Dbest))).sum()))


def summarise(r):
    f = r["F"][r["ok"]]
    if f.size == 0:
        return None
    return float(np.median(f)), float(np.percentile(f, 10)), float(np.percentile(f, 90)), int(f.size)


if __name__ == "__main__":
    subj = sys.argv[1]
    z = SB.build(subj)
    base = evaluate(z)
    s = summarise(base)
    print("%s: %d of %d sites measured, %d frames" % (subj, s[3], base["nsites"], base["nframes"]))
    print("  F median %.4f  p10 %.4f  p90 %.4f" % (s[0], s[1], s[2]))



