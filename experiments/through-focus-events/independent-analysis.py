"""Frozen signed trace descriptions; no election, optical label, p-value or image score."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
SHIFTS = ((0, 0), (1, 0))
PERMUTATION = (17 * np.arange(70) + 11) % 70
FEATURES = ('mean_dn', 'mean_l0', 'mean_energy', 'mean_guide', 'mean_guide_variance')
RECTS = {
    'facet-core': (1304,1448,16,10), 'facet-extension': (1296,1468,12,12),
    'facet-adjacent': (1324,1468,20,20), 'dark-core': (1532,1070,16,10),
    'dark-column': (1534,1101,12,12), 'dark-fan': (1545,1096,12,12),
    'dark-structure': (1612,1028,16,16), 'nearby-core': (1612,1030,16,10),
    'dark-continuation': (1612,1042,16,16), 'pale-background': (288,663,16,16),
}
for _name in ('facet-extension', 'dark-column', 'dark-fan', 'dark-continuation'):
    _x, _y, _w, _h = RECTS[_name]
    RECTS[_name+'-minus64'] = (_x-64, _y, _w, _h)
    RECTS[_name+'-plus64'] = (_x+64, _y, _w, _h)
# Names are bound to the author's fixed geometry registry before any actual read.
PAIRS = (
    ('facet-extension', 'facet-core', 'facet-extension'),
    ('facet-adjacent', 'facet-core', 'facet-adjacent'),
    ('dark-column', 'dark-core', 'dark-column'),
    ('dark-fan', 'dark-core', 'dark-fan'),
    ('dark-structure', 'dark-core', 'dark-structure'),
    ('nearby-continuation', 'nearby-core', 'dark-continuation'),
    ('nearby-column', 'nearby-core', 'dark-column'),
)


def binding(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def describe(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    assert a.shape == b.shape == (70, 4) and np.isfinite(a).all() and np.isfinite(b).all()
    da, db = np.diff(a, axis=0), np.diff(b, axis=0)
    aa, bb = (da * da).sum(axis=0), (db * db).sum(axis=0)
    dot = (da * db).sum(axis=0)
    cosine = [float(x / np.sqrt(y * z)) if y > 0 and z > 0 else None
              for x, y, z in zip(dot, aa, bb)]
    joint = float(dot.sum() / np.sqrt(aa.sum() * bb.sum())) if aa.sum() > 0 and bb.sum() > 0 else None
    return dict(dot_dn2=dot.tolist(), cosine=cosine, joint_dot_dn2=float(dot.sum()),
                joint_cosine=joint, source_rms_change_dn=np.sqrt(aa / 69).tolist(),
                target_rms_change_dn=np.sqrt(bb / 69).tolist(),
                interpretation='uncentred signed adjacent-change association; not ownership or noise significance')


def arithmetic_controls():
    # A step commissions event alignment; it is deliberately not an optical focus curve.
    a = np.zeros((70, 4)); a[11:] = [1, 2, 3, 4]
    same, opposite = describe(a, 3*a), describe(a, -2*a)
    assert same['joint_cosine'] == 1.0 and opposite['joint_cosine'] == -1.0
    assert np.allclose(same['dot_dn2'], 3*np.array([1, 4, 9, 16]), rtol=0, atol=0)
    c = np.zeros_like(a); c[31:] = [1, 2, 3, 4]
    assert describe(a, c)['joint_cosine'] == 0.0
    assert describe(a, np.ones_like(a))['joint_cosine'] is None
    assert describe(a[::-1], (3*a)[::-1]) == same
    assert describe(a+113, 3*a-59) == same
    permuted = describe(a, a[PERMUTATION]); reversed_one = describe(a, a[::-1])
    assert abs(permuted['joint_cosine']) < .5 and reversed_one['joint_cosine'] == 0.0
    signed = a[:, :1] * np.array([[1, -1, 1, -1]])
    positive = a[:, :1] * np.ones((1, 4))
    cancellation = describe(signed, positive)
    assert cancellation['joint_cosine'] == 0 and cancellation['cosine'] == [1, -1, 1, -1]
    return dict(status='ARITHMETIC_ONLY', positive_and_negative_live=True,
                independent_event_orthogonal=True, constant_undefined=True,
                common_reversal_exact=True, offset_invariant=True,
                fixed_permutation_destroyer=permuted, one_sided_reversal_destroyer=reversed_one,
                signed_colour_cancellation=cancellation, optical_validation=False)


def plots(traces, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups = {'facet': ('facet-core', 'facet-extension', 'facet-adjacent'),
              'dark': ('dark-core', 'dark-column', 'dark-fan', 'dark-structure'),
              'nearby': ('nearby-core', 'dark-continuation', 'dark-column', 'pale-background')}
    for group, names in groups.items():
        fig, axes = plt.subplots(4, 2, figsize=(12, 10), sharex=True, constrained_layout=True)
        for c, channel in enumerate(('R', 'G1', 'G2', 'B')):
            for col, field in enumerate(('mean_dn', 'mean_l0')):
                for name in names:
                    axes[c, col].plot(np.arange(70), traces[(name, (0, 0), field)][:, c], label=name, linewidth=1)
                axes[c, col].set_ylabel(f'{channel}: signed mean DN')
                axes[c, col].set_title(field)
                axes[c, col].grid(alpha=.2)
        for ax in axes[-1]: ax.set_xlabel('Original source index (0..69)')
        axes[0, 0].legend(fontsize=8)
        fig.suptitle(f'{group}: descriptive RAW-consumer traces; clipping limits apply; no ownership claim')
        fig.savefig(out / f'{group}-signed-traces.png', dpi=140); plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True, constrained_layout=True)
    for ax, (group, names) in zip(axes, groups.items()):
        for name in names:
            values = traces[(name, (0, 0), 'mean_energy')].mean(axis=1)
            ax.plot(np.arange(70), values, label=name, linewidth=1)
        ax.set_title(group); ax.set_ylabel('Mean four-CFA smooth5(L0²), DN²'); ax.legend(fontsize=8); ax.grid(alpha=.2)
    axes[-1].set_xlabel('Original source index (0..69)')
    fig.suptitle('Unsigned energy context only: neither signed coupling nor a source-selection score')
    fig.savefig(out / 'energy-context.png', dpi=140); plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--receipt', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--controls-only', action='store_true')
    args = p.parse_args(); out = args.out.resolve()
    assert out.is_relative_to(HERE) and not out.exists(); out.mkdir()
    controls = arithmetic_controls()
    if args.controls_only:
        (out/'result.json').write_text(json.dumps(controls, indent=2, allow_nan=False)+'\n')
        return
    assert args.receipt is not None
    record = json.loads(args.receipt.read_text())
    assert record['schema'] == 1 and record['plane_order'] == ['R', 'G1', 'G2', 'B']
    assert record['crop_quad_xywh'] == [28,19,3460,2306]
    assert record['parity_origin_quad_xy'] == [28,19] and record['original_metadata_unchanged']
    headroom = record['original_headroom']
    assert binding(headroom['path'])['sha256'] == headroom['sha256']
    sources = record['sources']
    assert [s['source_index0'] for s in sources] == list(range(70))
    registry = {}
    traces = {}
    for index, source in enumerate(sources):
        assert source['measurement_fields_unchanged']
        assert source['old_wide_bit_exact'] == (index in (25,28,33,69))
        assert len(source['rows']) == 36
        seen = set()
        for row in source['rows']:
            key = (row['roi_name'], tuple(row['shift_quad_xy']))
            assert key not in seen and key[1] in SHIFTS; seen.add(key)
            geometry = tuple(row['output_quad_xywh'])
            assert len(geometry) == 4 and all(isinstance(v, int) for v in geometry)
            x, y, w, h = RECTS[key[0]]
            assert geometry == (x+key[1][0], y+key[1][1], w, h)
            if index == 0: registry[key] = geometry
            else: assert registry[key] == geometry
            planes = row['planes']; assert len(planes) == 4
            assert all(v['count'] == geometry[2]*geometry[3] and sum(v['checker_count']) == v['count']
                       and min(v['checker_count']) > 0 for v in planes)
            for field in FEATURES + ('checker_mean_dn', 'checker_mean_l0'):
                values = np.array([v[field] for v in planes], dtype=np.float64)
                assert np.isfinite(values).all()
                traces.setdefault((*key, field), []).append(values)
        assert seen == set(registry)
    traces = {k: np.asarray(v) for k, v in traces.items()}
    result = dict(schema=1, status='COMPLETE_DESCRIPTIVE_ONLY', controls=controls,
                  bindings=[binding(args.receipt), binding(__file__), binding(HERE/'independent-plan.md'), binding(headroom['path'])],
                  frame_permutation=PERMUTATION.tolist(), cases=[], ownership_claim=False,
                  noise_calibration=False, image_quality_claim=False, selector_admission=False,
                  limits='Actual original clipping flags and source binding reside in export receipt; no Gaussian or conserved-flux inference.')
    for label, source_name, target_name in PAIRS:
        for shift in SHIFTS:
            for field in ('mean_dn', 'mean_l0'):
                for subset in (None, 0, 1):
                    f = field if subset is None else 'checker_'+field
                    def take(name):
                        data = traces[(name, shift, f)]
                        return data if subset is None else data[:, :, subset]
                    a, b = take(source_name), take(target_name)
                    actual = describe(a, b)
                    reverse = describe(a[::-1], b[::-1])
                    for key in ('dot_dn2', 'source_rms_change_dn', 'target_rms_change_dn'):
                        assert np.allclose(actual[key], reverse[key], rtol=1e-12, atol=1e-10)
                    item = dict(relation=label, shift_quad_xy=shift, field=field, checker_subset=subset,
                                actual=actual, common_reversal=reverse,
                                target_reversal=describe(a, b[::-1]), target_permutation=describe(a, b[PERMUTATION]),
                                background=describe(a, take('pale-background')), spatial_nulls={})
                    for suffix in ('-minus64', '-plus64'):
                        name = target_name + suffix
                        if (name, shift, f) in traces: item['spatial_nulls'][suffix] = describe(a, take(name))
                    result['cases'].append(item)
    archive = {f'{name}__{shift[0]}_{shift[1]}__{field}': values for (name, shift, field), values in traces.items()}
    np.savez_compressed(out/'traces.npz', **archive)
    plots(traces, out)
    result['traces'] = binding(out/'traces.npz')
    (out/'result.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'], relations=len(PAIRS), cases=len(result['cases']),
                          original_sources=70, selector_admission=False)), flush=True)


if __name__ == '__main__':
    main()
