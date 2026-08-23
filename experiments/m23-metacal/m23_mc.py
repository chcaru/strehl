"""M23 shared helpers: read the metacal CSV, form the response, apply it.

Kept separate from `m23_lib.py` (which is M10's transform algebra, copied
verbatim through M12) so the copied code and the new code never mix.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass

import numpy as np

PRIMARY_DELTA = 2e-4  # registered in PREREGISTRATION.md section 1.2


@dataclass
class MC:
    """One (edge, delta) response measurement."""

    case: str
    cfg: str
    i: int
    j: int
    span: int
    delta: float
    l0: float           # log|a| of the base fit  -- the quantity being corrected
    rms0: float
    used0: int
    lever0: float
    peak0: float
    l_plus: float
    l_minus: float
    r_two: float
    r_plus: float
    r_minus: float
    used_plus: int
    used_minus: int


def _f(v, d=float("nan")):
    return d if v is None or v == "" else float(v)


def read_metacal(path: str, cfg: str | None = None) -> list[MC]:
    out: list[MC] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if cfg is not None and r["cfg"] != cfg:
                continue
            if r["l0"] == "" or r["r_two"] == "":
                continue
            out.append(
                MC(
                    case=r["case"],
                    cfg=r["cfg"],
                    i=int(r["ref"]),
                    j=int(r["mov"]),
                    span=int(r["span"]),
                    delta=float(r["delta"]),
                    l0=float(r["l0"]),
                    rms0=_f(r["rms0"]),
                    used0=int(r["used0"]),
                    lever0=_f(r["lever0"]),
                    peak0=_f(r["peak0"]),
                    l_plus=_f(r["l_plus"]),
                    l_minus=_f(r["l_minus"]),
                    r_two=float(r["r_two"]),
                    r_plus=_f(r["r_plus"]),
                    r_minus=_f(r["r_minus"]),
                    used_plus=int(r["used_plus"]),
                    used_minus=int(r["used_minus"]),
                )
            )
    return out


def by_delta(rows: list[MC], delta: float) -> list[MC]:
    return [r for r in rows if abs(r.delta - delta) < 1e-12]


def by_span(rows: list[MC], span: int) -> list[MC]:
    return [r for r in rows if r.span == span]


def q(v, p):
    return float(np.percentile(np.asarray(v, dtype=float), p)) if len(v) else float("nan")


def summ(v) -> str:
    v = np.asarray(list(v), dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return f"{'-':>9} {'-':>9} {'-':>9} {'-':>5}"
    return (
        f"{np.median(v):>9.3f} {np.percentile(v, 25):>9.3f} "
        f"{np.percentile(v, 75):>9.3f} {v.size:>5}"
    )


def diff_disp_px(delta: float, lever: float = 1200.0) -> float:
    """Differential displacement a plant of `delta` produces at the anchor lever.

    M10's P6 table pairs g = 1e-4 with 0.12 px, so its lever is 1200 plane px;
    the same convention is used here so the two are directly comparable.
    """
    return abs(delta) * lever


# ---------------------------------------------------------------------------
# the correction, and its registered nulls
# ---------------------------------------------------------------------------


def corrected(l0: float, r: float, floor: float = 0.0) -> float:
    """`L' = L / R`.  `floor` clamps |R| from below; 0.0 means no clamp.

    FAILURE DIRECTION: with no clamp a single R near zero sends one edge to
    +-inf and any sum containing it is meaningless.  With a clamp the estimator
    is no longer the registered one.  Both are reported.
    """
    if not math.isfinite(r):
        return float("nan")
    if floor > 0.0:
        s = math.copysign(max(abs(r), floor), r if r != 0 else 1.0)
        return l0 / s
    if r == 0.0:
        return float("nan")
    return l0 / r


def shuffled(rvals: list[float], seed: int) -> list[float]:
    """N1: permute R, destroying the per-edge correspondence and nothing else."""
    rng = np.random.default_rng(seed)
    v = np.array(rvals, dtype=float)
    rng.shuffle(v)
    return list(v)
