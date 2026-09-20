"""Numerical continuity, separate from the unchanged failed quality admission."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / 'experiments/boundary-cfa-wavelet/controls-2/output/screen.json'
REFERENCE_HASH = '020d1ca61c99fc685527d648d1f40cd83b44d24405c0627e2f4610370b159fdf'


def without_timing(value):
    if isinstance(value, dict):
        return {k: without_timing(v) for k, v in value.items() if k != 'probe_seconds'}
    if isinstance(value, list):
        return [without_timing(v) for v in value]
    return value


def check(current):
    data = REFERENCE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == REFERENCE_HASH
    prior = json.loads(data)
    for key in ['bounded_photographic_prototype_admitted', 'production_admitted',
                'decisions', 'metric_controls', 'status']:
        assert current[key] == prior[key], key
    assert current['bounded_photographic_prototype_admitted'] is False
    assert len(current['cases']) == len(prior['cases']) == 12
    worst_score = 0.0
    worst_ratio = 0.0

    def scores(a, b):
        nonlocal worst_score
        if isinstance(a, dict):
            assert a.keys() == b.keys()
            for key in a:
                scores(a[key], b[key])
        elif isinstance(a, list):
            assert len(a) == len(b)
            for x, y in zip(a, b):
                scores(x, y)
        else:
            assert math.isfinite(a) and math.isfinite(b)
            delta = abs(a - b)
            worst_score = max(worst_score, delta)
            assert delta <= 2e-6, (a, b, delta)

    for a, b in zip(current['cases'], prior['cases']):
        for key in ['scene', 'iso', 'warp', 'guard_pass', 'fixture_exercised', 'baseline']:
            assert a[key] == b[key], (key, a['scene'], a['iso'], a['warp'])
        assert without_timing(a['evidence']) == without_timing(b['evidence'])
        scores(a['candidate'], b['candidate'])
        delta = abs(a['rgb_ratio'] - b['rgb_ratio'])
        worst_ratio = max(worst_ratio, delta)
        assert delta <= 2e-4
    observer = current['observer_neutrality']
    assert observer['on_rgb_sha256'] == observer['off_rgb_sha256']
    assert observer['on_rgb_sha256'][0] == prior['observer_neutrality']['on_rgb_sha256'][0]
    return dict(passed=True, reference=str(REFERENCE), reference_sha256=REFERENCE_HASH,
                candidate_score_max_absolute_difference=worst_score,
                ratio_max_absolute_difference=worst_ratio,
                score_absolute_tolerance=2e-6, ratio_absolute_tolerance=2e-4,
                baseline_and_evidence_exact_except_probe_timing=True,
                quality_decisions_identical=True, generated_admission=False)
