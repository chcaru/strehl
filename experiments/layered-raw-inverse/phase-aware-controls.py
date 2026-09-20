"""Independent phase-plant observations and fixed-final controls; never fits."""
from pathlib import Path
from dataclasses import asdict, replace
import argparse
import importlib.util
import struct
import sys
import time
import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('phase_control_common', HERE/'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read, load = common.sha, common.read, common.load
TRAIN, HELD, REFERENCE = [0, 2, 3, 4, 6, 7], [1, 5], 3
SOURCE = HERE/'screen-1'/'output'
PARAMETERS = ['near', 'far', 'alpha_logit']


def modules():
    control = common.frozen(SOURCE)
    focus = load(HERE/'in-focus-controls.py', 'phase_focus_controls')
    assert sha(HERE/'in-focus-controls.py') == '8aa5850574c9882aa6bb252bb21299a1e3625e45240850cd519a3e0649559891'
    pupil = load(HERE/'pupil-stencil-controls.py', 'phase_pupil_controls')
    author = load(HERE/'phase-aware.py', 'phase_author_controls')
    return control, focus, pupil, author


def geometry():
    root = HERE.parent/'quality-september14'
    census_path = root/'chip-corrected-sample-diversity-1.json'
    census = read(census_path)
    bindings = {str(census_path): sha(census_path), **census['source_hashes']}
    assert all(sha(p) == h for p, h in bindings.items())
    warp = root/'chip-baseline-1'/'chip.warpmap.txt'
    corrections = {r['frame']: r for r in read(root/'local-green-translation-1'/'result.json')['frames']}
    mappings = {}
    for line in warp.read_text().splitlines():
        p = line.split()
        if p and p[0].isdigit() and p[1] == 'placed':
            bits = [struct.unpack('>d', bytes.fromhex(v))[0] for v in p[2:6]]
            mappings[int(p[0])] = (complex(*bits[:2]), complex(*bits[2:]))
    point, centre = complex(1527.5, 1299.5), complex(3516, 2344)
    saved = {r['frame']: r for r in census['sites']['centre']['arms']['corrected-eight']['frames']}
    displacements = []
    for index in range(146, 154):
        correction = corrections[index]
        assert not correction['at_translation_bound']
        a, b = mappings[index]
        d = centre+a*(point-centre)+2*b+complex(*correction['delta_source_native'])-point
        actual = np.array([d.real, d.imag], np.float64)
        assert np.max(np.abs(actual-saved[index]['mapped_displacement_native'])) < 1e-10
        displacements.append(actual)
    delta = np.array(displacements)-displacements[REFERENCE]
    phase = -((delta+1.) % 2.-1.)
    assert np.array_equal(phase[REFERENCE], [0., 0.]) and np.max(np.abs(phase)) <= 1
    assert tuple(np.array([1527.5, 1299.5])-47.5) == (1480., 1252.)
    assert np.max(np.abs(phase)) > .1, 'phase stimulus absent'
    return phase, dict(bindings=bindings, source_indices=list(range(146, 154)), reference=149,
        point_native=[1527.5, 1299.5], mapped_displacements_native=np.array(displacements).tolist(),
        formula='t=-(((d-d149)+1)%2-1)', reduction='unit-scale translation plant; no a division',
        synthetic_origin_native=[1480, 1252], rggb_parity_preserved=True)


def config(author, control):
    return author.model.Config(width=96, height=96, focus_coordinates=tuple(k/7 for k in range(8)),
        gain=float(control.GAIN), read_variance=float(control.READ_VARIANCE), psf_sigma=float(np.float32(.7)))


def polar(n, phase):
    # Independently constructed equal-area polar setup in f64; image arithmetic f32.
    r = np.sqrt((np.arange(n, dtype=np.float64)+.5)/n)
    theta = 2*np.pi*(np.arange(n, dtype=np.float64)+.5)/n+phase
    return np.stack((r[:, None]*np.cos(theta), r[:, None]*np.sin(theta)), -1).reshape(-1, 2)


def reference_chunk(fields, cfg, index, pupil, translation):
    """Independent ray integration, no joint-table implementation imported."""
    near, far, alpha = fields
    h, w = cfg.height, cfg.width
    yy, xx = torch.meshgrid(torch.arange(h, device='cuda', dtype=torch.float32),
                            torch.arange(w, device='cuda', dtype=torch.float32), indexing='ij')
    rays = torch.tensor(np.array(pupil, np.float32, copy=True), device='cuda')
    base = torch.stack([xx, yy], -1)[None]+near.new_tensor(translation)[None, None, None]
    def pull(image, depth):
        shift = np.float32(cfg.defocus_scale*(cfg.focus_coordinates[index]-depth))
        position = base+shift*rays[:, None, None]
        grid = torch.stack((2*position[..., 0]/(w-1)-1, 2*position[..., 1]/(h-1)-1), -1)
        return F.grid_sample(image.permute(2, 0, 1)[None].expand(len(rays), -1, -1, -1),
            grid, mode='bilinear', padding_mode='zeros', align_corners=True).permute(0, 2, 3, 1)
    front = pull(torch.cat((alpha[..., None]*near, alpha[..., None]), -1), cfg.inverse_depths[0])
    back = pull(far, cfg.inverse_depths[1])
    return (front[..., :3]+(1-front[..., 3:])*back).mean(0)


def reference(fields, cfg, index, pupil, translation, focus):
    out = torch.zeros_like(fields[0])
    with torch.no_grad():
        for begin in range(0, len(pupil), 1024):
            rays = pupil[begin:begin+1024]
            out += reference_chunk(fields, cfg, index, rays, translation)*np.float32(len(rays)/len(pupil))
    return focus.optical(out.cpu().numpy().copy())


def table(author, cfg, index, pupil, translation):
    shifts = [cfg.defocus_scale*(cfg.focus_coordinates[index]-d) for d in cfg.inverse_depths]
    return author.build_translated_table(pupil, *shifts, translation)


def literal(pupil_control, fields, cfg, index, pupil, translation):
    n, f, a = fields
    out = np.zeros_like(n)
    shifts = [cfg.defocus_scale*(cfg.focus_coordinates[index]-d) for d in cfg.inverse_depths]
    for u in pupil:
        pn = np.asarray(translation)+shifts[0]*u
        pf = np.asarray(translation)+shifts[1]*u
        front = pupil_control.sample(a[..., None]*n, *pn)
        coverage = pupil_control.sample(a, *pn)
        back = pupil_control.sample(f, *pf)
        out += front+(np.float32(1)-coverage[..., None])*back
    return out*np.float32(1/len(pupil))


def commission(control, focus, pc, author):
    phase, provenance = geometry()
    cfg = replace(config(author, control), width=48, height=44)
    y, x = np.mgrid[:44, :48].astype(np.float32)
    n = np.stack((800+10*x, 1700+8*y, 1100+3*x), -1)
    f = np.stack((1700+9*y, 800+4*x, 2300-3*y), -1)
    a = (.15+.65*np.exp(-.5*((x-23)/2.2)**2)).astype(np.float32)
    values = [n, f, a]
    small = control.pupil_pairs(64)
    tests = []
    for index in [0, 3, 7]:
        for endpoint in [None, 0., 1.]:
            fields_np = [n, f, a if endpoint is None else np.full_like(a, endpoint)]
            tensors = pc.tensors(fields_np)
            tb = table(author, cfg, index, small, phase[index])
            actual = author.forward(*tensors, cfg, index, table=tb).detach().cpu().numpy()
            wanted = focus.optical(literal(pc, fields_np, cfg, index, small, phase[index]))
            error = float(np.max(np.abs(actual-wanted)))
            assert error <= .1, (index, endpoint, error)
            tests.append(dict(index=index, alpha=endpoint, max_abs_dn=error))
    # Fractional coincident-depth positions still require all p,q bilinear pairs.
    delta = [.37, -.61]
    direct = pc.sample(a[..., None]*n, *delta)+(1-pc.sample(a, *delta)[..., None])*pc.sample(f, *delta)
    wrong = pc.sample(a[..., None]*n+(1-a[..., None])*f, *delta)
    diagonal = author.build_translated_table(np.array([[0., 0.]]), 0., 0., delta)
    # forward validates optical geometry; use the joint kernel directly for this literal diagonal.
    return commission_dense(control, focus, pc, author, cfg, values, phase, tests,
                            provenance, direct, wrong, diagonal)


def commission_dense(control, focus, pc, author, cfg, values, phase, tests, provenance, direct, wrong, diagonal):
    joint = author.stencil.joint_pupil(*pc.tensors(values), diagonal).detach().cpu().numpy()
    assert np.max(np.abs(joint-direct)) <= .1
    diagonal_destroyer = float(np.max(np.abs(direct-wrong)))
    assert diagonal_destroyer > .1
    # Quarter-diagonal CFA cancellation is useful only if each axis survives.
    y, x = np.mgrid[:44, :48]
    axis_x, axis_y = np.cos(np.pi*x).astype(np.float32), np.cos(np.pi*y).astype(np.float32)
    cancellation = {}
    for label, translation in [('diagonal', [.25, .25]), ('x_only', [.25, 0.])]:
        outputs = []
        for perturbation in [axis_x, axis_y, axis_x-axis_y]:
            image = np.full((44, 48, 3), 1000, np.float32)
            image[..., 0] += 100*perturbation
            tb0 = author.build_translated_table(np.array([[0., 0.]]), 0., 0., translation)
            # Alpha0 makes the literal far translation valid even at zero-padded boundaries.
            output = author.stencil.joint_pupil(*pc.tensors([image, image, np.zeros((44, 48), np.float32)]), tb0)
            expected0 = pc.sample(image, *translation)
            assert np.max(np.abs(output.cpu().numpy()-expected0)) <= .001
            delivered = focus.optical(output.cpu().numpy())
            outputs.append(float(np.max(np.abs(delivered[16:28:2, 16:32:2, 0]-1000))))
        assert min(outputs[:2]) > 1
        assert outputs[2] < .001 if label == 'diagonal' else outputs[2] > 1
        cancellation[label] = dict(individual_axis_max_dn=outputs[:2], difference_max_dn=outputs[2])
    pupil = polar(128, .23)
    index = 4
    tb = table(author, cfg, index, pupil, phase[index])
    actual_fields = pc.tensors(values, True)
    result = author.forward(*actual_fields, cfg, index, table=tb)
    probe = torch.linspace(-1, 1, result.numel(), device='cuda').reshape_as(result)
    probe = probe/np.float32(result.numel())
    actual_gradients = torch.autograd.grad((result*probe).sum(), actual_fields)
    expected_gradients = [torch.zeros_like(v) for v in actual_fields]
    expected = torch.zeros_like(result)
    for begin in range(0, len(pupil), 1024):
        inputs = pc.tensors(values, True)
        chunk = reference_chunk(inputs, cfg, index, pupil[begin:begin+1024], phase[index])
        # Frozen optical blur is commissioned independently by focus controls.
        chunk = author.model._blur(chunk, cfg.psf_sigma)*np.float32(1024/len(pupil))
        derivatives = torch.autograd.grad((chunk*probe).sum(), inputs)
        expected += chunk.detach()
        for accumulated, g in zip(expected_gradients, derivatives):
            accumulated += g
    forward_error = float((result.detach()-expected).abs().max())
    assert forward_error <= .1
    gradients = []
    for label, measured, wanted in zip(['near', 'far', 'alpha'], actual_gradients, expected_gradients):
        diff = measured-wanted
        maximum = float(diff.abs().max())
        relative = float(torch.linalg.vector_norm(diff)/torch.linalg.vector_norm(wanted))
        assert maximum <= 1e-5+3e-4*float(wanted.abs().max()) and relative <= 3e-4
        gradients.append(dict(field=label, max_abs=maximum, relative_l2=relative))
    # Literal independent finite difference on a small translated same-ray operator.
    literals = control.pupil_pairs(64)
    weights = probe.cpu().numpy()
    finite = []
    yy = np.arange(cfg.height, dtype=np.float32)[:, None]/np.float32(cfg.height-1)
    for plane, step in [(0, .25), (1, .25), (2, .25)]:
        direction = np.broadcast_to(np.float32(.2)+yy, values[plane].shape[:2]).copy()
        if plane != 2:
            direction = np.repeat(direction[..., None], 3, axis=2)
        else:
            direction *= np.float32(.2)
        inputs = pc.tensors(values, True)
        small_table = table(author, cfg, index, literals, phase[index])
        output = author.forward(*inputs, cfg, index, table=small_table)
        gradient = torch.autograd.grad((output*probe).sum(), inputs)[plane]
        derivative = float((gradient*torch.tensor(direction, device='cuda')).sum())
        objectives = []
        for sign in [-1, 1]:
            changed = [v.copy() for v in values]
            changed[plane] += np.float32(sign*step)*direction
            assert np.isfinite(changed[2]).all() and np.all((changed[2] >= 0) & (changed[2] <= 1))
            image = focus.optical(literal(pc, changed, cfg, index, literals, phase[index]))
            objectives.append(float(np.sum(image.astype(np.float64)*weights, dtype=np.float64)))
        fd = (objectives[1]-objectives[0])/(2*step)
        bound = 2e-4+.005*abs(derivative)
        print('PHASE_LITERAL_FD', dict(field=plane, step=step, objectives=objectives,
              finite_difference=fd, autograd=derivative, tolerance=bound), flush=True)
        assert abs(fd-derivative) <= bound
        assert abs(derivative) > 10*bound and abs(fd) > bound and abs(fd-2*derivative) > bound
        finite.append(dict(field=plane, autograd=derivative, finite_difference=fd, tolerance=bound,
                           zero_and_doubled_derivatives_rejected=True, direction_sha256=control.digest(direction)))
    optical = focus.commission(control, SOURCE)
    return dict(passed=optical['passed'], mechanics=tests, dense_forward_max_dn=forward_error,
        dense_adjoint=gradients, literal_finite_difference=finite, diagonal_product_destroyer_dn=diagonal_destroyer,
        quarter_diagonal=cancellation, optical=optical, phase_provenance=provenance, no_fit=True)


def write_array(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists()
    np.save(path, np.ascontiguousarray(value), allow_pickle=False)


def generate(control, focus, pc, author, out):
    phase, provenance = geometry()
    cfg = config(author, control)
    fit_pupil, observation_pupil = polar(128, .23), polar(128, .60)
    write_array(out/'pupil-f64.npy', fit_pupil)
    cases, adequacy, initializers = {}, [], {}
    for ci, case in enumerate(['flat', 'layered']):
        latent = control.scene(case)
        fields = pc.tensors([latent[k] for k in ['near', 'far', 'alpha']])
        evaluation = out/'evaluation'/case
        target = focus.optical(latent['truth'])
        write_array(evaluation/'truth-rgb-f32.npy', target)
        paths, frames = {}, {}
        for mode, shifts in [('identity', np.zeros_like(phase)), ('phase', phase)]:
            expected, observed = [], []
            mean_sum, donor = np.zeros_like(target), np.zeros_like(target)
            best_error = np.full(target.shape[:2], np.inf, np.float32)
            for k in range(8):
                rgb = reference(fields, cfg, k, observation_pupil, shifts[k], focus)
                codes = control.observation(control.cfa_numpy(rgb), 20260923+1000*ci+k)
                expected.append(control.cfa_numpy(rgb)+np.float32(cfg.black))
                observed.append(codes)
                with torch.no_grad():
                    fitted = author.forward(*fields, cfg, k, table=table(author, cfg, k, fit_pupil, shifts[k])).cpu().numpy()
                adequacy.append(dict(case=case, geometry=mode, index=k, **pc.discrepancy(control, fitted, rgb)))
                if k in TRAIN:
                    registered = pc.sample(control.develop_bilinear(codes), *(-shifts[k]))
                    noiseless = pc.sample(rgb, *(-shifts[k]))
                    error = np.mean((noiseless-target)**2, axis=2, dtype=np.float32)
                    better = error < best_error  # Strict: the first source wins exact ties.
                    donor[better] = registered[better]
                    best_error[better] = error[better]
                    mean_sum += registered  # Fixed source order, f32, one current RGB frame.
            original = np.stack(observed)
            assert original.dtype == np.uint16 and original.shape == (8, 96, 96)
            frames[mode] = original
            paths[mode] = f'{case}/{mode}-u16.npy'
            write_array(out/paths[mode], original)
            write_array(evaluation/f'{mode}-expected-cfa-f32.npy', np.stack(expected))
            mean = mean_sum/np.float32(len(TRAIN))
            write_array(evaluation/f'{mode}-mean-rgb-f32.npy', mean)
            write_array(evaluation/f'{mode}-donor-rgb-f32.npy', donor)
        assert np.array_equal(frames['identity'][REFERENCE], frames['phase'][REFERENCE])
        initializers[case] = control.digest(frames['phase'][REFERENCE])
        cases[case] = paths
    manifest = dict(schema=1, config=asdict(cfg), train_indices=TRAIN, held_indices=HELD,
        reference_index=REFERENCE, translations_native=phase.tolist(), pupil_path='pupil-f64.npy',
        cases=cases, phase_provenance=provenance)
    control.save(out/'manifest.json', control.jsonable(manifest))
    files = {str(p.relative_to(out)): sha(p) for p in out.rglob('*') if p.is_file()}
    passed = all(r['passed'] for r in adequacy)
    return dict(status='GENERATED' if passed else 'OPTICAL_ADEQUACY_REFUSED', passed=passed,
        files=files, initializer_u16_sha256=initializers, adequacy=adequacy,
        generator='Independent same-ray grid_sample, <=1024-ray chunks, separate16384 phase.60',
        candidate_pupil_phase=.23, no_heldout_baseline_use=True, no_fit=True,
        observations_sha256={case: {g: sha(out/p) for g, p in ps.items()} for case, ps in cases.items()})


def read_arm(control, focus, author, data, fits, case, mode, manifest):
    directory = fits/case/mode
    receipt = read(directory/'receipt.json')
    selected = 'identity' if mode == 'identity' else 'phase'
    observed_path = data/manifest['cases'][case][selected]
    observed = np.load(observed_path, allow_pickle=False)
    cfg = author.model.Config(**manifest['config'])
    assert receipt['config'] == manifest['config'] and receipt['case'] == case and receipt['geometry'] == mode
    assert receipt['observed_geometry'] == selected and receipt['observation_sha256'] == sha(observed_path)
    assert receipt['train_indices'] == receipt['read_indices'] == TRAIN and receipt['held_indices'] == HELD
    assert receipt['gradient_parameter_names'] == PARAMETERS and receipt['visibility'] == 'free-original-sigmoid'
    assert receipt['training_sha256'] == [control.digest(observed[k]) for k in TRAIN]
    assert receipt['initial_reference_u16_sha256'] == control.digest(observed[REFERENCE])
    assert receipt['source_bindings_unchanged'] and receipt['hard_evaluation_cap'] == 1800
    assert 1 <= receipt['actual_evaluations'] <= 1800 and receipt['adam_evaluations'] <= 160
    assert receipt['support_native_xywh'] == [16, 16, 64, 64]
    wanted_phases = manifest['translations_native'] if mode == 'phase' else np.zeros((8, 2)).tolist()
    assert np.allclose(receipt['applied_translations_native'], wanted_phases, rtol=0, atol=1e-10)
    assert receipt['dense_pupil']['count'] == 16384 and receipt['dense_pupil']['sha256'] == sha(data/manifest['pupil_path'])
    for binding in receipt['source_bindings'].values():
        assert sha(binding['path']) == binding['sha256']
    state = author.initialize(observed[REFERENCE], cfg)
    wanted_parameters = {n: control.digest(p.detach().cpu().numpy()) for n, p in state.named_parameters()}
    assert wanted_parameters == receipt['initial_parameter_sha256']
    initial = author.model.FitResult(state, cfg, 'two-layer', [], receipt['training_sha256'])
    with np.load(directory/'initial-reconstruction.npz', allow_pickle=False) as snapshot:
        for name in ['near_rgb', 'far_rgb', 'alpha', 'pinhole_rgb']:
            assert np.array_equal(snapshot[name], getattr(initial, name))
            assert control.digest(snapshot[name]) == receipt['initial_field_sha256'][name]
    assert np.all(initial.alpha == .5) and np.array_equal(initial.near_rgb, initial.far_rgb)
    complete = receipt['status'] != 'numerical_refusal' and receipt['final_objective'] is not None
    if not complete:
        return dict(complete=False, receipt=receipt)
    assert receipt['returned_state_accepted'] and receipt['adam_steps_completed'] == 160
    assert sha(directory/'state.pt') == receipt['state_sha256']
    assert sorted(p['index'] for p in receipt['predictions']) == HELD
    for prediction in receipt['predictions']:
        assert prediction['path'] == f"predicted-cfa-{prediction['index']}.npy"
        assert sha(directory/prediction['path']) == prediction['sha256']
    with np.load(directory/'reconstruction.npz', allow_pickle=False) as saved:
        pinhole = saved['pinhole_rgb'].copy()
    assert np.array_equal(pinhole, np.load(directory/'pinhole-rgb-f32.npy', allow_pickle=False))
    image = np.load(directory/'in-focus-rgb-f32.npy', allow_pickle=False)
    assert image.dtype == np.float32 and image.shape == (96, 96, 3) and np.isfinite(image).all()
    assert np.max(np.abs(image-focus.optical(pinhole))) <= focus.tolerance(pinhole)
    expected = np.load(data/'evaluation'/case/f'{selected}-expected-cfa-f32.npy', allow_pickle=False)
    held = [dict(index=k, **control.prediction_score(np.load(directory/f'predicted-cfa-{k}.npy'), observed[k], expected[k])) for k in HELD]
    return dict(complete=True, receipt=receipt, image=image, pinhole=pinhole, held=held,
                output_sha256={str(p.relative_to(directory)): sha(p) for p in directory.iterdir() if p.is_file()})


def score(control, focus, author, data, fits, case):
    assert case in ['flat', 'layered']
    generated, manifest = read(data/'result.json'), read(data/'manifest.json')
    assert generated['passed'] and generated['status'] == 'GENERATED'
    before = {p: sha(data/p) for p in generated['files']}
    assert before == generated['files']
    phases, provenance = geometry()
    assert np.array_equal(np.array(manifest['translations_native']), phases)
    assert manifest['phase_provenance'] == provenance
    modes = ['identity', 'phase']+(['wrong'] if case == 'layered' else [])
    arms = {mode: read_arm(control, focus, author, data, fits, case, mode, manifest) for mode in modes}
    for mode in modes:
        assert arms[mode]['receipt']['initial_parameter_sha256'] == arms['identity']['receipt']['initial_parameter_sha256']
        assert arms[mode]['receipt']['initial_field_sha256'] == arms['identity']['receipt']['initial_field_sha256']
    if not all(a['complete'] for a in arms.values()):
        return dict(passed=False, continue_layered=False, status='NUMERICAL_REFUSAL',
                    arms={k: dict(complete=v['complete'], status=v['receipt']['status']) for k, v in arms.items()})
    latent = control.scene(case)
    target = np.load(data/'evaluation'/case/'truth-rgb-f32.npy')
    assert np.array_equal(target, focus.optical(latent['truth']))
    components = focus.transformed_components(latent)
    focus.generator_psf_checks(control, latent)
    old = HERE/'in-focus-2'/'delivered'/case
    retained = {name: np.load(old/f'{name}-rgb-f32.npy') for name in ['visibility', 'far-only']}
    retained_target_error = float(np.max(np.abs(target-np.load(old/'truth-rgb-f32.npy'))))
    assert retained_target_error <= focus.tolerance(latent['truth'])
    retained_hashes = {str(old/f'{k}-rgb-f32.npy'): sha(old/f'{k}-rgb-f32.npy') for k in retained}
    reports, quality_images = {}, {}
    for mode, arm in arms.items():
        observed_mode = 'identity' if mode == 'identity' else 'phase'
        images = dict(truth=target, **retained, candidate=arm['image'])
        for label, suffix in [('mean-observed', 'mean'), ('donor-observed', 'donor')]:
            images[label] = np.load(data/'evaluation'/case/f'{observed_mode}-{suffix}-rgb-f32.npy')
        quality_images[mode] = images
        q = focus.quality(control, case, images, 'candidate', components)
        reports[mode] = dict(quality=q, held=arm['held'], held_pass=all(r['passed'] for r in arm['held']),
            pinhole_regions={r: control.score(arm['pinhole'], latent['truth'], r) for r in (['whole'] if case == 'flat' else control.REGIONS)},
            status=arm['receipt']['status'], final_objective=arm['receipt']['final_objective'],
            same_data_mean_bars={k: v for k, v in q['bars'].items() if 'mean' in k},
            retained_nonmatched_bars={k: v for k, v in q['bars'].items() if 'visibility' in k or 'far_only' in k},
            outputs=arm['output_sha256'])
    candidate, identity = arms['phase']['image'], arms['identity']['image']
    paired, detail = {}, {}
    for region in (['whole'] if case == 'flat' else ['core', 'ridge']):
        a, b = control.score(candidate, target, region), control.score(identity, target, region)
        for key in ['rgb_rmse', 'chroma_rmse']:
            paired[region+'_'+key] = a[key] <= (1.05 if case == 'flat' else 1.02)*b[key]
    if case == 'layered':
        a, b = control.score(candidate, target), control.score(identity, target)
        for key in ['rgb_rmse', 'chroma_rmse']:
            paired['whole_'+key+'_useful_phase_gain'] = a[key] <= .95*b[key]
        for name, region in focus.COMPONENTS:
            a, b = [focus.component(control, img, components, name, region) for img in [candidate, identity]]
            paired[name+'_identity_component'] = focus.component_guard(a, b)
            detail[name] = dict(phase=a, identity=b)
    fixed_pass = reports['phase']['quality']['passed'] and reports['phase']['held_pass']
    # Wrong-phase is a capability check, never the benefit reference.
    wrong_rejected = case == 'flat' or not (reports['wrong']['quality']['passed'] and reports['wrong']['held_pass'])
    passed = bool(fixed_pass and all(paired.values()) and wrong_rejected)
    assert {p: sha(data/p) for p in generated['files']} == before
    return dict(status='SCORED', case=case, passed=passed, continue_layered=bool(case == 'flat' and passed),
        reports=reports, paired_identity_bars=paired, paired_components=detail,
        fixed_target_pass=fixed_pass, wrong_phase_rejected=wrong_rejected,
        old_reference_scope='Strict retained seven-training/64-pupil known-alpha target; not a paired phase regression',
        retained_target_psf_max_abs_dn=retained_target_error, retained_target_psf_bound_dn=focus.tolerance(latent['truth']),
        new_reference_scope='Six-training dense observations; phase and identity noise distributions share seeds, frame149 exact',
        nonstationarity_is_not_image_quality=True, original_data_unchanged=True, retained_source_hashes=retained_hashes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['commission', 'generate', 'score'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--data', type=Path)
    parser.add_argument('--fits', type=Path)
    parser.add_argument('--case', choices=['flat', 'layered'])
    args = parser.parse_args()
    out = args.out.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    control, focus, pc, author = modules()
    started = time.monotonic()
    torch.cuda.reset_peak_memory_stats()
    if args.command == 'commission':
        result = commission(control, focus, pc, author)
    elif args.command == 'generate':
        result = generate(control, focus, pc, author, out)
    else:
        result = score(control, focus, author, args.data.resolve(), args.fits.resolve(), args.case)
    result.update(seconds=time.monotonic()-started, cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                  cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(), real_photo_admission=False)
    assert result['cuda_peak_allocated_bytes'] <= 8*1024**3
    control.save(out/'result.json', control.jsonable(result))
    print('PHASE_AWARE_CONTROL', args.command, result.get('passed'), flush=True)


if __name__ == '__main__':
    main()
