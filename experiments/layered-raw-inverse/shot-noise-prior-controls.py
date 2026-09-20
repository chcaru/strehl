"""Independent prior arithmetic and fixed-final image checks; no fitting."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import importlib.util
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('shot_prior_helpers', HERE / 'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read, inventory = common.sha, common.read, common.inventory


def literal(image, gain, readvar):
    # Independent f64 scalar oracle, not the f32 candidate image operator.
    h = np.sqrt(2) / gain * np.sqrt(gain * image.astype(np.float64) + readvar + 1 / 12)
    epsilon = 1e-12 / (2 * (gain * 2048 + readvar + 1 / 12))
    answer = 0.
    for axis in [0, 1]:
        magnitude = np.sqrt(np.sum(np.diff(h, axis=axis) ** 2, axis=-1) + epsilon)
        answer += np.mean(np.where(magnitude <= 2, .5 * magnitude ** 2, 2 * magnitude - 2)) / 2
    return float(answer)


def commission(control):
    author = common.load(HERE / 'shot-noise-prior.py', 'commissioned_shot_prior')
    gain, readvar = float(control.GAIN), float(control.READ_VARIANCE)
    config = SimpleNamespace(gain=gain, read_variance=readvar)
    scale = float(control.CEILING - control.BLACK)
    reference_scale = np.sqrt(2 * (gain * 2048 + readvar + 1 / 12))
    constant = torch.full((9, 11, 3), 2500., dtype=torch.float32, requires_grad=True)
    zero = author.image_huber_dn(constant, gain, readvar)
    assert float(zero.detach()) < 1e-12 and torch.equal(torch.autograd.grad(zero, constant)[0], torch.zeros_like(constant))
    y, x = np.mgrid[:9, :11].astype(np.float32)
    field = np.stack([700 + 130*x + 40*y, 1700 + 90*x - 20*y, 800 + 70*y + 10*x], -1)
    tensor = torch.from_numpy(field)
    actual = float(author.image_huber_dn(tensor, gain, readvar))
    expected = literal(field, gain, readvar)
    assert actual > .01 and abs(actual - expected) <= 5e-6 * max(1, expected)
    small = torch.from_numpy(np.broadcast_to((2048 + .05*x - .05*y)[..., None], field.shape).copy())
    old = float(author.model._vector_huber(small, reference_scale))
    new = float(author.image_huber_dn(small, gain, readvar))
    assert old > 0 and abs(new / old - 1) < .002
    direction = field - field.mean((0, 1), keepdims=True)
    coefficient = torch.tensor(0., requires_grad=True)
    value = author.image_huber_dn(tensor + coefficient * torch.from_numpy(direction), gain, readvar)
    derivative = float(torch.autograd.grad(value, coefficient)[0])
    step = .001
    fd = (literal(field.astype(np.float64) + step * direction, gain, readvar) - literal(field.astype(np.float64) - step * direction, gain, readvar)) / (2 * step)
    assert abs(derivative) > .01 and abs(fd - derivative) <= 1e-4 + .002 * abs(derivative)
    offset = torch.tensor(1000., requires_grad=True)
    brighter = author.image_huber_dn(tensor + offset, gain, readvar)
    brightness_derivative = float(torch.autograd.grad(brighter, offset)[0])
    brightness_fd = (literal(field + 1001, gain, readvar) - literal(field + 999, gain, readvar)) / 2
    assert float(brighter.detach()) < actual and brightness_derivative < 0
    assert abs(brightness_derivative - brightness_fd) <= 1e-7 + .002 * abs(brightness_derivative)
    alpha = torch.from_numpy(.2 + .01*x + .02*y)
    far_dn = tensor.flip(0) + 333
    state = SimpleNamespace(fields=lambda: (tensor / scale, far_dn / scale, alpha), far=True, dn_scale=scale)
    image_prior = float(author.shot_image_prior(state, config))
    total = float(author.selected_prior(state, config))
    a = alpha.numpy().astype(np.float64)
    image_expected = (expected + literal(far_dn.numpy(), gain, readvar)) / 2
    flux = (np.mean((field.astype(np.float64)/scale)**2) + np.mean((far_dn.numpy().astype(np.float64)/scale)**2)) / 2
    extras = .02*(np.abs(np.diff(a, axis=0)).mean()+np.abs(np.diff(a, axis=1)).mean())/2 + .002*np.mean(a*(1-a)) + .0001*flux
    assert abs(image_prior - image_expected) <= 5e-6 * max(1, image_expected)
    assert abs(total - (image_expected + extras)) <= 5e-6 * max(1, image_expected + extras)
    return dict(status='PASS', passed=True, literal_prior=expected, actual_prior=actual, constant_prior=float(zero.detach()),
        reference_2048_ratio=new/old, autograd=derivative, independent_finite_difference=fd,
        bright_offset_prior=float(brighter.detach()), brightness_derivative=brightness_derivative, brightness_finite_difference=brightness_fd,
        expected_risk='Equal DN edges cost less at higher brightness; denominator derivative is retained. This is not a calibration or utility result.')


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
        complete = verify(r, current, old, 'shot-noise-stabilized-sheets')
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
                bars[region+'_rgb'] = control.score(image, latent['truth'], region)['rgb_rmse'] <= 1.02*control.score(original, latent['truth'], region)['rgb_rmse']
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
    return dict(status='SHOT_NOISE_PRIOR_SCORED', cases=rows, all_fixed_checks_pass=all(r.get('fixed_checks_pass', False) for r in rows),
        all_stationary=all(r.get('stationary', False) for r in rows), original_screens_remain_failed=True, real_photo_admission=False,
        physical_adequacy=read(source / 'layered' / 'physical-adequacy.json'), source_immutable=True, outputs_immutable=True,
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
    print('SHOT_NOISE_PRIOR_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
