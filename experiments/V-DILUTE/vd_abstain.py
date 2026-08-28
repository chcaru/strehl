# -*- coding: utf-8 -*-
"""Measure the GATE ABSTENTION fraction directly, instead of inferring it.

Round 1 refuted my prediction that the decorrelated floor equals N: measured
58.43 at N=79, not 79. The proposed repair was that pixels where NO frame
clears `gate * beta[k] * var` fall back to the unweighted mean, so the floor is
a blend `phi + (1 - phi) * N`. Solving that for phi gave 0.654 / 0.458 / 0.264
at N = 19 / 39 / 79.

That is an INFERENCE from the number it is meant to explain, which is circular.
This script measures phi independently -- counting, per level, the fraction of
pixels at which the shipping weight stack sums to zero -- and asks whether the
independently measured value reproduces the observed floor. If it does not,
the abstention explanation is wrong and I report the floor as unexplained.

Energy-weighted, because the premium is a power statistic: a level that carries
no energy cannot move it. Weights are the per-level share of reconstructed
noise power, approximated by BETA, which is how the gate floor itself is
scaled in the shipping merge.
"""
from __future__ import print_function

import io
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-NEVERWORSE"))

import vn_pyr as VP                                    # noqa: E402
from vd_prem_lib import (BETA, SHIP, Stack, base_scores, load_green,  # noqa
                         pick, weights_from)


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    ns = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 \
        else [19, 39, 79]
    # Which surface to count on. `twin` is the one the FLOOR is defined on and
    # is what H.2 needs. `real` is the surface the shipping binary's own
    # `averaged` log line reports, and is the only one comparable to it: the
    # twin carries no focus signal, so its coefficients sit at the noise floor
    # by construction and it necessarily abstains more. Measuring the wrong
    # one here would manufacture a disagreement with the shipping log.
    surface = sys.argv[3] if len(sys.argv) > 3 else "twin"

    g = load_green(subj)
    n = len(g)
    var0, read2, gph = VP.fit_variance(g[0])
    sd = np.sqrt(np.maximum(var0, 0.0))
    base = g.mean(axis=0)
    rng = np.random.default_rng(20260827)
    twin_all = np.stack([base + rng.normal(0.0, 1.0, base.shape) * sd
                         for _ in range(n)])
    varp = VP.gauss_pyr(var0, 7)

    print("subject %s   abstention counted on the %s frames\n" % (subj, surface.upper()))
    print("  %3s %6s %9s %9s %9s %9s"
          % ("N", "level", "abstain", "weight", "phi_cum", "floor_pred"))
    for N in ns:
        idx = pick(n, N)
        st = Stack((twin_all if surface == "twin" else g)[idx])
        num = 0.0
        den = 0.0
        for k in range(st.nb):
            L = st.level(k)
            p = VP.exponent_at(k, st.nb, SHIP["exponent"], SHIP["sharpen"])
            floor = SHIP["gate"] * BETA[k] * np.maximum(varp[k], 0.0)
            W = weights_from(base_scores(L), floor, p)
            ab = float(np.mean(W.sum(axis=0) <= 0.0))
            wt = BETA[k]
            num += ab * wt
            den += wt
            print("  %3d %6d %9.4f %9.4f" % (N, k, ab, wt))
            del L, W
        phi = num / den
        print("  %3d %6s %9s %9s %9.4f %9.2f   (observed floor at this N is "
              "the `random` arm)" % (N, "-", "-", "-", phi,
                                     phi + (1.0 - phi) * N))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
