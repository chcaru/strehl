"""Versioned saved-prefix audit with closed FileRef identity; both older frozen auditors unchanged.
No image/model/registrar execution. Root must release exact surviving five digests.
The lost parent Job receipt is a retention gap: complete CPU is NOT asserted.
"""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'experiments/m193c-output-grid'
OUT=HERE/'sift-lightglue-commission-1'
HELPER=(62292,'ccb78254596b6402139bb4ff4541a5bb6f0597175268a426bef66ba5e4f7c03c')
CPU_RESERVATION=300
PREVIOUS_SOURCE=(16742,'f2665e50742c6aa689dbdc20b0917ed4093368cff130417af6cdf565b0a11845')
FAILED_OUTER=(987,'5e7d5ed4990353a4edc90f2c611c23e63294890136635bc7993781fb30e8c16d')
FAILED_STDERR=(1215,'126e47d6299a4bcfc732a0323271bacc3d9cddc45d050dbb7e25cf357b6a0f55')
DIAGNOSIS=(9137,'e44fd6061c0d800e8d74278b6f3012565ce3d90e8dfc1096521237eeba1e8b6f')
SURVIVING_EXTRA={'request':(16327,'3c8933978180aa4c0429aa320739056f7d0992c26fd57c719969339cb007ed56'),'worker_log':(1971,'891c187ca21e5980b9a5bbc07ca6a3fc850a5ff19b9a8cc1ad8025733cd91f17')}


def load_helper():
    p=HERE/'work/independent-sift-lightglue-commission-audit.py';raw=p.read_bytes()
    if (len(raw),hashlib.sha256(raw).hexdigest())!=HELPER:raise ValueError('immutable prospective independent auditor')
    # Our own stdlib-only source, guarded main. No numerical subject import.
    h=types.ModuleType('independent_commission_prefix_helpers');h.__file__=str(p);sys.modules[h.__name__]=h
    exec(compile(raw,str(p),'exec'),h.__dict__);return h,p


def full_truth(h,rows):
    values=[]
    for row in rows:
        rx,ry=row['reference_q8'];sx,sy=row['source_q8'];dx,dy=rx+sy-3071*256,ry-sx
        values.append(dict(reference_q8=[rx,ry],source_q8=[sx,sy],offset_q8=[dx,dy],squared_error_q16=dx*dx+dy*dy))
    check=h.truth(rows);return dict(scope='every supplied correspondence versus literal native rotation, no fitted subset',rows=values,count=check['count'],within_two_native_pixels=check['within_two_native_pixels'],sum_squared_error_q16=check['sum_squared_error_q16'],rms_native_pixels=check['rms_native_pixels'],passes=check['passes'])


def compact_refs(value):
    if isinstance(value,dict):
        if set(value)=={'path','bytes','sha256'}:
            p=(ROOT/value['path']).resolve()
            if p.is_relative_to(ROOT):return dict(value,path=p.relative_to(ROOT).as_posix())
        return {k:compact_refs(v) for k,v in value.items()}
    if isinstance(value,list):return [compact_refs(v) for v in value]
    return value

def asset_identity(h,left,right):
    roles={'checkpoint','license','matcher','readme','rootsift_reference'}
    if type(left) is not dict or type(right) is not dict or set(left)!=roles or set(right)!=roles:return False
    for role in sorted(roles):
        for ref in (left[role],right[role]):
            if type(ref) is not dict or set(ref)!={'path','bytes','sha256'} or type(ref['path']) is not str or type(ref['bytes']) is not int or ref['bytes']<0 or type(ref['sha256']) is not str or len(ref['sha256'])!=64 or any(c not in '0123456789abcdef' for c in ref['sha256']):return False
        if not h.same(left[role],right[role]):return False
    return True


def request_conjuncts(h,worker,request,base,plan_ref):
    rows=[]
    def witness(x):
        raw=h.canonical(x);return dict(type=type(x).__name__,bytes=len(raw),sha256=h.sha(raw))
    def add(name,left,right,rule='exact Python equality',ok=None):
        rows.append(dict(name=name,rule=rule,passed=(left==right if ok is None else ok),left=witness(left),right=witness(right)))
    add('request-path',str(h.path(worker['request'])),str(OUT/'request.json'))
    add('closed-request-keys',sorted(request),sorted('schema plan rows private_ref real_refs assets prior_work'.split()))
    add('request-schema',request['schema'],'m193c-sift-lightglue-commission-request-v1')
    add('plan-identity',request['plan'],plan_ref,'resolved FileRef path + exact extent/SHA',h.same(request['plan'],plan_ref))
    add('whole-nine-rows',request['rows'],base['rows'])
    add('whole-nine-real-feature-refs',request['real_refs'],base['real_refs'])
    add('private-feature-identity',request['private_ref'],base['private_ref'],'resolved FileRef path + exact extent/SHA',h.same(request['private_ref'],base['private_ref']))
    add('closed-asset-role-identities',request['assets'],base['assets'],'closed five roles and closed typed FileRefs; per-role resolved path + exact extent/SHA',asset_identity(h,request['assets'],base['assets']))
    h.need(all(x['passed'] for x in rows),'every individually named request conjunct')
    original=request['assets'];positive=json.loads(json.dumps(original));positive['matcher']['path']=str(h.path(positive['matcher']))
    h.need(positive['matcher']['path']!=original['matcher']['path'],'equivalent-spelling positive exercised actual spelling change')
    mutants=[]
    for name in ('extent','hash','path','role','missing-field','boolean-extent'):
        v=json.loads(json.dumps(positive))
        if name=='extent':v['matcher']['bytes']+=1
        elif name=='hash':v['matcher']['sha256']=('0' if v['matcher']['sha256'][0]!='0' else '1')+v['matcher']['sha256'][1:]
        elif name=='path':v['matcher']['path']=str(HERE/'lightglue-acquisition-1/sift.py')
        elif name=='role':v['other-matcher']=v.pop('matcher')
        elif name=='missing-field':del v['matcher']['sha256']
        else:v['matcher']['bytes']=True
        mutants.append(dict(id=name,accepted=asset_identity(h,v,base['assets']),mutant_canonical=witness(v)))
    h.need(asset_identity(h,positive,base['assets']) and all(not x['accepted'] for x in mutants),'equivalent path positive and content/role/schema destroyers')
    return dict(conjuncts=rows,raw_asset_dictionaries_equal=original==base['assets'],equivalent_spelling_positive=dict(accepted=True,canonical=witness(positive)),destroyers=mutants,scope='Only typed FileRef identity semantics changed. Ordered rows, feature references and role names remain exact. Full source operands are retained in exact request/acquisition-audit FileRefs; canonical hashes bind complete values.')


def main():
    cpu=time.process_time();wall=time.perf_counter();h,helper_path=load_helper();need=h.need
    p=argparse.ArgumentParser()
    for name in ('plan','worker-result','outer','console','exit'):p.add_argument('--'+name+'-sha256',required=True)
    args=p.parse_args();need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode,'owned cwd/no bytecode')
    paths=dict(plan=HERE/'sift-lightglue-commission-plan-1.json',worker_result=OUT/'worker/result.json',outer=HERE/'work/sift-lightglue-commission-1-outer.json',console=HERE/'work/sift-lightglue-commission-1-console.txt',exit=HERE/'work/sift-lightglue-commission-1-exit.txt')
    external={}
    for name,path in paths.items():
        ref=h.file(path);need(ref['sha256']==getattr(args,name+'_sha256'),'root released surviving '+name);external[name]=ref
    need(not (OUT/'result.json').exists(),'parent result is actually missing, not a fabricated FileRef')
    failed_source=h.file(HERE/'work/independent-sift-lightglue-commission-prefix-audit.py');need((failed_source['bytes'],failed_source['sha256'])==PREVIOUS_SOURCE,'unchanged failed adapter')
    failed_outer_ref=h.file(HERE/'work/independent-sift-lightglue-commission-prefix-audit-outer.json');need((failed_outer_ref['bytes'],failed_outer_ref['sha256'])==FAILED_OUTER,'first actual failed audit outer');failed_outer=h.read(failed_outer_ref)
    failed_stderr=h.file(HERE/'work/independent-sift-lightglue-commission-prefix-audit-stderr.txt');need((failed_stderr['bytes'],failed_stderr['sha256'])==FAILED_STDERR,'first actual failed audit stderr')
    failed_stdout=h.file(HERE/'work/independent-sift-lightglue-commission-prefix-audit.json');need(failed_stdout['bytes']==0 and failed_stdout['sha256']==h.sha(b''),'first failed audit emitted no result')
    need(failed_outer['exit_code']==1 and failed_outer['stdout_bytes']==0 and failed_outer['stderr_bytes']==1215 and failed_outer['elapsed_wall_seconds']==0.3044222000025911,'actual first audit failure retained')
    expected_failed=[str(h.PYTHON),'-B',str(h.path(failed_source)),*sum(([f'--{k.replace("_","-")}-sha256',external[k]['sha256']] for k in ('plan','worker_result','outer','console','exit')),[])]
    need(failed_outer['command']==expected_failed and b'ValueError: same actual request and private2/real9/assets' in h.raw(failed_stderr),'exact failed audit argv/location')
    diagnosis_ref=h.file(HERE/'work/independent-sift-lightglue-request-diagnosis.json');need((diagnosis_ref['bytes'],diagnosis_ref['sha256'])==DIAGNOSIS,'held all-conjunct metadata diagnosis');diagnosis=h.read(diagnosis_ref)
    h.file(h.path(diagnosis['source']),diagnosis['source']);need(diagnosis['status']=='VERIFIED_PATH_SPELLING_ONLY_CONJUNCTION_FAILURE' and [r['name'] for r in diagnosis['conjuncts'] if not r['passed']]==['whole-asset-ref-mapping'] and all(r['identity_equal'] and not r['path_spelling_equal'] for r in diagnosis['asset_reference_pairs']),'verified narrow representation defect')

    helper_ref=h.file(helper_path);need((helper_ref['bytes'],helper_ref['sha256'])==HELPER,'frozen original auditor remains held and unexecuted main')
    plan=h.read(external['plan']);worker=h.read(external['worker_result']);outer=h.read(external['outer']);console=h.strict(h.raw(external['console']).splitlines()[-1]);exit_code=int(h.raw(external['exit']).strip())
    need(set(plan)==set('schema source_bindings area4_baseline acquisition_receipt prior_work preparation_allowance python_executable commands'.split()) and plan['schema']=='m193c-sift-lightglue-commission-plan-v1' and plan['preparation_allowance']==h.ALLOWANCE,'closed original plan')
    need(len(plan['source_bindings'])==226,'actual frozen source population')
    for name,pin in h.PINS.items():
        r=h.file(HERE/name);need((r['bytes'],r['sha256'])==pin,'same original subject/source '+name)
    for name,binding in plan['source_bindings'].items():h.file(ROOT/name,dict(path=name,**binding))
    need(plan['source_bindings'][helper_path.relative_to(ROOT).as_posix()]=={k:helper_ref[k] for k in ('bytes','sha256')},'original auditor was preregistered')
    need(h.path(plan['python_executable'])==h.PYTHON,'same actual Python');h.file(h.PYTHON,plan['python_executable'])
    base=h.baseline(plan);prior=base['prior'];request=h.read(worker['request'])
    need((worker['request']['bytes'],worker['request']['sha256'])==SURVIVING_EXTRA['request'],'root released exact request extent/hash')
    conjunction=request_conjuncts(h,worker,request,base,external['plan'])
    need(all(D(str(request['prior_work'][k]))>=D(str(prior[k])) for k in prior),'retained request carry')
    command_base=[str(h.PYTHON),'-B','-X','faulthandler','-X'];script=str(HERE/'sift-lightglue-commission-run.py');planpath=str(paths['plan'])
    parent_command=command_base+['pycache_prefix='+str(OUT/'parent-cache'),script,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT)]
    worker_command=command_base+['pycache_prefix='+str(OUT/'worker-cache'),script,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
    need(plan['commands']==dict(parent=parent_command,worker=worker_command) and outer['command']==h.replace(parent_command,external['plan']['sha256']) and worker['command']==h.replace(worker_command,external['plan']['sha256'],worker['request']['sha256']),'exact surviving parent/worker argv')
    need(integer_exit(outer['exit_code']) and outer['exit_code']==exit_code==1 and outer['admissible_parent_exit'] is True and outer['plan_sha256']==external['plan']['sha256'],'actual failed parent launch')
    need(worker['schema']=='m193c-sift-lightglue-commission-worker-v1' and worker['implementation_version']==h.VERSION and worker['status']=='REFUSED' and worker['prior_work']==prior and worker['source_bindings']==plan['source_bindings'] and worker['sources_unchanged'] is True and h.same(worker['plan'],external['plan']) and worker['finalization_errors']==[] and worker['qualification']==h.QUAL,'retained refused worker finalized successfully')
    need(worker['active_phase']=='private-known-geometry' and worker['assembly'] is None and not (OUT/'worker/private-assembled-matches.json').exists(),'actual refusal before assembled record and first registrar')
    need('save("private-assembled-matches"' in worker['error'] and worker['error'].rstrip().endswith('ValueError: trace metadata preallocation'),'named worker prewrite failure')
    need(worker['counters']==dict(private_decodes=1,real_decode_attempts=9,real_decodes_completed=9,feature_extractions=11,private_model_forwards=1,real_model_forwards=0,registrar_calls=0),'exact failed attempt counters; no repeat model or fit')
    need(len(worker['controls'])==12 and [r['id'] for r in worker['controls']]==h.CONTROLS[:12] and all(r['passed'] is True for r in worker['controls']) and worker['unvisited_real_exports']==[] and len(worker['exports'])==11 and worker['export_admission']=='ALL_ELEVEN_CACHED_FEATURES_REPRODUCED_AND_READ_BACK','complete export prefix before five unvisited scientific groups')
    need(worker['inference_observer_nonperturbation']=='UNTESTED_ONE_FORWARD' and worker['model_loading']['import_guard_restored'] is True and worker['model_loading']['model_load_completed'] is True,'one executed model and restored import guard')
    expected_max=dict(private_decodes=1,real_decodes=9,feature_extractions=11,private_model_forwards=1,real_model_forwards=0,registrar_calls=5,post_extraction_serializer_modes=3,private_model_input_constructions=8,wrong_normalization_rows=1)
    need(worker['fixed_maximum_calls']==expected_max,'original call ceilings remain')
    need(worker['extractor_runtime_before']==worker['extractor_runtime_after']==h.actual(ROOT/'experiments/M193-cover-overlap/contract-v1.json')['reference_environment'],'eleven extractions used original frozen runtime')
    commissioned=h.commission();science=h.scientific(worker,base)
    need(len(science['exports'])==11 and science['refused_control'] is None and len(science['controls'])==12 and science['unvisited_controls']==h.CONTROLS[12:],'every visited control, all later controls unvisited')
    need(len(worker['precise_factory_observations']['private'])==2 and len(worker['precise_factory_observations']['real'])==9 and all(h.factory(w,scope,i) for scope in ('private','real') for i,w in enumerate(worker['precise_factory_observations'][scope])),'all eleven exact true factory calls restored')
    # Re-open authenticated export arrays using our own decoder. No extractor/model call.
    data=[]
    for i,ref in enumerate(worker['exports'][:2]):
        side=('reference','source')[i];size=([384,288],[288,384])[i]
        data.append(h.exported(ref,h.core_expected(base['private'][side],True),'private-'+side,size,base['private_ref'],side))
    learned,capped=h.learned(worker,data);prediction=h.read(worker['learned_output'])['output'];raw_rows=[]
    for i,j in prediction['matches']:raw_rows.append(dict(reference_q8=data[0]['native'][i],source_q8=data[1]['native'][j]))
    relation='SAME_ROWS_NO_INDEPENDENT_CORROBORATION' if len(raw_rows)<=256 else 'UNCAPPED_AND_HASH_CAPPED_POPULATIONS'
    all_truth=full_truth(h,raw_rows);cap_truth=full_truth(h,capped)
    attempted=dict(landmarks=capped,truth=dict(uncapped=all_truth,capped=cap_truth,population_relation=relation),qualification=dict(h.QUAL),association_rule='LightGlue fixed mutual learned confidence >0.1; original descriptor/coordinate hash order and cap256; alternating split')
    attempted_bytes=h.canonical(attempted);pre_extent=worker['work']['new_extent_bytes']
    need(pre_extent+len(attempted_bytes)>8*h.MIB,'independently reconstructed attempted assembly actually exceeds prewrite cap')
    need(pre_extent+external['worker_result']['bytes']<=8*h.MIB,'smaller refused worker receipt fits original worker cap')
    need(type(console)==dict and set(console)=={'error','finalization_errors'} and 'observed exact zero child exit' in console['error'] and len(console['finalization_errors'])==2 and all('trace metadata preallocation' in x for x in console['finalization_errors']),'retained parent first/second publication failures')
    log=h.file(OUT/'worker.log');need((log['bytes'],log['sha256'])==SURVIVING_EXTRA['worker_log'],'root released exact worker terminal log');terminal=h.strict(h.raw(log).splitlines()[-1]);need(terminal['status']=='REFUSED' and terminal['error']==worker['error'] and terminal['finalization_errors']==[] and Path(terminal['result']).resolve()==OUT/'worker/result.json' and terminal['cpu_accounting_complete'] is worker['work']['cpu_accounting_complete'] is True,'actual worker final receipt is only a sub-observation')
    need(worker['work']['scope']=='worker sub-observation; parent Job owns complete actual CPU' and worker['work']['snapshot_bytes']==0,'worker CPU does not substitute for missing Job receipt')
    inv=h.inventory();total=sum(r['bytes'] for r in inv);worker_total=sum(r['bytes'] for r in inv if h.path(r).is_relative_to(OUT/'worker'));binary=sum(r['bytes'] for r in inv if h.path(r).suffix in ('.u8','.i64','.f32'))
    need(worker_total==pre_extent+external['worker_result']['bytes'] and terminal['work_through_final_checks']['file_bytes']-prior['file_bytes']==worker_total,'worker exact prepublication and terminal inventory')
    need(total<=8*h.MIB,'actual output tree remains within byte cap despite refused writes')
    own=h.file(__file__)
    for p in h.USED:need(h.identity(Path(p).stat(follow_symlinks=False))==h.IDENTITIES[p],'all consumed source/export/runtime identities remain stable')
    audit_cpu=time.process_time()-cpu;audit_wall=time.perf_counter()-wall
    worker_cpu=D(str(terminal['work_through_final_checks']['cpu_seconds']))-D(str(prior['cpu_seconds']));need(worker_cpu>=0,'worker CPU sub-observation lower bound')
    outer_delta=D(str(outer['elapsed_wall_seconds']));need(outer_delta>=0,'actual outer wall')
    carry=dict(cpu_seconds=float(D(str(prior['cpu_seconds']))+CPU_RESERVATION+D('2')+D(str(failed_outer['elapsed_wall_seconds']))+D('.25')+D(str(audit_cpu))+D('.25')),wall_seconds=float(D(str(prior['wall_seconds']))+outer_delta+D(str(failed_outer['elapsed_wall_seconds']))+D('.5')+D(str(audit_wall))+D('.5')),file_bytes=prior['file_bytes']+total,metadata_bytes=prior['metadata_bytes']+total)
    need(carry['cpu_seconds']<=1200 and carry['wall_seconds']<=1800 and carry['file_bytes']<=4<<30 and carry['metadata_bytes']<=128*h.MIB,'conservatively charged bookkeeping remains within global caps')
    result=dict(schema='m193c-saved-sift-lightglue-commission-prefix-audit-v2',status='PASS_SAVED_SIFT_LIGHTGLUE_COMMISSION_PREFIX_AUDIT',subject_complete=False,admission_allowed=False,saved_prefix_verified=True,parent_result_missing=True,parent_result_expected_path=str(OUT/'result.json'),cpu_accounting_complete=False,external=external,worker_result=external['worker_result'],request=worker['request'],worker_log=log,audit_source=own,original_frozen_auditor=helper_ref,previous_failed_audit=dict(source=failed_source,outer=failed_outer_ref,stderr=failed_stderr,stdout=failed_stdout,metadata_diagnosis=diagnosis_ref,cpu_charge_seconds=str(D(str(failed_outer['elapsed_wall_seconds']))+D('.25')),wall_charge_seconds=str(D(str(failed_outer['elapsed_wall_seconds']))+D('.5')),scope='Full actual outer used as conservative single-thread CPU bound plus .25/.5 publication policy; numerical verification was unvisited'),request_association=conjunction,source_bindings_count=len(plan['source_bindings']),worker_status=worker['status'],worker_error=worker['error'],parent_publication_errors=console,retention_gaps=['No parent result.json','No retained parent/owned-Job aggregate CPU or terminal Job/memory/cleanup receipt','No saved private assembled record or any downstream registrar/control result'],scientific=science,recovered_assembly=dict(status='INDEPENDENTLY_DERIVED_SAVED_OUTPUT_ROWS_NOT_SUBJECT_PUBLISHED',qualification=h.QUAL,landmark_layout=['learned_ordinal','reference_feature_index','source_feature_index','score','reference_x_q8','reference_y_q8','source_x_q8','source_y_q8','digest','split_bit'],landmarks=[[r['learned_ordinal'],r['reference_feature_index'],r['source_feature_index'],r['score'],*r['reference_q8'],*r['source_q8'],r['digest'],0 if r['split']=='calibration' else 1] for r in capped],expanded_landmarks_canonical_sha256=h.sha(h.canonical(capped)),uncapped_truth=h.truth(raw_rows),capped_truth=h.truth(capped),population_relation=relation,sites=h.sites(capped),attempted_original_canonical_bytes=len(attempted_bytes),attempted_original_canonical_sha256=h.sha(attempted_bytes),prewrite_extent_bytes=pre_extent,prewrite_with_assembly_bytes=pre_extent+len(attempted_bytes),original_cap_bytes=8*h.MIB),worker_terminal=terminal,actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),accounting_scope='actual_final_work is conservative charged bookkeeping, not a fully measured CPU total. Full original local300 CPU reservation plus2 CPU publication headroom and failed-audit outer/tail charged because parent Job receipt is missing; actual worker CPU only a lower-bound sub-observation. Metadata conservatively charges all new bytes. Ordinary complete commission admission remains denied.',cpu_reservation_seconds=CPU_RESERVATION,missing_parent_publication_cpu_allowance_seconds=2,worker_observed_cpu_lower_bound_seconds=str(worker_cpu),parent_outer_wall_seconds=str(outer_delta),job=None,inventory=inv,inventory_total_bytes=total,inventory_binary_bytes=binary,unique_hashed_files=len(h.USED),runtime_unique_hashed_files=len(h.RUNTIME),commissioning=commissioned,audit_timing=dict(cpu_seconds=audit_cpu,wall_seconds=audit_wall),audit_publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),scope='Exact saved-prefix compatibility/truth audit only. No subject imports, images, new features, inference, registrar calls or numerical fit. All eleven original exports, full actual normalized values and one actual learned output are checked through independent choices. No learned real-pair quality or complete private commission claim. Inference observer remains UNTESTED_ONE_FORWARD. Root must check actual audit launcher tail before separately authorizing a saved-record continuation; incomplete CPU accounting is never promoted by this audit.')
    output=json.dumps(compact_refs(result),sort_keys=True,allow_nan=False,separators=(',',':')).encode();need(len(output)<=112*1024,'bounded112 KiB result');ledger=h.actual(HERE/'work/independent-sift-lightglue-audit-family-ledger.json')
    need(ledger['schema']=='m193c-sift-lightglue-audit-family-reservation-v2' and ledger['limit_bytes']==256*1024,'root-authorized family reservation')
    held=ledger['held_files'];need(len({r['path'] for r in held})==len(held) and any(h.same(r,own) for r in held),'complete distinct held family including current source')
    for r in held:h.file(h.path(r),r)
    reserved=ledger['reserved_outputs'];need(sum(r['bytes'] for r in held)+sum(reserved.values())==ledger['maximum_total_bytes']<=256*1024,'independent complete family arithmetic')
    need(reserved['v2_json']==112*1024 and reserved['family_ledger']==4096 and len(output)<=reserved['v2_json'] and (HERE/'work/independent-sift-lightglue-audit-family-ledger.json').stat().st_size<=4096,'actual serialization fits reserved slots')
    print(output.decode())


def integer_exit(x):return type(x) is int

if __name__=='__main__':main()
