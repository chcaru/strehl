"""Independent generated-only controls; root executes, author does not self-verify."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import struct
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('tested_concentration', HERE / 'locator.py')
LOC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOC)
W, H, N = 336, 288, 31
Y, X = np.indices((H, W), dtype=np.float64)
GLINT = (144., 144.)
THIN = (194., 144.)
FIELD = [64, 64, W - 128, H - 128]
BITS = [struct.pack('>d', value).hex() for value in (1., 0., 0., 0.)]


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def bind(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def gaussian(cx, cy, sx, sy, angle=0.):
    u = (X - cx) * math.cos(angle) + (Y - cy) * math.sin(angle)
    v = -(X - cx) * math.sin(angle) + (Y - cy) * math.cos(angle)
    return np.exp(-.5 * ((u / sx) ** 2 + (v / sy) ** 2))


def blank():
    return np.full((H, W, 3), .18, dtype=np.float64)


def compact(index, fan=False):
    rgb = blank()
    sigma = 2. * (1. + .065 * abs(index - 10))
    light = .35 * (2. / sigma) ** 2 * gaussian(*GLINT, sigma, sigma)
    rgb += light[:, :, None] * np.array([1., .8, .65])
    if fan:
        strength = max(0., min(1., (index - 15) / 5.))
        ray = .12 * strength * gaussian(166., 144., 15., 1.3)
        rgb += ray[:, :, None] * np.array([.5, .8, 1.])
    return rgb


def thin_light(index, focus, centre, angle=0., narrow=False):
    blur = (.7 if index == focus else 2.6) if narrow else .7 + .19 * abs(index - focus)
    sx, sy = math.sqrt(64. + blur * blur), math.sqrt(1. + blur * blur)
    return .32 * 8. / (sx * sy) * gaussian(*centre, sx, sy, angle)


def thin_scene(index, channel, narrow=False):
    rgb = compact(index, fan=True)
    rgb[:, :, channel] += thin_light(index, 20, THIN, narrow=narrow)
    return rgb


def radial_scene(index):
    # Three fixed real thin directions, blurred by the same scalar Gaussian.
    rgb = blank()
    for angle in (0., math.pi / 3., 2. * math.pi / 3.):
        light = thin_light(index, 20, GLINT, angle) / 3.
        rgb += light[:, :, None] * np.array([1., .65, .8])
    return rgb


def contrast(rgb):
    before = digest(rgb)
    q, ceiling = LOC.local_contrast(rgb)
    assert digest(rgb) == before, 'local_contrast mutated source RGB'
    assert q.shape == ceiling.shape == (H - 128, W - 128), 'filter crop differs'
    rx, ry = LOC.reference_coordinates(q.shape, [64, 64], BITS, [0., 0.], [0., 0.])
    assert rx[0, 0] == ry[0, 0] == 64 and rx[-1, -1] == W - 65 and ry[-1, -1] == H - 65
    return q, ceiling, rx, ry


def index_records(records, reverse=False):
    ordered = list(reversed(records)) if reverse else records
    return [dict(record, index0=i) for i, record in enumerate(ordered)]


def scan(generator, targets=None, static=False):
    """Actual seed pass then measurement pass; one source q field at a time."""
    maximum = np.zeros(LOC.grid_shape(FIELD), dtype=np.float64)
    seen = np.zeros(maximum.shape, dtype=bool)
    for i in range(1 if static else N):
        q, ceiling, rx, ry = contrast(generator(i))
        LOC.accumulate_maximum(maximum, seen, q, rx, ry, FIELD)
    seeds = LOC.nominate_seeds(maximum, seen, FIELD)
    associations = {}
    if targets is not None:
        for name, point in targets.items():
            matches = [i for i, seed in enumerate(seeds)
                       if (seed['x'] - point[0]) ** 2 + (seed['y'] - point[1]) ** 2 <= 8. ** 2]
            associations[name] = matches
        selected = sorted({i for matches in associations.values() for i in matches})
    else:
        selected = list(range(len(seeds)))
    records = {i: [] for i in selected}
    for frame in range(1 if static else N):
        q, ceiling, rx, ry = contrast(generator(frame))
        before = [digest(a) for a in (q, ceiling, rx, ry)]
        for i in selected:
            records[i].append(LOC.measure_seed(q, ceiling, rx, ry, seeds[i]))
        assert [digest(a) for a in (q, ceiling, rx, ry)] == before, 'measurement mutated inputs'
    if static:
        records = {i: [copy.deepcopy(items[0]) for _ in range(N)] for i, items in records.items()}
    decisions = {str(i): LOC.nominate_track(index_records(items)) for i, items in records.items()}
    return dict(seeds=seeds, associations=associations, decisions=decisions,
                seed_positive_cells=int(np.count_nonzero(maximum > 0)),
                scope='All seed positions retained; non-null controls measure only seeds within8 of planted targets')


def target(result, name):
    indices = result['associations'][name]
    assert len(indices) == 1, f'{name}: expected one live seed, got {indices}'
    return result['decisions'][str(indices[0])]


def nominated(decision, expected):
    return decision['status'] == 'nominated' and abs(decision['index0'] - expected) <= 1


def check(name, passed, **evidence):
    return dict(name=name, passed=bool(passed), **evidence)


def nulls():
    tests, evidence = [], {}
    constant = scan(lambda _: blank(), static=True)
    tests.append(check('constant-no-nomination', all(d['status'] == 'refused' for d in constant['decisions'].values())))
    evidence['constant'] = constant
    for amplitude in (.0002, .002):
        def noisy(index):
            return blank() + np.random.default_rng(76193 + index).normal(0., amplitude, (H, W, 3))
        result = scan(noisy)
        tests.append(check(f'seeded-noise-{amplitude}', result['seed_positive_cells'] > 0 and
                           all(d['status'] == 'refused' for d in result['decisions'].values())))
        evidence[str(amplitude)] = result
    def hot(_):
        rgb = blank(); rgb[:, :, 0] += .4 * gaussian(*GLINT, 1.5, 1.5)
        return rgb
    result = scan(hot, {'hot': GLINT}, static=True)
    decision = target(result, 'hot')
    tests.append(check('persistent-point-no-contraction', decision['status'] == 'refused' and
                       any(r['status'] == 'measured' for r in decision['frames'])))
    evidence['persistent'] = result
    q = np.zeros((160, 176)); q[80, 88] = 1.
    yy, xx = np.indices(q.shape, dtype=np.float64)
    singular = LOC.measure_seed(q, np.zeros(q.shape, bool), xx, yy, {'x': 88., 'y': 80.})
    tests.append(check('single-pixel-singular', singular['status'] == 'unknown' and 'singular-covariance' in singular['reasons']))
    evidence['singular'] = singular
    return tests, evidence


def coordinates():
    values = (1.013, .009, 4.3, -2.7)
    bits = [struct.pack('>d', v).hex() for v in values]
    shape, origin, pivot, offset = (160, 176), [701, 803], [1000., 900.], [56., 38.]
    sy, sx = np.indices(shape, dtype=np.float64)
    z = ((sx + origin[0]) + 1j * (sy + origin[1]) - complex(*pivot) - 2 * complex(*values[2:])) / complex(*values[:2])
    z += complex(*pivot) - complex(*offset)
    rx, ry = LOC.reference_coordinates(shape, origin, bits, pivot, offset)
    error = max(float(np.max(np.abs(rx - z.real))), float(np.max(np.abs(ry - z.imag))))
    seed = {'x': float(z.real[80, 88]), 'y': float(z.imag[80, 88])}
    q = np.exp(-.5 * (((sx - 88.) / 4.) ** 2 + ((sy - 80.) / 2.) ** 2))
    record = LOC.measure_seed(q, np.zeros(shape, bool), rx, ry, seed)
    assert record['status'] == 'measured', record
    mask = q > .1  # A single known connected elliptical footprint, no component reuse.
    weights, points = q[mask], np.column_stack((z.real[mask], z.imag[mask]))
    mass = float(weights.sum())
    centre = np.sum(points * weights[:, None], axis=0) / mass
    delta = points - centre
    covariance = (delta.T * weights) @ delta / mass
    moment_error = max(abs(record['mass'] - mass), float(np.max(np.abs(record['centroid'] - centre))),
                       float(np.max(np.abs(np.array(record['covariance']) - covariance))))
    source_x, source_y = LOC.source_coordinates(z.real, z.imag, bits, pivot, offset)
    forward_error = max(float(np.max(np.abs(source_x - sx - origin[0]))), float(np.max(np.abs(source_y - sy - origin[1]))))
    field = [100, 200, 12, 4]
    xx = np.array([[100., 101.999, 102., 103.999, 104., 112.], [100., 101., 105.9, 108., 111.999, 99.99]])
    yy = np.array([[200.] * 6, [202.] * 6])
    signal = np.arange(1., 13.).reshape(2, 6)
    maximum, seen = np.zeros((2, 6)), np.zeros((2, 6), bool)
    LOC.accumulate_maximum(maximum, seen, signal, xx, yy, field)
    expected = np.array([[2., 4., 5., 0., 0., 0.], [8., 0., 9., 0., 10., 11.]])
    max2, seen2 = np.zeros((16, 48)), np.zeros((16, 48), bool)
    for x in (0, 1, 16, 32): max2[0, x], seen2[0, x] = 2., True
    seeds = LOC.nominate_seeds(max2, seen2, [0, 0, 96, 32])
    tests = [check('nonidentity-inverse-and-forward', error < 1e-10 and forward_error < 1e-10,
                   inverse_max_abs=error, forward_max_abs=forward_error),
             check('original-pixel-moments', moment_error < 1e-10, max_abs=moment_error),
             check('half-open-max-bins', np.array_equal(maximum, expected) and np.array_equal(seen, expected > 0)),
             check('row-major-seed-and-distance32', [(s['x'], s['y']) for s in seeds] == [(1., 1.), (65., 1.)])]
    return tests, dict(record=record, literal_covariance=covariance.tolist(), literal_centroid=centre.tolist(), seeds=seeds)


def glint():
    evidence, tests = {}, []
    for label, fan in [('isolated', False), ('late-fan', True)]:
        result = scan(lambda k: compact(k, fan=fan), {'glint': GLINT})
        decision = target(result, 'glint')
        reverse = LOC.nominate_track(index_records(decision['frames'], reverse=True))
        tests += [check(label + '-focus', nominated(decision, 10)), check(label + '-reversed', nominated(reverse, 20))]
        evidence[label] = dict(scan=result, reversed=reverse)
    return tests, evidence


def thin():
    evidence, tests = {}, []
    for channel in (0, 2):
        for narrow in (False, True):
            witness = []
            for k in (15, 20):
                rgb = blank(); rgb[:, :, channel] += thin_light(k, 20, THIN, narrow=narrow)
                q, ceiling, rx, ry = contrast(rgb)
                witness.append(LOC.measure_seed(q, ceiling, rx, ry, {'x': THIN[0], 'y': THIN[1]}))
            result = scan(lambda k: thin_scene(k, channel, narrow), {'thin': THIN, 'glint': GLINT})
            decision = target(result, 'thin')
            live = all(r['status'] == 'measured' for r in witness) and witness[0]['r'] > 1.1 * witness[1]['r']
            tests.append(check(f'channel{channel}-narrow{narrow}', live and
                               (decision['status'] == 'refused' or nominated(decision, 20)),
                               live_width_change=live))
            evidence[f'{channel}-{narrow}'] = dict(scan=result, isolated_width_witness=witness)
    return tests, evidence


def identity():
    qshape = (160, 176)
    yy, xx = np.indices(qshape, dtype=np.float64)
    records = []
    for k in range(N):
        left, right = 1. - k / (N - 1), k / (N - 1)
        q = left * np.exp(-.5 * ((xx - 85.) ** 2 + (yy - 80.) ** 2))
        q += right * np.exp(-.5 * ((xx - 91.) ** 2 + (yy - 80.) ** 2))
        records.append(LOC.measure_seed(q, np.zeros(qshape, bool), xx, yy, {'x': 88., 'y': 80.}))
    transferred = LOC.nominate_track(index_records(records))
    def crossing(k):
        rgb = blank()
        rgb[:, :, 0] += thin_light(k, 10, GLINT)
        rgb[:, :, 2] += thin_light(k, 20, GLINT, math.pi / 2.)
        return rgb
    crossed = scan(crossing, {'crossing': GLINT})
    decision = target(crossed, 'crossing')
    tests = [check('two-close-peaks-ambiguous', records[15]['status'] == 'unknown' and
                   'ambiguous-identity' in records[15]['reasons']),
             check('identity-transfer-track-refused', transferred['status'] == 'refused'),
             check('connected-crossing-depth-refused', decision['status'] == 'refused')]
    return tests, dict(transferred=transferred, crossing=crossed)


def damaged():
    def remnant(k):
        if k != 22: return compact(k)
        rgb = blank(); rgb[:, :, 0] += .025 * gaussian(*GLINT, .7, .7)
        return rgb
    result = scan(remnant, {'glint': GLINT})
    decision = target(result, 'glint')
    small = decision['frames'][22]
    tests = [check('faint-remnant-excluded', not small['eligible'] and any(
        reason in small['eligibility_reasons'] for reason in ('insufficient-relative-mass', 'insufficient-relative-peak'))),
        check('faint-remnant-not-selected', decision['status'] == 'refused' or nominated(decision, 10))]
    rgb = blank(); rgb[:, :, 0] += 1.4 * gaussian(*GLINT, 2., 2.)
    rgb = np.minimum(rgb, 1.)
    q, ceiling, rx, ry = contrast(rgb)
    clipped = LOC.measure_seed(q, ceiling, rx, ry, {'x': GLINT[0], 'y': GLINT[1]})
    clipped_track = LOC.nominate_track(index_records([clipped] * N))
    tests.append(check('display-clipped-unknown', clipped['status'] == 'unknown' and
                       'display-ceiling-contact' in clipped['reasons'] and clipped['raw_clipping'] == 'unknown' and
                       clipped_track['status'] == 'refused'))
    return tests, dict(remnant=result, clipped=clipped_track)


def radial():
    result = scan(radial_scene, {'radial': GLINT})
    decision = target(result, 'radial')
    reverse = LOC.nominate_track(index_records(decision['frames'], reverse=True))
    return [check('true-late-radial-focus', nominated(decision, 20)),
            check('true-late-radial-reversal', nominated(reverse, 10))], dict(scan=result, reversed=reverse)


def mechanics():
    def records(radii):
        return [dict(index0=i, status='measured', reasons=[], mass=100., peak=1., r=float(r),
                     centroid=[0., 0.], covariance=[[float(r*r), 0.], [0., float(r*r)]],
                     eigenvalues=[float(r*r), float(r*r)], display_ceiling_contact=False, raw_clipping='unknown',
                     footprint_bounds=[-2., -2., 2., 2.], component_pixels=9) for i, r in enumerate(radii)]
    r = np.array([1. + .1 * abs(i - 15) for i in range(N)])
    inputs = {'interior': r, 'endpoint': [1. + .1 * abs(i - 2) for i in range(N)],
              'plateau': [1. + .1 * max(10 - i, i - 12, 0) for i in range(N)],
              'separated': [1. + .1 * min(abs(i - 10), abs(i - 14)) for i in range(N)],
              'constant': [1.] * N,
              'exact-margin': [1. + .05 * abs(i - 5) for i in range(11)]}
    answers = {name: LOC.nominate_track(records(value)) for name, value in inputs.items()}
    tests = [check('interior-positive', answers['interior']['index0'] == 15),
             check('endpoint-refusal', answers['endpoint']['reason'] == 'endpoint-minimum'),
             check('contiguous-plateau-centre', answers['plateau']['index0'] == 11),
             check('separated-ties-refusal', answers['separated']['reason'] == 'separated-tied-intervals'),
             check('constant-refusal', answers['constant']['status'] == 'refused'),
             check('exact-five-frame-margin', answers['exact-margin']['index0'] == 5)]
    return tests, answers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(HERE) and not output.exists(), 'Output must be new below this experiment'
    output.mkdir(parents=True)
    result = dict(scope='Generated display-space operator/identity controls only; no RAW, calibrated noise or photographic quality claim',
                  helper=bind(Path(__file__)), implementation=bind(HERE / 'locator.py'), plan=bind(HERE / 'independent-plan.md'),
                  groups=[], real_locator_scan_admitted=False)
    for name, function in [('01-nulls-first', nulls), ('02-coordinates', coordinates), ('03-glint', glint),
                           ('04-coloured-thin', thin), ('05-identity', identity), ('06-damaged', damaged),
                           ('07-real-radial', radial), ('08-track-mechanics', mechanics)]:
        try:
            checks, evidence = function()
            entry = dict(name=name, passed=all(c['passed'] for c in checks), checks=checks, evidence=evidence)
        except Exception:
            entry = dict(name=name, passed=False, harness_exception=traceback.format_exc())
        result['groups'].append(entry)
        print(json.dumps({k: v for k, v in entry.items() if k != 'evidence'}), flush=True)
        (output / 'controls.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        if name == '01-nulls-first' and not entry['passed']:
            break
    result['real_locator_scan_admitted'] = len(result['groups']) == 8 and all(g['passed'] for g in result['groups'])
    (output / 'controls.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    raise SystemExit(0 if result['real_locator_scan_admitted'] else 1)


if __name__ == '__main__':
    main()
