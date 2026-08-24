"""M68 step 06 - is the "partial fix is worse than none" claim robust?

The orchestrator is going to record a standing rule off the back of one
sentence in M68 section 7, so that sentence gets audited before it is acted
on. Two questions, both answerable from numbers already measured; this
script introduces NO new data and makes no new choices.

  Q1  Is the SIGN of the partial fix's error robust, or does it inherit the
      provenance of the position statistic f that D1 forced me to withdraw?

  Q2  Does the harm hold across the ISO range and across signal levels, or
      only where read noise is a material share of the variance?

--------------------------------------------------------------- the model

`PlaneNoise` carries `gain_dn_per_e` (g) and `read_noise_e` (sigma_r). For
a measured pedestal-subtracted level D in DN, the signal in electrons is
D/g, so the model's predicted variance is

    var_DN = D*g + sigma_r^2 * g^2                                       (5)

the first term shot, the second read. For the B plane, truth is
g_B = k*g_G with k = 0.8396 (SYNTHESIS fact 921 / M61) and
sigma_r,B = m*sigma_r,G with m = 1.09943 (M68), and note that
m^2 k^2 = 0.85208 is exactly the measured alpha ratio - the read term is
pinned by M68's own measurement and does not depend on m separately.

Three candidate models:
    shipped      g = g_G,   sigma_r = sigma_r,G     (both knobs at 1.0)
    partial      g = k*g_G, sigma_r = sigma_r,G     (the one-line "fix")
    full         g = k*g_G, sigma_r = m*sigma_r,G   (M68 fact 27)

Parametrised by rho, the read-noise share of the TRUE variance:

    var_shipped / var_true = (1-rho)/k + rho/(m^2 k^2)                   (6)
    var_partial / var_true = (1-rho) + rho/m^2                           (7)

rho = 1 is a dark frame - the regime M68 actually measured. rho = 0 is the
shot-noise limit.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("m68", HERE / "src" / "01-dark-iso-sweep.py")
m68 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m68)

K = 0.8396          # SYNTHESIS fact 921 / M61 local fact 22, B gain / green
ALPHA = 0.85208     # M68, alpha_B / alpha_Gpool, arm r6
SIG = np.sqrt(ALPHA)
M = SIG / K         # implied read_noise_e scale


def main() -> int:
    blob = json.loads((HERE / "data" / "01-dark-iso-sweep.json").read_text())
    isos = sorted(int(i) for i in blob["isos"])

    def var(arm, plane):
        rows = {int(r["iso"]): r for r in blob["rows"][arm][plane]}
        return np.array([rows[i]["var"] for i in isos], float)

    print(f"k = {K:.4f}   alpha ratio = {ALPHA:.5f}   sigma ratio = {SIG:.5f}"
          f"   m = {M:.5f}")

    # ------------------------------------------------------------------- Q1
    print("\n=== Q1 sign robustness ===")
    print("  The partial fix under-predicts iff k < sigma_B/sigma_G, i.e. iff")
    print(f"  the alpha ratio exceeds k^2 = {K**2:.5f} - which is exactly the")
    print("  {P2,P3,P4} band that C3 excluded. Same statement, twice.\n")
    print("  worst case over the whole instrument:")
    for arm in ("none", "r6"):
        gp = np.sqrt(0.5 * (var(arm, "G1") + var(arm, "G2")))
        r = np.sqrt(var(arm, "B")) / gp
        i = int(np.argmin(r))
        print(f"    arm {arm:>4s}: min sigma_B/sigma_G over 11 ISOs = {r[i]:.5f} "
              f"(ISO {isos[i]}), margin over k = {100 * (r[i] / K - 1):+.1f}%")
    lo_band = np.sqrt(0.8181)     # 04 E1, lowest of 32 row bands, B/G2
    print(f"    lowest of 04's 32 row bands: sigma ratio {lo_band:.5f}, "
          f"margin over k = {100 * (lo_band / K - 1):+.1f}%")
    print("\n  Does it inherit the withdrawn f?  NO. f is an INTERPRETATION")
    print("  (where in the chain), withdrawn by D1 because it assumed spatial")
    print("  uniformity. The alpha ratio is the MEASUREMENT: E4 showed it is")
    print("  arm-independent and E5 that 0/32 bands reach either hypothesis band.")
    print("  m = 1.09943 is DERIVED from sigma/k, not an independent input, so")
    print("  the partial fix's error is simply X/{:.5f} - 1 for whatever X is".format(SIG))
    print("  written into the gain slot. The 0.9231 is mine; the 0.8396 is M61's,")
    print("  and I did NOT re-measure it (D2 closed the pedestal failure mode only).")

    # ------------------------------------------------------------------- Q2
    print("\n=== Q2a across ISO, dark frames (rho = 1) ===")
    print(f"{'ISO':>5s} {'sigma_B/sigma_G':>16s} {'shipped err':>12s} {'partial err':>12s}")
    gp = np.sqrt(0.5 * (var("none", "G1") + var("none", "G2")))
    r = np.sqrt(var("none", "B")) / gp
    for i, iso in enumerate(isos):
        print(f"{iso:5d} {r[i]:16.5f} {100 * (1.0 / r[i] - 1):+11.1f}% "
              f"{100 * (K / r[i] - 1):+11.1f}%")
    print(f"  shipped spans {100 * (1 / r.max() - 1):+.1f}% .. "
          f"{100 * (1 / r.min() - 1):+.1f}%;  partial spans "
          f"{100 * (K / r.max() - 1):+.1f}% .. {100 * (K / r.min() - 1):+.1f}%")
    print("  Both are material at EVERY ISO. Neither vanishes anywhere in the sweep.")

    print("\n=== Q2b across signal level: rho = read share of the true variance ===")
    print(f"{'rho':>6s} {'shipped var':>12s} {'partial var':>12s} "
          f"{'shipped sig':>12s} {'partial sig':>12s} {'|partial|<|shipped|?':>22s}")
    for rho in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        vs = (1 - rho) / K + rho / ALPHA
        vp = (1 - rho) + rho / M**2
        es, ep = np.sqrt(vs) - 1, np.sqrt(vp) - 1
        print(f"{rho:6.2f} {vs:12.5f} {vp:12.5f} {100 * es:+11.2f}% "
              f"{100 * ep:+11.2f}% {str(abs(ep) < abs(es)):>22s}")
    print("\n  The partial fix makes the SHOT term exactly right (it is a pure")
    print("  gain error) and leaves the READ term under-predicted by")
    print(f"  {100 * (1 / M - 1):+.1f}% in sigma. So its error is strictly SMALLER in")
    print("  magnitude than the shipped model's at every rho < 1, and roughly")
    print("  equal at rho = 1. What changes is the SIGN: shipped errs")
    print("  conservative everywhere, partial errs over-confident everywhere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
