"""Fixed independent recovery metadata controls. No child or image operations."""
import time
START=time.perf_counter();CPU=time.process_time()
import argparse,ast,copy,hashlib,json,os,stat,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;SELF=Path(__file__).resolve()
AUTHORITY=HERE/'recovery-authority.py'
AUTHORITY_SHA='45df35ca1ad6b47b3cea305f7f8519f76dee40d5625b7a647622ac5c822b1e3b'
CONTROLLER_SHA='442226bd08b128f8bb97460fab6f8ab6280fd0950d1912313b87d583b7a33940'
FREEZE_SHA='f3778c80df31b6cde6e253797cf497ca2cdfced85f8507ae126ba03ce8563708'
MIB=1<<20;READ=0;WRITTEN=0;OUTPUT=None;ROWS=[];OWN=None;SOURCES=[]
IDS=('ordinary-positive','verbatim-to-ordinary','ordinary-to-verbatim','different-manifest-same-bytes',
'different-output-same-bytes','wrong-extent','wrong-digest','boolean-extent','float-extent','zero-extent',
'extra-ref-key','nonstring-path','device-path','unc-path','verbatim-unc','alternate-stream','nul-path',
'dot-components','trailing-components','empty-component','outside-repository','drive-relative',
'malformed-verbatim-drive','restored-associations','saved-negative-parent-positive','historical-parent-complete',
'historical-failure-changed','child-nonzero','child-incomplete-job','child-command-changed','child-index-changed',
'restored-saved-parent','admission-positive','admission-status-changed','admission-old-parent-complete',
'admission-index-changed','producer-map-changed','execution-map-changed','archive-and-proof-associations','restored-admission')

def need(v,label):
    if not v:raise ValueError(label)

def encoded(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def shape_sha(v):return type(v) is str and len(v)==64 and all(x in '0123456789abcdef' for x in v)
def check(cpu=5,wall=10):need(time.process_time()-CPU<=cpu and time.perf_counter()-START<=wall,'fixed controls work allowance')
def ident(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink,getattr(s,'st_file_attributes',0))
def full(s):return ident(s)+(s.st_ctime_ns,)

def read(path,cap,expected=None,empty=False):
    global READ
    check();path=Path(path)
    for q in (path,*path.parents):
        v=q.lstat();need(not stat.S_ISLNK(v.st_mode) and not getattr(v,'st_file_attributes',0)&0x400,'plain control read ancestry')
    before=path.lstat();need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and
        (0 if empty else 1)<=before.st_size<=cap,'bounded control read extent')
    READ+=before.st_size+1;need(READ<=4*MIB,'aggregate controls read allowance')
    with path.open('rb') as f:
        a=os.fstat(f.fileno());need(ident(before)==ident(a),'control shared opened identity')
        raw=f.read(before.st_size+1);z=os.fstat(f.fileno())
    after=path.lstat();need(full(before)==full(after) and full(a)==full(z) and len(raw)==before.st_size,'stable control same-buffer read')
    if expected is not None:need(len(raw)==expected['bytes'] and sha(raw)==expected['sha256'],'literal control input bytes')
    return raw

def ref(path,raw):return dict(path=str(Path(path).resolve()),bytes=len(raw),sha256=sha(raw))

def write(path,raw,cap):
    global WRITTEN
    check();need(len(raw)<=cap,'fixed control output extent');WRITTEN+=len(raw)
    need(WRITTEN<=2*MIB,'aggregate controls write allowance')
    with Path(path).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    need(read(path,cap,empty=not raw)==raw,'actual control output readback')
    return ref(path,raw)

def error(e):
    v=dict(type=type(e).__name__,message=str(e)[:512])
    while len(encoded(v))>1024:v['message']=v['message'][:len(v['message'])//2]
    return v

def progress():
    if OUTPUT is None:return
    # Fixed <=8KiB compact progress, not40 repeated full-row publications.
    value=dict(schema='common-tiff-dimensions-recovery-controls-progress-v1',
        rows=[dict(id=r['id'],passed=r['passed']) for r in ROWS],source=OWN)
    stage=OUTPUT/'progress.stage.json';write(stage,encoded(value),8192);os.replace(stage,OUTPUT/'progress.json')

def group(ident,body):
    check();need(ident==IDS[len(ROWS)],'fixed ordered40 control groups')
    try:
        details=body();row=dict(id=ident,passed=True,details=details)
        need(len(encoded(row))<=2048,'fixed control row extent')
    except (ValueError,TypeError,KeyError,OSError,AssertionError) as e:
        row=dict(id=ident,passed=False,error=error(e))
    ROWS.append(row);progress()

def expect(call,reason=None):
    if reason is None:
        result=call();need(result is True,'expected literal boolean admission')
        return dict(outcome='ACCEPTED',visited=True)
    try:v=call()
    except ValueError as e:
        need(str(e)==reason,'exact reached rejection reason: '+reason)
        return dict(outcome='REFUSED',reason=reason,visited=True)
    need(v is False and reason=='association returned false','destroyer must reject at intended predicate')
    return dict(outcome='REFUSED',reason=reason,visited=True)

def load_authority():
    raw=read(AUTHORITY,128*1024);need(sha(raw)==AUTHORITY_SHA,'held recovery authority source')
    SOURCES.append(ref(AUTHORITY,raw));m=types.ModuleType('independent_recovery_control_subject');m.__file__=str(AUTHORITY)
    exec(compile(raw,str(AUTHORITY),'exec'),m.__dict__)
    return m

def inputs(a):
    # Metadata only. These held roots are separately authenticated source authority;
    # no TIFF, executable, source archive or numerical array is opened here.
    values={};raws={}
    for key in ('producer_freeze','prepare_child','prepare_log','index','original_controller','prepare_release'):
        pin=a.HISTORY[key];raw=read(ROOT/pin['path'],512*1024,pin);raws[key]=raw
        if key!='original_controller':values[key]=a.strict(raw)
    need(sha(raws['producer_freeze'])==FREEZE_SHA and sha(raws['original_controller'])==CONTROLLER_SHA,'independent historical source pins')
    for key in ('result','tail','outer','exit'):
        pin=a.HISTORY['prepare'][key];raw=read(ROOT/pin['path'],512*1024,pin);raws[key]=raw
        if key!='exit':values[key]=a.strict(raw)
    return values,raws

def path_controls(a,controller_raw):
    data=b'independent-recovery-twin\n';left=OUTPUT/'path-a.bin';right=OUTPUT/'path-b.bin'
    ra=write(left,data,64);rb=write(right,data,64)
    need(left.resolve()!=right.resolve() and ra['bytes']==rb['bytes'] and ra['sha256']==rb['sha256'],'actual distinct same-content controls')
    producer=types.SimpleNamespace();fn,proof=a.make_fixture_reader(producer,controller_raw)
    # Compile only the exact source conjunction in the actual modified reader.
    # Its global legacy_same_ref is the production observed wrapper returned by
    # make_fixture_reader. No full fixture read or generator is called.
    original=next(n for n in ast.parse(controller_raw).body if isinstance(n,ast.FunctionDef) and n.name=='fixture_read')
    call=next(n for n in ast.walk(original) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need'
        and len(n.args)==2 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='held legacy manifest/output association')
    expression=copy.deepcopy(call.args[0]);replaced=[]
    for n in ast.walk(expression):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='same_ref':
            role=n.args[0].slice.value;need(role in ('manifest','output'),'literal production callsite role')
            replaced.append(role);n.func=ast.Name(id='legacy_same_ref',ctx=ast.Load())
    need(replaced==['manifest','output'] and proof['replaced_calls']==2 and proof['original_ast_sha256']==proof['reverse_ast_sha256'],'exact two production callsites')
    need(sha(ast.dump(original,include_attributes=False).encode())==proof['original_ast_sha256']==
         '6fdf3945d43620706246caae9e962209ae3386e9e2b85315baed018d102c90c7','independently pinned original callsite AST')
    code=compile(ast.fix_missing_locations(ast.Expression(expression)),str(HERE/'run-stage.py'),'eval')
    namespace=fn.__globals__;baseline=dict(schema='common-tiff-stack-result-v1',status='COMPLETE',subject_complete=True,manifest=ra,output=ra)
    legacy=dict(manifest=ra,output=ra)
    def invoke(old,expected,reason=None,want=('manifest','output')):
        proof['visits'].clear();seen=[]
        original_observer=namespace['legacy_same_ref']
        def observed(x,y):
            seen.append(('manifest','output')[len(seen)]);return original_observer(x,y)
        namespace['legacy_same_ref']=observed;namespace['old']=old;namespace['legacy']=expected
        try:out=expect(lambda:eval(code,namespace),reason)
        finally:namespace['legacy_same_ref']=original_observer
        need(tuple(seen)==want,'actual ordered production association visitation')
        out['calls']=seen;return out
    def changed(key,value,reason,want=('manifest',)):
        old=copy.deepcopy(baseline);old['manifest'][key]=value;return invoke(old,legacy,reason,want)
    ordinary=ra['path'];verbatim='\\\\?\\'+ordinary
    group(IDS[0],lambda:invoke(copy.deepcopy(baseline),copy.deepcopy(legacy)))
    group(IDS[1],lambda:invoke({**baseline,'manifest':{**ra,'path':verbatim},'output':{**ra,'path':verbatim}},legacy))
    group(IDS[2],lambda:invoke(baseline,{k:{**ra,'path':verbatim} for k in ('manifest','output')}))
    group(IDS[3],lambda:invoke({**baseline,'manifest':rb},legacy,'association returned false',('manifest',)))
    group(IDS[4],lambda:invoke({**baseline,'output':rb},legacy,'association returned false'))
    group(IDS[5],lambda:changed('bytes',ra['bytes']+1,'association returned false'))
    group(IDS[6],lambda:changed('sha256',('0' if ra['sha256'][0]!='0' else '1')+ra['sha256'][1:],'association returned false'))
    group(IDS[7],lambda:changed('bytes',True,'association returned false'))
    group(IDS[8],lambda:changed('bytes',float(ra['bytes']),'association returned false'))
    group(IDS[9],lambda:changed('bytes',0,'association returned false'))
    group(IDS[10],lambda:invoke({**baseline,'manifest':{**ra,'extra':1}},legacy,'association returned false',('manifest',)))
    group(IDS[11],lambda:changed('path',1,'association returned false'))
    group(IDS[12],lambda:changed('path',r'\\.\C:\control','no device or UNC association'))
    group(IDS[13],lambda:changed('path',r'\\server\share\control','no device or UNC association'))
    group(IDS[14],lambda:changed('path',r'\\?\UNC\server\share\control','supported verbatim local-drive path'))
    group(IDS[15],lambda:changed('path',ordinary+':stream','canonical association components'))
    group(IDS[16],lambda:changed('path',ordinary+'\0','typed association path'))
    group(IDS[17],lambda:[changed('path',verbatim.rsplit('\\',1)[0]+'\\'+c+'\\path-a.bin','canonical association components') for c in ('.','..')])
    group(IDS[18],lambda:[changed('path',verbatim+s,'canonical association components') for s in ('.',' ')])
    group(IDS[19],lambda:changed('path',verbatim.rsplit('\\',1)[0]+'\\\\path-a.bin','canonical association components'))
    group(IDS[20],lambda:changed('path',str(ROOT.parent/'independent-outside.bin'),'repository association containment'))
    group(IDS[21],lambda:changed('path',ordinary[:2]+'relative.bin','absolute local-drive association'))
    group(IDS[22],lambda:changed('path',r'\\?\1:\control','supported verbatim local-drive path'))
    def restored():
        v=invoke(baseline,legacy);need(read(left,64)==read(right,64)==data,'both private originals restored');return v
    group(IDS[23],restored)
    return proof

def saved_controls(a,v,r):
    base=[v['result'],v['prepare_child'],v['prepare_log'],v['tail'],v['outer'],r['exit'],a.HISTORY['index'],
          v['prepare_release']['children'][0]['command']]
    def run(change=None,reason=None):
        operands=copy.deepcopy(base)
        if change:change(operands)
        def admitted():
            answer=a.admit_saved_prepare(*operands)
            j=operands[1]['job_accounting']
            need(type(j['total_user_100ns']) is int and type(j['total_kernel_100ns']) is int and
                 j['total_user_100ns']>=0 and j['total_kernel_100ns']>=0,'independent integer child CPU operands')
            expected=dict(original_parent_status='REFUSED',original_parent_complete=False,generator_child_exit_code=0,
                generator_child_cpu_seconds=(j['total_user_100ns']+j['total_kernel_100ns'])/1e7,saved_prefix_eligible=True)
            need(type(answer) is dict and encoded(answer)==encoded(expected),'exact saved-prefix-only admission result')
            return True
        return expect(admitted,reason)
    group(IDS[24],lambda:run())
    group(IDS[25],lambda:run(lambda x:x[0].update(status='COMPLETE_STAGE_UNVERIFIED'),'exact refused preparation parent'))
    group(IDS[26],lambda:run(lambda x:x[0]['error'].update(sha256='0'*64),'exact refused preparation parent'))
    group(IDS[27],lambda:run(lambda x:x[1].update(exit_code=1),'clean successful saved generator child'))
    group(IDS[28],lambda:run(lambda x:x[1]['job_accounting'].update(active_processes=1),'clean successful saved generator child'))
    group(IDS[29],lambda:run(lambda x:x[1]['command'].__setitem__(-1,'0'*64),'exact original generator command'))
    group(IDS[30],lambda:run(lambda x:x[2]['index'].update(sha256='0'*64),'saved generator advertisement'))
    group(IDS[31],lambda:run())

def admission_controls(a,v,proof):
    producer=v['producer_freeze']['source_bindings'];current=copy.deepcopy(producer)
    # Independent metadata-only extension fixture, not an assertion of executed
    # source bytes. Each required new role is a positive closed declaration.
    for name in a.EXTRAS:current[(HERE/name).relative_to(ROOT).as_posix()]=dict(bytes=17,sha256=sha(b'private-map-entry'))
    expected=[a.HISTORY['index'],*v['index']['generated_files']]
    # Exact historical operands are metadata links; no image contents are read.
    lr=v['index']['legacy'];raw=read(ROOT/lr['report']['path'],64*1024,lr['report']);old=a.strict(raw)
    fixture_proof=dict(scope=proof['scope'],replaced_calls=2,original_ast_sha256=proof['original_ast_sha256'],reverse_ast_sha256=proof['reverse_ast_sha256'],
        visits=[dict(left=old[k],right=lr[k],matched=True) for k in ('manifest','output')])
    tiny=ref(OUTPUT/'path-a.bin',b'independent-recovery-twin\n')
    controls={k:tiny.copy() for k in ('result','outer','stdout','stderr','exit')}
    value=dict(schema='common-tiff-dimensions-saved-fixture-admission-v1',status='SAVED_FIXTURES_ADMITTED',old_prepare_status='REFUSED',subject_complete=False,
        producer_freeze=a.HISTORY['producer_freeze'],producer_source_map_sha256=sha(encoded(producer)),execution_source_map_sha256=sha(encoded(current)),
        compiled_source_closure=dict(files=118,canonical_sha256='ee02f4b41cfc5cc5c1d501c72d9980f2131fba9b891e6b9aca9412e119ff72a8'),
        build=a.HISTORY['build'],failed_prepare=a.HISTORY['prepare'],generator_child=a.HISTORY['prepare_child'],generator_stdout=a.HISTORY['prepare_log'],
        index=a.HISTORY['index'],files=expected,file_bytes=16025258,fixture_read_proof=fixture_proof,controls=controls,scope='private metadata predicate operand only')
    def run(change=None,reason=None):
        candidate=copy.deepcopy(value)
        if change:change(candidate)
        return expect(lambda:a.admission_association(candidate,a.HISTORY['index'],a.HISTORY['producer_freeze'],producer,current,expected),reason)
    group(IDS[32],lambda:run())
    group(IDS[33],lambda:run(lambda x:x.update(status='COMPLETE_STAGE_UNVERIFIED'),'genuine saved-fixture admission disposition'))
    group(IDS[34],lambda:run(lambda x:x.update(old_prepare_status='COMPLETE_STAGE_UNVERIFIED'),'genuine saved-fixture admission disposition'))
    group(IDS[35],lambda:run(lambda x:x['index'].update(sha256='0'*64),'exact saved59 fixture identity population'))
    group(IDS[36],lambda:run(lambda x:x.update(producer_source_map_sha256='0'*64),'original and execution source provenance'))
    group(IDS[37],lambda:run(lambda x:x.update(execution_source_map_sha256='0'*64),'original and execution source provenance'))
    def proof_faults():
        rows=[run(lambda x:x['producer_freeze'].update(sha256='0'*64),'original and execution source provenance')]
        rows.append(run(lambda x:x['fixture_read_proof']['visits'].reverse(),'actual ordered two-callsite fixture proof'))
        rows.append(run(lambda x:x['fixture_read_proof']['visits'].__setitem__(1,copy.deepcopy(x['fixture_read_proof']['visits'][0])),'actual ordered two-callsite fixture proof'))
        rows.append(run(lambda x:x['fixture_read_proof'].update(original_ast_sha256='0'*64,reverse_ast_sha256='0'*64),'actual ordered two-callsite fixture proof'))
        return rows
    group(IDS[38],proof_faults)
    group(IDS[39],lambda:run())
    return dict(original_map_entries=len(producer),private_current_map_entries=len(current),fixture_refs=len(expected),scope='metadata declarations; no new-source/payload admission')

def main():
    global OUTPUT,OWN,WRITTEN
    parser=argparse.ArgumentParser();parser.add_argument('--source-sha256',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output).resolve()
    need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.orig_argv==
        [sys.executable,'-I','-S','-B',str(SELF),'--source-sha256',args.source_sha256,'--output',str(out)],'exact isolated controls invocation')
    raw=read(SELF,128*1024);need(shape_sha(args.source_sha256) and sha(raw)==args.source_sha256,'actual controls source identity');OWN=ref(SELF,raw)
    need(out==HERE/'work/recovery-controls-1' and not out.exists() and out.parent.is_dir(),'fresh fixed controls output')
    out.mkdir();OUTPUT=out;proof=None;metadata=None;failure=None
    try:
        a=load_authority();v,r=inputs(a);proof=path_controls(a,r['original_controller']);saved_controls(a,v,r);metadata=admission_controls(a,v,proof)
        need(len(ROWS)==40 and [x['id'] for x in ROWS]==list(IDS),'complete fixed40 controls')
    except (ValueError,TypeError,KeyError,OSError,AssertionError) as e:failure=error(e)
    complete=failure is None and len(ROWS)==40 and all(x['passed'] for x in ROWS)
    answer=dict(schema='common-tiff-dimensions-recovery-controls-v1',status='PASS_FIXED_RECOVERY_METADATA_CONTROLS' if complete else 'REFUSED',
        controls_complete=complete,source=OWN,invocation=sys.orig_argv,authority_sources=SOURCES,groups=40,completed_groups=len(ROWS),rows=ROWS,error=failure,
        fixture_reader_ast={k:v for k,v in (proof or {}).items() if k!='visits'},admission_metadata=metadata,
        scope='private path and saved-metadata controls only; no fixture admission, generator, child or scientific execution',
        own_work=dict(cpu_seconds=time.process_time()-CPU,wall_seconds=time.perf_counter()-START),
        publication_allowance=dict(cpu_seconds=1,wall_seconds=2),charged_read_bytes_before_final=READ,charged_write_bytes_before_final=WRITTEN,
        full_reserved_allowance=dict(cpu_seconds=5,wall_seconds=10,read_bytes=4*MIB,write_bytes=2*MIB))
    if answer['own_work']['cpu_seconds']+1>5 or answer['own_work']['wall_seconds']+2>10:
        answer.update(status='REFUSED',controls_complete=False,error=dict(type='ResourceRefusal',message='work including publication reserve'))
    need(read(SELF,128*1024)==raw and sha(read(AUTHORITY,128*1024))==AUTHORITY_SHA,'controls and actual predicate source restored')
    output=encoded(answer);need(len(output)<=128*1024,'whole control report cap')
    write(out/'result.json',output,128*1024);WRITTEN+=len(output);need(WRITTEN<=2*MIB,'control stdout write charge')
    need(sys.stdout.buffer.write(output)==len(output),'whole control stdout');sys.stdout.buffer.flush();check()
    return 0 if answer['controls_complete'] else 1

if __name__=='__main__':raise SystemExit(main())
