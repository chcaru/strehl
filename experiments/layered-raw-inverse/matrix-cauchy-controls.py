"""Independent matrix-prior calculus and fixed-final image checks; never fits."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import importlib.util
import sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('matrix_prior_helpers', HERE / 'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read, inventory = common.sha, common.read, common.inventory


def literal_edges(dx, dy):
    jacobian = np.stack([np.asarray(dx, np.float64), np.asarray(dy, np.float64)], -1)
    gram = np.swapaxes(jacobian, -1, -2) @ jacobian
    eigen = np.linalg.eigvalsh(gram)
    assert eigen.min() >= -1e-10
    value = np.log1p(np.maximum(eigen, 0)/4).sum(-1)
    determinant = np.log(np.linalg.det(np.eye(2)+gram/4))
    assert np.allclose(value, determinant, rtol=2e-12, atol=1e-12)
    return value


def literal_image(image, scale):
    image = np.asarray(image, np.float64)
    h, w, _ = image.shape
    dx, dy = np.zeros_like(image), np.zeros_like(image)
    dx[:, :-1] = np.diff(image, axis=1)*np.sqrt(w/(w-1))/scale
    dy[:-1] = np.diff(image, axis=0)*np.sqrt(h/(h-1))/scale
    return float(literal_edges(dx, dy).mean())


def commission(control):
    author = common.load(HERE / 'matrix-cauchy-prior.py', 'commissioned_matrix_prior')
    gain, readvar = float(control.GAIN), float(control.READ_VARIANCE)
    config = SimpleNamespace(gain=gain, read_variance=readvar)
    scale, dn_scale = np.sqrt(2*(gain*2048+readvar+1/12)), float(control.CEILING-control.BLACK)
    dx = torch.tensor([[0,0,0],[1,2,-3],[9,-2,4],[.01,.02,.03],[-20,3,8]], dtype=torch.float32)
    dy = torch.tensor([[0,0,0],[2,4,-6],[-1,5,7],[-.02,.005,.04],[11,13,-6]], dtype=torch.float32)
    actual = author.edge_matrix_loss(dx, dy)
    expected = literal_edges(dx.numpy(), dy.numpy())
    assert tuple(actual.shape) == (5,) and np.allclose(actual.detach().numpy(), expected, rtol=2e-6, atol=1e-7)
    rotation = torch.tensor([[.6,-.8,0],[.8,.6,0],[0,0,1]], dtype=torch.float32)
    rotated = author.edge_matrix_loss(dx@rotation.T, dy@rotation.T)
    assert torch.allclose(actual, rotated, rtol=2e-6, atol=1e-7)
    u, colour = torch.tensor([1.,2.,2.])/3, torch.tensor([-2.,1.,0.])/np.sqrt(5)
    spatial, perpendicular = [.6,.8], [-.8,.6]
    responses = []
    for name, direction, value in [('orthogonal-weak', perpendicular, 0.), ('same-spatial-weak', spatial, 0.), ('true-rank2-strong', perpendicular, 8.)]:
        t = torch.tensor(value, requires_grad=True)
        x = 16*u*spatial[0]+t*colour*direction[0]
        y = 16*u*spatial[1]+t*colour*direction[1]
        loss = author.edge_matrix_loss(x, y)
        gradient = torch.autograd.grad(loss, t, create_graph=True)[0]
        curvature = float(torch.autograd.grad(gradient, t)[0])
        if name == 'orthogonal-weak':
            expected_curvature = .5
        elif name == 'same-spatial-weak':
            expected_curvature = .5/65
        else:
            expected_curvature = .5*(1-value*value/4)/(1+value*value/4)**2
            assert abs(float(gradient.detach())-value/(2*(1+value*value/4))) < 2e-5 and curvature < 0
        assert abs(curvature-expected_curvature) < 2e-5
        responses.append(dict(name=name, weak_amplitude=value, derivative=float(gradient.detach()), curvature=curvature, expected_curvature=expected_curvature))
    assert responses[1]['curvature'] < .02*responses[0]['curvature']  # Live rank1 counterexample, not universal colour protection.
    hx, hy = .2*dx+.1*dy, .3*dy-.05*dx
    t = torch.tensor(0., requires_grad=True)
    derivative = float(torch.autograd.grad(author.edge_matrix_loss(dx+t*hx, dy+t*hy).mean(), t)[0])
    step = .001
    fd = float((literal_edges(dx.numpy().astype(np.float64)+step*hx.numpy(), dy.numpy().astype(np.float64)+step*hy.numpy()).mean()-literal_edges(dx.numpy().astype(np.float64)-step*hx.numpy(), dy.numpy().astype(np.float64)-step*hy.numpy()).mean())/(2*step))
    assert abs(derivative) > .001 and abs(derivative-fd) <= 1e-5+.002*abs(derivative)
    y, x = np.mgrid[:7, :11].astype(np.float32)
    pattern = torch.from_numpy(np.stack([x+2*y,3*x-y,2*x+4*y], -1))
    amplitude = torch.tensor(0., requires_grad=True)
    flat = 2048+amplitude*pattern
    loss = author.image_matrix_cauchy_dn(flat, gain, readvar)
    grad = torch.autograd.grad(loss, amplitude, create_graph=True, retain_graph=True)[0]
    curvature = float(torch.autograd.grad(grad, amplitude, retain_graph=True)[0])
    old = author.model._vector_huber(flat, scale)
    old_grad = torch.autograd.grad(old, amplitude, create_graph=True)[0]
    old_curvature = float(torch.autograd.grad(old_grad, amplitude)[0])
    expected_curvature = 17.5/scale**2
    assert float(loss.detach()) == 0 and float(grad.detach()) == 0
    assert abs(curvature-expected_curvature) <= 2e-6*expected_curvature
    assert abs(curvature-old_curvature) <= 2e-6*expected_curvature
    image = 800+15*pattern
    image_expected = literal_image(image.numpy(), scale)
    assert abs(float(author.image_matrix_cauchy_dn(image, gain, readvar))-image_expected) < 5e-6*max(1,image_expected)
    alpha, far = torch.from_numpy(.2+.01*x+.02*y), 1.5*image.flip(0)+333
    state = SimpleNamespace(fields=lambda: (image/dn_scale,far/dn_scale,alpha), far=True, dn_scale=dn_scale)
    both = (image_expected+literal_image(far.numpy(), scale))/2
    a = alpha.numpy().astype(np.float64)
    flux = (np.mean((image.numpy().astype(np.float64)/dn_scale)**2)+np.mean((far.numpy().astype(np.float64)/dn_scale)**2))/2
    extra = .02*(np.abs(np.diff(a,axis=0)).mean()+np.abs(np.diff(a,axis=1)).mean())/2+.002*np.mean(a*(1-a))+.0001*flux
    assert abs(float(author.matrix_image_prior(state,config))-both) < 5e-6*max(1,both)
    assert abs(float(author.selected_prior(state,config))-(both+extra)) < 5e-6*max(1,both+extra)
    return dict(status='PASS', passed=True, edge_eigen_oracle=expected.tolist(), responses=responses,
        arbitrary_autograd=derivative, independent_finite_difference=fd,
        rectangular_curvature=curvature, original_rectangular_curvature=old_curvature, expected_rectangular_curvature=expected_curvature,
        rgb_rotation_invariant=True, expected_risk='Only a new colour AND spatial singular direction retains .5 curvature. Same-spatial rank1 perturbations remain weak; strong rank2 is still nonconvex.')


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
        complete = verify(r, current, old, 'matrix-cauchy-original-scale-sheets')
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
    return dict(status='MATRIX_CAUCHY_PRIOR_SCORED', cases=rows, all_fixed_checks_pass=all(r.get('fixed_checks_pass', False) for r in rows),
        all_stationary=all(r.get('stationary', False) for r in rows), original_screens_remain_failed=True, real_photo_admission=False,
        physical_adequacy=read(source / 'layered' / 'physical-adequacy.json'), source_immutable=True, outputs_immutable=True,
        next_scope='A pass is only this fixed known-alpha discrete-optics screen, not photographs',
        cauchy_prior_descriptive_sha256=sha(HERE / 'cauchy-1' / 'scored' / 'result.json'),
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
    print('MATRIX_CAUCHY_PRIOR_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
