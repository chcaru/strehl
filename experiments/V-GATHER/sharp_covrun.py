"""Commission field coverage and run it."""
import os, sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import blur, usm
import sharp_bands as SB, sharp_F2 as S2, sharp_cov as CV
from sharp_final2 import master_bands
T = CV.TOLS
FMT = "%-18s" + " %7s" * len(T)


def row(name, c):
    if c is None:
        return FMT % ((name,) + ("-",) * len(T))
    return FMT % ((name,) + tuple("%.3f" % v for v in c))


def one(subj):
    z = dict(SB.build(subj))
    sites = z["sites"]
    base = S2.evaluate(z)
    cm, n = CV.cov_from(base)
    if cm is None or n < S2.MIN_SITES:
        print("%-18s REFUSED: only %d gated sites" % (subj, n if cm is not None else 0))
        return None
    print("\n=== %s === %d frames, %d gated sites of %d"
          % (subj, z["A"].shape[0], n, base["nsites"]))
    print(FMT % (("tolerance t",) + tuple("%.2f" % t for t in T)))
    print(row("MASTER", cm))

    # ---- CEILING ARM: cannot be beaten, must read 1.000 at every t <= 1
    orc = CV.oracle_numerator(z)
    cc, _ = CV.cov_from(S2.evaluate(z, Moverride=orc))
    print(row("CEILING (oracle)", cc))

    # ---- PHYSICS / FLOOR: every arm is a one-frame render, cannot reconstruct
    fc = CV.frame_coverage(z)
    bestf = np.nanmax(fc, axis=0)
    medf = np.nanmedian(fc, axis=0)
    print(row("FLOOR best 1 frame", bestf))
    print(row("FLOOR median frame", medf))

    # ---- PLANTS on the numerator
    for nm, op in (("PLANT blur .8", lambda a: blur(a, 0.8)),
                   ("PLANT usm .8/1.0", lambda a: usm(a, 0.8, 1.0))):
        mb = master_bands(subj, sites, op)
        c, _ = CV.cov_from(S2.evaluate(z, Moverride=mb))
        print(row(nm, c))

    # ---- AMPLITUDE: a pure gain is not focus
    ca, _ = CV.cov_from(S2.evaluate(z, mgain=2.0))
    print(row("AMP gain x2", ca))

    # ---- DENOMINATOR ARMS: perturb the ORACLE, not the master
    cd, _ = CV.cov_from(S2.evaluate(z, dropbest=True))
    print(row("DENOM drop best", cd))
    ck, _ = CV.cov_from(S2.evaluate(z, refkeep=2))
    print(row("DENOM keep 1 in 2", ck))

    # ---- NOISE BRACKET: the master averages, a single frame does not
    nb = np.nanmedian(base["noise_bias"][base["ok"]])
    f = base["F"][base["ok"]]; f = f[np.isfinite(f)]
    cu = np.array([float((f / max(1e-9, 1 - nb) >= t).mean()) for t in T])
    print(row("MASTER noise-upper", cu))

    coh = CV.oracle_coherence(z)
    if coh:
        real, mu, sd = coh
        zsc = (mu - real) / max(sd, 1e-9)
        print("  ORACLE COHERENCE  nearest-site |dk| = %.2f frames, shuffled %.2f +- %.2f"
              " -> %.1f sigma %s" % (real, mu, sd, zsc,
                                     "COHERENT (selects depth)" if zsc > 3 else "INCOHERENT -- oracle is chasing noise"))
    return dict(subj=subj, n=n, m=cm, ceil=cc, best=bestf, med=medf, amp=ca,
                drop=cd, keep=ck, up=cu, nb=float(nb), coh=coh,
                nfr=int(z["A"].shape[0]), nsites=int(base["nsites"]),
                r_resp=int(base["r_resp"]), r_few=int(base["r_few"]))


if __name__ == "__main__":
    res = [one(s) for s in sys.argv[1:]]
    res = [r for r in res if r]
    print("\n\n=== HEADLINE: field coverage at t=0.70 ===")
    print("%-18s %6s %9s %9s %9s %8s" % ("subject", "sites", "master", "best 1fr", "median fr", "gain"))
    i = T.index(0.70)
    for r in res:
        print("%-18s %6d %9.3f %9.3f %9.3f %7.1fx"
              % (r["subj"], r["n"], r["m"][i], r["best"][i], r["med"][i],
                 r["m"][i] / max(r["best"][i], 1e-9)))
