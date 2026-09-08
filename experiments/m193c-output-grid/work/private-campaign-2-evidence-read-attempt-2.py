"""Read retained private2 evidence only; no subject imports, subprocesses or rendering."""
import ast
import collections
import hashlib
import json
import math
from pathlib import Path
import struct
import traceback

ROOT = Path(__file__).resolve().parents[3]
B = ROOT / 'experiments/m193c-output-grid'
OUT = B / 'private-campaign-2'
REPORT = B / 'work/private-campaign-2-evidence-read.json'
checked = {}
summary = {'scope': 'retained evidence and independent classic-TIFF strip read only', 'errors': []}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def path(name):
    p = Path(name)
    return (p if p.is_absolute() else ROOT / p).resolve()


def digest(p):
    h = hashlib.sha256()
    n = 0
    with p.open('rb') as f:
        while chunk := f.read(1 << 20):
            n += len(chunk)
            h.update(chunk)
    return {'sha256': h.hexdigest(), 'bytes': n}


def ref(v):
    p = path(v['path'])
    need(type(v['bytes']) is int and v['bytes'] >= 0, 'typed FileRef extent')
    if p not in checked:
        checked[p] = digest(p)
    need(all(checked[p][k] == v[k] for k in ('bytes', 'sha256')), 'actual FileRef: ' + str(p))
    return p


def pairs(items):
    d = {}
    for k, v in items:
        need(k not in d, 'duplicate JSON key')
        d[k] = v
    return d


def read(v):
    p = ref(v) if isinstance(v, dict) else path(v)
    need(p.stat().st_size <= 4 << 20, 'bounded retained JSON')
    raw = p.read_bytes()
    if isinstance(v, dict):
        need(len(raw) == v['bytes'] and hashlib.sha256(raw).hexdigest() == v['sha256'], 'same-read JSON')
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def same_ref(a, b):
    need(ref(a) == ref(b) and all(a[k] == b[k] for k in ('sha256', 'bytes')), 'normalized FileRef association')


def source_map(m):
    for name, v in m.items():
        ref(dict(path=name, **v))


def source_literals():
    # Literal records only. Never compile/import the owner being inspected.
    wanted = {'CASES', 'STAGES', 'DERIVATIVE_SOURCE_IDS', 'DERIVATIVE_READER_IDS'}
    tree = ast.parse((B / 'private-campaign.py').read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in wanted:
                out[node.targets[0].id] = ast.literal_eval(node.value)
    need(set(out) == wanted, 'retained literal population')
    return out


def observation(o, command, label):
    need(o['command'] == command and o['exit_code'] == 0 and o['error'] is None and
         o['cleanup_errors'] == [] and o['terminal_job_accounting'] is True and
         o['direct_exit_observed'] is True and o['pipe_eof_observed'] is True, 'terminal launch: ' + label)
    a, lim = o['job_accounting'], o['limits']
    need(a['active_processes'] == 0 and a['total_cpu_100ns'] == a['total_user_100ns'] + a['total_kernel_100ns'], 'terminal CPU: ' + label)
    need(a['total_cpu_100ns'] / 1e7 <= lim['cpu_seconds'] and o['wall_seconds'] <= lim['wall_seconds'] and
         o['job_memory']['peak_job_memory_used_bytes'] <= lim['committed_bytes'], 'retained process bounds: ' + label)
    ref(o['log'])
    need(o['log_bytes'] == o['log']['bytes'] <= lim['log_bytes'], 'actual log bound: ' + label)
    d = o['post_exit_drain']
    need(d['completed'] is True and d['last_accounting']['active_processes'] == 0 and
         o['termination']['attempted'] is False, 'successful drain/termination: ' + label)
    return dict(label=label, cpu_seconds=a['total_cpu_100ns']/1e7, wall_seconds=o['wall_seconds'],
                peak_committed_bytes=o['job_memory']['peak_job_memory_used_bytes'], log_bytes=o['log_bytes'],
                first_active=d['initial_accounting']['active_processes'], polls=d['observation_count'],
                total_processes=a['total_processes'])


def test_log(launch):
    import re
    text = ref(launch['log']).read_text()
    name = launch['command'][launch['command'].index('--exact') + 1]
    need(len(re.findall(r'^test ' + re.escape(name) + r' \.\.\. ok$', text, re.M)) == 1, 'actual named test pass')
    need(len(re.findall(r'^test result: ok\. 1 passed; 0 failed; 0 ignored; 0 measured; \d+ filtered out; finished in [0-9.]+s$', text, re.M)) == 1, 'actual one-test summary')


def tiff(v):
    p = ref(v)
    need(v['bytes'] <= 1 << 20, 'small TIFF byte ceiling')
    raw = p.read_bytes()
    need(raw[:4] == b'II*\x00', 'little-endian classic TIFF')
    loc = struct.unpack_from('<I', raw, 4)[0]
    n = struct.unpack_from('<H', raw, loc)[0]
    need(0 < n <= 64 and loc + 2 + n*12 + 4 <= len(raw), 'bounded IFD')
    tags = {}
    for i in range(n):
        start = loc + 2 + i*12
        tag, typ, count = struct.unpack_from('<HHI', raw, start)
        need(tag not in tags and count <= 4096 and typ in (1, 2, 3, 4, 5), 'typed unique TIFF tag')
        unit = {1:1, 2:1, 3:2, 4:4, 5:8}[typ]
        offset = start+8 if unit*count <= 4 else struct.unpack_from('<I', raw, start+8)[0]
        need(offset + unit*count <= len(raw), 'TIFF tag extent')
        if typ in (3,4):
            value = list(struct.unpack_from('<'+('H' if typ == 3 else 'I')*count, raw, offset))
        else:
            value = raw[offset:offset+unit*count].hex()
        tags[tag] = value
    need(struct.unpack_from('<I', raw, loc+2+n*12)[0] == 0, 'one TIFF IFD')
    w, h = tags[256][0], tags[257][0]
    need(0 < w <= 320 and 0 < h <= 240 and tags[258] == [16,16,16] and tags[259] == [1] and
         tags[262] == [2] and tags[277] == [3] and tags.get(284,[1]) == [1] and
         tags.get(317,[1]) == [1] and tags.get(339,[1,1,1]) == [1,1,1], 'u16 uncompressed contiguous RGB')
    offsets, extents = tags[273], tags[279]
    need(len(offsets) == len(extents) and len(offsets) <= h and sum(extents) == w*h*6, 'strip population')
    intervals = sorted(zip(offsets, extents))
    for i,(off,extent) in enumerate(intervals):
        need(off >= 8 and off+extent <= len(raw) and (i == 0 or intervals[i-1][0]+intervals[i-1][1] <= off), 'nonoverlapping strips')
    pixels = b''.join(raw[o:o+s] for o,s in zip(offsets,extents))
    return dict(path=str(p.relative_to(ROOT)).replace('\\','/'), shape=[h,w,3], strips=len(offsets),
                pixel_sha256=hashlib.sha256(pixels).hexdigest(), file_sha256=v['sha256'], bytes=len(raw),
                identity=[p.stat().st_dev,p.stat().st_ino]), pixels


def run():
    literal = source_literals()
    result = read(OUT / 'result.json')
    release = read(result['execution_release'])
    outer = read(B / 'work/private-campaign-2-outer.json')
    console = read(B / 'work/private-campaign-2-console.txt')
    need(result['status'] == console['status'] == 'PASS_M193C_PRIVATE_STAGE_ONLY' and outer['exit_code'] == 0,
         'actual outer completed status')
    need(result['error'] is None and result['finalization_errors'] == [] and console['error'] is None and console['finalization_errors'] == [], 'terminal errors')
    for v in console['files'].values():
        ref(v)
    same_ref(console['files']['artifact_index'], result['artifact_index'])
    same_ref(console['files']['derivative_admission'], result['derivative_admission'])
    need(ref(console['files']['result']) == OUT / 'result.json', 'stdout result identity')
    release_sha = result['execution_release']['sha256']
    def command(stage, request=None):
        tokens = {'ACTUAL_EXECUTION_RELEASE_SHA256': release_sha}
        if request:
            tokens['ACTUAL_GRID_REQUEST_SHA256' if stage == 'grid_reader' else 'ACTUAL_DERIVATIVE_REQUEST_SHA256'] = request['sha256']
        return [tokens.get(t,t) for t in release['commands'][stage]]
    need(result['command'] == outer['command'] == command('owner'), 'released/observed owner argv')
    need(result['sources_before'] == result['sources_after'] == release['source_bindings'], 'owner source before/after')
    need(result['inputs_before'] == result['inputs_after'] == release['inputs'], 'owner input before/after')
    source_map(release['source_bindings'])
    for v in release['inputs']:
        ref(v)
    ref(release['reader_runtime'])
    build = read(result['build'])
    need(build['status'] == 'COMPLETE_COMPILED_TESTS_ONLY' and build['error'] is None and build['finalization_errors'] == [], 'actual build prerequisite')
    for name in ('compiler_artifact','test_executable','compiler_log','test_listing','driver','execution_release'):
        ref(build[name])
    worker = read(result['worker_result'])
    need(worker['status'] == 'COMPLETE_PRIVATE_CHILD_OUTPUTS_UNVERIFIED' and worker['unvisited'] == [] and
         worker['command'] == command('worker') and worker['execution_release'] == result['execution_release'] and
         worker['error'] is None and worker['finalization_errors'] == [], 'complete actual worker')
    need([r['stage'] for r in worker['stages']] == list(literal['STAGES']), 'exact stage order')
    summary['observations'] = [observation(result['enclosing_job'], command('worker'), 'enclosing-worker')]
    values, launches = {}, {}
    previous_end = 0
    for row in worker['stages']:
        stage = row['stage']
        launch = read(row['launch'])
        need(launch['schema'] == 'm193c-campaign-child-launch-v1' and launch['stage'] == stage and
             launch['status'] == 'COMPLETE_CHILD_EXIT_ZERO' and launch['error'] is None and
             launch['command'] == command(stage,row['request']), 'actual stage record ' + stage)
        same_ref(launch['log'], launch['observation']['log'])
        summary['observations'].append(observation(launch['observation'],launch['command'],stage))
        need(previous_end <= launch['started_monotonic_ns'] <= launch['ended_monotonic_ns'], 'stage monotonic sequence')
        previous_end = launch['ended_monotonic_ns']
        value = read(row['result'])
        need(value['error'] is None and value['finalization_errors'] == [], 'stage final errors')
        values[stage], launches[stage] = value,launch
        if row['request']:
            req = read(row['request'])
            same_ref(value['request'],row['request'])
            predecessor = worker['stages'][0 if stage == 'grid_reader' else 2]
            for key, expected in (('producer_result',predecessor['result']),('producer_launch',predecessor['launch']),('build',release['build'])):
                same_ref(req[key], expected)
                same_ref(value[key], expected)
            actual_argv = value['command'] if stage == 'grid_reader' else value['invocation']['orig_argv']
            need(actual_argv == launch['command'], 'reader exact invocation')
        if stage == 'derivative_producer':
            test_log(launch)
    grid, gr, deriv, dr = (values[k] for k in literal['STAGES'])
    need(grid['status'] == 'COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED' and gr['status'] == 'PASS_GRID_ADAPTER_PRIVATE_ONLY' and
         deriv['status'] == 'COMPLETE_PRIVATE_DERIVATIVE_PRODUCTS_UNVERIFIED' and dr['status'] == 'PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY', 'stage scopes')
    for v in (grid, gr):
        need(v['sources_before'] == v['sources_after'] and v['inputs_before'] == v['inputs_after'], 'producer/reader closure')
        source_map(v['sources_before'])
        for name, value in v['inputs_before'].items():
            ref(value if 'path' in value else dict(path=name, **value))
    need(gr['sources_before'] == release['source_bindings'] == dr['invocation']['source_bindings'], 'independent source set')
    need(grid['active_launch'] is None and grid['failed_launch'] is None and gr['active_child'] is None, 'no pending/refused stage')
    need(len(grid['entries']) == len(gr['cases']) == 10, 'ten actual cases')
    summary['grid_launches'] = []
    plan_launches, render_launches = [], []
    for ordinal, entry in enumerate(grid['entries']):
        need(entry['ordinal'] == ordinal and entry['id'] == literal['CASES'][ordinal], 'literal producer case')
        for phase, dest in (('plan',plan_launches),('render',render_launches)):
            launch = read(entry[phase+'_launch'])
            need(launch['ordinal'] == ordinal and launch['phase'] == phase and launch['status'] == 'COMPLETE_CHILD_EXIT_ZERO' and launch['error'] is None, 'grid phase identity')
            need(launch['environment']['STREHL_M193C_GRID_CASE'] == entry['id'] and
                 launch['environment']['STREHL_M193C_GRID_MODE'] == phase, 'actual grid environment')
            same_ref(launch['executable'],build['test_executable'])
            same_ref(launch['log'],launch['observation']['log'])
            test_log(launch)
            summary['grid_launches'].append(observation(launch['observation'],launch['command'],f'{ordinal:02}-{phase}'))
            dest.append(launch)
    component = read(grid['precision']['launch'])
    test_log(component)
    summary['grid_launches'].append(observation(component['observation'],component['command'],'precision-component'))
    ordered = plan_launches+[component]+render_launches
    need(all(a['ended_monotonic_ns'] <= b['started_monotonic_ns'] for a,b in zip(ordered,ordered[1:])), 'ten plans then precision then ten renders')
    need(launches['grid_producer']['started_monotonic_ns'] <= ordered[0]['started_monotonic_ns'] and
         ordered[-1]['ended_monotonic_ns'] <= launches['grid_producer']['ended_monotonic_ns'], 'nested grid interval containment')
    controls = read(gr['controls'])
    need(controls['status'] == 'PASS_GRID_READER_CONTROLS' and controls['error'] is None and controls['counts'] == {'total':45,'rejected':35,'valid':10}, '45 retained controls')
    need(len(controls['checks']) == len({r['id'] for r in controls['checks']}) == 45, 'distinct45')
    for row in controls['checks']:
        if row['status'] == 'PASS_EXPECTED_REFUSAL':
            need(row['observed']['type'] == 'Refusal' and row['observed']['boundary'] == row['expected_boundary'] and row['observed']['message'], 'named semantic refusal')
        else:
            need(row['status'] == 'PASS_VALID_COMPANION' and row['observed'] is None and row['expected_boundary'] is None, 'actual valid companion')
    summary['grid_controls'] = controls['checks']
    summary['cases'] = []
    all_pixel_ids = []
    all_products = []
    for ordinal,(entry,case_ref) in enumerate(zip(grid['entries'],gr['cases'])):
        case = read(case_ref)
        need(case['status'] == 'PASS_PRIVATE_CASE' and case['id'] == literal['CASES'][ordinal] and type(case['ordinal']) is int and case['ordinal'] == ordinal, 'actual independent case')
        for key in ('plan','receipt','tiff'):
            same_ref(case[key],entry[key])
        plan,receipt = read(entry['plan']),read(entry['receipt'])
        need(receipt['plan'] == plan and receipt['plan_bytes'] == entry['plan']['bytes'] and receipt['plan_sha256'] == entry['plan']['sha256'] and
             receipt['error'] is None and receipt['secondary_errors'] == [], 'plan-to-receipt bytes')
        same_ref(receipt['output'],entry['tiff'])
        need(case['observer'] == receipt['source'], 'observer actual source association')
        nframes = 1 if ordinal in (5,6,7,8) else 9
        need(case['observer']['attempts'] == [1]*nframes and len(case['observer']['records']) == nframes and
             case['observer']['optional_counts'] == ([1]*nframes if ordinal == 2 else [0]*nframes) and
             case['observer']['optional_hooks'] == (9 if ordinal in (2,3) else 0), 'actual observer choice/power')
        actual,pixels = tiff(entry['tiff'])
        need(actual['shape'] == case['tiff_evidence']['shape'] and actual['pixel_sha256'] == case['tiff_evidence']['pixel_sha256'], 'independent TIFF strip read')
        score=case['score']
        need(len(score['rows']) == 32 and [row['pair_index'] for row in score['rows']] == list(range(32)), 'all32 pair rows')
        def codes(xy):
            x,y=xy
            need(type(x) is int and type(y) is int and 0<=x<actual['shape'][1] and 0<=y<actual['shape'][0], 'retained sample position')
            return list(struct.unpack_from('<HHH',pixels,6*(y*actual['shape'][1]+x)))
        for row in score['rows']:
            xy = row['output_xy'] if ordinal == 9 else row['r_xy']
            need(codes(xy) == row['rgb_u16'], 'actual RGB sample codes')
            if ordinal == 9:
                need(max(abs(a-b) for a,b in zip(row['rgb_dn'],(1800,2300,2900)))<=.125, 'constant preservation')
            else:
                need(codes(row['g1_xy'])[1] == row['g1_u16'] and all(0<c<65535 for c in row['rgb_u16']+[row['g1_u16']]), 'paired distinct measured sites')
                need(max(map(abs,row['axis_errors_dn']))<=2.75 and row['paired_error_native']<=.1, 'retained fixed pair limits')
        if ordinal in (6,8):
            need(score['expectation']=='fault-consistent' and max(r['correct_u_error_native'] for r in score['rows'])>1, 'actual wrong-map power')
        if ordinal == 9:
            need(score['coordinate_inversion']=='REFUSED_RANK_ZERO', 'constant cannot claim coordinates')
        actual['id']=entry['id']
        actual['score']={k:v for k,v in score.items() if k!='rows'}
        summary['cases'].append(actual)
        all_pixel_ids.append(tuple(actual['identity']))
        all_products.append(ref(entry['tiff']))
    need(summary['cases'][1]['file_sha256']==summary['cases'][2]['file_sha256']==summary['cases'][3]['file_sha256'], 'actual off/count/placebo bytes')
    need(summary['cases'][5]['file_sha256']==summary['cases'][7]['file_sha256'] and summary['cases'][6]['file_sha256']!=summary['cases'][5]['file_sha256'] and
         summary['cases'][8]['file_sha256']!=summary['cases'][5]['file_sha256'], 'actual faults and restored byte identity')
    prec = read(gr['precision'])
    same_ref(prec['witness'],grid['precision']['result'])
    witness=read(prec['witness'])
    need(prec['status']=='PASS_LITERAL_KERNEL_PRECISION' and len(prec['samples'])==3712 and len(witness['cases'])==10, 'complete precision read')
    counts=collections.Counter()
    cursor=0
    live=collections.Counter()
    max_error=0
    for ordinal,child_ref in enumerate(witness['cases']):
        child=read(child_ref)
        entry=grid['entries'][ordinal]
        need(child['plan']==read(entry['plan']) and child['plan_sha256']==entry['plan']['sha256'] and child['plan_bytes']==entry['plan']['bytes'], 'precision actual plan')
        nframes=1 if ordinal in (5,6,7,8) else 9
        originals=[1] if nframes==1 else list(range(9))
        need(len(child['rows'])==nframes*64, 'precision per-case population')
        for i,a in enumerate(child['rows']):
            s=prec['samples'][cursor];cursor+=1
            local=i//64;pair=(i%64)//2;channel='R' if i%2==0 else 'G1'
            for k,v in dict(case_ordinal=ordinal,local_index=local,original_index=originals[local],pair_index=pair,channel=channel).items():
                need(type(s[k]) is type(v) and s[k]==v, 'precision ordered independent key')
                if k!='case_ordinal':need(a[k]==v, 'precision actual key')
            for key, sourcekey in [('modeled_bits','sample_f32_bits'),('black_added_bits','black_restored_f32_bits'),('modeled_f32','sample_f32_dn'),('black_added_f32','black_restored_f32_dn'),('rounded_u16','rounded_u16'),('sample_native_xy','sample_native_xy')]:
                need(s[key]==a[sourcekey], 'actual/independent precision '+key)
            need(a['actual_warp_u16']==s['rounded_u16'], 'actual full warp code')
            need(struct.unpack('<I',struct.pack('<f',s['modeled_f32']))[0]==s['modeled_bits'] and
                 struct.unpack('<I',struct.pack('<f',s['black_added_f32']))[0]==s['black_added_bits'], 'actual f32 value/bit association')
            need(abs(s['quantization_error_dn'])<=1.953125+1e-7 and all(math.isfinite(s[k]) for k in ('f64','modeled_f32','error_dn','quantization_error_dn')), 'retained quantization envelope')
            max_error=max(max_error,abs(s['error_dn']))
            xy=s['sample_native_xy']
            live['integer' if all(v==math.floor(v) for v in xy) else 'fractional']+=1
            t=child['plan']['track'][s['original_index']]['source_generation_pull']
            live['positive_imaginary']+=int(t['a_im']>0);live['negative_imaginary']+=int(t['a_im']<0)
            live['positive_translation']+=int(t['b_re']>0);live['negative_translation']+=int(t['b_re']<0)
            need(s['source_sha256']==child['source']['records'][local]['sha256_u16_le'], 'actual per-frame source digest')
            counts[ordinal]+=1
    need(cursor==3712 and dict(live)==prec['liveness'] and all(v>0 for v in live.values()) and max_error==prec['maximum_gather_error_dn'], 'precision liveness and complete maximum')
    summary['precision']={k:v for k,v in prec.items() if k!='samples'}
    summary['precision']['case_counts']=dict(counts)
    for group,expected in [('source',literal['DERIVATIVE_SOURCE_IDS']),('reader',literal['DERIVATIVE_READER_IDS'])]:
        rows=dr['checks'][group]
        need(tuple(r['id'] for r in rows)==expected and all(r['pass'] is True and type(r['evidence']) is dict for r in rows), 'literal derivative '+group)
    need(dr['checks']['source']==deriv['checks'], 'actual source32 association')
    summary['derivative_checks']=dr['checks']
    summary['derivative_outputs']=[]
    for key,sites in [('affine',54),('signed_border',660)]:
        row=dr['outputs'][key]
        same_ref(row['tiff'],deriv['outputs'][key])
        actual,pixels=tiff(row['tiff'])
        need(actual['shape']==row['shape']==[22,30,3] and actual['pixel_sha256']==row['pixel_sha256_u16_le'] and
             row['compared_sites']==sites and type(row['max_code_error']) is int and row['max_code_error']<=1, 'actual derivative TIFF association')
        actual.update(compared_sites=sites,max_code_error=row['max_code_error'],id=key)
        summary['derivative_outputs'].append(actual)
        all_pixel_ids.append(tuple(actual['identity']));all_products.append(ref(row['tiff']))
    need(len(set(all_pixel_ids))==12 and len(set(all_products))==12, '12 actual file identities')
    need([ref(v) for v in result['products']]==[ref(v) for v in worker['products']]==all_products, 'all actual producer products')
    product_tree={p.resolve() for d in (OUT/'worker/grid',OUT/'worker/derivative') for p in d.rglob('*') if p.is_file() and p.suffix.lower() in ('.tif','.tiff')}
    need(product_tree==set(all_products), 'complete producer TIFF set')
    gate=read(result['derivative_admission'])
    need(set(gate)=={'schema','status','build','private_result','independent_read','error','finalization_errors'} and
         gate['schema']=='m193c-derivative-private-admission-v1' and gate['status']=='PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY' and gate['error'] is None and gate['finalization_errors']==[], 'actual canonical gate')
    same_ref(gate['build'],result['build']);same_ref(gate['private_result'],worker['stages'][2]['result']);same_ref(gate['independent_read'],result['derivative_read'])
    idx=read(result['artifact_index'])
    for v in idx['files']:ref(v)
    files={p.resolve() for p in OUT.rglob('*') if p.is_file()}
    indexed={ref(v) for v in idx['files']}
    need(len(indexed)==len(idx['files'])==idx['file_count'] and indexed | {OUT/'result.json',OUT/'artifact-index.json'}==files, 'complete retained index')
    need(sum(v['bytes'] for v in idx['files'])==idx['retained_bytes'], 'index retained bytes')
    snapshots=[]
    for v in idx['files']:
        p=ref(v)
        if p.parent.name=='sources':
            matches=[name for name,b in release['source_bindings'].items() if b['sha256']==v['sha256'] and b['bytes']==v['bytes']]
            need(len(matches)==1,'declared snapshot source identity')
            snapshots.append(dict(snapshot=v['path'],source=matches[0]))
    final=console['work_through_final_checks']; job=result['enclosing_job']['job_accounting']
    need(final['observed_child_cpu_seconds']==job['total_cpu_100ns']/1e7 and
         final['cpu_seconds']==job['total_cpu_100ns']/1e7+final['owner_or_worker_cpu_seconds'], 'single encompassing CPU accounting')
    need(final['cpu_seconds']<=600 and final['wall_seconds']<=1200 and final['artifact_bytes']<=128*(1<<20) and
         outer['elapsed_wall_seconds']<=1200 and final['artifact_bytes']==sum(p.stat().st_size for p in files), 'terminal limits and complete retained bytes')
    need(result['work']['cpu_seconds']==141+result['work']['owner_or_worker_cpu_seconds'] and result['work']['cpu_seconds']<=final['cpu_seconds'], 'prepublication scope')
    summary.update(status='COMPLETE_READ_ONLY_EVIDENCE_AUDIT',source_count=len(release['source_bindings']),input_count=len(release['inputs']),
                   producer_source_count=len(grid['sources_before']),producer_input_count=len(grid['inputs_before']),
                   snapshots=snapshots,index_count=len(indexed),retained_file_count=len(files),retained_bytes=final['artifact_bytes'],
                   final_work=final,prepublication_work=result['work'],outer_wall_seconds=outer['elapsed_wall_seconds'],
                   grid_work=gr['work'],derivative_work=dr['invocation']['work'])
    # Final file recheck includes every source, input, executable and indexed file actually used.
    for p,expected in checked.items():
        need(digest(p)==expected,'post-read stable bytes: '+str(p))
    summary['distinct_bound_files_rehashed']=len(checked)


try:
    run()
except Exception:
    summary['status']='READ_ONLY_AUDIT_EXCEPTION'
    summary['errors'].append(traceback.format_exc())
finally:
    REPORT.write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('status','errors')},sort_keys=True))
