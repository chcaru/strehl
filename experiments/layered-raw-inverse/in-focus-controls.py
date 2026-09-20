"""Independent fixed-output commissioning/scoring; never fits or selects sources."""
from pathlib import Path
import argparse
import importlib.util
import sys
import numpy as np
from scipy import ndimage
import torch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('in_focus_helpers', HERE/'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read = common.sha, common.read
AUTHOR_SHA = '3e75c94dbf0c2f4665f25161751ec28c6ef162ebdd06c5f4f4681b4a1f0fc013'
ARMS = {'visibility': 'visibility-1', 'shot': 'shot-prior-1', 'cauchy': 'cauchy-1', 'matrix': 'matrix-cauchy-1'}
COMPONENTS = [('glint', 'core'), ('ridge', 'ridge-detail')]


def kernel():
    x = np.arange(-3, 4, dtype=np.float32)
    k = np.exp(np.float32(-.5)*(x/np.float32(.7))**2)
    return k/np.sum(k, dtype=np.float32)


def optical(image):
    """Independent SciPy separable y-then-x, full context, explicit zero padding."""
    assert image.dtype == np.float32 and image.ndim == 3 and image.shape[2] == 3 and np.isfinite(image).all()
    k = kernel()
    return ndimage.convolve1d(ndimage.convolve1d(image, k, axis=0, mode='constant', cval=0., output=np.float32),
                              k, axis=1, mode='constant', cval=0., output=np.float32)


def tolerance(image):
    # Two seven-tap reductions, kernel normalization and reversed pass order.
    # This is a prospective arithmetic bound, not a quality tolerance.
    return 32*np.finfo(np.float32).eps*max(1., float(np.max(np.abs(image))))


def transformed_components(latent):
    return {name: (optical(latent[name+'_template']), optical(latent['truth']-latent[name+'_template']))
            for name, _ in COMPONENTS}


def generator_psf_checks(control, latent):
    fields = {'truth': latent['truth']}
    for name, _ in COMPONENTS:
        fields[name+'_template'] = latent[name+'_template']
        fields[name+'_absent'] = latent['truth']-latent[name+'_template']
    checks = {}
    for name, field in fields.items():
        # Both filters receive the entire96 image. Frozen generator uses nearest
        # padding; its difference from zeros cannot reach this original support.
        a, b = optical(field), control.psf(field)
        error = float(np.max(np.abs(a[16:80, 16:80]-b[16:80, 16:80])))
        assert error <= tolerance(field)
        checks[name] = dict(max_abs_supported_dn=error, bound_dn=tolerance(field))
    return checks


def component(control, image, components, name, region):
    template, absent = components[name]
    sl = control.region_slice(region)
    t = template[sl].astype(np.float64)
    value = image[sl].astype(np.float64)-absent[sl].astype(np.float64)
    denominator = np.sum(t*t, axis=(0, 1))
    live = denominator > 100
    recovery = np.divide(np.sum(value*t, axis=(0, 1)), denominator, out=np.zeros(3), where=live)
    return dict(recovery=recovery.tolist(), template_energy=denominator.tolist(), live=bool(live.all()))


def component_guard(candidate, reference):
    a, b = np.array(candidate['recovery']), np.array(reference['recovery'])
    return bool(candidate['live'] and reference['live'] and np.all(b >= .5)
                and np.all(np.clip(a, 0, 1) >= .98*np.minimum(b, 1)))


def commission(control, source):
    assert sha(HERE/'in-focus-consumer.py') == AUTHOR_SHA
    author = common.load(HERE/'in-focus-consumer.py', 'in_focus_author')
    y, x = np.mgrid[:96, :96].astype(np.float32)
    constant = np.broadcast_to(np.array([2500, 3200, 2000], np.float32), (96, 96, 3)).copy()
    impulse = np.zeros_like(constant)
    impulse[48, 48] = [1000, 2000, 3000]
    signed = np.stack([100*np.sin(x/3), 80*np.cos(y/4), 30*np.sin((x+y)/5)], -1).astype(np.float32)
    operator = {}
    for name, image in [('constant', constant), ('impulse', impulse), ('signed', signed)]:
        before = control.digest(image)
        actual, expected = author.apply_in_focus(image), optical(image)
        error = float(np.max(np.abs(actual-expected)))
        assert error <= tolerance(image), (name, error, tolerance(image))
        assert before == control.digest(image)
        operator[name] = dict(max_abs_dn=error, bound_dn=tolerance(image))
    assert np.max(np.abs(optical(constant)[16:80, 16:80]-constant[16:80, 16:80])) <= tolerance(constant)
    assert np.max(np.abs(optical(impulse).sum((0, 1), dtype=np.float64)-[1000, 2000, 3000])) < .01
    apron = np.zeros_like(constant)
    apron[35, 15] = 1000
    correct, cropped = optical(apron)[16:80, 16:80], optical(apron[16:80, 16:80].copy())
    context_difference = float(np.max(np.abs(correct-cropped)))
    assert context_difference > 1, 'cropped filtering destroyer not exercised'
    alpha = ((x.astype(np.int32)+y.astype(np.int32)) % 2).astype(np.float32)[..., None]
    near = (2000+1000*alpha)*np.array([1, .5, .3], np.float32)
    far = np.broadcast_to(np.array([300, 400, 600], np.float32), near.shape).copy()
    composed = optical(alpha*near+(1-alpha)*far)
    blurred_alpha = optical(np.repeat(alpha, 3, axis=2))
    wrong = blurred_alpha*optical(near)+(1-blurred_alpha)*optical(far)
    noncommutation = float(np.max(np.abs(composed[16:80, 16:80]-wrong[16:80, 16:80])))
    assert noncommutation > 100, 'filter-sheets-before-composition destroyer inactive'
    cfg = author.model.Config(**read(source/'layered'/'two-layer'/'receipt.json')['config'])
    image = np.ascontiguousarray(constant+signed)
    with torch.no_grad():
        t = torch.as_tensor(image, device=cfg.device)
        focused = author.model.forward(t, t, torch.ones((96, 96), device=cfg.device), cfg, 0,
                                      single_depth=cfg.inverse_depths[1]).cpu().numpy()
    focused_error = float(np.max(np.abs(focused[16:80, 16:80]-optical(image)[16:80, 16:80])))
    assert focused_error <= tolerance(image)
    latent = control.scene('layered')
    generator_checks = generator_psf_checks(control, latent)
    target, components = optical(latent['truth']), transformed_components(latent)
    destroyers = {}
    for name, region in COMPONENTS:
        ideal = component(control, target, components, name, region)
        assert ideal['live'] and np.max(np.abs(np.array(ideal['recovery'])-1)) < 1e-5
        halves = []
        for channel in range(3):
            half = target.copy()
            half[..., channel] -= np.float32(.5)*components[name][0][..., channel]
            measured = component(control, half, components, name, region)
            assert abs(measured['recovery'][channel]-.5) < 1e-5
            assert not component_guard(measured, ideal)
            halves.append(dict(channel=channel, component=measured, rgb=control.score(half, target, region)))
        twice = optical(target)
        double_component = component(control, twice, components, name, region)
        destroyers[name] = dict(ideal=ideal, half_colour=halves, double_psf=double_component,
            double_psf_rejected=not component_guard(double_component, ideal),
            double_psf_errors=control.score(twice, target, region))
    # Both commissioned components must detect the fixed extra blur. No sigma/bar search.
    double_rejected = all(v['double_psf_rejected'] for v in destroyers.values())
    wrong_colour = optical(latent['truth'][..., [2, 1, 0]].copy())
    colour_error = control.score(wrong_colour, target, 'ridge')
    colour_component = component(control, wrong_colour, components, 'ridge', 'ridge-detail')
    colour_rejected = not component_guard(colour_component, destroyers['ridge']['ideal'])
    assert colour_error['chroma_rmse'] > 100 and colour_rejected
    return dict(status='PASS' if double_rejected else 'INADEQUATE_DETAIL_INSTRUMENT', passed=double_rejected,
        operator=operator, focused_one_layer_max_abs_dn=focused_error, context_destroyer_dn=context_difference,
        compose_before_filter_destroyer_dn=noncommutation, components=destroyers,
        wrong_colour=dict(errors=colour_error, component=colour_component, rejected=colour_rejected),
        frozen_generator_psf_checks=generator_checks,
        destroyer_reference='Ideal once-PSF target, per-colour recovery1; actual arms use filtered visibility',
        scope='Fixed supplied synthetic optical PSF; original pinhole failures unchanged')


def quality(control, case, images, arm, components):
    target, candidate = images['truth'], images[arm]
    regions = ['whole'] if case == 'flat' else list(control.REGIONS)
    values = {r: {k: control.score(v, target, r) for k, v in images.items() if k != 'truth'} for r in regions}
    bars, detail = {}, {}
    if case == 'flat':
        for key in ['rgb_rmse', 'chroma_rmse']:
            bars[key+'_mean'] = values['whole'][arm][key] <= 1.05*values['whole']['mean-observed'][key]
            bars[key+'_visibility'] = values['whole'][arm][key] <= 1.05*values['whole']['visibility'][key]
    else:
        for r in ['whole', 'core', 'ridge']:
            bars[r+'_mean_gain'] = values[r]['mean-observed']['rgb_rmse'] > 1 and values[r][arm]['rgb_rmse'] <= .90*values[r]['mean-observed']['rgb_rmse']
        for r in ['whole', 'crossing', 'core', 'ridge']:
            bars[r+'_far_only'] = values[r][arm]['rgb_rmse'] <= (.95 if r in ['whole', 'crossing'] else 1.05)*values[r]['far-only']['rgb_rmse']
        for r in ['core', 'ridge']:
            for key in ['rgb_rmse', 'chroma_rmse']:
                bars[r+'_'+key+'_visibility'] = values[r][arm][key] <= 1.02*values[r]['visibility'][key]
        for name, region in COMPONENTS:
            a, v, o = [component(control, images[k], components, name, region) for k in [arm, 'visibility', 'donor-observed']]
            bars[name+'_visibility'] = component_guard(a, v)
            bars[name+'_absolute_donor'] = bool(a['live'] and o['live'] and np.all(np.clip(a['recovery'], 0, 1) >= .8)
                and np.all(np.clip(a['recovery'], 0, 1) >= .98*np.clip(o['recovery'], 0, 1)))
            detail[name] = dict(candidate=a, visibility=v, retained_donor=o)
    return dict(regions=values, components=detail, bars=bars, passed=bool(all(bars.values())))


def score(control, source, candidate):
    manifest = read(candidate/'result.json')
    assert manifest['status'] == 'IN_FOCUS_CONSUMER_COMPLETE' and manifest['sources_unchanged']
    assert manifest['source_bindings_before'] == manifest['source_bindings_after']
    assert manifest['full_native_shape'] == [96, 96, 3] and manifest['scoring_support_native_xywh'] == [16, 16, 64, 64]
    assert manifest['original_pinhole_admission_unchanged'] and not manifest['real_photo_admission']
    psf = manifest['psf']
    assert psf['supplied_f32_sigma'] == float(np.float32(.7)) and psf['radius'] == 3
    supplied = np.array(psf['kernel_1d_f32'], np.float32)
    assert supplied.shape == (7,) and control.digest(supplied) == psf['kernel_sha256']
    assert np.max(np.abs(supplied-kernel())) <= 4*np.finfo(np.float32).eps
    expected, images, checks = {}, {}, []
    for case in ['flat', 'layered']:
        expected[(case, 'truth')] = source/case/'truth-rgb-f32.npy'
        for arm, root in ARMS.items():
            expected[(case, arm)] = HERE/root/'output'/case/'fixed-alpha'/'reconstruction.npz'
        expected[(case, 'far-only')] = source/case/'far-only'/'reconstruction.npz'
        for arm, filename in [('mean-observed', 'mean-rgb-f32.npy'), ('donor-observed', 'oracle-bound-rgb-f32.npy')]:
            expected[(case, arm)] = source/case/filename
    assert len(manifest['artifacts']) == 16 and {(a['case'], a['arm']) for a in manifest['artifacts']} == set(expected)
    files = set(manifest['source_bindings_before']) | {str(candidate/'result.json')}
    files |= {a['path'] for a in manifest['artifacts']}
    legacy = {arm: HERE/root/'scored'/'result.json' for arm, root in ARMS.items()}
    files |= {str(p) for p in legacy.values()}
    before = {p: sha(p) for p in sorted(files)}
    for p, digest in manifest['source_bindings_before'].items():
        assert before[p] == digest
    for row in manifest['artifacts']:
        case, arm = row['case'], row['arm']
        src, dst = expected[(case, arm)], candidate/case/f'{arm}-rgb-f32.npy'
        assert Path(row['source_path']).resolve() == src.resolve() and Path(row['path']).resolve() == dst
        assert sha(src) == row['source_sha256'] and sha(dst) == row['sha256']
        if src.suffix == '.npz':
            with np.load(src, allow_pickle=False) as data:
                original = data['pinhole_rgb'].copy()
            assert sha(src.parent/'receipt.json') == row['source_receipt_sha256']
        else:
            original = np.load(src, allow_pickle=False)
        delivered = np.load(dst, allow_pickle=False)
        assert row['shape'] == [96, 96, 3] and row['dtype'] == 'float32'
        assert all(v.dtype == np.float32 and v.shape == (96, 96, 3) and np.isfinite(v).all() for v in [original, delivered])
        assert control.digest(original) == row['source_array_sha256'] and control.digest(delivered) == row['array_sha256']
        observed = arm in ['mean-observed', 'donor-observed']
        assert row['psf_applications'] == (0 if observed else 1)
        assert row['source_kind'] == ('already-observed-developed' if observed else 'latent-pinhole')
        err = 0. if observed else float(np.max(np.abs(delivered-optical(original))))
        if observed:
            assert sha(src) == sha(dst) and np.array_equal(original, delivered)
        else:
            assert err <= tolerance(original), (case, arm, err)
        images.setdefault(case, {})[arm] = delivered
        checks.append(dict(case=case, arm=arm, max_abs_operator_error_dn=err, bound_dn=tolerance(original)))
    records, generator_checks = [], {}
    for case in ['flat', 'layered']:
        latent = control.scene(case)
        assert np.array_equal(latent['truth'], np.load(source/case/'truth-rgb-f32.npy', allow_pickle=False))
        generator_checks[case] = generator_psf_checks(control, latent)
        components = transformed_components(latent)
        for arm in ARMS:
            q = quality(control, case, images[case], arm, components)
            prior = next(r for r in read(legacy[arm])['cases'] if r['name'] == case)
            held_pass = all(h['scores']['passed'] for h in prior['heldout'])
            records.append(dict(case=case, arm=arm, quality=q, fixed_target_checks_pass=q['passed'],
                retained_heldout_pass=held_pass, retained_heldout=prior['heldout'],
                retained_pinhole_checks_pass=prior['fixed_checks_pass'], retained_status=prior['status'],
                combined_saved_state_checks_pass=bool(q['passed'] and held_pass),
                retained_scored_result_sha256=sha(legacy[arm])))
    assert {p: sha(p) for p in sorted(files)} == before
    return dict(status='IN_FOCUS_TARGET_SCORED', records=records, operator_checks=checks,
        frozen_generator_psf_checks=generator_checks,
        sources_and_outputs_immutable=True, bindings=before, original_pinhole_admission_unchanged=True,
        real_photo_admission=False, target='One supplied sigma0.7 PSF on composed pinhole; different output question',
        observed_baseline_scope='Mean and original training-only donor unchanged; donor not reselected for this target',
        physical_adequacy_unchanged=read(source/'layered'/'physical-adequacy.json'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['commission', 'score'])
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = HERE/'screen-1'/'output', args.out.resolve()
    assert not out.exists()
    control = common.frozen(source)
    result = commission(control, source) if args.mode == 'commission' else score(control, source, args.candidate.resolve())
    result['controls_sha256'] = sha(__file__)
    out.mkdir(parents=True)
    control.save(out/'result.json', control.jsonable(result))
    print('IN_FOCUS_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
