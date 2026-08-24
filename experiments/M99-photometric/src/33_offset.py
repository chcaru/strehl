"""Does the per-frame photometric term need an OFFSET, or only a gain?

An unnecessary offset eats real signal, so it has to be earned. Fit, per frame,
the scene-fixed patch levels against the reference frame's levels across the
whole candidate grid -- 294 patches spanning roughly 0.02 to 0.85 of the usable
range, which is enough lever arm to separate a slope from an intercept:

    L_p(k) = alpha_k + beta_k * L_p(ref)

If the drift is a pure gain, alpha_k is zero. The units are DN so the answer can
be compared against the read-noise floor directly.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module  # noqa: E402

A = import_module("21_phaseA")

# A7C II: black 512, white 16383 as decoded; the usable range strehl models is
# 15360-512, but the levels here are normalised by rawpy's own (white - black).
RANGE_DN = 16383.0 - 512.0


def main(stack):
    z = A.load(stack)
    scene, smad = z["scene"], z["scene_mad"]
    ref = int(z["ref"])
    ok = np.isfinite(scene).all(axis=0) & (scene > 0.005).all(axis=0)
    S = scene[:, ok]
    n, p = S.shape
    x = S[ref]
    alphas = np.empty(n)
    betas = np.empty(n)
    res = np.empty(n)
    for k in range(n):
        Xd = np.column_stack([np.ones(p), x])
        b, *_ = np.linalg.lstsq(Xd, S[k], rcond=None)
        alphas[k] = b[0]
        betas[k] = b[1]
        res[k] = np.sqrt(np.mean((S[k] - Xd @ b) ** 2))
    # Gain-only fit, for comparison.
    beta0 = np.array([float(x @ S[k] / (x @ x)) for k in range(n)])
    res0 = np.array([np.sqrt(np.mean((S[k] - beta0[k] * x) ** 2))
                     for k in range(n)])

    print("=" * 70)
    print("%s  n=%d frames, %d patches, level range %.4f..%.4f"
          % (stack, n, p, S.min(), S.max()))
    print("  gain+offset: beta %.4f..%.4f   alpha %+.5f..%+.5f "
          "(%.1f..%.1f DN)"
          % (betas.min(), betas.max(), alphas.min(), alphas.max(),
             alphas.min() * RANGE_DN, alphas.max() * RANGE_DN))
    print("  |alpha| max = %.5f of range = %.1f DN" %
          (np.abs(alphas).max(), np.abs(alphas).max() * RANGE_DN))
    print("  residual RMS: gain-only %.5f  gain+offset %.5f  "
          "improvement %.1f%%"
          % (res0.mean(), res.mean(), 100 * (1 - res.mean() / res0.mean())))
    print("  offset as a fraction of the gain effect: "
          "max|alpha| / (median level * max|beta-1|) = %.3f"
          % (np.abs(alphas).max()
             / (np.median(x) * max(1e-9, np.abs(betas - 1).max()))))


if __name__ == "__main__":
    for s in sys.argv[1:] or ["lavendar-cpl", "leaf-2-cpl", "bee-3-cpl",
                              "bee-2-cpl"]:
        main(s)
