"""M66 shared measurement kernel - the admission rule, and nothing else.

`n_eff(cube, idx, gates)` is a transcription of `merge.rs`:

    best  = max over the admitted frame list          FocusStats::best_focus
    n_eff = #{k in idx : best - cube[k] <= tol}        Estimator::fold + Gate::admits
    tol   = f32(T) * f32(sqrt 2) * f32(FOCUS_NOISE_SD) Gate::tolerance

Arithmetic is f32 on both sides of the comparison, as in the crate. The frame
list is the ONLY thing that varies across this milestone's sweep.
"""

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from m66 import FOCUS_NOISE_SD  # noqa: E402

SQRT2_F32 = np.float32(np.sqrt(np.float32(2.0)))
FNSD_F32 = np.float32(FOCUS_NOISE_SD)


def tolerance(gate):
    return np.float32(np.float32(gate) * SQRT2_F32 * FNSD_F32)


def n_eff(cube, idx, gates):
    """cube: (N, P) float32. idx: frame indices. Returns dict gate -> stats."""
    idx = np.asarray(idx, dtype=np.int64)
    best = cube[idx[0]].copy()
    for k in idx[1:]:
        np.maximum(best, cube[k], out=best)
    tols = [tolerance(g) for g in gates]
    counts = [np.zeros(cube.shape[1], dtype=np.int32) for _ in gates]
    max_gap = np.float32(0.0)
    for k in idx:
        gap = best - cube[k]
        m = gap.max()
        if m > max_gap:
            max_gap = m
        for c, t in zip(counts, tols):
            c += gap <= t
    out = {}
    n = len(idx)
    for g, t, c in zip(gates, tols, counts):
        mean = float(c.mean())
        out[g] = {
            "tol": float(t),
            "mean_n_eff": mean,
            "n_eff_over_N": mean / n,
            "frac_n1": float((c == 1).mean()),
            "N": n,
        }
    return out, float(max_gap)


def subset(mode, n_total, n, rep=0):
    """prefix / stride / random frame lists of size n out of n_total."""
    if n >= n_total:
        return np.arange(n_total)
    if mode == "prefix":
        return np.arange(n)
    if mode == "stride":
        return np.unique(np.round(np.linspace(0, n_total - 1, n)).astype(np.int64))
    if mode == "random":
        rng = np.random.default_rng(660000 + 1000 * n + rep)
        return np.sort(rng.choice(n_total, size=n, replace=False))
    raise ValueError(mode)


def load(stack, data_dir, kind="d4"):
    a = np.load(data_dir / f"{stack}-{kind}.npy", mmap_mode="r")
    return np.ascontiguousarray(a).reshape(a.shape[0], -1)
