r"""Dose-response: does the rim change track how much the gate actually changed?

The treatment's potency varies 60-fold across these subjects, read from each
render's OWN banner rather than assumed. If the per-band floor knob causes rim
changes, subjects where the gate went from 0.0% to 57-61% of coefficients
averaged must move more than wrapped-text-1, where it went to 1.0%. That is a
far stronger test than any single A/B, and it needs no extra render.
"""
import io
import json
import os
import re

import numpy as np

D = r"C:\dev\strehl-out\V-BANDFLOOR"
HERE = os.path.dirname(os.path.abspath(__file__))
SUBS = ["coffee-bubbles", "119MSDCF", "dry-erase-marker-head-cpl",
        "bee-2-cpl", "leaf-2-cpl", "wrapped-text-1"]
SPLIT = {"leaf-2-cpl": (0.9856, 1.0078), "119MSDCF": (0.9262, 1.0013),
         "coffee-bubbles": (0.9538, 1.0009),
         "dry-erase-marker-head-cpl": (0.9709, 1.0025),
         "bee-2-cpl": (0.9665, 1.0047), "wrapped-text-1": (1.0020, 1.0066)}


def band1(sub, arm):
    p = os.path.join(D, "%s__%s.log" % (sub, arm))
    if not os.path.exists(p):
        return None
    for ln in io.open(p, encoding="utf-8", errors="replace"):
        m = re.match(r"\s*averaged\s+:\s+(.*)", ln)
        if m:
            v = [float(x.rstrip("%")) for x in m.group(1).split()]
            return v
    return None


print("%-27s %7s %7s %9s %20s %8s %8s"
      % ("subject", "L1 A", "L1 B", "d rim", "95% CI raw", "flat", "detail"))
print("-" * 92)
dose, drim, dflat = [], [], []
for s in SUBS:
    a, b = band1(s, "A-unset"), band1(s, "B-coarse8")
    jf = os.path.join(HERE, "bg_%s.json" % s)
    if not os.path.exists(jf):
        print("%-27s %7.1f %7.1f   REFUSED by the instrument (floor)"
              % (s, a[1], b[1]))
        continue
    doc = json.load(io.open(jf, encoding="utf-8"))
    t = doc["arms"].get("B coarse8 TREATMENT")
    ci = t["ci_bright"]
    fl, dt = SPLIT[s]
    print("%-27s %7.1f %7.1f %+8.3f%% [%+7.3f%%,%+7.3f%%] %8.4f %8.4f"
          % (s, a[1], b[1], 100 * t["d_corr_bright"], 100 * ci[1], 100 * ci[2],
             fl, dt))
    dose.append(b[1] - a[1])
    drim.append(abs(100 * t["d_corr_bright"]))
    dflat.append(fl)

d = np.asarray(dose)
r_ = np.asarray(drim)
f = np.asarray(dflat)


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean()
    ry -= ry.mean()
    return float(rx @ ry / np.sqrt((rx @ rx) * (ry @ ry)))


print("\nDOSE = the rise in band-1 coefficients the gate averaged (pts)")
print("  dose range              %.1f .. %.1f pts (%.0f-fold)"
      % (d.min(), d.max(), d.max() / max(d.min(), 1e-9)))
print("  |d rim| vs dose         Spearman %+.3f   (rim range %.3f..%.3f pts)"
      % (spearman(d, r_), r_.min(), r_.max()))
print("  flat-noise ratio vs dose Spearman %+.3f  (flat range %.4f..%.4f)"
      % (spearman(d, f), f.min(), f.max()))
print("\nA dose-response in FLAT NOISE and none in RIM means the knob is doing")
print("something real -- and that the something is not the aura.")

# NaN guard, per my own earlier finding: `NaN > x` is False and reads as a pass.
allv = np.concatenate([d, r_, f])
print("\nnon-finite values anywhere in the table: %d" % int((~np.isfinite(allv)).sum()))