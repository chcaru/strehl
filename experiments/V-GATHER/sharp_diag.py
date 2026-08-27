"""Cache a run to npz, then interrogate the site population.

The bimodal p10/p90 says two populations are being averaged together. Before
any verdict, find out what separates them.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_real as SR

CACHE = r"C:\dev\strehl-out\V-GATHER\sharpcache"
os.makedirs(CACHE, exist_ok=True)


def cached(subject, numer="MASTER.tiff", **kw):
    tag = "%s__%s__%s" % (subject, numer.replace(".tiff", ""),
                          "_".join("%s%s" % (k, v) for k, v in sorted(kw.items())) or "base")
    p = os.path.join(CACHE, tag + ".npz")
    if os.path.exists(p):
        z = np.load(p, allow_pickle=True)
        return {k: z[k] for k in z.files}
    r = SR.run(subject, numer, **kw)
    np.savez_compressed(p, **{k: np.array(v, dtype=object) if k == "frames" else np.array(v)
                              for k, v in r.items()})
    z = np.load(p, allow_pickle=True)
    return {k: z[k] for k in z.files}


def analyse(r, label):
    A, M, C = r["A"], r["M"], r["C"]
    nreg = np.isfinite(A).sum(axis=0)
    amax = np.where(nreg >= 3, np.nanmax(np.where(np.isfinite(A), A, -np.inf), axis=0), np.nan)
    amin = np.where(nreg >= 3, np.nanmin(np.where(np.isfinite(A), A, np.inf), axis=0), np.nan)
    rng = amax / np.maximum(amin, 1e-12)
    rat = M / amax
    ok = np.isfinite(rat) & (nreg >= 3)
    print("\n=== %s ===" % label)
    print("gridded %d, >=3 frames registered %d" % (len(M), int((nreg >= 3).sum())))
    print("\nsplit by FOCUS RESPONSE = (best frame acutance)/(worst frame acutance)")
    print("a site where focus does not change the high band has no resolvable detail")
    print("%-18s %6s %10s %10s %10s" % ("focus response", "n", "med ratio", "med Amax", "med Mstd"))
    edges = [(1.0, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 15.0), (15.0, 1e9)]
    for lo, hi in edges:
        s = ok & (rng >= lo) & (rng < hi)
        if s.sum() == 0:
            print("%-18s %6d" % ("%.1f - %.1f" % (lo, hi), 0)); continue
        print("%-18s %6d %10.4f %10.5f %10s"
              % ("%.1f - %.1f" % (lo, hi), int(s.sum()), float(np.median(rat[s])),
                 float(np.median(amax[s])), "-"))
    print("\nsplit by the best frame's absolute high-band acutance Amax")
    qs = np.nanpercentile(amax[ok], [0, 20, 40, 60, 80, 100])
    for i in range(5):
        s = ok & (amax >= qs[i]) & (amax <= qs[i + 1])
        print("  Amax %8.5f - %8.5f  n=%4d  med ratio %.4f"
              % (qs[i], qs[i + 1], int(s.sum()), float(np.median(rat[s]))))


if __name__ == "__main__":
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    r = cached(subj)
    analyse(r, subj + "  master vs per-patch best frame")
