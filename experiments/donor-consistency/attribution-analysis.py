"""Read-only, signed CFA reconstruction accounting; no photographic quality score."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
PLAN = HERE / 'attribution-analysis-plan.md'
PLANES = ['R', 'G1', 'G2', 'B']
AC = ('baseline-ac', 'retained-ac', 'donor-ac')
OTHER = ('base', 'baseline-pre-hull', 'baseline-post-hull',
         'baseline-hull-correction', 'pre-hull', 'post-hull', 'hull-correction')
REGIONS = {
    'facet-edges': dict(native=[2500, 2700, 384, 384],
                        points={'core': [2624, 2906], 'fan': [2602, 2945]},
                        reference=[2548, 2920]),
    'dark-inclusion': dict(native=[3050, 1850, 384, 384],
                          points={'core': [3080, 2150], 'fan': [3102, 2203],
                                  'structure': [3240, 2070]},
                          reference=[3180, 2220]),
}
SUM_LIMIT = 0.02
HULL_LIMIT = 0.003


def require(condition, message):
    if not condition:
        raise ValueError(message)


def binding(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), sha256=digest, bytes=path.stat().st_size)


def load_inputs(directory):
    path = directory / 'receipt.json'
    receipt = json.loads(path.read_text(encoding='utf-8'))
    require(receipt['schema'] == 1, 'Unknown receipt schema')
    require(receipt['plane_order'] == PLANES, 'CFA plane order changed')
    require(receipt['layout'] == 'planar-y-x-f32le', 'Layout changed')
    require(receipt['units'] == 'signed black-subtracted source DN', 'Units changed')
    require(receipt['native_dimensions'] == [6920, 4612], 'Full output geometry changed')
    sizes = receipt['level_sizes']
    expected_sizes = [[3460, 2306]]
    for _ in range(7):
        expected_sizes.append([(v + 1) // 2 for v in expected_sizes[-1]])
    require(sizes == expected_sizes, 'Expected seven AC bands and retained terminal base')
    windows = {item['name']: item for item in receipt['windows']}
    require(len(receipt['windows']) == 2 and set(windows) == set(REGIONS), 'Windows changed')
    for region, spec in REGIONS.items():
        require(windows[region]['native_xywh'] == spec['native'], f'{region} native crop changed')
        require(windows[region]['quad_xywh'] == [v // 2 for v in spec['native']],
                f'{region} quad crop phase changed')
    data, bindings = {}, []
    expected = {(r, f, k) for r in REGIONS for f in AC for k in range(7)}
    expected |= {(r, f, None) for r in REGIONS for f in OTHER}
    used_paths = set()
    require(len(receipt['arms']) == 2, 'Both arms required exactly once')
    for arm in receipt['arms']:
        name = arm['arm']
        require(name in ('candidate', 'late') and name not in data, 'Duplicate/unknown arm')
        require(arm['actual_delivered_windows_bit_exact'] is True, 'Writer did not bind delivered planes')
        fields = {}
        for artifact in arm['artifacts']:
            key = (artifact['region'], artifact['field'], artifact['level'])
            require(key in expected and key not in fields, f'Unexpected/duplicate field {name}/{key}')
            require(artifact['shape'] == [4, 192, 192], f'Shape differs: {key}')
            file = (directory / artifact['path']).resolve()
            require(file.is_relative_to(directory) and file not in used_paths, 'Invalid/shared artifact path')
            used_paths.add(file)
            bound = binding(file)
            require(bound['sha256'] == artifact['sha256'], f'Hash mismatch: {file}')
            require(bound['bytes'] == 4 * 192 * 192 * 4, f'Byte count differs: {file}')
            values = np.fromfile(file, dtype='<f4').reshape(4, 192, 192)
            require(np.isfinite(values).all(), f'Nonfinite field: {file}')
            fields[key] = values
            bindings.append(dict(arm=name, region=key[0], field=key[1], level=key[2], **bound))
        require(set(fields) == expected, f'Missing fields in {name}')
        data[name] = fields
    require(set(data) == {'candidate', 'late'}, 'Missing arm')
    return receipt, data, bindings


def ac_sum(fields, region, field):
    return np.sum([fields[(region, field, k)] for k in range(7)], axis=0, dtype=np.float64)


def verify(data):
    result = {}
    shared = {(r, f, k) for r in REGIONS for f in ('baseline-ac', 'retained-ac') for k in range(7)}
    shared |= {(r, f, None) for r in REGIONS for f in OTHER if f.startswith('baseline-') or f == 'base'}
    for key in shared:
        require(data['candidate'][key].tobytes() == data['late'][key].tobytes(),
                f'Candidate/late shared field not byte exact: {key}')
    for arm, fields in data.items():
        result[arm] = {}
        for region in REGIONS:
            get = lambda f: fields[(region, f, None)].astype(np.float64)
            base = get('base')
            pairs = {
                'baseline-sum': (ac_sum(fields, region, 'baseline-ac') + base, get('baseline-pre-hull'), SUM_LIMIT),
                'mixed-sum': (ac_sum(fields, region, 'retained-ac') + ac_sum(fields, region, 'donor-ac') + base,
                              get('pre-hull'), SUM_LIMIT),
                'baseline-hull': (get('baseline-pre-hull') + get('baseline-hull-correction'), get('baseline-post-hull'), HULL_LIMIT),
                'mixed-hull': (get('pre-hull') + get('hull-correction'), get('post-hull'), HULL_LIMIT),
            }
            result[arm][region] = {}
            for name, (summed, actual, limit) in pairs.items():
                error = np.max(np.abs(summed - actual), axis=(1, 2))
                require(np.max(error) <= limit, f'{arm}/{region}/{name} closure failed: {error}')
                result[arm][region][name] = dict(max_abs_dn_per_plane=error.tolist(), limit_dn=limit)
    return dict(shared_fields_bit_exact=len(shared), windows=result)


def mean_at(values, region, native_xy):
    crop = REGIONS[region]['native']
    x, y = native_xy[0] // 2 - crop[0] // 2, native_xy[1] // 2 - crop[1] // 2
    require(1 <= x < 191 and 1 <= y < 191, f'3x3 support outside window: {native_xy}')
    return np.mean(values[:, y - 1:y + 2, x - 1:x + 2], axis=(1, 2), dtype=np.float64)


def record_fields(fields, region, point):
    per_band = {field: [mean_at(fields[(region, field, k)], region, point).tolist()
                        for k in range(7)] for field in AC}
    sums = {field: np.sum(per_band[field], axis=0).tolist() for field in AC}
    ordinary = {field: mean_at(fields[(region, field, None)], region, point).tolist() for field in OTHER}
    ordinary['removed-baseline-ac'] = (np.array(sums['baseline-ac']) - sums['retained-ac']).tolist()
    return dict(per_band=per_band, ac_sums=sums, fields=ordinary)


def difference(point, reference):
    return {group: {key: (np.array(value) - reference[group][key]).tolist()
                    for key, value in values.items()} for group, values in point.items()}


def point_account(data):
    result = {}
    for region, spec in REGIONS.items():
        result[region] = dict(reference_native_xy=spec['reference'], arms={})
        for arm, fields in data.items():
            reference = record_fields(fields, region, spec['reference'])
            points = {}
            for label, xy in spec['points'].items():
                raw = record_fields(fields, region, xy)
                points[label] = dict(native_xy=xy, containing_quad_xy=[v // 2 for v in xy],
                                     raw_signed_mean_dn=raw, minus_reference_dn=difference(raw, reference))
            result[region]['arms'][arm] = dict(reference_raw_signed_mean_dn=reference, points=points)
    return result


def write_table(path, account, checks):
    lines = ['# Signed component accounting', '',
             'All reconstruction checks passed. CFA source DN, fixed 3x3-quad means; no photographic quality score.', '',
             f"Shared candidate/late fields byte exact: {checks['shared_fields_bit_exact']}.", '',
             'Tables show point minus the preselected local reference. Raw means and all seven bands are retained in accounting.json.',
             'A reference may contain scene structure; signed contributions can cancel. No ownership percentages are implied.', '']
    for region, record in account.items():
        for point in REGIONS[region]['points']:
            c = record['arms']['candidate']['points'][point]
            late = record['arms']['late']['points'][point]
            lines += [f"## {region}: {point} {c['native_xy']}", '',
                      f"Reference {record['reference_native_xy']}; containing quad {c['containing_quad_xy']}.", '',
                      '| Component | R | G1 | G2 | B |', '| --- | ---: | ---: | ---: | ---: |']
            terms = [('Baseline AC', c, 'ac_sums', 'baseline-ac'),
                     ('Retained baseline AC', c, 'ac_sums', 'retained-ac'),
                     ('Removed baseline AC (derived)', c, 'fields', 'removed-baseline-ac'),
                     ('Candidate donor AC', c, 'ac_sums', 'donor-ac'),
                     ('Late donor AC', late, 'ac_sums', 'donor-ac'),
                     ('Shared terminal base', c, 'fields', 'base'),
                     ('Baseline hull correction', c, 'fields', 'baseline-hull-correction'),
                     ('Candidate hull correction', c, 'fields', 'hull-correction'),
                     ('Late hull correction', late, 'fields', 'hull-correction'),
                     ('Baseline post-hull', c, 'fields', 'baseline-post-hull'),
                     ('Candidate post-hull', c, 'fields', 'post-hull'),
                     ('Late post-hull', late, 'fields', 'post-hull')]
            for label, item, group, field in terms:
                values = item['minus_reference_dn'][group][field]
                lines.append('| ' + label + ' | ' + ' | '.join(f'{v:.6f}' for v in values) + ' |')
            lines += ['']
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def draw_maps(output, data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    paths = []
    for region, spec in REGIONS.items():
        c, late = data['candidate'], data['late']
        maps = [ac_sum(c, region, 'baseline-ac'), ac_sum(c, region, 'retained-ac'),
                ac_sum(c, region, 'donor-ac'), ac_sum(late, region, 'donor-ac'),
                c[(region, 'hull-correction', None)], late[(region, 'hull-correction', None)]]
        names = ['Baseline AC sum', 'Retained AC sum', 'Candidate donor AC', 'Late donor AC', 'Candidate hull', 'Late hull']
        for limit in (64, 512):
            fig, axes = plt.subplots(4, 6, figsize=(15, 10), layout='constrained')
            for row, plane in enumerate(PLANES):
                for col, (name, values) in enumerate(zip(names, maps)):
                    ax = axes[row, col]
                    im = ax.imshow(values[row], cmap='RdBu_r', vmin=-limit, vmax=limit,
                                   interpolation='nearest', origin='upper')
                    ax.set_xticks([]); ax.set_yticks([])
                    if col == 0:
                        ax.set_ylabel(plane)
                    if row == 0:
                        ax.set_title(name, fontsize=10)
                        for label, xy in {**spec['points'], 'ref': spec['reference']}.items():
                            x, y = xy[0] // 2 - spec['native'][0] // 2, xy[1] // 2 - spec['native'][1] // 2
                            ax.plot(x, y, 'o', ms=3, mfc='none', mec='black')
                            ax.annotate(label, (x, y), xytext=(3, -3), textcoords='offset points', fontsize=7,
                                        color='black', bbox=dict(facecolor='white', edgecolor='none', alpha=.7, pad=.3))
            fig.colorbar(im, ax=axes, shrink=.8, label='Signed black-subtracted source DN')
            fig.suptitle(f'{region}: fixed signed range +/-{limit} DN; full-context expansion, no MHC/WB/tone\n'
                         'Saturated display colours do not truncate numeric data; contributions are not ownership probabilities', fontsize=11)
            path = output / f'{region}-signed-{limit}dn.png'
            fig.savefig(path, dpi=140)
            plt.close(fig)
            paths.append(path)
    return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.input.resolve(), args.output.resolve()
    require(source.is_relative_to(HERE) and output.is_relative_to(HERE), 'Paths must stay within donor-consistency experiment')
    require(not output.exists() and not output.is_relative_to(source), 'Output must be new and separate from observer data')
    receipt, data, artifacts = load_inputs(source)
    checks = verify(data)
    account = point_account(data)
    output.mkdir(parents=True)
    result = dict(scope='Signed CFA accounting only; no photographic quality or source-ownership score',
                  command=sys.argv, analyzer=binding(Path(__file__).resolve()), plan=binding(PLAN),
                  observer_receipt=binding(source / 'receipt.json'), artifacts=artifacts,
                  plane_order=PLANES, native_dimensions=receipt['native_dimensions'],
                  level_sizes=receipt['level_sizes'], reconstruction_checks=checks,
                  observer_full_domain_summaries={arm['arm']: arm['summary'] for arm in receipt['arms']},
                  point_accounts=account)
    (output / 'accounting.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_table(output / 'accounting.md', account, checks)
    maps = draw_maps(output, data)
    generated = [output / 'accounting.json', output / 'accounting.md', *maps]
    manifest = dict(analyzer=result['analyzer'], plan=result['plan'], observer_receipt=result['observer_receipt'],
                    outputs=[binding(p) for p in generated])
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(output), checks=checks, diagnostic_maps=len(maps))))


if __name__ == '__main__':
    main()
