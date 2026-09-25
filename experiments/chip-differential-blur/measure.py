"""One bounded execution after independent synthetic controls; no RAW imports."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import time
import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SAMPLES = ROOT/'experiments/quality-september14/joint-raw-samples-2'
FROZEN = ROOT/'experiments/quality-september14/local-green-translation-1/result.json'


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and out.is_dir()
    started = time.process_time()
    model = load('chip_differential_blur_model', HERE/'implementation.py')
    verifier = load('chip_differential_blur_independent_controls', HERE/'independent-controls.py')
    # This path MUST complete before opening any photographic CFA array.
    try:
        controls = verifier.controls(model)
        write(out/'controls.json', controls)
    except Exception as error:
        write(out/'result.json', dict(status='STOP_SYNTHETIC_MODEL_SCREEN_FAILED', error=repr(error),
                                     photographic_arrays_read=0, raw_decodes=0, cpu_seconds=time.process_time()-started))
        raise
    receipt = json.loads((SAMPLES/'receipt.json').read_text())
    old = json.loads(FROZEN.read_text())
    old_by_frame = {row['frame']: row for row in old['frames']}
    assert receipt['reference_index'] == 149 and receipt['target_shape'] == [392, 392]
    assert [row['index'] for row in receipt['frames']] == list(range(145, 154))
    before = [binding(SAMPLES/'receipt.json'), binding(FROZEN)]
    origin = receipt['target_origin_native']
    sensor_h, sensor_w = receipt['native_sensor_shape']
    centre = complex(sensor_w/2, sensor_h/2)
    guides = {}
    for record in receipt['frames']:
        path = SAMPLES/f"frame-{record['index']}-cfa.npy"
        before.append(binding(path))
        raw = np.load(path, allow_pickle=False)
        assert raw.dtype == np.uint16 and raw.shape == tuple(reversed(record['source_xywh'][2:]))
        assert hashlib.sha256(raw.tobytes()).hexdigest() == record['raw_u16_sha256']
        black, white = map(np.float32, receipt['levels'])
        normalized = (raw.astype(np.float32)-black)/(white-black)
        guides[record['index']] = [model.guide(normalized, record['source_xywh'][:2], raw < 16383, phase)
                                    for phase in (0, 1)]
    reference = receipt['frames'][4]

    def positions(points, record):
        return model.mapped(points, origin, centre, complex(*record['a']), complex(*record['b_plane']), record['source_xywh'][:2])

    rows = []
    for axis in (0, 1):
        for phase in (0, 1):
            train, test = model.grids(axis, phase, origin)
            reference_values = [model.sample(guides[149][p], positions(xy, reference))
                                for p, xy in ((phase, train), (1-phase, test))]
            for record in receipt['frames']:
                index = record['index']
                source_xy = [positions(xy, record) for xy in (train, test)]
                arms = [model.fit(guides[index][phase], guides[index][1-phase], *reference_values,
                                  *source_xy, axis=axis, joint=joint) for joint in (False, True)]
                a, b = arms
                frozen = np.asarray(old_by_frame[index]['delta_source_native'])
                scale = complex(*record['a'])
                for arm in arms:
                    delta = complex(*arm['delta_source_native'])/scale
                    arm['delta_reference149_native'] = [delta.real, delta.imag]
                    arm['inverse_observation_delta_reference149_native'] = [-delta.real, -delta.imag]
                    arm['change_from_frozen_source_native'] = float(np.linalg.norm(np.asarray(arm['delta_source_native'])-frozen))
                row = dict(frame=index, train_phase='G1' if phase == 0 else 'G2',
                           test_phase='G2' if phase == 0 else 'G1', support='left-right' if axis == 0 else 'top-bottom',
                           translation=a, joint=b, frozen_delta_source_native=frozen.tolist(),
                           frozen_at_bound=old_by_frame[index]['at_translation_bound'],
                           incremental_holdout_rmse_ratio=b['after']['validation_rmse']/max(a['after']['validation_rmse'], 1e-15),
                           joint_shift_change_reference149_native=float(np.linalg.norm(np.subtract(
                               a['delta_reference149_native'], b['delta_reference149_native']))))
                rows.append(row)
                print(json.dumps({k: row[k] for k in ('frame', 'train_phase', 'support', 'incremental_holdout_rmse_ratio', 'joint_shift_change_reference149_native')}), flush=True)
    stability = []
    for index in range(145, 154):
        choices = [row for row in rows if row['frame'] == index]
        deltas = [np.asarray(row['joint']['delta_reference149_native']) for row in choices]
        spread = max(float(np.linalg.norm(a-b)) for a in deltas for b in deltas)
        betas = [row['joint']['beta_source_native_squared'] for row in choices]
        nonzero = [np.sign(v) for v in betas if abs(v) > .02]
        sign_stable = not nonzero or len(set(nonzero)) == 1
        all_admitted = all(row[arm]['admitted'] for row in choices for arm in ('translation', 'joint'))
        predictive = all(row['incremental_holdout_rmse_ratio'] < .95 for row in choices)
        stability.append(dict(frame=index, joint_phase_support_spread_reference149_native=spread,
                              betas_source_native_squared=betas, coefficient_sign_stable=sign_stable,
                              all_fits_admitted=all_admitted, all_holdout_improve_at_least_five_percent=predictive,
                              stable=all_admitted and spread <= .25 and sign_stable,
                              historical_boundary_refusal=index == 145, reference_identity=index == 149))
    eligible = [row for row in stability if row['frame'] not in (145, 149)]
    stable = all(row['stable'] for row in eligible)
    identifiable = stable and all(row['all_holdout_improve_at_least_five_percent'] for row in eligible)
    assert all(binding(Path(row['path'])) == row for row in before), 'Saved inputs changed.'
    write(out/'result.json', dict(status='LOCAL_BLUR_MODEL_TRANSFERRED' if identifiable else 'STOP_LOCAL_BLUR_NOT_IDENTIFIED',
         interpretation='Local model identifiability only; no camera-motion, PSF calibration, photographic improvement, or generalization claim.',
         frames=rows, stability=stability, all_eligible_stable=stable, incremental_blur_identified=identifiable,
         excluded_from_admission=[dict(frame=145, reason='historical translation bound'), dict(frame=149, reason='reference identity')],
         thresholds=dict(phase_support_spread_native=.25, sign_dead_zone_beta=.02, maximum_abs_beta=1., maximum_incremental_rmse_ratio=.95),
         source_bindings=before, source_map_sha256=receipt['map_sha256'], saved_photographic_arrays_read=9, raw_decodes=0,
         cpu_seconds=time.process_time()-started, numpy=np.__version__, scipy=scipy.__version__))


if __name__ == '__main__':
    main()
