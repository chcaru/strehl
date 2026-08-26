"""Bootstrap CIs and sign tests on the three-arm comparison."""
import json, pathlib
import numpy as np
from scipy import stats as sps

d = json.loads(pathlib.Path(r"C:\dev\strehl-out\V-THESIS\backend.json").read_text())
RNG = np.random.default_rng(7)


def boot(v):
    v = np.asarray(v, float)
    m = [np.median(RNG.choice(v, v.size, replace=True)) for _ in range(4000)]
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


print(f"{'subject':<19}{'comparison':<10}{'n':>4}{'median':>9}"
      f"{'  95% CI':>20}{'neg/n':>8}{'sign p':>9}")
print("-" * 80)
for subj, r in d.items():
    for key, lab in (("P_vs_A_all", "P vs A"), ("E_vs_A_all", "E vs A"), ("P_vs_E_all", "P vs E")):
        v = np.asarray(r[key], float); v = v[np.isfinite(v)]
        lo, hi = boot(v)
        neg = int((v < 0).sum())
        p = sps.binomtest(neg, v.size, 0.5).pvalue
        print(f"{subj:<19}{lab:<10}{v.size:>4}{np.median(v):>+9.3f}"
              f"   [{lo:+.3f}, {hi:+.3f}]{neg:>5}/{v.size:<3}{p:>9.4f}")
    print()
print("POOLED over the three subjects that have all three arms:")
for key, lab in (("P_vs_A_all", "pyramid  vs argmax"), ("E_vs_A_all", "estimator vs argmax"),
                 ("P_vs_E_all", "pyramid  vs estimator")):
    v = np.concatenate([np.asarray(r[key], float) for r in d.values()])
    v = v[np.isfinite(v)]
    lo, hi = boot(v)
    print(f"   {lab:<24} n={v.size:<4} median {np.median(v):+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]")
print()
print("A merge DETAIL GAIN would be a significantly POSITIVE median.")
