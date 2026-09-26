"""Generated-only sampler diagnosis; original photographic refusal stays intact."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import importlib.util
import json
import sys
import time
import numpy as np
import scipy
from scipy.ndimage import laplace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = ROOT/'experiments/chip-differential-blur'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def binding(path):
    data = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def array_binding(value):
    data = np.ascontiguousarray(value)
    return dict(shape=list(data.shape), dtype=str(data.dtype), sha256=hashlib.sha256(data.tobytes()).hexdigest())


def replay(original_controls, model, out, prefix):
    """Run unchanged controls, writing every returned fit BEFORE their assertions.

    The original module creates its own exact original f32 stimulus and grids.
    This recorder delegates guide/grids/fit without changing any array or option.
    It does not catch optimizer errors or alter the old assertions internally.
    """
    records = []

    def recorded_fit(*args, **kwargs):
        result = model.fit(*args, **kwargs)
        row = dict(call=len(records)+1, joint=bool(kwargs['joint']), axis=int(kwargs['axis']),
                   input_arrays=[array_binding(value) for value in args],
                   probe_deltas=[np.asarray(value).tolist() for value in kwargs.get('probe_deltas', ())],
                   result=result)
        write(out/f'{prefix}-fit-{len(records)+1:02d}.json', row)
        records.append(row)
        return result

    proxy = SimpleNamespace(guide=model.guide, grids=model.grids, fit=recorded_fit)
    start = time.perf_counter()
    try:
        result = original_controls.controls(proxy)
        receipt = dict(passed=True, original_result=result, error=None)
    except Exception as error:
        receipt = dict(passed=False, original_result=None, error=repr(error))
    receipt.update(records=records, seconds=time.perf_counter()-start,
                   unchanged_original_control_source=binding(PREVIOUS/'independent-controls.py'))
    write(out/f'{prefix}-replay.json', receipt)
    return receipt


def continuous_field(xy, waves):
    """Independent f64 direct evaluation; no resampling generates a source.

    The wave parameters are the old independently chosen stimulus. This unit
    layer deliberately omits the phase guide and its f32 rounding, equally in
    both arms, to isolate interpolation alone.
    """
    result = np.full(len(xy), .41, dtype=np.float64)
    for amplitude, fx, fy, phase in waves:
        result += amplitude*np.cos(2*np.pi*(fx*xy[:, 0]+fy*xy[:, 1])+phase)
    return result


def exact_source(xy, phase, waves):
    return 1.06*continuous_field(xy-np.asarray(phase), waves)+.017


def exact_five_point(xy, phase, waves):
    result = -4*exact_source(xy, phase, waves)
    for offset in ((1., 0.), (-1., 0.), (0., 1.), (0., -1.)):
        result += exact_source(xy+offset, phase, waves)
    return result


def linear_reading(train_columns, test_columns, train_target, test_target):
    matrix = np.column_stack((*train_columns, np.ones(len(train_target))))
    held_matrix = np.column_stack((*test_columns, np.ones(len(test_target))))
    coefficients, _, rank, singular = np.linalg.lstsq(matrix, train_target, rcond=None)
    train_error, test_error = matrix@coefficients-train_target, held_matrix@coefficients-test_target
    scales = np.std(matrix[:, :-1], axis=0)
    standardized = (matrix[:, :-1]-matrix[:, :-1].mean(axis=0))/np.maximum(scales, 1e-15)
    return dict(gain=float(coefficients[0]), bias=float(coefficients[2]),
                lap_coefficient=float(coefficients[1]),
                beta_source_native_squared=float(coefficients[1]/coefficients[0]),
                rank=int(rank), singular_values=singular.tolist(),
                standardized_condition=float(np.linalg.cond(np.column_stack((standardized, np.ones(len(matrix)))))),
                fit_rmse=float(np.sqrt(np.mean(train_error**2))),
                validation_rmse=float(np.sqrt(np.mean(test_error**2))),
                validation_max_abs=float(np.max(np.abs(test_error))),
                target_spatial_sd=float(np.std(train_target)),
                fit_samples=len(train_target), validation_samples=len(test_target))


def isolate(model, waves):
    """Known displacement, identity geometry, exact versus actual bilinear.

    The derivative in both arms is the SAME five-point finite difference.
    No translation fit can absorb interpolation's discrepancy in this layer.
    """
    train, test = model.grids(axis=1, phase=1)
    yy, xx = np.mgrid[:392, :392]
    raster_xy = np.column_stack((xx.ravel(), yy.ravel())).astype(np.float64)
    targets = [continuous_field(points, waves) for points in (train, test)]
    records = []
    for phase in ((0., 0.), (.5, .5), (.5, 0.)):
        image = exact_source(raster_xy, phase, waves).reshape(392, 392)
        derivative = laplace(image, mode='mirror')
        positions = [points+phase for points in (train, test)]
        arms = {}
        for mode in ('exact', 'bilinear'):
            columns = []
            for points in positions:
                if mode == 'exact':
                    columns.append((exact_source(points, phase, waves), exact_five_point(points, phase, waves)))
                else:
                    columns.append((model.sample(image, points), model.sample(derivative, points)))
            arms[mode] = linear_reading(*columns, *targets)
        integer_interior = raster_xy[(raster_xy[:, 0] > 1) & (raster_xy[:, 0] < 390) &
                                     (raster_xy[:, 1] > 1) & (raster_xy[:, 1] < 390)]
        # Cross-check the derivative convention directly, independently of beta.
        lap_difference = float(np.max(np.abs(model.sample(derivative, integer_interior)-
                                             exact_five_point(integer_interior, phase, waves))))
        records.append(dict(phase=list(phase), geometry='identity', motion='fixed-at-known-displacement',
                            scalar_blur_interpretation=phase != (.5, 0.),
                            no_physical_blur=True, phase_guide=False, source_dtype='float64', arms=arms,
                            raster_laplacian_vs_exact_five_point_integer_max_abs=lap_difference,
                            raster=array_binding(image), grids=[array_binding(train), array_binding(test)]))
    return records


def cubic_sample(image, xy):
    """One predeclared compact Catmull-Rom cubic convolution, 4x4 sites.

    Only this sampler replaces the old model.sample. Raster generation, phase
    guide, target sampling in original controls, derivative, objective, nuisance
    fit, optimizer, bars and holdout stay in the old unmodified source modules.
    There is no spline prefilter or globally supported preparation. The caller
    checks the expanded support radius. Accumulation is f64, rounded back to
    the guide dtype just as the original scipy bilinear sampler returns f32
    values for f32 guides.
    """
    assert np.isfinite(xy).all() and (xy >= 0).all()
    assert (xy[:, 0] < image.shape[1]-1).all() and (xy[:, 1] < image.shape[0]-1).all()
    floor = np.floor(xy).astype(np.int64)
    fraction = xy-floor
    weights = []
    for axis in (0, 1):
        t = fraction[:, axis]
        weights.append(np.column_stack((-.5*t+t*t-.5*t*t*t,
                                        1.-2.5*t*t+1.5*t*t*t,
                                        .5*t+2.*t*t-1.5*t*t*t,
                                        -.5*t*t+.5*t*t*t)))
    result = np.zeros(len(xy), dtype=np.float64)
    for iy in range(4):
        y = np.clip(floor[:, 1]+iy-1, 0, image.shape[0]-1)
        for ix in range(4):
            x = np.clip(floor[:, 0]+ix-1, 0, image.shape[1]-1)
            result += weights[0][:, ix]*weights[1][:, iy]*image[y, x]
    return result.astype(image.dtype).astype(np.float64)


def compact_support_fit(model):
    original_fit = model.fit

    def checked_fit(*args, **kwargs):
        axis = kwargs.get('axis', 0)
        radius = model.RADIUS+model.LAPLACIAN_RADIUS+model.MAX_SHIFT+model.FD_STEP+2
        gap = float(args[5][:, axis].min()-args[4][:, axis].max()-2*radius)
        if gap <= 0:
            raise ValueError('REFUSED: compact-cubic train/holdout source support overlaps')
        result = original_fit(*args, **kwargs)
        result['original_bilinear_support_gap_native'] = result['source_support_gap_native']
        result['source_support_gap_native'] = gap
        result['sampler_radius_native'] = 2
        return result

    return checked_fit


def saved_photo(out, qualified_from):
    """Separate mode: reuse the original nine-patch test only after qualification."""
    qualified_from = qualified_from.resolve()
    assert qualified_from.is_relative_to(HERE) and qualified_from != out
    result = json.loads((qualified_from/'result.json').read_text())
    process = json.loads((qualified_from/'process.json').read_text())
    assert result['saved_photo_phase_eligible'] and result['single_cubic']['passed']
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    sources = json.loads((qualified_from/'sources.json').read_text())
    assert all(binding(Path(row['path'])) == row for row in sources), 'Generated qualification sources changed.'
    measure = load('alignment_sampling_saved_photo_measure', PREVIOUS/'measure.py')
    original_load = measure.load

    def redirected_load(name, path):
        if name == 'chip_differential_blur_model':
            model = load('alignment_sampling_saved_photo_model', PREVIOUS/'implementation.py')
            model.sample = cubic_sample
            model.fit = compact_support_fit(model)
            return model
        if name == 'chip_differential_blur_independent_controls':
            return load('alignment_sampling_saved_photo_original_controls', PREVIOUS/'independent-controls.py')
        return original_load(name, path)

    write(out/'generated-qualification.json', dict(result=binding(qualified_from/'result.json'),
          process=binding(qualified_from/'process.json'), sources=binding(qualified_from/'sources.json'),
          substitution='compact Catmull-Rom sample and radius2 support guard only', raw_decodes=0))
    measure.load = redirected_load
    measure.HERE = HERE
    sys.argv = [str(PREVIOUS/'measure.py'), '--out', str(out)]
    measure.main()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--qualified-from', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and out.is_dir()
    if args.qualified_from is not None:
        saved_photo(out, args.qualified_from)
        return
    started = time.process_time()
    old_result_path = PREVIOUS/'run-1/result.json'
    old_result = json.loads(old_result_path.read_text())
    old_bindings = json.loads((PREVIOUS/'run-1/sources.json').read_text())
    for name in ('implementation.py', 'independent-controls.py'):
        actual = binding(PREVIOUS/name)
        expected = next(row for row in old_bindings if Path(row['path']).name == name)
        assert actual == expected, 'Original failed source changed; do not call a changed stimulus unchanged.'
    model = load('alignment_sampling_original_model', PREVIOUS/'implementation.py')
    original = load('alignment_sampling_original_controls', PREVIOUS/'independent-controls.py')
    review = load('alignment_sampling_independent_review', HERE/'independent-controls.py')
    write(out/'independent-commission.json', review.commission())

    # Preserve the historical failed assertion, then recover all lost readings.
    baseline = replay(original, model, out, 'original-bilinear')
    isolation = isolate(model, original.WAVES)
    write(out/'isolation.json', isolation)
    judgment = review.judge(isolation)
    write(out/'independent-isolation-judgment.json', judgment)
    repeat_confirmed = (not baseline['passed'] and baseline['error'] == old_result['error'] and
                        len(baseline['records']) == 2 and not baseline['records'][0]['joint'] and
                        baseline['records'][1]['joint'])
    cubic = None
    if repeat_confirmed and judgment['passed']:
        write(out/'independent-sampler-commission.json', review.commission_sampler(cubic_sample))
        # A separately imported module namespace prevents alteration of baseline.
        candidate = load('alignment_sampling_cubic_model', PREVIOUS/'implementation.py')
        candidate.sample = cubic_sample
        candidate.fit = compact_support_fit(candidate)
        cubic = replay(original, candidate, out, 'single-cubic')
        for a, b in zip(baseline['records'], cubic['records']):
            assert (a['input_arrays'], a['joint'], a['axis'], a['probe_deltas']) == \
                   (b['input_arrays'], b['joint'], b['axis'], b['probe_deltas']), \
                   'Sampler-only comparison changed its original input stimulus.'
    passes = bool(cubic and cubic['passed'])
    first_control_passes = bool(cubic and len(cubic['records']) >= 4)
    decision = ('ONE_CUBIC_SAMPLER_PASSES_ORIGINAL_GENERATED_CONTROLS' if passes else
                'STOP_GENERATED_SAMPLER_CORRECTION_NOT_ESTABLISHED')
    write(out/'result.json', dict(status=decision, original_refusal_reproduced=repeat_confirmed,
          historical_refusal=binding(old_result_path), historical_result=old_result,
          original_bilinear=baseline, isolated_sampler_effect=judgment,
          single_cubic=cubic, original_no_blur_beta_gate_repaired=first_control_passes,
          saved_photo_phase_eligible=passes, photographic_arrays_read=0, raw_decodes=0,
          interpretation='Generated operator evidence only. No photographic or geometric truth claim follows; saved-photo admission still needs root review.',
          cpu_seconds=time.process_time()-started, numpy=np.__version__, scipy=scipy.__version__))
    # Refusals above are scientific outcomes saved in full, not process errors.
    # The original beta bar is never altered; no additional kernel follows.
    print(json.dumps(dict(status=decision, original_refusal_reproduced=repeat_confirmed,
                          isolated_sampler_effect=judgment['passed'],
                          first_control_repaired=first_control_passes,
                          all_original_generated_controls_pass=passes)), flush=True)


if __name__ == '__main__':
    main()
