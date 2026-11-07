"""Small analytical controls for proposal assumptions; not a RAW quality test."""
import cmath
import json
import math
import pathlib
import sys

def close(a, b, tol=1e-12):
    assert math.isclose(a, b, rel_tol=tol, abs_tol=tol), (a, b)

def rank(rows, tol=1e-10):
    a = [list(map(complex, row)) for row in rows]
    nrows, ncols = len(a), len(a[0])
    r = 0
    for c in range(ncols):
        candidates = [i for i in range(r, nrows) if abs(a[i][c]) > tol]
        if not candidates:
            continue
        p = max(candidates, key=lambda i: abs(a[i][c]))
        a[r], a[p] = a[p], a[r]
        pivot = a[r][c]
        a[r] = [v / pivot for v in a[r]]
        for i in range(nrows):
            if i != r:
                f = a[i][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[r])]
        r += 1
    return r

g, rn, signal, k = 0.2289, 4.20, 3000.0, 3
variance = g * signal + (rn * g) ** 2
equal_model = (g / k) * signal + ((rn * math.sqrt(k)) * g / k) ** 2
close(equal_model, variance / k)
duplicate_variance = variance
close(duplicate_variance / (variance / k), k)

# Two normalized source noises at unequal exposure durations.
a, b = 0.2232, 0.887 ** 2
exposures = [1.0, 0.25]
variances = [a * signal / e + b / (e * e) for e in exposures]
inverse_variance = 1.0 / sum(1.0 / v for v in variances)
naive_half = (a * signal + b) / 2.0
assert inverse_variance > naive_half * 1.5

# y0=(x0+x1)/2 and y1=(x1+x2)/2, independent unit-variance x.
y_variance, adjacent_covariance = 0.5, 0.25
actual_difference_variance = 2 * y_variance - 2 * adjacent_covariance
diagonal_only_difference_variance = 2 * y_variance
close(actual_difference_variance, 0.5)
close(diagonal_only_difference_variance / actual_difference_variance, 2.0)

# Population FRC/coherence at a Fourier cell: common post-noise filter cancels.
scene_power, noise_power = 4.0, 1.0
coherence = scene_power / (scene_power + noise_power)
filtered = {
    str(gain): (gain * gain * scene_power)
    / (gain * gain * (scene_power + noise_power))
    for gain in (0.1, 0.5, 2.0, 10.0)
}
for v in filtered.values():
    close(v, coherence)
# Ring pooling can move under a common filter: A=(1,1), B=(1,-1).
pooled_before = 0.0
pooled_after = (4.0 - 1.0) / (4.0 + 1.0)
close(pooled_after, 0.6)

def alias_rows(phases):
    return [[cmath.exp(2j * math.pi * (fx * x + fy * y))
             for fx, fy in ((0, 0), (1, 0), (0, 1), (1, 1))]
            for x, y in phases]
phase_ranks = {
    "four_identical": rank(alias_rows([(0, 0)] * 4)),
    "four_distinct_x_only": rank(alias_rows([(i / 4, 0) for i in range(4)])),
    "two_axis_square": rank(alias_rows([(0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)])),
}
assert phase_ranks == {"four_identical": 1, "four_distinct_x_only": 2, "two_axis_square": 4}

# Purely lateral pinhole displacement; the approximation itself is reasonable.
s, depth, dz = 4922.4, 120.0, 5.0
first_order = s * dz / depth
exact = s * dz / (depth + dz)
relative_error = first_order / exact - 1
close(relative_error, dz / depth)

report = {
    "classification": "DERIVED; analytical counterexamples, not product or photographic validation",
    "command": "python -I experiments/multi-stack-2026-10-28/challenge/derive-assumption-controls.py",
    "python": sys.version,
    "equal_independent_repeat_model": {"variance": variance, "k": k, "actual_average": variance / k, "proposal_model": equal_model},
    "duplicate_false_gain": {"actual_variance": duplicate_variance, "naive_claimed_variance": variance / k, "variance_understatement": k},
    "unequal_exposure": {"relative_exposures": exposures, "normalized_source_variances": variances, "correct_fixed_oracle_weight_variance": inverse_variance, "naive_equal_model_variance": naive_half},
    "interpolation_covariance": {"pixel_variance": y_variance, "neighbor_covariance": adjacent_covariance, "actual_difference_variance": actual_difference_variance, "diagonal_only_prediction": diagonal_only_difference_variance},
    "common_postfilter_coherence": {"unfiltered": coherence, "filtered": filtered, "pooled_before": pooled_before, "pooled_after": pooled_after},
    "two_dimensional_2x_alias_matrix_rank": phase_ranks,
    "parallax": {"exact": exact, "first_order": first_order, "relative_error": relative_error},
    "assertions": "PASS",
}
print(json.dumps(report, indent=2))
