import io, json, os, sys

import numpy as np

sys.path.insert(0, os.path.abspath(r"experiments\V-GATHER"))
from printcert import COVERAGE_MIN, best_index, coverage   # noqa: E402

d = json.load(io.open(r"experiments\V-GATHER\cert.json", encoding="utf-8"))
rows = []
for s, v in d.items():
    if not v.get("done"):
        continue
    uf, sf, used, samp = coverage(v)
    src = [x for x in v["sources"] if "blotch" in x]
    if not src:
        rows.append((s, v["n_frames"], None, uf, sf))
        continue
    b = [x["blotch"] for x in src]
    f = [x["focus_win"] for x in src]
    i, _ = best_index(b, f)
    q = uf >= COVERAGE_MIN and sf >= COVERAGE_MIN
    rows.append((s, v["n_frames"], v["master"]["blotch"] / b[i] if q else None, uf, sf))
rows.sort(key=lambda r: r[1])

print("%-24s %6s %6s %6s %10s" % ("subject", "frames", "used%", "span%", "ratio"))
print("-" * 58)
for s, n, r, uf, sf in rows:
    print("%-24s %6d %5.0f%% %5.0f%% %10s"
          % (s, n, 100 * uf, 100 * sf, "%.4f" % r if r else "REFUSED"))

q = [(n, r) for _, n, r, _, _ in rows if r]
n = np.array([x[0] for x in q], float)
rt = np.array([x[1] for x in q], float)
rk = lambda a: np.argsort(np.argsort(a)).astype(float)
print("\nrank corr of ratio with stack depth:")
print("  all measured, before coverage gate : +0.867  (reported earlier)")
print("  QUALIFYING subjects only           : %+.3f over %d" % (
    float(np.corrcoef(rk(n), rk(rt))[0, 1]), len(q)))
print("""
The gate was added because the surviving-frame count fell with stack depth and a
minimum over fewer frames can only sit higher. If the correlation collapses once
the poorly covered subjects are refused, the residual depth signal was coverage,
not the merge, and the remaining ratios are interpretable.""")
