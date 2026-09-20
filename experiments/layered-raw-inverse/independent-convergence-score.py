"""Scores only prescribed final continuation outputs; never fits or selects."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ARMS = [('flat', 'two-layer'), ('far-only', 'far-only'), ('layered', 'two-layer')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def inventory(root):
    return {str(p.resolve()): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--continuation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, continued, out = args.source.resolve(), args.continuation.resolve(), args.out.resolve()
    assert source.is_dir() and continued.is_dir() and not out.exists()
    old_sources = read(source.parent / 'sources.json')
    for row in old_sources:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], str(path)
    original = inventory(source)
    new_files = inventory(continued)
    before_bindings = read(continued / 'bindings-before.json')
    assert before_bindings == read(continued / 'bindings-after.json')
    assert all(sha(path) == expected for path, expected in before_bindings.items())
    continuation = read(continued / 'result.json')
    assert Path(continuation['source_root']).resolve() == source and continuation['bindings_unchanged']
    prior = read(source / 'screen.json')
    assert prior['known_optics_utility_pass'] is False and prior['real_photo_admission'] is False
    bindings = read(source / 'bindings.json')
    assert sha(HERE / 'model.py') == bindings['model_sha256']
    assert sha(HERE / 'independent-controls.py') == bindings['controls_sha256']
    spec = importlib.util.spec_from_file_location('frozen_layered_controls', HERE / 'independent-controls.py')
    control = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = control
    spec.loader.exec_module(control)
    assert list(control.TRAIN) == bindings['train'] and list(control.HELD) == bindings['heldout']
    rows = []
    for name, arm in ARMS:
        old = source / name
        current = continued / name / arm
        receipt = read(current / 'receipt.json')
        old_receipt = read(old / arm / 'receipt.json')
        assert receipt['config'] == old_receipt['config']
        assert receipt['mode'] == old_receipt['mode']
        assert receipt['train_indices'] == old_receipt['train_indices'] == list(control.TRAIN)
        assert receipt['training_sha256'] == old_receipt['training_sha256']
        assert receipt['source_state_sha256'] == sha(old / arm / 'state.pt')
        assert receipt['state_sha256'] == sha(current / 'state.pt')
        assert receipt['read_indices'] == list(control.TRAIN)
        required = ['reconstruction.npz', 'predicted-cfa-2.npy', 'predicted-cfa-6.npy']
        missing = [p for p in required if not (current / p).is_file()]
        if missing or receipt['final_objective'] is None or receipt['status'] == 'numerical_refusal':
            rows.append(dict(name=name, arm=arm, measurement_complete=False, missing=missing,
                optimizer_status=receipt['status'], optimizer_error=receipt.get('error'),
                interpretation='Optimizer/export incomplete; not an image-quality rejection'))
            continue
        for prediction in receipt['predictions']:
            assert sha(current / prediction['path']) == prediction['sha256']
        raw = np.load(old / 'observations-u16.npy', allow_pickle=False)
        assert raw.dtype == np.uint16 and control.digest(raw) == read(old / 'result.json')['source_sha256']
        assert [control.digest(raw[k]) for k in control.TRAIN] == receipt['training_sha256']
        with np.load(current / 'reconstruction.npz', allow_pickle=False) as fields:
            candidate = fields['pinhole_rgb'].copy()
        assert candidate.dtype == np.float32 and candidate.shape == (96, 96, 3) and np.isfinite(candidate).all()
        latent = control.scene(name)
        truth = np.load(old / 'truth-rgb-f32.npy', allow_pickle=False)
        assert np.array_equal(truth, latent['truth'])
        mean = np.load(old / 'mean-rgb-f32.npy', allow_pickle=False)
        oracle = np.load(old / 'oracle-bound-rgb-f32.npy', allow_pickle=False)
        far = np.load(old / 'far-only-rgb-f32.npy', allow_pickle=False)
        quality = control.quality(name, latent, candidate, far, mean, oracle)
        predictions = []
        for k in control.HELD:
            expected_rgb = control.independent_forward(latent['near'], latent['far'], latent['alpha'], control.FOCI[k])
            expected = control.cfa_numpy(expected_rgb) + np.float32(control.BLACK)
            predicted = np.load(current / f'predicted-cfa-{k}.npy', allow_pickle=False)
            assert predicted.dtype == np.float32 and predicted.shape == raw[k].shape and np.isfinite(predicted).all()
            predictions.append(dict(index=k, scores=control.prediction_score(predicted, raw[k], expected)))
        prediction_pass = all(p['scores']['passed'] for p in predictions)
        final = receipt['final_objective']
        assert all(np.isfinite(float(final[key])) for key in ['data_nll', 'prior', 'total', 'gradient_l2', 'gradient_max'])
        old_row = read(old / 'result.json')
        rows.append(dict(name=name, arm=arm, measurement_complete=True, quality=quality, heldout=predictions,
            fixed_quality_pass=bool(quality['passed'] and prediction_pass),
            stationarity=dict(status=receipt['status'], final_objective=final,
                              stationary=receipt['status'] == 'stationary_gradient'),
            original_case_quality=old_row['quality'], original_heldout=old_row['heldout_prediction'],
            reference_scope='Final far-only vs frozen historical far-only, not two-layer admission' if name == 'far-only'
                            else 'Original fixed truth bars and historical references unchanged',
            final_checkpoint_sha256=sha(current / 'state.pt'), final_rgb_sha256=control.digest(candidate)))
    assert inventory(source) == original and inventory(continued) == new_files
    for row in old_sources:
        assert sha(row['path']) == row['sha256']
    physical = read(source / 'layered' / 'physical-adequacy.json')
    complete = all(r['measurement_complete'] for r in rows)
    result = dict(status='FINAL_CHECKPOINTS_SCORED', arms=rows,
        measurement_complete=complete,
        all_fixed_quality_bars_pass=all(r['fixed_quality_pass'] for r in rows) if complete else None,
        all_stationary=all(r['stationarity']['stationary'] for r in rows) if complete else None,
        original_160_step_screen_still_failed=True, physical_adequacy=physical,
        real_photo_admission=False, source_immutable=True, continuation_immutable=True,
        source_files=original, continued_files=new_files,
        scorer_sha256=sha(__file__), frozen_model_sha256=bindings['model_sha256'],
        scope='Unchanged-objective convergence diagnostic; no iteration chosen by truth and no canonical/SOTA claim')
    out.mkdir(parents=True)
    control.save(out / 'result.json', result)
    print('LAYERED_CONVERGENCE_SCORE', json.dumps({k: result[k] for k in
          ['all_fixed_quality_bars_pass', 'all_stationary', 'real_photo_admission']}), flush=True)


if __name__ == '__main__':
    main()
