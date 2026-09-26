"""Independent changed-path commissioning on old developer data, never fresh truth."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent / 'learned-band-guide/export-1/output/dataset.json'
DATASET_SHA = '0c8e7c457f971cc387fa06e7f5261e2b9ef15014c6591b6d7950ce0acdda9e19'
NAMES = ['train-flat-0', 'held-near-fine-far-coarse-n5', 'held-curved-bright-occlusion-n9']


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def delta(a, b, torch):
    need(a.shape == b.shape and bool(torch.isfinite(a).all() and torch.isfinite(b).all()), 'comparison shape/finite')
    return float((a-b).abs().max())


def model_for_control(scorer, torch):
    model = scorer.make_model(torch)
    # Four asymmetric three-layer paths: actual signed, parent, child and set SD.
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
        for branch, feature, ky, kx, head in [(0, 0, 1, 2, .375), (1, 12, 2, 2, -.25),
                                              (2, 17, 0, 0, .125), (3, 8, 2, 0, .1875)]:
            model.conv1.weight[branch, feature, ky, kx] = .75
            model.conv2.weight[branch, branch, ky, kx] = .625
            model.conv3.weight[branch, branch, ky, kx] = .5
            model.head.weight[0, branch, 0, 0] = head
        model.head.bias[0] = .03125
    return model.eval()


def wrong_two_pixel_context(model, features, torch, tile):
    h, w = features.shape[-2:]
    rows = []
    for y in range(0, h, tile):
        columns = []
        for x in range(0, w, tile):
            ey, ex = min(h, y+tile), min(w, x+tile)
            y0, x0 = max(0, y-2), max(0, x-2)
            y1, x1 = min(h, ey+2), min(w, ex+2)
            p = model(features[..., y0:y1, x0:x1])
            columns.append(p[..., y-y0:ey-y0, x-x0:ex-x0])
        rows.append(torch.cat(columns, -1))
    return torch.cat(rows, -2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    need(out.is_relative_to(HERE) and not out.exists(), 'fresh owned output')
    out.mkdir()
    source = HERE / 'generic-consumer.py'
    spec = importlib.util.spec_from_file_location('independent_generic_subject', source)
    generic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generic)
    helper, scorer = generic.imports()
    np, torch = helper.runtime()
    need(sha(DATASET) == DATASET_SHA, 'old developer dataset changed')
    manifest = helper.manifest(DATASET)
    by_name = {path.parent.name: path for path in manifest['training']+manifest['heldout']}
    need(all(name in by_name for name in NAMES), 'fixed developer case missing')
    model = model_for_control(scorer, torch)
    records, bindings = [], []
    maximum_activity, image_activity = 0., 0.
    with torch.no_grad():
        for name in NAMES:
            loaded = helper.load_case(by_name[name], np, torch, truth=False, goldens=True)
            bindings.extend(loaded['bindings'])
            batch = helper.batched([loaded], torch)
            expected_features, _ = scorer.build_features(batch, helper, torch)
            expected_weights = [model(feature) for feature in expected_features]
            expected_cfa, expected_rgb, _ = helper.reconstruct(batch, expected_weights, torch)
            case = dict(path=loaded['path'], sha256=loaded['sha256'], meta=loaded['meta'], bands=3,
                        arrays={key: value.cpu() for key, value in loaded['arrays'].items()}, truth_read=False)
            statistics = generic.prepare_statistics(case, torch)
            feature_error = 0.
            for index in range(case['meta']['source_count']):
                coeff = [case['arrays'][f'coeff-{k}'][index:index+1].cuda() for k in range(3)]
                for k in range(3):
                    actual = generic.source_features(case, index, k, statistics, coeff, helper, scorer, torch)
                    feature_error = max(feature_error, delta(actual, expected_features[k][:,index:index+1], torch))
            rows = []
            for tile in (19, 31):
                actual = generic.render(case, torch, mode='model', model=model, statistics=statistics,
                                        keep_weights=True, tile=tile)
                we = max(delta(a.cuda()[None], b, torch) for a, b in zip(actual['weights'], expected_weights))
                ce = delta(actual['cfa'], expected_cfa, torch)
                re = delta(actual['rgb'], expected_rgb, torch)
                rows.append(dict(tile=tile, weights_max_abs=we, cfa_max_abs_dn=ce, rgb_max_abs=re))
                need(we <= 2e-5 and ce <= .02 and re <= 5e-6, 'nonzero streamed consumer parity failed')
                del actual
            need(feature_error <= 2e-4, 'sequential source statistics exceed fixed feature parity')
            activity = max(float((w-1).abs().max()) for w in expected_weights)
            source_activity = max(float((w-w.mean(1,keepdim=True)).abs().max()) for w in expected_weights)
            rgb_activity = delta(expected_rgb, batch['uniform-rgb'], torch)
            maximum_activity = max(maximum_activity, source_activity)
            image_activity = max(image_activity, rgb_activity)
            records.append(dict(case=loaded['path'], case_sha256=loaded['sha256'], source_count=case['meta']['source_count'],
                                maximum_feature_error=feature_error, nonzero_weight_delta=activity,
                                source_weight_variation=source_activity, uniform_rgb_delta=rgb_activity,
                                comparisons=rows, all_boundary_pixels_included=True, truth_read=False))
        need(maximum_activity > 1e-5 and image_activity > 1e-6, 'nonzero source choice/output never exercised')
        # A separate asymmetric odd grid ensures neither test tile divides either extent.
        yy = torch.arange(73, device='cuda', dtype=torch.float32)[None,:,None]
        xx = torch.arange(81, device='cuda', dtype=torch.float32)[None,None,:]
        cc = torch.arange(30, device='cuda', dtype=torch.float32)[:,None,None]
        value = (torch.sin(.37*xx+.19*yy+.11*cc)+.25*torch.cos(.13*xx-.23*yy+.29*cc))[None,None]
        expected = model(value)
        tile_rows = []
        for tile in (19,31):
            actual = generic.score_source(model, value, torch, tile=tile)
            error = delta(actual, expected, torch)
            mutant = wrong_two_pixel_context(model, value, torch, tile)
            damage = delta(mutant, expected, torch)
            need(error <= 2e-5, 'odd/asymmetric tiled CNN mismatch')
            need(damage > 1e-6, 'missing-context destroyer did not exercise the changed path')
            tile_rows.append(dict(tile=tile, correct_max_abs=error, missing_context_max_abs=damage,
                                  missing_context_rejected=True))
    need(all(sha(row['file']) == row['sha256'] for row in bindings), 'developer source tensor changed')
    result = dict(schema=1, status='INDEPENDENT_GENERIC_COMPLETE', passed=True,
                  dataset=str(DATASET), dataset_sha256=DATASET_SHA,
                  generic_sha256=sha(source), source_sha256=sha(__file__),
                  consumer_sha256=generic.OLD_SHA, scorer_sha256=generic.SCORER_SHA,
                  known_developer_cases_only=True, fresh_validation_read=False,
                  arbitrary_nonzero_model='four fixed asymmetric signed/parent/child/set-SD paths',
                  cases=records, odd_grid_shape=[73,81], tile_controls=tile_rows,
                  input_tensor_bindings=bindings, photographic_admission=False,
                  scope='Changed statistics, cross-scale features, CNN tiling and final consumer arithmetic; no quality judgment or noise calibration.')
    with (out/'independent-generic.json').open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
