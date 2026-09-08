"""Independent saved precise-upscale outcome audit. No subject/image imports.
A pinned previous independent auditor supplies pure metadata and arithmetic
helpers. Main runs only after actual root-supplied terminal digests exist.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import types
from decimal import Decimal as D

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'precise-upscale-1'
HELPER=(42893,'4b4736b8a95ef7d347dd2ad98cc66ac4460e1d77d7f735e68f016e8e26912e30')
RUNNER=(21313,'bdb52e2a87992709d2479237ed2f275ce6a0e223667b55c3fc6a2c316d0f0547')
SPEC=(10070,'a7af9ccdf9d30d08b8a7aecb2341275123134282695ec4806380b047922f82af')
BASE_AUDIT='386a2c56515041d4c71a63b77876d3f987be1d2993182b9317b68db4ccea7440'
IDS=['cached-repeated-block-null','explicit-false-reproduction','precise-true-observation','restored-false-reproduction','precise-native-rotation-positive','precise-two-pixel-map-destroyer','precise-observer-null']
NAMES=['explicit-false','precise-true','restored-false']
FLAGS=[False,True,False]
KWARGS=dict(nfeatures=2048,nOctaveLayers=3,contrastThreshold=0.01,edgeThreshold=12,sigma=1.6)
ALLOWANCE=dict(cpu_seconds=20,wall_seconds=30,file_bytes=1<<20,metadata_bytes=1<<20)
COUNTERS=dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=5)
COMPLETE='COMPLETE_PRIVATE_PRECISE_UPSCALE_CONTROL_ONLY'


def need(ok,why):
    if not ok:raise ValueError(why)


def helpers():
    p=HERE/'work/independent-factor-eight-1-audit.py';raw=p.read_bytes()
    need((len(raw),hashlib.sha256(raw).hexdigest())==HELPER,'held independent helper bytes')
    # This imports only our own reviewed standard-library auditor, never a subject.
    m=types.ModuleType('independent_precise_helpers');m.__file__=str(p)
    sys.modules[m.__name__]=m;exec(compile(raw,str(p),'exec'),m.__dict__)
    m.OUT=OUT
    return m,p


def features(a,ref,fixture,name):
    need(a.path(ref)==OUT/'worker'/(name+'-features.json'),'exact arm feature path')
    r=a.read(ref)
    need(r['schema']=='m193c-factor-eight-private-features-v1' and r['qualification']==a.QUAL and a.same(r['fixture'],fixture),'arm feature identity')
    for side,shape in (('reference',[2304,3072,3]),('source',[3072,2304,3])):
        f=r[side];a.representation(f['representation'],shape);a.lifted_arrays(f['coarse_coordinates_q8'],f['native_coordinates_q8'],f['count']);a.hv(f['descriptors_sha256']);a.hv(f['keys_sha256'])
    return r


def memory_equality_from_source(a,outcome,cached):
    # This is a type reconstruction justified by immutable source, not a new fit.
    import copy
    import ast
    prototype=HERE/'factor-eight-prototype.py'
    ref=a.file(prototype)
    need(ref['sha256']=='86111beb318f270c4532d4a5299d8b6a14413845c5eb384790f3e8d21d959d6f','tuple-producer source pin')
    tree=ast.parse(prototype.read_text(encoding='utf-8-sig'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='site_evidence')
    text=ast.unparse(fn)
    need(".add(tuple(row[side]))" in text and "exact_locations_shared_between_splits=sorted(parts['calibration'] & parts['holdout'])" in text,'actual tuple intersection producer')
    reconstructed=copy.deepcopy(outcome);fields=[]
    for side in ('reference_q8','source_q8'):
        points=outcome['site_evidence']['sides'][side]['exact_locations_shared_between_splits']
        need(all(type(p) is list and len(p)==2 for p in points),'JSON cached coordinate lists')
        reconstructed['site_evidence']['sides'][side]['exact_locations_shared_between_splits']=[tuple(p) for p in points]
        if points:fields.append(dict(side=side,count=len(points)))
    need(json.loads(json.dumps(reconstructed))==outcome,'type-only reconstruction is JSON-neutral')
    if fields:need(reconstructed!=cached,'nonempty tuple/list fields force runtime inequality')
    return reconstructed==cached,dict(source=ref,nonempty_tuple_fields=fields,saved_json_whole_outcome_equal=outcome==cached,source_derived_whole_outcome_equal=reconstructed==cached,scope='Only known source tuple fields are reconstructed; no original runtime operands were retained. A nonempty listed field is sufficient to falsify whole-outcome equality.')


def arms_and_controls(a,w,inputs,cached,saved_features):
    controls=w['controls'];refs=w['arms']
    need([r['id'] for r in controls]==IDS[:len(controls)] and 1<=len(controls)<=7,'fixed control prefix')
    need(len(refs)<=3,'bounded arm prefix')
    arms=[];fs=[];summary=[]
    for i,ref in enumerate(refs):
        need(a.path(ref)==OUT/'worker'/(NAMES[i]+'-arm.json'),'arm FileRef/order')
        arm=a.read(ref);arms.append(arm)
        need(arm['schema']=='m193c-private-precise-arm-v1' and arm['name']==NAMES[i] and type(arm['enable_precise_upscale']) is bool and arm['enable_precise_upscale'] is FLAGS[i],'typed arm option')
        calls=arm['constructor_calls'];need(len(calls)<=2,'per-arm factory ceiling')
        for call in calls:
            expect=dict(KWARGS,enable_precise_upscale=FLAGS[i])
            need(call==expect and all(type(call[k]) is type(v) for k,v in expect.items()),'only the literal option varies')
        # Any recorded extraction exception still must restore the original factory.
        need(arm['factory_restored'] is True,'actual restoration witness')
        f=None;o=arm['outcome'];sites=truth=corners=None
        if arm['feature_record'] is not None:f=features(a,arm['feature_record'],inputs['fixture'],NAMES[i])
        if o is not None:
            need(f is not None and arm['error'] is None and len(calls)==2,'completed arm prerequisites')
            sites=a.observed(o,f['reference']['native_coordinates_q8'],f['source']['native_coordinates_q8'])
            if o['landmarks']:truth=a.true_rotation_landmarks(o['landmarks'])
            if o['transform'] is not None:corners=a.corners(o['transform'])
        else:need(arm['error'] is not None and i==len(refs)-1,'partial failed final arm')
        fs.append(f)
        summary.append(dict(name=NAMES[i],enable_precise_upscale=FLAGS[i],arm=ref,feature_record=arm['feature_record'],constructor_calls=calls,factory_restored=arm['factory_restored'],error=arm['error'],outcome_status=None if o is None else o['status'],corner_errors=corners,literal_truth_all_landmarks=truth,site_summary=sites))
    for row in controls:
        need(type(row['passed']) is bool,'typed control outcome')
        a.saved(OUT/'worker'/('control-'+row['id']+'.json'),row,True)
    summaries=[]
    for ordinal,row in enumerate(controls):
        name=row['id'];e=row['evidence'];equality_probe=None
        if set(e)=={'exception','arms'}:
            need(row is controls[-1] and row['passed'] is False and e['arms']==refs and type(e['exception']) is str and 'Traceback' in e['exception'],'retained unexpected private exception')
            summaries.append(dict(id=name,passed=False,exception=e['exception']));break
        if name=='cached-repeated-block-null':
            need(a.same(e['fixture'],inputs['fixture']) and a.same(e['cached_features'],inputs['cached_features']),'cached block association')
            a.representation(e['reference'],[2304,3072,3]);a.representation(e['source'],[3072,2304,3])
            ok=e['reference']==saved_features['reference']['representation'] and e['source']==saved_features['source']['representation']
        elif name=='explicit-false-reproduction':
            need(len(arms)>=1 and a.same(e['arm'],refs[0]) and a.same(e['cached_control'],inputs['cached_control']) and a.same(e['cached_features'],inputs['cached_features']),'false baseline association')
            memory_equal,equality_probe=memory_equality_from_source(a,arms[0]['outcome'],cached['evidence']['outcome'])
            equality_probe.update(saved_json_features_equal=fs[0]==saved_features,saved_json_signature_equal=a.signature(arms[0]['outcome'])==a.signature(cached['evidence']['outcome']))
            ok=fs[0]==saved_features and memory_equal and a.signature(arms[0]['outcome'])==a.signature(cached['evidence']['outcome'])
        elif name=='precise-true-observation':
            need(len(arms)>=2 and a.same(e['arm'],refs[1]) and e['scope']=='Completed fixed observation; this does not admit its map','true observation association/scope')
            ok=arms[1]['outcome']['status'] in ('RETURNED','REGISTRATION_REFUSED') and arms[1]['factory_restored']
        elif name=='restored-false-reproduction':
            need(len(arms)==3 and a.same(e['arm'],refs[2]) and a.same(e['baseline_arm'],refs[0]),'restored arm association')
            ok=fs[2]==fs[0]==saved_features and arms[2]['outcome']==arms[0]['outcome'] and a.signature(arms[2]['outcome'])==a.signature(cached['evidence']['outcome'])
        elif name=='precise-native-rotation-positive':
            need(a.same(e['arm'],refs[1]) and e['qualification']==a.QUAL and e['literal_truth_q32']==dict(a=0,b=a.Q,tx=3071*a.Q,ty=0),'true literal oracle association')
            o=arms[1]['outcome'];a.check_corners(e['corner_errors'],o['transform'])
            ok=o['status']=='RETURNED' and len(o['landmarks'])>=24 and a.corner_pass(o['transform'])
        elif name=='precise-two-pixel-map-destroyer':
            o=arms[1]['outcome'];need(e['baseline']==o['transform'] and e['mutated']==dict(o['transform'],tx=o['transform']['tx']+2*a.Q) and e['qualification']==a.QUAL,'only actual tx plus two')
            a.check_corners(e['corner_errors'],e['mutated']);ok=not a.corner_pass(e['mutated'])
        elif name=='precise-observer-null':
            need(a.same(e['count_arm'],refs[1]),'observer count uses existing true arm');o=arms[1]['outcome']
            for mode in ('off','placebo'):a.observed(e[mode],fs[1]['reference']['native_coordinates_q8'],fs[1]['source']['native_coordinates_q8'],captured=False)
            sigs=dict(off=a.signature(e['off']),count=a.signature(o),placebo=a.signature(e['placebo']))
            hs={k:a.sha(a.canonical(v)) for k,v in sigs.items()}
            need(e['canonical_signature_sha256']==hs,'actual observer signature hashes')
            ok=len(set(hs.values()))==1 and sigs['off']==sigs['count']==sigs['placebo'] and len(o['landmarks'])>=24
        need(row['passed'] is ok,'actual control boolean versus predicate: '+name)
        summaries.append(dict(id=name,passed=ok,equality_probe=equality_probe))
        if not ok:need(row is controls[-1],'no continuing past failed private control')
    allpass=len(controls)==7 and all(r['passed'] for r in controls)
    c=w['counters'];need(set(c)==set(COUNTERS) and all(a.integer(c[k]) and 0<=c[k]<=v for k,v in COUNTERS.items()),'typed bounded attempt counters')
    need(c['factory_calls']==sum(len(arm['constructor_calls']) for arm in arms),'factory call count from saved actual calls')
    need(c['feature_extraction_attempts']>=c['factory_calls'] and c['matcher_calls']>=sum(arm['outcome'] is not None for arm in arms),'attempts cover completed observed work')
    if allpass:need(c==COUNTERS and len(arms)==3,'exact complete private population')
    elif len(arms)==1 and arms[0]['outcome'] is not None and controls[-1]['id']==IDS[1]:
        need(c==dict(private_decode_attempts=1,feature_extraction_attempts=2,factory_calls=2,matcher_calls=1),'false gate stops before true arm')
    elif len(arms)==3 and all(arm['outcome'] is not None for arm in arms) and controls[-1]['id'] in IDS[4:6]:
        need(c==dict(private_decode_attempts=1,feature_extraction_attempts=6,factory_calls=6,matcher_calls=3),'failed true oracle/destroyer stops before observers')
    return dict(all_seven_pass=allpass,rows=summaries,unvisited=IDS[len(controls):]),summary

def main():
    cpu,wall=time.process_time(),time.perf_counter();p=argparse.ArgumentParser()
    for k in ('plan','result','outer','console','exit'):p.add_argument('--'+k+'-sha256',required=True)
    args=p.parse_args();a,hpath=helpers();commissioned=a.commissioning();refs={}
    names=dict(plan=HERE/'precise-upscale-plan-1.json',result=OUT/'result.json',outer=HERE/'work/precise-upscale-1-outer.json',console=HERE/'work/precise-upscale-1-console.txt',exit=HERE/'work/precise-upscale-1-exit.txt')
    for k,path in names.items():refs[k]=a.file(path);need(refs[k]['sha256']==getattr(args,k+'_sha256'),'actual external '+k)
    plan,parent,outer=(a.read(refs[k]) for k in ('plan','result','outer'))
    final=a.strict(a.path(refs['console']).read_bytes().splitlines()[-1]);code=int(a.path(refs['exit']).read_bytes().strip())
    need(set(plan)==set('schema source_bindings factor_eight_baseline prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-precise-upscale-plan-v1','closed precise plan')
    need(set(plan['factor_eight_baseline'])==set('plan result outer console exit audit'.split()),'six factor baseline refs')
    for path,binding in plan['source_bindings'].items():a.file(ROOT/path,dict(path=path,**binding))
    for name,pin in (('precise-upscale-run.py',RUNNER),('precise-upscale-preregister.md',SPEC)):
        r=a.file(HERE/name);need((r['bytes'],r['sha256'])==pin,'held executed source')
    py=a.file(a.path(plan['python_executable']),plan['python_executable'])
    historical={k:a.read(ref) if k in ('plan','result','outer','audit') else a.file(a.path(ref),ref) for k,ref in plan['factor_eight_baseline'].items()}
    old,base_audit=historical['plan'],historical['audit']
    need(plan['factor_eight_baseline']['audit']['sha256']==BASE_AUDIT and base_audit['schema']=='m193c-saved-factor-eight-audit-v1' and base_audit['status']=='PASS_SAVED_FACTOR_EIGHT_OUTCOME_AUDIT' and base_audit['subject_complete'] is False and base_audit['refused_control']=='native-rotation-positive' and base_audit['cpu_accounting_complete'] is True,'exact failed-positive audit authority')
    need(old['schema']=='m193c-factor-eight-plan-v1' and all(plan['source_bindings'].get(k)==v for k,v in old['source_bindings'].items()),'full prior source closure preserved')
    for k in ('plan','result','outer','console','exit'):need(a.same(plan['factor_eight_baseline'][k],base_audit['external'][k]),'baseline association')
    base_parent=historical['result'];base_worker=a.read(base_parent['worker_result']);need(a.same(base_parent['worker_result'],base_audit['worker_result']),'cached actual worker')
    need(base_parent['status']==base_worker['status']=='REFUSED' and base_parent['sources_unchanged'] is base_worker['sources_unchanged'] is True and base_parent['finalization_errors']==base_worker['finalization_errors']==[],'preserved subject refusal')
    need([x['id'] for x in base_worker['controls']]==a.ALL_IDS[:10] and all(x['passed'] for x in base_worker['controls'][:9]) and base_worker['controls'][9]['passed'] is False and base_worker['real_decode_attempts']==base_worker['real_decodes_completed']==0 and base_worker['features']==base_worker['pairs']==[] and base_worker['unvisited']==list(range(23)),'exact historical stopped population')
    prior=a.read(plan['prior_work']);need(plan['preparation_allowance']==ALLOWANCE,'whole new preparation charge')
    for k,v in ALLOWANCE.items():need(D(str(prior[k]))==D(base_audit['next_wall_seconds'] if k=='wall_seconds' else str(base_audit['actual_final_work'][k]))+v,'no refund carry')
    need(prior==dict(cpu_seconds=480.390625,wall_seconds=556.2322624,file_bytes=3952852624,metadata_bytes=27651978),'literal next prior')
    need(set(outer)==set('scope command plan_sha256 exit_code elapsed_wall_seconds admissible_parent_exit'.split()) and outer['plan_sha256']==refs['plan']['sha256'],'closed actual outer')
    commandbase=[py['path'],'-B','-X','faulthandler','-X'];script=str(HERE/'precise-upscale-run.py')
    pc=commandbase+['pycache_prefix='+str(OUT/'parent-cache'),script,'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT)]
    frozen_pc=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['parent']]
    need(set(plan['commands'])=={'parent','worker'} and pc==frozen_pc==parent['command']==outer['command'] and a.same(parent['plan'],refs['plan']),'independent actual parent argv')
    need(a.integer(outer['exit_code']) and outer['exit_code']==code and outer['admissible_parent_exit'] is (code==0),'actual parent exit')
    need(parent['schema']=='m193c-precise-upscale-run-v1' and parent['source_bindings']==plan['source_bindings'] and parent['prior_work']==prior and parent['qualification']==a.QUAL and parent['sources_unchanged'] is True and parent['finalization_errors']==[],'parent final source association')
    need(final['status']==parent['status'] and final['error']==parent['error'] and final['finalization_errors']==parent['finalization_errors'] and Path(final['result']).resolve()==OUT/'result.json','parent terminal publication')
    need(parent['request'] is not None and parent['worker_result'] is not None and parent['child'] is not None,'private worker exists')
    request=a.read(parent['request']);w=a.read(parent['worker_result']);inputs=request['inputs']
    need(set(request)==set('schema plan inputs prior_work'.split()) and request['schema']=='m193c-precise-upscale-request-v1' and a.same(request['plan'],refs['plan']) and set(inputs)=={'cached_control','cached_features','fixture'},'closed fixture-only request')
    need(all(request['prior_work'][k]>=prior[k] for k in prior),'setup work charged')
    cached=a.read(inputs['cached_control']);saved_features=a.read(inputs['cached_features'])
    need(a.path(inputs['cached_control'])==HERE/'factor-eight-1/worker/control-native-rotation-positive.json' and cached==base_worker['controls'][-1] and a.same(inputs['cached_features'],cached['evidence']['features']) and a.same(inputs['fixture'],saved_features['fixture']),'cached full control/features identity')
    need(cached['evidence']['outcome']['status']=='RETURNED' and not a.corner_pass(cached['evidence']['outcome']['transform']),'historical wrong map still wrong')
    a.image_stat(inputs['fixture'])
    wc=commandbase+['pycache_prefix='+str(OUT/'worker-cache'),script,'--plan',str(names['plan']),'--sha256',refs['plan']['sha256'],'--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256',parent['request']['sha256']]
    expected=[refs['plan']['sha256'] if x=='ACTUAL_PLAN_SHA256' else parent['request']['sha256'] if x=='ACTUAL_REQUEST_SHA256' else x for x in plan['commands']['worker']]
    child=parent['child'];need(wc==expected==child['command']==w['command'],'independent worker argv')
    need(w['schema']=='m193c-precise-upscale-worker-v1' and w['plan']==parent['plan'] and w['request']==parent['request'] and w['prior_work']==prior and w['source_bindings']==plan['source_bindings'] and w['qualification']==a.QUAL and w['sources_unchanged'] is True and w['finalization_errors']==[],'worker final association')
    scope='PRIVATE FIXTURE ONLY; no real image population or product admission'
    need(w['scope']==parent['scope']==scope and parent['arms']==parent['controls']==[] and parent['counters']==dict.fromkeys(COUNTERS,0),'explicit private scope/parent counters')
    need(parent['environment']==dict.fromkeys(('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'),'2') and parent['removed_environment']==sorted(set(parent['removed_environment'])),'saved bounded environment')
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'no cache outputs')
    control_summary,arm_summary=arms_and_controls(a,w,inputs,cached,saved_features)
    complete=parent['status']==COMPLETE
    if complete:need(control_summary['all_seven_pass'] and w['status']==COMPLETE and parent['error'] is w['error'] is None and code==child['exit_code']==0,'complete actual private run')
    else:need(parent['status']==w['status']=='REFUSED' and not control_summary['all_seven_pass'] and w['controls'][-1]['passed'] is False and parent['error'] is not None and w['error'] is not None and code==child['exit_code']==1,'named retained private failure')
    runtime=a.actual(ROOT/'experiments/M193-cover-overlap/contract-v1.json')['reference_environment']
    need(w['runtime_before']==runtime and w['runtime_after']==(runtime if complete else None),'frozen runtime branch')
    need(child['error'] is None and child['cleanup_errors']==[] and child['terminal_job_accounting'] is True and child['direct_exit_observed'] is True and child['pipe_eof_observed'] is True and child['job_accounting']['active_processes']==0 and child['termination']['attempted'] is False and child['post_exit_drain']['completed'] is True,'terminal Job without kill/helper error')
    account=child['job_accounting'];need(account['total_cpu_100ns']==account['total_user_100ns']+account['total_kernel_100ns'] and all(a.integer(account[k]) for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')),'actual CPU components')
    log=a.file(OUT/'worker.log');need(child['log_bytes']==log['bytes'] and (child.get('log') is None or a.same(child['log'],log)),'actual log binding')
    terminal=a.strict(a.path(log).read_bytes().splitlines()[-1]);need(terminal['status']==w['status'] and terminal['error']==w['error'] and terminal['finalization_errors']==w['finalization_errors'] and Path(terminal['result']).resolve()==OUT/'worker/result.json','worker final publication')
    need(final['cpu_accounting_complete'] is True and parent['work']['cpu_accounting_complete'] is True and w['work']['cpu_accounting_complete'] is True and terminal['cpu_accounting_complete'] is True,'complete terminal CPU accounting')
    inventory=a.all_inventory();total=sum(r['bytes'] for r in inventory);work=final['work_through_final_checks']
    need(parent['work']['snapshot_bytes']==w['work']['snapshot_bytes']==0 and work['file_bytes']-prior['file_bytes']==work['metadata_bytes']-prior['metadata_bytes']==total,'no snapshots and exact output byte charge')
    need(parent['work']['new_extent_bytes']+refs['result']['bytes']==total,'prepublication extent accounting')
    need(D(str(work['cpu_seconds']))-D(str(prior['cpu_seconds']))>=D(account['total_cpu_100ns'])/10000000,'terminal Job CPU charged')
    caps={k:D(str(work[k]))-D(str(prior[k]))<=v for k,v in dict(cpu_seconds=300,wall_seconds=480,file_bytes=8<<20,metadata_bytes=8<<20).items()}
    need(all(D(str(work[k]))>=D(str(prior[k])) for k in prior),'no negative cost/refund')
    limits=child['limits'];caps['global']=work['cpu_seconds']<=1200 and work['wall_seconds']<=1800 and work['file_bytes']<=4*(1<<30) and work['metadata_bytes']<=128*(1<<20)
    caps['child_cpu']=account['total_cpu_100ns']/1e7<=limits['cpu_seconds']<=300;caps['child_wall']=child['wall_seconds']<=limits['wall_seconds']<=240
    caps['child_memory']=child['job_memory']['peak_job_memory_used_bytes']<=limits['committed_bytes']==8*(1<<30);caps['child_log']=log['bytes']<=limits['log_bytes']==1<<20
    need(child['configured_job_limits']['committed_bytes']==limits['committed_bytes'] and all(caps.values()),'actual process/local/global caps')
    helper_ref=a.file(hpath);need((helper_ref['bytes'],helper_ref['sha256'])==HELPER,'executed helper still pinned')
    for ref in list(a.USED.values()):a.file(a.path(ref),ref)
    for s0 in a.TIFF_STAT:
        s=a.path(s0['reference']).stat(follow_symlinks=False);need((s.st_size,s.st_dev,s.st_ino,s.st_mtime_ns)==(s0['bytes'],s0['device'],s0['file_id'],s0['mtime_ns']),'unopened private TIFF metadata stable')
    result=dict(schema='m193c-saved-precise-upscale-audit-v1',status='PASS_SAVED_PRECISE_UPSCALE_OUTCOME_AUDIT',subject_complete=complete,subject_status=parent['status'],worker_status=w['status'],refused_control=None if complete else w['controls'][-1]['id'],external=refs,worker_result=parent['worker_result'],audit_source=a.file(__file__),pure_helper_source=helper_ref,commissioning=commissioned,baseline=plan['factor_eight_baseline'],controls=control_summary,arms=arm_summary,counters=w['counters'],qualification=a.QUAL,real_phase_available=False,actual_final_work=work,next_wall_seconds=str(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),job=child,caps=caps,cpu_accounting_complete=True,inventory=inventory,inventory_total_bytes=total,unique_hashed_metadata_files=len(a.USED),tiff_extent_checks_only=a.TIFF_STAT,audit_timing=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall),scope='One fixed private fixture, complete extractor/matcher option comparison only. All-match native truth scores are independent of fitted support. No image payload reads, numerical subject imports, new extraction/matching/fit, real-image accuracy, universal bias mechanism, or support/overlap/product admission.')
    raw=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode();need(len(raw)<120*(1<<10),'bounded audit result');print(raw.decode())

if __name__=='__main__':main()
