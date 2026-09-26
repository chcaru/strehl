"""Independent fixed proxy controls. Root executes; no photographic data loading."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MODULATION_MIN = 0.15
AGGREGATE_MAX = 0.50
P90_MAX = 0.75
TARGET_MAX = 0.75
BLOCK_MAX = 0.65


def fixed_sites():
    rows = []
    for r, y in enumerate([350, 1070, 1790, 2510, 3230, 3950]):
        for c, x in enumerate([500, 1600, 2700, 3800, 4900, 6000]):
            if (r, c) == (4, 4):
                continue
            rows.append(dict(name=f"grid-{r}-{c}", xy=[x, y], row=r, col=c,
                             target=False, train=(r // 2 + c // 2) % 2 == 0))
    for name, xy in [
        ("rail-crossing", [1290, 1150]), ("upper-colour", [1292, 452]),
        ("central-stipple", [3232, 1562]), ("lower-array", [822, 3052]),
        ("lower-colour", [4922, 3272]), ("surface-scratches", [5112, 1512]),
        ("upper-left-contact-grid", [304, 592]),
    ]:
        rows.append(dict(name=name, xy=xy, row=None, col=None, target=True, train=False))
    assert len(rows) == 42 and sum(row["train"] for row in rows) == 19
    return rows


def fixed_geometry():
    sites = fixed_sites()
    return np.array([s["xy"] for s in sites], dtype=np.float64), np.array(
        [s["train"] for s in sites], dtype=bool)


def stage_controls(stage):
    """Three tiny actual-extractor checks; no TIFF/RAW/model reads."""
    points = np.array([[3250., 2166.], [3350., 2116.], [3150., 2216.]])
    transform = np.array([1.1, 0.05, 2., -3.])
    # Centre maps to C+2b. The two offsets are +/-[100,-50] native pixels.
    expected = np.array([[3520., 2338.], [3632.5, 2288.], [3407.5, 2388.]])
    actual = stage.map_native(points, transform)
    assert np.allclose(actual, expected, rtol=0, atol=1e-10), "complex/crop/quad gauge failed"
    missing_crop = stage.map_native(points, transform, crop_xy=(0, 0))
    missing_quad_factor = stage.map_native(points, np.array([1.1, 0.05, 1., -1.5]))
    wrong_direction = stage.map_native(points, np.array([1 / 1.1, -0.05, -2., 3.]))
    assert all(not np.allclose(v, expected, rtol=0, atol=1e-10)
               for v in (missing_crop, missing_quad_factor, wrong_direction))

    yy, xx = np.indices((64, 80))
    image = np.stack([1000 + 3 * xx + 17 * yy,
                      7000 + 7 * xx + 23 * yy,
                      19000 + 11 * xx + 29 * yy], axis=2).astype(np.uint16)
    reference = np.array([[12, 15], [28, 31], [49, 42]], dtype=np.float64)
    positions = reference + [3, -4]
    sampled = stage.sample_rgb(image, positions[None, :, :])[0]
    sx, sy = positions.astype(int).T
    oracle = np.array([[1000 + 3*x + 17*y, 7000 + 7*x + 23*y,
                        19000 + 11*x + 29*y] for x, y in zip(sx, sy)], dtype=np.float32)
    oracle /= np.float32(65535)
    assert sampled.shape == (3, 3) and np.array_equal(sampled, oracle), "integer source addressing"
    assert not np.array_equal(stage.sample_rgb(image, positions[:, ::-1][None, :, :])[0], oracle)
    assert not np.array_equal(stage.sample_rgb(image, reference[None, :, :])[0], oracle)

    flat = stage.band_power(np.full((192, 192), 0.25, dtype=np.float32))
    py, px = np.indices((192, 192))
    signal = (0.4 + 0.10*np.cos(2*np.pi*px/12) + 0.05*np.cos(2*np.pi*py/48)).astype(np.float32)
    power = stage.band_power(signal)
    assert flat.shape == (2,) and np.isfinite(flat).all() and np.max(np.abs(flat)) <= 1e-12
    assert power.shape == (2,) and np.isfinite(power).all() and np.all(power > 1e-6)
    return dict(passed=True, controls=3, known_complex_native_gauge=True,
                missing_crop_rejected=True, missing_quad_factor_rejected=True,
                wrong_direction_rejected=True, integer_source_rgb_exact=True,
                axis_swap_rejected=True, omitted_shift_rejected=True,
                constant_power=flat.tolist(), two_band_signal_power=power.tolist(),
                scope="Addressing and filter arithmetic only; no focus or quality evidence")


def _safe(value):
    if isinstance(value, np.ndarray):
        return _safe(value.tolist())
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return _safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    return value


def judge(model_module, model, xy_native, contrast, train_mask):
    """Same frozen real/generated predictive bars; never an image-quality gate."""
    xy, expected_train = fixed_geometry()
    data = np.asarray(contrast, dtype=np.float64)
    assert np.array_equal(xy_native, xy) and np.array_equal(train_mask, expected_train)
    assert data.ndim == 3 and data.shape[1:] == (42, 2) and np.isfinite(data).all()
    even = np.arange(len(data)) % 2 == 0
    quantiles = np.quantile(data[even], [0.1, 0.9], axis=0)
    modulation = (quantiles[1] - quantiles[0]) / np.maximum(np.abs(quantiles[1]), 1e-12)
    informative = np.all(modulation >= MODULATION_MIN, axis=1)
    sites = fixed_sites()
    groups = {}
    for j, site in enumerate(sites):
        if not site["target"]:
            key = f"{site['row']//2}-{site['col']//2}"
            groups.setdefault(key, []).append(j)
    group_counts = {k: int(informative[v].sum()) for k, v in groups.items()}
    target_indices = np.arange(35, 42)
    coverage = all(n >= 2 for n in group_counts.values()) and bool(informative[target_indices].all())
    result = dict(schema=1, predictive_proxy_admitted=False, photographic_quality_admitted=False,
                  informative=informative, modulation_by_site_band=modulation,
                  coverage_pass=coverage, grid_block_informative_counts=group_counts,
                  target_coverage=informative[target_indices], train_sites=int(expected_train.sum()),
                  held_sites=int((~expected_train).sum()), model_status=model.get("status"),
                  scope="Spatially withheld, odd-frame profile prediction with even-only nuisance fits")
    if model.get("status") != "fit_completed":
        result.update(numerical_pass=False, reason="No fitted front", bands=[])
        return _safe(result)
    assert model["train_indices"] == np.flatnonzero(expected_train).tolist()
    diagnostic = model["fit"]
    numerical = bool(diagnostic["converged"] and not any(diagnostic["primary_bound_flags"])
                     and not diagnostic["secondary_at_width_bound"])
    evaluation = model_module.evaluate_profiles(model, xy, data)
    assert np.array_equal(evaluation["calibration_frames"], even)
    assert np.array_equal(evaluation["score_frames"], ~even)
    assert np.isfinite(evaluation["predicted"]).all()
    score = evaluation["score_sse"]
    null = evaluation["constant_score_sse"]
    ratio = np.sqrt(np.divide(score, null, out=np.full_like(score, np.inf), where=null > 1e-30))
    held = (~expected_train) & informative
    bands = []
    for b in range(2):
        aggregate = np.sqrt(score[held, b].sum() / null[held, b].sum()) if np.any(held) and null[held, b].sum() > 1e-30 else np.inf
        p90 = float(np.quantile(ratio[held, b], 0.9)) if np.any(held) else np.inf
        block_ratios = {}
        for k, members in groups.items():
            if expected_train[members[0]]:
                continue
            members = np.array(members)[informative[members]]
            denom = null[members, b].sum()
            block_ratios[k] = float(np.sqrt(score[members, b].sum()/denom)) if len(members) and denom > 1e-30 else np.inf
        target_ratios = ratio[target_indices, b]
        passed = bool(aggregate <= AGGREGATE_MAX and p90 <= P90_MAX
                      and np.all(target_ratios <= TARGET_MAX)
                      and all(v <= BLOCK_MAX for v in block_ratios.values()))
        bands.append(dict(band=b, pass_predictive=passed, aggregate_ratio=float(aggregate),
                          site_ratio_p90=p90, held_grid_block_ratios=block_ratios,
                          target_ratios=target_ratios))
    result.update(numerical_pass=numerical, bands=bands, per_site_ratios=ratio,
                  predictive_proxy_admitted=bool(coverage and numerical and all(b["pass_predictive"] for b in bands)))
    return _safe(result)


def generated_fixture(kind):
    xy, train = fixed_geometry()
    coords = (xy - (xy.min(0)+xy.max(0))/2) / ((xy.max(0)-xy.min(0))/2)
    x, y = coords.T
    knots = np.linspace(0, 1, 7)
    values = np.r_[0, np.cumsum([0.07, 0.11, 0.14, 0.19, 0.21, 0.28])]
    values[-1] = 1.0
    schedule = np.interp(np.linspace(0, 1, 97), knots, values)
    depth = 0.5 + 0.19*x + 0.14*y
    if kind == "two-dimensional-bowl":
        depth = 0.18 + 0.28*(x*x + y*y)
    widths = [0.050, 0.035]
    amplitude = np.stack([0.080+0.012*np.cos(1.3*x+0.7*y),
                          0.065+0.010*np.sin(0.8*x-1.1*y)], axis=1)
    offset = np.stack([0.020+0.003*x, 0.014+0.002*y], axis=1)
    unit = np.stack([np.exp(-0.5*((schedule[:, None]-depth[None, :])/s)**2)
                     for s in widths], axis=2)
    if kind == "two-depth-occlusion":
        unit = np.stack([0.5*np.exp(-0.5*((schedule[:, None]-depth[None, :]+0.14)/s)**2)
                         +0.5*np.exp(-0.5*((schedule[:, None]-depth[None, :]-0.14)/s)**2)
                         for s in widths], axis=2)
    if kind in ("flat-noisy", "flat-exact"):
        unit = np.zeros_like(unit)
    data = offset[None, :, :] + amplitude[None, :, :]*unit
    if kind != "flat-exact":
        # Independent fixed contrast-proxy noise; not the physical sensor model.
        data += np.random.default_rng(20260925).normal(0, 0.00015, data.shape)
    assert np.isfinite(data).all() and data.min() > 0
    return xy, train, data, dict(schedule_values=values.tolist(), widths=widths,
                                depth=depth.tolist(), proxy_noise_sd=0 if kind == "flat-exact" else 0.00015)


def model_controls(model_module):
    cases = []
    positive = None
    for name in ("nonuniform-planar", "flat-exact", "flat-noisy", "two-dimensional-bowl", "two-depth-occlusion"):
        xy, train, data, truth = generated_fixture(name)
        fitted = model_module.fit_model(xy, data, train)
        scored = judge(model_module, fitted, xy, data, train)
        expected = name == "nonuniform-planar"
        if name in ("two-dimensional-bowl", "two-depth-occlusion"):
            scientific_rejection = bool(scored["coverage_pass"] and scored["bands"]
                and not all(b["pass_predictive"] for b in scored["bands"]))
        elif name == "flat-noisy":
            scientific_rejection = not scored["coverage_pass"]
        elif name == "flat-exact":
            scientific_rejection = fitted["status"] == "insufficient_temporal_variation"
        else:
            scientific_rejection = False
        matches = scored["predictive_proxy_admitted"] if expected else (
            not scored["predictive_proxy_admitted"] and scientific_rejection)
        cases.append(dict(name=name, expected_admission=expected, matches_expected=bool(matches),
                          scientific_rejection_exercised=scientific_rejection,
                          truth=truth, model=fitted, judgment=scored))
        if expected:
            positive = fitted, xy, train, data
    mutants = []
    fitted, xy, train, data = positive
    if fitted.get("status") == "fit_completed":
        for name in ("shifted-front", "wrong-smooth-plane"):
            wrong = copy.deepcopy(fitted)
            if name == "shifted-front":
                wrong["plane"][2] += 0.25
            else:
                wrong["plane"][0] *= -1
                wrong["plane"][1] *= -1
            # Only the front changes. The original schedule and both widths are held.
            scored = judge(model_module, wrong, xy, data, train)
            mutants.append(dict(name=name, rejected=not scored["predictive_proxy_admitted"], judgment=scored))
    passed = all(row["matches_expected"] for row in cases) and len(mutants) == 2 and all(row["rejected"] for row in mutants)
    return _safe(dict(schema=1, controls_pass=passed, generated_cases=cases, prediction_destroyers=mutants,
                      fixed_bars=dict(modulation_min=MODULATION_MIN, aggregate_max=AGGREGATE_MAX,
                                      p90_max=P90_MAX, target_max=TARGET_MAX, block_max=BLOCK_MAX),
                      positive_family="Exact fitted Gaussian family plus independent proxy noise; fitting commission only",
                      photographic_quality_admitted=False, scope="Operator/prediction commissioning, not physical calibration"))


def _load(path):
    spec = importlib.util.spec_from_file_location("chip_focus_front_reviewed_model", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=HERE/"model.py")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = model_controls(_load(args.model))
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    if not result["controls_pass"]:
        raise SystemExit("Independent model controls refused; retain all results and do not extract/fit photographs.")


if __name__ == "__main__":
    main()
