# Prospective independent saved-outcome audit. No execution until root release.
# General-auditor main and all subject/model/image/registrar imports remain unused.
import time
START=time.perf_counter()
import argparse,ast,hashlib,json,math,os,stat,struct,sys,traceback,types
from decimal import Decimal as D,ROUND_CEILING
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=ROOT/'experiments/m193c-output-grid';WORK=HERE/'work'
SELF=Path(__file__).resolve();OUT=HERE/'real-accounting-repair-2'
GENERAL=WORK/'independent-sift-lightglue-real-audit.py'
GENERAL_PIN=(84962,'df220b094f28dfca82b173ac529d7edad807817ce2e2aee06be36812b8d9b323')
PREFIX=WORK/'independent-sift-lightglue-real-prefix-audit.json'
PREFIX_PIN=(11333,'4f8b48d9edf19fdac45c38aaf3bab85364e853a721827d4415d4d7dcb91cc66f')
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
PROGRESS=WORK/'independent-real-accounting-repair-v2-audit-progress.json'
LEDGER=WORK/'independent-real-accounting-repair-v2-audit-ledger.json'
KIB=1024;MIB=1<<20
LIMITS=dict(cpu_seconds=1440,wall_seconds=1800,file_bytes=4<<30,metadata_bytes=128*MIB)
OLD_LIMITS=dict(LIMITS,cpu_seconds=1320)
ALLOW=dict(cpu_seconds=20,wall_seconds=30,file_bytes=MIB,metadata_bytes=MIB)
ATTEMPT=dict(cpu_seconds=100,wall_seconds=180,file_bytes=8*MIB,metadata_bytes=8*MIB)
AUDIT_CAPS=dict(cpu_seconds=25,wall_seconds=40);TAIL=dict(cpu_seconds=.25,wall_seconds=.5)
RESERVES=dict(source=96*KIB,final=128*KIB,progress=32*KIB,staging=32*KIB,stderr=8*KIB,outer=4*KIB,source_review=16*KIB,report=8*KIB,ledger=4*KIB)
VERSION='m193c-real-accounting-repair-v2';SCIENCE_VERSION='m193c-sift-lightglue-real-v1'
COMPLETE='COMPLETE_FIXED_REAL_LIGHTGLUE_DIAGNOSTIC_ONLY'
LOADER_FIELDS='checkpoint_keys complete_parameter_coverage config constructor_buffer deterministic_algorithms device expected_state_keys features_argument float32_matmul_precision missing_state_keys num_interop_threads num_threads unexpected_state_keys'.split()
CALLER_FIELDS={'blocked_imports','import_guard_restored','load_cpu_seconds','load_wall_seconds','model_load_completed'}
G=None;PHASES=[];PROGRESS_OWNED=False
PHASE_CAPS=dict(initialization=1*KIB,authority_operational_controls=4*KIB,worker_publication_controls=2*KIB,saved_export_codec=3*KIB,actual_normalized_components=7*KIB,actual_science_prefix=3*KIB,worker_scientific_outcome=2*KIB,runtime_and_current_Job=4*KIB,resource_accounting=1*KIB)
FINAL_SECTIONS={
 'authority':(18*KIB,'external worker_result actual_request resource_authorization private_baseline failed_real_baseline callback_baseline failed_repair_baseline evidence_bindings previous_audit_semantics source_evidence_controls audit_source reused_general_source reviewed_replacement audit_family audit_progress accounting_implementation'),
 'operational':(5*KIB,'operational_controls live_wrapper_controls'),
 'terminal':(10*KIB,'parent_terminal worker_terminal parent_accounting_sample worker_accounting_sample'),
 'science':(68*KIB,'scientific'),
 'normalization':(8*KIB,'normalization model_state_witness'),
 'runtime':(4*KIB,'runtime parent_runtime graph guard_restoration'),
 'accounting':(6*KIB,'accounting'),
 'publication':(5*KIB,'publication_controls codec_controls'),
 'other':(4*KIB,'')}

def need(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def compact(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def check():
    need(time.process_time()<=AUDIT_CAPS['cpu_seconds']-TAIL['cpu_seconds'] and time.perf_counter()-START<=AUDIT_CAPS['wall_seconds']-TAIL['wall_seconds'],'whole audit before reserved publication tail')
def source_bytes(path,expected=None):
    path=Path(path);before=path.stat(follow_symlinks=False)
    identity=lambda x:(x.st_dev,x.st_ino,x.st_size,x.st_mtime_ns,getattr(x,'st_file_attributes',0),x.st_nlink)
    need(path.resolve()==path and stat.S_ISREG(before.st_mode) and before.st_nlink==1 and not getattr(before,'st_file_attributes',0)&0x400 and 0<before.st_size<=128*KIB,'ordinary exact bounded source')
    with path.open('rb') as stream:
        need(identity(os.fstat(stream.fileno()))==identity(before),'source opened identity');data=stream.read(128*KIB+1)
        need(identity(os.fstat(stream.fileno()))==identity(before),'source handle unchanged')
    need(identity(path.stat(follow_symlinks=False))==identity(before) and len(data)==before.st_size,'source unchanged through complete read')
    if expected is not None:need((len(data),sha(data))==expected,'exact immutable source pin')
    check();return data

def load_general():
    data=source_bytes(GENERAL,GENERAL_PIN)
    module=types.ModuleType('independent_repair_saved_definitions');module.__file__=str(GENERAL)
    sys.modules[module.__name__]=module
    exec(compile(data,str(GENERAL),'exec'),module.__dict__)
    # A new observed output directory, not changed scientific predicates or inputs.
    module.OUT=OUT
    old_file=module.file
    def bounded_file(*args,**kwargs):
        check();value=old_file(*args,**kwargs);check();return value
    module.file=bounded_file
    return module

def output_copy(value):
    if type(value) is dict:
        if set(value)=={'path','bytes','sha256'}:
            p=G.path(value)
            if p.is_relative_to(ROOT):
                result=dict(value,path=p.relative_to(ROOT).as_posix());need(G.same(value,result),'lossless output-only FileRef spelling');return result
            return dict(value)
        return {key:output_copy(item) for key,item in value.items()}
    if type(value) in (list,tuple):return [output_copy(item) for item in value]
    return value

def remember(phase,summary=None,error=None):
    if error is None:
        row=dict(phase=phase,status='VERIFIED_PHASE_ONLY',summary=summary)
        need(phase.replace('-','_') in PHASE_CAPS and len(compact(output_copy(row)))<=PHASE_CAPS[phase.replace('-','_')],'declared compact phase extent')
        PHASES.append(row)
    value=dict(schema='m193c-real-accounting-repair-v2-audit-progress-v1',status='AUDIT_INCOMPLETE',subject_complete=False,admission_allowed=False,active_phase=phase,visited=PHASES,error=error)
    data=compact(output_copy(value));need(PROGRESS_OWNED and len(data)<=RESERVES['progress'],'bounded phase progress')
    temporary=PROGRESS.with_suffix('.tmp');need(not temporary.exists(),'fresh atomic progress stage')
    with temporary.open('xb') as stream:need(stream.write(data)==len(data),'complete phase write');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,PROGRESS)

def bound_ref(g,ref,pin=None):
    actual=g.file(g.path(ref),ref)
    if pin is not None:need((actual['bytes'],actual['sha256'])==pin,'explicit prior outcome pin')
    return actual

def source_ref(g,plan,path):
    key=Path(path).relative_to(ROOT).as_posix();need(key in plan['source_bindings'],'closed required source')
    return bound_ref(g,dict(path=key,**plan['source_bindings'][key]))

PREVIOUS=WORK/'independent-real-accounting-repair-audit.py'
PREVIOUS_PIN=(73261,'71f7b6f83354f1e8195f3bc5c7898a799f0fdfe1f6197a82a0f1d94cedf12dd3')
FAILED_AUDIT_PIN=(16641,'7a86134c6e2e570194caac609824e8e54f1a86c5c7bff0ad02e1af470aa16447')
EMPTY_SHA=sha(b'')
EMPTY_PATHS=('experiments/m193c-output-grid/work/independent-sift-lightglue-real-prefix-audit-stderr.txt','experiments/m193c-output-grid/work/independent-real-accounting-repair-audit-stderr.txt')
V2_PINS={'real-accounting-repair-v2-run.py': (17916, '6422d6ce08b51d179d29f95eb0a3cf69c37657554c1ed511c0bf28c6a7b6ea39'), 'real-accounting-repair-v2-support.py': (2243, '2b2ece0185c7a55eace5bba46632ea0afd8a1632fe65f9188dcc7b4cd813b248'), 'real-accounting-repair-v2-preregister.md': (15215, '383a423f460bddf9d881b5947b4daec18b1586edb4604f9dc1f789d2c704c2f4')}  # Filled only after independent controller source review.

def previous_definitions():
    data=source_bytes(PREVIOUS,PREVIOUS_PIN);m=types.ModuleType('immutable_previous_repair_audit_authority');m.__file__=str(PREVIOUS)
    sys.modules[m.__name__]=m;exec(compile(data,str(PREVIOUS),'exec'),m.__dict__)
    return m

def namespaces(sources,evidence):
    need(type(sources) is dict and type(evidence) is dict and set(evidence)==set(EMPTY_PATHS),'closed explicit two-path empty diagnostic namespace')
    for key,value in sources.items():
        need(type(key) is str and (ROOT/key).resolve().is_relative_to(ROOT) and (ROOT/key).resolve().relative_to(ROOT).as_posix()==key and type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and value['bytes']>0 and type(value['sha256']) is str and len(value['sha256'])==64 and all(x in '0123456789abcdef' for x in value['sha256']),'positive executable/source/metadata binding contract')
    need(not set(sources).intersection(evidence),'empty evidence never reaches native binding_map')
    need(all(type(value) is dict and set(value)=={'bytes','sha256'} and type(value['bytes']) is int and value['bytes']==0 and value['sha256']==EMPTY_SHA for value in evidence.values()),'exact typed empty extent and full digest')

def authority(g,plan):
    keys='schema source_bindings private_baseline failed_real_baseline callback_baseline resource_authorization prior_work preparation_allowance python_executable commands failed_repair_baseline evidence_bindings'.split()
    need(set(plan)==set(keys) and plan['schema']=='m193c-real-accounting-repair-plan-v2' and plan['preparation_allowance']==ALLOW,'closed surgical twelve-key authority')
    namespaces(plan['source_bindings'],plan['evidence_bindings'])
    for key,value in plan['evidence_bindings'].items():bound_ref(g,dict(path=key,**value))
    # Different choice of namespace, with powered metadata faults only. No file mutation.
    for name in ('source-zero','source-bool','unknown-empty','nonempty-evidence','evidence-bool','wrong-empty-hash','overlap'):
        sources=dict(plan['source_bindings']);evidence={k:dict(v) for k,v in plan['evidence_bindings'].items()};key=next(iter(sources))
        if name=='source-zero':sources[key]=dict(sources[key],bytes=0)
        elif name=='source-bool':sources[key]=dict(sources[key],bytes=True)
        elif name=='unknown-empty':evidence['experiments/m193c-output-grid/work/UNLISTED-empty.txt']=dict(bytes=0,sha256=EMPTY_SHA)
        elif name=='nonempty-evidence':evidence[EMPTY_PATHS[0]]['bytes']=1
        elif name=='evidence-bool':evidence[EMPTY_PATHS[0]]['bytes']=False
        elif name=='wrong-empty-hash':evidence[EMPTY_PATHS[0]]['sha256']='f'*64
        else:sources[EMPTY_PATHS[0]]=dict(bytes=1,sha256='f'*64)
        need(g.rejection(lambda:namespaces(sources,evidence)),'powered namespace fault '+name)
    failed=plan['failed_repair_baseline'];need(set(failed)==set('plan result outer console exit audit'.split()),'closed actual failed-repair bundle')
    for ref in failed.values():bound_ref(g,ref)
    bound_ref(g,failed['audit'],FAILED_AUDIT_PIN);a=g.read(failed['audit']);oldplan=g.read(failed['plan']);parent=g.read(failed['result'])
    need(a['schema']=='m193c-saved-real-accounting-repair-audit-v1' and a['status']=='PASS_SAVED_REAL_ACCOUNTING_REPAIR_OUTCOME_AUDIT' and set(a['external'])==set(failed)-{'audit'} and all(g.same(a['external'][k],failed[k]) for k in a['external']),'actual original audit and exact five external references')
    need(all(a[k] is False for k in ('subject_complete','diagnostic_observations_verified','verified_worker_scientific_population','admission_allowed','cpu_accounting_complete')) and a['worker_result'] is None and a['new_run_cpu_accounting_complete'] is True,'legitimate parent-only current accounting; old science unvisited and historical gap retained')
    need(a['operational_exceptions']==['OBSERVED_RESOURCE_ENVELOPE_EXCEEDED'] and a['accounting']['resource_bounds']==dict(cumulative=True,last_measured_transport_within_attempt=False,subject_cpu_with_tail=True,subject_outer_wall=True),'preserve old completeness-conditioned false sentinel; not observed cap evidence')
    need(parent['status']=='REFUSED' and parent['active_phase']=='authority' and parent['request'] is parent['worker_result'] is None and parent['child_launch_entered'] is False and parent['counters']==dict(images=0,extractions=0,normalizations=0,model_forwards=0,registrar_calls=0),'actual first-attempt prelaunch refusal and zero saved counters')
    original=previous_definitions();old,private,older_prefix,oldprior,oldgrant,probe=original.authority(g,oldplan)
    need(a['audit_source']['bytes']==PREVIOUS_PIN[0] and a['audit_source']['sha256']==PREVIOUS_PIN[1],'exact old audit authority source')
    audit_outer_ref=g.file(WORK/'independent-real-accounting-repair-audit-outer.json');need((audit_outer_ref['bytes'],audit_outer_ref['sha256'])==(1026,'8c6f40cbe643e8b13c8504eba2874f983c1e16d249bcc69fd38ec5a82727375c'),'actual old audit launch pin')
    old_outer=g.read(audit_outer_ref);stderr=bound_ref(g,dict(path=EMPTY_PATHS[1],**plan['evidence_bindings'][EMPTY_PATHS[1]]));bound_ref(g,a['audit_progress'])
    argv=[str(PYTHON),'-B',str(PREVIOUS),'--source-sha256',PREVIOUS_PIN[1],'--ledger-sha256',a['audit_family']['ledger']['sha256']]
    for key in ('plan','result','outer','console','exit'):argv+=['--'+key+'-sha256',failed[key]['sha256']]
    need(old_outer['command']==argv and old_outer['exit_code']==0 and old_outer['stdout_bytes']==failed['audit']['bytes'] and old_outer['stderr_bytes']==stderr['bytes']==0 and old_outer['elapsed_wall_seconds']<=a['audit_timing']['wall_seconds']+a['audit_publication_allowance']['wall_seconds'],'actual once-only old audit and final tail')
    need(plan['private_baseline']==oldplan['private_baseline'] and plan['failed_real_baseline']==oldplan['failed_real_baseline'] and plan['callback_baseline']==oldplan['callback_baseline'],'unchanged older scientific/failed/probe prerequisites')
    positive={k:v for k,v in oldplan['source_bindings'].items() if v['bytes']>0};empty={k:v for k,v in oldplan['source_bindings'].items() if v['bytes']==0}
    need(len(positive)==295 and empty=={EMPTY_PATHS[0]:dict(bytes=0,sha256=EMPTY_SHA)} and all(plan['source_bindings'].get(k)==v for k,v in positive.items()),'exact old295 positive bindings retained; one named diagnostic moved without changing native reader')
    need(g.path(audit_outer_ref).relative_to(ROOT).as_posix() in plan['source_bindings'],'actual old audit outer included as positive proof')
    grant=g.read(plan['resource_authorization']);fields='schema status previous_cumulative_limits additional_authorized_work new_cumulative_limits preparation_allowance attempt_caps previous_charged_work previous_ceiling_disposition new_output failed_prefix_audit callback_result replacement_sources failed_repair_audit evidence_bindings'.split()
    need(set(grant)==set(fields) and grant['schema']=='m193c-real-accounting-repair-resource-authorization-v2' and grant['status']=='AUTHORIZED_SINGLE_FRESH_OPERATIONAL_REPLACEMENT' and grant['previous_cumulative_limits']==OLD_LIMITS and grant['new_cumulative_limits']==LIMITS and grant['additional_authorized_work']==dict(cpu_seconds=120,wall_seconds=0,file_bytes=0,metadata_bytes=0),'explicit finite1320 to1440 CPU grant')
    need(grant['preparation_allowance']==ALLOW and grant['attempt_caps']==ATTEMPT and grant['previous_ceiling_disposition']=='RETIRED_NOT_RESET' and (ROOT/grant['new_output']).resolve()==OUT and grant['evidence_bindings']==plan['evidence_bindings'],'unchanged preparation/local caps, fresh exact output and diagnostic namespace')
    need(g.same(grant['failed_prefix_audit'],plan['failed_real_baseline']['audit']) and g.same(grant['callback_result'],plan['callback_baseline']['result']) and g.same(grant['failed_repair_audit'],failed['audit']),'new and historical evidence associations')
    need(set(grant['replacement_sources'])=={'runner','support','spec'},'closed new source roles')
    for role,name in (('runner','real-accounting-repair-v2-run.py'),('support','real-accounting-repair-v2-support.py'),('spec','real-accounting-repair-v2-preregister.md')):need(g.same(grant['replacement_sources'][role],source_ref(g,plan,HERE/name)),'exact authorized v2 '+role)
    base=a['actual_final_work'];prior=g.read(plan['prior_work']);g.typed_work(base);g.typed_work(prior)
    need(base==dict(cpu_seconds=1292.771803,wall_seconds=1193.6198098999992,file_bytes=4059662381,metadata_bytes=68401447) and grant['previous_charged_work']==base and D(a['next_wall_seconds'])==D(str(base['wall_seconds'])),'full actual old102CPU policy charge and spent reservations retained')
    for key in ALLOW:
        value=D(str(base[key]));value=value.quantize(D('.000001'),rounding=ROUND_CEILING) if key.endswith('seconds') else value
        need(D(str(prior[key]))==value+ALLOW[key],'upward microsecond carry plus full preparation')
    need(prior['cpu_seconds']+100>1320 and all(D(str(prior[k]))+ATTEMPT[k]<=LIMITS[k] for k in ALLOW),'new full attempt affordable only under explicit extension')
    return old,private,a,prior,grant,probe

def model_witness(g,worker,old):
    # Re-choose actual13-field loader return, preserving all original input objects.
    if not worker.get('model_loading'):return None,None
    loading=g.read(worker['model_loading']);prior=old['model_loading']
    need(g.same(loading['prior_worker'],worker['private_baseline']['commission_prefix']['worker_result']) and loading['prior_field']=='model_loading' and loading['compared_field_names']==LOADER_FIELDS and set(prior)-CALLER_FIELDS==set(LOADER_FIELDS),'complete source-derived actual loader-return field population')
    actual={k:prior[k] for k in LOADER_FIELDS};actual['blocked_imports']=loading['blocked_imports']
    need(type(loading['blocked_imports']) is list and all(type(x) is str for x in loading['blocked_imports']) and sha(canonical(actual))==loading['actual_complete_loading_sha256'],'whole pre-exit loader witness')
    need(loading['complete_parameter_coverage'] is True and loading['config']==prior['config'] and loading['constructor_buffer']==prior['constructor_buffer'],'entire loaded configuration witness')
    if not worker.get('state_registry'):return None,dict(loading=worker['model_loading'],scope='Recorded13-field loader compatibility only; no state registry retained')
    state=g.read(worker['state_registry']);rows=state['rows']
    need(state['schema']=='m193c-real-state-registry-v1' and rows==sorted(rows) and len({r[0] for r in rows})==len(rows)>0,'unique complete sorted state registry')
    need(all(type(r) is list and len(r)==4 and r[1]=='torch.float32' and all(g.integer(x) and x>=0 for x in r[2]) and type(r[3]) is str and len(r[3])==64 and all(x in '0123456789abcdef' for x in r[3]) for r in rows),'typed complete state hash witnesses')
    need(sha(canonical(rows))==state['canonical_sha256'] and [r[0] for r in rows]==prior['expected_state_keys'],'whole actual state names and canonical identity')
    mappings={r['destination']:r for r in prior['checkpoint_keys']};buffer=prior['constructor_buffer']
    for name,dtype,shape,digest in rows:
        if name==buffer['name']:need(shape==[9] and digest==sha(struct.pack('<9f',*buffer['values'])),'constructor buffer byte witness versus held values')
        else:need(name in mappings and dtype==mappings[name]['dtype'] and shape==mappings[name]['shape'],'all admitted learned types and shapes')
    return state,dict(loading=worker['model_loading'],registry=worker['state_registry'],compared_loader_fields=LOADER_FIELDS,state_entries=len(rows),initial_state_sha256=state['canonical_sha256'],scope='Complete recorded parameter hashes, not independently reread parameter payloads; caller-only loading markers excluded')


def compact_slot(g,ref,capacity):
    # Operational slots are compact JSON; publisher slots alone use indent=2.
    data=g.raw(ref);value=g.strict(data);original=compact(value)
    need(len(data)==capacity and len(original)<=capacity and data==original+b' '*(capacity-len(original)),'exact compact operational slot plus declared padding')
    return value

def named_record(g,declared,path,capacity=None):
    # Preserve a saved-but-unreturned finalizer record without modifying its parent.
    if declared is not None:
        need(g.path(declared)==path,'fixed actual receipt location');ref=bound_ref(g,declared)
    elif path.exists():ref=g.file(path)
    else:return None,None,False
    return (compact_slot(g,ref,capacity) if capacity else g.read(ref)),ref,declared is not None

def source_evidence_receipt(g,value,plan,root):
    row,ref,linked=named_record(g,value.get('source_evidence_controls'),root/'metadata/controller/source-evidence-controls.json')
    if row is None:
        need(value['status']!=COMPLETE,'complete source/evidence control receipt')
        return dict(visited=False,process_link_retained=False,record=None)
    need(ref['bytes']<=4096 and g.raw(ref)==compact(row),'actual compact bounded metadata namespace receipt')
    witnesses=[]
    for name in EMPTY_PATHS:
        actual=bound_ref(g,dict(path=name,**plan['evidence_bindings'][name]))
        identity=list(g.IDENTITIES[str(g.path(actual))])
        need(len(identity)==6 and identity[2]==0 and identity[5]==1,'owned same-handle empty identity and single link')
        witnesses.append(dict(path=name,bytes=0,sha256=EMPTY_SHA,metadata=identity))
    faults=[('empty-as-source','typed FileRef'),('unexpected-empty-role','closed two-empty diagnostic namespace'),('nonzero-diagnostic-declaration','exact allowed empty diagnostic'),('wrong-empty-digest','exact allowed empty diagnostic'),('false-zero-diagnostic','closed two-empty diagnostic namespace'),('source-intake-zero','positive source extent and digest')]
    rows=[dict(id='actual-positive-sources-and-two-empty-evidence',passed=True,source_count=len(plan['source_bindings']),empty_count=2)]
    rows += [dict(id=name,passed=True,error=error) for name,error in faults]
    rows.append(dict(id='restored-positive-placebo',passed=True,namespace_sha256=sha(compact(dict(sources=plan['source_bindings'],evidence=plan['evidence_bindings'])))))
    expected=dict(schema='m193c-positive-source-empty-evidence-controls-v1',status='PASS_METADATA_NAMESPACE_ONLY',rows=rows,empty_witnesses=witnesses,source_namespace_sha256=sha(compact(plan['source_bindings'])),evidence_namespace_sha256=sha(compact(plan['evidence_bindings'])),scope='metadata only; no source/content edits or scientific calls')
    need(row==expected,'complete exact source/evidence controls, identities, ordering, restored hashes and error messages')
    if value['status']==COMPLETE:need(linked,'complete process retained its actual source/evidence receipt')
    return dict(visited=True,process_link_retained=linked,record=ref,rows=8,rejected=6,source_count=len(plan['source_bindings']),empty_count=2,complete_record_canonical_sha256=sha(canonical(row)),scope='Actual unchanged native reader rejected the named empty source; metadata predicates and restored source namespace only. Every saved operand checked; no scientific observer claim.')

def operational_controls(g,parent,complete):
    root=OUT/'operational/accounting-controls';value,ref,linked=named_record(g,parent.get('accounting_controls'),root/'controls.json')
    if value is None:
        need(not complete and not parent.get('child_launch_entered'),'no child before operational controls')
        return dict(record=None,status='UNVISITED_OR_UNRETAINED',controls=[])
    need(value['schema']=='m193c-accounting-control-prefix-v1' and type(value['rows']) is list and len(value['rows'])<=3,'bounded actual operational prefix')
    ids=['joint-cpu-refusal','exact-boundary-positive','restored-live-refusal'];summaries=[]
    for i,row in enumerate(value['rows']):
        name=ids[i];directory=root/name
        need(row['id']==name and type(row['passed']) is bool and row['measurement_scope']=='INJECTED_ACCOUNTING_SEAM' and row['expected_admission'] is (i==1),'ordered and explicitly injected control')
        current={p.name:g.file(p) for p in directory.iterdir() if p.is_file()} if directory.exists() else {}
        need(set(current)<=set(g.NAMES)|{'child-terminal.json','refused-canonical.json'},'whole declared operational control file population')
        if not row['passed']:
            need(not complete and i==len(value['rows'])-1 and row.get('failure') is not None,'final explicit failed operational control')
            summaries.append(dict(id=name,passed=False,error=row['failure'],observed_files=current,scope='Retained failed control prefix; no invented passed transport'))
            break
        childref=row['child_terminal'];need(g.same(childref,current['child-terminal.json']),'actual injected terminal ref')
        child=compact_slot(g,childref,16*KIB);observed=dict(command=['INJECTED_ACCOUNTING_NO_PROCESS'],exit_code=0,error=None,job_accounting=dict(total_cpu_100ns=950000000,active_processes=0),terminal_job_accounting=True)
        need(child['schema']=='m193c-durable-child-terminal-v1' and child['measurement_scope']=='INJECTED_ACCOUNTING_SEAM' and child['observation']==observed and child['latest_job_accounting']==observed['job_accounting'] and child['job_accounting_error'] is None and child['live_job_queries']==1 and child['new_run_cpu_accounting_complete'] is True,'entire actual injected child-query witness')
        work=child['parent_and_child_work'];g.typed_work(work)
        parent_cpu=5 if i==1 else 6;total=95+parent_cpu
        need(work['cpu_seconds']==total and work['file_bytes']==work['metadata_bytes']==24*KIB and row['combined_cpu']==total and row['child_allowed_cpu']==95 and row['error']==(None if i==1 else 'local cap'),'independent injected budget arithmetic and error gate')
        expected=dict(schema='m193c-accounting-control-v1',id=name,status='COMPLETE_CONTROL_ONLY' if i==1 else 'REFUSED',measurement_scope='INJECTED_ACCOUNTING_SEAM',child_terminal=childref,error=row['error'])
        pub=row['publication'];pubpath=directory/('refused-canonical.json' if i==2 else 'result.json')
        saved,savedref=g.slot(pubpath,2048)
        initial=dict(schema='m193c-accounting-control-v1',id=name,measurement_scope='INJECTED_ACCOUNTING_SEAM',status='REFUSED',publication_phase='INITIAL_INCOMPLETE',error=None)
        recovery=dict(initial,child_terminal=childref,error=row['error'],publication_phase='BOUND_RECOVERY_REFUSAL')
        fault=dict(type='ValueError',message='terminal slot capacity',phase='ENCODING')
        expected_saved=dict(recovery,publication_phase='TERMINAL_REFUSAL',error=fault,first_positive=None) if i==0 else expected
        need(saved==expected_saved and g.same(pub['canonical'],savedref) and pub['passed'] is (i==1) and pub['canonical_refusal_verified'] is (i!=1) and pub['error']==(fault if i==0 else None),'whole powered refreshed-refusal publication and separate admission outcome')
        need(pub['phase']==('TERMINAL_REFUSAL' if i==0 else 'TERMINAL') and (i!=0 or pub['revocation_errors']==[]),'actual encoding fault with successful detailed refusal')
        first,firstref=g.slot(directory/'first-publication.json',2048)
        initial=dict(schema='m193c-accounting-control-v1',id=name,measurement_scope='INJECTED_ACCOUNTING_SEAM',status='REFUSED',publication_phase='INITIAL_INCOMPLETE',error=None)
        if i==1:need(first==expected and g.same(pub['first_positive'],firstref),'actual accepted boundary retained positive')
        elif i==0:need(first==initial and pub['first_positive'] is None,'refusal never advertised as positive')
        else:
            need(pub['first_positive'] is None and Path(pub['original_canonical_path']).resolve()==directory/'result.json','preceding refusal retained separately before same-instance restoration')
            restored=row['restoration'];value_now,nowref=g.slot(directory/'result.json',2048)
            expected_now=dict(schema='m193c-accounting-control-v1',id=name,status='COMPLETE_RESTORATION_CONTROL_ONLY',measurement_scope='INJECTED_ACCOUNTING_SEAM',restored_parent_cpu=5,child_cpu=95,combined_cpu=100,preceding_failure_child=childref)
            need(value_now==first==expected_now and restored['passed'] is True and restored['canonical_refusal_verified'] is False and g.same(restored['canonical'],nowref) and g.same(restored['first_positive'],firstref),'exact current and first-positive restored control bytes')
        for name2,r in current.items():
            if name2 in g.NAMES and name2 not in ('result.json','first-publication.json'):
                parsed,_=g.slot(g.path(r),2048)
                need(parsed==recovery and name2=='emergency-refusal.json','remaining recovery slot preserves full exact child binding')
        summaries.append(dict(id=name,passed=True,injected_child_terminal=childref,combined_cpu=total,admitted=i==1,restoration_verified=i==2,scope='Injected bookkeeping/actual owned writer seam; not an actual Windows Job'))
    if complete or parent.get('child_launch_entered'):need(linked and len(summaries)==3 and all(x['passed'] for x in summaries),'all operational controls before any child launch')
    return dict(record=ref,parent_link_retained=linked,controls=summaries)

def live_controls(g,parent,complete):
    file=OUT/'operational/live-controls/live-controls.json';value,ref,linked=named_record(g,parent.get('live_accounting_controls'),file,8192)
    if value is None:
        need(not complete and not parent.get('child_launch_entered'),'no child before live-wrapper controls')
        return dict(record=None,status='UNVISITED_OR_UNRETAINED',controls=[])
    need(value['schema']=='m193c-injected-live-accounting-controls-v1' and value['scope']=='INJECTED_QUERY_AND_ACCOUNTING_SEAMS_NOT_WINDOWS_PROCESS_BOUNDARY','actual explicit fake-query scope')
    rows=value['rows'];ids=['live-wrapper-off','live-wrapper-on','live-wrapper-placebo','live-wrapper-decreasing','live-wrapper-malformed','authorized-cumulative-ceiling']
    need([r['id'] for r in rows]==ids and all(r['passed'] is True for r in rows),'whole injected wrapper control population')
    original=[dict(total_cpu_100ns=10000000,active_processes=1),dict(total_cpu_100ns=20000000,active_processes=0)]
    digest=sha(compact(original))
    for i,row in enumerate(rows[:3]):
        need(row['intrinsic_sha256']==digest and row['queries']==2 and row['observed_queries']==(0 if i==0 else 2) and row['restored'] is True,'literal full off/on/placebo query witness and update count')
    for row,n,error in ((rows[3],2,'nonmonotone actual Job CPU'),(rows[4],1,'missing typed actual Job CPU')):
        need(row['error']=='invalid live Job accounting' and row['queries']==n and row['next_operations']==0 and row['restored'] is True and row['retained_accounting_error']==error,'invalid accounting prevents next operation and preserves wrapper restoration')
    row=rows[5]
    need(row['admitted_cpu']==1439 and row['refused_cpu']==1441 and row['error']=='complete authorized cpu_seconds bound' and row['retired_ceiling']==1320 and row['new_ceiling']==1440,'isolated cumulative ceiling controls, local parent97/99 below100')
    if complete or parent.get('child_launch_entered'):need(linked,'actual live-control parent link before launch')
    return dict(record=ref,parent_link_retained=linked,controls=rows,scope=value['scope'])

def scientific_prefix(g,h,worker,old,private,plan,complete):
    pop=g.population(worker);expanded=dict(worker,fits=[] if pop is None else pop['fits'])
    pubs=g.publication_controls(expanded);remember('worker-publication-controls',pubs)
    values=cached=state=state_summary=inputs=input_ref=science=None;norm=[];codec=[];runtime=[];topology=None
    if worker.get('saved_feature_checks'):
        need(worker['saved_feature_checks']==11,'exact saved export population')
        values,cached=g.exports(h,old);codec=g.codec_controls(worker,cached)
        remember('saved-export-codec',dict(exports=len(values),codec_controls=codec))
        state,state_summary=model_witness(g,worker,old)
        inputs,norm,input_ref=g.input_records(h,worker,old,values)
        if norm:remember('actual-normalized-components',dict(inputs=input_ref,rows=norm))
        if inputs and state and pop:
            science=g.scientific(h,worker,old,private,values,cached,inputs,state,pop,complete)
            remember('actual-science-prefix',dict(controls=science['controls'],real_pairs=len(science['real_pairs']),predictions=science['prediction_count'],fits=science['fit_count'],unvisited=science['unvisited'],trailing_saved_values=science['trailing_saved_values']))
    for key in ('runtime_before','runtime_after'):
        if worker.get(key):runtime.append(runtime_summary(g.runtime_snapshot(worker[key],plan,old,True)))
    guard=None
    if worker.get('import_guard_final'):
        guard=g.read(worker['import_guard_final']);need(type(guard['blocked_imports']) is list and all(type(x) is str for x in guard['blocked_imports']) and type(guard['import_guard_restored']) is bool,'actual guard exit witness')
        if complete:need(guard['import_guard_restored'] is True,'completed actual guard restoration')
    if worker.get('counters'):
        counts=worker['counters'];need(set(counts)==set('images extractions normalizations model_forwards registrar_calls'.split()) and all(g.integer(v) and v>=0 for v in counts.values()) and counts['images']==counts['extractions']==0 and counts['normalizations']<=9 and counts['model_forwards']<=26 and counts['registrar_calls']<=28,'whole bounded scientific counter prefix')
    if complete:
        need(worker['counters']==dict(images=0,extractions=0,normalizations=9,model_forwards=26,registrar_calls=28) and science is not None and len(science['real_pairs'])==23 and len(codec)==10 and len(pubs)==7 and all(x['passed'] for x in pubs) and len(norm)==11 and len(runtime)==2,'complete worker scientific and verification populations')
        need(worker['inference_observer_nonperturbation']=='PASS_THREE_PRIVATE_FORWARDS_AFTER_CALL_SCOPE','actual bounded inference observer scope')
        topology=g.graph(pop,worker)
    return dict(scientific=science,publication_controls=pubs,codec_controls=codec,normalization=norm,model_state_witness=state_summary,runtime=runtime,graph=topology,guard_restoration=guard,population=pop)


def finite(value):return type(value) in (int,float) and math.isfinite(value) and value>=0

def terminal(g,directory,value,ref,console=None):
    current,current_ref=g.slot(directory/'result.json',64*KIB)
    need(current==value and g.same(current_ref,ref),'exact current canonical parent/worker')
    first=first_ref=None
    if (directory/'first-publication.json').exists():first,first_ref=g.slot(directory/'first-publication.json',64*KIB)
    if value['status']==COMPLETE:need(first==value and first_ref['sha256']==ref['sha256'],'retained complete first-positive value')
    else:need(value['status']=='REFUSED','canonical refusal governs')
    slots={}
    for name in g.NAMES:
        path=directory/name
        if path.exists():
            parsed,r=g.slot(path,64*KIB);slots[name]=dict(file=r,status=parsed['status'],publication_phase=parsed.get('publication_phase'))
            need(parsed.get('schema')==value['schema'] and g.same(parsed['plan'],value['plan']) and parsed.get('implementation_version')==VERSION,'whole terminal slot association')
            if parsed.get('publication_phase') in ('INITIAL_INCOMPLETE','BOUND_RECOVERY_REFUSAL'):
                need(parsed['status']=='REFUSED' and parsed['cpu_accounting_complete'] is False,'fallback does not become positive')
    records=[] if console is None else g.lines(console)
    ads=[x for x in records if type(x.get('result')) is dict and set(x['result'])=={'path','bytes','sha256'}]
    tails=[x for x in records if x.get('schema')=='m193c-real-accounting-repair-publication-tail-v2']
    need(len(ads)<=1 and len(tails)<=1,'one actual advertisement and bounded final tail')
    ad=ads[0] if ads else None;tail=tails[0] if tails else None;issues=[]
    if ad:
        need(g.path(ad['result'])==directory/'result.json' and ad['cpu_accounting_complete'] is False and type(ad['new_run_cpu_accounting_complete']) is bool,'actual scoped stdout identity')
        g.typed_work(ad['conservative_work_through_publication'])
        if not g.same(ad['result'],ref):
            need(first_ref is not None and ad['result']['bytes']==first_ref['bytes'] and ad['result']['sha256']==first_ref['sha256'],'escaped prior positive authenticated by retained first slot')
        need(ad['status'] in (COMPLETE,'REFUSED'),'known advertisement state')
    if tail:
        need(len(compact(tail))<=4096 and set(tail)==set('schema status publication publication_error_type child_observation worker_result accounting_final transport conservative_work_through_transport_exit timing_scope'.split()),'closed bounded actual final tail')
        publication=tail['publication']
        need(set(publication)==set('passed canonical canonical_refusal_verified first_positive phase'.split()) and type(publication['passed']) is bool and type(publication['canonical_refusal_verified']) is bool,'closed compact actual publication outcome')
        if publication['canonical'] is not None:need(g.same(publication['canonical'],ref),'tail binds final actual canonical')
        if publication['first_positive'] is not None:need(first_ref is not None and g.same(publication['first_positive'],first_ref),'tail first-positive exact bytes')
        if publication['canonical_refusal_verified']:need(value['status']=='REFUSED' and publication['passed'] is False and tail['status']=='REFUSED','actual revocation overrides any escaped positive')
        if publication['passed']:need(value['status']==COMPLETE and tail['status']==COMPLETE and ad is not None and g.same(ad['result'],ref),'actual complete publication includes advertisement')
        g.typed_work(tail['conservative_work_through_transport_exit']);transport_cost(g,tail['transport'])
        need(tail['timing_scope']=='measured through last transport exit; excludes this final bounded stderr write','explicit excluded final bounded stderr timing')
        for key in ('child_observation','worker_result','accounting_final'):
            r=tail[key]
            if r is not None:bound_ref(g,r)
            if value.get(key) is not None:need(r is not None and g.same(r,value[key]),'tail matches retained detail '+key)
        if ad:need(all(D(str(tail['conservative_work_through_transport_exit'][k]))>=D(str(ad['conservative_work_through_publication'][k])) for k in ALLOW),'tail no earlier than advertisement')
    if value['status']==COMPLETE and tail is None:issues.append('CANONICAL_COMPLETE_WITHOUT_FINAL_TAIL')
    if value['status']==COMPLETE and (ad is None or tail is not None and not tail['publication']['passed']):issues.append('CANONICAL_COMPLETE_WITHOUT_COMPLETE_PUBLICATION')
    return dict(canonical=ref,first_positive=first_ref,slots=slots,advertisement=ad,tail=tail,operational_exceptions=issues)

def transport_cost(g,value):
    need(set(value)==set('entries cpu_seconds wall_seconds allowance scope'.split()) and g.integer(value['entries']) and value['entries']>=0 and finite(value['cpu_seconds']) and finite(value['wall_seconds']),'typed actual accumulated transport intervals')
    need(value['allowance']==dict(cpu_seconds=2,wall_seconds=3) and value['scope']=='actual transport intervals; no scientific admission after cap failure','transport permission scope')
    return value['cpu_seconds']<=2 and value['wall_seconds']<=3

def final_account(g,result,root,terminal_record):
    declared=result.get('accounting_final')
    if declared is None and terminal_record['tail']:declared=terminal_record['tail']['accounting_final']
    value,ref,linked=named_record(g,declared,root/'operational/accounting-final.json',8192)
    if value is None:return dict(record=None,status='UNVISITED_OR_UNRETAINED')
    need(value['schema']=='m193c-real-accounting-repair-final-accounting-v2' and value['status'] in ('REFUSED',COMPLETE) and value['prior_cpu_accounting_complete'] is False and type(value['new_run_cpu_accounting_complete']) is bool,'actual earlier accounting sample scope')
    need(value['measurement_scope']=='CURRENT_PROCESS_PLUS_LATEST_OBSERVED_OWNED_JOB_CPU; historical CPU gap remains','no repaired historical CPU')
    g.typed_work(value['conservative_global_work']);t=value['transport'];transport_cost(g,t['transport_cost'])
    slots={name:['terminal',64*KIB] for name in g.NAMES}
    slots['operational/accounting-final.json']=['operational',8192]
    if root==OUT:
        slots['operational/child-terminal.json']=['operational',16*KIB]
        live=root/'operational/live-controls/live-controls.json'
        if live.exists():slots['operational/live-controls/live-controls.json']=['operational',8192]
    else:slots.update({'metadata/manifest/population.json':['metadata',48*KIB],'metadata/state/import-guard-final.json':['metadata',2048]})
    need(t['reserved_slots']==slots and g.integer(t['live_job_queries']) and t['live_job_queries']>=0 and (t['job_accounting_error'] is None or type(t['job_accounting_error']) is str),'complete independently chosen registered transport slots')
    if root!=OUT:need(t['live_job_queries']==0 and t['latest_job_accounting'] is None and t['job_accounting_error'] is None,'worker does not own a child-query loop')
    for key in ('child_observation','worker_result'):
        if value[key] is not None:bound_ref(g,value[key])
        if result.get(key) is not None:need(value[key] is not None and g.same(value[key],result[key]),'final sample retained association '+key)
    tail=terminal_record['tail']
    if tail:
        need(all(D(str(tail['conservative_work_through_transport_exit'][k]))>=D(str(value['conservative_global_work'][k])) for k in ALLOW),'later actual tail may follow earlier status, never refunds work')
        need(tail['transport']['entries']>=t['transport_cost']['entries'] and all(tail['transport'][k]>=t['transport_cost'][k] for k in ('cpu_seconds','wall_seconds')),'transport tail includes earlier active sample')
    return dict(record=ref,parent_or_tail_link_retained=linked,value=value,scope='Accounting-final is an earlier sample; later canonical refusal/tail governs final status.')

def runtime_job(g,parent,request_ref,worker_argv,terminal_record,account):
    declared=parent.get('child_observation')
    if declared is None and terminal_record['tail']:declared=terminal_record['tail']['child_observation']
    value,ref,linked=named_record(g,declared,OUT/'operational/child-terminal.json',16*KIB)
    if value is None:return dict(record=None,terminal_cpu_accounting=False,observed=False)
    need(value['schema']=='m193c-durable-child-terminal-v1','actual durable child schema')
    if value['measurement_scope']=='UNOBSERVED_CHILD_TERMINAL':
        need(value==dict(schema='m193c-durable-child-terminal-v1',measurement_scope='UNOBSERVED_CHILD_TERMINAL',observation=None,new_run_cpu_accounting_complete=False),'literal initial Job gap')
        return dict(record=ref,parent_or_tail_link_retained=linked,terminal_cpu_accounting=False,observed=False,scope='Initial durable placeholder; no actual child CPU.')
    need(value['measurement_scope']=='ACTUAL_OWNED_JOB_RETURN' and type(value['observation']) is dict,'actual Job scope cannot be replaced by injected control')
    o=value['observation'];need(o['command']==worker_argv and request_ref is not None,'actual attempted child argv and request')
    if o.get('log') is not None:
        log=bound_ref(g,o['log']);need(g.path(log)==OUT/'worker.log' and log['bytes']==o['log_bytes'],'actual complete bounded child log')
    else:need(o['log_bytes']==0 and not (OUT/'worker.log').exists(),'no omitted actual child log')
    lim=o['limits'];need(set(lim)==set('cpu_seconds wall_seconds log_bytes committed_bytes'.split()) and finite(lim['cpu_seconds']) and 2<lim['cpu_seconds']<=96 and finite(lim['wall_seconds']) and 3<lim['wall_seconds']<=150 and lim['log_bytes']==MIB and lim['committed_bytes']==8<<30,'exact dynamic worker cap envelope')
    need(finite(o['wall_seconds']) and type(o['terminal_job_accounting']) is bool and type(o['cleanup_errors']) is list and all(type(x) is str for x in o['cleanup_errors']),'actual final observation typed')
    def cpu_record(a):
        need(type(a) is dict and all(g.integer(a[k]) and a[k]>=0 for k in ('total_cpu_100ns','total_user_100ns','total_kernel_100ns','active_processes')) and a['total_cpu_100ns']==a['total_user_100ns']+a['total_kernel_100ns'],'independent Job user+kernel arithmetic')
        return a['total_cpu_100ns']/1e7
    cpu=None if o['job_accounting'] is None else cpu_record(o['job_accounting'])
    need(value['latest_job_accounting']==o['job_accounting'] and g.integer(value['live_job_queries']) and value['live_job_queries']>=1,'capture retained latest delegated query including final observation')
    observed_complete=o['terminal_job_accounting'] is True and cpu is not None and o['job_accounting']['active_processes']==0 and value['job_accounting_error'] is None
    need(value['new_run_cpu_accounting_complete'] is observed_complete,'new CPU completeness derives actual terminal Job')
    g.typed_work(value['parent_and_child_work'])
    if cpu is not None:need(D(str(value['parent_and_child_work']['cpu_seconds']))>=D(str(parent['prior_work']['cpu_seconds']))+D(str(cpu)),'durable parent sample includes whole observed Job CPU')
    configured=o['configured_job_limits']
    if configured is not None:need(configured['committed_bytes']==8<<30 and g.integer(configured['flags']) and configured['flags']&0x2200==0x2200,'actual queried Job memory and kill-on-close bits')
    drain=o['post_exit_drain']
    if drain is not None:
        need(type(drain['observations']) is list and len(drain['observations'])<=16 and g.integer(drain['observation_count']) and drain['observation_count']>=len(drain['observations']),'bounded actual post-exit observation prefix')
        sequence=[row['accounting'] for row in drain['observations']]
        if drain['initial_accounting'] is not None:cpu_record(drain['initial_accounting'])
        if drain['last_accounting'] is not None:cpu_record(drain['last_accounting'])
        if sequence:
            need(sequence[0]==drain['initial_accounting'],'first post-exit observation retained')
            times=[row['wall_seconds'] for row in drain['observations']];need(all(finite(x) for x in times) and times==sorted(times),'post-exit observation time order')
            numbers=[cpu_record(a) for a in sequence];need(numbers==sorted(numbers),'retained post-exit CPU monotone')
            if len(sequence)==drain['observation_count']:need(sequence[-1]==drain['last_accounting'],'full short drain final observation')
        if drain['completed']:need(drain['last_accounting']['active_processes']==0,'actual drain completion')
    termination=o['termination'];need(type(termination['attempted']) is bool and type(termination['succeeded']) is bool,'actual termination witness')
    if termination['before_accounting'] is not None:cpu_record(termination['before_accounting'])
    if account.get('value'):
        sample=account['value'];t=sample['transport']
        need(t['latest_job_accounting']==value['latest_job_accounting'] and t['live_job_queries']==value['live_job_queries'] and t['job_accounting_error']==value['job_accounting_error'] and sample['new_run_cpu_accounting_complete'] is observed_complete,'same final Job witness in later accounting sample')
        need(all(D(str(sample['conservative_global_work'][k]))>=D(str(value['parent_and_child_work'][k])) for k in ALLOW),'finalizer retains prior durable work')
    clean=observed_complete and o['exit_code']==0 and o['error'] is None and o['cleanup_errors']==[] and o['direct_exit_observed'] is True and o['pipe_eof_observed'] is True and drain is not None and drain['completed'] is True and termination['attempted'] is False
    if clean:need(configured is not None and cpu<=lim['cpu_seconds'] and o['wall_seconds']<=lim['wall_seconds'] and o['job_memory']['peak_job_memory_used_bytes']<=8<<30,'clean actual Job respects installed bounds')
    return dict(record=ref,parent_or_tail_link_retained=linked,observed=True,terminal_cpu_accounting=observed_complete,clean=clean,cpu_seconds=cpu,wall_seconds=o['wall_seconds'],limits=lim,live_query_count=value['live_job_queries'],latest_job_accounting=value['latest_job_accounting'],job_accounting_error=value['job_accounting_error'],exit_code=o['exit_code'],error=o['error'],cleanup_errors=o['cleanup_errors'],post_exit_observation_count=None if drain is None else drain['observation_count'],termination=termination,scope='Whole actual owned Job user+kernel CPU, retained latest query/count and bounded drain observations; full live-query history is not retained.')

def reservation_ledger(g,result,root,inv):
    saved=result.get('charged_path_extents')
    if saved is None:return None
    families=dict(g.FAMILY,operational=128*KIB);need(sum(families.values())==8217472,'new exact128KiB lane inside old8MiB')
    need(type(saved) is dict and len(saved)<=1024,'bounded monotone saved reservation ledger')
    paths={};totals=dict.fromkeys(families,0);subs=dict.fromkeys(g.META,0)
    merged=root==OUT and result.get('worker_result') is not None and (result.get('work') or {}).get('extent_accounting_complete') is True
    ambiguous=root==OUT and result.get('worker_result') is not None and not merged
    ambiguous_stage=0
    for name,size in saved.items():
        need(type(name) is str and g.integer(size) and 0<size<=MIB,'typed bounded reservation')
        p=(root/name).resolve();need(p.is_relative_to(root) and p.relative_to(root).as_posix()==name,'canonical relative owned reservation')
        parts=Path(name).parts;parts=parts[1:] if parts[0]=='worker' else parts
        family='operational' if parts[0]=='operational' else g.family(name,root,merged)
        need(family in families,'complete family population');paths[p]=size;totals[family]+=size
        if ambiguous and name=='worker/publication-stage.json':ambiguous_stage=size
        if family=='metadata':
            sub=parts[1] if parts[0]=='metadata' and len(parts)>2 else 'controller';need(sub in subs,'exact metadata group');subs[sub]+=size
    family_ranges={k:[v,v] for k,v in totals.items()}
    if ambiguous_stage:
        family_ranges['terminal']=[totals['terminal']-ambiguous_stage,totals['terminal']]
        family_ranges['publication']=[totals['publication'],totals['publication']+ambiguous_stage]
    need(all(family_ranges[k][0]<=families[k] for k in families) and all(subs[k]<=g.META[k] for k in subs),'complete known family subcaps; possible partial-merge family interval explicit')
    for name in g.NAMES:need(paths.get(root/name)==64*KIB,'four nonrefundable current-process terminal reservations')
    current={g.path(r):r for r in inv if g.path(r).is_relative_to(root)}
    uncovered=[dict(path=p.relative_to(OUT).as_posix(),actual=r['bytes'],reserved=paths.get(p,0)) for p,r in current.items() if r['bytes']>paths.get(p,0)]
    missing=[]
    for p,size in paths.items():
        if p in current:continue
        name=p.relative_to(root).as_posix();parts=p.relative_to(root).parts
        allowed=(p.name in ('publication-stage.json','emergency-refusal.json')) or (root==OUT and parts[0]=='worker' and p.name in g.NAMES) or name in ('metadata/manifest/population.json','metadata/state/import-guard-final.json','operational/accounting-final.json','worker/operational/accounting-final.json','worker.log')
        need(allowed,'only explicitly precharged or atomically consumed paths may be absent')
        missing.append([name,size])
    total=sum(paths.values());work=result.get('work');uncertain=work is None or work.get('extent_accounting_complete') is not True
    if work:
        need(work['new_charged_extent_bytes']==total and work['local_caps']==ATTEMPT and work['family_limits']==families and work['metadata_subfamily_limits']==g.META and work['prior_cpu_accounting_complete'] is False and type(work['extent_accounting_complete']) is bool,'whole new work envelope')
        g.typed_work(work['conservative_global_work']);charge=8*MIB if uncertain else total
        for key in ('file_bytes','metadata_bytes'):need(work['conservative_global_work'][key]==result['prior_work'][key]+charge,'actual logical charge includes full fallback when extent uncertain')
    return dict(total=total,paths=paths,families=None if ambiguous_stage else totals,family_ranges=family_ranges,partial_merge_family_ambiguity_bytes=ambiguous_stage,metadata_subfamilies=subs,physical_bytes=sum(r['bytes'] for r in current.values()),uncovered=uncovered,absent_but_charged=missing,extent_accounting_complete=not uncertain)

def resource_account(g,parent,worker,outer,inv,parent_terminal,worker_terminal,parent_account,worker_account,job,complete):
    prior=parent['prior_work'];pl=reservation_ledger(g,parent,OUT,inv);wl=reservation_ledger(g,worker,OUT/'worker',inv) if worker else None
    union={g.path(r):r['bytes'] for r in inv};missing=[]
    for ledger in (pl,wl):
        if ledger:
            for p,size in ledger['paths'].items():union[p]=max(union.get(p,0),size)
    if pl and wl:missing=[[p.relative_to(OUT).as_posix(),size,pl['paths'].get(p,0)] for p,size in wl['paths'].items() if size>pl['paths'].get(p,0)]
    uncertain=pl is None or not pl['extent_accounting_complete'] or worker is not None and (wl is None or not wl['extent_accounting_complete'])
    extent=max(sum(union.values()),8*MIB if uncertain else 0);need(extent<=8*MIB,'whole actual/charged union within original8MiB')
    samples=[]
    for terminal_value,account_value in ((parent_terminal,parent_account),):
        if account_value.get('value'):samples.append(account_value['value']['conservative_global_work'])
        if terminal_value['advertisement']:samples.append(terminal_value['advertisement']['conservative_work_through_publication'])
        if terminal_value['tail']:samples.append(terminal_value['tail']['conservative_work_through_transport_exit'])
    if parent.get('work'):samples.append(parent['work']['conservative_global_work'])
    for value in samples:g.typed_work(value);need(all(D(str(value[k]))>=D(str(prior[k])) for k in ALLOW),'actual parent sample no carry refund')
    subject=dict(cpu_seconds=prior['cpu_seconds']+102,wall_seconds=float(D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))),file_bytes=prior['file_bytes']+extent,metadata_bytes=prior['metadata_bytes']+extent)
    scope='Incomplete operational attempt: full100CPU plus2CPU publication policy charge, full actual outer wall, conservative physical/reservation union or full8MiB if ledger unavailable; CPU is not claimed measured.'
    if complete:
        need(pl and wl and not missing and not pl['uncovered'] and not wl['uncovered'] and not uncertain and job['terminal_cpu_accounting'] and job['clean'],'complete actual ledger and terminal Job evidence')
        latest=parent_terminal['tail']['conservative_work_through_transport_exit']
        need(latest['file_bytes']==prior['file_bytes']+pl['total'] and latest['metadata_bytes']==prior['metadata_bytes']+pl['total'] and D(str(latest['cpu_seconds']))>=D(str(prior['cpu_seconds']))+D(str(job['cpu_seconds'])),'latest parent tail includes full Job and all reserved extents')
        # The final actual sample may cross an admission boundary; report it, do not discard science.
        subject=dict(latest);subject['cpu_seconds']=float(D(str(latest['cpu_seconds']))+D(2));subject['wall_seconds']=float(max(D(str(latest['wall_seconds'])),D(str(prior['wall_seconds']))+D(str(outer['elapsed_wall_seconds']))))
        scope='Actual terminal Job CPU plus latest parent sample through transport exit and explicit2CPU final-stderr policy allowance; whole actual outer wall without duplicate wall tail. The final bounded stderr write is outside the last sample.'
    else:
        for sample in samples:
            subject['cpu_seconds']=max(subject['cpu_seconds'],sample['cpu_seconds']+2);subject['wall_seconds']=max(subject['wall_seconds'],sample['wall_seconds'])
            for key in ('file_bytes','metadata_bytes'):subject[key]=max(subject[key],sample[key])
    tail_sample=None if parent_terminal['tail'] is None else parent_terminal['tail']['conservative_work_through_transport_exit']
    measured=dict(final_transport_within_attempt=None if tail_sample is None else all(D(str(tail_sample[k]))-D(str(prior[k]))<=ATTEMPT[k] for k in ALLOW),whole_outer_wall_within_attempt=outer['elapsed_wall_seconds']<=ATTEMPT['wall_seconds'])
    bounds=dict(subject_cpu_with_tail=subject['cpu_seconds']-prior['cpu_seconds']<=102.000000001,subject_outer_wall=subject['wall_seconds']-prior['wall_seconds']<=180,cumulative=all(subject[k]<=LIMITS[k] for k in ALLOW))
    def reduced(item):return None if item is None else {k:v for k,v in item.items() if k!='paths'}
    return dict(subject_final_work=subject,job=job,inventory_count=len(inv),inventory_total_bytes=sum(r['bytes'] for r in inv),inventory_canonical_sha256=sha(canonical(inv)),parent_ledger=reduced(pl),worker_ledger=reduced(wl),missing_parent_assimilation=missing,conservative_union_extent_bytes=extent,extent_accounting_complete=not uncertain,resource_bounds=bounds,measured_resource_checks=measured,observed_resource_overrun=any(value is False for value in measured.values()),scope=scope)


def envelope(g,value,worker,plan,plan_ref,prior,argv):
    need(value['schema']==('m193c-real-accounting-repair-worker-v2' if worker else 'm193c-real-accounting-repair-run-v2') and value['implementation_version']==VERSION and value['scientific_implementation_version']==SCIENCE_VERSION,'actual new accounting and unchanged scientific versions')
    need(value['status'] in (COMPLETE,'REFUSED') and g.same(value['plan'],plan_ref) and value['prior_work']==prior and value['qualification']==g.QUAL and g.same(value['resource_authorization'],plan['resource_authorization']),'actual scoped terminal authority and gauge')
    need(value['cpu_accounting_complete'] is False and value['original_commission_complete'] is False and value['old_run_status']==value['previous_real_run_status']=='REFUSED','all historical failure/CPU gaps remain')
    if 'command' in value:need(value['command']==argv,'exact actual current-process command')
    if 'private_baseline' in value:need(value['private_baseline']==plan['private_baseline'] and value['failed_real_baseline']==plan['failed_real_baseline'] and value['callback_baseline']==plan['callback_baseline'],'whole detailed baseline associations')
    if value['status']==COMPLETE:need(value['sources_unchanged'] is True and value['error'] is None and value['new_run_cpu_accounting_complete'] is True,'canonical complete source/error/accounting witnesses')

def verify_source_derivation(g,plan,probe):
    need(set(V2_PINS)=={'real-accounting-repair-v2-run.py','real-accounting-repair-v2-support.py','real-accounting-repair-v2-preregister.md'},'prospective controller pins must be held before release')
    for name,pin in V2_PINS.items():bound_ref(g,source_ref(g,plan,HERE/name),pin)
    return dict(sources=[source_ref(g,plan,HERE/name) for name in V2_PINS],optimized_ast_sha256=probe['candidate_ast'],scope='Exact reviewed v2 sources; unchanged scientific and scoped transport functions, separately authorized namespace and cumulative limit.')

def accounting_implementation(g,value,probe,prior_prefix):
    row=value.get('accounting_implementation')
    if row is None:
        need(value['status']!=COMPLETE,'completed actual implementation witness');return None
    need(set(row)==set('optimized_ast_sha256 authorized_ast_sha256 old_cumulative_cpu_limit new_cumulative_cpu_limit old_ceiling_disposition previous_charged_work optimization_effect'.split()),'complete actual accounting implementation witness')
    need(row['optimized_ast_sha256']==probe['candidate_ast'] and row['old_cumulative_cpu_limit']==1320 and row['new_cumulative_cpu_limit']==1440 and row['old_ceiling_disposition']=='RETIRED_NOT_RESET' and row['previous_charged_work']==prior_prefix['actual_final_work'],'exact prior executed optimization and new resource grant')
    need(type(row['authorized_ast_sha256']) is str and len(row['authorized_ast_sha256'])==64 and all(x in '0123456789abcdef' for x in row['authorized_ast_sha256']) and row['optimization_effect']=='COUNTER_REDUCTION_VERIFIED; failed96s attribution unmeasured','reported authorized AST witness and measured scope')
    return row

def audit_family(g,own,ledger_ref,doc):
    need(doc['schema']=='m193c-real-accounting-repair-v2-audit-family-v1' and doc['limit_bytes']==384*KIB and doc['reservations']==RESERVES and doc['reserved_total_bytes']==sum(RESERVES.values())<=384*KIB and own['bytes']<=RESERVES['source'] and ledger_ref['bytes']<=RESERVES['ledger'],'entire finite new audit family')
    need(doc['final_section_caps_bytes']=={name:cap for name,(cap,_) in FINAL_SECTIONS.items()} and doc['progress_extent_ledger_bytes']==dict(verified_phase_rows=27*KIB,error_json_maximum=4096,outer_structure_reserve=1024,total=32*KIB),'exact retained final and progress section capacity ledger')
    need(doc['audit_caps_including_publication']==AUDIT_CAPS and doc['audit_publication_allowance']==TAIL and doc['within_existing_preparation_bytes']==MIB,'prospective whole own audit budget and no extra reservation')
    for row in doc['reused_previously_charged_helpers']:bound_ref(g,row)
    need({g.path(r) for r in doc['reused_previously_charged_helpers']}=={GENERAL,g.V1,g.HELPER,PREVIOUS},'exact four immutable reused independent helper sources')
    return dict(ledger=ledger_ref,limit_bytes=384*KIB,reservations=RESERVES,audit_caps_including_publication=AUDIT_CAPS)

def output_paths():
    return dict(plan=HERE/'real-accounting-repair-plan-2.json',result=OUT/'result.json',outer=WORK/'real-accounting-repair-2-outer.json',console=WORK/'real-accounting-repair-2-console.txt',exit=WORK/'real-accounting-repair-2-exit.txt')

def runtime_summary(value):
    # Fresh output copy only. Every original runtime entry was already checked.
    result=dict(value)
    for key in ('added_names','rebound_names'):
        rows=result.pop(key);result[key+'_count']=len(rows);result[key+'_canonical_sha256']=sha(canonical(rows))
    return result

def scientific_summary(value):
    if value is None:return None
    result=json.loads(canonical(value));columns=None
    def fitted(v):
        if v is None:return
        v.pop('scope',None);v.pop('refusal_scope',None)
        intrinsic=v.pop('intrinsic')
        v['intrinsic_summary']={key:intrinsic[key] for key in ('status','transform','guard','error')}
        v['intrinsic_summary'].update(canonical_sha256=sha(canonical(intrinsic)),full_intrinsic_in_record=True)
        if v.get('calibration_final_radius'):v['calibration_final_radius'].pop('scope',None)
    for item in result['private_fits']:fitted(item)
    for row in result['real_pairs']:
        fitted(row['fit']);sites=row['coordinate_support']
        keys=list(sites['reference_q8'])
        if columns is None:columns=keys
        need(columns==keys and all(list(v)==keys for v in sites.values()),'lossless fixed site columns')
        row['coordinate_support']={side:[v[k] for k in keys] for side,v in sites.items()}
        row.pop('coordinate_support_scope',None);row.pop('physical_truth',None)
    for row in result['trailing_saved_values']:fitted(row.get('fit'))
    result['coordinate_support_columns']=columns
    result['summary_scope']='All site columns losslessly retained in fixed declared order; radius-one connected components may chain. Fit record references retain full intrinsic code/message/map/metrics; compact copies keep map/guard/error and canonical hash, with duplicated metric fields represented by verified heldout/calibration summaries. Calibration radius is descriptive, not actual refinement subset; no real physical truth. Repeated explanatory strings omitted only from this fresh report copy.'
    return result

def final_capacity(value):
    seen=set();used={};remaining=dict(value)
    for name,(cap,keys) in FINAL_SECTIONS.items():
        if name=='other':continue
        fields=keys.split();need(not seen.intersection(fields),'nonoverlapping final report sections');seen.update(fields)
        part={key:remaining.pop(key) for key in fields};used[name]=len(compact(part));need(used[name]<=cap,'bounded final '+name+' section')
    used['other']=len(compact(remaining));need(used['other']<=FINAL_SECTIONS['other'][0],'bounded other final fields')
    need(sum(cap for cap,_ in FINAL_SECTIONS.values())==128*KIB and sum(PHASE_CAPS.values())==27*KIB,'literal complete128KiB final/27KiB phase ledger')
    need(sum(used.values())<=128*KIB,'complete final sections conservatively cover outer serialization')
    return used

def main():
    global G,PROGRESS_OWNED
    parser=argparse.ArgumentParser()
    for key in ('source','ledger','plan','result','outer','console','exit'):parser.add_argument('--'+key+'-sha256',required=True)
    parser.add_argument('--worker-result-sha256');args=parser.parse_args()
    need(Path.cwd().resolve()==ROOT and sys.dont_write_bytecode and Path(sys.executable).resolve()==PYTHON,'exact root and pinned no-bytecode Python')
    need(not PROGRESS.exists() and not PROGRESS.with_suffix('.tmp').exists(),'fresh retained progress and atomic stage')
    own_data=source_bytes(SELF);need(sha(own_data)==args.source_sha256,'released actual auditor source')
    ledger_data=source_bytes(LEDGER);need(sha(ledger_data)==args.ledger_sha256,'released actual ledger source')
    G=g=load_general();PROGRESS_OWNED=True
    own=g.file(SELF);ledger_ref=g.file(LEDGER);family=audit_family(g,own,ledger_ref,g.strict(ledger_data))
    remember('initialization',dict(audit_source=own,audit_family=family))
    paths=output_paths();external={}
    for key,path in paths.items():
        ref=g.file(path);need(ref['sha256']==getattr(args,key+'_sha256'),'root released actual '+key);external[key]=ref
    plan=g.read(external['plan']);parent=g.read(external['result']);outer=g.read(external['outer']);exit_raw=g.raw(external['exit']).strip()
    need(exit_raw in (b'0',b'1'),'retained actual exit0/1');exit_code=int(exit_raw)
    namespaces(plan['source_bindings'],plan['evidence_bindings'])
    for name,binding in plan['source_bindings'].items():bound_ref(g,dict(path=name,**binding))
    for ref in (own,ledger_ref):need(plan['source_bindings'].get(g.path(ref).relative_to(ROOT).as_posix())=={k:ref[k] for k in ('bytes','sha256')},'auditor and ledger frozen in exact actual new plan')
    need(g.path(plan['python_executable'])==PYTHON,'same pinned Python executable');bound_ref(g,plan['python_executable'])
    h=g.helper();checks=g.commissioning(h);old,private,prefix,prior,grant,probe=authority(g,plan);sources=verify_source_derivation(g,plan,probe)
    base=[str(PYTHON),'-B','-X','faulthandler','-X'];runner=str(HERE/'real-accounting-repair-v2-run.py');planpath=str(paths['plan'])
    parent_template=base+['pycache_prefix='+str(OUT/'parent-cache'),runner,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT)]
    worker_template=base+['pycache_prefix='+str(OUT/'worker-cache'),runner,'--plan',planpath,'--sha256','ACTUAL_PLAN_SHA256','--output',str(OUT/'worker'),'--worker','--request',str(OUT/'request.json'),'--request-sha256','ACTUAL_REQUEST_SHA256']
    need(plan['commands']==dict(parent=parent_template,worker=worker_template),'literal new fresh parent/worker argv templates')
    parent_argv=g.replace(parent_template,external['plan']['sha256'])
    need(outer['command']==parent_argv and outer['plan_sha256']==external['plan']['sha256'] and g.integer(outer['exit_code']) and outer['exit_code']==exit_code and outer['admissible_parent_exit'] is (exit_code in (0,1)) and finite(outer['elapsed_wall_seconds']),'actual external command, finite entire wall and exit')
    envelope(g,parent,False,plan,external['plan'],prior,parent_argv)
    parent_implementation=accounting_implementation(g,parent,probe,prefix)
    parent_source_evidence=source_evidence_receipt(g,parent,plan,OUT);worker_source_evidence=None
    parent_terminal=terminal(g,OUT,parent,external['result'],external['console'])
    op=operational_controls(g,parent,False);live=live_controls(g,parent,False)
    remember('authority-operational-controls',dict(prior_work=prior,resource_authorization=plan['resource_authorization'],injected_publication_controls=op,live_wrapper_controls=live,source_evidence_verified=parent_source_evidence['visited'],scope='Actual writer and injected counters/queries; no Windows-process control claim.'))
    parent_account=final_account(g,parent,OUT,parent_terminal)
    request=request_ref=None;worker=worker_ref=None;worker_terminal=None;worker_account=None;worker_argv=None;science=None
    if parent.get('request') is not None:
        request_ref=bound_ref(g,parent['request']);need(g.path(request_ref)==OUT/'request.json','exact retained parent request')
    worker_path=OUT/'worker/result.json'
    if worker_path.exists():
        worker_ref=g.file(worker_path)
        if args.worker_result_sha256 is not None:need(worker_ref['sha256']==args.worker_result_sha256,'separate root-released actual worker canonical')
        else:need(parent.get('worker_result') is not None and g.same(parent['worker_result'],worker_ref),'worker must be parent-bound or explicitly released')
        worker=g.read(worker_ref)
        if parent.get('worker_result') is not None:need(g.same(parent['worker_result'],worker_ref),'unchanged actual worker canonical link')
        if request_ref is None:request_ref=bound_ref(g,worker['request'])
        need(g.path(request_ref)==OUT/'request.json' and g.same(worker['request'],request_ref),'actual explicit worker request with parent null preserved')
    else:need(args.worker_result_sha256 is None and parent.get('worker_result') is None,'no invented released worker')
    if request_ref:
        request=g.read(request_ref);need(set(request)==set('schema plan prior_work'.split()) and request['schema']=='m193c-real-accounting-repair-request-v2' and g.same(request['plan'],external['plan']),'closed actual worker request')
        g.typed_work(request['prior_work']);need(all(D(str(request['prior_work'][k]))>=D(str(prior[k])) for k in ALLOW),'actual request carry cannot refund parent preparation')
        worker_argv=g.replace(worker_template,external['plan']['sha256'],request_ref['sha256'])
    if worker:
        need(parent_source_evidence['visited'],'actual worker launch follows verified parent source/evidence controls')
        envelope(g,worker,True,plan,external['plan'],request['prior_work'],worker_argv)
        worker_implementation=accounting_implementation(g,worker,probe,prefix)
        worker_source_evidence=source_evidence_receipt(g,worker,plan,OUT/'worker')
        if parent_implementation and worker_implementation:need(parent_implementation==worker_implementation,'whole actual parent/worker accounting implementation witnesses')
        worker_log=g.file(OUT/'worker.log') if (OUT/'worker.log').exists() else None
        worker_terminal=terminal(g,OUT/'worker',worker,worker_ref,worker_log)
        worker_account=final_account(g,worker,OUT/'worker',worker_terminal)
        if worker.get('saved_feature_checks') or worker.get('real_population') or worker.get('runtime_before') or any(worker.get('counters',{}).values()):need(worker_source_evidence['visited'],'any saved worker population requires complete source/evidence receipt')
        science=scientific_prefix(g,h,worker,old,private,plan,worker['status']==COMPLETE)
        remember('worker-scientific-outcome',dict(worker_status=worker['status'],canonical=worker_ref,scientific=None if science['scientific'] is None else dict(real_pairs=len(science['scientific']['real_pairs']),predictions=science['scientific']['prediction_count'],fits=science['scientific']['fit_count']),runtime= science['runtime']))
    job=runtime_job(g,parent,request_ref,worker_argv,parent_terminal,parent_account)
    runtime_final=None
    if parent.get('runtime_final'):runtime_final=runtime_summary(g.runtime_snapshot(parent['runtime_final'],plan,old,False))
    remember('runtime-and-current-Job',dict(parent_runtime=runtime_final,worker_runtime=None if science is None else science['runtime'],job=job))
    exceptions=list(parent_terminal['operational_exceptions'])
    if parent['status']==COMPLETE and exit_code!=0:exceptions.append('CANONICAL_COMPLETE_WITH_NONZERO_OUTER_EXIT')
    if parent['status']=='REFUSED' and exit_code==0:exceptions.append('CANONICAL_REFUSED_WITH_ZERO_OUTER_EXIT')
    terminal_ok=parent_terminal['tail'] is not None and parent_terminal['tail']['publication']['passed'] is True and transport_cost(g,parent_terminal['tail']['transport'])
    worker_terminal_ok=worker_terminal is not None and worker_terminal['tail'] is not None and worker_terminal['tail']['publication']['passed'] is True and transport_cost(g,worker_terminal['tail']['transport'])
    if parent['status']==COMPLETE and not terminal_ok:exceptions.append('PARENT_FINAL_TRANSPORT_UNVERIFIED_OR_OVERRUN')
    if worker and worker['status']==COMPLETE and not worker_terminal_ok:exceptions.append('WORKER_FINAL_TRANSPORT_UNVERIFIED_OR_OVERRUN')
    canonical_complete=parent['status']==COMPLETE and worker is not None and worker['status']==COMPLETE
    if canonical_complete:
        need(parent['counters']==worker['counters'] and parent['saved_feature_checks']==worker['saved_feature_checks']==11 and parent['development_outcome']==worker['development_outcome'] and parent['inference_observer_nonperturbation']==worker['inference_observer_nonperturbation'],'parent exactly advertises current worker diagnostic counters and outcome')
    complete=canonical_complete and exit_code==0 and terminal_ok and worker_terminal_ok and job.get('clean') is True and parent_account.get('value') is not None and worker_account.get('value') is not None and runtime_final is not None and not exceptions
    if complete:
        need(parent_source_evidence['visited'] and parent_source_evidence['process_link_retained'] and worker_source_evidence['visited'] and worker_source_evidence['process_link_retained'],'both actual process source/evidence namespace receipts')
        need(len(op['controls'])==3 and all(x['passed'] for x in op['controls']) and len(live['controls'])==6 and op['parent_link_retained'] and live['parent_link_retained'],'complete actual operational prerequisites')
    inv=g.inventory();account=resource_account(g,parent,worker,outer,inv,parent_terminal,worker_terminal,parent_account,worker_account,job,complete)
    resource_ok=all(account['resource_bounds'].values()) and not account['observed_resource_overrun']
    if account['observed_resource_overrun']:exceptions.append('OBSERVED_RESOURCE_ENVELOPE_EXCEEDED')
    if not all(account['resource_bounds'].values()):exceptions.append('CONSERVATIVE_ACCOUNTING_ENVELOPE_EXCEEDED')
    complete=complete and resource_ok
    remember('resource-accounting',dict(subject_final_work=account['subject_final_work'],inventory_count=account['inventory_count'],inventory_total_bytes=account['inventory_total_bytes'],resource_bounds=account['resource_bounds'],operational_exceptions=exceptions))
    need(not (OUT/'parent-cache').exists() and not (OUT/'worker-cache').exists(),'no new bytecode outputs')
    for path,identity in g.IDENTITIES.items():need(g.ident(Path(path).stat(follow_symlinks=False))==identity,'all consumed evidence and source identities unchanged')
    check();audit_cpu=time.process_time();audit_wall=time.perf_counter()-START
    carry=dict(account['subject_final_work']);carry['cpu_seconds']=float(D(str(carry['cpu_seconds']))+D(str(audit_cpu))+D(str(TAIL['cpu_seconds'])));carry['wall_seconds']=float(D(str(carry['wall_seconds']))+D(str(audit_wall))+D(str(TAIL['wall_seconds'])))
    carry_inside=all(carry[k]<=LIMITS[k] for k in ALLOW)
    if not carry_inside:exceptions.append('ACTUAL_CARRY_EXCEEDS_EXPLICIT_GRANT_NO_FURTHER_ADMISSION')
    full_science=worker_source_evidence is not None and worker_source_evidence['visited'] and science is not None and science['scientific'] is not None and len(science['scientific']['real_pairs'])==23 and len(science['normalization'])==11 and len(science['runtime'])==2 and len(science['scientific']['controls'])==8 and all(x['passed'] for x in science['scientific']['controls']) and science['guard_restoration'] is not None and science['guard_restoration']['import_guard_restored'] is True
    new_cpu=job.get('terminal_cpu_accounting') is True
    if not job.get('observed') and not parent.get('child_launch_entered') and worker is None and parent_account.get('value'):new_cpu=parent_account['value']['new_run_cpu_accounting_complete'] is True
    outcome=dict(schema='m193c-saved-real-accounting-repair-v2-audit-v1',status='PASS_SAVED_REAL_ACCOUNTING_REPAIR_V2_OUTCOME_AUDIT',subject_complete=complete,diagnostic_observations_verified=complete and full_science,verified_worker_scientific_population=full_science,admission_allowed=False,cpu_accounting_complete=False,new_run_cpu_accounting_complete=new_cpu,original_commission_complete=False,old_run_status='REFUSED',previous_real_run_status='REFUSED',subject_status=parent['status'],worker_status=None if worker is None else worker['status'],operational_exceptions=exceptions,external=external,worker_result=worker_ref,actual_request=request_ref,parent_request_link_retained=parent.get('request') is not None,resource_authorization=plan['resource_authorization'],private_baseline=plan['private_baseline'],failed_real_baseline=plan['failed_real_baseline'],callback_baseline=plan['callback_baseline'],failed_repair_baseline=plan['failed_repair_baseline'],evidence_bindings=plan['evidence_bindings'],previous_audit_semantics=dict(actual_audit=plan['failed_repair_baseline']['audit'],old_observed_resource_exception_retained=True,interpretation='Its false last_measured_transport field was conditioned on incomplete status; it is not evidence of an observed overrun. Full102CPU conservative charge is retained.'),source_evidence_controls=dict(parent=parent_source_evidence,worker=worker_source_evidence),audit_source=own,reused_general_source=g.file(GENERAL),reviewed_replacement=sources,accounting_implementation=parent_implementation,auditor_powered_checks=checks,operational_controls=op,live_wrapper_controls=live,parent_terminal=parent_terminal,worker_terminal=worker_terminal,parent_accounting_sample=parent_account,worker_accounting_sample=worker_account,scientific=None if science is None else scientific_summary(science['scientific']),publication_controls=[] if science is None else science['publication_controls'],codec_controls=[] if science is None else science['codec_controls'],normalization=[] if science is None else science['normalization'],model_state_witness=None if science is None else science['model_state_witness'],runtime=[] if science is None else science['runtime'],parent_runtime=runtime_final,graph=None if science is None else science['graph'],guard_restoration=None if science is None else science['guard_restoration'],accounting=account,actual_final_work=carry,next_wall_seconds=str(D(str(carry['wall_seconds']))),resource_bounds_respected=resource_ok and carry_inside,audit_timing=dict(cpu_seconds=audit_cpu,wall_seconds=audit_wall),audit_publication_allowance=TAIL,audit_family=family,audit_progress=g.file(PROGRESS),source_bindings_count=len(plan['source_bindings']),scope='Saved actual arrays, independently chosen literal private truth and whole-row residual/site populations, plus opaque manifest-bound runtime hashes. No images, checkpoint, subject, model or registrar execution. Same26 forwards/28 fits remain producer observations, never replayed here. Private actual inference observer is powered only at the after-call seam; complete recorded learned parameter hashes are witnesses, not independently reread parameter payloads. Learned matching conditions on the whole pair before geometric holdout. Final calibration-map membership is descriptive, not the unretained refinement subset. Real physical placement truth is absent; support guard remains unqualified for8-Q8 lattice. No support/placement/merge/SOTA admission. Historical CPU gaps remain. Canonical COMPLETE alone cannot establish operational completion; actual outer and final tail govern. Root must check this audit actual outer against sampled wall plus.5 before any continuation.')
    reported=output_copy(outcome);final_capacity(reported)
    data=compact(reported);need(len(data)<=RESERVES['final'],'bounded complete audit output before publication')
    need(time.process_time()-audit_cpu<=TAIL['cpu_seconds'] and time.perf_counter()-START-audit_wall<=TAIL['wall_seconds'],'serialization inside prospective publication allowance before final bounded write')
    sys.stdout.write(data.decode());sys.stdout.flush()

if __name__=='__main__':
    try:main()
    except BaseException:
        full=traceback.format_exc();error=dict(traceback_suffix=full[-4096:],full_utf8_sha256=sha(full.encode()),full_characters=len(full),status='INCOMPLETE_NO_ADMISSION')
        while len(compact(error))>4096:error['traceback_suffix']=error['traceback_suffix'][len(error['traceback_suffix'])//2:]
        publication_error=None
        try:
            if PROGRESS_OWNED:remember('audit-refused',error=error)
        except BaseException as exc:
            text=repr(exc);publication_error=dict(type=type(exc).__name__,suffix=text[-256:],full_utf8_sha256=sha(text.encode()))
        diagnostic=compact(dict(error=error,partial_publication_error=publication_error));need(len(diagnostic)<=RESERVES['stderr'],'bounded actual failure stderr')
        sys.stderr.write(diagnostic.decode());sys.stderr.flush();raise SystemExit(1)
