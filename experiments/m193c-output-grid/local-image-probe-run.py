"""One fixed local-image probe. Parent is stdlib-only; numerical work is child-only.
No launch, model, RAW, full-frame decode, graph fit or image read on import.
"""
import time
START=time.monotonic()
import argparse,ast,ctypes,ctypes.wintypes as wt,hashlib,io,json,math,os,stat,subprocess,sys,traceback,types
from contextlib import ExitStack
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
KIB=1024;MIB=1<<20;COMPLETE='COMPLETE_FIXED_LOCAL_IMAGE_PROBE_ONLY'
BASE=dict(cpu_seconds=1418.443678,wall_seconds=1321.9278447999966,file_bytes=4068213529,metadata_bytes=76952595)
PREP=dict(cpu_seconds=5,wall_seconds=10,file_bytes=MIB,metadata_bytes=MIB)
SUBJECT=dict(cpu_seconds=90,wall_seconds=140,file_bytes=60*MIB,metadata_bytes=60*MIB)
AUDIT=dict(cpu_seconds=25,wall_seconds=30,file_bytes=3*MIB,metadata_bytes=3*MIB)
PHASE=dict(cpu_seconds=120,wall_seconds=180,file_bytes=64*MIB,metadata_bytes=64*MIB)
CAPS=dict(cpu_seconds=1540,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=160*MIB)
EMPTY_SHA=hashlib.sha256(b'').hexdigest();RUNTIME_EMPTY={}
OLD_CAPS=dict(cpu_seconds=1440,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=128*MIB)
SLOT=64*KIB;PRIVATE_IDS=('zero','integer','fractional','differential-blur','flat','unrelated','periodic','outside-search')
PAIRS=((0,1),(3,4));ORDINALS=(0,1,3,4);ORIGINALS=(0,13,39,52)
PINS={
 'bounded-process.py':(None,'47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b'),
 'sift-lightglue-saved-completion-run.py':(44413,'12e3a81fb7dea313375f8227483b2303269c85357246d041a27ccd7d1033df27'),
 'work/independent-native-sensor-white-artifact-1-audit.json':(27399,'bb53b2437a0c6f0cbe45c9f4ee2a40e9fee540df9a4cc708d6acf60326094c28'),
 'work/independent-real-accounting-repair-v3-audit.json':(95373,'fcc60c8a0a5c4da71e7e10a4cb15c00e00f48bccedb24b547485663289674468'),
 'work/independent-real-accounting-repair-v3-audit-outer.json':(1157,'91f6102ea518e267392a56908951c83403200079176b31c85c1cb0cbdf48ba5f')}
HARNESS=ROOT/'experiments/m12-scorecard/m12-harness.py'
HARNESS_PIN=dict(bytes=117908,sha256='6cfb408992f37b225f102da4d62ba836f9c5b67c92bdd418ff460987866a1bb9')

def need(ok,message):
    if not ok:raise ValueError(message)
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def failure():
    raw=traceback.format_exc().encode();value=dict(full_utf8_bytes=len(raw),full_sha256=sha(raw),traceback_suffix=raw[-4096:].decode('utf-8','replace'))
    while len(encoded(value))>4096:value['traceback_suffix']=value['traceback_suffix'][len(value['traceback_suffix'])//2:]
    return value
def closed(v,keys):need(type(v) is dict and set(v)==set(keys),'closed metadata record')
def strict(raw):
    def pairs(items):
        d={}
        for k,v in items:need(k not in d,'duplicate JSON key');d[k]=v
        return d
    def walk(v):
        if type(v) is float:need(math.isfinite(v),'finite JSON')
        elif type(v) is dict:
            for x in v.values():walk(x)
        elif type(v) is list:
            for x in v:walk(x)
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)));walk(value);return value
def relative(p):return Path(p).resolve().relative_to(ROOT).as_posix()
def binding(raw):return dict(bytes=len(raw),sha256=sha(raw))
def identity(st):return tuple(int(getattr(st,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def ordinary(st,owned):need(stat.S_ISREG(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024 and st.st_nlink>=1 and (not owned or st.st_nlink==1),'regular non-reparse bound object/link policy')
def reference(path,raw):return dict(path=relative(path) if Path(path).resolve().is_relative_to(ROOT) else str(Path(path).resolve()),**binding(raw))
def bound(ref,cap=2*MIB,allow_empty=False):
    closed(ref,('path','bytes','sha256'));need(type(ref['path']) is str and type(ref['bytes']) is int and 0<=ref['bytes']<=cap and type(ref['sha256']) is str and len(ref['sha256'])==64,'typed bounded FileRef')
    path=(ROOT/ref['path']).resolve()
    if allow_empty:need(ref['bytes']==0 and ref['sha256']==EMPTY_SHA and RUNTIME_EMPTY.get(path)=={k:ref[k] for k in ('bytes','sha256')},'exact declared runtime-empty file role')
    else:need(ref['bytes']>0,'positive source or ordinary FileRef')
    before=path.lstat();owned=path.is_relative_to(HERE);ordinary(before,owned)
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno());ordinary(opened,owned);need(identity(before)==identity(opened),'same opened FileRef')
        raw=stream.read(cap+1);after=os.fstat(stream.fileno())
    named=path.lstat();ordinary(named,owned);need(identity(opened)==identity(after)==identity(named) and binding(raw)=={k:ref[k] for k in ('bytes','sha256')},'exact same-byte FileRef')
    return raw

def loaded(path,pin,name):
    raw=bound(dict(path=str(path),**pin),128*MIB);module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    exec(compile(raw,str(path),'exec'),module.__dict__);return module

def positive_namespace(values):
    need(type(values) is dict and 1<=len(values)<=8192,'finite binding namespace')
    for name,pin in values.items():
        need(type(name) is str and name and type(pin) is dict,'binding entry');closed(pin,('bytes','sha256'))
        need(type(pin['bytes']) is int and pin['bytes']>0 and type(pin['sha256']) is str and len(pin['sha256'])==64,'positive source/runtime namespace')

def runtime_namespace(positive,empty):
    positive_namespace(positive);need(type(empty) is dict and 1<=len(empty)<=4096 and not set(positive)&set(empty),'disjoint explicit runtime-empty namespace')
    for name,pin in empty.items():
        need(type(name) is str and name and type(pin) is dict,'runtime-empty entry');closed(pin,('bytes','sha256'))
        need(type(pin['bytes']) is int and pin['bytes']==0 and pin['sha256']==EMPTY_SHA,'typed literal runtime-empty declaration')
    names=[(ROOT/k).resolve() for k in [*positive,*empty]];need(len(names)==len(set(names)),'runtime resolved identities unique')
def runtime_bound(name,pin):return bound(dict(path=name,**pin),128*MIB,allow_empty=pin['bytes']==0)

def authority(args):
    global RUNTIME_EMPTY
    path=Path(args.plan).resolve();need(path==HERE/'local-image-probe-plan-1.json','fixed new plan path');extent=path.lstat().st_size;raw=bound(dict(path=str(path),bytes=extent,sha256=args.sha256),640*KIB);plan=strict(raw)
    closed(plan,('schema','source_bindings','runtime_bindings','runtime_empty_bindings','baseline_audit','baseline_outer','native_audit','resource_authorization','prior_work','python_executable','commands'))
    need(plan['schema']=='m193c-local-image-probe-plan-v1','plan version');positive_namespace(plan['source_bindings']);runtime_namespace(plan['runtime_bindings'],plan['runtime_empty_bindings']);RUNTIME_EMPTY={(ROOT/name).resolve():pin for name,pin in plan['runtime_empty_bindings'].items()}
    for name,pin in plan['source_bindings'].items():bound(dict(path=name,**pin),128*MIB)
    for name in ('local-image-probe-run.py','local-image-probe.py','local-image-patches.py','local-image-probe-preregister.md','local-image-probe-ledger.json','bounded-process.py','sift-lightglue-saved-completion-run.py'):
        need(relative(HERE/name) in plan['source_bindings'],'complete selected source closure')
    need(plan['source_bindings'][relative(HARNESS)]==HARNESS_PIN,'exact pure Job source')
    for name,(size,digest) in PINS.items():
        data=bound(dict(path=relative(HERE/name),**plan['source_bindings'][relative(HERE/name)]))
        need(sha(data)==digest and (size is None or len(data)==size),'fixed predecessor evidence/source')
    for role,name in (('baseline_audit','work/independent-real-accounting-repair-v3-audit.json'),('baseline_outer','work/independent-real-accounting-repair-v3-audit-outer.json'),('native_audit','work/independent-native-sensor-white-artifact-1-audit.json')):
        need((ROOT/plan[role]['path']).resolve()==HERE/name and {k:plan[role][k] for k in ('bytes','sha256')}==plan['source_bindings'][relative(HERE/name)],'exact prior role path/content')
    old=strict(bound(plan['baseline_audit']));outer=strict(bound(plan['baseline_outer']));native=strict(bound(plan['native_audit']))
    need(old['status']=='PASS_SAVED_REAL_ACCOUNTING_REPAIR_V3_OUTCOME_AUDIT' and old['subject_complete'] is True and old['admission_allowed'] is old['cpu_accounting_complete'] is False and old['actual_final_work']==BASE,'limited old audited outcome and historical CPU gap')
    need(outer['exit_code']==0 and outer['stderr_bytes']==0 and outer['stdout_bytes']==plan['baseline_audit']['bytes'] and outer['elapsed_wall_seconds']<=old['audit_timing']['wall_seconds']+old['audit_publication_allowance']['wall_seconds'],'actual previous audit final wall tail')
    previous=strict(bound(old['external']['plan']))
    need(all(plan['source_bindings'].get(k)==v for k,v in previous['source_bindings'].items()),'all prior positive source bindings preserved')
    need(native['status']=='PASS_SAVED_SENSOR_WHITE_ARTIFACT_OUTCOME_AUDIT','actual native image authority')
    frames=[native['frames'][i] for i in ORDINALS]
    need([r['ordinal'] for r in frames]==list(ORDINALS) and [r['original_index'] for r in frames]==list(ORIGINALS) and all(r['tiff']['bytes']==197798267 for r in frames),'fixed native image population')
    grant=strict(bound(plan['resource_authorization']));closed(grant,('schema','baseline_audit','baseline_outer','retained_work','previous_limits','new_limits','phase_allowance','preparation_allowance','subject_allowance','audit_allowance','scope'))
    need(grant==dict(schema='m193c-local-image-resource-authorization-v1',baseline_audit=plan['baseline_audit'],baseline_outer=plan['baseline_outer'],retained_work=BASE,previous_limits=OLD_CAPS,new_limits=CAPS,phase_allowance=PHASE,preparation_allowance=PREP,subject_allowance=SUBJECT,audit_allowance=AUDIT,scope='ONE_FIXED_LOCAL_IMAGE_PROBE; NO_RETIRED_COST_REFUND; NO_GEOMETRY_ADMISSION'),'explicit scoped CPU/metadata amendment')
    need(plan['prior_work']=={k:BASE[k]+PREP[k] for k in BASE} and all(BASE[k]+PHASE[k]<=CAPS[k] for k in BASE),'full prior/preparation charge and complete phase capacity')
    bound(plan['python_executable'],128*MIB);need(Path(plan['python_executable']['path']).resolve()==Path(sys.executable).resolve(),'exact pinned interpreter')
    closed(plan['commands'],('parent','worker'));actual=sys.orig_argv;expected=[args.sha256 if v=='ACTUAL_PLAN_SHA256' else v for v in plan['commands']['worker' if args.worker else 'parent']]
    need(actual==expected and sys.dont_write_bytecode and not sys._xoptions and Path.cwd().resolve()==ROOT,'exact current argv/cwd/no bytecode')
    output=Path(args.output).resolve();need(output==HERE/'local-image-probe-1'/('worker' if args.worker else '') and not output.exists(),'fresh fixed owned output')
    ledger=strict(bound(dict(path=relative(HERE/'local-image-probe-ledger.json'),**plan['source_bindings'][relative(HERE/'local-image-probe-ledger.json')])))
    need(ledger['schema']=='m193c-local-image-probe-ledger-v1' and ledger['phase']==PHASE and ledger['preparation']==PREP and ledger['subject']==SUBJECT and ledger['audit']==AUDIT,'exact finite phase ledger')
    need(sum(ledger['preparation_component_caps'].values())<=MIB and sum(ledger['worker_literal_maxima'].values())==ledger['worker_literal_maximum_bytes']<=59*MIB and sum(ledger['parent_component_caps'].values())<=MIB,'full source/plan/wrapper/data/output capacity')
    return plan,frames,output,reference(path,raw)

class Store:
    def __init__(self,output,worker):
        self.output=output;self.worker=worker;self.extents={};self.latest_job=None;self.job_queries=0;self.job_error=None;self.started=START
        output.mkdir();self.reserve('result.json',SLOT);self.reserve('result-stage.json',SLOT)
        self.publish(dict(schema='m193c-local-image-probe-worker-v1' if worker else 'm193c-local-image-probe-run-v1',status='REFUSED',phase='INITIAL_INCOMPLETE'))
    def reserve(self,name,size):
        path=self.output/name;need(path.is_relative_to(self.output) and type(size) is int and size>0,'owned positive write extent')
        self.extents[name]=max(size,self.extents.get(name,0));need(sum(self.extents.values())<=(59*MIB if self.worker else MIB),'fixed worker/parent file reservation')
    def check(self):
        need(self.job_error is None,'live Job observation error');cpu=time.process_time()+(0 if self.latest_job is None else self.latest_job['total_cpu_100ns']/1e7)
        need(cpu<=(85 if self.worker else 88),'live process plus owned Job CPU');need(time.monotonic()-START<=(130 if self.worker else 135),'ordinary work wall bound')
    def save(self,name,raw,cap):
        self.check();need(type(raw) is bytes and len(raw)<=cap,'bounded fresh artifact');self.reserve(name,len(raw));path=self.output/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:need(stream.write(raw)==len(raw),'full artifact write');stream.flush();os.fsync(stream.fileno())
        self.check();return reference(path,raw)
    def json(self,name,value,cap=64*KIB):return self.save(name,encoded(value),cap)
    def retained_json(self,name,value,cap):
        raw=encoded(value);need(len(raw)<=cap and self.extents.get(name,0)>=cap,'precharged retained receipt');path=self.output/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:need(stream.write(raw)==len(raw),'complete retained receipt');stream.flush();os.fsync(stream.fileno())
        return reference(path,raw)
    def publish(self,value):
        raw=encoded(value);need(len(raw)<=SLOT,'terminal fixed slot envelope');raw=raw.rstrip(b'\n').ljust(SLOT-1,b' ')+b'\n';stage=self.output/'result-stage.json'
        with stage.open('xb') as stream:need(stream.write(raw)==SLOT,'complete staged terminal');stream.flush();os.fsync(stream.fileno())
        os.replace(stage,self.output/'result.json');return reference(self.output/'result.json',raw)

def runtime(plan,store):
    # Complete Python module-file registry, not a native DLL dependency or parameter-state attestation.
    result=[];seen={};module_rows=[]
    for name,module in sorted(sys.modules.items()):
        value=getattr(module,'__file__',None)
        if not value:continue
        path=Path(value).resolve()
        if path.suffix.lower() in ('.pyc','.pyo'):
            import importlib.util
            path=Path(importlib.util.source_from_cache(str(path))).resolve()
        key=relative(path) if path.is_relative_to(ROOT) else str(path)
        allowed=plan['source_bindings'].get(key,plan['runtime_bindings'].get(key,plan['runtime_empty_bindings'].get(key)))
        need(allowed is not None,'undeclared imported module file: '+key)
        if key not in seen:
            store.check();raw=runtime_bound(key,allowed);seen[key]=len(result);result.append(reference(path,raw))
        module_rows.append([name,seen[key]])
    return store.json('runtime-modules.json',dict(schema='m193c-local-image-runtime-v1',files=result,modules=module_rows,scope='Actual imported module-file bytes and aliases only; native dependent DLL closure is not asserted.'),2*MIB)


def namespace_controls(plan,store):
    positive=plan['runtime_bindings'];empty=plan['runtime_empty_bindings'];name=sorted(empty)[0];pin=empty[name];original=sha(encoded([positive,empty]));rows=[]
    def attempt(label,callback,refusal):
        error=None
        try:callback()
        except ValueError as exc:error=str(exc)
        passed=(error is not None)==refusal;rows.append(dict(id=label,expected_refusal=refusal,passed=passed,error=error))
    attempt('actual-positive-and-empty-runtime',lambda:runtime_namespace(positive,empty),False)
    actual=runtime_bound(name,pin);need(actual==b'','actual declared empty module file')
    attempt('zero-as-source',lambda:bound(dict(path=name,**pin)),True)
    for label,key,value in (('false-empty','bytes',False),('nonzero-empty','bytes',1),('wrong-empty-sha','sha256','0'*64)):
        changed={**empty,name:{**pin,key:value}};attempt(label,lambda v=changed:runtime_namespace(positive,v),True)
    overlap={**positive,name:dict(bytes=1,sha256='0'*64)};attempt('overlapping-runtime-path',lambda:runtime_namespace(overlap,empty),True)
    unknown=dict(path=relative(HERE/'work/unlisted-empty-runtime-control.py'),bytes=0,sha256=EMPTY_SHA)
    attempt('unknown-empty-file-role',lambda:bound(unknown,allow_empty=True),True)
    attempt('restored-namespace',lambda:runtime_namespace(positive,empty),False)
    need(sha(encoded([positive,empty]))==original,'complete runtime namespaces unchanged')
    passed=all(row['passed'] for row in rows)
    record=store.json('runtime-namespace-controls.json',dict(passed=passed,schema='m193c-local-image-runtime-namespace-controls-v1',rows=rows,positive_count=len(positive),empty_count=len(empty),complete_namespace_before_sha256=original,complete_namespace_after_sha256=sha(encoded([positive,empty])),actual_empty_file=dict(path=name,**pin),unknown_empty_operand=unknown,scope='Actual same-handle empty read plus typed namespace/file-role controls; no numerical or scientific execution.'),8*KIB)
    return record,passed

def worker_science(plan,frames,store,state):
    state['runtime_namespace_controls'],namespace_passed=namespace_controls(plan,store);store.publish(state);need(namespace_passed,'runtime namespace controls failed')
    runtime_size=0;runtime_all={**plan['runtime_bindings'],**plan['runtime_empty_bindings']}
    for name,pin in sorted(runtime_all.items()):
        store.check();data=runtime_bound(name,pin);runtime_size+=len(data)
    state['runtime_intake']=store.json('runtime-intake.json',dict(schema='m193c-local-image-runtime-intake-v1',declared_files=len(runtime_all),empty_files=len(plan['runtime_empty_bindings']),declared_bytes=runtime_size,complete_namespace_sha256=sha(encoded(runtime_all)),scope='Opaque declared module-file authentication before numerical imports; no dependent-DLL closure claim.'),4*KIB)
    probe=loaded(HERE/'local-image-probe.py',plan['source_bindings'][relative(HERE/'local-image-probe.py')],'m193c_fixed_local_estimator')
    patches=loaded(HERE/'local-image-patches.py',plan['source_bindings'][relative(HERE/'local-image-patches.py')],'m193c_fixed_native_patches')
    import numpy as np
    need(probe.PAIRS==PAIRS and probe.CONTROL_IDS==PRIVATE_IDS and probe.SIDE==129 and probe.RADIUS==32 and probe.UPSAMPLE==100,'fixed science source/interface')
    state['planned_controls']=['rgb16-strip-reader',*PRIVATE_IDS,'observer-output','literal-displacement-oracle']
    centres=probe.centres(7032,4688);state['unvisited']=[f'{a}-{b}/g{g:02d}/q{q}' for a,b in PAIRS for g in range(16) for q in range(4)]
    state['counters']=dict(image_patch_reads=0,real_estimator_calls=0,private_estimator_calls=0,raw_decodes=0,full_frame_arrays=0,feature_extractions=0,model_calls=0,registrar_calls=0)
    def saved_array(name,value):
        need(value.dtype in (np.dtype('uint16'),np.dtype('float32')) and value.ndim in (2,3),'finite declared data array')
        dtype='<u2' if value.dtype==np.uint16 else '<f4';data=np.ascontiguousarray(value,dtype=dtype).tobytes()
        return dict(file=store.save(name,data,129*129*6),dtype=dtype,shape=list(value.shape))
    def save_inputs(prefix,rgb0,rgb1):
        a,b=probe.project(rgb0),probe.project(rgb1)
        data=dict(reference_rgb=saved_array(prefix+'-reference-rgb.u16',rgb0),source_rgb=saved_array(prefix+'-source-rgb.u16',rgb1),reference_f32=saved_array(prefix+'-reference.f32',a),source_f32=saved_array(prefix+'-source.f32',b))
        return a,b,data
    def control(name,passed,value):
        record=store.json('controls/'+name+'.json',dict(schema='m193c-local-image-control-v1',id=name,passed=passed,**value))
        state['controls'].append(dict(id=name,passed=passed,record=record));state['phase']='CONTROL_'+name;store.publish(state)
        need(passed,'private control failed: '+name)
    def call(a,b,observer=None,real=False):
        store.check();state['counters']['real_estimator_calls' if real else 'private_estimator_calls']+=1
        return probe.estimate(a,b,observer)
    # Same production strip parser and patch reader against independently indexed literal RGB rows.
    reader_cases=[]
    for endian in ('<','>'):
        data=patches.fixture_bytes(endian);image=store.save('controls/reader-'+('le' if endian=='<' else 'be')+'.tiff',data,256*KIB)
        stream=io.BytesIO(data);info=patches.layout(stream,len(data),(139,137,3));rect=[5,7,129,129];raw=patches.patch(stream,info,len(data),rect)
        actual=np.frombuffer(raw,dtype=endian+'u2').reshape(129,129,3).astype(np.uint16)
        yy,xx=np.indices((129,129),dtype=np.uint16);yy+=5;xx+=7
        expected=np.stack((100+yy*3+xx,200+yy+xx*2,300+yy*2+xx*3),axis=2)
        projected=probe.project(actual);error=0.
        # Scalar f64 reference chooses a different computation order; bound actual f32 projection at .001 DN.
        for row in range(129):
            for col in range(129):
                expected_value=sum(float(expected[row,col,c])*probe.LUMA[c] for c in range(3));error=max(error,abs(float(projected[row,col])-expected_value))
        rejected=False
        try:patches.patch(stream,info,len(data),[11,7,129,129])
        except ValueError:rejected=True
        reader_cases.append(dict(endian=endian,file=image,rect=rect,actual_rgb_sha256=sha(actual.astype('<u2').tobytes()),literal_rgb_sha256=sha(expected.astype('<u2').tobytes()),projection_maximum_error_dn=error,out_of_image_rejected=rejected,passed=bool(np.array_equal(actual,expected)) and error<=.001 and rejected))
    control('rgb16-strip-reader',all(x['passed'] for x in reader_cases),dict(cases=reader_cases))
    fractional=None;literal={'zero':(0.,0.),'integer':(5.,-7.),'fractional':(1.25,-.4),'differential-blur':(1.25,-.4),'outside-search':(40.,0.)}
    expected_refusal={'flat':'FLAT_OR_LOW_CONTRAST','periodic':'AMBIGUOUS_MULTIPLE_PEAKS','outside-search':'OUTSIDE_FIXED_SEARCH'}
    for name in PRIVATE_IDS:
        before_a,before_b,declared=probe.fixture(name)
        if name in literal:need(tuple(declared)==literal[name],'literal independently declared displacement')
        # Commission actual RGB16->f32 analysis path, with explicit nearest-even quantization of continuous private signals.
        rgb=[]
        for v in (before_a,before_b):
            need(v.shape==(129,129) and v.dtype==np.float32 and np.isfinite(v).all() and np.min(v)>=0 and np.max(v)<=65535,'bounded private continuous native signal')
            rgb.append(np.repeat(np.rint(v).astype(np.uint16)[:,:,None],3,axis=2))
        a,b,inputs=save_inputs('controls/'+name,*rgb);result,surface=call(a,b)
        error=None if name not in literal or result['status']!='RETURNED_LOCAL_TRANSLATION' else max(abs(result['feature_displacement_source_minus_reference_dydx_native'][i]-literal[name][i]) for i in range(2))
        if name in probe.POSITIVE:passed=error is not None and error<=probe.TRUTH_LIMIT
        else:passed=result['status']=='REFUSED' and (name not in expected_refusal or result['reason']==expected_refusal[name])
        if name=='outside-search':passed=passed and result['coarse_alignment_dydx_native'] is not None and max(abs(v) for v in result['coarse_alignment_dydx_native'])>32
        control(name,passed,dict(inputs=inputs,outcome=result,surface=saved_array('controls/'+name+'-surface.f32',surface),literal_displacement_dydx_native=literal.get(name),maximum_component_error_native=error,required_reason=expected_refusal.get(name)))
        if name=='fractional':fractional=(a,b,result)
    a,b,fractional_result=fractional;rows=[];hashes=[]
    for mode in ('off','on','placebo','restored'):
        visits=[]
        def observer(result,surface):
            # Actual diagnostic vs equal-access placebo; all reads, no fitted/selected rows.
            value=dict(surface_hash=probe.digest(surface),peak=float(np.max(surface)),mean=float(np.mean(surface,dtype=np.float32)))
            visits.append(value if mode=='on' else dict(surface_hash=value['surface_hash'],peak=0.,mean=0.))
        result,surface=call(a,b,observer if mode in ('on','placebo') else None)
        intrinsic=sha(probe.canonical(result));h=probe.digest(surface);hashes.append([intrinsic,h])
        rows.append(dict(mode=mode,outcome=result,surface=saved_array('controls/observer-'+mode+'-surface.f32',surface),observer_visits=visits))
    rejected=False
    try:call(a,b,lambda result,surface:result.update(reason='INJECTED_OUTPUT_MUTATION'))
    except ValueError as exc:rejected=str(exc)=='actual observer changed input or output'
    restored,surface=call(a,b)
    rows.append(dict(mode='after-rejected-mutation',outcome=restored,surface=saved_array('controls/observer-after-mutation-surface.f32',surface),observer_visits=[]))
    hashes.append([sha(probe.canonical(restored)),probe.digest(surface)])
    control('observer-output',rejected and all(h==hashes[0] for h in hashes) and [len(r['observer_visits']) for r in rows]==[0,1,1,0,0],dict(rows=rows,whole_outcome_and_surface_hashes=hashes,actual_mutating_observer_rejected=rejected,scope='Actual estimator input/output observer seam only.'))
    mutated=strict(encoded(fractional_result));mutated['feature_displacement_source_minus_reference_dydx_native']=[-v for v in mutated['feature_displacement_source_minus_reference_dydx_native']]
    original_error=max(abs(fractional_result['feature_displacement_source_minus_reference_dydx_native'][i]-literal['fractional'][i]) for i in range(2));wrong_error=max(abs(mutated['feature_displacement_source_minus_reference_dydx_native'][i]-literal['fractional'][i]) for i in range(2))
    control('literal-displacement-oracle',original_error<=probe.TRUTH_LIMIT and wrong_error>probe.TRUTH_LIMIT,dict(original=fractional_result,wrong_sign=mutated,literal=list(literal['fractional']),original_error_native=original_error,wrong_error_native=wrong_error,restored_complete_outcome_sha256=sha(probe.canonical(fractional_result))))
    frames_by_id={row['ordinal']:row for row in frames}
    for reference_id,source_id in PAIRS:
        frame0,frame1=frames_by_id[reference_id],frames_by_id[source_id];native_receipts=[{},{}];pair_name=f'{reference_id}-{source_id}'
        store.reserve('real/'+pair_name+'/native-file-reads.json',64*KIB)
        try:
            with ExitStack() as stack:
                opened=[]
                for frame,receipt in zip((frame0,frame1),native_receipts):
                    opened.append(stack.enter_context(patches.opened(ROOT/frame['tiff']['path'],frame['tiff'],(4688,7032,3),store.check,receipt)))
                for grid_index,(cy,cx) in enumerate(centres):
                    outcomes=[];record_refs=[]
                    for quadrant,(dy,dx) in enumerate(probe.OFFSETS):
                        key=f'{pair_name}/g{grid_index:02d}/q{quadrant}';rect=[cy+dy-64,cx+dx-64,129,129];rgb=[]
                        for stream,info,extent in opened:
                            data=patches.patch(stream,info,extent,rect);state['counters']['image_patch_reads']+=1
                            rgb.append(np.frombuffer(data,dtype=info['endian']+'u2').reshape(129,129,3).astype(np.uint16))
                        a,b,inputs=save_inputs('real/'+key,*rgb);result,surface=call(a,b,real=True);outcomes.append(result)
                        record=store.json('real/'+key+'.json',dict(schema='m193c-local-image-patch-v1',id=key,pair=[reference_id,source_id],original_pair=[frame0['original_index'],frame1['original_index']],native_images=[frame0['tiff'],frame1['tiff']],grid_index=grid_index,grid_centre_yx_native=[cy,cx],quadrant=quadrant,rect_yxhw_native=rect,inputs=inputs,outcome=result,surface=saved_array('real/'+key+'-surface.f32',surface)))
                        record_refs.append(record);state['real'].append(dict(id=key,status=result['status'],reason=result['reason'],record=record));need(state['unvisited'][0]==key,'fixed ordered complete real population');state['unvisited'].pop(0);state['phase']=key;store.publish(state)
                    record=store.json('real/'+pair_name+f'/g{grid_index:02d}-disjoint.json',dict(schema='m193c-local-image-disjoint-v1',pair=[reference_id,source_id],grid_index=grid_index,patch_records=record_refs,reproducibility=probe.reproduce(outcomes),scope='Disjoint finite-patch reproducibility only. Correlation is texture-weighted; scale/rotation can cause disagreement and diagonal point-displacement algebra does not calibrate this estimator.'))
                    state['disjoint'].append(record)
        finally:
            receipt=store.retained_json('real/'+pair_name+'/native-file-reads.json',dict(images=[frame0['tiff'],frame1['tiff']],receipts=native_receipts),64*KIB);state['native_reads'].append(receipt)
    need(len(state['real'])==128 and len(state['disjoint'])==32 and not state['unvisited'] and state['counters']['private_estimator_calls']==14 and state['counters']['real_estimator_calls']==128 and state['counters']['image_patch_reads']==256,'complete fixed population; no extra image/estimator calls')
    state['runtime_modules']=runtime(plan,store);state['status']=COMPLETE;state['phase']='COMPLETE'


def parent_child(plan,args,store,state,plan_ref):
    helper=loaded(HERE/'sift-lightglue-saved-completion-run.py',plan['source_bindings'][relative(HERE/'sift-lightglue-saved-completion-run.py')],'m193c_local_job_selector')
    api=helper.selected(HARNESS,HARNESS_PIN,helper.JOB_NAMES+helper.JOB_SIGNATURES)
    process=loaded(HERE/'bounded-process.py',plan['source_bindings'][relative(HERE/'bounded-process.py')],'m193c_local_bounded_process')
    original=api.job_accounting
    def observing(job):
        try:
            value=original(job);before=encoded(value)
            for key in ('total_user_100ns','total_kernel_100ns','total_cpu_100ns','active_processes'):need(type(value[key]) is int and value[key]>=0,'typed nonnegative actual Job CPU')
            need(value['total_cpu_100ns']==value['total_user_100ns']+value['total_kernel_100ns'],'actual Job CPU sum')
            if store.latest_job is not None:need(value['total_cpu_100ns']>=store.latest_job['total_cpu_100ns'],'nondecreasing observed owned Job CPU')
            store.latest_job=dict(value);store.job_queries+=1;need(encoded(value)==before,'accounting observer preserves returned object');return value
        except BaseException as exc:store.job_error=repr(exc);raise
    api.job_accounting=observing
    env,removed=process.clean_environment((('OMP_NUM_THREADS','1'),('OPENBLAS_NUM_THREADS','1'),('MKL_NUM_THREADS','1'),('NUMEXPR_NUM_THREADS','1'),('VECLIB_MAXIMUM_THREADS','1'),('PYTHONDONTWRITEBYTECODE','1'),('PYTHONHASHSEED','0')))
    for key in ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT'):env.pop(key,None)
    command=[args.sha256 if x=='ACTUAL_PLAN_SHA256' else x for x in plan['commands']['worker']]
    store.reserve('worker.log',256*KIB);store.reserve('child-terminal.json',64*KIB)
    try:job=process.run(command,env,ROOT,store.output/'worker.log',api=api,wall_seconds=130,cpu_seconds=85,log_bytes=256*KIB,committed_bytes=1<<30,check=store.check)
    finally:api.job_accounting=original
    # Publication lane deliberately has no ordinary CPU/wall gate: retain actual Job data even on a cap refusal.
    raw=encoded(dict(schema='m193c-local-image-child-terminal-v1',plan=plan_ref,job=job,live_queries=store.job_queries,latest_job=store.latest_job,accounting_error=store.job_error,environment_removed=removed,environment_fixed={k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED')}))
    need(len(raw)<=64*KIB,'durable child receipt extent');path=store.output/'child-terminal.json'
    with path.open('xb') as stream:need(stream.write(raw)==len(raw),'durable exact child receipt');stream.flush();os.fsync(stream.fileno())
    state['child_terminal']=reference(path,raw);state['current_job_accounting_complete']=bool(job['terminal_job_accounting'])
    child_path=store.output/'worker/result.json';child_raw=child_path.read_bytes() if child_path.exists() else None
    if child_raw is not None:
        need(len(child_raw)==SLOT,'exact child terminal extent');child=strict(child_raw);state['worker_result']=reference(child_path,child_raw);state['worker_status']=child['status'];state['verified_worker_scientific_population']=child['status']==COMPLETE
    clean=job['exit_code']==0 and job['error'] is None and not job['cleanup_errors'] and job['terminal_job_accounting'] and store.job_error is None
    need(clean and child_raw is not None and child['status']==COMPLETE,'retained child did not complete cleanly')
    store.check();state['status']=COMPLETE;state['phase']='COMPLETE'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--sha256',required=True);parser.add_argument('--output',required=True);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    plan,frames,output,plan_ref=authority(args);store=Store(output,args.worker)
    state=dict(schema='m193c-local-image-probe-worker-v1' if args.worker else 'm193c-local-image-probe-run-v1',status='REFUSED',phase='INITIALIZED',plan=plan_ref,controls=[],real=[],disjoint=[],native_reads=[],unvisited=[],error=None,worker_result=None,child_terminal=None,historical_cpu_accounting_complete=False,scope='Fixed local native image translation diagnostic. No real physical truth, similarity, graph support, per-frame placement, merge input or SOTA admission.')
    try:
        if args.worker:worker_science(plan,frames,store,state)
        else:parent_child(plan,args,store,state,plan_ref)
    except BaseException:
        state['status']='REFUSED';state['error']=failure()
    state['timing_sample']=dict(process_cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START,job_cpu_seconds=None if store.latest_job is None else store.latest_job['total_cpu_100ns']/1e7,scope='Current process sample plus complete owned Job where retained; final publication has2CPU/5wall reserved allowance, not a measured terminal parent sample.')
    state['high_water_extent_bytes']=sum(store.extents.values());charge=dict(SUBJECT)
    if not args.worker:
        charge['cpu_seconds']=max(charge['cpu_seconds'],state['timing_sample']['process_cpu_seconds']+(state['timing_sample']['job_cpu_seconds'] or 0)+2)
        charge['wall_seconds']=max(charge['wall_seconds'],state['timing_sample']['wall_seconds']+5)
    state['charged_work_policy']={k:plan['prior_work'][k]+charge[k] for k in BASE};state['unspent_audit_reservation']=AUDIT
    state['resource_admissible']=state['timing_sample']['process_cpu_seconds']+(state['timing_sample']['job_cpu_seconds'] or 0)+(0 if args.worker else 2)<= (85 if args.worker else 90) and state['timing_sample']['wall_seconds']+(0 if args.worker else 5)<=(130 if args.worker else 140)
    state['cumulative_capacity_for_reserved_audit']=all(state['charged_work_policy'][k]+AUDIT[k]<=CAPS[k] for k in BASE)
    if not state['resource_admissible'] or not state['cumulative_capacity_for_reserved_audit']:state['status']='REFUSED'
    result=store.publish(state)
    print(encoded(dict(schema='m193c-local-image-terminal-v1',status=state['status'],result=result,timing_sample=state['timing_sample'],resource_admissible=state['resource_admissible'],charged_work_policy=state['charged_work_policy'])).decode(),end='',flush=True)
    return 0 if state['status']==COMPLETE else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        message=encoded(dict(status='REFUSED',error=failure()));sys.stderr.write(message.decode());raise SystemExit(1)
