"""R1: form a shrunk response map from self-flat.py's accumulators.

  python -X utf8 self-flat-shrink.py OUT.npy KAPPA_R,KAPPA_G,KAPPA_B ACC_PREFIX [ACC_PREFIX ...]

ACC_PREFIX-num.npy and -den.npy are sum(w r) and sum(w) per photosite
([4, H/2, W/2], R G1 G2 B; w = 1 / variance of one sample's r). With a
zero-mean prior of standard deviation kappa (fraction of level) on a
photosite's response error, the posterior mean is

    map = sum(w r) / (sum(w) + 1 / kappa^2)

so a photosite seen often keeps its estimate and one seen rarely is pulled
to zero (no correction) instead of receiving a noisy one. Several prefixes
are summed (the whole stack from its parts). KAPPA 0 writes the unshrunk
ratio (control).
"""
import sys

import numpy as np


def main():
    out = sys.argv[1]
    kap = [float(v) for v in sys.argv[2].split(',')]
    kap = [kap[0], kap[1], kap[1], kap[2]]
    num = sum(np.load(p + '-num.npy').astype(np.float64) for p in sys.argv[3:])
    den = sum(np.load(p + '-den.npy').astype(np.float64) for p in sys.argv[3:])
    res = np.zeros_like(num, dtype=np.float32)
    for i in range(4):
        prior = 0.0 if kap[i] == 0 else 1.0 / kap[i] ** 2
        res[i] = (num[i] / np.maximum(den[i] + prior, 1e-20)).astype(np.float32)
        # posterior sd relative to the prior's: how much of each photosite's correction is trusted
        trust = den[i] / np.maximum(den[i] + prior, 1e-20)
        print(f'plane {i}: map sd {100 * res[i].std():.3f} %, median trust {np.median(trust):.3f}, share with trust under 0.5: {100 * (trust < 0.5).mean():.1f} %')
    np.save(out, res)


if __name__ == '__main__':
    main()
