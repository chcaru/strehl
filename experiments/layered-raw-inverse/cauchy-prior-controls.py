"""Independent fixed Cauchy-prior commission and final scoring; never fits."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import importlib.util
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cauchy_prior_helpers', HERE / 'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read, inventory = common.sha, common.read, common.inventory


def literal(image, scale):
    # Independent f64 scalar arithmetic oracle; candidate remains f32.
    result = 0.
    for axis in [0, 1]:
        squared = (np.sum(np.diff(image.astype(np.float64), axis=axis)**2, axis=-1) + 1e-12) / scale**2
        result += np.mean(2*np.log1p(squared/4))/2
    return float(result)


def commission(control):
    author = common.load(HERE / 'cauchy-prior.py', 'commissioned_cauchy_prior')
    gain, readvar = float(control.GAIN), float(control.READ_VARIANCE)
    config = SimpleNamespace(gain=gain, read_variance=readvar)
    scale = np.sqrt(2*(gain*2048 + readvar + 1/12))
    dn_scale = float(control.CEILING-control.BLACK)
    constant = torch.full((9, 11, 3), 2500., dtype=torch.float32, requires_grad=True)
    floor = author.image_cauchy_dn(constant, gain, readvar)
    expected_floor = 2*np.log1p(1e-12/(4*scale**2))
    assert abs(float(floor.detach())/expected_floor-1) < 1e-5
    assert torch.equal(torch.autograd.grad(floor, constant)[0], torch.zeros_like(constant))
    y, x = np.mgrid[:9, :11].astype(np.float32)
    field = np.stack([700+130*x+40*y, 1700+90*x-20*y, 800+70*y+10*x], -1)
    tensor = torch.from_numpy(field)
    expected = literal(field, scale)
    actual = float(author.image_cauchy_dn(tensor, gain, readvar))
    assert actual > .01 and abs(actual-expected) <= 5e-6*max(1, expected)
    offset = torch.tensor(1000., requires_grad=True)
    translated = author.image_cauchy_dn(tensor+offset, gain, readvar)
    brightness_derivative = float(torch.autograd.grad(translated, offset)[0])
    assert float(translated.detach()) == actual and abs(brightness_derivative) < 1e-7
    rows = []
    for magnitude in [0., .001, .1, 1., 2., 4., 16., 64.]:
        s = torch.tensor(magnitude, dtype=torch.float32, requires_grad=True)
        edge = s*float(scale/np.sqrt(3))*torch.ones(3)
        image = torch.stack([torch.zeros(3), edge]).unsqueeze(0).repeat(2, 1, 1)
        penalty = author.image_cauchy_dn(image, gain, readvar)
        # Only horizontal edges are live; undo its one-half spatial-direction mean.
        first = torch.autograd.grad(penalty, s, create_graph=magnitude == 0, retain_graph=magnitude == 0)[0]
        derivative = 2*float(first.detach())
        expected_derivative = magnitude/(1+magnitude*magnitude/4)
        assert abs(derivative-expected_derivative) <= 1e-7+5e-5*abs(expected_derivative)
        assert abs(float(penalty.detach())-literal(image.detach().numpy(), scale)) <= 5e-6*max(1, float(penalty.detach()))
        row = dict(s=magnitude, derivative=derivative, expected_derivative=expected_derivative, penalty=float(penalty.detach()))
        if magnitude == 0:
            curvature = 2*float(torch.autograd.grad(first, s, retain_graph=True)[0])
            old_zero = author.model._vector_huber(image, scale)
            old_first = torch.autograd.grad(old_zero, s, create_graph=True)[0]
            old_curvature = 2*float(torch.autograd.grad(old_first, s)[0])
            assert abs(curvature-1) < 2e-6 and abs(curvature-old_curvature) < 2e-6
            row.update(zero_curvature=curvature, original_zero_curvature=old_curvature)
        if magnitude == .001:
            original = float(author.model._vector_huber(image, scale).detach())
            row['small_gradient_original_ratio'] = float(penalty.detach())/original
            assert original > 0 and abs(row['small_gradient_original_ratio']-1) < 1e-4
        rows.append(row)
    slopes = {row['s']: row['derivative'] for row in rows}
    assert slopes[2.] > slopes[4.] > slopes[16.] > slopes[64.] > 0
    impulse_s = torch.tensor(16., requires_grad=True)
    impulse_shape = torch.zeros((9, 11, 3))
    impulse_shape[4, 5] = float(scale/np.sqrt(3))
    impulse = impulse_s*impulse_shape
    force = float(torch.autograd.grad(author.image_cauchy_dn(impulse, gain, readvar), impulse_s, retain_graph=True)[0])
    old_force = float(torch.autograd.grad(author.model._vector_huber(impulse, scale), impulse_s)[0])
    edge_factor = 1/((9-1)*11) + 1/(9*(11-1))  # two incident edges per spatial direction, each direction weighted one-half
    assert abs(force-edge_factor*16/65) < 1e-7 and abs(old_force-edge_factor*2) < 1e-7
    assert 0 < force < old_force
    alpha = torch.from_numpy(.2+.01*x+.02*y)
    far_dn = 1.5*tensor.flip(0)+333
    state = SimpleNamespace(fields=lambda: (tensor/dn_scale, far_dn/dn_scale, alpha), far=True, dn_scale=dn_scale)
    image_expected = (expected+literal(far_dn.numpy(), scale))/2
    a = alpha.numpy().astype(np.float64)
    flux = (np.mean((field.astype(np.float64)/dn_scale)**2)+np.mean((far_dn.numpy().astype(np.float64)/dn_scale)**2))/2
    extra = .02*(np.abs(np.diff(a, axis=0)).mean()+np.abs(np.diff(a, axis=1)).mean())/2 + .002*np.mean(a*(1-a)) + .0001*flux
    assert abs(float(author.cauchy_image_prior(state, config))-image_expected) <= 5e-6*max(1, image_expected)
    assert abs(float(author.selected_prior(state, config))-(image_expected+extra)) <= 5e-6*max(1, image_expected+extra)
    return dict(status='PASS', passed=True, actual_prior=actual, literal_prior=expected, constant_floor=float(floor.detach()),
        brightness_translation_exact=True, brightness_derivative=brightness_derivative, derivative_cases=rows,
        isolated_impulse=dict(native_xy=[5, 4], s=16, incident_edges=4, edge_mean_factor=edge_factor,
                              cauchy_force=force, huber_force=old_force, ratio=force/old_force),
        expected_risk='Restoring force decreases beyond s2; a large spurious edge can persist. Arithmetic pass is not a quality or noise-calibration claim.')


def verify(receipt, directory, old, kind):
    start = read(old / 'two-layer' / 'receipt.json')
    assert receipt['config'] == start['config'] and receipt['mode'] == 'two-layer' and receipt['prior_kind'] == kind
    assert receipt['source_state_sha256'] == sha(old / 'two-layer' / 'state.pt')
    assert receipt['training_sha256'] == start['training_sha256'] and receipt['read_indices'] == receipt['train_indices'] == start['train_indices']
    assert receipt['visibility'] == 'oracle-fixed' and receipt['fixed_alpha_exact']
    assert receipt['initial_sheet_parameters_exact'] and receipt['initial_sheet_images_exact'] and receipt['gradient_parameter_names'] == ['near', 'far']
    assert receipt['source_bindings_unchanged'] and 1 <= receipt['actual_evaluations'] <= 1800
    assert receipt['actual_evaluations'] == len(receipt['closure_history'])
    completed = [r for r in receipt['closure_history'] if r['evaluation_status'] == 'complete']
    assert len(completed) == receipt['completed_evaluations'] and all(r['gradient_storage_logical_exact'] for r in completed)
    for binding in receipt['source_bindings'].values():
        assert sha(binding['path']) == binding['sha256']
    if receipt['status'] == 'numerical_refusal' or receipt['final_objective'] is None:
        return False
    assert receipt['returned_state_accepted'] and receipt['final_objective']['gradient_storage_logical_exact']
    assert receipt['state_sha256'] == sha(directory / 'state.pt')
    assert sorted(p['index'] for p in receipt['predictions']) == [2, 6]
    for p in receipt['predictions']:
        assert sha(directory / p['path']) == p['sha256']
    return True


def score(control, source, candidate, reference):
    roots = [source, candidate, reference]
    before = [inventory(p) for p in roots]
    rows = []
    for name in ['flat', 'layered']:
        old, current, paired = source / name, candidate / name / 'fixed-alpha', reference / name / 'fixed-alpha'
        r, p = read(current / 'receipt.json'), read(paired / 'receipt.json')
        complete = verify(r, current, old, 'cauchy-original-scale-sheets')
        reference_complete = verify(p, paired, old, 'original')
        latent = control.scene(name)
        assert np.array_equal(latent['truth'], np.load(old / 'truth-rgb-f32.npy', allow_pickle=False))
        with np.load(current / 'initial-reconstruction.npz', allow_pickle=False) as a, np.load(paired / 'initial-reconstruction.npz', allow_pickle=False) as b:
            assert all(np.array_equal(a[k], b[k]) for k in ['near_rgb', 'far_rgb', 'alpha', 'pinhole_rgb'])
        if not complete or not reference_complete:
            rows.append(dict(name=name, complete=False, status=r['status'], reference_status=p['status']))
            continue
        with np.load(current / 'reconstruction.npz', allow_pickle=False) as a, np.load(paired / 'reconstruction.npz', allow_pickle=False) as b:
            image, original = a['pinhole_rgb'].copy(), b['pinhole_rgb'].copy()
            assert np.array_equal(a['alpha'], latent['alpha']) and np.array_equal(b['alpha'], latent['alpha'])
        assert all(x.dtype == np.float32 and x.shape == (96, 96, 3) and np.isfinite(x).all() for x in [image, original])
        references = [np.load(old / f'{label}-rgb-f32.npy', allow_pickle=False) for label in ['far-only', 'mean', 'oracle-bound']]
        quality = control.quality(name, latent, image, *references)
        raw = np.load(old / 'observations-u16.npy', allow_pickle=False)
        assert raw.dtype == np.uint16 and control.digest(raw) == read(old / 'result.json')['source_sha256']
        assert [control.digest(raw[k]) for k in control.TRAIN] == r['training_sha256']
        held = []
        for k in control.HELD:
            expected = control.cfa_numpy(control.independent_forward(latent['near'], latent['far'], latent['alpha'], control.FOCI[k])) + np.float32(control.BLACK)
            prediction = np.load(current / f'predicted-cfa-{k}.npy', allow_pickle=False)
            assert prediction.dtype == np.float32 and prediction.shape == raw[k].shape and np.isfinite(prediction).all()
            held.append(dict(index=k, scores=control.prediction_score(prediction, raw[k], expected)))
        bars, components, flat_description = {}, {}, {}
        if name == 'flat':
            a, b = control.score(image, latent['truth']), control.score(original, latent['truth'])
            bars = {key: a[key] <= 1.05*b[key] for key in ['rgb_rmse', 'chroma_rmse']}
            for label, value in [('candidate', image), ('reference', original)]:
                delta = (value-latent['truth'])[control.region_slice('whole')].astype(np.float64)
                flat_description[label] = dict(mean_bias_dn=delta.mean((0, 1)).tolist(), signed_error_p01_dn=np.quantile(delta, .01, axis=(0, 1)).tolist(), signed_error_p99_dn=np.quantile(delta, .99, axis=(0, 1)).tolist())
        else:
            for region in ['core', 'ridge']:
                for metric in ['rgb_rmse', 'chroma_rmse']:
                    bars[region+'_'+metric] = control.score(image, latent['truth'], region)[metric] <= 1.02*control.score(original, latent['truth'], region)[metric]
            for label, region in [('glint', 'core'), ('ridge', 'ridge-detail')]:
                a, b = control.component(image, latent, label, region), control.component(original, latent, label, region)
                ra, rb = np.array(a['recovery']), np.array(b['recovery'])
                bars[label+'_component'] = a['live'] and b['live'] and bool(np.all(rb >= .5) and np.all(np.clip(ra, 0, 1) >= .98*np.minimum(rb, 1)))
                components[label] = dict(candidate=a, reference=b)
        rows.append(dict(name=name, complete=True, quality=quality, heldout=held, paired_bars=bars, paired_components=components,
            flat_bias_descriptive=flat_description, fixed_checks_pass=bool(quality['passed'] and all(h['scores']['passed'] for h in held) and all(bars.values())),
            status=r['status'], stationary=r['status']=='stationary_gradient', final_objective=r['final_objective'],
            reference_status=p['status'], reference_final_objective=p['final_objective'], rgb_sha256=control.digest(image)))
    assert [inventory(p) for p in roots] == before
    return dict(status='CAUCHY_PRIOR_SCORED', cases=rows, all_fixed_checks_pass=all(r.get('fixed_checks_pass', False) for r in rows),
        all_stationary=all(r.get('stationary', False) for r in rows), original_screens_remain_failed=True, real_photo_admission=False,
        physical_adequacy=read(source / 'layered' / 'physical-adequacy.json'), source_immutable=True, outputs_immutable=True,
        next_scope='A two-case pass licenses only a separately fixed weak-ramp/new-seed stress test, not photographs',
        shot_prior_descriptive_sha256=sha(HERE / 'shot-prior-1' / 'scored' / 'result.json'),
        source_files=before[0], candidate_files=before[1], reference_files=before[2])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['commission', 'score'])
    parser.add_argument('--source', type=Path, default=HERE / 'screen-1' / 'output')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert not out.exists()
    control = common.frozen(source)
    if args.mode == 'commission':
        result = commission(control)
    else:
        assert args.candidate is not None and args.reference is not None
        result = score(control, source, args.candidate.resolve(), args.reference.resolve())
    result['controls_sha256'] = sha(__file__)
    out.mkdir(parents=True)
    control.save(out / 'result.json', result)
    print('CAUCHY_PRIOR_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
