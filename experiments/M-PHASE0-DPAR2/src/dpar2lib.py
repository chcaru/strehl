"""Curved-track injection/recovery support for M-PHASE0-DPAR2.

The estimator remains M6's S2.  This module supplies only the physical plant,
an exact fast evaluation of that unchanged statistic, and power arithmetic.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
LANE = ROOT / "experiments" / "M-PHASE0-DPAR2"
M6_DIR = ROOT / "experiments" / "m6-residual-halo"
M103_TRACK = ROOT / "experiments" / "M103-halfdrift" / "data" / "truth-dense.json"
if str(M6_DIR) not in sys.path:
    sys.path.insert(0, str(M6_DIR))
import m6_lib as M6  # noqa: E402


AMPLITUDES = np.array(
    [
        0.0,
        0.010,
        0.015,
        0.020,
        0.0269,
        0.035,
        0.045,
        0.0538,
        0.070,
        0.090,
        0.120,
        0.160,
        0.220,
        0.300,
        0.450,
        0.600,
        0.900,
    ],
    dtype=np.float64,
)
PRIMARY = "119MSDCF"
STACKS = ("119MSDCF", "109MSDCF", "coffee-bean")
POWER_THRESHOLD = 0.80
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260902
REFERENCE_RADIUS_PX = 1000.0


@dataclass
class Case:
    name: str
    tiles: object
    w: np.ndarray
    ox: float
    oy: float
    n_frames: int
    ell: np.ndarray
    track_median_adj: float
    input_paths: tuple[Path, ...]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_truth_ladder(path: Path = M103_TRACK) -> tuple[np.ndarray, np.ndarray]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = sorted((int(k), float(v["ln"])) for k, v in raw["ladder"].items())
    return (
        np.array([r[0] for r in rows], dtype=np.float64),
        np.array([r[1] for r in rows], dtype=np.float64),
    )


def mapped_track(n_frames: int, *, chord: bool = False) -> np.ndarray:
    """M103 ln(scale), mapped over a target stack's normalised focus axis."""
    if n_frames < 2:
        raise ValueError("a track needs at least two frames")
    j, ell = read_truth_ladder()
    target = np.linspace(float(j[0]), float(j[-1]), n_frames)
    if chord:
        return np.linspace(float(ell[0]), float(ell[-1]), n_frames)
    return np.interp(target, j, ell)


def load_case(name: str) -> Case:
    prefix = M6_DIR / "data" / name
    paths = tuple(
        Path(f"{prefix}-{suffix}.csv") for suffix in ("tiles", "focus", "fits")
    )
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
    t = M6.load_tiles(str(prefix), name)
    focus = M6.load_focus(str(prefix), name)
    fits = M6.load_fits(str(prefix), name, grid="m6")
    w, _peakiness, _profile = M6.winner_index(focus)
    if not np.all(np.isfinite(w[: M6.GRID_NX * M6.GRID_NY])):
        raise ValueError(f"{name}: all 96 torus labels must be finite")
    n_frames = int(max(np.max(t.ref), np.max(t.mov), np.max(focus["frame"]))) + 1
    ell = mapped_track(n_frames)
    med = float(np.median(np.abs(np.diff(ell))))
    if not med > 0:
        raise ValueError(f"{name}: degenerate mapped track")
    ox, oy = M6.scale_centre(fits)
    return Case(name, t, w, ox, oy, n_frames, ell, med, paths)


def phase_fields(w: np.ndarray) -> list[np.ndarray]:
    return [np.array(w, copy=True), *M6._torus_labels(w)]


def scalar_fixture(
    amplitude: float,
    pair_factor: np.ndarray,
    depth_steps: np.ndarray,
    radii_px: np.ndarray,
) -> np.ndarray:
    """Apply the preregistered scalar form; independent literals check this."""
    return (
        float(amplitude)
        * np.asarray(pair_factor, dtype=np.float64)
        * np.asarray(depth_steps, dtype=np.float64)
        * np.asarray(radii_px, dtype=np.float64)
        / REFERENCE_RADIUS_PX
    )


def _clone_tiles(t, ex: np.ndarray, ey: np.ndarray):
    values = {name: getattr(t, name) for name in t.__dataclass_fields__}
    values["ex"] = ex
    values["ey"] = ey
    return type(t)(**values)


def apply_plant(
    t,
    w: np.ndarray,
    ox: float,
    oy: float,
    ell: np.ndarray,
    amplitude: float,
):
    """Add a curved, depth-conditioned radial residual beyond one similarity."""
    ex = np.array(t.ex, copy=True)
    ey = np.array(t.ey, copy=True)
    if amplitude == 0.0:
        return _clone_tiles(t, ex, ey), {
            "max_similarity_inner_product_ratio": 0.0,
            "max_tangential_change_px": 0.0,
            "bit_identical_zero": bool(
                np.array_equal(ex.view(np.uint64), t.ex.view(np.uint64))
                and np.array_equal(ey.view(np.uint64), t.ey.view(np.uint64))
            ),
        }

    rx = t.ux - float(ox)
    ry = t.uy - float(oy)
    radius = np.hypot(rx, ry)
    wi = w[t.tile_id]
    valid = (
        t.ok
        & np.isfinite(t.ex)
        & np.isfinite(t.ey)
        & np.isfinite(radius)
        & (radius > 1e-12)
        & np.isfinite(wi)
    )
    pair = t.ref * 10000 + t.mov
    pair_values, pi = np.unique(pair[valid], return_inverse=True)
    rv = radius[valid]
    wv = wi[valid]
    r2 = rv * rv
    denom = np.bincount(pi, weights=r2, minlength=len(pair_values))
    wbar = np.bincount(pi, weights=r2 * wv, minlength=len(pair_values)) / denom
    median_adj = float(np.median(np.abs(np.diff(ell))))
    q = (ell[t.mov[valid]] - ell[t.ref[valid]]) / median_adj
    dr = (
        float(amplitude)
        * q
        * (wv - wbar[pi])
        * rv
        / REFERENCE_RADIUS_PX
    )

    ex[valid] += dr * rx[valid] / rv
    ey[valid] += dr * ry[valid] / rv

    inner_ratios = []
    for pidx in range(len(pair_values)):
        s = pi == pidx
        terms = rv[s] * dr[s]
        d = float(np.sum(np.abs(terms)))
        inner_ratios.append(abs(float(np.sum(terms))) / d if d > 0 else 0.0)

    before_tan = (-t.ex[valid] * ry[valid] + t.ey[valid] * rx[valid]) / rv
    after_tan = (-ex[valid] * ry[valid] + ey[valid] * rx[valid]) / rv
    return _clone_tiles(t, ex, ey), {
        "max_similarity_inner_product_ratio": float(max(inner_ratios, default=0.0)),
        "max_tangential_change_px": float(np.max(np.abs(after_tan - before_tan))),
        "bit_identical_zero": None,
        "max_abs_radial_plant_px": float(np.max(np.abs(dr))),
        "n_planted_rows": int(valid.sum()),
    }


def _m6_rank(v: np.ndarray) -> np.ndarray:
    # Deliberately identical to m6_lib._spearman, including its tie convention.
    r = np.argsort(np.argsort(v)).astype(np.float64)
    return r - r.mean()


def _group_demean(v: np.ndarray, group: np.ndarray, n_group: int) -> np.ndarray:
    count = np.bincount(group, minlength=n_group).astype(np.float64)
    mean = np.bincount(group, weights=v, minlength=n_group) / count
    return v - mean[group]


def prepare_power(case: Case):
    """Precompute the linear pieces of exact S2 for all 96 torus phases."""
    t = case.tiles
    finite_w = np.isfinite(case.w[t.tile_id])
    mask = t.ok & np.isfinite(t.res) & finite_w
    tt = t.select(mask)
    e_rad, _e_tan, radius = M6.radial_tangential(
        tt.ex, tt.ey, tt.ux, tt.uy, case.ox, case.oy
    )
    dg0 = e_rad / radius
    pair_values, pi = np.unique(tt.ref * 10000 + tt.mov, return_inverse=True)
    n_pair = len(pair_values)
    dg0 = _group_demean(dg0, pi, n_pair)
    ids, ti = np.unique(tt.tile_id, return_inverse=True)
    tile_count = np.bincount(ti, minlength=len(ids)).astype(np.float64)
    mean0 = np.bincount(ti, weights=dg0, minlength=len(ids)) / tile_count

    q = (case.ell[tt.mov] - case.ell[tt.ref]) / case.track_median_adj
    r2 = radius * radius
    pair_r2 = np.bincount(pi, weights=r2, minlength=n_pair)
    phases = phase_fields(case.w)
    units = []
    label_ranks = []
    for wp in phases:
        wobs = wp[tt.tile_id]
        wbar = np.bincount(pi, weights=r2 * wobs, minlength=n_pair) / pair_r2
        unit = q * (wobs - wbar[pi]) / REFERENCE_RADIUS_PX
        unit = _group_demean(unit, pi, n_pair)
        units.append(np.bincount(ti, weights=unit, minlength=len(ids)) / tile_count)
        label_ranks.append(_m6_rank(wp[ids]))

    label_ranks_a = np.asarray(label_ranks)
    label_norm = np.sqrt(np.sum(label_ranks_a * label_ranks_a, axis=1))
    return {
        "tt": tt,
        "ids": ids,
        "mean0": mean0,
        "units": np.asarray(units),
        "phases": phases,
        "label_ranks": label_ranks_a,
        "label_norm": label_norm,
    }


def evaluate_power(case: Case, amplitudes: np.ndarray = AMPLITUDES):
    prep = prepare_power(case)
    n_phase = len(prep["phases"])
    if n_phase != 96:
        raise AssertionError(f"{case.name}: expected 96 phases, got {n_phase}")
    rows = []
    detection = np.zeros((len(amplitudes), n_phase), dtype=bool)
    rho_all = np.zeros((len(amplitudes), n_phase), dtype=np.float64)
    p_all = np.zeros((len(amplitudes), n_phase), dtype=np.float64)
    for ai, amplitude in enumerate(amplitudes):
        for phase in range(n_phase):
            mean_dg = prep["mean0"] + float(amplitude) * prep["units"][phase]
            rr = _m6_rank(mean_dg)
            rr_norm = math.sqrt(float(np.sum(rr * rr)))
            correlations = (
                prep["label_ranks"] @ rr / (prep["label_norm"] * rr_norm)
            )
            rho = float(correlations[phase])
            null = np.delete(correlations, phase)
            p_torus = float(
                (np.sum(np.abs(null) >= abs(rho)) + 1) / n_phase
            )
            detected = rho < 0.0 and p_torus <= 0.05
            detection[ai, phase] = detected
            rho_all[ai, phase] = rho
            p_all[ai, phase] = p_torus
        k = int(detection[ai].sum())
        lo, hi = wilson(k, n_phase)
        rows.append(
            {
                "amplitude_px_per_step_r1000": float(amplitude),
                "amplitude_px_per_step_r2000": float(2.0 * amplitude),
                "detections": k,
                "replicates": n_phase,
                "power": float(k / n_phase),
                "power_wilson95": [lo, hi],
                "rho_identity": float(rho_all[ai, 0]),
                "p_identity": float(p_all[ai, 0]),
                "rho_phase_median": float(np.median(rho_all[ai])),
                "rho_phase_range": [
                    float(np.min(rho_all[ai])),
                    float(np.max(rho_all[ai])),
                ],
            }
        )
    return rows, detection, rho_all, p_all


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / den
    return float(centre - half), float(centre + half)


def crossing_from_rates(rates: np.ndarray, amplitudes: np.ndarray = AMPLITUDES):
    suffix_min = np.minimum.accumulate(np.asarray(rates, dtype=float)[::-1])[::-1]
    eligible = np.flatnonzero(suffix_min >= POWER_THRESHOLD)
    return float(amplitudes[eligible[0]]) if len(eligible) else math.inf


def bootstrap_mda(
    detection: np.ndarray,
    amplitudes: np.ndarray = AMPLITUDES,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
):
    point = crossing_from_rates(detection.mean(axis=1), amplitudes)
    rng = np.random.default_rng(seed)
    crossings = np.empty(draws, dtype=np.float64)
    n_phase = detection.shape[1]
    for b in range(draws):
        ix = rng.integers(0, n_phase, size=n_phase)
        crossings[b] = crossing_from_rates(detection[:, ix].mean(axis=1), amplitudes)
    lo = float(np.quantile(crossings, 0.025, method="inverted_cdf"))
    hi = float(np.quantile(crossings, 0.975, method="inverted_cdf"))
    return {
        "point": point if math.isfinite(point) else None,
        "bootstrap95": [
            lo if math.isfinite(lo) else None,
            hi if math.isfinite(hi) else None,
        ],
        "draws": int(draws),
        "seed": int(seed),
        "infinite_draws": int(np.sum(~np.isfinite(crossings))),
    }


def validate_fast_path(case: Case, checks=((0, 0.0), (0, 0.0269), (17, 0.300))):
    """Compare the fast evaluator to unchanged M6 S2 on fixed phase/dose cases."""
    prep = prepare_power(case)
    out = []
    for phase, amplitude in checks:
        wp = prep["phases"][phase]
        planted, _diag = apply_plant(
            case.tiles, wp, case.ox, case.oy, case.ell, amplitude
        )
        exact = M6.s2_scale_anomaly(planted, wp, case.ox, case.oy)

        mean_dg = prep["mean0"] + float(amplitude) * prep["units"][phase]
        rr = _m6_rank(mean_dg)
        correlations = prep["label_ranks"] @ rr / (
            prep["label_norm"] * math.sqrt(float(np.sum(rr * rr)))
        )
        fast_rho = float(correlations[phase])
        null = np.delete(correlations, phase)
        fast_p = float((np.sum(np.abs(null) >= abs(fast_rho)) + 1) / 96)
        out.append(
            {
                "phase": int(phase),
                "amplitude": float(amplitude),
                "m6_rho": float(exact["rho_dg_w"]),
                "fast_rho": fast_rho,
                "abs_rho_error": abs(fast_rho - float(exact["rho_dg_w"])),
                "m6_p": float(exact["p_torus_dg"]),
                "fast_p": fast_p,
                "abs_p_error": abs(fast_p - float(exact["p_torus_dg"])),
            }
        )
    return out


def provenance(case: Case) -> dict:
    paths = [*case.input_paths, M103_TRACK, M6_DIR / "m6_lib.py"]
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
        for path in paths
    }
