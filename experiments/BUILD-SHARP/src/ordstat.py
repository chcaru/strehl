"""What does an upper-envelope estimator cost, before anyone renders anything?

BUILD-HALO's veiling fix replaces (at background pixels) a gated MEAN over ~166.8
of 299 frames with an upper ENVELOPE -- a high per-pixel percentile, reported as
recovering essentially the whole aura from just 3 of 205 frames.

A maximum is not an unbiased estimator of a mean.  Over n independent samples of
noise with standard deviation sigma it carries a POSITIVE bias, and it is noisier
than a mean over the same samples.  Both matter here and they matter in opposite
ways:

  * the bias is UPWARD, and the defect being removed is a DARKENING.  So an
    undebiased envelope removes some of the veil arithmetically rather than
    physically, and would show an improvement even on a stack with no veil at all.
  * the variance cost is paid in the background, which is exactly where the
    project's other open defect (mottling) lives.

This script prints both, by Monte Carlo, so the prediction exists in writing BEFORE
the fix is measured.  The discriminator between "removed the veil" and "biased the
estimate upward" is the placebo: 109MSDCF has no depth separation and therefore no
veil, so any background level shift there is bias.
"""

from __future__ import annotations

import numpy as np

RNG = np.random.default_rng(11)
TRIALS = 400_000


def stats(n: int, kind: str = "max") -> tuple[float, float]:
    """Mean and sd of the estimator over n unit-variance normal samples."""
    x = RNG.normal(0.0, 1.0, (TRIALS, n))
    v = x.max(axis=1) if kind == "max" else x.mean(axis=1)
    return float(v.mean()), float(v.std())


def main() -> None:
    print("Estimator behaviour on unit-variance noise (Monte Carlo, "
          f"{TRIALS:,} trials)\n")
    print("  n     E[max]      sd[max]     sd[mean]    max noisier by")
    for n in (2, 3, 4, 5, 10, 30, 167, 205):
        bm, bs = stats(n, "max")
        _, ms = stats(n, "mean")
        print(f"{n:5d}   {bm:+8.4f}    {bs:8.4f}    {ms:8.4f}    {bs/ms:8.2f}x")

    print("\nThe comparison that matters for the veiling fix:")
    b3, s3 = stats(3, "max")
    ship_sd = 1.0 / np.sqrt(166.8)
    print(f"  shipped gated mean over 166.8 frames : bias  +0.0000 sigma, "
          f"sd {ship_sd:.4f} sigma")
    print(f"  upper envelope of 3 frames           : bias {b3:+.4f} sigma, "
          f"sd {s3:.4f} sigma")
    print(f"  -> envelope is {s3/ship_sd:.1f}x NOISIER and {b3:+.3f} sigma "
          f"BRIGHTER before any veil is removed")

    print("\nPredicted background level shift on a veil-free stack (the placebo),")
    print("for a range of plausible per-frame background noise levels:")
    print("   sigma_frame (DN)    predicted bias (DN)")
    for sig in (50, 100, 200, 400, 800):
        print(f"   {sig:12d}        {b3*sig:+14.1f}")
    print("\nAcceptance consequence: on 109MSDCF, whose aura is only -177 DN and")
    print("which has no depth separation, a debiased envelope should shift the")
    print("background by ~0 DN.  A shift of order +b*sigma_frame is the signature")
    print("of an undebiased order statistic and would mean part of the reported")
    print("flower-bud improvement is arithmetic, not physical.")


if __name__ == "__main__":
    main()
