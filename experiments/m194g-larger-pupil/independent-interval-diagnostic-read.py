"""Read retained diagnostic artifacts only; no numerical-library/helper imports."""
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from collections import Counter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKAGE = HERE / 'reference-interval-diagnostic-1'
RESULT_SHA = '194dbdb0454a02db985b4e28305c9f5a0f5f42fe4223829b3ea8db0f21e5e1f0'
RELEASE_SHA = 'cec6cb4fcb803b57b04b736777e8160264ce45e0e8e5b4fb8fb49048bbcca6e1'
FAILED = (4, 6, 11, 13, 15, 22, 60, 62, 67, 69, 71, 78, 116, 117)
IDS = [f'geometry-{i:03d}' for i in sorted(FAILED + (3, 14))]
PAIRS = [(i, a) for i in IDS for a in ('primary', 'refined')]


def canon(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def parse(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError('duplicate key')
            d[k] = v
        return d
    def bad(value):
        raise ValueError('nonfinite '+value)
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    def finite(v):
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError('nonfinite float')
        if isinstance(v, dict):
            for c in v.values(): finite(c)
        if isinstance(v, list):
            for c in v: finite(c)
    finite(result)
    return result


def checked(path, sha, size=None, limit=32*1024*1024):
    path = Path(path).resolve(strict=True)
    path.relative_to(ROOT)
    with path.open('rb') as f:
        raw = f.read(limit+1)
    assert len(raw) <= limit
    assert hashlib.sha256(raw).hexdigest() == sha
    assert size is None or len(raw) == size
    return raw


def ref(rec, base):
    assert set(rec) == {'path', 'sha256', 'bytes'}
    assert type(rec['bytes']) is int
    p = Path(rec['path'])
    return checked(p if p.is_absolute() else base/p, rec['sha256'], rec['bytes'])


def sig(row):
    return {k: row[k] for k in ('case_id', 'arm', 'status', 'value_e', 'branch', 'receipt', 'error', 'actual_integrand_calls')}


def count_trace(mode, records):
    groups = [[] for _ in mode['intervals']]
    for r in records:
        index = r['interval']
        assert type(index) is int and 0 <= index < len(groups)
        interval = mode['intervals'][index]
        assert r['call_id'] == interval['call_id']
        assert r['ordinal'] == len(groups[index])
        assert type(r['t']) is float and r['t'].hex() == r['t_hex']
        assert float(r['value']).hex() == r['value_hex']
        assert interval['left'] <= r['t'] <= interval['right'], 'sample outside bound'
        groups[index].append(r)
    for interval, samples in zip(mode['intervals'], groups):
        a, b = interval['left'], interval['right']
        assert -1 <= a < b <= 1 and a.hex() == interval['left_hex'] and b.hex() == interval['right_hex']
        assert interval['width'] == b-a
        assert len(samples) == interval['actual_calls'] == interval['collected_calls']
        unique = set(r['t_hex'] for r in samples)
        assert unique == set(interval['queried_t_hex'])
        assert len(unique) == interval['distinct_queried_coordinates']
        assert interval['repeated_queries'] == len(samples)-len(unique)
        assert interval['left_endpoint_queries'] == sum(r['t'] == a for r in samples)
        assert interval['right_endpoint_queries'] == sum(r['t'] == b for r in samples)
    return groups


def main():
    raw = checked(PACKAGE/'result.json', RESULT_SHA)
    result = parse(raw)
    assert result['status'] == 'PASS_DIAGNOSTIC'
    assert result['error'] is result['source_capture_error'] is None and result['cleanup_errors'] == []
    release = parse(ref(result['execution_release'], ROOT))
    assert result['execution_release']['sha256'] == RELEASE_SHA
    assert release['scope'] == 'reference-interval-diagnostic'
    commands = [[RELEASE_SHA if a == 'ACTUAL_EXECUTION_RELEASE_SHA256' else a for a in c] for c in release['commands']]
    assert result['invocation']['orig_argv'] in commands
    assert Path(result['invocation']['cwd']).resolve() == ROOT
    assert result['invocation']['orig_argv'][0] == result['invocation']['executable']
    assert result['invocation']['xoptions'] == dict(utf8=True, faulthandler=True, pycache_prefix='experiments/m194g-larger-pupil/work/cache-reference-interval-diagnostic-1')
    expected = dict(release['source_bindings'])
    for r in release['inputs']:
        v = {k: r[k] for k in ('sha256', 'bytes')}
        assert r['path'] not in expected or expected[r['path']] == v
        expected[r['path']] = v
    assert canon(expected) == canon(result['sources_before']) == canon(result['sources_after'])
    for name, r in expected.items():
        for base in (ROOT, PACKAGE/'sources-before', PACKAGE/'sources-after'):
            checked(base/name, r['sha256'], r['bytes'])
    first = parse(ref(result['first_result'], ROOT))
    original = {(r['case_id'], r['arm']): r for r in first['baseline']}
    reference_signatures = []
    for key in PAIRS:
        r = dict(original[key])
        r['actual_integrand_calls'] = r['work_after']['evaluations']-r['work_before']['evaluations']
        reference_signatures.append(sig(r))
    signature_bytes = canon(reference_signatures)
    modes = []
    for wanted, r in zip(('off', 'count', 'placebo'), result['modes']):
        mode = parse(ref(r, PACKAGE))
        assert mode['mode'] == wanted
        assert [(r['case_id'], r['arm']) for r in mode['rows']] == PAIRS
        assert canon([sig(r) for r in mode['rows']]) == signature_bytes
        assert sum(i['actual_calls'] for i in mode['intervals']) == sum(r['actual_integrand_calls'] for r in mode['rows'])
        assert sum(r['actual_integrand_calls'] for r in mode['rows']) == mode['work_after']['evaluations']-mode['work_before']['evaluations']
        for interval in mode['intervals']:
            assert interval['epsrel'] == 0 and type(interval['limit']) is int and interval['limit'] == 128
            assert interval['epsabs'] > 0
        modes.append(mode)
    assert len(result['modes']) == 3
    for left, right in zip(modes[:-1], modes[1:]):
        assert left['work_after']['evaluations'] == right['work_before']['evaluations']
    off, count, placebo = modes
    assert off['optional_hook_calls'] == off['collected_records'] == 0
    assert count['optional_hook_calls'] == count['collected_records'] > 0
    assert placebo['optional_hook_calls'] == count['optional_hook_calls'] and placebo['collected_records'] == 0
    assert off['trace'] is placebo['trace'] is None
    trace_raw = ref(count['trace'], PACKAGE)
    assert len(trace_raw) == count['trace_bytes']
    lines = trace_raw.splitlines()
    assert len(lines) <= 100000 and trace_raw.endswith(b'\n')
    records = [parse(line) for line in lines]
    groups = count_trace(count, records)
    warnings = []
    histogram = Counter()
    for i, samples in zip(count['intervals'], groups):
        if not i['warnings']:
            continue
        assert i['left'] == -1 or i['right'] == 1
        # Independently enumerate adjacent floats; no monotone-bit encoding.
        p, steps = i['left'], 0
        while p != i['right'] and steps <= 256:
            p = math.nextafter(p, i['right'])
            steps += 1
        assert p == i['right'] and steps <= 256
        assert steps == i['representable_steps']
        assert i['suspected_endpoint_interval'] is True
        assert all(w['category'] == 'IntegrationWarning' and 'Extremely bad integrand behavior' in w['message'] for w in i['warnings'])
        assert len(samples) > len({r['t_hex'] for r in samples})
        histogram[(steps, i['distinct_queried_coordinates'], len(samples))] += 1
        warnings.append(dict(call_id=i['call_id'], left_hex=i['left_hex'], right_hex=i['right_hex'], steps=steps,
                             queried=len(samples), distinct=i['distinct_queried_coordinates'], integral=i['integral'], error=i['error_indicator']))
    assert {(r['call_id']) for r in warnings} == {f'geometry-{i:03d}:{a}' for i in FAILED for a in ('primary','refined')}
    # Re-choose a trace-value location: force the last warned interval's first
    # sample outside its interval; keep its numeric/hex pair coherent.
    changed = copy.deepcopy(records)
    ordinal = max(i for i,r in enumerate(count['intervals']) if r['warnings'])
    target = next(r for r in changed if r['interval'] == ordinal)
    target['t'] = math.nextafter(count['intervals'][ordinal]['right'], math.inf)
    target['t_hex'] = target['t'].hex()
    detected = False
    try:
        count_trace(count, changed)
    except AssertionError as e:
        detected = str(e) == 'sample outside bound'
    assert detected
    count_trace(count, records)
    total = sum(r['actual_integrand_calls'] for m in modes for r in m['rows'])
    assert total == result['budget']['evaluations'] == result['budget']['chord_evaluations']
    assert result['budget']['factor_evaluations'] == 0 and total <= 100000
    assert result['budget']['cpu_seconds'] <= 10 and result['budget']['wall_seconds'] <= 20
    assert len(result['checks']) == 11 and all(c['passed'] is True for c in result['checks'])
    assert set(result['runtime']['threads'].values()) == {'2'}
    output = dict(status='VERIFIED_RETAINED_DIAGNOSTIC_ONLY', result_sha256=RESULT_SHA, execution_release_sha256=RELEASE_SHA,
                  source_binding_count=len(expected), compared_call_count=len(PAIRS)*3, actual_integrand_calls=total,
                  signature_sha256=hashlib.sha256(signature_bytes).hexdigest(), trace_records=len(records), trace_bytes=len(trace_raw),
                  warning_intervals=warnings, step_histogram=[dict(steps=k[0],distinct=k[1],calls=k[2],intervals=v) for k,v in sorted(histogram.items())],
                  independent_changed_sample_refused=detected, restored_actual_trace_pass=True,
                  cpu_seconds=result['budget']['cpu_seconds'], wall_seconds=result['budget']['wall_seconds'],
                  original_invocation=result['invocation'], reader_invocation=list(sys.orig_argv),
                  reader_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='Artifact/source/command/trace verification; no helper or quadrature execution and no complete reference commission')
    path = HERE/'independent-interval-diagnostic-read.json'
    path.write_bytes(canon(output))
    print(output['status'], 'calls', output['compared_call_count'], 'warnings', len(warnings), flush=True)


if __name__ == '__main__':
    main()
