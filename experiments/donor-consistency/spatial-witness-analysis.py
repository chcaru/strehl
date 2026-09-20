"""Read completed immutable spatial witnesses; no RAW or quality metric."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import tifffile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
WINDOWS = {'facet-edges': [2500, 2700, 384, 384], 'dark-inclusion': [3050, 1850, 384, 384]}
POINTS = {'facet-edges': [('core', 2624, 2906, 28), ('fan', 2602, 2945, 28), ('rim', 2760, 2998, 28)],
          'dark-inclusion': [('core', 3080, 2150, 33), ('fan', 3102, 2203, 33),
                             ('structure', 3240, 2070, 25), ('tail-post-failure', 3080, 2212, 33)]}
SOURCE_IDS = [25, 28, 33, 69]
FIELDS = ['baseline-ac', 'baseline-base', 'baseline-pre', 'baseline-post', 'baseline-hull',
          'lo', 'hi', 'coverage', 'mask-0', 'mask-1', 'mask-2', 'donor-sum', 'retained-ac',
          'pre-hull', 'post-hull', 'hull-correction']


def ref(path):
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': digest}


def json_write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def rgb8(value):
    assert value.dtype == np.uint16 and value.shape[-1] == 3
    return ((value.astype(np.uint32) + 128) // 257).astype(np.uint8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--witness', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.witness.resolve(), args.out.resolve()
    assert root.is_dir() and not out.exists()
    out.relative_to(HERE.parents[1] / 'experiments')
    receipt_path = root / 'receipt.json'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['schema'] == 1 and receipt['layout'] == 'planar-y-x-f32le'
    assert receipt['plane_order'] == ['R', 'G1', 'G2', 'B'] and receipt['native_dimensions'] == [6920, 4612]
    assert {w['name']: w['native_xywh'] for w in receipt['windows']} == WINDOWS
    groups = {g['group']: g for g in receipt['groups']}
    assert set(groups) == {'candidate', 'late', *(f'source-{i}' for i in SOURCE_IDS)}
    arrays, bindings, photos, profile = {}, [ref(receipt_path)], {}, None
    for group, info in groups.items():
        for row in info['artifacts']:
            path = (root / row['path']).resolve()
            path.relative_to(root)
            binding = ref(path)
            assert binding['sha256'] == row['sha256']
            shape = tuple(row['shape'])
            expected = (4, 196, 196) if row['field'] == 'source-known4-pad4' else (4, 192, 192)
            assert shape == expected and binding['bytes'] == int(np.prod(shape)) * 4
            values = np.fromfile(path, dtype='<f4').reshape(shape)
            assert np.isfinite(values).all()
            key = (group, row['region'], row['field'])
            assert key not in arrays
            arrays[key] = values
            bindings.append(binding)
        for row in info.get('developed', []):
            path = (root / row['path']).resolve()
            path.relative_to(root)
            binding = ref(path)
            assert binding['sha256'] == row['sha256'] and row['display_crop_xywh'] == [4, 4, 384, 384]
            with tifffile.TiffFile(path) as tf:
                image = tf.asarray()
                assert image.shape == (392, 392, 3) and image.dtype == np.uint16
                icc = tf.pages[0].tags[34675].value
            if profile is None:
                profile = icc
            assert icc == profile
            photos[group, row['region']] = rgb8(image[4:-4, 4:-4])
            bindings.append(binding)
    output = Path(receipt['source_output'])
    output_receipt_path = output / 'receipt.json'
    output_receipt = json.loads(output_receipt_path.read_text())
    bindings.append(ref(output_receipt_path))
    for arm in ['baseline', 'candidate', 'late']:
        path = output / f'{arm}.tiff'
        binding = ref(path)
        assert binding['sha256'] == output_receipt[f'{arm}_sha256']
        with tifffile.TiffFile(path) as tf:
            image = tf.asarray()
            assert image.shape == (4612, 6920, 3) and image.dtype == np.uint16
            assert tf.pages[0].tags[34675].value == profile
        for region, (x, y, w, h) in WINDOWS.items():
            photos[arm, region] = rgb8(image[y:y+h, x:x+w])
        del image
        bindings.append(binding)

    checks, points = {}, {}
    def field(group, region, name):
        return arrays[group, region, name]
    def identity(name, value):
        maximum = float(np.max(np.abs(value)))
        assert maximum <= .02, (name, maximum)
        checks[name] = maximum
    for region in WINDOWS:
        f = lambda group, name: field(group, region, name)
        for source in SOURCE_IDS:
            group = f'source-{source}'
            known, ac, base = (f(group, n) for n in ['source-known4', 'source-ac', 'source-base'])
            assert np.array_equal(known.view(np.uint32), f(group, 'source-known4-pad4')[:, 2:-2, 2:-2].view(np.uint32))
            identity(f'{region}/{group}/source', known.astype('f8') - ac - base)
        for name in FIELDS[:11]:
            assert np.array_equal(f('candidate', name).view(np.uint32), f('late', name).view(np.uint32))
        for arm in ['candidate', 'late']:
            for name in ['coverage', 'mask-0', 'mask-1', 'mask-2']:
                a = f(arm, name)
                assert np.all((a >= 0) & (a <= 1)) and all(np.array_equal(a[0], a[c]) for c in [1, 2, 3])
            a = np.zeros((4, 192, 192), dtype='f4')
            order = [(2, 25), (0, 28), (1, 33)] if arm == 'candidate' else [(0, 69), (1, 69), (2, 69)]
            for r, source in order:
                a += f(arm, f'mask-{r}') * f(f'source-{source}', 'source-ac')
            identity(f'{region}/{arm}/donor-sum', a.astype('f8') - f(arm, 'donor-sum'))
            bpre, bac, bbase = (f(arm, n) for n in ['baseline-pre', 'baseline-ac', 'baseline-base'])
            pre, post, hull = (f(arm, n) for n in ['pre-hull', 'post-hull', 'hull-correction'])
            identity(f'{region}/{arm}/baseline', bpre.astype('f8') - bac - bbase)
            identity(f'{region}/{arm}/retained', (1-f(arm, 'coverage')).astype('f8') * bac - f(arm, 'retained-ac'))
            identity(f'{region}/{arm}/spatial', pre.astype('f8') - f(arm, 'retained-ac') - a - bbase)
            identity(f'{region}/{arm}/hull', post.astype('f8') - pre - hull)
            assert np.array_equal(np.clip(pre, f(arm, 'lo'), f(arm, 'hi')).view(np.uint32), post.view(np.uint32))
        x0, y0, _, _ = WINDOWS[region]
        region_points = []
        for label, x, y, chosen in POINTS[region]:
            qx, qy = (x-x0)//2, (y-y0)//2
            patch = np.s_[:, qy-1:qy+2, qx-1:qx+2]
            def means(a):
                p = a[patch]
                assert p.shape == (4, 3, 3)
                return p.mean(axis=(1, 2), dtype='f8').tolist()
            row = {'label': label, 'native_xy': [x, y], 'quad_xy': [x//2, y//2],
                   'post_failure_location': label == 'tail-post-failure', 'chosen_source': chosen,
                   'coverage_center': f('candidate', 'coverage')[:, qy, qx].tolist(),
                   'coverage_3x3_minmax': [float(f('candidate', 'coverage')[patch].min()), float(f('candidate', 'coverage')[patch].max())],
                   'source_3x3_means': {}, 'arm_3x3_means': {}, 'shared_minus_source_base_3x3_means': {}}
            for source in SOURCE_IDS:
                row['source_3x3_means'][str(source)] = {n: means(f(f'source-{source}', n)) for n in ['source-known4', 'source-ac', 'source-base']}
                row['shared_minus_source_base_3x3_means'][str(source)] = means(f('candidate', 'baseline-base').astype('f8') - f(f'source-{source}', 'source-base'))
            for arm in ['candidate', 'late']:
                row['arm_3x3_means'][arm] = {n: means(f(arm, n)) for n in FIELDS}
            region_points.append(row)
        points[region] = region_points

    out.mkdir()
    output_files = []
    def mark(ax, region):
        for label, x, y, _ in POINTS[region]:
            post = label == 'tail-post-failure'
            ax.plot(x, y, marker='x' if post else '+', color='red' if post else 'yellow', markersize=6)
            ax.annotate('post-failure' if post else label, (x, y), xytext=(4, -9 if post else 4),
                        textcoords='offset points', fontsize=7, color='red' if post else 'yellow')
        ax.set_xlabel('Output-native x'); ax.set_ylabel('Output-native y')
    def save(fig, name):
        path = out / name
        fig.savefig(path, dpi=120, pil_kwargs={'icc_profile': profile})
        plt.close(fig)
        output_files.append(ref(path))
    for region, (x, y, w, h) in WINDOWS.items():
        extent = [x-.5, x+w-.5, y+h-.5, y-.5]
        chosen = 28 if region == 'facet-edges' else 33
        fig, axes = plt.subplots(2, 3, figsize=(12, 9), constrained_layout=True)
        arms = ['baseline', 'candidate', f'source-{chosen}', 'late', 'source-69', 'source-25']
        for ax, arm in zip(axes.flat, arms):
            ax.imshow(photos[arm, region], extent=extent, interpolation='nearest')
            ax.set_title(arm + (' actual gathered donor' if arm.startswith('source') else ' actual output'))
            mark(ax, region)
        fig.suptitle(region + ' | held development; native pixels; red point selected after failure')
        save(fig, f'{region}-photographs.png')
        green = lambda a: (a[1].astype('f8') + a[2]) * .5
        f = lambda group, name: field(group, region, name)
        panels = [('Actual coverage [0,1]', f('candidate', 'coverage')[0], True),
                  ('Baseline AC', green(f('candidate', 'baseline-ac')), False),
                  (f'Actual source{chosen} AC', green(f(f'source-{chosen}', 'source-ac')), False),
                  ('Shared base minus source base', green(f('candidate', 'baseline-base').astype('f8') - f(f'source-{chosen}', 'source-base')), False),
                  ('Retained baseline AC', green(f('candidate', 'retained-ac')), False),
                  ('Masked donor AC sum', green(f('candidate', 'donor-sum')), False),
                  ('Candidate hull correction', green(f('candidate', 'hull-correction')), False),
                  ('Candidate minus baseline post-hull', green(f('candidate', 'post-hull').astype('f8') - f('candidate', 'baseline-post')), False),
                  (f'Actual source{chosen} known4 green', green(f(f'source-{chosen}', 'source-known4')), False)]
        for span in [64, 512]:
            fig, axes = plt.subplots(3, 3, figsize=(13, 12), constrained_layout=True)
            for ax, (title, values, mask) in zip(axes.flat, panels):
                im = ax.imshow(values, extent=extent, interpolation='nearest', cmap='viridis' if mask else 'RdBu_r',
                               vmin=0 if mask else -span, vmax=1 if mask else span)
                ax.set_title(title, fontsize=10); mark(ax, region)
                fig.colorbar(im, ax=ax, shrink=.7, label='Coverage' if mask else 'Source DN')
            fig.suptitle(f'{region} | actual full-context fields; G1/G2 mean | signed display clips at +/-{span}DN\nRed point is post-failure; scalar views are quad samples, not ownership or photographs')
            save(fig, f'{region}-fields-{span}dn.png')
    report = {'scope': 'Immutable actual source/spatial accounting; no quality or ownership score',
              'checks_max_abs_dn': checks, 'point_statistic': 'Raw signed 3x3-quad means; exact centre/range coverage also retained',
              'points': points}
    json_write(out / 'accounting.json', report)
    lines = ['# Actual source and spatial accounting', '', 'Signed source DN; no quality score or ownership percentages.',
             'Post-failure tail location is explicitly labelled; it does not license mask tuning.', '']
    for region, rows in points.items():
        lines.extend([f'## {region}', '', '| Point | Native xy | Coverage centre / 3x3 range | Shared-source base G1 | Retained AC G1 | Donor sum G1 | Hull G1 |',
                      '| --- | --- | --- | ---: | ---: | ---: | ---: |'])
        for row in rows:
            f = row['arm_3x3_means']['candidate']
            b = row['shared_minus_source_base_3x3_means'][str(row['chosen_source'])][1]
            lines.append(f"| {row['label']} | {row['native_xy']} | {row['coverage_center'][0]:.6f} / {row['coverage_3x3_minmax']} | {b:.3f} | {f['retained-ac'][1]:.3f} | {f['donor-sum'][1]:.3f} | {f['hull-correction'][1]:.3f} |")
        lines.append('')
    (out / 'accounting.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    output_files += [ref(out / 'accounting.json'), ref(out / 'accounting.md')]
    json_write(out / 'manifest.json', {'analyzer': ref(Path(__file__)), 'plan': ref(HERE / 'spatial-witness-analysis-plan.md'),
                                     'inputs': bindings, 'outputs': output_files})
    print(json.dumps({'output': str(out), 'checks': checks, 'plots': len(output_files)-2}, indent=2))


if __name__ == '__main__':
    main()
