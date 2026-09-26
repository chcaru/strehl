"""Independent admission choices for the fixed sampler unit experiment only."""
from copy import deepcopy
import math


def judge(records):
    checks = {}
    phases = [(0., 0.), (.5, .5), (.5, 0.)]
    checks['exact_three_registered_phases'] = (
        isinstance(records, list) and len(records) == 3 and
        [tuple(row.get('phase', ())) for row in records] == phases)
    if not checks['exact_three_registered_phases']:
        return dict(passed=False, checks=checks, photographic_admission=False)
    counts = set()
    for index, row in enumerate(records):
        prefix = f'phase_{index}'
        checks[prefix+'_known_motion_unit_only'] = (
            row.get('geometry') == 'identity' and
            row.get('motion') == 'fixed-at-known-displacement' and
            row.get('no_physical_blur') is True and row.get('phase_guide') is False and
            row.get('source_dtype') == 'float64' and
            row.get('scalar_blur_interpretation') is (index != 2))
        lap_error = row.get('raster_laplacian_vs_exact_five_point_integer_max_abs', math.inf)
        checks[prefix+'_same_discrete_derivative'] = math.isfinite(lap_error) and 0 <= lap_error < 1e-10
        for name in ('exact', 'bilinear'):
            arm = row['arms'][name]
            finite_keys = ('beta_source_native_squared', 'gain', 'bias', 'lap_coefficient',
                           'standardized_condition', 'fit_rmse', 'validation_rmse',
                           'validation_max_abs', 'target_spatial_sd')
            checks[prefix+'_'+name+'_identified_finite_fit'] = (
                all(math.isfinite(arm[key]) for key in finite_keys) and
                arm['rank'] == 3 and 1 <= arm['standardized_condition'] <= 1e6 and
                arm['target_spatial_sd'] > 1e-7 and arm['gain'] > 0 and
                arm['fit_samples'] > 3 and arm['validation_samples'] > 3 and
                min(arm['fit_rmse'], arm['validation_rmse'], arm['validation_max_abs']) >= 0)
            counts.add((arm['fit_samples'], arm['validation_samples']))
        checks[prefix+'_exact_near_zero_beta'] = abs(row['arms']['exact']['beta_source_native_squared']) < .03
    checks['same_support_counts_in_all_arms'] = len(counts) == 1
    integer = records[0]['arms']
    half = records[1]['arms']
    checks['integer_bilinear_placebo'] = (
        abs(integer['bilinear']['beta_source_native_squared']) < .03 and
        abs(integer['bilinear']['beta_source_native_squared']-
            integer['exact']['beta_source_native_squared']) < .03)
    checks['half_bilinear_has_negative_nonzero_beta'] = half['bilinear']['beta_source_native_squared'] < -.03
    checks['half_bilinear_exceeds_exact_magnitude'] = (
        abs(half['bilinear']['beta_source_native_squared']) > abs(half['exact']['beta_source_native_squared']))
    return dict(passed=all(checks.values()), checks=checks, photographic_admission=False,
                scope='Known-motion interpolation unit evidence; not dominance in the original guide or photographic truth.')


def commission():
    """Reject adverse records on the actual judge path; no simulated result claim."""
    arm = dict(beta_source_native_squared=0., gain=1/1.06, bias=-.017/1.06,
               lap_coefficient=0., rank=3, standardized_condition=10.,
               fit_rmse=1e-15, validation_rmse=1e-15, validation_max_abs=1e-14,
               target_spatial_sd=.05, fit_samples=12000, validation_samples=12000)
    records = []
    for phase in ((0., 0.), (.5, .5), (.5, 0.)):
        records.append(dict(phase=list(phase), geometry='identity', motion='fixed-at-known-displacement',
                            no_physical_blur=True, phase_guide=False, source_dtype='float64',
                            scalar_blur_interpretation=phase != (.5, 0.),
                            raster_laplacian_vs_exact_five_point_integer_max_abs=1e-15,
                            arms=dict(exact=deepcopy(arm), bilinear=deepcopy(arm))))
    records[1]['arms']['bilinear']['beta_source_native_squared'] = -.125
    records[2]['arms']['bilinear']['beta_source_native_squared'] = -.06
    assert judge(records)['passed'], 'Judge refuses its explicitly admissible record fixture.'
    cases = {}
    def refused(name, change):
        changed = deepcopy(records)
        change(changed)
        result = judge(changed)
        assert not result['passed'], name
        cases[name] = [key for key, passed in result['checks'].items() if not passed]
    refused('missing_phase', lambda r: r.pop())
    refused('no_sampler_effect', lambda r: r[1]['arms']['bilinear'].update(beta_source_native_squared=0.))
    refused('opposite_beta_sign', lambda r: r[1]['arms']['bilinear'].update(beta_source_native_squared=.125))
    refused('exact_evaluation_already_blurred', lambda r: r[1]['arms']['exact'].update(beta_source_native_squared=-.125))
    refused('integer_placebo_broken', lambda r: r[0]['arms']['bilinear'].update(beta_source_native_squared=-.125))
    refused('inconsistent_derivative', lambda r: r[1].update(raster_laplacian_vs_exact_five_point_integer_max_abs=.01))
    refused('fitted_motion_confounds_isolation', lambda r: r[1].update(motion='jointly-fitted'))
    refused('anisotropy_mislabeled_isotropic', lambda r: r[2].update(scalar_blur_interpretation=True))
    refused('flat_design', lambda r: r[1]['arms']['bilinear'].update(target_spatial_sd=0.))
    refused('rank_deficient_design', lambda r: r[1]['arms']['bilinear'].update(rank=2))
    refused('ill_conditioned_design', lambda r: r[1]['arms']['bilinear'].update(standardized_condition=1e7))
    refused('empty_holdout', lambda r: r[1]['arms']['bilinear'].update(validation_samples=0))
    refused('nonfinite_result', lambda r: r[1]['arms']['bilinear'].update(gain=math.nan))
    return dict(passed=True, scope='Judge software commission only; these records are artificial.',
                admitted_fixture=True, rejected_cases=cases)


def commission_sampler(sample):
    """Exercise the actual compact candidate, with independently known taps."""
    import numpy as np
    y, x = np.mgrid[:17, :19]
    integer = np.array([[3., 4.], [11., 9.]])
    textured = (x*x+3*y+2*x*y).astype(np.float32)
    assert np.array_equal(sample(textured, integer), textured[integer[:, 1].astype(int), integer[:, 0].astype(int)])
    points = np.array([[6.5, 7.5], [6.25, 7.5]])
    constant = np.full(textured.shape, .375, dtype=np.float32)
    assert np.array_equal(sample(constant, points), np.full(2, .375))
    impulse = np.zeros(textured.shape, dtype=np.float64)
    impulse[7, 6] = 1.
    # Catmull-Rom central weights: 9/16 at half, 111/128 at quarter.
    expected = np.array([81/256, (111/128)*(9/16)])
    assert np.array_equal(sample(impulse, points), expected), 'Wrong cubic phase/taps (bilinear must fail here).'
    remote = impulse.copy()
    remote[0, 0] = 1e9
    assert np.array_equal(sample(remote, points), expected), 'Nonlocal preparation contaminates compact support.'
    polynomial = (x*x+3*y+2*x*y).astype(np.float64)
    truth = points[:, 0]**2+3*points[:, 1]+2*points[:, 0]*points[:, 1]
    assert np.max(np.abs(sample(polynomial, points)-truth)) < 1e-12, 'Axis or cubic reproduction is wrong.'
    return dict(passed=True, checks=['integer-f32-identity', 'constant-identity',
                                    'independent-half-and-quarter-taps', 'compact-support',
                                    'mixed-quadratic-axes'],
                scope='Sampler implementation only; not fitted-motion or photographic admission.')


if __name__ == '__main__':
    import json
    print(json.dumps(commission(), indent=2, allow_nan=False))
