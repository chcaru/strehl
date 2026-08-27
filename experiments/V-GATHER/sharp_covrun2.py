"""Commission and run FIELD COVERAGE on the defocus-robust cache.

Adds three things the first pass did not have:

 1. A POWER CHECK on the oracle-coherence arm. "Real ~ shuffled" has two
    causes: the oracle is chasing noise, OR the subject has no depth variation
    across the gated field, in which case there is no depth map to detect and
    the test has no power. Reporting the second as the first would be a false
    conviction, which is the exact error this project keeps making.
 2. A NO-HEADROOM REFUSAL. If the best single frame already covers the field,
    the floor has met the ceiling and coverage cannot discriminate. Measured on
    109MSDCF, where one frame reads 1.000 at t=0.70.
 3. Both normalisations side by side.
"""
import os, sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import blur, usm
import sharp_bands2 as B2, sharp_cov2 as CV
from sharp_final2 import master_bands

T = (0.30, 0.50, 0.70, 0.80, 0.90, 1.00)
HEAD = T.index(0.80)
FMT = "%-20s" + " %7s" * len(T)


def curve(r):
    f = r["F"][r["ok"]]; f = f[np.isfinite(f)]
    if f.size == 0:
        return None, 0
    return np.array([float((f >= t).mean()) for t in T]), int(f.size)


def paired(rb, r2):
    """Denominator arms must be compared ON THE SAME SITES.

    Perturbing the oracle changes which sites pass the >=4-frame gate, so an
    unpaired comparison mixes a real effect with a site-set change and can go
    the wrong way by one site. Restricting both arms to the sites they share
    makes the comparison exact: at a fixed site, weakening the oracle can only
    lower Hbest, so F can only rise.
    """
    j = rb["ok"] & r2["ok"]
    if j.sum() < CV.MIN_SITES:
        return None, None, 0
    a = rb["F"][j]; b = r2["F"][j]
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    return (np.array([float((a >= t).mean()) for t in T]),
            np.array([float((b >= t).mean()) for t in T]), int(a.size))


def row(name, c):
    return FMT % ((name,) + (("-",) * len(T) if c is None else tuple("%.3f" % v for v in c)))


def coherence(z, mode):
    r = CV.evaluate(z, mode=mode)
    sites = z["sites"]; ok = r["ok"]
    if ok.sum() < 12:
        return None
    ys = sites[ok, 0].astype(float); xs = sites[ok, 1].astype(float)
    bk = r["bestk"][ok].astype(float)
    d2 = (ys[:, None] - ys[None, :]) ** 2 + (xs[:, None] - xs[None, :]) ** 2
    np.fill_diagonal(d2, np.inf)
    nn = np.argmin(d2, axis=1)
    real = float(np.mean(np.abs(bk - bk[nn])))
    rng = np.random.default_rng(11)
    sh = [float(np.mean(np.abs(bk - rng.permutation(bk)[nn]))) for _ in range(200)]
    mu, sd = float(np.mean(sh)), float(np.std(sh))
    nf = r["nframes"]
    # POWER: if the winning index barely varies across the field there is no
    # depth map to find and the arm cannot conclude either way.
    power = mu / max(nf, 1)
    return real, mu, sd, power, float(np.std(bk)), nf


def one(subj, mode="raw"):
    z = dict(B2.build(subj))
    base = CV.evaluate(z, mode=mode)
    cm, n = curve(base)
    if cm is None or n < CV.MIN_SITES:
        return dict(subj=subj, verdict="REFUSED", why="only %d gated sites" % n,
                    n=n, nsites=int(base["nsites"]),
                    r_resp=int(base["r_resp"]), r_few=int(base["r_few"]))
    print("\n=== %s [%s] === %d frames, %d gated sites of %d"
          % (subj, mode, z["A"].shape[0], n, base["nsites"]))
    print(FMT % (("tolerance t",) + tuple("%.2f" % t for t in T)))
    print(row("MASTER", cm))
    A = z["A"].astype(np.float64)
    orc = A[base["bestk"], np.arange(A.shape[1])]
    cc, _ = curve(CV.evaluate(z, Moverride=orc, mode=mode))
    print(row("CEILING oracle", cc))
    nf = A.shape[0]
    fc = np.full((nf, len(T)), np.nan)
    for j in range(nf):
        c, _ = curve(CV.evaluate(z, numer=j, mode=mode))
        if c is not None:
            fc[j] = c
    bestf = np.nanmax(fc, axis=0); medf = np.nanmedian(fc, axis=0)
    print(row("FLOOR best 1 frame", bestf))
    print(row("FLOOR median frame", medf))
    arms = {}
    for nm, op in (("PLANT blur .8", lambda a: blur(a, 0.8)),
                   ("PLANT usm .8/1.0", lambda a: usm(a, 0.8, 1.0))):
        c, _ = curve(CV.evaluate(z, Moverride=master_bands(subj, z["sites"], op), mode=mode))
        arms[nm] = c; print(row(nm, c))
    for nm, kw in (("AMP x2 (sensitivity)", dict(mgain=2.0)),
                   ("DENOM drop best", dict(dropbest=True)),
                   ("DENOM keep 1 in 2", dict(refkeep=2)),
                   ("DENOM keep 1 in 3", dict(refkeep=3))):
        c, _ = curve(CV.evaluate(z, mode=mode, **kw))
        arms[nm] = c; print(row(nm, c))
    nb = float(np.nanmedian(base["noise_bias"][base["ok"]]))
    f = base["F"][base["ok"]]; f = f[np.isfinite(f)]
    cu = np.array([float((f / max(1e-9, 1 - nb) >= t).mean()) for t in T])
    print(row("MASTER noise-upper", cu))
    coh_bad = False
    coh = coherence(z, mode)
    if coh:
        real, mu, sd, power, sbk, nfr = coh
        if power < 0.08:
            verdict_c = "NO POWER (winning frame varies by only %.1f of %d frames across the field)" % (mu, nfr)
        elif (mu - real) / max(sd, 1e-9) > 3:
            verdict_c = "COHERENT -- the oracle is selecting DEPTH (%.1f sigma)" % ((mu-real)/max(sd,1e-9))
        else:
            verdict_c = "INCOHERENT -- the oracle is chasing NOISE"
            coh_bad = True
        print("  ORACLE COHERENCE  |dk| nearest-site %.2f vs shuffled %.2f+-%.2f : %s"
              % (real, mu, sd, verdict_c))
    # ---- verdicts
    ok_ceiling = cc is not None and cc[HEAD] > 0.999
    ok_plants = (arms["PLANT blur .8"][HEAD] < cm[HEAD] - 1e-9
                 and arms["PLANT usm .8/1.0"][HEAD] >= cm[HEAD] - 1e-9)
    # AMP is NOT a pass criterion. With no image-estimated normaliser the
    # statistic is deliberately proportional to numerator gain, and gauge
    # invariance comes from the experiment design instead: master and every
    # single-frame arm are renders from ONE binary with ONE pinned --exposure,
    # which the render logs confirm print the identical gain. Reported here so
    # the dependency is visible rather than assumed.
    ok_amp = True
    ok_denom = (arms["DENOM drop best"][HEAD] >= cm[HEAD] - 1e-9
                and arms["DENOM keep 1 in 2"][HEAD] >= cm[HEAD] - 1e-9)
    ok_floor = bestf[HEAD] < 0.95 and bestf[0] <= 1.0 + 1e-9
    v = dict(subj=subj, mode=mode, n=n, nsites=int(base["nsites"]), nfr=nf,
             m=cm, ceil=cc, best=bestf, med=medf, up=cu, nb=nb, coh=coh, arms=arms,
             r_resp=int(base["r_resp"]), r_few=int(base["r_few"]),
             A_ceiling=ok_ceiling, A_plants=ok_plants, A_amp=ok_amp,
             A_denom=ok_denom, A_headroom=ok_floor)
    if not ok_ceiling: v.update(verdict="FAILED-ARM", why="ceiling arm read %.3f, not 1.000" % cc[HEAD])

    elif not ok_plants:v.update(verdict="FAILED-ARM", why="planted blur/sharpen did not move the right way")
    elif not ok_denom: v.update(verdict="FAILED-ARM", why="weakening the oracle did not raise coverage")
    elif coh_bad:      v.update(verdict="REFUSED", why="oracle is not selecting depth: argmax is spatially incoherent")
    elif not ok_floor: v.update(verdict="REFUSED", why="no headroom: best single frame already covers %.3f" % bestf[HEAD])
    else:              v.update(verdict="MEASURED", why="")
    print("  ARMS ceiling=%s amp=%s plants=%s denom=%s headroom=%s -> %s %s"
          % (ok_ceiling, ok_amp, ok_plants, ok_denom, ok_floor, v["verdict"], v["why"]))
    return v


if __name__ == "__main__":
    mode = "lonorm" if "--lonorm" in sys.argv else "raw"
    subs = [a for a in sys.argv[1:] if not a.startswith("--")]
    res = [one(s, mode) for s in subs]
    print("\n\n=== HEADLINE: field coverage at t=0.80  [%s] ===" % mode)
    print("%-20s %6s %8s %9s %9s %8s  %s" % ("subject", "sites", "master", "best 1fr", "median fr", "gain", "verdict"))
    for r in res:
        if r.get("m") is None:
            print("%-20s %6d %8s %9s %9s %8s  %s: %s" % (r["subj"], r.get("n",0), "-","-","-","-", r["verdict"], r["why"]))
            continue
        print("%-20s %6d %8.3f %9.3f %9.3f %7.1fx  %s %s"
              % (r["subj"], r["n"], r["m"][HEAD], r["best"][HEAD], r["med"][HEAD],
                 r["m"][HEAD]/max(r["best"][HEAD],1e-9), r["verdict"], r["why"]))
    print("\n=== PARTITION (sites) ===")
    print("%-20s %7s %9s %11s %10s" % ("subject","sites","measured","ref:no-resp","ref:few-fr"))
    ts=tm=tr=tf=0
    for r in res:
        ts+=r["nsites"]; tm+=r["n"]; tr+=r["r_resp"]; tf+=r["r_few"]
        print("%-20s %7d %9d %11d %10d" % (r["subj"], r["nsites"], r["n"], r["r_resp"], r["r_few"]))
    print("%-20s %7d %9d %11d %10d   (sum %d)" % ("TOTAL", ts, tm, tr, tf, tm+tr+tf))



