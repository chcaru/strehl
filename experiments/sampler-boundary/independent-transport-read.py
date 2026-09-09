from pathlib import Path
import json,hashlib,time,subprocess,sys,ctypes,io,zipfile,struct,math,collections,os,re
INDEX=int(sys.argv[1])
assert INDEX in (1,2,3,4)
ROOT=Path.cwd()
BASE=ROOT/'experiments/sampler-boundary'
WORK=BASE/'work'
START=time.monotonic();CPU=time.process_time()
READS=[];READ_BYTES=0;PRIOR_CHARGE=513*(1<<20);ERRORS=[];DETAIL={}
def need(value,label):
    if not value: ERRORS.append(label)
def same_owned_ref(a,b,allow_empty=False):
    # Held prepare-release.same_owned_ref location+extent+hash semantics.
    # Only declared empty raw stream roles may use the zero-extent extension.
    def owned_name(v):
        minimum=0 if allow_empty else 1
        assert type(v) is dict and set(v)=={"path","bytes","sha256"}
        assert type(v["path"]) is str and type(v["bytes"]) is int and v["bytes"]>=minimum
        assert type(v["sha256"]) is str and re.fullmatch("[0-9a-f]{64}",v["sha256"])
        text=str(Path(os.path.abspath(ROOT/v["path"])))
        if re.match(r"^\\\\\?\\[A-Za-z]:\\",text):text=text[4:]
        p=Path(text)
        assert p.is_relative_to(ROOT)
        return p
    return owned_name(a)==owned_name(b) and a["bytes"]==b["bytes"] and a["sha256"]==b["sha256"]
def read(path,ref=None,cap=128*(1<<20)):
    global READ_BYTES
    p=Path(path)
    if not p.is_absolute():p=ROOT/p
    p=p.resolve(strict=True)
    n=p.stat().st_size
    assert p.is_relative_to(ROOT) and n<=cap and PRIOR_CHARGE+READ_BYTES+n<=768*(1<<20)
    b=p.read_bytes()
    actual=dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    READS.append(actual);READ_BYTES+=len(b)
    if ref is not None:need(same_owned_ref(actual,ref,allow_empty=ref['bytes']==0),'exact reference '+str(p))
    assert time.process_time()-CPU<9 and time.monotonic()-START<13
    return b
def get(ref,cap=128*(1<<20)):return read(ref['path'],ref,cap)
read(__file__)
for previous in range(1,INDEX):
    prior_ledger=json.loads(read(WORK/('independent-read-slice-'+str(previous)+'-ledger.json')))
    assert prior_ledger['slice']==previous and not prior_ledger['failures']
    PRIOR_CHARGE+=prior_ledger['charged_read_bytes']
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
    need(same_owned_ref(result['release'],refs['release']),name+' exact release')
    need(outer['command']==result['invocation']==[refs['release']['sha256'] if x=='ACTUAL_RELEASE_SHA256' else x for x in prior['command']],name+' exact invocation')
    need(same_owned_ref(advert['result'],refs['result']) and same_owned_ref(advert['tail'],refs['tail']) and same_owned_ref(tail['result'],refs['result']),name+' result/tail advertisement')
    for k in ('stdout','stderr','exit'):need(same_owned_ref(outer[k],refs[k],allow_empty=k=='stderr'),name+' outer '+k)
    need(outer['stdout_bytes']==len(raws['stdout']) and outer['stderr_bytes']==len(raws['stderr']),name+' stream extents')
    expected_exit=101 if name=="baseline-test" else 0
    need(child["command"]==prior["children"][0]["command"] and
         child["exit_code"]==expected_exit==prior["children"][0]["expected_exit_code"],name+" actual child command/exit")
    need(child["terminal_job_accounting"] is True and child["job_accounting"]["active_processes"]==0,
         name+" terminal owned Job zero")
    need(child["error"] is None and not child["cleanup_errors"] and child["direct_exit_observed"] is True
         and child["pipe_eof_observed"] is True and child["post_exit_drain"]["completed"] is True,
         name+" direct exit/EOF/drain without process error")
    need(child["termination"]["attempted"] is False,name+" no emergency termination")
    need(child["job_memory"]["peak_job_memory_used_bytes"]<=(3*(1<<30) if name.endswith("build") else 512*(1<<20)),
         name+" owned committed memory cap")
    need(same_owned_ref(child["log"],refs["log"]),name+" actual child log association")
    if name.endswith("build"):
        cleanup=child["compile_cleanup"]
        need(cleanup["policy"]=="AFTER_DIRECT_ZERO_AND_PIPE_EOF" and cleanup["completed"] is True
             and cleanup["error"] is None and cleanup["pid_query_error"] is None
             and cleanup["after_accounting"]["active_processes"]==0 and cleanup["wait_seconds"]<=5,
             name+" bounded compile-only owned cleanup")
    else:
        need("compile_cleanup" not in child,name+" strict test cleanup policy")
    need(len(result['children'])==1 and same_owned_ref(result['children'][0],refs['child']),name+' child receipt association')
    need(tail['cpu_accounting_complete'] is True and tail['live_child_cpu_seconds']==0 and
         result['work']['cpu_accounting_complete'] is True,name+' complete terminal CPU')
    accounting=child["job_accounting"]
    cpu_fields=("total_user_100ns","total_kernel_100ns","total_cpu_100ns")
    need(all(type(accounting.get(k)) is int and accounting[k]>=0 for k in cpu_fields),
         name+" typed nonnegative whole Job CPU")
    need(accounting["total_cpu_100ns"]==accounting["total_user_100ns"]+accounting["total_kernel_100ns"] and
         tail["completed_child_cpu_seconds"]==accounting["total_cpu_100ns"]/1e7,
         name+" terminal child CPU equals tail operand")
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
            a,b=get(copy,32*(1<<20)),get(origin,32*(1<<20))
            need(a==b,name+' exact retained '+key)
        for v in artifacts:
            need(v['fresh'] is False and v['profile']['test'] is True and v['features']==[],name+' non-fresh test artifact')
            need(v==result['artifacts']['compiler_messages'][v['target']['name']],name+' retained Cargo message')
        DETAIL[name+'_compiler_artifacts']=artifacts
    else:
        artifactkey='test_observation' if name.endswith('test') else 'regression_observation'
        need(same_owned_ref(result['artifacts'][artifactkey],refs['observation']),name+' detached observation association')
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
    need(same_owned_ref(staged['baseline-test'][0]['executable'],staged['baseline-build'][1]['artifacts']['executable']),'actual baseline test binary source association')
if INDEX==3:
    sources=staged['repaired-build'][0]['source_bindings']
    need(all(x[0]['source_bindings']==sources for x in staged.values()),'same repaired build/test/regression sources')
    need(same_owned_ref(staged['repaired-test'][0]['executable'],staged['repaired-build'][1]['artifacts']['executable']),'repaired public actual executable')
    need(same_owned_ref(staged['repaired-regression'][0]['executable'],staged['repaired-build'][1]['artifacts']['unit_executable']),'repaired regression actual executable')
if INDEX==4:
    archives={name:get(ref) for name,ref in release["archives"].items()}
    before=json.loads(get(release["stages"]["baseline-build"]["release"]))["source_bindings"]
    after=json.loads(get(release["stages"]["repaired-build"]["release"]))["source_bindings"]
    need(set(before)==set(after),"same source-map keyset")
    changed=[k for k in before if before[k]!=after[k]]
    need(changed==["crates/strehl-core/src/align.rs"],"sole reviewed align.rs source delta")
    compiled={}
    for name in ["baseline-source-1.zip","repaired-source-1.zip"]:
        with zipfile.ZipFile(io.BytesIO(archives[name])) as z:
            members=z.infolist()
            need(len(members)<=512 and sum(m.file_size for m in members)<=16<<20,"bounded source archive")
            need(len({m.filename for m in members})==len(members),"unique archive members")
            for m in members:
                need(m.filename in before and not m.is_dir() and m.file_size<=4<<20,"declared source member")
                b=z.read(m)
                READ_BYTES+=len(b)
                assert PRIOR_CHARGE+READ_BYTES<=768*(1<<20)
                compiled[m.filename]=b
                expected=(before if name=="baseline-source-1.zip" else after)[m.filename]
                need(len(b)==expected["bytes"] and hashlib.sha256(b).hexdigest()==expected["sha256"],"archived source "+m.filename)
        if name=="baseline-source-1.zip":
            need(set(compiled)==set(before),"complete original archived source map")
    need(set(compiled)==set(after),"complete repaired source map by declared delta")
    current=[]
    for path,binding in after.items():
        raw=get(dict(path=path,**binding))
        need(raw==compiled[path],"actual current source equals repaired archive "+path)
        current.append(path)
    for label in ["baseline","repaired"]:
        freeze=json.loads(archives[label+"-source-freeze-1.json"])
        need(freeze["source_bindings"]==(before if label=="baseline" else after),label+" freeze associations")
    braw=get(release["stages"]["baseline-test"]["log"])
    araw=get(release["stages"]["repaired-test"]["log"])
    def saved_rows(raw):
        return [json.loads(line.split(b" ",1)[1]) for line in raw.splitlines() if line.startswith(b"SAMPLER_BOUNDARY_ROW ")]
    b_rows,a_rows=saved_rows(braw),saved_rows(araw)
    need(len(b_rows)==len(a_rows)==344,"paired actual scalar population")
    changes=collections.Counter()
    for b,a in zip(b_rows,a_rows):
        for field in ("ordinal","id","group","kernel","api","x_f64_bits","y_f64_bits","oracle_kind","tolerance_code_units"):
            need(b[field]==a[field],"unchanged before/after row authority "+b["id"]+" "+field)
        if b["actual_kind"]!=a["actual_kind"] or b["actual_f32_bits"]!=a["actual_f32_bits"]:
            changes[(a["group"],a["kernel"])]+=1
    DETAIL["source_audit"]=dict(source_count=len(before),changed=changed,archive_reconstruction=True,
        all_current_sources_equal_repaired_archive=True,actual_scalar_changes=[
          dict(group=k[0],kernel=k[1],count=v) for k,v in sorted(changes.items())])
logref=release['stages'][command['variant']+'-test']['log']
lograw=get(logref)
need(str((ROOT/logref['path']).resolve())==command['command'][6],'helper exact released log path')
if ERRORS:
    refusal=dict(schema="sampler-independent-adapter-refusal-v1",command=command,
                 reads=READS,charged_read_bytes=READ_BYTES,findings=DETAIL,failures=ERRORS,
                 parent_cpu_sample=time.process_time()-CPU,whole_wall_sample=time.monotonic()-START)
    path=WORK/("independent-adapter-refusal-"+str(INDEX)+".json")
    with path.open("x",encoding="utf-8") as f:json.dump(refusal,f,indent=2)
    raise RuntimeError("transport metadata refusal; retained "+str(path))
prefix=WORK/('independent-read-slice-'+str(INDEX))
paths={k:Path(str(prefix)+'-'+suffix) for k,suffix in [('stdout','stdout.bin'),('stderr','stderr.bin'),('exit','exit.txt'),('ledger','ledger.json')]}
assert all(not p.exists() for p in paths.values())
childstart=time.monotonic()
p=subprocess.Popen(command['command'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
timed_out=False;owned_termination=False
try:
    out,err=p.communicate(timeout=max(.1,11-(time.monotonic()-START)))
except subprocess.TimeoutExpired:
    timed_out=True
    # This is the directly owned, childless saved-bit reader, never a peer process.
    p.kill();owned_termination=True
    out,err=p.communicate(timeout=1)
code=p.returncode
need(not timed_out and not owned_termination,"reader completed without timeout termination")
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
helper_raw=read(command['output']) if Path(command['output']).exists() else None
need(helper_raw is not None,"actual helper output exists")
helper=json.loads(helper_raw) if helper_raw is not None else None
try:
    helper_advert=json.loads(out)
except (ValueError,UnicodeError):
    helper_advert=None
    need(False,"complete helper stdout advertisement")
if helper_advert is not None and helper_raw is not None:
    output_ref=dict(path=command["output"],bytes=len(helper_raw),sha256=hashlib.sha256(helper_raw).hexdigest())
    need(same_owned_ref(dict(path=helper_advert["output"],bytes=helper_advert["bytes"],sha256=helper_advert["sha256"]),output_ref),
         "helper stdout authenticates actual output path/extent/hash")
    need(helper_advert["failures"]==helper["failures"],"helper stdout/output failure association")
if helper:
    need(helper['source']['sha256']==release['reader']['sha256'],'helper actual source hash')
    need(helper['reads'][-1]['sha256']==logref['sha256'] and helper['reads'][-1]['bytes']==logref['bytes'],'helper actual log bytes')
    need(helper['interpretation_complete'] is True and not helper['failures'],'independent saved-bit predicates')
    READ_BYTES+=helper['actual_read_bytes']
    need(PRIOR_CHARGE+READ_BYTES<=768*(1<<20),'aggregate read allocation including failed attempt')
totalcpu=time.process_time()-CPU+childcpu
wholewall=time.monotonic()-START
need(totalcpu+1<=10 and wholewall+2<=15,'combined audit slice plus publication reserve')
ledger=dict(schema='sampler-independent-audit-slice-v1',slice=INDEX,release_sha256=hashlib.sha256(rraw).hexdigest(),
    charged_allocation=INDEX+1,actual_command=command['command'],actual_exit_code=code,helper_timeout=timed_out,owned_reader_termination=owned_termination,
    streams={key:dict(path=str(paths[key]),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
             for key,data in [('stdout',out),('stderr',err),('exit',(str(code)+'\n').encode())]},
    helper_whole_wall_seconds=childwall,
    helper_complete_process_cpu_seconds=childcpu,metadata_parent_cpu_sample=time.process_time()-CPU,
    combined_cpu_sample=totalcpu,whole_slice_wall_sample=wholewall,final_allowance=dict(cpu_seconds=1,wall_seconds=2),
    reads=READS,helper_reads=[] if helper is None else helper['reads'],charged_read_bytes=READ_BYTES,prior_charged_bytes=PRIOR_CHARGE,cumulative_charged_bytes=PRIOR_CHARGE+READ_BYTES,
    findings=DETAIL,helper_review=None if helper is None else helper['review'],failures=ERRORS)
b=(json.dumps(ledger,indent=2,allow_nan=False)+'\n').encode()
assert len(b)<8<<20
with paths['ledger'].open('xb') as f:f.write(b)
assert time.process_time()-CPU+childcpu<=10 and time.monotonic()-START<=15
print(json.dumps(dict(slice=INDEX,actual_exit_code=code,combined_cpu_sample=totalcpu,whole_slice_wall_sample=wholewall,
    charged_read_bytes=READ_BYTES,ledger=dict(path=str(paths['ledger']),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()),
    failures=ERRORS,helper_review=None if helper is None else helper['review']),allow_nan=False))
raise SystemExit(0 if not ERRORS else 1)
