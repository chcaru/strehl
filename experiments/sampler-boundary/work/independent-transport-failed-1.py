from pathlib import Path
import json,hashlib,time,subprocess,sys,ctypes,io,zipfile,struct,math,collections
INDEX=1
ROOT=Path.cwd()
BASE=ROOT/'experiments/sampler-boundary'
WORK=BASE/'work'
START=time.monotonic();CPU=time.process_time()
READS=[];READ_BYTES=0;ERRORS=[];DETAIL={}
def need(value,label):
    if not value: ERRORS.append(label)
def read(path,ref=None):
    global READ_BYTES
    p=Path(path)
    if not p.is_absolute():p=ROOT/p
    p=p.resolve(strict=True)
    n=p.stat().st_size
    assert p.is_relative_to(ROOT) and n<=128*(1<<20) and READ_BYTES+n<=768*(1<<20)
    b=p.read_bytes()
    actual=dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    READS.append(actual);READ_BYTES+=len(b)
    if ref is not None:need(actual==ref,'exact reference '+str(p))
    assert time.process_time()-CPU<9 and time.monotonic()-START<13
    return b
def get(ref):return read(ref['path'],ref)
rraw=read(WORK/'independent-read-release-1.json')
assert len(rraw)==16124 and hashlib.sha256(rraw).hexdigest()=='fc92179b15531145ecd840373258524fc6bed0235e4b18c7c50690f049d2c60c'
release=json.loads(rraw)
get(release['reader'])
command=release['commands'][INDEX-1]
assert command['command'][0]==sys.executable
assert command['command'][1:5]==['-I','-S','-B',str(BASE/'independent-saved-read.py')]
assert command['command'][5]==command['mode'] and command['command'][-1]==command['output']
need(not Path(command['output']).exists(),'fresh independent helper output')
stages_to_read={1:['baseline-build','baseline-test'],2:[],3:['repaired-build','repaired-test','repaired-regression'],4:[]}[INDEX]
staged={}
for name in stages_to_read:
    refs=release['stages'][name]
    raws={k:get(v) for k,v in refs.items()}
    values={k:json.loads(v) for k,v in raws.items() if k not in ('log','exit','stderr')}
    result,tail,outer,advert,prior,child=(values[k] for k in ('result','tail','outer','stdout','release','child'))
    need(raws['exit']==b'0\n' and outer['exit_code']==0 and outer['timeout_terminated'] is False,name+' actual external0')
    need(result['status']=='COMPLETE_STAGE_UNVERIFIED' and result['error'] is None and not result['finalization_errors'],name+' completed operational status')
    need(result['release']==refs['release'],name+' exact release')
    need(outer['command']==result['invocation']==[refs['release']['sha256'] if x=='ACTUAL_RELEASE_SHA256' else x for x in prior['command']],name+' exact invocation')
    need(advert['result']==refs['result'] and advert['tail']==refs['tail'] and tail['result']==refs['result'],name+' result/tail advertisement')
    for k in ('stdout','stderr','exit'):need(outer[k]==refs[k],name+' outer '+k)
    need(outer['stdout_bytes']==len(raws['stdout']) and outer['stderr_bytes']==len(raws['stderr']),name+' stream extents')
    need(result['children']==[refs['child']],name+' child receipt association')
    need(tail['cpu_accounting_complete'] is True and tail['live_child_cpu_seconds']==0 and
         result['work']['cpu_accounting_complete'] is True,name+' complete terminal CPU')
    capcpu,capwall=(600,300) if name.endswith('build') else (30,60)
    need(tail['actual_parent_cpu_sample']+tail['completed_child_cpu_seconds']+2<=capcpu and
         tail['whole_wall_sample']+3<=capwall and outer['elapsed_wall_seconds']<=capwall and
         outer['elapsed_wall_seconds']<=tail['whole_wall_sample']+3,name+' sampled CPU plus tail/actual outer wall')
    need(tail['final_external_allowance']==dict(cpu_seconds=2.0,wall_seconds=3.0),name+' reserved final tail')
    if name.endswith('build'):
        need(b'Compiling strehl-core' in raws['log'],name+' actual fresh compilation')
        messages=[json.loads(line) for line in raws['log'].splitlines() if line.startswith(b'{')]
        finished=[v for v in messages if v.get('reason')=='build-finished']
        artifacts=[v for v in messages if v.get('reason')=='compiler-artifact' and v.get('executable')]
        need(len(finished)==1 and finished[0]['success'] is True and len(artifacts)==2,name+' actual two build artifacts')
        for key in ['executable','unit_executable']:
            copy=result['artifacts'][key];origin=result['artifacts'][key+'_compiled_original']
            a,b=get(copy),get(origin)
            need(a==b,name+' exact retained '+key)
        for v in artifacts:
            need(v['fresh'] is False and v['profile']['test'] is True and v['features']==[],name+' non-fresh test artifact')
            need(v==result['artifacts']['compiler_messages'][v['target']['name']],name+' retained Cargo message')
        DETAIL[name+'_compiler_artifacts']=artifacts
    else:
        artifactkey='test_observation' if name.endswith('test') else 'regression_observation'
        need(result['artifacts'][artifactkey]==refs['observation'],name+' detached observation association')
        if name=='baseline-test':
            need(b'fixed sampler boundary contract:' in raws['log'] and
                 b'test result: FAILED. 0 passed; 1 failed;' in raws['log'],name+' actual negative harness assertion')
        elif name=='repaired-test':
            need(b'test result: ok. 1 passed; 0 failed;' in raws['log'],name+' actual positive harness assertion')
        else:
            DETAIL['regression_raw_log']=raws['log'].decode()
    DETAIL[name]=dict(child=child,tail=tail,outer=outer,work=result['work'],
                     disposition=result.get('test_disposition'),observation=values.get('observation'),
                     environment=result.get('environment'),artifacts=result['artifacts'],
                     operations=result['operations'],source_count=len(prior['source_bindings']),
                     source_align=prior['source_bindings']['crates/strehl-core/src/align.rs'])
    staged[name]=(prior,result)
if INDEX==1:
    need(staged['baseline-build'][0]['source_bindings']==staged['baseline-test'][0]['source_bindings'],'same original build/test source map')
    need(staged['baseline-test'][0]['executable']==staged['baseline-build'][1]['artifacts']['executable'],'actual baseline test binary source association')
if INDEX==3:
    sources=staged['repaired-build'][0]['source_bindings']
    need(all(x[0]['source_bindings']==sources for x in staged.values()),'same repaired build/test/regression sources')
    need(staged['repaired-test'][0]['executable']==staged['repaired-build'][1]['artifacts']['executable'],'repaired public actual executable')
    need(staged['repaired-regression'][0]['executable']==staged['repaired-build'][1]['artifacts']['unit_executable'],'repaired regression actual executable')
if INDEX==4:
    pass
logref=release['stages'][command['variant']+'-test']['log']
lograw=get(logref)
need(str((ROOT/logref['path']).resolve())==command['command'][6],'helper exact released log path')
assert not ERRORS,ERRORS
prefix=WORK/('independent-read-slice-'+str(INDEX))
paths={k:Path(str(prefix)+'-'+suffix) for k,suffix in [('stdout','stdout.bin'),('stderr','stderr.bin'),('exit','exit.txt'),('ledger','ledger.json')]}
assert all(not p.exists() for p in paths.values())
childstart=time.monotonic()
p=subprocess.Popen(command['command'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
out,err=p.communicate(timeout=max(.1,13-(time.monotonic()-START)))
code=p.returncode
childwall=time.monotonic()-childstart
class FT(ctypes.Structure):_fields_=[('low',ctypes.c_ulong),('high',ctypes.c_ulong)]
created,ended,kernel,user=(FT() for _ in range(4))
gettime=ctypes.WinDLL('kernel32',use_last_error=True).GetProcessTimes
gettime.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(FT)]*4
gettime.restype=ctypes.c_int
assert gettime(int(p._handle),ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user))
seconds=lambda v:((v.high<<32)|v.low)/10000000
childcpu=seconds(kernel)+seconds(user)
need(code==command['expected_exit_code'],'exact independent reader exit')
assert len(out)<=8192 and len(err)<=32768
for key,b in [('stdout',out),('stderr',err),('exit',(str(code)+'\n').encode())]:
    with paths[key].open('xb') as f:f.write(b)
helper=json.loads(read(command['output'])) if Path(command['output']).exists() else None
if helper:
    need(helper['source']['sha256']==release['reader']['sha256'],'helper actual source hash')
    need(helper['reads'][-1]['sha256']==logref['sha256'] and helper['reads'][-1]['bytes']==logref['bytes'],'helper actual log bytes')
    need(helper['interpretation_complete'] is True and not helper['failures'],'independent saved-bit predicates')
    READ_BYTES+=helper['actual_read_bytes']
totalcpu=time.process_time()-CPU+childcpu
wholewall=time.monotonic()-START
need(totalcpu+1<=10 and wholewall+2<=15,'combined audit slice plus publication reserve')
ledger=dict(schema='sampler-independent-audit-slice-v1',slice=INDEX,release_sha256=hashlib.sha256(rraw).hexdigest(),
    actual_command=command['command'],actual_exit_code=code,helper_whole_wall_seconds=childwall,
    helper_complete_process_cpu_seconds=childcpu,metadata_parent_cpu_sample=time.process_time()-CPU,
    combined_cpu_sample=totalcpu,whole_slice_wall_sample=wholewall,final_allowance=dict(cpu_seconds=1,wall_seconds=2),
    reads=READS,helper_reads=[] if helper is None else helper['reads'],charged_read_bytes=READ_BYTES,
    findings=DETAIL,helper_review=None if helper is None else helper['review'],failures=ERRORS)
b=(json.dumps(ledger,indent=2,allow_nan=False)+'\n').encode()
assert len(b)<8<<20
with paths['ledger'].open('xb') as f:f.write(b)
assert time.process_time()-CPU+childcpu<=10 and time.monotonic()-START<=15
print(json.dumps(dict(slice=INDEX,actual_exit_code=code,combined_cpu_sample=totalcpu,whole_slice_wall_sample=wholewall,
    charged_read_bytes=READ_BYTES,ledger=dict(path=str(paths['ledger']),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()),
    failures=ERRORS,helper_review=None if helper is None else helper['review']),allow_nan=False))
raise SystemExit(0 if not ERRORS else 1)
