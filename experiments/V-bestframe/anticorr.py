"""If the deficit were a path-boundary artefact, subjects with the LARGEST
measured handicap would fail hardest. Test that directly."""
import numpy as np
from scipy import stats

RG = {"flowers-cpl": 0.8615, "flower-bud-alone-cpl": 0.8669,
      "couch-fibers-cpl": 0.8773, "bee-1-cpl": 0.8838, "109MSDCF": 0.9188,
      "119MSDCF": 0.9264, "112MSDCF": 0.9316, "flat-on-ruler-cpl": 0.9463}
WIN = {"flowers-cpl": 83.3, "flower-bud-alone-cpl": 46.6, "couch-fibers-cpl": 100.0,
       "bee-1-cpl": 99.5, "109MSDCF": 4.5, "119MSDCF": 22.6, "112MSDCF": 100.0,
       "flat-on-ruler-cpl": 86.4}
k = sorted(RG)
r = np.array([RG[s] for s in k]); w = np.array([WIN[s] for s in k])
rho, p = stats.spearmanr(r, w)
print(f"  n = {len(k)} subjects with a measured gather retention")
print(f"  Spearman(R_gather, merge>=frame %) = {rho:+.3f}, p = {p:.3f}")
print(f"  The objection REQUIRES a strong POSITIVE rho: a bigger handicap")
print(f"  (smaller R) must mean a lower pass rate. Observed sign is "
      f"{'POSITIVE' if rho > 0 else 'NEGATIVE'}.")
print(f"  R spread across subjects: {r.min():.4f}-{r.max():.4f}, a factor of "
      f"{r.max()/r.min():.3f}")
print(f"  pass-rate spread: {w.min():.1f}%-{w.max():.1f}%")
lo, hi = r < np.median(r), r >= np.median(r)
print(f"  worst-handicap half  (R {r[lo].min():.4f}-{r[lo].max():.4f}): "
      f"median pass {np.median(w[lo]):.1f}%")
print(f"  gentlest-handicap half (R {r[hi].min():.4f}-{r[hi].max():.4f}): "
      f"median pass {np.median(w[hi]):.1f}%")