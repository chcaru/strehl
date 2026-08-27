"""How big is F2's one-sided noise bias?

F2 does not subtract noise (F's 10th-percentile estimator over-subtracted to
zero on dense texture). The merge averages, so the master carries LESS noise
than any single frame, and an unsubtracted noise floor therefore biases F
DOWNWARD. F > 1 is a lower bound; F < 1 needs this correction before it can be
read as "the master is softer".

noise_bias = HI power of the MOST DEFOCUSED registered frame / HI power of the
best frame. At full defocus the detail band is essentially all noise, so this
is an upper bound on the noise fraction sitting inside the denominator.
"""
import os, sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB
from sharp_F2 import evaluate
print("%-16s %7s %10s %12s %14s" % ("subject", "F med", "noise nb", "F/(1-nb)", "upper bound"))
for s in ("coffee-bubbles", "109MSDCF", "119MSDCF"):
    z = dict(SB.build(s)); r = evaluate(z)
    ok = r["ok"]; f = r["F"][ok]; nb = r["noise_bias"][ok]
    m = np.isfinite(f) & np.isfinite(nb)
    F = float(np.median(f[m])); N = float(np.median(nb[m]))
    print("%-16s %7.4f %10.4f %12.4f %14s"
          % (s, F, N, F / max(1e-9, 1.0 - N),
             "%.2f" % (F / max(1e-9, 1.0 - N))))
print()
print("F/(1-nb) removes ALL of the denominator's noise and none of the master's,")
print("so it is a hard UPPER bound on the true detail ratio. Truth is between.")
