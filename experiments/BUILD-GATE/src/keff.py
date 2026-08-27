"""Where does the SHIPPING configuration sit on the swept gate line?

WS4 measured that the shipping band-0 floor is 1.1787x too low on the arm that
actually ships, so the gate constant the product effectively enforced was not
k=2.0 but roughly 2.0/1.1787 = 1.697.

That is an inference from the floor arithmetic. This script tests it against the
sweep, which knows nothing about beta: interpolate the measured sweep to find
the k whose sharpness equals the shipping arm's, and independently the k whose
NOISE equals it. The two axes are different physics -- one is measured on the
three most textured sites against a per-site focus ceiling, the other on the
flattest decile against nothing at all. If they land on the same k, the sweep
and the floor arithmetic are describing the same object.

WHAT THIS IS NOT

It is not a claim that the shipping arm IS k_eff. Fact 631 forbids that: gate
rescaling does not reproduce another configuration's decisions, because beta is
per-frame and per-band while k is global, so no single k can reproduce a
per-frame error. The prediction is therefore that k_eff lands NEAR 1.697 and
NOT exactly on it, and a suspiciously exact hit would be evidence of a
book-keeping error rather than of success.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ceiling import score                                        # noqa: E402
from acuity import luma as aluma, tiles, stats                   # noqa: E402

SWEEP = r"C:\dev\strehl-out\BUILD-GATE\sweep"
CEIL = r"C:\dev\strehl-out\BUILD-GATE\ceil"
KS = [("G100", 1.0), ("G140", 1.4), ("G170", 1.7), ("G200", 2.0),
      ("G300", 3.0), ("G400", 4.0)]
BETA_ERR = 1.1787
PREDICTED = 2.0 / BETA_ERR


def invert(ks, ys, target):
    """k at which the curve y(k) crosses target, plus the number of crossings.

    Returning the FIRST crossing would be a silent lie on a non-monotone curve:
    the answer would depend on which end the scan started from. 119MSDCF's noise
    curve is genuinely non-monotone near k=1.0 (G100 reads BELOW the shipping
    arm), so it has two roots and neither is 'the' effective k. The count is
    returned so the caller can refuse to average an ambiguous estimate rather
    than quietly folding an artifact into the mean.
    """
    ks = np.asarray(ks, float)
    ys = np.asarray(ys, float)
    roots = []
    for i in range(len(ks) - 1):
        a, b = ys[i], ys[i + 1]
        if (a - target) * (b - target) <= 0 and a != b:
            roots.append(float(ks[i] + (ks[i + 1] - ks[i]) * (a - target) / (a - b)))
    if not roots:
        return float("nan"), 0
    return roots[-1], len(roots)


def main():
    print("prediction from the floor arithmetic: k_eff = 2.0/%.4f = %.3f" % (BETA_ERR, PREDICTED))
    print("(fact 631: expect NEAR, not EXACT -- beta is per-frame, k is global)\n")
    print("%-22s %10s %10s %10s" % ("subject", "k_eff(sharp)", "k_eff(noise)", "spread"))
    rows = []
    for subject in sys.argv[1:]:
        cz = np.load(os.path.join(CEIL, "%s.npz" % subject), allow_pickle=True)
        flat_idx, sharp_idx = tiles(aluma(os.path.join(SWEEP, "G200", "%s.tiff" % subject)))
        ks, sh, no = [], [], []
        for arm, k in KS:
            p = os.path.join(SWEEP, arm, "%s.tiff" % subject)
            r, _, _, _ = score(p, cz)
            f, _ = stats(aluma(p), flat_idx, sharp_idx)
            ks.append(k)
            sh.append(r)
            no.append(f)
        w = os.path.join(SWEEP, "WHITE200", "%s.tiff" % subject)
        rs, _, _, _ = score(w, cz)
        fs, _ = stats(aluma(w), flat_idx, sharp_idx)
        a, na = invert(ks, sh, rs)
        b, nb = invert(ks, no, fs)
        amb = (na > 1) or (nb > 1)
        rows.append((subject, a, b, amb))
        print("%-22s %10.3f %10.3f %10.3f   %s"
              % (subject, a, b, abs(a - b),
                 ("AMBIGUOUS: %d/%d crossings - EXCLUDED" % (na, nb)) if amb else ""))
    fin = [r for r in rows if np.isfinite(r[1]) and np.isfinite(r[2]) and not r[3]]
    allk = [v for _, a, b, _ in fin for v in (a, b)]
    print("\nmean k_eff over %d unambiguous estimates = %.3f  (sd %.3f)"
          % (len(allk), float(np.mean(allk)), float(np.std(allk))))
    print("predicted %.3f -> discrepancy %+.1f%%"
          % (PREDICTED, 100.0 * (float(np.mean(allk)) / PREDICTED - 1.0)))
    print("\nagreement between the two axes is the real result: they share no "
          "tiles,\nno reference and no physics, so a common k is not built in.")


if __name__ == "__main__":
    main()
