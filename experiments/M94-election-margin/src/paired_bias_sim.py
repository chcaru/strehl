"""Is the paired real-vs-permuted statistic unbiased under exchangeability?

Independently re-derived, in numpy, with no strehl code involved. Draw N i.i.d.
values per pixel (so the frame ORDER carries no information at all), apply two
independent uniform permutations, and compute the same `m_d` the Rust
instrument computes. Under exchangeability the win rate among decided pairs
must be 50%.

If this reports ~50%, the Rust null's 69% is a bug in the Rust RNG or wiring.
If this reports ~69%, the *statistic itself* is biased and the Rust null is
correct to report it.
"""

import numpy as np

RNG = np.random.default_rng(20260101)
NPIX = 200_000


def m_d(vals: np.ndarray, d: int) -> np.ndarray:
    """`R_win - max R_k over |k - k_win| >= d`, per row. NaN where undefined."""
    n = vals.shape[1]
    kwin = vals.argmax(axis=1)
    win = vals[np.arange(len(vals)), kwin]
    k = np.arange(n)[None, :]
    far = np.abs(k - kwin[:, None]) >= d
    masked = np.where(far, vals, -np.inf)
    hi = masked.max(axis=1)
    out = win - hi
    out[~np.isfinite(hi)] = np.nan
    return out


def one(n_frames: int, dists=(1, 2, 4, 8, 16)) -> None:
    base = RNG.normal(size=(NPIX, n_frames)).astype(np.float32)
    pa = RNG.permutation(n_frames)
    pb = RNG.permutation(n_frames)
    a = base[:, pa]
    b = base[:, pb]
    print(f"--- N = {n_frames} frames, {NPIX} pixels, i.i.d. normal (order is pure noise) ---")
    for d in dists:
        ma, mb = m_d(a, d), m_d(b, d)
        ok = np.isfinite(ma) & np.isfinite(mb)
        wins = int((ma[ok] > mb[ok]).sum())
        loss = int((ma[ok] < mb[ok]).sum())
        ties = int((ma[ok] == mb[ok]).sum())
        wl = 100.0 * wins / max(wins + loss, 1)
        print(
            f"  d={d:<3} n={int(ok.sum()):8}  wins {wins:8}  losses {loss:8} "
            f" ties {ties:8}  w/(w+l) {wl:7.3f}%"
        )


for nf in (22, 100, 299):
    one(nf)
    print()
