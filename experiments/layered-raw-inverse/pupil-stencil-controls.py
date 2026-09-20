"""Independent fixed pupil-stencil mechanics and quadrature checks; never fits."""
from pathlib import Path
from dataclasses import replace
import argparse
import importlib.util
import sys
import time
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pupil_control_helpers', HERE/'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read, load = common.sha, common.read, common.load
STAGES = {'setup': 60., 'mechanics': 60., 'density': 120.}
FOCI = [0, 2, 4, 6, 8]


def translate(image, dx, dy):
    """Literal zero extension: output[y,x]=input[y+dy,x+dx]."""
    h, w = image.shape[:2]
    out = np.zeros_like(image)
    x0, x1, y0, y1 = max(0, -dx), min(w, w-dx), max(0, -dy), min(h, h-dy)
    if x0 < x1 and y0 < y1:
        out[y0:y1, x0:x1] = image[y0+dy:y1+dy, x0+dx:x1+dx]
    return out


def sample(image, dx, dy):
    # Scalar coordinates/setup use f64; image products and sums remain f32.
    ix, iy = int(np.floor(dx)), int(np.floor(dy))
    fx, fy = np.float32(dx-ix), np.float32(dy-iy)
    out = np.zeros_like(image)
    for oy, wy in [(0, np.float32(1)-fy), (1, fy)]:
        for ox, wx in [(0, np.float32(1)-fx), (1, fx)]:
            out += np.float32(wx*wy)*translate(image, ix+ox, iy+oy)
    return out


def direct(near, far, alpha, pupil, sn, sf, wrong=False):
    premult = alpha[..., None]*near
    out, nm, fm = np.zeros_like(near), np.zeros_like(near), np.zeros_like(far)
    am = np.zeros_like(alpha)
    for ux, uy in pupil.astype(np.float64):
        a, n = sample(alpha, sn*ux, sn*uy), sample(premult, sn*ux, sn*uy)
        b = sample(far, sf*ux, sf*uy)
        if wrong:
            nm += n
            am += a
            fm += b
        else:
            out += n+(np.float32(1)-a[..., None])*b
    weight = np.float32(1/len(pupil))
    return nm*weight+(1-am[..., None]*weight)*(fm*weight) if wrong else out*weight


def tensors(values, gradients=False):
    return [torch.tensor(np.ascontiguousarray(v), device='cuda', dtype=torch.float32, requires_grad=gradients) for v in values]


def check_table(table):
    offsets, weights = np.asarray(table.offsets), np.asarray(table.weights)
    near, marginal = np.asarray(table.near_offsets), np.asarray(table.near_weights)
    assert offsets.dtype == np.int32 and offsets.ndim == 2 and offsets.shape[1] == 4
    assert weights.dtype == np.float32 and weights.shape == (len(offsets),) and np.isfinite(weights).all() and (weights > 0).all()
    assert near.dtype == np.int32 and near.shape == (len(marginal), 2) and marginal.dtype == np.float32
    assert len({tuple(p) for p in offsets}) == len(offsets)
    assert abs(float(weights.sum(dtype=np.float64))-1) < 2e-6
    sums = {}
    for p, weight in zip(offsets, weights):
        key = tuple(p[:2])
        sums[key] = sums.get(key, 0.)+float(weight)
    assert set(sums) == {tuple(p) for p in near}
    assert max(abs(sums[tuple(p)]-float(v)) for p, v in zip(near, marginal)) < 2e-6
    return dict(entries=len(weights), marginal_entries=len(marginal), table_bytes=int(offsets.nbytes+weights.nbytes+near.nbytes+marginal.nbytes))


def boundary(author):
    near, far = np.zeros((5, 7, 3), np.float32), np.full((5, 7, 3), 500, np.float32)
    alpha = np.ones((5, 7), np.float32)
    table = author.build_table(np.array([[1., 0.]], np.float32), -1., 0.)
    n, f, a = tensors([near, far, alpha], True)
    out = author.joint_pupil(n, f, a, table)
    expected = np.zeros_like(far)
    expected[:, 0] = 500
    assert np.array_equal(out.detach().cpu().numpy(), expected)
    out[:, 0].sum().backward()
    wanted = np.zeros_like(far)
    wanted[:, 0] = 1
    assert np.array_equal(f.grad.cpu().numpy(), wanted)
    assert torch.count_nonzero(n.grad) == 0 and torch.count_nonzero(a.grad) == 0
    return dict(outside_near_transmission_one=True, far_adjoint_exact=True, wrong_discard_far_max_error_dn=500.)


def refusals(author):
    table = author.build_table(np.array([[0, 0]], np.float32), 0., 0.)
    n, f, a = tensors([np.ones((3, 3, 3), np.float32), np.ones((3, 3, 3), np.float32), np.full((3, 3), .4, np.float32)], True)
    bad = n.detach().clone()
    bad[0, 0, 0] = float('nan')
    cases = {'cpu_input': lambda: author.joint_pupil(n.cpu(), f, a, table),
             'wrong_dtype': lambda: author.joint_pupil(n.double(), f, a, table),
             'noncontiguous': lambda: author.joint_pupil(n.transpose(0, 1), f, a, table),
             'nonfinite': lambda: author.joint_pupil(bad, f, a, table),
             'invalid_alpha': lambda: author.joint_pupil(n, f, a+1, table),
             'invalid_pupil': lambda: author.build_table(np.array([[2., 0.]], np.float32), 0., 0.)}
    records = {}
    for name, action in cases.items():
        try:
            action()
        except (ValueError, TypeError, RuntimeError) as exc:
            records[name] = type(exc).__name__
        else:
            raise AssertionError('missing refusal: '+name)
    derivative = torch.autograd.grad(author.joint_pupil(n, f, a, table).sum(), n, create_graph=True)[0]
    try:
        torch.autograd.grad(derivative.sum(), a)
    except RuntimeError as exc:
        records['double_backward'] = type(exc).__name__
    else:
        raise AssertionError('higher-order differentiation silently accepted')
    return records


def mechanics(author, control, config):
    config = replace(config, width=48, height=44)
    y, x = np.mgrid[:44, :48].astype(np.float32)
    near = np.stack((100+2*x, 130+y, 160+.7*x), -1).astype(np.float32)
    spot = np.exp(-np.float32(.5)*(((x-25)/4)**2+((y-23)/3)**2))
    far = np.stack((220+800*spot, 260+600*spot, 190+500*spot), -1).astype(np.float32)
    alpha = (.2+.55*np.exp(-np.float32(.5)*((x-23)/2.2)**2)).astype(np.float32)
    constant = np.full_like(near, 123)
    impulse = np.zeros_like(near)
    impulse[22, 24] = [100, 200, 300]
    fixtures = [('constant', constant, constant, np.full_like(alpha, .35)),
                ('impulse', impulse, np.zeros_like(far), np.ones_like(alpha)),
                ('alpha0', near, far, np.zeros_like(alpha)), ('alpha1', near, far, np.ones_like(alpha)),
                ('crossing', near, far, alpha)]
    pupil = control.pupil_pairs(64)
    records = []
    for label, nv, fv, av in fixtures:
        snapshot = [control.digest(v) for v in [nv, fv, av]]
        for index in [0, 4, 8]:
            sn = config.defocus_scale*(config.focus_coordinates[index]-config.inverse_depths[0])
            sf = config.defocus_scale*(config.focus_coordinates[index]-config.inverse_depths[1])
            table = author.build_table(pupil, sn, sf)
            geometry = check_table(table)
            n, f, a = tensors([nv, fv, av], True)
            actual_joint = author.joint_pupil(n, f, a, table)
            oracle = direct(nv, fv, av, pupil, sn, sf)
            joint_error = float(np.max(np.abs(actual_joint.detach().cpu().numpy()-oracle)))
            assert joint_error <= .1, (label, index, joint_error)
            actual = author.forward(n, f, a, config, index, pupil=pupil, table=table)
            old_inputs = tensors([nv, fv, av], True)
            reference = author.model.forward(*old_inputs, config, index, pupil=torch.tensor(pupil, device='cuda'))
            forward_error = float((actual-reference).abs().max().detach())
            assert forward_error <= .1, (label, index, forward_error)
            gradients = None
            if label == 'crossing':
                cot = np.ascontiguousarray(np.stack((.5+.2*np.sin(x/3), .7+.2*np.cos(y/4), .6+.1*np.sin((x+y)/7)), -1)/np.float32(x.size*3))
                incoming = torch.tensor(cot, device='cuda')
                ga = torch.autograd.grad((actual*incoming).sum(), (n, f, a))
                gb = torch.autograd.grad((reference*incoming).sum(), tuple(old_inputs))
                gradients = []
                for name, u, v in zip(['near', 'far', 'alpha'], ga, gb):
                    error, maximum = float((u-v).abs().max()), float(v.abs().max())
                    relative = float(torch.linalg.vector_norm(u-v)/torch.linalg.vector_norm(v))
                    assert maximum > 0 and error <= 1e-5+3e-4*maximum and relative <= 3e-4, (name, error, relative)
                    gradients.append(dict(parameter=name, max_error=error, relative_l2=relative))
            assert snapshot == [control.digest(v) for v in [nv, fv, av]]
            assert all(np.array_equal(v.detach().cpu().numpy(), w) for v, w in zip([n, f, a], [nv, fv, av]))
            records.append(dict(fixture=label, index=index, pre_psf_max_dn=joint_error, full_forward_max_dn=forward_error, gradients=gradients, table=geometry))
    table = author.build_table(pupil, -6., 6.)
    n, f, a = tensors([near, far, alpha], True)
    output = author.joint_pupil(n, f, a, table)
    gradients = torch.autograd.grad(output.mean(), (n, f, a))
    directions = [np.broadcast_to(np.array([1, .5, .25], np.float32), near.shape).copy(),
                  np.broadcast_to(np.array([1, .25, .5], np.float32), far.shape).copy(), np.ones_like(alpha)]
    finite = []
    for k, (name, step) in enumerate([('near', .25), ('far', .25), ('alpha', .001)]):
        plus, minus = [v.copy() for v in [near, far, alpha]], [v.copy() for v in [near, far, alpha]]
        plus[k] += np.float32(step)*directions[k]
        minus[k] -= np.float32(step)*directions[k]
        fd = float((direct(*plus, pupil, -6., 6.).mean(dtype=np.float64)-direct(*minus, pupil, -6., 6.).mean(dtype=np.float64))/(2*step))
        ad = float(np.sum(gradients[k].detach().cpu().numpy().astype(np.float64)*directions[k]))
        tolerance = 2e-4+.005*abs(ad)
        assert abs(ad) > .05 and abs(ad-fd) <= tolerance and abs(2*ad-fd) > tolerance
        finite.append(dict(parameter=name, adjoint=ad, independent_finite_difference=fd, tolerance=tolerance, doubled_gradient_rejected=True))
    proper, wrong = direct(near, far, alpha, pupil, -6., 6.), direct(near, far, alpha, pupil, -6., 6., wrong=True)
    coupling_difference = float(np.max(np.abs(proper[12:-12, 12:-12]-wrong[12:-12, 12:-12])))
    assert coupling_difference > 1, 'outer-product independence destroyer is inactive'
    stream = torch.cuda.Stream()
    assert stream.cuda_stream != torch.cuda.default_stream().cuda_stream
    # All producers and consumers use this stream; do not omit a caller dependency.
    with torch.cuda.stream(stream):
        alternate_stream = boundary(author)
    stream.synchronize()
    return dict(records=records, finite_differences=finite, boundary=boundary(author),
                nondefault_stream_boundary=alternate_stream, refusals=refusals(author),
                incorrect_outer_product_max_supported_dn=coupling_difference, source_immutable=True)


def polar(nr, nt, phase):
    # Independent deterministic equal-area setup in f64, then fixed f32 sites.
    radius = np.sqrt((np.arange(nr, dtype=np.float64)+.5)/nr)
    theta = 2*np.pi*(np.arange(nt, dtype=np.float64)+.5)/nt+phase
    return np.stack((radius[:, None]*np.cos(theta), radius[:, None]*np.sin(theta)), -1).reshape(-1, 2).astype(np.float32)


def reference_chunks(model, fields, config, index, pupil):
    out = torch.zeros_like(fields[0])
    with torch.no_grad():
        for start in range(0, len(pupil), 1024):
            rays = torch.tensor(np.ascontiguousarray(pupil[start:start+1024]), device='cuda')
            rgb = model.forward(*fields, config, index, pupil=rays)
            out += rgb*np.float32(len(rays)/len(pupil))
            del rgb, rays
    return out.cpu().numpy().copy()


def discrepancy(control, image, reference):
    a, b = control.cfa_numpy(image), control.cfa_numpy(reference)
    sigma = np.sqrt(control.GAIN*np.maximum(b, np.float32(0))+control.READ_VARIANCE+np.float32(1/12))
    delta = (a-b)/sigma
    records = {region: float(np.sqrt(np.mean(delta[control.region_slice(region)].astype(np.float64)**2))) for region in ['whole', 'crossing']}
    return dict(normalized_rms=records, passed=all(v <= .75 for v in records.values()))


def density(author, control, config):
    latent = control.scene('layered')
    originals = [latent[k] for k in ['near', 'far', 'alpha']]
    before = [control.digest(v) for v in originals]
    fields = tensors(originals)
    pupils = {'original64': control.pupil_pairs(64), 'golden1024': control.pupil_pairs(1024),
              'polar1024': polar(32, 32, .23), 'polar4096': polar(64, 64, .23),
              'fixed16384': polar(128, 128, .23), 'rotated16384': polar(128, 128, .60)}
    records = []
    for index in FOCI:
        sn = config.defocus_scale*(config.focus_coordinates[index]-config.inverse_depths[0])
        sf = config.defocus_scale*(config.focus_coordinates[index]-config.inverse_depths[1])
        started = time.monotonic()
        table = author.build_table(pupils['fixed16384'], sn, sf)
        geometry = check_table(table)
        with torch.no_grad():
            candidate = author.forward(*fields, config, index, pupil=pupils['fixed16384'], table=table).cpu().numpy().copy()
        reference = reference_chunks(author.model, fields, config, index, pupils['fixed16384'])
        mechanical_error = float(np.max(np.abs(candidate-reference)))
        assert mechanical_error <= .1, (index, mechanical_error)
        comparisons = {}
        for name in ['original64', 'golden1024', 'polar1024', 'polar4096', 'rotated16384']:
            independent = reference_chunks(author.model, fields, config, index, pupils[name])
            comparisons[name] = discrepancy(control, candidate, independent)
        records.append(dict(index=index, fixed_candidate_rays=16384, table=geometry,
            same_pupil_full_max_dn=mechanical_error, comparisons=comparisons, seconds=time.monotonic()-started))
        print('PUPIL_DENSITY', index, records[-1]['seconds'], flush=True)
    assert before == [control.digest(v) for v in originals]
    assert all(np.array_equal(t.cpu().numpy(), a) for t, a in zip(fields, originals))
    adequate = all(r['comparisons'][label]['passed'] for r in records for label in ['polar4096', 'rotated16384'])
    return dict(fixed16384_convergence_proxy_pass=adequate, records=records,
        pupils={name: dict(count=len(p), sha256=control.digest(p)) for name, p in pupils.items()},
        candidate_selected_before_data=True, original64_and1024_are_diagnostics_not_vetoes=True,
        reference_scope='Chunked original operator; finite-density convergence proxy, not continuum or calibrated optics truth')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    source = HERE/'screen-1'/'output'
    control = common.frozen(source)
    author = load(HERE/'pupil-stencil.py', 'pupil_stencil_author_controls')
    config = author.model.Config(**read(source/'layered'/'two-layer'/'receipt.json')['config'])
    bindings = {str(p): sha(p) for p in [HERE/'model.py', HERE/'pupil-stencil.py', Path(__file__), HERE/'independent-controls.py']}
    result = dict(status='STARTED', stages={}, bindings=bindings, no_fit_performed=True, real_photo_admission=False)
    torch.cuda.reset_peak_memory_stats()
    phase = 'setup'
    try:
        started = time.monotonic()
        print('PUPIL_STAGE setup', flush=True)
        table = author.build_table(np.array([[0, 0]], np.float32), 0., 0.)
        inputs = tensors([np.ones((3, 3, 3), np.float32), np.ones((3, 3, 3), np.float32), np.full((3, 3), .5, np.float32)], True)
        author.joint_pupil(*inputs, table).sum().backward()
        torch.cuda.synchronize()
        result['runtime'] = author.runtime_metadata()
        result['stages']['setup'] = time.monotonic()-started
        assert result['stages']['setup'] <= STAGES['setup']
        started = time.monotonic()
        phase = 'mechanics'
        print('PUPIL_STAGE mechanics', flush=True)
        result['mechanics'] = mechanics(author, control, config)
        result['stages']['mechanics'] = time.monotonic()-started
        assert result['stages']['mechanics'] <= STAGES['mechanics']
        control.save(out/'mechanics.json', control.jsonable(result))
        started = time.monotonic()
        phase = 'density'
        print('PUPIL_STAGE density', flush=True)
        result['density'] = density(author, control, config)
        result['stages']['density'] = time.monotonic()-started
        assert result['stages']['density'] <= STAGES['density']
        result['status'] = 'PUPIL_STENCIL_CHECKED'
        result['passed'] = result['density']['fixed16384_convergence_proxy_pass']
    except Exception as exc:
        result.update(status='REFUSED', passed=False, failure_stage=phase, failure_type=type(exc).__name__, failure=str(exc))
        raise
    finally:
        result['cuda_peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        result['cuda_peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        if result['cuda_peak_allocated_bytes'] > 8*1024**3:
            result.update(status='RESOURCE_REFUSED', passed=False)
        result['source_unchanged'] = all(sha(p) == digest for p, digest in bindings.items())
        if not result['source_unchanged']:
            result.update(status='SOURCE_CHANGED', passed=False)
        control.save(out/'result.json', control.jsonable(result))
        print('PUPIL_STENCIL_CONTROLS', result['status'], flush=True)


if __name__ == '__main__':
    main()
