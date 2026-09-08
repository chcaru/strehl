"""Independent saved-metadata startup audit. Stdlib only; never imports subjects.
No child, product, RAW/TIFF, model, monitor, native API or image operation.
"""
import time
START=time.monotonic()
import argparse,ast,copy,hashlib,json,math,os,stat,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SELF=Path(__file__).resolve()
KIB=1024;MIB=1<<20;CAPS=dict(cpu_seconds=10,wall_seconds=20,file_bytes=MIB)
SOURCE_PIN=(24534,'48698b704042766c24aaeb5fe674d493e628cc58397ec0823e4c10a4a30afe44')
SPEC_PIN=(12750,'fbd2d8425ccace3229a65d4159f203ecaa3d1ecd9d94c630ce3bd25db14fa492')
ARMS=('off','on','placebo','before-popen-delay','after-resume-delay')
PHASES=('startup-system-times','startup-memory-status','startup-create-job','startup-stdout-open','startup-stderr-open','startup-popen','startup-assign-job','startup-resume')
COMPLETE='COMPLETE_PRIVATE_STARTUP_OBSERVATIONS_ONLY'
SCOPE='Private saved startup observations only; no production coverage, exact historical cause, changed sampling origin, timing improvement or campaign admission.'
CONSUMED={};PROGRESS=None;STAGES=[]

def need(ok,msg):
    if not ok:raise ValueError(msg)
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check():need(time.process_time()+.25<=10 and time.monotonic()-START+.5<=20,'independent audit10CPU20wall including final reserve')
def integer(v):return type(v) is int and v>=0
def number(v):return type(v) in (int,float) and math.isfinite(v) and v>=0
def close(a,b,tolerance=1e-8):return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tolerance

def parse(raw):
    def pairs(items):
        out={}
        for key,value in items:need(key not in out,'duplicate JSON key');out[key]=value
        return out
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
    def finite(x):
        if type(x) is float:need(math.isfinite(x),'finite JSON')
        elif type(x) is dict:
            for v in x.values():finite(v)
        elif type(x) is list:
            for v in x:finite(v)
    finite(value);return value

def path_of(value):
    path=Path(value)
    need(path.is_absolute(),'absolute evidence path')
    for item in (path,*path.parents):
        st=item.lstat();need(not stat.S_ISLNK(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024,'no lexical reparse evidence')
    return path.resolve()
def fields(st):return tuple(int(getattr(st,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def ref_shape(ref):
    need(type(ref) is dict and set(ref)=={'path','bytes','sha256'} and type(ref['path']) is str and integer(ref['bytes']) and type(ref['sha256']) is str and len(ref['sha256'])==64 and all(c in '0123456789abcdefABCDEF' for c in ref['sha256']),'closed typed FileRef')
def file(path,cap,expected=None,expected_hash=None):
    check();path=path_of(path);before=path.lstat();need(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=cap and (not path.is_relative_to(ROOT) or before.st_nlink==1),'bounded ordinary evidence')
    if expected is not None:ref_shape(expected);need(path_of(expected['path'])==path and expected['bytes']<=cap,'exact role identity/extent before read')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno());need(fields(before)==fields(opened),'same opened evidence')
        raw=stream.read(cap+1);after=os.fstat(stream.fileno())
    named=path.lstat();need(fields(before)==fields(opened)==fields(after)==fields(named) and len(raw)==before.st_size,'same complete stable evidence buffer')
    ref=dict(path=str(path),bytes=len(raw),sha256=sha(raw))
    if expected is not None:need(ref['bytes']==expected['bytes'] and ref['sha256']==expected['sha256'].lower(),'exact saved evidence bytes')
    if expected_hash is not None:need(ref['sha256']==expected_hash.lower(),'released exact digest')
    need(str(path) not in CONSUMED or CONSUMED[str(path)]==ref,'previously consumed file remained unchanged');CONSUMED[str(path)]=ref;return raw,ref

def read(ref,cap=384*KIB):
    ref_shape(ref);raw,actual=file(ref['path'],cap,expected=ref);return parse(raw),actual

def same(a,b):
    ref_shape(a);ref_shape(b);return path_of(a['path'])==path_of(b['path']) and a['bytes']==b['bytes'] and a['sha256'].lower()==b['sha256'].lower()
def retained(phase,summary):
    STAGES.append(dict(phase=phase,summary=summary));value=dict(schema='m192e-startup-audit-progress-v1',status='INCOMPLETE_NO_ADMISSION',visited=STAGES,commission_pass=False)
    raw=encode(value);need(len(raw)<=32*KIB,'bounded startup audit progress')
    temp=PROGRESS.with_name(PROGRESS.stem+'-stage.json')
    with temp.open('xb') as stream:need(stream.write(raw)==len(raw),'progress complete');stream.flush();os.fsync(stream.fileno())
    os.replace(temp,PROGRESS)

def job(value):
    need(type(value) is dict,'Job object')
    for key in ('total_user_100ns','total_kernel_100ns','total_cpu_100ns','active_processes','total_processes','total_terminated_processes'):need(integer(value.get(key)),'typed actual Job components')
    need(value['total_cpu_100ns']==value['total_user_100ns']+value['total_kernel_100ns'],'actual user plus kernel CPU')
    return value['total_cpu_100ns']/1e7

def slot(path):
    raw,ref=file(path,32768);need(len(raw)==32768,'fixed publisher slot')
    value=parse(raw);canonical=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();need(raw==canonical+b' '*(32768-len(canonical)),'whole original publisher encoding/padding')
    return value,ref

def publisher(folder,planref):
    actual={};values={}
    for name in ('result.json','first-publication.json','publication-stage.json','emergency-refusal.json'):
        path=folder/name
        if path.exists():values[name],actual[name]=slot(path);need(same(values[name]['plan'],planref),'all retained publication plan associations')
    need('result.json' in values,'actual canonical publication')
    canonical=values['result.json'];positive=values.get('first-publication.json')
    if canonical['status']==COMPLETE:need(positive==canonical and actual['first-publication.json']['sha256']==actual['result.json']['sha256'],'whole first-positive/canonical equality')
    elif canonical.get('first_positive') is not None:need(same(canonical['first_positive'],actual['first-publication.json']),'refusal preserves actual first positive')
    return canonical,actual,dict(canonical=actual['result.json'],status=canonical['status'],first_positive=None if positive is None or positive['status']!=COMPLETE else actual['first-publication.json'],slots=actual,scope='Canonical and actual outer govern; a stale stdout advertisement cannot override refusal.')

def source_structure(sources):
    # Re-choose the original AST slices. No compile/exec or subject function call.
    def source(path):
        ref=sources[str(path.resolve())];raw,_=file(ref['path'],MIB,expected=ref);return ast.parse(raw,str(path))
    sampler=source(ROOT/'experiments/m192c-sampler/sampler.py');harness=source(ROOT/'experiments/m12-scorecard/m12-harness.py')
    monitor=next(n for n in sampler.body if isinstance(n,ast.FunctionDef) and n.name=='monitor');assign=next(n for n in harness.body if isinstance(n,ast.FunctionDef) and n.name=='assign_process_to_job')
    boundary=min(n.lineno for n in ast.walk(monitor) if isinstance(n,ast.While))
    mkeys=('h.system_times','h.memory_status','k32.CreateJobObjectW',"(folder / 'stdout.log').open","(folder / 'stderr.log').open",'subprocess.Popen','h.assign_process_to_job')
    akeys=('kernel32.AssignProcessToJobObject','ntdll.NtResumeProcess')
    def counts(node,keys,before):return {k:sum(isinstance(n,ast.Call) and ast.unparse(n.func)==k and n.lineno<before for n in ast.walk(node)) for k in keys}
    mc=counts(monitor,mkeys,boundary);ac=counts(assign,akeys,10**9);need(all(v==1 for v in [*mc.values(),*ac.values()]),'independently selected complete startup call population')
    def rewritten(original,mapping,before):
        node=copy.deepcopy(original)
        for call in list(ast.walk(node)):
            if not isinstance(call,ast.Call) or call.lineno>=before:continue
            key=ast.unparse(call.func)
            if key not in mapping:continue
            if key=='h.assign_process_to_job':call.func=ast.Attribute(value=ast.Name(id='probe',ctx=ast.Load()),attr='assign',ctx=ast.Load())
            else:
                call.args=[ast.Constant(mapping[key]),call.func,*call.args];call.func=ast.Attribute(value=ast.Name(id='probe',ctx=ast.Load()),attr='call',ctx=ast.Load())
        return sha(ast.dump(node,include_attributes=False).encode())
    mm=dict(zip(mkeys,(*PHASES[:6],'assignment-helper')));am=dict(zip(akeys,PHASES[6:]))
    return dict(monitor_original_ast_sha256=sha(ast.dump(monitor,include_attributes=False).encode()),assignment_original_ast_sha256=sha(ast.dump(assign,include_attributes=False).encode()),monitor_changed_ast_sha256=rewritten(monitor,mm,boundary),assignment_changed_ast_sha256=rewritten(assign,am,10**9),monitor_counts=mc,assignment_counts=ac)

def proof(value,kind,expected):
    need(type(value) is dict and value['original_ast_sha256'].lower()==value['restored_ast_sha256'].lower()==expected[kind+'_original_ast_sha256'],'original/restored complete AST hashes')
    counts=expected['monitor_counts' if kind=='monitor' else 'assignment_counts'];need(value['replacement_counts']==value['reverse_replacement_counts']==counts,'complete forward/reverse counts')
    need(value['changed_ast_sha256'].lower()==expected[kind+'_changed_ast_sha256'] and value['changed_ast_sha256'].lower()!=value['original_ast_sha256'].lower(),'complete independently re-derived wrapper AST')

def intervals(raw):
    need(type(raw['trace']) is dict and raw['trace']['enabled'] is True and raw['trace']['injection'] is None and raw['trace']['injected'] is False and raw['trace']['placebo'] is False,'unchanged regular trace mode')
    dropped=raw['trace']['dropped'];need(set(dropped)=={'events','observations','incidents','telemetry'} and all(type(v) is int and v==0 for v in dropped.values()),'complete untruncated private trace')
    observations=raw['trace']['observations'];events=raw['trace']['events'];need(1<=len(observations)<=1000 and raw['sample_count']==len(observations),'complete observed population')
    start,end=raw['start_ns'],raw['end_ns'];need(integer(start) and integer(end) and start<end,'actual monitor endpoints')
    previous=start;gaps=[];sample_starts=[]
    for i,row in enumerate(observations):
        need(row['poll']==i and integer(row['start_ns']) and integer(row['observed_ns']) and previous<=row['start_ns']<=row['observed_ns']<=end,'monotone complete independent observation rows')
        gaps.append(row['observed_ns']-previous);previous=row['observed_ns'];sample_starts.append(row['start_ns'])
    missed=0;next_sample=start
    for sample in sample_starts[:-1]:
        next_sample+=10000000
        if next_sample<=sample:
            skipped=(sample-next_sample)//10000000+1;missed+=skipped;next_sample+=skipped*10000000
    coverage=len(observations)/(len(observations)+missed)
    need(raw['missed_intervals']==missed and close(raw['coverage'],coverage) and close(raw['legacy_start_max_gap_ms'],max([0,*[b-a for a,b in zip(sample_starts,sample_starts[1:])]])/1e6),'independently reconstructed original skipped/coverage arithmetic')
    need(close(raw['wall_seconds'],(end-start)/1e9),'actual monitor duration')
    final=[r for r in events if r['phase']=='final-memory'];need(len(final)==1,'unique final-memory bracket')
    for event in events:
        need(integer(event['start_ns']) and integer(event['end_ns']) and start<=event['start_ns']<=event['end_ns']<=end and close(event['wall_ms'],(event['end_ns']-event['start_ns'])/1e6,1e-6),'whole phase timestamp order/duration')
    lower=final[0]['end_ns']-observations[-1]['observed_ns'];upper=end-observations[-1]['observed_ns'];need(0<=lower<=upper,'final closure bounded by actual endpoints')
    exact=None
    for incident in raw['trace']['incidents']:
        trigger=incident['trigger']
        if trigger['kind']=='final-closure-gap':
            need(trigger['start_ns']==observations[-1]['observed_ns'] and lower<=trigger['end_ns']-trigger['start_ns']<=upper,'actual closure incident endpoints');exact=trigger['end_ns']-trigger['start_ns']
    claimed_tail=raw['final_interval_ms']*1e6;need(lower-1e-6<=claimed_tail<=upper+1e-6,'reported final-interval witness inside independently retained bracket')
    if exact is not None:need(close(claimed_tail,exact,1e-6),'exact retained closure incident')
    known=max(gaps);lo=max(known,lower);hi=max(known,upper)
    if exact is not None:lo=hi=max(known,exact)
    elif known>=upper:lo=hi=known
    reported=raw['max_interval_ms_including_final']*1e6
    need(lo-1e-6<=reported<=hi+1e-6 and close(reported,max(known,claimed_tail),1e-6),'whole reported maximum consistent with actual intervals and explicit tail witness')
    sampling=reported<=100000000 and coverage>=.9;need(raw['sampling_pass'] is sampling,'unchanged100ms/90percent reported disposition')
    independently_determined=(hi<=100000000 or lo>100000000 or coverage<.9)
    return dict(observations=len(observations),phase_events=len(events),first_interval_ms=gaps[0]/1e6,maximum_initial_or_inter_observation_ms=known/1e6,final_closure_lower_ms=lower/1e6,final_closure_upper_ms=upper/1e6,reported_final_interval_ms=raw['final_interval_ms'],full_maximum_lower_ms=lo/1e6,full_maximum_upper_ms=hi/1e6,exact_full_maximum_ms=None if lo!=hi else lo/1e6,original_gate_independently_determined=independently_determined,reported_sampling_pass=sampling,missed_intervals=missed,coverage=coverage,scope='Final interval remains a reported witness unless retained endpoints determine it; no synthesized closed_at.'),observations,events


def arm_record(ref,arm,out,plan,structure):
    area=out/'arms'/arm;need(path_of(ref['path'])==area/'record.json','fixed ordered arm record')
    row,actual_ref=read(ref,16*KIB);need(row['arm']==arm,'arm identity')
    expected=[plan['python']['path'],'-B',str(ROOT/'experiments/m192c-sampler/child.py'),'--mode','null','--output',str(area/'null-output.bin'),'--receipt',str(area/'child-receipt.json')]
    need(row['command']==expected and number(row['wall_seconds']),'exact null argv/finite arm wall')
    startup,start_ref=read(row['startup'],8*KIB);need(path_of(start_ref['path'])==area/'startup.json' and startup['arm']==arm and startup['baseline_query_added'] is startup['old_sampling_origin_changed'] is False,'actual startup record/no clock mutation')
    if row['raw'] is None:
        need(row['passed'] is False and row['error'] is not None,'retained operational arm failure')
        return dict(arm=arm,record=actual_ref,startup=start_ref,operational=False,expected_disposition_pass=False,error=row['error']),None
    raw,raw_ref=read(row['raw']);need(path_of(raw_ref['path'])==area/'monitor.json' and raw['argv']==expected and raw['mode']=='on','original raw monitor association')
    summary,obs,events=intervals(raw);cpu=job(raw['job_accounting']);need(close(cpu,raw['product_cpu_seconds']),'whole recorded inner Job CPU')
    children,child_ref=read(row['child_receipt'],8192);need(path_of(child_ref['path'])==area/'child-receipt.json' and type(children) is list and len(children)==2,'whole fixed null child receipt')
    begin,end=children;need(begin['event']=='start' and end['event']=='end' and begin['mode']=='null' and integer(begin['pid']) and begin['pid']>0 and begin['pid']==end['pid'] and integer(begin['parent_pid']) and integer(begin['qpc_ns']) and integer(end['qpc_ns']) and raw['start_ns']<=begin['qpc_ns']<end['qpc_ns']<=obs[-1]['observed_ns'],'independent child identity/lifetime within observations')
    matches=[p for p in raw['processes'] if p['pid']==begin['pid']];need(len(matches)==1 and integer(matches[0]['created']) and matches[0]['parent_pid']==begin['parent_pid'],'monitor creation-identity table agrees with independent child PID/parent')
    phases=startup['phases'];delay=None
    if arm=='off':need(startup['mode']=='OFF' and phases==[] and all(startup[k] is None for k in ('child_pid','actual_popen_argv','actual_popen_flags','monitor_ast','assignment_ast')),'actual uninstrumented off arm')
    else:
        proof(startup['monitor_ast'],'monitor',structure);proof(startup['assignment_ast'],'assignment',structure)
        native=[r for r in phases if r['scope']=='ACTUAL_STARTUP_CALL'];need([r['phase'] for r in native]==list(PHASES),'all original startup seams exercised once')
        need(startup['mode']==('ON_LABEL_PLACEBO' if arm=='placebo' else 'ON') and startup['child_pid']==begin['pid'] and startup['actual_popen_argv']==expected and startup['actual_popen_flags']==4,'actual Popen identity/argv/suspended flags')
        for r in phases:
            need(integer(r['start_ns']) and integer(r['end_ns']) and r['start_ns']<=r['end_ns'] and integer(r['thread_cpu_start_ns']) and integer(r['thread_cpu_end_ns']) and r['thread_cpu_start_ns']<=r['thread_cpu_end_ns'] and raw['start_ns']<=r['start_ns']<=r['end_ns']<=obs[0]['observed_ns'] and r.get('error') is None,'complete successful startup brackets')
        need(all(a['end_ns']<=b['start_ns'] for a,b in zip(native,native[1:])),'unchanged actual native/file call order')
        need(native[5]['returned_pid']==begin['pid'] and native[2]['native_result']>0 and native[6]['native_result']!=0 and native[7]['native_result']==0,'actual create/assign/resume success')
        injected=[r for r in phases if r['scope']=='INJECTED_OBSERVER_DELAY']
        if arm in ('on','placebo'):need(injected==[] and len(phases)==8,'no hidden untreated delay')
        else:
            need(len(injected)==1 and len(phases)==9 and injected[0]['phase']==arm and injected[0]['requested_delay_ms']==150,'one fixed injected observer delay')
            delay=injected[0];popen=native[5];resume=native[7];elapsed=(delay['end_ns']-delay['start_ns'])/1e6
            if arm=='before-popen-delay':positioned=delay['end_ns']<=popen['start_ns']<begin['qpc_ns']
            else:positioned=resume['end_ns']<=delay['start_ns']<delay['end_ns']<=obs[0]['observed_ns'] and resume['start_ns']<=begin['qpc_ns']<=delay['end_ns']
            need(row['positioned'] is positioned and close(row['injected_phase_ms'],elapsed),'independently re-chosen child timestamp positioning')
            delay=dict(phase=arm,elapsed_ms=elapsed,positioned=positioned,starts_before_child=delay['start_ns']<begin['qpc_ns'],ends_before_child=delay['end_ns']<=begin['qpc_ns'],child_start_inside_delay=delay['start_ns']<=begin['qpc_ns']<=delay['end_ns'],observer_thread_cpu_ms=(delay['thread_cpu_end_ns']-delay['thread_cpu_start_ns'])/1e6)
    null_path=area/'null-output.bin';need(path_of(row['output']['path'])==null_path,'fixed nonempty output role')
    output,output_ref=file(null_path,8192,expected=row['output']);literal=b'M192c deterministic synthetic output\nnull\n'+bytes(range(256))*16;need(output==literal and end['output_bytes']==len(literal),'independently known whole nonempty output')
    intrinsic=dict(returncode=raw['returncode'],output=dict(bytes=len(output),sha256=sha(output).upper()))
    logs={}
    for name in ('stdout','stderr'):
        target=area/'monitor'/(name+'.log');need(path_of(row['logs'][name]['path'])==target,'exact native log association');data,log_ref=file(target,8192,expected=row['logs'][name]);logs[name]=log_ref;intrinsic[name]=dict(bytes=len(data),sha256=sha(data).upper())
    need(row['intrinsic']==intrinsic and row['sampling_pass'] is raw['sampling_pass'] and close(row['coverage'],summary['coverage']) and close(row['maximum_interval_ms'],raw['max_interval_ms_including_final']) and close(row['first_observation_interval_ms'],summary['first_interval_ms']) and row['dropped']==raw['trace']['dropped'],'whole saved intrinsic/control summary association')
    common=raw['returncode']==0 and raw['job_accounting']['active_processes']==0 and row['error'] is startup['error'] is None
    expected_pass=common and (raw['sampling_pass'] if arm in ('off','on','placebo') else delay['elapsed_ms']>=140 and delay['positioned'] and raw['max_interval_ms_including_final']>=140 and raw['sampling_pass'] is False)
    first=obs[0]['observed_ns'];start=raw['start_ns'];a=max(0,min(first,begin['qpc_ns'])-start);b=max(0,min(first,end['qpc_ns'])-max(start,begin['qpc_ns']));c=max(0,first-max(start,end['qpc_ns']));need(a+b+c==first-start,'literal disjoint child-time partition')
    wrong=bytearray(output);wrong[-1]^=1;need(bytes(wrong)!=literal and sha(wrong)!=sha(literal) and bytes(output)==literal,'known wrong-byte rejection and unchanged restored placebo')
    return dict(arm=arm,record=actual_ref,startup=start_ref,raw=raw_ref,child=child_ref,output=output_ref,logs=logs,operational=common,source_reported_pass=row['passed'],expected_disposition_pass=expected_pass,intervals=summary,delay=delay,child_pid=begin['pid'],child_parent_pid=begin['parent_pid'],created_identity=matches[0]['created'],child_cpu_seconds=end['cpu_s'],inner_job_cpu_seconds=cpu,initial_gap_partition_ms=dict(before_child_start=a/1e6,during_child_lifetime=b/1e6,after_child_end=c/1e6,scope='Arithmetic partition by independent child timestamps; unchanged original sampling gate.'),output_oracle=dict(literal_bytes=len(literal),literal_sha256=sha(literal),wrong_byte_sha256=sha(wrong),wrong_rejected=True,restored_sha256=sha(output))),intrinsic


def inventory(out):
    rows=[];total=0
    for folder,dirs,names in os.walk(out,followlinks=False):
        for name in dirs:path_of(Path(folder)/name)
        for name in names:
            path=Path(folder)/name;rel=path.relative_to(out).as_posix();allowed=False;cap=0
            if rel in ('worker.log','child.json','progress.json'):allowed=True;cap={'worker.log':128*KIB,'child.json':64*KIB,'progress.json':32*KIB}[rel]
            elif len(path.relative_to(out).parts)==2 and path.relative_to(out).parts[0] in ('parent','worker') and name in ('result.json','first-publication.json','publication-stage.json','emergency-refusal.json'):allowed=True;cap=32768
            else:
                parts=path.relative_to(out).parts
                if len(parts)>=3 and parts[0]=='arms' and parts[1] in ARMS:
                    tail='/'.join(parts[2:]);caps={'record.json':16*KIB,'startup.json':8*KIB,'monitor.json':384*KIB,'null-output.bin':8192,'child-receipt.json':8192,'monitor/stdout.log':8192,'monitor/stderr.log':8192,'monitor/temp/fixture.bin':4096};allowed=tail in caps;cap=caps.get(tail,0)
            need(allowed,'unlisted startup output file: '+rel);raw,ref=file(path,cap);total+=len(raw);rows.append(dict(relative_path=rel,bytes=len(raw),sha256=ref['sha256']))
            if rel.endswith('/fixture.bin'):need(raw==bytes(4096),'actual null scan fixture bytes')
    rows.sort(key=lambda x:x['relative_path']);need(total<=3*MIB,'whole observed private output extent');return dict(files=len(rows),file_bytes=total,inventory_sha256=sha(encode(rows)),rows=rows)


def main():
    global PROGRESS
    ap=argparse.ArgumentParser()
    for role in ('plan','outer','stdout','exit'):
        ap.add_argument('--'+role,required=True,type=Path);ap.add_argument('--'+role+'-sha256',required=True)
    ap.add_argument('--result-sha256');ap.add_argument('--worker-sha256');ap.add_argument('--source-sha256',required=True);args=ap.parse_args()
    own,own_ref=file(SELF,64*KIB,expected_hash=args.source_sha256)
    external={};values={}
    for role,cap in (('plan',65536),('outer',16384),('stdout',16384),('exit',32)):
        data,external[role]=file(getattr(args,role),cap,expected_hash=getattr(args,role+'_sha256'));values[role]=parse(data) if role in ('plan','outer') else data
    plan=values['plan'];need(set(plan)=={'schema','source_bindings','rehearsal_baseline','python','output_directory','commands','resource_limits'} and plan['schema']=='m192e-startup-attribution-plan-v1','closed actual plan')
    need(plan['resource_limits']==dict(phase_cpu_seconds=20,phase_wall_seconds=30,source_bytes=MIB,output_bytes=3*MIB,audit_cpu_seconds=10,audit_wall_seconds=20,audit_file_bytes=MIB),'same fixed phase/audit ceilings')
    need(type(plan['source_bindings']) is list and len(plan['source_bindings'])<=64,'bounded complete source count')
    for r in plan['source_bindings']:ref_shape(r);need(r['bytes']>0,'typed positive source before aggregate')
    need(sum(r['bytes'] for r in plan['source_bindings'])<=MIB,'complete source aggregate before reading')
    sources={}
    for ref in plan['source_bindings']:
        ref_shape(ref);need(ref['bytes']>0,'positive bound source');path=path_of(ref['path']);need(str(path) not in sources,'unique source');sources[str(path)]=ref;file(path,MIB,expected=ref)
    for name,pin in (('startup-attribution-run.py',SOURCE_PIN),('startup-attribution-preregister.md',SPEC_PIN)):
        r=sources[str(HERE/name)];need((r['bytes'],r['sha256'].lower())==pin,'independently reviewed held subject bytes')
    need(same(sources[str(SELF)],own_ref),'actual independent checker source in held plan')
    py=plan['python'];need(path_of(py['path'])==Path(sys.executable).resolve(),'same actual pinned Python');file(py['path'],16*MIB,expected=py)
    outer=values['outer'];template=plan['commands']['parent'];need(template.count('ACTUAL_PLAN_SHA256')==1 and len(outer['command'])==len(template),'one actual command hash placeholder')
    actual_hash=outer['command'][template.index('ACTUAL_PLAN_SHA256')];need(actual_hash.lower()==external['plan']['sha256'],'actual invocation digest spelling authenticates same plan')
    expected=[actual_hash if x=='ACTUAL_PLAN_SHA256' else x for x in template];code=int(values['exit'].decode().strip())
    need(outer['command']==expected and type(outer['exit_code']) is int and outer['exit_code']==code and number(outer['elapsed_wall_seconds']),'actual parent command/exit/wall association')
    if 'stdout_bytes' in outer:need(outer['stdout_bytes']==external['stdout']['bytes'],'actual stdout extent')
    out=path_of(plan['output_directory']);need(out.parent==HERE and out.name.startswith('startup-attribution-'),'exact owned private output scope')
    PROGRESS=HERE/(out.name+'-audit-progress.json');need(not PROGRESS.exists() and not PROGRESS.with_name(PROGRESS.stem+'-stage.json').exists(),'fresh audit progress slots')
    baseline=plan['rehearsal_baseline'];need(set(baseline)=={'plan','result','outer','verification','diagnosis','independent_review'},'all six historical baseline refs')
    for ref in baseline.values():file(ref['path'],65536,expected=ref)
    old,_=read(baseline['verification'],16384);need(old['status']=='PASS_BOUND_TERMINAL_REHEARSAL_ONLY' and old['integration_pass'] is old['sampling_all_pass'] is False and old['output_nonperturbation'] is True and same(old['plan'],baseline['plan']) and same(old['parent'],baseline['result']) and same(old['outer'],baseline['outer']),'actual old integration remains failed')
    structure=source_structure(sources);retained('authority',dict(plan=external['plan'],out=str(out),sources=len(sources),old_integration_pass=False,structure=structure))
    parent=None;worker=None;parent_summary=None;worker_summary=None;pubrefs={};rows=[];intrinsics=[];child=None;job_cpu=None;operational=False
    path=out/'parent/result.json'
    if path.exists():
        need(args.result_sha256 is not None,'released actual parent canonical hash');_,external['result']=file(path,32768,expected_hash=args.result_sha256)
        parent,refs,parent_summary=publisher(out/'parent',external['plan']);need(same(parent_summary['canonical'],external['result']),'parsed parent is same released bytes');pubrefs.update(refs)
    else:need(args.result_sha256 is None,'explicit absent parent receipt');external['result']=dict(path=str(path),absent=True)
    path=out/'worker/result.json'
    if path.exists():
        if parent is not None and parent.get('worker') is not None:file(path,32768,expected=parent['worker'],expected_hash=args.worker_sha256)
        else:need(args.worker_sha256 is not None,'separate release pin for unlinked worker canonical');file(path,32768,expected_hash=args.worker_sha256)
        worker,_,worker_summary=publisher(out/'worker',external['plan'])
        if parent is not None and parent.get('worker') is not None:need(same(worker_summary['canonical'],parent['worker']),'parsed worker is same linked bytes')
        if args.worker_sha256 is not None:need(worker_summary['canonical']['sha256']==args.worker_sha256.lower(),'supplied worker release pin always enforced')
    ads=[];other=[]
    for line in values['stdout'].decode('utf-8','replace').splitlines():
        try:v=parse(line)
        except Exception:other.append(line);continue
        if type(v) is dict and set(v)=={'status','plan','result'}:ads.append(v)
        else:other.append(line)
    if parent is not None and parent['status']==COMPLETE and code==0:
        need(len(ads)==1 and not other and same(ads[0]['plan'],external['plan']) and same(ads[0]['result'],parent_summary['canonical']) and ads[0]['status']==COMPLETE,'actual current parent stdout advertisement')
    retained('publication',dict(parent=None if parent_summary is None else parent_summary['canonical'],worker=None if worker_summary is None else worker_summary['canonical'],parent_status=None if parent is None else parent['status'],worker_status=None if worker is None else worker['status'],advertisements=len(ads),other_stdout_lines=len(other),exit_code=code))
    if worker is not None:
        refs=worker.get('arms',[]);need(type(refs) is list and len(refs)<=5,'finite saved arm prefix')
        for arm,ref in zip(ARMS,refs):
            result,intrinsic=arm_record(ref,arm,out,plan,structure);rows.append(result)
            if intrinsic is not None:intrinsics.append(intrinsic)
            retained('arm-'+arm,{k:result[k] for k in ('arm','record','startup','operational','expected_disposition_pass','intervals','delay','output_oracle') if k in result})
        unvisited=worker.get('unvisited',list(ARMS));need(unvisited==list(ARMS[len(refs):]),'ordered retained/unvisited suffix')
        if worker['status']==COMPLETE:need(len(refs)==5 and not unvisited,'complete means all fixed observations')
    else:unvisited=list(ARMS)
    identical=len(intrinsics)==5 and all(v==intrinsics[0] for v in intrinsics)
    for row,intrinsic in zip([r for r in rows if 'source_reported_pass' in r],intrinsics):
        saved,_=read(row['record'],16384);matches=intrinsic==intrinsics[0];need(saved['intrinsic_matches_off'] is matches,'actual entire intrinsic versus off')
        expected=row['expected_disposition_pass'] and matches;need(saved['passed'] is expected,'whole actual expected disposition including identity');row['expected_disposition_pass']=expected
    all_pass=len(rows)==5 and identical and all(r['operational'] and r['expected_disposition_pass'] and r['intervals']['original_gate_independently_determined'] for r in rows)
    if worker is not None and worker['status']==COMPLETE:need(worker['all_five_pass'] is all(r.get('source_reported_pass',False) for r in rows) and worker['intrinsic_all_identical'] is identical,'whole worker summary')
    if parent is not None and parent.get('child') is not None:
        child,child_ref=read(parent['child'],65536);need(path_of(child_ref['path'])==out/'child.json','actual durable child receipt')
        if child==dict(status='UNOBSERVED',terminal_job_accounting=False):
            need(type(child['terminal_job_accounting']) is bool,'exact typed prelaunch placeholder');clean=False
        else:
            expected_child=[actual_hash if v=='ACTUAL_PLAN_SHA256' else v for v in plan['commands']['worker']];need(child['command']==expected_child,'actual owned worker command')
            if child.get('job_accounting') is not None:job_cpu=job(child['job_accounting'])
            clean=child.get('exit_code')==0 and child.get('error') is None and child.get('cleanup_errors')==[] and child.get('terminal_job_accounting') is True and child['job_accounting']['active_processes']==0 and child.get('termination',{}).get('attempted') is False
            need(child['limits']['committed_bytes']==512*MIB and child['limits']['log_bytes']==128*KIB and 8<=child['limits']['wall_seconds']<=12 and 0<child['limits']['cpu_seconds']<=20,'fixed owned Job envelope')
            if clean:
                need(child['direct_exit_observed'] is child['pipe_eof_observed'] is True and child['post_exit_drain']['completed'] is True and child['post_exit_drain']['observation_count']>=1,'actual whole Job drain')
                need(child['configured_job_limits']==dict(flags=0x2200,committed_bytes=512*MIB) and number(child['wall_seconds']) and child['wall_seconds']<=child['limits']['wall_seconds'] and job_cpu<=child['limits']['cpu_seconds'] and integer(child['job_memory']['peak_job_memory_used_bytes']) and child['job_memory']['peak_job_memory_used_bytes']<=512*MIB,'actual final Job limits and memory readback')
    else:clean=False;child_ref=None
    accounting=None
    if parent is not None and parent.get('accounting_sample') is not None:
        a=parent['accounting_sample'];need(parent['complete_process_cpu_accounting'] is False and parent['actual_outer_exit_required'] is True and parent['publication_allowance']==dict(cpu_seconds=.25,wall_seconds=.5),'explicit sampled parent plus policy publication tail')
        need(all(number(a[k]) for k in ('parent_or_worker_process_cpu_seconds','latest_owned_job_cpu_seconds','wall_seconds','observed_file_bytes')),'finite final accounting')
        if job_cpu is not None:need(close(a['latest_owned_job_cpu_seconds'],job_cpu),'saved final actual Job CPU used once')
        cpu=a['parent_or_worker_process_cpu_seconds']+(job_cpu or 0)+.25;wall=outer['elapsed_wall_seconds'];resource=job_cpu is not None and cpu<=20 and wall<=30 and wall<=a['wall_seconds']+.5 and a['accounting_error'] is None
        accounting=dict(sample=a,owned_job=child_ref,job_cpu_seconds=job_cpu,parent_sample_plus_job_plus_tail_cpu_seconds=cpu,whole_outer_wall_seconds=wall,resource_admissible=resource,complete_parent_cpu_measured=False,scope='Complete retained worker Job plus parent sample and.25CPU reserve; inner null Job totals are not added again. Actual outer closes.5wall publication allowance.')
    else:resource=False
    inv=inventory(out);external_extra=sum(r.get('bytes',0) for k,r in external.items() if k in ('outer','stdout','exit','plan'));source_total=sum(r['bytes'] for r in sources.values());need(inv['file_bytes']+external_extra+source_total<=4*MIB,'complete source/plan/root-receipt/output family within4MiB')
    if parent is not None and parent['status']==COMPLETE:
        need(worker is not None and parent['arms']==worker['arms'] and parent['all_five_pass']==worker['all_five_pass'] and parent['intrinsic_all_identical']==worker['intrinsic_all_identical'],'whole parent worker summary links')
    operational=parent is not None and worker is not None and parent['status']==worker['status']==COMPLETE and code==0 and clean and resource
    commission=operational and all_pass;status='PASS_SAVED_PRIVATE_STARTUP_OUTCOME_AUDIT' if commission else 'VERIFIED_PRIVATE_STARTUP_NOT_COMMISSIONED'
    retained('final-accounting',dict(operational_complete=operational,all_five_pass=all_pass,accounting=accounting,files=inv['files'],bytes=inv['file_bytes']))
    check();result=dict(schema='m192e-saved-startup-attribution-audit-v1',status=status,verified_record_complete=True,subject_complete=operational,commission_pass=commission,admission_allowed=commission,external=external,audit_source=own_ref,source_structure=structure,source_bindings_count=len(sources),parent=parent_summary,worker=worker_summary,arms=rows,unvisited=unvisited,whole_intrinsic_identity=identical,all_five_correct_dispositions=all_pass,accounting=accounting,inventory=inv,advertisements=ads,nonadvertisement_stdout=dict(lines=len(other),sha256=sha('\n'.join(other).encode())),audit_timing=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START),audit_publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),audit_caps=CAPS,audit_family=dict(source=64*KIB,source_review=8*KIB,result=128*KIB,progress=32*KIB,stage=32*KIB,outer=8*KIB,stderr=8*KIB,report=16*KIB,maximum_bytes=296*KIB,cap_bytes=MIB),scope=SCOPE+' Root must check actual audit outer against this sampled wall plus.5; untreated failures are not retries.')
    raw=encode(result);need(len(raw)<=128*KIB,'bounded entire saved startup audit result');sys.stdout.write(raw.decode());sys.stdout.flush();return 0 if commission else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        raw=traceback.format_exc().encode();error=dict(schema='m192e-startup-audit-error-v1',status='AUDIT_INCOMPLETE_NO_ADMISSION',full_traceback_bytes=len(raw),full_traceback_sha256=sha(raw),traceback_suffix=raw[-4096:].decode('utf-8','replace'))
        while len(encode(error))>8192:error['traceback_suffix']=error['traceback_suffix'][len(error['traceback_suffix'])//2:]
        if PROGRESS is not None:
            try:retained('audit-incomplete',error)
            except Exception:pass
        sys.stderr.write(encode(error).decode());raise SystemExit(1)
