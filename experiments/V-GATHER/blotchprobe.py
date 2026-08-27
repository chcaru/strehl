r"""Is `blotch` measuring mottling, or is it measuring background brightness?

blotch = band_dn / mean_dn. If band_dn is roughly constant across subjects while
mean_dn ranges over an order of magnitude, then the statistic is dominated by
its own denominator and the PASS/FAIL split is a split on how bright the flattest
window happened to be -- not on how mottled it is.

Decided by partial correlation: how much of the variance in log(blotch) is
explained by log(mean_dn) alone, versus by log(band_dn), the term that actually
carries the mottling.
"""
import io
import json

import numpy as np

d = json.load(io.open(r"experiments\V-GATHER\delivered.json", encoding="utf-8"))
subs = sorted(d)
bl = np.array([d[s]["blotch"] for s in subs])
bd = np.array([d[s]["band_dn"] for s in subs])
mn = np.array([d[s]["mean_dn"] for s in subs])


def rank(a):
    return np.argsort(np.argsort(a)).astype(float)


def rho(a, b):
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


print("across %d delivered masters" % len(subs))
print("  band_dn  (the MOTTLING term)   range %9.1f .. %9.1f   spread %6.1fx"
      % (bd.min(), bd.max(), bd.max() / bd.min()))
print("  mean_dn  (the BRIGHTNESS term) range %9.1f .. %9.1f   spread %6.1fx"
      % (mn.min(), mn.max(), mn.max() / mn.min()))
print("  blotch                         range %9.5f .. %9.5f   spread %6.1fx"
      % (bl.min(), bl.max(), bl.max() / bl.min()))
print()
print("  rank corr  log(blotch) vs log(mean_dn) : %+.3f" % rho(np.log(bl), np.log(mn)))
print("  rank corr  log(blotch) vs log(band_dn) : %+.3f" % rho(np.log(bl), np.log(bd)))
print()

lb, lm, ld = np.log(bl), np.log(mn), np.log(bd)
for nm, x in (("log(mean_dn) alone", lm), ("log(band_dn) alone", ld)):
    A = np.vstack([x, np.ones_like(x)]).T
    r = lb - A @ np.linalg.lstsq(A, lb, rcond=None)[0]
    print("  R^2 of log(blotch) on %-20s = %.3f"
          % (nm, 1 - r.var() / lb.var()))

order = np.argsort(-bl)
print("\n%-36s %9s %11s %11s" % ("subject (worst blotch first)", "blotch", "band_dn", "mean_dn"))
for i in order:
    print("%-36s %9.5f %11.1f %11.1f" % (subs[i], bl[i], bd[i], mn[i]))

print("""
READ THE TWO COLUMNS AGAINST EACH OTHER. If the subjects at the top of this
table are there because band_dn is large, the statistic is measuring mottling.
If they are there because mean_dn is small, it is measuring exposure of whatever
region flattest() happened to select -- and every verdict built on it inherits
that, including the 17/9 split and every ratio in this lane.""")
