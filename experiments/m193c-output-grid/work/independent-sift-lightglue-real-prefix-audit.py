"""SOURCE ONLY until root release: exact failed-real metadata prefix audit.
No subject imports, runtime-library hashes, images, normalization, inference or fit.
The original general auditor remains immutable and its main is never called.
"""
import time
START=time.perf_counter()
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
import sys
import traceback
import types
from decimal import Decimal as D
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/m193c-output-grid';WORK=HERE/'work'
OUT=HERE/'sift-lightglue-real-1';SELF=Path(__file__).resolve()
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
GENERAL=WORK/'independent-sift-lightglue-real-audit.py'
GENERAL_PIN=(84962,'df220b094f28dfca82b173ac529d7edad807817ce2e2aee06be36812b8d9b323')
GENERAL_LEDGER=WORK/'independent-sift-lightglue-real-audit-ledger.json'
GENERAL_LEDGER_PIN=(1811,'1d62fc42105b36bdc2ffa34e134a0c8d14f4cca6177da090157b90b499c4c158')
GENERAL_REVIEW=WORK/'independent-sift-lightglue-real-auditor-source-read.md'
GENERAL_REVIEW_PIN=(6943,'8c35696a050d2ecd68afdb1b102edd6b9f1f4d9ac268154eda9f5d3c0895eeb9')
LEDGER=WORK/'independent-sift-lightglue-real-prefix-audit-ledger.json'
PROGRESS=WORK/'independent-sift-lightglue-real-prefix-audit-progress.json'
ACTUAL_PINS={'worker/result.json':(65536,'f07f38142ec0fe04f6c80b9789be924aea3e1da54e879a3f9f834f2e1c1843be'),'request.json':(393,'7b317dfb1e0ac5df1bb3d1367ef6ce54180360565057b991beab57956c8baea2'),'worker/metadata/state/model-loading.json':(1447,'eac056c381e62157adf532675f0fa9f7ff5d648660f6e169c185ea40341a8ab3')}
KIB=1024;MIB=1<<20;TAIL=dict(cpu_seconds=.25,wall_seconds=.5)
OTHER_WORK=dict(cpu_seconds=10,wall_seconds=20,preparation_family_bytes=32768,scope='Full nonrefunded reservation for actual once-only accounting-callback-comparison-1; reserved, not measured CPU/wall. Its32KiB files are inside already charged1MiB preparation.')
EXTRA=dict(source=24*KIB,source_review=6*KIB,applicability=8*KIB,final=12*KIB,progress=4*KIB,staging=4*KIB,stderr=2*KIB,outer=2*KIB,ledger=2*KIB)
CALLER_FIELDS={'blocked_imports','model_load_completed','load_cpu_seconds','load_wall_seconds','import_guard_restored'}
LOADER_FIELDS=['checkpoint_keys','complete_parameter_coverage','config','constructor_buffer','deterministic_algorithms','device','expected_state_keys','features_argument','float32_matmul_precision','missing_state_keys','num_interop_threads','num_threads','unexpected_state_keys']
PHASES=[];PROGRESS_OWNED=False;G=None

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def compact(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def check():
    need(time.process_time()<=9.75 and time.perf_counter()-START<=19.5,'prefix audit10CPU/20wall including declared publication tail')
def bound_source(path,pin=None):
    check();path=Path(path);before=path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and path.resolve()==path and before.st_nlink==1 and not getattr(before,'st_file_attributes',0)&0x400 and 0<before.st_size<=128*KIB,'ordinary bounded immutable source')
    with path.open('rb') as f:
        opened=os.fstat(f.fileno());need((opened.st_dev,opened.st_ino,opened.st_size)==(before.st_dev,before.st_ino,before.st_size),'same opened source');raw=f.read(128*KIB+1)
    after=path.stat(follow_symlinks=False);need((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)==(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns),'unchanged source identity')
    ref=dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=sha(raw))
    if pin is not None:need((ref['bytes'],ref['sha256'])==pin,'frozen exact source pin')
    check();return ref,raw

def load_general():
    ref,raw=bound_source(GENERAL,GENERAL_PIN)
    tree_name='independent_real_prefix_reused_definitions'
    g=types.ModuleType(tree_name);g.__file__=str(GENERAL);sys.modules[tree_name]=g
    # Pinned module contains stdlib imports/constants/function definitions only;
    # its guarded main is not called. No subject or original helper math runs here.
    exec(compile(raw,str(GENERAL),'exec'),g.__dict__)
    original_file=g.file
    def controlled_file(path,expected=None,kind='metadata'):
        check();need(kind in ('metadata','payload'),'prefix excludes export/runtime/image/model reads')
        if kind=='payload':
            p=Path(path).resolve();need(p.parent==OUT/'worker/metadata/codec' and p.suffix=='.bin','only retained codec payloads; reject unexpected normalized/model payload before read')
        result=original_file(path,expected,kind);check();return result
    g.file=controlled_file
    return g,ref

def actual_ref(g,name):
    ref=g.file(OUT/name);need((ref['bytes'],ref['sha256'])==ACTUAL_PINS[name],'independently frozen actual prefix '+name);return ref

def output_copy(value):
    # Fresh output-only FileRefs; never normalize arbitrary strings or mutate
    # intrinsic inputs. Resolved path, byte extent and hash must be identical.
    if type(value) is dict:
        if set(value)=={'path','bytes','sha256'}:
            p=G.path(value);need(p.is_relative_to(ROOT),'output FileRef stays in held workspace')
            result=dict(value,path=p.relative_to(ROOT).as_posix());need(G.same(value,result),'same output-only resolved FileRef');return result
        return {k:output_copy(v) for k,v in value.items()}
    if type(value) in (list,tuple):return [output_copy(v) for v in value]
    return value

def remember(phase,summary=None,error=None):
    if error is None:PHASES.append(dict(phase=phase,status='VERIFIED_METADATA_PHASE_ONLY',summary=summary))
    if error is not None:error={k:error[k] for k in ('type','message','full_traceback_sha256','full_traceback_chars','truncated')}
    value=dict(schema='m193c-real-prefix-audit-progress-v1',status='AUDIT_INCOMPLETE',subject_complete=False,diagnostic_observations_verified=False,admission_allowed=False,active_phase=phase,visited=PHASES,error=error)
    data=compact(output_copy(value))
    if len(data)>4*KIB and error is not None:
        value['error']['message']='See retained stderr; full traceback hash and length retained';data=compact(output_copy(value))
    need(PROGRESS_OWNED and len(data)<=4*KIB,'bounded4KiB prefix partial')
    temporary=PROGRESS.with_suffix('.tmp');need(not temporary.exists(),'fresh4KiB staging')
    with temporary.open('xb') as f:need(f.write(data)==len(data),'complete partial');f.flush();os.fsync(f.fileno())
    os.replace(temporary,PROGRESS)

def request_association(g,parent,worker,request,ref,plan_ref):
    need(parent['request'] is None,'original emergency parent null is preserved')
    need(g.same(worker['request'],ref) and g.path(ref)==OUT/'request.json','explicit independent actual worker request')
    need(set(request)=={'schema','plan','prior_work'} and request['schema']=='m193c-real-lightglue-request-v1' and g.same(request['plan'],plan_ref),'exact request schema and plan')
    g.typed_work(request['prior_work']);need(worker['prior_work']==request['prior_work'] and all(D(str(request['prior_work'][k]))>=D(str(parent['prior_work'][k])) for k in request['prior_work']),'actual worker carry and monotone parent relation')
    return dict(parent_request_retained=False,worker_request=ref,request_plan=plan_ref,worker_prior_work=request['prior_work'],scope='Explicit independently authenticated request fallback. Parent record remains unaltered; no parent command/child accounting fabricated.')

def loader_projection(g,value,old,prefix):
    need(value['prior_field']=='model_loading' and g.same(value['prior_worker'],prefix['worker_result']),'actual loader prior association')
    names=value['compared_field_names'];prior=old['model_loading']
    need(names==LOADER_FIELDS and set(prior)-CALLER_FIELDS==set(LOADER_FIELDS),'exact source-derived13 loader fields, caller-only fields separate')
    need(type(value['blocked_imports']) is list and all(type(x) is str for x in value['blocked_imports']),'actual separately retained blocked imports')
    reconstruction={k:prior[k] for k in names};reconstruction['blocked_imports']=value['blocked_imports']
    need(sha(canonical(reconstruction))==value['actual_complete_loading_sha256'],'whole actual pre-exit loader witness identity')
    need(value['complete_parameter_coverage'] is True and value['config']==prior['config'] and value['constructor_buffer']==prior['constructor_buffer'],'complete loaded configuration and constructor buffer witness')
    return reconstruction

def powered(g,parent,worker,request,request_ref,plan_ref,loading,old,prefix):
    def copy(v):return g.strict(canonical(v))
    def rejects(fn):
        try:fn()
        except (ValueError,KeyError):return True
        return False
    positive=dict(request_ref,path=request_ref['path'].replace(str(ROOT)+'\\','').replace('\\','/'))
    request_association(g,parent,worker,request,positive,plan_ref)
    faults=[]
    for name,ref in (('path',dict(request_ref,path=str(OUT/'worker/result.json'))),('extent',dict(request_ref,bytes=request_ref['bytes']+1)),('hash',dict(request_ref,sha256='0'*64))):
        need(rejects(lambda:request_association(g,parent,worker,request,ref,plan_ref)),'powered request '+name);faults.append(name)
    bad=copy(request);bad['plan']['sha256']='0'*64
    need(rejects(lambda:request_association(g,parent,worker,bad,request_ref,plan_ref)),'wrong request plan');faults.append('plan')
    bad=copy(request);bad['prior_work']['cpu_seconds']+=1
    need(rejects(lambda:request_association(g,parent,worker,bad,request_ref,plan_ref)),'wrong request worker prior');faults.append('prior')
    baseline=loader_projection(g,loading,old,prefix);before=sha(canonical(loading))
    bad=copy(loading);bad['compared_field_names'].remove('config')
    need(rejects(lambda:loader_projection(g,bad,old,prefix)),'omitted actual loader field rejects')
    bad=copy(loading);bad['config']['n_layers']=8
    need(rejects(lambda:loader_projection(g,bad,old,prefix)),'changed configuration rejects')
    bad=copy(loading);bad['compared_field_names'].append('model_load_completed')
    need(rejects(lambda:loader_projection(g,bad,old,prefix)),'old caller field is not helper output')
    need(sha(canonical(loading))==before and loader_projection(g,loading,old,prefix)==baseline,'actual loader input restored unchanged')
    return dict(request_spelling_positive=True,request_destroyers=faults,loader_destroyers=['omitted_config','changed_n_layers','caller_field_invented_as_helper_output'],restored=True,scope='Metadata predicate controls only; no model, normalization or fit.')

def exact_terminal(g,ref,plan_ref,prior,schema,request):
    value=g.read(ref)
    expected=dict(schema=schema,implementation_version=g.VERSION,plan=plan_ref,request=request,prior_work=prior,cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,old_run_status='REFUSED',original_commission_complete=False,qualification=g.QUAL,status='REFUSED',publication_phase='INITIAL_INCOMPLETE',error=None)
    need(value==expected,'entire initial emergency refusal, no inferred counters or later fields')
    parsed,current=g.slot(g.path(ref),65536);need(parsed==expected and g.same(current,ref),'actual padded canonical emergency')
    return value

def main():
    global G,PROGRESS_OWNED
    parser=argparse.ArgumentParser()
    for name in ('source','ledger','plan','result','outer','console','exit'):parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args();need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,'exact no-bytecode Python/cwd')
    need(not PROGRESS.exists() and not PROGRESS.with_suffix('.tmp').exists(),'new prefix partial only');PROGRESS_OWNED=True
    own,_=bound_source(SELF);need(own['sha256']==args.source_sha256 and own['bytes']<=EXTRA['source'],'root frozen executed prefix source')
    ledger_ref,raw_ledger=bound_source(LEDGER);need(ledger_ref['sha256']==args.ledger_sha256 and ledger_ref['bytes']<=EXTRA['ledger'],'root frozen prefix ledger')
    g,reused=load_general();G=g;ledger=g.strict(raw_ledger)
    need(ledger['schema']=='m193c-real-prefix-audit-family-v1' and ledger['extra_reservations']==EXTRA and sum(EXTRA.values())==64*KIB and ledger['frozen_general_reservation_bytes']==320*KIB and ledger['total_family_limit_bytes']==384*KIB,'fixed additional64KiB, unchanged384KiB family')
    need(ledger['full_preparation_bound_bytes']==967369 and ledger['full_preparation_with_root_metadata_bytes']==975154 and ledger['other_work']==OTHER_WORK and ledger['full_preparation_with_other_work_bytes']==1007922 and 1007922<MIB,'whole conservative preparation remains inside1MiB')
    for path,pin in ((GENERAL_LEDGER,GENERAL_LEDGER_PIN),(GENERAL_REVIEW,GENERAL_REVIEW_PIN)):bound_source(path,pin)
    remember('initialization',dict(source=own,ledger=ledger_ref,general_main_executed=False))
    paths=dict(plan=HERE/'sift-lightglue-real-plan-1.json',result=OUT/'result.json',outer=WORK/'sift-lightglue-real-1-outer.json',console=WORK/'sift-lightglue-real-1-console.txt',exit=WORK/'sift-lightglue-real-1-exit.txt');external={}
    for key,path in paths.items():
        ref=g.file(path);need(ref['sha256']==getattr(args,key+'_sha256'),'released exact '+key);external[key]=ref
    plan=g.read(external['plan']);outer=g.read(external['outer']);parent=g.read(external['result'])
    for name,pin in plan['source_bindings'].items():g.file(ROOT/name,dict(path=name,**pin))
    need(plan['source_bindings'][GENERAL.relative_to(ROOT).as_posix()]==dict(bytes=GENERAL_PIN[0],sha256=GENERAL_PIN[1]),'original general auditor remained source-bound and unexecuted')
    need(g.path(plan['python_executable'])==PYTHON,'same actual executable path');g.file(PYTHON,plan['python_executable'])
    old,private,prior_audit,prior=g.authority(plan)
    parent=exact_terminal(g,external['result'],external['plan'],prior,'m193c-sift-lightglue-real-run-v1',None)
    worker_ref=actual_ref(g,'worker/result.json');worker=g.read(worker_ref);request_ref=actual_ref(g,'request.json');request=g.read(request_ref)
    worker=exact_terminal(g,worker_ref,external['plan'],request['prior_work'],'m193c-sift-lightglue-real-worker-v1',worker['request'])
    association=request_association(g,parent,worker,request,request_ref,external['plan'])
    expected_argv=g.replace(plan['commands']['parent'],external['plan']['sha256'])
    need(outer['command']==expected_argv and outer['plan_sha256']==external['plan']['sha256'] and outer['exit_code']==1 and outer['admissible_parent_exit'] is True and g.raw(external['exit']).strip()==b'1','actual unsuccessful parent command/outer')
    need(type(outer['elapsed_wall_seconds']) in (float,int) and 0<=outer['elapsed_wall_seconds']<=180,'actual full outer wall')
    console=g.lines(external['console']);need(len(console)==1 and console[0]['status']=='REFUSED','one actual terminal refusal line')
    pub=console[0]['publication'];need(pub['passed'] is False and pub['canonical_refusal_verified'] is True and g.same(pub['canonical'],external['result']) and pub['first_positive'] is None and pub['error']==dict(type='ValueError',message='local cap',phase='CANONICAL_REPLACEMENT') and pub['phase']=='TERMINAL_REFUSAL','actual canonical emergency overrides failed publication')
    need(pub['revocation_errors']==[dict(stage=x,type='ValueError',message='local cap') for x in ('detailed','emergency')],'both actual postcheck failures retained')
    log=g.file(OUT/'worker.log');need(log['bytes']==0 and g.raw(log)==b'','actual empty worker log; no command/CPU inferred')
    for root,expected in ((OUT,parent),(OUT/'worker',worker)):
        for name in g.NAMES:
            path=root/name
            if path.exists():value,ref=g.slot(path,65536);need(value==expected,'all actual surviving initial terminal slots')
            else:need(root==OUT and name=='emergency-refusal.json','only consumed parent emergency slot missing')
    remember('actual-emergency-authority',dict(worker=worker_ref,request=request_ref,parent_request=None,log=log,status='REFUSED'))
    absent=['child-observation.json','runtime/parent-final.json','worker/runtime/worker-before.json','worker/runtime/worker-after.json','worker/metadata/state/initial-registry.json','worker/metadata/state/import-guard-final.json','worker/metadata/manifest/population.json','worker/metadata/manifest/inputs.json']
    need(all(not (OUT/name).exists() for name in absent),'all named post-loader and process receipts remain absent')
    final_ref=g.file(OUT/'worker/publication-control-result.json');final=g.read(final_ref);prefixes=final['controls']
    need(final['passed'] is True and len(prefixes)==7,'actual seven-control final index')
    summaries=[]
    for i,ref in enumerate(prefixes,1):
        need(g.path(ref)==OUT/'worker'/('publication-progress-'+str(i)+'.json'),'fixed actual linked publication files')
        row=g.read(ref)['row'];summaries.append(dict(id=row['id'],passed=row['passed'],error=row.get('error')))
    projection=dict(publication_control_prefixes=prefixes,publication_control_summary=summaries,publication_controls=final_ref,fits=[],status='REFUSED')
    publisher_rows=g.publication_controls(projection);need(len(publisher_rows)==7 and all(x['passed'] for x in publisher_rows),'independent actual seven publisher groups')
    remember('actual-publisher-controls',dict(final=final_ref,verified_groups=7,scope='Explicit projection of actual linked records; not a repaired worker result'))
    codec_rows=[]
    for i,name in enumerate(g.CODEC_IDS,1):
        ref=g.file(OUT/'worker/metadata/codec'/('control-'+str(i)+'.json'));row=g.read(ref);need(row['id']==name,'fixed actual codec receipt order');codec_rows.append(dict(id=name,passed=row['passed']))
    cached_ref=old['learned_output'];cached=g.read(cached_ref)
    verified_codec=g.codec_controls(dict(codec_controls=codec_rows),cached);need(len(verified_codec)==10,'all ten independently reconstructed codec groups')
    remember('actual-codec-controls',dict(cached_prediction=cached_ref,verified_groups=10,scope='Full original cached tensor/value identity and powered retained mutants; zero model calls'))
    loading_ref=actual_ref(g,'worker/metadata/state/model-loading.json');loading=g.read(loading_ref)
    loaded=loader_projection(g,loading,old,plan['private_baseline']['commission_prefix']);controls=powered(g,parent,worker,request,request_ref,external['plan'],loading,old,plan['private_baseline']['commission_prefix'])
    remember('actual-loader-witness',dict(record=loading_ref,compared_fields=13,recorded_parameter_coverage=True,runtime_or_model_state_verified=False,controls=controls))
    consumed={str(g.path(ref)) for ref in g.USED.values() if g.path(ref).is_relative_to(OUT)}
    inv=g.inventory();need({str(g.path(ref)) for ref in inv}==consumed and len(inv)==63 and sum(x['bytes'] for x in inv)==750878,'closed actual63-file750878-byte metadata/control inventory, no unseen later observation')
    for path,identity in g.IDENTITIES.items():need(g.ident(Path(path).stat(follow_symlinks=False))==identity,'all retained metadata/control identities unchanged')
    check();cpu=time.process_time();wall=time.perf_counter()-START
    subject=dict(cpu_seconds=float(D(str(prior['cpu_seconds']))+D(102)),wall_seconds=float(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),file_bytes=prior['file_bytes']+8*MIB,metadata_bytes=prior['metadata_bytes']+8*MIB)
    carry=dict(subject);carry['cpu_seconds']=float(D(str(subject['cpu_seconds']))+D(OTHER_WORK['cpu_seconds'])+D(str(cpu))+D('.25'));carry['wall_seconds']=float(D(str(subject['wall_seconds']))+D(OTHER_WORK['wall_seconds'])+D(str(wall))+D('.5'))
    need(carry['cpu_seconds']<=1200 and carry['wall_seconds']<=1800 and carry['file_bytes']<=4<<30 and carry['metadata_bytes']<=128*MIB,'conservative actual-prefix carry remains globally bounded')
    result=dict(schema='m193c-saved-sift-lightglue-real-prefix-audit-v1',status='PASS_SAVED_REAL_LIGHTGLUE_METADATA_PREFIX_AUDIT',saved_metadata_prefix_verified=True,subject_complete=False,diagnostic_observations_verified=False,admission_allowed=False,cpu_accounting_complete=False,new_run_cpu_accounting_complete=False,model_runtime_verified=False,model_state_verified=False,guard_restoration_verified=False,scientific_call_counters_retained=False,scientific_call_counts=None,subject_status='REFUSED',worker_status='REFUSED',external=external,worker_result=worker_ref,request_association=association,worker_log=log,missing_receipts=absent,source_gate=dict(label='DERIVED',last_durable_receipt='model-loading.json',next_required_receipt='runtime/worker-before.json',scope='Held controller must return from runtime receipt publication before state/input/private inference. No retained call counters, current-runtime proof or real scientific observations; absence is not zero cost.'),real_pair_observations=0,real_pair_unvisited=[list(x) for x in g.PAIRS],publication_controls=publisher_rows,codec_controls=verified_codec,loader_witness=dict(record=loading_ref,compared_fields=LOADER_FIELDS,caller_fields_excluded=sorted(CALLER_FIELDS-{'blocked_imports'}),current_blocked_imports=loading['blocked_imports'],whole_witness_sha256=sha(canonical(loaded)),scope='Recorded strict loader compatibility only. No model parameter bytes or runtime libraries reread.'),metadata_controls=controls,inventory=dict(count=len(inv),actual_bytes=sum(x['bytes'] for x in inv),canonical_sha256=sha(canonical(inv)),scope='All actual owned files, including zero/hidden names; separate from charged reservations'),accounting=dict(subject_final_work=subject,cpu_reservation_seconds=102,extent_reservation_bytes=8*MIB,actual_parent_outer_wall_seconds=outer['elapsed_wall_seconds'],job_cpu_retained=False,charged_path_extents_retained=False,scope='Full released100CPU plus2CPU publication allowance and8MiB reservations. Actual outer wall only; no measured workerCPU or original local-cap cause inferred.'),other_work_reserved=OTHER_WORK,actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),audit_source=own,reused_frozen_general_source=reused,general_main_executed=False,audit_family=dict(ledger=ledger_ref,extra_reservations=EXTRA,total_limit_bytes=384*KIB),audit_timing=dict(cpu_seconds=cpu,wall_seconds=wall),audit_publication_allowance=TAIL,audit_caps=dict(cpu_seconds=10,wall_seconds=20),progress=g.file(PROGRESS),scope='Only retained metadata, padded publication controls and cached-prediction codec payloads are independently verified. Original failed subject and historical CPU gap stay false. No new image, normalization, model/checkpoint/runtime-library read, inference or fit. Root must verify exact outer/output pins and actual audit time<=sample+.5wall before continuation.')
    data=compact(output_copy(result));need(len(data)<=12*KIB,'bounded12KiB actual final');check();sys.stdout.buffer.write(data);sys.stdout.flush()

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        full=traceback.format_exc();detail=dict(type=type(exc).__name__,message=str(exc)[:384],traceback_suffix=full[-900:],full_traceback_chars=len(full),full_traceback_sha256=sha(full.encode()),truncated=len(full)>900)
        try:
            if PROGRESS_OWNED:remember('audit-refused',error=detail)
        except BaseException as secondary:detail['partial_error']=str(secondary)[:160]
        data=compact(dict(status='AUDIT_REFUSED',error=detail))
        if len(data)>2*KIB:
            detail.pop('traceback_suffix',None);detail['message']='Oversized escaped error; full traceback hash and length retained';data=compact(dict(status='AUDIT_REFUSED',error=detail))
        need(len(data)<=2*KIB,'bounded retained stderr');sys.stderr.buffer.write(data);sys.stderr.flush();raise SystemExit(1)
