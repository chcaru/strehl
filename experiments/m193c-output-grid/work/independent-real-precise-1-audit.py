"""Saved real AREA8+precise metadata audit. No subject imports or image payloads.
Held before outcome audit; actual run requires root-supplied terminal digests.
Falsifiers: omitted pair/refusal, wrong true flag, unrestored factory, altered
entire private cache record, wrong native lift, duplicate sites called support,
false graph bridge/cycle, detached source/argv/accounting or uncharged bytes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import types
from decimal import Decimal as D

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'real-precise-1'
HELPER=(42893,'4b4736b8a95ef7d347dd2ad98cc66ac4460e1d77d7f735e68f016e8e26912e30')
RUNNER_PIN=(20506, '7f71fa2414f72bd994ff1701d7ae8c39d49005a11f0fb60027622e780c43efa6')
SPEC_PIN=(12083, 'd8e9b7385f229ed8635ee86d50082f96ca837037fb3bb1a223074dd01f9a1a31')
PRIVATE_AUDIT='471c68d50e1cca2804eec32e38756d06b3e0d8db79716de1450fb038ff197b5e'
VERSION='m193c-real-precise-v1'
METHOD='ENTIRE records: immutable n.json_bytes; exact serialized byte equality; no omitted fields or tolerance'
BUDGET=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1<<20,metadata_bytes=1<<20)
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6,enable_precise_upscale=True)
PRIVATE_CACHE=None


def helpers():
    p=HERE/'work/independent-factor-eight-1-audit.py';raw=p.read_bytes()
    if (len(raw),hashlib.sha256(raw).hexdigest())!=HELPER:raise ValueError('held independent helper')
    # Only our own standard-library helper executes; its main is guarded.
    a=types.ModuleType('independent_real_precise_helpers');a.__file__=str(p)
    sys.modules[a.__name__]=a;exec(compile(raw,str(p),'exec'),a.__dict__);a.OUT=OUT
    names=('need integer sha canonical strict path file read actual same saved planned components topology controls landmarks hv image_stat signature coordinate_rows corners corner_pass check_corners near_components site_check residual observed representation lifted_arrays private_features true_rotation_landmarks commissioning all_inventory USED GAPS TIFF_STAT QUAL CODE ORIGINAL ALL_IDS NATIVE_AUDIT Q').split()
    for name in names:globals()[name]=getattr(a,name)
    return a,p


def comparison(got,label,left,right):
    l,r=canonical(left),canonical(right)
    expected=dict(label=label,method=METHOD,equal=l==r,left=dict(bytes=len(l),sha256=sha(l)),right=dict(bytes=len(r),sha256=sha(r)))
    need(got==expected,'entire canonical predicate: '+label)
    return l==r


def witness(w,scope,ordinal,complete=False):
    keys=set('scope ordinal requested_true calls restored error'.split())
    if scope=='real':keys.add('original_index')
    need(set(w)==keys and w['scope']==scope and integer(w['ordinal']) and w['ordinal']==ordinal and w['requested_true'] is True,'fixed scoped factory attempt')
    if scope=='real':need(w['original_index']==ORIGINAL[ordinal],'factory actual original index')
    need(type(w['calls']) is list and len(w['calls'])<=1 and w['restored'] is True,'one call ceiling and final restoration')
    for call in w['calls']:need(call==KWARGS and all(type(call[k]) is type(v) for k,v in KWARGS.items()),'only explicit true constructor flag')
    need(w['error'] is None or (type(w['error']) is str and 'Traceback' in w['error']),'retained factory error')
    if complete:need(len(w['calls'])==1 and w['error'] is None,'completed extraction actual factory')


def baseline(plan):
    global PRIVATE_CACHE
    refs=plan['private_baseline'];need(set(refs)==set('plan result outer console exit audit'.split()),'six private baseline FileRefs')
    historical={k:read(r) if k in ('plan','result','outer','audit') else file(path(r),r) for k,r in refs.items()}
    old,audit,parent=historical['plan'],historical['audit'],historical['result'];worker=read(parent['worker_result'])
    need(refs['audit']['sha256']==PRIVATE_AUDIT and audit['schema']=='m193c-saved-precise-upscale-canonical-audit-v1' and audit['status']=='PASS_SAVED_PRECISE_UPSCALE_CANONICAL_OUTCOME_AUDIT' and audit['subject_complete'] is True and audit['refused_control'] is None and audit['cpu_accounting_complete'] is True,'held completed canonical private authority')
    need(old['schema']=='m193c-precise-upscale-canonical-plan-v1' and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'whole exercised private source closure')
    for k in ('plan','result','outer','console','exit'):need(same(refs[k],audit['external'][k]),'private audit external association')
    need(same(parent['worker_result'],audit['worker_result']) and same(parent['plan'],refs['plan']) and parent['status']==worker['status']=='COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY' and parent['implementation_version']==worker['implementation_version']=='m193c-precise-upscale-canonical-v1','actual audited complete private worker')
    need(parent['sources_unchanged'] is worker['sources_unchanged'] is True and parent['error'] is worker['error'] is None and parent['finalization_errors']==worker['finalization_errors']==[],'historical terminal/source checks')
    final=strict(path(refs['console']).read_bytes().splitlines()[-1]);outer=historical['outer']
    need(final['work_through_final_checks']==audit['actual_final_work'] and final['cpu_accounting_complete'] is True and final['status']==parent['status'] and final['error'] is None and final['finalization_errors']==[],'canonical final accounting association')
    need(outer['exit_code']==0 and type(outer['exit_code']) is int and outer['admissible_parent_exit'] is True and path(refs['exit']).read_bytes().strip()==b'0' and outer['command']==parent['command'] and outer['plan_sha256']==refs['plan']['sha256'],'canonical actual outer/exit')
    need(D(str(parent['prior_work']['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))==D(audit['next_wall_seconds']),'canonical conservative wall')
    need(len(worker['controls'])==7 and all(r['passed'] is True for r in worker['controls']) and [(r['id'],r['passed']) for r in worker['comparison_controls']]==[('whole-record-comparator',True)] and worker['counters']==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5) and len(worker['arms'])==3,'cached complete private population')
    ar=worker['arms'][1];arm=read(ar);fr=arm['feature_record'];f=read(fr)
    need(arm['name']=='precise-true' and arm['enable_precise_upscale'] is True and arm['factory_restored'] is True and arm['constructor_calls']==[KWARGS]*2 and arm['error'] is None and arm['outcome']['status']=='RETURNED' and corner_pass(arm['outcome']['transform']),'audited actual true arm')
    need(path(ar)==HERE/'precise-upscale-canonical-1/worker/precise-true-arm.json' and path(fr)==HERE/'precise-upscale-canonical-1/worker/precise-true-features.json','literal private cache paths')
    PRIVATE_CACHE=dict(arm_ref=ar,features_ref=fr,features=f,outcome=arm['outcome'])
    # The pinned complete private audit owns its earlier failure chain. Recover
    # the original real9/native23 authority without inventing a new population.
    previous=read(old['failed_attempt']['plan']);factor=read(previous['factor_eight_baseline']['plan']);native_refs=factor['native_baseline']
    native={k:read(r) if k in ('plan','result','outer','audit') else file(path(r),r) for k,r in native_refs.items()}
    nold,na=native['plan'],native['audit'];np=native['result'];nw=read(np['worker_result']);nr=read(np['request'])
    need(native_refs['audit']['sha256']==NATIVE_AUDIT and na['status']=='PASS_SAVED_DIRECT_PAIR_OUTCOME_AUDIT' and na['subject_complete'] is True and len(nold['source_bindings'])==170 and all(plan['source_bindings'].get(k)==v for k,v in nold['source_bindings'].items()),'old 170-source closure and complete native audit')
    for k in ('plan','result','outer','console','exit'):need(same(native_refs[k],na['external'][k]),'native external authority')
    need(same(np['worker_result'],na['worker_result']) and np['status']==nw['status']=='COMPLETE_DIRECT_PAIR_SUPPORT_ONLY' and np['sources_unchanged'] is nw['sources_unchanged'] is True and np['error'] is nw['error'] is None and np['finalization_errors']==nw['finalization_errors']==[],'cached complete native outcome')
    need([r['pair'] for r in nw['pairs']]==planned() and all(r['outcome']['status']=='REGISTRATION_REFUSED' for r in nw['pairs']),'all 23 native refusals retained')
    return audit,native_refs,nw,nr


def graph_commission():
    def score(edges):
        groups=components(edges);bridges=[e for i,e in enumerate(edges) if len(components(edges[:i]+edges[i+1:]))>len(groups)]
        return len(groups),len(edges)-9+len(groups),bridges
    need(score([[0,1],[1,2]])==(7,0,[[0,1],[1,2]]),'graph tree is two bridges and zero cycles')
    need(score([[0,1],[1,2],[2,0]])==(7,1,[]),'graph ring positive has one cycle and no bridges')
    need(score([])==(9,0,[]),'graph empty retains all nodes')
    return ['tree_bridges','ring_cycle','empty_nine_nodes']


def control_audit(rows,fixtures):
    need([r['id'] for r in rows]==ALL_IDS[:len(rows)] and 7<=len(rows)<=14,'fixed control prefix')
    for r in rows:need(type(r['passed']) is bool,'typed control outcome')
    controls(rows[:7])
    for r in rows:saved(OUT/'worker'/('control-'+r['id']+'.json'),r,True)
    e={r['id']:r['evidence'] for r in rows};private=None;positive=None;audit=[]
    for row in rows[7:]:
        name=row['id'];v=row['evidence'];site_summary=None;truth_summary=None;comparisons=None
        if set(v)=={'exception'}:
            need(row is rows[-1] and row['passed'] is False and type(v['exception']) is str and 'Traceback' in v['exception'],'retained private exception')
            audit.append(dict(id=name,passed=False,exception=True));break
        if name=='area8-half-ties':
            sums=[31,32,33,95,96,97,64*65535];expected=[[[round(s/64)]*3 for s in sums]]
            need(v['input_channel_sums']==sums and v['expected']==expected,'independent ties-even truth');ok=v['actual']==expected
        elif name=='repeated-block-null':
            need(any(same(v['fixture'],f) for f in fixtures),'repeated fixture ref')
            representation(v['reference'],[2304,3072,3]);representation(v['source'],[3072,2304,3]);hs=v['actual_sha256']
            need(set(hs)=={'original','coarse_reference','expected_rotation','coarse_source'},'null hash keys')
            for h in hs.values():hv(h)
            need(hs['coarse_reference']==v['reference']['coarse_rgb_sha256_u16_le'] and hs['coarse_source']==v['source']['coarse_rgb_sha256_u16_le'],'representation hash association')
            ok=hs['original']==hs['coarse_reference'] and hs['expected_rotation']==hs['coarse_source']
        elif name=='native-rotation-positive':
            private=private_features(v['features'],fixtures);positive=v['outcome']
            site_summary=observed(positive,private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8'])
            check_corners(v['corner_errors'],positive['transform'])
            need(v['literal_truth_q32']==dict(a=0,b=Q,tx=3071*Q,ty=0),'independent rotation truth')
            need(same(v['cached_true_arm'],PRIVATE_CACHE['arm_ref']) and same(v['cached_true_features'],PRIVATE_CACHE['features_ref']),'private cached true FileRefs')
            comparisons=v['canonical_comparisons'];need(len(comparisons)==2,'both complete positive records')
            equalities=[comparison(comparisons[0],'entire-private-feature-record-vs-cached-true',private,PRIVATE_CACHE['features']),comparison(comparisons[1],'entire-private-outcome-vs-cached-true',positive,PRIVATE_CACHE['outcome'])]
            need(len(v['precise_factories'])==2,'two completed private true factories')
            for i,w in enumerate(v['precise_factories']):witness(w,'private',i,True)
            ok=positive['status']=='RETURNED' and len(positive['landmarks'])>=24 and corner_pass(positive['transform']) and all(equalities)
            if positive['landmarks']:truth_summary=true_rotation_landmarks(positive['landmarks'])
        elif name=='native-two-pixel-map-destroyer':
            need(positive is not None and v['baseline']==positive['transform'] and v['qualification']==QUAL and v['added_native_px']==2,'two-pixel baseline')
            need(v['mutated']==dict(positive['transform'],tx=positive['transform']['tx']+2*Q),'tx mutation only')
            check_corners(v['corner_errors'],v['mutated']);ok=not corner_pass(v['mutated'])
        elif name=='centre-offset-destroyer':
            need(private is not None and same(v['features'],e['native-rotation-positive']['features']) and v['active_omission_q8']==896,'same private features')
            o=v['outcome'];site_summary=observed(o,[[8*x for x in p] for p in private['reference']['coarse_coordinates_q8']],[[8*x for x in p] for p in private['source']['coarse_coordinates_q8']],missing=True)
            check_corners(v['corner_errors'],o['transform']);ok=o['status']=='RETURNED' and not corner_pass(o['transform'])
        elif name=='native-rotation-restored':
            o=v['outcome'];site_summary=observed(o,private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8']);check_corners(v['corner_errors'],o['transform'])
            comparisons=v['canonical_comparisons'];need(len(comparisons)==2,'both complete restored outcomes')
            equalities=[comparison(comparisons[0],'entire-restored-outcome-vs-fresh-positive',o,positive),comparison(comparisons[1],'entire-restored-outcome-vs-cached-true',o,PRIVATE_CACHE['outcome'])]
            ok=signature(o)==signature(positive) and v['corner_errors']==e['native-rotation-positive']['corner_errors'] and o['status']=='RETURNED' and corner_pass(o['transform']) and all(equalities)
        elif name=='rotation-observer-null':
            for mode in ('off','count','placebo'):observed(v[mode],private['reference']['native_coordinates_q8'],private['source']['native_coordinates_q8'],captured=mode=='count')
            need(v['count']==e['native-rotation-restored']['outcome'],'count reuses restored call')
            expected={k:sha(canonical(signature(v[k]))) for k in ('off','count','placebo')}
            need(v['canonical_signature_sha256']==expected,'canonical observer hashes');ok=len(set(expected.values()))==1 and len(v['count']['landmarks'])>=24
        need(row['passed'] is ok,'saved boolean versus independent predicate: '+name)
        audit.append(dict(id=name,passed=ok,corner_errors=v.get('corner_errors'),captured_landmarks=len(v.get('outcome',{}).get('landmarks',[])),site_summary=site_summary,literal_truth_all_landmarks=truth_summary,canonical_comparisons=comparisons))
        if not ok:need(row is rows[-1],'no continuing after failed control')
    all_pass=len(rows)==14 and all(r['passed'] for r in rows)
    if all_pass:saved(OUT/'worker/controls.json',rows,True)
    else:need(not (OUT/'worker/controls.json').exists(),'no complete control record after failure')
    if private is None and (OUT/'worker/rotation-feature-record.json').exists():private=private_features(file(OUT/'worker/rotation-feature-record.json'),fixtures)
    return dict(all_fourteen_pass=all_pass,rows=[dict(id=r['id'],passed=r['passed']) for r in rows],additive_checks=audit,private_features_present=private is not None,private_counts=None if private is None else {k:private[k]['count'] for k in ('reference','source')},unvisited=ALL_IDS[len(rows):])


def main():
    cpu,wall=time.process_time(),time.perf_counter();parser=argparse.ArgumentParser()
    for k in ('plan','result','outer','console','exit'):parser.add_argument('--'+k+'-sha256',required=True)
    args=parser.parse_args();helper,hpath=helpers();commissioned=commissioning()+graph_commission();refs={}
    names=dict(plan=HERE/'real-precise-plan-1.json',result=OUT/'result.json',outer=HERE/'work/real-precise-1-outer.json',console=HERE/'work/real-precise-1-console.txt',exit=HERE/'work/real-precise-1-exit.txt')
    for k,p in names.items():refs[k]=file(p);need(refs[k]['sha256']==getattr(args,k+'_sha256'),'external actual '+k)
    plan,parent,outer=(read(refs[k]) for k in ('plan','result','outer'))
    console=strict(path(refs['console']).read_bytes().splitlines()[-1]);exit_code=int(path(refs['exit']).read_bytes().strip())
    need(set(plan)==set('schema source_bindings private_baseline prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-real-precise-plan-v1','closed new plan')
    need(set(plan['private_baseline'])==set('plan result outer console exit audit'.split()),'six baseline references')
    need(set(outer)==set('scope command plan_sha256 exit_code elapsed_wall_seconds admissible_parent_exit'.split()) and outer['plan_sha256']==refs['plan']['sha256'],'closed actual outer')
    for relative,binding in plan['source_bindings'].items():file(ROOT/relative,dict(path=relative,**binding))
    for relative,pin in (('real-precise-run.py',RUNNER_PIN),('real-precise-preregister.md',SPEC_PIN)):
        r=file(HERE/relative);need((r['bytes'],r['sha256'])==pin,'held executed '+relative)
    py=file(path(plan['python_executable']),plan['python_executable'])
    audit,native_refs,native_worker,native_request=baseline(plan)
    schedule=planned()
    prior=read(plan['prior_work']);need(plan['preparation_allowance']==BUDGET,'whole preparation allowance')
    for k,extra in BUDGET.items():need(D(str(prior[k]))==D(audit['next_wall_seconds'] if k=='wall_seconds' else str(audit['actual_final_work'][k]))+extra,'exact no-refund carry')
    need(prior==dict(cpu_seconds=530.46875,wall_seconds=626.5200758,file_bytes=3956544489,metadata_bytes=31343843),'literal new carry')
    need(set(plan['commands'])=={'parent','worker'},'two exact commands');base=[py['path'],'-B','-X','faulthandler','-X']
    pc=base+['pycache_prefix='+str(OUT/'parent-cache'),str(HERE/'real-precise-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT)]
    command=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['parent']]
    need(pc==command==parent['command']==outer['command'] and same(parent['plan'],refs['plan']),'independent parent argv')
    need(integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is (exit_code==0),'actual parent exit')
    need(parent['schema']=='m193c-factor-eight-run-v1' and parent['source_bindings']==plan['source_bindings'] and parent['prior_work']==prior and parent['qualification']==QUAL,'parent association')
    need(parent['sources_unchanged'] is True and parent['finalization_errors']==[],'parent final checks')
    need(console['status']==parent['status'] and Path(console['result']).resolve()==OUT/'result.json' and console['error']==parent['error'] and console['finalization_errors']==parent['finalization_errors'],'terminal publication')
    need(parent['request'] is not None and parent['worker_result'] is not None and parent['child'] is not None,'audited branch has worker')
    request=read(parent['request']);worker=read(parent['worker_result'])
    need(set(request)==set('schema plan pairs rows fixtures native_pairs prior_work'.split()) and request['schema']=='m193c-factor-eight-request-v1','closed request')
    need(same(request['plan'],refs['plan']) and request['pairs']==schedule and request['rows']==native_request['rows'] and request['fixtures']==native_request['fixtures'],'same requested population')
    need([(r['ordinal'],r['original_index']) for r in request['rows']]==list(enumerate(ORIGINAL)) and len(request['fixtures'])==5,'literal nine/five population')
    for r in request['rows']:image_stat(r['tiff'])
    for r in request['fixtures']:image_stat(r)
    need(len(request['native_pairs'])==23,'cached native FileRef count')
    for i,r in enumerate(request['native_pairs']):need(path(r)==HERE/'direct-pair-1/worker'/(schedule[i]['id']+'.json') and read(r)==native_worker['pairs'][i],'exact cached pair FileRef')
    need(all(request['prior_work'][k]>=prior[k] for k in prior),'setup carry into request')
    pair_plan=dict(rows=request['rows'],pairs=schedule,native_pairs=request['native_pairs'])
    saved(OUT/'pair-plan.json',pair_plan,True);saved(OUT/'worker/pair-plan.json',pair_plan,True)
    need(worker['schema']=='m193c-factor-eight-worker-v1' and worker['request']==parent['request'] and worker['plan']==parent['plan'] and worker['source_bindings']==plan['source_bindings'] and worker['prior_work']==prior and worker['qualification']==QUAL and worker['sources_unchanged'] is True and worker['finalization_errors']==[],'worker final/associations')
    wc=base+['pycache_prefix='+str(OUT/'worker-cache'),str(HERE/'real-precise-run.py'),'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256',parent['request']['sha256']]
    expected=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else parent['request']['sha256'] if x=='ACTUAL_REQUEST_SHA256' else x for x in plan['commands']['worker']]
    child=parent['child'];need(wc==expected==child['command']==worker['command'],'independent worker argv')
    need(parent['environment']==dict.fromkeys(('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'),'2') and parent['removed_environment']==sorted(set(parent['removed_environment'])),'bounded saved environment')
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'no bytecode/cache artifacts')
    need(parent['implementation_version']==worker['implementation_version']==VERSION,'actual precise implementation tags')
    cache_refs={k:PRIVATE_CACHE[k] for k in ('arm_ref','features_ref')}
    need(parent['private_precision_baseline']==worker['private_precision_baseline']==cache_refs,'actual published private baseline')
    obs=worker['precise_factory_observations']
    need(parent['precise_factory_observations']==dict(private=[],real=[]) and set(obs)=={'private','real'} and len(obs['private'])<=2 and len(obs['real'])<=9,'factory scope/population')
    for scope in ('private','real'):
        for i,w in enumerate(obs[scope]):witness(w,scope,i)
    ctrl=control_audit(worker['controls'],request['fixtures']);complete=parent['status']=='COMPLETE_FACTOR_EIGHT_SUPPORT_ONLY'
    for row in worker['controls']:
        if row['id']=='native-rotation-positive' and 'precise_factories' in row['evidence']:
            need(row['evidence']['precise_factories']==obs['private'],'control/publication actual private witnesses')
    features=[];fs=[];pairs=[];records=[];graph=None
    if ctrl['all_fourteen_pass']:
        need(len(obs['private'])==2 and len(obs['real'])==9,'complete explicit true extraction population')
        for i,w in enumerate(obs['private']):witness(w,'private',i,True)
        need(complete and worker['status']==parent['status'] and worker['error'] is parent['error'] is None and worker['real_decode_attempts']==worker['real_decodes_completed']==9 and len(worker['features'])==9 and len(worker['pairs'])==23,'complete real phase')
        for i,ref in enumerate(worker['features']):
            need(path(ref)==OUT/'worker'/f'feature-{i}.json','feature FileRef path');f=read(ref);features.append(f)
            need(f['original_index']==ORIGINAL[i] and same(f['tiff'],request['rows'][i]['tiff']),'real feature association')
            if f['representation'] is not None:
                representation(f['representation'],[4688,7032,3])
                need(f['representation']['precise_factory']==obs['real'][i],'feature receipt actual factory witness')
            if f['status']=='RETURNED':
                need(f['error'] is None and f['representation'] is not None,'returned feature receipt');witness(obs['real'][i],'real',i,True);r=f['representation'];lifted_arrays(r['coarse_coordinates_q8'],r['native_coordinates_q8'],f['count'])
                need(f['coordinates_q8']==r['native_coordinates_q8'],'emitted native coordinates');hv(f['descriptors_sha256']);hv(f['keys_sha256'])
            else:need(f['status']=='FEATURE_UNAVAILABLE' and f['error']['code']==CODE and obs['real'][i]['error'] is not None,'feature scientific refusal retained through factory')
            fs.append(dict(original_index=ORIGINAL[i],status=f['status'],count=f.get('count'),representation=f['representation'] is not None,keys_sha256=f.get('keys_sha256'),descriptors_sha256=f.get('descriptors_sha256'),record=ref,precise_factory=obs['real'][i],error=f.get('error')))
        for i,index in enumerate(worker['pairs']):
            need(index['pair']==schedule[i] and path(index['record'])==OUT/'worker'/(schedule[i]['id']+'.json'),'ordered pair FileRef')
            record=read(index['record']);records.append(record);o=record['outcome'];p=record['pair']
            need(p==schedule[i] and same(record['native_baseline'],request['native_pairs'][i]) and index['status']==o['status'],'pair cached association')
            a,z=p['reference'],p['source'];missing=[j for j in (a,z) if features[j]['status']!='RETURNED'];sites=None
            if missing:need(o==dict(status='FEATURE_UNAVAILABLE',unavailable=missing,qualification=QUAL),'unavailable propagation')
            else:sites=observed(o,features[a]['coordinates_q8'],features[z]['coordinates_q8'])
            err=o.get('error');pairs.append(dict(id=p['id'],source=z,reference=a,source_original=ORIGINAL[z],reference_original=ORIGINAL[a],record=index['record'],native_baseline=record['native_baseline'],native_baseline_status='REGISTRATION_REFUSED',status=o['status'],matches=len(o.get('landmarks',[])),transform=o.get('transform'),metrics=o.get('metrics'),error=None if err is None else {k:err[k] for k in ('code','message')},site_summary=sites))
        need(worker['unvisited']==parent['unvisited']==[] and worker['graph']==parent['graph'] and worker['graph']['qualification']==QUAL,'complete topology')
        graph=topology(records,worker['graph']);graph.update(anchor_local=4,anchor_original=52,reference_local=5,reference_original=65,anchor_component=next(c for c in graph['components'] if 4 in c),reference_component=next(c for c in graph['components'] if 5 in c));need(exit_code==child['exit_code']==0,'complete exits')
    else:
        need(not complete and parent['status']==worker['status']=='REFUSED' and exit_code==child['exit_code']==1 and parent['error'] is not None and worker['error'] is not None,'failed control remains refusal')
        need(worker['controls'][-1]['passed'] is False and len(worker['controls'])>=8,'named additive failed control')
        need(obs['real']==[] and worker['real_decode_attempts']==worker['real_decodes_completed']==0 and worker['features']==worker['pairs']==[] and worker['unvisited']==parent['unvisited']==list(range(23)) and worker['graph'] is parent['graph'] is None,'zero real phase after failed control')
        need(not list((OUT/'worker').glob('feature-*.json')) and not list((OUT/'worker').glob('pair-[0-9]*.json')),'no real records after failed control')
    need(parent['features']==parent['pairs']==parent['controls']==[] and parent['real_decode_attempts']==parent['real_decodes_completed']==0,'parent owns no worker counters')
    runtime=actual(ROOT/'experiments/M193-cover-overlap/contract-v1.json')['reference_environment']
    need(worker['runtime_before']==runtime and worker['runtime_after']==(runtime if complete else None),'runtime branch')
    need(child['error'] is None and child['cleanup_errors']==[] and child['terminal_job_accounting'] is True and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['job_accounting']['active_processes']==0 and child['termination']['attempted'] is False and child['post_exit_drain']['completed'] is True,'terminal Job no kill/error')
    account=child['job_accounting'];need(all(integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'],'CPU components')
    log=file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or same(child['log'],log)),'actual worker log')
    terminal=strict(path(log).read_bytes().splitlines()[-1]);need(terminal['status']==worker['status'] and terminal['error']==worker['error'] and terminal['finalization_errors']==worker['finalization_errors'] and Path(terminal['result']).resolve()==OUT/'worker/result.json','worker terminal publication')
    need(console['cpu_accounting_complete'] is True and parent['work']['cpu_accounting_complete'] is True and terminal['cpu_accounting_complete'] is True and worker['work']['cpu_accounting_complete'] is True,'complete CPU accounting even on refusal')
    inventory=all_inventory();total=sum(r['bytes'] for r in inventory);work=console['work_through_final_checks']
    need(parent['work']['snapshot_bytes']==worker['work']['snapshot_bytes']==0,'no snapshots')
    need(work['file_bytes']-prior['file_bytes']==work['metadata_bytes']-prior['metadata_bytes']==total,'all actual metadata charged once')
    need(parent['work']['new_extent_bytes']+refs['result']['bytes']==total,'prepublication extent plus result')
    need(D(str(work['cpu_seconds']))-D(str(prior['cpu_seconds']))>=D(account['total_cpu_100ns'])/10000000,'whole terminal Job CPU charged')
    limits=child['limits'];caps={k:D(str(work[k]))-D(str(prior[k]))<=v for k,v in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8<<20,metadata_bytes=8<<20).items()}
    need(all(D(str(work[k]))>=D(str(prior[k])) for k in prior),'no refund')
    caps['global']=work['cpu_seconds']<=1200 and work['wall_seconds']<=1800 and work['file_bytes']<=4*(1<<30) and work['metadata_bytes']<=128*(1<<20)
    caps['child_cpu']=account['total_cpu_100ns']/1e7<=limits['cpu_seconds']<=300;caps['child_wall']=child['wall_seconds']<=limits['wall_seconds']<=240
    caps['child_memory']=child['job_memory']['peak_job_memory_used_bytes']<=limits['committed_bytes']==8*(1<<30);caps['child_log']=log['bytes']<=limits['log_bytes']==1<<20
    need(child['configured_job_limits']['committed_bytes']==limits['committed_bytes'] and all(caps.values()),'actual owned caps')
    helper_ref=file(hpath);need((helper_ref['bytes'],helper_ref['sha256'])==HELPER,'executed independent helper stable')
    for ref in list(USED.values()):file(path(ref),ref)
    for s0 in list(TIFF_STAT):
        s=path(s0['reference']).stat(follow_symlinks=False);need((s.st_size,s.st_dev,s.st_ino,s.st_mtime_ns)==(s0['bytes'],s0['device'],s0['file_id'],s0['mtime_ns']),'unopened TIFF metadata stable')
    result=dict(schema='m193c-saved-real-precise-audit-v1',status='PASS_SAVED_REAL_PRECISE_OUTCOME_AUDIT',subject_complete=complete,subject_status=parent['status'],worker_status=worker['status'],subject_errors=dict(parent=parent['error'],worker=worker['error']),finalization_errors=dict(parent=parent['finalization_errors'],worker=worker['finalization_errors']),sources_unchanged=dict(parent=parent['sources_unchanged'],worker=worker['sources_unchanged']),subject_branch='COMPLETE_DIAGNOSTIC_POPULATION' if complete else 'NAMED_CONTROL_FAILED_ZERO_REAL_DECODES',refused_control=None if complete else worker['controls'][-1]['id'],external=refs,audit_source=file(__file__),pure_helper_source=helper_ref,commissioning=commissioned,private_baseline=plan['private_baseline'],private_cache={k:PRIVATE_CACHE[k] for k in ('arm_ref','features_ref')},native_baseline=native_refs,precise_factory_observations=obs,worker_result=parent['worker_result'],controls=ctrl,features=fs,pairs=pairs,graph=graph,qualification=QUAL,unvisited=worker['unvisited'],real_decode_attempts=worker['real_decode_attempts'],real_decodes_completed=worker['real_decodes_completed'],actual_final_work=work,next_wall_seconds=str(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),job=child,caps=caps,cpu_accounting_complete=True,inventory=inventory,inventory_total_bytes=total,tiff_extent_checks_only=TIFF_STAT,unique_hashed_metadata_files=len(USED),retention_gaps=GAPS,audit_timing=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall),scope='Saved JSON/metadata only; no TIFF/RAW payload hash, decode, feature extraction, matching, fit or subject import. Coarse image/descriptor/key hashes and factory restoration are producer witnesses. Exact and radius-one site groups describe repeated coordinates; connected groups may chain beyond one pixel and do not establish independence. Returned fit residuals can favor biased maps and are only consistency checks. Graph components/cycle rank/bridges are descriptive, not physical geometry, support, overlap, per-frame placement or quality admission.')
    raw=json.dumps(result,sort_keys=True,allow_nan=False,separators=(',',':')).encode();need(len(raw)<=120*(1<<10),'bounded audit result');need(len(raw)+Path(__file__).stat().st_size+12*(1<<10)<=196*(1<<10),'196 KiB audit source/result/report reservation');print(raw.decode())

if __name__=='__main__':main()
