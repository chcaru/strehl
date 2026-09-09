"""Read four fixed tiny timing controls; no native input or product execution."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASES = ('decode-validate', 'defect', 'gather', 'probe', 'extract-luma', 'variance', 'pyramid-add')
VISITED = ('decode-validate', 'extract-luma', 'variance', 'pyramid-add')
READ = 0


def need(value, reason):
    if not value:
        raise ValueError(reason)


def integer(value):
    return type(value) is int and value >= 0


def read(path, cap):
    global READ
    n = path.stat().st_size
    need(0 < n <= cap and READ + n <= 2 * 1024**2, 'read bound')
    READ += n
    with path.open('rb') as f:
        raw = f.read(n + 1)
    need(len(raw) == n and path.stat().st_size == n, 'stable saved extent')
    return raw, {'path': str(path.resolve()), 'bytes': n, 'sha256': hashlib.sha256(raw).hexdigest()}


def trace_admit(record):
    profile = record['profile']
    mode, trace = profile['mode'], profile['trace']
    phases = profile['phases']
    need(profile['schema'] == 'native-pyramid-phase-profile-v1', 'profile schema')
    need([p['phase'] for p in phases] == list(PHASES), 'phase population')
    need(mode in ('off', 'on', 'placebo'), 'profile mode')
    need([t['phase'] for t in trace] == ([] if mode == 'off' else list(VISITED) * 3),
         'trace call order')
    for p in phases:
        want = 3 if mode != 'off' and p['phase'] in VISITED else 0
        need(integer(p['calls']) and p['calls'] == want, 'phase calls')
    if mode != 'on':
        need(all(p['wall_nanoseconds'] is None and p['wall_seconds'] is None for p in phases)
             and profile['summed_phase_wall_seconds'] is None, 'untimed modes')
        need(all(t['start_ns'] is None and t['end_ns'] is None for t in trace), 'placebo timestamps')
        return
    begin, end = record['consumer_start_ns'], record['consumer_end_ns']
    need(integer(begin) and integer(end) and begin <= end, 'consumer interval')
    totals = dict.fromkeys(PHASES, 0)
    previous = begin
    for t in trace:
        a, b = t['start_ns'], t['end_ns']
        need(integer(a) and integer(b) and begin <= a <= b <= end, 'interval containment')
        need(a >= previous, 'overlapping leaf intervals')
        previous = b
        totals[t['phase']] += b - a
    if record['label'] == 'delay':
        need(totals['decode-validate'] >= 75_000_000, 'known delay attribution')
    for p in phases:
        need(integer(p['wall_nanoseconds']) and p['wall_nanoseconds'] == totals[p['phase']],
             'aggregate duration association')
        need(abs(p['wall_seconds'] - totals[p['phase']] * 1e-9) <= 1e-12, 'wall units')
    need(abs(profile['summed_phase_wall_seconds'] - sum(totals.values()) * 1e-9) <= 1e-9,
         'leaf sum association')
    need(sum(totals.values()) <= end - begin, 'leaf elapsed containment')
    # These are separate reads of the same monotone clock: shared-epoch
    # endpoints enclose the local whole timer, not identical samples.
    need(0 <= record['whole_consumer_wall_seconds'] <= (end - begin) * 1e-9 + 1e-9,
         'consumer wall containment')


def expect_fault(value, expected):
    try:
        trace_admit(value)
    except ValueError as e:
        need(str(e) == expected, 'wrong fault rejection: ' + str(e))
        return {'rejected': True, 'reason': str(e)}
    raise ValueError('fault accepted')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    need(args.output.resolve().parent == HERE and not args.output.exists(), 'fresh local result')
    _, source = read(Path(__file__), 32 * 1024)
    actual = []
    records = {}
    for label in ('off', 'on', 'placebo', 'delay'):
        directory = HERE / ('smoke-' + label)
        raw, ref = read(directory / 'result.json', 32 * 1024)
        row = json.loads(raw)
        need(row['schema'] == 'native-pyramid-profile-smoke-v1' and row['label'] == label,
             'control identity')
        need(row['source_calls'] == [1, 1, 1] and row['folds'] == 3, 'actual consumer population')
        need(row['profile']['mode'] == ('on' if label == 'delay' else label), 'observer arm')
        need(row['requested_delay_ms_per_decode'] == (25 if label == 'delay' else 0)
             and row['actual_delay_calls'] == (3 if label == 'delay' else 0), 'delay visit')
        trace_admit(row)
        outputs = {}
        for kind, filename, cap in (('f32', 'output.f32', 49152), ('tiff', 'output.tiff', 256 * 1024)):
            path = directory / filename
            need(Path(row[kind]['path']).samefile(path), 'fixed output file')
            _, actual_ref = read(path, cap)
            need(row[kind]['bytes'] == actual_ref['bytes'] and row[kind]['sha256'] == actual_ref['sha256'],
                 'actual output hash/extent')
            if kind == 'f32':
                need(actual_ref['bytes'] == 49152, 'complete CFA payload')
            outputs[kind] = actual_ref
        records[label] = row
        actual.append({'label': label, 'result': ref, 'outputs': outputs,
                       'whole_consumer_wall_seconds': row['whole_consumer_wall_seconds'],
                       'profile': row['profile']})
    for kind in ('f32', 'tiff'):
        need(len({r['outputs'][kind]['sha256'] for r in actual}) == 1, 'observer output neutrality')

    # Move exactly the independently requested75ms from the decode aggregate
    # into variance, preserving phase names/counts and the total duration.
    # The actual raw intervals stay fixed and must reject that attribution.
    relabel = copy.deepcopy(records['delay'])
    phases = relabel['profile']['phases']
    phases[0]['wall_nanoseconds'] -= 75_000_000
    phases[5]['wall_nanoseconds'] += 75_000_000
    for p in (phases[0], phases[5]):
        p['wall_seconds'] = p['wall_nanoseconds'] * 1e-9
    faults = {'misattributed-phase': expect_fault(relabel, 'aggregate duration association')}
    overlap = copy.deepcopy(records['delay'])
    first, second = overlap['profile']['trace'][0], overlap['profile']['trace'][4]
    second['start_ns'], second['end_ns'] = first['start_ns'], first['end_ns']
    faults['duplicated-interval'] = expect_fault(overlap, 'overlapping leaf intervals')
    trace_admit(records['delay'])
    result = {'schema': 'native-pyramid-profile-independent-controls-v1', 'status': 'SAVED_CONTROLS_PASS',
              'source': source, 'actual_controls': actual, 'faults': faults, 'restored_delay_passed': True,
              'read_bytes': READ,
              'scope': 'Four actual tiny consumers; two private saved-trace faults. Wall intervals, not CPU. '
                       'Output f32 and whole TIFF bytes equal. No defect/gather/probe or native speed claim.'}
    raw = json.dumps(result, allow_nan=False, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    need(len(raw) < 64 * 1024, 'result extent')
    with args.output.open('xb') as f:
        f.write(raw)
    print(json.dumps({'result': str(args.output.resolve()), 'bytes': len(raw),
                      'sha256': hashlib.sha256(raw).hexdigest()}))


if __name__ == '__main__':
    main()
