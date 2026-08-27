"""noisediag -- is fullhp's NOISE-PROP failure a BIAS or is it VARIANCE?

NOISE-PROP has now read -4.9%, +15.1% and +20.3% under three different noise
estimators, and its UNMATCHED companion reads 0.9833 throughout.  Swings that
large under changes that should be second-order are the signature of an
estimator with a wide sampling distribution, not of three different biases --
but "looks like variance" is not a measurement.

A commissioning arm compared against a fixed 10% gate with no notion of its own
sampling spread cannot tell a broken instrument from a noisy one.  This settles
it by running the arm over many independent noise realisations and reading the
spread, and by sweeping the plant's potency.

WHY POTENCY MATTERS HERE.  `mut_noise_prop(beta)` adds sigma = beta * tile mean,
so in contrast units every tile gains exactly beta^2 * pi*(hi^2 - lo^2) of band
power regardless of level.  At beta = 0.04 that is 1.13e-04 against a DETAIL
median of 2.40e-05 -- the plant is nearly FIVE TIMES the signal it is planted
on, so the scene term becomes a difference of two large nearly-equal numbers and
any relative error in the noise estimate is amplified by ~10x.  A plant can be
too potent to be informative, which is not a failure mode this lane had met.

    python noisediag.py [key=119] [nseed=12]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
from h2h2b import Comp                                           # noqa: E402

import hd2                                                       # noqa: E402
from fullhp import (BAND, W, mut_noise_abs, mut_noise_prop,      # noqa: E402
                    ratio_of, scene_matched, scene_unmatched, tiles)


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    nseed = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    arm = os.path.join(hd2.ROOT, key, "arms")
    S = Comp(dict(path=os.path.join(arm, "strehl-full.tiff"), weights=W))
    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    lvD, bpD = tiles(S, DET, BAND)
    lvF, bpF = tiles(S, FLAT, BAND)
    base_d, _, _ = scene_matched(lvD, bpD, lvF, bpF)
    base_S = float(np.median(base_d))
    base_un = scene_unmatched(bpD, bpF)
    frac = np.pi * (BAND[1] ** 2 - BAND[0] ** 2)

    print("=" * 96)
    print(f"NOISEDIAG -- bias or variance in fullhp's noise arms, {key}")
    print("=" * 96)
    print(f"  strehl base: bp DETAIL median {np.median(bpD):.4e}  "
          f"FLAT median {np.median(bpF):.4e}  matched S {base_S:.4e}")
    print(f"  annulus area fraction {frac:.4f}; a plant of sigma = beta*level "
          f"adds beta^2*{frac:.4f} to every tile")
    print(f"\n  {'arm':12s} {'beta':>6s} {'added a':>10s} {'a/S':>7s} "
          f"{'mean':>8s} {'sd':>7s} {'min':>8s} {'max':>8s} {'uncorr':>8s}  "
          f"reading")

    for label, mk in (("NOISE-PROP", mut_noise_prop),
                      ("NOISE-ABS", None)):
        for beta in (0.005, 0.010, 0.020, 0.0212, 0.024, 0.028, 0.032, 0.040):
            a = beta * beta * frac
            vals, uncs, unms = [], [], []
            for sd in range(nseed):
                if label == "NOISE-PROP":
                    mut = mut_noise_prop(beta)
                else:
                    mut = mut_noise_abs(beta * float(np.median(lvD)))
                mlv, mbp = tiles(S, DET, BAND, mutate=mut,
                                 rng=np.random.default_rng(1000 + sd))
                mlvF, mbpF = tiles(S, FLAT, BAND, mutate=mut,
                                   rng=np.random.default_rng(2000 + sd))
                md, _, _ = scene_matched(mlv, mbp, mlvF, mbpF)
                vals.append(ratio_of(base_S, float(np.median(md))))
                uncs.append(float(np.sqrt(np.median(mbp) / np.median(bpD))))
                unms.append(ratio_of(base_un, scene_unmatched(mbp, mbpF)))
            v = np.array(vals, float)
            good = np.isfinite(v)
            mu, sd_ = float(v[good].mean()), float(v[good].std(ddof=1))
            se = sd_ / np.sqrt(good.sum())
            biased = abs(mu - 1.0) > 2 * se
            read = (f"BIAS {mu - 1:+.1%} (>2se)" if biased
                    else f"consistent with 1.000 (2se = {2*se:.3f})")
            print(f"  {label:12s} {beta:6.3f} {a:10.3e} "
                  f"{a/base_S:7.2f} {mu:8.4f} {sd_:7.4f} "
                  f"{v[good].min():8.4f} {v[good].max():8.4f} "
                  f"{np.mean(uncs):8.4f}  {read}")
    print()
    print("  NOTE: 'a/S' is how many times the plant exceeds the signal it is "
          "planted on.")
    print("  A plant far above 1 turns the scene term into a difference of two "
          "large nearly-")
    print("  equal numbers and inflates the estimator's variance without "
          "testing it any harder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
