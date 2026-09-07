"""Read-only independent M192d artifact reviewer; never executes saved commands.

Choices/falsifiers are frozen in independent-preregistration.md. No sampler,
author runner, inherited harness, numpy or tifffile is imported.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCHEDULE = [('warmup', 'off'), ('forward', 'off'), ('forward', 'on'),
            ('forward', 'placebo'), ('reverse', 'placebo'), ('reverse', 'on'),
            ('reverse', 'off')]


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


class PatchedView:
    """Read-only virtual copy; exact byte substitutions cannot touch source."""
    def __init__(self, path, changes=None):
        self.stream = Path(path).open('rb')
        self.changes = changes or {}

    def seek(self, offset):
        self.stream.seek(offset)

    def read(self, count):
        offset = self.stream.tell()
        block = self.stream.read(count)
        patches = [(i-offset, value) for i, value in self.changes.items()
                   if offset <= i < offset+len(block)]
        if patches:
            block = bytearray(block)
            for i, value in patches:
                block[i] = value
            return bytes(block)
        return block

    def close(self):
        self.stream.close()


def sha_file(path, patches=None):
    stream = PatchedView(path, patches)
    digest = hashlib.sha256()
    try:
        while block := stream.read(768*1024):
            digest.update(block)
    finally:
        stream.close()
    return digest.hexdigest().upper()


def tiff(path, patches=None):
    """Independent restricted TIFF parser: native RGB16 strips, no decompressor."""
    stream = PatchedView(path, patches)
    size = Path(path).stat().st_size
    try:
        header = stream.read(8)
        assert header[:4] == b'II*\x00', 'expected little-endian classic TIFF'
        ifd = struct.unpack_from('<I', header, 4)[0]
        assert 8 <= ifd < size-6
        stream.seek(ifd)
        count = struct.unpack('<H', stream.read(2))[0]
        entries = stream.read(12*count)
        assert struct.unpack('<I', stream.read(4))[0] == 0, 'multiple TIFF pages'
        tags = {}
        for i in range(count):
            tag, kind, n, offset = struct.unpack_from('<HHII', entries, i*12)
            assert tag not in tags, 'duplicate TIFF tag'
            width = {1:1, 2:1, 3:2, 4:4, 5:8, 7:1, 9:4, 10:8, 11:4, 12:8}[kind]
            length = n*width
            start = ifd+2+12*i+8 if length <= 4 else offset
            assert 0 <= start <= size-length
            stream.seek(start)
            data = stream.read(length)
            assert len(data) == length
            values = list(struct.unpack('<'+{3:'H',4:'I'}[kind]*n, data)) if kind in (3,4) else data
            tags[tag] = (values, start)
        scalar = lambda k, default=None: tags[k][0][0] if k in tags else default
        w, h = scalar(256), scalar(257)
        assert w > 0 and h > 0
        assert tags[258][0] == [16,16,16]
        assert scalar(259) == 1 and scalar(262) == 2
        assert scalar(277) == 3 and scalar(284,1) == 1
        assert scalar(274,1) == 1, 'oriented output'
        assert 339 not in tags or tags[339][0] in ([1], [1,1,1])
        rows = scalar(278)
        offsets, counts = tags[273][0], tags[279][0]
        assert rows > 0 and len(offsets) == len(counts) == math.ceil(h/rows)
        digest = hashlib.sha256()
        for i, (offset, length) in enumerate(zip(offsets,counts)):
            assert length == min(rows,h-i*rows)*w*6
            assert 0 <= offset <= size-length
            stream.seek(offset)
            remain = length
            while remain:
                block = stream.read(min(remain,768*1024))
                assert block
                digest.update(block)
                remain -= len(block)
        software = tags[305][0].rstrip(b'\x00').decode('ascii')
        return dict(shape=[h,w,3], pixel_sha256=digest.hexdigest().upper(),
                    output_sha256=sha_file(path,patches), output_bytes=size,
                    strip_count=len(offsets), rows_per_strip=rows,
                    offsets=offsets, software=software, software_offset=tags[305][1])
    finally:
        stream.close()


def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8), (a,b)


def check_record(row):
    close(row['wall_seconds'], (row['end_ns']-row['start_ns'])/1e9)
    host = []
    for boundary in ('host_start','host_end'):
        counters = row[boundary]
        total = counters['kernel_100ns']+counters['user_100ns']
        busy = total-counters['idle_100ns']
        assert total == counters['total_100ns'] and busy == counters['busy_100ns']
        host.append(busy)
    close(row['host_busy_cpu_seconds'],(host[1]-host[0])/1e7)
    job = row['job_accounting']
    assert job['total_cpu_100ns'] == job['total_user_100ns']+job['total_kernel_100ns']
    close(row['product_cpu_seconds'],(job['total_user_100ns']+job['total_kernel_100ns'])/1e7)
    assert job['active_processes'] == 0 and job['total_processes'] >= 1
    assert row['observer_cpu_seconds'] >= 0
    coverage = row['sample_count']/(row['sample_count']+row['missed_intervals'])
    close(row['coverage'],coverage)
    disposition = row['max_interval_ms_including_final'] <= 100 and coverage >= .9
    assert row['sampling_pass'] is disposition
    trace = row['trace']
    obs = trace['observations']
    assert len(obs)+trace['dropped']['observations'] == row['sample_count']
    assert len(obs) <= 1000 and len(trace['events']) <= 4096 and len(trace['incidents']) <= 32
    gaps = []
    if obs[0]['poll'] == 0:
        gaps.append((obs[0]['observed_ns']-row['start_ns'])/1e6)
    for a,b in zip(obs,obs[1:]):
        assert b['poll'] == a['poll']+1
        gaps.append((b['observed_ns']-a['observed_ns'])/1e6)
    for observation in obs:
        assert observation['observed_ns'] >= observation['start_ns']
        assert observation['private_bytes'] == sum(p['private'] for p in observation['processes'])
        assert observation['private_bytes'] <= row['peak_private_bytes']
    assert obs[-1]['poll'] == row['sample_count']-1
    gaps.append(row['final_interval_ms'])
    reconstructed_closed = obs[-1]['observed_ns']+round(row['final_interval_ms']*1e6)
    assert reconstructed_closed <= row['end_ns']
    events = {}
    for event in trace['events']:
        events[(event['phase'],event['poll'],event['start_ns'])] = event
    for incident in trace['incidents']:
        trigger = incident['trigger']
        if trigger['kind'] in ('observation-gap','final-closure-gap'):
            gap = (trigger['end_ns']-trigger['start_ns'])/1e6
            close(trigger['gap_ms'],gap)
            gaps.append(gap)
        for event in incident['context']+incident['following']:
            events[(event['phase'],event['poll'],event['start_ns'])] = event
    observed_max = {}
    for event in events.values():
        ms = (event['end_ns']-event['start_ns'])/1e6
        close(event['wall_ms'],ms)
        assert event['start_ns'] <= event['end_ns'] <= row['end_ns']
        assert event['injected_delay_ms'] == 0, 'real delay injected'
        assert event['observer_thread_cpu_ms'] >= 0
        observed_max[event['phase']] = max(observed_max.get(event['phase'],0),ms)
    lower_bound = max(gaps)
    assert lower_bound <= row['max_interval_ms_including_final']+1e-8
    if trace['dropped']['observations'] == 0:
        close(lower_bound,row['max_interval_ms_including_final'])
    if trace['enabled']:
        assert sum(trace['phase_counts'].values()) == len(trace['events'])+trace['dropped']['events']
        for phase in ('sleep-wakeup','job-pids','job-accounting','job-memory'):
            assert trace['phase_counts'][phase] == row['sample_count']
        for phase in ('final-poll','final-accounting','final-memory'):
            assert trace['phase_counts'][phase] == 1
            assert any(e['phase']==phase for e in events.values())
        for phase,ms in observed_max.items():
            assert ms <= trace['phase_max_ms'][phase]+1e-8
        assert max(e['end_ns'] for e in events.values()) <= reconstructed_closed
        expected_telemetry = math.ceil(row['sample_count']/10)
        assert trace['phase_counts']['telemetry'] == expected_telemetry
        assert len(row['telemetry'])+trace['dropped']['telemetry'] == expected_telemetry
        assert trace['placebo'] == (row['mode']=='placebo')
    else:
        assert not trace['events'] and not trace['phase_counts'] and not row['telemetry']
    return dict(reconstructed_retained_max_interval_ms=lower_bound,
                complete_max_reproduced=math.isclose(lower_bound,row['max_interval_ms_including_final'],abs_tol=1e-8),
                retained_unique_phase_events=len(events),
                phase_max_supported={k:math.isclose(v,observed_max.get(k,-1),abs_tol=1e-8)
                                     for k,v in trace['phase_max_ms'].items()},
                dropped=trace['dropped'], incidents=trace['incidents'],
                observer_exact_boundary_counters_available=False)


def rejected(function):
    try:
        function()
    except (AssertionError,ValueError,KeyError):
        return True
    return False


def check_telemetry(row):
    rows = row['telemetry']
    for point in rows:
        assert row['start_ns'] <= point['start_ns'] <= point['end_ns'] <= row['end_ns']
        host = point['host']
        assert host['kernel_100ns']+host['user_100ns']==host['total_100ns']
        assert host['total_100ns']-host['idle_100ns']==host['busy_100ns']
        assert row['host_start']['busy_100ns'] <= host['busy_100ns'] <= row['host_end']['busy_100ns']
        assert point['product_cpu_100ns'] <= row['job_accounting']['total_cpu_100ns']
        assert isinstance(point['per_core_cpu_seconds'],list)
        assert isinstance(point['processor_power'],list) and point['power_query_status']==0
        n = len(point['per_core_cpu_seconds'])
        assert len(point['processor_power'])==n and 0 <= point['observer_cpu_number'] < n
        assert sorted(core['number'] for core in point['processor_power'])==list(range(n))
    for before,after in zip(rows,rows[1:]):
        for key in ('observer_process_cpu_s','observer_thread_cpu_s','product_cpu_100ns'):
            assert after[key] >= before[key]
    return dict(snapshots=len(rows),logical_processor_counts=sorted({len(t['processor_power']) for t in rows}),
        sampled_observer_cpu_numbers=sorted({t['observer_cpu_number'] for t in rows}),
        os_current_mhz=sorted({core['current_mhz'] for t in rows for core in t['processor_power']}),
        current_idle_states=sorted({core['current_idle_state'] for t in rows for core in t['processor_power']}),
        active_power_schemes=sorted({t['active_power_scheme'] for t in rows}),
        unavailable=row['unavailable'],frequency_semantics=row['frequency_semantics'])


def check_manifest(rows):
    for row in rows:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes']
        assert sha_file(path) == row['sha256']
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output_directory',type=Path)
    args = parser.parse_args()
    out = args.output_directory.resolve()
    assert (out/'summary.json').exists() or (out/'aborted.json').exists(), 'await complete/abort record'
    if (out/'aborted.json').exists():
        raise RuntimeError('Registered rehearsal aborted; preserve and review abort before success validation')
    freeze = read_json(out/'source-freeze.json')
    summary = read_json(out/'summary.json')
    original = ROOT/'experiments/M192-m12-certify/recovery-20260906-163253/results/records.jsonl'
    prior = [json.loads(line) for line in original.read_text().splitlines()]
    reference = next(row for row in prior if row['run_id']==freeze['reference_run_id'])
    assert reference['phase']=='native' and reference['limit']==33 and reference['workers']==8 and reference['kind']=='scored'
    assert reference['output_sha256']==freeze['reference_output_sha256']
    assert reference['pixel_sha256']==freeze['reference_pixel_sha256']
    before,after = read_json(out/'inputs-before.json'),read_json(out/'inputs-after.json')
    assert before == after and len(before)==33
    integrity = dict(inputs=check_manifest(before), originals=check_manifest(freeze['originals']),
                     sources=check_manifest(freeze['sources']),sidecar=check_manifest([freeze['sidecar']]))
    paths = sorted(out.glob('*-record.json'))
    assert len(paths)==7 and summary['completed']==7
    reports,rows = [],[]
    for i,path in enumerate(paths):
        row = read_json(path)
        assert row['index']==i and (row['sweep'],row['mode'])==SCHEDULE[i]
        assert row['returncode']==0
        assert row['binary_sha256']==freeze['sources'][-1]['sha256']
        assert row['sidecar_sha256']==freeze['sidecar']['sha256']
        expected = [freeze['sources'][-1]['path'],'stack',str(Path(before[0]['path']).parent),
                    '--limit','33','--out',row['output_path'],'--merge','pyramid','--pyramid-gate','2.0',
                    '--resampler','catmull-rom','--cover','scale','--linear-srgb','--demosaic']
        assert row['argv']==expected
        env = {k:v for k,v in row['environment'].items() if v is not None}
        assert set(env)=={'STREHL_PYRAMID_WORKERS','STREHL_WARPMAP','STREHL_CACHE_DIR','TEMP','TMP'}
        assert env['STREHL_PYRAMID_WORKERS']=='8' and env['STREHL_WARPMAP']==freeze['sidecar']['path']
        assert env['TEMP']==env['TMP']==str(Path(row['output_path']).parent/'temp')
        for stream in ('stdout','stderr'):
            artifact = row[stream+'_artifact']
            actual = out/artifact['path']
            assert actual.stat().st_size==artifact['bytes'] and sha_file(actual)==artifact['sha256']
        terminal = (out/row['stderr_artifact']['path']).read_text(encoding='utf-8')
        for pattern in (r'frames\s*:\s*33 from ',r'33 placed / 0 refused',r'folded\s*:\s*33 / 33 frames',
                        r'8 execution threads',r'4 canonical chunks',r'alignment\s*:\s*ON \(sidecar-override\)',
                        r'camera RGB -> LINEAR sRGB',r'Malvar-He-Cutler demosaic',r'total\s*:'):
            assert re.search(pattern,terminal), pattern
        assert 'wrote           : '+row['output_path'] in terminal
        witness = tiff(row['output_path'])
        for key in ('output_sha256','pixel_sha256','shape'):
            assert witness[key]==reference[key] and witness[key]==row['tiff'][key]
        assert witness['output_bytes']==row['tiff']['output_bytes']
        trace_report = check_record(row)
        reports.append(dict(index=i,sweep=row['sweep'],mode=row['mode'],wall_seconds=row['wall_seconds'],
             output_sha256=witness['output_sha256'],pixel_sha256=witness['pixel_sha256'],shape=witness['shape'],
             sampling_pass=row['sampling_pass'],max_interval_ms=row['max_interval_ms_including_final'],
             final_interval_ms=row['final_interval_ms'],coverage=row['coverage'],
             phase_max_ms=row['trace']['phase_max_ms'],product_cpu_seconds=row['product_cpu_seconds'],
             host_busy_cpu_seconds=row['host_busy_cpu_seconds'],observer_cpu_seconds=row['observer_cpu_seconds'],
             telemetry_count=len(row['telemetry']),telemetry=check_telemetry(row),trace=trace_report))
        rows.append(row)
    # Re-choose the first on-mode file, rather than the author's final off file.
    chosen = next(row for row in rows if row['mode']=='on')
    output = Path(chosen['output_path'])
    baseline = tiff(output)
    placebo = tiff(output,{})
    assert baseline==placebo
    with output.open('rb') as stream:
        metadata_offset = baseline['software_offset']
        stream.seek(metadata_offset)
        metadata_old = stream.read(1)[0]
        h,w,_ = baseline['shape']
        x,y,channel = w-29,h-17,2
        strip = y//baseline['rows_per_strip']
        pixel_offset = baseline['offsets'][strip]+((y%baseline['rows_per_strip'])*w+x)*6+channel*2+1
        stream.seek(pixel_offset)
        pixel_old = stream.read(1)[0]
    metadata_mutant = tiff(output,{metadata_offset:metadata_old^1})
    pixel_mutant = tiff(output,{pixel_offset:pixel_old^8})
    assert metadata_mutant['output_sha256']!=baseline['output_sha256']
    assert metadata_mutant['pixel_sha256']==baseline['pixel_sha256']
    assert pixel_mutant['output_sha256']!=baseline['output_sha256']
    assert pixel_mutant['pixel_sha256']!=baseline['pixel_sha256']
    assert tiff(output)==baseline
    mutations = {}
    for name in ('cpu','phase','sampling'):
        mutant = copy.deepcopy(chosen)
        if name=='cpu':
            mutant['host_end']['kernel_100ns'] += 1_000_000
        elif name=='phase':
            mutant['trace']['events'][-1]['wall_ms'] += 123
        else:
            mutant['sampling_pass'] = not mutant['sampling_pass']
        mutations[name] = rejected(lambda:check_record(mutant))
        assert mutations[name]
    wrong_shape = copy.deepcopy(baseline)
    wrong_shape['shape'][1] -= 2
    def shape_contract(witness):
        assert witness['shape']==reference['shape']
    mutations['dimensions'] = rejected(lambda:shape_contract(wrong_shape))
    assert mutations['dimensions']
    timings = {}
    for mode in ('off','on','placebo'):
        selected = [row for row in rows[1:] if row['mode']==mode]
        deltas = [row['wall_seconds']-next(base['wall_seconds'] for base in rows[1:]
                  if base['sweep']==row['sweep'] and base['mode']=='off') for row in selected]
        timings[mode] = dict(minimum_wall_seconds=min(r['wall_seconds'] for r in selected),
                    paired_delta_seconds=deltas,paired_mean_seconds=statistics.mean(deltas),
                    paired_sem_seconds=statistics.stdev(deltas)/math.sqrt(2))
    result = dict(schema='m192d-independent-artifact-review-v1',status='PASS',integrity=integrity,
        source_sha256=sha_file(Path(__file__)),preregistration_sha256=sha_file(HERE/'independent-preregistration.md'),
        author_output_directory=str(out),rows=reports,semantic_mutations_rejected=mutations,
        file_pixel_mutations=dict(chosen_run=chosen['index'],metadata_offset=metadata_offset,
          pixel_coordinate=[x,y,channel],pixel_offset=pixel_offset,baseline=baseline,
          metadata_mutant=metadata_mutant,pixel_mutant=pixel_mutant,placebo_and_original_recheck=True),
        sampling_pass_count=sum(row['sampling_pass'] for row in rows),timing_descriptive_only=timings,
        limitations=['Exact observer CPU start/end pair not retained; only delta and interior cumulative snapshots.',
          'Bounded observation/phase tails cannot reconstruct every omitted sub-threshold interval or phase maximum.',
          'File and pixel hash checks do not qualify geometry, image quality, native N299 memory or historical sampler stalls.'])
    (HERE/'independent-verification.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','integrity','semantic_mutations_rejected','sampling_pass_count','timing_descriptive_only')},indent=2))


if __name__=='__main__':
    main()
