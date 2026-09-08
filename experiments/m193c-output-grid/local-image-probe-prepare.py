"""Metadata-only release preparation for one fixed local-image probe.
No subject, numerical package, model, RAW or TIFF import/read/execution.
"""
import time
START=time.monotonic()
import argparse,hashlib,json,math,os,stat,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
PYTHON=Path(r'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe')
MIB=1<<20;KIB=1024;EMPTY=hashlib.sha256(b'').hexdigest();SEEN={};ANCESTORS=set()
BASE=dict(cpu_seconds=1418.443678,wall_seconds=1321.9278447999966,file_bytes=4068213529,metadata_bytes=76952595)
PREP=dict(cpu_seconds=5,wall_seconds=10,file_bytes=MIB,metadata_bytes=MIB)
SUBJECT=dict(cpu_seconds=90,wall_seconds=140,file_bytes=60*MIB,metadata_bytes=60*MIB)
AUDIT=dict(cpu_seconds=25,wall_seconds=30,file_bytes=3*MIB,metadata_bytes=3*MIB)
PHASE=dict(cpu_seconds=120,wall_seconds=180,file_bytes=64*MIB,metadata_bytes=64*MIB)
CAPS=dict(cpu_seconds=1540,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=160*MIB)
OLD_CAPS=dict(cpu_seconds=1440,wall_seconds=1800,file_bytes=4*(1<<30),metadata_bytes=128*MIB)
LEDGER=dict(fresh_sources_and_reviews=256*KIB,plan=640*KIB,authorization=8*KIB,
            outer_console_exit=16*KIB,preparation_receipt=32*KIB,inventory_receipt=64*KIB)
REQUIRED=('local-image-probe-prepare.py','local-image-probe-preparation.md',
 'local-image-probe-run.py','local-image-probe.py','local-image-patches.py','local-image-probe-preregister.md','local-image-probe-ledger.json',
 'work/independent-local-image-probe-source-review.md','work/root-local-image-probe-source-read.md',
 'work/independent-local-image-probe-audit.py','work/independent-local-image-probe-preparation-review.md')
FIXED={
 'real-accounting-repair-plan-2.json':(67155,'362ed32da1459334d1066ddde9826afc75195050aa7eb5d8263db46f7362d478'),
 'work/independent-real-accounting-repair-v3-audit.json':(95373,'fcc60c8a0a5c4da71e7e10a4cb15c00e00f48bccedb24b547485663289674468'),
 'work/independent-real-accounting-repair-v3-audit-outer.json':(1157,'91f6102ea518e267392a56908951c83403200079176b31c85c1cb0cbdf48ba5f'),
 'work/independent-native-sensor-white-artifact-1-audit.json':(27399,'bb53b2437a0c6f0cbe45c9f4ee2a40e9fee540df9a4cc708d6acf60326094c28')}
PACKAGES=('numpy','scipy','skimage','lazy_loader','packaging','imageio','PIL')
SKIP={'site-packages','__pycache__','tests','test'}

def need(ok,message):
    if not ok:raise ValueError(message)
def check():
    need(time.process_time()+.25<=5 and time.monotonic()-START+.5<=10,'preparation including reserved final CPU/wall tail')
def key(path):
    path=Path(path).resolve();return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
def encode(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(st):return tuple(int(getattr(st,k,0)) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_file_attributes','st_nlink'))
def ordinary(st,owned):
    need(stat.S_ISREG(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024 and st.st_nlink>=1 and (not owned or st.st_nlink==1),'regular bound non-reparse file')
def safe_path(path):
    # Check lexical ancestors before resolving; never normalize away a reparse point.
    path=Path(os.path.abspath(path))
    for parent in (path.parent,*path.parent.parents):
        if str(parent) not in ANCESTORS:
            st=parent.lstat();need(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode) and not getattr(st,'st_file_attributes',0)&1024,'ordinary path ancestry')
            ANCESTORS.add(str(parent))
    return path
def read(path,cap=128*MIB,expected=None,empty=False):
    check();path=safe_path(path);before=path.lstat();owned=path.is_relative_to(HERE);ordinary(before,owned)
    need(type(cap) is int and (0 if empty else 1)<=before.st_size<=cap,'bounded extent before read')
    if expected is not None:need(before.st_size==expected['bytes'],'expected extent before read')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno());ordinary(opened,owned);need(identity(before)==identity(opened),'same opened file')
        raw=stream.read(before.st_size+1);after=os.fstat(stream.fileno())
    named=path.lstat();ordinary(named,owned)
    need(identity(before)==identity(after)==identity(named) and len(raw)==before.st_size,'same complete file identity')
    ref=dict(path=key(path),bytes=len(raw),sha256=sha(raw))
    if expected is not None:need({k:ref[k] for k in ('bytes','sha256')}==expected,'exact held bytes/hash')
    if not raw:need(empty and ref['sha256']==EMPTY,'explicit empty runtime initializer only')
    SEEN[str(path)]=(identity(named),owned);check();return raw,ref

def strict(raw):
    def pairs(items):
        out={}
        for k,v in items:need(k not in out,'duplicate JSON key');out[k]=v
        return out
    def finite(value):
        if type(value) is float:need(math.isfinite(value),'finite JSON scalar')
        elif type(value) is dict:
            for v in value.values():finite(v)
        elif type(value) is list:
            for v in value:finite(v)
    obj=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite JSON')));finite(obj);return obj

def namespaces(sources,runtime,empty):
    need(type(sources) is dict and sources and type(runtime) is dict and runtime and type(empty) is dict,'declared three namespaces')
    need(not(set(sources)&set(runtime) or set(sources)&set(empty) or set(runtime)&set(empty)),'disjoint binding namespaces')
    for values,allow_empty in ((sources,False),(runtime,False),(empty,True)):
        need(len(values)<=8192,'bounded binding namespace')
        for name,pin in values.items():
            need(type(name) is str and name and type(pin) is dict and set(pin)=={'bytes','sha256'} and type(pin['bytes']) is int and
                type(pin['sha256']) is str and len(pin['sha256'])==64 and all(c in '0123456789abcdef' for c in pin['sha256']),'typed binding')
            need(pin==dict(bytes=0,sha256=EMPTY) if allow_empty else pin['bytes']>0,'namespace extent policy')

def write(path,raw,cap):
    need(type(raw) is bytes and len(raw)<=cap and not path.exists(),'bounded exclusive release artifact')
    with path.open('xb') as stream:
        need(stream.write(raw)==len(raw),'complete release write');stream.flush();os.fsync(stream.fileno())
        written=os.fstat(stream.fileno());ordinary(written,True)
    # Bounded same-object readback; final allowance pays these writes/checks.
    before=path.lstat();ordinary(before,True)
    need(identity(before)==identity(written) and before.st_size==len(raw),'same just-written release object')
    with path.open('rb') as stream:
        opened=os.fstat(stream.fileno());ordinary(opened,True)
        need(identity(opened)==identity(written),'same release readback handle')
        observed=stream.read(len(raw)+1);after=os.fstat(stream.fileno())
    named=path.lstat();ordinary(named,True)
    need(observed==raw and identity(after)==identity(named)==identity(written),'release exact bytes and identity unchanged')
    return dict(path=key(path),bytes=len(observed),sha256=sha(observed))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',nargs=3,action='append',required=True,metavar=('PATH','BYTES','SHA256'));args=parser.parse_args()
    need(Path.cwd().resolve()==ROOT and Path(sys.executable).resolve()==PYTHON and sys.dont_write_bytecode and not sys._xoptions,'exact fixed preparation interpreter/cwd')
    expected=[str(PYTHON),'-B',str(SELF)]
    for row in args.source:expected+=['--source',*row]
    need(sys.orig_argv==expected,'exact held preparation argv')
    plan_path=HERE/'local-image-probe-plan-1.json';grant_path=HERE/'work/local-image-probe-resource-authorization-1.json'
    receipt_path=HERE/'work/local-image-probe-preparation-1.json';inventory_path=HERE/'work/local-image-probe-runtime-inventory-1.json'
    need(all(not p.exists() for p in (plan_path,grant_path,receipt_path,inventory_path,HERE/'local-image-probe-1')),'fresh fixed preparation and subject paths')
    fixed={}
    for name,(size,digest) in FIXED.items():
        raw,ref=read(HERE/name,2*MIB,dict(bytes=size,sha256=digest));fixed[name]=(strict(raw),ref)
    previous,previous_ref=fixed['real-accounting-repair-plan-2.json']
    old,audit_ref=fixed['work/independent-real-accounting-repair-v3-audit.json']
    outer,outer_ref=fixed['work/independent-real-accounting-repair-v3-audit-outer.json']
    native,native_ref=fixed['work/independent-native-sensor-white-artifact-1-audit.json']
    need(len(previous['source_bindings'])==312 and old['status']=='PASS_SAVED_REAL_ACCOUNTING_REPAIR_V3_OUTCOME_AUDIT' and
        old['subject_complete'] is True and old['actual_final_work']==BASE and old['admission_allowed'] is False and
        old['cpu_accounting_complete'] is False,'exact limited completed baseline with all retained costs')
    need(outer['exit_code']==0 and outer['stderr_bytes']==0 and outer['stdout_bytes']==audit_ref['bytes'] and
        outer['elapsed_wall_seconds']<=old['audit_timing']['wall_seconds']+old['audit_publication_allowance']['wall_seconds'],'previous audit actual final wall binding')
    need(native['status']=='PASS_SAVED_SENSOR_WHITE_ARTIFACT_OUTCOME_AUDIT' and
        [(native['frames'][i]['ordinal'],native['frames'][i]['original_index']) for i in (0,1,3,4)]==[(0,0),(1,13),(3,39),(4,52)],'unchanged exact native pair identities')
    sources=dict(previous['source_bindings'])
    for path,pin in sources.items():read(ROOT/path,2*MIB,pin)
    for _,ref in fixed.values():
        pin={k:ref[k] for k in ('bytes','sha256')};need(sources.setdefault(ref['path'],pin)==pin,'unchanged already-accounted baseline additions')
    fresh={}
    for name,size,digest in args.source:
        need(size.isdecimal() and int(size)>0 and digest==digest.lower(),'canonical held source triple')
        raw,ref=read(ROOT/name,256*KIB,dict(bytes=int(size),sha256=digest));name=ref['path']
        need(name not in fresh and name not in sources,'unique fresh source addition')
        fresh[name]={k:ref[k] for k in ('bytes','sha256')}
    need(all(key(HERE/name) in fresh for name in REQUIRED),'complete fresh source/preregistration/independent review/auditor/preparer package')
    need(sum(v['bytes'] for v in fresh.values())<=LEDGER['fresh_sources_and_reviews'],'complete fresh source/review allocation');sources.update(fresh)
    runtime={};empty={};rows=[];base=PYTHON.parent
    roots=[base/'Lib',base/'DLLs',*[base/'Lib/site-packages'/name for name in PACKAGES]]
    for directory in roots:
        need(directory.is_dir(),'fixed existing runtime directory');count=zero=total=0
        for current,dirs,names in os.walk(directory,followlinks=False):
            dirs[:]=sorted(name for name in dirs if name not in SKIP)
            for name in sorted(names):
                if Path(name).suffix.lower() not in ('.py','.pyd'):continue
                raw,ref=read(Path(current)/name,128*MIB,empty=True);pin={k:ref[k] for k in ('bytes','sha256')}
                namespace=runtime if ref['bytes'] else empty
                need(ref['path'] not in namespace and ref['path'] not in sources,'unique external runtime file')
                namespace[ref['path']]=pin;count+=1;zero+=not ref['bytes'];total+=ref['bytes']
        rows.append(dict(root=str(directory),files=count,empty_files=zero,bytes=total))
    namespaces(sources,runtime,empty)
    # Powered preparation-only metadata tests. No estimator or subject module import.
    controls=[]
    for label,bad_source,bad_runtime,bad_empty in (
        ('zero-project-source',{**sources,'injected-zero-source':dict(bytes=0,sha256=EMPTY)},runtime,empty),
        ('boolean-empty-runtime',sources,runtime,{**empty,'injected-empty':dict(bytes=False,sha256=EMPTY)}),
        ('false-empty-runtime-hash',sources,runtime,{**empty,'injected-empty':dict(bytes=0,sha256='0'*64)})):
        failed=False
        try:namespaces(bad_source,bad_runtime,bad_empty)
        except ValueError:failed=True
        need(failed,'powered preparation namespace fault: '+label);controls.append(dict(id=label,rejected=True))
    namespaces(sources,runtime,empty)
    python_raw,python_ref=read(PYTHON,128*MIB,{k:previous['python_executable'][k] for k in ('bytes','sha256')})
    grant=dict(schema='m193c-local-image-resource-authorization-v1',baseline_audit=audit_ref,baseline_outer=outer_ref,
        retained_work=BASE,previous_limits=OLD_CAPS,new_limits=CAPS,phase_allowance=PHASE,preparation_allowance=PREP,
        subject_allowance=SUBJECT,audit_allowance=AUDIT,scope='ONE_FIXED_LOCAL_IMAGE_PROBE; NO_RETIRED_COST_REFUND; NO_GEOMETRY_ADMISSION')
    need(all(BASE[k]+PHASE[k]<=CAPS[k] for k in BASE) and sum(LEDGER.values())<=MIB,'full conservative phase and preparation allocations')
    grant_raw=encode(grant);grant_ref=dict(path=key(grant_path),bytes=len(grant_raw),sha256=sha(grant_raw))
    command=[str(PYTHON),'-B',str(HERE/'local-image-probe-run.py'),'--plan',str(plan_path),'--sha256','ACTUAL_PLAN_SHA256','--output',str(HERE/'local-image-probe-1')]
    worker_command=command[:-1]+[str(HERE/'local-image-probe-1/worker'),'--worker']
    plan=dict(schema='m193c-local-image-probe-plan-v1',source_bindings=sources,runtime_bindings=runtime,runtime_empty_bindings=empty,
        baseline_audit=audit_ref,baseline_outer=outer_ref,native_audit=native_ref,resource_authorization=grant_ref,
        prior_work={k:BASE[k]+PREP[k] for k in BASE},python_executable=python_ref,commands=dict(parent=command,worker=worker_command))
    plan_raw=encode(plan);need(len(plan_raw)<=LEDGER['plan'] and len(grant_raw)<=LEDGER['authorization'],'exact release envelopes')
    inventory=encode(dict(schema='m193c-local-image-runtime-inventory-v1',roots=rows,positive_files=len(runtime),empty_files=len(empty),
        exclusion_names=sorted(SKIP),suffixes=['.py','.pyd'],scope='Deterministic module-file inventory, no numerical imports. Actual imported files/aliases checked by worker; native dependent DLL closure is not asserted.'))
    need(len(inventory)<=LEDGER['inventory_receipt'],'bounded runtime inventory receipt')
    for path,(expected_identity,owned) in SEEN.items():
        st=Path(path).lstat();ordinary(st,owned);need(identity(st)==expected_identity,'all held sources/evidence/runtime unchanged before release')
    check();sample=dict(cpu_seconds=time.process_time(),wall_seconds=time.monotonic()-START)
    plan_ref=dict(path=key(plan_path),bytes=len(plan_raw),sha256=sha(plan_raw))
    receipt=encode(dict(schema='m193c-local-image-preparation-v1',status='COMPLETE_METADATA_PREPARATION_ONLY',argv=sys.orig_argv,
        source=dict(path=key(SELF),**fresh[key(SELF)]),plan=plan_ref,authorization=grant_ref,
        runtime_inventory=dict(path=key(inventory_path),bytes=len(inventory),sha256=sha(inventory)),
        source_files=len(sources),runtime_files=len(runtime),empty_runtime_files=len(empty),source_addition_bytes=sum(v['bytes'] for v in fresh.values()),
        full_family_reservations=LEDGER,allowance=PREP,sample=sample,publication_allowance=dict(cpu_seconds=.25,wall_seconds=.5),
        complete_process_cpu_accounting=False,external_exit_and_whole_wall_required=True,namespace_controls=controls,
        launch_command=[plan_ref['sha256'] if v=='ACTUAL_PLAN_SHA256' else v for v in command],
        scope='New source/review bytes and release artifacts charged; fixed historical artifacts re-bound but not copied or refunded. No native image payload, estimator, model or subject execution.'))
    need(len(receipt)<=LEDGER['preparation_receipt'],'complete preparation receipt envelope')
    write(grant_path,grant_raw,LEDGER['authorization']);write(inventory_path,inventory,LEDGER['inventory_receipt'])
    write(plan_path,plan_raw,LEDGER['plan']);receipt_ref=write(receipt_path,receipt,LEDGER['preparation_receipt'])
    # Post-publication failure remains a failed preparation even if exclusive files exist.
    need(time.process_time()<=5 and time.monotonic()-START<=10,'complete preparation observed cap')
    print(encode(dict(status='COMPLETE_METADATA_PREPARATION_ONLY',receipt=receipt_ref,plan=plan_ref,sample=sample)).decode(),end='',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
