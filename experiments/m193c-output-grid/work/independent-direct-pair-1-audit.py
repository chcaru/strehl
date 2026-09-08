"""Saved evidence only. Never import a subject, decode an image or call a registrar.
Prospective falsifiers: missing/reordered pair, inverted star direction, changed
feature association/split, mismatched observer signature, dropped refusal, false
bridge/component, changed source or detached terminal receipt. Historical chain
is delegated to the pinned completed coverage audit, not reconstructed here.
Execution requires root's actual terminal notice and external outcome digests.
"""
import argparse
from decimal import Decimal as D
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
OUT = HERE / "direct-pair-1"
ORIGINAL = list(range(0, 105, 13))
EDGES = [(0,1),(0,2),(0,4),(0,5),(1,2),(1,3),(1,5),(2,3),(2,4),
         (2,5),(2,6),(3,4),(3,5),(3,7),(4,5),(4,6),(4,8),(5,6),
         (5,7),(5,8),(6,7),(6,8),(7,8)]
IDS = ['geometry-0','geometry-2','observer-null','identity',
       'complementary-refusal','association-destroyer-restored','blob-sha-refusal-restored']
CODE = 'UNMEASURED_INPUT_REGISTRATION_INADEQUATE'
OLD = CODE + ': too few total mutual landmarks'
HISTORY = 'f5372a6fc28f9a0d34cc37356374beeca266ac5539d5fb93d3d1f2ff1b7c979a'
USED = {}
GAPS = []

def need(ok, why):
    if not ok: raise ValueError(why)

def integer(x):
    return type(x) is int

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def unique(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,'duplicate JSON key'); result[key]=value
    return result

def strict(raw):
    value=json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda x:need(False,'nonfinite JSON'))
    def finite(x):
        if type(x) is float: need(math.isfinite(x),'overflow JSON')
        elif isinstance(x,dict):
            for v in x.values(): finite(v)
        elif isinstance(x,list):
            for v in x: finite(v)
    finite(value)
    return value

def path(ref):
    return (ROOT / ref['path']).resolve()

def file(p,expected=None):
    p=Path(p).resolve(); need(p.suffix.lower()!='.arw','no RAW reads')
    need(p.stat().st_size<=200_000_000,'bounded file')
    h=hashlib.sha256(); size=0
    with p.open('rb') as stream:
        while chunk:=stream.read(1<<20): h.update(chunk); size+=len(chunk)
    ref=dict(path=str(p),sha256=h.hexdigest(),bytes=size)
    if expected is not None:
        need(set(expected)=={'path','sha256','bytes'} and integer(expected['bytes']) and
             path(expected)==p and all(ref[k]==expected[k] for k in ('bytes','sha256')),'file association')
    need(str(p) not in USED or USED[str(p)]==ref,'conflicting consumed file')
    USED[str(p)]=ref
    return ref

def read(ref):
    file(path(ref),ref); need(ref['bytes']<=8*(1<<20),'bounded JSON')
    raw=path(ref).read_bytes(); need(sha(raw)==ref['sha256'],'same parsed bytes')
    return strict(raw)

def actual(p):
    return read(file(p))

def same(a,b):
    return path(a)==path(b) and all(a[k]==b[k] for k in ('bytes','sha256'))

def saved(p,value,complete):
    if p.exists(): need(actual(p)==value,'persisted record association')
    else:
        need(not complete,'missing complete artifact'); GAPS.append(str(p))

def planned():
    result=[]
    for i,j in EDGES:
        a,z=(5,i if j==5 else j) if 5 in (i,j) else (i,j)
        result.append(dict(id=f'pair-{i}-{j}',reference=a,source=z,local_span=j-i,
            star=5 in (i,j),reference_original=ORIGINAL[a],source_original=ORIGINAL[z]))
    return result

def components(edges):
    parent=list(range(9))
    def find(i):
        while parent[i]!=i: i=parent[i]
        return i
    for a,b in edges: parent[find(a)]=find(b)
    return sorted([sorted(i for i in range(9) if find(i)==r)
                   for r in set(find(i) for i in range(9))])

def topology(records,g):
    edges=[[r['pair']['reference'],r['pair']['source']] for r in records
           if r['outcome']['status']=='RETURNED']
    groups=components(edges)
    bridges=[e for i,e in enumerate(edges) if len(components(edges[:i]+edges[i+1:]))>len(groups)]
    need(g['anchor_local']==4 and g['anchor_original']==52 and
         g['reference_local']==5 and g['reference_original']==65,'distinct graph gauges')
    need(g['edges']==edges and g['bridges']==bridges and len(g['nodes'])==9,'edge-removal bridges')
    for i,node in enumerate(g['nodes']):
        group=next(c for c in groups if i in c)
        need(node==dict(local=i,original=ORIGINAL[i],component=group,
             anchor_connected=4 in group,degree=sum(i in e for e in edges),
             cycle_participation=any(i in e and e not in bridges for e in edges)),'union-find node')
    return dict(components=groups,edges=edges,bridges=bridges,cycle_rank=len(edges)-9+len(groups))

def controls(rows):
    need([r['id'] for r in rows]==IDS and all(r['passed'] is True for r in rows),'seven controls')
    e={r['id']:r['evidence'] for r in rows}; o=e['observer-null']
    need(o['off']==o['count']==o['placebo']==e['geometry-0'],'actual observer equality')
    need(o['canonical_signature_sha256']=={k:sha(canonical(o[k])) for k in ('off','count','placebo')},'canonical observer hashes')
    frozen=actual(ROOT/'experiments/M193-cover-overlap/fixtures.json')['synthetic_overlap']['sources']
    for name,w in zip(IDS[:2],frozen[1:]):
        g=e[name]
        need(g['status']=='RETURNED' and g['error'] is None and g['transform']==w['source_to_reference_q32'] and dict(g['metrics'],reference=False)==w['registration'] and g['guard']==w['valid_center_guard_q8'],'fixture oracle')
    need(e['geometry-0']['transform']!=e['geometry-2']['transform'],'distinct associations')
    identity=e['identity']; bad=e['complementary-refusal']; s=e['association-destroyer-restored']
    need(identity['transform']==dict(a=1<<32,b=0,tx=0,ty=0) and identity['metrics']['heldout_rms_reference_px']=='0.000000000','identity')
    need(bad['status']=='REGISTRATION_REFUSED' and bad['error']['code']==CODE and bad['error']['type']=='ContractError','specific refusal')
    need(s['first']==s['restored']==e['geometry-0']['transform'] and s['wrong']==e['geometry-2']['transform'],'swapped/restored')
    blob=e['blob-sha-refusal-restored']
    need(blob==dict(exception='authenticated same TIFF blob',refused_decoder_calls=0,restored_decoder_calls=1),'decoder auth call power')

def landmarks(o,features,p):
    marks=o['landmarks']; status=o['status']; order=[]; held=[]
    need(status in ('RETURNED','REGISTRATION_REFUSED') and len(marks)<=256,'bounded matches')
    coords=[set(map(tuple,features[p[k]]['coordinates_q8'])) for k in ('reference','source')]
    for i,m in enumerate(marks):
        rx,ry=m['reference_q8']; sx,sy=m['source_q8']
        need(all(integer(x) for x in (rx,ry,sx,sy)) and (rx,ry) in coords[0] and (sx,sy) in coords[1] and m['split']==('holdout' if i%2 else 'calibration'),'point/split association')
        need(len(m['digest'])==64 and len(bytes.fromhex(m['digest']))==32,'landmark digest')
        order.append((m['digest'],ry,rx,sy,sx))
        need(type(m['inlier']) is bool if status=='RETURNED' else m['inlier'] is None,'inlier type/scope')
        if i%2 and m['inlier']: held.append(m)
    need(order==sorted(order),'actual digest order')
    if status=='RETURNED':
        m=o['metrics']
        need(all(integer(m[k]) for k in ('mutual_match_count','calibration_count','holdout_count','holdout_inlier_count')),'typed match counts')
        need(o['error'] is None and m['mutual_match_count']==len(marks) and m['calibration_count']==(len(marks)+1)//2 and m['holdout_count']==len(marks)//2 and m['holdout_inlier_count']==len(held)>=12,'match counts')
        need(integer(m['calibration_inlier_count']) and 12<=m['calibration_inlier_count']<=m['calibration_count'],'fit count bounds')
        box={k:[min(m[k][0] for m in held),min(m[k][1] for m in held),max(m[k][0] for m in held),max(m[k][1] for m in held)] for k in ('reference_q8','source_q8')}
        need(o['heldout_bbox_q8']==box,'saved accepted bounds')
    else:
        need(o['transform'] is o['metrics'] is o['guard'] is o['heldout_bbox_q8'] is None and o['error']['type']=='ContractError' and o['error']['code']==CODE and o['error']['message'].startswith(CODE+': ') and 'register_to_reference' in o['error']['traceback'],'scientific refusal')
    return len(marks)

def main():
    parser=argparse.ArgumentParser()
    for k in ('plan','result','outer','console','exit'): parser.add_argument('--'+k+'-sha256',required=True)
    args=parser.parse_args(); refs={}
    names=dict(plan=HERE/'direct-pair-plan-1.json',result=OUT/'result.json',
        **{k:HERE/f'work/direct-pair-1-{k}.json' if k=='outer' else HERE/f'work/direct-pair-1-{k}.txt' for k in ('outer','console','exit')})
    for k,p in names.items():
        refs[k]=file(p); need(refs[k]['sha256']==getattr(args,k+'_sha256'),'external '+k)
    plan,result,outer=(read(refs[k]) for k in ('plan','result','outer'))
    console=strict(path(refs['console']).read_bytes().splitlines()[-1]); code=int(path(refs['exit']).read_bytes().strip())
    need(plan['schema']=='m193c-direct-pair-plan-v1' and result['schema']=='m193c-direct-pair-run-v1','run schema')
    need(set(outer)==set('scope command plan_sha256 exit_code elapsed_wall_seconds admissible_parent_exit'.split()) and outer['plan_sha256']==refs['plan']['sha256'],'closed actual root outer')
    history=read(plan['coverage']['audit']); need(plan['coverage']['audit']['sha256']==HISTORY and
        history['status']=='PASS_SAVED_COVERAGE_OUTCOME_AUDIT','committed historical audit')
    for k in ('result','release','outer','console','exit'):
        need(same(history['external'][k],plan['coverage'][k]),'coverage association')
        ref=plan['coverage'][k]; file(path(ref),ref)
    historical=read(plan['coverage']['result'])
    prior=read(plan['prior_work']); base=history['actual_final_accounting']['work_observed_or_lower_bound']
    for k,extra in dict(cpu_seconds=20,wall_seconds=30,file_bytes=1<<20,metadata_bytes=1<<20).items():
        need(D(str(prior[k]))==D(history['next_wall_seconds'] if k=='wall_seconds' else str(base[k]))+extra,'no refunded carry')
    for p,binding in plan['source_bindings'].items(): file(ROOT/p,dict(path=p,**binding))
    file(path(plan['python_executable']),plan['python_executable'])
    command=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['parent']]
    need(result['command']==outer['command']==command and same(result['plan'],refs['plan']) and
         outer['exit_code']==code and integer(outer['exit_code']) and outer['admissible_parent_exit'] is (code==0),'actual parent launch')
    need(console['status']==result['status'] and Path(console['result']).resolve()==OUT/'result.json' and
         console['error']==result['error'] and console['finalization_errors']==result['finalization_errors'],'terminal result')
    complete=result['status']=='COMPLETE_DIRECT_PAIR_SUPPORT_ONLY'
    worker=read(result['worker_result']) if result['worker_result'] else None
    request=read(result['request']) if result['request'] else None; schedule=planned()
    need(result['prior_work']==prior,'recorded prior carry')
    if request is not None:
        need(request['pairs']==schedule and request['rows']==historical['admitted_inputs'],'fixed requested population')
        need([(r['ordinal'],r['original_index']) for r in request['rows']]==list(enumerate(ORIGINAL)) and all(integer(r['ordinal']) and integer(r['original_index']) for r in request['rows']),'typed nine inputs')
        for row in request['rows']: file(path(row['tiff']),row['tiff'])
        parent_plan=actual(OUT/'pair-plan.json'); need(parent_plan['pairs']==schedule and parent_plan['rows']==request['rows'],'persisted parent plan')
    else: need(not complete and worker is None,'pre-request refusal')
    pair_summary=[]; graph=None; control_summary=None; feature_summary=[]
    if worker is not None:
        wdir=OUT/'worker'; saved(wdir/'pair-plan.json',dict(rows=request['rows'],pairs=schedule),complete)
        need(worker['schema']=='m193c-direct-pair-worker-v1' and worker['request']==result['request'] and
             worker['plan']==result['plan'] and worker['source_bindings']==result['source_bindings']==plan['source_bindings'],'worker associations')
        if complete: need(worker['sources_unchanged'] is True and result['sources_unchanged'] is True,'final source checks')
        cr=worker['controls']
        need([r['id'] for r in cr]==IDS[:len(cr)] and len(cr)<=7,'actual control prefix')
        for r in cr: saved(wdir/('control-'+r['id']+'.json'),r,complete)
        control_summary=dict(ids=[r['id'] for r in cr],passed=[r['passed'] for r in cr])
        if len(cr)==7 and all(r['passed'] is True for r in cr):
            controls(cr); saved(wdir/'controls.json',cr,complete)
        else: need(not complete and worker['error'] is not None,'retained control refusal')
        features=worker['features']
        need(len(features)<=9,'bounded feature prefix')
        for i,f in enumerate(features):
            saved(wdir/f'feature-{i}.json',f,complete)
            need(f['original_index']==ORIGINAL[i] and integer(f['original_index']) and
                 same(f['tiff'],request['rows'][i]['tiff']),'feature input')
            if f['status']=='RETURNED':
                need(integer(f['count']) and 0<f['count']<=1024 and len(f['coordinates_q8'])==f['count'] and
                     f['error'] is None,'feature count')
                for h in ('keys_sha256','descriptors_sha256'): need(len(bytes.fromhex(f[h]))==32,'feature hash')
                need(all(type(x) is list and len(x)==2 and all(integer(v) for v in x) for x in f['coordinates_q8']),'typed feature coordinates')
            else: need(f['status']=='FEATURE_UNAVAILABLE' and f['error']['code']==CODE,'feature refusal')
            summary={k:f.get(k) for k in ('original_index','status','count','descriptors_sha256','keys_sha256')}
            summary['error']=None if f['error'] is None else {k:f['error'][k] for k in ('code','message')}
            feature_summary.append(summary)
        for i,row in enumerate(worker['pairs']):
            need(i<23 and row['pair']==schedule[i],'ordered pair')
            saved(wdir/(schedule[i]['id']+'.json'),row,complete)
            p,o=row['pair'],row['outcome']; a,z=p['reference'],p['source']; count=None
            need(all(integer(p[k]) for k in ('reference','source','local_span','reference_original','source_original')) and type(p['star']) is bool,'typed pair identity')
            missing=[j for j in (a,z) if features[j]['status']!='RETURNED']
            if missing: need(o==dict(status='FEATURE_UNAVAILABLE',unavailable=missing),'unavailable propagation')
            else: count=landmarks(o,features,p)
            error=o.get('error')
            pair_summary.append(dict(id=p['id'],reference=a,source=z,status=o['status'],matches=count,
                error=None if error is None else {k:error[k] for k in ('type','code','message')}))
        need(worker['unvisited']==list(range(len(worker['pairs']),23)),'exact unvisited suffix')
        if worker['graph'] is not None:
            graph=topology(worker['pairs'],worker['graph'])
            old=next(r for r in worker['pairs'] if r['pair']['id']=='pair-5-8')
            reproduced=(old['outcome'].get('error') or {}).get('message')==OLD
            need(worker['historical_pair_reproduced'] is reproduced and worker['graph']['interpretation_eligible'] is reproduced,'historical ordered call')
            need(worker['graph']['eligibility_reason']==('historical ordered refusal reproduced' if reproduced else 'STOP: resolve changed historical pair outcome before topology interpretation'),'explicit interpretation stop')
            graph['interpretation_eligible']=reproduced
        if worker['runtime_after'] is not None:
            need(worker['runtime_before']==worker['runtime_after']==history['runtime'],'unchanged actual runtime')
    child=result['child']
    wcmd=[] if request is None else [refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else result['request']['sha256'] if x=='ACTUAL_REQUEST_SHA256' else x for x in plan['commands']['worker']]
    if child is not None:
        need(child['command']==wcmd and (worker is None or worker['command']==wcmd),'worker actual argv')
        if (OUT/'worker.log').exists():
            log=file(OUT/'worker.log'); need(child['log_bytes']==log['bytes'],'actual worker log extent')
        else: need(not complete and child['error'] is not None,'pre-log failure')
        need(result['environment']==dict.fromkeys(('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'),'2'),'thread overrides')
        need(result['removed_environment']==sorted(set(result['removed_environment'])),'removed environment record')
    else: need(not complete and worker is None,'pre-child refusal')
    if complete:
        need(code==0 and child['exit_code']==0 and child['error'] is None and child['cleanup_errors']==[] and
             child['terminal_job_accounting'] is True and child['job_accounting']['active_processes']==0 and
             child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and
             result['error'] is worker['error'] is None and result['finalization_errors']==worker['finalization_errors']==[] and
             console['cpu_accounting_complete'] is True and worker['status']==result['status'] and
             len(features)==9 and len(worker['pairs'])==23 and result['unvisited']==[] and result['graph']==worker['graph'],'complete actual population/Job')
    else: need(code!=0 and (result['error'] is not None or result['finalization_errors']),'explicit refusal')
    work=console['work_through_final_checks']
    caps={}
    for k,cap in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8<<20,metadata_bytes=8<<20).items():
        need(D(str(work[k]))>=D(str(prior[k])),'no negative cost/refund')
        caps[k]=D(str(work[k]))-D(str(prior[k]))<=cap
    caps['global']=work['cpu_seconds']<=1200 and work['wall_seconds']<=1800 and work['file_bytes']<=4*(1<<30) and work['metadata_bytes']<=128*(1<<20)
    account=None if child is None else child['job_accounting']
    if account is not None:
        need(integer(account['total_cpu_100ns']) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'actual CPU components')
        caps['child_cpu']=account['total_cpu_100ns']/1e7<=child['limits']['cpu_seconds']
        caps['child_wall']=child['wall_seconds']<=child['limits']['wall_seconds']
        caps['child_committed']=None if child['job_memory'] is None else child['job_memory']['peak_job_memory_used_bytes']<=child['limits']['committed_bytes']
        need(work['cpu_seconds']-prior['cpu_seconds']>=account['total_cpu_100ns']/1e7,'whole Job CPU charged')
    if worker is not None:
        need(worker['work']['snapshot_bytes']==result['work']['snapshot_bytes']==0,'no new snapshot charge')
    if complete: need(all(caps.values()),'complete run caps')
    for ref in list(USED.values()): file(path(ref),ref)
    answer=dict(schema='m193c-saved-direct-pair-audit-v1',status='PASS_SAVED_DIRECT_PAIR_OUTCOME_AUDIT',
        subject_complete=complete,subject_status=result['status'],external=refs,audit_source=file(__file__),
        history=plan['coverage']['audit'],worker_result=result['worker_result'],controls=control_summary,features=feature_summary,pairs=pair_summary,unvisited=list(range(23)) if worker is None else worker['unvisited'],
        graph=graph,actual_final_work=work,next_wall_seconds=str(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),
        job=child,caps=caps,cpu_accounting_complete=console['cpu_accounting_complete'],retention_gaps=GAPS,unique_hashed_files=len(USED),
        scope='Saved outcomes and graph topology; no matching, decode, placement solve, overlap or accuracy claim. Descriptor/key/split digests are producer witnesses; descriptors were not retained for independent reconstruction.')
    raw=json.dumps(answer,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
    need(len(raw)<=32768,'bounded audit stdout'); print(raw.decode())

if __name__=='__main__': main()
