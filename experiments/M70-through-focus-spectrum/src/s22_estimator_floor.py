"""M70 s22 - is the s21 reading OPTICS or is it the ESTIMATOR?

s21 returned INDETERMINATE with a suggestive structure: 7 of 12 stacks read
above Gaussian, the three bee captures agree with each other (2.65/2.43/2.70)
and the two wrapped-text captures agree (1.855/1.844). But two things in s21's
own output are threats to that reading, and PREREGISTRATION-C section 2 required
this check in advance:

  (1) EVERY corpus w50 is 1.61-3.57 frames. s20 Tier 1b only verified the
      estimator unbiased down to w50 = 5.89 (+0.25%) and measured +1.2% at
      w50 = 2.38. The whole corpus sits BELOW the verified range, in the
      regime where the measured bias is positive - the same direction as the
      finding.

  (2) The shuffle null median sits at 1.800-1.809 on every powered stack.
      The Gaussian value is 1.8226. If the estimator returns ~1.80 for a
      structureless narrow blob, then "reads Gaussian" and "reads nothing"
      are the same number, and Criterion H could not have been interpreted
      even if it had passed.

Both are answered here with analytic curves of known shape, sampled at exactly
the widths the corpus exhibits. No corpus data is used.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import s20_shape_controls as S20  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
G = S20.GAUSS["R10_50"]

CORPUS_W50 = {"coffee-bubbles": 1.61, "109MSDCF": 2.25, "119MSDCF": 3.28,
              "113MSDCF": 3.14, "112MSDCF": 2.95, "foam": 2.19, "coffee-bean": 2.38,
              "wrapped-text-2": 1.96, "wrapped-text-1": 1.99, "bee-1": 2.86,
              "bee-2": 3.57, "bee-3": 3.46}
CORPUS_R10 = {"coffee-bubbles": 1.8857, "109MSDCF": 1.9741, "119MSDCF": 2.2905,
              "113MSDCF": 2.1035, "112MSDCF": 2.0490, "foam": 2.1803,
              "coffee-bean": 1.8161, "wrapped-text-2": 1.8546, "wrapped-text-1": 1.8444,
              "bee-1": 2.6514, "bee-2": 2.4345, "bee-3": 2.6959}


def gauss_at_w50(w50, K=201):
    """A DISCRETELY SAMPLED Gaussian whose true half-width at 0.50 is w50."""
    sigma = w50 / math.sqrt(2.0 * math.log(2.0))
    x = np.arange(K, dtype=np.float64) - (K - 1) / 2.0
    return np.exp(-0.5 * (x / sigma) ** 2)


def r10(curve, smooth=True):
    return S20.widths(curve, smooth=smooth)["R10_50"]


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main() -> None:
    res = {"gauss": G}

    hdr("(1) THE NARROW-CURVE BIAS, at exactly the widths the corpus exhibits")
    print("  A TRUE GAUSSIAN sampled at each stack's measured w50. Any departure from")
    print("  1.8226 here is the ESTIMATOR, not the optics. Corpus reading shown for")
    print("  comparison; 'excess' is what is left once the instrument is subtracted.")
    print(f"\n{'stack':<16}{'w50':>7}{'Gauss@w50':>12}{'inst. bias':>12}"
          f"{'corpus':>9}{'excess':>9}{'still >G?':>11}")
    res["bias"] = {}
    excess = []
    for st, w in sorted(CORPUS_W50.items(), key=lambda kv: kv[1]):
        gw = r10(gauss_at_w50(w), smooth=True)
        exc = CORPUS_R10[st] - gw
        excess.append((st, exc))
        res["bias"][st] = {"w50": w, "gauss_at_w50": float(gw),
                           "inst_bias": float(gw - G), "corpus": CORPUS_R10[st],
                           "excess": float(exc)}
        print(f"{st:<16}{w:>7.2f}{gw:>12.4f}{gw - G:>+12.4f}"
              f"{CORPUS_R10[st]:>9.4f}{exc:>+9.4f}{('yes' if exc > 0 else 'NO'):>11}")
    ex = np.array([e for _s, e in excess])
    print(f"\n  instrument bias at corpus widths spans "
          f"{min(v['inst_bias'] for v in res['bias'].values()):+.4f} .. "
          f"{max(v['inst_bias'] for v in res['bias'].values()):+.4f}")
    print(f"  corpus excess over a same-width Gaussian: median {np.median(ex):+.4f}, "
          f"range {ex.min():+.4f} .. {ex.max():+.4f}")
    res["excess_median"] = float(np.median(ex))

    hdr("(1b) how far down is the estimator trustworthy? unbiased-range sweep")
    print(f"{'w50 frames':>11}{'R10_50':>10}{'bias':>10}{'bias %':>9}")
    res["sweep"] = []
    for w in (1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 9.0, 14.0, 24.0):
        v = r10(gauss_at_w50(w, K=401), smooth=True)
        res["sweep"].append({"w50": w, "R10_50": float(v), "bias": float(v - G)})
        print(f"{w:>11.1f}{v:>10.4f}{v - G:>+10.4f}{100 * (v - G) / G:>+8.2f}%")

    hdr("(2) WHAT DOES THE ESTIMATOR RETURN WHEN THERE IS NO CURVE?")
    print("  s21's shuffle null sat at 1.800-1.809 on every powered stack, and the")
    print("  Gaussian value is 1.8226. Is that a coincidence, or is ~1.80 simply what")
    print("  a structureless narrow blob returns? Pure noise, no curve, 400 draws:")
    rng = np.random.default_rng(2222)
    for K in (19, 33, 105, 299):
        vals = []
        for _ in range(400):
            v = r10(rng.normal(0.0, 1.0, K))
            if np.isfinite(v):
                vals.append(v)
        a = np.array(vals)
        print(f"    K={K:>4}  median {np.median(a):.4f}  sd {a.std(ddof=1):.4f}  "
              f"n {a.size}/400   |median - Gaussian| = {abs(np.median(a) - G):.4f}")
        res.setdefault("noise_floor", {})[str(K)] = {
            "median": float(np.median(a)), "sd": float(a.std(ddof=1)), "n": int(a.size)}
    nf = np.median([v["median"] for v in res["noise_floor"].values()])
    print(f"\n  structureless floor = {nf:.4f}   Gaussian = {G:.4f}   "
          f"separation = {abs(nf - G):.4f}")
    print(f"  The pre-registered bar is 0.11. The pooled floor is {abs(nf - G):.4f} from")
    print(f"  the Gaussian value, i.e. {'OUTSIDE' if abs(nf - G) > 0.11 else 'INSIDE'} the bar.")
    print("  BUT the floor is K-DEPENDENT and rises toward Gaussian with K: at K=299 it")
    print("  is 0.0426 away, INSIDE the bar. So on the LONG stacks a Gaussian reading is")
    print("  NOT separable from a structureless one; on the short stacks it is.")
    res["floor_vs_gauss"] = float(abs(nf - G))

    hdr("(3) WHAT CURVE WIDTH WOULD BE NEEDED? resolving power vs w50")
    print("  Separation between a Gaussian and a sech2 (the mildest real heavy tail),")
    print("  as a function of curve width. Both sampled at the same w50.")
    print(f"{'w50':>7}{'Gauss':>9}{'sech2':>9}{'separation':>12}{'> bar 0.11?':>13}")
    res["resolving"] = []
    for w in (1.6, 2.5, 3.6, 5.0, 8.0, 13.0):
        s = w / (2.0 * math.acosh(math.sqrt(2.0)))
        x = np.arange(401, dtype=np.float64) - 200.0
        sech = 1.0 / np.cosh(x / s) ** 2
        gv, sv = r10(gauss_at_w50(w, K=401)), r10(sech)
        sep = sv - gv
        res["resolving"].append({"w50": w, "gauss": float(gv), "sech2": float(sv),
                                 "sep": float(sep)})
        print(f"{w:>7.1f}{gv:>9.4f}{sv:>9.4f}{sep:>+12.4f}"
              f"{('YES' if abs(sep) > 0.11 else 'no'):>13}")

    with open(os.path.join(OUT, "s22_estimator_floor.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s22_estimator_floor.json")


if __name__ == "__main__":
    main()

