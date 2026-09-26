"""Independent first-fit commissioning/review; all19 cases are developer-visible."""
from pathlib import Path
import argparse
import importlib.util
import json
import math

HERE = Path(__file__).resolve().parent
OLD_CHECKER = HERE.parent / 'band-weight-oracle/independent-check.py'
OLD_SHA = 'be05178c244e69ddcd5e4b29a9b9c7d9da3770fea1caebd1ee398fe36b3a4012'
METRICS = ('rgb_rmse', 'green_rmse', 'chroma_rmse')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def prospective(old, case, rgb, np):
    historical = old.judge(case, rgb, np)
    rows = []
    flat = case['id'].startswith('held-flat-')
    for row in historical['windows']:
        c, u, p = (row[key] for key in ('canonical', 'uniform', 'candidate'))
        limits = [('canonical', c, 1.10 if flat else 1.05)]
        if flat:
            limits.append(('uniform', u, 1.10))
        failures = [f'{metric}>{factor}*{name}' for name, ref, factor in limits
                    for metric in METRICS if p[metric] > factor * ref[metric]]
        if not old.retained(c, p):
            failures.append('eligible_current_component_retention<0.90')
        positive = row['window'].endswith('-positive')
        if positive and p['rgb_rmse'] > .95 * c['rgb_rmse']:
            failures.append('positive_RGB_improvement<0.05_current')
        ratios = {name: {key: p[key]/ref[key] if ref[key] != 0 else None
                         for key in METRICS}
                  for name, ref in (('canonical', c), ('uniform', u))}
        rows.append({**row, 'prospective_pass': not failures,
                     'prospective_failures': failures, 'candidate_reference_ratios': ratios})
    return {'id': case['id'], 'developer_visible': True, 'historical': historical,
            'prospective_windows': rows, 'prospective_pass': all(r['prospective_pass'] for r in rows),
            'uniform_structured_chroma_is_descriptive': not flat}


def score_controls(old, cases, np):
    truth = [prospective(old, c, c['truth'], np) for c in cases]
    old.need(all(r['prospective_pass'] for r in truth), 'truth fails prospective judgments')
    thin, glint, colour, flat = cases[3], cases[4], cases[6], cases[0]
    rng = np.random.default_rng(0x42ab0179)
    mutants = {
        'erased_near': (thin, thin['truth']-thin['near']),
        'erased_far': (thin, thin['truth']-thin['far']),
        'suppressed_genuine_glint': (glint, glint['truth']-glint['far']),
        'erased_colour_image': (colour, np.zeros_like(colour['truth'])),
        'added_flat_noise': (flat, flat['truth'] + np.float32(.1)*rng.standard_normal(flat['truth'].shape).astype(np.float32)),
    }
    rows = {}
    for name, (case, mutant) in mutants.items():
        delta = float(np.max(np.abs(mutant-case['truth'])))
        old.need(delta > 0, 'score destroyer not exercised')
        row = prospective(old, case, mutant, np)
        old.need(not row['prospective_pass'], f'prospective score accepted {name}')
        rows[name] = {'maximum_mutation': delta, 'judgment': row}
    return {'truth_pass': True, 'destroyers_rejected': True, 'destroyers': rows}


def checked_weights(old, arrays, n, np):
    rows = []
    for k, (w, h) in enumerate(((80,72), (40,36), (20,18))):
        a = arrays[f'weights-{k}']
        old.need(a.shape == (n,h,w), 'weight shape differs')
        old.need(bool(np.isfinite(a).all()) and bool((a > 0).all()) and bool((a <= 2).all()),
                 'weights outside finite positive bounded-sigmoid domain')
        denominator = a.sum(axis=0, dtype=np.float32)
        old.need(bool(np.isfinite(denominator).all()) and bool((denominator > 0).all()),
                 'invalid denominator')
        rows.append({'band': k, 'minimum_weight': float(a.min()), 'maximum_weight': float(a.max()),
                     'minimum_denominator': float(denominator.min()),
                     'maximum_source_weight_spread': float(np.ptp(a, axis=0).max())})
    return rows


def mask_controls(old, subject, helper, paths, np, torch):
    # Assert every case's exact mask; mutation points are chosen independently.
    clipped = 'held-clipped-point-glint-n5'
    window_names = {
        'held-curved-bright-occlusion-n9': ['curved-bright-boundary-positive'],
        'held-near-fine-far-coarse-n5': ['near-fine-far-coarse-positive'],
        'held-unclipped-point-glint-n5': ['genuine-unclipped-glint'],
        'held-weak-colour-dots-n5': ['weak-colour-components'],
        clipped: ['glint-adjacent-near-detail', 'unclipped-spread-outside-core'],
    }
    records = []
    for path in paths:
        case = helper.load_case(path, np, torch, truth=False, goldens=False)
        batch = helper.batched([case], torch)
        valid = subject.loss_mask([case], batch, torch)
        expected = torch.ones((1,144,160), device='cuda')
        if path.parent.name == clipped:
            expected[:,57:80,61:84] = 0
        old.need(torch.equal(valid, expected), 'fixed clipped-only training support differs')
        roi = subject.loss_regions([case], batch, torch)
        expected_roi = np.zeros((144,160), dtype=np.float32)
        names = window_names.get(path.parent.name, [])
        areas = []
        for name in names:
            x0,y0,x1,y1 = old.WINDOWS[name]
            region = np.zeros_like(expected_roi)
            region[y0-16:y1-16,x0-16:x1-16] = 1
            if path.parent.name == clipped:
                region[57:80,61:84] = 0
            area = int(region.sum())
            old.need(area > 0, 'declared region has no retained support')
            areas.append(area)
            expected_roi += region/np.float32(area*len(names))
        actual_roi = roi[0].cpu().numpy()
        old.need(np.array_equal(actual_roi > 0, expected_roi > 0)
                 and np.allclose(actual_roi, expected_roi, rtol=2e-7, atol=0),
                 'ROI windows/equal-region normalization differs')
        old.need(abs(float(roi.sum())-(1. if names else 0.)) < 1e-6, 'ROI total mass differs')
        old.need(bool((roi[valid == 0] == 0).all()), 'ROI leaked excluded clipped core')
        records.append({'id': path.parent.name, 'excluded_pixels': int((valid == 0).sum()),
                        'roi_windows': names, 'roi_retained_areas': areas,
                        'roi_mass': float(roi.sum()),
                        'roi_weight_max_abs': float(np.max(np.abs(actual_roi-expected_roi)))})
        if path.parent.name in (clipped, 'held-unclipped-point-glint-n5'):
            truth = torch.zeros((1,144,160,3), device='cuda')
            weights = [torch.ones_like(batch[f'coeff-{k}'][:,:,0]) for k in range(3)]
            mutated = truth.clone()
            mutated[:,57,61] = torch.tensor([.3,.8,-.2], device='cuda')
            loss, parts = subject.per_case_loss(mutated, truth, weights, torch.zeros(1, device='cuda'), torch, valid, roi)
            if path.parent.name == clipped:
                old.need(float(loss[0]) == 0 and all(float(v[0]) == 0 for v in parts.values()),
                         'clipped corner/gradient stencil leaked into loss')
            else:
                old.need(float(loss[0]) > 0, 'genuine unclipped core was silenced')
            # A point one pixel OUTSIDE the excluded rectangle must remain live.
            outside = truth.clone()
            outside[:,57,60] = 1
            outside_loss, _ = subject.per_case_loss(outside, truth, weights, torch.zeros(1, device='cuda'), torch, valid, roi)
            old.need(float(outside_loss[0]) > 0, 'mask removed outside support')
    return {'exact_masks': records, 'clipped_core_output_xyxy': [61,57,84,80],
            'inside_corner_and_crossing_gradient_refused': True,
            'outside_and_genuine_unclipped_mutations_live': True}


def direction(old, subject, helper, case, np, torch):
    loaded = helper.load_case(case['path'], np, torch, truth=True, goldens=False)
    batch = helper.batched([loaded], torch)
    features, _ = subject.build_features(batch, helper, torch)
    model = subject.make_model(torch)
    with torch.no_grad():
        values = torch.arange(model.head.weight.numel(), device='cuda', dtype=torch.float32)
        model.head.weight.copy_((.013*torch.sin(values+.7)).reshape_as(model.head.weight))
        model.head.bias.fill_(.009)
    valid = subject.loss_mask([loaded], batch, torch)
    roi = subject.loss_regions([loaded], batch, torch)
    def loss():
        weights = [model(f) for f in features]
        _, rgb, _ = helper.reconstruct(batch, weights, torch)
        value, _ = subject.per_case_loss(rgb, batch['truth-rgb'], weights,
                                        torch.zeros(1, device='cuda'), torch, valid, roi)
        return value.mean()
    objective = loss()
    grad, = torch.autograd.grad(objective, model.head.weight)
    old.need(bool(torch.isfinite(grad).all()) and float(grad.abs().max()) > 0, 'head gradient is not live')
    # Pick largest magnitude only for numerical conditioning, never by quality.
    index = int(grad.abs().flatten().argmax())
    signed = float(grad.flatten()[index])
    descent_sign = -1. if signed > 0 else 1.
    epsilon = .01
    saved = model.head.weight.detach().clone()
    with torch.no_grad():
        model.head.weight.flatten()[index] += epsilon*descent_sign
        plus = float(loss())
        model.head.weight.copy_(saved)
        model.head.weight.flatten()[index] -= epsilon*descent_sign
        minus = float(loss())
        model.head.weight.copy_(saved)
    ad = signed*descent_sign
    fd = (plus-minus)/(2*epsilon)
    relative = abs(fd-ad)/abs(ad)
    old.need(math.isfinite(relative) and relative <= .05, 'new scorer directional derivative differs by >5%')
    old.need(plus < float(objective) < minus, 'declared loss descent/ascent foil not exercised')
    return {'case': case['id'], 'head_index': index, 'epsilon': epsilon,
            'objective0': float(objective), 'descent_objective': plus, 'ascent_objective': minus,
            'autograd_derivative': ad, 'central_difference': fd, 'relative_error': relative,
            'selection_is_gradient_magnitude_conditioning': True, 'passed': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('check-commission', 'check'))
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--commission', type=Path)
    parser.add_argument('--predictions', type=Path)
    parser.add_argument('--weights', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    import hashlib
    if hashlib.sha256(OLD_CHECKER.read_bytes()).hexdigest() != OLD_SHA:
        raise RuntimeError('trusted analytic/native-score checker changed')
    old = module(OLD_CHECKER, 'cross_scale_existing_score')
    old.sha(OLD_CHECKER)
    old.need(not args.out.exists(), 'fresh independent output required')
    args.out.mkdir()
    source_sha = old.sha(HERE/'train.py')
    subject = module(HERE/'train.py', 'cross_scale_subject')
    helper = old.consumer()
    np, torch = helper.runtime()
    cases, historic_commission = old.load_cases(args.dataset, np)
    score_commission = score_controls(old, cases, np)
    manifest = helper.manifest(args.dataset)
    paths = manifest['training'] + manifest['heldout']
    common = {'schema': 1, 'source_sha256': source_sha, 'checker_sha256': old.sha(__file__),
              'dataset_sha256': old.sha(args.dataset), 'consumer_sha256': old.CONSUMER_SHA,
              'all19_are_developer_visible': True, 'old_seven_are_known_regressions': True,
              'independent_validation': False, 'photographic_replay_admitted': False,
              'historical_score_commission': historic_commission,
              'prospective_score_commission': score_commission}
    if args.phase == 'check-commission':
        old.need(args.commission is not None, 'original author commission required')
        original = old.load(args.commission)
        old.need(original['passed'] is True and original['source_sha256'] == source_sha
                 and original['dataset_sha256'] == old.DATASET_SHA, 'original commission binding differs')
        old.need([row['case_sha256'] for row in original['cases']] == [old.sha(p) for p in paths],
                 'original commission case coverage differs')
        result = {**common, 'status': 'INDEPENDENT_COMMISSION_COMPLETE', 'passed': True,
                  'author_commission': str(args.commission.resolve()),
                  'author_commission_sha256': old.sha(args.commission),
                  'fixed_support': mask_controls(old, subject, helper, paths, np, torch),
                  'new_scorer_direction': direction(old, subject, helper, cases[3], np, torch)}
        destination = args.out/'commission.json'
    else:
        old.need(args.predictions is not None and args.weights is not None, 'predictions and model required')
        predictions = old.load(args.predictions)
        old.need(predictions['dataset_sha256'] == old.DATASET_SHA
                 and predictions['consumer_sha256'] == old.CONSUMER_SHA
                 and predictions['source_sha256'] == source_sha
                 and predictions['model_sha256'] == old.sha(args.weights)
                 and predictions['truth_read'] is False
                 and predictions['all19_are_developer_cases'] is True, 'inference binding/scope differs')
        old.need(len(predictions['records']) == 19, 'all19 predictions required')
        old.load(args.weights)
        model = subject.load_model(args.weights, torch)
        scored, replay, development = [], [], []
        known = {c['path']: c for c in cases}
        for path, row in zip(paths, predictions['records']):
            loaded = helper.load_case(path, np, torch, truth=True, goldens=True)
            for item in loaded['bindings']:
                old.need(old.sha(item['file']) == item['sha256'], 'consumer array binding differs')
            case = {'path': path, 'meta': loaded['meta']}
            pred = old.prediction(row, case, np)
            weight_rows = checked_weights(old, pred, loaded['meta']['source_count'], np)
            batch = helper.batched([loaded], torch)
            features, _ = subject.build_features(batch, helper, torch)
            weights = [torch.from_numpy(pred[f'weights-{k}'].copy()).to('cuda')[None] for k in range(3)]
            with torch.no_grad():
                inferred = [model(f) for f in features]
                me = max(float((a-b).abs().max()) for a,b in zip(inferred,weights))
                old.need(me == 0, 'saved model does not exactly reproduce saved weights')
                cfa, rgb, _ = helper.reconstruct(batch, weights, torch)
            ca, ra = cfa[0].cpu().numpy(), rgb[0].cpu().numpy()
            old.need(np.array_equal(ca, pred['cfa']) and np.array_equal(ra, pred['rgb']),
                     'saved weights do not exactly reconstruct saved CFA/RGB')
            replay.append({'id': path.parent.name, 'model_weights_exact': True, 'cfa_rgb_exact': True,
                           'all_boundary_pixels_included': True, 'bands': weight_rows})
            truth = batch['truth-rgb'][0].cpu().numpy().astype(np.float64)
            e = pred['rgb'].astype(np.float64)-truth
            development.append({'id': path.parent.name, 'developer_visible': True,
                                'whole_rgb_rmse': float(np.sqrt(np.mean(e*e))),
                                'whole_green_rmse': float(np.sqrt(np.mean(e[:,:,1]**2))),
                                'whole_chroma_rmse': float(np.sqrt(np.mean(np.stack((e[:,:,0]-e[:,:,1],e[:,:,2]-e[:,:,1]))**2))),
                                'whole_error_includes_unqualified_clipped_core': path.parent.name == 'held-clipped-point-glint-n5'})
            if path in known:
                scored.append(prospective(old, known[path], pred['rgb'], np))
        old.need([r['id'] for r in scored] == old.IDS, 'old seven regression coverage differs')
        result = {**common, 'status': 'DEVELOPER_SCREEN_COMPLETE', 'mechanical_pass': True,
                  'model_sha256': old.sha(args.weights), 'predictions_sha256': old.sha(args.predictions),
                  'weight_replay': replay, 'all19_development_errors': development, 'cases': scored,
                  'all_historical_guards_pass': all(r['historical']['pass'] for r in scored),
                  'all_prospective_development_guards_pass': all(r['prospective_pass'] for r in scored),
                  'candidate_nominated': False, 'failed_fit_proves_ceiling': False}
        destination = args.out/'screen.json'
    old.need(old.sha(HERE/'train.py') == source_sha, 'subject source changed during check')
    result['inputs'] = [{'path': p, 'sha256': v} for p,v in sorted(old.BINDINGS.items())]
    with destination.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
