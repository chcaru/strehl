r"""Is the rim reading confounded with how few edges a subject has?

The five largest readings all came from subjects with the fewest isolated edges
(leaf-2-cpl +37.1% on 112 edges, 113MSDCF +17.3% on 72). That is the shape of
the depth confound found earlier in this project, where a `min` over fewer
frames could only sit higher and the ratio tracked stack depth at rho +0.764.
If it recurs here the readings are an artifact of sample size and not of halo.
"""
import io, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(io.open(os.path.join(HERE, "rim.json"), encoding="utf-8"))
ok = {k: v for k, v in d.items() if "refused" not in v}
n = np.array([v["n_sel"] for v in ok.values()], float)
c = np.array([v["corrected_bright"] for v in ok.values()], float)
iso = np.array([v["isolated_frac"] for v in ok.values()], float)
w = np.array([v["master"]["width"] for v in ok.values()], float)


def rho(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra, rb = a.argsort().argsort(), b.argsort().argsort()
    return float(np.corrcoef(ra, rb)[0, 1])


print("examined subjects: %d  refused: %d" % (len(ok), len(d) - len(ok)))
print("Spearman rho(corrected, n_sel)        = %+.3f" % rho(c, n))
print("Spearman rho(corrected, isolated_frac)= %+.3f" % rho(c, iso))
print("Spearman rho(corrected, edge_width)   = %+.3f" % rho(c, w))
print("Spearman rho(n_sel, edge_width)       = %+.3f" % rho(n, w))
print()
print("%-38s %6s %6s %7s %8s  %s" % ("subject", "n_sel", "iso%", "width", "corr%", "boot CI on raw bright"))
for k in sorted(ok, key=lambda k: -ok[k]["corrected_bright"]):
    v = ok[k]
    ci = v["master"].get("ci_bright")
    print("%-38s %6d %6.1f %7.2f %+8.3f  %s" % (
        k, v["n_sel"], 100 * v["isolated_frac"], v["master"]["width"],
        100 * v["corrected_bright"],
        "[%+.3f%%, %+.3f%%]" % (100 * ci[0], 100 * ci[1]) if ci else "n/a"))

print()
big = [k for k in ok if ok[k]["corrected_bright"] > 0.02]
small = [k for k in ok if ok[k]["corrected_bright"] <= 0.02]
print("n_sel median: over-threshold %.0f (n=%d) vs at-or-under %.0f (n=%d)"
      % (np.median([ok[k]["n_sel"] for k in big]), len(big),
         np.median([ok[k]["n_sel"] for k in small]), len(small)))
print("width median: over-threshold %.2f vs at-or-under %.2f"
      % (np.median([ok[k]["master"]["width"] for k in big]),
         np.median([ok[k]["master"]["width"] for k in small])))
