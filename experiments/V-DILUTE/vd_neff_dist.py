"""n_eff distribution, hard gate vs soft Gaussian, on the same subject.

`selection_inflation(n)` fires only at `n <= 1`. Fact 458 measured n_eff = 1
across 41.66% of the plane at a working gate. If the soft kernel collapses that
mass, then a re-armed inflation term keyed on the integer count fires on
essentially nothing -- and it is the pixels it exists to serve that it stops
serving.
"""
import io
import sys

import numpy as np
import tifffile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

D = r"D:\strehl-out\V-DILUTE\softgate"
hard = tifffile.imread(rf"{D}\neff_hard.tiff").astype(np.float64)
soft = tifffile.imread(rf"{D}\neff_soft.tiff").astype(np.float64)
N = 22

print(f"subject 109MSDCF, N={N}, plane {hard.shape}, {hard.size:,} pixels\n")
print(f"  {'':<22}{'hard gate':>14}{'soft gaussian':>16}")
print(f"  {'-'*52}")
for label, fn in (
    ("mean n_eff", lambda a: a.mean()),
    ("median n_eff", lambda a: np.median(a)),
    ("p10", lambda a: np.percentile(a, 10)),
    ("p90", lambda a: np.percentile(a, 90)),
    ("% at n_eff <= 1", lambda a: 100 * (a <= 1).mean()),
    ("% at n_eff <= 2", lambda a: 100 * (a <= 2).mean()),
    (f"% at n_eff >= {N-2}", lambda a: 100 * (a >= N - 2).mean()),
):
    print(f"  {label:<22}{fn(hard):>14.3f}{fn(soft):>16.3f}")

h1, s1 = 100 * (hard <= 1).mean(), 100 * (soft <= 1).mean()
print()
print("  CONSEQUENCE for a re-armed selection_inflation(n), which fires at n <= 1:")
print(f"    hard path : fires on {h1:6.2f}% of the plane")
print(f"    soft path : fires on {s1:6.2f}% of the plane   <- n_eff; the INTEGER")
print("                count is >= n_eff, so the true soft figure is this or lower.")
if h1 > 0:
    print(f"    the term loses {100*(1-s1/h1):.1f}% of its reach under the soft kernel.")
