import io, json

import numpy as np


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def ratios(d):
    out = []
    for s, v in d.items():
        if not v.get("done"):
            continue
        src = [x for x in v["sources"] if "blotch" in x]
        if not src:
            continue
        b = [x["blotch"] for x in src]
        f = [x["focus_win"] for x in src]
        hi = max(f)
        keep = [i for i in range(len(b)) if f[i] >= 0.5 * hi]
        gi = min(keep, key=lambda i: b[i])
        out.append((s, v["n_frames"], len(src), v["master"]["blotch"] / b[gi], src[gi]["k"]))
    return out


def rho(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


un = {s: (n, r) for s, n, _, r, _ in ratios(load(r"experiments\V-GATHER\cert-unregistered.json"))}
re_ = ratios(load(r"experiments\V-GATHER\cert.json"))
re_.sort(key=lambda x: x[1])

print("%-24s %6s %6s %10s %10s %7s" % ("subject", "frames", "used", "unreg", "REGISTERED", "best k"))
print("-" * 70)
for s, n, used, r, k in re_:
    u = un.get(s, (0, float("nan")))[1]
    print("%-24s %6d %6d %10.4f %10.4f %7d" % (s, n, used, u, r, k))

common = [(s, n, r) for s, n, _, r, _ in re_ if s in un]
n1 = np.array([un[s][0] for s, _, _ in common], float)
ru = np.array([un[s][1] for s, _, _ in common], float)
rr = np.array([r for _, _, r in common], float)
print("\nrank corr of RATIO with STACK DEPTH, over the same %d subjects:" % len(common))
print("  unregistered : rho = %+.3f   <- the artifact" % rho(n1, ru))
print("  REGISTERED   : rho = %+.3f" % rho(n1, rr))
print("""
Registration was applied to remove a contamination that grew with stack depth.
If the correlation with depth survives at nearly full strength, the fix did not
reach the cause and the remaining ratios are still suspect. This is the check
that decides whether the corrected numbers may be reported at all.""")
