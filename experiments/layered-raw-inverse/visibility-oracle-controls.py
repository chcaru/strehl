"""Independent alpha-only export and fixed-final scoring; never fits a model."""
from pathlib import Path
import argparse
import numpy as np
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('visibility_scoring_helpers', HERE / 'independent-composite-score.py')
helpers = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)
sha, read, inventory, load = helpers.sha, helpers.read, helpers.inventory, helpers.load
CASES = ['flat', 'layered']
CONTROL_HASH = '6915c024dbbfaa0e0d912ecba1a22075aabce6ef29c845f0e586472be60815ec'
MODEL_HASH = '5710146ffcf463de85e317050bc81357922965d6006c7b4cf311f4d80d8ee512'


def frozen(source):
    assert sha(HERE / 'independent-controls.py') == CONTROL_HASH
    assert sha(HERE / 'model.py') == MODEL_HASH
    for row in read(source.parent / 'sources.json'):
        assert sha(row['path']) == row['sha256']
    bindings = read(source / 'bindings.json')
    assert bindings['model_sha256'] == MODEL_HASH and bindings['controls_sha256'] == CONTROL_HASH
    control = load(HERE / 'independent-controls.py', 'visibility_frozen_truth')
    assert list(control.TRAIN) == bindings['train'] and list(control.HELD) == bindings['heldout']
    return control


def prepare(control, source, out):
    before = inventory(source)
    out.mkdir(parents=True)
    rows = []
    for case in CASES:
        alpha = np.ascontiguousarray(control.scene(case)['alpha'], dtype=np.float32)
        assert alpha.shape == (96, 96) and np.isfinite(alpha).all() and ((alpha >= 0) & (alpha <= 1)).all()
        path = out / f'{case}-alpha-f32.npy'
        np.save(path, alpha, allow_pickle=False)
        rows.append(dict(case=case, path=str(path), sha256=sha(path), array_sha256=control.digest(alpha),
                         shape=list(alpha.shape), dtype=str(alpha.dtype), minimum=float(alpha.min()), maximum=float(alpha.max())))
    assert inventory(source) == before
    result = dict(status='ALPHA_ONLY_PREPARED', arrays=rows, controls_sha256=CONTROL_HASH, model_sha256=MODEL_HASH,
                  exporter_sha256=sha(__file__), source_root=str(source), source_immutable=True,
                  scope='Known synthetic coverage only; no truth radiances or heldout observations exported')
    control.save(out / 'manifest.json', result)
    return result


def receipt_checks(receipt, directory, start, source_state):
    assert receipt['config'] == start['config'] and receipt['mode'] == 'two-layer'
    assert receipt['prior_kind'] == 'original' and receipt['source_state_sha256'] == sha(source_state)
    assert receipt['training_sha256'] == start['training_sha256']
    assert receipt['train_indices'] == start['train_indices'] == receipt['read_indices']
    assert receipt['source_bindings_unchanged'] and 1 <= receipt['actual_evaluations'] <= 1800
    assert len(receipt['closure_history']) == receipt['actual_evaluations']
    completed = [r for r in receipt['closure_history'] if r['evaluation_status'] == 'complete']
    assert len(completed) == receipt['completed_evaluations']
    assert all(r['gradient_storage_logical_exact'] for r in completed)
    for binding in receipt['source_bindings'].values():
        assert sha(binding['path']) == binding['sha256']
    complete = receipt['status'] != 'numerical_refusal' and receipt['final_objective'] is not None
    if complete:
        assert receipt['returned_state_accepted'] and receipt['final_objective']['gradient_storage_logical_exact']
        assert receipt['state_sha256'] == sha(directory / 'state.pt')
        assert sorted(p['index'] for p in receipt['predictions']) == [2, 6]
        for p in receipt['predictions']:
            assert sha(directory / p['path']) == p['sha256']
    return complete


def score(control, source, oracle, reference):
    roots = [source, oracle, reference]
    before = [inventory(p) for p in roots]
    result = read(oracle / 'result.json')
    assert Path(result['source_root']).resolve() == source
    alpha_root = Path(result['alpha_directory']).resolve()
    alpha_before = inventory(alpha_root)
    manifest = read(alpha_root / 'manifest.json')
    assert manifest['controls_sha256'] == CONTROL_HASH and manifest['model_sha256'] == MODEL_HASH
    assert manifest['exporter_sha256'] == sha(__file__)
    assert sorted(row['case'] for row in manifest['arrays']) == sorted(CASES)
    records = []
    for case in CASES:
        old, current, paired = source / case, oracle / case / 'fixed-alpha', reference / case / 'original'
        start = read(old / 'two-layer' / 'receipt.json')
        receipt, ref_receipt = read(current / 'receipt.json'), read(paired / 'receipt.json')
        complete = receipt_checks(receipt, current, start, old / 'two-layer' / 'state.pt')
        reference_complete = receipt_checks(ref_receipt, paired, start, old / 'two-layer' / 'state.pt')
        assert ref_receipt['initial_checkpoint_exact']
        assert receipt['visibility'] == 'oracle-fixed' and receipt['gradient_parameter_names'] == ['near', 'far']
        assert receipt['fixed_alpha_exact'] and receipt['initial_sheet_parameters_exact'] and receipt['initial_sheet_images_exact']
        alpha_path = alpha_root / f'{case}-alpha-f32.npy'
        entry = next(row for row in manifest['arrays'] if row['case'] == case)
        assert Path(entry['path']).resolve() == alpha_path and sha(alpha_path) == entry['sha256'] == receipt['alpha_sha256']
        latent = control.scene(case)
        alpha = np.load(alpha_path, allow_pickle=False)
        assert alpha.dtype == np.float32 and np.array_equal(alpha, latent['alpha'])
        assert control.digest(alpha) == entry['array_sha256']
        assert np.array_equal(latent['truth'], np.load(old / 'truth-rgb-f32.npy', allow_pickle=False))
        raw = np.load(old / 'observations-u16.npy', allow_pickle=False)
        assert raw.dtype == np.uint16 and control.digest(raw) == read(old / 'result.json')['source_sha256']
        assert [control.digest(raw[k]) for k in control.TRAIN] == receipt['training_sha256']
        with np.load(current / 'initial-reconstruction.npz', allow_pickle=False) as initial, np.load(old / 'two-layer' / 'reconstruction.npz', allow_pickle=False) as previous:
            assert np.array_equal(initial['alpha'], alpha)
            assert all(np.array_equal(initial[k], previous[k]) for k in ['near_rgb', 'far_rgb'])
            initial_image = initial['pinhole_rgb'].copy()
            change = float(np.max(np.abs(initial_image - previous['pinhole_rgb'])))
            assert change == receipt['initial_pinhole_max_abs_change_dn'] and change > 0
        assert initial_image.dtype == np.float32 and initial_image.shape == (96, 96, 3) and np.isfinite(initial_image).all()
        references = [np.load(old / f'{label}-rgb-f32.npy', allow_pickle=False) for label in ['far-only', 'mean', 'oracle-bound']]
        initial_quality = control.quality(case, latent, initial_image, *references)
        if not complete or not reference_complete:
            records.append(dict(name=case, complete=False, status=receipt['status'], reference_status=ref_receipt['status'],
                                initial_quality=initial_quality,
                                interpretation='Incomplete optimizer arm; not an image-quality measurement'))
            continue
        with np.load(current / 'reconstruction.npz', allow_pickle=False) as fields:
            image = fields['pinhole_rgb'].copy()
            assert np.array_equal(fields['alpha'], alpha)
        with np.load(paired / 'reconstruction.npz', allow_pickle=False) as fields:
            free_image = fields['pinhole_rgb'].copy()
        assert all(a.dtype == np.float32 and a.shape == (96, 96, 3) and np.isfinite(a).all() for a in [image, free_image])
        quality = control.quality(case, latent, image, *references)
        held = []
        for k in control.HELD:
            rgb = control.independent_forward(latent['near'], latent['far'], latent['alpha'], control.FOCI[k])
            expected = control.cfa_numpy(rgb) + np.float32(control.BLACK)
            predicted = np.load(current / f'predicted-cfa-{k}.npy', allow_pickle=False)
            assert predicted.dtype == np.float32 and predicted.shape == raw[k].shape and np.isfinite(predicted).all()
            held.append(dict(index=k, scores=control.prediction_score(predicted, raw[k], expected)))
        bars, components = {}, {}
        if case == 'flat':
            a, b = control.score(image, latent['truth']), control.score(free_image, latent['truth'])
            bars = {k: a[k] <= 1.05 * b[k] for k in ['rgb_rmse', 'chroma_rmse']}
        else:
            for region in ['core', 'ridge']:
                a, b = control.score(image, latent['truth'], region), control.score(free_image, latent['truth'], region)
                bars[region + '_rgb'] = a['rgb_rmse'] <= 1.02 * b['rgb_rmse']
            for name, region in [('glint', 'core'), ('ridge', 'ridge-detail')]:
                a, b = control.component(image, latent, name, region), control.component(free_image, latent, name, region)
                ra, rb = np.array(a['recovery']), np.array(b['recovery'])
                passed = a['live'] and b['live'] and bool(np.all(rb >= .5) and np.all(np.clip(ra, 0, 1) >= .98 * np.minimum(rb, 1)))
                bars[name + '_component'] = passed
                components[name] = dict(fixed=a, free=b, passed=passed)
        held_pass = all(h['scores']['passed'] for h in held)
        records.append(dict(name=case, complete=True, initial_quality=initial_quality, quality=quality, heldout=held, heldout_pass=held_pass,
            paired_bars=bars, paired_components=components, fixed_checks_pass=bool(quality['passed'] and held_pass and all(bars.values())),
            status=receipt['status'], stationary=receipt['status'] == 'stationary_gradient', final_objective=receipt['final_objective'],
            free_status=ref_receipt['status'], free_final_objective=ref_receipt['final_objective'],
            initial_pinhole_max_abs_change_dn=receipt['initial_pinhole_max_abs_change_dn'], rgb_sha256=control.digest(image)))
    assert [inventory(p) for p in roots] == before and inventory(alpha_root) == alpha_before
    return dict(status='FIXED_VISIBILITY_SCORED', cases=records, all_complete=all(r['complete'] for r in records),
        all_fixed_checks_pass=all(r.get('fixed_checks_pass', False) for r in records),
        all_stationary=all(r.get('stationary', False) for r in records), source_immutable=True, outputs_immutable=True,
        physical_adequacy=read(source / 'layered' / 'physical-adequacy.json'), source_files=before[0], oracle_files=before[1], reference_files=before[2],
        original_screens_remain_failed=True, real_photo_admission=False,
        scope='Known-alpha degree-of-freedom diagnostic with unchanged original sheet prior; no automatic visibility or calibrated-camera claim')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'score'])
    parser.add_argument('--source', type=Path, default=HERE / 'screen-1' / 'output')
    parser.add_argument('--oracle', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert not out.exists()
    control = frozen(source)
    if args.mode == 'prepare':
        result = prepare(control, source, out)
    else:
        assert args.oracle is not None and args.reference is not None
        result = score(control, source, args.oracle.resolve(), args.reference.resolve())
        result['scorer_sha256'] = sha(__file__)
        out.mkdir(parents=True)
        control.save(out / 'result.json', result)
    print('VISIBILITY_ORACLE_' + args.mode.upper(), {k: result[k] for k in ['status', 'all_fixed_checks_pass', 'all_stationary'] if k in result}, flush=True)


if __name__ == '__main__':
    main()
