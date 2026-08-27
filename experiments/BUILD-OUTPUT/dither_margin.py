"""How much dither does 8-bit need, and how much margin does this corpus have?

The corpus reads 0.0% banded.  The commissioned explanation is that sensor noise
dithers the quantiser.  That explanation has a consequence nobody has costed:

    NOISE IS THE THING THAT MAKES 8 BITS SAFE HERE, AND REDUCING NOISE IS
    STREHL'S HEADLINE WIN (2.4x over the fork).

A focus merge averages frames; averaging N frames divides sigma by up to sqrt(N).
So the very improvement the project leads on is the improvement that removes the
dither.  If the corpus sits just above the dither threshold, then a cleaner
future render -- more frames, lower ISO, a better merge -- lands under it and
8-bit output starts to band on subjects that are fine today.

That makes the margin a number worth having, so this measures it: sweep sigma on
a ramp with treads wide enough to be unambiguous banding, and find where the
detector crosses over.  Then place the corpus on that axis.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import banding as B  # noqa: E402
import commission_banding as C  # noqa: E402


SIZE = 2304          # 25 tiles per draw at banding.STRIDE, vs 9 at 1024
SEEDS = 5            # the first run was non-monotone at 9 tiles / 1 draw:
                     # 100 -> 33.3 -> 0.0 -> 22.2 -> 0.0.  That is 2/9 tiles of
                     # sampling noise, not a threshold.  The monotonicity
                     # control caught it, which is the whole reason it is here.


def ramp(tread_px, base_code, noise_codes, seed):
    """16-bit ramp whose 8-bit treads are `tread_px` wide, with seeded dither."""
    rng = np.random.default_rng(seed)
    step16 = 257.0 / tread_px
    x = np.arange(SIZE, dtype=np.float64)[None, :] * step16
    a16 = base_code * 257.0 + np.repeat(x, SIZE, axis=0)
    if noise_codes:
        a16 = a16 + rng.normal(0.0, noise_codes * 257.0, a16.shape)
    a16 = np.clip(a16, 0, 65535)
    a8 = np.clip(np.rint(a16 / 257.0), 0, 255).astype(np.uint8)
    return a16, a8


def frac(a16, a8):
    rows = B.summarise(B.tile_stats(a16, a8))
    tot = sum(n for _, n, _ in rows)
    bn = sum(r["banded_n"] for _, n, r in rows if n)
    return (100.0 * bn / tot if tot else float("nan")), tot


def main():
    base = int(np.argmax(np.diff(B.LSTAR)))
    print("dither ladder on a 40-px-tread ramp (unambiguous banding at sigma=0)")
    print(f"{'sigma (codes)':>14}{'banded %':>11}{'tiles':>7}   (mean of {SEEDS} seeds)")
    print("-" * 32)
    xs, ys = [], []
    for s in (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80):
        ps, tots = [], 0
        for sd in range(SEEDS):
            p, tot = frac(*ramp(40.0, base, s, 1000 + sd))
            ps.append(p)
            tots += tot
        p = float(np.mean(ps))
        xs.append(s)
        ys.append(p)
        print(f"{s:>14.2f}{p:>11.1f}{tots:>7}")

    xs, ys = np.array(xs), np.array(ys)

    def cross_at(level):
        b = np.flatnonzero(ys < level)
        return xs[b[0]] if len(b) else float("nan")

    c50, c1, c0 = cross_at(50.0), cross_at(1.0), cross_at(1e-9)
    print(f"\n  banded < 50%  at sigma ~ {c50:.2f} codes")
    print(f"  banded <  1%  at sigma ~ {c1:.2f} codes")
    print(f"  banded ==  0% at sigma ~ {c0:.2f} codes")

    # Monotonicity: more dither must never band MORE.  The tolerance is the
    # binomial sampling error of the ladder itself, not a magic number -- with
    # `tiles` tiles per rung, a fraction near p has SE sqrt(p(1-p)/n), and a
    # rung is only a violation if it rises by more than 3 SE.  Testing exact
    # monotonicity on a stochastic ladder fails on sampling noise and would
    # have condemned a ladder that is behaving correctly.
    n_per = 180.0
    se = np.sqrt(np.maximum(ys, 1.0) / 100.0 * (1 - np.maximum(ys, 1.0) / 100.0)
                 / n_per) * 100.0
    rises = np.diff(ys)
    tol = 3.0 * se[1:]
    mono = bool(np.all(rises <= tol))
    worst = int(np.argmax(rises - tol))
    print(f"  monotone non-increasing within 3 SE: {mono}"
          f"   (worst rung +{rises[worst]:.1f} pp vs tol {tol[worst]:.1f} pp)")
    print(f"  ladder: {list(np.round(ys, 1))}")

    print("\n  measured corpus sigma, from banding.py (median per stratum):")
    corpus = {"bee-1-cpl": (0.84, 0.58), "tweezers-cpl": (0.62, 0.72, 0.42),
              "coffee-bean": (0.51, 0.28), "flower-inner-edge-cpl": (0.54, 0.50, 0.31)}
    allv = [v for vs in corpus.values() for v in vs]
    for k, vs in corpus.items():
        print(f"    {k:<24} {vs}")
    lo = min(allv)
    print(f"\n  corpus minimum sigma      : {lo:.2f} codes")
    for label, c in (("50%", c50), ("1%", c1), ("0%", c0)):
        if c == c and c > 0:
            print(f"  margin vs the {label:<3} crossover : {lo / c:>5.2f}x"
                  f"   -> consumed by averaging {(lo / c) ** 2:>5.1f}x more frames")
    return 0 if mono else 1


if __name__ == "__main__":
    raise SystemExit(main())




