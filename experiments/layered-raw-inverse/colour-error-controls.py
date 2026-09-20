"""Independent orthogonal error-attribution checks; no image fitting/ranking."""
from pathlib import Path
import argparse
import importlib.util
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('colour_error_helpers', HERE / 'visibility-oracle-controls.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)
sha, read = common.sha, common.read
PHASES = [[0, 0], [1, 0], [0, 1], [1, 1]]
ARMS = {'visibility': 'visibility-1', 'shot': 'shot-prior-1', 'cauchy': 'cauchy-1'}


def projection(error, size, phase):
    """Coordinate-group enumeration, independent of reshape/pooling/roll."""
    height, width, _ = error.shape
    out = np.empty_like(error, dtype=np.float64)
    for by in range(0, height, size):
        yy = (by + np.arange(size) + phase[1]) % height
        for bx in range(0, width, size):
            xx = (bx + np.arange(size) + phase[0]) % width
            out[yy[:, None], xx[None, :]] = error[yy[:, None], xx[None, :]].mean((0, 1))
    return out


def oracle(error, phase):
    two, four = projection(error, 2, phase), projection(error, 4, phase)
    mean = error.mean((0, 1))
    terms = {'within2_mean_square': error-two, 'between2_4_mean_square': two-four,
             'common4_mean_square': four, 'common4_ac_mean_square': four-mean}
    return {**{name: (value*value).mean((0, 1)) for name, value in terms.items()}, 'dc_mean_square': mean*mean}


def check(error, report):
    total, mean = (error*error).mean((0, 1)), error.mean((0, 1))
    assert np.allclose(report['total_mean_square'], total, rtol=2e-12, atol=1e-10)
    assert np.allclose(report['signed_mean'], mean, rtol=2e-12, atol=1e-10)
    assert abs(report['chroma_rmse']-float(np.sqrt(total.mean()))) <= 1e-10+2e-12*float(np.sqrt(total.mean()))
    assert [p['origin_xy'] for p in report['phases']] == PHASES
    for record in report['phases']:
        expected = oracle(error, record['origin_xy'])
        for name, values in expected.items():
            assert np.allclose(record[name], values, rtol=2e-12, atol=1e-10), name
        summed = sum(np.array(record[name]) for name in ['within2_mean_square', 'between2_4_mean_square', 'common4_mean_square'])
        assert np.allclose(summed, total, rtol=2e-12, atol=1e-10)
        assert np.allclose(np.array(record['common4_ac_mean_square'])+record['dc_mean_square'], record['common4_mean_square'], rtol=2e-12, atol=1e-10)


def commission(author):
    y, x = np.mgrid[:64, :64]
    constant = np.broadcast_to([-7., 13.], (64, 64, 2)).copy()
    checker = ((-1.)**(x+y))[..., None]*[5., -9.]
    blocks = ((-1.)**(x//4+y//4))[..., None]*[4., -6.]
    sine = np.stack([.25*np.sin(2*np.pi*x/64)+.125*np.cos(2*np.pi*y/64), .15*np.cos(2*np.pi*(x+2*y)/64)], -1)
    rows = []
    for name, error in [('constant', constant), ('bayer-checker', checker), ('aligned-four-blocks', blocks), ('weak-sine', sine)]:
        original = error.copy()
        report = author.decompose(error)
        check(error, report)
        assert np.array_equal(error, original)
        row = report['phases'][0]
        if name == 'constant':
            assert np.array_equal(report['signed_mean'], [-7., 13.])
            assert np.allclose(row['dc_mean_square'], [49., 169.]) and np.max(row['common4_ac_mean_square']) < 1e-20
        elif name == 'bayer-checker':
            assert np.allclose(row['within2_mean_square'], [25., 81.]) and np.max(row['common4_mean_square']) < 1e-20
        elif name == 'aligned-four-blocks':
            assert np.allclose(row['common4_ac_mean_square'], [16., 36.]) and np.max(row['within2_mean_square']) < 1e-20
            assert np.max(row['between2_4_mean_square']) < 1e-20
            assert any(np.max(p['within2_mean_square']) > 0 for p in report['phases'][1:])
        else:
            assert all(np.min(row[k]) > 1e-8 for k in ['within2_mean_square', 'between2_4_mean_square', 'common4_ac_mean_square'])
        rows.append(dict(name=name, decomposition=report))
    two, four = projection(sine, 2, [0, 0]), projection(sine, 4, [0, 0])
    wrong = ((sine-four)**2).mean((0, 1))+((two-four)**2).mean((0, 1))+(four*four).mean((0, 1))
    excess = wrong-(sine*sine).mean((0, 1))
    assert np.min(excess) > 1e-6  # Overlapping residuals double-count middle-scale energy.
    return dict(status='PASS', passed=True, cases=rows, wrong_nonorthogonal_excess=excess.tolist(),
                scope='Projection arithmetic and phase convention; not optical information or quality evidence')


def score(source, candidate):
    result = read(candidate / 'result.json')
    assert result['support_native_xywh'] == [16, 16, 64, 64]
    before, after = result['source_bindings_before'], result['source_bindings_after']
    assert before == after and all(sha(path) == digest for path, digest in before.items())
    assert sorted((r['case'], r['arm']) for r in result['records']) == sorted((case, arm) for case in ['flat', 'layered'] for arm in ARMS)
    rows, score_bindings = [], {}
    for record in result['records']:
        case, arm = record['case'], record['arm']
        path = HERE / ARMS[arm] / 'output' / case / 'fixed-alpha' / 'reconstruction.npz'
        truth_path = source / case / 'truth-rgb-f32.npy'
        assert Path(record['source_path']).resolve() == path.resolve() and sha(path) == record['source_sha256']
        assert Path(record['truth_path']).resolve() == truth_path.resolve() and sha(truth_path) == record['truth_sha256']
        with np.load(path, allow_pickle=False) as fields:
            image = fields['pinhole_rgb'].copy()
        truth = np.load(truth_path, allow_pickle=False)
        delta = image[16:80, 16:80].astype(np.float64)-truth[16:80, 16:80].astype(np.float64)
        error = np.stack([delta[..., 0]-delta[..., 1], delta[..., 2]-delta[..., 1]], -1)
        check(error, record['decomposition'])
        scores_path = HERE / ARMS[arm] / 'scored' / 'result.json'
        score_bindings[str(scores_path)] = sha(scores_path)
        old = next(r for r in read(scores_path)['cases'] if r['name'] == case)
        frozen_chroma = old['quality']['regions']['whole']['candidate']['chroma_rmse']
        assert np.isclose(record['decomposition']['chroma_rmse'], frozen_chroma, rtol=2e-12, atol=1e-10)
        rows.append(dict(case=case, arm=arm, frozen_chroma_rmse=frozen_chroma, decomposition=record['decomposition']))
    assert all(sha(path) == digest for path, digest in before.items())
    assert all(sha(path) == digest for path, digest in score_bindings.items())
    return dict(status='COLOUR_ERROR_ATTRIBUTION_CHECKED', passed=True, records=rows, source_unchanged=True,
                scalar_score_bindings=score_bindings, diagnostic_sha256=sha(candidate / 'result.json'),
                scope='Same pixels and total colour error at all phases. Scale attribution only; no optical null-mode or quality-rank conclusion.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['commission', 'score'])
    parser.add_argument('--source', type=Path, default=HERE / 'screen-1' / 'output')
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    assert not out.exists()
    control = common.frozen(source)
    if args.mode == 'commission':
        author = common.load(HERE / 'colour-error-decomposition.py', 'commissioned_colour_error')
        result = commission(author)
    else:
        assert args.candidate is not None
        result = score(source, args.candidate.resolve())
    result['controls_sha256'] = sha(__file__)
    out.mkdir(parents=True)
    control.save(out / 'result.json', result)
    print('COLOUR_ERROR_' + args.mode.upper(), result['status'], flush=True)


if __name__ == '__main__':
    main()
