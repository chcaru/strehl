"""Recompute report numbers from frozen receipts, and retain compact evidence."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import statistics

SRC = Path(__file__).resolve().parent
OUT = SRC.parents[1]/'outputs'/SRC.name


def records(name):
    return [json.loads(s) for s in (OUT/name).read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def main():
    inputs = json.loads((OUT/'input-manifest.json').read_text())
    assert len(inputs) == 20
    for r in inputs:
        p = Path(r['path'])
        assert p.stat().st_size == r['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == r['sha256']
    groups = {}
    temporal = records('advanced-temporal.jsonl')
    entropy = records('entropy.jsonl')
    for group in ['4', '16']:
        n = int(group)
        sizes = {'original': sum(r['bytes'] for r in inputs if r['group'] == group)}
        jls = [r for r in temporal if r.get('label') == group]
        assert len(jls) == n and all(r['full_file_exact'] for r in jls)
        sizes['jpeg-ls-independent'] = sum(r['encoded_bytes'] for r in jls)
        for kind in ['spatial', 'raw-reference', 'aligned-reference', 'filtered-reference', 'running-reference']:
            rows = [r for r in temporal if r.get('group') == group and r.get('reference_kind') in [kind, 'spatial-keyframe']]
            assert len(rows) == n and all(r['exact_sensor_and_side'] for r in rows)
            sizes[kind+'-zstd'] = sum(r['encoded_bytes'] for r in rows)
        for kind in ['spatial', 'filtered-temporal']:
            rows = [r for r in entropy if r.get('group') == group and (r['kind'] == kind or (kind == 'filtered-temporal' and r['index'] == 0))]
            assert len(rows) == n and all(r['exact'] for r in rows)
            sizes[kind+'-aec'] = sum(r['bytes'] for r in rows)
        groups[group] = sizes
    network = records('network-bench.jsonl')[1:]
    timing = {}
    for mode in ['identity', 'zstd', 'cfa']:
        rows = [r for r in network if r['mode'] == mode]
        assert len(rows) == 2 and all(r['exact'] for r in rows)
        times = [r['seconds_to_durable'] for r in rows]
        timing[mode] = {'wire_bytes': rows[0]['wire_bytes'], 'durable_s_min': min(times),
                        'durable_s_max': max(times), 'durable_s_mean': statistics.mean(times),
                        'standard_error_s_two_repeats': statistics.stdev(times)/(2**0.5)}
    pi = [r for r in records('pi-bench-v3.jsonl') if 'workers' in r]
    assert len(pi) == 42 and all(r['roundtrip_exact'] for r in pi)
    pi_modes = {}
    for mode in [-1, 2, 3, 8, 9, 4, 6]:
        rows = [r for r in pi if r['mode'] == mode and r['workers'] == 4]
        pi_modes[str(mode)] = {'encoded_bytes': rows[0]['encoded_bytes'],
                               'encode_s_min': min(r['encode_s'] for r in rows),
                               'encode_s_median': statistics.median(r['encode_s'] for r in rows),
                               'encode_s_max': max(r['encode_s'] for r in rows)}
    result = {'groups_bytes_including_keyframes': groups, 'lan_short_replay': timing,
              'pi_four_worker_encode': pi_modes,
              'pi_peak_temperature_C': max(r['after']['temperature_mC'] for r in pi)/1000,
              'resource_replay': records('resource-bench.jsonl'),
              'independent_review': False}
    (OUT/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    evidence = SRC/'evidence'
    evidence.mkdir(exist_ok=True)
    names = ['input-manifest.json', 'measured-build.json', 'spatial.jsonl', 'temporal.jsonl',
             'advanced-spatial.jsonl', 'advanced-temporal.jsonl', 'entropy.jsonl',
             'pi-bench-v3.jsonl', 'network-bench.jsonl', 'video-bench.jsonl',
             'extra-controls.jsonl', 'current-camera-bench.jsonl', 'resource-bench.jsonl',
             'summary.json']
    for name in names:
        shutil.copyfile(OUT/name, evidence/name)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
