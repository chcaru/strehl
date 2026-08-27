"""Does ORACLE SUBSAMPLING bias the COVERAGE GAIN?

bee-3-cpl is a COMPLETE 299-of-299 enumeration, so its oracle is the true
per-site best frame. Thinning it to 1-in-k reproduces exactly the handicap the
other deep subjects carry (they were rendered 1-in-9). Whatever it does to the
gain here is the correction those subjects need.

A thinner oracle is a weaker oracle, so it raises the master's coverage AND a
single frame's coverage. The question is whether the RATIO survives.
"""
import os, sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands2 as B2, sharp_cov2 as CV
T = 0.80
z = dict(B2.build("bee-3-cpl"))
print("%6s %8s %8s %9s %9s %8s %10s" % ("keep", "frames", "sites", "master", "best 1fr", "gain", "vs full"))
base = None
for k in (1, 2, 3, 5, 9, 15):
    r = CV.evaluate(z, refkeep=k)
    f = r["F"][r["ok"]]; f = f[np.isfinite(f)]
    if f.size < CV.MIN_SITES:
        print("%6d   too few sites" % k); continue
    m = float((f >= T).mean())
    nf = z["A"][::k].shape[0]
    bf = 0.0
    for j in range(nf):
        rj = CV.evaluate(z, numer=j, refkeep=k)
        g = rj["F"][rj["ok"]]; g = g[np.isfinite(g)]
        if g.size:
            bf = max(bf, float((g >= T).mean()))
    gain = m / max(bf, 1e-9)
    if k == 1:
        base = gain
    print("%6d %8d %8d %9.3f %9.3f %7.1fx %9.3f"
          % (k, nf, f.size, m, bf, gain, gain / base))
